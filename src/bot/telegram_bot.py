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

from telegram import Update, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackContext,
    ContextTypes,
    CallbackQueryHandler,
    MessageHandler,
    filters
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
        - /start: Welcome message, create user profile (Phase 3: Enhanced onboarding)
        - /help: Show available commands
        - /status: Show streak and recent compliance
        - /mode: Change constitution mode
        
        Phase 3A: Inline keyboard callback handlers for onboarding
        Note: /checkin conversation handler registered separately
        """
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        self.application.add_handler(CommandHandler("mode", self.mode_command))
        
        # Phase 3A: Streak shield command
        self.application.add_handler(CommandHandler("use_shield", self.use_shield_command))
        
        # Phase 3B: Accountability partner commands
        self.application.add_handler(CommandHandler("set_partner", self.set_partner_command))
        self.application.add_handler(CommandHandler("unlink_partner", self.unlink_partner_command))
        
        # Phase 3A: Callback query handlers for inline keyboard buttons
        self.application.add_handler(CallbackQueryHandler(self.mode_selection_callback, pattern="^mode_"))
        self.application.add_handler(CallbackQueryHandler(self.timezone_confirmation_callback, pattern="^tz_"))
        
        # Phase 3B: Partner request callbacks
        self.application.add_handler(CallbackQueryHandler(self.accept_partner_callback, pattern="^accept_partner:"))
        self.application.add_handler(CallbackQueryHandler(self.decline_partner_callback, pattern="^decline_partner:"))
        
        # Phase 3B: General message handler for emotional support and queries
        # This catches all non-command text messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_general_message)
        )
        
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
        Handle /start command - Phase 3A Enhanced Onboarding.
        
        Flow for new users:
        1. Welcome message + bot purpose explanation
        2. Tier 1 non-negotiables explanation
        3. Mode selection (inline keyboard)
        4. Timezone confirmation
        5. First check-in prompt
        
        Returning users: Quick welcome with stats
        
        Args:
            update: Incoming update from Telegram
            context: Bot context (state, user data)
        """
        user = update.effective_user
        user_id = str(user.id)
        
        # Check if user exists
        existing_user = firestore_service.get_user(user_id)
        
        if existing_user:
            # ===== Returning User =====
            await update.message.reply_text(
                f"Welcome back, {existing_user.name}! 👋\n\n"
                f"🔥 Current streak: {existing_user.streaks.current_streak} days\n"
                f"🏆 Personal best: {existing_user.streaks.longest_streak} days\n"
                f"🎯 Mode: {existing_user.constitution_mode.title()}\n"
                f"🛡️ Streak shields: {existing_user.streak_shields.available}/{existing_user.streak_shields.total}\n\n"
                f"Ready to check in? Use /checkin\n"
                f"Need help? Use /help"
            )
        else:
            # ===== New User - Phase 3A Onboarding =====
            
            # Step 1: Welcome + Purpose
            welcome_message = (
                f"🎯 **Welcome to Your Constitution Accountability Agent!**\n\n"
                f"Hi {user.first_name}! I'm here to help you build unbreakable discipline "
                f"through daily accountability.\n\n"
                f"**What I do for you:**\n"
                f"✅ Daily check-ins to track your progress\n"
                f"✅ Smart reminders (9 PM, 9:30 PM, 10 PM)\n"
                f"✅ Personalized AI feedback on your performance\n"
                f"✅ Pattern detection & proactive interventions\n"
                f"✅ Streak tracking with protection shields\n"
                f"✅ Gamification & achievements\n\n"
                f"**📋 Your Tier 1 Non-Negotiables:**\n\n"
                f"These are your *daily foundation* - the 5 non-negotiables:\n\n"
                f"1️⃣ **💤 Sleep:** 7+ hours of quality sleep\n"
                f"2️⃣ **💪 Training:** Workout or scheduled rest day\n"
                f"3️⃣ **🧠 Deep Work:** 2+ hours of focused work\n"
                f"4️⃣ **🚫 Zero Porn:** Absolute rule, no exceptions\n"
                f"5️⃣ **🛡️ Boundaries:** No toxic interactions\n\n"
                f"Every day, I'll ask you about these 5 items + a few questions "
                f"to calculate your compliance score.\n\n"
                f"Let's personalize your experience..."
            )
            
            await update.message.reply_text(welcome_message)
            
            # Step 2: Mode Selection with Inline Keyboard
            mode_message = (
                f"🎯 **Choose Your Mode:**\n\n"
                f"**Optimization Mode** (Beast Mode)\n"
                f"• Training: 6x/week, one rest day\n"
                f"• Deep work: 2+ hours daily\n"
                f"• For aggressive growth phases\n\n"
                f"**Maintenance Mode** (Steady State)\n"
                f"• Training: 4x/week, flexible schedule\n"
                f"• Deep work: 2+ hours daily\n"
                f"• For sustainable consistency\n\n"
                f"**Survival Mode** (Crisis)\n"
                f"• Training: 3x/week minimum\n"
                f"• Deep work: 1+ hour daily\n"
                f"• For recovery or difficult life phases\n\n"
                f"Which mode are you in right now?"
            )
            
            keyboard = [
                [InlineKeyboardButton("🚀 Optimization", callback_data="mode_optimization")],
                [InlineKeyboardButton("⚖️ Maintenance", callback_data="mode_maintenance")],
                [InlineKeyboardButton("🛡️ Survival", callback_data="mode_survival")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(mode_message, reply_markup=reply_markup)
        
        logger.info(f"✅ /start command from {user_id} ({user.first_name})")
    
    async def mode_selection_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle mode selection during onboarding (Phase 3A).
        
        Callback from inline keyboard buttons in start_command.
        Creates user profile with selected mode, then confirms timezone.
        
        Args:
            update: Callback query update
            context: Bot context
        """
        query = update.callback_query
        await query.answer()  # Acknowledge button press
        
        user = update.effective_user
        user_id = str(user.id)
        
        # Extract mode from callback_data (e.g., "mode_optimization" → "optimization")
        selected_mode = query.data.replace("mode_", "")
        
        # Create user profile with selected mode
        new_user = User(
            user_id=user_id,
            telegram_id=user.id,
            telegram_username=user.username,
            name=user.first_name or "User",
            timezone="Asia/Kolkata",  # Default, will confirm next
            constitution_mode=selected_mode
        )
        
        firestore_service.create_user(new_user)
        
        # Confirm mode selection
        mode_emojis = {
            "optimization": "🚀",
            "maintenance": "⚖️",
            "survival": "🛡️"
        }
        
        await query.edit_message_text(
            f"✅ **{mode_emojis[selected_mode]} {selected_mode.title()} Mode Selected!**\n\n"
            f"Great choice. I've set your constitution to {selected_mode} mode.\n"
            f"You can change this anytime with /mode"
        )
        
        # Step 3: Timezone Confirmation
        timezone_message = (
            f"🌍 **Timezone Confirmation**\n\n"
            f"I've set your timezone to **Asia/Kolkata (IST)**.\n\n"
            f"Your daily reminders will be sent at:\n"
            f"• 1st reminder: 9:00 PM IST\n"
            f"• 2nd reminder: 9:30 PM IST\n"
            f"• 3rd reminder: 10:00 PM IST\n\n"
            f"Is this correct?"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, IST is correct", callback_data="tz_confirm")],
            [InlineKeyboardButton("🌎 No, I'm in another timezone", callback_data="tz_change")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user.id,
            text=timezone_message,
            reply_markup=reply_markup
        )
        
        logger.info(f"✅ User {user_id} selected mode: {selected_mode}")
    
    async def timezone_confirmation_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle timezone confirmation during onboarding (Phase 3A).
        
        Final step: Confirms timezone and prompts first check-in.
        
        Args:
            update: Callback query update
            context: Bot context
        """
        query = update.callback_query
        await query.answer()
        
        user = update.effective_user
        user_id = str(user.id)
        
        if query.data == "tz_confirm":
            # Timezone confirmed
            await query.edit_message_text(
                f"✅ **Timezone Confirmed!**\n\n"
                f"Perfect. You're all set for reminders at 9 PM IST daily."
            )
            
            # Step 4: Streak Mechanics Explanation
            streak_message = (
                f"🔥 **How Streaks Work:**\n\n"
                f"• **Check in daily** to build your streak\n"
                f"• **48-hour grace period:** Miss a day? You have 48 hours to recover\n"
                f"• **Streak shields:** You get 3 shields per month to protect your streak\n"
                f"• **Achievements:** Unlock badges at 7, 30, 90, 180, 365 days\n\n"
                f"Your longest streak becomes your permanent record - it never decreases!"
            )
            
            await context.bot.send_message(
                chat_id=user.id,
                text=streak_message
            )
            
            # Step 5: First Check-In Prompt
            first_checkin_message = (
                f"🎯 **You're Ready to Start!**\n\n"
                f"Welcome to your accountability journey. I'll remind you daily at 9 PM,  "
                f"but you can check in anytime.\n\n"
                f"**Your first check-in is available now!**\n\n"
                f"Use /checkin to complete your first check-in and start building your streak.\n\n"
                f"**Quick Commands:**\n"
                f"/checkin - Start daily check-in\n"
                f"/status - View your stats\n"
                f"/help - Show all commands\n\n"
                f"Let's build something great together! 💪"
            )
            
            await context.bot.send_message(
                chat_id=user.id,
                text=first_checkin_message
            )
            
        else:  # tz_change
            # User wants to change timezone (Phase 3 future enhancement)
            await query.edit_message_text(
                f"🌍 **Custom Timezone Support**\n\n"
                f"Custom timezone support is coming soon! For now, your reminders "
                f"will be sent at 9 PM IST.\n\n"
                f"You can still check in anytime using /checkin - your check-in will "
                f"count for the correct day based on your actual timezone.\n\n"
                f"Ready to start? Use /checkin"
            )
        
        logger.info(f"✅ Onboarding complete for user {user_id}")
    
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
            "<b>📋 Available Commands:</b>\n\n"
            "/start - Welcome message & setup\n"
            "/checkin - Start daily check-in (4 questions)\n"
            "/status - View streak, compliance, and recent stats\n"
            "/mode - Change constitution mode (optimization/maintenance/survival)\n"
            "/use_shield - Use a streak shield to protect your streak\n"
            "/help - Show this help message\n\n"
            "<b>👥 Accountability Partners (Phase 3B):</b>\n"
            "/set_partner @username - Link an accountability partner\n"
            "/unlink_partner - Remove your accountability partner\n\n"
            "<b>💭 Emotional Support (Phase 3B):</b>\n"
            "Send a message describing how you're feeling:\n"
            "• 'I'm feeling lonely tonight'\n"
            "• 'Having urges right now'\n"
            "• 'Feeling stressed about work'\n\n"
            "<b>🎯 How Check-Ins Work:</b>\n"
            "1. You'll be asked 4 questions\n"
            "2. Answer about your Tier 1 non-negotiables\n"
            "3. I'll calculate your compliance score\n"
            "4. Your streak updates automatically\n"
            "5. You get immediate feedback\n\n"
            "<b>⏰ Timing:</b>\n"
            "• Check-ins scheduled at 9 PM IST\n"
            "• You can check in anytime with /checkin\n"
            "• One check-in per day maximum\n"
            "• Streak continues if you check in within 48 hours\n\n"
            "<b>🔥 Streak Rules:</b>\n"
            "• Increments: Check in within 48 hours of last check-in\n"
            "• Resets: Gap exceeds 48 hours (2+ days)\n"
            "• Longest streak never decreases (historical record)\n\n"
            "Need support? You've got this! 💪"
        )
        
        await update.message.reply_text(help_text, parse_mode='HTML')
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
        
        # Phase 3A: Streak shields status
        shields_display = "🛡️" * user.streak_shields.available + "⚪" * (user.streak_shields.total - user.streak_shields.available)
        
        status_text = (
            f"**📊 Your Status**\n\n"
            f"{streak_emoji} **Streak:** {user.streaks.current_streak} days\n"
            f"🏆 **Personal Best:** {user.streaks.longest_streak} days\n"
            f"📈 **Total Check-ins:** {user.streaks.total_checkins}\n"
            f"🎯 **Mode:** {user.constitution_mode.title()}\n"
            f"🛡️ **Streak Shields:** {shields_display} ({user.streak_shields.available}/{user.streak_shields.total})\n\n"
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
    
    async def use_shield_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /use_shield command (Phase 3A Streak Protection).
        
        Allows user to use a streak shield to prevent streak break.
        
        Use Cases:
        - User about to miss check-in (emergency, travel, sickness)
        - User already missed check-in and wants to protect streak
        
        Rules:
        - 3 shields per 30 days
        - Shields reset monthly
        - Can only use if shields available
        """
        user_id = str(update.effective_user.id)
        user = firestore_service.get_user(user_id)
        
        if not user:
            await update.message.reply_text(
                "❌ User not found. Please use /start first."
            )
            return
        
        # Check if shields available
        if user.streak_shields.available <= 0:
            await update.message.reply_text(
                f"❌ **No Streak Shields Available**\n\n"
                f"You've used all {user.streak_shields.total} shields this month.\n"
                f"Shields reset every 30 days.\n\n"
                f"**Last reset:** {user.streak_shields.last_reset or 'Never'}\n\n"
                f"💪 The best protection is consistency! Try to check in daily."
            )
            return
        
        # Check if user actually needs a shield (hasn't checked in today)
        from src.utils.timezone_utils import get_checkin_date
        from src.utils.streak import calculate_days_without_checkin
        
        checkin_date = get_checkin_date()
        checked_in_today = firestore_service.checkin_exists(user_id, checkin_date)
        
        if checked_in_today:
            await update.message.reply_text(
                f"✅ **Shield Not Needed!**\n\n"
                f"You've already checked in for {checkin_date}.\n"
                f"Your streak is safe! 🔥\n\n"
                f"🛡️ Shields remaining: {user.streak_shields.available}/{user.streak_shields.total}\n\n"
                f"Save your shields for emergencies."
            )
            return
        
        # Calculate days since last check-in
        days_without = calculate_days_without_checkin(user.streaks.last_checkin_date)
        
        if days_without == 0:
            # User already checked in (shouldn't happen, but handle it)
            await update.message.reply_text(
                "✅ You've already checked in! No shield needed."
            )
            return
        
        # Use shield
        success = firestore_service.use_streak_shield(user_id)
        
        if success:
            # Get updated user data
            updated_user = firestore_service.get_user(user_id)
            
            await update.message.reply_text(
                f"🛡️ **Streak Shield Activated!**\n\n"
                f"Your {user.streaks.current_streak}-day streak is protected.\n\n"
                f"**Shields remaining:** {updated_user.streak_shields.available}/{updated_user.streak_shields.total}\n\n"
                f"⚠️ **Important:** Shields are for emergencies only!\n"
                f"Using too many shields defeats the purpose of daily accountability.\n\n"
                f"Get back on track tomorrow with /checkin! 💪"
            )
            
            logger.info(f"✅ User {user_id} used streak shield ({updated_user.streak_shields.available} remaining)")
        else:
            await update.message.reply_text(
                f"❌ **Failed to use shield**\n\n"
                f"Something went wrong. Please try again or contact support."
            )
            logger.error(f"❌ Failed to use streak shield for {user_id}")
    
    # ===== Phase 3B: Accountability Partner Commands =====
    
    async def set_partner_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /set_partner @username command (Phase 3B).
        
        Allows user to request accountability partnership with another user.
        
        Flow:
        1. User A sends /set_partner @UserB
        2. Bot searches for User B by telegram username
        3. Bot sends invite to User B with Accept/Decline buttons
        4. User B clicks button
        5. If accepted: Both users linked bidirectionally
        
        Why Bidirectional?
        - Partner relationships are mutual
        - Both users should consent
        - Both users get notified if either ghosts
        """
        user_id = str(update.effective_user.id)
        user = firestore_service.get_user(user_id)
        
        if not user:
            await update.message.reply_text(
                "❌ User not found. Please use /start first."
            )
            return
        
        # Parse @username from message
        if not context.args or not context.args[0].startswith('@'):
            await update.message.reply_text(
                "❌ **Invalid usage**\n\n"
                "Format: /set_partner @username\n\n"
                "Example: /set_partner @john_doe"
            )
            return
        
        partner_username = context.args[0][1:]  # Remove @ symbol
        
        # Search for partner by telegram username
        partner = firestore_service.get_user_by_telegram_username(partner_username)
        
        if not partner:
            await update.message.reply_text(
                f"❌ **User not found**\n\n"
                f"User @{partner_username} hasn't started using the bot yet.\n\n"
                "They need to send /start first!"
            )
            return
        
        # Check if trying to partner with self
        if partner.user_id == user_id:
            await update.message.reply_text(
                "❌ You can't be your own accountability partner!"
            )
            return
        
        # Send invite to partner with inline buttons
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [
                InlineKeyboardButton("✅ Accept", callback_data=f"accept_partner:{user_id}"),
                InlineKeyboardButton("❌ Decline", callback_data=f"decline_partner:{user_id}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=partner.telegram_id,
            text=(
                f"👥 **Accountability Partner Request**\n\n"
                f"{user.name} wants to be your accountability partner.\n\n"
                f"**What this means:**\n"
                f"• You'll be notified if they ghost for 5+ days\n"
                f"• They'll be notified if you ghost for 5+ days\n"
                f"• Mutual support and motivation\n\n"
                f"Accept this request?"
            ),
            reply_markup=reply_markup
        )
        
        await update.message.reply_text(
            f"✅ **Partner request sent to @{partner_username}!**\n\n"
            f"Waiting for them to accept..."
        )
        
        logger.info(f"✅ Partner request sent: {user_id} → {partner.user_id}")
    
    async def accept_partner_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle partner request acceptance (Phase 3B).
        
        Callback data format: "accept_partner:<requester_user_id>"
        """
        query = update.callback_query
        await query.answer()
        
        # Parse requester user_id from callback data
        requester_user_id = query.data.split(':')[1]
        accepter_user_id = str(query.from_user.id)
        
        # Get both users
        requester = firestore_service.get_user(requester_user_id)
        accepter = firestore_service.get_user(accepter_user_id)
        
        if not requester or not accepter:
            await query.edit_message_text(
                "❌ **Error:** One or both users not found."
            )
            return
        
        # Link partners bidirectionally
        firestore_service.set_accountability_partner(
            user_id=requester_user_id,
            partner_id=accepter_user_id,
            partner_name=accepter.name
        )
        
        firestore_service.set_accountability_partner(
            user_id=accepter_user_id,
            partner_id=requester_user_id,
            partner_name=requester.name
        )
        
        # Notify both users
        await query.edit_message_text(
            f"✅ **Partnership Confirmed!**\n\n"
            f"You and {requester.name} are now accountability partners.\n\n"
            f"You'll be notified if they ghost for 5+ days, and vice versa."
        )
        
        await context.bot.send_message(
            chat_id=requester.telegram_id,
            text=(
                f"✅ **Partnership Confirmed!**\n\n"
                f"{accepter.name} accepted your request!\n\n"
                f"You're now accountability partners. 🤝"
            )
        )
        
        logger.info(f"✅ Partnership confirmed: {requester_user_id} ↔️ {accepter_user_id}")
    
    async def decline_partner_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle partner request decline (Phase 3B).
        
        Callback data format: "decline_partner:<requester_user_id>"
        """
        query = update.callback_query
        await query.answer()
        
        requester_user_id = query.data.split(':')[1]
        decliner = firestore_service.get_user(str(query.from_user.id))
        requester = firestore_service.get_user(requester_user_id)
        
        if not requester or not decliner:
            await query.edit_message_text(
                "❌ **Error:** User not found."
            )
            return
        
        await query.edit_message_text(
            "❌ **Partnership declined.**"
        )
        
        await context.bot.send_message(
            chat_id=requester.telegram_id,
            text=f"❌ {decliner.name} declined your partnership request."
        )
        
        logger.info(f"❌ Partnership declined: {requester_user_id} ← {decliner.user_id}")
    
    async def unlink_partner_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /unlink_partner command (Phase 3B).
        
        Allows user to remove their accountability partner.
        Unlinks both users bidirectionally.
        """
        user_id = str(update.effective_user.id)
        user = firestore_service.get_user(user_id)
        
        if not user:
            await update.message.reply_text(
                "❌ User not found. Please use /start first."
            )
            return
        
        if not user.accountability_partner_id:
            await update.message.reply_text(
                "❌ You don't have an accountability partner."
            )
            return
        
        partner = firestore_service.get_user(user.accountability_partner_id)
        
        if not partner:
            # Partner user doesn't exist anymore (deleted account?)
            # Just unlink on this side
            firestore_service.set_accountability_partner(user_id, None, None)
            await update.message.reply_text(
                "✅ **Partnership removed.**"
            )
            return
        
        # Unlink bidirectionally
        firestore_service.set_accountability_partner(user_id, None, None)
        firestore_service.set_accountability_partner(partner.user_id, None, None)
        
        await update.message.reply_text(
            f"✅ **Partnership with {partner.name} removed.**"
        )
        
        await context.bot.send_message(
            chat_id=partner.telegram_id,
            text=f"👥 {user.name} has removed you as their accountability partner."
        )
        
        logger.info(f"✅ Partnership unlinked: {user_id} ↔️ {partner.user_id}")
    
    # ===== Phase 3B: General Message Handler =====
    
    async def handle_general_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle general text messages (non-commands) - Phase 3B.
        
        **Flow:**
        1. Use supervisor to classify intent (emotional, query, checkin)
        2. Route to appropriate agent:
           - emotional → Emotional Support Agent
           - query → Query handler (future)
           - checkin → Suggest /checkin command
        
        **Why This Handler?**
        Users don't always use commands. They might say:
        - "I'm feeling lonely" (emotional)
        - "What's my streak?" (query)
        - "Ready to check in" (checkin intent)
        
        This handler intelligently routes these messages.
        """
        user_id = str(update.effective_user.id)
        message_text = update.message.text
        
        logger.info(f"📩 General message from {user_id}: '{message_text[:50]}...'")
        
        try:
            # Import agents (avoid circular imports)
            from src.agents.supervisor import SupervisorAgent
            from src.agents.emotional_agent import get_emotional_agent
            from src.agents.state import create_initial_state
            
            # Create supervisor
            supervisor = SupervisorAgent(project_id=settings.gcp_project_id)
            
            # Create initial state
            state = create_initial_state(
                user_id=user_id,
                message=message_text,
                message_id=update.message.message_id,
                username=update.effective_user.username
            )
            
            # Classify intent
            state = await supervisor.classify_intent(state)
            intent = state.get("intent", "query")
            
            logger.info(f"🎯 Classified intent: {intent}")
            
            # Route based on intent
            if intent == "emotional":
                # Emotional support
                emotional_agent = get_emotional_agent()
                state = await emotional_agent.process(state)
                
                response = state.get("response", "I'm here to help. Could you tell me more?")
                await update.message.reply_text(response)
                
                logger.info(f"✅ Emotional support provided to {user_id}")
                
            elif intent == "checkin":
                # User wants to check in but didn't use command
                await update.message.reply_text(
                    "Ready to check in? Use the /checkin command to start!\n\n"
                    "Or just say /checkin and we'll begin your daily accountability check."
                )
                
            elif intent == "query":
                # User asking a question
                await update.message.reply_text(
                    "I can help with that! Here are some useful commands:\n\n"
                    "📊 /status - See your streak and stats\n"
                    "✅ /checkin - Do your daily check-in\n"
                    "❓ /help - See all available commands\n\n"
                    "What would you like to do?"
                )
                
            else:
                # Unknown intent (shouldn't happen, but handle gracefully)
                await update.message.reply_text(
                    "I'm not sure how to help with that. Try:\n\n"
                    "/help - See available commands\n"
                    "/checkin - Start your daily check-in"
                )
        
        except Exception as e:
            logger.error(f"❌ Error handling general message: {e}", exc_info=True)
            await update.message.reply_text(
                "Sorry, I encountered an error. Please try again or use /help for available commands."
            )


# ===== Singleton Instance =====
# Import this throughout the app: `from src.bot.telegram_bot import bot_manager`

bot_manager = TelegramBotManager(token=settings.telegram_bot_token)
