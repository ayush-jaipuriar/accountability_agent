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
    
Where total_items = 6 (Tier 1 non-negotiables - Phase 3D expansion)
"""

from typing import Optional

from src.models.schemas import Tier1NonNegotiables


def calculate_compliance_score(tier1: Tier1NonNegotiables) -> float:
    """
    Calculate compliance score as percentage of Tier 1 items completed.
    
    **Phase 3D Expansion: 5 items → 6 items**
    
    Tier 1 Non-Negotiables (6 items):
    1. Sleep: 7+ hours
    2. Training: Workout OR rest day
    3. Deep Work: 2+ hours
    4. Skill Building: 2+ hours career-focused learning (NEW in Phase 3D)
    5. Zero Porn: No consumption (absolute)
    6. Boundaries: No toxic interactions
    
    **Impact on Scoring:**
    - Before Phase 3D: Each item = 20% (5 items)
    - After Phase 3D: Each item = 16.67% (6 items)
    - 100% requires all 6 items completed
    
    Args:
        tier1: Tier 1 non-negotiables responses
        
    Returns:
        float: Score from 0.0 to 100.0
        
    Examples:
        >>> tier1 = Tier1NonNegotiables(
        ...     sleep=True, training=True, deep_work=False,
        ...     skill_building=True, zero_porn=True, boundaries=True
        ... )
        >>> calculate_compliance_score(tier1)
        83.33  # 5/6 items completed
        
        >>> tier1_perfect = Tier1NonNegotiables(
        ...     sleep=True, training=True, deep_work=True,
        ...     skill_building=True, zero_porn=True, boundaries=True
        ... )
        >>> calculate_compliance_score(tier1_perfect)
        100.0  # 6/6 items completed
    """
    # Count completed items (Phase 3D: Now 6 items)
    items = [
        tier1.sleep,
        tier1.training,
        tier1.deep_work,
        tier1.skill_building,  # Phase 3D: New item
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
        "critical": f"Streak: {streak} days - Tomorrow is a fresh start. The fact that you checked in shows real commitment.\nNeed to talk? Just type how you're feeling."
    }
    
    # Level-specific header
    headers = {
        "excellent": "Perfect day!",
        "good": "Strong day!",
        "warning": "Room for improvement.",
        "critical": "Tough day."
    }
    
    message = f"{emoji} {headers[level]} Compliance: {score:.1f}%\n{encouragement[level]}"
    
    return message


def calculate_compliance_score_normalized(
    tier1: Tier1NonNegotiables,
    checkin_date: Optional[str] = None
) -> float:
    """
    Calculate compliance score with Phase 3D backward compatibility.
    
    WHY THIS EXISTS:
    ----------------
    Phase 3D (deployed 2026-02-05) added Skill Building as a 6th Tier 1 item.
    Check-ins before this date had 5 items. When their tier1_non_negotiables are
    loaded from Firestore, skill_building defaults to False (Pydantic default).
    
    If you recalculate compliance using the 6-item formula, old check-ins max out
    at 83.3% (5/6) instead of their original 100% (5/5). This creates a fake
    decline in historical stats.
    
    This function detects the era and uses the correct denominator:
    - Pre-Phase 3D: score = completed / 5 * 100 (exclude skill_building)
    - Post-Phase 3D: score = completed / 6 * 100 (include skill_building)
    
    NOTE: The stored compliance_score in Firestore is already correct. Use this
    function only when RE-EVALUATING tier1 data (e.g., achievement checks, reports
    that re-aggregate from raw tier1 booleans).
    
    Args:
        tier1: Tier 1 non-negotiables
        checkin_date: Check-in date in YYYY-MM-DD format. If None, uses 6-item formula.
        
    Returns:
        float: Normalized compliance score (0.0 to 100.0)
    """
    from src.config import settings
    
    # Determine which era this check-in belongs to
    is_pre_phase3d = False
    if checkin_date:
        is_pre_phase3d = checkin_date < settings.phase_3d_deployment_date
    
    if is_pre_phase3d:
        # Pre-Phase 3D: 5 items (exclude skill_building)
        items = [
            tier1.sleep,
            tier1.training,
            tier1.deep_work,
            tier1.zero_porn,
            tier1.boundaries
        ]
        total = 5
    else:
        # Post-Phase 3D: 6 items
        items = [
            tier1.sleep,
            tier1.training,
            tier1.deep_work,
            tier1.skill_building,
            tier1.zero_porn,
            tier1.boundaries
        ]
        total = 6
    
    completed = sum(1 for item in items if item)
    return (completed / total) * 100.0


def is_all_tier1_complete(tier1: Tier1NonNegotiables, checkin_date: Optional[str] = None) -> bool:
    """
    Check if all Tier 1 items are complete, with Phase 3D backward compatibility.
    
    Pre-Phase 3D: checks 5 items (excludes skill_building)
    Post-Phase 3D: checks all 6 items
    
    Args:
        tier1: Tier 1 non-negotiables
        checkin_date: Check-in date (YYYY-MM-DD). If None, checks all 6 items.
        
    Returns:
        bool: True if all applicable Tier 1 items are complete
    """
    from src.config import settings
    
    is_pre_phase3d = False
    if checkin_date:
        is_pre_phase3d = checkin_date < settings.phase_3d_deployment_date
    
    base_complete = (
        tier1.sleep and
        tier1.training and
        tier1.deep_work and
        tier1.zero_porn and
        tier1.boundaries
    )
    
    if is_pre_phase3d:
        return base_complete
    else:
        return base_complete and tier1.skill_building


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
        "skill_building": {  # Phase 3D: New item
            "completed": tier1.skill_building,
            "hours": tier1.skill_building_hours,
            "activity": tier1.skill_building_activity
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
    if not tier1.skill_building:  # Phase 3D: New item
        missed.append("skill_building")
    if not tier1.zero_porn:
        missed.append("zero_porn")
    if not tier1.boundaries:
        missed.append("boundaries")
    
    return missed
