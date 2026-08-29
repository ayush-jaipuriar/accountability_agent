import logging
import json
import re
from datetime import datetime
from typing import List, Dict, Any, Optional

from src.models.schemas import User, DailyCheckIn, AIProfileMemory
from src.services.firestore_service import firestore_service
from src.services.llm_service import get_llm_service
from src.config import settings

logger = logging.getLogger(__name__)

class MemoryService:
    """
    Manages long-term AI-derived memory of user's behavior patterns, strengths,
    weaknesses, and habit correlations.
    """
    def __init__(self, project_id: str = None):
        self.project_id = project_id or settings.gcp_project_id
        self.llm = get_llm_service(self.project_id)
        self.firestore = firestore_service

    async def update_user_memory(self, user_id: str) -> Optional[AIProfileMemory]:
        """
        Fetch user check-ins (last 30 days) and update User's AIProfileMemory.
        
        Args:
            user_id: The user ID to update memory for
            
        Returns:
            The newly synthesized AIProfileMemory object or None if failed
        """
        try:
            user = self.firestore.get_user(user_id)
            if not user:
                logger.error(f"User {user_id} not found in Firestore.")
                return None

            # Get recent 30 check-ins (ordered by date)
            checkins = self.firestore.get_recent_checkins(user_id, days=30)
            if len(checkins) < 5:
                logger.info(f"User {user_id} has {len(checkins)} check-ins (minimum 5 required for synthesis). Skipping.")
                return None

            # Sort checkins by date ascending
            checkins_sorted = sorted(checkins, key=lambda c: c.date)

            # Build qualitative summary of recent check-ins
            history_lines = []
            for c in checkins_sorted:
                t1 = c.tier1_non_negotiables
                completed_habits = []
                if t1:
                    if t1.sleep: completed_habits.append("sleep")
                    if t1.training or t1.is_rest_day: completed_habits.append("training")
                    if t1.deep_work: completed_habits.append("deep work")
                    if t1.skill_building: completed_habits.append("skill building")
                    if t1.zero_porn: completed_habits.append("zero porn")
                    if t1.boundaries: completed_habits.append("boundaries")
                
                habits_str = ", ".join(completed_habits) if completed_habits else "None"
                
                resp = c.responses
                history_lines.append(
                    f"Date: {c.date}\n"
                    f"  Habit Compliance: {c.compliance_score:.0f}%\n"
                    f"  Completed Habits: {habits_str}\n"
                    f"  Energy: {resp.energy_rating or 'N/A'}/10, Mood: {resp.mood_rating or 'N/A'}/10\n"
                    f"  Self-Rating: {resp.rating or 'N/A'}/10\n"
                    f"  Challenges: \"{resp.challenges or 'None'}\"\n"
                    f"  Rating Reason: \"{resp.rating_reason or 'None'}\"\n"
                    f"  Tomorrow's Priority: \"{resp.tomorrow_priority or 'None'}\"\n"
                    f"  Tomorrow's Obstacle: \"{resp.tomorrow_obstacle or 'None'}\"\n"
                )

            history_context = "\n".join(history_lines)

            # Format current memory
            curr_mem = user.ai_profile_memory
            current_memory_str = (
                f"Summary: {curr_mem.summary}\n"
                f"Strengths: {curr_mem.strengths}\n"
                f"Weaknesses: {curr_mem.weaknesses}\n"
                f"Recurring Obstacles: {curr_mem.recurring_obstacles}\n"
                f"Correlations: {curr_mem.correlations}\n"
                f"Coaching Notes: {curr_mem.coaching_notes}\n"
                f"Say-Do Ratio: {curr_mem.say_do_ratio:.1f}%\n"
            )

            prompt = f"""You are a professional behavioral psychologist and habit coach. Your job is to analyze a user's daily check-in logs over the past 30 days and update their long-term behavior profile memory.

CURRENT BEHAVIOR PROFILE MEMORY:
--------------------------------
{current_memory_str}

LAST 30 DAYS CHECK-IN DATA:
---------------------------
{history_context}

USER CONTEXT:
-------------
- Career Mode: {user.career_mode}
- Constitution Mode: {user.constitution_mode}

TASK:
Analyze the new check-in logs and synthesize an updated BEHAVIOR PROFILE MEMORY. Be highly analytical, looking for:
1. **Strengths**: What is the user consistently executing well? (e.g. morning routines, specific habits)
2. **Weaknesses**: Where are the patterns of failure? (e.g. weekend slumps, late night drop-offs)
3. **Recurring Obstacles**: What trigger or context is mentioned repeatedly as a blocker?
4. **Correlations**: What quantitative or qualitative connections exist? (e.g. sleep hours vs deep work, training vs mood)
5. **Say-Do Ratio**: Analyze how often they successfully executed their stated "Priority" from the day before (e.g. if they set "Leetcode" and the next day reported doing Leetcode, that is a success. If they got distracted, it's a miss). Estimate this ratio as a percentage (0-100).
6. **Coaching Notes**: Synthesize advice for the AI coaching engine on how to interact with this user. Should the coach be tough, supportive, focus on micro-habits, or warn them about weekends?
7. **Summary**: A single paragraph capturing the user's current behavioral journey, momentum, and progression.

Output ONLY a valid JSON object matching the following schema. Do NOT include any markdown code blocks, backticks, or extra text. All fields must be populated:

{{
  "summary": "...",
  "strengths": ["...", "..."],
  "weaknesses": ["...", "..."],
  "recurring_obstacles": [
    {{"obstacle": "...", "frequency": "high/medium/low", "last_seen": "YYYY-MM-DD"}},
    {{"obstacle": "...", "frequency": "high/medium/low", "last_seen": "YYYY-MM-DD"}}
  ],
  "correlations": ["...", "..."],
  "coaching_notes": "...",
  "say_do_ratio": 75.0
}}
"""
            logger.info(f"Invoking Gemini to synthesize long-term profile memory for user {user_id}")
            response = await self.llm.generate_text(prompt, max_output_tokens=1500, temperature=0.2)
            
            # Robust JSON extraction
            json_match = re.search(r"\{.*\}", response, re.DOTALL)
            if json_match:
                cleaned_response = json_match.group(0)
            else:
                cleaned_response = response.strip()
                if cleaned_response.startswith("```"):
                    cleaned_response = re.sub(r"^```(?:json)?\n", "", cleaned_response)
                    cleaned_response = re.sub(r"\n```$", "", cleaned_response)
                    cleaned_response = cleaned_response.strip()

            parsed = json.loads(cleaned_response)
            
            # Construct updated AIProfileMemory object
            raw_sdr = parsed.get("say_do_ratio", curr_mem.say_do_ratio)
            sdr_val = curr_mem.say_do_ratio
            if raw_sdr is not None:
                try:
                    match = re.search(r"[\d.]+", str(raw_sdr))
                    if match:
                        sdr_val = float(match.group(0))
                    else:
                        sdr_val = float(raw_sdr)
                except (ValueError, TypeError):
                    sdr_val = curr_mem.say_do_ratio

            updated_memory = AIProfileMemory(
                summary=parsed.get("summary", curr_mem.summary),
                strengths=parsed.get("strengths", curr_mem.strengths),
                weaknesses=parsed.get("weaknesses", curr_mem.weaknesses),
                recurring_obstacles=parsed.get("recurring_obstacles", curr_mem.recurring_obstacles),
                correlations=parsed.get("correlations", curr_mem.correlations),
                coaching_notes=parsed.get("coaching_notes", curr_mem.coaching_notes),
                say_do_ratio=sdr_val,
                last_updated=datetime.utcnow()
            )

            # Persist to Firestore
            success = self.firestore.update_user(user_id, {"ai_profile_memory": updated_memory.model_dump()})
            if success:
                logger.info(f"✅ Successfully updated long-term memory for user {user_id}")
                return updated_memory
            else:
                logger.error(f"❌ Failed to persist updated memory for user {user_id} in Firestore")
                return None

        except Exception as e:
            logger.error(f"❌ Error synthesizing memory for user {user_id}: {e}", exc_info=True)
            return None

memory_service = MemoryService()
