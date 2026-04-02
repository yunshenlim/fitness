"""
Bio-OS 2026 — Telegram → Vercel ingest bot
Fix: Asyncio event loop handling
"""

import os
import re
import json
import logging
import requests
import asyncio
from io import BytesIO

from dotenv import load_dotenv
from telethon import TelegramClient, events
from telethon.tl.types import MessageMediaPhoto
import google.generativeai as genai

# ── 1. 环境加载 ────────────────────────────────────────────────────────────────
base_dir = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(base_dir, ".env"))

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bio-os")

# ── 2. 配置读取 ───────────────────────────────────────────────────────────────
try:
    API_ID        = int(os.environ["TG_API_ID"])
    API_HASH      = os.environ["TG_API_HASH"]
    BOT_TOKEN     = os.environ["TG_BOT_TOKEN"]
    INGEST_URL    = os.environ["INGEST_URL"]
    INGEST_SECRET = os.environ["INGEST_API_SECRET"]
    USER_ID       = os.environ["DEFAULT_USER_ID"]
    GEMINI_KEY    = os.environ["GEMINI_API_KEY"]
except KeyError as e:
    log.error(f"❌ 环境变量缺失: {e}")
    exit(1)

genai.configure(api_key=GEMINI_KEY)
gemini = genai.GenerativeModel("gemini-1.5-flash")

# ── 3. 正则与推送逻辑 ──────────────────────────────────────────────────────────
RE_FITNESS = re.compile(r"^(?P<exercise>[a-z]+)\s+(?P<weight>\d+(?:\.\d+)?)\s+(?P<sets>\d+)\s+(?P<reps>\d+)$", re.IGNORECASE)
RE_DISCIPLINE = re.compile(r"^1$")

def push(category: str, data: dict) -> bool:
    try:
        payload = {"category": category, "data": data, "user_id": USER_ID}
        headers = {"x-api-secret": INGEST_SECRET}
        r = requests.post(INGEST_URL, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        log.info(f"✅ Success: {category} -> {data}")
        return True
    except Exception as e:
        log.error(f"❌ Push failed: {e}")
        return False

async def extract_body_stats(image_bytes: bytes) -> dict | None:
    prompt = "Evolt 360 report. Extract numeric metrics. Return ONLY raw JSON."
    try:
        response = gemini.generate_content([{"mime_type": "image/jpeg", "data": image_bytes}, prompt])
        text = response.text.strip()
        if "```" in text:
            text = re.sub(r"```[a-z]*\n|```", "", text).strip()
        return json.loads(text)
    except Exception as e:
        log.error(f"⚠️ Gemini extraction failed: {e}")
        return None

# ── 4. Bot 核心 (修复异步启动) ─────────────────────────────────────────────────
async def main():
    log.info("🚀 Bio-OS Bot 正在初始化...")
    client = TelegramClient("bio_os_session", API_ID, API_HASH)
    
    @client.on(events.NewMessage)
    async def handler(event: events.NewMessage.Event):
        if event.message.media and isinstance(event.message.media, MessageMediaPhoto):
            msg = await event.reply("🔍 正在解析图片...")
            image_bytes = await client.download_media(event.message, bytes)
            stats = await extract_body_stats(image_bytes)
            if stats:
                ok = push("body", stats)
                await msg.edit(f"✅ 已存入:\n`{json.dumps(stats)}`" if ok else "❌ 写入失败")
            else:
                await msg.edit("⚠️ 无法解析")
            return

        text = (event.message.text or "").strip()
        if RE_DISCIPLINE.match(text):
            ok = push("admin", {"event_type": "discipline_tick"})
            await event.reply("🎯 +1" if ok else "❌")
        
        m = RE_FITNESS.match(text)
        if m:
            data = {"exercise": m.group("exercise").lower(), "weight_kg": float(m.group("weight")), "sets": int(m.group("sets")), "reps": int(m.group("reps"))}
            ok = push("fitness", data)
            await event.reply(f"💪 Logged: {data['exercise']}" if ok else "❌")

    await client.start(bot_token=BOT_TOKEN)
    log.info("✅ 机器人上线成功！")
    await client.run_until_disconnected()

if __name__ == "__main__":
    try:
        # 显式创建并运行事件循环
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("👋 机器人已关闭")
    except Exception as e:
        log.critical(f"💥 发生错误: {e}")
