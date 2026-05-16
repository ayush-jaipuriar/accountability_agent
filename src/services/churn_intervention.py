"""
Churn Intervention Service
===========================

Sends graduated interventions to at-risk users.

Tone: Softer than pattern interventions. These are "nudges," not "warnings."
Design: The message acknowledges the user's history (streak, past success)
and offers a low-friction path back (quick check-in or support).

Theory: Preemptive Retention
------------------------------
By the time a user ghosts for 2+ days, re-engagement is much harder.
Intervening while they're still checking in (but showing decline signals)
keeps them in the habit loop.
"""

import logging
from typing import List

from src.models.schemas import User

logger = logging.getLogger(__name__)


# Message templates by risk level
HIGH_RISK_MESSAGE = (
    "Hey {name}, I noticed your check-ins have been slipping. "
    "No judgment — life happens.\n\n"
    "Want to talk about what's getting in the way? Type /support\n"
    "Or just do a quick check-in to get back on track: /quickcheckin"
)

MEDIUM_RISK_MESSAGE = (
    "{name}, you've been doing great ({streak} days!). "
    "I noticed things have been a bit harder lately.\n\n"
    "One small win today is all it takes. Ready? /checkin"
)


def generate_intervention_message(user: User, risk_score: float, factors: List[str]) -> str:
    """
    Generate a churn prevention message based on risk score.
    
    Args:
        user: User object
        risk_score: 0.0-1.0 risk score
        factors: List of triggered risk factors
    
    Returns:
        Formatted message string, or empty string if no intervention needed
    """
    if risk_score >= 0.8:
        return HIGH_RISK_MESSAGE.format(
            name=user.name,
        )
    elif risk_score >= 0.5:
        streak = user.streaks.current_streak if user.streaks else 0
        return MEDIUM_RISK_MESSAGE.format(
            name=user.name,
            streak=streak,
        )
    else:
        return ""  # Low risk — don't message


async def send_churn_intervention(
    bot,
    user: User,
    risk_score: float,
    factors: List[str]
) -> bool:
    """
    Send a churn prevention intervention to a user via Telegram.
    
    Args:
        bot: Telegram bot instance
        user: User object
        risk_score: Calculated risk score
        factors: Triggered risk factors
    
    Returns:
        True if message was sent, False otherwise
    """
    message = generate_intervention_message(user, risk_score, factors)
    
    if not message:
        return False
    
    try:
        await bot.send_message(
            chat_id=user.telegram_id,
            text=message,
            parse_mode='HTML'
        )
        logger.info(
            f"🛟 Churn intervention sent to {user.user_id} "
            f"(score={risk_score:.2f}, factors={factors})"
        )
        return True
    except Exception as e:
        logger.error(f"❌ Failed to send churn intervention to {user.user_id}: {e}")
        return False
