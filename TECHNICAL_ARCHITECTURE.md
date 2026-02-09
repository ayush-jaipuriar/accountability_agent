# Technical Architecture — Constitution Accountability Agent

**Version:** 2.0 (Post-P2/P3 Implementation)  
**Last Updated:** February 9, 2026  
**Author:** Ayush Jaipuriar  
**Repository:** https://github.com/ayush-jaipuriar/accountability_agent

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [High-Level Architecture](#2-high-level-architecture)
3. [Infrastructure & Deployment](#3-infrastructure--deployment)
4. [Data Model & Schema](#4-data-model--schema)
5. [Application Layer — FastAPI](#5-application-layer--fastapi)
6. [Bot Layer — Telegram Interface](#6-bot-layer--telegram-interface)
7. [Agent Layer — AI Processing](#7-agent-layer--ai-processing)
8. [Service Layer — Business Logic](#8-service-layer--business-logic)
9. [Utility Layer — Shared Functions](#9-utility-layer--shared-functions)
10. [Conversation Flow — Check-In System](#10-conversation-flow--check-in-system)
11. [Pattern Detection & Intervention Pipeline](#11-pattern-detection--intervention-pipeline)
12. [Gamification & Achievement System](#12-gamification--achievement-system)
13. [Social Features](#13-social-features)
14. [Scheduled Jobs & Cron System](#14-scheduled-jobs--cron-system)
15. [Monitoring, Metrics & Rate Limiting](#15-monitoring-metrics--rate-limiting)
16. [Security Architecture](#16-security-architecture)
17. [End-to-End Data Flows](#17-end-to-end-data-flows)
18. [Feature Matrix](#18-feature-matrix)
19. [Technology Stack](#19-technology-stack)
20. [File Structure](#20-file-structure)

---

## 1. System Overview

### What It Is

The Constitution Accountability Agent is an AI-powered Telegram bot that enforces a personal "Life Constitution" — a set of daily non-negotiable habits. It combines structured check-ins, AI feedback, pattern detection, emotional support, gamification, and social accountability into a single system.

### Core Philosophy

The system is built around 6 Tier 1 Non-Negotiables derived from the user's personal constitution:

| # | Non-Negotiable | Metric |
|---|----------------|--------|
| 1 | **Sleep** | 7+ hours per night |
| 2 | **Training** | Daily workout (or scheduled rest day) |
| 3 | **Deep Work** | 2+ hours of focused, distraction-free work |
| 4 | **Skill Building** | 2+ hours career-focused learning (adapts to career mode) |
| 5 | **Zero Porn** | Complete abstinence maintained |
| 6 | **Boundaries** | No toxic interactions tolerated |

### Key Capabilities

- **Daily Check-In System** — Structured 6-question Tier 1 assessment + open-ended reflection
- **AI-Powered Feedback** — Personalized feedback using Gemini 2.5 Flash referencing constitution principles
- **Pattern Detection** — Automated identification of negative trends (sleep degradation, training abandonment, etc.)
- **Intervention System** — Proactive alerts when patterns are detected, with severity-graded support bridges
- **Emotional Support** — CBT-style emotional processing via `/support` command
- **Natural Language Queries** — Ask questions like "What's my sleep trend?" and get AI-generated answers
- **Gamification** — 15 achievements, XP system, streak milestones, comeback mechanics
- **Social Accountability** — Partner system, leaderboard, referrals, shareable stats
- **Multi-Timezone Support** — Full IANA timezone support with bucket-based reminder scheduling
- **Reporting & Visualization** — Weekly reports with 4 graph types, PDF/CSV/JSON export
- **Rate Limiting** — 3-tier rate limiting to prevent abuse of expensive AI commands
- **Monitoring** — In-memory metrics, JSON structured logging, admin dashboard

---

## 2. High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                         TELEGRAM CLIENT                            │
│                    (User's Phone/Desktop)                           │
└──────────────────────────┬──────────────────────────────────────────┘
                           │ HTTPS (Webhook)
                           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      GOOGLE CLOUD RUN                              │
│                   (Serverless Container)                            │
│                                                                     │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │                    FastAPI Application                         │  │
│  │                     (src/main.py)                              │  │
│  │                                                                │  │
│  │  ┌─────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐  │  │
│  │  │ Webhook │  │  Health   │  │  Cron    │  │   Admin      │  │  │
│  │  │Endpoint │  │  Check   │  │Endpoints │  │  Metrics     │  │  │
│  │  └────┬────┘  └──────────┘  └────┬─────┘  └──────────────┘  │  │
│  │       │                          │                            │  │
│  │       ▼                          ▼                            │  │
│  │  ┌──────────────────────────────────────────────────────┐    │  │
│  │  │              BOT LAYER (src/bot/)                     │    │  │
│  │  │                                                       │    │  │
│  │  │  TelegramBotManager  │  ConversationHandler  │ Stats │    │  │
│  │  └──────────┬───────────┴──────────┬────────────┴───────┘    │  │
│  │             │                      │                          │  │
│  │             ▼                      ▼                          │  │
│  │  ┌──────────────────────────────────────────────────────┐    │  │
│  │  │             AGENT LAYER (src/agents/)                 │    │  │
│  │  │                                                       │    │  │
│  │  │  Supervisor → CheckIn │ Emotional │ Query │ Pattern  │    │  │
│  │  │               Agent   │  Agent    │ Agent │Detection │    │  │
│  │  └──────────────────────┬────────────────────────────────┘    │  │
│  │                         │                                     │  │
│  │                         ▼                                     │  │
│  │  ┌──────────────────────────────────────────────────────┐    │  │
│  │  │           SERVICE LAYER (src/services/)               │    │  │
│  │  │                                                       │    │  │
│  │  │  Firestore │Achievement│ Social │Analytics│ LLM      │    │  │
│  │  │  Service   │ Service   │Service │Service  │Service    │    │  │
│  │  │            │           │        │         │           │    │  │
│  │  │  Visualization │ Export │ Constitution │ Reporting   │    │  │
│  │  └────────┬───────────────┴────────────┬─────────────────┘    │  │
│  │           │                            │                      │  │
│  └───────────┼────────────────────────────┼──────────────────────┘  │
│              │                            │                         │
└──────────────┼────────────────────────────┼─────────────────────────┘
               │                            │
               ▼                            ▼
┌──────────────────────┐    ┌──────────────────────────────┐
│   GOOGLE FIRESTORE   │    │   GOOGLE GEMINI 2.5 FLASH    │
│  (NoSQL Database)    │    │   (via Vertex AI SDK)         │
│                      │    │                               │
│  Collections:        │    │  Used for:                    │
│  • users/            │    │  • Intent classification      │
│  • daily_checkins/   │    │  • Check-in feedback          │
│  • interventions/    │    │  • Natural language queries    │
│  • reminder_status/  │    │  • Emotional support          │
│  • emotional_logs/   │    │  • Weekly report insights     │
│  • partial_states/   │    │  • Pattern severity analysis  │
└──────────────────────┘    └──────────────────────────────┘
               │
               │  Triggered by
               ▼
┌──────────────────────────┐
│  GOOGLE CLOUD SCHEDULER  │
│                          │
│  Jobs:                   │
│  • Pattern scan (6h)     │
│  • Reminders (15min)     │
│  • Weekly report (Sun)   │
│  • Quick reset (Mon)     │
└──────────────────────────┘
```

### Architectural Principles

1. **Webhook-Based** — Telegram sends updates to Cloud Run via HTTPS webhook (not polling)
2. **Serverless** — Scale-to-zero on Cloud Run; only pay when processing requests
3. **Singleton Services** — All services use singleton pattern to avoid re-initialization
4. **Layered Architecture** — Bot → Agent → Service → Database (strict dependency direction)
5. **Feature Flags** — Individual features can be toggled via environment variables
6. **Backward Compatible** — All schema changes use Pydantic defaults for safe migration

---

## 3. Infrastructure & Deployment

### Google Cloud Platform

| Service | Purpose | Configuration |
|---------|---------|--------------|
| **Cloud Run** | Hosts the containerized FastAPI application | asia-south1, 512Mi RAM, 1 vCPU, scale 0-10 |
| **Firestore** | NoSQL document database (Native mode) | asia-south1, automatic indexes |
| **Cloud Scheduler** | Triggers cron endpoints on schedule | asia-south1, HTTP POST with secret header |
| **Artifact Registry** | Stores Docker container images | Auto-managed by Cloud Run source deploy |

### Container

```dockerfile
FROM python:3.11-slim
# System deps: curl, fontconfig, fonts-dejavu-core, libfreetype6, libjpeg62-turbo, zlib1g
# Python deps: requirements.txt (20 packages)
# Entry: uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers 1
```

**Key details:**
- Python 3.11 slim base image (lightweight)
- System libraries for matplotlib rendering (fonts, image processing)
- Single uvicorn worker (Cloud Run handles scaling via instances)
- `PORT` set by Cloud Run (8080)

### Environment Variables

| Variable | Required | Default | Purpose |
|----------|----------|---------|---------|
| `TELEGRAM_BOT_TOKEN` | Yes | — | Bot authentication |
| `TELEGRAM_CHAT_ID` | Yes | — | Default admin chat |
| `GCP_PROJECT_ID` | No | `accountability-agent` | GCP project |
| `GCP_REGION` | No | `asia-south1` | GCP region |
| `WEBHOOK_URL` | No | `""` | Cloud Run service URL |
| `GEMINI_MODEL` | No | `gemini-2.5-flash` | LLM model name |
| `GEMINI_API_KEY` | No | `None` | Direct Gemini API key |
| `VERTEX_AI_LOCATION` | No | `asia-south1` | Vertex AI region |
| `ENVIRONMENT` | No | `development` | dev/staging/production |
| `LOG_LEVEL` | No | `INFO` | Logging verbosity |
| `TIMEZONE` | No | `Asia/Kolkata` | Default timezone |
| `CHECKIN_TIME` | No | `21:00` | Default reminder time |
| `ENABLE_PATTERN_DETECTION` | No | `true` | Feature flag |
| `ENABLE_EMOTIONAL_PROCESSING` | No | `false` | Feature flag |
| `ENABLE_GHOSTING_DETECTION` | No | `false` | Feature flag |
| `ENABLE_REPORTS` | No | `false` | Feature flag |
| `JSON_LOGGING` | No | `false` | Structured logging |
| `CRON_SECRET` | No | `""` | Cron endpoint auth |
| `ADMIN_TELEGRAM_IDS` | No | `""` | Admin user IDs |

### Deployment Flow

```
Local Development → Git Push → gcloud run deploy --source . → Cloud Build → Artifact Registry → Cloud Run
```

1. Code pushed to GitHub
2. `gcloud run deploy` uploads source
3. Cloud Build builds Docker image
4. Image stored in Artifact Registry
5. Cloud Run creates new revision
6. Traffic routed to new revision (zero-downtime)
7. On startup, app registers webhook with Telegram API

---

## 4. Data Model & Schema

### Firestore Collections

```
firestore/
├── users/{user_id}                    # User profiles
│   ├── user_id: string               # Primary key (Telegram ID as string)
│   ├── telegram_id: int              # Telegram user ID
│   ├── telegram_username: string?    # @username
│   ├── name: string                  # Display name
│   ├── timezone: string              # IANA timezone (e.g., "America/New_York")
│   ├── constitution_mode: string     # "optimization" | "maintenance" | "survival"
│   ├── career_mode: string           # "skill_building" | "job_searching" | "employed"
│   ├── streaks: {                    # Nested object
│   │   ├── current_streak: int
│   │   ├── longest_streak: int
│   │   ├── last_checkin_date: string?
│   │   ├── total_checkins: int
│   │   ├── streak_before_reset: int  # Phase D
│   │   └── last_reset_date: string?  # Phase D
│   │ }
│   ├── streak_shields: {             # Nested object
│   │   ├── total: int (3)
│   │   ├── used: int
│   │   ├── available: int
│   │   ├── earned_at: [string]
│   │   └── last_reset: string?
│   │ }
│   ├── reminder_times: {first, second, third}
│   ├── accountability_partner_id: string?
│   ├── accountability_partner_name: string?
│   ├── achievements: [string]        # List of achievement IDs
│   ├── level: int
│   ├── xp: int
│   ├── leaderboard_opt_in: bool
│   ├── referral_code: string?
│   ├── referred_by: string?
│   ├── created_at: timestamp
│   └── updated_at: timestamp
│
├── daily_checkins/{user_id}/checkins/{date}  # Check-in records
│   ├── date: string                          # YYYY-MM-DD
│   ├── user_id: string
│   ├── mode: string
│   ├── tier1_non_negotiables: {
│   │   ├── sleep: bool
│   │   ├── sleep_hours: float?
│   │   ├── training: bool
│   │   ├── is_rest_day: bool
│   │   ├── training_type: string?
│   │   ├── deep_work: bool
│   │   ├── deep_work_hours: float?
│   │   ├── skill_building: bool       # Phase 3D
│   │   ├── skill_building_hours: float?
│   │   ├── skill_building_activity: string?
│   │   ├── zero_porn: bool
│   │   └── boundaries: bool
│   │ }
│   ├── responses: {
│   │   ├── challenges: string (10-500 chars)
│   │   ├── rating: int (1-10)
│   │   ├── rating_reason: string
│   │   ├── tomorrow_priority: string
│   │   └── tomorrow_obstacle: string
│   │ }
│   ├── compliance_score: float (0-100)
│   ├── is_quick_checkin: bool
│   ├── corrected_at: timestamp?
│   ├── duration_seconds: int
│   └── completed_at: timestamp
│
├── interventions/{user_id}/logs/{auto_id}  # Intervention history
│   ├── pattern_type: string
│   ├── severity: string
│   ├── message: string
│   ├── data: map
│   └── timestamp: timestamp
│
├── reminder_status/{user_id}_{date}        # Reminder tracking
│   ├── user_id: string
│   ├── date: string
│   ├── first_sent: bool
│   ├── second_sent: bool
│   ├── third_sent: bool
│   └── *_sent_at: timestamp?
│
├── emotional_interactions/{user_id}/logs/{auto_id}  # Support logs
│   ├── emotion_type: string
│   ├── user_message: string
│   ├── bot_response: string
│   └── timestamp: timestamp
│
└── partial_states/{user_id}               # Conversation recovery
    ├── conversation_type: string
    ├── state_data: map
    ├── saved_at: timestamp
    └── expires_at: timestamp
```

### Pydantic Models (Python ↔ Firestore)

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `User` | User profile | 25+ fields, nested `UserStreaks` + `StreakShields` + `ReminderTimes` |
| `DailyCheckIn` | Check-in record | `tier1_non_negotiables`, `responses`, `compliance_score` |
| `UserStreaks` | Streak tracking | `current_streak`, `longest_streak`, `streak_before_reset` |
| `StreakShields` | Streak protection | `total`, `used`, `available`, monthly reset |
| `Tier1NonNegotiables` | 6 habit completion | `sleep`, `training`, `deep_work`, `skill_building`, `zero_porn`, `boundaries` |
| `CheckInResponses` | Free-text responses | `challenges`, `rating`, `tomorrow_priority`, `tomorrow_obstacle` |
| `ReminderTimes` | Configurable reminders | `first`, `second`, `third` (HH:MM) |
| `ReminderStatus` | Reminder dedup | Tracks which of 3 reminders were sent today |
| `Achievement` | Achievement definition | `achievement_id`, `name`, `icon`, `criteria`, `rarity` |
| `Pattern` | Detected pattern | `pattern_name`, `severity`, `data_points`, `message` |

---

## 5. Application Layer — FastAPI

### Route Map

```
GET  /                          → Service info & available endpoints
GET  /health                    → Health check (Firestore test + metrics summary)
GET  /admin/metrics             → Full metrics (admin auth required)

POST /webhook/telegram          → Telegram webhook receiver
POST /trigger/pattern-scan      → Pattern detection scan (cron-protected)
POST /cron/reminder_first       → 9:00 PM reminder (cron-protected)
POST /cron/reminder_second      → 9:30 PM reminder (cron-protected)
POST /cron/reminder_third       → 10:00 PM reminder (cron-protected)
POST /cron/reminder_tz_aware    → Timezone-aware reminders (cron-protected, every 15min)
POST /cron/reset_quick_checkins → Weekly quick check-in reset (cron-protected, Monday)
POST /trigger/weekly-report     → Weekly report generation (cron-protected, Sunday)
```

### Lifecycle

```python
@app.on_event("startup")
async def startup():
    1. Initialize TelegramBotManager
    2. Register ConversationHandler (check-in flow)
    3. Initialize Telegram Application
    4. Test Firestore connection
    5. Set webhook URL (production only)
    6. Log startup metrics

@app.on_event("shutdown")
async def shutdown():
    1. Shut down Telegram application gracefully
```

### Webhook Processing

```
Telegram → POST /webhook/telegram
  → Record start time
  → Parse Update object
  → Process through bot application (handlers)
  → Record latency metric
  → Return {"ok": true}
```

---

## 6. Bot Layer — Telegram Interface

### TelegramBotManager

The `TelegramBotManager` class orchestrates all Telegram interactions. It registers command handlers, callback query handlers, and the conversation handler.

### Command Reference

#### Core Commands
| Command | Handler | Description | Rate Tier |
|---------|---------|-------------|-----------|
| `/start` | `start_command` | Onboarding (new) or welcome back (returning) | free |
| `/help` | `help_command` | Show all available commands | free |
| `/status` | `status_command` | Current streak, compliance, performance | standard |
| `/mode [mode]` | `mode_command` | View/change constitution mode | free |
| `/checkin` | ConversationHandler | Full daily check-in (6 Tier 1 + 4 open-ended) | free |
| `/quickcheckin` | ConversationHandler | Quick check-in (6 Tier 1 only, 2/week limit) | free |
| `/correct` | `correct_command` | Fix mistakes in today's check-in | standard |
| `/cancel` | `cancel_checkin` | Cancel active check-in | free |

#### Analytics & Reports
| Command | Handler | Description | Rate Tier |
|---------|---------|-------------|-----------|
| `/weekly` | `weekly_command` | Last 7 days summary | standard |
| `/monthly` | `monthly_command` | Last 30 days summary | standard |
| `/yearly` | `yearly_command` | Year-to-date summary | standard |
| `/report` | `report_command` | AI-generated weekly report with graphs | expensive |
| `/export [format]` | `export_command` | Export data as CSV/JSON/PDF | expensive |

#### Social & Gamification
| Command | Handler | Description | Rate Tier |
|---------|---------|-------------|-----------|
| `/achievements` | `achievements_command` | View unlocked achievements | standard |
| `/leaderboard` | `leaderboard_command` | View rankings | standard |
| `/set_partner @user` | `set_partner_command` | Request accountability partner | standard |
| `/partner_status` | `partner_status_command` | View partner's dashboard | standard |
| `/unlink_partner` | `unlink_partner_command` | Remove partner link | standard |
| `/invite` | `invite_command` | Generate referral link | standard |
| `/share` | `share_command` | Generate shareable stats image | standard |
| `/resume` | `resume_command` | Generate career resume from data | expensive |

#### Support & Settings
| Command | Handler | Description | Rate Tier |
|---------|---------|-------------|-----------|
| `/support [msg]` | `support_command` | Emotional support (context-aware) | ai_powered |
| `/timezone` | `timezone_command` | Change timezone (2-level picker) | free |
| `/career` | `career_command` | View/change career mode | free |
| `/use_shield` | `use_shield_command` | Use streak shield | standard |
| `/admin_status` | `admin_status_command` | System metrics (admin only) | free |

#### Natural Language
Any non-command text message is processed by the **Supervisor Agent** for intent classification:
- `query` → Query Agent (e.g., "What's my sleep trend?")
- `emotional` → Emotional Agent (e.g., "I'm feeling stressed")
- `checkin` → Suggests `/checkin`

### Callback Query Handlers

| Pattern | Handler | Purpose |
|---------|---------|---------|
| `mode_*` | `mode_selection_callback` | Onboarding mode selection |
| `change_mode_*` | `mode_change_callback` | Post-onboarding mode change |
| `tz_*` | `timezone_confirmation_callback` | 2-level timezone picker |
| `career_*` | `career_callback` | Career mode selection |
| `correct_*` | `correct_toggle_callback` | Toggle Tier 1 items in correction |
| `accept_partner:*` | `accept_partner_callback` | Accept partner request |
| `decline_partner:*` | `decline_partner_callback` | Decline partner request |

### Handler Priority

```
Group 0 (highest): ConversationHandler → Catches /checkin, /quickcheckin, and button presses during check-in
Group 1 (lower):   General Message Handler → Catches all non-command text for AI processing
```

---

## 7. Agent Layer — AI Processing

### Agent Architecture

The agent layer uses a **Supervisor + Specialist** pattern. The Supervisor classifies user intent and routes to the appropriate specialist agent.

```
User Message
    │
    ▼
┌─────────────┐
│  Supervisor  │──── Intent Classification (Gemini)
│    Agent     │     + Fast keyword detection
└──────┬──────┘
       │
       ├── intent: "query"     → Query Agent
       ├── intent: "emotional" → Emotional Agent
       ├── intent: "checkin"   → Suggest /checkin
       └── intent: "command"   → Route to command handler
```

### State Schema (ConstitutionState)

All agents share a common TypedDict state:

```python
ConstitutionState = TypedDict('ConstitutionState', {
    # User context
    'user_id': str,
    'username': Optional[str],
    # Message
    'message': str,
    'message_id': int,
    'timestamp': str,
    # Intent
    'intent': str,                    # checkin | emotional | query | command
    'intent_confidence': float,
    # Check-in state
    'checkin_step': int,
    'checkin_answers': Dict,
    'compliance_score': float,
    'streak': int,
    # Pattern detection
    'detected_patterns': Annotated[list, operator.add],
    # Response
    'response': str,
    'next_action': str,
    # Error handling
    'error': Optional[str],
})
```

### Supervisor Agent

**Purpose:** Classifies user intent and routes to appropriate specialist.

**Fast Path:** Keyword detection for common queries (avoids LLM call):
- "compliance", "average", "score" → `query`
- "streak", "how many days" → `query`
- "sleep", "training", "trend" → `query`
- "feel", "stressed", "struggling" → `emotional`

**Slow Path:** If keywords don't match, uses Gemini for classification.

### CheckIn Agent

**Purpose:** Generates personalized AI feedback after check-in completion.

**Input:** Compliance score, Tier 1 results, streak, recent check-ins, constitution principles.

**Process:**
1. Fetch recent 7 check-ins for trend analysis
2. Analyze trend (improving/declining/stable)
3. Get relevant constitution principles
4. Build prompt with all context
5. Generate feedback via Gemini (200 tokens max, thinking disabled)
6. Fallback to template if AI fails

**Output:** 3-5 sentence personalized feedback referencing specific habits and constitution.

### Query Agent

**Purpose:** Answers natural language questions about user data.

**Query Types:**
| Type | Example | Data Fetched |
|------|---------|-------------|
| `compliance_average` | "What's my compliance?" | Recent check-ins, calculate average |
| `streak_info` | "How's my streak?" | Current/longest streak |
| `training_history` | "Training this week?" | Training data from check-ins |
| `sleep_trends` | "My sleep trend?" | Sleep hours over time |
| `pattern_frequency` | "Any patterns?" | Detected patterns |
| `goal_progress` | "How am I doing?" | Overall progress summary |
| `unknown` | Everything else | Generic data fetch |

**Process:**
1. Classify query type (Gemini)
2. Fetch relevant data from Firestore
3. Generate natural language response (Gemini)

### Emotional Agent

**Purpose:** Provides CBT-style emotional support.

**Capabilities:**
- Validates emotions without judgment
- Cognitive reframing
- Identifies triggers
- Provides actionable coping strategies
- Context-aware (references recent interventions if applicable)

### Pattern Detection Agent

**Purpose:** Scans check-in data for concerning patterns.

**Pattern Rules:**
| Pattern | Trigger | Severity |
|---------|---------|----------|
| `sleep_degradation` | 3+ days below 7h sleep | warning → critical |
| `training_abandonment` | 3+ consecutive missed workouts | warning |
| `compliance_decline` | 15%+ drop over 7 days | warning |
| `consumption_vortex` | Porn relapses detected | critical |

### Intervention Agent

**Purpose:** Generates and sends intervention messages when patterns are detected.

**Features:**
- AI-generated interventions (Gemini) with template fallback
- Severity-graded support bridges (low/medium/high/critical)
- Pattern-specific intervention templates
- Ghosting detection alerts (partner accountability)
- All interventions end with `/support` prompt

### Reporting Agent

**Purpose:** Generates weekly performance reports.

**Output:**
1. 4 visualization graphs (sleep, training, compliance, radar)
2. AI-powered insights (trend analysis, recommendations)
3. Formatted Telegram message with stats
4. Sent every Sunday at 9 AM

---

## 8. Service Layer — Business Logic

### Firestore Service (`firestore_service.py`)

Central data access layer. All database operations go through this singleton.

**Operation Categories:**
- **User CRUD** — create, get, update, exists
- **Check-In CRUD** — store, get, update, list recent/all
- **Atomic Operations** — `store_checkin_with_streak_update()` (transactional)
- **Query Operations** — users by timezone, users without checkin, active users
- **Intervention Logging** — store and retrieve interventions
- **Reminder Tracking** — set/get reminder status (prevents duplicate sends)
- **Streak Shields** — use shield, reset shields
- **Quick Check-In** — increment/reset counters
- **Achievements** — unlock achievement
- **Partner Operations** — link/unlink, find by username
- **Emotional Interactions** — store support session logs
- **Health Check** — test Firestore connection

### Achievement Service (`achievement_service.py`)

Manages 15 achievements across 3 categories:

**Streak Achievements (7):**
| ID | Name | Icon | Criteria | Rarity |
|----|------|------|----------|--------|
| `first_step` | First Step | 🌱 | 1-day streak | common |
| `week_warrior` | Week Warrior | 💪 | 7-day streak | common |
| `fortnight_fighter` | Fortnight Fighter | ⚡ | 14-day streak | rare |
| `month_master` | Month Master | 🏆 | 30-day streak | rare |
| `quarter_champion` | Quarter Champion | 👑 | 90-day streak | epic |
| `half_year_hero` | Half Year Hero | 🌟 | 180-day streak | epic |
| `year_legend` | Year Legend | 💎 | 365-day streak | legendary |

**Performance Achievements (5):**
| ID | Name | Icon | Criteria | Rarity |
|----|------|------|----------|--------|
| `perfect_week` | Perfect Week | ⭐ | 7 consecutive 100% days | rare |
| `perfect_month` | Perfect Month | 🏅 | 30 consecutive 100% days | epic |
| `tier1_master` | Tier 1 Master | 🎖️ | All Tier 1 complete 14 days straight | rare |
| `comeback_king` | Comeback King | 🦁 | 7-day streak after reset | rare |
| `zero_breaks_month` | Zero Breaks Month | 🔒 | 30 days no porn breaks | rare |

**Special Achievements (3):**
| ID | Name | Icon | Criteria | Rarity |
|----|------|------|----------|--------|
| `comeback_kid` | Comeback Kid | 🐣 | 3-day streak after reset | uncommon |
| `comeback_legend` | Comeback Legend | 👑 | Exceed previous streak after reset | epic |
| `shield_master` | Shield Master | 🛡️ | Successfully used 3 shields | rare |

### Social Service (`social_service.py`)

- **Leaderboard** — Rankings by compliance + streak score, formatted for Telegram
- **Referral System** — Deep-link generation, referral stats tracking
- **Shareable Stats** — Instagram-sized image with stats and QR code

### Visualization Service (`visualization_service.py`)

Generates 4 chart types using matplotlib:
1. **Sleep Chart** — Line chart with color zones (green >7h, yellow 6-7h, red <6h)
2. **Training Chart** — Bar chart showing workout/rest/skip days
3. **Compliance Chart** — Scores with linear regression trend line
4. **Domain Radar** — 5-axis radar (Physical, Career, Mental, Discipline, Consistency)

### Export Service (`export_service.py`)

Exports user data in 3 formats:
- **CSV** — UTF-8 BOM for Excel compatibility
- **JSON** — Structured with metadata and nested objects
- **PDF** — Formatted report with ReportLab (summary stats, Tier 1 performance, monthly breakdown)

### Analytics Service (`analytics_service.py`)

Calculates period-based statistics:
- **Weekly** — 7-day compliance, Tier 1 breakdown, patterns
- **Monthly** — 4-week breakdown, achievements, percentile
- **Yearly** — Monthly breakdown, career progress, totals

### LLM Service (`llm_service.py` + `llm_service_gemini.py`)

Two LLM backends:
1. **Vertex AI** (primary) — Uses `google-genai` SDK with Vertex AI backend
2. **Direct Gemini API** (fallback) — Uses API key directly

**Configuration:**
- Model: `gemini-2.5-flash`
- Thinking: Disabled (cost optimization)
- Max tokens: 200-500 depending on use case
- Temperature: 0.7 (creative) for feedback, 0.1 (deterministic) for classification

### Constitution Service (`constitution_service.py`)

Manages the user's Life Constitution document:
- Loads `constitution.md` from disk
- Extracts Tier 1 rules, operating modes, historical patterns, crisis protocols
- Provides constitution excerpts to AI agents for context-aware feedback

---

## 9. Utility Layer — Shared Functions

### Compliance (`compliance.py`)

| Function | Purpose |
|----------|---------|
| `calculate_compliance_score()` | Percentage of 6 Tier 1 items completed (0-100%) |
| `calculate_compliance_score_normalized()` | Backward-compatible (5 items pre-Phase 3D, 6 after) |
| `get_compliance_level()` | Categorize: excellent (90+), good (80+), warning (60+), critical (<60) |
| `get_tier1_breakdown()` | Detailed breakdown with hours and activity types |
| `get_missed_items()` | List of incomplete Tier 1 items |

### Streak (`streak.py`)

| Function | Purpose |
|----------|---------|
| `update_streak_data()` | Main function: calculate new streak, detect resets, generate recovery messages |
| `calculate_new_streak()` | New streak value (increment/reset logic) |
| `should_increment_streak()` | Is gap ≤1 day? |
| `check_milestone()` | Check for major milestones (30/60/90/180/365) |
| `format_streak_reset_message()` | Compassionate reset message with recovery fact |
| `get_recovery_milestone_message()` | Recovery milestone at Day 3, 7, 14, or exceed old streak |
| `is_streak_at_risk()` | Has it been >24h since last check-in? |
| `should_reset_streak_shields()` | Monthly shield reset check |
| `days_until_milestone()` | Days to next streak milestone |

### Timezone (`timezone_utils.py`)

| Function | Purpose |
|----------|---------|
| `get_current_time()` | Current datetime in any timezone |
| `get_current_date()` | Current date string in any timezone |
| `get_checkin_date()` | Which date check-in counts for (3 AM cutoff) |
| `utc_to_local()` / `local_to_utc()` | Timezone conversions |
| `get_timezones_at_local_time()` | Find timezones where it's a specific local time |
| `is_valid_timezone()` | Validate IANA timezone string |
| `get_timezone_display_name()` | Human-readable name from catalog |

**Timezone Catalog:** 60+ timezones organized by region (Americas, Europe, Asia, etc.) for the 2-level picker.

### Metrics (`metrics.py`)

| Method | Purpose |
|--------|---------|
| `increment(metric)` | Increment counter (checkins, commands, errors, etc.) |
| `record_latency(metric, ms)` | Record latency sample (rolling buffer of 100) |
| `record_error(category, detail)` | Record error with detail string |
| `get_latency_stats(metric)` | Calculate avg, p50, p95, p99, min, max |
| `get_summary()` | Full metrics snapshot |
| `format_admin_status()` | HTML-formatted admin dashboard |

### Rate Limiter (`rate_limiter.py`)

**3-Tier System:**

| Tier | Cooldown | Hourly Limit | Commands |
|------|----------|-------------|----------|
| `expensive` | 30 min | 2/hour | `/report`, `/export` |
| `ai_powered` | 2 min | 20/hour | `/support`, natural language queries |
| `standard` | 10 sec | 30/hour | `/weekly`, `/monthly`, `/leaderboard`, etc. |
| `free` | None | Unlimited | `/start`, `/help`, `/mode`, `/cancel` |

**Algorithm:** Sliding window with per-user tracking. Admins bypass all limits.

### UX (`ux.py`)

| Component | Purpose |
|-----------|---------|
| `EMOJI` dict | Semantic emoji constants for consistent messaging |
| `format_header()` | Consistent message headers |
| `format_stat_line()` | Formatted stat display |
| `ErrorMessages` | 9 standardized error messages |
| `TimeoutManager` | Conversation timeout handling (15 min) |
| `generate_help_text()` | Dynamic help text generation |
| `format_partner_dashboard()` | Partner status formatting |

---

## 10. Conversation Flow — Check-In System

### Full Check-In (`/checkin`)

```
User: /checkin
  │
  ▼
┌──────────────────────────┐
│ VALIDATION               │
│ • User exists?           │
│ • Already checked in?    │
│ • Initialize timer       │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ STATE: Q1_TIER1          │  ← 6 questions, one at a time
│                          │
│ Q1: Sleep (7+ hours?)    │  [✅ Yes] [❌ No]
│     → If Yes: How many?  │  [7] [7.5] [8] [8+]
│ Q2: Training?            │  [💪 Trained] [😴 Rest Day] [⏭ Skipped]
│ Q3: Deep Work (2+ hrs?)  │  [✅ Yes] [❌ No]
│     → If Yes: How many?  │  [2] [3] [4+]
│ Q4: Skill Building?      │  [✅ Yes] [❌ No]  (adapts to career_mode)
│     → If Yes: Activity?  │  [LeetCode] [Design] [Projects] [Other]
│ Q5: Zero Porn?           │  [✅ Clean] [❌ Slipped]
│ Q6: Boundaries?          │  [✅ Maintained] [❌ Compromised]
│                          │
│ [↩ Undo Last] available  │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ STATE: Q2_CHALLENGES     │
│                          │
│ "What challenges did     │
│  you face today?"        │
│ (10-500 characters)      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ STATE: Q3_RATING         │
│                          │
│ "Rate your day 1-10      │
│  and explain why"        │
│ (e.g., "7 - Good but     │
│  could've slept more")   │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ STATE: Q4_TOMORROW       │
│                          │
│ "What's your #1 priority │
│  tomorrow and what could │
│  get in the way?"        │
│ (10-500 characters)      │
└──────────┬───────────────┘
           │
           ▼
┌──────────────────────────┐
│ COMPLETION (finish_checkin)       │
│                                    │
│ 1. Create DailyCheckIn object     │
│ 2. Calculate compliance score     │
│ 3. Update streak (atomic txn)     │
│ 4. Store check-in to Firestore    │
│ 5. Generate AI feedback (Gemini)  │
│ 6. Check achievements             │
│ 7. Send celebration if milestone  │
│ 8. Send recovery msg if reset     │
│ 9. Record metrics                 │
└──────────────────────────────────┘
```

### Quick Check-In (`/quickcheckin`)

Same as full check-in but:
- Skips Q2-Q4 (open-ended questions)
- Uses abbreviated AI feedback (1-2 sentences)
- Limited to 2 per week (resets Monday)
- Default responses filled in for skipped questions

### Check-In Correction (`/correct`)

- Allows toggling any Tier 1 item for today's check-in
- Recalculates compliance score
- Records `corrected_at` timestamp
- Preserves open-ended responses

---

## 11. Pattern Detection & Intervention Pipeline

### Detection Flow

```
Cloud Scheduler (every 6 hours)
    │
    ▼
POST /trigger/pattern-scan
    │
    ▼
For each active user:
    │
    ├── Fetch last 7 days of check-ins
    │
    ├── Run Pattern Rules:
    │   ├── Sleep Degradation: 3+ days <7h
    │   ├── Training Abandonment: 3+ missed workouts
    │   ├── Compliance Decline: 15%+ drop
    │   └── Consumption Vortex: Porn relapses
    │
    ├── If patterns found:
    │   ├── Assess severity (nudge/warning/critical)
    │   ├── Generate intervention message (AI or template)
    │   ├── Add support bridge (severity-graded)
    │   ├── Send to user via Telegram
    │   └── Log to Firestore
    │
    └── Record scan metrics
```

### Support Bridge System (Phase D)

Every intervention ends with a severity-appropriate support prompt:

| Severity | Bridge Message |
|----------|---------------|
| `low` | "Need to talk? Type /support anytime. No judgment." |
| `medium` | "Struggling with this? Type /support to talk it through." |
| `high` | "This is hard. Type /support — I can help you work through this." |
| `critical` | "I'm here for you. Type /support or just tell me how you're feeling." |

### Intervention → Support Flow

```
Pattern Detected → Intervention Sent (with support bridge)
    │
    User types /support (within 24h)
    │
    ▼
Context-Aware Support:
    "I noticed you recently received an alert about [pattern]..."
    │
    ▼
Emotional Agent processes with intervention context
    │
    ▼
CBT-style response (validate → reframe → trigger → action)
```

---

## 12. Gamification & Achievement System

### XP & Leveling

- XP earned per check-in (based on compliance score)
- Level thresholds: Level 1 (0 XP), Level 2 (100 XP), etc.

### Achievement Flow

```
Check-in completed
    │
    ▼
AchievementService.check_achievements(user, recent_checkins)
    │
    ├── Check streak achievements (1, 7, 14, 30, 90, 180, 365)
    ├── Check performance achievements (perfect week/month, tier1 master)
    └── Check special achievements (comeback kid/king/legend, shield master)
    │
    ├── For each newly unlocked:
    │   ├── Persist to Firestore (add to user.achievements)
    │   ├── Generate celebration message
    │   └── Send to user
    │
    └── Return list of new achievement IDs
```

### Streak Recovery System (Phase D)

When a streak resets:
1. `streak_before_reset` preserved in user profile
2. "Fresh Start!" message with previous streak acknowledgment
3. Random motivational recovery fact
4. Recovery milestones at Day 3, 7, 14
5. If user exceeds old streak: "NEW RECORD!" celebration
6. Comeback achievements unlock at Day 3, 7, and exceed

### Streak Shields (Phase 3A)

- 3 shields per month
- Protects streak for 1 missed day
- Resets on the 1st of each month
- `/use_shield` command

---

## 13. Social Features

### Accountability Partners

```
User A: /set_partner @userB
    │
    ▼
Bot sends request to User B with [Accept] [Decline] buttons
    │
    ├── Accept → Both users linked (bidirectional)
    └── Decline → Notifies User A
```

**Partner Dashboard (`/partner_status`):**
- Partner's current streak
- Partner's compliance average (7-day)
- Partner's check-in status today
- Motivational comparison footer

**Ghosting Detection:**
- If partner misses 3+ days, notify the other partner
- Alert includes partner's streak and last check-in date

### Leaderboard

- Rankings by composite score: `(compliance_avg * 0.7) + (streak_bonus * 0.3)`
- Opt-in system (`leaderboard_opt_in` field)
- Shows top N users with anonymized names

### Referral System

- Unique deep-link per user
- Tracks referral count and active referrals
- `/invite` generates shareable link

### Shareable Stats

- Instagram story-sized image (1080x1920)
- QR code linking to bot
- Stats overlay (streak, compliance, achievements)

---

## 14. Scheduled Jobs & Cron System

### Cloud Scheduler Jobs

| Job | Schedule | Endpoint | Purpose |
|-----|----------|----------|---------|
| **TZ-Aware Reminders** | Every 15 min | `/cron/reminder_tz_aware` | Send reminders to users at 9 PM, 9:30 PM, 10 PM local time |
| **Pattern Scan** | Every 6 hours | `/trigger/pattern-scan` | Detect negative patterns across all users |
| **Weekly Report** | Sunday 9 AM | `/trigger/weekly-report` | Generate and send weekly performance reports |
| **Quick Reset** | Monday 12 AM | `/cron/reset_quick_checkins` | Reset weekly quick check-in counters |

### Legacy Reminders (IST-only)

| Job | Schedule | Endpoint |
|-----|----------|----------|
| First Reminder | 9:00 PM IST | `/cron/reminder_first` |
| Second Reminder | 9:30 PM IST | `/cron/reminder_second` |
| Third Reminder | 10:00 PM IST | `/cron/reminder_third` |

### Reminder System Architecture (Phase B)

```
Cloud Scheduler → POST /cron/reminder_tz_aware (every 15 min)
    │
    ▼
For each reminder tier (first=21:00, second=21:30, third=22:00):
    │
    ├── get_timezones_at_local_time(utc_now, target_hour, target_minute)
    │   → Returns list of matching IANA timezone IDs
    │
    ├── get_users_by_timezones(matching_tzs)
    │   → Returns users in those timezones
    │
    ├── Filter: already checked in today? reminder already sent?
    │
    └── Send tier-appropriate message:
        • First:  "Daily Check-In Time!" (friendly)
        • Second: "Still There?" (nudge)
        • Third:  "URGENT: Closing Soon!" (with shield info)
```

---

## 15. Monitoring, Metrics & Rate Limiting

### In-Memory Metrics

```python
metrics.increment("checkins_total")
metrics.record_latency("webhook", 150.5)
metrics.record_error("gemini", "429 rate limit")
```

**Tracked Metrics:**
| Metric | Type | Description |
|--------|------|-------------|
| `checkins_total` | counter | Total check-ins completed |
| `commands_total` | counter | Total commands processed |
| `support_sessions` | counter | `/support` command uses |
| `errors_total` | counter | Total errors |
| `webhook` | latency | Webhook processing time (ms) |
| `gemini` | error | LLM API errors |

### Health Check

```json
GET /health
{
  "status": "healthy",
  "service": "constitution-agent",
  "version": "1.0.0",
  "environment": "production",
  "uptime": "12h 34m",
  "checks": { "firestore": "ok" },
  "metrics_summary": {
    "checkins_total": 42,
    "commands_total": 156,
    "errors_total": 3
  }
}
```

### Admin Dashboard

```
/admin_status → HTML-formatted metrics:
• Uptime
• All counters
• Latency percentiles (p50, p95, p99)
• Error breakdown by category
• Rate limiter stats
```

### JSON Structured Logging

When `JSON_LOGGING=true`, all logs are structured for Cloud Logging:

```json
{
  "severity": "INFO",
  "message": "✅ Full check-in started for 1034585649",
  "module": "conversation",
  "function": "start_checkin",
  "timestamp": "2026-02-09T16:16:24Z"
}
```

---

## 16. Security Architecture

### Cron Endpoint Protection

All cron endpoints require `X-Cron-Secret` header matching `settings.cron_secret`:

```python
def verify_cron_request(request: Request):
    secret = request.headers.get("X-Cron-Secret")
    if not settings.cron_secret:
        return  # Dev mode: skip auth
    if secret != settings.cron_secret:
        raise HTTPException(403, "Unauthorized")
```

### Admin Command Protection

Admin commands (`/admin_status`) check `settings.admin_telegram_ids`:

```python
if str(user_id) not in admin_ids:
    await update.message.reply_text("⛔ Admin only.")
    return
```

### Admin Metrics Endpoint

`GET /admin/metrics` requires `admin_id` query parameter.

### Rate Limiting

Per-user sliding window prevents abuse of expensive operations:
- Gemini API calls (AI feedback, intent classification)
- Report generation (graphs + PDF)
- Data export

### Secret Management

- Bot token and API keys stored as Cloud Run env vars
- `.env` file for local development (never committed)
- `.gitignore` blocks `.env`, `.credentials/`, `*.key`, `*.pem`
- Pre-commit checks for secret patterns

### Webhook Security

- HTTPS-only (enforced by Cloud Run)
- Telegram verifies webhook URL ownership
- No API key exposure in webhook URL

---

## 17. End-to-End Data Flows

### Flow 1: Daily Check-In

```
User sends /checkin
    → Telegram Webhook → FastAPI → ConversationHandler
    → 6 Tier 1 questions (inline buttons) → User answers each
    → 4 open-ended questions → User types responses
    → finish_checkin():
        → calculate_compliance_score(tier1) → 83.3%
        → update_streak_data(current=7, last_date="2026-02-08", new_date="2026-02-09")
            → streak increments to 8, checks milestones
        → store_checkin_with_streak_update() [Firestore atomic transaction]
        → CheckInAgent.generate_feedback(compliance, tier1, streak, history)
            → Gemini generates personalized feedback
        → AchievementService.check_achievements(user, checkins)
            → Checks if any new achievements unlocked
        → Send feedback message to Telegram
        → Send milestone/achievement celebrations (separate messages)
        → Record metrics (checkins_total, duration)
```

### Flow 2: Natural Language Query

```
User sends "How did I sleep this week?"
    → Telegram Webhook → FastAPI → General Message Handler
    → Rate limit check (ai_powered tier)
    → SupervisorAgent.classify_intent("How did I sleep this week?")
        → Fast path: keyword "sleep" → intent: "query"
    → QueryAgent.process(state)
        → classify_query("How did I sleep this week?") → "sleep_trends"
        → fetch_query_data("sleep_trends", user_id)
            → Firestore: get_recent_checkins(7 days) → extract sleep_hours
        → generate_response(query, data)
            → Gemini: "This week your sleep averaged 7.2 hours..."
    → Send response to Telegram
```

### Flow 3: Pattern Scan → Intervention → Support

```
Cloud Scheduler → POST /trigger/pattern-scan (every 6 hours)
    → For each active user:
        → Get last 7 check-ins from Firestore
        → Run 4 pattern rules
        → Example: 3 nights <7h sleep → sleep_degradation (warning)
        → generate_intervention(pattern, severity)
            → Gemini generates intervention message
            → add_support_bridge(message, severity="warning")
                → Appends: "Struggling with this? Type /support..."
        → Send to Telegram
        → Log to Firestore (interventions collection)

    ... User sees intervention, types /support ...

    → support_command()
        → Fetch recent interventions (last 24h)
        → Found: sleep_degradation
        → Build context: "I noticed you got an alert about sleep degradation..."
        → Set support_mode = True
    → User types: "Yeah, I've been staying up too late"
        → handle_general_message() → support_mode detected
        → _process_support_message()
            → Enrich with intervention context
            → EmotionalAgent.process(state)
                → CBT response: validate → reframe → triggers → action steps
        → Send emotional support response
```

### Flow 4: Timezone-Aware Reminders

```
Cloud Scheduler → POST /cron/reminder_tz_aware (every 15 min, e.g., 13:30 UTC)
    │
    ├── Tier "first" (target: 21:00 local):
    │   → get_timezones_at_local_time(13:30 UTC, 21, 0)
    │   → Returns: ["Asia/Kolkata"] (IST = UTC+5:30, so 13:30+5:30 = 19:00 ❌ no match)
    │   → No users to remind at this time
    │
    ├── Tier "second" (target: 21:30 local):
    │   → get_timezones_at_local_time(13:30 UTC, 21, 30)
    │   → Returns: ["America/New_York"] (EST = UTC-5, so 13:30-5 = 08:30 ❌ no match)
    │   → No match either
    │
    └── ... continues checking all 3 tiers every 15 min
        until timezone alignment occurs
```

---

## 18. Feature Matrix

### By Implementation Phase

| Phase | Feature | Status |
|-------|---------|--------|
| **Phase 1** | Hardcoded check-in (4 items), Firestore, FastAPI, Cloud Run | ✅ Complete |
| **Phase 2** | LangGraph agents, Gemini feedback, pattern detection, interventions | ✅ Complete |
| **Phase 3A** | Multi-user, 3-tier reminders, streak shields, quick check-in limits | ✅ Complete |
| **Phase 3B** | Emotional support, accountability partners, ghosting detection | ✅ Complete |
| **Phase 3C** | Achievement system (13 achievements), XP, social proof | ✅ Complete |
| **Phase 3D** | Career mode (3 modes), skill building Tier 1, backward compat | ✅ Complete |
| **Phase 3E** | Quick check-in, stats commands (/weekly/monthly/yearly), /correct | ✅ Complete |
| **Phase 3F** | Visualization (4 graphs), PDF/CSV/JSON export, leaderboard, referrals | ✅ Complete |
| **P0/P1** | Bug fixes, cron auth, multi-user isolation, error handling | ✅ Complete |
| **Phase A** | Rate limiting (3-tier), in-memory metrics, JSON logging | ✅ Complete |
| **Phase B** | Full IANA timezone support, 2-level picker, bucket reminders | ✅ Complete |
| **Phase C** | Partner mutual visibility dashboard | ✅ Complete |
| **Phase D** | Streak recovery system, intervention-to-support linking, /support | ✅ Complete |

### By Capability

| Capability | Components |
|------------|-----------|
| **Data Collection** | 6 Tier 1 Y/N + 4 open-ended questions |
| **AI Feedback** | Gemini 2.5 Flash via Vertex AI SDK |
| **Pattern Detection** | 4 rules (sleep, training, compliance, porn) |
| **Interventions** | AI-generated + template fallback + support bridges |
| **Emotional Support** | CBT-style processing via /support command |
| **Natural Language** | Intent classification + query answering |
| **Gamification** | 15 achievements, XP, levels, milestones |
| **Social** | Partners, leaderboard, referrals, sharing |
| **Reporting** | 4 graphs, PDF/CSV/JSON, weekly auto-reports |
| **Reminders** | 3-tier, timezone-aware, duplicate prevention |
| **Monitoring** | Metrics, latency tracking, admin dashboard |
| **Rate Limiting** | 3-tier sliding window |
| **Streak Recovery** | Reset messages, recovery milestones, comeback achievements |

---

## 19. Technology Stack

### Runtime

| Technology | Version | Purpose |
|------------|---------|---------|
| Python | 3.11 | Application runtime |
| FastAPI | 0.109.0 | Web framework (async) |
| Uvicorn | 0.27.0 | ASGI server |
| python-telegram-bot | 21.0 | Telegram Bot API |
| Pydantic | ≥2.10.0 | Data validation |
| pydantic-settings | ≥2.7.0 | Environment config |

### Google Cloud

| Technology | Version | Purpose |
|------------|---------|---------|
| google-genai | ≥1.61.0 | Gemini 2.5 Flash (unified SDK) |
| google-cloud-firestore | 2.14.0 | Database client |
| google-cloud-aiplatform | 1.42.0 | Vertex AI compatibility |
| google-cloud-secret-manager | 2.17.0 | Secret retrieval |

### Data & Visualization

| Technology | Version | Purpose |
|------------|---------|---------|
| matplotlib | ≥3.8.0 | Graph generation |
| Pillow | ≥10.0.0 | Image processing |
| ReportLab | ≥4.0 | PDF generation |
| qrcode | ≥7.4 | QR code generation |

### Utilities

| Technology | Version | Purpose |
|------------|---------|---------|
| pytz | 2024.1 | Timezone handling |
| httpx | ≥0.28.1 | HTTP client (for google-genai) |
| python-dotenv | 1.0.0 | Local .env loading |

### Testing

| Technology | Version | Purpose |
|------------|---------|---------|
| pytest | 8.0.0 | Test framework |
| pytest-asyncio | 0.23.0 | Async test support |
| pytest-cov | 4.1.0 | Coverage reports |

### Infrastructure

| Technology | Purpose |
|------------|---------|
| Docker | Container packaging |
| Google Cloud Run | Serverless hosting |
| Google Cloud Scheduler | Cron job triggering |
| Google Firestore | NoSQL database |
| Google Artifact Registry | Container image storage |

---

## 20. File Structure

```
accountability_agent/
│
├── src/                              # Application source code
│   ├── __init__.py
│   ├── main.py                       # FastAPI app, routes, lifecycle, cron endpoints
│   ├── config.py                     # Pydantic settings, env validation
│   │
│   ├── agents/                       # AI agent layer
│   │   ├── __init__.py
│   │   ├── supervisor.py             # Intent classification & routing
│   │   ├── checkin_agent.py          # AI feedback generation
│   │   ├── emotional_agent.py        # CBT-style emotional support
│   │   ├── intervention.py           # Intervention message generation
│   │   ├── pattern_detection.py      # Pattern detection rules
│   │   ├── query_agent.py            # Natural language query answering
│   │   ├── reporting_agent.py        # Weekly report generation
│   │   └── state.py                  # ConstitutionState TypedDict
│   │
│   ├── bot/                          # Telegram interface layer
│   │   ├── __init__.py
│   │   ├── telegram_bot.py           # TelegramBotManager, all commands
│   │   ├── conversation.py           # Check-in conversation flow (state machine)
│   │   └── stats_commands.py         # /weekly, /monthly, /yearly
│   │
│   ├── models/                       # Data models
│   │   ├── __init__.py
│   │   └── schemas.py                # 10 Pydantic models + helper functions
│   │
│   ├── services/                     # Business logic & external integrations
│   │   ├── __init__.py
│   │   ├── firestore_service.py      # All Firestore CRUD operations
│   │   ├── achievement_service.py    # 15 achievements, celebration messages
│   │   ├── social_service.py         # Leaderboard, referrals, shareable stats
│   │   ├── visualization_service.py  # 4 matplotlib chart generators
│   │   ├── export_service.py         # CSV, JSON, PDF export
│   │   ├── analytics_service.py      # Weekly/monthly/yearly stats
│   │   ├── llm_service.py            # Gemini via Vertex AI SDK
│   │   ├── llm_service_gemini.py     # Gemini via direct API (fallback)
│   │   └── constitution_service.py   # Constitution document management
│   │
│   └── utils/                        # Shared utilities
│       ├── __init__.py
│       ├── compliance.py             # Compliance score calculation
│       ├── streak.py                 # Streak logic, recovery system
│       ├── timezone_utils.py         # Full IANA timezone support
│       ├── metrics.py                # In-memory metrics tracking
│       ├── rate_limiter.py           # 3-tier rate limiting
│       └── ux.py                     # Message formatting, error messages
│
├── tests/                            # Test suite (833 tests)
│   ├── conftest.py                   # Shared fixtures
│   ├── test_achievements.py
│   ├── test_agents_integration.py
│   ├── test_analytics_service.py
│   ├── test_checkin_agent.py
│   ├── test_compliance.py
│   ├── test_conversation_flow.py
│   ├── test_e2e_flows.py
│   ├── test_export_service.py
│   ├── test_fastapi_endpoints.py
│   ├── test_firestore_service.py
│   ├── test_gamification_integration.py
│   ├── test_intent_classification.py
│   ├── test_p0_p1_fixes.py
│   ├── test_phase_a_monitoring_ratelimit.py
│   ├── test_phase_b_timezone.py
│   ├── test_phase_c_partner.py
│   ├── test_phase_d_recovery_support.py
│   ├── test_phase3d_career_mode.py
│   ├── test_phase3d_integration.py
│   ├── test_phase3f_integration.py
│   ├── test_reporting_agent.py
│   ├── test_schemas_3f.py
│   ├── test_social_service.py
│   ├── test_streak.py
│   ├── test_telegram_bot_commands.py
│   ├── test_telegram_commands.py
│   ├── test_timezone_utils.py
│   ├── test_ux.py
│   └── test_visualization_service.py
│
├── constitution.md                    # The Life Constitution document
├── Dockerfile                         # Container build instructions
├── requirements.txt                   # Python dependencies
├── pyproject.toml                     # Project metadata & pytest config
├── .env                               # Local environment variables (not committed)
├── .gitignore                         # Git ignore patterns
└── .dockerignore                      # Docker build ignore patterns
```

### Code Statistics

| Category | Files | Approximate Lines |
|----------|-------|-------------------|
| **Application** (`src/`) | 35 | ~12,000 |
| **Tests** (`tests/`) | 31 | ~9,000 |
| **Configuration** | 4 | ~200 |
| **Documentation** | 90+ | ~15,000 |
| **Total** | 160+ | ~36,000 |

---

## Appendix A: Constitution Modes

The system adapts its expectations based on the user's current life situation:

| Mode | Description | Expectations |
|------|-------------|-------------|
| **Optimization** | Peak performance phase | All 6 Tier 1 items expected daily |
| **Maintenance** | Steady state | 5/6 Tier 1 acceptable, flexibility on deep work |
| **Survival** | Crisis mode (injury, emergency) | 3/6 minimum, focus on sleep + zero porn |

## Appendix B: Career Modes

The Skill Building Tier 1 question adapts to career mode:

| Mode | Question | Activity Types |
|------|----------|---------------|
| **skill_building** | "2+ hours skill building?" | LeetCode, System Design, Projects, Courses |
| **job_searching** | "Job search progress today?" | Applications, Networking, Interview Prep |
| **employed** | "Work toward promotion/raise?" | Side Projects, Certifications, Leadership |

## Appendix C: Timezone Catalog

60+ timezones organized by region:
- **Americas:** US/Eastern, US/Central, US/Pacific, America/New_York, etc.
- **Europe:** Europe/London, Europe/Berlin, Europe/Paris, etc.
- **Asia:** Asia/Kolkata, Asia/Tokyo, Asia/Singapore, etc.
- **Oceania:** Australia/Sydney, Pacific/Auckland, etc.
- **Africa:** Africa/Cairo, Africa/Lagos, etc.

---

*This document reflects the system architecture as of February 9, 2026, after completion of all P2/P3 implementation phases.*
