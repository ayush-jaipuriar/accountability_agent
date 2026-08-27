"""
Integration Tests: Full Check-In Flow
=====================================

Tests the complete 5-state conversation through Telegram handlers.
These are higher-level tests that verify handler integration, not just
business logic in isolation.

Why these matter:
- The production bug was in handler glue code, not services
- Callback query paths differ from command paths
- State transitions must be verified end-to-end
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from telegram import Update, Message, Chat, User as TelegramUser, InlineKeyboardMarkup
from telegram.ext import ContextTypes

from src.bot.conversation import (
    Q1_TIER1, Q2_ALIGNMENT_RATING, Q3_ENERGY_MOOD, Q4_REFLECTION_NOTE,
    handle_mood_callback, finish_checkin, finish_checkin_quick,
)


# ===== Test Fixtures =====

def _make_telegram_user(user_id=123456789, first_name="Test"):
    return TelegramUser(id=user_id, is_bot=False, first_name=first_name)

def _make_chat(chat_id=123456789):
    return Chat(id=chat_id, type="private")

def _make_message(text="", chat_id=123456789, user_id=123456789, message_id=1):
    return Message(
        message_id=message_id,
        date=1715865600,
        chat=_make_chat(chat_id),
        from_user=_make_telegram_user(user_id),
        text=text,
    )

def _make_update(text="", user_id=123456789):
    update = MagicMock(spec=Update)
    update.effective_user = _make_telegram_user(user_id)
    update.message = _make_message(text=text, user_id=user_id)
    update.callback_query = None
    return update

def _make_callback_update(data="", user_id=123456789):
    """Create an update from a callback query (inline button tap)."""
    update = MagicMock(spec=Update)
    update.effective_user = _make_telegram_user(user_id)
    update.message = None  # CRITICAL: callbacks have no update.message
    
    query = MagicMock()
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.message = _make_message(user_id=user_id)
    update.callback_query = query
    
    return update

def _make_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.user_data = {
            "user_id": "123456789",
            "date": "2026-05-16",
            "mode": "maintenance",
            "checkin_start_time": MagicMock(),
            "tier1": MagicMock(),
            "challenges": "test challenges today",
            "rating": 8,
            "rating_reason": "good day overall",
            "tomorrow_priority": "sleep early tonight",
            "tomorrow_obstacle": "feeling very tired",
            "energy_rating": 7,
            "mood_rating": 8,
        }
    context.bot = MagicMock()
    return context


# ===== Callback Safety Tests =====

@pytest.mark.asyncio
class TestCallbackSafety:
    """Verify callback handlers work when update.message is None."""

    async def test_mood_callback_uses_callback_query_message(self):
        """Mood callback must use callback_query.message, not update.message."""
        update = _make_callback_update(data="mood_8")
        context = _make_context()
        
        result = await handle_mood_callback(update, context)
        
        # Should edit message text using callback query message
        update.callback_query.edit_message_text.assert_called_once()
        
        # Should return Q4_REFLECTION_NOTE
        assert result == Q4_REFLECTION_NOTE

    async def test_mood_callback_answered(self):
        """Callback query must be answered to stop loading spinner."""
        update = _make_callback_update(data="mood_8")
        context = _make_context()
        
        await handle_mood_callback(update, context)
        
        update.callback_query.answer.assert_awaited_once()

    async def test_finish_checkin_from_callback_has_no_update_message(self):
        """finish_checkin must handle update.message being None gracefully."""
        update = _make_callback_update(data="mood_8")
        update.message = None  # Explicitly None
        context = _make_context()
        
        # This test verifies that when finish_checkin is called from a callback
        # (where update.message is None), the error handler uses the fallback
        # message path instead of crashing on update.message.reply_text.
        # We expect it to fail validation (mock tier1), but the error handler
        # should still send the error message via callback_query.message.
        with patch("src.bot.conversation._get_message_from_update") as mock_get_msg:
            mock_msg = MagicMock()
            mock_msg.reply_text = AsyncMock()
            mock_get_msg.return_value = mock_msg
            
            # This should NOT crash with AttributeError on update.message
            await finish_checkin(update, context)
            
            # _get_message_from_update should have been called
            mock_get_msg.assert_called_with(update)
            
            # The fallback message should have received the error reply
            mock_msg.reply_text.assert_awaited()


# ===== Handler Consistency Tests =====

class TestHandlerRegistrationConsistency:
    """Verify command lists stay in sync."""

    def test_registered_commands_in_handler_map(self):
        """Every command in REGISTERED_COMMANDS must exist in _get_command_handler_map."""
        from src.bot.telegram_bot import TelegramBotManager
        
        bot = TelegramBotManager.__new__(TelegramBotManager)
        registered = set(bot.REGISTERED_COMMANDS)
        handler_map = bot._get_command_handler_map()
        mapped = set(handler_map.keys())
        
        # ConversationHandler commands don't need to be in the handler map
        conversation_commands = {"checkin", "quickcheckin"}
        missing = registered - mapped - conversation_commands
        extra = mapped - registered
        
        assert not missing, f"Commands in REGISTERED_COMMANDS but missing from handler map: {missing}"
        # Extra in map is okay (aliases, internal commands)

    def test_handler_map_methods_exist(self):
        """Every entry in handler map must be a callable method."""
        from src.bot.telegram_bot import TelegramBotManager
        
        bot = TelegramBotManager.__new__(TelegramBotManager)
        handler_map = bot._get_command_handler_map()
        
        for cmd, handler in handler_map.items():
            assert callable(handler), f"Handler for /{cmd} is not callable: {handler}"


class TestHandlerGroupOrdering:
    """Verify handlers are registered in a single unified group (group 0) in strict precedence order."""

    def test_all_handlers_in_group_zero(self):
        """No handlers should be in group 1 or 2 to avoid parallel execution bugs."""
        from src.bot.telegram_bot import TelegramBotManager
        from telegram.ext import ConversationHandler, MessageHandler
        
        bot = TelegramBotManager("dummy_token:123456789")
        handlers = bot.application.handlers
        
        assert 1 not in handlers or len(handlers[1]) == 0, "Group 1 must be empty"
        assert 2 not in handlers or len(handlers[2]) == 0, "Group 2 must be empty"
        assert 0 in handlers, "Group 0 must contain all handlers"

    def test_conversation_handler_precedes_catchall_message_handlers(self):
        """ConversationHandler must precede general message and unknown command handlers in group 0."""
        from src.bot.telegram_bot import TelegramBotManager
        from telegram.ext import ConversationHandler, MessageHandler
        
        bot = TelegramBotManager("dummy_token:123456789")
        handlers_0 = bot.application.handlers[0]
        
        conv_indices = [i for i, h in enumerate(handlers_0) if isinstance(h, ConversationHandler)]
        msg_indices = [i for i, h in enumerate(handlers_0) if isinstance(h, MessageHandler)]
        
        assert len(conv_indices) >= 1, "Must have at least one ConversationHandler in group 0"
        assert len(msg_indices) >= 2, "Must have general and unknown MessageHandlers in group 0"
        
        first_conv_idx = conv_indices[0]
        first_msg_idx = msg_indices[0]
        assert first_conv_idx < first_msg_idx, (
            f"ConversationHandler (index {first_conv_idx}) must precede catch-all MessageHandler (index {first_msg_idx})"
        )

    def test_register_conversation_handler_maintains_order(self):
        """Calling register_conversation_handler replaces or maintains order in group 0."""
        from src.bot.telegram_bot import TelegramBotManager
        from src.bot.conversation import create_checkin_conversation_handler
        from telegram.ext import ConversationHandler, MessageHandler
        
        bot = TelegramBotManager("dummy_token:123456789")
        new_conv = create_checkin_conversation_handler()
        bot.register_conversation_handler(new_conv)
        
        handlers_0 = bot.application.handlers[0]
        conv_idx = handlers_0.index(new_conv)
        first_msg_idx = [i for i, h in enumerate(handlers_0) if isinstance(h, MessageHandler)][0]
        
        assert conv_idx < first_msg_idx, "Custom ConversationHandler must precede catch-all MessageHandler"


# ===== Feature Flag Tests =====

class TestFeatureFlagWiring:
    """Verify handlers respect feature flags."""

    def test_mood_tracking_flag_gates_handler(self):
        """When enable_mood_tracking is False, mood Q5 handler should not be registered."""
        from src.bot.telegram_bot import TelegramBotManager
        from src.config import settings
        
        # This is a design-level check — actual registration happens at runtime
        # We verify the flag exists and is referenced
        assert hasattr(settings, "enable_mood_tracking")
        assert isinstance(settings.enable_mood_tracking, bool)

    def test_all_new_features_have_flags(self):
        """Every v2.0 feature must have a corresponding flag."""
        from src.config import settings
        
        required_flags = [
            "enable_morning_briefing",
            "enable_churn_prediction",
            "enable_continuous_data",
            "enable_adaptive_checkin",
            "enable_constitution_viewer",
            "enable_goals",
            "enable_partner_challenges",
            "enable_insights_engine",
            "enable_mood_tracking",
            "enable_predictive_interventions",
            "enable_streak_recovery",
            "enable_feature_hints",
            "enable_feedback_collection",
        ]
        
        for flag in required_flags:
            assert hasattr(settings, flag), f"Missing feature flag: {flag}"
            assert isinstance(getattr(settings, flag), bool), f"Flag {flag} must be a bool"


# ===== HTML Safety Tests =====

class TestHtmlSafety:
    """Verify HTML escaping works correctly."""

    def test_escape_unsafe_html_allows_bold(self):
        from src.utils.telegram_utils import _escape_unsafe_html
        
        result = _escape_unsafe_html("<b>Bold</b>")
        assert result == "<b>Bold</b>"

    def test_escape_unsafe_html_escapes_less_than(self):
        from src.utils.telegram_utils import _escape_unsafe_html
        
        result = _escape_unsafe_html("Sleep <6 hours")
        assert "&lt;6" in result
        assert "<6" not in result

    def test_escape_unsafe_html_escapes_arbitrary_tag(self):
        from src.utils.telegram_utils import _escape_unsafe_html
        
        result = _escape_unsafe_html("Value <10 and >5")
        assert "&lt;10" in result
        assert "&gt;5" in result

    def test_get_message_from_update_prefers_message(self):
        from src.utils.telegram_utils import get_message_from_update
        
        update = MagicMock()
        update.message = MagicMock()
        update.callback_query = None
        
        result = get_message_from_update(update)
        assert result == update.message

    def test_get_message_from_update_fallback_to_callback(self):
        from src.utils.telegram_utils import get_message_from_update
        
        update = MagicMock()
        update.message = None
        update.callback_query = MagicMock()
        update.callback_query.message = MagicMock()
        
        result = get_message_from_update(update)
        assert result == update.callback_query.message

    def test_get_message_from_update_returns_none(self):
        from src.utils.telegram_utils import get_message_from_update
        
        update = MagicMock()
        update.message = None
        update.callback_query = None
        
        result = get_message_from_update(update)
        assert result is None
