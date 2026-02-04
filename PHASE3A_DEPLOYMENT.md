# Phase 3A Deployment Guide

**Date:** February 4, 2026  
**Phase:** 3A - Critical Foundation (Multi-User + Triple Reminder System)  
**Status:** Ready for Deployment

---

## 📋 Deployment Checklist

### ✅ Pre-Deployment Tasks

- [x] **Database Schema Updated:** All Phase 3A fields added to User model
- [x] **Code Complete:** Onboarding flow, reminders, late check-in, shields implemented
- [x] **Testing:** Local testing completed (see PHASE3A_TESTING.md)
- [ ] **Firestore Data Migration:** Existing users need Phase 3A fields
- [ ] **Cloud Scheduler Jobs:** Create 3 reminder cron jobs
- [ ] **Deploy to Cloud Run:** Push updated code
- [ ] **Webhook Verification:** Confirm Telegram webhook working
- [ ] **End-to-End Test:** Test full flow with real user

---

## 1. Database Migration (Existing Users)

### Why Migration Needed?

Existing Phase 1-2 users don't have Phase 3A fields (reminder_times, streak_shields, etc.). We need to add them.

### Migration Strategy

**Option A: Automatic Migration (Recommended)**

The schema has default values, so existing users will automatically get Phase 3A fields when they interact with the bot. No manual migration needed!

```python
# User model has defaults for all Phase 3A fields:
reminder_times: ReminderTimes = Field(default_factory=ReminderTimes)  # 9 PM, 9:30 PM, 10 PM
quick_checkin_count: int = Field(default=0, ge=0)
streak_shields: StreakShields = Field(default_factory=StreakShields)  # 3/3
achievements: List[str] = Field(default_factory=list)  # Empty
level: int = Field(default=1, ge=1)
xp: int = Field(default=0, ge=0)
career_mode: str = "skill_building"
```

**Option B: Manual Migration Script (Optional)**

If you want to explicitly migrate all users at once:

```python
# scripts/migrate_phase3a_fields.py

from src.services.firestore_service import firestore_service
from src.models.schemas import ReminderTimes, StreakShields
from datetime import datetime

def migrate_users_to_phase3a():
    """
    Add Phase 3A fields to all existing users.
    """
    users = firestore_service.get_active_users()
    
    print(f"Migrating {len(users)} users to Phase 3A schema...")
    
    for user in users:
        print(f"Migrating user: {user.user_id} ({user.name})")
        
        # Update user with Phase 3A fields (only if missing)
        updates = {}
        
        # Add reminder_times if not present
        if not hasattr(user, 'reminder_times'):
            updates['reminder_times'] = ReminderTimes().model_dump()
        
        # Add streak_shields if not present
        if not hasattr(user, 'streak_shields'):
            shields = StreakShields()
            shields.last_reset = datetime.utcnow().strftime("%Y-%m-%d")
            updates['streak_shields'] = shields.model_dump()
        
        # Add other Phase 3A fields
        if not hasattr(user, 'achievements'):
            updates['achievements'] = []
        
        if not hasattr(user, 'level'):
            updates['level'] = 1
            updates['xp'] = 0
        
        if not hasattr(user, 'career_mode'):
            updates['career_mode'] = 'skill_building'
        
        if not hasattr(user, 'quick_checkin_count'):
            updates['quick_checkin_count'] = 0
        
        # Perform update if needed
        if updates:
            user_ref = firestore_service.db.collection('users').document(user.user_id)
            user_ref.update({
                **updates,
                'updated_at': datetime.utcnow()
            })
            print(f"  ✅ Updated: {list(updates.keys())}")
        else:
            print(f"  ℹ️  Already migrated")
    
    print(f"\n✅ Migration complete! {len(users)} users updated.")

if __name__ == "__main__":
    migrate_users_to_phase3a()
```

**Run Migration:**

```bash
# From project root
python scripts/migrate_phase3a_fields.py
```

---

## 2. Deploy Code to Cloud Run

### Step 1: Update requirements.txt

Ensure all dependencies are up-to-date:

```bash
# Check current requirements
cat requirements.txt

# If any packages were added, regenerate:
# pip freeze > requirements.txt
```

### Step 2: Test Locally (Optional but Recommended)

```bash
# Activate virtual environment
source venv/bin/activate

# Run FastAPI locally
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, test health endpoint
curl http://localhost:8000/health
```

### Step 3: Deploy to Cloud Run

```bash
# Set project
gcloud config set project accountability-agent-452418

# Deploy (from project root)
gcloud run deploy constitution-agent \
  --source . \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 512Mi \
  --timeout 60s \
  --set-env-vars="ENVIRONMENT=production"

# Deployment takes 2-3 minutes
# Output will show: Service URL: https://constitution-agent-XXXXX-as.a.run.app
```

### Step 4: Verify Deployment

```bash
# Get service URL
SERVICE_URL=$(gcloud run services describe constitution-agent \
  --region asia-south1 \
  --format 'value(status.url)')

echo "Service URL: $SERVICE_URL"

# Test health endpoint
curl $SERVICE_URL/health

# Expected response:
# {
#   "status": "healthy",
#   "service": "constitution-agent",
#   "version": "1.0.0",
#   "environment": "production",
#   "checks": {
#     "firestore": "ok"
#   }
# }
```

---

## 3. Create Cloud Scheduler Jobs (Triple Reminder System)

### Why Cloud Scheduler?

Cloud Scheduler triggers our reminder endpoints at 9 PM, 9:30 PM, and 10 PM IST daily. This is the **Phase 3A killer feature** - proactive reminders to prevent ghosting.

### Create 3 Scheduler Jobs

```bash
# Get Cloud Run service URL
SERVICE_URL=$(gcloud run services describe constitution-agent \
  --region asia-south1 \
  --format 'value(status.url)')

# ===== Job 1: First Reminder (9:00 PM IST) =====

gcloud scheduler jobs create http reminder-first-job \
  --location=asia-south1 \
  --schedule="30 15 * * *" \
  --time-zone="Asia/Kolkata" \
  --uri="${SERVICE_URL}/cron/reminder_first" \
  --http-method=POST \
  --oidc-service-account-email=accountability-agent@accountability-agent-452418.iam.gserviceaccount.com \
  --headers="X-CloudScheduler-JobName=reminder-first-job" \
  --description="Daily check-in reminder at 9:00 PM IST (first of three)" \
  --attempt-deadline=60s

# NOTE: Schedule is in UTC, not IST!
# IST = UTC+5:30, so 9:00 PM IST = 3:30 PM UTC = 15:30 = "30 15 * * *"

# ===== Job 2: Second Reminder (9:30 PM IST) =====

gcloud scheduler jobs create http reminder-second-job \
  --location=asia-south1 \
  --schedule="0 16 * * *" \
  --time-zone="Asia/Kolkata" \
  --uri="${SERVICE_URL}/cron/reminder_second" \
  --http-method=POST \
  --oidc-service-account-email=accountability-agent@accountability-agent-452418.iam.gserviceaccount.com \
  --headers="X-CloudScheduler-JobName=reminder-second-job" \
  --description="Daily check-in reminder at 9:30 PM IST (second of three)" \
  --attempt-deadline=60s

# 9:30 PM IST = 4:00 PM UTC = 16:00 = "0 16 * * *"

# ===== Job 3: Third Reminder (10:00 PM IST) =====

gcloud scheduler jobs create http reminder-third-job \
  --location=asia-south1 \
  --schedule="30 16 * * *" \
  --time-zone="Asia/Kolkata" \
  --uri="${SERVICE_URL}/cron/reminder_third" \
  --http-method=POST \
  --oidc-service-account-email=accountability-agent@accountability-agent-452418.iam.gserviceaccount.com \
  --headers="X-CloudScheduler-JobName=reminder-third-job" \
  --description="Daily check-in reminder at 10:00 PM IST (third urgent)" \
  --attempt-deadline=60s

# 10:00 PM IST = 4:30 PM UTC = 16:30 = "30 16 * * *"
```

### Verify Scheduler Jobs

```bash
# List all scheduler jobs
gcloud scheduler jobs list --location=asia-south1

# Expected output:
# ID                  LOCATION      SCHEDULE (TZ)       TARGET_TYPE  STATE
# reminder-first-job  asia-south1   30 15 * * * (IST)   HTTP         ENABLED
# reminder-second-job asia-south1   0 16 * * * (IST)    HTTP         ENABLED
# reminder-third-job  asia-south1   30 16 * * * (IST)   HTTP         ENABLED
```

### Test Scheduler Jobs Manually

```bash
# Trigger first reminder job manually (don't wait for 9 PM)
gcloud scheduler jobs run reminder-first-job --location=asia-south1

# Check logs to verify it worked
gcloud run logs read constitution-agent \
  --region=asia-south1 \
  --limit=50 \
  | grep "First reminder"

# Expected log output:
# 🔔 First reminder triggered by: reminder-first-job
# 📤 Sending first reminder to X users
# ✅ Sent first reminder to 123456789 (Ayush)
# ✅ First reminder complete: 1 sent, 0 errors
```

---

## 4. Telegram Webhook Configuration

### Why Webhook Update Needed?

When we redeploy to Cloud Run, the service URL might change. We need to update Telegram's webhook to point to the new URL.

### Update Webhook

**Option A: Automatic (Handled by FastAPI Startup Event)**

The app automatically sets the webhook on startup if `WEBHOOK_URL` environment variable is set.

```bash
# Set webhook URL as environment variable
gcloud run services update constitution-agent \
  --region=asia-south1 \
  --set-env-vars="WEBHOOK_URL=${SERVICE_URL}"

# Redeploy to trigger webhook update
gcloud run services update constitution-agent \
  --region=asia-south1 \
  --update-env-vars=ENVIRONMENT=production
```

**Option B: Manual (Using Telegram API)**

```bash
# Get bot token from .env or config
BOT_TOKEN="YOUR_BOT_TOKEN"

# Set webhook manually
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -d "url=${SERVICE_URL}/webhook/telegram"

# Verify webhook
curl "https://api.telegram.org/bot${BOT_TOKEN}/getWebhookInfo"

# Expected response:
# {
#   "ok": true,
#   "result": {
#     "url": "https://constitution-agent-XXXXX-as.a.run.app/webhook/telegram",
#     "has_custom_certificate": false,
#     "pending_update_count": 0
#   }
# }
```

---

## 5. End-to-End Testing

### Test Flow

1. **Onboarding Flow (New User)**

```
User: /start
Bot: Welcome message → Mode selection buttons → Timezone confirmation → Ready prompt
User: Click "Maintenance" button
Bot: Mode selected → Timezone confirmation → Streak explanation → First check-in prompt
```

2. **Check-In Flow**

```
User: /checkin
Bot: Question 1 (Tier 1) → Q2 (Challenges) → Q3 (Rating) → Q4 (Tomorrow) → AI Feedback
Expected: Compliance score calculated, streak updated, check-in stored
```

3. **Status Check**

```
User: /status
Bot: Shows streak, shields (3/3), mode, compliance, today's status
Expected: All Phase 3A fields displayed correctly
```

4. **Late Check-In (Before 3 AM)**

```
Time: 1:30 AM Feb 5
User: /checkin (completes check-in)
Expected: Check-in counts for Feb 4 (previous day), not Feb 5
```

5. **Reminder System**

```
Wait until 9:00 PM IST
Expected: All users without check-in receive first reminder
Expected: Message includes streak count and friendly tone

Wait until 9:30 PM IST (if not checked in)
Expected: Second reminder received (nudge tone)

Wait until 10:00 PM IST (if still not checked in)
Expected: Third urgent reminder with shield info
```

6. **Streak Shield**

```
Scenario: User missed yesterday's check-in
User: /use_shield
Bot: Shield activated, streak protected, shields remaining shown
Expected: Firestore updated (shields.used += 1, shields.available -= 1)
```

---

## 6. Monitoring & Logging

### View Logs

```bash
# Real-time logs
gcloud run logs tail constitution-agent --region=asia-south1

# Filter for reminders
gcloud run logs read constitution-agent \
  --region=asia-south1 \
  --limit=100 \
  | grep "reminder"

# Filter for errors
gcloud run logs read constitution-agent \
  --region=asia-south1 \
  --limit=100 \
  | grep "❌"
```

### Key Metrics to Monitor

1. **Reminder Success Rate**
   - Check logs for "reminders_sent" count
   - Should be close to (total users - users who checked in early)

2. **Late Check-In Usage**
   - Check logs for check-ins between 12 AM - 3 AM
   - Verify they count for previous day

3. **Streak Shield Usage**
   - Monitor how many users use shields
   - High usage (>50% of users) = system too lenient

4. **Error Rate**
   - Check logs for "❌ Failed" messages
   - Should be <1% error rate

### Set Up Alerts (Optional)

```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=YOUR_CHANNEL_ID \
  --display-name="Constitution Agent Errors" \
  --condition-display-name="Error Rate > 5%" \
  --condition-threshold-value=5 \
  --condition-threshold-duration=300s \
  --condition-filter='resource.type="cloud_run_revision"
    AND resource.labels.service_name="constitution-agent"
    AND severity="ERROR"'
```

---

## 7. Rollback Plan (If Issues Occur)

### Rollback to Previous Version

```bash
# List revisions
gcloud run revisions list \
  --service=constitution-agent \
  --region=asia-south1

# Rollback to previous revision
gcloud run services update-traffic constitution-agent \
  --region=asia-south1 \
  --to-revisions=PREVIOUS_REVISION=100

# Example:
# gcloud run services update-traffic constitution-agent \
#   --region=asia-south1 \
#   --to-revisions=constitution-agent-00042-abc=100
```

### Disable Scheduler Jobs

```bash
# If reminders are causing issues, disable them temporarily
gcloud scheduler jobs pause reminder-first-job --location=asia-south1
gcloud scheduler jobs pause reminder-second-job --location=asia-south1
gcloud scheduler jobs pause reminder-third-job --location=asia-south1

# Re-enable when fixed
gcloud scheduler jobs resume reminder-first-job --location=asia-south1
gcloud scheduler jobs resume reminder-second-job --location=asia-south1
gcloud scheduler jobs resume reminder-third-job --location=asia-south1
```

---

## 8. Cost Estimates (Phase 3A)

### Current Phase 2 Costs

- **Cloud Run:** $0/month (within free tier)
- **Firestore:** $0.01/month (minimal reads/writes)
- **Vertex AI (Gemini):** $0.0036/month (1 user)
- **Total:** ~$0.01/month

### Phase 3A Projected Costs (10 Users)

- **Cloud Run:** $0/month (still within free tier with reminders)
- **Firestore:** $0.10/month (more reads for reminders)
- **Vertex AI (Gemini):** $1.70/month (10 users × $0.17)
- **Cloud Scheduler:** $0.90/month (3 jobs × $0.30 each)
- **Total:** ~$2.70/month

### Phase 3A Projected Costs (50 Users)

- **Cloud Run:** $0.50/month (exceeds free tier slightly)
- **Firestore:** $0.50/month
- **Vertex AI (Gemini):** $8.50/month (50 users × $0.17)
- **Cloud Scheduler:** $0.90/month
- **Total:** ~$10.40/month

**Budget:** Still well under $50/month target! 🎉

---

## 9. Success Criteria

Phase 3A deployment is successful if:

✅ **All reminders sent on time** (9 PM, 9:30 PM, 10 PM IST daily)  
✅ **Late check-ins work** (before 3 AM counts for previous day)  
✅ **Streak shields functional** (/use_shield command works)  
✅ **Onboarding flow complete** (new users can sign up and select mode)  
✅ **No existing users broken** (Phase 1-2 users still work)  
✅ **Error rate <1%** (minimal failures in logs)  
✅ **Cost stays <$5/month** (for 10 users)

---

## 10. Next Steps After Phase 3A

Once Phase 3A is stable (1 week of monitoring):

1. **Phase 3B:** Ghosting Detection + Emotional Support Agent
2. **Phase 3C:** Gamification (Achievements, Levels, XP)
3. **Phase 3D:** Career Tracking + Advanced Patterns
4. **Phase 3E:** Quick Check-In + Query Agent
5. **Phase 3F:** Weekly Reports + Social Features

---

## Deployment Summary

```bash
# Complete deployment in order:

# 1. Deploy code
gcloud run deploy constitution-agent --source . --region asia-south1

# 2. Get service URL
SERVICE_URL=$(gcloud run services describe constitution-agent --region asia-south1 --format 'value(status.url)')

# 3. Create scheduler jobs
gcloud scheduler jobs create http reminder-first-job --schedule="30 15 * * *" --uri="${SERVICE_URL}/cron/reminder_first" ...
gcloud scheduler jobs create http reminder-second-job --schedule="0 16 * * *" --uri="${SERVICE_URL}/cron/reminder_second" ...
gcloud scheduler jobs create http reminder-third-job --schedule="30 16 * * *" --uri="${SERVICE_URL}/cron/reminder_third" ...

# 4. Test manually
gcloud scheduler jobs run reminder-first-job --location=asia-south1

# 5. Monitor logs
gcloud run logs tail constitution-agent --region=asia-south1

# 6. Test end-to-end with Telegram bot
```

🚀 **Phase 3A Ready for Production!**
