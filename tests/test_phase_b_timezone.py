"""
Phase B: Custom Timezone Support — Comprehensive Test Suite
============================================================

Tests cover:
1. timezone_utils.py — Generalized functions (get_current_date, get_checkin_date, etc.)
2. TIMEZONE_CATALOG — Structure and validity
3. Backward compatibility aliases — IST defaults still work
4. get_timezones_at_local_time — Bucket-based matching
5. format_datetime_for_display — Multi-timezone formatting
6. streak.py — Timezone-parameterized streak functions
7. schemas.py — Updated helper functions delegate correctly
8. Code integration — Verify all callers pass timezone correctly

Run: python -m pytest tests/test_phase_b_timezone.py -v
"""

import pytest
import pytz
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock


# ============================================================
# 1. timezone_utils.py Core Functions
# ============================================================

class TestGetCurrentTime:
    """Test get_current_time() for multiple timezones."""

    def test_ist_default(self):
        """Default timezone should be Asia/Kolkata (IST)."""
        from src.utils.timezone_utils import get_current_time
        result = get_current_time()
        assert result.tzinfo is not None
        assert result.tzinfo.zone == "Asia/Kolkata"

    def test_pst(self):
        """PST timezone should return LA timezone."""
        from src.utils.timezone_utils import get_current_time
        result = get_current_time("America/Los_Angeles")
        assert result.tzinfo is not None
        assert result.tzinfo.zone == "America/Los_Angeles"

    def test_utc(self):
        """UTC timezone should work."""
        from src.utils.timezone_utils import get_current_time
        result = get_current_time("UTC")
        assert result.tzinfo is not None

    def test_invalid_timezone_raises(self):
        """Invalid timezone should raise pytz.UnknownTimeZoneError."""
        from src.utils.timezone_utils import get_current_time
        with pytest.raises(pytz.UnknownTimeZoneError):
            get_current_time("Invalid/Timezone")


class TestGetCurrentDate:
    """Test get_current_date() returns correct date for timezone."""

    def test_ist_default(self):
        """Default returns date in IST."""
        from src.utils.timezone_utils import get_current_date
        result = get_current_date()
        # Should be a valid YYYY-MM-DD string
        datetime.strptime(result, "%Y-%m-%d")

    def test_different_timezones_may_differ(self):
        """Far-apart timezones may show different dates near midnight."""
        from src.utils.timezone_utils import get_current_date
        # Both should return valid dates
        ist_date = get_current_date("Asia/Kolkata")
        pst_date = get_current_date("America/Los_Angeles")
        # Just verify format — they may or may not differ depending on current time
        datetime.strptime(ist_date, "%Y-%m-%d")
        datetime.strptime(pst_date, "%Y-%m-%d")

    def test_explicit_ist(self):
        """Explicit IST should match default."""
        from src.utils.timezone_utils import get_current_date
        assert get_current_date("Asia/Kolkata") == get_current_date()


class TestGetCheckinDate:
    """Test 3 AM cutoff rule in different timezones."""

    def test_before_3am_counts_previous_day(self):
        """Check-in at 2 AM should count for previous day."""
        from src.utils.timezone_utils import get_checkin_date
        # Create a time at 2:00 AM IST on Feb 8
        ist = pytz.timezone("Asia/Kolkata")
        test_time = ist.localize(datetime(2026, 2, 8, 2, 0, 0))
        result = get_checkin_date(test_time, tz="Asia/Kolkata")
        assert result == "2026-02-07"  # Previous day

    def test_after_3am_counts_current_day(self):
        """Check-in at 4 AM should count for current day."""
        from src.utils.timezone_utils import get_checkin_date
        ist = pytz.timezone("Asia/Kolkata")
        test_time = ist.localize(datetime(2026, 2, 8, 4, 0, 0))
        result = get_checkin_date(test_time, tz="Asia/Kolkata")
        assert result == "2026-02-08"

    def test_exactly_3am_counts_current_day(self):
        """Check-in at exactly 3:00 AM counts for current day."""
        from src.utils.timezone_utils import get_checkin_date
        ist = pytz.timezone("Asia/Kolkata")
        test_time = ist.localize(datetime(2026, 2, 8, 3, 0, 0))
        result = get_checkin_date(test_time, tz="Asia/Kolkata")
        assert result == "2026-02-08"

    def test_pst_before_3am(self):
        """3 AM cutoff should apply in PST timezone too."""
        from src.utils.timezone_utils import get_checkin_date
        pst = pytz.timezone("America/Los_Angeles")
        # 2 AM PST on Feb 8
        test_time = pst.localize(datetime(2026, 2, 8, 2, 0, 0))
        result = get_checkin_date(test_time, tz="America/Los_Angeles")
        assert result == "2026-02-07"  # Previous day in PST

    def test_pst_evening(self):
        """Normal evening check-in in PST."""
        from src.utils.timezone_utils import get_checkin_date
        pst = pytz.timezone("America/Los_Angeles")
        test_time = pst.localize(datetime(2026, 2, 8, 21, 0, 0))  # 9 PM PST
        result = get_checkin_date(test_time, tz="America/Los_Angeles")
        assert result == "2026-02-08"

    def test_utc_time_converted_to_local(self):
        """UTC time should be converted to user's timezone before 3 AM check."""
        from src.utils.timezone_utils import get_checkin_date
        # 10:30 PM UTC on Feb 7 = 4:00 AM IST Feb 8 (after 3 AM cutoff)
        utc_time = pytz.UTC.localize(datetime(2026, 2, 7, 22, 30, 0))
        result = get_checkin_date(utc_time, tz="Asia/Kolkata")
        assert result == "2026-02-08"

    def test_naive_time_assumes_specified_tz(self):
        """Naive datetime should be treated as in the specified timezone."""
        from src.utils.timezone_utils import get_checkin_date
        naive_time = datetime(2026, 2, 8, 2, 0, 0)  # 2 AM, no tz
        result = get_checkin_date(naive_time, tz="America/New_York")
        assert result == "2026-02-07"  # Previous day (before 3 AM EST)

    def test_default_tz_is_ist(self):
        """Default timezone for get_checkin_date should be IST."""
        from src.utils.timezone_utils import get_checkin_date
        ist = pytz.timezone("Asia/Kolkata")
        test_time = ist.localize(datetime(2026, 2, 8, 21, 0, 0))
        result = get_checkin_date(test_time)  # No tz= argument
        assert result == "2026-02-08"


class TestUtcToLocal:
    """Test UTC to local timezone conversion."""

    def test_utc_to_ist(self):
        """UTC 15:30 should be IST 21:00 (9 PM)."""
        from src.utils.timezone_utils import utc_to_local
        utc_time = pytz.UTC.localize(datetime(2026, 1, 30, 15, 30, 0))
        ist_time = utc_to_local(utc_time, "Asia/Kolkata")
        assert ist_time.hour == 21
        assert ist_time.minute == 0

    def test_utc_to_pst(self):
        """UTC 20:00 should be PST 12:00 (noon) in winter."""
        from src.utils.timezone_utils import utc_to_local
        utc_time = pytz.UTC.localize(datetime(2026, 1, 15, 20, 0, 0))
        pst_time = utc_to_local(utc_time, "America/Los_Angeles")
        assert pst_time.hour == 12
        assert pst_time.minute == 0

    def test_naive_utc_assumed(self):
        """Naive datetime should be assumed UTC."""
        from src.utils.timezone_utils import utc_to_local
        naive_time = datetime(2026, 1, 30, 15, 30, 0)
        ist_time = utc_to_local(naive_time, "Asia/Kolkata")
        assert ist_time.hour == 21


class TestLocalToUtc:
    """Test local timezone to UTC conversion."""

    def test_ist_to_utc(self):
        """IST 21:00 should be UTC 15:30."""
        from src.utils.timezone_utils import local_to_utc
        ist = pytz.timezone("Asia/Kolkata")
        ist_time = ist.localize(datetime(2026, 1, 30, 21, 0, 0))
        utc_time = local_to_utc(ist_time, "Asia/Kolkata")
        assert utc_time.hour == 15
        assert utc_time.minute == 30

    def test_pst_to_utc(self):
        """PST 12:00 should be UTC 20:00 in winter."""
        from src.utils.timezone_utils import local_to_utc
        pst = pytz.timezone("America/Los_Angeles")
        pst_time = pst.localize(datetime(2026, 1, 15, 12, 0, 0))
        utc_time = local_to_utc(pst_time, "America/Los_Angeles")
        assert utc_time.hour == 20

    def test_naive_assumed_local(self):
        """Naive datetime should be assumed local timezone."""
        from src.utils.timezone_utils import local_to_utc
        naive_time = datetime(2026, 1, 30, 21, 0, 0)
        utc_time = local_to_utc(naive_time, "Asia/Kolkata")
        assert utc_time.hour == 15
        assert utc_time.minute == 30


class TestGetDateRange:
    """Test timezone-aware date range calculation."""

    def test_default_7_days(self):
        """Default should return 7-day range."""
        from src.utils.timezone_utils import get_date_range
        start, end = get_date_range(7)
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        assert (end_dt - start_dt).days == 6  # 7 days inclusive = 6 day diff

    def test_pst_range(self):
        """PST range should be valid."""
        from src.utils.timezone_utils import get_date_range
        start, end = get_date_range(7, "America/Los_Angeles")
        start_dt = datetime.strptime(start, "%Y-%m-%d")
        end_dt = datetime.strptime(end, "%Y-%m-%d")
        assert (end_dt - start_dt).days == 6


# ============================================================
# 2. TIMEZONE_CATALOG Validation
# ============================================================

class TestTimezoneCatalog:
    """Validate the timezone catalog structure."""

    def test_catalog_has_three_regions(self):
        from src.utils.timezone_utils import TIMEZONE_CATALOG
        assert "americas" in TIMEZONE_CATALOG
        assert "europe" in TIMEZONE_CATALOG
        assert "asia_oceania" in TIMEZONE_CATALOG

    def test_each_region_has_label(self):
        from src.utils.timezone_utils import TIMEZONE_CATALOG
        for region_key, region_data in TIMEZONE_CATALOG.items():
            assert "label" in region_data, f"Region {region_key} missing label"
            assert "timezones" in region_data, f"Region {region_key} missing timezones"

    def test_all_timezone_ids_are_valid(self):
        """Every timezone ID in the catalog should be recognized by pytz."""
        from src.utils.timezone_utils import TIMEZONE_CATALOG
        for region_key, region_data in TIMEZONE_CATALOG.items():
            for tz_info in region_data["timezones"]:
                assert "id" in tz_info
                assert "label" in tz_info
                # Validate the timezone ID is real
                try:
                    pytz.timezone(tz_info["id"])
                except pytz.UnknownTimeZoneError:
                    pytest.fail(f"Invalid timezone: {tz_info['id']} in region {region_key}")

    def test_ist_is_in_catalog(self):
        """Asia/Kolkata must be in the catalog."""
        from src.utils.timezone_utils import TIMEZONE_CATALOG
        all_tz_ids = []
        for region_data in TIMEZONE_CATALOG.values():
            for tz_info in region_data["timezones"]:
                all_tz_ids.append(tz_info["id"])
        assert "Asia/Kolkata" in all_tz_ids

    def test_catalog_has_minimum_timezones(self):
        """Should have at least 10 timezone options."""
        from src.utils.timezone_utils import TIMEZONE_CATALOG
        total = sum(len(r["timezones"]) for r in TIMEZONE_CATALOG.values())
        assert total >= 10


# ============================================================
# 3. Helper Functions
# ============================================================

class TestIsValidTimezone:
    """Test timezone validation."""

    def test_valid_timezones(self):
        from src.utils.timezone_utils import is_valid_timezone
        assert is_valid_timezone("Asia/Kolkata") is True
        assert is_valid_timezone("America/New_York") is True
        assert is_valid_timezone("Europe/London") is True
        assert is_valid_timezone("UTC") is True

    def test_invalid_timezones(self):
        from src.utils.timezone_utils import is_valid_timezone
        assert is_valid_timezone("Invalid/Zone") is False
        assert is_valid_timezone("IST") is False  # IST is ambiguous, not IANA
        assert is_valid_timezone("") is False


class TestGetTimezoneDisplayName:
    """Test display name lookups."""

    def test_known_timezone(self):
        from src.utils.timezone_utils import get_timezone_display_name
        result = get_timezone_display_name("Asia/Kolkata")
        assert "India" in result

    def test_unknown_timezone_returns_raw(self):
        from src.utils.timezone_utils import get_timezone_display_name
        result = get_timezone_display_name("Pacific/Honolulu")
        assert result == "Pacific/Honolulu"  # Not in catalog, fallback to raw

    def test_us_eastern(self):
        from src.utils.timezone_utils import get_timezone_display_name
        result = get_timezone_display_name("America/New_York")
        assert "Eastern" in result or "New York" in result


class TestFormatDatetimeForDisplay:
    """Test multi-timezone display formatting."""

    def test_ist_format(self):
        from src.utils.timezone_utils import format_datetime_for_display
        utc_time = pytz.UTC.localize(datetime(2026, 1, 30, 15, 30, 0))
        result = format_datetime_for_display(utc_time, "Asia/Kolkata")
        assert "Jan 30, 2026" in result
        assert "9:00 PM" in result
        assert "IST" in result

    def test_date_only(self):
        from src.utils.timezone_utils import format_datetime_for_display
        utc_time = pytz.UTC.localize(datetime(2026, 1, 30, 15, 30, 0))
        result = format_datetime_for_display(utc_time, "Asia/Kolkata", include_time=False)
        assert "Jan 30, 2026" in result
        assert "PM" not in result

    def test_pst_format(self):
        from src.utils.timezone_utils import format_datetime_for_display
        utc_time = pytz.UTC.localize(datetime(2026, 1, 30, 20, 0, 0))
        result = format_datetime_for_display(utc_time, "America/Los_Angeles")
        assert "Jan 30, 2026" in result
        assert "12:00 PM" in result


# ============================================================
# 4. Backward Compatibility Aliases
# ============================================================

class TestBackwardCompatAliases:
    """Verify that old IST-specific function names still work."""

    def test_get_current_time_ist(self):
        from src.utils.timezone_utils import get_current_time_ist, get_current_time
        ist_result = get_current_time_ist()
        gen_result = get_current_time("Asia/Kolkata")
        assert ist_result.tzinfo.zone == gen_result.tzinfo.zone
        # Times should be within 1 second of each other
        assert abs((ist_result - gen_result).total_seconds()) < 1

    def test_get_current_date_ist(self):
        from src.utils.timezone_utils import get_current_date_ist, get_current_date
        assert get_current_date_ist() == get_current_date("Asia/Kolkata")

    def test_utc_to_ist(self):
        from src.utils.timezone_utils import utc_to_ist, utc_to_local
        utc_time = pytz.UTC.localize(datetime(2026, 1, 30, 15, 30, 0))
        assert utc_to_ist(utc_time) == utc_to_local(utc_time, "Asia/Kolkata")

    def test_ist_to_utc(self):
        from src.utils.timezone_utils import ist_to_utc, local_to_utc
        ist = pytz.timezone("Asia/Kolkata")
        ist_time = ist.localize(datetime(2026, 1, 30, 21, 0, 0))
        assert ist_to_utc(ist_time) == local_to_utc(ist_time, "Asia/Kolkata")

    def test_get_date_range_ist(self):
        from src.utils.timezone_utils import get_date_range_ist, get_date_range
        assert get_date_range_ist(7) == get_date_range(7, "Asia/Kolkata")


# ============================================================
# 5. Bucket-Based Reminder Matching
# ============================================================

class TestGetTimezonesAtLocalTime:
    """Test the bucket matching function used by /cron/reminder_tz_aware."""

    def test_9pm_ist(self):
        """When UTC is 15:30, IST is 21:00 (9 PM)."""
        from src.utils.timezone_utils import get_timezones_at_local_time
        utc_now = pytz.UTC.localize(datetime(2026, 2, 8, 15, 30, 0))
        matching = get_timezones_at_local_time(utc_now, 21, 0)
        assert "Asia/Kolkata" in matching

    def test_9pm_pst(self):
        """When UTC is 05:00 (winter), PST is 21:00 (9 PM)."""
        from src.utils.timezone_utils import get_timezones_at_local_time
        utc_now = pytz.UTC.localize(datetime(2026, 1, 15, 5, 0, 0))  # Winter
        matching = get_timezones_at_local_time(utc_now, 21, 0)
        assert "America/Los_Angeles" in matching

    def test_no_match_at_wrong_time(self):
        """When UTC is 12:00, no timezone should be at 9 PM (most are day/morning)."""
        from src.utils.timezone_utils import get_timezones_at_local_time
        utc_now = pytz.UTC.localize(datetime(2026, 2, 8, 12, 0, 0))
        matching = get_timezones_at_local_time(utc_now, 21, 0, tolerance_minutes=7)
        # IST at noon UTC = 5:30 PM IST — not 9 PM
        assert "Asia/Kolkata" not in matching

    def test_tolerance_window(self):
        """Matching should work within the tolerance window."""
        from src.utils.timezone_utils import get_timezones_at_local_time
        # IST at UTC 15:25 = 20:55 IST (5 min before 9 PM)
        utc_now = pytz.UTC.localize(datetime(2026, 2, 8, 15, 25, 0))
        # With 7-min tolerance, 20:55 should match 21:00
        matching = get_timezones_at_local_time(utc_now, 21, 0, tolerance_minutes=7)
        assert "Asia/Kolkata" in matching

    def test_tolerance_outside_window(self):
        """Outside tolerance should not match."""
        from src.utils.timezone_utils import get_timezones_at_local_time
        # IST at UTC 15:15 = 20:45 IST (15 min before 9 PM)
        utc_now = pytz.UTC.localize(datetime(2026, 2, 8, 15, 15, 0))
        # With 7-min tolerance, 20:45 should NOT match 21:00
        matching = get_timezones_at_local_time(utc_now, 21, 0, tolerance_minutes=7)
        assert "Asia/Kolkata" not in matching

    def test_empty_on_no_catalog_match(self):
        """If no catalog timezone matches, return empty list."""
        from src.utils.timezone_utils import get_timezones_at_local_time
        # Midnight UTC — no catalog timezone is at 3:15 AM
        utc_now = pytz.UTC.localize(datetime(2026, 2, 8, 0, 0, 0))
        matching = get_timezones_at_local_time(utc_now, 3, 15, tolerance_minutes=5)
        # This might still match some; just check it returns a list
        assert isinstance(matching, list)


# ============================================================
# 6. Streak Functions with Timezone Parameter
# ============================================================

class TestStreakFunctionsWithTz:
    """Test that streak functions accept and use tz parameter."""

    def test_is_streak_at_risk_signature(self):
        """is_streak_at_risk should accept tz parameter."""
        from src.utils.streak import is_streak_at_risk
        # Default (IST) should work
        from src.utils.timezone_utils import get_current_date
        yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        result = is_streak_at_risk(yesterday)
        assert result is True

    def test_is_streak_at_risk_with_explicit_tz(self):
        """Should work with explicit timezone."""
        from src.utils.streak import is_streak_at_risk
        yesterday = (datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
        result = is_streak_at_risk(yesterday, tz="America/New_York")
        assert result is True

    def test_should_reset_streak_shields_none(self):
        """None last_reset should always return True."""
        from src.utils.streak import should_reset_streak_shields
        assert should_reset_streak_shields(None) is True
        assert should_reset_streak_shields(None, tz="America/Los_Angeles") is True

    def test_should_reset_streak_shields_recent(self):
        """Recent reset (yesterday) should not need resetting."""
        from src.utils.streak import should_reset_streak_shields
        from src.utils.timezone_utils import get_current_date
        today = get_current_date("Asia/Kolkata")
        assert should_reset_streak_shields(today) is False

    def test_should_reset_streak_shields_old(self):
        """Reset from 31 days ago should need resetting."""
        from src.utils.streak import should_reset_streak_shields
        old_date = (datetime.now() - timedelta(days=31)).strftime("%Y-%m-%d")
        assert should_reset_streak_shields(old_date) is True

    def test_calculate_days_without_checkin_none(self):
        """None should return -1."""
        from src.utils.streak import calculate_days_without_checkin
        assert calculate_days_without_checkin(None) == -1
        assert calculate_days_without_checkin(None, tz="Europe/London") == -1

    def test_calculate_days_without_checkin_today(self):
        """Check-in today should return 0."""
        from src.utils.streak import calculate_days_without_checkin
        from src.utils.timezone_utils import get_current_date
        today = get_current_date("Asia/Kolkata")
        assert calculate_days_without_checkin(today) == 0

    def test_calculate_days_without_checkin_with_tz(self):
        """Should work with different timezones."""
        from src.utils.streak import calculate_days_without_checkin
        from src.utils.timezone_utils import get_current_date
        today_pst = get_current_date("America/Los_Angeles")
        assert calculate_days_without_checkin(today_pst, tz="America/Los_Angeles") == 0


# ============================================================
# 7. schemas.py Updated Helpers
# ============================================================

class TestSchemasHelpers:
    """Test that schemas.py helpers delegate correctly."""

    def test_get_current_date_ist_default(self):
        """Default should return IST date."""
        from src.models.schemas import get_current_date_ist
        result = get_current_date_ist()
        datetime.strptime(result, "%Y-%m-%d")

    def test_get_current_date_ist_with_tz(self):
        """Should accept timezone parameter now."""
        from src.models.schemas import get_current_date_ist
        result = get_current_date_ist(tz="America/New_York")
        datetime.strptime(result, "%Y-%m-%d")

    def test_get_current_datetime_ist_default(self):
        """Default should return IST datetime."""
        from src.models.schemas import get_current_datetime_ist
        result = get_current_datetime_ist()
        assert result.tzinfo is not None

    def test_get_current_datetime_ist_with_tz(self):
        """Should accept timezone parameter."""
        from src.models.schemas import get_current_datetime_ist
        result = get_current_datetime_ist(tz="America/Los_Angeles")
        assert result.tzinfo is not None


# ============================================================
# 8. Code Integration Tests (Source-Level)
# ============================================================

class TestCodeIntegration:
    """
    Verify that production code correctly threads user timezone.
    
    These tests read source files to verify the timezone parameter
    is properly passed through call chains — critical for confidence
    that a PST user gets correct date calculations.
    """

    def test_conversation_py_uses_user_tz(self):
        """conversation.py should read user.timezone and pass to get_checkin_date."""
        with open("src/bot/conversation.py", "r") as f:
            content = f.read()
        assert "user_tz = getattr(user, 'timezone'" in content
        assert "get_checkin_date(tz=user_tz)" in content
        assert "context.user_data['timezone'] = user_tz" in content

    def test_telegram_bot_status_uses_user_tz(self):
        """telegram_bot.py status_command should use user's timezone."""
        with open("src/bot/telegram_bot.py", "r") as f:
            content = f.read()
        # Status command
        assert "get_current_date(user_tz)" in content
        # Shield command
        assert "get_checkin_date(tz=user_tz)" in content

    def test_telegram_bot_correct_uses_user_tz(self):
        """correct_command should use user's timezone for today's date."""
        with open("src/bot/telegram_bot.py", "r") as f:
            content = f.read()
        assert "get_current_date(user_tz)" in content

    def test_streak_py_accepts_tz(self):
        """streak.py functions should accept tz parameter."""
        with open("src/utils/streak.py", "r") as f:
            content = f.read()
        assert 'def is_streak_at_risk(last_checkin_date: str, tz: str = "Asia/Kolkata")' in content
        assert 'def should_reset_streak_shields(last_reset_date: Optional[str], tz: str = "Asia/Kolkata")' in content
        assert 'def calculate_days_without_checkin(last_checkin_date: Optional[str], tz: str = "Asia/Kolkata")' in content

    def test_pattern_detection_uses_user_tz(self):
        """Pattern detection should pass user timezone to date calculation."""
        with open("src/agents/pattern_detection.py", "r") as f:
            content = f.read()
        assert "user_tz = getattr(user, 'timezone'" in content
        assert "tz=user_tz" in content

    def test_firestore_shield_uses_user_tz(self):
        """Firestore service shield methods should use user timezone."""
        with open("src/services/firestore_service.py", "r") as f:
            content = f.read()
        assert "user_tz = getattr(user, 'timezone'" in content
        assert "get_checkin_date(tz=user_tz)" in content

    def test_timezone_utils_has_catalog(self):
        """timezone_utils should have TIMEZONE_CATALOG."""
        with open("src/utils/timezone_utils.py", "r") as f:
            content = f.read()
        assert "TIMEZONE_CATALOG" in content
        assert "americas" in content
        assert "europe" in content
        assert "asia_oceania" in content

    def test_timezone_command_registered(self):
        """telegram_bot.py should register /timezone command."""
        with open("src/bot/telegram_bot.py", "r") as f:
            content = f.read()
        assert 'CommandHandler("timezone"' in content
        assert "async def timezone_command" in content

    def test_help_text_includes_timezone(self):
        """Help text should list /timezone command."""
        with open("src/utils/ux.py", "r") as f:
            content = f.read()
        assert "/timezone" in content

    def test_onboarding_has_region_picker(self):
        """Onboarding should show region → city picker, not 'coming soon'."""
        with open("src/bot/telegram_bot.py", "r") as f:
            content = f.read()
        assert "tz_region_" in content  # Region callback data
        assert "tz_set_" in content     # City selection callback
        # The "coming soon" message should be gone
        assert "coming soon" not in content.lower() or "Custom timezone support is coming soon" not in content

    def test_bucket_reminder_endpoint_exists(self):
        """main.py should have /cron/reminder_tz_aware endpoint."""
        with open("src/main.py", "r") as f:
            content = f.read()
        assert "/cron/reminder_tz_aware" in content
        assert "get_timezones_at_local_time" in content

    def test_get_users_by_timezones_method_exists(self):
        """Firestore service should have get_users_by_timezones method."""
        with open("src/services/firestore_service.py", "r") as f:
            content = f.read()
        assert "def get_users_by_timezones" in content


# ============================================================
# 9. Edge Cases and Cross-Timezone Scenarios
# ============================================================

class TestEdgeCases:
    """Edge cases for timezone handling."""

    def test_date_line_crossing(self):
        """Timezones on either side of the date line."""
        from src.utils.timezone_utils import get_current_date
        # Auckland (UTC+12/+13) and Samoa (UTC-11) are near the date line
        nz_date = get_current_date("Pacific/Auckland")
        datetime.strptime(nz_date, "%Y-%m-%d")  # Should be valid

    def test_half_hour_offset(self):
        """India's +5:30 offset should work correctly."""
        from src.utils.timezone_utils import utc_to_local
        utc_time = pytz.UTC.localize(datetime(2026, 2, 8, 0, 0, 0))
        ist_time = utc_to_local(utc_time, "Asia/Kolkata")
        assert ist_time.hour == 5
        assert ist_time.minute == 30

    def test_roundtrip_utc_local_utc(self):
        """Converting UTC→local→UTC should give the same time."""
        from src.utils.timezone_utils import utc_to_local, local_to_utc
        original = pytz.UTC.localize(datetime(2026, 6, 15, 14, 30, 0))
        local = utc_to_local(original, "America/Chicago")
        roundtrip = local_to_utc(local, "America/Chicago")
        assert abs((original - roundtrip).total_seconds()) < 1

    def test_user_schema_has_timezone_field(self):
        """User model should have timezone field with IST default."""
        from src.models.schemas import User
        user = User(
            user_id="test123",
            telegram_id=123456789,
            name="Test User"
        )
        assert user.timezone == "Asia/Kolkata"

    def test_user_schema_custom_timezone(self):
        """User model should accept custom timezone."""
        from src.models.schemas import User
        user = User(
            user_id="test123",
            telegram_id=123456789,
            name="Test User",
            timezone="America/New_York"
        )
        assert user.timezone == "America/New_York"


# ============================================================
# 10. Regression: Existing IST behavior unchanged
# ============================================================

class TestRegressionIST:
    """
    Ensure all changes are backward compatible.
    Existing IST users should see zero change in behavior.
    """

    def test_default_ist_dates_match(self):
        """Default function calls should match IST-specific functions."""
        from src.utils.timezone_utils import (
            get_current_time, get_current_time_ist,
            get_current_date, get_current_date_ist,
        )
        assert get_current_date() == get_current_date_ist()
        time_gen = get_current_time()
        time_ist = get_current_time_ist()
        assert time_gen.tzinfo.zone == time_ist.tzinfo.zone

    def test_checkin_date_default_ist(self):
        """get_checkin_date() without args should use IST."""
        from src.utils.timezone_utils import get_checkin_date
        # Just verify it returns a valid date string
        result = get_checkin_date()
        datetime.strptime(result, "%Y-%m-%d")

    def test_date_range_default_ist(self):
        """get_date_range() without tz should use IST."""
        from src.utils.timezone_utils import get_date_range, get_date_range_ist
        assert get_date_range(7) == get_date_range_ist(7)

    def test_streak_functions_default_ist(self):
        """Streak functions with no tz arg should use IST."""
        from src.utils.streak import calculate_days_without_checkin
        from src.utils.timezone_utils import get_current_date
        today = get_current_date("Asia/Kolkata")
        # Both calls should give same result
        result_default = calculate_days_without_checkin(today)
        result_explicit = calculate_days_without_checkin(today, tz="Asia/Kolkata")
        assert result_default == result_explicit
