"""
Timezone Utilities Tests
========================

Tests for the 3AM cutoff logic, IST/UTC conversions, and date range calculations.

**Why These Tests Matter:**
The 3AM cutoff is a critical business rule. If `get_checkin_date()` is wrong:
- Late check-ins (12:30 AM) could be assigned to the wrong day
- Users could get double-counted or miss a day
- Streaks could break incorrectly

**Testing Strategy:**
- Test boundary conditions around 3 AM exactly
- Test both naive and timezone-aware datetimes
- Test UTC→IST and IST→UTC conversions
- Test date range calculations
"""

import pytest
import pytz
from datetime import datetime, timedelta, time

from src.utils.timezone_utils import (
    get_checkin_date,
    utc_to_ist,
    ist_to_utc,
    parse_time_ist,
    get_date_range_ist,
    get_next_monday,
    format_datetime_for_display,
    IST,
    UTC,
)


# ===== get_checkin_date: 3 AM Cutoff Tests =====

class TestGetCheckinDate:
    """
    Tests for the 3 AM cutoff rule.
    
    The rule: Check-ins before 3 AM count for the previous day.
    This is because users might check in late at night (e.g., 1 AM)
    and it should count for "yesterday" from their perspective.
    
    Edge cases:
    - Exactly 3:00 AM → counts for current day (after 3 AM)
    - 2:59 AM → counts for previous day (before 3 AM)
    - 11:00 PM → counts for current day (normal)
    - Midnight → counts for previous day (before 3 AM)
    """

    def test_normal_evening_checkin(self):
        """11 PM check-in should count for that day (Feb 3)."""
        evening = IST.localize(datetime(2026, 2, 3, 23, 0, 0))
        result = get_checkin_date(evening)
        assert result == "2026-02-03"

    def test_late_night_before_midnight(self):
        """11:59 PM check-in should count for that day."""
        late_night = IST.localize(datetime(2026, 2, 3, 23, 59, 0))
        result = get_checkin_date(late_night)
        assert result == "2026-02-03"

    def test_midnight_counts_for_previous_day(self):
        """12:00 AM (midnight) should count for previous day."""
        midnight = IST.localize(datetime(2026, 2, 4, 0, 0, 0))
        result = get_checkin_date(midnight)
        assert result == "2026-02-03"

    def test_1am_counts_for_previous_day(self):
        """1:00 AM should count for previous day (late check-in)."""
        one_am = IST.localize(datetime(2026, 2, 4, 1, 0, 0))
        result = get_checkin_date(one_am)
        assert result == "2026-02-03"

    def test_230am_counts_for_previous_day(self):
        """2:30 AM should still count for previous day."""
        early_morning = IST.localize(datetime(2026, 2, 4, 2, 30, 0))
        result = get_checkin_date(early_morning)
        assert result == "2026-02-03"

    def test_259am_counts_for_previous_day(self):
        """2:59 AM is the last moment that counts for previous day."""
        just_before_cutoff = IST.localize(datetime(2026, 2, 4, 2, 59, 0))
        result = get_checkin_date(just_before_cutoff)
        assert result == "2026-02-03"

    def test_3am_exactly_counts_for_current_day(self):
        """3:00 AM exactly should count for the current day (new day starts)."""
        exactly_3am = IST.localize(datetime(2026, 2, 4, 3, 0, 0))
        result = get_checkin_date(exactly_3am)
        assert result == "2026-02-04"

    def test_301am_counts_for_current_day(self):
        """3:01 AM should count for current day."""
        just_after_cutoff = IST.localize(datetime(2026, 2, 4, 3, 1, 0))
        result = get_checkin_date(just_after_cutoff)
        assert result == "2026-02-04"

    def test_morning_checkin(self):
        """9:00 AM normal morning check-in counts for current day."""
        morning = IST.localize(datetime(2026, 2, 4, 9, 0, 0))
        result = get_checkin_date(morning)
        assert result == "2026-02-04"

    def test_afternoon_checkin(self):
        """3:00 PM afternoon check-in counts for current day."""
        afternoon = IST.localize(datetime(2026, 2, 4, 15, 0, 0))
        result = get_checkin_date(afternoon)
        assert result == "2026-02-04"

    def test_naive_datetime_assumed_ist(self):
        """Naive datetime (no timezone) should be treated as IST."""
        naive_evening = datetime(2026, 2, 3, 21, 0, 0)
        result = get_checkin_date(naive_evening)
        assert result == "2026-02-03"

    def test_naive_midnight_assumed_ist(self):
        """Naive midnight should be treated as IST and count for previous day."""
        naive_midnight = datetime(2026, 2, 4, 0, 30, 0)
        result = get_checkin_date(naive_midnight)
        assert result == "2026-02-03"

    def test_utc_datetime_converted_to_ist(self):
        """
        UTC datetime should be converted to IST before applying 3AM rule.
        
        3:30 PM UTC = 9:00 PM IST → should count for current IST day.
        IST is UTC+5:30, so 15:30 UTC = 21:00 IST.
        """
        utc_time = UTC.localize(datetime(2026, 2, 3, 15, 30, 0))
        result = get_checkin_date(utc_time)
        assert result == "2026-02-03"

    def test_utc_late_night_converts_correctly(self):
        """
        UTC 20:00 = IST 1:30 AM next day → should count for previous IST day.
        
        20:00 UTC on Feb 3 = 1:30 AM IST on Feb 4 → counts for Feb 3.
        """
        utc_late = UTC.localize(datetime(2026, 2, 3, 20, 0, 0))
        result = get_checkin_date(utc_late)
        # 20:00 UTC = 1:30 AM IST Feb 4 → before 3AM → counts for Feb 3
        assert result == "2026-02-03"

    def test_month_boundary(self):
        """Late check-in at month boundary: 1 AM Feb 1 counts for Jan 31."""
        month_boundary = IST.localize(datetime(2026, 2, 1, 1, 0, 0))
        result = get_checkin_date(month_boundary)
        assert result == "2026-01-31"

    def test_year_boundary(self):
        """Late check-in at year boundary: 1 AM Jan 1 counts for Dec 31."""
        year_boundary = IST.localize(datetime(2026, 1, 1, 1, 0, 0))
        result = get_checkin_date(year_boundary)
        assert result == "2025-12-31"


# ===== UTC/IST Conversion Tests =====

class TestUTCToIST:
    """
    Tests for UTC → IST conversion.
    IST is UTC+5:30 (5 hours 30 minutes ahead).
    """

    def test_basic_conversion(self):
        """3:30 PM UTC → 9:00 PM IST."""
        utc_time = UTC.localize(datetime(2026, 2, 3, 15, 30, 0))
        ist_time = utc_to_ist(utc_time)
        assert ist_time.hour == 21
        assert ist_time.minute == 0

    def test_midnight_utc_to_ist(self):
        """Midnight UTC → 5:30 AM IST."""
        utc_midnight = UTC.localize(datetime(2026, 2, 3, 0, 0, 0))
        ist_time = utc_to_ist(utc_midnight)
        assert ist_time.hour == 5
        assert ist_time.minute == 30

    def test_naive_utc_assumed(self):
        """Naive datetime should be assumed UTC."""
        naive_time = datetime(2026, 2, 3, 12, 0, 0)
        ist_time = utc_to_ist(naive_time)
        assert ist_time.hour == 17
        assert ist_time.minute == 30

    def test_date_rollover(self):
        """UTC 20:00 → IST 1:30 AM next day."""
        utc_evening = UTC.localize(datetime(2026, 2, 3, 20, 0, 0))
        ist_time = utc_to_ist(utc_evening)
        assert ist_time.day == 4
        assert ist_time.hour == 1
        assert ist_time.minute == 30


class TestISTToUTC:
    """Tests for IST → UTC conversion."""

    def test_basic_conversion(self):
        """9:00 PM IST → 3:30 PM UTC."""
        ist_time = IST.localize(datetime(2026, 2, 3, 21, 0, 0))
        utc_time = ist_to_utc(ist_time)
        assert utc_time.hour == 15
        assert utc_time.minute == 30

    def test_naive_ist_assumed(self):
        """Naive datetime should be assumed IST."""
        naive_time = datetime(2026, 2, 3, 21, 0, 0)
        utc_time = ist_to_utc(naive_time)
        assert utc_time.hour == 15
        assert utc_time.minute == 30

    def test_roundtrip_conversion(self):
        """UTC → IST → UTC should give back same time."""
        original = UTC.localize(datetime(2026, 2, 3, 12, 0, 0))
        roundtrip = ist_to_utc(utc_to_ist(original))
        assert original.hour == roundtrip.hour
        assert original.minute == roundtrip.minute


# ===== Parse Time Tests =====

class TestParseTimeIST:
    """Tests for time string parsing."""

    def test_standard_time(self):
        result = parse_time_ist("21:00")
        assert result == time(21, 0)

    def test_midnight(self):
        result = parse_time_ist("00:00")
        assert result == time(0, 0)

    def test_with_minutes(self):
        result = parse_time_ist("21:30")
        assert result == time(21, 30)


# ===== Date Range Tests =====

class TestGetDateRangeIST:
    """Tests for date range calculation."""

    def test_7_day_range(self):
        """7-day range should span exactly 7 days."""
        start, end = get_date_range_ist(7)
        # Parse dates
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        # Difference should be 6 days (inclusive of both start and end = 7 days)
        assert (end_dt - start_dt).days == 6

    def test_30_day_range(self):
        """30-day range should span exactly 30 days."""
        start, end = get_date_range_ist(30)
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        assert (end_dt - start_dt).days == 29

    def test_1_day_range(self):
        """1-day range should be just today."""
        start, end = get_date_range_ist(1)
        assert start == end


# ===== Next Monday Tests =====

class TestGetNextMonday:
    """Tests for weekly reset scheduling."""

    def test_returns_future_date(self):
        """Next Monday should always be in the future."""
        next_mon = get_next_monday(format_string="%Y-%m-%d")
        next_mon_dt = datetime.strptime(next_mon, "%Y-%m-%d")
        today = datetime.now()
        assert next_mon_dt.date() > today.date()

    def test_returns_monday(self):
        """Result should always be a Monday (weekday=0)."""
        next_mon = get_next_monday(format_string="%Y-%m-%d")
        next_mon_dt = datetime.strptime(next_mon, "%Y-%m-%d")
        assert next_mon_dt.weekday() == 0  # Monday = 0

    def test_custom_format(self):
        """Custom format string should work."""
        result = get_next_monday(format_string="%B %d, %Y")
        # Should contain month name
        months = ["January", "February", "March", "April", "May", "June",
                  "July", "August", "September", "October", "November", "December"]
        assert any(m in result for m in months)


# ===== Display Format Tests =====

class TestFormatDatetimeForDisplay:
    """Tests for user-facing datetime formatting."""

    def test_with_time(self):
        dt = IST.localize(datetime(2026, 1, 30, 21, 0, 0))
        result = format_datetime_for_display(dt)
        assert "Jan 30, 2026" in result
        assert "9:00 PM IST" in result

    def test_without_time(self):
        dt = IST.localize(datetime(2026, 1, 30, 21, 0, 0))
        result = format_datetime_for_display(dt, include_time=False)
        assert "Jan 30, 2026" in result
        assert "PM" not in result

    def test_utc_input_converted(self):
        """UTC datetime should be converted to IST for display."""
        dt = UTC.localize(datetime(2026, 1, 30, 15, 30, 0))  # 3:30 PM UTC = 9:00 PM IST
        result = format_datetime_for_display(dt)
        assert "9:00 PM IST" in result
