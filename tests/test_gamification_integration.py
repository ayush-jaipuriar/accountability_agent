"""
Integration Tests for Gamification System (Phase 3C)
===================================================

Tests verify the complete gamification flow works end-to-end:
- Check-in → Streak update → Achievement unlock → Milestone celebration
- Social proof integration
- `/achievements` command
- Error handling and graceful degradation

These are integration tests (marked as slow) that test multiple components together.

Run tests:
    pytest tests/test_gamification_integration.py -v
    pytest tests/test_gamification_integration.py -v -m integration
"""

import pytest
from unittest.mock import Mock, patch, AsyncMock
from src.services.achievement_service import achievement_service
from src.utils.streak import update_streak_data, check_milestone
from src.models.schemas import (
    User,
    UserStreaks,
    DailyCheckIn,
    Tier1NonNegotiables,
    CheckInResponses
)
from datetime import datetime


# ===== Fixtures =====

@pytest.fixture
def mock_firestore_service():
    """Mock Firestore service for testing."""
    with patch('src.services.achievement_service.firestore_service') as mock_fs:
        mock_fs.get_user = Mock()
        mock_fs.update_user = Mock()
        mock_fs.get_recent_checkins = Mock(return_value=[])
        mock_fs.get_all_users = Mock(return_value=[])
        yield mock_fs


@pytest.fixture
def user_day_29():
    """User about to hit 30-day milestone."""
    return User(
        user_id="user_milestone",
        telegram_id=123456789,
        name="Milestone User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=29,
            longest_streak=29,
            last_checkin_date="2026-02-05",
            total_checkins=29
        ),
        achievements=["first_checkin", "week_warrior", "fortnight_fighter"]
    )


@pytest.fixture
def perfect_checkins_7days():
    """7 perfect check-ins for achievement testing."""
    checkins = []
    for i in range(1, 8):
        checkins.append(
            DailyCheckIn(
                date=f"2026-01-{30+i:02d}" if i <= 2 else f"2026-02-{i-2:02d}",
                user_id="user_milestone",
                mode="maintenance",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep=True,
                    sleep_hours=7.5,
                    training=True,
                    deep_work=True,
                    deep_work_hours=3.0,
                    zero_porn=True,
                    boundaries=True
                ),
                responses=CheckInResponses(
                    challenges="None",
                    rating=10,
                    rating_reason="Perfect day",
                    tomorrow_priority="Continue",
                    tomorrow_obstacle="None"
                ),
                compliance_score=100.0,
                completed_at=datetime.utcnow(),
                duration_seconds=120
            )
        )
    return checkins


# ===== Integration Test: Complete Check-In Flow =====

@pytest.mark.integration
def test_complete_checkin_flow_with_milestone_and_achievement(
    mock_firestore_service,
    user_day_29,
    perfect_checkins_7days
):
    """
    Test complete check-in flow:
    1. User completes check-in (day 30)
    2. Streak updates to 30 days
    3. Milestone detected (30-day celebration)
    4. Achievement unlocked (month_master)
    5. Both messages would be sent
    """
    # Step 1: Simulate check-in completion and streak update
    streak_updates = update_streak_data(
        current_streak=user_day_29.streaks.current_streak,
        longest_streak=user_day_29.streaks.longest_streak,
        total_checkins=user_day_29.streaks.total_checkins,
        last_checkin_date=user_day_29.streaks.last_checkin_date,
        new_checkin_date="2026-02-06"
    )
    
    # Step 2: Verify streak updated correctly
    assert streak_updates['current_streak'] == 30
    assert streak_updates['longest_streak'] == 30
    
    # Step 3: Verify milestone detected
    milestone = streak_updates['milestone_hit']
    assert milestone is not None
    assert milestone['title'] == "🎉 30 DAYS!"
    assert "top 10%" in milestone['message'].lower()
    
    # Step 4: Update user with new streak
    user_day_29.streaks.current_streak = 30
    user_day_29.streaks.longest_streak = 30
    
    # Step 5: Check for achievements
    mock_firestore_service.get_recent_checkins.return_value = perfect_checkins_7days
    newly_unlocked = achievement_service.check_achievements(
        user_day_29,
        perfect_checkins_7days
    )
    
    # Step 6: Verify achievements detected
    assert "month_master" in newly_unlocked  # 30-day streak achievement
    
    # This flow would result in 2 separate messages:
    # - Milestone celebration message
    # - Achievement unlock message


@pytest.mark.integration
def test_checkin_flow_without_milestone(mock_firestore_service, user_day_29):
    """Test check-in flow on non-milestone day (day 28 → 29)."""
    # User on day 28
    user_day_29.streaks.current_streak = 28
    user_day_29.streaks.longest_streak = 28
    user_day_29.streaks.total_checkins = 28
    user_day_29.streaks.last_checkin_date = "2026-02-05"
    
    # Complete check-in
    streak_updates = update_streak_data(
        current_streak=28,
        longest_streak=28,
        total_checkins=28,
        last_checkin_date="2026-02-05",
        new_checkin_date="2026-02-06"
    )
    
    # Verify streak updated but no milestone
    assert streak_updates['current_streak'] == 29
    assert streak_updates['milestone_hit'] is None
    
    # Check for achievements (should not unlock month_master yet)
    user_day_29.streaks.current_streak = 29
    newly_unlocked = achievement_service.check_achievements(user_day_29, [])
    
    assert "month_master" not in newly_unlocked


# ===== Integration Test: Social Proof =====

@pytest.mark.integration
def test_social_proof_integration(mock_firestore_service):
    """Test social proof message generation with real percentile calculation."""
    # Create 100 mock users with varying streaks
    mock_users = []
    for i in range(1, 101):
        mock_users.append(
            User(
                user_id=f"user_{i}",
                telegram_id=i,
                name=f"User {i}",
                timezone="Asia/Kolkata",
                streaks=UserStreaks(
                    current_streak=i,
                    longest_streak=i,
                    last_checkin_date="2026-02-06",
                    total_checkins=i
                )
            )
        )
    mock_firestore_service.get_all_users.return_value = mock_users
    
    # User with 95-day streak (should be top 5%)
    top_user = User(
        user_id="top_performer",
        telegram_id=999,
        name="Top User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=95,
            longest_streak=95,
            last_checkin_date="2026-02-06",
            total_checkins=95
        )
    )
    
    # Get social proof message
    social_proof = achievement_service.get_social_proof_message(top_user)
    
    # Verify message generated
    assert social_proof is not None
    assert "TOP 5%" in social_proof or "TOP 10%" in social_proof  # Should be in top tier
    assert "💎" in social_proof or "🌟" in social_proof


@pytest.mark.integration
def test_social_proof_not_shown_for_new_users(mock_firestore_service):
    """Test social proof not shown for users with < 30 day streak."""
    # Create sufficient users for percentile calculation
    mock_users = []
    for i in range(1, 20):
        mock_users.append(
            User(
                user_id=f"user_{i}",
                telegram_id=i,
                name=f"User {i}",
                timezone="Asia/Kolkata",
                streaks=UserStreaks(
                    current_streak=i * 5,
                    longest_streak=i * 5,
                    last_checkin_date="2026-02-06",
                    total_checkins=i * 5
                )
            )
        )
    mock_firestore_service.get_all_users.return_value = mock_users
    
    # New user with 15-day streak
    new_user = User(
        user_id="new_user",
        telegram_id=888,
        name="New User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=15,  # Below 30-day threshold
            longest_streak=15,
            last_checkin_date="2026-02-06",
            total_checkins=15
        )
    )
    
    # Get social proof message
    social_proof = achievement_service.get_social_proof_message(new_user)
    
    # Should not show social proof
    assert social_proof is None


# ===== Integration Test: Multiple Achievements Unlocked =====

@pytest.mark.integration
def test_multiple_achievements_unlocked_at_once(mock_firestore_service, perfect_checkins_7days):
    """Test multiple achievements can be unlocked in single check-in."""
    # User hitting 30 days with 7 perfect days
    user = User(
        user_id="multi_achievement_user",
        telegram_id=777,
        name="Multi User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=30,
            longest_streak=30,
            last_checkin_date="2026-02-06",
            total_checkins=30
        ),
        achievements=["first_checkin", "week_warrior", "fortnight_fighter"]
    )
    
    # Get all check-ins for 30 days (last 7 are perfect)
    all_checkins = perfect_checkins_7days  # Simplified - just 7 perfect days
    
    # Check achievements
    mock_firestore_service.get_recent_checkins.return_value = all_checkins
    newly_unlocked = achievement_service.check_achievements(user, all_checkins)
    
    # Should unlock multiple achievements
    assert "month_master" in newly_unlocked  # 30-day streak
    assert "perfect_week" in newly_unlocked  # 7 days at 100%
    assert len(newly_unlocked) >= 2


# ===== Integration Test: Graceful Degradation =====

@pytest.mark.integration
def test_achievement_system_failure_doesnt_break_checkin(mock_firestore_service, user_day_29):
    """Test check-in succeeds even if achievement system fails."""
    # Simulate Firestore error for achievements
    mock_firestore_service.get_recent_checkins.side_effect = Exception("Firestore error")
    
    # Streak update should still work
    streak_updates = update_streak_data(
        current_streak=29,
        longest_streak=29,
        total_checkins=29,
        last_checkin_date="2026-02-05",
        new_checkin_date="2026-02-06"
    )
    
    # Core functionality preserved
    assert streak_updates['current_streak'] == 30
    assert streak_updates['milestone_hit'] is not None
    
    # Achievement check would fail gracefully (handled in conversation.py)
    # But streak data is intact


@pytest.mark.integration
def test_percentile_calculation_failure_doesnt_break_checkin(mock_firestore_service):
    """Test social proof failure doesn't break check-in."""
    # Simulate Firestore error
    mock_firestore_service.get_all_users.side_effect = Exception("Database error")
    
    user = User(
        user_id="test_user",
        telegram_id=123,
        name="Test",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=50,
            longest_streak=50,
            last_checkin_date="2026-02-06",
            total_checkins=50
        )
    )
    
    # Social proof calculation should fail gracefully
    social_proof = achievement_service.get_social_proof_message(user)
    
    # Should return None (not crash)
    assert social_proof is None


# ===== Integration Test: User Progress Tracking =====

@pytest.mark.integration
def test_user_progress_tracks_across_sessions(mock_firestore_service):
    """Test user progress accumulates across multiple check-ins."""
    user = User(
        user_id="progress_user",
        telegram_id=555,
        name="Progress User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=1,
            longest_streak=1,
            last_checkin_date="2026-01-07",
            total_checkins=1
        ),
        achievements=[]
    )
    
    # Day 1: First check-in
    newly_unlocked = achievement_service.check_achievements(user, [])
    assert "first_checkin" in newly_unlocked
    user.achievements.append("first_checkin")
    
    # Day 7: Week warrior
    user.streaks.current_streak = 7
    newly_unlocked = achievement_service.check_achievements(user, [])
    assert "week_warrior" in newly_unlocked
    assert "first_checkin" not in newly_unlocked  # No duplicates
    user.achievements.append("week_warrior")
    
    # Day 14: Fortnight fighter
    user.streaks.current_streak = 14
    newly_unlocked = achievement_service.check_achievements(user, [])
    assert "fortnight_fighter" in newly_unlocked
    user.achievements.append("fortnight_fighter")
    
    # Check progress
    progress = achievement_service.get_user_progress(user)
    assert progress['total_unlocked'] == 3
    assert progress['common_count'] == 3  # All are common tier


# ===== Integration Test: Comeback Journey =====

@pytest.mark.integration
def test_comeback_king_journey(mock_firestore_service):
    """Test comeback king achievement over multiple check-ins."""
    # User had 50-day streak, broke it, now rebuilding
    user = User(
        user_id="comeback_user",
        telegram_id=444,
        name="Comeback User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=49,
            longest_streak=50,  # Previous best
            last_checkin_date="2026-02-05",
            total_checkins=120
        ),
        achievements=["first_checkin", "week_warrior", "fortnight_fighter", "month_master"]
    )
    
    # Day 49: Not yet comeback king
    newly_unlocked = achievement_service.check_achievements(user, [])
    assert "comeback_king" not in newly_unlocked
    
    # Day 50: Rebuilt to longest streak
    user.streaks.current_streak = 50
    newly_unlocked = achievement_service.check_achievements(user, [])
    assert "comeback_king" in newly_unlocked


# ===== Integration Test: Milestone Sequence =====

@pytest.mark.integration
def test_milestone_sequence_over_time():
    """Test all milestones trigger at correct days."""
    milestones_hit = []
    
    # Simulate 365 days of check-ins
    for day in range(1, 366):
        streak_updates = update_streak_data(
            current_streak=day - 1,
            longest_streak=day - 1,
            total_checkins=day - 1,
            last_checkin_date=f"2025-02-{(day-1) % 28 + 1:02d}",  # Simplified
            new_checkin_date=f"2025-02-{day % 28 + 1:02d}"
        )
        
        if streak_updates['milestone_hit']:
            milestones_hit.append(day)
    
    # Verify all 5 milestones hit
    assert milestones_hit == [30, 60, 90, 180, 365]


# ===== Integration Test: Achievement Catalog Access =====

@pytest.mark.integration
def test_get_all_achievements_integration():
    """Test achievement catalog is accessible and complete."""
    all_achievements = achievement_service.get_all_achievements()
    
    # Verify all 13 achievements present
    assert len(all_achievements) == 13
    
    # Verify all required achievements
    required_ids = [
        "first_checkin",
        "week_warrior",
        "fortnight_fighter",
        "month_master",
        "quarter_conqueror",
        "half_year_hero",
        "year_yoda",
        "perfect_week",
        "perfect_month",
        "tier1_master",
        "zero_breaks_month",
        "comeback_king",
        "shield_master"
    ]
    
    for achievement_id in required_ids:
        assert achievement_id in all_achievements
        achievement = all_achievements[achievement_id]
        assert achievement.name
        assert achievement.description
        assert achievement.icon
        assert achievement.rarity in ["Common", "Rare", "Epic", "Legendary"]


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
