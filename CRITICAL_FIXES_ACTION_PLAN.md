# Critical Fixes: Action Plan & Implementation Guide

**Date:** February 3, 2026  
**Priority:** P0 - Fix Before Adding New Users  
**Estimated Time:** 5-7 days total

---

## 🎯 Overview

This document provides **step-by-step implementation instructions** for the 5 critical gaps identified in the product review.

**Goal:** Make the bot actually fulfill its core mission - **prevent ghosting spirals** like the Feb 2025 regression.

---

## Fix #1: Add 9 PM Check-In Reminder ⚡

**Why:** You WILL forget to check in one day and break your streak  
**Time:** 1 hour  
**Impact:** HIGH - Prevents #1 failure mode

### Implementation Steps

#### Step 1: Create Reminder Endpoint (15 min)

**File:** `src/main.py`

```python
@app.post("/cron/checkin_reminder")
async def checkin_reminder():
    """
    Triggered by Cloud Scheduler daily at 9 PM IST.
    Sends reminder to all users who haven't checked in today.
    """
    logger.info("Starting daily check-in reminder scan...")
    
    today = get_current_date_ist()
    users = firestore_service.get_all_users()
    
    reminders_sent = 0
    
    for user in users:
        # Check if user already checked in today
        if not firestore_service.checkin_exists(user.user_id, today):
            try:
                # Send reminder
                await bot_manager.application.bot.send_message(
                    chat_id=int(user.telegram_id),
                    text=(
                        "🔔 **Daily Check-In Time!**\n\n"
                        f"Current streak: {user.streaks.current_streak} days\n"
                        f"Personal best: {user.streaks.longest_streak} days\n\n"
                        "Ready to check in? /checkin"
                    ),
                    parse_mode='Markdown'
                )
                reminders_sent += 1
                logger.info(f"✅ Reminder sent to user {user.user_id}")
            except Exception as e:
                logger.error(f"❌ Failed to send reminder to {user.user_id}: {e}")
    
    logger.info(f"Check-in reminder scan complete. Sent {reminders_sent} reminders.")
    
    return {
        "status": "success",
        "reminders_sent": reminders_sent,
        "timestamp": datetime.utcnow().isoformat()
    }
```

#### Step 2: Create Cloud Scheduler Job (10 min)

```bash
# Enable Cloud Scheduler API (if not already enabled)
gcloud services enable cloudscheduler.googleapis.com

# Create job (runs daily at 9 PM IST = 3:30 PM UTC)
gcloud scheduler jobs create http checkin-reminder-job \
  --schedule="30 15 * * *" \
  --time-zone="Asia/Kolkata" \
  --uri="https://constitution-agent-450357249483.asia-south1.run.app/cron/checkin_reminder" \
  --http-method=POST \
  --headers="Content-Type=application/json" \
  --location=asia-south1

# Verify job created
gcloud scheduler jobs describe checkin-reminder-job --location=asia-south1

# Test job manually
gcloud scheduler jobs run checkin-reminder-job --location=asia-south1
```

#### Step 3: Add Follow-Up Reminder (20 min)

**File:** `src/main.py`

```python
@app.post("/cron/checkin_followup")
async def checkin_followup():
    """
    Triggered 30 minutes after first reminder (9:30 PM IST).
    Sends follow-up to users who still haven't checked in.
    """
    logger.info("Starting check-in follow-up scan...")
    
    today = get_current_date_ist()
    users = firestore_service.get_all_users()
    
    followups_sent = 0
    
    for user in users:
        if not firestore_service.checkin_exists(user.user_id, today):
            try:
                await bot_manager.application.bot.send_message(
                    chat_id=int(user.telegram_id),
                    text=(
                        "👋 **Still there?**\n\n"
                        "Your daily check-in is waiting. Takes just 2 minutes!\n\n"
                        "/checkin"
                    )
                )
                followups_sent += 1
            except Exception as e:
                logger.error(f"❌ Failed to send follow-up to {user.user_id}: {e}")
    
    logger.info(f"Follow-up scan complete. Sent {followups_sent} follow-ups.")
    
    return {"status": "success", "followups_sent": followups_sent}
```

**Create second scheduler job:**

```bash
# 9:30 PM IST = 4:00 PM UTC
gcloud scheduler jobs create http checkin-followup-job \
  --schedule="0 16 * * *" \
  --time-zone="Asia/Kolkata" \
  --uri="https://constitution-agent-450357249483.asia-south1.run.app/cron/checkin_followup" \
  --http-method=POST \
  --location=asia-south1
```

#### Step 4: Add Final Warning (15 min)

**File:** `src/main.py`

```python
@app.post("/cron/checkin_warning")
async def checkin_warning():
    """
    Triggered at 10 PM IST (final warning before midnight).
    """
    today = get_current_date_ist()
    users = firestore_service.get_all_users()
    
    warnings_sent = 0
    
    for user in users:
        if not firestore_service.checkin_exists(user.user_id, today):
            try:
                await bot_manager.application.bot.send_message(
                    chat_id=int(user.telegram_id),
                    text=(
                        "⚠️ **Final Reminder**\n\n"
                        "Check-in closes at midnight!\n"
                        f"Don't break your {user.streaks.current_streak}-day streak.\n\n"
                        "/checkin"
                    )
                )
                warnings_sent += 1
            except Exception as e:
                logger.error(f"❌ Failed to send warning to {user.user_id}: {e}")
    
    return {"status": "success", "warnings_sent": warnings_sent}
```

**Create third scheduler job:**

```bash
# 10 PM IST = 4:30 PM UTC
gcloud scheduler jobs create http checkin-warning-job \
  --schedule="30 16 * * *" \
  --time-zone="Asia/Kolkata" \
  --uri="https://constitution-agent-450357249483.asia-south1.run.app/cron/checkin_warning" \
  --http-method=POST \
  --location=asia-south1
```

#### Step 5: Deploy and Test (10 min)

```bash
# Redeploy Cloud Run
gcloud run deploy constitution-agent \
  --source . \
  --region asia-south1

# Test endpoints manually
curl -X POST https://constitution-agent-450357249483.asia-south1.run.app/cron/checkin_reminder

# Verify you received Telegram message

# View scheduler job logs
gcloud scheduler jobs describe checkin-reminder-job --location=asia-south1
```

**Success Criteria:**
- ✅ Receive reminder at 9 PM IST
- ✅ Receive follow-up at 9:30 PM if not checked in
- ✅ Receive warning at 10 PM if still not checked in

---

## Fix #2: Add Mode Switching Command ⚡

**Why:** You can't change mode without editing Firestore manually  
**Time:** 1 hour  
**Impact:** HIGH - Core constitution feature

### Implementation Steps

#### Step 1: Add Mode Command Handler (30 min)

**File:** `src/bot/telegram_bot.py`

```python
async def mode_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /mode command - Switch constitution operating mode
    
    Modes:
    - Optimization: 6x/week training, aggressive goals
    - Maintenance: 4x/week training, sustaining progress
    - Survival: Crisis mode, minimal expectations
    """
    user_id = str(update.effective_user.id)
    
    # Get current mode
    user = firestore_service.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ Please use /start first.")
        return
    
    current_mode = user.constitution_mode or "maintenance"
    
    # Create mode selection keyboard
    keyboard = [
        [InlineKeyboardButton("🚀 Optimization Mode", callback_data="mode_optimization")],
        [InlineKeyboardButton("🔄 Maintenance Mode", callback_data="mode_maintenance")],
        [InlineKeyboardButton("🛡️ Survival Mode", callback_data="mode_survival")]
    ]
    
    await update.message.reply_text(
        f"**Current Mode:** {current_mode.title()}\n\n"
        "**Select Your Operating Mode:**\n\n"
        "🚀 **Optimization Mode**\n"
        "• Training: 6x/week (Push/Pull/Legs x2)\n"
        "• Deep Work: 2+ hours daily\n"
        "• All metrics tracked aggressively\n\n"
        "🔄 **Maintenance Mode** (Default)\n"
        "• Training: 4x/week\n"
        "• Deep Work: 2+ hours daily\n"
        "• Sustaining progress, not pushing limits\n\n"
        "🛡️ **Survival Mode** (Crisis)\n"
        "• Training: Walking only\n"
        "• Sleep: As much as needed\n"
        "• Minimal expectations, focus on recovery\n\n"
        "Choose your mode:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mode selection button press"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    mode = query.data.replace("mode_", "")  # "mode_optimization" → "optimization"
    
    # Update user mode in Firestore
    firestore_service.update_user_mode(user_id, mode)
    
    mode_emoji = {
        "optimization": "🚀",
        "maintenance": "🔄",
        "survival": "🛡️"
    }
    
    await query.edit_message_text(
        f"✅ Mode updated to **{mode_emoji[mode]} {mode.title()}**\n\n"
        f"Your check-in questions and expectations will be adjusted accordingly.",
        parse_mode='Markdown'
    )
    
    logger.info(f"User {user_id} switched to {mode} mode")
```

#### Step 2: Add Firestore Method (10 min)

**File:** `src/services/firestore_service.py`

```python
def update_user_mode(self, user_id: str, mode: str) -> None:
    """
    Update user's constitution mode
    
    Args:
        user_id: User ID
        mode: One of "optimization", "maintenance", "survival"
    """
    valid_modes = ["optimization", "maintenance", "survival"]
    if mode not in valid_modes:
        raise ValueError(f"Invalid mode: {mode}. Must be one of {valid_modes}")
    
    user_ref = self.db.collection('users').document(user_id)
    user_ref.update({
        'constitution_mode': mode,
        'mode_updated_at': firestore.SERVER_TIMESTAMP
    })
    
    logger.info(f"✅ User {user_id} mode updated to: {mode}")
```

#### Step 3: Register Command (5 min)

**File:** `src/bot/telegram_bot.py`

```python
# In build_application() function
application.add_handler(CommandHandler("mode", mode_command))
application.add_handler(CallbackQueryHandler(mode_callback, pattern="^mode_"))
```

#### Step 4: Update Check-In Questions Based on Mode (15 min)

**File:** `src/bot/conversation.py`

```python
async def ask_tier1_question(message, context):
    """
    Ask Question 1: Tier 1 non-negotiables with inline keyboard.
    Questions adjusted based on current mode.
    """
    mode = context.user_data.get('mode', 'maintenance')
    
    # Adjust training expectations based on mode
    if mode == "optimization":
        training_desc = "💪 **Training:** Workout OR rest day? (6x/week target)"
    elif mode == "maintenance":
        training_desc = "💪 **Training:** Workout OR rest day? (4x/week target)"
    else:  # survival
        training_desc = "💪 **Movement:** Did you walk today? (No workouts during crisis)"
    
    question_text = (
        "**📋 Daily Check-In - Question 1/4**\n\n"
        f"**Mode: {mode.title()}**\n\n"
        "Did you complete the following today?\n\n"
        "• 💤 **Sleep:** 7+ hours last night?\n"
        f"• {training_desc}\n"
        "• 🧠 **Deep Work:** 2+ hours focused work/study?\n"
        "• 🚫 **Zero Porn:** No consumption today?\n"
        "• 🛡️ **Boundaries:** No toxic interactions?\n\n"
        "Click the buttons below to answer:"
    )
    
    # ... rest of function
```

**Success Criteria:**
- ✅ `/mode` shows current mode and selection buttons
- ✅ Clicking button updates mode in Firestore
- ✅ Check-in questions adjust based on selected mode

---

## Fix #3: Add Ghosting Detection ⚡

**Why:** User can ghost for weeks with no escalation (THE core use case)  
**Time:** 2 hours  
**Impact:** CRITICAL - Main constitution goal

### Implementation Steps

#### Step 1: Create Ghosting Pattern Detector (45 min)

**File:** `src/agents/pattern_detection.py`

```python
def detect_ghosting(self, user_id: str) -> Optional[Pattern]:
    """
    Detect missing check-ins (ghosting pattern).
    
    From Constitution:
    - Day 2: Gentle reminder
    - Day 3: Urgent check-in
    - Day 4: Reference historical patterns
    - Day 5: Emergency escalation
    
    Returns:
        Pattern if user has missed 2+ consecutive check-ins
    """
    user = firestore_service.get_user(user_id)
    if not user or not user.streaks.last_checkin_date:
        return None
    
    today = get_current_date_ist()
    last_checkin = datetime.strptime(user.streaks.last_checkin_date, "%Y-%m-%d").date()
    
    # Calculate days since last check-in
    days_since_checkin = (today - last_checkin).days
    
    # Ghosting starts at 2 days
    if days_since_checkin >= 2:
        # Get historical ghosting episodes
        historical_ghosts = firestore_service.get_historical_patterns(
            user_id, 
            pattern_type="ghosting"
        )
        
        # Severity increases with days
        if days_since_checkin >= 5:
            severity = "critical"
        elif days_since_checkin >= 4:
            severity = "high"
        elif days_since_checkin >= 3:
            severity = "medium"
        else:  # 2 days
            severity = "low"
        
        return Pattern(
            type="ghosting",
            severity=severity,
            detected_at=datetime.now(),
            data={
                "days_missing": days_since_checkin,
                "last_checkin_date": user.streaks.last_checkin_date,
                "previous_streak": user.streaks.current_streak,
                "historical_ghost_count": len(historical_ghosts),
                "last_ghost_date": historical_ghosts[-1]["detected_at"] if historical_ghosts else None
            }
        )
    
    return None
```

#### Step 2: Add Ghosting Intervention Messages (45 min)

**File:** `src/agents/intervention.py`

```python
def _build_ghosting_intervention(self, pattern: Pattern, user: Any) -> str:
    """
    Build escalating intervention for ghosting pattern.
    
    Day 2: Gentle
    Day 3: Urgent
    Day 4: Historical pattern reference
    Day 5: Emergency escalation
    """
    days = pattern.data["days_missing"]
    previous_streak = pattern.data["previous_streak"]
    last_date = pattern.data["last_checkin_date"]
    
    if days == 2:
        # Day 2: Gentle reminder
        message = (
            "👋 **Missed Check-In Alert**\n\n"
            f"You haven't checked in for {days} days (last check-in: {last_date}).\n\n"
            f"Your {previous_streak}-day streak is paused but not broken yet. "
            "You have 48 hours to check in before it resets.\n\n"
            "Everything okay? /checkin"
        )
    
    elif days == 3:
        # Day 3: Urgent
        message = (
            "⚠️ **URGENT: 3-Day Absence**\n\n"
            f"You've missed {days} check-ins in a row.\n\n"
            f"Your {previous_streak}-day streak is at risk. "
            "This pattern led to your 6-month regression in Feb 2025.\n\n"
            "**Constitution violation detected.**\n\n"
            "Check in NOW: /checkin"
        )
    
    elif days == 4:
        # Day 4: Historical pattern reference
        hist_count = pattern.data.get("historical_ghost_count", 0)
        last_ghost = pattern.data.get("last_ghost_date")
        
        message = (
            "🚨 **4-DAY ABSENCE - CRITICAL**\n\n"
            f"You've ghosted for {days} days straight.\n\n"
        )
        
        if hist_count > 0:
            message += (
                f"**Historical Pattern:**\n"
                f"You've ghosted {hist_count} times before.\n"
                f"Last time: {last_ghost}\n"
                f"Last outcome: Led to spiral\n\n"
            )
        
        message += (
            f"Your {previous_streak}-day streak is LOST if you don't check in by midnight.\n\n"
            "**This is how spirals start.**\n\n"
            "Check in RIGHT NOW: /checkin"
        )
    
    else:  # Day 5+
        # Day 5: Emergency escalation
        message = (
            "🔴 **EMERGENCY: 5-DAY GHOSTING**\n\n"
            f"You haven't checked in for {days} days.\n\n"
            f"Your {previous_streak}-day streak is BROKEN.\n\n"
            "**Constitution Protocol:**\n"
            "• This is a full regression event\n"
            "• Last time (Feb 2025): 6-month spiral\n"
            "• You need external accountability NOW\n\n"
            "**Immediate Actions:**\n"
            "1. Check in right now: /checkin\n"
            "2. Text your accountability partner\n"
            "3. Schedule call with friend/coach today\n\n"
            "**DO NOT ISOLATE.**"
        )
    
    return message
```

#### Step 3: Update Pattern Scan to Include Ghosting (15 min)

**File:** `src/agents/pattern_detection.py`

```python
def detect_patterns(self, user_id: str) -> List[Pattern]:
    """
    Run all pattern detection rules.
    
    UPDATED: Now includes ghosting detection
    """
    patterns = []
    
    # 1. Check for ghosting FIRST (most critical)
    ghosting_pattern = self.detect_ghosting(user_id)
    if ghosting_pattern:
        patterns.append(ghosting_pattern)
    
    # 2. Only check other patterns if user has checked in recently
    recent_checkins = firestore_service.get_recent_checkins(user_id, days=7)
    
    if not recent_checkins:
        # User has no check-ins, ghosting already detected above
        return patterns
    
    # 3. Check data-based patterns (existing logic)
    pattern = self.detect_sleep_degradation(recent_checkins)
    if pattern:
        patterns.append(pattern)
    
    # ... rest of existing patterns
    
    return patterns
```

#### Step 4: Deploy and Test (15 min)

```bash
# Deploy updated code
gcloud run deploy constitution-agent --source . --region asia-south1

# Test ghosting detection manually
# 1. Set last_checkin_date in Firestore to 2 days ago
# 2. Trigger pattern scan
curl -X POST https://constitution-agent-450357249483.asia-south1.run.app/trigger/pattern-scan

# 3. Verify you received ghosting intervention via Telegram
```

**Success Criteria:**
- ✅ Missing 2 days → Gentle reminder
- ✅ Missing 3 days → Urgent warning
- ✅ Missing 4 days → Historical pattern reference
- ✅ Missing 5 days → Emergency escalation

---

## Fix #4: Add Surgery Recovery Mode Enforcement ⚡

**Why:** Feb 21 - Apr 15 = Recovery period, shouldn't ask about 6x/week training  
**Time:** 1 hour  
**Impact:** HIGH - Medical safety

### Implementation Steps

#### Step 1: Create Date-Based Mode Validator (20 min)

**File:** `src/utils/mode_validator.py` (new file)

```python
"""
Mode Validator - Enforces date-based mode restrictions
"""

from datetime import datetime, date
from typing import Optional

# Surgery recovery dates (from constitution)
SURGERY_START = date(2026, 2, 21)
SURGERY_SURVIVAL_END = date(2026, 3, 7)
SURGERY_MAINTENANCE_END = date(2026, 4, 15)


def get_enforced_mode(user_mode: str, today: Optional[date] = None) -> tuple[str, str]:
    """
    Get enforced mode based on date-based constitution rules.
    
    Args:
        user_mode: User's selected mode
        today: Current date (defaults to today)
        
    Returns:
        Tuple of (enforced_mode, reason)
        
    Examples:
        - Feb 21 - Mar 7: Force survival mode (surgery recovery week)
        - Mar 8 - Apr 15: Force maintenance mode (gradual return)
        - After Apr 15: Allow user's selected mode
    """
    if today is None:
        today = date.today()
    
    # Check if in surgery recovery period
    if SURGERY_START <= today <= SURGERY_SURVIVAL_END:
        return ("survival", "Surgery recovery - Survival mode enforced until Mar 7")
    
    elif SURGERY_SURVIVAL_END < today <= SURGERY_MAINTENANCE_END:
        return ("maintenance", "Post-surgery recovery - Maintenance mode enforced until Apr 15")
    
    else:
        # No date-based override, use user's selected mode
        return (user_mode, "User-selected mode")


def validate_training_question(mode: str, today: Optional[date] = None) -> str:
    """
    Get appropriate training question based on enforced mode.
    
    Returns:
        Training question text
    """
    enforced_mode, _ = get_enforced_mode(mode, today)
    
    if enforced_mode == "survival":
        return "💪 **Movement:** Did you walk today? (No workouts during recovery)"
    elif enforced_mode == "maintenance":
        return "💪 **Training:** Workout OR rest day? (4x/week, no pushing PRs)"
    else:  # optimization
        return "💪 **Training:** Workout OR rest day? (6x/week target)"


def get_mode_notice(user_mode: str, today: Optional[date] = None) -> Optional[str]:
    """
    Get notice to display if mode is being overridden.
    
    Returns:
        Notice text or None if no override
    """
    enforced_mode, reason = get_enforced_mode(user_mode, today)
    
    if enforced_mode != user_mode:
        return (
            f"🏥 **Mode Override Active**\n"
            f"Your selected mode ({user_mode.title()}) is overridden.\n"
            f"Enforced mode: **{enforced_mode.title()}**\n"
            f"Reason: {reason}\n\n"
        )
    
    return None
```

#### Step 2: Update Check-In Questions (20 min)

**File:** `src/bot/conversation.py`

```python
from src.utils.mode_validator import get_enforced_mode, validate_training_question, get_mode_notice

async def ask_tier1_question(message, context):
    """
    Ask Question 1: Tier 1 non-negotiables.
    UPDATED: Now respects date-based mode enforcement
    """
    user_mode = context.user_data.get('mode', 'maintenance')
    today = get_current_date_ist()
    
    # Get enforced mode (may override user's selection)
    enforced_mode, override_reason = get_enforced_mode(user_mode, today)
    
    # Get mode override notice (if applicable)
    mode_notice = get_mode_notice(user_mode, today)
    
    # Store enforced mode for this check-in
    context.user_data['enforced_mode'] = enforced_mode
    
    # Get appropriate training question
    training_question = validate_training_question(enforced_mode, today)
    
    question_text = ""
    
    # Add mode override notice if present
    if mode_notice:
        question_text += mode_notice
    
    question_text += (
        "**📋 Daily Check-In - Question 1/4**\n\n"
        f"**Mode: {enforced_mode.title()}**\n\n"
        "Did you complete the following today?\n\n"
        "• 💤 **Sleep:** 7+ hours last night?\n"
        f"• {training_question}\n"
        "• 🧠 **Deep Work:** 2+ hours focused work/study?\n"
        "• 🚫 **Zero Porn:** No consumption today?\n"
        "• 🛡️ **Boundaries:** No toxic interactions?\n\n"
        "Click the buttons below to answer:"
    )
    
    # ... rest of function
```

#### Step 3: Add Automatic Mode Notification (15 min)

**File:** Create new cron job for mode change notifications

```python
# src/main.py

@app.post("/cron/mode_change_notification")
async def mode_change_notification():
    """
    Triggered on key dates to notify users of automatic mode changes.
    
    Key dates:
    - Feb 21: Surgery start → Survival mode
    - Mar 8: Gradual return → Maintenance mode
    - Apr 16: Full recovery → User-selected mode
    """
    today = get_current_date_ist()
    
    # Check if today is a mode change date
    if today == date(2026, 2, 21):
        message = (
            "🏥 **Surgery Recovery Mode Activated**\n\n"
            "Starting today, your constitution is in **Survival Mode** until Mar 7.\n\n"
            "**Adjusted Expectations:**\n"
            "• Training → Walking only (no workouts)\n"
            "• Sleep → As much as needed\n"
            "• Deep work → Reduced expectations\n"
            "• Focus: HEAL\n\n"
            "This is NON-NEGOTIABLE per medical protocol.\n"
            "See you tonight for check-in! 💪"
        )
        
        users = firestore_service.get_all_users()
        for user in users:
            await bot_manager.application.bot.send_message(
                chat_id=int(user.telegram_id),
                text=message,
                parse_mode='Markdown'
            )
    
    elif today == date(2026, 3, 8):
        message = (
            "🔄 **Maintenance Mode Activated**\n\n"
            "Starting today, gradual return to training.\n\n"
            "**Adjusted Expectations:**\n"
            "• Training → 4x/week (no pushing PRs)\n"
            "• Follow medical clearance only\n"
            "• Still in recovery mode\n\n"
            "Maintenance mode active until Apr 15."
        )
        
        users = firestore_service.get_all_users()
        for user in users:
            await bot_manager.application.bot.send_message(
                chat_id=int(user.telegram_id),
                text=message,
                parse_mode='Markdown'
            )
    
    elif today == date(2026, 4, 16):
        message = (
            "🚀 **Full Recovery Complete!**\n\n"
            "Surgery recovery period ended yesterday.\n"
            "You can now select any mode.\n\n"
            "Use /mode to choose:\n"
            "• Optimization (aggressive)\n"
            "• Maintenance (sustaining)\n"
            "• Survival (if needed)\n\n"
            "Welcome back to full capacity! 💪"
        )
        
        users = firestore_service.get_all_users()
        for user in users:
            await bot_manager.application.bot.send_message(
                chat_id=int(user.telegram_id),
                text=message,
                parse_mode='Markdown'
            )
    
    return {"status": "success"}
```

**Create scheduler job:**

```bash
# Daily check at 8 AM IST for mode change notifications
gcloud scheduler jobs create http mode-change-notification-job \
  --schedule="30 2 * * *" \
  --time-zone="Asia/Kolkata" \
  --uri="https://constitution-agent-450357249483.asia-south1.run.app/cron/mode_change_notification" \
  --http-method=POST \
  --location=asia-south1
```

#### Step 4: Test (5 min)

```bash
# Test mode enforcement
# 1. Change system date to Feb 21, 2026 (or update code to test today)
# 2. Start check-in
# 3. Verify training question says "Did you walk today? (No workouts)"
# 4. Verify mode notice shows "Surgery recovery - Survival mode enforced"
```

**Success Criteria:**
- ✅ Feb 21 - Mar 7: Survival mode enforced, training = walking only
- ✅ Mar 8 - Apr 15: Maintenance mode enforced
- ✅ Apr 16+: User can select any mode
- ✅ Mode override notice displayed during check-in

---

## Fix #5: Add Basic Onboarding Flow ⚡

**Why:** New users have no idea what bot does  
**Time:** 1-2 hours  
**Impact:** HIGH - Prevents 95% abandonment

### Implementation Steps

#### Step 1: Create Onboarding Flow (45 min)

**File:** `src/bot/telegram_bot.py`

```python
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /start command - Now with proper onboarding
    """
    user_id = str(update.effective_user.id)
    
    # Check if user already exists
    existing_user = firestore_service.get_user(user_id)
    
    if existing_user:
        # Returning user
        await update.message.reply_text(
            f"👋 Welcome back!\n\n"
            f"🔥 Current streak: {existing_user.streaks.current_streak} days\n"
            f"🏆 Personal best: {existing_user.streaks.longest_streak} days\n\n"
            "Ready to check in? /checkin\n"
            "Need help? /help"
        )
        return
    
    # NEW USER - Start onboarding
    
    # Step 1: Welcome message
    await update.message.reply_text(
        "👋 **Welcome to Constitution Agent!**\n\n"
        "I'm your AI accountability partner.\n\n"
        "Think of me as a strict but supportive coach who:\n"
        "✅ Tracks your daily commitments\n"
        "✅ Detects harmful patterns before they spiral\n"
        "✅ Provides personalized feedback\n"
        "✅ Keeps you accountable to YOUR constitution\n\n"
        "Let me explain how this works...",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)  # Dramatic pause
    
    # Step 2: Explain Tier 1
    await update.message.reply_text(
        "**📋 Tier 1 Non-Negotiables**\n\n"
        "Every day, I'll ask if you completed these 5 things:\n\n"
        "1️⃣ **Sleep:** 7+ hours\n"
        "2️⃣ **Training:** Workout or rest day\n"
        "3️⃣ **Deep Work:** 2+ hours focused work\n"
        "4️⃣ **Zero Porn:** No consumption\n"
        "5️⃣ **Boundaries:** No toxic interactions\n\n"
        "These are the foundation of your life. Everything else is secondary.",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    
    # Step 3: Explain modes
    keyboard = [
        [InlineKeyboardButton("🚀 Optimization", callback_data="onboard_optimization")],
        [InlineKeyboardButton("🔄 Maintenance", callback_data="onboard_maintenance")],
        [InlineKeyboardButton("🛡️ Survival", callback_data="onboard_survival")]
    ]
    
    await update.message.reply_text(
        "**🎯 Choose Your Operating Mode**\n\n"
        "Your expectations adjust based on your current situation:\n\n"
        "🚀 **Optimization Mode**\n"
        "High capacity, pushing limits\n"
        "Training: 6x/week\n\n"
        "🔄 **Maintenance Mode**\n"
        "Sustaining progress (recommended)\n"
        "Training: 4x/week\n\n"
        "🛡️ **Survival Mode**\n"
        "Crisis/recovery, minimal expectations\n"
        "Training: Walking only\n\n"
        "Which mode are you in right now?",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode='Markdown'
    )


async def onboarding_mode_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle mode selection during onboarding"""
    query = update.callback_query
    await query.answer()
    
    user_id = str(update.effective_user.id)
    mode = query.data.replace("onboard_", "")  # "onboard_maintenance" → "maintenance"
    
    # Create user profile with selected mode
    firestore_service.create_user_profile(
        user_id=user_id,
        telegram_id=update.effective_user.id,
        telegram_username=update.effective_user.username,
        first_name=update.effective_user.first_name,
        constitution_mode=mode
    )
    
    mode_emoji = {
        "optimization": "🚀",
        "maintenance": "🔄",
        "survival": "🛡️"
    }
    
    await query.edit_message_text(
        f"✅ Profile created!\n\n"
        f"**Mode:** {mode_emoji[mode]} {mode.title()}\n\n"
        "You can change this anytime with /mode"
    )
    
    await asyncio.sleep(1)
    
    # Step 4: Explain check-in schedule
    await query.message.reply_text(
        "**⏰ Check-In Schedule**\n\n"
        "I'll remind you daily at **9:00 PM IST** to check in.\n\n"
        "Check-in takes 2-3 minutes:\n"
        "• 5 yes/no questions (Tier 1)\n"
        "• What challenged you today?\n"
        "• How do you rate today 1-10?\n"
        "• What's tomorrow's priority?\n\n"
        "You'll get personalized AI feedback based on your responses.",
        parse_mode='Markdown'
    )
    
    await asyncio.sleep(2)
    
    # Step 5: First check-in prompt
    await query.message.reply_text(
        "🎉 **You're all set!**\n\n"
        "Ready to start your first check-in?\n\n"
        "Type: /checkin\n\n"
        "Or wait until 9 PM tonight for your reminder.",
        parse_mode='Markdown'
    )
```

#### Step 2: Register Onboarding Callbacks (5 min)

```python
# In build_application()
application.add_handler(CallbackQueryHandler(
    onboarding_mode_callback, 
    pattern="^onboard_"
))
```

#### Step 3: Test (10 min)

```bash
# 1. Delete your user profile from Firestore
# 2. Send /start to bot
# 3. Follow onboarding flow
# 4. Verify mode is saved correctly
```

**Success Criteria:**
- ✅ New user gets 5-step onboarding
- ✅ User selects mode during onboarding
- ✅ User profile created with selected mode
- ✅ Clear expectations set (9 PM check-in, Tier 1 definition)

---

## Deployment & Validation

### Final Deployment Steps

```bash
# 1. Run all tests
pytest tests/ -v

# 2. Deploy to Cloud Run
gcloud run deploy constitution-agent \
  --source . \
  --region asia-south1

# 3. Verify all scheduler jobs
gcloud scheduler jobs list --location=asia-south1

# 4. Test each cron endpoint manually
curl -X POST https://YOUR-URL/cron/checkin_reminder
curl -X POST https://YOUR-URL/cron/checkin_followup
curl -X POST https://YOUR-URL/cron/checkin_warning
curl -X POST https://YOUR-URL/trigger/pattern-scan
```

### Validation Checklist

**Day 1 (After Deployment):**
- [ ] Received 9 PM reminder
- [ ] `/mode` command works
- [ ] Onboarding flow tested with test user
- [ ] Ghosting detection doesn't trigger (you checked in today)
- [ ] Surgery mode enforcement verified (if Feb 21-Apr 15)

**Day 2:**
- [ ] Intentionally skip check-in
- [ ] Verify ghosting detection triggers next day
- [ ] Receive Day 2 gentle reminder

**Day 3:**
- [ ] Check in to break ghosting pattern
- [ ] Verify AI feedback still working
- [ ] Test mode switching

**Week 1:**
- [ ] All 5 critical fixes validated in production
- [ ] No errors in Cloud Run logs
- [ ] Cost still under $0.05/month

---

## Cost Impact

**Before Fixes:**
- Monthly cost: $0.0036

**After Fixes:**
- Additional scheduler jobs: +$0.30/month
- Additional LLM calls for onboarding: ~$0.001/new user
- Total monthly cost: ~$0.30/month

**Still well under $5/month budget! ✅**

---

## Success Metrics

After implementing these 5 fixes, you should see:

1. **Zero missed check-ins** due to forgetting (9 PM reminder prevents this)
2. **Immediate ghosting detection** if you do miss (Day 2 reminder)
3. **Proper mode enforcement** during surgery recovery
4. **Easy mode switching** without manual Firestore edits
5. **Clear onboarding** for any new users

**Most importantly: The bot will actually fulfill its core mission - preventing the spirals it was designed to prevent!**

---

## Questions?

- Detailed analysis: `PRODUCT_REVIEW_PHASE1-2.md` (60+ issues)
- Quick summary: `PRODUCT_REVIEW_SUMMARY.md`
- This action plan: `CRITICAL_FIXES_ACTION_PLAN.md` (you are here)

**Ready to implement? Start with Fix #1 (9 PM reminder) - takes 1 hour and has the highest impact!**
