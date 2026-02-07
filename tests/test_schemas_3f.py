"""
Unit Tests for Phase 3F Schema Fields
========================================

Tests that the new Phase 3F fields on User model work correctly,
including defaults, serialization (to_firestore), and deserialization
(from_firestore).

**Testing Strategy:**
- Test that new fields have correct defaults
- Test to_firestore includes new fields
- Test from_firestore handles missing fields (backward compat)
- Test from_firestore with new fields present

**Theory: Backward Compatibility in Schema Evolution**
When adding new fields to a data model that's already stored in a database,
you must ensure:
1. Old documents (without new fields) can still be deserialized
2. New documents include the new fields
3. Default values are sensible for existing users

Pydantic achieves this with `Optional` fields and `default` values.
We test both directions: creating new users and loading old users.

Run tests:
    pytest tests/test_schemas_3f.py -v
"""

import pytest
from datetime import datetime

from src.models.schemas import User


# ===== Default Values Tests =====

class TestPhase3FDefaults:
    """Tests that Phase 3F fields have correct default values."""
    
    def test_leaderboard_opt_in_default_true(self):
        """
        New users should be opted INTO the leaderboard by default.
        
        **Design Decision:**
        We default to True to bootstrap the leaderboard with users.
        In a production app with privacy concerns, you might default
        to False and require explicit opt-in. For our small user base,
        defaulting to True creates a more engaging experience.
        """
        user = User(
            user_id="test",
            telegram_id=12345,
            name="Test",
            timezone="Asia/Kolkata",
        )
        assert user.leaderboard_opt_in is True
    
    def test_referred_by_default_none(self):
        """referred_by should default to None (organic user)."""
        user = User(
            user_id="test",
            telegram_id=12345,
            name="Test",
            timezone="Asia/Kolkata",
        )
        assert user.referred_by is None
    
    def test_referral_code_default_none(self):
        """referral_code should default to None (generated on first /invite)."""
        user = User(
            user_id="test",
            telegram_id=12345,
            name="Test",
            timezone="Asia/Kolkata",
        )
        assert user.referral_code is None


# ===== Serialization Tests =====

class TestPhase3FSerialization:
    """Tests that Phase 3F fields serialize correctly to Firestore."""
    
    def test_to_firestore_includes_leaderboard(self):
        """to_firestore should include leaderboard_opt_in field."""
        user = User(
            user_id="test",
            telegram_id=12345,
            name="Test",
            timezone="Asia/Kolkata",
            leaderboard_opt_in=False,
        )
        data = user.to_firestore()
        assert "leaderboard_opt_in" in data
        assert data["leaderboard_opt_in"] is False
    
    def test_to_firestore_includes_referred_by(self):
        """to_firestore should include referred_by field."""
        user = User(
            user_id="test",
            telegram_id=12345,
            name="Test",
            timezone="Asia/Kolkata",
            referred_by="999",
        )
        data = user.to_firestore()
        assert "referred_by" in data
        assert data["referred_by"] == "999"
    
    def test_to_firestore_includes_referral_code(self):
        """to_firestore should include referral_code field."""
        user = User(
            user_id="test",
            telegram_id=12345,
            name="Test",
            timezone="Asia/Kolkata",
            referral_code="ref_test",
        )
        data = user.to_firestore()
        assert "referral_code" in data
        assert data["referral_code"] == "ref_test"


# ===== Deserialization Tests =====

class TestPhase3FDeserialization:
    """Tests backward compatibility when loading from Firestore."""
    
    def test_from_firestore_without_3f_fields(self):
        """
        Loading a pre-3F user document should work with defaults.
        
        **Theory: Schema Migration Without Migration**
        By using default values in Pydantic, existing Firestore documents
        that don't have the new fields will still deserialize correctly.
        Pydantic fills in the defaults. This eliminates the need for a
        database migration script.
        """
        # Simulate a pre-Phase3F Firestore document
        old_data = {
            "user_id": "old_user",
            "telegram_id": 11111,
            "name": "OldUser",
            "timezone": "Asia/Kolkata",
            "streaks": {
                "current_streak": 10,
                "longest_streak": 10,
                "last_checkin_date": "2026-01-01",
                "total_checkins": 10,
            },
            "constitution_mode": "maintenance",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        user = User.from_firestore(old_data)
        
        # New fields should have defaults
        assert user.leaderboard_opt_in is True
        assert user.referred_by is None
        assert user.referral_code is None
    
    def test_from_firestore_with_3f_fields(self):
        """Loading a Phase 3F document should populate all new fields."""
        data = {
            "user_id": "new_user",
            "telegram_id": 22222,
            "name": "NewUser",
            "timezone": "Asia/Kolkata",
            "streaks": {
                "current_streak": 5,
                "longest_streak": 5,
                "total_checkins": 5,
            },
            "constitution_mode": "optimization",
            "leaderboard_opt_in": False,
            "referred_by": "referrer_id",
            "referral_code": "ref_new_user",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        }
        
        user = User.from_firestore(data)
        
        assert user.leaderboard_opt_in is False
        assert user.referred_by == "referrer_id"
        assert user.referral_code == "ref_new_user"
    
    def test_roundtrip_serialization(self):
        """
        to_firestore → from_firestore should produce equivalent User.
        
        This tests that serialization and deserialization are symmetric.
        Any field added to to_firestore() must be handled by from_firestore().
        """
        original = User(
            user_id="roundtrip",
            telegram_id=33333,
            name="RoundTrip",
            timezone="Asia/Kolkata",
            leaderboard_opt_in=False,
            referred_by="friend_123",
            referral_code="ref_roundtrip",
        )
        
        data = original.to_firestore()
        restored = User.from_firestore(data)
        
        assert restored.user_id == original.user_id
        assert restored.leaderboard_opt_in == original.leaderboard_opt_in
        assert restored.referred_by == original.referred_by
        assert restored.referral_code == original.referral_code


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
