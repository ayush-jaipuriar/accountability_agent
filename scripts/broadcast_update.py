"""
Broadcast Update Script
=======================
Sends the v3.0.0 announcement notification message to all registered users.
"""

import os
import sys
import asyncio
import logging
from google.cloud import secretmanager, firestore
from telegram import Bot

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger("broadcast")

PROJECT_ID = "accountability-agent"

ANNOUNCEMENT_MESSAGE = """<b>🚀 INTRODUCING CONSTITUTION AGENT 3.0</b>
<i>A major upgrade to your AI accountability partner.</i>
━━━━━━━━━━━━━━━━━━━━

We’ve completely redesigned your experience to be faster, cleaner, and more powerful. Say goodbye to command clutter and hello to <b>5 Unified Interactive Hubs</b>:

• <b>/today — Master Daily Driver</b> ☀️
Your daily focal point. See morning priorities, toggle completed tasks with 1 tap, and launch your check-in seamlessly.

• <b>/progress — Interactive Performance Hub</b> 📈
Switch between <b>7D</b>, <b>30D</b>, <b>YTD</b>, and <b>All-Time</b> metrics in real time without message spam. Access visual charts, AI memory, and CSV exports instantly.

• <b>/partner — Partner Arena & Duels</b> ⚔️
View your partner's live status and launch 7-day head-to-head duels across Sleep, Deep Work, and Workout consistency.

• <b>/goals — SMART Goals Studio</b> 🎯
Set auto-tracking goals with 1-tap presets and visual progress trackers.

• <b>/settings — Control Center</b> ⚙️
Customize your mode, career stage, timezone, briefing alerts, and streak shields in one place.

━━━━━━━━━━━━━━━━━━━━
<b>⚡ Smarter, Frictionless Check-Ins:</b>
• <b>Predictive Baselines:</b> Intelligent, honest starting values tailored to your recent habits.
• <b>Single Hero Summary:</b> All your habit scores, duel updates, and earned badges delivered in one message.

<i>Tap /today to take the new experience for a spin!</i> 🚀"""


def get_secret(secret_id: str) -> str:
    """Fetch secret from Google Cloud Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    name = f"projects/{PROJECT_ID}/secrets/{secret_id}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("UTF-8").strip()


async def run_broadcast():
    token = get_secret("telegram-bot-token")
    bot = Bot(token=token)
    
    db = firestore.Client(project=PROJECT_ID)
    users_ref = db.collection("users")
    docs = users_ref.stream()
    
    users = []
    for doc in docs:
        d = doc.to_dict()
        if d.get("telegram_id"):
            users.append(d)
            
    logger.info("Found %d registered users to broadcast to.", len(users))
    
    sent = 0
    failed = 0
    
    for u in users:
        telegram_id = u["telegram_id"]
        name = u.get("name", "User")
        try:
            await bot.send_message(
                chat_id=telegram_id,
                text=ANNOUNCEMENT_MESSAGE,
                parse_mode="HTML"
            )
            sent += 1
            logger.info("✅ Sent update broadcast to %s (%s, ID: %s)", name, u.get("user_id"), telegram_id)
            await asyncio.sleep(0.05)  # Rate limit safety
        except Exception as e:
            failed += 1
            logger.error("❌ Failed sending broadcast to %s (%s): %s", name, telegram_id, e)
            
    logger.info("🎉 Broadcast Complete: %d sent successfully, %d failed.", sent, failed)


if __name__ == "__main__":
    asyncio.run(run_broadcast())
