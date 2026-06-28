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
        "🚀 <b>Accountability Agent v3.0: Daily Focus Engine is Live!</b>\n\n"
        "We've combined your morning briefs, to-do lists, and check-ins into one loop:\n\n"
        "🎯 <b>Commit in the Morning</b>\n"
        "Your Morning Brief now has interactive buttons. State your primary priority, tap \"+ Add Task\" for secondary items, and tap \"Commit & Start\" to lock in your day.\n\n"
        "✅ <b>Inline Checkboxes</b>\n"
        "Check off your tasks throughout the day by clicking the checkboxes directly inside your morning brief message.\n\n"
        "⏰ <b>Mid-day Support Nudge</b>\n"
        "If your primary task is incomplete by 3:00 PM, you will get a supportive nudge. Tap the \"Need Support\" button to talk with your AI Coach and work through obstacles.\n\n"
        "📊 <b>80/20 Compliance Scoring</b>\n"
        "Your daily tasks are now integrated into your daily score! Compliance is now weighted: 80% Tier 1 habits + 20% committed daily tasks.\n\n"
        "👉 <i>Type <b>/briefing</b> to start today's focus list! 💪</i>"
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
