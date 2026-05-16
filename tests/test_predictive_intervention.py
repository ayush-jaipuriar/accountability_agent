"""
Test: Predictive Intervention Engine
=====================================

Tests risk prediction and preventive action generation.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch

from src.models.schemas import DailyCheckIn, Tier1NonNegotiables, CheckInResponses, User, UserStreaks
from src.services.predictive_intervention import PredictiveInterventionEngine


@pytest.fixture
def engine():
    return PredictiveInterventionEngine()


def make_checkin(
    date: str,
    compliance: float = 80.0,
    sleep_hours: float = 7.5,
    training: bool = True,
    deep_work: bool = True,
) -> DailyCheckIn:
    return DailyCheckIn(
        date=date,
        user_id="111",
        mode="maintenance",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=sleep_hours >= 7.0,
            sleep_hours=sleep_hours,
            training=training,
            training_intensity="moderate" if training else "rest",
            deep_work=deep_work,
            deep_work_hours=2.5 if deep_work else 0.5,
            skill_building=True,
            skill_building_hours=2.0,
            zero_porn=True,
            boundaries=True,
        ),
        responses=CheckInResponses(
            challenges="Test challenges for the day with enough characters",
            rating=7,
            rating_reason="Solid day overall with good consistency and progress",
            tomorrow_priority="Continue daily check-ins and maintain streak",
            tomorrow_obstacle="Late night work might interfere with bedtime routine",
        ),
        compliance_score=compliance,
    )


def make_user(streak: int = 10) -> User:
    return User(
        user_id="111",
        telegram_id=111,
        telegram_username="testuser",
        name="Test",
        timezone="Asia/Kolkata",
        constitution_mode="maintenance",
        career_mode="software_engineering",
        streaks=UserStreaks(
            current_streak=streak,
            longest_streak=streak,
            total_checkins=streak + 5,
        ),
    )


class TestDOWRisk:
    """Test day-of-week risk detection."""

    def test_detects_high_risk_day(self, engine):
        """Saturdays have 50%+ miss rate for training."""
        base = datetime(2026, 1, 5)  # Monday
        checkins = []
        for i in range(21):  # 3 weeks
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            # Saturdays (day 5): skip training
            training = i % 7 != 5
            checkins.append(make_checkin(date, training=training))

        user = make_user()
        # Mock tomorrow to be Saturday (where training risk exists)
        with patch.object(engine, '_get_tomorrow_date', return_value=datetime(2026, 1, 10)):
            prediction = engine.predict_tomorrow_risk(user, checkins)
        risks = prediction["risks"]

        dow_risks = [r for r in risks if r["risk"] == "dow_risk"]
        assert len(dow_risks) >= 1

    def test_no_risk_on_good_days(self, engine):
        """All days consistent = no DOW risk."""
        base = datetime(2026, 1, 5)
        checkins = []
        for i in range(21):
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            checkins.append(make_checkin(date, training=True))

        user = make_user()
        prediction = engine.predict_tomorrow_risk(user, checkins)
        dow_risks = [r for r in prediction["risks"] if r["risk"] == "dow_risk"]
        assert len(dow_risks) == 0


class TestStreakFatigue:
    """Test streak fatigue detection."""

    def test_detects_day_6_fatigue(self, engine):
        """Streak day 6 triggers fatigue risk."""
        checkins = [make_checkin(f"2026-01-{i:02d}") for i in range(1, 15)]
        user = make_user(streak=6)  # Day 6 of streak
        prediction = engine.predict_tomorrow_risk(user, checkins)

        fatigue_risks = [r for r in prediction["risks"] if r["risk"] == "streak_fatigue"]
        assert len(fatigue_risks) == 1
        assert fatigue_risks[0]["probability"] == 0.6

    def test_no_fatigue_early_streak(self, engine):
        """Streak < 6 doesn't trigger fatigue."""
        checkins = [make_checkin(f"2026-01-{i:02d}") for i in range(1, 10)]
        user = make_user(streak=3)
        prediction = engine.predict_tomorrow_risk(user, checkins)

        fatigue_risks = [r for r in prediction["risks"] if r["risk"] == "streak_fatigue"]
        assert len(fatigue_risks) == 0


class TestRecentDecline:
    """Test recent compliance decline detection."""

    def test_detects_decline(self, engine):
        """15%+ drop triggers risk."""
        base = datetime(2026, 1, 5)
        checkins = []
        for i in range(14):
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            # Days 1-11: high compliance, days 12-14: sharp drop
            compliance = 90.0 if i < 11 else 50.0
            checkins.append(make_checkin(date, compliance=compliance))

        user = make_user()
        prediction = engine.predict_tomorrow_risk(user, checkins)

        decline_risks = [r for r in prediction["risks"] if r["risk"] == "momentum_loss"]
        assert len(decline_risks) == 1
        assert "dropped 40%" in decline_risks[0]["reason"]

    def test_stable_no_decline(self, engine):
        """Stable compliance = no decline risk."""
        checkins = [make_checkin(f"2026-01-{i:02d}", compliance=80.0) for i in range(1, 15)]
        user = make_user()
        prediction = engine.predict_tomorrow_risk(user, checkins)

        decline_risks = [r for r in prediction["risks"] if r["risk"] == "momentum_loss"]
        assert len(decline_risks) == 0


class TestPreventiveActions:
    """Test preventive action generation."""

    def test_suggests_actions(self, engine):
        """Risks generate specific preventive actions."""
        risks = [
            {"metric": "sleep", "risk": "dow_risk"},
            {"metric": "training", "risk": "dow_risk"},
        ]
        actions = engine._suggest_preventive_actions(risks)

        assert len(actions) == 2
        assert any("bedtime alarm" in a for a in actions)
        assert any("workout clothes" in a for a in actions)

    def test_deduplicates_actions(self, engine):
        """Duplicate risks don't duplicate actions."""
        risks = [
            {"metric": "sleep", "risk": "dow_risk"},
            {"metric": "sleep", "risk": "dow_risk"},
        ]
        actions = engine._suggest_preventive_actions(risks)
        assert len(actions) == 1


class TestFormatting:
    """Test message formatting."""

    def test_formats_prediction(self, engine):
        """Prediction formats with risks and actions."""
        prediction = {
            "risk_score": 0.7,
            "risks": [
                {"metric": "sleep", "risk": "dow_risk", "probability": 0.7, "reason": "You miss sleep on 70% of Saturdays"},
            ],
            "preventive_actions": ["Set a bedtime alarm for tonight"],
        }
        user = make_user(streak=10)
        message = engine.format_prediction(prediction, user)

        assert "Tomorrow's Risk Forecast" in message
        assert "sleep" in message.lower()
        assert "bedtime alarm" in message
        assert "10-day streak" in message

    def test_no_risks_positive_message(self, engine):
        """No risks = positive message."""
        prediction = {"risk_score": 0.0, "risks": [], "preventive_actions": []}
        user = make_user()
        message = engine.format_prediction(prediction, user)

        assert "No elevated risks" in message


class TestMinimumData:
    """Test minimum data requirements."""

    def test_less_than_14_checkins(self, engine):
        """Need 14+ check-ins for prediction."""
        checkins = [make_checkin(f"2026-01-{i:02d}") for i in range(1, 10)]
        user = make_user()
        prediction = engine.predict_tomorrow_risk(user, checkins)

        assert prediction["risk_score"] == 0.0
        assert len(prediction["risks"]) == 0
