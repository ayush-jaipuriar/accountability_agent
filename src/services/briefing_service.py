"""
Morning Briefing Service
========================

Generates personalized morning briefings for users.

Trigger: Cron job at 8:00 AM local time (timezone-aware).
Content:
- Yesterday's performance summary
- Stated priority follow-up
- Day-of-week historical insight
- Actionable suggestion for today

Theory: Closing the Feedback Loop
---------------------------------
Every check-in captures "tomorrow's priority" and "tomorrow's obstacle,"
but these were never referenced again. The morning briefing closes this loop
by surfacing yesterday's priority as today's focus, creating continuity
between check-ins and increasing engagement.
"""

import logging
from datetime import datetime, timedelta
from statistics import mean
from typing import Optional, List

from src.models.schemas import User, DailyCheckIn
from src.services.firestore_service import firestore_service
from src.utils.timezone_utils import get_current_time

logger = logging.getLogger(__name__)


class BriefingService:
    """Generate personalized morning briefings."""

    def __init__(self):
        self.firestore = firestore_service

    async def generate_briefing(self, user: User) -> Optional[str]:
        """
        Generate morning briefing for a user.

        Returns None if:
        - Briefings are disabled
        - User has no check-in history
        - Already sent briefing today

        Args:
            user: User object

        Returns:
            Formatted HTML message or None
        """
        settings = getattr(user, 'settings', {}) or {}

        # Check if enabled
        if not settings.get("morning_briefing_enabled", True):
            logger.info(f"Briefing disabled for user {user.user_id}")
            return None

        # Get yesterday's date in user's timezone
        now_local = get_current_time(user.timezone)
        yesterday = (now_local - timedelta(days=1)).strftime("%Y-%m-%d")
        today_str = now_local.strftime("%A, %B %d")

        # Check if already sent today
        last_briefing = settings.get("last_briefing_date")
        if last_briefing == now_local.strftime("%Y-%m-%d"):
            logger.info(f"Briefing already sent today for user {user.user_id}")
            return None

        # Fetch yesterday's check-in
        yesterday_checkin = self.firestore.get_checkin(user.user_id, yesterday)

        # Fetch 30-day history for patterns
        history = self.firestore.get_recent_checkins(user.user_id, days=30)

        # Skip if no history at all
        if not history and not yesterday_checkin:
            logger.info(f"No check-in history for user {user.user_id}, skipping briefing")
            return None

        # Build sections
        sections = []

        # Header
        sections.append(f"🌅 <b>Good morning, {user.name}!</b>")
        sections.append(f"<i>{today_str}</i>\n")

        # Yesterday's performance
        if yesterday_checkin:
            sections.append(self._format_yesterday_summary(yesterday_checkin))
        else:
            sections.append("📭 <b>Yesterday:</b> No check-in recorded\n")

        # Priority follow-up
        if yesterday_checkin and yesterday_checkin.responses.tomorrow_priority:
            priority = yesterday_checkin.responses.tomorrow_priority
            # Truncate if too long
            if len(priority) > 120:
                priority = priority[:117] + "..."
            sections.append(f"🎯 <b>Your stated priority:</b> \"{priority}\"\n")

        # Day-of-week insight
        dow_insight = self._generate_dow_insight(history, user.timezone)
        if dow_insight:
            sections.append(dow_insight + "\n")

        # Suggestion
        suggestion = self._generate_suggestion(user, yesterday_checkin, history)
        if suggestion:
            sections.append(f"💡 <b>Today's focus:</b> {suggestion}\n")

        # Footer
        sections.append("<i>/checkin when ready →</i>")

        return "\n".join(sections)

    def _format_yesterday_summary(self, checkin: DailyCheckIn) -> str:
        """Format yesterday's check-in as a brief summary."""
        score = checkin.compliance_score
        if score >= 90:
            emoji = "🔥"
        elif score >= 70:
            emoji = "✅"
        else:
            emoji = "⚠️"

        lines = [f"{emoji} <b>Yesterday:</b> {score:.0f}% compliance"]

        # Tier 1 wins (brief)
        tier1 = checkin.tier1_non_negotiables
        wins = []

        # Sleep
        if tier1.sleep:
            sleep_val = getattr(tier1, 'sleep_hours', None)
            if sleep_val is not None:
                wins.append(f"sleep ({sleep_val}h)")
            else:
                wins.append("sleep")

        # Deep Work
        if tier1.deep_work:
            dw_val = getattr(tier1, 'deep_work_hours', None)
            if dw_val is not None:
                wins.append(f"deep work ({dw_val}h)")
            else:
                wins.append("deep work")

        # Training
        if tier1.training:
            intensity = getattr(tier1, 'training_intensity', None)
            if intensity and intensity.lower() != 'rest':
                wins.append(f"training ({intensity})")
            else:
                wins.append("training")

        # Skill Building
        if tier1.skill_building:
            sb_val = getattr(tier1, 'skill_building_hours', None)
            if sb_val is not None:
                wins.append(f"skill building ({sb_val}h)")
            else:
                wins.append("skill building")

        if wins:
            lines.append(f"   ✅ {', '.join(wins)}")

        misses = []
        if not tier1.sleep: misses.append("sleep")
        if not tier1.deep_work: misses.append("deep work")
        if not tier1.training: misses.append("training")
        if not tier1.skill_building: misses.append("skill building")

        if misses:
            lines.append(f"   ❌ {', '.join(misses)}")

        return "\n".join(lines)

    def _generate_dow_insight(self, history: List[DailyCheckIn], timezone: str) -> Optional[str]:
        """Generate day-of-week insight."""
        if len(history) < 14:  # Need at least 2 weeks of data
            return None

        # Get today's day of week
        now_local = get_current_time(timezone)
        today_dow = now_local.strftime("%A")

        # Group by day of week
        dow_scores = {}
        for checkin in history:
            try:
                dow = datetime.strptime(checkin.date, "%Y-%m-%d").strftime("%A")
                if dow not in dow_scores:
                    dow_scores[dow] = []
                dow_scores[dow].append(checkin.compliance_score)
            except (ValueError, AttributeError):
                continue

        if today_dow not in dow_scores or len(dow_scores[today_dow]) < 2:
            return None

        today_avg = mean(dow_scores[today_dow])
        all_scores = [s for scores in dow_scores.values() for s in scores]
        overall_avg = mean(all_scores) if all_scores else 0

        if today_avg >= overall_avg + 5:
            trend = "strongest"
        elif today_avg <= overall_avg - 5:
            trend = "weakest"
        else:
            return None  # No significant difference

        return f"📊 <b>{today_dow}s are historically your {trend} day</b> ({today_avg:.0f}% avg)"

    def _generate_suggestion(
        self,
        user: User,
        yesterday_checkin: Optional[DailyCheckIn],
        history: List[DailyCheckIn]
    ) -> str:
        """Generate one actionable suggestion."""

        # If yesterday was missed, suggest getting back on track
        if yesterday_checkin is None:
            streak = user.streaks.current_streak if user.streaks else 0
            if streak > 0:
                return (
                    f"You missed yesterday after a {streak}-day streak. "
                    "One check-in today restarts momentum. You've done it before."
                )
            return "You missed yesterday. One check-in today gets you back on track."

        tier1 = yesterday_checkin.tier1_non_negotiables

        # Suggest based on yesterday's misses
        if not tier1.sleep:
            sleep_h = getattr(tier1, 'sleep_hours', None)
            if sleep_h is not None and sleep_h < 6:
                return "You were short on sleep. Aim for 10:30 PM bedtime tonight."
            return "Sleep was missed yesterday. Protect your wind-down routine tonight."

        if not tier1.training:
            return f"You skipped training yesterday. Schedule it for {self._suggest_training_time(history)}."

        if not tier1.deep_work:
            return "Protect your deep work block today. Put phone in another room."

        if not tier1.skill_building:
            return "Even 30 minutes of skill building counts. Block 30 min after lunch."

        # If perfect, suggest maintenance
        if yesterday_checkin.compliance_score == 100:
            return "Perfect day yesterday! The goal is consistency, not perfection. Keep the rhythm."

        return "Focus on one thing today. Small wins compound."

    def _suggest_training_time(self, history: List[DailyCheckIn]) -> str:
        """Suggest optimal training time based on history."""
        # Simple heuristic: suggest morning
        return "7 AM before the day gets away"


# Singleton instance
briefing_service = BriefingService()
