"""
Conversation Flow Tests
========================

Tests the multi-step check-in conversation handler including:
- /checkin entry (new, existing, already checked in)
- /quickcheckin entry + weekly limits
- Tier 1 button responses + undo
- Q2 challenges validation
- Q3 rating validation
- Q4 tomorrow plan parsing
- Cancel / timeout
- get_skill_building_question career mode adaptation
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from telegram.ext import ConversationHandler

from src.models.schemas import User, UserStreaks
from src.bot.conversation import (
    Q1_TIER1, Q2_CHALLENGES, Q3_RATING, Q4_TOMORROW,
    get_skill_building_question,
    start_checkin,
    handle_tier1_response,
    handle_challenges_response,
    handle_rating_response,
    handle_tomorrow_response,
    cancel_checkin,
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


def _make_callback_update(data="sleep_yes"):
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


# =============================================
# get_skill_building_question Tests
# =============================================

class TestGetSkillBuildingQuestion:
    """Tests career mode adaptive question logic."""

    def test_skill_building_mode(self):
        q = get_skill_building_question("skill_building")
        assert "Skill Building" in q["question"]
        assert "LeetCode" in q["description"]

    def test_job_searching_mode(self):
        q = get_skill_building_question("job_searching")
        assert "Job Search" in q["question"]
        assert "Applications" in q["description"]

    def test_employed_mode(self):
        q = get_skill_building_question("employed")
        assert "Career" in q["question"] or "promotion" in q["question"].lower()
        assert "promotion" in q["description"].lower() or "High-impact" in q["description"]

    def test_unknown_mode_fallback(self):
        q = get_skill_building_question("unknown_mode")
        assert "Skill Building" in q["question"]

    def test_returns_required_keys(self):
        for mode in ["skill_building", "job_searching", "employed"]:
            q = get_skill_building_question(mode)
            assert "question" in q
            assert "label" in q
            assert "description" in q


# =============================================
# start_checkin Tests
# =============================================

class TestStartCheckin:

    @pytest.mark.asyncio
    async def test_user_not_found(self):
        update = _make_update()
        context = _make_context()
        with patch('src.bot.conversation.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = None
            result = await start_checkin(update, context)
        assert result == ConversationHandler.END
        text = update.message.reply_text.call_args[0][0]
        assert "/start" in text

    @pytest.mark.asyncio
    async def test_already_checked_in_today(self):
        user = _make_user()
        update = _make_update()
        context = _make_context()
        with patch('src.bot.conversation.firestore_service') as mock_fs, \
             patch('src.bot.conversation.get_checkin_date',
                   return_value="2026-02-07"):
            mock_fs.get_user.return_value = user
            mock_fs.checkin_exists.return_value = True
            result = await start_checkin(update, context)
        assert result == ConversationHandler.END
        text = update.message.reply_text.call_args[0][0]
        assert "already" in text.lower()

    @pytest.mark.asyncio
    async def test_full_checkin_starts(self):
        user = _make_user()
        update = _make_update(text="/checkin")
        context = _make_context(user_data={})
        with patch('src.bot.conversation.firestore_service') as mock_fs, \
             patch('src.bot.conversation.get_checkin_date',
                   return_value="2026-02-07"):
            mock_fs.get_user.return_value = user
            mock_fs.checkin_exists.return_value = False
            result = await start_checkin(update, context)
        assert result == Q1_TIER1
        assert context.user_data.get('checkin_type') == 'full'

    @pytest.mark.asyncio
    async def test_quick_checkin_starts(self):
        user = _make_user(quick_checkin_count=0)
        update = _make_update(text="/quickcheckin")
        context = _make_context(user_data={})
        with patch('src.bot.conversation.firestore_service') as mock_fs, \
             patch('src.bot.conversation.get_checkin_date',
                   return_value="2026-02-07"):
            mock_fs.get_user.return_value = user
            mock_fs.checkin_exists.return_value = False
            result = await start_checkin(update, context)
        assert result == Q1_TIER1
        assert context.user_data.get('checkin_type') == 'quick'

    @pytest.mark.asyncio
    async def test_quick_checkin_limit_reached(self):
        user = _make_user(quick_checkin_count=2,
                          quick_checkin_used_dates=["2026-02-05", "2026-02-06"])
        update = _make_update(text="/quickcheckin")
        context = _make_context(user_data={})
        with patch('src.bot.conversation.firestore_service') as mock_fs, \
             patch('src.bot.conversation.get_checkin_date',
                   return_value="2026-02-07"):
            mock_fs.get_user.return_value = user
            mock_fs.get_checkin.return_value = None
            result = await start_checkin(update, context)
        assert result == ConversationHandler.END
        text = update.message.reply_text.call_args[0][0]
        assert "Limit Reached" in text or "limit" in text.lower()


# =============================================
# handle_tier1_response Tests
# =============================================

class TestHandleTier1Response:

    @pytest.mark.asyncio
    async def test_single_answer_stays_in_q1(self):
        update = _make_callback_update(data="sleep_yes")
        context = _make_context(user_data={
            'user_id': '111',
            'tier1_responses': {},
            'tier1_answer_order': [],
        })
        result = await handle_tier1_response(update, context)
        assert result == Q1_TIER1
        assert context.user_data['tier1_responses']['sleep'] is True

    @pytest.mark.asyncio
    async def test_all_six_answered_moves_to_q2(self):
        update = _make_callback_update(data="boundaries_yes")
        context = _make_context(user_data={
            'user_id': '111',
            'checkin_type': 'full',
            'tier1_responses': {
                'sleep': True, 'training': True, 'deepwork': True,
                'skillbuilding': True, 'porn': True
            },
            'tier1_answer_order': ['sleep', 'training', 'deepwork',
                                   'skillbuilding', 'porn'],
        })
        result = await handle_tier1_response(update, context)
        assert result == Q2_CHALLENGES

    @pytest.mark.asyncio
    async def test_undo_removes_last_answer(self):
        update = _make_callback_update(data="tier1_undo")
        context = _make_context(user_data={
            'user_id': '111',
            'tier1_responses': {'sleep': True, 'training': False},
            'tier1_answer_order': ['sleep', 'training'],
        })
        result = await handle_tier1_response(update, context)
        assert result == Q1_TIER1
        assert 'training' not in context.user_data['tier1_responses']
        assert len(context.user_data['tier1_answer_order']) == 1

    @pytest.mark.asyncio
    async def test_undo_empty_does_nothing(self):
        update = _make_callback_update(data="tier1_undo")
        context = _make_context(user_data={
            'user_id': '111',
            'tier1_responses': {},
            'tier1_answer_order': [],
        })
        result = await handle_tier1_response(update, context)
        assert result == Q1_TIER1


# =============================================
# handle_challenges_response Tests
# =============================================

class TestHandleChallengesResponse:

    @pytest.mark.asyncio
    async def test_valid_challenge(self):
        update = _make_update(text="Had difficulty staying focused during deep work session today")
        context = _make_context()
        result = await handle_challenges_response(update, context)
        assert result == Q3_RATING
        assert context.user_data['challenges'] is not None

    @pytest.mark.asyncio
    async def test_too_short(self):
        update = _make_update(text="ok")
        context = _make_context()
        result = await handle_challenges_response(update, context)
        assert result == Q2_CHALLENGES

    @pytest.mark.asyncio
    async def test_too_long(self):
        update = _make_update(text="x" * 501)
        context = _make_context()
        result = await handle_challenges_response(update, context)
        assert result == Q2_CHALLENGES


# =============================================
# handle_rating_response Tests
# =============================================

class TestHandleRatingResponse:

    @pytest.mark.asyncio
    async def test_valid_rating(self):
        update = _make_update(text="8 - Solid day, hit all targets except skill building which was short")
        context = _make_context()
        result = await handle_rating_response(update, context)
        assert result == Q4_TOMORROW
        assert context.user_data['rating'] == 8

    @pytest.mark.asyncio
    async def test_no_number(self):
        update = _make_update(text="great day overall felt strong")
        context = _make_context()
        result = await handle_rating_response(update, context)
        assert result == Q3_RATING

    @pytest.mark.asyncio
    async def test_out_of_range(self):
        update = _make_update(text="15 - amazing day")
        context = _make_context()
        result = await handle_rating_response(update, context)
        assert result == Q3_RATING

    @pytest.mark.asyncio
    async def test_reason_too_short(self):
        update = _make_update(text="7 ok")
        context = _make_context()
        result = await handle_rating_response(update, context)
        assert result == Q3_RATING


# =============================================
# handle_tomorrow_response Tests
# =============================================

class TestHandleTomorrowResponse:

    @pytest.mark.asyncio
    async def test_valid_response_no_delimiter(self):
        update = _make_update(
            text="Focus on completing three LeetCode problems and study system design patterns"
        )
        context = _make_context(user_data={
            'user_id': '111',
            'date': '2026-02-07',
            'mode': 'maintenance',
            'checkin_start_time': datetime.utcnow(),
            'tier1_responses': {
                'sleep': True, 'training': True, 'deepwork': True,
                'skillbuilding': True, 'porn': True, 'boundaries': True
            },
            'challenges': 'Test challenges text here for validation',
            'rating': 8,
            'rating_reason': 'Solid day overall with good consistency',
            'tomorrow_priority': '',
            'tomorrow_obstacle': '',
        })

        with patch('src.bot.conversation.finish_checkin', new_callable=AsyncMock):
            result = await handle_tomorrow_response(update, context)
        assert result == ConversationHandler.END

    @pytest.mark.asyncio
    async def test_valid_response_with_delimiter(self):
        update = _make_update(
            text="Priority: Complete 3 LeetCode problems | Obstacle: Evening meeting might drain energy"
        )
        context = _make_context(user_data={
            'user_id': '111',
            'date': '2026-02-07',
            'mode': 'maintenance',
            'checkin_start_time': datetime.utcnow(),
            'tier1_responses': {
                'sleep': True, 'training': True, 'deepwork': True,
                'skillbuilding': True, 'porn': True, 'boundaries': True
            },
            'challenges': 'Test challenges text here for validation',
            'rating': 8,
            'rating_reason': 'Solid day overall with good consistency',
            'tomorrow_priority': '',
            'tomorrow_obstacle': '',
        })

        with patch('src.bot.conversation.finish_checkin', new_callable=AsyncMock):
            result = await handle_tomorrow_response(update, context)
        assert result == ConversationHandler.END
        assert "LeetCode" in context.user_data['tomorrow_priority']

    @pytest.mark.asyncio
    async def test_too_short(self):
        update = _make_update(text="ok")
        context = _make_context()
        result = await handle_tomorrow_response(update, context)
        assert result == Q4_TOMORROW

    @pytest.mark.asyncio
    async def test_too_long(self):
        update = _make_update(text="x" * 501)
        context = _make_context()
        result = await handle_tomorrow_response(update, context)
        assert result == Q4_TOMORROW


# =============================================
# cancel_checkin Tests
# =============================================

class TestCancelCheckin:

    @pytest.mark.asyncio
    async def test_cancel_ends_conversation(self):
        update = _make_update(text="/cancel")
        context = _make_context()
        result = await cancel_checkin(update, context)
        assert result == ConversationHandler.END
        text = update.message.reply_text.call_args[0][0]
        assert "cancelled" in text.lower()


# =============================================
# Quick Check-in All-6-Answered Path
# =============================================

class TestQuickCheckinPath:
    """When all 6 Tier1 items answered during quick checkin, it should
    skip Q2-Q4 and call finish_checkin_quick instead."""

    @pytest.mark.asyncio
    async def test_quick_checkin_skips_q2_q4(self):
        update = _make_callback_update(data="boundaries_yes")
        context = _make_context(user_data={
            'user_id': '111',
            'checkin_type': 'quick',
            'tier1_responses': {
                'sleep': True, 'training': True, 'deepwork': True,
                'skillbuilding': True, 'porn': True
            },
            'tier1_answer_order': ['sleep', 'training', 'deepwork',
                                   'skillbuilding', 'porn'],
        })

        with patch('src.bot.conversation.finish_checkin_quick',
                   new_callable=AsyncMock) as mock_finish:
            result = await handle_tier1_response(update, context)

        assert result == ConversationHandler.END
        mock_finish.assert_called_once()
