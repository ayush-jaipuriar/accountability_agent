# Deployment Log — 2026-08-04

## Summary
- **Target Service:** `accountability-agent`
- **Region:** `us-central1`
- **GCP Project:** `accountability-agent`
- **Production URL:** `https://accountability-agent-450357249483.us-central1.run.app`
- **Image Tag:** `manual-20260804-233600`
- **Revision:** `accountability-agent-00023-vcd`
- **Test Suite Status:** 1073 / 1073 tests passed (100%)
- **Health Check Status:** `{"status":"healthy","service":"constitution-agent","version":"3.0.0","environment":"production","checks":{"firestore":"ok"}}`

---

## Behavior Change Fixes Released

This deployment addresses the behavior change failures identified during deep impact analysis (compliance score decline from 70% → 63%, consistency halving, and collapse of deep work / skill building habits).

### 1. Scoring Reform (v3 Proportional Credit)
- **Problem:** Binary 0/16.7% scoring punished partial effort (e.g. 1.5h deep work scored 0%), creating learned helplessness.
- **Fix:** Refactored `calculate_compliance_score()` and `calculate_compliance_score_normalized()` in `src/utils/compliance.py` to grant proportional credit for continuous habits (`sleep_hours`, `deep_work_hours`, `skill_building_hours`).
- **Impact:** 1.5h deep work now scores 75% for that habit instead of 0%. 0.7h skill building scores 35%. Effort is reflected in the score.

### 2. Progress Bar Visual Feedback
- **Problem:** Check-in feedback only showed pass/fail booleans and a summary score.
- **Fix:** Added `format_progress_summary()` to `src/bot/conversation.py` that generates visual progress bars (`Deep Work: 1.5h/2h ██████░░ 75%`) in check-in complete messages.

### 3. Ghosting Intervention Reform
- **Problem:** Ghosting messages used rigid escalation ("EMERGENCY", "constitution violation") asking for full `/checkin`, creating guilt and desensitization across 182 interventions.
- **Fix:** Refactored `_build_ghosting_intervention()` in `src/agents/intervention.py` to lead with empathy, lower friction:
  - Day 2: Minimal emoji reply prompt (`🟢🟡🔴`) or `/quickcheckin`
  - Day 3: Suggests 30-second `/quickcheckin`
  - Day 4: Asks a single low-friction question ("What's one thing you did for yourself today?")
  - Day 5+: Empathy-first choices + partner alert + shield options

### 4. Post-Ghosting Return Reason Flow
- **Problem:** Users returned after ghosting with zero context on why they disappeared.
- **Fix:** Added return-reason prompt flow in `src/bot/conversation.py` for users returning after 2+ days absence ("Life got busy", "Felt overwhelmed", "Didn't want to report failure", "Check-in felt pointless").
- **Storage:** Saved in `DailyCheckIn.return_reason` for future intervention adaptation.

---

## Pre-Deploy Verification Checklist
- [x] GCP Project confirmed (`accountability-agent`)
- [x] Existing service verified (`accountability-agent`)
- [x] Pre-deploy config export saved (`/tmp/accountability-agent.predeploy.yaml`)
- [x] Source compilation sanity check passed (`python3 -m compileall src`)
- [x] Pre-deploy validation script passed (`python3 scripts/pre_deploy_check.py` — 17/17 checks)
- [x] Test suite passed (`pytest tests` — 1073/1073 tests passed)
- [x] Image built and pushed (`us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260804-233600`)
- [x] Service updated in-place (`gcloud run services update`)

## Post-Deploy Verification Checklist
- [x] Exactly one production service active (`accountability-agent`)
- [x] New revision created on same service (`accountability-agent-00023-vcd`)
- [x] Live health check returned 200 OK (`/health`)
