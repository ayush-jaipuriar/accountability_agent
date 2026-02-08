"""
Tiered Rate Limiter
===================

In-memory rate limiting for Telegram bot commands, using a sliding window approach.

Why Rate Limiting?
------------------
Without throttling, a single user (or bot) can:
- Spam /report → generates 4 graphs + Gemini AI analysis each time
- Spam /export pdf → CPU-intensive PDF generation
- Flood AI queries → burns through Gemini API token budget
- Overwhelm Firestore → drives up read costs

Sliding Window Algorithm
------------------------
For each (user_id, tier) pair, we store timestamps of recent requests.
When a new request arrives:
1. Prune timestamps older than the window (1 hour)
2. Check if hourly limit is exceeded
3. Check if cooldown period has elapsed since last request
4. If allowed, record the new timestamp

This is more accurate than fixed windows (no boundary burst issues)
and simpler than token buckets (no refill rate math).

Tier System
-----------
Commands are grouped by resource cost:
- Expensive: /report, /export — AI + graph generation (30min cooldown, 2/hour)
- AI-Powered: General messages, /support — Gemini API calls (2min cooldown, 20/hour)
- Standard: /stats, /partner_status, /leaderboard — DB reads only (10s cooldown, 30/hour)
- Free: /start, /help, /mode, /cancel — no backend cost (unlimited)

Memory Considerations
---------------------
Each user+tier entry stores a list of datetime objects (8 bytes each).
Worst case: 1000 users × 3 tiers × 30 entries = ~720KB. Negligible.
Entries auto-prune after 1 hour, so memory is bounded.

Usage:
    from src.utils.rate_limiter import rate_limiter

    allowed, message = rate_limiter.check("user123", "report")
    if not allowed:
        await update.message.reply_text(message)
        return
"""

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    In-memory tiered rate limiter for Telegram bot commands.

    Thread-safety: Python's GIL ensures dict operations are atomic.
    For async code (our case), there's no concurrency issue since
    we're single-threaded within the event loop.
    """

    # ===== Tier Definitions =====
    # Each tier has:
    #   cooldown_seconds: Minimum time between consecutive uses
    #   max_per_hour: Maximum number of uses within a rolling 1-hour window
    TIERS = {
        "expensive": {
            "cooldown_seconds": 1800,  # 30 minutes
            "max_per_hour": 2,
            "description": "Resource-intensive (graphs + AI analysis)",
        },
        "ai_powered": {
            "cooldown_seconds": 120,  # 2 minutes
            "max_per_hour": 20,
            "description": "Gemini API calls",
        },
        "standard": {
            "cooldown_seconds": 10,  # 10 seconds
            "max_per_hour": 30,
            "description": "Database reads",
        },
    }

    # ===== Command → Tier Mapping =====
    # Commands not listed here are "free tier" (unlimited).
    COMMAND_TIERS = {
        # Expensive tier: AI + visualization
        "report": "expensive",
        "export": "expensive",
        # AI-powered tier: Gemini calls
        "support": "ai_powered",
        "query": "ai_powered",           # General AI messages
        # Standard tier: Firestore reads
        "stats": "standard",
        "weekly": "standard",
        "monthly": "standard",
        "yearly": "standard",
        "partner_status": "standard",
        "leaderboard": "standard",
        "achievements": "standard",
        "share": "standard",
    }

    def __init__(self):
        # Nested dict: {user_id: {tier: [datetime, datetime, ...]}}
        # defaultdict auto-creates empty structures on first access.
        self._requests: dict[str, dict[str, list[datetime]]] = defaultdict(
            lambda: defaultdict(list)
        )

        # Admin user IDs that bypass rate limits (loaded from config).
        # Set externally via set_admin_ids().
        self._admin_ids: set[str] = set()

    def set_admin_ids(self, admin_ids: list[str]) -> None:
        """
        Set admin user IDs that bypass rate limits.

        Called once at startup from config.

        Args:
            admin_ids: List of Telegram user ID strings
        """
        self._admin_ids = set(admin_ids)
        if admin_ids:
            logger.info(f"✅ Rate limiter: {len(admin_ids)} admin(s) configured for bypass")

    def check(self, user_id: str, command: str) -> Tuple[bool, Optional[str]]:
        """
        Check if a command is allowed for this user.

        This is the main entry point. Call before executing any rate-limited command.

        Algorithm:
        1. Look up the command's tier. If no tier → free (always allowed).
        2. If user is admin → always allowed.
        3. Prune old entries (older than 1 hour) to bound memory.
        4. Check hourly limit → deny if exceeded.
        5. Check cooldown → deny if too soon since last use.
        6. Record timestamp and allow.

        Args:
            user_id: Telegram user ID as string
            command: Command name without slash (e.g., "report", "export")

        Returns:
            Tuple of (allowed: bool, denial_message: Optional[str]).
            If allowed, message is None.
            If denied, message is user-friendly text explaining when to retry.
        """
        tier = self.COMMAND_TIERS.get(command)
        if tier is None:
            return True, None  # Free tier — always allowed

        # Admin bypass
        if user_id in self._admin_ids:
            return True, None

        config = self.TIERS[tier]
        now = datetime.utcnow()

        # Get this user's request history for this tier
        entries = self._requests[user_id][tier]

        # Prune entries older than 1 hour (sliding window maintenance)
        cutoff = now - timedelta(hours=1)
        entries[:] = [t for t in entries if t > cutoff]

        # Check 1: Hourly limit
        if len(entries) >= config["max_per_hour"]:
            logger.info(
                f"⏳ Rate limit (hourly): user={user_id}, command={command}, "
                f"tier={tier}, count={len(entries)}/{config['max_per_hour']}"
            )
            return False, (
                f"⏳ You've used this {len(entries)} times in the last hour "
                f"(limit: {config['max_per_hour']}).\n\n"
                f"Try again when the oldest request expires."
            )

        # Check 2: Cooldown since last use
        if entries:
            last_request = entries[-1]
            elapsed = (now - last_request).total_seconds()
            cooldown_remaining = config["cooldown_seconds"] - elapsed

            if cooldown_remaining > 0:
                # Format remaining time human-readably
                minutes = int(cooldown_remaining // 60)
                seconds = int(cooldown_remaining % 60)

                if minutes > 0:
                    time_str = f"{minutes}m {seconds}s"
                else:
                    time_str = f"{seconds}s"

                logger.info(
                    f"⏳ Rate limit (cooldown): user={user_id}, command={command}, "
                    f"tier={tier}, remaining={time_str}"
                )
                return False, (
                    f"⏳ Please wait {time_str} before using this again.\n\n"
                    f"💡 Tip: {self._get_tip(command)}"
                )

        # Allowed — record this request
        entries.append(now)
        return True, None

    def get_usage(self, user_id: str) -> dict:
        """
        Get rate limit usage summary for a user.

        Useful for a /usage command or debugging.

        Args:
            user_id: Telegram user ID as string

        Returns:
            dict with per-tier usage info
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=1)
        usage = {}

        for tier, config in self.TIERS.items():
            entries = self._requests.get(user_id, {}).get(tier, [])
            recent = [t for t in entries if t > cutoff]

            if recent:
                last_used = recent[-1]
                elapsed = (now - last_used).total_seconds()
                cooldown_remaining = max(0, config["cooldown_seconds"] - elapsed)
            else:
                cooldown_remaining = 0

            usage[tier] = {
                "used_this_hour": len(recent),
                "max_per_hour": config["max_per_hour"],
                "cooldown_remaining_seconds": round(cooldown_remaining),
                "description": config["description"],
            }

        return usage

    def _get_tip(self, command: str) -> str:
        """
        Get a context-appropriate tip for rate-limited commands.

        Args:
            command: The command that was rate-limited

        Returns:
            str: Helpful tip for the user
        """
        tips = {
            "report": "Reports are most useful when reviewed weekly, not hourly!",
            "export": "Your data isn't going anywhere — exports can wait.",
            "support": "Take a moment to reflect before our next chat.",
            "query": "Journaling your thoughts while waiting can help too.",
        }
        return tips.get(command, "This limit protects the service for all users.")

    def cleanup(self) -> int:
        """
        Remove stale entries from all users.

        Called periodically (e.g., every hour) to prevent memory growth
        from users who haven't been active recently.

        Returns:
            int: Number of user entries cleaned up
        """
        now = datetime.utcnow()
        cutoff = now - timedelta(hours=2)  # Keep 2 hours for safety
        cleaned = 0

        stale_users = []
        for user_id, tiers in self._requests.items():
            all_empty = True
            for tier, entries in tiers.items():
                entries[:] = [t for t in entries if t > cutoff]
                if entries:
                    all_empty = False

            if all_empty:
                stale_users.append(user_id)

        for user_id in stale_users:
            del self._requests[user_id]
            cleaned += 1

        if cleaned:
            logger.debug(f"🧹 Rate limiter cleanup: removed {cleaned} stale user entries")

        return cleaned


# ===== Singleton Instance =====
# Imported throughout the app: `from src.utils.rate_limiter import rate_limiter`
rate_limiter = RateLimiter()
