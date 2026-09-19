"""
Tests for Webhook Security, Secret Verification, and Auto-Healing
=================================================================

Validates the multi-layer security defenses:
1. Webhook Secret Token derivation and validation (Settings & FastAPI endpoint)
2. Webhook Drift Detection & Auto-Healing (TelegramBotManager)
3. Secret Scanner regex pattern detection and exclusion behavior
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from httpx import AsyncClient, ASGITransport

from src.config import Settings
from src.bot.telegram_bot import TelegramBotManager
from scripts.secret_scanner import scan_text, is_sensitive_file


# =====================================================================
# 1. Webhook Secret Token Derivation & Validation
# =====================================================================

class TestWebhookSecretToken:
    def test_derived_secret_token_is_deterministic(self):
        token = "123456789:ABCdefGHIjklMNOpqrSTUvwxYZ_1234567"
        s1 = Settings(telegram_bot_token=token)
        s2 = Settings(telegram_bot_token=token)
        
        secret1 = s1.get_webhook_secret()
        secret2 = s2.get_webhook_secret()
        
        assert secret1 is not None
        assert secret1 == secret2
        assert len(secret1) == 64
        # Telegram secret_token must only contain [A-Za-z0-9_-]
        assert all(c.isalnum() or c in "-_" for c in secret1)

    def test_explicit_secret_overrides_derived(self):
        s = Settings(
            telegram_bot_token="123456789:ABCdefGHIjklMNOpqrSTUvwxYZ_1234567",
            telegram_webhook_secret="custom-secure-token-12345"
        )
        assert s.get_webhook_secret() == "custom-secure-token-12345"

    def test_missing_bot_token_returns_none(self):
        s = Settings(telegram_bot_token="")
        assert s.get_webhook_secret() is None


# =====================================================================
# 2. Webhook Endpoint Authentication (HTTP 403 vs 200)
# =====================================================================

@pytest.fixture
def webhook_app_client():
    from src.main import app
    transport = ASGITransport(app=app)
    return AsyncClient(transport=transport, base_url="http://test")


class TestWebhookEndpointAuth:
    @pytest.mark.asyncio
    async def test_webhook_rejects_missing_secret_token(self, webhook_app_client):
        with patch.object(Settings, "get_webhook_secret", return_value="expected-secret-token-123"):
            response = await webhook_app_client.post(
                "/webhook/telegram",
                json={"update_id": 1001, "message": {"text": "/start"}},
            )
            assert response.status_code == 403
            data = response.json()
            assert data["ok"] is False
            assert "Forbidden" in data["error"]

    @pytest.mark.asyncio
    async def test_webhook_rejects_invalid_secret_token(self, webhook_app_client):
        with patch.object(Settings, "get_webhook_secret", return_value="expected-secret-token-123"):
            response = await webhook_app_client.post(
                "/webhook/telegram",
                json={"update_id": 1001, "message": {"text": "/start"}},
                headers={"x-telegram-bot-api-secret-token": "wrong-secret-token"}
            )
            assert response.status_code == 403
            data = response.json()
            assert data["ok"] is False

    @pytest.mark.asyncio
    async def test_webhook_accepts_valid_secret_token(self, webhook_app_client):
        valid_secret = "expected-secret-token-123"
        mock_app = MagicMock()
        mock_app.process_update = AsyncMock()
        with patch.object(Settings, "get_webhook_secret", return_value=valid_secret), \
             patch("src.main.bot_manager.application", mock_app):
            
            response = await webhook_app_client.post(
                "/webhook/telegram",
                json={
                    "update_id": 1001,
                    "message": {
                        "message_id": 1,
                        "date": 1700000000,
                        "chat": {"id": 111, "type": "private"},
                        "from": {"id": 111, "is_bot": False, "first_name": "Test"},
                        "text": "/status"
                    }
                },
                headers={"x-telegram-bot-api-secret-token": valid_secret}
            )
            assert response.status_code == 200
            data = response.json()
            assert data["ok"] is True
            mock_app.process_update.assert_awaited_once()


# =====================================================================
# 3. Webhook Drift Detection & Auto-Healing
# =====================================================================

class TestWebhookDriftAndHealing:
    @pytest.mark.asyncio
    async def test_verify_when_webhook_matches(self):
        expected = "https://app.run.app/webhook/telegram"
        bot_mgr = MagicMock(spec=TelegramBotManager)
        
        info_mock = MagicMock()
        info_mock.url = expected
        info_mock.pending_update_count = 0
        info_mock.last_error_message = None
        info_mock.last_error_date = None
        
        bot_mgr.get_webhook_info = AsyncMock(return_value=info_mock)
        bot_mgr.set_webhook = AsyncMock(return_value=True)
        
        # Call the actual method on the class
        result = await TelegramBotManager.verify_and_heal_webhook(
            bot_mgr, expected_url=expected, secret_token="sec123"
        )
        
        assert result["ok"] is True
        assert result["drift_detected"] is False
        assert result["reclaimed"] is False
        bot_mgr.set_webhook.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_verify_when_webhook_hijacked_auto_heals(self):
        expected = "https://app.run.app/webhook/telegram"
        hijacked = "https://tele.goldenherd.com/tg/webhook/123456789"
        
        bot_mgr = MagicMock(spec=TelegramBotManager)
        info_mock = MagicMock()
        info_mock.url = hijacked
        info_mock.pending_update_count = 5
        info_mock.last_error_message = "Wrong response 530"
        info_mock.last_error_date = None
        
        bot_mgr.get_webhook_info = AsyncMock(return_value=info_mock)
        bot_mgr.set_webhook = AsyncMock(return_value=True)
        
        result = await TelegramBotManager.verify_and_heal_webhook(
            bot_mgr, expected_url=expected, secret_token="sec123"
        )
        
        assert result["ok"] is True
        assert result["drift_detected"] is True
        assert result["reclaimed"] is True
        assert result["current_url"] == hijacked
        bot_mgr.set_webhook.assert_awaited_once_with(expected, secret_token="sec123")

    @pytest.mark.asyncio
    async def test_verify_handles_api_exception(self):
        bot_mgr = MagicMock(spec=TelegramBotManager)
        bot_mgr.get_webhook_info = AsyncMock(side_effect=Exception("Telegram network error"))
        
        result = await TelegramBotManager.verify_and_heal_webhook(
            bot_mgr, expected_url="https://app.run.app/webhook/telegram"
        )
        
        assert result["ok"] is False
        assert "Telegram network error" in result["error"]


# =====================================================================
# 4. Secret Scanner Regex Detection
# =====================================================================

class TestSecretScanner:
    def test_detects_live_telegram_bot_token(self):
        # Dynamically assembled to avoid static regex matches on test code
        dummy_token = "9876543210:" + "B" * 35
        code = f'BOT_TOKEN = "{dummy_token}"'
        findings = scan_text(code, "test_file.py")
        assert len(findings) == 1
        assert "Telegram Bot Token found" in findings[0]

    def test_detects_google_api_key(self):
        dummy_key = "AIza" + "SyD1234567890abcdefghijklmnopqrstuv"
        code = f'API_KEY = "{dummy_key}"'
        findings = scan_text(code, "test_file.py")
        assert len(findings) == 1
        assert "Google / Gemini API Key found" in findings[0]

    def test_detects_private_key(self):
        header = "-----BEGIN " + "RSA PRIVATE KEY-----"
        footer = "-----END " + "RSA PRIVATE KEY-----"
        code = f"{header}\nMIIEowIBAAKCAQEA0...\n{footer}"
        findings = scan_text(code, "test_file.py")
        assert len(findings) == 1
        assert "Private Key found" in findings[0]

    def test_ignores_placeholders(self):
        placeholders = [
            "your_bot_token_here",
            "1234567890:ABCdefGHIjklMNOpqrSTUvwxYZ_EXAMPLE",
            "AIzaSyExamplePlaceholderKey1234567890",
        ]
        for p in placeholders:
            findings = scan_text(f'val = "{p}"', "test_file.py")
            assert len(findings) == 0

    def test_clean_file_has_no_findings(self):
        code = """
        import os
        token = os.environ.get("TELEGRAM_BOT_TOKEN")
        def run():
            return "ok"
        """
        findings = scan_text(code, "clean_file.py")
        assert len(findings) == 0

    def test_detects_sensitive_files(self):
        assert is_sensitive_file(".env") is True
        assert is_sensitive_file("foo/.env.production") is True
        assert is_sensitive_file("service_account.json") is True
        assert is_sensitive_file("service_account_prod.json") is True
        assert is_sensitive_file(".env.example") is False
        assert is_sensitive_file("src/main.py") is False
