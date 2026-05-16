# Accountability Agent — Next Version Implementation Plan
## Deep Spec & Technical Roadmap

**Version Target:** v2.0 (Major Release)  
**Estimated Timeline:** 16-20 weeks  
**Team Size:** 1-2 developers  
**Last Updated:** 2026-05-05

---

## Table of Contents

1. [Executive Overview](#1-executive-overview)
2. [Phase 1: Data Depth & Core Loop (Weeks 1-6)](#2-phase-1-data-depth--core-loop-weeks-1-6)
3. [Phase 2: Constitution & Social (Weeks 7-10)](#3-phase-2-constitution--social-weeks-7-10)
4. [Phase 3: Intelligence & Insights (Weeks 11-14)](#4-phase-3-intelligence--insights-weeks-11-14)
5. [Phase 4: Scale & Polish (Weeks 15-18)](#5-phase-4-scale--polish-weeks-15-18)
6. [Phase 5: Hardening & Launch (Weeks 19-20)](#6-phase-5-hardening--launch-weeks-19-20)
7. [Cross-Cutting Concerns](#7-cross-cutting-concerns)
8. [Testing Strategy](#8-testing-strategy)
9. [Risk Register](#9-risk-register)
10. [Appendix: Schema Migrations](#10-appendix-schema-migrations)

---

## 1. Executive Overview

### 1.1 Vision Statement

Transform the Accountability Agent from a "check-in tracker" into an **indispensable daily companion** that feels like a personal coach who remembers your goals, anticipates your struggles, and celebrates your wins.

### 1.2 Success Metrics

| Metric | Current | Target (v2.0) | Measurement |
|--------|---------|---------------|-------------|
| Daily Check-in Rate | ~60% | 85% | % of active users checking in daily |
| 7-Day Retention | ~45% | 70% | % of new users still active on day 7 |
| 30-Day Retention | ~25% | 50% | % of new users still active on day 30 |
| Check-in Completion Time | 3-4 min | 1.5-2 min | Time from /checkin to finish |
| User Satisfaction (NPS) | N/A | 50+ | /feedback command + periodic survey |
| Feature Discovery Rate | ~30% | 80% | % of users using >5 commands |

### 1.3 Guiding Principles

1. **Close every loop**: If we ask for data, we must use it within 24 hours
2. **Reduce friction at every step**: Every extra tap, every extra question is a drop-off risk
3. **Predict, don't just react**: The system should see problems coming before the user does
4. **Make it visible**: Dashboards, constitutions, and progress must be glanceable
5. **Fail gracefully**: Every new feature degrades cleanly if dependencies fail

---

## 2. Phase 1: Data Depth & Core Loop (Weeks 1-6)

### 2.1 P1.1: Capture Continuous Data, Not Just Booleans
**Priority: P0 | Owner: Backend + Bot | Complexity: High**

#### Problem
The system asks "Did you sleep 7+ hours? (Y/N)" but never captures the actual hours. This means:
- Pattern detection fabricates data (`7.5 if compliant else 5.5`)
- AI feedback is generic (can't say "you averaged 6.2 hours")
- Analytics are shallow (binary completion rates vs. meaningful averages)
- Optional fields like `sleep_hours`, `deep_work_hours` exist in schema but are never populated

#### Solution
Replace binary Y/N with **numeric capture** for continuous metrics. Keep boolean as "met threshold?" but add actual value.

#### Technical Design

**Conversation Flow Changes:**

```
OLD:
Bot: "😴 Sleep: 7+ hours today?"
[Yes] [No]

NEW (Adaptive):
Bot: "😴 How many hours did you sleep last night?"
[6] [6.5] [7] [7.5] [8] [8.5] [9] [Other]
→ If >= 7: "✅ Target met!"
→ If < 7: "⚠️ Below target. What got in the way?" (optional quick-reply)
```

**Schema Changes:**

```python
# src/models/schemas.py

class Tier1NonNegotiables(BaseModel):
    # ... existing fields ...
    
    # NEW: Make hours required, not optional
    sleep_hours: float = Field(..., ge=0, le=16, description="Actual hours slept")
    deep_work_hours: float = Field(..., ge=0, le=16, description="Actual focused hours")
    skill_building_hours: float = Field(..., ge=0, le=16, description="Actual learning hours")
    
    # Training intensity (replaces simple boolean)
    training_intensity: str = Field(..., pattern="^(rest|light|moderate|intense)$")
    
    # Computed property (backward compatible)
    @property
    def sleep(self) -> bool:
        return self.sleep_hours >= 7.0
    
    @property
    def deep_work(self) -> bool:
        return self.deep_work_hours >= 2.0
```

**Firestore Migration Strategy:**

```python
# scripts/migrate_binary_to_continuous.py
"""
One-time migration script to backfill continuous data from binary fields.

For existing check-ins:
- sleep=True → sleep_hours=7.5 (estimated)
- sleep=False → sleep_hours=5.5 (estimated)
- deep_work=True → deep_work_hours=2.5
- deep_work=False → deep_work_hours=0.5

Mark migrated records with `data_quality: "estimated"` flag.
"""
```

**Pattern Detection Updates:**

```python
# src/agents/pattern_detection.py

def _detect_sleep_degradation(self, checkins: List[DailyCheckIn]) -> Optional[Pattern]:
    # OLD: Uses fabricated estimates
    # sleep_hours = 7.5 if compliant else 5.5
    
    # NEW: Uses actual data
    sleep_data = []
    for c in checkins[-3:]:
        if c.tier1_non_negotiables.sleep_hours is not None:
            sleep_data.append((c.date, c.tier1_non_negotiables.sleep_hours))
    
    if len(sleep_data) < 3:
        return None  # Insufficient data
    
    avg_sleep = sum(h for _, h in sleep_data) / len(sleep_data)
    
    if avg_sleep < 6.0:
        return Pattern(
            type="sleep_degradation",
            severity="high",
            detected_at=datetime.utcnow(),
            data={
                "avg_sleep_hours": round(avg_sleep, 1),
                "actual_values": sleep_data,  # Real data!
                "trend": "declining" if self._is_declining(sleep_data) else "stable"
            }
        )
```

**Files to Modify:**
- [ ] `src/models/schemas.py` — Add continuous fields, computed properties
- [ ] `src/bot/conversation.py` — Update Q1 flow with numeric inputs
- [ ] `src/agents/pattern_detection.py` — Use real data instead of estimates
- [ ] `src/agents/checkin_agent.py` — Reference actual hours in feedback
- [ ] `src/services/analytics_service.py` — Calculate averages, trends, correlations
- [ ] `src/services/visualization_service.py` — Update charts to show distributions
- [ ] `scripts/migrate_binary_to_continuous.py` — One-time data migration
- [ ] `tests/test_schemas.py` — Validate new fields
- [ ] `tests/test_pattern_detection.py` — Update test data with real hours

#### Rollback Plan
If continuous capture causes drop-off:
1. Add `/settings` toggle: "Simple mode (Yes/No)" vs "Detailed mode (hours)"
2. Default to simple mode for new users
3. Keep continuous fields but make them optional again

#### Acceptance Criteria
- [ ] User can enter sleep hours via quick-reply buttons (6, 6.5, 7, 7.5, 8, 8.5, 9)
- [ ] Pattern detection uses actual hours (not estimates)
- [ ] AI feedback references specific averages (e.g., "You averaged 6.8 hours this week")
- [ ] All existing check-ins migrated with `data_quality` flag
- [ ] Analytics service shows distributions, not just completion rates

---

### 2.2 P1.2: Morning Briefing Feature
**Priority: P0 | Owner: Backend + Cron | Complexity: Medium**

#### Problem
The system captures "tomorrow's priority" and "tomorrow's obstacle" but never references them again. The feedback loop is broken.

#### Solution
Send a **Morning Briefing** message at 8 AM each day that:
1. Summarizes yesterday's performance
2. References yesterday's stated priority and obstacle
3. Provides day-of-week context ("Tuesdays are historically your weakest")
4. Offers one actionable suggestion

#### Technical Design

**New Cron Endpoint:**

```python
# src/main.py

@app.post("/cron/morning_briefing")
async def morning_briefing(request: Request):
    """
    Send morning briefing to all users at 8 AM local time.
    
    Triggered by Cloud Scheduler every 15 minutes (timezone-aware).
    """
    _verify_cron_secret(request)
    
    results = {"sent": 0, "skipped": 0, "errors": 0}
    
    # Find users in timezones currently at 8:00 AM
    target_timezones = timezone_utils.get_timezones_at_hour(8)
    
    for tz in target_timezones:
        users = firestore_service.get_users_by_timezone(tz)
        
        for user in users:
            try:
                # Check if user has opted in (default: True)
                if not user.settings.get("morning_briefing_enabled", True):
                    results["skipped"] += 1
                    continue
                
                # Generate briefing
                briefing = await generate_morning_briefing(user)
                
                # Send via Telegram
                await bot_manager.bot.send_message(
                    chat_id=user.telegram_id,
                    text=briefing,
                    parse_mode='HTML'
                )
                
                results["sent"] += 1
                
            except Exception as e:
                logger.error(f"Failed to send briefing to {user.user_id}: {e}")
                results["errors"] += 1
    
    return results
```

**Briefing Generation Service:**

```python
# src/services/briefing_service.py

async def generate_morning_briefing(user: User) -> str:
    """
    Generate personalized morning briefing.
    
    Components:
    1. Yesterday's summary
    2. Priority/obstacle follow-up
    3. Day-of-week context
    4. Suggestion
    """
    # Fetch yesterday's check-in
    yesterday = get_yesterday_date(user.timezone)
    yesterday_checkin = firestore_service.get_checkin(user.user_id, yesterday)
    
    # Fetch 30-day history for patterns
    history = firestore_service.get_recent_checkins(user.user_id, days=30)
    
    # Calculate day-of-week stats
    today_dow = get_day_of_week(user.timezone)
    dow_stats = calculate_dow_stats(history, today_dow)
    
    # Build briefing
    sections = []
    
    # Header
    sections.append(f"🌅 <b>Good morning, {user.name}!</b>")
    sections.append(f"<i>{yesterday.strftime('%A, %B %d')}</i>\n")
    
    # Yesterday's performance
    if yesterday_checkin:
        score = yesterday_checkin.compliance_score
        emoji = "🔥" if score >= 90 else "✅" if score >= 70 else "⚠️"
        sections.append(f"{emoji} <b>Yesterday:</b> {score:.0f}% compliance")
        
        # Tier 1 breakdown (brief)
        tier1 = yesterday_checkin.tier1_non_negotiables
        wins = []
        if tier1.sleep: wins.append("sleep")
        if tier1.training: wins.append("training")
        if tier1.deep_work: wins.append("deep work")
        if wins:
            sections.append(f"   Wins: {', '.join(wins)}")
    else:
        sections.append("📭 <b>Yesterday:</b> No check-in recorded")
    
    # Priority follow-up
    if yesterday_checkin and yesterday_checkin.responses.tomorrow_priority:
        priority = yesterday_checkin.responses.tomorrow_priority
        sections.append(f"\n🎯 <b>Your stated priority:</b> \"{priority}\"")
    
    # Day-of-week insight
    if dow_stats:
        avg = dow_stats["avg_compliance"]
        trend = "strong" if avg >= 80 else "challenging"
        sections.append(f"\n📊 <b>{today_dow}s are historically your {trend}est day</b> ({avg:.0f}% avg)")
    
    # Suggestion (AI-generated or rule-based)
    suggestion = await generate_suggestion(user, yesterday_checkin, dow_stats)
    sections.append(f"\n💡 <b>Today's focus:</b> {suggestion}")
    
    # Footer
    sections.append(f"\n<i>/checkin when ready →</i>")
    
    return "\n".join(sections)
```

**Files to Create/Modify:**
- [ ] `src/services/briefing_service.py` — New service for briefing generation
- [ ] `src/main.py` — Add `/cron/morning_briefing` endpoint
- [ ] `src/utils/timezone_utils.py` — Add `get_timezones_at_hour()` helper
- [ ] `src/models/schemas.py` — Add `settings.morning_briefing_enabled` to User
- [ ] `src/bot/telegram_bot.py` — Add `/briefing` on-demand command + `/settings` toggle
- [ ] `tests/test_briefing_service.py` — Unit tests for briefing generation
- [ ] `tests/test_main.py` — Test cron endpoint

#### Acceptance Criteria
- [ ] User receives briefing at 8 AM local time
- [ ] Briefing references yesterday's stated priority
- [ ] Briefing includes day-of-week historical context
- [ ] Briefing contains one actionable suggestion
- [ ] User can toggle on/off via `/settings morning_briefing off`
- [ ] On-demand `/briefing` command works

---

### 2.3 P1.3: Adaptive Check-In Flow
**Priority: P0 | Owner: Bot | Complexity: Medium**

#### Problem
Every user gets the exact same 4-question flow regardless of their streak, performance, or history. A 100% compliance day still requires answering "what was your biggest challenge?"

#### Solution
**Branch the conversation** based on user context. Make the flow shorter for high performers, more supportive for struggling users.

#### Technical Design

**Branching Logic:**

```python
# src/bot/conversation.py

async def start_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point with adaptive branching."""
    
    user = firestore_service.get_user(user_id)
    
    # Check if user is in "power user" mode (streak > 30, high compliance)
    is_power_user = (
        user.streaks.current_streak >= 30 and
        get_recent_avg_compliance(user_id, days=7) >= 85
    )
    
    # Check if user is struggling (low compliance, declining trend)
    is_struggling = get_recent_avg_compliance(user_id, days=7) < 60
    
    # Store adaptive context
    context.user_data["adaptive_mode"] = {
        "power_user": is_power_user,
        "struggling": is_struggling,
        "skip_challenges": False,  # Set later based on Q1 results
    }
    
    # Power users get a faster greeting
    if is_power_user:
        await update.message.reply_text(
            f"🔥 Day {user.streaks.current_streak} — let's keep the momentum!\n"
            f"(Quick mode available: /quickcheckin)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Full Check-in", callback_data="full")],
                [InlineKeyboardButton("⚡ Quick Check-in", callback_data="quick")],
            ])
        )
        return Q0_MODE_SELECT
    
    # Struggling users get encouragement
    if is_struggling:
        await update.message.reply_text(
            f"💪 Hey {user.name}, I know it's been tough. "
            f"Let's take this one step at a time. Ready?"
        )
    
    return Q1_TIER1


async def handle_q1_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """After Q1, decide whether to skip Q2 (challenges)."""
    
    adaptive_mode = context.user_data.get("adaptive_mode", {})
    compliance_score = context.user_data.get("compliance_score", 0)
    self_rating = context.user_data.get("self_rating", 5)
    
    # Skip challenges if perfect score and high rating
    if compliance_score == 100 and self_rating >= 8:
        adaptive_mode["skip_challenges"] = True
        await update.message.reply_text(
            "💯 Perfect day! Skipping challenges question.\n"
            "Let's quickly plan tomorrow:"
        )
        return Q4_TOMORROW  # Skip Q2 and Q3
    
    return Q2_CHALLENGES
```

**Files to Modify:**
- [ ] `src/bot/conversation.py` — Add adaptive branching logic
- [ ] `src/utils/compliance.py` — Add `get_recent_avg_compliance()` helper
- [ ] `tests/test_conversation.py` — Test adaptive flows

#### Acceptance Criteria
- [ ] Perfect days (100% compliance + rating >= 8) skip the challenges question
- [ ] Power users (streak >= 30) get quick/full mode choice at start
- [ ] Struggling users get encouraging framing
- [ ] Check-in completion time reduced to < 2 minutes for power users

---

### 2.4 P1.4: Churn Risk Prediction
**Priority: P1 | Owner: Backend | Complexity: High**

#### Problem
Users ghost silently. By the time pattern detection triggers "ghosting," the user has already disengaged.

#### Solution
Build a **churn risk model** that runs daily and identifies at-risk users BEFORE they disappear.

#### Technical Design

**Risk Factors:**

```python
# src/services/churn_prediction.py

CHURN_RISK_FACTORS = {
    "checkin_time_drift": {
        "weight": 0.25,
        "description": "Check-in time getting later (procrastination signal)",
        "threshold": 45,  # minutes later than 7-day average
    },
    "compliance_decline": {
        "weight": 0.30,
        "description": "3-week downward compliance trend",
        "threshold": -15,  # 15 point drop
    },
    "quick_checkin_overuse": {
        "weight": 0.20,
        "description": "Using quick check-ins for 5+ consecutive days",
        "threshold": 5,
    },
    "self_rating_decline": {
        "weight": 0.15,
        "description": "Average self-rating dropping",
        "threshold": -2,  # 2 point drop
    },
    "missed_reminders": {
        "weight": 0.10,
        "description": "Not responding to reminders",
        "threshold": 3,  # 3 missed reminders in a row
    },
}

class ChurnRiskPredictor:
    def calculate_risk_score(self, user: User) -> Tuple[float, List[str]]:
        """
        Returns (risk_score_0_to_1, list_of_triggered_factors).
        """
        score = 0.0
        factors = []
        
        # Check each factor
        if self._check_time_drift(user):
            score += CHURN_RISK_FACTORS["checkin_time_drift"]["weight"]
            factors.append("checkin_time_drift")
        
        if self._check_compliance_decline(user):
            score += CHURN_RISK_FACTORS["compliance_decline"]["weight"]
            factors.append("compliance_decline")
        
        # ... etc
        
        return score, factors
    
    def _check_time_drift(self, user: User) -> bool:
        """Has check-in time drifted later by >45 min?"""
        recent = firestore_service.get_recent_checkins(user.user_id, days=14)
        if len(recent) < 7:
            return False
        
        # Compare last 3 days vs first 7 days
        early_avg = self._avg_checkin_time(recent[:7])
        recent_avg = self._avg_checkin_time(recent[-3:])
        
        return (recent_avg - early_avg) > timedelta(minutes=45)
```

**Intervention Strategy:**

```python
# src/services/churn_intervention.py

async def send_churn_prevention_message(user: User, risk_score: float, factors: List[str]):
    """
    Send graduated intervention based on risk score.
    """
    if risk_score >= 0.8:
        # High risk: Personal, empathetic message
        message = (
            f"Hey {user.name}, I noticed your check-ins have been slipping. "
            f"No judgment — life happens.\n\n"
            f"Want to talk about what's getting in the way? /support\n"
            f"Or just do a quick check-in to get back on track: /quickcheckin"
        )
    elif risk_score >= 0.5:
        # Medium risk: Gentle nudge with context
        message = (
            f"{user.name}, you've been doing great ({user.streaks.current_streak} days!). "
            f"I noticed things have been a bit harder lately.\n\n"
            f"One small win today is all it takes. Ready? /checkin"
        )
    else:
        # Low risk: Generic encouragement
        return  # Don't message, just monitor
    
    await bot_manager.bot.send_message(
        chat_id=user.telegram_id,
        text=message,
        parse_mode='HTML'
    )
```

**Files to Create/Modify:**
- [ ] `src/services/churn_prediction.py` — Risk scoring algorithm
- [ ] `src/services/churn_intervention.py` — Intervention messaging
- [ ] `src/main.py` — Add `/cron/churn_prevention` endpoint (runs daily at 10 AM)
- [ ] `src/models/schemas.py` — Add `churn_risk_score` and `last_churn_check` to User
- [ ] `src/services/analytics_service.py` — Add churn metrics to admin dashboard
- [ ] `tests/test_churn_prediction.py` — Unit tests with synthetic data

#### Acceptance Criteria
- [ ] Model identifies 80% of churned users before day 3 of inactivity
- [ ] False positive rate < 20% (don't annoy stable users)
- [ ] Interventions are sent via existing notification system
- [ ] Risk scores are visible in admin dashboard
- [ ] A/B test framework supports testing intervention message variants

---

## 3. Phase 2: Constitution & Social (Weeks 7-10)

### 3.1 P2.1: Interactive Constitution Viewer & Editor
**Priority: P1 | Owner: Bot + Backend | Complexity: Medium**

#### Problem
Users can't see or edit their constitution after onboarding. It becomes invisible.

#### Solution
Make the constitution a **living document** stored in Firestore, viewable via `/constitution`, editable via `/constitution_edit`.

#### Technical Design

**Schema:**

```python
# src/models/schemas.py

class ConstitutionPrinciple(BaseModel):
    """Single principle in the user's constitution."""
    principle_id: str  # e.g., "physical_sovereignty"
    title: str         # e.g., "Physical Sovereignty"
    description: str   # The full text
    tier: str          # "tier1" | "tier2" | "aspirational"
    created_at: datetime
    updated_at: Optional[datetime] = None

class Constitution(BaseModel):
    """User's personal constitution."""
    user_id: str
    version: int = 1  # Increment on edit
    principles: List[ConstitutionPrinciple]
    career_goals: Dict[str, Any]  # e.g., {"target_salary": "₹28-42 LPA", "target_date": "2026-06"}
    updated_at: datetime
    
    def to_firestore(self) -> dict:
        return {
            "user_id": self.user_id,
            "version": self.version,
            "principles": [p.model_dump() for p in self.principles],
            "career_goals": self.career_goals,
            "updated_at": self.updated_at,
        }

# Migrate existing users: generate Constitution from hardcoded defaults
```

**Bot Commands:**

```
/constitution
→ Shows formatted constitution with current stats

/constitution_edit
→ Opens interactive editor
  1. "Which principle to edit?" [List]
  2. "New text:" [Free text input]
  3. "Saved! Your constitution v2 is live."

/constitution_add
→ "Title:" → "Description:" → "Tier:" → Saved
```

**Files to Create/Modify:**
- [ ] `src/models/schemas.py` — Constitution model
- [ ] `src/services/constitution_service.py` — Refactor to use user-specific constitutions
- [ ] `src/bot/telegram_bot.py` — Add `/constitution`, `/constitution_edit`, `/constitution_add`
- [ ] `src/agents/checkin_agent.py` — Reference user's actual constitution principles
- [ ] `src/agents/intervention.py` — Reference user's actual constitution
- [ ] `scripts/migrate_hardcoded_constitution.py` — One-time migration
- [ ] `tests/test_constitution_service.py`

#### Acceptance Criteria
- [ ] `/constitution` shows user's principles with live stats (e.g., "Sleep: 7+ hours — Current avg: 6.8h")
- [ ] `/constitution_edit` allows editing existing principles
- [ ] `/constitution_add` allows adding new principles
- [ ] AI feedback references principles from user's constitution, not hardcoded text
- [ ] Version history is tracked (can see previous versions)

---

### 3.2 P2.2: Goal-Setting & Milestone Tracking
**Priority: P1 | Owner: Bot + Backend | Complexity: Medium**

#### Problem
The constitution has aspirational goals ("₹28-42 LPA by June 2026") but no mechanism to break them into trackable milestones.

#### Solution
Add a **Goal System** with SMART goals tied to constitution principles.

#### Technical Design

```python
# src/models/schemas.py

class Goal(BaseModel):
    """User-defined goal with tracking."""
    goal_id: str = Field(default_factory=lambda: str(uuid.uuid4())[:8])
    user_id: str
    title: str                    # "Sleep 7+ hours for 14 days"
    description: str              # "Build consistent sleep habit"
    category: str                 # "sleep" | "training" | "deep_work" | "skill_building" | "custom"
    target_value: Optional[float] = None  # e.g., 7.0 hours
    target_days: int              # e.g., 14 consecutive days
    start_date: str               # YYYY-MM-DD
    end_date: Optional[str] = None
    status: str = "active"        # active | completed | failed | paused
    progress: List[Dict] = Field(default_factory=list)  # Daily progress snapshots
    created_at: datetime

# Example goals:
# - "Complete LeetCode 150 by June 1" (category: skill_building)
# - "Sleep 7+ hours for 30 days" (category: sleep)
# - "Zero porn for 90 days" (category: custom)
```

**Bot Commands:**

```
/goals — List active goals with progress
/goal_new — Create new goal (interactive flow)
/goal_progress <id> — Update progress manually
/goal_complete <id> — Mark complete (celebration!)
```

**Auto-Progress Tracking:**

```python
# src/services/goal_service.py

def update_goal_progress(user_id: str, checkin: DailyCheckIn):
    """Auto-update goal progress based on check-in data."""
    goals = firestore_service.get_active_goals(user_id)
    
    for goal in goals:
        # Check if checkin contributes to goal
        if goal.category == "sleep" and checkin.tier1_non_negotiables.sleep_hours:
            met = checkin.tier1_non_negotiables.sleep_hours >= goal.target_value
            goal.progress.append({
                "date": checkin.date,
                "met": met,
                "value": checkin.tier1_non_negotiables.sleep_hours,
            })
        
        # Check completion
        consecutive_met = count_consecutive_met(goal.progress)
        if consecutive_met >= goal.target_days:
            complete_goal(goal)
```

**Files to Create/Modify:**
- [ ] `src/models/schemas.py` — Goal model
- [ ] `src/services/goal_service.py` — Goal CRUD + progress tracking
- [ ] `src/bot/telegram_bot.py` — Goal commands
- [ ] `src/bot/conversation.py` — Post-checkin goal progress notification
- [ ] `src/agents/achievement_service.py` — "Goal Crusher" achievement
- [ ] `tests/test_goal_service.py`

#### Acceptance Criteria
- [ ] User can create a goal via `/goal_new` with interactive prompts
- [ ] Goals auto-update based on check-in data
- [ ] User gets notified when goal is 50%, 75%, and 100% complete
- [ ] Completed goals show in `/achievements`
- [ ] Goals are referenced in weekly reports

---

### 3.3 P2.3: Partner Challenges
**Priority: P1 | Owner: Bot + Backend | Complexity: Medium**

#### Problem
Accountability partners are just notifications. No shared experience.

#### Solution
Add **challenges** that partners can do together.

#### Technical Design

```python
# src/models/schemas.py

class PartnerChallenge(BaseModel):
    """Shared challenge between partners."""
    challenge_id: str
    challenger_id: str      # Who created it
    partner_id: str         # Who was invited
    challenge_type: str     # "sleep_7_days" | "training_5_days" | "custom"
    title: str
    description: str
    start_date: str
    end_date: str
    status: str = "pending"  # pending | active | completed | cancelled
    
    # Progress tracking per participant
    progress: Dict[str, List[Dict]]  # {user_id: [{date, met, value}]}
    
    # Winner (if competitive)
    winner_id: Optional[str] = None
    completed_at: Optional[datetime] = None
```

**Bot Flow:**

```
User A: /challenge @partner 7-day-sleep
Bot: "Challenge created! Invite sent to @partner."

User B: [Gets invite]
[Accept] [Decline]

Bot: "🎯 Challenge accepted! '7-Day Sleep Challenge' starts tomorrow.\n"
     "Both commit to 7+ hours sleep for 7 days.\n"
     "Current standings will update daily."

[Daily updates]
Bot: "📊 Sleep Challenge — Day 3\n"
     "You: 3/3 ✅ (7.5h avg)\n"
     "Partner: 2/3 ✅ (6.8h avg)\n"
     "Leader: You by 1 day!"

[Completion]
Bot: "🏆 Challenge Complete!\n"
     "You: 7/7 ✅\n"
     "Partner: 6/7 ✅\n"
     "Winner: You! 🎉\n"
     "+50 XP | +1 Win Streak"
```

**Files to Create/Modify:**
- [ ] `src/models/schemas.py` — PartnerChallenge model
- [ ] `src/services/challenge_service.py` — Challenge logic
- [ ] `src/bot/telegram_bot.py` — `/challenge`, challenge acceptance flow
- [ ] `src/bot/conversation.py` — Post-checkin challenge progress update
- [ ] `src/agents/achievement_service.py` — "Challenge Champion" achievement
- [ ] `tests/test_challenge_service.py`

#### Acceptance Criteria
- [ ] User can create a challenge with `/challenge @partner <type>`
- [ ] Partner receives invite with Accept/Decline buttons
- [ ] Daily progress updates sent to both participants
- [ ] Winner declared at end (or tie celebrated)
- [ ] Challenges appear in `/achievements` history

---

### 3.4 P2.4: Small Group Cohorts
**Priority: P2 | Owner: Backend + Bot | Complexity: High**

#### Problem
Partner accountability is limited to 1:1. Group dynamics (3-5 people) create stronger social bonds.

#### Solution
**Cohorts** — small groups auto-matched by timezone + career mode.

#### Technical Design

```python
# src/models/schemas.py

class Cohort(BaseModel):
    """Small accountability group (3-5 members)."""
    cohort_id: str
    name: str                    # e.g., "Night Owls — IST"
    timezone: str
    career_mode: str
    member_ids: List[str]       # 3-5 user IDs
    created_at: datetime
    status: str = "active"      # active | dissolved
    
    # Group stats
    weekly_compliance: float = 0.0  # Avg across all members
    challenges_completed: int = 0

class CohortInvitation(BaseModel):
    """Pending invitation to join a cohort."""
    invitation_id: str
    cohort_id: str
    user_id: str
    status: str = "pending"     # pending | accepted | declined
    created_at: datetime
```

**Matching Algorithm:**

```python
# src/services/cohort_service.py

def match_users_to_cohorts():
    """
    Match unmatched users into cohorts of 3-5.
    
    Criteria:
    1. Same timezone (or within 2 hours)
    2. Same career mode
    3. Similar check-in time preference
    4. Mix of experience levels (1 veteran, 1-2 mid, 1-2 new)
    """
    unmatched = firestore_service.get_unmatched_users()
    
    # Group by (timezone, career_mode)
    buckets = defaultdict(list)
    for user in unmatched:
        key = (user.timezone, user.career_mode)
        buckets[key].append(user)
    
    # Form cohorts of 3-5
    for key, users in buckets.items():
        while len(users) >= 3:
            cohort_users = users[:5]  # Take up to 5
            create_cohort(cohort_users)
            users = users[5:]
```

**Files to Create/Modify:**
- [ ] `src/models/schemas.py` — Cohort, CohortInvitation models
- [ ] `src/services/cohort_service.py` — Matching + management
- [ ] `src/bot/telegram_bot.py` — `/cohort`, `/cohort_status`, `/leave_cohort`
- [ ] `src/main.py` — `/cron/cohort_matching` (weekly)
- [ ] `tests/test_cohort_service.py`

#### Acceptance Criteria
- [ ] Unmatched users are auto-matched into cohorts weekly
- [ ] Cohort members can see each other's daily compliance (not details)
- [ ] Weekly cohort report: "Your cohort averaged 82% this week"
- [ ] Cohort group challenges available
- [ ] User can leave cohort and rejoin matching queue

---

## 4. Phase 3: Intelligence & Insights (Weeks 11-14)

### 4.1 P3.1: Day-of-Week & Time-based Insights
**Priority: P1 | Owner: Backend + AI | Complexity: Medium**

#### Problem
Users don't know their own patterns. "When am I weakest?" "What time of day do I skip training?"

#### Solution
**Pattern Insights Engine** that analyzes historical data and surfaces actionable patterns.

#### Technical Design

```python
# src/services/insights_engine.py

class InsightsEngine:
    """Generate personalized insights from check-in history."""
    
    def generate_weekly_insights(self, user_id: str) -> List[Dict]:
        """
        Generate 3-5 insights for the weekly report.
        
        Insight types:
        1. Day-of-week patterns
        2. Time-of-day patterns
        3. Correlation insights
        4. Trend predictions
        """
        checkins = firestore_service.get_recent_checkins(user_id, days=90)
        insights = []
        
        # Day-of-week analysis
        dow_insight = self._analyze_dow_patterns(checkins)
        if dow_insight:
            insights.append(dow_insight)
        
        # Correlation: sleep → next day performance
        correlation_insight = self._analyze_sleep_performance_correlation(checkins)
        if correlation_insight:
            insights.append(correlation_insight)
        
        # Risk window detection
        risk_insight = self._detect_risk_windows(checkins)
        if risk_insight:
            insights.append(risk_insight)
        
        return insights
    
    def _analyze_dow_patterns(self, checkins: List[DailyCheckIn]) -> Optional[Dict]:
        """Find day-of-week patterns."""
        dow_scores = defaultdict(list)
        for c in checkins:
            dow = datetime.strptime(c.date, "%Y-%m-%d").strftime("%A")
            dow_scores[dow].append(c.compliance_score)
        
        avgs = {dow: sum(scores)/len(scores) for dow, scores in dow_scores.items() if len(scores) >= 3}
        
        if not avgs:
            return None
        
        best = max(avgs, key=avgs.get)
        worst = min(avgs, key=avgs.get)
        
        return {
            "type": "day_of_week",
            "title": f"Your {best}s are strongest ({avgs[best]:.0f}%), {worst}s are toughest ({avgs[worst]:.0f}%)",
            "suggestion": f"Plan harder tasks for {best}s. Be extra vigilant on {worst}s.",
        }
```

**Weekly Report Integration:**

```python
# src/agents/reporting_agent.py

async def generate_ai_insights(...):
    # Existing metrics...
    
    # NEW: Add pattern insights
    insights_engine = InsightsEngine()
    pattern_insights = insights_engine.generate_weekly_insights(user.user_id)
    
    # Include in prompt
    insights_block = "\n".join([f"- {i['title']}" for i in pattern_insights])
    
    prompt += f"""

Personalized Patterns Detected:
{insights_block}

Reference these patterns in your insight."""
```

**Files to Create/Modify:**
- [ ] `src/services/insights_engine.py` — New service
- [ ] `src/agents/reporting_agent.py` — Integrate insights into weekly report
- [ ] `src/bot/telegram_bot.py` — `/insights` on-demand command
- [ ] `tests/test_insights_engine.py`

#### Acceptance Criteria
- [ ] Weekly report includes 2-3 personalized pattern insights
- [ ] Insights reference actual data (not generic advice)
- [ ] `/insights` command shows all detected patterns
- [ ] Insights update as more data is collected

---

### 4.2 P3.2: Mood & Energy Tracking
**Priority: P2 | Owner: Bot + Backend | Complexity: Low-Medium**

#### Problem
No emotional state tracking beyond the 1-10 self-rating. Can't correlate mood with habits.

#### Solution
Add **mood + energy** ratings to check-in, then correlate with habits.

#### Technical Design

```python
# src/models/schemas.py

class CheckInResponses(BaseModel):
    # ... existing fields ...
    
    # NEW: Mood & energy tracking
    energy_rating: int = Field(..., ge=1, le=10, description="Energy level 1-10")
    mood_rating: int = Field(..., ge=1, le=10, description="Mood level 1-10")


# Correlation analysis
# src/services/analytics_service.py

def calculate_mood_correlations(checkins: List[DailyCheckIn]) -> Dict[str, Any]:
    """
    Find correlations between habits and mood/energy.
    
    Returns:
        {
            "sleep_mood_correlation": 0.72,  # Strong positive
            "training_energy_correlation": 0.65,
            "deep_work_mood_correlation": 0.45,
            "best_combination": ["sleep", "training"],  # Highest mood
        }
    """
    # Pearson correlation between sleep hours and mood
    sleep_hours = [c.tier1_non_negotiables.sleep_hours for c in checkins if c.tier1_non_negotiables.sleep_hours]
    moods = [c.responses.mood_rating for c in checkins if c.responses.mood_rating]
    
    if len(sleep_hours) == len(moods) and len(sleep_hours) > 5:
        correlation = pearson_correlation(sleep_hours, moods)
        return {"sleep_mood_correlation": correlation}
```

**Conversation Flow:**

```
Bot: "🌤️ Rate your energy today (1 = exhausted, 10 = unstoppable)"
[1] [2] [3] [4] [5] [6] [7] [8] [9] [10]

Bot: "😊 Rate your mood today (1 = terrible, 10 = amazing)"
[1] [2] [3] [4] [5] [6] [7] [8] [9] [10]
```

**Files to Create/Modify:**
- [ ] `src/models/schemas.py` — Add energy_rating, mood_rating
- [ ] `src/bot/conversation.py` — Add Q5 (mood/energy) after Q4
- [ ] `src/services/analytics_service.py` — Correlation calculations
- [ ] `src/agents/reporting_agent.py` — Include mood trends in report
- [ ] `tests/test_analytics_service.py`

#### Acceptance Criteria
- [ ] Check-in includes energy (1-10) and mood (1-10) questions
- [ ] Weekly report shows mood trend line
- [ ] Insights engine surfaces correlations ("You sleep <6h → next day mood averages 4.2")
- [ ] Mood data visible in `/metrics` command

---

### 4.3 P3.3: Predictive Interventions
**Priority: P2 | Owner: Backend + AI | Complexity: High**

#### Problem
Interventions happen AFTER patterns are detected. Can we predict problems before they occur?

#### Solution
**Predictive model** that identifies high-risk days BEFORE they happen.

#### Technical Design

```python
# src/services/predictive_intervention.py

class PredictiveInterventionEngine:
    """
    Predict tomorrow's risk and intervene preemptively.
    """
    
    def predict_tomorrow_risk(self, user: User) -> Dict[str, Any]:
        """
        Predict which Tier 1 items are at risk tomorrow.
        
        Signals:
        - Day-of-week risk (user skips training on 80% of Saturdays)
        - Streak fatigue (day 6 of week, historically lower compliance)
        - Context (travel, work deadline, etc. from user's calendar - future)
        - Recent decline (compliance dropped 20% over last 3 days)
        """
        checkins = firestore_service.get_recent_checkins(user.user_id, days=30)
        
        tomorrow = get_tomorrow_date(user.timezone)
        tomorrow_dow = tomorrow.strftime("%A")
        
        risks = []
        
        # Day-of-week risk
        dow_risks = self._get_dow_risks(checkins, tomorrow_dow)
        risks.extend(dow_risks)
        
        # Streak fatigue
        if user.streaks.current_streak % 7 == 6:  # Day 6 of week
            risks.append({
                "metric": "general",
                "risk": "streak_fatigue",
                "probability": 0.6,
                "reason": "Day 6 of week is historically your weakest",
            })
        
        # Recent decline
        recent_trend = calculate_trend(checkins[-7:])
        if recent_trend["direction"] == "down" and recent_trend["magnitude"] > 15:
            risks.append({
                "metric": "general",
                "risk": "momentum_loss",
                "probability": 0.7,
                "reason": "Compliance dropped 15%+ over last week",
            })
        
        return {
            "risk_score": max(r["probability"] for r in risks) if risks else 0.0,
            "risks": risks,
            "preventive_actions": self._suggest_preventive_actions(risks),
        }
    
    def _suggest_preventive_actions(self, risks: List[Dict]) -> List[str]:
        """Suggest actions to prevent predicted failures."""
        actions = []
        
        for risk in risks:
            if risk["metric"] == "sleep" and risk["risk"] == "dow_risk":
                actions.append("Set a bedtime alarm for tonight")
            elif risk["metric"] == "training":
                actions.append("Lay out workout clothes before bed")
            elif risk["risk"] == "streak_fatigue":
                actions.append("Plan one fun activity for tomorrow as reward")
        
        return actions
```

**Preemptive Message:**

```
🔮 Tomorrow's Risk Forecast

Based on your patterns, tomorrow (Saturday) has elevated risk:
• Sleep: 65% risk (you average 5.8h on Saturdays)
• Training: 45% risk (you skip 40% of Saturday workouts)

Preventive Actions:
1. Set bedtime alarm for 10:30 PM tonight
2. Schedule workout for 8 AM (before day gets away)
3. Prep healthy breakfast tonight

You've got this. Your 52-day streak is worth protecting.
```

**Files to Create/Modify:**
- [ ] `src/services/predictive_intervention.py` — New engine
- [ ] `src/main.py` — `/cron/predictive_intervention` (evening, 9 PM)
- [ ] `src/models/schemas.py` — Add `predictive_interventions_enabled` to User settings
- [ ] `tests/test_predictive_intervention.py`

#### Acceptance Criteria
- [ ] System predicts tomorrow's risks based on historical patterns
- [ ] Preventive message sent the evening before (9 PM)
- [ ] Predictions reference actual data (not generic)
- [ ] User can toggle predictive interventions in `/settings`

---

## 5. Phase 4: Scale & Polish (Weeks 15-18)

### 5.1 P4.1: Progressive Onboarding
**Priority: P1 | Owner: Bot | Complexity: Medium**

#### Problem
`/start` instantly creates a profile. No guided setup, no feature discovery.

#### Solution
**5-step progressive onboarding** that builds investment and teaches features.

#### Technical Design

```python
# src/bot/onboarding.py

class OnboardingFlow:
    """
    5-step progressive onboarding.
    """
    
    STEPS = [
        "welcome",           # Welcome message + name confirmation
        "timezone",          # Timezone selection
        "career_mode",       # Career goal selection
        "bedtime",           # Bedtime reminder setup
        "first_checkin",     # Complete first check-in
    ]
    
    async def step_welcome(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Step 1: Welcome and name."""
        await update.message.reply_text(
            "🎯 Welcome to Accountability Agent!\n\n"
            "I'm your AI-powered accountability partner. "
            "Together, we'll build habits that stick.\n\n"
            "What's your name?",
            reply_markup=ForceReply(selective=True)
        )
        return ONBOARDING_NAME
    
    async def step_timezone(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Step 2: Timezone."""
        # Show common timezones as buttons
        await update.message.reply_text(
            "🌍 What timezone are you in?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("IST (India)", callback_data="Asia/Kolkata")],
                [InlineKeyboardButton("EST (New York)", callback_data="America/New_York")],
                [InlineKeyboardButton("PST (California)", callback_data="America/Los_Angeles")],
                [InlineKeyboardButton("GMT (London)", callback_data="Europe/London")],
            ])
        )
        return ONBOARDING_TIMEZONE
    
    async def step_career_mode(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Step 3: Career mode."""
        await update.message.reply_text(
            "💼 What's your primary career focus right now?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("📚 Learning & Skill Building", callback_data="skill_building")],
                [InlineKeyboardButton("🔍 Active Job Search", callback_data="job_searching")],
                [InlineKeyboardButton("🎯 Working Toward Promotion", callback_data="employed")],
            ])
        )
        return ONBOARDING_CAREER
    
    async def step_bedtime(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Step 4: Set bedtime for reminders."""
        await update.message.reply_text(
            "😴 What time do you want to go to bed?\n"
            "I'll send your first check-in reminder 2 hours before.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("10:00 PM", callback_data="22:00")],
                [InlineKeyboardButton("11:00 PM", callback_data="23:00")],
                [InlineKeyboardButton("12:00 AM", callback_data="00:00")],
            ])
        )
        return ONBOARDING_BEDTIME
    
    async def step_first_checkin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Step 5: Complete first check-in to unlock dashboard."""
        await update.message.reply_text(
            "🎉 Almost there!\n\n"
            "Complete your first check-in to unlock:\n"
            "• Your personal dashboard\n"
            "• Streak tracking\n"
            "• AI-powered feedback\n\n"
            "Ready? /checkin"
        )
        return ConversationHandler.END
```

**Files to Create/Modify:**
- [ ] `src/bot/onboarding.py` — New onboarding flow
- [ ] `src/bot/telegram_bot.py` — Replace `/start` handler with onboarding
- [ ] `src/models/schemas.py` — Add `onboarding_completed` flag to User
- [ ] `tests/test_onboarding.py`

#### Acceptance Criteria
- [ ] New users go through 5-step guided onboarding
- [ ] Each step teaches a feature or collects a preference
- [ ] Dashboard is "locked" until first check-in is complete
- [ ] Onboarding can be resumed if interrupted
- [ ] Existing users are unaffected (onboarding_completed=True)

---

### 5.2 P4.2: Streak Recovery Ritual
**Priority: P1 | Owner: Bot | Complexity: Low**

#### Problem
When a streak breaks, the system just resets to 0. This feels punishing and can trigger abandonment.

#### Solution
**Streak Recovery Ritual** — a structured, compassionate response to streak breaks.

#### Technical Design

```python
# src/bot/conversation.py (or new streak_recovery.py)

async def handle_streak_break(user: User, bot) -> None:
    """
    Send streak recovery ritual when streak is broken.
    """
    previous_streak = user.streaks.streak_before_reset
    
    message = (
        f"💔 <b>Streak Broken: {previous_streak} → 0</b>\n\n"
        f"This happens. The question is: what will you do in the next 24 hours?\n\n"
        f"<b>1. Analyze</b> (Optional)\n"
        f"What caused the break? A quick answer helps me help you:\n"
        f"[😴 Sleep] [🏋️ Training] [💼 Work] [😔 Motivation] [🤷 Other]\n\n"
        f"<b>2. Forgive</b>\n"
        f"Your past self did their best. Your future self is counting on you.\n\n"
        f"<b>3. Restart</b>\n"
        f"Your comeback begins NOW.\n\n"
        f"[/checkin to start Day 1] [/support to talk]"
    )
    
    await bot.send_message(
        chat_id=user.telegram_id,
        text=message,
        parse_mode='HTML'
    )
    
    # Store break reason if provided
    # (Would need a conversation handler for the button responses)
```

**Break Reason Analysis:**

```python
# src/services/analytics_service.py

def analyze_break_patterns(user_id: str) -> Dict[str, Any]:
    """
    Analyze historical break reasons to identify patterns.
    
    Returns:
        {
            "most_common_reason": "sleep",
            "break_dow_pattern": "Saturday",  # Most breaks on Saturdays
            "recovery_time_avg": 2.3,  # Days to restart
        }
    """
    breaks = firestore_service.get_streak_breaks(user_id)
    
    # Analyze reasons
    reasons = [b.get("reason", "unknown") for b in breaks]
    most_common = Counter(reasons).most_common(1)[0][0] if reasons else None
    
    # Analyze day-of-week
    break_dows = [datetime.strptime(b["date"], "%Y-%m-%d").strftime("%A") for b in breaks]
    most_common_dow = Counter(break_dows).most_common(1)[0][0] if break_dows else None
    
    return {
        "most_common_reason": most_common,
        "break_dow_pattern": most_common_dow,
        "total_breaks": len(breaks),
    }
```

**Files to Create/Modify:**
- [ ] `src/bot/streak_recovery.py` — Recovery ritual flow
- [ ] `src/utils/streak.py` — Trigger recovery ritual on streak break
- [ ] `src/services/analytics_service.py` — Break pattern analysis
- [ ] `src/models/schemas.py` — Add `break_reasons` array to User
- [ ] `tests/test_streak_recovery.py`

#### Acceptance Criteria
- [ ] Streak break triggers compassionate ritual (not just reset)
- [ ] User can select break reason via quick-reply buttons
- [ ] Break reasons are stored and analyzed
- [ ] Recovery message includes personalized context ("You broke 3 of last 5 streaks on Saturdays")
- [ ] `/checkin` prominently featured as restart action

---

### 5.3 P4.3: Feature Discovery & Hints
**Priority: P2 | Owner: Bot | Complexity: Low**

#### Problem
Users discover < 30% of features. Most never use `/quickcheckin`, `/support`, `/achievements`.

#### Solution
**Contextual hints** triggered by user behavior milestones.

#### Technical Design

```python
# src/services/feature_discovery.py

FEATURE_HINTS = {
    "quickcheckin": {
        "trigger": "after_3_checkins",
        "message": "💡 <b>Tip:</b> Busy day? Use /quickcheckin for a 30-second check-in (2 per week).",
    },
    "support": {
        "trigger": "low_rating_3_days",
        "message": "💡 <b>Tip:</b> Struggling? Type /support anytime to talk it through.",
    },
    "achievements": {
        "trigger": "streak_7_days",
        "message": "🏅 <b>Achievement unlocked!</b> See all your badges: /achievements",
    },
    "partner": {
        "trigger": "streak_14_days",
        "message": "💡 <b>Tip:</b> An accountability partner 2x's your success rate. /set_partner",
    },
    "shield": {
        "trigger": "streak_at_risk",
        "message": "🛡️ <b>Tip:</b> Missed a day? Use /use_shield to protect your streak (3 per month).",
    },
    "insights": {
        "trigger": "first_pattern_detected",
        "message": "🔍 <b>Pattern detected!</b> I analyze your habits automatically. See patterns: /insights",
    },
}

class FeatureDiscoveryService:
    def check_and_send_hints(self, user: User, event: str):
        """
        Check if any hints should be sent based on user event.
        
        Events:
        - after_3_checkins
        - low_rating_3_days
        - streak_7_days
        - streak_14_days
        - first_pattern_detected
        - streak_at_risk
        """
        hints_sent = user.settings.get("hints_sent", [])
        
        for feature_id, hint in FEATURE_HINTS.items():
            if hint["trigger"] == event and feature_id not in hints_sent:
                # Send hint
                await bot_manager.bot.send_message(
                    chat_id=user.telegram_id,
                    text=hint["message"],
                    parse_mode='HTML'
                )
                
                # Mark as sent
                hints_sent.append(feature_id)
                firestore_service.update_user_settings(user.user_id, {"hints_sent": hints_sent})
                break  # Send max 1 hint per event
```

**Files to Create/Modify:**
- [ ] `src/services/feature_discovery.py` — New service
- [ ] `src/bot/telegram_bot.py` — Integrate hint triggers into command handlers
- [ ] `src/bot/conversation.py` — Trigger hints after check-ins
- [ ] `src/models/schemas.py` — Add `hints_sent` to User settings

#### Acceptance Criteria
- [ ] User receives contextual hints based on behavior
- [ ] No more than 1 hint per day (not spammy)
- [ ] Hints are marked as "sent" and not repeated
- [ ] User can disable hints in `/settings`
- [ ] Feature usage increases by 50%+

---

### 5.4 P4.4: User Feedback Loop
**Priority: P2 | Owner: Bot + Backend | Complexity: Low**

#### Problem
No systematic way to collect user feedback or satisfaction.

#### Solution
Add `/feedback` command and periodic NPS-style surveys.

#### Technical Design

```python
# src/models/schemas.py

class Feedback(BaseModel):
    """User feedback entry."""
    feedback_id: str
    user_id: str
    type: str          # "nps" | "feature_request" | "bug" | "general"
    rating: Optional[int] = None  # 1-10 for NPS
    message: str
    context: Dict[str, Any] = Field(default_factory=dict)  # e.g., {"command": "/checkin"}
    created_at: datetime


# src/bot/telegram_bot.py

async def feedback_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /feedback command."""
    await update.message.reply_text(
        "📣 <b>Your Feedback Matters</b>\n\n"
        "How likely are you to recommend Accountability Agent to a friend?\n"
        "(0 = not likely, 10 = very likely)",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton(str(i), callback_data=f"nps_{i}") for i in range(0, 6)],
            [InlineKeyboardButton(str(i), callback_data=f"nps_{i}") for i in range(6, 11)],
        ])
    )

async def handle_nps_rating(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Store NPS rating and ask for follow-up."""
    rating = int(update.callback_query.data.split("_")[1])
    
    # Store rating
    firestore_service.store_feedback(
        user_id=str(update.effective_user.id),
        type="nps",
        rating=rating,
        message="",
    )
    
    if rating >= 9:
        await update.callback_query.message.reply_text(
            "🎉 Thank you! What do you love most about the bot?"
        )
    elif rating >= 7:
        await update.callback_query.message.reply_text(
            "Thanks! What's one thing we could improve?"
        )
    else:
        await update.callback_query.message.reply_text(
            "I'm sorry to hear that. What's the biggest issue you're facing?"
        )
```

**Periodic Survey:**

```python
# src/main.py — /cron/weekly_nps

@app.post("/cron/weekly_nps")
async def weekly_nps_survey(request: Request):
    """
    Send NPS survey to active users every Sunday.
    Only to users who haven't provided feedback in 14 days.
    """
    active_users = firestore_service.get_active_users(days=7)
    
    for user in active_users:
        last_feedback = firestore_service.get_last_feedback(user.user_id)
        if not last_feedback or days_since(last_feedback.created_at) >= 14:
            await bot_manager.bot.send_message(
                chat_id=user.telegram_id,
                text="📊 Quick question: How's your experience going? /feedback",
            )
```

**Files to Create/Modify:**
- [ ] `src/models/schemas.py` — Feedback model
- [ ] `src/services/feedback_service.py` — Feedback CRUD
- [ ] `src/bot/telegram_bot.py` — `/feedback` command
- [ ] `src/main.py` — `/cron/weekly_nps` endpoint
- [ ] `src/services/analytics_service.py` — NPS calculation
- [ ] `tests/test_feedback_service.py`

#### Acceptance Criteria
- [ ] `/feedback` command collects NPS + qualitative feedback
- [ ] Weekly NPS survey sent to active users (max 1 per 14 days)
- [ ] Feedback stored in Firestore with context
- [ ] Admin dashboard shows NPS trend over time
- [ ] Feedback influences feature prioritization

---

### 5.5 P4.5: Admin Dashboard Enhancement
**Priority: P2 | Owner: Backend | Complexity: Medium**

#### Problem
`/admin_status` shows basic metrics but no user health, cohort analysis, or churn tracking.

#### Solution
**Enhanced admin dashboard** with user health scores, cohort retention, and feature usage.

#### Technical Design

```python
# src/services/admin_dashboard.py

class AdminDashboard:
    def generate_full_report(self) -> Dict[str, Any]:
        """Generate comprehensive admin report."""
        return {
            "overview": {
                "total_users": self._count_total_users(),
                "active_users_7d": self._count_active_users(days=7),
                "active_users_30d": self._count_active_users(days=30),
                "new_users_7d": self._count_new_users(days=7),
            },
            "retention": {
                "day_7": self._calculate_retention(days=7),
                "day_30": self._calculate_retention(days=30),
                "day_90": self._calculate_retention(days=90),
            },
            "user_health": {
                "at_risk": self._count_at_risk_users(),
                "churned_7d": self._count_churned_users(days=7),
                "churned_30d": self._count_churned_users(days=30),
            },
            "feature_usage": {
                "checkin_rate": self._calculate_checkin_rate(),
                "quickcheckin_rate": self._calculate_feature_usage("/quickcheckin"),
                "support_rate": self._calculate_feature_usage("/support"),
                "partner_link_rate": self._calculate_partner_link_rate(),
            },
            "ai_costs": {
                "daily_tokens": self._calculate_daily_tokens(),
                "daily_cost_usd": self._calculate_daily_cost(),
                "cost_per_user": self._calculate_cost_per_user(),
            },
        }
    
    def _calculate_retention(self, days: int) -> float:
        """Calculate X-day retention rate."""
        # Cohort analysis: of users who signed up X days ago, what % are still active?
        pass
```

**Files to Create/Modify:**
- [ ] `src/services/admin_dashboard.py` — New service
- [ ] `src/main.py` — Enhance `/admin/metrics` endpoint
- [ ] `src/bot/telegram_bot.py` — Enhance `/admin_status` command output
- [ ] `tests/test_admin_dashboard.py`

#### Acceptance Criteria
- [ ] Admin dashboard shows retention rates (7d, 30d, 90d)
- [ ] Admin dashboard shows user health (at-risk, churned)
- [ ] Admin dashboard shows feature usage rates
- [ ] Admin dashboard shows AI cost breakdown
- [ ] Data exportable as CSV

---

## 6. Phase 5: Hardening & Launch (Weeks 19-20)

### 6.1 P5.1: Testing & Reliability
**Priority: P0 | Owner: QA | Complexity: High**

#### Tasks

- [ ] **Integration Tests**
  - [ ] Full check-in conversation flow (all branches)
  - [ ] Morning briefing generation + delivery
  - [ ] Streak break detection + recovery ritual
  - [ ] Partner challenge creation + completion
  - [ ] Cohort matching algorithm

- [ ] **Load Tests**
  - [ ] Cron endpoints with 1000 simulated users
  - [ ] Webhook handling under burst traffic
  - [ ] Firestore read/write throughput
  - [ ] Gemini API rate limit handling

- [ ] **Chaos Tests**
  - [ ] Gemini API down for 1 hour (fallback templates work)
  - [ ] Firestore connection lost (graceful degradation)
  - [ ] Telegram API rate limit (retry + backoff)
  - [ ] Cloud Run cold start (startup time < 30s)

- [ ] **Snapshot Tests**
  - [ ] AI prompts don't drift (compare to baseline)
  - [ ] Intervention messages meet tone requirements
  - [ ] Weekly report format is consistent

### 6.2 P5.2: Security & Privacy
**Priority: P1 | Owner: Backend | Complexity: Medium**

#### Tasks

- [ ] **Data Export Security**
  - [ ] `/export` data encrypted with user-specific password
  - [ ] Export links expire after 24 hours
  - [ ] Audit log of all exports

- [ ] **GDPR Compliance**
  - [ ] `/delete_my_data` command (full account deletion)
  - [ ] Data portability (export in standard format)
  - [ ] Consent tracking for data collection

- [ ] **AI Prompt Audit**
  - [ ] Review all prompts for PII leakage
  - [ ] Ensure no user names/emails in LLM logs
  - [ ] Add prompt sanitization layer

- [ ] **Access Control**
  - [ ] Admin endpoints behind VPN/IAP
  - [ ] Rate limiting on all endpoints
  - [ ] API key rotation policy

### 6.3 P5.3: Performance Optimization
**Priority: P1 | Owner: Backend | Complexity: Medium**

#### Tasks

- [ ] **Firestore Optimization**
  - [ ] Add composite indexes for common queries
  - [ ] Implement query result caching (5-min TTL)
  - [ ] Batch writes for bulk operations

- [ ] **AI Cost Optimization**
  - [ ] Cache AI responses for identical prompts (1-hour TTL)
  - [ ] Use smaller model (Gemini 1.5 Flash) for simple tasks
  - [ ] Batch AI requests where possible

- [ ] **Cold Start Reduction**
  - [ ] Min container instances: 1 (keep warm)
  - [ ] Lazy-load heavy modules
  - [ ] Optimize Docker image size

### 6.4 P5.4: Launch Checklist

- [ ] **Pre-Launch**
  - [ ] All P0 features implemented and tested
  - [ ] Staging environment validates all flows
  - [ ] Beta test with 5 real users for 1 week
  - [ ] Performance benchmarks meet targets
  - [ ] Security audit completed
  - [ ] Documentation updated (README, API docs, user guide)

- [ ] **Launch**
  - [ ] Deploy to production (Cloud Run)
  - [ ] Monitor error rates for 24 hours
  - [ ] Send announcement to all users via broadcast
  - [ ] Update website/bot description

- [ ] **Post-Launch**
  - [ ] Monitor NPS scores weekly
  - [ ] Track feature adoption rates
  - [ ] Respond to user feedback within 24 hours
  - [ ] Iterate based on first 100 user sessions

---

## 7. Cross-Cutting Concerns

### 7.1 Schema Migration Strategy

Every schema change must follow this pattern:

1. **Add new fields** with defaults (backward compatible)
2. **Deploy code** that writes to new fields
3. **Run migration script** to backfill old data
4. **Update code** to read from new fields
5. **(Optional) Remove old fields** after 30 days

### 7.2 Feature Flags

All new features should be behind feature flags:

```python
# src/config/settings.py

class Settings(BaseModel):
    # ... existing settings ...
    
    # Feature flags
    ENABLE_CONTINUOUS_DATA: bool = False
    ENABLE_MORNING_BRIEFING: bool = False
    ENABLE_ADAPTIVE_CHECKIN: bool = False
    ENABLE_CHURN_PREDICTION: bool = False
    ENABLE_CONSTITUTION_EDITOR: bool = False
    ENABLE_GOALS: bool = False
    ENABLE_PARTNER_CHALLENGES: bool = False
    ENABLE_COHORTS: bool = False
    ENABLE_INSIGHTS_ENGINE: bool = False
    ENABLE_MOOD_TRACKING: bool = False
    ENABLE_PREDICTIVE_INTERVENTIONS: bool = False
    ENABLE_PROGRESSIVE_ONBOARDING: bool = False
    ENABLE_STREAK_RECOVERY: bool = False
    ENABLE_FEATURE_HINTS: bool = False
    ENABLE_FEEDBACK: bool = False
```

Enable features progressively:
- Week 1-2: Internal testing (flags ON for admin only)
- Week 3-4: Beta users (flags ON for 10% of users)
- Week 5+: General availability (flags ON for all)

### 7.3 Cost Impact Analysis

| Feature | Additional Monthly Cost (10 users) | Driver |
|---------|-----------------------------------|--------|
| Continuous data capture | $0 | No new API calls |
| Morning briefing | $0.02 | 30 extra tokens/user/day |
| Adaptive check-in | $0 | No new API calls |
| Churn prediction | $0.01 | 10 extra tokens/user/week |
| Constitution editor | $0 | No new API calls |
| Goals | $0 | No new API calls |
| Partner challenges | $0 | No new API calls |
| Cohorts | $0 | No new API calls |
| Insights engine | $0.05 | 50 extra tokens/user/week |
| Mood tracking | $0.01 | 10 extra tokens/user/day |
| Predictive interventions | $0.03 | 30 extra tokens/user/week |
| Progressive onboarding | $0 | No new API calls |
| Streak recovery | $0 | No new API calls |
| Feature hints | $0 | No new API calls |
| Feedback system | $0 | No new API calls |
| **Total** | **~$0.12/month** | Negligible at scale |

### 7.4 Documentation Requirements

- [ ] Update `README.md` with new features
- [ ] Update `PRODUCT_GUIDE.md` with user-facing changes
- [ ] Update `TECHNICAL_ARCHITECTURE.md` with new services
- [ ] Create `USER_GUIDE_V2.md` for end users
- [ ] Update API documentation (if any public APIs)
- [ ] Create `MIGRATION_GUIDE.md` for existing users

---

## 8. Testing Strategy

### 8.1 Unit Tests

Every new module must have > 80% coverage:

- [ ] `src/services/briefing_service.py`
- [ ] `src/services/churn_prediction.py`
- [ ] `src/services/insights_engine.py`
- [ ] `src/services/goal_service.py`
- [ ] `src/services/challenge_service.py`
- [ ] `src/services/cohort_service.py`
- [ ] `src/services/predictive_intervention.py`
- [ ] `src/services/feature_discovery.py`
- [ ] `src/services/feedback_service.py`
- [ ] `src/services/admin_dashboard.py`

### 8.2 Integration Tests

- [ ] Full check-in flow (all adaptive branches)
- [ ] Morning briefing generation + delivery
- [ ] Streak break → recovery ritual
- [ ] Partner challenge lifecycle
- [ ] Cohort matching + group report
- [ ] Constitution edit → AI feedback references new text

### 8.3 End-to-End Tests

- [ ] New user onboarding → first check-in → weekly report
- [ ] At-risk user → churn prediction → intervention → retention
- [ ] Streak break → recovery → comeback achievement
- [ ] Partner challenge → completion → celebration

### 8.4 Performance Tests

- [ ] 1000 concurrent check-ins
- [ ] Cron endpoints under load
- [ ] Firestore query performance (p95 < 200ms)
- [ ] AI response time (p95 < 3s)

---

## 9. Risk Register

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Continuous data capture increases check-in abandonment | Medium | High | A/B test with control group; add simple mode toggle |
| Morning briefing feels spammy | Medium | Medium | Make opt-in; limit to 3x/week initially |
| AI costs exceed budget | Low | Medium | Cache responses; use smaller model; set daily spend limits |
| Firestore migration fails | Low | High | Backup before migration; test on staging; rollback script ready |
| Cohort matching creates toxic groups | Medium | Medium | Manual approval for first cohorts; leave button always available |
| Predictive interventions are inaccurate | Medium | Low | Start with high-confidence predictions only; A/B test |
| Feature overload confuses users | Medium | Medium | Progressive disclosure; feature hints; optional advanced mode |
| Security vulnerability in data export | Low | High | Encrypt exports; expire links; audit access logs |

---

## 10. Appendix: Schema Migrations

### Migration 1: Binary → Continuous Data

```python
# scripts/migrate_v1_to_v2.py
"""
Migration: Add continuous data fields to existing check-ins.

Run: python scripts/migrate_v1_to_v2.py
"""

from src.services.firestore_service import firestore_service
from src.models.schemas import DailyCheckIn

def migrate_checkins():
    """Backfill sleep_hours, deep_work_hours for all existing check-ins."""
    users = firestore_service.get_all_users()
    
    for user in users:
        checkins = firestore_service.get_all_checkins(user.user_id)
        
        for checkin in checkins:
            # Only migrate if hours fields are missing
            if checkin.tier1_non_negotiables.sleep_hours is None:
                # Estimate from boolean
                estimated_hours = 7.5 if checkin.tier1_non_negotiables.sleep else 5.5
                checkin.tier1_non_negotiables.sleep_hours = estimated_hours
                
                # Mark as estimated
                checkin.data_quality = "estimated"
            
            # Save back to Firestore
            firestore_service.update_checkin(checkin)
    
    print(f"Migrated {len(checkins)} check-ins")

if __name__ == "__main__":
    migrate_checkins()
```

### Migration 2: Add User Settings

```python
# scripts/migrate_add_user_settings.py

def migrate_user_settings():
    """Add settings dict to existing users."""
    users = firestore_service.get_all_users()
    
    for user in users:
        if not hasattr(user, 'settings') or user.settings is None:
            user.settings = {
                "morning_briefing_enabled": True,
                "predictive_interventions_enabled": True,
                "feature_hints_enabled": True,
                "onboarding_completed": True,  # Existing users
            }
            firestore_service.update_user(user)
    
    print(f"Updated {len(users)} users")
```

### Migration 3: Create Constitution Documents

```python
# scripts/migrate_create_constitutions.py

def migrate_constitutions():
    """Create Constitution documents for existing users from hardcoded defaults."""
    from src.services.constitution_service import DEFAULT_CONSTITUTION
    
    users = firestore_service.get_all_users()
    
    for user in users:
        constitution = Constitution(
            user_id=user.user_id,
            principles=[
                ConstitutionPrinciple(
                    principle_id="physical_sovereignty",
                    title="Physical Sovereignty",
                    description=DEFAULT_CONSTITUTION["physical_sovereignty"],
                    tier="tier1",
                    created_at=datetime.utcnow(),
                ),
                # ... other principles ...
            ],
            career_goals={
                "target_salary": "₹28-42 LPA",
                "target_date": "2026-06",
            },
            updated_at=datetime.utcnow(),
        )
        
        firestore_service.create_constitution(constitution)
    
    print(f"Created {len(users)} constitutions")
```

---

## Master Implementation Checklist

### Phase 1: Data Depth & Core Loop (Weeks 1-6)

- [ ] **P1.1: Continuous Data Capture**
  - [ ] Update `Tier1NonNegotiables` schema with required continuous fields
  - [ ] Update check-in conversation flow (Q1) with numeric inputs
  - [ ] Update pattern detection to use real data
  - [ ] Update AI feedback prompts to reference actual hours
  - [ ] Update analytics service for distributions/averages
  - [ ] Create migration script for existing check-ins
  - [ ] Write tests

- [ ] **P1.2: Morning Briefing**
  - [ ] Create `briefing_service.py`
  - [ ] Add `/cron/morning_briefing` endpoint
  - [ ] Add timezone-aware scheduling
  - [ ] Add `/briefing` on-demand command
  - [ ] Add `/settings` toggle
  - [ ] Write tests

- [ ] **P1.3: Adaptive Check-In**
  - [ ] Implement branching logic in conversation handler
  - [ ] Add power user detection
  - [ ] Add struggling user detection
  - [ ] Skip challenges for perfect days
  - [ ] Write tests

- [ ] **P1.4: Churn Prediction**
  - [ ] Create `churn_prediction.py` with risk scoring
  - [ ] Create `churn_intervention.py` with graduated messages
  - [ ] Add `/cron/churn_prevention` endpoint
  - [ ] Add churn metrics to admin dashboard
  - [ ] Write tests

### Phase 2: Constitution & Social (Weeks 7-10)

- [ ] **P2.1: Interactive Constitution**
  - [ ] Create `Constitution` and `ConstitutionPrinciple` models
  - [ ] Refactor `constitution_service.py` for user-specific constitutions
  - [ ] Add `/constitution`, `/constitution_edit`, `/constitution_add` commands
  - [ ] Update AI agents to reference user's constitution
  - [ ] Create migration script
  - [ ] Write tests

- [ ] **P2.2: Goal Setting**
  - [ ] Create `Goal` model
  - [ ] Create `goal_service.py`
  - [ ] Add `/goals`, `/goal_new`, `/goal_progress` commands
  - [ ] Auto-update goals from check-ins
  - [ ] Add goal achievements
  - [ ] Write tests

- [ ] **P2.3: Partner Challenges**
  - [ ] Create `PartnerChallenge` model
  - [ ] Create `challenge_service.py`
  - [ ] Add `/challenge` command with invite flow
  - [ ] Add daily progress updates
  - [ ] Add challenge completion celebration
  - [ ] Write tests

- [ ] **P2.4: Cohorts**
  - [ ] Create `Cohort` and `CohortInvitation` models
  - [ ] Create `cohort_service.py` with matching algorithm
  - [ ] Add `/cohort`, `/cohort_status`, `/leave_cohort` commands
  - [ ] Add weekly cohort reports
  - [ ] Write tests

### Phase 3: Intelligence & Insights (Weeks 11-14)

- [ ] **P3.1: Insights Engine**
  - [ ] Create `insights_engine.py`
  - [ ] Implement day-of-week analysis
  - [ ] Implement correlation analysis
  - [ ] Implement risk window detection
  - [ ] Integrate into weekly reports
  - [ ] Add `/insights` command
  - [ ] Write tests

- [ ] **P3.2: Mood & Energy Tracking**
  - [ ] Add `energy_rating` and `mood_rating` to `CheckInResponses`
  - [ ] Add Q5 to check-in conversation
  - [ ] Implement correlation calculations
  - [ ] Add mood trend to weekly reports
  - [ ] Write tests

- [ ] **P3.3: Predictive Interventions**
  - [ ] Create `predictive_intervention.py`
  - [ ] Implement tomorrow risk prediction
  - [ ] Add `/cron/predictive_intervention` endpoint
  - [ ] Add preventive action suggestions
  - [ ] Write tests

### Phase 4: Scale & Polish (Weeks 15-18)

- [ ] **P4.1: Progressive Onboarding**
  - [ ] Create `onboarding.py` with 5-step flow
  - [ ] Replace `/start` handler
  - [ ] Add "locked" dashboard until first check-in
  - [ ] Write tests

- [ ] **P4.2: Streak Recovery**
  - [ ] Create `streak_recovery.py`
  - [ ] Add recovery ritual on streak break
  - [ ] Add break reason collection
  - [ ] Add break pattern analysis
  - [ ] Write tests

- [ ] **P4.3: Feature Discovery**
  - [ ] Create `feature_discovery.py`
  - [ ] Implement contextual hint triggers
  - [ ] Add hint suppression settings
  - [ ] Write tests

- [ ] **P4.4: User Feedback**
  - [ ] Create `Feedback` model
  - [ ] Create `feedback_service.py`
  - [ ] Add `/feedback` command
  - [ ] Add `/cron/weekly_nps` endpoint
  - [ ] Write tests

- [ ] **P4.5: Admin Dashboard**
  - [ ] Create `admin_dashboard.py`
  - [ ] Add retention metrics
  - [ ] Add user health scores
  - [ ] Add feature usage rates
  - [ ] Add cost breakdown
  - [ ] Write tests

### Phase 5: Hardening & Launch (Weeks 19-20)

- [ ] **Testing**
  - [ ] Unit tests for all new modules (>80% coverage)
  - [ ] Integration tests for all user flows
  - [ ] Load tests with 1000 users
  - [ ] Chaos tests for failure scenarios
  - [ ] Snapshot tests for AI prompts

- [ ] **Security**
  - [ ] Encrypt data exports
  - [ ] Add `/delete_my_data` command
  - [ ] Audit AI prompts for PII
  - [ ] Implement rate limiting

- [ ] **Performance**
  - [ ] Add Firestore indexes
  - [ ] Implement caching
  - [ ] Optimize AI costs
  - [ ] Reduce cold start time

- [ ] **Launch**
  - [ ] Deploy to staging
  - [ ] Beta test with 5 users
  - [ ] Deploy to production
  - [ ] Monitor for 24 hours
  - [ ] Send announcement broadcast
  - [ ] Update documentation

---

## Document Control

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 1.0 | 2026-05-05 | Product Review | Initial comprehensive implementation plan |

**Next Review:** After Phase 1 completion (Week 6)
