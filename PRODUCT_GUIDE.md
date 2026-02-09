# Constitution Agent — Your AI Accountability Partner

### The only accountability system that actually understands why you failed yesterday and knows exactly how to make sure you don't fail tomorrow.

---

## The Problem

You've tried habit trackers. You've tried accountability apps. You've tried telling your friends "hold me accountable." None of it worked. Here's why:

**Habit trackers don't care.** They show you a green square or a red square. They don't know that you skipped the gym because you slept 4 hours because you were doom-scrolling at 2 AM because you had a fight with someone. They see isolated events. Life is a chain reaction.

**Accountability partners forget.** Your friend said they'd check on you. They did — for three days. Then they got busy with their own life. And you were relieved, because now nobody was watching.

**Willpower is a lie.** You don't need more motivation. You need a system that runs whether you feel like it or not. One that notices when you're slipping *before* you hit rock bottom, and intervenes with the right message at the right time.

**That's what Constitution Agent is.**

It's not a habit tracker. It's not a chatbot. It's an AI-powered operating system for your life — built on YOUR rules, enforced by an agent that never sleeps, never forgets, and never lets you off the hook.

---

## What Is a "Life Constitution"?

Before we talk about the agent, let's talk about what powers it.

A Life Constitution is a written document — your personal set of non-negotiable rules for how you live. Think of it as the kernel of your operating system. Everything else — your habits, your decisions, your relationships — runs on top of it.

The Constitution Agent takes this document and turns it into an enforceable system. Every day, it checks whether you're living by your own rules. If you're not, it tells you. If you're slipping into old patterns, it catches you. If you're struggling, it supports you.

**You write the rules. The agent enforces them.**

---

## How It Works — The Daily Loop

Every day follows the same rhythm. Simple, consistent, non-negotiable.

### 9:00 PM — The Reminder

Your phone buzzes. Not an annoying generic notification — a personalized message that knows your streak, your mode, and your name.

> **Daily Check-In Time!**
>
> Hey Ayush! It's 9 PM — time for your daily check-in.
>
> Current streak: 23 days
> Mode: Optimization
>
> Ready to keep the momentum going?
>
> Use /checkin to start!

Didn't respond? You'll get a nudge at 9:30. Still nothing? An urgent reminder at 10:00 PM that tells you exactly how many days of work you're about to throw away.

The reminder system respects your timezone. Whether you're in Mumbai, New York, or Tokyo, you get reminded at 9 PM *your time*.

### The Check-In — 2 Minutes That Change Everything

You type `/checkin`. The agent walks you through 6 non-negotiable questions:

**1. Sleep** — Did you get 7+ hours? If yes, how many?

**2. Training** — Did you work out today, or was it a scheduled rest day?

**3. Deep Work** — Did you complete 2+ hours of focused, distraction-free work?

**4. Skill Building** — Did you spend 2+ hours on career growth? (This adapts to your career stage — LeetCode if you're learning, applications if you're job hunting, certifications if you're employed.)

**5. Zero Porn** — Did you maintain complete abstinence?

**6. Boundaries** — Did you maintain healthy boundaries in relationships?

Each question is answered with a single tap — inline buttons right in Telegram. Yes or No. No friction. No typing. Just honest answers.

After the Tier 1 questions, you answer 4 reflection questions:
- What challenges did you face today?
- Rate your day 1-10 and explain why.
- What's your #1 priority tomorrow?
- What could get in the way?

The whole thing takes 2 minutes. And those 2 minutes are the most honest conversation you'll have all day.

### The Feedback — AI That Actually Knows You

Here's where Constitution Agent separates from everything else. After you check in, you don't get a generic "Good job!" or "Try harder!" You get feedback from an AI that has read your constitution, analyzed your last 7 days of data, and knows exactly what to say.

> **Check-In Complete!**
>
> Compliance: 83%
> Streak: 24 days
>
> Solid day, Ayush. Sleep at 7.5 hours puts you back in the green zone after two nights of 6-hour sleep. Your constitution's Principle 1 — Physical Sovereignty — is about protecting this exact foundation. The deep work block is strong at 3 hours, but I notice training has been skipped twice this week. Your body is your primary asset — consider whether the evening time block needs restructuring to protect the gym slot.
>
> Tomorrow's priority: System design study. The obstacle you identified — "social media rabbit hole" — maps to Principle 2: Create Don't Consume. Try the 2-minute rule: before opening any platform, ask "What am I avoiding?"

This isn't templated. This isn't a chatbot pretending to understand you. This is Gemini 2.5 Flash analyzing your actual data against your actual constitution and generating feedback that references specific principles you wrote yourself.

### Short on Time? Quick Check-In

Some days are chaos. You can use `/quickcheckin` to answer just the 6 Tier 1 questions — skip the reflection questions entirely. You get 2 quick check-ins per week. Enough for emergencies, not enough to become a crutch.

---

## The Features

### 1. Pattern Detection — Your Early Warning System

This is the feature that makes Constitution Agent fundamentally different from any habit tracker.

Every 6 hours, the agent scans your check-in history looking for dangerous patterns:

| Pattern | What It Detects | Why It Matters |
|---------|----------------|----------------|
| **Sleep Degradation** | 3+ nights below 7 hours | Sleep loss compounds. By night 3, your willpower is shot and every other habit collapses. |
| **Training Abandonment** | 3+ consecutive skipped workouts | Missing one day is rest. Missing three is a spiral. |
| **Compliance Decline** | 15%+ drop in your score over a week | You're not failing suddenly — you're eroding slowly, and that's harder to notice. |
| **Consumption Vortex** | Porn relapses detected | The agent catches the pattern before it becomes a streak-ending crisis. |

When a pattern is detected, you don't get a sterile "Warning: sleep below threshold." You get a message calibrated to the severity of the situation — from a gentle nudge to an urgent intervention — and every single one ends with a bridge to emotional support:

> **Sleep Alert**
>
> I've noticed your sleep has dropped below 7 hours for 3 nights running (6.5h, 5h, 6h). Your constitution's Principle 1 is clear: sleep is non-negotiable. Here's what typically happens next: deep work quality drops → you compensate with consumption → the cycle accelerates.
>
> Let's break the pattern now. What's keeping you up? Is it screens, stress, or schedule?
>
> ---
> Struggling with this? Type /support to talk it through. I can help you figure out what's driving this pattern.

The pattern detection runs silently in the background. You never have to think about it. It just watches, and when it sees trouble brewing, it steps in.

**Under the hood:** The detection engine runs as a Cloud Scheduler job, hitting a secured API endpoint every 6 hours. It loads each user's recent check-ins, applies pattern-matching rules with severity assessment, generates interventions using Gemini (with template fallbacks for reliability), and delivers them via Telegram. Every intervention is logged to Firestore for context-aware follow-up.

---

### 2. Emotional Support — When Accountability Meets Compassion

Most accountability systems are all stick, no carrot. They punish failure without understanding the human behind it.

Constitution Agent has a full emotional support system built in. Type `/support` anytime, and you enter a conversation with an AI trained in Cognitive Behavioral Therapy (CBT) principles:

> **/support** I'm feeling really stressed about work and I skipped the gym again
>
> **Constitution Agent:** Stress is a signal, not a weakness. The fact that you're naming it means you're already ahead of most people who just suppress and spiral.
>
> Let's break this down:
> - **What specifically** is causing the work stress? Is it deadline-driven or relationship-driven?
> - **The gym skip** — was it a conscious choice ("I need rest") or an avoidance pattern ("I just couldn't")?
>
> Your constitution says: "Evidence over emotion, systems over willpower." The gym isn't about motivation today — it's about the system. Can you do even 20 minutes? Sometimes the hardest part is just showing up.
>
> **Right now, try this:**
> 1. Write down the ONE work thing causing the most stress
> 2. Ask: "Is this actionable today, or am I ruminating?"
> 3. If actionable: do 15 minutes on it, then reassess
> 4. If ruminating: put on shoes, walk to gym, do minimum viable workout

The support system is context-aware. If you received an intervention earlier that day about sleep degradation, and then type `/support`, the agent already knows the context:

> I noticed you recently received an alert about your sleep pattern. Want to talk about what's going on?

This bridges the gap that exists in every other system: detection without support is just surveillance. Detection *with* support is coaching.

**Under the hood:** The emotional agent uses a 4-step CBT framework — validate, reframe, identify triggers, provide actions. It receives enriched context including recent interventions and user history. Support sessions are logged for continuity.

---

### 3. Streak System — Momentum, Not Punishment

Your streak is the number of consecutive days you've completed a check-in. It's simple, but the psychology behind how Constitution Agent handles it is not.

**Building momentum:**
- Day 1-6: "Keep going!"
- Day 7: "Week Warrior" achievement unlocked
- Day 14: "Fortnight Fighter"
- Day 30: "Month Master" — "You're in the top 15%!"
- Day 90: "Quarter Champion"
- Day 180: "Half Year Hero"
- Day 365: "Year Legend"

Each milestone comes with a celebration, a percentile ranking ("Top 10% of all users!"), and a dopamine hit that reinforces the behavior.

**The reset problem — solved:**

This is where most streak systems fail catastrophically. You miss one day. Your 47-day streak becomes 0. You feel devastated. You give up for a week.

Constitution Agent handles this completely differently:

> **Fresh Start!**
>
> Your previous streak: 47 days. That's still YOUR record — and you earned every day of it.
>
> Did you know? 83% of people who reach 90+ days had at least one reset along the way. The streak isn't about perfection — it's about how fast you come back.
>
> New streak: Day 1 — the comeback starts now.
>
> Next milestone: 3 days — unlocks Comeback Kid!

Instead of making a reset feel like failure, the agent reframes it as the start of a comeback story. And it backs this up with a whole recovery system:

- **Day 3 after reset:** "3 Days Strong! You're proving the reset was just a bump, not a stop."
- **Day 7 after reset:** "Comeback King! A full week back. Your resilience is your superpower."
- **Exceed your old streak:** "NEW RECORD! You've surpassed your previous 47-day streak! Current: 48 days. Unstoppable."

There are even dedicated achievements for comebacks — Comeback Kid (3 days), Comeback King (7 days), Comeback Legend (exceed your previous best). The system *rewards* resilience, not just consistency.

**Streak Shields:**

Life happens. You get 3 streak shields per month. If you absolutely cannot check in one night, use a shield — your streak is protected. It's an escape valve that prevents the "I missed one day so the streak is ruined" spiral. But you only get 3 per month, so you use them wisely.

**Under the hood:** Streak calculations use atomic Firestore transactions to prevent race conditions. The recovery system stores `streak_before_reset` and `last_reset_date` in the user profile, enabling milestone tracking relative to the reset point. Shields reset on the 1st of each month via scheduled job.

---

### 4. Achievement System — Gamification That Means Something

15 achievements across 3 categories, each tied to real behavioral milestones:

**Streak Achievements** — Rewarding consistency

| Achievement | Icon | Unlock | Rarity |
|-------------|------|--------|--------|
| First Step | 🌱 | 1 day | Common |
| Week Warrior | 💪 | 7 days | Common |
| Fortnight Fighter | ⚡ | 14 days | Rare |
| Month Master | 🏆 | 30 days | Rare |
| Quarter Champion | 👑 | 90 days | Epic |
| Half Year Hero | 🌟 | 180 days | Epic |
| Year Legend | 💎 | 365 days | Legendary |

**Performance Achievements** — Rewarding excellence

| Achievement | Icon | Unlock | Rarity |
|-------------|------|--------|--------|
| Perfect Week | ⭐ | 7 days at 100% compliance | Rare |
| Perfect Month | 🏅 | 30 days at 100% compliance | Epic |
| Tier 1 Master | 🎖️ | All 6 habits complete for 14 straight days | Rare |
| Zero Breaks Month | 🔒 | 30 days with no porn relapses | Rare |

**Comeback Achievements** — Rewarding resilience

| Achievement | Icon | Unlock | Rarity |
|-------------|------|--------|--------|
| Comeback Kid | 🐣 | 3-day streak after a reset | Uncommon |
| Comeback King | 🦁 | 7-day streak after a reset | Rare |
| Comeback Legend | 👑 | Exceed your previous streak after a reset | Epic |

Plus **Shield Master** (🛡️) for using all 3 streak shields successfully.

Each achievement comes with a rarity tag and a celebration message that makes you feel like you actually accomplished something — because you did.

---

### 5. Accountability Partners — Social Pressure That Works

Habits are easier to maintain when someone else is watching. Constitution Agent has a full accountability partner system:

**Linking up:**
```
You: /set_partner @yourfriend
Bot: Partnership request sent to @yourfriend!
Friend gets: [Accept] [Decline] buttons
```

**Mutual visibility:**

Use `/partner_status` to see how your partner is doing:

> **Partner Dashboard: @yourfriend**
>
> Streak: 31 days
> This Week: 5/7 check-ins (85% compliance avg)
> Today: Checked in at 9:15 PM
>
> ---
> You: 24 days | Them: 31 days
> They're 7 days ahead — time to close the gap!

The dashboard is privacy-preserving — you see aggregate data (streak, compliance percentage, check-in status), not their individual answers. You know *how* they're doing without knowing the details of what they shared.

**Ghosting detection:**

If your partner goes silent for 3+ days, you get alerted:

> Your partner @yourfriend hasn't checked in for 3 days. Their streak was 31 days. Maybe reach out and check on them?

This creates gentle social pressure in both directions — you don't want to ghost because your partner will know, and you don't want your partner to ghost because you care.

---

### 6. Natural Language Intelligence — Just Talk to It

You don't have to memorize commands. Just type naturally:

> "How's my sleep been this week?"
>
> "What's my compliance trend?"
>
> "How many days have I trained?"
>
> "I'm feeling stressed about tomorrow"

The agent uses a Supervisor-Specialist architecture to understand what you're asking:

1. **Supervisor Agent** classifies your intent (is this a data query? emotional support? a check-in request?)
2. Routes to the right **Specialist Agent** (Query Agent for data questions, Emotional Agent for feelings, etc.)
3. The specialist fetches your data, analyzes it, and responds in natural language

No menus. No button navigation. Just say what you need.

**Under the hood:** Intent classification uses a two-layer system — fast keyword matching for common patterns (avoiding an LLM call), falling back to Gemini classification for ambiguous messages. The Query Agent supports 7 query types (compliance, streak, training, sleep, patterns, goals, and general), each with dedicated data-fetching logic.

---

### 7. Reports & Visualization — See Your Progress

Every Sunday at 9 AM, you receive an automated weekly report with:

**Four custom-generated graphs:**

1. **Sleep Trend** — Line chart with color zones (green for 7+, yellow for 6-7, red for under 6)
2. **Training Frequency** — Bar chart showing workout vs. rest vs. skip days
3. **Compliance Score** — Your daily scores with a trend line showing direction
4. **Domain Radar** — A 5-axis radar chart covering Physical, Career, Mental, Discipline, and Consistency

Plus AI-generated insights that analyze your week and give specific recommendations.

**On-demand reports:**

Type `/report` anytime for a full performance report with all 4 graphs and AI analysis.

**Data export:**

Type `/export csv`, `/export json`, or `/export pdf` to download your complete check-in history. The CSV is Excel-compatible. The JSON includes full metadata. The PDF is a formatted report with summary stats, Tier 1 performance breakdown, and monthly trends.

**Under the hood:** Graphs are generated server-side using matplotlib with a consistent color palette and styling. The PDF uses ReportLab. All generated files are sent as Telegram documents. Report generation is rate-limited (30-minute cooldown) because it's computationally expensive.

---

### 8. Career Mode Adaptation — Not One-Size-Fits-All

Your life isn't static. Neither is the agent. The Skill Building question adapts based on your career stage:

| Mode | The Question | Activity Options |
|------|-------------|-----------------|
| **Skill Building** | "Did you do 2+ hours of skill building?" | LeetCode, System Design, Side Projects, Online Courses |
| **Job Searching** | "Did you make job search progress today?" | Applications, Networking, Interview Prep, Portfolio |
| **Employed** | "Did you work toward a promotion/raise?" | Side Projects, Certifications, Leadership, Mentoring |

Switch modes anytime with `/career`. The agent tracks your progress within each mode and adjusts its feedback accordingly.

---

### 9. Constitution Modes — Adapt to Life's Phases

Life has seasons. Sometimes you're pushing for peak performance. Sometimes you're just surviving. The agent respects this:

| Mode | When to Use | Expectations |
|------|-------------|-------------|
| **Optimization** | You're healthy, stable, and hungry | All 6 Tier 1 items expected daily. Maximum output. |
| **Maintenance** | Normal life, steady state | 5/6 acceptable. Flexibility on deep work hours. |
| **Survival** | Injury, crisis, major life event | 3/6 minimum. Focus on sleep and core discipline. |

The agent adjusts its feedback tone and expectations based on your current mode. In Survival mode, it doesn't guilt you about missing a workout — it celebrates that you slept 7 hours during a crisis.

---

### 10. Multi-Timezone Support — Works Wherever You Are

The agent supports 60+ timezones across every continent. During onboarding (or anytime via `/timezone`), you pick your timezone with a clean 2-level picker:

**Level 1:** Choose your region
```
[Americas] [Europe] [Asia] [Oceania] [Africa]
```

**Level 2:** Choose your city
```
[New York] [Chicago] [Denver] [Los Angeles] [Anchorage] [Honolulu]
```

All reminders, date calculations, streak logic, and check-in cutoffs respect your local timezone. A check-in at 1 AM counts for the previous day (3 AM cutoff rule). A user in Tokyo and a user in London both get their reminders at 9 PM local time.

**Under the hood:** The reminder system uses a bucket-based architecture. A Cloud Scheduler job runs every 15 minutes. It calculates which IANA timezones are currently at 9:00 PM, 9:30 PM, or 10:00 PM, fetches users in those timezones from Firestore, and sends the appropriate reminder tier. This means adding a new timezone is zero-effort — it's automatically included in the next scan.

---

### 11. Leaderboard & Social Proof — Healthy Competition

Rankings based on a composite score of compliance and streak:

```
/leaderboard

🏆 Leaderboard (Last 7 Days)

1. 🥇 Ayush — 92% (24-day streak)
2. 🥈 Sarah — 88% (15-day streak)
3. 🥉 Raj — 85% (31-day streak)
4.    Mike — 80% (7-day streak)
5.    Priya — 78% (12-day streak)

Your rank: #1 — Top 20%!
```

Leaderboard participation is opt-in. If you don't want to be ranked, toggle it off — your data stays private.

**Referral system:**

Every user gets a unique invite link. Share it with friends:

```
/invite

🔗 Invite a Friend

Share this link:
https://t.me/ConstitutionAgentBot?start=ref_AYUSH123

Your referrals: 3 users invited, 2 active

The more friends using the system, the better the accountability network works!
```

**Shareable stats:**

Generate an Instagram-story-sized image of your stats with a QR code:

```
/share
```

The bot sends you a beautiful image with your streak, compliance, top achievements, and a QR code that links to the bot. Perfect for posting on social media when you hit a milestone.

---

### 12. Check-In Correction — Because Mistakes Happen

Tapped "No" on sleep when you meant "Yes"? No need to stress.

```
/correct
```

Shows today's check-in with toggle buttons for each Tier 1 item. Tap to flip any answer. The compliance score recalculates automatically. The correction is timestamped so you know it was modified.

---

### 13. Rate Limiting — Thoughtful Usage

The agent has a 3-tier rate limiting system that prevents abuse while keeping the experience smooth:

| Tier | Cooldown | Examples |
|------|----------|---------|
| **Expensive** | 30 min | Reports, exports (generate graphs, PDFs) |
| **AI-Powered** | 2 min | Emotional support, natural language queries |
| **Standard** | 10 sec | Stats, leaderboard, achievements |
| **Free** | Unlimited | Help, mode changes, check-ins |

If you hit a limit, you get a friendly message with a countdown and a contextual tip:

> Please wait 1m 30s before using this again.
> Tip: Emotional support works best when you take time to reflect between sessions.

---

## The Tech (For Nerds)

If you've read this far and you're wondering "how does this actually work?" — here's the satisfying answer.

### Architecture

```
Telegram → Webhook → Cloud Run (FastAPI) → Agent Layer → Service Layer → Firestore
                                              ↕
                                        Gemini 2.5 Flash (Vertex AI)
```

- **Cloud Run** — Serverless, scale-to-zero. You only pay when the bot is processing a message. No idle servers. ~$1-3/month for a single user.
- **FastAPI** — Async Python web framework. Sub-200ms webhook processing for most commands.
- **Firestore** — NoSQL document database. Schema-less, so adding new fields is trivial. Atomic transactions for streak updates.
- **Gemini 2.5 Flash** — Google's latest efficient LLM. Thinking mode disabled for cost optimization. ~$0.001 per feedback generation.
- **python-telegram-bot v21** — Official Telegram SDK. ConversationHandler manages multi-step check-in flow as a state machine.

### Agent Architecture

The AI layer uses a **Supervisor + Specialist** pattern inspired by multi-agent systems:

```
                    ┌─────────────┐
User Message ──────>│  Supervisor  │
                    │    Agent     │
                    └──────┬──────┘
                           │ Intent Classification
              ┌────────────┼────────────┐────────────┐
              ▼            ▼            ▼            ▼
         ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌─────────┐
         │ CheckIn │ │  Query  │ │Emotional│ │ Pattern │
         │  Agent  │ │  Agent  │ │  Agent  │ │Detection│
         └─────────┘ └─────────┘ └─────────┘ └─────────┘
```

The Supervisor uses a two-layer classification: fast keyword matching first (no LLM call needed for obvious intents like "what's my streak?"), falling back to Gemini for ambiguous messages. This keeps costs near zero for common interactions.

### Data Flow — Atomic Check-In

The check-in completion is the most critical operation. It uses a Firestore transaction to atomically:

1. Store the check-in document
2. Update the user's streak
3. Update total check-in count
4. Update longest streak if applicable

If any step fails, the entire operation rolls back. No partial state. No corrupted streaks.

### Cost Optimization

Running an AI-powered agent for under $5/month:

- **Gemini 2.5 Flash** with thinking disabled: ~$0.001 per call
- **Cloud Run scale-to-zero:** No idle costs
- **Firestore free tier:** 50K reads/20K writes per day (more than enough)
- **Rate limiting:** Prevents runaway AI costs from spam
- **Fast keyword detection:** Avoids LLM calls for 60%+ of messages

### Monitoring

- In-memory metrics tracking (counters, latencies, error rates)
- JSON structured logging for Cloud Logging integration
- `/admin_status` command shows real-time system health
- Health check endpoint for Cloud Run liveness probes

### Testing

833 unit and integration tests covering:
- All agent behaviors
- Firestore operations
- Streak calculations (including edge cases)
- Achievement unlocking logic
- Rate limiter behavior
- Timezone calculations
- Pattern detection rules
- Conversation state transitions

---

## A Day in the Life

Here's what using Constitution Agent actually looks like over time:

### Week 1 — The Honeymoon

You check in every night. The streak builds. You unlock First Step (Day 1), then Week Warrior (Day 7). You feel good. The AI feedback references your constitution and you think "huh, I actually wrote that." The commitment feels real.

### Week 2 — The First Test

Day 10, you almost skip. You're tired. The 9 PM reminder pings. You ignore it. 9:30, the nudge comes. 10 PM — "URGENT: Your 10-day streak is at risk." You do the check-in. It takes 2 minutes. You're glad you did.

### Week 3 — The Pattern

You've been sleeping under 7 hours for 3 nights. You didn't notice. The agent did. At 3 PM, you get a message:

> I've noticed a sleep pattern forming. Your constitution says sleep is non-negotiable. Here's what's typically happening...

You adjust. The pattern breaks. You never would have caught it on your own.

### Month 1 — The Milestone

Day 30. Month Master unlocked. "You're in the top 15% of all users!" Your weekly report shows a compliance uptrend. The radar chart shows Physical and Discipline are strong, Career needs work. You switch to job searching mode.

### Month 2 — The Reset

Day 47. Life happens. You miss two days. Your streak resets to 0. But instead of devastation:

> Fresh Start! Your previous streak: 47 days. 83% of people who reach 90+ days had at least one reset. The comeback starts now.

Day 50 (3 days after reset): Comeback Kid unlocked. Day 54 (7 days): Comeback King unlocked. Day 95 (exceed old streak): "NEW RECORD! You've surpassed 47 days! Comeback Legend unlocked!" The reset wasn't the end. It was a chapter.

### Month 3+ — The System

You stop thinking about it. The check-in is automatic — like brushing your teeth. The agent fades into the background, quietly watching, only surfacing when you need it. Your sleep average is up. Your training consistency is at 90%+. Your deep work hours have doubled.

The constitution isn't a document you read once. It's a living system that runs every single day.

---

## Command Reference

| Command | What It Does |
|---------|-------------|
| `/start` | Begin onboarding |
| `/checkin` | Full daily check-in (~2 min) |
| `/quickcheckin` | Quick check-in — Tier 1 only (~30 sec, 2/week) |
| `/status` | View current streak, compliance, mode |
| `/help` | See all commands |
| `/mode` | View or change constitution mode |
| `/correct` | Fix mistakes in today's check-in |
| `/support` | Talk to the emotional support agent |
| `/weekly` | Last 7 days summary |
| `/monthly` | Last 30 days summary |
| `/yearly` | Year-to-date summary |
| `/report` | Full AI-generated report with graphs |
| `/export csv/json/pdf` | Download your data |
| `/achievements` | View unlocked achievements |
| `/leaderboard` | See rankings |
| `/set_partner @user` | Link with accountability partner |
| `/partner_status` | View partner's dashboard |
| `/timezone` | Change your timezone |
| `/career` | Change career mode |
| `/use_shield` | Protect your streak for one day |
| `/invite` | Generate referral link |
| `/share` | Generate shareable stats image |

Plus: just type naturally. "What's my compliance this month?" "I'm feeling stressed." "Show my sleep trend." The agent understands.

---

## Who Is This For?

**The self-improver** who has tried everything and needs a system that actually sticks.

**The comeback story** who has failed before and needs a system that celebrates resilience, not just perfection.

**The data nerd** who wants graphs, trends, and analytics on their own behavior.

**The tech enthusiast** who appreciates that this runs on serverless infrastructure, multi-agent AI, and costs under $5/month.

**The accountability seeker** who wants a partner system that works even when human partners forget.

**Anyone** who has a set of principles they believe in but struggles to live by them consistently.

---

## The Philosophy Behind the Design

Every design decision in Constitution Agent traces back to behavioral psychology:

**1. Reduce friction to zero.** Check-in is inline buttons. 2 minutes. No app to open. No separate platform. It lives in Telegram — a messenger you already use every day.

**2. Make streaks recoverable.** The #1 killer of habit systems is the "what the hell" effect — one slip becomes "I already ruined it, so why bother?" The recovery system turns resets into comeback stories.

**3. Detect patterns, not isolated failures.** One bad night is noise. Three bad nights is a pattern. The agent focuses on trends, not individual data points.

**4. Bridge detection and support.** Noticing a problem without offering help is just surveillance. Every intervention leads to emotional support.

**5. Gamify resilience, not just consistency.** Most systems reward perfection. This one rewards bouncing back. Comeback achievements are deliberately rarer and more prestigious than streak achievements.

**6. Respect autonomy.** The constitution is YOURS. The agent enforces YOUR rules, not someone else's idea of what you should do. Mode switching lets you adapt to life's phases without abandoning the system.

**7. Social pressure without toxicity.** Partner visibility is aggregate, not granular. Leaderboards are opt-in. Competition is motivating, not shaming.

---

## What's Next

Constitution Agent is a living system. Upcoming capabilities on the roadmap:

- **Voice Note Check-Ins** — Speak your check-in instead of typing
- **Multi-Language Support** — Hindi, Spanish, and more
- **Weekly Reflection Prompts** — Guided Sunday reviews
- **Habit Stacking Suggestions** — AI-powered habit optimization
- **Advanced Monitoring** — Proactive error alerting and uptime monitoring
- **Constitution Versioning** — Track how your rules evolve over time

---

## Try It

The Constitution Agent is live on Telegram. Write your constitution, configure your non-negotiables, and let the agent do what humans can't: hold you accountable, every single day, without ever forgetting, getting tired, or letting you off the hook.

**Start the bot:** Search for `@ConstitutionAgentBot` on Telegram and type `/start`.

**Write your constitution.** Define your non-negotiable rules.

**Check in tonight at 9 PM.** And tomorrow. And the day after.

Because the only accountability system that works is the one you actually use. And this one makes it impossible not to.

---

*Built with FastAPI, Gemini 2.5 Flash, Google Cloud Run, and Firestore. 35 source files, 833 tests, and one relentless commitment to making you live by your own rules.*
