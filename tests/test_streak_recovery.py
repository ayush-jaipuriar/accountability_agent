"""
Test: Streak Recovery Service
==============================

Tests compassionate streak break handling.
"""

import pytest
from datetime import datetime

from src.services.streak_recovery_service import (
    format_recovery_ritual,
    analyze_break_patterns,
    BREAK_REASONS,
)


class TestRecoveryRitual:
    """Test recovery ritual message formatting."""

    def test_includes_previous_streak(self):
        msg = format_recovery_ritual(15)
        assert "15" in msg
        assert "Streak Broken" in msg

    def test_includes_three_parts(self):
        msg = format_recovery_ritual(10)
        assert "Acknowledge" in msg
        assert "Forgive" in msg
        assert "Restart" in msg

    def test_includes_quote(self):
        msg = format_recovery_ritual(5)
        assert "💡" in msg

    def test_includes_checkin_cta(self):
        msg = format_recovery_ritual(20)
        assert "/checkin" in msg

    def test_with_break_reason(self):
        msg = format_recovery_ritual(8, break_reason="sleep")
        assert "Poor Sleep" in msg


class TestBreakPatternAnalysis:
    """Test break pattern analysis."""

    def test_no_data(self):
        result = analyze_break_patterns([])
        assert result["has_data"] is False

    def test_finds_most_common(self):
        breaks = [
            {"date": "2026-01-01", "reason": "sleep"},
            {"date": "2026-01-02", "reason": "sleep"},
            {"date": "2026-01-03", "reason": "work"},
        ]
        result = analyze_break_patterns(breaks)
        assert result["has_data"] is True
        assert result["most_common_reason"] == "sleep"
        assert result["break_count"] == 3

    def test_distribution(self):
        breaks = [
            {"date": "2026-01-01", "reason": "sleep"},
            {"date": "2026-01-02", "reason": "sleep"},
            {"date": "2026-01-03", "reason": "work"},
        ]
        result = analyze_break_patterns(breaks)
        assert result["reason_distribution"]["sleep"] == 2
        assert result["reason_distribution"]["work"] == 1


from unittest.mock import AsyncMock, MagicMock, patch
from src.models.schemas import User, UserStreaks
from src.services.streak_recovery_service import (
    create_break_reason_keyboard,
    send_recovery_ritual,
    _notify_partner_of_break,
    handle_break_reason_callback,
    format_break_pattern_summary,
)


@pytest.fixture
def recovery_user():
    return User(
        user_id="user_123",
        telegram_id=123,
        name="Recovery User",
        accountability_partner_id="partner_456",
        partner_checkin_notifications_enabled=True,
        streaks=UserStreaks(current_streak=10, longest_streak=20),
    )


class TestSendRecoveryRitual:

    @pytest.mark.asyncio
    async def test_send_recovery_ritual_full_flow(self, recovery_user):
        bot = MagicMock()
        bot.send_message = AsyncMock()

        partner_user = User(
            user_id="partner_456",
            telegram_id=456,
            name="Partner",
            streaks=UserStreaks(current_streak=5),
        )

        with patch('src.services.streak_recovery_service.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = partner_user

            await send_recovery_ritual(bot, recovery_user, previous_streak=15)

            # 2 messages to user + 1 to partner = 3 messages total
            assert bot.send_message.call_count == 3


class TestNotifyPartnerOfBreak:

    @pytest.mark.asyncio
    async def test_notify_partner_disabled_or_missing(self, recovery_user):
        bot = MagicMock()
        bot.send_message = AsyncMock()

        # Disabled notifications
        recovery_user.partner_checkin_notifications_enabled = False
        await _notify_partner_of_break(bot, recovery_user, 10)
        bot.send_message.assert_not_called()

        # No partner id
        recovery_user.accountability_partner_id = None
        recovery_user.partner_checkin_notifications_enabled = True
        await _notify_partner_of_break(bot, recovery_user, 10)
        bot.send_message.assert_not_called()


class TestHandleBreakReasonCallback:

    @pytest.mark.asyncio
    async def test_handle_break_reason_success(self, recovery_user):
        bot = MagicMock()
        with patch('src.services.streak_recovery_service.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = recovery_user

            msg = await handle_break_reason_callback(bot, "user_123", "break_sleep")

            assert "Poor Sleep" in msg
            assert "/checkin" in msg
            mock_fs.update_user.assert_called_once()
            call_updates = mock_fs.update_user.call_args[0][1]
            assert "break_reasons" in call_updates

    @pytest.mark.asyncio
    async def test_handle_break_reason_user_not_found(self):
        bot = MagicMock()
        with patch('src.services.streak_recovery_service.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = None

            msg = await handle_break_reason_callback(bot, "unknown_user", "break_sleep")
            assert "User not found" in msg


class TestFormatBreakPatternSummary:

    def test_format_break_pattern_summary_empty(self):
        assert format_break_pattern_summary([]) == ""

    def test_format_break_pattern_summary_with_data(self):
        break_reasons = [
            {"date": "2026-01-01", "reason": "sleep"},
            {"date": "2026-01-02", "reason": "sleep"},
            {"date": "2026-01-03", "reason": "work"},
        ]
        summary = format_break_pattern_summary(break_reasons)
        assert "Break Pattern Analysis" in summary
        assert "Poor Sleep: 2x" in summary
        assert "Work" in summary


class TestCreateBreakReasonKeyboard:

    def test_create_break_reason_keyboard_all_buttons(self):
        keyboard = create_break_reason_keyboard()
        buttons = keyboard.inline_keyboard
        assert len(buttons) == len(BREAK_REASONS)
