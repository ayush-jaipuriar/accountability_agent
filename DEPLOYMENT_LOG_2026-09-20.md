# Deployment Log: Security Hardening & Webhook Defense-in-Depth

**Date:** 2026-09-20 (UTC: 2026-09-19 19:28:51)  
**Release:** Security Fix & Webhook Hardening  
**Target:** Cloud Run `accountability-agent` in `us-central1`  
**Image Tag:** `manual-20260919-192541`  
**Revision:** `accountability-agent-00034-kw8` (100% traffic)  
**Service URL:** `https://accountability-agent-450357249483.us-central1.run.app`  
**Test Suite:** 1259 passed, 0 failed  
**Pre-Deploy Check:** 18/18 passed  

---

## 1. Incident Root Cause Analysis (RCA)

- **Symptom**: Bot check-ins and command interactions (`/checkin`, `/partner`) stopped responding.
- **Root Cause**: A Telegram bot token was committed to `scripts/broadcast_notification_standalone.py` in the public GitHub repository on 2026-05-05 (commit `3e5cc9f`). Public GitHub token scrapers hijacked the Telegram webhook to `https://tele.goldenherd.com/tg/webhook/8197561499`. The external server returned Cloudflare 530 errors, causing all Telegram webhook updates to queue and fail.
- **User Constraint**: "dont make it private, figure out a safer way to do it". Keep the repository public while engineering a multi-layered defense-in-depth model.

---

## 2. Implemented Defense-in-Depth Architecture

### Layer 1: Secret Elimination & Sanitization
- Revoked leaked bot token and provisioned new token into Google Secret Manager (`telegram-bot-token` version 2).
- Sanitized `scripts/broadcast_notification_standalone.py` to read `TELEGRAM_BOT_TOKEN` strictly from environment variables.
- Sanitized documentation and study guides (`COMPREHENSIVE_STUDY_GUIDE.md`, `READY_TO_COMMIT.md`) to use safe placeholders.

### Layer 2: Automated Leak Prevention (Pre-Commit & CI)
- **`scripts/secret_scanner.py`**: Scans files and git staged diffs for:
  - Telegram bot tokens (`[0-9]{8,10}:[A-Za-z0-9_-]{35}`)
  - Google / Gemini API keys (`AIzaSy...`)
  - Private key certificates (`BEGIN ... PRIVATE KEY`)
  - GCP service account JSON credentials
  - Sensitive files (`.env`, `.env.*`, `service_account*.json`, `*.predeploy.yaml`)
- **Git Hooks**: Configured `.githooks/pre-commit` and `core.hooksPath = .githooks` to automatically reject commits containing secrets or sensitive files.
- **Pre-Deploy Gate**: Integrated secret scanning into `scripts/pre_deploy_check.py` as pre-flight check #0.
- **GitHub Actions**: Added `.github/workflows/security-scan.yml` running the scanner on all PRs and pushes.

### Layer 3: Webhook Request Authentication (`secret_token`)
- Configured Telegram webhook registration with `secret_token` via `set_webhook(url, secret_token=...)`.
- In `src/config.py`, derived a deterministic SHA-256 token from the bot token (or optional `TELEGRAM_WEBHOOK_SECRET` override).
- In `src/main.py` (`POST /webhook/telegram`), incoming requests are validated against header `X-Telegram-Bot-Api-Secret-Token`.
- Unauthenticated or forged requests are rejected with `HTTP 403 Forbidden`.

### Layer 4: Automated Drift Detection & Self-Healing
- Implemented `verify_and_heal_webhook(expected_url, secret_token)` in `TelegramBotManager`.
- Integrated webhook health reporting and self-healing into:
  - `GET /health`: Checks current webhook URL against expected URL; auto-reclaims webhook if drift is detected.
  - `POST /cron/reminder_tz_aware`: Automatically validates and heals webhook registration every 15 minutes during background cron runs.

---

## 3. Post-Deploy Verification

- [x] Only one Cloud Run service exists: `accountability-agent` in `us-central1`.
- [x] New revision `accountability-agent-00034-kw8` serving 100% of traffic.
- [x] `/health` returns `200 OK` with:
  - `"checks": {"firestore": "ok", "webhook": "ok"}`
  - `"webhook_status": {"drift_detected": false, "reclaimed": false, "pending_update_count": 0}`
- [x] Webhook endpoint rejects forged requests:
  - `curl -X POST .../webhook/telegram` without header -> `HTTP 403 Forbidden` (`{"ok":false,"error":"Forbidden: invalid secret token"}`).
- [x] All 1259 tests passed (`pytest tests`).
- [x] All 18 pre-deploy checks passed (`python3 scripts/pre_deploy_check.py`).
- [x] Secret scanner passed on all repository files (`python3 scripts/secret_scanner.py --all`).
- [x] Changes pushed to GitHub repository `main` branch.
