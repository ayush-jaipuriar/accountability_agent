"""
Unit Tests for Streak Tracking Logic
====================================

Tests verify streak increment/reset rules work correctly.

Streak Rules:
- Increment: Check-in within 48 hours (1 day gap)
- Reset: Gap exceeds 48 hours (2+ days)
- First check-in: Streak = 1

Run tests:
    pytest tests/test_streak.py -v
"""

import pytest
from src.utils.streak import (
    should_increment_streak,
    calculate_new_streak,
    update_streak_data,
    get_streak_emoji,
    days_until_milestone,
    check_milestone,
    MILESTONE_MESSAGES
)


# ===== Test: Streak Increment Logic =====

def test_should_increment_consecutive_days():
    """Test streak increments for consecutive days (1 day gap)."""
    # Yesterday → today
    assert should_increment_streak("2026-01-29", "2026-01-30") == True


def test_should_not_increment_same_day():
    """Test streak doesn't increment for same day (shouldn't happen)."""
    assert should_increment_streak("2026-01-30", "2026-01-30") == False


def test_should_not_increment_large_gap():
    """Test streak resets for 2+ day gap."""
    # 5 day gap
    assert should_increment_streak("2026-01-25", "2026-01-30") == False
    
    # 2 day gap (exactly 48 hours)
    assert should_increment_streak("2026-01-28", "2026-01-30") == False


# ===== Test: New Streak Calculation =====

def test_calculate_new_streak_first_checkin():
    """Test first ever check-in sets streak to 1."""
    new_streak = calculate_new_streak(
        current_streak=0,
        last_checkin_date=None,
        new_checkin_date="2026-01-30"
    )
    
    assert new_streak == 1


def test_calculate_new_streak_increment():
    """Test streak increments for consecutive check-in."""
    new_streak = calculate_new_streak(
        current_streak=47,
        last_checkin_date="2026-01-29",
        new_checkin_date="2026-01-30"
    )
    
    assert new_streak == 48


def test_calculate_new_streak_reset():
    """Test streak resets after gap."""
    new_streak = calculate_new_streak(
        current_streak=47,
        last_checkin_date="2026-01-25",  # 5 day gap
        new_checkin_date="2026-01-30"
    )
    
    assert new_streak == 1


# ===== Test: Full Streak Update =====

def test_update_streak_data_increment():
    """Test full streak update when incrementing."""
    updates = update_streak_data(
        current_streak=47,
        longest_streak=47,
        total_checkins=100,
        last_checkin_date="2026-01-29",
        new_checkin_date="2026-01-30"
    )
    
    assert updates['current_streak'] == 48
    assert updates['longest_streak'] == 48  # Updated because current exceeded
    assert updates['last_checkin_date'] == "2026-01-30"
    assert updates['total_checkins'] == 101


def test_update_streak_data_reset():
    """Test full streak update when resetting."""
    updates = update_streak_data(
        current_streak=47,
        longest_streak=60,  # Historical best
        total_checkins=150,
        last_checkin_date="2026-01-20",  # 10 day gap
        new_checkin_date="2026-01-30"
    )
    
    assert updates['current_streak'] == 1  # Reset
    assert updates['longest_streak'] == 60  # Unchanged (historical best)
    assert updates['last_checkin_date'] == "2026-01-30"
    assert updates['total_checkins'] == 151


def test_update_streak_data_first_checkin():
    """Test first ever check-in."""
    updates = update_streak_data(
        current_streak=0,
        longest_streak=0,
        total_checkins=0,
        last_checkin_date=None,
        new_checkin_date="2026-01-30"
    )
    
    assert updates['current_streak'] == 1
    assert updates['longest_streak'] == 1
    assert updates['last_checkin_date'] == "2026-01-30"
    assert updates['total_checkins'] == 1


def test_update_streak_data_ties_record():
    """Test when current streak ties longest streak."""
    updates = update_streak_data(
        current_streak=59,
        longest_streak=60,
        total_checkins=200,
        last_checkin_date="2026-01-29",
        new_checkin_date="2026-01-30"
    )
    
    assert updates['current_streak'] == 60
    assert updates['longest_streak'] == 60  # Tied, not exceeded


def test_update_streak_data_breaks_record():
    """Test when current streak exceeds longest streak."""
    updates = update_streak_data(
        current_streak=60,
        longest_streak=60,
        total_checkins=200,
        last_checkin_date="2026-01-29",
        new_checkin_date="2026-01-30"
    )
    
    assert updates['current_streak'] == 61
    assert updates['longest_streak'] == 61  # New record!


# ===== Test: Streak Emoji Selection =====

def test_get_streak_emoji_building():
    """Test 🔥 emoji for 1-6 days."""
    assert get_streak_emoji(1) == "🔥"
    assert get_streak_emoji(6) == "🔥"


def test_get_streak_emoji_strong():
    """Test 💪 emoji for 7-29 days."""
    assert get_streak_emoji(7) == "💪"
    assert get_streak_emoji(29) == "💪"


def test_get_streak_emoji_amazing():
    """Test 🚀 emoji for 30-89 days."""
    assert get_streak_emoji(30) == "🚀"
    assert get_streak_emoji(89) == "🚀"


def test_get_streak_emoji_champion():
    """Test 🏆 emoji for 90-179 days."""
    assert get_streak_emoji(90) == "🏆"
    assert get_streak_emoji(179) == "🏆"


def test_get_streak_emoji_legendary():
    """Test 👑 emoji for 180+ days."""
    assert get_streak_emoji(180) == "👑"
    assert get_streak_emoji(365) == "👑"


# ===== Test: Milestone Calculation =====

def test_days_until_milestone_approaching_7():
    """Test days until 7-day milestone."""
    days_left, milestone = days_until_milestone(5)
    assert days_left == 2
    assert milestone == "7 days"


def test_days_until_milestone_approaching_30():
    """Test days until 30-day milestone."""
    days_left, milestone = days_until_milestone(25)
    assert days_left == 5
    assert milestone == "30 days"


def test_days_until_milestone_approaching_90():
    """Test days until 90-day milestone."""
    days_left, milestone = days_until_milestone(85)
    assert days_left == 5
    assert milestone == "90 days"


def test_days_until_milestone_past_all():
    """Test when past all milestones."""
    days_left, milestone = days_until_milestone(400)
    assert days_left == 0
    assert milestone == "legendary status"


# ===== Test: Edge Cases =====

def test_streak_exactly_one_day():
    """Test exactly 24 hours (1 day) increments."""
    assert should_increment_streak("2026-01-29", "2026-01-30") == True


def test_streak_exactly_two_days():
    """Test exactly 48 hours (2 days) resets."""
    assert should_increment_streak("2026-01-28", "2026-01-30") == False


def test_streak_month_boundary():
    """Test streak across month boundary."""
    # Jan 31 → Feb 1
    assert should_increment_streak("2026-01-31", "2026-02-01") == True


def test_streak_year_boundary():
    """Test streak across year boundary."""
    # Dec 31, 2025 → Jan 1, 2026
    assert should_increment_streak("2025-12-31", "2026-01-01") == True


# ===== Test: Milestone Detection (Phase 3C Day 4) =====

def test_check_milestone_30_days():
    """Test 30-day milestone is detected."""
    milestone = check_milestone(30)
    
    assert milestone is not None
    assert milestone['title'] == "🎉 30 DAYS!"
    assert "top 10%" in milestone['message'].lower()
    assert milestone['percentile'] == "Top 10%"


def test_check_milestone_60_days():
    """Test 60-day milestone is detected."""
    milestone = check_milestone(60)
    
    assert milestone is not None
    assert milestone['title'] == "🔥 60 DAYS!"
    assert "top 5%" in milestone['message'].lower()


def test_check_milestone_90_days():
    """Test 90-day milestone is detected.
    
    The 90-day message says '98% of people never reach' rather than
    'top 2%' - both convey the same percentile, different phrasing.
    """
    milestone = check_milestone(90)
    
    assert milestone is not None
    assert milestone['title'] == "💎 90 DAYS!"
    assert "98%" in milestone['message'] or "top 2%" in milestone['message'].lower()


def test_check_milestone_180_days():
    """Test 180-day milestone is detected."""
    milestone = check_milestone(180)
    
    assert milestone is not None
    assert milestone['title'] == "🏆 HALF YEAR!"
    assert "top 1%" in milestone['message'].lower()


def test_check_milestone_365_days():
    """Test 365-day milestone is detected.
    
    The 365-day message says 'less than 0.1% of people ever will' rather
    than 'top 0.1%' - both convey the same rarity, different phrasing.
    """
    milestone = check_milestone(365)
    
    assert milestone is not None
    assert milestone['title'] == "👑 ONE YEAR!"
    assert "0.1%" in milestone['message']


def test_check_milestone_non_milestone():
    """Test non-milestone streaks return None."""
    # Test various non-milestone values
    assert check_milestone(1) is None
    assert check_milestone(7) is None
    assert check_milestone(29) is None
    assert check_milestone(31) is None
    assert check_milestone(50) is None
    assert check_milestone(100) is None
    assert check_milestone(200) is None


def test_update_streak_data_returns_milestone():
    """Test update_streak_data includes milestone when hit."""
    updates = update_streak_data(
        current_streak=29,
        longest_streak=29,
        total_checkins=29,
        last_checkin_date="2026-02-05",
        new_checkin_date="2026-02-06"
    )
    
    # Should hit 30-day milestone
    assert updates['current_streak'] == 30
    assert updates['milestone_hit'] is not None
    assert updates['milestone_hit']['title'] == "🎉 30 DAYS!"


def test_update_streak_data_no_milestone():
    """Test update_streak_data returns None for non-milestones."""
    updates = update_streak_data(
        current_streak=28,
        longest_streak=28,
        total_checkins=28,
        last_checkin_date="2026-02-05",
        new_checkin_date="2026-02-06"
    )
    
    # Should be day 29 (not a milestone)
    assert updates['current_streak'] == 29
    assert updates['milestone_hit'] is None


def test_milestone_not_triggered_on_reset():
    """Test milestone not triggered when streak resets."""
    updates = update_streak_data(
        current_streak=50,
        longest_streak=50,
        total_checkins=100,
        last_checkin_date="2026-01-20",  # Large gap
        new_checkin_date="2026-02-06"
    )
    
    # Streak resets to 1, no milestone
    assert updates['current_streak'] == 1
    assert updates['milestone_hit'] is None


def test_all_milestone_messages_exist():
    """Test all 5 milestone messages are defined."""
    assert len(MILESTONE_MESSAGES) == 5
    assert 30 in MILESTONE_MESSAGES
    assert 60 in MILESTONE_MESSAGES
    assert 90 in MILESTONE_MESSAGES
    assert 180 in MILESTONE_MESSAGES
    assert 365 in MILESTONE_MESSAGES


def test_milestone_messages_have_required_fields():
    """Test all milestone messages have required fields."""
    for days, milestone_data in MILESTONE_MESSAGES.items():
        assert 'title' in milestone_data
        assert 'message' in milestone_data
        assert 'percentile' in milestone_data
        
        # Check fields are non-empty
        assert len(milestone_data['title']) > 0
        assert len(milestone_data['message']) > 0
        assert len(milestone_data['percentile']) > 0


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
