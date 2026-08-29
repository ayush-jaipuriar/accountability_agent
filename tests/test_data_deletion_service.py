"""
Tests for src/services/data_deletion_service.py
================================================
Comprehensive test suite for GDPR user data deletion service.
"""

import pytest
from unittest.mock import MagicMock, patch

from src.services.data_deletion_service import DataDeletionService, data_deletion_service
from src.models.schemas import User


@pytest.fixture
def mock_firestore():
    with patch("src.services.data_deletion_service.firestore_service") as mock_fs:
        mock_db = MagicMock()
        mock_fs.db = mock_db
        yield mock_fs


@pytest.fixture
def sample_user_with_partner():
    return User(
        user_id="user_123",
        telegram_id=123,
        telegram_username="test_user",
        name="Test User",
        accountability_partner_id="partner_456",
        accountability_partner_name="Partner",
    )


class TestDataDeletionService:

    def test_singleton_instance(self):
        assert isinstance(data_deletion_service, DataDeletionService)

    def test_delete_all_user_data_full_success(self, mock_firestore, sample_user_with_partner):
        service = DataDeletionService()
        mock_firestore.get_user.return_value = sample_user_with_partner

        # Mock reverse partners stream
        mock_rev_doc = MagicMock()
        mock_rev_doc.id = "partner_789"
        mock_rev_ref = MagicMock()
        mock_rev_doc.reference = mock_rev_ref
        
        mock_users_collection = MagicMock()
        mock_users_collection.where.return_value.stream.return_value = [mock_rev_doc]
        
        # Subcollection doc mocks
        mock_sub_doc1 = MagicMock()
        mock_sub_doc2 = MagicMock()
        mock_sub_stream = [mock_sub_doc1, mock_sub_doc2]

        # Collections dictionary setup
        collections = {}
        for coll_name in ["users", "daily_checkins", "daily_tasks", "emotional_interactions",
                           "interventions", "reminder_status", "partner_checkin_notifications",
                           "goals", "challenges", "feedback"]:
            c = MagicMock()
            doc_mock = MagicMock()
            sub_coll_mock = MagicMock()
            sub_coll_mock.stream.return_value = mock_sub_stream
            doc_mock.collection.return_value = sub_coll_mock
            c.document.return_value = doc_mock
            c.where.return_value.stream.return_value = mock_sub_stream
            collections[coll_name] = c

        collections["users"].where.return_value.stream.return_value = [mock_rev_doc]

        def get_coll(name):
            return collections.get(name, MagicMock())

        mock_firestore.db.collection.side_effect = get_coll

        result = service.delete_all_user_data("user_123")

        assert result["success"] is True
        assert len(result["errors"]) == 0
        assert result["deleted"]["partner_link"] is True
        assert result["deleted"]["user_profile"] is True
        assert result["deleted"]["checkins"] == 2
        assert result["deleted"]["daily_tasks"] == 2
        assert result["deleted"]["emotional_interactions"] == 2
        assert result["deleted"]["interventions"] == 2
        assert result["deleted"]["goals"] == 2
        assert result["deleted"]["challenges"] == 4  # query1 + query2
        assert result["deleted"]["feedback"] == 2

        # Verify forward partner unlink was executed
        mock_firestore.update_user.assert_called_once_with(
            "partner_456",
            {"accountability_partner_id": None, "accountability_partner_name": None}
        )

        # Verify reverse partner doc update was executed
        mock_rev_ref.update.assert_called_once_with(
            {"accountability_partner_id": None, "accountability_partner_name": None}
        )

    def test_delete_user_without_partner(self, mock_firestore):
        service = DataDeletionService()
        user_no_partner = User(
            user_id="user_solo",
            telegram_id=999,
            telegram_username="solo",
            name="Solo",
            accountability_partner_id=None,
        )
        mock_firestore.get_user.return_value = user_no_partner

        mock_coll = MagicMock()
        mock_doc = MagicMock()
        mock_sub = MagicMock()
        mock_sub.stream.return_value = []
        mock_doc.collection.return_value = mock_sub
        mock_coll.document.return_value = mock_doc
        mock_coll.where.return_value.stream.return_value = []
        mock_firestore.db.collection.return_value = mock_coll

        result = service.delete_all_user_data("user_solo")

        assert result["success"] is True
        assert "partner_link" not in result["deleted"]
        mock_firestore.update_user.assert_not_called()

    def test_partial_failure_handling(self, mock_firestore):
        service = DataDeletionService()
        mock_firestore.get_user.side_effect = Exception("Firestore timeout on user lookup")

        mock_coll = MagicMock()
        mock_coll.document.side_effect = Exception("Delete error")
        mock_coll.where.side_effect = Exception("Query error")
        mock_firestore.db.collection.return_value = mock_coll

        result = service.delete_all_user_data("user_err")

        assert result["success"] is False
        assert len(result["errors"]) > 0
        assert any("Partner unlink failed" in e for e in result["errors"])
