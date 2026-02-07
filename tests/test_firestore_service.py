"""
Firestore Service Tests
=======================

Tests for all database operations with mocked Firestore client.

**Testing Strategy:**
The Firestore service is a critical layer - all data flows through it.
We mock `google.cloud.firestore.Client` to avoid needing a real database.

**What We Test:**
- CRUD operations (create, read, update, delete)
- User operations (create, get, update streak, update mode)
- Check-in operations (store, get, exists, get_recent)
- Reminder operations (get status, set sent)
- Streak shield operations (use, reset)
- Achievement operations (unlock)
- Partner operations (set, unlink, find by username)

**Mocking Pattern:**
We mock at the `google.cloud.firestore.Client` level, creating mock documents
and collections that behave like the real Firestore SDK.
"""

import pytest
from unittest.mock import patch, MagicMock, PropertyMock
from datetime import datetime

from src.models.schemas import (
    User, UserStreaks, DailyCheckIn, Tier1NonNegotiables,
    CheckInResponses, StreakShields, ReminderTimes
)


# ===== Fixtures =====

@pytest.fixture
def mock_db():
    """
    Create a mocked Firestore client.
    
    This replaces the real Firestore client with a mock that
    tracks all calls without hitting the real database.
    """
    with patch('src.services.firestore_service.firestore.Client') as mock_client:
        mock_instance = MagicMock()
        mock_client.return_value = mock_instance
        yield mock_instance


@pytest.fixture
def firestore_svc(mock_db):
    """
    Create FirestoreService instance with mocked DB.
    
    We import here to ensure the mock is in place before
    the module-level singleton is created.
    """
    from src.services.firestore_service import FirestoreService
    svc = FirestoreService.__new__(FirestoreService)
    svc.db = mock_db
    return svc


@pytest.fixture
def test_user():
    """Standard test user."""
    return User(
        user_id="123456789",
        telegram_id=123456789,
        telegram_username="test_user",
        name="Test User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=10,
            longest_streak=15,
            last_checkin_date="2026-02-06",
            total_checkins=50
        ),
        constitution_mode="maintenance",
        career_mode="skill_building",
        streak_shields=StreakShields(total=3, used=0, available=3),
    )


@pytest.fixture
def test_checkin():
    """Standard test check-in."""
    return DailyCheckIn(
        date="2026-02-07",
        user_id="123456789",
        mode="maintenance",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=True, sleep_hours=7.5,
            training=True, deep_work=True,
            deep_work_hours=2.5, zero_porn=True,
            boundaries=True
        ),
        responses=CheckInResponses(
            challenges="Test challenges for the day with enough length to pass validation",
            rating=8,
            rating_reason="Good day with solid productivity and discipline maintained throughout",
            tomorrow_priority="Focus on LeetCode and system design preparation for interviews",
            tomorrow_obstacle="Late evening meeting might drain energy and reduce focus time",
        ),
        compliance_score=100.0,
    )


# ===== User Operations Tests =====

class TestCreateUser:
    """Tests for creating user profiles in Firestore."""

    def test_create_user_calls_set(self, firestore_svc, mock_db, test_user):
        """create_user should call document.set() with user data."""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        firestore_svc.create_user(test_user)

        mock_db.collection.assert_called_with('users')
        mock_db.collection.return_value.document.assert_called_with(test_user.user_id)
        mock_doc_ref.set.assert_called_once()
        
        # Verify the data passed to set()
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["user_id"] == "123456789"
        assert call_args["name"] == "Test User"
        assert call_args["timezone"] == "Asia/Kolkata"

    def test_create_user_includes_phase3_fields(self, firestore_svc, mock_db, test_user):
        """User data should include Phase 3 fields."""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        firestore_svc.create_user(test_user)

        call_args = mock_doc_ref.set.call_args[0][0]
        assert "career_mode" in call_args
        assert "streak_shields" in call_args
        assert "leaderboard_opt_in" in call_args
        assert "achievements" in call_args


class TestGetUser:
    """Tests for fetching user profiles."""

    def test_get_existing_user(self, firestore_svc, mock_db, test_user):
        """Should return User object when document exists."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = test_user.to_firestore()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = firestore_svc.get_user("123456789")

        assert result is not None
        assert result.user_id == "123456789"
        assert result.name == "Test User"
        assert result.streaks.current_streak == 10

    def test_get_nonexistent_user(self, firestore_svc, mock_db):
        """Should return None when document doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = firestore_svc.get_user("nonexistent")

        assert result is None

    def test_get_user_backward_compatible(self, firestore_svc, mock_db):
        """
        Should handle Phase 1-2 users without Phase 3 fields.
        
        Backward compatibility is crucial: existing users shouldn't break
        when we add new fields with defaults.
        """
        # Simulate a Phase 1-2 user (no Phase 3 fields)
        old_user_data = {
            "user_id": "old_user",
            "telegram_id": 999,
            "name": "Old User",
            "timezone": "Asia/Kolkata",
            "streaks": {"current_streak": 5, "longest_streak": 5, "total_checkins": 5},
            "constitution_mode": "maintenance",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = old_user_data
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = firestore_svc.get_user("old_user")

        assert result is not None
        assert result.career_mode == "skill_building"  # Default
        assert result.leaderboard_opt_in is True  # Default
        assert result.achievements == []  # Default


class TestUpdateUserStreak:
    """Tests for updating streak data."""

    def test_update_streak(self, firestore_svc, mock_db):
        """Should update streak fields in Firestore."""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        streak_data = {
            "current_streak": 11,
            "longest_streak": 15,
            "last_checkin_date": "2026-02-07",
            "total_checkins": 51
        }
        firestore_svc.update_user_streak("123456789", streak_data)

        mock_doc_ref.update.assert_called_once()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args["streaks"]["current_streak"] == 11


class TestUpdateCareerMode:
    """Tests for career mode updates (Phase 3D)."""

    def test_update_career_mode(self, firestore_svc, mock_db):
        """Should update career_mode field."""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        result = firestore_svc.update_user_career_mode("123456789", "job_searching")

        assert result is True
        mock_doc_ref.update.assert_called_once()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args["career_mode"] == "job_searching"


# ===== Check-In Operations Tests =====

class TestStoreCheckin:
    """Tests for storing check-in records."""

    def test_store_checkin(self, firestore_svc, mock_db, test_checkin):
        """Should store check-in in subcollection."""
        mock_doc_ref = MagicMock()
        (mock_db.collection.return_value
         .document.return_value
         .collection.return_value
         .document.return_value) = mock_doc_ref

        firestore_svc.store_checkin("123456789", test_checkin)

        mock_doc_ref.set.assert_called_once()
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["date"] == "2026-02-07"
        assert call_args["compliance_score"] == 100.0


class TestCheckinExists:
    """Tests for checking if check-in already exists."""

    def test_checkin_exists_true(self, firestore_svc, mock_db):
        """Should return True when check-in document exists."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        (mock_db.collection.return_value
         .document.return_value
         .collection.return_value
         .document.return_value
         .get.return_value) = mock_doc

        assert firestore_svc.checkin_exists("123456789", "2026-02-07") is True

    def test_checkin_exists_false(self, firestore_svc, mock_db):
        """Should return False when check-in document doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        (mock_db.collection.return_value
         .document.return_value
         .collection.return_value
         .document.return_value
         .get.return_value) = mock_doc

        assert firestore_svc.checkin_exists("123456789", "2026-02-07") is False


# ===== Reminder System Tests =====

class TestReminderStatus:
    """Tests for reminder tracking (Phase 3A)."""

    def test_get_reminder_status_none(self, firestore_svc, mock_db):
        """Should return None when no reminder status exists."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        (mock_db.collection.return_value
         .document.return_value
         .collection.return_value
         .document.return_value
         .get.return_value) = mock_doc

        result = firestore_svc.get_reminder_status("123456789", "2026-02-07")
        assert result is None

    def test_get_reminder_status_with_data(self, firestore_svc, mock_db):
        """Should return reminder status dict when exists."""
        status_data = {
            "user_id": "123456789",
            "date": "2026-02-07",
            "first_sent": True,
            "second_sent": False,
            "third_sent": False,
        }
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = status_data
        (mock_db.collection.return_value
         .document.return_value
         .collection.return_value
         .document.return_value
         .get.return_value) = mock_doc

        result = firestore_svc.get_reminder_status("123456789", "2026-02-07")
        assert result is not None
        assert result["first_sent"] is True
        assert result["second_sent"] is False

    def test_set_reminder_sent_first(self, firestore_svc, mock_db):
        """Should mark first reminder as sent."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        (mock_db.collection.return_value
         .document.return_value
         .collection.return_value
         .document.return_value) = mock_doc_ref

        firestore_svc.set_reminder_sent("123456789", "2026-02-07", "first")

        mock_doc_ref.set.assert_called_once()
        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["first_sent"] is True

    def test_set_reminder_sent_preserves_previous(self, firestore_svc, mock_db):
        """Setting second reminder should preserve first reminder status."""
        existing_status = {
            "user_id": "123456789",
            "date": "2026-02-07",
            "first_sent": True,
            "second_sent": False,
            "third_sent": False,
        }
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = existing_status.copy()
        mock_doc_ref = MagicMock()
        mock_doc_ref.get.return_value = mock_doc
        (mock_db.collection.return_value
         .document.return_value
         .collection.return_value
         .document.return_value) = mock_doc_ref

        firestore_svc.set_reminder_sent("123456789", "2026-02-07", "second")

        call_args = mock_doc_ref.set.call_args[0][0]
        assert call_args["first_sent"] is True  # Preserved
        assert call_args["second_sent"] is True  # Set


# ===== Streak Shield Tests =====

class TestStreakShields:
    """Tests for streak protection system (Phase 3A)."""

    def test_use_shield_success(self, firestore_svc, mock_db, test_user):
        """Should use shield when available."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = test_user.to_firestore()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = firestore_svc.use_streak_shield("123456789")

        assert result is True
        mock_db.collection.return_value.document.return_value.update.assert_called_once()

    def test_use_shield_none_available(self, firestore_svc, mock_db, test_user):
        """Should return False when no shields left."""
        test_user.streak_shields.used = 3
        test_user.streak_shields.available = 0
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = test_user.to_firestore()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = firestore_svc.use_streak_shield("123456789")

        assert result is False

    def test_use_shield_user_not_found(self, firestore_svc, mock_db):
        """Should return False when user doesn't exist."""
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        result = firestore_svc.use_streak_shield("nonexistent")

        assert result is False


# ===== Achievement Tests =====

class TestUnlockAchievement:
    """Tests for achievement system (Phase 3C)."""

    def test_unlock_new_achievement(self, firestore_svc, mock_db, test_user):
        """Should add achievement to user's list."""
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = test_user.to_firestore()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        firestore_svc.unlock_achievement("123456789", "week_warrior")

        mock_db.collection.return_value.document.return_value.update.assert_called_once()

    def test_unlock_duplicate_ignored(self, firestore_svc, mock_db, test_user):
        """Should not duplicate an already-unlocked achievement."""
        test_user.achievements = ["week_warrior"]
        
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = test_user.to_firestore()
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        firestore_svc.unlock_achievement("123456789", "week_warrior")

        # update should NOT be called since achievement already unlocked
        mock_db.collection.return_value.document.return_value.update.assert_not_called()


# ===== Partner System Tests =====

class TestAccountabilityPartner:
    """Tests for accountability partner system (Phase 3B)."""

    def test_set_partner(self, firestore_svc, mock_db):
        """Should update partner fields."""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        firestore_svc.set_accountability_partner(
            user_id="user1",
            partner_id="user2",
            partner_name="Partner User"
        )

        mock_doc_ref.update.assert_called_once()
        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args["accountability_partner_id"] == "user2"
        assert call_args["accountability_partner_name"] == "Partner User"

    def test_unlink_partner(self, firestore_svc, mock_db):
        """Should set partner fields to None."""
        mock_doc_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_doc_ref

        firestore_svc.set_accountability_partner(
            user_id="user1",
            partner_id=None,
            partner_name=None
        )

        call_args = mock_doc_ref.update.call_args[0][0]
        assert call_args["accountability_partner_id"] is None
        assert call_args["accountability_partner_name"] is None


# ===== Emotional Interaction Logging Tests =====

class TestEmotionalInteraction:
    """Tests for emotional support interaction logging (Phase 3B)."""

    def test_store_emotional_interaction(self, firestore_svc, mock_db):
        """Should store emotional interaction document."""
        mock_collection = MagicMock()
        mock_db.collection.return_value = mock_collection

        firestore_svc.store_emotional_interaction(
            user_id="123456789",
            emotion_type="loneliness",
            user_message="I'm feeling lonely tonight",
            bot_response="I hear you. Loneliness is real and temporary...",
            timestamp=datetime.utcnow()
        )

        mock_collection.add.assert_called_once()
        call_args = mock_collection.add.call_args[0][0]
        assert call_args["emotion_type"] == "loneliness"
        assert call_args["user_id"] == "123456789"


# ===== Health Check Tests =====

class TestHealthCheck:
    """Tests for Firestore connection health check."""

    def test_connection_success(self, firestore_svc, mock_db):
        """Should return True when connection works."""
        mock_db.collections.return_value = iter([])
        assert firestore_svc.test_connection() is True

    def test_connection_failure(self, firestore_svc, mock_db):
        """Should return False when connection fails."""
        mock_db.collections.side_effect = Exception("Connection refused")
        assert firestore_svc.test_connection() is False
