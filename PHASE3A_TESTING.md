# Phase 3A Testing Guide

**Date:** February 4, 2026  
**Phase:** 3A - Critical Foundation (Multi-User + Triple Reminder System)  
**Status:** Ready for Testing

---

## 📋 Testing Overview

### What We're Testing

Phase 3A introduces 5 major features:

1. ✅ **Enhanced Onboarding Flow** - Interactive mode selection, timezone confirmation
2. ✅ **Triple Reminder System** - 9 PM, 9:30 PM, 10 PM reminders
3. ✅ **Late Check-In Support** - 3 AM cutoff (before 3 AM = previous day)
4. ✅ **Streak Protection System** - 3 shields per month
5. ✅ **Multi-User Support** - User isolation, per-user reminders

### Testing Strategy

- **Unit Tests:** Individual functions (streak logic, timezone calculations)
- **Integration Tests:** End-to-end flows (onboarding, check-in, reminders)
- **Manual Tests:** Real Telegram bot testing with 3 test users
- **Load Tests:** Simulate 10+ users for reminder system

---

## 1. Unit Tests

### Test Streak Shield Logic

```bash
# Create test file: tests/test_streak_shields.py
```

```python
"""
Unit tests for streak shield functionality (Phase 3A).
"""

import pytest
from datetime import datetime, timedelta
from src.models.schemas import User, StreakShields
from src.utils.streak import should_reset_streak_shields, calculate_days_without_checkin


def test_streak_shields_initialization():
    """Test that new users get 3 shields by default."""
    shields = StreakShields()
    
    assert shields.total == 3
    assert shields.used == 0
    assert shields.available == 3
    assert shields.earned_at == []
    assert shields.last_reset is None


def test_should_reset_streak_shields_never_reset():
    """Test shield reset when never reset before."""
    result = should_reset_streak_shields(None)
    assert result is True


def test_should_reset_streak_shields_29_days_ago():
    """Test shield reset when 29 days since last reset (should not reset)."""
    last_reset = (datetime.now() - timedelta(days=29)).strftime("%Y-%m-%d")
    result = should_reset_streak_shields(last_reset)
    assert result is False


def test_should_reset_streak_shields_30_days_ago():
    """Test shield reset when 30 days since last reset (should reset)."""
    last_reset = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    result = should_reset_streak_shields(last_reset)
    assert result is True


def test_calculate_days_without_checkin_never():
    """Test days without check-in when never checked in."""
    result = calculate_days_without_checkin(None)
    assert result == -1


def test_calculate_days_without_checkin_today():
    """Test days without check-in when checked in today."""
    today = datetime.now().strftime("%Y-%m-%d")
    result = calculate_days_without_checkin(today)
    assert result == 0


def test_calculate_days_without_checkin_3_days_ago():
    """Test days without check-in when last checked in 3 days ago."""
    three_days_ago = (datetime.now() - timedelta(days=3)).strftime("%Y-%m-%d")
    result = calculate_days_without_checkin(three_days_ago)
    assert result == 3


# Run tests
# pytest tests/test_streak_shields.py -v
```

### Test Late Check-In Logic (3 AM Cutoff)

```bash
# Create test file: tests/test_late_checkin.py
```

```python
"""
Unit tests for late check-in 3 AM cutoff logic (Phase 3A).
"""

import pytest
from datetime import datetime, timedelta
import pytz
from src.utils.timezone_utils import get_checkin_date

IST = pytz.timezone("Asia/Kolkata")


def test_get_checkin_date_before_3am():
    """Test check-in before 3 AM counts for previous day."""
    # February 5, 2:30 AM IST
    test_time = IST.localize(datetime(2026, 2, 5, 2, 30, 0))
    result = get_checkin_date(test_time)
    
    # Should count for Feb 4 (previous day)
    assert result == "2026-02-04"


def test_get_checkin_date_at_3am():
    """Test check-in at exactly 3 AM counts for current day."""
    # February 5, 3:00 AM IST
    test_time = IST.localize(datetime(2026, 2, 5, 3, 0, 0))
    result = get_checkin_date(test_time)
    
    # Should count for Feb 5 (current day)
    assert result == "2026-02-05"


def test_get_checkin_date_after_3am():
    """Test check-in after 3 AM counts for current day."""
    # February 5, 9:00 PM IST
    test_time = IST.localize(datetime(2026, 2, 5, 21, 0, 0))
    result = get_checkin_date(test_time)
    
    # Should count for Feb 5 (current day)
    assert result == "2026-02-05"


def test_get_checkin_date_edge_case_259am():
    """Test check-in at 2:59 AM (1 minute before cutoff)."""
    # February 5, 2:59 AM IST
    test_time = IST.localize(datetime(2026, 2, 5, 2, 59, 0))
    result = get_checkin_date(test_time)
    
    # Should count for Feb 4 (previous day)
    assert result == "2026-02-04"


def test_get_checkin_date_edge_case_301am():
    """Test check-in at 3:01 AM (1 minute after cutoff)."""
    # February 5, 3:01 AM IST
    test_time = IST.localize(datetime(2026, 2, 5, 3, 1, 0))
    result = get_checkin_date(test_time)
    
    # Should count for Feb 5 (current day)
    assert result == "2026-02-05"


# Run tests
# pytest tests/test_late_checkin.py -v
```

### Run All Unit Tests

```bash
# Install pytest if not already installed
pip install pytest pytest-asyncio

# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_streak_shields.py -v
pytest tests/test_late_checkin.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

---

## 2. Integration Tests

### Test Reminder System End-to-End

```bash
# Create test file: tests/integration/test_reminder_flow.py
```

```python
"""
Integration tests for triple reminder system (Phase 3A).
"""

import pytest
from datetime import datetime
from src.services.firestore_service import firestore_service
from src.models.schemas import User


@pytest.mark.asyncio
async def test_reminder_flow_complete():
    """Test complete reminder flow: 1st, 2nd, 3rd reminders."""
    
    # Create test user
    test_user = User(
        user_id="test_user_reminder",
        telegram_id=123456789,
        name="Test Reminder User",
        timezone="Asia/Kolkata",
        constitution_mode="maintenance"
    )
    firestore_service.create_user(test_user)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Test 1: User without check-in should be in reminder list
    users_without_checkin = firestore_service.get_users_without_checkin_today(today)
    assert any(u.user_id == "test_user_reminder" for u in users_without_checkin)
    
    # Test 2: First reminder status
    firestore_service.set_reminder_sent("test_user_reminder", today, "first")
    reminder_status = firestore_service.get_reminder_status("test_user_reminder", today)
    assert reminder_status is not None
    assert reminder_status["first_sent"] is True
    assert reminder_status["second_sent"] is False
    
    # Test 3: Second reminder status
    firestore_service.set_reminder_sent("test_user_reminder", today, "second")
    reminder_status = firestore_service.get_reminder_status("test_user_reminder", today)
    assert reminder_status["second_sent"] is True
    
    # Test 4: Third reminder status
    firestore_service.set_reminder_sent("test_user_reminder", today, "third")
    reminder_status = firestore_service.get_reminder_status("test_user_reminder", today)
    assert reminder_status["third_sent"] is True
    
    # Cleanup
    firestore_service.db.collection('users').document("test_user_reminder").delete()
    firestore_service.db.collection('reminder_status').document("test_user_reminder").delete()


@pytest.mark.asyncio
async def test_reminder_not_sent_after_checkin():
    """Test that reminders stop after user checks in."""
    
    # Create test user
    test_user = User(
        user_id="test_user_checkin",
        telegram_id=987654321,
        name="Test Checkin User"
    )
    firestore_service.create_user(test_user)
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    # Simulate check-in (create dummy check-in)
    from src.models.schemas import DailyCheckIn, Tier1NonNegotiables, CheckInResponses
    
    checkin = DailyCheckIn(
        date=today,
        user_id="test_user_checkin",
        mode="maintenance",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=True, training=True, deep_work=True, zero_porn=True, boundaries=True
        ),
        responses=CheckInResponses(
            challenges="Test",
            rating=8,
            rating_reason="Test",
            tomorrow_priority="Test",
            tomorrow_obstacle="Test"
        ),
        compliance_score=100.0
    )
    firestore_service.store_checkin("test_user_checkin", checkin)
    
    # Test: User should NOT be in reminder list after check-in
    users_without_checkin = firestore_service.get_users_without_checkin_today(today)
    assert not any(u.user_id == "test_user_checkin" for u in users_without_checkin)
    
    # Cleanup
    firestore_service.db.collection('users').document("test_user_checkin").delete()
    firestore_service.db.collection('daily_checkins').document("test_user_checkin").delete()


# Run tests
# pytest tests/integration/test_reminder_flow.py -v
```

---

## 3. Manual Testing (Telegram Bot)

### Setup Test Users

Create 3 test Telegram accounts or use real friends:

1. **User A:** Fresh onboarding (test new user flow)
2. **User B:** Existing user (test migration)
3. **User C:** Test late check-in & shields

### Test Case 1: New User Onboarding

**Steps:**

1. Send `/start` to bot
2. Read welcome message
3. Click "Maintenance" mode button
4. Confirm timezone "Yes, IST is correct"
5. Read streak mechanics explanation
6. Send `/status` to verify profile

**Expected Results:**

- ✅ Welcome message includes Tier 1 explanation
- ✅ Mode selection has 3 buttons (Optimization, Maintenance, Survival)
- ✅ Timezone confirmation has 2 buttons (Yes/No)
- ✅ `/status` shows: Mode = Maintenance, Shields = 🛡️🛡️🛡️ (3/3)

### Test Case 2: Complete Check-In Flow

**Steps:**

1. Send `/checkin`
2. Answer all 4 questions
3. Receive AI feedback
4. Send `/status` to verify streak

**Expected Results:**

- ✅ Check-in completes successfully
- ✅ Compliance score calculated (0-100%)
- ✅ Streak increments to 1
- ✅ `/status` shows "Today: ✅ Check-in complete!"

### Test Case 3: Late Check-In (Before 3 AM)

**Test Time:** Between 12:00 AM - 2:59 AM

**Steps:**

1. Wait until after midnight (e.g., 1:30 AM Feb 5)
2. Send `/checkin`
3. Complete check-in
4. Check Firestore to verify date

**Expected Results:**

- ✅ Check-in stored with date = Feb 4 (previous day), not Feb 5
- ✅ Streak continues from previous day
- ✅ No duplicate check-in error

### Test Case 4: Late Check-In (After 3 AM)

**Test Time:** After 3:00 AM

**Steps:**

1. Wait until after 3 AM (e.g., 3:30 AM Feb 5)
2. Send `/checkin`
3. Complete check-in
4. Check Firestore to verify date

**Expected Results:**

- ✅ Check-in stored with date = Feb 5 (current day)
- ✅ Streak resets (gap from Feb 4)
- ✅ "Today" shows Feb 5

### Test Case 5: Streak Shield Usage

**Setup:** User has 3/3 shields, hasn't checked in today

**Steps:**

1. Send `/use_shield`
2. Read confirmation message
3. Send `/status` to verify shields remaining

**Expected Results:**

- ✅ Message: "Streak Shield Activated! Your X-day streak is protected."
- ✅ Shields remaining: 2/3 (one used)
- ✅ Firestore updated (shields.used = 1, shields.available = 2)

### Test Case 6: Streak Shield When Already Checked In

**Setup:** User already checked in today

**Steps:**

1. Complete `/checkin`
2. Send `/use_shield`

**Expected Results:**

- ✅ Message: "Shield Not Needed! You've already checked in."
- ✅ Shields NOT consumed (still 3/3)

### Test Case 7: Streak Shield When No Shields Left

**Setup:** User has 0/3 shields (used all 3)

**Steps:**

1. Manually set user's shields to 0 in Firestore
2. Send `/use_shield`

**Expected Results:**

- ✅ Message: "No Streak Shields Available. You've used all 3 shields this month."
- ✅ Shows last reset date

### Test Case 8: Triple Reminder System

**Test Time:** 8:55 PM IST (prepare for reminders)

**Steps:**

1. Do NOT check in today
2. Wait for 9:00 PM IST
3. Check Telegram for first reminder
4. Still don't check in
5. Wait for 9:30 PM IST
6. Check for second reminder
7. Still don't check in
8. Wait for 10:00 PM IST
9. Check for third reminder

**Expected Results:**

- ✅ **9:00 PM:** First reminder received (friendly tone)
  - "🔔 Daily Check-In Time! Ready? /checkin"
- ✅ **9:30 PM:** Second reminder received (nudge tone)
  - "👋 Still There? Your check-in is waiting!"
- ✅ **10:00 PM:** Third reminder received (urgent tone)
  - "⚠️ URGENT: Check-In Closing Soon! Your X-day streak is at risk"
  - Shows shield info if available

### Test Case 9: No Reminder After Early Check-In

**Steps:**

1. Complete `/checkin` at 6:00 PM (before reminders)
2. Wait for 9:00 PM, 9:30 PM, 10:00 PM

**Expected Results:**

- ✅ NO reminders received (already checked in)

### Test Case 10: Multi-User Isolation

**Setup:** 3 different users (A, B, C)

**Steps:**

1. User A completes check-in
2. User B does NOT check in
3. User C completes check-in
4. Check reminder logs at 9 PM

**Expected Results:**

- ✅ Only User B receives reminder (A and C already checked in)
- ✅ Each user sees only their own data in `/status`
- ✅ No data leakage between users

---

## 4. Load Testing (10+ Users)

### Simulate Multiple Users

```python
# scripts/load_test_reminders.py

from src.services.firestore_service import firestore_service
from src.models.schemas import User
from datetime import datetime

def create_test_users(count=10):
    """Create multiple test users for load testing."""
    print(f"Creating {count} test users...")
    
    for i in range(count):
        user = User(
            user_id=f"load_test_user_{i}",
            telegram_id=100000 + i,
            name=f"LoadTest{i}",
            timezone="Asia/Kolkata",
            constitution_mode="maintenance"
        )
        firestore_service.create_user(user)
        print(f"  ✅ Created user: load_test_user_{i}")
    
    print(f"\n✅ Created {count} test users")

def test_reminder_query_performance():
    """Test reminder query performance with multiple users."""
    import time
    
    today = datetime.now().strftime("%Y-%m-%d")
    
    start = time.time()
    users_without_checkin = firestore_service.get_users_without_checkin_today(today)
    duration = time.time() - start
    
    print(f"\n📊 Reminder Query Performance:")
    print(f"   Users without check-in: {len(users_without_checkin)}")
    print(f"   Query duration: {duration:.2f} seconds")
    print(f"   Target: <5 seconds for 50 users")
    
    if duration < 5:
        print(f"   ✅ PASS: Query completed in {duration:.2f}s")
    else:
        print(f"   ❌ FAIL: Query too slow ({duration:.2f}s)")

def cleanup_test_users(count=10):
    """Delete test users after load testing."""
    print(f"\nCleaning up {count} test users...")
    
    for i in range(count):
        user_id = f"load_test_user_{i}"
        firestore_service.db.collection('users').document(user_id).delete()
        print(f"  ✅ Deleted: {user_id}")
    
    print(f"\n✅ Cleanup complete")

if __name__ == "__main__":
    # Create 10 test users
    create_test_users(10)
    
    # Test query performance
    test_reminder_query_performance()
    
    # Cleanup
    cleanup_test_users(10)
```

**Run Load Test:**

```bash
python scripts/load_test_reminders.py
```

**Expected Output:**

```
Creating 10 test users...
  ✅ Created user: load_test_user_0
  ...
  ✅ Created user: load_test_user_9

✅ Created 10 test users

📊 Reminder Query Performance:
   Users without check-in: 10
   Query duration: 1.23 seconds
   Target: <5 seconds for 50 users
   ✅ PASS: Query completed in 1.23s

Cleaning up 10 test users...
  ✅ Deleted: load_test_user_0
  ...

✅ Cleanup complete
```

---

## 5. Error Scenarios

### Test Error Handling

1. **Invalid Mode Selection**
   - Steps: Edit callback_data to invalid mode
   - Expected: Graceful error, fallback to "maintenance"

2. **Firestore Connection Lost**
   - Steps: Temporarily disable Firestore
   - Expected: Health check fails, error logged, user sees friendly message

3. **Telegram API Timeout**
   - Steps: Send very long message (>4096 chars)
   - Expected: Message truncated or split

4. **Duplicate Check-In Attempt**
   - Steps: Complete `/checkin`, try again same day
   - Expected: Message: "You've already completed today's check-in!"

5. **Shield Usage Edge Cases**
   - Scenario 1: Use shield when no streak (streak = 0)
   - Scenario 2: Use shield multiple times rapidly
   - Expected: Proper validation, no double-deduction

---

## 6. Regression Testing (Phase 1-2 Features)

Ensure Phase 3A didn't break existing features:

### Test Existing Features Still Work

1. **Basic Check-In (Phase 1)**
   - `/checkin` → Complete 4 questions → Feedback
   - Expected: Works exactly as before

2. **Streak Calculation (Phase 1)**
   - Check in daily for 3 days
   - Expected: Streak = 3, longest streak updates

3. **Pattern Detection (Phase 2)**
   - Miss training 3 days in a row
   - Expected: Pattern intervention sent

4. **AI Feedback (Phase 2)**
   - Complete check-in with low compliance
   - Expected: Gemini generates personalized feedback

### Run Existing Tests

```bash
# Run all Phase 1-2 tests to ensure no regressions
pytest tests/test_checkin_agent.py -v
pytest tests/test_compliance.py -v
pytest tests/test_streak.py -v
pytest tests/test_intent_classification.py -v
```

---

## 7. Test Results Documentation

### Test Summary Template

```markdown
## Phase 3A Test Results

**Date:** [YYYY-MM-DD]
**Tester:** [Name]
**Environment:** [Local/Production]

### Unit Tests
- ✅ Streak shields: 6/6 passed
- ✅ Late check-in: 5/5 passed
- ⬜ Total: 11/11 passed (100%)

### Integration Tests
- ✅ Reminder flow: PASS
- ✅ No reminder after check-in: PASS
- ⬜ Total: 2/2 passed (100%)

### Manual Tests
- ✅ New user onboarding: PASS
- ✅ Complete check-in: PASS
- ✅ Late check-in (before 3 AM): PASS
- ✅ Late check-in (after 3 AM): PASS
- ✅ Streak shield usage: PASS
- ✅ Shield when checked in: PASS
- ✅ Shield when none left: PASS
- ✅ Triple reminders: PASS (9 PM, 9:30 PM, 10 PM all received)
- ✅ No reminder after early check-in: PASS
- ✅ Multi-user isolation: PASS
- ⬜ Total: 10/10 passed (100%)

### Load Tests
- ✅ 10 users: Query time = 1.2s (target: <5s)
- ✅ 50 users: Query time = 3.8s (target: <5s)
- ⬜ Performance: PASS

### Regression Tests
- ✅ Phase 1 features: All working
- ✅ Phase 2 features: All working
- ⬜ No regressions detected

### Issues Found
- None

### Overall Status
✅ **Phase 3A READY FOR PRODUCTION**

All tests passed. No critical issues.
Deployment can proceed.
```

---

## 8. Success Criteria

Phase 3A is ready for production if:

✅ **All unit tests pass** (100%)  
✅ **All integration tests pass** (100%)  
✅ **Manual tests complete successfully** (10/10)  
✅ **Load test performance acceptable** (<5s for 50 users)  
✅ **No Phase 1-2 regressions** (all existing features work)  
✅ **Error handling graceful** (no crashes)  
✅ **Cost projections accurate** (<$5/month for 10 users)

---

## Testing Complete! 🎉

Once all tests pass, proceed to `PHASE3A_DEPLOYMENT.md` for production deployment.
