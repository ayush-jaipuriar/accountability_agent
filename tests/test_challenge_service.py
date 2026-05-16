"""
Test: Challenge Service
=======================

Tests partner challenge creation, acceptance, progress tracking,
and completion detection.

Theory: Mutual Accountability
-------------------------------
A challenge creates a shared target between two users. Both partners
see each other's progress daily, creating mutual accountability
that is stronger than solo goal-setting.
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

from src.models.schemas import PartnerChallenge, DailyCheckIn, Tier1NonNegotiables, CheckInResponses
from src.services.challenge_service import ChallengeService


@pytest.fixture
def challenge_service():
    svc = ChallengeService()
    return svc


@pytest.fixture
def mock_firestore(challenge_service):
    with patch("src.services.challenge_service.firestore_service") as mock:
        mock.db = MagicMock()
        challenge_service.firestore = mock
        yield mock


class TestChallengeCreation:
    """Test challenge creation and retrieval."""

    def test_create_challenge(self, challenge_service, mock_firestore):
        """Create a new challenge between two users."""
        challenge = challenge_service.create_challenge(
            challenger_id="111",
            partner_id="222",
            challenge_type="sleep_7_days",
            title="7-Day Sleep Challenge",
            description="Get 7+ hours of sleep every day",
            start_date="2026-02-01",
            end_date="2026-02-07",
        )

        assert challenge.challenger_id == "111"
        assert challenge.partner_id == "222"
        assert challenge.challenge_type == "sleep_7_days"
        assert challenge.title == "7-Day Sleep Challenge"
        assert challenge.status == "pending"
        assert challenge.start_date == "2026-02-01"
        assert challenge.end_date == "2026-02-07"
        assert challenge.progress == {}

        # Verify Firestore write
        mock_firestore.db.collection.assert_called_with("challenges")

    def test_get_challenge(self, challenge_service, mock_firestore):
        """Fetch a challenge by ID."""
        challenge_data = {
            "challenge_id": "ch_123",
            "challenger_id": "111",
            "partner_id": "222",
            "challenge_type": "sleep_7_days",
            "title": "Sleep Challenge",
            "description": "Test",
            "start_date": "2026-02-01",
            "end_date": "2026-02-07",
            "status": "active",
            "progress": {},
            "winner_id": None,
            "created_at": datetime.utcnow(),
            "completed_at": None,
        }

        doc_mock = MagicMock()
        doc_mock.exists = True
        doc_mock.to_dict.return_value = challenge_data
        mock_firestore.db.collection.return_value.document.return_value.get.return_value = doc_mock

        result = challenge_service.get_challenge("ch_123")

        assert result is not None
        assert result.challenge_id == "ch_123"
        assert result.status == "active"

    def test_get_user_challenges(self, challenge_service, mock_firestore):
        """Fetch all challenges for a user."""
        challenge_data = {
            "challenge_id": "ch_123",
            "challenger_id": "111",
            "partner_id": "222",
            "challenge_type": "sleep_7_days",
            "title": "Sleep Challenge",
            "description": "Test",
            "start_date": "2026-02-01",
            "end_date": "2026-02-07",
            "status": "active",
            "progress": {},
            "winner_id": None,
            "created_at": datetime.utcnow(),
            "completed_at": None,
        }

        doc_mock = MagicMock()
        doc_mock.id = "ch_123"
        doc_mock.to_dict.return_value = challenge_data

        stream_mock = MagicMock()
        stream_mock.stream.return_value = [doc_mock]
        mock_firestore.db.collection.return_value.where.return_value = stream_mock

        challenges = challenge_service.get_user_challenges("111")
        assert len(challenges) == 1
        assert challenges[0].challenge_id == "ch_123"


class TestChallengeLifecycle:
    """Test accept/decline flow."""

    def test_accept_challenge(self, challenge_service, mock_firestore):
        """Partner accepts a pending challenge."""
        result = challenge_service.accept_challenge("ch_123")
        assert result is True
        mock_firestore.db.collection.return_value.document.return_value.update.assert_called_with(
            {"status": "active"}
        )

    def test_decline_challenge(self, challenge_service, mock_firestore):
        """Partner declines a pending challenge."""
        result = challenge_service.decline_challenge("ch_123")
        assert result is True
        mock_firestore.db.collection.return_value.document.return_value.update.assert_called_with(
            {"status": "cancelled"}
        )


class TestProgressTracking:
    """Test progress evaluation from check-ins."""

    def test_sleep_challenge_met(self, challenge_service, mock_firestore):
        """Sleep challenge: 7+ hours = met."""
        challenge = PartnerChallenge(
            challenge_id="ch_123",
            challenger_id="111",
            partner_id="222",
            challenge_type="sleep_7_days",
            title="Sleep",
            description="Test",
            start_date="2026-02-01",
            end_date="2026-02-07",
            status="active",
            progress={},
        )

        # Mock get_user_challenges to return this challenge
        challenge_service.get_user_challenges = lambda uid, status=None: [challenge]

        checkin = DailyCheckIn(
            date="2026-02-01",
            user_id="111",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=True, deep_work=True,
                skill_building=True, zero_porn=True, boundaries=True,
            ),
            responses=CheckInResponses(
                challenges="Test challenges for the day with enough characters",
                rating=5,
                rating_reason="Bad day with poor sleep and low energy levels",
                tomorrow_priority="Sleep better tonight and establish routine",
                tomorrow_obstacle="Late night work might interfere with bedtime",
            ),
            compliance_score=100.0,
        )

        updated = challenge_service.update_progress_from_checkin(checkin)
        assert len(updated) == 1
        assert updated[0].challenge_id == "ch_123"
        assert updated[0].progress["111"][0]["met"] is True

    def test_sleep_challenge_missed(self, challenge_service, mock_firestore):
        """Sleep challenge: <7 hours = missed."""
        challenge = PartnerChallenge(
            challenge_id="ch_123",
            challenger_id="111",
            partner_id="222",
            challenge_type="sleep_7_days",
            title="Sleep",
            description="Test",
            start_date="2026-02-01",
            end_date="2026-02-07",
            status="active",
            progress={},
        )

        challenge_service.get_user_challenges = lambda uid, status=None: [challenge]

        checkin = DailyCheckIn(
            date="2026-02-01",
            user_id="111",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=False, sleep_hours=5.5,
                training=True, deep_work=True,
                skill_building=True, zero_porn=True, boundaries=True,
            ),
            responses=CheckInResponses(
                challenges="Test challenges for the day with enough characters",
                rating=5,
                rating_reason="Bad day with poor sleep and low energy levels",
                tomorrow_priority="Sleep better tonight and establish routine",
                tomorrow_obstacle="Late night work might interfere with bedtime",
            ),
            compliance_score=50.0,
        )

        updated = challenge_service.update_progress_from_checkin(checkin)
        assert len(updated) == 1
        assert updated[0].progress["111"][0]["met"] is False

    def test_training_challenge_met_with_intensity(self, challenge_service, mock_firestore):
        """Training challenge: any intensity = met."""
        challenge = PartnerChallenge(
            challenge_id="ch_123",
            challenger_id="111",
            partner_id="222",
            challenge_type="training_5_days",
            title="Training",
            description="Test",
            start_date="2026-02-01",
            end_date="2026-02-07",
            status="active",
            progress={},
        )

        challenge_service.get_user_challenges = lambda uid, status=None: [challenge]

        checkin = DailyCheckIn(
            date="2026-02-01",
            user_id="111",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=True, training_intensity="moderate",
                deep_work=True, skill_building=True, zero_porn=True, boundaries=True,
            ),
            responses=CheckInResponses(
                challenges="Test challenges for the day with enough characters",
                rating=5,
                rating_reason="Bad day with poor sleep and low energy levels",
                tomorrow_priority="Sleep better tonight and establish routine",
                tomorrow_obstacle="Late night work might interfere with bedtime",
            ),
            compliance_score=100.0,
        )

        updated = challenge_service.update_progress_from_checkin(checkin)
        assert len(updated) == 1
        assert updated[0].progress["111"][0]["met"] is True

    def test_deep_work_challenge_met(self, challenge_service, mock_firestore):
        """Deep work challenge: 2+ hours = met."""
        challenge = PartnerChallenge(
            challenge_id="ch_123",
            challenger_id="111",
            partner_id="222",
            challenge_type="deep_work_7_days",
            title="Deep Work",
            description="Test",
            start_date="2026-02-01",
            end_date="2026-02-07",
            status="active",
            progress={},
        )

        challenge_service.get_user_challenges = lambda uid, status=None: [challenge]

        checkin = DailyCheckIn(
            date="2026-02-01",
            user_id="111",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=True, deep_work=True, deep_work_hours=3.0,
                skill_building=True, zero_porn=True, boundaries=True,
            ),
            responses=CheckInResponses(
                challenges="Test challenges for the day with enough characters",
                rating=5,
                rating_reason="Bad day with poor sleep and low energy levels",
                tomorrow_priority="Sleep better tonight and establish routine",
                tomorrow_obstacle="Late night work might interfere with bedtime",
            ),
            compliance_score=100.0,
        )

        updated = challenge_service.update_progress_from_checkin(checkin)
        assert len(updated) == 1
        assert updated[0].progress["111"][0]["met"] is True

    def test_date_outside_range_skipped(self, challenge_service, mock_firestore):
        """Check-in outside challenge date range is skipped."""
        challenge = PartnerChallenge(
            challenge_id="ch_123",
            challenger_id="111",
            partner_id="222",
            challenge_type="sleep_7_days",
            title="Sleep",
            description="Test",
            start_date="2026-02-10",
            end_date="2026-02-16",
            status="active",
            progress={},
        )

        challenge_service.get_user_challenges = lambda uid, status=None: [challenge]

        checkin = DailyCheckIn(
            date="2026-02-01",
            user_id="111",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=True, sleep_hours=7.5,
                training=True, deep_work=True,
                skill_building=True, zero_porn=True, boundaries=True,
            ),
            responses=CheckInResponses(
                challenges="Test challenges for the day with enough characters",
                rating=5,
                rating_reason="Bad day with poor sleep and low energy levels",
                tomorrow_priority="Sleep better tonight and establish routine",
                tomorrow_obstacle="Late night work might interfere with bedtime",
            ),
            compliance_score=100.0,
        )

        updated = challenge_service.update_progress_from_checkin(checkin)
        assert len(updated) == 0


class TestCompletion:
    """Test challenge completion detection."""

    def test_challenger_wins(self, challenge_service, mock_firestore):
        """Challenger has more met days."""
        challenge = PartnerChallenge(
            challenge_id="ch_123",
            challenger_id="111",
            partner_id="222",
            challenge_type="sleep_7_days",
            title="Sleep",
            description="Test",
            start_date="2026-01-01",
            end_date="2026-01-07",
            status="active",
            progress={
                "111": [
                    {"date": "2026-01-01", "met": True},
                    {"date": "2026-01-02", "met": True},
                    {"date": "2026-01-03", "met": True},
                    {"date": "2026-01-04", "met": True},
                    {"date": "2026-01-05", "met": True},
                    {"date": "2026-01-06", "met": True},
                    {"date": "2026-01-07", "met": True},
                ],
                "222": [
                    {"date": "2026-01-01", "met": True},
                    {"date": "2026-01-02", "met": True},
                    {"date": "2026-01-03", "met": True},
                    {"date": "2026-01-04", "met": True},
                    {"date": "2026-01-05", "met": True},
                    {"date": "2026-01-06", "met": False},
                    {"date": "2026-01-07", "met": False},
                ],
            },
        )

        with patch("src.utils.timezone_utils.get_current_date", return_value="2026-01-08"):
            winner = challenge_service.check_completion(challenge)

        assert winner == "111"

    def test_partner_wins(self, challenge_service, mock_firestore):
        """Partner has more met days."""
        challenge = PartnerChallenge(
            challenge_id="ch_123",
            challenger_id="111",
            partner_id="222",
            challenge_type="sleep_7_days",
            title="Sleep",
            description="Test",
            start_date="2026-01-01",
            end_date="2026-01-07",
            status="active",
            progress={
                "111": [
                    {"date": "2026-01-01", "met": True},
                    {"date": "2026-01-02", "met": False},
                ],
                "222": [
                    {"date": "2026-01-01", "met": True},
                    {"date": "2026-01-02", "met": True},
                ],
            },
        )

        with patch("src.utils.timezone_utils.get_current_date", return_value="2026-01-08"):
            winner = challenge_service.check_completion(challenge)

        assert winner == "222"

    def test_tie(self, challenge_service, mock_firestore):
        """Equal met days = tie."""
        challenge = PartnerChallenge(
            challenge_id="ch_123",
            challenger_id="111",
            partner_id="222",
            challenge_type="sleep_7_days",
            title="Sleep",
            description="Test",
            start_date="2026-01-01",
            end_date="2026-01-07",
            status="active",
            progress={
                "111": [
                    {"date": "2026-01-01", "met": True},
                    {"date": "2026-01-02", "met": True},
                ],
                "222": [
                    {"date": "2026-01-01", "met": True},
                    {"date": "2026-01-02", "met": True},
                ],
            },
        )

        with patch("src.utils.timezone_utils.get_current_date", return_value="2026-01-08"):
            winner = challenge_service.check_completion(challenge)

        assert winner == "tie"

    def test_not_yet_complete(self, challenge_service, mock_firestore):
        """Before end_date, returns None."""
        challenge = PartnerChallenge(
            challenge_id="ch_123",
            challenger_id="111",
            partner_id="222",
            challenge_type="sleep_7_days",
            title="Sleep",
            description="Test",
            start_date="2026-01-01",
            end_date="2026-01-07",
            status="active",
            progress={},
        )

        with patch("src.utils.timezone_utils.get_current_date", return_value="2026-01-05"):
            winner = challenge_service.check_completion(challenge)

        assert winner is None
