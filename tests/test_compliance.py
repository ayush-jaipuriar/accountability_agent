"""
Unit Tests for Compliance Score Calculation
===========================================

These tests verify that compliance score calculation works correctly.

Why Unit Tests?
- Catch bugs early (before deploying)
- Document expected behavior
- Prevent regressions (ensure fixes don't break things)
- Fast feedback (run in seconds)

Run tests:
    pytest tests/test_compliance.py -v
"""

import pytest
from src.models.schemas import Tier1NonNegotiables
from src.utils.compliance import (
    calculate_compliance_score,
    get_compliance_level,
    get_compliance_emoji,
    get_missed_items
)


# ===== Test: Compliance Score Calculation =====

def test_compliance_score_all_complete():
    """Test 100% compliance when all 6 items completed (Phase 3D: 6 items)."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        skill_building=True,  # Phase 3D: 6th item
        zero_porn=True,
        boundaries=True
    )
    
    score = calculate_compliance_score(tier1)
    assert score == 100.0


def test_compliance_score_all_incomplete():
    """Test 0% compliance when no items completed."""
    tier1 = Tier1NonNegotiables(
        sleep=False,
        training=False,
        deep_work=False,
        zero_porn=False,
        boundaries=False
    )
    
    score = calculate_compliance_score(tier1)
    assert score == 0.0


def test_compliance_score_partial():
    """Test ~83.3% compliance when 5/6 items completed (Phase 3D: 6 items)."""
    tier1 = Tier1NonNegotiables(
        sleep=False,  # Only one missed
        training=True,
        deep_work=True,
        skill_building=True,  # Phase 3D: 6th item
        zero_porn=True,
        boundaries=True
    )
    
    score = calculate_compliance_score(tier1)
    expected = (5 / 6) * 100  # 83.33% with 6-item denominator
    assert abs(score - expected) < 0.01


def test_compliance_score_half():
    """Test ~66.7% compliance when 4/6 items completed (Phase 3D: 6 items)."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        skill_building=True,  # Phase 3D: 6th item
        zero_porn=False,
        boundaries=False
    )
    
    score = calculate_compliance_score(tier1)
    expected = (4 / 6) * 100  # 66.67% with 6-item denominator
    assert abs(score - expected) < 0.01


# ===== Test: Compliance Level Categorization =====

def test_compliance_level_excellent():
    """Test 'excellent' level for 90-100%."""
    assert get_compliance_level(100.0) == "excellent"
    assert get_compliance_level(90.0) == "excellent"


def test_compliance_level_good():
    """Test 'good' level for 80-89%."""
    assert get_compliance_level(89.0) == "good"
    assert get_compliance_level(80.0) == "good"


def test_compliance_level_warning():
    """Test 'warning' level for 60-79%."""
    assert get_compliance_level(79.0) == "warning"
    assert get_compliance_level(60.0) == "warning"


def test_compliance_level_critical():
    """Test 'critical' level for <60%."""
    assert get_compliance_level(59.0) == "critical"
    assert get_compliance_level(0.0) == "critical"


# ===== Test: Emoji Selection =====

def test_compliance_emoji():
    """Test correct emoji for each level."""
    assert get_compliance_emoji(100.0) == "🎯"  # excellent
    assert get_compliance_emoji(85.0) == "✅"   # good
    assert get_compliance_emoji(70.0) == "⚠️"   # warning
    assert get_compliance_emoji(50.0) == "🚨"   # critical


# ===== Test: Missed Items Detection =====

def test_get_missed_items_none():
    """Test when no items missed (all 6 items complete)."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        skill_building=True,  # Phase 3D: 6th item
        zero_porn=True,
        boundaries=True
    )
    
    missed = get_missed_items(tier1)
    assert missed == []


def test_get_missed_items_one():
    """Test when one item missed (with all 6 items)."""
    tier1 = Tier1NonNegotiables(
        sleep=False,  # Missed
        training=True,
        deep_work=True,
        skill_building=True,  # Phase 3D: 6th item
        zero_porn=True,
        boundaries=True
    )
    
    missed = get_missed_items(tier1)
    assert missed == ["sleep"]


def test_get_missed_items_multiple():
    """Test when multiple items missed (with all 6 items)."""
    tier1 = Tier1NonNegotiables(
        sleep=False,
        training=False,
        deep_work=True,
        skill_building=True,  # Phase 3D: 6th item
        zero_porn=False,
        boundaries=True
    )
    
    missed = get_missed_items(tier1)
    assert set(missed) == {"sleep", "training", "zero_porn"}


# ===== Test: Edge Cases =====

def test_compliance_score_with_details():
    """Test that optional details don't affect score (Phase 3D: 6 items)."""
    tier1_with_details = Tier1NonNegotiables(
        sleep=True,
        sleep_hours=7.5,
        training=True,
        is_rest_day=True,
        training_type="rest",
        deep_work=True,
        deep_work_hours=2.5,
        skill_building=True,  # Phase 3D: 6th item
        zero_porn=True,
        boundaries=True
    )
    
    tier1_without_details = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        skill_building=True,  # Phase 3D: 6th item
        zero_porn=True,
        boundaries=True
    )
    
    score_with = calculate_compliance_score(tier1_with_details)
    score_without = calculate_compliance_score(tier1_without_details)
    
    assert score_with == score_without == 100.0


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
