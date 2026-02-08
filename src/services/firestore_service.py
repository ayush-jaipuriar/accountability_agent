"""
Firestore Service Layer
=======================

Handles all database operations for the accountability agent.

Architecture Pattern: Service Layer
- All database logic centralized here
- Rest of app uses this service (no direct Firestore calls)
- Makes testing easier (can mock this service)

Firestore Structure:
    users/
      {user_id}/                      # Document per user
        - telegram_id, name, streaks, etc.
    
    daily_checkins/
      {user_id}/                      # Document (container)
        checkins/                     # Subcollection
          {date}/                     # Document per day (e.g., "2026-01-30")
            - tier1_non_negotiables, responses, compliance_score, etc.

Why Subcollections?
- Organizes check-ins under each user
- Efficient queries (get all check-ins for one user)
- Automatic cleanup (delete user → deletes all their check-ins)
"""

from google.cloud import firestore
from google.cloud.firestore_v1 import FieldFilter
from datetime import datetime, timedelta
from typing import Optional, List
import logging

from src.models.schemas import User, DailyCheckIn, UserStreaks, ReminderStatus, Achievement
from src.utils.timezone_utils import get_current_date_ist, utc_to_ist


logger = logging.getLogger(__name__)


class FirestoreService:
    """
    Service for interacting with Firestore database.
    
    Collections:
    - users: User profiles
    - daily_checkins: Check-in records (with subcollections)
    
    Usage:
        from src.services.firestore_service import firestore_service
        
        user = firestore_service.get_user("123456789")
        firestore_service.store_checkin(user_id, checkin)
    """
    
    def __init__(self):
        """
        Initialize Firestore client.
        
        The client automatically uses credentials from:
        1. GOOGLE_APPLICATION_CREDENTIALS environment variable
        2. Service account key file specified in config
        """
        self.db = firestore.Client()
        logger.info("✅ Firestore client initialized")
    
    # ===== User Operations =====
    
    def create_user(self, user: User) -> None:
        """
        Create new user profile in Firestore.
        
        Called when user sends /start command for the first time.
        
        Args:
            user: User object with profile data
            
        Example:
            >>> user = User(
            ...     user_id="123456789",
            ...     telegram_id=123456789,
            ...     name="Ayush"
            ... )
            >>> firestore_service.create_user(user)
        """
        try:
            user_ref = self.db.collection('users').document(user.user_id)
            user_ref.set(user.to_firestore())
            logger.info(f"✅ Created user: {user.user_id} ({user.name})")
        except Exception as e:
            logger.error(f"❌ Failed to create user: {e}")
            raise
    
    def get_user(self, user_id: str) -> Optional[User]:
        """
        Fetch user profile by ID.
        
        Args:
            user_id: User's unique ID (Telegram ID as string)
            
        Returns:
            User object if exists, None if not found
            
        Example:
            >>> user = firestore_service.get_user("123456789")
            >>> if user:
            ...     print(user.streaks.current_streak)
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            doc = user_ref.get()
            
            if doc.exists:
                return User.from_firestore(doc.to_dict())
            else:
                logger.warning(f"⚠️ User not found: {user_id}")
                return None
        except Exception as e:
            logger.error(f"❌ Failed to fetch user: {e}")
            raise
    
    def user_exists(self, user_id: str) -> bool:
        """
        Check if user exists in database.
        
        Lightweight check (doesn't fetch full document).
        
        Args:
            user_id: User's unique ID
            
        Returns:
            bool: True if user exists
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            return user_ref.get().exists
        except Exception as e:
            logger.error(f"❌ Failed to check user existence: {e}")
            return False
    
    def update_user_streak(self, user_id: str, streak_data: dict) -> None:
        """
        Update user's streak information.
        
        Called after each check-in to update:
        - current_streak
        - longest_streak
        - last_checkin_date
        - total_checkins
        
        Args:
            user_id: User's unique ID
            streak_data: Dictionary with streak updates (from update_streak_data())
            
        Example:
            >>> streak_updates = {
            ...     "current_streak": 48,
            ...     "longest_streak": 48,
            ...     "last_checkin_date": "2026-01-30",
            ...     "total_checkins": 101
            ... }
            >>> firestore_service.update_user_streak(user_id, streak_updates)
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            
            # Update nested streaks field and updated_at timestamp
            user_ref.update({
                "streaks": streak_data,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"✅ Updated streak for {user_id}: {streak_data['current_streak']} days")
        except Exception as e:
            logger.error(f"❌ Failed to update user streak: {e}")
            raise
    
    def update_user_mode(self, user_id: str, mode: str) -> None:
        """
        Update user's constitution mode.
        
        Modes: optimization, maintenance, survival
        
        Args:
            user_id: User's unique ID
            mode: New constitution mode
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                "constitution_mode": mode,
                "updated_at": datetime.utcnow()
            })
            logger.info(f"✅ Updated mode for {user_id}: {mode}")
        except Exception as e:
            logger.error(f"❌ Failed to update user mode: {e}")
            raise
    
    def update_user_career_mode(self, user_id: str, career_mode: str) -> bool:
        """
        Update user's career mode (Phase 3D).
        
        Modes: skill_building, job_searching, employed
        
        Args:
            user_id: User's unique ID
            career_mode: New career mode
            
        Returns:
            bool: True if update successful, False otherwise
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                "career_mode": career_mode,
                "updated_at": datetime.utcnow()
            })
            logger.info(f"✅ Updated career mode for {user_id}: {career_mode}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update career mode: {e}")
            return False
    
    def update_user(self, user_id: str, updates: dict) -> bool:
        """
        Generic update for user fields in Firestore.
        
        Use this for ad-hoc field updates that don't have a dedicated method.
        For specific updates, prefer dedicated methods (update_user_streak,
        update_user_mode, etc.) which include validation and logging.
        
        How Firestore update() works:
        - Only modifies the specified fields (doesn't overwrite entire doc)
        - Uses dot-notation for nested fields (e.g., "streaks.current_streak")
        - Atomic per-field updates
        
        Args:
            user_id: User's unique ID
            updates: Dictionary of field names to new values
            
        Returns:
            bool: True if update successful, False on error
            
        Example:
            >>> firestore_service.update_user("123456", {
            ...     "quick_checkin_count": 0,
            ...     "quick_checkin_used_dates": []
            ... })
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            updates["updated_at"] = datetime.utcnow()
            user_ref.update(updates)
            logger.info(f"✅ Updated user {user_id}: {list(updates.keys())}")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to update user {user_id}: {e}")
            return False
    
    # ===== Check-In Operations =====
    
    def store_checkin(self, user_id: str, checkin: DailyCheckIn) -> None:
        """
        Store completed check-in in Firestore.
        
        Path: daily_checkins/{user_id}/checkins/{date}
        
        Args:
            user_id: User's unique ID
            checkin: Complete check-in data
            
        Example:
            >>> checkin = DailyCheckIn(...)
            >>> firestore_service.store_checkin(user_id, checkin)
        """
        try:
            checkin_ref = (
                self.db.collection('daily_checkins')
                .document(user_id)
                .collection('checkins')
                .document(checkin.date)
            )
            
            checkin_ref.set(checkin.to_firestore())
            
            logger.info(
                f"✅ Stored check-in for {user_id} on {checkin.date} "
                f"(Compliance: {checkin.compliance_score}%)"
            )
        except Exception as e:
            logger.error(f"❌ Failed to store check-in: {e}")
            raise
    
    def get_checkin(self, user_id: str, date: str) -> Optional[DailyCheckIn]:
        """
        Fetch check-in for specific date.
        
        Args:
            user_id: User's unique ID
            date: Date in YYYY-MM-DD format
            
        Returns:
            DailyCheckIn object if exists, None if not found
            
        Example:
            >>> checkin = firestore_service.get_checkin(user_id, "2026-01-30")
            >>> if checkin:
            ...     print(checkin.compliance_score)
        """
        try:
            checkin_ref = (
                self.db.collection('daily_checkins')
                .document(user_id)
                .collection('checkins')
                .document(date)
            )
            
            doc = checkin_ref.get()
            
            if doc.exists:
                return DailyCheckIn.from_firestore(doc.to_dict())
            else:
                return None
        except Exception as e:
            logger.error(f"❌ Failed to fetch check-in: {e}")
            raise
    
    def checkin_exists(self, user_id: str, date: str) -> bool:
        """
        Check if user already completed check-in for specific date.
        
        Used to prevent duplicate check-ins on same day.
        
        Args:
            user_id: User's unique ID
            date: Date in YYYY-MM-DD format
            
        Returns:
            bool: True if check-in exists
            
        Example:
            >>> today = get_current_date_ist()
            >>> if firestore_service.checkin_exists(user_id, today):
            ...     print("Already checked in today!")
        """
        try:
            checkin_ref = (
                self.db.collection('daily_checkins')
                .document(user_id)
                .collection('checkins')
                .document(date)
            )
            return checkin_ref.get().exists
        except Exception as e:
            logger.error(f"❌ Failed to check checkin existence: {e}")
            return False
    
    def get_recent_checkins(
        self,
        user_id: str,
        days: int = 7
    ) -> List[DailyCheckIn]:
        """
        Fetch recent check-ins for user.
        
        Used for:
        - Pattern detection (Phase 2)
        - Weekly reports (Phase 3)
        - Analytics
        
        Args:
            user_id: User's unique ID
            days: Number of days to look back (default: 7)
            
        Returns:
            List of DailyCheckIn objects, sorted by date (newest first)
            
        Example:
            >>> recent = firestore_service.get_recent_checkins(user_id, days=7)
            >>> for checkin in recent:
            ...     print(f"{checkin.date}: {checkin.compliance_score}%")
        """
        try:
            # Calculate date range
            from src.utils.timezone_utils import get_date_range_ist
            start_date, end_date = get_date_range_ist(days)
            
            # Query Firestore
            checkins_ref = (
                self.db.collection('daily_checkins')
                .document(user_id)
                .collection('checkins')
                .where(filter=FieldFilter('date', '>=', start_date))
                .where(filter=FieldFilter('date', '<=', end_date))
                .order_by('date', direction=firestore.Query.DESCENDING)
            )
            
            docs = checkins_ref.stream()
            
            checkins = []
            for doc in docs:
                checkins.append(DailyCheckIn.from_firestore(doc.to_dict()))
            
            logger.info(f"✅ Fetched {len(checkins)} check-ins for {user_id} (last {days} days)")
            return checkins
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch recent check-ins: {e}")
            raise
    
    def get_all_checkins(self, user_id: str) -> List[DailyCheckIn]:
        """
        Fetch ALL check-ins for user (no date limit).
        
        Warning: Expensive operation. Use only for:
        - Monthly reports
        - Full data export
        - Analytics dashboards
        
        Args:
            user_id: User's unique ID
            
        Returns:
            List of all DailyCheckIn objects, sorted by date
        """
        try:
            checkins_ref = (
                self.db.collection('daily_checkins')
                .document(user_id)
                .collection('checkins')
                .order_by('date', direction=firestore.Query.DESCENDING)
            )
            
            docs = checkins_ref.stream()
            
            checkins = []
            for doc in docs:
                checkins.append(DailyCheckIn.from_firestore(doc.to_dict()))
            
            logger.info(f"✅ Fetched {len(checkins)} total check-ins for {user_id}")
            return checkins
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch all check-ins: {e}")
            raise
    
    def update_checkin(self, user_id: str, date: str, updates: dict) -> bool:
        """
        Update specific fields of an existing check-in document.
        
        Used by the /correct command to fix mistakes in today's check-in.
        
        Args:
            user_id: User's unique ID
            date: Check-in date (YYYY-MM-DD)
            updates: Dictionary of fields to update
            
        Returns:
            bool: True if update successful
        """
        try:
            checkin_ref = (
                self.db.collection('daily_checkins')
                .document(user_id)
                .collection('checkins')
                .document(date)
            )
            
            updates["corrected_at"] = datetime.utcnow()
            checkin_ref.update(updates)
            
            logger.info(f"✅ Updated check-in for {user_id} on {date}: {list(updates.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to update check-in: {e}")
            return False
    
    def store_checkin_with_streak_update(
        self,
        user_id: str,
        checkin: DailyCheckIn,
        streak_updates: dict
    ) -> None:
        """
        Atomically store check-in AND update streak in a single Firestore transaction.
        
        WHY A TRANSACTION?
        ------------------
        Previously, store_checkin() and update_user_streak() were two separate writes.
        If the second write failed (e.g., Firestore timeout), the check-in would exist
        in the database but the streak would NOT be updated. On the next check-in,
        the streak logic would see a stale last_checkin_date, detect a multi-day gap,
        and incorrectly RESET the streak -- even though the user actually checked in.
        
        A Firestore transaction guarantees all-or-nothing: either BOTH the check-in
        record and streak update succeed, or NEITHER does. This prevents data corruption.
        
        HOW FIRESTORE TRANSACTIONS WORK:
        ---------------------------------
        1. Transaction reads current state (snapshot isolation)
        2. Transaction performs writes
        3. If any read data changed since step 1, Firestore retries automatically
        4. After max retries (default 5), raises an exception
        5. All writes in a transaction are applied atomically
        
        Args:
            user_id: User's unique ID
            checkin: Complete check-in data to store
            streak_updates: Dictionary with streak field updates (from update_streak_data())
            
        Raises:
            Exception: If transaction fails after retries (caller should handle)
        """
        transaction = self.db.transaction()
        
        @firestore.transactional
        def _transactional_checkin(transaction, user_id, checkin, streak_updates):
            # Reference to the check-in document
            checkin_ref = (
                self.db.collection('daily_checkins')
                .document(user_id)
                .collection('checkins')
                .document(checkin.date)
            )
            
            # Reference to the user document
            user_ref = self.db.collection('users').document(user_id)
            
            # Write 1: Store the check-in
            transaction.set(checkin_ref, checkin.to_firestore())
            
            # Write 2: Update the streak (remove transient keys that are not Firestore fields)
            _transient_keys = {'milestone_hit', 'is_reset', 'recovery_message', 'recovery_fact'}
            streak_data_for_firestore = {
                k: v for k, v in streak_updates.items() 
                if k not in _transient_keys
            }
            transaction.update(user_ref, {
                "streaks": streak_data_for_firestore,
                "updated_at": datetime.utcnow()
            })
        
        try:
            _transactional_checkin(transaction, user_id, checkin, streak_updates)
            logger.info(
                f"✅ Transactional check-in + streak update for {user_id} on {checkin.date} "
                f"(Compliance: {checkin.compliance_score}%, Streak: {streak_updates.get('current_streak')})"
            )
        except Exception as e:
            logger.error(
                f"❌ Transaction failed for {user_id} check-in on {checkin.date}: {e}"
            )
            raise
    
    # ===== User Management =====
    
    def get_all_users(self) -> List[User]:
        """
        Get list of ALL users in the system.
        
        Alias for get_active_users for Phase 2 compatibility.
        
        Returns:
            List of User objects
        """
        return self.get_active_users()
    
    def get_active_users(self) -> List[User]:
        """
        Get list of all active users.
        
        Used by:
        - Pattern detection scanning (Phase 2)
        - Broadcast messages
        - Analytics
        
        Returns:
            List of User objects
        """
        try:
            users_ref = self.db.collection('users')
            docs = users_ref.stream()
            
            users = []
            for doc in docs:
                users.append(User.from_firestore(doc.to_dict()))
            
            logger.info(f"✅ Fetched {len(users)} active users")
            return users
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch active users: {e}")
            raise
    
    def get_users_by_timezones(self, timezone_ids: list[str]) -> List[User]:
        """
        Get all users whose timezone matches one of the given IANA timezone IDs.
        
        Used by the bucket-based reminder system: find all users in timezones
        that are currently at 9 PM (or 9:30, or 10 PM) and send reminders.
        
        Args:
            timezone_ids: List of IANA timezone strings (e.g., ["Asia/Kolkata", "Asia/Dubai"])
            
        Returns:
            List of User objects in matching timezones
        """
        try:
            if not timezone_ids:
                return []
            
            all_users = self.get_active_users()
            matching = [
                u for u in all_users
                if getattr(u, 'timezone', 'Asia/Kolkata') in timezone_ids
            ]
            
            logger.info(
                f"✅ Found {len(matching)} users in timezones {timezone_ids} "
                f"(out of {len(all_users)} total)"
            )
            return matching
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch users by timezone: {e}")
            return []

    # ===== Intervention Logging (Phase 2) =====
    
    def log_intervention(
        self,
        user_id: str,
        pattern_type: str,
        severity: str,
        data: dict,
        message: str
    ) -> None:
        """
        Log intervention sent to user (Phase 2).
        
        Interventions are stored for:
        - Analytics (how often patterns occur)
        - Effectiveness tracking (did user improve after intervention?)
        - Historical context (show user past patterns)
        
        Firestore Structure:
        --------------------
        interventions/{user_id}/interventions/{auto_id}:
        {
            "pattern_type": "sleep_degradation",
            "severity": "high",
            "detected_at": "2026-02-02T10:30:00Z",
            "data": {"avg_sleep": 5.3, "consecutive_days": 3},
            "message": "🚨 PATTERN ALERT: Sleep Degradation...",
            "sent_at": "2026-02-02T10:30:15Z",
            "user_response": null,  # For Phase 3: track acknowledgment
            "resolved": false  # For Phase 3: track if pattern was fixed
        }
        
        Args:
            user_id: User ID
            pattern_type: Type of pattern (sleep_degradation, etc.)
            severity: Severity level (critical, high, medium, low)
            data: Pattern-specific data
            message: Intervention message sent
        """
        try:
            intervention_data = {
                "user_id": user_id,
                "pattern_type": pattern_type,
                "severity": severity,
                "detected_at": datetime.utcnow(),
                "data": data,
                "message": message,
                "sent_at": datetime.utcnow(),
                "user_response": None,
                "resolved": False
            }
            
            # Store in interventions collection
            self.db.collection('interventions').document(user_id).collection('interventions').add(
                intervention_data
            )
            
            logger.info(f"✅ Logged intervention for {user_id}: {pattern_type} ({severity})")
            
        except Exception as e:
            logger.error(f"❌ Failed to log intervention: {e}")
            # Don't raise - logging failure shouldn't block intervention sending
    
    def get_recent_interventions(
        self,
        user_id: str,
        days: int = 30
    ) -> List[dict]:
        """
        Get recent interventions for user (Phase 2).
        
        Used for:
        - Checking if intervention already sent for current pattern
        - Historical pattern analysis
        - Effectiveness tracking
        
        Args:
            user_id: User ID
            days: Number of days to look back
            
        Returns:
            List of intervention dictionaries
        """
        try:
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            interventions_ref = (
                self.db.collection('interventions')
                .document(user_id)
                .collection('interventions')
                .where(filter=FieldFilter('sent_at', '>=', cutoff_date))
                .order_by('sent_at', direction=firestore.Query.DESCENDING)
            )
            
            docs = interventions_ref.stream()
            
            interventions = []
            for doc in docs:
                intervention_data = doc.to_dict()
                intervention_data['id'] = doc.id
                interventions.append(intervention_data)
            
            logger.info(f"✅ Fetched {len(interventions)} interventions for {user_id} (last {days} days)")
            return interventions
            
        except Exception as e:
            logger.error(f"❌ Failed to fetch recent interventions: {e}")
            return []
    
    # ===== Phase 3A: Reminder System =====
    
    def get_users_without_checkin_today(self, today_date: str) -> List[User]:
        """
        Get all users who haven't completed check-in today.
        
        Used by reminder system to send reminders at 9 PM, 9:30 PM, 10 PM.
        
        Args:
            today_date: Date in YYYY-MM-DD format
            
        Returns:
            List of users without check-in for today
        
        Phase 3A Implementation Note:
        -----------------------------
        This queries ALL users and checks each one. For 10-50 users, this is fine.
        For 1000+ users, we'd need to add a "last_checkin_date" field to users
        collection and query directly (but that adds complexity).
        """
        try:
            all_users = self.get_active_users()
            users_without_checkin = []
            
            for user in all_users:
                checkin = self.get_checkin(user.user_id, today_date)
                if not checkin:
                    users_without_checkin.append(user)
            
            logger.info(
                f"✅ Found {len(users_without_checkin)}/{len(all_users)} users "
                f"without check-in for {today_date}"
            )
            return users_without_checkin
            
        except Exception as e:
            logger.error(f"❌ Failed to get users without check-in: {e}")
            return []
    
    def get_reminder_status(self, user_id: str, date: str) -> Optional[dict]:
        """
        Get reminder status for user on specific date.
        
        Args:
            user_id: User ID
            date: Date in YYYY-MM-DD format
            
        Returns:
            Dictionary with reminder status or None if not found
        """
        try:
            reminder_ref = (
                self.db.collection('reminder_status')
                .document(user_id)
                .collection('dates')
                .document(date)
            )
            doc = reminder_ref.get()
            
            if doc.exists:
                return doc.to_dict()
            return None
            
        except Exception as e:
            logger.error(f"❌ Failed to get reminder status: {e}")
            return None
    
    def set_reminder_sent(
        self,
        user_id: str,
        date: str,
        reminder_type: str  # 'first', 'second', or 'third'
    ) -> None:
        """
        Mark reminder as sent for user.
        
        Prevents duplicate reminders: If user checks in after reminder_first,
        don't send reminder_second.
        
        Args:
            user_id: User ID
            date: Date in YYYY-MM-DD format
            reminder_type: 'first', 'second', or 'third'
        """
        try:
            reminder_ref = (
                self.db.collection('reminder_status')
                .document(user_id)
                .collection('dates')
                .document(date)
            )
            
            # Get existing status
            doc = reminder_ref.get()
            if doc.exists:
                status = doc.to_dict()
            else:
                status = {
                    "user_id": user_id,
                    "date": date,
                    "first_sent": False,
                    "second_sent": False,
                    "third_sent": False
                }
            
            # Update specific reminder
            status[f"{reminder_type}_sent"] = True
            status[f"{reminder_type}_sent_at"] = datetime.utcnow()
            
            reminder_ref.set(status)
            logger.info(f"✅ Marked {reminder_type} reminder sent for {user_id} on {date}")
            
        except Exception as e:
            logger.error(f"❌ Failed to set reminder status: {e}")
    
    # ===== Phase 3A: Streak Shields =====
    
    def use_streak_shield(self, user_id: str) -> bool:
        """
        Use one streak shield to protect streak from breaking.
        
        CRITICAL FIX (Feb 2026): Shield usage now also updates last_checkin_date
        to the current date. Without this, the streak logic in streak.py sees a
        2+ day gap on the next check-in and resets the streak -- making the shield
        useless (shield consumed but streak still breaks).
        
        By advancing last_checkin_date to today, the next real check-in will see
        only a 1-day gap and correctly increment the streak.
        
        Returns True if shield was available and used, False if no shields left.
        
        Args:
            user_id: User ID
            
        Returns:
            bool: True if shield used successfully
        """
        try:
            user = self.get_user(user_id)
            if not user:
                return False
            
            # Check if shields available
            if user.streak_shields.available <= 0:
                logger.warning(f"⚠️ User {user_id} has no shields available")
                return False
            
            # Use shield
            user.streak_shields.used += 1
            user.streak_shields.available = user.streak_shields.total - user.streak_shields.used
            
            # Get today's date for bridging the gap (Phase B: timezone-aware)
            from src.utils.timezone_utils import get_checkin_date
            user_tz = getattr(user, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
            shielded_date = get_checkin_date(tz=user_tz)
            
            # Update Firestore: shield count AND last_checkin_date
            # The last_checkin_date update is what actually protects the streak.
            # Without it, streak.py:should_increment_streak() sees a multi-day gap
            # and resets the streak on the next check-in.
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                "streak_shields": user.streak_shields.model_dump(),
                "streaks.last_checkin_date": shielded_date,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(
                f"✅ Used streak shield for {user_id}. "
                f"last_checkin_date advanced to {shielded_date}. "
                f"Remaining: {user.streak_shields.available}/{user.streak_shields.total}"
            )
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to use streak shield: {e}")
            return False
    
    def reset_streak_shields(self, user_id: str) -> None:
        """
        Reset streak shields to full (3/3).
        
        Called monthly (every 30 days from last reset).
        
        Args:
            user_id: User ID
        """
        try:
            user = self.get_user(user_id)
            if not user:
                return
            
            # Reset shields
            user.streak_shields.used = 0
            user.streak_shields.available = user.streak_shields.total
            user_tz = getattr(user, 'timezone', 'Asia/Kolkata') or 'Asia/Kolkata'
            from src.utils.timezone_utils import get_current_date
            user.streak_shields.last_reset = get_current_date(user_tz)
            
            # Update Firestore
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                "streak_shields": user.streak_shields.model_dump(),
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"✅ Reset streak shields for {user_id} to {user.streak_shields.total}/{user.streak_shields.total}")
            
        except Exception as e:
            logger.error(f"❌ Failed to reset streak shields: {e}")
    
    # ===== Phase 3A: Quick Check-In Counter =====
    
    def increment_quick_checkin_count(self, user_id: str) -> int:
        """
        Increment weekly quick check-in counter.
        
        Returns new count.
        
        Args:
            user_id: User ID
            
        Returns:
            int: New quick check-in count
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            user = self.get_user(user_id)
            
            if not user:
                return 0
            
            new_count = user.quick_checkin_count + 1
            
            user_ref.update({
                "quick_checkin_count": new_count,
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"✅ Incremented quick check-in count for {user_id}: {new_count}/2")
            return new_count
            
        except Exception as e:
            logger.error(f"❌ Failed to increment quick check-in count: {e}")
            return 0
    
    def reset_quick_checkin_counts(self) -> None:
        """
        Reset quick check-in counter for all users.
        
        Called every Monday at midnight by cron job.
        """
        try:
            users = self.get_active_users()
            
            for user in users:
                user_ref = self.db.collection('users').document(user.user_id)
                user_ref.update({
                    "quick_checkin_count": 0,
                    "updated_at": datetime.utcnow()
                })
            
            logger.info(f"✅ Reset quick check-in counts for {len(users)} users")
            
        except Exception as e:
            logger.error(f"❌ Failed to reset quick check-in counts: {e}")
    
    # ===== Phase 3C: Achievements =====
    
    def unlock_achievement(self, user_id: str, achievement_id: str) -> None:
        """
        Unlock achievement for user.
        
        Args:
            user_id: User ID
            achievement_id: Achievement ID (e.g., "week_warrior")
        """
        try:
            user = self.get_user(user_id)
            if not user:
                return
            
            # Check if already unlocked
            if achievement_id in user.achievements:
                logger.warning(f"⚠️ Achievement {achievement_id} already unlocked for {user_id}")
                return
            
            # Add to achievements list
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                "achievements": firestore.ArrayUnion([achievement_id]),
                "updated_at": datetime.utcnow()
            })
            
            logger.info(f"✅ Unlocked achievement '{achievement_id}' for {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to unlock achievement: {e}")
    
    # ===== Phase 3B: Accountability Partners =====
    
    def get_user_by_telegram_username(self, telegram_username: str) -> Optional[User]:
        """
        Find user by their Telegram username (Phase 3B).
        
        When user wants to link accountability partner with /set_partner @username,
        this method searches Firestore for that username.
        
        Args:
            telegram_username: Telegram username (without @ symbol)
            
        Returns:
            User object if found, None otherwise
        """
        try:
            users_ref = self.db.collection('users')
            query = users_ref.where('telegram_username', '==', telegram_username).limit(1)
            docs = query.stream()
            
            for doc in docs:
                user_data = doc.to_dict()
                logger.info(f"Found user by username: @{telegram_username} → {user_data.get('name')}")
                return User.from_firestore(user_data)
            
            logger.info(f"No user found with username: @{telegram_username}")
            return None
            
        except Exception as e:
            logger.error(f"Error finding user by username @{telegram_username}: {e}")
            return None
    
    def set_accountability_partner(
        self,
        user_id: str,
        partner_id: Optional[str],
        partner_name: Optional[str]
    ) -> None:
        """
        Link or unlink accountability partners (Phase 3B).
        
        To link: Pass partner_id and partner_name
        To unlink: Pass None for both
        
        Args:
            user_id: Primary user ID
            partner_id: Partner user ID (None to unlink)
            partner_name: Partner's display name (None to unlink)
        """
        try:
            user_ref = self.db.collection('users').document(user_id)
            user_ref.update({
                "accountability_partner_id": partner_id,
                "accountability_partner_name": partner_name,
                "updated_at": datetime.utcnow()
            })
            
            if partner_id:
                logger.info(f"✅ Set accountability partner: {user_id} ↔️ {partner_name} ({partner_id})")
            else:
                logger.info(f"✅ Removed accountability partner for: {user_id}")
            
        except Exception as e:
            logger.error(f"❌ Failed to set accountability partner: {e}")
    
    def store_emotional_interaction(
        self,
        user_id: str,
        emotion_type: str,
        user_message: str,
        bot_response: str,
        timestamp: datetime
    ) -> None:
        """
        Store emotional support interaction for tracking (Phase 3B).
        
        **What is This?**
        Logs every time the emotional agent responds to a user. Useful for:
        - Analytics: Which emotions are most common?
        - Quality review: Are responses helpful?
        - Pattern detection: User in emotional crisis frequently?
        
        **Database Structure:**
        Collection: emotional_interactions
        Document ID: Auto-generated
        Fields:
        - user_id: User ID
        - emotion_type: Classified emotion
        - user_message: Original user message
        - bot_response: Bot's response
        - timestamp: When interaction occurred
        - created_at: Server timestamp
        
        Args:
            user_id: User ID
            emotion_type: Classified emotion (loneliness, porn_urge, etc.)
            user_message: User's original message
            bot_response: Bot's generated response
            timestamp: Interaction timestamp
        """
        try:
            self.db.collection('emotional_interactions').add({
                'user_id': user_id,
                'emotion_type': emotion_type,
                'user_message': user_message,
                'bot_response': bot_response,
                'timestamp': timestamp,
                'created_at': firestore.SERVER_TIMESTAMP
            })
            
            logger.info(f"✅ Logged emotional interaction: {user_id} - {emotion_type}")
            
        except Exception as e:
            logger.error(f"❌ Failed to log emotional interaction: {e}")
    
    # ===== Phase 3E: Pattern Retrieval =====
    
    def get_patterns(
        self,
        user_id: str,
        days: int = 30
    ) -> List:
        """
        Get detected patterns for user (Phase 3E Query Agent support).
        
        **Purpose:**
        Allows Query Agent to answer: "How often do I get sleep degradation?"
        
        **Firestore Structure:**
        patterns/{pattern_id}
        {
            user_id: str
            pattern_name: str (e.g., "sleep_degradation")
            detected_at: datetime
            severity: str
            data_points: List
        }
        
        Args:
            user_id: User ID to fetch patterns for
            days: Number of days to look back
            
        Returns:
            List of Pattern objects (empty if none found)
        """
        try:
            from datetime import datetime, timedelta
            
            # Calculate cutoff date
            cutoff_date = datetime.utcnow() - timedelta(days=days)
            
            # Query patterns collection
            patterns_ref = self.db.collection('patterns')
            query = patterns_ref.where('user_id', '==', user_id) \
                               .where('detected_at', '>=', cutoff_date) \
                               .order_by('detected_at', direction=firestore.Query.DESCENDING)
            
            patterns = []
            for doc in query.stream():
                patterns.append(doc.to_dict())
            
            logger.info(f"📊 Retrieved {len(patterns)} patterns for user {user_id} (last {days} days)")
            return patterns
            
        except Exception as e:
            # Graceful handling if patterns collection doesn't exist yet
            logger.warning(f"⚠️ Could not fetch patterns for {user_id}: {e}")
            return []  # Return empty list instead of crashing
    
    # ===== Health Check =====
    
    def test_connection(self) -> bool:
        """
        Test Firestore connection.
        
        Used for health checks and debugging.
        
        Returns:
            bool: True if connection successful
        """
        try:
            # Try to read from a collection (doesn't need to exist)
            list(self.db.collections())
            logger.info("✅ Firestore connection test passed")
            return True
        except Exception as e:
            logger.error(f"❌ Firestore connection test failed: {e}")
            return False


# ===== Singleton Instance =====
# Import this throughout the app: `from src.services.firestore_service import firestore_service`

firestore_service = FirestoreService()
