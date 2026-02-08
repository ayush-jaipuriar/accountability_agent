"""
Application Metrics Collector
=============================

In-memory metrics tracking for application health monitoring.

Architecture Concept: Observability Triad
-----------------------------------------
Production systems need three pillars of observability:
1. **Logs** — What happened (events, errors, debug info)
2. **Metrics** — How much (counters, gauges, histograms)
3. **Traces** — How long (request flows, latencies)

This module provides pillar #2 (Metrics). It collects:
- Counters: Total check-ins, commands processed, errors
- Latencies: Webhook processing time, AI response time, Firestore query time
- Error rates: Categorized by source (Telegram, Firestore, AI, etc.)

Design Decisions:
- **In-memory** (no Redis/external store): Acceptable for a single-instance Cloud Run service.
  Metrics reset on deployment/restart, which is fine because:
  1. Restarts are rare (Cloud Run keeps warm instances)
  2. Failing open (allowing on restart) is better than failing closed
  3. Avoids external dependency cost and complexity
- **Thread-safe** via simple operations: Python's GIL makes counter increments atomic.
- **Fixed-size latency buffers**: Keep last 100 entries per metric to bound memory usage.

Usage:
    from src.utils.metrics import metrics

    metrics.increment("checkins_total")
    metrics.record_latency("webhook_latency", 230.5)
    metrics.record_error("firestore")

    summary = metrics.get_summary()
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional


class AppMetrics:
    """
    In-memory application metrics collector.

    Tracks three types of metrics:
    1. Counters — Monotonically increasing values (total events)
    2. Latencies — Timing data with rolling buffer (last N samples)
    3. Errors — Categorized error counts

    All data resets on application restart (by design).
    """

    # Maximum number of latency samples to keep per metric.
    # 100 is enough for meaningful percentile calculations while bounding memory.
    MAX_LATENCY_SAMPLES = 100

    def __init__(self):
        # Each counter is a simple integer. defaultdict auto-initializes to 0.
        self.counters: dict[str, int] = defaultdict(int)

        # Each latency metric stores a list of (timestamp, value_ms) tuples.
        # We keep only the last MAX_LATENCY_SAMPLES entries per metric.
        self.latencies: dict[str, list[tuple[datetime, float]]] = defaultdict(list)

        # Error counters, separate from general counters for easy filtering.
        self.errors: dict[str, int] = defaultdict(int)

        # Track when the app started for uptime calculation.
        self.start_time: datetime = datetime.utcnow()

        # Recent errors log (last 50) for debugging via /admin_status
        self.recent_errors: list[dict] = []
        self.MAX_RECENT_ERRORS = 50

    def increment(self, metric: str, value: int = 1) -> None:
        """
        Increment a counter metric.

        Counters are monotonically increasing — they never decrease.
        Use for: total check-ins, total commands, total AI requests.

        Args:
            metric: Counter name (e.g., "checkins_total", "commands_report")
            value: Amount to increment by (default 1)
        """
        self.counters[metric] += value

    def record_latency(self, metric: str, ms: float) -> None:
        """
        Record a latency measurement.

        Latencies are stored in a rolling buffer of the last N samples.
        This bounds memory usage while providing enough data for percentiles.

        Args:
            metric: Latency metric name (e.g., "webhook_latency", "ai_latency")
            ms: Duration in milliseconds
        """
        entries = self.latencies[metric]
        entries.append((datetime.utcnow(), ms))

        # Prune to keep only the last MAX_LATENCY_SAMPLES entries.
        # This is O(1) amortized since we only prune when buffer is full.
        if len(entries) > self.MAX_LATENCY_SAMPLES:
            entries.pop(0)

    def record_error(self, category: str, detail: str = "") -> None:
        """
        Record an error occurrence.

        Errors are tracked both as counters (for totals) and as a recent log
        (for debugging). The recent log includes timestamps and details.

        Args:
            category: Error category (e.g., "firestore", "telegram", "ai")
            detail: Optional detail message for the recent errors log
        """
        self.errors[category] += 1
        self.counters["errors_total"] += 1

        # Add to recent errors log (bounded size)
        error_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "category": category,
            "detail": detail[:200] if detail else "",  # Truncate long details
        }
        self.recent_errors.append(error_entry)
        if len(self.recent_errors) > self.MAX_RECENT_ERRORS:
            self.recent_errors.pop(0)

    def get_uptime(self) -> dict:
        """
        Calculate application uptime.

        Returns:
            dict with uptime_seconds and human-readable uptime_human
        """
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        hours = int(uptime // 3600)
        minutes = int((uptime % 3600) // 60)
        return {
            "uptime_seconds": round(uptime, 1),
            "uptime_human": f"{hours}h {minutes}m",
        }

    def get_latency_stats(self, metric: str, window_minutes: int = 60) -> dict:
        """
        Calculate latency statistics for a metric within a time window.

        Uses percentile calculations:
        - p50 (median): Typical experience
        - p95: Worst case for 95% of requests
        - p99: Worst case for 99% of requests (tail latency)

        Args:
            metric: Latency metric name
            window_minutes: Time window in minutes (default 60 = last hour)

        Returns:
            dict with avg, p50, p95, p99, min, max, count
        """
        entries = self.latencies.get(metric, [])
        if not entries:
            return {"avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "count": 0}

        # Filter to time window
        cutoff = datetime.utcnow() - timedelta(minutes=window_minutes)
        values = [ms for ts, ms in entries if ts > cutoff]

        if not values:
            return {"avg_ms": 0, "p50_ms": 0, "p95_ms": 0, "count": 0}

        values.sort()
        count = len(values)

        return {
            "avg_ms": round(sum(values) / count, 1),
            "p50_ms": round(values[count // 2], 1),
            "p95_ms": round(values[int(count * 0.95)], 1) if count >= 2 else round(values[-1], 1),
            "min_ms": round(values[0], 1),
            "max_ms": round(values[-1], 1),
            "count": count,
        }

    def get_counter(self, metric: str) -> int:
        """Get current value of a counter."""
        return self.counters.get(metric, 0)

    def get_error_count(self, category: str = "") -> int:
        """
        Get error count, optionally filtered by category.

        Args:
            category: If empty, returns total errors. Otherwise, returns for that category.
        """
        if not category:
            return self.counters.get("errors_total", 0)
        return self.errors.get(category, 0)

    def get_summary(self) -> dict:
        """
        Generate a complete metrics summary.

        Returns a structured dict suitable for:
        - /health endpoint enrichment
        - /admin_status Telegram command
        - /admin/metrics API endpoint
        - Daily health digest generation

        Returns:
            dict with uptime, counters, errors, latencies, recent_errors
        """
        uptime = self.get_uptime()

        return {
            "uptime": uptime,
            "counters": dict(self.counters),
            "errors": {
                "total": self.counters.get("errors_total", 0),
                "by_category": dict(self.errors),
                "recent": self.recent_errors[-10:],  # Last 10 for summary
            },
            "latencies": {
                metric: self.get_latency_stats(metric)
                for metric in self.latencies
            },
        }

    def format_admin_status(self) -> str:
        """
        Format metrics into a Telegram-friendly admin status message.

        Uses Telegram HTML formatting for readability.

        Returns:
            str: HTML-formatted status message
        """
        uptime = self.get_uptime()
        summary = self.get_summary()

        lines = [
            "🔧 <b>Admin Status Report</b>",
            "━━━━━━━━━━━━━━━━━━",
            "",
            f"⏱ <b>Uptime:</b> {uptime['uptime_human']}",
            "",
            "📊 <b>Activity:</b>",
            f"  Check-ins: {self.get_counter('checkins_total')} "
            f"({self.get_counter('checkins_full')} full, {self.get_counter('checkins_quick')} quick)",
            f"  Commands: {self.get_counter('commands_total')}",
            f"  AI Requests: {self.get_counter('ai_requests_total')}",
            "",
        ]

        # Errors section
        total_errors = self.get_error_count()
        if total_errors > 0:
            lines.append(f"⚠️ <b>Errors:</b> {total_errors} total")
            for cat, count in sorted(self.errors.items(), key=lambda x: -x[1]):
                lines.append(f"  {cat}: {count}")
        else:
            lines.append("✅ <b>Errors:</b> None!")

        lines.append("")

        # Latencies section
        lines.append("📈 <b>Performance:</b>")
        for metric_name in ["webhook_latency", "ai_latency", "firestore_latency"]:
            stats = self.get_latency_stats(metric_name)
            if stats["count"] > 0:
                display_name = metric_name.replace("_latency", "").replace("_", " ").title()
                lines.append(
                    f"  {display_name}: avg {stats['avg_ms']}ms, "
                    f"p95 {stats['p95_ms']}ms ({stats['count']} samples)"
                )
        if not any(self.get_latency_stats(m)["count"] > 0 for m in ["webhook_latency", "ai_latency", "firestore_latency"]):
            lines.append("  No latency data yet")

        lines.append("")
        lines.append(f"🕐 <i>Report generated: {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}</i>")

        return "\n".join(lines)

    def reset(self) -> None:
        """
        Reset all metrics. Used in testing.
        """
        self.counters.clear()
        self.latencies.clear()
        self.errors.clear()
        self.recent_errors.clear()
        self.start_time = datetime.utcnow()


# ===== Singleton Instance =====
# Imported throughout the app: `from src.utils.metrics import metrics`
metrics = AppMetrics()
