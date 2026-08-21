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

        # 1. Unlink partner (both forward and reverse links)
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
            
            # Reverse partner unlink: any other user pointing to this user
            reverse_partners = firestore_service.db.collection("users").where("accountability_partner_id", "==", user_id).stream()
            for rp in reverse_partners:
                rp.reference.update({
                    "accountability_partner_id": None,
                    "accountability_partner_name": None,
                })
                logger.info(f"🔗 Unlinked reverse partner {rp.id} pointing to {user_id}")
        except Exception as e:
            results["errors"].append(f"Partner unlink failed: {e}")
            logger.error(f"❌ Failed to unlink partner for {user_id}: {e}")

        # Helper to delete a subcollection and its parent document
        def _delete_subcollection_and_parent(collection_name: str, subcollection_name: str) -> int:
            parent_ref = firestore_service.db.collection(collection_name).document(user_id)
            docs = parent_ref.collection(subcollection_name).stream()
            count = 0
            for doc in docs:
                doc.reference.delete()
                count += 1
            parent_ref.delete()
            return count

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
            deleted_count = _delete_subcollection_and_parent("daily_checkins", "checkins")
            results["deleted"]["checkins"] = deleted_count
            logger.info(f"🗑️ Deleted {deleted_count} check-ins for {user_id}")
        except Exception as e:
            results["errors"].append(f"Check-in deletion failed: {e}")
            logger.error(f"❌ Failed to delete check-ins for {user_id}: {e}")

        # 4. Delete daily tasks
        try:
            deleted_count = _delete_subcollection_and_parent("daily_tasks", "tasks")
            results["deleted"]["daily_tasks"] = deleted_count
            logger.info(f"🗑️ Deleted {deleted_count} daily tasks for {user_id}")
        except Exception as e:
            results["errors"].append(f"Daily tasks deletion failed: {e}")
            logger.error(f"❌ Failed to delete daily tasks for {user_id}: {e}")

        # 5. Delete emotional interactions
        try:
            deleted_count = _delete_subcollection_and_parent("emotional_interactions", "interactions")
            results["deleted"]["emotional_interactions"] = deleted_count
            logger.info(f"🗑️ Deleted {deleted_count} emotional interactions for {user_id}")
        except Exception as e:
            results["errors"].append(f"Emotional interactions deletion failed: {e}")
            logger.error(f"❌ Failed to delete emotional interactions for {user_id}: {e}")

        # 6. Delete interventions
        try:
            deleted_count = _delete_subcollection_and_parent("interventions", "interventions")
            results["deleted"]["interventions"] = deleted_count
            logger.info(f"🗑️ Deleted {deleted_count} interventions for {user_id}")
        except Exception as e:
            results["errors"].append(f"Interventions deletion failed: {e}")
            logger.error(f"❌ Failed to delete interventions for {user_id}: {e}")

        # 7. Delete reminder status
        try:
            deleted_count = _delete_subcollection_and_parent("reminder_status", "dates")
            # Also check direct docs under reminder_status/{user_id}
            firestore_service.db.collection("reminder_status").document(user_id).delete()
            results["deleted"]["reminder_status"] = deleted_count
            logger.info(f"🗑️ Deleted reminder status for {user_id}")
        except Exception as e:
            results["errors"].append(f"Reminder status deletion failed: {e}")
            logger.error(f"❌ Failed to delete reminder status for {user_id}: {e}")

        # 8. Delete partner checkin notifications
        try:
            deleted_count = _delete_subcollection_and_parent("partner_checkin_notifications", "dates")
            firestore_service.db.collection("partner_checkin_notifications").document(user_id).delete()
            results["deleted"]["partner_checkin_notifications"] = deleted_count
            logger.info(f"🗑️ Deleted partner notifications for {user_id}")
        except Exception as e:
            results["errors"].append(f"Partner notifications deletion failed: {e}")
            logger.error(f"❌ Failed to delete partner notifications for {user_id}: {e}")

        # 9. Delete goals
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

        # 10. Delete challenges where user is participant
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

        # 11. Delete feedback
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
