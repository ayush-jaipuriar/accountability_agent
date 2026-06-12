"""
Data Deletion Service
=====================

GDPR-compliant user data deletion.

Theory: Right to be Forgotten
--------------------------------
Users have the right to request complete deletion of their data.
This service removes all user-associated records from Firestore.
"""

import logging
from typing import Dict, Any

from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


class DataDeletionService:
    """Handle complete user data deletion (GDPR right to be forgotten)."""

    def delete_all_user_data(self, user_id: str) -> Dict[str, Any]:
        """
        Delete all data associated with a user.

        Deletes:
        - User profile (users/{user_id})
        - All check-ins (daily_checkins/{user_id}/checkins/*)
        - Goals (goals/* where user_id matches)
        - Challenges (challenges/* where user is participant)
        - Feedback (feedback/* where user_id matches)
        - Partner links (updates partner's accountability_partner_id)

        Returns:
            {"success": True, "deleted": {...}, "errors": [...]}
        """
        results = {
            "success": True,
            "deleted": {},
            "errors": [],
        }

        # 1. Unlink partner (if any)
        try:
            user = firestore_service.get_user(user_id)
            if user and user.accountability_partner_id:
                partner_id = user.accountability_partner_id
                firestore_service.update_user(
                    partner_id,
                    {
                        "accountability_partner_id": None,
                        "accountability_partner_name": None,
                    }
                )
                results["deleted"]["partner_link"] = True
                logger.info(f"🔗 Unlinked partner {partner_id} from {user_id}")
        except Exception as e:
            results["errors"].append(f"Partner unlink failed: {e}")
            logger.error(f"❌ Failed to unlink partner for {user_id}: {e}")

        # 2. Delete user profile
        try:
            firestore_service.db.collection("users").document(user_id).delete()
            results["deleted"]["user_profile"] = True
            logger.info(f"🗑️ User profile deleted: {user_id}")
        except Exception as e:
            results["errors"].append(f"User profile deletion failed: {e}")
            logger.error(f"❌ Failed to delete user profile {user_id}: {e}")

        # 3. Delete all check-ins
        try:
            checkins_ref = firestore_service.db.collection("daily_checkins").document(user_id).collection("checkins")
            checkins = checkins_ref.stream()
            deleted_count = 0
            for checkin in checkins:
                checkin.reference.delete()
                deleted_count += 1
            results["deleted"]["checkins"] = deleted_count
            logger.info(f"🗑️ Deleted {deleted_count} check-ins for {user_id}")
        except Exception as e:
            results["errors"].append(f"Check-in deletion failed: {e}")
            logger.error(f"❌ Failed to delete check-ins for {user_id}: {e}")

        # 4. Delete goals
        try:
            goals_query = firestore_service.db.collection("goals").where("user_id", "==", user_id)
            goals = goals_query.stream()
            deleted_count = 0
            for goal in goals:
                goal.reference.delete()
                deleted_count += 1
            results["deleted"]["goals"] = deleted_count
            logger.info(f"🗑️ Deleted {deleted_count} goals for {user_id}")
        except Exception as e:
            results["errors"].append(f"Goal deletion failed: {e}")
            logger.error(f"❌ Failed to delete goals for {user_id}: {e}")

        # 5. Delete challenges where user is participant
        try:
            challenges_query1 = firestore_service.db.collection("challenges").where("challenger_id", "==", user_id)
            challenges_query2 = firestore_service.db.collection("challenges").where("partner_id", "==", user_id)
            
            deleted_count = 0
            for challenge in challenges_query1.stream():
                challenge.reference.delete()
                deleted_count += 1
            for challenge in challenges_query2.stream():
                challenge.reference.delete()
                deleted_count += 1
                
            results["deleted"]["challenges"] = deleted_count
            logger.info(f"🗑️ Deleted {deleted_count} challenges for {user_id}")
        except Exception as e:
            results["errors"].append(f"Challenge deletion failed: {e}")
            logger.error(f"❌ Failed to delete challenges for {user_id}: {e}")

        # 6. Delete feedback
        try:
            feedback_query = firestore_service.db.collection("feedback").where("user_id", "==", user_id)
            feedbacks = feedback_query.stream()
            deleted_count = 0
            for fb in feedbacks:
                fb.reference.delete()
                deleted_count += 1
            results["deleted"]["feedback"] = deleted_count
            logger.info(f"🗑️ Deleted {deleted_count} feedback entries for {user_id}")
        except Exception as e:
            results["errors"].append(f"Feedback deletion failed: {e}")
            logger.error(f"❌ Failed to delete feedback for {user_id}: {e}")

        # Determine overall success
        if results["errors"]:
            results["success"] = False
            logger.warning(f"⚠️ Data deletion for {user_id} completed with errors: {results['errors']}")
        else:
            logger.info(f"✅ Complete data deletion successful for {user_id}")

        return results


# Singleton instance
data_deletion_service = DataDeletionService()
