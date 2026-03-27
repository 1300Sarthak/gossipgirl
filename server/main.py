import os
import json
import uuid
import httpx
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Form, Request
from fastapi.responses import PlainTextResponse
from fastapi.staticfiles import StaticFiles
from twilio.request_validator import RequestValidator

from server.llm_client import transform_to_gossip_girl

app = FastAPI()

UPLOADS_DIR = Path("static/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# In-memory post store
# ---------------------------------------------------------------------------
posts: List[dict] = []
MAX_POSTS = 50

# ---------------------------------------------------------------------------
# WebSocket connection manager
# ---------------------------------------------------------------------------
connected_clients: List[WebSocket] = []


async def broadcast(post: dict):
    payload = json.dumps(post)
    stale = []
    for ws in connected_clients:
        try:
            await ws.send_text(payload)
        except Exception:
            stale.append(ws)
    for ws in stale:
        connected_clients.remove(ws)


@app.websocket("/ws")
async def websocket_endpoint(ws: WebSocket):
    await ws.accept()
    connected_clients.append(ws)
    try:
        while True:
            await ws.receive_text()
    except WebSocketDisconnect:
        if ws in connected_clients:
            connected_clients.remove(ws)


# ---------------------------------------------------------------------------
# Twilio SMS/MMS webhook
# ---------------------------------------------------------------------------
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN", "")
TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID", "")


def _validate_twilio(request: Request, body: dict) -> bool:
    if not TWILIO_AUTH_TOKEN or TWILIO_AUTH_TOKEN.startswith("your_"):
        return True
    signature = request.headers.get("X-Twilio-Signature", "")
    if not signature:
        return True  # no signature = local dev request, skip validation
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    url = str(request.url)
    return validator.validate(url, body, signature)


async def _download_twilio_media(media_url: str) -> tuple[bytes, str]:
    """Download media from Twilio, returns (data, content_type)."""
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(media_url, auth=auth)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "image/jpeg")
        return resp.content, ct


@app.post("/webhook/sms")
async def twilio_sms(request: Request):
    form = await request.form()
    form_dict = dict(form)

    if not _validate_twilio(request, form_dict):
        return PlainTextResponse("Forbidden", status_code=403)

    body_text = str(form_dict.get("Body", "")).strip()
    from_num = str(form_dict.get("From", ""))
    num_media = int(form_dict.get("NumMedia", 0))

    image_data: Optional[bytes] = None
    image_mime: Optional[str] = None
    image_url: Optional[str] = None

    if num_media > 0:
        media_url = str(form_dict.get("MediaUrl0", ""))
        media_ct = str(form_dict.get("MediaContentType0", "image/jpeg"))
        if media_url:
            try:
                image_data, image_mime = await _download_twilio_media(media_url)
                ext = image_mime.split("/")[-1].split(";")[0]
                if ext == "jpeg":
                    ext = "jpg"
                fname = f"{uuid.uuid4().hex}.{ext}"
                (UPLOADS_DIR / fname).write_bytes(image_data)
                image_url = f"/uploads/{fname}"
                print(f"[MMS] Saved image: {image_url} ({len(image_data)} bytes)")
            except Exception as e:
                print(f"[MMS] Failed to download media: {e}")

    if not body_text and not image_data:
        return _twiml_response("Send me some gossip and I'll spread the word. xo xo")

    gossip_text, provider = await transform_to_gossip_girl(
        body_text or "Check out this photo.",
        image_data=image_data,
        image_mime=image_mime,
    )

    post = {
        "id": str(uuid.uuid4()),
        "original": body_text,
        "gossip": gossip_text,
        "provider": provider,
        "from": from_num[-4:] if len(from_num) >= 4 else "anon",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    if image_url:
        post["image"] = image_url

    posts.insert(0, post)
    if len(posts) > MAX_POSTS:
        posts.pop()

    await broadcast(post)
    return _twiml_response(gossip_text)


def _twiml_response(message: str) -> PlainTextResponse:
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        "<Response><Message>" + message + "</Message></Response>"
    )
    return PlainTextResponse(xml, media_type="application/xml")


# ---------------------------------------------------------------------------
# REST API
# ---------------------------------------------------------------------------
@app.get("/api/posts")
async def get_posts():
    return posts


# ---------------------------------------------------------------------------
# Serve uploaded images
# ---------------------------------------------------------------------------
app.mount("/uploads", StaticFiles(directory="static/uploads"), name="uploads")

# ---------------------------------------------------------------------------
# Static files (served last so API routes take priority)
# ---------------------------------------------------------------------------
app.mount("/", StaticFiles(directory="static", html=True), name="static")
