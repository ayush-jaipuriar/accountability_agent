# Deployment & Testing Report - February 7, 2026

## Summary

This iteration completed 4 major tasks:
1. Fixed 22 pre-existing test failures (18 fails + 4 errors) + 1 additional LLM test
2. Deployed to production (Cloud Run revision `constitution-agent-00031-x6z`)
3. Added test coverage reporting (pytest-cov, 67% overall)
4. Prepared CI/CD plan for GitHub Actions (~$0.02/month)

---

## Task 1: Fix Pre-existing Test Failures

### Root Causes (6 Categories)

| Category | Files Affected | Failures | Root Cause |
|----------|---------------|----------|------------|
| Schema Evolution | test_compliance.py | 7 | Phase 3D added 6th Tier 1 item (skill_building), old tests still used 5-item constructor |
| Pydantic Validation | test_achievements.py, test_gamification_integration.py | 4 errors | CheckInResponses min_length=10 chars, fixtures used "None" (4 chars) |
| API Key Changes | test_achievements.py, test_gamification_integration.py | 4 | get_user_progress returns 'percentage' not 'unlock_percentage', 'rarity_breakdown' dict not flat keys |
| Rarity Case | test_gamification_integration.py | 1 | Achievement rarity values lowercase ("common") but tests checked titlecase ("Common") |
| Message Drift | test_streak.py | 2 | Milestone messages rewritten - "98% of people never reach" vs "top 2%" |
| Test Data | test_phase3d_*.py, test_checkin_agent.py | 4 | days_affected int not list, missing DailyCheckIn.metadata field, wrong assertion fields |

### Production Bugs Found & Fixed

**Bug 1: `achievement_service._all_tier1_complete()` (CRITICAL)**
- **File:** `src/services/achievement_service.py` line 455
- **Was:** `checkin.tier1.sleep.completed` (non-existent nested path)
- **Fixed to:** `checkin.tier1_non_negotiables.sleep` (flat boolean)
- **Impact:** `tier1_master` achievement could never be unlocked in production

**Bug 2: `achievement_service` zero_breaks_month check (CRITICAL)**
- **File:** `src/services/achievement_service.py` line 374
- **Was:** `c.tier1.zero_porn.completed`
- **Fixed to:** `c.tier1_non_negotiables.zero_porn`
- **Impact:** `zero_breaks_month` achievement could never be unlocked

**Bug 3: `pattern_detection.py` constitution mode access (previously fixed)**
- **File:** `src/agents/pattern_detection.py` line 896
- **Was:** `user.constitution.current_mode`
- **Fixed to:** `user.constitution_mode`

### Files Modified

| File | Changes |
|------|---------|
| `tests/test_compliance.py` | Added skill_building=True to all Tier1 fixtures, updated score assertions for 6-item denominator |
| `tests/test_achievements.py` | Fixed CheckInResponses min_length, achievement.id → achievement_id, get_user_progress keys |
| `tests/test_gamification_integration.py` | Fixed CheckInResponses, rarity case (lowercase), progress dict keys |
| `tests/test_streak.py` | Updated milestone message assertions to match actual text |
| `tests/test_phase3d_career_mode.py` | Fixed employed mode assertion (check question field not description) |
| `tests/test_phase3d_integration.py` | Removed DailyCheckIn.metadata assignment, fixed days_affected to be list |
| `tests/test_checkin_agent.py` | Made LLM assertion flexible (accept "thirty" or "30") |
| `src/services/achievement_service.py` | Fixed _all_tier1_complete() and zero_breaks_month check |

---

## Task 2: Deploy to Production

### Deployment Details

- **Platform:** Google Cloud Run (managed)
- **Region:** asia-south1
- **Revision:** constitution-agent-00031-x6z
- **Service URL:** https://constitution-agent-450357249483.asia-south1.run.app
- **Image:** gcr.io/accountability-agent/constitution-agent:latest
- **Architecture:** linux/amd64 (cross-compiled from ARM Mac via docker buildx)

### Configuration

```
Memory: 512Mi
CPU: 1
Min instances: 0 (scale to zero)
Max instances: 3
Timeout: 300s
Environment: ENVIRONMENT=production
```

### Smoke Test Results

- `/health` endpoint: **PASSED** (status: healthy, firestore: ok)
- Webhook endpoint: Configured and receiving Telegram updates
- Zero-downtime deployment confirmed

---

## Task 3: Test Coverage Reporting

### Setup

- **Tool:** pytest-cov 4.1.0 (wraps coverage.py)
- **Config:** pyproject.toml with branch coverage enabled
- **Output:** Terminal (term-missing) + HTML (htmlcov/)

### Coverage Results (67% overall)

| Module | Coverage | Notes |
|--------|----------|-------|
| schemas.py | 95% | Data models well tested |
| export_service.py | 98% | Export flows comprehensive |
| visualization_service.py | 99% | Graph generation well tested |
| social_service.py | 92% | Social features well covered |
| analytics_service.py | 80% | Stats calculations covered |
| telegram_bot.py | 78% | Command handlers tested |
| achievement_service.py | 76% | Gamification tested |
| pattern_detection.py | 73% | 9 patterns tested |
| conversation.py | 70% | Check-in flow tested |
| reporting_agent.py | 70% | Report generation tested |
| main.py | 62% | FastAPI endpoints tested |
| firestore_service.py | 46% | Mostly mocked in tests |
| query_agent.py | 48% | LLM-dependent, hard to test |
| stats_commands.py | 6% | Needs dedicated test file |
| llm_service_gemini.py | 0% | Alternative LLM service, unused |

### How to Run

```bash
# Run with coverage (automatic via pyproject.toml)
python3 -m pytest tests/

# View HTML report
open htmlcov/index.html
```

---

## Task 4: CI/CD Plan (Awaiting Approval)

### Architecture

- **Workflow 1 (test.yml):** Run on every push/PR → install deps → pytest → coverage report
- **Workflow 2 (deploy.yml):** Run on merge to main → tests → Docker build (amd64) → push GCR → deploy Cloud Run

### Cost: ~$0.02/month

- GitHub Actions: $0 (within 2,000 free minutes/month for private repos)
- GCR Storage: ~$0.02/month
- No additional Cloud Run costs

---

## Final Test Results

```
488 passed, 0 failed, 0 errors
67% code coverage (branch coverage enabled)
20 test files across tests/ directory
```

## Next Steps

1. **CI/CD Implementation** (pending user approval of plan)
2. **Increase coverage** - target 75%+ (especially stats_commands.py at 6%)
3. **Monitor production** for 24-48 hours
4. **Invite test users** to try the deployed bot
