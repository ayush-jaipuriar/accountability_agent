"""
Streamlined 3-Card Check-In Flow Unit & Regression Tests
========================================================

Tests:
1. start_checkin loads predictive baseline and renders Card 1
2. start_checkin works with callback updates (when update.message is None)
3. Habit matrix interactive adjustments (inc/dec/cycle/toggle)
4. Habit matrix confirmation transitions to Card 2 (Energy & Reflection)
5. Card 2 energy tap transitions to Card 3 (Tomorrow's Focus Lock)
6. Card 3 focus lock submit commits tasks and calls finish_checkin
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime
from telegram.ext import ConversationHandler

from src.models.schemas import User, UserStreaks, Tier1NonNegotiables
from src.bot.conversation import (
    Q1_TIER1, Q3_ENERGY_MOOD, Q5_TODO_PRIMARY,
    start_checkin,
    handle_tier1_response,
    handle_energy_callback,
    handle_focus_lock_callback,
)


def _make_user(**overrides) -> User:
    defaults = dict(
        user_id="12345",
        telegram_id=12345,
        telegram_username="ayush",
        name="Ayush",
        timezone="Asia/Kolkata",
        constitution_mode="maintenance",
        career_mode="skill_building",
        streaks=UserStreaks(
            current_streak=5, longest_streak=10,
            last_checkin_date="2026-08-23", total_checkins=25
        ),
        quick_checkin_count=0,
        quick_checkin_used_dates=[],
    )
    defaults.update(overrides)
    return User(**defaults)


def _make_msg_update(user_id=12345, text="/checkin"):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.message = AsyncMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.callback_query = None
    return update


def _make_callback_update(data="hmatrix_confirm", user_id=12345):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.message = None
    query = AsyncMock()
    query.data = data
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.edit_message_reply_markup = AsyncMock()
    query.message = AsyncMock()
    query.message.reply_text = AsyncMock()
    update.callback_query = query
    return update


def _make_context(user_data=None):
    context = MagicMock()
    context.user_data = user_data if user_data is not None else {}
    context.bot = AsyncMock()
    return context


@pytest.mark.asyncio
async def test_start_checkin_with_callback_query_does_not_crash():
    """Verify start_checkin does not raise AttributeError when called from inline callback."""
    user = _make_user()
    update = _make_callback_update(data="today_start_checkin")
    context = _make_context()

    with patch('src.bot.conversation.firestore_service') as mock_fs, \
         patch('src.bot.conversation.get_checkin_date', return_value="2026-08-24"):
        mock_fs.get_user.return_value = user
        mock_fs.checkin_exists.return_value = False
        mock_fs.get_recent_checkins.return_value = []

        result = await start_checkin(update, context)

    assert result == Q1_TIER1
    assert update.callback_query.message.reply_text.called
    assert "HABIT MATRIX (1/3)" in update.callback_query.message.reply_text.call_args[0][0]
    assert "tier1_data" in context.user_data


@pytest.mark.asyncio
async def test_habit_matrix_toggles():
    """Verify that habit matrix increment/decrement/cycle buttons update tier1_data."""
    context = _make_context({
        'user_id': '12345',
        'date': '2026-08-24',
        'tier1_data': {
            'sleep_hours': 7.0,
            'deep_work_hours': 2.0,
            'skill_building_hours': 1.0,
            'training_intensity': 'rest',
            'zero_porn': True,
            'boundaries': True,
        }
    })

    # Test inc sleep
    up1 = _make_callback_update(data="hmatrix_inc_sleep")
    await handle_tier1_response(up1, context)
    assert context.user_data['tier1_data']['sleep_hours'] == 7.5

    # Test cycle training
    up2 = _make_callback_update(data="hmatrix_cycle_training")
    await handle_tier1_response(up2, context)
    assert context.user_data['tier1_data']['training_intensity'] == 'light'

    # Test toggle porn
    up3 = _make_callback_update(data="hmatrix_toggle_porn")
    await handle_tier1_response(up3, context)
    assert context.user_data['tier1_data']['zero_porn'] is False


@pytest.mark.asyncio
async def test_habit_matrix_confirm_to_energy():
    """Verify confirming Card 1 stores Tier1NonNegotiables and moves to Card 2."""
    context = _make_context({
        'user_id': '12345',
        'date': '2026-08-24',
        'checkin_type': 'full',
        'tier1_data': {
            'sleep_hours': 8.0,
            'deep_work_hours': 3.0,
            'skill_building_hours': 2.0,
            'training_intensity': 'moderate',
            'zero_porn': True,
            'boundaries': True,
        }
    })

    update = _make_callback_update(data="hmatrix_confirm")
    with patch('src.services.task_service.task_service.get_daily_tasks', return_value=None):
        result = await handle_tier1_response(update, context)

    assert result == Q3_ENERGY_MOOD
    assert isinstance(context.user_data['tier1'], Tier1NonNegotiables)
    assert context.user_data['tier1'].sleep_hours == 8.0
    assert context.user_data['tier1'].deep_work_hours == 3.0
    assert "ENERGY & REFLECTION (2/3)" in update.callback_query.edit_message_text.call_args[0][0]


@pytest.mark.asyncio
async def test_energy_callback_to_focus_lock():
    """Verify rating energy moves directly to Card 3 Focus Lock."""
    context = _make_context({
        'user_id': '12345',
        'date': '2026-08-24',
        'tomorrow_priority': 'Ship v3 check-in refactor'
    })

    update = _make_callback_update(data="energy_9")
    result = await handle_energy_callback(update, context)

    assert result == Q5_TODO_PRIMARY
    assert context.user_data['energy_rating'] == 9
    assert context.user_data['rating'] == 9
    assert "TOMORROW'S FOCUS LOCK (3/3)" in update.callback_query.edit_message_text.call_args[0][0]


@pytest.mark.asyncio
async def test_focus_lock_submit_finalizes_checkin():
    """Verify tapping focus lock submit commits tasks and calls finish_checkin."""
    context = _make_context({
        'user_id': '12345',
        'date': '2026-08-24',
        'timezone': 'Asia/Kolkata',
        'tomorrow_priority': 'Ship v3 check-in refactor',
        'todo_sec1': 'Code review',
        'todo_sec2': None,
    })

    update = _make_callback_update(data="focus_lock_submit")
    with patch('src.services.task_service.task_service.save_committed_task_list') as mock_save, \
         patch('src.bot.conversation.finish_checkin', new_callable=AsyncMock) as mock_finish:
        result = await handle_focus_lock_callback(update, context)

    assert result == ConversationHandler.END
    assert mock_save.called
    assert mock_finish.called
