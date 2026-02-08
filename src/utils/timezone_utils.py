"""
Timezone Utilities
==================

Helper functions for working with timezones.

Architecture:
- All functions accept an optional `tz` parameter (IANA timezone string).
- Default is "Asia/Kolkata" (IST) for backward compatibility.
- Old IST-specific function names are kept as aliases.
- Firestore stores timestamps in UTC; we convert to user's local tz for display.

Key Concept:
Always store in UTC, convert to user's local timezone for display and date calculations.

Supported Timezones (IANA format):
- "Asia/Kolkata" (IST, UTC+5:30)
- "America/New_York" (EST/EDT, UTC-5/-4)
- "America/Los_Angeles" (PST/PDT, UTC-8/-7)
- "Europe/London" (GMT/BST, UTC+0/+1)
- Any valid IANA timezone string recognized by pytz

Phase B Enhancement (Feb 2026):
Generalized from IST-only to support any timezone. All functions
now accept a `tz` parameter. The default remains IST so existing
callers continue to work without changes.
"""

import pytz
from datetime import datetime, time, timedelta
from typing import Optional, Tuple

# ===== Common Timezone Objects =====
# Pre-built for frequently-used timezones. Others are created on-demand.
IST = pytz.timezone("Asia/Kolkata")
UTC = pytz.UTC

# ===== Predefined Timezone Catalog =====
# Used by the onboarding picker and /timezone command.
# Organized by region for the two-level selection menu.
TIMEZONE_CATALOG = {
    "americas": {
        "label": "🌎 Americas",
        "timezones": [
            {"id": "America/Los_Angeles", "label": "🇺🇸 US Pacific (Los Angeles)", "offset": "UTC-8"},
            {"id": "America/Denver", "label": "🇺🇸 US Mountain (Denver)", "offset": "UTC-7"},
            {"id": "America/Chicago", "label": "🇺🇸 US Central (Chicago)", "offset": "UTC-6"},
            {"id": "America/New_York", "label": "🇺🇸 US Eastern (New York)", "offset": "UTC-5"},
            {"id": "America/Sao_Paulo", "label": "🇧🇷 Brazil (São Paulo)", "offset": "UTC-3"},
        ],
    },
    "europe": {
        "label": "🌍 Europe",
        "timezones": [
            {"id": "Europe/London", "label": "🇬🇧 UK (London)", "offset": "UTC+0"},
            {"id": "Europe/Paris", "label": "🇫🇷 Central Europe (Paris)", "offset": "UTC+1"},
            {"id": "Europe/Helsinki", "label": "🇫🇮 Eastern Europe (Helsinki)", "offset": "UTC+2"},
        ],
    },
    "asia_oceania": {
        "label": "🌏 Asia & Oceania",
        "timezones": [
            {"id": "Asia/Dubai", "label": "🇦🇪 Gulf (Dubai)", "offset": "UTC+4"},
            {"id": "Asia/Kolkata", "label": "🇮🇳 India (Kolkata)", "offset": "UTC+5:30"},
            {"id": "Asia/Singapore", "label": "🇸🇬 Singapore", "offset": "UTC+8"},
            {"id": "Asia/Tokyo", "label": "🇯🇵 Japan (Tokyo)", "offset": "UTC+9"},
            {"id": "Australia/Sydney", "label": "🇦🇺 Australia East (Sydney)", "offset": "UTC+11"},
            {"id": "Pacific/Auckland", "label": "🇳🇿 New Zealand (Auckland)", "offset": "UTC+12"},
        ],
    },
}


def _get_tz(tz: str = "Asia/Kolkata") -> pytz.BaseTzInfo:
    """
    Convert an IANA timezone string to a pytz timezone object.

    Why a helper? pytz.timezone() is called frequently. This function
    provides a single place for error handling and potential caching.

    Args:
        tz: IANA timezone string (e.g., "America/New_York")

    Returns:
        pytz timezone object

    Raises:
        pytz.UnknownTimeZoneError: If timezone string is invalid
    """
    return pytz.timezone(tz)


def get_timezone_display_name(tz: str) -> str:
    """
    Get a human-readable display name for a timezone.

    Searches the TIMEZONE_CATALOG for a matching label.
    Falls back to the raw IANA string if not found.

    Args:
        tz: IANA timezone string

    Returns:
        str: Display name (e.g., "US Eastern (New York)")
    """
    for region in TIMEZONE_CATALOG.values():
        for tz_info in region["timezones"]:
            if tz_info["id"] == tz:
                return tz_info["label"]
    return tz  # Fallback to raw IANA string


def is_valid_timezone(tz: str) -> bool:
    """
    Check if a timezone string is valid.

    Args:
        tz: IANA timezone string to validate

    Returns:
        bool: True if valid, False otherwise
    """
    try:
        pytz.timezone(tz)
        return True
    except pytz.UnknownTimeZoneError:
        return False


# ===== Core Functions (Timezone-Parameterized) =====


def get_current_time(tz: str = "Asia/Kolkata") -> datetime:
    """
    Get current datetime in the specified timezone.

    Args:
        tz: IANA timezone string (default: "Asia/Kolkata" for IST)

    Returns:
        datetime: Current time in specified timezone (timezone-aware)

    Example:
        >>> now_ist = get_current_time("Asia/Kolkata")
        >>> now_est = get_current_time("America/New_York")
    """
    local_tz = _get_tz(tz)
    return datetime.now(local_tz)


def get_current_date(tz: str = "Asia/Kolkata") -> str:
    """
    Get current date in the specified timezone (YYYY-MM-DD format).

    Used for:
    - Determining which day's check-in we're on
    - Storing check-in dates
    - Preventing duplicate same-day check-ins

    Args:
        tz: IANA timezone string (default: "Asia/Kolkata")

    Returns:
        str: Date in YYYY-MM-DD format

    Example:
        >>> get_current_date("Asia/Kolkata")
        '2026-02-08'
        >>> get_current_date("America/New_York")
        '2026-02-07'  # Behind IST by 10.5 hours
    """
    now_local = get_current_time(tz)
    return now_local.strftime("%Y-%m-%d")


def get_checkin_date(current_time: Optional[datetime] = None, tz: str = "Asia/Kolkata") -> str:
    """
    Determine which date a check-in should count for.

    **3 AM Cutoff Rule (in user's local timezone):**
    - Check-in before 3 AM local → Counts for PREVIOUS day (late check-in)
    - Check-in after 3 AM local → Counts for CURRENT day (normal check-in)

    **Why 3 AM?**
    Some users work late or have irregular sleep schedules.
    3 AM gives a 3-hour grace period after midnight while still
    maintaining "daily" discipline.

    **Examples (in user's local timezone):**
    - 11:30 PM Feb 3 → Counts for Feb 3 (normal)
    - 12:30 AM Feb 4 → Counts for Feb 3 (late check-in)
    - 2:45 AM Feb 4 → Counts for Feb 3 (late check-in)
    - 3:05 AM Feb 4 → Counts for Feb 4 (new day)

    Args:
        current_time: Datetime to check (defaults to now in user's tz).
                      If naive, assumes the specified timezone.
        tz: IANA timezone string for the 3 AM cutoff calculation.

    Returns:
        str: Date in YYYY-MM-DD format that check-in should count for
    """
    local_tz = _get_tz(tz)

    # Get current time in user's local timezone
    if current_time is None:
        local_time = datetime.now(local_tz)
    else:
        # Convert to user's local timezone
        if current_time.tzinfo is None:
            # Assume the specified timezone if naive
            local_time = local_tz.localize(current_time)
        else:
            # Convert from whatever timezone to user's local
            local_time = current_time.astimezone(local_tz)

    # Apply 3 AM cutoff rule in user's local timezone
    if local_time.hour < 3:
        # Before 3 AM = count for previous day
        checkin_date = (local_time - timedelta(days=1)).date()
    else:
        # After 3 AM = count for current day
        checkin_date = local_time.date()

    return checkin_date.strftime("%Y-%m-%d")


def utc_to_local(utc_datetime: datetime, tz: str = "Asia/Kolkata") -> datetime:
    """
    Convert UTC datetime to a local timezone.

    Used when reading timestamps from Firestore (which stores in UTC)
    and displaying them to the user.

    Args:
        utc_datetime: Datetime in UTC (timezone-aware or naive).
                      If naive, assumes UTC.
        tz: Target timezone IANA string (default: "Asia/Kolkata")

    Returns:
        datetime: Same moment in time, in the target timezone

    Example:
        >>> utc_time = datetime(2026, 1, 30, 15, 30, tzinfo=pytz.UTC)
        >>> local_time = utc_to_local(utc_time, "Asia/Kolkata")
        >>> local_time.strftime("%H:%M")
        '21:00'  # 9:00 PM IST
    """
    local_tz = _get_tz(tz)

    # If naive (no timezone), assume UTC
    if utc_datetime.tzinfo is None:
        utc_datetime = UTC.localize(utc_datetime)

    return utc_datetime.astimezone(local_tz)


def local_to_utc(local_datetime: datetime, tz: str = "Asia/Kolkata") -> datetime:
    """
    Convert a local timezone datetime to UTC.

    Used when storing timestamps to Firestore.

    Args:
        local_datetime: Datetime in local timezone (timezone-aware or naive).
                        If naive, assumes the specified timezone.
        tz: Source timezone IANA string (default: "Asia/Kolkata")

    Returns:
        datetime: Same moment in time, in UTC

    Example:
        >>> ist_time = datetime(2026, 1, 30, 21, 0)  # 9:00 PM (naive)
        >>> utc_time = local_to_utc(ist_time, "Asia/Kolkata")
        >>> utc_time.strftime("%H:%M")
        '15:30'  # 3:30 PM UTC
    """
    local_tz = _get_tz(tz)

    # If naive (no timezone), assume the specified timezone
    if local_datetime.tzinfo is None:
        local_datetime = local_tz.localize(local_datetime)

    return local_datetime.astimezone(UTC)


def format_datetime_for_display(dt: datetime, tz: str = "Asia/Kolkata", include_time: bool = True) -> str:
    """
    Format datetime for user-friendly display in Telegram.

    Args:
        dt: Datetime to format (any timezone)
        tz: User's timezone for display (default: "Asia/Kolkata")
        include_time: Whether to include time (or just date)

    Returns:
        str: Formatted string

    Examples:
        >>> dt = datetime(2026, 1, 30, 15, 30, tzinfo=pytz.UTC)
        >>> format_datetime_for_display(dt, "Asia/Kolkata")
        'Jan 30, 2026 at 9:00 PM IST'
        >>> format_datetime_for_display(dt, "America/New_York")
        'Jan 30, 2026 at 10:30 AM EST'
    """
    local_tz = _get_tz(tz)

    # Convert to user's timezone if not already
    if dt.tzinfo is None or dt.tzinfo != local_tz:
        dt = utc_to_local(dt, tz)

    # Get timezone abbreviation (e.g., IST, EST, PST)
    tz_abbr = dt.strftime("%Z")

    if include_time:
        return dt.strftime(f"%b %d, %Y at %I:%M %p {tz_abbr}")
    else:
        return dt.strftime("%b %d, %Y")


def get_date_range(days: int = 7, tz: str = "Asia/Kolkata") -> Tuple[str, str]:
    """
    Get date range for last N days in the specified timezone.

    Used for fetching recent check-ins from Firestore.

    Args:
        days: Number of days to look back
        tz: Timezone for "today" calculation

    Returns:
        tuple: (start_date, end_date) in YYYY-MM-DD format
    """
    now_local = get_current_time(tz)
    end_date = now_local.strftime("%Y-%m-%d")
    start_date_dt = now_local - timedelta(days=days - 1)
    start_date = start_date_dt.strftime("%Y-%m-%d")
    return (start_date, end_date)


def parse_time_ist(time_str: str) -> time:
    """
    Parse time string (HH:MM) format.

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
    Check if current IST time matches the target check-in time.

    Used by Cloud Scheduler for legacy fixed-time reminders.

    Args:
        target_time_str: Target time in "HH:MM" format (default: 21:00)

    Returns:
        bool: True if current time matches (within 1 minute tolerance)
    """
    now_ist = get_current_time("Asia/Kolkata")
    target_time = parse_time_ist(target_time_str)

    current_time = now_ist.time()
    hour_match = current_time.hour == target_time.hour
    minute_close = abs(current_time.minute - target_time.minute) <= 1

    return hour_match and minute_close


def seconds_until_checkin_time(target_time_str: str = "21:00") -> int:
    """
    Calculate seconds until next check-in time (IST).

    Args:
        target_time_str: Target time in "HH:MM" format

    Returns:
        int: Seconds until target time
    """
    now_ist = get_current_time("Asia/Kolkata")
    target_time = parse_time_ist(target_time_str)

    target_datetime = now_ist.replace(
        hour=target_time.hour,
        minute=target_time.minute,
        second=0,
        microsecond=0,
    )

    if target_datetime < now_ist:
        target_datetime += timedelta(days=1)

    time_diff = target_datetime - now_ist
    return int(time_diff.total_seconds())


def get_next_monday(timezone: str = "Asia/Kolkata", format_string: str = "%B %d, %Y") -> str:
    """
    Get the date of the next Monday (for weekly resets).

    Args:
        timezone: Timezone to use (default: Asia/Kolkata)
        format_string: How to format the date

    Returns:
        str: Next Monday's date formatted as specified
    """
    tz = pytz.timezone(timezone)
    now = datetime.now(tz)

    days_ahead = 7 - now.weekday()
    if days_ahead == 0:
        days_ahead = 7

    next_monday = now + timedelta(days=days_ahead)
    return next_monday.strftime(format_string)


def get_timezones_at_local_time(utc_now: datetime, target_hour: int, target_minute: int = 0,
                                 tolerance_minutes: int = 15) -> list[str]:
    """
    Find all timezone IDs from our catalog where current local time matches target.

    Used by bucket-based reminder scheduling: "which timezones are at 9 PM right now?"

    Theory: Given a UTC time, we check each timezone in our catalog.
    If the local time in that timezone falls within `tolerance_minutes`
    of the target hour:minute, we include it.

    Args:
        utc_now: Current UTC datetime
        target_hour: Target local hour (0-23)
        target_minute: Target local minute (0-59)
        tolerance_minutes: How many minutes of slack to allow (default: 15)

    Returns:
        list[str]: IANA timezone IDs that match (e.g., ["Asia/Kolkata", "Asia/Dubai"])
    """
    matching = []

    # Collect all timezone IDs from our catalog
    all_tz_ids = []
    for region in TIMEZONE_CATALOG.values():
        for tz_info in region["timezones"]:
            all_tz_ids.append(tz_info["id"])

    for tz_id in all_tz_ids:
        local_tz = pytz.timezone(tz_id)
        local_now = utc_now.astimezone(local_tz)

        # Calculate minutes since midnight in local time
        local_minutes = local_now.hour * 60 + local_now.minute
        target_minutes = target_hour * 60 + target_minute

        # Check if within tolerance
        diff = abs(local_minutes - target_minutes)
        # Handle midnight wraparound (e.g., 23:50 vs 00:05 = 15 min diff)
        if diff > 720:  # More than 12 hours → wrap around
            diff = 1440 - diff

        if diff <= tolerance_minutes:
            matching.append(tz_id)

    return matching


# ===== Backward Compatibility Aliases =====
# These keep all existing callers working without any changes.
# They simply delegate to the new generalized functions with IST defaults.

def get_current_time_ist() -> datetime:
    """Backward-compatible alias for get_current_time("Asia/Kolkata")."""
    return get_current_time("Asia/Kolkata")


def get_current_date_ist() -> str:
    """Backward-compatible alias for get_current_date("Asia/Kolkata")."""
    return get_current_date("Asia/Kolkata")


def utc_to_ist(utc_datetime: datetime) -> datetime:
    """Backward-compatible alias for utc_to_local(dt, "Asia/Kolkata")."""
    return utc_to_local(utc_datetime, "Asia/Kolkata")


def ist_to_utc(ist_datetime: datetime) -> datetime:
    """Backward-compatible alias for local_to_utc(dt, "Asia/Kolkata")."""
    return local_to_utc(ist_datetime, "Asia/Kolkata")


def get_date_range_ist(days: int = 7) -> Tuple[str, str]:
    """Backward-compatible alias for get_date_range(days, "Asia/Kolkata")."""
    return get_date_range(days, "Asia/Kolkata")
