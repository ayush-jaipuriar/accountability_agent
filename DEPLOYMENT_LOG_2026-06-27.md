# Deployment Log: 2026-06-27

**Date:** 2026-06-27  

---

## Deployment 2: Daily Focus Engine (To-Dos) Integration (v3.0.0)

- **Phases Deployed**: Daily Focus Engine (To-Dos) + Mid-day Nudges + App Metadata Version Bump (v3.0.0)
- **Test Count**: 8 passed (new focus engine suite), 1,072 passed total
- **Pre-Deploy Check**: 16/16 passed
- **Image Tag**: `manual-20260627-191300`
- **Revision**: `accountability-agent-00020-m68`
- **Deployed At**: 2026-06-27 19:16:51 UTC

### Features Deployed
1. **Interactive Focus Briefs**: Integrated interactive checkboxes `[✅ Done]` and `[⬜️ Pending]` inline on morning briefs with live edit-in-place updates on Telegram. Added CBT `🛡️ Need Support` callback bridging.
2. **Dynamic Check-in reflection**: Checked-in responses dynamically classify task metrics and prompt the user about missed or completed commitments for reflection.
3. **Task Compliance Scoring**: Implemented `calculate_task_score` following the 80% Tier 1 habits + 20% Daily Tasks compliance split (with a dynamic weighting matrix depending on committed task counts).
4. **FastAPI Mid-day Nudge**: Added `/cron/midday_nudge` endpoint scheduled at 3:00 PM local time to check incomplete primary tasks and nudge users.
5. **App Version Metadata Bump**: Updated system health/root endpoints to serve `3.0.0` version info.

---

## Deployment 1: Scheduled Morning Briefing & LLM Personalization

- **Phases Deployed**: Scheduled Morning Briefing & LLM Personalization
- **Test Count**: 15 passed (briefing suite), 1,064 passed total
- **Pre-Deploy Check**: 16/16 passed
- **Image Tag**: `manual-20260627-162923`
- **Revision**: `accountability-agent-00018-kz9`
- **Deployed At**: 2026-06-27 16:32:09 UTC

### Features Deployed
1. **Timezone Duplication Bug Fix**: Patched timezone briefing sending duplicates.
2. **Gemini Personalization Engine**: Added personalized coach's guidance and daily obstacle-mitigation advice.
3. **Closing the Loop on Obstacles**: Surfaced yesterday's expected obstacle.
4. **Goals & Challenges Integration**: Listed active goals and challenges.
5. **GCP Scheduler Integration**: Scheduled morning briefing cron job.
