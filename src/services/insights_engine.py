"""
Insights Engine
===============

Generates personalized insights from check-in history.

Theory: Pattern Visibility
----------------------------
Users don't know their own patterns. The insights engine surfaces
actionable patterns: "Your Tuesdays are strongest", "Sleep <6h → next
day mood averages 4.2". This makes invisible patterns visible.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from collections import defaultdict

from src.models.schemas import DailyCheckIn, User
from src.services.analytics_service import calculate_mood_correlations

logger = logging.getLogger(__name__)


class InsightsEngine:
    """Generate personalized insights from check-in history."""

    def generate_insights(
        self,
        checkins: List[DailyCheckIn],
        user: Optional[User] = None,
    ) -> List[Dict[str, Any]]:
        """
        Generate 3-5 insights from check-in history.

        Insight types:
        1. Day-of-week patterns
        2. Sleep → performance correlation
        3. Mood/energy trends
        4. Risk windows
        """
        if len(checkins) < 7:
            return []

        insights = []

        # Day-of-week analysis (needs 14+ days for meaningful patterns)
        if len(checkins) >= 14:
            dow_insight = self._analyze_dow_patterns(checkins)
            if dow_insight:
                insights.append(dow_insight)

        # Sleep → performance correlation
        sleep_insight = self._analyze_sleep_performance_correlation(checkins)
        if sleep_insight:
            insights.append(sleep_insight)

        # Mood/energy insights (needs 5+ check-ins with mood data)
        mood_insight = self._analyze_mood_energy_patterns(checkins)
        if mood_insight:
            insights.append(mood_insight)

        # Risk window detection
        risk_insight = self._detect_risk_windows(checkins)
        if risk_insight:
            insights.append(risk_insight)

        return insights

    def _analyze_dow_patterns(
        self,
        checkins: List[DailyCheckIn]
    ) -> Optional[Dict[str, Any]]:
        """Find day-of-week patterns in compliance."""
        dow_scores = defaultdict(list)
        for c in checkins:
            dow = datetime.strptime(c.date, "%Y-%m-%d").strftime("%A")
            dow_scores[dow].append(c.compliance_score)

        # Only include days with at least 3 data points
        avgs = {
            dow: sum(scores) / len(scores)
            for dow, scores in dow_scores.items()
            if len(scores) >= 3
        }

        if len(avgs) < 3:
            return None

        best = max(avgs, key=avgs.get)
        worst = min(avgs, key=avgs.get)
        spread = avgs[best] - avgs[worst]

        # Only report if spread is meaningful (>10%)
        if spread < 10:
            return None

        return {
            "type": "day_of_week",
            "title": f"Your {best}s are strongest ({avgs[best]:.0f}%), {worst}s are toughest ({avgs[worst]:.0f}%)",
            "suggestion": f"Plan harder tasks for {best}s. Be extra vigilant on {worst}s.",
            "data": {"best_day": best, "worst_day": worst, "spread": spread},
        }

    def _analyze_sleep_performance_correlation(
        self,
        checkins: List[DailyCheckIn]
    ) -> Optional[Dict[str, Any]]:
        """Analyze how sleep hours affect next-day performance."""
        # Pair each day's sleep with next day's compliance
        checkins_by_date = {c.date: c for c in checkins}

        pairs = []
        for c in checkins:
            next_date = (
                datetime.strptime(c.date, "%Y-%m-%d") + __import__('datetime').timedelta(days=1)
            ).strftime("%Y-%m-%d")
            if next_date in checkins_by_date:
                sleep_hrs = c.tier1_non_negotiables.sleep_hours
                if sleep_hrs is not None:
                    pairs.append((sleep_hrs, checkins_by_date[next_date].compliance_score))

        if len(pairs) < 5:
            return None

        # Categorize sleep quality
        good_sleep = [comp for sleep, comp in pairs if sleep >= 7.0]
        bad_sleep = [comp for sleep, comp in pairs if sleep < 6.0]

        if not good_sleep or not bad_sleep:
            return None

        avg_good = sum(good_sleep) / len(good_sleep)
        avg_bad = sum(bad_sleep) / len(bad_sleep)
        diff = avg_good - avg_bad

        if diff < 10:
            return None

        return {
            "type": "sleep_performance",
            "title": f"Sleep 7h+ → next day averages {avg_good:.0f}% compliance",
            "suggestion": f"Sleep <6h drops next-day performance to {avg_bad:.0f}%. Protect your sleep.",
            "data": {"good_sleep_avg": avg_good, "bad_sleep_avg": avg_bad, "diff": diff},
        }

    def _analyze_mood_energy_patterns(
        self,
        checkins: List[DailyCheckIn]
    ) -> Optional[Dict[str, Any]]:
        """Analyze mood/energy trends and correlations."""
        valid = [
            c for c in checkins
            if c.responses.energy_rating is not None
            and c.responses.mood_rating is not None
        ]

        if len(valid) < 5:
            return None

        correlations = calculate_mood_correlations(checkins)
        if not correlations.get("has_data"):
            return None

        # Find the strongest correlation
        corr_keys = [
            "sleep_mood_correlation",
            "sleep_energy_correlation",
            "training_energy_correlation",
            "deep_work_mood_correlation",
        ]
        best_corr = None
        best_value = 0.0
        for key in corr_keys:
            val = correlations.get(key)
            if val is not None and abs(val) > abs(best_value):
                best_corr = key
                best_value = val

        if not best_corr or abs(best_value) < 0.3:
            return None

        labels = {
            "sleep_mood_correlation": ("sleep", "mood"),
            "sleep_energy_correlation": ("sleep", "energy"),
            "training_energy_correlation": ("training", "energy"),
            "deep_work_mood_correlation": ("deep work", "mood"),
        }
        habit, metric = labels.get(best_corr, ("habit", "metric"))

        direction = "positively" if best_value > 0 else "negatively"
        strength = "strongly" if abs(best_value) > 0.6 else "moderately"

        return {
            "type": "mood_correlation",
            "title": f"{habit.capitalize()} {strength} correlates with {metric} (r={best_value:.2f})",
            "suggestion": f"Focus on {habit} — it has the biggest impact on your {metric}.",
            "data": {"correlation": best_value, "habit": habit, "metric": metric},
        }

    def _detect_risk_windows(
        self,
        checkins: List[DailyCheckIn]
    ) -> Optional[Dict[str, Any]]:
        """Detect high-risk periods based on recent decline."""
        if len(checkins) < 7:
            return None

        sorted_checkins = sorted(checkins, key=lambda c: c.date)
        recent = sorted_checkins[-7:]
        previous = sorted_checkins[-14:-7] if len(sorted_checkins) >= 14 else []

        recent_avg = sum(c.compliance_score for c in recent) / len(recent)

        if previous:
            prev_avg = sum(c.compliance_score for c in previous) / len(previous)
            decline = prev_avg - recent_avg

            if decline > 15:
                return {
                    "type": "risk_window",
                    "title": f"⚠️ Compliance dropped {decline:.0f}% over the last week",
                    "suggestion": "Your momentum is slipping. Review your tomorrow priorities and protect one Tier 1 item.",
                    "data": {"decline": decline, "recent_avg": recent_avg, "previous_avg": prev_avg},
                }

        # Check for streak fatigue: low compliance on day 6+ of week
        # (simplified: just check if recent compliance is below 60%)
        if recent_avg < 60:
            return {
                "type": "risk_window",
                "title": f"⚠️ Recent compliance is {recent_avg:.0f}% — below 60% threshold",
                "suggestion": "You're in a rough patch. Consider using a streak shield or reaching out to your partner.",
                "data": {"recent_avg": recent_avg},
            }

        return None


# Singleton instance
insights_engine = InsightsEngine()
