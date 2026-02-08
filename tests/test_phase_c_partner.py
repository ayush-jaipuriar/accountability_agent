"""
Phase C: Partner Mutual Visibility — Comprehensive Test Suite
==============================================================

Tests cover:
1. format_partner_dashboard() — formatting with various data combinations
2. get_partner_comparison_footer() — all comparison branches
3. /partner_status command — handler logic integration
4. Privacy model — verifying no Tier 1 items leak
5. Code integration — source-level verification
6. Edge cases — no partner, deleted partner, zero streaks

Run: python -m pytest tests/test_phase_c_partner.py -v
"""

import pytest
from datetime import datetime
from unittest.mock import patch, MagicMock, AsyncMock, PropertyMock
from pydantic import Field
from typing import Optional, List


# ============================================================
# Helper: Create mock User objects
# ============================================================

def _make_user(
    user_id: str = "111111",
    name: str = "Ayush",
    partner_id: Optional[str] = "222222",
    partner_name: Optional[str] = "Meera",
    streak_current: int = 15,
    streak_longest: int = 47,
    total_checkins: int = 100,
    timezone: str = "Asia/Kolkata",
):
    """Create a mock User object with Pydantic-like attributes."""
    user = MagicMock()
    user.user_id = user_id
    user.telegram_id = int(user_id)
    user.name = name
    user.timezone = timezone
    user.accountability_partner_id = partner_id
    user.accountability_partner_name = partner_name
    user.constitution_mode = "maintenance"

    # Nested streaks object
    user.streaks = MagicMock()
    user.streaks.current_streak = streak_current
    user.streaks.longest_streak = streak_longest
    user.streaks.total_checkins = total_checkins
    user.streaks.last_checkin_date = "2026-02-08"

    # Streak shields
    user.streak_shields = MagicMock()
    user.streak_shields.available = 3
    user.streak_shields.total = 3

    return user


def _make_checkin(date: str, compliance: float = 85.0):
    """Create a mock DailyCheckIn."""
    checkin = MagicMock()
    checkin.date = date
    checkin.compliance_score = compliance
    checkin.tier1 = MagicMock()  # Should NOT be accessed in partner view
    return checkin


# ============================================================
# 1. format_partner_dashboard() Tests
# ============================================================

class TestFormatPartnerDashboard:
    """Test the partner dashboard message formatter."""

    def test_partner_checked_in_today(self):
        """Dashboard when partner has checked in today."""
        from src.utils.ux import format_partner_dashboard
        result = format_partner_dashboard(
            partner_name="Meera",
            partner_streak_current=23,
            partner_streak_longest=47,
            partner_checked_in_today=True,
            partner_today_compliance=83.0,
            partner_weekly_checkins=5,
            partner_weekly_possible=7,
            partner_weekly_avg_compliance=87.0,
            user_streak_current=15,
            user_weekly_avg_compliance=80.0,
        )
        assert "Meera" in result
        assert "Checked in today" in result
        assert "83%" in result
        assert "23 days" in result
        assert "47 days" in result
        assert "5/7" in result
        assert "87%" in result

    def test_partner_not_checked_in(self):
        """Dashboard when partner hasn't checked in yet."""
        from src.utils.ux import format_partner_dashboard
        result = format_partner_dashboard(
            partner_name="Meera",
            partner_streak_current=22,
            partner_streak_longest=47,
            partner_checked_in_today=False,
            partner_today_compliance=None,
            partner_weekly_checkins=4,
            partner_weekly_possible=7,
            partner_weekly_avg_compliance=85.0,
            user_streak_current=15,
            user_weekly_avg_compliance=80.0,
        )
        assert "Not yet checked in" in result
        assert "at risk!" in result
        assert "Compliance:" not in result or "None" not in result

    def test_zero_streak_partner(self):
        """Dashboard for partner with zero streak."""
        from src.utils.ux import format_partner_dashboard
        result = format_partner_dashboard(
            partner_name="John",
            partner_streak_current=0,
            partner_streak_longest=10,
            partner_checked_in_today=False,
            partner_today_compliance=None,
            partner_weekly_checkins=0,
            partner_weekly_possible=7,
            partner_weekly_avg_compliance=0.0,
            user_streak_current=5,
            user_weekly_avg_compliance=75.0,
        )
        assert "0 days" in result
        assert "No check-ins yet this week" in result
        # "at risk!" should NOT show for zero streak (nothing to risk)
        assert "at risk!" not in result

    def test_perfect_week(self):
        """Dashboard for partner with perfect week."""
        from src.utils.ux import format_partner_dashboard
        result = format_partner_dashboard(
            partner_name="Sarah",
            partner_streak_current=30,
            partner_streak_longest=30,
            partner_checked_in_today=True,
            partner_today_compliance=100.0,
            partner_weekly_checkins=7,
            partner_weekly_possible=7,
            partner_weekly_avg_compliance=95.0,
            user_streak_current=30,
            user_weekly_avg_compliance=95.0,
        )
        assert "7/7" in result
        assert "100%" in result
        assert "95%" in result

    def test_html_formatting(self):
        """Dashboard should contain HTML tags for Telegram."""
        from src.utils.ux import format_partner_dashboard
        result = format_partner_dashboard(
            partner_name="Test",
            partner_streak_current=1,
            partner_streak_longest=1,
            partner_checked_in_today=True,
            partner_today_compliance=50.0,
            partner_weekly_checkins=1,
            partner_weekly_possible=7,
            partner_weekly_avg_compliance=50.0,
            user_streak_current=1,
            user_weekly_avg_compliance=50.0,
        )
        assert "<b>" in result  # Should use HTML bold


# ============================================================
# 2. get_partner_comparison_footer() Tests
# ============================================================

class TestPartnerComparisonFooter:
    """Test all branches of the motivational comparison footer."""

    def test_user_leading_both(self):
        """User has higher streak AND compliance."""
        from src.utils.ux import get_partner_comparison_footer
        result = get_partner_comparison_footer(
            user_streak=30, partner_streak=15,
            user_compliance_week=90.0, partner_compliance_week=80.0,
            partner_name="Meera"
        )
        assert "leading" in result.lower() or "momentum" in result.lower()

    def test_partner_ahead_streak(self):
        """Partner has higher streak."""
        from src.utils.ux import get_partner_comparison_footer
        result = get_partner_comparison_footer(
            user_streak=10, partner_streak=25,
            user_compliance_week=80.0, partner_compliance_week=80.0,
            partner_name="Meera"
        )
        assert "15 days" in result  # difference
        assert "Meera" in result

    def test_tied_streaks(self):
        """Both have the same streak (non-zero)."""
        from src.utils.ux import get_partner_comparison_footer
        result = get_partner_comparison_footer(
            user_streak=20, partner_streak=20,
            user_compliance_week=85.0, partner_compliance_week=85.0,
            partner_name="Meera"
        )
        assert "matched" in result.lower() or "together" in result.lower()
        assert "20 days" in result

    def test_user_better_compliance(self):
        """User has significantly better compliance (>10% diff), same streak."""
        from src.utils.ux import get_partner_comparison_footer
        # Use streak=0 so tied-streak branch (which requires >0) doesn't fire
        result = get_partner_comparison_footer(
            user_streak=0, partner_streak=0,
            user_compliance_week=95.0, partner_compliance_week=70.0,
            partner_name="Meera"
        )
        assert "compliance" in result.lower() or "keep it up" in result.lower()

    def test_partner_better_compliance(self):
        """Partner has significantly better compliance."""
        from src.utils.ux import get_partner_comparison_footer
        # Use streak=0 so tied-streak branch doesn't fire
        result = get_partner_comparison_footer(
            user_streak=0, partner_streak=0,
            user_compliance_week=60.0, partner_compliance_week=95.0,
            partner_name="Meera"
        )
        assert "Meera" in result or "energy" in result.lower() or "compliance" in result.lower()

    def test_both_zero_streaks(self):
        """Both at zero — should still return encouraging message."""
        from src.utils.ux import get_partner_comparison_footer
        result = get_partner_comparison_footer(
            user_streak=0, partner_streak=0,
            user_compliance_week=0.0, partner_compliance_week=0.0,
            partner_name="Meera"
        )
        assert len(result) > 5  # Not empty
        assert "showing up" in result.lower() or "together" in result.lower() or "going" in result.lower()


# ============================================================
# 3. /partner_status Command Handler Tests
# ============================================================

class TestPartnerStatusCommand:
    """Test the /partner_status command handler using mocks."""

    @pytest.fixture
    def bot_mgr(self):
        """Create TelegramBotManager with mocked dependencies."""
        with patch("src.bot.telegram_bot.firestore_service") as mock_fs, \
             patch("src.bot.telegram_bot.rate_limiter") as mock_rl:
            mock_rl.check.return_value = (True, None)  # Always allow
            from src.bot.telegram_bot import TelegramBotManager
            mgr = TelegramBotManager.__new__(TelegramBotManager)
            mgr.application = MagicMock()
            yield mgr, mock_fs

    def _make_update(self):
        """Create mock Update for command."""
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111111
        update.message = MagicMock()
        update.message.reply_text = AsyncMock()
        return update

    def _make_context(self):
        context = MagicMock()
        context.user_data = {}
        return context

    @pytest.mark.asyncio
    async def test_no_partner_shows_message(self, bot_mgr):
        """User with no partner should see helpful message."""
        mgr, mock_fs = bot_mgr
        user = _make_user(partner_id=None)
        mock_fs.get_user.return_value = user

        update = self._make_update()
        context = self._make_context()
        await mgr.partner_status_command(update, context)

        reply_text = update.message.reply_text.call_args[0][0]
        assert "No Partner" in reply_text or "don't have" in reply_text
        assert "/set_partner" in reply_text

    @pytest.mark.asyncio
    async def test_partner_not_found(self, bot_mgr):
        """Linked partner ID but user doesn't exist."""
        mgr, mock_fs = bot_mgr
        user = _make_user(partner_id="999999")
        mock_fs.get_user.side_effect = lambda uid: user if uid == "111111" else None

        update = self._make_update()
        context = self._make_context()
        await mgr.partner_status_command(update, context)

        reply_text = update.message.reply_text.call_args[0][0]
        assert "could not be found" in reply_text or "deleted" in reply_text

    @pytest.mark.asyncio
    async def test_partner_checked_in_shows_dashboard(self, bot_mgr):
        """Partner who checked in should show full dashboard."""
        mgr, mock_fs = bot_mgr

        user = _make_user(user_id="111111", partner_id="222222", streak_current=10)
        partner = _make_user(user_id="222222", name="Meera", streak_current=23, streak_longest=47)

        mock_fs.get_user.side_effect = lambda uid: user if uid == "111111" else partner
        mock_fs.get_checkin.return_value = _make_checkin("2026-02-08", 83.0)
        mock_fs.get_recent_checkins.side_effect = lambda uid, days: [
            _make_checkin(f"2026-02-0{i}", 85.0) for i in range(1, 6)
        ]

        update = self._make_update()
        context = self._make_context()
        await mgr.partner_status_command(update, context)

        reply_text = update.message.reply_text.call_args[0][0]
        assert "Meera" in reply_text
        assert "Partner Dashboard" in reply_text
        assert "Checked in today" in reply_text

    @pytest.mark.asyncio
    async def test_partner_not_checked_in(self, bot_mgr):
        """Partner who hasn't checked in should show 'not yet' status."""
        mgr, mock_fs = bot_mgr

        user = _make_user(user_id="111111", partner_id="222222", streak_current=10)
        partner = _make_user(user_id="222222", name="Meera", streak_current=5)

        mock_fs.get_user.side_effect = lambda uid: user if uid == "111111" else partner
        mock_fs.get_checkin.return_value = None  # Not checked in
        mock_fs.get_recent_checkins.return_value = [
            _make_checkin(f"2026-02-0{i}", 80.0) for i in range(1, 4)
        ]

        update = self._make_update()
        context = self._make_context()
        await mgr.partner_status_command(update, context)

        reply_text = update.message.reply_text.call_args[0][0]
        assert "Not yet checked in" in reply_text
        assert "at risk!" in reply_text

    @pytest.mark.asyncio
    async def test_user_not_found(self, bot_mgr):
        """User not in Firestore should see error."""
        mgr, mock_fs = bot_mgr
        mock_fs.get_user.return_value = None

        update = self._make_update()
        context = self._make_context()
        await mgr.partner_status_command(update, context)

        reply_text = update.message.reply_text.call_args[0][0]
        assert "not found" in reply_text.lower() or "/start" in reply_text


# ============================================================
# 4. Privacy Model Tests
# ============================================================

class TestPrivacyModel:
    """Ensure no private data leaks through partner dashboard."""

    def test_no_tier1_in_dashboard(self):
        """Dashboard message should never contain Tier 1 item names."""
        from src.utils.ux import format_partner_dashboard
        result = format_partner_dashboard(
            partner_name="Meera",
            partner_streak_current=23,
            partner_streak_longest=47,
            partner_checked_in_today=True,
            partner_today_compliance=83.0,
            partner_weekly_checkins=5,
            partner_weekly_possible=7,
            partner_weekly_avg_compliance=87.0,
            user_streak_current=15,
            user_weekly_avg_compliance=80.0,
        )
        # These should NEVER appear in partner view
        privacy_violations = [
            "sleep", "training", "porn", "diet", "sunlight",
            "skill building", "deep work", "leetcode",
            "challenge", "rating_reason", "tomorrow_priority"
        ]
        result_lower = result.lower()
        for term in privacy_violations:
            assert term not in result_lower, f"Privacy violation: '{term}' found in dashboard"

    def test_dashboard_source_has_no_tier1_access(self):
        """The format function signature should not accept Tier 1 data."""
        import inspect
        from src.utils.ux import format_partner_dashboard
        sig = inspect.signature(format_partner_dashboard)
        params = list(sig.parameters.keys())
        # Should NOT have any tier1-related parameters
        for param in params:
            assert "tier1" not in param.lower(), f"Parameter '{param}' may leak Tier 1 data"

    def test_command_source_doesnt_pass_tier1(self):
        """partner_status_command should not pass tier1 items to formatter."""
        with open("src/bot/telegram_bot.py", "r") as f:
            content = f.read()
        # Find the partner_status_command section
        start = content.find("async def partner_status_command")
        end = content.find("async def unlink_partner_command")
        section = content[start:end]
        # Verify no tier1 access
        assert ".tier1" not in section, "partner_status_command accesses tier1 items"
        assert "tier1_items" not in section


# ============================================================
# 5. Code Integration Tests
# ============================================================

class TestCodeIntegration:
    """Source-level verification of Phase C code."""

    def test_partner_status_command_registered(self):
        """telegram_bot.py should register /partner_status handler."""
        with open("src/bot/telegram_bot.py", "r") as f:
            content = f.read()
        assert 'CommandHandler("partner_status"' in content

    def test_partner_status_command_exists(self):
        """telegram_bot.py should have partner_status_command method."""
        with open("src/bot/telegram_bot.py", "r") as f:
            content = f.read()
        assert "async def partner_status_command" in content

    def test_format_partner_dashboard_exists(self):
        """ux.py should have format_partner_dashboard function."""
        with open("src/utils/ux.py", "r") as f:
            content = f.read()
        assert "def format_partner_dashboard" in content

    def test_get_partner_comparison_footer_exists(self):
        """ux.py should have comparison footer function."""
        with open("src/utils/ux.py", "r") as f:
            content = f.read()
        assert "def get_partner_comparison_footer" in content

    def test_help_text_includes_partner_status(self):
        """Help text should list /partner_status."""
        with open("src/utils/ux.py", "r") as f:
            content = f.read()
        assert "/partner_status" in content

    def test_rate_limiter_has_partner_status(self):
        """Rate limiter should include partner_status in standard tier."""
        with open("src/utils/rate_limiter.py", "r") as f:
            content = f.read()
        assert '"partner_status"' in content

    def test_ghosting_alert_enhanced(self):
        """Ghosting alert in main.py should include partner context."""
        with open("src/main.py", "r") as f:
            content = f.read()
        assert "/partner_status" in content
        assert "partner_streak" in content
        assert "Your own streak" in content

    def test_partner_status_uses_partner_timezone(self):
        """Command should use partner's timezone for date calculation."""
        with open("src/bot/telegram_bot.py", "r") as f:
            content = f.read()
        # Find the partner_status_command section
        start = content.find("async def partner_status_command")
        end = content.find("async def unlink_partner_command")
        section = content[start:end]
        assert "partner_tz" in section
        assert "get_current_date(partner_tz)" in section

    def test_partner_status_fetches_weekly_for_both(self):
        """Command should fetch weekly stats for BOTH user and partner."""
        with open("src/bot/telegram_bot.py", "r") as f:
            content = f.read()
        start = content.find("async def partner_status_command")
        end = content.find("async def unlink_partner_command")
        section = content[start:end]
        assert "partner_weekly" in section
        assert "user_weekly" in section


# ============================================================
# 6. Edge Cases
# ============================================================

class TestEdgeCases:
    """Edge case scenarios for partner dashboard."""

    def test_dashboard_with_new_partner(self):
        """Brand new partner (zero everything)."""
        from src.utils.ux import format_partner_dashboard
        result = format_partner_dashboard(
            partner_name="NewUser",
            partner_streak_current=0,
            partner_streak_longest=0,
            partner_checked_in_today=False,
            partner_today_compliance=None,
            partner_weekly_checkins=0,
            partner_weekly_possible=7,
            partner_weekly_avg_compliance=0.0,
            user_streak_current=50,
            user_weekly_avg_compliance=90.0,
        )
        assert "NewUser" in result
        assert "0 days" in result

    def test_dashboard_with_100_percent_compliance(self):
        """Perfect compliance day."""
        from src.utils.ux import format_partner_dashboard
        result = format_partner_dashboard(
            partner_name="Perfect",
            partner_streak_current=100,
            partner_streak_longest=100,
            partner_checked_in_today=True,
            partner_today_compliance=100.0,
            partner_weekly_checkins=7,
            partner_weekly_possible=7,
            partner_weekly_avg_compliance=100.0,
            user_streak_current=100,
            user_weekly_avg_compliance=100.0,
        )
        assert "100%" in result
        assert "100 days" in result

    def test_comparison_footer_with_zero_vs_high(self):
        """User at 0 streak, partner at high streak."""
        from src.utils.ux import get_partner_comparison_footer
        result = get_partner_comparison_footer(
            user_streak=0, partner_streak=50,
            user_compliance_week=0.0, partner_compliance_week=95.0,
            partner_name="Champion"
        )
        assert "Champion" in result
        assert "50 days" in result

    def test_dashboard_returns_string(self):
        """Dashboard must return a string."""
        from src.utils.ux import format_partner_dashboard
        result = format_partner_dashboard(
            partner_name="Test",
            partner_streak_current=1,
            partner_streak_longest=1,
            partner_checked_in_today=True,
            partner_today_compliance=50.0,
            partner_weekly_checkins=1,
            partner_weekly_possible=7,
            partner_weekly_avg_compliance=50.0,
            user_streak_current=1,
            user_weekly_avg_compliance=50.0,
        )
        assert isinstance(result, str)
        assert len(result) > 50  # Non-trivially long
