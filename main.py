"""
Bio-OS 2026 — Telegram → Vercel ingest bot
Deps: telethon, google-generativeai, requests, python-dotenv
"""

import os
import re
import json
import logging
import requests
from io import BytesIO

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto
import google.generativeai as genai

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bio-os")

# ── Config ────────────────────────────────────────────────────────────────────
API_ID        = int(os.environ["TG_API_ID"])
API_HASH      = os.environ["TG_API_HASH"]
BOT_TOKEN     = os.environ["TG_BOT_TOKEN"]
INGEST_URL    = os.environ["INGEST_URL"]          # https://your-app.vercel.app/api/ingest
INGEST_SECRET = os.environ["INGEST_API_SECRET"]
USER_ID       = os.environ["DEFAULT_USER_ID"]
GEMINI_KEY    = os.environ["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_KEY)
gemini = genai.GenerativeModel("gemini-1.5-flash")

# ── Regex patterns ────────────────────────────────────────────────────────────
# rdl 80 3 8  →  exercise=rdl, weight=80, sets=3, reps=8
RE_FITNESS = re.compile(
    r"^(?P<exercise>[a-z]+)\s+(?P<weight>\d+(?:\.\d+)?)\s+(?P<sets>\d+)\s+(?P<reps>\d+)$",
    re.IGNORECASE,
)
# "1" alone → discipline tick
RE_DISCIPLINE = re.compile(r"^1$")


# ── HTTP helper ───────────────────────────────────────────────────────────────
def push(category: str, data: dict) -> bool:
    try:
        r = requests.post(
            INGEST_URL,
            json={"category": category, "data": data, "user_id": USER_ID},
            headers={"x-api-secret": INGEST_SECRET},
            timeout=10,
        )
        r.raise_for_status()
        log.info("✓ pushed %s → %s", category, data)
        return True
    except requests.RequestException as e:
        log.error("push failed: %s", e)
        return False


# ── Gemini: extract body stats from Evolt image ───────────────────────────────
async def extract_body_stats(image_bytes: bytes) -> dict | None:
    prompt = (
        "This is an Evolt 360 body composition report. "
        "Extract ALL numeric metrics and return ONLY a valid JSON object "
        "with snake_case keys (e.g. body_fat_percent, muscle_mass_kg, bmr_kcal). "
        "No markdown, no explanation — raw JSON only."
    )
    try:
        response = gemini.generate_content(
            [{"mime_type": "image/jpeg", "data": image_bytes}, prompt]
        )
        raw = response.text.strip().lstrip("```json").rstrip("```").strip()
        return json.loads(raw)
    except Exception as e:
        log.error("Gemini extraction failed: %s", e)
        return None


# ── Bot ───────────────────────────────────────────────────────────────────────
client = TelegramClient("bio_os_session", API_ID, API_HASH)


@client.on(events.NewMessage)
async def handler(event: events.NewMessage.Event):
    # ── Image → body stats ────────────────────────────────────────────────────
    if event.message.media and isinstance(event.message.media, MessageMediaPhoto):
        log.info("📷 image received — calling Gemini")
        image_bytes = await client.download_media(event.message, bytes)
        stats = await extract_body_stats(image_bytes)
        if stats:
            ok = push("body", stats)
            await event.reply("✅ Body stats saved." if ok else "❌ Failed to save stats.")
        else:
            await event.reply("⚠️ Could not parse the report image.")
        return

    text = (event.message.text or "").strip()
    if not text:
        return

    # ── Discipline tick ───────────────────────────────────────────────────────
    if RE_DISCIPLINE.match(text):
        ok = push("admin", {"event_type": "discipline_tick"})
        await event.reply("🎯 +1" if ok else "❌ Error")
        return

    # ── Fitness log ───────────────────────────────────────────────────────────
    m = RE_FITNESS.match(text)
    if m:
        ok = push("fitness", {
            "exercise":  m.group("exercise").lower(),
            "weight_kg": float(m.group("weight")),
            "sets":      int(m.group("sets")),
            "reps":      int(m.group("reps")),
        })
        await event.reply("💪 Logged." if ok else "❌ Error")
        return

    # Unknown input — silently ignore or echo help
    # await event.reply("Usage: `<exercise> <weight> <sets> <reps>` or send `1`")


if __name__ == "__main__":
    log.info("Bio-OS bot starting…")
    client.start(bot_token=BOT_TOKEN)
    client.run_until_disconnected()
