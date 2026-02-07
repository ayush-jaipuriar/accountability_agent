# Phase 3D Day 1 - Local Testing Guide

**Date:** February 7, 2026  
**Features to Test:** Career Mode System + Tier 1 Expansion (5→6 items)  
**Estimated Time:** 30-45 minutes

---

## 🎯 What We're Testing

### Day 1 Changes:
1. ✅ `/career` command with 3 modes (skill_building, job_searching, employed)
2. ✅ Adaptive skill building question based on career mode
3. ✅ Tier 1 expanded from 5 to 6 items (added skill_building)
4. ✅ Compliance calculation updated (16.67% per item instead of 20%)
5. ✅ Career mode toggle via inline buttons

---

## 🚀 Pre-Test Setup

### Step 1: Verify Environment

**Check Python version:**
```bash
python3 --version
# Should show: Python 3.11.x or higher
```

**Check virtual environment exists:**
```bash
ls venv/
# Should show: bin/ lib/ include/ etc.
```

**Activate virtual environment:**
```bash
source venv/bin/activate
```

**Install/update dependencies (if needed):**
```bash
pip install -r requirements.txt
```

---

### Step 2: Verify Environment Variables

**Check .env file exists:**
```bash
cat .env | grep -E "TELEGRAM_BOT_TOKEN|GCP_PROJECT_ID"
```

**Expected output:**
```
GCP_PROJECT_ID=accountability-agent
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
```

✅ **If you see these values, environment is configured correctly.**

---

### Step 3: Verify Firestore Credentials

**Check credentials file:**
```bash
ls -lh .credentials/accountability-agent-*.json
```

**Expected:** File exists and is ~2-3 KB

✅ **If file exists, Firestore authentication is ready.**

---

## 🧪 Testing Phase 3D Day 1 Features

### Test 1: Run Bot Locally

**Command:**
```bash
python src/main.py
```

**Expected Output:**
```
INFO:     Started server process [12345]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
✅ Telegram bot initialized
✅ Firestore service initialized
```

**Troubleshooting:**
- **Error: "No module named 'X'"** → Run `pip install -r requirements.txt`
- **Error: "Could not authenticate"** → Check `.credentials/` file exists
- **Error: "Bot token invalid"** → Check `TELEGRAM_BOT_TOKEN` in `.env`

**✅ Test passes if:** Bot starts without errors

---

### Test 2: Test /career Command (Career Mode Toggle)

**In Telegram:**

**2.1: Open Career Menu**
```
/career
```

**Expected Response:**
```
🎯 Career Phase Tracking

Current Mode:
📚 Skill Building
Learning phase: LeetCode, system design, AI/ML upskilling, courses, projects

✅ Skill building question: Did you do 2+ hours skill building?

━━━━━━━━━━━━━━━━━━━━
Why Career Mode Matters:
• Your Tier 1 skill building question adapts to your career phase
• Tracks progress toward ₹28-42 LPA June 2026 goal
• Aligns check-ins with constitution career protocols

Change mode using buttons below:
```

**With 3 inline buttons:**
- [📚 Skill Building]
- [💼 Job Searching]
- [🎯 Employed]

**✅ Test passes if:** Message displays with 3 buttons

---

**2.2: Switch to Job Searching Mode**

**Action:** Click **[💼 Job Searching]** button

**Expected Response:**
```
✅ Career mode updated!

New Mode: 💼 Job Searching

Your Tier 1 skill building question will now be:
"Did you make job search progress?"

This change takes effect starting your next check-in.

🎯 Keep tracking progress toward your June 2026 goal! (₹28-42 LPA)
```

**✅ Test passes if:** Confirmation message shows, mode changes to "Job Searching"

---

**2.3: Switch to Employed Mode**

**Action:** Run `/career` again, click **[🎯 Employed]** button

**Expected Response:**
```
✅ Career mode updated!

New Mode: 🎯 Employed

Your Tier 1 skill building question will now be:
"Did you work toward promotion/raise?"

This change takes effect starting your next check-in.

🎯 Keep tracking progress toward your June 2026 goal! (₹28-42 LPA)
```

**✅ Test passes if:** Confirmation message shows, mode changes to "Employed"

---

**2.4: Switch Back to Skill Building**

**Action:** Run `/career` again, click **[📚 Skill Building]** button

**Expected Response:**
```
✅ Career mode updated!

New Mode: 📚 Skill Building

Your Tier 1 skill building question will now be:
"Did you do 2+ hours skill building?"

This change takes effect starting your next check-in.

🎯 Keep tracking progress toward your June 2026 goal! (₹28-42 LPA)
```

**✅ Test passes if:** All 3 mode switches work correctly

---

### Test 3: Test Tier 1 with 6 Items (skill_building mode)

**Prerequisite:** Ensure career mode is **skill_building** (run `/career` and verify)

**In Telegram:**

**3.1: Start Check-In**
```
/checkin
```

**Expected Response:**
```
📋 Daily Check-In - Question 1/4

Constitution Compliance (Tier 1 Non-Negotiables):

Did you complete the following today?

• 💤 Sleep: 7+ hours last night?
• 💪 Training: Workout OR rest day? (4x/week)
• 🧠 Deep Work: 2+ hours focused work/study?
• 📚 Skill Building: 2+ hours today? (LeetCode, system design, AI/ML upskilling, courses, projects)
• 🚫 Zero Porn: No consumption today?
• 🛡️ Boundaries: No toxic interactions?

Click the buttons below to answer:
```

**With 12 inline buttons (6 items × 2 buttons each):**

**Row 1:** [💤 Sleep: YES] [💤 Sleep: NO]  
**Row 2:** [💪 Training: YES] [💪 Training: NO]  
**Row 3:** [🧠 Deep Work: YES] [🧠 Deep Work: NO]  
**Row 4:** [📚 Skill Building: YES] [📚 Skill Building: NO]  ← **NEW!**  
**Row 5:** [🚫 Zero Porn: YES] [🚫 Zero Porn: NO]  
**Row 6:** [🛡️ Boundaries: YES] [🛡️ Boundaries: NO]

**✅ Test passes if:** 
- 6 rows of buttons show (not 5!)
- 4th row says "📚 Skill Building"
- Question text includes "📚 Skill Building: 2+ hours today?"

---

**3.2: Answer All 6 Items**

**Action:** Click buttons to answer all 6 items (any combination)

**Example sequence:**
1. Click [💤 Sleep: YES]
2. Click [💪 Training: YES]
3. Click [🧠 Deep Work: YES]
4. Click [📚 Skill Building: YES]
5. Click [🚫 Zero Porn: YES]
6. Click [🛡️ Boundaries: YES]

**Expected:** After each click, see confirmation like:
```
💤 Sleep: ✅ YES
```

**After clicking all 6:**
```
📋 Question 2/4

Challenges & Handling:
What challenges did you face today? How did you handle them?

📝 Type your response (10-500 characters).

Example: 'Urge to watch porn around 10 PM. Went for a walk and texted friend instead.'
```

**✅ Test passes if:** Conversation moves to Q2 after answering all 6 items (not 5!)

---

**3.3: Complete Full Check-In**

**Action:** Answer remaining questions:

**Q2 (Challenges):**
```
Testing Phase 3D Day 1 - career mode and tier 1 expansion working great!
```

**Q3 (Rating):**
```
8 - Good progress on skill building today, LeetCode medium problem solved
```

**Q4 (Tomorrow Priority):**
```
Priority: Complete system design practice (2 hours)
```

**Q4 (Tomorrow Obstacle):**
```
Obstacle: Meetings in morning might interrupt deep work flow
```

**Expected Final Response:**
```
✅ Perfect day! Compliance: 100.0%
Streak: X days - You're unstoppable!

[AI-generated personalized feedback here]

📊 Summary:
• Compliance: 100.0% (6/6 completed)
• Streak: X days
• Mode: Maintenance

Keep it up! 💪
```

**✅ Test passes if:** 
- Compliance shows 100.0% (all 6 items)
- Check-in completes successfully
- No errors in console

---

### Test 4: Test Adaptive Questions (job_searching mode)

**4.1: Switch to Job Searching Mode**
```
/career
```
Click **[💼 Job Searching]**

**4.2: Start New Check-In**

**Important:** You can only do one check-in per day. To test again:

**Option A (Quick Test):** Check Firestore directly
- Go to Firebase Console → Firestore
- Check `users/{your_user_id}/career_mode` = "job_searching"
- Confirms mode saved

**Option B (Full Test):** Delete today's check-in and retry

**Delete check-in command:**
```bash
# In Python console (or create temp script)
python3 << EOF
from src.services.firestore_service import firestore_service
from src.models.schemas import get_current_date_ist

user_id = "YOUR_TELEGRAM_USER_ID"
date = get_current_date_ist()
firestore_service.delete_checkin(user_id, date)
print(f"✅ Deleted check-in for {date}")
EOF
```

**Then run:**
```
/checkin
```

**Expected:** Question 4 now says:
```
• 💼 Job Search Progress: Made progress today? (Applications, interviews, LeetCode, networking)
```

**Button label:**
```
[💼 Job Search: YES] [💼 Job Search: NO]
```

**✅ Test passes if:** Question text and button label adapted to job_searching mode

---

### Test 5: Test Compliance Calculation (6 items)

**Goal:** Verify compliance scores calculated correctly with 6 items

**Test Cases:**

| Items Completed | Expected Score | Formula |
|----------------|----------------|---------|
| 6/6 (all) | 100.0% | 6/6 × 100 |
| 5/6 | 83.33% | 5/6 × 100 |
| 4/6 | 66.67% | 4/6 × 100 |
| 3/6 | 50.0% | 3/6 × 100 |

**How to Test:**

**5.1: Complete check-in with 5/6 items** (e.g., answer NO to one item)

**Example:**
- Sleep: YES
- Training: YES
- Deep Work: NO ← (miss this one)
- Skill Building: YES
- Zero Porn: YES
- Boundaries: YES

**Expected compliance:** 83.33% (or 83.3%)

**✅ Test passes if:** Score shows ~83% (not 80% which was old calculation!)

---

### Test 6: Verify Firestore Storage

**6.1: Check Career Mode Stored**

**Firebase Console:**
1. Go to https://console.firebase.google.com/
2. Select project: `accountability-agent`
3. Navigate to Firestore Database
4. Open `users/{your_user_id}` document
5. Find field: `career_mode`

**Expected value:** "skill_building" | "job_searching" | "employed"

**✅ Test passes if:** Field exists and matches your last selection

---

**6.2: Check Tier 1 skill_building Field Stored**

**Firebase Console:**
1. Navigate to `daily_checkins/{your_user_id}/checkins/{today_date}`
2. Open document
3. Check `tier1_non_negotiables` object
4. Verify field `skill_building` exists

**Expected structure:**
```json
{
  "tier1_non_negotiables": {
    "sleep": true,
    "training": true,
    "deep_work": true,
    "skill_building": true,  // ← NEW FIELD!
    "zero_porn": true,
    "boundaries": true
  }
}
```

**✅ Test passes if:** `skill_building` field exists in check-in data

---

## 📊 Testing Checklist

### Core Functionality

- [ ] **Test 1:** Bot starts without errors
- [ ] **Test 2.1:** /career command shows 3 mode buttons
- [ ] **Test 2.2:** Can switch to job_searching mode
- [ ] **Test 2.3:** Can switch to employed mode
- [ ] **Test 2.4:** Can switch back to skill_building mode
- [ ] **Test 3.1:** Tier 1 shows 6 items (not 5)
- [ ] **Test 3.2:** All 6 items answerable
- [ ] **Test 3.3:** Check-in completes successfully with 6 items
- [ ] **Test 4:** Skill building question adapts to career mode
- [ ] **Test 5:** Compliance calculated correctly (83.33% for 5/6)
- [ ] **Test 6.1:** Career mode saved to Firestore
- [ ] **Test 6.2:** skill_building field saved in check-ins

### Edge Cases

- [ ] **EC1:** /career command works for new user (default: skill_building)
- [ ] **EC2:** Switching modes mid-check-in doesn't break flow
- [ ] **EC3:** Help command includes /career command

---

## 🐛 Common Issues & Fixes

### Issue 1: Bot won't start - "ModuleNotFoundError"

**Error:**
```
ModuleNotFoundError: No module named 'telegram'
```

**Fix:**
```bash
source venv/bin/activate
pip install -r requirements.txt
```

---

### Issue 2: "Could not authenticate with Firestore"

**Error:**
```
google.auth.exceptions.DefaultCredentialsError
```

**Fix:**
```bash
# Check credentials file exists
ls .credentials/

# Verify GOOGLE_APPLICATION_CREDENTIALS in .env
cat .env | grep GOOGLE_APPLICATION_CREDENTIALS
```

---

### Issue 3: /career command not recognized

**Error:**
```
Sorry, I didn't understand that command.
```

**Fix:**
1. Stop bot (Ctrl+C)
2. Restart bot: `python src/main.py`
3. Wait for "✅ Telegram bot initialized"
4. Try /career again

**Why:** Handler registration happens at startup

---

### Issue 4: Tier 1 still shows 5 items

**Symptom:** No skill building button appears

**Fix:**
1. Check `src/bot/conversation.py` line 125-165 (ask_tier1_question)
2. Verify skill_building button exists in keyboard array
3. Restart bot
4. Clear Telegram cache (Settings → Data and Storage → Clear Cache)

---

### Issue 5: Compliance calculation wrong

**Symptom:** 5/6 items = 80% (should be 83.33%)

**Fix:**
1. Check `src/utils/compliance.py` line 54-68
2. Verify `tier1.skill_building` in items list
3. Restart bot
4. Complete new check-in

---

## ✅ Success Criteria

**Phase 3D Day 1 testing is SUCCESSFUL if:**

1. ✅ All 12 checklist items pass
2. ✅ No errors in console during testing
3. ✅ Career mode persists across bot restarts
4. ✅ Tier 1 consistently shows 6 items
5. ✅ Compliance calculation correct for 6 items
6. ✅ Adaptive questions work for all 3 modes

**If any test fails:**
1. Note which test failed
2. Check error logs in console
3. Review relevant code file
4. Fix issue
5. Restart bot and retest

---

## 📝 Test Results Template

**Copy and fill this out during testing:**

```markdown
## Phase 3D Day 1 Testing Results

**Date:** February 7, 2026  
**Tester:** Ayush Jaipuriar  
**Environment:** Local (macOS)

### Core Functionality
- [ ] Test 1: Bot startup - PASS / FAIL
- [ ] Test 2: Career mode toggle - PASS / FAIL
- [ ] Test 3: Tier 1 with 6 items - PASS / FAIL
- [ ] Test 4: Adaptive questions - PASS / FAIL
- [ ] Test 5: Compliance calculation - PASS / FAIL
- [ ] Test 6: Firestore storage - PASS / FAIL

### Issues Found
1. [Issue description if any]
2. [Issue description if any]

### Summary
- ✅ READY FOR PRODUCTION / ⚠️ FIXES NEEDED
- Next Steps: [Deploy to Cloud Run / Fix issues first]
```

---

## 🚀 Next Steps After Testing

**If all tests pass:**
1. ✅ Update PHASE3D_IMPLEMENTATION.md with test results
2. ✅ Commit changes to Git
3. ✅ Proceed to Day 3 implementation (Advanced Pattern Detection)
4. OR Deploy Day 1 changes to production immediately

**If tests fail:**
1. Document failing test
2. Fix issue
3. Retest
4. Repeat until all pass

---

**Happy Testing! 🧪**

If you encounter any issues, check the error logs in the console and refer to the troubleshooting section above.
