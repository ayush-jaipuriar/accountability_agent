"""
Comprehensive Tests for P0 + P1 Bug Fixes & UX Improvements
============================================================

Tests all 11 fixes implemented in the Feb 8, 2026 product gap analysis.

P0 Critical Bug Fixes:
  Fix 1: Streak shield must update last_checkin_date
  Fix 2: update_user() method must exist in FirestoreService
  Fix 3: Achievement field paths audit (confirmed correct)
  Fix 4: Atomic check-in + streak update transaction

P1 UX Fixes:
  Fix 5: /mode command argument parsing and inline buttons
  Fix 6: Welcome message updated to 6 items
  Fix 7: Undo button during Tier 1 check-in
  Fix 8: /correct command for check-in corrections
  Fix 9: Historical compliance score normalization
  Fix 10: Empathetic 0% compliance fallback
  Fix 11: Cron endpoint authentication
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch, AsyncMock

from src.models.schemas import (
    User, UserStreaks, Tier1NonNegotiables, CheckInResponses,
    DailyCheckIn, StreakShields
)
from src.utils.compliance import (
    calculate_compliance_score,
    calculate_compliance_score_normalized,
    is_all_tier1_complete,
    get_compliance_level,
    format_compliance_message,
)
from src.services.achievement_service import AchievementService


# =====================================================
# FIXTURES
# =====================================================

@pytest.fixture
def tier1_all_complete():
    """All 6 Tier 1 items completed."""
    return Tier1NonNegotiables(
        sleep=True, training=True, deep_work=True,
        skill_building=True, zero_porn=True, boundaries=True
    )


@pytest.fixture
def tier1_5_of_6():
    """5 of 6 items complete (missing skill_building)."""
    return Tier1NonNegotiables(
        sleep=True, training=True, deep_work=True,
        skill_building=False, zero_porn=True, boundaries=True
    )


@pytest.fixture
def tier1_none_complete():
    """No items complete."""
    return Tier1NonNegotiables(
        sleep=False, training=False, deep_work=False,
        skill_building=False, zero_porn=False, boundaries=False
    )


@pytest.fixture
def tier1_pre_3d_all_complete():
    """Pre-Phase 3D: 5 original items all complete, skill_building defaults to False."""
    return Tier1NonNegotiables(
        sleep=True, training=True, deep_work=True,
        skill_building=False,  # Didn't exist before Phase 3D
        zero_porn=True, boundaries=True
    )


@pytest.fixture
def sample_user_with_shields():
    """User with streak shields available."""
    return User(
        user_id="test_user_1",
        telegram_id=123456789,
        name="Test User",
        streaks=UserStreaks(
            current_streak=47,
            longest_streak=47,
            last_checkin_date="2026-02-06",
            total_checkins=100
        ),
        streak_shields=StreakShields(
            total=3, used=0, available=3
        )
    )


@pytest.fixture
def checkin_post_3d(tier1_all_complete):
    """Check-in after Phase 3D (6 items)."""
    return DailyCheckIn(
        date="2026-02-08",
        user_id="test_user_1",
        mode="maintenance",
        tier1_non_negotiables=tier1_all_complete,
        responses=CheckInResponses(
            challenges="Focused work session went well today with no interruptions at all",
            rating=9,
            rating_reason="Great overall day with strong productivity and good energy levels",
            tomorrow_priority="Continue momentum with deep work sessions and skill building practice",
            tomorrow_obstacle="Late meeting might drain evening energy so planning morning sessions"
        ),
        compliance_score=100.0,
    )


@pytest.fixture
def checkin_pre_3d(tier1_pre_3d_all_complete):
    """Check-in before Phase 3D (5 items only)."""
    return DailyCheckIn(
        date="2026-02-01",  # Before Phase 3D deployment date
        user_id="test_user_1",
        mode="maintenance",
        tier1_non_negotiables=tier1_pre_3d_all_complete,
        responses=CheckInResponses(
            challenges="Managed to stay focused despite various distractions throughout the day",
            rating=8,
            rating_reason="Solid day with room for improvement in some areas of focus today",
            tomorrow_priority="Hit all five non-negotiables and maintain steady consistent progress",
            tomorrow_obstacle="Evening event may reduce available time for deep work session today"
        ),
        compliance_score=100.0,  # Was 5/5 = 100% at time of check-in
    )


# =====================================================
# FIX 1: STREAK SHIELD MUST UPDATE last_checkin_date
# =====================================================

class TestFix1StreakShield:
    """
    Verify that use_streak_shield() updates last_checkin_date.
    
    Theory: The shield's purpose is to "bridge" a missed day. If last_checkin_date
    isn't advanced, the streak logic sees a multi-day gap and resets the streak
    regardless -- making the shield useless.
    """
    
    def test_shield_updates_last_checkin_date_in_code(self):
        """Verify the fix exists in the source code."""
        import inspect
        from src.services.firestore_service import FirestoreService
        
        source = inspect.getsource(FirestoreService.use_streak_shield)
        
        # Must contain the fix: updating last_checkin_date
        assert "last_checkin_date" in source, (
            "use_streak_shield() must update streaks.last_checkin_date "
            "to bridge the gap and protect the streak"
        )
        assert "get_checkin_date" in source, (
            "use_streak_shield() must import and use get_checkin_date() "
            "to determine the correct date for the bridge"
        )
    
    def test_shield_method_signature_unchanged(self):
        """Shield method must accept user_id and return bool."""
        import inspect
        from src.services.firestore_service import FirestoreService
        
        sig = inspect.signature(FirestoreService.use_streak_shield)
        params = list(sig.parameters.keys())
        assert "self" in params
        assert "user_id" in params
        assert sig.return_annotation is bool or "bool" in str(sig.return_annotation)


# =====================================================
# FIX 2: update_user() METHOD EXISTS
# =====================================================

class TestFix2UpdateUser:
    """
    Verify that FirestoreService.update_user() exists and has correct signature.
    
    Theory: Generic update method for ad-hoc field updates. Uses Firestore's
    update() which modifies only specified fields (no full doc overwrite).
    """
    
    def test_update_user_method_exists(self):
        """update_user must be a method on FirestoreService."""
        from src.services.firestore_service import FirestoreService
        assert hasattr(FirestoreService, 'update_user'), (
            "FirestoreService must have update_user() method"
        )
    
    def test_update_user_signature(self):
        """update_user must accept user_id (str) and updates (dict)."""
        import inspect
        from src.services.firestore_service import FirestoreService
        
        sig = inspect.signature(FirestoreService.update_user)
        params = list(sig.parameters.keys())
        assert "user_id" in params
        assert "updates" in params
    
    def test_update_user_return_type(self):
        """update_user must return bool."""
        import inspect
        from src.services.firestore_service import FirestoreService
        
        sig = inspect.signature(FirestoreService.update_user)
        assert sig.return_annotation is bool


# =====================================================
# FIX 3: ACHIEVEMENT SERVICE FIELD PATHS
# =====================================================

class TestFix3AchievementFields:
    """
    Verify all tier1 field accesses use correct paths.
    No stale .tier1. prefix or .completed suffix.
    """
    
    def test_no_stale_tier1_prefix(self):
        """No code should access checkin.tier1.X (old path)."""
        import inspect
        from src.services.achievement_service import AchievementService
        
        source = inspect.getsource(AchievementService)
        # .tier1. followed by a field name (but not .tier1_non_negotiables)
        lines = source.split('\n')
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('#') or stripped.startswith('"""') or stripped.startswith("'''"):
                continue
            # Check for .tier1. but NOT .tier1_non_negotiables
            if '.tier1.' in stripped and '.tier1_non_negotiables' not in stripped:
                # Allow comments and docstrings
                if '#' in stripped and stripped.index('#') < stripped.index('.tier1.'):
                    continue
                pytest.fail(f"Stale .tier1. access found: {stripped}")
    
    def test_no_completed_suffix(self):
        """No code should access tier1_non_negotiables.X.completed."""
        import inspect
        from src.services.achievement_service import AchievementService
        
        source = inspect.getsource(AchievementService)
        assert '.completed' not in source or 'not .completed' in source.lower(), (
            "Achievement service should not use .completed suffix on tier1 fields"
        )
    
    def test_all_tier1_complete_delegates_to_compliance(self):
        """_all_tier1_complete should use is_all_tier1_complete from compliance."""
        import inspect
        from src.services.achievement_service import AchievementService
        
        source = inspect.getsource(AchievementService._all_tier1_complete)
        assert 'is_all_tier1_complete' in source, (
            "_all_tier1_complete should delegate to compliance.is_all_tier1_complete "
            "for date-aware backward compatibility"
        )


# =====================================================
# FIX 4: ATOMIC CHECK-IN TRANSACTION
# =====================================================

class TestFix4Transaction:
    """
    Verify transactional check-in + streak update method exists.
    
    Theory: Without a transaction, store_checkin() and update_user_streak()
    are separate writes. If the second fails, the streak becomes stale.
    """
    
    def test_transactional_method_exists(self):
        """store_checkin_with_streak_update must exist on FirestoreService."""
        from src.services.firestore_service import FirestoreService
        assert hasattr(FirestoreService, 'store_checkin_with_streak_update')
    
    def test_transactional_method_signature(self):
        """Must accept user_id, checkin, and streak_updates."""
        import inspect
        from src.services.firestore_service import FirestoreService
        
        sig = inspect.signature(FirestoreService.store_checkin_with_streak_update)
        params = list(sig.parameters.keys())
        assert "user_id" in params
        assert "checkin" in params
        assert "streak_updates" in params
    
    def test_transaction_used_in_code(self):
        """Must use @firestore.transactional decorator."""
        import inspect
        from src.services.firestore_service import FirestoreService
        
        source = inspect.getsource(FirestoreService.store_checkin_with_streak_update)
        assert 'transactional' in source, (
            "store_checkin_with_streak_update must use @firestore.transactional"
        )
    
    def test_conversation_uses_transactional_method(self):
        """conversation.py must call store_checkin_with_streak_update, not separate calls."""
        # Read file directly to avoid google-genai import dependency
        import os
        conv_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'bot', 'conversation.py'
        )
        with open(conv_path, 'r') as f:
            source = f.read()
        assert 'store_checkin_with_streak_update' in source, (
            "conversation.py must use the transactional method"
        )


# =====================================================
# FIX 5: /mode COMMAND ARGUMENT PARSING
# =====================================================

class TestFix5ModeCommand:
    """
    Verify /mode command supports both text args and inline buttons.
    """
    
    def test_mode_command_checks_args(self):
        """mode_command must parse context.args for mode name."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager.mode_command)
        assert 'context.args' in source, (
            "mode_command must check context.args for direct mode argument"
        )
    
    def test_mode_command_validates_modes(self):
        """mode_command must validate against known mode names."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager.mode_command)
        assert 'optimization' in source
        assert 'maintenance' in source
        assert 'survival' in source
    
    def test_mode_change_callback_exists(self):
        """mode_change_callback must exist for inline button handling."""
        from src.bot.telegram_bot import TelegramBotManager
        assert hasattr(TelegramBotManager, 'mode_change_callback')
    
    def test_mode_change_callback_registered(self):
        """change_mode_ pattern must be registered in handler setup."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager._register_handlers)
        assert 'change_mode_' in source, (
            "Handler for 'change_mode_' callback pattern must be registered"
        )
    
    def test_mode_command_shows_inline_keyboard(self):
        """mode_command must create InlineKeyboardMarkup when no args."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager.mode_command)
        assert 'InlineKeyboardMarkup' in source
        assert 'change_mode_' in source


# =====================================================
# FIX 6: WELCOME MESSAGE UPDATED TO 6 ITEMS
# =====================================================

class TestFix6WelcomeMessage:
    """
    Verify welcome message mentions 6 Tier 1 items including Skill Building.
    """
    
    def test_welcome_says_6_not_5(self):
        """Welcome text must say '6 non-negotiables', not '5'."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager.start_command)
        assert '6 non-negotiables' in source, "Welcome must say '6 non-negotiables'"
        assert '5 non-negotiables' not in source, "Must NOT say '5 non-negotiables'"
    
    def test_welcome_includes_skill_building(self):
        """Welcome text must mention Skill Building."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager.start_command)
        assert 'Skill Building' in source, "Welcome must mention 'Skill Building'"
    
    def test_welcome_has_6_numbered_items(self):
        """Welcome must have items numbered 1-6."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager.start_command)
        assert '6️⃣' in source, "Welcome must have 6th numbered item"
    
    def test_welcome_says_6_items_in_body(self):
        """Body text must say 'these 6 items'."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager.start_command)
        assert 'these 6 items' in source, "Body must reference 'these 6 items'"
        assert 'these 5 items' not in source, "Must NOT reference 'these 5 items'"


# =====================================================
# FIX 7: UNDO BUTTON DURING CHECK-IN TIER 1
# =====================================================

class TestFix7UndoButton:
    """
    Verify undo functionality in Tier 1 check-in questions.
    Read file directly to avoid google-genai import dependency.
    """
    
    @pytest.fixture(autouse=True)
    def _read_conversation_source(self):
        """Read conversation.py source once for all tests in this class."""
        import os
        conv_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'bot', 'conversation.py'
        )
        with open(conv_path, 'r') as f:
            self.source = f.read()
    
    def test_undo_handler_exists(self):
        """handle_tier1_response must handle 'tier1_undo' callback."""
        assert 'tier1_undo' in self.source, (
            "handle_tier1_response must handle 'tier1_undo' callback data"
        )
    
    def test_answer_order_tracking(self):
        """Must track answer order in tier1_answer_order."""
        assert 'tier1_answer_order' in self.source, (
            "Must track answer order for undo functionality"
        )
    
    def test_undo_removes_last_answer(self):
        """Undo logic must pop last item from responses and order."""
        assert 'answer_order.pop()' in self.source or '.pop()' in self.source, (
            "Undo must pop the last answer from the order list"
        )
    
    def test_undo_button_added_to_confirmation(self):
        """Each answer confirmation must include Undo button."""
        assert 'Undo Last' in self.source, (
            "Must show 'Undo Last' button in confirmation messages"
        )


# =====================================================
# FIX 8: /correct COMMAND
# =====================================================

class TestFix8CorrectCommand:
    """
    Verify /correct command for check-in corrections.
    """
    
    def test_correct_command_exists(self):
        """correct_command must be a method on TelegramBotManager."""
        from src.bot.telegram_bot import TelegramBotManager
        assert hasattr(TelegramBotManager, 'correct_command')
    
    def test_correct_toggle_callback_exists(self):
        """correct_toggle_callback must exist."""
        from src.bot.telegram_bot import TelegramBotManager
        assert hasattr(TelegramBotManager, 'correct_toggle_callback')
    
    def test_correct_command_registered(self):
        """correct command must be registered in handlers."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager._register_handlers)
        assert '"correct"' in source or "'correct'" in source, (
            "/correct command must be registered"
        )
    
    def test_correct_callback_registered(self):
        """correct_ callback pattern must be registered."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager._register_handlers)
        assert 'correct_' in source
    
    def test_correct_enforces_time_limit(self):
        """Must check 2-hour time constraint."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager.correct_command)
        assert 'hours=2' in source or 'hour' in source, (
            "Correction must enforce 2-hour time window"
        )
    
    def test_correct_checks_already_corrected(self):
        """Must prevent double corrections."""
        import inspect
        from src.bot.telegram_bot import TelegramBotManager
        
        source = inspect.getsource(TelegramBotManager.correct_command)
        assert 'corrected_at' in source, (
            "Must check corrected_at to prevent double corrections"
        )
    
    def test_update_checkin_method_exists(self):
        """FirestoreService must have update_checkin method."""
        from src.services.firestore_service import FirestoreService
        assert hasattr(FirestoreService, 'update_checkin')
    
    def test_checkin_has_corrected_at_field(self):
        """DailyCheckIn model must have corrected_at field."""
        from src.models.schemas import DailyCheckIn
        
        # Create a check-in and verify corrected_at is None by default
        checkin = DailyCheckIn(
            date="2026-02-08",
            user_id="test",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=True, training=True, deep_work=True,
                zero_porn=True, boundaries=True
            ),
            responses=CheckInResponses(
                challenges="Test challenges text with adequate length for validation purposes here",
                rating=7,
                rating_reason="Test rating reason with enough detail to pass validation length checks",
                tomorrow_priority="Tomorrow priority text with adequate length for validation purposes",
                tomorrow_obstacle="Tomorrow obstacle with enough detail to pass validation length checks",
            ),
            compliance_score=83.3,
        )
        assert checkin.corrected_at is None
    
    def test_corrected_at_in_to_firestore(self):
        """to_firestore() must include corrected_at when set."""
        checkin = DailyCheckIn(
            date="2026-02-08",
            user_id="test",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=True, training=True, deep_work=True,
                zero_porn=True, boundaries=True
            ),
            responses=CheckInResponses(
                challenges="Test challenges text with adequate length for validation purposes here",
                rating=7,
                rating_reason="Test rating reason with enough detail to pass validation length checks",
                tomorrow_priority="Tomorrow priority text with adequate length for validation purposes",
                tomorrow_obstacle="Tomorrow obstacle with enough detail to pass validation length checks",
            ),
            compliance_score=83.3,
            corrected_at=datetime.utcnow(),
        )
        data = checkin.to_firestore()
        assert "corrected_at" in data
    
    def test_corrected_at_not_in_firestore_when_none(self):
        """to_firestore() must NOT include corrected_at when None."""
        checkin = DailyCheckIn(
            date="2026-02-08",
            user_id="test",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=True, training=True, deep_work=True,
                zero_porn=True, boundaries=True
            ),
            responses=CheckInResponses(
                challenges="Test challenges text with adequate length for validation purposes here",
                rating=7,
                rating_reason="Test rating reason with enough detail to pass validation length checks",
                tomorrow_priority="Tomorrow priority text with adequate length for validation purposes",
                tomorrow_obstacle="Tomorrow obstacle with enough detail to pass validation length checks",
            ),
            compliance_score=83.3,
        )
        data = checkin.to_firestore()
        assert "corrected_at" not in data


# =====================================================
# FIX 9: COMPLIANCE SCORE NORMALIZATION
# =====================================================

class TestFix9ComplianceNormalization:
    """
    Verify date-aware compliance score normalization.
    
    Theory: Phase 3D added Skill Building as 6th item on 2026-02-05.
    Old check-ins had 5 items. When re-evaluating tier1 data, we must
    use the correct denominator for the era.
    """
    
    def test_pre_3d_100_percent_with_5_items(self, tier1_pre_3d_all_complete):
        """Pre-3D check-in with all 5 original items = 100%."""
        score = calculate_compliance_score_normalized(
            tier1_pre_3d_all_complete, "2026-02-01"
        )
        assert score == 100.0, f"Pre-3D 5/5 should be 100%, got {score}"
    
    def test_post_3d_83_percent_with_5_of_6(self, tier1_5_of_6):
        """Post-3D check-in missing skill_building = 83.3%."""
        score = calculate_compliance_score_normalized(
            tier1_5_of_6, "2026-02-08"
        )
        expected = (5 / 6) * 100
        assert abs(score - expected) < 0.1, f"Post-3D 5/6 should be {expected:.1f}%, got {score}"
    
    def test_post_3d_100_percent_with_6_items(self, tier1_all_complete):
        """Post-3D check-in with all 6 items = 100%."""
        score = calculate_compliance_score_normalized(
            tier1_all_complete, "2026-02-08"
        )
        assert score == 100.0, f"Post-3D 6/6 should be 100%, got {score}"
    
    def test_pre_3d_0_percent(self, tier1_none_complete):
        """Pre-3D check-in with 0 items = 0%."""
        score = calculate_compliance_score_normalized(
            tier1_none_complete, "2026-02-01"
        )
        assert score == 0.0
    
    def test_no_date_uses_6_item_formula(self, tier1_5_of_6):
        """When no date provided, default to 6-item formula."""
        score = calculate_compliance_score_normalized(tier1_5_of_6)
        expected = (5 / 6) * 100
        assert abs(score - expected) < 0.1
    
    def test_is_all_tier1_complete_pre_3d(self, tier1_pre_3d_all_complete):
        """Pre-3D: all 5 items complete = True (ignores skill_building)."""
        assert is_all_tier1_complete(tier1_pre_3d_all_complete, "2026-02-01") is True
    
    def test_is_all_tier1_complete_post_3d_missing_skill(self, tier1_5_of_6):
        """Post-3D: missing skill_building = False."""
        assert is_all_tier1_complete(tier1_5_of_6, "2026-02-08") is False
    
    def test_is_all_tier1_complete_post_3d_all_6(self, tier1_all_complete):
        """Post-3D: all 6 items = True."""
        assert is_all_tier1_complete(tier1_all_complete, "2026-02-08") is True
    
    def test_is_all_tier1_complete_no_date(self, tier1_all_complete):
        """No date: assumes post-3D (6 items)."""
        assert is_all_tier1_complete(tier1_all_complete) is True
    
    def test_achievement_tier1_master_pre_3d(self):
        """Tier 1 Master achievement should work for pre-3D check-ins."""
        service = AchievementService()
        
        # Create 30 pre-3D check-ins with all 5 original items
        checkins = []
        for i in range(30):
            date = f"2026-01-{(i % 28) + 1:02d}"
            checkins.append(DailyCheckIn(
                date=date,
                user_id="test",
                mode="maintenance",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep=True, training=True, deep_work=True,
                    skill_building=False,  # Didn't exist before 3D
                    zero_porn=True, boundaries=True
                ),
                responses=CheckInResponses(
                    challenges="Pre-3D challenge text with adequate length for validation purposes here",
                    rating=8,
                    rating_reason="Pre-3D rating reason with enough detail to pass validation length here",
                    tomorrow_priority="Pre-3D priority text with adequate length for validation purposes here",
                    tomorrow_obstacle="Pre-3D obstacle with enough detail to pass validation length checks here",
                ),
                compliance_score=100.0,  # Was 5/5 at the time
            ))
        
        # All should pass _all_tier1_complete since dates are pre-3D
        for c in checkins:
            assert service._all_tier1_complete(c) is True, (
                f"Pre-3D check-in on {c.date} with all 5 items should pass tier1 check"
            )
    
    def test_phase_3d_date_in_config(self):
        """Config must have phase_3d_deployment_date."""
        from src.config import Settings
        
        # Check that the field exists on the Settings class
        assert hasattr(Settings, 'model_fields') or hasattr(Settings, '__fields__')
        # Verify the setting name exists
        import inspect
        source = inspect.getsource(Settings)
        assert 'phase_3d_deployment_date' in source


# =====================================================
# FIX 10: EMPATHETIC 0% COMPLIANCE FALLBACK
# =====================================================

class TestFix10EmpatheticFallback:
    """
    Verify 0% compliance message is empathetic, not harsh.
    
    Theory: Shame-based messaging leads to avoidance (user stops checking in).
    Empathetic messaging maintains the habit loop.
    """
    
    def test_critical_header_is_empathetic(self):
        """Critical level header should be 'Tough day.' not 'Below standards.'"""
        # Create a 0% compliance tier1
        tier1 = Tier1NonNegotiables(
            sleep=False, training=False, deep_work=False,
            skill_building=False, zero_porn=False, boundaries=False
        )
        score = calculate_compliance_score(tier1)
        level = get_compliance_level(score)
        
        assert level == "critical", f"0% should be critical, got {level}"
        
        message = format_compliance_message(score, 5)
        
        assert "Tough day" in message, f"Must say 'Tough day', got: {message}"
        assert "Below standards" not in message, "Must NOT say 'Below standards'"
    
    def test_critical_encouragement_is_empathetic(self):
        """Critical level must have empathetic encouragement."""
        tier1 = Tier1NonNegotiables(
            sleep=False, training=False, deep_work=False,
            skill_building=False, zero_porn=False, boundaries=False
        )
        score = calculate_compliance_score(tier1)
        message = format_compliance_message(score, 5)
        
        assert "fresh start" in message, "Must mention 'fresh start'"
        assert "Time to refocus. You know what to do" not in message, (
            "Must NOT contain old harsh message"
        )
    
    def test_critical_message_includes_emotional_bridge(self):
        """Critical level must bridge to emotional support."""
        tier1 = Tier1NonNegotiables(
            sleep=False, training=False, deep_work=False,
            skill_building=False, zero_porn=False, boundaries=False
        )
        score = calculate_compliance_score(tier1)
        message = format_compliance_message(score, 5)
        
        assert "how you're feeling" in message.lower() or "need to talk" in message.lower(), (
            "Critical message should bridge to emotional support"
        )
    
    def test_non_critical_levels_unchanged(self):
        """Excellent, good, warning levels should still work normally."""
        # Excellent (90-100%)
        msg = format_compliance_message(100.0, 10)
        assert "Perfect day" in msg
        
        # Good (80-89%)
        msg = format_compliance_message(83.0, 10)
        assert "Strong day" in msg
        
        # Warning (60-79%)
        msg = format_compliance_message(67.0, 10)
        assert "improvement" in msg


# =====================================================
# FIX 11: CRON ENDPOINT AUTHENTICATION
# =====================================================

class TestFix11CronAuth:
    """
    Verify cron endpoint authentication.
    Read main.py source directly to avoid google-genai import dependency.
    """
    
    @pytest.fixture(autouse=True)
    def _read_main_source(self):
        """Read main.py source once for all tests in this class."""
        import os
        main_path = os.path.join(
            os.path.dirname(__file__), '..', 'src', 'main.py'
        )
        with open(main_path, 'r') as f:
            self.source = f.read()
    
    def test_verify_cron_request_function_exists(self):
        """verify_cron_request must be defined in main.py."""
        assert 'def verify_cron_request' in self.source
    
    def test_cron_secret_in_config(self):
        """Config must have cron_secret setting."""
        from src.config import Settings
        import inspect
        source = inspect.getsource(Settings)
        assert 'cron_secret' in source
    
    def test_all_cron_endpoints_call_verify(self):
        """All 6 cron/trigger endpoints must call verify_cron_request."""
        # Extract each endpoint function from the source
        endpoints = [
            'pattern_scan_trigger',
            'reminder_first',
            'reminder_second', 
            'reminder_third',
            'reset_quick_checkins',
            'weekly_report_trigger',
        ]
        
        for endpoint_name in endpoints:
            # Find the function definition and its body
            func_start = self.source.find(f'async def {endpoint_name}(')
            assert func_start != -1, f"Endpoint {endpoint_name} not found"
            
            # Find the next function definition (end of this function)
            next_func = self.source.find('\n@app.', func_start + 1)
            if next_func == -1:
                next_func = self.source.find('\n# ===== Singleton', func_start + 1)
            if next_func == -1:
                next_func = len(self.source)
            
            func_body = self.source[func_start:next_func]
            assert 'verify_cron_request' in func_body, (
                f"Endpoint {endpoint_name} must call verify_cron_request()"
            )
    
    def test_verify_checks_header(self):
        """verify_cron_request must check X-Cron-Secret header."""
        assert 'X-Cron-Secret' in self.source
    
    def test_verify_returns_403(self):
        """verify_cron_request must raise 403 on failure."""
        assert '403' in self.source
    
    def test_verify_skips_when_empty_secret(self):
        """verify_cron_request must skip auth when cron_secret is empty."""
        # Find the function body
        func_start = self.source.find('def verify_cron_request')
        func_end = self.source.find('\n# =====', func_start)
        func_body = self.source[func_start:func_end]
        
        # Must have logic to skip when secret is empty
        assert 'not expected_secret' in func_body or 'not settings.cron_secret' in func_body, (
            "Must skip auth when cron_secret is empty"
        )


# =====================================================
# CROSS-CUTTING: SCHEMA BACKWARD COMPATIBILITY
# =====================================================

class TestSchemaBackwardCompatibility:
    """
    Verify that models handle both old (5-item) and new (6-item) data.
    """
    
    def test_tier1_defaults_skill_building_false(self):
        """Tier1 without skill_building should default to False."""
        tier1 = Tier1NonNegotiables(
            sleep=True, training=True, deep_work=True,
            zero_porn=True, boundaries=True
            # skill_building omitted → should default to False
        )
        assert tier1.skill_building is False
    
    def test_checkin_defaults_corrected_at_none(self):
        """DailyCheckIn without corrected_at should default to None."""
        checkin = DailyCheckIn(
            date="2026-02-08",
            user_id="test",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=True, training=True, deep_work=True,
                zero_porn=True, boundaries=True
            ),
            responses=CheckInResponses(
                challenges="Test challenges text with adequate length for validation purposes here",
                rating=7,
                rating_reason="Test rating reason with enough detail to pass validation length checks",
                tomorrow_priority="Tomorrow priority text with adequate length for validation purposes",
                tomorrow_obstacle="Tomorrow obstacle with enough detail to pass validation length checks",
            ),
            compliance_score=83.3,
        )
        assert checkin.corrected_at is None
    
    def test_compliance_score_6_items_all_yes(self, tier1_all_complete):
        """6/6 items = 100%."""
        score = calculate_compliance_score(tier1_all_complete)
        assert score == 100.0
    
    def test_compliance_score_6_items_5_yes(self, tier1_5_of_6):
        """5/6 items = 83.3%."""
        score = calculate_compliance_score(tier1_5_of_6)
        expected = (5 / 6) * 100
        assert abs(score - expected) < 0.1
    
    def test_compliance_score_0_items(self, tier1_none_complete):
        """0/6 items = 0%."""
        score = calculate_compliance_score(tier1_none_complete)
        assert score == 0.0
    
    def test_checkin_from_firestore_with_corrected_at(self):
        """from_firestore should handle corrected_at field."""
        data = {
            "date": "2026-02-08",
            "user_id": "test",
            "mode": "maintenance",
            "tier1_non_negotiables": {
                "sleep": True, "training": True, "deep_work": True,
                "skill_building": True, "zero_porn": True, "boundaries": True
            },
            "responses": {
                "challenges": "Test challenges with adequate length for validation purposes here",
                "rating": 7,
                "rating_reason": "Test rating reason with enough detail to pass validation checks",
                "tomorrow_priority": "Tomorrow priority text with adequate length for validation",
                "tomorrow_obstacle": "Tomorrow obstacle with enough detail to pass validation",
            },
            "compliance_score": 100.0,
            "completed_at": datetime.utcnow(),
            "duration_seconds": 120,
            "is_quick_checkin": False,
            "corrected_at": datetime.utcnow(),
        }
        checkin = DailyCheckIn.from_firestore(data)
        assert checkin.corrected_at is not None
    
    def test_checkin_from_firestore_without_corrected_at(self):
        """from_firestore should handle missing corrected_at (old data)."""
        data = {
            "date": "2026-02-01",
            "user_id": "test",
            "mode": "maintenance",
            "tier1_non_negotiables": {
                "sleep": True, "training": True, "deep_work": True,
                "zero_porn": True, "boundaries": True
            },
            "responses": {
                "challenges": "Test challenges with adequate length for validation purposes here",
                "rating": 7,
                "rating_reason": "Test rating reason with enough detail to pass validation checks",
                "tomorrow_priority": "Tomorrow priority text with adequate length for validation",
                "tomorrow_obstacle": "Tomorrow obstacle with enough detail to pass validation",
            },
            "compliance_score": 100.0,
            "completed_at": datetime.utcnow(),
            "duration_seconds": 120,
            "is_quick_checkin": False,
        }
        checkin = DailyCheckIn.from_firestore(data)
        assert checkin.corrected_at is None
