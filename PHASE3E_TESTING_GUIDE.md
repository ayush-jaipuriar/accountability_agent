# Phase 3E Testing Guide
## Comprehensive Testing Checklist

**Purpose:** Ensure all Phase 3E features work correctly before production deployment  
**Testing Environment:** Docker + Python 3.11 + Production-like configuration  
**Required:** Local Firestore emulator OR test project in GCP

---

## 🎯 Testing Overview

### Features to Test
1. ✅ Quick Check-In Mode (Tier 1-only, weekly limit)
2. ✅ Query Agent (natural language queries)
3. ✅ Stats Commands (/weekly, /monthly, /yearly)
4. ✅ Cron Job (weekly reset)
5. ✅ Integration (all features work together)

### Test Data Setup
Before testing, you'll need:
- At least 1 test user created via /start
- 7+ check-ins for weekly stats
- 30+ check-ins for monthly stats (optional but recommended)
- Mix of compliance scores (100%, 80%, 60%) for variety

---

## 📋 Pre-Testing Checklist

### Environment Setup

```bash
# 1. Build Docker image
docker build -t accountability-agent:phase3e-test .

# 2. Set environment variables
export GCP_PROJECT_ID="your-test-project"
export TELEGRAM_BOT_TOKEN="your-test-bot-token"
export VERTEX_AI_LOCATION="us-central1"
export GEMINI_MODEL="gemini-2.0-flash-exp"

# 3. Run container (local testing)
docker run -p 8080:8080 \
    -e GCP_PROJECT_ID="$GCP_PROJECT_ID" \
    -e TELEGRAM_BOT_TOKEN="$TELEGRAM_BOT_TOKEN" \
    -e VERTEX_AI_LOCATION="$VERTEX_AI_LOCATION" \
    -e GEMINI_MODEL="$GEMINI_MODEL" \
    accountability-agent:phase3e-test

# 4. Verify health
curl http://localhost:8080/health
# Should return: {"status": "ok"}
```

### Test User Setup

```bash
# In Telegram:
1. Send /start to bot
2. Complete onboarding
3. Do 7+ check-ins with varied compliance:
   - 3 days with 100% compliance
   - 2 days with 80-90% compliance
   - 2 days with 60-70% compliance
```

---

## 🧪 Test Suite 1: Quick Check-In Mode

### Test 1.1: Basic Quick Check-In Flow

**Objective:** Verify quick check-in completes successfully

**Steps:**
1. Send `/quickcheckin` to bot
2. Verify intro message shows:
   - "⚡ Quick Check-In Mode"
   - "Available This Week: 2/2 quick check-ins"
   - Reset date (next Monday)
3. Answer all 6 Tier 1 questions (use inline buttons)
4. Verify completion message shows:
   - "⚡ Quick Check-In Complete!"
   - Compliance score
   - Current streak
   - Abbreviated feedback (1-2 sentences)
   - "Quick Check-Ins This Week: 1/2"

**Expected Result:** ✅ Quick check-in completes in ~2 minutes

**Verification:**
```bash
# Check Firestore
# daily_checkins/{user_id}/checkins/{date}
# Should have: is_quick_checkin = true

# Check user document
# users/{user_id}
# Should have: quick_checkin_count = 1
# Should have: quick_checkin_used_dates = [today's date]
```

**Pass/Fail:** ________

---

### Test 1.2: Weekly Limit Enforcement

**Objective:** Verify limit prevents 3rd quick check-in

**Steps:**
1. Complete 1st quick check-in (if not done in Test 1.1)
2. Wait 24 hours OR change date in Firestore
3. Complete 2nd quick check-in
4. Verify counter shows "1/2" after 2nd completion
5. Try 3rd quick check-in immediately
6. Verify error message:
   - "❌ Quick Check-In Limit Reached"
   - Shows dates of 2 used quick check-ins
   - Shows reset date (next Monday)
   - Suggests /checkin instead

**Expected Result:** ✅ 3rd quick check-in blocked

**Pass/Fail:** ________

---

### Test 1.3: Full Check-In Still Works

**Objective:** Verify full check-in unaffected by quick check-in limit

**Steps:**
1. After hitting quick check-in limit
2. Send `/checkin`
3. Complete full check-in (4 questions)
4. Verify full feedback received (3-4 paragraphs)

**Expected Result:** ✅ Full check-in works normally

**Pass/Fail:** ________

---

### Test 1.4: Abbreviated Feedback Quality

**Objective:** Verify abbreviated feedback is concise and relevant

**Steps:**
1. Complete quick check-in with:
   - All Tier 1 items: Yes
2. Verify feedback mentions wins
3. Complete another quick check-in with:
   - Some Tier 1 items: No
4. Verify feedback suggests focus area

**Expected Result:** 
- ✅ 1-2 sentences only
- ✅ Specific (mentions actual Tier 1 items)
- ✅ Encouraging tone

**Pass/Fail:** ________

---

### Test 1.5: Streak Increments Normally

**Objective:** Verify quick check-ins count toward streak

**Steps:**
1. Note current streak before quick check-in
2. Complete quick check-in
3. Verify streak incremented by 1
4. Send `/status`
5. Verify streak matches

**Expected Result:** ✅ Streak increments for quick check-ins

**Pass/Fail:** ________

---

## 🧪 Test Suite 2: Query Agent

### Test 2.1: Compliance Query

**Objective:** Verify compliance average query works

**Steps:**
1. Send message: "What's my average compliance this month?"
2. Verify response includes:
   - "📊 Your average compliance..."
   - Specific percentage (e.g., "87%")
   - Breakdown (days tracked, 100% days, etc.)
   - Encouragement or context

**Expected Result:** ✅ Natural language response with specific data

**Pass/Fail:** ________

---

### Test 2.2: Streak Query

**Objective:** Verify streak information query works

**Steps:**
1. Send: "Show me my longest streak"
2. Verify response includes:
   - Current streak
   - Longest streak
   - Period of longest streak (if available)
   - Days until beating record

**Expected Result:** ✅ Detailed streak information

**Pass/Fail:** ________

---

### Test 2.3: Training History Query

**Objective:** Verify training history query works

**Steps:**
1. Send: "When did I last miss training?"
2. Verify response includes:
   - Date of last missed training
   - Recent 5-7 days training history
   - Consistency percentage

**Expected Result:** ✅ Training history with dates

**Pass/Fail:** ________

---

### Test 2.4: Sleep Trends Query

**Objective:** Verify sleep analysis query works

**Steps:**
1. Send: "How much am I sleeping?"
2. Verify response includes:
   - Average sleep hours
   - Days above/below 7 hours target
   - Trend (improving/declining/stable)

**Expected Result:** ✅ Sleep statistics with trend

**Pass/Fail:** ________

---

### Test 2.5: Pattern Frequency Query

**Objective:** Verify pattern detection query works

**Steps:**
1. Send: "How often do I get sleep degradation?"
2. Verify response includes:
   - Pattern count
   - Most common pattern (if multiple)
   - Time period analyzed

**Expected Result:** ✅ Pattern frequency information

**Pass/Fail:** ________

---

### Test 2.6: Goal Progress Query

**Objective:** Verify career goal tracking query works

**Steps:**
1. Send: "Am I on track for June goals?"
2. Verify response includes:
   - Skill building consistency
   - Career mode
   - Target (₹28-42 LPA June 2026)
   - Progress assessment

**Expected Result:** ✅ Career progress information

**Pass/Fail:** ________

---

### Test 2.7: Fast Keyword Detection

**Objective:** Verify keyword detection saves API calls

**Steps:**
1. Check logs before sending query
2. Send: "what's my streak?"
3. Check logs after
4. Verify log shows: "📊 Fast query detection: ... → query"
5. Verify NO LLM call made (check logs for "Generating" messages)

**Expected Result:** ✅ Query routed without LLM call

**Pass/Fail:** ________

---

### Test 2.8: Unknown Query Handling

**Objective:** Verify graceful handling of unclear queries

**Steps:**
1. Send: "hello how are you?"
2. Verify response is NOT treated as query
3. Verify fallback response or general conversation

**Expected Result:** ✅ Doesn't try to query data for non-query messages

**Pass/Fail:** ________

---

## 🧪 Test Suite 3: Stats Commands

### Test 3.1: /weekly Command

**Objective:** Verify weekly stats display correctly

**Steps:**
1. Send `/weekly`
2. Verify response includes ALL sections:
   - Header with date range
   - Compliance (avg + trend)
   - Streaks (current + check-in rate)
   - Tier 1 performance (all 6 items)
   - Patterns
   - Encouragement

**Expected Result:** ✅ Complete weekly summary

**Sample Output:**
```
📊 Last 7 Days (Feb 1-7)

Compliance:
Average: 89%
Trend: ↗️ +5%

Streaks:
Current: 24 days 🔥
Check-ins: 7/7 (100%)

Tier 1 Performance:
• Sleep: 6/7 days (7.2 hrs avg)
• Training: 6/7 days
• Deep Work: 7/7 days (2.3 hrs avg)
• Skill Building: 5/7 days
• Zero Porn: 7/7 days ✅
• Boundaries: 6/7 days

Patterns: None detected ✨

Strong week! You're building solid habits. 🎯
```

**Pass/Fail:** ________

---

### Test 3.2: /monthly Command

**Objective:** Verify monthly stats display correctly

**Steps:**
1. Send `/monthly`
2. Verify response includes:
   - Date range (last 30 days)
   - Compliance with best/worst week
   - Streaks
   - Tier 1 averages (not just days, but hours)
   - Achievement count (if any)
   - Pattern summary
   - Social proof ("Top X% of users")

**Expected Result:** ✅ Complete monthly summary

**Pass/Fail:** ________

---

### Test 3.3: /yearly Command

**Objective:** Verify yearly stats display correctly

**Steps:**
1. Send `/yearly`
2. Verify response includes:
   - Year-to-date header
   - Overview (days tracked, completion %)
   - Streaks
   - Monthly breakdown (Jan, Feb, etc.)
   - Total achievements
   - Pattern count
   - Career progress
   - Link to /dashboard

**Expected Result:** ✅ Complete yearly summary

**Pass/Fail:** ________

---

### Test 3.4: Stats with No Data

**Objective:** Verify graceful handling when no data

**Steps:**
1. Create new test user
2. Don't do any check-ins
3. Send `/weekly`
4. Verify friendly message:
   - "No check-in data available yet"
   - Suggests /checkin to start

**Expected Result:** ✅ Helpful message for new users

**Pass/Fail:** ________

---

### Test 3.5: Stats Formatting on Mobile

**Objective:** Verify formatting looks good on Telegram mobile

**Steps:**
1. Open Telegram on mobile device
2. Send `/weekly`, `/monthly`, `/yearly`
3. Verify:
   - Text is readable (not too long lines)
   - Emojis display correctly
   - Sections are clearly separated
   - Numbers align nicely
   - Markdown formatting works

**Expected Result:** ✅ Clean, readable formatting on mobile

**Pass/Fail:** ________

---

## 🧪 Test Suite 4: Cron Job (Weekly Reset)

### Test 4.1: Manual Cron Trigger

**Objective:** Verify cron job resets counters

**Steps:**
1. Complete 2 quick check-ins (hit weekly limit)
2. Verify counter = 2 in Firestore
3. Trigger cron manually:
```bash
curl -X POST \
    -H "X-CloudScheduler-JobName: reset-quick-checkins" \
    http://localhost:8080/cron/reset_quick_checkins
```
4. Verify response:
```json
{
    "status": "reset_complete",
    "total_users": 1,
    "reset_count": 1,
    "errors": 0,
    "next_reset_date": "2026-02-17"
}
```
5. Check Firestore:
   - `quick_checkin_count` should be 0
   - `quick_checkin_used_dates` should be []
   - `quick_checkin_reset_date` should be next Monday

**Expected Result:** ✅ Counter reset to 0

**Pass/Fail:** ________

---

### Test 4.2: Reset Allows New Quick Check-Ins

**Objective:** Verify users can do quick check-ins after reset

**Steps:**
1. After manual reset (Test 4.1)
2. Send `/quickcheckin`
3. Verify intro shows "2/2 quick check-ins available"
4. Complete quick check-in
5. Verify counter increments to 1/2

**Expected Result:** ✅ Quick check-ins available after reset

**Pass/Fail:** ________

---

### Test 4.3: Next Monday Calculation

**Objective:** Verify reset date calculates correctly

**Steps:**
1. Check Firestore `quick_checkin_reset_date` field
2. Verify it's the next Monday from today
3. If today is Monday, verify it's NEXT Monday (not today)

**Expected Result:** ✅ Reset date is always future Monday

**Pass/Fail:** ________

---

## 🧪 Test Suite 5: Integration Tests

### Test 5.1: Full Check-In + Query + Stats

**Objective:** Verify all systems work together

**Steps:**
1. Complete full check-in: `/checkin`
2. Wait for completion (verify full feedback)
3. Query data: "What's my compliance?"
4. Verify query returns updated data (includes today's check-in)
5. Check stats: `/weekly`
6. Verify stats include today's check-in

**Expected Result:** ✅ All features reflect latest check-in

**Pass/Fail:** ________

---

### Test 5.2: Quick Check-In + Query + Stats

**Objective:** Verify quick check-ins integrate with queries/stats

**Steps:**
1. Complete quick check-in: `/quickcheckin`
2. Query: "Show my recent check-ins"
3. Verify quick check-in appears in results
4. Check stats: `/weekly`
5. Verify quick check-in counted in weekly stats

**Expected Result:** ✅ Quick check-ins appear in queries and stats

**Pass/Fail:** ________

---

### Test 5.3: Mixed Check-Ins (Full + Quick)

**Objective:** Verify mixing full and quick check-ins works

**Steps:**
1. Day 1: Complete full check-in
2. Day 2: Complete quick check-in
3. Day 3: Complete full check-in
4. Day 4: Complete quick check-in
5. Day 5: Try 3rd quick check-in → Should be blocked
6. Day 5: Complete full check-in → Should work
7. Check `/weekly`
8. Verify all 5 check-ins appear

**Expected Result:** ✅ Both types work together seamlessly

**Pass/Fail:** ________

---

### Test 5.4: Query Agent + Stats Commands (Same Data)

**Objective:** Verify consistency between query agent and stats commands

**Steps:**
1. Ask query: "What's my average compliance this week?"
2. Note the percentage from response
3. Send `/weekly`
4. Verify compliance average matches query response

**Expected Result:** ✅ Same data from both sources

**Pass/Fail:** ________

---

### Test 5.5: Error Handling Under Load

**Objective:** Verify graceful error handling

**Steps:**
1. Disconnect internet / stop Firestore
2. Send `/quickcheckin`
3. Verify error message is user-friendly
4. Reconnect
5. Try again
6. Verify recovery works

**Expected Result:** ✅ Graceful failures, clean recovery

**Pass/Fail:** ________

---

## 🧪 Test Suite 6: Edge Cases

### Test 6.1: Empty Query Response

**Objective:** Handle queries with no data

**Steps:**
1. New user (no check-ins)
2. Ask: "What's my average compliance?"
3. Verify response says "No data available" or similar

**Expected Result:** ✅ Helpful message for missing data

**Pass/Fail:** ________

---

### Test 6.2: Extreme Values

**Objective:** Handle edge case values

**Steps:**
1. Create check-in with:
   - 0% compliance
2. Query: "Show my compliance"
3. Verify response handles 0% gracefully
4. Check `/weekly`
5. Verify stats display 0% without crashing

**Expected Result:** ✅ Edge values handled gracefully

**Pass/Fail:** ________

---

### Test 6.3: Long Query Strings

**Objective:** Handle very long queries

**Steps:**
1. Send very long query (200+ words)
2. Verify response or timeout

**Expected Result:** ✅ Handles long input without crashing

**Pass/Fail:** ________

---

### Test 6.4: Concurrent Requests

**Objective:** Handle multiple users simultaneously

**Steps:**
1. Have 3+ test users
2. All send `/weekly` at same time
3. Verify all get responses
4. Check logs for race conditions

**Expected Result:** ✅ Handles concurrent requests

**Pass/Fail:** ________

---

## 📊 Test Results Summary

### Overall Results

**Quick Check-In Mode:**
- Tests Passed: ____/5
- Tests Failed: ____/5
- Critical Issues: ________

**Query Agent:**
- Tests Passed: ____/8
- Tests Failed: ____/8
- Critical Issues: ________

**Stats Commands:**
- Tests Passed: ____/5
- Tests Failed: ____/5
- Critical Issues: ________

**Cron Job:**
- Tests Passed: ____/3
- Tests Failed: ____/3
- Critical Issues: ________

**Integration:**
- Tests Passed: ____/5
- Tests Failed: ____/5
- Critical Issues: ________

**Edge Cases:**
- Tests Passed: ____/4
- Tests Failed: ____/4
- Critical Issues: ________

**Total: ____/30 Tests Passed**

---

## 🐛 Issues Found

### Critical (Blocks Deployment)
1. ___________________________________
2. ___________________________________

### High Priority
1. ___________________________________
2. ___________________________________

### Medium Priority
1. ___________________________________
2. ___________________________________

### Low Priority (Nice to Have)
1. ___________________________________
2. ___________________________________

---

## ✅ Pre-Deployment Checklist

Before deploying to production:

- [ ] All critical tests pass
- [ ] All high priority issues fixed
- [ ] Medium priority issues documented
- [ ] Low priority issues added to backlog
- [ ] Code reviewed
- [ ] Logs configured properly
- [ ] Error handling tested
- [ ] Cost monitoring set up
- [ ] Documentation updated
- [ ] Cloud Scheduler job created
- [ ] Webhook tested
- [ ] Rollback plan ready

---

## 📝 Notes & Observations

### Performance
- Query response time: _______ seconds
- Quick check-in completion time: _______ seconds
- Stats command response time: _______ seconds

### Cost Analysis
- Gemini API calls during testing: _______
- Estimated monthly cost: $_______

### User Experience
- Feedback clarity: _______
- Command discoverability: _______
- Error messages: _______
- Mobile formatting: _______

### Code Quality
- Logs useful for debugging: _______
- Error messages actionable: _______
- Type hints complete: _______
- Documentation sufficient: _______

---

## 🚀 Deployment Readiness

**Overall Status:** ⬜ Ready / ⬜ Not Ready

**Reason (if not ready):**
___________________________________
___________________________________

**Recommended Actions:**
1. ___________________________________
2. ___________________________________
3. ___________________________________

**Tester Signature:** ___________________
**Date:** ___________________

---

**End of Testing Guide**
