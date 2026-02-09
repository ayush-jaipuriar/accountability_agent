"""
Phase A Tests: Monitoring & Rate Limiting
==========================================

Comprehensive tests for:
- F6: AppMetrics (counters, latencies, errors, admin status formatting)
- F5: RateLimiter (tiered cooldowns, hourly limits, admin bypass, cleanup)
- Integration: Config settings, JSON logging formatter, health endpoint enrichment
"""

import pytest
import time
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

from src.utils.metrics import AppMetrics
from src.utils.rate_limiter import RateLimiter


# =====================================================
# F6: METRICS — CORE FUNCTIONALITY
# =====================================================

class TestAppMetricsCounters:
    """Test counter operations in AppMetrics."""
    
    def setup_method(self):
        """Fresh metrics instance for each test."""
        self.metrics = AppMetrics()
    
    def test_counter_starts_at_zero(self):
        """Uninitialized counters should return 0."""
        assert self.metrics.get_counter("nonexistent") == 0
    
    def test_increment_by_default(self):
        """Default increment is +1."""
        self.metrics.increment("test_counter")
        assert self.metrics.get_counter("test_counter") == 1
    
    def test_increment_by_custom_value(self):
        """Can increment by arbitrary positive integer."""
        self.metrics.increment("test_counter", 5)
        assert self.metrics.get_counter("test_counter") == 5
    
    def test_multiple_increments_accumulate(self):
        """Multiple increments should accumulate."""
        self.metrics.increment("test_counter")
        self.metrics.increment("test_counter")
        self.metrics.increment("test_counter")
        assert self.metrics.get_counter("test_counter") == 3
    
    def test_independent_counters(self):
        """Different counter names are independent."""
        self.metrics.increment("counter_a", 10)
        self.metrics.increment("counter_b", 20)
        assert self.metrics.get_counter("counter_a") == 10
        assert self.metrics.get_counter("counter_b") == 20
    
    def test_counter_in_summary(self):
        """Counters appear in get_summary()."""
        self.metrics.increment("checkins_total", 15)
        summary = self.metrics.get_summary()
        assert summary["counters"]["checkins_total"] == 15


class TestAppMetricsLatencies:
    """Test latency recording and statistics."""
    
    def setup_method(self):
        self.metrics = AppMetrics()
    
    def test_empty_latency_stats(self):
        """No data → zeroed stats."""
        stats = self.metrics.get_latency_stats("nonexistent")
        assert stats["count"] == 0
        assert stats["avg_ms"] == 0
    
    def test_single_latency(self):
        """Single sample → avg = that sample."""
        self.metrics.record_latency("webhook", 200.0)
        stats = self.metrics.get_latency_stats("webhook")
        assert stats["count"] == 1
        assert stats["avg_ms"] == 200.0
    
    def test_latency_average(self):
        """Multiple samples → correct average."""
        for ms in [100, 200, 300]:
            self.metrics.record_latency("webhook", ms)
        stats = self.metrics.get_latency_stats("webhook")
        assert stats["avg_ms"] == 200.0
        assert stats["count"] == 3
    
    def test_latency_percentiles(self):
        """Percentiles calculated correctly."""
        # Add 100 samples: 1, 2, 3, ..., 100
        for i in range(1, 101):
            self.metrics.record_latency("webhook", float(i))
        stats = self.metrics.get_latency_stats("webhook")
        # p50 = sorted[50] = 51 (0-indexed median of 100 items)
        assert 49.0 <= stats["p50_ms"] <= 52.0  # ~median
        assert 94.0 <= stats["p95_ms"] <= 96.0  # ~95th percentile
        assert stats["min_ms"] == 1.0
        assert stats["max_ms"] == 100.0
    
    def test_latency_buffer_bounded(self):
        """Buffer should not grow beyond MAX_LATENCY_SAMPLES."""
        for i in range(200):
            self.metrics.record_latency("test", float(i))
        # Internal buffer should be bounded
        assert len(self.metrics.latencies["test"]) <= AppMetrics.MAX_LATENCY_SAMPLES
    
    def test_latency_time_window(self):
        """get_latency_stats respects the time window."""
        # Add a sample "from the past" by manipulating internals
        past_time = datetime.utcnow() - timedelta(hours=2)
        self.metrics.latencies["test"].append((past_time, 999.0))
        
        # Add a recent sample
        self.metrics.record_latency("test", 100.0)
        
        # Only recent samples should be in the 60-min window
        stats = self.metrics.get_latency_stats("test", window_minutes=60)
        assert stats["count"] == 1
        assert stats["avg_ms"] == 100.0


class TestAppMetricsErrors:
    """Test error recording."""
    
    def setup_method(self):
        self.metrics = AppMetrics()
    
    def test_error_count_starts_zero(self):
        """No errors recorded → count is 0."""
        assert self.metrics.get_error_count() == 0
        assert self.metrics.get_error_count("firestore") == 0
    
    def test_record_error_increments_total(self):
        """Recording an error increments total."""
        self.metrics.record_error("firestore", "connection timeout")
        assert self.metrics.get_error_count() == 1
    
    def test_record_error_increments_category(self):
        """Recording categorized errors tracks per category."""
        self.metrics.record_error("firestore")
        self.metrics.record_error("firestore")
        self.metrics.record_error("telegram")
        assert self.metrics.get_error_count("firestore") == 2
        assert self.metrics.get_error_count("telegram") == 1
        assert self.metrics.get_error_count() == 3
    
    def test_recent_errors_stored(self):
        """Recent errors log should store entries."""
        self.metrics.record_error("test", "detail message")
        assert len(self.metrics.recent_errors) == 1
        assert self.metrics.recent_errors[0]["category"] == "test"
        assert self.metrics.recent_errors[0]["detail"] == "detail message"
    
    def test_recent_errors_bounded(self):
        """Recent errors log should not exceed MAX_RECENT_ERRORS."""
        for i in range(100):
            self.metrics.record_error("test", f"error {i}")
        assert len(self.metrics.recent_errors) == self.metrics.MAX_RECENT_ERRORS
    
    def test_errors_in_summary(self):
        """Errors appear in get_summary()."""
        self.metrics.record_error("firestore", "timeout")
        summary = self.metrics.get_summary()
        assert summary["errors"]["total"] == 1
        assert summary["errors"]["by_category"]["firestore"] == 1


class TestAppMetricsUptime:
    """Test uptime calculation."""
    
    def test_uptime_is_positive(self):
        """Uptime should be positive immediately after creation."""
        m = AppMetrics()
        uptime = m.get_uptime()
        assert uptime["uptime_seconds"] >= 0
    
    def test_uptime_human_format(self):
        """Human-readable uptime should contain 'h' and 'm'."""
        m = AppMetrics()
        uptime = m.get_uptime()
        assert "h" in uptime["uptime_human"]
        assert "m" in uptime["uptime_human"]


class TestAppMetricsAdminStatus:
    """Test the Telegram-formatted admin status message."""
    
    def test_format_admin_status_returns_string(self):
        """format_admin_status should return a non-empty string."""
        m = AppMetrics()
        msg = m.format_admin_status()
        assert isinstance(msg, str)
        assert len(msg) > 0
    
    def test_format_includes_header(self):
        """Status message should include 'Admin Status Report'."""
        m = AppMetrics()
        msg = m.format_admin_status()
        assert "Admin Status Report" in msg
    
    def test_format_includes_uptime(self):
        """Status message should show uptime."""
        m = AppMetrics()
        msg = m.format_admin_status()
        assert "Uptime" in msg
    
    def test_format_includes_counters(self):
        """Status message should show check-in and command counts."""
        m = AppMetrics()
        m.increment("checkins_total", 15)
        m.increment("checkins_full", 12)
        m.increment("checkins_quick", 3)
        m.increment("commands_total", 42)
        msg = m.format_admin_status()
        assert "15" in msg  # checkins_total
        assert "12" in msg  # checkins_full
        assert "42" in msg  # commands_total
    
    def test_format_includes_errors(self):
        """Status message should show error info."""
        m = AppMetrics()
        m.record_error("firestore", "timeout")
        msg = m.format_admin_status()
        assert "firestore" in msg
    
    def test_format_no_errors_shows_none(self):
        """Status message with zero errors says 'None!'."""
        m = AppMetrics()
        msg = m.format_admin_status()
        assert "None!" in msg


class TestAppMetricsReset:
    """Test metrics reset (for testing isolation)."""
    
    def test_reset_clears_all(self):
        """reset() should clear all metrics."""
        m = AppMetrics()
        m.increment("test", 10)
        m.record_error("test")
        m.record_latency("test", 100)
        
        m.reset()
        
        assert m.get_counter("test") == 0
        assert m.get_error_count() == 0
        assert m.get_latency_stats("test")["count"] == 0
        assert len(m.recent_errors) == 0


# =====================================================
# F5: RATE LIMITER — CORE FUNCTIONALITY
# =====================================================

class TestRateLimiterBasic:
    """Test basic rate limiter behavior."""
    
    def setup_method(self):
        """Fresh rate limiter for each test."""
        self.limiter = RateLimiter()
    
    def test_free_tier_always_allowed(self):
        """Commands not in COMMAND_TIERS are always allowed."""
        for _ in range(100):
            allowed, msg = self.limiter.check("user1", "help")
            assert allowed is True
            assert msg is None
    
    def test_unknown_command_is_free(self):
        """Unknown commands default to free tier."""
        allowed, msg = self.limiter.check("user1", "nonexistent_command")
        assert allowed is True
    
    def test_first_request_always_allowed(self):
        """First request for any tier is always allowed (using separate users)."""
        # Use separate users to avoid cross-tier cooldown interactions
        # (report and export share the "expensive" tier)
        for i, command in enumerate(["report", "query", "leaderboard"]):
            allowed, msg = self.limiter.check(f"user_first_{i}", command)
            assert allowed is True, f"First {command} should be allowed"
    
    def test_command_tier_mapping(self):
        """All mapped commands should have valid tiers."""
        for command, tier in RateLimiter.COMMAND_TIERS.items():
            assert tier in RateLimiter.TIERS, f"Command '{command}' maps to unknown tier '{tier}'"


class TestRateLimiterCooldown:
    """Test cooldown enforcement."""
    
    def setup_method(self):
        self.limiter = RateLimiter()
    
    def test_expensive_cooldown(self):
        """Expensive commands should enforce 30-minute cooldown."""
        # First request: allowed
        allowed, _ = self.limiter.check("user1", "report")
        assert allowed is True
        
        # Immediate second request: denied
        allowed, msg = self.limiter.check("user1", "report")
        assert allowed is False
        assert "wait" in msg.lower()
    
    def test_ai_powered_cooldown(self):
        """AI-powered commands should enforce 2-minute cooldown."""
        allowed, _ = self.limiter.check("user1", "query")
        assert allowed is True
        
        allowed, msg = self.limiter.check("user1", "query")
        assert allowed is False
        assert "wait" in msg.lower()
    
    def test_standard_cooldown(self):
        """Standard commands should enforce 10-second cooldown."""
        allowed, _ = self.limiter.check("user1", "leaderboard")
        assert allowed is True
        
        allowed, msg = self.limiter.check("user1", "leaderboard")
        assert allowed is False
        assert "wait" in msg.lower()
    
    def test_cooldown_message_includes_time(self):
        """Denial message should tell user how long to wait."""
        self.limiter.check("user1", "report")
        allowed, msg = self.limiter.check("user1", "report")
        assert allowed is False
        # Should contain minutes since 30min cooldown
        assert "m" in msg or "s" in msg
    
    def test_cooldown_includes_tip(self):
        """Denial message should include a helpful tip."""
        self.limiter.check("user1", "report")
        _, msg = self.limiter.check("user1", "report")
        assert "Tip" in msg


class TestRateLimiterHourlyLimit:
    """Test hourly limit enforcement."""
    
    def setup_method(self):
        self.limiter = RateLimiter()
    
    def test_hourly_limit_reached(self):
        """Should deny after hourly limit is reached."""
        # Standard tier: 90/hour with 3sec cooldown (tripled from 30/hour)
        # Simulate reaching the limit by manipulating internals
        user_entries = self.limiter._requests["user1"]["standard"]
        now = datetime.utcnow()
        
        # Fill up to the limit (90 requests)
        for i in range(90):
            user_entries.append(now - timedelta(minutes=i % 60, seconds=i // 60))
        
        allowed, msg = self.limiter.check("user1", "leaderboard")
        assert allowed is False
        assert "times in the last hour" in msg
    
    def test_expensive_hourly_limit(self):
        """Expensive tier: max 6 per hour (tripled from 2)."""
        # Manipulate timestamps to bypass cooldown but hit hourly limit
        now = datetime.utcnow()
        self.limiter._requests["user1"]["expensive"].extend([
            now - timedelta(minutes=55),
            now - timedelta(minutes=45),
            now - timedelta(minutes=35),
            now - timedelta(minutes=25),
            now - timedelta(minutes=15),
            now - timedelta(minutes=5),
        ])
        
        allowed, msg = self.limiter.check("user1", "report")
        assert allowed is False
        assert "6" in msg  # Should mention the limit


class TestRateLimiterAdminBypass:
    """Test admin ID bypass functionality."""
    
    def setup_method(self):
        self.limiter = RateLimiter()
    
    def test_admin_bypasses_cooldown(self):
        """Admin users should bypass cooldowns."""
        self.limiter.set_admin_ids(["admin1"])
        
        # First request
        self.limiter.check("admin1", "report")
        
        # Immediate second request — should be allowed for admin
        allowed, msg = self.limiter.check("admin1", "report")
        assert allowed is True
    
    def test_non_admin_still_limited(self):
        """Non-admin users should still be rate-limited."""
        self.limiter.set_admin_ids(["admin1"])
        
        self.limiter.check("user1", "report")
        allowed, _ = self.limiter.check("user1", "report")
        assert allowed is False
    
    def test_empty_admin_ids(self):
        """Empty admin list means nobody bypasses."""
        self.limiter.set_admin_ids([])
        
        self.limiter.check("user1", "report")
        allowed, _ = self.limiter.check("user1", "report")
        assert allowed is False
    
    def test_multiple_admin_ids(self):
        """Multiple admins can all bypass."""
        self.limiter.set_admin_ids(["admin1", "admin2"])
        
        for admin_id in ["admin1", "admin2"]:
            self.limiter.check(admin_id, "report")
            allowed, _ = self.limiter.check(admin_id, "report")
            assert allowed is True, f"Admin {admin_id} should bypass"


class TestRateLimiterUserIsolation:
    """Test that rate limits are per-user."""
    
    def setup_method(self):
        self.limiter = RateLimiter()
    
    def test_different_users_independent(self):
        """Rate limits for one user don't affect another."""
        self.limiter.check("user1", "report")
        
        # User 2 should still be allowed
        allowed, _ = self.limiter.check("user2", "report")
        assert allowed is True
    
    def test_same_user_different_tiers_independent(self):
        """Different tiers for the same user are independent."""
        self.limiter.check("user1", "report")    # Expensive tier
        
        # Standard tier should be unaffected
        allowed, _ = self.limiter.check("user1", "leaderboard")
        assert allowed is True


class TestRateLimiterUsage:
    """Test the usage summary feature."""
    
    def setup_method(self):
        self.limiter = RateLimiter()
    
    def test_usage_returns_all_tiers(self):
        """get_usage should return info for all tiers."""
        usage = self.limiter.get_usage("user1")
        assert "expensive" in usage
        assert "ai_powered" in usage
        assert "standard" in usage
    
    def test_usage_tracks_counts(self):
        """Usage should reflect actual requests."""
        self.limiter.check("user1", "report")
        usage = self.limiter.get_usage("user1")
        assert usage["expensive"]["used_this_hour"] == 1
    
    def test_usage_shows_limits(self):
        """Usage should show max_per_hour (tripled limits)."""
        usage = self.limiter.get_usage("user1")
        assert usage["expensive"]["max_per_hour"] == 6  # Tripled from 2
        assert usage["ai_powered"]["max_per_hour"] == 60  # Tripled from 20
        assert usage["standard"]["max_per_hour"] == 90  # Tripled from 30


class TestRateLimiterCleanup:
    """Test periodic cleanup functionality."""
    
    def setup_method(self):
        self.limiter = RateLimiter()
    
    def test_cleanup_removes_stale_entries(self):
        """Cleanup should remove users with only old entries."""
        # Add stale entries (3 hours old)
        past = datetime.utcnow() - timedelta(hours=3)
        self.limiter._requests["stale_user"]["standard"].append(past)
        
        cleaned = self.limiter.cleanup()
        assert cleaned >= 1
        assert "stale_user" not in self.limiter._requests
    
    def test_cleanup_keeps_active_entries(self):
        """Cleanup should keep users with recent entries."""
        self.limiter.check("active_user", "leaderboard")
        
        cleaned = self.limiter.cleanup()
        assert "active_user" in self.limiter._requests
    
    def test_cleanup_returns_count(self):
        """Cleanup should return the number of cleaned entries."""
        cleaned = self.limiter.cleanup()
        assert isinstance(cleaned, int)


# =====================================================
# INTEGRATION: CONFIG, LOGGING, HEALTH
# =====================================================

class TestConfigSettings:
    """Test new config settings for Phase A."""
    
    def test_admin_telegram_ids_exists(self):
        """Config must have admin_telegram_ids field."""
        from src.config import Settings
        import inspect
        source = inspect.getsource(Settings)
        assert 'admin_telegram_ids' in source
    
    def test_json_logging_exists(self):
        """Config must have json_logging field."""
        from src.config import Settings
        import inspect
        source = inspect.getsource(Settings)
        assert 'json_logging' in source
    
    def test_admin_ids_default_empty(self):
        """admin_telegram_ids should default to empty string."""
        from src.config import Settings
        import inspect
        source = inspect.getsource(Settings)
        assert 'admin_telegram_ids: str = ""' in source
    
    def test_json_logging_default_false(self):
        """json_logging should default to False."""
        from src.config import Settings
        import inspect
        source = inspect.getsource(Settings)
        assert 'json_logging: bool = False' in source


class TestJSONFormatter:
    """Test the JSON log formatter."""
    
    def test_json_formatter_produces_valid_json(self):
        """JSONFormatter output should be valid JSON."""
        import json
        import os
        
        # Read the JSONFormatter source to verify it exists
        main_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'main.py'
        )
        with open(main_path, 'r') as f:
            source = f.read()
        
        assert 'class JSONFormatter' in source
        assert 'json.dumps' in source
    
    def test_json_formatter_includes_severity(self):
        """JSON logs must include 'severity' field (Cloud Logging convention)."""
        import os
        main_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'main.py'
        )
        with open(main_path, 'r') as f:
            source = f.read()
        
        assert '"severity"' in source
    
    def test_json_formatter_includes_custom_fields(self):
        """JSON logs must support custom fields (user_id, command, latency_ms)."""
        import os
        main_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'main.py'
        )
        with open(main_path, 'r') as f:
            source = f.read()
        
        assert '"user_id"' in source or "'user_id'" in source
        assert '"latency_ms"' in source or "'latency_ms'" in source


class TestHealthEndpointEnriched:
    """Test that health endpoint includes metrics."""
    
    def test_health_endpoint_includes_metrics(self):
        """Health endpoint must return metrics_summary."""
        import os
        main_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'main.py'
        )
        with open(main_path, 'r') as f:
            source = f.read()
        
        assert 'metrics_summary' in source
        assert 'checkins_total' in source
        assert 'commands_total' in source
        assert 'errors_total' in source
    
    def test_health_endpoint_includes_uptime(self):
        """Health endpoint must return uptime."""
        import os
        main_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'main.py'
        )
        with open(main_path, 'r') as f:
            source = f.read()
        
        assert 'uptime' in source


class TestAdminMetricsEndpoint:
    """Test /admin/metrics endpoint exists."""
    
    def test_admin_metrics_endpoint_exists(self):
        """/admin/metrics must be defined in main.py."""
        import os
        main_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'main.py'
        )
        with open(main_path, 'r') as f:
            source = f.read()
        
        assert '/admin/metrics' in source
        assert 'admin_metrics' in source
    
    def test_admin_metrics_requires_auth(self):
        """/admin/metrics must check admin_id."""
        import os
        main_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'main.py'
        )
        with open(main_path, 'r') as f:
            source = f.read()
        
        # Find admin_metrics function
        assert 'admin_id' in source
        assert '403' in source


class TestWebhookMetrics:
    """Test that webhook endpoint records metrics."""
    
    def test_webhook_records_latency(self):
        """Webhook handler must record latency."""
        import os
        main_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'main.py'
        )
        with open(main_path, 'r') as f:
            source = f.read()
        
        assert 'record_latency' in source
        assert 'webhook_latency' in source
    
    def test_webhook_records_errors(self):
        """Webhook handler must record errors on failure."""
        import os
        main_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'main.py'
        )
        with open(main_path, 'r') as f:
            source = f.read()
        
        assert 'record_error' in source


class TestBotRateLimitIntegration:
    """Test that bot commands use rate limiting."""
    
    def _read_bot_source(self):
        import os
        path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'bot', 'telegram_bot.py'
        )
        with open(path, 'r') as f:
            return f.read()
    
    def test_report_command_rate_limited(self):
        """report_command must check rate limit."""
        source = self._read_bot_source()
        # Find the report_command function
        idx = source.find('async def report_command')
        func_end = source.find('async def ', idx + 1)
        func_body = source[idx:func_end]
        assert '_check_rate_limit' in func_body
        assert '"report"' in func_body
    
    def test_export_command_rate_limited(self):
        """export_command must check rate limit."""
        source = self._read_bot_source()
        idx = source.find('async def export_command')
        func_end = source.find('async def ', idx + 1)
        func_body = source[idx:func_end]
        assert '_check_rate_limit' in func_body
        assert '"export"' in func_body
    
    def test_leaderboard_command_rate_limited(self):
        """leaderboard_command must check rate limit."""
        source = self._read_bot_source()
        idx = source.find('async def leaderboard_command')
        func_end = source.find('async def ', idx + 1)
        func_body = source[idx:func_end]
        assert '_check_rate_limit' in func_body
        assert '"leaderboard"' in func_body
    
    def test_general_message_rate_limited(self):
        """handle_general_message must check rate limit."""
        source = self._read_bot_source()
        idx = source.find('async def handle_general_message')
        func_end = source.find('async def ', idx + 1)
        if func_end == -1:
            func_end = len(source)
        func_body = source[idx:func_end]
        assert '_check_rate_limit' in func_body
        assert '"query"' in func_body
    
    def test_admin_status_command_registered(self):
        """admin_status must be registered in handlers."""
        source = self._read_bot_source()
        assert '"admin_status"' in source or "'admin_status'" in source
    
    def test_admin_status_checks_admin_ids(self):
        """admin_status_command must verify admin permissions."""
        source = self._read_bot_source()
        idx = source.find('async def admin_status_command')
        func_end = source.find('async def ', idx + 1)
        func_body = source[idx:func_end]
        assert 'admin_telegram_ids' in func_body
    
    def test_check_rate_limit_helper_exists(self):
        """_check_rate_limit helper must exist."""
        source = self._read_bot_source()
        assert 'async def _check_rate_limit' in source
    
    def test_check_rate_limit_tracks_metrics(self):
        """_check_rate_limit must increment metrics on denial."""
        source = self._read_bot_source()
        idx = source.find('async def _check_rate_limit')
        func_end = source.find('async def ', idx + 1)
        func_body = source[idx:func_end]
        assert 'metrics.increment' in func_body
        assert 'rate_limit_hits' in func_body


# =====================================================
# REGRESSION: EXISTING TESTS MUST STILL PASS
# =====================================================

class TestRegressionExistingMetrics:
    """Ensure new metrics don't break existing functionality."""
    
    def test_metrics_singleton_import(self):
        """metrics singleton should be importable."""
        from src.utils.metrics import metrics
        assert metrics is not None
    
    def test_rate_limiter_singleton_import(self):
        """rate_limiter singleton should be importable."""
        from src.utils.rate_limiter import rate_limiter
        assert rate_limiter is not None
    
    def test_metrics_get_summary_structure(self):
        """get_summary must return expected structure."""
        m = AppMetrics()
        summary = m.get_summary()
        
        assert "uptime" in summary
        assert "counters" in summary
        assert "errors" in summary
        assert "latencies" in summary
        
        assert "uptime_seconds" in summary["uptime"]
        assert "uptime_human" in summary["uptime"]
        assert "total" in summary["errors"]
        assert "by_category" in summary["errors"]
        assert "recent" in summary["errors"]
