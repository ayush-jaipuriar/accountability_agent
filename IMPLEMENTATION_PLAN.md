# Phase 1 MVP - Detailed Implementation Plan

## Overview

We're building a **Telegram bot-based check-in system** that:
1. Asks you 4 questions daily at 9 PM IST
2. Stores your responses in Firestore
3. Calculates compliance score (% of Tier 1 non-negotiables completed)
4. Tracks your streak (consecutive check-in days)
5. Provides immediate feedback

**Architecture Flow:**
```
User → Telegram App → Telegram Servers → Webhook → FastAPI (Cloud Run)
                                                          ↓
                                                    Bot Handler
                                                          ↓
                                              Conversation State Machine
                                                          ↓
                                              Firestore (store data)
                                                          ↓
                                              Calculate Score + Streak
                                                          ↓
                                              Send Feedback → User
```

---

## File Structure We'll Create

```
accountability_agent/
├── .credentials/
│   └── accountability-agent-9256adc55379.json  # ✅ Already exists
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point, webhook handler
│   ├── config.py                  # Configuration from environment variables
│   │
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── telegram_bot.py        # Bot initialization
│   │   ├── handlers.py            # Command handlers (/start, /checkin, /help)
│   │   └── conversation.py        # Check-in conversation flow (state machine)
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── firestore_service.py   # Database operations (CRUD)
│   │   └── constitution_service.py # Load constitution.md for context
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic data models (User, CheckIn)
│   │
│   └── utils/
│       ├── __init__.py
│       ├── compliance.py          # Compliance score calculation
│       ├── streak.py              # Streak tracking logic
│       └── timezone_utils.py      # IST timezone handling
│
├── tests/
│   ├── __init__.py
│   ├── test_compliance.py         # Unit tests for scoring
│   ├── test_streak.py             # Unit tests for streak logic
│   └── conftest.py                # Pytest fixtures
│
├── constitution.md                # ✅ Already exists
├── gcp-setup.md                   # ✅ Already exists
├── .env                           # Create from .env.example
├── .env.example                   # ✅ Already exists
├── .gitignore                     # ✅ Already exists
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container image definition
└── README.md                      # Project documentation
```

---

## Component Breakdown

### 1. Configuration (`src/config.py`)

**What:** Centralized configuration management using environment variables.

**Why:** Keeps secrets out of code, makes it easy to switch between development and production.

**Key Concepts:**
- **Environment Variables:** Configuration stored outside code (in `.env` file locally, Cloud Run environment in production)
- **Pydantic Settings:** Type-safe configuration with validation

**Structure:**
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # GCP
    gcp_project_id: str = "accountability-agent"
    google_application_credentials: str = ".credentials/..."
    gcp_region: str = "asia-south1"
    
    # Telegram
    telegram_bot_token: str  # Required, no default
    
    # Application
    environment: str = "development"
    webhook_url: str = ""  # Set in production
    
    class Config:
        env_file = ".env"
        case_sensitive = False

settings = Settings()
```

**What You'll Learn:**
- Environment-based configuration
- Secrets management
- Settings validation

---

### 2. Data Models (`src/models/schemas.py`)

**What:** Define the structure of data we'll store in Firestore using Pydantic models.

**Why:** Type safety, automatic validation, clear data contracts.

**Key Concepts:**
- **Pydantic Models:** Python classes that validate data automatically
- **Type Hints:** Python's way of specifying data types (`str`, `int`, `bool`, `datetime`)
- **Data Validation:** Automatic checking that data matches expected format

**Models We'll Create:**

#### User Model
```python
from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class UserStreaks(BaseModel):
    current_streak: int = 0
    longest_streak: int = 0
    last_checkin_date: Optional[str] = None
    total_checkins: int = 0

class User(BaseModel):
    user_id: str
    telegram_id: int
    telegram_username: Optional[str] = None
    name: str
    timezone: str = "Asia/Kolkata"
    streaks: UserStreaks = UserStreaks()
    constitution_mode: str = "maintenance"  # optimization/maintenance/survival
    created_at: datetime
    updated_at: datetime
```

#### Check-In Model
```python
class Tier1NonNegotiables(BaseModel):
    sleep: bool
    sleep_hours: Optional[float] = None
    training: bool
    is_rest_day: bool = False
    deep_work: bool
    deep_work_hours: Optional[float] = None
    zero_porn: bool
    boundaries: bool

class CheckInResponses(BaseModel):
    challenges: str
    rating: int  # 1-10
    rating_reason: str
    tomorrow_priority: str
    tomorrow_obstacle: str

class DailyCheckIn(BaseModel):
    date: str  # YYYY-MM-DD format
    user_id: str
    mode: str
    tier1_non_negotiables: Tier1NonNegotiables
    responses: CheckInResponses
    compliance_score: float  # 0-100
    completed_at: datetime
    duration_seconds: int
```

**What You'll Learn:**
- Data modeling
- Type safety in Python
- Nested data structures

---

### 3. Firestore Service (`src/services/firestore_service.py`)

**What:** All database operations centralized in one service layer.

**Why:** 
- **Separation of Concerns:** Database logic separate from business logic
- **Reusability:** Use these functions anywhere in the app
- **Easier Testing:** Can mock database calls

**Key Concepts:**
- **Service Layer Pattern:** Business logic separated from data access
- **Firestore NoSQL:** Document-based database (documents organized in collections)
- **CRUD Operations:** Create, Read, Update, Delete

**Functions We'll Implement:**

```python
class FirestoreService:
    def __init__(self):
        self.db = firestore.Client()
    
    # User operations
    def create_user(self, user: User) -> None:
        """Create new user document in Firestore"""
        
    def get_user(self, user_id: str) -> Optional[User]:
        """Fetch user by ID"""
        
    def update_user_streak(self, user_id: str, streak_data: dict) -> None:
        """Update user's streak information"""
    
    # Check-in operations
    def store_checkin(self, user_id: str, checkin: DailyCheckIn) -> None:
        """Store completed check-in"""
        
    def get_checkin(self, user_id: str, date: str) -> Optional[DailyCheckIn]:
        """Get check-in for specific date"""
        
    def get_recent_checkins(self, user_id: str, days: int = 7) -> list[DailyCheckIn]:
        """Fetch recent check-ins for pattern detection"""
        
    def checkin_exists(self, user_id: str, date: str) -> bool:
        """Check if user already completed check-in today"""
```

**Firestore Structure:**
```
users/
  {user_id}/  # Document
    - telegram_id: 123456789
    - name: "Ayush"
    - streaks: {...}
    - ...

daily_checkins/
  {user_id}/  # Document (container)
    checkins/  # Subcollection
      {date}/  # Document (e.g., "2026-01-30")
        - tier1_non_negotiables: {...}
        - responses: {...}
        - compliance_score: 100.0
        - ...
```

**What You'll Learn:**
- NoSQL database concepts
- Firestore document model
- Service layer architecture

---

### 4. Constitution Service (`src/services/constitution_service.py`)

**What:** Loads your constitution.md file and provides it as context for AI prompts (Phase 2).

**Why:** Makes your constitution accessible to all agents for personalized feedback.

**Key Concepts:**
- **Context Loading:** Reading file content at startup
- **Singleton Pattern:** Load once, use everywhere
- **Future-Proofing:** Ready for Phase 2 AI integration

**Structure:**
```python
class ConstitutionService:
    def __init__(self):
        self._constitution_text = self._load_constitution()
    
    def _load_constitution(self) -> str:
        """Load constitution.md from file"""
        with open("constitution.md", "r") as f:
            return f.read()
    
    def get_constitution_context(self, user_id: str) -> str:
        """Get constitution text for AI prompts (Phase 2)"""
        return self._constitution_text
    
    def get_tier1_rules(self) -> dict:
        """Extract Tier 1 non-negotiables for validation"""
        return {
            "sleep": {"target": 7.0, "unit": "hours"},
            "training": {"frequency": "6x/week in optimization, 3-4x in maintenance"},
            "deep_work": {"target": 2.0, "unit": "hours"},
            "zero_porn": {"rule": "absolute"},
            "boundaries": {"rule": "no toxic sacrifices"}
        }

constitution_service = ConstitutionService()
```

**What You'll Learn:**
- File I/O in Python
- Singleton pattern
- Preparing for AI integration

---

### 5. Compliance Calculator (`src/utils/compliance.py`)

**What:** Calculate your daily compliance score (percentage of Tier 1 items completed).

**Why:** Objective measurement of constitution adherence.

**Key Concepts:**
- **Pure Functions:** Input → Output, no side effects
- **Business Logic:** The "rules" of your constitution
- **Percentage Calculation:** Simple but important

**Implementation:**
```python
def calculate_compliance_score(tier1: Tier1NonNegotiables) -> float:
    """
    Calculate compliance score as percentage of Tier 1 items completed.
    
    Formula: (completed_items / total_items) * 100
    
    Args:
        tier1: Tier 1 non-negotiables responses
        
    Returns:
        float: Score from 0.0 to 100.0
        
    Example:
        tier1 = Tier1NonNegotiables(
            sleep=True, training=True, deep_work=False, 
            zero_porn=True, boundaries=True
        )
        score = calculate_compliance_score(tier1)  # 80.0 (4/5 * 100)
    """
    items = [
        tier1.sleep,
        tier1.training,
        tier1.deep_work,
        tier1.zero_porn,
        tier1.boundaries
    ]
    
    completed = sum(1 for item in items if item)
    total = len(items)
    
    return (completed / total) * 100.0


def get_compliance_level(score: float) -> str:
    """
    Categorize compliance score into levels.
    
    Levels (from your constitution):
    - Excellent: 90-100%
    - Good: 80-89%
    - Warning: 60-79%
    - Critical: <60%
    """
    if score >= 90:
        return "excellent"
    elif score >= 80:
        return "good"
    elif score >= 60:
        return "warning"
    else:
        return "critical"
```

**What You'll Learn:**
- Pure functions
- Unit testing (easy to test this!)
- Business logic separation

---

### 6. Streak Tracker (`src/utils/streak.py`)

**What:** Track consecutive days of check-ins, reset if gap >48 hours.

**Why:** Streaks are powerful psychological motivators (and you want to see that number grow!).

**Key Concepts:**
- **Date Arithmetic:** Calculate days between dates
- **Business Rules:** When to increment vs reset
- **Timezone Awareness:** Always work in IST

**Implementation:**
```python
from datetime import datetime, timedelta
from typing import Optional

def should_increment_streak(last_checkin_date: str, current_date: str) -> bool:
    """
    Determine if streak should increment.
    
    Rules (from your constitution):
    - If last check-in was yesterday → increment
    - If gap is 2+ days (>48 hours) → reset
    - If same day → no change (shouldn't happen but handle it)
    
    Args:
        last_checkin_date: Last check-in date in "YYYY-MM-DD" format
        current_date: Current check-in date in "YYYY-MM-DD" format
        
    Returns:
        bool: True if should increment, False if should reset
    """
    last_date = datetime.strptime(last_checkin_date, "%Y-%m-%d")
    curr_date = datetime.strptime(current_date, "%Y-%m-%d")
    
    days_diff = (curr_date - last_date).days
    
    if days_diff == 0:
        # Same day check-in (shouldn't happen)
        return False
    elif days_diff == 1:
        # Yesterday → increment
        return True
    else:
        # Gap >48 hours → reset
        return False


def calculate_new_streak(
    current_streak: int,
    last_checkin_date: Optional[str],
    new_checkin_date: str
) -> int:
    """
    Calculate new streak value after check-in.
    
    Args:
        current_streak: Current streak count
        last_checkin_date: Last check-in date or None (first check-in)
        new_checkin_date: Today's check-in date
        
    Returns:
        int: New streak value (incremented or reset to 1)
    """
    if last_checkin_date is None:
        # First ever check-in
        return 1
    
    if should_increment_streak(last_checkin_date, new_checkin_date):
        return current_streak + 1
    else:
        # Reset streak
        return 1


def update_streak_data(user: User, checkin_date: str) -> dict:
    """
    Calculate all streak updates after a check-in.
    
    Returns dict with:
    - current_streak: New streak value
    - longest_streak: Updated if current exceeds longest
    - last_checkin_date: Today's date
    - total_checkins: Incremented by 1
    """
    new_streak = calculate_new_streak(
        user.streaks.current_streak,
        user.streaks.last_checkin_date,
        checkin_date
    )
    
    new_longest = max(new_streak, user.streaks.longest_streak)
    
    return {
        "current_streak": new_streak,
        "longest_streak": new_longest,
        "last_checkin_date": checkin_date,
        "total_checkins": user.streaks.total_checkins + 1
    }
```

**What You'll Learn:**
- Date/time handling in Python
- Business rule implementation
- Edge case handling

---

### 7. Telegram Bot Handler (`src/bot/telegram_bot.py`)

**What:** Initialize the Telegram bot and register command handlers.

**Why:** This is how your bot comes alive - it listens for messages and responds.

**Key Concepts:**
- **Bot API:** Telegram's interface for bots
- **Webhooks vs Polling:** Webhooks are event-driven (Telegram pushes to us)
- **Command Handlers:** Functions that respond to /start, /checkin, etc.

**Structure:**
```python
from telegram import Update, Bot
from telegram.ext import Application, CommandHandler, ConversationHandler

class TelegramBotManager:
    def __init__(self, token: str):
        self.token = token
        self.application = Application.builder().token(token).build()
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Register all command handlers"""
        
        # Simple commands
        self.application.add_handler(CommandHandler("start", self.start_command))
        self.application.add_handler(CommandHandler("help", self.help_command))
        self.application.add_handler(CommandHandler("status", self.status_command))
        
        # Check-in conversation handler (state machine)
        from src.bot.conversation import create_checkin_conversation_handler
        checkin_handler = create_checkin_conversation_handler()
        self.application.add_handler(checkin_handler)
    
    async def start_command(self, update: Update, context):
        """Handle /start command"""
        user = update.effective_user
        
        # Create user in Firestore if doesn't exist
        # Send welcome message
        
    async def status_command(self, update: Update, context):
        """Handle /status command - show streak and compliance"""
        user_id = str(update.effective_user.id)
        user = firestore_service.get_user(user_id)
        
        # Format and send status message
```

**What You'll Learn:**
- Telegram Bot API
- Async Python (await, async functions)
- Command routing

---

### 8. Check-In Conversation (`src/bot/conversation.py`)

**What:** The core check-in flow - asks 4 questions, validates responses, stores data.

**Why:** This is THE MAIN FEATURE of Phase 1 - your daily accountability.

**Key Concepts:**
- **State Machine:** Conversation has states (Q1, Q2, Q3, Q4, END)
- **ConversationHandler:** Telegram's built-in state machine
- **State Persistence:** Remember where user is in conversation
- **Input Validation:** Check that responses are valid

**State Flow:**
```
START
  ↓
  /checkin command received
  ↓
Q1_TIER1 (Ask Tier 1 non-negotiables with Y/N buttons)
  ↓
  User responds with Y/N for each item
  ↓
Q2_CHALLENGES (Ask about challenges)
  ↓
  User types free text (validated: 10-500 chars)
  ↓
Q3_RATING (Ask for 1-10 rating + reason)
  ↓
  User types "8 - solid day overall"
  ↓
Q4_TOMORROW (Ask about tomorrow's priority)
  ↓
  User types priority + obstacle
  ↓
FINISH
  ↓
  - Calculate compliance score
  - Update streak
  - Store in Firestore
  - Send feedback
  ↓
END
```

**Implementation Structure:**
```python
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

# States
Q1_TIER1, Q2_CHALLENGES, Q3_RATING, Q4_TOMORROW = range(4)

async def start_checkin(update: Update, context):
    """Entry point - /checkin command"""
    user_id = str(update.effective_user.id)
    
    # Check if already checked in today
    today = get_current_date_ist()
    if firestore_service.checkin_exists(user_id, today):
        await update.message.reply_text(
            "You've already completed today's check-in! ✅\n"
            f"Current streak: {user.streaks.current_streak} days"
        )
        return ConversationHandler.END
    
    # Initialize conversation data
    context.user_data['checkin_start_time'] = datetime.now()
    context.user_data['user_id'] = user_id
    
    # Ask Question 1 with inline keyboard
    keyboard = [
        [InlineKeyboardButton("✅ Sleep (7+ hrs)", callback_data="sleep_yes"),
         InlineKeyboardButton("❌ No", callback_data="sleep_no")],
        [InlineKeyboardButton("✅ Training", callback_data="training_yes"),
         InlineKeyboardButton("❌ No", callback_data="training_no")],
        # ... more buttons
    ]
    
    await update.message.reply_text(
        "Time for your daily check-in! 📋\n\n"
        "**Question 1/4: Constitution Compliance**\n"
        "Did you complete your Tier 1 non-negotiables?\n\n"
        "• Sleep: 7+ hours last night?\n"
        "• Training: Workout OR rest day?\n"
        "• Deep Work: 2+ hours focused work/study?\n"
        "• Zero Porn: No consumption today?\n"
        "• Boundaries: No toxic interactions?",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )
    
    return Q1_TIER1


async def handle_tier1_response(update: Update, context):
    """Handle button presses for Tier 1 responses"""
    query = update.callback_query
    await query.answer()
    
    # Parse button data (e.g., "sleep_yes" → sleep: True)
    # Store in context.user_data
    # When all 5 answered, move to Q2
    
    if all_tier1_answered(context.user_data):
        await query.message.reply_text(
            "**Question 2/4: Challenges**\n"
            "What challenges did you face today? "
            "How did you handle them?\n\n"
            "(Type your response, 10-500 characters)"
        )
        return Q2_CHALLENGES
    
    return Q1_TIER1


async def handle_challenges_response(update: Update, context):
    """Handle Question 2 - challenges"""
    text = update.message.text
    
    # Validate length
    if len(text) < 10:
        await update.message.reply_text(
            "Please provide more detail (minimum 10 characters)"
        )
        return Q2_CHALLENGES
    
    context.user_data['challenges'] = text
    
    await update.message.reply_text(
        "**Question 3/4: Self-Rating**\n"
        "Rate today 1-10 on constitution alignment. "
        "Why that score?\n\n"
        "(Example: '8 - solid day, missed one study hour')"
    )
    
    return Q3_RATING


async def handle_rating_response(update: Update, context):
    """Handle Question 3 - rating"""
    text = update.message.text
    
    # Parse rating (first number 1-10) and reason
    # Validation logic
    
    await update.message.reply_text(
        "**Question 4/4: Tomorrow's Plan**\n"
        "What's tomorrow's #1 priority and biggest potential obstacle?\n\n"
        "(Example: 'Priority: LeetCode. Obstacle: late meeting')"
    )
    
    return Q4_TOMORROW


async def finish_checkin(update: Update, context):
    """Complete check-in - calculate, store, feedback"""
    # Collect all data from context.user_data
    # Create CheckIn object
    # Calculate compliance score
    # Update streak
    # Store in Firestore
    # Generate feedback message
    
    checkin = DailyCheckIn(...)
    score = calculate_compliance_score(checkin.tier1_non_negotiables)
    
    # Update streak
    user = firestore_service.get_user(user_id)
    streak_data = update_streak_data(user, today)
    
    # Store everything
    firestore_service.store_checkin(user_id, checkin)
    firestore_service.update_user_streak(user_id, streak_data)
    
    # Send feedback (hardcoded for Phase 1, AI in Phase 2)
    feedback = generate_feedback(checkin, streak_data)
    await update.message.reply_text(feedback)
    
    return ConversationHandler.END


def create_checkin_conversation_handler():
    """Create and configure the conversation handler"""
    return ConversationHandler(
        entry_points=[CommandHandler("checkin", start_checkin)],
        states={
            Q1_TIER1: [CallbackQueryHandler(handle_tier1_response)],
            Q2_CHALLENGES: [MessageHandler(filters.TEXT, handle_challenges_response)],
            Q3_RATING: [MessageHandler(filters.TEXT, handle_rating_response)],
            Q4_TOMORROW: [MessageHandler(filters.TEXT, finish_checkin)]
        },
        fallbacks=[CommandHandler("cancel", cancel_checkin)],
        conversation_timeout=900  # 15 minutes
    )
```

**What You'll Learn:**
- State machines
- Conversation design
- Input validation
- Telegram inline keyboards
- Async flow control

---

### 9. FastAPI Application (`src/main.py`)

**What:** The web server that receives Telegram webhook calls.

**Why:** Telegram needs an HTTP endpoint to send updates to.

**Key Concepts:**
- **FastAPI:** Modern Python web framework
- **Webhooks:** Event-driven communication (Telegram → your server)
- **Async Handlers:** Non-blocking I/O for better performance
- **Health Checks:** Cloud Run pings this to verify app is running

**Implementation:**
```python
from fastapi import FastAPI, Request, HTTPException
from src.bot.telegram_bot import TelegramBotManager
from src.config import settings
import logging

# Initialize FastAPI
app = FastAPI(
    title="Constitution Accountability Agent",
    description="AI-powered accountability system",
    version="1.0.0"
)

# Initialize bot
bot_manager = TelegramBotManager(settings.telegram_bot_token)

@app.post("/webhook/telegram")
async def telegram_webhook(request: Request):
    """
    Receive updates from Telegram.
    
    Telegram sends POST requests here whenever:
    - User sends a message to bot
    - User presses inline button
    - User sends a command
    
    Flow:
    1. Telegram servers → POST to this endpoint
    2. We parse the update
    3. Pass to bot application for processing
    4. Bot sends response back to user
    """
    try:
        # Get update data from request
        update_data = await request.json()
        
        # Process with bot
        from telegram import Update
        update = Update.de_json(update_data, bot_manager.application.bot)
        await bot_manager.application.process_update(update)
        
        return {"ok": True}
        
    except Exception as e:
        logging.error(f"Error processing webhook: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    
    Cloud Run pings this to verify app is running.
    Returns 200 OK if healthy.
    """
    return {
        "status": "healthy",
        "service": "constitution-agent",
        "version": "1.0.0"
    }


@app.on_event("startup")
async def startup_event():
    """
    Run once when app starts.
    
    Tasks:
    1. Initialize bot
    2. Set webhook URL (tell Telegram where to send updates)
    3. Load constitution
    """
    logging.info("Starting Constitution Agent...")
    
    # Set webhook if in production
    if settings.environment == "production" and settings.webhook_url:
        webhook_url = f"{settings.webhook_url}/webhook/telegram"
        await bot_manager.application.bot.set_webhook(webhook_url)
        logging.info(f"Webhook set to: {webhook_url}")
    else:
        logging.info("Development mode - no webhook set")
    
    logging.info("Constitution Agent started successfully!")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup when app shuts down"""
    logging.info("Shutting down Constitution Agent...")
```

**What You'll Learn:**
- Web API development
- Webhook handling
- FastAPI framework
- Async web applications

---

### 10. Requirements File (`requirements.txt`)

**What:** List of Python packages we need to install.

**Why:** Dependency management - ensures everyone has same versions.

```txt
# Web Framework
fastapi==0.109.0
uvicorn[standard]==0.27.0

# Telegram Bot
python-telegram-bot==21.0

# Google Cloud
google-cloud-firestore==2.14.0
google-cloud-aiplatform==1.42.0  # For Phase 2 (Vertex AI)

# LangChain/LangGraph (Phase 2)
langchain==0.1.0
langgraph==0.0.40

# Data Validation
pydantic==2.5.0
pydantic-settings==2.1.0

# Utilities
python-dotenv==1.0.0
httpx==0.26.0
pytz==2024.1  # Timezone handling

# Testing
pytest==8.0.0
pytest-asyncio==0.23.0
pytest-cov==4.1.0

# Development
black==24.1.0  # Code formatter
ruff==0.1.0    # Linter
```

---

### 11. Dockerfile

**What:** Instructions to build a container image of your app.

**Why:** Containers package code + dependencies together, making deployment easy.

**Key Concepts:**
- **Docker:** Platform for containerization
- **Images:** Template for containers
- **Layers:** Each instruction creates a layer (cached for faster rebuilds)
- **Multi-stage builds:** Separate build and runtime environments

```dockerfile
# Use official Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies (if needed)
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first (for layer caching)
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Expose port 8000
EXPOSE 8000

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PORT=8000

# Run FastAPI with uvicorn
CMD exec uvicorn src.main:app --host 0.0.0.0 --port ${PORT}
```

**What You'll Learn:**
- Docker basics
- Container images
- Layer caching optimization
- Production deployments

---

## Implementation Sequence

We'll build in this order (logical dependencies):

### Step 1: Foundation (30 min)
1. Create project structure (folders and `__init__.py` files)
2. `requirements.txt` → install dependencies
3. `src/config.py` → configuration management
4. `.env` → copy from `.env.example`, fill in bot token

### Step 2: Data Layer (45 min)
1. `src/models/schemas.py` → Pydantic models
2. `src/services/firestore_service.py` → database operations
3. `src/services/constitution_service.py` → load constitution.md
4. Test Firestore connection

### Step 3: Business Logic (30 min)
1. `src/utils/compliance.py` → score calculation
2. `src/utils/streak.py` → streak tracking
3. `src/utils/timezone_utils.py` → IST handling
4. Write unit tests

### Step 4: Bot Handlers (2 hours)
1. `src/bot/telegram_bot.py` → bot initialization
2. `src/bot/handlers.py` → simple commands (/start, /help, /status)
3. `src/bot/conversation.py` → check-in state machine (MOST COMPLEX)
4. Test locally with polling (before webhook)

### Step 5: Web Application (30 min)
1. `src/main.py` → FastAPI app with webhook endpoint
2. Test locally

### Step 6: Deployment (1 hour)
1. `Dockerfile` → containerization
2. Build image
3. Deploy to Cloud Run
4. Set webhook
5. Test end-to-end with real bot

### Step 7: Testing & Polish (1 hour)
1. Complete check-in flow multiple times
2. Test streak logic (check in consecutive days)
3. Test edge cases (same day, gap >48hrs)
4. Verify Firestore data
5. Fix any bugs
6. Document setup in README

---

## Testing Strategy

### Unit Tests (Fast, Isolated)
```python
# tests/test_compliance.py
def test_compliance_score_all_complete():
    tier1 = Tier1NonNegotiables(
        sleep=True, training=True, deep_work=True,
        zero_porn=True, boundaries=True
    )
    assert calculate_compliance_score(tier1) == 100.0

def test_compliance_score_partial():
    tier1 = Tier1NonNegotiables(
        sleep=False, training=True, deep_work=True,
        zero_porn=True, boundaries=True
    )
    assert calculate_compliance_score(tier1) == 80.0

# tests/test_streak.py
def test_streak_increments_consecutive_days():
    assert should_increment_streak("2026-01-29", "2026-01-30") == True

def test_streak_resets_after_gap():
    assert should_increment_streak("2026-01-25", "2026-01-30") == False
```

### Integration Tests (Database + Bot)
- Test full check-in flow with real Firestore (emulator in CI/CD)
- Test streak updates persist correctly
- Test check-in prevents duplicate same-day

### Manual Testing Checklist
- [ ] `/start` command works
- [ ] `/checkin` starts conversation
- [ ] Can complete full check-in (4 questions)
- [ ] Compliance score calculated correctly
- [ ] Streak increments on consecutive days
- [ ] Streak resets after 2+ day gap
- [ ] Can't check in twice same day
- [ ] `/status` shows correct streak
- [ ] Firestore data stored correctly
- [ ] Response time <5 seconds

---

## Key Learning Outcomes

By building Phase 1, you'll learn:

### Python Concepts
- **Async/await:** Modern async programming
- **Type hints & Pydantic:** Type safety
- **Virtual environments:** Dependency isolation
- **Package structure:** Organizing large projects

### Architecture Patterns
- **Service layer:** Separate business logic from data access
- **State machines:** Model conversational flows
- **Configuration management:** Environment-based config
- **Pure functions:** Testable, predictable code

### Cloud & DevOps
- **Firestore:** NoSQL database operations
- **Docker:** Containerization
- **Cloud Run:** Serverless deployment
- **Webhooks:** Event-driven architecture

### Bot Development
- **Telegram Bot API:** Building conversational interfaces
- **Conversation handlers:** Managing multi-turn interactions
- **Inline keyboards:** Interactive buttons
- **User state management:** Context persistence

---

## Phase 1 MVP Success Criteria

When Phase 1 is complete, you'll have:

✅ **Working Telegram bot** that responds to commands  
✅ **Daily check-in flow** with 4 questions  
✅ **Firestore storage** of all check-in data  
✅ **Compliance scoring** (% of Tier 1 completed)  
✅ **Streak tracking** (consecutive check-in days)  
✅ **Deployed to Cloud Run** (accessible 24/7)  
✅ **Response time <5 seconds**  
✅ **Hardcoded feedback** (AI feedback comes in Phase 2)  

---

## Next: Phase 2 Preview

Once Phase 1 is solid, Phase 2 adds:

- **LangGraph supervisor** → routes messages to specialized agents
- **Gemini AI feedback** → personalized responses using your constitution
- **Pattern detection** → catches sleep degradation, training abandonment, etc.
- **Interventions** → AI sends warnings when patterns detected
- **Scheduled scans** → Pattern detection runs every 6 hours

But first, let's build Phase 1 and get your daily check-ins working!

---

## Ready to Start Building?

Say **"let's build Phase 1"** and I'll:
1. Create all the files in sequence
2. Explain each component as I build it
3. Guide you through testing
4. Help you deploy to Cloud Run
5. Get your first check-in working tonight!

Or ask any questions about this plan first - I'm happy to clarify anything! 🚀
