"""
Unit Tests for Achievement System (Phase 3C)
===========================================

Tests verify the achievement system works correctly:
- Achievement detection logic
- Percentile calculation
- Social proof messaging
- User progress tracking

Run tests:
    pytest tests/test_achievements.py -v
"""

import pytest
from unittest.mock import Mock, patch
from src.services.achievement_service import AchievementService, ACHIEVEMENTS
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
def achievement_service():
    """Provide AchievementService instance."""
    return AchievementService()


@pytest.fixture
def user_new():
    """New user with no achievements."""
    return User(
        user_id="test_user_1",
        telegram_id=123456789,
        name="Test User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=1,
            longest_streak=1,
            last_checkin_date="2026-02-06",
            total_checkins=1
        ),
        achievements=[]
    )


@pytest.fixture
def user_7day_streak():
    """User with 7-day streak."""
    return User(
        user_id="test_user_2",
        telegram_id=987654321,
        name="Test User 2",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=7,
            longest_streak=7,
            last_checkin_date="2026-02-06",
            total_checkins=7
        ),
        achievements=["first_checkin"]
    )


@pytest.fixture
def user_30day_streak():
    """User with 30-day streak."""
    return User(
        user_id="test_user_3",
        telegram_id=111222333,
        name="Test User 3",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=30,
            longest_streak=30,
            last_checkin_date="2026-02-06",
            total_checkins=30
        ),
        achievements=["first_checkin", "week_warrior", "fortnight_fighter"]
    )


@pytest.fixture
def user_comeback():
    """User who rebuilt their streak to match longest after a reset (Phase D)."""
    return User(
        user_id="test_user_4",
        telegram_id=444555666,
        name="Test User 4",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=50,
            longest_streak=50,  # Rebuilt to match
            last_checkin_date="2026-02-06",
            total_checkins=120,
            streak_before_reset=40,  # Phase D: had 40-day streak before reset
            last_reset_date="2025-12-01"  # Phase D: when the reset happened
        ),
        achievements=["first_checkin", "week_warrior", "fortnight_fighter", "month_master"]
    )


@pytest.fixture
def perfect_checkin():
    """Check-in with 100% compliance (Phase 3D: 6 items)."""
    return DailyCheckIn(
        date="2026-02-06",
        user_id="test_user",
        mode="maintenance",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=True,
            sleep_hours=7.5,
            training=True,
            deep_work=True,
            deep_work_hours=2.5,
            skill_building=True,  # Phase 3D: 6th item
            zero_porn=True,
            boundaries=True
        ),
        responses=CheckInResponses(
            challenges="No challenges today, everything went smoothly",
            rating=10,
            rating_reason="Perfect day with all goals achieved on time",
            tomorrow_priority="Continue daily constitution practice as planned",
            tomorrow_obstacle="No significant obstacles expected tomorrow"
        ),
        compliance_score=100.0,
        completed_at=datetime.utcnow(),
        duration_seconds=120
    )


@pytest.fixture
def recent_perfect_checkins(perfect_checkin):
    """7 consecutive perfect check-ins."""
    return [
        DailyCheckIn(
            **{**perfect_checkin.__dict__, "date": f"2026-02-{i:02d}"}
        )
        for i in range(1, 8)
    ]


@pytest.fixture
def recent_checkins_30days(perfect_checkin):
    """30 consecutive perfect check-ins."""
    return [
        DailyCheckIn(
            **{**perfect_checkin.__dict__, "date": f"2026-01-{7+i:02d}" if i < 24 else f"2026-02-{i-23:02d}"}
        )
        for i in range(30)
    ]


# ===== Test: Achievement Detection - Streak-Based =====

def test_first_checkin_achievement(achievement_service, user_new):
    """Test 'first_checkin' achievement unlocks on first check-in."""
    recent_checkins = []
    newly_unlocked = achievement_service.check_achievements(user_new, recent_checkins)
    
    assert "first_checkin" in newly_unlocked
    assert len(newly_unlocked) == 1


def test_week_warrior_achievement(achievement_service, user_7day_streak):
    """Test 'week_warrior' achievement unlocks at 7-day streak."""
    recent_checkins = []
    newly_unlocked = achievement_service.check_achievements(user_7day_streak, recent_checkins)
    
    assert "week_warrior" in newly_unlocked


def test_month_master_achievement(achievement_service, user_30day_streak):
    """Test 'month_master' achievement unlocks at 30-day streak."""
    recent_checkins = []
    newly_unlocked = achievement_service.check_achievements(user_30day_streak, recent_checkins)
    
    assert "month_master" in newly_unlocked


def test_no_duplicate_achievements(achievement_service, user_7day_streak):
    """Test already-unlocked achievements are not returned."""
    # User already has 'first_checkin'
    user_7day_streak.achievements = ["first_checkin", "week_warrior"]
    
    recent_checkins = []
    newly_unlocked = achievement_service.check_achievements(user_7day_streak, recent_checkins)
    
    # Should not return 'first_checkin' or 'week_warrior' again
    assert "first_checkin" not in newly_unlocked
    assert "week_warrior" not in newly_unlocked


# ===== Test: Achievement Detection - Performance-Based =====

def test_perfect_week_achievement(achievement_service, user_7day_streak, recent_perfect_checkins):
    """Test 'perfect_week' achievement unlocks after 7 days at 100%."""
    newly_unlocked = achievement_service.check_achievements(
        user_7day_streak,
        recent_perfect_checkins
    )
    
    assert "perfect_week" in newly_unlocked


def test_tier1_master_achievement(achievement_service, user_30day_streak, recent_checkins_30days):
    """Test 'tier1_master' achievement unlocks after 30 days with all Tier 1 complete."""
    newly_unlocked = achievement_service.check_achievements(
        user_30day_streak,
        recent_checkins_30days
    )
    
    assert "tier1_master" in newly_unlocked


def test_perfect_week_not_unlocked_with_partial_compliance(achievement_service, user_7day_streak):
    """Test 'perfect_week' doesn't unlock if compliance < 100%."""
    # Create check-ins with 80% compliance
    partial_checkins = []
    for i in range(7):
        checkin = DailyCheckIn(
            date=f"2026-02-{i+1:02d}",
            user_id="test_user",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=False,  # Missed this
                sleep_hours=5.5,
                training=True,
                deep_work=True,
                deep_work_hours=2.0,
                zero_porn=True,
                boundaries=True
            ),
            responses=CheckInResponses(
                challenges="Struggled with sleep",
                rating=8,
                rating_reason="Good but not perfect",
                tomorrow_priority="Sleep early",
                tomorrow_obstacle="Late meeting"
            ),
            compliance_score=80.0,  # Not 100%
            completed_at=datetime.utcnow(),
            duration_seconds=120
        )
        partial_checkins.append(checkin)
    
    newly_unlocked = achievement_service.check_achievements(
        user_7day_streak,
        partial_checkins
    )
    
    assert "perfect_week" not in newly_unlocked


# ===== Test: Achievement Detection - Special =====

def test_comeback_king_achievement(achievement_service, user_comeback):
    """Test 'comeback_king' achievement unlocks when rebuilding to longest streak."""
    # User has rebuilt from a broken streak back to their longest (50 days)
    recent_checkins = []
    newly_unlocked = achievement_service.check_achievements(user_comeback, recent_checkins)
    
    assert "comeback_king" in newly_unlocked


# ===== Test: Achievement Catalog =====

def test_get_achievement_valid(achievement_service):
    """Test retrieving a valid achievement."""
    achievement = achievement_service.get_achievement("week_warrior")
    
    assert achievement is not None
    assert achievement.achievement_id == "week_warrior"  # Field is achievement_id, not id
    assert achievement.name == "Week Warrior"
    assert achievement.icon == "🏅"


def test_get_achievement_invalid(achievement_service):
    """Test retrieving non-existent achievement returns None."""
    achievement = achievement_service.get_achievement("fake_achievement")
    
    assert achievement is None


def test_get_all_achievements(achievement_service):
    """Test getting all achievements."""
    all_achievements = achievement_service.get_all_achievements()
    
    assert len(all_achievements) == 15  # Phase 3C (13) + Phase D (2: comeback_kid, comeback_legend)
    assert "first_checkin" in all_achievements
    assert "year_yoda" in all_achievements


# ===== Test: User Progress =====

def test_get_user_progress_new_user(achievement_service, user_new):
    """Test user progress for new user.
    
    The get_user_progress API returns:
    - 'percentage' (not 'unlock_percentage')
    - 'rarity_breakdown' dict (not flat 'common_count'/'rare_count')
    """
    progress = achievement_service.get_user_progress(user_new)
    
    assert progress['total_unlocked'] == 0
    assert progress['total_available'] == 15  # Phase D: 13 + 2 new comeback achievements
    assert progress['percentage'] == 0.0
    assert progress['rarity_breakdown']['common'] == 0
    assert progress['rarity_breakdown']['rare'] == 0


def test_get_user_progress_active_user(achievement_service, user_30day_streak):
    """Test user progress for active user with achievements.
    
    The API returns 'percentage' (not 'unlock_percentage') and
    'next_milestone' (not 'next_streak_achievement').
    """
    user_30day_streak.achievements = ["first_checkin", "week_warrior", "fortnight_fighter", "month_master"]
    
    progress = achievement_service.get_user_progress(user_30day_streak)
    
    assert progress['total_unlocked'] == 4
    assert progress['total_available'] == 15  # Phase D: 13 + 2 new comeback achievements
    assert progress['percentage'] == pytest.approx(26.7, rel=0.1)  # 4/15 = 26.7%
    assert progress['next_milestone'] == "quarter_conqueror"


# ===== Test: Celebration Messages =====

def test_celebration_message_format(achievement_service, user_7day_streak):
    """Test celebration message includes required elements.
    
    The celebration message includes a rarity-specific message line:
    - common: "A great start! 💪"
    - rare: "You're in the top 20%! 🌟"
    - epic: "Elite territory! Top 5%! 💎"
    - legendary: "LEGENDARY! You're in the 1%! 👑"
    """
    message = achievement_service.get_celebration_message("week_warrior", user_7day_streak)
    
    # Should include achievement name, description, rarity-specific message
    assert "Week Warrior" in message
    assert "7-day streak" in message
    assert "great start" in message or "💪" in message  # Common rarity message


def test_celebration_message_legendary(achievement_service, user_30day_streak):
    """Test celebration message for legendary achievement."""
    # Create user with 365-day streak
    user_365 = User(
        user_id="legendary_user",
        telegram_id=999888777,
        name="Legend",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=365,
            longest_streak=365,
            last_checkin_date="2026-02-06",
            total_checkins=365
        ),
        achievements=[]
    )
    
    message = achievement_service.get_celebration_message("year_yoda", user_365)
    
    assert "Year Yoda" in message
    assert "Legendary" in message or "👑" in message


# ===== Test: Percentile Calculation =====

def test_calculate_percentile_top_performer(achievement_service):
    """Test percentile calculation for top performer."""
    # Mock firestore to return 100 users with varying streaks
    with patch('src.services.achievement_service.firestore_service.get_all_users') as mock_get_users:
        # Create 100 users with streaks 1-100
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
        mock_get_users.return_value = mock_users
        
        # User with streak 95 should be in top 5%
        percentile = achievement_service.calculate_percentile(95)
        
        assert percentile is not None
        assert percentile >= 95  # Top 5%


def test_calculate_percentile_median(achievement_service):
    """Test percentile calculation for median performer."""
    with patch('src.services.achievement_service.firestore_service.get_all_users') as mock_get_users:
        # Create 100 users with streaks 1-100
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
        mock_get_users.return_value = mock_users
        
        # User with streak 50 should be around 50th percentile
        percentile = achievement_service.calculate_percentile(50)
        
        assert percentile is not None
        assert 45 <= percentile <= 55  # Around median


def test_calculate_percentile_insufficient_users(achievement_service):
    """Test percentile returns None with < 10 users (privacy threshold)."""
    with patch('src.services.achievement_service.firestore_service.get_all_users') as mock_get_users:
        # Only 5 users (below minimum)
        mock_users = []
        for i in range(1, 6):
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
        mock_get_users.return_value = mock_users
        
        percentile = achievement_service.calculate_percentile(3)
        
        assert percentile is None  # Privacy protection


# ===== Test: Social Proof Messages =====

def test_social_proof_message_top_1_percent(achievement_service):
    """Test social proof message for top 1% user."""
    with patch.object(achievement_service, 'calculate_percentile', return_value=99):
        user = User(
            user_id="top_user",
            telegram_id=123,
            name="Top User",
            timezone="Asia/Kolkata",
            streaks=UserStreaks(
                current_streak=100,
                longest_streak=100,
                last_checkin_date="2026-02-06",
                total_checkins=100
            )
        )
        
        message = achievement_service.get_social_proof_message(user)
        
        assert message is not None
        assert "TOP 1%" in message
        assert "👑" in message


def test_social_proof_message_top_10_percent(achievement_service):
    """Test social proof message for top 10% user."""
    with patch.object(achievement_service, 'calculate_percentile', return_value=92):
        user = User(
            user_id="good_user",
            telegram_id=456,
            name="Good User",
            timezone="Asia/Kolkata",
            streaks=UserStreaks(
                current_streak=50,
                longest_streak=50,
                last_checkin_date="2026-02-06",
                total_checkins=50
            )
        )
        
        message = achievement_service.get_social_proof_message(user)
        
        assert message is not None
        assert "TOP 10%" in message
        assert "🌟" in message


def test_social_proof_message_short_streak_returns_none(achievement_service):
    """Test social proof not shown for streaks < 30 days."""
    with patch.object(achievement_service, 'calculate_percentile', return_value=95):
        user = User(
            user_id="new_user",
            telegram_id=789,
            name="New User",
            timezone="Asia/Kolkata",
            streaks=UserStreaks(
                current_streak=15,  # Below 30-day threshold
                longest_streak=15,
                last_checkin_date="2026-02-06",
                total_checkins=15
            )
        )
        
        message = achievement_service.get_social_proof_message(user)
        
        assert message is None  # No social proof for short streaks


def test_social_proof_message_no_percentile_returns_none(achievement_service):
    """Test social proof not shown if percentile can't be calculated."""
    with patch.object(achievement_service, 'calculate_percentile', return_value=None):
        user = User(
            user_id="user",
            telegram_id=111,
            name="User",
            timezone="Asia/Kolkata",
            streaks=UserStreaks(
                current_streak=50,
                longest_streak=50,
                last_checkin_date="2026-02-06",
                total_checkins=50
            )
        )
        
        message = achievement_service.get_social_proof_message(user)
        
        assert message is None


# ===== Test: Edge Cases =====

def test_achievement_check_with_empty_recent_checkins(achievement_service, user_7day_streak):
    """Test achievement checking works with empty recent check-ins."""
    newly_unlocked = achievement_service.check_achievements(user_7day_streak, [])
    
    # Should still detect streak-based achievements
    assert isinstance(newly_unlocked, list)


def test_achievement_check_with_invalid_achievement_id(achievement_service, user_7day_streak):
    """Test getting invalid achievement doesn't crash."""
    achievement = achievement_service.get_achievement("invalid_id")
    assert achievement is None


def test_percentile_calculation_with_zero_streak(achievement_service):
    """Test percentile calculation handles zero streak."""
    with patch('src.services.achievement_service.firestore_service.get_all_users') as mock_get_users:
        mock_users = [
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
            for i in range(10, 20)
        ]
        mock_get_users.return_value = mock_users
        
        percentile = achievement_service.calculate_percentile(0)
        
        assert percentile is not None
        assert percentile == 0  # 0 streak is at bottom


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
