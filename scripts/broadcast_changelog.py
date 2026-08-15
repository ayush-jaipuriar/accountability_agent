"""
Broadcast Changelog to All Active Users (v3.3 Release)
=====================================================
"""

import asyncio
import logging
import os
import sys

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from telegram import Bot
from telegram.error import TelegramError, Forbidden
from src.config import settings
from src.services.firestore_service import firestore_service

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

CHANGELOG_MESSAGE = (
    "🚀 <b>What's New in Your Constitution Agent (v3.3)</b>\n\n"
    "We just released a major upgrade to make your daily check-in faster, cleaner, and more actionable!\n\n"
    "✨ <b>Key Updates:</b>\n\n"
    "⚡ <b>Blazing Fast & Punchy AI Coaching</b>\n"
    "No more long essay paragraphs. Your coach now delivers <b>3 razor-sharp takeaways</b> in seconds:\n"
    "• ⚡ <b>Win:</b> Your biggest execution highlight\n"
    "• ⚠️ <b>Risk:</b> Slipping habits or recurring friction points\n"
    "• 🎯 <b>Action:</b> One concrete micro-action for tomorrow\n\n"
    "📊 <b>Sleek Visual Dashboard</b>\n"
    "Your check-in summary now features clean percentage indicators and a dedicated <b>Daily Focus (Top 3 To-Dos)</b> breakdown.\n\n"
    "───────────────\n"
    "💡 <i>Try it out on your next check-in at 9 PM, or type /checkin anytime to see the new look!</i>"
)

async def main():
    logger.info("📡 Fetching active users from Firestore...")
    users = firestore_service.get_all_users()
    logger.info(f"👥 Found {len(users)} registered user(s).")
    
    if not users:
        logger.warning("No users found to broadcast to.")
        return
    
    bot = Bot(token=settings.telegram_bot_token)
    
    success_count = 0
    failed_count = 0
    
    for user in users:
        user_id = str(user.user_id)
        try:
            logger.info(f"📤 Sending changelog to user {user_id}...")
            await bot.send_message(
                chat_id=user_id,
                text=CHANGELOG_MESSAGE,
                parse_mode="HTML"
            )
            success_count += 1
            await asyncio.sleep(0.05)  # Avoid Telegram rate limits
        except Forbidden:
            logger.warning(f"⚠️ User {user_id} has blocked or not started the bot.")
            failed_count += 1
        except TelegramError as e:
            logger.error(f"❌ Failed to send to {user_id}: {e}")
            failed_count += 1
        except Exception as e:
            logger.error(f"❌ Unexpected error for {user_id}: {e}")
            failed_count += 1
            
    logger.info("=" * 50)
    logger.info(f"🎉 Broadcast Summary: {success_count} succeeded, {failed_count} failed out of {len(users)} total.")
    logger.info("=" * 50)

if __name__ == "__main__":
    asyncio.run(main())
