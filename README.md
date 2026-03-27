# gossip girl

> *"Spotted: An anonymous tip line for the Upper East Side, powered by AI."*

A real-time gossip platform inspired by the iconic Gossip Girl blog from the CW television series. Text your gossip (with photos) to a phone number, and an AI transforms it into dramatic Gossip Girl narration — broadcast live to everyone watching. Just like the show, but real.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-latest-009688)
![Docker](https://img.shields.io/badge/Docker-ready-2496ED)
![License](https://img.shields.io/badge/License-MIT-yellow)

---

## The Idea

In the show *Gossip Girl*, an anonymous blogger narrates the scandalous lives of Manhattan's elite. Students at Constance Billard and St. Jude's would text tips to Gossip Girl, who'd publish them on her blog with her signature dramatic flair — snarky commentary, single-letter nicknames, and always signed off with *"xo xo, Gossip Girl."*

This project brings that concept to life. Anyone can text gossip (or send photos) to a real phone number. An AI — channeling the voice of Gossip Girl herself — rewrites the tip in her iconic style and publishes it to a live website that looks like it was pulled straight from the show. The site features the same dark, elegant aesthetic with gold accents, bokeh city lights, and the familiar navigation layout fans will recognize.

It's designed for parties, college events, campus life, or just messing around with friends. Set it up, share the number, project the site on a screen, and watch the gossip roll in.

---

## What It Does

- **Text-to-blog pipeline** — Send an SMS or MMS to the Twilio number. The AI transforms your message into Gossip Girl's voice and publishes it instantly.
- **Photo support** — Send images via MMS. They show up alongside the narration, described by the AI in Gossip Girl's style.
- **Real-time updates** — Posts appear live on every connected browser via WebSocket. No refreshing needed.
- **Anonymized tips** — Phone numbers are masked (only last 4 digits shown as `***XXXX`). Gossip Girl protects her sources.
- **AI narration** — The AI writes in third-person dramatic narrator voice with snarky commentary, rhetorical questions, Upper East Side references, and single-letter nicknames.
- **Photo gallery** — The "pics" tab collects all image posts into a visual grid.
- **Legal protection** — Terms & Conditions popup on first visit. Full legal disclaimers in the links section.

---

## Ideas & Use Cases

- **College parties** — Project the site on a TV or monitor. Share the number. Let the gossip flow.
- **Campus events** — Rush week, homecoming, greek life events — anonymous tips make it fun.
- **Friend groups** — Drop the number in a group chat. See who has the best tea.
- **School spirit events** — Pep rallies, dances, game days. The Upper East Side energy fits anywhere.
- **Corporate events** — Company parties, team offsites (keep it PG). An anonymous compliment/roast board.
- **Watch parties** — Watching Gossip Girl together? Text gossip about the characters. Meta.
- **Wedding receptions** — Guests text anonymous tips about the couple. The AI narrates the love story.
- **Birthday parties** — Friends send embarrassing stories. Gossip Girl delivers them with style.
- **Dorm floors** — Set it up for the semester. A living, breathing gossip board for your floor.
- **Hackathons** — Use it as a fun social layer during the event.

---

## Architecture

```
                    +-----------+
  User sends SMS -> |  Twilio   |
  or MMS           +-----------+
                         |
                    POST /webhook/sms
                         |
                   +------------+
                   |  FastAPI   |
                   |  Server    |
                   +------------+
                     |        |
              Download MMS    Pass text + image
              from Twilio     to LLM chain
                     |        |
                     v        v
              +----------+  +------------------+
              | /uploads |  | LLM Fallback     |
              |          |  | Chain:           |
              +----------+  | 1. Claude        |
                            | 2. Gemini        |
                            | 3. NVIDIA NIM    |
                            | 4. Hardcoded     |
                            +------------------+
                                    |
                              Gossip Girl
                              narration
                                    |
                         +-------------------+
                         | WebSocket         |
                         | Broadcast to all  |
                         | connected clients |
                         +-------------------+
                                    |
                              +----------+
                              | Browser  |
                              | (Live    |
                              |  Feed)   |
                              +----------+
```

---

## Tech Stack

| Layer | Technology | Purpose |
|-------|-----------|---------|
| **Backend** | FastAPI + Uvicorn | Async web server with WebSocket support |
| **SMS/MMS** | Twilio | Receives texts, downloads images, sends confirmations |
| **AI (Primary)** | Claude (`claude-sonnet-4-20250514`) | Best narration quality, image understanding |
| **AI (Fallback 1)** | Gemini (`gemini-2.0-flash`) | Fast, solid fallback with image support |
| **AI (Fallback 2)** | NVIDIA NIM (`meta/llama-3.3-70b-instruct`) | Text-only fallback via NVIDIA's inference API |
| **AI (Fallback 3)** | Hardcoded response | If all 3 providers are down, a static Gossip Girl message |
| **Frontend** | Vanilla HTML/CSS/JS | Single-page app, no build step, no dependencies |
| **Real-time** | WebSocket | Instant post delivery to all connected browsers |
| **Containerization** | Docker + Docker Compose | One command deployment |
| **Tunnel** | ngrok | Expose local server to the internet for Twilio webhooks |

### LLM Fallback Chain

The system tries providers in order and gracefully degrades:

1. **Claude** — Primary. Best quality narration. Supports text + images.
2. **Gemini** — If Claude is down or rate-limited. Supports text + images.
3. **NVIDIA NIM** — If both Claude and Gemini fail. Text-only (no image analysis).
4. **Hardcoded** — Nuclear option. If every API is down, returns a pre-written Gossip Girl response so the site never breaks.

This means the site literally cannot fail to produce a response. Worst case, you get a generic Gossip Girl quip instead of AI-generated narration.

---

## Setup & Usage

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) installed
- [ngrok](https://ngrok.com/) installed and authenticated
- A [Twilio](https://www.twilio.com/) account with a phone number
- API keys for at least one LLM provider (Claude, Gemini, or NVIDIA NIM)

### 1. Clone the repo

```bash
git clone https://github.com/1300Sarthak/gossipgirl.git
cd gossipgirl
```

### 2. Create your `.env` file

```bash
cp .env.example .env  # or create manually
```

Add your keys:

```env
TWILIO_PHONE_NUMBER=+1XXXXXXXXXX
TWILIO_ACCOUNT_SID=ACXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
TWILIO_AUTH_TOKEN=your_twilio_auth_token

CLAUDE_API_KEY=sk-ant-XXXXXXXXXXXXX
GEMINI_API_KEY=XXXXXXXXXXXXX
NVIDIA_NIM_API_KEY=nvapi-XXXXXXXXXXXXX
```

You don't need all three LLM keys — the fallback chain skips providers with missing keys. But having at least one is required.

### 3. Start the server

```bash
docker compose up -d
```

That's it. The server is running on port 8000.

### 4. Expose with ngrok

In a separate terminal:

```bash
ngrok http 8000
```

ngrok will output something like:

```
Forwarding  https://xxxx-xx-xx-xxx-xx.ngrok-free.app -> http://localhost:8000
```

**Copy that `https://....ngrok-free.app` URL.** That's your public URL.

### 5. Configure Twilio

1. Go to your [Twilio Console](https://console.twilio.com/)
2. Navigate to **Phone Numbers** > **Manage** > **Active Numbers**
3. Click your phone number
4. Under **Messaging** > **A message comes in**, set:
   - **Webhook**: `https://xxxx-xx-xx-xxx-xx.ngrok-free.app/webhook/sms`
   - **HTTP Method**: `POST`
5. Save

### 6. You're live

- Open `https://xxxx-xx-xx-xxx-xx.ngrok-free.app` in your browser to see the site
- Text something to your Twilio number
- Watch it appear on the site in Gossip Girl's voice

---

## Project Structure

```
gossipgirl/
├── server/
│   ├── __init__.py          # Package init
│   ├── main.py              # FastAPI app, routes, WebSocket, Twilio webhook
│   └── llm_client.py        # Multi-provider LLM integration & fallback chain
├── static/
│   ├── index.html           # Frontend (single file — HTML, CSS, JS)
│   └── uploads/             # MMS images downloaded from Twilio
├── reference/               # Design reference images from the show
├── .env                     # Environment variables (not committed)
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── README.md
```

---

## Technical Details

### How a Text Becomes a Post

1. User sends SMS/MMS to the Twilio phone number
2. Twilio sends a `POST` request to `/webhook/sms` with the message body, sender info, and media URLs
3. Server validates the Twilio request signature (optional, gracefully skipped for local dev)
4. If MMS media is attached, the server downloads the image from Twilio's servers using authenticated `httpx` requests and saves it to `static/uploads/` with a UUID filename
5. The original text (and image, if any) is passed to the LLM fallback chain
6. The LLM rewrites the message in Gossip Girl's voice — third person, snarky, dramatic, with Upper East Side references and `xo xo, Gossip Girl` sign-off
7. A post object is created with: unique ID, original text, AI narration, LLM provider used, anonymized sender, timestamp, and image path
8. The post is broadcast to all connected WebSocket clients instantly
9. The post is stored in-memory (up to 50 posts, FIFO)
10. A TwiML XML response is sent back to Twilio, which delivers a confirmation SMS to the sender

### WebSocket Protocol

The frontend establishes a WebSocket connection to `/ws`. Each message is a JSON object:

```json
{
  "id": "uuid",
  "original": "original text",
  "gossip": "AI-transformed narration",
  "provider": "claude|gemini|nvidia|fallback",
  "from": "1234",
  "timestamp": "2024-01-01T00:00:00",
  "image": "/uploads/filename.jpg"
}
```

Auto-reconnect with exponential backoff (1s → 15s max) ensures the connection recovers from drops.

### Frontend Architecture

The entire frontend is a single `index.html` file — no build step, no npm, no framework. It uses:

- **CSS Grid** for the 3-column desktop layout (sidebar / feed / nav)
- **CSS custom properties** for the color system
- **Vanilla JavaScript** for WebSocket management, tab navigation, and DOM manipulation
- **Google Fonts** (Cormorant Garamond, Playfair Display) for the editorial aesthetic
- **Programmatic bokeh dots** (60 animated blurred circles) for the city-lights background
- **Fixed bottom nav bar** on mobile for thumb-friendly navigation
- **localStorage** for terms acceptance persistence

### Security

- Phone numbers are anonymized — only the last 4 digits are shown publicly
- HTML content is escaped to prevent XSS
- Twilio request signature validation is implemented (soft-fail for local dev)
- No database — posts are in-memory and lost on restart (by design, for privacy)
- Terms & Conditions with explicit user consent required on first visit

---

## Important Notes

- **ngrok must be running** for Twilio to reach your server. If ngrok stops or your machine sleeps, incoming texts won't be processed until you restart it.
- **Posts are in-memory only.** Restart the server and they're gone. This is intentional — gossip is fleeting.
- **The Twilio number is real.** Standard SMS rates apply to anyone texting it.
- **AI costs apply.** Each text triggers an API call to your LLM provider. Claude and Gemini have free tiers; monitor your usage.

---

## Legal Disclaimer

This project is a fan-made creation for entertainment and educational purposes only. "Gossip Girl" is a trademark of Alloy Entertainment, Warner Bros. Television, and The CW Network. This project is not affiliated with, endorsed by, or connected to the Gossip Girl franchise or any related entities.

All content submitted through this service is user-generated. The developer assumes no responsibility for the content posted. See the in-app Terms & Conditions for the full legal agreement.

---

## License

MIT License

Copyright (c) 2025 Sarthak Sethi

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

---

## Made by

**Sarthak Sethi**

- [sarthak.lol](https://sarthak.lol)
- [cal.com/sxthak](https://cal.com/sxthak)
- [sarthakluv@gmail.com](mailto:sarthakluv@gmail.com)
- [linkedin.com/in/sarsethi](https://linkedin.com/in/sarsethi)
- [github.com/1300Sarthak](https://github.com/1300Sarthak)

---

*you know you love me, xo xo*
