"""
UX Utilities - Formatting, Error Messages, and Timeout Handling
================================================================

Phase 3F: Standardized UX components for consistent user experience.

**Three Pillars:**
1. Message Formatting - Consistent visual structure across all commands
2. Error Messages - Helpful, actionable errors with emoji indicators
3. Timeout Management - Conversation state tracking and auto-cleanup

**Design Philosophy:**
- Telegram messages have limited formatting (HTML/Markdown)
- Mobile screens are small - concise is better
- Every error must answer: "What happened?" and "What should I do?"
- Emojis are semantic (success=✅, error=❌, warning=⚠️), not decorative

**Why a Utility Module?**
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
    
    **Structure:**
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
    
    **Structure:**
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
    
    **Structure:**
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
    
    **Structure:**
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
    
    **Pattern: Emoji + What Happened + What To Do**
    
    Every error message follows this structure:
    1. Emoji indicator (❌, ⚠️, 🔧)
    2. Clear explanation of what went wrong
    3. Actionable next step
    
    **Theory: Error Messages as UX**
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
    
    **Problem:** When a user starts a check-in but doesn't finish,
    the conversation state gets stuck. The bot keeps waiting for
    the next answer indefinitely, which:
    1. Confuses the user ("Why isn't /status working?")
    2. Wastes memory (conversation state stored in RAM)
    3. Can corrupt data (partial check-in state)
    
    **Solution: Proactive Timeouts**
    - Check-in: 15 min → reminder, 30 min → auto-cancel
    - Query: 5 min → auto-cancel
    - Store partial state for /resume capability
    
    **Implementation:**
    We store the start timestamp in context.user_data when a
    conversation begins. A background check (or middleware) compares
    against current time and triggers cleanup if expired.
    
    **Firestore State Storage:**
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
        
        **Firestore Structure:**
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
    
    **Design: Category-Based Organization**
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
        f"/use_shield - Use streak shield\n"
        f"/achievements - View achievements\n\n"
        
        f"<b>{EMOJI['partner']} Social:</b>\n"
        f"/set_partner @user - Link accountability partner\n"
        f"/unlink_partner - Remove partner\n\n"
        
        f"<b>{EMOJI['emotional']} Natural Language:</b>\n"
        f"Just type naturally!\n"
        f"• 'What's my compliance this month?'\n"
        f"• 'I'm feeling stressed'\n"
        f"• 'Show my sleep trend'\n\n"
        
        f"<i>{EMOJI['clock']} Reminders at 9 PM, 9:30 PM, 10 PM IST daily</i>"
    )
