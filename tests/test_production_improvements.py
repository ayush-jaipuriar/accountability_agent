"""
Production Improvements Tests (Phases 1-5)
==========================================

Comprehensive unit, integration, and regression tests for the 5 production
improvement phases:

  Phase 1: Intervention Cooldowns + Resolution
  Phase 2: Check-in Memory (Yesterday Context)
  Phase 3: Fuzzy Command Matching + NL Routing
  Phase 4: Deeper Per-Metric Tracking
  Phase 5: Automated Reports Every 3 Days

Run:
    pytest tests/test_production_improvements.py -v --no-cov
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, AsyncMock, patch

from src.models.schemas import (
    User, UserStreaks, StreakShields, DailyCheckIn,
    Tier1NonNegotiables, CheckInResponses,
)


# =====================================================================
# Helpers
# =====================================================================

def _make_user(**overrides) -> User:
    defaults = dict(
        user_id="111",
        telegram_id=111,
        telegram_username="testuser",
        name="TestUser",
        timezone="Asia/Kolkata",
        constitution_mode="maintenance",
        career_mode="skill_building",
        streaks=UserStreaks(
            current_streak=10, longest_streak=20,
            last_checkin_date="2026-02-07", total_checkins=50
        ),
        streak_shields=StreakShields(total=3, used=1, available=2),
        achievements=["week_warrior"],
        accountability_partner_id=None,
        accountability_partner_name=None,
    )
    defaults.update(overrides)
    return User(**defaults)


def _make_checkin(date_str, sleep=True, training=True, deep_work=True,
                  skill_building=False, zero_porn=True, boundaries=True,
                  sleep_hours=7.5, compliance=100.0) -> DailyCheckIn:
    return DailyCheckIn(
        date=date_str,
        user_id="111",
        mode="maintenance",
        tier1_non_negotiables=Tier1NonNegotiables(
            sleep=sleep, sleep_hours=sleep_hours,
            training=training, is_rest_day=False, training_type="workout",
            deep_work=deep_work, deep_work_hours=2.5 if deep_work else 0,
            skill_building=skill_building,
            zero_porn=zero_porn, boundaries=boundaries,
        ),
        responses=CheckInResponses(
            challenges="Test challenges text for today.",
            rating=8,
            rating_reason="Solid day overall with good progress.",
            tomorrow_priority="Complete deep work session tomorrow morning.",
            tomorrow_obstacle="Late meeting might drain my energy.",
        ),
        compliance_score=compliance,
        completed_at=datetime.utcnow(),
        duration_seconds=90,
    )


def _make_checkins(n_days, **overrides):
    """Build n_days of check-ins ending today."""
    base = datetime.utcnow()
    return [
        _make_checkin(
            (base - timedelta(days=n_days - 1 - i)).strftime("%Y-%m-%d"),
            **overrides,
        )
        for i in range(n_days)
    ]


def _make_update(user_id=111, text="/start"):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "TestUser"
    update.message = AsyncMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.message.reply_document = AsyncMock()
    update.message.reply_photo = AsyncMock()
    update.message.message_id = 1234
    return update


def _make_context(args=None, user_data=None):
    context = MagicMock()
    context.args = args or []
    context.user_data = user_data if user_data is not None else {}
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    context.bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
    return context


def _make_callback_update(user_id=111, data="fuzzy_cmd:help"):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "TestUser"
    query = AsyncMock()
    query.data = data
    query.from_user = MagicMock()
    query.from_user.id = user_id
    query.answer = AsyncMock()
    query.message = MagicMock()
    query.message.reply_text = AsyncMock()
    update.callback_query = query
    update.message = None
    return update


# =====================================================================
# Shared Bot Fixture (follows test_telegram_bot_commands.py pattern)
# =====================================================================

@pytest.fixture
def bot_manager():
    """TelegramBotManager with all external deps mocked."""
    with patch('src.bot.telegram_bot.Application') as MockApp, \
         patch('src.bot.telegram_bot.settings') as mock_settings, \
         patch('src.bot.telegram_bot.firestore_service') as mock_fs, \
         patch('src.bot.telegram_bot.rate_limiter') as mock_rl, \
         patch('src.bot.telegram_bot.metrics') as mock_metrics:

        mock_app = MagicMock()
        MockApp.builder.return_value.token.return_value.build.return_value = mock_app
        mock_app.bot = AsyncMock()

        mock_settings.telegram_bot_token = "fake_token"
        mock_settings.gcp_project_id = "test-project"
        mock_settings.admin_telegram_ids = "111"

        mock_rl.check.return_value = (True, None)

        from src.bot.telegram_bot import TelegramBotManager
        manager = TelegramBotManager(token="fake_token")

        manager._mock_fs = mock_fs
        manager._mock_rl = mock_rl
        manager._mock_metrics = mock_metrics
        manager._mock_settings = mock_settings

        yield manager


# =====================================================================
# Phase 1 — Intervention Cooldowns + Resolution
# =====================================================================

class TestPhase1CooldownFirestore:
    """Unit tests for has_recent_intervention and resolve_interventions."""

    @pytest.fixture
    def firestore_svc(self):
        with patch('src.services.firestore_service.firestore.Client') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance
            from src.services.firestore_service import FirestoreService
            svc = FirestoreService.__new__(FirestoreService)
            svc.db = mock_instance
            yield svc

    def test_has_recent_intervention_true(self, firestore_svc):
        """Returns True when a matching intervention exists within cooldown window."""
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {"pattern_type": "training_abandonment"}
        coll = MagicMock()
        coll.where.return_value = coll
        coll.stream.return_value = [mock_doc]

        firestore_svc.db.collection.return_value.document.return_value.collection.return_value = coll

        result = firestore_svc.has_recent_intervention("111", "training_abandonment", 48)
        assert result is True

    def test_has_recent_intervention_false_no_docs(self, firestore_svc):
        """Returns False when no interventions found in cooldown window."""
        coll = MagicMock()
        coll.where.return_value = coll
        coll.stream.return_value = []

        firestore_svc.db.collection.return_value.document.return_value.collection.return_value = coll

        result = firestore_svc.has_recent_intervention("111", "training_abandonment", 48)
        assert result is False

    def test_has_recent_intervention_false_wrong_pattern(self, firestore_svc):
        """Returns False when docs exist but none match the target pattern_type."""
        mock_doc = MagicMock()
        mock_doc.to_dict.return_value = {"pattern_type": "sleep_degradation"}
        coll = MagicMock()
        coll.where.return_value = coll
        coll.stream.return_value = [mock_doc]

        firestore_svc.db.collection.return_value.document.return_value.collection.return_value = coll

        result = firestore_svc.has_recent_intervention("111", "training_abandonment", 48)
        assert result is False

    def test_has_recent_intervention_uses_single_where(self, firestore_svc):
        """Query should use only one .where() call (sent_at range), not two."""
        coll = MagicMock()
        coll.where.return_value = coll
        coll.stream.return_value = []

        firestore_svc.db.collection.return_value.document.return_value.collection.return_value = coll

        firestore_svc.has_recent_intervention("111", "training_abandonment", 48)
        assert coll.where.call_count == 1, "Should use exactly 1 .where() to avoid composite index"

    def test_has_recent_intervention_error_failopen(self, firestore_svc):
        """On Firestore error, fail-open (return False) so interventions still send."""
        firestore_svc.db.collection.side_effect = Exception("Firestore down")
        result = firestore_svc.has_recent_intervention("111", "sleep_degradation", 24)
        assert result is False

    def test_resolve_interventions_marks_resolved(self, firestore_svc):
        """Marks all matching unresolved docs with resolved=True + timestamp."""
        doc1 = MagicMock()
        doc2 = MagicMock()

        coll = MagicMock()
        coll.where.return_value = coll
        coll.stream.return_value = [doc1, doc2]

        firestore_svc.db.collection.return_value.document.return_value.collection.return_value = coll

        count = firestore_svc.resolve_interventions("111", "training_abandonment")
        assert count == 2
        assert doc1.reference.update.called
        assert doc2.reference.update.called
        update_args = doc1.reference.update.call_args[0][0]
        assert update_args["resolved"] is True
        assert "resolved_at" in update_args

    def test_resolve_interventions_none_to_resolve(self, firestore_svc):
        """Returns 0 when no unresolved interventions exist."""
        coll = MagicMock()
        coll.where.return_value = coll
        coll.stream.return_value = []

        firestore_svc.db.collection.return_value.document.return_value.collection.return_value = coll

        count = firestore_svc.resolve_interventions("111", "porn_relapse")
        assert count == 0

    def test_resolve_interventions_error_returns_zero(self, firestore_svc):
        """On error, gracefully return 0 rather than crash."""
        firestore_svc.db.collection.side_effect = Exception("oops")
        count = firestore_svc.resolve_interventions("111", "training_abandonment")
        assert count == 0


class TestPhase1StalenessGuard:
    """Pattern detection should skip stale check-in data (> 7 days old)."""

    def test_stale_checkins_skipped(self):
        """Check-ins older than 7 days should produce no patterns."""
        with patch('src.services.firestore_service.firestore.Client'):
            from src.agents.pattern_detection import PatternDetectionAgent
            agent = PatternDetectionAgent.__new__(PatternDetectionAgent)

            old_date = (datetime.utcnow() - timedelta(days=10)).strftime("%Y-%m-%d")
            checkins = [
                _make_checkin(old_date, training=False, sleep=False),
            ] * 3
            patterns = agent.detect_patterns(checkins)
            assert patterns == []

    def test_fresh_checkins_detected(self):
        """Check-ins within 7 days should still trigger detection."""
        with patch('src.services.firestore_service.firestore.Client'):
            from src.agents.pattern_detection import PatternDetectionAgent
            agent = PatternDetectionAgent.__new__(PatternDetectionAgent)

            recent_date = (datetime.utcnow() - timedelta(days=1)).strftime("%Y-%m-%d")
            checkins = [
                _make_checkin(recent_date, training=False),
            ] * 3
            patterns = agent.detect_patterns(checkins)
            pattern_types = [p.type for p in patterns]
            assert "training_abandonment" in pattern_types

    def test_boundary_7_days_included(self):
        """Check-ins exactly 7 days old should still be processed."""
        with patch('src.services.firestore_service.firestore.Client'):
            from src.agents.pattern_detection import PatternDetectionAgent
            agent = PatternDetectionAgent.__new__(PatternDetectionAgent)

            boundary_date = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
            checkins = [
                _make_checkin(boundary_date, training=False),
            ] * 3
            patterns = agent.detect_patterns(checkins)
            pattern_types = [p.type for p in patterns]
            assert "training_abandonment" in pattern_types


# =====================================================================
# Phase 2 — Check-in Memory (Yesterday Context)
# =====================================================================

class TestPhase2YesterdayContext:
    """Tests for _build_yesterday_section on CheckInAgent."""

    @pytest.fixture
    def agent(self):
        with patch('src.services.firestore_service.firestore.Client'):
            from src.agents.checkin_agent import CheckInAgent
            a = CheckInAgent.__new__(CheckInAgent)
            yield a

    def test_with_data(self, agent):
        yesterday = {
            "compliance_score": 80.0,
            "rating": 7,
            "rating_reason": "Missed deep work",
            "tomorrow_priority": "Do 3 LeetCode problems",
            "tomorrow_obstacle": "Late meeting",
            "challenges": "Felt tired after lunch",
            "tier1": {
                "sleep": True, "training": False,
                "deep_work": True, "skill_building": False,
                "zero_porn": True, "boundaries": True,
            },
        }
        result = agent._build_yesterday_section(yesterday)
        assert "YESTERDAY'S CONTEXT" in result
        assert "80" in result
        assert "3 LeetCode problems" in result
        assert "training" in result.lower()

    def test_none_returns_empty(self, agent):
        result = agent._build_yesterday_section(None)
        assert result == ""

    def test_empty_dict_treated_as_none(self, agent):
        """Empty dict is falsy in Python, so it should behave like None."""
        result = agent._build_yesterday_section({})
        assert result == ""

    def test_generate_feedback_signature_accepts_yesterday(self):
        """Regression: generate_feedback must accept yesterday_checkin kwarg."""
        import inspect
        with patch('src.services.firestore_service.firestore.Client'):
            from src.agents.checkin_agent import CheckInAgent
            sig = inspect.signature(CheckInAgent.generate_feedback)
            assert "yesterday_checkin" in sig.parameters


# =====================================================================
# Phase 3 — Fuzzy Command Matching + NL Routing
# =====================================================================

class TestPhase3FuzzyMatching:
    """Unit tests for _fuzzy_match_command."""

    def test_fuzzy_staus(self, bot_manager):
        cmd, score = bot_manager._fuzzy_match_command("/staus")
        assert cmd == "status"
        assert score >= 0.85

    def test_fuzzy_parner_status(self, bot_manager):
        cmd, score = bot_manager._fuzzy_match_command("/parner_status")
        assert cmd == "partner_status"
        assert score >= 0.85

    def test_fuzzy_achivements(self, bot_manager):
        cmd, score = bot_manager._fuzzy_match_command("/achivements")
        assert cmd == "achievements"
        assert score >= 0.85

    def test_fuzzy_chckin(self, bot_manager):
        cmd, score = bot_manager._fuzzy_match_command("/chckin")
        assert cmd == "checkin"
        assert score >= 0.85

    def test_fuzzy_reportt(self, bot_manager):
        cmd, score = bot_manager._fuzzy_match_command("/reportt")
        assert cmd == "report"
        assert score >= 0.85

    def test_fuzzy_use_sheild(self, bot_manager):
        cmd, score = bot_manager._fuzzy_match_command("/use_sheild")
        assert cmd == "use_shield"
        assert score >= 0.85

    def test_fuzzy_helo_suggest(self, bot_manager):
        cmd, score = bot_manager._fuzzy_match_command("/helo")
        assert cmd == "help"
        assert score >= 0.60

    def test_fuzzy_gibberish_rejected(self, bot_manager):
        cmd, score = bot_manager._fuzzy_match_command("/xyzabc")
        assert score < 0.60

    def test_fuzzy_exact_match(self, bot_manager):
        cmd, score = bot_manager._fuzzy_match_command("/status")
        assert cmd == "status"
        assert score == 1.0

    def test_fuzzy_with_bot_suffix(self, bot_manager):
        """Commands like /status@my_bot should strip the @suffix."""
        cmd, score = bot_manager._fuzzy_match_command("/staus@my_bot")
        assert cmd == "status"
        assert score >= 0.80


class TestPhase3KeywordMatching:
    """Unit tests for _match_command_keywords."""

    def test_partner_status_keyword(self, bot_manager):
        assert bot_manager._match_command_keywords("how is my partner") == "partner_status"

    def test_status_keyword(self, bot_manager):
        assert bot_manager._match_command_keywords("show me my status") == "status"

    def test_checkin_keyword(self, bot_manager):
        assert bot_manager._match_command_keywords("I want to check in") == "checkin"

    def test_report_keyword(self, bot_manager):
        assert bot_manager._match_command_keywords("give me a report please") == "report"

    def test_help_keyword(self, bot_manager):
        assert bot_manager._match_command_keywords("what can you do?") == "help"

    def test_metrics_keyword(self, bot_manager):
        assert bot_manager._match_command_keywords("show my metrics dashboard") == "metrics"

    def test_no_match_returns_none(self, bot_manager):
        assert bot_manager._match_command_keywords("random unrelated message") is None

    def test_emotional_no_match(self, bot_manager):
        assert bot_manager._match_command_keywords("I feel sad today") is None

    def test_longest_match_wins(self, bot_manager):
        """'partner status' should beat 'status' for 'show partner status'."""
        assert bot_manager._match_command_keywords("show partner status") == "partner_status"

    def test_case_insensitive(self, bot_manager):
        assert bot_manager._match_command_keywords("WEEKLY STATS please") == "weekly"


class TestPhase3UnknownCommand:
    """Tests for handle_unknown_command handler."""

    @pytest.mark.asyncio
    async def test_auto_execute_high_score(self, bot_manager):
        """Score >= 0.85: auto-correct and call matched handler."""
        update = _make_update(text="/staus")
        context = _make_context()
        with patch.object(bot_manager, "_get_command_handler_map") as mock_map:
            handler = AsyncMock()
            mock_map.return_value = {"status": handler}
            await bot_manager.handle_unknown_command(update, context)
            calls = [c[0][0] for c in update.message.reply_text.call_args_list]
            assert any("Auto-correcting" in c for c in calls)
            handler.assert_called_once_with(update, context)

    @pytest.mark.asyncio
    async def test_suggest_medium_score(self, bot_manager):
        """Score 0.60-0.85: offer 'Did you mean?' inline button."""
        update = _make_update(text="/helo")
        context = _make_context()
        await bot_manager.handle_unknown_command(update, context)
        call_args = update.message.reply_text.call_args
        assert "Did you mean" in call_args[0][0]
        assert call_args[1].get("reply_markup") is not None

    @pytest.mark.asyncio
    async def test_reject_low_score(self, bot_manager):
        """Score < 0.60: show generic unknown message."""
        update = _make_update(text="/xyzabc")
        context = _make_context()
        await bot_manager.handle_unknown_command(update, context)
        msg = update.message.reply_text.call_args[0][0]
        assert "don't recognize" in msg.lower() or "unknown" in msg.lower() or "/help" in msg

    @pytest.mark.asyncio
    async def test_fuzzy_callback_dispatches(self, bot_manager):
        """Pressing 'Yes, run /help' button should dispatch to help handler."""
        update = _make_callback_update(data="fuzzy_cmd:help")
        context = _make_context()
        with patch.object(bot_manager, "_get_command_handler_map") as mock_map:
            handler = AsyncMock()
            mock_map.return_value = {"help": handler}
            await bot_manager.fuzzy_command_callback(update, context)
            handler.assert_called_once()


class TestPhase3KeywordShortcutInGeneralMessage:
    """Keyword match in handle_general_message should bypass LLM call."""

    @pytest.mark.asyncio
    async def test_keyword_skips_llm(self, bot_manager):
        update = _make_update(text="how is my partner")
        context = _make_context()

        with patch.object(bot_manager, "partner_status_command", new_callable=AsyncMock) as mock_cmd:
            await bot_manager.handle_general_message(update, context)
            mock_cmd.assert_called_once_with(update, context)


# =====================================================================
# Phase 4 — Deeper Per-Metric Tracking
# =====================================================================

class TestPhase4MetricStreaks:
    """Unit tests for calculate_metric_streaks."""

    def test_all_completed(self):
        from src.services.analytics_service import calculate_metric_streaks
        checkins = _make_checkins(7, sleep=True, training=True)
        streaks = calculate_metric_streaks(checkins)
        assert streaks["sleep"] == 7
        assert streaks["training"] == 7

    def test_streak_broken_midway(self):
        from src.services.analytics_service import calculate_metric_streaks
        base = datetime.utcnow()
        checkins = []
        for i in range(7):
            d = (base - timedelta(days=6 - i)).strftime("%Y-%m-%d")
            checkins.append(_make_checkin(d, sleep=(i >= 4)))
        streaks = calculate_metric_streaks(checkins)
        assert streaks["sleep"] == 3

    def test_streak_zero_when_last_missed(self):
        from src.services.analytics_service import calculate_metric_streaks
        base = datetime.utcnow()
        checkins = []
        for i in range(5):
            d = (base - timedelta(days=4 - i)).strftime("%Y-%m-%d")
            checkins.append(_make_checkin(d, training=(i != 4)))
        streaks = calculate_metric_streaks(checkins)
        assert streaks["training"] == 0

    def test_empty_checkins(self):
        from src.services.analytics_service import calculate_metric_streaks
        streaks = calculate_metric_streaks([])
        assert all(v == 0 for v in streaks.values())


class TestPhase4MetricTrends:
    """Unit tests for calculate_metric_trends."""

    def test_improving_trend(self):
        from src.services.analytics_service import calculate_metric_trends
        base = datetime.utcnow()
        checkins = []
        for i in range(14):
            d = (base - timedelta(days=13 - i)).strftime("%Y-%m-%d")
            checkins.append(_make_checkin(d, sleep=(i >= 7)))
        trends = calculate_metric_trends(checkins, days=7)
        assert trends["sleep"]["direction"] == "up"
        assert trends["sleep"]["current_pct"] == 100.0
        assert trends["sleep"]["previous_pct"] == pytest.approx(0.0, abs=0.1)

    def test_declining_trend(self):
        from src.services.analytics_service import calculate_metric_trends
        base = datetime.utcnow()
        checkins = []
        for i in range(14):
            d = (base - timedelta(days=13 - i)).strftime("%Y-%m-%d")
            checkins.append(_make_checkin(d, training=(i < 7)))
        trends = calculate_metric_trends(checkins, days=7)
        assert trends["training"]["direction"] == "down"

    def test_stable_trend(self):
        from src.services.analytics_service import calculate_metric_trends
        checkins = _make_checkins(14, zero_porn=True)
        trends = calculate_metric_trends(checkins, days=7)
        assert trends["zero_porn"]["direction"] == "stable"
        assert trends["zero_porn"]["change"] == pytest.approx(0.0)

    def test_insufficient_data_no_crash(self):
        from src.services.analytics_service import calculate_metric_trends
        checkins = _make_checkins(3)
        trends = calculate_metric_trends(checkins, days=7)
        assert "sleep" in trends


class TestPhase4FormatFunctions:
    """Unit tests for formatting functions."""

    def test_status_breakdown_format(self):
        from src.services.analytics_service import format_status_tier1_breakdown
        checkins = _make_checkins(7, sleep=True, training=True)
        result = format_status_tier1_breakdown(checkins)
        assert "Tier 1 Breakdown" in result
        assert "Sleep 7h+" in result
        assert "7/7" in result
        assert "100%" in result

    def test_status_breakdown_empty(self):
        from src.services.analytics_service import format_status_tier1_breakdown
        assert format_status_tier1_breakdown([]) == ""

    def test_dashboard_has_all_sections(self):
        from src.services.analytics_service import format_metric_dashboard
        c7 = _make_checkins(7)
        c30 = _make_checkins(30)
        dashboard = format_metric_dashboard(c7, c30)
        assert "Last 7 Days" in dashboard
        assert "Last 30 Days" in dashboard
        assert "Current Streaks" in dashboard

    def test_dashboard_empty_7d(self):
        from src.services.analytics_service import format_metric_dashboard
        c30 = _make_checkins(10)
        dashboard = format_metric_dashboard([], c30)
        assert "No check-ins" in dashboard

    def test_pct_bar_bounds(self):
        from src.services.analytics_service import _pct_bar
        assert "░" in _pct_bar(0)
        assert "█" in _pct_bar(100)
        bar_50 = _pct_bar(50)
        filled = bar_50.count("█")
        empty = bar_50.count("░")
        assert filled + empty == 5

    def test_direction_arrow(self):
        from src.services.analytics_service import _direction_arrow
        up = _direction_arrow("up")
        down = _direction_arrow("down")
        stable = _direction_arrow("stable")
        assert up != ""
        assert down != ""
        assert stable != ""
        assert up != down
        assert up != stable


class TestPhase4MetricsCommand:
    """/metrics command handler tests."""

    @pytest.mark.asyncio
    async def test_sends_dashboard(self, bot_manager):
        update = _make_update(text="/metrics")
        context = _make_context()
        user = _make_user()
        checkins = _make_checkins(7)

        bot_manager._mock_fs.get_user.return_value = user
        bot_manager._mock_fs.get_recent_checkins.return_value = checkins

        await bot_manager.metrics_command(update, context)
        update.message.reply_text.assert_called_once()
        msg = update.message.reply_text.call_args[0][0]
        assert "Metrics Dashboard" in msg or "metrics" in msg.lower()

    @pytest.mark.asyncio
    async def test_user_not_found(self, bot_manager):
        update = _make_update(text="/metrics")
        context = _make_context()

        bot_manager._mock_fs.get_user.return_value = None
        await bot_manager.metrics_command(update, context)
        update.message.reply_text.assert_called_once()


class TestPhase4StatusBreakdown:
    """Regression: /status should include Tier 1 breakdown."""

    @pytest.mark.asyncio
    async def test_status_includes_tier1(self, bot_manager):
        update = _make_update(text="/status")
        context = _make_context()
        user = _make_user()
        checkins = _make_checkins(5)

        bot_manager._mock_fs.get_user.return_value = user
        bot_manager._mock_fs.get_recent_checkins.return_value = checkins
        bot_manager._mock_fs.checkin_exists.return_value = True

        await bot_manager.status_command(update, context)
        msg = update.message.reply_text.call_args[0][0]
        assert "Tier 1 Breakdown" in msg
        assert "/metrics" in msg


# =====================================================================
# Phase 5 — Automated Reports Every 3 Days
# =====================================================================

class TestPhase5UserModel:
    """Unit tests for last_report_date on User schema."""

    def test_default_none(self):
        user = _make_user()
        assert user.last_report_date is None

    def test_set_value(self):
        user = _make_user(last_report_date="2026-02-18")
        assert user.last_report_date == "2026-02-18"

    def test_to_firestore_includes_field(self):
        user = _make_user(last_report_date="2026-02-18")
        data = user.to_firestore()
        assert "last_report_date" in data
        assert data["last_report_date"] == "2026-02-18"

    def test_to_firestore_none(self):
        user = _make_user()
        data = user.to_firestore()
        assert data["last_report_date"] is None


class TestPhase5ReportMessageDays:
    """Unit tests for _build_report_message with configurable days."""

    def test_weekly_label(self, sample_week_checkins, sample_user):
        from src.agents.reporting_agent import _build_report_message
        msg = _build_report_message(sample_week_checkins, sample_user, "Great!", days=7)
        assert "Weekly Report" in msg
        assert "/7 days" in msg

    def test_3day_label(self, sample_week_checkins, sample_user):
        from src.agents.reporting_agent import _build_report_message
        three = sample_week_checkins[:3]
        msg = _build_report_message(three, sample_user, "Nice!", days=3)
        assert "3-Day Report" in msg
        assert "/3 days" in msg

    def test_empty_checkins(self, sample_user):
        from src.agents.reporting_agent import _build_report_message
        msg = _build_report_message([], sample_user, "", days=3)
        assert "3-Day Report" in msg
        assert "last 3 days" in msg

    def test_default_days_is_7(self, sample_week_checkins, sample_user):
        """Regression: default produces 'Weekly Report'."""
        from src.agents.reporting_agent import _build_report_message
        msg = _build_report_message(sample_week_checkins, sample_user, "insights")
        assert "Weekly Report" in msg


class TestPhase5CooldownLogic:
    """Unit tests for send_weekly_reports_to_all cooldown behavior."""

    @pytest.mark.asyncio
    async def test_skips_recent_report(self):
        from src.agents.reporting_agent import send_weekly_reports_to_all
        today = datetime.utcnow().strftime("%Y-%m-%d")
        user = _make_user(last_report_date=today)

        with patch("src.agents.reporting_agent.firestore_service") as mock_fs:
            mock_fs.get_all_users.return_value = [user]
            mock_bot = AsyncMock()
            results = await send_weekly_reports_to_all(
                project_id="test", bot=mock_bot, days=3, min_gap_days=3
            )
            assert results["reports_cooldown"] == 1
            assert results["reports_sent"] == 0

    @pytest.mark.asyncio
    async def test_sends_after_gap(self):
        from src.agents.reporting_agent import send_weekly_reports_to_all
        old_date = (datetime.utcnow() - timedelta(days=5)).strftime("%Y-%m-%d")
        user = _make_user(last_report_date=old_date)

        with patch("src.agents.reporting_agent.firestore_service") as mock_fs:
            mock_fs.get_all_users.return_value = [user]
            mock_fs.get_user.return_value = user
            mock_fs.get_recent_checkins.return_value = _make_checkins(3)
            mock_fs.update_user.return_value = True

            mock_bot = AsyncMock()
            with patch("src.agents.reporting_agent.generate_weekly_graphs", return_value={}):
                with patch("src.agents.reporting_agent.generate_ai_insights",
                           new_callable=AsyncMock, return_value="good"):
                    results = await send_weekly_reports_to_all(
                        project_id="test", bot=mock_bot, days=3, min_gap_days=3
                    )
                    assert results["reports_sent"] == 1
                    assert results["reports_cooldown"] == 0

    @pytest.mark.asyncio
    async def test_no_cooldown_when_min_gap_zero(self):
        """min_gap_days=0 sends unconditionally (backward compat)."""
        from src.agents.reporting_agent import send_weekly_reports_to_all
        today = datetime.utcnow().strftime("%Y-%m-%d")
        user = _make_user(last_report_date=today)

        with patch("src.agents.reporting_agent.firestore_service") as mock_fs:
            mock_fs.get_all_users.return_value = [user]
            mock_fs.get_user.return_value = user
            mock_fs.get_recent_checkins.return_value = _make_checkins(7)
            mock_fs.update_user.return_value = True

            mock_bot = AsyncMock()
            with patch("src.agents.reporting_agent.generate_weekly_graphs", return_value={}):
                with patch("src.agents.reporting_agent.generate_ai_insights",
                           new_callable=AsyncMock, return_value="insight"):
                    results = await send_weekly_reports_to_all(
                        project_id="test", bot=mock_bot, days=7, min_gap_days=0
                    )
                    assert results["reports_sent"] == 1
                    assert results["reports_cooldown"] == 0

    @pytest.mark.asyncio
    async def test_malformed_date_sends_anyway(self):
        """A corrupt last_report_date should not block future reports."""
        from src.agents.reporting_agent import send_weekly_reports_to_all
        user = _make_user(last_report_date="not-a-date")

        with patch("src.agents.reporting_agent.firestore_service") as mock_fs:
            mock_fs.get_all_users.return_value = [user]
            mock_fs.get_user.return_value = user
            mock_fs.get_recent_checkins.return_value = _make_checkins(3)
            mock_fs.update_user.return_value = True

            mock_bot = AsyncMock()
            with patch("src.agents.reporting_agent.generate_weekly_graphs", return_value={}):
                with patch("src.agents.reporting_agent.generate_ai_insights",
                           new_callable=AsyncMock, return_value="ok"):
                    results = await send_weekly_reports_to_all(
                        project_id="test", bot=mock_bot, days=3, min_gap_days=3
                    )
                    assert results["reports_sent"] == 1


class TestPhase5PeriodicEndpoint:
    """Integration test for /trigger/periodic-report endpoint."""

    def test_periodic_endpoint_exists(self):
        from src.main import app
        routes = [r.path for r in app.routes]
        assert "/trigger/periodic-report" in routes

    def test_weekly_endpoint_still_exists(self):
        """Regression: weekly endpoint must still be present."""
        from src.main import app
        routes = [r.path for r in app.routes]
        assert "/trigger/weekly-report" in routes


# =====================================================================
# Integration Tests — Cross-Phase Interactions
# =====================================================================

class TestIntegrationFuzzyAndMetrics:
    """Phase 3+4: fuzzy matching should recognize /metrics command."""

    def test_metrics_in_registered_commands(self, bot_manager):
        assert "metrics" in bot_manager.REGISTERED_COMMANDS

    def test_metrics_in_handler_map(self, bot_manager):
        handler_map = bot_manager._get_command_handler_map()
        assert "metrics" in handler_map

    def test_fuzzy_metircs_matches(self, bot_manager):
        cmd, score = bot_manager._fuzzy_match_command("/metircs")
        assert cmd == "metrics"
        assert score >= 0.60

    def test_keyword_metrics(self, bot_manager):
        assert bot_manager._match_command_keywords("show my metrics") == "metrics"


class TestIntegrationReportIncludesTier1:
    """Phase 4+5: Report messages include Tier 1 breakdown section."""

    def test_3day_report_has_tier1(self, sample_user):
        from src.agents.reporting_agent import _build_report_message
        checkins = _make_checkins(3)
        msg = _build_report_message(checkins, sample_user, "insights", days=3)
        assert "Tier 1 Breakdown" in msg
        assert "Sleep 7h+" in msg

    def test_weekly_report_has_tier1(self, sample_week_checkins, sample_user):
        from src.agents.reporting_agent import _build_report_message
        msg = _build_report_message(sample_week_checkins, sample_user, "insights", days=7)
        assert "Tier 1 Breakdown" in msg


class TestIntegrationEndToEndKeywordToMetrics:
    """Phase 3+4: Natural language -> keyword match -> metrics command."""

    @pytest.mark.asyncio
    async def test_show_metrics_keyword_triggers_command(self, bot_manager):
        update = _make_update(text="show metrics")
        context = _make_context()
        user = _make_user()
        checkins = _make_checkins(7)

        bot_manager._mock_fs.get_user.return_value = user
        bot_manager._mock_fs.get_recent_checkins.return_value = checkins

        with patch.object(bot_manager, "metrics_command", new_callable=AsyncMock) as mock_cmd:
            await bot_manager.handle_general_message(update, context)
            mock_cmd.assert_called_once_with(update, context)


# =====================================================================
# Regression Tests
# =====================================================================

class TestRegressionExistingFeatures:
    """Ensure existing features aren't broken by our production improvements."""

    def test_user_model_backward_compat(self):
        """Old user data without new fields should still parse."""
        data = {
            "user_id": "999", "telegram_id": 999,
            "name": "OldUser", "timezone": "Asia/Kolkata",
            "constitution_mode": "maintenance",
        }
        user = User(**data)
        assert user.last_report_date is None
        assert user.user_id == "999"

    def test_weekly_report_default_7_days(self):
        import inspect
        from src.agents.reporting_agent import generate_and_send_weekly_report
        sig = inspect.signature(generate_and_send_weekly_report)
        assert sig.parameters["days"].default == 7

    def test_send_reports_default_no_cooldown(self):
        import inspect
        from src.agents.reporting_agent import send_weekly_reports_to_all
        sig = inspect.signature(send_weekly_reports_to_all)
        assert sig.parameters["min_gap_days"].default == 0

    def test_build_report_default_weekly(self):
        import inspect
        from src.agents.reporting_agent import _build_report_message
        sig = inspect.signature(_build_report_message)
        assert sig.parameters["days"].default == 7

    def test_registered_commands_includes_all_originals(self, bot_manager):
        originals = [
            "start", "help", "status", "mode", "checkin",
            "partner_status", "achievements", "report",
            "weekly", "monthly", "yearly", "export",
        ]
        for cmd in originals:
            assert cmd in bot_manager.REGISTERED_COMMANDS, f"Missing: {cmd}"

    def test_compliance_calculation_unchanged(self):
        from src.utils.compliance import calculate_compliance_score
        tier1 = Tier1NonNegotiables(
            sleep=True, sleep_hours=7.5,
            training=True, deep_work=True,
            zero_porn=True, boundaries=True,
        )
        score = calculate_compliance_score(tier1)
        assert score >= 80.0

    def test_streak_logic_unchanged(self):
        from src.utils.streak import should_increment_streak
        assert should_increment_streak("2026-02-19", "2026-02-20") is True
        assert should_increment_streak("2026-02-17", "2026-02-20") is False

    def test_fuzzy_does_not_interfere_with_known_commands(self, bot_manager):
        """An exact registered command should score 1.0, never fuzzy-match to something else."""
        for cmd in ["status", "help", "checkin", "report", "weekly", "metrics"]:
            matched_cmd, score = bot_manager._fuzzy_match_command(f"/{cmd}")
            assert matched_cmd == cmd
            assert score == 1.0

    def test_user_model_serialization_roundtrip(self):
        """User -> to_firestore -> User should preserve all fields."""
        user = _make_user(last_report_date="2026-02-18")
        data = user.to_firestore()
        restored = User(**data)
        assert restored.user_id == user.user_id
        assert restored.last_report_date == "2026-02-18"
        assert restored.streaks.current_streak == user.streaks.current_streak
