# Phase D: Streak Recovery Encouragement + Intervention-to-Support Linking

**Date:** February 8, 2026  
**Status:** Complete — 833 tests passing (57 new Phase D tests + 776 existing)

---

## Overview

Phase D implements two complementary features that address psychological gaps in the accountability system:

1. **Feature 3: Streak Recovery Encouragement** — Transforms demoralizing streak resets into motivating comeback opportunities
2. **Feature 4: Intervention-to-Support Linking** — Bridges the gap between pattern detection and emotional support

---

## Feature 3: Streak Recovery Encouragement

### Problem
When a streak resets, the user sees `🔥 Streak: 1 days` with no context, encouragement, or acknowledgment of their previous achievement. This triggers the "what-the-hell" cognitive distortion and increases dropout risk.

### Solution
A comprehensive Recovery Journey System that reframes resets as temporary setbacks, not failures.

### Changes Made

#### `src/models/schemas.py`
- **`UserStreaks` model**: Added two new fields:
  - `streak_before_reset: int = 0` — The streak value right before the last reset
  - `last_reset_date: Optional[str] = None` — When the reset happened (YYYY-MM-DD)
- Both fields have safe defaults for backward compatibility with existing Firestore data

#### `src/utils/streak.py`
- **New constant `RECOVERY_FACTS`** (8 items): Motivational facts from behavioral psychology that normalize resets as part of the habit-building process. A random fact is shown on each reset.
- **New function `format_streak_reset_message()`**: Generates the compassionate reset message with:
  - "Fresh Start!" framing
  - Previous streak acknowledgment ("Your previous streak: 23 days 🏆")
  - Comeback framing ("Day 1 — the comeback starts now")
  - Random recovery fact
  - Next milestone prompt ("7 days → unlocks Comeback King!")
- **New function `get_recovery_milestone_message()`**: Checks for recovery milestones at key post-reset days:
  - Day 3: "💪 3 Days Strong!" — Proves the reset was a bump, not a stop
  - Day 7: "🦁 Comeback King!" — Full week = real momentum
  - Day 14: "🔥 Two Weeks Strong!" — Halfway to a strong habit
  - Exceeds old streak: "👑 NEW RECORD!" — Ultimate vindication
- **Modified `update_streak_data()`**: Now accepts `streak_before_reset` and `last_reset_date` parameters. Returns enhanced dict with:
  - `is_reset` (bool): Whether this check-in caused a reset
  - `recovery_message` (str|None): Reset or milestone message for display
  - `recovery_fact` (str|None): Random motivational fact
  - `streak_before_reset` / `last_reset_date`: Persistent fields for Firestore

#### `src/services/firestore_service.py`
- **`store_checkin_with_streak_update()`**: Updated transient key filter to exclude `is_reset`, `recovery_message`, and `recovery_fact` from Firestore writes (these are UI-only).

#### `src/bot/conversation.py`
- **`finish_checkin()`**: 
  - Now passes `streak_before_reset` and `last_reset_date` to `update_streak_data()`
  - Shows recovery message instead of bare "Streak: N days" when a reset occurs
  - Shows recovery milestone messages as separate follow-up messages
- **`finish_checkin_quick()`**: Same recovery enhancements as full check-in

#### `src/services/achievement_service.py`
- **New achievement `comeback_kid`**: Unlocks when reaching 3 days after a reset (🐣, uncommon rarity)
- **Enhanced achievement `comeback_king`**: Now unlocks at 7 days after a reset (previously required rebuilding to all-time best — too difficult). Icon 🦁, rare rarity.
- **New achievement `comeback_legend`**: Unlocks when exceeding `streak_before_reset` after a reset (👑, epic rarity)
- Updated `_check_special_achievements()` to check all three comeback achievements
- Updated celebration messages for new achievements
- Added "uncommon" to rarity message map

---

## Feature 4: Intervention-to-Support Linking

### Problem
The intervention agent detects patterns and sends warnings, but never connects the user to emotional support. The emotional support agent exists but is only triggered when the supervisor classifies free-text messages as "emotional." There's no explicit bridge.

### Solution
A severity-based support bridge on every intervention message + a new `/support` command.

### Changes Made

#### `src/agents/intervention.py`
- **New constant `SUPPORT_BRIDGES`**: Four severity-appropriate support prompts:
  - `low`: "💬 Want to talk about what got in the way? /support"
  - `medium`: "💬 Struggling with this? Type /support to talk it through."
  - `high`: "💙 This is hard. Type /support — no judgment, just support."
  - `critical`: "🆘 I'm here for you. Type /support or just tell me how you're feeling."
- **New function `add_support_bridge(message, severity)`**: Appends the appropriate bridge to any intervention message
- **Integrated in ALL intervention paths**:
  - AI-generated interventions
  - Ghosting template interventions
  - Fallback template intervention
  - Pattern-specific templates (snooze_trap, consumption_vortex, deep_work_collapse, relationship_interference)

#### `src/bot/telegram_bot.py`
- **New `/support` command registration**: `CommandHandler("support", self.support_command)`
- **New `support_command()` method**: 
  - Checks recent interventions (last 24h) for context
  - If recent intervention found: shows context-aware prompt referencing the pattern
  - If standalone: shows welcoming prompt for the user to share
  - If inline message provided (`/support I'm feeling down`): routes directly to emotional agent
  - Sets `support_mode` in `context.user_data` for follow-up routing
- **New `_process_support_message()` method**: Processes support messages through the emotional agent with optional intervention context
- **Updated `handle_general_message()`**: Checks for `support_mode` at the start; if set, routes directly to emotional agent (bypassing supervisor classification)

#### `src/utils/ux.py`
- Updated help text to include `/support` command under "Support & Natural Language" section

---

## Test Results

### Phase D Tests (`tests/test_phase_d_recovery_support.py`)
**57 tests, all passing:**

| Category | Tests | Status |
|----------|-------|--------|
| Recovery Facts | 3 | ✅ |
| Reset Message Format | 3 | ✅ |
| Recovery Milestones | 8 | ✅ |
| Update Streak Data | 7 | ✅ |
| Schema (UserStreaks) | 3 | ✅ |
| Firestore Key Filtering | 1 | ✅ |
| Comeback Achievements | 8 | ✅ |
| Celebration Messages | 2 | ✅ |
| Support Bridges | 3 | ✅ |
| add_support_bridge() | 4 | ✅ |
| Integration (source code) | 4 | ✅ |
| /support Command | 3 | ✅ |
| /support Behavior (async) | 3 | ✅ |
| Support Mode Handler | 1 | ✅ |
| E2E Reset Flow | 2 | ✅ |
| E2E Intervention Bridge | 2 | ✅ |

### Full Regression Suite
**833 total tests passing** (6 pre-existing tests updated for Phase D compatibility)

### Updated Pre-Existing Tests
- `tests/test_achievements.py`: Updated `user_comeback` fixture, achievement counts (13→15), progress percentages
- `tests/test_gamification_integration.py`: Updated comeback_king logic, achievement catalog count

---

## Architecture: Transient vs. Persistent Keys

**Key design decision:** `update_streak_data()` returns both types of keys:

| Key | Type | Purpose |
|-----|------|---------|
| `current_streak` | Persistent | Stored in Firestore |
| `longest_streak` | Persistent | Stored in Firestore |
| `streak_before_reset` | Persistent | Stored in Firestore |
| `last_reset_date` | Persistent | Stored in Firestore |
| `is_reset` | **Transient** | UI flag — stripped before write |
| `recovery_message` | **Transient** | Display text — stripped before write |
| `recovery_fact` | **Transient** | Display text — stripped before write |
| `milestone_hit` | **Transient** | Display text — stripped before write |

---

## Acceptance Criteria

### Feature 3 ✅
- [x] Streak reset shows previous streak context ("Your previous streak: 23 days")
- [x] Comeback framing instead of bare "Streak: 1 days"
- [x] Random recovery fact shown on reset
- [x] `streak_before_reset` and `last_reset_date` stored in Firestore
- [x] Recovery milestone messages at days 3, 7, 14, and "exceeds previous"
- [x] Comeback Kid (3 days) and Comeback Legend (exceeds previous) achievements added
- [x] Existing Comeback King (7 days) achievement enhanced

### Feature 4 ✅
- [x] All intervention messages include a support bridge prompt
- [x] Severity-appropriate prompt language (low → critical)
- [x] `/support` command invokes the emotional support agent
- [x] Context-aware: if triggered after intervention, agent knows the pattern
- [x] Standalone: `/support` also works without prior intervention
- [x] No new dependencies — uses existing emotional agent
