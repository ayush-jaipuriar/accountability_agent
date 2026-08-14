"""
Partner check-in notification helpers.

Keeps formatting and delivery rules in one place so full check-ins,
quick check-ins, and corrections behave the same way.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from src.models.schemas import Tier1NonNegotiables, User
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


def get_preferred_first_name(user: Optional[User], fallback_name: Optional[str] = None) -> str:
    """Use saved profile name first, then fall back to runtime display name."""
    if user and getattr(user, "name", None):
        return user.name
    if fallback_name:
        return fallback_name
    if user and getattr(user, "telegram_username", None):
        return user.telegram_username.lstrip("@")
    return "Your partner"


def _build_metric_summary(tier1: Tier1NonNegotiables) -> str:
    metrics = [
        ("Sleep", "met" if tier1.sleep else "missed"),
        ("Training", "done" if tier1.training else "missed"),
        ("Deep work", "done" if tier1.deep_work else "missed"),
        ("Skill building", "done" if tier1.skill_building else "missed"),
    ]
    return "\n".join(f"• {label}: {status}" for label, status in metrics)


def build_partner_checkin_message(
    sender_name: str,
    tier1: Tier1NonNegotiables,
    is_update: bool = False
) -> str:
    """Format a privacy-safe partner notification message."""
    header = (
        f"🤝 <b>{sender_name} updated today's check-in.</b>"
        if is_update
        else f"🤝 <b>{sender_name} checked in for today.</b>"
    )

    completed_count = sum([
        tier1.sleep,
        tier1.training,
        tier1.deep_work,
        tier1.skill_building,
    ])

    if completed_count == 4:
        encouragement = "Strong day. Keep backing each other and building consistency."
    elif completed_count >= 2:
        encouragement = "Solid progress. A little encouragement from you will go a long way."
    else:
        encouragement = "Today may have been tough. A supportive nudge from you could really help."

    return (
        f"{header}\n\n"
        f"<b>Today's snapshot:</b>\n"
        f"{_build_metric_summary(tier1)}\n\n"
        f"{encouragement}"
    )


async def send_partner_checkin_notification(
    bot: Any,
    sender: User,
    tier1: Tier1NonNegotiables,
    date: str,
    fallback_sender_name: Optional[str] = None,
    is_update: bool = False,
) -> Dict[str, Any]:
    """
    Send the partner notification if the pair is eligible.

    Returns a small status dict so callers can decide whether they need to
    inform the sender about a delivery failure.
    """
    result: Dict[str, Any] = {
        "sent": False,
        "reason": None,
        "partner": None,
        "event_type": None,
    }

    if not sender.accountability_partner_id:
        result["reason"] = "no_partner"
        return result

    if not getattr(sender, "partner_checkin_notifications_enabled", True):
        result["reason"] = "disabled"
        return result

    partner = firestore_service.get_user(sender.accountability_partner_id)
    result["partner"] = partner

    if not partner:
        result["reason"] = "partner_missing"
        return result

    if not getattr(partner, "partner_checkin_notifications_enabled", True):
        result["reason"] = "disabled"
        return result

    status = firestore_service.get_partner_checkin_notification_status(sender.user_id, date) or {}

    if is_update and status.get("updated_sent"):
        result["reason"] = "already_updated"
        return result

    if not is_update and status.get("initial_sent"):
        result["reason"] = "already_sent"
        return result

    event_type = "updated" if is_update and status.get("initial_sent") else "initial"
    sender_name = get_preferred_first_name(sender, fallback_sender_name)
    message = build_partner_checkin_message(
        sender_name=sender_name,
        tier1=tier1,
        is_update=(event_type == "updated"),
    )

    try:
        await bot.send_message(
            chat_id=partner.telegram_id,
            text=message,
            parse_mode="HTML",
        )
        firestore_service.mark_partner_checkin_notification_sent(
            user_id=sender.user_id,
            date=date,
            partner_id=partner.user_id,
            event_type=event_type,
        )
        result["sent"] = True
        result["event_type"] = event_type
        return result
    except Exception as e:
        logger.error(
            f"❌ Failed to send partner check-in notification for {sender.user_id}: {e}"
        )
        result["reason"] = "delivery_failed"
        result["error"] = str(e)
        return result


def build_partner_weekly_summary_message(
    partner_name: str,
    performance: Dict[str, Any]
) -> str:
    """
    Format weekly partner status report highlighting strongest and weakest habit areas.
    """
    if not performance.get("has_data"):
        return f"🤝 <b>Weekly Partner Snapshot: {partner_name}</b>\n\nNo check-in records logged this week."

    lines = [
        f"🤝 <b>Weekly Partner Snapshot: {partner_name}</b>",
        f"<i>Summary of your partner's execution over the last 7 days:</i>\n",
    ]

    # Strongest Areas
    lines.append("🔥 <b>Strongest Areas:</b>")
    strongest = performance.get("strongest", [])
    if strongest:
        for name, data in strongest:
            lines.append(f"• <b>{name}</b>: {data['pct']:.0f}% ({data['detail']})")
    else:
        lines.append("• Building baseline consistency")

    lines.append("")

    # Weakest / Needs Support
    lines.append("⚠️ <b>Needs Support / Growth Areas:</b>")
    weakest = performance.get("weakest", [])
    if weakest:
        for name, data in weakest:
            lines.append(f"• <b>{name}</b>: {data['pct']:.0f}% ({data['detail']})")
    else:
        lines.append("• None — all areas meeting targets!")

    lines.append("")
    lines.append(f"📊 <b>Weekly Compliance Avg:</b> {performance['avg_compliance']:.1f}%")

    # Tasks / To-Dos
    tasks_stat = performance.get("tasks_stat")
    if tasks_stat:
        lines.append(
            f"🎯 <b>To-Dos Completed:</b> {tasks_stat['completed']}/{tasks_stat['total']} "
            f"({tasks_stat['pct']:.0f}%)"
        )

    # Dynamic Coaching Tip
    weakest_names = [name for name, _ in weakest]
    focus_topic = weakest_names[0] if weakest_names else "consistency"
    lines.append(
        f"\n💡 <i>Tip: Send {partner_name} an encouraging text about their "
        f"{focus_topic.lower()} goals this week!</i>"
    )

    return "\n".join(lines)


async def send_partner_weekly_report(
    bot: Any,
    user: User,
    checkins: list,
) -> Dict[str, Any]:
    """
    Send weekly status report of user's performance to their accountability partner.
    """
    from src.services.analytics_service import calculate_partner_weekly_performance

    result: Dict[str, Any] = {
        "sent": False,
        "reason": None,
        "partner": None,
    }

    if not user.accountability_partner_id:
        result["reason"] = "no_partner"
        return result

    if not getattr(user, "partner_checkin_notifications_enabled", True):
        result["reason"] = "disabled"
        return result

    partner = firestore_service.get_user(user.accountability_partner_id)
    result["partner"] = partner

    if not partner:
        result["reason"] = "partner_missing"
        return result

    if not getattr(partner, "partner_checkin_notifications_enabled", True):
        result["reason"] = "disabled"
        return result

    perf = calculate_partner_weekly_performance(checkins)
    user_name = get_preferred_first_name(user)
    message = build_partner_weekly_summary_message(user_name, perf)

    try:
        await bot.send_message(
            chat_id=partner.telegram_id,
            text=message,
            parse_mode="HTML",
        )
        result["sent"] = True
        logger.info(f"✅ Sent weekly partner status report for {user.user_id} to partner {partner.user_id}")
        return result
    except Exception as e:
        logger.error(
            f"❌ Failed to send weekly partner status report for {user.user_id}: {e}"
        )
        result["reason"] = "delivery_failed"
        result["error"] = str(e)
        return result

