# P0 + P1 Bug Fixes & UX Improvements Changelog

**Date:** February 8, 2026  
**Scope:** All 4 P0 (Critical Bugs) + 7 P1 (UX Fixes) from Product Gap Analysis  
**Source Plan:** `.cursor/plans/product_gap_analysis_review_a59e6212.plan.md`

---

## P0: Critical Bug Fixes (4 items)

### Fix 1: Streak Shield Must Actually Protect the Streak ✅

**File:** `src/services/firestore_service.py` — method `use_streak_shield()`

**Problem:** When a user called `/use_shield`, the shield counter was decremented but `last_checkin_date` was NOT updated. The streak logic in `streak.py` compares `last_checkin_date` to the current date — if the gap is 2+ days, the streak resets regardless of shield usage.

**Fix:** Added `"streaks.last_checkin_date": get_checkin_date()` to the Firestore update inside `use_streak_shield()`. This "bridges" the gap so the next check-in sees only a 1-day difference and correctly increments the streak instead of resetting it.

**Theory:** Firestore's dot-notation update (`"streaks.last_checkin_date"`) modifies a nested field without overwriting the entire `streaks` object. This is safer than reading the full object, modifying it, and writing it back (which risks race conditions).

---

### Fix 2: Add Missing `update_user()` Method ✅

**File:** `src/services/firestore_service.py` — new method `update_user()`

**Problem:** The quick check-in reset endpoint in `main.py` (line 706) called `firestore_service.update_user()` which didn't exist, causing a runtime crash (`AttributeError`).

**Fix:** Added a generic `update_user(user_id, updates)` method to `FirestoreService`. It uses Firestore's `update()` API which only modifies specified fields (no full doc overwrite). Also automatically stamps `updated_at`.

---

### Fix 3: Achievement Service Field Paths Audit ✅ (No Changes Needed)

**File:** `src/services/achievement_service.py`

**Finding:** After a comprehensive audit (grep for `.tier1.` and `.completed` across all Python files), all field accesses were confirmed correct:
- Line 374: `c.tier1_non_negotiables.zero_porn` ✅
- Lines 460-467: Uses `tier1 = checkin.tier1_non_negotiables` then flat booleans ✅
- No stale `tier1.X` or `tier1_non_negotiables.X.completed` patterns found

---

### Fix 4: Atomic Check-In + Streak Update Transaction ✅

**Files:** 
- `src/services/firestore_service.py` — new method `store_checkin_with_streak_update()`
- `src/bot/conversation.py` — `finish_checkin()` and `finish_checkin_quick()`

**Problem:** `store_checkin()` and `update_user_streak()` were two separate Firestore writes. If the streak update failed after the check-in was stored, the streak would become stale and incorrectly reset on the next check-in.

**Fix:** Created a new transactional method `store_checkin_with_streak_update()` using `@firestore.transactional`. Both the check-in document write and the user streak update happen atomically — either both succeed or neither does. Updated both the regular and quick check-in flows in `conversation.py` to use the new method.

**Theory:** Firestore transactions provide snapshot isolation. The transaction reads current state, performs writes, and if any read data changed since the snapshot, Firestore retries automatically (up to 5 times). This guarantees consistency even under concurrent access.

---

## P1: UX Fixes (7 items)

### Fix 5: `/mode` Command Now Actually Changes Mode ✅

**File:** `src/bot/telegram_bot.py` — rewritten `mode_command()` + new `mode_change_callback()`

**Problem:** `/mode` only displayed information and told users to type `/mode <mode_name>`, but there was no argument parsing or inline buttons.

**Fix:** Complete rewrite of `mode_command()`:
1. **Text argument parsing:** `/mode optimization` directly switches mode
2. **Inline keyboard buttons:** `/mode` (no args) shows info + buttons for each mode
3. **Callback handler:** `mode_change_callback()` handles button presses

Uses `"change_mode_"` callback prefix to avoid conflict with `"mode_"` prefix used during onboarding.

---

### Fix 6: Welcome Message Updated to 6 Items ✅

**File:** `src/bot/telegram_bot.py` — `start_command()`

**Problem:** Welcome message said "5 non-negotiables" and listed only 5 items. Skill Building (6th) was added in Phase 3D but the welcome text was never updated.

**Fix:** Changed "5" to "6", added "📚 Skill Building: 2+ hours career-focused learning" as item 4, renumbered subsequent items, updated "these 5 items" to "these 6 items".

---

### Fix 7: Undo Button During Check-In Tier 1 Questions ✅

**File:** `src/bot/conversation.py` — `handle_tier1_response()`

**Problem:** Accidental button presses during Tier 1 questions were permanent. The only escape was `/cancel` which restarted the entire check-in.

**Fix:** Added undo functionality:
1. Each answer confirmation now includes an "↩️ Undo Last" inline button
2. Answer order tracked in `context.user_data['tier1_answer_order']` (list)
3. Pressing "Undo Last" removes the most recent answer and prompts re-answer
4. Works for any number of undos (can undo all 6 if needed)
5. Re-answering after undo correctly updates the order tracking

---

### Fix 8: `/correct` Command for Check-In Corrections ✅

**Files:**
- `src/bot/telegram_bot.py` — new `correct_command()` + `correct_toggle_callback()`
- `src/services/firestore_service.py` — new `update_checkin()` method
- `src/models/schemas.py` — added `corrected_at` field to `DailyCheckIn`

**Problem:** No way to fix wrong answers after submission. One fat-finger permanently affected compliance scores, streaks, patterns, and achievements.

**Fix:** New `/correct` command that:
1. Loads today's check-in from Firestore
2. Validates constraints (today only, within 2 hours, max 1 correction)
3. Displays current Tier 1 answers with toggle buttons
4. User taps items to flip YES↔NO
5. "Save Correction" recalculates compliance score and updates Firestore
6. "Cancel" aborts without changes

**Constraints:**
- Only today's check-in (not historical)
- Within 2 hours of original check-in time
- Maximum 1 correction per check-in (prevents gaming)

---

### Fix 9: Historical Compliance Score Normalization ✅

**Files:**
- `src/utils/compliance.py` — new `calculate_compliance_score_normalized()` + `is_all_tier1_complete()`
- `src/config.py` — new `phase_3d_deployment_date` setting
- `src/services/achievement_service.py` — updated `_all_tier1_complete()` to use date-aware check

**Problem:** Phase 3D added Skill Building as a 6th Tier 1 item. Old check-ins (5 items) deserialize with `skill_building=False` (Pydantic default). Functions that re-evaluate tier1 data (like achievement checks) would incorrectly penalize old check-ins.

**Fix:** 
1. Added `phase_3d_deployment_date = "2026-02-05"` to config
2. Created `calculate_compliance_score_normalized(tier1, checkin_date)` that uses /5 for pre-3D and /6 for post-3D check-ins
3. Created `is_all_tier1_complete(tier1, checkin_date)` that excludes `skill_building` for pre-3D check-ins
4. Updated `achievement_service._all_tier1_complete()` to delegate to the date-aware function

**Note:** The stored `compliance_score` in Firestore is already correct (calculated at check-in time). These functions are for code that re-analyzes raw `tier1_non_negotiables` booleans.

---

### Fix 10: Empathetic 0% Compliance Fallback ✅

**File:** `src/utils/compliance.py` — `format_compliance_message()`

**Problem:** Critical-level fallback said "Below standards. Time to refocus. You know what to do." — harsh and shame-inducing for someone who checked in despite a bad day.

**Fix:** Rewrote critical messages:
- Header: "Tough day." (was "Below standards.")
- Encouragement: "Tomorrow is a fresh start. The fact that you checked in shows real commitment." (was "Time to refocus. You know what to do.")
- Added: "Need to talk? Just type how you're feeling." (bridges to emotional support agent)

**Theory:** Behavioral psychology shows that shame-based messaging leads to avoidance (user stops checking in). Empathetic messaging maintains the habit loop — the user is already showing commitment by completing the check-in.

---

### Fix 11: Cloud Scheduler Cron Endpoint Authentication ✅

**Files:**
- `src/main.py` — new `verify_cron_request()` helper, applied to all 6 endpoints
- `src/config.py` — new `cron_secret` setting

**Problem:** All cron/trigger endpoints were publicly accessible. The auth header check was commented out. Anyone who discovered the URLs could trigger mass reminders, pattern scans, or reports.

**Fix:**
1. Added `cron_secret` config setting (env var `CRON_SECRET`)
2. Created `verify_cron_request(request)` helper that checks `X-Cron-Secret` header
3. Applied to all 6 endpoints: `/trigger/pattern-scan`, `/cron/reminder_first`, `/cron/reminder_second`, `/cron/reminder_third`, `/cron/reset_quick_checkins`, `/trigger/weekly-report`
4. Returns HTTP 403 if header is missing or invalid
5. Auth is skipped when `cron_secret` is empty (development mode)

**Deployment Note:** After deploying, set `CRON_SECRET` env var in Cloud Run and configure Cloud Scheduler jobs to include `X-Cron-Secret: <value>` header.

---

## Files Modified Summary

| File | Changes |
|------|---------|
| `src/services/firestore_service.py` | Added `update_user()`, `update_checkin()`, `store_checkin_with_streak_update()`; Fixed `use_streak_shield()` |
| `src/bot/telegram_bot.py` | Rewrote `mode_command()`; Added `mode_change_callback()`, `correct_command()`, `correct_toggle_callback()`; Updated welcome message; Registered new handlers |
| `src/bot/conversation.py` | Added undo to `handle_tier1_response()`; Updated both check-in finishers to use transactional method |
| `src/utils/compliance.py` | Added `calculate_compliance_score_normalized()`, `is_all_tier1_complete()`; Fixed empathetic fallback |
| `src/config.py` | Added `phase_3d_deployment_date`, `cron_secret` |
| `src/main.py` | Added `verify_cron_request()` helper; Applied to all 6 cron endpoints |
| `src/services/achievement_service.py` | Updated `_all_tier1_complete()` to use date-aware compliance check |
| `src/models/schemas.py` | Added `corrected_at` field to `DailyCheckIn`; Updated `to_firestore()` |

---

## Next Steps (P2/P3 — Deferred)

These items were identified in the product review but deferred:
- Vacation/pause mode
- Custom timezone support
- Partner dashboard
- Telegram message splitting for >4096 char
- Rate limiting on expensive commands
- GDPR data deletion command
- Pattern → emotional support linking
