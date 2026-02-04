"""
Check-In Conversation Handler
=============================

Multi-turn conversation state machine for daily check-ins.

Flow:
    /checkin → Q1 (Tier 1) → Q2 (Challenges) → Q3 (Rating) → Q4 (Tomorrow) → FINISH
    
States:
- Q1_TIER1: Ask about 5 Tier 1 non-negotiables with Y/N buttons
- Q2_CHALLENGES: Free text about today's challenges (10-500 chars)
- Q3_RATING: 1-10 rating + reason (validation: must start with number)
- Q4_TOMORROW: Tomorrow's priority + obstacle (10-500 chars each)
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
from src.models.schemas import (
    DailyCheckIn,
    Tier1NonNegotiables,
    CheckInResponses
)
from src.utils.timezone_utils import get_current_date_ist, get_checkin_date
from src.utils.compliance import calculate_compliance_score, format_compliance_message
from src.utils.streak import update_streak_data, format_streak_message
from src.agents.checkin_agent import get_checkin_agent
from src.config import settings

logger = logging.getLogger(__name__)


# ===== Conversation States =====
Q1_TIER1, Q2_CHALLENGES, Q3_RATING, Q4_TOMORROW = range(4)


# ===== Entry Point =====

async def start_checkin(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Entry point for /checkin command.
    
    Checks if:
    1. User exists in database
    2. User hasn't already checked in today
    
    Then starts conversation with Question 1.
    
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
    
    # Check if already checked in today (Phase 3A: Use 3 AM cutoff logic)
    checkin_date = get_checkin_date()  # Before 3 AM = previous day, after = current day
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
    
    # Start Question 1: Tier 1 non-negotiables
    await ask_tier1_question(update.message, context)
    
    logger.info(f"✅ Check-in started for {user_id}")
    return Q1_TIER1


async def ask_tier1_question(message, context):
    """
    Ask Question 1: Tier 1 non-negotiables with inline keyboard.
    
    5 items to answer (Y/N):
    1. Sleep (7+ hours)
    2. Training (workout or rest day)
    3. Deep Work (2+ hours)
    4. Zero Porn
    5. Boundaries
    """
    # Get current mode for context
    mode = context.user_data.get('mode', 'maintenance')
    training_target = "6x/week" if mode == "optimization" else "4x/week"
    
    question_text = (
        "**📋 Daily Check-In - Question 1/4**\n\n"
        "**Constitution Compliance** (Tier 1 Non-Negotiables):\n\n"
        "Did you complete the following today?\n\n"
        "• 💤 **Sleep:** 7+ hours last night?\n"
        f"• 💪 **Training:** Workout OR rest day? ({training_target})\n"
        "• 🧠 **Deep Work:** 2+ hours focused work/study?\n"
        "• 🚫 **Zero Porn:** No consumption today?\n"
        "• 🛡️ **Boundaries:** No toxic interactions?\n\n"
        "Click the buttons below to answer:"
    )
    
    # Create inline keyboard with buttons
    keyboard = [
        [
            InlineKeyboardButton("💤 Sleep: YES", callback_data="sleep_yes"),
            InlineKeyboardButton("💤 Sleep: NO", callback_data="sleep_no")
        ],
        [
            InlineKeyboardButton("💪 Training: YES", callback_data="training_yes"),
            InlineKeyboardButton("💪 Training: NO", callback_data="training_no")
        ],
        [
            InlineKeyboardButton("🧠 Deep Work: YES", callback_data="deepwork_yes"),
            InlineKeyboardButton("🧠 Deep Work: NO", callback_data="deepwork_no")
        ],
        [
            InlineKeyboardButton("🚫 Zero Porn: YES", callback_data="porn_yes"),
            InlineKeyboardButton("🚫 Zero Porn: NO", callback_data="porn_no")
        ],
        [
            InlineKeyboardButton("🛡️ Boundaries: YES", callback_data="boundaries_yes"),
            InlineKeyboardButton("🛡️ Boundaries: NO", callback_data="boundaries_no")
        ]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await message.reply_text(question_text, reply_markup=reply_markup)


# ===== State Q1: Tier 1 Non-Negotiables =====

async def handle_tier1_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle button presses for Tier 1 responses.
    
    Stores responses in context.user_data and tracks which items are answered.
    When all 5 items answered, moves to Q2.
    
    Returns:
        int: Q1_TIER1 (still answering) or Q2_CHALLENGES (all answered)
    """
    query = update.callback_query
    await query.answer()  # Acknowledge button press
    
    # Parse callback data (e.g., "sleep_yes" → sleep: True)
    item, response = query.data.rsplit('_', 1)
    response_bool = (response == "yes")
    
    # Store response
    if 'tier1_responses' not in context.user_data:
        context.user_data['tier1_responses'] = {}
    
    context.user_data['tier1_responses'][item] = response_bool
    
    # Map item names to user-friendly labels
    item_labels = {
        'sleep': '💤 Sleep',
        'training': '💪 Training',
        'deepwork': '🧠 Deep Work',
        'porn': '🚫 Zero Porn',
        'boundaries': '🛡️ Boundaries'
    }
    
    # Show what was selected
    response_text = "✅ YES" if response_bool else "❌ NO"
    await query.edit_message_reply_markup(reply_markup=None)  # Remove buttons
    await query.message.reply_text(
        f"{item_labels.get(item, item.title())}: {response_text}"
    )
    
    # Check if all 5 items answered
    required_items = {'sleep', 'training', 'deepwork', 'porn', 'boundaries'}
    answered_items = set(context.user_data['tier1_responses'].keys())
    
    if required_items.issubset(answered_items):
        # All answered → move to Q2
        await query.message.reply_text(
            "**📋 Question 2/4**\n\n"
            "**Challenges & Handling:**\n"
            "What challenges did you face today? How did you handle them?\n\n"
            "📝 Type your response (10-500 characters).\n\n"
            "_Example: 'Urge to watch porn around 10 PM. Went for a walk and texted friend instead.'_"
        )
        return Q2_CHALLENGES
    
    # Still need more answers
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
        "**📋 Question 3/4**\n\n"
        "**Self-Rating & Reflection:**\n"
        "Rate today 1-10 on constitution alignment. Why that score?\n\n"
        "📝 Format: Start with number (1-10), then explain.\n\n"
        "_Example: '8 - Solid day overall. Missed one study hour but otherwise strong.'_"
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
        "**📋 Question 4/4**\n\n"
        "**Tomorrow's Plan:**\n"
        "1. What's tomorrow's #1 priority?\n"
        "2. What's the biggest potential obstacle?\n\n"
        "📝 Format: Priority | Obstacle\n\n"
        "_Example: 'Priority: Complete 3 LeetCode problems. Obstacle: Late evening meeting might drain energy.'_"
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
    date = context.user_data['date']
    
    try:
        # Calculate check-in duration
        duration = int((datetime.utcnow() - context.user_data['checkin_start_time']).total_seconds())
        
        # Create Tier1NonNegotiables object
        tier1_data = context.user_data['tier1_responses']
        tier1 = Tier1NonNegotiables(
            sleep=tier1_data.get('sleep', False),
            training=tier1_data.get('training', False),
            deep_work=tier1_data.get('deepwork', False),
            zero_porn=tier1_data.get('porn', False),
            boundaries=tier1_data.get('boundaries', False)
        )
        
        # Create CheckInResponses object
        responses = CheckInResponses(
            challenges=context.user_data['challenges'],
            rating=context.user_data['rating'],
            rating_reason=context.user_data['rating_reason'],
            tomorrow_priority=context.user_data['tomorrow_priority'],
            tomorrow_obstacle=context.user_data['tomorrow_obstacle']
        )
        
        # Calculate compliance score
        compliance_score = calculate_compliance_score(tier1)
        
        # Create DailyCheckIn object
        checkin = DailyCheckIn(
            date=date,
            user_id=user_id,
            mode=context.user_data['mode'],
            tier1_non_negotiables=tier1,
            responses=responses,
            compliance_score=compliance_score,
            completed_at=datetime.utcnow(),
            duration_seconds=duration
        )
        
        # Store check-in
        firestore_service.store_checkin(user_id, checkin)
        
        # Update streak
        user = firestore_service.get_user(user_id)
        streak_updates = update_streak_data(
            current_streak=user.streaks.current_streak,
            longest_streak=user.streaks.longest_streak,
            total_checkins=user.streaks.total_checkins,
            last_checkin_date=user.streaks.last_checkin_date,
            new_checkin_date=date
        )
        
        firestore_service.update_user_streak(user_id, streak_updates)
        
        # Generate AI-powered feedback message
        is_new_record = (
            streak_updates['current_streak'] > streak_updates['longest_streak'] - 1
            and streak_updates['current_streak'] > 1
        )
        
        try:
            # Get CheckIn Agent
            checkin_agent = get_checkin_agent(settings.gcp_project_id)
            
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
                tomorrow_obstacle=context.user_data['tomorrow_obstacle']
            )
            
            # Build final message with header and AI feedback
            feedback_parts = []
            feedback_parts.append("🎉 **Check-In Complete!**\n")
            feedback_parts.append(f"📊 Compliance: {compliance_score}%")
            feedback_parts.append(f"🔥 Streak: {streak_updates['current_streak']} days")
            
            if is_new_record:
                feedback_parts.append("🏆 **NEW PERSONAL RECORD!**")
            
            feedback_parts.append(f"📈 Total check-ins: {streak_updates['total_checkins']}")
            feedback_parts.append(f"\n---\n\n{ai_feedback}")
            feedback_parts.append(f"\n---\n\n🎯 See you tomorrow at 9 PM!")
            
            final_message = "\n".join(feedback_parts)
            
        except Exception as e:
            logger.error(f"AI feedback generation failed, using fallback: {e}")
            
            # Fallback to Phase 1 hardcoded feedback
            feedback_parts = []
            feedback_parts.append("🎉 **Check-In Complete!**\n")
            feedback_parts.append(f"📊 Compliance: {compliance_score}%")
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
            feedback_parts.append(f"\n🎯 See you tomorrow!")
            
            final_message = "\n".join(feedback_parts)
        
        await update.message.reply_text(final_message)
        
        logger.info(
            f"✅ Check-in completed for {user_id}: {compliance_score}% compliance, "
            f"{streak_updates['current_streak']} day streak"
        )
        
    except Exception as e:
        logger.error(f"❌ Error completing check-in: {e}", exc_info=True)
        await update.message.reply_text(
            "❌ Sorry, there was an error saving your check-in. "
            "Please try again or contact support."
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
    
    Returns:
        ConversationHandler: Configured conversation handler
    """
    return ConversationHandler(
        entry_points=[
            CommandHandler("checkin", start_checkin)
        ],
        states={
            Q1_TIER1: [
                CallbackQueryHandler(handle_tier1_response)
            ],
            Q2_CHALLENGES: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_challenges_response)
            ],
            Q3_RATING: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_rating_response)
            ],
            Q4_TOMORROW: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tomorrow_response)
            ]
        },
        fallbacks=[
            CommandHandler("cancel", cancel_checkin)
        ],
        conversation_timeout=900,  # 15 minutes
        name="checkin_conversation"
    )
