# Rate Limit Change Log

## February 9, 2026 - Limits Tripled

**Reason:** Increase user flexibility and reduce friction for legitimate usage patterns.

### Changes Made

All rate limits have been **tripled** across all tiers:

| Tier | Metric | Old Value | New Value | Change |
|------|--------|-----------|-----------|--------|
| **Expensive** | Cooldown | 30 min | 10 min | ÷ 3 |
| **Expensive** | Max/hour | 2 | 6 | × 3 |
| **AI-Powered** | Cooldown | 2 min | 40 sec | ÷ 3 |
| **AI-Powered** | Max/hour | 20 | 60 | × 3 |
| **Standard** | Cooldown | 10 sec | 3 sec | ÷ 3 |
| **Standard** | Max/hour | 30 | 90 | × 3 |

### Impact Analysis

**Expensive Tier (`/report`, `/export`):**
- **Before:** Users could generate 2 reports per hour, waiting 30 min between each
- **After:** Users can generate 6 reports per hour, waiting 10 min between each
- **Impact:** 3x more reports possible, 3x faster iteration
- **Cost impact:** Max cost increases from ~$0.04/hour to ~$0.12/hour per user
- **Risk:** Low (reports are still rate-limited enough to prevent abuse)

**AI-Powered Tier (`/support`, AI queries):**
- **Before:** 20 queries/hour, 2 min cooldown
- **After:** 60 queries/hour, 40 sec cooldown
- **Impact:** Enables more natural conversational flow
- **Cost impact:** Max cost increases from ~$0.02/hour to ~$0.06/hour per user
- **Risk:** Low (60/hour = 1/min average, still reasonable)

**Standard Tier (stats commands):**
- **Before:** 30 queries/hour, 10 sec cooldown
- **After:** 90 queries/hour, 3 sec cooldown
- **Impact:** Nearly eliminates user-facing rate limiting for stats
- **Cost impact:** Negligible (Firestore reads are cheap)
- **Risk:** Very low (3 sec still prevents accidental spam)

### Rationale

**Why triple?**

1. **User feedback:** Original limits were conservative (set during Phase A with limited user data)
2. **Legitimate use cases:** Users checking stats multiple times while reviewing data shouldn't be blocked
3. **Conversational AI:** 2-minute cooldown on `/support` interrupted natural conversation flow
4. **Cost is manageable:** Even at 3x usage, costs remain low:
   - Expensive tier: $0.12/hour max per user
   - AI-Powered tier: $0.06/hour max per user
   - Standard tier: negligible

**Why not remove limits entirely?**

- ✅ **Abuse protection:** Still need protection against malicious bots or accidental infinite loops
- ✅ **Cost control:** Even tripled limits keep costs predictable
- ✅ **Service stability:** Prevents one user from overwhelming shared resources

### Files Modified

1. **`src/utils/rate_limiter.py`**
   - Updated `TIERS` dictionary with new values
   - Added comment noting limits were tripled
   - Updated docstring with new tier values

2. **`RATE_LIMITS_SUMMARY.md`**
   - Updated all tables and examples
   - Added "Last Updated" timestamp
   - Updated example flows with new timing

### Testing Required

Before deployment, verify:

- [ ] Rate limiter still enforces limits (not accidentally disabled)
- [ ] Admin bypass still works
- [ ] User-facing denial messages show correct wait times
- [ ] Metrics tracking still works (`rate_limit_hits` counter)

**Test commands:**

```bash
# Test expensive tier (should allow 6 in an hour, 10 min cooldown)
/report
# Wait 10+ minutes
/report
# Should succeed

# Test AI-powered tier (should allow 60 in an hour, 40 sec cooldown)
/support
# Wait 40+ seconds
/support
# Should succeed

# Test standard tier (should allow 90 in an hour, 3 sec cooldown)
/stats
# Wait 3+ seconds
/stats
# Should succeed
```

### Rollback Plan

If issues arise, revert to original limits:

```python
TIERS = {
    "expensive": {
        "cooldown_seconds": 1800,  # 30 minutes
        "max_per_hour": 2,
    },
    "ai_powered": {
        "cooldown_seconds": 120,  # 2 minutes
        "max_per_hour": 20,
    },
    "standard": {
        "cooldown_seconds": 10,  # 10 seconds
        "max_per_hour": 30,
    },
}
```

### Monitoring

After deployment, monitor:

1. **Rate limit hit rate:** Should decrease (users hitting limits less often)
2. **API costs:** Should increase proportionally (but remain manageable)
3. **User feedback:** Should improve (less friction)
4. **Abuse patterns:** Watch for any malicious usage

**Metrics to track:**
- `rate_limit_hits` counter (should decrease)
- `ai_requests_total` counter (may increase)
- `ai_tokens_used` counter (may increase)
- Daily cost reports (should remain under budget)

### Expected Outcomes

**Positive:**
- ✅ Better user experience (less friction)
- ✅ More natural AI conversations (shorter cooldowns)
- ✅ Faster iteration on reports/exports
- ✅ Reduced user frustration

**Potential Negatives:**
- ⚠️ Slightly higher API costs (manageable)
- ⚠️ Slightly higher server load (negligible)

**Net effect:** Significant UX improvement with minimal cost increase.

---

## Historical Limits

### Original Limits (Phase A - Feb 2026)

| Tier | Cooldown | Max/Hour |
|------|----------|----------|
| Expensive | 30 min | 2 |
| AI-Powered | 2 min | 20 |
| Standard | 10 sec | 30 |

**Context:** These were conservative initial limits set during Phase A implementation when user behavior was unknown.

---

*Change implemented: February 9, 2026*  
*Approved by: User request*  
*Status: Ready for deployment*
