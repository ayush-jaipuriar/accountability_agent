# Constitution Accountability Agent

AI-powered accountability system for personal constitution adherence, built with LangGraph + Gemini 2.0 Flash on GCP.

## 🎯 What This Does

Daily check-in system that:
- ✅ Tracks your Tier 1 non-negotiables (sleep, training, deep work, zero porn, boundaries)
- ✅ Calculates compliance scores (% of commitments completed)
- ✅ Monitors your check-in streak (consecutive days)
- ✅ Detects patterns and intervenes when violations occur (Phase 2)
- ✅ Provides personalized AI feedback based on your constitution (Phase 2)

## 🏗️ Architecture

```
User → Telegram App → Webhook → FastAPI (Cloud Run)
                                    ↓
                              Bot Handler
                                    ↓
                          Conversation State Machine
                                    ↓
                              Firestore (data)
                                    ↓
                          Calculate Score + Streak
                                    ↓
                          Send Feedback → User
```

**Tech Stack:**
- **Runtime:** Python 3.11+ with FastAPI
- **AI:** LangGraph + Vertex AI Gemini 2.0 Flash (Phase 2)
- **Infrastructure:** GCP Cloud Run, Firestore, Cloud Scheduler
- **Interface:** Telegram Bot (python-telegram-bot 21.0+)

## 📋 Project Status

**✅ Phase 1 (MVP) - COMPLETE (Feb 1, 2026):**
- ✅ Project structure and configuration
- ✅ Data models and schemas
- ✅ Firestore service layer
- ✅ Compliance and streak tracking utilities
- ✅ Telegram bot handlers
- ✅ Check-in conversation flow (4 questions)
- ✅ FastAPI webhook server
- ✅ Dockerfile for deployment
- ✅ Unit tests for core functionality
- ✅ Deployed to Cloud Run (asia-south1)
- ✅ Webhook configured and tested
- ✅ End-to-end testing complete

**✅ Phase 2 (LangGraph + Pattern Detection) - LOCAL TESTING COMPLETE (Feb 3, 2026):**
- ✅ LangGraph supervisor with intent classification (100% accuracy)
- ✅ AI-generated personalized feedback (Gemini 2.5 Flash)
- ✅ Pattern detection - 5 types (sleep degradation, porn relapse, training abandonment, compliance decline, bedtime inconsistency)
- ✅ Intervention agent (proactive warnings)
- ✅ Cost optimized: $0.0036/month (166x cheaper than target!)
- ✅ All tests passing: 50/50 (100% success rate)
- ⏸️ **Deployment Pending:** Cloud Run + Scheduler setup

**📊 Testing Results:**
```
Tests: 50/50 passing ✅
├─ Unit Tests: 37/37 ✅ (compliance, streak logic)
├─ Integration Tests: 13/13 ✅ (AI features)
└─ Coverage: ~85% (core logic)

Performance:
├─ Intent accuracy: 100%
├─ Token usage: ~150/check-in (target: <1000)
├─ Cost: $0.000022/check-in (target: <$0.001)
└─ Response time: ~7s (acceptable with AI)
```

📚 **Documentation:**
- `TESTING_COMPLETE_SUMMARY.md` - Deployment checklist
- `PHASE2_LOCAL_TESTING.md` - Testing methodology
- `PHASE2_TEST_RESULTS.md` - Detailed metrics

## 🚀 Setup Instructions

### Prerequisites

1. **Python 3.11+** installed
2. **Google Cloud Platform account** with:
   - Project created (`accountability-agent`)
   - Firestore database (Native mode, `asia-south1`)
   - Service account with JSON key
   - APIs enabled (Cloud Run, Firestore, Vertex AI, Secret Manager)
3. **Telegram bot** created via @BotFather (get bot token)

### Local Development Setup

#### 1. Clone Repository

```bash
cd ~/Documents/GitHub
git clone <repo-url> accountability_agent
cd accountability_agent
```

#### 2. Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

#### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

#### 4. Configure Environment Variables

```bash
# Copy .env.example to .env
cp .env.example .env

# Edit .env and fill in:
# - TELEGRAM_BOT_TOKEN (from @BotFather)
# - TELEGRAM_CHAT_ID (your Telegram user ID)
nano .env
```

**To get your Telegram Chat ID:**
1. Send a message to your bot
2. Visit: `https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates`
3. Look for `"from": {"id": 123456789}` in the JSON response

#### 5. Verify Service Account Key

Ensure service account key exists:

```bash
ls -la .credentials/accountability-agent-9256adc55379.json
```

If missing, download from GCP Console → IAM & Admin → Service Accounts.

#### 6. Test Firestore Connection

```bash
python -c "from src.services.firestore_service import firestore_service; print('✅ Connected!' if firestore_service.test_connection() else '❌ Failed')"
```

#### 7. Run Unit Tests

```bash
# Run all tests
pytest tests/ -v

# Run specific test file
pytest tests/test_compliance.py -v
pytest tests/test_streak.py -v

# Run with coverage
pytest tests/ --cov=src --cov-report=html
```

#### 8. Run Local Development Server

**Option A: Webhook Mode (requires ngrok or similar)**

```bash
# Start FastAPI server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000

# In another terminal, expose local server to internet
ngrok http 8000

# Set webhook URL
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/setWebhook?url=<NGROK_URL>/webhook/telegram"
```

**Option B: Polling Mode (easier for local testing)**

```bash
# TODO: Create polling script
python -m src.polling
```

#### 9. Test Bot Locally

Send commands to your Telegram bot:
- `/start` - Create your user profile
- `/checkin` - Start daily check-in
- `/status` - View your streak and compliance
- `/help` - Show available commands

## 🚢 Deployment to Cloud Run

### 1. Build Container Image

```bash
# Authenticate with GCP
gcloud auth login
gcloud config set project accountability-agent

# Build image using Cloud Build
gcloud builds submit --tag gcr.io/accountability-agent/constitution-agent:latest
```

### 2. Deploy to Cloud Run

```bash
gcloud run deploy constitution-agent \
  --image gcr.io/accountability-agent/constitution-agent:latest \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production,GCP_PROJECT_ID=accountability-agent,GCP_REGION=asia-south1,WEBHOOK_URL=https://constitution-agent-450357249483.asia-south1.run.app"
```

**Important:** The `WEBHOOK_URL` environment variable is critical for the bot to set the webhook correctly on startup.

**Note:** Store secrets in Secret Manager first (if not already done):

```bash
# Store bot token
echo -n "YOUR_BOT_TOKEN" | gcloud secrets create telegram-bot-token --data-file=-

# Store chat ID
echo -n "YOUR_CHAT_ID" | gcloud secrets create telegram-chat-id --data-file=-
```

### 3. Verify Webhook Configuration

The bot automatically sets the webhook on startup. Verify it's correct:

```bash
# Check webhook info
curl "https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getWebhookInfo"

# If webhook URL is wrong, manually update it:
BOT_TOKEN="YOUR_BOT_TOKEN"
CLOUD_RUN_URL="https://constitution-agent-450357249483.asia-south1.run.app"
curl "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${CLOUD_RUN_URL}/webhook/telegram"
```

### 4. Critical Fix: Application Initialization

**Issue:** The Telegram bot requires explicit initialization before processing webhook updates.

**Solution:** The `src/main.py` startup event now includes:

```python
# Initialize Telegram application (CRITICAL for webhook mode)
await bot_manager.application.initialize()
```

Without this, you'll get: `RuntimeError: This Application was not initialized via Application.initialize!`

**Why This Matters:**
- The `python-telegram-bot` library has a lifecycle: Build → Initialize → Process → Shutdown
- Webhook mode requires initialization but not `start()` (polling mode needs both)
- The `initialize()` call sets up internal state, handlers, and connection pooling

### 4. Test Production Deployment

- Send `/start` to your bot
- Complete a check-in with `/checkin`
- Check Cloud Run logs: `gcloud run logs read --service constitution-agent --region asia-south1`
- Verify data in Firestore Console

## 📊 Monitoring

### View Logs

```bash
# Recent logs
gcloud run logs read --service constitution-agent --region asia-south1 --limit 50

# Follow logs (live tail)
gcloud run logs tail --service constitution-agent --region asia-south1
```

### Check Service Status

```bash
# Health check
curl https://<CLOUD_RUN_URL>/health

# Service info
gcloud run services describe constitution-agent --region asia-south1
```

### Monitor Costs

- **GCP Console:** https://console.cloud.google.com/billing
- **Set Budget Alert:** $5/month threshold
- **Expected Cost:** ~$0.55/month (within free tier)

## 🧪 Testing

### Unit Tests

```bash
# Run all unit tests
pytest tests/ -v -m unit

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing
```

### Integration Tests (TODO: Phase 1)

```bash
# Test full check-in flow
pytest tests/integration/ -v -m integration
```

### Manual Testing Checklist

- [ ] `/start` command creates user profile
- [ ] `/checkin` starts conversation
- [ ] Complete full check-in (4 questions)
- [ ] Compliance score calculated correctly
- [ ] Streak increments on consecutive days
- [ ] Streak resets after 2+ day gap
- [ ] Can't check in twice same day
- [ ] `/status` shows correct streak
- [ ] Data stored correctly in Firestore

## 📂 Project Structure

```
accountability_agent/
├── src/
│   ├── __init__.py
│   ├── main.py                    # FastAPI entry point
│   ├── config.py                  # Configuration management
│   │
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── telegram_bot.py        # Bot initialization & handlers
│   │   └── conversation.py        # Check-in state machine
│   │
│   ├── services/
│   │   ├── __init__.py
│   │   ├── firestore_service.py   # Database operations
│   │   └── constitution_service.py # Load constitution.md
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   └── schemas.py             # Pydantic data models
│   │
│   └── utils/
│       ├── __init__.py
│       ├── compliance.py          # Score calculation
│       ├── streak.py              # Streak tracking
│       └── timezone_utils.py      # IST timezone handling
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py                # Pytest fixtures
│   ├── test_compliance.py         # Compliance tests
│   └── test_streak.py             # Streak tests
│
├── .credentials/                  # Service account keys (gitignored)
├── constitution.md                # Your personal constitution
├── requirements.txt               # Python dependencies
├── Dockerfile                     # Container image definition
├── .env                           # Environment variables (gitignored)
├── .env.example                   # Environment variables template
├── .gitignore                     # Git ignore rules
├── gcp-setup.md                   # GCP configuration reference
└── README.md                      # This file
```

## 🤝 Contributing

This is a personal accountability project, but contributions are welcome!

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/amazing-feature`
3. Commit your changes: `git commit -m 'Add amazing feature'`
4. Push to the branch: `git push origin feature/amazing-feature`
5. Open a Pull Request

## 📝 License

Private project - All rights reserved.

## 🙏 Acknowledgments

- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot) - Telegram Bot API wrapper
- [FastAPI](https://fastapi.tiangolo.com/) - Modern web framework
- [LangGraph](https://github.com/langchain-ai/langgraph) - Multi-agent orchestration
- [Google Cloud Platform](https://cloud.google.com/) - Infrastructure

## 📞 Support

- **Issues:** Open an issue in this repository
- **Documentation:** See `IMPLEMENTATION_PLAN.md` for detailed architecture
- **GCP Setup:** See `gcp-setup.md` for infrastructure details
- **Phase 1 Summary:** See `PHASE1_SUMMARY.md` for implementation details
- **Deployment Fix:** See `DEPLOYMENT_FIX.md` for webhook initialization bug fix
- **Completion Report:** See `PHASE1_COMPLETE.md` for final status

---

## 📚 Additional Documentation

### Phase 1-2 Implementation
- **[PHASE1_COMPLETE.md](PHASE1_COMPLETE.md)** - Phase 1 completion report with all metrics
- **[PHASE1_SUMMARY.md](PHASE1_SUMMARY.md)** - Detailed implementation summary
- **[DEPLOYMENT_FIX.md](DEPLOYMENT_FIX.md)** - Critical bug fix documentation
- **[PHASE2_CODE_REVIEW.md](PHASE2_CODE_REVIEW.md)** - Architecture deep dive
- **[TESTING_COMPLETE_SUMMARY.md](TESTING_COMPLETE_SUMMARY.md)** - Test results (50/50 passing)
- **[DEPLOYMENT_COMPLETE.md](DEPLOYMENT_COMPLETE.md)** - Phase 2 deployment status

### Product Review & Gap Analysis
- **[PRODUCT_REVIEW_PHASE1-2.md](PRODUCT_REVIEW_PHASE1-2.md)** - 📋 **Comprehensive review** with 60+ identified gaps
- **[PRODUCT_REVIEW_SUMMARY.md](PRODUCT_REVIEW_SUMMARY.md)** - 📊 Executive summary with critical findings
- **[CRITICAL_FIXES_ACTION_PLAN.md](CRITICAL_FIXES_ACTION_PLAN.md)** - 🛠️ Step-by-step implementation guide for P0 fixes

### Project Planning
- **[IMPLEMENTATION_PLAN.md](IMPLEMENTATION_PLAN.md)** - Full project roadmap
- **[gcp-setup.md](gcp-setup.md)** - GCP infrastructure configuration
- **[constitution.md](constitution.md)** - Personal constitution (AI context)

---

## 🚨 Known Issues & Next Steps

**See `PRODUCT_REVIEW_SUMMARY.md` for critical gaps that should be addressed before wider rollout:**

1. 🔴 **No 9 PM check-in reminders** - Users must remember manually
2. 🔴 **No onboarding flow** - New users will be confused
3. 🔴 **Constitution not surfaced to user** - No `/mode` or `/constitution` commands
4. 🔴 **Ghosting detection missing** - Can disappear for weeks with no escalation
5. 🔴 **Surgery recovery mode not enforced** - Medical safety issue (Feb 21 - Apr 15)

**Implementation guide available in `CRITICAL_FIXES_ACTION_PLAN.md`**

---

Built with ❤️ for personal accountability and growth.
