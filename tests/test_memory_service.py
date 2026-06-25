"""
Tests for AI-First Profile Memory & Reflection Validator
========================================================

Tests:
- AIProfileMemory serialization/deserialization on the User model.
- Length validation (min 20 characters) for user daily reflections.
- MemoryService synthesis trigger, prompt building, and Firestore persistence.
"""

import pytest
import json
from datetime import datetime, UTC
from unittest.mock import MagicMock, AsyncMock, patch

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler

from src.models.schemas import User, AIProfileMemory, DailyCheckIn, Tier1NonNegotiables, CheckInResponses
from src.services.memory_service import MemoryService
from src.bot.conversation import handle_reflection_response, Q4_REFLECTION_NOTE


# ===== Helpers =====

def _make_user(user_id="user123", **overrides) -> User:
    defaults = dict(
        user_id=user_id,
        telegram_id=12345,
        name="Test User",
        timezone="Asia/Kolkata",
        ai_profile_memory=AIProfileMemory()
    )
    defaults.update(overrides)
    return User(**defaults)


def _make_checkin(date="2026-06-25", compliance=80.0) -> DailyCheckIn:
    return DailyCheckIn(
        date=date,
        user_id="user123",
        mode="maintenance",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=True, sleep_hours=7.5,
            training=True, training_intensity="moderate",
            deep_work=True, deep_work_hours=3.0,
            zero_porn=True, boundaries=True
        ),
        responses=CheckInResponses(
            challenges="Felt a bit tired in the afternoon",
            energy_rating=7,
            mood_rating=8,
            rating=8,
            rating_reason="Got most of my tasks done",
            tomorrow_priority="Complete the backend unit tests",
            tomorrow_obstacle="None anticipated"
        ),
        compliance_score=compliance
    )


# ===== Schema Tests =====

class TestAIProfileMemorySchema:
    """Tests the AIProfileMemory model nested inside User."""

    def test_default_values(self):
        """Verify defaults are set correctly when User is created."""
        user = _make_user()
        mem = user.ai_profile_memory
        
        assert mem.summary == "New user starting their journey."
        assert mem.strengths == []
        assert mem.weaknesses == []
        assert mem.recurring_obstacles == []
        assert mem.correlations == []
        assert mem.coaching_notes == ""
        assert mem.say_do_ratio == 0.0
        assert mem.last_updated is None

    def test_serialization_roundtrip(self):
        """Verify serialization to/from Firestore preserves memory fields."""
        custom_memory = AIProfileMemory(
            summary="A highly motivated builder who sometimes sleeps late.",
            strengths=["Consistent workouts", "Strong morning routines"],
            weaknesses=["Late night distractions", "Skipping weekend planning"],
            recurring_obstacles=[{"obstacle": "social media", "frequency": "high", "last_seen": "2026-06-25"}],
            correlations=["Sleep <7h correlates with a 30% drop in deep work"],
            coaching_notes="Keep prompts short, focus on weekend preparation.",
            say_do_ratio=82.5,
            last_updated=datetime(2026, 6, 25, 12, 0, 0, tzinfo=UTC)
        )
        
        original_user = _make_user(ai_profile_memory=custom_memory)
        serialized_data = original_user.to_firestore()
        
        assert "ai_profile_memory" in serialized_data
        restored_user = User.from_firestore(serialized_data)
        
        restored_mem = restored_user.ai_profile_memory
        assert restored_mem.summary == custom_memory.summary
        assert restored_mem.strengths == custom_memory.strengths
        assert restored_mem.weaknesses == custom_memory.weaknesses
        assert restored_mem.recurring_obstacles == custom_memory.recurring_obstacles
        assert restored_mem.correlations == custom_memory.correlations
        assert restored_mem.coaching_notes == custom_memory.coaching_notes
        assert restored_mem.say_do_ratio == custom_memory.say_do_ratio
        
        # Test backward compatibility (handling legacy Firestore data lacking memory field)
        legacy_data = {
            "user_id": "legacy_user",
            "telegram_id": 99999,
            "name": "Legacy User",
            "timezone": "Asia/Kolkata"
        }
        legacy_user = User.from_firestore(legacy_data)
        assert legacy_user.ai_profile_memory is not None
        assert legacy_user.ai_profile_memory.summary == "New user starting their journey."


# ===== Reflection Validator Tests =====

class TestReflectionValidation:
    """Tests the minimum character validation for daily reflections."""

    @pytest.mark.asyncio
    async def test_reflection_too_short(self):
        """A message under 20 characters should be rejected and prompt again."""
        update = MagicMock(spec=Update)
        update.message = AsyncMock()
        update.message.text = "Too short."
        update.message.reply_text = AsyncMock()

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {}

        result = await handle_reflection_response(update, context)
        
        # Should stay in reflection state
        assert result == Q4_REFLECTION_NOTE
        # Reply text should have warning
        args, kwargs = update.message.reply_text.call_args
        assert "Reflection note too short!" in args[0]
        assert "at least 20 characters" in args[0]

    @pytest.mark.asyncio
    @patch("src.bot.conversation.get_checkin_agent")
    @patch("src.bot.conversation.finish_checkin", new_callable=AsyncMock)
    async def test_reflection_valid_length(self, mock_finish, mock_get_agent):
        """A message with 20 or more characters should proceed to parse."""
        update = MagicMock(spec=Update)
        update.message = AsyncMock()
        update.message.text = "This is a detailed reflection note that satisfies the 20 character requirement."
        update.message.reply_text = AsyncMock(return_value=AsyncMock()) # mock progress message

        context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
        context.user_data = {
            "compliance_score": 80.0,
            "tier1": MagicMock(),
            "user_id": "user123",
            "checkin_type": "full",
            "rating_reason": "",
            "tomorrow_priority": "",
            "tomorrow_obstacle": ""
        }

        # Mock check-in agent response
        mock_agent = AsyncMock()
        mock_agent.parse_reflection_note.return_value = {
            "rating": 8,
            "rating_reason": "Good work on priorities",
            "tomorrow_priority": "Write tests",
            "tomorrow_obstacle": "Distractions",
            "challenges": "Felt tired"
        }
        mock_get_agent.return_value = mock_agent

        result = await handle_reflection_response(update, context)
        
        assert result == ConversationHandler.END
        mock_agent.parse_reflection_note.assert_called_once()
        mock_finish.assert_called_once_with(update, context)
        assert context.user_data["rating"] == 8
        assert context.user_data["rating_reason"] == "Good work on priorities"


# ===== Memory Service Tests =====

class TestMemoryService:
    """Tests the MemoryService profile synthesis logic."""

    @pytest.mark.asyncio
    @patch("src.services.memory_service.firestore_service")
    async def test_update_user_memory_insufficient_checkins(self, mock_fs):
        """If user has fewer than 5 check-ins, synthesis is skipped."""
        user = _make_user()
        mock_fs.get_user.return_value = user
        # Only 4 checkins
        mock_fs.get_recent_checkins.return_value = [_make_checkin() for _ in range(4)]

        service = MemoryService(project_id="test-proj")
        service.llm = AsyncMock()
        result = await service.update_user_memory("user123")

        assert result is None
        # Should not call LLM
        service.llm.generate_text.assert_not_called()

    @pytest.mark.asyncio
    @patch("src.services.memory_service.firestore_service")
    @patch("src.services.memory_service.get_llm_service")
    async def test_update_user_memory_success(self, mock_get_llm, mock_fs):
        """If user has 5+ checkins, Gemini is called to synthesize profile memory."""
        user = _make_user()
        mock_fs.get_user.return_value = user
        mock_fs.get_recent_checkins.return_value = [_make_checkin(date=f"2026-06-{20+i}") for i in range(5)]
        mock_fs.update_user.return_value = True

        # Mock Gemini response
        mock_llm = AsyncMock()
        mock_response_json = {
            "summary": "User shows high discipline in deep work but slumps on workouts.",
            "strengths": ["Deep work consistency", "Early mornings"],
            "weaknesses": ["Weekend workouts", "Late bedtime"],
            "recurring_obstacles": [
                {"obstacle": "Social events", "frequency": "medium", "last_seen": "2026-06-24"}
            ],
            "correlations": ["Sleep deprivation leads to skipped training"],
            "coaching_notes": "Prompt user specifically on workout scheduling.",
            "say_do_ratio": 75.0
        }
        # Include markdown formatting to test cleaning regex
        mock_llm.generate_text.return_value = f"```json\n{json.dumps(mock_response_json)}\n```"
        mock_get_llm.return_value = mock_llm

        service = MemoryService(project_id="test-proj")
        result = await service.update_user_memory("user123")

        assert result is not None
        assert result.summary == mock_response_json["summary"]
        assert result.strengths == mock_response_json["strengths"]
        assert result.weaknesses == mock_response_json["weaknesses"]
        assert len(result.recurring_obstacles) == 1
        assert result.recurring_obstacles[0]["obstacle"] == "Social events"
        assert result.correlations == mock_response_json["correlations"]
        assert result.coaching_notes == mock_response_json["coaching_notes"]
        assert result.say_do_ratio == 75.0
        assert isinstance(result.last_updated, datetime)

        # Check firestore update payload
        mock_fs.update_user.assert_called_once()
        args, kwargs = mock_fs.update_user.call_args
        assert args[0] == "user123"
        payload = args[1]
        assert "ai_profile_memory" in payload
        assert payload["ai_profile_memory"]["summary"] == result.summary
        assert payload["ai_profile_memory"]["say_do_ratio"] == 75.0
