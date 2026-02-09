"""
Stats Commands - Quick Statistics Commands
==========================================

Phase 3E: /weekly, /monthly, /yearly command handlers.

<b>Purpose:</b>
Provide instant access to statistics without opening dashboard:
- /weekly: Last 7 days summary
- /monthly: Last 30 days summary
- /yearly: Year-to-date summary

<b>User Experience:</b>
One command → Formatted stats message in Telegram
No context switching, no dashboard loading

<b>Implementation:</b>
1. Parse command (weekly/monthly/yearly)
2. Call analytics_service to calculate stats
3. Format stats into Markdown message
4. Send to user via Telegram

Key Concepts:
-------------
1. <b>Markdown Formatting</b>: Use Telegram's Markdown for readability
   - <b>Bold</b> for headers
   - • Bullets for lists
   - Emojis for visual appeal

2. <b>Information Hierarchy</b>: Most important stats first
   - Compliance average (primary metric)
   - Streaks (motivation)
   - Tier 1 breakdown (actionable insights)
   - Patterns (warnings)

3. <b>Actionable Insights</b>: Not just numbers, but meaning
   - "↗️ +5% improving" vs just "89%"
   - "Top 20% of users" vs just raw percentile
   - "Focus on deep work" vs just "2/7 days"
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from src.services.analytics_service import (
    calculate_weekly_stats,
    calculate_monthly_stats,
    calculate_yearly_stats
)
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


# ===== Command Handlers =====

async def weekly_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle /weekly command - Last 7 days summary.
    
    <b>What It Shows:</b>
    - Compliance average and trend
    - Current streak and check-in rate
    - Tier 1 performance breakdown
    - Pattern detections
    
    <b>User Experience:</b>
    Simple command → Instant stats → Back to chat
    
    <b>Error Handling:</b>
    - No user profile → Prompt to use /start
    - No check-ins → Show helpful message
    - Calculation error → Show fallback message
    """
    user_id = str(update.effective_user.id)
    
    logger.info(f"📊 /weekly command from user {user_id}")
    
    try:
        # Check if user exists
        user = firestore_service.get_user(user_id)
        if not user:
            await update.message.reply_text(
                "❌ Please use /start first to create your profile."
            )
            return
        
        # Calculate weekly stats
        stats = calculate_weekly_stats(user_id)
        
        # Check if data available
        if not stats.get("has_data", False):
            error_msg = stats.get("error", "No check-ins found")
            await update.message.reply_text(
                f"📊 <b>Last 7 Days</b>\n\n"
                f"No check-in data available yet.\n\n"
                f"Complete your first check-in with /checkin to start tracking!",
                parse_mode='HTML'
            )
            logger.info(f"⚠️ No weekly data for user {user_id}: {error_msg}")
            return
        
        # Format and send message
        message = format_weekly_summary(stats)
        await update.message.reply_text(message, parse_mode='HTML')
        
        logger.info(f"✅ Weekly stats sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /weekly command failed for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Sorry, I couldn't calculate your weekly stats right now.\n\n"
            "Try again in a moment or use /status for basic stats.",
            parse_mode='HTML'
        )


async def monthly_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle /monthly command - Last 30 days summary.
    
    <b>What It Shows:</b>
    - Compliance average with weekly breakdown
    - Best/worst week analysis
    - Tier 1 performance averages
    - Achievement unlocks
    - Pattern summary
    - Social proof (percentile)
    
    <b>Richer Than Weekly:</b>
    - Week-by-week comparison
    - Achievement tracking
    - Percentile ranking
    """
    user_id = str(update.effective_user.id)
    
    logger.info(f"📊 /monthly command from user {user_id}")
    
    try:
        # Check if user exists
        user = firestore_service.get_user(user_id)
        if not user:
            await update.message.reply_text(
                "❌ Please use /start first to create your profile."
            )
            return
        
        # Calculate monthly stats
        stats = calculate_monthly_stats(user_id)
        
        # Check if data available
        if not stats.get("has_data", False):
            error_msg = stats.get("error", "No check-ins found")
            await update.message.reply_text(
                f"📊 <b>Last 30 Days</b>\n\n"
                f"No check-in data available yet.\n\n"
                f"Complete more check-ins to see monthly trends!",
                parse_mode='HTML'
            )
            logger.info(f"⚠️ No monthly data for user {user_id}: {error_msg}")
            return
        
        # Format and send message
        message = format_monthly_summary(stats)
        await update.message.reply_text(message, parse_mode='HTML')
        
        logger.info(f"✅ Monthly stats sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /monthly command failed for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Sorry, I couldn't calculate your monthly stats right now.\n\n"
            "Try again in a moment or use /status for basic stats.",
            parse_mode='HTML'
        )


async def yearly_command(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Handle /yearly command - Year-to-date summary.
    
    <b>What It Shows:</b>
    - Overall compliance and check-in rate
    - Current vs longest streak
    - Monthly breakdown (Jan, Feb, Mar...)
    - Total achievements
    - Career progress (skill building)
    - Pattern summary
    
    <b>Big Picture View:</b>
    - Shows progress over entire year
    - Highlights career goal alignment
    - Motivates with achievements count
    """
    user_id = str(update.effective_user.id)
    
    logger.info(f"📊 /yearly command from user {user_id}")
    
    try:
        # Check if user exists
        user = firestore_service.get_user(user_id)
        if not user:
            await update.message.reply_text(
                "❌ Please use /start first to create your profile."
            )
            return
        
        # Calculate yearly stats
        stats = calculate_yearly_stats(user_id)
        
        # Check if data available
        if not stats.get("has_data", False):
            error_msg = stats.get("error", "No check-ins found")
            await update.message.reply_text(
                f"📊 <b>2026 Year to Date</b>\n\n"
                f"No check-in data available yet.\n\n"
                f"Complete more check-ins to see yearly trends!",
                parse_mode='HTML'
            )
            logger.info(f"⚠️ No yearly data for user {user_id}: {error_msg}")
            return
        
        # Format and send message
        message = format_yearly_summary(stats)
        await update.message.reply_text(message, parse_mode='HTML')
        
        logger.info(f"✅ Yearly stats sent to user {user_id}")
        
    except Exception as e:
        logger.error(f"❌ /yearly command failed for user {user_id}: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Sorry, I couldn't calculate your yearly stats right now.\n\n"
            "Try again in a moment or use /status for basic stats.",
            parse_mode='HTML'
        )


# ===== Formatting Functions =====

def format_weekly_summary(stats: dict) -> str:
    """
    Format weekly stats into Telegram-friendly Markdown message.
    
    <b>Structure:</b>
    1. Header with date range
    2. Compliance section (avg + trend)
    3. Streaks section (current + check-in rate)
    4. Tier 1 performance (detailed breakdown)
    5. Patterns section
    6. Encouragement
    
    <b>Design Principles:</b>
    - Most important info first (compliance, streak)
    - Use emojis for visual scanning
    - Group related stats together
    - End with encouragement
    
    Args:
        stats: Dictionary from calculate_weekly_stats()
        
    Returns:
        Formatted Markdown string
    """
    compliance = stats["compliance"]
    streaks = stats["streaks"]
    tier1 = stats["tier1"]
    patterns = stats["patterns"]
    
    # Build message parts
    parts = []
    
    # Header
    parts.append(f"📊 <b>{stats['period']}</b> ({stats['date_range']})\n")
    
    # Compliance section
    parts.append("<b>Compliance:</b>")
    parts.append(f"Average: {compliance['average']:.0f}%")
    parts.append(f"Trend: {compliance['trend']}\n")
    
    # Streaks section
    parts.append("<b>Streaks:</b>")
    parts.append(f"Current: {streaks['current']} days 🔥")
    parts.append(f"Check-ins: {streaks['checkin_rate']} ({streaks['completion_pct']:.0f}%)\n")
    
    # Tier 1 performance
    parts.append("<b>Tier 1 Performance:</b>")
    parts.append(f"• Sleep: {tier1['sleep']['days']}/{tier1['sleep']['total']} days ({tier1['sleep']['avg_hours']:.1f} hrs avg)")
    parts.append(f"• Training: {tier1['training']['days']}/{tier1['training']['total']} days")
    parts.append(f"• Deep Work: {tier1['deep_work']['days']}/{tier1['deep_work']['total']} days ({tier1['deep_work']['avg_hours']:.1f} hrs avg)")
    parts.append(f"• Skill Building: {tier1['skill_building']['days']}/{tier1['skill_building']['total']} days")
    
    # Zero porn status (only show if perfect or needs attention)
    if tier1['zero_porn']['pct'] == 100:
        parts.append(f"• Zero Porn: {tier1['zero_porn']['days']}/{tier1['zero_porn']['total']} days ✅")
    else:
        parts.append(f"• Zero Porn: {tier1['zero_porn']['days']}/{tier1['zero_porn']['total']} days ⚠️")
    
    parts.append(f"• Boundaries: {tier1['boundaries']['days']}/{tier1['boundaries']['total']} days\n")
    
    # Patterns
    parts.append(f"<b>Patterns:</b> {patterns['message']}\n")
    
    # Encouragement based on performance
    if compliance['average'] >= 90:
        parts.append("Outstanding week! Keep this momentum going! 💪")
    elif compliance['average'] >= 80:
        parts.append("Strong week! You're building solid habits. 🎯")
    elif compliance['average'] >= 70:
        parts.append("Good progress! Focus on consistency. 📈")
    else:
        parts.append("Every week is a fresh start. You've got this! 💪")
    
    return "\n".join(parts)


def format_monthly_summary(stats: dict) -> str:
    """
    Format monthly stats into Telegram-friendly Markdown message.
    
    <b>Additional Elements vs Weekly:</b>
    - Week-by-week comparison
    - Achievement tracking
    - Social proof (percentile)
    
    Args:
        stats: Dictionary from calculate_monthly_stats()
        
    Returns:
        Formatted Markdown string
    """
    compliance = stats["compliance"]
    streaks = stats["streaks"]
    tier1 = stats["tier1"]
    achievements = stats["achievements"]
    patterns = stats["patterns"]
    social_proof = stats["social_proof"]
    
    # Build message parts
    parts = []
    
    # Header
    parts.append(f"📊 <b>{stats['period']}</b> ({stats['date_range']})\n")
    
    # Compliance section with weekly breakdown
    parts.append("<b>Compliance:</b>")
    parts.append(f"Average: {compliance['average']:.0f}%")
    parts.append(f"Best week: {compliance['best_week']}")
    parts.append(f"Worst week: {compliance['worst_week']}\n")
    
    # Streaks section
    parts.append("<b>Streaks:</b>")
    parts.append(f"Current: {streaks['current']} days 🔥")
    parts.append(f"Longest this month: {streaks['longest_this_month']} days")
    parts.append(f"Check-ins: {streaks['checkin_rate']} ({streaks['completion_pct']:.0f}%)\n")
    
    # Tier 1 averages
    parts.append("<b>Tier 1 Averages:</b>")
    parts.append(f"• Sleep: {tier1['sleep']['avg_hours']:.1f} hrs (target: {tier1['sleep']['target']}+)")
    parts.append(f"• Training: {tier1['training']['pct']:.0f}% days ({tier1['training']['days']}/{tier1['training']['total']})")
    parts.append(f"• Deep Work: {tier1['deep_work']['avg_hours']:.1f} hrs (target: {tier1['deep_work']['target']}+)")
    parts.append(f"• Skill Building: {tier1['skill_building']['avg_hours']:.1f} hrs")
    
    # Zero porn status
    if tier1['zero_porn']['pct'] == 100:
        parts.append(f"• Zero Porn: 100% ✅")
    else:
        parts.append(f"• Zero Porn: {tier1['zero_porn']['pct']:.0f}% ({tier1['zero_porn']['days']}/{tier1['zero_porn']['total']} days)")
    
    parts.append(f"• Boundaries: {tier1['boundaries']['pct']:.0f}% days\n")
    
    # Achievements
    if achievements['count'] > 0:
        parts.append(f"<b>Achievements Unlocked:</b> {achievements['count']}")
        for achievement in achievements['list']:
            parts.append(f"🏆 {achievement}")
        parts.append("")  # Empty line
    
    # Patterns
    parts.append(f"<b>Patterns Detected:</b> {patterns['count']}")
    if patterns['count'] > 0:
        parts.append(f"⚠️ {patterns['message']}\n")
    else:
        parts.append(f"{patterns['message']}\n")
    
    # Social proof
    parts.append(social_proof['message'])
    
    return "\n".join(parts)


def format_yearly_summary(stats: dict) -> str:
    """
    Format yearly stats into Telegram-friendly Markdown message.
    
    <b>Yearly Specifics:</b>
    - Overview stats (days tracked, completion %)
    - Monthly breakdown
    - Career progress tracking
    - Total achievements count
    
    Args:
        stats: Dictionary from calculate_yearly_stats()
        
    Returns:
        Formatted Markdown string
    """
    overview = stats["overview"]
    streaks = stats["streaks"]
    monthly_breakdown = stats["monthly_breakdown"]
    achievements = stats["achievements"]
    patterns = stats["patterns"]
    career = stats["career_progress"]
    
    # Build message parts
    parts = []
    
    # Header
    parts.append(f"📊 <b>{stats['period']}</b> ({stats['date_range']})\n")
    
    # Overview
    parts.append("<b>Overview:</b>")
    parts.append(f"Days tracked: {overview['days_tracked']}/{overview['total_days']} ({overview['completion_pct']:.0f}%)")
    parts.append(f"Average compliance: {overview['avg_compliance']:.0f}%\n")
    
    # Streaks
    parts.append("<b>Streaks:</b>")
    parts.append(f"Current: {streaks['current']} days 🔥")
    parts.append(f"Longest this year: {streaks['longest_this_year']} days")
    parts.append(f"Total check-ins: {streaks['total_checkins']}\n")
    
    # Monthly breakdown
    parts.append("<b>Monthly Breakdown:</b>")
    for month_data in monthly_breakdown:
        parts.append(f"{month_data['month']}: {month_data['days']}/{month_data.get('total_days', 31)} days, {month_data['avg_compliance']} avg")
    parts.append("")  # Empty line
    
    # Achievements
    parts.append(f"<b>Achievements:</b> {achievements['total']} {achievements['message']}\n")
    
    # Patterns
    parts.append(f"<b>Patterns:</b> {patterns['total']} {patterns['message']}\n")
    
    # Career progress
    parts.append("<b>Career Progress:</b>")
    parts.append(f"Skill building: {career['consistency_pct']:.0f}% days ({career['skill_building_days']} days)")
    
    # Career mode context
    if career['career_mode'] == 'skill_building':
        parts.append("Mode: 📚 Skill Building")
    elif career['career_mode'] == 'job_searching':
        parts.append("Mode: 💼 Job Searching")
    elif career['career_mode'] == 'employed':
        parts.append("Mode: 🎯 Employed")
    
    parts.append(f"\nOn track for {career['target_date']} goals! ({career['target_salary']}) 🎯\n")
    
    # Action item
    parts.append("View detailed breakdown: /dashboard")
    
    return "\n".join(parts)


# ===== Helper Functions =====

def get_emoji_for_trend(trend: str) -> str:
    """
    Get emoji for trend indicator.
    
    Args:
        trend: "improving", "declining", or "stable"
        
    Returns:
        Emoji string
    """
    trend_emojis = {
        "improving": "↗️",
        "declining": "↘️",
        "stable": "→"
    }
    return trend_emojis.get(trend, "→")


def get_encouragement(compliance: float) -> str:
    """
    Get contextual encouragement based on compliance score.
    
    <b>Psychology:</b>
    - High performers: Maintain momentum
    - Mid performers: Focus on consistency
    - Low performers: Fresh start mindset
    
    Args:
        compliance: Average compliance score (0-100)
        
    Returns:
        Encouragement string
    """
    if compliance >= 95:
        return "Exceptional performance! You're setting the standard. 🌟"
    elif compliance >= 90:
        return "Outstanding! Maintain this momentum. 💪"
    elif compliance >= 85:
        return "Strong work! You're in the top tier. 🎯"
    elif compliance >= 80:
        return "Solid progress! Keep building these habits. 📈"
    elif compliance >= 70:
        return "Good effort! Focus on consistency. 💪"
    elif compliance >= 60:
        return "Making progress! Small improvements add up. 📈"
    else:
        return "Every day is a fresh start. You've got this! 💪"
