"""
Tests for P2.2: Goal Service
==============================

Tests goal creation, progress tracking, and milestone detection.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.models.schemas import (
    Goal, Tier1NonNegotiables, CheckInResponses, DailyCheckIn
)
from src.services.goal_service import GoalService


# ===== Fixtures =====

@pytest.fixture
def goal_service():
    return GoalService()


@pytest.fixture
def sample_goal():
    return Goal(
        goal_id="goal_test_001",
        user_id="111",
        title="Sleep 7+ hours for 14 days",
        description="Build consistent sleep habit",
        category="sleep",
        target_value=7.0,
        target_days=14,
        start_date="2026-02-01",
        status="active",
        progress=[],
    )


@pytest.fixture
def sample_checkin():
    return DailyCheckIn(
        date="2026-02-15",
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
    )


# ===== Goal Creation =====

class TestGoalCreation:

    def test_create_goal(self, goal_service):
        with patch.object(goal_service.firestore.db, 'collection') as mock_coll:
            mock_doc = MagicMock()
            mock_coll.return_value.document.return_value = mock_doc
            
            goal = goal_service.create_goal(
                user_id="111",
                title="Sleep 7+ hours",
                description="Build habit",
                category="sleep",
                target_value=7.0,
                target_days=14,
                start_date="2026-02-01",
            )
            
            assert goal.user_id == "111"
            assert goal.title == "Sleep 7+ hours"
            assert goal.category == "sleep"
            assert goal.target_value == 7.0
            assert goal.target_days == 14
            assert goal.status == "active"
            mock_doc.set.assert_called_once()


# ===== Progress Tracking =====

class TestProgressTracking:

    def test_sleep_goal_met(self, goal_service, sample_goal, sample_checkin):
        milestone = goal_service._evaluate_goal_for_date(
            sample_goal, "2026-02-15", sample_checkin.tier1_non_negotiables
        )
        assert sample_goal.progress[-1]["met"] is True
        assert sample_goal.progress[-1]["value"] == 7.5

    def test_sleep_goal_missed(self, goal_service, sample_goal):
        checkin = DailyCheckIn(
            date="2026-02-15",
            user_id="111",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=False, sleep_hours=5.5,
                training=True, deep_work=True,
                skill_building=True, zero_porn=True, boundaries=True,
            ),
            responses=CheckInResponses(
                challenges="Test challenges for the day with enough characters",
                rating=5,
                rating_reason="Bad day with poor sleep and low energy levels",
                tomorrow_priority="Sleep better tonight and establish routine",
                tomorrow_obstacle="Late night work might interfere with bedtime",
            ),
            compliance_score=50.0,
        )
        
        milestone = goal_service._evaluate_goal_for_date(
            sample_goal, "2026-02-15", checkin.tier1_non_negotiables
        )
        assert sample_goal.progress[-1]["met"] is False
        assert sample_goal.progress[-1]["value"] == 5.5

    def test_consecutive_met_counting(self, goal_service):
        progress = [
            {"date": "2026-02-10", "met": True},
            {"date": "2026-02-11", "met": True},
            {"date": "2026-02-12", "met": True},
            {"date": "2026-02-13", "met": False},
            {"date": "2026-02-14", "met": True},
        ]
        assert goal_service._count_consecutive_met(progress) == 1

        progress2 = [
            {"date": "2026-02-10", "met": True},
            {"date": "2026-02-11", "met": True},
            {"date": "2026-02-12", "met": True},
        ]
        assert goal_service._count_consecutive_met(progress2) == 3

    def test_50_percent_milestone(self, goal_service, sample_goal):
        # Set target_days to 10 for easier testing
        sample_goal.target_days = 10
        sample_goal.progress = [
            {"date": f"2026-02-{i:02d}", "met": True}
            for i in range(1, 6)  # 5 consecutive days
        ]
        
        milestone = goal_service._evaluate_goal_for_date(
            sample_goal, "2026-02-15",
            Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=True, deep_work=True,
                skill_building=True, zero_porn=True, boundaries=True,
            )
        )
        assert milestone == "50%"

    def test_100_percent_completion(self, goal_service, sample_goal):
        # Set target_days to 3 for easier testing
        sample_goal.target_days = 3
        sample_goal.progress = [
            {"date": "2026-02-13", "met": True},
            {"date": "2026-02-14", "met": True},
        ]
        
        milestone = goal_service._evaluate_goal_for_date(
            sample_goal, "2026-02-15",
            Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=True, deep_work=True,
                skill_building=True, zero_porn=True, boundaries=True,
            )
        )
        assert milestone == "100%"
        assert sample_goal.status == "completed"

    def test_zero_porn_goal(self, goal_service):
        goal = Goal(
            goal_id="goal_zp_001",
            user_id="111",
            title="30 days clean",
            description="No porn for 30 days",
            category="zero_porn",
            target_days=30,
            start_date="2026-02-01",
            status="active",
            progress=[],
        )
        
        tier1 = Tier1NonNegotiables(
            sleep=True, training=True, deep_work=True,
            skill_building=True, zero_porn=True, boundaries=True,
        )
        
        milestone = goal_service._evaluate_goal_for_date(goal, "2026-02-15", tier1)
        assert goal.progress[-1]["met"] is True


# ===== Formatting =====

class TestGoalFormatting:

    def test_format_active_goal(self, goal_service, sample_goal):
        sample_goal.progress = [
            {"date": "2026-02-01", "met": True},
            {"date": "2026-02-02", "met": True},
            {"date": "2026-02-03", "met": True},
        ]
        text = goal_service.format_goal_progress(sample_goal)
        assert "Sleep 7+ hours for 14 days" in text
        assert "3/14" in text
        assert "21%" in text or "█" in text

    def test_format_completed_goal(self, goal_service, sample_goal):
        sample_goal.status = "completed"
        sample_goal.progress = [
            {"date": f"2026-02-{i:02d}", "met": True}
            for i in range(1, 15)
        ]
        text = goal_service.format_goal_progress(sample_goal)
        assert "🏆" in text
        assert "Completed" in text


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
