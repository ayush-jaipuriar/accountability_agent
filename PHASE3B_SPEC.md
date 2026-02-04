# Phase 3B: Ghosting Detection & Emotional Support - Technical Specification

**Version:** 1.0  
**Date:** February 4, 2026  
**Status:** Approved for Implementation  
**Estimated Implementation Time:** 9 days  
**Target Cost:** +$0.15/month (total: $1.41/month)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Feature 1: Ghosting Detection](#feature-1-ghosting-detection)
3. [Feature 2: Accountability Partner System](#feature-2-accountability-partner-system)
4. [Feature 3: Emotional Support Agent](#feature-3-emotional-support-agent)
5. [Implementation Plan](#implementation-plan)
6. [Testing Strategy](#testing-strategy)
7. [Deployment Plan](#deployment-plan)
8. [Success Criteria](#success-criteria)

---

## Executive Summary

### What Phase 3B Adds

Phase 3B transforms the accountability agent from a passive tracker into an **active intervention system** with three critical features:

1. **Ghosting Detection** - Proactive escalation when users disappear (Day 2-5)
2. **Accountability Partner System** - Peer support network with Day 5 escalation
3. **Emotional Support Agent** - CBT-style support for crisis moments

### Why This Matters

**Current Gap (After Phase 3A):**
- ✅ Triple reminders prevent Day 1 misses (9 PM, 9:30 PM, 10 PM)
- ❌ No follow-up if user ignores all 3 reminders
- ❌ User could ghost for weeks without escalation
- ❌ No emotional support during difficult moments

**Phase 3B Solution:**
- ✅ Day 2-5 escalating intervention (gentle → urgent → emergency)
- ✅ Partner notification on Day 5 ghosting
- ✅ CBT-style emotional support (loneliness, porn urges, breakup thoughts)

### Success Metrics

**Functional:**
- ✅ Ghosting detection triggers correctly on Day 2, 3, 4, 5
- ✅ Escalation messages match constitution tone
- ✅ Partner linking works bidirectionally
- ✅ Emotional agent handles 3 emotion types
- ✅ Supervisor routes emotional messages correctly

**Business:**
- ✅ Reduce 7-day churn by 50% (ghosting detection)
- ✅ Emotional agent used by 30% of users monthly
- ✅ Partner feature adopted by 20% of user pairs

**Technical:**
- ✅ Cost increase <$0.20/month for 10 users
- ✅ No performance degradation
- ✅ All tests passing (unit + integration)

---

## Feature 1: Ghosting Detection

### Overview

**Problem:** User ignores triple reminders → disappears for days → system doesn't follow up

**Solution:** Escalating intervention system that detects missing check-ins and sends increasingly urgent messages.

### Escalation Timeline

| Day | Severity | Message Example | Action |
|-----|----------|-----------------|--------|
| 1 | Grace | (Triple reminders sent) | None (Phase 3A handles) |
| 2 | Nudge | "👋 Missed you yesterday! Everything okay?" | Gentle reminder |
| 3 | Warning | "⚠️ 3 days missing. Constitution violation." | Firm warning |
| 4 | Critical | "🚨 4-day absence. Last time (Feb 2025): 6-month spiral." | Historical reference |
| 5+ | Emergency | "🔴 EMERGENCY. Contact accountability partner NOW." | Partner escalation |

### Technical Design

#### 1. Pattern Detection

**File:** `src/agents/pattern_detection.py`

**New Method:**

```python
def detect_ghosting(self, user_id: str) -> Optional[Pattern]:
    """
    Detect missing check-ins with escalating severity.
    
    Algorithm:
    1. Get user's last check-in date
    2. Calculate days since last check-in
    3. If days >= 2, create ghosting pattern
    4. Severity based on days missing
    
    Returns:
        Pattern object with ghosting data, or None if no ghosting
    """
    user = self.firestore_service.get_user(user_id)
    
    if not user or not user.streaks.last_checkin_date:
        return None
    
    # Calculate days since last check-in
    days_since = self._calculate_days_since_checkin(
        user.streaks.last_checkin_date
    )
    
    # Day 1 = grace period (triple reminders handle it)
    if days_since < 2:
        return None
    
    # Day 2+ = ghosting detected
    severity = self._get_ghosting_severity(days_since)
    
    return Pattern(
        pattern_id=f"ghosting_{user_id}_{datetime.utcnow().strftime('%Y%m%d')}",
        user_id=user_id,
        type="ghosting",
        severity=severity,
        detected_at=datetime.utcnow(),
        data={
            "days_missing": days_since,
            "last_checkin_date": user.streaks.last_checkin_date,
            "previous_streak": user.streaks.current_streak,
            "current_mode": user.constitution.current_mode
        },
        resolved=False
    )

def _calculate_days_since_checkin(self, last_checkin_date: str) -> int:
    """
    Calculate days between last check-in and today.
    
    Args:
        last_checkin_date: Date string in format "YYYY-MM-DD"
    
    Returns:
        Number of days since last check-in
    """
    from datetime import datetime
    from src.utils.timezone_utils import get_current_date_ist
    
    last_date = datetime.strptime(last_checkin_date, "%Y-%m-%d").date()
    today = datetime.strptime(get_current_date_ist(), "%Y-%m-%d").date()
    
    return (today - last_date).days

def _get_ghosting_severity(self, days: int) -> str:
    """
    Map days missing to severity level.
    
    Args:
        days: Number of days since last check-in
    
    Returns:
        Severity string: "nudge" | "warning" | "critical" | "emergency"
    """
    if days == 2:
        return "nudge"
    elif days == 3:
        return "warning"
    elif days == 4:
        return "critical"
    else:  # 5+
        return "emergency"
```

#### 2. Intervention Messages

**File:** `src/agents/intervention.py`

**New Method:**

```python
def _build_ghosting_intervention(self, pattern: Pattern, user: User) -> str:
    """
    Build escalating ghosting intervention message.
    
    Message structure:
    - Day 2: Gentle, checking in
    - Day 3: Firm, constitution reference
    - Day 4: Critical, historical pattern reference
    - Day 5+: Emergency, partner escalation
    
    Args:
        pattern: Ghosting pattern with days_missing data
        user: User object for personalization
    
    Returns:
        Intervention message string
    """
    days = pattern.data["days_missing"]
    streak = pattern.data["previous_streak"]
    
    if days == 2:
        return (
            "👋 **Missed you yesterday!**\n\n"
            f"You had a {streak}-day streak going. Everything okay?\n\n"
            "Quick check-in: /checkin"
        )
    
    elif days == 3:
        return (
            "⚠️ **3 Days Missing**\n\n"
            f"Your {streak}-day streak is at risk. This is a constitution violation.\n\n"
            "Check in NOW to save your progress: /checkin"
        )
    
    elif days == 4:
        return (
            "🚨 **4-Day Absence - CRITICAL**\n\n"
            f"You had a {streak}-day streak. Last time this happened (Feb 2025): "
            "6-month spiral.\n\n"
            "**Don't let history repeat.** Check in immediately: /checkin"
        )
    
    else:  # Day 5+
        shield_text = ""
        if user.streak_shields.available > 0:
            shield_text = f"\n\n🛡️ You have {user.streak_shields.available} streak shields available. Use one: /use_shield"
        
        partner_text = ""
        if user.accountability_partner_name:
            partner_text = f"\n\n👥 I'm notifying your accountability partner ({user.accountability_partner_name})."
        
        return (
            "🔴 **EMERGENCY - 5+ Days Missing**\n\n"
            f"Your {streak}-day streak is gone. This is exactly how the Feb 2025 "
            "regression started.\n\n"
            "**You need help. Do this NOW:**\n"
            "1. Check in: /checkin\n"
            "2. Text a friend\n"
            "3. Review your constitution"
            f"{shield_text}"
            f"{partner_text}"
        )
```

#### 3. Integration with Pattern Scan

**File:** `src/agents/pattern_detection.py`

**Update Existing Method:**

```python
async def scan_patterns(self, user_id: str) -> List[Pattern]:
    """
    Scan for all pattern types (existing method - UPDATE THIS).
    
    Pattern types:
    - sleep_degradation (Phase 2)
    - training_abandonment (Phase 2)
    - porn_relapse (Phase 2)
    - compliance_decline (Phase 2)
    - ghosting (Phase 3B - NEW)
    """
    patterns = []
    
    # Existing Phase 2 patterns
    patterns.extend(self.detect_sleep_degradation(user_id))
    patterns.extend(self.detect_training_abandonment(user_id))
    patterns.extend(self.detect_porn_relapse(user_id))
    patterns.extend(self.detect_compliance_decline(user_id))
    
    # NEW: Phase 3B ghosting detection
    ghosting_pattern = self.detect_ghosting(user_id)
    if ghosting_pattern:
        patterns.append(ghosting_pattern)
    
    return patterns
```

**Existing Cron Job:** `/trigger/pattern-scan` already exists (runs every 6 hours)

No new scheduler job needed! ✅

### Data Models

**No schema changes needed!** Pattern model already supports ghosting type.

Existing `Pattern` model (from Phase 2):

```python
class Pattern(BaseModel):
    pattern_id: str
    user_id: str
    type: str  # Can be "ghosting"
    severity: str  # "nudge" | "warning" | "critical" | "emergency"
    detected_at: datetime
    data: dict  # Can hold days_missing, last_checkin, etc.
    resolved: bool
```

### User Experience

**Scenario: User Ghosts After Triple Reminders**

```
Monday: User checks in ✅
Tuesday: User checks in ✅
Wednesday: User doesn't check in ❌
  → 9:00 PM: First reminder sent
  → 9:30 PM: Second reminder sent
  → 10:00 PM: Third reminder sent
  → User ignores all 3

Thursday 6 AM: Pattern scan runs
  → Detects Day 2 ghosting (Wednesday missing)
  → Sends: "👋 Missed you yesterday! Everything okay?"

Thursday: User still doesn't respond

Friday 6 AM: Pattern scan runs
  → Detects Day 3 ghosting
  → Sends: "⚠️ 3 days missing. Constitution violation."

Friday: User still doesn't respond

Saturday 6 AM: Pattern scan runs
  → Detects Day 4 ghosting
  → Sends: "🚨 4-day absence. Last time: 6-month spiral."

Saturday: User still doesn't respond

Sunday 6 AM: Pattern scan runs
  → Detects Day 5 ghosting
  → Sends: "🔴 EMERGENCY. Contact accountability partner NOW."
  → ALSO notifies partner (if linked)
```

### Edge Cases

**1. User checks in during escalation:**
- Pattern marked as resolved
- No further ghosting messages
- Streak saved (if within 48 hours or shield used)

**2. User has no partner (Day 5):**
- Emergency message sent
- Partner notification skipped
- Future: Could escalate to admin

**3. Pattern scan runs multiple times per day:**
- Check if ghosting pattern already exists for this date
- Prevent duplicate messages
- Only send once per severity level

---

## Feature 2: Accountability Partner System

### Overview

**Problem:** User ghosts → no human escalation, only bot messages

**Solution:** Users can link as accountability partners. On Day 5 ghosting, partner gets notified.

### User Stories

**As a user, I want to:**
- Link another user as my accountability partner
- Get notified if my partner ghosts for 5+ days
- Unlink a partner if relationship changes

**As the system, I need to:**
- Store bidirectional partner relationships
- Send partner notifications on Day 5 ghosting
- Handle partnership requests (invite/accept/decline)

### Technical Design

#### 1. Database Schema

**Already exists from Phase 3A!** ✅

```python
# src/models/schemas.py

class User(BaseModel):
    # ... existing fields ...
    
    # Phase 3A added these (already deployed):
    accountability_partner_id: Optional[str] = None
    accountability_partner_name: Optional[str] = None
```

No migration needed! Just start using these fields.

#### 2. Bot Commands

**File:** `src/bot/telegram_bot.py`

**New Commands:**

```python
async def set_partner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /set_partner @username - Request to link accountability partner
    
    Flow:
    1. User A sends /set_partner @UserB
    2. Bot searches for User B by telegram username
    3. Bot sends invite to User B
    4. User B accepts/declines
    5. If accepted: Link both users bidirectionally
    """
    user_id = str(update.effective_user.id)
    user = firestore_service.get_user(user_id)
    
    # Parse @username from message
    if not context.args or not context.args[0].startswith('@'):
        await update.message.reply_text(
            "❌ **Invalid usage**\n\n"
            "Format: /set_partner @username\n\n"
            "Example: /set_partner @john_doe"
        )
        return
    
    partner_username = context.args[0][1:]  # Remove @ symbol
    
    # Search for partner by telegram username
    partner = firestore_service.get_user_by_telegram_username(partner_username)
    
    if not partner:
        await update.message.reply_text(
            f"❌ **User not found**\n\n"
            f"User @{partner_username} hasn't started using the bot yet.\n\n"
            "They need to send /start first!"
        )
        return
    
    if partner.user_id == user_id:
        await update.message.reply_text("❌ You can't be your own accountability partner!")
        return
    
    # Send invite to partner
    keyboard = [
        [
            InlineKeyboardButton("✅ Accept", callback_data=f"accept_partner:{user_id}"),
            InlineKeyboardButton("❌ Decline", callback_data=f"decline_partner:{user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await context.bot.send_message(
        chat_id=partner.telegram_id,
        text=(
            f"👥 **Accountability Partner Request**\n\n"
            f"{user.name} wants to be your accountability partner.\n\n"
            f"**What this means:**\n"
            f"• You'll be notified if they ghost for 5+ days\n"
            f"• They'll be notified if you ghost for 5+ days\n"
            f"• Mutual support and motivation\n\n"
            f"Accept this request?"
        ),
        reply_markup=reply_markup
    )
    
    await update.message.reply_text(
        f"✅ **Partner request sent to @{partner_username}!**\n\n"
        f"Waiting for them to accept..."
    )


async def accept_partner_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Handle partner request acceptance.
    
    Callback data format: "accept_partner:<requester_user_id>"
    """
    query = update.callback_query
    await query.answer()
    
    # Parse requester user_id from callback data
    requester_user_id = query.data.split(':')[1]
    accepter_user_id = str(query.from_user.id)
    
    # Get both users
    requester = firestore_service.get_user(requester_user_id)
    accepter = firestore_service.get_user(accepter_user_id)
    
    # Link partners bidirectionally
    firestore_service.set_accountability_partner(
        user_id=requester_user_id,
        partner_id=accepter_user_id,
        partner_name=accepter.name
    )
    
    firestore_service.set_accountability_partner(
        user_id=accepter_user_id,
        partner_id=requester_user_id,
        partner_name=requester.name
    )
    
    # Notify both users
    await query.edit_message_text(
        f"✅ **Partnership Confirmed!**\n\n"
        f"You and {requester.name} are now accountability partners.\n\n"
        f"You'll be notified if they ghost for 5+ days, and vice versa."
    )
    
    await context.bot.send_message(
        chat_id=requester.telegram_id,
        text=(
            f"✅ **Partnership Confirmed!**\n\n"
            f"{accepter.name} accepted your request!\n\n"
            f"You're now accountability partners. 🤝"
        )
    )


async def decline_partner_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle partner request decline."""
    query = update.callback_query
    await query.answer()
    
    requester_user_id = query.data.split(':')[1]
    accepter = firestore_service.get_user(str(query.from_user.id))
    requester = firestore_service.get_user(requester_user_id)
    
    await query.edit_message_text(
        "❌ **Partnership declined.**"
    )
    
    await context.bot.send_message(
        chat_id=requester.telegram_id,
        text=f"❌ {accepter.name} declined your partnership request."
    )


async def unlink_partner_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    /unlink_partner - Remove accountability partner
    """
    user_id = str(update.effective_user.id)
    user = firestore_service.get_user(user_id)
    
    if not user.accountability_partner_id:
        await update.message.reply_text(
            "❌ You don't have an accountability partner."
        )
        return
    
    partner = firestore_service.get_user(user.accountability_partner_id)
    
    # Unlink bidirectionally
    firestore_service.set_accountability_partner(user_id, None, None)
    firestore_service.set_accountability_partner(partner.user_id, None, None)
    
    await update.message.reply_text(
        f"✅ **Partnership with {partner.name} removed.**"
    )
    
    await context.bot.send_message(
        chat_id=partner.telegram_id,
        text=f"👥 {user.name} has removed you as their accountability partner."
    )
```

#### 3. Firestore Service Methods

**File:** `src/services/firestore_service.py`

**New Methods:**

```python
def get_user_by_telegram_username(self, telegram_username: str) -> Optional[User]:
    """
    Find user by their Telegram username.
    
    Args:
        telegram_username: Telegram username (without @ symbol)
    
    Returns:
        User object if found, None otherwise
    """
    users_ref = self.db.collection('users')
    query = users_ref.where('telegram_username', '==', telegram_username).limit(1)
    docs = query.stream()
    
    for doc in docs:
        return User(**doc.to_dict())
    
    return None


def set_accountability_partner(
    self,
    user_id: str,
    partner_id: Optional[str],
    partner_name: Optional[str]
) -> None:
    """
    Set or remove accountability partner for a user.
    
    Args:
        user_id: User ID
        partner_id: Partner's user ID (None to unlink)
        partner_name: Partner's name (None to unlink)
    """
    self.db.collection('users').document(user_id).update({
        'accountability_partner_id': partner_id,
        'accountability_partner_name': partner_name,
        'updated_at': firestore.SERVER_TIMESTAMP
    })
```

**Update User Model to Include telegram_username:**

```python
# src/models/schemas.py

class User(BaseModel):
    user_id: str
    telegram_id: int
    telegram_username: Optional[str] = None  # ADD THIS FIELD
    name: str
    # ... rest of fields ...
```

**Update create_user_profile to store telegram_username:**

```python
# src/services/firestore_service.py

def create_user_profile(
    self,
    user_id: str,
    telegram_id: int,
    telegram_username: Optional[str],  # ADD THIS PARAMETER
    first_name: str,
    # ... other params ...
) -> User:
    """Create new user profile with telegram_username"""
    user_data = {
        'user_id': user_id,
        'telegram_id': telegram_id,
        'telegram_username': telegram_username,  # STORE THIS
        'name': first_name,
        # ... rest of fields ...
    }
    # ... rest of method ...
```

#### 4. Partner Notification on Day 5 Ghosting

**File:** `src/agents/intervention.py`

**Update trigger_intervention Method:**

```python
async def trigger_intervention(self, user_id: str, pattern: Pattern) -> None:
    """
    Trigger intervention for detected pattern.
    
    Phase 3B addition: Notify partner on Day 5 ghosting.
    """
    user = self.firestore_service.get_user(user_id)
    
    # Build intervention message
    if pattern.type == "ghosting":
        message = self._build_ghosting_intervention(pattern, user)
    else:
        message = self._build_intervention(pattern, user)
    
    # Send to user
    await self.telegram_bot.send_message(
        chat_id=user.telegram_id,
        text=message
    )
    
    # Log intervention
    self.firestore_service.store_intervention(user_id, {
        'pattern_id': pattern.pattern_id,
        'pattern_type': pattern.type,
        'severity': pattern.severity,
        'message': message,
        'sent_at': datetime.utcnow()
    })
    
    # NEW: Day 5 ghosting → Notify partner
    if pattern.type == "ghosting" and pattern.data["days_missing"] >= 5:
        await self._notify_accountability_partner(user, pattern)


async def _notify_accountability_partner(self, user: User, pattern: Pattern) -> None:
    """
    Notify user's accountability partner about prolonged ghosting.
    
    Only called on Day 5+ ghosting.
    """
    if not user.accountability_partner_id:
        logger.info(f"User {user.user_id} has no partner to notify")
        return
    
    partner = self.firestore_service.get_user(user.accountability_partner_id)
    if not partner:
        logger.error(f"Partner {user.accountability_partner_id} not found")
        return
    
    days_missing = pattern.data["days_missing"]
    last_checkin = pattern.data["last_checkin_date"]
    
    message = (
        f"🚨 **Accountability Partner Alert**\n\n"
        f"Your partner **{user.name}** hasn't checked in for **{days_missing} days**.\n\n"
        f"Last check-in: {last_checkin}\n\n"
        f"This is serious. Consider reaching out to check on them:\n"
        f"• Text them directly\n"
        f"• Call if you have their number\n"
        f"• Make sure they're okay\n\n"
        f"Sometimes people need a friend more than a bot."
    )
    
    await self.telegram_bot.send_message(
        chat_id=partner.telegram_id,
        text=message
    )
    
    logger.info(
        f"Partner notification sent: {user.user_id} ghosted, "
        f"notified partner {partner.user_id}"
    )
```

### User Experience

**Scenario: Setting Up Partnership**

```
User A: /set_partner @UserB
  ↓
Bot → User B: "👥 UserA wants to be your accountability partner. Accept?"
  [✅ Accept] [❌ Decline]
  ↓
User B clicks [✅ Accept]
  ↓
Bot → User B: "✅ Partnership confirmed!"
Bot → User A: "✅ UserB accepted your request!"
  ↓
Partnership active ✅
```

**Scenario: Partner Notification (Day 5 Ghosting)**

```
User A: [Hasn't checked in for 5 days]
  ↓
System detects Day 5 ghosting
  ↓
Bot → User A: "🔴 EMERGENCY - 5+ days missing..."
  ↓
Bot → User B (partner): "🚨 Your partner UserA hasn't checked in for 5 days..."
  ↓
User B texts User A directly
  ↓
User A returns and checks in ✅
```

---

## Feature 3: Emotional Support Agent

### Overview

**Problem:** Users face difficult moments (loneliness, porn urges, breakup thoughts) with no support.

**Solution:** AI agent that provides CBT-style emotional support using constitution protocols.

### Emotional Support Protocol

**4-Step Approach:**

1. **VALIDATE** - Acknowledge the emotion (not dismiss it)
2. **REFRAME** - Tie emotion to constitution principles
3. **TRIGGER** - Ask what caused this feeling
4. **ACTION** - 3 immediate concrete actions

**Example:**

```
User: "I'm feeling really lonely tonight"
  ↓
Bot Response:
"I hear you. Loneliness is real and it's temporary. Your intentional 
celibacy phase is by design, not default. You're building the foundation 
for the life partner you deserve. This is strategic isolation, not abandonment.

What specifically triggered this feeling right now?

Here's what you need to do RIGHT NOW:
1. Text one friend: 'Hey, what's up?'
2. Go to gym or cafe (public place, don't isolate)
3. If you can't leave: 20 pushups

You got this. Your constitution matters more than this moment."
```

### Technical Design

#### 1. New Agent File

**Create:** `src/agents/emotional_agent.py`

```python
"""
Emotional Support Agent

Provides CBT-style emotional support using constitution protocols.

Supported emotion types:
- loneliness: Intentional celibacy validation + action
- porn_urge: Interrupt pattern + accountability
- breakup: Historical pattern reference + reframe
- stress: General support + action
"""

from typing import Optional
from datetime import datetime
import logging

from src.agents.state import ConstitutionState, Intent
from src.services.llm_service import llm_service
from src.services.constitution_service import constitution_service
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


class EmotionalSupportAgent:
    """
    Handles emotional support requests using CBT-style protocols.
    
    Protocol Structure:
    1. VALIDATE - Acknowledge emotion
    2. REFRAME - Tie to constitution principles
    3. TRIGGER - Ask what caused it
    4. ACTION - 3 immediate concrete actions
    """
    
    def __init__(self):
        self.llm_service = llm_service
        self.constitution_service = constitution_service
        self.firestore_service = firestore_service
    
    async def process(self, state: ConstitutionState) -> ConstitutionState:
        """
        Process emotional support request.
        
        Args:
            state: Current conversation state with user message
        
        Returns:
            Updated state with emotional support response
        """
        logger.info(f"Processing emotional support for user {state.user_id}")
        
        try:
            # 1. Classify emotion type
            emotion_type = await self._classify_emotion(state.message)
            logger.info(f"Classified emotion: {emotion_type}")
            
            # 2. Load protocol from constitution
            protocol = self.constitution_service.get_emotional_protocol(emotion_type)
            
            if not protocol:
                # Fallback for emotions without specific protocol
                protocol = self.constitution_service.get_emotional_protocol("general")
            
            # 3. Get user context for personalization
            user = self.firestore_service.get_user(state.user_id)
            
            # 4. Generate personalized response
            response = await self._generate_emotional_response(
                emotion_type=emotion_type,
                user_message=state.message,
                protocol=protocol,
                user=user
            )
            
            # 5. Log emotional interaction
            self.firestore_service.store_emotional_interaction(
                user_id=state.user_id,
                emotion_type=emotion_type,
                user_message=state.message,
                bot_response=response,
                timestamp=datetime.utcnow()
            )
            
            return state.update(response=response)
        
        except Exception as e:
            logger.error(f"Error in emotional support: {e}")
            
            # Fallback response
            return state.update(
                response=(
                    "I hear that you're going through something difficult. "
                    "While I want to help, this is a moment where talking to a real person "
                    "might be more valuable.\n\n"
                    "Consider:\n"
                    "• Texting a friend\n"
                    "• Calling someone you trust\n"
                    "• If urgent: Crisis hotline (988 in US)\n\n"
                    "Your constitution reminds you: difficult moments pass, "
                    "your long-term goals remain."
                )
            )
    
    async def _classify_emotion(self, message: str) -> str:
        """
        Classify user's emotion from their message.
        
        Args:
            message: User's message
        
        Returns:
            Emotion type: "loneliness" | "porn_urge" | "breakup" | "stress" | "general"
        """
        prompt = f"""
Classify the emotion in this message:

Message: "{message}"

Possible emotions:
- loneliness: Feeling alone, isolated, wanting companionship
- porn_urge: Sexual urges, temptation to view porn
- breakup: Missing ex, thinking about getting back together
- stress: General stress, anxiety, overwhelm
- general: Other emotions not fitting above categories

Respond with ONLY the emotion word (lowercase).
"""
        
        response = await self.llm_service.generate_text(
            prompt=prompt,
            max_tokens=10
        )
        
        emotion = response.strip().lower()
        
        # Validate response
        valid_emotions = ["loneliness", "porn_urge", "breakup", "stress", "general"]
        if emotion not in valid_emotions:
            logger.warning(f"Invalid emotion classification: {emotion}, defaulting to 'general'")
            emotion = "general"
        
        return emotion
    
    async def _generate_emotional_response(
        self,
        emotion_type: str,
        user_message: str,
        protocol: dict,
        user: object
    ) -> str:
        """
        Generate personalized emotional support response using Gemini.
        
        Args:
            emotion_type: Classified emotion
            user_message: User's original message
            protocol: Constitution protocol for this emotion
            user: User object for personalization
        
        Returns:
            Emotional support response string
        """
        # Build context
        context_parts = []
        
        if user.streaks.current_streak > 0:
            context_parts.append(f"Current streak: {user.streaks.current_streak} days")
        
        if user.constitution.current_mode:
            context_parts.append(f"Mode: {user.constitution.current_mode}")
        
        if user.accountability_partner_name:
            context_parts.append(f"Has accountability partner: {user.accountability_partner_name}")
        
        context = ". ".join(context_parts) if context_parts else "No additional context"
        
        prompt = f"""
You are Ayush's constitution AI agent providing emotional support.

User emotion: {emotion_type}
User message: "{user_message}"
User context: {context}

Constitution protocol for {emotion_type}:
VALIDATE: {protocol.get('validate', 'N/A')}
REFRAME: {protocol.get('reframe', 'N/A')}
TRIGGER: {protocol.get('trigger', 'N/A')}
ACTIONS: {', '.join(protocol.get('actions', []))}

Generate a response using this EXACT structure:

1. VALIDATE (2 sentences): Acknowledge the emotion using the protocol's validation text. Personalize slightly but keep the core message.

2. REFRAME (2 sentences): Reframe using constitution principles from the protocol. Connect to their current situation.

3. TRIGGER (1 question): Ask what specifically triggered this feeling right now. Use protocol's trigger question.

4. ACTION (3 specific steps): List 3 immediate concrete actions from the protocol. Number them clearly.

Requirements:
- Tone: Firm but compassionate. Like a coach, not a therapist.
- Length: 200-300 words total
- Structure: Must follow 4-step protocol exactly
- Personalization: Reference their streak/mode if relevant
- Direct: No fluff, no platitudes
- Action-oriented: End with clear next steps

Generate the response now:
"""
        
        response = await self.llm_service.generate_text(
            prompt=prompt,
            max_tokens=400
        )
        
        return response.strip()
```

#### 2. Constitution Protocols

**Update:** `constitution.md`

**Add Section:**

```markdown
---

## 🧠 Emotional Support Protocols

### Protocol: Loneliness

**VALIDATE:** "Loneliness is real and temporary. Your intentional celibacy phase is by design, not default."

**REFRAME:** "You're building the foundation for the life partner you deserve. This is strategic isolation, not abandonment. You're in monk mode preparing for the relationship that will last."

**TRIGGER:** "What specifically triggered this feeling right now? Time of day? Something you saw? Someone you saw?"

**ACTIONS:**
1. Text one friend right now: "Hey, what's up?" (Don't isolate further)
2. Go to gym, cafe, or any public place (Physical presence of others helps)
3. If you can't leave house: 20 pushups, cold shower, or call someone

**REMINDER:** Your constitution says relationships in May-June 2026. This feeling is temporary. Your mission is permanent.

---

### Protocol: Porn Urge

**VALIDATE:** "The urge is normal. Acknowledging it is strength, not weakness. You're not broken for feeling this."

**REFRAME:** "Porn is the enemy of your constitution. One relapse = 7-day reset minimum. Your X-day streak represents months of discipline. One urge is not worth destroying that."

**TRIGGER:** "What triggered this? Boredom? Loneliness? Stress? Late-night scrolling? Identify the pattern."

**ACTIONS:**
1. Cold shower RIGHT NOW (Interrupt the physiological pattern)
2. Text accountability partner: "Having urges, need support" (Immediate accountability)
3. Leave your room, go to public place immediately (Remove yourself from privacy)

**EMERGENCY:** If urge is overwhelming, text 3 people. Don't give yourself permission to be alone with the urge.

**REMINDER:** Every streak day is a victory. Don't throw it away for 10 minutes of dopamine.

---

### Protocol: Breakup Thoughts

**VALIDATE:** "Missing her is natural. The relationship mattered. Your feelings are valid."

**REFRAME:** "But remember Feb 2025: 6-month spiral after breakup. Reaching out led to inconsistency, confusion, and regression. Your constitution says: relationships disrupting sleep/training are violations. That relationship violated your boundaries repeatedly."

**TRIGGER:** "What triggered this thought? Saw something that reminded you? Feeling lonely? Bored? Specific memory?"

**ACTIONS:**
1. Review your journal from Feb-Aug 2025 (Reality check - it was toxic)
2. Text a friend about how you're feeling (Don't contact her)
3. Gym session or 30-minute walk (Physical release)

**BOUNDARY:** No contact until May 2026 at earliest. That's 3 months away. If you still want to reach out then, reassess. Not today.

**REMINDER:** "Just one more time" is the lie that led to 6 months of regression. Don't repeat history.

---

### Protocol: Stress/Anxiety

**VALIDATE:** "Stress is your body's response to demands. It's not weakness, it's a signal."

**REFRAME:** "Your constitution handles stress through systems, not emotion. Career stress? LeetCode + applications. Physical stress? Training + sleep. Mental stress? Deep work + boundaries."

**TRIGGER:** "What specifically is causing this stress? Is it actionable? If yes, what's the next smallest step?"

**ACTIONS:**
1. Brain dump: Write down every stressor (Externalize the anxiety)
2. Identify ONE action you can take in next 15 minutes (Action beats rumination)
3. Execute that action, then reassess (Progress creates momentum)

**EMERGENCY:** If stress is overwhelming (8-10/10), do this immediately:
- 10 minutes of controlled breathing (Box breathing: 4-4-4-4)
- Cold shower or face dunk in ice water
- Call someone (Don't isolate in the stress)

**REMINDER:** Your constitution says "Evidence over emotion." What's the evidence this stress is insurmountable? Vs what's the fear?

---

### Protocol: General Emotional Support

(For emotions not fitting above categories)

**VALIDATE:** "Whatever you're feeling is valid. Emotions are data, not directives."

**REFRAME:** "Your constitution gives you a framework when emotions are loud. Return to your principles: Physical sovereignty, Create don't consume, Evidence over emotion, Top 1% or nothing."

**TRIGGER:** "What's the feeling? What triggered it? What does it want you to do? (Identify before acting)"

**ACTIONS:**
1. Physical reset: Cold shower, pushups, or 10-min walk
2. Write it out: Journal for 5 minutes without filter
3. Constitution check: Which principle applies here?

**REMINDER:** Difficult moments pass. Your long-term trajectory is what matters.
```

#### 3. Constitution Service Enhancement

**File:** `src/services/constitution_service.py`

**New Method:**

```python
def get_emotional_protocol(self, emotion_type: str) -> dict:
    """
    Get emotional support protocol from constitution.
    
    Args:
        emotion_type: Type of emotion (loneliness, porn_urge, breakup, stress, general)
    
    Returns:
        Dictionary with protocol keys: validate, reframe, trigger, actions
    """
    protocols = {
        "loneliness": {
            "validate": "Loneliness is real and temporary. Your intentional celibacy phase is by design, not default.",
            "reframe": "You're building the foundation for the life partner you deserve. This is strategic isolation, not abandonment.",
            "trigger": "What specifically triggered this feeling right now?",
            "actions": [
                "Text one friend: 'Hey, what's up?'",
                "Go to gym or cafe (public place, no isolating)",
                "20 pushups if you can't leave house"
            ]
        },
        "porn_urge": {
            "validate": "The urge is normal. Acknowledging it is strength, not weakness.",
            "reframe": "Porn is the enemy. One relapse = 7-day reset. Your streak is worth more.",
            "trigger": "What triggered this? Boredom/Loneliness/Stress/Late-night scrolling?",
            "actions": [
                "Cold shower NOW (interrupt pattern)",
                "Text accountability partner: 'Having urges, need support'",
                "Leave room, go to public place immediately"
            ]
        },
        "breakup": {
            "validate": "Missing her is natural. The relationship mattered. Your feelings are valid.",
            "reframe": "Feb 2025: 6-month spiral after reaching out. Your constitution says relationships disrupting sleep/training are violations.",
            "trigger": "What triggered this thought? Saw something? Feeling lonely? Specific memory?",
            "actions": [
                "Review journal from Feb-Aug 2025 (reality check)",
                "Text a friend about how you're feeling (not her)",
                "Gym session or 30-minute walk"
            ]
        },
        "stress": {
            "validate": "Stress is your body's response to demands. It's a signal, not weakness.",
            "reframe": "Your constitution handles stress through systems, not emotion. Career stress? LeetCode. Physical stress? Training. Mental stress? Deep work.",
            "trigger": "What specifically is causing this stress? Is it actionable? What's the next smallest step?",
            "actions": [
                "Brain dump: Write down every stressor",
                "Identify ONE action for next 15 minutes",
                "Execute that action, then reassess"
            ]
        },
        "general": {
            "validate": "Whatever you're feeling is valid. Emotions are data, not directives.",
            "reframe": "Your constitution gives framework when emotions are loud. Return to principles: Physical sovereignty, Create don't consume, Evidence over emotion.",
            "trigger": "What's the feeling? What triggered it? What does it want you to do?",
            "actions": [
                "Physical reset: Cold shower or 10-min walk",
                "Write it out: Journal for 5 minutes",
                "Constitution check: Which principle applies?"
            ]
        }
    }
    
    return protocols.get(emotion_type, protocols["general"])
```

#### 4. Firestore Service Enhancement

**File:** `src/services/firestore_service.py`

**New Method:**

```python
def store_emotional_interaction(
    self,
    user_id: str,
    emotion_type: str,
    user_message: str,
    bot_response: str,
    timestamp: datetime
) -> None:
    """
    Store emotional support interaction for tracking.
    
    Args:
        user_id: User ID
        emotion_type: Classified emotion
        user_message: User's message
        bot_response: Bot's response
        timestamp: Interaction timestamp
    """
    self.db.collection('emotional_interactions').add({
        'user_id': user_id,
        'emotion_type': emotion_type,
        'user_message': user_message,
        'bot_response': bot_response,
        'timestamp': timestamp,
        'created_at': firestore.SERVER_TIMESTAMP
    })
```

#### 5. Supervisor Agent Update

**File:** `src/agents/supervisor.py`

**Update Method:**

```python
async def classify_intent(self, state: ConstitutionState) -> ConstitutionState:
    """
    Classify user's intent from message.
    
    Existing intents: checkin, query, command
    NEW Phase 3B: emotional
    
    Args:
        state: Current conversation state
    
    Returns:
        State with classified intent
    """
    message_lower = state.message.lower()
    
    # Command intent (highest priority)
    if message_lower.startswith('/'):
        state.intent = Intent.COMMAND
        return state
    
    # NEW: Emotional intent (check emotional keywords)
    emotional_keywords = [
        "lonely", "loneliness", "alone",
        "urge", "urges", "tempted", "temptation",
        "miss", "missing", "ex", "breakup",
        "stressed", "stress", "anxious", "anxiety", "overwhelmed",
        "help", "struggling", "hard", "difficult",
        "feeling", "feel"
    ]
    
    if any(keyword in message_lower for keyword in emotional_keywords):
        state.intent = Intent.EMOTIONAL
        return state
    
    # Check-in intent
    checkin_keywords = ["checkin", "check in", "check-in", "ready"]
    if any(keyword in message_lower for keyword in checkin_keywords):
        state.intent = Intent.CHECKIN
        return state
    
    # Query intent (questions about data)
    query_keywords = ["average", "compliance", "streak", "how many", "show me", "what's my"]
    if any(keyword in message_lower for keyword in query_keywords):
        state.intent = Intent.QUERY
        return state
    
    # Default to query for general messages
    state.intent = Intent.QUERY
    return state
```

**Update Intent Enum:**

```python
# src/agents/state.py

class Intent(str, Enum):
    CHECKIN = "checkin"
    QUERY = "query"
    COMMAND = "command"
    EMOTIONAL = "emotional"  # NEW
```

#### 6. LangGraph Integration

**File:** `src/main.py` (webhook handler)

**Update graph to include emotional agent:**

```python
# Update the agent routing in your LangGraph workflow

async def route_to_agent(state: ConstitutionState) -> str:
    """Determine which agent to route to based on intent"""
    
    if state.intent == Intent.CHECKIN:
        return "checkin_agent"
    elif state.intent == Intent.EMOTIONAL:  # NEW
        return "emotional_agent"
    elif state.intent == Intent.QUERY:
        return "query_agent"
    elif state.intent == Intent.COMMAND:
        return "command_handler"
    else:
        return "query_agent"  # Default
```

### User Experience

**Scenario: User Feeling Lonely**

```
User: "I'm feeling really lonely tonight"
  ↓
Supervisor: Detects "lonely" keyword → emotional intent
  ↓
Emotional Agent:
  1. Classifies as "loneliness"
  2. Loads loneliness protocol from constitution
  3. Generates personalized response with Gemini
  ↓
Bot Response:
"I hear you. Loneliness is real and it's temporary. Your intentional 
celibacy phase is by design, not default. You're building the foundation 
for the life partner you deserve. This is strategic isolation, not abandonment.

What specifically triggered this feeling right now?

Here's what you need to do RIGHT NOW:
1. Text one friend: 'Hey, what's up?'
2. Go to gym or cafe (public place, don't isolate)
3. If you can't leave: 20 pushups

You got this. Your 47-day streak proves you can handle difficult moments."
  ↓
Interaction logged in Firestore for tracking
```

---

## Implementation Plan

### Day 1-3: Ghosting Detection

#### Day 1: Pattern Detection Logic

**Tasks:**
1. Add `detect_ghosting()` method to `pattern_detection.py`
2. Add helper methods: `_calculate_days_since_checkin()`, `_get_ghosting_severity()`
3. Update `scan_patterns()` to include ghosting detection
4. Write unit tests for ghosting detection logic

**Deliverable:** Ghosting pattern detection functional and tested

#### Day 2: Intervention Messages

**Tasks:**
1. Add `_build_ghosting_intervention()` to `intervention.py`
2. Test all 4 severity levels (Day 2, 3, 4, 5+)
3. Add shield info to Day 5+ message
4. Update intervention logging

**Deliverable:** Escalating intervention messages working

#### Day 3: Integration & Testing

**Tasks:**
1. Test end-to-end: Create user, trigger ghosting, verify messages
2. Test pattern scan cron job includes ghosting
3. Test edge cases (check-in during escalation, no partner)
4. Documentation

**Deliverable:** Ghosting detection fully integrated and tested

---

### Day 4-5: Accountability Partner System

#### Day 4: Partner Commands & Linking

**Tasks:**
1. Add `set_partner_command()` to `telegram_bot.py`
2. Add `accept_partner_callback()` and `decline_partner_callback()`
3. Add `unlink_partner_command()`
4. Add `get_user_by_telegram_username()` to `firestore_service.py`
5. Add `set_accountability_partner()` to `firestore_service.py`
6. Update User model to include `telegram_username`

**Deliverable:** Partner linking functional

#### Day 5: Day 5 Escalation

**Tasks:**
1. Add `_notify_accountability_partner()` to `intervention.py`
2. Update `trigger_intervention()` to call partner notification on Day 5
3. Test with 2 users: Link partners, trigger Day 5 ghosting, verify notification
4. Add logging for partner notifications

**Deliverable:** Partner escalation working end-to-end

---

### Day 6-9: Emotional Support Agent

#### Day 6: Agent Scaffolding

**Tasks:**
1. Create `src/agents/emotional_agent.py`
2. Implement `EmotionalSupportAgent` class structure
3. Implement `_classify_emotion()` method
4. Add Intent.EMOTIONAL to state.py
5. Write unit tests for emotion classification

**Deliverable:** Emotional agent scaffolding complete

#### Day 7: Protocols & Response Generation

**Tasks:**
1. Add emotional support protocols to `constitution.md`
2. Add `get_emotional_protocol()` to `constitution_service.py`
3. Implement `_generate_emotional_response()` method
4. Add `store_emotional_interaction()` to `firestore_service.py`
5. Test response generation for each emotion type

**Deliverable:** Response generation working for all 5 emotion types

#### Day 8: Supervisor Routing

**Tasks:**
1. Update `classify_intent()` in `supervisor.py` to detect emotional keywords
2. Update LangGraph routing to include emotional agent
3. Test supervisor correctly routes emotional messages
4. Test edge cases (ambiguous messages, multiple intents)

**Deliverable:** Emotional agent integrated into conversation flow

#### Day 9: End-to-End Testing & Polish

**Tasks:**
1. Test all 5 emotion types end-to-end
2. Verify response quality (validate/reframe/trigger/action structure)
3. Test with real messages (role-play scenarios)
4. Refine prompts if responses are generic
5. Add error handling and fallback responses
6. Documentation and code cleanup

**Deliverable:** Emotional agent fully functional and polished

---

## Testing Strategy

### Unit Tests

#### Ghosting Detection Tests

```python
# tests/test_pattern_detection.py

def test_ghosting_detection_day_2():
    """Test ghosting detected on Day 2"""
    user = create_test_user(last_checkin_date="2026-02-02")  # 2 days ago
    
    pattern = pattern_detection_agent.detect_ghosting(user.user_id)
    
    assert pattern is not None
    assert pattern.type == "ghosting"
    assert pattern.severity == "nudge"
    assert pattern.data["days_missing"] == 2


def test_ghosting_detection_day_5():
    """Test ghosting escalates to emergency on Day 5"""
    user = create_test_user(last_checkin_date="2026-01-30")  # 5 days ago
    
    pattern = pattern_detection_agent.detect_ghosting(user.user_id)
    
    assert pattern.severity == "emergency"
    assert pattern.data["days_missing"] == 5


def test_no_ghosting_day_1():
    """Test no ghosting on Day 1 (grace period)"""
    user = create_test_user(last_checkin_date="2026-02-03")  # 1 day ago
    
    pattern = pattern_detection_agent.detect_ghosting(user.user_id)
    
    assert pattern is None  # Grace period
```

#### Accountability Partner Tests

```python
# tests/test_accountability_partner.py

async def test_set_partner_success():
    """Test successful partner linking"""
    user_a = create_test_user("user_a", telegram_username="userA")
    user_b = create_test_user("user_b", telegram_username="userB")
    
    # User A requests User B as partner
    await telegram_bot.set_partner_command(
        update=mock_update(user_a, "/set_partner @userB"),
        context=mock_context()
    )
    
    # Verify invite sent
    assert_message_sent_to(user_b, contains="partnership request")


async def test_partner_notification_day_5():
    """Test partner notified on Day 5 ghosting"""
    user = create_test_user(last_checkin_date="2026-01-30")  # 5 days ago
    partner = create_test_user()
    
    # Link partners
    firestore_service.set_accountability_partner(user.user_id, partner.user_id, partner.name)
    
    # Trigger Day 5 ghosting intervention
    pattern = Pattern(type="ghosting", severity="emergency", data={"days_missing": 5, ...})
    await intervention_agent.trigger_intervention(user.user_id, pattern)
    
    # Verify partner notified
    assert_message_sent_to(partner, contains="hasn't checked in for 5 days")
```

#### Emotional Agent Tests

```python
# tests/test_emotional_agent.py

async def test_emotion_classification_loneliness():
    """Test loneliness correctly classified"""
    emotion = await emotional_agent._classify_emotion("I'm feeling really lonely tonight")
    
    assert emotion == "loneliness"


async def test_emotion_classification_porn_urge():
    """Test porn urge correctly classified"""
    emotion = await emotional_agent._classify_emotion("Having strong urges right now")
    
    assert emotion == "porn_urge"


async def test_emotional_response_structure():
    """Test response follows 4-step protocol"""
    state = ConstitutionState(
        user_id="test_user",
        message="I'm feeling lonely",
        intent=Intent.EMOTIONAL
    )
    
    updated_state = await emotional_agent.process(state)
    response = updated_state.response
    
    # Verify response has all 4 components
    assert "lonely" in response.lower()  # Validation
    assert "?" in response  # Trigger question
    assert "1." in response  # Actions listed
    assert len(response.split()) >= 50  # Substantial response
```

### Integration Tests

#### End-to-End Ghosting Flow

```python
# tests/integration/test_ghosting_flow.py

async def test_full_ghosting_escalation():
    """Test complete Day 2-5 ghosting escalation"""
    user = create_test_user()
    
    # Check in Monday
    await complete_checkin(user.user_id, date="2026-02-03")
    
    # Skip Tuesday (Day 1 - grace period)
    # Pattern scan runs - no ghosting detected yet
    patterns = await pattern_detection_agent.scan_patterns(user.user_id)
    assert not any(p.type == "ghosting" for p in patterns)
    
    # Skip Wednesday (Day 2 - ghosting starts)
    patterns = await pattern_detection_agent.scan_patterns(user.user_id)
    ghosting = next(p for p in patterns if p.type == "ghosting")
    assert ghosting.severity == "nudge"
    assert_message_sent_to(user, contains="Missed you yesterday")
    
    # Skip Thursday (Day 3 - warning)
    patterns = await pattern_detection_agent.scan_patterns(user.user_id)
    ghosting = next(p for p in patterns if p.type == "ghosting")
    assert ghosting.severity == "warning"
    assert_message_sent_to(user, contains="3 days missing")
    
    # Skip Friday (Day 4 - critical)
    patterns = await pattern_detection_agent.scan_patterns(user.user_id)
    ghosting = next(p for p in patterns if p.type == "ghosting")
    assert ghosting.severity == "critical"
    assert_message_sent_to(user, contains="4-day absence")
    
    # Skip Saturday (Day 5 - emergency)
    patterns = await pattern_detection_agent.scan_patterns(user.user_id)
    ghosting = next(p for p in patterns if p.type == "ghosting")
    assert ghosting.severity == "emergency"
    assert_message_sent_to(user, contains="EMERGENCY")
```

#### End-to-End Emotional Support Flow

```python
# tests/integration/test_emotional_support_flow.py

async def test_full_emotional_support_flow():
    """Test user message → emotional response"""
    user = create_test_user()
    
    # User sends emotional message
    update = mock_telegram_update(
        user_id=user.telegram_id,
        message="I'm feeling really lonely tonight"
    )
    
    # Process through supervisor → emotional agent
    await telegram_bot.handle_message(update, context)
    
    # Verify response sent
    sent_messages = get_sent_messages(user.telegram_id)
    assert len(sent_messages) == 1
    
    response = sent_messages[0]
    
    # Verify response structure
    assert "loneliness" in response.lower() or "lonely" in response.lower()  # Validation
    assert "?" in response  # Trigger question
    assert "1." in response and "2." in response and "3." in response  # Actions
    
    # Verify interaction logged
    interactions = firestore_service.get_emotional_interactions(user.user_id)
    assert len(interactions) == 1
    assert interactions[0]["emotion_type"] == "loneliness"
```

### Manual Testing Checklist

**Ghosting Detection:**
- [ ] User ghosts Day 2 → receives "Missed you" message
- [ ] User ghosts Day 3 → receives "3 days missing" warning
- [ ] User ghosts Day 4 → receives historical pattern reference
- [ ] User ghosts Day 5 → receives emergency message
- [ ] User with partner ghosts Day 5 → partner receives notification
- [ ] User checks in during escalation → ghosting pattern resolved, no more messages

**Accountability Partner:**
- [ ] User A sends /set_partner @UserB → User B receives invite
- [ ] User B accepts → Both users linked bidirectionally
- [ ] User B declines → Both users notified, no link created
- [ ] User A sends /unlink_partner → Both users unlinked
- [ ] Day 5 ghosting with partner → Partner notified
- [ ] Day 5 ghosting without partner → No crash, emergency message still sent

**Emotional Support:**
- [ ] "I'm feeling lonely" → Loneliness protocol response
- [ ] "Having porn urges" → Porn urge protocol response
- [ ] "Missing my ex" → Breakup protocol response
- [ ] "Feeling stressed" → Stress protocol response
- [ ] Generic emotional message → General protocol response
- [ ] Response follows 4-step structure (validate, reframe, trigger, action)
- [ ] Response is personalized (mentions streak, mode, etc.)

---

## Deployment Plan

### Pre-Deployment Checklist

- [ ] All unit tests passing (30+ tests)
- [ ] All integration tests passing (5+ scenarios)
- [ ] Manual testing complete (18 test cases)
- [ ] Code reviewed and cleaned up
- [ ] Documentation updated
- [ ] Constitution.md updated with emotional protocols
- [ ] Firestore indexes created (if needed)
- [ ] Cost projections validated

### Deployment Steps

#### Step 1: Update Constitution

```bash
# No deployment needed - just git commit
git add constitution.md
git commit -m "Add emotional support protocols to constitution"
```

#### Step 2: Deploy Code

```bash
# Deploy to Cloud Run
gcloud run deploy constitution-agent \
  --source . \
  --region asia-south1 \
  --allow-unauthenticated

# Verify health
curl https://constitution-agent-2lvj3hhnkq-el.a.run.app/health
```

#### Step 3: Test End-to-End

1. **Test Ghosting Detection:**
   - Create test user
   - Don't check in for 2 days
   - Verify Day 2 ghosting message received

2. **Test Partner System:**
   - Create 2 test users
   - Link as partners: /set_partner @user2
   - Verify invite and acceptance flow

3. **Test Emotional Support:**
   - Send emotional message: "I'm feeling lonely"
   - Verify CBT-style response received
   - Check Firestore for logged interaction

#### Step 4: Monitor

```bash
# Watch logs in real-time
gcloud run services logs tail constitution-agent --region=asia-south1

# Look for:
# - "Processing emotional support for user..."
# - "Classified emotion: loneliness"
# - "Partner notification sent..."
# - "Ghosting pattern detected: Day X"
```

### Rollback Plan

If critical issues found:

1. **Revert to previous Cloud Run revision:**
   ```bash
   gcloud run services update-traffic constitution-agent \
     --to-revisions=PREVIOUS_REVISION=100 \
     --region=asia-south1
   ```

2. **If emotional agent causes issues:**
   - Disable emotional routing in supervisor (comment out emotional intent)
   - Redeploy
   - Fix issues locally
   - Test thoroughly
   - Redeploy with fix

### Post-Deployment Monitoring

**Week 1 (Feb 5-11):**
- Monitor emotional agent usage (how many interactions?)
- Check response quality (are responses helpful? Generic?)
- Track ghosting detection (false positives? Missing real ghosting?)
- Monitor partner system adoption

**Success Metrics:**
- Emotional agent used by at least 1 user in first week
- No crashes or error spikes
- Ghosting detection working (test manually)
- Partner system functional (link 2+ user pairs)

---

## Success Criteria

### Functional Criteria (Must Have)

- ✅ Ghosting detection triggers on Day 2, 3, 4, 5
- ✅ Escalation messages progressively more urgent
- ✅ Partner linking works bidirectionally
- ✅ Partner notification sent on Day 5 ghosting
- ✅ Emotional agent handles 5 emotion types
- ✅ Supervisor routes emotional messages correctly
- ✅ Emotional responses follow 4-step protocol
- ✅ No regressions in Phase 1-2-3A functionality

### Quality Criteria (Should Have)

- ✅ Ghosting messages reference user's actual streak
- ✅ Day 4 message references historical patterns (Feb 2025)
- ✅ Emotional responses are personalized (not generic)
- ✅ Emotional responses mention user's streak/mode if relevant
- ✅ Partner notifications are clear and actionable
- ✅ All error cases handled gracefully (no crashes)

### Business Criteria (Nice to Have)

- ✅ 7-day churn reduced by 30%+ (vs Phase 3A baseline)
- ✅ Emotional agent used by 20%+ of users monthly
- ✅ Partner feature adopted by 10%+ of user pairs
- ✅ User feedback positive ("helpful", "felt supported")

### Technical Criteria (Must Have)

- ✅ Cost increase <$0.20/month for 10 users
- ✅ No performance degradation (response time <2s)
- ✅ All tests passing (30+ unit, 5+ integration)
- ✅ Code coverage >80% for new code
- ✅ Documentation complete (this spec + inline comments)

---

## Risk Mitigation

### Risk 1: Bad Emotional Advice

**Risk:** Gemini generates inappropriate/harmful emotional support.

**Likelihood:** Medium (AI can be unpredictable)

**Impact:** High (user trust lost, potential harm)

**Mitigation:**
1. Hardcode protocols in constitution.md (AI only rephrases, doesn't create)
2. Include disclaimer in emotional responses: "AI support, not therapy. If crisis: call 988"
3. Log all emotional interactions for manual review
4. Test thoroughly with edge cases before launch
5. Add fallback: If emotion classification fails, use generic supportive message

**Monitoring:**
- Review 100% of emotional interactions first week
- Check for concerning patterns (suicidal ideation, self-harm)
- Have human escalation path if concerning message detected

### Risk 2: Partner Spam

**Risk:** Users annoyed by partner notifications.

**Likelihood:** Low (only Day 5+ ghosting)

**Impact:** Medium (user disables notifications, quits)

**Mitigation:**
1. Only notify on Day 5+ (rare event, 1-2x per month max)
2. Allow /unlink_partner command (easy opt-out)
3. Limit to 1 notification per ghosting episode (don't spam daily)
4. Make notification valuable ("Your partner needs you" vs "FYI they're missing")

### Risk 3: False Positive Ghosting

**Risk:** User on vacation → gets "EMERGENCY" messages.

**Likelihood:** Medium (users travel, get sick, etc.)

**Impact:** Low (annoying but not harmful)

**Mitigation:**
1. Escalation is gradual (Day 2 gentle → Day 5 emergency)
2. User can dismiss by checking in (even minimal check-in resolves)
3. Future: Add /vacation command (Phase 3C)
4. Day 2-3 messages are gentle enough to not cause alarm

### Risk 4: Emotion Misclassification

**Risk:** User says "lonely" but means something else → wrong protocol.

**Likelihood:** Medium (language is ambiguous)

**Impact:** Low (still gets supportive response, just wrong protocol)

**Mitigation:**
1. General protocol covers all emotions (fallback)
2. LLM classification is pretty good (GPT-4 level)
3. User can clarify and get better response next time
4. Log misclassifications and improve over time

### Risk 5: Cost Overrun

**Risk:** Emotional agent usage higher than expected → cost spike.

**Likelihood:** Low (5-10 uses per user per month max)

**Impact:** Low ($0.15 → $0.30 is still cheap)

**Mitigation:**
1. Set budget alert at $2/month (double current)
2. Monitor token usage per emotion type
3. Optimize prompts if needed (shorter prompts, cache constitution)
4. Rate limit if abuse detected (1 emotional message per 10 minutes)

---

## Appendix A: Example Emotional Responses

### Loneliness Example

**User:** "I'm feeling really lonely tonight"

**Bot Response:**

```
I hear you. Loneliness is real and it's temporary. Your intentional celibacy phase is by design, not default. You're building the foundation for the life partner you deserve. This is strategic isolation, not abandonment. You're in monk mode preparing for the relationship that will last.

What specifically triggered this feeling right now? Time of day? Something you saw? Someone you saw?

Here's what you need to do RIGHT NOW:
1. Text one friend: "Hey, what's up?" (Don't isolate further)
2. Go to gym, cafe, or any public place (Physical presence helps)
3. If you can't leave: 20 pushups, cold shower, or call someone

Your 47-day streak proves you can handle difficult moments. This feeling is temporary. Your mission is permanent.
```

### Porn Urge Example

**User:** "Having really strong urges right now"

**Bot Response:**

```
I hear you. The urge is normal. Acknowledging it is strength, not weakness. You're not broken for feeling this.

But here's the reality: Porn is the enemy of your constitution. One relapse = 7-day reset minimum. Your 47-day streak represents months of discipline. One urge is not worth destroying that.

What triggered this? Boredom? Loneliness? Stress? Late-night scrolling? Identify the pattern so we can prevent it next time.

Here's what you need to do RIGHT NOW:
1. Cold shower RIGHT NOW (Interrupt the physiological pattern)
2. Text your accountability partner: "Having urges, need support" (Immediate accountability)
3. Leave your room, go to public place immediately (Remove yourself from privacy)

Every streak day is a victory. Don't throw away 47 days for 10 minutes of dopamine. You're stronger than this urge.
```

### Breakup Thoughts Example

**User:** "Missing my ex a lot tonight. Thinking about reaching out"

**Bot Response:**

```
I hear you. Missing her is natural. The relationship mattered. Your feelings are valid.

But remember Feb 2025: 6-month spiral after reaching out. The inconsistency, the confusion, the regression. Your constitution says relationships disrupting sleep/training are violations. That relationship violated your boundaries repeatedly. You know this.

What triggered this thought? Saw something that reminded you? Feeling lonely? Bored? Specific memory? Understanding the trigger helps you avoid it next time.

Here's what you need to do RIGHT NOW:
1. Review your journal from Feb-Aug 2025 (Reality check - it was toxic)
2. Text a friend about how you're feeling (Don't contact her)
3. Gym session or 30-minute walk (Physical release)

Boundary: No contact until May 2026 at earliest. That's 3 months away. If you still want to reach out then, reassess. Not tonight. "Just one more time" is the lie that led to 6 months of regression. Don't repeat history.
```

---

## Appendix B: Firestore Collections

### New Collection: emotional_interactions

```
emotional_interactions/
  {interaction_id}/
    - user_id: string
    - emotion_type: string ("loneliness" | "porn_urge" | "breakup" | "stress" | "general")
    - user_message: string
    - bot_response: string
    - timestamp: datetime
    - created_at: server_timestamp
```

**Purpose:** Track emotional support usage for:
- Analytics (which emotions most common?)
- Quality review (are responses helpful?)
- Pattern detection (user in emotional crisis frequently?)

**Queries Needed:**
- Get all interactions for user
- Get interactions by emotion type
- Count interactions per user per month

---

## Appendix C: Cost Breakdown

### Additional AI Costs (10 Users, 1 Month)

| Operation | Frequency | Tokens | Cost/Call | Monthly Cost |
|-----------|-----------|--------|-----------|--------------|
| Emotion classification | 5 calls/user/month | ~50 | $0.000013 | $0.00065 |
| Emotional response generation | 5 calls/user/month | ~300 | $0.000075 | $0.00375 |
| Ghosting detection | 0 (rule-based) | 0 | $0 | $0 |
| Partner notification | 0.1 calls/user/month | 0 | $0 | $0 |
| **Phase 3B Total** | | | | **$0.044/month** |

**Projected Total Cost:**
- Phase 3A: $1.26/month
- Phase 3B: +$0.04/month
- **Total: $1.30/month** for 10 users

Even better than estimated! ✅

---

**END OF SPECIFICATION**

---

**Document Version:** 1.0  
**Last Updated:** February 4, 2026  
**Status:** Ready for Implementation  
**Approved By:** User (Ayush)  
**Next Steps:** Begin Day 1 implementation (Ghosting Detection)
