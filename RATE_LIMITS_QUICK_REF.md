# Rate Limits Quick Reference Card

**Last Updated:** February 9, 2026 (Limits Tripled)

---

## Current Limits

| Tier | Cooldown | Max/Hour | Commands |
|------|----------|----------|----------|
| **Expensive** | 10 min | 6 | `/report`, `/export` |
| **AI-Powered** | 40 sec | 60 | `/support`, AI queries |
| **Standard** | 3 sec | 90 | `/stats`, `/weekly`, `/monthly`, `/yearly`, `/partner_status`, `/leaderboard`, `/achievements`, `/share` |
| **Free** | None | ∞ | `/start`, `/help`, `/mode`, `/cancel`, `/timezone`, `/checkin`, partner commands |

---

## What This Means

### Expensive Commands
- Generate 6 reports per hour (was 2)
- Wait 10 minutes between reports (was 30 min)
- Example: Report at 2:00 PM → next at 2:10 PM

### AI-Powered Commands
- 60 AI interactions per hour (was 20)
- Wait 40 seconds between messages (was 2 min)
- Natural conversation pace

### Standard Commands
- 90 stats queries per hour (was 30)
- Wait 3 seconds between queries (was 10 sec)
- Nearly unlimited for normal use

---

## Admin Bypass

**Admins bypass ALL rate limits.**

Set via environment variable:
```bash
ADMIN_TELEGRAM_IDS=12345,67890
```

---

## Cost Impact (Max)

| Tier | Max Cost/Hour |
|------|---------------|
| Expensive | $0.12 |
| AI-Powered | $0.06 |
| Standard | $0.009 |
| **Total** | **$0.189** |

*Note: These are maximum costs if user hits every limit. Actual costs much lower.*

---

## Testing Commands

```bash
# Run all rate limiter tests
pytest tests/test_phase_a_monitoring_ratelimit.py -v

# Expected: 74/74 passing
```

---

## Rollback (If Needed)

**File:** `src/utils/rate_limiter.py`

Change back to:
```python
"expensive": {"cooldown_seconds": 1800, "max_per_hour": 2}
"ai_powered": {"cooldown_seconds": 120, "max_per_hour": 20}
"standard": {"cooldown_seconds": 10, "max_per_hour": 30}
```

---

## Monitoring

Watch these metrics after deployment:

- `rate_limit_hits` → Should decrease
- `ai_requests_total` → May increase
- Daily costs → Should stay under $10/day

---

*Quick reference for rate limits in accountability agent*  
*Updated: February 9, 2026*
