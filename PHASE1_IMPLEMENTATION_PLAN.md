# Phase 1 Implementation Plan: Data Depth & Core Loop
## Accountability Agent v2.0 — Sprint 1

**Status:** Planning Complete | Awaiting Approval  
**Timeline:** 6 Weeks (Weeks 1–6)  
**Features:** 4 Major Deliverables  
**Last Updated:** 2026-05-05

---

## Table of Contents

1. [Sprint Overview](#1-sprint-overview)
2. [P1.1: Continuous Data Capture](#2-p11-continuous-data-capture-weeks-1-2)
3. [P1.2: Morning Briefing](#3-p12-morning-briefing-weeks-3-4)
4. [P1.3: Adaptive Check-In Flow](#4-p13-adaptive-check-in-flow-week-5)
5. [P1.4: Churn Risk Prediction](#5-p14-churn-risk-prediction-week-6)
6. [Cross-Cutting Tasks](#6-cross-cutting-tasks)
7. [Testing Strategy](#7-testing-strategy)
8. [Risk Mitigation](#8-risk-mitigation)
9. [Master Checklist](#9-master-checklist)

---

## 1. Sprint Overview

### 1.1 Goal

Transform the Accountability Agent from a binary tracker into a **data-rich, intelligent system** that captures continuous metrics, closes feedback loops, adapts to user behavior, and predicts churn before it happens.

### 1.2 Success Criteria

| Metric | Baseline | Target | Measurement Method |
|--------|----------|--------|-------------------|
| Check-in data depth | 6 booleans | 6 booleans + 3 continuous metrics + 1 intensity scale | Schema validation |
| Feedback loop closure | 0% (tomorrow's priorities never referenced) | 100% (referenced in next-day briefing) | Manual inspection of briefing messages |
| Check-in completion time (power users) | 3-4 min | < 2 min | Log `duration_seconds` |
| Churn prediction accuracy | N/A | 80% of churned users flagged before day 3 of inactivity | Backtest on historical data |
| Test coverage for new code | N/A | > 80% | `pytest --cov` |

### 1.3 Implementation Sequence

| Week | Feature | Focus |
|------|---------|-------|
| 1 | P1.1 | Schema migration, conversation flow update, pattern detection refactor |
| 2 | P1.1 | Analytics update, visualization update, data migration script, tests |
| 3 | P1.2 | Briefing service, cron endpoint, timezone scheduling |
| 4 | P1.2 | On-demand command, settings toggle, integration tests |
| 5 | P1.3 + P1.4 | Adaptive branching, churn prediction model, intervention messages |
| 6 | P1.3 + P1.4 | Integration tests, load tests, staging validation, bug fixes |

### 1.4 Principles for This Sprint

1. **Backward compatibility is non-negotiable** — existing users must not be broken
2. **Every new data point must be used** — if we capture it, something must consume it within the same feature
3. **Graceful degradation** — if AI fails, hardcoded fallbacks must work
4. **Test-first for critical paths** — check-in flow, briefing generation, churn scoring

---

## 2. P1.1: Continuous Data Capture (Weeks 1-2)

### 2.1 Problem Statement

The system asks "Did you sleep 7+ hours? (Y/N)" but never captures actual hours. This causes:
- **Fabricated data in pattern detection** (`7.5 if compliant else 5.5`)
- **Generic AI feedback** (can't say "you averaged 6.2 hours this week")
- **Shallow analytics** (binary completion rates instead of meaningful distributions)
- **Unused schema fields** (`sleep_hours`, `deep_work_hours` exist but are never populated)

### 2.2 User Experience

#### Before (Binary)
```
Bot: "😴 Sleep: 7+ hours today?"
[Yes] [No]
→ Stores: sleep=True/False
```

#### After (Continuous with Buttons)
```
Bot: "😴 How many hours did you sleep last night?"
[6] [6.5] [7] [7.5] [8] [8.5] [9] [Other]
→ User taps "7.5"
→ Bot: "✅ Target met! 7.5 hours"
→ Stores: sleep_hours=7.5, sleep=True (computed)

Bot: "💼 Deep Work: How many focused hours today?"
[0] [0.5] [1] [1.5] [2] [2.5] [3] [3.5] [4] [More]
→ User taps "2.5"
→ Bot: "✅ Target met! 2.5 hours"
→ Stores: deep_work_hours=2.5, deep_work=True (computed)

Bot: "📚 Skill Building: How many hours today?"
[0] [0.5] [1] [1.5] [2] [2.5] [3] [More]
→ User taps "1.5"
→ Bot: "⚠️ Below 2h target, but still solid."
→ Stores: skill_building_hours=1.5, skill_building=False (computed)

Bot: "🏋️ Training: What did you do today?"
[Rest Day] [Light] [Moderate] [Intense]
→ User taps "Moderate"
→ Bot: "💪 Nice work!"
→ Stores: training=True, training_intensity="moderate"
```

### 2.3 Technical Design

#### 2.3.1 Schema Changes

**File:** `src/models/schemas.py`

```python
class Tier1NonNegotiables(BaseModel):
    """
    Tier 1 non-negotiables with continuous data capture.
    
    Backward Compatibility:
    - Boolean fields remain as computed properties
    - Old code reading 'tier1.sleep' continues to work
    - New code can access 'tier1.sleep_hours' for deeper insights
    """
    
    # ===== Continuous Metrics (NEW — Primary Data) =====
    sleep_hours: float = Field(..., ge=0, le=16, description="Actual hours slept")
    deep_work_hours: float = Field(..., ge=0, le=16, description="Actual focused hours")
    skill_building_hours: float = Field(..., ge=0, le=16, description="Actual learning hours")
    
    # ===== Training Intensity (NEW) =====
    training_intensity: str = Field(
        ..., 
        pattern="^(rest|light|moderate|intense)$",
        description="Training intensity level"
    )
    
    # ===== Legacy Boolean Fields (RETAINED — Computed) =====
    @property
    def sleep(self) -> bool:
        """Did user meet 7+ hour sleep target?"""
        return self.sleep_hours >= 7.0
    
    @property
    def deep_work(self) -> bool:
        """Did user meet 2+ hour deep work target?"""
        return self.deep_work_hours >= 2.0
    
    @property
    def skill_building(self) -> bool:
        """Did user meet 2+ hour skill building target?"""
        return self.skill_building_hours >= 2.0
    
    @property
    def training(self) -> bool:
        """Did user train today? (rest counts as planned)"""
        return True  # Any selection means they tracked it
    
    # ===== Optional Detail Fields (EXISTING — Unchanged) =====
    is_rest_day: bool = False
    training_type: Optional[str] = None
    skill_building_activity: Optional[str] = None
    zero_porn: bool
    boundaries: bool
    
    # ===== Data Quality Flag (NEW) =====
    data_quality: str = Field(default="actual", description="actual | estimated | migrated")
```

**Migration Impact:**
- Old check-ins: `data_quality="migrated"`, hours backfilled from boolean
- New check-ins: `data_quality="actual"`, hours from user input
- Future estimates (if any): `data_quality="estimated"`

#### 2.3.2 Conversation Flow Changes

**File:** `src/bot/conversation.py`

The Q1_TIER1 state will be expanded from 6 boolean questions to 4 continuous + 2 boolean questions:

```python
# Q1_TIER1 state handler (pseudocode)

async def q1_tier1_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Q1: Collect Tier 1 metrics with continuous data.
    
    Flow:
    1. Sleep hours (buttons: 6, 6.5, 7, 7.5, 8, 8.5, 9, Other)
    2. Deep work hours (buttons: 0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, More)
    3. Skill building hours (buttons: 0, 0.5, 1, 1.5, 2, 2.5, 3, More)
    4. Training intensity (buttons: Rest Day, Light, Moderate, Intense)
    5. Zero porn (buttons: Yes, No)
    6. Boundaries (buttons: Yes, No)
    """
    
    step = context.user_data.get("tier1_step", 0)
    tier1_data = context.user_data.get("tier1_data", {})
    
    steps = [
        ("sleep", "😴 How many hours did you sleep last night?", 
         ["6", "6.5", "7", "7.5", "8", "8.5", "9", "Other"]),
        ("deep_work", "💼 How many focused deep work hours today?",
         ["0", "0.5", "1", "1.5", "2", "2.5", "3", "3.5", "4", "More"]),
        ("skill_building", "📚 How many skill building hours today?",
         ["0", "0.5", "1", "1.5", "2", "2.5", "3", "More"]),
        ("training", "🏋️ What training did you do today?",
         ["Rest Day", "Light", "Moderate", "Intense"]),
        ("zero_porn", "🚫 Zero porn maintained?", ["Yes", "No"]),
        ("boundaries", "🛡️ Healthy boundaries maintained?", ["Yes", "No"]),
    ]
    
    if step < len(steps):
        metric, question, options = steps[step]
        
        # Build inline keyboard
        keyboard = []
        row = []
        for opt in options:
            row.append(InlineKeyboardButton(opt, callback_data=f"tier1_{metric}_{opt}"))
            if len(row) == 4:  # 4 buttons per row
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        
        await update.callback_query.message.reply_text(
            question,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
        context.user_data["tier1_step"] = step + 1
        return Q1_TIER1
    else:
        # All steps complete, build Tier1NonNegotiables
        tier1 = Tier1NonNegotiables(
            sleep_hours=tier1_data["sleep"],
            deep_work_hours=tier1_data["deep_work"],
            skill_building_hours=tier1_data["skill_building"],
            training_intensity=tier1_data["training"].lower(),
            zero_porn=tier1_data["zero_porn"] == "Yes",
            boundaries=tier1_data["boundaries"] == "Yes",
            data_quality="actual",
        )
        context.user_data["tier1"] = tier1
        return Q2_CHALLENGES
```

#### 2.3.3 Pattern Detection Refactor

**File:** `src/agents/pattern_detection.py`

```python
def _detect_sleep_degradation(self, checkins: List[DailyCheckIn]) -> Optional[Pattern]:
    """
    Detect: <6 hours sleep for 3+ consecutive nights.
    
    OLD: Used fabricated estimates (7.5 if compliant else 5.5)
    NEW: Uses actual sleep_hours from check-ins
    """
    if len(checkins) < 3:
        return None
    
    # Collect actual sleep data from last 3 check-ins
    sleep_data = []
    for c in checkins[-3:]:
        hours = c.tier1_non_negotiables.sleep_hours
        if hours is not None:
            sleep_data.append((c.date, hours))
    
    if len(sleep_data) < 3:
        return None  # Insufficient actual data
    
    # Check if all 3 are <6 hours
    low_sleep_nights = [(d, h) for d, h in sleep_data if h < 6]
    
    if len(low_sleep_nights) >= 3:
        avg_sleep = sum(h for _, h in sleep_data) / len(sleep_data)
        dates = [d for d, _ in sleep_data]
        
        return Pattern(
            type="sleep_degradation",
            severity="high",
            detected_at=datetime.utcnow(),
            data={
                "avg_sleep_hours": round(avg_sleep, 1),
                "actual_values": sleep_data,  # REAL DATA: [("2026-05-01", 5.2), ...]
                "consecutive_days": 3,
                "threshold": 6,
                "dates": dates,
                "data_quality": "actual",  # NEW: Track data provenance
            }
        )
    
    return None
```

**Additional pattern updates:**
- `_detect_deep_work_collapse`: Use `deep_work_hours` instead of boolean
- `_detect_training_abandonment`: Use `training_intensity` — skip "rest" days, count "light/moderate/intense"
- `_detect_compliance_decline`: No change (already uses compliance_score)

#### 2.3.4 AI Feedback Prompt Update

**File:** `src/agents/checkin_agent.py`

```python
# In _build_feedback_prompt():

# OLD (generic):
# "Sleep: {'✅' if tier1.sleep else '❌'} (7+ hours)"

# NEW (specific):
prompt += f"""
<b>Tier 1 Results (Actual Data):</b>
• Sleep: {tier1.sleep_hours}h {'✅' if tier1.sleep else '❌'} (Target: 7h)
• Deep Work: {tier1.deep_work_hours}h {'✅' if tier1.deep_work else '❌'} (Target: 2h)
• Skill Building: {tier1.skill_building_hours}h {'✅' if tier1.skill_building else '❌'} (Target: 2h)
• Training: {tier1.training_intensity.title()} {'✅' if tier1.training else '❌'}
• Zero Porn: {'✅' if tier1.zero_porn else '❌'}
• Boundaries: {'✅' if tier1.boundaries else '❌'}

<b>Recent Averages (7 days):</b>
• Sleep: {recent_avg_sleep:.1f}h/day
• Deep Work: {recent_avg_deep_work:.1f}h/day
• Skill Building: {recent_avg_skill_building:.1f}h/day
"""
```

#### 2.3.5 Analytics Service Update

**File:** `src/services/analytics_service.py`

```python
def _calculate_tier1_stats(checkins: List[DailyCheckIn]) -> Dict[str, Any]:
    """
    Calculate Tier 1 stats with continuous data.
    
    Returns both completion rates AND averages.
    """
    stats = {}
    
    # Sleep
    sleep_hours_list = [c.tier1_non_negotiables.sleep_hours for c in checkins if c.tier1_non_negotiables.sleep_hours is not None]
    if sleep_hours_list:
        stats["sleep"] = {
            "days": sum(1 for h in sleep_hours_list if h >= 7),
            "total": len(sleep_hours_list),
            "pct": (sum(1 for h in sleep_hours_list if h >= 7) / len(sleep_hours_list)) * 100,
            "avg_hours": sum(sleep_hours_list) / len(sleep_hours_list),
            "min_hours": min(sleep_hours_list),
            "max_hours": max(sleep_hours_list),
        }
    
    # Deep Work
    dw_hours_list = [c.tier1_non_negotiables.deep_work_hours for c in checkins if c.tier1_non_negotiables.deep_work_hours is not None]
    if dw_hours_list:
        stats["deep_work"] = {
            "days": sum(1 for h in dw_hours_list if h >= 2),
            "total": len(dw_hours_list),
            "pct": (sum(1 for h in dw_hours_list if h >= 2) / len(dw_hours_list)) * 100,
            "avg_hours": sum(dw_hours_list) / len(dw_hours_list),
            "min_hours": min(dw_hours_list),
            "max_hours": max(dw_hours_list),
        }
    
    # Skill Building
    sb_hours_list = [c.tier1_non_negotiables.skill_building_hours for c in checkins if c.tier1_non_negotiables.skill_building_hours is not None]
    if sb_hours_list:
        stats["skill_building"] = {
            "days": sum(1 for h in sb_hours_list if h >= 2),
            "total": len(sb_hours_list),
            "pct": (sum(1 for h in sb_hours_list if h >= 2) / len(sb_hours_list)) * 100,
            "avg_hours": sum(sb_hours_list) / len(sb_hours_list),
            "min_hours": min(sb_hours_list),
            "max_hours": max(sb_hours_list),
        }
    
    return stats
```

#### 2.3.6 Data Migration Script

**File:** `scripts/migrate_v1_to_v2_continuous_data.py`

```python
#!/usr/bin/env python3
"""
One-time migration: Backfill continuous data from binary fields.

Run: python scripts/migrate_v1_to_v2_continuous_data.py

Safety:
- Dry-run mode by default (set DRY_RUN=False to execute)
- Backs up affected documents before modification
- Logs all changes
"""

import os
import sys
from pathlib import Path
from datetime import datetime

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.services.firestore_service import firestore_service
from src.models.schemas import DailyCheckIn
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DRY_RUN = True  # Set to False to execute

# Estimation rules for migration
ESTIMATES = {
    "sleep": {"compliant": 7.5, "non_compliant": 5.5},
    "deep_work": {"compliant": 2.5, "non_compliant": 0.5},
    "skill_building": {"compliant": 2.5, "non_compliant": 0.5},
}


def migrate_checkins():
    """Backfill sleep_hours, deep_work_hours, skill_building_hours, training_intensity."""
    
    users = firestore_service.get_all_users()
    total_migrated = 0
    total_skipped = 0
    
    for user in users:
        checkins = firestore_service.get_all_checkins(user.user_id)
        
        for checkin in checkins:
            tier1 = checkin.tier1_non_negotiables
            modified = False
            
            # Migrate sleep_hours
            if tier1.sleep_hours is None:
                tier1.sleep_hours = ESTIMATES["sleep"]["compliant"] if tier1.sleep else ESTIMATES["sleep"]["non_compliant"]
                modified = True
            
            # Migrate deep_work_hours
            if tier1.deep_work_hours is None:
                tier1.deep_work_hours = ESTIMATES["deep_work"]["compliant"] if tier1.deep_work else ESTIMATES["deep_work"]["non_compliant"]
                modified = True
            
            # Migrate skill_building_hours
            if tier1.skill_building_hours is None:
                tier1.skill_building_hours = ESTIMATES["skill_building"]["compliant"] if tier1.skill_building else ESTIMATES["skill_building"]["non_compliant"]
                modified = True
            
            # Migrate training_intensity
            if not hasattr(tier1, 'training_intensity') or tier1.training_intensity is None:
                if tier1.is_rest_day:
                    tier1.training_intensity = "rest"
                elif tier1.training:
                    tier1.training_intensity = "moderate"  # Default assumption
                else:
                    tier1.training_intensity = "rest"  # If not trained, assume rest
                modified = True
            
            # Set data quality flag
            if modified:
                tier1.data_quality = "migrated"
                total_migrated += 1
                
                if not DRY_RUN:
                    firestore_service.update_checkin(checkin)
            else:
                total_skipped += 1
    
    logger.info(f"Migration complete (DRY_RUN={DRY_RUN}):")
    logger.info(f"  Migrated: {total_migrated} check-ins")
    logger.info(f"  Skipped: {total_skipped} check-ins (already had data)")
    
    if DRY_RUN:
        logger.info("  This was a dry run. Set DRY_RUN=False to execute.")


if __name__ == "__main__":
    migrate_checkins()
```

### 2.4 Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `src/models/schemas.py` | Add continuous fields, computed properties, data_quality flag | ~40 lines |
| `src/bot/conversation.py` | Rewrite Q1_TIER1 handler with button-based continuous capture | ~80 lines |
| `src/agents/pattern_detection.py` | Use actual hours instead of estimates | ~30 lines |
| `src/agents/checkin_agent.py` | Reference actual hours in feedback prompt | ~20 lines |
| `src/services/analytics_service.py` | Calculate averages, min/max, distributions | ~50 lines |
| `src/services/visualization_service.py` | Update charts to show distributions | ~40 lines |
| `scripts/migrate_v1_to_v2_continuous_data.py` | One-time migration script | ~80 lines |
| `tests/test_schemas.py` | Validate new fields | ~30 lines |
| `tests/test_pattern_detection.py` | Update test data with real hours | ~20 lines |
| `tests/test_conversation.py` | Test new Q1 flow | ~40 lines |

### 2.5 Acceptance Criteria

- [ ] User can enter sleep hours via quick-reply buttons (6, 6.5, 7, 7.5, 8, 8.5, 9)
- [ ] User can enter deep work hours via quick-reply buttons (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4)
- [ ] User can enter skill building hours via quick-reply buttons (0, 0.5, 1, 1.5, 2, 2.5, 3)
- [ ] User selects training intensity via buttons (Rest Day, Light, Moderate, Intense)
- [ ] Pattern detection uses actual hours (not estimates)
- [ ] AI feedback references specific averages (e.g., "You averaged 6.8 hours this week")
- [ ] Analytics service shows distributions, averages, min/max — not just completion rates
- [ ] All existing check-ins migrated with `data_quality="migrated"` flag
- [ ] Existing code reading `tier1.sleep` still works (computed property)
- [ ] Backward compatibility: old check-ins without hours load successfully

---

## 3. P1.2: Morning Briefing (Weeks 3-4)

### 3.1 Problem Statement

The system captures "tomorrow's priority" and "tomorrow's obstacle" in every check-in, but:
- These answers are **never referenced again**
- Users don't get a summary of yesterday's performance
- No day-of-week context ("Tuesdays are your weakest day")
- The feedback loop is completely broken

### 3.2 User Experience

```
[8:00 AM local time]

Bot: 🌅 <b>Good morning, Ayush!</b>
     <i>Tuesday, May 6</i>

     🔥 <b>Yesterday:</b> 85% compliance
        • Sleep: 7.5h ✅
        • Deep Work: 2.5h ✅
        • Training: Skipped ❌

     🎯 <b>Your stated priority:</b> "Complete system design module"

     📊 <b>Tuesdays are historically your weakest day</b> (72% avg)

     💡 <b>Today's focus:</b> You skip training 60% of Tuesdays. 
        Schedule it for 7 AM before meetings.

     <i>/checkin when ready →</i>
```

### 3.3 Technical Design

#### 3.3.1 New Service: Briefing Service

**File:** `src/services/briefing_service.py`

```python
"""
Morning Briefing Service
=========================

Generates personalized morning briefings for users.

Trigger: Cron job at 8:00 AM local time (timezone-aware).
"""

from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from statistics import mean
import logging

from src.models.schemas import User, DailyCheckIn
from src.services.firestore_service import firestore_service
from src.utils.timezone_utils import get_current_date, get_yesterday_date, get_day_of_week

logger = logging.getLogger(__name__)


class BriefingService:
    """Generate personalized morning briefings."""
    
    def __init__(self):
        self.firestore = firestore_service
    
    async def generate_briefing(self, user: User) -> Optional[str]:
        """
        Generate morning briefing for a user.
        
        Returns None if user has disabled briefings or has no data.
        """
        # Check if enabled
        if not user.settings.get("morning_briefing_enabled", True):
            logger.info(f"Briefing disabled for user {user.user_id}")
            return None
        
        # Fetch yesterday's check-in
        yesterday = get_yesterday_date(user.timezone)
        yesterday_checkin = self.firestore.get_checkin(user.user_id, yesterday.strftime("%Y-%m-%d"))
        
        # Fetch 30-day history for patterns
        history = self.firestore.get_recent_checkins(user.user_id, days=30)
        
        # Build sections
        sections = []
        
        # Header
        today_str = get_current_date(user.timezone).strftime("%A, %B %d")
        sections.append(f"🌅 <b>Good morning, {user.name}!</b>")
        sections.append(f"<i>{today_str}</i>\n")
        
        # Yesterday's performance
        if yesterday_checkin:
            sections.append(self._format_yesterday_summary(yesterday_checkin))
        else:
            sections.append("📭 <b>Yesterday:</b> No check-in recorded\n")
        
        # Priority follow-up
        if yesterday_checkin and yesterday_checkin.responses.tomorrow_priority:
            priority = yesterday_checkin.responses.tomorrow_priority
            sections.append(f"🎯 <b>Your stated priority:</b> \"{priority}\"\n")
        
        # Day-of-week insight
        dow_insight = self._generate_dow_insight(history, user.timezone)
        if dow_insight:
            sections.append(dow_insight + "\n")
        
        # Suggestion
        suggestion = self._generate_suggestion(user, yesterday_checkin, history)
        sections.append(f"💡 <b>Today's focus:</b> {suggestion}\n")
        
        # Footer
        sections.append("<i>/checkin when ready →</i>")
        
        return "\n".join(sections)
    
    def _format_yesterday_summary(self, checkin: DailyCheckIn) -> str:
        """Format yesterday's check-in as a brief summary."""
        score = checkin.compliance_score
        emoji = "🔥" if score >= 90 else "✅" if score >= 70 else "⚠️"
        
        lines = [f"{emoji} <b>Yesterday:</b> {score:.0f}% compliance"]
        
        # Tier 1 wins (brief)
        tier1 = checkin.tier1_non_negotiables
        wins = []
        if tier1.sleep: wins.append(f"sleep ({tier1.sleep_hours}h)")
        if tier1.deep_work: wins.append(f"deep work ({tier1.deep_work_hours}h)")
        if tier1.training: wins.append(f"training ({tier1.training_intensity})")
        if tier1.skill_building: wins.append(f"skill building ({tier1.skill_building_hours}h)")
        
        if wins:
            lines.append(f"   ✅ {', '.join(wins)}")
        
        misses = []
        if not tier1.sleep: misses.append("sleep")
        if not tier1.deep_work: misses.append("deep work")
        if not tier1.training: misses.append("training")
        if not tier1.skill_building: misses.append("skill building")
        
        if misses:
            lines.append(f"   ❌ {', '.join(misses)}")
        
        return "\n".join(lines)
    
    def _generate_dow_insight(self, history: list, timezone: str) -> Optional[str]:
        """Generate day-of-week insight."""
        if len(history) < 14:  # Need at least 2 weeks of data
            return None
        
        today_dow = get_day_of_week(timezone)
        
        # Group by day of week
        dow_scores = {}
        for checkin in history:
            dow = datetime.strptime(checkin.date, "%Y-%m-%d").strftime("%A")
            if dow not in dow_scores:
                dow_scores[dow] = []
            dow_scores[dow].append(checkin.compliance_score)
        
        if today_dow not in dow_scores or len(dow_scores[today_dow]) < 2:
            return None
        
        today_avg = mean(dow_scores[today_dow])
        overall_avg = mean([s for scores in dow_scores.values() for s in scores])
        
        if today_avg >= overall_avg + 5:
            trend = "strongest"
        elif today_avg <= overall_avg - 5:
            trend = "weakest"
        else:
            return None  # No significant difference
        
        return f"📊 <b>{today_dow}s are historically your {trend} day</b> ({today_avg:.0f}% avg)"
    
    def _generate_suggestion(self, user: User, yesterday_checkin: Optional[DailyCheckIn], history: list) -> str:
        """Generate one actionable suggestion."""
        
        # If yesterday was missed, suggest getting back on track
        if yesterday_checkin is None:
            return "You missed yesterday. One check-in today restarts momentum. You've done it before."
        
        tier1 = yesterday_checkin.tier1_non_negotiables
        
        # Suggest based on yesterday's misses
        if not tier1.sleep and tier1.sleep_hours < 6:
            return "You were short on sleep. Aim for 10:30 PM bedtime tonight."
        
        if not tier1.training:
            return f"You skipped training yesterday. Schedule it for {self._suggest_training_time(history)}."
        
        if not tier1.deep_work:
            return "Protect your deep work block today. Put phone in another room."
        
        if not tier1.skill_building:
            return "Even 30 minutes of skill building counts. Block 30 min after lunch."
        
        # If perfect, suggest maintenance
        if yesterday_checkin.compliance_score == 100:
            return "Perfect day yesterday! The goal is consistency, not perfection. Keep the rhythm."
        
        return "Focus on one thing today. Small wins compound."
    
    def _suggest_training_time(self, history: list) -> str:
        """Suggest optimal training time based on history."""
        # Simple heuristic: suggest morning if user has morning check-ins
        return "7 AM before the day gets away"
```

#### 3.3.2 Cron Endpoint

**File:** `src/main.py`

```python
@app.post("/cron/morning_briefing")
async def morning_briefing(request: Request):
    """
    Send morning briefings to all users at 8:00 AM local time.
    
    Triggered by Cloud Scheduler every 15 minutes.
    Each invocation checks which timezones are currently at 8:00 AM
    and sends briefings to users in those timezones.
    """
    _verify_cron_secret(request)
    
    from src.services.briefing_service import BriefingService
    from src.utils.timezone_utils import get_timezones_at_hour
    
    briefing_service = BriefingService()
    results = {"sent": 0, "skipped": 0, "errors": 0}
    
    # Find timezones at 8:00 AM (within 15-min window)
    target_timezones = get_timezones_at_hour(8)
    logger.info(f"Sending morning briefings to timezones at 8 AM: {target_timezones}")
    
    for tz in target_timezones:
        users = firestore_service.get_users_by_timezone(tz)
        
        for user in users:
            try:
                briefing = await briefing_service.generate_briefing(user)
                
                if briefing is None:
                    results["skipped"] += 1
                    continue
                
                await bot_manager.bot.send_message(
                    chat_id=user.telegram_id,
                    text=briefing,
                    parse_mode='HTML'
                )
                
                results["sent"] += 1
                logger.info(f"Briefing sent to {user.user_id}")
                
            except Exception as e:
                logger.error(f"Failed to send briefing to {user.user_id}: {e}")
                results["errors"] += 1
    
    logger.info(f"Morning briefing complete: {results}")
    return results
```

#### 3.3.3 Timezone Utilities

**File:** `src/utils/timezone_utils.py`

```python
def get_timezones_at_hour(target_hour: int, tolerance_minutes: int = 15) -> list:
    """
    Get all supported timezones where current time is target_hour ± tolerance.
    
    Args:
        target_hour: Hour to match (0-23)
        tolerance_minutes: How many minutes before/after target_hour to include
    
    Returns:
        List of timezone strings (e.g., ["Asia/Kolkata", "Asia/Dubai"])
    """
    from pytz import timezone
    
    matched = []
    for tz_name in SUPPORTED_TIMEZONES:
        tz = timezone(tz_name)
        now = datetime.now(tz)
        
        # Check if within tolerance
        target_time = now.replace(hour=target_hour, minute=0, second=0, microsecond=0)
        diff = abs((now - target_time).total_seconds())
        
        if diff <= tolerance_minutes * 60:
            matched.append(tz_name)
    
    return matched
```

#### 3.3.4 Settings Toggle

**File:** `src/bot/telegram_bot.py`

```python
async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command."""
    user_id = str(update.effective_user.id)
    user = firestore_service.get_user(user_id)
    
    # Parse args
    args = context.args
    if len(args) >= 2 and args[0] == "morning_briefing":
        enabled = args[1].lower() in ("on", "true", "yes", "1")
        user.settings["morning_briefing_enabled"] = enabled
        firestore_service.update_user(user)
        
        status = "enabled" if enabled else "disabled"
        await update.message.reply_text(f"Morning briefing {status}.")
        return
    
    # Show current settings
    briefing_status = "✅ On" if user.settings.get("morning_briefing_enabled", True) else "❌ Off"
    
    await update.message.reply_text(
        f"⚙️ <b>Settings</b>\n\n"
        f"Morning Briefing: {briefing_status}\n"
        f"   Toggle: /settings morning_briefing off\n\n"
        f"Timezone: {user.timezone}\n"
    )
```

### 3.4 Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `src/services/briefing_service.py` | Create | ~150 lines |
| `src/main.py` | Add `/cron/morning_briefing` endpoint | ~40 lines |
| `src/utils/timezone_utils.py` | Add `get_timezones_at_hour()` | ~20 lines |
| `src/models/schemas.py` | Add `settings` dict to User | ~10 lines |
| `src/bot/telegram_bot.py` | Add `/settings` command | ~30 lines |
| `src/bot/telegram_bot.py` | Add `/briefing` on-demand command | ~20 lines |
| `tests/test_briefing_service.py` | Create unit tests | ~60 lines |
| `tests/test_main.py` | Test cron endpoint | ~30 lines |

### 3.5 Acceptance Criteria

- [ ] User receives briefing at 8:00 AM local time
- [ ] Briefing references yesterday's stated priority (from check-in responses)
- [ ] Briefing includes yesterday's Tier 1 performance with actual hours
- [ ] Briefing includes day-of-week historical context (if 14+ days of data)
- [ ] Briefing contains one actionable suggestion based on yesterday's misses
- [ ] User can disable briefings via `/settings morning_briefing off`
- [ ] User can request on-demand briefing via `/briefing`
- [ ] Briefing is skipped if user has no check-in history
- [ ] Cron job handles multiple timezones correctly
- [ ] Failed sends are logged but don't crash the batch

---

## 4. P1.3: Adaptive Check-In Flow (Week 5)

### 4.1 Problem Statement

Every user gets the same 4-question flow regardless of context:
- Power users (streak 30+, 85% compliance) still answer "what was your biggest challenge?" on perfect days
- Struggling users get the same clinical tone as everyone else
- No mid-flow save — timeout at Q3 loses all progress
- Check-in takes 3-4 minutes for everyone

### 4.2 User Experience

#### Power User (Streak 30+, 85% compliance)
```
User: /checkin
Bot: 🔥 Day 47 — let's keep the momentum!
     (Quick mode available: /quickcheckin)
     
     [🚀 Full Check-in] [⚡ Quick Check-in]
→ User taps "Full Check-in"
→ Q1: Tier 1 (continuous data, as designed)
→ Q2: "💯 Perfect day! Want to skip the challenges question?"
     [Skip → Go to Q4] [Answer Anyway]
→ Q4: Tomorrow planning (2 questions)
→ Total time: ~90 seconds
```

#### Struggling User (< 60% compliance last 7 days)
```
User: /checkin
Bot: 💪 Hey Ayush, I know it's been tough. 
     Let's take this one step at a time. Ready?
→ Q1: Tier 1 (same, but with encouraging framing)
→ Q2: Challenges (kept — they need it)
→ Q3: Rating + reason (kept)
→ Q4: Tomorrow (framed as "one small win")
→ AI feedback: Extra empathetic, focuses on one improvement
```

#### Perfect Day (100% compliance + rating >= 8)
```
→ After Q1: "💯 Perfect day! Skipping challenges question."
→ Q3: Rating (pre-filled suggestion: "10?")
→ Q4: Tomorrow planning
→ Total time: ~60 seconds
```

### 4.3 Technical Design

#### 4.3.1 Adaptive Context Detection

**File:** `src/bot/conversation.py`

```python
async def start_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Entry point with adaptive branching."""
    
    user_id = str(update.effective_user.id)
    user = firestore_service.get_user(user_id)
    
    # Calculate adaptive context
    recent_checkins = firestore_service.get_recent_checkins(user_id, days=7)
    recent_compliance = [c.compliance_score for c in recent_checkins] if recent_checkins else []
    avg_compliance = sum(recent_compliance) / len(recent_compliance) if recent_compliance else 0
    
    is_power_user = (
        user.streaks.current_streak >= 30 and
        avg_compliance >= 85
    )
    
    is_struggling = avg_compliance < 60 if recent_compliance else False
    
    # Store adaptive context
    context.user_data["adaptive_context"] = {
        "power_user": is_power_user,
        "struggling": is_struggling,
        "avg_compliance": avg_compliance,
        "recent_count": len(recent_checkins),
    }
    
    # Power user: offer quick mode
    if is_power_user:
        await update.message.reply_text(
            f"🔥 Day {user.streaks.current_streak} — let's keep the momentum!\n"
            f"(Quick mode available: /quickcheckin)",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🚀 Full Check-in", callback_data="mode_full")],
                [InlineKeyboardButton("⚡ Quick Check-in", callback_data="mode_quick")],
            ])
        )
        return Q0_MODE_SELECT
    
    # Struggling user: empathetic framing
    if is_struggling:
        await update.message.reply_text(
            f"💪 Hey {user.name}, I know it's been tough. "
            f"Let's take this one step at a time. Ready?"
        )
    
    return Q1_TIER1


async def handle_q0_mode_select(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle mode selection for power users."""
    choice = update.callback_query.data
    
    if choice == "mode_quick":
        # Redirect to quick check-in flow
        return await start_quick_checkin(update, context)
    
    # Full mode — proceed to Q1
    await update.callback_query.message.reply_text("Let's do it! 🚀")
    return Q1_TIER1


async def handle_q1_complete(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """After Q1, decide next state based on adaptive context."""
    
    adaptive = context.user_data.get("adaptive_context", {})
    tier1 = context.user_data.get("tier1")
    
    # Calculate compliance score early for adaptive branching
    compliance_score = calculate_compliance_score(tier1)
    context.user_data["compliance_score"] = compliance_score
    
    # Perfect day? Offer to skip Q2
    if compliance_score == 100:
        await update.callback_query.message.reply_text(
            "💯 Perfect day! Want to skip the challenges question?",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("Skip → Plan Tomorrow", callback_data="skip_q2")],
                [InlineKeyboardButton("Answer Anyway", callback_data="do_q2")],
            ])
        )
        return Q2_SKIP_DECISION
    
    return Q2_CHALLENGES


async def handle_q2_skip_decision(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Handle perfect-day skip decision."""
    choice = update.callback_query.data
    
    if choice == "skip_q2":
        # Skip Q2 (challenges) and Q3 (rating is auto-10)
        context.user_data["responses"] = {"rating": 10, "rating_reason": "Perfect day"}
        return Q4_TOMORROW
    
    return Q2_CHALLENGES
```

#### 4.3.2 Mid-Flow Save (Bonus)

```python
# In conversation timeout handler or periodic save

async def save_conversation_progress(context: ContextTypes.DEFAULT_TYPE):
    """
    Save conversation progress to Firestore so user can resume after timeout.
    
    Called every 2 minutes or on timeout.
    """
    user_id = context.user_data.get("user_id")
    if not user_id:
        return
    
    progress = {
        "state": context.user_data.get("current_state"),
        "tier1": context.user_data.get("tier1"),
        "responses": context.user_data.get("responses", {}),
        "adaptive_context": context.user_data.get("adaptive_context"),
        "saved_at": datetime.utcnow().isoformat(),
    }
    
    firestore_service.save_conversation_progress(user_id, progress)


async def resume_checkin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Resume check-in from saved progress."""
    user_id = str(update.effective_user.id)
    progress = firestore_service.get_conversation_progress(user_id)
    
    if progress and not is_expired(progress["saved_at"]):
        # Restore state
        context.user_data.update(progress)
        await update.message.reply_text(
            "🔄 Resuming your check-in from where you left off..."
        )
        return progress["state"]
    
    # No progress or expired — start fresh
    return await start_checkin(update, context)
```

### 4.4 Files to Modify

| File | Changes | Lines |
|------|---------|-------|
| `src/bot/conversation.py` | Add adaptive branching, Q0 mode select, Q2 skip | ~80 lines |
| `src/utils/compliance.py` | Export `calculate_compliance_score()` for early use | ~5 lines |
| `src/services/firestore_service.py` | Add conversation progress save/get | ~30 lines |
| `tests/test_conversation.py` | Test adaptive flows, skip logic | ~50 lines |

### 4.5 Acceptance Criteria

- [ ] Power users (streak ≥ 30 + 7-day compliance ≥ 85%) see mode selection (full/quick)
- [ ] Perfect days (100% compliance) offer to skip challenges question
- [ ] Struggling users (< 60% compliance) get empathetic framing
- [ ] User can force full flow even on perfect days ("Answer Anyway" button)
- [ ] Check-in completion time < 2 minutes for power users on perfect days
- [ ] Conversation progress is saved periodically (can resume after timeout)
- [ ] All adaptive branches tested with unit tests

---

## 5. P1.4: Churn Risk Prediction (Week 6)

### 5.1 Problem Statement

Users ghost silently. By the time "ghosting" pattern triggers (2+ days missed), the user has already disengaged. We need to **predict churn before it happens** and intervene preemptively.

### 5.2 User Experience

#### Medium Risk User
```
[10:00 AM, after 3 days of declining engagement]

Bot: Ayush, you've been doing great (47 days!). 
     I noticed things have been a bit harder lately.
     
     One small win today is all it takes. Ready? /checkin
```

#### High Risk User
```
[10:00 AM, after check-in time drifted 90 min later + compliance dropped 20%]

Bot: Hey Ayush, I noticed your check-ins have been slipping. 
     No judgment — life happens.
     
     Want to talk about what's getting in the way? /support
     Or just do a quick check-in to get back on track: /quickcheckin
```

### 5.3 Technical Design

#### 5.3.1 Churn Risk Predictor

**File:** `src/services/churn_prediction.py`

```python
"""
Churn Risk Prediction Service
==============================

Predicts user churn risk based on behavioral signals.

Risk factors:
- Check-in time drift (procrastination signal)
- Compliance decline (3-week trend)
- Quick check-in overuse (avoiding depth)
- Self-rating decline (disengagement signal)
- Missed reminders (ignoring system)
"""

from datetime import datetime, timedelta
from typing import Tuple, List, Dict
from statistics import mean
import logging

from src.models.schemas import User, DailyCheckIn
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


class ChurnRiskPredictor:
    """Predict user churn risk from behavioral signals."""
    
    # Risk factor weights (must sum to 1.0)
    FACTORS = {
        "checkin_time_drift": {"weight": 0.25, "threshold_minutes": 45},
        "compliance_decline": {"weight": 0.30, "threshold_points": 15},
        "quick_checkin_overuse": {"weight": 0.20, "threshold_days": 5},
        "self_rating_decline": {"weight": 0.15, "threshold_points": 2},
        "missed_reminders": {"weight": 0.10, "threshold_count": 3},
    }
    
    def calculate_risk_score(self, user: User) -> Tuple[float, List[str], Dict]:
        """
        Calculate churn risk score (0.0 to 1.0).
        
        Returns:
            (risk_score, triggered_factors, raw_data)
        """
        score = 0.0
        factors = []
        raw_data = {}
        
        # Get recent data
        checkins = firestore_service.get_recent_checkins(user.user_id, days=21)
        
        if len(checkins) < 7:
            return 0.0, [], {"insufficient_data": True}
        
        # Factor 1: Check-in time drift
        drift = self._calculate_time_drift(checkins)
        raw_data["time_drift_minutes"] = drift
        if drift > self.FACTORS["checkin_time_drift"]["threshold_minutes"]:
            score += self.FACTORS["checkin_time_drift"]["weight"]
            factors.append("checkin_time_drift")
        
        # Factor 2: Compliance decline
        decline = self._calculate_compliance_decline(checkins)
        raw_data["compliance_decline"] = decline
        if decline > self.FACTORS["compliance_decline"]["threshold_points"]:
            score += self.FACTORS["compliance_decline"]["weight"]
            factors.append("compliance_decline")
        
        # Factor 3: Quick check-in overuse
        qc_overuse = self._calculate_quick_checkin_overuse(user, checkins)
        raw_data["quick_checkin_overuse_days"] = qc_overuse
        if qc_overuse >= self.FACTORS["quick_checkin_overuse"]["threshold_days"]:
            score += self.FACTORS["quick_checkin_overuse"]["weight"]
            factors.append("quick_checkin_overuse")
        
        # Factor 4: Self-rating decline
        rating_decline = self._calculate_rating_decline(checkins)
        raw_data["rating_decline"] = rating_decline
        if rating_decline > self.FACTORS["self_rating_decline"]["threshold_points"]:
            score += self.FACTORS["self_rating_decline"]["weight"]
            factors.append("self_rating_decline")
        
        # Factor 5: Missed reminders
        # (Would need reminder tracking data)
        
        return min(score, 1.0), factors, raw_data
    
    def _calculate_time_drift(self, checkins: List[DailyCheckIn]) -> float:
        """Calculate how much later check-ins are happening (in minutes)."""
        if len(checkins) < 10:
            return 0.0
        
        # Compare first 7 days vs last 3 days
        early_times = [c.completed_at for c in checkins[:7] if c.completed_at]
        recent_times = [c.completed_at for c in checkins[-3:] if c.completed_at]
        
        if not early_times or not recent_times:
            return 0.0
        
        early_avg = mean([t.hour * 60 + t.minute for t in early_times])
        recent_avg = mean([t.hour * 60 + t.minute for t in recent_times])
        
        return recent_avg - early_avg
    
    def _calculate_compliance_decline(self, checkins: List[DailyCheckIn]) -> float:
        """Calculate compliance drop over last 3 weeks."""
        if len(checkins) < 14:
            return 0.0
        
        week1 = mean([c.compliance_score for c in checkins[:7]])
        week3 = mean([c.compliance_score for c in checkins[-7:]])
        
        return week1 - week3
    
    def _calculate_quick_checkin_overuse(self, user: User, checkins: List[DailyCheckIn]) -> int:
        """Count consecutive quick check-ins."""
        consecutive = 0
        for c in reversed(checkins):
            if c.is_quick_checkin:
                consecutive += 1
            else:
                break
        return consecutive
    
    def _calculate_rating_decline(self, checkins: List[DailyCheckIn]) -> float:
        """Calculate self-rating drop."""
        if len(checkins) < 10:
            return 0.0
        
        early_ratings = [c.responses.rating for c in checkins[:5] if hasattr(c, 'responses')]
        recent_ratings = [c.responses.rating for c in checkins[-5:] if hasattr(c, 'responses')]
        
        if not early_ratings or not recent_ratings:
            return 0.0
        
        return mean(early_ratings) - mean(recent_ratings)
```

#### 5.3.2 Churn Intervention Service

**File:** `src/services/churn_intervention.py`

```python
"""
Churn Intervention Service
===========================

Sends graduated interventions to at-risk users.

Tone: Softer than pattern interventions. These are "nudges," not "warnings."
"""

from src.models.schemas import User


async def send_churn_prevention_message(user: User, risk_score: float, factors: List[str]):
    """Send intervention based on risk score."""
    
    if risk_score >= 0.8:
        message = (
            f"Hey {user.name}, I noticed your check-ins have been slipping. "
            f"No judgment — life happens.\n\n"
            f"Want to talk about what's getting in the way? /support\n"
            f"Or just do a quick check-in to get back on track: /quickcheckin"
        )
    elif risk_score >= 0.5:
        message = (
            f"{user.name}, you've been doing great ({user.streaks.current_streak} days!). "
            f"I noticed things have been a bit harder lately.\n\n"
            f"One small win today is all it takes. Ready? /checkin"
        )
    else:
        return  # Low risk — don't message
    
    await bot_manager.bot.send_message(
        chat_id=user.telegram_id,
        text=message,
        parse_mode='HTML'
    )
```

#### 5.3.3 Cron Endpoint

**File:** `src/main.py`

```python
@app.post("/cron/churn_prevention")
async def churn_prevention(request: Request):
    """
    Daily churn prevention scan.
    
    Runs at 10:00 AM local time for each timezone.
    Identifies at-risk users and sends gentle nudges.
    """
    _verify_cron_secret(request)
    
    from src.services.churn_prediction import ChurnRiskPredictor
    from src.services.churn_intervention import send_churn_prevention_message
    
    predictor = ChurnRiskPredictor()
    results = {"scanned": 0, "at_risk": 0, "messaged": 0, "errors": 0}
    
    # Get active users (checked in within last 7 days)
    active_users = firestore_service.get_active_users(days=7)
    
    for user in active_users:
        try:
            results["scanned"] += 1
            
            # Calculate risk
            risk_score, factors, raw_data = predictor.calculate_risk_score(user)
            
            # Store risk score (internal only)
            user.churn_risk_score = risk_score
            user.last_churn_check = datetime.utcnow().isoformat()
            firestore_service.update_user(user)
            
            if risk_score >= 0.5:
                results["at_risk"] += 1
                
                # Check cooldown (don't message more than once every 3 days)
                last_intervention = user.settings.get("last_churn_intervention")
                if last_intervention and days_since(last_intervention) < 3:
                    continue
                
                # Send intervention
                await send_churn_prevention_message(user, risk_score, factors)
                
                user.settings["last_churn_intervention"] = datetime.utcnow().isoformat()
                firestore_service.update_user(user)
                
                results["messaged"] += 1
        
        except Exception as e:
            logger.error(f"Churn prevention failed for {user.user_id}: {e}")
            results["errors"] += 1
    
    return results
```

### 5.4 Files to Create/Modify

| File | Action | Lines |
|------|--------|-------|
| `src/services/churn_prediction.py` | Create | ~120 lines |
| `src/services/churn_intervention.py` | Create | ~40 lines |
| `src/main.py` | Add `/cron/churn_prevention` endpoint | ~50 lines |
| `src/models/schemas.py` | Add `churn_risk_score` (internal) to User | ~5 lines |
| `src/services/analytics_service.py` | Add churn metrics | ~20 lines |
| `tests/test_churn_prediction.py` | Unit tests with synthetic data | ~60 lines |

### 5.5 Acceptance Criteria

- [ ] Model identifies 80% of churned users before day 3 of inactivity
- [ ] False positive rate < 20% (don't annoy stable users)
- [ ] Risk scores are internal-only (not shown to users)
- [ ] Interventions sent via existing Telegram bot (softer tone than pattern interventions)
- [ ] Max 1 intervention per user every 3 days (cooldown)
- [ ] Risk scores visible in admin dashboard
- [ ] Model backtested on historical data

---

## 6. Cross-Cutting Tasks

### 6.1 Schema Migration (Week 1, Day 1)

- [ ] Backup Firestore before migration
- [ ] Run `scripts/migrate_v1_to_v2_continuous_data.py` in dry-run mode
- [ ] Review dry-run logs
- [ ] Execute migration (set `DRY_RUN=False`)
- [ ] Validate migration: sample 10 users, verify hours populated
- [ ] Run full test suite against migrated data

### 6.2 Feature Flags

All new features behind flags:

```python
# src/config/settings.py

ENABLE_CONTINUOUS_DATA: bool = True      # P1.1
ENABLE_MORNING_BRIEFING: bool = True     # P1.2
ENABLE_ADAPTIVE_CHECKIN: bool = True     # P1.3
ENABLE_CHURN_PREDICTION: bool = True     # P1.4
```

- [ ] Add flags to settings
- [ ] Wrap all new features with flag checks
- [ ] Admin endpoint to toggle flags

### 6.3 Documentation

- [ ] Update `README.md` with new features
- [ ] Update `PRODUCT_GUIDE.md` with user-facing changes
- [ ] Create `MIGRATION_GUIDE.md` for existing users
- [ ] Update `TECHNICAL_ARCHITECTURE.md` with new services

---

## 7. Testing Strategy

### 7.1 Unit Tests

| Module | Target Coverage | Key Tests |
|--------|-----------------|-----------|
| `src/models/schemas.py` (Tier1NonNegotiables) | 90% | Computed properties, validation, backward compat |
| `src/services/briefing_service.py` | 85% | Formatting, DOW insight, suggestion generation |
| `src/services/churn_prediction.py` | 85% | Risk scoring, factor detection, edge cases |
| `src/bot/conversation.py` (adaptive) | 80% | Power user path, struggling user path, perfect day skip |
| `src/agents/pattern_detection.py` | 80% | Actual hours usage, data quality handling |

### 7.2 Integration Tests

- [ ] Full check-in flow (all 3 adaptive branches)
- [ ] Morning briefing generation + simulated delivery
- [ ] Churn prediction on synthetic user histories
- [ ] Data migration script (dry-run + execution)
- [ ] Backward compatibility: old check-ins load without errors

### 7.3 Regression Tests

- [ ] All 932 existing tests pass
- [ ] `/checkin` works for existing users (no schema breakage)
- [ ] `/weekly` report generates correctly
- [ ] Pattern detection still triggers on migrated data
- [ ] AI feedback generation works with new prompt format

### 7.4 Performance Tests

- [ ] Cron endpoint `/cron/morning_briefing` handles 100 users in < 30 seconds
- [ ] Churn prediction scans 100 users in < 10 seconds
- [ ] Check-in conversation flow completes in < 3 seconds per step

---

## 8. Risk Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Continuous data capture increases check-in time | Medium | High | Button-based input (faster than typing); A/B test with 10% of users first |
| Firestore migration corrupts data | Low | Critical | Dry-run first; backup before migration; rollback script ready |
| Morning briefing feels spammy | Medium | Medium | Strictly opt-out; only sent if user has check-in history; 1 per day max |
| Churn prediction has high false positives | Medium | Low | Start conservative (only message at 0.8+ risk); monitor and tune weekly |
| Adaptive check-in confuses users | Low | Medium | Clear buttons ("Skip → Plan Tomorrow"); can always answer anyway |
| AI costs increase significantly | Low | Medium | No new AI calls in P1.1-P1.4; briefings are rule-based; churn detection is statistical |

---

## 9. Master Checklist

### Week 1: P1.1 — Schema & Conversation Flow

- [ ] **Schema Changes**
  - [ ] Update `Tier1NonNegotiables` with continuous fields
  - [ ] Add computed properties for backward compatibility
  - [ ] Add `data_quality` flag
  - [ ] Add `training_intensity` field
  - [ ] Update `User.settings` dict

- [ ] **Conversation Flow**
  - [ ] Rewrite Q1_TIER1 handler with button-based continuous capture
  - [ ] Add sleep hours buttons (6, 6.5, 7, 7.5, 8, 8.5, 9, Other)
  - [ ] Add deep work hours buttons (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, More)
  - [ ] Add skill building hours buttons (0, 0.5, 1, 1.5, 2, 2.5, 3, More)
  - [ ] Add training intensity buttons (Rest Day, Light, Moderate, Intense)
  - [ ] Update zero porn / boundaries questions (unchanged)

- [ ] **Pattern Detection**
  - [ ] Refactor `_detect_sleep_degradation` to use actual hours
  - [ ] Refactor `_detect_deep_work_collapse` to use actual hours
  - [ ] Refactor `_detect_training_abandonment` to use intensity
  - [ ] Add `data_quality` tracking to pattern data

- [ ] **AI Feedback**
  - [ ] Update `_build_feedback_prompt` to reference actual hours
  - [ ] Add 7-day averages to prompt context

- [ ] **Migration Script**
  - [ ] Create `scripts/migrate_v1_to_v2_continuous_data.py`
  - [ ] Implement dry-run mode
  - [ ] Add backup functionality
  - [ ] Test on staging data

### Week 2: P1.1 — Analytics, Viz, Tests

- [ ] **Analytics Service**
  - [ ] Update `_calculate_tier1_stats` for averages, min, max
  - [ ] Add distribution calculations
  - [ ] Update weekly/monthly/yearly stats

- [ ] **Visualization Service**
  - [ ] Update charts to show distributions (box plots, histograms)
  - [ ] Add average lines to trend charts

- [ ] **Tests**
  - [ ] Unit tests for schema validation
  - [ ] Unit tests for pattern detection with real hours
  - [ ] Unit tests for conversation flow
  - [ ] Integration test for full check-in with continuous data
  - [ ] Regression test: old check-ins load successfully

- [ ] **Migration Execution**
  - [ ] Backup production Firestore
  - [ ] Run migration in dry-run mode
  - [ ] Execute migration
  - [ ] Validate 10 sample users

### Week 3: P1.2 — Briefing Service

- [ ] **Briefing Service**
  - [ ] Create `src/services/briefing_service.py`
  - [ ] Implement `generate_briefing()`
  - [ ] Implement `_format_yesterday_summary()`
  - [ ] Implement `_generate_dow_insight()`
  - [ ] Implement `_generate_suggestion()`

- [ ] **Cron Endpoint**
  - [ ] Add `/cron/morning_briefing` to `src/main.py`
  - [ ] Implement timezone-aware scheduling
  - [ ] Add error handling and batch processing

- [ ] **Timezone Utils**
  - [ ] Add `get_timezones_at_hour()` helper
  - [ ] Add `get_day_of_week()` helper

- [ ] **Settings**
  - [ ] Add `morning_briefing_enabled` to User.settings
  - [ ] Add `/settings` command to toggle
  - [ ] Add `/briefing` on-demand command

### Week 4: P1.2 — Tests & Integration

- [ ] **Tests**
  - [ ] Unit tests for briefing generation (all branches)
  - [ ] Unit tests for DOW insight calculation
  - [ ] Unit tests for suggestion generation
  - [ ] Integration test for cron endpoint
  - [ ] Test timezone handling across DST boundaries

- [ ] **Staging Validation**
  - [ ] Deploy to staging
  - [ ] Trigger briefing manually for test users
  - [ ] Verify formatting, content, timing
  - [ ] Test opt-out flow

### Week 5: P1.3 + P1.4 — Adaptive Flow & Churn

- [ ] **Adaptive Check-In**
  - [ ] Implement power user detection (streak ≥ 30 + compliance ≥ 85%)
  - [ ] Add Q0 mode selection (full/quick)
  - [ ] Implement perfect day skip (Q2 skip)
  - [ ] Add struggling user empathetic framing
  - [ ] Add conversation progress save/resume

- [ ] **Churn Prediction**
  - [ ] Create `ChurnRiskPredictor` class
  - [ ] Implement time drift calculation
  - [ ] Implement compliance decline calculation
  - [ ] Implement quick check-in overuse detection
  - [ ] Implement self-rating decline calculation

- [ ] **Churn Intervention**
  - [ ] Create `send_churn_prevention_message()`
  - [ ] Implement graduated messaging (0.5 vs 0.8 risk)
  - [ ] Add 3-day cooldown logic

- [ ] **Cron Endpoint**
  - [ ] Add `/cron/churn_prevention` to `src/main.py`
  - [ ] Implement batch scanning
  - [ ] Store risk scores internally

### Week 6: Integration, Load Testing, Hardening

- [ ] **Integration Tests**
  - [ ] Full check-in (all adaptive branches)
  - [ ] Morning briefing + check-in data consistency
  - [ ] Churn prediction on synthetic histories
  - [ ] Conversation timeout + resume

- [ ] **Regression Tests**
  - [ ] All 932 existing tests pass
  - [ ] Old check-ins load without errors
  - [ ] `/weekly` report works with new data

- [ ] **Load Tests**
  - [ ] Morning briefing: 100 users in < 30s
  - [ ] Churn scan: 100 users in < 10s
  - [ ] Check-in flow: < 3s per step

- [ ] **Staging Validation**
  - [ ] Deploy full Phase 1 to staging
  - [ ] Run all tests
  - [ ] Fix any bugs
  - [ ] Prepare production deployment plan

- [ ] **Documentation**
  - [ ] Update README
  - [ ] Update PRODUCT_GUIDE
  - [ ] Write MIGRATION_GUIDE

---

## Approval Section

**Product Owner Approval:**

- [ ] Plan reviewed and approved
- [ ] Clarifying questions answered
- [ ] Success criteria accepted
- [ ] Timeline accepted
- [ ] Ready to begin implementation

**Approved By:** _________________  **Date:** _________________

---

*Once approved, implementation will begin with Week 1 tasks.*
