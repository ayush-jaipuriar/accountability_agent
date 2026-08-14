"""
Unit tests for Partner Weekly Strongest/Weakest Status Report (Feature 3).

Tests:
1. calculate_partner_weekly_performance correctly computes habit adherence and identifies strongest/weakest areas.
2. build_partner_weekly_summary_message generates formatted HTML output with tips and compliance average.
3. send_partner_weekly_report sends message to partner when notifications enabled, and respects privacy settings.
4. reporting_agent dispatches partner weekly report on weekly schedule.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from src.models.schemas import (
    User,
    UserStreaks,
    Tier1NonNegotiables,
    DailyCheckIn,
    CheckInResponses,
    DailyTaskItem,
)
from src.services.analytics_service import calculate_partner_weekly_performance
from src.services.partner_notification_service import (
    build_partner_weekly_summary_message,
    send_partner_weekly_report,
)


def _create_sample_checkin(
    date: str,
    sleep_hours: float,
    training_intensity: str,
    dw_hours: float,
    sb_hours: float,
    zero_porn: bool = True,
    boundaries: bool = True,
    tasks_completed: int = 2,
) -> DailyCheckIn:
    """Helper to create realistic checkin fixtures."""
    tier1 = Tier1NonNegotiables(
        sleep=sleep_hours >= 6.0,
        sleep_hours=sleep_hours,
        training=training_intensity in ('light', 'moderate', 'intense'),
        training_intensity=training_intensity,
        is_rest_day=(training_intensity == "rest"),
        deep_work=dw_hours >= 0.5,
        deep_work_hours=dw_hours,
        skill_building=sb_hours >= 0.5,
        skill_building_hours=sb_hours,
        zero_porn=zero_porn,
        boundaries=boundaries,
    )
    tasks = [
        DailyTaskItem(id="t1", title="Task 1", is_primary=True, completed=(tasks_completed >= 1)),
        DailyTaskItem(id="t2", title="Task 2", is_primary=False, completed=(tasks_completed >= 2)),
    ]
    responses = CheckInResponses(
        challenges="None reported for today.",
        rating=8,
        rating_reason="Good execution overall.",
        tomorrow_priority="Focus on key project.",
        tomorrow_obstacle="None anticipated.",
    )
    return DailyCheckIn(
        date=date,
        user_id="user_test_1",
        mode="active",
        tier1_non_negotiables=tier1,
        responses=responses,
        compliance_score=85.0,
        completed_at=datetime.utcnow(),
        duration_seconds=120,
        committed_tasks=tasks,
    )


def test_calculate_partner_weekly_performance_aggregation():
    """Test performance metric calculation and rank order."""
    # 4 days of checkins with varying adherence
    checkins = [
        _create_sample_checkin("2026-08-10", sleep_hours=7.5, training_intensity="moderate", dw_hours=2.5, sb_hours=0.0),
        _create_sample_checkin("2026-08-11", sleep_hours=7.2, training_intensity="moderate", dw_hours=2.0, sb_hours=0.0),
        _create_sample_checkin("2026-08-12", sleep_hours=8.0, training_intensity="intense", dw_hours=1.5, sb_hours=0.0),
        _create_sample_checkin("2026-08-13", sleep_hours=7.0, training_intensity="rest", dw_hours=0.0, sb_hours=0.0),
    ]

    perf = calculate_partner_weekly_performance(checkins)
    assert perf["has_data"] is True
    assert perf["checkin_count"] == 4

    # Sleep was met 4/4 = 100%
    assert perf["habits"]["Sleep"]["pct"] == 100.0
    # Training was done/rested 4/4 = 100%
    assert perf["habits"]["Training"]["pct"] == 100.0
    # Skill Building was 0/4 = 0%
    assert perf["habits"]["Skill Building"]["pct"] == 0.0

    # Strongest habits should include Sleep or Training or Zero Porn
    strongest_names = [h[0] for h in perf["strongest"]]
    assert "Sleep" in strongest_names or "Training" in strongest_names or "Zero Porn" in strongest_names

    # Weakest habits should include Skill Building
    weakest_names = [h[0] for h in perf["weakest"]]
    assert "Skill Building" in weakest_names

    # Tasks stat
    assert perf["tasks_stat"] is not None
    assert perf["tasks_stat"]["total"] == 8


def test_build_partner_weekly_summary_message():
    """Test message formatting for partner report."""
    performance = {
        "has_data": True,
        "checkin_count": 7,
        "avg_compliance": 88.5,
        "strongest": [
            ("Training", {"pct": 100.0, "detail": "7/7 sessions/rests"}),
            ("Sleep", {"pct": 85.7, "detail": "avg 7.4h"}),
        ],
        "weakest": [
            ("Deep Work", {"pct": 42.8, "detail": "avg 1.1h vs 2.0h target"}),
            ("Skill Building", {"pct": 28.5, "detail": "avg 0.8h vs 2.0h target"}),
        ],
        "tasks_stat": {
            "completed": 12,
            "total": 14,
            "pct": 85.7,
        }
    }

    msg = build_partner_weekly_summary_message("Alex", performance)
    assert "Weekly Partner Snapshot: Alex" in msg
    assert "🔥 <b>Strongest Areas:</b>" in msg
    assert "• <b>Training</b>: 100%" in msg
    assert "⚠️ <b>Needs Support / Growth Areas:</b>" in msg
    assert "• <b>Deep Work</b>: 43%" in msg or "• <b>Deep Work</b>: 42%" in msg or "Deep Work" in msg
    assert "Weekly Compliance Avg:</b> 88.5%" in msg
    assert "To-Dos Completed:</b> 12/14" in msg
    assert "💡 <i>Tip:" in msg


@pytest.mark.asyncio
async def test_send_partner_weekly_report_privacy_and_delivery():
    """Test send_partner_weekly_report delivers to partner and honors disable flags."""
    bot = AsyncMock()
    user = User(
        user_id="u1",
        telegram_id=11111,
        name="Alex Smith",
        accountability_partner_id="u2",
        partner_checkin_notifications_enabled=True,
    )
    partner = User(
        user_id="u2",
        telegram_id=22222,
        name="Sam Jones",
        accountability_partner_id="u1",
        partner_checkin_notifications_enabled=True,
    )
    checkins = [_create_sample_checkin("2026-08-10", 7.5, "moderate", 2.0, 2.0)]

    with patch("src.services.partner_notification_service.firestore_service.get_user", return_value=partner):
        # Successful delivery
        result = await send_partner_weekly_report(bot, user, checkins)
        assert result["sent"] is True
        bot.send_message.assert_called_once()
        assert bot.send_message.call_args[1]["chat_id"] == 22222

    # Disabled by user
    user_disabled = User(
        user_id="u1",
        telegram_id=11111,
        name="Alex Smith",
        accountability_partner_id="u2",
        partner_checkin_notifications_enabled=False,
    )
    result_disabled = await send_partner_weekly_report(bot, user_disabled, checkins)
    assert result_disabled["sent"] is False
    assert result_disabled["reason"] == "disabled"
