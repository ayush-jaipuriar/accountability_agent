# Deployment Log: v2.0 Phases 1-4

**Date:** 2026-05-16  
**Release:** v2.0 (Major)  
**Phases Deployed:** 1, 2, 3, 4 (Partial) + 5 (Hardening)  
**Test Count:** 1043 passed, 0 failed  
**Pre-Deploy Check:** 12/12 passed  
**Image Tag:** `manual-20260516-230915` (RCA follow-up)  
**Revision:** `accountability-agent-00013-mqc`  
**Deployed At:** 2026-05-16 17:41:33 UTC

---

## Deployment Summary

This release implements the full v2.0 roadmap through Phase 4, transforming Accountability Agent from a simple check-in tracker into an intelligent accountability companion with predictive capabilities, social features, and emotional intelligence.

---

## Features Deployed

### Phase 1: Data Depth & Core Loop
- **P1.1 Continuous Data Capture**: Numeric Q1 inputs (sleep hours, deep work hours, training intensity). Pattern detection uses actual data. AI feedback references averages.
- **P1.2 Morning Briefing**: Personalized 8 AM briefings referencing yesterday's priorities. `/settings` toggle. On-demand `/briefing`.
- **P1.3 Adaptive Check-In**: Power user detection (streak ≥30 + 85% compliance). Struggling user empathy. Perfect-day Q2 skip.
- **P1.4 Churn Prediction**: 5-factor risk scoring. Internal-only risk scores. Gentle interventions. 3-day cooldown.

### Phase 2: Constitution & Social
- **P2.1 Interactive Constitution**: `/constitution` with live stats overlay (personal sleep avg, deep work avg, compliance).
- **P2.2 Goal-Setting**: `Goal` schema + auto-progress. `/goals`, `/goal_new`, `/goal_progress`, `/goal_complete`. Milestone notifications (50%/75%/100%).
- **P2.3 Partner Challenges**: `PartnerChallenge` schema. `/challenges`, `/challenge_new`, `/challenge_accept`, `/challenge_decline`. Sleep/training/deep_work challenge types. Winner/tie detection.
- **P2.4 Small Group Cohorts**: Deferred.

### Phase 3: Intelligence & Insights
- **P3.1 Insights Engine**: DOW pattern detection, sleep→performance correlation, mood correlation, risk window detection. `/insights` on-demand command.
- **P3.2 Mood & Energy Tracking**: Q5 with inline buttons (1-10 scale). Pearson correlations in analytics.
- **P3.3 Predictive Interventions**: Evening 9 PM cron. DOW risk, streak fatigue, momentum loss signals. Preventive actions.

### Phase 4: Scale & Polish
- **P4.1 Progressive Onboarding**: Schema flag added (`onboarding_completed`). Full 5-step flow deferred.
- **P4.2 Streak Recovery**: Compassionate 3-part ritual (Acknowledge → Forgive → Restart). Break reason capture. Partner notification.
- **P4.3 Feature Discovery**: Contextual hints at milestones. Daily throttle. `/settings` toggle.
- **P4.4 Feedback Loop**: `/feedback` NPS collection. Weekly `/cron/weekly_nps`. NPS calculation and admin summary.
- **P4.5 Admin Dashboard Enhancement**: Deferred to Phase 5.

### Phase 5: Hardening
- **P5.1 Feature Flags**: 16 config flags for safe rollout.
- **P5.2 GDPR Compliance**: `/delete_my_data` command with confirmation. Complete data deletion service.
- **P5.3 Pre-Deploy Validation**: `scripts/pre_deploy_check.py` runs compilation + tests + import checks.
- **P5.4 Deployment Documentation**: Updated `AGENTS.md`, `DEPLOYMENT_LOG_2026-05-16.md`, `REVIEW_PHASES_1-4.md`.

---

## Files Changed

### New Files
- `src/services/briefing_service.py`
- `src/services/churn_prediction.py`
- `src/services/churn_intervention.py`
- `src/services/constitution_service.py` (enhanced)
- `src/services/goal_service.py`
- `src/services/challenge_service.py`
- `src/services/insights_engine.py`
- `src/services/predictive_intervention.py`
- `src/services/feature_discovery_service.py`
- `src/services/feedback_service.py`
- `src/services/streak_recovery_service.py`
- `src/services/data_deletion_service.py`
- `tests/test_briefing_service.py`
- `tests/test_churn_prediction.py`
- `tests/test_adaptive_checkin.py`
- `tests/test_constitution_command.py`
- `tests/test_goal_service.py`
- `tests/test_challenge_service.py`
- `tests/test_insights_engine.py`
- `tests/test_predictive_intervention.py`
- `tests/test_streak_recovery.py`
- `tests/test_feature_discovery.py`
- `tests/test_feedback_service.py`
- `scripts/pre_deploy_check.py`
- `REVIEW_PHASES_1-4.md`

### Modified Files
- `src/models/schemas.py` — Added continuous fields, Goal, PartnerChallenge, energy/mood, onboarding, break_reasons, hints_sent
- `src/bot/conversation.py` — Q1 numeric flow, Q5 mood, adaptive context, streak recovery trigger, feature hints trigger
- `src/bot/telegram_bot.py` — 12 new commands, 4 new callbacks
- `src/main.py` — 3 new cron endpoints
- `src/services/analytics_service.py` — Mood/energy stats, correlations
- `src/config.py` — 11 new feature flags

---

## Deployment Commands

```bash
# Pre-deploy
python3 scripts/pre_deploy_check.py

# Build
gcloud builds submit --tag us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260516-201939

# Deploy
gcloud run services update accountability-agent \
  --platform=managed \
  --region=us-central1 \
  --image us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260516-201939

# Post-deploy verification
curl -fsS https://accountability-agent-450357249483.us-central1.run.app/health
```

---

## RCA Follow-Up 2026-05-16 (Post-Hotfix)

### Process Improvements Deployed

| # | Improvement | File(s) | Status |
|---|-------------|---------|--------|
| 1 | **Handler checklist** | `HANDLER_CHECKLIST.md` | Created |
| 2 | **Expanded pre-deploy checks** | `scripts/pre_deploy_check.py` | 16 checks (was 12) |
| 3 | **HTML safety utilities** | `src/utils/telegram_utils.py` | Created |
| 4 | **Feature flag wiring** | `src/bot/telegram_bot.py` | Conditional handler registration |
| 5 | **Model name centralization** | `src/config.py` | Centralized defaults |
| 6 | **Integration tests** | `tests/test_handler_integration.py` | 13 tests added |
| 7 | **Rollback script** | `scripts/rollback.sh` | One-command rollback |
| 8 | **Manual QA checklist** | `DEPLOYMENT_QA.md` | Created |

### Pre-Deploy Check Expansion

New checks added:
- **Handler registration consistency**: Verifies `REGISTERED_COMMANDS` and `_get_command_handler_map` stay in sync
- **Callback handler safety**: Flags `update.message` usage inside callback handlers
- **HTML parse_mode safety**: Detects unescaped `<` in HTML-mode messages
- **Model name centralization**: Warns on hardcoded model names outside config

### Feature Flags Now Wired

Handlers are conditionally registered based on feature flags:
- `enable_morning_briefing` → `/briefing`
- `enable_constitution_viewer` → `/constitution`
- `enable_goals` → `/goals`, `/goal_new`, etc.
- `enable_partner_challenges` → `/challenges`, etc.
- `enable_insights_engine` → `/insights`
- `enable_feedback_collection` → `/feedback`, NPS callback
- `enable_streak_recovery` → Break reason callback

---

## Hotfix 2026-05-16 (Post-Deploy)

### Bugs Fixed

| # | Bug | Severity | Fix |
|---|-----|----------|-----|
| 1 | `UnboundLocalError: DailyCheckIn` in `finish_checkin` | **CRITICAL** | Removed nested import inside `try` block that shadowed module-level import |
| 2 | `update.message=None` when `finish_checkin` called from callback | **CRITICAL** | Added `_get_message_from_update()` helper; replaced all `update.message` refs in `finish_checkin` with safe fallback to `callback_query.message` |
| 3 | "Did you mean?" firing after successful commands | **HIGH** | Added early return in `handle_unknown_command` if command is already in `REGISTERED_COMMANDS` |
| 4 | Missing commands in `_get_command_handler_map` | **HIGH** | Added 15 new v2.0 commands to handler map for fuzzy matching |
| 5 | Constitution HTML parse error (`<6` treated as tag) | **HIGH** | Escaped `<` as `&lt;` in historical patterns text |
| 6 | Feedback NPS raw HTML tags visible | **MEDIUM** | Added `parse_mode='HTML'` to all `edit_message_text` calls in `nps_callback` |
| 7 | Query agent using deprecated `gemini-2.0-flash-exp` | **MEDIUM** | Updated default model to `gemini-2.5-flash` |
| 8 | Supervisor `last_checkin_date` attribute error | **LOW** | Fixed `user.last_checkin_date` → `user.streaks.last_checkin_date`; fixed `user.mode` → `user.constitution_mode` |

### Files Changed in Hotfix
- `src/bot/conversation.py` — Removed nested import, added `_get_message_from_update()` helper, replaced 12 unsafe `update.message` references
- `src/bot/telegram_bot.py` — Added registered-command guard in `handle_unknown_command`, expanded `_get_command_handler_map` with 15 commands, added `parse_mode='HTML'` to NPS callbacks
- `src/services/constitution_service.py` — Escaped `<6` HTML entity
- `src/agents/query_agent.py` — Updated default model to `gemini-2.5-flash`
- `src/agents/supervisor.py` — Fixed attribute access paths

---

## Post-Deploy Verification

- [x] Health endpoint returns 200 (`{"status":"healthy"}`)
- [x] Only one production service (`accountability-agent` in `us-central1`)
- [x] New revision `accountability-agent-00012-gdj` serving 100% traffic
- [x] Runtime shape preserved (CPU: 1, Memory: 512Mi, Timeout: 300s, Service Account: compute@developer.gserviceaccount.com)
- [x] `/start` creates user profile
- [x] `/checkin` completes full 5-question flow (hotfix: mood Q5 now completes successfully)
- [x] `/quickcheckin` completes in 30 seconds
- [x] `/briefing` generates morning briefing
- [x] `/insights` shows personalized patterns
- [x] `/goals` lists active goals
- [x] `/feedback` collects NPS rating (hotfix: HTML now renders correctly)
- [x] `/constitution` shows live stats overlay (hotfix: HTML parse error fixed)
- [x] `/delete_my_data` shows confirmation + deletes data
- [x] Streak break triggers recovery ritual
- [x] User broadcast sent: 2/2 users notified of v2.0 update
- [ ] Cron endpoints return 200 (morning_briefing, churn_prevention, predictive_intervention, weekly_nps)

---

## Known Limitations

1. **P4.1 Onboarding**: Schema flag exists but 5-step guided flow not implemented. New users still get instant profile.
2. **P4.5 Admin Dashboard**: `/admin_status` shows basic metrics. NPS and user health not yet integrated.
3. **NPS Follow-up**: Free-text feedback after NPS falls through to general handler (not captured separately).
4. **Settings Toggles**: `predictive_interventions_enabled` and `feature_hints_enabled` not exposed in `/settings` UI.
5. **Feature Flag Wiring**: Flags added to config but not all features gated at runtime (most are always-on).

---

## Rollback Plan

If critical issues discovered:
1. Re-deploy previous image tag
2. Disable features via config flags:
   ```bash
   gcloud run services update accountability-agent \
     --set-env-vars="ENABLE_MOOD_TRACKING=false,ENABLE_PREDICTIVE_INTERVENTIONS=false"
   ```
3. Monitor error rates and user complaints

---

## Metrics to Monitor

- Daily check-in rate (target: maintain >60%)
- Quick check-in adoption (target: >30% of users)
- Morning briefing engagement (target: >50% open rate)
- Feature discovery hint click-through (target: >20%)
- NPS score (target: >50)
- Streak recovery restart rate (target: >70% within 48h)

---

## Next Release (Phase 5 Completion)

- Progressive onboarding flow
- Admin dashboard enhancement
- NPS follow-up handler
- Settings toggle expansion
- Performance optimization (caching, indexes)
- Load testing at 1000-user scale

---

**Deployed by:** OpenCode Agent  
**Reviewed by:** OpenCode Agent (self-review)
