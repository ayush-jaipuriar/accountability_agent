"""
Test: Streak Recovery Service
==============================

Tests compassionate streak break handling.
"""

import pytest
from datetime import datetime

from src.services.streak_recovery_service import (
    format_recovery_ritual,
    analyze_break_patterns,
    BREAK_REASONS,
)


class TestRecoveryRitual:
    """Test recovery ritual message formatting."""

    def test_includes_previous_streak(self):
        msg = format_recovery_ritual(15)
        assert "15" in msg
        assert "Streak Broken" in msg

    def test_includes_three_parts(self):
        msg = format_recovery_ritual(10)
        assert "Acknowledge" in msg
        assert "Forgive" in msg
        assert "Restart" in msg

    def test_includes_quote(self):
        msg = format_recovery_ritual(5)
        assert "💡" in msg

    def test_includes_checkin_cta(self):
        msg = format_recovery_ritual(20)
        assert "/checkin" in msg

    def test_with_break_reason(self):
        msg = format_recovery_ritual(8, break_reason="sleep")
        assert "Poor Sleep" in msg


class TestBreakPatternAnalysis:
    """Test break pattern analysis."""

    def test_no_data(self):
        result = analyze_break_patterns([])
        assert result["has_data"] is False

    def test_finds_most_common(self):
        breaks = [
            {"date": "2026-01-01", "reason": "sleep"},
            {"date": "2026-01-02", "reason": "sleep"},
            {"date": "2026-01-03", "reason": "work"},
        ]
        result = analyze_break_patterns(breaks)
        assert result["has_data"] is True
        assert result["most_common_reason"] == "sleep"
        assert result["break_count"] == 3

    def test_distribution(self):
        breaks = [
            {"date": "2026-01-01", "reason": "sleep"},
            {"date": "2026-01-02", "reason": "sleep"},
            {"date": "2026-01-03", "reason": "work"},
        ]
        result = analyze_break_patterns(breaks)
        assert result["reason_distribution"]["sleep"] == 2
        assert result["reason_distribution"]["work"] == 1
