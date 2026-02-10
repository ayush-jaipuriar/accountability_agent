# Agent HTML Formatting Fix Log

**Date:** 2026-02-10  
**Issue:** Telegram responses showed literal HTML tags (e.g. `<b>...</b>`) instead of formatted text.

## Root Cause

Some bot response paths constructed HTML-formatted messages but sent them without `parse_mode='HTML'`.  
Telegram only renders `<b>`, `<i>`, and related tags when parse mode is explicitly set.

## What Was Fixed

Updated bot messaging paths to consistently set `parse_mode='HTML'` where HTML tags are used:

- `src/bot/telegram_bot.py` (onboarding, timezone, and partner callback flows)
- `src/main.py` partner ghosting alert notification path

### Fixed Areas

- Onboarding mode confirmation message
- Onboarding timezone setup message
- Timezone region/city picker edit messages
- Timezone updated / timezone set confirmations
- Onboarding streak explanation and first-check-in prompt follow-ups
- Partner accept/decline callback confirmation/error messages
- Partner acceptance notification sent to requester
- Partner ghosting alert notification sent from scheduled pattern scan

## Verification Performed

1. **Static scan**: searched all source for direct HTML-tagged Telegram sends without parse mode.
2. **Focused tests** (all passing):
   - `tests/test_telegram_commands.py -k "start or timezone or partner or mode"`
   - Result: **21 passed**
3. **Syntax check**:
   - `python3 -m py_compile src/bot/telegram_bot.py`

## Why This Is Safe

- Changes are scoped only to parse mode metadata on responses already using HTML tags.
- Message logic/content remains unchanged.
- New-user onboarding and partner workflows are covered by passing tests.

## Next Steps

- Reload Telegram client and re-run onboarding (`/start`) to confirm bold formatting renders correctly.
- If any remaining literal tags appear, capture the exact command/flow and message text to patch that specific path quickly.
