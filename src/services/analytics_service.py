"""
Analytics Service - Stats Calculation & Aggregation
===================================================

Phase 3E: Provides stats calculations for /weekly, /monthly, /yearly commands.

<b>Purpose:</b>
Calculate summary statistics from historical check-in data:
- Compliance averages and trends
- Tier 1 item completion rates
- Streak information
- Pattern detection counts
- Achievement unlocks

<b>Why a Separate Service:</b>
- Reusable logic across commands (weekly, monthly, yearly)
- Centralized calculation algorithms
- Easy to test and maintain
- Can be used by dashboard, reports, or API endpoints

<b>Key Functions:</b>
- calculate_weekly_stats(): Last 7 days summary
- calculate_monthly_stats(): Last 30 days summary
- calculate_yearly_stats(): Year-to-date summary
"""

import logging
from datetime import datetime, timedelta
from statistics import mean
from typing import List, Dict, Any, Optional

from src.models.schemas import DailyCheckIn, User, Tier1NonNegotiables
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


def calculate_weekly_stats(user_id: str) -> Dict[str, Any]:
    """
    Calculate last 7 days statistics.
    
    <b>Output Structure:</b>
    - Compliance: Average, trend
    - Streaks: Current streak, check-in rate
    - Tier 1 Performance: Completion rates for each item
    - Patterns: Count of detected patterns
    
    Args:
        user_id: User ID to calculate stats for
        
    Returns:
        Dictionary with weekly stats
    """
    try:
        # Fetch data
        user = firestore_service.get_user(user_id)
        checkins = firestore_service.get_recent_checkins(user_id, days=7)
        patterns = firestore_service.get_patterns(user_id, days=7)
        
        if not checkins:
            return {
                "error": "No check-ins found in last 7 days",
                "has_data": False
            }
        
        # Calculate compliance
        compliance_scores = [c.compliance_score for c in checkins]
        avg_compliance = mean(compliance_scores)
        
        # Calculate trend (compare first 3 days vs last 4 days)
        if len(checkins) >= 6:
            first_half = compliance_scores[:3]
            second_half = compliance_scores[3:]
            trend_diff = mean(second_half) - mean(first_half)
            
            if trend_diff >= 5:
                trend = "↗️ +{:.0f}%".format(trend_diff)
            elif trend_diff <= -5:
                trend = "↘️ {:.0f}%".format(trend_diff)
            else:
                trend = "→ Stable"
        else:
            trend = "→ Stable"
        
        # Calculate Tier 1 performance
        tier1_stats = _calculate_tier1_stats(checkins)
        
        # Count patterns
        pattern_count = len(patterns)
        
        return {
            "has_data": True,
            "period": "Last 7 Days",
            "date_range": f"{checkins[0].date} - {checkins[-1].date}",
            "compliance": {
                "average": avg_compliance,
                "trend": trend,
                "max": max(compliance_scores),
                "min": min(compliance_scores)
            },
            "streaks": {
                "current": user.streaks.current_streak,
                "checkin_rate": f"{len(checkins)}/7",
                "completion_pct": (len(checkins) / 7) * 100
            },
            "tier1": tier1_stats,
            "patterns": {
                "count": pattern_count,
                "message": "None detected ✨" if pattern_count == 0 else f"{pattern_count} patterns"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Weekly stats calculation failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "has_data": False
        }


def calculate_monthly_stats(user_id: str) -> Dict[str, Any]:
    """
    Calculate last 30 days statistics.
    
    Similar to weekly but with:
    - Week-by-week breakdown
    - Achievement tracking
    - Deeper pattern analysis
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary with monthly stats
    """
    try:
        # Fetch data
        user = firestore_service.get_user(user_id)
        checkins = firestore_service.get_recent_checkins(user_id, days=30)
        patterns = firestore_service.get_patterns(user_id, days=30)
        
        if not checkins:
            return {
                "error": "No check-ins found in last 30 days",
                "has_data": False
            }
        
        # Calculate compliance
        compliance_scores = [c.compliance_score for c in checkins]
        avg_compliance = mean(compliance_scores)
        
        # Weekly breakdown (4 weeks)
        weekly_breakdown = _calculate_weekly_breakdown(checkins)
        best_week = max(weekly_breakdown, key=lambda w: w["avg_compliance"])
        worst_week = min(weekly_breakdown, key=lambda w: w["avg_compliance"])
        
        # Calculate Tier 1 performance
        tier1_stats = _calculate_tier1_stats(checkins)
        
        # Achievements (last 30 days)
        recent_achievements = _get_recent_achievements(user, days=30)
        
        # Patterns
        pattern_summary = _summarize_patterns(patterns)
        
        # Percentile rank (simulated - would need all users' data)
        percentile = _estimate_percentile(avg_compliance)
        
        return {
            "has_data": True,
            "period": "Last 30 Days",
            "date_range": f"{checkins[0].date} - {checkins[-1].date}",
            "compliance": {
                "average": avg_compliance,
                "best_week": f"Week {best_week['week_num']} ({best_week['avg_compliance']:.0f}%)",
                "worst_week": f"Week {worst_week['week_num']} ({worst_week['avg_compliance']:.0f}%)"
            },
            "streaks": {
                "current": user.streaks.current_streak,
                "longest_this_month": user.streaks.longest_streak,
                "checkin_rate": f"{len(checkins)}/30",
                "completion_pct": (len(checkins) / 30) * 100
            },
            "tier1": tier1_stats,
            "achievements": {
                "count": len(recent_achievements),
                "list": recent_achievements
            },
            "patterns": pattern_summary,
            "social_proof": {
                "percentile": percentile,
                "message": f"You're in the top {100 - percentile}% of users this month! 🎯"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Monthly stats calculation failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "has_data": False
        }


def calculate_yearly_stats(user_id: str) -> Dict[str, Any]:
    """
    Calculate year-to-date statistics.
    
    <b>What's Different from Monthly:</b>
    - All data since Jan 1 of current year
    - Monthly breakdown (Jan, Feb, Mar...)
    - Career progress tracking
    - Total achievements count
    
    Args:
        user_id: User ID
        
    Returns:
        Dictionary with yearly stats
    """
    try:
        # Fetch data
        user = firestore_service.get_user(user_id)
        
        # Calculate days since start of year
        today = datetime.now()
        year_start = datetime(today.year, 1, 1)
        days_in_year = (today - year_start).days + 1
        
        # Fetch all check-ins this year
        checkins = firestore_service.get_recent_checkins(user_id, days=days_in_year)
        patterns = firestore_service.get_patterns(user_id, days=days_in_year)
        
        if not checkins:
            return {
                "error": f"No check-ins found in {today.year}",
                "has_data": False
            }
        
        # Calculate compliance
        compliance_scores = [c.compliance_score for c in checkins]
        avg_compliance = mean(compliance_scores)
        
        # Monthly breakdown
        monthly_breakdown = _calculate_monthly_breakdown(checkins, today)
        
        # Calculate Tier 1 performance (averaged)
        tier1_stats = _calculate_tier1_stats(checkins)
        
        # Career progress (skill building frequency)
        skill_building_days = sum(
            1 for c in checkins 
            if c.tier1_non_negotiables.skill_building
        )
        
        return {
            "has_data": True,
            "period": f"{today.year} Year to Date",
            "date_range": f"Jan 1 - {today.strftime('%b %d')}",
            "overview": {
                "days_tracked": len(checkins),
                "total_days": days_in_year,
                "completion_pct": (len(checkins) / days_in_year) * 100,
                "avg_compliance": avg_compliance
            },
            "streaks": {
                "current": user.streaks.current_streak,
                "longest_this_year": user.streaks.longest_streak,
                "total_checkins": user.streaks.total_checkins
            },
            "monthly_breakdown": monthly_breakdown,
            "achievements": {
                "total": len(user.achievements),
                "message": f"{len(user.achievements)} unlocked"
            },
            "patterns": {
                "total": len(patterns),
                "message": f"{len(patterns)} detected (all resolved)" if patterns else "None detected ✨"
            },
            "career_progress": {
                "skill_building_days": skill_building_days,
                "consistency_pct": (skill_building_days / len(checkins)) * 100,
                "career_mode": user.career_mode,
                "target_date": "June 2026",
                "target_salary": "₹28-42 LPA"
            }
        }
        
    except Exception as e:
        logger.error(f"❌ Yearly stats calculation failed: {e}", exc_info=True)
        return {
            "error": str(e),
            "has_data": False
        }


def _calculate_tier1_stats(checkins: List[DailyCheckIn]) -> Dict[str, Any]:
    """
    Calculate Tier 1 item completion statistics.
    
    Returns completion rates and averages for:
    - Sleep (% days + average hours)
    - Training (% days + type breakdown)
    - Deep Work (% days + average hours)
    - Skill Building (% days + average hours)
    - Zero Porn (% days)
    - Boundaries (% days)
    
    Args:
        checkins: List of check-ins to analyze
        
    Returns:
        Dictionary with Tier 1 stats
    """
    total_days = len(checkins)
    
    # Count completions
    sleep_days = sum(1 for c in checkins if c.tier1_non_negotiables.sleep)
    training_days = sum(1 for c in checkins if c.tier1_non_negotiables.training)
    deep_work_days = sum(1 for c in checkins if c.tier1_non_negotiables.deep_work)
    skill_building_days = sum(1 for c in checkins if c.tier1_non_negotiables.skill_building)
    zero_porn_days = sum(1 for c in checkins if c.tier1_non_negotiables.zero_porn)
    boundaries_days = sum(1 for c in checkins if c.tier1_non_negotiables.boundaries)
    
    # Calculate averages for quantifiable items
    sleep_hours = [c.tier1_non_negotiables.sleep_hours 
                   for c in checkins 
                   if c.tier1_non_negotiables.sleep_hours is not None]
    avg_sleep = mean(sleep_hours) if sleep_hours else 0
    
    deep_work_hours = [c.tier1_non_negotiables.deep_work_hours 
                       for c in checkins 
                       if c.tier1_non_negotiables.deep_work_hours is not None]
    avg_deep_work = mean(deep_work_hours) if deep_work_hours else 0
    
    skill_building_hours = [c.tier1_non_negotiables.skill_building_hours 
                            for c in checkins 
                            if c.tier1_non_negotiables.skill_building_hours is not None]
    avg_skill_building = mean(skill_building_hours) if skill_building_hours else 0
    
    # Calculate min/max for continuous metrics
    sleep_min = min(sleep_hours) if sleep_hours else 0
    sleep_max = max(sleep_hours) if sleep_hours else 0
    
    dw_min = min(deep_work_hours) if deep_work_hours else 0
    dw_max = max(deep_work_hours) if deep_work_hours else 0
    
    sb_min = min(skill_building_hours) if skill_building_hours else 0
    sb_max = max(skill_building_hours) if skill_building_hours else 0
    
    return {
        "sleep": {
            "days": sleep_days,
            "total": total_days,
            "pct": (sleep_days / total_days) * 100,
            "avg_hours": avg_sleep,
            "min_hours": sleep_min,
            "max_hours": sleep_max,
            "target": 7.0
        },
        "training": {
            "days": training_days,
            "total": total_days,
            "pct": (training_days / total_days) * 100
        },
        "deep_work": {
            "days": deep_work_days,
            "total": total_days,
            "pct": (deep_work_days / total_days) * 100,
            "avg_hours": avg_deep_work,
            "min_hours": dw_min,
            "max_hours": dw_max,
            "target": 2.0
        },
        "skill_building": {
            "days": skill_building_days,
            "total": total_days,
            "pct": (skill_building_days / total_days) * 100,
            "avg_hours": avg_skill_building,
            "min_hours": sb_min,
            "max_hours": sb_max,
            "target": 2.0
        },
        "zero_porn": {
            "days": zero_porn_days,
            "total": total_days,
            "pct": (zero_porn_days / total_days) * 100
        },
        "boundaries": {
            "days": boundaries_days,
            "total": total_days,
            "pct": (boundaries_days / total_days) * 100
        }
    }


def _calculate_weekly_breakdown(checkins: List[DailyCheckIn]) -> List[Dict[str, Any]]:
    """
    Break down 30 days into 4 weeks with stats for each.
    
    Args:
        checkins: 30 days of check-ins
        
    Returns:
        List of 4 week summaries
    """
    weeks = []
    
    for week_num in range(1, 5):
        start_idx = (week_num - 1) * 7
        end_idx = min(week_num * 7, len(checkins))
        week_checkins = checkins[start_idx:end_idx]
        
        if week_checkins:
            avg_compliance = mean([c.compliance_score for c in week_checkins])
            weeks.append({
                "week_num": week_num,
                "days": len(week_checkins),
                "avg_compliance": avg_compliance
            })
    
    return weeks


def _calculate_monthly_breakdown(checkins: List[DailyCheckIn], today: datetime) -> List[Dict[str, Any]]:
    """
    Break down year-to-date into months with stats for each.
    
    Args:
        checkins: All check-ins this year
        today: Current date
        
    Returns:
        List of month summaries
    """
    # Group check-ins by month
    monthly_data = {}
    
    for checkin in checkins:
        # Parse date string to get month
        date_obj = datetime.strptime(checkin.date, "%Y-%m-%d")
        month_key = date_obj.strftime("%b")  # "Jan", "Feb", etc.
        
        if month_key not in monthly_data:
            monthly_data[month_key] = []
        
        monthly_data[month_key].append(checkin)
    
    # Calculate stats for each month
    months = []
    month_order = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", 
                   "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
    
    for month_name in month_order:
        if month_name in monthly_data:
            month_checkins = monthly_data[month_name]
            avg_compliance = mean([c.compliance_score for c in month_checkins])
            
            months.append({
                "month": month_name,
                "days": len(month_checkins),
                "avg_compliance": f"{avg_compliance:.0f}%"
            })
    
    return months


def _get_recent_achievements(user: User, days: int = 30) -> List[str]:
    """
    Get achievements unlocked in last N days.
    
    Note: This is a simplified version. In production, we'd track
    unlock timestamps in Firestore.
    
    Args:
        user: User profile
        days: Number of days to look back
        
    Returns:
        List of achievement names
    """
    # For now, just return the last 2 achievements
    # In production, we'd filter by unlock_date
    if len(user.achievements) > 0:
        return user.achievements[-2:]  # Last 2 achievements
    else:
        return []


def _summarize_patterns(patterns: List[Any]) -> Dict[str, Any]:
    """
    Summarize patterns detected in the period.
    
    Args:
        patterns: List of detected patterns
        
    Returns:
        Pattern summary dictionary
    """
    if not patterns:
        return {
            "count": 0,
            "message": "None detected ✨"
        }
    
    # Count by pattern type
    pattern_counts = {}
    for pattern in patterns:
        pattern_type = pattern.pattern_name
        pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
    
    # Find most common
    most_common = max(pattern_counts.items(), key=lambda x: x[1]) if pattern_counts else None
    
    return {
        "count": len(patterns),
        "most_common": most_common[0] if most_common else None,
        "message": f"{len(patterns)} detected (all resolved)"
    }


def _estimate_percentile(compliance: float) -> int:
    """
    Estimate user's percentile rank based on compliance.
    
    Simplified algorithm:
    - 95%+ compliance → top 10%
    - 85-94% → top 20%
    - 75-84% → top 40%
    - 65-74% → top 60%
    - <65% → top 80%
    
    In production, this would query all users' data.
    
    Args:
        compliance: Average compliance score
        
    Returns:
        Percentile (0-100)
    """
    if compliance >= 95:
        return 90  # Top 10%
    elif compliance >= 85:
        return 80  # Top 20%
    elif compliance >= 75:
        return 60  # Top 40%
    elif compliance >= 65:
        return 40  # Top 60%
    else:
        return 20  # Top 80%


# ===== Phase 4: Deeper Per-Metric Tracking =====

TIER1_METRICS = ["sleep", "training", "deep_work", "skill_building", "zero_porn", "boundaries"]

METRIC_LABELS = {
    "sleep": "Sleep 7h+",
    "training": "Training",
    "deep_work": "Deep Work",
    "skill_building": "Skill Building",
    "zero_porn": "Zero Porn",
    "boundaries": "Boundaries",
}

METRIC_EMOJIS = {
    "sleep": "😴",
    "training": "💪",
    "deep_work": "🧠",
    "skill_building": "📚",
    "zero_porn": "🚫",
    "boundaries": "🛡️",
}


def calculate_metric_streaks(checkins: List[DailyCheckIn]) -> Dict[str, int]:
    """
    Calculate current consecutive-day streak for each Tier 1 metric.

    Walks the check-in list (assumed newest-first) and counts how many
    consecutive days each metric was completed from the most recent day.
    The streak breaks on the first missed day.

    Returns dict mapping metric name -> current streak length.
    """
    sorted_by_date = sorted(checkins, key=lambda c: c.date, reverse=True)
    streaks = {m: 0 for m in TIER1_METRICS}

    for metric in TIER1_METRICS:
        for c in sorted_by_date:
            val = getattr(c.tier1_non_negotiables, metric, False)
            if val:
                streaks[metric] += 1
            else:
                break

    return streaks


def calculate_metric_trends(
    checkins: List[DailyCheckIn],
    days: int = 7,
) -> Dict[str, Dict[str, Any]]:
    """
    Week-over-week trend for each Tier 1 metric.

    Splits the check-ins into two halves (recent vs older) and computes
    the change in completion rate between them. This gives a directional
    signal: is each metric improving, declining, or stable?

    Args:
        checkins: All available check-ins (should be >= 2*days for comparison)
        days: Window size for the "current" period (default 7)

    Returns:
        Dict[metric_name, {"current_pct": float, "previous_pct": float,
                           "change": float, "direction": str}]
    """
    sorted_asc = sorted(checkins, key=lambda c: c.date)
    current = sorted_asc[-days:] if len(sorted_asc) >= days else sorted_asc
    previous = sorted_asc[-(2 * days):-days] if len(sorted_asc) >= 2 * days else []

    trends = {}
    for metric in TIER1_METRICS:
        cur_count = sum(1 for c in current if getattr(c.tier1_non_negotiables, metric, False))
        cur_pct = (cur_count / len(current) * 100) if current else 0

        if previous:
            prev_count = sum(1 for c in previous if getattr(c.tier1_non_negotiables, metric, False))
            prev_pct = (prev_count / len(previous) * 100) if previous else 0
        else:
            prev_pct = cur_pct

        change = cur_pct - prev_pct
        if change > 10:
            direction = "up"
        elif change < -10:
            direction = "down"
        else:
            direction = "stable"

        trends[metric] = {
            "current_pct": cur_pct,
            "previous_pct": prev_pct,
            "change": change,
            "direction": direction,
        }

    return trends


def format_metric_dashboard(
    checkins_7d: List[DailyCheckIn],
    checkins_30d: List[DailyCheckIn],
) -> str:
    """
    Build a comprehensive per-metric dashboard string (HTML) for Telegram.

    Sections:
    1. 7-day completion bar for each Tier 1 metric
    2. 7-day vs previous-7-day trend arrows
    3. 30-day completion rates
    4. Per-metric streaks (from 30-day data)

    Returns an HTML-formatted string ready for Telegram parse_mode='HTML'.
    """
    tier1_7d = _calculate_tier1_stats(checkins_7d) if checkins_7d else {}
    tier1_30d = _calculate_tier1_stats(checkins_30d) if checkins_30d else {}
    trends_7d = calculate_metric_trends(checkins_30d, days=7) if len(checkins_30d) >= 7 else {}
    streaks = calculate_metric_streaks(checkins_30d) if checkins_30d else {}

    parts = ["<b>📊 Metrics Dashboard</b>\n"]

    # Section 1: 7-day snapshot
    parts.append("<b>Last 7 Days:</b>")
    if not checkins_7d:
        parts.append("  No check-ins recorded.\n")
    else:
        for metric in TIER1_METRICS:
            emoji = METRIC_EMOJIS[metric]
            label = METRIC_LABELS[metric]
            stats = tier1_7d.get(metric, {})
            pct = stats.get("pct", 0)
            days_done = stats.get("days", 0)
            total = stats.get("total", 0)

            bar = _pct_bar(pct)
            trend_info = trends_7d.get(metric, {})
            arrow = _direction_arrow(trend_info.get("direction", "stable"))
            change = trend_info.get("change", 0)
            change_str = f"+{change:.0f}%" if change >= 0 else f"{change:.0f}%"

            parts.append(
                f"  {emoji} {label}: {bar} {pct:.0f}% ({days_done}/{total}) {arrow}{change_str}"
            )
        parts.append("")

    # Section 2: 30-day overview
    parts.append("<b>Last 30 Days:</b>")
    if not checkins_30d:
        parts.append("  No data.\n")
    else:
        for metric in TIER1_METRICS:
            emoji = METRIC_EMOJIS[metric]
            label = METRIC_LABELS[metric]
            stats = tier1_30d.get(metric, {})
            pct = stats.get("pct", 0)
            days_done = stats.get("days", 0)
            total = stats.get("total", 0)
            parts.append(f"  {emoji} {label}: {pct:.0f}% ({days_done}/{total})")
        parts.append("")

    # Section 3: Per-metric streaks
    parts.append("<b>Current Streaks:</b>")
    for metric in TIER1_METRICS:
        emoji = METRIC_EMOJIS[metric]
        label = METRIC_LABELS[metric]
        streak_val = streaks.get(metric, 0)
        if streak_val > 0:
            parts.append(f"  {emoji} {label}: {streak_val} day{'s' if streak_val != 1 else ''}")
        else:
            parts.append(f"  {emoji} {label}: ---")

    return "\n".join(parts)


def format_status_tier1_breakdown(checkins_7d: List[DailyCheckIn]) -> str:
    """
    Compact Tier 1 breakdown section for the /status command.

    Shows a single-line per metric: emoji + label + completion fraction.
    Designed to be appended to the existing status message.
    """
    if not checkins_7d:
        return ""

    tier1 = _calculate_tier1_stats(checkins_7d)
    lines = ["<b>Tier 1 Breakdown (7d):</b>"]
    for metric in TIER1_METRICS:
        emoji = METRIC_EMOJIS[metric]
        label = METRIC_LABELS[metric]
        stats = tier1.get(metric, {})
        pct = stats.get("pct", 0)
        days_done = stats.get("days", 0)
        total = stats.get("total", 0)
        lines.append(f"  {emoji} {label}: {days_done}/{total} ({pct:.0f}%)")
    return "\n".join(lines)


def _pct_bar(pct: float, width: int = 5) -> str:
    """Render a tiny text progress bar: [███░░] style."""
    filled = round(pct / 100 * width)
    empty = width - filled
    return "[" + "█" * filled + "░" * empty + "]"


def _direction_arrow(direction: str) -> str:
    if direction == "up":
        return "↗️"
    elif direction == "down":
        return "↘️"
    return "→"


# ===== P3.2: Mood & Energy Analytics =====

def calculate_mood_energy_stats(checkins: List[DailyCheckIn]) -> Dict[str, Any]:
    """
    Calculate mood and energy statistics from check-ins.

    Returns averages, trends, and correlation signals.
    """
    energy_ratings = [
        c.responses.energy_rating for c in checkins
        if c.responses.energy_rating is not None
    ]
    mood_ratings = [
        c.responses.mood_rating for c in checkins
        if c.responses.mood_rating is not None
    ]

    if not energy_ratings or not mood_ratings:
        return {"has_data": False}

    return {
        "has_data": True,
        "energy": {
            "avg": mean(energy_ratings),
            "min": min(energy_ratings),
            "max": max(energy_ratings),
            "count": len(energy_ratings),
        },
        "mood": {
            "avg": mean(mood_ratings),
            "min": min(mood_ratings),
            "max": max(mood_ratings),
            "count": len(mood_ratings),
        },
    }


def calculate_mood_correlations(checkins: List[DailyCheckIn]) -> Dict[str, Any]:
    """
    Calculate Pearson correlations between habits and mood/energy.

    Returns correlation coefficients and best combination insights.
    """
    from statistics import correlation

    # Filter check-ins that have both mood and energy data
    valid = [
        c for c in checkins
        if c.responses.energy_rating is not None
        and c.responses.mood_rating is not None
    ]

    if len(valid) < 5:
        return {"has_data": False, "reason": "Need at least 5 check-ins with mood/energy data"}

    result = {"has_data": True, "n": len(valid)}

    def _safe_correlation(x, y):
        try:
            return correlation(x, y)
        except Exception:
            return None

    # Sleep hours → mood correlation
    sleep_mood_pairs = [
        (c.tier1_non_negotiables.sleep_hours, c.responses.mood_rating)
        for c in valid
        if c.tier1_non_negotiables.sleep_hours is not None
    ]
    if len(sleep_mood_pairs) >= 5:
        sleep_hours, moods = zip(*sleep_mood_pairs)
        result["sleep_mood_correlation"] = _safe_correlation(sleep_hours, moods)

    # Sleep hours → energy correlation
    sleep_energy_pairs = [
        (c.tier1_non_negotiables.sleep_hours, c.responses.energy_rating)
        for c in valid
        if c.tier1_non_negotiables.sleep_hours is not None
    ]
    if len(sleep_energy_pairs) >= 5:
        sleep_hours, energies = zip(*sleep_energy_pairs)
        result["sleep_energy_correlation"] = _safe_correlation(sleep_hours, energies)

    # Training → energy correlation (training is boolean, use point-biserial approximation)
    training_energy_pairs = [
        (1.0 if c.tier1_non_negotiables.training else 0.0, c.responses.energy_rating)
        for c in valid
    ]
    if len(training_energy_pairs) >= 5:
        training_vals, energies = zip(*training_energy_pairs)
        result["training_energy_correlation"] = _safe_correlation(training_vals, energies)

    # Deep work hours → mood correlation
    dw_mood_pairs = [
        (c.tier1_non_negotiables.deep_work_hours, c.responses.mood_rating)
        for c in valid
        if c.tier1_non_negotiables.deep_work_hours is not None
    ]
    if len(dw_mood_pairs) >= 5:
        dw_hours, moods = zip(*dw_mood_pairs)
        result["deep_work_mood_correlation"] = _safe_correlation(dw_hours, moods)

    # Best combination: find highest mood days and see what they have in common
    sorted_by_mood = sorted(valid, key=lambda c: c.responses.mood_rating or 0, reverse=True)
    top_third = sorted_by_mood[:max(1, len(sorted_by_mood) // 3)]

    best_combo = []
    if all(c.tier1_non_negotiables.sleep for c in top_third):
        best_combo.append("sleep")
    if all(c.tier1_non_negotiables.training for c in top_third):
        best_combo.append("training")
    if all(c.tier1_non_negotiables.deep_work for c in top_third):
        best_combo.append("deep_work")

    result["best_combination"] = best_combo
    result["top_mood_avg"] = mean(c.responses.mood_rating for c in top_third)

    return result


def format_mood_energy_summary(checkins: List[DailyCheckIn]) -> str:
    """Format mood/energy stats for display in /metrics or reports."""
    stats = calculate_mood_energy_stats(checkins)
    if not stats.get("has_data"):
        return ""

    lines = [
        "",
        "<b>🧠 Mood & Energy (7d):</b>",
        f"  ⚡ Avg Energy: {stats['energy']['avg']:.1f}/10",
        f"  😊 Avg Mood: {stats['mood']['avg']:.1f}/10",
    ]
    return "\n".join(lines)


def calculate_partner_weekly_performance(checkins: List[DailyCheckIn]) -> Dict[str, Any]:
    """
    Calculate 7-day habit performance metrics to identify strongest and weakest areas
    for the partner weekly status report.
    
    Returns structured dict with:
    - has_data: bool
    - checkin_count: int
    - avg_compliance: float
    - habits: dict of habit stats
    - strongest: list of (habit_name, habit_stat)
    - weakest: list of (habit_name, habit_stat)
    - tasks_stat: optional dict of task stats
    """
    if not checkins:
        return {"has_data": False, "checkin_count": 0}

    total = len(checkins)
    valid_scores = [c.compliance_score for c in checkins if c.compliance_score is not None]
    avg_compliance = mean(valid_scores) if valid_scores else 0.0

    habits = {}

    # 1. Sleep
    sleep_met_count = sum(1 for c in checkins if c.tier1_non_negotiables.sleep_met)
    sleep_hours_list = [
        c.tier1_non_negotiables.sleep_hours
        for c in checkins
        if c.tier1_non_negotiables.sleep_hours is not None
    ]
    avg_sleep = mean(sleep_hours_list) if sleep_hours_list else None
    habits["Sleep"] = {
        "pct": (sleep_met_count / total) * 100,
        "detail": f"avg {avg_sleep:.1f}h" if avg_sleep is not None else f"{sleep_met_count}/{total} days",
        "key": "sleep"
    }

    # 2. Training
    training_done_count = sum(
        1 for c in checkins
        if (c.tier1_non_negotiables.training_done or c.tier1_non_negotiables.is_rest_day)
    )
    habits["Training"] = {
        "pct": (training_done_count / total) * 100,
        "detail": f"{training_done_count}/{total} sessions/rests",
        "key": "training"
    }

    # 3. Deep Work
    dw_met_count = sum(1 for c in checkins if c.tier1_non_negotiables.deep_work_met)
    dw_hours_list = [
        c.tier1_non_negotiables.deep_work_hours
        for c in checkins
        if c.tier1_non_negotiables.deep_work_hours is not None
    ]
    avg_dw = mean(dw_hours_list) if dw_hours_list else None
    habits["Deep Work"] = {
        "pct": (dw_met_count / total) * 100,
        "detail": f"avg {avg_dw:.1f}h vs 2.0h target" if avg_dw is not None else f"{dw_met_count}/{total} days",
        "key": "deep_work"
    }

    # 4. Skill Building
    sb_met_count = sum(1 for c in checkins if c.tier1_non_negotiables.skill_building_met)
    sb_hours_list = [
        c.tier1_non_negotiables.skill_building_hours
        for c in checkins
        if c.tier1_non_negotiables.skill_building_hours is not None
    ]
    avg_sb = mean(sb_hours_list) if sb_hours_list else None
    habits["Skill Building"] = {
        "pct": (sb_met_count / total) * 100,
        "detail": f"avg {avg_sb:.1f}h vs 2.0h target" if avg_sb is not None else f"{sb_met_count}/{total} days",
        "key": "skill_building"
    }

    # 5. Zero Porn
    zp_count = sum(1 for c in checkins if c.tier1_non_negotiables.zero_porn)
    habits["Zero Porn"] = {
        "pct": (zp_count / total) * 100,
        "detail": f"{zp_count}/{total} days clean",
        "key": "zero_porn"
    }

    # 6. Boundaries
    b_count = sum(1 for c in checkins if c.tier1_non_negotiables.boundaries)
    habits["Boundaries"] = {
        "pct": (b_count / total) * 100,
        "detail": f"{b_count}/{total} days held",
        "key": "boundaries"
    }

    # 7. Tasks / To-Dos
    all_tasks = []
    for c in checkins:
        if c.committed_tasks:
            all_tasks.extend(c.committed_tasks)

    tasks_stat = None
    if all_tasks:
        tasks_completed = sum(1 for t in all_tasks if t.completed)
        tasks_stat = {
            "completed": tasks_completed,
            "total": len(all_tasks),
            "pct": (tasks_completed / len(all_tasks)) * 100
        }

    # Sort habits by percentage descending
    sorted_habits = sorted(habits.items(), key=lambda x: x[1]["pct"], reverse=True)

    # Strongest = top 2 habits
    strongest = sorted_habits[:2]
    # Weakest = bottom 2 habits
    weakest = sorted_habits[-2:]

    return {
        "has_data": True,
        "checkin_count": total,
        "avg_compliance": avg_compliance,
        "habits": habits,
        "strongest": strongest,
        "weakest": weakest,
        "tasks_stat": tasks_stat
    }


def calculate_progress_hub_stats(user_id: str, window_key: str = "30d") -> Dict[str, Any]:
    """
    Calculate unified executive dashboard metrics for /progress hub.
    Supports windows: '7d', '30d', 'ytd', 'all'.
    """
    try:
        user = firestore_service.get_user(user_id)
        if not user:
            return {"has_data": False, "error": "User not found"}

        now = datetime.utcnow()
        if window_key == "7d":
            days = 7
            period_label = "Last 7 Days"
        elif window_key == "30d":
            days = 30
            period_label = "Last 30 Days"
        elif window_key == "ytd":
            jan1 = datetime(now.year, 1, 1)
            days = max(1, (now - jan1).days + 1)
            period_label = f"Year-To-Date ({now.year})"
        elif window_key == "all":
            days = 3650
            period_label = "All-Time"
        else:
            days = 30
            period_label = "Last 30 Days"

        checkins = firestore_service.get_recent_checkins(user_id, days=days)
        if not checkins:
            return {
                "has_data": False,
                "period_label": period_label,
                "window_key": window_key,
                "user": user,
                "streaks": {
                    "current": user.streaks.current_streak if user.streaks else 0,
                    "longest": user.streaks.longest_streak if user.streaks else 0,
                    "total": user.streaks.total_checkins if user.streaks else 0,
                },
                "shields": {
                    "available": user.streak_shields.available if user.streak_shields else 0,
                    "total": user.streak_shields.total if user.streak_shields else 3,
                },
                "achievements_count": len(user.achievements or []),
                "say_do_ratio": getattr(user.ai_profile_memory, 'say_do_ratio', 0.0) if hasattr(user, 'ai_profile_memory') and user.ai_profile_memory else 0.0,
            }

        # Checkin scores
        scores = [c.compliance_score for c in checkins if c.compliance_score is not None]
        avg_compliance = mean(scores) if scores else 0.0

        # Trend (compare first half vs second half)
        if len(scores) >= 6:
            mid = len(scores) // 2
            first_half = mean(scores[:mid])
            second_half = mean(scores[mid:])
            diff = second_half - first_half
            if diff >= 5:
                trend = f"↗️ +{diff:.0f}%"
            elif diff <= -5:
                trend = f"↘️ {diff:.0f}%"
            else:
                trend = "→ Stable"
        else:
            trend = "→ Stable"

        tier1_stats = _calculate_tier1_stats(checkins)

        # Say-Do ratio
        say_do = 0.0
        if hasattr(user, 'ai_profile_memory') and user.ai_profile_memory and user.ai_profile_memory.say_do_ratio:
            say_do = user.ai_profile_memory.say_do_ratio
        else:
            # Calculate from committed tasks if available
            all_tasks = [t for c in checkins if c.committed_tasks for t in c.committed_tasks]
            if all_tasks:
                completed = sum(1 for t in all_tasks if t.completed)
                say_do = (completed / len(all_tasks)) * 100

        # Date range string
        sorted_checkins = sorted(checkins, key=lambda c: c.date)
        date_range_str = f"{sorted_checkins[0].date} to {sorted_checkins[-1].date}"

        return {
            "has_data": True,
            "period_label": period_label,
            "window_key": window_key,
            "date_range": date_range_str,
            "checkin_count": len(checkins),
            "days_in_window": days if days <= 365 else len(checkins),
            "user": user,
            "compliance": {
                "average": avg_compliance,
                "trend": trend,
                "max": max(scores) if scores else 0,
                "min": min(scores) if scores else 0,
            },
            "streaks": {
                "current": user.streaks.current_streak if user.streaks else 0,
                "longest": user.streaks.longest_streak if user.streaks else 0,
                "total": user.streaks.total_checkins if user.streaks else 0,
            },
            "shields": {
                "available": user.streak_shields.available if user.streak_shields else 0,
                "total": user.streak_shields.total if user.streak_shields else 3,
            },
            "tier1": tier1_stats,
            "achievements_count": len(user.achievements or []),
            "say_do_ratio": say_do,
        }
    except Exception as e:
        logger.error(f"❌ Error calculating progress hub stats: {e}", exc_info=True)
        return {"has_data": False, "error": str(e)}


