"""
Unit Tests for Data Models & Schemas Validation
===============================================

Comprehensive test coverage for:
- Pydantic models constraints (ge, le, min_length, max_length, pattern)
- Negative & out-of-bounds inputs
- Computed properties (sleep_met, deep_work_met, etc.)
- to_firestore() and from_firestore() serialization/deserialization
- Helper functions (get_current_date_ist, get_current_datetime_ist)
"""

import pytest
from datetime import datetime
from pydantic import ValidationError

from src.models.schemas import (
    User, UserStreaks, StreakShields, ReminderTimes, AIProfileMemory,
    Tier1NonNegotiables, CheckInResponses, DailyCheckIn, DailyTaskItem,
    DailyTaskList, Goal, PartnerChallenge, ReminderStatus, Achievement,
    Pattern, get_current_date_ist, get_current_datetime_ist
)


class TestUserStreaksValidation:
    """Test UserStreaks model validation and constraints."""

    def test_valid_user_streaks(self):
        streaks = UserStreaks(
            current_streak=5,
            longest_streak=10,
            total_checkins=25,
            last_checkin_date="2026-02-01",
            streak_before_reset=15,
            last_reset_date="2026-01-20"
        )
        assert streaks.current_streak == 5
        assert streaks.longest_streak == 10

    def test_negative_current_streak_raises_validation_error(self):
        with pytest.raises(ValidationError):
            UserStreaks(current_streak=-1)

    def test_negative_longest_streak_raises_validation_error(self):
        with pytest.raises(ValidationError):
            UserStreaks(longest_streak=-5)

    def test_negative_total_checkins_raises_validation_error(self):
        with pytest.raises(ValidationError):
            UserStreaks(total_checkins=-1)


class TestStreakShieldsValidation:
    """Test StreakShields model defaults and properties."""

    def test_defaults(self):
        shields = StreakShields()
        assert shields.total == 3
        assert shields.used == 0
        assert shields.available == 3
        assert shields.earned_at == []
        assert shields.last_reset is None


class TestAIProfileMemoryValidation:
    """Test AIProfileMemory say_do_ratio bounds."""

    def test_valid_say_do_ratio(self):
        memory = AIProfileMemory(say_do_ratio=85.5)
        assert memory.say_do_ratio == 85.5

    def test_negative_say_do_ratio_raises(self):
        with pytest.raises(ValidationError):
            AIProfileMemory(say_do_ratio=-0.1)

    def test_overflow_say_do_ratio_raises(self):
        with pytest.raises(ValidationError):
            AIProfileMemory(say_do_ratio=105.0)


class TestUserValidationAndFirestore:
    """Test User schema validation, churn score constraints, and Firestore roundtrip."""

    def test_valid_user_and_roundtrip(self):
        user = User(
            user_id="user_999",
            telegram_id=999,
            name="Schema Test User",
            timezone="America/New_York",
            constitution_mode="optimization",
            career_mode="job_searching",
            churn_risk_score=0.35,
        )
        data = user.to_firestore()
        assert data["user_id"] == "user_999"
        assert data["timezone"] == "America/New_York"
        assert data["churn_risk_score"] == 0.35
        assert isinstance(data["streaks"], dict)

        restored_user = User.from_firestore(data)
        assert restored_user.user_id == user.user_id
        assert restored_user.streaks.current_streak == 0
        assert restored_user.career_mode == "job_searching"

    def test_user_churn_risk_bounds(self):
        with pytest.raises(ValidationError):
            User(user_id="1", telegram_id=1, name="A", churn_risk_score=-0.1)

        with pytest.raises(ValidationError):
            User(user_id="1", telegram_id=1, name="A", churn_risk_score=1.5)

    def test_from_firestore_with_iso_strings(self):
        data = {
            "user_id": "user_str_date",
            "telegram_id": 888,
            "name": "Date User",
            "last_churn_check": "2026-02-01T12:00:00",
            "last_churn_intervention": "invalid_date_format",
        }
        user = User.from_firestore(data)
        assert isinstance(user.last_churn_check, datetime)
        assert user.last_churn_intervention is None


class TestTier1NonNegotiablesValidation:
    """Test continuous metric limits, intensity regex, and computed properties."""

    def test_valid_continuous_tier1(self):
        tier1 = Tier1NonNegotiables(
            sleep_hours=7.5,
            deep_work_hours=3.0,
            skill_building_hours=2.0,
            training_intensity="moderate",
            zero_porn=True,
            boundaries=True,
        )
        assert tier1.sleep_met is True
        assert tier1.sleep_met_full is True
        assert tier1.deep_work_met is True
        assert tier1.deep_work_met_full is True
        assert tier1.skill_building_met is True
        assert tier1.skill_building_met_full is True
        assert tier1.training_done is True

    def test_micro_habits_properties(self):
        tier1 = Tier1NonNegotiables(
            sleep_hours=6.2,           # >= 6.0 (micro) but < 7.0 (full)
            deep_work_hours=0.75,      # >= 0.5 (micro) but < 2.0 (full)
            skill_building_hours=1.0,  # >= 0.5 (micro) but < 2.0 (full)
            training_intensity="rest",
            zero_porn=True,
            boundaries=True,
        )
        assert tier1.sleep_met is True
        assert tier1.sleep_met_full is False
        assert tier1.deep_work_met is True
        assert tier1.deep_work_met_full is False
        assert tier1.skill_building_met is True
        assert tier1.skill_building_met_full is False
        assert tier1.training_done is False

    def test_legacy_boolean_fallbacks(self):
        tier1 = Tier1NonNegotiables(
            sleep=True,
            training=True,
            deep_work=True,
            skill_building=False,
            zero_porn=True,
            boundaries=True,
        )
        assert tier1.sleep_met is True
        assert tier1.sleep_met_full is True
        assert tier1.deep_work_met is True
        assert tier1.skill_building_met is False
        assert tier1.training_done is True

    def test_negative_and_overflow_hours_raise(self):
        with pytest.raises(ValidationError):
            Tier1NonNegotiables(sleep_hours=-1.0, zero_porn=True, boundaries=True)

        with pytest.raises(ValidationError):
            Tier1NonNegotiables(sleep_hours=18.0, zero_porn=True, boundaries=True)

        with pytest.raises(ValidationError):
            Tier1NonNegotiables(deep_work_hours=-0.5, zero_porn=True, boundaries=True)

        with pytest.raises(ValidationError):
            Tier1NonNegotiables(skill_building_hours=20.0, zero_porn=True, boundaries=True)

    def test_invalid_training_intensity_raise(self):
        with pytest.raises(ValidationError):
            Tier1NonNegotiables(
                training_intensity="super_intense",
                zero_porn=True,
                boundaries=True
            )


class TestCheckInResponsesValidation:
    """Test min_length, max_length, rating bounds for CheckInResponses."""

    def test_valid_responses(self):
        responses = CheckInResponses(
            challenges="Faced meetings throughout the afternoon.",
            rating=8,
            rating_reason="Got deep work done in the morning despite busy afternoon.",
            tomorrow_priority="Finish high-priority sprint tickets.",
            tomorrow_obstacle="Potential ad-hoc requests from stakeholders.",
            energy_rating=7,
            mood_rating=8,
        )
        assert responses.rating == 8
        assert responses.energy_rating == 7

    def test_short_challenge_raises(self):
        with pytest.raises(ValidationError):
            CheckInResponses(
                challenges="Too short",  # < 10 chars
                rating=8,
                rating_reason="Valid reason with enough characters.",
                tomorrow_priority="Valid priority with enough characters.",
                tomorrow_obstacle="Valid obstacle with enough characters.",
            )

    def test_invalid_rating_bounds_raise(self):
        with pytest.raises(ValidationError):
            CheckInResponses(
                challenges="Valid challenges with enough length.",
                rating=0,  # < 1
                rating_reason="Valid reason with enough characters.",
                tomorrow_priority="Valid priority with enough characters.",
                tomorrow_obstacle="Valid obstacle with enough characters.",
            )

        with pytest.raises(ValidationError):
            CheckInResponses(
                challenges="Valid challenges with enough length.",
                rating=11,  # > 10
                rating_reason="Valid reason with enough characters.",
                tomorrow_priority="Valid priority with enough characters.",
                tomorrow_obstacle="Valid obstacle with enough characters.",
            )

    def test_invalid_mood_and_energy_raise(self):
        with pytest.raises(ValidationError):
            CheckInResponses(
                challenges="Valid challenges with enough length.",
                rating=8,
                rating_reason="Valid reason with enough characters.",
                tomorrow_priority="Valid priority with enough characters.",
                tomorrow_obstacle="Valid obstacle with enough characters.",
                energy_rating=0,
            )


class TestDailyCheckInAndTasksSerialization:
    """Test DailyCheckIn, DailyTaskList, Goal, and Challenge serialization."""

    def test_daily_checkin_firestore_roundtrip(self):
        tier1 = Tier1NonNegotiables(
            sleep_hours=7.5,
            training_intensity="moderate",
            deep_work_hours=2.5,
            skill_building_hours=2.0,
            zero_porn=True,
            boundaries=True,
        )
        responses = CheckInResponses(
            challenges="Valid challenges with enough length.",
            rating=9,
            rating_reason="Valid reason with enough characters.",
            tomorrow_priority="Valid priority with enough characters.",
            tomorrow_obstacle="Valid obstacle with enough characters.",
        )
        checkin = DailyCheckIn(
            date="2026-02-07",
            user_id="user_123",
            mode="maintenance",
            tier1_non_negotiables=tier1,
            responses=responses,
            compliance_score=100.0,
            committed_tasks=[
                DailyTaskItem(id="t1", title="Write tests", is_primary=True, completed=True)
            ],
            return_reason="Was traveling"
        )

        doc = checkin.to_firestore()
        assert doc["date"] == "2026-02-07"
        assert doc["return_reason"] == "Was traveling"
        assert len(doc["committed_tasks"]) == 1

        restored = DailyCheckIn.from_firestore(doc)
        assert restored.user_id == "user_123"
        assert restored.compliance_score == 100.0
        assert restored.committed_tasks[0].title == "Write tests"

    def test_daily_task_list_firestore_roundtrip(self):
        task_list = DailyTaskList(
            user_id="user_123",
            date="2026-02-07",
            tasks=[
                DailyTaskItem(id="t1", title="Primary task", is_primary=True, completed=False),
                DailyTaskItem(id="t2", title="Secondary task", is_primary=False, completed=True),
            ],
            committed=True
        )
        doc = task_list.to_firestore()
        assert len(doc["tasks"]) == 2
        assert doc["committed"] is True

        restored = DailyTaskList.from_firestore(doc)
        assert len(restored.tasks) == 2
        assert restored.tasks[0].is_primary is True
        assert restored.tasks[1].completed is True

    def test_goal_firestore_roundtrip(self):
        goal = Goal(
            user_id="user_123",
            title="Sleep 7+ hours for 14 days",
            description="Consistent sleep habit",
            category="sleep",
            target_value=7.0,
            target_days=14,
            start_date="2026-02-01",
            status="active",
        )
        doc = goal.to_firestore()
        assert doc["category"] == "sleep"

        restored = Goal.from_firestore(doc)
        assert restored.title == goal.title
        assert restored.target_value == 7.0

    def test_partner_challenge_firestore_roundtrip(self):
        challenge = PartnerChallenge(
            challenger_id="u1",
            partner_id="u2",
            challenge_type="sleep_7_days",
            title="7 Day Sleep Challenge",
            description="Sleep 7+ hours each night",
            start_date="2026-02-01",
            end_date="2026-02-07",
            status="active"
        )
        doc = challenge.to_firestore()
        assert doc["challenge_type"] == "sleep_7_days"

        restored = PartnerChallenge.from_firestore(doc)
        assert restored.challenger_id == "u1"
        assert restored.partner_id == "u2"


class TestTimezoneHelperFunctions:
    """Test date/time helper wrappers in schemas.py."""

    def test_get_current_date_ist(self):
        date_str = get_current_date_ist("Asia/Kolkata")
        assert isinstance(date_str, str)
        assert len(date_str.split("-")) == 3

    def test_get_current_datetime_ist(self):
        dt = get_current_datetime_ist("Asia/Kolkata")
        assert isinstance(dt, datetime)
