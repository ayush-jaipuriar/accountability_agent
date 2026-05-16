"""
Challenge Service
=================

Manages partner challenges: creation, acceptance, progress tracking,
and completion declaration.

Theory: Shared Accountability
-------------------------------
A challenge transforms the 1:1 partner notification into a shared
experience. Both partners commit to the same target and see each
other's progress daily, creating mutual accountability.
"""

import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict

from src.models.schemas import PartnerChallenge, DailyCheckIn, Tier1NonNegotiables
from src.services.firestore_service import firestore_service

logger = logging.getLogger(__name__)


class ChallengeService:
    """Manage partner challenges."""

    def __init__(self):
        self.firestore = firestore_service

    def create_challenge(
        self,
        challenger_id: str,
        partner_id: str,
        challenge_type: str,
        title: str,
        description: str,
        start_date: str,
        end_date: str,
    ) -> PartnerChallenge:
        """Create a new partner challenge."""
        challenge = PartnerChallenge(
            challenger_id=challenger_id,
            partner_id=partner_id,
            challenge_type=challenge_type,
            title=title,
            description=description,
            start_date=start_date,
            end_date=end_date,
        )

        self.firestore.db.collection("challenges").document(challenge.challenge_id).set(
            challenge.to_firestore()
        )
        logger.info(f"🏆 Challenge created: {challenge.challenge_id} by {challenger_id}")
        return challenge

    def get_challenge(self, challenge_id: str) -> Optional[PartnerChallenge]:
        """Fetch a challenge by ID."""
        try:
            doc = self.firestore.db.collection("challenges").document(challenge_id).get()
            if doc.exists:
                return PartnerChallenge.from_firestore(doc.to_dict())
            return None
        except Exception as e:
            logger.error(f"❌ Failed to fetch challenge {challenge_id}: {e}")
            return None

    def get_user_challenges(self, user_id: str, status: Optional[str] = None) -> List[PartnerChallenge]:
        """Fetch challenges where user is a participant."""
        try:
            # Query both challenger_id and partner_id
            query1 = self.firestore.db.collection("challenges").where("challenger_id", "==", user_id)
            query2 = self.firestore.db.collection("challenges").where("partner_id", "==", user_id)

            docs1 = list(query1.stream())
            docs2 = list(query2.stream())

            seen = set()
            challenges = []
            for doc in docs1 + docs2:
                if doc.id not in seen:
                    seen.add(doc.id)
                    challenges.append(PartnerChallenge.from_firestore(doc.to_dict()))

            if status:
                challenges = [c for c in challenges if c.status == status]

            return challenges
        except Exception as e:
            logger.error(f"❌ Failed to fetch challenges for {user_id}: {e}")
            return []

    def accept_challenge(self, challenge_id: str) -> bool:
        """Partner accepts the challenge."""
        try:
            self.firestore.db.collection("challenges").document(challenge_id).update({
                "status": "active"
            })
            logger.info(f"🏆 Challenge {challenge_id} accepted")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to accept challenge {challenge_id}: {e}")
            return False

    def decline_challenge(self, challenge_id: str) -> bool:
        """Partner declines the challenge."""
        try:
            self.firestore.db.collection("challenges").document(challenge_id).update({
                "status": "cancelled"
            })
            logger.info(f"🏆 Challenge {challenge_id} declined")
            return True
        except Exception as e:
            logger.error(f"❌ Failed to decline challenge {challenge_id}: {e}")
            return False

    def update_progress_from_checkin(self, checkin: DailyCheckIn) -> List[PartnerChallenge]:
        """
        Update challenge progress based on a check-in.

        Called after every check-in. Returns list of updated challenges.
        """
        user_id = checkin.user_id
        date = checkin.date
        tier1 = checkin.tier1_non_negotiables

        active_challenges = self.get_user_challenges(user_id, status="active")
        updated = []

        for challenge in active_challenges:
            # Skip if date is before start or after end
            if date < challenge.start_date or date > challenge.end_date:
                continue

            met = self._evaluate_challenge_for_date(challenge, tier1)
            if met is not None:
                # Initialize progress dict if needed
                if user_id not in challenge.progress:
                    challenge.progress[user_id] = []

                challenge.progress[user_id].append({
                    "date": date,
                    "met": met,
                })

                # Save
                self.firestore.db.collection("challenges").document(
                    challenge.challenge_id
                ).update({"progress": challenge.progress})

                updated.append(challenge)

        return updated

    def _evaluate_challenge_for_date(self, challenge: PartnerChallenge, tier1: Tier1NonNegotiables) -> Optional[bool]:
        """Evaluate whether a challenge was met for a single day."""
        ctype = challenge.challenge_type

        if ctype == "sleep_7_days":
            hours = getattr(tier1, 'sleep_hours', None)
            if hours is not None:
                return hours >= 7.0
            return tier1.sleep

        elif ctype == "training_5_days":
            intensity = getattr(tier1, 'training_intensity', None)
            if intensity is not None:
                return intensity.lower() in ('light', 'moderate', 'intense')
            return tier1.training

        elif ctype == "deep_work_7_days":
            hours = getattr(tier1, 'deep_work_hours', None)
            if hours is not None:
                return hours >= 2.0
            return tier1.deep_work

        elif ctype == "custom":
            # Custom challenges require manual evaluation
            return None

        return None

    def check_completion(self, challenge: PartnerChallenge) -> Optional[str]:
        """
        Check if a challenge has completed (reached end_date).

        Returns:
            winner_id or "tie" or None
        """
        from src.utils.timezone_utils import get_current_date
        today = get_current_date()

        if today < challenge.end_date:
            return None

        # Count met days per participant
        challenger_days = sum(
            1 for p in challenge.progress.get(challenge.challenger_id, [])
            if p.get("met")
        )
        partner_days = sum(
            1 for p in challenge.progress.get(challenge.partner_id, [])
            if p.get("met")
        )

        total_days = (datetime.strptime(challenge.end_date, "%Y-%m-%d") - 
                     datetime.strptime(challenge.start_date, "%Y-%m-%d")).days + 1

        if challenger_days > partner_days:
            winner = challenge.challenger_id
        elif partner_days > challenger_days:
            winner = challenge.partner_id
        else:
            winner = "tie"

        # Update challenge
        self.firestore.db.collection("challenges").document(challenge.challenge_id).update({
            "status": "completed",
            "winner_id": winner if winner != "tie" else None,
            "completed_at": datetime.utcnow(),
        })

        logger.info(f"🏆 Challenge {challenge.challenge_id} completed. Winner: {winner}")
        return winner

    def format_challenge_status(self, challenge: PartnerChallenge, user_id: str) -> str:
        """Format challenge status for display."""
        challenger_days = sum(
            1 for p in challenge.progress.get(challenge.challenger_id, [])
            if p.get("met")
        )
        partner_days = sum(
            1 for p in challenge.progress.get(challenge.partner_id, [])
            if p.get("met")
        )

        total_days = (datetime.strptime(challenge.end_date, "%Y-%m-%d") -
                     datetime.strptime(challenge.start_date, "%Y-%m-%d")).days + 1
        days_left = (datetime.strptime(challenge.end_date, "%Y-%m-%d") - datetime.utcnow()).days + 1

        lines = [
            f"🏆 <b>{challenge.title}</b>",
            f"   <i>{challenge.description}</i>",
            f"",
            f"   📊 Standings:",
            f"   • You: {challenger_days if challenge.challenger_id == user_id else partner_days}/{total_days} days",
            f"   • Partner: {partner_days if challenge.challenger_id == user_id else challenger_days}/{total_days} days",
            f"   ⏳ Days left: {max(0, days_left)}",
        ]

        if challenge.status == "completed":
            if challenge.winner_id == user_id:
                lines.append(f"   🎉 You won!")
            elif challenge.winner_id:
                lines.append(f"   Partner won!")
            else:
                lines.append(f"   🤝 It's a tie!")

        return "\n".join(lines)


# Singleton instance
challenge_service = ChallengeService()
