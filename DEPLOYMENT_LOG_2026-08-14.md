# Deployment Log — 2026-08-14

## Summary
- **Target Service:** `accountability-agent`
- **Region:** `us-central1`
- **GCP Project:** `accountability-agent`
- **Production URL:** `https://accountability-agent-450357249483.us-central1.run.app`
- **Image Tag:** `manual-20260814-202312`
- **Revision:** `accountability-agent-00025-ggg`
- **Test Suite Status:** 1081 / 1081 tests passed (100%)
- **Health Check Status:** `{"status":"healthy","service":"constitution-agent","version":"3.0.0","environment":"production","uptime":"0h 0m","checks":{"firestore":"ok"}}`

---

## Features Released (v3.2.0)

### 1. Next-Day Top 3 To-Dos Collection
- **Functionality:** At the conclusion of daily check-in, users are guided through 3 distinct sequential prompts:
  1. `🎯 Primary Focus (#1 Must-Do)`
  2. `🥈 Secondary Task (#2)`
  3. `🥉 Secondary Task (#3)`
- **Storage:** Persisted atomically to Firestore at `daily_tasks/{user_id}/tasks/{date}` and committed for the upcoming date via `task_service.save_committed_task_list()`.

### 2. Next-Day Interactive To-Do Verification & 80/20 Compliance Scoring
- **Functionality:** At check-in start, committed tasks for the current day are rendered as interactive inline toggle buttons (`[ ✅ / ❌ ]`).
- **Scoring Formula:**
  - Weighted task scoring: Primary task accounts for 50%, Secondaries account for 25% each.
  - Overall compliance blending: `(Tier 1 Score * 0.8) + (To-Do Score * 0.2)`.
- **Visual Feedback:** Added visual progress bar and task execution breakdown to `format_progress_summary()`.

### 3. Partner Weekly Strongest & Weakest Areas Report
- **Functionality:** Aggregates 7-day habit execution across all Tier 1 habits and to-dos via `calculate_partner_weekly_performance()`.
- **Output:** Identifies the user's top 2 strongest habits and top 2 growth/weakest areas, accompanied by actionable partner coaching tips.
- **Delivery:** Wired into the Sunday weekly reporting agent cycle and dispatched to linked partners via Telegram.

---

## Pre-Deploy Verification Checklist
- [x] GCP Project confirmed (`accountability-agent`)
- [x] Existing service verified (`accountability-agent` in `us-central1`)
- [x] Pre-deploy config export saved (`/tmp/accountability-agent.predeploy.yaml`)
- [x] Source compilation sanity check passed (`python3 -m compileall src`)
- [x] Pre-deploy validation script passed (`python3 scripts/pre_deploy_check.py` — 17/17 checks)
- [x] Test suite passed (`pytest tests` — 1081/1081 tests passed)
- [x] Image built and pushed (`us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260814-202312`)
- [x] Service updated in-place (`gcloud run services update accountability-agent`)

## Post-Deploy Verification Checklist
- [x] Exactly one production service active (`accountability-agent`)
- [x] New revision created on same service (`accountability-agent-00025-ggg`)
- [x] Live health check returned 200 OK (`/health`)
- [x] In-place service identity and URL preserved
