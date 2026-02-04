# Phase 3B Days 4-5: Accountability Partner System

**Date:** February 4, 2026  
**Status:** ✅ Complete  
**Files Modified:** 3

---

## 📋 Summary

Implemented complete **accountability partner system** including:
- Partner linking via `/set_partner @username`  
- Invite/accept/decline flow with inline buttons
- Partner unlinking via `/unlink_partner`
- Day 5 ghosting → automatic partner notification

---

## 🎯 Day 4: Partner Commands Implementation

### **1. Firestore Service Methods**

**File:** `src/services/firestore_service.py`

#### `get_user_by_telegram_username()`
```python
def get_user_by_telegram_username(self, telegram_username: str) -> Optional[User]:
```

**Purpose:** Search for user by Telegram username (used when requesting partner)

**Query:** `WHERE telegram_username == "john_doe" LIMIT 1`

**Returns:** User object if found, None otherwise

---

#### `set_accountability_partner()` (Updated)
```python
def set_accountability_partner(
    self,
    user_id: str,
    partner_id: Optional[str],
    partner_name: Optional[str]
) -> None:
```

**Purpose:** Link or unlink accountability partners

**To Link:** Pass partner_id and partner_name  
**To Unlink:** Pass None for both

**Bidirectional:** Must be called twice to link both users

---

### **2. Bot Commands**

**File:** `src/bot/telegram_bot.py`

#### `/set_partner @username`
```python
async def set_partner_command(self, update, context) -> None:
```

**Flow:**
1. Parse @username from command
2. Search for user by username
3. Send invite to partner with Accept/Decline buttons
4. Wait for partner response

**Inline Keyboard:**
```
[✅ Accept] [❌ Decline]
```

**Validation:**
- ✅ User exists and has started bot
- ✅ Not partnering with self
- ✅ Valid username format (@username)

---

#### Accept/Decline Callbacks
```python
async def accept_partner_callback(self, update, context) -> None:
async def decline_partner_callback(self, update, context) -> None:
```

**Callback Data Format:**
- Accept: `accept_partner:<requester_user_id>`
- Decline: `decline_partner:<requester_user_id>`

**Accept Flow:**
1. Link requester → accepter (bidirectional)
2. Notify both users of success
3. Edit original message to show confirmation

**Decline Flow:**
1. Edit original message to show decline
2. Notify requester of decline
3. No database changes

---

#### `/unlink_partner`
```python
async def unlink_partner_command(self, update, context) -> None:
```

**Purpose:** Remove accountability partnership

**Flow:**
1. Check if user has partner
2. Unlink bidirectionally
3. Notify both users

---

### **3. Handler Registration**

**File:** `src/bot/telegram_bot.py`

```python
# Commands
self.application.add_handler(CommandHandler("set_partner", self.set_partner_command))
self.application.add_handler(CommandHandler("unlink_partner", self.unlink_partner_command))

# Callbacks
self.application.add_handler(CallbackQueryHandler(self.accept_partner_callback, pattern="^accept_partner:"))
self.application.add_handler(CallbackQueryHandler(self.decline_partner_callback, pattern="^decline_partner:"))
```

---

## 🎯 Day 5: Partner Notification on Day 5 Ghosting

### **Partner Notification Logic**

**File:** `src/main.py` (pattern scan endpoint)

**Added After Intervention Sent:**
```python
# Phase 3B: Day 5 ghosting → Notify accountability partner
if pattern.type == "ghosting" and pattern.data.get("days_missing", 0) >= 5:
    if user.accountability_partner_id:
        # Get partner
        # Build notification message
        # Send to partner via Telegram
        # Log notification
```

**Notification Message:**
```
🚨 **Accountability Partner Alert**

Your partner **John Doe** hasn't checked in for **5 days**.

Last check-in: 2026-01-30

This is serious. Consider reaching out to check on them:
• Text them directly
• Call if you have their number
• Make sure they're okay

Sometimes people need a friend more than a bot.
```

---

## 🧠 Theory & Concepts

### **Why Accountability Partners?**

**Research-Backed:**
- Peer accountability increases compliance by **65%** (American Society of Training and Development)
- Social support is most effective intervention for behavior change
- Fear of disappointing friend > fear of disappointing bot

### **Bidirectional Linking**

**Why Not One-Way?**
- Relationships are mutual
- Both users should consent
- Both users benefit (if either ghosts, other is notified)

**Implementation:**
```python
# Link User A → User B
set_accountability_partner(user_a_id, user_b_id, user_b_name)

# Link User B → User A  
set_accountability_partner(user_b_id, user_a_id, user_a_name)
```

### **Why Day 5 Threshold?**

**Too Early (Day 2-3):**
- User might recover on their own
- Partner notification feels intrusive
- False alarms damage trust

**Too Late (Day 7+):**
- User already in spiral
- Harder to recover
- Intervention less effective

**Day 5 Sweet Spot:**
- Clear pattern (not accident)
- Still recoverable
- Partner can meaningfully help

---

## 📊 User Experience

### **Scenario 1: Successful Partnership**

```
User A: /set_partner @UserB
Bot → User A: "✅ Partner request sent to @UserB! Waiting..."

Bot → User B: "👥 User A wants to be your partner. Accept?"
               [✅ Accept] [❌ Decline]

User B: [Clicks ✅ Accept]

Bot → User B: "✅ Partnership confirmed!"
Bot → User A: "✅ User B accepted your request!"

Database:
- User A: partner_id = UserB, partner_name = "User B"
- User B: partner_id = UserA, partner_name = "User A"
```

---

### **Scenario 2: Partnership Decline**

```
User A: /set_partner @UserB
Bot → User B: [Shows invite]

User B: [Clicks ❌ Decline]

Bot → User B: "❌ Partnership declined."
Bot → User A: "❌ User B declined your partnership request."

Database: No changes (no link created)
```

---

### **Scenario 3: Day 5 Partner Notification**

```
Day 1: User A checks in ✅
Day 2: User A ghosts (triple reminders sent)
Day 3: Day 3 ghosting intervention sent
Day 4: Day 4 critical intervention sent
Day 5: Day 5 emergency intervention sent
       ↓
       🚨 ALSO send to User B (partner):
       "Your partner User A hasn't checked in for 5 days..."

User B texts User A: "Hey, you okay?"
User A returns: "Thanks for checking, I'll get back on track"
User A: /checkin
```

---

## ✅ What's Working

**Day 4: Partner Commands**
- ✅ `/set_partner @username` command  
- ✅ Username search in Firestore
- ✅ Inline keyboard Accept/Decline buttons
- ✅ Bidirectional linking
- ✅ `/unlink_partner` command
- ✅ Both users notified on link/unlink

**Day 5: Partner Notification**
- ✅ Detects Day 5 ghosting patterns
- ✅ Checks if user has partner
- ✅ Sends notification to partner
- ✅ Logs notification event
- ✅ Handles missing partner gracefully

---

## 🔧 Edge Cases Handled

1. **User not found:** Clear error message, suggests /start
2. **Self-partnering:** Blocked with friendly error
3. **Partner hasn't started bot:** Clear message explaining requirement
4. **Partner declines:** Both users notified, no link created
5. **Unlinking without partner:** Clear error message
6. **Partner deleted account:** Graceful handling, unlinks on one side only
7. **Day 5 ghosting without partner:** Logged, no crash

---

## 📝 Database Schema

**User Document (Already Exists):**
```python
{
  "user_id": "user_123",
  "telegram_id": 123456789,
  "telegram_username": "john_doe",  # Used for partner search
  "name": "John Doe",
  
  # Phase 3B Fields:
  "accountability_partner_id": "user_456",    # Partner's user_id
  "accountability_partner_name": "Jane Smith" # Partner's display name
}
```

**No Migration Needed:** Fields added in Phase 3A, already deployed.

---

## 🎓 Key Learnings

### **1. Bidirectional Relationships are Tricky**
Must update both sides:
- Link: Call set_partner() twice
- Unlink: Call set_partner(None, None) twice
- Delete: Handle orphaned relationships

### **2. Inline Keyboards are Powerful**
Better UX than text commands:
- One-click action (no typing)
- Visual (buttons stand out)
- Callback data passes context

### **3. Social Accountability >> Bot Accountability**
Partner notification more effective than any bot message:
- Real person checking on you
- Social pressure (positive)
- Emotional connection

### **4. Consent Matters**
Always ask before linking:
- Not everyone wants partner
- Relationships are personal
- User autonomy respected

---

## ⏭️ What's Next (Days 6-9)

**Emotional Support Agent** (Feature 3):
- Day 6: Agent scaffolding
- Day 7: Protocols & response generation
- Day 8: Supervisor routing
- Day 9: End-to-end testing

**Features:**
- Loneliness support
- Porn urge intervention
- Breakup thought management
- Stress/anxiety support

---

**Status:** ✅ Days 1-5 complete (Feature 1-2)  
**Remaining:** Days 6-9 (Feature 3)

**Deployment Ready:** Yes (Days 1-5 tested and working)
