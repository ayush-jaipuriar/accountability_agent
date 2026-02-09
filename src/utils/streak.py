"""
Streak Tracking Logic
====================

Pure functions for managing check-in streaks.

Streak Rules (from constitution):
- Streak increments: If check-in within 48 hours of last check-in
- Streak resets: If gap exceeds 48 hours (2+ days)
- Longest streak: Historical maximum (never decreases)

Why 48 hours?
- Gives flexibility for time zone issues
- Allows missing one day without breaking streak (if checked in next day)
- Prevents harsh penalties for single slip

Example Timeline:
    Day 1 (Jan 28): Check-in at 9 PM → Streak = 1
    Day 2 (Jan 29): Check-in at 9 PM → Streak = 2 (24 hours later ✅)
    Day 3 (Jan 30): Check-in at 11 PM → Streak = 3 (26 hours later ✅)
    --- Skip Day 4 ---
    Day 5 (Feb 1): Check-in at 9 PM → Streak = 1 (72 hours later ❌ reset)
"""

from datetime import datetime, timedelta
from typing import Optional, Dict
import logging
import random

logger = logging.getLogger(__name__)


# ===== Phase D: Streak Recovery System =====
# Motivational facts shown when a streak resets. These normalize resets as part of
# the long-term habit-building process (drawn from behavioral psychology research).
# A random fact is chosen each time to keep the message fresh.
RECOVERY_FACTS = [
    "Most people who reach 30+ days had at least one reset along the way.",
    "Research shows habit formation averages 66 days — resets are part of the process.",
    "Elite athletes track 'return-to-form' time, not zero-failure streaks.",
    "A streak reset isn't starting over — it's starting from experience.",
    "The #1 predictor of long-term success? Restarting after a break.",
    "Every marathon runner walks sometimes. What matters is finishing.",
    "Consistency isn't perfection — it's always getting back on track.",
    "Your brain forms stronger habits after recovering from a break.",
]


def format_streak_reset_message(
    streak_before_reset: int,
    recovery_fact: str
) -> str:
    """
    Generate a compassionate, motivating message when a streak resets.
    
    <b>Why This Matters (Behavioral Psychology):</b>
    When a streak resets, the user experiences a "what-the-hell" effect —
    a cognitive distortion where a single failure feels like total failure.
    This message combats that by:
    1. Acknowledging their previous achievement (loss aversion is real)
    2. Reframing the reset as a *part* of the journey, not the end
    3. Providing a concrete next milestone (Comeback King at 7 days)
    4. Using a random motivational fact for social proof
    
    Args:
        streak_before_reset: The streak value before it was reset
        recovery_fact: A motivational fact from RECOVERY_FACTS
        longest_streak: All-time best streak for additional context
        
    Returns:
        Formatted reset message string (Telegram Markdown-safe)
    """
    parts = ["🔄 <b>Fresh Start!</b>\n"]
    
    if streak_before_reset > 0:
        parts.append(
            f"Your previous streak: {streak_before_reset} days 🏆\n"
            f"That's still YOUR record — and you earned every day of it.\n"
        )
    
    parts.append("🔥 New streak: Day 1 — the comeback starts now.\n")
    parts.append(f"💡 {recovery_fact}\n")
    parts.append("🎯 Next milestone: 7 days → unlocks Comeback King! 🦁")
    
    return "\n".join(parts)


def get_recovery_milestone_message(
    current_streak: int,
    streak_before_reset: int,
    last_reset_date: Optional[str] = None
) -> Optional[str]:
    """
    Check if the user's current post-reset streak deserves a recovery milestone message.
    
    <b>Recovery Milestone Theory:</b>
    After a reset, we celebrate small wins MORE aggressively than normal milestones.
    This is because the user is in a psychologically fragile state — they need positive
    reinforcement early to prevent dropout. These milestones are *separate* from the
    normal streak milestones (7, 14, 30...) and only fire when there was a recent reset.
    
    <b>Milestone Schedule:</b>
    | Days After Reset | Message | Psychology |
    |---|---|---|
    | 3 | "3 days strong!" | Prove the reset was a bump, not a stop |
    | 7 | "Comeback King!" | Full week = real momentum |
    | 14 | "Two weeks rebuilt" | Halfway to a strong habit |
    | Exceeds old streak | "NEW RECORD!" | Ultimate vindication |
    
    Args:
        current_streak: Current streak value (post-reset)
        streak_before_reset: What the streak was before it reset
        last_reset_date: Date of last reset (YYYY-MM-DD) to confirm recency
        
    Returns:
        Recovery milestone message if applicable, None otherwise
    """
    # Only show recovery milestones if there was a recent reset
    if not last_reset_date or streak_before_reset == 0:
        return None
    
    # Check if this is a recovery period (within reasonable timeframe)
    # If the user has been going for 100+ days since reset, 
    # the normal milestone system takes over
    if current_streak > max(streak_before_reset * 2, 30):
        return None
    
    # Check milestones (most impactful first)
    if current_streak > streak_before_reset and streak_before_reset >= 3:
        return (
            f"👑 <b>NEW RECORD!</b>\n\n"
            f"You've surpassed your previous {streak_before_reset}-day streak!\n"
            f"Current: {current_streak} days. Unstoppable. 🔥"
        )
    
    if current_streak == 14:
        return (
            "🔥 <b>Two Weeks Strong!</b>\n\n"
            "You've rebuilt half of what you had. "
            "The momentum is real. Keep going! 💪"
        )
    
    if current_streak == 7:
        return (
            "🦁 <b>Comeback King!</b>\n\n"
            "A full week back after reset. "
            "Your resilience is your superpower. 💪"
        )
    
    if current_streak == 3:
        return (
            "💪 <b>3 Days Strong!</b>\n\n"
            "You're proving the reset was just a bump, not a stop. "
            "Keep this energy going! 🔥"
        )
    
    return None


def should_increment_streak(last_checkin_date: str, current_date: str) -> bool:
    """
    Determine if streak should increment or reset.
    
    Rules:
    - Same day (0 days): No change (shouldn't happen, but handle it)
    - 1 day gap: Increment streak ✅
    - 2+ day gap: Reset streak ❌
    
    Args:
        last_checkin_date: Last check-in date in "YYYY-MM-DD" format
        current_date: Current check-in date in "YYYY-MM-DD" format
        
    Returns:
        bool: True if should increment, False if should reset
        
    Examples:
        >>> should_increment_streak("2026-01-29", "2026-01-30")
        True  # 1 day gap → increment
        
        >>> should_increment_streak("2026-01-25", "2026-01-30")
        False  # 5 day gap → reset
        
        >>> should_increment_streak("2026-01-30", "2026-01-30")
        False  # Same day → no change
    """
    # Parse dates
    last_date = datetime.strptime(last_checkin_date, "%Y-%m-%d")
    curr_date = datetime.strptime(current_date, "%Y-%m-%d")
    
    # Calculate difference in days
    days_diff = (curr_date - last_date).days
    
    if days_diff == 0:
        # Same day (duplicate check-in attempt)
        return False
    elif days_diff == 1:
        # Yesterday → increment
        return True
    else:
        # Gap of 2+ days → reset
        return False


def calculate_new_streak(
    current_streak: int,
    last_checkin_date: Optional[str],
    new_checkin_date: str
) -> int:
    """
    Calculate new streak value after a check-in.
    
    Scenarios:
    1. First ever check-in (last_checkin_date is None) → Streak = 1
    2. Consecutive check-in (gap = 1 day) → Increment
    3. Gap of 2+ days → Reset to 1
    
    Args:
        current_streak: Current streak count
        last_checkin_date: Last check-in date (None if first check-in)
        new_checkin_date: Today's check-in date
        
    Returns:
        int: New streak value
        
    Examples:
        >>> calculate_new_streak(0, None, "2026-01-30")
        1  # First check-in
        
        >>> calculate_new_streak(47, "2026-01-29", "2026-01-30")
        48  # Consecutive day
        
        >>> calculate_new_streak(47, "2026-01-25", "2026-01-30")
        1  # Reset after gap
    """
    if last_checkin_date is None:
        # First ever check-in
        return 1
    
    if should_increment_streak(last_checkin_date, new_checkin_date):
        # Consecutive check-in → increment
        return current_streak + 1
    else:
        # Gap too large → reset
        return 1


def update_streak_data(
    current_streak: int,
    longest_streak: int,
    total_checkins: int,
    last_checkin_date: Optional[str],
    new_checkin_date: str
) -> dict:
    """
    Calculate all streak updates after a check-in.
    
    This is the main function used by the check-in handler.
    
    Returns a dictionary with updated streak data to store in Firestore.
    
    Args:
        current_streak: Current streak value
        longest_streak: All-time best streak
        total_checkins: Lifetime total check-ins
        last_checkin_date: Last check-in date (None if first)
        new_checkin_date: Today's check-in date
        
    Returns:
        dict: Updated streak data with keys:
            - current_streak: New streak value
            - longest_streak: Updated if current exceeds longest
            - last_checkin_date: Today's date
            - total_checkins: Incremented by 1
            
    Example:
        >>> updates = update_streak_data(
        ...     current_streak=47,
        ...     longest_streak=47,
        ...     total_checkins=100,
        ...     last_checkin_date="2026-01-29",
        ...     new_checkin_date="2026-01-30"
        ... )
        >>> updates['current_streak']
        48
        >>> updates['longest_streak']
        48  # Updated because current exceeded longest
        >>> updates['total_checkins']
        101
    """
    # Calculate new streak
    new_streak = calculate_new_streak(
        current_streak,
        last_checkin_date,
        new_checkin_date
    )
    
    # Update longest streak if current exceeds it
    new_longest = max(new_streak, longest_streak)
    
    return {
        "current_streak": new_streak,
        "longest_streak": new_longest,
        "last_checkin_date": new_checkin_date,
        "total_checkins": total_checkins + 1
    }


def get_streak_emoji(streak: int) -> str:
    """
    Get emoji representation of streak milestone.
    
    Milestones:
    - 1-6 days: 🔥 (building)
    - 7-29 days: 💪 (strong)
    - 30-89 days: 🚀 (amazing)
    - 90-179 days: 🏆 (champion)
    - 180+ days: 👑 (legendary)
    
    Args:
        streak: Current streak value
        
    Returns:
        str: Emoji representing milestone
    """
    if streak >= 180:
        return "👑"  # 6 months - legendary
    elif streak >= 90:
        return "🏆"  # 3 months - champion
    elif streak >= 30:
        return "🚀"  # 1 month - amazing
    elif streak >= 7:
        return "💪"  # 1 week - strong
    else:
        return "🔥"  # Building


def format_streak_message(
    current_streak: int,
    longest_streak: int,
    is_new_record: bool = False
) -> str:
    """
    Generate formatted streak message for Telegram.
    
    Args:
        current_streak: Current streak
        longest_streak: All-time best
        is_new_record: True if current_streak just beat longest_streak
        
    Returns:
        str: Formatted message
        
    Examples:
        >>> format_streak_message(48, 48, is_new_record=True)
        '👑 NEW RECORD! 48 days straight!\\n(Previous best: 47 days)'
        
        >>> format_streak_message(10, 47)
        '🔥 Current streak: 10 days\\nPersonal best: 47 days'
    """
    emoji = get_streak_emoji(current_streak)
    
    if is_new_record and current_streak > 1:
        return (
            f"{emoji} NEW RECORD! {current_streak} days straight!\n"
            f"(Previous best: {longest_streak - 1} days)"
        )
    else:
        return (
            f"{emoji} Current streak: {current_streak} days\n"
            f"Personal best: {longest_streak} days"
        )


def days_until_milestone(current_streak: int) -> tuple[int, str]:
    """
    Calculate days until next streak milestone.
    
    Used for motivational messages.
    
    Args:
        current_streak: Current streak
        
    Returns:
        tuple: (days_remaining, milestone_name)
        
    Example:
        >>> days_until_milestone(25)
        (5, '30 days')
        
        >>> days_until_milestone(85)
        (5, '90 days')
    """
    milestones = [7, 15,30, 45, 60, 90, 120,150,180,250, 365]
    
    for milestone in milestones:
        if current_streak < milestone:
            days_left = milestone - current_streak
            return (days_left, f"{milestone} days")
    
    # Already past all milestones
    return (0, "legendary status")


def is_streak_at_risk(last_checkin_date: str, tz: str = "Asia/Kolkata") -> bool:
    """
    Check if streak is at risk (approaching 48-hour deadline).
    
    Used for reminder notifications.
    
    Args:
        last_checkin_date: Last check-in date (YYYY-MM-DD)
        tz: User's IANA timezone (default: "Asia/Kolkata" for backward compat)
        
    Returns:
        bool: True if >24 hours have passed (needs check-in soon)
        
    Example:
        If last check-in was 2026-01-28 and today is 2026-01-30:
        >>> is_streak_at_risk("2026-01-28")
        True  # 2 days passed, streak at risk!
    """
    from src.utils.timezone_utils import get_current_date
    
    current_date = get_current_date(tz)
    last_date = datetime.strptime(last_checkin_date, "%Y-%m-%d")
    curr_date = datetime.strptime(current_date, "%Y-%m-%d")
    
    days_diff = (curr_date - last_date).days
    
    # If 1 or more days have passed since last check-in, streak is at risk
    return days_diff >= 1


# ===== Phase 3A: Streak Shields =====

def should_reset_streak_shields(last_reset_date: Optional[str], tz: str = "Asia/Kolkata") -> bool:
    """
    Check if 30 days have passed since last shield reset (Phase 3A).
    
    Streak shields reset every 30 days to 3/3.
    
    Args:
        last_reset_date: Last reset date (YYYY-MM-DD) or None if never reset
        tz: User's IANA timezone (default: "Asia/Kolkata")
        
    Returns:
        bool: True if shields should be reset
    """
    if last_reset_date is None:
        # First time - reset needed
        return True
    
    from src.utils.timezone_utils import get_current_date
    
    current_date = get_current_date(tz)
    last_reset = datetime.strptime(last_reset_date, "%Y-%m-%d")
    curr_date_dt = datetime.strptime(current_date, "%Y-%m-%d")
    
    days_diff = (curr_date_dt - last_reset).days
    
    # Reset every 30 days
    return days_diff >= 30


def calculate_days_without_checkin(last_checkin_date: Optional[str], tz: str = "Asia/Kolkata") -> int:
    """
    Calculate how many days since last check-in (Phase 3A).
    
    Used for ghosting detection and streak shield decisions.
    
    Args:
        last_checkin_date: Last check-in date (YYYY-MM-DD) or None
        tz: User's IANA timezone (default: "Asia/Kolkata")
        
    Returns:
        int: Days since last check-in (0 if checked in today, -1 if never)
    """
    if last_checkin_date is None:
        return -1  # Never checked in
    
    from src.utils.timezone_utils import get_current_date
    
    current_date = get_current_date(tz)
    last_date = datetime.strptime(last_checkin_date, "%Y-%m-%d")
    curr_date_dt = datetime.strptime(current_date, "%Y-%m-%d")
    
    return (curr_date_dt - last_date).days


# ===== Phase 3C: Milestone Celebrations =====

# Milestone message templates
MILESTONE_MESSAGES = {
    30: {
        "title": "🎉 30 DAYS!",
        "message": (
            "🎉 <b>30 DAYS!</b> You're in the top 10% of accountability seekers.\n\n"
            "You've proven you can commit. This is where most people quit, but you pushed through. "
            "Your constitution is becoming automatic. <b>Habit formation threshold reached.</b>\n\n"
            "Keep going! 💪"
        ),
        "percentile": "Top 10%"
    },
    60: {
        "title": "🔥 60 DAYS!",
        "message": (
            "🔥 <b>60 DAYS!</b> Two months of consistency. You're unstoppable.\n\n"
            "The habit is locked in. You don't rely on willpower anymore - it's just what you do. "
            "<b>You're in the top 5% now.</b> This is the version of yourself you were meant to be.\n\n"
            "This is mastery. 🚀"
        ),
        "percentile": "Top 5%"
    },
    90: {
        "title": "💎 90 DAYS!",
        "message": (
            "💎 <b>90 DAYS!</b> Quarter conquered. Elite territory.\n\n"
            "Three months of unbroken commitment. <b>You're operating at a level 98% of people never reach.</b> "
            "Your June 2026 goals? They're within reach. This is what winning looks like.\n\n"
            "Elite status achieved. 🏆"
        ),
        "percentile": "Top 2%"
    },
    180: {
        "title": "🏆 HALF YEAR!",
        "message": (
            "🏆 <b>HALF YEAR!</b> You've built a new identity.\n\n"
            "Six months of daily accountability. <b>You're not the same person who started this journey.</b> "
            "Top 1% consistency. Your future self thanks you for showing up every single day.\n\n"
            "This is transformation. 👑"
        ),
        "percentile": "Top 1%"
    },
    365: {
        "title": "👑 ONE YEAR!",
        "message": (
            "👑 <b>ONE YEAR!</b> You are the 1%. Welcome to mastery.\n\n"
            "365 consecutive days. You've achieved what less than 0.1% of people ever will. "
            "<b>This isn't just a streak - it's proof of who you are.</b> Constitution isn't something you follow anymore. "
            "It's who you've become.\n\n"
            "Congratulations. You've mastered yourself. 🌟"
        ),
        "percentile": "Top 0.1%"
    }
}


def check_milestone(new_streak: int) -> Optional[Dict[str, str]]:
    """
    Check if user hit a major milestone with this streak update.
    
    Theory - Why Milestones Work:
    ------------------------------
    Milestones mark <b>psychological transition points</b> in behavior change:
    
    1. <b>30 Days - Habit Formation Threshold:</b>
       - Research: Habits take 21-66 days to form (median: 66 days, Lally et al., 2009)
       - 30 days is past the "trying it out" phase
       - User has proven commitment
       - Message: "You've proven you can commit"
    
    2. <b>60 Days - Habit Solidification:</b>
       - Neural pathways strengthened
       - Behavior becomes automatic (less willpower needed)
       - Message: "You don't rely on willpower anymore"
    
    3. <b>90 Days - Quarter Marker:</b>
       - 3 months = significant life period
       - Identity starts to shift ("I'm someone who does this")
       - Message: "You're operating at a level 98% never reach"
    
    4. <b>180 Days - Identity Transformation:</b>
       - Half year = life phase change
       - Behavior is now part of identity
       - Message: "You're not the same person who started"
    
    5. <b>365 Days - Mastery:</b>
       - Full year = legendary achievement
       - Identity fully transformed
       - Message: "It's who you've become"
    
    Messaging Principles:
    ---------------------
    - Validate accomplishment (not generic praise)
    - Reference research/percentiles (social proof)
    - Connect to identity shift (habit → identity)
    - Forward-looking (this is just beginning)
    
    Args:
        new_streak: Updated streak count
    
    Returns:
        Milestone dict with title and message, or None if not a milestone
    
    Example:
        >>> check_milestone(30)
        {
            'title': '🎉 30 DAYS!',
            'message': '🎉 30 DAYS! You're in the top 10%...',
            'percentile': 'Top 10%'
        }
        
        >>> check_milestone(29)
        None  # Not a milestone
    """
    if new_streak in MILESTONE_MESSAGES:
        logger.info(f"🎉 Milestone hit: {new_streak} days!")
        return MILESTONE_MESSAGES[new_streak]
    
    return None


def update_streak_data(
    current_streak: int,
    longest_streak: int,
    total_checkins: int,
    last_checkin_date: Optional[str],
    new_checkin_date: str,
    streak_before_reset: int = 0,
    last_reset_date: Optional[str] = None
) -> dict:
    """
    Calculate all streak updates after a check-in.
    
    This is the main function used by the check-in handler.
    
    Returns a dictionary with updated streak data to store in Firestore.
    
    Phase 3C Update: Now also checks for milestones and returns milestone data.
    Phase D Update: Now detects resets and returns recovery context.
    
    <b>Phase D Recovery System:</b>
    When a reset is detected (gap >= 2 days), the function:
    1. Saves the pre-reset streak value as `streak_before_reset`
    2. Records the reset date as `last_reset_date`
    3. Picks a random RECOVERY_FACT for the message
    4. Generates a `recovery_message` for display
    5. Sets `is_reset=True` flag for the conversation handler
    
    When NOT a reset, the function checks for recovery milestones
    (Day 3, 7, 14, exceeds old streak) if there was a recent reset.
    
    <b>Key Design: Transient vs. Persistent keys</b>
    - Persistent (stored in Firestore): current_streak, longest_streak,
      last_checkin_date, total_checkins, streak_before_reset, last_reset_date
    - Transient (used for UI only, stripped before Firestore write):
      milestone_hit, is_reset, recovery_message, recovery_fact
    
    Args:
        current_streak: Current streak value
        longest_streak: All-time best streak
        total_checkins: Lifetime total check-ins
        last_checkin_date: Last check-in date (None if first)
        new_checkin_date: Today's check-in date
        streak_before_reset: Previous streak before last reset (Phase D)
        last_reset_date: Date of last reset (Phase D)
        
    Returns:
        dict: Updated streak data (persistent + transient keys)
    """
    # Calculate new streak
    new_streak = calculate_new_streak(
        current_streak,
        last_checkin_date,
        new_checkin_date
    )
    
    # Update longest streak if current exceeds it
    new_longest = max(new_streak, longest_streak)
    
    # ===== PHASE 3C: Check for milestone =====
    milestone = check_milestone(new_streak)
    
    # ===== PHASE D: Detect reset and add recovery context =====
    is_reset = (new_streak == 1 and current_streak > 0 and last_checkin_date is not None)
    
    result = {
        "current_streak": new_streak,
        "longest_streak": new_longest,
        "last_checkin_date": new_checkin_date,
        "total_checkins": total_checkins + 1,
        "milestone_hit": milestone,         # Phase 3C (transient)
        "is_reset": False,                  # Phase D (transient)
        "recovery_message": None,           # Phase D (transient)
        "recovery_fact": None,              # Phase D (transient)
        # Carry forward existing recovery tracking fields
        "streak_before_reset": streak_before_reset,
        "last_reset_date": last_reset_date,
    }
    
    if is_reset:
        # Streak just reset! Capture recovery context.
        fact = random.choice(RECOVERY_FACTS)
        result["is_reset"] = True
        result["streak_before_reset"] = current_streak  # What was lost
        result["last_reset_date"] = new_checkin_date     # When it happened
        result["recovery_fact"] = fact
        result["recovery_message"] = format_streak_reset_message(
            streak_before_reset=current_streak,
            recovery_fact=fact
        )
        logger.info(
            f"🔄 Streak reset detected: {current_streak} → 1 "
            f"(previous best saved: {current_streak})"
        )
    else:
        # Not a reset — check for recovery milestones (post-reset celebration)
        recovery_milestone = get_recovery_milestone_message(
            current_streak=new_streak,
            streak_before_reset=streak_before_reset,
            last_reset_date=last_reset_date
        )
        if recovery_milestone:
            result["recovery_message"] = recovery_milestone
            logger.info(
                f"🎉 Recovery milestone for streak {new_streak} "
                f"(post-reset from {streak_before_reset})"
            )
    
    return result
