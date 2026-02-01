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
