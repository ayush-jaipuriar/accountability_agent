"""
Telegram Bot Manager
===================

Initializes and manages the Telegram bot application.

Architecture:
- Application: Main bot instance (from python-telegram-bot)
- Handlers: Registered functions that respond to commands/messages
- Webhook: Telegram sends updates to our Cloud Run URL

Key Concepts:
- Async: All handlers are async functions (await keyword)
- Update: Incoming message/button press from Telegram
- Context: Bot state, user data, application reference
"""

from telegram import Update, Bot
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    ContextTypes
)
import logging

from src.config import settings
from src.services.firestore_service import firestore_service
from src.models.schemas import User, get_current_date_ist

logger = logging.getLogger(__name__)


class TelegramBotManager:
    """
    Manages Telegram bot lifecycle and command handlers.
    
    Responsibilities:
    - Initialize bot application
    - Register command handlers
    - Handle webhook setup
    - Provide bot instance for sending messages
    
    Usage:
        bot_manager = TelegramBotManager(token="YOUR_BOT_TOKEN")
        application = bot_manager.get_application()
    """
    
    def __init__(self, token: str):
        """
        Initialize Telegram bot.
        
        Args:
            token: Bot token from @BotFather
        """
        self.token = token
        self.application = Application.builder().token(token).build()
        self.bot: Bot = self.application.bot
        
        # Register handlers
        self._register_handlers()
        
        logger.info("✅ Telegram bot initialized")
    
    def _register_handlers(self) -> None:
        """
        Register all command handlers.
        
        Command handlers respond to:
        - /start: Welcome message, create user profile
        - /help: Show available commands
        - /status: Show streak and recent compliance
        - /mode: Change constitution mode
        
        Note: /checkin conversation handler registered separately
        """
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("mode", self.mode_command))
        
        logger.info("✅ Command handlers registered")
    
    def register_conversation_handler(self, conversation_handler) -> None:
        """
        Register check-in conversation handler.
        
        Called from main.py after conversation handler is created.
        
        Args:
            conversation_handler: ConversationHandler for check-ins
        """
        self.application.add_handler(conversation_handler)
        logger.info("✅ Conversation handler registered")
    
    def get_application(self) -> Application:
        """
        Get bot application instance.
        
        Returns:
            Application: python-telegram-bot Application
        """
        return self.application
    
    async def set_webhook(self, webhook_url: str) -> bool:
        """
        Set Telegram webhook URL.
        
        Tells Telegram where to send updates (messages, button presses).
        
        Args:
            webhook_url: Full URL to webhook endpoint (e.g., https://your-app.run.app/webhook/telegram)
            
        Returns:
            bool: True if webhook set successfully
        """
        try:
            await self.bot.set_webhook(url=webhook_url)
            logger.info(f"✅ Webhook set to: {webhook_url}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to set webhook: {e}")
            return False
    
    async def delete_webhook(self) -> bool:
        """
        Remove webhook (used for local development with polling).
        
        Returns:
            bool: True if webhook removed successfully
        """
        try:
            await self.bot.delete_webhook()
            logger.info("✅ Webhook removed")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete webhook: {e}")
            return False
    
    # ===== Command Handlers =====
    
    async def start_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /start command.
        
        Creates user profile if doesn't exist, sends welcome message.
        
        Args:
            update: Incoming update from Telegram
            context: Bot context (state, user data)
        """
        user = update.effective_user
        user_id = str(user.id)
        
        # Check if user exists
        existing_user = firestore_service.get_user(user_id)
        
        if existing_user:
            # User already exists
            await update.message.reply_text(
                f"Welcome back, {existing_user.name}! 👋\n\n"
                f"🔥 Current streak: {existing_user.streaks.current_streak} days\n"
                f"🎯 Mode: {existing_user.constitution_mode.title()}\n\n"
                f"Ready to check in? Use /checkin\n"
                f"Need help? Use /help"
            )
        else:
            # Create new user
            new_user = User(
                user_id=user_id,
                telegram_id=user.id,
                telegram_username=user.username,
                name=user.first_name or "User",
                timezone="Asia/Kolkata",
                constitution_mode="maintenance"
            )
            
            firestore_service.create_user(new_user)
            
            await update.message.reply_text(
                f"Welcome to your Constitution Accountability Agent! 🎯\n\n"
                f"I'm here to help you stay accountable to your constitution.\n\n"
                f"**What I do:**\n"
                f"• Daily check-ins at 9 PM IST\n"
                f"• Track your Tier 1 non-negotiables\n"
                f"• Calculate compliance scores\n"
                f"• Monitor your streak\n"
                f"• Detect patterns and intervene when needed\n\n"
                f"**Your Tier 1 Non-Negotiables:**\n"
                f"1. 💤 Sleep: 7+ hours\n"
                f"2. 💪 Training: 6x/week (4x in maintenance mode)\n"
                f"3. 🧠 Deep Work: 2+ hours\n"
                f"4. 🚫 Zero Porn: Absolute rule\n"
                f"5. 🛡️ Boundaries: No toxic interactions\n\n"
                f"**Commands:**\n"
                f"/checkin - Start daily check-in\n"
                f"/status - View your stats\n"
                f"/help - Show all commands\n\n"
                f"Let's build something great together! Ready to check in? Use /checkin"
            )
        
        logger.info(f"✅ /start command from {user_id} ({user.first_name})")
    
    async def help_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /help command.
        
        Shows available commands and usage info.
        """
        help_text = (
            "**📋 Available Commands:**\n\n"
            "/start - Welcome message & setup\n"
            "/checkin - Start daily check-in (4 questions)\n"
            "/status - View streak, compliance, and recent stats\n"
            "/mode - Change constitution mode (optimization/maintenance/survival)\n"
            "/help - Show this help message\n\n"
            "**🎯 How Check-Ins Work:**\n"
            "1. You'll be asked 4 questions\n"
            "2. Answer about your Tier 1 non-negotiables\n"
            "3. I'll calculate your compliance score\n"
            "4. Your streak updates automatically\n"
            "5. You get immediate feedback\n\n"
            "**⏰ Timing:**\n"
            "• Check-ins scheduled at 9 PM IST\n"
            "• You can check in anytime with /checkin\n"
            "• One check-in per day maximum\n"
            "• Streak continues if you check in within 48 hours\n\n"
            "**🔥 Streak Rules:**\n"
            "• Increments: Check in within 48 hours of last check-in\n"
            "• Resets: Gap exceeds 48 hours (2+ days)\n"
            "• Longest streak never decreases (historical record)\n\n"
            "Need support? You've got this! 💪"
        )
        
        await update.message.reply_text(help_text)
        logger.info(f"✅ /help command from {update.effective_user.id}")
    
    async def status_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /status command.
        
        Shows user's current streak, compliance, and recent performance.
        """
        user_id = str(update.effective_user.id)
        
        # Fetch user data
        user = firestore_service.get_user(user_id)
        
        if not user:
            await update.message.reply_text(
                "❌ User not found. Please use /start first."
            )
            return
        
        # Fetch recent check-ins
        recent_checkins = firestore_service.get_recent_checkins(user_id, days=7)
        
        # Calculate average compliance
        if recent_checkins:
            avg_compliance = sum(c.compliance_score for c in recent_checkins) / len(recent_checkins)
        else:
            avg_compliance = 0.0
        
        # Check if checked in today
        today = get_current_date_ist()
        checked_in_today = firestore_service.checkin_exists(user_id, today)
        
        # Format streak emoji
        from src.utils.streak import get_streak_emoji
        streak_emoji = get_streak_emoji(user.streaks.current_streak)
        
        status_text = (
            f"**📊 Your Status**\n\n"
            f"{streak_emoji} **Streak:** {user.streaks.current_streak} days\n"
            f"🏆 **Personal Best:** {user.streaks.longest_streak} days\n"
            f"📈 **Total Check-ins:** {user.streaks.total_checkins}\n"
            f"🎯 **Mode:** {user.constitution_mode.title()}\n\n"
            f"**📅 Last 7 Days:**\n"
            f"• Check-ins completed: {len(recent_checkins)}/7\n"
            f"• Average compliance: {avg_compliance:.1f}%\n\n"
            f"**✅ Today:**\n"
        )
        
        if checked_in_today:
            status_text += "• ✅ Check-in complete!\n"
        else:
            status_text += "• ⏳ Check-in pending (use /checkin)\n"
        
        # Add encouragement based on streak
        if user.streaks.current_streak >= 30:
            status_text += "\n🚀 You're on fire! Keep it up!"
        elif user.streaks.current_streak >= 7:
            status_text += "\n💪 Solid consistency! You're building something real."
        elif user.streaks.current_streak > 0:
            status_text += "\n🔥 Great start! Keep the momentum going."
        else:
            status_text += "\n🎯 Ready to start a new streak? Use /checkin"
        
        await update.message.reply_text(status_text)
        logger.info(f"✅ /status command from {user_id}")
    
    async def mode_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /mode command.
        
        Shows current mode and allows switching.
        """
        user_id = str(update.effective_user.id)
        user = firestore_service.get_user(user_id)
        
        if not user:
            await update.message.reply_text(
                "❌ User not found. Please use /start first."
            )
            return
        
        mode_info = (
            f"**🎯 Constitution Modes**\n\n"
            f"**Current Mode:** {user.constitution_mode.title()} ✅\n\n"
            f"**📈 Optimization Mode:**\n"
            f"• All systems firing - aggressive growth\n"
            f"• 6x/week training, 3+ hours deep work\n"
            f"• Target: 90%+ compliance\n\n"
            f"**⚖️ Maintenance Mode:**\n"
            f"• Sustaining progress, recovery phase\n"
            f"• 4x/week training, 2+ hours deep work\n"
            f"• Target: 80%+ compliance\n\n"
            f"**🛡️ Survival Mode:**\n"
            f"• Crisis mode - protect bare minimums\n"
            f"• 3x/week training, 1+ hour deep work\n"
            f"• Target: 60%+ compliance\n\n"
            f"To change mode, use:\n"
            f"/mode optimization\n"
            f"/mode maintenance\n"
            f"/mode survival"
        )
        
        await update.message.reply_text(mode_info)
        logger.info(f"✅ /mode command from {user_id}")


# ===== Singleton Instance =====
# Import this throughout the app: `from src.bot.telegram_bot import bot_manager`

bot_manager = TelegramBotManager(token=settings.telegram_bot_token)
