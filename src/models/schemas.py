"""
Data Models & Schemas
=====================

This module defines the structure of all data in the system using Pydantic.

Why Pydantic?
- Type Safety: Python enforces types automatically
- Validation: Data is validated before storing in database
- Serialization: Easy conversion to/from JSON and Firestore
- Documentation: Models serve as living documentation

Key Concepts:
- BaseModel: Pydantic's base class for data models
- Optional: Field can be None (e.g., user hasn't done deep work yet)
- datetime: Python's date/time type
- Field: Add validation rules (e.g., min/max values)
"""

from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List, Dict


# ===== User Models =====

class ReminderTimes(BaseModel):
    """
    Configurable reminder times for daily check-ins.
    
    Phase 3A: Triple reminder system
    - First: Friendly reminder (9:00 PM)
    - Second: Nudge (9:30 PM)
    - Third: Urgent reminder (10:00 PM)
    
    Future: Per-user customizable times
    """
    first: str = "21:00"   # HH:MM format (9:00 PM)
    second: str = "21:30"  # HH:MM format (9:30 PM)
    third: str = "22:00"   # HH:MM format (10:00 PM)


class StreakShields(BaseModel):
    """
    Streak protection system (gamification feature).
    
    Concept:
    - Users get 3 shields per 30 days
    - Shields can be used to prevent streak break
    - Monthly reset encourages consistent check-ins
    
    Example: User on 47-day streak misses a day → can use shield to protect streak
    """
    total: int = 3                    # Max shields allowed
    used: int = 0                     # Shields used this period
    available: int = 3                # Remaining shields (total - used)
    earned_at: List[str] = Field(default_factory=list)  # Dates when shields were earned
    last_reset: Optional[str] = None  # Last monthly reset date (YYYY-MM-DD)


class UserStreaks(BaseModel):
    """
    Tracks user's streak information.
    
    Streak Rules (from constitution):
    - Increment: If check-in completed within 48 hours of last check-in
    - Reset: If gap exceeds 48 hours
    - Longest: Historical maximum streak (never decreases)
    """
    current_streak: int = Field(default=0, ge=0)  # Current consecutive days (>= 0)
    longest_streak: int = Field(default=0, ge=0)  # All-time best streak
    last_checkin_date: Optional[str] = None       # Last check-in date (YYYY-MM-DD format)
    total_checkins: int = Field(default=0, ge=0)  # Lifetime total check-ins
    # Phase D: Streak Recovery Tracking
    streak_before_reset: int = Field(default=0, ge=0)  # Streak value right before last reset
    last_reset_date: Optional[str] = None              # Date of last streak reset (YYYY-MM-DD)


class User(BaseModel):
    """
    User profile stored in Firestore users/ collection.
    
    Phase 1-2 Fields: Basic profile + streaks
    Phase 3 Fields: Multi-user support, reminders, gamification, accountability
    
    Example:
        user = User(
            user_id="123456789",
            telegram_id=123456789,
            name="Ayush",
            timezone="Asia/Kolkata",
            career_mode="skill_building"
        )
    """
    # ===== Core Profile (Phase 1-2) =====
    user_id: str                                  # Primary key (Telegram user ID as string)
    telegram_id: int                              # Telegram user ID (integer)
    telegram_username: Optional[str] = None       # @username (may be None)
    name: str                                     # Display name
    timezone: str = "Asia/Kolkata"                # User's timezone for check-in scheduling
    streaks: UserStreaks = Field(default_factory=UserStreaks)  # Nested streak data
    constitution_mode: str = "maintenance"        # Current mode: optimization/maintenance/survival
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    # ===== Phase 3A: Multi-User & Reminders =====
    reminder_times: ReminderTimes = Field(default_factory=ReminderTimes)  # Reminder configuration
    quick_checkin_count: int = Field(default=0, ge=0)  # Quick check-ins used this week (max 2)
    quick_checkin_used_dates: List[str] = Field(default_factory=list)  # Dates when quick check-ins were used
    quick_checkin_reset_date: str = ""  # Next Monday for weekly reset
    streak_shields: StreakShields = Field(default_factory=StreakShields)  # Streak protection
    
    # ===== Phase 3B: Emotional Support & Accountability =====
    accountability_partner_id: Optional[str] = None       # Linked user ID for accountability
    accountability_partner_name: Optional[str] = None     # Partner's display name
    
    # ===== Phase 3C: Gamification =====
    achievements: List[str] = Field(default_factory=list)  # Unlocked achievement IDs
    level: int = Field(default=1, ge=1)                    # User level (future: XP-based)
    xp: int = Field(default=0, ge=0)                       # Experience points (future)
    
    # ===== Phase 3D: Career Tracking =====
    career_mode: str = "skill_building"  # skill_building | job_searching | employed
    
    # ===== Phase 3F: Social Features =====
    leaderboard_opt_in: bool = True          # Whether user appears on leaderboard
    referred_by: Optional[str] = None        # User ID of the person who referred this user
    referral_code: Optional[str] = None      # Unique referral code for this user
    
    def to_firestore(self) -> dict:
        """
        Convert to Firestore-compatible dictionary.
        
        Firestore doesn't understand Pydantic models directly, so we convert
        to a plain Python dict. All nested Pydantic models are converted using model_dump().
        
        Phase 3 Note: Includes all new Phase 3 fields with backward compatibility
        """
        return {
            # Core profile
            "user_id": self.user_id,
            "telegram_id": self.telegram_id,
            "telegram_username": self.telegram_username,
            "name": self.name,
            "timezone": self.timezone,
            "streaks": self.streaks.model_dump(),  # Convert nested model to dict
            "constitution_mode": self.constitution_mode,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            
            # Phase 3A: Multi-user & Reminders
            "reminder_times": self.reminder_times.model_dump(),
            "quick_checkin_count": self.quick_checkin_count,
            "quick_checkin_used_dates": self.quick_checkin_used_dates,
            "quick_checkin_reset_date": self.quick_checkin_reset_date,
            "streak_shields": self.streak_shields.model_dump(),
            
            # Phase 3B: Accountability
            "accountability_partner_id": self.accountability_partner_id,
            "accountability_partner_name": self.accountability_partner_name,
            
            # Phase 3C: Gamification
            "achievements": self.achievements,
            "level": self.level,
            "xp": self.xp,
            
            # Phase 3D: Career
            "career_mode": self.career_mode,
            
            # Phase 3F: Social
            "leaderboard_opt_in": self.leaderboard_opt_in,
            "referred_by": self.referred_by,
            "referral_code": self.referral_code
        }
    
    @classmethod
    def from_firestore(cls, data: dict) -> "User":
        """
        Create User object from Firestore document.
        
        Backward Compatibility: All Phase 3 fields have defaults, so existing
        Phase 1-2 users will work without migration.
        
        Args:
            data: Dictionary from Firestore document.data()
            
        Returns:
            User object with validated data
        """
        # Convert nested dicts back to Pydantic models
        if "streaks" in data and isinstance(data["streaks"], dict):
            data["streaks"] = UserStreaks(**data["streaks"])
        
        # Phase 3A: Reminder times
        if "reminder_times" in data and isinstance(data["reminder_times"], dict):
            data["reminder_times"] = ReminderTimes(**data["reminder_times"])
        
        # Phase 3A: Streak shields
        if "streak_shields" in data and isinstance(data["streak_shields"], dict):
            data["streak_shields"] = StreakShields(**data["streak_shields"])
        
        return cls(**data)


# ===== Reminder Tracking Models (Phase 3A) =====

class ReminderStatus(BaseModel):
    """
    Tracks which reminders have been sent today.
    
    Used to prevent spam: Don't send reminder_second if user already checked in
    after reminder_first.
    
    Stored in Firestore: reminder_status/{user_id}/{date}
    """
    user_id: str
    date: str  # YYYY-MM-DD
    first_sent: bool = False
    second_sent: bool = False
    third_sent: bool = False
    first_sent_at: Optional[datetime] = None
    second_sent_at: Optional[datetime] = None
    third_sent_at: Optional[datetime] = None


class Achievement(BaseModel):
    """
    Achievement definition (global, not per-user).
    
    Stored in Firestore: achievements/{achievement_id}
    
    User unlocks are stored as list of IDs in User.achievements
    """
    achievement_id: str                 # Unique ID (e.g., "week_warrior")
    name: str                           # Display name (e.g., "Week Warrior")
    description: str                    # What it's for (e.g., "7-day streak")
    icon: str                           # Emoji (e.g., "🏅")
    criteria: Dict[str, int]            # Unlock criteria (e.g., {"streak": 7})
    rarity: str = "common"              # common | rare | epic | legendary


# ===== Check-In Models =====

class Tier1NonNegotiables(BaseModel):
    """
    Tier 1 non-negotiables from constitution.
    
    **Phase 3D Expansion: 5 items → 6 items**
    
    6 Core Habits (Boolean + Optional Details):
    1. Sleep: 7+ hours
    2. Training: Workout or scheduled rest day
    3. Deep Work: 2+ hours focused work
    4. Skill Building: 2+ hours career-focused learning (NEW in Phase 3D)
    5. Zero Porn: No consumption (absolute rule)
    6. Boundaries: No toxic interactions
    
    **Why Add Skill Building?**
    - Constitution Section III.B mandates daily skill building (LeetCode, system design)
    - June 2026 career goal (₹28-42 LPA) requires tracking
    - Different from general deep work (career-specific learning)
    - Question adapts to career mode (skill_building/job_searching/employed)
    
    **Backward Compatibility:**
    - skill_building has default value False
    - Old check-ins without this field will work (Pydantic sets default)
    - New check-ins require this field
    """
    sleep: bool                                   # Did you get 7+ hours?
    sleep_hours: Optional[float] = None           # Actual hours slept (e.g., 7.5)
    
    training: bool                                # Did you train?
    is_rest_day: bool = False                     # Was today a scheduled rest day?
    training_type: Optional[str] = None           # "workout", "rest", "skipped"
    
    deep_work: bool                               # Did you complete 2+ hours?
    deep_work_hours: Optional[float] = None       # Actual hours (e.g., 2.5)
    
    # Phase 3D: New field for career tracking
    skill_building: bool = False                  # Did you do career-focused learning?
    skill_building_hours: Optional[float] = None  # Actual hours (e.g., 2.5)
    skill_building_activity: Optional[str] = None # "LeetCode", "System Design", "Courses", etc.
    
    zero_porn: bool                               # Did you maintain zero porn?
    
    boundaries: bool                              # Did you maintain boundaries?


class CheckInResponses(BaseModel):
    """
    User's responses to check-in questions.
    
    Questions (Phase 1 - Hardcoded):
    1. Challenges: What challenges did you face today?
    2. Rating: Rate today 1-10 on constitution alignment
    3. Rating Reason: Why that score?
    4. Tomorrow Priority: What's tomorrow's #1 priority?
    5. Tomorrow Obstacle: What's the biggest potential obstacle?
    """
    challenges: str = Field(..., min_length=10, max_length=500)      # 10-500 chars
    rating: int = Field(..., ge=1, le=10)                            # 1-10 scale
    rating_reason: str = Field(..., min_length=10, max_length=500)   # Why that rating?
    tomorrow_priority: str = Field(..., min_length=10, max_length=500)
    tomorrow_obstacle: str = Field(..., min_length=10, max_length=500)


class DailyCheckIn(BaseModel):
    """
    Complete daily check-in record.
    
    Stored in Firestore: daily_checkins/{user_id}/checkins/{date}
    
    Example:
        checkin = DailyCheckIn(
            date="2026-01-30",
            user_id="123456789",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(...),
            responses=CheckInResponses(...),
            compliance_score=80.0,
            completed_at=datetime.utcnow(),
            duration_seconds=120
        )
    """
    date: str                                     # YYYY-MM-DD format
    user_id: str                                  # User who completed check-in
    mode: str                                     # User's constitution mode at time of check-in
    
    tier1_non_negotiables: Tier1NonNegotiables    # Tier 1 responses
    responses: CheckInResponses                    # Free-text responses
    
    compliance_score: float = Field(..., ge=0.0, le=100.0)  # 0-100%
    completed_at: datetime = Field(default_factory=datetime.utcnow)
    duration_seconds: int = Field(default=0, ge=0)  # Time taken to complete (for analytics)
    
    # Phase 3E: Quick check-in tracking
    is_quick_checkin: bool = False  # Was this a quick check-in (Tier 1 only)?
    
    # Correction tracking: set when /correct command updates this check-in
    corrected_at: Optional[datetime] = None  # Timestamp of correction (None = not corrected)
    
    def to_firestore(self) -> dict:
        """Convert to Firestore-compatible dictionary."""
        data = {
            "date": self.date,
            "user_id": self.user_id,
            "mode": self.mode,
            "tier1_non_negotiables": self.tier1_non_negotiables.model_dump(),
            "responses": self.responses.model_dump(),
            "compliance_score": self.compliance_score,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds,
            "is_quick_checkin": self.is_quick_checkin,
        }
        if self.corrected_at:
            data["corrected_at"] = self.corrected_at
        return data
    
    @classmethod
    def from_firestore(cls, data: dict) -> "DailyCheckIn":
        """Create DailyCheckIn object from Firestore document."""
        # Convert nested dicts back to models
        if "tier1_non_negotiables" in data and isinstance(data["tier1_non_negotiables"], dict):
            data["tier1_non_negotiables"] = Tier1NonNegotiables(**data["tier1_non_negotiables"])
        
        if "responses" in data and isinstance(data["responses"], dict):
            data["responses"] = CheckInResponses(**data["responses"])
        
        return cls(**data)


# ===== Pattern Detection Models (Phase 2) =====

class Pattern(BaseModel):
    """
    Detected constitution violation pattern.
    
    Examples:
    - sleep_degradation: <6 hours for 3 consecutive nights
    - training_abandonment: 3+ missed workouts in a row
    - porn_relapse: 3+ instances in one week
    """
    pattern_id: str                               # Unique ID
    pattern_name: str                             # "sleep_degradation", "training_abandonment", etc.
    user_id: str                                  # Affected user
    severity: str                                 # "nudge", "warning", "critical"
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    data_points: list                             # Check-in dates that triggered pattern
    message: str                                  # Intervention message sent to user
    acknowledged: bool = False                    # Did user respond to intervention?


# ===== Helper Functions =====

def get_current_date_ist(tz: str = "Asia/Kolkata") -> str:
    """
    Get current date in the specified timezone (YYYY-MM-DD format).

    Delegates to timezone_utils.get_current_date() for the actual calculation.
    Kept here for backward compatibility — many modules import from schemas.

    Args:
        tz: IANA timezone string (default: "Asia/Kolkata" for backward compat)

    Returns:
        str: Date in YYYY-MM-DD format (e.g., "2026-02-08")
    """
    from src.utils.timezone_utils import get_current_date
    return get_current_date(tz)


def get_current_datetime_ist(tz: str = "Asia/Kolkata") -> datetime:
    """
    Get current datetime in the specified timezone.

    Delegates to timezone_utils.get_current_time().

    Args:
        tz: IANA timezone string (default: "Asia/Kolkata")

    Returns:
        datetime: Current time in specified timezone
    """
    from src.utils.timezone_utils import get_current_time
    return get_current_time(tz)
