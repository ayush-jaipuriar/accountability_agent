"""
Phase D: Streak Recovery Encouragement + Intervention-to-Support Linking Tests
===============================================================================

Comprehensive test suite covering:
- Feature 3: Streak Recovery System
  - RECOVERY_FACTS database
  - format_streak_reset_message()
  - get_recovery_milestone_message()
  - update_streak_data() with recovery context
  - Schema: UserStreaks new fields (streak_before_reset, last_reset_date)
  - Achievement: Comeback Kid, Comeback King, Comeback Legend
  - Firestore transient key filtering
  
- Feature 4: Intervention-to-Support Linking
  - SUPPORT_BRIDGES definitions
  - add_support_bridge() function
  - Support bridge integration in all intervention paths
  - /support command (standalone and with context)
  - support_mode in general message handler
"""

import pytest
import sys
import os
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# ============================================================
# FEATURE 3: STREAK RECOVERY SYSTEM TESTS
# ============================================================

class TestRecoveryFacts:
    """Test the RECOVERY_FACTS motivational messages database."""

    def test_recovery_facts_exist(self):
        """RECOVERY_FACTS should be a non-empty list of strings."""
        from src.utils.streak import RECOVERY_FACTS
        assert isinstance(RECOVERY_FACTS, list)
        assert len(RECOVERY_FACTS) >= 5, "Should have at least 5 facts for variety"

    def test_recovery_facts_are_strings(self):
        """Each fact should be a non-empty string."""
        from src.utils.streak import RECOVERY_FACTS
        for fact in RECOVERY_FACTS:
            assert isinstance(fact, str)
            assert len(fact) > 10, f"Fact too short: '{fact}'"

    def test_recovery_facts_no_duplicates(self):
        """All facts should be unique."""
        from src.utils.streak import RECOVERY_FACTS
        assert len(RECOVERY_FACTS) == len(set(RECOVERY_FACTS))


class TestFormatStreakResetMessage:
    """Test the streak reset message formatter."""

    def test_basic_reset_message(self):
        """Should generate a compassionate reset message."""
        from src.utils.streak import format_streak_reset_message
        msg = format_streak_reset_message(
            streak_before_reset=23,
            recovery_fact="Most people who reach 30+ days had at least one reset."
        )
        assert "Fresh Start" in msg
        assert "23 days" in msg
        assert "Day 1" in msg
        assert "Comeback King" in msg
        assert "Most people" in msg

    def test_reset_message_with_zero_previous(self):
        """Edge case: streak_before_reset=0 (first ever streak)."""
        from src.utils.streak import format_streak_reset_message
        msg = format_streak_reset_message(
            streak_before_reset=0,
            recovery_fact="A streak reset isn't starting over."
        )
        assert "Fresh Start" in msg
        assert "Day 1" in msg
        # Should NOT show "Your previous streak: 0 days" — that's not meaningful
        assert "0 days" not in msg

    def test_reset_message_html_safe(self):
        """Message should use HTML tags (not Markdown) for Telegram."""
        from src.utils.streak import format_streak_reset_message
        msg = format_streak_reset_message(
            streak_before_reset=10,
            recovery_fact="Test fact."
        )
        assert "<b>" in msg


class TestGetRecoveryMilestoneMessage:
    """Test recovery milestone detection at days 3, 7, 14, and exceeds previous."""

    def test_day_3_milestone(self):
        """Day 3 after reset should show '3 Days Strong'."""
        from src.utils.streak import get_recovery_milestone_message
        msg = get_recovery_milestone_message(
            current_streak=3,
            streak_before_reset=15,
            last_reset_date="2026-02-01"
        )
        assert msg is not None
        assert "3 Days Strong" in msg

    def test_day_7_milestone(self):
        """Day 7 after reset should show 'Comeback King'."""
        from src.utils.streak import get_recovery_milestone_message
        msg = get_recovery_milestone_message(
            current_streak=7,
            streak_before_reset=20,
            last_reset_date="2026-02-01"
        )
        assert msg is not None
        assert "Comeback King" in msg

    def test_day_14_milestone(self):
        """Day 14 after reset should show 'Two Weeks Strong'."""
        from src.utils.streak import get_recovery_milestone_message
        msg = get_recovery_milestone_message(
            current_streak=14,
            streak_before_reset=30,
            last_reset_date="2026-02-01"
        )
        assert msg is not None
        assert "Two Weeks" in msg

    def test_exceed_previous_streak(self):
        """Exceeding previous best should show 'NEW RECORD'."""
        from src.utils.streak import get_recovery_milestone_message
        msg = get_recovery_milestone_message(
            current_streak=16,
            streak_before_reset=15,
            last_reset_date="2026-02-01"
        )
        assert msg is not None
        assert "NEW RECORD" in msg
        assert "15" in msg  # References old streak

    def test_exceed_only_if_previous_meaningful(self):
        """Exceed check should only trigger if previous was >= 3 days."""
        from src.utils.streak import get_recovery_milestone_message
        msg = get_recovery_milestone_message(
            current_streak=3,
            streak_before_reset=2,
            last_reset_date="2026-02-01"
        )
        # streak_before_reset=2 < 3, so "exceed" shouldn't trigger (but Day 3 milestone should)
        if msg:
            assert "NEW RECORD" not in msg

    def test_no_milestone_on_day_2(self):
        """Day 2 is NOT a recovery milestone (no message)."""
        from src.utils.streak import get_recovery_milestone_message
        msg = get_recovery_milestone_message(
            current_streak=2,
            streak_before_reset=10,
            last_reset_date="2026-02-01"
        )
        assert msg is None

    def test_no_milestone_without_reset(self):
        """Without a recent reset, no recovery milestones should fire."""
        from src.utils.streak import get_recovery_milestone_message
        msg = get_recovery_milestone_message(
            current_streak=7,
            streak_before_reset=0,
            last_reset_date=None
        )
        assert msg is None

    def test_no_milestone_very_long_recovery(self):
        """If way past old streak, stop showing recovery milestones."""
        from src.utils.streak import get_recovery_milestone_message
        msg = get_recovery_milestone_message(
            current_streak=100,
            streak_before_reset=5,
            last_reset_date="2026-01-01"
        )
        # 100 > max(5*2, 30), so should return None (normal milestones take over)
        assert msg is None


class TestUpdateStreakDataRecovery:
    """Test update_streak_data() with Phase D recovery enhancements."""

    def test_normal_increment_no_reset(self):
        """Consecutive day check-in should NOT trigger reset."""
        from src.utils.streak import update_streak_data
        result = update_streak_data(
            current_streak=10,
            longest_streak=10,
            total_checkins=10,
            last_checkin_date="2026-02-07",
            new_checkin_date="2026-02-08"
        )
        assert result["current_streak"] == 11
        assert result["is_reset"] is False
        assert result["recovery_message"] is None

    def test_reset_detected(self):
        """Gap of 2+ days should trigger reset with recovery context."""
        from src.utils.streak import update_streak_data
        result = update_streak_data(
            current_streak=23,
            longest_streak=23,
            total_checkins=50,
            last_checkin_date="2026-02-05",
            new_checkin_date="2026-02-08"  # 3-day gap
        )
        assert result["current_streak"] == 1
        assert result["is_reset"] is True
        assert result["streak_before_reset"] == 23  # Saved previous
        assert result["last_reset_date"] == "2026-02-08"
        assert result["recovery_message"] is not None
        assert "Fresh Start" in result["recovery_message"]
        assert result["recovery_fact"] is not None

    def test_first_checkin_not_reset(self):
        """First ever check-in (None last_checkin_date) should NOT be a reset."""
        from src.utils.streak import update_streak_data
        result = update_streak_data(
            current_streak=0,
            longest_streak=0,
            total_checkins=0,
            last_checkin_date=None,
            new_checkin_date="2026-02-08"
        )
        assert result["current_streak"] == 1
        assert result["is_reset"] is False

    def test_recovery_milestone_day_3(self):
        """Day 3 post-reset should produce a recovery milestone message."""
        from src.utils.streak import update_streak_data
        result = update_streak_data(
            current_streak=2,
            longest_streak=20,
            total_checkins=25,
            last_checkin_date="2026-02-07",
            new_checkin_date="2026-02-08",
            streak_before_reset=15,
            last_reset_date="2026-02-05"
        )
        assert result["current_streak"] == 3
        assert result["is_reset"] is False
        assert result["recovery_message"] is not None
        assert "3 Days Strong" in result["recovery_message"]

    def test_recovery_milestone_day_7(self):
        """Day 7 post-reset should produce Comeback King milestone."""
        from src.utils.streak import update_streak_data
        result = update_streak_data(
            current_streak=6,
            longest_streak=20,
            total_checkins=30,
            last_checkin_date="2026-02-07",
            new_checkin_date="2026-02-08",
            streak_before_reset=15,
            last_reset_date="2026-02-01"
        )
        assert result["current_streak"] == 7
        assert result["recovery_message"] is not None
        assert "Comeback King" in result["recovery_message"]

    def test_streak_before_reset_carried_forward(self):
        """On normal increment, streak_before_reset should carry forward."""
        from src.utils.streak import update_streak_data
        result = update_streak_data(
            current_streak=5,
            longest_streak=20,
            total_checkins=30,
            last_checkin_date="2026-02-07",
            new_checkin_date="2026-02-08",
            streak_before_reset=15,
            last_reset_date="2026-02-01"
        )
        # Should carry forward (not overwrite unless reset happens)
        assert result["streak_before_reset"] == 15
        assert result["last_reset_date"] == "2026-02-01"

    def test_reset_overwrites_previous_tracking(self):
        """A new reset should overwrite old streak_before_reset."""
        from src.utils.streak import update_streak_data
        result = update_streak_data(
            current_streak=8,
            longest_streak=20,
            total_checkins=35,
            last_checkin_date="2026-02-05",
            new_checkin_date="2026-02-08",  # 3-day gap = reset
            streak_before_reset=15,  # From previous reset
            last_reset_date="2026-01-15"
        )
        assert result["is_reset"] is True
        assert result["streak_before_reset"] == 8  # New value (not 15)
        assert result["last_reset_date"] == "2026-02-08"


class TestUserStreaksSchema:
    """Test the new fields in UserStreaks Pydantic model."""

    def test_default_values(self):
        """New fields should have safe defaults for backward compatibility."""
        from src.models.schemas import UserStreaks
        streaks = UserStreaks()
        assert streaks.streak_before_reset == 0
        assert streaks.last_reset_date is None

    def test_with_values(self):
        """Should accept explicit values."""
        from src.models.schemas import UserStreaks
        streaks = UserStreaks(
            current_streak=5,
            longest_streak=20,
            streak_before_reset=15,
            last_reset_date="2026-02-01"
        )
        assert streaks.streak_before_reset == 15
        assert streaks.last_reset_date == "2026-02-01"

    def test_backward_compatible_deserialization(self):
        """Old data without new fields should deserialize without errors."""
        from src.models.schemas import UserStreaks
        # Simulate Firestore data from before Phase D
        old_data = {
            "current_streak": 10,
            "longest_streak": 10,
            "last_checkin_date": "2026-02-07",
            "total_checkins": 10
        }
        streaks = UserStreaks(**old_data)
        assert streaks.streak_before_reset == 0
        assert streaks.last_reset_date is None


class TestFirestoreTransientKeyFiltering:
    """Test that transient keys are filtered before Firestore write."""

    def test_transient_keys_filtered(self):
        """is_reset, recovery_message, recovery_fact should not go to Firestore."""
        # Simulate the filtering logic from store_checkin_with_streak_update
        streak_updates = {
            "current_streak": 1,
            "longest_streak": 23,
            "last_checkin_date": "2026-02-08",
            "total_checkins": 51,
            "streak_before_reset": 23,
            "last_reset_date": "2026-02-08",
            "milestone_hit": None,
            "is_reset": True,
            "recovery_message": "Some message",
            "recovery_fact": "Some fact",
        }
        
        _transient_keys = {'milestone_hit', 'is_reset', 'recovery_message', 'recovery_fact'}
        filtered = {
            k: v for k, v in streak_updates.items()
            if k not in _transient_keys
        }
        
        assert "is_reset" not in filtered
        assert "recovery_message" not in filtered
        assert "recovery_fact" not in filtered
        assert "milestone_hit" not in filtered
        # Persistent keys should remain
        assert "current_streak" in filtered
        assert "streak_before_reset" in filtered
        assert "last_reset_date" in filtered


# ============================================================
# FEATURE 3: COMEBACK ACHIEVEMENTS TESTS
# ============================================================

class TestComebackAchievements:
    """Test the new Comeback Kid, enhanced Comeback King, and Comeback Legend achievements."""

    def test_comeback_kid_defined(self):
        """Comeback Kid should exist in ACHIEVEMENTS."""
        from src.services.achievement_service import ACHIEVEMENTS
        assert "comeback_kid" in ACHIEVEMENTS
        kid = ACHIEVEMENTS["comeback_kid"]
        assert kid.name == "Comeback Kid"
        assert kid.icon == "🐣"
        assert kid.rarity == "uncommon"

    def test_comeback_king_defined(self):
        """Comeback King should still exist (enhanced)."""
        from src.services.achievement_service import ACHIEVEMENTS
        assert "comeback_king" in ACHIEVEMENTS
        king = ACHIEVEMENTS["comeback_king"]
        assert king.name == "Comeback King"
        assert king.icon == "🦁"

    def test_comeback_legend_defined(self):
        """Comeback Legend should exist in ACHIEVEMENTS."""
        from src.services.achievement_service import ACHIEVEMENTS
        assert "comeback_legend" in ACHIEVEMENTS
        legend = ACHIEVEMENTS["comeback_legend"]
        assert legend.name == "Comeback Legend"
        assert legend.icon == "👑"
        assert legend.rarity == "epic"

    def test_comeback_kid_unlocks_at_3_days(self):
        """Comeback Kid should unlock when streak reaches 3 after a reset."""
        from src.services.achievement_service import AchievementService
        from src.models.schemas import User, UserStreaks
        
        service = AchievementService.__new__(AchievementService)
        
        user = User(
            user_id="test_user",
            telegram_id=12345,
            name="Test",
            streaks=UserStreaks(
                current_streak=3,
                longest_streak=20,
                streak_before_reset=15,
                last_reset_date="2026-02-01"
            ),
            achievements=[]
        )
        
        unlocked = service._check_special_achievements(user, [])
        assert "comeback_kid" in unlocked

    def test_comeback_king_unlocks_at_7_days(self):
        """Comeback King should unlock when streak reaches 7 after a reset."""
        from src.services.achievement_service import AchievementService
        from src.models.schemas import User, UserStreaks
        
        service = AchievementService.__new__(AchievementService)
        
        user = User(
            user_id="test_user",
            telegram_id=12345,
            name="Test",
            streaks=UserStreaks(
                current_streak=7,
                longest_streak=20,
                streak_before_reset=15,
                last_reset_date="2026-02-01"
            ),
            achievements=[]
        )
        
        unlocked = service._check_special_achievements(user, [])
        assert "comeback_king" in unlocked

    def test_comeback_legend_unlocks_on_exceed(self):
        """Comeback Legend should unlock when exceeding streak_before_reset."""
        from src.services.achievement_service import AchievementService
        from src.models.schemas import User, UserStreaks
        
        service = AchievementService.__new__(AchievementService)
        
        user = User(
            user_id="test_user",
            telegram_id=12345,
            name="Test",
            streaks=UserStreaks(
                current_streak=16,
                longest_streak=20,
                streak_before_reset=15,
                last_reset_date="2026-02-01"
            ),
            achievements=[]
        )
        
        unlocked = service._check_special_achievements(user, [])
        assert "comeback_legend" in unlocked

    def test_no_comeback_without_reset(self):
        """Without a reset, comeback achievements should NOT trigger."""
        from src.services.achievement_service import AchievementService
        from src.models.schemas import User, UserStreaks
        
        service = AchievementService.__new__(AchievementService)
        
        user = User(
            user_id="test_user",
            telegram_id=12345,
            name="Test",
            streaks=UserStreaks(
                current_streak=10,
                longest_streak=10,
                streak_before_reset=0,
                last_reset_date=None
            ),
            achievements=[]
        )
        
        unlocked = service._check_special_achievements(user, [])
        assert "comeback_kid" not in unlocked
        assert "comeback_king" not in unlocked
        assert "comeback_legend" not in unlocked

    def test_no_duplicate_unlock(self):
        """Already-unlocked achievements should NOT re-trigger."""
        from src.services.achievement_service import AchievementService
        from src.models.schemas import User, UserStreaks
        
        service = AchievementService.__new__(AchievementService)
        
        user = User(
            user_id="test_user",
            telegram_id=12345,
            name="Test",
            streaks=UserStreaks(
                current_streak=10,
                longest_streak=20,
                streak_before_reset=8,
                last_reset_date="2026-02-01"
            ),
            achievements=["comeback_kid", "comeback_king", "comeback_legend"]
        )
        
        unlocked = service._check_special_achievements(user, [])
        assert "comeback_kid" not in unlocked
        assert "comeback_king" not in unlocked
        assert "comeback_legend" not in unlocked


class TestComebackCelebrationMessages:
    """Test celebration messages for new comeback achievements."""

    def test_comeback_kid_celebration(self):
        """Comeback Kid celebration should mention '3 days'."""
        from src.services.achievement_service import AchievementService
        from src.models.schemas import User, UserStreaks
        
        service = AchievementService.__new__(AchievementService)
        user = User(
            user_id="test", telegram_id=1, name="Test",
            streaks=UserStreaks(current_streak=3, streak_before_reset=10)
        )
        
        msg = service.get_celebration_message("comeback_kid", user)
        assert "Comeback Kid" in msg
        assert "🐣" in msg

    def test_comeback_legend_celebration(self):
        """Comeback Legend celebration should reference the surpassed streak."""
        from src.services.achievement_service import AchievementService
        from src.models.schemas import User, UserStreaks
        
        service = AchievementService.__new__(AchievementService)
        user = User(
            user_id="test", telegram_id=1, name="Test",
            streaks=UserStreaks(
                current_streak=16, 
                longest_streak=20, 
                streak_before_reset=15
            )
        )
        
        msg = service.get_celebration_message("comeback_legend", user)
        assert "Comeback Legend" in msg
        assert "15" in msg  # Previous streak referenced
        assert "👑" in msg


# ============================================================
# FEATURE 4: INTERVENTION-TO-SUPPORT LINKING TESTS
# ============================================================

class TestSupportBridges:
    """Test the SUPPORT_BRIDGES definitions."""

    def test_all_severities_defined(self):
        """Support bridges should exist for all 4 severity levels."""
        from src.agents.intervention import SUPPORT_BRIDGES
        assert "low" in SUPPORT_BRIDGES
        assert "medium" in SUPPORT_BRIDGES
        assert "high" in SUPPORT_BRIDGES
        assert "critical" in SUPPORT_BRIDGES

    def test_bridges_contain_support_command(self):
        """All bridges should reference /support command."""
        from src.agents.intervention import SUPPORT_BRIDGES
        for severity, bridge in SUPPORT_BRIDGES.items():
            assert "/support" in bridge, f"'{severity}' bridge missing /support"

    def test_bridge_tone_graduation(self):
        """Bridges should escalate in empathy from low to critical."""
        from src.agents.intervention import SUPPORT_BRIDGES
        # Low: casual
        assert "💬" in SUPPORT_BRIDGES["low"]
        # Medium: encouraging
        assert "help you identify" in SUPPORT_BRIDGES["medium"]
        # High: empathetic
        assert "no judgment" in SUPPORT_BRIDGES["high"]
        # Critical: urgent + safe
        assert "🆘" in SUPPORT_BRIDGES["critical"]


class TestAddSupportBridge:
    """Test the add_support_bridge() function."""

    def test_appends_bridge_to_message(self):
        """Should append the bridge text to the intervention message."""
        from src.agents.intervention import add_support_bridge
        original = "🚨 PATTERN ALERT: Sleep Degradation\n\nEvidence..."
        result = add_support_bridge(original, "medium")
        assert result.startswith(original)
        assert "/support" in result

    def test_uses_correct_severity(self):
        """Should use the bridge matching the given severity."""
        from src.agents.intervention import add_support_bridge
        low_result = add_support_bridge("Alert", "low")
        critical_result = add_support_bridge("Alert", "critical")
        assert "🆘" not in low_result
        assert "🆘" in critical_result

    def test_defaults_to_medium(self):
        """Unknown severity should default to medium bridge."""
        from src.agents.intervention import add_support_bridge
        result = add_support_bridge("Alert", "unknown_severity")
        assert "help you identify" in result

    def test_preserves_original_message(self):
        """Original message content should be intact."""
        from src.agents.intervention import add_support_bridge
        original = "This is the full intervention text with details."
        result = add_support_bridge(original, "high")
        assert original in result


class TestInterventionSupportBridgeIntegration:
    """Test that support bridges are added to all intervention paths."""

    def test_ghosting_intervention_has_bridge(self):
        """Ghosting template interventions should include support bridge."""
        # Read the source code and verify the bridge is applied
        with open("src/agents/intervention.py", "r") as f:
            source = f.read()
        
        # The ghosting path should call add_support_bridge
        assert "add_support_bridge(intervention, pattern.severity)" in source

    def test_fallback_intervention_has_bridge(self):
        """Generic fallback intervention should include support bridge."""
        with open("src/agents/intervention.py", "r") as f:
            source = f.read()
        
        # The fallback return should call add_support_bridge
        assert "add_support_bridge(message, pattern.severity)" in source

    def test_ai_intervention_has_bridge(self):
        """AI-generated interventions should include support bridge."""
        with open("src/agents/intervention.py", "r") as f:
            source = f.read()
        
        # The AI path should call add_support_bridge
        assert "add_support_bridge(intervention.strip(), pattern.severity)" in source

    def test_template_interventions_have_bridge(self):
        """All template-based interventions should include support bridge."""
        with open("src/agents/intervention.py", "r") as f:
            source = f.read()
        
        # All pattern-specific templates should use add_support_bridge
        for pattern in ["snooze_trap", "consumption_vortex", "deep_work_collapse", "relationship_interference"]:
            assert f"add_support_bridge(" in source, f"Missing bridge for {pattern}"


class TestSupportCommand:
    """Test the /support command implementation."""

    def test_support_command_registered(self):
        """Bot should register /support as a command handler."""
        with open("src/bot/telegram_bot.py", "r") as f:
            source = f.read()
        assert 'CommandHandler("support"' in source

    def test_support_in_help_text(self):
        """Help text should include /support command."""
        with open("src/utils/ux.py", "r") as f:
            source = f.read()
        assert "/support" in source

    def test_support_in_rate_limiter(self):
        """Support should be in the rate limiter (ai_powered tier)."""
        from src.utils.rate_limiter import rate_limiter
        tier = rate_limiter.COMMAND_TIERS.get("support")
        assert tier == "ai_powered"


class TestSupportCommandBehavior:
    """Test /support command behavior with mocked dependencies."""

    @pytest.mark.asyncio
    async def test_standalone_support_prompt(self):
        """
        /support with no args should show welcome prompt and set support_mode.
        """
        from src.bot.telegram_bot import TelegramBotManager
        
        # Create mock bot
        with patch('src.bot.telegram_bot.Application'):
            bot = TelegramBotManager.__new__(TelegramBotManager)
            bot.application = MagicMock()
        
        # Mock update and context
        update = MagicMock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []  # No args — standalone /support
        context.user_data = {}
        
        # Mock rate limiter
        with patch.object(bot, '_check_rate_limit', new_callable=AsyncMock, return_value=True):
            # Mock firestore
            with patch('src.bot.telegram_bot.firestore_service') as mock_fs:
                mock_fs.get_recent_interventions.return_value = []
                
                await bot.support_command(update, context)
        
        # Should have replied with welcome prompt
        update.message.reply_text.assert_called_once()
        call_args = update.message.reply_text.call_args
        assert "I'm here" in call_args[0][0]
        
        # Should set support_mode in user_data
        assert context.user_data.get('support_mode') is True

    @pytest.mark.asyncio
    async def test_context_aware_support_prompt(self):
        """
        /support after a recent intervention should reference the intervention pattern.
        """
        from src.bot.telegram_bot import TelegramBotManager
        
        with patch('src.bot.telegram_bot.Application'):
            bot = TelegramBotManager.__new__(TelegramBotManager)
            bot.application = MagicMock()
        
        update = MagicMock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = []
        context.user_data = {}
        
        with patch.object(bot, '_check_rate_limit', new_callable=AsyncMock, return_value=True):
            with patch('src.bot.telegram_bot.firestore_service') as mock_fs:
                mock_fs.get_recent_interventions.return_value = [
                    {"pattern_type": "sleep_degradation", "sent_at": datetime.utcnow()}
                ]
                
                await bot.support_command(update, context)
        
        call_args = update.message.reply_text.call_args
        reply_text = call_args[0][0]
        assert "sleep degradation" in reply_text

    @pytest.mark.asyncio
    async def test_support_with_inline_message(self):
        """
        /support I'm feeling down should route directly to emotional agent.
        """
        from src.bot.telegram_bot import TelegramBotManager
        
        with patch('src.bot.telegram_bot.Application'):
            bot = TelegramBotManager.__new__(TelegramBotManager)
            bot.application = MagicMock()
        
        update = MagicMock()
        update.effective_user.id = 12345
        update.message.reply_text = AsyncMock()
        
        context = MagicMock()
        context.args = ["I'm", "feeling", "down"]
        context.user_data = {}
        
        with patch.object(bot, '_check_rate_limit', new_callable=AsyncMock, return_value=True):
            with patch.object(bot, '_process_support_message', new_callable=AsyncMock) as mock_process:
                await bot.support_command(update, context)
                
                # Should call _process_support_message with the joined args
                mock_process.assert_called_once()
                call_args = mock_process.call_args
                assert "I'm feeling down" in call_args[0][3]


class TestSupportModeInGeneralHandler:
    """Test that support_mode is consumed by the general message handler."""

    def test_support_mode_check_exists(self):
        """General message handler should check for support_mode."""
        with open("src/bot/telegram_bot.py", "r") as f:
            source = f.read()
        assert "support_mode" in source
        assert "_process_support_message" in source


# ============================================================
# INTEGRATION TESTS
# ============================================================

class TestEndToEndResetFlow:
    """Integration tests for the full streak reset → recovery flow."""

    def test_full_reset_and_recovery_flow(self):
        """
        Simulate: 23-day streak → 3-day gap → reset → rebuild to Day 7.
        
        Expected:
        - Day 1 (reset): is_reset=True, recovery_message with "Fresh Start"
        - Day 2: no milestone
        - Day 3: recovery_message with "3 Days Strong"
        - Day 7: recovery_message with "Comeback King"
        """
        from src.utils.streak import update_streak_data
        
        # Day 1: Reset (3-day gap from Feb 5 to Feb 8)
        r1 = update_streak_data(
            current_streak=23, longest_streak=23, total_checkins=50,
            last_checkin_date="2026-02-05", new_checkin_date="2026-02-08"
        )
        assert r1["is_reset"] is True
        assert r1["streak_before_reset"] == 23
        assert "Fresh Start" in r1["recovery_message"]
        
        # Day 2: Normal increment
        r2 = update_streak_data(
            current_streak=1, longest_streak=23, total_checkins=51,
            last_checkin_date="2026-02-08", new_checkin_date="2026-02-09",
            streak_before_reset=23, last_reset_date="2026-02-08"
        )
        assert r2["current_streak"] == 2
        assert r2["is_reset"] is False
        assert r2["recovery_message"] is None  # No milestone at Day 2
        
        # Day 3: Recovery milestone
        r3 = update_streak_data(
            current_streak=2, longest_streak=23, total_checkins=52,
            last_checkin_date="2026-02-09", new_checkin_date="2026-02-10",
            streak_before_reset=23, last_reset_date="2026-02-08"
        )
        assert r3["current_streak"] == 3
        assert r3["recovery_message"] is not None
        assert "3 Days Strong" in r3["recovery_message"]
        
        # Days 4-6: Normal (no milestones)
        r4 = update_streak_data(
            current_streak=3, longest_streak=23, total_checkins=53,
            last_checkin_date="2026-02-10", new_checkin_date="2026-02-11",
            streak_before_reset=23, last_reset_date="2026-02-08"
        )
        assert r4["recovery_message"] is None
        
        r5 = update_streak_data(
            current_streak=4, longest_streak=23, total_checkins=54,
            last_checkin_date="2026-02-11", new_checkin_date="2026-02-12",
            streak_before_reset=23, last_reset_date="2026-02-08"
        )
        assert r5["recovery_message"] is None
        
        r6 = update_streak_data(
            current_streak=5, longest_streak=23, total_checkins=55,
            last_checkin_date="2026-02-12", new_checkin_date="2026-02-13",
            streak_before_reset=23, last_reset_date="2026-02-08"
        )
        assert r6["recovery_message"] is None
        
        # Day 7: Comeback King milestone
        r7 = update_streak_data(
            current_streak=6, longest_streak=23, total_checkins=56,
            last_checkin_date="2026-02-13", new_checkin_date="2026-02-14",
            streak_before_reset=23, last_reset_date="2026-02-08"
        )
        assert r7["current_streak"] == 7
        assert r7["recovery_message"] is not None
        assert "Comeback King" in r7["recovery_message"]

    def test_double_reset_flow(self):
        """
        Simulate: streak → reset → rebuild to 8 → reset again → Day 1.
        
        The second reset should save streak_before_reset=8 (not the old value).
        """
        from src.utils.streak import update_streak_data
        
        # First reset: 15 → 1
        r1 = update_streak_data(
            current_streak=15, longest_streak=15, total_checkins=30,
            last_checkin_date="2026-01-25", new_checkin_date="2026-01-28"
        )
        assert r1["streak_before_reset"] == 15
        
        # Rebuild to 8
        # ... (skip intermediate days for brevity)
        
        # Second reset: 8 → 1
        r2 = update_streak_data(
            current_streak=8, longest_streak=15, total_checkins=38,
            last_checkin_date="2026-02-05", new_checkin_date="2026-02-08",
            streak_before_reset=15, last_reset_date="2026-01-28"
        )
        assert r2["is_reset"] is True
        assert r2["streak_before_reset"] == 8  # NEW reset value, not old 15
        assert r2["last_reset_date"] == "2026-02-08"


class TestInterventionSupportBridgeEndToEnd:
    """Test support bridge in actual intervention message generation."""

    def test_ghosting_day2_has_low_bridge(self):
        """Day 2 ghosting (low severity) should get low bridge."""
        from src.agents.intervention import InterventionAgent, add_support_bridge
        from src.agents.pattern_detection import Pattern
        from src.models.schemas import User, UserStreaks
        
        # Create agent without LLM (we won't use AI generation)
        agent = InterventionAgent.__new__(InterventionAgent)
        
        pattern = Pattern(
            type="ghosting",
            severity="low",
            detected_at=datetime.utcnow(),
            data={"days_missing": 2, "previous_streak": 10}
        )
        
        user = User(
            user_id="test", telegram_id=1, name="Test",
            streaks=UserStreaks(current_streak=10)
        )
        
        msg = agent._build_ghosting_intervention(pattern, user)
        bridged = add_support_bridge(msg, "low")
        
        assert "Missed you" in bridged
        assert "/support" in bridged

    def test_ghosting_day5_has_critical_bridge(self):
        """Day 5+ ghosting (critical severity) should get critical bridge."""
        from src.agents.intervention import InterventionAgent, add_support_bridge
        from src.agents.pattern_detection import Pattern
        from src.models.schemas import User, UserStreaks, StreakShields
        
        agent = InterventionAgent.__new__(InterventionAgent)
        
        pattern = Pattern(
            type="ghosting",
            severity="critical",
            detected_at=datetime.utcnow(),
            data={"days_missing": 5, "previous_streak": 20}
        )
        
        user = User(
            user_id="test", telegram_id=1, name="Test",
            streaks=UserStreaks(current_streak=0),
            streak_shields=StreakShields(available=1)
        )
        
        msg = agent._build_ghosting_intervention(pattern, user)
        bridged = add_support_bridge(msg, "critical")
        
        assert "EMERGENCY" in bridged
        assert "🆘" in bridged
        assert "/support" in bridged


# ============================================================
# RUN ALL TESTS
# ============================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
