# Implementation Progress - 2026-03-22

## Summary

Implemented two linked changes:

1. Reduced the repeated post-check-in stress coaching bug by:
   - suppressing one-shot re-routing of the final free-text check-in message through the general message handler
   - adding explicit support gating inside the full check-in completion flow so support guidance only appears when the check-in shows a strong enough signal
   - generating short LLM-based support guidance inline in the main check-in response instead of as a separate repetitive message

2. Added partner check-in notifications by:
   - introducing a mirrored pair-level setting: `partner_checkin_notifications_enabled`
   - sending a privacy-safe daily summary for the first successful full or quick check-in
   - sending a single updated partner notification if the user corrects the check-in later
   - adding `/partner_notifications` as the settings surface for toggling the shared pair setting

## Files Changed

- `src/models/schemas.py`
  - Added `User.partner_checkin_notifications_enabled`
  - Included the field in `User.to_firestore()`

- `src/services/firestore_service.py`
  - Added `get_partner_checkin_notification_status()`
  - Added `mark_partner_checkin_notification_sent()`

- `src/services/partner_notification_service.py`
  - New helper service for:
    - display-name fallback resolution
    - partner notification formatting
    - partner notification delivery and dedupe logic

- `src/agents/checkin_agent.py`
  - Added `should_offer_support_guidance()`
  - Added `generate_support_guidance()`
  - Tightened the main feedback prompt so it avoids drifting into therapy-style output

- `src/bot/conversation.py`
  - Added inline support guidance logic to full check-in completion
  - Added partner notification delivery for full and quick check-ins
  - Added sender-facing failure notice helper for partner notification delivery problems
  - Added one-shot suppression flag before ending the full check-in flow

- `src/bot/telegram_bot.py`
  - Added `/partner_notifications`
  - Added `partner_notifications_callback()`
  - Added shared pair-setting update helpers
  - Reset partner notifications to ON when a new partnership is confirmed
  - Added correction-triggered partner update notifications
  - Suppressed one-shot post-check-in general routing

- `src/utils/ux.py`
  - Added `/partner_notifications` to help text

- `tests/test_partner_notification_service.py`
  - Added coverage for message formatting and initial/update send behavior

- `tests/test_checkin_agent.py`
  - Added support-gating tests

- `tests/test_firestore_service.py`
  - Added partner notification status tests

- `tests/test_telegram_bot_commands.py`
  - Added partner notification command tests
  - Added one-shot post-check-in suppression test

## Why These Changes

- The bug fix needed to address behavior, not just copy. The repeated stress message appeared to come from an unintended post-check-in routing path plus overly broad support generation.
- The partner notification feature needed to fit the existing user/partner model and avoid exposing sensitive fields like porn and boundaries.
- The correction flow needed explicit support so the partner sees the updated metrics, not stale ones.

## Next Validation Steps

1. Run targeted tests for the newly changed areas.
2. Run `pytest tests`.
3. Manually test:
   - full check-in with no strong stress signal
   - full check-in with a strong stress signal
   - quick check-in partner notification
   - `/partner_notifications` toggle flow
   - `/correct` update partner notification
