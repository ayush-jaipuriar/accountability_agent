"""
Unit tests for 5 Unified Hubs, Checkin Predictive Baselines, and Single Hero Card consolidation.
Phase 3.1 UX Architecture.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, date

from telegram import Update, Message, User as TelegramUser, CallbackQuery
from telegram.ext import ContextTypes

from src.models.schemas import User, UserStreaks, DailyCheckIn, Tier1NonNegotiables, CheckInResponses
from src.services.analytics_service import calculate_progress_hub_stats
from src.services.checkin_baseline import compute_predictive_baseline
from src.utils.ux import (
    format_progress_hub,
    get_progress_keyboard,
    format_settings_panel,
    get_settings_keyboard,
    format_goals_studio,
    get_goals_keyboard,
    format_partner_arena,
    get_partner_keyboard,
    generate_executive_help_text,
)


def _make_responses():
    return CheckInResponses(
        challenges="Completed all tasks today with high focus",
        rating=9,
        rating_reason="Maintained deep work without distractions",
        tomorrow_priority="Continue refactoring test coverage",
        tomorrow_obstacle="No blockers or obstacles anticipated",
    )


def _make_user(user_id="12345", name="Alex", mode="standard", partner_id=None):
    return User(
        user_id=user_id,
        telegram_id=int(user_id) if user_id.isdigit() else 12345,
        name=name,
        telegram_username="alex_test",
        timezone="America/New_York",
        constitution_mode=mode,
        career_mode="software_engineer",
        accountability_partner_id=partner_id,
        streaks=UserStreaks(current_streak=10, longest_streak=15, total_checkins=25),
        settings={"morning_briefing_enabled": True},
    )


def _make_checkins(user_id="12345", count=7, score=100.0):
    res = []
    for i in range(count):
        d_str = f"2026-08-{10+i:02d}"
        res.append(
            DailyCheckIn(
                date=d_str,
                user_id=user_id,
                mode="standard",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep_hours=7.5,
                    deep_work_hours=2.5,
                    training=True,
                    training_intensity="moderate",
                    zero_porn=True,
                    boundaries=True,
                ),
                responses=_make_responses(),
                compliance_score=score,
            )
        )
    return res


# =========================================================================
# 1. Progress Hub Tests
# =========================================================================

class TestProgressHub:
    """Test progress hub analytics, formatters, and bot handlers."""

    @patch("src.services.firestore_service.firestore_service.get_recent_checkins")
    @patch("src.services.firestore_service.firestore_service.get_user")
    def test_calculate_progress_hub_stats(self, mock_get_user, mock_get_checkins):
        mock_get_user.return_value = _make_user()
        mock_get_checkins.return_value = _make_checkins("12345", count=7, score=100.0)

        stats = calculate_progress_hub_stats("12345", window_key="7d")
        assert stats["window_key"] == "7d"
        assert stats["period_label"] == "Last 7 Days"
        assert stats["checkin_count"] == 7
        assert stats["compliance"]["average"] == 100.0
        assert stats["streaks"]["current"] == 10

    def test_format_progress_hub_and_keyboard(self):
        user = _make_user()
        stats = {
            "has_data": True,
            "user": user,
            "window_key": "30d",
            "period_label": "Last 30 Days",
            "streaks": {"current": 12, "longest": 20},
            "shields": {"available": 3, "total": 3},
            "compliance": {"average": 92.5, "trend": "↑ Improving"},
            "tier1": {
                "sleep": {"pct": 90.0},
                "deep_work": {"pct": 85.0},
                "skill_building": {"pct": 75.0},
                "training": {"pct": 80.0},
                "zero_porn": {"pct": 100.0},
                "boundaries": {"pct": 100.0},
            },
            "say_do_ratio": 95.0,
            "achievements_count": 8,
        }
        text = format_progress_hub(stats)
        assert "EXECUTIVE PERFORMANCE HUB" in text
        assert "12" in text
        assert "92.5%" in text

        kb = get_progress_keyboard(current_window="30d")
        assert kb is not None
        button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
        assert "• 30 Days •" in button_texts

    @pytest.mark.asyncio
    @patch("src.services.firestore_service.firestore_service.get_user")
    @patch("src.services.firestore_service.firestore_service.get_recent_checkins")
    async def test_progress_command_and_callback(self, mock_checkins, mock_user):
        from src.bot.telegram_bot import TelegramBotManager
        mock_user.return_value = _make_user()
        mock_checkins.return_value = _make_checkins()

        bot = TelegramBotManager.__new__(TelegramBotManager)
        
        # Test command
        update = MagicMock(spec=Update)
        update.effective_user.id = 12345
        update.message = AsyncMock(spec=Message)
        update.callback_query = None
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.args = ["7d"]

        await bot.progress_command(update, context)
        update.message.reply_text.assert_awaited_once()

        # Test callback query
        cb_update = MagicMock(spec=Update)
        cb_query = AsyncMock(spec=CallbackQuery)
        cb_query.data = "progress_win_30d"
        cb_query.from_user.id = 12345
        cb_update.callback_query = cb_query

        await bot.progress_callback(cb_update, context)
        cb_query.answer.assert_awaited_once()
        cb_query.edit_message_text.assert_awaited_once()


# =========================================================================
# 2. Settings Panel Tests
# =========================================================================

class TestSettingsPanel:
    """Test settings control panel and interactive toggles."""

    def test_format_settings_panel_and_keyboard(self):
        user = _make_user()
        text = format_settings_panel(user)
        assert "ACCOUNT & PREFERENCES" in text
        assert "Standard" in text
        assert "America/New_York" in text

        kb = get_settings_keyboard(user)
        button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("Briefing" in t for t in button_texts)
        assert any("Timezone" in t for t in button_texts)

    @pytest.mark.asyncio
    @patch("src.services.firestore_service.firestore_service.get_user")
    @patch("src.services.firestore_service.firestore_service.update_user")
    async def test_settings_briefing_toggle_callback(self, mock_update, mock_get_user):
        from src.bot.telegram_bot import TelegramBotManager
        user = _make_user()
        mock_get_user.return_value = user

        bot = TelegramBotManager.__new__(TelegramBotManager)
        cb_update = MagicMock(spec=Update)
        cb_query = AsyncMock(spec=CallbackQuery)
        cb_query.data = "settings_action_briefing_toggle"
        cb_query.from_user.id = 12345
        cb_update.callback_query = cb_query
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await bot.settings_callback(cb_update, context)
        cb_query.answer.assert_awaited_once()
        mock_update.assert_called_once()
        cb_query.edit_message_text.assert_awaited_once()


# =========================================================================
# 3. Goals Studio Tests
# =========================================================================

class TestGoalsStudio:
    """Test SMART goals studio and 1-tap template presets."""

    def test_format_goals_studio_empty(self):
        text = format_goals_studio([])
        assert "ACTIVE GOALS STUDIO" in text
        assert "No active goals" in text

    @pytest.mark.asyncio
    @patch("src.services.firestore_service.firestore_service.get_user")
    @patch("src.services.goal_service.goal_service.create_goal")
    @patch("src.services.goal_service.goal_service.get_user_goals")
    async def test_goals_callback_preset_creation(self, mock_get_goals, mock_create, mock_get_user):
        from src.bot.telegram_bot import TelegramBotManager
        mock_get_user.return_value = _make_user()
        mock_get_goals.return_value = []

        bot = TelegramBotManager.__new__(TelegramBotManager)
        cb_update = MagicMock(spec=Update)
        cb_query = AsyncMock(spec=CallbackQuery)
        cb_query.data = "goal_tpl_sleep_14"
        cb_query.from_user.id = 12345
        cb_update.callback_query = cb_query
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await bot.goals_callback(cb_update, context)
        cb_query.answer.assert_awaited_once()
        mock_create.assert_called_once_with(
            user_id="12345", category="sleep", target_days=14, title="14-Day Sleep Master (7h+)"
        )
        cb_query.edit_message_text.assert_awaited_once()


# =========================================================================
# 4. Partner Arena Tests
# =========================================================================

class TestPartnerArena:
    """Test Partner Arena dashboard and duel launcher."""

    def test_format_partner_arena_linked(self):
        text = format_partner_arena(
            user_name="Alex",
            partner_name="Jordan",
            user_streak=10,
            partner_streak=8,
            user_compliance=95.0,
            partner_compliance=90.0,
            partner_checked_in_today=True,
            challenges=[]
        )
        assert "ACCOUNTABILITY PARTNER ARENA" in text
        assert "Jordan" in text
        assert "10d" in text
        assert "Checked in" in text

    def test_get_partner_keyboard_unlinked(self):
        kb = get_partner_keyboard(has_partner=False)
        button_texts = [btn.text for row in kb.inline_keyboard for btn in row]
        assert any("Link Partner" in t for t in button_texts)

    @pytest.mark.asyncio
    @patch("src.services.firestore_service.firestore_service.get_user")
    @patch("src.services.challenge_service.challenge_service.create_challenge")
    async def test_partner_duel_creation(self, mock_create_ch, mock_get_user):
        from src.bot.telegram_bot import TelegramBotManager
        user = _make_user(partner_id="67890")
        partner = _make_user(user_id="67890", name="Jordan")
        
        def user_side_effect(uid):
            return user if uid == "12345" else partner
        mock_get_user.side_effect = user_side_effect

        mock_challenge = MagicMock()
        mock_challenge.challenge_id = "duel_123"
        mock_create_ch.return_value = mock_challenge

        bot = TelegramBotManager.__new__(TelegramBotManager)
        cb_update = MagicMock(spec=Update)
        cb_query = AsyncMock(spec=CallbackQuery)
        cb_query.data = "duel_start_sleep"
        cb_query.from_user.id = 12345
        cb_update.callback_query = cb_query
        
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.bot = AsyncMock()

        await bot.partner_hub_callback(cb_update, context)
        cb_query.answer.assert_awaited_once()
        mock_create_ch.assert_called_once()
        cb_query.edit_message_text.assert_awaited_once()


# =========================================================================
# 5. Today Master Daily Driver Tests
# =========================================================================

class TestTodayHub:
    """Test /today command master daily driver."""

    @pytest.mark.asyncio
    @patch("src.services.firestore_service.firestore_service.get_user")
    @patch("src.services.firestore_service.firestore_service.checkin_exists")
    @patch("src.services.task_service.task_service.get_daily_tasks")
    async def test_today_command_pending_checkin(self, mock_tasks, mock_checkin_exists, mock_get_user):
        from src.bot.telegram_bot import TelegramBotManager
        mock_get_user.return_value = _make_user()
        mock_checkin_exists.return_value = False
        mock_tasks.return_value = None

        bot = TelegramBotManager.__new__(TelegramBotManager)
        update = MagicMock(spec=Update)
        update.effective_user.id = 12345
        update.message = AsyncMock(spec=Message)
        update.callback_query = None
        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)

        await bot.today_command(update, context)
        update.message.reply_text.assert_awaited_once()
        call_args = update.message.reply_text.call_args[0][0]
        assert "TODAY'S FOCUS & DAILY DRIVER" in call_args
        assert "Daily Check-In Pending" in call_args


# =========================================================================
# 6. Executive Help Tests
# =========================================================================

class TestExecutiveHelp:
    """Test executive help text generation."""

    def test_executive_help_text_structure(self):
        help_text = generate_executive_help_text()
        assert "CONSTITUTION AGENT — COMMAND DIRECTORY" in help_text
        assert "/today" in help_text
        assert "/progress" in help_text
        assert "/partner" in help_text
        assert "/goals" in help_text
        assert "/settings" in help_text
        assert "/support" in help_text


# =========================================================================
# 7. Checkin Predictive Baseline Tests
# =========================================================================

class TestCheckinPredictiveBaseline:
    """Test predictive baseline computation for honest check-in defaults."""

    @patch("src.services.firestore_service.firestore_service.get_user")
    @patch("src.services.firestore_service.firestore_service.get_recent_checkins")
    @patch("src.services.task_service.task_service.get_daily_tasks")
    def test_compute_predictive_baseline_with_history(self, mock_tasks, mock_checkins, mock_user):
        mock_user.return_value = _make_user()
        mock_checkins.return_value = [
            DailyCheckIn(
                date="2026-08-20",
                user_id="12345",
                mode="standard",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep_hours=7.0,
                    deep_work_hours=2.0,
                    training=True,
                    training_intensity="moderate",
                    zero_porn=True,
                    boundaries=True,
                ),
                responses=_make_responses(),
                compliance_score=100.0,
            ),
            DailyCheckIn(
                date="2026-08-21",
                user_id="12345",
                mode="standard",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep_hours=8.0,
                    deep_work_hours=3.0,
                    training=True,
                    training_intensity="moderate",
                    zero_porn=True,
                    boundaries=True,
                ),
                responses=_make_responses(),
                compliance_score=80.0,
            )
        ]
        mock_tasks.return_value = None

        baseline = compute_predictive_baseline("12345", "2026-08-22")
        assert baseline["sleep_hours"] == 7.5
        assert baseline["deep_work_hours"] == 2.0  # capped at 2.0
        assert baseline["training_intensity"] == "moderate"
        assert baseline["zero_porn"] is True
        assert baseline["boundaries"] is True

    @patch("src.services.firestore_service.firestore_service.get_user")
    @patch("src.services.firestore_service.firestore_service.get_recent_checkins")
    @patch("src.services.task_service.task_service.get_daily_tasks")
    def test_compute_predictive_baseline_cold_start(self, mock_tasks, mock_checkins, mock_user):
        mock_user.return_value = _make_user()
        mock_checkins.return_value = []
        mock_tasks.return_value = None

        baseline = compute_predictive_baseline("12345", "2026-08-22")
        assert baseline["sleep_hours"] == 6.5
        assert baseline["deep_work_hours"] == 1.0
        assert baseline["training_intensity"] == "rest"
        assert baseline["zero_porn"] is True
        assert baseline["boundaries"] is True
