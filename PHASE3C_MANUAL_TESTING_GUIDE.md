# Phase 3C Manual Testing Guide

**Purpose:** Manual test scenarios for Phase 3C gamification features before deployment

**Date:** February 6, 2026

---

## 🧪 Pre-Testing Setup

### Local Environment

```bash
# 1. Ensure Docker is running
docker --version

# 2. Build latest image
docker build -t constitution-agent .

# 3. Run locally with prod-like config
docker run -p 8080:8080 \
  -e GCP_PROJECT_ID="your-project" \
  -e TELEGRAM_BOT_TOKEN="your-token" \
  -e FIRESTORE_COLLECTION="users-test" \
  constitution-agent

# 4. Keep logs visible
docker logs -f <container-id>
```

### Test User Setup

Create test users with different streak levels:

| User | Telegram ID | Current Streak | Purpose |
|------|-------------|----------------|---------|
| test_new | 111111111 | 0 days | First check-in, basic achievements |
| test_week | 222222222 | 6 days | Week warrior achievement |
| test_milestone | 333333333 | 29 days | 30-day milestone + month master |
| test_comeback | 444444444 | 49 days (longest: 50) | Comeback king |
| test_perfect | 555555555 | 6 days (all 100%) | Perfect week achievement |

---

## Test Suite 1: Basic Achievement System

### Test 1.1: First Check-In Achievement

**Objective:** Verify "First Step" achievement unlocks on first check-in

**Steps:**
1. Start check-in with `test_new` user: `/checkin`
2. Complete check-in flow (any responses)
3. Observe messages after check-in completion

**Expected Result:**
```
✅ Check-In Complete!
[... feedback message ...]

🎉 Achievement Unlocked!

🎯 First Step

You took the first step! Every journey begins with a single check-in.

Rarity: Common 🥉
```

**Validation:**
- ✅ Achievement message appears as separate message
- ✅ Contains achievement name, description, rarity
- ✅ Personalized with user's name
- ✅ Check-in completes successfully even if achievement fails

---

### Test 1.2: Week Warrior Achievement

**Objective:** Verify 7-day streak achievement

**Setup:**
- Use `test_week` user (6-day streak)

**Steps:**
1. Complete check-in for day 7
2. Verify streak updates to 7 days
3. Check for achievement unlock

**Expected Result:**
```
[Check-in feedback with "Streak: 7 days"]

🎉 Achievement Unlocked!

🏅 Week Warrior

7-day streak achieved! You're building momentum.

Rarity: Common 🥉
```

**Validation:**
- ✅ Achievement triggers on exactly 7-day streak
- ✅ Does not trigger on day 6 or day 8

---

### Test 1.3: No Duplicate Achievements

**Objective:** Verify achievements don't unlock twice

**Setup:**
- Use `test_week` user who already has "week_warrior"

**Steps:**
1. Complete another check-in (day 8)
2. Observe messages

**Expected Result:**
- ✅ No achievement message (already unlocked)
- ✅ Check-in feedback normal
- ✅ No errors in logs

---

## Test Suite 2: Milestone Celebrations

### Test 2.1: 30-Day Milestone

**Objective:** Verify milestone celebration at 30 days

**Setup:**
- Use `test_milestone` user (29-day streak)

**Steps:**
1. Complete check-in for day 30
2. Observe messages (should be 2-3 separate messages)

**Expected Result:**
```
[Message 1: Check-in feedback]
✅ Solid day! ...
🔥 Streak: 30 days
...

[Message 2: Achievement - Month Master]
🎉 Achievement Unlocked!
🏆 Month Master
...

[Message 3: Milestone Celebration]
**🎉 30 DAYS!**

🎉 **30 DAYS!** You're in the top 10% of accountability seekers.

You've proven you can commit. This is where most people quit, 
but you pushed through. Your constitution is becoming automatic. 
**Habit formation threshold reached.**

Keep going! 💪
```

**Validation:**
- ✅ Milestone message appears as separate message
- ✅ Contains "TOP 10%" reference
- ✅ Includes research-backed messaging
- ✅ Order: Feedback → Achievement → Milestone
- ✅ Bold formatting renders correctly in Telegram

---

### Test 2.2: Non-Milestone Days

**Objective:** Verify no milestone on day 29, 31, etc.

**Setup:**
- Use user with 28-day streak

**Steps:**
1. Complete check-in (day 29)
2. Observe messages

**Expected Result:**
- ✅ Check-in feedback normal
- ✅ No milestone celebration
- ✅ Only regular achievement messages (if any)

---

### Test 2.3: Milestone Sequence

**Objective:** Verify all 5 milestones trigger correctly

**Test Days:** 30, 60, 90, 180, 365

**For each milestone:**

| Day | Expected Title | Expected Percentile |
|-----|---------------|---------------------|
| 30 | 🎉 30 DAYS! | Top 10% |
| 60 | 🔥 60 DAYS! | Top 5% |
| 90 | 💎 90 DAYS! | Top 2% |
| 180 | 🏆 HALF YEAR! | Top 1% |
| 365 | 👑 ONE YEAR! | Top 0.1% |

**Validation:**
- ✅ Each milestone has unique title and message
- ✅ Percentiles decrease with higher streaks
- ✅ Messages reference identity shift appropriately

---

## Test Suite 3: Social Proof

### Test 3.1: Social Proof Display (30+ Day Streak)

**Objective:** Verify social proof shows for users with 30+ day streaks

**Setup:**
- Ensure 10+ users exist in test Firestore
- Use `test_milestone` user (30+ days)

**Steps:**
1. Complete check-in
2. Look for social proof in feedback message

**Expected Result:**
```
[Within check-in feedback message]
...
🎯 See you tomorrow at 9 PM!

---

You're in the **TOP 10%** of users with a 30-day streak! 🌟
```

**Validation:**
- ✅ Social proof appears at end of feedback
- ✅ Shows percentile tier (TOP X%)
- ✅ Includes appropriate emoji
- ✅ No specific ranking or user names revealed

---

### Test 3.2: Social Proof Not Shown (< 30 Days)

**Objective:** Verify social proof hidden for streaks < 30 days

**Setup:**
- Use `test_week` user (7 days)

**Steps:**
1. Complete check-in
2. Check feedback message

**Expected Result:**
- ✅ No social proof line in feedback
- ✅ Feedback ends normally with "See you tomorrow"

---

### Test 3.3: Social Proof Privacy (< 10 Users)

**Objective:** Verify social proof hidden when too few users

**Setup:**
- Use test database with < 10 users

**Steps:**
1. Complete check-in with 30+ day user
2. Check feedback

**Expected Result:**
- ✅ No social proof shown (privacy protection)
- ✅ Check-in completes normally

---

## Test Suite 4: `/achievements` Command

### Test 4.1: View Achievements Command

**Objective:** Verify `/achievements` command displays user's unlocked achievements

**Setup:**
- Use `test_milestone` user (has multiple achievements)

**Steps:**
1. Send `/achievements` command
2. Observe response

**Expected Result:**
```
🏆 **Your Achievements**

You've unlocked **4 out of 13** achievements! (30.8%)

**Common (🥉):**
🎯 First Step
🏅 Week Warrior
🥈 Fortnight Fighter

**Rare (🥈):**
🏆 Month Master

**Epic (🥇):** _None yet_
**Legendary (👑):** _None yet_

---

**Next Milestone:**
🚀 Keep going! 60 more days to unlock Quarter Conqueror (90-day streak)

---
Use /checkin at 9 PM IST to continue your streak!
```

**Validation:**
- ✅ Shows correct count of unlocked achievements
- ✅ Grouped by rarity tier
- ✅ Includes achievement icons and names
- ✅ Shows next streak achievement
- ✅ Markdown formatting renders correctly

---

### Test 4.2: Achievements for New User

**Objective:** Verify command works for users with no achievements

**Setup:**
- Use brand new user (no check-ins)

**Steps:**
1. Send `/achievements`
2. Observe response

**Expected Result:**
```
🏆 **Your Achievements**

You haven't unlocked any achievements yet.

Start your journey with /checkin at 9 PM IST!
```

**Validation:**
- ✅ Shows helpful message for new users
- ✅ No errors
- ✅ Encourages first check-in

---

## Test Suite 5: Performance-Based Achievements

### Test 5.1: Perfect Week Achievement

**Objective:** Verify "Perfect Week" unlocks after 7 days at 100% compliance

**Setup:**
- Use `test_perfect` user (6 perfect days)

**Steps:**
1. Complete day 7 with 100% compliance:
   - All Tier 1 items: ✅
   - Sleep: 7+ hours
   - Training: Complete
   - Deep work: 2+ hours
   - Zero porn: Yes
   - Boundaries: Yes
2. Check for achievement

**Expected Result:**
```
🎉 Achievement Unlocked!

⭐ Perfect Week

7 consecutive days at 100% compliance! You're mastering your constitution.

Rarity: Rare 🥈
```

**Validation:**
- ✅ Only triggers with 7 consecutive 100% days
- ✅ Rarity is "Rare"
- ✅ Does not trigger if any day has < 100%

---

### Test 5.2: Tier 1 Master Achievement

**Objective:** Verify "Tier 1 Master" for 30 days with all Tier 1 complete

**Setup:**
- User with 30 days of all Tier 1 items complete

**Steps:**
1. Review recent 30 check-ins (all have complete Tier 1)
2. Complete day 30 check-in
3. Check for achievement

**Expected Result:**
```
🎉 Achievement Unlocked!

💯 Tier 1 Master

30 days with all Tier 1 non-negotiables complete! Foundation solidified.

Rarity: Epic 🥇
```

**Validation:**
- ✅ Checks all Tier 1 items (sleep, training, deep work, zero porn, boundaries)
- ✅ Only triggers after 30 days
- ✅ Rarity is "Epic"

---

## Test Suite 6: Special Achievements

### Test 6.1: Comeback King Achievement

**Objective:** Verify comeback achievement when rebuilding to longest streak

**Setup:**
- Use `test_comeback` user:
  - Current: 49 days
  - Longest: 50 days (previously achieved)

**Steps:**
1. Complete check-in for day 50 (matching longest)
2. Check for achievement

**Expected Result:**
```
🎉 Achievement Unlocked!

🔄 Comeback King

You rebuilt your streak to match your record! Resilience in action.

Rarity: Rare 🥈
```

**Validation:**
- ✅ Only triggers when current_streak == longest_streak (and longest > 7)
- ✅ Does not trigger if it's the first time reaching that streak
- ✅ Represents a "comeback" after breaking a streak

---

## Test Suite 7: Error Handling & Graceful Degradation

### Test 7.1: Achievement System Failure

**Objective:** Verify check-in succeeds even if achievement system fails

**Setup:**
- Temporarily cause Firestore error (e.g., wrong collection name)

**Steps:**
1. Complete check-in
2. Check logs for errors
3. Verify check-in saved

**Expected Result:**
- ✅ Check-in completes successfully
- ✅ Streak updates correctly
- ✅ User gets feedback message
- ✅ Achievement error logged as "non-critical"
- ✅ No achievement messages sent (failed gracefully)

**Log Example:**
```
⚠️ Achievement checking failed (non-critical): [Firestore error]
✅ Check-in completed for user_id: ...
```

---

### Test 7.2: Milestone System Failure

**Objective:** Verify milestone failure doesn't break check-in

**Setup:**
- User on day 29 (about to hit milestone)

**Steps:**
1. Complete check-in for day 30
2. Simulate milestone message send failure

**Expected Result:**
- ✅ Check-in completes
- ✅ Streak updates to 30 days
- ✅ Achievement messages sent (if any)
- ✅ Milestone error logged
- ✅ User experience minimally impacted

---

### Test 7.3: Social Proof Database Error

**Objective:** Verify social proof failure doesn't break feedback

**Setup:**
- Cause Firestore `get_all_users()` to fail

**Steps:**
1. Complete check-in with 30+ day user
2. Check feedback message

**Expected Result:**
- ✅ Check-in feedback sent normally
- ✅ Social proof line missing (graceful degradation)
- ✅ Error logged as "non-critical"
- ✅ Feedback message still includes closing line

---

## Test Suite 8: Message Ordering & Flow

### Test 8.1: Complete Message Flow (All Features)

**Objective:** Verify correct message order when all features trigger

**Setup:**
- User on day 29 with 7 perfect days

**Steps:**
1. Complete check-in for day 30 with 100% compliance
2. Observe all messages in order

**Expected Result:**

**Message 1 (Primary Feedback):**
```
✅ Solid day! You completed all Tier 1 priorities.

📊 Compliance: 100%
🔥 Streak: 30 days
🏆 Personal best: 30 days

[... AI-generated personalized feedback ...]

You're in the **TOP 10%** of users with a 30-day streak! 🌟

---

🎯 See you tomorrow at 9 PM!
```

**Message 2 (Achievement - Month Master):**
```
🎉 Achievement Unlocked!

🏆 Month Master

30-day streak achieved! ...
```

**Message 3 (Achievement - Perfect Week):**
```
🎉 Achievement Unlocked!

⭐ Perfect Week

7 consecutive days at 100% compliance! ...
```

**Message 4 (Milestone Celebration):**
```
**🎉 30 DAYS!**

🎉 **30 DAYS!** You're in the top 10% of accountability seekers.
...
```

**Validation:**
- ✅ Order: Feedback → Achievements → Milestone
- ✅ Each message is separate
- ✅ All messages appear within 1-2 seconds
- ✅ No duplicate messages

---

## Test Suite 9: Edge Cases

### Test 9.1: Streak Reset Behavior

**Objective:** Verify no achievements/milestones when streak resets

**Setup:**
- User with 50-day streak

**Steps:**
1. Skip 3 days (break streak)
2. Complete check-in (streak resets to 1)
3. Check for messages

**Expected Result:**
- ✅ Streak resets to 1 day
- ✅ No milestone message
- ✅ "First Step" achievement not unlocked again (already has it)
- ✅ Check-in feedback shows "Streak: 1 day"

---

### Test 9.2: Same-Day Check-In Attempt

**Objective:** Verify gamification doesn't trigger on duplicate check-in

**Setup:**
- User who already checked in today

**Steps:**
1. Attempt `/checkin` again same day
2. Observe response

**Expected Result:**
```
✅ You've already completed your check-in for 2026-02-06!

🔥 Current streak: 30 days
🏆 Personal best: 30 days

See you tomorrow at 9 PM for your next check-in! 💪
```

**Validation:**
- ✅ No new achievements
- ✅ No milestone celebration
- ✅ Streak unchanged
- ✅ Helpful message displayed

---

### Test 9.3: Multiple Users Simultaneously

**Objective:** Verify system handles concurrent check-ins correctly

**Setup:**
- 5 test users

**Steps:**
1. Have all 5 users complete check-ins within 1 minute
2. Verify each gets correct achievements/milestones
3. Check Firestore for data consistency

**Expected Result:**
- ✅ Each user gets their own achievements
- ✅ No cross-user contamination
- ✅ Percentile calculations work correctly
- ✅ All data saved properly

---

## Test Suite 10: Command Integration

### Test 10.1: Help Command Includes Achievements

**Objective:** Verify `/help` mentions `/achievements` command

**Steps:**
1. Send `/help`
2. Check response

**Expected Result:**
```
Available commands:
...
/achievements - View your unlocked achievements 🏆
...
```

**Validation:**
- ✅ `/achievements` listed in help
- ✅ Includes brief description

---

## 📋 Test Execution Checklist

Before deploying Phase 3C, verify:

### Critical Tests (Must Pass)
- [ ] Test 1.1: First check-in achievement
- [ ] Test 2.1: 30-day milestone celebration
- [ ] Test 3.1: Social proof display
- [ ] Test 4.1: `/achievements` command
- [ ] Test 7.1: Achievement system failure (graceful degradation)

### Important Tests (Should Pass)
- [ ] Test 1.2: Week warrior achievement
- [ ] Test 1.3: No duplicate achievements
- [ ] Test 2.2: Non-milestone days
- [ ] Test 3.2: Social proof privacy (< 30 days)
- [ ] Test 5.1: Perfect week achievement
- [ ] Test 6.1: Comeback king achievement
- [ ] Test 8.1: Complete message flow

### Edge Cases (Nice to Have)
- [ ] Test 9.1: Streak reset behavior
- [ ] Test 9.2: Same-day check-in
- [ ] Test 9.3: Multiple users simultaneously

---

## 🐛 Bug Tracking

| Test | Issue | Severity | Status | Notes |
|------|-------|----------|--------|-------|
| | | | | |

---

## ✅ Sign-Off

**Tester:** ___________________  
**Date:** ___________________  
**All Critical Tests Passed:** [ ] Yes [ ] No  
**Ready for Deployment:** [ ] Yes [ ] No  

**Notes:**
_________________________________________________________________
_________________________________________________________________
_________________________________________________________________

---

**Next Step After Testing:** Deploy to Cloud Run and monitor production for 24 hours
