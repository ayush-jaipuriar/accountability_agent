# Phase 4: Deeper Per-Metric Tracking

## Summary

Phase 4 addresses the **focus-on-streak-only** problem where the agent tracked only aggregate compliance scores and streak length, without showing how each individual Tier 1 habit (sleep, training, deep work, etc.) was performing over time. The solution adds three layers of per-metric visibility:

1. **Enhanced /status command** -- now includes a Tier 1 breakdown showing 7-day completion rates per metric
2. **New /metrics command** -- full dashboard with 7d/30d rates, week-over-week trend arrows, and per-metric streaks
3. **Enhanced weekly reports** -- Tier 1 breakdown in the report text + per-metric trends in the AI insights prompt

## Changes Made

### File: `src/services/analytics_service.py`

#### New Module-Level Constants

| Constant | Purpose |
|----------|---------|
| `TIER1_METRICS` | Canonical list of 6 Tier 1 metric names (used everywhere for consistency) |
| `METRIC_LABELS` | Display-friendly names (e.g., "Sleep 7h+", "Deep Work") |
| `METRIC_EMOJIS` | Emoji prefix per metric for Telegram formatting |

#### New Functions

**`calculate_metric_streaks(checkins) -> Dict[str, int]`**
- Walks check-ins from newest to oldest
- For each metric, counts consecutive completed days until the first miss
- Returns `{"sleep": 12, "training": 7, ...}`

**`calculate_metric_trends(checkins, days=7) -> Dict[str, Dict]`**
- Splits check-in history into "current N days" and "previous N days" windows
- Computes completion percentage for each half
- Returns change direction: `"up"` (>10% improvement), `"down"` (>10% decline), or `"stable"`
- Used by both `/metrics` command and reporting agent's LLM prompt

**`format_metric_dashboard(checkins_7d, checkins_30d) -> str`**
- Builds the full HTML-formatted dashboard for the `/metrics` command
- Three sections: 7-day snapshot with trend arrows, 30-day overview, per-metric streaks
- Uses `_pct_bar()` to render mini progress bars: `[███░░]`

**`format_status_tier1_breakdown(checkins_7d) -> str`**
- Compact one-line-per-metric format for the `/status` command
- Shows: emoji + label + completion fraction (e.g., "5/7 (71%)")

**`_pct_bar(pct, width=5) -> str`**
- Renders a 5-character text progress bar using block elements

**`_direction_arrow(direction) -> str`**
- Maps "up"/"down"/"stable" to arrow emoji

### File: `src/bot/telegram_bot.py`

#### New: `metrics_command()` method
- Handles the `/metrics` slash command
- Fetches 7-day and 30-day check-ins from Firestore
- Delegates formatting to `format_metric_dashboard()`
- Sends the result as an HTML Telegram message

#### Modified: `status_command()`
- Added a Tier 1 breakdown section between the "Last 7 Days" aggregate stats and the "Today" section
- Added a footer hint: "Use /metrics for detailed trends and streaks."

#### Modified: `_register_handlers()`
- Registered `CommandHandler("metrics", self.metrics_command)` alongside status/help/mode

#### Modified: `REGISTERED_COMMANDS`, `COMMAND_KEYWORDS`, `_get_command_handler_map()`
- Added "metrics" to all three for fuzzy matching + keyword routing support

### File: `src/agents/reporting_agent.py`

#### Modified: `generate_ai_insights()`
- Now fetches 14 days of check-ins (instead of relying on just the 7-day batch)
- Calls `calculate_metric_trends()` to get per-metric week-over-week changes
- Injects a "Per-Metric Trends (vs previous week)" section into the LLM prompt
- Added rules: "If a metric is trending down, call it out directly"

#### Modified: `_build_report_message()`
- Added a "Tier 1 Breakdown" section showing per-metric completion rates
- This appears between the Quick Summary and AI Insights sections

## How It Works

### Scenario: User sends `/metrics`

1. Bot fetches 7-day and 30-day check-ins from Firestore
2. `format_metric_dashboard()` computes:
   - `_calculate_tier1_stats()` for each window (leveraging existing function)
   - `calculate_metric_trends()` comparing last 7d vs previous 7d
   - `calculate_metric_streaks()` from 30-day data
3. Formats into three HTML sections with progress bars and trend arrows
4. Sends to user

**Example output:**
```
Metrics Dashboard

Last 7 Days:
  Sleep 7h+:       [████░] 71% (5/7) →+0%
  Training:        [██░░░] 43% (3/7) ↘️-14%
  Deep Work:       [█████] 100% (7/7) →+0%
  Skill Building:  [█████] 100% (7/7) ↗️+71%
  Zero Porn:       [█████] 100% (7/7) →+0%
  Boundaries:      [█████] 100% (7/7) →+0%

Last 30 Days:
  Sleep 7h+:       67% (20/30)
  Training:        50% (15/30)
  ...

Current Streaks:
  Sleep 7h+:       2 days
  Training:        ---
  Deep Work:       30 days
  ...
```

### Scenario: User sends `/status`

Now includes after the aggregate "Last 7 Days" section:
```
Tier 1 Breakdown (7d):
  Sleep 7h+:       5/7 (71%)
  Training:        3/7 (43%)
  Deep Work:       7/7 (100%)
  Skill Building:  7/7 (100%)
  Zero Porn:       7/7 (100%)
  Boundaries:      7/7 (100%)
```

### Scenario: Weekly report generated

The LLM prompt now includes trend data like:
```
Per-Metric Trends (vs previous week):
  Sleep 7h+: 71% (prev week 71%, stable)
  Training: 43% (prev week 57%, down)
  ...
```

And the report message includes a "Tier 1 Breakdown" section with per-metric rates.

## Design Decisions

1. **Reused `_calculate_tier1_stats()`**: This function already existed in `analytics_service.py` and computed exactly what we needed. Rather than duplicating logic, the new functions call it and layer on additional computations (streaks, trends, formatting).

2. **10% threshold for trend direction**: A small fluctuation (e.g., 86% -> 83%) shouldn't be flagged as "trending down" -- it's noise. The 10% threshold ensures only meaningful changes get directional arrows. This prevents alarm fatigue.

3. **Streak counting from newest to oldest**: The streak measures "how many consecutive recent days did you complete X?" Walking backwards from the most recent day gives the current streak, which is what users care about.

4. **Two Firestore queries for `/metrics`**: We make two `get_recent_checkins` calls (7d and 30d). The 30d call includes the 7d data, but since Firestore queries are cheap and fast, the simplicity outweighs the minor redundancy.

5. **14-day fetch for report trends**: The reporting agent now fetches 14 days of data so it can compute a meaningful "previous week" comparison. This costs one extra Firestore read but dramatically improves the quality of AI insights.

## Test Results

All tests passed:
- Metric streaks: Correct consecutive-day counting
- Metric trends: Correct week-over-week direction detection (up/down/stable)
- Progress bars: Correct rendering at 0%, 20%, 100%
- Tier 1 breakdown format: Correct emoji, label, fraction output
- Dashboard format: Full 643-character output verified

## Files Modified

| File | Changes |
|------|---------|
| `src/services/analytics_service.py` | +6 new functions, +3 constants (~180 lines) |
| `src/bot/telegram_bot.py` | +`metrics_command`, enhanced `status_command`, registered handler + fuzzy match |
| `src/agents/reporting_agent.py` | Enhanced AI prompt with trends, added Tier 1 breakdown to report text |

## Next Steps

- **Phase 5**: Automated Reports Every 3 Days (configurable `days` param, new endpoint, Cloud Scheduler setup)
