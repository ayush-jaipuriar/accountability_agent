"""
Configuration Management
========================

This module loads environment variables and provides type-safe configuration
for the entire application.

Why Pydantic Settings?
- Type validation: Ensures variables are correct types
- Automatic .env loading: Reads from .env file in development
- Defaults: Provides sensible defaults for optional settings
- Validation: Raises errors if required settings are missing

Usage:
    from src.config import settings
    
    print(settings.telegram_bot_token)  # Access configuration
    print(settings.gcp_project_id)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    
    Required variables:
    - TELEGRAM_BOT_TOKEN: Bot token from @BotFather
    - TELEGRAM_CHAT_ID: Your Telegram user ID
    
    Optional variables have defaults (see below).
    """
    
    # ===== GCP Configuration =====
    gcp_project_id: str = "accountability-agent"
    google_application_credentials: Optional[str] = None  # Optional: Cloud Run uses default service account
    gcp_region: str = "asia-south1"
    
    # ===== Telegram Configuration =====
    telegram_bot_token: str  # Required - no default (will raise error if missing)
    telegram_chat_id: str    # Required - your Telegram user ID
    
    # ===== Cloud Run Configuration =====
    webhook_url: str = ""  # Set when deployed to Cloud Run
    environment: str = "development"  # development, staging, production
    
    # ===== Vertex AI Configuration =====
    vertex_ai_location: str = "asia-south1"
    gemini_model: str = "gemini-2.5-flash"  # Use Gemini 2.5 Flash (standard reasoning, fast)
    gemini_api_key: Optional[str] = None  # For direct Gemini API (alternative to Vertex AI)
    
    # ===== Application Settings =====
    log_level: str = "INFO"
    timezone: str = "Asia/Kolkata"
    
    # ===== Check-in Settings =====
    checkin_time: str = "21:00"  # 9 PM IST
    checkin_reminder_delay_minutes: int = 30
    
    # ===== Feature Flags =====
    enable_pattern_detection: bool = True
    enable_emotional_processing: bool = False  # Phase 4
    enable_ghosting_detection: bool = False    # Phase 4
    enable_reports: bool = False                # Phase 3
    
    # ===== Pydantic Configuration =====
    model_config = SettingsConfigDict(
        env_file=".env",           # Load from .env file
        env_file_encoding="utf-8",
        case_sensitive=False,      # TELEGRAM_BOT_TOKEN = telegram_bot_token
        extra="ignore"             # Ignore extra variables in .env
    )


# Create singleton instance
# This is imported throughout the app: `from src.config import settings`
settings = Settings()


def get_settings() -> Settings:
    """
    Get the settings singleton instance
    
    This is a helper function for consistency with other get_* functions.
    You can also import `settings` directly: `from src.config import settings`
    
    Returns:
        Settings singleton instance
    """
    return settings


# Validate critical paths on import
import os
from pathlib import Path

def validate_configuration():
    """
    Validate that critical files exist and configuration is correct.
    
    Called when module is imported. Raises errors if setup is incomplete.
    
    Note: In production (Cloud Run), service account key file is not needed
    as Cloud Run uses Application Default Credentials automatically.
    """
    # Check service account key exists (only in development)
    if settings.environment == "development":
        creds_path = Path(settings.google_application_credentials)
        if not creds_path.exists():
            raise FileNotFoundError(
                f"Service account key not found at: {settings.google_application_credentials}\n"
                f"Expected location: {creds_path.absolute()}\n"
                "Please ensure you've moved the key file to .credentials/ folder."
            )
    else:
        # Production: Cloud Run uses Application Default Credentials
        print(f"ℹ️  Production mode: Using Application Default Credentials")
    
    # Validate timezone
    import pytz
    try:
        pytz.timezone(settings.timezone)
    except pytz.UnknownTimeZoneError:
        raise ValueError(f"Invalid timezone: {settings.timezone}")
    
    print(f"✅ Configuration loaded successfully")
    print(f"   Environment: {settings.environment}")
    print(f"   GCP Project: {settings.gcp_project_id}")
    print(f"   Region: {settings.gcp_region}")
    print(f"   Timezone: {settings.timezone}")


# Run validation when module loads
if __name__ != "__main__":  # Don't run during testing
    validate_configuration()
