# Bug Fixes — Implementation Plan

## Overview

Fix 3 production bugs identified from user screenshots and feedback:

| Bug | Issue | Severity |
|-----|-------|----------|
| **Bug 1** | Sleep trend chart is redundant — sleep hours are never collected numerically | Medium |
| **Bug 2** | `<b>` HTML tags visible in emergency intervention messages | High (UX) |
| **Bug 3** | Check-in AI feedback only uses yesterday's qualitative data, not full 7-day context | High (Value) |

---

## Bug 1: Replace Redundant Sleep Chart

### Problem
The weekly report's "Sleep Trend (Last 7 Days)" line chart plots `tier1_non_negotiables.sleep_hours` — a numeric field that is **never populated** during check-in. The check-in flow only asks "Did you sleep 7+ hours?" as a yes/no boolean. Result: chart renders flat zeros and is meaningless.

### Solution
Replace with a **"Tier 1 Consistency Chart"** — a stacked horizontal bar chart showing, for each of the 6 Tier 1 non-negotiables, how many days they were completed vs missed over the last 7 days.

### Visual Design
```
Tier 1 Consistency (Last 7 Days)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Sleep 7h+    ██████░░░  6/7  ✅
Training     ███░░░░░░  3/7  ⚠️
Deep Work    █████░░░░  5/7  ✅
Skill Build  ████░░░░░  4/7  ⚠️
Zero Porn    ███████░░  7/7  🔒
Boundaries   ███████░░  7/7  🔒
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

### Files to Modify
- [ ] `src/services/visualization_service.py`
  - [ ] Remove `generate_sleep_chart()`
  - [ ] Add `generate_tier1_consistency_chart(checkins: List[DailyCheckIn]) -> io.BytesIO`
  - [ ] Update `generate_weekly_graphs()` mapping: `'sleep'` → `'tier1_consistency'`
- [ ] `src/agents/reporting_agent.py`
  - [ ] Update `graph_captions` dict: `'tier1_consistency': '📊 Tier 1 Consistency'`
  - [ ] Remove AI insights references to "avg sleep" if hallucinating from empty data
- [ ] `src/agents/query_agent.py`
  - [ ] Update sleep trend query response to use boolean completion rate instead of hours
- [ ] `src/utils/ux.py`
  - [ ] Update help text example: `'Show my sleep trend'` → `'Show my Tier 1 consistency'`

---

## Bug 2: Fix Visible HTML Tags in Interventions

### Problem
Intervention messages contain `<b>` HTML tags for bold formatting, but `bot.send_message()` in `src/main.py:501-504` is missing `parse_mode='HTML'`. Python-telegram-bot defaults to plain text, so raw tags appear literally.

### Solution
Add `parse_mode='HTML'` to the intervention `send_message` call.

### Files to Modify
- [ ] `src/main.py`
  - [ ] Line 501-504: Add `parse_mode='HTML'` to `bot_manager.bot.send_message(...)` for interventions
- [ ] `src/agents/intervention.py`
  - [ ] Audit all template-based intervention methods for HTML tag consistency
  - [ ] Verify no malformed tags (e.g., unclosed `<b>`)

---

## Bug 3: Enrich Check-in Feedback with Full 7-Day Qualitative Context

### Problem
The AI feedback prompt only includes:
- Compliance scores for all 7 days (numbers only)
- Rich qualitative data (challenges, rating reasons, priorities, obstacles, tier1 breakdown) for **yesterday only**

This makes the AI blind to weekly patterns like recurring stress, repeating obstacles, or declining motivation trends.

### Solution
Add a new **"Weekly Qualitative Context"** section to the prompt that includes all 7 days' qualitative data, with the most recent day emphasized.

### Prompt Structure (New Section)
```
WEEKLY QUALITATIVE CONTEXT (All 7 Days — Use for Pattern Recognition):
----------------------------------------------------------------------
Day 1 (2026-04-29): Score 67%, Rating 6/10
  Challenges: "Work deadline stress"
  Reason: "Felt rushed all day"
  Priority: "Complete deep work block"
  Obstacle: "Late evening meeting"
  Tier 1: Sleep ✅, Training ❌, Deep Work ✅, Skill ❌, Porn ✅, Boundaries ✅

Day 2 (2026-04-30): Score 83%, Rating 8/10
  ...

[Day 3-6 ...]

Day 7 (TODAY - MOST IMPORTANT): Score 56%, Rating 5/10
  Challenges: "Exhausted from yesterday"
  Reason: "Couldn't focus"
  Priority: "Sleep early"
  Obstacle: "Phone scrolling"
  Tier 1: Sleep ❌, Training ❌, Deep Work ❌, Skill ❌, Porn ✅, Boundaries ✅

INSTRUCTIONS FOR USING WEEKLY CONTEXT:
- Identify recurring themes across the week (e.g., "stress" mentioned 4 times)
- Note if the same obstacle appears repeatedly (e.g., "phone addiction" on 3 days)
- Compare today's priority vs what was actually achieved yesterday
- Reference specific patterns from the week, not just yesterday
- Give MORE weight to recent days, but don't ignore earlier signals
```

### Files to Modify
- [ ] `src/agents/checkin_agent.py`
  - [ ] Modify `_get_recent_checkins()` to include all qualitative fields for all days
  - [ ] Add `_build_weekly_qualitative_section(recent_checkins: List[Dict]) -> str` method
  - [ ] Update `_build_feedback_prompt()` to inject the new weekly section
  - [ ] Update prompt instructions to explicitly tell the AI to use weekly patterns

---

## Testing Strategy

### Unit Tests
- [ ] `tests/test_visualization_service.py`: Test new `generate_tier1_consistency_chart` with 7 days of mixed data
- [ ] `tests/test_checkin_agent.py`: Verify `_build_weekly_qualitative_section` generates correct markdown
- [ ] `tests/test_checkin_agent.py`: Verify prompt includes weekly context (mock LLM call)

### Regression Tests
- [ ] `pytest tests/test_fastapi_endpoints.py`: Ensure intervention endpoint tests still pass
- [ ] `pytest tests/test_phase3f_integration.py`: Weekly report pipeline still works with new chart
- [ ] `pytest tests/test_conversation_flow.py`: Check-in flow unchanged

### Manual Verification Points
1. Weekly report sends 4 graphs, one of which is "Tier 1 Consistency" instead of "Sleep Trend"
2. Intervention messages render with proper bold formatting (no visible tags)
3. Check-in feedback references multi-day patterns when applicable

---

## Risk Assessment

| Bug | Risk | Mitigation |
|-----|------|------------|
| Bug 1 (Chart) | Low | Only affects visualization; data model unchanged |
| Bug 2 (HTML) | Very Low | Single line addition; existing tests cover send path |
| Bug 3 (Context) | Low-Medium | Prompt change could affect AI output style; monitor first few responses |

---

## Deployment Notes

- Changes are backward-compatible (no Firestore schema changes)
- Can be deployed via standard `gcloud run services update` workflow
- No user-facing breaking changes

---

## Approval

**Status:** ⏳ Awaiting user approval before implementation.
