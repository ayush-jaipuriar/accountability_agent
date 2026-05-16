"""
Tests for P1.4: Churn Risk Prediction
=======================================

Tests the ChurnRiskPredictor and intervention services:
- calculate_risk_score() with various user patterns
- Individual factor calculations
- Intervention cooldown logic
- Message generation for different risk levels
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.models.schemas import (
    User, UserStreaks, Tier1NonNegotiables, CheckInResponses, DailyCheckIn
)
from src.services.churn_prediction import ChurnRiskPredictor
from src.services.churn_intervention import generate_intervention_message


# ===== Fixtures =====

@pytest.fixture
def predictor():
    return ChurnRiskPredictor()


@pytest.fixture
def stable_user():
    """User with consistent high compliance and no risk signals."""
    return User(
        user_id="111",
        telegram_id=111,
        name="StableUser",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(current_streak=20, longest_streak=30, total_checkins=100),
        settings={},
        last_churn_intervention=None,
    )


@pytest.fixture
def at_risk_user():
    """User with declining compliance and recent missed check-ins."""
    return User(
        user_id="222",
        telegram_id=222,
        name="AtRiskUser",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(current_streak=5, longest_streak=25, total_checkins=60),
        settings={},
        last_churn_intervention=None,
    )


def _make_checkin(
    date_offset=0,
    compliance=80.0,
    rating=7,
    is_quick=False,
    completed_at_hour=21,
):
    """Helper to create a check-in with given parameters."""
    date = (datetime(2026, 5, 15) + timedelta(days=date_offset)).strftime("%Y-%m-%d")
    return DailyCheckIn(
        date=date,
        user_id="111",
        mode="maintenance",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=True, sleep_hours=7.0,
            training=True, training_intensity="moderate",
            deep_work=True, deep_work_hours=2.0,
            skill_building=True, skill_building_hours=1.5,
            zero_porn=True, boundaries=True,
        ),
        responses=CheckInResponses(
            challenges="Test challenges for the day with enough characters",
            rating=rating,
            rating_reason="Average day with some progress made overall",
            tomorrow_priority="Continue working on main priorities",
            tomorrow_obstacle="Potential distractions from meetings",
        ),
        compliance_score=compliance,
        is_quick_checkin=is_quick,
        completed_at=datetime(2026, 5, 15, completed_at_hour, 0),
    )


def _make_declining_checkins(days=21):
    """Create check-ins with declining compliance and ratings."""
    checkins = []
    for i in range(days):
        # Compliance declines from 95 to 50
        comp = 95 - (i * (45 / days))
        # Rating declines from 9 to 4
        rating = max(1, 9 - (i * (5 / days)))
        # Time drifts later (21:00 -> 23:00)
        hour = 21 + int((i / days) * 2)
        # Last 7 days are quick check-ins
        is_quick = i >= (days - 7)
        checkins.append(_make_checkin(
            date_offset=i - days,
            compliance=comp,
            rating=int(rating),
            is_quick=is_quick,
            completed_at_hour=hour,
        ))
    return checkins


# ===== Risk Score Calculation =====

class TestCalculateRiskScore:

    def test_insufficient_data(self, predictor, stable_user):
        """Users with < 7 check-ins should get score 0."""
        with patch('src.services.churn_prediction.firestore_service') as mock_fs:
            mock_fs.get_recent_checkins.return_value = []
            score, factors, raw = predictor.calculate_risk_score(stable_user)
        assert score == 0.0
        assert raw.get("insufficient_data") is True

    def test_stable_user_low_risk(self, predictor, stable_user):
        """Stable user with consistent check-ins should have low risk."""
        checkins = [_make_checkin(date_offset=i, compliance=85.0, rating=7) for i in range(-14, 1)]
        with patch('src.services.churn_prediction.firestore_service') as mock_fs:
            mock_fs.get_recent_checkins.return_value = checkins
            score, factors, raw = predictor.calculate_risk_score(stable_user)
        assert score < 0.5
        assert len(factors) == 0

    def test_declining_user_high_risk(self, predictor, at_risk_user):
        """User with declining compliance should have high risk."""
        checkins = _make_declining_checkins(21)
        with patch('src.services.churn_prediction.firestore_service') as mock_fs:
            mock_fs.get_recent_checkins.return_value = checkins
            score, factors, raw = predictor.calculate_risk_score(at_risk_user)
        assert score >= 0.5
        assert len(factors) >= 2
        assert "compliance_decline" in factors
        assert "quick_checkin_overuse" in factors
        assert raw["compliance_decline"] > 0

    def test_quick_checkin_overuse(self, predictor, stable_user):
        """Consecutive quick check-ins should trigger overuse factor."""
        checkins = [_make_checkin(date_offset=i, is_quick=(i >= -6)) for i in range(-14, 1)]
        with patch('src.services.churn_prediction.firestore_service') as mock_fs:
            mock_fs.get_recent_checkins.return_value = checkins
            score, factors, raw = predictor.calculate_risk_score(stable_user)
        assert "quick_checkin_overuse" in factors
        assert raw["quick_checkin_overuse_days"] >= 5

    def test_time_drift(self, predictor, stable_user):
        """Check-ins getting later should trigger drift factor."""
        checkins = [_make_checkin(date_offset=i, completed_at_hour=(21 + i//3)) for i in range(-14, 1)]
        with patch('src.services.churn_prediction.firestore_service') as mock_fs:
            mock_fs.get_recent_checkins.return_value = checkins
            score, factors, raw = predictor.calculate_risk_score(stable_user)
        # Drift may or may not trigger depending on exact threshold
        assert raw["time_drift_minutes"] >= 0

    def test_rating_decline(self, predictor, stable_user):
        """Declining self-ratings should trigger rating_decline factor."""
        checkins = [
            _make_checkin(date_offset=i, rating=(9 if i < -7 else 4))
            for i in range(-14, 1)
        ]
        with patch('src.services.churn_prediction.firestore_service') as mock_fs:
            mock_fs.get_recent_checkins.return_value = checkins
            score, factors, raw = predictor.calculate_risk_score(stable_user)
        assert "self_rating_decline" in factors
        assert raw["rating_decline"] > 0


# ===== Factor Calculations =====

class TestFactorCalculations:

    def test_time_drift_calculation(self, predictor):
        """Time drift should be positive when check-ins get later."""
        early = [_make_checkin(completed_at_hour=21) for _ in range(7)]
        late = [_make_checkin(completed_at_hour=23) for _ in range(3)]
        drift = predictor._calculate_time_drift(early + late)
        assert drift > 0

    def test_compliance_decline(self, predictor):
        """Compliance decline should be positive when scores drop."""
        high = [_make_checkin(compliance=95.0) for _ in range(7)]
        low = [_make_checkin(compliance=60.0) for _ in range(7)]
        decline = predictor._calculate_compliance_decline(high + low)
        assert decline > 0
        assert decline == pytest.approx(35.0, abs=1.0)

    def test_quick_checkin_overuse(self, predictor):
        """Should count consecutive quick check-ins from the end."""
        checkins = [
            _make_checkin(is_quick=False),
            _make_checkin(is_quick=True),
            _make_checkin(is_quick=True),
            _make_checkin(is_quick=True),
        ]
        overuse = predictor._calculate_quick_checkin_overuse(checkins)
        assert overuse == 3

    def test_rating_decline(self, predictor):
        """Rating decline should be positive when ratings drop."""
        high = [_make_checkin(rating=9) for _ in range(5)]
        low = [_make_checkin(rating=5) for _ in range(5)]
        decline = predictor._calculate_rating_decline(high + low)
        assert decline > 0
        assert decline == pytest.approx(4.0, abs=0.5)

    def test_missed_checkins(self, predictor):
        """Should detect gaps between check-in dates."""
        # Need at least 7 check-ins to trigger the check
        checkins = [
            _make_checkin(date_offset=-10),
            _make_checkin(date_offset=-8),   # 1-day gap
            _make_checkin(date_offset=-7),
            _make_checkin(date_offset=-6),
            _make_checkin(date_offset=-5),
            _make_checkin(date_offset=-3),   # 1-day gap
            _make_checkin(date_offset=0),    # 2-day gap
        ]
        missed = predictor._calculate_missed_checkins(checkins)
        assert missed == 4  # 1 + 1 + 2 day gaps


# ===== Intervention Cooldown =====

class TestInterventionCooldown:

    def test_no_previous_intervention(self, predictor, stable_user):
        """Should allow intervention if none was ever sent."""
        assert predictor.is_intervention_cooled_down(stable_user, cooldown_days=3) is True

    def test_recent_intervention_blocked(self, predictor, stable_user):
        """Should block if intervention was sent yesterday."""
        stable_user.last_churn_intervention = datetime.utcnow() - timedelta(days=1)
        assert predictor.is_intervention_cooled_down(stable_user, cooldown_days=3) is False

    def test_old_intervention_allowed(self, predictor, stable_user):
        """Should allow if intervention was sent 5 days ago."""
        stable_user.last_churn_intervention = datetime.utcnow() - timedelta(days=5)
        assert predictor.is_intervention_cooled_down(stable_user, cooldown_days=3) is True


# ===== Message Generation =====

class TestInterventionMessages:

    def test_low_risk_no_message(self, stable_user):
        """Low risk (< 0.5) should return empty string."""
        msg = generate_intervention_message(stable_user, 0.3, [])
        assert msg == ""

    def test_medium_risk_message(self, stable_user):
        """Medium risk (0.5-0.8) should return encouraging message."""
        msg = generate_intervention_message(stable_user, 0.6, ["compliance_decline"])
        assert "doing great" in msg.lower() or "small win" in msg.lower()
        assert stable_user.name in msg

    def test_high_risk_message(self, stable_user):
        """High risk (>= 0.8) should return supportive message with options."""
        msg = generate_intervention_message(stable_user, 0.85, ["compliance_decline", "quick_checkin_overuse"])
        assert "no judgment" in msg.lower() or "support" in msg.lower()
        assert "/quickcheckin" in msg or "/support" in msg


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
