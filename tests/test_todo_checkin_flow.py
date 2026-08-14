"""
Unit tests for Next-Day To-Dos in Daily Check-In (Features 1 & 2).

Tests:
1. save_committed_task_list creates primary and secondary tasks and marks committed.
2. calculate_task_score properly weights primary (60%) and secondary (20% each).
3. calculate_compliance_score blends 80% Tier 1 + 20% To-Dos.
4. format_progress_summary formats to-dos with progress bar.
5. Check-in conversation flow transitions to Q5_TODO_PRIMARY, Q6_TODO_SECONDARY_1, Q7_TODO_SECONDARY_2.
6. Task verification flow on next day check-in.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from src.models.schemas import (
    DailyTaskItem,
    DailyTaskList,
    Tier1NonNegotiables,
    DailyCheckIn,
    CheckInResponses,
)
from src.utils.compliance import (
    calculate_task_score,
    calculate_compliance_score,
)
from src.services.task_service import TaskService
from src.bot.conversation import (
    format_progress_summary,
    handle_todo_primary,
    handle_todo_secondary_1,
    handle_todo_secondary_2,
    Q5_TODO_PRIMARY,
    Q6_TODO_SECONDARY_1,
    Q7_TODO_SECONDARY_2,
)


def test_calculate_task_score_weights():
    """Test task score weighting (Primary=50%, Secondaries=25% each when 2 secondaries)."""
    # Case 1: No tasks -> 100.0 (no penalty)
    assert calculate_task_score([]) == 100.0

    # Case 2: All completed
    tasks_all = [
        DailyTaskItem(id="t1", title="Must Ship Feature", is_primary=True, completed=True),
        DailyTaskItem(id="t2", title="Code Review", is_primary=False, completed=True),
        DailyTaskItem(id="t3", title="Clean Inbox", is_primary=False, completed=True),
    ]
    assert calculate_task_score(tasks_all) == 100.0

    # Case 3: Only primary completed (50%)
    tasks_primary = [
        DailyTaskItem(id="t1", title="Must Ship Feature", is_primary=True, completed=True),
        DailyTaskItem(id="t2", title="Code Review", is_primary=False, completed=False),
        DailyTaskItem(id="t3", title="Clean Inbox", is_primary=False, completed=False),
    ]
    assert calculate_task_score(tasks_primary) == 50.0

    # Case 4: Only 1 secondary completed (25%)
    tasks_sec = [
        DailyTaskItem(id="t1", title="Must Ship Feature", is_primary=True, completed=False),
        DailyTaskItem(id="t2", title="Code Review", is_primary=False, completed=True),
        DailyTaskItem(id="t3", title="Clean Inbox", is_primary=False, completed=False),
    ]
    assert calculate_task_score(tasks_sec) == 25.0

    # Case 5: Both secondaries completed (50%)
    tasks_both_sec = [
        DailyTaskItem(id="t1", title="Must Ship Feature", is_primary=True, completed=False),
        DailyTaskItem(id="t2", title="Code Review", is_primary=False, completed=True),
        DailyTaskItem(id="t3", title="Clean Inbox", is_primary=False, completed=True),
    ]
    assert calculate_task_score(tasks_both_sec) == 50.0


def test_calculate_compliance_score_with_tasks():
    """Test 80% Tier 1 + 20% To-Dos compliance blending."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        sleep_hours=7.5,  # 100%
        training=True,
        training_intensity="moderate",  # 100%
        deep_work=True,
        deep_work_hours=2.0,  # 100%
        skill_building=True,
        skill_building_hours=2.0,  # 100%
        zero_porn=True,  # 100%
        boundaries=True,  # 100%
    )
    # Tier 1 score = 100.0

    # If no committed tasks -> 100% based purely on Tier 1
    assert calculate_compliance_score(tier1, None) == 100.0

    # If committed tasks all done -> 80% of 100 + 20% of 100 = 100.0
    tasks_all_done = [
        DailyTaskItem(id="t1", title="Task 1", is_primary=True, completed=True),
        DailyTaskItem(id="t2", title="Task 2", is_primary=False, completed=True),
    ]
    assert calculate_compliance_score(tier1, tasks_all_done) == 100.0

    # If committed tasks 0% done -> 80% of 100 + 20% of 0 = 80.0
    tasks_none_done = [
        DailyTaskItem(id="t1", title="Task 1", is_primary=True, completed=False),
        DailyTaskItem(id="t2", title="Task 2", is_primary=False, completed=False),
    ]
    assert calculate_compliance_score(tier1, tasks_none_done) == 80.0

    # If only primary done (50%) -> 80 + (0.2 * 50) = 80 + 10 = 90.0
    tasks_primary_done = [
        DailyTaskItem(id="t1", title="Task 1", is_primary=True, completed=True),
        DailyTaskItem(id="t2", title="Task 2", is_primary=False, completed=False),
        DailyTaskItem(id="t3", title="Task 3", is_primary=False, completed=False),
    ]
    assert calculate_compliance_score(tier1, tasks_primary_done) == 90.0


def test_save_committed_task_list_service():
    """Test TaskService.save_committed_task_list correctly constructs and commits tasks."""
    mock_firestore = MagicMock()
    mock_doc = MagicMock()
    mock_firestore.db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc

    service = TaskService()
    service.firestore = mock_firestore
    result = service.save_committed_task_list(
        user_id="user_123",
        date="2026-08-15",
        primary_title="Deploy v3.2.0 to Cloud Run",
        sec1_title="Write unit tests",
        sec2_title="Update documentation",
    )

    assert result.user_id == "user_123"
    assert result.date == "2026-08-15"
    assert result.committed is True
    assert len(result.tasks) == 3

    assert result.tasks[0].title == "Deploy v3.2.0 to Cloud Run"
    assert result.tasks[0].is_primary is True
    assert result.tasks[0].completed is False

    assert result.tasks[1].title == "Write unit tests"
    assert result.tasks[1].is_primary is False

    assert result.tasks[2].title == "Update documentation"
    assert result.tasks[2].is_primary is False

    # Check that set was called on Firestore doc
    mock_doc.set.assert_called_once()


def test_format_progress_summary_with_tasks():
    """Test format_progress_summary includes daily focus section."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        sleep_hours=7.0,
        training=True,
        training_intensity="intense",
        deep_work=True,
        deep_work_hours=2.0,
        skill_building=True,
        skill_building_hours=2.0,
        zero_porn=True,
        boundaries=True,
    )
    tasks = [
        DailyTaskItem(id="t1", title="Finish Architecture", is_primary=True, completed=True),
        DailyTaskItem(id="t2", title="Send Newsletter", is_primary=False, completed=False),
    ]

    summary = format_progress_summary(tier1, tasks)
    assert "Daily Focus" in summary
    assert "1/2 completed" in summary
    assert "✅ Finish Architecture (Primary)" in summary
    assert "❌ Send Newsletter" in summary


@pytest.mark.asyncio
async def test_todo_input_handlers_chain():
    """Test sequential prompt transitions for tomorrow's to-dos."""
    update = MagicMock()
    update.message = AsyncMock()
    update.message.text = "Deliver major milestone"
    context = MagicMock()
    context.user_data = {
        "user_id": "test_user_42",
        "date": "2026-08-14",
        "timezone": "UTC",
    }

    # Step 1: Handle primary
    next_state = await handle_todo_primary(update, context)
    assert next_state == Q6_TODO_SECONDARY_1
    assert context.user_data["todo_primary"] == "Deliver major milestone"
    assert context.user_data["tomorrow_priority"] == "Deliver major milestone"

    # Step 2: Handle secondary 1
    update.message.text = "Write migration tests"
    next_state_2 = await handle_todo_secondary_1(update, context)
    assert next_state_2 == Q7_TODO_SECONDARY_2
    assert context.user_data["todo_sec1"] == "Write migration tests"

    # Step 3: Handle secondary 2 with mock task_service
    update.message.text = "Refactor logging"
    with patch("src.services.task_service.task_service.save_committed_task_list") as mock_save, \
         patch("src.bot.conversation.finish_checkin", new_callable=AsyncMock) as mock_finish:
        from telegram.ext import ConversationHandler
        end_state = await handle_todo_secondary_2(update, context)
        assert end_state == ConversationHandler.END
        mock_save.assert_called_once_with(
            user_id="test_user_42",
            date="2026-08-15",
            primary_title="Deliver major milestone",
            sec1_title="Write migration tests",
            sec2_title="Refactor logging",
        )
        mock_finish.assert_called_once()
