"""
CheckIn Agent - AI-Powered Personalized Feedback

This agent generates personalized check-in feedback using Gemini 2.5 Flash.

What Changed from Phase 1:
---------------------------
**Phase 1 (Hardcoded):**
```
if compliance_score == 100:
    return "💯 Perfect day! All Tier 1 non-negotiables completed."
elif compliance_score >= 80:
    return "✅ Strong day! You're maintaining solid consistency."
```

**Phase 2 (AI-Generated):**
```
# Gemini analyzes:
# - Today's compliance score
# - Current streak (47 days)
# - Recent 7-day trend (improving/declining/consistent)
# - Constitution principles violated/followed
# - User's self-rating and reasons

# Generates:
"Excellent work! 100% compliance today - you're locked in. 🔥

Your 47-day streak is now in the top 1% territory. The consistency 
you're building here is exactly what Principle 3 (Systems Over Willpower) 
is about - you've made excellence automatic.

Sleep (8hrs), training, deep work (3hrs), zero porn, boundaries - all green. 
This is what Physical Sovereignty looks like in practice.

Tomorrow's focus: Protect that morning deep work slot. You're building 
momentum - don't let anything interrupt it.

Keep going. 💪"
```

Key Concepts:
-------------
1. **Context-Aware Feedback**:
   - References actual streak numbers
   - Mentions specific items completed/missed
   - Identifies patterns over last 7 days

2. **Constitution Integration**:
   - Quotes relevant principles
   - Connects daily actions to long-term goals
   - Reinforces identity ("Physical Sovereignty")

3. **Forward-Looking Guidance**:
   - Specific action for tomorrow
   - Based on user's stated priorities
   - Addresses potential obstacles

4. **Tone Calibration**:
   - Direct, not fluffy
   - Motivating but realistic
   - Like a coach who knows the athlete

Token Budget:
-------------
- Input: ~600 tokens (context + prompt)
- Output: ~200 tokens (feedback)
- Total: ~800 tokens per check-in
- Cost: ~$0.002 per check-in ($0.06/month)
"""

from src.agents.state import ConstitutionState
from src.services.llm_service import get_llm_service
from src.services.firestore_service import firestore_service
from src.services.constitution_service import constitution_service
from src.config import settings
from src.models.schemas import Tier1NonNegotiables
import logging
from datetime import datetime, timedelta
from typing import Optional, List, Dict

logger = logging.getLogger(__name__)


class CheckInAgent:
    """
    AI-powered check-in feedback generator
    
    Replaces hardcoded Phase 1 feedback with personalized Gemini-generated insights.
    """
    
    def __init__(self, project_id: str):
        """
        Initialize CheckIn Agent
        
        Args:
            project_id: GCP project ID for LLM service
        """
        self.llm = get_llm_service(
            project_id=project_id,
            location=settings.vertex_ai_location,
            model_name=settings.gemini_model
        )
        logger.info("CheckIn Agent initialized")
    
    async def generate_feedback(
        self,
        user_id: str,
        compliance_score: int,
        tier1: Tier1NonNegotiables,
        current_streak: int,
        longest_streak: int,
        self_rating: int,
        rating_reason: str,
        tomorrow_priority: str,
        tomorrow_obstacle: str
    ) -> str:
        """
        Generate personalized check-in feedback using AI
        
        Args:
            user_id: User ID
            compliance_score: Today's compliance score (0-100)
            tier1: Tier 1 non-negotiables object
            current_streak: Current streak count
            longest_streak: Longest streak ever
            self_rating: User's self-rating (1-10)
            rating_reason: Why they gave that rating
            tomorrow_priority: What they plan to focus on tomorrow
            tomorrow_obstacle: What might get in the way
            
        Returns:
            Personalized feedback message (150-250 words)
            
        Theory - Why This Works:
        ------------------------
        1. **Contextualization**: LLM has all the data to make specific observations
        2. **Pattern Recognition**: Can identify trends from recent check-ins
        3. **Personalization**: References actual numbers and user's own words
        4. **Consistency**: Same prompt structure ensures reliable quality
        5. **Scalability**: No need to write rules for every scenario
        """
        try:
            # Get recent check-ins for pattern analysis
            recent_checkins = self._get_recent_checkins(user_id, days=7)
            
            # Analyze trend
            trend = self._analyze_trend(recent_checkins, compliance_score)
            
            # Get relevant constitution principles
            constitution_excerpt = self._get_relevant_principles(tier1)
            
            # Build feedback prompt
            prompt = self._build_feedback_prompt(
                compliance_score=compliance_score,
                tier1=tier1,
                current_streak=current_streak,
                longest_streak=longest_streak,
                trend=trend,
                self_rating=self_rating,
                rating_reason=rating_reason,
                tomorrow_priority=tomorrow_priority,
                tomorrow_obstacle=tomorrow_obstacle,
                constitution_excerpt=constitution_excerpt,
                recent_checkins=recent_checkins
            )
            
            # Generate feedback with Gemini
            logger.info(f"Generating AI feedback for user {user_id} (score: {compliance_score}%, streak: {current_streak})")
            
            feedback = await self.llm.generate_text(
                prompt=prompt,
                max_output_tokens=3072,  # Increased 1.5x from 2048 (gemini-2.5 with thinking disabled)
                temperature=0.7  # Moderate creativity (not too robotic, not too random)
            )
            
            logger.info(f"✅ Generated {len(feedback)} char feedback for user {user_id}")
            
            return feedback.strip()
            
        except Exception as e:
            logger.error(f"❌ AI feedback generation failed: {e}", exc_info=True)
            # Fallback to Phase 1 hardcoded feedback
            return self._fallback_feedback(compliance_score, current_streak)
    
    def _get_recent_checkins(self, user_id: str, days: int = 7) -> List[Dict]:
        """
        Get recent check-ins for trend analysis
        
        Args:
            user_id: User ID
            days: Number of recent days to fetch
            
        Returns:
            List of recent check-ins with key metrics
        """
        try:
            # Get last N check-ins
            checkins = firestore_service.get_recent_checkins(user_id, days=days)
            
            # Extract key metrics
            recent_data = []
            for checkin in checkins:
                recent_data.append({
                    'date': checkin.date,
                    'compliance_score': checkin.compliance_score,
                    'rating': checkin.responses.rating if hasattr(checkin, 'responses') else None
                })
            
            return recent_data
            
        except Exception as e:
            logger.warning(f"Could not fetch recent check-ins: {e}")
            return []
    
    def _analyze_trend(self, recent_checkins: List[Dict], today_score: int) -> str:
        """
        Analyze trend from recent check-ins
        
        Args:
            recent_checkins: List of recent check-ins
            today_score: Today's compliance score
            
        Returns:
            Trend description: "improving", "declining", "consistent high", "consistent low", "new"
        """
        if len(recent_checkins) < 3:
            return "new check-in routine"
        
        # Get last 3 scores (before today)
        recent_scores = [c['compliance_score'] for c in recent_checkins[-3:]]
        
        # Check for consistent high performance
        if all(s >= 80 for s in recent_scores) and today_score >= 80:
            return "consistent high compliance (3+ days >80%)"
        
        # Check for consistent low performance
        if all(s < 70 for s in recent_scores) and today_score < 70:
            return "struggling (3+ days <70%)"
        
        # Check for improvement trend
        if len(recent_scores) >= 2:
            avg_recent = sum(recent_scores) / len(recent_scores)
            if today_score > avg_recent + 10:
                return "improving (today higher than recent average)"
            elif today_score < avg_recent - 10:
                return "declining (today lower than recent average)"
        
        return "stable performance"
    
    def _get_relevant_principles(self, tier1: Tier1NonNegotiables) -> str:
        """
        Get relevant constitution principles based on what was completed/missed
        
        Args:
            tier1: Tier 1 non-negotiables
            
        Returns:
            Relevant excerpt from constitution
        """
        # Get abbreviated constitution summary (token-efficient)
        constitution_excerpt = constitution_service.get_constitution_summary(max_chars=800)
        
        return constitution_excerpt
    
    def _build_feedback_prompt(
        self,
        compliance_score: int,
        tier1: Tier1NonNegotiables,
        current_streak: int,
        longest_streak: int,
        trend: str,
        self_rating: int,
        rating_reason: str,
        tomorrow_priority: str,
        tomorrow_obstacle: str,
        constitution_excerpt: str,
        recent_checkins: List[Dict]
    ) -> str:
        """
        Build the feedback generation prompt for Gemini
        
        This is where the magic happens - the prompt structure determines
        the quality and consistency of the AI feedback.
        
        Prompt Engineering Principles Used:
        -----------------------------------
        1. **Clear Role**: "You are a constitution accountability coach"
        2. **Structured Data**: Organized input (today's data, context, trends)
        3. **Output Format**: Specific word count and sections
        4. **Tone Specification**: Direct, motivating, no fluff
        5. **Examples**: (Could add few-shot examples for better quality)
        6. **Constraints**: What to avoid (generic praise, fluff, vague advice)
        """
        # Summarize tier1 status
        tier1_items = []
        if tier1.sleep:
            tier1_items.append("✅ Sleep (7+ hours)")
        else:
            tier1_items.append("❌ Sleep (<7 hours)")
        
        if tier1.training:
            tier1_items.append("✅ Training")
        else:
            tier1_items.append("❌ Training (missed)")
        
        if tier1.deep_work:
            tier1_items.append("✅ Deep Work (2+ hours)")
        else:
            tier1_items.append("❌ Deep Work (<2 hours)")
        
        if tier1.zero_porn:
            tier1_items.append("✅ Zero Porn")
        else:
            tier1_items.append("❌ Porn violation")
        
        if tier1.boundaries:
            tier1_items.append("✅ Boundaries")
        else:
            tier1_items.append("❌ Boundaries (violated)")
        
        tier1_summary = "\n".join(tier1_items)
        
        # Format recent history
        if recent_checkins:
            recent_summary = f"Last 7 days: {len(recent_checkins)} check-ins"
            recent_scores = [str(c['compliance_score']) for c in recent_checkins[-7:]]
            recent_summary += f"\nRecent scores: {', '.join(recent_scores)}%"
        else:
            recent_summary = "First check-in or limited history"
        
        # Identify streak milestone
        streak_milestone = ""
        if current_streak >= 100:
            streak_milestone = "🏆 LEGENDARY (100+ days)"
        elif current_streak >= 60:
            streak_milestone = "🔥 Elite (60+ days)"
        elif current_streak >= 30:
            streak_milestone = "💪 Strong (30+ days)"
        elif current_streak >= 14:
            streak_milestone = "✨ Building momentum (2+ weeks)"
        elif current_streak >= 7:
            streak_milestone = "🎯 First week done!"
        elif current_streak >= 3:
            streak_milestone = "🌱 Starting to build habit"
        else:
            streak_milestone = "🚀 Just getting started"
        
        prompt = f"""You are a direct, no-nonsense constitution accountability coach. Generate personalized check-in feedback for this user.

TODAY'S CHECK-IN:
-----------------
Compliance Score: {compliance_score}%
Tier 1 Non-Negotiables:
{tier1_summary}

Self-Rating: {self_rating}/10
Reason: "{rating_reason}"

Tomorrow's Priority: "{tomorrow_priority}"
Tomorrow's Obstacle: "{tomorrow_obstacle}"

USER CONTEXT:
-------------
Current Streak: {current_streak} days {streak_milestone}
Longest Streak: {longest_streak} days
Recent Trend: {trend}

{recent_summary}

CONSTITUTION PRINCIPLES (reference these):
------------------------------------------
{constitution_excerpt}

GENERATE FEEDBACK (150-250 words):
----------------------------------
Write feedback that:

1. **ACKNOWLEDGE TODAY** (1-2 sentences):
   - Reference exact compliance score
   - If perfect (100%): Strong praise
   - If good (80-99%): Acknowledge + note what was missed
   - If struggling (<80%): Direct but supportive

2. **STREAK CONTEXT** (1-2 sentences):
   - Mention current streak number
   - If milestone (7, 14, 30, 60, 100 days): Celebrate it
   - If near personal best: Motivate to break it
   - Connect streak to identity/systems

3. **PATTERN OBSERVATION** (1 sentence):
   - Note the trend (improving/declining/consistent)
   - Reference specific numbers if relevant

4. **CONSTITUTION CONNECTION** (1-2 sentences):
   - Reference a relevant principle from constitution
   - Connect today's actions to that principle
   - Use principle names (e.g., "Physical Sovereignty", "Create Don't Consume")

5. **FORWARD FOCUS** (1-2 sentences):
   - ONE specific action for tomorrow
   - Reference their stated priority or obstacle
   - Make it actionable and concrete

TONE REQUIREMENTS:
- Direct and clear (no corporate-speak or generic praise)
- Motivating but realistic
- Like a coach who knows the athlete well
- Use emojis sparingly (🔥, ✅, 💪, 🎯 only)
- Focus on BEHAVIOR, not feelings
- NO: "Great job!", "Keep it up!", "You're amazing!"
- YES: Specific observations, data, actionable guidance

WORD COUNT: 150-250 words max
FORMAT: Paragraphs, not bullet points

Feedback:"""

        return prompt
    
    def _fallback_feedback(self, compliance_score: int, current_streak: int) -> str:
        """
        Fallback to Phase 1 hardcoded feedback if AI generation fails
        
        Args:
            compliance_score: Compliance score
            current_streak: Current streak
            
        Returns:
            Basic hardcoded feedback message
        """
        if compliance_score == 100:
            message = (
                "💯 Perfect day! All Tier 1 non-negotiables completed.\n"
                "This is what constitution mastery looks like."
            )
        elif compliance_score >= 80:
            message = (
                "✅ Strong day! You're maintaining solid consistency.\n"
                "Keep this momentum going."
            )
        elif compliance_score >= 60:
            message = (
                "⚠️ Room for improvement. Which Tier 1 items can you prioritize tomorrow?"
            )
        else:
            message = (
                "🚨 Below standards today. Let's refocus.\n"
                "Your constitution is your foundation - protect it."
            )
        
        message += f"\n\n🔥 Current streak: {current_streak} days"
        message += "\n\n(Note: AI feedback temporarily unavailable - using basic feedback)"
        
        return message


# Global instance
_checkin_agent_instance: Optional[CheckInAgent] = None


def get_checkin_agent(project_id: str) -> CheckInAgent:
    """
    Get or create CheckIn agent instance (singleton)
    
    Args:
        project_id: GCP project ID
        
    Returns:
        CheckInAgent instance
    """
    global _checkin_agent_instance
    
    if _checkin_agent_instance is None:
        logger.info("Creating new CheckInAgent instance (singleton)")
        _checkin_agent_instance = CheckInAgent(project_id)
    else:
        logger.debug("Returning existing CheckInAgent instance")
    
    return _checkin_agent_instance


def reset_checkin_agent():
    """Reset CheckIn agent instance (for testing)"""
    global _checkin_agent_instance
    _checkin_agent_instance = None
    logger.info("CheckIn agent instance reset")
