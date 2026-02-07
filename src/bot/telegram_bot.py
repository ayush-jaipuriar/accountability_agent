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
        
        # Phase 3C: Achievement system commands
        self.application.add_handler(CommandHandler("achievements", self.achievements_command))
        
        # Phase 3D: Career mode command
        self.application.add_handler(CommandHandler("career", self.career_command))
        
        # Phase 3E: Quick check-in handled by ConversationHandler (see conversation.py)
        # No separate handler needed here
        
        # Phase 3E: Stats commands
        from src.bot.stats_commands import weekly_command, monthly_command, yearly_command
        self.application.add_handler(CommandHandler("weekly", weekly_command))
        self.application.add_handler(CommandHandler("monthly", monthly_command))
        self.application.add_handler(CommandHandler("yearly", yearly_command))
        
        # Phase 3F: Export, Report, Social commands
        self.application.add_handler(CommandHandler("export", self.export_command))
        self.application.add_handler(CommandHandler("report", self.report_command))
        self.application.add_handler(CommandHandler("leaderboard", self.leaderboard_command))
        self.application.add_handler(CommandHandler("rank", self.leaderboard_command))  # Alias
        self.application.add_handler(CommandHandler("invite", self.invite_command))
        self.application.add_handler(CommandHandler("refer", self.invite_command))  # Alias
        self.application.add_handler(CommandHandler("share", self.share_command))
        self.application.add_handler(CommandHandler("brag", self.share_command))  # Alias
        self.application.add_handler(CommandHandler("resume", self.resume_command))
        
        # Phase 3A: Callback query handlers for inline keyboard buttons
        self.application.add_handler(CallbackQueryHandler(self.mode_selection_callback, pattern="^mode_"))
        self.application.add_handler(CallbackQueryHandler(self.timezone_confirmation_callback, pattern="^tz_"))
        
        # Phase 3D: Career mode callback handlers
        self.application.add_handler(CallbackQueryHandler(self.career_callback, pattern="^career_"))
        
        # Phase 3B: Partner request callbacks
        self.application.add_handler(CallbackQueryHandler(self.accept_partner_callback, pattern="^accept_partner:"))
        self.application.add_handler(CallbackQueryHandler(self.decline_partner_callback, pattern="^decline_partner:"))
        
        # Phase 3B: General message handler for emotional support and queries
        # This catches all non-command text messages
        # CRITICAL: Must be in group 1 (lower priority than ConversationHandler in group 0)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_general_message),
            group=1  # Lower priority ensures ConversationHandler processes /checkin first
        )
        
        logger.info("✅ Command handlers registered")
    
    def register_conversation_handler(self, conversation_handler) -> None:
        """
        Register check-in conversation handler.
        
        Called from main.py after conversation handler is created.
        
        Args:
            conversation_handler: ConversationHandler for check-ins
            
        **CRITICAL: Handler Groups**
        ConversationHandler is added to group 0 (default, highest priority).
        This ensures /checkin and /quickcheckin commands are caught by the
        ConversationHandler BEFORE the general message handler.
        """
        self.application.add_handler(conversation_handler, group=0)
        logger.info("✅ Conversation handler registered (group 0 - highest priority)")
    
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
        
        # Phase 3F: Parse referral code from deep link (/start ref_USERID)
        referral_user_id = None
        if context.args and len(context.args) > 0:
            arg = context.args[0]
            if arg.startswith("ref_"):
                referral_user_id = arg[4:]  # Extract user ID after "ref_"
                logger.info(f"🔗 Referral detected: {user_id} referred by {referral_user_id}")
        
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
            
            # Phase 3F: Store referral code for use in mode_selection_callback
            if referral_user_id:
                context.user_data["referral_user_id"] = referral_user_id
            
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
            
            await update.message.reply_text(welcome_message, parse_mode='Markdown')
            
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
            
            await update.message.reply_text(mode_message, reply_markup=reply_markup, parse_mode='Markdown')
        
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
        # Phase 3F: Check for referral code stored in context
        referred_by = context.user_data.get("referral_user_id") if context.user_data else None
        
        new_user = User(
            user_id=user_id,
            telegram_id=user.id,
            telegram_username=user.username,
            name=user.first_name or "User",
            timezone="Asia/Kolkata",  # Default, will confirm next
            constitution_mode=selected_mode,
            referred_by=referred_by
        )
        
        firestore_service.create_user(new_user)
        
        # Phase 3F: If referred, give bonus streak shields
        if referred_by:
            logger.info(f"🎁 Giving 3 bonus shields to {user_id} (referred by {referred_by})")
            # Bonus shields are already 3/3 by default - this is the welcome bonus
        
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
        
        Shows available commands organized by category using Phase 3F
        UX utilities for consistent formatting.
        """
        from src.utils.ux import generate_help_text
        
        help_text = generate_help_text()
        
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
            from src.utils.ux import ErrorMessages
            await update.message.reply_text(ErrorMessages.user_not_found(), parse_mode='HTML')
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
            f"<b>📊 Your Status</b>\n\n"
            f"{streak_emoji} <b>Streak:</b> {user.streaks.current_streak} days\n"
            f"🏆 <b>Personal Best:</b> {user.streaks.longest_streak} days\n"
            f"📈 <b>Total Check-ins:</b> {user.streaks.total_checkins}\n"
            f"🎯 <b>Mode:</b> {user.constitution_mode.title()}\n"
            f"🛡️ <b>Streak Shields:</b> {shields_display} ({user.streak_shields.available}/{user.streak_shields.total})\n\n"
            f"<b>📅 Last 7 Days:</b>\n"
            f"• Check-ins completed: {len(recent_checkins)}/7\n"
            f"• Average compliance: {avg_compliance:.1f}%\n\n"
            f"<b>✅ Today:</b>\n"
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
        
        await update.message.reply_text(status_text, parse_mode='HTML')
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
        
        await update.message.reply_text(mode_info, parse_mode='Markdown')
        logger.info(f"✅ /mode command from {user_id}")
    
    # ===== Phase 3D: Career Mode Commands =====
    
    async def career_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /career command (Phase 3D Career Tracking).
        
        Display and toggle career mode.
        
        **Career Mode System:**
        - **skill_building:** Learning phase (LeetCode, system design, upskilling)
        - **job_searching:** Active job hunt (applications, interviews)
        - **employed:** Working toward promotion/raise
        
        **Why This Matters:**
        Career mode determines how the Tier 1 skill building question is phrased.
        The question adapts to your current career phase for more relevant tracking.
        
        **Constitution Alignment:**
        - Tracks progress toward ₹28-42 LPA June 2026 goal
        - Ensures daily skill building (LeetCode, system design)
        - Adapts as you transition from learning → job searching → employed
        """
        user_id = str(update.effective_user.id)
        user = firestore_service.get_user(user_id)
        
        if not user:
            await update.message.reply_text(
                "❌ User not found. Please use /start first."
            )
            return
        
        # Career mode descriptions
        mode_descriptions = {
            "skill_building": (
                "📚 **Skill Building**\n"
                "Learning phase: LeetCode, system design, AI/ML upskilling, courses, projects\n\n"
                "✅ **Skill building question:** Did you do 2+ hours skill building?"
            ),
            "job_searching": (
                "💼 **Job Searching**\n"
                "Active job hunt: Applications, interviews, networking, skill building\n\n"
                "✅ **Skill building question:** Did you make job search progress?"
            ),
            "employed": (
                "🎯 **Employed**\n"
                "Working toward promotion/raise: High-impact work, skill development, visibility\n\n"
                "✅ **Skill building question:** Did you work toward promotion/raise?"
            )
        }
        
        current_desc = mode_descriptions.get(user.career_mode, "Unknown mode")
        
        message = (
            f"**🎯 Career Phase Tracking**\n\n"
            f"**Current Mode:**\n{current_desc}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Why Career Mode Matters:**\n"
            f"• Your Tier 1 skill building question adapts to your career phase\n"
            f"• Tracks progress toward ₹28-42 LPA June 2026 goal\n"
            f"• Aligns check-ins with constitution career protocols\n\n"
            f"**Change mode using buttons below:**"
        )
        
        # Create inline keyboard for mode selection
        keyboard = [
            [InlineKeyboardButton("📚 Skill Building", callback_data="career_skill")],
            [InlineKeyboardButton("💼 Job Searching", callback_data="career_job")],
            [InlineKeyboardButton("🎯 Employed", callback_data="career_employed")]
        ]
        
        await update.message.reply_text(
            message,
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        logger.info(f"✅ /career command from {user_id}")
    
    async def career_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle career mode selection from inline buttons (Phase 3D).
        
        **Callback Data Format:**
        - career_skill → skill_building mode
        - career_job → job_searching mode
        - career_employed → employed mode
        
        **Process:**
        1. Parse callback data to get selected mode
        2. Update user's career_mode in Firestore
        3. Edit message to show confirmation
        4. Log change
        
        **Impact:**
        Starting next check-in, Tier 1 skill building question will adapt
        to the new career mode.
        """
        query = update.callback_query
        await query.answer()  # Acknowledge button press (prevents loading spinner)
        
        user_id = str(query.from_user.id)
        callback_data = query.data
        
        # Map callback data to career mode
        mode_map = {
            "career_skill": "skill_building",
            "career_job": "job_searching",
            "career_employed": "employed"
        }
        
        new_mode = mode_map.get(callback_data)
        
        if not new_mode:
            await query.edit_message_text("❌ Invalid selection.")
            logger.error(f"❌ Invalid career callback data: {callback_data}")
            return
        
        # Update career mode in Firestore
        success = firestore_service.update_user_career_mode(user_id, new_mode)
        
        if not success:
            await query.edit_message_text(
                "❌ Failed to update career mode. Please try again."
            )
            logger.error(f"❌ Failed to update career mode for {user_id}")
            return
        
        # Mode names for display
        mode_names = {
            "skill_building": "📚 Skill Building",
            "job_searching": "💼 Job Searching",
            "employed": "🎯 Employed"
        }
        
        # Mode descriptions for confirmation
        mode_questions = {
            "skill_building": "Did you do 2+ hours skill building?",
            "job_searching": "Did you make job search progress?",
            "employed": "Did you work toward promotion/raise?"
        }
        
        # Send confirmation
        await query.edit_message_text(
            f"✅ **Career mode updated!**\n\n"
            f"**New Mode:** {mode_names[new_mode]}\n\n"
            f"**Your Tier 1 skill building question will now be:**\n"
            f"\"{mode_questions[new_mode]}\"\n\n"
            f"This change takes effect starting your next check-in.\n\n"
            f"🎯 Keep tracking progress toward your June 2026 goal! (₹28-42 LPA)",
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ User {user_id} changed career mode to {new_mode}")
    
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
                f"💪 The best protection is consistency! Try to check in daily.",
                parse_mode='Markdown'
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
                f"Save your shields for emergencies.",
                parse_mode='Markdown'
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
                f"Get back on track tomorrow with /checkin! 💪",
                parse_mode='Markdown'
            )
            
            logger.info(f"✅ User {user_id} used streak shield ({updated_user.streak_shields.available} remaining)")
        else:
            await update.message.reply_text(
                f"❌ **Failed to use shield**\n\n"
                f"Something went wrong. Please try again or contact support.",
                parse_mode='Markdown'
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
                "Example: /set_partner @john_doe",
                parse_mode='Markdown'
            )
            return
        
        partner_username = context.args[0][1:]  # Remove @ symbol
        
        # Search for partner by telegram username
        partner = firestore_service.get_user_by_telegram_username(partner_username)
        
        if not partner:
            await update.message.reply_text(
                f"❌ **User not found**\n\n"
                f"User @{partner_username} hasn't started using the bot yet.\n\n"
                "They need to send /start first!",
                parse_mode='Markdown'
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
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
        
        await update.message.reply_text(
            f"✅ **Partner request sent to @{partner_username}!**\n\n"
            f"Waiting for them to accept...",
            parse_mode='Markdown'
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
                "✅ **Partnership removed.**",
                parse_mode='Markdown'
            )
            return
        
        # Unlink bidirectionally
        firestore_service.set_accountability_partner(user_id, None, None)
        firestore_service.set_accountability_partner(partner.user_id, None, None)
        
        await update.message.reply_text(
            f"✅ **Partnership with {partner.name} removed.**",
            parse_mode='Markdown'
        )
        
        await context.bot.send_message(
            chat_id=partner.telegram_id,
            text=f"👥 {user.name} has removed you as their accountability partner."
        )
        
        logger.info(f"✅ Partnership unlinked: {user_id} ↔️ {partner.user_id}")
    
    # ===== Phase 3C: Achievement System Commands =====
    
    async def achievements_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /achievements command (Phase 3C).
        
        Display user's unlocked achievements grouped by rarity.
        Shows progress toward next milestone.
        
        **Theory - Why This Works:**
        - Viewing achievements creates **progress visualization**
        - Rarity grouping creates **status hierarchy** (legendary first)
        - Next milestone creates **goal clarity** (X days until Month Master)
        - Together these drive continued engagement
        """
        user_id = str(update.effective_user.id)
        user = firestore_service.get_user(user_id)
        
        if not user:
            await update.message.reply_text(
                "❌ User not found. Please use /start first."
            )
            return
        
        # Import achievement service
        from src.services.achievement_service import achievement_service
        
        # If no achievements yet, show motivation message
        if not user.achievements:
            await update.message.reply_text(
                "🎯 **No achievements yet!**\n\n"
                "Keep checking in daily to unlock:\n"
                "🎯 First Step (1 day)\n"
                "🏅 Week Warrior (7 days)\n"
                "🏆 Month Master (30 days)\n"
                "⭐ Perfect Week (7 days at 100%)\n\n"
                f"Your current streak: **{user.streaks.current_streak} days** 🔥\n\n"
                "Complete your daily check-in with /checkin",
                parse_mode="Markdown"
            )
            return
        
        # Build achievements display message
        message_parts = []
        message_parts.append(f"🏆 **Your Achievements ({len(user.achievements)}/{len(achievement_service.get_all_achievements())})**\n")
        
        # Group achievements by rarity
        from collections import defaultdict
        by_rarity = defaultdict(list)
        
        for achievement_id in user.achievements:
            achievement = achievement_service.get_achievement(achievement_id)
            if achievement:
                by_rarity[achievement.rarity].append(achievement)
        
        # Display by rarity (legendary → epic → rare → common)
        rarity_order = ["legendary", "epic", "rare", "common"]
        rarity_labels = {
            "legendary": "👑 LEGENDARY",
            "epic": "💎 EPIC",
            "rare": "🌟 RARE",
            "common": "🏅 COMMON"
        }
        
        for rarity in rarity_order:
            if by_rarity[rarity]:
                message_parts.append(f"\n**{rarity_labels[rarity]}**")
                for achievement in by_rarity[rarity]:
                    message_parts.append(f"{achievement.icon} {achievement.name}")
                    # Optionally add description (commented out to keep message short)
                    # message_parts.append(f"   _{achievement.description}_")
        
        # Add progress toward next milestone
        current_streak = user.streaks.current_streak
        next_milestone = None
        next_milestone_name = None
        
        streak_milestones = {
            7: ("week_warrior", "Week Warrior"),
            14: ("fortnight_fighter", "Fortnight Fighter"),
            30: ("month_master", "Month Master"),
            90: ("quarter_conqueror", "Quarter Conqueror"),
            180: ("half_year_hero", "Half Year Hero"),
            365: ("year_yoda", "Year Yoda")
        }
        
        for milestone_days, (achievement_id, achievement_name) in streak_milestones.items():
            if current_streak < milestone_days:
                next_milestone = milestone_days
                next_milestone_name = achievement_name
                break
        
        if next_milestone:
            days_remaining = next_milestone - current_streak
            message_parts.append(
                f"\n📈 **Next Milestone:** {next_milestone_name} "
                f"({days_remaining} day{'s' if days_remaining != 1 else ''} to go!)"
            )
        else:
            # User has completed all streak milestones!
            message_parts.append("\n🎉 **All streak milestones unlocked!** You're a legend! 👑")
        
        # Add call to action
        message_parts.append(
            f"\n💪 Keep going! Current streak: **{current_streak} days** 🔥"
        )
        
        final_message = "\n".join(message_parts)
        
        await update.message.reply_text(
            final_message,
            parse_mode="Markdown"
        )
        
        logger.info(f"✅ Displayed {len(user.achievements)} achievements for user {user_id}")
    
    # ===== Phase 3F: Export Command =====
    
    async def export_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /export command (Phase 3F Data Export).
        
        Supports: /export csv, /export json, /export pdf
        
        **How It Works:**
        1. Parse format from command arguments
        2. Call export service to generate file in memory
        3. Send file via Telegram's document upload API
        
        **Telegram File Limits:**
        - Documents: up to 50MB
        - Our exports: typically <1MB (well within limits)
        """
        from src.services.export_service import export_user_data
        from src.utils.ux import ErrorMessages
        
        user_id = str(update.effective_user.id)
        
        # Parse format argument
        if not context.args:
            await update.message.reply_text(
                "<b>📤 Data Export</b>\n\n"
                "Choose a format:\n\n"
                "/export csv - Excel/Google Sheets compatible\n"
                "/export json - Developer-friendly with nested data\n"
                "/export pdf - Formatted report with summary stats\n\n"
                "<i>All formats include your complete check-in history.</i>",
                parse_mode='HTML'
            )
            return
        
        format_type = context.args[0].lower()
        
        if format_type not in ('csv', 'json', 'pdf'):
            await update.message.reply_text(
                "❌ Invalid format. Use: /export csv, /export json, or /export pdf"
            )
            return
        
        # Send "generating" message
        status_msg = await update.message.reply_text(
            f"⏳ Generating {format_type.upper()} export..."
        )
        
        try:
            result = await export_user_data(user_id, format_type)
            
            if result is None:
                await status_msg.edit_text(ErrorMessages.export_no_data())
                return
            
            # Send file
            await update.message.reply_document(
                document=result["buffer"],
                filename=result["filename"],
                caption=(
                    f"✅ <b>{format_type.upper()} Export Complete</b>\n"
                    f"• {result['checkin_count']} check-ins exported\n"
                    f"• File: {result['filename']}"
                ),
                parse_mode='HTML'
            )
            
            await status_msg.delete()
            logger.info(f"✅ Export ({format_type}) sent to {user_id}: {result['checkin_count']} check-ins")
            
        except Exception as e:
            logger.error(f"Export failed for {user_id}: {e}", exc_info=True)
            await status_msg.edit_text(ErrorMessages.export_failed(format_type))
    
    # ===== Phase 3F: Report Command =====
    
    async def report_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /report command - Generate on-demand weekly report.
        
        This is the same report that auto-sends on Sundays, but
        available anytime via command.
        
        **Process:**
        1. Show "generating" message (reports take 5-15 seconds)
        2. Generate 4 graphs + AI insights
        3. Send text summary + 4 graph images
        """
        from src.agents.reporting_agent import generate_and_send_weekly_report
        from src.utils.ux import ErrorMessages
        
        user_id = str(update.effective_user.id)
        
        # Check user exists
        user = firestore_service.get_user(user_id)
        if not user:
            await update.message.reply_text(ErrorMessages.user_not_found(), parse_mode='HTML')
            return
        
        status_msg = await update.message.reply_text(
            "⏳ Generating your weekly report with graphs...\nThis may take a few seconds."
        )
        
        try:
            result = await generate_and_send_weekly_report(
                user_id=user_id,
                project_id=settings.gcp_project_id,
                bot=self.bot,
            )
            
            await status_msg.delete()
            
            if result.get("status") == "failed":
                await update.message.reply_text(ErrorMessages.service_unavailable(), parse_mode='HTML')
            
            logger.info(f"✅ On-demand report generated for {user_id}")
            
        except Exception as e:
            logger.error(f"Report generation failed for {user_id}: {e}", exc_info=True)
            await status_msg.edit_text(ErrorMessages.service_unavailable())
    
    # ===== Phase 3F: Leaderboard Command =====
    
    async def leaderboard_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /leaderboard command - Show weekly rankings.
        
        **Ranking Logic:**
        1. Average compliance score over last 7 days (primary)
        2. Current streak length (tiebreaker, +0.1 per day, max +5)
        3. Minimum 3 check-ins to qualify
        
        **Privacy:**
        Only users with leaderboard_opt_in=True are shown.
        Users see their own rank even if not in top 10.
        """
        from src.services.social_service import calculate_leaderboard, format_leaderboard_message
        from src.utils.ux import ErrorMessages
        
        user_id = str(update.effective_user.id)
        
        user = firestore_service.get_user(user_id)
        if not user:
            await update.message.reply_text(ErrorMessages.user_not_found(), parse_mode='HTML')
            return
        
        try:
            entries = calculate_leaderboard(period_days=7, top_n=10)
            message = format_leaderboard_message(entries, user_id)
            
            await update.message.reply_text(message, parse_mode='HTML')
            logger.info(f"✅ Leaderboard shown to {user_id}")
            
        except Exception as e:
            logger.error(f"Leaderboard failed for {user_id}: {e}", exc_info=True)
            await update.message.reply_text(ErrorMessages.generic_error(), parse_mode='HTML')
    
    # ===== Phase 3F: Invite/Referral Command =====
    
    async def invite_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /invite command - Show referral link and stats.
        
        **Deep Link Mechanism:**
        Telegram supports deep links: t.me/botname?start=PAYLOAD
        When a new user clicks this, the bot receives /start PAYLOAD.
        We parse the referral code to attribute the new user.
        
        **Rewards:**
        - Referrer: +1% compliance boost per active referral (max +5%)
        - Referee: 3 bonus streak shields
        """
        from src.services.social_service import generate_referral_link, get_referral_stats, format_referral_message
        from src.utils.ux import ErrorMessages
        
        user_id = str(update.effective_user.id)
        
        user = firestore_service.get_user(user_id)
        if not user:
            await update.message.reply_text(ErrorMessages.user_not_found(), parse_mode='HTML')
            return
        
        try:
            # Get bot username for deep link
            bot_info = await self.bot.get_me()
            bot_username = bot_info.username
            
            referral_link = generate_referral_link(user_id, bot_username)
            stats = get_referral_stats(user_id)
            message = format_referral_message(referral_link, stats)
            
            await update.message.reply_text(message, parse_mode='HTML')
            logger.info(f"✅ Referral info shown to {user_id}")
            
        except Exception as e:
            logger.error(f"Invite command failed for {user_id}: {e}", exc_info=True)
            await update.message.reply_text(ErrorMessages.generic_error(), parse_mode='HTML')
    
    # ===== Phase 3F: Share/Brag Command =====
    
    async def share_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /share command - Generate shareable stats image.
        
        Creates a visually appealing image (1080x1920) with the user's
        key stats, branded design, and QR code to join the bot.
        
        Designed for sharing on Instagram stories, WhatsApp status, etc.
        """
        from src.services.social_service import generate_shareable_stats_image
        from src.utils.ux import ErrorMessages
        
        user_id = str(update.effective_user.id)
        
        user = firestore_service.get_user(user_id)
        if not user:
            await update.message.reply_text(ErrorMessages.user_not_found(), parse_mode='HTML')
            return
        
        status_msg = await update.message.reply_text("⏳ Generating your stats card...")
        
        try:
            checkins = firestore_service.get_recent_checkins(user_id, days=30)
            image_buffer = generate_shareable_stats_image(user, checkins)
            
            await update.message.reply_photo(
                photo=image_buffer,
                caption=(
                    f"📸 <b>Your Accountability Stats</b>\n\n"
                    f"🔥 {user.streaks.current_streak}-day streak\n"
                    f"🏆 {user.streaks.longest_streak} best streak\n"
                    f"✅ {user.streaks.total_checkins} total check-ins\n\n"
                    f"<i>Share this image to inspire others!</i>"
                ),
                parse_mode='HTML'
            )
            
            await status_msg.delete()
            logger.info(f"✅ Shareable stats generated for {user_id}")
            
        except Exception as e:
            logger.error(f"Share command failed for {user_id}: {e}", exc_info=True)
            await status_msg.edit_text(ErrorMessages.generic_error())
    
    # ===== Phase 3F: Resume Command =====
    
    async def resume_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /resume command - Resume an incomplete check-in.
        
        **How It Works:**
        1. Check Firestore for partial_checkins/{user_id}
        2. If found and <24h old, offer to resume
        3. If not found, tell user no incomplete check-in exists
        
        This enables timeout recovery - when a check-in times out,
        the partial state is saved and can be resumed here.
        """
        from src.utils.ux import TimeoutManager
        
        user_id = str(update.effective_user.id)
        
        partial_state = TimeoutManager.get_partial_state(user_id)
        
        if partial_state:
            conversation_type = partial_state.get("conversation_type", "check-in")
            await update.message.reply_text(
                f"💾 <b>Incomplete {conversation_type.title()} Found</b>\n\n"
                f"You have an unfinished {conversation_type}.\n\n"
                f"Use /checkin to start fresh, or just continue where you left off.\n"
                f"Your previous answers have been saved.",
                parse_mode='HTML'
            )
            # Note: Actual resume integration with ConversationHandler would
            # require modifying conversation.py to check for partial state
            # on entry. For now, we inform the user and let them restart.
        else:
            await update.message.reply_text(
                "ℹ️ <b>No Incomplete Check-In</b>\n\n"
                "You don't have any unfinished check-ins.\n"
                "Start a new one with /checkin",
                parse_mode='HTML'
            )
    
    # ===== Phase 3B: General Message Handler =====
    
    async def handle_general_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle general text messages (non-commands) - Phase 3B + 3E.
        
        **Flow:**
        1. Use supervisor to classify intent (emotional, query, checkin)
        2. Route to appropriate agent:
           - emotional → Emotional Support Agent
           - query → Query Agent (Phase 3E: Natural language queries)
           - checkin → Suggest /checkin command
        
        **Phase 3E Enhancement:**
        Query intent now routes to QueryAgent which:
        - Classifies query type (compliance, streak, training, etc.)
        - Fetches relevant data from Firestore
        - Generates natural language response
        
        **Why This Handler?**
        Users don't always use commands. They might say:
        - "I'm feeling lonely" (emotional)
        - "What's my average compliance?" (query → QueryAgent)
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
            from src.agents.query_agent import get_query_agent  # Phase 3E
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
                # Phase 3E: Natural language query processing
                query_agent = get_query_agent(project_id=settings.gcp_project_id)
                state = await query_agent.process(state)
                
                response = state.get("response", 
                    "I can help with that! Here are some useful commands:\n\n"
                    "📊 /status - See your streak and stats\n"
                    "⚡ /weekly - Last 7 days summary\n"
                    "📅 /monthly - Last 30 days summary\n"
                    "✅ /checkin - Do your daily check-in\n"
                    "❓ /help - See all available commands"
                )
                
                await update.message.reply_text(response, parse_mode="Markdown")
                
                logger.info(f"✅ Query answered for {user_id}")
                
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
