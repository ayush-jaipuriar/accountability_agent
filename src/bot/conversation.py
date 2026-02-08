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
from src.config import settings

logger = logging.getLogger(__name__)


# ===== Conversation States =====
Q1_TIER1, Q2_CHALLENGES, Q3_RATING, Q4_TOMORROW = range(4)


# ===== Phase 3D: Career Mode Adaptive Questions =====

def get_skill_building_question(career_mode: str) -> dict:
    """
    Get skill building question adapted to user's career mode.
    
    **Design Pattern: Strategy Pattern**
    - Same interface (returns consistent dict structure)
    - Different behavior based on state (career_mode)
    - Clean separation of concerns
    
    **Why This Matters:**
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
            "question": "📚 **Skill Building:** 2+ hours today?",
            "label": "📚 Skill Building",
            "description": "(LeetCode, system design, AI/ML upskilling, courses, projects)"
        }
    
    elif career_mode == "job_searching":
        return {
            "question": "💼 **Job Search Progress:** Made progress today?",
            "label": "💼 Job Search",
            "description": "(Applications, interviews, LeetCode, networking)"
        }
    
    elif career_mode == "employed":
        return {
            "question": "🎯 **Career Progress:** Worked toward promotion/raise?",
            "label": "🎯 Career",
            "description": "(High-impact work, skill development, visibility projects)"
        }
    
    else:
        # Default fallback (defensive programming)
        logger.warning(f"⚠️ Unknown career_mode: {career_mode}, using default")
        return {
            "question": "📚 **Skill Building:** 2+ hours today?",
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
    
    **Process:**
    1. Check if user exists
    2. Check if already checked in today
    3. If /quickcheckin: Check weekly limit (2/week)
    4. Initialize conversation data
    5. Start Question 1 (Tier 1)
    
    **Phase 3E Quick Check-In:**
    - /quickcheckin triggers Tier 1-only flow (skip Q2-Q4)
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
            f"❌ **Quick Check-In Limit Reached**\n\n"
            f"You've used both quick check-ins this week (max 2/week):\n\n"
            f"{history_text}\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Use /checkin for full check-in.**\n\n"
            f"🔄 Limit resets: {reset_date} at 12:00 AM IST\n\n"
            f"💡 **Why the limit?**\n"
            f"Full check-ins provide better insights and accountability.\n"
            f"Quick check-ins are for genuinely busy days only.",
            parse_mode="Markdown"
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
    
    # Phase 3E: Set quick check-in flag if /quickcheckin was used
    if is_quick_checkin:
        context.user_data['checkin_type'] = 'quick'
        
        # Show quick check-in intro
        from src.utils.timezone_utils import get_next_monday
        remaining = 2 - user.quick_checkin_count
        reset_date = get_next_monday(format_string="%A, %B %d")
        
        await update.message.reply_text(
            f"⚡ **Quick Check-In Mode**\n\n"
            f"Complete Tier 1 in ~2 minutes (6 questions only)\n\n"
            f"━━━━━━━━━━━━━━━━━━━━\n\n"
            f"**Available This Week:** {remaining}/2 quick check-ins\n"
            f"**Resets:** {reset_date} at 12:00 AM IST\n\n"
            f"💡 Quick check-ins count toward your streak but provide\n"
            f"abbreviated feedback. Use /checkin for full insights.\n\n"
            f"Let's go! Starting Tier 1 questions...",
            parse_mode="Markdown"
        )
    else:
        context.user_data['checkin_type'] = 'full'
    
    # Start Question 1: Tier 1 non-negotiables
    await ask_tier1_question(update.message, context)
    
    logger_msg = "⚡ Quick check-in" if is_quick_checkin else "✅ Full check-in"
    logger.info(f"{logger_msg} started for {user_id}")
    return Q1_TIER1


async def ask_tier1_question(message, context):
    """
    Ask Question 1: Tier 1 non-negotiables with inline keyboard.
    
    **Phase 3D Expansion: 5 items → 6 items**
    
    6 items to answer (Y/N):
    1. Sleep (7+ hours)
    2. Training (workout or rest day)
    3. Deep Work (2+ hours)
    4. Skill Building (2+ hours) - **NEW in Phase 3D** - Adapts to career mode
    5. Zero Porn
    6. Boundaries
    
    **Why 6 Items?**
    - Constitution mandates daily skill building (LeetCode, system design, AI/ML)
    - June 2026 career goal (₹28-42 LPA) requires tracking career progress
    - Skill building is different from general deep work (career-specific learning)
    
    **Adaptive Question Logic:**
    - Skill building question adapts based on user's career_mode
    - skill_building mode: "Did you do 2+ hours skill building?"
    - job_searching mode: "Did you make job search progress?"
    - employed mode: "Did you work toward promotion/raise?"
    """
    # Get user to determine career mode
    user_id = context.user_data.get('user_id')
    user = firestore_service.get_user(user_id)
    
    # Get current mode for training target
    mode = context.user_data.get('mode', 'maintenance')
    training_target = "6x/week" if mode == "optimization" else "4x/week"
    
    # Get adaptive skill building question
    career_mode = user.career_mode if user else "skill_building"
    skill_q = get_skill_building_question(career_mode)
    
    question_text = (
        "**📋 Daily Check-In - Question 1/4**\n\n"
        "**Constitution Compliance** (Tier 1 Non-Negotiables):\n\n"
        "Did you complete the following today?\n\n"
        "• 💤 **Sleep:** 7+ hours last night?\n"
        f"• 💪 **Training:** Workout OR rest day? ({training_target})\n"
        "• 🧠 **Deep Work:** 2+ hours focused work/study?\n"
        f"• {skill_q['question']} {skill_q['description']}\n"
        "• 🚫 **Zero Porn:** No consumption today?\n"
        "• 🛡️ **Boundaries:** No toxic interactions?\n\n"
        "Click the buttons below to answer:"
    )
    
    # Create inline keyboard with buttons (now 6 items)
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
            # Phase 3D: New skill building button (adapts label to career mode)
            InlineKeyboardButton(f"{skill_q['label']}: YES", callback_data="skillbuilding_yes"),
            InlineKeyboardButton(f"{skill_q['label']}: NO", callback_data="skillbuilding_no")
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
    await message.reply_text(question_text, reply_markup=reply_markup, parse_mode="Markdown")


# ===== State Q1: Tier 1 Non-Negotiables =====

async def handle_tier1_response(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
) -> int:
    """
    Handle button presses for Tier 1 responses, including Undo.
    
    Stores responses in context.user_data and tracks which items are answered.
    When all 6 items answered, moves to Q2.
    
    Undo Feature:
    - After each answer, a confirmation message with an "Undo Last" button is shown
    - Pressing "Undo Last" removes the most recently answered item
    - User can then re-answer that item via the original buttons
    - Tracks answer order in context.user_data['tier1_answer_order'] (list)
    
    Returns:
        int: Q1_TIER1 (still answering) or Q2_CHALLENGES (all answered)
    """
    query = update.callback_query
    await query.answer()  # Acknowledge button press
    
    # Map item names to user-friendly labels
    item_labels = {
        'sleep': '💤 Sleep',
        'training': '💪 Training',
        'deepwork': '🧠 Deep Work',
        'skillbuilding': '📚 Skill Building',
        'porn': '🚫 Zero Porn',
        'boundaries': '🛡️ Boundaries'
    }
    
    # Initialize data structures if needed
    if 'tier1_responses' not in context.user_data:
        context.user_data['tier1_responses'] = {}
    if 'tier1_answer_order' not in context.user_data:
        context.user_data['tier1_answer_order'] = []
    
    # ===== Handle Undo =====
    if query.data == "tier1_undo":
        answer_order = context.user_data.get('tier1_answer_order', [])
        
        if not answer_order:
            await query.message.reply_text("Nothing to undo yet!")
            return Q1_TIER1
        
        # Remove the last answered item
        last_item = answer_order.pop()
        old_value = context.user_data['tier1_responses'].pop(last_item, None)
        old_text = "YES" if old_value else "NO"
        
        # Remove the undo button from the confirmation message
        await query.edit_message_reply_markup(reply_markup=None)
        
        remaining = 6 - len(context.user_data['tier1_responses'])
        await query.message.reply_text(
            f"↩️ Undone: {item_labels.get(last_item, last_item)} (was {old_text})\n"
            f"Please re-answer it using the buttons above.\n"
            f"({remaining} item{'s' if remaining != 1 else ''} remaining)"
        )
        
        logger.info(f"↩️ User {context.user_data.get('user_id')} undid {last_item}")
        return Q1_TIER1
    
    # ===== Handle Normal Tier 1 Answer =====
    # Parse callback data (e.g., "sleep_yes" → sleep: True)
    item, response = query.data.rsplit('_', 1)
    response_bool = (response == "yes")
    
    # Store response and track order
    context.user_data['tier1_responses'][item] = response_bool
    
    # Track order: if item was already in order (re-answer after undo), remove old position
    answer_order = context.user_data['tier1_answer_order']
    if item in answer_order:
        answer_order.remove(item)
    answer_order.append(item)
    
    # Show what was selected, with Undo button
    response_text = "✅ YES" if response_bool else "❌ NO"
    
    undo_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("↩️ Undo Last", callback_data="tier1_undo")
    ]])
    
    await query.message.reply_text(
        f"{item_labels.get(item, item.title())}: {response_text}",
        reply_markup=undo_keyboard
    )
    
    # Check if all 6 items answered (Phase 3D: was 5, now 6)
    required_items = {'sleep', 'training', 'deepwork', 'skillbuilding', 'porn', 'boundaries'}
    answered_items = set(context.user_data['tier1_responses'].keys())
    
    if required_items.issubset(answered_items):
        # All answered → Remove buttons from original question
        await query.edit_message_reply_markup(reply_markup=None)
        
        # Phase 3E: Check if this is a quick check-in
        is_quick_checkin = context.user_data.get('checkin_type') == 'quick'
        
        if is_quick_checkin:
            # Quick check-in: Skip Q2-Q4 and finish immediately
            await query.message.reply_text(
                "⚡ **Quick Check-In Complete!**\n\n"
                "Processing Tier 1 responses and generating feedback...",
                parse_mode="Markdown"
            )
            
            # Set dummy values for Q2-Q4 (required by finish_checkin)
            context.user_data['challenges'] = "Quick check-in (Q2-Q4 skipped)"
            context.user_data['rating'] = 7  # Neutral rating
            context.user_data['rating_reason'] = "Quick check-in mode"
            context.user_data['tomorrow_priority'] = "Continue daily check-ins"
            context.user_data['tomorrow_obstacle'] = "None identified"
            
            # Finish check-in
            await finish_checkin_quick(update, context)
            return ConversationHandler.END
        else:
            # Normal check-in: Move to Q2
            await query.message.reply_text(
                "📋 Question 2/4\n\n"
                "Challenges & Handling:\n"
                "What challenges did you face today? How did you handle them?\n\n"
                "📝 Type your response (10-500 characters).\n\n"
                "Example: 'Urge to watch porn around 10 PM. Went for a walk and texted friend instead.'",
                parse_mode=None  # No markdown formatting
            )
            return Q2_CHALLENGES
    
    # Still need more answers - keep buttons visible
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
        "_Example: '8 - Solid day overall. Missed one study hour but otherwise strong.'_",
        parse_mode="Markdown"
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
        "_Example: 'Priority: Complete 3 LeetCode problems. Obstacle: Late evening meeting might drain energy.'_",
        parse_mode="Markdown"
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
        
        # Create Tier1NonNegotiables object (Phase 3D: Now 6 items)
        tier1_data = context.user_data['tier1_responses']
        tier1 = Tier1NonNegotiables(
            sleep=tier1_data.get('sleep', False),
            training=tier1_data.get('training', False),
            deep_work=tier1_data.get('deepwork', False),
            skill_building=tier1_data.get('skillbuilding', False),  # Phase 3D: New field
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
            
            # Phase D: Show recovery message on reset, normal streak otherwise
            if streak_updates.get('is_reset') and streak_updates.get('recovery_message'):
                feedback_parts.append(f"\n{streak_updates['recovery_message']}")
            else:
                feedback_parts.append(f"🔥 Streak: {streak_updates['current_streak']} days")
            
            if is_new_record:
                feedback_parts.append("🏆 **NEW PERSONAL RECORD!**")
            
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
            
            feedback_parts.append(f"\n---\n\n🎯 See you tomorrow at 9 PM!")
            
            final_message = "\n".join(feedback_parts)
            
        except Exception as e:
            logger.error(f"AI feedback generation failed, using fallback: {e}")
            
            # Fallback to Phase 1 hardcoded feedback
            feedback_parts = []
            feedback_parts.append("🎉 **Check-In Complete!**\n")
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
        
        await update.message.reply_text(final_message, parse_mode="Markdown")
        
        # ===== PHASE 3C: Achievement System Integration =====
        # Check for newly unlocked achievements after streak update
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
                        await update.message.reply_text(
                            celebration_message,
                            parse_mode="Markdown"
                        )
                        
                        logger.info(f"✅ Sent celebration for {achievement_id} to user {user_id}")
                else:
                    logger.debug(f"No new achievements for user {user_id}")
            
        except Exception as e:
            # Don't fail check-in if achievement system has issues
            logger.error(f"⚠️ Achievement checking failed (non-critical): {e}", exc_info=True)
        
        # ===== End Achievement System Integration =====
        
        # ===== PHASE 3C DAY 4: Milestone Celebrations =====
        # Send milestone celebration if milestone was hit
        if milestone_hit:
            try:
                milestone_message = (
                    f"**{milestone_hit['title']}**\n\n"
                    f"{milestone_hit['message']}"
                )
                
                await update.message.reply_text(
                    milestone_message,
                    parse_mode="Markdown"
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
                await update.message.reply_text(
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
        await update.message.reply_text(
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
    
    **Differences from Regular Check-In:**
    1. Tier 1 ONLY (no Q2-Q4 data)
    2. Abbreviated AI feedback (1-2 sentences vs 3-4 paragraphs)
    3. Increment quick_checkin_count
    4. Track date in quick_checkin_used_dates
    5. Mark as quick check-in in database
    
    **Process:**
    1. Create CheckIn object (with dummy Q2-Q4 data)
    2. Calculate compliance score
    3. Update streak
    4. Store in Firestore with is_quick_checkin=True
    5. Generate abbreviated feedback
    6. Increment quick check-in counter
    7. Send feedback
    
    **Why Abbreviated Feedback:**
    - Quick check-ins are for busy days
    - User wants fast completion (~2 min total)
    - Full AI analysis requires Q2-Q4 context
    - 1-2 sentences acknowledge wins + suggest focus area
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
            skill_building=tier1_data.get('skillbuilding', False),
            zero_porn=tier1_data.get('porn', False),
            boundaries=tier1_data.get('boundaries', False)
        )
        
        # Create CheckInResponses with dummy data (Q2-Q4 skipped)
        responses = CheckInResponses(
            challenges=context.user_data['challenges'],
            rating=context.user_data['rating'],
            rating_reason=context.user_data['rating_reason'],
            tomorrow_priority=context.user_data['tomorrow_priority'],
            tomorrow_obstacle=context.user_data['tomorrow_obstacle']
        )
        
        # Calculate compliance score
        compliance_score = calculate_compliance_score(tier1)
        
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
            is_quick_checkin=True  # Phase 3E: Mark as quick check-in
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
        feedback_parts.append("⚡ **Quick Check-In Complete!**\n")
        feedback_parts.append(f"📊 Compliance: {compliance_score}%")
        
        # Phase D: Show recovery message on reset, normal streak otherwise
        if streak_updates.get('is_reset') and streak_updates.get('recovery_message'):
            feedback_parts.append(f"\n{streak_updates['recovery_message']}")
        else:
            feedback_parts.append(f"🔥 Streak: {streak_updates['current_streak']} days")
        
        feedback_parts.append(f"\n{ai_feedback}")
        feedback_parts.append(f"\n━━━━━━━━━━━━━━━━━━━━")
        feedback_parts.append(f"\n**Quick Check-Ins This Week:** {new_count}/2")
        feedback_parts.append(f"Use /checkin for full check-in next time.")
        
        final_message = "\n".join(feedback_parts)
        
        # Get the query object from update (since this was triggered by callback query)
        query = update.callback_query
        if query:
            await query.message.reply_text(final_message, parse_mode="Markdown")
        else:
            await update.message.reply_text(final_message, parse_mode="Markdown")
        
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
        name="checkin_conversation",
        block=True  # CRITICAL: Block other handlers when conversation is active
    )
