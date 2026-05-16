"""
Predictive Intervention Engine
==============================

Forecasts tomorrow's risk and sends preemptive messages.

Theory: Preemptive Strike
---------------------------
Instead of reacting to patterns after they occur, this engine
predicts problems before they happen and sends specific preventive
actions the evening before.
"""

import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from src.models.schemas import User, DailyCheckIn
from src.services.firestore_service import firestore_service
from src.utils.timezone_utils import get_current_date

logger = logging.getLogger(__name__)


class PredictiveInterventionEngine:
    """Predict tomorrow's risk and suggest preventive actions."""

    def predict_tomorrow_risk(
        self,
        user: User,
        checkins: List[DailyCheckIn],
    ) -> Dict[str, Any]:
        """
        Predict which Tier 1 items are at risk tomorrow.

        Signals:
        - Day-of-week risk (user skips training on 80% of Saturdays)
        - Streak fatigue (day 6 of week, historically lower compliance)
        - Recent decline (compliance dropped 20% over last 3 days)
        """
        if len(checkins) < 14:
            return {"risk_score": 0.0, "risks": [], "preventive_actions": []}

        risks = []
        tomorrow = self._get_tomorrow_date(user.timezone)
        tomorrow_dow = tomorrow.strftime("%A")

        # Day-of-week risk
        dow_risks = self._get_dow_risks(checkins, tomorrow_dow)
        risks.extend(dow_risks)

        # Streak fatigue
        streak_risk = self._get_streak_fatigue_risk(user, checkins)
        if streak_risk:
            risks.append(streak_risk)

        # Recent decline
        decline_risk = self._get_recent_decline_risk(checkins)
        if decline_risk:
            risks.append(decline_risk)

        risk_score = max(r["probability"] for r in risks) if risks else 0.0

        return {
            "risk_score": risk_score,
            "risks": risks,
            "preventive_actions": self._suggest_preventive_actions(risks),
        }

    def _get_tomorrow_date(self, timezone: str) -> datetime:
        """Get tomorrow's date in user's timezone."""
        from src.utils.timezone_utils import get_current_date
        today_str = get_current_date(timezone)
        today = datetime.strptime(today_str, "%Y-%m-%d")
        return today + timedelta(days=1)

    def _get_dow_risks(
        self,
        checkins: List[DailyCheckIn],
        target_dow: str
    ) -> List[Dict[str, Any]]:
        """Find habits that are frequently missed on a given day of week."""
        risks = []

        # Group by day of week
        dow_checkins = defaultdict(list)
        for c in checkins:
            dow = datetime.strptime(c.date, "%Y-%m-%d").strftime("%A")
            dow_checkins[dow].append(c)

        target_checkins = dow_checkins.get(target_dow, [])
        if len(target_checkins) < 3:
            return []

        metrics = ["sleep", "training", "deep_work", "skill_building"]
        for metric in metrics:
            missed = sum(
                1 for c in target_checkins
                if not getattr(c.tier1_non_negotiables, metric, False)
            )
            rate = missed / len(target_checkins)
            if rate >= 0.5:
                risks.append({
                    "metric": metric,
                    "risk": "dow_risk",
                    "probability": min(0.9, rate),
                    "reason": f"You miss {metric} on {rate:.0%} of {target_dow}s",
                })

        return risks

    def _get_streak_fatigue_risk(
        self,
        user: User,
        checkins: List[DailyCheckIn]
    ) -> Optional[Dict[str, Any]]:
        """Check if user is experiencing streak fatigue."""
        current_streak = user.streaks.current_streak
        if current_streak < 6:
            return None

        # Day 6+ of a streak is historically weaker
        if current_streak % 7 == 6:
            return {
                "metric": "general",
                "risk": "streak_fatigue",
                "probability": 0.6,
                "reason": "Day 6 of your streak is historically your weakest",
            }

        return None

    def _get_recent_decline_risk(
        self,
        checkins: List[DailyCheckIn]
    ) -> Optional[Dict[str, Any]]:
        """Check for recent compliance decline."""
        sorted_checkins = sorted(checkins, key=lambda c: c.date)

        if len(sorted_checkins) < 7:
            return None

        recent = sorted_checkins[-3:]
        previous = sorted_checkins[-7:-3]

        recent_avg = sum(c.compliance_score for c in recent) / len(recent)
        prev_avg = sum(c.compliance_score for c in previous) / len(previous)

        decline = prev_avg - recent_avg
        if decline > 15:
            return {
                "metric": "general",
                "risk": "momentum_loss",
                "probability": min(0.9, 0.5 + decline / 100),
                "reason": f"Compliance dropped {decline:.0f}% over the last week",
            }

        return None

    def _suggest_preventive_actions(self, risks: List[Dict[str, Any]]) -> List[str]:
        """Suggest actions to prevent predicted failures."""
        actions = []
        seen = set()

        for risk in risks:
            metric = risk.get("metric", "")
            risk_type = risk.get("risk", "")

            if metric == "sleep" and risk_type == "dow_risk":
                action = "Set a bedtime alarm for tonight"
            elif metric == "training" and risk_type == "dow_risk":
                action = "Lay out workout clothes before bed"
            elif metric == "deep_work" and risk_type == "dow_risk":
                action = "Block 2 hours on your calendar for tomorrow morning"
            elif risk_type == "streak_fatigue":
                action = "Plan one fun activity for tomorrow as a reward"
            elif risk_type == "momentum_loss":
                action = "Do a 5-minute review of your constitution tonight"
            else:
                action = f"Focus on protecting your {metric} tomorrow"

            if action not in seen:
                seen.add(action)
                actions.append(action)

        return actions

    def format_prediction(self, prediction: Dict[str, Any], user: User) -> str:
        """Format prediction into a user-friendly message."""
        risks = prediction.get("risks", [])
        actions = prediction.get("preventive_actions", [])
        risk_score = prediction.get("risk_score", 0.0)

        if not risks:
            return (
                f"🔮 <b>Tomorrow's Forecast</b>\n\n"
                f"No elevated risks detected. You're on track! 🎯"
            )

        lines = [
            f"🔮 <b>Tomorrow's Risk Forecast</b>",
            f"",
            f"Based on your patterns, tomorrow has elevated risk:",
        ]

        for risk in risks:
            metric = risk.get("metric", "general")
            prob = risk.get("probability", 0.0)
            reason = risk.get("reason", "")
            emoji = "🟡" if prob < 0.6 else "🟠" if prob < 0.8 else "🔴"
            lines.append(f"{emoji} {metric.capitalize()}: {prob:.0%} risk — {reason}")

        if actions:
            lines.extend(["", "<b>Preventive Actions:</b>"])
            for i, action in enumerate(actions, 1):
                lines.append(f"{i}. {action}")

        if user.streaks.current_streak > 7:
            lines.extend([
                "",
                f"You've got this. Your {user.streaks.current_streak}-day streak is worth protecting. 🔥"
            ])

        return "\n".join(lines)


# Singleton instance
predictive_intervention_engine = PredictiveInterventionEngine()
