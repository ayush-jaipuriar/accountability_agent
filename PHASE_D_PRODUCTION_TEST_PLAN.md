# Phase D Production Testing Plan

**Deployment:** February 8, 2026, 21:45 IST  
**Service URL:** https://accountability-agent-450357249483.asia-south1.run.app  
**Status:** Live in production

---

## Testing Strategy

Test both features in production with real Telegram interactions. Each test includes:
- **Setup:** What state is needed
- **Action:** What to do in Telegram
- **Expected:** What should happen
- **Verification:** How to confirm it worked

---

## Feature 3: Streak Recovery System Tests

### Test 1: Streak Reset Message (Fresh Start)

**Setup:**
- User with active streak (e.g., 10+ days)
- Don't check in for 3 days

**Action:**
```
/checkin
[Complete check-in flow]
```

**Expected:**
```
🎉 Check-In Complete!

📊 Compliance: [score]%

🔄 Fresh Start!

Your previous streak: 10 days 🏆
That's still YOUR record — and you earned every day of it.

🔥 New streak: Day 1 — the comeback starts now.

💡 [Random recovery fact]

🎯 Next milestone: 7 days → unlocks Comeback King! 🦁

[AI feedback]
---
🎯 See you tomorrow at 9 PM!
```

**Verification:**
- [ ] "Fresh Start" heading appears
- [ ] Previous streak referenced (correct number)
- [ ] Recovery fact shown (one of 8 possible)
- [ ] Comeback King mentioned as next milestone
- [ ] No bare "Streak: 1 days" shown

---

### Test 2: Recovery Milestone — Day 3

**Setup:**
- User had a reset 2 days ago
- Checking in for the 3rd consecutive day post-reset

**Action:**
```
/checkin
[Complete check-in]
```

**Expected:**
After the main check-in feedback, a **separate message**:
```
💪 3 Days Strong!

You're proving the reset was just a bump, not a stop.
Keep this energy going! 🔥
```

**Verification:**
- [ ] Separate message sent after check-in feedback
- [ ] "3 Days Strong" heading
- [ ] Motivational text about proving resilience

---

### Test 3: Recovery Milestone — Day 7 (Comeback King)

**Setup:**
- User had a reset 6 days ago
- Checking in for the 7th consecutive day post-reset

**Action:**
```
/checkin
[Complete check-in]
```

**Expected:**
1. Recovery milestone message:
```
🦁 Comeback King!

A full week back after reset.
Your resilience is your superpower. 💪
```

2. Achievement unlock message:
```
🎉 ACHIEVEMENT UNLOCKED!

🦁 Comeback King
Reached 7-day streak after a reset

You're in the top 20%! 🌟
```

**Verification:**
- [ ] Recovery milestone message sent
- [ ] Achievement unlock message sent separately
- [ ] Achievement appears in `/achievements`

---

### Test 4: Comeback Kid Achievement (Day 3)

**Setup:**
- User had a reset 2 days ago
- Reaching Day 3 post-reset

**Action:**
```
/checkin
[Complete]
```

**Expected:**
Achievement unlock after check-in:
```
🎉 ACHIEVEMENT UNLOCKED!

🐣 Comeback Kid
Reached 3-day streak after a reset

Nice milestone! Keep going! 🌱
```

**Verification:**
- [ ] Achievement unlocks at Day 3 post-reset
- [ ] Icon is 🐣
- [ ] Rarity is "uncommon"
- [ ] Appears in `/achievements` list

---

### Test 5: Comeback Legend Achievement (Exceed Previous)

**Setup:**
- User had 15-day streak before reset
- Now rebuilt to 16 days

**Action:**
```
/checkin
[Complete Day 16]
```

**Expected:**
1. Recovery milestone:
```
👑 NEW RECORD!

You've surpassed your previous 15-day streak!
Current: 16 days. Unstoppable. 🔥
```

2. Achievement unlock:
```
🎉 ACHIEVEMENT UNLOCKED!

👑 Comeback Legend
Exceeded previous best streak after a reset

Elite territory! Top 5%! 💎
```

**Verification:**
- [ ] "NEW RECORD" milestone fires
- [ ] References old streak (15 days)
- [ ] Achievement unlocks
- [ ] Rarity is "epic"

---

### Test 6: Normal Streak (No Recovery Messages)

**Setup:**
- User with active streak (no recent reset)

**Action:**
```
/checkin
[Complete]
```

**Expected:**
```
🎉 Check-In Complete!

📊 Compliance: [score]%
🔥 Streak: [N] days

[Normal AI feedback]
```

**Verification:**
- [ ] Normal "Streak: N days" shown (not recovery message)
- [ ] No recovery milestones
- [ ] No comeback achievements (unless Day 3/7 post-reset)

---

## Feature 4: Intervention-to-Support Linking Tests

### Test 7: Support Bridge on Intervention (Medium Severity)

**Setup:**
- Trigger a medium-severity pattern (e.g., sleep degradation for 3 days)

**Action:**
Wait for intervention message (sent by pattern detection cron)

**Expected:**
Intervention message ends with:
```
━━━━━━━━━━━━━━━━━━
💬 Struggling with this? Type /support to talk it through.
   I can help you identify what's driving this pattern.
```

**Verification:**
- [ ] Support bridge appears at bottom
- [ ] Uses medium severity tone
- [ ] References `/support` command
- [ ] Offers to help identify pattern

---

### Test 8: Support Bridge on Critical Intervention

**Setup:**
- Trigger a critical pattern (e.g., ghost for 5+ days)

**Action:**
Wait for ghosting intervention

**Expected:**
Intervention ends with:
```
━━━━━━━━━━━━━━━━━━
🆘 I'm here for you. Type /support or just tell me how you're feeling.
```

**Verification:**
- [ ] Critical tone (🆘 emoji)
- [ ] More empathetic language
- [ ] "I'm here for you" phrasing
- [ ] No judgment language

---

### Test 9: `/support` Command (Standalone)

**Setup:**
- User with no recent interventions

**Action:**
```
/support
```

**Expected:**
```
💙 I'm here.

What's going on? You can tell me about:
• What you're struggling with right now
• What triggered a slip or pattern
• How you're feeling emotionally
• Anything on your mind

Just type naturally — I'll listen and help you work through it.
```

**Verification:**
- [ ] Welcome prompt appears
- [ ] Lists what user can share
- [ ] Inviting, non-judgmental tone
- [ ] No reference to specific patterns

---

### Test 10: `/support` Command (Context-Aware)

**Setup:**
- User received an intervention in last 24h (e.g., sleep degradation)

**Action:**
```
/support
```

**Expected:**
```
💙 I'm here.

I noticed you recently received an alert about sleep degradation.

Want to talk about what's going on? You can tell me about:
• What you're struggling with right now
• What triggered a slip or pattern
• How you're feeling emotionally
• Anything on your mind

Just type naturally — I'll listen and help you work through it.
```

**Verification:**
- [ ] References the specific intervention pattern
- [ ] "I noticed you recently received..." phrasing
- [ ] Pattern name displayed correctly
- [ ] Still shows full prompt

---

### Test 11: `/support` with Inline Message

**Action:**
```
/support I'm feeling really stressed about work
```

**Expected:**
Immediate emotional support response (no prompt):
```
[CBT-style response]
Stress is your body's response to demands. It's a signal, not weakness.

Your constitution handles stress through systems, not emotion...

What specifically is causing this stress? Is it actionable?

Here's what you need to do RIGHT NOW:
1. Brain dump: Write down every stressor
2. Identify ONE action for next 15 minutes
3. Execute that action, then reassess

[Personalized context: streak, mode, etc.]
```

**Verification:**
- [ ] No welcome prompt (direct response)
- [ ] CBT 4-step structure (validate, reframe, trigger, action)
- [ ] References user's streak/context
- [ ] Actionable steps provided

---

### Test 12: Support Mode Follow-Up

**Setup:**
- User typed `/support` (no args)
- Bot showed welcome prompt

**Action:**
```
[Type any message, e.g.:]
I'm struggling with staying consistent
```

**Expected:**
Routes to emotional agent without re-classifying:
```
[Emotional support response]
```

**Verification:**
- [ ] No supervisor classification (direct routing)
- [ ] Emotional agent processes the message
- [ ] Context from intervention (if any) included

---

### Test 13: Rate Limiting on `/support`

**Action:**
```
/support test 1
[Wait 30 seconds]
/support test 2
[Immediately:]
/support test 3
```

**Expected:**
Third `/support` within 2 minutes should be rate-limited:
```
⏳ Please wait 1m 30s before using this again.

💡 Tip: Emotional support works best when you take time to reflect between sessions.
```

**Verification:**
- [ ] Rate limit triggers (ai_powered tier: 2min cooldown)
- [ ] Countdown shown
- [ ] Helpful tip provided

---

### Test 14: `/help` Command Updated

**Action:**
```
/help
```

**Expected:**
Help text includes:
```
💙 Support & Natural Language:
/support - Talk through something you're struggling with
Just type naturally!
• 'What's my compliance this month?'
• 'I'm feeling stressed'
• 'Show my sleep trend'
```

**Verification:**
- [ ] `/support` command listed
- [ ] Under "Support & Natural Language" section
- [ ] Description clear

---

## Integration Tests (Cross-Phase)

### Test 15: Timezone + Recovery (Phase B + D)

**Setup:**
- User in non-IST timezone (e.g., US/Pacific)
- Has a streak that resets

**Action:**
```
/checkin
[After 3-day gap]
```

**Expected:**
- Reset detected using user's timezone
- Recovery message shows correct previous streak
- All dates calculated in user's local timezone

**Verification:**
- [ ] Reset detection timezone-aware
- [ ] Recovery message correct
- [ ] No IST hardcoding issues

---

### Test 16: Partner + Support (Phase C + D)

**Setup:**
- User has accountability partner
- Receives intervention with partner notification

**Action:**
```
/support
```

**Expected:**
- Context-aware prompt references intervention
- Emotional agent knows about partner context
- Support response may reference partner relationship

**Verification:**
- [ ] Partner context preserved
- [ ] Support feels connected to intervention

---

## Monitoring Checks

### Test 17: Metrics Tracking

**Action:**
```
[Use various commands]
/support test
/checkin
/status
```

Then check metrics:
```
/admin_status
```

**Expected:**
```
📊 System Metrics

⏱️ Uptime: [X]h [Y]m

📈 Counters:
• support_sessions: 1
• checkins_total: 1
• commands_total: 3
...
```

**Verification:**
- [ ] `support_sessions` counter exists
- [ ] Increments on `/support` usage
- [ ] Other metrics still tracking

---

### Test 18: JSON Logging

**Action:**
Check Cloud Run logs after triggering commands

**Expected:**
Logs in JSON format:
```json
{
  "severity": "INFO",
  "message": "✅ Full check-in started for 1034585649",
  "module": "conversation",
  "function": "start_checkin",
  "timestamp": "2026-02-08T16:16:24.006689Z"
}
```

**Verification:**
- [ ] Logs are structured JSON
- [ ] Searchable in Cloud Logging
- [ ] Contains severity, module, function fields

---

## Regression Tests (Ensure Nothing Broke)

### Test 19: Normal Check-In Flow

**Action:**
```
/checkin
[Answer all questions]
```

**Expected:**
- All 6 Tier 1 questions (including Skill Building from Phase 3D)
- AI feedback generation works
- Streak increments correctly
- Compliance calculated correctly

**Verification:**
- [ ] Check-in completes without errors
- [ ] All phases still working

---

### Test 20: Partner Status Dashboard (Phase C)

**Action:**
```
/partner_status
```

**Expected:**
Partner dashboard with aggregate data

**Verification:**
- [ ] Dashboard displays correctly
- [ ] No errors from Phase D changes

---

### Test 21: Timezone Picker (Phase B)

**Action:**
```
/timezone
```

**Expected:**
2-level region/city picker

**Verification:**
- [ ] Picker works
- [ ] Timezone saves correctly

---

## Success Criteria

Phase D deployment is considered successful when:

✅ **Feature 3 (Streak Recovery):**
- [ ] Reset message shows on first check-in after gap
- [ ] Recovery milestones fire at Day 3, 7, 14
- [ ] Comeback achievements unlock correctly
- [ ] No errors in streak calculation

✅ **Feature 4 (Intervention-to-Support):**
- [ ] All interventions have support bridges
- [ ] `/support` command works standalone
- [ ] Context-aware support works after interventions
- [ ] Support mode routing works correctly

✅ **Backward Compatibility:**
- [ ] Existing users with old schema work fine
- [ ] Normal streaks (no reset) unaffected
- [ ] All previous phases still functional

✅ **Performance:**
- [ ] Webhook latency <500ms
- [ ] No timeout errors
- [ ] Rate limiting working
- [ ] Metrics tracking active

---

## Known Issues to Monitor

1. **First Reset in Production**: The first user to experience a streak reset will be the real test. Monitor logs closely.

2. **Recovery Milestone Timing**: Verify milestones fire on the correct days (not off-by-one).

3. **Support Context**: Verify intervention context is passed correctly to emotional agent.

4. **Achievement Unlocking**: Ensure comeback achievements don't unlock for users without resets.

---

## Rollback Triggers

Rollback immediately if:
- ❌ Check-ins start failing (>10% error rate)
- ❌ Streak calculations become incorrect
- ❌ Webhook stops responding
- ❌ Critical errors in logs (>5 per hour)

Otherwise, monitor for 24-48 hours before considering stable.

---

## Post-Testing Actions

After successful testing:
1. Update main plan (`.cursor/plans/...`) to mark Phase D complete
2. Document any issues found
3. Decide on Feature 6 (Advanced Monitoring) or declare P2/P3 complete
4. Celebrate! 🎉
