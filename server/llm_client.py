import os
import base64
import httpx
import anthropic
from google import genai

SYSTEM_PROMPT = """You are Gossip Girl from the TV show "Gossip Girl" on the CW.
You narrate the lives of Manhattan's elite Upper East Siders.
When given a piece of gossip or information, rewrite it in your signature style:

- Third-person dramatic narrator voice
- Snarky, knowing, playful tone with rhetorical questions
- Reference "the Upper East Side" or Manhattan when it fits naturally
- Give people single-letter nicknames (e.g. "B", "S", "little J") if names appear
- Keep it concise: 2-4 sentences max
- ALWAYS end with "xo xo, Gossip Girl"
- Never break character. You ARE Gossip Girl.
- If an image is included, describe what you see in the photo in your Gossip Girl voice."""

# ── Clients (lazy-initialized, None if key missing) ──

_claude = None
_gemini = None
_nvidia = None

if os.getenv("CLAUDE_API_KEY"):
    _claude = anthropic.AsyncAnthropic(api_key=os.getenv("CLAUDE_API_KEY"))

if os.getenv("GEMINI_API_KEY"):
    _gemini = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

_nvidia_key = os.getenv("NVIDIA_NIM_API_KEY", "")


async def _try_claude(text: str, image_data: bytes | None = None, image_mime: str | None = None) -> str:
    if not _claude:
        raise RuntimeError("No CLAUDE_API_KEY")

    content = []
    if image_data and image_mime:
        content.append({
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_mime,
                "data": base64.b64encode(image_data).decode(),
            },
        })
    content.append({"type": "text", "text": text or "Describe this photo as Gossip Girl."})

    msg = await _claude.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=300,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": content}],
    )
    return msg.content[0].text.strip()


async def _try_gemini(text: str, image_data: bytes | None = None, image_mime: str | None = None) -> str:
    if not _gemini:
        raise RuntimeError("No GEMINI_API_KEY")

    contents = []
    if image_data and image_mime:
        contents.append(genai.types.Part.from_bytes(data=image_data, mime_type=image_mime))
    contents.append(text or "Describe this photo as Gossip Girl.")

    response = await _gemini.aio.models.generate_content(
        model="gemini-2.0-flash",
        contents=contents,
        config=genai.types.GenerateContentConfig(system_instruction=SYSTEM_PROMPT),
    )
    return response.text.strip()


async def _try_nvidia(text: str, image_data: bytes | None = None, image_mime: str | None = None) -> str:
    if not _nvidia_key:
        raise RuntimeError("No NVIDIA_NIM_API_KEY")

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": text or "Write a gossip post."},
    ]

    async with httpx.AsyncClient() as client:
        resp = await client.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {_nvidia_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": "meta/llama-3.3-70b-instruct",
                "messages": messages,
                "max_tokens": 300,
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
        return data["choices"][0]["message"]["content"].strip()


_CHAIN = [
    ("Claude", _try_claude),
    ("Gemini", _try_gemini),
    ("NVIDIA NIM", _try_nvidia),
]


async def transform_to_gossip_girl(
    text: str,
    image_data: bytes | None = None,
    image_mime: str | None = None,
) -> tuple[str, str]:
    """Returns (gossip_text, provider_used). Tries Claude -> Gemini -> NVIDIA."""
    for name, fn in _CHAIN:
        try:
            result = await fn(text, image_data, image_mime)
            print(f"[LLM] {name} succeeded")
            return result, name
        except Exception as e:
            print(f"[LLM] {name} failed: {e}")
            continue

    fallback = (
        f'Spotted: someone spilling tea on the Upper East Side — "{text}" '
        "The details are still developing, but trust me, I always find out. "
        "xo xo, Gossip Girl"
    )
    return fallback, "fallback"
