"""
Start Telegram Bot in Polling Mode for Local Testing
====================================================

This script starts the Telegram bot in polling mode, allowing you to test
Phase 3E features via Telegram without setting up webhooks.

Usage:
    python3 start_polling_local.py

The bot will listen for messages from Telegram and respond in real-time.
Press Ctrl+C to stop.
"""

import asyncio
import logging
import sys
import os

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.bot.telegram_bot import bot_manager
from src.bot.conversation import create_checkin_conversation_handler
from src.config import settings

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


async def main():
    """Start bot in polling mode."""
    print("="*70)
    print("  TELEGRAM BOT - POLLING MODE")
    print("  Phase 3E Local Testing")
    print("="*70)
    print(f"\n✅ Bot Token: {settings.telegram_bot_token[:20]}...")
    print(f"✅ Project: {settings.gcp_project_id}")
    print(f"✅ Environment: {settings.environment}\n")
    
    try:
        # Register conversation handler
        logger.info("📝 Registering conversation handler...")
        conversation_handler = create_checkin_conversation_handler()
        bot_manager.register_conversation_handler(conversation_handler)
        
        # Get application
        application = bot_manager.get_application()
        
        # Remove webhook (if any)
        logger.info("🔄 Removing webhook...")
        await bot_manager.delete_webhook()
        
        # Initialize application
        logger.info("🚀 Initializing bot application...")
        await application.initialize()
        await application.start()
        
        # Start polling
        logger.info("🔄 Starting polling mode...")
        await application.updater.start_polling(drop_pending_updates=True)
        
        print("\n" + "="*70)
        print("  ✅ BOT IS NOW ACTIVE!")
        print("="*70)
        print("\n📱 Open Telegram and send commands to your bot:\n")
        print("   Phase 3E Commands to Test:")
        print("   • /quickcheckin - Quick check-in mode")
        print("   • What's my average compliance? - Query agent")
        print("   • /weekly - Last 7 days stats")
        print("   • /monthly - Last 30 days stats")
        print("   • /yearly - Year-to-date stats\n")
        print("   Other Commands:")
        print("   • /status - Current status")
        print("   • /help - All commands")
        print("   • /checkin - Full check-in\n")
        print("="*70)
        print("  Press Ctrl+C to stop the bot")
        print("="*70)
        print()
        
        # Keep running
        while True:
            await asyncio.sleep(1)
            
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping bot...")
        await application.stop()
        await application.shutdown()
        print("✅ Bot stopped successfully")
    except Exception as e:
        logger.error(f"❌ Error: {e}", exc_info=True)
        print(f"\n❌ Error: {e}")
        print("\nCheck logs for details")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n✅ Shutdown complete")
