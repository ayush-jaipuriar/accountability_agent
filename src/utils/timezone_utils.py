"""
Timezone Utilities
==================

Helper functions for working with timezones (primarily IST).

Why Timezone Handling Matters:
- Firestore stores timestamps in UTC
- User is in India (IST = UTC+5:30)
- Check-ins happen at 9 PM IST
- "Today" for the user might be "tomorrow" in UTC

Key Concept:
Always store in UTC, convert to IST for display and date calculations.
"""

import pytz
from datetime import datetime, time
from typing import Optional


# IST Timezone object (reused throughout app)
IST = pytz.timezone("Asia/Kolkata")
UTC = pytz.UTC


def get_current_time_ist() -> datetime:
    """
    Get current datetime in IST timezone.
    
    Returns:
        datetime: Current time in IST (timezone-aware)
        
    Example:
        >>> now_ist = get_current_time_ist()
        >>> now_ist.tzinfo.zone
        'Asia/Kolkata'
    """
    return datetime.now(IST)


def get_current_date_ist() -> str:
    """
    Get current date in IST timezone (YYYY-MM-DD format).
    
    Used for:
    - Determining which day's check-in we're on
    - Storing check-in dates
    - Preventing duplicate same-day check-ins
    
    Returns:
        str: Date in YYYY-MM-DD format
        
    Example:
        >>> get_current_date_ist()
        '2026-01-30'
    """
    now_ist = get_current_time_ist()
    return now_ist.strftime("%Y-%m-%d")


def get_checkin_date(current_time: Optional[datetime] = None) -> str:
    """
    Determine which date a check-in should count for (Phase 3A Late Check-In Support).
    
    **3 AM Cutoff Rule:**
    - Check-in before 3 AM → Counts for PREVIOUS day (late check-in)
    - Check-in after 3 AM → Counts for CURRENT day (normal check-in)
    
    **Why 3 AM?**
    From constitution:
    - Some users work late or have irregular sleep schedules
    - 3 AM gives 3-hour grace period after midnight
    - Still maintains "daily" discipline without being too lenient
    
    **Examples:**
    - 11:30 PM Feb 3 → Counts for Feb 3 (normal)
    - 12:30 AM Feb 4 → Counts for Feb 3 (late check-in)
    - 2:45 AM Feb 4 → Counts for Feb 3 (late check-in)
    - 3:05 AM Feb 4 → Counts for Feb 4 (new day)
    
    Args:
        current_time: Datetime to check (defaults to now). If naive, assumes IST.
        
    Returns:
        str: Date in YYYY-MM-DD format that check-in should count for
        
    Phase 3A Integration:
    ---------------------
    Use this instead of get_current_date_ist() when storing check-ins
    to support late check-ins properly.
    """
    from datetime import timedelta
    
    # Get current time in IST
    if current_time is None:
        ist_time = get_current_time_ist()
    else:
        # Convert to IST if not already
        if current_time.tzinfo is None:
            # Assume IST if naive
            ist_time = IST.localize(current_time)
        elif current_time.tzinfo != IST:
            ist_time = utc_to_ist(current_time)
        else:
            ist_time = current_time
    
    # Check if before 3 AM
    if ist_time.hour < 3:
        # Before 3 AM = count for previous day
        checkin_date = (ist_time - timedelta(days=1)).date()
    else:
        # After 3 AM = count for current day
        checkin_date = ist_time.date()
    
    return checkin_date.strftime("%Y-%m-%d")


def utc_to_ist(utc_datetime: datetime) -> datetime:
    """
    Convert UTC datetime to IST.
    
    Used when reading timestamps from Firestore (which stores in UTC).
    
    Args:
        utc_datetime: Datetime in UTC (timezone-aware or naive)
        
    Returns:
        datetime: Same moment in time, but IST timezone
        
    Example:
        >>> utc_time = datetime(2026, 1, 30, 15, 30, tzinfo=pytz.UTC)  # 3:30 PM UTC
        >>> ist_time = utc_to_ist(utc_time)
        >>> ist_time.strftime("%H:%M")
        '21:00'  # 9:00 PM IST
    """
    # If naive (no timezone), assume UTC
    if utc_datetime.tzinfo is None:
        utc_datetime = UTC.localize(utc_datetime)
    
    # Convert to IST
    return utc_datetime.astimezone(IST)


def ist_to_utc(ist_datetime: datetime) -> datetime:
    """
    Convert IST datetime to UTC.
    
    Used when storing timestamps to Firestore.
    
    Args:
        ist_datetime: Datetime in IST (timezone-aware or naive)
        
    Returns:
        datetime: Same moment in time, but UTC timezone
        
    Example:
        >>> ist_time = datetime(2026, 1, 30, 21, 0)  # 9:00 PM IST (naive)
        >>> utc_time = ist_to_utc(ist_time)
        >>> utc_time.strftime("%H:%M")
        '15:30'  # 3:30 PM UTC
    """
    # If naive (no timezone), assume IST
    if ist_datetime.tzinfo is None:
        ist_datetime = IST.localize(ist_datetime)
    
    # Convert to UTC
    return ist_datetime.astimezone(UTC)


def parse_time_ist(time_str: str) -> time:
    """
    Parse time string (HH:MM) in IST timezone.
    
    Args:
        time_str: Time in "HH:MM" format (e.g., "21:00")
        
    Returns:
        time: Time object
        
    Example:
        >>> check_in_time = parse_time_ist("21:00")
        >>> check_in_time.hour
        21
    """
    hour, minute = map(int, time_str.split(":"))
    return time(hour=hour, minute=minute)


def is_time_for_checkin(target_time_str: str = "21:00") -> bool:
    """
    Check if current time is the scheduled check-in time.
    
    Used by Cloud Scheduler to trigger check-in reminders.
    
    Args:
        target_time_str: Target time in "HH:MM" format (default: 21:00 = 9 PM)
        
    Returns:
        bool: True if current time matches target (within 1 minute tolerance)
        
    Example:
        If current IST time is 21:00:
        >>> is_time_for_checkin("21:00")
        True
    """
    now_ist = get_current_time_ist()
    target_time = parse_time_ist(target_time_str)
    
    current_time = now_ist.time()
    
    # Check if within 1 minute of target time
    # (gives Cloud Scheduler some leeway for execution timing)
    hour_match = current_time.hour == target_time.hour
    minute_close = abs(current_time.minute - target_time.minute) <= 1
    
    return hour_match and minute_close


def format_datetime_for_display(dt: datetime, include_time: bool = True) -> str:
    """
    Format datetime for user-friendly display in Telegram.
    
    Args:
        dt: Datetime to format (UTC or IST)
        include_time: Whether to include time (or just date)
        
    Returns:
        str: Formatted string
        
    Examples:
        >>> dt = datetime(2026, 1, 30, 21, 0, tzinfo=IST)
        >>> format_datetime_for_display(dt)
        'Jan 30, 2026 at 9:00 PM IST'
        
        >>> format_datetime_for_display(dt, include_time=False)
        'Jan 30, 2026'
    """
    # Convert to IST if not already
    if dt.tzinfo != IST:
        dt = utc_to_ist(dt)
    
    if include_time:
        return dt.strftime("%b %d, %Y at %I:%M %p IST")
    else:
        return dt.strftime("%b %d, %Y")


def get_date_range_ist(days: int = 7) -> tuple[str, str]:
    """
    Get date range for last N days in IST.
    
    Used for fetching recent check-ins from Firestore.
    
    Args:
        days: Number of days to look back
        
    Returns:
        tuple: (start_date, end_date) in YYYY-MM-DD format
        
    Example:
        If today is 2026-01-30:
        >>> get_date_range_ist(7)
        ('2026-01-23', '2026-01-30')
    """
    now_ist = get_current_time_ist()
    end_date = now_ist.strftime("%Y-%m-%d")
    
    from datetime import timedelta
    start_date_dt = now_ist - timedelta(days=days - 1)  # -1 to include today
    start_date = start_date_dt.strftime("%Y-%m-%d")
    
    return (start_date, end_date)


def seconds_until_checkin_time(target_time_str: str = "21:00") -> int:
    """
    Calculate seconds until next check-in time.
    
    Used for scheduling reminders.
    
    Args:
        target_time_str: Target time in "HH:MM" format
        
    Returns:
        int: Seconds until target time (positive if in future, negative if in past)
        
    Example:
        If current time is 8:00 PM and target is 9:00 PM:
        >>> seconds_until_checkin_time("21:00")
        3600  # 1 hour = 3600 seconds
    """
    from datetime import timedelta
    
    now_ist = get_current_time_ist()
    target_time = parse_time_ist(target_time_str)
    
    # Create datetime for today at target time
    target_datetime = now_ist.replace(
        hour=target_time.hour,
        minute=target_time.minute,
        second=0,
        microsecond=0
    )
    
    # If target time has passed today, use tomorrow
    if target_datetime < now_ist:
        target_datetime += timedelta(days=1)
    
    # Calculate difference
    time_diff = target_datetime - now_ist
    return int(time_diff.total_seconds())


def get_next_monday(timezone: str = "Asia/Kolkata", format_string: str = "%B %d, %Y") -> str:
    """
    Get the date of the next Monday (for weekly resets).
    
    Used for:
    - Quick check-in weekly reset (every Monday 12:00 AM)
    - Displaying when limit resets to users
    
    Args:
        timezone: Timezone to use (default: Asia/Kolkata)
        format_string: How to format the date (default: "February 10, 2026")
        
    Returns:
        str: Next Monday's date formatted as specified
        
    Examples:
        If today is Wednesday, Feb 5, 2026:
        >>> get_next_monday()
        'February 10, 2026'  # Following Monday
        
        If today is Monday, Feb 3, 2026:
        >>> get_next_monday()
        'February 10, 2026'  # Next Monday (not today)
        
    Phase 3E Usage:
    ---------------
    - Quick check-ins reset every Monday 12:00 AM
    - Show users: "Limit resets: Monday Feb 10 at 12:00 AM IST"
    """
    from datetime import timedelta
    
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)
    
    # Calculate days until next Monday
    # Monday = 0, Sunday = 6
    days_ahead = 7 - now.weekday()  # Days until next Monday
    
    # If today is Monday, go to next week's Monday
    if days_ahead == 0:
        days_ahead = 7
    
    next_monday = now + timedelta(days=days_ahead)
    
    return next_monday.strftime(format_string)
