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
from src.bot.telegram_bot import bot_manager
from src.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def send_broadcast():
    """Send reminder time update notification to all users."""
    
    logger.info("🚀 Starting broadcast notification...")
    logger.info(f"   Environment: {settings.environment}")
    
    # Initialize bot application
    await bot_manager.application.initialize()
    logger.info("✅ Telegram bot initialized")
    
    # Get all users
    try:
        users = firestore_service.get_all_users()
        logger.info(f"📋 Found {len(users)} users to notify")
    except Exception as e:
        logger.error(f"❌ Failed to fetch users: {e}")
        return
    
    # Notification message
    message = (
        f"🛠️ <b>Update & Bug Fixes</b>\n\n"
        f"We just shipped a few improvements to make your experience better:\n\n"
        f"1️⃣ <b>Weekly Report Chart Fixed</b>\n"
        f"The meaningless sleep chart is gone. Your weekly report now shows a Tier 1 Consistency chart — a clear visual of how you're doing on your 6 core habits.\n\n"
        f"2️⃣ <b>Bold Text Rendering Fixed</b>\n"
        f"Intervention and feedback messages now render bold text correctly in Telegram.\n\n"
        f"3️⃣ <b>Smarter AI Feedback</b>\n"
        f"Your daily AI coach now sees a full week of your qualitative notes (challenges, priorities, obstacles) to give more pattern-aware, personalized feedback.\n\n"
        f"Everything else stays the same. Keep building those streaks! 🔥"
    )
    
    # Send messages with rate limiting
    sent = 0
    failed = 0
    start_time = time.time()
    
    for user in users:
        try:
            await bot_manager.bot.send_message(
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
