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
from uuid import uuid4


# ===== User Models =====

class ReminderTimes(BaseModel):
    """
    Configurable reminder times for daily check-ins.
    
    Phase 3A: Triple reminder system
    - First: Friendly reminder (9:00 PM)
    - Second: Nudge (10:00 PM)
    - Third: Urgent reminder (11:00 PM)
    
    Future: Per-user customizable times
    """
    first: str = "21:00"   # HH:MM format (9:00 PM)
    second: str = "22:00"  # HH:MM format (10:00 PM)
    third: str = "23:00"   # HH:MM format (11:00 PM)


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


class AIProfileMemory(BaseModel):
    """
    Long-term AI-derived memory of user's behavior patterns, strengths, weaknesses,
    and habit correlations (synthesized periodically).
    """
    summary: str = "New user starting their journey."
    strengths: List[str] = Field(default_factory=list)
    weaknesses: List[str] = Field(default_factory=list)
    recurring_obstacles: List[Dict] = Field(default_factory=list)  # [{"obstacle": "social media", "frequency": "high", "last_seen": "YYYY-MM-DD"}]
    correlations: List[str] = Field(default_factory=list)
    coaching_notes: str = ""
    say_do_ratio: float = Field(default=0.0, ge=0.0, le=100.0)
    last_updated: Optional[datetime] = None


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
    partner_checkin_notifications_enabled: bool = True    # Shared pair setting for daily check-in notifications
    
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
    
    # ===== Phase 5: Periodic Reports =====
    last_report_date: Optional[str] = None   # YYYY-MM-DD of last sent report (prevents duplicates)
    
    # ===== P1.2: User Settings =====
    settings: Dict = Field(default_factory=lambda: {
        "morning_briefing_enabled": True,
        "last_briefing_date": None,
    })
    
    # ===== P1.4: Churn Risk (Internal Only) =====
    churn_risk_score: float = Field(default=0.0, ge=0.0, le=1.0)
    last_churn_check: Optional[datetime] = None
    last_churn_intervention: Optional[datetime] = None
    
    # ===== P4.1: Onboarding =====
    onboarding_completed: bool = True  # Default True for backward compat with existing users
    onboarding_step: Optional[str] = None  # Current step if incomplete
    
    # ===== P4.2: Streak Recovery =====
    break_reasons: List[Dict] = Field(default_factory=list)  # [{"date": "2026-02-01", "reason": "sleep", "context": "..."}]
    
    # ===== P4.3: Feature Discovery =====
    hints_sent: List[str] = Field(default_factory=list)  # IDs of hints already sent
    
    # ===== AI Memory Upgrade =====
    ai_profile_memory: AIProfileMemory = Field(default_factory=AIProfileMemory)
    
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
            "partner_checkin_notifications_enabled": self.partner_checkin_notifications_enabled,
            
            # Phase 3C: Gamification
            "achievements": self.achievements,
            "level": self.level,
            "xp": self.xp,
            
            # Phase 3D: Career
            "career_mode": self.career_mode,
            
            # Phase 3F: Social
            "leaderboard_opt_in": self.leaderboard_opt_in,
            "referred_by": self.referred_by,
            "referral_code": self.referral_code,
            
            # Phase 5: Periodic Reports
            "last_report_date": self.last_report_date,
            
            # P1.2: User Settings
            "settings": self.settings,
            
            # P1.4: Churn Risk (Internal)
            "churn_risk_score": self.churn_risk_score,
            "last_churn_check": self.last_churn_check,
            "last_churn_intervention": self.last_churn_intervention,
            
            # P4.1: Onboarding
            "onboarding_completed": self.onboarding_completed,
            "onboarding_step": self.onboarding_step,
            
            # P4.2: Streak Recovery
            "break_reasons": self.break_reasons,
            
            # P4.3: Feature Discovery
            "hints_sent": self.hints_sent,
            
            # AI Memory Upgrade
            "ai_profile_memory": self.ai_profile_memory.model_dump() if hasattr(self.ai_profile_memory, 'model_dump') else self.ai_profile_memory,
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
        
        # P1.4: Convert churn datetime strings to datetime objects (if stored as strings)
        for churn_field in ["last_churn_check", "last_churn_intervention"]:
            if churn_field in data and isinstance(data[churn_field], str):
                try:
                    data[churn_field] = datetime.fromisoformat(data[churn_field])
                except (ValueError, TypeError):
                    data[churn_field] = None
        
        # AI Memory Upgrade
        if "ai_profile_memory" in data and isinstance(data["ai_profile_memory"], dict):
            data["ai_profile_memory"] = AIProfileMemory(**data["ai_profile_memory"])
        
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
    
    <b>Phase v2.0: Continuous Data Capture</b>
    
    Now captures continuous metrics (hours) with computed boolean properties
    for backward compatibility.
    
    6 Core Habits (Continuous + Computed Boolean):
    1. Sleep: 7+ hours (captured as hours, computed boolean)
    2. Training: Workout or scheduled rest day (captured as intensity, computed boolean)
    3. Deep Work: 2+ hours focused work (captured as hours, computed boolean)
    4. Skill Building: 2+ hours career-focused learning (captured as hours, computed boolean)
    5. Zero Porn: No consumption (absolute rule) - boolean only
    6. Boundaries: No toxic interactions - boolean only
    
    <b>Backward Compatibility:</b>
    - Old code reading 'tier1.sleep' still works (computed property)
    - Old code reading 'tier1.deep_work' still works (computed property)
    - Migrated check-ins have data_quality="migrated"
    - New check-ins have data_quality="actual"
    """
    
    # ===== Continuous Metrics (Primary Data — v2.0) =====
    # Optional with defaults for backward compatibility with v1 check-ins
    sleep_hours: Optional[float] = Field(default=None, ge=0, le=16, description="Actual hours slept")
    deep_work_hours: Optional[float] = Field(default=None, ge=0, le=16, description="Actual focused hours")
    skill_building_hours: Optional[float] = Field(default=None, ge=0, le=16, description="Actual learning hours")
    
    # ===== Training Intensity (v2.0) =====
    training_intensity: Optional[str] = Field(
        default=None,
        pattern="^(rest|light|moderate|intense)$",
        description="Training intensity level"
    )
    
    # ===== Legacy Boolean Fields (RETAINED for backward compatibility) =====
    sleep: bool = False
    training: bool = False
    deep_work: bool = False
    skill_building: bool = False
    
    # ===== Computed Properties (v2.0) =====
    @property
    def sleep_met(self) -> bool:
        """Did user meet sleep target (allowing micro-habit: 6+ hours)? Uses hours if available, falls back to boolean."""
        if self.sleep_hours is not None:
            return self.sleep_hours >= 6.0
        return self.sleep
    
    @property
    def sleep_met_full(self) -> bool:
        """Did user meet the full 7+ hour sleep target?"""
        if self.sleep_hours is not None:
            return self.sleep_hours >= 7.0
        return self.sleep
    
    @property
    def deep_work_met(self) -> bool:
        """Did user meet deep work target (allowing micro-habit: 0.5+ hours)? Uses hours if available, falls back to boolean."""
        if self.deep_work_hours is not None:
            return self.deep_work_hours >= 0.5
        return self.deep_work
    
    @property
    def deep_work_met_full(self) -> bool:
        """Did user meet the full 2+ hour deep work target?"""
        if self.deep_work_hours is not None:
            return self.deep_work_hours >= 2.0
        return self.deep_work
    
    @property
    def skill_building_met(self) -> bool:
        """Did user meet skill building target (allowing micro-habit: 0.5+ hours)? Uses hours if available, falls back to boolean."""
        if self.skill_building_hours is not None:
            return self.skill_building_hours >= 0.5
        return self.skill_building
    
    @property
    def skill_building_met_full(self) -> bool:
        """Did user meet the full 2+ hour skill building target?"""
        if self.skill_building_hours is not None:
            return self.skill_building_hours >= 2.0
        return self.skill_building
    
    @property
    def training_done(self) -> bool:
        """Did user train today? Uses intensity if available, falls back to boolean."""
        if self.training_intensity is not None:
            return self.training_intensity in ("light", "moderate", "intense")
        return self.training
    
    # ===== Optional Detail Fields (Existing — Unchanged) =====
    is_rest_day: bool = False
    training_type: Optional[str] = None
    skill_building_activity: Optional[str] = None
    
    zero_porn: bool
    boundaries: bool
    
    # ===== Data Quality Flag (v2.0) =====
    data_quality: str = Field(
        default="actual",
        description="actual | migrated | estimated"
    )


class CheckInResponses(BaseModel):
    """
    User's responses to check-in questions.
    
    Questions (Phase 1 - Hardcoded):
    1. Challenges: What challenges did you face today?
    2. Rating: Rate today 1-10 on constitution alignment
    3. Rating Reason: Why that score?
    4. Tomorrow Priority: What's tomorrow's #1 priority?
    5. Tomorrow Obstacle: What's the biggest potential obstacle?
    
    Questions (Phase 3 - Mood & Energy):
    6. Energy: Rate your energy today 1-10
    7. Mood: Rate your mood today 1-10
    """
    challenges: str = Field(..., min_length=10, max_length=500)      # 10-500 chars
    rating: int = Field(..., ge=1, le=10)                            # 1-10 scale
    rating_reason: str = Field(..., min_length=10, max_length=500)   # Why that rating?
    tomorrow_priority: str = Field(..., min_length=10, max_length=500)
    tomorrow_obstacle: str = Field(..., min_length=10, max_length=500)
    
    # P3.2: Mood & Energy tracking (optional for backward compatibility)
    energy_rating: Optional[int] = Field(None, ge=1, le=10, description="Energy level 1-10")
    mood_rating: Optional[int] = Field(None, ge=1, le=10, description="Mood level 1-10")


class DailyTaskItem(BaseModel):
    """
    Individual task item for a user's daily focus list.
    """
    id: str
    title: str
    is_primary: bool
    completed: bool
    completed_at: Optional[datetime] = None


class DailyTaskList(BaseModel):
    """
    User's daily focus list (tasks) for a specific date.
    
    Stored in Firestore: daily_tasks/{user_id}/tasks/{date}
    """
    user_id: str
    date: str                                     # YYYY-MM-DD format
    tasks: List[DailyTaskItem] = Field(default_factory=list)
    committed: bool = False
    committed_at: Optional[datetime] = None

    def to_firestore(self) -> dict:
        """Convert to Firestore-compatible dictionary."""
        return {
            "user_id": self.user_id,
            "date": self.date,
            "tasks": [t.model_dump() for t in self.tasks],
            "committed": self.committed,
            "committed_at": self.committed_at,
        }

    @classmethod
    def from_firestore(cls, data: dict) -> "DailyTaskList":
        """Create DailyTaskList object from Firestore document."""
        data = dict(data)  # Avoid mutating caller's dict
        if "tasks" in data and isinstance(data["tasks"], list):
            data["tasks"] = [
                DailyTaskItem(**t) if isinstance(t, dict) else t
                for t in data["tasks"]
            ]
        return cls(**data)


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
    
    # Added for daily tasks integration
    committed_tasks: Optional[List[DailyTaskItem]] = None
    
    return_reason: Optional[str] = None  # Why user returned after ghosting (2A)
    
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
        if self.committed_tasks is not None:
            data["committed_tasks"] = [t.model_dump() for t in self.committed_tasks]
        else:
            data["committed_tasks"] = None
        if self.return_reason is not None:
            data["return_reason"] = self.return_reason
        return data
    
    @classmethod
    def from_firestore(cls, data: dict) -> "DailyCheckIn":
        """Create DailyCheckIn object from Firestore document."""
        data = dict(data)  # Avoid mutating caller's dict
        # Convert nested dicts back to models
        if "tier1_non_negotiables" in data and isinstance(data["tier1_non_negotiables"], dict):
            data["tier1_non_negotiables"] = Tier1NonNegotiables(**data["tier1_non_negotiables"])
        
        if "responses" in data and isinstance(data["responses"], dict):
            data["responses"] = CheckInResponses(**data["responses"])
            
        if "committed_tasks" in data and data["committed_tasks"] is not None:
            data["committed_tasks"] = [
                DailyTaskItem(**t) if isinstance(t, dict) else t
                for t in data["committed_tasks"]
            ]
        
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


# ===== P2.2: Goal Model =====

class Goal(BaseModel):
    """
    User-defined SMART goal with automatic progress tracking.

    Goals are tied to constitution principles and auto-update based on
    check-in data. Examples:
        - "Sleep 7+ hours for 14 consecutive days"
        - "Complete LeetCode 150 by June 1"
        - "Zero porn for 90 days"
    """
    goal_id: str = Field(default_factory=lambda: f"goal_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:6]}")
    user_id: str
    title: str                        # "Sleep 7+ hours for 14 days"
    description: str                  # "Build consistent sleep habit"
    category: str                     # sleep | training | deep_work | skill_building | zero_porn | boundaries | custom
    target_value: Optional[float] = None  # e.g., 7.0 hours
    target_days: int = 14             # e.g., 14 consecutive days
    start_date: str                   # YYYY-MM-DD
    end_date: Optional[str] = None    # YYYY-MM-DD
    status: str = "active"            # active | completed | failed | paused
    progress: List[Dict] = Field(default_factory=list)  # [{"date": "2026-02-01", "met": True, "value": 7.5}]
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_firestore(self) -> dict:
        return {
            "goal_id": self.goal_id,
            "user_id": self.user_id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "target_value": self.target_value,
            "target_days": self.target_days,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status,
            "progress": self.progress,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_firestore(cls, data: dict) -> "Goal":
        return cls(**data)


# ===== P2.3: Partner Challenge Model =====

class PartnerChallenge(BaseModel):
    """
    Shared challenge between two accountability partners.

    Partners compete or collaborate on a shared goal (e.g., "7-day sleep challenge").
    Progress is tracked per participant and updated after each check-in.
    """
    challenge_id: str = Field(default_factory=lambda: f"ch_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{uuid4().hex[:6]}")
    challenger_id: str      # Who created the challenge
    partner_id: str         # Who was invited
    challenge_type: str     # sleep_7_days | training_5_days | deep_work_7_days | custom
    title: str
    description: str
    start_date: str         # YYYY-MM-DD
    end_date: str           # YYYY-MM-DD
    status: str = "pending"  # pending | active | completed | cancelled
    
    # Progress tracking per participant
    # progress: {user_id: [{"date": "2026-02-01", "met": True, "value": 7.5}]}
    progress: Dict[str, List[Dict]] = Field(default_factory=dict)
    
    # Winner (if competitive)
    winner_id: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None

    def to_firestore(self) -> dict:
        return {
            "challenge_id": self.challenge_id,
            "challenger_id": self.challenger_id,
            "partner_id": self.partner_id,
            "challenge_type": self.challenge_type,
            "title": self.title,
            "description": self.description,
            "start_date": self.start_date,
            "end_date": self.end_date,
            "status": self.status,
            "progress": self.progress,
            "winner_id": self.winner_id,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
        }

    @classmethod
    def from_firestore(cls, data: dict) -> "PartnerChallenge":
        return cls(**data)


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
