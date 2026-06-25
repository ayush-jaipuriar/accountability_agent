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

from src.models.schemas import User, UserStreaks, Tier1NonNegotiables
from src.bot.conversation import (
    Q1_TIER1, Q2_ALIGNMENT_RATING, Q3_ENERGY_MOOD, Q4_REFLECTION_NOTE,
    get_skill_building_question,
    start_checkin,
    handle_tier1_response,
    handle_alignment_rating_callback,
    handle_reflection_response,
    handle_reflection_skip_callback,
    handle_voice_reflection,
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
        update = _make_callback_update(data="tier1_sleep_hours_7.5")
        context = _make_context(user_data={
            'user_id': '111',
            'tier1_step': 0,
            'tier1_data': {},
            'tier1_answer_order': [],
        })
        result = await handle_tier1_response(update, context)
        assert result == Q1_TIER1
        assert context.user_data['tier1_data']['sleep_hours'] == 7.5
        assert context.user_data['tier1_step'] == 1

    @pytest.mark.asyncio
    async def test_all_six_answered_moves_to_q3(self):
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
        assert result == Q3_ENERGY_MOOD

    @pytest.mark.asyncio
    async def test_undo_removes_last_answer(self):
        update = _make_callback_update(data="tier1_undo")
        context = _make_context(user_data={
            'user_id': '111',
            'tier1_step': 2,
            'tier1_data': {'sleep_hours': 7.5, 'deep_work_hours': 2.5},
            'tier1_answer_order': ['sleep_hours', 'deep_work_hours'],
        })
        result = await handle_tier1_response(update, context)
        assert result == Q1_TIER1
        assert 'deep_work_hours' not in context.user_data['tier1_data']
        assert len(context.user_data['tier1_answer_order']) == 1
        assert context.user_data['tier1_step'] == 1

    @pytest.mark.asyncio
    async def test_undo_empty_does_nothing(self):
        update = _make_callback_update(data="tier1_undo")
        context = _make_context(user_data={
            'user_id': '111',
            'tier1_step': 0,
            'tier1_data': {},
            'tier1_answer_order': [],
        })
        result = await handle_tier1_response(update, context)
        assert result == Q1_TIER1


# =============================================
# handle_alignment_rating_callback Tests
# =============================================

class TestHandleAlignmentRatingCallback:

    @pytest.mark.asyncio
    async def test_valid_alignment_rating(self):
        update = _make_callback_update(data="align_8")
        context = _make_context(user_data={'rating': 0})
        result = await handle_alignment_rating_callback(update, context)
        assert result == Q3_ENERGY_MOOD
        assert context.user_data['rating'] == 8


# =============================================
# handle_reflection_skip_callback Tests
# =============================================

class TestHandleReflectionSkipCallback:

    @pytest.mark.asyncio
    async def test_reflection_skip(self):
        update = _make_callback_update(data="ref_skip")
        context = _make_context(user_data={
            'user_id': '111',
            'date': '2026-02-07',
            'mode': 'maintenance',
            'checkin_start_time': datetime.utcnow(),
            'tier1': Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=True, training_intensity='moderate',
                deep_work=True, deep_work_hours=2.5,
                skill_building=True, skill_building_hours=2.0,
                zero_porn=True, boundaries=True
            ),
            'rating': 8,
            'energy_rating': 7,
            'mood_rating': 8,
        })
        
        with patch('src.bot.conversation.finish_checkin', new_callable=AsyncMock) as mock_finish:
            result = await handle_reflection_skip_callback(update, context)
            
        assert result == ConversationHandler.END
        assert context.user_data['challenges'] == "None reported."
        assert "alignment" in context.user_data['rating_reason'].lower()
        assert context.user_data['tomorrow_priority'] == "Maintain consistency."
        mock_finish.assert_called_once()


# =============================================
# handle_reflection_response Tests
# =============================================

class TestHandleReflectionResponse:

    @pytest.mark.asyncio
    async def test_reflection_text_input(self):
        update = _make_update(text="Felt good today, completed tasks. Tomorrow focus on study.")
        context = _make_context(user_data={
            'user_id': '111',
            'date': '2026-02-07',
            'mode': 'maintenance',
            'checkin_start_time': datetime.utcnow(),
            'tier1': Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=True, training_intensity='moderate',
                deep_work=True, deep_work_hours=2.5,
                skill_building=True, skill_building_hours=2.0,
                zero_porn=True, boundaries=True
            ),
            'rating': 8,
            'energy_rating': 7,
            'mood_rating': 8,
        })
        
        mock_parsed = {
            "challenges": "None reported.",
            "rating_reason": "Felt good today, completed tasks.",
            "tomorrow_priority": "Study.",
            "tomorrow_obstacle": "None reported."
        }
        
        with patch('src.bot.conversation.get_checkin_agent') as mock_agent_get, \
             patch('src.bot.conversation.finish_checkin', new_callable=AsyncMock) as mock_finish:
            mock_agent = MagicMock()
            mock_agent.parse_reflection_note = AsyncMock(return_value=mock_parsed)
            mock_agent_get.return_value = mock_agent
            
            result = await handle_reflection_response(update, context)
            
        assert result == ConversationHandler.END
        assert context.user_data['challenges'] == "None reported."
        assert context.user_data['tomorrow_priority'] == "Study."
        mock_finish.assert_called_once()


# =============================================
# handle_voice_reflection Tests
# =============================================

class TestHandleVoiceReflection:

    @pytest.mark.asyncio
    async def test_voice_reflection(self):
        update = MagicMock()
        update.message = AsyncMock()
        update.message.voice = MagicMock()
        update.message.reply_text = AsyncMock()
        
        context = _make_context(user_data={
            'user_id': '111',
            'date': '2026-02-07',
            'mode': 'maintenance',
            'checkin_start_time': datetime.utcnow(),
            'tier1': Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=True, training_intensity='moderate',
                deep_work=True, deep_work_hours=2.5,
                skill_building=True, skill_building_hours=2.0,
                zero_porn=True, boundaries=True
            ),
            'rating': 8,
            'energy_rating': 7,
            'mood_rating': 8,
        })
        
        with patch('src.bot.conversation.finish_checkin', new_callable=AsyncMock) as mock_finish:
            result = await handle_voice_reflection(update, context)
            
        assert result == ConversationHandler.END
        assert "voice" in context.user_data['challenges'].lower()
        mock_finish.assert_called_once()


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
        update = _make_callback_update(data="tier1_boundaries_yes")
        context = _make_context(user_data={
            'user_id': '111',
            'checkin_type': 'quick',
            'tier1_step': 5,
            'tier1_data': {
                'sleep_hours': 7.5, 'deep_work_hours': 2.5,
                'skill_building_hours': 2.0, 'training_intensity': 'moderate',
                'zero_porn': True
            },
            'tier1_answer_order': ['sleep_hours', 'deep_work_hours',
                                   'skill_building_hours', 'training_intensity', 'zero_porn'],
        })

        with patch('src.bot.conversation.finish_checkin_quick',
                   new_callable=AsyncMock) as mock_finish:
            result = await handle_tier1_response(update, context)

        assert result == ConversationHandler.END
        mock_finish.assert_called_once()
