"""
Unit and Integration Tests for Daily Focus Engine (To-Dos)
============================================================

Tests:
1. Pure calculation function `calculate_task_score`.
2. Combined compliance score calculations (80% Tier 1 + 20% Tasks).
3. Backward compatibility (when no tasks are committed).
4. TaskService Firestore operations via mocking.
"""

import pytest
from datetime import datetime
from unittest.mock import MagicMock

from src.models.schemas import Tier1NonNegotiables, DailyTaskItem, DailyTaskList
from src.utils.compliance import calculate_task_score, calculate_compliance_score, calculate_compliance_score_normalized
from src.services.task_service import TaskService


# ===== 1. Test: Task Score Calculations =====

def test_calculate_task_score_empty():
    """Verify empty task list returns 100.0 (no penalty)."""
    assert calculate_task_score([]) == 100.0


def test_calculate_task_score_primary_only():
    """Verify score for primary task only (100% weight)."""
    p_task_comp = DailyTaskItem(id="p", title="Primary", is_primary=True, completed=True)
    p_task_fail = DailyTaskItem(id="p", title="Primary", is_primary=True, completed=False)
    
    assert calculate_task_score([p_comp := p_task_comp]) == 100.0
    assert calculate_task_score([p_fail := p_task_fail]) == 0.0


def test_calculate_task_score_primary_and_one_secondary():
    """Verify score with 1 primary and 1 secondary task (60% / 40% weight split)."""
    t_primary_yes = DailyTaskItem(id="p", title="Primary", is_primary=True, completed=True)
    t_primary_no = DailyTaskItem(id="p", title="Primary", is_primary=True, completed=False)
    
    t_sec_yes = DailyTaskItem(id="s1", title="Sec 1", is_primary=False, completed=True)
    t_sec_no = DailyTaskItem(id="s1", title="Sec 1", is_primary=False, completed=False)
    
    # Both complete: 100%
    assert calculate_task_score([t_primary_yes, t_sec_yes]) == 100.0
    
    # Primary complete, Secondary missed: 60%
    assert calculate_task_score([t_primary_yes, t_sec_no]) == 60.0
    
    # Primary missed, Secondary complete: 40%
    assert calculate_task_score([t_primary_no, t_sec_yes]) == 40.0
    
    # Both missed: 0%
    assert calculate_task_score([t_primary_no, t_sec_no]) == 0.0


def test_calculate_task_score_primary_and_two_secondaries():
    """Verify score with 1 primary and 2 secondary tasks (50% / 25% / 25% weight split)."""
    t_primary_yes = DailyTaskItem(id="p", title="Primary", is_primary=True, completed=True)
    t_primary_no = DailyTaskItem(id="p", title="Primary", is_primary=True, completed=False)
    
    t_sec1_yes = DailyTaskItem(id="s1", title="Sec 1", is_primary=False, completed=True)
    t_sec1_no = DailyTaskItem(id="s1", title="Sec 1", is_primary=False, completed=False)
    
    t_sec2_yes = DailyTaskItem(id="s2", title="Sec 2", is_primary=False, completed=True)
    t_sec2_no = DailyTaskItem(id="s2", title="Sec 2", is_primary=False, completed=False)
    
    # All complete: 100%
    assert calculate_task_score([t_primary_yes, t_sec1_yes, t_sec2_yes]) == 100.0
    
    # Primary complete, 1/2 secondary complete: 50% + 25% = 75%
    assert calculate_task_score([t_primary_yes, t_sec1_yes, t_sec2_no]) == 75.0
    
    # Primary complete, 0/2 secondary complete: 50%
    assert calculate_task_score([t_primary_yes, t_sec1_no, t_sec2_no]) == 50.0
    
    # Primary missed, both secondary complete: 0% + 50% = 50%
    assert calculate_task_score([t_primary_no, t_sec1_yes, t_sec2_yes]) == 50.0
    
    # Primary missed, 1/2 secondary complete: 25%
    assert calculate_task_score([t_primary_no, t_sec1_yes, t_sec2_no]) == 25.0


# ===== 2. Test: Combined Compliance Score Calculations =====

@pytest.fixture
def perfect_tier1():
    return Tier1NonNegotiables(
        sleep=True, training=True, deep_work=True,
        skill_building=True, zero_porn=True, boundaries=True
    )


@pytest.fixture
def partial_tier1():
    # 5/6 complete = 83.33%
    return Tier1NonNegotiables(
        sleep=False, training=True, deep_work=True,
        skill_building=True, zero_porn=True, boundaries=True
    )


def test_compliance_score_combined_perfect(perfect_tier1):
    """Verify 100% tier 1 + 100% tasks yields 100% compliance."""
    tasks = [DailyTaskItem(id="p", title="Primary", is_primary=True, completed=True)]
    score = calculate_compliance_score(perfect_tier1, tasks)
    assert score == 100.0


def test_compliance_score_combined_weighted(perfect_tier1, partial_tier1):
    """Verify weighted formula: (Tier1 * 0.8) + (Tasks * 0.2)."""
    tasks_fail = [DailyTaskItem(id="p", title="Primary", is_primary=True, completed=False)]
    tasks_success = [DailyTaskItem(id="p", title="Primary", is_primary=True, completed=True)]
    
    # Case A: Perfect Tier 1 (100%), Failed Tasks (0%) -> 80%
    score_a = calculate_compliance_score(perfect_tier1, tasks_fail)
    assert abs(score_a - 80.0) < 0.01
    
    # Case B: Partial Tier 1 (83.33%), Perfect Tasks (100%) -> 83.33 * 0.8 + 20 = 86.66%
    score_b = calculate_compliance_score(partial_tier1, tasks_success)
    assert abs(score_b - 86.67) < 0.02


def test_compliance_score_backward_compatibility(perfect_tier1, partial_tier1):
    """Verify that when committed_tasks is None, scoring falls back to 100% Tier 1 weight."""
    assert calculate_compliance_score(perfect_tier1) == 100.0
    assert abs(calculate_compliance_score(partial_tier1) - 83.33) < 0.01
    
    assert calculate_compliance_score_normalized(perfect_tier1) == 100.0
    assert abs(calculate_compliance_score_normalized(partial_tier1)) - 83.33 < 0.01


# ===== 3. Test: Task Service Firestore Operations =====

def test_task_service_flow():
    """Verify TaskService create, add task constraints, commit, and toggles."""
    service = TaskService()
    
    # Mock firestore database client statefully
    mock_db = MagicMock()
    service.firestore = MagicMock()
    service.firestore.db = mock_db
    
    user_id = "test_user"
    date = "2026-06-28"
    
    db_store = {}
    mock_doc = MagicMock()
    
    def get_doc():
        mock_doc.exists = date in db_store
        return mock_doc
        
    def to_dict():
        return db_store.get(date)
        
    def set_doc(data):
        db_store[date] = data
        return MagicMock()
        
    mock_doc.to_dict = to_dict
    
    mock_doc_ref = MagicMock()
    mock_doc_ref.get = get_doc
    mock_doc_ref.set = set_doc
    
    mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_doc_ref
    
    # 1. Test create_or_get_daily_tasks when list doesn't exist
    # Calling get_daily_tasks should return None
    assert service.get_daily_tasks(user_id, date) is None
    
    # Calling create_or_get_daily_tasks should initialize with primary task
    task_list = service.create_or_get_daily_tasks(user_id, date, "Primary Task Title")
    assert len(task_list.tasks) == 1
    assert task_list.tasks[0].title == "Primary Task Title"
    assert task_list.tasks[0].is_primary is True
    assert task_list.committed is False
    
    # 2. Add first secondary task
    success, msg = service.add_secondary_task(user_id, date, "Secondary Task 1")
    assert success is True
    
    # Retrieve
    task_list = service.get_daily_tasks(user_id, date)
    assert len(task_list.tasks) == 2
    assert task_list.tasks[1].title == "Secondary Task 1"
    assert task_list.tasks[1].is_primary is False
    
    # 3. Add second secondary task
    success, msg = service.add_secondary_task(user_id, date, "Secondary Task 2")
    assert success is True
    
    task_list = service.get_daily_tasks(user_id, date)
    assert len(task_list.tasks) == 3
    
    # 4. Add third secondary task (should fail due to max 2 limit)
    success, msg = service.add_secondary_task(user_id, date, "Secondary Task 3")
    assert success is False
    assert "maximum of 2 secondary tasks" in msg
    
    # 5. Commit tasks
    success, msg = service.commit_daily_tasks(user_id, date)
    assert success is True
    
    task_list = service.get_daily_tasks(user_id, date)
    assert task_list.committed is True
    
    # 6. Add task after commit (should fail)
    success, msg = service.add_secondary_task(user_id, date, "Too Late Task")
    assert success is False
    assert "already committed" in msg
    
    # 7. Toggle completion
    success, updated_list = service.toggle_task_completion(user_id, date, "task_primary", True)
    assert success is True
    assert updated_list.tasks[0].completed is True
    assert updated_list.tasks[0].completed_at is not None
