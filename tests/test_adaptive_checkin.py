"""
Tests for P1.3: Adaptive Check-In Flow
========================================

Tests the adaptive features:
- Power user detection (streak >= 30, avg compliance >= 85%)
- Struggling user empathetic framing (< 60% compliance)
- Perfect-day Q2 skip (100% compliance)
- "Answer Anyway" button on perfect days
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from telegram.ext import ConversationHandler

from src.models.schemas import (
    User, UserStreaks, Tier1NonNegotiables, CheckInResponses, DailyCheckIn
)
from src.bot.conversation import (
    Q1_TIER1, Q2_CHALLENGES, Q4_TOMORROW,
    start_checkin,
    handle_tier1_response,
)


# ===== Helpers =====

def _make_user(**overrides) -> User:
    defaults = dict(
        user_id="111",
        telegram_id=111,
        telegram_username="testuser",
        name="TestUser",
        timezone="Asia/Kolkata",
        constitution_mode="maintenance",
        career_mode="skill_building",
        streaks=UserStreaks(
            current_streak=10, longest_streak=20,
            last_checkin_date="2026-02-06", total_checkins=50
        ),
        quick_checkin_count=0,
        quick_checkin_used_dates=[],
    )
    defaults.update(overrides)
    return User(**defaults)


def _make_update(user_id=111, text="/checkin"):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.message = AsyncMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    return update


def _make_callback_update(data="tier1_sleep_hours_7.5"):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = 111
    query = AsyncMock()
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    query.message = AsyncMock()
    query.message.reply_text = AsyncMock()
    update.callback_query = query
    update.message = None
    return update


def _make_context(user_data=None):
    context = MagicMock()
    context.user_data = user_data if user_data is not None else {}
    context.bot = AsyncMock()
    return context


def _make_checkin(compliance=80.0, date="2026-02-06"):
    return DailyCheckIn(
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
            tomorrow_priority="Continue focus on main priorities tomorrow",
            tomorrow_obstacle="Potential distractions from various meetings",
        ),
        compliance_score=compliance,
    )


# ===== Power User Detection =====

class TestPowerUserDetection:

    @pytest.mark.asyncio
    async def test_power_user_mentions_quick_mode(self):
        """Power users (streak >= 30, avg >= 85%) should see quick mode mention."""
        user = _make_user(streaks=UserStreaks(
            current_streak=35, longest_streak=35,
            last_checkin_date="2026-02-06", total_checkins=100
        ))
        update = _make_update(text="/checkin")
        context = _make_context(user_data={})

        checkins = [_make_checkin(compliance=90.0) for _ in range(7)]

        with patch('src.bot.conversation.firestore_service') as mock_fs, \
             patch('src.bot.conversation.get_checkin_date', return_value="2026-02-07"):
            mock_fs.get_user.return_value = user
            mock_fs.checkin_exists.return_value = False
            mock_fs.get_recent_checkins.return_value = checkins
            result = await start_checkin(update, context)

        assert result == Q1_TIER1
        # Should have sent quick mode mention
        calls = [c[0][0] for c in update.message.reply_text.call_args_list]
        assert any("quickcheckin" in c for c in calls), f"Expected quick mode mention in {calls}"

    @pytest.mark.asyncio
    async def test_non_power_user_no_quick_mention(self):
        """Non-power users should NOT see quick mode mention."""
        user = _make_user(streaks=UserStreaks(
            current_streak=10, longest_streak=20,
            last_checkin_date="2026-02-06", total_checkins=50
        ))
        update = _make_update(text="/checkin")
        context = _make_context(user_data={})

        checkins = [_make_checkin(compliance=70.0) for _ in range(7)]

        with patch('src.bot.conversation.firestore_service') as mock_fs, \
             patch('src.bot.conversation.get_checkin_date', return_value="2026-02-07"):
            mock_fs.get_user.return_value = user
            mock_fs.checkin_exists.return_value = False
            mock_fs.get_recent_checkins.return_value = checkins
            result = await start_checkin(update, context)

        assert result == Q1_TIER1
        calls = [c[0][0] for c in update.message.reply_text.call_args_list]
        assert not any("quickcheckin" in c for c in calls), f"Unexpected quick mode mention in {calls}"


# ===== Struggling User Framing =====

class TestStrugglingUserFraming:

    @pytest.mark.asyncio
    async def test_struggling_user_gets_empathy(self):
        """Users with < 60% avg compliance should get empathetic message."""
        user = _make_user(streaks=UserStreaks(
            current_streak=5, longest_streak=10,
            last_checkin_date="2026-02-06", total_checkins=20
        ))
        update = _make_update(text="/checkin")
        context = _make_context(user_data={})

        checkins = [_make_checkin(compliance=50.0) for _ in range(7)]

        with patch('src.bot.conversation.firestore_service') as mock_fs, \
             patch('src.bot.conversation.get_checkin_date', return_value="2026-02-07"):
            mock_fs.get_user.return_value = user
            mock_fs.checkin_exists.return_value = False
            mock_fs.get_recent_checkins.return_value = checkins
            result = await start_checkin(update, context)

        assert result == Q1_TIER1
        calls = [c[0][0] for c in update.message.reply_text.call_args_list]
        assert any("tough" in c.lower() for c in calls), f"Expected empathetic message in {calls}"

    @pytest.mark.asyncio
    async def test_normal_user_no_empathy(self):
        """Users with >= 60% compliance should NOT get empathetic message."""
        user = _make_user(streaks=UserStreaks(
            current_streak=10, longest_streak=20,
            last_checkin_date="2026-02-06", total_checkins=50
        ))
        update = _make_update(text="/checkin")
        context = _make_context(user_data={})

        checkins = [_make_checkin(compliance=80.0) for _ in range(7)]

        with patch('src.bot.conversation.firestore_service') as mock_fs, \
             patch('src.bot.conversation.get_checkin_date', return_value="2026-02-07"):
            mock_fs.get_user.return_value = user
            mock_fs.checkin_exists.return_value = False
            mock_fs.get_recent_checkins.return_value = checkins
            result = await start_checkin(update, context)

        assert result == Q1_TIER1
        calls = [c[0][0] for c in update.message.reply_text.call_args_list]
        assert not any("tough" in c.lower() for c in calls), f"Unexpected empathy in {calls}"


# ===== Perfect Day Q2 Skip =====

class TestPerfectDaySkip:

    @pytest.mark.asyncio
    async def test_perfect_day_offers_skip(self):
        """100% compliance should offer to skip Q2."""
        update = _make_callback_update(data="tier1_boundaries_yes")
        context = _make_context(user_data={
            'user_id': '111',
            'checkin_type': 'full',
            'tier1_step': 5,
            'tier1_data': {
                'sleep_hours': 8.0, 'deep_work_hours': 3.0,
                'skill_building_hours': 2.5, 'training_intensity': 'intense',
                'zero_porn': True
            },
            'tier1_answer_order': ['sleep_hours', 'deep_work_hours',
                                   'skill_building_hours', 'training_intensity', 'zero_porn'],
        })

        result = await handle_tier1_response(update, context)
        assert result == Q1_TIER1  # Stays in Q1 while awaiting skip decision
        assert context.user_data.get('awaiting_q2_skip') is True
        # Should have sent skip offer with inline keyboard
        text = update.callback_query.message.reply_text.call_args[0][0]
        assert "Perfect day" in text or "skip" in text.lower()

    @pytest.mark.asyncio
    async def test_skip_q2_goes_to_q4(self):
        """Clicking 'Skip' should go directly to Q4."""
        update = _make_callback_update(data="skip_q2")
        context = _make_context(user_data={
            'user_id': '111',
            'checkin_type': 'full',
            'awaiting_q2_skip': True,
            'tier1': Tier1NonNegotiables(
                sleep=True, sleep_hours=8.0,
                training=True, training_intensity='intense',
                deep_work=True, deep_work_hours=3.0,
                skill_building=True, skill_building_hours=2.5,
                zero_porn=True, boundaries=True,
            ),
        })

        result = await handle_tier1_response(update, context)
        assert result == Q4_TOMORROW
        assert context.user_data['challenges'] == "Perfect day — skipped challenges question"
        assert context.user_data['rating'] == 10

    @pytest.mark.asyncio
    async def test_answer_anyway_goes_to_q2(self):
        """Clicking 'Answer Anyway' should go to Q2."""
        update = _make_callback_update(data="answer_q2")
        context = _make_context(user_data={
            'user_id': '111',
            'checkin_type': 'full',
            'awaiting_q2_skip': True,
            'tier1': Tier1NonNegotiables(
                sleep=True, sleep_hours=8.0,
                training=True, training_intensity='intense',
                deep_work=True, deep_work_hours=3.0,
                skill_building=True, skill_building_hours=2.5,
                zero_porn=True, boundaries=True,
            ),
        })

        result = await handle_tier1_response(update, context)
        assert result == Q2_CHALLENGES
        assert context.user_data.get('awaiting_q2_skip') is False

    @pytest.mark.asyncio
    async def test_non_perfect_day_no_skip_offer(self):
        """< 100% compliance should NOT offer skip, go straight to Q2."""
        update = _make_callback_update(data="tier1_boundaries_yes")
        context = _make_context(user_data={
            'user_id': '111',
            'checkin_type': 'full',
            'tier1_step': 5,
            'tier1_data': {
                'sleep_hours': 5.5, 'deep_work_hours': 1.0,
                'skill_building_hours': 0.5, 'training_intensity': 'rest',
                'zero_porn': True
            },
            'tier1_answer_order': ['sleep_hours', 'deep_work_hours',
                                   'skill_building_hours', 'training_intensity', 'zero_porn'],
        })

        result = await handle_tier1_response(update, context)
        assert result == Q2_CHALLENGES
        assert context.user_data.get('awaiting_q2_skip') is not True


# ===== Adaptive Context Stored =====

class TestAdaptiveContextStored:

    @pytest.mark.asyncio
    async def test_adaptive_context_stored(self):
        """Adaptive context should be stored in user_data."""
        user = _make_user()
        update = _make_update(text="/checkin")
        context = _make_context(user_data={})

        checkins = [_make_checkin(compliance=80.0) for _ in range(7)]

        with patch('src.bot.conversation.firestore_service') as mock_fs, \
             patch('src.bot.conversation.get_checkin_date', return_value="2026-02-07"):
            mock_fs.get_user.return_value = user
            mock_fs.checkin_exists.return_value = False
            mock_fs.get_recent_checkins.return_value = checkins
            result = await start_checkin(update, context)

        assert result == Q1_TIER1
        assert 'adaptive_context' in context.user_data
        assert context.user_data['adaptive_context']['avg_compliance'] == 80.0
        assert context.user_data['adaptive_context']['recent_count'] == 7


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
