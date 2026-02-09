"""
UX Utilities - Formatting, Error Messages, and Timeout Handling
================================================================

Phase 3F: Standardized UX components for consistent user experience.

<b>Three Pillars:</b>
1. Message Formatting - Consistent visual structure across all commands
2. Error Messages - Helpful, actionable errors with emoji indicators
3. Timeout Management - Conversation state tracking and auto-cleanup

<b>Design Philosophy:</b>
- Telegram messages have limited formatting (HTML/Markdown)
- Mobile screens are small - concise is better
- Every error must answer: "What happened?" and "What should I do?"
- Emojis are semantic (success=✅, error=❌, warning=⚠️), not decorative

<b>Why a Utility Module?</b>
These functions are used by every command handler. Centralizing them:
1. Ensures consistency (all messages look the same)
2. Makes updates easy (change format in one place)
3. Prevents copy-paste drift (each handler uses the same helpers)
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


# ===== Message Formatting Constants =====

# Semantic emoji map - consistent meaning across all messages
EMOJI = {
    # Status
    'success': '✅',
    'error': '❌',
    'warning': '⚠️',
    'info': 'ℹ️',
    'loading': '⏳',
    
    # Features
    'checkin': '📋',
    'stats': '📊',
    'streak': '🔥',
    'shield': '🛡️',
    'achievement': '🏆',
    'goal': '🎯',
    'encourage': '💪',
    'report': '📈',
    'export': '📤',
    'leaderboard': '🏅',
    'referral': '🔗',
    'share': '📸',
    'help': '❓',
    'settings': '⚙️',
    'career': '💼',
    'sleep': '😴',
    'training': '🏋️',
    'clock': '⏰',
    'calendar': '📅',
    'partner': '👥',
    'emotional': '💭',
}


# ===== Message Formatting =====

def format_header(title: str, subtitle: Optional[str] = None) -> str:
    """
    Format a consistent message header.
    
    <b>Structure:</b>
    <b>EMOJI Title</b>
    <i>Subtitle (if provided)</i>
    
    Args:
        title: Header text (will be bold)
        subtitle: Optional subtitle (will be italic)
        
    Returns:
        HTML-formatted header string
    """
    header = f"<b>{title}</b>"
    if subtitle:
        header += f"\n<i>{subtitle}</i>"
    return header


def format_stat_line(label: str, value: str, emoji_key: Optional[str] = None) -> str:
    """
    Format a single statistic line.
    
    <b>Structure:</b>
    • EMOJI <b>Label:</b> Value
    
    Args:
        label: Stat name (e.g., "Current Streak")
        value: Stat value (e.g., "47 days")
        emoji_key: Key from EMOJI dict (optional)
        
    Returns:
        Formatted stat line
    """
    prefix = EMOJI.get(emoji_key, '•') if emoji_key else '•'
    return f"{prefix} <b>{label}:</b> {value}"


def format_command_hint(command: str, description: str) -> str:
    """
    Format a command suggestion.
    
    <b>Structure:</b>
    /{command} - Description
    
    Args:
        command: Command name without /
        description: What the command does
        
    Returns:
        Formatted command hint
    """
    return f"/{command} - {description}"


def format_section(title: str, content: str) -> str:
    """
    Format a message section with header and content.
    
    <b>Structure:</b>
    <b>Title:</b>
    Content
    
    Args:
        title: Section title
        content: Section body
        
    Returns:
        Formatted section
    """
    return f"<b>{title}:</b>\n{content}"


def format_divider() -> str:
    """
    Return a visual divider for message sections.
    
    Uses Unicode box-drawing characters for a clean look.
    """
    return "━━━━━━━━━━━━━━━━━━━━"


# ===== Error Messages =====

class ErrorMessages:
    """
    Centralized error messages following a consistent pattern.
    
    <b>Pattern: Emoji + What Happened + What To Do</b>
    
    Every error message follows this structure:
    1. Emoji indicator (❌, ⚠️, 🔧)
    2. Clear explanation of what went wrong
    3. Actionable next step
    
    <b>Theory: Error Messages as UX</b>
    Most apps show generic "An error occurred" messages. This is a
    missed opportunity. Good error messages:
    - Reduce support requests (user can self-serve)
    - Build trust (user knows the app is well-built)
    - Maintain engagement (user knows what to do next)
    
    Example:
        Bad:  "Error: user not found"
        Good: "❌ Profile not found. Use /start to create your profile."
    """
    
    @staticmethod
    def user_not_found() -> str:
        return (
            f"{EMOJI['error']} <b>Profile Not Found</b>\n\n"
            f"You don't have a profile yet.\n"
            f"Use /start to create your profile and begin your accountability journey."
        )
    
    @staticmethod
    def no_checkins(period: str = "") -> str:
        period_text = f" in {period}" if period else ""
        return (
            f"{EMOJI['stats']} <b>No Check-Ins Found{period_text}</b>\n\n"
            f"You haven't completed any check-ins{period_text}.\n"
            f"Complete your first check-in with /checkin to start tracking!"
        )
    
    @staticmethod
    def already_checked_in(date: str) -> str:
        return (
            f"{EMOJI['success']} <b>Already Checked In</b>\n\n"
            f"You've already completed your check-in for {date}.\n"
            f"Come back tomorrow to continue your streak!\n\n"
            f"Use /status to view your current stats."
        )
    
    @staticmethod
    def rate_limited(seconds: int = 30) -> str:
        return (
            f"{EMOJI['clock']} <b>Please Slow Down</b>\n\n"
            f"You're sending messages too quickly.\n"
            f"Try again in {seconds} seconds."
        )
    
    @staticmethod
    def service_unavailable() -> str:
        return (
            f"🔧 <b>Temporary Issue</b>\n\n"
            f"We're experiencing a brief service disruption.\n"
            f"Please try again in a few minutes.\n\n"
            f"If this persists, your data is safe - nothing is lost."
        )
    
    @staticmethod
    def invalid_command(attempted: str = "") -> str:
        cmd_text = f" '{attempted}'" if attempted else ""
        return (
            f"{EMOJI['warning']} <b>Unknown Command{cmd_text}</b>\n\n"
            f"I didn't recognize that command.\n"
            f"Use /help to see all available commands."
        )
    
    @staticmethod
    def export_failed(format_type: str) -> str:
        return (
            f"{EMOJI['error']} <b>Export Failed</b>\n\n"
            f"Couldn't generate your {format_type.upper()} export.\n"
            f"This is usually a temporary issue. Please try again.\n\n"
            f"If the problem persists, try a different format:\n"
            f"/export csv | /export json | /export pdf"
        )
    
    @staticmethod
    def export_no_data() -> str:
        return (
            f"{EMOJI['stats']} <b>No Data to Export</b>\n\n"
            f"You don't have any check-in data to export yet.\n"
            f"Complete some check-ins first with /checkin, then try again."
        )
    
    @staticmethod
    def generic_error() -> str:
        return (
            f"{EMOJI['error']} <b>Something Went Wrong</b>\n\n"
            f"An unexpected error occurred.\n"
            f"Please try again, or use /help if you need assistance.\n\n"
            f"Your data is safe - nothing was lost."
        )


# ===== Timeout Management =====

class TimeoutManager:
    """
    Manages conversation timeout tracking and cleanup.
    
    <b>Problem:</b> When a user starts a check-in but doesn't finish,
    the conversation state gets stuck. The bot keeps waiting for
    the next answer indefinitely, which:
    1. Confuses the user ("Why isn't /status working?")
    2. Wastes memory (conversation state stored in RAM)
    3. Can corrupt data (partial check-in state)
    
    <b>Solution: Proactive Timeouts</b>
    - Check-in: 15 min → reminder, 30 min → auto-cancel
    - Query: 5 min → auto-cancel
    - Store partial state for /resume capability
    
    <b>Implementation:</b>
    We store the start timestamp in context.user_data when a
    conversation begins. A background check (or middleware) compares
    against current time and triggers cleanup if expired.
    
    <b>Firestore State Storage:</b>
    Partial check-in data is stored in Firestore under:
    partial_checkins/{user_id} → {state, last_updated, data}
    This enables /resume across server restarts.
    """
    
    # Timeout durations (in minutes)
    CHECKIN_REMINDER_MINUTES = 15
    CHECKIN_CANCEL_MINUTES = 30
    QUERY_CANCEL_MINUTES = 5
    
    @staticmethod
    def get_timeout_warning(minutes_remaining: int) -> str:
        """
        Generate a timeout warning message.
        
        Args:
            minutes_remaining: Minutes until auto-cancel
            
        Returns:
            Warning message string
        """
        return (
            f"{EMOJI['clock']} <b>Check-In Timeout</b>\n\n"
            f"Your check-in will expire in {minutes_remaining} minutes.\n"
            f"Send your answer to continue, or use /cancel to stop.\n\n"
            f"💡 <i>Tip: You can resume later with /resume</i>"
        )
    
    @staticmethod
    def get_timeout_cancel_message() -> str:
        """
        Generate a timeout cancellation message.
        
        Returns:
            Cancellation message string
        """
        return (
            f"{EMOJI['clock']} <b>Check-In Expired</b>\n\n"
            f"Your check-in was cancelled due to inactivity (30 minutes).\n\n"
            f"Your progress has been saved. Resume anytime with /resume\n"
            f"Or start fresh with /checkin"
        )
    
    @staticmethod
    def check_timeout(
        start_time: datetime,
        timeout_minutes: int,
    ) -> bool:
        """
        Check if a conversation has exceeded its timeout.
        
        Args:
            start_time: When the conversation started
            timeout_minutes: Maximum allowed duration
            
        Returns:
            True if timed out, False if still within limit
        """
        elapsed = datetime.utcnow() - start_time
        return elapsed > timedelta(minutes=timeout_minutes)
    
    @staticmethod
    def save_partial_state(
        user_id: str,
        conversation_type: str,
        state_data: Dict[str, Any],
    ) -> bool:
        """
        Save partial conversation state for /resume capability.
        
        Stores the current state of an incomplete conversation so
        the user can pick up where they left off later.
        
        <b>Firestore Structure:</b>
        partial_checkins/{user_id}:
        {
            "conversation_type": "checkin",
            "state_step": 3,  (which question they're on)
            "data": { ... partial answers ... },
            "started_at": datetime,
            "last_updated": datetime,
        }
        
        Args:
            user_id: User's Telegram ID
            conversation_type: "checkin" or "quick_checkin"
            state_data: Partial conversation data to save
            
        Returns:
            True if saved successfully
        """
        try:
            from src.services.firestore_service import firestore_service
            
            doc_data = {
                "user_id": user_id,
                "conversation_type": conversation_type,
                "data": state_data,
                "last_updated": datetime.utcnow(),
            }
            
            firestore_service.db.collection('partial_checkins').document(user_id).set(doc_data)
            logger.info(f"💾 Saved partial state for {user_id} ({conversation_type})")
            return True
            
        except Exception as e:
            logger.error(f"Failed to save partial state for {user_id}: {e}")
            return False
    
    @staticmethod
    def get_partial_state(user_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve partial conversation state for /resume.
        
        Args:
            user_id: User's Telegram ID
            
        Returns:
            Partial state dictionary, or None if not found
        """
        try:
            from src.services.firestore_service import firestore_service
            
            doc = firestore_service.db.collection('partial_checkins').document(user_id).get()
            
            if doc.exists:
                data = doc.to_dict()
                # Check if state is still valid (not older than 24 hours)
                last_updated = data.get("last_updated")
                if last_updated:
                    if isinstance(last_updated, datetime):
                        age = datetime.utcnow() - last_updated
                    else:
                        # Firestore timestamp
                        age = datetime.utcnow() - last_updated.replace(tzinfo=None)
                    
                    if age > timedelta(hours=24):
                        logger.info(f"Partial state for {user_id} expired (>24h old)")
                        return None
                
                return data
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to get partial state for {user_id}: {e}")
            return None
    
    @staticmethod
    def clear_partial_state(user_id: str) -> bool:
        """
        Delete partial state after successful resume or explicit cancel.
        
        Args:
            user_id: User's Telegram ID
            
        Returns:
            True if cleared successfully
        """
        try:
            from src.services.firestore_service import firestore_service
            
            firestore_service.db.collection('partial_checkins').document(user_id).delete()
            logger.info(f"🧹 Cleared partial state for {user_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to clear partial state for {user_id}: {e}")
            return False


# ===== Help Text Generator =====

def generate_help_text() -> str:
    """
    Generate comprehensive help text organized by category.
    
    <b>Design: Category-Based Organization</b>
    Commands are grouped by function (Check-Ins, Stats, Social, Settings)
    rather than listed alphabetically. This helps users find what they
    need based on intent rather than knowing the command name.
    
    Returns:
        HTML-formatted help message
    """
    return (
        f"{format_header(EMOJI['help'] + ' Available Commands')}\n\n"
        
        f"<b>{EMOJI['checkin']} Check-Ins:</b>\n"
        f"/checkin - Full daily check-in (~5 min)\n"
        f"/quickcheckin - Quick Tier 1 only (~2 min, 2/week)\n"
        f"/resume - Resume incomplete check-in\n\n"
        
        f"<b>{EMOJI['stats']} Stats & Reports:</b>\n"
        f"/status - Current streak and overview\n"
        f"/weekly - Last 7 days summary\n"
        f"/monthly - Last 30 days summary\n"
        f"/yearly - Year-to-date summary\n"
        f"/report - Generate visual weekly report\n\n"
        
        f"<b>{EMOJI['export']} Data Export:</b>\n"
        f"/export csv - Download check-ins as CSV\n"
        f"/export json - Download as JSON\n"
        f"/export pdf - Download formatted PDF report\n\n"
        
        f"<b>{EMOJI['leaderboard']} Social:</b>\n"
        f"/leaderboard - See weekly rankings\n"
        f"/invite - Get your referral link\n"
        f"/share - Generate shareable stats image\n\n"
        
        f"<b>{EMOJI['settings']} Settings:</b>\n"
        f"/mode - Change constitution mode\n"
        f"/career - Change career phase\n"
        f"/timezone - Change your timezone\n"
        f"/use_shield - Use streak shield\n"
        f"/achievements - View achievements\n\n"
        
        f"<b>{EMOJI['partner']} Partner:</b>\n"
        f"/set_partner @user - Link accountability partner\n"
        f"/partner_status - View partner's dashboard\n"
        f"/unlink_partner - Remove partner\n\n"
        
        f"<b>{EMOJI['emotional']} Support & Natural Language:</b>\n"
        f"/support - Talk through something you're struggling with\n"
        f"Just type naturally!\n"
        f"• 'What's my compliance this month?'\n"
        f"• 'I'm feeling stressed'\n"
        f"• 'Show my sleep trend'\n\n"
        
        f"<i>{EMOJI['clock']} Reminders at 9 PM, 9:30 PM, 10 PM in your local time</i>"
    )


# ===== Phase C: Partner Dashboard Formatting =====

def format_partner_dashboard(
    partner_name: str,
    partner_streak_current: int,
    partner_streak_longest: int,
    partner_checked_in_today: bool,
    partner_today_compliance: float | None,
    partner_weekly_checkins: int,
    partner_weekly_possible: int,
    partner_weekly_avg_compliance: float,
    user_streak_current: int,
    user_weekly_avg_compliance: float
) -> str:
    """
    Format the /partner_status dashboard message.

    <b>Privacy Model (Aggregate Only):</b>
    Partners see streak, compliance %, and check-in status.
    They do NOT see individual Tier 1 items, challenges, or ratings.

    <b>Design:</b>
    - Top: partner identity
    - Middle: today's status + streak + weekly stats
    - Bottom: motivational comparison footer

    Args:
        partner_name: Partner's display name
        partner_streak_current: Partner's current streak in days
        partner_streak_longest: Partner's all-time best streak
        partner_checked_in_today: Whether partner has checked in today
        partner_today_compliance: Today's compliance % (None if no check-in)
        partner_weekly_checkins: Number of check-ins in last 7 days
        partner_weekly_possible: Number of days in the window (usually 7)
        partner_weekly_avg_compliance: Average compliance % over last 7 days
        user_streak_current: Requesting user's current streak
        user_weekly_avg_compliance: Requesting user's weekly avg compliance

    Returns:
        HTML-formatted partner dashboard string
    """
    # Header
    lines = [
        f"<b>{EMOJI['partner']} Partner Dashboard</b>",
        "━━━━━━━━━━━━━━━━━━",
        "",
        f"🤝 Your partner: <b>{partner_name}</b>",
        "",
    ]

    # Today's status
    lines.append(f"<b>{EMOJI['stats']} {partner_name}'s Status Today:</b>")
    if partner_checked_in_today:
        lines.append(f"  {EMOJI['success']} Checked in today")
        if partner_today_compliance is not None:
            lines.append(f"  {EMOJI['report']} Compliance: {partner_today_compliance:.0f}%")
    else:
        lines.append(f"  {EMOJI['loading']} Not yet checked in")
    lines.append("")

    # Streak info
    lines.append(f"<b>{EMOJI['streak']} {partner_name}'s Streak:</b>")
    streak_label = f"  Current: {partner_streak_current} days"
    if not partner_checked_in_today and partner_streak_current > 0:
        streak_label += " (at risk!)"
    lines.append(streak_label)
    lines.append(f"  Longest ever: {partner_streak_longest} days")
    lines.append("")

    # Weekly stats
    lines.append(f"<b>{EMOJI['calendar']} This Week:</b>")
    if partner_weekly_checkins > 0:
        lines.append(f"  Check-ins: {partner_weekly_checkins}/{partner_weekly_possible}")
        lines.append(f"  Avg Compliance: {partner_weekly_avg_compliance:.0f}%")
    else:
        lines.append("  No check-ins yet this week")
    lines.append("")

    # Comparison footer
    lines.append("━━━━━━━━━━━━━━━━━━")
    footer = get_partner_comparison_footer(
        user_streak_current, partner_streak_current,
        user_weekly_avg_compliance, partner_weekly_avg_compliance,
        partner_name
    )
    lines.append(footer)

    return "\n".join(lines)


def get_partner_comparison_footer(
    user_streak: int,
    partner_streak: int,
    user_compliance_week: float,
    partner_compliance_week: float,
    partner_name: str
) -> str:
    """
    Generate a motivational comparison footer for the partner dashboard.

    <b>Framing philosophy:</b> Always encouraging, never shaming.
    - Leading = positive reinforcement
    - Behind = competitive nudge
    - Tied = celebration of teamwork

    Args:
        user_streak: Requesting user's current streak
        partner_streak: Partner's current streak
        user_compliance_week: User's weekly avg compliance %
        partner_compliance_week: Partner's weekly avg compliance %
        partner_name: Partner's name for personalization

    Returns:
        Motivational string
    """
    if user_streak > partner_streak and user_compliance_week >= partner_compliance_week:
        return f"{EMOJI['achievement']} You're leading! Keep the momentum and inspire {partner_name}."
    elif partner_streak > user_streak:
        diff = partner_streak - user_streak
        return f"{EMOJI['encourage']} {partner_name} is ahead by {diff} days. Time to close the gap!"
    elif user_streak == partner_streak and user_streak > 0:
        return f"🤝 You're perfectly matched at {user_streak} days! Keep pushing together."
    elif user_compliance_week > partner_compliance_week + 10:
        return f"{EMOJI['report']} Your compliance is stronger this week. Keep it up!"
    elif partner_compliance_week > user_compliance_week + 10:
        return f"{EMOJI['encourage']} {partner_name}'s compliance is strong. Match their energy!"
    else:
        return f"{EMOJI['encourage']} You're both showing up. Keep it going!"
