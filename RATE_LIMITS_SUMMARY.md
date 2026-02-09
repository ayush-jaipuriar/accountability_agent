# Current Rate Limits in Accountability Agent

**Generated:** February 9, 2026  
**Last Updated:** February 9, 2026 (Limits tripled)  
**Status:** ✅ Deployed and Active  
**Implementation:** Phase A (Feature 5)

---

## Table of Contents

1. [Overview](#overview)
2. [Rate Limiting Theory](#rate-limiting-theory)
3. [Tier System](#tier-system)
4. [Command Mapping](#command-mapping)
5. [How It Works](#how-it-works)
6. [Admin Bypass](#admin-bypass)
7. [User Experience](#user-experience)

---

## Overview

The accountability agent implements a **tiered rate limiting system** to protect expensive resources from abuse while maintaining a good user experience for legitimate usage.

**Why Rate Limiting?**

Without throttling, a single user (or malicious bot) could:
- ✅ Spam `/report` → generates 4 graphs + Gemini AI analysis each time
- ✅ Spam `/export pdf` → CPU-intensive PDF generation
- ✅ Flood AI queries → burns through Gemini API token budget
- ✅ Overwhelm Firestore → drives up read costs

**Implementation Location:** `src/utils/rate_limiter.py`

---

## Rate Limiting Theory

### Sliding Window Algorithm

The system uses a **sliding window approach** rather than fixed windows or token buckets.

**How it works:**

For each `(user_id, tier)` pair, we store timestamps of recent requests:

```
User 123, "expensive" tier:
[2026-02-09 14:30:00, 2026-02-09 15:15:00]
```

When a new request arrives:

1. **Prune old entries** — Remove timestamps older than 1 hour
2. **Check hourly limit** — Is the user under the max requests/hour?
3. **Check cooldown** — Has enough time passed since the last request?
4. **Record timestamp** — If allowed, add the current time to the list

**Why sliding window?**

- ✅ **More accurate** than fixed windows (no boundary burst issues)
- ✅ **Simpler** than token buckets (no refill rate math)
- ✅ **Memory efficient** — Auto-prunes after 1 hour

**Boundary Burst Problem (Fixed Window):**

```
Fixed window (1 hour blocks):
12:00-13:00 | 13:00-14:00

User sends:
- 12:59:50 → Request 1 (allowed)
- 12:59:55 → Request 2 (allowed)
- 13:00:05 → Request 3 (allowed) ❌ 3 requests in 15 seconds!

Sliding window prevents this by checking "last 60 minutes" continuously.
```

### Memory Considerations

Each user+tier entry stores a list of `datetime` objects (8 bytes each).

**Worst case:**
- 1000 users × 3 tiers × 30 entries = ~720KB

This is negligible. Entries auto-prune after 1 hour, so memory is bounded.

---

## Tier System

Commands are grouped by **resource cost**:

| Tier | Cooldown | Max/Hour | Description | Resource Cost |
|------|----------|----------|-------------|---------------|
| **Expensive** | 10 min | 6/hour | AI + graph generation | High CPU + Gemini API |
| **AI-Powered** | 40 sec | 60/hour | Gemini API calls | Gemini API tokens |
| **Standard** | 3 sec | 90/hour | Database reads only | Firestore reads |
| **Free** | None | Unlimited | No backend cost | Negligible |

### Tier Design Rationale

**Expensive Tier (10 min cooldown, 6/hour):**
- `/report` generates 4 matplotlib graphs + Gemini AI analysis
- `/export pdf` requires PDF rendering (CPU-intensive)
- **Cost:** ~$0.02 per report (Gemini API + compute)
- **Use case:** Weekly review, not real-time monitoring
- **Limit rationale:** 6/hour prevents abuse while allowing more frequent legitimate use (tripled from 2/hour)

**AI-Powered Tier (40 sec cooldown, 60/hour):**
- General AI queries (pattern detection, emotional support)
- `/support` command (CBT-based conversations)
- **Cost:** ~$0.001 per query (Gemini API tokens)
- **Use case:** Conversational AI, support sessions
- **Limit rationale:** 60/hour = 1 per minute on average, excellent for natural conversation (tripled from 20/hour)

**Standard Tier (3 sec cooldown, 90/hour):**
- `/stats`, `/partner_status`, `/leaderboard` — Firestore reads
- **Cost:** ~$0.0001 per query (Firestore read)
- **Use case:** Quick status checks
- **Limit rationale:** 3 sec prevents accidental spam, 90/hour is very generous (tripled from 30/hour)

**Free Tier (unlimited):**
- `/start`, `/help`, `/mode`, `/cancel` — No backend cost
- These are essential for onboarding and navigation

---

## Command Mapping

### Currently Rate-Limited Commands

| Command | Tier | Cooldown | Max/Hour | Reason |
|---------|------|----------|----------|--------|
| `/report` | Expensive | 10 min | 6 | Generates 4 graphs + AI analysis |
| `/export` | Expensive | 10 min | 6 | PDF generation (CPU-intensive) |
| `/support` | AI-Powered | 40 sec | 60 | Gemini API calls (CBT conversations) |
| General AI queries | AI-Powered | 40 sec | 60 | Gemini API calls (pattern detection) |
| `/stats` | Standard | 3 sec | 90 | Firestore reads |
| `/weekly` | Standard | 3 sec | 90 | Firestore reads |
| `/monthly` | Standard | 3 sec | 90 | Firestore reads |
| `/yearly` | Standard | 3 sec | 90 | Firestore reads |
| `/partner_status` | Standard | 3 sec | 90 | Firestore reads |
| `/leaderboard` | Standard | 3 sec | 90 | Firestore reads |
| `/achievements` | Standard | 3 sec | 90 | Firestore reads |
| `/share` | Standard | 3 sec | 90 | Firestore reads |

### Unlimited Commands (Free Tier)

These commands have **no rate limits**:

- `/start` — Onboarding
- `/help` — Help text
- `/mode` — Mode selection
- `/cancel` — Cancel current operation
- `/timezone` — Change timezone
- `/checkin` — Daily check-in (has separate "already checked in today" guard)
- `/set_partner` — Partner linking
- `/unlink_partner` — Partner unlinking
- `/use_shield` — Streak shield usage

**Why no limit on `/checkin`?**

Check-ins have a built-in guard: "You've already checked in today." This prevents spam without rate limiting. Users should be able to attempt check-ins freely (they might forget they already checked in).

---

## How It Works

### Example Flow: User Sends `/report`

```
1. User sends /report
   ↓
2. Bot calls: rate_limiter.check(user_id="12345", command="report")
   ↓
3. Rate limiter looks up:
   - Command tier: "report" → "expensive"
   - Tier config: cooldown=600s, max_per_hour=6
   ↓
4. Check user's history for "expensive" tier:
   - Prune entries older than 1 hour
   - Current entries: [2026-02-09 14:30:00]
   ↓
5. Check hourly limit:
   - Used: 1 request
   - Max: 6 requests
   - ✅ Under limit
   ↓
6. Check cooldown:
   - Last request: 14:30:00
   - Current time: 14:42:00
   - Elapsed: 12 minutes (720 seconds)
   - Cooldown: 10 minutes (600 seconds)
   - ✅ Cooldown passed
   ↓
7. Record new timestamp: [2026-02-09 14:30:00, 2026-02-09 15:05:00]
   ↓
8. Return: (allowed=True, message=None)
   ↓
9. Bot proceeds with /report generation
```

### Example Flow: Rate Limit Denial

```
1. User sends /report again at 14:48:00
   ↓
2. Rate limiter checks:
   - Last request: 14:42:00
   - Elapsed: 6 minutes (360 seconds)
   - Cooldown: 10 minutes (600 seconds)
   - Remaining: 4 minutes (240 seconds)
   ↓
3. Return: (allowed=False, message="⏳ Please wait 4m 0s before using this again.")
   ↓
4. Bot sends denial message to user (does NOT generate report)
```

---

## Admin Bypass

**Admins bypass ALL rate limits.**

### Configuration

Admin user IDs are loaded from environment variables at startup:

```python
# In main.py:
admin_ids = settings.admin_telegram_ids  # e.g., ["12345", "67890"]
rate_limiter.set_admin_ids(admin_ids)
```

### Why Admin Bypass?

- ✅ **Testing:** Admins need to test expensive commands repeatedly
- ✅ **Debugging:** Admins may need to generate reports for multiple users
- ✅ **Support:** Admins helping users shouldn't be blocked

### How It Works

```python
def check(self, user_id: str, command: str) -> Tuple[bool, Optional[str]]:
    tier = self.COMMAND_TIERS.get(command)
    if tier is None:
        return True, None  # Free tier
    
    # Admin bypass — checked BEFORE any rate limiting logic
    if user_id in self._admin_ids:
        return True, None  # ✅ Admins always allowed
    
    # ... normal rate limiting for non-admins
```

---

## User Experience

### Denial Messages

When a user is rate-limited, they receive a **user-friendly message** explaining:

1. **How long to wait** (human-readable)
2. **A helpful tip** (context-appropriate)

**Example denial messages:**

**Expensive tier (report):**
```
⏳ Please wait 8m 30s before using this again.

💡 Tip: Reports are most useful when reviewed weekly, not hourly!
```

**AI-Powered tier (support):**
```
⏳ Please wait 35s before using this again.

💡 Tip: Take a moment to reflect before our next chat.
```

**Standard tier (stats):**
```
⏳ Please wait 2s before using this again.

💡 Tip: This limit protects the service for all users.
```

**Hourly limit exceeded:**
```
⏳ You've used this 6 times in the last hour (limit: 6).

Try again when the oldest request expires.
```

### Tips by Command

| Command | Tip |
|---------|-----|
| `/report` | "Reports are most useful when reviewed weekly, not hourly!" |
| `/export` | "Your data isn't going anywhere — exports can wait." |
| `/support` | "Take a moment to reflect before our next chat." |
| General AI query | "Journaling your thoughts while waiting can help too." |
| Other | "This limit protects the service for all users." |

---

## Implementation Details

### Code Location

**Main implementation:** `src/utils/rate_limiter.py`

**Integration points:**
- `src/bot/telegram_bot.py` — All rate-limited command handlers call `_check_rate_limit()`
- `src/main.py` — Admin IDs loaded at startup

### Key Methods

```python
# Check if a command is allowed
allowed, message = rate_limiter.check(user_id, command)

# Get usage summary for a user (for debugging)
usage = rate_limiter.get_usage(user_id)

# Set admin IDs (called once at startup)
rate_limiter.set_admin_ids(admin_ids)

# Cleanup stale entries (called periodically)
cleaned_count = rate_limiter.cleanup()
```

### Thread Safety

**Python's GIL (Global Interpreter Lock)** ensures dict operations are atomic. For async code (our case), there's no concurrency issue since we're single-threaded within the event loop.

No locks or mutexes needed.

### Restart Behavior

**Rate limits reset on deployment/restart.**

This is **intentional** (fail-open design):

- ✅ **Better UX:** Denying all requests after restart would be worse than briefly allowing extra requests
- ✅ **Rare restarts:** Cloud Run keeps instances warm, restarts are infrequent
- ✅ **Bounded impact:** Even if limits reset, the worst case is 2 extra reports per user

**Alternative (fail-closed):** Persist rate limit state to Firestore. Rejected because:
- ❌ Adds Firestore writes on every command (cost + latency)
- ❌ Increases complexity
- ❌ Doesn't meaningfully improve security (restarts are rare)

---

## Testing

Rate limiting is tested in `tests/test_phase_a_monitoring_ratelimit.py`:

**Test coverage:**
- ✅ Basic rate limiting (cooldown + hourly limit)
- ✅ Admin bypass
- ✅ User isolation (one user's limits don't affect another)
- ✅ Tier definitions (all commands map to valid tiers)
- ✅ Cleanup (stale entries removed)
- ✅ Integration (bot commands use rate limiter)

**Test count:** 23 tests (all passing)

---

## Metrics

Rate limiting is tracked in the metrics system:

```python
# When a user is rate-limited:
metrics.increment("rate_limit_hits")
```

This allows monitoring:
- How often users hit rate limits
- Which commands are most rate-limited
- Whether limits are too strict or too lenient

---

## Future Enhancements

**Potential improvements (not currently implemented):**

1. **Per-tier usage command:** `/usage` shows user's current rate limit status
2. **Redis-backed limits:** For multi-instance deployments (not needed for single Cloud Run instance)
3. **Dynamic limits:** Adjust limits based on time of day or user tier (premium users get higher limits)
4. **Burst allowance:** Allow short bursts (e.g., 3 requests in 10 seconds) for legitimate use cases

---

## Summary Table

| Feature | Value |
|---------|-------|
| **Algorithm** | Sliding window |
| **Storage** | In-memory (dict) |
| **Tiers** | 4 (Expensive, AI-Powered, Standard, Free) |
| **Commands rate-limited** | 13 |
| **Commands unlimited** | 9 |
| **Admin bypass** | ✅ Yes |
| **Restart behavior** | Fail-open (limits reset) |
| **Memory usage** | ~720KB worst case |
| **Thread-safe** | ✅ Yes (GIL) |
| **Tested** | ✅ 23 tests passing |
| **Deployed** | ✅ Phase A (active) |
| **Limits** | 🔼 Tripled (Feb 9, 2026) |

---

*Document generated: February 9, 2026*  
*Last updated: February 9, 2026 (Limits tripled)*  
*Implementation: Phase A (Feature 5)*  
*Status: ✅ Deployed and Active*
