#!/usr/bin/env python3
"""
Broadcast Notification Script
==============================

Sends a one-time update notification to all active users about reminder time changes.

Usage:
    python scripts/broadcast_notification.py

Rate Limiting:
    - Sends max 25 messages/second to stay well below Telegram's 30 msg/sec limit
    - 0.04s delay between messages
"""

import sys
import os
from pathlib import Path
import asyncio
import time

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.firestore_service import firestore_service
from src.config import settings
from telegram import Bot
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def get_live_bot_token() -> str:
    """Retrieve live bot token from settings or Secret Manager."""
    token = settings.telegram_bot_token
    if token and not token.startswith("dummy_"):
        return token
    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{settings.gcp_project_id}/secrets/telegram-bot-token/versions/latest"
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8").strip()
    except Exception as e:
        logger.warning(f"Could not load token from Secret Manager: {e}")
        return token


async def send_broadcast():
    """Send reminder time update notification to all users."""
    
    logger.info("🚀 Starting broadcast notification...")
    logger.info(f"   Environment: {settings.environment}")
    
    token = get_live_bot_token()
    bot = Bot(token=token)
    await bot.initialize()
    logger.info("✅ Telegram bot initialized")
    
    # Get all users
    try:
        users = firestore_service.get_all_users()
        logger.info(f"📋 Found {len(users)} users to notify")
    except Exception as e:
        logger.error(f"❌ Failed to fetch users: {e}")
        return
    
    # Notification message (v3.2.0 release)
    message = (
        "🚀 <b>Update: Accountability Agent v3.2.0 Release</b>\n\n"
        "We've deployed <b>v3.2.0</b> featuring the <b>Daily Focus Engine</b> and <b>Partner Weekly Performance Reports</b>.\n\n"
        "<b>What's New in v3.2.0:</b>\n\n"
        "1️⃣ <b>Top 3 To-Dos Commitment</b> 🎯\n"
        "• At the end of /checkin, you will now be prompted to lock in tomorrow's priorities:\n"
        "  - <b>#1 Primary Focus (Must-Do)</b>\n"
        "  - <b>#2 Secondary Task</b>\n"
        "  - <b>#3 Secondary Task</b>\n"
        "• Helps you close your day with clear intention for tomorrow.\n\n"
        "2️⃣ <b>Next-Day Task Verification & 80/20 Scoring</b> ⚖️\n"
        "• At the start of your check-in, tap inline buttons (<code>[ ✅ / ❌ ]</code>) to mark which to-dos you completed.\n"
        "• <b>Compliance Score Blending:</b>\n"
        "  - <b>80%</b> Tier 1 Habits (Sleep, Training, Deep Work, etc.)\n"
        "  - <b>20%</b> Daily Focus Tasks (Primary: 50%, Secondaries: 25% each)\n"
        "• Visual progress bars now display your task completion breakdown.\n\n"
        "3️⃣ <b>Partner Weekly Performance Reports</b> 🤝\n"
        "• Sunday weekly reports delivered to your accountability partner now include a performance snapshot highlighting:\n"
        "  - 🔥 <b>Strongest execution areas</b> (e.g., <i>Training: 100%</i>)\n"
        "  - ⚠️ <b>Focus & growth areas</b> (e.g., <i>Deep Work: 45%</i>)\n"
        "  - 💡 <b>Actionable coaching tips</b> for your partner to support you.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "👉 <i>Ready for today? Start your check-in anytime with</i> /checkin <i>or quick mode with</i> /quickcheckin!"
    )
    
    # Send messages with rate limiting
    sent = 0
    failed = 0
    start_time = time.time()
    
    for user in users:
        try:
            await bot.send_message(
                chat_id=user.telegram_id,
                text=message,
                parse_mode='HTML'
            )
            sent += 1
            logger.info(f"✅ Sent to {user.user_id} ({user.name})")
            
            # Rate limiting: 25 msg/sec max (0.04s delay)
            await asyncio.sleep(0.04)
            
        except Exception as e:
            failed += 1
            logger.error(f"❌ Failed to send to {user.user_id}: {e}")
    
    duration = time.time() - start_time
    logger.info("=" * 60)
    logger.info(f"📊 Broadcast Complete")
    logger.info(f"   Total users: {len(users)}")
    logger.info(f"   Sent: {sent}")
    logger.info(f"   Failed: {failed}")
    logger.info(f"   Duration: {duration:.1f}s")
    logger.info("=" * 60)


if __name__ == "__main__":
    asyncio.run(send_broadcast())
