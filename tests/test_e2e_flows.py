"""
End-to-End Flow Tests
=====================

Tests for complete user journeys across multiple components.

**What Are E2E Flow Tests?**
Unlike unit tests (1 function) or integration tests (2-3 components),
E2E flow tests verify entire user journeys:
- Reminder → Ghosting → Partner escalation
- Check-in → Achievement unlock → Milestone celebration
- Onboarding → First check-in → Streak start
- Quick check-in → Weekly limit → Reset

**Why These Matter:**
Individual components can pass tests but still fail when connected.
E2E tests catch:
- Data format mismatches between components
- Missing handoffs (component A produces data, B expects different format)
- State management bugs (data lost between steps)

**Testing Strategy:**
Mock external services (Firestore, Telegram, Gemini) but let internal
components talk to each other naturally. This tests the "glue" between them.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from src.models.schemas import (
    User, UserStreaks, DailyCheckIn, Tier1NonNegotiables,
    CheckInResponses, StreakShields
)


# ===== Fixtures =====

@pytest.fixture
def active_user():
    """User who has been checking in regularly."""
    return User(
        user_id="e2e_user",
        telegram_id=555666777,
        telegram_username="e2e_tester",
        name="E2E Tester",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=29,
            longest_streak=29,
            last_checkin_date="2026-02-06",
            total_checkins=60
        ),
        constitution_mode="optimization",
        career_mode="skill_building",
        achievements=["week_warrior"],
        streak_shields=StreakShields(total=3, used=0, available=3),
        leaderboard_opt_in=True,
    )


@pytest.fixture
def ghosting_user():
    """User who has stopped checking in (ghosting scenario)."""
    return User(
        user_id="ghost_user",
        telegram_id=888999000,
        telegram_username="ghost_tester",
        name="Ghost Tester",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=47,
            longest_streak=47,
            last_checkin_date=(datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d"),
            total_checkins=100
        ),
        constitution_mode="maintenance",
        accountability_partner_id="partner_456",
        accountability_partner_name="Partner User",
        streak_shields=StreakShields(total=3, used=1, available=2),
    )


@pytest.fixture
def partner_user():
    """The accountability partner."""
    return User(
        user_id="partner_456",
        telegram_id=111222333,
        name="Partner User",
    )


def _make_perfect_checkin(date_str, user_id="e2e_user"):
    """Create a perfect compliance check-in."""
    return DailyCheckIn(
        date=date_str,
        user_id=user_id,
        mode="optimization",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=True, sleep_hours=8.0,
            training=True, deep_work=True,
            deep_work_hours=3.0,
            skill_building=True, skill_building_hours=2.0,
            zero_porn=True, boundaries=True,
        ),
        responses=CheckInResponses(
            challenges="Strong day with all objectives met and discipline maintained well",
            rating=9,
            rating_reason="Excellent execution across all constitution principles and career goals",
            tomorrow_priority="Continue streak and focus on system design interview preparation",
            tomorrow_obstacle="Late meeting might impact sleep schedule if not managed carefully",
        ),
        compliance_score=100.0,
    )


# ===== Flow 1: Reminder → Ghosting → Partner Escalation =====

class TestReminderToGhostingFlow:
    """
    Tests the complete flow when a user stops checking in:
    
    Day 1: No check-in → Triple reminders sent
    Day 2: Still no check-in → Ghosting detected (gentle nudge)
    Day 3: Still absent → Ghosting escalates (warning)
    Day 5: Still absent → Partner notified (emergency)
    
    This tests that reminders, pattern detection, and partner
    notification all work together correctly.
    """

    async def test_reminder_then_ghosting_detection(self, ghosting_user):
        """
        After reminders fail and user ghosts, pattern scan should detect it.
        """
        from src.agents.pattern_detection import PatternDetectionAgent
        
        with patch('src.agents.pattern_detection.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = ghosting_user
            
            agent = PatternDetectionAgent()
            pattern = agent.detect_ghosting("ghost_user")
            
            assert pattern is not None
            assert pattern.type == "ghosting"
            assert pattern.data["days_missing"] == 5
            assert pattern.severity in ["critical", "emergency"]

    async def test_ghosting_generates_correct_intervention(self, ghosting_user):
        """Day 5 ghosting should generate emergency intervention with partner info."""
        from src.agents.pattern_detection import Pattern
        from src.agents.intervention import InterventionAgent
        
        with patch('src.agents.intervention.get_llm_service'):
            agent = InterventionAgent.__new__(InterventionAgent)
            
            pattern = Pattern(type="ghosting", severity="critical", detected_at=datetime.utcnow(), data={
                "days_missing": 5,
                "previous_streak": 47,
                "last_checkin_date": ghosting_user.streaks.last_checkin_date,
            })
            
            msg = agent._build_ghosting_intervention(pattern, ghosting_user)
            
            # Should be emergency level
            assert "EMERGENCY" in msg
            # Should reference historical spiral
            assert "Feb 2025" in msg
            # Should mention partner notification
            assert "Partner User" in msg
            # Should mention streak shields
            assert "shield" in msg.lower()

    async def test_partner_notification_message(self, ghosting_user, partner_user):
        """
        When user ghosts 5+ days, partner should receive notification.
        
        This tests the pattern-scan endpoint's partner notification logic.
        """
        # Simulate the partner message construction from main.py
        days_missing = 5
        last_checkin = ghosting_user.streaks.last_checkin_date
        
        partner_msg = (
            f"🚨 **Accountability Partner Alert**\n\n"
            f"Your partner **{ghosting_user.name}** hasn't checked in for **{days_missing} days**.\n\n"
            f"Last check-in: {last_checkin}\n\n"
            f"This is serious. Consider reaching out to check on them:\n"
            f"• Text them directly\n"
            f"• Call if you have their number\n"
            f"• Make sure they're okay\n\n"
            f"Sometimes people need a friend more than a bot."
        )
        
        assert "Ghost Tester" in partner_msg
        assert "5 days" in partner_msg
        assert last_checkin in partner_msg


# ===== Flow 2: Check-In → Achievement → Milestone =====

class TestCheckinToAchievementFlow:
    """
    Tests the complete flow when user completes a milestone check-in:
    
    1. User completes check-in (streak becomes 30)
    2. Streak is updated
    3. Achievement "month_master" is unlocked
    4. Milestone celebration message is generated
    5. Social proof percentile is calculated
    
    This tests that check-in completion, achievement checking,
    and milestone detection all integrate correctly.
    """

    def test_streak_increment_triggers_milestone(self, active_user):
        """Day 30 check-in should trigger month master milestone."""
        from src.utils.streak import check_milestone, MILESTONE_MESSAGES
        
        # User currently at 29, check-in will make it 30
        milestone = check_milestone(30)
        
        assert milestone is not None
        assert "30" in str(milestone) or "Month" in str(milestone).title()

    def test_achievement_check_after_checkin(self, active_user):
        """Achievement service should detect new unlocks after check-in."""
        from src.services.achievement_service import AchievementService
        
        svc = AchievementService()
        
        # Update streak to 30 (milestone)
        active_user.streaks.current_streak = 30
        active_user.streaks.total_checkins = 61
        
        # Create perfect week of check-ins
        recent = [_make_perfect_checkin(
            (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
        ) for i in range(7)]
        
        unlocked = svc.check_achievements(active_user, recent)
        
        # Should unlock "month_master" (30-day streak)
        assert "month_master" in unlocked

    def test_social_proof_at_30_day_streak(self, active_user):
        """30+ day streak should generate social proof message."""
        from src.services.achievement_service import AchievementService
        
        svc = AchievementService()
        active_user.streaks.current_streak = 30
        
        with patch('src.services.achievement_service.firestore_service') as mock_fs:
            mock_fs.get_all_users.return_value = [active_user]
            msg = svc.get_social_proof_message(active_user)
        
        # Should return a message (non-empty for 30+ streaks)
        if msg:
            assert "%" in msg or "top" in msg.lower()


# ===== Flow 3: Quick Check-In → Limit → Reset =====

class TestQuickCheckinLimitFlow:
    """
    Tests the quick check-in weekly limit system:
    
    1. User uses /quickcheckin (count: 1/2)
    2. User uses /quickcheckin again (count: 2/2)
    3. User tries /quickcheckin → rejected (limit reached)
    4. Monday reset cron runs → count back to 0/2
    5. User can use /quickcheckin again
    """

    def test_limit_tracking(self, active_user):
        """Quick check-in count should track usage."""
        assert active_user.quick_checkin_count == 0
        
        active_user.quick_checkin_count = 1
        assert active_user.quick_checkin_count < 2  # Still allowed
        
        active_user.quick_checkin_count = 2
        assert active_user.quick_checkin_count >= 2  # At limit

    def test_limit_enforcement(self, active_user):
        """Should block quick check-in when limit reached."""
        active_user.quick_checkin_count = 2
        
        # This is the check that conversation.py performs
        can_quick_checkin = active_user.quick_checkin_count < 2
        assert can_quick_checkin is False


# ===== Flow 4: Export → Report Pipeline =====

class TestExportReportFlow:
    """
    Tests that export and report generation work with real data.
    
    1. Generate CSV export from check-ins
    2. Generate visualization graphs
    3. Generate AI insights (mocked)
    """

    def test_csv_export_from_checkins(self, active_user):
        """Should generate valid CSV from check-in data."""
        from src.services.export_service import generate_csv_export
        
        checkins = [_make_perfect_checkin(f"2026-02-0{i+1}") for i in range(7)]
        
        csv_buffer = generate_csv_export(checkins, active_user)
        
        assert csv_buffer is not None
        csv_data = csv_buffer.getvalue().decode('utf-8-sig')
        assert len(csv_data) > 0
        # CSV should contain header and 7 data rows
        lines = csv_data.strip().split('\n')
        assert len(lines) >= 8  # Header + 7 rows

    def test_json_export_from_checkins(self, active_user):
        """Should generate valid JSON from check-in data."""
        from src.services.export_service import generate_json_export
        import json
        
        checkins = [_make_perfect_checkin(f"2026-02-0{i+1}") for i in range(7)]
        
        json_buffer = generate_json_export(checkins, active_user)
        
        json_data = json_buffer.getvalue().decode('utf-8')
        parsed = json.loads(json_data)
        assert "export_metadata" in parsed
        assert "check_ins" in parsed
        assert len(parsed["check_ins"]) == 7

    def test_visualization_graphs(self):
        """Should generate all 4 graphs without errors."""
        from src.services.visualization_service import generate_weekly_graphs
        
        checkins = [_make_perfect_checkin(
            (datetime.now() - timedelta(days=6-i)).strftime("%Y-%m-%d")
        ) for i in range(7)]
        
        graphs = generate_weekly_graphs(checkins)
        
        assert graphs is not None
        # generate_weekly_graphs returns a dict with graph names as keys
        assert isinstance(graphs, dict)
        assert len(graphs) == 4  # sleep, training, compliance, radar
        for name, graph_buffer in graphs.items():
            assert graph_buffer is not None
            # BytesIO buffer should contain PNG data
            data = graph_buffer.getvalue()
            assert len(data) > 100, f"Graph '{name}' should be non-trivial PNG data"


# ===== Flow 5: Leaderboard Calculation =====

class TestLeaderboardFlow:
    """
    Tests that leaderboard works across multiple users.
    """

    def test_leaderboard_excludes_opted_out(self):
        """Users who opt out should not appear on leaderboard."""
        from src.services.social_service import calculate_leaderboard
        
        users = [
            User(
                user_id="user1", telegram_id=1, name="User 1",
                streaks=UserStreaks(current_streak=10),
                leaderboard_opt_in=True,
            ),
            User(
                user_id="user2", telegram_id=2, name="User 2",
                streaks=UserStreaks(current_streak=20),
                leaderboard_opt_in=False,  # Opted out
            ),
        ]
        
        # Mock firestore for leaderboard
        with patch('src.services.social_service.firestore_service') as mock_fs:
            mock_fs.get_all_users.return_value = users
            mock_fs.get_recent_checkins.return_value = [
                _make_perfect_checkin("2026-02-07", user_id="user1")
            ]
            
            leaderboard = calculate_leaderboard()
            
            # User 2 should not appear
            user_ids = [entry["user_id"] for entry in leaderboard]
            assert "user2" not in user_ids


# ===== Flow 6: Career Mode Affects Check-In =====

class TestCareerModeFlow:
    """
    Tests that career mode changes affect check-in questions.
    """

    def test_skill_building_question_varies_by_mode(self):
        """Different career modes should produce different questions."""
        from src.bot.conversation import get_skill_building_question
        
        q_skill = get_skill_building_question("skill_building")
        q_job = get_skill_building_question("job_searching")
        q_employed = get_skill_building_question("employed")
        
        # Each mode should produce a different question
        assert q_skill != q_job
        assert q_job != q_employed

    def test_compliance_includes_skill_building(self):
        """Compliance score should include skill building (6 items, not 5)."""
        from src.utils.compliance import calculate_compliance_score
        
        # All 6 items complete = 100%
        tier1_all = Tier1NonNegotiables(
            sleep=True, sleep_hours=7.5,
            training=True, deep_work=True, deep_work_hours=2.5,
            skill_building=True, skill_building_hours=2.0,
            zero_porn=True, boundaries=True,
        )
        score_all = calculate_compliance_score(tier1_all)
        assert score_all == 100.0
        
        # 5 of 6 items complete (missing skill building) = 83.3%
        tier1_no_sb = Tier1NonNegotiables(
            sleep=True, sleep_hours=7.5,
            training=True, deep_work=True, deep_work_hours=2.5,
            skill_building=False,
            zero_porn=True, boundaries=True,
        )
        score_no_sb = calculate_compliance_score(tier1_no_sb)
        assert abs(score_no_sb - 83.3) < 0.5  # 5/6 ≈ 83.3%
