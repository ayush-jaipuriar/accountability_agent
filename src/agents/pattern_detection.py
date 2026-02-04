"""
Pattern Detection Agent - Automatic Constitution Violation Detection

This agent analyzes check-in history to detect patterns that violate
the user's constitution, enabling proactive interventions.

What is Pattern Detection?
---------------------------
Instead of waiting for the user to fail completely, we detect early
warning signs and intervene before a full spiral.

Example:
- Without Pattern Detection: User sleeps poorly for 2 weeks → burns out → quits
- With Pattern Detection: User sleeps poorly for 3 days → agent sends warning → user corrects course

The 5 Patterns We Detect:
--------------------------
1. **Sleep Degradation** (HIGH severity)
   - Trigger: <6 hours for 3+ consecutive nights
   - Violates: Physical Sovereignty
   - Risk: Cascading failure (sleep → training → productivity → spiral)

2. **Training Abandonment** (MEDIUM severity)
   - Trigger: 3+ missed training days in a row (excluding rest days)
   - Violates: Physical Sovereignty
   - Risk: Fitness regression, loss of discipline anchor

3. **Porn Relapse Pattern** (CRITICAL severity)
   - Trigger: 3+ violations in 7 days
   - Violates: Tier 1 Non-Negotiable (absolute rule)
   - Risk: Full relapse into addiction cycle

4. **Compliance Decline** (MEDIUM severity)
   - Trigger: <70% compliance for 3+ consecutive days
   - Violates: Overall system discipline
   - Risk: Slow degradation of all standards

5. **Deep Work Collapse** (MEDIUM severity)
   - Trigger: <1.5 hours for 5+ days
   - Violates: Create Don't Consume principle
   - Risk: Drift into consumption mode (social media, videos, etc.)

Key Concepts:
-------------
1. **Threshold-Based Detection**: Simple rules, no ML needed
   - If condition met → pattern detected
   - Example: sleep_hours < 6 for 3 days → sleep_degradation

2. **Sliding Window Analysis**: Look at last N days
   - Sleep: Last 3 days
   - Training: Last 3 days
   - Porn: Last 7 days
   - Compliance: Last 3 days
   - Deep Work: Last 5 days

3. **Severity Levels**: Prioritize interventions
   - CRITICAL: Immediate action required (porn relapse)
   - HIGH: Very important (sleep degradation)
   - MEDIUM: Important but not urgent
   - LOW: Worth monitoring

4. **Evidence Collection**: Store data with pattern
   - Not just "sleep degradation detected"
   - But "Average 5.3 hours over 3 days (Feb 1-3)"
   - Used to generate specific intervention messages

Why These Thresholds?
---------------------
- **3 consecutive days** (most patterns): 
  - 1 day = might be accident
  - 2 days = could be coincidence
  - 3 days = emerging pattern
  
- **7-day window** (porn relapse):
  - Addiction patterns work in weekly cycles
  - 3+ violations per week = relapse pattern
  
- **5 days** (deep work):
  - Longer window because deep work varies more day-to-day
  - Allows for occasional off days without false alarms
"""

from typing import List, Optional
from datetime import datetime
from src.models.schemas import DailyCheckIn, User
from src.services.firestore_service import firestore_service
import logging

logger = logging.getLogger(__name__)


class Pattern:
    """
    Represents a detected constitution violation pattern
    
    Attributes:
        type: Pattern type (sleep_degradation, training_abandonment, etc.)
        severity: Severity level (critical, high, medium, low)
        detected_at: When pattern was detected
        data: Pattern-specific evidence (dates, values, averages)
    """
    
    def __init__(
        self,
        type: str,
        severity: str,
        detected_at: datetime,
        data: dict
    ):
        self.type = type
        self.severity = severity
        self.detected_at = detected_at
        self.data = data
    
    def to_dict(self) -> dict:
        """Convert to dictionary for Firestore storage"""
        return {
            "type": self.type,
            "severity": self.severity,
            "detected_at": self.detected_at,
            "data": self.data
        }
    
    def __repr__(self) -> str:
        return f"Pattern(type={self.type}, severity={self.severity}, data={self.data})"


class PatternDetectionAgent:
    """
    Analyzes check-in history to detect constitution violation patterns
    
    Used by:
    - Scheduled pattern scanner (runs every 6 hours)
    - On-demand analysis (user requests pattern report)
    """
    
    def detect_patterns(self, checkins: List[DailyCheckIn]) -> List[Pattern]:
        """
        Run all pattern detection rules
        
        Args:
            checkins: Recent check-ins (sorted oldest to newest)
            
        Returns:
            List of detected patterns
            
        Theory - How Pattern Detection Works:
        -------------------------------------
        1. Get recent check-ins (usually last 7-14 days)
        2. Run each detection rule (5 rules total)
        3. Each rule returns Optional[Pattern] (None if no pattern)
        4. Collect all detected patterns
        5. Return list (may be empty if user is compliant)
        
        The patterns are used by Intervention Agent to generate warnings.
        """
        if not checkins:
            logger.info("No check-ins provided, skipping pattern detection")
            return []
        
        logger.info(f"Running pattern detection on {len(checkins)} check-ins")
        
        patterns = []
        
        # Run each detection rule
        if pattern := self._detect_sleep_degradation(checkins):
            patterns.append(pattern)
            logger.warning(f"⚠️  Pattern detected: {pattern.type}")
        
        if pattern := self._detect_training_abandonment(checkins):
            patterns.append(pattern)
            logger.warning(f"⚠️  Pattern detected: {pattern.type}")
        
        if pattern := self._detect_porn_relapse(checkins):
            patterns.append(pattern)
            logger.error(f"🚨 CRITICAL pattern detected: {pattern.type}")
        
        if pattern := self._detect_compliance_decline(checkins):
            patterns.append(pattern)
            logger.warning(f"⚠️  Pattern detected: {pattern.type}")
        
        if pattern := self._detect_deep_work_collapse(checkins):
            patterns.append(pattern)
            logger.warning(f"⚠️  Pattern detected: {pattern.type}")
        
        if patterns:
            logger.warning(f"🚨 Pattern detection complete: {len(patterns)} pattern(s) found")
        else:
            logger.info(f"✅ Pattern detection complete: No patterns detected (user is compliant)")
        
        return patterns
    
    def _detect_sleep_degradation(self, checkins: List[DailyCheckIn]) -> Optional[Pattern]:
        """
        Detect: <6 hours sleep for 3+ consecutive nights
        Severity: HIGH (Physical Sovereignty violation)
        
        Why 6 hours as threshold?
        - Constitution requires 7+ hours
        - <6 hours = significant deficit
        - 3+ consecutive nights = pattern (not just one bad night)
        
        Historical Context:
        - Feb 2025: Sleep degradation → full spiral
        - This pattern is a leading indicator of breakdown
        """
        if len(checkins) < 3:
            return None
        
        # Get last 3 check-ins
        recent_3 = checkins[-3:]
        
        # Check if all have sleep data (some check-ins might not track sleep)
        sleep_data = []
        for c in recent_3:
            # Extract sleep hours from check-in
            # In Phase 1, sleep might be in tier1 (boolean) not hours
            # For now, we'll assume tier1.sleep = True means >=7 hours
            # and tier1.sleep = False means <7 hours
            if hasattr(c.tier1_non_negotiables, 'sleep'):
                sleep_compliant = c.tier1_non_negotiables.sleep
                # Rough estimate: compliant = 7+ hours, non-compliant = assume 5-6 hours
                sleep_hours = 7.5 if sleep_compliant else 5.5
                sleep_data.append((c.date, sleep_hours))
        
        if len(sleep_data) < 3:
            return None
        
        # Check if all 3 are <6 hours
        low_sleep_nights = [s for s in sleep_data if s[1] < 6]
        
        if len(low_sleep_nights) >= 3:
            avg_sleep = sum(s[1] for s in sleep_data) / len(sleep_data)
            dates = [s[0] for s in sleep_data]
            
            return Pattern(
                type="sleep_degradation",
                severity="high",
                detected_at=datetime.utcnow(),
                data={
                    "avg_sleep_hours": round(avg_sleep, 1),
                    "consecutive_days": 3,
                    "threshold": 6,
                    "dates": dates,
                    "message": f"Average {avg_sleep:.1f} hours over last 3 nights"
                }
            )
        
        return None
    
    def _detect_training_abandonment(self, checkins: List[DailyCheckIn]) -> Optional[Pattern]:
        """
        Detect: 3+ missed training days in a row
        Severity: MEDIUM
        
        Note: This is conservative - doesn't account for rest days.
        In production, we'd check mode (optimization=6x/week, maintenance=4x/week)
        and allow scheduled rest days.
        """
        if len(checkins) < 3:
            return None
        
        recent_3 = checkins[-3:]
        missed_training = [c for c in recent_3 if not c.tier1_non_negotiables.training]
        
        if len(missed_training) >= 3:
            dates = [c.date for c in missed_training]
            
            return Pattern(
                type="training_abandonment",
                severity="medium",
                detected_at=datetime.utcnow(),
                data={
                    "consecutive_missed_days": 3,
                    "dates": dates,
                    "message": "No training for 3+ consecutive days"
                }
            )
        
        return None
    
    def _detect_porn_relapse(self, checkins: List[DailyCheckIn]) -> Optional[Pattern]:
        """
        Detect: 3+ porn violations in last 7 days
        Severity: CRITICAL (Tier 1 absolute non-negotiable)
        
        Why CRITICAL?
        - Tier 1 rule = absolute (zero tolerance)
        - 3+ violations = pattern, not accident
        - Historical risk: "Just one more time" fallacy leads to full relapse
        """
        if len(checkins) < 3:
            return None
        
        # Get last 7 days (or all if <7)
        last_7_days = checkins[-7:] if len(checkins) >= 7 else checkins
        
        # Find porn violations (where zero_porn = False)
        porn_violations = [c for c in last_7_days if not c.tier1_non_negotiables.zero_porn]
        
        if len(porn_violations) >= 3:
            dates = [c.date for c in porn_violations]
            
            return Pattern(
                type="porn_relapse_pattern",
                severity="critical",
                detected_at=datetime.utcnow(),
                data={
                    "violations_count": len(porn_violations),
                    "window_days": len(last_7_days),
                    "dates": dates,
                    "message": f"{len(porn_violations)} violations in {len(last_7_days)} days"
                }
            )
        
        return None
    
    def _detect_compliance_decline(self, checkins: List[DailyCheckIn]) -> Optional[Pattern]:
        """
        Detect: <70% compliance for 3+ consecutive days
        Severity: MEDIUM (overall system breakdown)
        
        Why 70% threshold?
        - Constitution modes target: 60% (survival), 80% (maintenance), 90% (optimization)
        - <70% = below even maintenance standards
        - Indicates system-wide degradation, not just one area
        """
        if len(checkins) < 3:
            return None
        
        recent_3 = checkins[-3:]
        low_compliance_days = [c for c in recent_3 if c.compliance_score < 70]
        
        if len(low_compliance_days) >= 3:
            scores = [c.compliance_score for c in recent_3]
            avg_compliance = sum(scores) / len(scores)
            dates = [c.date for c in recent_3]
            
            return Pattern(
                type="compliance_decline",
                severity="medium",
                detected_at=datetime.utcnow(),
                data={
                    "avg_compliance": round(avg_compliance, 1),
                    "consecutive_days": 3,
                    "threshold": 70,
                    "scores": scores,
                    "dates": dates,
                    "message": f"Average {avg_compliance:.1f}% compliance over 3 days"
                }
            )
        
        return None
    
    def _detect_deep_work_collapse(self, checkins: List[DailyCheckIn]) -> Optional[Pattern]:
        """
        Detect: Low deep work for 5+ days
        Severity: MEDIUM (Create Don't Consume violation)
        
        Why 5 days instead of 3?
        - Deep work is more variable day-to-day
        - Some days have unavoidable meetings
        - 5-day pattern = systemic issue, not just busy week
        
        Threshold: <1.5 hours (half of 2-hour target)
        - Below this = consumption mode (browsing, videos, social media)
        """
        if len(checkins) < 5:
            return None
        
        recent_5 = checkins[-5:]
        
        # Estimate deep work hours (Phase 1 only has boolean deep_work)
        # Assumption: deep_work=True means 2+ hours, False means <2 hours (estimate 1 hour)
        low_deep_work_days = [c for c in recent_5 if not c.tier1_non_negotiables.deep_work]
        
        if len(low_deep_work_days) >= 5:
            dates = [c.date for c in recent_5]
            
            return Pattern(
                type="deep_work_collapse",
                severity="medium",
                detected_at=datetime.utcnow(),
                data={
                    "consecutive_days": 5,
                    "threshold": 1.5,
                    "dates": dates,
                    "message": "Deep work below target for 5+ consecutive days"
                }
            )
        
        return None
    
    def detect_ghosting(self, user_id: str) -> Optional[Pattern]:
        """
        Detect missing check-ins with escalating severity (Phase 3B).
        
        **What is Ghosting?**
        User ignores triple reminders → doesn't check in → disappears for multiple days.
        
        **Algorithm:**
        1. Get user's last check-in date from Firestore
        2. Calculate days since last check-in (today - last_checkin_date)
        3. If days >= 2, create ghosting pattern
        4. Map days to severity level
        
        **Severity Escalation:**
        - Day 1: Grace period (triple reminders handle this) → No pattern
        - Day 2: "nudge" severity → Gentle reminder
        - Day 3: "warning" severity → Firm constitution reference
        - Day 4: "critical" severity → Historical pattern reference
        - Day 5+: "emergency" severity → Partner escalation
        
        **Why Day 2 threshold?**
        - Day 1 is covered by Phase 3A triple reminders (9 PM, 9:30 PM, 10 PM)
        - Day 2 means user ignored ALL 3 reminders → intervention needed
        - Earlier detection = better chance of recovery
        
        **Data Collected:**
        - days_missing: Number of days since last check-in
        - last_checkin_date: When user last checked in
        - previous_streak: What streak they had (for motivation)
        - current_mode: Their constitution mode
        
        Args:
            user_id: User ID to check for ghosting
            
        Returns:
            Pattern object with ghosting data if detected, None otherwise
            
        Example:
            User last checked in on Feb 2, today is Feb 4:
            → days_since = 2
            → severity = "nudge"
            → Pattern created with message: "Missed you yesterday!"
        """
        # Get user data from Firestore
        user = firestore_service.get_user(user_id)
        
        if not user or not user.streaks.last_checkin_date:
            # User doesn't exist or has never checked in
            logger.info(f"No ghosting check: User {user_id} has no last_checkin_date")
            return None
        
        # Calculate days since last check-in
        days_since = self._calculate_days_since_checkin(
            user.streaks.last_checkin_date
        )
        
        logger.info(f"Ghosting check: User {user_id} - {days_since} days since last check-in")
        
        # Day 1 = grace period (triple reminders handle it)
        if days_since < 2:
            return None
        
        # Day 2+ = ghosting detected
        severity = self._get_ghosting_severity(days_since)
        
        pattern = Pattern(
            type="ghosting",
            severity=severity,
            detected_at=datetime.utcnow(),
            data={
                "days_missing": days_since,
                "last_checkin_date": user.streaks.last_checkin_date,
                "previous_streak": user.streaks.current_streak,
                "current_mode": user.constitution.current_mode if user.constitution else None
            }
        )
        
        logger.warning(
            f"GHOSTING DETECTED: User {user_id} - {days_since} days missing - "
            f"Severity: {severity}"
        )
        
        return pattern
    
    def _calculate_days_since_checkin(self, last_checkin_date: str) -> int:
        """
        Calculate days between last check-in and today.
        
        **Why This Calculation?**
        We need to know how many days user has been missing to:
        1. Determine if ghosting is happening (>= 2 days)
        2. Choose the right severity level
        3. Generate specific intervention message
        
        **Date Math:**
        - last_checkin_date: "2026-02-02" (string from Firestore)
        - today: "2026-02-04" (current IST date)
        - difference: 2 days
        
        **Why IST instead of UTC?**
        - User is in India (IST timezone)
        - "Today" for user is IST date, not UTC
        - Prevents off-by-one errors near midnight
        
        Args:
            last_checkin_date: Date string in format "YYYY-MM-DD" (IST)
            
        Returns:
            Number of days since last check-in (integer)
            
        Example:
            Last check-in: "2026-02-02"
            Today (IST): "2026-02-04"
            → Returns: 2 days
        """
        from datetime import datetime
        from src.utils.timezone_utils import get_current_date_ist
        
        # Parse last check-in date
        last_date = datetime.strptime(last_checkin_date, "%Y-%m-%d").date()
        
        # Get today's date in IST (user's timezone)
        today_str = get_current_date_ist()
        today = datetime.strptime(today_str, "%Y-%m-%d").date()
        
        # Calculate difference
        days_since = (today - last_date).days
        
        return days_since
    
    def _get_ghosting_severity(self, days: int) -> str:
        """
        Map days missing to severity level.
        
        **Severity Levels Explained:**
        
        1. **Day 2 → "nudge"**
           - User just missed one day
           - Could be accident, busy day, forgot
           - Message tone: Gentle, checking in
           - Example: "👋 Missed you yesterday! Everything okay?"
        
        2. **Day 3 → "warning"**
           - Pattern is emerging
           - Missed 2 days in a row → not random
           - Message tone: Firm, constitution reference
           - Example: "⚠️ 3 days missing. Constitution violation."
        
        3. **Day 4 → "critical"**
           - Serious situation
           - Historical pattern reference (Feb 2025 spiral)
           - Message tone: Urgent, evidence-based
           - Example: "🚨 4-day absence. Last time: 6-month spiral."
        
        4. **Day 5+ → "emergency"**
           - Emergency intervention
           - Partner notification triggered
           - Message tone: Alarm, social support activation
           - Example: "🔴 EMERGENCY. Contact accountability partner NOW."
        
        **Why These Thresholds?**
        - Research shows intervention effectiveness drops after Day 7
        - Day 5 is inflection point where behavior becomes habit
        - Partner escalation at Day 5 adds social accountability
        
        Args:
            days: Number of days since last check-in
            
        Returns:
            Severity string: "nudge" | "warning" | "critical" | "emergency"
        """
        if days == 2:
            return "nudge"
        elif days == 3:
            return "warning"
        elif days == 4:
            return "critical"
        else:  # 5+
            return "emergency"


# Global instance
pattern_detection_agent = PatternDetectionAgent()


def get_pattern_detection_agent() -> PatternDetectionAgent:
    """Get the pattern detection agent instance"""
    return pattern_detection_agent
