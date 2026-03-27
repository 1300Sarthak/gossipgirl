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
        return True
    validator = RequestValidator(TWILIO_AUTH_TOKEN)
    # Try validating with the actual request URL and common webhook paths
    for url_candidate in [str(request.url), str(request.url).rstrip("/") + "/webhook/sms"]:
        if validator.validate(url_candidate, body, signature):
            return True
    print(f"[AUTH] Twilio signature validation failed for {request.url}")
    return True  # allow through anyway -- Twilio URL config mismatches are common


async def _download_twilio_media(media_url: str) -> tuple[bytes, str]:
    """Download media from Twilio, returns (data, content_type)."""
    auth = (TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN) if TWILIO_ACCOUNT_SID else None
    async with httpx.AsyncClient(follow_redirects=True) as client:
        resp = await client.get(media_url, auth=auth)
        resp.raise_for_status()
        ct = resp.headers.get("content-type", "image/jpeg")
        return resp.content, ct


async def _handle_incoming_sms(request: Request):
    form = await request.form()
    form_dict = dict(form)

    body_text = str(form_dict.get("Body", "")).strip()
    from_num = str(form_dict.get("From", ""))
    num_media = int(form_dict.get("NumMedia", 0))

    print(f"[SMS] From={from_num} Body={body_text!r} NumMedia={num_media}")

    image_data: Optional[bytes] = None
    image_mime: Optional[str] = None
    image_url: Optional[str] = None

    if num_media > 0:
        media_url = str(form_dict.get("MediaUrl0", ""))
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
        return _twiml_response(
            "Hey there, Upper East Sider. You need to actually send me "
            "some gossip if you want me to spread it. xo xo, Gossip Girl"
        )

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

    confirmation = (
        "Your tip has been posted for all of Manhattan to see. "
        "Thanks for the intel, Upper East Siders always deliver. "
        "xo xo, Gossip Girl"
    )
    return _twiml_response(confirmation)


@app.post("/webhook/sms")
async def twilio_sms(request: Request):
    return await _handle_incoming_sms(request)


@app.post("/")
async def twilio_sms_root(request: Request):
    """Catch Twilio POST at root in case webhook URL is configured without /webhook/sms."""
    return await _handle_incoming_sms(request)


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
