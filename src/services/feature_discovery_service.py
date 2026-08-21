"""
Feature Discovery Service
=========================

Contextual hints triggered by user behavior milestones.

Theory: Progressive Disclosure
--------------------------------
Users discover <30% of features because they're hidden behind commands.
Contextual hints surface features at the exact moment they're relevant,
maximizing adoption without feeling spammy.
"""

import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

from src.models.schemas import User, DailyCheckIn
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


FEATURE_HINTS = {
    "quickcheckin": {
        "trigger": "after_3_checkins",
        "message": (
            "💡 <b>Tip:</b> Busy day? Use /quickcheckin for a 30-second check-in "
            "(2 per week). Try it tomorrow!"
        ),
    },
    "support": {
        "trigger": "low_rating_3_days",
        "message": (
            "💡 <b>Tip:</b> Struggling? Type /support anytime to talk it through. "
            "You're not alone."
        ),
    },
    "achievements": {
        "trigger": "streak_7_days",
        "message": (
            "🏅 <b>Achievement unlocked!</b> See all your badges: /achievements"
        ),
    },
    "partner": {
        "trigger": "streak_14_days",
        "message": (
            "💡 <b>Tip:</b> An accountability partner 2x's your success rate. "
            "Link up: /set_partner"
        ),
    },
    "shield": {
        "trigger": "streak_at_risk",
        "message": (
            "🛡️ <b>Tip:</b> Missed a day? Use /use_shield to protect your streak "
            "(3 per month)."
        ),
    },
    "insights": {
        "trigger": "first_pattern_detected",
        "message": (
            "🔍 <b>Pattern detected!</b> I analyze your habits automatically. "
            "See patterns: /insights"
        ),
    },
    "goals": {
        "trigger": "streak_21_days",
        "message": (
            "🎯 <b>Tip:</b> Set a goal to track specific habits over time: /goal_new"
        ),
    },
    "challenges": {
        "trigger": "streak_30_days",
        "message": (
            "🏆 <b>Tip:</b> Challenge your accountability partner to a friendly duel: "
            "/challenge_new"
        ),
    },
}


class FeatureDiscoveryService:
    """Send contextual feature hints based on user behavior."""

    def __init__(self):
        self.last_hint_date: Dict[str, str] = {}  # In-memory daily throttling

    def check_and_send_hint(
        self,
        user: User,
        event: str,
        checkins: List[DailyCheckIn],
    ) -> Optional[str]:
        """
        Check if any hint should be sent based on user event.

        Returns hint message or None if no hint should be sent.
        """
        # Check if hints are enabled
        settings = getattr(user, 'settings', {}) or {}
        if not settings.get("feature_hints_enabled", True):
            return None

        # Daily throttle: max 1 hint per day
        from src.utils.timezone_utils import get_current_date
        today = get_current_date()
        last_hint = self.last_hint_date.get(user.user_id)
        if last_hint == today:
            return None

        # Get already-sent hints
        hints_sent = list(user.hints_sent) if getattr(user, 'hints_sent', None) is not None else []

        for feature_id, hint in FEATURE_HINTS.items():
            if hint["trigger"] == event and feature_id not in hints_sent:
                if self._should_trigger(event, user, checkins):
                    self.last_hint_date[user.user_id] = today
                    return hint["message"]

        return None

    def _should_trigger(
        self,
        event: str,
        user: User,
        checkins: List[DailyCheckIn],
    ) -> bool:
        """Evaluate if the trigger condition is actually met."""
        if event == "after_3_checkins":
            return user.streaks.total_checkins >= 3

        elif event == "low_rating_3_days":
            recent = checkins[-3:] if len(checkins) >= 3 else checkins
            low_ratings = sum(
                1 for c in recent
                if c.responses.rating <= 4
            )
            return low_ratings >= 2

        elif event == "streak_7_days":
            return user.streaks.current_streak == 7

        elif event == "streak_14_days":
            return user.streaks.current_streak == 14

        elif event == "streak_21_days":
            return user.streaks.current_streak == 21

        elif event == "streak_30_days":
            return user.streaks.current_streak == 30

        elif event == "streak_at_risk":
            # Triggered externally by streak logic
            return True

        elif event == "first_pattern_detected":
            # Triggered externally by pattern detection
            return True

        return False

    def mark_hint_sent(self, user_id: str, feature_id: str) -> None:
        """Mark a hint as sent for a user."""
        user = firestore_service.get_user(user_id)
        if not user:
            return

        hints_sent = list(user.hints_sent) if hasattr(user, 'hints_sent') else []
        if feature_id not in hints_sent:
            hints_sent.append(feature_id)
            firestore_service.update_user(user_id, {"hints_sent": hints_sent})
            logger.info(f"💡 Hint '{feature_id}' marked as sent for {user_id}")


# Singleton instance
feature_discovery_service = FeatureDiscoveryService()
