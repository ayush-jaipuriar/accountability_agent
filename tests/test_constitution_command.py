"""
Tests for P2.1: /constitution Command
======================================

Tests the constitution command:
- User not found
- Constitution formatted with stats overlay
- Error handling
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from src.models.schemas import (
    User, UserStreaks, Tier1NonNegotiables, CheckInResponses, DailyCheckIn
)
from src.bot.telegram_bot import TelegramBotManager
from src.services.constitution_service import constitution_service


# ===== Fixtures =====

@pytest.fixture
def mock_bot():
    bot = MagicMock()
    bot.send_message = AsyncMock()
    return bot


@pytest.fixture
def sample_user():
    return User(
        user_id="111",
        telegram_id=111,
        name="TestUser",
        timezone="Asia/Kolkata",
        constitution_mode="maintenance",
        streaks=UserStreaks(
            current_streak=10, longest_streak=20,
            last_checkin_date="2026-02-06", total_checkins=50
        ),
    )


@pytest.fixture
def sample_checkins():
    """7 days of varied check-ins."""
    checkins = []
    for i in range(7):
        date = (datetime(2026, 2, 6) - timedelta(days=6-i)).strftime("%Y-%m-%d")
        checkins.append(DailyCheckIn(
            date=date,
            user_id="111",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=True, training_intensity="moderate",
                deep_work=True, deep_work_hours=2.5,
                skill_building=True, skill_building_hours=2.0,
                zero_porn=True, boundaries=True,
            ),
            responses=CheckInResponses(
                challenges="Test challenges for the day with enough characters",
                rating=8,
                rating_reason="Good day with solid progress made overall",
                tomorrow_priority="Continue working on main priorities",
                tomorrow_obstacle="Potential distractions from meetings",
            ),
            compliance_score=100.0,
        ))
    return checkins


# ===== Constitution Command Tests =====

class TestConstitutionCommand:

    @pytest.mark.asyncio
    async def test_user_not_found(self, mock_bot):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        manager = TelegramBotManager(mock_bot)

        with patch('src.bot.telegram_bot.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = None
            await manager.constitution_command(update, context)

        text = update.message.reply_text.call_args[0][0]
        assert "/start" in text

    @pytest.mark.asyncio
    async def test_constitution_with_stats(self, mock_bot, sample_user, sample_checkins):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        manager = TelegramBotManager(mock_bot)

        with patch('src.bot.telegram_bot.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = sample_user
            mock_fs.get_recent_checkins.return_value = sample_checkins
            await manager.constitution_command(update, context)

        text = update.message.reply_text.call_args[0][0]
        assert "TestUser" in text
        assert "Constitution" in text
        assert "7.5h" in text  # avg sleep
        assert "2.5h" in text  # avg deep work
        assert "100%" in text  # avg compliance
        assert "maintenance" in text.lower()

    @pytest.mark.asyncio
    async def test_constitution_no_checkins(self, mock_bot, sample_user):
        update = MagicMock()
        update.effective_user = MagicMock()
        update.effective_user.id = 111
        update.message = AsyncMock()
        update.message.reply_text = AsyncMock()
        context = MagicMock()

        manager = TelegramBotManager(mock_bot)

        with patch('src.bot.telegram_bot.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = sample_user
            mock_fs.get_recent_checkins.return_value = []
            await manager.constitution_command(update, context)

        text = update.message.reply_text.call_args[0][0]
        assert "TestUser" in text
        assert "Constitution" in text
        # Should show 0.0 for averages when no data


# ===== Constitution Service Tests =====

class TestConstitutionServiceFormatting:

    def test_format_with_high_compliance(self):
        text = constitution_service.format_constitution_with_stats(
            user_name="Ayush",
            current_mode="optimization",
            streak_days=30,
            avg_sleep=8.0,
            avg_deep_work=3.0,
            avg_skill_building=2.5,
            avg_compliance=95.0,
            training_days_this_week=6,
        )
        assert "Ayush" in text
        assert "Optimization" in text
        assert "8.0h" in text
        assert "3.0h" in text
        assert "95%" in text
        assert "🔥" in text  # high compliance emoji
        assert "✅" in text  # met targets

    def test_format_with_low_compliance(self):
        text = constitution_service.format_constitution_with_stats(
            user_name="Ayush",
            current_mode="survival",
            streak_days=2,
            avg_sleep=5.5,
            avg_deep_work=0.5,
            avg_skill_building=0.0,
            avg_compliance=45.0,
            training_days_this_week=1,
        )
        assert "Ayush" in text
        assert "Survival" in text
        assert "⚠️" in text  # low compliance emoji

    def test_format_includes_crisis_protocols(self):
        text = constitution_service.format_constitution_with_stats(
            user_name="Ayush",
            current_mode="maintenance",
            streak_days=10,
            avg_sleep=7.0,
            avg_deep_work=2.0,
            avg_skill_building=1.5,
            avg_compliance=80.0,
            training_days_this_week=4,
        )
        assert "Crisis Protocols" in text
        assert "Ghosting" in text or "Sleep Crisis" in text


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
