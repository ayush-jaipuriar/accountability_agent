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

from src.models.schemas import User, DailyCheckIn, UserStreaks
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
    
    # ===== User Management =====
    
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
