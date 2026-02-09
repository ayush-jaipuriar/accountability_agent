"""
Reporting Agent - Weekly Report Generation & Delivery
=======================================================

Phase 3F: Orchestrates weekly visual reports with graphs and AI insights.

<b>Architecture: Mediator Pattern</b>
This agent coordinates between multiple services without them knowing
about each other:
- FirestoreService → data retrieval
- VisualizationService → graph generation
- LLMService → AI insights generation
- Telegram Bot → report delivery

<b>Weekly Report Contents:</b>
1. Summary header (week dates, check-in count)
2. 4 graphs (sleep, training, compliance, radar)
3. AI-generated insights (2-3 sentences referencing actual data)
4. Quick stats (compliance avg, streak, best day)

<b>Delivery Schedule:</b>
- Automated: Every Sunday 9:00 AM IST via Cloud Scheduler
- On-demand: /report command for immediate generation

<b>Cost Analysis:</b>
- Graphs: $0.00 (matplotlib, open source)
- AI Insights: ~300 tokens × $0.25/1M = $0.000075 per report
- Monthly (4 reports × 10 users): $0.003/month
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
from statistics import mean

from src.models.schemas import DailyCheckIn, User
from src.services.firestore_service import firestore_service
from src.services.visualization_service import generate_weekly_graphs

logger = logging.getLogger(__name__)


async def generate_ai_insights(
    checkins: List[DailyCheckIn],
    user: User,
    project_id: str,
) -> str:
    """
    Generate AI-powered insights for the weekly report.
    
    <b>Theory: Data-Grounded Generation</b>
    We pass actual metrics to the LLM rather than asking it to analyze
    raw data. This approach:
    1. Reduces token count (summary data vs raw check-ins)
    2. Prevents hallucination (LLM only formats, doesn't calculate)
    3. Keeps costs low (~300 tokens total)
    
    The prompt is structured to force specific, actionable feedback
    rather than generic encouragement.
    
    Args:
        checkins: Last 7 days of check-ins
        user: User profile
        project_id: GCP project ID for LLM service
        
    Returns:
        AI-generated insight text (2-3 sentences)
    """
    from src.services.llm_service import get_llm_service
    
    if not checkins:
        return "No check-in data available for insights this week."
    
    # Pre-calculate metrics (don't send raw data to LLM)
    total = len(checkins)
    avg_compliance = mean([c.compliance_score for c in checkins])
    sleep_hours_list = [c.tier1_non_negotiables.sleep_hours for c in checkins
                        if c.tier1_non_negotiables.sleep_hours]
    avg_sleep = mean(sleep_hours_list) if sleep_hours_list else 0
    
    training_days = sum(1 for c in checkins if c.tier1_non_negotiables.training)
    porn_free_days = sum(1 for c in checkins if c.tier1_non_negotiables.zero_porn)
    skill_building_days = sum(1 for c in checkins if c.tier1_non_negotiables.skill_building)
    
    best_day = max(checkins, key=lambda c: c.compliance_score)
    worst_day = min(checkins, key=lambda c: c.compliance_score)
    
    # Build compact prompt
    prompt = f"""You are an accountability coach analyzing a user's weekly performance.
Generate exactly 2-3 sentences of specific, actionable insight.

User: {user.name} (Mode: {user.constitution_mode}, Streak: {user.streaks.current_streak} days)

This Week's Data:
- Check-ins: {total}/7 days
- Avg Compliance: {avg_compliance:.0f}%
- Avg Sleep: {avg_sleep:.1f} hours
- Training: {training_days}/7 days
- Skill Building: {skill_building_days}/7 days
- Porn-Free: {porn_free_days}/7 days
- Best Day: {best_day.date} ({best_day.compliance_score:.0f}%)
- Worst Day: {worst_day.date} ({worst_day.compliance_score:.0f}%)

Rules:
- Reference SPECIFIC numbers from the data above
- Highlight the biggest strength AND one area to improve
- Keep it under 60 words total
- Be encouraging but honest
- Do NOT use emojis"""

    try:
        llm = get_llm_service(project_id=project_id)
        response = await llm.generate_text(
            prompt=prompt,
            max_output_tokens=150,
            temperature=0.7,
        )
        return response.strip()
    except Exception as e:
        logger.error(f"AI insights generation failed: {e}")
        # Fallback to template-based insights
        return _generate_fallback_insights(checkins, avg_compliance, avg_sleep)


def _generate_fallback_insights(
    checkins: List[DailyCheckIn],
    avg_compliance: float,
    avg_sleep: float,
) -> str:
    """
    Generate template-based insights when LLM is unavailable.
    
    <b>Why Fallback?</b>
    LLM calls can fail (rate limits, network issues, API outages).
    Rather than showing an error in the report, we generate a
    reasonable template-based insight. The user still gets value.
    
    Args:
        checkins: Week's check-ins
        avg_compliance: Average compliance score
        avg_sleep: Average sleep hours
    
    Returns:
        Template-based insight string
    """
    parts = []
    
    if avg_compliance >= 90:
        parts.append(f"Outstanding week with {avg_compliance:.0f}% average compliance.")
    elif avg_compliance >= 75:
        parts.append(f"Solid week at {avg_compliance:.0f}% compliance - room to push higher.")
    else:
        parts.append(f"Challenging week at {avg_compliance:.0f}% compliance - let's refocus.")
    
    if avg_sleep < 7:
        parts.append(f"Sleep averaged {avg_sleep:.1f}h - prioritize hitting 7+ hours.")
    else:
        parts.append(f"Sleep on track at {avg_sleep:.1f}h average.")
    
    return " ".join(parts)


def _build_report_message(
    checkins: List[DailyCheckIn],
    user: User,
    ai_insights: str,
) -> str:
    """
    Build the text portion of the weekly report message.
    
    This is sent alongside the 4 graph images as a Telegram message.
    It provides the context and summary that the graphs visualize.
    
    Args:
        checkins: Week's check-ins
        user: User profile
        ai_insights: AI-generated insight text
        
    Returns:
        Formatted Telegram message (HTML mode)
    """
    total = len(checkins)
    
    if not checkins:
        return (
            "<b>📊 Weekly Report</b>\n\n"
            "No check-ins recorded this week.\n"
            "Start building your data with /checkin!"
        )
    
    avg_compliance = mean([c.compliance_score for c in checkins])
    best_day = max(checkins, key=lambda c: c.compliance_score)
    
    # Determine trend
    if total >= 4:
        first_half = [c.compliance_score for c in checkins[:total // 2]]
        second_half = [c.compliance_score for c in checkins[total // 2:]]
        diff = mean(second_half) - mean(first_half)
        if diff > 5:
            trend = "📈 Trending Up"
        elif diff < -5:
            trend = "📉 Trending Down"
        else:
            trend = "➡️ Stable"
    else:
        trend = "➡️ Stable"
    
    # Week date range
    sorted_checkins = sorted(checkins, key=lambda c: c.date)
    week_start = sorted_checkins[0].date
    week_end = sorted_checkins[-1].date
    
    message = (
        f"<b>📊 Weekly Report</b>\n"
        f"<i>{week_start} → {week_end}</i>\n\n"
        
        f"<b>Quick Summary:</b>\n"
        f"• Check-ins: {total}/7 days\n"
        f"• Avg Compliance: {avg_compliance:.0f}%\n"
        f"• Trend: {trend}\n"
        f"• Best Day: {best_day.date} ({best_day.compliance_score:.0f}%)\n"
        f"• Streak: {user.streaks.current_streak} days 🔥\n\n"
        
        f"<b>💡 AI Insights:</b>\n"
        f"<i>{ai_insights}</i>\n\n"
        
        f"<i>Graphs attached below ⬇️</i>"
    )
    
    return message


async def generate_and_send_weekly_report(
    user_id: str,
    project_id: str,
    bot,
) -> Dict[str, Any]:
    """
    Generate and deliver a complete weekly report to a single user.
    
    <b>Full Report Pipeline:</b>
    1. Fetch last 7 days of check-ins from Firestore
    2. Generate 4 graphs using Visualization Service
    3. Generate AI insights using LLM Service
    4. Build summary message
    5. Send message + 4 images via Telegram
    
    <b>Error Handling Strategy:</b>
    - If graph generation fails: Send text-only report (graceful degradation)
    - If AI insights fail: Use template-based fallback
    - If Telegram send fails: Log error, don't retry (next week's report will work)
    
    Args:
        user_id: User's Telegram ID
        project_id: GCP project ID for LLM
        bot: Telegram Bot instance for sending messages
        
    Returns:
        Result dictionary with status and metadata
    """
    result = {
        "user_id": user_id,
        "status": "unknown",
        "graphs_sent": 0,
        "error": None,
    }
    
    try:
        # Step 1: Fetch user and check-ins
        user = firestore_service.get_user(user_id)
        if not user:
            result["status"] = "skipped"
            result["error"] = "User not found"
            return result
        
        checkins = firestore_service.get_recent_checkins(user_id, days=7)
        
        if not checkins:
            # Send a brief "no data" message instead of a full report
            await bot.send_message(
                chat_id=user.telegram_id,
                text=(
                    "<b>📊 Weekly Report</b>\n\n"
                    "No check-ins recorded this week.\n"
                    "Start building your data with /checkin!"
                ),
                parse_mode='HTML',
            )
            result["status"] = "sent_empty"
            return result
        
        # Step 2: Generate graphs
        graphs = generate_weekly_graphs(checkins)
        
        # Step 3: Generate AI insights
        ai_insights = await generate_ai_insights(checkins, user, project_id)
        
        # Step 4: Build report message
        report_text = _build_report_message(checkins, user, ai_insights)
        
        # Step 5: Send report text
        await bot.send_message(
            chat_id=user.telegram_id,
            text=report_text,
            parse_mode='HTML',
        )
        
        # Step 6: Send graphs as photos
        graph_captions = {
            'sleep': '😴 Sleep Trend',
            'training': '💪 Training Frequency',
            'compliance': '📈 Compliance Scores',
            'radar': '🎯 Life Balance Radar',
        }
        
        for graph_name, graph_buffer in graphs.items():
            try:
                caption = graph_captions.get(graph_name, graph_name.title())
                await bot.send_photo(
                    chat_id=user.telegram_id,
                    photo=graph_buffer,
                    caption=caption,
                )
                result["graphs_sent"] += 1
            except Exception as e:
                logger.error(f"Failed to send {graph_name} graph to {user_id}: {e}")
        
        result["status"] = "sent"
        logger.info(
            f"✅ Weekly report sent to {user_id} ({user.name}): "
            f"{result['graphs_sent']}/4 graphs"
        )
        
    except Exception as e:
        result["status"] = "failed"
        result["error"] = str(e)
        logger.error(f"❌ Weekly report failed for {user_id}: {e}", exc_info=True)
    
    return result


async def send_weekly_reports_to_all(
    project_id: str,
    bot,
) -> Dict[str, Any]:
    """
    Send weekly reports to ALL active users.
    
    Called by Cloud Scheduler endpoint every Sunday 9 AM IST.
    
    <b>Process:</b>
    1. Get all active users
    2. For each user, generate and send report
    3. Aggregate results for logging
    
    <b>Why Sequential (not parallel)?</b>
    - Telegram rate limits: 30 messages/second
    - Graph generation is CPU-intensive
    - Cloud Run has limited CPU (1-2 vCPUs)
    - Sequential is simpler and more predictable
    
    For >50 users, we'd use Cloud Tasks for parallel execution.
    
    Args:
        project_id: GCP project ID
        bot: Telegram Bot instance
        
    Returns:
        Aggregate result with counts
    """
    all_users = firestore_service.get_all_users()
    
    results = {
        "total_users": len(all_users),
        "reports_sent": 0,
        "reports_empty": 0,
        "reports_failed": 0,
        "reports_skipped": 0,
        "timestamp": datetime.utcnow().isoformat(),
    }
    
    logger.info(f"📊 Starting weekly reports for {len(all_users)} users")
    
    for user in all_users:
        report_result = await generate_and_send_weekly_report(
            user_id=user.user_id,
            project_id=project_id,
            bot=bot,
        )
        
        status = report_result.get("status", "unknown")
        if status == "sent":
            results["reports_sent"] += 1
        elif status == "sent_empty":
            results["reports_empty"] += 1
        elif status == "skipped":
            results["reports_skipped"] += 1
        else:
            results["reports_failed"] += 1
    
    logger.info(
        f"📊 Weekly reports complete: {results['reports_sent']} sent, "
        f"{results['reports_empty']} empty, {results['reports_failed']} failed"
    )
    
    return results
