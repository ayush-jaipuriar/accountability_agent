"""
Compliance Score Calculation
============================

Pure functions for calculating constitution compliance scores.

Why Pure Functions?
- Predictable: Same input → same output (no surprises)
- Testable: Easy to write unit tests
- No Side Effects: Doesn't modify database or external state
- Reusable: Can be called from anywhere

Compliance Score Formula:
    score = (completed_items / total_items) * 100
    
Where total_items = 5 (Tier 1 non-negotiables)
"""

from src.models.schemas import Tier1NonNegotiables


def calculate_compliance_score(tier1: Tier1NonNegotiables) -> float:
    """
    Calculate compliance score as percentage of Tier 1 items completed.
    
    Tier 1 Non-Negotiables (5 items):
    1. Sleep: 7+ hours
    2. Training: Workout OR rest day
    3. Deep Work: 2+ hours
    4. Zero Porn: No consumption (absolute)
    5. Boundaries: No toxic interactions
    
    Args:
        tier1: Tier 1 non-negotiables responses
        
    Returns:
        float: Score from 0.0 to 100.0
        
    Examples:
        >>> tier1 = Tier1NonNegotiables(
        ...     sleep=True, training=True, deep_work=False,
        ...     zero_porn=True, boundaries=True
        ... )
        >>> calculate_compliance_score(tier1)
        80.0
        
        >>> tier1_perfect = Tier1NonNegotiables(
        ...     sleep=True, training=True, deep_work=True,
        ...     zero_porn=True, boundaries=True
        ... )
        >>> calculate_compliance_score(tier1_perfect)
        100.0
    """
    # Count completed items
    items = [
        tier1.sleep,
        tier1.training,
        tier1.deep_work,
        tier1.zero_porn,
        tier1.boundaries
    ]
    
    completed = sum(1 for item in items if item)
    total = len(items)
    
    return (completed / total) * 100.0


def get_compliance_level(score: float) -> str:
    """
    Categorize compliance score into performance levels.
    
    Levels (from constitution):
    - Excellent: 90-100% (constitution mastery)
    - Good: 80-89% (solid consistency)
    - Warning: 60-79% (slipping, needs attention)
    - Critical: <60% (danger zone, spiral risk)
    
    Args:
        score: Compliance score (0-100)
        
    Returns:
        str: Level name ("excellent", "good", "warning", "critical")
        
    Examples:
        >>> get_compliance_level(100.0)
        'excellent'
        >>> get_compliance_level(85.0)
        'good'
        >>> get_compliance_level(70.0)
        'warning'
        >>> get_compliance_level(50.0)
        'critical'
    """
    if score >= 90:
        return "excellent"
    elif score >= 80:
        return "good"
    elif score >= 60:
        return "warning"
    else:
        return "critical"


def get_compliance_emoji(score: float) -> str:
    """
    Get emoji representation of compliance level.
    
    Useful for visual feedback in Telegram messages.
    
    Args:
        score: Compliance score (0-100)
        
    Returns:
        str: Emoji representing performance level
    """
    level = get_compliance_level(score)
    
    emoji_map = {
        "excellent": "🎯",   # Target - perfect execution
        "good": "✅",         # Check mark - solid
        "warning": "⚠️",     # Warning - pay attention
        "critical": "🚨"     # Alert - emergency
    }
    
    return emoji_map[level]


def format_compliance_message(score: float, streak: int) -> str:
    """
    Generate formatted compliance feedback message (Phase 1 - Hardcoded).
    
    In Phase 2, this will be replaced with AI-generated personalized feedback.
    For now, we use templates.
    
    Args:
        score: Compliance score (0-100)
        streak: Current streak (consecutive days)
        
    Returns:
        str: Formatted message with emoji and encouragement
        
    Examples:
        >>> format_compliance_message(100.0, 47)
        '🎯 Perfect day! Compliance: 100.0%\\nStreak: 47 days - You're unstoppable!'
    """
    emoji = get_compliance_emoji(score)
    level = get_compliance_level(score)
    
    # Level-specific encouragement
    encouragement = {
        "excellent": f"Streak: {streak} days - You're unstoppable!",
        "good": f"Streak: {streak} days - Solid consistency!",
        "warning": f"Streak: {streak} days - Let's tighten up tomorrow.",
        "critical": f"Streak: {streak} days - Time to refocus. You know what to do."
    }
    
    # Level-specific header
    headers = {
        "excellent": "Perfect day!",
        "good": "Strong day!",
        "warning": "Room for improvement.",
        "critical": "Below standards."
    }
    
    message = f"{emoji} {headers[level]} Compliance: {score:.1f}%\n{encouragement[level]}"
    
    return message


# ===== Tier 1 Breakdown Analysis =====

def get_tier1_breakdown(tier1: Tier1NonNegotiables) -> dict:
    """
    Get detailed breakdown of which Tier 1 items were completed.
    
    Useful for analytics and pattern detection (Phase 2).
    
    Args:
        tier1: Tier 1 non-negotiables
        
    Returns:
        dict: Breakdown with completion status and details
        
    Example:
        >>> breakdown = get_tier1_breakdown(tier1)
        >>> breakdown['sleep']['completed']
        True
        >>> breakdown['sleep']['hours']
        7.5
    """
    return {
        "sleep": {
            "completed": tier1.sleep,
            "hours": tier1.sleep_hours
        },
        "training": {
            "completed": tier1.training,
            "is_rest_day": tier1.is_rest_day,
            "type": tier1.training_type
        },
        "deep_work": {
            "completed": tier1.deep_work,
            "hours": tier1.deep_work_hours
        },
        "zero_porn": {
            "completed": tier1.zero_porn
        },
        "boundaries": {
            "completed": tier1.boundaries
        }
    }


def get_missed_items(tier1: Tier1NonNegotiables) -> list[str]:
    """
    Get list of Tier 1 items that were NOT completed.
    
    Useful for targeted feedback.
    
    Args:
        tier1: Tier 1 non-negotiables
        
    Returns:
        list: Names of missed items
        
    Example:
        >>> missed = get_missed_items(tier1)
        >>> missed
        ['deep_work']
    """
    missed = []
    
    if not tier1.sleep:
        missed.append("sleep")
    if not tier1.training:
        missed.append("training")
    if not tier1.deep_work:
        missed.append("deep_work")
    if not tier1.zero_porn:
        missed.append("zero_porn")
    if not tier1.boundaries:
        missed.append("boundaries")
    
    return missed
