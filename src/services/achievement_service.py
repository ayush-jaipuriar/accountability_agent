"""
Achievement System Service

Handles the gamification layer for user retention and motivation.

Key Concepts:
--------------
1. **Behavioral Psychology**: Uses operant conditioning through intermittent rewards
2. **Progressive Disclosure**: Achievements revealed as user progresses
3. **Social Proof**: Rarity tiers create aspirational comparison
4. **Intrinsic Motivation**: Transforms external streaks into internal identity

Architecture:
-------------
- Global achievement catalog (ACHIEVEMENTS dict)
- User-specific unlocks stored in User.achievements list
- Duplicate prevention through set membership checks
- Async checking after check-in completion (doesn't block user)

Achievement Types:
------------------
1. Streak-based: Progression milestones (7, 14, 30, 90, 180, 365 days)
2. Performance-based: Excellence markers (perfect week/month, tier1 master)
3. Special: Unique accomplishments (comeback king, shield master)

Author: Ayush Jaipuriar
Date: February 6, 2026
Phase: 3C - Gamification & User Retention
"""

from typing import List, Optional, Dict
from datetime import datetime
import logging
import bisect

from src.models.schemas import User, DailyCheckIn, Achievement
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


# =====================================================
# ACHIEVEMENT CATALOG (Global Definitions)
# =====================================================

ACHIEVEMENTS: Dict[str, Achievement] = {
    # ==========================================
    # STREAK-BASED ACHIEVEMENTS (7 total)
    # ==========================================
    # These create clear progression and are the primary retention driver
    
    "first_checkin": Achievement(
        achievement_id="first_checkin",
        name="First Step",
        description="Complete your first check-in",
        icon="🎯",
        criteria={"checkins": 1},
        rarity="common"
    ),
    
    "week_warrior": Achievement(
        achievement_id="week_warrior",
        name="Week Warrior",
        description="7 consecutive days - Building momentum!",
        icon="🏅",
        criteria={"streak": 7},
        rarity="common"
    ),
    
    "fortnight_fighter": Achievement(
        achievement_id="fortnight_fighter",
        name="Fortnight Fighter",
        description="14 consecutive days - Habit forming!",
        icon="🥈",
        criteria={"streak": 14},
        rarity="common"
    ),
    
    "month_master": Achievement(
        achievement_id="month_master",
        name="Month Master",
        description="30 consecutive days - Top 10% territory",
        icon="🏆",
        criteria={"streak": 30},
        rarity="rare"
    ),
    
    "quarter_conqueror": Achievement(
        achievement_id="quarter_conqueror",
        name="Quarter Conqueror",
        description="90 consecutive days - Elite status",
        icon="💎",
        criteria={"streak": 90},
        rarity="epic"
    ),
    
    "half_year_hero": Achievement(
        achievement_id="half_year_hero",
        name="Half Year Hero",
        description="180 consecutive days - Top 1% club",
        icon="🏅",
        criteria={"streak": 180},
        rarity="epic"
    ),
    
    "year_yoda": Achievement(
        achievement_id="year_yoda",
        name="Year Yoda",
        description="365 consecutive days - Legend status!",
        icon="👑",
        criteria={"streak": 365},
        rarity="legendary"
    ),
    
    # ==========================================
    # PERFORMANCE-BASED ACHIEVEMENTS (4 total)
    # ==========================================
    # These reward excellence, not just consistency
    
    "perfect_week": Achievement(
        achievement_id="perfect_week",
        name="Perfect Week",
        description="7 consecutive days at 100% compliance",
        icon="⭐",
        criteria={"days": 7, "compliance": 100},
        rarity="rare"
    ),
    
    "perfect_month": Achievement(
        achievement_id="perfect_month",
        name="Perfect Month",
        description="30 consecutive days at 100% compliance",
        icon="🌟",
        criteria={"days": 30, "compliance": 100},
        rarity="epic"
    ),
    
    "tier1_master": Achievement(
        achievement_id="tier1_master",
        name="Tier 1 Master",
        description="30 consecutive days with all Tier 1 items complete",
        icon="💯",
        criteria={"days": 30, "tier1_complete": True},
        rarity="epic"
    ),
    
    "zero_breaks_month": Achievement(
        achievement_id="zero_breaks_month",
        name="Zero Breaks Month",
        description="30 consecutive days with zero porn",
        icon="🚫",
        criteria={"days": 30, "zero_porn": True},
        rarity="rare"
    ),
    
    # ==========================================
    # SPECIAL ACHIEVEMENTS (4 total — Phase D added Comeback Kid + Comeback Legend)
    # ==========================================
    # These create memorable moments and unique stories
    
    "comeback_kid": Achievement(
        achievement_id="comeback_kid",
        name="Comeback Kid",
        description="Reached 3-day streak after a reset",
        icon="🐣",
        criteria={"comeback_days": 3},
        rarity="uncommon"
    ),
    
    "comeback_king": Achievement(
        achievement_id="comeback_king",
        name="Comeback King",
        description="Reached 7-day streak after a reset",
        icon="🦁",
        criteria={"comeback_days": 7},
        rarity="rare"
    ),
    
    "comeback_legend": Achievement(
        achievement_id="comeback_legend",
        name="Comeback Legend",
        description="Exceeded previous best streak after a reset",
        icon="👑",
        criteria={"comeback_exceed": True},
        rarity="epic"
    ),
    
    "shield_master": Achievement(
        achievement_id="shield_master",
        name="Shield Master",
        description="Used all 3 shields wisely in one month",
        icon="🛡️",
        criteria={"shields_used": 3},
        rarity="common"
    ),
}


# =====================================================
# ACHIEVEMENT SERVICE CLASS
# =====================================================

class AchievementService:
    """
    Service for managing achievement unlocks and celebrations.
    
    Workflow:
    ---------
    1. CheckInAgent calls check_achievements() after check-in completion
    2. Service checks streak, performance, and special achievements
    3. Returns list of newly unlocked achievement IDs
    4. CheckInAgent calls unlock_achievement() for each
    5. CheckInAgent sends celebration message to user
    
    Performance:
    ------------
    - O(1) for streak checks (just compare numbers)
    - O(n) for performance checks where n = days to check (7-30)
    - Total: <10ms per check-in (doesn't block user experience)
    """
    
    def __init__(self):
        """Initialize achievement service."""
        self.achievements = ACHIEVEMENTS
        logger.info(f"✅ AchievementService initialized with {len(ACHIEVEMENTS)} achievements")
    
    def check_achievements(
        self, 
        user: User, 
        recent_checkins: List[DailyCheckIn]
    ) -> List[str]:
        """
        Check if user unlocked any new achievements.
        
        This is the main entry point called by CheckInAgent after each check-in.
        
        Algorithm:
        ----------
        1. Check streak-based achievements (O(1) - just compare current_streak to milestones)
        2. Check performance achievements (O(n) - iterate last 7-30 check-ins)
        3. Check special achievements (O(1) - compare metadata)
        4. Return only achievements not already in user.achievements (duplicate prevention)
        
        Args:
            user: User profile with current streak, achievements list
            recent_checkins: Last 30 check-ins for performance analysis
        
        Returns:
            List of newly unlocked achievement IDs (e.g., ["week_warrior", "perfect_week"])
        
        Example:
            >>> user = User(user_id="123", streaks={"current_streak": 7}, achievements=[])
            >>> checkins = [... last 7 check-ins ...]
            >>> newly_unlocked = achievement_service.check_achievements(user, checkins)
            >>> newly_unlocked
            ['week_warrior']
        """
        newly_unlocked = []
        
        # 1. Check streak-based achievements (most common)
        newly_unlocked.extend(self._check_streak_achievements(user))
        
        # 2. Check performance-based achievements (requires recent data)
        newly_unlocked.extend(self._check_performance_achievements(user, recent_checkins))
        
        # 3. Check special achievements (rare but high-value)
        newly_unlocked.extend(self._check_special_achievements(user, recent_checkins))
        
        if newly_unlocked:
            logger.info(
                f"🎉 User {user.user_id} unlocked {len(newly_unlocked)} achievement(s): "
                f"{', '.join(newly_unlocked)}"
            )
        
        return newly_unlocked
    
    def _check_streak_achievements(self, user: User) -> List[str]:
        """
        Check streak-based achievements.
        
        Theory:
        -------
        Streak achievements use **progressive goal-setting**:
        - Early goals are easy (1, 7 days) - high success rate creates momentum
        - Middle goals are challenging (30, 90 days) - require sustained effort
        - Late goals are aspirational (180, 365 days) - identity-forming
        
        Complexity: O(1) - constant time (just 7 comparisons)
        
        Args:
            user: User profile with current_streak
        
        Returns:
            List of newly unlocked streak achievements
        """
        unlocked = []
        current_streak = user.streaks.current_streak
        
        # Milestone map: {streak_count: achievement_id}
        streak_milestones = {
            1: "first_checkin",
            7: "week_warrior",
            14: "fortnight_fighter",
            30: "month_master",
            90: "quarter_conqueror",
            180: "half_year_hero",
            365: "year_yoda"
        }
        
        for milestone, achievement_id in streak_milestones.items():
            # Only unlock if:
            # 1. User has reached this milestone (current_streak >= milestone)
            # 2. Achievement not already unlocked (achievement_id not in list)
            if current_streak >= milestone and achievement_id not in user.achievements:
                unlocked.append(achievement_id)
                logger.info(
                    f"✅ Streak milestone: User {user.user_id} unlocked {achievement_id} "
                    f"(streak: {current_streak})"
                )
        
        return unlocked
    
    def _check_performance_achievements(
        self, 
        user: User, 
        recent_checkins: List[DailyCheckIn]
    ) -> List[str]:
        """
        Check performance-based achievements (perfect week/month, tier1 master, etc.).
        
        Theory:
        -------
        Performance achievements use **excellence benchmarking**:
        - Not just showing up, but performing at 100%
        - Creates higher standard than just consistency
        - Research: High performers motivated by excellence, not just completion
        
        Complexity: O(n) where n = days to check (7-30)
        
        Algorithm:
        ----------
        1. Perfect Week: Check last 7 check-ins, all must be 100% compliance
        2. Perfect Month: Check last 30 check-ins, all must be 100% compliance
        3. Tier 1 Master: Check last 30 check-ins, all Tier 1 items must be complete
        4. Zero Breaks Month: Check last 30 check-ins, all must have zero_porn = True
        
        Args:
            user: User profile
            recent_checkins: Last 30 check-ins (sorted oldest to newest)
        
        Returns:
            List of newly unlocked performance achievements
        """
        unlocked = []
        
        # Perfect Week: 7 consecutive days at 100% compliance
        if len(recent_checkins) >= 7:
            last_7 = recent_checkins[-7:]  # Get last 7 check-ins
            if all(c.compliance_score == 100.0 for c in last_7):
                if "perfect_week" not in user.achievements:
                    unlocked.append("perfect_week")
                    logger.info(
                        f"✅ Performance milestone: User {user.user_id} unlocked perfect_week "
                        f"(7 days at 100%)"
                    )
        
        # Perfect Month: 30 consecutive days at 100% compliance
        if len(recent_checkins) >= 30:
            last_30 = recent_checkins[-30:]
            if all(c.compliance_score == 100.0 for c in last_30):
                if "perfect_month" not in user.achievements:
                    unlocked.append("perfect_month")
                    logger.info(
                        f"✅ Performance milestone: User {user.user_id} unlocked perfect_month "
                        f"(30 days at 100%)"
                    )
        
        # Tier 1 Master: 30 consecutive days with all Tier 1 items complete
        if len(recent_checkins) >= 30:
            last_30 = recent_checkins[-30:]
            if all(self._all_tier1_complete(c) for c in last_30):
                if "tier1_master" not in user.achievements:
                    unlocked.append("tier1_master")
                    logger.info(
                        f"✅ Performance milestone: User {user.user_id} unlocked tier1_master "
                        f"(30 days all Tier 1 complete)"
                    )
        
        # Zero Breaks Month: 30 consecutive days with zero porn
        if len(recent_checkins) >= 30:
            last_30 = recent_checkins[-30:]
            if all(c.tier1_non_negotiables.zero_porn for c in last_30):
                if "zero_breaks_month" not in user.achievements:
                    unlocked.append("zero_breaks_month")
                    logger.info(
                        f"✅ Performance milestone: User {user.user_id} unlocked zero_breaks_month "
                        f"(30 days zero porn)"
                    )
        
        return unlocked
    
    def _check_special_achievements(
        self, 
        user: User, 
        recent_checkins: List[DailyCheckIn]
    ) -> List[str]:
        """
        Check special achievements (comeback king, shield master, etc.).
        
        Theory:
        -------
        Special achievements create **narrative moments**:
        - Comeback King: Celebrates resilience (growth mindset)
        - Shield Master: Rewards strategic use of safety nets
        - These create stories users tell themselves and others
        
        Complexity: O(1) - constant time checks
        
        Args:
            user: User profile with streak history and shield usage
            recent_checkins: Recent check-ins (not used for special achievements)
        
        Returns:
            List of newly unlocked special achievements
        """
        unlocked = []
        
        # Phase D: Read recovery tracking fields (backward-compatible with getattr)
        streak_before_reset = getattr(user.streaks, 'streak_before_reset', 0) or 0
        last_reset_date = getattr(user.streaks, 'last_reset_date', None)
        has_recent_reset = last_reset_date is not None and streak_before_reset > 0
        
        # Comeback Kid: Reached 3 days after a reset (Phase D)
        # Rewards the user for proving the reset was temporary
        if (has_recent_reset and 
            user.streaks.current_streak >= 3 and
            "comeback_kid" not in user.achievements):
            unlocked.append("comeback_kid")
            logger.info(
                f"✅ Special milestone: User {user.user_id} unlocked comeback_kid "
                f"(3 days after reset from {streak_before_reset})"
            )
        
        # Comeback King: Reached 7 days after a reset (Phase D enhancement)
        # Previously required rebuilding to longest_streak. Now triggers at 7 days
        # post-reset, which is more achievable and encouraging.
        if (has_recent_reset and
            user.streaks.current_streak >= 7 and
            "comeback_king" not in user.achievements):
            unlocked.append("comeback_king")
            logger.info(
                f"✅ Special milestone: User {user.user_id} unlocked comeback_king "
                f"(7 days after reset from {streak_before_reset})"
            )
        
        # Comeback Legend: Exceeded previous best streak after a reset (Phase D)
        # The ultimate vindication — proving the reset made you stronger
        if (has_recent_reset and
            user.streaks.current_streak > streak_before_reset and
            streak_before_reset >= 3 and
            "comeback_legend" not in user.achievements):
            unlocked.append("comeback_legend")
            logger.info(
                f"✅ Special milestone: User {user.user_id} unlocked comeback_legend "
                f"(exceeded {streak_before_reset} days with {user.streaks.current_streak})"
            )
        
        # Shield Master: User has used all 3 shields in a month
        # This rewards strategic shield usage, not hoarding
        if user.streak_shields.used >= 3:
            if "shield_master" not in user.achievements:
                unlocked.append("shield_master")
                logger.info(
                    f"✅ Special milestone: User {user.user_id} unlocked shield_master "
                    f"(used {user.streak_shields.used} shields)"
                )
        
        return unlocked
    
    def _all_tier1_complete(self, checkin: DailyCheckIn) -> bool:
        """
        Check if all Tier 1 items are complete for a check-in.
        
        Uses date-aware logic from compliance.py to handle Phase 3D backward
        compatibility. Check-ins from before Phase 3D only had 5 items, so
        skill_building is excluded from the check for those dates.
        
        Args:
            checkin: Daily check-in to evaluate
        
        Returns:
            True if all applicable Tier 1 items completed, False otherwise
        """
        from src.utils.compliance import is_all_tier1_complete
        return is_all_tier1_complete(checkin.tier1_non_negotiables, checkin.date)
    
    def unlock_achievement(self, user_id: str, achievement_id: str) -> None:
        """
        Unlock achievement for user (persist to Firestore).
        
        This method is called by CheckInAgent after check_achievements() returns
        newly unlocked achievement IDs.
        
        Workflow:
        ---------
        1. Call firestore_service.unlock_achievement() (handles duplicate check)
        2. Log success
        3. Firestore updates User.achievements list with ArrayUnion (atomic)
        
        Args:
            user_id: User ID
            achievement_id: Achievement to unlock (e.g., "week_warrior")
        
        Side Effects:
            - Updates Firestore User document
            - Logs unlock event
        """
        try:
            # Firestore service handles duplicate prevention and atomic update
            firestore_service.unlock_achievement(user_id, achievement_id)
            logger.info(f"✅ Successfully unlocked {achievement_id} for user {user_id}")
        except Exception as e:
            logger.error(f"❌ Failed to unlock achievement {achievement_id} for user {user_id}: {e}")
    
    def get_achievement(self, achievement_id: str) -> Optional[Achievement]:
        """
        Get achievement definition by ID.
        
        Used to fetch achievement details for display (name, icon, description).
        
        Args:
            achievement_id: Achievement ID (e.g., "week_warrior")
        
        Returns:
            Achievement object if found, None otherwise
        """
        return ACHIEVEMENTS.get(achievement_id)
    
    def get_celebration_message(self, achievement_id: str, user: User) -> str:
        """
        Generate celebration message for unlocked achievement.
        
        Theory:
        -------
        Celebration messages use **positive reinforcement psychology**:
        1. Immediate acknowledgment (🎉 ACHIEVEMENT UNLOCKED!)
        2. Specific accomplishment (icon + name + description)
        3. Social context (rarity tier messaging)
        4. Encouragement to continue
        
        Message Structure:
        ------------------
        Line 1: 🎉 ACHIEVEMENT UNLOCKED!
        Line 2: [icon] [name]
        Line 3: [description]
        Line 4: [context] (e.g., "You've built a 7-day streak!")
        Line 5: [rarity message] (e.g., "You're in the top 20%!")
        
        Args:
            achievement_id: Achievement that was unlocked
            user: User profile (for personalized context)
        
        Returns:
            Formatted celebration message (multi-line string)
        
        Example Output:
            🎉 **ACHIEVEMENT UNLOCKED!**
            
            🏆 **Month Master**
            30 consecutive days - Top 10% territory
            
            You've built a 30-day streak! 🔥
            You're in the top 20%! 🌟
        """
        achievement = ACHIEVEMENTS.get(achievement_id)
        if not achievement:
            return "🎉 Achievement unlocked!"
        
        # Base celebration (lines 1-3)
        message = (
            f"🎉 **ACHIEVEMENT UNLOCKED!**\n\n"
            f"{achievement.icon} **{achievement.name}**\n"
            f"{achievement.description}\n\n"
        )
        
        # Add context based on achievement type (line 4)
        if "streak" in achievement.criteria:
            streak_days = achievement.criteria["streak"]
            message += f"You've built a {streak_days}-day streak! 🔥\n"
        elif "days" in achievement.criteria:
            days = achievement.criteria["days"]
            if achievement_id == "perfect_week":
                message += f"7 consecutive days at 100% compliance! ⭐\n"
            elif achievement_id == "perfect_month":
                message += f"30 consecutive days at 100% compliance! 🌟\n"
            elif achievement_id == "tier1_master":
                message += f"30 days of complete Tier 1 mastery! 💯\n"
            elif achievement_id == "zero_breaks_month":
                message += f"30 days without porn - incredible discipline! 🚫\n"
        elif achievement_id == "comeback_kid":
            message += f"3 days back after a reset — the comeback is real! 🐣\n"
        elif achievement_id == "comeback_king":
            message += f"A full week rebuilt — {user.streaks.current_streak} days and counting! 🦁\n"
        elif achievement_id == "comeback_legend":
            streak_before = getattr(user.streaks, 'streak_before_reset', 0) or 0
            message += (
                f"You surpassed your previous {streak_before}-day streak! "
                f"Now at {user.streaks.current_streak} days! 👑\n"
            )
        elif achievement_id == "shield_master":
            message += f"You've mastered the strategic use of shields! 🛡️\n"
        
        # Add rarity indicator (line 5)
        rarity_messages = {
            "common": "A great start! 💪",
            "uncommon": "Nice milestone! Keep going! 🌱",
            "rare": "You're in the top 20%! 🌟",
            "epic": "Elite territory! Top 5%! 💎",
            "legendary": "LEGENDARY! You're in the 1%! 👑"
        }
        message += rarity_messages.get(achievement.rarity, "Keep going!")
        
        return message
    
    def get_all_achievements(self) -> Dict[str, Achievement]:
        """
        Get all achievement definitions.
        
        Used for:
        - /achievements command (display all achievements and unlock status)
        - Admin dashboard
        - Testing
        
        Returns:
            Dictionary of all achievements {achievement_id: Achievement}
        """
        return ACHIEVEMENTS
    
    def calculate_percentile(self, user_streak: int) -> Optional[int]:
        """
        Calculate user's percentile based on streak compared to all users.
        
        Theory - Social Comparison Theory (Festinger, 1954):
        -----------------------------------------------------
        Humans determine self-worth through social comparison. Percentile rankings
        create two psychological effects:
        1. **Upward Comparison:** "I'm in top 10%, want to reach top 5%" (motivation)
        2. **Status Signaling:** "I'm better than 90% of users" (self-esteem)
        
        Algorithm:
        ----------
        1. Fetch all active users from Firestore
        2. Extract their current streaks into array
        3. Sort array descending (highest first)
        4. Use binary search (bisect) to find user's rank
        5. Calculate percentile: (total - rank) / total * 100
        
        Complexity: O(n log n) where n = number of users
        - Fetch: O(n)
        - Sort: O(n log n)
        - Binary search: O(log n)
        - Total: O(n log n)
        
        For 1,000 users: ~10ms (acceptable)
        
        Args:
            user_streak: User's current streak count
        
        Returns:
            Percentile (0-100) where 100 = best, 0 = worst
            None if <10 users (insufficient sample size)
        
        Example:
            100 users, streaks: [180, 90, 60, 30, 30, 28, ...]
            User has 30-day streak
            Rank: 5 (4 users ahead, ties broken arbitrarily)
            Percentile: (100 - 5) / 100 * 100 = 95th percentile = "TOP 5%"
        """
        try:
            # Get all active users
            all_users = firestore_service.get_all_users()
            
            # Need at least 10 users for meaningful percentile
            if len(all_users) < 10:
                logger.debug(
                    f"Not enough users for percentile calculation "
                    f"({len(all_users)} < 10 minimum)"
                )
                return None
            
            # Extract streaks and sort descending (highest first)
            streaks = [u.streaks.current_streak for u in all_users]
            streaks.sort(reverse=True)
            
            # Find user's rank using binary search
            # bisect_right finds insertion point for value in sorted list
            # For reverse-sorted list, we need to find position in normal sort
            # Convert to ascending for bisect, then invert
            streaks_ascending = sorted(streaks)
            rank_ascending = bisect.bisect_right(streaks_ascending, user_streak)
            rank = len(streaks) - rank_ascending
            
            # Calculate percentile (higher percentile = better performance)
            # If rank = 0 (best), percentile = 100
            # If rank = len-1 (worst), percentile = 0
            percentile = ((len(streaks) - rank) / len(streaks)) * 100
            
            logger.debug(
                f"Percentile calculation: {user_streak} days → "
                f"rank {rank}/{len(streaks)} → {int(percentile)}th percentile"
            )
            
            return int(percentile)
            
        except Exception as e:
            logger.error(f"❌ Failed to calculate percentile: {e}", exc_info=True)
            return None
    
    def get_social_proof_message(self, user: User) -> Optional[str]:
        """
        Generate social proof message based on user's percentile.
        
        Theory - Why Percentiles Work:
        -------------------------------
        1. **Concrete Status:** "Top 10%" is clearer than "you're doing well"
        2. **Aspirational:** Creates desire to reach next tier (Top 10% → Top 5%)
        3. **Validation:** Confirms user's effort is exceptional
        4. **Social Identity:** Becomes part of self-concept ("I'm a top performer")
        
        Privacy Design:
        ---------------
        - Never reveal other users' names or exact ranks
        - Never show total user count (keeps it abstract)
        - Focus on user's accomplishment, not competition
        
        Threshold:
        ----------
        Only show social proof for streaks ≥ 30 days because:
        - Early streaks too volatile (someone at 7 days might be "top 50%" today, "bottom 50%" tomorrow)
        - Prevents discouragement for new users
        - 30+ days is meaningful achievement worth celebrating
        
        Percentile Tiers:
        ------------------
        - ≥99: TOP 1% 👑 (legendary)
        - ≥95: TOP 5% 💎 (elite)
        - ≥90: TOP 10% 🌟 (excellent)
        - ≥75: TOP 25% 🏅 (above average)
        - <75: "Ahead of X%" 💪 (encouragement)
        
        Args:
            user: User profile with current streak
        
        Returns:
            Social proof message string, or None if not applicable
        
        Example Output:
            "📊 You're in the **TOP 10%** of users with a 45-day streak! 🌟"
        """
        streak = user.streaks.current_streak
        
        # Only show social proof for meaningful streaks (30+ days)
        if streak < 30:
            logger.debug(f"Streak {streak} < 30, skipping social proof")
            return None
        
        # Calculate percentile
        percentile = self.calculate_percentile(streak)
        
        if percentile is None:
            logger.debug("Percentile calculation returned None (insufficient users)")
            return None
        
        # Generate message based on percentile tier
        if percentile >= 99:
            # TOP 1% - Legendary status
            return f"📊 You're in the **TOP 1%** of users with a {streak}-day streak! 👑"
        
        elif percentile >= 95:
            # TOP 5% - Elite territory
            return f"📊 You're in the **TOP 5%** of users with a {streak}-day streak! 💎"
        
        elif percentile >= 90:
            # TOP 10% - Excellent performance
            return f"📊 You're in the **TOP 10%** of users with a {streak}-day streak! 🌟"
        
        elif percentile >= 75:
            # TOP 25% - Above average
            return f"📊 You're in the **TOP 25%** of users with a {streak}-day streak! 🏅"
        
        else:
            # <75th percentile - Still encouraging
            # Show what they're ahead of (downward comparison for validation)
            return f"📊 Your {streak}-day streak puts you ahead of {percentile}% of users! 💪"
    
    def get_user_progress(self, user: User) -> Dict[str, any]:
        """
        Get user's achievement progress statistics.
        
        Returns:
            {
                "total_unlocked": 5,
                "total_available": 13,
                "percentage": 38.5,
                "rarity_breakdown": {
                    "common": 3,
                    "rare": 1,
                    "epic": 1,
                    "legendary": 0
                },
                "next_milestone": "month_master"
            }
        """
        total_unlocked = len(user.achievements)
        total_available = len(ACHIEVEMENTS)
        percentage = (total_unlocked / total_available * 100) if total_available > 0 else 0
        
        # Count by rarity
        rarity_breakdown = {"common": 0, "rare": 0, "epic": 0, "legendary": 0}
        for achievement_id in user.achievements:
            achievement = ACHIEVEMENTS.get(achievement_id)
            if achievement:
                rarity_breakdown[achievement.rarity] += 1
        
        # Find next streak milestone
        current_streak = user.streaks.current_streak
        streak_milestones = [7, 14, 30, 90, 180, 365]
        next_milestone_days = None
        next_milestone_id = None
        
        for milestone in streak_milestones:
            if current_streak < milestone:
                next_milestone_days = milestone
                milestone_map = {
                    7: "week_warrior",
                    14: "fortnight_fighter",
                    30: "month_master",
                    90: "quarter_conqueror",
                    180: "half_year_hero",
                    365: "year_yoda"
                }
                next_milestone_id = milestone_map[milestone]
                break
        
        return {
            "total_unlocked": total_unlocked,
            "total_available": total_available,
            "percentage": round(percentage, 1),
            "rarity_breakdown": rarity_breakdown,
            "next_milestone": next_milestone_id,
            "next_milestone_days": next_milestone_days,
            "days_until_next": next_milestone_days - current_streak if next_milestone_days else None
        }


# =====================================================
# GLOBAL INSTANCE
# =====================================================

achievement_service = AchievementService()
