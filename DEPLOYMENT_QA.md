# Pre-Deployment Manual QA Checklist

**Complete this checklist BEFORE deploying to production.**

**Tester:** _______________  
**Date:** _______________  
**Branch/Commit:** _______________  
**Staging Revision:** _______________

---

## Environment Setup

- [ ] Deployed to staging Cloud Run service (`accountability-agent-staging`)
- [ ] Using test Telegram bot (not production bot)
- [ ] Firestore database is staging/test instance
- [ ] Feature flags are in default state

---

## Onboarding Flow

- [ ] `/start` → Welcome message displays correctly
- [ ] Mode selection inline buttons work
- [ ] Timezone confirmation works
- [ ] Profile created successfully in Firestore
- [ ] `/start` as returning user shows stats correctly

---

## Check-In Flow (CRITICAL)

### Full Check-In
- [ ] `/checkin` → Q1 Tier 1 questions display
- [ ] Q1 inline buttons (Y/N) work
- [ ] Q1 numeric inputs (sleep hours, etc.) accepted
- [ ] Q2 Challenges text input accepted
- [ ] Q3 Rating (1-10) inline buttons work
- [ ] Q4 Tomorrow priority + obstacle accepted
- [ ] **Q5 Mood & Energy inline buttons work** ← HOTFIX VERIFICATION
- [ ] Check-in completes successfully
- [ ] Feedback message displays (not "Saving..." forever)
- [ ] Compliance score calculated correctly
- [ ] Streak updates correctly

### Quick Check-In
- [ ] `/quickcheckin` → Tier 1 inline buttons work
- [ ] Quick check-in completes in <30 seconds
- [ ] Abbreviated feedback displays
- [ ] Quick check-in counter increments

---

## New v2.0 Commands

- [ ] `/briefing` → Morning briefing generates
- [ ] `/settings` → Settings menu displays
- [ ] `/constitution` → Live stats overlay displays (no HTML parse error)
- [ ] `/goals` → Active goals listed
- [ ] `/goal_new sleep 7 14` → Goal created
- [ ] `/goal_progress` → Progress shown
- [ ] `/goal_complete` → Completion works
- [ ] `/challenges` → Challenges listed
- [ ] `/feedback` → NPS inline buttons (0-10) work
- [ ] `/feedback` → HTML renders correctly (no raw `<b>` tags)
- [ ] `/delete_my_data` → Confirmation displayed
- [ ] `/delete_my_data` → Cancellation works
- [ ] `/insights` → Insights generated

---

## Edge Cases

- [ ] Type `/constitution` → No "unsupported start tag" error
- [ ] Type `/goals` → No "Did you mean /goals?" double message
- [ ] Type `/insights` → No "Did you mean /insights?" double message
- [ ] Type any `/command` → Fuzzy matching only fires for actual typos
- [ ] Tap mood rating (1-10) → Check-in completes (not hangs)

---

## Partner Features (if applicable)

- [ ] `/set_partner @username` → Request sent
- [ ] Partner receives notification
- [ ] `/partner_status` → Status displayed
- [ ] Partner check-in notification works

---

## Admin & Cron

- [ ] `/admin_status` → Metrics displayed (admin only)
- [ ] Verify cron endpoints reject unauthenticated requests

---

## Sign-Off

**QA Result:** ☐ PASS  ☐ FAIL

**Issues Found:**
_______________________________________________
_______________________________________________
_______________________________________________

**Approved for production deploy by:** _______________  
**Date/Time:** _______________

---

**DO NOT DEPLOY TO PRODUCTION WITHOUT THIS SIGN-OFF.**
