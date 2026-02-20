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
import difflib
import logging
from typing import Optional, Tuple

from src.config import settings
from src.services.firestore_service import firestore_service
from src.models.schemas import User, get_current_date_ist
from src.utils.metrics import metrics
from src.utils.rate_limiter import rate_limiter

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
    
    # All registered slash-command names (used for fuzzy matching)
    REGISTERED_COMMANDS = [
        "start", "help", "status", "metrics", "mode", "checkin", "quickcheckin",
        "use_shield", "set_partner", "partner_status", "unlink_partner",
        "achievements", "career", "weekly", "monthly", "yearly",
        "export", "report", "leaderboard", "rank", "invite", "refer",
        "brag", "share", "resume", "correct", "timezone", "support",
        "admin_status",
    ]
    
    # Natural language phrases mapped to command names.
    # Checked BEFORE the LLM supervisor to save API costs.
    # Longest-match wins (more specific phrases take priority).
    COMMAND_KEYWORDS = {
        "partner_status": [
            "partner status", "how is my partner", "partner update",
            "accountability partner", "partner doing", "my partner",
        ],
        "report": [
            "give me a report", "weekly report", "show report",
            "my report", "generate report",
        ],
        "status": [
            "my status", "how am i doing", "show status",
            "my dashboard",
        ],
        "checkin": [
            "check in", "let me check in", "ready to check in",
            "want to check in", "daily check",
        ],
        "help": [
            "available commands", "what can you do",
            "show commands", "list commands",
        ],
        "achievements": [
            "my achievements", "show achievements", "my badges",
        ],
        "leaderboard": [
            "leaderboard", "rankings", "how do i compare",
        ],
        "export": [
            "export data", "download data", "export csv",
        ],
        "weekly": [
            "weekly stats", "last week", "this week stats",
        ],
        "monthly": [
            "monthly stats", "last month", "this month stats",
        ],
        "metrics": [
            "my metrics", "show metrics", "metric dashboard",
            "per metric", "detailed metrics", "tier 1 breakdown",
        ],
    }
    
    def _fuzzy_match_command(self, text: str) -> Tuple[Optional[str], float]:
        """
        Match a misspelled /command against registered commands using
        SequenceMatcher (Ratcliff/Obershelp algorithm from stdlib).
        
        Returns (best_command_name, similarity_score) or (None, 0.0).
        """
        if not text.startswith('/'):
            return None, 0.0
        
        # Extract the attempted command, strip / and any @bot suffix
        attempted = text.split()[0].lstrip('/').split('@')[0].lower()
        
        best_match = None
        best_score = 0.0
        for cmd in self.REGISTERED_COMMANDS:
            score = difflib.SequenceMatcher(None, attempted, cmd).ratio()
            if score > best_score:
                best_score = score
                best_match = cmd
        
        return best_match, best_score
    
    def _get_command_handler_map(self) -> dict:
        """Map command names to their handler methods for programmatic dispatch."""
        from src.bot.stats_commands import weekly_command, monthly_command, yearly_command
        return {
            "start": self.start_command,
            "help": self.help_command,
            "status": self.status_command,
            "metrics": self.metrics_command,
            "mode": self.mode_command,
            "use_shield": self.use_shield_command,
            "set_partner": self.set_partner_command,
            "partner_status": self.partner_status_command,
            "unlink_partner": self.unlink_partner_command,
            "achievements": self.achievements_command,
            "career": self.career_command,
            "export": self.export_command,
            "report": self.report_command,
            "leaderboard": self.leaderboard_command,
            "invite": self.invite_command,
            "share": self.share_command,
            "resume": self.resume_command,
            "correct": self.correct_command,
            "timezone": self.timezone_command,
            "support": self.support_command,
            "admin_status": self.admin_status_command,
            "weekly": weekly_command,
            "monthly": monthly_command,
            "yearly": yearly_command,
        }
    
    def _match_command_keywords(self, message: str) -> Optional[str]:
        """
        Match a natural-language message against the keyword-to-command map.
        Prefers the longest keyword match for specificity (e.g., "partner status"
        beats "status" when the message says "show partner status").
        """
        msg_lower = message.lower().strip()
        
        best_match = None
        best_length = 0
        for command, keywords in self.COMMAND_KEYWORDS.items():
            for keyword in keywords:
                if keyword in msg_lower and len(keyword) > best_length:
                    best_match = command
                    best_length = len(keyword)
        
        return best_match
    
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
        self.application.add_handler(CommandHandler("metrics", self.metrics_command))
        self.application.add_handler(CommandHandler("mode", self.mode_command))
        
        # Phase 3A: Streak shield command
        self.application.add_handler(CommandHandler("use_shield", self.use_shield_command))
        
        # Phase 3B: Accountability partner commands
        self.application.add_handler(CommandHandler("set_partner", self.set_partner_command))
        self.application.add_handler(CommandHandler("partner_status", self.partner_status_command))
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
        
        # Correction command: fix mistakes in today's check-in
        self.application.add_handler(CommandHandler("correct", self.correct_command))
        
        # Phase B: Timezone change command (post-onboarding)
        self.application.add_handler(CommandHandler("timezone", self.timezone_command))
        
        # Phase D: /support command — direct entry to emotional support agent
        self.application.add_handler(CommandHandler("support", self.support_command))
        
        # Admin-only: monitoring status command
        self.application.add_handler(CommandHandler("admin_status", self.admin_status_command))
        
        # Phase 3A: Callback query handlers for inline keyboard buttons
        self.application.add_handler(CallbackQueryHandler(self.mode_selection_callback, pattern="^mode_"))
        self.application.add_handler(CallbackQueryHandler(self.timezone_confirmation_callback, pattern="^tz_"))
        
        # Mode change callback (from /mode command inline buttons)
        # Uses "change_mode_" prefix to avoid conflict with "mode_" (onboarding)
        self.application.add_handler(CallbackQueryHandler(self.mode_change_callback, pattern="^change_mode_"))
        
        # Phase 3D: Career mode callback handlers
        self.application.add_handler(CallbackQueryHandler(self.career_callback, pattern="^career_"))
        
        # Correction callback: toggle individual tier1 items in today's check-in
        self.application.add_handler(CallbackQueryHandler(self.correct_toggle_callback, pattern="^correct_"))
        
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
        
        # Fuzzy command matching: catch any unrecognized /command at group 2.
        # All valid CommandHandlers (group 0) run first; this only fires when
        # no handler matched the slash-command.
        self.application.add_handler(
            MessageHandler(filters.COMMAND, self.handle_unknown_command),
            group=2
        )
        
        # Callback for fuzzy-match "Did you mean /X?" inline buttons
        self.application.add_handler(
            CallbackQueryHandler(self.fuzzy_command_callback, pattern="^fuzzy_cmd:")
        )
        
        logger.info("✅ Command handlers registered")
    
    def register_conversation_handler(self, conversation_handler) -> None:
        """
        Register check-in conversation handler.
        
        Called from main.py after conversation handler is created.
        
        Args:
            conversation_handler: ConversationHandler for check-ins
            
        <b>CRITICAL: Handler Groups</b>
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
                f"🎯 <b>Welcome to Your Constitution Accountability Agent!</b>\n\n"
                f"Hi {user.first_name}! I'm here to help you build unbreakable discipline "
                f"through daily accountability.\n\n"
                f"<b>What I do for you:</b>\n"
                f"✅ Daily check-ins to track your progress\n"
                f"✅ Smart reminders (9 PM, 9:30 PM, 10 PM)\n"
                f"✅ Personalized AI feedback on your performance\n"
                f"✅ Pattern detection & proactive interventions\n"
                f"✅ Streak tracking with protection shields\n"
                f"✅ Gamification & achievements\n\n"
                f"<b>📋 Your Tier 1 Non-Negotiables:</b>\n\n"
                f"These are your *daily foundation* - the 6 non-negotiables:\n\n"
                f"1️⃣ <b>💤 Sleep:</b> 7+ hours of quality sleep\n"
                f"2️⃣ <b>💪 Training:</b> Workout or scheduled rest day\n"
                f"3️⃣ <b>🧠 Deep Work:</b> 2+ hours of focused work\n"
                f"4️⃣ <b>📚 Skill Building:</b> 2+ hours career-focused learning\n"
                f"5️⃣ <b>🚫 Zero Porn:</b> Absolute rule, no exceptions\n"
                f"6️⃣ <b>🛡️ Boundaries:</b> No toxic interactions\n\n"
                f"Every day, I'll ask you about these 6 items + a few questions "
                f"to calculate your compliance score.\n\n"
                f"Let's personalize your experience..."
            )
            
            await update.message.reply_text(welcome_message, parse_mode='HTML')
            
            # Step 2: Mode Selection with Inline Keyboard
            mode_message = (
                f"🎯 <b>Choose Your Mode:</b>\n\n"
                f"<b>Optimization Mode</b> (Beast Mode)\n"
                f"• Training: 6x/week, one rest day\n"
                f"• Deep work: 2+ hours daily\n"
                f"• For aggressive growth phases\n\n"
                f"<b>Maintenance Mode</b> (Steady State)\n"
                f"• Training: 4x/week, flexible schedule\n"
                f"• Deep work: 2+ hours daily\n"
                f"• For sustainable consistency\n\n"
                f"<b>Survival Mode</b> (Crisis)\n"
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
            
            await update.message.reply_text(mode_message, reply_markup=reply_markup, parse_mode='HTML')
        
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
            f"✅ <b>{mode_emojis[selected_mode]} {selected_mode.title()} Mode Selected!</b>\n\n"
            f"Great choice. I've set your constitution to {selected_mode} mode.\n"
            f"You can change this anytime with /mode",
            parse_mode='HTML'
        )
        
        # Step 3: Timezone Selection (2-level picker: confirm IST or pick region → city)
        timezone_message = (
            f"🌍 <b>Timezone Setup</b>\n\n"
            f"I've defaulted your timezone to <b>Asia/Kolkata (IST)</b>.\n\n"
            f"Your daily reminders will be sent at:\n"
            f"• 1st reminder: 9:00 PM\n"
            f"• 2nd reminder: 9:30 PM\n"
            f"• 3rd reminder: 10:00 PM\n\n"
            f"Is IST your timezone?"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Yes, IST is correct", callback_data="tz_confirm")],
            [InlineKeyboardButton("🌎 No, change my timezone", callback_data="tz_change")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=user.id,
            text=timezone_message,
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        logger.info(f"✅ User {user_id} selected mode: {selected_mode}")
    
    async def timezone_confirmation_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle timezone selection during onboarding (Phase B: Custom Timezone).

        This implements a 2-level picker flow:
        1. User confirms IST or clicks "Change" → show Region picker
        2. User picks a region (Americas/Europe/Asia) → show City picker
        3. User picks a city → timezone is saved, onboarding continues

        Callback data patterns:
        - "tz_confirm"                → IST confirmed
        - "tz_change"                 → Show region picker
        - "tz_region_<region>"        → Show cities in that region
        - "tz_set_<IANA timezone>"    → Set the selected timezone
        - "tz_back"                   → Go back to region picker

        Args:
            update: Callback query update
            context: Bot context
        """
        from src.utils.timezone_utils import TIMEZONE_CATALOG, get_timezone_display_name

        query = update.callback_query
        await query.answer()

        user = update.effective_user
        user_id = str(user.id)

        if query.data == "tz_confirm":
            is_post_onboarding = (
                context.user_data is not None
                and context.user_data.get("tz_change_mode") == "post_onboarding"
            )
            if is_post_onboarding:
                # From /timezone command — just confirm current timezone
                context.user_data.pop("tz_change_mode", None)
                await query.edit_message_text("✅ Timezone unchanged. Your current timezone is still active.")
            else:
                # Onboarding flow — full setup
                await self._finalize_timezone_onboarding(query, context, user, user_id, "Asia/Kolkata")

        elif query.data == "tz_change":
            # Show region picker (level 1)
            keyboard = []
            for region_key, region_data in TIMEZONE_CATALOG.items():
                keyboard.append([
                    InlineKeyboardButton(
                        region_data["label"],
                        callback_data=f"tz_region_{region_key}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("🇮🇳 Keep IST", callback_data="tz_confirm")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "🌍 <b>Select Your Region:</b>\n\n"
                "Pick the region closest to you, then you'll choose your city.",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

        elif query.data.startswith("tz_region_"):
            # Show city picker for the chosen region (level 2)
            region_key = query.data.replace("tz_region_", "")

            if region_key not in TIMEZONE_CATALOG:
                await query.edit_message_text("Invalid region. Please use /timezone to try again.")
                return

            region = TIMEZONE_CATALOG[region_key]
            keyboard = []
            for tz_info in region["timezones"]:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{tz_info['label']} ({tz_info['offset']})",
                        callback_data=f"tz_set_{tz_info['id']}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("⬅️ Back to regions", callback_data="tz_back")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                f"🏙️ <b>{region['label']} — Choose Your City:</b>\n\n"
                f"Select the timezone closest to you:",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

        elif query.data == "tz_back":
            # Go back to region picker
            keyboard = []
            for region_key, region_data in TIMEZONE_CATALOG.items():
                keyboard.append([
                    InlineKeyboardButton(
                        region_data["label"],
                        callback_data=f"tz_region_{region_key}"
                    )
                ])
            keyboard.append([InlineKeyboardButton("🇮🇳 Keep IST", callback_data="tz_confirm")])
            reply_markup = InlineKeyboardMarkup(keyboard)

            await query.edit_message_text(
                "🌍 <b>Select Your Region:</b>\n\n"
                "Pick the region closest to you, then you'll choose your city.",
                reply_markup=reply_markup,
                parse_mode='HTML'
            )

        elif query.data.startswith("tz_set_"):
            # Set the selected timezone
            selected_tz = query.data.replace("tz_set_", "")
            is_post_onboarding = (
                context.user_data is not None
                and context.user_data.get("tz_change_mode") == "post_onboarding"
            )

            if is_post_onboarding:
                # Post-onboarding: just update timezone and confirm
                await self._update_timezone_post_onboarding(query, user_id, selected_tz)
                context.user_data.pop("tz_change_mode", None)
            else:
                # Onboarding: full flow with streak explanation + first check-in prompt
                await self._finalize_timezone_onboarding(query, context, user, user_id, selected_tz)

        elif query.data == "tz_cancel":
            # User cancelled the timezone change (post-onboarding only)
            if context.user_data is not None:
                context.user_data.pop("tz_change_mode", None)
            await query.edit_message_text("✅ Timezone unchanged. Your current timezone is still active.")

        else:
            logger.warning(f"Unknown timezone callback data: {query.data}")

    async def _update_timezone_post_onboarding(
        self,
        query,
        user_id: str,
        timezone: str
    ) -> None:
        """
        Handle timezone change from /timezone command (post-onboarding).

        Unlike onboarding, this simply updates the user's timezone in Firestore
        and confirms the change. No streak explanation or first check-in prompt.
        """
        from src.utils.timezone_utils import get_timezone_display_name

        firestore_service.update_user(user_id, {"timezone": timezone})
        tz_display = get_timezone_display_name(timezone)

        await query.edit_message_text(
            f"✅ <b>Timezone Updated!</b>\n\n"
            f"Your timezone is now: <b>{tz_display}</b> (`{timezone}`)\n\n"
            f"All reminders and date calculations will use this timezone.\n"
            f"Your daily reminders will be sent at 9 PM in your new local time.",
            parse_mode='HTML'
        )
        logger.info(f"🌍 User {user_id} changed timezone to {timezone}")

    async def _finalize_timezone_onboarding(
        self,
        query,
        context: ContextTypes.DEFAULT_TYPE,
        user,
        user_id: str,
        timezone: str
    ) -> None:
        """
        Complete the timezone step of onboarding: save tz, show streak info, prompt first check-in.

        This is called once the user has either confirmed IST or picked a custom timezone.
        It updates the user's Firestore document and sends the remaining onboarding messages.

        Args:
            query: The callback query to edit
            context: Bot context for sending follow-up messages
            user: The effective_user from the update
            user_id: String user ID
            timezone: IANA timezone string to save
        """
        from src.utils.timezone_utils import get_timezone_display_name

        # Update timezone in Firestore
        firestore_service.update_user(user_id, {"timezone": timezone})

        tz_display = get_timezone_display_name(timezone)

        await query.edit_message_text(
            f"✅ <b>Timezone Set: {tz_display}</b>\n\n"
            f"Your daily reminders will be sent at 9 PM in your local time.",
            parse_mode='HTML'
        )

        # Streak Mechanics Explanation
        streak_message = (
            f"🔥 <b>How Streaks Work:</b>\n\n"
            f"• <b>Check in daily</b> to build your streak\n"
            f"• <b>48-hour grace period:</b> Miss a day? You have 48 hours to recover\n"
            f"• <b>Streak shields:</b> You get 3 shields per month to protect your streak\n"
            f"• <b>Achievements:</b> Unlock badges at 7, 30, 90, 180, 365 days\n\n"
            f"Your longest streak becomes your permanent record — it never decreases!"
        )

        await context.bot.send_message(
            chat_id=user.id,
            text=streak_message,
            parse_mode='HTML'
        )

        # First Check-In Prompt
        first_checkin_message = (
            f"🎯 <b>You're Ready to Start!</b>\n\n"
            f"Welcome to your accountability journey. I'll remind you daily at 9 PM "
            f"in your local time, but you can check in anytime.\n\n"
            f"<b>Your first check-in is available now!</b>\n\n"
            f"Use /checkin to complete your first check-in and start building your streak.\n\n"
            f"<b>Quick Commands:</b>\n"
            f"/checkin - Start daily check-in\n"
            f"/status - View your stats\n"
            f"/help - Show all commands\n\n"
            f"Let's build something great together!"
        )

        await context.bot.send_message(
            chat_id=user.id,
            text=first_checkin_message,
            parse_mode='HTML'
        )

        logger.info(f"✅ Onboarding complete for user {user_id} (timezone: {timezone})")

    async def timezone_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        /timezone — Let existing users change their timezone post-onboarding.

        Presents the same 2-level picker (Region → City) used during onboarding,
        but updates the existing user record instead of creating a new one.

        The callback reuses the same "tz_" prefix handlers, so the
        timezone_confirmation_callback method handles the selection.
        We store a flag in context.user_data to distinguish from onboarding flow.
        """
        from src.utils.timezone_utils import TIMEZONE_CATALOG, get_timezone_display_name

        user_id = str(update.effective_user.id)
        user = firestore_service.get_user(user_id)

        if not user:
            await update.message.reply_text(
                "Please run /start first to create your profile."
            )
            return

        current_tz = getattr(user, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
        tz_display = get_timezone_display_name(current_tz)

        # Mark context so callback knows this is post-onboarding
        if context.user_data is not None:
            context.user_data["tz_change_mode"] = "post_onboarding"

        # Show current timezone + region picker
        keyboard = []
        for region_key, region_data in TIMEZONE_CATALOG.items():
            keyboard.append([
                InlineKeyboardButton(
                    region_data["label"],
                    callback_data=f"tz_region_{region_key}"
                )
            ])
        keyboard.append([InlineKeyboardButton("🚫 Cancel (keep current)", callback_data="tz_cancel")])
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            f"🌍 <b>Change Timezone</b>\n\n"
            f"Current timezone: <b>{tz_display}</b> (`{current_tz}`)\n\n"
            f"Select your new region:",
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        logger.info(f"🌍 User {user_id} initiated timezone change (current: {current_tz})")

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
        
        # Check if checked in today (Phase B: use user's timezone)
        user_tz = getattr(user, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
        from src.utils.timezone_utils import get_current_date
        today = get_current_date(user_tz)
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
        )
        
        # Tier 1 per-metric breakdown (Phase 4)
        from src.services.analytics_service import format_status_tier1_breakdown
        tier1_section = format_status_tier1_breakdown(recent_checkins)
        if tier1_section:
            status_text += tier1_section + "\n\n"
        
        status_text += "<b>✅ Today:</b>\n"
        
        if checked_in_today:
            status_text += "• ✅ Check-in complete!\n"
        else:
            status_text += "• ⏳ Check-in pending (use /checkin)\n"
        
        if user.streaks.current_streak >= 30:
            status_text += "\n🚀 You're on fire! Keep it up!"
        elif user.streaks.current_streak >= 7:
            status_text += "\n💪 Solid consistency! You're building something real."
        elif user.streaks.current_streak > 0:
            status_text += "\n🔥 Great start! Keep the momentum going."
        else:
            status_text += "\n🎯 Ready to start a new streak? Use /checkin"
        
        status_text += "\n\n<i>Use /metrics for detailed trends and streaks.</i>"
        
        await update.message.reply_text(status_text, parse_mode='HTML')
        logger.info(f"✅ /status command from {user_id}")
    
    async def metrics_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /metrics command -- detailed per-metric tracking dashboard.

        Shows 7-day and 30-day completion rates, week-over-week trend
        arrows, and per-metric streaks for every Tier 1 non-negotiable.
        """
        user_id = str(update.effective_user.id)

        user = firestore_service.get_user(user_id)
        if not user:
            from src.utils.ux import ErrorMessages
            await update.message.reply_text(ErrorMessages.user_not_found(), parse_mode='HTML')
            return

        checkins_7d = firestore_service.get_recent_checkins(user_id, days=7)
        checkins_30d = firestore_service.get_recent_checkins(user_id, days=30)

        from src.services.analytics_service import format_metric_dashboard
        dashboard = format_metric_dashboard(checkins_7d, checkins_30d)
        await update.message.reply_text(dashboard, parse_mode='HTML')
        logger.info(f"✅ /metrics command from {user_id}")
    
    async def mode_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /mode command -- view or change constitution mode.
        
        Usage:
        - /mode            → Shows current mode + inline buttons to switch
        - /mode optimization → Directly switches to optimization mode
        - /mode maintenance  → Directly switches to maintenance mode
        - /mode survival     → Directly switches to survival mode
        
        Why inline buttons AND text args?
        ---------------------------------
        Text args are faster for power users who know what they want.
        Inline buttons are friendlier for casual users who need to see options.
        Supporting both is a standard UX pattern in Telegram bots.
        """
        user_id = str(update.effective_user.id)
        user = firestore_service.get_user(user_id)
        
        if not user:
            await update.message.reply_text(
                "❌ User not found. Please use /start first."
            )
            return
        
        valid_modes = ['optimization', 'maintenance', 'survival']
        
        # Check if user provided a mode argument (e.g., /mode optimization)
        if context.args and len(context.args) > 0:
            requested_mode = context.args[0].lower()
            
            if requested_mode in valid_modes:
                if requested_mode == user.constitution_mode:
                    await update.message.reply_text(
                        f"You're already in <b>{requested_mode.title()}</b> mode! ✅",
                        parse_mode='HTML'
                    )
                    return
                
                # Switch mode
                firestore_service.update_user_mode(user_id, requested_mode)
                
                mode_emojis = {
                    "optimization": "🚀",
                    "maintenance": "⚖️",
                    "survival": "🛡️"
                }
                
                await update.message.reply_text(
                    f"✅ <b>Mode Changed!</b>\n\n"
                    f"{mode_emojis[requested_mode]} <b>{requested_mode.title()} Mode</b> is now active.\n\n"
                    f"This affects your check-in expectations and pattern detection thresholds.\n"
                    f"Use /mode anytime to view or change.",
                    parse_mode='HTML'
                )
                logger.info(f"✅ User {user_id} changed mode to {requested_mode}")
                return
            else:
                await update.message.reply_text(
                    f"❌ Unknown mode: '{requested_mode}'\n\n"
                    f"Valid modes: optimization, maintenance, survival\n"
                    f"Example: /mode optimization"
                )
                return
        
        # No args provided: show info + inline keyboard buttons
        mode_emojis = {
            "optimization": "🚀",
            "maintenance": "⚖️",
            "survival": "🛡️"
        }
        current_emoji = mode_emojis.get(user.constitution_mode, "🎯")
        
        mode_info = (
            f"<b>🎯 Constitution Modes</b>\n\n"
            f"<b>Current Mode:</b> {current_emoji} {user.constitution_mode.title()} ✅\n\n"
            f"<b>🚀 Optimization Mode:</b>\n"
            f"• All systems firing - aggressive growth\n"
            f"• 6x/week training, 3+ hours deep work\n"
            f"• Target: 90%+ compliance\n\n"
            f"<b>⚖️ Maintenance Mode:</b>\n"
            f"• Sustaining progress, recovery phase\n"
            f"• 4x/week training, 2+ hours deep work\n"
            f"• Target: 80%+ compliance\n\n"
            f"<b>🛡️ Survival Mode:</b>\n"
            f"• Crisis mode - protect bare minimums\n"
            f"• 3x/week training, 1+ hour deep work\n"
            f"• Target: 60%+ compliance\n\n"
            f"Tap a button below to switch, or type:\n"
            f"/mode optimization | /mode maintenance | /mode survival"
        )
        
        # Build inline keyboard (exclude current mode)
        keyboard = []
        for mode in valid_modes:
            if mode != user.constitution_mode:
                keyboard.append([
                    InlineKeyboardButton(
                        f"{mode_emojis[mode]} Switch to {mode.title()}",
                        callback_data=f"change_mode_{mode}"
                    )
                ])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(mode_info, reply_markup=reply_markup, parse_mode='HTML')
        logger.info(f"✅ /mode command from {user_id}")
    
    async def mode_change_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle mode change via inline button press (from /mode command).
        
        Callback data format: "change_mode_optimization", "change_mode_maintenance", etc.
        Uses "change_mode_" prefix to avoid conflict with "mode_" prefix used
        during onboarding (mode_selection_callback).
        """
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        new_mode = query.data.replace("change_mode_", "")
        
        valid_modes = ['optimization', 'maintenance', 'survival']
        if new_mode not in valid_modes:
            await query.edit_message_text("❌ Invalid mode selection.")
            return
        
        # Update mode in Firestore
        firestore_service.update_user_mode(user_id, new_mode)
        
        mode_emojis = {
            "optimization": "🚀",
            "maintenance": "⚖️",
            "survival": "🛡️"
        }
        
        await query.edit_message_text(
            f"✅ <b>Mode Changed!</b>\n\n"
            f"{mode_emojis[new_mode]} <b>{new_mode.title()} Mode</b> is now active.\n\n"
            f"This affects your check-in expectations and pattern detection thresholds.\n"
            f"Use /mode anytime to view or change.",
            parse_mode='HTML'
        )
        
        logger.info(f"✅ User {user_id} changed mode to {new_mode} via inline button")
    
    # ===== Phase 3D: Career Mode Commands =====
    
    async def career_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /career command (Phase 3D Career Tracking).
        
        Display and toggle career mode.
        
        <b>Career Mode System:</b>
        - <b>skill_building:</b> Learning phase (LeetCode, system design, upskilling)
        - <b>job_searching:</b> Active job hunt (applications, interviews)
        - <b>employed:</b> Working toward promotion/raise
        
        <b>Why This Matters:</b>
        Career mode determines how the Tier 1 skill building question is phrased.
        The question adapts to your current career phase for more relevant tracking.
        
        <b>Constitution Alignment:</b>
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
                "📚 <b>Skill Building</b>\n"
                "Learning phase: LeetCode, system design, AI/ML upskilling, courses, projects\n\n"
                "✅ <b>Skill building question:</b> Did you do 2+ hours skill building?"
            ),
            "job_searching": (
                "💼 <b>Job Searching</b>\n"
                "Active job hunt: Applications, interviews, networking, skill building\n\n"
                "✅ <b>Skill building question:</b> Did you make job search progress?"
            ),
            "employed": (
                "🎯 <b>Employed</b>\n"
                "Working toward promotion/raise: High-impact work, skill development, visibility\n\n"
                "✅ <b>Skill building question:</b> Did you work toward promotion/raise?"
            )
        }
        
        current_desc = mode_descriptions.get(user.career_mode, "Unknown mode")
        
        message = (
            f"<b>🎯 Career Phase Tracking</b>\n\n"
            f"<b>Current Mode:</b>\n{current_desc}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Why Career Mode Matters:</b>\n"
            f"• Your Tier 1 skill building question adapts to your career phase\n"
            f"• Tracks progress toward ₹28-42 LPA June 2026 goal\n"
            f"• Aligns check-ins with constitution career protocols\n\n"
            f"<b>Change mode using buttons below:</b>"
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
            parse_mode='HTML'
        )
        logger.info(f"✅ /career command from {user_id}")
    
    async def career_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle career mode selection from inline buttons (Phase 3D).
        
        <b>Callback Data Format:</b>
        - career_skill → skill_building mode
        - career_job → job_searching mode
        - career_employed → employed mode
        
        <b>Process:</b>
        1. Parse callback data to get selected mode
        2. Update user's career_mode in Firestore
        3. Edit message to show confirmation
        4. Log change
        
        <b>Impact:</b>
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
            f"✅ <b>Career mode updated!</b>\n\n"
            f"<b>New Mode:</b> {mode_names[new_mode]}\n\n"
            f"<b>Your Tier 1 skill building question will now be:</b>\n"
            f"\"{mode_questions[new_mode]}\"\n\n"
            f"This change takes effect starting your next check-in.\n\n"
            f"🎯 Keep tracking progress toward your June 2026 goal! (₹28-42 LPA)",
            parse_mode='HTML'
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
                f"❌ <b>No Streak Shields Available</b>\n\n"
                f"You've used all {user.streak_shields.total} shields this month.\n"
                f"Shields reset every 30 days.\n\n"
                f"<b>Last reset:</b> {user.streak_shields.last_reset or 'Never'}\n\n"
                f"💪 The best protection is consistency! Try to check in daily.",
                parse_mode='HTML'
            )
            return
        
        # Check if user actually needs a shield (hasn't checked in today)
        from src.utils.timezone_utils import get_checkin_date
        from src.utils.streak import calculate_days_without_checkin
        
        # Phase B: Use user's timezone for 3 AM cutoff calculation
        user_tz = getattr(user, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
        checkin_date = get_checkin_date(tz=user_tz)
        checked_in_today = firestore_service.checkin_exists(user_id, checkin_date)
        
        if checked_in_today:
            await update.message.reply_text(
                f"✅ <b>Shield Not Needed!</b>\n\n"
                f"You've already checked in for {checkin_date}.\n"
                f"Your streak is safe! 🔥\n\n"
                f"🛡️ Shields remaining: {user.streak_shields.available}/{user.streak_shields.total}\n\n"
                f"Save your shields for emergencies.",
                parse_mode='HTML'
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
                f"🛡️ <b>Streak Shield Activated!</b>\n\n"
                f"Your {user.streaks.current_streak}-day streak is protected.\n\n"
                f"<b>Shields remaining:</b> {updated_user.streak_shields.available}/{updated_user.streak_shields.total}\n\n"
                f"⚠️ <b>Important:</b> Shields are for emergencies only!\n"
                f"Using too many shields defeats the purpose of daily accountability.\n\n"
                f"Get back on track tomorrow with /checkin! 💪",
                parse_mode='HTML'
            )
            
            logger.info(f"✅ User {user_id} used streak shield ({updated_user.streak_shields.available} remaining)")
        else:
            await update.message.reply_text(
                f"❌ <b>Failed to use shield</b>\n\n"
                f"Something went wrong. Please try again or contact support.",
                parse_mode='HTML'
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
                "❌ <b>Invalid usage</b>\n\n"
                "Format: /set_partner @username\n\n"
                "Example: /set_partner @john_doe",
                parse_mode='HTML'
            )
            return
        
        partner_username = context.args[0][1:]  # Remove @ symbol
        
        # Search for partner by telegram username
        partner = firestore_service.get_user_by_telegram_username(partner_username)
        
        if not partner:
            await update.message.reply_text(
                f"❌ <b>User not found</b>\n\n"
                f"User @{partner_username} hasn't started using the bot yet.\n\n"
                "They need to send /start first!",
                parse_mode='HTML'
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
                f"👥 <b>Accountability Partner Request</b>\n\n"
                f"{user.name} wants to be your accountability partner.\n\n"
                f"<b>What this means:</b>\n"
                f"• You'll be notified if they ghost for 5+ days\n"
                f"• They'll be notified if you ghost for 5+ days\n"
                f"• Mutual support and motivation\n\n"
                f"Accept this request?"
            ),
            parse_mode='HTML',
            reply_markup=reply_markup
        )
        
        await update.message.reply_text(
            f"✅ <b>Partner request sent to @{partner_username}!</b>\n\n"
            f"Waiting for them to accept...",
            parse_mode='HTML'
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
                "❌ <b>Error:</b> One or both users not found.",
                parse_mode='HTML'
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
            f"✅ <b>Partnership Confirmed!</b>\n\n"
            f"You and {requester.name} are now accountability partners.\n\n"
            f"You'll be notified if they ghost for 5+ days, and vice versa.",
            parse_mode='HTML'
        )
        
        await context.bot.send_message(
            chat_id=requester.telegram_id,
            text=(
                f"✅ <b>Partnership Confirmed!</b>\n\n"
                f"{accepter.name} accepted your request!\n\n"
                f"You're now accountability partners. 🤝"
            ),
            parse_mode='HTML'
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
                "❌ <b>Error:</b> User not found.",
                parse_mode='HTML'
            )
            return
        
        await query.edit_message_text(
            "❌ <b>Partnership declined.</b>",
            parse_mode='HTML'
        )
        
        await context.bot.send_message(
            chat_id=requester.telegram_id,
            text=f"❌ {decliner.name} declined your partnership request."
        )
        
        logger.info(f"❌ Partnership declined: {requester_user_id} ← {decliner.user_id}")
    
    async def partner_status_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        /partner_status — View your accountability partner's dashboard (Phase C).

        This is the core of Partner Mutual Visibility. It shows aggregate
        partner stats while respecting privacy (no individual Tier 1 items).

        <b>What is shown (aggregate only):</b>
        - Partner's current/longest streak
        - Whether partner checked in today
        - Today's compliance % (if checked in)
        - Weekly check-in count and avg compliance
        - Motivational comparison footer

        <b>What is NOT shown (privacy):</b>
        - Individual Tier 1 items (sleep, training, etc.)
        - Challenge text / rating reason
        - Emotional support conversations

        <b>Rate limiting:</b> Standard tier (10s cooldown, 30/hour)
        """
        if not await self._check_rate_limit(update, "partner_status"):
            return

        user_id = str(update.effective_user.id)
        user = firestore_service.get_user(user_id)

        if not user:
            await update.message.reply_text(
                "❌ User not found. Please use /start first."
            )
            return

        if not user.accountability_partner_id:
            await update.message.reply_text(
                "❌ <b>No Partner Linked</b>\n\n"
                "You don't have an accountability partner yet.\n\n"
                "Link one with: /set_partner @username\n\n"
                "Having a partner increases your check-in consistency by 40%!",
                parse_mode='HTML'
            )
            return

        # Fetch partner data
        partner = firestore_service.get_user(user.accountability_partner_id)
        if not partner:
            await update.message.reply_text(
                "❌ Your partner's account could not be found.\n"
                "They may have deleted their profile.\n\n"
                "Use /unlink_partner to remove, then /set_partner to link a new one."
            )
            return

        # Get partner's timezone for date calculation
        partner_tz = getattr(partner, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'

        from src.utils.timezone_utils import get_current_date

        # Partner's today check-in status
        partner_today = get_current_date(partner_tz)
        partner_checkin_today = firestore_service.get_checkin(
            partner.user_id, partner_today
        )
        partner_checked_in = partner_checkin_today is not None
        partner_today_compliance = (
            partner_checkin_today.compliance_score
            if partner_checkin_today else None
        )

        # Partner's weekly stats
        partner_weekly = firestore_service.get_recent_checkins(partner.user_id, days=7)
        partner_weekly_count = len(partner_weekly)
        partner_weekly_avg = (
            sum(c.compliance_score for c in partner_weekly) / partner_weekly_count
            if partner_weekly_count > 0 else 0.0
        )

        # User's weekly stats (for comparison footer)
        user_weekly = firestore_service.get_recent_checkins(user_id, days=7)
        user_weekly_avg = (
            sum(c.compliance_score for c in user_weekly) / len(user_weekly)
            if user_weekly else 0.0
        )

        # Format the dashboard
        from src.utils.ux import format_partner_dashboard
        dashboard = format_partner_dashboard(
            partner_name=partner.name,
            partner_streak_current=partner.streaks.current_streak,
            partner_streak_longest=partner.streaks.longest_streak,
            partner_checked_in_today=partner_checked_in,
            partner_today_compliance=partner_today_compliance,
            partner_weekly_checkins=partner_weekly_count,
            partner_weekly_possible=7,
            partner_weekly_avg_compliance=partner_weekly_avg,
            user_streak_current=user.streaks.current_streak,
            user_weekly_avg_compliance=user_weekly_avg,
        )

        await update.message.reply_text(dashboard, parse_mode='HTML')
        logger.info(
            f"👥 /partner_status from {user_id} → partner {partner.user_id} "
            f"(checked_in={partner_checked_in})"
        )

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
                "✅ <b>Partnership removed.</b>",
                parse_mode='HTML'
            )
            return
        
        # Unlink bidirectionally
        firestore_service.set_accountability_partner(user_id, None, None)
        firestore_service.set_accountability_partner(partner.user_id, None, None)
        
        await update.message.reply_text(
            f"✅ <b>Partnership with {partner.name} removed.</b>",
            parse_mode='HTML'
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
        
        <b>Theory - Why This Works:</b>
        - Viewing achievements creates <b>progress visualization</b>
        - Rarity grouping creates <b>status hierarchy</b> (legendary first)
        - Next milestone creates <b>goal clarity</b> (X days until Month Master)
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
                "🎯 <b>No achievements yet!</b>\n\n"
                "Keep checking in daily to unlock:\n"
                "🎯 First Step (1 day)\n"
                "🏅 Week Warrior (7 days)\n"
                "🏆 Month Master (30 days)\n"
                "⭐ Perfect Week (7 days at 100%)\n\n"
                f"Your current streak: <b>{user.streaks.current_streak} days</b> 🔥\n\n"
                "Complete your daily check-in with /checkin",
                parse_mode='HTML'
            )
            return
        
        # Build achievements display message
        message_parts = []
        message_parts.append(f"🏆 <b>Your Achievements ({len(user.achievements)}/{len(achievement_service.get_all_achievements())})</b>\n")
        
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
                message_parts.append(f"\n<b>{rarity_labels[rarity]}</b>")
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
                f"\n📈 <b>Next Milestone:</b> {next_milestone_name} "
                f"({days_remaining} day{'s' if days_remaining != 1 else ''} to go!)"
            )
        else:
            # User has completed all streak milestones!
            message_parts.append("\n🎉 <b>All streak milestones unlocked!</b> You're a legend! 👑")
        
        # Add call to action
        message_parts.append(
            f"\n💪 Keep going! Current streak: <b>{current_streak} days</b> 🔥"
        )
        
        final_message = "\n".join(message_parts)
        
        await update.message.reply_text(
            final_message,
            parse_mode='HTML'
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
        
        <b>How It Works:</b>
        1. Rate limit check (expensive tier: 30min cooldown, 2/hour)
        2. Parse format from command arguments
        3. Call export service to generate file in memory
        4. Send file via Telegram's document upload API
        
        <b>Telegram File Limits:</b>
        - Documents: up to 50MB
        - Our exports: typically <1MB (well within limits)
        """
        from src.services.export_service import export_user_data
        from src.utils.ux import ErrorMessages
        
        # Rate limit check — /export is expensive (especially PDF)
        if not await self._check_rate_limit(update, "export"):
            return
        
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
        
        <b>Process:</b>
        1. Rate limit check (expensive tier: 30min cooldown, 2/hour)
        2. Show "generating" message (reports take 5-15 seconds)
        3. Generate 4 graphs + AI insights
        4. Send text summary + 4 graph images
        """
        from src.agents.reporting_agent import generate_and_send_weekly_report
        from src.utils.ux import ErrorMessages
        
        # Rate limit check — /report is expensive (AI + 4 graphs)
        if not await self._check_rate_limit(update, "report"):
            return
        
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
        
        <b>Ranking Logic:</b>
        1. Average compliance score over last 7 days (primary)
        2. Current streak length (tiebreaker, +0.1 per day, max +5)
        3. Minimum 3 check-ins to qualify
        
        <b>Privacy:</b>
        Only users with leaderboard_opt_in=True are shown.
        Users see their own rank even if not in top 10.
        """
        from src.services.social_service import calculate_leaderboard, format_leaderboard_message
        from src.utils.ux import ErrorMessages
        
        # Rate limit check — standard tier
        if not await self._check_rate_limit(update, "leaderboard"):
            return
        
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
        
        <b>Deep Link Mechanism:</b>
        Telegram supports deep links: t.me/botname?start=PAYLOAD
        When a new user clicks this, the bot receives /start PAYLOAD.
        We parse the referral code to attribute the new user.
        
        <b>Rewards:</b>
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
        
        <b>How It Works:</b>
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
    
    # ===== Check-In Correction Command =====
    
    async def correct_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /correct command -- fix mistakes in today's check-in.
        
        WHY THIS EXISTS:
        ----------------
        Users sometimes fat-finger a button during the fast-paced Tier 1 
        questions (e.g., accidentally pressing "NO" for Sleep when they meant
        "YES"). Without a correction mechanism, one wrong tap permanently
        affects compliance scores, streaks, patterns, and achievements.
        
        CONSTRAINTS:
        - Only today's check-in can be corrected
        - Must be within 2 hours of the original check-in
        - Maximum 1 correction per check-in (to prevent gaming)
        
        FLOW:
        1. Load today's check-in from Firestore
        2. Verify time constraints
        3. Display current Tier 1 answers with toggle buttons
        4. User taps items to toggle (YES<->NO)
        5. When done, user taps "Save Correction"
        6. Compliance score is recalculated and saved
        """
        user_id = str(update.effective_user.id)
        
        user = firestore_service.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found. Please use /start first.")
            return
        
        # Get today's date (Phase B: use user's timezone)
        from src.utils.timezone_utils import get_current_date
        user_tz = getattr(user, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
        today = get_current_date(user_tz)
        
        # Load today's check-in
        checkin = firestore_service.get_checkin(user_id, today)
        if not checkin:
            await update.message.reply_text(
                "❌ No check-in found for today.\n\n"
                "You can only correct today's check-in after completing it.\n"
                "Use /checkin to start your daily check-in."
            )
            return
        
        # Check if already corrected
        if checkin.corrected_at is not None:
            await update.message.reply_text(
                "❌ You've already corrected today's check-in.\n\n"
                "Only 1 correction is allowed per check-in to prevent gaming."
            )
            return
        
        # Check time constraint: within 2 hours of original check-in
        from datetime import datetime, timedelta
        now = datetime.utcnow()
        if checkin.completed_at:
            time_since = now - checkin.completed_at
            if time_since > timedelta(hours=2):
                hours_ago = time_since.total_seconds() / 3600
                await update.message.reply_text(
                    f"❌ Correction window has expired.\n\n"
                    f"Your check-in was {hours_ago:.1f} hours ago. "
                    f"Corrections must be made within 2 hours of check-in.\n\n"
                    f"This prevents gaming the system -- own your answers and use "
                    f"tomorrow as a fresh start!"
                )
                return
        
        # Build the correction interface
        tier1 = checkin.tier1_non_negotiables
        items = {
            'sleep': ('💤 Sleep', tier1.sleep),
            'training': ('💪 Training', tier1.training),
            'deepwork': ('🧠 Deep Work', tier1.deep_work),
            'skillbuilding': ('📚 Skill Building', tier1.skill_building),
            'porn': ('🚫 Zero Porn', tier1.zero_porn),
            'boundaries': ('🛡️ Boundaries', tier1.boundaries),
        }
        
        # Show current answers
        lines = ["<b>✏️ Correct Today's Check-In</b>\n"]
        lines.append("Current answers:\n")
        for key, (label, value) in items.items():
            status = "✅ YES" if value else "❌ NO"
            lines.append(f"  {label}: {status}")
        lines.append("\nTap an item below to toggle it (YES↔NO):")
        lines.append("Then tap <b>Save Correction</b> when done.\n")
        
        # Build toggle keyboard
        keyboard = []
        for key, (label, value) in items.items():
            current = "✅" if value else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{current} {label} → Tap to toggle",
                    callback_data=f"correct_{key}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton("💾 Save Correction", callback_data="correct_save")
        ])
        keyboard.append([
            InlineKeyboardButton("🚫 Cancel", callback_data="correct_cancel")
        ])
        
        # Store current correction state in user context
        context.user_data['correction_items'] = {
            k: v for k, (_, v) in items.items()
        }
        context.user_data['correction_date'] = today
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "\n".join(lines),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
        
        logger.info(f"✏️ User {user_id} started correction for {today}")
    
    async def correct_toggle_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle correction button presses (toggle items or save/cancel).
        
        Callback data format:
        - "correct_sleep" → Toggle sleep
        - "correct_save" → Save all changes
        - "correct_cancel" → Abort correction
        """
        query = update.callback_query
        await query.answer()
        
        user_id = str(update.effective_user.id)
        action = query.data.replace("correct_", "")
        
        # Cancel correction
        if action == "cancel":
            context.user_data.pop('correction_items', None)
            context.user_data.pop('correction_date', None)
            await query.edit_message_text("❌ Correction cancelled. No changes saved.")
            return
        
        # Save correction
        if action == "save":
            items = context.user_data.get('correction_items')
            date = context.user_data.get('correction_date')
            
            if not items or not date:
                await query.edit_message_text("❌ Correction session expired. Use /correct to try again.")
                return
            
            # Build Firestore update payload
            from src.utils.compliance import calculate_compliance_score
            from src.models.schemas import Tier1NonNegotiables
            
            tier1 = Tier1NonNegotiables(
                sleep=items['sleep'],
                training=items['training'],
                deep_work=items['deepwork'],
                skill_building=items['skillbuilding'],
                zero_porn=items['porn'],
                boundaries=items['boundaries']
            )
            
            new_compliance = calculate_compliance_score(tier1)
            
            firestore_update = {
                "tier1_non_negotiables": tier1.model_dump(),
                "compliance_score": new_compliance,
            }
            
            success = firestore_service.update_checkin(user_id, date, firestore_update)
            
            if success:
                # Clean up context
                context.user_data.pop('correction_items', None)
                context.user_data.pop('correction_date', None)
                
                await query.edit_message_text(
                    f"✅ <b>Check-In Corrected!</b>\n\n"
                    f"Updated compliance: {new_compliance:.0f}%\n\n"
                    f"Your stats, patterns, and achievements will reflect the correction.\n"
                    f"Note: Only 1 correction per check-in is allowed.",
                    parse_mode='HTML'
                )
                logger.info(f"✅ User {user_id} corrected check-in for {date}: compliance={new_compliance}%")
            else:
                await query.edit_message_text(
                    "❌ Failed to save correction. Please try again or contact support."
                )
            return
        
        # Toggle an item
        items = context.user_data.get('correction_items')
        if not items or action not in items:
            await query.edit_message_text("❌ Correction session expired. Use /correct to try again.")
            return
        
        # Flip the boolean
        items[action] = not items[action]
        context.user_data['correction_items'] = items
        
        # Rebuild the message and keyboard
        item_labels = {
            'sleep': '💤 Sleep',
            'training': '💪 Training',
            'deepwork': '🧠 Deep Work',
            'skillbuilding': '📚 Skill Building',
            'porn': '🚫 Zero Porn',
            'boundaries': '🛡️ Boundaries',
        }
        
        lines = ["<b>✏️ Correct Today's Check-In</b>\n"]
        lines.append("Updated answers:\n")
        for key, label in item_labels.items():
            status = "✅ YES" if items[key] else "❌ NO"
            lines.append(f"  {label}: {status}")
        lines.append("\nTap an item to toggle (YES↔NO):")
        lines.append("Then tap <b>Save Correction</b> when done.\n")
        
        keyboard = []
        for key, label in item_labels.items():
            current = "✅" if items[key] else "❌"
            keyboard.append([
                InlineKeyboardButton(
                    f"{current} {label} → Tap to toggle",
                    callback_data=f"correct_{key}"
                )
            ])
        keyboard.append([
            InlineKeyboardButton("💾 Save Correction", callback_data="correct_save")
        ])
        keyboard.append([
            InlineKeyboardButton("🚫 Cancel", callback_data="correct_cancel")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            "\n".join(lines),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )
    
    # ===== Rate Limiting Helper =====
    
    async def _check_rate_limit(
        self,
        update: Update,
        command: str
    ) -> bool:
        """
        Check rate limit for a command. If denied, sends user-friendly message.
        
        Rate limiting protects expensive resources (AI API, graph generation)
        from abuse. Each command is assigned a tier (expensive, ai_powered,
        standard, or free) with corresponding cooldowns and hourly limits.
        
        Args:
            update: Telegram Update object
            command: Command name without slash (e.g., "report")
            
        Returns:
            bool: True if allowed, False if rate-limited (message already sent)
        """
        user_id = str(update.effective_user.id)
        allowed, message = rate_limiter.check(user_id, command)
        
        if not allowed:
            await update.message.reply_text(message)
            metrics.increment("rate_limit_hits")
            return False
        
        # Track the command in metrics
        metrics.increment("commands_total")
        metrics.increment(f"commands_{command}")
        return True
    
    # ===== Admin: Monitoring Status Command =====
    
    async def admin_status_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /admin_status command — show live application metrics.
        
        Admin-only: Checks if the sender's Telegram ID is in the
        admin_telegram_ids config. Non-admins get a generic "unknown command"
        response (security through obscurity — don't reveal the command exists).
        
        Shows:
        - Uptime
        - Check-in counts (full + quick)
        - Command counts
        - AI request counts
        - Error breakdown by category
        - Latency percentiles (webhook, AI, Firestore)
        """
        user_id = str(update.effective_user.id)
        
        # Check admin permission
        admin_ids = [aid.strip() for aid in settings.admin_telegram_ids.split(",") if aid.strip()]
        if user_id not in admin_ids:
            # Don't reveal the command exists to non-admins
            await update.message.reply_text(
                "❓ Unknown command. Use /help to see available commands."
            )
            return
        
        # Generate and send the admin status report
        status_message = metrics.format_admin_status()
        await update.message.reply_text(status_message, parse_mode='HTML')
        logger.info(f"🔧 Admin status requested by {user_id}")
    
    # ===== Phase D: /support Command — Emotional Support Entry Point =====
    
    async def support_command(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle /support command — direct entry to emotional support agent.
        
        <b>What This Does:</b>
        This command creates a direct bridge from "I need help" to the 
        Emotional Support Agent. Previously, emotional support was only 
        available when the supervisor classified a free-text message as 
        "emotional" intent. Now users can explicitly request it.
        
        <b>Context-Aware Support:</b>
        If the user received an intervention in the last 24 hours, the 
        emotional agent is given context about what pattern was detected.
        This makes the support feel connected rather than generic.
        
        For example, if the user got a sleep degradation intervention and 
        then types /support, the agent might say: "I see you've been 
        struggling with sleep. Let's talk about what's driving that."
        
        <b>Flow:</b>
        1. Check rate limit (ai_powered tier — uses Gemini API)
        2. Look up recent interventions (24h) for context
        3. If user provided text after /support, use that as the message
        4. If standalone /support, show welcome prompt and wait
        5. Route to emotional support agent with context
        
        <b>Rate Limiting:</b> ai_powered tier (2 min cooldown, 20/hour)
        """
        user_id = str(update.effective_user.id)
        
        # Rate limit check (ai_powered tier — uses Gemini API)
        if not await self._check_rate_limit(user_id, "support", update):
            return
        
        # Check if user provided text after /support (e.g., "/support I'm feeling down")
        user_message = ""
        if context.args:
            user_message = " ".join(context.args)
        
        if not user_message:
            # No message provided — show welcome prompt
            # Check for recent interventions to personalize the prompt
            recent_interventions = []
            try:
                recent_interventions = firestore_service.get_recent_interventions(
                    user_id, days=1  # Last 24 hours
                )
            except Exception as e:
                logger.warning(f"Failed to fetch recent interventions for context: {e}")
            
            if recent_interventions:
                # Context-aware prompt: reference the recent intervention
                latest = recent_interventions[0]
                pattern_type = latest.get('pattern_type', 'a pattern')
                pattern_display = pattern_type.replace('_', ' ')
                
                prompt_message = (
                    "💙 <b>I'm here.</b>\n\n"
                    f"I noticed you recently received an alert about <b>{pattern_display}</b>.\n\n"
                    "Want to talk about what's going on? You can tell me about:\n"
                    "• What you're struggling with right now\n"
                    "• What triggered a slip or pattern\n"
                    "• How you're feeling emotionally\n"
                    "• Anything on your mind\n\n"
                    "Just type naturally — I'll listen and help you work through it."
                )
            else:
                # Standalone prompt (no recent intervention)
                prompt_message = (
                    "💙 <b>I'm here.</b>\n\n"
                    "What's going on? You can tell me about:\n"
                    "• What you're struggling with right now\n"
                    "• What triggered a slip or pattern\n"
                    "• How you're feeling emotionally\n"
                    "• Anything on your mind\n\n"
                    "Just type naturally — I'll listen and help you work through it."
                )
            
            await update.message.reply_text(prompt_message, parse_mode='HTML')
            
            # Store context so the general message handler knows to route to emotional agent
            context.user_data['support_mode'] = True
            context.user_data['support_intervention_context'] = (
                recent_interventions[0] if recent_interventions else None
            )
            
            logger.info(f"💙 /support prompt sent to {user_id} (context: {bool(recent_interventions)})")
            return
        
        # User provided a message — route directly to emotional support agent
        await self._process_support_message(update, context, user_id, user_message)
    
    async def _process_support_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: str,
        user_message: str,
        intervention_context: dict = None
    ) -> None:
        """
        Process a support message through the emotional support agent.
        
        <b>How Context-Aware Support Works:</b>
        When `intervention_context` is provided, we prepend context to the 
        user's message so the emotional agent understands the situation:
        
        Without context: "I'm struggling" → generic CBT response
        With context: "[Context: Recent sleep degradation intervention] I'm struggling"
                       → sleep-specific CBT response referencing the pattern
        
        Args:
            update: Telegram update object
            context: Bot context
            user_id: User's Telegram ID
            user_message: What the user said
            intervention_context: Recent intervention data (if any)
        """
        try:
            from src.agents.emotional_agent import get_emotional_agent
            from src.agents.state import create_initial_state
            
            # Build context-enriched message for the emotional agent
            enriched_message = user_message
            if intervention_context:
                pattern_type = intervention_context.get('pattern_type', 'unknown')
                enriched_message = (
                    f"[Context: User recently received an intervention for {pattern_type}. "
                    f"They may be struggling with this specific issue.]\n\n"
                    f"{user_message}"
                )
            
            # Create state for emotional agent
            state = create_initial_state(
                user_id=user_id,
                message=enriched_message,
                intent="emotional"
            )
            
            # Process through emotional agent
            emotional_agent = get_emotional_agent()
            state = await emotional_agent.process(state)
            
            response = state.get("response", "I'm here to help. Could you tell me more?")
            await update.message.reply_text(response)
            
            logger.info(f"✅ Emotional support provided via /support to {user_id}")
            
            # Record metric
            from src.utils.metrics import metrics
            metrics.increment("support_sessions")
            
        except Exception as e:
            logger.error(f"❌ Support command failed: {e}", exc_info=True)
            
            # Fallback response (always provide something)
            await update.message.reply_text(
                "I hear that you're going through something difficult. "
                "While I want to help, this is a moment where talking to a real person "
                "might be more valuable.\n\n"
                "Consider:\n"
                "• Texting a friend\n"
                "• Calling someone you trust\n"
                "• If urgent: Crisis hotline (988 in US)\n\n"
                "Your constitution reminds you: difficult moments pass, "
                "your long-term goals remain."
            )
    
    # ===== Fuzzy Command Matching Handler =====
    
    AUTO_EXECUTE_THRESHOLD = 0.85
    SUGGEST_THRESHOLD = 0.60
    
    async def handle_unknown_command(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Catch-all for unrecognized slash-commands (group 2).
        
        Uses difflib.SequenceMatcher to find the closest registered command:
          - score >= 0.85 : auto-execute (obvious typo, e.g. /staus -> /status)
          - 0.60 <= score < 0.85 : suggest with inline button
          - score < 0.60 : generic "unknown command" + show /help
        """
        message_text = update.message.text
        user_id = str(update.effective_user.id)
        
        best_cmd, score = self._fuzzy_match_command(message_text)
        
        logger.info(
            "Fuzzy match for %s from %s: best=%s score=%.2f",
            message_text, user_id, best_cmd, score
        )
        
        if best_cmd and score >= self.AUTO_EXECUTE_THRESHOLD:
            handler_map = self._get_command_handler_map()
            handler = handler_map.get(best_cmd)
            if handler:
                await update.message.reply_text(
                    f"Auto-correcting to /{best_cmd}..."
                )
                await handler(update, context)
                return
        
        if best_cmd and score >= self.SUGGEST_THRESHOLD:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton(
                    f"Yes, run /{best_cmd}",
                    callback_data=f"fuzzy_cmd:{best_cmd}"
                )]
            ])
            await update.message.reply_text(
                f"I don't recognize that command. Did you mean /{best_cmd}?",
                reply_markup=keyboard
            )
            return
        
        await update.message.reply_text(
            "I don't recognize that command.\n\n"
            "Type /help to see all available commands."
        )
    
    async def fuzzy_command_callback(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """Handle inline button press from fuzzy-match suggestion."""
        query = update.callback_query
        await query.answer()
        
        cmd_name = query.data.replace("fuzzy_cmd:", "")
        handler_map = self._get_command_handler_map()
        handler = handler_map.get(cmd_name)
        
        if handler:
            await query.message.reply_text(f"Running /{cmd_name}...")
            await handler(update, context)
        else:
            await query.message.reply_text(
                "Sorry, something went wrong. Try typing the command directly."
            )
    
    # ===== Phase 3B: General Message Handler =====
    
    async def handle_general_message(
        self,
        update: Update,
        context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """
        Handle general text messages (non-commands) - Phase 3B + 3E.
        
        <b>Flow:</b>
        1. Use supervisor to classify intent (emotional, query, checkin)
        2. Route to appropriate agent:
           - emotional → Emotional Support Agent
           - query → Query Agent (Phase 3E: Natural language queries)
           - checkin → Suggest /checkin command
        
        <b>Phase 3E Enhancement:</b>
        Query intent now routes to QueryAgent which:
        - Classifies query type (compliance, streak, training, etc.)
        - Fetches relevant data from Firestore
        - Generates natural language response
        
        <b>Why This Handler?</b>
        Users don't always use commands. They might say:
        - "I'm feeling lonely" (emotional)
        - "What's my average compliance?" (query → QueryAgent)
        - "Ready to check in" (checkin intent)
        
        This handler intelligently routes these messages.
        """
        user_id = str(update.effective_user.id)
        message_text = update.message.text
        
        logger.info(f"📩 General message from {user_id}: '{message_text[:50]}...'")
        
        # Phase D: Check if user is in support mode (sent /support, now sending follow-up)
        if context.user_data.get('support_mode'):
            # Clear support mode (one-shot: consume the context)
            intervention_ctx = context.user_data.pop('support_intervention_context', None)
            context.user_data.pop('support_mode', None)
            
            # Route directly to emotional support agent with context
            await self._process_support_message(
                update, context, user_id, message_text,
                intervention_context=intervention_ctx
            )
            return
        
        # Keyword shortcut: match natural-language phrases to commands
        # BEFORE calling the LLM supervisor (saves API costs).
        matched_cmd = self._match_command_keywords(message_text)
        if matched_cmd:
            logger.info(
                "Keyword match for '%s' -> /%s (skipping LLM)",
                message_text[:50], matched_cmd
            )
            handler_map = self._get_command_handler_map()
            handler = handler_map.get(matched_cmd)
            if handler:
                await handler(update, context)
                return
        
        # Rate limit check — AI-powered tier (Gemini API calls)
        if not await self._check_rate_limit(update, "query"):
            return
        
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
                
                await update.message.reply_text(response, parse_mode='HTML')
                
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
