"""
Goal Service
============

CRUD operations and automatic progress tracking for user goals.

Goals are created by users via /goal_new and auto-update after every check-in.
Progress is calculated by comparing check-in data against the goal's target.

Theory: Closing the Loop
--------------------------
The constitution says "Sleep 7+ hours" but there's no way to track "have I
slept 7+ hours for 14 days straight?" Goals make that explicit and celebrate
milestones.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Tuple

from src.models.schemas import Goal, DailyCheckIn
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


class GoalService:
    """Manage user goals and auto-track progress from check-ins."""

    def __init__(self):
        self.firestore = firestore_service

    def create_goal(
        self,
        user_id: str,
        title: str,
        description: str,
        category: str,
        target_value: Optional[float],
        target_days: int,
        start_date: Optional[str] = None,
    ) -> Goal:
        """
        Create a new goal for a user.

        Args:
            user_id: User ID
            title: Short title
            description: Detailed description
            category: sleep | training | deep_work | skill_building | zero_porn | boundaries | custom
            target_value: Numeric target (e.g., 7.0 hours)
            target_days: Number of consecutive days
            start_date: YYYY-MM-DD (defaults to today)

        Returns:
            Created Goal object
        """
        if start_date is None:
            from src.utils.timezone_utils import get_current_date
            start_date = get_current_date()

        goal = Goal(
            user_id=user_id,
            title=title,
            description=description,
            category=category,
            target_value=target_value,
            target_days=target_days,
            start_date=start_date,
        )

        # Store in Firestore
        self.firestore.db.collection("goals").document(goal.goal_id).set(goal.to_firestore())
        logger.info(f"🎯 Goal created: {goal.goal_id} for {user_id}")
        return goal

    def get_user_goals(self, user_id: str, status: Optional[str] = None) -> List[Goal]:
        """
        Fetch goals for a user.

        Args:
            user_id: User ID
            status: Filter by status (active | completed | failed | paused)

        Returns:
            List of Goal objects
        """
        try:
            query = self.firestore.db.collection("goals").where("user_id", "==", user_id)
            if status:
                query = query.where("status", "==", status)

            docs = query.stream()
            goals = [Goal.from_firestore(doc.to_dict()) for doc in docs]
            return goals
        except Exception as e:
            logger.error(f"❌ Failed to fetch goals for {user_id}: {e}")
            return []

    def get_goal(self, goal_id: str) -> Optional[Goal]:
        """Fetch a single goal by ID."""
        try:
            doc = self.firestore.db.collection("goals").document(goal_id).get()
            if doc.exists:
                return Goal.from_firestore(doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"❌ Failed to fetch goal {goal_id}: {e}")
            return None

    def update_goal_status(self, goal_id: str, status: str) -> bool:
        """Update goal status (completed | failed | paused | active)."""
        try:
            updates = {"status": status}
            if status == "completed":
                updates["completed_at"] = datetime.utcnow()
            self.firestore.db.collection("goals").document(goal_id).update(updates)
            logger.info(f"🎯 Goal {goal_id} status updated to {status}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update goal {goal_id}: {e}")
            return False

    def delete_goal(self, goal_id: str) -> bool:
        """Delete a goal."""
        try:
            self.firestore.db.collection("goals").document(goal_id).delete()
            logger.info(f"🗑️ Goal {goal_id} deleted")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to delete goal {goal_id}: {e}")
            return False

    def update_progress_from_checkin(self, checkin: DailyCheckIn) -> List[Tuple[Goal, str]]:
        """
        Auto-update goal progress based on a check-in.

        Called after every check-in. Compares check-in data against active goals
        and updates progress. Returns list of (goal, milestone) tuples where
        milestone is one of: "50%", "75%", "100%", "streak_broken", or None.

        Args:
            checkin: DailyCheckIn object

        Returns:
            List of (Goal, milestone_str) tuples
        """
        user_id = checkin.user_id
        date = checkin.date
        tier1 = checkin.tier1_non_negotiables

        active_goals = self.get_user_goals(user_id, status="active")
        results = []

        for goal in active_goals:
            milestone = self._evaluate_goal_for_date(goal, date, tier1)
            if milestone:
                results.append((goal, milestone))

        return results

    def _evaluate_goal_for_date(
        self,
        goal: Goal,
        date: str,
        tier1
    ) -> Optional[str]:
        """
        Evaluate whether a single goal was met for a given date.

        Returns:
            Milestone string if hit, None otherwise
        """
        # Skip if date is before start_date
        if date < goal.start_date:
            return None

        met = False
        value = None

        # Evaluate based on category
        if goal.category == "sleep":
            value = getattr(tier1, 'sleep_hours', None)
            if value is not None and goal.target_value is not None:
                met = value >= goal.target_value
            else:
                met = tier1.sleep

        elif goal.category == "training":
            intensity = getattr(tier1, 'training_intensity', None)
            if intensity is not None:
                met = intensity.lower() in ('light', 'moderate', 'intense')
            else:
                met = tier1.training

        elif goal.category == "deep_work":
            value = getattr(tier1, 'deep_work_hours', None)
            if value is not None and goal.target_value is not None:
                met = value >= goal.target_value
            else:
                met = tier1.deep_work

        elif goal.category == "skill_building":
            value = getattr(tier1, 'skill_building_hours', None)
            if value is not None and goal.target_value is not None:
                met = value >= goal.target_value
            else:
                met = tier1.skill_building

        elif goal.category == "zero_porn":
            met = tier1.zero_porn

        elif goal.category == "boundaries":
            met = tier1.boundaries

        elif goal.category == "custom":
            # Custom goals require manual progress updates
            return None

        # Record progress (deduplicate by date)
        progress_entry = {
            "date": date,
            "met": met,
            "value": value,
        }
        prev_consecutive = self._count_consecutive_met(goal.progress)
        goal.progress = [p for p in goal.progress if p.get("date") != date]
        goal.progress.append(progress_entry)

        # Check for streak completion
        consecutive_met = self._count_consecutive_met(goal.progress)

        # Check milestones
        milestone = None
        if consecutive_met >= goal.target_days:
            milestone = "100%"
            goal.status = "completed"
            goal.completed_at = datetime.utcnow()
        elif consecutive_met >= int(goal.target_days * 0.75):
            milestone = "75%"
        elif consecutive_met >= int(goal.target_days * 0.5):
            milestone = "50%"

        # Save updated goal
        try:
            self.firestore.db.collection("goals").document(goal.goal_id).update({
                "progress": goal.progress,
                "status": goal.status,
                "completed_at": goal.completed_at,
            })
        except Exception as e:
            logger.error(f"❌ Failed to save goal progress for {goal.goal_id}: {e}")

        return milestone

    def _count_consecutive_met(self, progress: List[Dict]) -> int:
        """Count consecutive days with met=True at the end of progress."""
        consecutive = 0
        for entry in reversed(progress):
            if entry.get("met"):
                consecutive += 1
            else:
                break
        return consecutive

    def format_goal_progress(self, goal: Goal) -> str:
        """
        Format a goal's progress for display in Telegram.

        Returns:
            HTML-formatted string
        """
        consecutive = self._count_consecutive_met(goal.progress)
        pct = min(100, int((consecutive / goal.target_days) * 100))

        # Progress bar
        filled = int(pct / 10)
        bar = "█" * filled + "░" * (10 - filled)

        status_emoji = {
            "active": "🎯",
            "completed": "🏆",
            "failed": "❌",
            "paused": "⏸️",
        }.get(goal.status, "🎯")

        lines = [
            f"{status_emoji} <b>{goal.title}</b>",
            f"   <i>{goal.description}</i>",
            f"",
            f"   Progress: {bar} {pct}%",
            f"   {consecutive}/{goal.target_days} days",
        ]

        if goal.target_value is not None:
            lines.append(f"   Target: {goal.target_value}")

        if goal.status == "completed":
            lines.append(f"   🎉 Completed!")

        return "\n".join(lines)


# Singleton instance
goal_service = GoalService()
