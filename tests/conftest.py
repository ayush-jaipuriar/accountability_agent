"""
Pytest Configuration & Fixtures
===============================

Shared test fixtures and configuration for all tests.

Fixtures are reusable test components (like mock data, test users, etc.)
that pytest automatically provides to test functions.

Usage in tests:
    def test_something(sample_user):
        # sample_user is automatically provided by pytest
        assert sample_user.user_id == "123456789"
"""

import pytest
from datetime import datetime
from src.models.schemas import (
    User,
    UserStreaks,
    Tier1NonNegotiables,
    CheckInResponses,
    DailyCheckIn
)


# ===== Test Data Fixtures =====

@pytest.fixture
def sample_user_streaks():
    """Provide sample UserStreaks object."""
    return UserStreaks(
        current_streak=47,
        longest_streak=47,
        last_checkin_date="2026-01-29",
        total_checkins=100
    )


@pytest.fixture
def sample_user(sample_user_streaks):
    """Provide sample User object."""
    return User(
        user_id="123456789",
        telegram_id=123456789,
        telegram_username="ayush_test",
        name="Ayush",
        timezone="Asia/Kolkata",
        streaks=sample_user_streaks,
        constitution_mode="maintenance"
    )


@pytest.fixture
def sample_tier1_complete():
    """Provide Tier1NonNegotiables with all items completed."""
    return Tier1NonNegotiables(
        sleep=True,
        sleep_hours=7.5,
        training=True,
        is_rest_day=False,
        training_type="workout",
        deep_work=True,
        deep_work_hours=2.5,
        zero_porn=True,
        boundaries=True
    )


@pytest.fixture
def sample_tier1_partial():
    """Provide Tier1NonNegotiables with some items incomplete."""
    return Tier1NonNegotiables(
        sleep=False,  # Missed
        sleep_hours=5.5,
        training=True,
        deep_work=True,
        deep_work_hours=2.0,
        zero_porn=True,
        boundaries=True
    )


@pytest.fixture
def sample_responses():
    """Provide sample CheckInResponses."""
    return CheckInResponses(
        challenges="Urge to watch porn around 10 PM. Went for walk instead.",
        rating=8,
        rating_reason="Solid day overall. Missed sleep target but otherwise strong.",
        tomorrow_priority="Complete 3 LeetCode problems and apply to 2 jobs",
        tomorrow_obstacle="Late evening meeting might drain energy"
    )


@pytest.fixture
def sample_checkin(sample_tier1_complete, sample_responses):
    """Provide sample DailyCheckIn object."""
    return DailyCheckIn(
        date="2026-01-30",
        user_id="123456789",
        mode="maintenance",
        tier1_non_negotiables=sample_tier1_complete,
        responses=sample_responses,
        compliance_score=100.0,
        completed_at=datetime.utcnow(),
        duration_seconds=120
    )


# ===== Phase 3F Fixtures =====

@pytest.fixture
def sample_week_checkins():
    """
    Provide 7 days of varied check-ins for graph/report testing.
    
    Data is realistic with variation in sleep, compliance, training
    to ensure graphs render meaningful visualizations.
    """
    from datetime import timedelta
    
    checkins = []
    # Parameters that vary day by day for realistic test data
    day_params = [
        {"sleep": True, "sleep_h": 8.0, "train": True,  "dw": True,  "sb": True,  "zp": True,  "bd": True,  "comp": 100.0, "rating": 9},
        {"sleep": True, "sleep_h": 7.5, "train": True,  "dw": True,  "sb": False, "zp": True,  "bd": True,  "comp": 83.3,  "rating": 8},
        {"sleep": False,"sleep_h": 5.5, "train": False, "dw": True,  "sb": True,  "zp": True,  "bd": True,  "comp": 66.7,  "rating": 6},
        {"sleep": True, "sleep_h": 7.0, "train": True,  "dw": True,  "sb": True,  "zp": True,  "bd": False, "comp": 83.3,  "rating": 7},
        {"sleep": True, "sleep_h": 7.8, "train": True,  "dw": True,  "sb": True,  "zp": True,  "bd": True,  "comp": 100.0, "rating": 10},
        {"sleep": False,"sleep_h": 6.0, "train": True,  "dw": False, "sb": False, "zp": True,  "bd": True,  "comp": 50.0,  "rating": 5},
        {"sleep": True, "sleep_h": 7.2, "train": False, "dw": True,  "sb": True,  "zp": True,  "bd": True,  "comp": 83.3,  "rating": 8},
    ]
    
    for i, params in enumerate(day_params):
        date = (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
        checkins.append(DailyCheckIn(
            date=date,
            user_id="123456789",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=params["sleep"],
                sleep_hours=params["sleep_h"],
                training=params["train"],
                is_rest_day=(i == 6 and not params["train"]),
                training_type="workout" if params["train"] else "skipped",
                deep_work=params["dw"],
                deep_work_hours=2.5 if params["dw"] else 0.5,
                skill_building=params["sb"],
                skill_building_hours=2.0 if params["sb"] else 0,
                zero_porn=params["zp"],
                boundaries=params["bd"],
            ),
            responses=CheckInResponses(
                challenges="Test challenges for day with varied difficulty and focus areas today",
                rating=params["rating"],
                rating_reason="Rating explanation with enough detail to pass validation check min length",
                tomorrow_priority="Priority for tomorrow focuses on key deliverables and consistency here",
                tomorrow_obstacle="Potential obstacle includes time management and energy preservation task",
            ),
            compliance_score=params["comp"],
            is_quick_checkin=(i == 5),
        ))
    
    return checkins


@pytest.fixture
def sample_month_checkins():
    """
    Provide 30 days of check-ins for export/report testing.
    Generates varied data across a month.
    """
    from datetime import timedelta
    import random
    random.seed(42)  # Deterministic for tests
    
    checkins = []
    for i in range(30):
        date = (datetime.now() - timedelta(days=29-i)).strftime("%Y-%m-%d")
        comp = random.uniform(50, 100)
        sleep_ok = random.random() > 0.2
        train_ok = random.random() > 0.3
        
        checkins.append(DailyCheckIn(
            date=date,
            user_id="123456789",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=sleep_ok,
                sleep_hours=round(random.uniform(5.5, 9.0), 1),
                training=train_ok,
                is_rest_day=(i % 7 == 6),
                deep_work=random.random() > 0.1,
                deep_work_hours=round(random.uniform(1.0, 4.0), 1),
                skill_building=random.random() > 0.4,
                skill_building_hours=round(random.uniform(0, 3.0), 1),
                zero_porn=random.random() > 0.05,
                boundaries=random.random() > 0.1,
            ),
            responses=CheckInResponses(
                challenges=f"Day {i+1} challenges: Working through various tasks and maintaining consistency",
                rating=random.randint(4, 10),
                rating_reason=f"Day {i+1} reason: Overall good effort with some areas needing extra attention",
                tomorrow_priority=f"Day {i+1} priority: Focus on the most impactful tasks and maintain momentum",
                tomorrow_obstacle=f"Day {i+1} obstacle: Managing time across multiple commitments effectively today",
            ),
            compliance_score=round(comp, 1),
        ))
    
    return checkins


@pytest.fixture
def sample_user_3f(sample_user_streaks):
    """User with Phase 3F fields populated."""
    return User(
        user_id="123456789",
        telegram_id=123456789,
        telegram_username="ayush_test",
        name="Ayush",
        timezone="Asia/Kolkata",
        streaks=sample_user_streaks,
        constitution_mode="maintenance",
        career_mode="skill_building",
        leaderboard_opt_in=True,
        referred_by=None,
        referral_code="ref_123456789",
        achievements=["week_warrior", "month_master"],
        level=5,
        xp=500,
    )


# ===== Configuration =====

def pytest_configure(config):
    """
    Pytest configuration hook.
    
    Called before tests run.
    """
    # Add custom markers
    config.addinivalue_line(
        "markers",
        "integration: marks tests as integration tests (slow)"
    )
    config.addinivalue_line(
        "markers",
        "unit: marks tests as unit tests (fast)"
    )


# ===== Async Test Support =====

# pytest-asyncio automatically handles async tests
# No additional configuration needed if pytest-asyncio is installed
