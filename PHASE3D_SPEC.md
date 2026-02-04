# Phase 3D: Career Tracking & Advanced Patterns - Technical Specification

**Version:** 1.0  
**Date:** February 5, 2026  
**Status:** Approved for Implementation  
**Estimated Implementation Time:** 5 days  
**Target Cost:** +$0.03/month (total: $1.46/month)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Feature 1: Career Goal Tracking](#feature-1-career-goal-tracking)
3. [Feature 2: Advanced Pattern Detection](#feature-2-advanced-pattern-detection)
4. [Implementation Plan](#implementation-plan)
5. [Testing Strategy](#testing-strategy)
6. [Deployment Plan](#deployment-plan)
7. [Success Criteria](#success-criteria)

---

## Executive Summary

### What Phase 3D Adds

Phase 3D transforms the accountability agent from general life tracking into a **career-focused achievement engine** with precision pattern detection:

1. **Career Goal Tracking** - Tier 1 expansion with skill building question + career mode system
2. **Advanced Pattern Detection (4 New Patterns)**:
   - Snooze Trap: Waking >30min late for 3+ days
   - Consumption Vortex: >3 hours daily consumption for 5+ days
   - Deep Work Collapse: <1.5 hours deep work for 5+ days  
   - Relationship Interference: Boundaries violated → sleep/training failures

### Why This Matters

**Current Gap (After Phase 3C):**
- ✅ Gamification drives retention with achievements
- ✅ Basic patterns detected (sleep degradation, training abandonment, porn relapse)
- ❌ **No career progress tracking** toward ₹28-42 LPA June 2026 goal
- ❌ **Missing subtle patterns** that predict spirals (snooze trap, consumption vortex)
- ❌ **No distinction between career phases** (skill building vs job searching)

**Phase 3D Solution:**
- ✅ Daily skill building tracking (LeetCode, system design progress)
- ✅ Career mode adaptation (3 modes: skill_building, job_searching, employed)
- ✅ 4 advanced patterns detect early warning signs before major failure
- ✅ Integration with constitution career goals (₹28-42 LPA by June 2026)

### Constitution Alignment

**From `constitution.md` Section III.B - Career & Professional Development:**

**Optimization Mode Goal:**
> "Secure ₹28-42 LPA role (Bangalore or Hyderabad), backend/AI-ML focused, by June 2026"

**Daily (2-3 hours/day):**
> - LeetCode: 2 problems (1 medium, 1 hard) - 60min  
> - System Design: Read/practice 1 topic - 30min  
> - AI/ML upskilling: LangChain/LangGraph projects - 60min

**Current Mode (Jan-Feb 2026):** Maintenance Mode until surgery recovery

**Phase 3D Enables:** Tracking whether user hits 2+ hours skill building daily, adapting to job search phase when ready.

---

### Success Metrics

**Functional:**
- ✅ Tier 1 expanded to 6 items (skill building added)
- ✅ Career mode toggle functional (3 modes)
- ✅ Adaptive career questions based on mode
- ✅ 4 new patterns detect correctly with <5% false positive rate
- ✅ Integration with existing pattern detection seamless

**Business:**
- ✅ 100% career mode adoption (mandatory for all users)
- ✅ Career tracking improves job search success (qualitative feedback)
- ✅ Advanced patterns reduce spiral incidents by 30%
- ✅ Early intervention (pattern → action within 24 hours)

**Technical:**
- ✅ Cost increase <$0.05/month for 10 users
- ✅ Pattern scan performance unchanged (<30s for 10 users)
- ✅ Database schema updated with skill_building field
- ✅ All tests passing (unit + integration)

---

## Feature 1: Career Goal Tracking

### Overview

**Problem:** User has specific career goals (₹28-42 LPA by June 2026, LeetCode mastery, system design skills) but system doesn't track daily progress toward these goals. Deep work tracking exists but isn't career-specific.

**Solution:** 
1. Extend Tier 1 from 5 items to 6 items (add skill building)
2. Implement career mode system with 3 modes
3. Adaptive question phrasing based on career phase
4. Integration with constitution career protocols

### Career Mode System

#### Career Mode Definitions

Phase 3D introduces 3 career modes matching constitution lifecycle:

| Mode | Description | Question Focus | Typical Duration |
|------|-------------|----------------|------------------|
| **skill_building** | Learning phase (LeetCode, system design, upskilling) | "Did you do 2+ hours skill building?" | 3-6 months |
| **job_searching** | Active job hunt (applications, interviews) | "Did you apply/interview OR skill build?" | 1-3 months |
| **employed** | In role, working toward promotion/raise | "Did you work toward promotion/raise?" | Ongoing |

**Constitution Mapping:**
- **Maintenance Mode** (current) → skill_building career mode
- **Optimization Mode** (post-surgery) → skill_building → job_searching
- **After job secured** → employed career mode

**User Journey Example:**
```
Jan-Apr 2026: Maintenance Mode + skill_building (surgery recovery, LeetCode)
  ↓
May-June 2026: Optimization Mode + skill_building (intense prep)
  ↓
July-Aug 2026: Optimization Mode + job_searching (5 apps/week, interviews)
  ↓
Sept 2026: Job secured at ₹32 LPA → employed mode
  ↓
Ongoing: employed mode (focus on performance, next promotion)
```

---

### Technical Design

#### 1. Database Schema Extension

**Already Exists in `User` Model (`src/models/schemas.py`):**

```python
class User(BaseModel):
    # ... existing fields ...
    career_mode: str = "skill_building"  # Already exists!
```

**No schema change needed.** The field exists but hasn't been used. We're now activating it.

---

#### 2. Tier 1 Expansion: Add Skill Building

**Current Tier 1 (Phase 1-3C): 5 Items**

```python
TIER_1_ITEMS = {
    "sleep": "💤 Sleep: 7+ hours?",
    "training": "💪 Training: Workout/rest?",
    "deep_work": "🧠 Deep Work: 2+ hours?",
    "zero_porn": "🚫 Zero Porn?",
    "boundaries": "🛡️ Boundaries: No toxic?"
}
```

**New Tier 1 (Phase 3D): 6 Items**

```python
TIER_1_ITEMS = {
    "sleep": "💤 Sleep: 7+ hours?",
    "training": "💪 Training: Workout/rest?",
    "deep_work": "🧠 Deep Work: 2+ hours?",
    "skill_building": "📚 Skill Building: 2+ hours?",  # NEW
    "zero_porn": "🚫 Zero Porn?",
    "boundaries": "🛡️ Boundaries: No toxic?"
}
```

**Rationale for Addition:**
1. **Constitution mandates it:** Section III.B specifies daily skill building (LeetCode, system design)
2. **Different from deep work:** Deep work = any focused work. Skill building = career-specific learning.
3. **June 2026 goal dependency:** Hitting ₹28-42 LPA requires daily skill building evidence

**Order Matters:** Skill building inserted between deep_work and zero_porn to group mental work together (sleep, training, deep_work, skill_building, zero_porn, boundaries).

---

#### 3. Adaptive Career Question

**File:** `src/bot/conversation.py`

**Current (Phase 1-3C):** Static question for deep work.

**New (Phase 3D):** Dynamic question for skill building based on career mode.

```python
def get_skill_building_question(user: User) -> dict:
    """
    Get skill building question based on user's career mode.
    
    Args:
        user: User profile
    
    Returns:
        {
            "question": str,
            "label": str,
            "description": str
        }
    """
    
    if user.career_mode == "skill_building":
        return {
            "question": "📚 **Skill Building**\n\nDid you do 2+ hours today?\n(LeetCode, system design, courses, projects)",
            "label": "📚 Skill Building: 2+ hours?",
            "description": "LeetCode, system design, AI/ML upskilling, courses, projects"
        }
    
    elif user.career_mode == "job_searching":
        return {
            "question": "💼 **Job Search Progress**\n\nDid you apply/interview OR do skill building today?\n(Applications, interviews, LeetCode, networking)",
            "label": "💼 Job Search: Progress made?",
            "description": "Job applications, interviews, skill building, networking"
        }
    
    elif user.career_mode == "employed":
        return {
            "question": "🎯 **Career Progress**\n\nDid you work toward promotion/raise today?\n(High-impact work, skill development, visibility projects)",
            "label": "🎯 Career: Toward promotion?",
            "description": "High-impact work, skill development, visibility projects, performance goals"
        }
    
    else:
        # Default fallback
        return {
            "question": "📚 **Skill Building**\n\nDid you do 2+ hours today?",
            "label": "📚 Skill Building: 2+ hours?",
            "description": "Career-focused learning and development"
        }
```

**Implementation in Check-In Flow:**

```python
# src/bot/conversation.py

async def tier1_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask Tier 1 non-negotiables with adaptive skill building question."""
    
    user_id = str(update.effective_user.id)
    user = firestore_service.get_user(user_id)
    
    # Get adaptive skill building question
    skill_q = get_skill_building_question(user)
    
    # Build Tier 1 question message
    message = (
        "📋 **Tier 1 Non-Negotiables**\n\n"
        "Answer Yes/No for each:\n\n"
        "1. 💤 Sleep: 7+ hours?\n"
        "2. 💪 Training: Workout or rest day?\n"
        "3. 🧠 Deep Work: 2+ hours focused work?\n"
        f"4. {skill_q['label']}\n"
        "5. 🚫 Zero Porn?\n"
        "6. 🛡️ Boundaries: No toxic interactions?\n\n"
        "Reply with 6 answers (e.g., 'Y Y N Y Y Y')"
    )
    
    await update.message.reply_text(message, parse_mode="Markdown")
```

**User Experience:**

```
User in skill_building mode:

Bot:
📋 Tier 1 Non-Negotiables

1. 💤 Sleep: 7+ hours?
2. 💪 Training: Workout or rest day?
3. 🧠 Deep Work: 2+ hours focused work?
4. 📚 Skill Building: 2+ hours? (LeetCode, system design, courses)
5. 🚫 Zero Porn?
6. 🛡️ Boundaries: No toxic interactions?

Reply with 6 answers (e.g., 'Y Y N Y Y Y')

---

User switches to job_searching mode:

Bot (next check-in):
📋 Tier 1 Non-Negotiables

1. 💤 Sleep: 7+ hours?
2. 💪 Training: Workout or rest day?
3. 🧠 Deep Work: 2+ hours focused work?
4. 💼 Job Search: Progress made? (Applications, interviews, networking)
5. 🚫 Zero Porn?
6. 🛡️ Boundaries: No toxic interactions?

Reply with 6 answers
```

**Note:** Question #4 adapts based on career mode. All other Tier 1 items remain constant.

---

#### 4. Career Mode Toggle Command

**File:** `src/bot/telegram_bot.py`

**Command:** `/career`

```python
async def career_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Display and toggle career mode.
    
    Usage: /career
    Shows current mode with inline buttons to switch.
    """
    user_id = str(update.effective_user.id)
    user = firestore_service.get_user(user_id)
    
    if not user:
        await update.message.reply_text("❌ User not found. Use /start first.")
        return
    
    # Current mode description
    mode_descriptions = {
        "skill_building": "📚 **Skill Building**\nLearning phase (LeetCode, system design, upskilling)",
        "job_searching": "💼 **Job Searching**\nActive job hunt (applications, interviews)",
        "employed": "🎯 **Employed**\nWorking toward promotion/raise"
    }
    
    current_desc = mode_descriptions.get(user.career_mode, "Unknown mode")
    
    message = (
        f"**Current Career Mode:**\n{current_desc}\n\n"
        "This determines your Tier 1 skill building question.\n\n"
        "Select new mode:"
    )
    
    # Inline keyboard for mode selection
    keyboard = [
        [InlineKeyboardButton("📚 Skill Building", callback_data="career_skill")],
        [InlineKeyboardButton("💼 Job Searching", callback_data="career_job")],
        [InlineKeyboardButton("🎯 Employed", callback_data="career_employed")]
    ]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )


async def career_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle career mode selection from inline buttons."""
    
    query = update.callback_query
    await query.answer()
    
    user_id = str(query.from_user.id)
    callback_data = query.data
    
    # Map callback data to career mode
    mode_map = {
        "career_skill": "skill_building",
        "career_job": "job_searching",
        "career_employed": "employed"
    }
    
    new_mode = mode_map.get(callback_data)
    
    if not new_mode:
        await query.edit_message_text("❌ Invalid selection.")
        return
    
    # Update career mode in Firestore
    firestore_service.update_user(user_id, {"career_mode": new_mode})
    
    # Confirmation message
    mode_names = {
        "skill_building": "📚 Skill Building",
        "job_searching": "💼 Job Searching",
        "employed": "🎯 Employed"
    }
    
    await query.edit_message_text(
        f"✅ Career mode updated to: **{mode_names[new_mode]}**\n\n"
        "Your Tier 1 questions will adapt starting next check-in.",
        parse_mode="Markdown"
    )
```

**User Experience:**

```
User: /career

Bot:
Current Career Mode:
📚 Skill Building
Learning phase (LeetCode, system design, upskilling)

This determines your Tier 1 skill building question.

Select new mode:
[📚 Skill Building] [💼 Job Searching] [🎯 Employed]

User clicks: [💼 Job Searching]

Bot:
✅ Career mode updated to: 💼 Job Searching

Your Tier 1 questions will adapt starting next check-in.
```

**Integration:** Career mode is read during each check-in to determine question phrasing.

---

#### 5. Onboarding Flow Enhancement

**File:** `src/bot/telegram_bot.py` (start command)

**Addition:** During onboarding, ask user to select career mode.

```python
async def onboarding_career_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ask user to select career mode during onboarding."""
    
    message = (
        "🎯 **Career Phase**\n\n"
        "What's your current career focus?\n\n"
        "📚 **Skill Building** - Learning phase (LeetCode, system design)\n"
        "💼 **Job Searching** - Active job hunt\n"
        "🎯 **Employed** - Working toward promotion/raise"
    )
    
    keyboard = [
        [InlineKeyboardButton("📚 Skill Building", callback_data="onboard_career_skill")],
        [InlineKeyboardButton("💼 Job Searching", callback_data="onboard_career_job")],
        [InlineKeyboardButton("🎯 Employed", callback_data="onboard_career_employed")]
    ]
    
    await update.message.reply_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="Markdown"
    )
```

**Integration Point:** Add between mode selection and timezone confirmation in onboarding flow.

**Result:** All new users have career mode set explicitly during signup.

---

#### 6. Data Model for Skill Building

**File:** `src/models/schemas.py`

**New Model:** Skill building data structure to match other Tier 1 items.

```python
class SkillBuildingData(BaseModel):
    """
    Skill building tracking (Tier 1 item).
    
    Tracks:
    - Whether skill building completed (Y/N)
    - Hours spent (optional, for detailed tracking)
    - Activity type (optional: LeetCode, System Design, etc.)
    """
    completed: bool
    hours: Optional[float] = None
    activity: Optional[str] = None  # "LeetCode", "System Design", "Courses", "Projects"
```

**Integration with Tier1NonNegotiables:**

```python
class Tier1NonNegotiables(BaseModel):
    """Tier 1 non-negotiables (daily requirements)."""
    
    sleep: SleepData
    training: TrainingData
    deep_work: DeepWorkData
    skill_building: SkillBuildingData  # NEW
    zero_porn: CompletionData
    boundaries: CompletionData
```

**Compliance Calculation Update:**

```python
# src/utils/compliance.py

def calculate_compliance_score(tier1: Tier1NonNegotiables) -> float:
    """
    Calculate compliance score based on Tier 1 completion.
    
    Phase 1-3C: 5 items → each worth 20%
    Phase 3D: 6 items → each worth 16.67%
    """
    items = [
        tier1.sleep.completed,
        tier1.training.completed,
        tier1.deep_work.completed,
        tier1.skill_building.completed,  # NEW
        tier1.zero_porn.completed,
        tier1.boundaries.completed
    ]
    
    completed_count = sum(items)
    total_items = len(items)  # 6
    
    return (completed_count / total_items) * 100
```

**Impact:** 
- **Before Phase 3D:** Each Tier 1 item = 20% (5 items)
- **After Phase 3D:** Each Tier 1 item = 16.67% (6 items)
- **100% compliance:** All 6 items completed

---

#### 7. Constitution Integration

**Career Goal Tracking (Future Enhancement):**

While Phase 3D adds skill building tracking, **future phases** can add:
- LeetCode problem counter (API integration)
- Job application tracker (manual entry or API)
- Salary progress toward ₹28-42 LPA goal
- Monthly review of career trajectory

**Phase 3D Foundation:** Establishes career mode system and daily skill building tracking. Future features build on this.

**Alignment with Constitution Section III.B:**

| Constitution Requirement | Phase 3D Implementation |
|--------------------------|-------------------------|
| "LeetCode: 2 problems (1 medium, 1 hard) - 60min" | Skill building question asks "2+ hours?" |
| "System Design: Read/practice 1 topic - 30min" | Covered in skill building umbrella |
| "Apply to 5+ jobs (weekly)" | Job searching mode question adapts |
| "Career mode: skill_building | job_searching | employed" | Implemented as career mode system |

**Result:** Daily tracking aligns with constitution requirements, enables AI to hold user accountable to career goals.

---

## Feature 2: Advanced Pattern Detection

### Overview

**Problem:** Current pattern detection (sleep degradation, training abandonment, porn relapse, compliance decline, ghosting) catches major failures but **misses subtle early-warning patterns** that predict spirals.

**Solution:** Add 4 advanced patterns based on constitution interrupt patterns:

1. **Snooze Trap** - Waking >30min late for 3+ days → rushed mornings → deep work failure
2. **Consumption Vortex** - >3 hours daily consumption for 5+ days → creator → consumer shift
3. **Deep Work Collapse** - <1.5 hours deep work for 5+ days → career progress stalls
4. **Relationship Interference** - Boundary violations correlate with sleep/training failures

**Constitution Basis:** Section G (Interrupt Patterns) explicitly calls out these patterns.

---

### Pattern 6: Snooze Trap

#### Constitution Reference

From `constitution.md` Section G - Interrupt Pattern 2:

> **The Snooze Trap**
> 
> **Trigger Detection:**
> - Alarm goes off
> - "Just 10 more minutes" thought
> - "I deserve more sleep" rationalization
> 
> **Consequence Protocol:**
> - Each snooze = 15min earlier bedtime that night (forced sleep debt repayment)
> - 3 snoozes in a week = Maintenance Mode warning (system breaking down)

**Expanded for Phase 3D:** Track wake time vs target, detect sustained snooze pattern.

---

#### Technical Design

**Detection Logic:**

```python
# src/agents/pattern_detection.py

def detect_snooze_trap(self, user_id: str) -> Optional[Pattern]:
    """
    Detect snooze trap pattern.
    
    Algorithm:
    1. Get user's target wake time (from profile or constitution default: 6:30 AM)
    2. Get recent check-ins (last 7 days)
    3. Extract actual wake time from check-in metadata (if tracked)
    4. Calculate snooze duration: actual_wake - target_wake
    5. If >30min snooze for 3+ consecutive days → flag pattern
    
    Args:
        user_id: User ID
    
    Returns:
        Pattern object if detected, None otherwise
    """
    try:
        user = firestore_service.get_user(user_id)
        recent_checkins = firestore_service.get_recent_checkins(user_id, days=7)
        
        # Get target wake time (default: 6:30 AM from constitution)
        target_wake_time = user.settings.get("target_wake_time", "06:30")
        
        # Track snooze days
        snooze_days = []
        total_snooze_minutes = 0
        
        for checkin in recent_checkins[-3:]:  # Last 3 days
            # Check if wake time was tracked
            wake_time = checkin.metadata.get("wake_time")
            
            if not wake_time:
                # Wake time not tracked, can't detect pattern
                continue
            
            # Calculate snooze duration
            snooze_minutes = self._calculate_snooze_duration(
                target_wake_time, 
                wake_time
            )
            
            if snooze_minutes > 30:
                snooze_days.append({
                    "date": checkin.date,
                    "snooze_minutes": snooze_minutes,
                    "wake_time": wake_time
                })
                total_snooze_minutes += snooze_minutes
        
        # Trigger if 3+ consecutive days with >30min snooze
        if len(snooze_days) >= 3:
            avg_snooze = total_snooze_minutes / len(snooze_days)
            
            return Pattern(
                type="snooze_trap",
                severity="warning",
                detected_at=datetime.utcnow(),
                data={
                    "days_affected": [d["date"] for d in snooze_days],
                    "avg_snooze_minutes": int(avg_snooze),
                    "worst_day": max(snooze_days, key=lambda x: x["snooze_minutes"]),
                    "target_wake": target_wake_time
                },
                resolved=False
            )
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error detecting snooze trap: {e}")
        return None


def _calculate_snooze_duration(self, target: str, actual: str) -> int:
    """
    Calculate snooze duration in minutes.
    
    Args:
        target: Target wake time (HH:MM format, e.g., "06:30")
        actual: Actual wake time (HH:MM format, e.g., "07:15")
    
    Returns:
        Snooze duration in minutes (positive if late, negative if early)
    """
    from datetime import datetime
    
    target_time = datetime.strptime(target, "%H:%M")
    actual_time = datetime.strptime(actual, "%H:%M")
    
    diff = actual_time - target_time
    return int(diff.total_seconds() / 60)
```

**Data Requirement:** Wake time tracking.

**Implementation Options:**

1. **Option A (Simple):** Ask during check-in: "What time did you wake up today?"
2. **Option B (Automated):** Integrate with alarm app or phone sensors (complex)
3. **Option C (Estimated):** Infer from check-in time (e.g., late check-in at 8 AM → likely woke late)

**Phase 3D Decision:** Use **Option A** (simple) - add optional wake time question.

**Check-In Flow Addition:**

```python
# After Tier 1 questions, before Q2:

async def ask_wake_time(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Optional: Ask wake time for snooze trap detection."""
    
    message = (
        "⏰ **Optional: What time did you wake up today?**\n\n"
        "Format: HH:MM (e.g., 06:45)\n\n"
        "This helps detect snooze trap patterns.\n"
        "Skip by typing 'skip'"
    )
    
    await update.message.reply_text(message)
    
    return WAKE_TIME_STATE
```

**Storage:** Store in `checkin.metadata["wake_time"]`.

---

#### Intervention Message

**File:** `src/agents/intervention.py`

```python
def _build_snooze_trap_intervention(self, pattern: Pattern) -> str:
    """Build intervention message for snooze trap pattern."""
    
    days = len(pattern.data["days_affected"])
    avg_snooze = pattern.data["avg_snooze_minutes"]
    target_wake = pattern.data["target_wake"]
    
    message = (
        f"⚠️ **SNOOZE TRAP DETECTED**\n\n"
        f"You've snoozed for {avg_snooze}+ minutes for {days} straight days.\n\n"
        f"**This pattern leads to:**\n"
        f"• Rushed mornings\n"
        f"• Missed deep work sessions\n"
        f"• Compliance decline\n"
        f"• Energy drain throughout day\n\n"
        f"**Constitution Protocol:**\n"
        f"1. Move alarm across room (tonight)\n"
        f"2. Sleep 30min earlier (target: 10:30 PM)\n"
        f"3. No snooze button - stand up immediately\n"
        f"4. Morning routine: Bathroom → Water → Light\n\n"
        f"Your June 2026 goal depends on morning execution.\n"
        f"Target wake time: {target_wake}. Tomorrow: no snooze."
    )
    
    return message
```

**User Experience:**

```
User snoozes 3 days in a row (45min, 50min, 60min):

Bot (intervention message):
⚠️ SNOOZE TRAP DETECTED

You've snoozed for 51+ minutes for 3 straight days.

This pattern leads to:
• Rushed mornings
• Missed deep work sessions
• Compliance decline
• Energy drain throughout day

Constitution Protocol:
1. Move alarm across room (tonight)
2. Sleep 30min earlier (target: 10:30 PM)
3. No snooze button - stand up immediately
4. Morning routine: Bathroom → Water → Light

Your June 2026 goal depends on morning execution.
Target wake time: 06:30. Tomorrow: no snooze.
```

**Historical Context:** Constitution references Feb 2025 pattern (snooze → late start → missed study → job search stall).

---

### Pattern 7: Consumption Vortex

#### Constitution Reference

From `constitution.md` Section G - Interrupt Pattern 3:

> **The Consumption Vortex**
> 
> **Trigger Detection:**
> - Opening YouTube/Reddit/Twitter without specific purpose
> - "Just gonna check for 5min" thought
> - Bored/procrastinating on task
> - Daydreaming about being successful instead of working toward it
> 
> **AI Intervention:**
> - Screen time tracking (AI reviews weekly)
> - If consumption >2hrs/day (excluding work) → AI flags in weekly review
> - "You spent 12hrs on YouTube this week. What are you avoiding?"

**Expanded for Phase 3D:** Track consumption hours, detect >3 hours/day for 5+ days.

---

#### Technical Design

**Detection Logic:**

```python
def detect_consumption_vortex(self, user_id: str) -> Optional[Pattern]:
    """
    Detect excessive consumption pattern.
    
    Algorithm:
    1. Get recent check-ins (last 7 days)
    2. Extract consumption hours from responses (if tracked)
    3. Count days with >3 hours consumption
    4. If ≥5 days in week → flag pattern
    
    Args:
        user_id: User ID
    
    Returns:
        Pattern object if detected, None otherwise
    """
    try:
        recent_checkins = firestore_service.get_recent_checkins(user_id, days=7)
        
        high_consumption_days = []
        total_consumption_hours = 0
        
        for checkin in recent_checkins:
            # Check if consumption hours tracked
            consumption_hours = checkin.responses.get("consumption_hours")
            
            if consumption_hours is None:
                # Not tracked for this day, skip
                continue
            
            if consumption_hours > 3:
                high_consumption_days.append({
                    "date": checkin.date,
                    "hours": consumption_hours
                })
                total_consumption_hours += consumption_hours
        
        # Trigger if 5+ days with >3 hours
        if len(high_consumption_days) >= 5:
            avg_consumption = total_consumption_hours / len(high_consumption_days)
            worst_day = max(high_consumption_days, key=lambda x: x["hours"])
            
            return Pattern(
                type="consumption_vortex",
                severity="warning",
                detected_at=datetime.utcnow(),
                data={
                    "days_affected": len(high_consumption_days),
                    "avg_consumption_hours": round(avg_consumption, 1),
                    "worst_day": worst_day,
                    "total_weekly_hours": total_consumption_hours
                },
                resolved=False
            )
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error detecting consumption vortex: {e}")
        return None
```

**Data Requirement:** Consumption hours tracking.

**Check-In Flow Addition:**

```python
# After Q4 (tomorrow's priority), add optional question:

async def ask_consumption_hours(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Optional: Ask daily consumption hours."""
    
    message = (
        "📱 **Optional: Screen time tracking**\n\n"
        "How many hours did you spend on consumption today?\n"
        "(YouTube, Reddit, Twitter, gaming, etc.)\n\n"
        "Be honest - this helps detect consumption vortex.\n"
        "Format: Number (e.g., 2.5) or skip"
    )
    
    await update.message.reply_text(message)
    
    return CONSUMPTION_STATE
```

**Storage:** Store in `checkin.responses["consumption_hours"]`.

---

#### Intervention Message

```python
def _build_consumption_vortex_intervention(self, pattern: Pattern) -> str:
    """Build intervention message for consumption vortex pattern."""
    
    days = pattern.data["days_affected"]
    avg_hours = pattern.data["avg_consumption_hours"]
    total_hours = pattern.data["total_weekly_hours"]
    
    message = (
        f"⚠️ **CONSUMPTION VORTEX DETECTED**\n\n"
        f"You've averaged {avg_hours} hours of consumption for {days} days.\n"
        f"Total this week: {total_hours} hours.\n\n"
        f"**You're becoming a consumer, not a creator.**\n\n"
        f"**Constitution Violation:**\n"
        f"• Principle 2: \"Create Don't Consume\"\n"
        f"• Your time is irreplaceable\n"
        f"• {total_hours} hours = {int(total_hours * 60)} minutes of life\n\n"
        f"**Actions NOW:**\n"
        f"1. Install blockers (Freedom app, Cold Turkey)\n"
        f"2. Delete time-sink apps from phone\n"
        f"3. Schedule creation time (morning 2-hour block)\n"
        f"4. Track consumption daily (accountability)\n\n"
        f"**Historical Pattern:**\n"
        f"Jan 2025: Consumption vortex → job search stall → opportunity lost\n\n"
        f"Your ₹28 LPA goal requires creation, not consumption.\n"
        f"Tomorrow: <2 hours consumption. No exceptions."
    )
    
    return message
```

**User Experience:**

```
User logs 4-5 hours daily consumption for 5 days:

Bot:
⚠️ CONSUMPTION VORTEX DETECTED

You've averaged 4.2 hours of consumption for 5 days.
Total this week: 21 hours.

You're becoming a consumer, not a creator.

Constitution Violation:
• Principle 2: "Create Don't Consume"
• Your time is irreplaceable
• 21 hours = 1260 minutes of life

Actions NOW:
1. Install blockers (Freedom app, Cold Turkey)
2. Delete time-sink apps from phone
3. Schedule creation time (morning 2-hour block)
4. Track consumption daily (accountability)

Historical Pattern:
Jan 2025: Consumption vortex → job search stall → opportunity lost

Your ₹28 LPA goal requires creation, not consumption.
Tomorrow: <2 hours consumption. No exceptions.
```

**Severity:** Warning (not critical) because consumption doesn't immediately break constitution, but it's a leading indicator of deeper issues.

---

### Pattern 8: Deep Work Collapse

#### Constitution Reference

From `constitution.md` Section III.C - Daily AI Check-In:

> **AI asks:**
> 3. "Did you complete your Tier 1 non-negotiables today?" [Y/N for each: ... **2+ hours focused work/study**, ...]

Constitution mandates 2+ hours deep work daily. Falling below 1.5 hours for sustained period indicates collapse.

---

#### Technical Design

**Detection Logic:**

```python
def detect_deep_work_collapse(self, user_id: str) -> Optional[Pattern]:
    """
    Detect sustained deep work decline.
    
    Algorithm:
    1. Get recent check-ins (last 7 days)
    2. Extract deep work hours from Tier 1
    3. Count days with <1.5 hours
    4. If ≥5 days → flag as critical pattern
    
    Target: 2+ hours (constitution)
    Warning threshold: <1.5 hours (75% of target)
    
    Args:
        user_id: User ID
    
    Returns:
        Pattern object if detected, None otherwise
    """
    try:
        recent_checkins = firestore_service.get_recent_checkins(user_id, days=7)
        
        low_deep_work_days = []
        total_deep_work_hours = 0
        
        for checkin in recent_checkins:
            deep_work_hours = checkin.tier1.deep_work.get("hours", 0)
            
            if deep_work_hours < 1.5:
                low_deep_work_days.append({
                    "date": checkin.date,
                    "hours": deep_work_hours
                })
            
            total_deep_work_hours += deep_work_hours
        
        # Trigger if 5+ days below threshold
        if len(low_deep_work_days) >= 5:
            avg_hours = total_deep_work_hours / len(recent_checkins) if recent_checkins else 0
            
            return Pattern(
                type="deep_work_collapse",
                severity="critical",  # Critical because impacts career goal directly
                detected_at=datetime.utcnow(),
                data={
                    "days_affected": len(low_deep_work_days),
                    "avg_deep_work_hours": round(avg_hours, 1),
                    "target": 2.0,
                    "dates": [d["date"] for d in low_deep_work_days]
                },
                resolved=False
            )
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error detecting deep work collapse: {e}")
        return None
```

**Data Source:** Existing! `checkin.tier1.deep_work.hours` is already tracked from Phase 1.

**No new data collection needed.**

---

#### Intervention Message

```python
def _build_deep_work_collapse_intervention(self, pattern: Pattern) -> str:
    """Build intervention message for deep work collapse pattern."""
    
    days = pattern.data["days_affected"]
    avg_hours = pattern.data["avg_deep_work_hours"]
    target = pattern.data["target"]
    
    message = (
        f"🚨 **DEEP WORK COLLAPSE**\n\n"
        f"You've averaged {avg_hours} hours deep work for {days} days.\n"
        f"Constitution target: {target}+ hours.\n\n"
        f"**This is how you miss June 2026 career goals.**\n\n"
        f"**Historical Pattern:**\n"
        f"• Jan 2025: Deep work collapse → no job offers\n"
        f"• Recovery took 3 months\n"
        f"• You've seen this movie before\n\n"
        f"**Root Cause Analysis:**\n"
        f"What's blocking deep work?\n"
        f"• Meetings eating your calendar?\n"
        f"• Distractions (phone, notifications)?\n"
        f"• Energy/motivation low?\n"
        f"• Avoiding difficult tasks?\n\n"
        f"**Actions NOW:**\n"
        f"1. Block calendar: 2-hour morning slot (6:30-8:30 AM)\n"
        f"2. Phone on airplane mode during deep work\n"
        f"3. Track specific output (LeetCode problems solved)\n"
        f"4. Identify #1 distraction → remove it\n\n"
        f"**Tomorrow's Deep Work:**\n"
        f"2+ hours, no excuses. Your ₹28 LPA goal depends on it.\n"
        f"If you don't fix this by Friday → Maintenance Mode warning."
    )
    
    return message
```

**Severity Rationale:** CRITICAL (not just warning) because:
1. Directly impacts career goal (₹28-42 LPA by June 2026)
2. Historical evidence of 3-month spiral (Jan 2025)
3. Constitution explicitly mandates 2+ hours

**User Experience:**

```
User has 5 days with <1.5 hours deep work:

Bot:
🚨 DEEP WORK COLLAPSE

You've averaged 1.2 hours deep work for 5 days.
Constitution target: 2+ hours.

This is how you miss June 2026 career goals.

Historical Pattern:
• Jan 2025: Deep work collapse → no job offers
• Recovery took 3 months
• You've seen this movie before

Root Cause Analysis:
What's blocking deep work?
• Meetings eating your calendar?
• Distractions (phone, notifications)?
• Energy/motivation low?
• Avoiding difficult tasks?

Actions NOW:
1. Block calendar: 2-hour morning slot (6:30-8:30 AM)
2. Phone on airplane mode during deep work
3. Track specific output (LeetCode problems solved)
4. Identify #1 distraction → remove it

Tomorrow's Deep Work:
2+ hours, no excuses. Your ₹28 LPA goal depends on it.
If you don't fix this by Friday → Maintenance Mode warning.
```

**Escalation:** If pattern continues for 7+ days → suggest switching to Survival Mode (system failure).

---

### Pattern 9: Relationship Interference

#### Constitution Reference

From `constitution.md` Section G - Interrupt Pattern 4:

> **The Boundary Violation (Relationship)**
> 
> **Trigger Detection:**
> - Call/text during scheduled study/work/sleep time
> - Partner wants 1+ hour of time when you have priorities
> - "But she'll be upset if I don't" thought
> 
> **AI Intervention:**
> - Daily check-in asks: "Did you sacrifice sleep/study/training time for relationship today?"
> - If yes → "Was it worth it? Or pattern repeating?"
> - 3 sacrifices in a week = AI flags: "Warning: Relationship boundary pattern from toxic relationship recurring"

From `constitution.md` Principle 5:

> **Fear of Loss is Not a Reason to Stay**
> 
> "I do not tolerate toxic relationships, jobs, or situations out of fear of losing them."

**Expanded for Phase 3D:** Detect correlation between boundary violations and sleep/training failures.

---

#### Technical Design

**Detection Logic:**

```python
def detect_relationship_interference(self, user_id: str) -> Optional[Pattern]:
    """
    Detect relationships disrupting sleep/training.
    
    Algorithm:
    1. Get recent check-ins (last 7 days)
    2. Identify days where:
       - Boundaries = No (Tier 1 violation)
       - AND (sleep <7hrs OR training = No)
    3. Calculate correlation: interference_days / total_days
    4. If correlation >70% → flag pattern
    
    This detects: Boundary violations → constitution failures
    
    Args:
        user_id: User ID
    
    Returns:
        Pattern object if detected, None otherwise
    """
    try:
        recent_checkins = firestore_service.get_recent_checkins(user_id, days=7)
        
        if len(recent_checkins) < 5:
            # Need at least 5 days of data for correlation
            return None
        
        interference_days = []
        
        for checkin in recent_checkins:
            # Check if boundaries violated
            boundaries_violated = not checkin.tier1.boundaries.completed
            
            # Check if sleep or training failed
            sleep_failed = checkin.tier1.sleep.hours < 7
            training_failed = not checkin.tier1.training.completed
            
            # Interference = boundaries violated AND (sleep failed OR training failed)
            if boundaries_violated and (sleep_failed or training_failed):
                interference_days.append({
                    "date": checkin.date,
                    "sleep_hours": checkin.tier1.sleep.hours,
                    "training_completed": checkin.tier1.training.completed,
                    "boundaries_violated": True
                })
        
        # Calculate correlation
        correlation = len(interference_days) / len(recent_checkins)
        
        # Trigger if >70% correlation
        if correlation > 0.7:
            return Pattern(
                type="relationship_interference",
                severity="critical",  # Critical due to historical toxic relationship pattern
                detected_at=datetime.utcnow(),
                data={
                    "days_affected": len(interference_days),
                    "correlation_pct": int(correlation * 100),
                    "total_days_analyzed": len(recent_checkins),
                    "details": interference_days
                },
                resolved=False
            )
        
        return None
        
    except Exception as e:
        logger.error(f"❌ Error detecting relationship interference: {e}")
        return None
```

**Correlation Threshold:** 70% chosen because:
- 5/7 days = 71% → clear pattern
- Random coincidence unlikely at >70%
- Constitution history shows this was consistent pattern in toxic relationship

---

#### Intervention Message

```python
def _build_relationship_interference_intervention(self, pattern: Pattern) -> str:
    """Build intervention message for relationship interference pattern."""
    
    days = pattern.data["days_affected"]
    correlation = pattern.data["correlation_pct"]
    total = pattern.data["total_days_analyzed"]
    
    message = (
        f"🚨 **RELATIONSHIP INTERFERENCE PATTERN DETECTED**\n\n"
        f"{days}/{total} days: Boundary violations → Sleep/Training failures\n"
        f"Correlation: {correlation}% (threshold: 70%)\n\n"
        f"**This is the EXACT pattern from your toxic relationship (Feb 2025).**\n\n"
        f"**Constitution Principle 5:**\n"
        f"\"Fear of loss is not a reason to stay.\"\n\n"
        f"**Historical Consequences:**\n"
        f"• Feb-July 2025: 6-month regression\n"
        f"• Sacrificed sleep for 1-1.5hr calls about partying\n"
        f"• Missed workouts due to exhaustion\n"
        f"• Job search stalled → opportunity lost\n"
        f"• Ended in breakup anyway\n\n"
        f"**Critical Questions:**\n"
        f"1. Are you sacrificing constitution for this person?\n"
        f"2. Do they respect your boundaries when you set them?\n"
        f"3. Are you afraid to enforce boundaries? (RED FLAG)\n"
        f"4. Is this relationship making you better or worse?\n\n"
        f"**Actions NOW:**\n"
        f"1. Set boundary TODAY: \"I need sleep/training time\"\n"
        f"2. Observe reaction: Supportive? Or guilt-trip?\n"
        f"3. If guilt-trip → Relationship audit required\n"
        f"4. If pattern continues 3 more days → Serious conversation\n\n"
        f"**This is your system telling you something is wrong.**\n"
        f"Listen to it. Your future self will thank you."
    )
    
    return message
```

**Severity Rationale:** CRITICAL because:
1. Historical evidence of 6-month spiral (Feb-July 2025)
2. Constitution Principle 5 violation (fear of loss)
3. Impacts multiple domains (sleep, training, likely career too)
4. Toxic relationship pattern can destroy years of progress

**User Experience:**

```
User violates boundaries 5/7 days, each day also misses sleep or training:

Bot:
🚨 RELATIONSHIP INTERFERENCE PATTERN DETECTED

5/7 days: Boundary violations → Sleep/Training failures
Correlation: 71% (threshold: 70%)

This is the EXACT pattern from your toxic relationship (Feb 2025).

Constitution Principle 5:
"Fear of loss is not a reason to stay."

Historical Consequences:
• Feb-July 2025: 6-month regression
• Sacrificed sleep for 1-1.5hr calls about partying
• Missed workouts due to exhaustion
• Job search stalled → opportunity lost
• Ended in breakup anyway

Critical Questions:
1. Are you sacrificing constitution for this person?
2. Do they respect your boundaries when you set them?
3. Are you afraid to enforce boundaries? (RED FLAG)
4. Is this relationship making you better or worse?

Actions NOW:
1. Set boundary TODAY: "I need sleep/training time"
2. Observe reaction: Supportive? Or guilt-trip?
3. If guilt-trip → Relationship audit required
4. If pattern continues 3 more days → Serious conversation

This is your system telling you something is wrong.
Listen to it. Your future self will thank you.
```

**Note:** Message is firm and direct because constitution explicitly mandates this. User's historical pattern shows this is serious.

---

### Pattern Detection Summary

**Total Patterns After Phase 3D:** 9 patterns

**Original (Phase 2):** 5 patterns
1. Sleep Degradation
2. Training Abandonment
3. Porn Relapse
4. Compliance Decline
5. Ghosting (Phase 3B)

**New (Phase 3D):** 4 patterns
6. Snooze Trap
7. Consumption Vortex
8. Deep Work Collapse
9. Relationship Interference

**Architecture Integration:**

All patterns use the same detection framework:
- Detected by `PatternDetectionAgent`
- Interventions built by `InterventionAgent`
- Logged in Firestore `patterns/` collection
- Scanned every 6 hours by Cloud Scheduler

**No architectural changes needed** - we're just adding more pattern detection functions to existing system.

---

## Implementation Plan

### Day 1: Career Mode System

**Tasks:**
1. Activate `career_mode` field in User model (verify it exists)
2. Implement `get_skill_building_question()` function
3. Add career mode to onboarding flow
4. Create `/career` command with inline buttons
5. Test career mode toggle end-to-end

**Deliverables:**
- ✅ Career mode toggle functional
- ✅ Onboarding includes career mode selection
- ✅ `/career` command shows current mode and allows switching
- ✅ Unit tests for career mode functions

**Testing:**
```python
def test_career_mode_toggle():
    user = create_user(career_mode="skill_building")
    update_career_mode(user.user_id, "job_searching")
    user_updated = get_user(user.user_id)
    assert user_updated.career_mode == "job_searching"
```

---

### Day 2: Tier 1 Expansion

**Tasks:**
1. Add `SkillBuildingData` model to schemas.py
2. Update `Tier1NonNegotiables` to include skill_building
3. Modify check-in flow to ask skill building question
4. Update compliance calculation (6 items instead of 5)
5. Test Tier 1 with 6 items end-to-end
6. Update database migration (add skill_building field to existing check-ins)

**Deliverables:**
- ✅ Tier 1 has 6 items
- ✅ Skill building question adapts to career mode
- ✅ Compliance calculation updated (16.67% per item)
- ✅ Check-in flow functional with new item

**Migration Script:**
```python
# scripts/add_skill_building_to_tier1.py
"""Add skill_building field to existing check-ins."""

async def migrate_tier1():
    """Add skill_building: {completed: False} to all existing check-ins."""
    
    all_users = firestore_service.get_all_users()
    
    for user in all_users:
        checkins = firestore_service.get_all_checkins(user.user_id)
        
        for checkin in checkins:
            # Add skill_building if missing
            if not hasattr(checkin.tier1, 'skill_building'):
                checkin.tier1.skill_building = SkillBuildingData(completed=False)
                firestore_service.update_checkin(user.user_id, checkin)
        
        print(f"✅ Migrated {len(checkins)} check-ins for user {user.user_id}")
```

---

### Day 3: Advanced Pattern Detection (Part 1)

**Tasks:**
1. Implement `detect_snooze_trap()` in pattern_detection.py
2. Implement `detect_consumption_vortex()` in pattern_detection.py
3. Add wake time optional question to check-in flow
4. Add consumption hours optional question
5. Build intervention messages for both patterns
6. Unit test both detection functions

**Deliverables:**
- ✅ Snooze trap detection functional
- ✅ Consumption vortex detection functional
- ✅ Optional questions added to check-in
- ✅ Intervention messages written
- ✅ Unit tests passing (10+ tests)

**Testing:**
```python
def test_snooze_trap_detection():
    user = create_user()
    checkins = [
        create_checkin(wake_time="07:00", target="06:30"),  # 30min snooze
        create_checkin(wake_time="07:15", target="06:30"),  # 45min snooze
        create_checkin(wake_time="07:30", target="06:30"),  # 60min snooze
    ]
    
    pattern = pattern_detection.detect_snooze_trap(user.user_id, checkins)
    assert pattern is not None
    assert pattern.type == "snooze_trap"
    assert pattern.severity == "warning"
```

---

### Day 4: Advanced Pattern Detection (Part 2)

**Tasks:**
1. Implement `detect_deep_work_collapse()` in pattern_detection.py
2. Implement `detect_relationship_interference()` in pattern_detection.py
3. Build intervention messages for both patterns
4. Integrate all 4 new patterns with pattern scan
5. Unit test both detection functions
6. Integration test all 9 patterns together

**Deliverables:**
- ✅ Deep work collapse detection functional (uses existing data!)
- ✅ Relationship interference detection functional
- ✅ All 4 patterns integrated with scan
- ✅ Pattern scan runs all 9 patterns correctly
- ✅ Unit + integration tests passing

**Testing:**
```python
async def test_pattern_scan_all_9_patterns():
    """Test that pattern scan checks all patterns including new ones."""
    
    user_id = create_test_user()
    create_pattern_triggers(user_id)  # Setup data to trigger each pattern
    
    # Run pattern scan
    patterns = await pattern_detection_agent.scan_patterns(user_id)
    
    # Verify all patterns checked (should detect some)
    assert len(patterns) > 0
    
    # Verify new patterns present
    pattern_types = [p.type for p in patterns]
    assert "deep_work_collapse" in pattern_types or "snooze_trap" in pattern_types
```

---

### Day 5: Integration Testing & Polish

**Tasks:**
1. Full end-to-end testing with career mode + patterns
2. Test career mode switch during check-in
3. Test all 4 new patterns triggering interventions
4. Performance testing (pattern scan with 4 new patterns)
5. Edge case testing (missing wake time, missing consumption hours)
6. Documentation update
7. Bug fixes

**Deliverables:**
- ✅ All features tested end-to-end
- ✅ Performance acceptable (pattern scan <30s for 10 users)
- ✅ Edge cases handled gracefully
- ✅ Documentation complete (PHASE3D_SPEC.md, code comments)

**Integration Test:**
```python
async def test_career_mode_with_patterns():
    """Test career mode and pattern detection working together."""
    
    user_id = create_test_user(career_mode="skill_building")
    
    # Complete check-in in skill_building mode
    await checkin_agent.complete_checkin(user_id, sample_data())
    
    # Verify skill building question asked correctly
    # Verify compliance calculated with 6 items
    
    # Trigger deep work collapse pattern
    create_low_deep_work_checkins(user_id, days=5)
    await pattern_scan()
    
    # Verify pattern detected and intervention sent
    patterns = firestore_service.get_patterns(user_id)
    assert any(p.type == "deep_work_collapse" for p in patterns)
```

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_career_mode.py`

```python
import pytest
from src.bot.conversation import get_skill_building_question
from src.models.schemas import User

def test_skill_building_question_skill_mode():
    """Test skill building question in skill_building mode."""
    user = create_user(career_mode="skill_building")
    question = get_skill_building_question(user)
    
    assert "Skill Building" in question["question"]
    assert "LeetCode" in question["description"]

def test_skill_building_question_job_mode():
    """Test skill building question in job_searching mode."""
    user = create_user(career_mode="job_searching")
    question = get_skill_building_question(user)
    
    assert "Job Search" in question["question"]
    assert "Applications" in question["description"]

def test_skill_building_question_employed_mode():
    """Test skill building question in employed mode."""
    user = create_user(career_mode="employed")
    question = get_skill_building_question(user)
    
    assert "Career Progress" in question["question"]
    assert "promotion" in question["description"]

def test_career_mode_toggle():
    """Test toggling career mode."""
    user = create_user(career_mode="skill_building")
    
    # Toggle to job_searching
    firestore_service.update_user(user.user_id, {"career_mode": "job_searching"})
    
    user_updated = firestore_service.get_user(user.user_id)
    assert user_updated.career_mode == "job_searching"
```

---

**File:** `tests/test_pattern_detection.py`

```python
def test_snooze_trap_detection():
    """Test snooze trap pattern detection."""
    user = create_user(target_wake="06:30")
    
    checkins = [
        create_checkin(date="2026-02-01", wake_time="07:00"),  # 30min snooze
        create_checkin(date="2026-02-02", wake_time="07:15"),  # 45min snooze
        create_checkin(date="2026-02-03", wake_time="07:30"),  # 60min snooze
    ]
    
    pattern = pattern_detection.detect_snooze_trap(user.user_id)
    
    assert pattern is not None
    assert pattern.type == "snooze_trap"
    assert pattern.severity == "warning"
    assert pattern.data["avg_snooze_minutes"] >= 30

def test_snooze_trap_not_detected_if_only_2_days():
    """Test snooze trap requires 3+ days."""
    user = create_user()
    
    checkins = [
        create_checkin(wake_time="07:00", target="06:30"),  # 30min
        create_checkin(wake_time="07:15", target="06:30"),  # 45min (only 2 days)
    ]
    
    pattern = pattern_detection.detect_snooze_trap(user.user_id)
    assert pattern is None

def test_consumption_vortex_detection():
    """Test consumption vortex pattern detection."""
    user = create_user()
    
    checkins = [
        create_checkin(consumption_hours=4),
        create_checkin(consumption_hours=5),
        create_checkin(consumption_hours=3.5),
        create_checkin(consumption_hours=4.5),
        create_checkin(consumption_hours=4),  # 5 days >3hrs
    ]
    
    pattern = pattern_detection.detect_consumption_vortex(user.user_id)
    
    assert pattern is not None
    assert pattern.type == "consumption_vortex"
    assert pattern.data["days_affected"] == 5

def test_deep_work_collapse_detection():
    """Test deep work collapse pattern detection."""
    user = create_user()
    
    checkins = [
        create_checkin(deep_work_hours=1.0),
        create_checkin(deep_work_hours=1.2),
        create_checkin(deep_work_hours=0.5),
        create_checkin(deep_work_hours=1.3),
        create_checkin(deep_work_hours=1.0),  # 5 days <1.5hrs
    ]
    
    pattern = pattern_detection.detect_deep_work_collapse(user.user_id)
    
    assert pattern is not None
    assert pattern.type == "deep_work_collapse"
    assert pattern.severity == "critical"

def test_relationship_interference_detection():
    """Test relationship interference pattern detection."""
    user = create_user()
    
    checkins = [
        create_checkin(boundaries=False, sleep_hours=6.0),  # Interference
        create_checkin(boundaries=False, training=False),   # Interference
        create_checkin(boundaries=False, sleep_hours=6.5),  # Interference
        create_checkin(boundaries=False, training=False),   # Interference
        create_checkin(boundaries=False, sleep_hours=6.0),  # Interference (5/7 days)
        create_checkin(boundaries=True, sleep_hours=7.5),   # OK
        create_checkin(boundaries=True, training=True),     # OK
    ]
    
    pattern = pattern_detection.detect_relationship_interference(user.user_id)
    
    assert pattern is not None
    assert pattern.type == "relationship_interference"
    assert pattern.data["correlation_pct"] > 70

def test_pattern_detection_graceful_missing_data():
    """Test pattern detection handles missing optional data gracefully."""
    user = create_user()
    
    checkins = [
        create_checkin(wake_time=None),  # Missing wake time
        create_checkin(consumption_hours=None),  # Missing consumption
    ]
    
    # Should not crash
    pattern1 = pattern_detection.detect_snooze_trap(user.user_id)
    pattern2 = pattern_detection.detect_consumption_vortex(user.user_id)
    
    assert pattern1 is None
    assert pattern2 is None
```

**Coverage Target:** 90%+ for pattern_detection.py additions

---

### Integration Tests

**File:** `tests/integration/test_phase3d.py`

```python
import pytest
from src.agents.checkin_agent import checkin_agent
from src.agents.pattern_detection import pattern_detection_agent

@pytest.mark.integration
async def test_tier1_with_skill_building():
    """Test Tier 1 check-in with 6 items including skill building."""
    
    user_id = "test_user_tier1"
    await setup_test_user(user_id, career_mode="skill_building")
    
    # Complete check-in with all 6 items
    checkin_data = {
        "tier1": {
            "sleep": {"completed": True, "hours": 7.5},
            "training": {"completed": True},
            "deep_work": {"completed": True, "hours": 2.5},
            "skill_building": {"completed": True, "hours": 2.0},
            "zero_porn": {"completed": True},
            "boundaries": {"completed": True}
        }
    }
    
    await checkin_agent.complete_checkin(user_id, checkin_data)
    
    # Verify compliance = 100% (all 6 items)
    checkin = firestore_service.get_latest_checkin(user_id)
    assert checkin.compliance_score == 100.0

@pytest.mark.integration
async def test_career_mode_switch_affects_question():
    """Test that switching career mode changes skill building question."""
    
    user_id = "test_user_career_switch"
    user = await setup_test_user(user_id, career_mode="skill_building")
    
    # Get question in skill_building mode
    q1 = get_skill_building_question(user)
    assert "Skill Building" in q1["question"]
    
    # Switch to job_searching
    firestore_service.update_user(user_id, {"career_mode": "job_searching"})
    user = firestore_service.get_user(user_id)
    
    # Get question in job_searching mode
    q2 = get_skill_building_question(user)
    assert "Job Search" in q2["question"]

@pytest.mark.integration
async def test_deep_work_collapse_intervention():
    """Test deep work collapse pattern triggers intervention."""
    
    user_id = "test_user_deep_work"
    await setup_test_user(user_id)
    
    # Create 5 check-ins with low deep work
    for i in range(5):
        await create_checkin(user_id, deep_work_hours=1.0)
    
    # Run pattern scan
    await pattern_detection_agent.scan_all_users()
    
    # Verify pattern detected
    patterns = firestore_service.get_patterns(user_id)
    assert any(p.type == "deep_work_collapse" for p in patterns)
    
    # Verify intervention sent
    interventions = firestore_service.get_interventions(user_id)
    assert any("DEEP WORK COLLAPSE" in i.message for i in interventions)

@pytest.mark.integration
async def test_all_9_patterns_coexist():
    """Test that all 9 patterns can be detected without conflicts."""
    
    user_id = "test_user_all_patterns"
    await setup_test_user(user_id)
    
    # Create data that triggers multiple patterns
    # (sleep degradation + deep work collapse + snooze trap)
    for i in range(5):
        await create_checkin(
            user_id,
            sleep_hours=6.0,  # Sleep degradation
            deep_work_hours=1.0,  # Deep work collapse
            wake_time="07:30"  # Snooze trap (if target is 06:30)
        )
    
    # Run pattern scan
    await pattern_detection_agent.scan_all_users()
    
    # Verify multiple patterns detected
    patterns = firestore_service.get_patterns(user_id)
    pattern_types = [p.type for p in patterns]
    
    assert "sleep_degradation" in pattern_types
    assert "deep_work_collapse" in pattern_types
    # Snooze trap may or may not trigger depending on target wake time setup
```

---

### Manual Testing Checklist

**Career Mode:**
- [ ] New user onboarding asks career mode selection
- [ ] Skill building question shows correctly for each mode
- [ ] `/career` command displays current mode
- [ ] Career mode toggle works (switch between 3 modes)
- [ ] Check-in question adapts when mode changes
- [ ] Tier 1 shows 6 items (including skill building)

**Pattern Detection:**
- [ ] Snooze trap triggers after 3 days >30min snooze
- [ ] Consumption vortex triggers after 5 days >3hrs
- [ ] Deep work collapse triggers after 5 days <1.5hrs
- [ ] Relationship interference triggers at 70%+ correlation
- [ ] All intervention messages formatted correctly
- [ ] Patterns logged in Firestore
- [ ] Interventions sent via Telegram

**Optional Data Collection:**
- [ ] Wake time question skippable
- [ ] Consumption hours question skippable
- [ ] Check-in completes even if optional questions skipped
- [ ] Patterns gracefully handle missing optional data

**Edge Cases:**
- [ ] User with no wake time data → snooze trap doesn't trigger (correct)
- [ ] User with no consumption data → vortex doesn't trigger (correct)
- [ ] User switches career mode mid-week → question adapts immediately
- [ ] Compliance calculation correct with 6 items (16.67% each)

---

## Deployment Plan

### Step 1: Database Verification

**Verify career_mode field exists:**

```python
user = firestore_service.get_user(test_user_id)
print(user.career_mode)  # Should print "skill_building" (default)
```

**Result:** No schema change needed! Field already exists from Phase 3A.

---

### Step 2: Code Deployment

**Files to Deploy:**

**Modified Files:**
- `src/models/schemas.py` (+30 lines for SkillBuildingData model)
- `src/bot/conversation.py` (+80 lines for Tier 1 expansion + optional questions)
- `src/bot/telegram_bot.py` (+70 lines for `/career` command)
- `src/utils/compliance.py` (+10 lines for 6-item calculation)
- `src/agents/pattern_detection.py` (+400 lines for 4 new patterns)
- `src/agents/intervention.py` (+200 lines for 4 new intervention messages)

**New Files:** None (all modifications to existing files)

**Deployment Command:**
```bash
# Test locally first
python -m pytest tests/test_career_mode.py
python -m pytest tests/test_pattern_detection.py
python -m pytest tests/integration/test_phase3d.py

# Deploy to Cloud Run
gcloud run deploy constitution-agent \
  --source . \
  --region asia-south1 \
  --platform managed
```

---

### Step 3: Data Migration (Optional Questions)

**Migration for Existing Check-Ins:**

Existing check-ins don't have skill_building field. When loading old check-ins, handle gracefully:

```python
# src/services/firestore_service.py

def get_checkin(user_id: str, date: str) -> DailyCheckIn:
    """Get check-in with backward compatibility."""
    
    doc = self.db.collection('daily_checkins').document(user_id)\
        .collection('checkins').document(date).get()
    
    if doc.exists:
        data = doc.to_dict()
        
        # Add skill_building if missing (backward compatibility)
        if 'skill_building' not in data.get('tier1', {}):
            data['tier1']['skill_building'] = {
                'completed': False,
                'hours': None
            }
        
        return DailyCheckIn(**data)
```

**Compliance Recalculation:** Old check-ins calculated with 5 items (20% each). Don't recalculate retroactively - only new check-ins use 6 items.

---

### Step 4: Testing in Production

**Test Sequence:**

1. **Career Mode:**
   - Run `/career` → verify shows current mode
   - Switch to different mode → verify updates
   - Complete check-in → verify question adapted

2. **Tier 1 Expansion:**
   - Complete check-in with all 6 items = Yes → verify 100% compliance
   - Complete check-in with 5/6 = Yes → verify 83.3% compliance

3. **Pattern Detection:**
   - Manually create low deep work check-ins → trigger pattern scan → verify intervention

4. **Optional Questions:**
   - Skip wake time and consumption → verify check-in completes
   - Provide wake time and consumption → verify stored correctly

**Monitor:**
- Cloud Logging for pattern detection logs
- Firestore for new pattern types
- Telegram for intervention messages

---

### Step 5: Gradual Rollout

**Phase 3D introduces optional data collection (wake time, consumption hours).**

**Rollout Strategy:**

**Week 1:** Deploy with optional questions OFF
- Users get Tier 1 with 6 items (skill building added)
- Career mode toggle works
- Deep work collapse + relationship interference patterns active (use existing data)
- Snooze trap + consumption vortex patterns inactive (no data yet)

**Week 2:** Enable optional questions for power users
- Ask 10% of users to track wake time and consumption
- Monitor data quality
- Test snooze trap and consumption vortex patterns

**Week 3:** Full rollout
- Enable optional questions for all users
- All 9 patterns active
- Monitor false positive rate

---

## Success Criteria

### Functional Criteria (Launch Blockers)

**Must Have:**
- ✅ Tier 1 expanded to 6 items (skill building added)
- ✅ Career mode toggle functional (3 modes)
- ✅ Adaptive questions working (tested all 3 modes)
- ✅ Compliance calculation correct (6 items, 16.67% each)
- ✅ 4 new patterns detect correctly (unit tested)
- ✅ Intervention messages formatted and sent
- ✅ Existing patterns still work (regression tested)
- ✅ Pattern scan performance acceptable (<30s for 10 users)

**Should Have (Can Deploy Without):**
- ⚪ Optional questions enabled for all users (can start with subset)
- ⚪ Career goal progress tracking dashboard (future enhancement)
- ⚪ LeetCode problem counter integration (future)

---

### Performance Criteria

| Metric | Target | Acceptable |
|--------|--------|------------|
| Pattern scan time (10 users) | <20s | <30s |
| Additional scan time (4 new patterns) | <5s | <10s |
| Check-in flow time | <10s | <15s |
| Career mode toggle | <1s | <2s |

**Reasoning:** 4 new patterns add minimal overhead because:
- Deep work collapse: uses existing data (no new queries)
- Relationship interference: uses existing data
- Snooze trap: optional data (if missing, skip)
- Consumption vortex: optional data (if missing, skip)

---

### Business Criteria

**Career Tracking Impact (60 days post-launch):**
- ✅ 100% career mode adoption (mandatory during onboarding)
- ✅ 70%+ users complete skill building 5+ days/week
- ✅ Qualitative feedback: "Career tracking helped job search" (3+ users)

**Pattern Detection Impact (60 days post-launch):**
- ✅ Deep work collapse interventions: 80% resolution within 7 days
- ✅ Relationship interference early detection: 2+ cases caught
- ✅ Snooze trap interventions: 60% resolution within 3 days
- ✅ Overall spiral reduction: 30% fewer 7-day compliance drops

**False Positive Rate:**
- ✅ <5% false positive rate for all patterns (user feedback)
- ✅ Pattern dismissal rate <10% (users rarely dismiss interventions)

---

### Cost Criteria

**Hard Limits (Must Not Exceed):**
- ✅ Phase 3D increase: <$0.05/month
- ✅ Total system cost: <$1.50/month (currently $1.43)

**Projected Costs (10 users):**

**Pattern Detection:**
- Deep work collapse: +0 Firestore reads (uses existing data)
- Relationship interference: +0 Firestore reads (uses existing data)
- Snooze trap: +0 queries if wake_time missing, +0 if present (already loaded)
- Consumption vortex: +0 queries if consumption_hours missing, +0 if present

**Career Mode:**
- Career mode queries: +0 reads (mode stored in User object, already loaded)

**Total Phase 3D cost: ~$0.000/month** ✅

**Why so cheap?**
- New patterns use existing check-in data (already loaded during scan)
- Optional data stored in existing check-in objects (no new reads)
- Career mode stored in User object (already loaded)
- No new API calls needed

**Result:** Phase 3D is essentially free! Main value is in better pattern detection, not increased cost.

---

## Appendix A: Data Model Changes

### Tier 1 Data Structure (Updated)

**Before Phase 3D (5 items):**

```python
class Tier1NonNegotiables(BaseModel):
    sleep: SleepData
    training: TrainingData
    deep_work: DeepWorkData
    zero_porn: CompletionData
    boundaries: CompletionData
```

**After Phase 3D (6 items):**

```python
class Tier1NonNegotiables(BaseModel):
    sleep: SleepData
    training: TrainingData
    deep_work: DeepWorkData
    skill_building: SkillBuildingData  # NEW
    zero_porn: CompletionData
    boundaries: CompletionData


class SkillBuildingData(BaseModel):
    completed: bool
    hours: Optional[float] = None
    activity: Optional[str] = None
```

---

### Optional Data Fields (Check-In Metadata)

**New Optional Fields:**

```python
class DailyCheckIn(BaseModel):
    # ... existing fields ...
    
    metadata: dict = Field(default_factory=dict)
    # metadata can contain:
    # - "wake_time": "HH:MM" (e.g., "07:15")
    # - "target_wake_time": "HH:MM" (e.g., "06:30")
    
    responses: CheckInResponses
    # responses can contain:
    # - "consumption_hours": float (e.g., 3.5)
```

**Storage:** Optional fields stored in existing structures (metadata, responses). No new collections needed.

---

## Appendix B: Pattern Detection Algorithm Comparison

### Simple vs Complex Patterns

**Simple Patterns (Rule-Based):**
- Sleep Degradation: Check if sleep <6hrs for 3+ days → DONE
- Training Abandonment: Check if training missed 3+ days → DONE
- Ghosting: Check if no check-in for 2+ days → DONE

**Complex Patterns (Correlation-Based):**
- Relationship Interference: Check if boundaries violated AND (sleep OR training failed) for 70%+ days
- Deep Work Collapse: Check trend over 5+ days, flag if sustained below threshold

**Algorithm Complexity:**
- Simple patterns: O(n) where n = days to check (usually 3-7)
- Complex patterns: O(n) but with more conditions per day

**Performance Impact:** Negligible. All patterns scan same check-ins (already loaded). Extra conditions add <1ms per user.

---

## Appendix C: Constitution Career Goals Tracking

### Current Implementation vs Future Enhancements

**Phase 3D Implements:**
- ✅ Daily skill building tracking (2+ hours Y/N)
- ✅ Career mode system (skill_building, job_searching, employed)
- ✅ Adaptive questions based on career phase

**Future Enhancements (Phase 3E+):**
- ⚪ LeetCode problem counter (API integration or manual entry)
- ⚪ Job application tracker (count applications per week)
- ⚪ Interview tracker (count interviews, track outcomes)
- ⚪ Salary progress dashboard (current salary → ₹28-42 LPA goal)
- ⚪ Monthly career review (AI analyzes progress toward June 2026 goal)
- ⚪ Career trajectory prediction ("on track" vs "behind" vs "ahead")

**Why Not Phase 3D?**
- Focus on foundation (skill building tracking + pattern detection)
- Advanced tracking requires more UX design (dashboards, input forms)
- Daily tracking sufficient for now; monthly reviews can come later

**Phase 3D Success:** Establishes career mode system that future enhancements build on.

---

**END OF SPECIFICATION**

---

**Document Version:** 1.0  
**Last Updated:** February 5, 2026  
**Status:** Ready for Implementation  
**Approved By:** User (Ayush)  
**Next Steps:** Begin Day 1 implementation (Career Mode System)
