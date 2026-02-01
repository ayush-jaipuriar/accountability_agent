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
