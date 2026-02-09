# Phase A: Foundation — Monitoring & Rate Limiting

**Date:** February 8, 2026  
**Status:** COMPLETE — Ready for Phase B

---

## Summary

Phase A establishes the observability and safety foundation:
- **F6: Monitoring** — Structured logging, metrics, admin dashboard
- **F5: Rate Limiting** — Tiered throttling for expensive commands

---

## New Files Created

### `src/utils/metrics.py` — Application Metrics Collector
- **AppMetrics class** with counters, latencies, errors, and recent error log
- **Counters**: `increment(metric, value)` for tracking totals (check-ins, commands, AI calls)
- **Latencies**: `record_latency(metric, ms)` with rolling buffer (last 100 samples)
  - Calculates avg, p50, p95, min, max within configurable time windows
- **Errors**: `record_error(category, detail)` with categorization and recent log
- **Admin Status**: `format_admin_status()` generates Telegram HTML-formatted report
- **Summary**: `get_summary()` returns full structured metrics dict
- **Singleton**: `from src.utils.metrics import metrics`

### `src/utils/rate_limiter.py` — Tiered Rate Limiter
- **Sliding window algorithm**: Timestamps pruned hourly, no memory leaks
- **Three tiers**:
  | Tier | Cooldown | Max/Hour | Commands |
  |------|----------|----------|----------|
  | Expensive | 30 min | 2 | `/report`, `/export` |
  | AI-Powered | 2 min | 20 | General AI messages, `/support` |
  | Standard | 10 sec | 30 | `/stats`, `/leaderboard`, `/achievements` |
- **Admin bypass**: Configured via `admin_telegram_ids` in settings
- **User-friendly denial**: Shows countdown + contextual tips
- **Cleanup**: Periodic `cleanup()` removes stale user entries
- **Singleton**: `from src.utils.rate_limiter import rate_limiter`

---

## Modified Files

### `src/config.py`
- Added `admin_telegram_ids: str = ""` — comma-separated admin Telegram IDs
- Added `json_logging: bool = False` — enables JSON structured logging for production

### `src/main.py`
- **JSON logging**: New `JSONFormatter` class that outputs Cloud Logging-compatible JSON
  - Includes `severity`, `message`, `module`, `function`, `timestamp`
  - Custom fields: `user_id`, `command`, `latency_ms`, `error_category`
  - Controlled by `json_logging` config setting (plain text for dev, JSON for prod)
- **Rate limiter initialization**: Parses `admin_telegram_ids` at startup
- **Enhanced `/health`**: Now includes `uptime`, `metrics_summary` (check-ins, commands, errors)
- **New `/admin/metrics`**: Full metrics endpoint (requires admin_id query param)
- **Webhook metrics**: Records `webhook_latency` and error counts on every webhook
- **Global exception handler**: Records `unhandled` errors in metrics

### `src/bot/telegram_bot.py`
- **Imports**: Added `metrics` and `rate_limiter`
- **New `_check_rate_limit()` helper**: Shared rate-limit check + metrics increment
- **New `/admin_status` command**: Admin-only, shows formatted metrics via Telegram
  - Non-admins see "Unknown command" (doesn't reveal the command exists)
- **Rate limiting applied to**:
  - `report_command` → expensive tier
  - `export_command` → expensive tier
  - `leaderboard_command` → standard tier
  - `handle_general_message` → ai_powered tier

---

## Test Results

| Test Suite | Tests | Result |
|-----------|-------|--------|
| Phase A: Monitoring | 27 | 27/27 PASS |
| Phase A: Rate Limiting | 23 | 23/23 PASS |
| Phase A: Integration | 24 | 24/24 PASS |
| Existing regression suite | 247 | 247/247 PASS |
| **TOTAL** | **321** | **321/321 PASS** |

---

## Design Decisions

1. **In-memory vs Redis**: Chose in-memory because we're a single-instance Cloud Run service. Metrics reset on deploy (acceptable — deploys are rare). Avoids Redis cost/complexity.

2. **JSON logging opt-in**: `json_logging=False` by default so local development remains readable. Set `JSON_LOGGING=true` in Cloud Run env vars for production.

3. **Admin as config**: Admin IDs in env vars (not Firestore) because admin check happens on every rate-limited command. Env vars are O(1) access, no DB query needed.

4. **Sliding window**: More accurate than fixed-window rate limiting — no "boundary burst" issue where a user sends 2 requests at 12:59 and 2 more at 13:01 (4 in 2 minutes).

5. **Fail-open on restart**: Rate limits reset on deploy. This is intentional — denying all requests after restart would be worse than briefly allowing extra requests.
