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


class TestPartnerCheckinNotificationStatus:
    """Tests for partner notification status tracking."""

    def test_get_partner_notification_status_none(self, firestore_svc, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = False
        (mock_db.collection.return_value
         .document.return_value
         .collection.return_value
         .document.return_value
         .get.return_value) = mock_doc

        result = firestore_svc.get_partner_checkin_notification_status(
            "123456789", "2026-03-22"
        )
        assert result is None

    def test_mark_partner_notification_sent_initial(self, firestore_svc, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = False
        mock_doc.to_dict.return_value = {}
        mock_doc_ref = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
            .document.return_value
        )
        mock_doc_ref.get.return_value = mock_doc

        result = firestore_svc.mark_partner_checkin_notification_sent(
            user_id="123456789",
            date="2026-03-22",
            partner_id="987654321",
            event_type="initial",
        )

        assert result is True
        mock_doc_ref.set.assert_called_once()
        payload = mock_doc_ref.set.call_args[0][0]
        assert payload["initial_sent"] is True
        assert payload["partner_id"] == "987654321"

    def test_mark_partner_notification_sent_update(self, firestore_svc, mock_db):
        existing = {
            "user_id": "123456789",
            "date": "2026-03-22",
            "partner_id": "987654321",
            "initial_sent": True,
            "updated_sent": False,
        }
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = existing
        mock_doc_ref = (
            mock_db.collection.return_value
            .document.return_value
            .collection.return_value
            .document.return_value
        )
        mock_doc_ref.get.return_value = mock_doc

        result = firestore_svc.mark_partner_checkin_notification_sent(
            user_id="123456789",
            date="2026-03-22",
            partner_id="987654321",
            event_type="updated",
        )

        assert result is True
        payload = mock_doc_ref.set.call_args[0][0]
        assert payload["initial_sent"] is True
        assert payload["updated_sent"] is True

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


# ===== Atomic Check-in Transaction Tests =====

class TestAtomicTransactionalCheckin:

    def test_store_checkin_with_streak_update_success(self, firestore_svc, mock_db, test_user, test_checkin):
        """Test transactional execution of checkin store + user streak update with transient keys stripped."""
        mock_transaction = MagicMock()
        mock_db.transaction.return_value = mock_transaction

        with patch("src.services.firestore_service.firestore.transactional", lambda fn: fn):
            streak_data = {
                "current_streak": 11,
                "longest_streak": 15,
                "last_checkin_date": "2026-02-07",
                "total_checkins": 51,
                "milestone_hit": 10,
                "is_reset": False,
                "recovery_message": "Keep going!",
                "recovery_fact": "Daily habit creates success",
            }

            mock_user_ref = MagicMock()
            mock_checkin_ref = MagicMock()
            
            mock_db.collection.return_value.document.return_value = mock_user_ref
            mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_checkin_ref

            firestore_svc.store_checkin_with_streak_update("123456789", test_checkin, streak_data)
            
            mock_transaction.set.assert_called_once()
            mock_transaction.update.assert_called_once()
            updated_data = mock_transaction.update.call_args[0][1]
            assert "milestone_hit" not in updated_data["streaks"]
            assert updated_data["streaks"]["current_streak"] == 11

    def test_store_checkin_with_streak_update_failure(self, firestore_svc, mock_db, test_checkin):
        """Test transactional failure raises exception."""
        mock_transaction = MagicMock()
        mock_db.transaction.return_value = mock_transaction

        with patch("src.services.firestore_service.firestore.transactional", lambda fn: fn):
            mock_transaction.set.side_effect = Exception("Write conflict")
            with pytest.raises(Exception, match="Write conflict"):
                firestore_svc.store_checkin_with_streak_update("123456789", test_checkin, {"current_streak": 1})


# ===== User Extended Operations Tests =====

class TestUserExtendedOperations:

    def test_user_exists(self, firestore_svc, mock_db):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_db.collection.return_value.document.return_value.get.return_value = mock_doc

        assert firestore_svc.user_exists("123") is True

        mock_doc.exists = False
        assert firestore_svc.user_exists("456") is False

        mock_db.collection.return_value.document.return_value.get.side_effect = Exception("Read error")
        assert firestore_svc.user_exists("789") is False

    def test_update_user_mode(self, firestore_svc, mock_db):
        mock_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_ref

        firestore_svc.update_user_mode("123", "focus")
        mock_ref.update.assert_called_once()
        assert mock_ref.update.call_args[0][0]["constitution_mode"] == "focus"

        mock_ref.update.side_effect = Exception("Update error")
        with pytest.raises(Exception, match="Update error"):
            firestore_svc.update_user_mode("123", "focus")

    def test_update_user(self, firestore_svc, mock_db):
        mock_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_ref

        assert firestore_svc.update_user("123", {"name": "New Name"}) is True
        mock_ref.update.assert_called_once()
        assert mock_ref.update.call_args[0][0]["name"] == "New Name"

        mock_ref.update.side_effect = Exception("Update error")
        assert firestore_svc.update_user("123", {"name": "New Name"}) is False

    def test_get_active_users_and_all_users(self, firestore_svc, mock_db, test_user):
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = test_user.to_firestore()
        mock_db.collection.return_value.stream.return_value = [mock_doc]

        users = firestore_svc.get_active_users()
        assert len(users) == 1
        assert users[0].user_id == test_user.user_id

        all_users = firestore_svc.get_all_users()
        assert len(all_users) == 1

    def test_get_users_by_timezones(self, firestore_svc, mock_db, test_user):
        test_user.timezone = "Asia/Kolkata"
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = test_user.to_firestore()
        mock_db.collection.return_value.stream.return_value = [mock_doc]

        # Match IST
        matched = firestore_svc.get_users_by_timezones(["Asia/Kolkata"])
        assert len(matched) == 1

        # No match America/New_York
        unmatched = firestore_svc.get_users_by_timezones(["America/New_York"])
        assert len(unmatched) == 0

    def test_get_users_without_checkin_today(self, firestore_svc, mock_db, test_user):
        mock_user_doc = MagicMock()
        mock_user_doc.to_dict.return_value = test_user.to_firestore()
        mock_db.collection.return_value.stream.return_value = [mock_user_doc]

        # Mock checkin_exists returns False (hasn't checked in)
        mock_checkin_doc = MagicMock()
        mock_checkin_doc.exists = False
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_checkin_doc

        users = firestore_svc.get_users_without_checkin_today("2026-02-07")
        assert len(users) == 1

    def test_get_user_by_telegram_username(self, firestore_svc, mock_db, test_user):
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = test_user.to_firestore()
        mock_query = MagicMock()
        mock_query.stream.return_value = [mock_doc]
        mock_db.collection.return_value.where.return_value.limit.return_value = mock_query

        user = firestore_svc.get_user_by_telegram_username("@test_user")
        assert user is not None
        assert user.telegram_username == "test_user"

        # Not found
        mock_query.stream.return_value = []
        user2 = firestore_svc.get_user_by_telegram_username("@unknown")
        assert user2 is None


# ===== Checkin Extended Operations Tests =====

class TestCheckinExtendedOperations:

    def test_get_checkin(self, firestore_svc, mock_db, test_checkin):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = test_checkin.to_firestore()
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value.get.return_value = mock_doc

        c = firestore_svc.get_checkin("123", "2026-02-07")
        assert c is not None
        assert c.date == "2026-02-07"

        mock_doc.exists = False
        assert firestore_svc.get_checkin("123", "2026-02-08") is None

    def test_get_all_checkins_and_recent(self, firestore_svc, mock_db, test_checkin):
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = test_checkin.to_firestore()
        
        mock_coll = MagicMock()
        # Chained .where().where().order_by().stream()
        mock_coll.where.return_value.where.return_value.order_by.return_value.stream.return_value = [mock_doc]
        mock_coll.order_by.return_value.stream.return_value = [mock_doc]
        mock_db.collection.return_value.document.return_value.collection.return_value = mock_coll

        recent = firestore_svc.get_recent_checkins("123", days=7)
        assert len(recent) == 1

        all_checkins = firestore_svc.get_all_checkins("123")
        assert len(all_checkins) == 1

    def test_update_checkin(self, firestore_svc, mock_db):
        mock_ref = MagicMock()
        mock_db.collection.return_value.document.return_value.collection.return_value.document.return_value = mock_ref

        assert firestore_svc.update_checkin("123", "2026-02-07", {"compliance_score": 90.0}) is True
        mock_ref.update.assert_called_once()


# ===== Interventions & Patterns Tests =====

class TestInterventionsAndPatterns:

    def test_log_intervention(self, firestore_svc, mock_db):
        mock_sub = MagicMock()
        mock_db.collection.return_value.document.return_value.collection.return_value = mock_sub

        firestore_svc.log_intervention(
            user_id="123",
            pattern_type="ghosting",
            severity="warning",
            data={"avg_sleep": 5.0},
            message="Hey where are you?"
        )
        mock_sub.add.assert_called_once()

    def test_get_recent_interventions_and_has_recent(self, firestore_svc, mock_db):
        mock_doc = MagicMock()
        mock_doc.id = "int_1"
        mock_doc.to_dict.return_value = {
            "pattern_type": "ghosting",
            "sent_at": datetime.utcnow(),
            "resolved": False,
        }
        mock_sub = MagicMock()
        mock_sub.where.return_value.order_by.return_value.stream.return_value = [mock_doc]
        mock_sub.where.return_value.stream.return_value = [mock_doc]
        mock_db.collection.return_value.document.return_value.collection.return_value = mock_sub

        interventions = firestore_svc.get_recent_interventions("123", days=3)
        assert len(interventions) == 1
        assert interventions[0]["id"] == "int_1"

        has_recent = firestore_svc.has_recent_intervention("123", "ghosting", cooldown_hours=48)
        assert has_recent is True

    def test_resolve_interventions(self, firestore_svc, mock_db):
        mock_doc = MagicMock()
        mock_doc.reference = MagicMock()
        mock_sub = MagicMock()
        mock_sub.where.return_value.where.return_value.stream.return_value = [mock_doc]
        mock_db.collection.return_value.document.return_value.collection.return_value = mock_sub

        resolved_count = firestore_svc.resolve_interventions("123", "ghosting")
        assert resolved_count == 1
        mock_doc.reference.update.assert_called_once()


# ===== Quick Checkins and Shields Tests =====

class TestQuickCheckinsAndShields:

    def test_reset_streak_shields(self, firestore_svc, mock_db, test_user):
        mock_doc = MagicMock()
        mock_doc.exists = True
        mock_doc.to_dict.return_value = test_user.to_firestore()
        mock_ref = MagicMock()
        mock_ref.get.return_value = mock_doc
        mock_db.collection.return_value.document.return_value = mock_ref

        with patch.object(firestore_svc, "get_user", return_value=test_user):
            firestore_svc.reset_streak_shields("123")
            mock_ref.update.assert_called_once()

    def test_increment_and_reset_quick_checkins(self, firestore_svc, mock_db, test_user):
        test_user.quick_checkin_count = 1
        mock_ref = MagicMock()
        mock_db.collection.return_value.document.return_value = mock_ref

        with patch.object(firestore_svc, "get_user", return_value=test_user):
            new_count = firestore_svc.increment_quick_checkin_count("123")
            assert new_count == 2
            mock_ref.update.assert_called_once()

        with patch.object(firestore_svc, "get_active_users", return_value=[test_user]):
            firestore_svc.reset_quick_checkin_counts()
            mock_ref.update.assert_called()
