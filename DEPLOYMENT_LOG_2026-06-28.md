# Deployment Log: 2026-06-28

**Date:** 2026-06-28  

---

## Deployment 2: Static Analysis Gate Integration (v3.0.2)

- **Phases Deployed**: static analysis linting gate + telegram bot datetime fixes
- **Test Count**: 17 passed (endpoints suite), 1,073 passed total
- **Pre-Deploy Check**: 17/17 passed
- **Image Tag**: `manual-20260628-110400`
- **Revision**: `accountability-agent-00022-cv4`
- **Deployed At**: 2026-06-28 11:06:32 UTC

### Features Deployed
1. **Integrated Static Analysis (Pyflakes)**: Integrated `pyflakes` check into the `scripts/pre_deploy_check.py` validation runner. This checks for undefined variables, syntax errors, and other namespace collisions. Critical failures halt the deployment check, while style/unused warnings remain non-blocking.
2. **Fixed Undefined Telegram Bot Names**: Fixed missing module-level import of `datetime` and `timedelta` in `src/bot/telegram_bot.py`.
3. **Pushed to Git**: All code and validation changes pushed to the remote repository.

---

## Deployment 1: Morning Briefing Cron Keyboard Hotfix (v3.0.1)

- **Phases Deployed**: morning_briefing endpoint hotfix
- **Test Count**: 1 passed (new endpoints test), 1,073 passed total
- **Pre-Deploy Check**: 16/16 passed
- **Image Tag**: `manual-20260628-105400`
- **Revision**: `accountability-agent-00021-df7`
- **Deployed At**: 2026-06-28 10:56:49 UTC

### Features & Hotfixes Deployed
1. **Cron Morning Briefing NameError Hotfix**: Resolved a runtime `NameError` where `task_list` was referenced but not defined inside the `/cron/morning_briefing` handler in `src/main.py`. The endpoint now correctly resolves `task_list` using `task_service` relative to the target user's local timezone date.
2. **Added Endpoint Test Case**: Implemented `TestMorningBriefingCron` inside `tests/test_fastapi_endpoints.py` to prevent regression and ensure `/cron/morning_briefing` is fully covered.
