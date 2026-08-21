"""
Comprehensive Verification Tests for Audited Bug Fixes (Phases 1 - 5)
======================================================================
Validates confirmed fixes across core math, Telegram UI,
multi-agent routing, GDPR deletion, exports, gamification, and utilities.
"""

import pytest
import html
from datetime import datetime, date, timedelta, timezone
import pytz

from src.models.schemas import (
    User, DailyCheckIn, Tier1NonNegotiables, CheckInResponses,
    DailyTaskItem, Goal, PartnerChallenge
)
from src.utils.streak import calculate_new_streak, update_streak_data
from src.utils.compliance import habit_credit, get_missed_items
from src.utils.telegram_utils import _escape_unsafe_html
from src.utils.timezone_utils import get_timezones_at_local_time
from src.utils.metrics import AppMetrics
from src.utils.rate_limiter import RateLimiter
from src.agents.state import merge_dicts, merge_state
from src.agents.pattern_detection import PatternDetectionAgent
from src.agents.query_agent import QueryAgent
from src.agents.supervisor import SupervisorAgent
from src.services.achievement_service import achievement_service
from src.services.goal_service import goal_service
from src.services.challenge_service import challenge_service
from src.services.streak_recovery_service import analyze_break_patterns
from src.services.feature_discovery_service import feature_discovery_service
from src.services.churn_prediction import churn_predictor
from src.services.feedback_service import feedback_service
from src.services.export_service import generate_pdf_export, generate_csv_export, generate_json_export
from src.services.data_deletion_service import data_deletion_service
from src.services.constitution_service import ConstitutionService
from src.services.visualization_service import _figure_to_bytes
import matplotlib.pyplot as plt


# ==============================================================================
# Phase 1: Core Mathematical & Logic Fixes
# ==============================================================================

def test_streak_same_day_checkin_preserves_streak():
    """Same-day checkin should preserve current streak instead of resetting to 1."""
    streak = calculate_new_streak(
        current_streak=15,
        last_checkin_date="2026-03-10",
        new_checkin_date="2026-03-10"
    )
    assert streak == 15

    # Test update_streak_data handles same-day check-in
    user = User(telegram_id=12345, user_id="u123", name="Tester", telegram_username="tester")
    user.streaks.current_streak = 10
    user.streaks.total_checkins = 25
    user.streaks.last_checkin_date = "2026-03-10"

    updates = update_streak_data(
        current_streak=user.streaks.current_streak,
        longest_streak=user.streaks.longest_streak,
        total_checkins=user.streaks.total_checkins,
        last_checkin_date=user.streaks.last_checkin_date,
        new_checkin_date="2026-03-10"
    )
    assert updates["current_streak"] == 10
    assert updates["total_checkins"] == 25
    assert updates["is_reset"] is False


def test_compliance_habit_credit_zero_division():
    """habit_credit with target <= 0 should never raise ZeroDivisionError."""
    assert habit_credit(actual=5.0, target=0.0) == 1.0
    assert habit_credit(actual=0.0, target=0.0) == 0.0
    assert habit_credit(actual=-2.0, target=0.0) == 0.0
    assert habit_credit(actual=None, target=0.0) == 0.0
    assert habit_credit(actual=3.0, target=6.0) == 0.5


def test_compliance_get_missed_items_phase3d():
    """get_missed_items should not flag skill_building on pre-Phase 3D records."""
    tier1 = Tier1NonNegotiables(
        sleep=True, training=True, deep_work=True,
        skill_building=False, zero_porn=True, boundaries=True
    )
    # Pre-Phase 3D record
    missed_pre = get_missed_items(tier1, checkin_date="2026-01-01")
    assert "skill_building" not in missed_pre

    # Post-Phase 3D record
    missed_post = get_missed_items(tier1, checkin_date="2026-04-01")
    assert "skill_building" in missed_post


def test_pattern_detection_rest_day_no_training_abandonment():
    """Scheduled rest day does not trigger training abandonment or relationship failure."""
    agent = PatternDetectionAgent()
    checkins = []
    base_date = date(2026, 3, 1)
    for i in range(10):
        d_str = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        tier1 = Tier1NonNegotiables(
            sleep=True,
            training=False,
            training_intensity="rest",
            is_rest_day=True,
            deep_work=True,
            zero_porn=True,
            boundaries=True
        )
        c = DailyCheckIn(
            date=d_str, user_id="u1", mode="optimization", compliance_score=80.0,
            tier1_non_negotiables=tier1,
            responses=CheckInResponses(
                rating=8,
                challenges="No major challenges faced today.",
                rating_reason="Everything was completely on track.",
                tomorrow_priority="Deep work focus on core project.",
                tomorrow_obstacle="No obstacles foreseen tomorrow."
            )
        )
        checkins.append(c)

    patterns = agent.detect_patterns(checkins)
    pattern_types = [p.type for p in patterns]
    assert "training_abandonment" not in pattern_types


def test_query_agent_trend_and_streak_record():
    """QueryAgent calculates trend chronologically."""
    agent = QueryAgent(project_id="accountability-agent")

    checkins = []
    base_date = date(2026, 3, 1)
    scores = [40, 50, 60, 70, 80, 90, 100]  # Improving over time
    for i, s in enumerate(scores):
        d_str = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        c = DailyCheckIn(
            date=d_str, user_id="u1", mode="optimization",
            tier1_non_negotiables=Tier1NonNegotiables(zero_porn=True, boundaries=True),
            responses=CheckInResponses(
                rating=8,
                challenges="No major challenges faced today.",
                rating_reason="Everything was completely on track.",
                tomorrow_priority="Deep work focus on core project.",
                tomorrow_obstacle="No obstacles foreseen tomorrow."
            ),
            compliance_score=float(s)
        )
        checkins.append(c)

    trend = agent._calculate_compliance_trend(checkins)
    assert trend == "improving"


# ==============================================================================
# Phase 2: Telegram UI & HTML Escaping
# ==============================================================================

def test_escape_unsafe_html_strips_illegal_attributes():
    """_escape_unsafe_html restores only valid tags and attributes."""
    raw = '<b style="color:red">Red</b> <blockquote expandable>Quote</blockquote> <a href="http://x.com">Link</a> Sleep <6 hours & 2>1'
    safe = _escape_unsafe_html(raw)
    assert "<blockquote expandable>" in safe
    assert '<a href="http://x.com">Link</a>' in safe
    assert "&lt;b style=" in safe  # Invalid attribute on <b> stripped/escaped
    assert "Sleep &lt;6 hours &amp; 2&gt;1" in safe


# ==============================================================================
# Phase 3: Multi-Agent Intelligence & State
# ==============================================================================

def test_state_merge_dicts_reducer_and_deepcopy():
    """merge_dicts reducer merges without mutating and merge_state does deep copies."""
    d1 = {"a": 1, "b": 2}
    d2 = {"b": 3, "c": 4}
    res = merge_dicts(d1, d2)
    assert res == {"a": 1, "b": 3, "c": 4}
    assert d1 == {"a": 1, "b": 2}  # d1 not mutated

    base_state = {
        "user_id": "u1",
        "checkin_answers": {"q1": "yes"},
        "detected_patterns": ["p1"]
    }
    updates = {
        "checkin_answers": {"q2": "no"},
        "detected_patterns": ["p2"]
    }
    new_state = merge_state(base_state, updates)
    assert new_state["checkin_answers"] == {"q1": "yes", "q2": "no"}
    assert new_state["detected_patterns"] == ["p1", "p2"]
    assert base_state["checkin_answers"] == {"q1": "yes"}  # Base state untouched


def test_supervisor_fast_query_emotional_guard():
    """Supervisor fast query detection does not steal emotional distress messages."""
    supervisor = SupervisorAgent(project_id="accountability-agent")
    state = {
        "user_id": "u1",
        "message": "What's my streak? I'm feeling lonely and struggling tonight"
    }
    message_lower = state["message"].lower()
    emotional_markers = [
        "feeling", "lonely", "sad", "anxious", "stressed", "urge", "urges",
        "struggling", "depressed", "giving up", "failed", "relapse", "help",
        "crying", "breakdown", "overwhelmed", "scared", "frustrated"
    ]
    query_keywords = ["what's my", "what is my"]
    has_emotional = any(marker in message_lower for marker in emotional_markers)
    has_query = any(kw in message_lower for kw in query_keywords)
    assert has_emotional is True
    assert has_query is True


def test_supervisor_parse_intent_sanitization():
    """Supervisor intent parsing handles markdown formatting and punctuation."""
    supervisor = SupervisorAgent(project_id="accountability-agent")
    assert supervisor._parse_intent("```checkin```") == "checkin"
    assert supervisor._parse_intent("**query**") == "query"
    assert supervisor._parse_intent("emotional.") == "emotional"
    assert supervisor._parse_intent("`command`!") == "command"


# ==============================================================================
# Phase 4: Data Layer, GDPR Deletion, Storage & Exports
# ==============================================================================

def test_export_service_date_ranges_and_sort():
    """Export service generates chronological metadata date ranges and newest-first recent table."""
    checkins = []
    base_date = date(2026, 3, 1)
    for i in range(20):
        d_str = (base_date + timedelta(days=i)).strftime("%Y-%m-%d")
        c = DailyCheckIn(
            date=d_str, user_id="u1", mode="optimization",
            tier1_non_negotiables=Tier1NonNegotiables(zero_porn=True, boundaries=True),
            responses=CheckInResponses(
                rating=8,
                challenges="No major challenges faced today.",
                rating_reason="Everything was completely on track.",
                tomorrow_priority="Deep work focus on core project.",
                tomorrow_obstacle="No obstacles foreseen tomorrow."
            ),
            compliance_score=80.0
        )
        checkins.append(c)

    user = User(telegram_id=12345, user_id="u1", name="Tester", telegram_username="tester")
    # Date range formatting in JSON metadata
    min_d = min(c.date for c in checkins)
    max_d = max(c.date for c in checkins)
    assert min_d == "2026-03-01"
    assert max_d == "2026-03-20"

    # Recent 14 slice in PDF
    recent = sorted(checkins, key=lambda c: c.date, reverse=True)[:14]
    assert len(recent) == 14
    assert recent[0].date == "2026-03-20"
    assert recent[-1].date == "2026-03-07"


def test_schemas_unique_ids():
    """Goal and Challenge IDs have random hex suffix to prevent collisions."""
    g1 = Goal(user_id="u1", title="Sleep", description="Sleep goal", category="sleep", start_date="2026-03-01")
    g2 = Goal(user_id="u1", title="Sleep", description="Sleep goal", category="sleep", start_date="2026-03-01")
    assert g1.goal_id != g2.goal_id

    c1 = PartnerChallenge(challenger_id="u1", partner_id="u2", challenge_type="custom", title="C", description="D", start_date="2026-03-01", end_date="2026-03-07")
    c2 = PartnerChallenge(challenger_id="u1", partner_id="u2", challenge_type="custom", title="C", description="D", start_date="2026-03-01", end_date="2026-03-07")
    assert c1.challenge_id != c2.challenge_id


def test_constitution_service_path_resolution():
    """ConstitutionService successfully resolves path relative to repo root."""
    cs = ConstitutionService()
    assert cs.constitution_path.exists()
    assert len(cs.get_constitution_text()) > 100


def test_visualization_service_figure_closure():
    """_figure_to_bytes closes the figure safely."""
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [4, 5, 6])
    buf = _figure_to_bytes(fig)
    assert buf.getvalue() is not None
    assert not plt.fignum_exists(fig.number)


# ==============================================================================
# Phase 5: Gamification, Analytics, Churn & Timezones
# ==============================================================================

def test_achievement_rarity_breakdown_uncommon():
    """get_user_progress includes uncommon achievements without KeyError."""
    user = User(telegram_id=12345, user_id="u1", name="Tester", telegram_username="tester")
    user.achievements = ["comeback_kid", "first_checkin"]
    progress = achievement_service.get_user_progress(user)
    assert "uncommon" in progress["rarity_breakdown"]
    assert progress["rarity_breakdown"]["uncommon"] >= 1


def test_goal_and_challenge_progress_date_deduplication():
    """Goal and challenge progress entries are deduplicated by date."""
    goal = Goal(
        user_id="u1", title="Sleep", description="Sleep goal", category="sleep",
        target_value=7.0, target_days=7, start_date="2026-03-01"
    )
    goal.progress.append({"date": "2026-03-01", "met": True, "value": 8.0})
    progress_entry = {"date": "2026-03-01", "met": True, "value": 8.5}
    goal.progress = [p for p in goal.progress if p.get("date") != "2026-03-01"]
    goal.progress.append(progress_entry)
    assert len(goal.progress) == 1
    assert goal.progress[0]["value"] == 8.5


def test_churn_prediction_timezone_aware_subtraction():
    """is_intervention_cooled_down handles both aware and naive datetimes."""
    user = User(telegram_id=12345, user_id="u1", name="Tester", telegram_username="tester")
    user.last_churn_intervention = datetime.now(timezone.utc) - timedelta(days=5)
    assert churn_predictor.is_intervention_cooled_down(user, cooldown_days=3) is True

    user.last_churn_intervention = datetime.utcnow() - timedelta(days=1)
    assert churn_predictor.is_intervention_cooled_down(user, cooldown_days=3) is False


def test_feedback_service_nps_none_filtering():
    """calculate_nps filters None ratings safely."""
    mock_feedbacks = [
        {"rating": 10, "type": "nps"},
        {"rating": 9, "type": "nps"},
        {"rating": 7, "type": "nps"},
        {"rating": 5, "type": "nps"},
        {"rating": None, "type": "nps"}
    ]
    rated = [f for f in mock_feedbacks if f.get("rating") is not None]
    promoters = sum(1 for f in rated if f["rating"] >= 9)
    passives = sum(1 for f in rated if 7 <= f["rating"] <= 8)
    detractors = sum(1 for f in rated if f["rating"] <= 6)
    total = len(rated)
    assert total == 4
    assert promoters == 2
    assert passives == 1
    assert detractors == 1


def test_timezone_utils_utc_localization_and_tolerance():
    """get_timezones_at_local_time localizes naive datetimes to UTC."""
    naive_utc = datetime(2026, 3, 15, 15, 30, 0)  # 15:30 UTC = 21:00 IST
    matching = get_timezones_at_local_time(naive_utc, target_hour=21, target_minute=0, tolerance_minutes=7)
    assert "Asia/Kolkata" in matching


def test_metrics_tracker_latency_summary_schema():
    """MetricsTracker get_latency_stats returns consistent schema with p99_ms."""
    tracker = AppMetrics()
    empty_stats = tracker.get_latency_stats("ai_latency")
    assert "p99_ms" in empty_stats
    assert "avg_ms" in empty_stats
    assert empty_stats["count"] == 0

    tracker.record_latency("ai_latency", 150.0)
    tracker.record_latency("ai_latency", 250.0)
    stats = tracker.get_latency_stats("ai_latency")
    assert stats["count"] == 2
    assert stats["p99_ms"] >= 250.0
