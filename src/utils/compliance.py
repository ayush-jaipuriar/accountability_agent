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

from typing import Optional, List

from src.models.schemas import Tier1NonNegotiables, DailyTaskItem


def calculate_task_score(tasks: List[DailyTaskItem]) -> float:
    """
    Calculate the task score (0.0 to 100.0) based on task completion.
    
    Scoring logic:
    - Primary task represents:
      - 100% of task score if it's the only task committed.
      - 60% of task score if there is 1 secondary task.
      - 50% of task score if there are 2 secondary tasks.
    - Secondary tasks represent the remainder (40% or 50% total, split equally).
    """
    if not tasks:
        return 100.0

    primary_tasks = [t for t in tasks if t.is_primary]
    secondary_tasks = [t for t in tasks if not t.is_primary]

    if not primary_tasks and not secondary_tasks:
        return 100.0

    if primary_tasks and not secondary_tasks:
        # Only primary task committed
        return 100.0 if primary_tasks[0].completed else 0.0

    if not primary_tasks and secondary_tasks:
        # Only secondary tasks
        completed_sec = sum(1 for t in secondary_tasks if t.completed)
        return (completed_sec / len(secondary_tasks)) * 100.0

    # Both primary and secondary tasks are present
    primary_completed = primary_tasks[0].completed
    completed_sec = sum(1 for t in secondary_tasks if t.completed)
    total_sec = len(secondary_tasks)

    if total_sec == 1:
        # Primary: 60%, Secondary: 40%
        primary_weight = 60.0
        sec_weight = 40.0
    else:
        # Primary: 50%, Secondary: 50% (25% each if 2 tasks)
        primary_weight = 50.0
        sec_weight = 50.0

    sec_score = (completed_sec / total_sec) * sec_weight
    pri_score = primary_weight if primary_completed else 0.0
    return pri_score + sec_score


def calculate_compliance_score(
    tier1: Tier1NonNegotiables,
    committed_tasks: Optional[List[DailyTaskItem]] = None
) -> float:
    """
    Calculate compliance score as percentage of Tier 1 items completed.
    Optionally incorporates committed_tasks (20% weight) if present.
    
    <b>Phase 3D Expansion: 5 items → 6 items</b>
    
    Tier 1 Non-Negotiables (6 items):
    1. Sleep: 7+ hours
    2. Training: Workout OR rest day
    3. Deep Work: 2+ hours
    4. Skill Building: 2+ hours career-focused learning
    5. Zero Porn: No consumption (absolute)
    6. Boundaries: No toxic interactions
    
    <b>Impact on Scoring:</b>
    - Before Phase 3D: Each item = 20% (5 items)
    - After Phase 3D: Each item = 16.67% (6 items)
    - 100% requires all 6 items completed
    
    Args:
        tier1: Tier 1 non-negotiables responses
        committed_tasks: Optional list of committed daily tasks
        
    Returns:
        float: Score from 0.0 to 100.0
    """
    # Count completed items (Phase 3D: Now 6 items)
    items = [
        tier1.sleep,
        tier1.training or tier1.is_rest_day,
        tier1.deep_work,
        tier1.skill_building,  # Phase 3D: New item
        tier1.zero_porn,
        tier1.boundaries
    ]
    
    completed = sum(1 for item in items if item)
    total = len(items)
    tier1_score = (completed / total) * 100.0
    
    if committed_tasks:
        task_score = calculate_task_score(committed_tasks)
        return (tier1_score * 0.8) + (task_score * 0.2)
        
    return tier1_score


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
    checkin_date: Optional[str] = None,
    committed_tasks: Optional[List[DailyTaskItem]] = None
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
        committed_tasks: Optional list of committed daily tasks
        
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
            tier1.training or tier1.is_rest_day,
            tier1.deep_work,
            tier1.zero_porn,
            tier1.boundaries
        ]
        total = 5
    else:
        # Post-Phase 3D: 6 items
        items = [
            tier1.sleep,
            tier1.training or tier1.is_rest_day,
            tier1.deep_work,
            tier1.skill_building,
            tier1.zero_porn,
            tier1.boundaries
        ]
        total = 6
    
    completed = sum(1 for item in items if item)
    tier1_score = (completed / total) * 100.0
    
    if committed_tasks:
        task_score = calculate_task_score(committed_tasks)
        return (tier1_score * 0.8) + (task_score * 0.2)
        
    return tier1_score


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
        (tier1.training or tier1.is_rest_day) and
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
    if not (tier1.training or tier1.is_rest_day):
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
