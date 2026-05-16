"""
Test: Insights Engine
=====================

Tests personalized insight generation from check-in history.
"""

import pytest
from datetime import datetime, timedelta

from src.models.schemas import DailyCheckIn, Tier1NonNegotiables, CheckInResponses, User, UserStreaks
from src.services.insights_engine import InsightsEngine


@pytest.fixture
def engine():
    return InsightsEngine()


def make_checkin(
    date: str,
    compliance: float = 80.0,
    sleep_hours: float = 7.5,
    training: bool = True,
    deep_work: bool = True,
    energy: int = None,
    mood: int = None,
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
            energy_rating=energy,
            mood_rating=mood,
        ),
        compliance_score=compliance,
    )


class TestDayOfWeekPatterns:
    """Test day-of-week insight detection."""

    def test_detects_best_and_worst_days(self, engine):
        """Find strongest and weakest days of the week."""
        base = datetime(2026, 1, 5)  # Monday
        checkins = []
        for i in range(21):  # 3 weeks
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            # Saturdays (day 5) have low compliance
            compliance = 50.0 if i % 7 == 5 else 85.0
            checkins.append(make_checkin(date, compliance=compliance))

        insights = engine.generate_insights(checkins)
        dow_insights = [i for i in insights if i["type"] == "day_of_week"]

        assert len(dow_insights) == 1
        assert "Saturday" in dow_insights[0]["title"]
        assert "Monday" in dow_insights[0]["title"] or "Tuesday" in dow_insights[0]["title"]

    def test_no_spread_no_insight(self, engine):
        """If all days are similar, no DOW insight."""
        base = datetime(2026, 1, 5)
        checkins = []
        for i in range(21):
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            checkins.append(make_checkin(date, compliance=80.0))

        insights = engine.generate_insights(checkins)
        dow_insights = [i for i in insights if i["type"] == "day_of_week"]
        assert len(dow_insights) == 0


class TestSleepPerformanceCorrelation:
    """Test sleep → next-day performance insight."""

    def test_detects_sleep_impact(self, engine):
        """Sleep <6h → lower next-day compliance."""
        base = datetime(2026, 1, 5)
        checkins = []
        for i in range(10):
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            # Even days: good sleep → good next day, odd days: bad sleep → bad next day
            sleep = 7.5 if i % 2 == 0 else 5.0
            # Compliance is SAME as sleep quality (good sleep day = good compliance)
            # But the function pairs sleep with NEXT day's compliance
            # So we need: good sleep day → next day has good compliance
            compliance = 85.0 if i % 2 == 1 else 55.0
            checkins.append(make_checkin(date, sleep_hours=sleep, compliance=compliance))

        insights = engine.generate_insights(checkins)
        sleep_insights = [i for i in insights if i["type"] == "sleep_performance"]

        assert len(sleep_insights) == 1
        assert "Sleep 7h+" in sleep_insights[0]["title"]

    def test_no_data_no_insight(self, engine):
        """Need at least 5 paired days."""
        checkins = [make_checkin("2026-01-0" + str(i)) for i in range(1, 5)]
        insights = engine.generate_insights(checkins)
        sleep_insights = [i for i in insights if i["type"] == "sleep_performance"]
        assert len(sleep_insights) == 0


class TestMoodEnergyPatterns:
    """Test mood/energy correlation insights."""

    def test_detects_mood_correlation(self, engine):
        """Strong sleep-mood correlation detected."""
        base = datetime(2026, 1, 5)
        checkins = []
        for i in range(10):
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            sleep = 7.5 if i % 2 == 0 else 5.0
            mood = 8 if i % 2 == 0 else 4
            energy = 8 if i % 2 == 0 else 3
            training = i % 3 != 0  # vary training to avoid constant input
            deep_work = i % 2 == 0  # vary deep_work to avoid constant hours
            checkins.append(make_checkin(date, sleep_hours=sleep, mood=mood, energy=energy, training=training, deep_work=deep_work))

        insights = engine.generate_insights(checkins)
        mood_insights = [i for i in insights if i["type"] == "mood_correlation"]

        assert len(mood_insights) == 1
        assert "sleep" in mood_insights[0]["title"].lower()

    def test_no_mood_data_no_insight(self, engine):
        """No mood data = no mood insight."""
        checkins = [make_checkin("2026-01-0" + str(i)) for i in range(1, 10)]
        insights = engine.generate_insights(checkins)
        mood_insights = [i for i in insights if i["type"] == "mood_correlation"]
        assert len(mood_insights) == 0


class TestRiskWindows:
    """Test risk window detection."""

    def test_detects_recent_decline(self, engine):
        """Compliance drop >15% triggers risk window."""
        base = datetime(2026, 1, 5)
        checkins = []
        for i in range(14):
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            # First week high, second week low
            compliance = 90.0 if i < 7 else 60.0
            checkins.append(make_checkin(date, compliance=compliance))

        insights = engine.generate_insights(checkins)
        risk_insights = [i for i in insights if i["type"] == "risk_window"]

        assert len(risk_insights) == 1
        assert "dropped" in risk_insights[0]["title"]

    def test_low_compliance_triggers_risk(self, engine):
        """Recent avg <60% triggers risk."""
        base = datetime(2026, 1, 5)
        checkins = []
        for i in range(7):
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            checkins.append(make_checkin(date, compliance=50.0))

        insights = engine.generate_insights(checkins)
        risk_insights = [i for i in insights if i["type"] == "risk_window"]

        assert len(risk_insights) == 1
        assert "below 60%" in risk_insights[0]["title"]


class TestEdgeCases:
    """Test edge cases and minimum data requirements."""

    def test_less_than_7_checkins(self, engine):
        """Need at least 7 check-ins for any insights."""
        checkins = [make_checkin("2026-01-0" + str(i)) for i in range(1, 6)]
        insights = engine.generate_insights(checkins)
        assert len(insights) == 0

    def test_insight_structure(self, engine):
        """All insights have required fields."""
        base = datetime(2026, 1, 5)
        checkins = []
        for i in range(21):
            date = (base + timedelta(days=i)).strftime("%Y-%m-%d")
            compliance = 50.0 if i % 7 == 5 else 85.0
            checkins.append(make_checkin(date, compliance=compliance, energy=7, mood=7))

        insights = engine.generate_insights(checkins)
        for insight in insights:
            assert "type" in insight
            assert "title" in insight
            assert "suggestion" in insight
            assert "data" in insight
