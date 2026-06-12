"""
Feedback Service
================

NPS collection and feedback storage.

Theory: Feedback Loop
-----------------------
Systematic feedback collection enables data-driven prioritization.
NPS + qualitative feedback gives both quantitative trend and
qualitative context.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional, List

from src.models.schemas import User
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


class FeedbackService:
    """Manage user feedback collection and storage."""

    def store_feedback(
        self,
        user_id: str,
        feedback_type: str,
        rating: Optional[int] = None,
        message: str = "",
        context: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Store a feedback entry.

        Args:
            user_id: User who submitted feedback
            feedback_type: "nps" | "feature_request" | "bug" | "general"
            rating: 1-10 for NPS
            message: Qualitative feedback
            context: Additional context (e.g., {"command": "/checkin"})

        Returns:
            feedback_id
        """
        feedback_id = f"fb_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"

        entry = {
            "feedback_id": feedback_id,
            "user_id": user_id,
            "type": feedback_type,
            "rating": rating,
            "message": message,
            "context": context or {},
            "created_at": datetime.utcnow(),
        }

        firestore_service.db.collection("feedback").document(feedback_id).set(entry)
        logger.info(f"📝 Feedback stored: {feedback_id} from {user_id}")
        return feedback_id

    def get_recent_feedback(
        self,
        days: int = 30,
        feedback_type: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Get recent feedback entries.

        Args:
            days: Number of days to look back
            feedback_type: Filter by type (optional)

        Returns:
            List of feedback entries
        """
        from datetime import timedelta
        cutoff = datetime.utcnow() - timedelta(days=days)

        query = firestore_service.db.collection("feedback").where("created_at", ">=", cutoff)
        if feedback_type:
            query = query.where("type", "==", feedback_type)

        docs = query.order_by("created_at", direction="DESCENDING").limit(100).stream()
        return [doc.to_dict() for doc in docs]

    def get_last_feedback(
        self,
        user_id: str,
        feedback_type: Optional[str] = None,
    ) -> Optional[Dict[str, Any]]:
        """Get the most recent feedback from a user."""
        query = firestore_service.db.collection("feedback").where("user_id", "==", user_id)
        if feedback_type:
            query = query.where("type", "==", feedback_type)

        docs = query.order_by("created_at", direction="DESCENDING").limit(1).stream()
        for doc in docs:
            return doc.to_dict()
        return None

    def calculate_nps(self, days: int = 30) -> Dict[str, Any]:
        """
        Calculate NPS score from recent feedback.

        NPS = % Promoters (9-10) - % Detractors (0-6)
        Passives (7-8) are neutral.

        Returns:
            {"nps": float, "promoters": int, "passives": int, "detractors": int, "total": int}
        """
        feedbacks = self.get_recent_feedback(days=days, feedback_type="nps")

        promoters = sum(1 for f in feedbacks if f.get("rating", 0) >= 9)
        passives = sum(1 for f in feedbacks if 7 <= f.get("rating", 0) <= 8)
        detractors = sum(1 for f in feedbacks if f.get("rating", 0) <= 6)
        total = len(feedbacks)

        if total == 0:
            return {"nps": None, "promoters": 0, "passives": 0, "detractors": 0, "total": 0}

        nps = round(((promoters / total) - (detractors / total)) * 100, 1)

        return {
            "nps": nps,
            "promoters": promoters,
            "passives": passives,
            "detractors": detractors,
            "total": total,
        }

    def format_nps_summary(self, days: int = 30) -> str:
        """Format NPS summary for admin display."""
        nps_data = self.calculate_nps(days)
        if nps_data["total"] == 0:
            return "📊 No NPS feedback collected yet."

        nps = nps_data["nps"]
        emoji = "🟢" if nps >= 50 else "🟡" if nps >= 0 else "🔴"

        return (
            f"{emoji} <b>NPS Score: {nps}</b> (last {days} days)\n"
            f"  Promoters (9-10): {nps_data['promoters']}\n"
            f"  Passives (7-8): {nps_data['passives']}\n"
            f"  Detractors (0-6): {nps_data['detractors']}\n"
            f"  Total responses: {nps_data['total']}"
        )


# Singleton instance
feedback_service = FeedbackService()
