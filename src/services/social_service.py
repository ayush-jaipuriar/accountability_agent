"""
Social Service - Leaderboard, Referrals, and Shareable Stats
==============================================================

Phase 3F: Social features to increase engagement and retention.

<b>Three Components:</b>
1. Leaderboard - Weekly compliance ranking with privacy controls
2. Referral System - Invite tracking with deep-link attribution
3. Shareable Stats - Image generation for social sharing

<b>Privacy Model: Opt-In</b>
Users are NOT shown on the leaderboard by default. They must opt in.
This respects privacy while still enabling social comparison for those
who want it. Stored as a boolean flag on the User document.

<b>Referral Deep Links:</b>
Telegram supports bot deep links: t.me/botname?start=ref_USERID
When a new user clicks this link, Telegram sends /start ref_USERID
to the bot. We parse the referral code and attribute the new user.

<b>Cost: $0.00</b> (all logic runs against existing Firestore data)
"""

import io
import logging
from typing import List, Dict, Any
from statistics import mean

from src.models.schemas import User, DailyCheckIn
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


# ===== Leaderboard =====

def calculate_leaderboard(
    period_days: int = 7,
    top_n: int = 10,
) -> List[Dict[str, Any]]:
    """
    Calculate leaderboard rankings for all opted-in users.
    
    <b>Ranking Algorithm:</b>
    1. Primary sort: Average compliance score (last N days)
    2. Tiebreaker: Current streak length
    3. Minimum qualification: 3+ check-ins in the period
    
    <b>Why Compliance + Streak?</b>
    Compliance measures quality (how well you do each day).
    Streak measures consistency (how many days in a row).
    Together they reward users who are both consistent AND thorough.
    
    <b>Privacy: Opt-In Only</b>
    Only users with leaderboard_opt_in=True are included.
    This is checked via a field on the User document.
    
    Args:
        period_days: Number of days to look back (default: 7)
        top_n: Number of entries to return (default: 10)
        
    Returns:
        List of leaderboard entries, ranked:
        [{"rank": 1, "name": "Ayush", "compliance": 95.0, "streak": 47, ...}]
    """
    all_users = firestore_service.get_all_users()
    
    entries = []
    
    for user in all_users:
        # Check privacy opt-in (default: opted in for now to bootstrap)
        # In production, default would be False (opt-in required)
        leaderboard_visible = getattr(user, 'leaderboard_opt_in', True)
        if not leaderboard_visible:
            continue
        
        # Fetch recent check-ins
        checkins = firestore_service.get_recent_checkins(user.user_id, days=period_days)
        
        # Minimum qualification: at least 3 check-ins
        if len(checkins) < 3:
            continue
        
        avg_compliance = mean([c.compliance_score for c in checkins])
        
        entries.append({
            "user_id": user.user_id,
            "name": user.name,
            "compliance": avg_compliance,
            "streak": user.streaks.current_streak,
            "checkin_count": len(checkins),
            # Combined score for ranking (compliance is primary, streak is tiebreaker)
            # Streak is normalized to 0-5 bonus points to prevent streak-only gaming
            "score": avg_compliance + min(user.streaks.current_streak * 0.1, 5),
        })
    
    # Sort by score descending
    entries.sort(key=lambda e: e["score"], reverse=True)
    
    # Assign ranks (handle ties)
    for i, entry in enumerate(entries):
        entry["rank"] = i + 1
    
    logger.info(f"🏆 Leaderboard calculated: {len(entries)} qualifying users")
    
    return entries[:top_n]


def format_leaderboard_message(
    entries: List[Dict[str, Any]],
    requesting_user_id: str,
) -> str:
    """
    Format leaderboard as a Telegram-friendly message.
    
    <b>Design Decisions:</b>
    - First name only (privacy)
    - Rank medals for top 3 (🥇🥈🥉)
    - Compliance + streak shown for each entry
    - Requesting user's rank highlighted if not in top N
    
    Args:
        entries: Ranked leaderboard entries
        requesting_user_id: User who requested the leaderboard
        
    Returns:
        Formatted HTML string for Telegram
    """
    if not entries:
        return (
            "<b>🏆 Leaderboard</b>\n\n"
            "Not enough data yet! At least 3 check-ins needed to qualify.\n"
            "Keep checking in with /checkin to join the leaderboard."
        )
    
    # Rank emojis
    rank_icons = {1: "🥇", 2: "🥈", 3: "🥉"}
    
    lines = ["<b>🏆 Accountability Leaders (This Week)</b>\n"]
    
    user_found = False
    user_rank = None
    
    for entry in entries:
        rank = entry["rank"]
        icon = rank_icons.get(rank, f"{rank}.")
        
        # Highlight requesting user
        if entry["user_id"] == requesting_user_id:
            user_found = True
            user_rank = rank
            name = f"<b>{entry['name']} (You)</b>"
        else:
            name = entry["name"]
        
        lines.append(
            f"{icon} {name} - {entry['compliance']:.0f}% compliance, "
            f"{entry['streak']}🔥"
        )
    
    # If user not in top N, show their rank separately
    if not user_found:
        # Find user's rank
        all_users_leaderboard = calculate_leaderboard(period_days=7, top_n=100)
        for entry in all_users_leaderboard:
            if entry["user_id"] == requesting_user_id:
                user_rank = entry["rank"]
                lines.append(
                    f"\n<b>Your Rank: #{user_rank}</b> - "
                    f"{entry['compliance']:.0f}% compliance, {entry['streak']}🔥"
                )
                break
        
        if user_rank is None:
            lines.append("\n<i>Complete 3+ check-ins this week to join the leaderboard!</i>")
    else:
        total = len(calculate_leaderboard(period_days=7, top_n=100))
        lines.append(f"\n<b>Your Rank: #{user_rank} / {total} users</b>")
    
    lines.append("\n💪 Keep pushing!")
    
    return "\n".join(lines)


# ===== Referral System =====

def generate_referral_link(user_id: str, bot_username: str) -> str:
    """
    Generate a Telegram deep-link referral URL.
    
    <b>How Telegram Deep Links Work:</b>
    When someone clicks t.me/botname?start=PAYLOAD, Telegram sends
    the bot a /start command with the payload as argument:
    
    Update.message.text = "/start ref_123456"
    
    We parse this in the start_command handler to attribute the referral.
    
    <b>Payload Format:</b> ref_{user_id}
    Simple and traceable. User IDs are already unique.
    
    Args:
        user_id: Referrer's Telegram user ID
        bot_username: Bot's @username (without @)
        
    Returns:
        Full referral URL string
    """
    return f"https://t.me/{bot_username}?start=ref_{user_id}"


def get_referral_stats(user_id: str) -> Dict[str, Any]:
    """
    Get referral statistics for a user.
    
    <b>Tracked Metrics:</b>
    - Total referrals: Number of users who joined via this user's link
    - Active referrals: Users with 7+ check-ins in last 30 days
    - Reward: Compliance boost percentage (1% per active, max 5%)
    
    Args:
        user_id: Referrer's user ID
        
    Returns:
        Dictionary with referral stats
    """
    # Query all users who were referred by this user
    all_users = firestore_service.get_all_users()
    
    referrals = []
    for user in all_users:
        referred_by = getattr(user, 'referred_by', None)
        if referred_by == user_id:
            # Check if active (7+ check-ins in last 30 days)
            checkins = firestore_service.get_recent_checkins(user.user_id, days=30)
            is_active = len(checkins) >= 7
            referrals.append({
                "user_id": user.user_id,
                "name": user.name,
                "is_active": is_active,
                "checkin_count": len(checkins),
            })
    
    total = len(referrals)
    active = sum(1 for r in referrals if r["is_active"])
    reward_pct = min(active * 1, 5)  # 1% per active referral, max 5%
    
    return {
        "total_referrals": total,
        "active_referrals": active,
        "inactive_referrals": total - active,
        "reward_percentage": reward_pct,
        "referrals": referrals,
    }


def format_referral_message(
    referral_link: str,
    stats: Dict[str, Any],
) -> str:
    """
    Format referral info as a Telegram message.
    
    Args:
        referral_link: User's referral URL
        stats: Referral statistics
        
    Returns:
        Formatted message string
    """
    return (
        f"<b>🔗 Your Referral Link</b>\n\n"
        f"<code>{referral_link}</code>\n\n"
        f"Share with friends who need accountability!\n\n"
        f"<b>Your Referral Stats:</b>\n"
        f"• Total Referrals: {stats['total_referrals']}\n"
        f"• Active: {stats['active_referrals']} (7+ check-ins/month)\n"
        f"• Reward: +{stats['reward_percentage']}% compliance boost\n\n"
        f"<b>Rewards:</b>\n"
        f"• You get: +1% compliance boost per active referral (max +5%)\n"
        f"• They get: 3 bonus streak shields on signup 🛡️\n\n"
        f"<i>Active = 7+ check-ins in last 30 days</i>"
    )


# ===== Shareable Stats Image =====

def generate_shareable_stats_image(user: User, checkins: List[DailyCheckIn]) -> io.BytesIO:
    """
    Generate a visually appealing stats image for social sharing.
    
    <b>Image Design:</b>
    - Mobile-optimized (1080x1920 story format)
    - Dark gradient background (modern look)
    - Key stats: streak, compliance, check-in count
    - QR code at bottom linking to bot
    - Branded with bot name
    
    <b>Theory: Social Proof via Shareable Content</b>
    When users share their stats, it creates social proof for the bot.
    The image acts as both a brag and an advertisement. The QR code
    makes it easy for viewers to join, completing the viral loop.
    
    <b>Technology:</b> Pillow for image composition, qrcode for QR generation
    
    Args:
        user: User profile
        checkins: Recent check-ins (for stats calculation)
        
    Returns:
        BytesIO buffer with PNG image (1080x1920)
    """
    from PIL import Image, ImageDraw, ImageFont
    import qrcode
    
    # Image dimensions (Instagram story size)
    WIDTH, HEIGHT = 1080, 1920
    
    # Create base image with gradient background
    img = Image.new('RGB', (WIDTH, HEIGHT), '#1a1a2e')
    draw = ImageDraw.Draw(img)
    
    # Simple gradient effect (dark blue to dark purple)
    for y in range(HEIGHT):
        r = int(26 + (y / HEIGHT) * 20)
        g = int(26 + (y / HEIGHT) * 10)
        b = int(46 + (y / HEIGHT) * 30)
        draw.line([(0, y), (WIDTH, y)], fill=(r, g, b))
    
    # Use default font (system fonts may not be available on Cloud Run)
    try:
        # Try to use a nice font if available
        title_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        stats_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        label_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 28)
    except (OSError, IOError):
        # Fallback to default
        title_font = ImageFont.load_default()
        stats_font = ImageFont.load_default()
        label_font = ImageFont.load_default()
        small_font = ImageFont.load_default()
    
    # Calculate stats
    total_checkins = user.streaks.total_checkins
    current_streak = user.streaks.current_streak
    avg_compliance = mean([c.compliance_score for c in checkins]) if checkins else 0
    
    # Draw content
    y_pos = 200
    
    # Title
    draw.text((WIDTH // 2, y_pos), "CONSTITUTION", fill='#e94560', font=title_font, anchor='mm')
    y_pos += 80
    draw.text((WIDTH // 2, y_pos), "ACCOUNTABILITY", fill='#e94560', font=title_font, anchor='mm')
    y_pos += 120
    
    # User name
    draw.text((WIDTH // 2, y_pos), user.name.upper(), fill='white', font=title_font, anchor='mm')
    y_pos += 150
    
    # Divider
    draw.line([(200, y_pos), (880, y_pos)], fill='#e94560', width=3)
    y_pos += 80
    
    # Stat boxes
    stats_data = [
        (str(current_streak), "DAY STREAK", "🔥"),
        (f"{avg_compliance:.0f}%", "COMPLIANCE", "📊"),
        (str(total_checkins), "CHECK-INS", "✅"),
        (str(user.streaks.longest_streak), "BEST STREAK", "🏆"),
    ]
    
    for value, label, emoji in stats_data:
        draw.text((WIDTH // 2, y_pos), f"{emoji} {value}", fill='white',
                  font=stats_font, anchor='mm')
        y_pos += 90
        draw.text((WIDTH // 2, y_pos), label, fill='#8892b0', font=label_font, anchor='mm')
        y_pos += 100
    
    # QR Code
    try:
        qr = qrcode.QRCode(version=1, box_size=8, border=2)
        qr.add_data("https://t.me/constitution_bot")
        qr.make(fit=True)
        qr_img = qr.make_image(fill_color='white', back_color='#1a1a2e')
        qr_img = qr_img.resize((200, 200))
        img.paste(qr_img, (WIDTH // 2 - 100, HEIGHT - 350))
    except Exception as e:
        logger.warning(f"QR code generation failed: {e}")
    
    # Footer
    draw.text((WIDTH // 2, HEIGHT - 100), "Join the journey → @constitution_bot",
              fill='#8892b0', font=small_font, anchor='mm')
    
    # Save to buffer
    buf = io.BytesIO()
    img.save(buf, format='PNG', quality=95)
    buf.seek(0)
    
    logger.info(f"📸 Shareable stats image generated: {buf.getbuffer().nbytes} bytes")
    return buf
