"""
Test: Feature Discovery Service
================================

Tests contextual hint triggering.
"""

import pytest
from datetime import datetime

from src.models.schemas import User, UserStreaks, DailyCheckIn, Tier1NonNegotiables, CheckInResponses
from src.services.feature_discovery_service import FeatureDiscoveryService


def make_user(total_checkins=0, current_streak=0, hints_sent=None) -> User:
    return User(
        user_id="111",
        telegram_id=111,
        name="Test",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=current_streak,
            longest_streak=current_streak,
            total_checkins=total_checkins,
        ),
        hints_sent=hints_sent or [],
    )


def make_checkin(rating=7) -> DailyCheckIn:
    return DailyCheckIn(
        date="2026-02-15",
        user_id="111",
        mode="maintenance",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=True, training=True, deep_work=True,
            skill_building=True, zero_porn=True, boundaries=True,
        ),
        responses=CheckInResponses(
            challenges="Test challenges for the day with enough characters",
            rating=rating,
            rating_reason="Solid day overall with good consistency and progress",
            tomorrow_priority="Continue daily check-ins and maintain streak",
            tomorrow_obstacle="Late night work might interfere with bedtime routine",
        ),
        compliance_score=80.0,
    )


class TestFeatureHints:
    """Test hint triggering."""

    def test_hint_after_3_checkins(self):
        svc = FeatureDiscoveryService()
        user = make_user(total_checkins=3)
        checkins = [make_checkin()]

        hint = svc.check_and_send_hint(user, "after_3_checkins", checkins)
        assert hint is not None
        assert "quickcheckin" in hint.lower()

    def test_no_hint_if_disabled(self):
        svc = FeatureDiscoveryService()
        user = make_user(total_checkins=3)
        user.settings = {"feature_hints_enabled": False}
        checkins = [make_checkin()]

        hint = svc.check_and_send_hint(user, "after_3_checkins", checkins)
        assert hint is None

    def test_no_duplicate_hint(self):
        svc = FeatureDiscoveryService()
        user = make_user(total_checkins=3, hints_sent=["quickcheckin"])
        checkins = [make_checkin()]

        hint = svc.check_and_send_hint(user, "after_3_checkins", checkins)
        assert hint is None

    def test_streak_7_hint(self):
        svc = FeatureDiscoveryService()
        user = make_user(current_streak=7)
        checkins = [make_checkin()]

        hint = svc.check_and_send_hint(user, "streak_7_days", checkins)
        assert hint is not None
        assert "achievements" in hint.lower()

    def test_low_rating_hint(self):
        svc = FeatureDiscoveryService()
        user = make_user()
        checkins = [make_checkin(rating=3), make_checkin(rating=3), make_checkin(rating=3)]

        hint = svc.check_and_send_hint(user, "low_rating_3_days", checkins)
        assert hint is not None
        assert "support" in hint.lower()

    def test_daily_throttle(self):
        svc = FeatureDiscoveryService()
        user = make_user(total_checkins=3)
        checkins = [make_checkin()]

        # First hint
        hint1 = svc.check_and_send_hint(user, "after_3_checkins", checkins)
        assert hint1 is not None

        # Same day, no more hints
        hint2 = svc.check_and_send_hint(user, "streak_7_days", checkins)
        assert hint2 is None
