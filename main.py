"""
Bio-OS 2026 — Telegram → Vercel Ingest Bot (FSGE Edition)
Author: yunshenlim
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

# 加载配置
load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("bio-os")

# ── 配置校验 ──────────────────────────────────────────────────────────────────
API_ID        = int(os.environ["TG_API_ID"])
API_HASH      = os.environ["TG_API_HASH"]
BOT_TOKEN     = os.environ["TG_BOT_TOKEN"]
INGEST_URL    = os.environ["INGEST_URL"]          # 确保是 https://fitness-xa22.vercel.app/api/ingest
INGEST_SECRET = os.environ["INGEST_API_SECRET"]
USER_ID       = os.environ.get("DEFAULT_USER_ID", "yunshen")
GEMINI_KEY    = os.environ["GEMINI_API_KEY"]

genai.configure(api_key=GEMINI_KEY)
gemini = genai.GenerativeModel("gemini-1.5-flash")

# ── 正则匹配模式 ──────────────────────────────────────────────────────────────
# 健身记录: bench 80 5 5 (动作 重量 组数 次数)
RE_FITNESS = re.compile(
    r"^(?P<exercise>[a-z]+)\s+(?P<weight>\d+(?:\.\d+)?)\s+(?P<sets>\d+)\s+(?P<reps>\d+)$",
    re.IGNORECASE,
)
# 纪律打卡: 发送 "1"
RE_DISCIPLINE = re.compile(r"^1$")

# ── 数据推送助手 ───────────────────────────────────────────────────────────────
def push(category: str, data: dict) -> bool:
    try:
        payload = {"category": category, "data": data, "user_id": USER_ID}
        headers = {"x-api-secret": INGEST_SECRET, "Content-Type": "application/json"}
        
        log.info(f"🚀 Pushing {category} to {INGEST_URL}...")
        r = requests.post(INGEST_URL, json=payload, headers=headers, timeout=15)
        r.raise_for_status()
        log.info(f"✅ Push Success: {r.status_code}")
        return True
    except Exception as e:
        log.error(f"❌ Push Failed: {e}")
        return False

# ── Gemini: 智能解析 Evolt 360 报告 ───────────────────────────────────────────
async def extract_body_stats(image_bytes: bytes) -> dict | None:
    prompt = (
        "Analysis needed for Evolt 360 body composition image. "
        "Extract all numeric data: Body Fat %, Muscle Mass (kg), Weight (kg), BMR, etc. "
        "Format: Return ONLY raw JSON with snake_case keys. No conversational text."
    )
    try:
        response = gemini.generate_content(
            [{"mime_type": "image/jpeg", "data": image_bytes}, prompt]
        )
        # 清理可能存在的 Markdown 代码块标记
        raw = response.text.strip().replace("```json", "").replace("```", "").strip()
        return json.loads(raw)
    except Exception as e:
        log.error(f"Gemini processing error: {e}")
        return None

# ── Bot 主程序 ────────────────────────────────────────────────────────────────
client = TelegramClient("bio_os_session", API_ID, API_HASH)

@client.on(events.NewMessage)
async def handler(event: events.NewMessage.Event):
    # 1. 处理图片 (Evolt 扫描件)
    if event.message.media and isinstance(event.message.media, MessageMediaPhoto):
        log.info("📷 收到报告图片，启动 Gemini 解析...")
        image_bytes = await client.download_media(event.message, bytes)
        stats = await extract_body_stats(image_bytes)
        if stats:
            ok = push("body", stats)
            await event.reply("✅ 身体数据已成功解析并存入 Bio-OS。" if ok else "❌ 数据保存失败，请检查 Vercel 端。")
        else:
            await event.reply("⚠️ 无法识别报告内容，请确保照片清晰。")
        return

    text = (event.message.text or "").strip()
    if not text: return

    # 2. 处理纪律打卡 (发送 "1")
    if RE_DISCIPLINE.match(text):
        ok = push("admin", {"event_type": "discipline_tick"})
        await event.reply("🎯 纪律值 +1！继续保持。" if ok else "❌ 系统推送故障。")
        return

    # 3. 处理健身记录 (例如: rdl 80 3 8)
    m = RE_FITNESS.match(text)
    if m:
        data = {
            "exercise": m.group("exercise").lower(),
            "weight": float(m.group("weight")),
            "sets": int(m.group("sets")),
            "reps": int(m.group("reps")),
        }
        ok = push("fitness", data)
        await event.reply(f"💪 已记录: {data['exercise']} {data['weight']}kg" if ok else "❌ 记录失败，后端拒绝连接。")
        return

if __name__ == "__main__":
    log.info("🚀 Bio-OS Telegram Bot 启动中...")
    client.start(bot_token=BOT_TOKEN)
    client.run_until_disconnected()
