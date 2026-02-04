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
from typing import Optional


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


def is_streak_at_risk(last_checkin_date: str) -> bool:
    """
    Check if streak is at risk (approaching 48-hour deadline).
    
    Used for reminder notifications.
    
    Args:
        last_checkin_date: Last check-in date (YYYY-MM-DD)
        
    Returns:
        bool: True if >24 hours have passed (needs check-in soon)
        
    Example:
        If last check-in was 2026-01-28 and today is 2026-01-30:
        >>> is_streak_at_risk("2026-01-28")
        True  # 2 days passed, streak at risk!
    """
    from src.models.schemas import get_current_date_ist
    
    current_date = get_current_date_ist()
    last_date = datetime.strptime(last_checkin_date, "%Y-%m-%d")
    curr_date = datetime.strptime(current_date, "%Y-%m-%d")
    
    days_diff = (curr_date - last_date).days
    
    # If 1 or more days have passed since last check-in, streak is at risk
    return days_diff >= 1


# ===== Phase 3A: Streak Shields =====

def should_reset_streak_shields(last_reset_date: Optional[str]) -> bool:
    """
    Check if 30 days have passed since last shield reset (Phase 3A).
    
    Streak shields reset every 30 days to 3/3.
    
    Args:
        last_reset_date: Last reset date (YYYY-MM-DD) or None if never reset
        
    Returns:
        bool: True if shields should be reset
    """
    if last_reset_date is None:
        # First time - reset needed
        return True
    
    from src.models.schemas import get_current_date_ist
    
    current_date = get_current_date_ist()
    last_reset = datetime.strptime(last_reset_date, "%Y-%m-%d")
    curr_date_dt = datetime.strptime(current_date, "%Y-%m-%d")
    
    days_diff = (curr_date_dt - last_reset).days
    
    # Reset every 30 days
    return days_diff >= 30


def calculate_days_without_checkin(last_checkin_date: Optional[str]) -> int:
    """
    Calculate how many days since last check-in (Phase 3A).
    
    Used for ghosting detection and streak shield decisions.
    
    Args:
        last_checkin_date: Last check-in date (YYYY-MM-DD) or None
        
    Returns:
        int: Days since last check-in (0 if checked in today, -1 if never)
    """
    if last_checkin_date is None:
        return -1  # Never checked in
    
    from src.models.schemas import get_current_date_ist
    
    current_date = get_current_date_ist()
    last_date = datetime.strptime(last_checkin_date, "%Y-%m-%d")
    curr_date_dt = datetime.strptime(current_date, "%Y-%m-%d")
    
    return (curr_date_dt - last_date).days
