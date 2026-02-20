# Phase 5: Automated Reports Every 3 Days

## Summary

Phase 5 addresses the **manual report triggering** problem where reports were only generated on a weekly schedule (Sunday 9 AM) or via the on-demand `/report` command. Users going through important transitions (first week of training, post-relapse recovery) had to wait up to 7 days for automated feedback. The solution adds a configurable periodic reporting system.

## Changes Made

### File: `src/models/schemas.py`

#### New Field on `User` model
- `last_report_date: Optional[str] = None` -- Stores the date (YYYY-MM-DD) of the last report sent to this user. Used by the periodic trigger to enforce a minimum gap between reports and prevent spam. Default `None` means "never received a report" (backward-compatible with all existing users).
- Added to both `to_firestore()` serialization and `from_firestore()` deserialization (Pydantic default handles backward compat).

### File: `src/agents/reporting_agent.py`

#### Modified: `generate_and_send_weekly_report()`
- **New parameter**: `days: int = 7` -- Controls the reporting window. Existing callers pass no argument and get the default 7-day behavior. The periodic trigger passes `days=3`.
- After successful delivery, writes today's date to the user's `last_report_date` field in Firestore via `firestore_service.update_user()`.
- The `period_label` is dynamically set: "Weekly" for `days=7`, "3-Day" for `days=3`, etc.

#### Modified: `send_weekly_reports_to_all()`
- **New parameters**: `days: int = 7`, `min_gap_days: int = 0`
- `min_gap_days` controls the cooldown between reports per user. If a user's `last_report_date` is within `min_gap_days`, they are skipped.
- `min_gap_days=0` (default) sends unconditionally -- preserving the existing weekly Sunday behavior.
- Malformed `last_report_date` values are treated as "no previous report" (fail-open).
- Added `reports_cooldown` counter to the result dict.

#### Modified: `_build_report_message()`
- **New parameter**: `days: int = 7`
- Report header shows "Weekly Report" or "3-Day Report" based on the value.
- Check-in count denominator uses `days` instead of hardcoded 7.

### File: `src/main.py`

#### New Endpoint: `POST /trigger/periodic-report`
- Protected by `verify_cron_request()` (same auth as all other cron endpoints).
- Accepts optional query parameters: `?days=3&min_gap=3` (both default to 3).
- Calls `send_weekly_reports_to_all(days=days, min_gap_days=min_gap)`.
- Returns aggregate results (sent/cooldown/failed counts).

#### Existing Endpoint: `POST /trigger/weekly-report` -- UNCHANGED
- Still calls `send_weekly_reports_to_all()` with no arguments.
- Defaults to `days=7, min_gap_days=0` -- sends to all users every time.
- Full backward compatibility with the existing Sunday cron job.

## Architecture

```
Cloud Scheduler
  ├─ "weekly-report-job" (Sunday 9:00 AM IST)
  │   └─ POST /trigger/weekly-report
  │       └─ send_weekly_reports_to_all(days=7, min_gap_days=0)
  │           └─ Sends to ALL users (no cooldown)
  │
  └─ "periodic-report-job" (Daily 9:00 AM IST) [NEW]
      └─ POST /trigger/periodic-report?days=3&min_gap=3
          └─ send_weekly_reports_to_all(days=3, min_gap_days=3)
              ├─ User A: last_report 1 day ago → SKIP (cooldown)
              ├─ User B: last_report 3 days ago → SEND 3-day report
              └─ User C: never received report → SEND 3-day report
```

## How It Works

### Scenario: Daily periodic trigger fires at 9 AM

1. Cloud Scheduler sends `POST /trigger/periodic-report?days=3&min_gap=3`
2. Endpoint reads query params: `days=3`, `min_gap=3`
3. For each user:
   - Check `user.last_report_date` against today
   - If gap < 3 days: skip (increment `reports_cooldown`)
   - If gap >= 3 days or no previous report: generate 3-day report
4. Report generation:
   - Fetch last 3 days of check-ins
   - Generate graphs + AI insights
   - Build message with "3-Day Report" header and "X/3 days" denominator
   - Send via Telegram
   - Update `last_report_date` to today

### Scenario: Sunday weekly trigger fires as usual

1. `POST /trigger/weekly-report` (no query params)
2. `send_weekly_reports_to_all(days=7, min_gap_days=0)` -- defaults
3. `min_gap_days=0` means NO cooldown check -- sends to ALL users
4. Each user gets a 7-day "Weekly Report"
5. `last_report_date` is updated to today

### Edge Cases

- **User got a 3-day report on Saturday, weekly fires on Sunday**: Since the weekly trigger uses `min_gap_days=0`, it sends unconditionally. User gets both reports. This is intentional -- the weekly report covers a full 7-day window which is different from the 3-day snapshot.
- **Malformed `last_report_date`**: Treated as "no previous report" (fail-open) rather than blocking the user from ever receiving reports.
- **New user with no `last_report_date`**: Gets their first report immediately (field is `None`, which skips the cooldown check).

## Cloud Scheduler Configuration

### New Job: `periodic-report-job`

```bash
gcloud scheduler jobs create http periodic-report-job \
  --schedule="0 9 * * *" \
  --uri="https://constitution-agent-450357249483.asia-south1.run.app/trigger/periodic-report?days=3&min_gap=3" \
  --http-method=POST \
  --time-zone="Asia/Kolkata" \
  --headers="X-Cron-Secret=${CRON_SECRET}" \
  --description="Periodic 3-day reports (runs daily, skips users who got a report <3 days ago)"
```

This fires every day at 9:00 AM IST. Because of the `min_gap=3` parameter, each user only actually receives a report every 3 days. The daily schedule ensures no user waits more than 24 hours past their 3-day window.

### Existing Job: `weekly-report-job` -- NO CHANGES

The existing Sunday weekly job continues to work unchanged. It still calls `/trigger/weekly-report` with no query params, which uses the default `days=7, min_gap_days=0`.

## Test Results

### Cooldown Logic (7/7 passed)
- 2 days ago -> skip (within 3-day gap)
- 3 days ago -> send (exactly at gap boundary)
- 5 days ago -> send (past gap)
- No previous report -> send
- Malformed date -> send (fail-open)
- Today -> skip
- 1 day ago -> skip

### Backward Compatibility (3/3 passed)
- min_gap=0 with today's date -> send
- min_gap=0 with yesterday's date -> send
- min_gap=0 with None -> send

## Files Modified

| File | Changes |
|------|---------|
| `src/models/schemas.py` | +`last_report_date` field on `User` + serialization |
| `src/agents/reporting_agent.py` | +`days` param on 3 functions, cooldown logic, `last_report_date` tracking |
| `src/main.py` | +`POST /trigger/periodic-report` endpoint |

## Design Decisions

1. **Daily trigger with per-user cooldown (vs 3-day cron)**: A pure "every 3 days" cron expression (`0 9 */3 * *`) runs on fixed calendar days (1st, 4th, 7th...). If a user misses day 1, they still get a report on day 4 regardless. Our approach is user-relative: each user's 3-day timer starts from their last report, ensuring consistent gaps.

2. **`min_gap_days=0` default for backward compatibility**: The existing weekly trigger passes no arguments, so it must work identically to before. The default of 0 means "no cooldown check."

3. **`last_report_date` stored as string, not datetime**: Firestore handles strings more cleanly than datetime objects for simple date comparisons. YYYY-MM-DD format sorts lexicographically, which is a nice bonus.

4. **Fail-open on malformed dates**: If `last_report_date` is somehow corrupted, we send the report anyway. Missing a report is worse than sending an extra one.

5. **Query parameters instead of separate endpoints per interval**: Using `?days=3&min_gap=3` makes the system flexible. If you want to change to 5-day reports, just update the Cloud Scheduler URL -- no code changes needed.
