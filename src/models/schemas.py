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
from typing import Optional


# ===== User Models =====

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


class User(BaseModel):
    """
    User profile stored in Firestore users/ collection.
    
    Example:
        user = User(
            user_id="123456789",
            telegram_id=123456789,
            name="Ayush",
            timezone="Asia/Kolkata"
        )
    """
    user_id: str                                  # Primary key (Telegram user ID as string)
    telegram_id: int                              # Telegram user ID (integer)
    telegram_username: Optional[str] = None       # @username (may be None)
    name: str                                     # Display name
    timezone: str = "Asia/Kolkata"                # User's timezone for check-in scheduling
    streaks: UserStreaks = Field(default_factory=UserStreaks)  # Nested streak data
    constitution_mode: str = "maintenance"        # Current mode: optimization/maintenance/survival
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    
    def to_firestore(self) -> dict:
        """
        Convert to Firestore-compatible dictionary.
        
        Firestore doesn't understand Pydantic models directly, so we convert
        to a plain Python dict.
        """
        return {
            "user_id": self.user_id,
            "telegram_id": self.telegram_id,
            "telegram_username": self.telegram_username,
            "name": self.name,
            "timezone": self.timezone,
            "streaks": self.streaks.model_dump(),  # Convert nested model to dict
            "constitution_mode": self.constitution_mode,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_firestore(cls, data: dict) -> "User":
        """
        Create User object from Firestore document.
        
        Args:
            data: Dictionary from Firestore document.data()
            
        Returns:
            User object with validated data
        """
        # Convert nested dict back to UserStreaks
        if "streaks" in data and isinstance(data["streaks"], dict):
            data["streaks"] = UserStreaks(**data["streaks"])
        
        return cls(**data)


# ===== Check-In Models =====

class Tier1NonNegotiables(BaseModel):
    """
    Tier 1 non-negotiables from constitution.
    
    5 Core Habits (Boolean + Optional Details):
    1. Sleep: 7+ hours
    2. Training: Workout or scheduled rest day
    3. Deep Work: 2+ hours focused work
    4. Zero Porn: No consumption (absolute rule)
    5. Boundaries: No toxic interactions
    """
    sleep: bool                                   # Did you get 7+ hours?
    sleep_hours: Optional[float] = None           # Actual hours slept (e.g., 7.5)
    
    training: bool                                # Did you train?
    is_rest_day: bool = False                     # Was today a scheduled rest day?
    training_type: Optional[str] = None           # "workout", "rest", "skipped"
    
    deep_work: bool                               # Did you complete 2+ hours?
    deep_work_hours: Optional[float] = None       # Actual hours (e.g., 2.5)
    
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
    
    def to_firestore(self) -> dict:
        """Convert to Firestore-compatible dictionary."""
        return {
            "date": self.date,
            "user_id": self.user_id,
            "mode": self.mode,
            "tier1_non_negotiables": self.tier1_non_negotiables.model_dump(),
            "responses": self.responses.model_dump(),
            "compliance_score": self.compliance_score,
            "completed_at": self.completed_at,
            "duration_seconds": self.duration_seconds
        }
    
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

def get_current_date_ist() -> str:
    """
    Get current date in IST timezone (YYYY-MM-DD format).
    
    Why IST?
    - User is in India (Hyderabad)
    - Check-ins happen at 9 PM IST
    - Dates should align with user's perception of "today"
    
    Returns:
        str: Date in YYYY-MM-DD format (e.g., "2026-01-30")
    """
    import pytz
    from datetime import datetime
    
    ist = pytz.timezone("Asia/Kolkata")
    now_ist = datetime.now(ist)
    return now_ist.strftime("%Y-%m-%d")


def get_current_datetime_ist() -> datetime:
    """
    Get current datetime in IST timezone.
    
    Returns:
        datetime: Current time in IST
    """
    import pytz
    from datetime import datetime
    
    ist = pytz.timezone("Asia/Kolkata")
    return datetime.now(ist)
