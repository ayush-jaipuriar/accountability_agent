"""
Analytics Service Tests
=======================

Tests for weekly, monthly, and yearly stats calculations.

**Testing Strategy:**
The analytics service fetches data from Firestore then computes stats.
We mock Firestore and provide known check-in data, then verify the
computed statistics are correct.

**What We Test:**
- Weekly stats (7-day summary)
- Monthly stats (30-day summary with weekly breakdown)
- Yearly stats (year-to-date)
- Tier 1 stats calculation
- Weekly breakdown calculation
- Percentile estimation
"""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta
from statistics import mean

from src.models.schemas import (
    User, UserStreaks, DailyCheckIn, Tier1NonNegotiables,
    CheckInResponses
)


# ===== Fixtures =====

@pytest.fixture
def mock_firestore():
    """Mock Firestore service for analytics tests."""
    with patch('src.services.analytics_service.firestore_service') as mock_fs:
        yield mock_fs


@pytest.fixture
def test_user():
    """User for analytics testing."""
    return User(
        user_id="analytics_user",
        telegram_id=111,
        name="Analytics User",
        streaks=UserStreaks(
            current_streak=15,
            longest_streak=30,
            total_checkins=60,
            last_checkin_date="2026-02-07"
        ),
        constitution_mode="maintenance",
        career_mode="skill_building",
        achievements=["week_warrior", "month_master"],
    )


def _make_checkin(date_str, compliance, sleep=True, sleep_hours=7.5,
                  training=True, deep_work=True, dw_hours=2.5,
                  skill_building=False, sb_hours=0, zero_porn=True,
                  boundaries=True):
    """Helper to create a check-in with minimal boilerplate."""
    return DailyCheckIn(
        date=date_str,
        user_id="analytics_user",
        mode="maintenance",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=sleep, sleep_hours=sleep_hours,
            training=training, deep_work=deep_work,
            deep_work_hours=dw_hours,
            skill_building=skill_building,
            skill_building_hours=sb_hours,
            zero_porn=zero_porn, boundaries=boundaries,
        ),
        responses=CheckInResponses(
            challenges="Test challenges for the day with enough character length for valid data",
            rating=8,
            rating_reason="Test rating reason with sufficient length to pass the validation check",
            tomorrow_priority="Tomorrow's priority test data with enough characters for validation",
            tomorrow_obstacle="Tomorrow's obstacle test data with enough characters for validation",
        ),
        compliance_score=compliance,
    )


@pytest.fixture
def seven_day_checkins():
    """7 days of check-ins with known values."""
    return [
        _make_checkin("2026-02-01", 100.0, sleep_hours=8.0, skill_building=True, sb_hours=2.0),
        _make_checkin("2026-02-02", 83.3, sleep_hours=7.5, training=False),
        _make_checkin("2026-02-03", 66.7, sleep=False, sleep_hours=5.0, training=False),
        _make_checkin("2026-02-04", 100.0, sleep_hours=7.0, skill_building=True, sb_hours=2.5),
        _make_checkin("2026-02-05", 83.3, sleep_hours=7.8, boundaries=False),
        _make_checkin("2026-02-06", 100.0, sleep_hours=8.2, skill_building=True, sb_hours=3.0),
        _make_checkin("2026-02-07", 83.3, sleep_hours=7.0, deep_work=False, dw_hours=1.0),
    ]


# ===== Weekly Stats Tests =====

class TestWeeklyStats:
    """Tests for calculate_weekly_stats()."""

    def test_weekly_stats_basic(self, mock_firestore, test_user, seven_day_checkins):
        """Should calculate basic weekly statistics."""
        from src.services.analytics_service import calculate_weekly_stats
        
        mock_firestore.get_user.return_value = test_user
        mock_firestore.get_recent_checkins.return_value = seven_day_checkins
        mock_firestore.get_patterns.return_value = []
        
        stats = calculate_weekly_stats("analytics_user")
        
        assert stats["has_data"] is True
        assert stats["period"] == "Last 7 Days"
        assert "compliance" in stats
        assert "streaks" in stats
        assert "tier1" in stats

    def test_weekly_compliance_average(self, mock_firestore, test_user, seven_day_checkins):
        """Should compute correct average compliance."""
        from src.services.analytics_service import calculate_weekly_stats
        
        mock_firestore.get_user.return_value = test_user
        mock_firestore.get_recent_checkins.return_value = seven_day_checkins
        mock_firestore.get_patterns.return_value = []
        
        stats = calculate_weekly_stats("analytics_user")
        
        expected_avg = mean([c.compliance_score for c in seven_day_checkins])
        assert abs(stats["compliance"]["average"] - expected_avg) < 0.1

    def test_weekly_no_checkins(self, mock_firestore, test_user):
        """Should return error when no check-ins found."""
        from src.services.analytics_service import calculate_weekly_stats
        
        mock_firestore.get_user.return_value = test_user
        mock_firestore.get_recent_checkins.return_value = []
        mock_firestore.get_patterns.return_value = []
        
        stats = calculate_weekly_stats("analytics_user")
        
        assert stats["has_data"] is False
        assert "error" in stats

    def test_weekly_streak_info(self, mock_firestore, test_user, seven_day_checkins):
        """Should include streak information."""
        from src.services.analytics_service import calculate_weekly_stats
        
        mock_firestore.get_user.return_value = test_user
        mock_firestore.get_recent_checkins.return_value = seven_day_checkins
        mock_firestore.get_patterns.return_value = []
        
        stats = calculate_weekly_stats("analytics_user")
        
        assert stats["streaks"]["current"] == 15
        assert stats["streaks"]["checkin_rate"] == "7/7"


# ===== Monthly Stats Tests =====

class TestMonthlyStats:
    """Tests for calculate_monthly_stats()."""

    def test_monthly_stats_basic(self, mock_firestore, test_user, seven_day_checkins):
        """Should calculate monthly statistics."""
        from src.services.analytics_service import calculate_monthly_stats
        
        # Extend to 30 days
        thirty_day_checkins = seven_day_checkins * 4 + seven_day_checkins[:2]
        
        mock_firestore.get_user.return_value = test_user
        mock_firestore.get_recent_checkins.return_value = thirty_day_checkins
        mock_firestore.get_patterns.return_value = []
        
        stats = calculate_monthly_stats("analytics_user")
        
        assert stats["has_data"] is True
        assert "social_proof" in stats
        assert "achievements" in stats

    def test_monthly_includes_percentile(self, mock_firestore, test_user, seven_day_checkins):
        """Should include percentile rank."""
        from src.services.analytics_service import calculate_monthly_stats
        
        thirty_day_checkins = seven_day_checkins * 4 + seven_day_checkins[:2]
        
        mock_firestore.get_user.return_value = test_user
        mock_firestore.get_recent_checkins.return_value = thirty_day_checkins
        mock_firestore.get_patterns.return_value = []
        
        stats = calculate_monthly_stats("analytics_user")
        
        assert "percentile" in stats["social_proof"]
        assert isinstance(stats["social_proof"]["percentile"], int)


# ===== Yearly Stats Tests =====

class TestYearlyStats:
    """Tests for calculate_yearly_stats()."""

    def test_yearly_stats_basic(self, mock_firestore, test_user, seven_day_checkins):
        """Should calculate year-to-date statistics."""
        from src.services.analytics_service import calculate_yearly_stats
        
        mock_firestore.get_user.return_value = test_user
        mock_firestore.get_recent_checkins.return_value = seven_day_checkins
        mock_firestore.get_patterns.return_value = []
        
        stats = calculate_yearly_stats("analytics_user")
        
        assert stats["has_data"] is True
        assert "career_progress" in stats
        assert stats["career_progress"]["career_mode"] == "skill_building"

    def test_yearly_career_tracking(self, mock_firestore, test_user, seven_day_checkins):
        """Should track skill building days for career progress."""
        from src.services.analytics_service import calculate_yearly_stats
        
        mock_firestore.get_user.return_value = test_user
        mock_firestore.get_recent_checkins.return_value = seven_day_checkins
        mock_firestore.get_patterns.return_value = []
        
        stats = calculate_yearly_stats("analytics_user")
        
        # Count skill building days in fixture
        expected_sb = sum(1 for c in seven_day_checkins if c.tier1_non_negotiables.skill_building)
        assert stats["career_progress"]["skill_building_days"] == expected_sb


# ===== Tier 1 Stats Tests =====

class TestTier1Stats:
    """Tests for _calculate_tier1_stats helper."""

    def test_tier1_all_six_items(self, seven_day_checkins):
        """Should track all 6 Tier 1 items (Phase 3D expansion)."""
        from src.services.analytics_service import _calculate_tier1_stats
        
        stats = _calculate_tier1_stats(seven_day_checkins)
        
        assert "sleep" in stats
        assert "training" in stats
        assert "deep_work" in stats
        assert "skill_building" in stats
        assert "zero_porn" in stats
        assert "boundaries" in stats

    def test_tier1_sleep_stats(self, seven_day_checkins):
        """Should calculate correct sleep completion rate and average hours."""
        from src.services.analytics_service import _calculate_tier1_stats
        
        stats = _calculate_tier1_stats(seven_day_checkins)
        
        # 6 out of 7 days had sleep=True
        assert stats["sleep"]["days"] == 6
        assert stats["sleep"]["total"] == 7
        assert abs(stats["sleep"]["pct"] - (6/7) * 100) < 0.1
        assert stats["sleep"]["avg_hours"] > 0
        assert stats["sleep"]["target"] == 7.0

    def test_tier1_training_stats(self, seven_day_checkins):
        """Should calculate correct training completion rate."""
        from src.services.analytics_service import _calculate_tier1_stats
        
        stats = _calculate_tier1_stats(seven_day_checkins)
        
        # 5 out of 7 days had training=True
        assert stats["training"]["days"] == 5
        assert stats["training"]["pct"] == pytest.approx((5/7) * 100, abs=0.1)


# ===== Percentile Estimation Tests =====

class TestPercentileEstimation:
    """Tests for the simplified percentile estimation."""

    def test_high_compliance_top_10(self):
        """95%+ compliance should be top 10%."""
        from src.services.analytics_service import _estimate_percentile
        assert _estimate_percentile(95) == 90
        assert _estimate_percentile(100) == 90

    def test_good_compliance_top_20(self):
        """85-94% compliance should be top 20%."""
        from src.services.analytics_service import _estimate_percentile
        assert _estimate_percentile(85) == 80
        assert _estimate_percentile(94) == 80

    def test_moderate_compliance_top_40(self):
        """75-84% compliance should be top 40%."""
        from src.services.analytics_service import _estimate_percentile
        assert _estimate_percentile(75) == 60
        assert _estimate_percentile(84) == 60

    def test_below_average_compliance(self):
        """<65% compliance should be top 80%."""
        from src.services.analytics_service import _estimate_percentile
        assert _estimate_percentile(50) == 20
        assert _estimate_percentile(64) == 20


# ===== Weekly Breakdown Tests =====

class TestWeeklyBreakdown:
    """Tests for _calculate_weekly_breakdown helper."""

    def test_produces_4_weeks(self):
        """Should produce 4 weekly summaries from 30 days."""
        from src.services.analytics_service import _calculate_weekly_breakdown
        
        checkins = [_make_checkin(f"2026-02-{i+1:02d}", 80.0) for i in range(28)]
        
        weeks = _calculate_weekly_breakdown(checkins)
        
        assert len(weeks) == 4
        for week in weeks:
            assert "week_num" in week
            assert "avg_compliance" in week
            assert "days" in week

    def test_week_averages_correct(self):
        """Each week's average should reflect its check-ins."""
        from src.services.analytics_service import _calculate_weekly_breakdown
        
        # Week 1: all 100%, Week 2: all 50%
        checkins = (
            [_make_checkin(f"2026-02-{i+1:02d}", 100.0) for i in range(7)] +
            [_make_checkin(f"2026-02-{i+8:02d}", 50.0) for i in range(7)]
        )
        
        weeks = _calculate_weekly_breakdown(checkins)
        
        assert weeks[0]["avg_compliance"] == 100.0
        assert weeks[1]["avg_compliance"] == 50.0


# ===== Mood & Energy Analytics Tests =====

from src.services.analytics_service import (
    calculate_mood_energy_stats,
    calculate_mood_correlations,
    format_mood_energy_summary,
    calculate_partner_weekly_performance,
)


def _make_mood_checkin(date_str, energy=8, mood=8, sleep_hours=7.5, dw_hours=2.5, training=True):
    return DailyCheckIn(
        date=date_str,
        user_id="analytics_user",
        mode="maintenance",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=True, sleep_hours=sleep_hours,
            training=training, deep_work=True,
            deep_work_hours=dw_hours,
            skill_building=True, skill_building_hours=2.0,
            zero_porn=True, boundaries=True,
        ),
        responses=CheckInResponses(
            challenges="Test challenges with enough length",
            rating=8,
            rating_reason="Test rating reason with enough length",
            tomorrow_priority="Test priority with enough length",
            tomorrow_obstacle="Test obstacle with enough length",
            energy_rating=energy,
            mood_rating=mood,
        ),
        compliance_score=100,
    )


class TestMoodAndEnergyAnalytics:

    def test_calculate_mood_energy_stats_no_data(self):
        result = calculate_mood_energy_stats([])
        assert result["has_data"] is False

    def test_calculate_mood_energy_stats_with_data(self):
        checkins = [_make_mood_checkin(f"2026-02-{i+1:02d}", energy=7+i, mood=6+i) for i in range(3)]
        result = calculate_mood_energy_stats(checkins)
        assert result["has_data"] is True
        assert result["energy"]["avg"] == 8.0
        assert result["mood"]["avg"] == 7.0
        assert result["energy"]["count"] == 3

    def test_calculate_mood_correlations_insufficient_data(self):
        checkins = [_make_mood_checkin(f"2026-02-{i+1:02d}") for i in range(3)]
        result = calculate_mood_correlations(checkins)
        assert result["has_data"] is False
        assert "Need at least 5" in result["reason"]

    def test_calculate_mood_correlations_with_valid_data(self):
        # 6 days with varying sleep, dw, training and mood/energy
        checkins = [
            _make_mood_checkin("2026-02-01", energy=6, mood=6, sleep_hours=6.0, dw_hours=1.0, training=False),
            _make_mood_checkin("2026-02-02", energy=7, mood=7, sleep_hours=7.0, dw_hours=2.0, training=True),
            _make_mood_checkin("2026-02-03", energy=8, mood=8, sleep_hours=8.0, dw_hours=3.0, training=True),
            _make_mood_checkin("2026-02-04", energy=9, mood=9, sleep_hours=8.5, dw_hours=3.5, training=True),
            _make_mood_checkin("2026-02-05", energy=8, mood=8, sleep_hours=8.0, dw_hours=3.0, training=True),
            _make_mood_checkin("2026-02-06", energy=9, mood=9, sleep_hours=9.0, dw_hours=4.0, training=True),
        ]
        result = calculate_mood_correlations(checkins)
        assert result["has_data"] is True
        assert result["n"] == 6
        assert "sleep_mood_correlation" in result
        assert "best_combination" in result
        assert "top_mood_avg" in result

    def test_format_mood_energy_summary(self):
        # Empty
        assert format_mood_energy_summary([]) == ""

        # With checkins
        checkins = [_make_mood_checkin(f"2026-02-{i+1:02d}", energy=8, mood=9) for i in range(3)]
        summary = format_mood_energy_summary(checkins)
        assert "Mood & Energy" in summary
        assert "8.0/10" in summary
        assert "9.0/10" in summary

    def test_calculate_partner_weekly_performance(self):
        # Empty
        res_empty = calculate_partner_weekly_performance([])
        assert res_empty["has_data"] is False

        # With 7 days
        checkins = [_make_mood_checkin(f"2026-02-{i+1:02d}") for i in range(7)]
        res = calculate_partner_weekly_performance(checkins)
        assert res["has_data"] is True
        assert res["checkin_count"] == 7
        assert "habits" in res
        assert "strongest" in res
        assert "weakest" in res
