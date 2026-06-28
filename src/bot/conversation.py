"""
Check-In Conversation Handler
=============================

Multi-turn conversation state machine for daily check-ins.

Flow:
    /checkin → Q1 (Tier 1) → Q2 (Challenges) → Q3 (Rating) → Q4 (Tomorrow) → Q5 (Mood) → FINISH
    
States:
- Q1_TIER1: Ask about 5 Tier 1 non-negotiables with Y/N buttons
- Q2_CHALLENGES: Free text about today's challenges (10-500 chars)
- Q3_RATING: 1-10 rating + reason (validation: must start with number)
- Q4_TOMORROW: Tomorrow's priority + obstacle (10-500 chars each)
- Q5_MOOD: Energy & mood ratings 1-10 (inline buttons)
- FINISH: Calculate score, update streak, store data, send feedback

Key Concepts:
- ConversationHandler: Telegram's built-in state machine
- context.user_data: Temporary storage during conversation
- InlineKeyboard: Interactive buttons (Y/N)
- Input Validation: Ensure responses meet requirements
- Timeout: 15 minutes of inactivity → cancel conversation
"""

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)
from datetime import datetime
import re
import logging

from src.services.firestore_service import firestore_service
from src.services.achievement_service import achievement_service
from src.models.schemas import (
    DailyCheckIn,
    Tier1NonNegotiables,
    CheckInResponses
)
from src.utils.timezone_utils import get_current_date_ist, get_checkin_date, get_current_date
from src.utils.compliance import calculate_compliance_score, format_compliance_message
from src.utils.streak import update_streak_data, format_streak_message
from src.agents.checkin_agent import get_checkin_agent
from src.services.partner_notification_service import send_partner_checkin_notification
from src.config import settings

logger = logging.getLogger(__name__)


# ===== Conversation States =====
Q1_TIER1, Q2_ALIGNMENT_RATING, Q3_ENERGY_MOOD, Q4_REFLECTION_NOTE = range(4)

# Legacy states kept for test compilation compatibility
Q2_CHALLENGES = 99
Q3_RATING = 98
Q4_TOMORROW = 97
Q5_MOOD = 96


async def _notify_sender_if_partner_delivery_failed(message, notification_result) -> None:
    """
    Tell the sender only when partner delivery truly failed.

    We stay quiet for normal skip cases like "no partner", "disabled", or
    "already sent" because those are expected and shouldn't clutter check-ins.
    """
    if notification_result.get("reason") == "partner_missing":
        await message.reply_text(
            "ℹ️ Your check-in was saved, but partner notification could not be delivered "
            "because your linked partner account could not be found."
        )
    elif notification_result.get("reason") == "delivery_failed":
        await message.reply_text(
            "ℹ️ Your check-in was saved, but partner notification could not be delivered."
        )


def _get_message_from_update(update: Update):
    """
    Safely get the message object from an Update.

    When called from a callback query handler (e.g., mood button tap),
    update.message is None. We must use update.callback_query.message instead.
    """
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


# ===== Phase 3D: Career Mode Adaptive Questions =====

def get_skill_building_question(career_mode: str) -> dict:
    """
    Get skill building question adapted to user's career mode.
    
    <b>Design Pattern: Strategy Pattern</b>
    - Same interface (returns consistent dict structure)
    - Different behavior based on state (career_mode)
    - Clean separation of concerns
    
    <b>Why This Matters:</b>
    Your career phase determines what "skill building" means:
    - Learning phase: LeetCode, system design, courses
    - Job search: Applications + skill building
    - Employed: Promotion-focused work
    
    The question adapts to your current reality, making tracking more meaningful.
    
    Args:
        career_mode: User's current career phase
            - "skill_building": Learning phase (LeetCode, system design)
            - "job_searching": Active job hunt
            - "employed": Working toward promotion
    
    Returns:
        dict with keys:
            - question: Full question text shown in check-in
            - label: Short label for button/summary
            - description: Explanation of what counts
            
    Example:
        >>> q = get_skill_building_question("skill_building")
        >>> print(q["label"])
        "📚 Skill Building: 2+ hours?"
    """
    
    if career_mode == "skill_building":
        return {
            "question": "📚 <b>Skill Building:</b> 2+ hours today?",
            "label": "📚 Skill Building",
            "description": "(LeetCode, system design, AI/ML upskilling, courses, projects)"
        }
    
    elif career_mode == "job_searching":
        return {
            "question": "💼 <b>Job Search Progress:</b> Made progress today?",
            "label": "💼 Job Search",
            "description": "(Applications, interviews, LeetCode, networking)"
        }
    
    elif career_mode == "employed":
        return {
            "question": "🎯 <b>Career Progress:</b> Worked toward promotion/raise?",
            "label": "🎯 Career",
            "description": "(High-impact work, skill development, visibility projects)"
        }
    
    else:
        # Default fallback (defensive programming)
        logger.warning(f"⚠️ Unknown career_mode: {career_mode}, using default")
        return {
            "question": "📚 <b>Skill Building:</b> 2+ hours today?",
            "label": "📚 Skill Building",
            "description": "(Career-focused learning and development)"
        }


# ===== Entry Point =====

async def start_checkin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Entry point for /checkin and /quickcheckin commands (Phase 3E: Added quick check-in).
    
    <b>Process:</b>
    1. Check if user exists
    2. Check if already checked in today
    3. If /quickcheckin: Check weekly limit (2/week)
    4. Initialize conversation data
    5. Start Question 1 (Tier 1)
    
    <b>Phase 3E Quick Check-In:</b>
    - /quickcheckin triggers Tier 1-only flow (skip Q2-Q5)
    - Limited to 2 per week (enforced here)
    - Resets every Monday 12:00 AM IST
    
    Returns:
        int: Next state (Q1_TIER1) or ConversationHandler.END
    """
    user_id = str(update.effective_user.id)
    
    # Check if user exists
    user = firestore_service.get_user(user_id)
    if not user:
        await update.message.reply_text(
            "❌ Please use /start first to create your profile."
        )
        return ConversationHandler.END
    
    # Detect if this is a quick check-in
    command = update.message.text.split()[0] if update.message and update.message.text else ""
    is_quick_checkin = command == "/quickcheckin"
    
    # Phase 3E: Check quick check-in weekly limit
    if is_quick_checkin and user.quick_checkin_count >= 2:
        from src.utils.timezone_utils import get_next_monday
        
        # Build list of dates when quick check-ins were used
        history_lines = []
        for date_str in user.quick_checkin_used_dates[-2:]:  # Last 2 dates
            # Try to get compliance from that check-in
            try:
                checkin = firestore_service.get_checkin(user_id, date_str)
                compliance = f"{checkin.compliance_score:.0f}% compliance" if checkin else ""
                history_lines.append(f"• {date_str} - {compliance}")
            except:
                history_lines.append(f"• {date_str}")
        
        history_text = "\n".join(history_lines) if history_lines else "• Not tracked"
        
        # Get next Monday for reset date
        reset_date = get_next_monday(format_string="%A, %B %d")  # "Monday, February 10"
        
        await update.message.reply_text(
            f"❌ <b>Quick Check-In Limit Reached</b>\n\n"
            f"You've used both quick check-ins this week (max 2/week):\n\n"
            f"{history_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Use /checkin for full check-in.</b>\n\n"
            f"🔄 Limit resets: {reset_date} at 12:00 AM IST\n\n"
            f"💡 <b>Why the limit?</b>\n"
            f"Full check-ins provide better insights and accountability.\n"
            f"Quick check-ins are for genuinely busy days only.",
            parse_mode='HTML'
        )
        logger.info(f"❌ User {user_id} hit quick check-in limit (2/week)")
        return ConversationHandler.END
    
    # Phase B: Read user's timezone (defaults to IST for backward compat)
    user_tz = getattr(user, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
    
    # Check if already checked in today (Phase 3A: Use 3 AM cutoff logic, now timezone-aware)
    checkin_date = get_checkin_date(tz=user_tz)  # Before 3 AM local = previous day, after = current day
    if firestore_service.checkin_exists(user_id, checkin_date):
        await update.message.reply_text(
            f"✅ You've already completed your check-in for {checkin_date}!\n\n"
            f"🔥 Current streak: {user.streaks.current_streak} days\n"
            f"🏆 Personal best: {user.streaks.longest_streak} days\n\n"
            f"See you tomorrow at 9 PM for your next check-in! 💪"
        )
        return ConversationHandler.END
    
    # Initialize conversation data
    context.user_data.clear()  # Clear any previous data
    context.user_data['user_id'] = user_id
    context.user_data['checkin_start_time'] = datetime.utcnow()
    context.user_data['date'] = checkin_date  # Phase 3A: Use 3 AM cutoff
    context.user_data['mode'] = user.constitution_mode
    context.user_data['timezone'] = user_tz  # Phase B: Store for rest of conversation
    
    # Fetch yesterday's check-in for contextual memory.
    # This powers three things downstream:
    #   1. A recall intro message ("Yesterday you planned to...")
    #   2. An adapted Q2 question referencing yesterday's priority
    #   3. AI feedback that compares today vs yesterday's commitments
    from datetime import timedelta as td
    yesterday_date_str = (
        datetime.strptime(checkin_date, "%Y-%m-%d") - td(days=1)
    ).strftime("%Y-%m-%d")
    yesterday_checkin = firestore_service.get_checkin(user_id, yesterday_date_str)
    
    if yesterday_checkin and yesterday_checkin.responses:
        yesterday_data = {
            'date': yesterday_checkin.date,
            'compliance_score': yesterday_checkin.compliance_score,
            'rating': yesterday_checkin.responses.rating,
            'rating_reason': yesterday_checkin.responses.rating_reason,
            'tomorrow_priority': yesterday_checkin.responses.tomorrow_priority,
            'tomorrow_obstacle': yesterday_checkin.responses.tomorrow_obstacle,
            'challenges': yesterday_checkin.responses.challenges,
            'tier1': {
                'sleep': yesterday_checkin.tier1_non_negotiables.sleep,
                'training': yesterday_checkin.tier1_non_negotiables.training,
                'deep_work': yesterday_checkin.tier1_non_negotiables.deep_work,
                'skill_building': yesterday_checkin.tier1_non_negotiables.skill_building,
                'zero_porn': yesterday_checkin.tier1_non_negotiables.zero_porn,
                'boundaries': yesterday_checkin.tier1_non_negotiables.boundaries,
            }
        }
        context.user_data['yesterday_checkin'] = yesterday_data
        
        # Build recall intro message
        intro_parts = []
        if yesterday_data.get('tomorrow_priority'):
            intro_parts.append(
                f"You planned to focus on: <b>{yesterday_data['tomorrow_priority']}</b>"
            )
        if yesterday_data.get('tomorrow_obstacle'):
            intro_parts.append(
                f"Anticipated obstacle: <i>{yesterday_data['tomorrow_obstacle']}</i>"
            )
        tier1_results = yesterday_data.get('tier1', {})
        failures = [
            k.replace('_', ' ') for k, v in tier1_results.items() if not v
        ]
        if failures:
            intro_parts.append(f"Missed yesterday: {', '.join(failures)}")
        if yesterday_data.get('rating'):
            intro_parts.append(f"Self-rating: {yesterday_data['rating']}/10")
        
        if intro_parts:
            recall_msg = (
                "📋 <b>Yesterday's Recap:</b>\n"
                + "\n".join(f"• {p}" for p in intro_parts)
                + "\n\nLet's see how today went..."
            )
            await update.message.reply_text(recall_msg, parse_mode='HTML')
    else:
        context.user_data['yesterday_checkin'] = None
    
    # Phase 3E: Set quick check-in flag if /quickcheckin was used
    if is_quick_checkin:
        context.user_data['checkin_type'] = 'quick'
        
        # Show quick check-in intro
        from src.utils.timezone_utils import get_next_monday
        remaining = 2 - user.quick_checkin_count
        reset_date = get_next_monday(format_string="%A, %B %d")
        
        await update.message.reply_text(
            f"⚡ <b>Quick Check-In Mode</b>\n\n"
            f"Complete Tier 1 in ~2 minutes (6 questions only)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"<b>Available This Week:</b> {remaining}/2 quick check-ins\n"
            f"<b>Resets:</b> {reset_date} at 12:00 AM IST\n\n"
            f"💡 Quick check-ins count toward your streak but provide\n"
            f"abbreviated feedback. Use /checkin for full insights.\n\n"
            f"Let's go! Starting Tier 1 questions...",
            parse_mode='HTML'
        )
    else:
        context.user_data['checkin_type'] = 'full'
    
    # P1.3: Calculate adaptive context
    recent_checkins = firestore_service.get_recent_checkins(user_id, days=7)
    recent_scores = [c.compliance_score for c in recent_checkins if c.compliance_score is not None]
    avg_compliance = sum(recent_scores) / len(recent_scores) if recent_scores else 0.0
    
    is_power_user = (
        user.streaks.current_streak >= 30 and avg_compliance >= 85.0
    ) if user.streaks else False
    is_struggling = avg_compliance < 60.0 if recent_scores else False
    
    context.user_data['adaptive_context'] = {
        'power_user': is_power_user,
        'struggling': is_struggling,
        'avg_compliance': avg_compliance,
        'recent_count': len(recent_scores),
    }
    
    # P1.3: Struggling user — empathetic framing
    if is_struggling and not is_quick_checkin:
        await update.message.reply_text(
            f"💪 Hey {user.name}, I know it's been tough lately. "
            f"Let's take this one step at a time. Ready?"
        )
    
    # P1.3: Power user — mention quick mode availability
    if is_power_user and not is_quick_checkin:
        await update.message.reply_text(
            f"🔥 Day {user.streaks.current_streak} — you're on fire! "
            f"Quick mode available anytime with /quickcheckin."
        )
    
    # Start Question 1: Tier 1 non-negotiables
    await ask_tier1_question(update.message, context)
    
    logger_msg = "⚡ Quick check-in" if is_quick_checkin else "✅ Full check-in"
    logger.info(f"{logger_msg} started for {user_id}")
    return Q1_TIER1


async def ask_tier1_question(message, context):
    """
    Ask Question 1: Tier 1 non-negotiables with continuous data capture.
    
    <b>Phase v2.0: Continuous Data Capture</b>
    
    Now captures actual hours and intensity levels via button-based input:
    1. Sleep hours (6, 6.5, 7, 7.5, 8, 8.5, 9, Other)
    2. Deep work hours (0, 0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, More)
    3. Skill building hours (0, 0.5, 1, 1.5, 2, 2.5, 3, More)
    4. Training intensity (Rest Day, Light, Moderate, Intense)
    5. Zero Porn (Yes, No)
    6. Boundaries (Yes, No)
    
    Uses a step-by-step flow with inline keyboards for faster input.
    """
    # Initialize tier1 step tracking
    context.user_data['tier1_step'] = 0
    context.user_data['tier1_data'] = {}
    
    # Start with first question (sleep hours)
    await ask_tier1_step(message, context)


async def ask_tier1_step(message, context):
    """
    Ask a single step of the Tier 1 continuous data capture flow.
    
    Steps:
    0: Sleep hours
    1: Deep work hours
    2: Skill building hours
    3: Training intensity
    4: Zero Porn
    5: Boundaries
    """
    step = context.user_data.get('tier1_step', 0)
    
    steps = [
        {
            'metric': 'sleep_hours',
            'question': '💤 <b>How many hours did you sleep last night?</b>',
            'options': ['6', '6.5', '7', '7.5', '8', '8.5', '9', 'Other'],
            'target': '7h+',
        },
        {
            'metric': 'deep_work_hours',
            'question': '🧠 <b>How many focused deep work hours today?</b>',
            'options': ['0', '0.5', '1', '1.5', '2', '2.5', '3', '3.5', '4', 'More'],
            'target': '2h+',
        },
        {
            'metric': 'skill_building_hours',
            'question': '📚 <b>How many skill building hours today?</b>',
            'options': ['0', '0.5', '1', '1.5', '2', '2.5', '3', 'More'],
            'target': '2h+',
        },
        {
            'metric': 'training_intensity',
            'question': '💪 <b>What training did you do today?</b>',
            'options': ['Rest Day', 'Light', 'Moderate', 'Intense'],
            'target': None,
        },
        {
            'metric': 'zero_porn',
            'question': '🚫 <b>Zero porn maintained today?</b>',
            'options': ['Yes', 'No'],
            'target': None,
        },
        {
            'metric': 'boundaries',
            'question': '🛡️ <b>Healthy boundaries maintained today?</b>',
            'options': ['Yes', 'No'],
            'target': None,
        },
    ]
    
    if step >= len(steps):
        # All steps complete — move to completion
        return
    
    current = steps[step]
    question_text = current['question']
    if current['target']:
        question_text += f"\n<i>Target: {current['target']}</i>"
    question_text += f"\n\n<i>Step {step + 1}/6</i>"
    
    # Build keyboard with 4 buttons per row
    options = current['options']
    keyboard = []
    row = []
    
    for opt in options:
        callback = f"tier1_{current['metric']}_{opt.lower().replace(' ', '_')}"
        row.append(InlineKeyboardButton(opt, callback_data=callback))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    # Add Undo button if not on first step
    if step > 0:
        keyboard.append([InlineKeyboardButton("↩️ Undo Last", callback_data="tier1_undo")])
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(question_text, reply_markup=reply_markup, parse_mode='HTML')


# ===== State Q1: Tier 1 Non-Negotiables =====

async def handle_tier1_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle button presses for Tier 1 continuous data capture.
    
    Uses a step-by-step flow where each question is answered sequentially.
    When all 6 steps are complete, moves to Q2.
    
    Steps:
    0: Sleep hours
    1: Deep work hours
    2: Skill building hours
    3: Training intensity
    4: Zero Porn
    5: Boundaries
    
    Returns:
        int: Q1_TIER1 (still answering) or Q2_CHALLENGES (all answered)
    """
    query = update.callback_query
    await query.answer()  # Acknowledge button press
    
    # Initialize data structures if needed
    if 'tier1_step' not in context.user_data:
        context.user_data['tier1_step'] = 0
    if 'tier1_data' not in context.user_data:
        context.user_data['tier1_data'] = {}
    if 'tier1_answer_order' not in context.user_data:
        context.user_data['tier1_answer_order'] = []
    
    # P1.3: Handle perfect-day Q2 skip decision
    if context.user_data.get('awaiting_q2_skip'):
        context.user_data['awaiting_q2_skip'] = False
        if query.data == 'skip_q2':
            # Skip Q2 and Q3, set neutral values and go to Q4
            context.user_data['challenges'] = "Perfect day — skipped challenges question"
            context.user_data['rating'] = 10
            context.user_data['rating_reason'] = "Perfect day! All Tier 1 targets met."
            await query.message.reply_text(
                "⚡ <b>Skipped to Question 4/4</b>\n\n"
                "<b>Tomorrow's Plan:</b>\n"
                "1. What's tomorrow's #1 priority?\n"
                "2. What's the biggest potential obstacle?\n\n"
                "📝 Format: Priority | Obstacle",
                parse_mode='HTML'
            )
            return Q4_TOMORROW
        else:
            # User chose to answer anyway — proceed to Q2
            user_id = context.user_data['user_id']
            date = context.user_data.get('date') or get_checkin_date(tz="UTC")
            yesterday = context.user_data.get('yesterday_checkin')
            
            from src.services.task_service import task_service
            task_list = task_service.get_daily_tasks(user_id, date)
            
            missed_tasks = []
            completed_tasks = []
            if task_list and task_list.committed:
                missed_tasks = [t for t in task_list.tasks if not t.completed]
                completed_tasks = [t for t in task_list.tasks if t.completed]
            
            if missed_tasks:
                missed_str = "\n".join([f"• \"{t.title}\"" for t in missed_tasks])
                obstacle = yesterday.get('tomorrow_obstacle') if yesterday else ""
                obstacle_str = f"You anticipated that <b>\"{obstacle}\"</b> might get in the way.\n" if obstacle else ""
                
                q2_text = (
                    f"📋 <b>Question 2/4</b>\n\n"
                    f"<b>Challenges & Reflection:</b>\n"
                    f"I noticed you didn't complete all of today's committed tasks:\n"
                    f"{missed_str}\n\n"
                    f"{obstacle_str}"
                    f"What got in the way? Did your anticipated obstacle happen, or was it something else?\n\n"
                    f"📝 Type your response (10-500 characters)."
                )
            elif completed_tasks:
                q2_text = (
                    f"📋 <b>Question 2/4</b>\n\n"
                    f"<b>Challenges & Reflection:</b>\n"
                    f"Amazing! You completed all committed tasks today, including your primary focus!\n\n"
                    f"What challenges (if any) did you face today, and what went well to help you succeed?\n\n"
                    f"📝 Type your response (10-500 characters)."
                )
            elif yesterday and yesterday.get('tomorrow_priority'):
                priority = yesterday['tomorrow_priority']
                q2_text = (
                    f"📋 <b>Question 2/4</b>\n\n"
                    f"<b>Challenges & Reflection:</b>\n"
                    f"Yesterday you planned to focus on:\n"
                    f"<b>\"{priority}\"</b>\n\n"
                    f"How did that go? What challenges did you face today?\n\n"
                    f"📝 Type your response (10-500 characters)."
                )
            else:
                q2_text = (
                    "📋 <b>Question 2/4</b>\n\n"
                    "<b>Challenges & Handling:</b>\n"
                    "What challenges did you face today? How did you handle them?\n\n"
                    "📝 Type your response (10-500 characters).\n\n"
                    "Example: 'Urge to watch porn around 10 PM. Went for a walk and texted friend instead.'"
                )
            await query.message.reply_text(q2_text, parse_mode='HTML')
            return Q2_CHALLENGES
    
    # Handle undo callback
    if query.data == 'tier1_undo':
        answer_order = context.user_data.get('tier1_answer_order', [])
        if answer_order:
            # Pop the last answered metric
            last_metric = answer_order.pop()
            context.user_data['tier1_data'].pop(last_metric, None)
            context.user_data['tier1_step'] -= 1
            # Ensure step doesn't go below 0
            if context.user_data['tier1_step'] < 0:
                context.user_data['tier1_step'] = 0
            await query.message.reply_text(
                f"↩️ Undo complete. Let's re-answer that question."
            )
        else:
            await query.message.reply_text("Nothing to undo yet.")
        # Re-ask the current step
            await ask_tier1_step(query.message, context)
        return Q1_TIER1
    
    # Parse callback data — supports BOTH old format ("sleep_yes") and new format ("tier1_sleep_hours_7.5")
    if query.data.startswith('tier1_'):
        # NEW FORMAT: tier1_<metric>_<value>
        parts = query.data.split('_')
        metric = '_'.join(parts[1:-1])  # e.g., "sleep_hours" or "training_intensity"
        value = parts[-1].replace('_', ' ')  # e.g., "7.5" or "rest day"
        
        # Convert value based on metric type
        if metric in ('sleep_hours', 'deep_work_hours', 'skill_building_hours'):
            try:
                value = float(value)
                target_met = value >= 7.0 if metric == 'sleep_hours' else value >= 2.0
                emoji = '✅' if target_met else '⚠️'
                unit = 'h'
                confirmation = f"{emoji} {metric.replace('_', ' ').title()}: {value}{unit}"
            except ValueError:
                confirmation = f"📋 {metric.replace('_', ' ').title()}: {value}"
        elif metric == 'training_intensity':
            emoji = '💪' if value in ('light', 'moderate', 'intense') else '😴'
            confirmation = f"{emoji} Training: {value.title()}"
        elif metric in ('zero_porn', 'boundaries'):
            response_bool = (value.lower() == 'yes')
            emoji = '✅' if response_bool else '❌'
            label = 'Zero Porn' if metric == 'zero_porn' else 'Boundaries'
            confirmation = f"{emoji} {label}: {'Yes' if response_bool else 'No'}"
            value = response_bool
        else:
            confirmation = f"📋 {metric}: {value}"
        
        context.user_data['tier1_data'][metric] = value
        context.user_data['tier1_answer_order'].append(metric)
    
    elif '_' in query.data and not query.data.startswith('tier1_'):
        # OLD FORMAT: "sleep_yes", "training_no", etc. (backward compatibility)
        item, response = query.data.rsplit('_', 1)
        response_bool = (response == "yes")
        
        # Map old item names to new metric names
        metric_map = {
            'sleep': 'sleep_hours',
            'training': 'training_intensity',
            'deepwork': 'deep_work_hours',
            'skillbuilding': 'skill_building_hours',
            'porn': 'zero_porn',
            'boundaries': 'boundaries',
        }
        metric = metric_map.get(item, item)
        
        # Convert to new format values
        if metric == 'sleep_hours':
            value = 7.5 if response_bool else 5.5
            confirmation = f"{'✅' if response_bool else '❌'} Sleep: {value}h"
        elif metric == 'deep_work_hours':
            value = 2.5 if response_bool else 0.5
            confirmation = f"{'✅' if response_bool else '❌'} Deep Work: {value}h"
        elif metric == 'skill_building_hours':
            value = 2.5 if response_bool else 0.5
            confirmation = f"{'✅' if response_bool else '❌'} Skill Building: {value}h"
        elif metric == 'training_intensity':
            value = 'moderate' if response_bool else 'rest'
            confirmation = f"{'✅' if response_bool else '❌'} Training: {value.title()}"
        elif metric == 'zero_porn':
            value = response_bool
            confirmation = f"{'✅' if response_bool else '❌'} Zero Porn"
        elif metric == 'boundaries':
            value = response_bool
            confirmation = f"{'✅' if response_bool else '❌'} Boundaries"
        else:
            value = response_bool
            confirmation = f"{'✅' if response_bool else '❌'} {item.title()}"
        
        context.user_data['tier1_data'][metric] = value
        context.user_data['tier1_answer_order'].append(metric)
    
    else:
        logger.warning(f"Unknown callback data: {query.data}")
        return Q1_TIER1
    
    # Show confirmation
    await query.message.reply_text(confirmation)
    
    # Move to next step
    context.user_data['tier1_step'] += 1
    step = context.user_data['tier1_step']
    
    # Check if all steps complete
    if step >= 6:
        # All answered → build Tier1NonNegotiables
        tier1_data = context.user_data['tier1_data']
        
        # Build the Tier1NonNegotiables object with continuous data
        # Set BOTH continuous fields AND boolean fields for backward compatibility
        sleep_hours = float(tier1_data.get('sleep_hours', 0))
        dw_hours = float(tier1_data.get('deep_work_hours', 0))
        sb_hours = float(tier1_data.get('skill_building_hours', 0))
        training_intensity = tier1_data.get('training_intensity', 'rest').lower()
        
        tier1 = Tier1NonNegotiables(
            sleep_hours=sleep_hours,
            deep_work_hours=dw_hours,
            skill_building_hours=sb_hours,
            training_intensity=training_intensity,
            # Set boolean fields to represent FULL targets (not micro-habits)
            sleep=sleep_hours >= 7.0,
            training=training_intensity in ('light', 'moderate', 'intense'),
            deep_work=dw_hours >= 2.0,
            skill_building=sb_hours >= 2.0,
            is_rest_day=training_intensity == 'rest',
            zero_porn=tier1_data.get('zero_porn', False),
            boundaries=tier1_data.get('boundaries', False),
            data_quality='actual',
        )
        
        context.user_data['tier1'] = tier1
        
        # Calculate compliance score early for adaptive branching (P1.3)
        user_id = context.user_data['user_id']
        date = context.user_data.get('date') or get_checkin_date(tz="UTC")
        from src.services.task_service import task_service
        task_list = task_service.get_daily_tasks(user_id, date)
        committed_tasks = task_list.tasks if (task_list and task_list.committed) else None
        
        compliance_score = calculate_compliance_score(tier1, committed_tasks)
        context.user_data['compliance_score'] = compliance_score
        
        # Phase 3E: Check if this is a quick check-in
        is_quick_checkin = context.user_data.get('checkin_type') == 'quick'
        
        if is_quick_checkin:
            # Quick check-in: Skip Q2-Q4 and finish immediately
            await query.message.reply_text(
                "⚡ <b>Quick Check-In Complete!</b>\n\n"
                "Processing Tier 1 responses and generating feedback...",
                parse_mode='HTML'
            )
            
            # Set dummy values for Q2-Q4 (required by finish_checkin)
            context.user_data['challenges'] = "Quick check-in (Q2-Q5 skipped)"
            context.user_data['rating'] = 7  # Neutral rating
            context.user_data['rating_reason'] = "Quick check-in mode"
            context.user_data['tomorrow_priority'] = "Continue daily check-ins"
            context.user_data['tomorrow_obstacle'] = "None identified"
            
            # Finish check-in
            await finish_checkin_quick(update, context)
            return ConversationHandler.END
        else:
            # Move to Q3: Energy Rating directly (manual alignment rating bypassed)
            energy_keyboard = [
                [InlineKeyboardButton(str(i), callback_data=f"energy_{i}") for i in range(1, 6)],
                [InlineKeyboardButton(str(i), callback_data=f"energy_{i}") for i in range(6, 11)],
            ]
            await query.message.reply_text(
                "📋 <b>Question 2/3: Energy & Mood</b>\n\n"
                "⚡ <b>Rate your energy today?</b> (1 = exhausted, 10 = unstoppable)",
                reply_markup=InlineKeyboardMarkup(energy_keyboard),
                parse_mode='HTML'
            )
            return Q3_ENERGY_MOOD
    
    # Ask next step
    await ask_tier1_step(query.message, context)
    return Q1_TIER1


# ===== State Q2: Challenges =====

async def handle_challenges_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle Question 2: Challenges.
    
    Validates:
    - Length: 10-500 characters
    
    Returns:
        int: Q2_CHALLENGES (invalid) or Q3_RATING (valid)
    """
    text = update.message.text.strip()
    
    # Validate length
    if len(text) < 10:
        await update.message.reply_text(
            "⚠️ Please provide more detail (minimum 10 characters).\n\n"
            "What challenges did you face? How did you handle them?"
        )
        return Q2_CHALLENGES
    
    if len(text) > 500:
        await update.message.reply_text(
            "⚠️ Response too long (maximum 500 characters).\n\n"
            "Please summarize your key challenges."
        )
        return Q2_CHALLENGES
    
    # Store response
    context.user_data['challenges'] = text
    
    # Move to Q3
    await update.message.reply_text(
        "<b>📋 Question 3/5</b>\n\n"
        "<b>Self-Rating & Reflection:</b>\n"
        "Rate today 1-10 on constitution alignment. Why that score?\n\n"
        "📝 Format: Start with number (1-10), then explain.\n\n"
        "_Example: '8 - Solid day overall. Missed one study hour but otherwise strong.'_",
        parse_mode='HTML'
    )
    
    return Q3_RATING


# ===== State Q3: Rating =====

async def handle_rating_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle Question 3: Self-rating.
    
    Validates:
    - Must start with number 1-10
    - Must have explanation after number (min 10 chars)
    
    Returns:
        int: Q3_RATING (invalid) or Q4_TOMORROW (valid)
    """
    text = update.message.text.strip()
    
    # Extract rating (first number in text)
    rating_match = re.match(r'^(\d+)', text)
    
    if not rating_match:
        await update.message.reply_text(
            "⚠️ Please start with a number (1-10).\n\n"
            "Example: '7 - Good day, but missed workout'"
        )
        return Q3_RATING
    
    rating = int(rating_match.group(1))
    
    if rating < 1 or rating > 10:
        await update.message.reply_text(
            "⚠️ Rating must be between 1 and 10.\n\n"
            "How well did you align with your constitution today?"
        )
        return Q3_RATING
    
    # Extract reason (text after number)
    reason = text[len(rating_match.group(1)):].strip()
    reason = reason.lstrip('-–—').strip()  # Remove dashes
    
    if len(reason) < 10:
        await update.message.reply_text(
            "⚠️ Please explain your rating (minimum 10 characters).\n\n"
            "Why did you rate today as " + str(rating) + "/10?"
        )
        return Q3_RATING
    
    # Store responses
    context.user_data['rating'] = rating
    context.user_data['rating_reason'] = reason
    
    # Move to Q4
    await update.message.reply_text(
        "<b>📋 Question 4/5</b>\n\n"
        "<b>Tomorrow's Plan:</b>\n"
        "1. What's tomorrow's #1 priority?\n"
        "2. What's the biggest potential obstacle?\n\n"
        "📝 Format: Priority | Obstacle\n\n"
        "_Example: 'Priority: Complete 3 LeetCode problems. Obstacle: Late evening meeting might drain energy.'_",
        parse_mode='HTML'
    )
    
    return Q4_TOMORROW


# ===== State Q4: Tomorrow's Plan =====

async def handle_tomorrow_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle Question 4: Tomorrow's plan.
    
    Final question - after this, we calculate score and save data.
    
    Validates:
    - Length: 10-500 characters
    
    Returns:
        int: Q4_TOMORROW (invalid) or ConversationHandler.END (valid, complete)
    """
    text = update.message.text.strip()
    
    # Validate length
    if len(text) < 10:
        await update.message.reply_text(
            "⚠️ Please provide more detail (minimum 10 characters).\n\n"
            "What's tomorrow's priority and obstacle?"
        )
        return Q4_TOMORROW
    
    if len(text) > 500:
        await update.message.reply_text(
            "⚠️ Response too long (maximum 500 characters).\n\n"
            "Please summarize your priority and obstacle."
        )
        return Q4_TOMORROW
    
    # Try to split into priority and obstacle
    if '|' in text or ' - ' in text:
        # User provided delimiter
        parts = re.split(r'\||—|-', text, maxsplit=1)
        priority = parts[0].strip()
        obstacle = parts[1].strip() if len(parts) > 1 else text
    else:
        # No delimiter - store as priority, obstacle same
        priority = text
        obstacle = text
    
    # Store responses
    context.user_data['tomorrow_priority'] = priority
    context.user_data['tomorrow_obstacle'] = obstacle
    context.user_data['suppress_general_message_once'] = True

    # Move to Q5 (Energy & Mood)
    await update.message.reply_text(
        "<b>📋 Question 5/5</b>\n\n"
        "<b>Energy & Mood:</b>\n"
        "Rate your energy and mood today (1-10 each).\n\n"
        "📝 Format: Energy | Mood\n"
        "_Example: '7 | 8' (7 energy, 8 mood)_\n\n"
        "Or use the quick-reply buttons below:",
        parse_mode='HTML'
    )

    # Send energy quick-reply buttons
    energy_keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"energy_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"energy_{i}") for i in range(6, 11)],
    ]
    await update.message.reply_text(
        "⚡ <b>Energy today?</b> (1 = exhausted, 10 = unstoppable)",
        reply_markup=InlineKeyboardMarkup(energy_keyboard),
        parse_mode='HTML'
    )

    return Q5_MOOD


# ===== State Q5: Energy & Mood =====

async def handle_alignment_rating_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle alignment rating selection via inline button (1-10).
    Stores rating and prompts for Energy rating.
    """
    query = update.callback_query
    await query.answer()
    
    rating = int(query.data.split("_")[1])
    context.user_data['rating'] = rating
    
    # Prompt for Energy
    energy_keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"energy_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"energy_{i}") for i in range(6, 11)],
    ]
    await query.edit_message_text(
        f"🎯 Alignment Rating: <b>{rating}/10</b>\n\n"
        f"⚡ <b>Rate your energy today?</b> (1 = exhausted, 10 = unstoppable)",
        reply_markup=InlineKeyboardMarkup(energy_keyboard),
        parse_mode='HTML'
    )
    return Q3_ENERGY_MOOD


async def handle_energy_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle energy rating selection via inline button.
    Stores energy and prompts for mood rating.
    """
    query = update.callback_query
    await query.answer()

    # Extract energy rating from callback_data
    energy_rating = int(query.data.split("_")[1])
    context.user_data['energy_rating'] = energy_rating

    # Send mood quick-reply buttons
    mood_keyboard = [
        [InlineKeyboardButton(str(i), callback_data=f"mood_{i}") for i in range(1, 6)],
        [InlineKeyboardButton(str(i), callback_data=f"mood_{i}") for i in range(6, 11)],
    ]
    await query.edit_message_text(
        f"⚡ Energy: <b>{energy_rating}/10</b>\n\n"
        f"😊 <b>Mood today?</b> (1 = terrible, 10 = amazing)",
        reply_markup=InlineKeyboardMarkup(mood_keyboard),
        parse_mode='HTML'
    )

    return Q3_ENERGY_MOOD


async def handle_mood_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle mood rating selection via inline button.
    Stores mood and prompts for mandatory reflection note (Q3).
    """
    query = update.callback_query
    await query.answer()

    # Extract mood rating from callback_data
    mood_rating = int(query.data.split("_")[1])
    context.user_data['mood_rating'] = mood_rating

    # Update the message to show ratings
    energy = context.user_data.get('energy_rating', '?')

    await query.edit_message_text(
        f"⚡ Energy: <b>{energy}/10</b>\n"
        f"😊 Mood: <b>{mood_rating}/10</b>\n\n"
        f"📝 <b>Question 3/3: Daily Reflection (Mandatory)</b>\n\n"
        f"To maintain true accountability, please type a short reflection (minimum 20 characters) describing:\n"
        f"1. How today went and any challenges or mistakes you encountered.\n"
        f"2. Your #1 focus and expected obstacle for tomorrow.\n\n"
        f"<i>(You can also record and send a voice note reflecting on your day)</i>",
        parse_mode='HTML'
    )

    return Q4_REFLECTION_NOTE


async def handle_reflection_skip_callback(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle skip button press for reflection note.
    Fills in neutral defaults and completes check-in.
    """
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "🏁 Check-in reflection skipped.\n"
        "💾 Saving check-in and generating feedback...",
        parse_mode='HTML'
    )
    
    # Populate neutral values
    rating = context.user_data.get('rating', 8)
    context.user_data['challenges'] = "None reported."
    context.user_data['rating_reason'] = f"Cohesive alignment with targets (Rated {rating}/10)."
    context.user_data['tomorrow_priority'] = "Maintain consistency."
    context.user_data['tomorrow_obstacle'] = "None reported."
    
    # Finish check-in
    await finish_checkin(update, context)
    return ConversationHandler.END


async def handle_reflection_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle free-text reflection note response.
    Parses using Gemini to extract challenges, rating reason, priority, obstacle,
    saves the check-in, and completes.
    """
    note_text = update.message.text.strip()
    
    # Enforce minimum length (20 characters)
    if len(note_text) < 20:
        await update.message.reply_text(
            "⚠️ <b>Reflection note too short!</b>\n\n"
            "Please write at least 20 characters reflecting on today's execution "
            "and tomorrow's plan so the AI coach can analyze your patterns.",
            parse_mode='HTML'
        )
        return Q4_REFLECTION_NOTE

    # Send a progress indicator
    progress_msg = await update.message.reply_text(
        "🧠 <i>Analyzing your reflection and structuring daily focus...</i>",
        parse_mode='HTML'
    )
    
    compliance_score = context.user_data.get('compliance_score', 0.0)
    
    # Format a summary of Tier 1 metrics for LLM context
    tier1 = context.user_data.get('tier1')
    t1_completed = []
    if tier1:
        if tier1.sleep_met: t1_completed.append("sleep")
        if tier1.training_done or tier1.is_rest_day: t1_completed.append("training")
        if tier1.deep_work_met: t1_completed.append("deep work")
        if tier1.skill_building_met: t1_completed.append("skill building")
        if tier1.zero_porn: t1_completed.append("zero porn")
        if tier1.boundaries: t1_completed.append("boundaries")
    t1_str = ", ".join(t1_completed) if t1_completed else "none"
    
    # Call Gemini to parse reflection and grade alignment rating
    agent = get_checkin_agent(settings.gcp_project_id)
    parsed = await agent.parse_reflection_note(
        note_text=note_text,
        tier1_completed=t1_str,
        compliance_score=compliance_score
    )
    
    # Extract AI-graded alignment rating
    rating = parsed.get("alignment_rating", 8)
    
    # Store parsed data in context.user_data
    context.user_data['rating'] = rating
    context.user_data['challenges'] = parsed.get("challenges", "None reported.")
    context.user_data['rating_reason'] = parsed.get("rating_reason", f"Alignment rating: {rating}/10.")
    context.user_data['tomorrow_priority'] = parsed.get("tomorrow_priority", "Maintain consistency.")
    context.user_data['tomorrow_obstacle'] = parsed.get("tomorrow_obstacle", "None reported.")
    context.user_data['suppress_general_message_once'] = True
    
    try:
        await progress_msg.delete()
    except Exception as e:
        logger.warning(f"Could not delete progress message: {e}")
        
    await update.message.reply_text(
        "💾 Reflection parsed. Saving check-in and generating feedback...",
        parse_mode='HTML'
    )
    
    await finish_checkin(update, context)
    return ConversationHandler.END


async def handle_voice_reflection(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle voice reflection note by acknowledging and completing with defaults.
    """
    await update.message.reply_text(
        "🎤 <b>Voice note received!</b> (Audio transcription is not configured in this version, "
        "so I will complete your check-in with standard defaults).\n\n"
        "💾 Saving check-in and generating feedback...",
        parse_mode='HTML'
    )
    
    # Populate neutral values
    rating = context.user_data.get('rating', 8)
    context.user_data['challenges'] = "Voice reflection recorded (audio file)."
    context.user_data['rating_reason'] = f"Cohesive alignment with targets (Rated {rating}/10)."
    context.user_data['tomorrow_priority'] = "Maintain consistency."
    context.user_data['tomorrow_obstacle'] = "None reported."
    
    # Finish check-in
    await finish_checkin(update, context)
    return ConversationHandler.END


# ===== Finish Check-In =====

async def finish_checkin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Complete check-in:
    1. Create CheckIn object
    2. Calculate compliance score
    3. Update streak
    4. Store in Firestore
    5. Send feedback message
    """
    user_id = context.user_data['user_id']
    date = context.user_data.get('date') or get_checkin_date(tz="UTC")
    
    try:
        # Calculate check-in duration
        duration = int((datetime.utcnow() - context.user_data['checkin_start_time']).total_seconds())
        
        # Get Tier1NonNegotiables object (built during Q1 continuous data capture)
        tier1 = context.user_data.get('tier1')
        
        # Fallback: if using old flow (backward compatibility for in-progress check-ins)
        if tier1 is None:
            tier1_data = context.user_data.get('tier1_responses', {})
            sleep_val = tier1_data.get('sleep', False)
            training_val = tier1_data.get('training', False)
            dw_val = tier1_data.get('deepwork', False)
            sb_val = tier1_data.get('skillbuilding', False)
            
            tier1 = Tier1NonNegotiables(
                sleep=sleep_val,
                training=training_val,
                deep_work=dw_val,
                skill_building=sb_val,
                sleep_hours=7.5 if sleep_val else 5.5,
                deep_work_hours=2.5 if dw_val else 0.5,
                skill_building_hours=2.5 if sb_val else 0.5,
                training_intensity='moderate' if training_val else 'rest',
                is_rest_day=not training_val,
                zero_porn=tier1_data.get('porn', False),
                boundaries=tier1_data.get('boundaries', False),
                data_quality='migrated',
            )
        
        # Create CheckInResponses object
        responses = CheckInResponses(
            challenges=context.user_data['challenges'],
            rating=context.user_data['rating'],
            rating_reason=context.user_data['rating_reason'],
            tomorrow_priority=context.user_data['tomorrow_priority'],
            tomorrow_obstacle=context.user_data['tomorrow_obstacle'],
            energy_rating=context.user_data.get('energy_rating'),
            mood_rating=context.user_data.get('mood_rating'),
        )
        
        # Load committed tasks for today
        from src.services.task_service import task_service
        task_list = task_service.get_daily_tasks(user_id, date)
        committed_tasks = task_list.tasks if (task_list and task_list.committed) else None

        # Calculate compliance score
        compliance_score = calculate_compliance_score(tier1, committed_tasks)
        
        # Create DailyCheckIn object
        checkin = DailyCheckIn(
            date=date,
            user_id=user_id,
            mode=context.user_data['mode'],
            tier1_non_negotiables=tier1,
            responses=responses,
            compliance_score=compliance_score,
            completed_at=datetime.utcnow(),
            duration_seconds=duration,
            committed_tasks=committed_tasks
        )
        
        # Store check-in + update streak ATOMICALLY in a single transaction.
        # Previously these were two separate writes. If the streak update failed
        # after the check-in was stored, the streak would become stale and
        # incorrectly reset on the next check-in. The transaction guarantees
        # all-or-nothing: either both succeed or neither does.
        user = firestore_service.get_user(user_id)
        streak_updates = update_streak_data(
            current_streak=user.streaks.current_streak,
            longest_streak=user.streaks.longest_streak,
            total_checkins=user.streaks.total_checkins,
            last_checkin_date=user.streaks.last_checkin_date,
            new_checkin_date=date,
            # Phase D: Pass recovery tracking fields for reset detection
            streak_before_reset=getattr(user.streaks, 'streak_before_reset', 0) or 0,
            last_reset_date=getattr(user.streaks, 'last_reset_date', None)
        )
        
        firestore_service.store_checkin_with_streak_update(user_id, checkin, streak_updates)
        
        # Phase 4: Long-Term Memory Synthesis
        updated_memory = getattr(user, 'ai_profile_memory', None)
        total_checkins = streak_updates.get('total_checkins', 0)
        if total_checkins > 0 and total_checkins % 5 == 0:
            from src.services.memory_service import memory_service
            logger.info(f"Triggering long-term memory synthesis for user {user_id} (check-in count: {total_checkins})")
            try:
                synthesized = await memory_service.update_user_memory(user_id)
                if synthesized:
                    updated_memory = synthesized
            except Exception as e:
                logger.error(f"Failed to synthesize memory in check-in flow: {e}")

        # Extract milestone if hit (Phase 3C Day 4)
        milestone_hit = streak_updates.get('milestone_hit')
        if milestone_hit:
            logger.info(
                f"🎉 User {user_id} hit milestone: {streak_updates['current_streak']} days!"
            )
        
        # Generate AI-powered feedback message
        is_new_record = (
            streak_updates['current_streak'] > streak_updates['longest_streak'] - 1
            and streak_updates['current_streak'] > 1
        )
        
        try:
            # Get CheckIn Agent
            checkin_agent = get_checkin_agent(settings.gcp_project_id)
            recent_checkins = checkin_agent._get_recent_checkins(user_id, days=7)
            
            # Generate personalized feedback with AI
            ai_feedback = await checkin_agent.generate_feedback(
                user_id=user_id,
                compliance_score=compliance_score,
                tier1=tier1,
                current_streak=streak_updates['current_streak'],
                longest_streak=streak_updates['longest_streak'],
                self_rating=context.user_data['rating'],
                rating_reason=context.user_data['rating_reason'],
                tomorrow_priority=context.user_data['tomorrow_priority'],
                tomorrow_obstacle=context.user_data['tomorrow_obstacle'],
                yesterday_checkin=context.user_data.get('yesterday_checkin'),
                ai_profile_memory=updated_memory,
            )

            support_guidance = None
            if checkin_agent.should_offer_support_guidance(
                tier1=tier1,
                self_rating=context.user_data['rating'],
                rating_reason=context.user_data['rating_reason'],
                challenges=context.user_data['challenges'],
                recent_checkins=recent_checkins,
                compliance_score=compliance_score,
            ):
                try:
                    support_guidance = await checkin_agent.generate_support_guidance(
                        user_id=user_id,
                        tier1=tier1,
                        compliance_score=compliance_score,
                        self_rating=context.user_data['rating'],
                        rating_reason=context.user_data['rating_reason'],
                        challenges=context.user_data['challenges'],
                        current_streak=streak_updates['current_streak'],
                        recent_checkins=recent_checkins,
                    )
                except Exception as e:
                    logger.error(f"Support guidance generation failed, skipping: {e}")
            
            # Build final message with header and AI feedback
            feedback_parts = []
            feedback_parts.append("🎉 <b>Check-In Complete!</b>\n")
            feedback_parts.append(f"📊 Compliance: {compliance_score}%")
            
            # Phase D: Show recovery message on reset, normal streak otherwise
            if streak_updates.get('is_reset') and streak_updates.get('recovery_message'):
                feedback_parts.append(f"\n{streak_updates['recovery_message']}")
            else:
                feedback_parts.append(f"🔥 Streak: {streak_updates['current_streak']} days")
            
            if is_new_record:
                feedback_parts.append("🏆 <b>NEW PERSONAL RECORD!</b>")
            
            feedback_parts.append(f"📈 Total check-ins: {streak_updates['total_checkins']}")
            feedback_parts.append(f"\n---\n\n{ai_feedback}")
            
            # ===== PHASE 3C: Add Social Proof (Day 3) =====
            try:
                # Get updated user for social proof calculation
                user_profile = firestore_service.get_user(user_id)
                if user_profile:
                    social_proof = achievement_service.get_social_proof_message(user_profile)
                    if social_proof:
                        feedback_parts.append(f"\n{social_proof}")
                        logger.info(f"📊 Added social proof for user {user_id}")
            except Exception as e:
                logger.error(f"⚠️ Social proof generation failed (non-critical): {e}")

            if support_guidance:
                feedback_parts.append(f"\n---\n\n💙 <b>Support Focus</b>\n{support_guidance}")
            
            feedback_parts.append(f"\n---\n\n🎯 See you tomorrow at 9 PM!")
            
            final_message = "\n".join(feedback_parts)
            
        except Exception as e:
            logger.error(f"AI feedback generation failed, using fallback: {e}")
            
            # Fallback to Phase 1 hardcoded feedback
            feedback_parts = []
            feedback_parts.append("🎉 <b>Check-In Complete!</b>\n")
            feedback_parts.append(f"📊 Compliance: {compliance_score}%")
            
            # Phase D: Show recovery message on reset, normal streak otherwise
            if streak_updates.get('is_reset') and streak_updates.get('recovery_message'):
                feedback_parts.append(f"\n{streak_updates['recovery_message']}")
            else:
                feedback_parts.append(f"🔥 Streak: {streak_updates['current_streak']} days")
            
            if compliance_score == 100:
                feedback_parts.append(
                    "\n💯 Perfect day! All Tier 1 non-negotiables completed."
                )
            elif compliance_score >= 80:
                feedback_parts.append(
                    "\n✅ Strong day! Keep this momentum going."
                )
            else:
                feedback_parts.append(
                    "\n⚠️ Room for improvement. Focus on Tier 1 priorities tomorrow."
                )
            
            feedback_parts.append(f"\n📈 Total: {streak_updates['total_checkins']} check-ins")
            
            # ===== PHASE 3C: Add Social Proof to Fallback (Day 3) =====
            try:
                user_profile = firestore_service.get_user(user_id)
                if user_profile:
                    social_proof = achievement_service.get_social_proof_message(user_profile)
                    if social_proof:
                        feedback_parts.append(f"\n{social_proof}")
            except Exception as e:
                logger.error(f"⚠️ Social proof failed in fallback: {e}")
            
            feedback_parts.append(f"\n🎯 See you tomorrow!")
            
            final_message = "\n".join(feedback_parts)
        
        msg = _get_message_from_update(update)
        if msg:
            await msg.reply_text(final_message, parse_mode='HTML')

        partner_notification = await send_partner_checkin_notification(
            bot=context.bot,
            sender=user,
            tier1=tier1,
            date=date,
            fallback_sender_name=update.effective_user.first_name,
        )
        if msg:
            await _notify_sender_if_partner_delivery_failed(msg, partner_notification)
        
        # ===== P2.2: Goal Progress Integration =====
        try:
            from src.services.goal_service import goal_service
            
            # Rebuild a proper DailyCheckIn object for goal evaluation
            checkin_for_goals = DailyCheckIn(
                date=date,
                user_id=user_id,
                mode=context.user_data['mode'],
                tier1_non_negotiables=tier1,
                responses=responses,
                compliance_score=compliance_score,
            )
            
            goal_updates = goal_service.update_progress_from_checkin(checkin_for_goals)
            
            if goal_updates:
                goal_messages = []
                for goal, milestone in goal_updates:
                    if milestone == "100%":
                        goal_messages.append(
                            f"🏆 <b>Goal Completed!</b>\n"
                            f"'{goal.title}' — {len(goal.progress)}/{goal.target_days} days!"
                        )
                    elif milestone in ("50%", "75%"):
                        goal_messages.append(
                            f"🎯 <b>{milestone} Milestone!</b>\n"
                            f"'{goal.title}' — keep going!"
                        )
                
                if goal_messages:
                    if msg:
                        await msg.reply_text(
                            "\n\n".join(goal_messages),
                            parse_mode='HTML'
                        )
                    logger.info(f"🎯 Goal milestones reached for {user_id}: {len(goal_updates)}")
        except Exception as e:
            logger.error(f"⚠️ Goal progress update failed (non-critical): {e}")
        
        # ===== P2.3: Challenge Progress Update =====
        try:
            from src.services.challenge_service import challenge_service
            updated_challenges = challenge_service.update_progress_from_checkin(checkin_for_goals)
            if updated_challenges:
                for ch in updated_challenges:
                    # Check if challenge completed
                    winner = challenge_service.check_completion(ch)
                    if winner:
                        if winner == user_id:
                            if msg:
                                await msg.reply_text(
                                    f"🏆 <b>You Won the Challenge!</b>\n\n"
                                    f"'{ch.title}' — victory is yours! 🔥",
                                    parse_mode='HTML'
                                )
                        elif winner == ch.partner_id:
                            if msg:
                                await msg.reply_text(
                                    f"😤 <b>Challenge Lost</b>\n\n"
                                    f"'{ch.title}' — your partner edged you out. Rematch?",
                                    parse_mode='HTML'
                                )
                        else:
                            if msg:
                                await msg.reply_text(
                                    f"🤝 <b>Challenge Tie!</b>\n\n"
                                    f"'{ch.title}' — dead even. Rematch?",
                                    parse_mode='HTML'
                                )
                    else:
                        # Daily progress update
                        progress = ch.progress.get(user_id, [])
                        met_days = sum(1 for p in progress if p.get("met"))
                        total = (datetime.strptime(ch.end_date, "%Y-%m-%d") -
                                datetime.strptime(ch.start_date, "%Y-%m-%d")).days + 1
                        if msg:
                            await msg.reply_text(
                                f"🏆 <b>Challenge Update</b>\n\n"
                                f"'{ch.title}': {met_days}/{total} days",
                                parse_mode='HTML'
                            )
        except Exception as e:
            logger.error(f"⚠️ Challenge progress update failed (non-critical): {e}")
        
        # ===== PHASE 3C: Achievement System Integration =====
        # Check for newly unlocked achievements after streak update
        newly_unlocked = []  # Initialize for feature discovery hints below
        try:
            # Get updated user profile with current streak
            user = firestore_service.get_user(user_id)
            
            if user:
                # Get recent check-ins for performance achievement checks (30 days)
                recent_checkins = firestore_service.get_recent_checkins(user_id, days=30)
                
                # Check for newly unlocked achievements
                newly_unlocked = achievement_service.check_achievements(user, recent_checkins)
                
                if newly_unlocked:
                    logger.info(
                        f"🎉 User {user_id} unlocked {len(newly_unlocked)} achievement(s): "
                        f"{', '.join(newly_unlocked)}"
                    )
                    
                    # Process each newly unlocked achievement
                    for achievement_id in newly_unlocked:
                        # Unlock achievement in Firestore (with duplicate prevention)
                        achievement_service.unlock_achievement(user_id, achievement_id)
                        
                        # Generate celebration message
                        celebration_message = achievement_service.get_celebration_message(
                            achievement_id,
                            user
                        )
                        
                        # Send celebration as separate message (after check-in feedback)
                        if msg:
                            await msg.reply_text(
                                celebration_message,
                                parse_mode='HTML'
                            )
                        
                        logger.info(f"✅ Sent celebration for {achievement_id} to user {user_id}")
                else:
                    logger.debug(f"No new achievements for user {user_id}")
            
        except Exception as e:
            # Don't fail check-in if achievement system has issues
            logger.error(f"⚠️ Achievement checking failed (non-critical): {e}", exc_info=True)
        
        # ===== P4.3: Feature Discovery Hints =====
        try:
            from src.services.feature_discovery_service import feature_discovery_service
            
            # Determine which event to check based on user state
            event = None
            if user.streaks.current_streak == 7:
                event = "streak_7_days"
            elif user.streaks.current_streak == 14:
                event = "streak_14_days"
            elif user.streaks.current_streak == 21:
                event = "streak_21_days"
            elif user.streaks.current_streak == 30:
                event = "streak_30_days"
            elif user.streaks.total_checkins == 3:
                event = "after_3_checkins"
            elif newly_unlocked:
                event = "first_pattern_detected"
            
            if event:
                hint = feature_discovery_service.check_and_send_hint(
                    user=user,
                    event=event,
                    checkins=recent_checkins,
                )
                if hint:
                    if msg:
                        await msg.reply_text(hint, parse_mode='HTML')
                    # Mark as sent
                    feature_discovery_service.mark_hint_sent(user_id, event)
                    logger.info(f"💡 Hint sent to {user_id}: {event}")
        except Exception as e:
            logger.error(f"⚠️ Feature discovery hint failed (non-critical): {e}")
        
        # ===== End Achievement System Integration =====
        
        # ===== PHASE 3C DAY 4: Milestone Celebrations =====
        # Send milestone celebration if milestone was hit
        if milestone_hit:
            try:
                milestone_message = (
                    f"<b>{milestone_hit['title']}</b>\n\n"
                    f"{milestone_hit['message']}"
                )
                
                if msg:
                    await msg.reply_text(
                        milestone_message,
                        parse_mode='HTML'
                    )
                
                logger.info(
                    f"🎉 Sent milestone celebration ({streak_updates['current_streak']} days) "
                    f"to user {user_id}"
                )
                
            except Exception as e:
                # Don't fail check-in if milestone message fails
                logger.error(f"⚠️ Milestone celebration failed (non-critical): {e}", exc_info=True)
        
        # ===== End Milestone Celebrations =====
        
        # ===== PHASE D: Recovery Milestone Celebrations =====
        # If the user is in a post-reset recovery period, show recovery milestones
        # (Day 3, 7, 14, or exceeding old streak). These are SEPARATE from the
        # reset message (which shows on Day 1) and the normal milestones.
        recovery_msg = streak_updates.get('recovery_message')
        if recovery_msg and not streak_updates.get('is_reset'):
            # Recovery milestone (not the initial reset — that's shown inline above)
            try:
                if msg:
                    await msg.reply_text(
                        recovery_msg,
                        parse_mode="HTML"
                    )
                logger.info(
                    f"🔄 Sent recovery milestone for {user_id} "
                    f"(streak: {streak_updates['current_streak']})"
                )
            except Exception as e:
                logger.error(f"⚠️ Recovery milestone message failed (non-critical): {e}")
        # ===== End Recovery Milestones =====
        
        logger.info(
            f"✅ Check-in completed for {user_id}: {compliance_score}% compliance, "
            f"{streak_updates['current_streak']} day streak"
        )
        
    except Exception as e:
        logger.error(f"❌ Error completing check-in: {e}", exc_info=True)
        msg = _get_message_from_update(update)
        if msg:
            await msg.reply_text(
                "❌ Sorry, there was an error saving your check-in. "
                "Please try again or contact support."
            )


# ===== Phase 3E: Quick Check-In Completion =====

async def finish_checkin_quick(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> None:
    """
    Complete quick check-in (Phase 3E).
    
    <b>Differences from Regular Check-In:</b>
    1. Tier 1 ONLY (no Q2-Q4 data)
    2. Abbreviated AI feedback (1-2 sentences vs 3-4 paragraphs)
    3. Increment quick_checkin_count
    4. Track date in quick_checkin_used_dates
    5. Mark as quick check-in in database
    
    <b>Process:</b>
    1. Create CheckIn object (with dummy Q2-Q4 data)
    2. Calculate compliance score
    3. Update streak
    4. Store in Firestore with is_quick_checkin=True
    5. Generate abbreviated feedback
    6. Increment quick check-in counter
    7. Send feedback
    
    <b>Why Abbreviated Feedback:</b>
    - Quick check-ins are for busy days
    - User wants fast completion (~2 min total)
    - Full AI analysis requires Q2-Q4 context
    - 1-2 sentences acknowledge wins + suggest focus area
    """
    user_id = context.user_data['user_id']
    date = context.user_data.get('date') or get_checkin_date(tz="UTC")
    
    try:
        # Calculate check-in duration
        duration = int((datetime.utcnow() - context.user_data['checkin_start_time']).total_seconds())
        
        # Get Tier1NonNegotiables object (built during Q1 continuous data capture)
        tier1 = context.user_data.get('tier1')
        
        # Fallback: if using old flow (backward compatibility for in-progress check-ins)
        if tier1 is None:
            tier1_data = context.user_data.get('tier1_responses', {})
            sleep_val = tier1_data.get('sleep', False)
            training_val = tier1_data.get('training', False)
            dw_val = tier1_data.get('deepwork', False)
            sb_val = tier1_data.get('skillbuilding', False)
            
            tier1 = Tier1NonNegotiables(
                sleep=sleep_val,
                training=training_val,
                deep_work=dw_val,
                skill_building=sb_val,
                sleep_hours=7.5 if sleep_val else 5.5,
                deep_work_hours=2.5 if dw_val else 0.5,
                skill_building_hours=2.5 if sb_val else 0.5,
                training_intensity='moderate' if training_val else 'rest',
                is_rest_day=not training_val,
                zero_porn=tier1_data.get('porn', False),
                boundaries=tier1_data.get('boundaries', False),
                data_quality='migrated',
            )
        
        # Create CheckInResponses with dummy data (Q2-Q5 skipped)
        responses = CheckInResponses(
            challenges=context.user_data['challenges'],
            rating=context.user_data['rating'],
            rating_reason=context.user_data['rating_reason'],
            tomorrow_priority=context.user_data['tomorrow_priority'],
            tomorrow_obstacle=context.user_data['tomorrow_obstacle'],
            energy_rating=context.user_data.get('energy_rating'),
            mood_rating=context.user_data.get('mood_rating'),
        )
        
        # Load committed tasks for today
        from src.services.task_service import task_service
        task_list = task_service.get_daily_tasks(user_id, date)
        committed_tasks = task_list.tasks if (task_list and task_list.committed) else None

        # Calculate compliance score
        compliance_score = calculate_compliance_score(tier1, committed_tasks)
        
        # Create DailyCheckIn object with is_quick_checkin=True
        checkin = DailyCheckIn(
            date=date,
            user_id=user_id,
            mode=context.user_data['mode'],
            tier1_non_negotiables=tier1,
            responses=responses,
            compliance_score=compliance_score,
            completed_at=datetime.utcnow(),
            duration_seconds=duration,
            is_quick_checkin=True,  # Phase 3E: Mark as quick check-in
            committed_tasks=committed_tasks
        )
        
        # Store check-in + update streak ATOMICALLY (same transaction fix as full check-in)
        user = firestore_service.get_user(user_id)
        streak_updates = update_streak_data(
            current_streak=user.streaks.current_streak,
            longest_streak=user.streaks.longest_streak,
            total_checkins=user.streaks.total_checkins,
            last_checkin_date=user.streaks.last_checkin_date,
            new_checkin_date=date,
            # Phase D: Pass recovery tracking fields for reset detection
            streak_before_reset=getattr(user.streaks, 'streak_before_reset', 0) or 0,
            last_reset_date=getattr(user.streaks, 'last_reset_date', None)
        )
        
        firestore_service.store_checkin_with_streak_update(user_id, checkin, streak_updates)
        
        # Phase 3E: Increment quick check-in counter
        new_count = user.quick_checkin_count + 1
        updated_dates = user.quick_checkin_used_dates + [date]
        
        firestore_service.update_user(user_id, {
            "quick_checkin_count": new_count,
            "quick_checkin_used_dates": updated_dates
        })
        
        logger.info(f"⚡ Quick check-in counter incremented for {user_id}: {new_count}/2")
        
        # Generate abbreviated AI feedback (1-2 sentences)
        try:
            checkin_agent = get_checkin_agent(settings.gcp_project_id)
            
            # Generate abbreviated feedback
            ai_feedback = await checkin_agent.generate_abbreviated_feedback(
                user_id=user_id,
                tier1=tier1,
                compliance_score=compliance_score,
                current_streak=streak_updates['current_streak']
            )
            
        except Exception as e:
            logger.error(f"Abbreviated AI feedback failed, using fallback: {e}")
            
            # Fallback abbreviated feedback
            wins = []
            if tier1.sleep:
                wins.append("sleep")
            if tier1.training:
                wins.append("training")
            if tier1.boundaries:
                wins.append("boundaries")
            
            if wins:
                ai_feedback = f"Good job on {', '.join(wins[:2])}! "
            else:
                ai_feedback = "Check-in recorded. "
            
            # Suggest focus area
            if not tier1.deep_work:
                ai_feedback += "Focus on deep work tomorrow."
            elif not tier1.skill_building:
                ai_feedback += "Don't skip skill building tomorrow."
            else:
                ai_feedback += "Keep up the momentum!"
        
        # Build final message
        feedback_parts = []
        feedback_parts.append("⚡ <b>Quick Check-In Complete!</b>\n")
        feedback_parts.append(f"📊 Compliance: {compliance_score}%")
        
        # Phase D: Show recovery message on reset, normal streak otherwise
        if streak_updates.get('is_reset') and streak_updates.get('recovery_message'):
            feedback_parts.append(f"\n{streak_updates['recovery_message']}")
        else:
            feedback_parts.append(f"🔥 Streak: {streak_updates['current_streak']} days")
        
        feedback_parts.append(f"\n{ai_feedback}")
        feedback_parts.append(f"\n━━━━━━━━━━━━━━━━━━━━")
        feedback_parts.append(f"\n<b>Quick Check-Ins This Week:</b> {new_count}/2")
        feedback_parts.append(f"Use /checkin for full check-in next time.")
        
        final_message = "\n".join(feedback_parts)
        
        # Get the query object from update (since this was triggered by callback query)
        query = update.callback_query
        if query:
            await query.message.reply_text(final_message, parse_mode='HTML')
        else:
            await update.message.reply_text(final_message, parse_mode='HTML')

        # ===== P4.2: Streak Recovery Ritual =====
        if streak_updates.get('is_reset'):
            try:
                from src.services.streak_recovery_service import send_recovery_ritual
                await send_recovery_ritual(
                    bot=context.bot,
                    user=user,
                    previous_streak=streak_updates.get('streak_before_reset', 0),
                )
            except Exception as e:
                logger.error(f"⚠️ Recovery ritual failed (non-critical): {e}")

        partner_notification = await send_partner_checkin_notification(
            bot=context.bot,
            sender=user,
            tier1=tier1,
            date=date,
            fallback_sender_name=update.effective_user.first_name,
        )
        target_message = query.message if query else update.message
        await _notify_sender_if_partner_delivery_failed(target_message, partner_notification)
        
        # ===== P2.2: Goal Progress Integration (Quick Check-In) =====
        try:
            from src.services.goal_service import goal_service
            
            goal_updates = goal_service.update_progress_from_checkin(checkin)
            
            if goal_updates:
                goal_messages = []
                for goal, milestone in goal_updates:
                    if milestone == "100%":
                        goal_messages.append(
                            f"🏆 <b>Goal Completed!</b>\n"
                            f"'{goal.title}' — {len(goal.progress)}/{goal.target_days} days!"
                        )
                    elif milestone in ("50%", "75%"):
                        goal_messages.append(
                            f"🎯 <b>{milestone} Milestone!</b>\n"
                            f"'{goal.title}' — keep going!"
                        )
                
                if goal_messages:
                    await target_message.reply_text(
                        "\n\n".join(goal_messages),
                        parse_mode='HTML'
                    )
        except Exception as e:
            logger.error(f"⚠️ Goal progress update failed in quick check-in (non-critical): {e}")
        
        # ===== P2.3: Challenge Progress Integration (Quick Check-In) =====
        try:
            from src.services.challenge_service import challenge_service
            updated_challenges = challenge_service.update_progress_from_checkin(checkin)
            if updated_challenges:
                for ch in updated_challenges:
                    winner = challenge_service.check_completion(ch)
                    if winner:
                        if winner == user_id:
                            await target_message.reply_text(
                                f"🏆 <b>You Won the Challenge!</b>\n\n"
                                f"'{ch.title}' — victory is yours! 🔥",
                                parse_mode='HTML'
                            )
                        elif winner == ch.partner_id:
                            await target_message.reply_text(
                                f"😤 <b>Challenge Lost</b>\n\n"
                                f"'{ch.title}' — your partner edged you out. Rematch?",
                                parse_mode='HTML'
                            )
                        else:
                            await target_message.reply_text(
                                f"🤝 <b>Challenge Tie!</b>\n\n"
                                f"'{ch.title}' — dead even. Rematch?",
                                parse_mode='HTML'
                            )
                    else:
                        progress = ch.progress.get(user_id, [])
                        met_days = sum(1 for p in progress if p.get("met"))
                        total = (datetime.strptime(ch.end_date, "%Y-%m-%d") -
                                datetime.strptime(ch.start_date, "%Y-%m-%d")).days + 1
                        await target_message.reply_text(
                            f"🏆 <b>Challenge Update</b>\n\n"
                            f"'{ch.title}': {met_days}/{total} days",
                            parse_mode='HTML'
                        )
        except Exception as e:
            logger.error(f"⚠️ Challenge progress update failed in quick check-in (non-critical): {e}")
        
        # ===== P4.3: Feature Discovery Hints (Quick Check-In) =====
        try:
            from src.services.feature_discovery_service import feature_discovery_service
            
            # Re-fetch user for current streak data
            user_quick = firestore_service.get_user(user_id)
            if user_quick:
                event = None
                if user_quick.streaks.current_streak == 7:
                    event = "streak_7_days"
                elif user_quick.streaks.current_streak == 14:
                    event = "streak_14_days"
                elif user_quick.streaks.current_streak == 21:
                    event = "streak_21_days"
                elif user_quick.streaks.current_streak == 30:
                    event = "streak_30_days"
                
                if event:
                    hint = feature_discovery_service.check_and_send_hint(
                        user=user_quick,
                        event=event,
                        checkins=[checkin],  # Quick check-in only has current checkin
                    )
                    if hint:
                        await target_message.reply_text(hint, parse_mode='HTML')
                        feature_discovery_service.mark_hint_sent(user_id, event)
                        logger.info(f"💡 Hint sent to {user_id} (quick): {event}")
        except Exception as e:
            logger.error(f"⚠️ Feature discovery hint failed in quick check-in (non-critical): {e}")
        
        logger.info(
            f"⚡ Quick check-in completed for {user_id}: {compliance_score}% compliance, "
            f"{streak_updates['current_streak']} day streak, count: {new_count}/2"
        )
        
    except Exception as e:
        logger.error(f"❌ Error completing quick check-in: {e}", exc_info=True)
        if update.callback_query:
            await update.callback_query.message.reply_text(
                "❌ Sorry, there was an error saving your quick check-in. "
                "Please try /quickcheckin again or use /checkin for full check-in."
            )
        else:
            await update.message.reply_text(
                "❌ Sorry, there was an error saving your quick check-in. "
                "Please try /quickcheckin again or use /checkin for full check-in."
            )


# ===== Cancel/Timeout Handlers =====

async def cancel_checkin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle /cancel command during check-in.
    
    Allows user to abort check-in.
    """
    await update.message.reply_text(
        "Check-in cancelled. You can start again with /checkin whenever you're ready."
    )
    
    logger.info(f"✅ Check-in cancelled by user {update.effective_user.id}")
    return ConversationHandler.END


async def checkin_timeout(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle conversation timeout (15 minutes of inactivity).
    
    Automatically cancels check-in.
    """
    await update.message.reply_text(
        "⏰ Check-in timed out due to inactivity.\n\n"
        "You can start a new check-in anytime with /checkin."
    )
    
    logger.info(f"✅ Check-in timed out for user {update.effective_user.id}")
    return ConversationHandler.END


# ===== Conversation Handler Factory =====

def create_checkin_conversation_handler() -> ConversationHandler:
    """
    Create and configure the check-in conversation handler.
    
    Phase 3E: Added /quickcheckin as entry point
    
    Returns:
        ConversationHandler: Configured conversation handler
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler("checkin", start_checkin),
            CommandHandler("quickcheckin", start_checkin)  # Phase 3E: Quick check-in entry
        ],
        states={
            Q1_TIER1: [
                CallbackQueryHandler(handle_tier1_response)
            ],
            Q2_ALIGNMENT_RATING: [
                CallbackQueryHandler(handle_alignment_rating_callback, pattern="^align_")
            ],
            Q3_ENERGY_MOOD: [
                CallbackQueryHandler(handle_energy_callback, pattern="^energy_"),
                CallbackQueryHandler(handle_mood_callback, pattern="^mood_"),
            ],
            Q4_REFLECTION_NOTE: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_reflection_response),
                MessageHandler(filters.VOICE, handle_voice_reflection),
                CallbackQueryHandler(handle_reflection_skip_callback, pattern="^ref_")
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_checkin)
        ],
        conversation_timeout=900,  # 15 minutes
        name="checkin_conversation",
        block=True  # CRITICAL: Block other handlers when conversation is active
    )
