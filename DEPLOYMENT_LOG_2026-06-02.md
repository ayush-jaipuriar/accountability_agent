# Deployment Log: v2.1 Frictionless Mobile Check-In & Rest Day Compliance

**Date:** 2026-06-02  
**Release:** v2.1 (Minor)  
**Phases Deployed:** Mobile check-in redesign, rest-day compliance updates, micro-habit scoring.  
**Test Count:** 1051 passed, 0 failed  
**Pre-Deploy Check:** 16/16 passed  
**Image Tag:** `manual-20260602-155400`  
**Revision:** `accountability-agent-00014-cr5`  
**Deployed At:** 2026-06-02 10:26:26 UTC  

---

## Deployment Summary

This release resolves user engagement friction by transitioning check-in steps Q2-Q5 to frictionless button taps on mobile devices. It also corrects a defect where rest days were penalized, and introduces micro-habit tracking to prevent streak breaks and habit abandonment.

---

## Features Deployed

### 1. Frictionless UX Redesign
- Replaced subjective essay text questions with button rating interfaces on Telegram (Alignment 1–10, Energy 1–10, Mood 1–10).
- Introduced a final step with a single optional reflection text note or voice note.
- Added a `parse_reflection_note` Gemini-based service to structure optional free-form note entries into legacy database schemas.

### 2. Scheduled Rest Day Compliance
- Updated compliance calculations and target completion checks to treat rest days (`tier1.training or tier1.is_rest_day`) as compliant.

### 3. Micro-Habit Streak Preservation
- Added properties (`sleep_met`, `deep_work_met`, `skill_building_met`) matching micro-habit targets (6h sleep, 0.5h deep work, 0.5h skill building) to keep streaks alive.
- Retained full analytics tracking for full targets (`sleep_met_full`, etc.).

---

## Files Changed

### New Files
- `tests/test_frictionless_checkin.py`

### Modified Files
- `src/models/schemas.py` — Continuous data mapping and micro-habit checks
- `src/bot/conversation.py` — State machine flow, callback query endpoints, reflection parser integration
- `src/bot/telegram_bot.py` — Correction and handler registrations
- `src/utils/compliance.py` — Rest day evaluation logic
- `tests/test_adaptive_checkin.py` — Adjusted transition test assertions
- `tests/test_handler_integration.py` — Adjusted callback query assertions

---

## Deployment Commands Executed

```bash
# Pre-deploy checks
python3 scripts/pre_deploy_check.py

# Cloud Build submission
gcloud builds submit --tag us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260602-155400

# Service revision rollout
gcloud run services update accountability-agent \
  --platform=managed \
  --region=us-central1 \
  --image us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260602-155400
```

---

## Post-Deploy Verification Results

- [x] Health endpoint returns 200 (`{"status":"healthy"}`)
- [x] Only one production service active (`accountability-agent` in `us-central1`)
- [x] New revision `accountability-agent-00014-cr5` serving 100% traffic
- [x] Runtime shape fully preserved:
  - **Memory:** 512Mi
  - **Service Account:** 450357249483-compute@developer.gserviceaccount.com
- [x] Environment variables and secrets compared and matched perfectly

---

**Deployed by:** Antigravity Agent  
**Reviewed by:** Antigravity Agent (self-review)
