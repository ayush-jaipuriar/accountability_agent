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
from typing import Optional, List, Any

from src.models.schemas import User, DailyCheckIn, DailyTaskList
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

        # Get or create today's daily focus list
        today_yyyy_mm_dd = now_local.strftime("%Y-%m-%d")
        yesterday_priority = ""
        if yesterday_checkin:
            yesterday_priority = yesterday_checkin.responses.tomorrow_priority or ""

        from src.services.task_service import task_service
        task_list = task_service.create_or_get_daily_tasks(user.user_id, today_yyyy_mm_dd, yesterday_priority)

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

        # Priority and obstacle follow-up (closing the loop)
        if yesterday_checkin:
            obstacle = yesterday_checkin.responses.tomorrow_obstacle
            if obstacle:
                if len(obstacle) > 120:
                    obstacle = obstacle[:117] + "..."
                sections.append(f"⚠️ <b>Anticipated obstacle for today:</b> \"{obstacle}\"\n")

        # Daily Focus List rendering
        if task_list:
            if not task_list.committed:
                sections.append("🎯 <b>Today's Focus List (Uncommitted):</b>")
                for t in task_list.tasks:
                    prefix = "🎯 [Primary]" if t.is_primary else "• [Secondary]"
                    sections.append(f"   {prefix} {t.title}")
                sections.append("<i>Use the buttons below to add secondary tasks or commit to your list.</i>\n")
            else:
                sections.append("🎯 <b>Today's Active Focus:</b>")
                for t in task_list.tasks:
                    status_icon = "✅" if t.completed else "⬜️"
                    prefix = "[Primary]" if t.is_primary else "[Secondary]"
                    sections.append(f"   {status_icon} {prefix} {t.title}")
                sections.append("")

        # Day-of-week insight
        dow_insight = self._generate_dow_insight(history, user.timezone)
        if dow_insight:
            sections.append(dow_insight + "\n")

        # Active Goals Integration
        try:
            from src.services.goal_service import goal_service
            active_goals = goal_service.get_user_goals(user.user_id, status="active")
            if active_goals:
                goal_lines = ["🏁 <b>Active Goals:</b>"]
                for goal in active_goals[:2]:  # limit to 2 for brevity
                    consecutive = goal_service._count_consecutive_met(goal.progress)
                    pct = min(100, int((consecutive / goal.target_days) * 100))
                    goal_lines.append(f"• 🎯 {goal.title} ({consecutive}/{goal.target_days}d, {pct}%)")
                sections.append("\n".join(goal_lines) + "\n")
        except Exception as e:
            logger.warning(f"Error fetching active goals for briefing: {e}")

        # Partner Challenges Integration
        try:
            from src.services.challenge_service import challenge_service
            active_challenges = challenge_service.get_user_challenges(user.user_id, status="active")
            if active_challenges:
                challenge_lines = ["👥 <b>Active Challenges:</b>"]
                for ch in active_challenges[:1]:  # limit to 1
                    challenge_lines.append(f"• 🔥 {ch.title} vs partner")
                sections.append("\n".join(challenge_lines) + "\n")
        except Exception as e:
            logger.warning(f"Error fetching active challenges for briefing: {e}")

        # Coach's Guidance / Daily Suggestion
        gemini_sug = await self._generate_gemini_suggestion(user, yesterday_checkin, history)
        if gemini_sug:
            sections.append(f"💡 <b>Coach's Guidance:</b>\n{gemini_sug}\n")
        else:
            suggestion = self._generate_suggestion(user, yesterday_checkin, history)
            if suggestion:
                sections.append(f"💡 <b>Today's focus:</b> {suggestion}\n")

        # Footer
        sections.append("<i>/checkin when ready →</i>")

        return "\n".join(sections)

    async def _generate_gemini_suggestion(
        self,
        user: User,
        yesterday_checkin: Optional[DailyCheckIn],
        history: List[DailyCheckIn]
    ) -> Optional[str]:
        """Generate a personalized suggestion using Gemini API."""
        try:
            from src.config import settings
            from src.services.llm_service import get_llm_service
            
            # 1. Instantiate the LLM service
            project_id = getattr(settings, 'gcp_project_id', 'accountability-agent')
            llm = get_llm_service(project_id=project_id)
            
            # 2. Gather user context
            streak = user.streaks.current_streak if user.streaks else 0
            
            # Yesterday's details
            yesterday_summary = "No check-in recorded yesterday."
            priority = "Not specified"
            obstacle = "Not specified"
            mood_text = ""
            
            if yesterday_checkin:
                compliance = yesterday_checkin.compliance_score
                yesterday_summary = f"- Compliance Score: {compliance:.0f}%\n"
                
                wins = []
                misses = []
                tier1 = yesterday_checkin.tier1_non_negotiables
                
                if tier1.sleep: wins.append("sleep")
                else: misses.append("sleep")
                if tier1.deep_work: wins.append("deep work")
                else: misses.append("deep work")
                if tier1.training: wins.append("training")
                else: misses.append("training")
                if tier1.skill_building: wins.append("skill building")
                else: misses.append("skill building")
                
                if wins:
                    yesterday_summary += f"- Accomplished: {', '.join(wins)}\n"
                if misses:
                    yesterday_summary += f"- Missed: {', '.join(misses)}\n"
                    
                priority = yesterday_checkin.responses.tomorrow_priority or "Not specified"
                obstacle = yesterday_checkin.responses.tomorrow_obstacle or "Not specified"
                
                mood_rating = getattr(yesterday_checkin.responses, 'mood_rating', None)
                energy_rating = getattr(yesterday_checkin.responses, 'energy_rating', None)
                if mood_rating is not None or energy_rating is not None:
                    mood_parts = []
                    if mood_rating is not None:
                        mood_parts.append(f"Mood: {mood_rating}/10")
                    if energy_rating is not None:
                        mood_parts.append(f"Energy: {energy_rating}/10")
                    mood_text = f"Yesterday's Mood/Energy:\n- {', '.join(mood_parts)}\n"
            
            # 30-day history trend
            compliance_avg = 0
            dow_trend_text = "No long-term day of week trend available."
            if history:
                scores = [c.compliance_score for c in history if c.compliance_score is not None]
                if scores:
                    compliance_avg = mean(scores)
                
                # Check for DOW insight
                dow_insight = self._generate_dow_insight(history, user.timezone)
                if dow_insight:
                    import re
                    clean_insight = re.sub(r'<[^>]+>', '', dow_insight)
                    dow_trend_text = clean_insight
            
            # Build final prompt
            prompt = f"""You are a supportive, high-performance accountability coach. Write a highly personalized, concise morning briefing note for the user based on their check-in data.

User: {user.name}
Current Streak: {streak} days

Yesterday's Check-in Summary:
{yesterday_summary}
{mood_text}
Yesterday's Stated Focus for Today:
- Today's Priority: "{priority}"
- Anticipated Obstacle: "{obstacle}"

Historical Trend (Past 30 Days):
- Compliance Average: {compliance_avg:.0f}%
- Day of Week Trend: {dow_trend_text}

Instructions:
1. Write a 2-3 sentence daily coaching note.
2. Address the user's priority for today and their anticipated obstacle.
3. Suggest a concrete, highly actionable strategy to overcome that obstacle.
4. Keep the tone empathetic, encouraging, and brief (under 60 words).
5. Output ONLY the note. Do not include any greeting, markdown headings, or conversational filler.
"""
            
            response = await llm.generate_text(
                prompt=prompt,
                max_output_tokens=150,
                temperature=0.7
            )
            
            note = response.strip()
            if note.startswith('"') and note.endswith('"'):
                note = note[1:-1].strip()
            
            return note
            
        except Exception as e:
            logger.warning(f"Failed to generate Gemini morning briefing suggestion: {e}", exc_info=True)
            return None

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

    def get_briefing_keyboard(self, task_list: Optional[DailyTaskList]) -> Optional[Any]:
        """Generate Telegram inline keyboard for daily focus tasks."""
        if not task_list:
            return None
            
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = []
        if not task_list.committed:
            # Uncommitted: Show Add Task and Commit buttons
            secondary_tasks = [t for t in task_list.tasks if not t.is_primary]
            buttons_row = []
            if len(secondary_tasks) < 2:
                buttons_row.append(InlineKeyboardButton("➕ Add Task", callback_data="task_add"))
            buttons_row.append(InlineKeyboardButton("🚀 Commit & Start", callback_data="task_commit"))
            keyboard.append(buttons_row)
        else:
            # Committed: Show checkboxes for toggling each task
            for t in task_list.tasks:
                status_icon = "✅" if t.completed else "⬜️"
                label = "Primary" if t.is_primary else "Secondary"
                button_text = f"{status_icon} {label}: {t.title}"
                if len(button_text) > 30:
                    button_text = button_text[:27] + "..."
                
                new_state = 0 if t.completed else 1
                keyboard.append([
                    InlineKeyboardButton(button_text, callback_data=f"task_toggle:{t.id}:{new_state}")
                ])
                
            # Add Need Support button
            keyboard.append([
                InlineKeyboardButton("🛡️ Need Support", callback_data="task_support")
            ])
            
        return InlineKeyboardMarkup(keyboard)


# Singleton instance
briefing_service = BriefingService()
