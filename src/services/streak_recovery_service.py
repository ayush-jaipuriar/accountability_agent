"""
Streak Recovery Service
=======================

Compassionate streak break handling with ritual, reason capture,
and partner notification.

Theory: Compassionate Reset
-----------------------------
When a streak breaks, users experience the "what-the-hell" effect —
a cognitive distortion where a single failure feels like total failure.
The recovery ritual combats this by acknowledging the loss, offering
forgiveness, and providing a clear restart path.
"""

import logging
import random
from datetime import datetime
from typing import Optional, Dict, Any, List

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from src.models.schemas import User
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


# Break reason options with emojis
BREAK_REASONS = {
    "sleep": "😴 Poor Sleep",
    "training": "🏋️ Missed Training",
    "work": "💼 Work/Study Overload",
    "motivation": "😔 Low Motivation",
    "travel": "✈️ Travel/Schedule Change",
    "social": "🎉 Social Event",
    "health": "🤒 Health Issue",
    "other": "🤷 Other",
}


# Compassionate recovery quotes
RECOVERY_QUOTES = [
    "A streak reset isn't starting over — it's starting from experience.",
    "The #1 predictor of long-term success? Restarting after a break.",
    "Consistency isn't perfection — it's always getting back on track.",
    "Your brain forms stronger habits after recovering from a break.",
    "Every marathon runner walks sometimes. What matters is finishing.",
    "Elite athletes track 'return-to-form' time, not zero-failure streaks.",
]


def format_recovery_ritual(
    previous_streak: int,
    break_reason: Optional[str] = None,
) -> str:
    """
    Format the streak recovery ritual message.

    Three-part structure: Acknowledge → Forgive → Restart
    """
    quote = random.choice(RECOVERY_QUOTES)

    lines = [
        f"💔 <b>Streak Broken: {previous_streak} → 0</b>",
        f"",
        f"<b>1. Acknowledge</b>",
        f"Your {previous_streak}-day streak was real. You earned every day of it.",
        f"",
        f"<b>2. Forgive</b>",
        f"Your past self did their best. Your future self is counting on you.",
        f"",
        f"<b>3. Restart</b>",
        f"Your comeback begins NOW.",
        f"",
        f"💡 <i>{quote}</i>",
    ]

    if break_reason:
        lines.append(f"")
        lines.append(f"📊 You noted: <b>{BREAK_REASONS.get(break_reason, break_reason)}</b>")
        lines.append(f"We'll use this to identify your patterns.")

    lines.extend([
        f"",
        f"🎯 <b>Next milestone:</b> 7 days → Comeback King 🦁",
        f"",
        f"Ready? /checkin",
    ])

    return "\n".join(lines)


def create_break_reason_keyboard() -> InlineKeyboardMarkup:
    """Create inline keyboard for break reason selection."""
    buttons = [
        [InlineKeyboardButton(label, callback_data=f"break_{key}")]
        for key, label in BREAK_REASONS.items()
    ]
    return InlineKeyboardMarkup(buttons)


async def send_recovery_ritual(
    bot,
    user: User,
    previous_streak: int,
) -> None:
    """
    Send the full recovery ritual to a user whose streak just broke.

    1. Send compassionate message
    2. Ask for break reason via inline buttons
    3. Notify partner (if linked)
    """
    # Step 1: Send compassionate message
    await bot.send_message(
        chat_id=user.telegram_id,
        text=format_recovery_ritual(previous_streak),
        parse_mode='HTML',
    )

    # Step 2: Ask for break reason
    await bot.send_message(
        chat_id=user.telegram_id,
        text="What got in the way? (Tap one — this helps me help you)",
        reply_markup=create_break_reason_keyboard(),
        parse_mode='HTML',
    )

    logger.info(f"💔 Recovery ritual sent to {user.user_id} (streak: {previous_streak})")

    # Step 3: Notify partner
    await _notify_partner_of_break(bot, user, previous_streak)


async def _notify_partner_of_break(
    bot,
    user: User,
    previous_streak: int,
) -> None:
    """Notify accountability partner that user's streak broke."""
    if not user.accountability_partner_id:
        return

    if not user.partner_checkin_notifications_enabled:
        return

    partner = firestore_service.get_user(user.accountability_partner_id)
    if not partner:
        return

    try:
        first_name = user.name or user.telegram_username or "Your partner"
        await bot.send_message(
            chat_id=partner.telegram_id,
            text=(
                f"💔 <b>{first_name}'s streak broke</b>\n\n"
                f"They were on a {previous_streak}-day streak.\n\n"
                f"This is a great time to reach out with encouragement. "
                f"A simple message can make a huge difference.\n\n"
                f"Why not send them a quick note?"
            ),
            parse_mode='HTML',
        )
        logger.info(f"📨 Partner {partner.user_id} notified of break by {user.user_id}")
    except Exception as e:
        logger.warning(f"Failed to notify partner of break: {e}")


async def handle_break_reason_callback(
    bot,
    user_id: str,
    callback_data: str,
) -> str:
    """
    Handle break reason selection from inline button.

    Stores the reason and returns a confirmation message.
    """
    reason_key = callback_data.replace("break_", "")
    reason_label = BREAK_REASONS.get(reason_key, reason_key)

    # Store in Firestore
    user = firestore_service.get_user(user_id)
    if not user:
        return "❌ User not found."

    from src.utils.timezone_utils import get_current_date
    break_entry = {
        "date": get_current_date(),
        "reason": reason_key,
        "timestamp": datetime.utcnow(),
    }

    break_reasons = list(user.break_reasons) if hasattr(user, 'break_reasons') else []
    break_reasons.append(break_entry)

    firestore_service.update_user(user_id, {"break_reasons": break_reasons})

    logger.info(f"📊 Break reason recorded for {user_id}: {reason_key}")

    return (
        f"✅ Noted: <b>{reason_label}</b>\n\n"
        f"Thanks for sharing. I'll use this to spot patterns and help you prepare.\n\n"
        f"Ready to start your comeback? /checkin"
    )


def analyze_break_patterns(break_reasons: List[Dict]) -> Dict[str, Any]:
    """
    Analyze historical break reasons to identify patterns.

    Returns:
        {
            "most_common_reason": "sleep",
            "break_count": 5,
            "reason_distribution": {"sleep": 3, "work": 2},
        }
    """
    if not break_reasons:
        return {"has_data": False}

    from collections import Counter

    reasons = [b.get("reason", "unknown") for b in break_reasons]
    distribution = Counter(reasons)
    most_common = distribution.most_common(1)[0] if distribution else ("unknown", 0)

    return {
        "has_data": True,
        "break_count": len(break_reasons),
        "most_common_reason": most_common[0],
        "most_common_count": most_common[1],
        "reason_distribution": dict(distribution),
    }


def format_break_pattern_summary(break_reasons: List[Dict]) -> str:
    """Format break pattern analysis for display."""
    analysis = analyze_break_patterns(break_reasons)
    if not analysis["has_data"]:
        return ""

    lines = [
        f"📊 <b>Break Pattern Analysis</b>",
        f"",
        f"Total streak breaks: {analysis['break_count']}",
        f"Most common reason: {BREAK_REASONS.get(analysis['most_common_reason'], analysis['most_common_reason'])} ({analysis['most_common_count']}x)",
        f"",
    ]

    # Show top 3 reasons
    sorted_reasons = sorted(
        analysis["reason_distribution"].items(),
        key=lambda x: x[1],
        reverse=True,
    )[:3]

    for reason, count in sorted_reasons:
        label = BREAK_REASONS.get(reason, reason)
        lines.append(f"  • {label}: {count}x")

    return "\n".join(lines)
