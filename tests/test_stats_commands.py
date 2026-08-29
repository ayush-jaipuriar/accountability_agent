"""
Tests for src/bot/stats_commands.py
====================================
Tests /weekly, /monthly, /yearly command handlers and message formatters.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from telegram import Update, User as TgUser, Message
from telegram.ext import ContextTypes

from src.bot.stats_commands import (
    weekly_command,
    monthly_command,
    yearly_command,
    format_weekly_summary,
    format_monthly_summary,
    format_yearly_summary,
    get_emoji_for_trend,
    get_encouragement,
)
from src.models.schemas import User, UserStreaks


@pytest.fixture
def mock_update():
    update = MagicMock(spec=Update)
    user = MagicMock(spec=TgUser)
    user.id = 123456
    user.first_name = "Alex"
    user.username = "alex_test"
    update.effective_user = user

    message = AsyncMock(spec=Message)
    message.reply_text = AsyncMock()
    update.message = message
    return update


@pytest.fixture
def mock_context():
    return MagicMock(spec=ContextTypes.DEFAULT_TYPE)


@pytest.fixture
def sample_user():
    return User(
        user_id="123456",
        telegram_id=123456,
        telegram_username="alex_test",
        name="Alex",
        streaks=UserStreaks(current_streak=10, longest_streak=15),
    )


@pytest.fixture
def sample_weekly_stats():
    return {
        "has_data": True,
        "period": "Last 7 Days",
        "date_range": "Feb 10 - Feb 16",
        "compliance": {
            "average": 88.5,
            "trend": "↗️ +5%",
        },
        "streaks": {
            "current": 10,
            "checkin_rate": "7/7",
            "completion_pct": 100.0,
        },
        "tier1": {
            "sleep": {"days": 6, "total": 7, "avg_hours": 7.4},
            "training": {"days": 5, "total": 7},
            "deep_work": {"days": 5, "total": 7, "avg_hours": 2.5},
            "skill_building": {"days": 6, "total": 7},
            "zero_porn": {"days": 7, "total": 7, "pct": 100.0},
            "boundaries": {"days": 7, "total": 7},
        },
        "patterns": {
            "message": "No negative patterns detected ✅",
        },
    }


@pytest.fixture
def sample_monthly_stats():
    return {
        "has_data": True,
        "period": "Last 30 Days",
        "date_range": "Jan 18 - Feb 16",
        "compliance": {
            "average": 82.0,
            "best_week": "Week 2 (92%)",
            "worst_week": "Week 1 (71%)",
        },
        "streaks": {
            "current": 10,
            "longest_this_month": 12,
            "checkin_rate": "28/30",
            "completion_pct": 93.3,
        },
        "tier1": {
            "sleep": {"avg_hours": 7.2, "target": 7.0},
            "training": {"pct": 80.0, "days": 24, "total": 30},
            "deep_work": {"avg_hours": 2.1, "target": 2.0},
            "skill_building": {"avg_hours": 1.2},
            "zero_porn": {"pct": 96.7, "days": 29, "total": 30},
            "boundaries": {"pct": 90.0},
        },
        "achievements": {
            "count": 2,
            "list": ["Week Warrior", "Double Digits"],
        },
        "patterns": {
            "count": 1,
            "message": "Late night sleep detected on weekends",
        },
        "social_proof": {
            "message": "Top 15% of all users this month! 🏆",
        },
    }


@pytest.fixture
def sample_yearly_stats():
    return {
        "has_data": True,
        "period": "2026 Year to Date",
        "date_range": "Jan 1 - Feb 16",
        "overview": {
            "days_tracked": 45,
            "total_days": 47,
            "completion_pct": 95.7,
            "avg_compliance": 85.0,
        },
        "streaks": {
            "current": 10,
            "longest_this_year": 20,
            "total_checkins": 45,
        },
        "monthly_breakdown": [
            {"month": "Jan", "days": 30, "total_days": 31, "avg_compliance": "86%"},
            {"month": "Feb", "days": 15, "total_days": 16, "avg_compliance": "84%"},
        ],
        "achievements": {
            "total": 5,
            "message": "unlocked in 2026 🏆",
        },
        "patterns": {
            "total": 2,
            "message": "identified & resolved 🛡️",
        },
        "career_progress": {
            "consistency_pct": 88.0,
            "skill_building_days": 40,
            "career_mode": "skill_building",
            "target_date": "Dec 2026",
            "target_salary": "k",
        },
    }


class TestWeeklyCommand:

    @pytest.mark.asyncio
    async def test_weekly_command_user_not_found(self, mock_update, mock_context):
        with patch("src.bot.stats_commands.firestore_service.get_user", return_value=None):
            await weekly_command(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            assert "Please use /start" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_weekly_command_no_data(self, mock_update, mock_context, sample_user):
        with patch("src.bot.stats_commands.firestore_service.get_user", return_value=sample_user),              patch("src.bot.stats_commands.calculate_weekly_stats", return_value={"has_data": False, "error": "No check-ins"}):
            await weekly_command(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            assert "No check-in data available" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_weekly_command_success(self, mock_update, mock_context, sample_user, sample_weekly_stats):
        with patch("src.bot.stats_commands.firestore_service.get_user", return_value=sample_user),              patch("src.bot.stats_commands.calculate_weekly_stats", return_value=sample_weekly_stats):
            await weekly_command(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            text = mock_update.message.reply_text.call_args[0][0]
            assert "Last 7 Days" in text
            assert "88%" in text or "89%" in text

    @pytest.mark.asyncio
    async def test_weekly_command_exception(self, mock_update, mock_context):
        with patch("src.bot.stats_commands.firestore_service.get_user", side_effect=Exception("DB Error")):
            await weekly_command(mock_update, mock_context)
            mock_update.message.reply_text.assert_called_once()
            assert "couldn't calculate your weekly stats" in mock_update.message.reply_text.call_args[0][0]


class TestMonthlyCommand:

    @pytest.mark.asyncio
    async def test_monthly_command_user_not_found(self, mock_update, mock_context):
        with patch("src.bot.stats_commands.firestore_service.get_user", return_value=None):
            await monthly_command(mock_update, mock_context)
            assert "Please use /start" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_monthly_command_no_data(self, mock_update, mock_context, sample_user):
        with patch("src.bot.stats_commands.firestore_service.get_user", return_value=sample_user),              patch("src.bot.stats_commands.calculate_monthly_stats", return_value={"has_data": False}):
            await monthly_command(mock_update, mock_context)
            assert "No check-in data available" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_monthly_command_success(self, mock_update, mock_context, sample_user, sample_monthly_stats):
        with patch("src.bot.stats_commands.firestore_service.get_user", return_value=sample_user),              patch("src.bot.stats_commands.calculate_monthly_stats", return_value=sample_monthly_stats):
            await monthly_command(mock_update, mock_context)
            text = mock_update.message.reply_text.call_args[0][0]
            assert "Last 30 Days" in text
            assert "82%" in text

    @pytest.mark.asyncio
    async def test_monthly_command_exception(self, mock_update, mock_context):
        with patch("src.bot.stats_commands.firestore_service.get_user", side_effect=Exception("DB Error")):
            await monthly_command(mock_update, mock_context)
            assert "couldn't calculate your monthly stats" in mock_update.message.reply_text.call_args[0][0]


class TestYearlyCommand:

    @pytest.mark.asyncio
    async def test_yearly_command_user_not_found(self, mock_update, mock_context):
        with patch("src.bot.stats_commands.firestore_service.get_user", return_value=None):
            await yearly_command(mock_update, mock_context)
            assert "Please use /start" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_yearly_command_no_data(self, mock_update, mock_context, sample_user):
        with patch("src.bot.stats_commands.firestore_service.get_user", return_value=sample_user),              patch("src.bot.stats_commands.calculate_yearly_stats", return_value={"has_data": False}):
            await yearly_command(mock_update, mock_context)
            assert "No check-in data available" in mock_update.message.reply_text.call_args[0][0]

    @pytest.mark.asyncio
    async def test_yearly_command_success(self, mock_update, mock_context, sample_user, sample_yearly_stats):
        with patch("src.bot.stats_commands.firestore_service.get_user", return_value=sample_user),              patch("src.bot.stats_commands.calculate_yearly_stats", return_value=sample_yearly_stats):
            await yearly_command(mock_update, mock_context)
            text = mock_update.message.reply_text.call_args[0][0]
            assert "Year to Date" in text
            assert "85%" in text

    @pytest.mark.asyncio
    async def test_yearly_command_exception(self, mock_update, mock_context):
        with patch("src.bot.stats_commands.firestore_service.get_user", side_effect=Exception("DB Error")):
            await yearly_command(mock_update, mock_context)
            assert "couldn't calculate your yearly stats" in mock_update.message.reply_text.call_args[0][0]


class TestFormatters:

    def test_format_weekly_summary_perfect_porn(self, sample_weekly_stats):
        sample_weekly_stats["compliance"]["average"] = 92.0
        text = format_weekly_summary(sample_weekly_stats)
        assert "Outstanding week" in text
        assert "Zero Porn: 7/7 days ✅" in text

    def test_format_weekly_summary_imperfect_porn(self, sample_weekly_stats):
        sample_weekly_stats["tier1"]["zero_porn"]["pct"] = 80.0
        sample_weekly_stats["tier1"]["zero_porn"]["days"] = 5
        sample_weekly_stats["compliance"]["average"] = 65.0
        text = format_weekly_summary(sample_weekly_stats)
        assert "Zero Porn: 5/7 days ⚠️" in text
        assert "fresh start" in text

    def test_format_weekly_summary_brackets(self, sample_weekly_stats):
        sample_weekly_stats["compliance"]["average"] = 82.0
        assert "Strong week" in format_weekly_summary(sample_weekly_stats)

        sample_weekly_stats["compliance"]["average"] = 75.0
        assert "Good progress" in format_weekly_summary(sample_weekly_stats)

    def test_format_monthly_summary(self, sample_monthly_stats):
        text = format_monthly_summary(sample_monthly_stats)
        assert "Week Warrior" in text
        assert "Double Digits" in text
        assert "Top 15%" in text

    def test_format_monthly_summary_no_achievements(self, sample_monthly_stats):
        sample_monthly_stats["achievements"] = {"count": 0, "list": []}
        sample_monthly_stats["patterns"] = {"count": 0, "message": "All habits consistent"}
        sample_monthly_stats["tier1"]["zero_porn"]["pct"] = 100.0
        text = format_monthly_summary(sample_monthly_stats)
        assert "Achievements Unlocked" not in text
        assert "Zero Porn: 100% ✅" in text

    def test_format_yearly_summary_modes(self, sample_yearly_stats):
        sample_yearly_stats["career_progress"]["career_mode"] = "job_searching"
        text = format_yearly_summary(sample_yearly_stats)
        assert "Job Searching" in text

        sample_yearly_stats["career_progress"]["career_mode"] = "employed"
        text = format_yearly_summary(sample_yearly_stats)
        assert "Employed" in text


class TestHelpers:

    def test_get_emoji_for_trend(self):
        assert get_emoji_for_trend("improving") == "↗️"
        assert get_emoji_for_trend("declining") == "↘️"
        assert get_emoji_for_trend("stable") == "→"
        assert get_emoji_for_trend("other") == "→"

    def test_get_encouragement(self):
        assert "Exceptional" in get_encouragement(96)
        assert "Outstanding" in get_encouragement(91)
        assert "Strong work" in get_encouragement(86)
        assert "Solid progress" in get_encouragement(81)
        assert "Good effort" in get_encouragement(72)
        assert "Making progress" in get_encouragement(62)
        assert "fresh start" in get_encouragement(50)
