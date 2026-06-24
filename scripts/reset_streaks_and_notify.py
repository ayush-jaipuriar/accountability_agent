#!/usr/bin/env python3
"""
Reset Streaks and Notify Users
==============================

Resets user streaks to 1 due to the 1-week Telegram ban in India, and sends
a notification informing them of the reset along with a motivational quote.

Usage:
    # Dry run to see what would happen
    python3 scripts/reset_streaks_and_notify.py --dry-run
    
    # Run only for a specific user (for testing)
    python3 scripts/reset_streaks_and_notify.py --user 123456789
    
    # Run for all users
    python3 scripts/reset_streaks_and_notify.py
"""

import sys
import os
import argparse
import asyncio
import time
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.firestore_service import firestore_service
from src.bot.telegram_bot import bot_manager
from src.config import settings
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DEFAULT_MESSAGE = (
    "⚡ <b>We are Operational Again!</b>\n\n"
    "Due to the recent Telegram service disruption in India, our agent was offline for about a week. "
    "We know many of you missed check-ins and saw your streaks break.\n\n"
    "To ensure a fair and fresh start, we have <b>reset all user streak counters to 1</b>. "
    "Your historical all-time best streaks remain unchanged!\n\n"
    "<blockquote><i>\"If you can't control your mind, you can't control your life.\"</i>\n"
    "— Alex Becker</blockquote>\n\n"
    "Let's get back on track and start building again today! Send /start or perform your check-in tonight to keep your new streak alive. 💪"
)

async def main():
    parser = argparse.ArgumentParser(description="Reset user streaks and notify them.")
    parser.add_argument("--dry-run", action="store_true", help="Do not write to DB or send messages.")
    parser.add_argument("--user", type=str, help="Only run for this specific user ID.")
    parser.add_argument("--silent", action="store_true", help="Update database but do not send Telegram notifications.")
    parser.add_argument("--message", type=str, default=DEFAULT_MESSAGE, help="Custom notification message.")
    
    args = parser.parse_args()
    
    logger.info("🚀 Starting streak reset and notification script...")
    logger.info(f"   Environment: {settings.environment}")
    logger.info(f"   Dry Run: {args.dry_run}")
    logger.info(f"   Silent (No Telegram): {args.silent}")
    if args.user:
        logger.info(f"   Target User: {args.user}")
    else:
        logger.info(f"   Target: ALL users")
        
    # Initialize bot if not silent and not dry run
    if not args.silent and not args.dry_run:
        logger.info("Initializing Telegram bot...")
        await bot_manager.application.initialize()
        logger.info("✅ Telegram bot initialized")
        
    # Fetch users
    users = []
    if args.user:
        user = firestore_service.get_user(args.user)
        if user:
            users = [user]
        else:
            logger.error(f"❌ User {args.user} not found in database.")
            sys.exit(1)
    else:
        try:
            users = firestore_service.get_all_users()
        except Exception as e:
            logger.error(f"❌ Failed to fetch users: {e}")
            sys.exit(1)
            
    logger.info(f"📋 Found {len(users)} users to process.")
    
    updated_count = 0
    notified_count = 0
    failed_notifications = 0
    
    start_time = time.time()
    
    for user in users:
        current_streak = user.streaks.current_streak if user.streaks else 0
        logger.info(f"👤 User: {user.name} ({user.user_id}) - Current Streak: {current_streak}")
        
        # 1. Update streak in database
        if current_streak != 1:
            logger.info(f"   🔄 Resetting streak from {current_streak} -> 1")
            if not args.dry_run:
                success = firestore_service.update_user(user.user_id, {"streaks.current_streak": 1})
                if success:
                    updated_count += 1
                    logger.info("   ✅ Firestore updated successfully")
                else:
                    logger.error("   ❌ Failed to update Firestore")
            else:
                updated_count += 1
                logger.info("   [Dry Run] Would update Firestore")
        else:
            logger.info("   ℹ️ Streak is already 1, no update needed")
            
        # 2. Send notification
        if not args.silent:
            if not args.dry_run:
                try:
                    await bot_manager.bot.send_message(
                        chat_id=user.telegram_id,
                        text=args.message,
                        parse_mode='HTML'
                    )
                    notified_count += 1
                    logger.info("   ✅ Telegram notification sent")
                    
                    # Rate limiting: 25 msg/sec max (0.04s delay)
                    await asyncio.sleep(0.04)
                except Exception as e:
                    failed_notifications += 1
                    logger.error(f"   ❌ Failed to send Telegram notification: {e}")
            else:
                notified_count += 1
                logger.info("   [Dry Run] Would send Telegram notification")
                
    duration = time.time() - start_time
    logger.info("=" * 60)
    logger.info("📊 Processing Summary")
    logger.info(f"   Total Users Evaluated: {len(users)}")
    logger.info(f"   Firestore Streaks Updated: {updated_count}")
    logger.info(f"   Telegram Notifications Sent: {notified_count}")
    logger.info(f"   Telegram Notifications Failed: {failed_notifications}")
    logger.info(f"   Duration: {duration:.2f}s")
    logger.info("=" * 60)

if __name__ == "__main__":
    asyncio.run(main())
