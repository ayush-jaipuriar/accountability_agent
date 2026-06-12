"""
Test: Feedback Service
======================

Tests NPS collection and storage.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.services.feedback_service import FeedbackService


@pytest.fixture
def feedback_service():
    return FeedbackService()


@pytest.fixture
def mock_firestore():
    with patch("src.services.feedback_service.firestore_service") as mock:
        mock.db = MagicMock()
        yield mock


class TestStoreFeedback:
    """Test feedback storage."""

    def test_store_nps(self, feedback_service, mock_firestore):
        fid = feedback_service.store_feedback(
            user_id="111",
            feedback_type="nps",
            rating=9,
        )
        assert fid.startswith("fb_")
        mock_firestore.db.collection.assert_called_with("feedback")

    def test_store_feature_request(self, feedback_service, mock_firestore):
        fid = feedback_service.store_feedback(
            user_id="111",
            feedback_type="feature_request",
            message="Add dark mode",
        )
        assert fid.startswith("fb_")


class TestCalculateNPS:
    """Test NPS calculation."""

    def test_no_feedback(self, feedback_service):
        with patch.object(feedback_service, 'get_recent_feedback', return_value=[]):
            result = feedback_service.calculate_nps()
        assert result["nps"] is None
        assert result["total"] == 0

    def test_all_promoters(self, feedback_service):
        feedbacks = [
            {"rating": 10}, {"rating": 9}, {"rating": 10},
        ]
        with patch.object(feedback_service, 'get_recent_feedback', return_value=feedbacks):
            result = feedback_service.calculate_nps()
        assert result["nps"] == 100.0
        assert result["promoters"] == 3

    def test_mixed(self, feedback_service):
        feedbacks = [
            {"rating": 10}, {"rating": 8}, {"rating": 5},
        ]
        with patch.object(feedback_service, 'get_recent_feedback', return_value=feedbacks):
            result = feedback_service.calculate_nps()
        # 1 promoter, 1 passive, 1 detractor
        # NPS = (1/3 - 1/3) * 100 = 0
        assert result["nps"] == 0.0
        assert result["promoters"] == 1
        assert result["passives"] == 1
        assert result["detractors"] == 1

    def test_negative_nps(self, feedback_service):
        feedbacks = [
            {"rating": 3}, {"rating": 4}, {"rating": 5},
        ]
        with patch.object(feedback_service, 'get_recent_feedback', return_value=feedbacks):
            result = feedback_service.calculate_nps()
        assert result["nps"] == -100.0
        assert result["detractors"] == 3

    def test_format_nps_summary(self, feedback_service):
        feedbacks = [
            {"rating": 10}, {"rating": 9}, {"rating": 5},
        ]
        with patch.object(feedback_service, 'get_recent_feedback', return_value=feedbacks):
            summary = feedback_service.format_nps_summary()
        assert "NPS Score" in summary
        assert "33.3" in summary or "33" in summary
