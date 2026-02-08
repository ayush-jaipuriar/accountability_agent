# P2/P3 Implementation Specification & PRD

**Date:** February 8, 2026  
**Status:** Pre-Implementation  
**Scope:** 6 features selected from product gap analysis

---

## Table of Contents

1. [Feature 1: Custom Timezone Support](#feature-1-custom-timezone-support)
2. [Feature 2: Partner Mutual Visibility](#feature-2-partner-mutual-visibility)
3. [Feature 3: Streak Recovery Encouragement](#feature-3-streak-recovery-encouragement)
4. [Feature 4: Intervention-to-Support Linking](#feature-4-intervention-to-support-linking)
5. [Feature 5: Tiered Rate Limiting](#feature-5-tiered-rate-limiting)
6. [Feature 6: Cloud-Native Monitoring & Alerting](#feature-6-cloud-native-monitoring--alerting)
7. [Implementation Order & Dependencies](#implementation-order--dependencies)
8. [File Change Map](#file-change-map)
9. [Testing Strategy](#testing-strategy)
10. [Rollback Plan](#rollback-plan)

---

## Feature 1: Custom Timezone Support

### Problem Statement

The system is hardcoded to IST (`Asia/Kolkata`). The `User.timezone` field exists but is never read. All date calculations, reminder scheduling, and check-in date assignment use IST. Non-IST users (e.g., someone in New York) get reminders at 9 PM IST (= 10:30 AM EST), and their late-night check-ins may be assigned to the wrong date.

### Current State

| Component | Current Behavior |
|-----------|-----------------|
| `User.timezone` | Defaults to `"Asia/Kolkata"`, never used |
| `timezone_utils.py` | 7 functions, ALL hardcoded to IST |
| `get_checkin_date()` | Uses IST for 3 AM cutoff rule |
| Onboarding | Shows "No, I'm in another timezone" → "coming soon" |
| Reminders | 3 global cron jobs at 21:00, 21:30, 22:00 IST |
| `get_current_date_ist()` | Used by reminders, pattern detection, streak logic |

### Design: Predefined Timezone Buttons + Bucket-Based Reminders

#### 1.1 Onboarding Timezone Selection

When user clicks "No, I'm in another timezone" during onboarding, show a **two-level menu** of common timezones:

**Level 1 — Region:**
```
🌍 Select your region:
[Americas] [Europe] [Asia/Oceania]
```

**Level 2 — Specific timezone:**

Americas:
```
🇺🇸 US Pacific (Los Angeles) — UTC-8
🇺🇸 US Mountain (Denver) — UTC-7
🇺🇸 US Central (Chicago) — UTC-6
🇺🇸 US Eastern (New York) — UTC-5
🇧🇷 Brazil (São Paulo) — UTC-3
```

Europe:
```
🇬🇧 UK (London) — UTC+0
🇫🇷 Central Europe (Paris) — UTC+1
🇫🇮 Eastern Europe (Helsinki) — UTC+2
```

Asia/Oceania:
```
🇦🇪 Gulf (Dubai) — UTC+4
🇮🇳 India (Kolkata) — UTC+5:30
🇸🇬 Singapore — UTC+8
🇯🇵 Japan (Tokyo) — UTC+9
🇦🇺 Australia East (Sydney) — UTC+11
🇳🇿 New Zealand (Auckland) — UTC+12
```

After selection, confirm:
```
✅ Timezone set to US Eastern (New York)

Your daily reminders will be at:
🔔 9:00 PM, 9:30 PM, 10:00 PM (your local time)

Your check-in day resets at 3:00 AM your time.
```

#### 1.2 `/timezone` Command (Post-Onboarding Change)

New command: `/timezone` — shows same region → timezone picker. Updates `User.timezone` in Firestore.

#### 1.3 Timezone-Aware Utility Functions

**Concept: Generalize IST functions to accept a timezone parameter.**

Every function that currently assumes IST will gain an optional `tz: str = "Asia/Kolkata"` parameter. This maintains backward compatibility (existing callers don't break) while allowing timezone-aware behavior.

| Current Function | New Signature | Change |
|-----------------|---------------|--------|
| `get_current_time_ist()` | `get_current_time(tz="Asia/Kolkata")` | Accept any IANA timezone string |
| `get_current_date_ist()` | `get_current_date(tz="Asia/Kolkata")` | Same |
| `get_checkin_date(current_time)` | `get_checkin_date(current_time, tz="Asia/Kolkata")` | 3 AM cutoff in user's timezone |
| `utc_to_ist(dt)` | `utc_to_local(dt, tz="Asia/Kolkata")` | Convert UTC to any timezone |
| `ist_to_utc(dt)` | `local_to_utc(dt, tz="Asia/Kolkata")` | Convert any timezone to UTC |
| `format_datetime_for_display(dt)` | `format_datetime_for_display(dt, tz="Asia/Kolkata")` | Display in user's timezone |
| `get_date_range_ist(days)` | `get_date_range(days, tz="Asia/Kolkata")` | Date range in user's timezone |

**Old function names kept as aliases** pointing to the new functions (so existing code doesn't break):
```python
# Backward compatibility aliases
get_current_time_ist = lambda: get_current_time("Asia/Kolkata")
get_current_date_ist = lambda: get_current_date("Asia/Kolkata")
```

#### 1.4 Bucket-Based Reminder Scheduling

**Concept:** Instead of 3 cron jobs running at IST times, create timezone buckets. Each bucket maps to a UTC hour range. Cloud Scheduler runs jobs more frequently (every 30 min), and each run checks "which buckets are due now?"

**Timezone Buckets:**

| Bucket | UTC Offset Range | Example Cities | 9PM local = UTC |
|--------|-----------------|----------------|-----------------|
| UTC-8 to UTC-5 | Americas | LA, NY | 05:00–02:00 next day |
| UTC+0 to UTC+2 | Europe | London, Paris | 21:00–19:00 |
| UTC+4 to UTC+5:30 | South Asia/Gulf | Dubai, India | 17:00–15:30 |
| UTC+8 to UTC+12 | East Asia/Oceania | Singapore, Sydney | 13:00–09:00 |

**Implementation approach:**

The 3 existing cron jobs (`/cron/reminder_first`, `second`, `third`) remain but change behavior:

1. Each cron job runs **every 30 minutes** via Cloud Scheduler (instead of once at a fixed IST time).
2. On each invocation, the endpoint:
   - Gets current UTC time
   - Calculates which timezone offsets are currently at 21:00 / 21:30 / 22:00 local time
   - Queries users whose `timezone` falls in those offsets
   - Sends reminders only to those users

```python
# Pseudocode for reminder_first (9 PM local):
async def reminder_first(request: Request):
    verify_cron_request(request)
    now_utc = datetime.now(UTC)
    
    # Which UTC offset has local time = 21:00 right now?
    # If it's 15:30 UTC → offset +5:30 has local 21:00 → India
    # If it's 02:00 UTC → offset -5 has local 21:00 → US Eastern
    target_local_hour = 21
    target_local_minute = 0
    
    # Find all timezone strings where current local time matches
    matching_timezones = get_timezones_at_local_time(now_utc, target_local_hour, target_local_minute)
    
    # Get users in those timezones who haven't checked in
    for tz in matching_timezones:
        today_for_tz = get_current_date(tz)
        users = firestore_service.get_users_without_checkin_today_in_timezone(today_for_tz, tz)
        for user in users:
            send_reminder(user, "first")
```

**Cloud Scheduler changes:**
- Change existing 3 jobs from fixed IST times to every 30 minutes
- Schedule: `*/30 * * * *` (every 30 min)
- This ensures no timezone bucket is missed by more than 30 minutes

#### 1.5 Check-in Date Assignment

The critical `get_checkin_date()` must use the user's timezone for the 3 AM cutoff:

```python
def get_checkin_date(current_time=None, tz="Asia/Kolkata"):
    """
    Determine which date a check-in counts for.
    
    Rule: Check-ins before 3 AM LOCAL TIME count for the previous day.
    This allows night-owl users to check in after midnight.
    """
    local_tz = pytz.timezone(tz)
    
    if current_time is None:
        local_now = datetime.now(local_tz)
    elif current_time.tzinfo is None:
        local_now = local_tz.localize(current_time)
    else:
        local_now = current_time.astimezone(local_tz)
    
    if local_now.hour < 3:
        checkin_date = (local_now - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        checkin_date = local_now.strftime("%Y-%m-%d")
    
    return checkin_date
```

**Where user timezone must be threaded through:**
- `src/bot/conversation.py` → `finish_checkin()` and `finish_checkin_quick()` — pass user.timezone
- `src/bot/telegram_bot.py` → `/use_shield` — pass user.timezone
- `src/services/firestore_service.py` → `use_streak_shield()` — pass user.timezone
- `src/main.py` → reminder endpoints — already handled by bucket logic
- `src/main.py` → pattern scan — use user.timezone for "today" calculation

#### 1.6 Data Model Changes

```python
# No new fields needed — User.timezone already exists
# Just need to actually USE it

# New Firestore query needed:
def get_users_without_checkin_today_in_timezone(self, date: str, timezone: str) -> list:
    """Get users in a specific timezone who haven't checked in on the given date."""
    users = self.db.collection('users').where('timezone', '==', timezone).stream()
    # ... filter by check-in status
```

#### 1.7 Acceptance Criteria

- [ ] Onboarding shows timezone picker (2-level: region → city)
- [ ] User can change timezone via `/timezone` command
- [ ] All date/time displays show user's local timezone
- [ ] Check-in date uses 3 AM cutoff in user's timezone
- [ ] Reminders arrive at ~9PM/9:30PM/10PM in user's local time
- [ ] Existing IST users are unaffected (backward compatible)
- [ ] Old function aliases still work (`get_current_time_ist()`, etc.)

---

## Feature 2: Partner Mutual Visibility

### Problem Statement

The partner system currently only provides Day 5+ ghosting alerts. Partners can't see each other's streak, compliance, or daily check-in status. The partnership feels one-directional and hollow.

### Current State

| Component | Status |
|-----------|--------|
| Partner linking (`/set_partner`) | ✅ Works, bidirectional |
| Partner unlinking (`/unlink_partner`) | ✅ Works |
| Ghosting alert (Day 5+) | ✅ Works |
| Partner status view | ❌ Not implemented |
| Mutual visibility | ❌ Not implemented |

### Design: Basic Partner Status Dashboard

#### 2.1 `/partner_status` Command

New command showing aggregate partner info (respecting privacy — NO individual Tier 1 items):

```
👥 Partner Dashboard
━━━━━━━━━━━━━━━━━━

🤝 Your partner: Meera

📊 Meera's Status Today:
  ✅ Checked in today
  📈 Compliance: 83%

🔥 Meera's Streak:
  Current: 23 days
  Longest ever: 47 days

📅 This Week:
  Check-ins: 5/7
  Avg Compliance: 87%

━━━━━━━━━━━━━━━━━━
💪 You're both showing up. Keep it going!
```

**If partner hasn't checked in yet:**
```
👥 Partner Dashboard
━━━━━━━━━━━━━━━━━━

🤝 Your partner: Meera

📊 Meera's Status Today:
  ⏳ Not yet checked in
  
🔥 Meera's Streak:
  Current: 22 days (at risk!)
  Longest ever: 47 days

📅 This Week:
  Check-ins: 4/6 (so far)
  Avg Compliance: 85%

━━━━━━━━━━━━━━━━━━
💬 Consider sending them encouragement!
```

#### 2.2 Data Flow

```
User sends /partner_status
    ↓
Bot retrieves user.accountability_partner_id
    ↓
Bot calls firestore_service.get_user(partner_id)
    ↓
Bot calls firestore_service.get_recent_checkins(partner_id, days=7)
    ↓
Bot calculates:
  - Today's check-in status (checked in or not)
  - Today's compliance % (from check-in doc)
  - Current/longest streak (from partner's User doc)
  - Weekly check-in count and avg compliance
    ↓
Bot formats message using ux.py helpers
    ↓
Sends to user (aggregate only, no individual Tier 1 items)
```

#### 2.3 Privacy Model

**Aggregate Only** — partner sees:
- ✅ Compliance score (percentage)
- ✅ Streak (current and longest)
- ✅ Check-in status (done today or not)
- ✅ Weekly averages
- ❌ Individual Tier 1 items (sleep, training, porn, etc.)
- ❌ Challenge text / rating reason
- ❌ Emotional support conversations

#### 2.4 Comparison Footer

Add a motivational comparison at the bottom:

```python
def get_partner_comparison_footer(user_streak, partner_streak, user_compliance_week, partner_compliance_week):
    if user_streak > partner_streak:
        return "🏆 You're leading the streak race! Keep the momentum."
    elif partner_streak > user_streak:
        return f"💪 {partner_name} is ahead by {partner_streak - user_streak} days. Time to catch up!"
    else:
        return "🤝 You're perfectly matched! Keep pushing together."
```

#### 2.5 New Methods Needed

```python
# firestore_service.py
def get_recent_checkins(self, user_id: str, days: int = 7) -> list[DailyCheckIn]:
    """Get last N days of check-ins for a user."""

# telegram_bot.py  
async def partner_status_command(self, update, context):
    """Handle /partner_status command."""

# ux.py
def format_partner_dashboard(partner_user, partner_checkins, user_streak):
    """Format the partner status message."""
```

#### 2.6 Acceptance Criteria

- [ ] `/partner_status` shows partner's streak, compliance %, check-in status
- [ ] No individual Tier 1 items exposed (privacy)
- [ ] Shows weekly stats (check-in count, avg compliance)
- [ ] Comparison footer with motivational framing
- [ ] Graceful handling: no partner linked, partner account deleted
- [ ] Works when partner hasn't checked in yet today

---

## Feature 3: Streak Recovery Encouragement

### Problem Statement

When a streak resets (gap ≥ 2 days), the user just sees `🔥 Streak: 1 days` with no context, no encouragement, and no acknowledgment of their previous achievement. This is demoralizing and increases dropout risk.

### Current State

| Component | Behavior |
|-----------|----------|
| Streak reset detection | ✅ `calculate_new_streak()` returns 1 |
| Reset message | ❌ Just shows "Streak: 1 days" |
| Previous best context | ❌ Not shown |
| Comeback framing | ❌ Not implemented |
| Comeback King achievement | ✅ Exists (reach 7 days after reset) |

### Design: Recovery Journey System

#### 3.1 Enhanced Streak Reset Message

When `calculate_new_streak()` detects a reset (gap ≥ 2 days), the check-in summary changes from:

**Before (current):**
```
🔥 Streak: 1 days
```

**After (new):**
```
🔄 Fresh Start!

Your previous streak: 23 days 🏆
That's still YOUR record — and you earned every day of it.

🔥 New streak: Day 1 — the comeback starts now.

💡 Did you know? Most people who reach 30+ days 
had at least one reset along the way. 
The difference? They started again.

🎯 Next milestone: 7 days → unlocks Comeback King! 🦁
```

#### 3.2 Streak Data Enhancement

Add `previous_best_streak` tracking to `UserStreaks`:

```python
class UserStreaks(BaseModel):
    current_streak: int = 0
    longest_streak: int = 0
    last_checkin_date: Optional[str] = None
    total_checkins: int = 0
    # NEW:
    streak_before_reset: int = 0  # What the streak was right before it reset
    last_reset_date: Optional[str] = None  # When the reset happened
```

When a reset occurs in `update_streak_data()`:
```python
if gap_days >= 2:
    streak_updates["streak_before_reset"] = current_streak  # Save what was lost
    streak_updates["last_reset_date"] = today
    streak_updates["current_streak"] = 1
```

#### 3.3 Recovery Milestone Messages

Special messages at key post-reset milestones:

| Day After Reset | Message |
|----------------|---------|
| Day 1 | "🔄 Fresh Start! [previous streak context + comeback framing]" |
| Day 3 | "💪 3 days strong! You're proving the reset was just a bump, not a stop." |
| Day 7 | "🦁 Comeback King! A full week back. Your resilience is your superpower." |
| Day 14 | "🔥 Two weeks! You've rebuilt half of what you had. The momentum is real." |
| Exceeds old streak | "👑 NEW RECORD! You've surpassed your previous {old} day streak! Unstoppable." |

#### 3.4 Comeback Achievement Acceleration

Currently, `Comeback King` requires reaching 7 days after a reset. Enhance with a **Comeback Series**:

| Achievement | Condition | Badge |
|------------|-----------|-------|
| Comeback Kid | 3 days after reset | 🐣 |
| Comeback King | 7 days after reset | 🦁 (existing) |
| Comeback Legend | Exceed previous best after reset | 👑 |

#### 3.5 Recovery Facts Database

Rotate motivational recovery facts:

```python
RECOVERY_FACTS = [
    "Most people who reach 30+ days had at least one reset along the way.",
    "Research shows habit formation averages 66 days — resets are part of the process.",
    "Elite athletes track 'return-to-form' time, not zero-failure streaks.",
    "A streak reset isn't starting over — it's starting from experience.",
    "The #1 predictor of long-term success? Restarting after a break.",
]
```

#### 3.6 Implementation in `streak.py`

```python
def update_streak_data(current_streak, longest_streak, last_checkin_date, today):
    # ... existing logic ...
    
    if gap_days >= 2:
        # RESET — add recovery context
        return {
            "current_streak": 1,
            "longest_streak": longest_streak,
            "streak_before_reset": current_streak,  # NEW
            "last_reset_date": today,                # NEW
            "is_reset": True,                        # NEW flag
            "recovery_fact": random.choice(RECOVERY_FACTS),  # NEW
        }
    else:
        return {
            "current_streak": new_streak,
            "longest_streak": max(new_streak, longest_streak),
            "is_reset": False,
        }
```

#### 3.7 Acceptance Criteria

- [ ] Streak reset shows previous streak context ("Your previous streak: 23 days")
- [ ] Comeback framing instead of bare "Streak: 1 days"
- [ ] Random recovery fact shown on reset
- [ ] `streak_before_reset` and `last_reset_date` stored in Firestore
- [ ] Recovery milestone messages at days 3, 7, 14, and "exceeds previous"
- [ ] Comeback Kid (3 days) and Comeback Legend (exceeds previous) achievements added
- [ ] Existing Comeback King (7 days) achievement unchanged

---

## Feature 4: Intervention-to-Support Linking

### Problem Statement

The intervention agent sends pattern-detected warnings (e.g., "Sleep degradation detected") but doesn't connect the user to emotional support. The emotional support agent exists but is only triggered when the user coincidentally sends a message classified as "emotional." There's no explicit bridge.

### Current State

| Component | Status |
|-----------|--------|
| Pattern detection | ✅ Detects 9 pattern types |
| Intervention messages | ✅ Sent via Telegram |
| Emotional support agent | ✅ Exists, uses CBT approach |
| Link between them | ❌ No connection |
| `/support` command | ❌ Doesn't exist |

### Design: Support Linking + `/support` Command

#### 4.1 Intervention Message Enhancement

Every intervention message currently ends with a "take action" section. Add a **support bridge** at the bottom:

**Current intervention message (example):**
```
🚨 Pattern Alert: Sleep Degradation

📊 Evidence: Sleep dropped below 7h for 3 of last 5 days.
📜 Constitution: "7+ hours sleep is non-negotiable."
⚠️ Risk: Sleep deprivation compounds — affects training, deep work, and impulse control.
✅ Action: Set a hard 10:30 PM bedtime tonight. No screens after 10 PM.
🔥 Your 23-day streak is worth protecting!
```

**Enhanced (add support bridge):**
```
🚨 Pattern Alert: Sleep Degradation

📊 Evidence: Sleep dropped below 7h for 3 of last 5 days.
📜 Constitution: "7+ hours sleep is non-negotiable."
⚠️ Risk: Sleep deprivation compounds — affects training, deep work, and impulse control.
✅ Action: Set a hard 10:30 PM bedtime tonight. No screens after 10 PM.
🔥 Your 23-day streak is worth protecting!

━━━━━━━━━━━━━━━━━━
💬 Struggling with this? Type /support to talk it through.
   I can help you identify what's driving this pattern.
```

#### 4.2 `/support` Command

New command that directly invokes the emotional support agent:

```
User: /support

Bot: 
💙 I'm here. 

What's going on? You can tell me about:
• What you're struggling with right now
• What triggered a slip or pattern
• How you're feeling emotionally
• Anything on your mind

Just type naturally — I'll listen and help you work through it.
```

After the user responds, the emotional support agent handles the conversation using its existing CBT-based approach.

#### 4.3 Context-Aware Support

When `/support` is triggered from an intervention context (user clicks within 24h of receiving an intervention), the emotional agent receives context:

```python
# When user types /support:
recent_interventions = firestore_service.get_recent_interventions(user_id, hours=24)
if recent_interventions:
    # Provide context to emotional agent
    context = f"User recently received intervention for: {intervention.pattern_type}"
    # Agent can reference the specific pattern in its response
```

This makes the support feel connected rather than generic.

#### 4.4 Severity-Based Support Prompts

Different intervention severity levels get different support prompts:

| Severity | Pattern Types | Support Prompt |
|----------|--------------|----------------|
| Low | Single missed item | "💬 Want to talk about what got in the way? /support" |
| Medium | Sleep, training decline | "💬 Struggling with this? Type /support to talk it through." |
| High | Porn relapse, 3+ items failing | "💙 This is hard. Type /support — no judgment, just support." |
| Critical | Ghosting Day 3+, spiral pattern | "🆘 I'm here for you. Type /support or just tell me how you're feeling." |

#### 4.5 Implementation

```python
# intervention.py — add to message generation
def _add_support_bridge(self, message: str, severity: str) -> str:
    bridges = {
        "low": "\n\n💬 Want to talk about what got in the way? /support",
        "medium": "\n\n━━━━━━━━━━━━━━━━━━\n💬 Struggling with this? Type /support to talk it through.\n   I can help you identify what's driving this pattern.",
        "high": "\n\n━━━━━━━━━━━━━━━━━━\n💙 This is hard. Type /support — no judgment, just support.",
        "critical": "\n\n━━━━━━━━━━━━━━━━━━\n🆘 I'm here for you. Type /support or just tell me how you're feeling.",
    }
    return message + bridges.get(severity, bridges["medium"])

# telegram_bot.py — new command
async def support_command(self, update, context):
    """Handle /support command — invoke emotional support agent."""
```

#### 4.6 Acceptance Criteria

- [ ] All intervention messages include a support bridge prompt
- [ ] Severity-appropriate prompt language (low → critical)
- [ ] `/support` command invokes the emotional support agent
- [ ] Context-aware: if triggered after intervention, agent knows the pattern
- [ ] Standalone: `/support` also works without prior intervention
- [ ] No new dependencies — uses existing emotional agent

---

## Feature 5: Tiered Rate Limiting

### Problem Statement

There's no throttling on any commands. A user (or bot) can spam `/report` (generates 4 graphs + AI analysis), `/export pdf`, or AI-powered queries repeatedly, consuming expensive resources (Gemini API tokens, CPU for graph generation).

### Current State

| Component | Rate Limiting |
|-----------|--------------|
| `/report` (AI + graphs) | ❌ None |
| `/export pdf/csv` | ❌ None |
| AI queries (general messages) | ❌ None |
| `/checkin` | ❌ None (but already has "already checked in today" guard) |
| `/partner_status` | ❌ None |
| Cron endpoints | ✅ Protected by auth (Fix 11) |

### Design: In-Memory Tiered Rate Limiter

#### 5.1 Command Tiers

| Tier | Commands | Cooldown | Max per Hour | Rationale |
|------|----------|----------|-------------|-----------|
| **Expensive** | `/report`, `/export pdf` | 30 min | 2/hour | Generates graphs, PDF, AI analysis |
| **AI-Powered** | General messages (AI query), `/support` | 2 min | 20/hour | Gemini API calls |
| **Standard** | `/stats`, `/partner_status`, `/leaderboard` | 10 sec | 30/hour | Firestore reads only |
| **Free** | `/start`, `/help`, `/mode`, `/timezone`, `/cancel` | None | Unlimited | No backend cost |

#### 5.2 Rate Limiter Architecture

**In-memory rate limiter** using a simple dict with timestamps. No external dependencies (Redis etc.) needed for a single-instance Cloud Run service.

```python
# src/utils/rate_limiter.py

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Tuple

class RateLimiter:
    """
    In-memory tiered rate limiter for Telegram bot commands.
    
    Theory: We use a sliding window approach. For each user+tier combo,
    we track the timestamp of each request. When a new request comes in,
    we prune old entries and check if the user is within limits.
    
    Trade-off: In-memory means limits reset on deployment/restart.
    This is acceptable because:
    1. Restarts are rare (Cloud Run keeps instances warm)
    2. Failing open (allowing on restart) is better than failing closed
    3. No Redis dependency reduces complexity and cost
    """
    
    TIERS = {
        "expensive": {"cooldown_seconds": 1800, "max_per_hour": 2},
        "ai_powered": {"cooldown_seconds": 120, "max_per_hour": 20},
        "standard": {"cooldown_seconds": 10, "max_per_hour": 30},
    }
    
    COMMAND_TIERS = {
        "report": "expensive",
        "export": "expensive",
        "support": "ai_powered",
        "query": "ai_powered",       # General AI messages
        "stats": "standard",
        "partner_status": "standard",
        "leaderboard": "standard",
        "achievements": "standard",
    }
    
    def __init__(self):
        # {user_id: {tier: [timestamp, timestamp, ...]}}
        self._requests = defaultdict(lambda: defaultdict(list))
    
    def check(self, user_id: str, command: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a command is allowed for this user.
        
        Returns:
            (allowed: bool, message: Optional[str])
            If not allowed, message explains when they can retry.
        """
        tier = self.COMMAND_TIERS.get(command)
        if tier is None:
            return True, None  # Free tier, always allowed
        
        config = self.TIERS[tier]
        now = datetime.utcnow()
        
        # Prune entries older than 1 hour
        entries = self._requests[user_id][tier]
        cutoff = now - timedelta(hours=1)
        entries[:] = [t for t in entries if t > cutoff]
        
        # Check hourly limit
        if len(entries) >= config["max_per_hour"]:
            return False, f"⏳ You've used this {len(entries)} times in the last hour. Try again later."
        
        # Check cooldown
        if entries:
            last = entries[-1]
            cooldown_remaining = config["cooldown_seconds"] - (now - last).total_seconds()
            if cooldown_remaining > 0:
                minutes = int(cooldown_remaining // 60)
                seconds = int(cooldown_remaining % 60)
                if minutes > 0:
                    return False, f"⏳ Please wait {minutes}m {seconds}s before using this again."
                else:
                    return False, f"⏳ Please wait {seconds}s before using this again."
        
        # Allowed — record this request
        entries.append(now)
        return True, None
```

#### 5.3 Integration Point

Wrap rate limiting as a decorator or early check in command handlers:

```python
# In telegram_bot.py, at the start of expensive commands:
async def report_command(self, update, context):
    user_id = str(update.effective_user.id)
    allowed, message = rate_limiter.check(user_id, "report")
    if not allowed:
        await update.message.reply_text(message)
        return
    
    # ... proceed with expensive operation
```

#### 5.4 User-Friendly Denial Messages

```
⏳ Please wait 12m 30s before generating another report.
   Your last report was generated at 3:47 PM.
   
💡 Tip: Reports are most useful when reviewed weekly, not daily!
```

#### 5.5 Admin Override

Add `admin_telegram_ids` to config. Admin users bypass rate limits:

```python
def check(self, user_id: str, command: str) -> Tuple[bool, Optional[str]]:
    if user_id in settings.admin_telegram_ids:
        return True, None  # Admins bypass rate limits
    # ... normal rate limiting
```

#### 5.6 Acceptance Criteria

- [ ] Expensive commands (`/report`, `/export`) limited to 2/hour with 30min cooldown
- [ ] AI-powered commands limited to 20/hour with 2min cooldown
- [ ] Standard commands limited to 30/hour with 10sec cooldown
- [ ] Free commands unlimited
- [ ] User-friendly denial messages with countdown
- [ ] Admin users bypass rate limits
- [ ] Rate limits reset gracefully on deployment (fail open)

---

## Feature 6: Cloud-Native Monitoring & Alerting

### Problem Statement

The only observability is basic Python logging to stdout and a `/health` endpoint that checks Firestore. There's no error aggregation, no performance metrics, no alerting on failures. If the bot goes down or starts erroring, nobody knows until a user complains.

### Current State

| Component | Status |
|-----------|--------|
| `/health` endpoint | ✅ Basic Firestore check |
| Structured logging | ⚠️ Basic format, not JSON |
| Error tracking | ❌ Logged but not aggregated |
| Metrics | ❌ None |
| Alerting | ❌ None |
| Admin status command | ❌ None |

### Design: Cloud Monitoring Integration

#### 6.1 Structured JSON Logging

Change log format from plain text to JSON for Cloud Logging parsing:

```python
# Current:
format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'

# New: JSON structured logging
import json

class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "severity": record.levelname,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "timestamp": self.formatTime(record),
        }
        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)
        if hasattr(record, 'user_id'):
            log_entry["user_id"] = record.user_id
        if hasattr(record, 'command'):
            log_entry["command"] = record.command
        if hasattr(record, 'latency_ms'):
            log_entry["latency_ms"] = record.latency_ms
        return json.dumps(log_entry)
```

**Why JSON?** Cloud Logging (formerly Stackdriver) automatically parses JSON log entries, making them searchable, filterable, and usable in Cloud Monitoring log-based metrics. Plain text requires regex parsing.

#### 6.2 Application Metrics Tracking

Track key metrics in-memory, exposed via `/admin/metrics` endpoint:

```python
# src/utils/metrics.py

class AppMetrics:
    """
    In-memory metrics collector for application health monitoring.
    
    Tracks counters and timing data that can be:
    1. Exposed via /admin/metrics endpoint
    2. Scraped by monitoring systems
    3. Sent to your Telegram via daily digest
    """
    
    def __init__(self):
        self.counters = defaultdict(int)
        self.latencies = defaultdict(list)  # Last 100 per metric
        self.errors = defaultdict(int)
        self.start_time = datetime.utcnow()
    
    def increment(self, metric: str, value: int = 1):
        self.counters[metric] += value
    
    def record_latency(self, metric: str, ms: float):
        entries = self.latencies[metric]
        entries.append(ms)
        if len(entries) > 100:
            entries.pop(0)
    
    def record_error(self, category: str):
        self.errors[category] += 1
    
    def get_summary(self) -> dict:
        uptime = (datetime.utcnow() - self.start_time).total_seconds()
        return {
            "uptime_seconds": uptime,
            "uptime_human": f"{uptime // 3600:.0f}h {(uptime % 3600) // 60:.0f}m",
            "counters": dict(self.counters),
            "errors": dict(self.errors),
            "latencies": {
                k: {
                    "avg_ms": sum(v) / len(v) if v else 0,
                    "p50_ms": sorted(v)[len(v)//2] if v else 0,
                    "p95_ms": sorted(v)[int(len(v)*0.95)] if v else 0,
                    "count": len(v),
                }
                for k, v in self.latencies.items()
            },
        }

# Singleton
metrics = AppMetrics()
```

**Metrics to track:**

| Metric | Type | Description |
|--------|------|-------------|
| `checkins_total` | Counter | Total check-ins processed |
| `checkins_quick` | Counter | Quick check-ins |
| `checkins_full` | Counter | Full check-ins |
| `commands_total` | Counter | Total commands processed |
| `commands_{name}` | Counter | Per-command counts |
| `ai_requests_total` | Counter | Gemini API calls |
| `ai_tokens_used` | Counter | Total tokens consumed |
| `errors_total` | Counter | Total errors |
| `errors_{category}` | Counter | Errors by category (firestore, telegram, ai, etc.) |
| `webhook_latency` | Latency | Webhook processing time |
| `ai_latency` | Latency | Gemini API response time |
| `firestore_latency` | Latency | Firestore query time |

#### 6.3 Enhanced `/health` Endpoint

Expand the health endpoint to include metrics:

```json
{
    "status": "healthy",
    "uptime": "14h 23m",
    "checks": {
        "firestore": "ok",
        "bot_webhook": "ok"
    },
    "metrics": {
        "checkins_today": 15,
        "commands_last_hour": 42,
        "errors_last_hour": 0,
        "avg_webhook_latency_ms": 230
    }
}
```

#### 6.4 `/admin_status` Telegram Command

Admin-only command that sends a rich status summary:

```
🔧 Admin Status Report
━━━━━━━━━━━━━━━━━━

⏱ Uptime: 14h 23m
📊 Today's Activity:
  Check-ins: 15 (12 full, 3 quick)
  Commands: 142
  AI Requests: 38
  
⚠️ Errors (last 24h):
  Firestore: 0
  Telegram API: 2
  AI/Gemini: 1
  
📈 Performance:
  Avg webhook: 230ms
  Avg AI response: 1.2s
  P95 webhook: 890ms

💰 AI Cost Estimate:
  Tokens today: ~12,400
  Est. cost: $0.03
```

#### 6.5 Google Cloud Monitoring Integration

**Log-based metrics** (no code needed, configured in GCP Console):

1. **Error rate metric:** Count log entries where `severity=ERROR`
2. **Check-in count metric:** Count log entries containing "Check-in completed"
3. **AI latency metric:** Extract `latency_ms` from AI request logs

**Alert policies:**

| Alert | Condition | Notification |
|-------|-----------|-------------|
| Bot Down | Health check fails for 5 min | Telegram message to admin |
| Error Spike | >5 errors in 10 min | Telegram message to admin |
| High Latency | P95 webhook > 5s for 10 min | Telegram message to admin |
| Zero Check-ins | No check-ins by 11 PM IST | Telegram message to admin |

**Implementation:** Alert policies configured in GCP Console (not in code). The code provides the structured logs and metrics that Cloud Monitoring consumes.

#### 6.6 Daily Health Digest

A cron job that sends a daily summary to the admin's Telegram:

```
📊 Daily Health Digest — Feb 8, 2026
━━━━━━━━━━━━━━━━━━

👥 Users: 3 active today
📝 Check-ins: 15 completed
  - Full: 12 | Quick: 3
  
🤖 AI Usage:
  - Requests: 38
  - Tokens: ~12,400
  - Est. cost: $0.03
  
⚡ Performance:
  - Avg response: 230ms
  - Slowest: 2.1s (/report)
  - Errors: 3 (2 transient, 1 Telegram)
  
🔥 Engagement:
  - Avg compliance: 87%
  - Avg streak: 23 days
  - Partner check-ins: 2/3
```

#### 6.7 Acceptance Criteria

- [ ] JSON structured logging (Cloud Logging compatible)
- [ ] In-memory metrics tracking (counters, latencies, errors)
- [ ] Enhanced `/health` endpoint with metrics summary
- [ ] `/admin_status` command (admin-only) showing live metrics
- [ ] Log-based metrics configured in GCP (documented, not coded)
- [ ] Alert policies documented for GCP setup
- [ ] Daily health digest sent to admin Telegram at midnight

---

## Implementation Order & Dependencies

```
Phase A: Foundation (no user-facing changes)
├── 6. Monitoring — JSON logging + metrics framework
│   (Provides observability for all subsequent changes)
└── 5. Rate Limiting — In-memory limiter
    (Protects against abuse during rollout)

Phase B: Core Infrastructure
└── 1. Timezone Support — The biggest change
    ├── 1a. Generalize timezone_utils.py functions
    ├── 1b. Onboarding timezone picker
    ├── 1c. /timezone command
    ├── 1d. Thread user.timezone through all callers
    └── 1e. Bucket-based reminder scheduling

Phase C: User-Facing Features
├── 3. Streak Recovery — Relatively isolated
├── 4. Intervention-to-Support — Small addition
└── 2. Partner Dashboard — Small addition

Phase D: Polish
├── Wire up monitoring for all new features
├── Add rate limiting to new commands
└── End-to-end testing
```

**Rationale:**
- Monitoring goes first so we can observe the impact of all subsequent changes.
- Rate limiting goes second as a safety net.
- Timezone is the biggest risk (touches date calculations everywhere) so it goes third, when we have monitoring to catch issues.
- Streak recovery and intervention linking are isolated and low-risk.
- Partner dashboard is small and self-contained.

---

## File Change Map

| File | Features | Changes |
|------|----------|---------|
| `src/utils/timezone_utils.py` | F1 | Generalize all functions, add aliases |
| `src/utils/rate_limiter.py` | F5 | **NEW** — Rate limiter class |
| `src/utils/metrics.py` | F6 | **NEW** — Metrics collector |
| `src/utils/streak.py` | F3 | Add reset context, recovery facts |
| `src/utils/compliance.py` | — | No changes |
| `src/models/schemas.py` | F1, F3 | UserStreaks: add `streak_before_reset`, `last_reset_date` |
| `src/config.py` | F5, F6 | Add `admin_telegram_ids`, monitoring settings |
| `src/bot/telegram_bot.py` | F1, F2, F4, F5 | New commands: `/timezone`, `/partner_status`, `/support`. Rate limit checks. |
| `src/bot/conversation.py` | F1, F3 | Pass user.timezone to date functions. Enhanced streak reset message. |
| `src/services/firestore_service.py` | F1, F2 | Timezone-aware queries. `get_recent_checkins()`. |
| `src/agents/intervention.py` | F4 | Add support bridge to intervention messages |
| `src/main.py` | F1, F5, F6 | Bucket reminders. JSON logging. Metrics middleware. `/admin/metrics`. Daily digest cron. |
| `src/services/achievement_service.py` | F3 | Add Comeback Kid, Comeback Legend achievements |

**New files:** 2 (`rate_limiter.py`, `metrics.py`)  
**Modified files:** 11  
**Total files affected:** 13

---

## Testing Strategy

| Feature | Unit Tests | Integration Tests |
|---------|-----------|-------------------|
| F1: Timezone | timezone_utils with various TZ params | Onboarding flow, reminder bucketing |
| F2: Partner | format_partner_dashboard | /partner_status end-to-end |
| F3: Streak Recovery | update_streak_data with resets | Check-in flow showing reset message |
| F4: Support Linking | _add_support_bridge | /support command with intervention context |
| F5: Rate Limiting | RateLimiter.check() all tiers | Command handlers respecting limits |
| F6: Monitoring | AppMetrics.get_summary() | /health, /admin_status, JSON log format |

---

## Rollback Plan

Each feature is designed to be independently deployable and rollback-safe:

- **F1 Timezone:** Old IST aliases still work. If timezone breaks, set all users back to `"Asia/Kolkata"`.
- **F2 Partner:** New command only — removing it doesn't break existing partner system.
- **F3 Streak Recovery:** New fields have defaults. Old streak logic is a subset of new logic.
- **F4 Support Linking:** Additive only — intervention messages get extra text. `/support` is a new command.
- **F5 Rate Limiting:** Fails open on restart. Can be disabled by removing checks.
- **F6 Monitoring:** JSON logging is backward compatible with Cloud Logging. Metrics are optional.

---

*Document Version: 1.0 — Feb 8, 2026*
