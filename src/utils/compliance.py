"""
Compliance Score Calculation
============================

Pure functions for calculating constitution compliance scores.

Why Pure Functions?
- Predictable: Same input → same output (no surprises)
- Testable: Easy to write unit tests
- No Side Effects: Doesn't modify database or external state
- Reusable: Can be called from anywhere

Compliance Score Formula (v3 — Proportional Credit):
    For continuous habits (sleep, deep work, skill building):
        credit = min(actual_hours / target_hours, 1.0)
    For binary habits (training, zero_porn, boundaries):
        credit = 1.0 if met else 0.0
    score = (sum_of_credits / 6) * 100

    This replaced the v2 binary formula (completed_items / 6 * 100) which
    gave zero credit for partial effort, causing learned helplessness.
    See impact_analysis_2026-08-04.md for the data that motivated this change.
"""

from typing import Optional, List

from src.models.schemas import Tier1NonNegotiables, DailyTaskItem


def habit_credit(
    actual: Optional[float],
    target: float,
    floor: float = 0.0
) -> float:
    """
    Calculate proportional credit for a continuous habit.

    Returns a value from 0.0 to 1.0 representing how much of the
    target the user achieved. Effort below `floor` (as a fraction
    of target) scores 0 — this prevents gaming with trivially small
    values.

    Why Proportional Credit?
    - 1.5h deep work against a 2h target = 0.75 credit, not 0
    - 0.7h skill building against a 2h target = 0.35 credit, not 0
    - This rewards real effort instead of punishing near-misses

    Args:
        actual: Actual hours logged (None = no data, falls through)
        target: Target hours for full credit (e.g. 7.0 for sleep)
        floor: Minimum ratio to earn any credit (0.0 = any effort counts)

    Returns:
        float: Credit between 0.0 and 1.0

    Examples:
        >>> habit_credit(7.5, 7.0)
        1.0
        >>> habit_credit(5.0, 7.0)
        0.7142857142857143
        >>> habit_credit(1.5, 2.0)
        0.75
        >>> habit_credit(0.0, 2.0)
        0.0
        >>> habit_credit(None, 2.0)
        0.0
    """
    if actual is None or actual <= 0:
        return 0.0
    if target is None or target <= 0:
        return 1.0 if actual > 0 else 0.0
    ratio = min(actual / target, 1.0)
    return ratio if ratio >= floor else 0.0


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
    Calculate compliance score with proportional credit for continuous habits.
    Optionally incorporates committed_tasks (20% weight) if present.
    
    <b>v3 — Proportional Credit (replaces binary pass/fail)</b>
    
    Tier 1 Non-Negotiables (6 items):
    1. Sleep: Proportional credit up to 7h target
    2. Training: Binary — workout OR rest day
    3. Deep Work: Proportional credit up to 2h target
    4. Skill Building: Proportional credit up to 2h target
    5. Zero Porn: Binary — no consumption (absolute)
    6. Boundaries: Binary — no toxic interactions
    
    <b>Why Proportional?</b>
    Impact analysis (2026-08-04) showed that binary scoring caused users to
    abandon deep work and skill building after months of "doing the work but
    scoring 0%." Users averaged 1.39h deep work and 0.72h skill building —
    real effort — but scored 0% for both because they didn't hit 2h.
    
    Now: 1.5h deep work = 75% credit for that habit. 0.7h skill building =
    35% credit. Any effort is reflected in the score.
    
    <b>Backward Compatibility:</b>
    - Binary habits (training, zero_porn, boundaries) score identically
    - When continuous data is absent (legacy check-ins), falls back to
      boolean fields which behave the same as before
    - Historical scores stored in Firestore are NOT retroactively changed
    
    Args:
        tier1: Tier 1 non-negotiables responses
        committed_tasks: Optional list of committed daily tasks
        
    Returns:
        float: Score from 0.0 to 100.0
    """
    # Proportional credit for continuous habits, binary for the rest
    credits = [
        # Sleep: proportional up to 7h, fallback to boolean
        habit_credit(tier1.sleep_hours, 7.0) if tier1.sleep_hours is not None
        else (1.0 if tier1.sleep else 0.0),

        # Training: binary (did they train or rest?)
        1.0 if (tier1.training or tier1.is_rest_day) else 0.0,

        # Deep work: proportional up to 2h, fallback to boolean
        habit_credit(tier1.deep_work_hours, 2.0) if tier1.deep_work_hours is not None
        else (1.0 if tier1.deep_work else 0.0),

        # Skill building: proportional up to 2h, fallback to boolean
        habit_credit(tier1.skill_building_hours, 2.0) if tier1.skill_building_hours is not None
        else (1.0 if tier1.skill_building else 0.0),

        # Zero porn: binary
        1.0 if tier1.zero_porn else 0.0,

        # Boundaries: binary
        1.0 if tier1.boundaries else 0.0,
    ]
    
    tier1_score = (sum(credits) / len(credits)) * 100.0
    
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
        # Pre-Phase 3D: 5 items, binary (no continuous data available)
        items = [
            tier1.sleep,
            tier1.training or tier1.is_rest_day,
            tier1.deep_work,
            tier1.zero_porn,
            tier1.boundaries
        ]
        completed = sum(1 for item in items if item)
        tier1_score = (completed / 5) * 100.0
    else:
        # Post-Phase 3D: 6 items, proportional credit (v3 scoring)
        credits = [
            habit_credit(tier1.sleep_hours, 7.0) if tier1.sleep_hours is not None
            else (1.0 if tier1.sleep else 0.0),

            1.0 if (tier1.training or tier1.is_rest_day) else 0.0,

            habit_credit(tier1.deep_work_hours, 2.0) if tier1.deep_work_hours is not None
            else (1.0 if tier1.deep_work else 0.0),

            habit_credit(tier1.skill_building_hours, 2.0) if tier1.skill_building_hours is not None
            else (1.0 if tier1.skill_building else 0.0),

            1.0 if tier1.zero_porn else 0.0,

            1.0 if tier1.boundaries else 0.0,
        ]
        tier1_score = (sum(credits) / len(credits)) * 100.0
    
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


def get_missed_items(tier1: Tier1NonNegotiables, checkin_date: Optional[str] = None) -> list:
    """
    Get list of Tier 1 items that were NOT completed.
    
    Useful for targeted feedback.
    
    Args:
        tier1: Tier 1 non-negotiables
        checkin_date: Optional date of check-in (YYYY-MM-DD) for Phase 3D compat
        
    Returns:
        list: Names of missed items
        
    Example:
        >>> missed = get_missed_items(tier1)
        >>> missed
        ['deep_work']
    """
    from src.config import settings
    is_pre_phase3d = False
    if checkin_date:
        is_pre_phase3d = checkin_date < settings.phase_3d_deployment_date
    
    missed = []
    
    if not tier1.sleep:
        missed.append("sleep")
    if not (tier1.training or tier1.is_rest_day):
        missed.append("training")
    if not tier1.deep_work:
        missed.append("deep_work")
    if not is_pre_phase3d and not tier1.skill_building:  # Phase 3D: New item
        missed.append("skill_building")
    if not tier1.zero_porn:
        missed.append("zero_porn")
    if not tier1.boundaries:
        missed.append("boundaries")
    
    return missed
