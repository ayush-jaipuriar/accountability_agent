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
    
    # Notification message (v3.1.0 release)
    message = (
        "🚀 <b>Release Notes: Accountability Agent v3.1.0 Update</b>\n\n"
        "We've deployed a core architecture and scoring engine upgrade (<b>v3.1.0</b>) to improve behavior-change dynamics and telemetry accuracy.\n\n"
        "<b>What's Changed in v3.1.0:</b>\n\n"
        "1️⃣ <b>Proportional Habit Scoring (v3 Engine)</b> 📈\n"
        "• Replaced binary pass/fail cutoffs with continuous proportional credit curves:\n"
        "  <code>credit = min(actual_hours / target_hours, 1.0)</code>\n"
        "• Logging 1.5h deep work (2.0h target) or 0.7h skill building now earns <b>75% and 35% credit</b> respectively instead of 0%. Eliminates single-threshold penalty traps.\n\n"
        "2️⃣ <b>Visual Telemetry & Progress Bars</b> 📊\n"
        "• Post check-in feedback now renders real-time visual progress bars per habit vector:\n"
        "  <code>Deep Work: 1.5h / 2.0h  ██████░░ 75%</code>\n"
        "• Evaluates continuous metrics directly from your Tier 1 schema.\n\n"
        "3️⃣ <b>Low-Friction Intervention Engine</b> 💙\n"
        "• Reduced activation energy on missed check-in triggers (Days 2–5+).\n"
        "• Introduces single-emoji state queries (🟢/🟡/🔴) and 30-second <code>/quickcheckin</code> routes to prevent ghosting cascades.\n\n"
        "4️⃣ <b>Return Telemetry & Contextual Adaptation</b> 🧠\n"
        "• Returning after an absence now captures a <code>return_reason</code> classification (<i>Overwhelmed</i>, <i>Avoidance</i>, <i>Schedule Conflict</i>, etc.) to dynamically tune downstream coaching logic.\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        "Run a check-in tonight to inspect your updated telemetry:\n"
        "👉 <b>/checkin</b>"
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
