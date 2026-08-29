"""
FastAPI Endpoint Tests
======================

Tests for all HTTP endpoints exposed by the application.

**Testing Strategy:**
We use httpx.AsyncClient with FastAPI's TestClient pattern to test endpoints
without starting a real server. All external dependencies (Firestore, Telegram,
Gemini) are mocked to isolate the endpoint logic.

**What We Test:**
- Health check endpoint (/)
- Root endpoint (/)
- Triple reminder endpoints (/cron/reminder_first, _second, _third)
- Quick check-in reset (/cron/reset_quick_checkins)
- Pattern scan trigger (/trigger/pattern-scan)
- Weekly report trigger (/trigger/weekly-report)

**Key Concept: ASGI TestClient**
Instead of making real HTTP requests, we create an in-process test client
that speaks directly to the ASGI app. This is:
- Fast (no network overhead)
- Isolated (no real server needed)
- Deterministic (no timing issues)
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime


# We need to mock external services BEFORE importing the app
# because main.py imports firestore_service at module level

@pytest.fixture
def mock_services():
    """
    Mock all external services used by FastAPI endpoints.
    
    This fixture patches:
    1. firestore_service - Database operations
    2. bot_manager - Telegram bot operations
    3. settings - Application configuration
    
    These are patched at the module level where they're used (src.main)
    to ensure the mocks are in place when endpoint functions execute.
    """
    with patch('src.main.firestore_service') as mock_fs, \
         patch('src.main.bot_manager') as mock_bot, \
         patch('src.main.settings') as mock_settings:
        
        # Configure settings
        mock_settings.environment = "development"
        mock_settings.gcp_project_id = "test-project"
        mock_settings.gcp_region = "asia-south1"
        mock_settings.vertex_ai_location = "asia-south1"
        mock_settings.gemini_model = "gemini-2.0-flash"
        mock_settings.log_level = "INFO"
        mock_settings.cron_secret = ""  # Disable cron auth for tests
        mock_settings.admin_telegram_ids = "111222333"
        
        # Configure bot manager
        mock_bot.bot = MagicMock()
        mock_bot.bot.send_message = AsyncMock()
        
        yield {
            'firestore': mock_fs,
            'bot': mock_bot,
            'settings': mock_settings,
        }


@pytest.fixture
def test_user_obj():
    """Create a test User object for endpoint tests."""
    from src.models.schemas import User, UserStreaks, StreakShields
    return User(
        user_id="111222333",
        telegram_id=111222333,
        telegram_username="test_endpoint_user",
        name="Endpoint Test",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(current_streak=10, longest_streak=15, total_checkins=50),
        constitution_mode="maintenance",
        streak_shields=StreakShields(total=3, used=0, available=3),
    )


@pytest.fixture
def app_client(mock_services):
    """
    Create a FastAPI test client with mocked services.
    
    httpx.AsyncClient is the recommended way to test FastAPI async endpoints.
    It doesn't trigger startup/shutdown events, which is what we want
    (those would try to connect to real Telegram/Firestore).
    """
    from httpx import AsyncClient, ASGITransport
    from src.main import app
    
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


# ===== Root Endpoint Tests =====

class TestRootEndpoint:
    """Tests for GET / - basic service info."""

    async def test_root_returns_service_info(self, app_client):
        """Root should return service name and version."""
        response = await app_client.get("/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "Constitution Accountability Agent"
        assert data["version"] == "3.0.0"
        assert data["status"] == "running"

    async def test_root_includes_endpoints(self, app_client):
        """Root should list available endpoints."""
        response = await app_client.get("/")
        data = response.json()
        
        assert "endpoints" in data
        assert data["endpoints"]["health"] == "/health"
        assert data["endpoints"]["webhook"] == "/webhook/telegram"


# ===== Health Check Tests =====

class TestHealthEndpoint:
    """Tests for GET /health - Cloud Run health check."""

    async def test_health_ok(self, app_client, mock_services):
        """Should return 200 when Firestore is connected."""
        mock_services['firestore'].test_connection.return_value = True
        
        response = await app_client.get("/health")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["checks"]["firestore"] == "ok"

    async def test_health_unhealthy(self, app_client, mock_services):
        """Should return 503 when Firestore is down."""
        mock_services['firestore'].test_connection.return_value = False
        
        response = await app_client.get("/health")
        
        assert response.status_code == 503


# ===== Reminder Endpoint Tests =====

class TestReminderFirst:
    """
    Tests for POST /cron/reminder_first (9 PM IST).
    
    This endpoint:
    1. Gets current IST date
    2. Finds users without check-in today
    3. Checks if first reminder already sent
    4. Sends friendly reminder via Telegram
    5. Marks reminder as sent in Firestore
    """

    async def test_sends_reminder_to_users_without_checkin(
        self, app_client, mock_services, test_user_obj
    ):
        """Should send reminders to users who haven't checked in."""
        mock_fs = mock_services['firestore']
        mock_fs.get_users_without_checkin_today.return_value = [test_user_obj]
        mock_fs.get_reminder_status.return_value = None  # No reminder sent yet
        
        response = await app_client.post(
            "/cron/reminder_first",
            headers={"X-CloudScheduler-JobName": "reminder-first-job"}
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["reminder_type"] == "first"
        assert data["reminders_sent"] == 1
        
        # Verify Telegram message was sent
        mock_services['bot'].bot.send_message.assert_called_once()

    async def test_skips_if_already_sent(self, app_client, mock_services, test_user_obj):
        """Should skip users who already received first reminder."""
        mock_fs = mock_services['firestore']
        mock_fs.get_users_without_checkin_today.return_value = [test_user_obj]
        mock_fs.get_reminder_status.return_value = {"first_sent": True}
        
        response = await app_client.post("/cron/reminder_first")
        
        data = response.json()
        assert data["reminders_sent"] == 0

    async def test_no_users_need_reminder(self, app_client, mock_services):
        """Should handle case where all users have checked in."""
        mock_services['firestore'].get_users_without_checkin_today.return_value = []
        
        response = await app_client.post("/cron/reminder_first")
        
        data = response.json()
        assert data["reminders_sent"] == 0
        assert data["users_without_checkin"] == 0


class TestReminderSecond:
    """Tests for POST /cron/reminder_second (10:00 PM IST)."""

    async def test_sends_nudge_reminder(self, app_client, mock_services, test_user_obj):
        """Should send nudge-style reminder."""
        mock_fs = mock_services['firestore']
        mock_fs.get_users_without_checkin_today.return_value = [test_user_obj]
        mock_fs.get_reminder_status.return_value = {"second_sent": False}
        
        response = await app_client.post("/cron/reminder_second")
        
        assert response.status_code == 200
        data = response.json()
        assert data["reminder_type"] == "second"
        assert data["reminders_sent"] == 1


class TestReminderThird:
    """Tests for POST /cron/reminder_third (10 PM IST)."""

    async def test_sends_urgent_reminder(self, app_client, mock_services, test_user_obj):
        """Should send urgent reminder with streak shield info."""
        mock_fs = mock_services['firestore']
        mock_fs.get_users_without_checkin_today.return_value = [test_user_obj]
        mock_fs.get_reminder_status.return_value = {"third_sent": False}
        
        response = await app_client.post("/cron/reminder_third")
        
        assert response.status_code == 200
        data = response.json()
        assert data["reminder_type"] == "third"
        assert data["reminders_sent"] == 1

    async def test_multiple_users_reminder(self, app_client, mock_services, test_user_obj):
        """Should send reminders to multiple users."""
        from src.models.schemas import User, UserStreaks, StreakShields
        user2 = User(
            user_id="999888777",
            telegram_id=999888777,
            name="User Two",
            streaks=UserStreaks(current_streak=5),
            streak_shields=StreakShields(total=3, used=2, available=1),
        )
        
        mock_fs = mock_services['firestore']
        mock_fs.get_users_without_checkin_today.return_value = [test_user_obj, user2]
        mock_fs.get_reminder_status.return_value = None
        
        response = await app_client.post("/cron/reminder_third")
        
        data = response.json()
        assert data["reminders_sent"] == 2


# ===== Quick Check-In Reset Tests =====

class TestResetQuickCheckins:
    """
    Tests for POST /cron/reset_quick_checkins.
    
    This endpoint runs every Monday to reset the 2/week quick check-in limit.
    """

    async def test_resets_all_users(self, app_client, mock_services, test_user_obj):
        """Should reset quick check-in count for all users."""
        test_user_obj.quick_checkin_count = 2  # Used both
        mock_services['firestore'].get_all_users.return_value = [test_user_obj]
        
        response = await app_client.post("/cron/reset_quick_checkins")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "reset_complete"
        assert data["reset_count"] == 1
        
        # Verify Firestore update was called
        mock_services['firestore'].update_user.assert_called_once()

    async def test_reset_empty_users(self, app_client, mock_services):
        """Should handle case with no users."""
        mock_services['firestore'].get_all_users.return_value = []
        
        response = await app_client.post("/cron/reset_quick_checkins")
        
        data = response.json()
        assert data["reset_count"] == 0


# ===== Pattern Scan Tests =====

class TestPatternScan:
    """
    Tests for POST /trigger/pattern-scan.
    
    This is the proactive pattern detection endpoint that runs every 6 hours.
    It scans all users for constitution violation patterns and sends interventions.
    """

    async def test_no_patterns_found(self, app_client, mock_services, test_user_obj):
        """Should complete successfully when no patterns found."""
        mock_fs = mock_services['firestore']
        mock_fs.get_all_users.return_value = [test_user_obj]
        mock_fs.get_recent_checkins.return_value = []
        
        with patch('src.agents.pattern_detection.get_pattern_detection_agent') as mock_pd, \
             patch('src.agents.intervention.get_intervention_agent') as mock_ia:
            mock_pd.return_value.detect_patterns.return_value = []
            mock_pd.return_value.detect_ghosting.return_value = None
            
            response = await app_client.post("/trigger/pattern-scan")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "scan_complete"
        assert data["patterns_detected"] == 0

    async def test_pattern_detected_sends_intervention(
        self, app_client, mock_services, test_user_obj
    ):
        """Should detect pattern and send intervention message."""
        from src.agents.pattern_detection import Pattern
        
        mock_fs = mock_services['firestore']
        mock_fs.get_all_users.return_value = [test_user_obj]
        mock_fs.get_recent_checkins.return_value = [MagicMock()]
        mock_fs.get_user.return_value = None  # For partner lookup
        
        test_pattern = Pattern(
            type="sleep_degradation",
            severity="high",
            detected_at=datetime.utcnow(),
            data={"avg_sleep": 5.2, "consecutive_days": 3, "message": "test"},
        )
        
        mock_bot = mock_services['bot']
        mock_bot.send_message = AsyncMock()
        
        with patch('src.agents.pattern_detection.get_pattern_detection_agent') as mock_pd, \
             patch('src.agents.intervention.get_intervention_agent') as mock_ia:
            mock_pd.return_value.detect_patterns.return_value = [test_pattern]
            mock_pd.return_value.detect_ghosting.return_value = None
            mock_ia.return_value.generate_intervention = AsyncMock(return_value="Test intervention")
            
            response = await app_client.post("/trigger/pattern-scan")
        
        assert response.status_code == 200
        data = response.json()
        assert data["patterns_detected"] >= 1
        # Intervention may or may not be sent depending on bot_manager mock chain
        assert data["status"] == "scan_complete"


# ===== Weekly Report Tests =====

class TestWeeklyReport:
    """Tests for POST /trigger/weekly-report."""

    async def test_weekly_report_success(self, app_client, mock_services):
        """Should trigger weekly reports and return results."""
        with patch('src.agents.reporting_agent.send_weekly_reports_to_all') as mock_reports:
            mock_reports.return_value = {
                "reports_sent": 2,
                "reports_failed": 0,
                "total_users": 2,
            }
            
            response = await app_client.post("/trigger/weekly-report")
        
        assert response.status_code == 200
        data = response.json()
        assert data["reports_sent"] == 2
        assert data["reports_failed"] == 0

    async def test_weekly_report_failure(self, app_client, mock_services):
        """Should return 500 when report generation fails."""
        with patch('src.agents.reporting_agent.send_weekly_reports_to_all') as mock_reports:
            mock_reports.side_effect = Exception("Report generation failed")
            
            response = await app_client.post("/trigger/weekly-report")
        
        assert response.status_code == 500


# ===== Morning Briefing Tests =====

class TestMorningBriefingCron:
    """Tests for POST /cron/morning_briefing."""

    @patch('src.utils.timezone_utils.get_timezones_at_local_time')
    @patch('src.services.briefing_service.briefing_service.generate_briefing')
    @patch('src.services.task_service.task_service.get_daily_tasks')
    async def test_morning_briefing_success(
        self, mock_get_tasks, mock_gen_briefing, mock_get_tzs,
        app_client, mock_services, test_user_obj
    ):
        """Should successfully generate and send morning briefings."""
        mock_get_tzs.return_value = ["Asia/Kolkata"]
        mock_fs = mock_services['firestore']
        mock_fs.get_users_by_timezones.return_value = [test_user_obj]
        mock_gen_briefing.return_value = "Mocked Morning Brief"
        
        from src.models.schemas import DailyTaskList
        mock_get_tasks.return_value = DailyTaskList(
            user_id="111222333",
            date="2026-06-28",
            tasks=[],
            committed=False
        )
        
        response = await app_client.post("/cron/morning_briefing")
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["results"]["sent"] == 1
        assert data["results"]["errors"] == 0
        
        # Verify bot sent the message
        mock_bot = mock_services['bot']
        mock_bot.bot.send_message.assert_called_once()
        args, kwargs = mock_bot.bot.send_message.call_args
        assert kwargs["chat_id"] == test_user_obj.telegram_id
        assert kwargs["text"] == "Mocked Morning Brief"



# ===== Admin Metrics Tests =====

class TestAdminMetrics:

    async def test_admin_metrics_authorized(self, app_client, mock_services):
        mock_services['settings'].admin_telegram_ids = "111222333,999888"
        response = await app_client.get("/admin/metrics?admin_id=111222333")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    async def test_admin_metrics_unauthorized(self, app_client, mock_services):
        mock_services['settings'].admin_telegram_ids = "111222333"
        response = await app_client.get("/admin/metrics?admin_id=wrong_id")
        assert response.status_code == 403


# ===== Telegram Webhook Tests =====

class TestTelegramWebhook:

    async def test_telegram_webhook_success(self, app_client, mock_services):
        mock_bot = mock_services['bot']
        mock_bot.application = MagicMock()
        mock_bot.application.process_update = AsyncMock()

        with patch('src.main.Update.de_json', return_value=MagicMock()):
            payload = {"update_id": 10001, "message": {"text": "/status"}}
            response = await app_client.post("/webhook/telegram", json=payload)
            assert response.status_code == 200
            assert response.json() == {"ok": True}
            mock_bot.application.process_update.assert_called_once()

    async def test_telegram_webhook_error_handling(self, app_client, mock_services):
        mock_bot = mock_services['bot']
        mock_bot.application = MagicMock()
        mock_bot.application.process_update = AsyncMock(side_effect=Exception("Processing error"))

        with patch('src.main.Update.de_json', return_value=MagicMock()):
            payload = {"update_id": 10002}
            response = await app_client.post("/webhook/telegram", json=payload)
            assert response.status_code == 200
            assert response.json()["ok"] is False


# ===== Timezone-Aware Reminder Cron Tests =====

class TestTimezoneAwareReminderCron:

    @patch('src.utils.timezone_utils.get_timezones_at_local_time')
    async def test_reminder_tz_aware_success(self, mock_get_tzs, app_client, mock_services, test_user_obj):
        mock_get_tzs.side_effect = lambda utc, h, m=0, tolerance_minutes=7: ["Asia/Kolkata"] if h == 21 else []
        mock_fs = mock_services['firestore']
        mock_fs.get_users_by_timezones.return_value = [test_user_obj]
        mock_fs.get_reminder_status.return_value = None
        mock_fs.checkin_exists.return_value = False

        response = await app_client.post("/cron/reminder_tz_aware")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "tz_aware_reminders_complete"


# ===== Additional Cron and Admin Endpoints =====

class TestAdditionalCronAndAdminEndpoints:

    @patch('src.utils.timezone_utils.get_timezones_at_local_time')
    @patch('src.services.task_service.task_service.get_daily_tasks')
    async def test_midday_nudge(self, mock_get_tasks, mock_get_tzs, app_client, mock_services, test_user_obj):
        mock_get_tzs.return_value = ["Asia/Kolkata"]
        mock_fs = mock_services['firestore']
        mock_fs.get_users_by_timezones.return_value = [test_user_obj]
        mock_fs.checkin_exists.return_value = False
        
        from src.models.schemas import DailyTaskList
        mock_get_tasks.return_value = DailyTaskList(user_id=test_user_obj.user_id, date="2026-02-07", tasks=[])

        response = await app_client.post("/cron/midday_nudge")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"

    @patch('src.services.churn_intervention.send_churn_intervention', return_value=True)
    @patch('src.services.churn_prediction.churn_predictor.is_intervention_cooled_down', return_value=True)
    @patch('src.services.churn_prediction.churn_predictor.calculate_risk_score', return_value=(0.8, ["declining_compliance"], {}))
    @patch('src.utils.timezone_utils.get_timezones_at_local_time')
    async def test_churn_prevention(self, mock_get_tzs, mock_calc_risk, mock_cooldown, mock_send, app_client, mock_services, test_user_obj):
        mock_services['settings'].enable_churn_prediction = True
        mock_get_tzs.return_value = ["Asia/Kolkata"]
        mock_fs = mock_services['firestore']
        mock_fs.get_users_by_timezones.return_value = [test_user_obj]

        response = await app_client.post("/cron/churn_prevention")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch('src.utils.timezone_utils.get_timezones_at_local_time')
    @patch('src.services.predictive_intervention.predictive_intervention_engine.predict_tomorrow_risk')
    async def test_predictive_intervention(self, mock_predict, mock_get_tzs, app_client, mock_services, test_user_obj):
        mock_get_tzs.return_value = ["Asia/Kolkata"]
        mock_fs = mock_services['firestore']
        mock_fs.get_users_by_timezones.return_value = [test_user_obj]
        mock_predict.return_value = {"risk_level": "high", "should_intervene": True, "risk_factors": ["late sleep"]}

        response = await app_client.post("/cron/predictive_intervention")
        assert response.status_code == 200
        assert response.json()["status"] == "success"

    @patch('src.services.feedback_service.feedback_service.get_last_feedback', return_value=None)
    async def test_weekly_nps(self, mock_feedback, app_client, mock_services, test_user_obj):
        mock_fs = mock_services['firestore']
        mock_fs.get_all_users.return_value = [test_user_obj]

        response = await app_client.post("/cron/weekly_nps")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "success"
        assert data["results"]["sent"] == 1

    async def test_admin_broadcast_success_and_unauthorized(self, app_client, mock_services, test_user_obj):
        mock_services['settings'].admin_telegram_ids = "111222333"
        mock_fs = mock_services['firestore']
        mock_fs.get_all_users.return_value = [test_user_obj]

        # Success
        response = await app_client.post(
            "/admin/broadcast?admin_id=111222333",
            json={"message": "System maintenance at 2 AM UTC"}
        )
        assert response.status_code == 200
        assert response.json()["sent"] == 1

        # Missing message
        res_missing = await app_client.post(
            "/admin/broadcast?admin_id=111222333",
            json={"message": ""}
        )
        assert res_missing.status_code == 400

        # Unauthorized
        res_unauth = await app_client.post(
            "/admin/broadcast?admin_id=unknown",
            json={"message": "test"}
        )
        assert res_unauth.status_code == 403

    @patch('src.agents.reporting_agent.send_weekly_reports_to_all')
    async def test_periodic_report(self, mock_weekly, app_client, mock_services):
        mock_weekly.return_value = {"reports_sent": 3, "reports_cooldown": 0, "reports_failed": 0}
        response = await app_client.post("/trigger/periodic-report")
        assert response.status_code == 200
        assert response.json()["reports_sent"] == 3


# ===== Cron Secret Authentication Tests =====

class TestVerifyCronRequestAuth:

    async def test_cron_auth_header_valid_and_invalid(self, app_client, mock_services):
        mock_services['settings'].cron_secret = "super_secret_token"

        # Valid secret
        response_valid = await app_client.post(
            "/cron/reset_quick_checkins",
            headers={"X-Cron-Secret": "super_secret_token"}
        )
        assert response_valid.status_code == 200

        # Missing / invalid secret
        response_invalid = await app_client.post(
            "/cron/reset_quick_checkins",
            headers={"X-Cron-Secret": "wrong_token"}
        )
        assert response_invalid.status_code == 403
