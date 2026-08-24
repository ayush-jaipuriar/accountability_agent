# Deployment Log — 2026-08-24

## Summary
- **Service Name**: `accountability-agent`
- **Region**: `us-central1`
- **GCP Project**: `accountability-agent`
- **Production URL**: `https://accountability-agent-450357249483.us-central1.run.app`
- **Revision**: `accountability-agent-00028-v9d`
- **Container Image Tag**: `us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260824-192550`
- **Release Phase**: Phase 3.1 — Unified Interactive Hubs & Streamlined Check-In UX

---

## Features & Improvements Deployed

1. **5 Core Unified Interactive Hubs**:
   - `/today`: Master Daily Driver (daytime focus items with live completion toggles & 1-tap check-in launch).
   - `/progress`: Executive Performance Dashboard with in-place time-window switching (`7D`, `30D`, `YTD`, `All-Time`), visual chart pack launcher, and export actions.
   - `/partner`: Accountability Partner Arena with mutual check-in status and 1-tap 7-Day duel creations.
   - `/goals`: SMART Goals Studio with 1-tap template presets and 10-block progress visualizers.
   - `/settings`: Interactive Control Center consolidating modes, career stage, timezone, briefing switches, streak shields, and GDPR deletion.
2. **Predictive Baseline Defaults**:
   - `compute_predictive_baseline(user_id, checkin_date)` in `src/services/checkin_baseline.py` calculates honest baseline defaults from rolling 3-day history and daytime tasks.
3. **Single Unified Hero Completion Card**:
   - Consolidated `finish_checkin()` in `src/bot/conversation.py` to deliver habit breakdown, AI takeaway, support focus, and milestone/duel updates in one post-checkin message.
4. **100% Backward Compatibility**:
   - Retained direct command access for all 43 legacy commands.

---

## Pre-Deploy Validation Gates
- `pytest tests`: 1,114 passed (100% green).
- `python3 -m compileall src`: 0 errors.
- `python3 scripts/pre_deploy_check.py`: 17/17 checks passed.

---

## Post-Deploy Verification
1. **Single Production Service**: Confirmed only `accountability-agent` in `us-central1`.
2. **Active Revision**: `accountability-agent-00028-v9d` deployed and serving 100% of traffic.
3. **Live Health Check**:
   ```json
   {"status":"healthy","service":"constitution-agent","version":"3.0.0","environment":"production","uptime":"0h 0m","checks":{"firestore":"ok"},"metrics_summary":{"checkins_total":0,"commands_total":0,"errors_total":0}}
   ```
4. **Runtime Shape**:
   - Concurrency: 80
   - CPU: 1
   - Memory: 512Mi
   - Timeout: 300s
   - Service Account: `450357249483-compute@developer.gserviceaccount.com`

---

## Release Revision: `accountability-agent-00029-8k7` (3-Card Check-In Flow Fix)

### Issue Addressed
- Fixed `AttributeError: 'NoneType' object has no attribute 'reply_text'` on callback queries entering check-in.
- Upgraded check-in state machine to the modern **3-Card Flow with Predictive Baselines**:
  - **Card 1: Habit Matrix** — Interactive card pre-populated with honest predictive baselines with instant in-place increment/decrement/training toggles (`[ ➖ / ➕ ]`).
  - **Card 2: Energy & Reflection** — 1-10 rating buttons + optional reflection note/voice note.
  - **Card 3: Tomorrow's Focus Lock** — 1-tap `[ 🎯 Lock Focus & Submit Check-In ]`.
  - **Single Hero Card** — Output with all habit progress, coach takeaways, duel updates, and earned badges.

### Pre-Deploy Verification
- Automated tests: 1119 passed (`pytest tests`)
- Pre-deploy check: 17/17 passed (`python3 scripts/pre_deploy_check.py`)
- Python compile sanity check: PASSED (`python3 -m compileall src`)

### Deployment Details
- Image: `us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260824-194907`
- Revision: `accountability-agent-00029-8k7`
- Health check: `https://accountability-agent-450357249483.us-central1.run.app/health` returned `200 OK`
- Live smoke tests: PASSED (`python3 scripts/test_live_smoke.py`)

