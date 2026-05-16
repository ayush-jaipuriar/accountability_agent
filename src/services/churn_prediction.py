"""
Churn Risk Prediction Service
==============================

Predicts user churn risk based on behavioral signals.

Risk factors:
- Check-in time drift (procrastination signal)
- Compliance decline (3-week trend)
- Quick check-in overuse (avoiding depth)
- Self-rating decline (disengagement signal)
- Missed reminders (ignoring system)

Theory: Behavioral Prediction
-------------------------------
Churn is not random — it follows predictable behavioral patterns.
By measuring signals that precede disengagement, we can intervene
before the user ghosts completely.

Design Principles:
- Risk scores are INTERNAL-ONLY (never shown to users)
- Multiple weak signals combine into a strong prediction
- Cooldown prevents spam (max 1 intervention per 3 days)
- Interventions are soft nudges, not warnings
"""

import logging
from datetime import datetime, timedelta
from statistics import mean
from typing import Tuple, List, Dict, Optional

from src.models.schemas import User, DailyCheckIn
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


class ChurnRiskPredictor:
    """Predict user churn risk from behavioral signals."""
    
    # Risk factor weights (must sum to 1.0)
    FACTORS = {
        "checkin_time_drift": {"weight": 0.25, "threshold_minutes": 45},
        "compliance_decline": {"weight": 0.30, "threshold_points": 15},
        "quick_checkin_overuse": {"weight": 0.20, "threshold_days": 5},
        "self_rating_decline": {"weight": 0.15, "threshold_points": 2},
        "missed_checkins": {"weight": 0.10, "threshold_days": 2},
    }
    
    def calculate_risk_score(self, user: User) -> Tuple[float, List[str], Dict]:
        """
        Calculate churn risk score (0.0 to 1.0).
        
        Returns:
            (risk_score, triggered_factors, raw_data)
        """
        score = 0.0
        factors = []
        raw_data = {}
        
        # Get recent data (21 days = 3 weeks)
        checkins = firestore_service.get_recent_checkins(user.user_id, days=21)
        
        if len(checkins) < 7:
            return 0.0, [], {"insufficient_data": True, "checkins_found": len(checkins)}
        
        # Sort by date ascending
        checkins = sorted(checkins, key=lambda c: c.date)
        
        # Factor 1: Check-in time drift
        drift = self._calculate_time_drift(checkins)
        raw_data["time_drift_minutes"] = drift
        if drift > self.FACTORS["checkin_time_drift"]["threshold_minutes"]:
            score += self.FACTORS["checkin_time_drift"]["weight"]
            factors.append("checkin_time_drift")
        
        # Factor 2: Compliance decline
        decline = self._calculate_compliance_decline(checkins)
        raw_data["compliance_decline"] = decline
        if decline > self.FACTORS["compliance_decline"]["threshold_points"]:
            score += self.FACTORS["compliance_decline"]["weight"]
            factors.append("compliance_decline")
        
        # Factor 3: Quick check-in overuse
        qc_overuse = self._calculate_quick_checkin_overuse(checkins)
        raw_data["quick_checkin_overuse_days"] = qc_overuse
        if qc_overuse >= self.FACTORS["quick_checkin_overuse"]["threshold_days"]:
            score += self.FACTORS["quick_checkin_overuse"]["weight"]
            factors.append("quick_checkin_overuse")
        
        # Factor 4: Self-rating decline
        rating_decline = self._calculate_rating_decline(checkins)
        raw_data["rating_decline"] = rating_decline
        if rating_decline > self.FACTORS["self_rating_decline"]["threshold_points"]:
            score += self.FACTORS["self_rating_decline"]["weight"]
            factors.append("self_rating_decline")
        
        # Factor 5: Missed check-ins (gaps in the streak)
        missed = self._calculate_missed_checkins(checkins)
        raw_data["missed_checkins"] = missed
        if missed >= self.FACTORS["missed_checkins"]["threshold_days"]:
            score += self.FACTORS["missed_checkins"]["weight"]
            factors.append("missed_checkins")
        
        final_score = min(score, 1.0)
        raw_data["final_score"] = final_score
        raw_data["triggered_count"] = len(factors)
        
        return final_score, factors, raw_data
    
    def _calculate_time_drift(self, checkins: List[DailyCheckIn]) -> float:
        """Calculate how much later check-ins are happening (in minutes)."""
        if len(checkins) < 10:
            return 0.0
        
        # Compare first 7 days vs last 3 days
        early_times = [c.completed_at for c in checkins[:7] if c.completed_at]
        recent_times = [c.completed_at for c in checkins[-3:] if c.completed_at]
        
        if not early_times or not recent_times:
            return 0.0
        
        try:
            early_avg = mean([t.hour * 60 + t.minute for t in early_times])
            recent_avg = mean([t.hour * 60 + t.minute for t in recent_times])
            return recent_avg - early_avg
        except (AttributeError, TypeError):
            return 0.0
    
    def _calculate_compliance_decline(self, checkins: List[DailyCheckIn]) -> float:
        """Calculate compliance drop over last 3 weeks."""
        if len(checkins) < 14:
            return 0.0
        
        mid = len(checkins) // 2
        week1 = mean([c.compliance_score for c in checkins[:mid]])
        week3 = mean([c.compliance_score for c in checkins[mid:]])
        
        return max(0, week1 - week3)
    
    def _calculate_quick_checkin_overuse(self, checkins: List[DailyCheckIn]) -> int:
        """Count consecutive quick check-ins at the end."""
        consecutive = 0
        for c in reversed(checkins):
            if getattr(c, 'is_quick_checkin', False):
                consecutive += 1
            else:
                break
        return consecutive
    
    def _calculate_rating_decline(self, checkins: List[DailyCheckIn]) -> float:
        """Calculate self-rating drop."""
        if len(checkins) < 10:
            return 0.0
        
        mid = len(checkins) // 2
        early_ratings = [
            c.responses.rating for c in checkins[:mid]
            if getattr(c, 'responses', None) and c.responses.rating is not None
        ]
        recent_ratings = [
            c.responses.rating for c in checkins[mid:]
            if getattr(c, 'responses', None) and c.responses.rating is not None
        ]
        
        if not early_ratings or not recent_ratings:
            return 0.0
        
        return max(0, mean(early_ratings) - mean(recent_ratings))
    
    def _calculate_missed_checkins(self, checkins: List[DailyCheckIn]) -> int:
        """Count missed days in the last 7 days."""
        if len(checkins) < 7:
            return 0
        
        # Check for date gaps in the last 7 check-ins
        from datetime import datetime as dt
        missed = 0
        for i in range(1, min(8, len(checkins))):
            try:
                prev_date = dt.strptime(checkins[-i].date, "%Y-%m-%d")
                curr_date = dt.strptime(checkins[-(i+1)].date, "%Y-%m-%d")
                gap = (prev_date - curr_date).days - 1
                if gap > 0:
                    missed += gap
            except (ValueError, IndexError):
                continue
        return min(missed, 7)  # Cap at 7
    
    def is_intervention_cooled_down(self, user: User, cooldown_days: int = 3) -> bool:
        """
        Check if enough time has passed since last intervention.
        
        Args:
            user: User object
            cooldown_days: Minimum days between interventions
        
        Returns:
            True if intervention is allowed, False if in cooldown
        """
        if user.last_churn_intervention is None:
            return True
        
        days_since = (datetime.utcnow() - user.last_churn_intervention).days
        return days_since >= cooldown_days


# Singleton instance
churn_predictor = ChurnRiskPredictor()
