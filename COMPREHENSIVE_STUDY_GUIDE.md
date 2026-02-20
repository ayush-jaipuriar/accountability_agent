# Comprehensive Senior Software Engineer Study Guide
## Constitution Accountability Agent — All Phases (1 through D)

> **Scope:** Every concept, pattern, algorithm, and design decision used across all 12 phases of the Accountability Agent project, explained at a senior software engineer interview level.

---

## Table of Contents

1. [System Architecture Overview](#1-system-architecture-overview)
2. [Python Language Deep-Dive](#2-python-language-deep-dive)
3. [FastAPI and ASGI Web Servers](#3-fastapi-and-asgi-web-servers)
4. [Webhook Architecture vs Polling](#4-webhook-architecture-vs-polling)
5. [Telegram Bot Development](#5-telegram-bot-development)
6. [Google Cloud Platform Services](#6-google-cloud-platform-services)
7. [Firestore NoSQL Database Design](#7-firestore-nosql-database-design)
8. [LangGraph Multi-Agent Systems](#8-langgraph-multi-agent-systems)
9. [LLM Integration and Prompt Engineering](#9-llm-integration-and-prompt-engineering)
10. [Design Patterns Used](#10-design-patterns-used)
11. [State Machine and Conversation Management](#11-state-machine-and-conversation-management)
12. [Pattern Detection and Sliding Window Algorithms](#12-pattern-detection-and-sliding-window-algorithms)
13. [Rate Limiting Algorithms](#13-rate-limiting-algorithms)
14. [Timezone Engineering](#14-timezone-engineering)
15. [Observability: Logging, Metrics, and Health Checks](#15-observability-logging-metrics-and-health-checks)
16. [Docker and Containerization](#16-docker-and-containerization)
17. [Cloud Run Serverless Deployment](#17-cloud-run-serverless-deployment)
18. [Cloud Scheduler and Cron Systems](#18-cloud-scheduler-and-cron-systems)
19. [Security Engineering](#19-security-engineering)
20. [Data Modeling with Pydantic](#20-data-modeling-with-pydantic)
21. [Async Programming and Concurrency](#21-async-programming-and-concurrency)
22. [Configuration Management](#22-configuration-management)
23. [Feature Flags and Backward Compatibility](#23-feature-flags-and-backward-compatibility)
24. [Behavioral Psychology in Software](#24-behavioral-psychology-in-software)
25. [Gamification Systems](#25-gamification-systems)
26. [Data Visualization and Reporting](#26-data-visualization-and-reporting)
27. [Export Systems (CSV, JSON, PDF)](#27-export-systems-csv-json-pdf)
28. [Social Features Architecture](#28-social-features-architecture)
29. [Testing Strategy](#29-testing-strategy)
30. [Cost Optimization](#30-cost-optimization)
31. [Error Handling and Graceful Degradation](#31-error-handling-and-graceful-degradation)
32. [Git Workflow and Security Hygiene](#32-git-workflow-and-security-hygiene)
33. [Phase-by-Phase Architecture Evolution](#33-phase-by-phase-architecture-evolution)

---

## 1. System Architecture Overview

### High-Level Data Flow

```
User (Telegram App)
    ↓ sends message
Telegram Servers
    ↓ HTTPS POST (webhook)
Cloud Run (FastAPI)
    ↓ parses Update object
Bot Handler (python-telegram-bot)
    ↓ routes to handler
Conversation / Agent Layer
    ↓ business logic
Firestore (database) ←→ Vertex AI (Gemini LLM)
    ↓ response
User (Telegram App)
```

### Architectural Layers

| Layer | Responsibility | Files |
|-------|---------------|-------|
| **Presentation** | Telegram messages, formatting, inline keyboards | `telegram_bot.py`, `ux.py`, `stats_commands.py` |
| **Routing** | Intent classification, conversation flow management | `supervisor.py`, `conversation.py` |
| **Business Logic** | Check-in processing, pattern detection, compliance | `checkin_agent.py`, `pattern_detection.py`, `compliance.py`, `streak.py` |
| **Services** | Database access, LLM calls, analytics | `firestore_service.py`, `llm_service.py`, `analytics_service.py` |
| **Infrastructure** | Web server, cron, metrics, rate limiting | `main.py`, `config.py`, `metrics.py`, `rate_limiter.py` |

### Why This Layering Matters

**Separation of Concerns** is the most fundamental principle in this architecture. Each layer has a single responsibility:

- **Presentation layer** never talks to the database directly — it goes through services.
- **Business logic** doesn't know about Telegram's API format — it works with domain objects.
- **Services** don't know about the UI — they return plain data.

This means you can swap Telegram for Slack by only changing the presentation layer. You can swap Firestore for PostgreSQL by only changing the service layer. The business logic remains untouched.

**Key Interview Concept:** Hexagonal Architecture (Ports and Adapters). The core domain (agents, compliance, streaks) is surrounded by adapters (Telegram, Firestore, Gemini). The adapters can be swapped without touching the core. This is why `firestore_service.py` exists as a dedicated service layer — the rest of the application never imports `google.cloud.firestore` directly.

---

## 2. Python Language Deep-Dive

### 2.1 Type Hints and Type Safety

Python is dynamically typed, but this project uses **type hints extensively** for several reasons:

```python
def calculate_new_streak(
    current_streak: int,
    last_checkin_date: Optional[str],
    new_checkin_date: str
) -> int:
```

**Why Type Hints?**
- **Documentation:** The function signature tells you exactly what it expects and returns.
- **IDE Support:** Autocomplete, error detection, refactoring tools all work better.
- **Runtime Validation:** Pydantic uses type hints for automatic validation.
- **Maintainability:** New developers understand the codebase faster.

**Key Types Used:**
- `Optional[str]` — Value can be `str` or `None`. Used when a field may not exist (e.g., `last_checkin_date` is `None` for a new user).
- `List[str]` — A list containing strings. Used for achievement IDs, referral codes, etc.
- `Dict[str, Any]` — A dictionary with string keys and values of any type.
- `Tuple[bool, Optional[str]]` — A fixed-size sequence. Used by rate limiter's `check()` to return both a boolean and an optional message.

### 2.2 TypedDict vs Dataclass vs Pydantic BaseModel

This project uses all three, each for a different purpose:

| Type | When Used | Why |
|------|-----------|-----|
| `TypedDict` | LangGraph state (`ConstitutionState`) | LangGraph requires TypedDict for state schemas; gives dictionary-like access with type checking |
| `BaseModel` (Pydantic) | Data models (`User`, `DailyCheckIn`) | Validation on construction, serialization to/from dict/JSON, field defaults |
| Plain `dict` | Firestore documents | Firestore's native format is dictionaries |

**TypedDict Deep-Dive:**

```python
class ConstitutionState(TypedDict):
    user_id: str
    checkin_answers: Annotated[Dict[str, Any], add]
    detected_patterns: Annotated[List[Dict[str, Any]], add]
```

`TypedDict` creates a type-checkable dictionary. Unlike `dataclass`, it's still a regular `dict` at runtime — you access fields with `state["user_id"]`, not `state.user_id`. This is important for LangGraph, which needs to merge state updates from different agents using dictionary operations.

### 2.3 `Annotated` and Reducer Functions

```python
from typing import Annotated
from operator import add

checkin_answers: Annotated[Dict[str, Any], add]
```

`Annotated[T, metadata]` attaches metadata to a type without changing the type itself. Here, `add` is a **reducer function** from Python's `operator` module.

**What does `add` do as a reducer?**
- For lists: concatenation (`[1,2] + [3] = [1,2,3]`)
- For dicts: merge (`{"a":1}.update({"b":2}) = {"a":1, "b":2}`)

**Why this matters for LangGraph:** When multiple agents update the state, LangGraph needs to know HOW to merge their updates. For `checkin_answers`, we want answers from different steps to MERGE (not replace). Without the reducer, the second agent's answers would overwrite the first agent's.

### 2.4 `defaultdict` and `lambda` for Nested Structures

```python
from collections import defaultdict

self._requests: dict[str, dict[str, list[datetime]]] = defaultdict(
    lambda: defaultdict(list)
)
```

This creates a **two-level auto-initializing dictionary**:
- Level 1: `user_id` → inner dict (auto-created)
- Level 2: `tier` → list of timestamps (auto-created)

**Why `defaultdict`?**
Without it, you'd need to check and initialize at every level:
```python
# Without defaultdict (verbose and error-prone)
if user_id not in self._requests:
    self._requests[user_id] = {}
if tier not in self._requests[user_id]:
    self._requests[user_id][tier] = []
self._requests[user_id][tier].append(timestamp)

# With defaultdict (clean)
self._requests[user_id][tier].append(timestamp)
```

**Why `lambda: defaultdict(list)` instead of just `defaultdict(list)`?**
`defaultdict` takes a **factory function** — a callable that returns the default value. `lambda: defaultdict(list)` creates a new `defaultdict(list)` for each missing key, giving us the nested structure.

### 2.5 List Comprehensions and Generator Expressions

```python
# List comprehension: Creates a list
entries[:] = [t for t in entries if t > cutoff]

# Generator expression: Lazy evaluation (doesn't create intermediate list)
completed = sum(1 for item in items if item)

# Conditional expression
time_str = f"{minutes}m {seconds}s" if minutes > 0 else f"{seconds}s"
```

**`entries[:] = ...` vs `entries = ...`:**
`entries[:] = ` modifies the list **in-place** (same object, new contents). `entries = ` would rebind the variable to a new list, but the original list (which other references point to) would be unchanged. In the rate limiter, we need in-place modification because the list is stored inside a dictionary that other code references.

### 2.6 The `global` Keyword and Module-Level State

```python
_supervisor_agent_instance: Optional[SupervisorAgent] = None

def get_supervisor_agent(project_id: str) -> SupervisorAgent:
    global _supervisor_agent_instance
    if _supervisor_agent_instance is None:
        _supervisor_agent_instance = SupervisorAgent(project_id)
    return _supervisor_agent_instance
```

`global` tells Python "I want to modify the module-level variable, not create a local one." Without `global`, the assignment `_supervisor_agent_instance = SupervisorAgent(...)` would create a **local variable** that shadows the module-level one.

**Python Scoping (LEGB Rule):**
1. **L**ocal — Inside the current function
2. **E**nclosing — Inside enclosing functions (closures)
3. **G**lobal — Module level
4. **B**uilt-in — Python built-ins (`print`, `len`, etc.)

Python looks up names in this order. Reading a global works without `global`, but **writing** requires it.

---

## 3. FastAPI and ASGI Web Servers

### 3.1 What is ASGI?

**ASGI** (Asynchronous Server Gateway Interface) is the async successor to WSGI. It's a specification that defines how a Python web application communicates with a web server.

```
Browser/Client
    ↓ HTTP Request
Uvicorn (ASGI Server)
    ↓ ASGI Protocol
FastAPI (ASGI Application)
    ↓ Route matching
Your handler function
```

**WSGI vs ASGI:**
- **WSGI** (Flask, Django): One request at a time per worker. If a handler waits for a database query, that worker is blocked.
- **ASGI** (FastAPI, Starlette): Hundreds of concurrent requests per worker via `async/await`. While one handler waits for I/O, others can execute.

### 3.2 FastAPI Application Structure

```python
app = FastAPI(
    title="Constitution Accountability Agent",
    docs_url="/docs" if settings.environment == "development" else None,
    redoc_url="/redoc" if settings.environment == "development" else None
)
```

**Conditional API Docs:** In development, Swagger UI (`/docs`) and ReDoc (`/redoc`) are enabled for testing. In production, they're disabled (`None`) to prevent information disclosure (attackers could learn your API structure).

### 3.3 Lifecycle Events

```python
@app.on_event("startup")
async def startup_event():
    # Initialize bot, test Firestore, set webhook

@app.on_event("shutdown")
async def shutdown_event():
    # Gracefully shutdown bot
```

**Startup events** run before the first request is served. This is where you:
- Initialize database connections
- Set up the Telegram webhook
- Register bot handlers
- Validate configuration

**Shutdown events** run when the server receives SIGTERM (Cloud Run sends this before killing the instance). This is where you:
- Close database connections
- Flush pending writes
- Clean up resources

**Why not initialize in global scope?** Because async operations (like setting the webhook) can't run outside an async context. The startup event runs inside the event loop.

### 3.4 Request Processing

```python
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    start_time = time.time()
    try:
        body = await request.json()
        update = Update.de_json(body, bot_manager.application.bot)
        await bot_manager.application.process_update(update)
        return {"status": "ok"}
    except Exception as e:
        metrics.record_error("webhook", str(e))
        return {"status": "ok"}  # Always 200 to Telegram
```

**Critical Design Decision: Always return 200 to Telegram.**

If your webhook returns a non-200 status code, Telegram will **retry** the request — potentially many times. This can cause:
- Duplicate message processing
- Cascading failures (if the error persists)
- Rate limiting from Telegram

By always returning 200, we tell Telegram "message received" and handle errors internally.

### 3.5 Global Exception Handler

```python
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    metrics.record_error("unhandled", str(exc))
    return JSONResponse(status_code=500, content={"detail": "Internal error"})
```

This catches any unhandled exception in any endpoint. It:
1. Records the error in metrics (for monitoring)
2. Returns a generic 500 response (doesn't leak stack traces)
3. Logs the full traceback (for debugging)

**Security:** Never expose stack traces in production responses. They reveal internal file paths, library versions, and business logic — all useful to attackers.

---

## 4. Webhook Architecture vs Polling

### 4.1 Two Ways to Get Updates from Telegram

**Polling (Development):**
```
Bot → "Any new messages?" → Telegram
Bot → "Any new messages?" → Telegram
Bot → "Any new messages?" → Telegram (maybe gets one)
```

**Webhook (Production):**
```
Telegram → "Here's a new message" → Bot (only when there IS a message)
```

### 4.2 Why Webhooks Win for Production

| Aspect | Polling | Webhook |
|--------|---------|---------|
| **Latency** | Depends on poll interval (100ms-2s delay) | Near-instant (Telegram pushes immediately) |
| **Resource Usage** | Constant CPU/network (even when idle) | Zero when idle (event-driven) |
| **Cloud Run Cost** | Instance must stay running | Scale to zero between messages |
| **Complexity** | Simple (just a loop) | Needs HTTPS endpoint + SSL cert |

### 4.3 Webhook Registration

```python
await bot.set_webhook(
    url="https://accountability-agent-xxx.run.app/webhook/telegram"
)
```

This tells Telegram: "Send all updates for this bot to this URL." Telegram requires:
- **HTTPS** (not HTTP) — self-signed certs not accepted on custom domains
- **Valid SSL certificate** — Cloud Run provides this automatically
- **Port 443, 80, 88, or 8443** — Cloud Run handles port mapping

### 4.4 Update Object Structure

When Telegram sends an update to your webhook, it's a JSON object:

```json
{
  "update_id": 123456789,
  "message": {
    "message_id": 42,
    "from": {"id": 123456789, "first_name": "Ayush"},
    "chat": {"id": 123456789, "type": "private"},
    "date": 1706655600,
    "text": "/checkin"
  }
}
```

`Update.de_json()` deserializes this into a Python object that `python-telegram-bot` can process through its handler chain.

---

## 5. Telegram Bot Development

### 5.1 python-telegram-bot Library (v21.0)

This project uses v21.0, which is fully **async** (v13.x was sync, v20+ is async). Key components:

| Component | Purpose |
|-----------|---------|
| `Application` | Main bot application, manages handlers and lifecycle |
| `CommandHandler` | Handles `/command` messages |
| `MessageHandler` | Handles non-command text messages |
| `CallbackQueryHandler` | Handles inline keyboard button presses |
| `ConversationHandler` | Multi-step conversations with state management |

### 5.2 Handler Registration Order

```python
app.add_handler(conversation_handler)  # Priority 1: Check-in flow
app.add_handler(CommandHandler("start", start_command))  # Priority 2: Commands
app.add_handler(MessageHandler(filters.TEXT, general_message))  # Priority 3: Catch-all
```

Handlers are checked **in registration order**. The first matching handler wins. This is why `ConversationHandler` is registered first — when a user is mid-check-in, we don't want a general message handler to intercept their answers.

### 5.3 Inline Keyboards

```python
keyboard = InlineKeyboardMarkup([
    [InlineKeyboardButton("✅ Yes", callback_data="tier1_sleep_yes"),
     InlineKeyboardButton("❌ No", callback_data="tier1_sleep_no")],
])
```

**InlineKeyboardMarkup** creates buttons attached to a message. Each button has:
- `text`: What the user sees ("✅ Yes")
- `callback_data`: What the bot receives when pressed ("tier1_sleep_yes")

**Why callback_data and not just text?** Because:
1. The text can be emoji-heavy or localized — hard to parse reliably
2. `callback_data` is a programmer-controlled string you can parse deterministically
3. You can encode state in it (e.g., `tier1_sleep_yes` tells you the category AND the answer)

### 5.4 CallbackQuery Handling

```python
async def handle_tier1_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()  # Acknowledge the button press (removes loading spinner)
    
    data = query.data  # "tier1_sleep_yes"
    item, answer = parse_callback(data)
    
    # Edit the original message (instead of sending a new one)
    await query.edit_message_text(f"Sleep: {'✅' if answer else '❌'}")
```

`query.answer()` is required by Telegram's API — it tells the client to stop showing the "loading" indicator on the button. If you don't call it within 30 seconds, the user sees a timeout error.

### 5.5 Context and User Data

```python
context.user_data["checkin_answers"] = {"sleep": True, "training": False}
```

`context.user_data` is a per-user dictionary that persists across handler calls within the same `Application` instance. It's used to track state during multi-step conversations (like the check-in flow).

**Important:** This is **in-memory only**. If Cloud Run restarts the instance, all `user_data` is lost. For persistence, we use Firestore (partial check-in data is saved to `partial_checkins` collection).

---

## 6. Google Cloud Platform Services

### 6.1 Service Architecture on GCP

```
Cloud Scheduler (cron)
    ↓ HTTPS POST (with auth header)
Cloud Run (compute)
    ↓ reads/writes
Firestore (database)
    ↓ generates content
Vertex AI / Gemini (LLM)
```

### 6.2 Application Default Credentials (ADC)

```python
# In production (Cloud Run):
self.db = firestore.Client()  # No credentials needed!

# In development:
# GOOGLE_APPLICATION_CREDENTIALS=/path/to/key.json
self.db = firestore.Client()  # Uses the key file
```

**ADC** is GCP's automatic credential discovery system. It checks, in order:
1. `GOOGLE_APPLICATION_CREDENTIALS` environment variable (points to a service account key file)
2. **Attached service account** (Cloud Run, GCE, GKE automatically have one)
3. `gcloud auth application-default login` (developer's personal credentials)

**Why this matters:** In production, Cloud Run's identity IS the service account. No key files needed. This is more secure because:
- No key file to leak
- Credentials are automatically rotated
- IAM permissions are scoped to the service

### 6.3 Secret Manager

Sensitive values (like `TELEGRAM_BOT_TOKEN`) are stored in **Secret Manager**, not as plain-text environment variables.

```
Cloud Run → Secret Manager → Environment Variable (injected at container start)
```

Cloud Run can mount secrets as environment variables at deploy time. The application code just reads `os.getenv("TELEGRAM_BOT_TOKEN")` — it doesn't know the value came from Secret Manager.

### 6.4 IAM and Least Privilege

The Cloud Run service account has only the permissions it needs:
- `roles/datastore.user` — Read/write Firestore
- `roles/aiplatform.user` — Call Vertex AI
- `roles/secretmanager.secretAccessor` — Read secrets

**Principle of Least Privilege:** If the service account were compromised, the attacker could only access Firestore, Vertex AI, and secrets — not BigQuery, Cloud Storage, or other services.

---

## 7. Firestore NoSQL Database Design

### 7.1 Document-Oriented Data Model

Firestore is a **document database** (like MongoDB). Data is organized as:
- **Collections** → contain **Documents** → contain **Fields** and **Subcollections**

```
users/                          ← Collection
  {user_id}/                    ← Document (one per user)
    - name: "Ayush"             ← Field
    - streaks: {                ← Map (nested object)
        current_streak: 47,
        longest_streak: 47
      }
    
daily_checkins/                 ← Collection
  {user_id}/                    ← Document (container)
    checkins/                   ← Subcollection
      {date}/                   ← Document (one per day)
        - compliance_score: 100
        - tier1_non_negotiables: {...}
```

### 7.2 Why Subcollections?

The project uses `daily_checkins/{user_id}/checkins/{date}` instead of a flat `checkins` collection.

**Benefits:**
1. **Scoped queries:** Get all check-ins for one user without scanning the entire collection.
2. **Natural sharding:** Each user's data is isolated.
3. **Security rules:** You can write Firestore security rules that say "users can only read their own subcollection."

**Trade-off:** Cross-user queries (e.g., "find all users with compliance < 50% today") require querying each user separately. For this project, that's acceptable because pattern detection scans are per-user.

### 7.3 Transactions for Data Integrity

```python
@firestore.transactional
def _transactional_checkin(transaction, user_ref, checkin_ref, checkin_data, streak_updates):
    transaction.set(checkin_ref, checkin_data)
    transaction.update(user_ref, {"streaks": streak_updates})
```

A **transaction** ensures that the check-in storage AND streak update happen **atomically** — either both succeed or neither does.

**Why is this critical?**
Without a transaction, this could happen:
1. Check-in stored successfully ✅
2. Server crashes before streak update 💥
3. User has a check-in but their streak didn't increment 🐛

Firestore transactions use **optimistic concurrency control:**
1. Read the current values
2. Compute new values locally
3. Attempt to write — if the data changed since the read, the transaction **retries** automatically
4. Maximum 5 retry attempts before failing

### 7.4 Serialization: Pydantic ↔ Firestore

```python
class User(BaseModel):
    def to_firestore(self) -> dict:
        return {
            "streaks": self.streaks.model_dump(),
            "created_at": self.created_at,
            ...
        }
    
    @classmethod
    def from_firestore(cls, data: dict) -> "User":
        if "streaks" in data and isinstance(data["streaks"], dict):
            data["streaks"] = UserStreaks(**data["streaks"])
        return cls(**data)
```

Firestore stores plain dictionaries, timestamps, and primitive types. Pydantic models need to be converted:
- **To Firestore:** `model.model_dump()` converts nested Pydantic models to dictionaries
- **From Firestore:** `cls(**data)` reconstructs the Pydantic model, with manual handling for nested types that Pydantic can't auto-coerce

### 7.5 Querying Patterns

```python
# Get recent check-ins (date range query)
checkins_ref = (
    self.db.collection('daily_checkins')
    .document(user_id)
    .collection('checkins')
    .where(filter=FieldFilter('date', '>=', start_date))
    .where(filter=FieldFilter('date', '<=', end_date))
    .order_by('date', direction=firestore.Query.DESCENDING)
)
```

**Firestore query limitations:**
- No `JOIN` (it's NoSQL) — you denormalize data or do multiple queries
- No `OR` queries across different fields — use `in` operator or multiple queries
- Compound queries need **composite indexes** (Firestore auto-suggests them)
- Range filters (`>=`, `<=`) can only apply to a single field per query

---

## 8. LangGraph Multi-Agent Systems

### 8.1 What is a Multi-Agent Architecture?

Instead of one monolithic handler that does everything, we decompose the system into **specialized agents**, each responsible for one domain:

```
User Message
    ↓
Supervisor Agent (intent classification)
    ├→ CheckIn Agent (daily check-in flow)
    ├→ Emotional Agent (CBT-style support)
    ├→ Query Agent (data queries)
    └→ Command Handler (bot commands)
```

**Benefits:**
- **Single Responsibility:** Each agent is an expert in one thing.
- **Independent Scaling:** You can optimize or replace one agent without affecting others.
- **Testability:** Each agent can be unit tested in isolation.
- **Cost Control:** Only the relevant agent is invoked (not all of them).

### 8.2 LangGraph State Schema

```python
class ConstitutionState(TypedDict):
    user_id: str
    message: str
    intent: Optional[str]
    checkin_answers: Annotated[Dict[str, Any], add]  # Merge reducer
    detected_patterns: Annotated[List[Dict[str, Any]], add]  # Append reducer
    response: Optional[str]
    error: Optional[str]
```

The **state** is the central data structure that flows through the agent graph. Think of it as a shared context object:

1. **Webhook creates initial state** (user_id, message, timestamp)
2. **Supervisor adds intent** (checkin, emotional, query, command)
3. **Domain agent processes** (adds checkin_answers, compliance_score, response)
4. **Response is sent** (state.response → Telegram message)

### 8.3 State Merging Strategy

Two types of fields:

**Replace fields** (default): New value overwrites old value.
```python
intent: Optional[str]  # Supervisor sets this once
```

**Merge fields** (with reducer): New value is combined with old value.
```python
checkin_answers: Annotated[Dict[str, Any], add]  # Dict merge
detected_patterns: Annotated[List[Dict[str, Any]], add]  # List append
```

This is critical when multiple steps contribute to the same field. For example, during a check-in, each question adds answers to `checkin_answers`:

```python
# After Q1: {"sleep": True, "training": True}
# After Q2: {"challenges": "felt tired"}
# Merged:   {"sleep": True, "training": True, "challenges": "felt tired"}
```

### 8.4 Supervisor Agent: Zero-Shot Intent Classification

```python
prompt = f"""Classify the user's intent from this message.
MESSAGE: "{message}"
USER CONTEXT:
- Current streak: {streak} days
- Last check-in: {last_checkin_str}

INTENT OPTIONS:
1. emotional - User expressing feelings, emotions, struggles
2. checkin - User wants to start/continue daily check-in
3. query - Factual questions about stats, constitution, bot
4. command - Bot commands (starts with /)

Respond with EXACTLY ONE WORD: emotional, checkin, query, or command"""
```

**Zero-shot classification** means the LLM classifies intents without being explicitly trained on labeled examples. We achieve this through **prompt engineering:**

1. **Clear task definition:** "Classify the user's intent"
2. **Context injection:** Streak and last check-in help disambiguate (e.g., "let's go" from a user who hasn't checked in today = checkin)
3. **Intent descriptions with examples:** Each intent is described with typical phrases
4. **Priority ordering:** Emotional takes priority over query (if ambiguous, emotional is safer)
5. **Output constraint:** "EXACTLY ONE WORD" prevents verbose responses

**Temperature = 0.1:** Low temperature makes the model nearly deterministic. Same input → same output. This is essential for classification (we want consistency, not creativity).

### 8.5 Fast Keyword Pre-Filter

```python
query_keywords = [
    "what's my", "what is my", "show me", "show my",
    "how much", "how many", "when did", "average", ...
]

if any(keyword in message_lower for keyword in query_keywords):
    state["intent"] = "query"
    return state  # Skip LLM call entirely
```

**Cost optimization:** If we can classify the intent with a simple keyword check, we skip the LLM call entirely. This saves ~$0.00005 per message and reduces latency from ~1 second to <1 millisecond.

This is a **cascading classification strategy:**
1. First: Cheap heuristic (keyword matching)
2. Only if heuristic fails: Expensive LLM call
3. If LLM fails: Safe default ("query")

### 8.6 Intent Parsing and Robustness

```python
def _parse_intent(self, intent_response: str) -> str:
    intent = intent_response.strip().lower()
    if " " in intent:
        intent = intent.split()[0]
    intent = intent.rstrip('.,!?;:')
    
    intent_mapping = {
        "check-in": "checkin",
        "emotion": "emotional",
        "question": "query",
    }
```

LLMs are probabilistic — they might return "Checkin" (capitalized), "check-in" (hyphenated), or even "The intent is checkin because..." (verbose). This parser handles all variations:
1. Strip whitespace and lowercase
2. Take only the first word (handles verbose responses)
3. Remove trailing punctuation
4. Map common variations to canonical forms
5. Default to "query" for unrecognized intents (safest fallback — queries don't modify state)

---

## 9. LLM Integration and Prompt Engineering

### 9.1 Google GenAI SDK Architecture

```python
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = location
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

self.client = genai.Client()
```

The **Google GenAI SDK** is a unified SDK that works with both:
- **Gemini Developer API** (simpler, API key auth)
- **Vertex AI** (enterprise, IAM auth, more features)

By setting `GOOGLE_GENAI_USE_VERTEXAI=True`, we route through Vertex AI, which uses ADC for authentication and provides enterprise features like VPC-SC, audit logging, and data residency.

### 9.2 Thinking Budget Optimization

```python
response = await self.client.aio.models.generate_content(
    model=self.model_name,
    contents=prompt,
    config=types.GenerateContentConfig(
        max_output_tokens=max_output_tokens,
        temperature=temperature,
        thinking_config=types.ThinkingConfig(thinking_budget=0),
    )
)
```

**Gemini 2.5 Flash** has a "thinking" mode where it reasons internally before responding. This uses invisible "thinking tokens" that you're billed for but don't see in the output.

**`thinking_budget=0`** disables thinking entirely. For our use cases (intent classification, feedback generation), thinking is unnecessary overhead. This saves approximately **40% on token costs**.

**When to use thinking:**
- Complex reasoning tasks (math, multi-step logic)
- Code generation requiring deep analysis
- Tasks where accuracy > cost

**When to disable thinking:**
- Classification tasks (one-word output)
- Template-based generation
- Simple text formatting

### 9.3 Token Counting and Cost Tracking

```python
self.total_input_tokens += input_tokens
self.total_output_tokens += output_tokens

estimated_cost = (input_tokens / 1_000_000 * 0.25) + (output_tokens / 1_000_000 * 0.50)
```

**What is a token?**
- Roughly 4 characters or 0.75 words in English
- "accountability" = 3 tokens, "I" = 1 token
- Pricing is per million tokens

**Gemini 2.5 Flash Pricing (2026):**
- Input: $0.25 per million tokens
- Output: $0.50 per million tokens

**Budget analysis for this project:**
- Intent classification: ~200 input + 1 output = $0.00005/call
- Feedback generation: ~500 input + 200 output = $0.00023/call
- Daily usage (3 messages): ~$0.00084/day
- Monthly: ~$0.17/month (well within free tier)

### 9.4 Prompt Engineering Patterns

**Pattern 1: Role Assignment**
```
You are a strict but empathetic accountability coach...
```
Frames the LLM's persona for consistent tone.

**Pattern 2: Context Injection**
```
USER CONTEXT:
- Current streak: 47 days
- Last 3 days compliance: [100%, 83%, 67%]
- Constitution mode: Optimization
```
Gives the LLM relevant data to personalize responses.

**Pattern 3: Output Constraints**
```
Respond in EXACTLY this format:
1. VALIDATE: (2 sentences)
2. REFRAME: (2 sentences)
3. ACTION: (3 bullet points)
```
Structured output formats are more reliable than free-form responses.

**Pattern 4: Few-Shot Examples**
```
Examples:
- "I'm feeling lonely" → emotional
- "What's my streak?" → query
- "Let's check in" → checkin
```
Showing the LLM examples improves classification accuracy.

---

## 10. Design Patterns Used

### 10.1 Singleton Pattern

```python
_supervisor_agent_instance: Optional[SupervisorAgent] = None

def get_supervisor_agent(project_id: str) -> SupervisorAgent:
    global _supervisor_agent_instance
    if _supervisor_agent_instance is None:
        _supervisor_agent_instance = SupervisorAgent(project_id)
    return _supervisor_agent_instance
```

**Used in:** `supervisor.py`, `llm_service.py`, `checkin_agent.py`, `intervention.py`, `emotional_agent.py`, `query_agent.py`, `rate_limiter.py`, `metrics.py`, `config.py`

**Why Singleton?**
- LLM service initializes a client connection — expensive, should only happen once
- Metrics collector needs to aggregate data across all requests — one instance
- Rate limiter needs shared state across all handler calls — one instance

**Why not a class-level singleton (metaclass)?**
The module-level function approach is simpler and more Pythonic. It also supports lazy initialization (the instance isn't created until first access) and is easy to reset for testing.

### 10.2 Service Layer Pattern

```python
# All database access goes through the service
from src.services.firestore_service import firestore_service

user = firestore_service.get_user(user_id)
firestore_service.store_checkin(user_id, checkin)
```

The **Service Layer** is the exclusive gateway to the database. No other module imports `google.cloud.firestore` directly.

**Benefits:**
- **Abstraction:** The rest of the app doesn't know or care that we're using Firestore.
- **Testability:** Mock `firestore_service` in tests instead of mocking Firestore SDK internals.
- **Consistency:** All database operations go through one place — easy to add logging, caching, or validation.
- **Migration:** To switch from Firestore to PostgreSQL, only `firestore_service.py` needs to change.

### 10.3 State Machine Pattern

The check-in flow is a **finite state machine:**

```
START → Q1_TIER1 → Q2_CHALLENGES → Q3_RATING → Q4_TOMORROW → END
```

Each state:
- Sends a message/question to the user
- Waits for input
- Validates input
- Transitions to the next state (or stays in current state if input is invalid)

```python
ConversationHandler(
    entry_points=[CommandHandler("checkin", start_checkin)],
    states={
        Q1_TIER1: [CallbackQueryHandler(handle_tier1)],
        Q2_CHALLENGES: [MessageHandler(filters.TEXT, handle_challenges)],
        Q3_RATING: [CallbackQueryHandler(handle_rating)],
        Q4_TOMORROW: [MessageHandler(filters.TEXT, handle_tomorrow)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    block=True,
)
```

**`block=True`:** While a user is in the check-in conversation, no other handler can process their messages. This prevents mid-check-in messages from being routed to the general message handler.

### 10.4 Strategy Pattern

```python
def get_skill_building_question(career_mode: str) -> str:
    questions = {
        "skill_building": "Did you spend 2+ hours on skill building today?",
        "job_searching": "Did you spend 2+ hours on job search activities today?",
        "employed": "Did you spend 2+ hours on professional development today?",
    }
    return questions.get(career_mode, questions["skill_building"])
```

The **Strategy Pattern** selects behavior at runtime based on context. Here, the question text changes based on the user's career mode, but the overall check-in flow is identical.

### 10.5 Mediator Pattern

The **Reporting Agent** coordinates multiple services without them knowing about each other:

```python
class ReportingAgent:
    async def generate_weekly_report(self, user_id: str):
        # 1. Get data from Firestore service
        checkins = firestore_service.get_recent_checkins(user_id, days=7)
        
        # 2. Generate graphs from visualization service
        graphs = visualization_service.generate_graphs(checkins)
        
        # 3. Generate insights from LLM service
        insights = await llm_service.generate_text(analysis_prompt)
        
        # 4. Compile report
        return Report(checkins, graphs, insights)
```

`firestore_service`, `visualization_service`, and `llm_service` don't know about each other. The `ReportingAgent` orchestrates them. This keeps each service focused and decoupled.

### 10.6 Factory Pattern (via `create_initial_state`)

```python
def create_initial_state(user_id, message, message_id, username=None):
    return ConstitutionState(
        user_id=user_id,
        message=message,
        intent=None,
        checkin_answers={},
        detected_patterns=[],
        ...
    )
```

This factory function ensures every state object starts with the correct structure and defaults. Without it, each caller would need to know all the fields and their initial values.

### 10.7 Observer Pattern (via Metrics)

```python
# In webhook handler:
metrics.increment("checkins_total")
metrics.record_latency("webhook_latency", elapsed_ms)

# In error handler:
metrics.record_error("firestore", str(e))
```

The metrics system is an **observer** — it passively collects events from across the application without the application needing to know how metrics are stored or reported. The metrics module doesn't affect the flow of the application.

---

## 11. State Machine and Conversation Management

### 11.1 Conversation Handler Architecture

```python
ConversationHandler(
    entry_points=[CommandHandler("checkin", start_checkin)],
    states={
        Q1_TIER1: [CallbackQueryHandler(handle_tier1)],
        Q2_CHALLENGES: [MessageHandler(filters.TEXT, handle_challenges)],
        Q3_RATING: [CallbackQueryHandler(handle_rating)],
        Q4_TOMORROW: [MessageHandler(filters.TEXT, handle_tomorrow)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    block=True,
    per_chat=True,
    per_user=True,
)
```

**Entry Points:** What triggers the conversation (e.g., `/checkin` command).

**States:** A dictionary mapping state identifiers (integers) to lists of handlers. The conversation can only be in one state at a time for each user.

**Fallbacks:** Handlers that work in any state (e.g., `/cancel` to abort the conversation).

**`per_chat=True, per_user=True`:** Conversations are isolated per-user-per-chat. User A's check-in doesn't interfere with User B's.

### 11.2 State Transitions

```python
async def handle_tier1(update, context):
    # Process tier 1 answer
    context.user_data["tier1"] = parse_answer(update.callback_query.data)
    
    # Transition to next state
    await update.callback_query.message.reply_text("What challenges did you face?")
    return Q2_CHALLENGES  # ← State transition

async def handle_challenges(update, context):
    context.user_data["challenges"] = update.message.text
    # ... ask next question ...
    return Q3_RATING  # ← State transition
```

Returning an integer from a handler tells `ConversationHandler` which state to transition to. Returning `ConversationHandler.END` ends the conversation.

### 11.3 Quick Check-In (Abbreviated Flow)

Phase 3E added a `/quickcheckin` that only asks Tier 1 questions (skipping challenges, rating, and tomorrow's plan).

```
/quickcheckin → Q1_TIER1 (all 6 items) → END
```

**Business Rules:**
- Maximum 2 quick check-ins per week (tracked per user)
- Resets every Monday at 00:00 IST via Cloud Scheduler
- Quick check-ins don't include AI feedback (saves LLM cost)

### 11.4 Partial Check-In Recovery

If a user starts a check-in but doesn't finish (e.g., network drops, app closes), the partial answers are saved to Firestore:

```python
# Save partial state
firestore_service.save_partial_checkin(user_id, {
    "step": Q2_CHALLENGES,
    "answers_so_far": context.user_data.get("tier1", {})
})

# Recover on /resume
partial = firestore_service.get_partial_checkin(user_id)
context.user_data.update(partial["answers_so_far"])
return partial["step"]  # Resume from where they left off
```

This prevents users from losing progress in a multi-step flow — a critical UX consideration.

---

## 12. Pattern Detection and Sliding Window Algorithms

### 12.1 Threshold-Based Pattern Detection

Each pattern is defined by:
- **Metric:** What to measure (sleep hours, training days, compliance score)
- **Threshold:** When to trigger (sleep < 6h, missed training 3 days)
- **Window:** How far back to look (last 3 days, last 7 days, last 5 days)
- **Severity:** How urgent (CRITICAL, HIGH, MEDIUM, WARNING)

```python
def detect_sleep_degradation(self, checkins: List[DailyCheckIn]) -> Optional[dict]:
    recent = checkins[-3:]  # Sliding window: last 3 days
    
    consecutive_poor = 0
    for checkin in recent:
        if checkin.tier1_non_negotiables.sleep_hours < 6:
            consecutive_poor += 1
        else:
            consecutive_poor = 0  # Reset on any good night
    
    if consecutive_poor >= 3:
        avg_sleep = sum(c.tier1_non_negotiables.sleep_hours for c in recent) / len(recent)
        return {
            "type": "sleep_degradation",
            "severity": "high",
            "data": {"avg_sleep": avg_sleep, "consecutive_days": consecutive_poor}
        }
    return None
```

### 12.2 Sliding Window Algorithm Explained

A **sliding window** looks at the most recent N items in a sequence:

```
Day:     1    2    3    4    5    6    7    8
Sleep:   7    6    5    4    8    5    4    3
         ─────────────┐
Window (3):     [5, 4, 8]  → Not triggered (8 >= 6)
                    [4, 8, 5]  → Not triggered (8 >= 6)
                       [8, 5, 4]  → Not triggered (8 >= 6)
                          [5, 4, 3]  → TRIGGERED! (all < 6)
```

**Why sliding windows instead of fixed windows?**
- **Fixed window** (e.g., "this week"): Misses patterns that span window boundaries. Poor sleep on Sat-Mon would be split across two weeks.
- **Sliding window**: Always looks at the most recent N days, regardless of calendar boundaries.

### 12.3 The 9 Detection Rules

| Pattern | Window | Threshold | Severity | Rationale |
|---------|--------|-----------|----------|-----------|
| Sleep Degradation | 3 days | <6 hours consecutively | HIGH | Cascading failure risk |
| Training Abandonment | 3 days | 3+ missed (excl. rest) | MEDIUM | Fitness regression |
| Porn Relapse | 7 days | 3+ violations | CRITICAL | Addiction cycle |
| Compliance Decline | 3 days | <70% consecutively | MEDIUM | Standards erosion |
| Deep Work Collapse | 5 days | <1.5 hours | CRITICAL | Career goal at risk |
| Snooze Trap | 3 days | >30min late waking | WARNING | Morning routine erosion |
| Consumption Vortex | 5 days | >3 hours consumption | WARNING | Creator→consumer shift |
| Relationship Interference | 7 days | >70% boundary-failure correlation | CRITICAL | Toxic pattern |
| Ghosting | 2+ days | Missing check-ins | ESCALATING | System abandonment |

### 12.4 Correlation-Based Detection

The **Relationship Interference** pattern uses correlation, not simple thresholds:

```python
def detect_relationship_interference(self, checkins):
    boundary_failures = [not c.tier1.boundaries for c in checkins]
    sleep_failures = [not c.tier1.sleep for c in checkins]
    
    # Count co-occurrences
    co_failures = sum(1 for b, s in zip(boundary_failures, sleep_failures) if b and s)
    total_boundary_fails = sum(boundary_failures)
    
    if total_boundary_fails > 0:
        correlation = co_failures / total_boundary_fails
        if correlation > 0.7:  # 70%+ of boundary failures correlate with other failures
            return {"type": "relationship_interference", "severity": "critical"}
```

This is more sophisticated than threshold detection — it identifies **causal patterns** rather than just counting violations.

### 12.5 Ghosting Escalation Model

```
Day 2: 💬 "Hey, I noticed you missed yesterday's check-in..."     (gentle)
Day 3: 📋 "It's been 3 days. Your streak is at risk..."           (concerned)
Day 5: 🚨 "Emergency: 5 days without check-in. Partner notified." (escalation)
```

This implements a **graduated response model** where intervention intensity increases with the duration of absence. The psychology: gentle nudges work for short lapses; escalation is needed for longer ones.

---

## 13. Rate Limiting Algorithms

### 13.1 Sliding Window Rate Limiter

The project implements a **sliding window** rate limiter with two checks:

```python
def check(self, user_id: str, command: str) -> Tuple[bool, Optional[str]]:
    entries = self._requests[user_id][tier]
    now = datetime.utcnow()
    
    # Step 1: Prune old entries (older than 1 hour)
    cutoff = now - timedelta(hours=1)
    entries[:] = [t for t in entries if t > cutoff]
    
    # Step 2: Check hourly limit
    if len(entries) >= config["max_per_hour"]:
        return False, "Rate limit exceeded"
    
    # Step 3: Check cooldown since last request
    if entries:
        elapsed = (now - entries[-1]).total_seconds()
        if elapsed < config["cooldown_seconds"]:
            return False, f"Wait {cooldown_remaining}s"
    
    # Step 4: Record and allow
    entries.append(now)
    return True, None
```

### 13.2 Rate Limiting Algorithms Compared

| Algorithm | How It Works | Pros | Cons |
|-----------|-------------|------|------|
| **Fixed Window** | Count requests per fixed time bucket (e.g., per minute) | Simple to implement | Burst at boundary (2x limit in 2 seconds spanning two windows) |
| **Sliding Window** (our choice) | Count requests in a rolling time window | Accurate, no boundary burst | More memory (stores timestamps) |
| **Token Bucket** | Bucket of tokens, refilled at fixed rate | Smooth rate, allows controlled bursts | Complex refill rate math |
| **Leaky Bucket** | Queue requests, process at fixed rate | Perfectly smooth output | High latency for burst traffic |

### 13.3 Tiered Rate Limits

| Tier | Cooldown | Max/Hour | Commands | Rationale |
|------|----------|----------|----------|-----------|
| **Expensive** | 10 min | 6 | `/report`, `/export` | CPU-intensive (graphs, PDF) + AI |
| **AI-Powered** | 40 sec | 60 | General messages, `/support` | Gemini API costs |
| **Standard** | 3 sec | 90 | `/stats`, `/leaderboard` | DB reads only |
| **Free** | None | ∞ | `/start`, `/help`, `/cancel` | No backend cost |

### 13.4 Admin Bypass

```python
if user_id in self._admin_ids:
    return True, None
```

Admin users bypass all rate limits. This is essential for:
- Testing (you don't want to wait 10 minutes between report generations while debugging)
- Monitoring (admins need unrestricted access to `/admin_status`)

### 13.5 Memory Analysis

```
Per entry: 1 datetime (8 bytes) + list overhead (~56 bytes for the list itself)
Per user-tier: ~60 * 8 = 480 bytes (assuming 60 entries max)
Per user: 3 tiers × 480 = 1,440 bytes
1000 users: 1,440 KB ≈ 1.4 MB
```

In-memory rate limiting is acceptable for this scale. For thousands of concurrent users across multiple instances, you'd need Redis or a distributed rate limiter.

### 13.6 Thread Safety Note

```python
"""
Thread-safety: Python's GIL ensures dict operations are atomic.
For async code (our case), there's no concurrency issue since
we're single-threaded within the event loop.
"""
```

Python's **Global Interpreter Lock (GIL)** ensures only one thread executes Python bytecode at a time. Combined with the fact that our FastAPI app uses `async/await` (single-threaded event loop, not multi-threading), there are no race conditions in dictionary access.

In a multi-worker setup, each worker would have its own rate limiter instance. For true cross-worker rate limiting, you'd need Redis.

---

## 14. Timezone Engineering

### 14.1 The Core Problem

A user in New York (UTC-5) checking in at 11 PM should see "Feb 8" as their check-in date. A user in India (UTC+5:30) at the same instant sees "Feb 9." If we stored dates in UTC, both users would get the UTC date, which would be wrong for at least one of them.

### 14.2 The 3 AM Cutoff Rule

```python
def get_checkin_date(current_time=None, tz="Asia/Kolkata"):
    if local_time.hour < 3:
        checkin_date = (local_time - timedelta(days=1)).date()
    else:
        checkin_date = local_time.date()
```

**What problem does this solve?**
Users who check in at 12:30 AM intend to log "yesterday's" data (they were up late). Without the cutoff, a 12:30 AM check-in on Feb 4 would be logged as Feb 4, but the user is really logging their Feb 3 activities.

**Why 3 AM specifically?**
- It's late enough to catch most night owls
- It's early enough that almost nobody is doing their "next day's" activities at 3 AM
- It provides a clear 3-hour grace period after midnight

### 14.3 Timezone-Aware Bucket Reminders

```python
def get_timezones_at_local_time(utc_now, target_hour, target_minute=0, tolerance_minutes=15):
    matching = []
    for tz_id in all_catalog_timezones:
        local_now = utc_now.astimezone(pytz.timezone(tz_id))
        local_minutes = local_now.hour * 60 + local_now.minute
        target_minutes = target_hour * 60 + target_minute
        diff = abs(local_minutes - target_minutes)
        if diff > 720:
            diff = 1440 - diff  # Midnight wraparound
        if diff <= tolerance_minutes:
            matching.append(tz_id)
    return matching
```

**How timezone-aware reminders work:**

Instead of a fixed "send at 9 PM IST" schedule, the system runs **every 15 minutes** and asks: "Which timezones are currently at 9 PM?"

```
UTC 15:15 → Check: Who's at 9 PM local time?
  → Asia/Kolkata (9:45 PM) ← within 15-min tolerance ✅
  → Send reminder to all users in Asia/Kolkata timezone

UTC 15:30 → Check again
  → Europe/Helsinki (5:30 PM) ← not 9 PM ❌
  → America/New_York (10:30 AM) ← not 9 PM ❌
  → No reminders needed
```

**Midnight Wraparound:**
```python
if diff > 720:  # More than 12 hours apart
    diff = 1440 - diff  # 1440 minutes in a day
```

This handles the edge case where `target=23:50` and `current=00:05`. The naive difference is 1425 minutes, but the actual gap is only 15 minutes (crossing midnight). We detect this by checking if the difference exceeds 12 hours and wrapping around.

### 14.4 Naive vs Aware Datetimes

```python
# Naive (no timezone info) — DANGEROUS
dt = datetime(2026, 2, 8, 21, 0)  # Is this UTC? IST? ???

# Aware (has timezone info) — SAFE
dt = IST.localize(datetime(2026, 2, 8, 21, 0))  # Explicitly IST
dt = datetime(2026, 2, 8, 15, 30, tzinfo=pytz.UTC)  # Explicitly UTC
```

**Rule of thumb:** Store in UTC, display in local timezone. Never perform date arithmetic on naive datetimes — the result is ambiguous.

### 14.5 pytz vs zoneinfo (Python 3.9+)

This project uses `pytz` because:
- It was the standard before Python 3.9
- Wider compatibility with older libraries (Firestore SDK, etc.)
- More explicit timezone handling (`localize()` instead of `replace(tzinfo=)`)

**Trade-off:** `pytz.localize()` is needed because `datetime.replace(tzinfo=pytz.timezone(...))` can give wrong results for timezones with historical offset changes. `zoneinfo` (Python 3.9+) handles this correctly with `replace()`.

### 14.6 Backward Compatibility Aliases

```python
def get_current_time_ist() -> datetime:
    return get_current_time("Asia/Kolkata")

def utc_to_ist(utc_datetime: datetime) -> datetime:
    return utc_to_local(utc_datetime, "Asia/Kolkata")
```

When Phase B generalized timezone support, the old IST-specific functions were kept as **aliases** pointing to the new generic functions. This means:
- Zero code changes required for existing callers
- New callers can use the generic versions with any timezone
- Both old and new APIs are tested

This is a textbook example of **backward-compatible refactoring**.

---

## 15. Observability: Logging, Metrics, and Health Checks

### 15.1 The Three Pillars of Observability

| Pillar | What It Tells You | Implementation |
|--------|-------------------|----------------|
| **Logs** | What happened (events, errors) | `JSONFormatter` → Cloud Logging |
| **Metrics** | How much (counters, latencies) | `AppMetrics` → `/admin/metrics` |
| **Traces** | How long (request flow) | `record_latency()` with per-endpoint timing |

### 15.2 Structured JSON Logging

```python
class JSONFormatter(logging.Formatter):
    def format(self, record):
        log_entry = {
            "severity": record.levelname,  # Not "level" — Cloud Logging expects "severity"
            "message": record.getMessage(),
            "module": record.module,
            "timestamp": self.formatTime(record),
        }
        for field in ("user_id", "command", "latency_ms", "error_category"):
            if hasattr(record, field):
                log_entry[field] = getattr(record, field)
        return json.dumps(log_entry)
```

**Why JSON logging?**
Google Cloud Logging automatically parses JSON log lines into structured log entries. This means:
- You can **filter** logs by `severity`, `user_id`, `command`
- You can create **log-based metrics** (e.g., count of errors by category)
- You can set up **alerts** (e.g., notify if error_count > 10 in 5 minutes)

**Why `severity` not `level`?**
Cloud Logging uses `severity` (DEBUG, INFO, WARNING, ERROR, CRITICAL). If you use `level`, it won't be recognized as the severity field.

### 15.3 In-Memory Metrics

```python
class AppMetrics:
    MAX_LATENCY_SAMPLES = 100  # Rolling buffer size
    
    def __init__(self):
        self.counters = defaultdict(int)      # Monotonically increasing
        self.latencies = defaultdict(list)    # Rolling buffer of (timestamp, ms)
        self.errors = defaultdict(int)        # Error counters by category
        self.start_time = datetime.utcnow()   # For uptime calculation
```

**Three metric types:**

1. **Counters** — Always go up. "Total check-ins: 1,247"
2. **Latencies** — Rolling buffer of the last 100 measurements. Enables percentile calculations (p50, p95, p99).
3. **Errors** — Counters segmented by category (firestore, telegram, ai).

### 15.4 Percentile Calculations

```python
def get_latency_stats(self, metric, window_minutes=60):
    values.sort()
    return {
        "p50_ms": values[count // 2],           # Median: typical experience
        "p95_ms": values[int(count * 0.95)],     # 95th percentile: worst for most users
        "p99_ms": values[int(count * 0.99)],     # 99th percentile: tail latency
    }
```

**Why percentiles over averages?**
Averages hide outliers. If 99 requests take 50ms and 1 takes 5000ms, the average is 99ms — which describes nobody's actual experience.

- **p50 (median):** "Half of requests are faster than this"
- **p95:** "95% of requests are faster than this" — this is what users typically experience
- **p99:** "Only 1% of requests are slower than this" — catches tail latency issues

### 15.5 Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    health = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0",
        "checks": {
            "firestore": check_firestore_connection(),
        },
        "metrics": metrics.get_uptime(),
    }
    return health
```

**Cloud Run health checks:** Cloud Run periodically pings `/health` to verify the instance is alive. If it returns non-200 too many times, Cloud Run:
1. Stops routing traffic to that instance
2. Starts a new instance
3. Eventually kills the unhealthy instance

This is **self-healing infrastructure** — the system automatically replaces broken instances without human intervention.

---

## 16. Docker and Containerization

### 16.1 Dockerfile Architecture

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# System dependencies (for matplotlib, Pillow)
RUN apt-get update && apt-get install -y \
    curl fontconfig fonts-dejavu-core \
    libfreetype6 libjpeg62-turbo zlib1g \
    && rm -rf /var/lib/apt/lists/*

# Python dependencies (layer caching)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Application code
COPY . .

ENV PYTHONUNBUFFERED=1
ENV ENVIRONMENT=production

CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT} --workers 1
```

### 16.2 Docker Layer Caching

Docker builds images in **layers**. Each instruction (`FROM`, `RUN`, `COPY`) creates a new layer. Docker caches layers and only rebuilds when the input changes.

```
Layer 1: FROM python:3.11-slim          ← Cached (rarely changes)
Layer 2: RUN apt-get install ...        ← Cached (rarely changes)
Layer 3: COPY requirements.txt .        ← Cached if requirements.txt unchanged
Layer 4: RUN pip install ...            ← Cached if requirements.txt unchanged
Layer 5: COPY . .                       ← Rebuilt every code change
```

**Why `COPY requirements.txt` before `COPY . .`?**

If we copied everything first, ANY code change would invalidate the pip install layer, causing a full dependency reinstall (~2 minutes). By copying `requirements.txt` first, dependencies are only reinstalled when the dependencies actually change.

### 16.3 Multi-Stage Builds (Theory)

While not used in this project, a multi-stage build would look like:

```dockerfile
# Build stage
FROM python:3.11 as builder
COPY requirements.txt .
RUN pip install --user -r requirements.txt

# Production stage
FROM python:3.11-slim
COPY --from=builder /root/.local /root/.local
COPY . .
CMD ...
```

This produces smaller images by excluding build tools. Our image is simple enough that a single stage suffices.

### 16.4 Key Environment Variables

- **`PYTHONUNBUFFERED=1`:** Prevents Python from buffering stdout/stderr. Without this, log messages might be delayed or lost when the container is killed.
- **`PORT`:** Cloud Run sets this dynamically (typically 8080). The CMD reads it via `${PORT}`.
- **`exec`** in CMD: Replaces the shell process with uvicorn. Without `exec`, uvicorn would be a child of the shell, and SIGTERM (from Cloud Run shutdown) would go to the shell, not uvicorn.

### 16.5 .dockerignore

```
.env
.env.*
.credentials/
*.json
tests/
test_*.py
htmlcov/
*.md (except README.md, constitution.md)
```

The `.dockerignore` prevents sensitive files and unnecessary files from being copied into the image. This:
- **Reduces image size** (faster deployments)
- **Prevents secret leakage** (.env files inside the container)
- **Speeds up builds** (less data to copy)

---

## 17. Cloud Run Serverless Deployment

### 17.1 Cloud Run Architecture

```
Internet → Cloud Run Proxy → Container Instance(s)
                                  ↓
                              Your FastAPI app
```

Cloud Run manages:
- **SSL termination** (HTTPS certificate)
- **Load balancing** (routes requests to healthy instances)
- **Auto-scaling** (0 to N instances based on traffic)
- **Concurrency** (80 concurrent requests per instance)

### 17.2 Scale-to-Zero

```yaml
Min instances: 0
Max instances: 3
```

With `min-instances: 0`, Cloud Run **kills all instances when idle**. This means:
- **Zero cost when nobody is using the bot** (Cloud Run charges per-second of instance uptime)
- **Cold start penalty** (~2-5 seconds for the first request after idle period)

**Trade-off:** The first message after idle takes longer because Cloud Run needs to:
1. Pull the container image (cached after first time)
2. Start the container
3. Run the FastAPI startup event (initialize bot, test Firestore)
4. Process the request

### 17.3 Concurrency vs Parallelism

```yaml
Concurrency: 80
Workers: 1
```

**Concurrency = 80** means one instance handles up to 80 **simultaneous requests**. This works because:
- FastAPI is async — while one request waits for Firestore, another can be processed
- Most request time is I/O wait (network calls to Telegram, Firestore, Vertex AI)
- CPU-intensive work is minimal

**Workers = 1** means one uvicorn process per container. More workers would use more memory but allow true parallelism for CPU-bound work.

### 17.4 CPU Throttling

```yaml
CPU Throttling: ON
```

With CPU throttling enabled, the instance only gets CPU allocation while processing a request. Between requests, CPU is paused (billing stops). This is cheaper but means:
- No background tasks between requests
- No cron-like internal scheduling
- All work must be triggered by incoming requests

This is why we use **Cloud Scheduler** for periodic tasks instead of internal timers.

### 17.5 Resource Configuration

| Setting | Value | Rationale |
|---------|-------|-----------|
| Memory | 512Mi | FastAPI + matplotlib + Pillow + reportlab |
| CPU | 1 vCPU | Sufficient for I/O-bound workload |
| Timeout | 300s | Long AI operations + graph generation |

**Why 512Mi memory?** matplotlib and Pillow load large libraries into memory. A minimal FastAPI app needs ~128Mi, but graph generation can peak at ~400Mi.

---

## 18. Cloud Scheduler and Cron Systems

### 18.1 Why External Scheduling?

Because Cloud Run instances can be killed at any time (scale-to-zero), we can't rely on internal timers. Cloud Scheduler sends HTTP requests to wake up the instance and trigger work.

### 18.2 Cron Jobs Configuration

| Job | Schedule | Timezone | Endpoint | Purpose |
|-----|----------|----------|----------|---------|
| `reminder-tz-aware` | `*/15 * * * *` | UTC | `/cron/reminder_tz_aware` | Multi-timezone reminders |
| `pattern-scan` | `0 */6 * * *` | UTC | `/trigger/pattern-scan` | Pattern detection every 6h |
| `reset-quick-checkins` | `0 0 * * 1` | Asia/Kolkata | `/cron/reset_quick_checkins` | Monday weekly reset |
| `weekly-report` | `0 9 * * 0` | Asia/Kolkata | `/trigger/weekly-report` | Sunday 9 AM reports |

### 18.3 Cron Expression Syntax

```
┌─────────── minute (0-59)
│ ┌─────────── hour (0-23)
│ │ ┌─────────── day of month (1-31)
│ │ │ ┌─────────── month (1-12)
│ │ │ │ ┌─────────── day of week (0-6, Sunday=0)
│ │ │ │ │
* * * * *
```

Examples:
- `*/15 * * * *` — Every 15 minutes
- `0 */6 * * *` — Every 6 hours at :00
- `0 0 * * 1` — Every Monday at midnight
- `0 9 * * 0` — Every Sunday at 9 AM

### 18.4 Cron Authentication

```python
def verify_cron_request(request: Request):
    expected = settings.cron_secret
    if not expected:
        return  # Auth disabled (development)
    
    actual = request.headers.get("X-Cron-Secret")
    if actual != expected:
        raise HTTPException(status_code=403, detail="Invalid cron secret")
```

**Why authenticate cron endpoints?**
Without auth, anyone who discovers the URL can trigger:
- Mass reminder spam to all users
- Unnecessary pattern scans (burns API credits)
- Weekly report generation (CPU-intensive)

Cloud Scheduler sends a custom header (`X-Cron-Secret`) with each request. The endpoint verifies it matches the expected secret.

---

## 19. Security Engineering

### 19.1 Defense in Depth

| Layer | Protection | Implementation |
|-------|-----------|----------------|
| **Network** | HTTPS only | Cloud Run provides automatic TLS |
| **Authentication** | Webhook verification | Telegram token in URL path |
| **Authorization** | Admin checks | `admin_telegram_ids` config |
| **Rate Limiting** | Abuse prevention | Tiered sliding window |
| **Cron Auth** | Endpoint protection | `X-Cron-Secret` header |
| **Secret Management** | Credential storage | GCP Secret Manager |
| **API Docs** | Information hiding | Disabled in production |
| **Error Responses** | Stack trace hiding | Generic 500 messages |

### 19.2 Secrets Management

**Never in code:**
```python
# ❌ NEVER
bot_token = "8197561499:AAEhBUhr..."

# ✅ ALWAYS
bot_token = os.getenv("TELEGRAM_BOT_TOKEN")
```

**Storage hierarchy:**
1. **Secret Manager** (production) → injected as env vars at container start
2. **`.env` file** (development) → loaded by pydantic-settings, git-ignored
3. **`.env.example`** (documentation) → placeholder values, committed to git

### 19.3 .gitignore Security Patterns

```gitignore
# Environment files
.env
.env.*
.env.bak

# Credentials
.credentials/
*.json (except package*.json)
*.pem
*.key

# Backup files (created by tools like sed)
*.bak
*.backup
```

**Real-world incident (Feb 7, 2026):** `sed -i.bak` on `.env` created `.env.bak` containing the bot token. This backup file was not in `.gitignore` and almost got committed. The rule was added after this incident.

### 19.4 Pre-Commit Security Checks

Before every commit, the following should be verified:
1. `git status` — No `.env*`, `.bak`, or credential files in untracked
2. `git diff --cached` — No secrets in staged changes
3. Pattern scan — No tokens matching `\d{10}:[A-Za-z0-9_-]{35}` (Telegram format)

---

## 20. Data Modeling with Pydantic

### 20.1 Why Pydantic?

Pydantic provides **runtime data validation** using Python type hints:

```python
class UserStreaks(BaseModel):
    current_streak: int = Field(default=0, ge=0)  # >= 0 enforced at runtime
    longest_streak: int = Field(default=0, ge=0)
    last_checkin_date: Optional[str] = None
```

If someone tries to create `UserStreaks(current_streak=-1)`, Pydantic raises a `ValidationError`. This catches bugs at the boundary (data entry) instead of deep inside business logic.

### 20.2 Field Validators and Constraints

```python
from pydantic import Field

total: int = 3                    # Simple default
used: int = 0                     # Simple default
current_streak: int = Field(default=0, ge=0)  # Greater than or equal to 0
```

`Field(ge=0)` adds a **constraint** — Pydantic validates this on construction. Other common constraints:
- `gt=0` — greater than 0
- `le=100` — less than or equal to 100
- `min_length=1` — string minimum length
- `max_length=50` — string maximum length
- `regex="^[a-z]+$"` — string must match pattern

### 20.3 Nested Models

```python
class User(BaseModel):
    streaks: UserStreaks = Field(default_factory=UserStreaks)
    reminder_times: ReminderTimes = Field(default_factory=ReminderTimes)
    streak_shields: StreakShields = Field(default_factory=StreakShields)
```

**`default_factory`** creates a new instance for each `User`. Without it, all users would share the SAME `UserStreaks` object (Python mutable default argument trap).

```python
# ❌ WRONG (shared mutable default)
streaks: UserStreaks = UserStreaks()

# ✅ CORRECT (new instance per user)
streaks: UserStreaks = Field(default_factory=UserStreaks)
```

### 20.4 Pydantic Settings for Configuration

```python
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    telegram_bot_token: str  # Required (no default → error if missing)
    gcp_project_id: str = "accountability-agent"  # Optional with default
    
    model_config = SettingsConfigDict(
        env_file=".env",
        case_sensitive=False,  # TELEGRAM_BOT_TOKEN → telegram_bot_token
        extra="ignore"
    )
```

`pydantic-settings` extends Pydantic to load values from environment variables. It:
1. Reads `.env` file (if exists)
2. Maps environment variable names to field names (case-insensitive)
3. Validates types (converts `"True"` string to `bool`, `"8080"` to `int`)
4. Raises clear errors if required fields are missing

---

## 21. Async Programming and Concurrency

### 21.1 Event Loop Model

```python
async def handle_webhook(request):
    body = await request.json()          # I/O wait: reading request body
    update = parse_update(body)           # CPU: parsing JSON
    user = await get_user(update.user_id) # I/O wait: Firestore query
    response = await get_ai_feedback()    # I/O wait: Gemini API call
    await send_message(response)          # I/O wait: Telegram API call
    return {"status": "ok"}
```

When the code hits `await`, the event loop **pauses this coroutine** and runs another one. This is cooperative multitasking:

```
Time:  0ms    50ms    200ms    250ms    500ms    550ms
Task1: [CPU]  await   [CPU]    await    [CPU]    done
Task2:        [CPU]   await    [CPU]    await    done
```

Both tasks complete in ~550ms instead of ~1000ms (sequential), using a **single thread**.

### 21.2 async/await Mechanics

```python
# Coroutine function (returns a coroutine object when called)
async def generate_text(self, prompt: str) -> str:
    response = await self.client.aio.models.generate_content(...)
    return response.text

# Calling a coroutine (must be inside another async function or event loop)
result = await generate_text("classify this intent")
```

**Key rules:**
- `async def` defines a coroutine function
- `await` pauses execution until the awaited operation completes
- You can only `await` inside an `async def` function
- `await` gives the event loop a chance to run other tasks

### 21.3 Sync Functions in Async Context

```python
def _get_user_context(self, user_id: str) -> dict:
    user_profile = firestore_service.get_user(user_id)  # Sync Firestore call
    return {"current_streak": user_profile.streaks.current_streak}
```

Some Firestore operations use the **synchronous** client. In an async application, this blocks the event loop. Solutions:
1. Use the async Firestore client (`google.cloud.firestore_v1.async_client`)
2. Run sync code in a thread pool: `await asyncio.to_thread(sync_function)`
3. Accept the blocking (acceptable for fast queries like single-document reads)

This project uses approach #3 — Firestore reads are fast enough (~10-50ms) that blocking briefly is acceptable for the current scale.

---

## 22. Configuration Management

### 22.1 Configuration Hierarchy

```
1. Environment variables (highest priority)
2. .env file (development convenience)
3. Pydantic defaults (fallback values)
```

This follows the **12-Factor App** methodology: configuration should come from the environment, not from code.

### 22.2 Feature Flags

```python
enable_pattern_detection: bool = True
enable_emotional_processing: bool = False
enable_ghosting_detection: bool = False
enable_reports: bool = False
```

Feature flags allow enabling/disabling features without code changes:
- **Development:** All flags off, enable one at a time for testing
- **Staging:** Enable new features for testing
- **Production:** Gradually enable features (canary deployment)

**Usage in code:**
```python
if settings.enable_pattern_detection:
    patterns = await detect_patterns(user_id)
```

### 22.3 Module-Level Validation

```python
# Run validation when module loads
if __name__ != "__main__":  # Don't run during testing
    validate_configuration()
```

Configuration is validated at import time, not at first use. This means:
- **Fail fast:** Missing config is caught at startup, not 3 AM when a cron job tries to run
- **Clear errors:** `FileNotFoundError("Service account key not found at: ...")` instead of a cryptic Firestore auth error

The `__name__ != "__main__"` check prevents validation during testing (where you might not have a real service account key).

---

## 23. Feature Flags and Backward Compatibility

### 23.1 Schema Evolution Problem

When Phase 3D added `skill_building` as a 6th Tier 1 item, existing check-ins only had 5 items. Re-evaluating old data with the 6-item formula would artificially lower scores:

```
Pre-Phase 3D: 5/5 = 100% ✅
Re-evaluated:  5/6 = 83.3% 😡 (unfair — skill_building didn't exist then!)
```

### 23.2 Era-Based Calculation

```python
def calculate_compliance_score_normalized(tier1, checkin_date=None):
    is_pre_phase3d = checkin_date and checkin_date < settings.phase_3d_deployment_date
    
    if is_pre_phase3d:
        items = [tier1.sleep, tier1.training, tier1.deep_work, tier1.zero_porn, tier1.boundaries]
        total = 5
    else:
        items = [tier1.sleep, tier1.training, tier1.deep_work, tier1.skill_building, tier1.zero_porn, tier1.boundaries]
        total = 6
    
    return (sum(1 for i in items if i) / total) * 100.0
```

**The deployment date acts as a boundary marker.** Data before that date is evaluated with the old rules; data after uses the new rules.

**Important nuance:** The stored `compliance_score` in Firestore is already correct (calculated at check-in time with the right formula). This normalized function is only needed when **re-evaluating raw tier1 booleans** (e.g., in reports that aggregate from raw data).

### 23.3 Pydantic Default Values for New Fields

```python
class Tier1NonNegotiables(BaseModel):
    sleep: bool = False
    training: bool = False
    deep_work: bool = False
    skill_building: bool = False  # NEW in Phase 3D (defaults to False)
    zero_porn: bool = False
    boundaries: bool = False
```

When loading old Firestore documents that don't have `skill_building`, Pydantic's `default=False` ensures the field exists. This prevents `KeyError` without requiring a database migration.

---

## 24. Behavioral Psychology in Software

### 24.1 CBT (Cognitive Behavioral Therapy) Protocol

The Emotional Agent follows a 4-step CBT-inspired protocol:

```
1. VALIDATE   → Acknowledge the emotion (prevents defensiveness)
2. REFRAME    → Connect to long-term goals (provides perspective)
3. TRIGGER    → Ask what caused it (builds self-awareness)
4. ACTION     → Give 3 concrete steps (breaks rumination)
```

**Why this structure works in software:**
- **Validation first** — users who feel judged disengage
- **Reframing** — connects temporary emotion to permanent goals
- **Trigger identification** — builds pattern recognition (meta-skill)
- **Action items** — physical activity interrupts emotional spirals

### 24.2 The "What-the-Hell" Effect

When a streak resets, users experience the **abstinence violation effect** (AVE) — a cognitive distortion where one failure feels like total failure ("I already broke my streak, might as well give up").

The recovery system combats this with:

```python
RECOVERY_FACTS = [
    "Most people who reach 30+ days had at least one reset along the way.",
    "Research shows habit formation averages 66 days — resets are part of the process.",
    "The #1 predictor of long-term success? Restarting after a break.",
]
```

1. **Normalize the reset:** "Resets are part of the process" (reduces shame)
2. **Acknowledge the loss:** "Your previous 47-day streak is YOUR record" (validates effort)
3. **Provide immediate goal:** "7 days → Comeback King" (new target to chase)
4. **Random fact:** Different message each time (prevents habituation)

### 24.3 Streak Milestones and Identity Theory

```python
MILESTONE_MESSAGES = {
    30: "You're in the top 10% of accountability seekers...",
    60: "You don't rely on willpower anymore — it's just what you do.",
    90: "You're operating at a level 98% of people never reach.",
    180: "You're not the same person who started this journey.",
    365: "This isn't just a streak — it's proof of who you are.",
}
```

These messages are designed around **identity-based habit formation** (James Clear, "Atomic Habits"):
- **30 days:** "I'm someone who keeps commitments" (behavioral evidence)
- **60 days:** "This is automatic, not effortful" (habit → identity shift)
- **90 days:** "I'm in the top 2%" (social proof, elite framing)
- **180 days:** "I'm a different person now" (identity transformation)
- **365 days:** "This is who I am" (complete identity integration)

### 24.4 Graduated Intervention Model

```
Severity: WARNING → MEDIUM → HIGH → CRITICAL
Response: Informational → Concerned → Urgent → Emergency + Partner Notification
```

This mirrors clinical intervention models:
1. **Early warning:** "Your sleep has been declining" (awareness)
2. **Active intervention:** "3 consecutive days below target" (urgency)
3. **Crisis response:** "Pattern detected. Here's what to do" (action plan)
4. **Social support:** "Your accountability partner has been notified" (external accountability)

---

## 25. Gamification Systems

### 25.1 Achievement Types

| Category | Examples | Trigger |
|----------|----------|---------|
| **Streak** | Week Warrior (7d), Month Master (30d) | Streak milestones |
| **Performance** | Perfect Day, Full Week 100% | Compliance scores |
| **Special** | Early Bird, Comeback Kid | Specific behaviors |
| **Recovery** | Comeback Kid (3d), King (7d), Legend (14d) | Post-reset milestones |

### 25.2 Streak Shields (Loss Aversion)

```python
class StreakShields(BaseModel):
    total: int = 3
    used: int = 0
    available: int = 3
    last_reset: Optional[str] = None  # Resets every 30 days
```

**Psychology:** Loss aversion means losing a 47-day streak feels much worse than the joy of reaching day 47. Shields mitigate this by allowing occasional misses without losing the streak.

**Game design:**
- Limited supply (3/month) → makes them precious → users avoid using them → increases daily compliance
- Monthly reset → prevents hoarding → ensures engagement each month

### 25.3 Social Proof Integration

When generating AI feedback, the system injects social proof:
- "You've completed 15 achievements — more than 80% of users"
- "Your 47-day streak places you in the top 5%"

This leverages **social comparison theory** — people are motivated by knowing where they stand relative to others.

---

## 26. Data Visualization and Reporting

### 26.1 Matplotlib on a Server

```python
import matplotlib
matplotlib.use('Agg')  # Non-interactive backend — no GUI needed
import matplotlib.pyplot as plt
```

**Why 'Agg' backend?** Cloud Run has no display. The default matplotlib backend tries to open a window, which fails. 'Agg' renders to memory buffers (images), not screens.

### 26.2 Four Graph Types

1. **Sleep Trend:** Line chart of sleep hours over time
2. **Training Consistency:** Bar chart of training days
3. **Compliance Trend:** Line chart with threshold markers
4. **Radar Chart:** Multi-axis comparison of all Tier 1 areas

### 26.3 Image Pipeline

```
Matplotlib → PIL/Pillow → BytesIO → Telegram API
```

1. Matplotlib renders a figure to a numpy array
2. Pillow converts to PNG bytes
3. BytesIO wraps bytes in a file-like object
4. python-telegram-bot sends as a photo message

### 26.4 Docker Font Dependencies

```dockerfile
RUN apt-get install -y fontconfig fonts-dejavu-core libfreetype6
```

Without fonts, matplotlib renders text as empty boxes. The Dockerfile installs:
- **fontconfig:** Font discovery system
- **fonts-dejavu-core:** Default font family
- **libfreetype6:** Font rendering library

---

## 27. Export Systems (CSV, JSON, PDF)

### 27.1 CSV Export

```python
import csv
import io

def export_csv(checkins):
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=['date', 'compliance', 'sleep', ...])
    writer.writeheader()
    for checkin in checkins:
        writer.writerow(checkin.to_dict())
    return output.getvalue()
```

**StringIO** creates an in-memory file-like object. This avoids writing to disk (which is read-only on Cloud Run anyway).

### 27.2 PDF Generation with ReportLab

```python
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Table

def export_pdf(checkins, graphs):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = [
        Paragraph("Weekly Report", title_style),
        Table(data, colWidths=[...]),
        Image(graph_bytes),
    ]
    doc.build(elements)
    return buffer.getvalue()
```

ReportLab builds PDFs programmatically:
- **SimpleDocTemplate:** Handles page layout, margins, page breaks
- **Paragraph:** Styled text with fonts, sizes, colors
- **Table:** Tabular data with borders and formatting
- **Image:** Embeds matplotlib graphs

### 27.3 QR Code Generation

```python
import qrcode

def generate_share_qr(user_id):
    qr = qrcode.make(f"https://t.me/your_bot?start=ref_{user_id}")
    buffer = io.BytesIO()
    qr.save(buffer, format='PNG')
    return buffer.getvalue()
```

QR codes are used for the referral system — users can share their unique referral link as a scannable code.

---

## 28. Social Features Architecture

### 28.1 Leaderboard System

```python
def get_leaderboard():
    users = firestore_service.get_all_users()
    # Filter: only opted-in users
    opted_in = [u for u in users if u.leaderboard_opt_in]
    # Sort by current streak (descending)
    sorted_users = sorted(opted_in, key=lambda u: u.streaks.current_streak, reverse=True)
    return sorted_users[:10]  # Top 10
```

**Privacy considerations:**
- Users must opt-in (`leaderboard_opt_in: bool`)
- Only streak data is shown (not Tier 1 details)
- No real names unless user consents

### 28.2 Referral System

```python
# Deep link format
f"https://t.me/your_bot?start=ref_{referral_code}"
```

Telegram **deep links** allow passing parameters to the `/start` command:
- User clicks link → opens Telegram → sends `/start ref_ABC123` to bot
- Bot parses the parameter → records the referral

### 28.3 Accountability Partners

```
/set_partner @username
    ↓
Bot sends invitation to @username
    ↓
Partner accepts/declines via inline keyboard
    ↓
Both users linked (accountability_partner_id)
```

**Partner features:**
- `/partner_status` shows aggregate stats (not individual Tier 1 items)
- Ghosting alerts notify the partner after 5 days
- Partner unlinking available via `/unlink_partner`

---

## 29. Testing Strategy

### 29.1 Test Architecture

```
tests/
├── conftest.py          # Shared fixtures
├── test_compliance.py   # Unit: compliance calculation
├── test_streak.py       # Unit: streak logic
├── test_fastapi_endpoints.py  # Integration: API endpoints
├── test_checkin_agent.py      # Integration: AI agent
├── test_pattern_intervention.py  # Integration: pattern detection
└── test_phase3f_integration.py   # Integration: Phase 3F features
```

**776+ tests across 28 files** — comprehensive coverage.

### 29.2 Fixture Design

```python
@pytest.fixture
def sample_user():
    return User(
        user_id="123456789",
        telegram_id=123456789,
        name="Test User",
        timezone="Asia/Kolkata",
    )

@pytest.fixture
def sample_checkin():
    return DailyCheckIn(
        user_id="123456789",
        date="2026-02-08",
        compliance_score=100.0,
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=True, training=True, deep_work=True,
            skill_building=True, zero_porn=True, boundaries=True
        ),
    )
```

Fixtures provide **reusable test data**. By defining them in `conftest.py`, any test file can use them without import.

### 29.3 Async Test Support

```toml
# pyproject.toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

`asyncio_mode = "auto"` means pytest-asyncio automatically runs `async def test_*` functions in an event loop. Without this, you'd need the `@pytest.mark.asyncio` decorator on every async test.

### 29.4 Test Markers

```python
@pytest.mark.unit
def test_compliance_score():
    ...

@pytest.mark.integration
async def test_checkin_flow():
    ...
```

Markers allow selective test execution:
```bash
pytest -m unit          # Only unit tests (fast, no external dependencies)
pytest -m integration   # Only integration tests (may need Firestore, etc.)
```

### 29.5 Docker-Specific Tests

```python
# test_docker_phase3f.py - Runs inside the Docker container
def test_matplotlib_available():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3])
    plt.close()

def test_fonts_available():
    from matplotlib import font_manager
    fonts = font_manager.findSystemFonts()
    assert len(fonts) > 0
```

These tests verify that system dependencies (fonts, libraries) are correctly installed in the Docker image. They run as part of the build process:
```bash
docker run --rm accountability-agent:latest python3 test_docker_phase3f.py
```

---

## 30. Cost Optimization

### 30.1 Overall Cost Budget

| Service | Monthly Cost | Optimization |
|---------|-------------|--------------|
| **Cloud Run** | ~$0.15 | Scale-to-zero, CPU throttling |
| **Firestore** | ~$0.10 | Subcollections, efficient queries |
| **Vertex AI** | ~$0.17 | Thinking budget=0, keyword pre-filter |
| **Cloud Scheduler** | ~$0.00 | 4 jobs (free tier: 3 per month, $0.10/month) |
| **Secret Manager** | ~$0.00 | Free tier covers our usage |
| **Total** | ~$0.68/month | |

### 30.2 LLM Cost Reduction Strategies

1. **Thinking budget = 0:** Saves ~40% on token costs by disabling reasoning tokens.
2. **Keyword pre-filter:** Skip LLM for obvious intents (query keywords).
3. **Minimal prompts:** Keep prompts short (~200 tokens) with clear constraints.
4. **One-word responses:** For classification, request exactly one word (1 output token).
5. **Quick check-in skips AI:** The abbreviated flow doesn't generate AI feedback.

### 30.3 Firestore Cost Reduction

1. **Subcollections:** Only read one user's check-ins (not a global scan).
2. **Date-range queries:** Limit to last N days (not full history).
3. **Transactions:** Reduce number of writes by batching related operations.
4. **Caching user profiles:** Supervisor reads user context once per message.

### 30.4 Cloud Run Cost Reduction

1. **Scale-to-zero:** No charge when idle.
2. **CPU throttling:** No charge for CPU between requests.
3. **Single worker:** Minimizes memory usage.
4. **Max instances = 3:** Cost cap even under load.

---

## 31. Error Handling and Graceful Degradation

### 31.1 Fallback Hierarchy

Each agent has a fallback strategy:

| Agent | Primary | Fallback |
|-------|---------|----------|
| **Supervisor** | Gemini classification | Default to "query" |
| **CheckIn Agent** | AI feedback via Gemini | Hardcoded template feedback |
| **Intervention** | AI-generated warning | Template-based warning |
| **Reporting** | Full report with graphs | Partial report (text only) |
| **Emotional** | CBT-style AI response | Generic support message |

### 31.2 Graceful Degradation Philosophy

```python
try:
    # Expensive: AI-generated personalized feedback
    feedback = await llm_service.generate_text(prompt)
except Exception as e:
    # Cheap: Template-based feedback
    feedback = format_compliance_message(score, streak)
    logger.error(f"AI feedback failed, using template: {e}")
```

The system always provides **some** response, even if the best response isn't available. This is better than showing an error because:
- Users don't see technical failures
- The core function (check-in recording) still works
- Feedback quality degrades gracefully, not catastrophically

### 31.3 Webhook Resilience

```python
@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    try:
        body = await request.json()
        await bot_manager.application.process_update(update)
    except Exception as e:
        logger.error(f"Webhook error: {e}")
    return {"status": "ok"}  # ALWAYS 200
```

**Always return 200 to Telegram.** If you return 500, Telegram retries the update, potentially causing:
- Duplicate message processing
- Infinite retry loops
- Rate limiting from Telegram

---

## 32. Git Workflow and Security Hygiene

### 32.1 Safe Commit Process

```bash
# 1. Check what's changed
git status
git diff --cached

# 2. Scan for secrets
git diff --cached | grep -E "(token|secret|password|api_key)"

# 3. Stage specific files (NEVER git add .)
git add src/ tests/ requirements.txt

# 4. Verify staging area
git diff --cached --name-only

# 5. Commit
git commit -m "descriptive message"
```

### 32.2 The Feb 7 Incident

**What happened:**
1. `sed -i.bak` was used to modify `.env`
2. This created `.env.bak` (containing the bot token)
3. `.env.bak` was not in `.gitignore`
4. It appeared as an untracked file
5. Caught before `git add` — crisis averted

**Mitigation added:**
- `.gitignore` updated with `*.bak` pattern
- Cursor rules created to enforce pre-commit checks
- macOS `sed -i ''` (no backup) used instead of `sed -i.bak`

### 32.3 Documentation Security

```markdown
❌ NEVER:
curl https://api.telegram.org/bot8197561499:AAE.../getMe

✅ ALWAYS:
curl https://api.telegram.org/bot${TELEGRAM_BOT_TOKEN}/getMe
```

Every curl command, code example, and configuration snippet in documentation must use placeholders. Real secrets should never appear in committed files.

---

## 33. Phase-by-Phase Architecture Evolution

### Phase 1: Foundation (MVP)
```
Telegram → Webhook → FastAPI → Bot Handler → Conversation → Firestore
```
**Key decisions:** Webhook over polling, Firestore over SQL, ConversationHandler for state machine.

### Phase 2: Intelligence (AI + Patterns)
```
+ Supervisor Agent (intent classification)
+ CheckIn Agent (AI feedback)
+ Pattern Detection (sliding windows)
+ Intervention Agent (warnings)
+ LLM Service (Gemini integration)
```
**Key decisions:** Multi-agent architecture, zero-shot classification, threshold-based detection.

### Phase 3A-3F: Features
```
+ 3A: Multi-user, reminders, streak shields
+ 3B: Emotional support (CBT), accountability partners
+ 3C: Achievements, milestones, social proof
+ 3D: Career modes, skill building (6th Tier 1 item)
+ 3E: Quick check-in, query agent, stats commands
+ 3F: Export (CSV/JSON/PDF), visualization, reports, social
```
**Key decisions:** Backward compatibility for schema changes, partial check-in recovery, graduated intervention model.

### Phases A-D: Operations & Enhancements
```
+ Phase A: Metrics, rate limiting, JSON logging
+ Phase B: Multi-timezone support (IANA)
+ Phase C: Partner mutual visibility
+ Phase D: Streak recovery, intervention-support linking
```
**Key decisions:** In-memory metrics (vs external store), sliding window rate limiting, backward-compatible timezone refactoring.

---

## Appendix A: Key Interview Questions

### System Design
1. **"Design a chatbot that scales to 10,000 users."** → Discuss webhook vs polling, Cloud Run auto-scaling, Firestore sharding, rate limiting.
2. **"How would you add real-time notifications?"** → Cloud Scheduler cron vs PubSub, timezone-aware bucketing.
3. **"How would you migrate from Firestore to PostgreSQL?"** → Service layer abstraction, one file to change.

### Algorithms
4. **"Implement a sliding window rate limiter."** → Explain timestamp list, pruning, cooldown check.
5. **"Detect patterns in time-series data."** → Sliding windows, threshold rules, severity levels.

### Architecture
6. **"When would you use a multi-agent system vs monolithic handler?"** → Separation of concerns, independent testing, cost control.
7. **"How do you handle backward compatibility when schema evolves?"** → Era-based calculation, Pydantic defaults, deployment dates.

### Production Engineering
8. **"How do you prevent secrets from being committed?"** → .gitignore, pre-commit checks, Secret Manager.
9. **"Explain your observability strategy."** → Logs (structured JSON), metrics (counters + latencies + percentiles), health checks.
10. **"How do you optimize LLM costs?"** → Thinking budget=0, keyword pre-filter, minimal prompts, one-word responses.

---

## Appendix B: Technology Stack Summary

| Category | Technology | Version | Purpose |
|----------|-----------|---------|---------|
| Language | Python | 3.11 | Core language |
| Web Framework | FastAPI | 0.109.0 | ASGI web server |
| ASGI Server | Uvicorn | 0.27.0 | Production server |
| Bot Framework | python-telegram-bot | 21.0 | Telegram API |
| Database | Google Cloud Firestore | 2.14.0 | NoSQL document DB |
| LLM | Google GenAI SDK (Gemini 2.5 Flash) | >=1.61.0 | AI text generation |
| Secrets | Google Cloud Secret Manager | 2.17.0 | Credential storage |
| Data Validation | Pydantic | >=2.10.0 | Type-safe models |
| Config | pydantic-settings | >=2.7.0 | Environment loading |
| Timezone | pytz | 2024.1 | Timezone handling |
| Visualization | matplotlib | >=3.8.0 | Charts/graphs |
| Image Processing | Pillow | >=10.0.0 | Image manipulation |
| PDF Generation | ReportLab | >=4.0 | PDF export |
| QR Codes | qrcode | >=7.4 | Referral links |
| Testing | pytest | 8.0.0 | Test framework |
| Async Testing | pytest-asyncio | 0.23.0 | Async test support |
| Coverage | pytest-cov | 4.1.0 | Code coverage |
| HTTP Client | httpx | >=0.28.1 | HTTP requests |
| Containerization | Docker | python:3.11-slim | Container image |
| Compute | Google Cloud Run | — | Serverless hosting |
| Scheduling | Google Cloud Scheduler | — | Cron jobs |

---

## Appendix C: File Map

```
src/
├── main.py                    # FastAPI app, webhook, cron endpoints
├── config.py                  # Pydantic Settings, env configuration
├── bot/
│   ├── telegram_bot.py        # Bot manager, command handlers, inline keyboards
│   ├── conversation.py        # Check-in state machine (ConversationHandler)
│   └── stats_commands.py      # /weekly, /monthly, /yearly commands
├── agents/
│   ├── state.py               # LangGraph ConstitutionState (TypedDict)
│   ├── supervisor.py          # Intent classification (Supervisor Agent)
│   ├── checkin_agent.py       # AI feedback generation (CheckIn Agent)
│   ├── pattern_detection.py   # 9 pattern rules (sliding windows)
│   ├── intervention.py        # Warning message generation
│   ├── emotional_agent.py     # CBT-style emotional support
│   ├── query_agent.py         # Natural language data queries
│   └── reporting_agent.py     # Weekly report orchestration (Mediator)
├── services/
│   ├── firestore_service.py   # All database operations (Service Layer)
│   ├── llm_service.py         # Vertex AI Gemini wrapper (Singleton)
│   ├── constitution_service.py # Constitution document loading
│   ├── analytics_service.py   # Stats aggregation (weekly/monthly/yearly)
│   ├── achievement_service.py # Gamification (15+ achievements)
│   ├── visualization_service.py # Matplotlib chart generation
│   ├── export_service.py      # CSV, JSON, PDF export
│   └── social_service.py      # Leaderboard, referrals, sharing
├── models/
│   └── schemas.py             # Pydantic models (User, CheckIn, Tier1, etc.)
└── utils/
    ├── compliance.py          # Pure functions: compliance score calculation
    ├── streak.py              # Pure functions: streak logic, recovery
    ├── timezone_utils.py      # Timezone handling (multi-tz support)
    ├── rate_limiter.py        # Tiered sliding window rate limiter
    ├── metrics.py             # In-memory metrics collector
    └── ux.py                  # Message formatting, error messages
```

---

*Generated: February 18, 2026*
*Project: Constitution Accountability Agent*
*Phases Covered: 1, 2, 3A, 3B, 3C, 3D, 3E, 3F, A, B, C, D*
*Total Tests: 776+ across 28 files*
*Total Endpoints: 12*
*Total Agents: 7*
*Monthly Cost: ~$0.68*
