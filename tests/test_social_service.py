"""
Unit Tests for Social Service (Phase 3F)
==========================================

Tests leaderboard, referral system, and shareable stats.

**Testing Strategy:**
- Leaderboard and referral functions depend on Firestore (get_all_users, get_recent_checkins)
- We mock firestore_service using unittest.mock.patch
- Shareable stats image generation is a pure function (User, List[DailyCheckIn]) -> BytesIO
- Format functions are tested for HTML output structure

**Theory: Mocking External Dependencies**
Unit tests should be FAST and DETERMINISTIC. Firestore calls are:
1. Slow (network round trip)
2. Non-deterministic (data changes between runs)
3. Require credentials (won't work in CI)

We use unittest.mock.patch to replace firestore_service with a mock
that returns controlled test data. This isolates the business logic
from the infrastructure layer.

Run tests:
    pytest tests/test_social_service.py -v
"""

import pytest
import io
from unittest.mock import patch, MagicMock

from src.services.social_service import (
    calculate_leaderboard,
    format_leaderboard_message,
    generate_referral_link,
    get_referral_stats,
    format_referral_message,
    generate_shareable_stats_image,
)
from src.models.schemas import User, UserStreaks, DailyCheckIn, Tier1NonNegotiables, CheckInResponses


# ===== Fixtures =====

@pytest.fixture
def mock_users():
    """Create a set of mock users for leaderboard testing."""
    users = []
    for i, (name, streak, opt_in) in enumerate([
        ("Alice", 30, True),
        ("Bob", 15, True),
        ("Charlie", 7, True),
        ("Diana", 50, False),  # Opted out
        ("Eve", 2, True),      # Low streak
    ]):
        users.append(User(
            user_id=str(100 + i),
            telegram_id=100 + i,
            name=name,
            timezone="Asia/Kolkata",
            streaks=UserStreaks(current_streak=streak, longest_streak=streak, total_checkins=streak),
            leaderboard_opt_in=opt_in,
        ))
    return users


@pytest.fixture
def mock_checkins_map():
    """
    Map of user_id -> list of check-ins for mock data.
    Used by the mock get_recent_checkins.
    """
    def make_checkins(user_id, count, avg_score):
        checkins = []
        for j in range(count):
            checkins.append(DailyCheckIn(
                date=f"2026-02-{j+1:02d}",
                user_id=user_id,
                mode="maintenance",
                tier1_non_negotiables=Tier1NonNegotiables(
                    sleep=True, training=True, deep_work=True,
                    zero_porn=True, boundaries=True,
                ),
                responses=CheckInResponses(
                    challenges="Test challenge for leaderboard mock data checkin entry today",
                    rating=8,
                    rating_reason="Good day overall with solid progress on all key habit areas",
                    tomorrow_priority="Continue building momentum and maintain current consistency",
                    tomorrow_obstacle="Time management might be tricky with upcoming commitments",
                ),
                compliance_score=avg_score,
            ))
        return checkins
    
    return {
        "100": make_checkins("100", 7, 95.0),   # Alice - high compliance
        "101": make_checkins("101", 5, 85.0),   # Bob - medium compliance
        "102": make_checkins("102", 4, 70.0),   # Charlie - lower compliance
        "103": make_checkins("103", 7, 99.0),   # Diana - opted out
        "104": make_checkins("104", 2, 90.0),   # Eve - too few check-ins
    }


# ===== Referral Link Tests =====

class TestReferralLink:
    """Tests for referral link generation."""
    
    def test_generates_correct_format(self):
        """
        Referral link should follow Telegram deep-link format.
        
        **Theory: Telegram Deep Links**
        t.me/{botname}?start={payload} is Telegram's standard format
        for bot deep links. When clicked, Telegram sends /start {payload}
        to the bot, which we parse in start_command.
        """
        link = generate_referral_link("123456", "my_bot")
        assert link == "https://t.me/my_bot?start=ref_123456"
    
    def test_includes_user_id(self):
        """The user ID should be embedded in the referral link."""
        link = generate_referral_link("999", "test_bot")
        assert "ref_999" in link
    
    def test_includes_bot_username(self):
        """The bot username should be in the link domain."""
        link = generate_referral_link("123", "accountability_bot")
        assert "accountability_bot" in link


# ===== Leaderboard Tests =====

class TestLeaderboard:
    """Tests for leaderboard calculation."""
    
    @patch('src.services.social_service.firestore_service')
    def test_excludes_opted_out_users(self, mock_fs, mock_users, mock_checkins_map):
        """
        Users with leaderboard_opt_in=False should NOT appear.
        
        **Theory: Privacy-First Design**
        Privacy is a feature, not an afterthought. Users who opt out
        of the leaderboard should never appear, regardless of their
        performance. This is a hard filter, not a soft preference.
        """
        mock_fs.get_all_users.return_value = mock_users
        mock_fs.get_recent_checkins.side_effect = lambda uid, days: mock_checkins_map.get(uid, [])
        
        result = calculate_leaderboard(period_days=7)
        
        user_ids = [e["user_id"] for e in result]
        assert "103" not in user_ids  # Diana opted out
    
    @patch('src.services.social_service.firestore_service')
    def test_excludes_insufficient_checkins(self, mock_fs, mock_users, mock_checkins_map):
        """Users with fewer than 3 check-ins should be excluded."""
        mock_fs.get_all_users.return_value = mock_users
        mock_fs.get_recent_checkins.side_effect = lambda uid, days: mock_checkins_map.get(uid, [])
        
        result = calculate_leaderboard(period_days=7)
        
        user_ids = [e["user_id"] for e in result]
        assert "104" not in user_ids  # Eve only has 2 check-ins
    
    @patch('src.services.social_service.firestore_service')
    def test_ranks_by_compliance_score(self, mock_fs, mock_users, mock_checkins_map):
        """Higher compliance should result in higher rank."""
        mock_fs.get_all_users.return_value = mock_users
        mock_fs.get_recent_checkins.side_effect = lambda uid, days: mock_checkins_map.get(uid, [])
        
        result = calculate_leaderboard(period_days=7)
        
        # Alice (95%) should rank higher than Bob (85%)
        alice = next(e for e in result if e["user_id"] == "100")
        bob = next(e for e in result if e["user_id"] == "101")
        assert alice["rank"] < bob["rank"]
    
    @patch('src.services.social_service.firestore_service')
    def test_entries_have_required_fields(self, mock_fs, mock_users, mock_checkins_map):
        """Each leaderboard entry should have required fields."""
        mock_fs.get_all_users.return_value = mock_users
        mock_fs.get_recent_checkins.side_effect = lambda uid, days: mock_checkins_map.get(uid, [])
        
        result = calculate_leaderboard(period_days=7)
        
        for entry in result:
            assert "rank" in entry
            assert "name" in entry
            assert "compliance" in entry
            assert "streak" in entry
            assert "score" in entry
    
    @patch('src.services.social_service.firestore_service')
    def test_respects_top_n_limit(self, mock_fs, mock_users, mock_checkins_map):
        """Should only return top N entries."""
        mock_fs.get_all_users.return_value = mock_users
        mock_fs.get_recent_checkins.side_effect = lambda uid, days: mock_checkins_map.get(uid, [])
        
        result = calculate_leaderboard(period_days=7, top_n=2)
        assert len(result) <= 2
    
    @patch('src.services.social_service.firestore_service')
    def test_empty_users(self, mock_fs):
        """Leaderboard should return empty list when no users exist."""
        mock_fs.get_all_users.return_value = []
        
        result = calculate_leaderboard()
        assert result == []


# ===== Leaderboard Format Tests =====

class TestFormatLeaderboard:
    """Tests for leaderboard message formatting."""
    
    def test_empty_entries_shows_encouraging_message(self):
        """Empty leaderboard should show encouraging message."""
        result = format_leaderboard_message([], "123")
        assert "Not enough data" in result
        assert "/checkin" in result
    
    def test_top_3_have_medal_emojis(self):
        """Top 3 entries should have medal emojis (🥇🥈🥉)."""
        entries = [
            {"rank": 1, "user_id": "1", "name": "Alice", "compliance": 95, "streak": 30},
            {"rank": 2, "user_id": "2", "name": "Bob", "compliance": 90, "streak": 20},
            {"rank": 3, "user_id": "3", "name": "Charlie", "compliance": 85, "streak": 10},
        ]
        
        result = format_leaderboard_message(entries, "999")
        assert "🥇" in result
        assert "🥈" in result
        assert "🥉" in result
    
    def test_requesting_user_highlighted(self):
        """Requesting user should see '(You)' next to their name."""
        entries = [
            {"rank": 1, "user_id": "1", "name": "Alice", "compliance": 95, "streak": 30},
            {"rank": 2, "user_id": "2", "name": "Bob", "compliance": 90, "streak": 20},
        ]
        
        result = format_leaderboard_message(entries, "1")
        assert "(You)" in result
    
    def test_uses_html_formatting(self):
        """Message should use HTML formatting for Telegram."""
        entries = [
            {"rank": 1, "user_id": "1", "name": "Alice", "compliance": 95, "streak": 30},
        ]
        
        result = format_leaderboard_message(entries, "1")
        assert "<b>" in result


# ===== Referral Format Tests =====

class TestFormatReferral:
    """Tests for referral message formatting."""
    
    def test_includes_referral_link(self):
        """Message should display the referral link."""
        link = "https://t.me/bot?start=ref_123"
        stats = {"total_referrals": 5, "active_referrals": 3, "reward_percentage": 3}
        
        result = format_referral_message(link, stats)
        assert link in result
    
    def test_shows_stats(self):
        """Message should display referral statistics."""
        stats = {"total_referrals": 5, "active_referrals": 3, "reward_percentage": 3}
        
        result = format_referral_message("https://t.me/bot?start=ref_123", stats)
        assert "5" in result  # total
        assert "3" in result  # active
    
    def test_shows_reward_info(self):
        """Message should explain the reward system."""
        stats = {"total_referrals": 0, "active_referrals": 0, "reward_percentage": 0}
        
        result = format_referral_message("https://t.me/bot?start=ref_123", stats)
        assert "Reward" in result or "reward" in result


# ===== Referral Stats Tests =====

class TestReferralStats:
    """Tests for referral statistics calculation."""
    
    @patch('src.services.social_service.firestore_service')
    def test_counts_referrals(self, mock_fs):
        """Should count users who were referred by the given user."""
        referred_user = User(
            user_id="200", telegram_id=200, name="Referred",
            timezone="Asia/Kolkata", referred_by="100",
        )
        other_user = User(
            user_id="201", telegram_id=201, name="Other",
            timezone="Asia/Kolkata", referred_by="999",  # Different referrer
        )
        mock_fs.get_all_users.return_value = [referred_user, other_user]
        mock_fs.get_recent_checkins.return_value = []
        
        stats = get_referral_stats("100")
        assert stats["total_referrals"] == 1
    
    @patch('src.services.social_service.firestore_service')
    def test_active_referral_threshold(self, mock_fs):
        """Active referral requires 7+ check-ins in 30 days."""
        referred = User(
            user_id="200", telegram_id=200, name="Referred",
            timezone="Asia/Kolkata", referred_by="100",
        )
        mock_fs.get_all_users.return_value = [referred]
        
        # Give 7 check-ins → should be active
        mock_fs.get_recent_checkins.return_value = [MagicMock()] * 7
        
        stats = get_referral_stats("100")
        assert stats["active_referrals"] == 1
    
    @patch('src.services.social_service.firestore_service')
    def test_reward_capped_at_5(self, mock_fs):
        """Reward should cap at 5% even with many active referrals."""
        # Create 10 referred users
        users = []
        for i in range(10):
            users.append(User(
                user_id=str(200 + i), telegram_id=200 + i,
                name=f"User{i}", timezone="Asia/Kolkata", referred_by="100",
            ))
        mock_fs.get_all_users.return_value = users
        mock_fs.get_recent_checkins.return_value = [MagicMock()] * 10  # All active
        
        stats = get_referral_stats("100")
        assert stats["reward_percentage"] <= 5


# ===== Shareable Stats Image Tests =====

class TestShareableStatsImage:
    """Tests for shareable stats image generation."""
    
    def test_returns_bytesio(self, sample_user_3f, sample_week_checkins):
        """Should return BytesIO buffer."""
        result = generate_shareable_stats_image(sample_user_3f, sample_week_checkins)
        assert isinstance(result, io.BytesIO)
    
    def test_produces_valid_png(self, sample_user_3f, sample_week_checkins):
        """
        Output should be a valid PNG image.
        
        **Theory: Pillow Image Format**
        We save as PNG (lossless compression) rather than JPEG because:
        1. Text is crisp (no JPEG compression artifacts on text)
        2. Supports transparency (for potential future use)
        3. No quality degradation on re-sharing
        """
        result = generate_shareable_stats_image(sample_user_3f, sample_week_checkins)
        result.seek(0)
        magic = result.read(8)
        assert magic[:4] == b'\x89PNG', "Shareable stats image should be PNG format"
    
    def test_image_size_reasonable(self, sample_user_3f, sample_week_checkins):
        """Image should be reasonably sized (not too small, not too large)."""
        result = generate_shareable_stats_image(sample_user_3f, sample_week_checkins)
        size = result.getbuffer().nbytes
        assert size > 1_000, f"Image too small ({size} bytes)"
        assert size < 10_000_000, f"Image too large ({size} bytes)"
    
    def test_handles_empty_checkins(self, sample_user_3f):
        """Should generate image even with no check-in data."""
        result = generate_shareable_stats_image(sample_user_3f, [])
        assert isinstance(result, io.BytesIO)
        assert result.getbuffer().nbytes > 0


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
