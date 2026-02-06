"""
Unit Tests for Phase 3D Day 1: Career Mode System
==================================================

Tests:
1. Adaptive skill building question generation
2. Tier 1 with 6 items (not 5)
3. Compliance calculation with 6 items
4. Career mode field in User model

Run with: pytest tests/test_phase3d_career_mode.py -v
"""

import pytest
from src.bot.conversation import get_skill_building_question
from src.models.schemas import Tier1NonNegotiables, User, UserStreaks
from src.utils.compliance import (
    calculate_compliance_score,
    get_tier1_breakdown,
    get_missed_items
)


# ===== Test 1: Adaptive Skill Building Question =====

def test_get_skill_building_question_skill_mode():
    """Test skill building question in skill_building mode."""
    result = get_skill_building_question("skill_building")
    
    assert "question" in result
    assert "label" in result
    assert "description" in result
    assert "📚 Skill Building" in result["label"]
    assert "LeetCode" in result["description"]
    print("✅ Test 1.1: skill_building mode - PASS")


def test_get_skill_building_question_job_mode():
    """Test skill building question in job_searching mode."""
    result = get_skill_building_question("job_searching")
    
    assert "question" in result
    assert "label" in result
    assert "description" in result
    assert "💼 Job Search" in result["label"]
    assert "Applications" in result["description"] or "interviews" in result["description"]
    print("✅ Test 1.2: job_searching mode - PASS")


def test_get_skill_building_question_employed_mode():
    """Test skill building question in employed mode."""
    result = get_skill_building_question("employed")
    
    assert "question" in result
    assert "label" in result
    assert "description" in result
    assert "🎯 Career" in result["label"]
    assert "promotion" in result["description"] or "raise" in result["description"]
    print("✅ Test 1.3: employed mode - PASS")


def test_get_skill_building_question_unknown_mode():
    """Test skill building question with unknown mode (fallback)."""
    result = get_skill_building_question("unknown_mode")
    
    # Should return default fallback
    assert "question" in result
    assert "label" in result
    assert "description" in result
    print("✅ Test 1.4: unknown mode fallback - PASS")


# ===== Test 2: Tier 1 with 6 Items =====

def test_tier1_has_6_items():
    """Test that Tier1NonNegotiables has 6 required fields."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        skill_building=True,  # NEW in Phase 3D
        zero_porn=True,
        boundaries=True
    )
    
    # Verify all 6 fields exist
    assert hasattr(tier1, 'sleep')
    assert hasattr(tier1, 'training')
    assert hasattr(tier1, 'deep_work')
    assert hasattr(tier1, 'skill_building')  # NEW field
    assert hasattr(tier1, 'zero_porn')
    assert hasattr(tier1, 'boundaries')
    
    # Verify values are correct
    assert tier1.sleep == True
    assert tier1.training == True
    assert tier1.deep_work == True
    assert tier1.skill_building == True
    assert tier1.zero_porn == True
    assert tier1.boundaries == True
    
    print("✅ Test 2.1: Tier 1 has 6 items - PASS")


def test_tier1_skill_building_default_false():
    """Test that skill_building defaults to False (backward compatibility)."""
    # Create tier1 without skill_building (simulating old data)
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        # skill_building NOT provided (should default to False)
        zero_porn=True,
        boundaries=True
    )
    
    # Should default to False
    assert tier1.skill_building == False
    print("✅ Test 2.2: skill_building defaults to False - PASS")


def test_tier1_skill_building_optional_fields():
    """Test that skill_building has optional hours and activity fields."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        skill_building=True,
        skill_building_hours=2.5,
        skill_building_activity="LeetCode",
        zero_porn=True,
        boundaries=True
    )
    
    assert tier1.skill_building_hours == 2.5
    assert tier1.skill_building_activity == "LeetCode"
    print("✅ Test 2.3: skill_building optional fields - PASS")


# ===== Test 3: Compliance Calculation with 6 Items =====

def test_compliance_score_all_6_items_complete():
    """Test compliance score with all 6 items completed."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        skill_building=True,
        zero_porn=True,
        boundaries=True
    )
    
    score = calculate_compliance_score(tier1)
    assert score == 100.0
    print("✅ Test 3.1: 6/6 items = 100% - PASS")


def test_compliance_score_5_of_6_items():
    """Test compliance score with 5 of 6 items completed."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=False,  # Missing this one
        skill_building=True,
        zero_porn=True,
        boundaries=True
    )
    
    score = calculate_compliance_score(tier1)
    expected = (5/6) * 100  # 83.33...
    assert abs(score - expected) < 0.01  # Allow small floating point difference
    print(f"✅ Test 3.2: 5/6 items = {score:.2f}% (expected ~83.33%) - PASS")


def test_compliance_score_4_of_6_items():
    """Test compliance score with 4 of 6 items completed."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=False,  # Missing
        skill_building=False,  # Missing
        zero_porn=True,
        boundaries=True
    )
    
    score = calculate_compliance_score(tier1)
    expected = (4/6) * 100  # 66.67...
    assert abs(score - expected) < 0.01
    print(f"✅ Test 3.3: 4/6 items = {score:.2f}% (expected ~66.67%) - PASS")


def test_compliance_score_3_of_6_items():
    """Test compliance score with 3 of 6 items completed."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=False,
        deep_work=False,
        skill_building=True,
        zero_porn=True,
        boundaries=False
    )
    
    score = calculate_compliance_score(tier1)
    expected = (3/6) * 100  # 50.0%
    assert abs(score - expected) < 0.01
    print(f"✅ Test 3.4: 3/6 items = {score:.2f}% (expected 50.0%) - PASS")


def test_compliance_score_no_items():
    """Test compliance score with 0 items completed."""
    tier1 = Tier1NonNegotiables(
        sleep=False,
        training=False,
        deep_work=False,
        skill_building=False,
        zero_porn=False,
        boundaries=False
    )
    
    score = calculate_compliance_score(tier1)
    assert score == 0.0
    print("✅ Test 3.5: 0/6 items = 0% - PASS")


# ===== Test 4: Tier 1 Breakdown with skill_building =====

def test_tier1_breakdown_includes_skill_building():
    """Test that get_tier1_breakdown includes skill_building."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        sleep_hours=7.5,
        training=True,
        deep_work=True,
        deep_work_hours=2.5,
        skill_building=True,
        skill_building_hours=2.0,
        skill_building_activity="LeetCode",
        zero_porn=True,
        boundaries=True
    )
    
    breakdown = get_tier1_breakdown(tier1)
    
    # Verify skill_building is in breakdown
    assert "skill_building" in breakdown
    assert breakdown["skill_building"]["completed"] == True
    assert breakdown["skill_building"]["hours"] == 2.0
    assert breakdown["skill_building"]["activity"] == "LeetCode"
    
    print("✅ Test 4.1: Tier 1 breakdown includes skill_building - PASS")


def test_missed_items_includes_skill_building():
    """Test that get_missed_items includes skill_building when not completed."""
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        skill_building=False,  # Missing this one
        zero_porn=True,
        boundaries=True
    )
    
    missed = get_missed_items(tier1)
    
    assert "skill_building" in missed
    assert len(missed) == 1
    print("✅ Test 4.2: get_missed_items includes skill_building - PASS")


# ===== Test 5: User Model Has career_mode =====

def test_user_has_career_mode_field():
    """Test that User model has career_mode field."""
    user = User(
        user_id="12345",
        telegram_id=12345,
        name="Test User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(),
        career_mode="skill_building"
    )
    
    assert hasattr(user, 'career_mode')
    assert user.career_mode == "skill_building"
    print("✅ Test 5.1: User has career_mode field - PASS")


def test_user_career_mode_default():
    """Test that career_mode defaults to skill_building."""
    user = User(
        user_id="12345",
        telegram_id=12345,
        name="Test User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks()
        # career_mode not provided
    )
    
    # Should default to "skill_building"
    assert user.career_mode == "skill_building"
    print("✅ Test 5.2: career_mode defaults to skill_building - PASS")


def test_user_to_firestore_includes_career_mode():
    """Test that User.to_firestore() includes career_mode."""
    user = User(
        user_id="12345",
        telegram_id=12345,
        name="Test User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(),
        career_mode="job_searching"
    )
    
    firestore_data = user.to_firestore()
    
    assert "career_mode" in firestore_data
    assert firestore_data["career_mode"] == "job_searching"
    print("✅ Test 5.3: to_firestore includes career_mode - PASS")


# ===== Test 6: Regression Tests (Ensure old code still works) =====

def test_tier1_backward_compatibility():
    """Test that old code (5 items) still works with new model."""
    # Simulate old code that doesn't know about skill_building
    tier1_data = {
        "sleep": True,
        "training": True,
        "deep_work": True,
        "zero_porn": True,
        "boundaries": True
        # skill_building not provided (old data)
    }
    
    # Should work with default value
    tier1 = Tier1NonNegotiables(**tier1_data)
    
    assert tier1.sleep == True
    assert tier1.training == True
    assert tier1.deep_work == True
    assert tier1.skill_building == False  # Default
    assert tier1.zero_porn == True
    assert tier1.boundaries == True
    
    # Compliance should calculate correctly
    score = calculate_compliance_score(tier1)
    expected = (5/6) * 100  # 5 items completed out of 6
    assert abs(score - expected) < 0.01
    
    print(f"✅ Test 6.1: Backward compatibility - PASS (old 5-item data = {score:.2f}%)")


# ===== Run All Tests =====

if __name__ == "__main__":
    print("\n" + "="*60)
    print("Phase 3D Day 1 - Career Mode System - Unit Tests")
    print("="*60 + "\n")
    
    # Test 1: Adaptive Questions
    print("📚 Test Suite 1: Adaptive Skill Building Questions")
    test_get_skill_building_question_skill_mode()
    test_get_skill_building_question_job_mode()
    test_get_skill_building_question_employed_mode()
    test_get_skill_building_question_unknown_mode()
    
    # Test 2: Tier 1 Structure
    print("\n📊 Test Suite 2: Tier 1 with 6 Items")
    test_tier1_has_6_items()
    test_tier1_skill_building_default_false()
    test_tier1_skill_building_optional_fields()
    
    # Test 3: Compliance Calculation
    print("\n🎯 Test Suite 3: Compliance Calculation (6 items)")
    test_compliance_score_all_6_items_complete()
    test_compliance_score_5_of_6_items()
    test_compliance_score_4_of_6_items()
    test_compliance_score_3_of_6_items()
    test_compliance_score_no_items()
    
    # Test 4: Helper Functions
    print("\n🔧 Test Suite 4: Helper Functions")
    test_tier1_breakdown_includes_skill_building()
    test_missed_items_includes_skill_building()
    
    # Test 5: User Model
    print("\n👤 Test Suite 5: User Model career_mode")
    test_user_has_career_mode_field()
    test_user_career_mode_default()
    test_user_to_firestore_includes_career_mode()
    
    # Test 6: Regression
    print("\n🔄 Test Suite 6: Backward Compatibility")
    test_tier1_backward_compatibility()
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED! Phase 3D Day 1 implementation verified.")
    print("="*60 + "\n")
    
    print("Next steps:")
    print("1. Run bot locally: python src/main.py")
    print("2. Test /career command in Telegram")
    print("3. Verify Tier 1 shows 6 items during check-in")
    print("4. Confirm compliance calculation matches test results")
