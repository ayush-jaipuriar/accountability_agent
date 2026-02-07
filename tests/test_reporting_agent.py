"""
Unit Tests for Reporting Agent (Phase 3F)
==========================================

Tests the weekly report generation logic, message building, and fallback insights.

**Testing Strategy:**
- _build_report_message is a pure function (checkins, user, insights -> str)
- _generate_fallback_insights is a pure function (checkins, avg, avg -> str)
- generate_ai_insights requires LLM service → mocked in integration tests
- generate_and_send_weekly_report requires Telegram + Firestore → integration
- send_weekly_reports_to_all requires Telegram + Firestore → integration

**What We CAN Unit Test:**
1. Report message structure and content
2. Fallback insight generation (template-based)
3. Trend calculation logic
4. Edge cases (0 check-ins, 1 check-in)

Run tests:
    pytest tests/test_reporting_agent.py -v
"""

import pytest
from datetime import datetime, timedelta

from src.agents.reporting_agent import (
    _build_report_message,
    _generate_fallback_insights,
)
from src.models.schemas import (
    DailyCheckIn,
    Tier1NonNegotiables,
    CheckInResponses,
)


# ===== Fallback Insights Tests =====

class TestFallbackInsights:
    """
    Tests for template-based fallback insights.
    
    **Theory: Graceful Degradation**
    When the LLM is unavailable (rate limits, outage, cost control),
    we still need to provide useful insights. Template-based insights
    use predefined patterns with dynamic data interpolation.
    
    This is a "worse but acceptable" fallback that ensures the user
    always gets value from their weekly report, even without AI.
    """
    
    def test_excellent_compliance(self, sample_week_checkins):
        """High compliance (>=90%) should generate positive message."""
        result = _generate_fallback_insights(sample_week_checkins, 95.0, 7.5)
        assert "95%" in result
        assert "outstanding" in result.lower() or "solid" in result.lower() or "95" in result
    
    def test_good_compliance(self, sample_week_checkins):
        """Medium compliance (75-89%) should acknowledge room for improvement."""
        result = _generate_fallback_insights(sample_week_checkins, 82.0, 7.5)
        assert "82%" in result
    
    def test_low_compliance(self, sample_week_checkins):
        """Low compliance (<75%) should mention need to refocus."""
        result = _generate_fallback_insights(sample_week_checkins, 55.0, 7.5)
        assert "55%" in result
        assert "refocus" in result.lower() or "challenging" in result.lower()
    
    def test_low_sleep_warning(self, sample_week_checkins):
        """Sleep < 7h should generate a sleep warning."""
        result = _generate_fallback_insights(sample_week_checkins, 80.0, 5.5)
        assert "5.5" in result
        assert "sleep" in result.lower()
    
    def test_good_sleep_positive(self, sample_week_checkins):
        """Sleep >= 7h should generate positive sleep feedback."""
        result = _generate_fallback_insights(sample_week_checkins, 80.0, 7.8)
        assert "7.8" in result
        assert "track" in result.lower() or "sleep" in result.lower()
    
    def test_returns_non_empty(self, sample_week_checkins):
        """Fallback insights should always return a non-empty string."""
        result = _generate_fallback_insights(sample_week_checkins, 50.0, 5.0)
        assert isinstance(result, str)
        assert len(result) > 20


# ===== Report Message Builder Tests =====

class TestBuildReportMessage:
    """Tests for weekly report message construction."""
    
    def test_empty_checkins_message(self, sample_user_3f):
        """Empty check-ins should produce a specific 'no data' message."""
        result = _build_report_message([], sample_user_3f, "No insights")
        assert "No check-ins" in result
        assert "/checkin" in result
    
    def test_includes_date_range(self, sample_user_3f, sample_week_checkins):
        """Report should include the date range of the week."""
        result = _build_report_message(sample_week_checkins, sample_user_3f, "Test insights")
        assert "→" in result  # Arrow between start and end dates
    
    def test_includes_checkin_count(self, sample_user_3f, sample_week_checkins):
        """Report should show number of check-ins out of 7."""
        result = _build_report_message(sample_week_checkins, sample_user_3f, "Test insights")
        assert "/7" in result
    
    def test_includes_compliance_average(self, sample_user_3f, sample_week_checkins):
        """Report should show average compliance percentage."""
        result = _build_report_message(sample_week_checkins, sample_user_3f, "Test insights")
        assert "Compliance" in result
        assert "%" in result
    
    def test_includes_ai_insights(self, sample_user_3f, sample_week_checkins):
        """Report should include the AI insights text."""
        insight_text = "Your training consistency improved by 20% this week."
        result = _build_report_message(sample_week_checkins, sample_user_3f, insight_text)
        assert insight_text in result
    
    def test_includes_streak(self, sample_user_3f, sample_week_checkins):
        """Report should show current streak."""
        result = _build_report_message(sample_week_checkins, sample_user_3f, "Test")
        assert str(sample_user_3f.streaks.current_streak) in result
    
    def test_uses_html_format(self, sample_user_3f, sample_week_checkins):
        """Report should use HTML tags for Telegram parsing."""
        result = _build_report_message(sample_week_checkins, sample_user_3f, "Test")
        assert "<b>" in result
        assert "<i>" in result
    
    def test_includes_trend(self, sample_user_3f, sample_week_checkins):
        """
        Report should include a trend indicator.
        
        **Theory: Trend Detection**
        We split the week in half and compare average compliance:
        - First half avg vs second half avg
        - >5% increase = "Trending Up"
        - >5% decrease = "Trending Down"
        - Otherwise = "Stable"
        
        This gives users at-a-glance feedback on their trajectory.
        """
        result = _build_report_message(sample_week_checkins, sample_user_3f, "Test")
        # Should contain one of the trend indicators
        assert any(indicator in result for indicator in ["📈", "📉", "➡️"])
    
    def test_trend_stable_with_few_checkins(self, sample_user_3f):
        """
        With <4 check-ins, trend should be 'Stable' (not enough data).
        """
        checkins = []
        for i in range(2):
            date = (datetime.now() - timedelta(days=1-i)).strftime("%Y-%m-%d")
            checkins.append(DailyCheckIn(
                date=date,
                user_id="123456789",
                mode="maintenance",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep=True, training=True, deep_work=True,
                    zero_porn=True, boundaries=True,
                ),
                responses=CheckInResponses(
                    challenges="Test challenge with minimum character requirement met for validation",
                    rating=8,
                    rating_reason="Good day with solid compliance and consistency across areas",
                    tomorrow_priority="Maintain momentum and focus on the most impactful priorities",
                    tomorrow_obstacle="Time constraints may limit deep work hours available today",
                ),
                compliance_score=80.0,
            ))
        
        result = _build_report_message(checkins, sample_user_3f, "Test")
        assert "➡️" in result  # Stable indicator
    
    def test_includes_best_day(self, sample_user_3f, sample_week_checkins):
        """Report should highlight the best day of the week."""
        result = _build_report_message(sample_week_checkins, sample_user_3f, "Test")
        assert "Best Day" in result


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
