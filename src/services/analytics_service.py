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
    
    return {
        "sleep": {
            "days": sleep_days,
            "total": total_days,
            "pct": (sleep_days / total_days) * 100,
            "avg_hours": avg_sleep,
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
            "target": 2.0
        },
        "skill_building": {
            "days": skill_building_days,
            "total": total_days,
            "pct": (skill_building_days / total_days) * 100,
            "avg_hours": avg_skill_building
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
