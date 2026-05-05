# Deployment Log — 2026-05-05

## Summary

Updated nightly reminder times from **9:00 PM → 9:30 PM → 10:00 PM** to **9:00 PM → 10:00 PM → 11:00 PM**.

## Changes Deployed

- `src/models/schemas.py` — `ReminderTimes` defaults: `second="22:00"`, `third="23:00"`
- `src/main.py` — Legacy cron docstrings + `reminder_tz_aware` tiers tuple updated
- `src/bot/telegram_bot.py` — Onboarding & timezone messages updated
- `src/utils/ux.py` — `/help` text updated
- `src/services/firestore_service.py` — Docstring updated
- `src/agents/pattern_detection.py` — Docstring reference updated
- `tests/test_fastapi_endpoints.py` — Test docstring updated
- `README.md` — Reminder status table updated
- `PRODUCT_GUIDE.md` — User journey copy updated
- `TECHNICAL_ARCHITECTURE.md` — Endpoint docs & scheduler table updated

## Deployment Details

| Item | Value |
|------|-------|
| **Date** | 2026-05-05 |
| **Time** | 12:52:27 UTC |
| **Image Tag** | `manual-20260505-181950` |
| **Revision** | `accountability-agent-00009-67f` |
| **Previous Revision** | `accountability-agent-00008-qvq` (2026-03-22) |
| **Deploy Method** | `gcloud run services update` (in-place) |
| **Service URL** | https://accountability-agent-450357249483.us-central1.run.app |

## Pre-Deploy Checks

- [x] Active GCP project: `accountability-agent`
- [x] Existing Cloud Run service confirmed in `us-central1`
- [x] Pre-deploy config snapshot saved to `/tmp/accountability-agent.predeploy.yaml`
- [x] `pytest tests`: **932 passed, 0 failed**
- [x] `python3 -m compileall src`: **0 errors**
- [x] Cloud Build image build & push: **SUCCESS**

## Post-Deploy Verification

- [x] Single Cloud Run service confirmed (`accountability-agent`)
- [x] New revision `accountability-agent-00009-67f` active and serving 100% traffic
- [x] Health endpoint: `{"status":"healthy","service":"constitution-agent",...}`
- [x] Runtime shape preserved:
  - CPU: 1
  - Memory: 512Mi
  - Concurrency: 80
  - Timeout: 300s
  - Service Account: `450357249483-compute@developer.gserviceaccount.com`
- [x] Post-deploy config snapshot saved to `/tmp/accountability-agent.postdeploy.yaml`

---

## Deployment 2 — Bug Fixes (Tier 1 Chart, HTML Parse Mode, Weekly Context)

### Summary

Fixed 3 production bugs: replaced meaningless sleep chart with Tier 1 Consistency chart, enabled HTML rendering in intervention messages, and injected weekly qualitative context into AI feedback prompts.

### Changes Deployed

- `src/services/visualization_service.py` — Replaced `generate_sleep_chart()` with `generate_tier1_consistency_chart()`; updated `generate_weekly_graphs()` mapping
- `src/agents/checkin_agent.py` — Added `_build_weekly_qualitative_section()`; injected into feedback prompt with explicit pattern-observation instructions
- `src/main.py` — Added `parse_mode='HTML'` to intervention `send_message()` call
- `src/agents/reporting_agent.py` — Updated graph caption to `📊 Tier 1 Consistency`; AI insights now use `sleep_days/7` instead of `avg_sleep`
- `src/utils/ux.py` — Help text example updated to `Show my Tier 1 consistency`
- `tests/test_visualization_service.py` — Updated tests for new chart function

### Deployment Details

| Item | Value |
|------|-------|
| **Date** | 2026-05-05 |
| **Time** | 14:02:19 UTC |
| **Image Tag** | `manual-20260505-192740` |
| **Revision** | `accountability-agent-00010-pfr` |
| **Previous Revision** | `accountability-agent-00009-67f` (2026-05-05 12:52:27 UTC) |
| **Deploy Method** | `gcloud run services update` (in-place) |
| **Service URL** | https://accountability-agent-450357249483.us-central1.run.app |

### Pre-Deploy Checks

- [x] Active GCP project: `accountability-agent`
- [x] Existing Cloud Run service confirmed in `us-central1`
- [x] Pre-deploy config snapshot saved to `/tmp/accountability-agent.predeploy.yaml`
- [x] `pytest tests`: **932 passed, 0 failed**
- [x] `python3 -m compileall src`: **0 errors**
- [x] Cloud Build image build & push: **SUCCESS**

### Post-Deploy Verification

- [x] Single Cloud Run service confirmed (`accountability-agent`)
- [x] New revision `accountability-agent-00010-pfr` active and serving 100% traffic
- [x] Health endpoint: `{"status":"healthy","service":"constitution-agent",...}`
- [x] Runtime shape preserved:
  - CPU: 1
  - Memory: 512Mi
  - Concurrency: 80
  - Timeout: 300s
  - Service Account: `450357249483-compute@developer.gserviceaccount.com`
- [x] Post-deploy config snapshot saved to `/tmp/accountability-agent.postdeploy.yaml`

## Rollback Plan

If issues arise, rollback to previous revision:

```bash
gcloud run services update accountability-agent \
  --platform=managed \
  --region=us-central1 \
  --image us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260505-181950
```

Or use revision traffic split:

```bash
gcloud run services update-traffic accountability-agent \
  --platform=managed \
  --region=us-central1 \
  --to-revisions accountability-agent-00009-67f=100
```
