"""
CheckIn Agent - AI-Powered Personalized Feedback

This agent generates personalized check-in feedback using Gemini 2.5 Flash.

What Changed from Phase 1:
---------------------------
<b>Phase 1 (Hardcoded):</b>
```
if compliance_score == 100:
    return "💯 Perfect day! All Tier 1 non-negotiables completed."
elif compliance_score >= 80:
    return "✅ Strong day! You're maintaining solid consistency."
```

<b>Phase 2 (AI-Generated):</b>
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
1. <b>Context-Aware Feedback</b>:
   - References actual streak numbers
   - Mentions specific items completed/missed
   - Identifies patterns over last 7 days

2. <b>Constitution Integration</b>:
   - Quotes relevant principles
   - Connects daily actions to long-term goals
   - Reinforces identity ("Physical Sovereignty")

3. <b>Forward-Looking Guidance</b>:
   - Specific action for tomorrow
   - Based on user's stated priorities
   - Addresses potential obstacles

4. <b>Tone Calibration</b>:
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
import re
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
        tomorrow_obstacle: str,
        yesterday_checkin: dict = None,
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
        1. <b>Contextualization</b>: LLM has all the data to make specific observations
        2. <b>Pattern Recognition</b>: Can identify trends from recent check-ins
        3. <b>Personalization</b>: References actual numbers and user's own words
        4. <b>Consistency</b>: Same prompt structure ensures reliable quality
        5. <b>Scalability</b>: No need to write rules for every scenario
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
                recent_checkins=recent_checkins,
                yesterday_checkin=yesterday_checkin,
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
    
    async def generate_abbreviated_feedback(
        self,
        user_id: str,
        tier1: Tier1NonNegotiables,
        compliance_score: int,
        current_streak: int
    ) -> str:
        """
        Generate abbreviated feedback for quick check-ins (Phase 3E).
        
        <b>Goal:</b> 1-2 sentences that:
        1. Acknowledge 1-2 wins from Tier 1
        2. Suggest 1 focus area for tomorrow
        
        <b>Why Abbreviated:</b>
        - Quick check-ins skip Q2-Q4 (no challenges, priorities, obstacles)
        - User wants fast completion (~2 minutes total)
        - Limited context = limited analysis
        - Still provide value: recognize wins + actionable advice
        
        <b>Format:</b>
        "Good job on X and Y! Focus on Z tomorrow."
        OR
        "Strong performance on X! Don't skip Y tomorrow."
        
        Args:
            user_id: User ID
            tier1: Tier 1 non-negotiables object
            compliance_score: Today's compliance score (0-100)
            current_streak: Current streak count
            
        Returns:
            Abbreviated feedback (1-2 sentences, <100 words)
        """
        try:
            # Build abbreviated prompt
            prompt = f"""Generate brief (1-2 sentences) check-in feedback.

<b>Tier 1 Results:</b>
- Sleep: {'✅' if tier1.sleep else '❌'} (7+ hours)
- Training: {'✅' if tier1.training else '❌'} (workout or rest)
- Deep Work: {'✅' if tier1.deep_work else '❌'} (2+ hours)
- Skill Building: {'✅' if tier1.skill_building else '❌'} (2+ hours career learning)
- Zero Porn: {'✅' if tier1.zero_porn else '❌'}
- Boundaries: {'✅' if tier1.boundaries else '❌'} (no toxic interactions)

<b>Compliance:</b> {compliance_score}%
<b>Streak:</b> {current_streak} days

<b>Task:</b> Generate 1-2 sentences:
1. Acknowledge 1-2 wins (things with ✅)
2. Suggest 1 focus area for tomorrow (prioritize ❌ items)

<b>Requirements:</b>
- Maximum 100 words
- Specific (mention actual areas like "sleep", "deep work")
- Encouraging but direct
- No generic platitudes

<b>Examples:</b>
- "Great work on sleep and training! Focus on skill building tomorrow."
- "Strong day with perfect compliance! Keep this momentum going."
- "Good boundaries maintained! Prioritize deep work and skill building tomorrow."
- "Sleep on track! Don't skip training tomorrow - consistency matters."

<b>Your Response (1-2 sentences only):</b>"""

            # Generate abbreviated feedback with Gemini
            logger.info(f"⚡ Generating abbreviated feedback for quick check-in (user {user_id})")
            
            feedback = await self.llm.generate_text(
                prompt=prompt,
                max_output_tokens=150,  # Very short output
                temperature=0.5  # Lower creativity for consistency
            )
            
            logger.info(f"✅ Generated abbreviated feedback ({len(feedback)} chars) for user {user_id}")
            
            return feedback.strip()
            
        except Exception as e:
            logger.error(f"❌ Abbreviated AI feedback failed: {e}", exc_info=True)
            
            # Fallback abbreviated feedback
            wins = []
            if tier1.sleep:
                wins.append("sleep")
            if tier1.training:
                wins.append("training")
            if tier1.boundaries:
                wins.append("boundaries")
            
            if wins:
                feedback = f"Good job on {', '.join(wins[:2])}! "
            else:
                feedback = "Check-in recorded. "
            
            # Suggest focus area
            if not tier1.deep_work:
                feedback += "Focus on deep work tomorrow."
            elif not tier1.skill_building:
                feedback += "Don't skip skill building tomorrow."
            elif not tier1.sleep:
                feedback += "Prioritize sleep tomorrow."
            else:
                feedback += "Keep up the momentum!"
            
            return feedback

    def should_offer_support_guidance(
        self,
        tier1: Tier1NonNegotiables,
        self_rating: int,
        rating_reason: str,
        challenges: str,
        recent_checkins: Optional[List[Dict]] = None,
        compliance_score: Optional[int] = None,
    ) -> bool:
        """
        Decide whether a check-in deserves a short support section.

        The goal is to catch genuine stress/overwhelm signals without turning
        every imperfect day into an unsolicited emotional-support response.
        """
        text = f"{rating_reason} {challenges}".lower()
        explicit_patterns = [
            r"\bstress(?:ed)?\b",
            r"\banxious\b",
            r"\banxiety\b",
            r"\boverwhelm(?:ed|ing)?\b",
            r"\bburn(?:ed)? out\b",
            r"\bpanic(?:king|ked)?\b",
            r"\bdrained\b",
            r"\bexhausted\b",
            r"\bno momentum\b",
            r"\black of momentum\b",
        ]
        explicit_hits = sum(
            1 for pattern in explicit_patterns if re.search(pattern, text)
        )

        score = 0
        if explicit_hits:
            score += 2 + min(explicit_hits - 1, 1)

        if self_rating <= 4:
            score += 2
        elif self_rating <= 6:
            score += 1

        if not tier1.sleep:
            score += 1
        if not tier1.deep_work:
            score += 1
        if not tier1.training:
            score += 0.5

        if compliance_score is not None and compliance_score < 70:
            score += 1

        if recent_checkins:
            trend = self._analyze_trend(recent_checkins, compliance_score or 0)
            if "declining" in trend or "struggling" in trend:
                score += 1

        # Explicit emotional language should usually be enough when paired with
        # at least one other signal. Inferred support needs a higher bar.
        if explicit_hits and score >= 3:
            return True

        return score >= 4

    async def generate_support_guidance(
        self,
        user_id: str,
        tier1: Tier1NonNegotiables,
        compliance_score: int,
        self_rating: int,
        rating_reason: str,
        challenges: str,
        current_streak: int,
        recent_checkins: Optional[List[Dict]] = None,
    ) -> str:
        """
        Generate a short LLM-based support section for difficult check-ins.

        This is intentionally compact and action-oriented so it can live inside
        the main check-in response instead of showing up as a separate message.
        """
        recent_checkins = recent_checkins or self._get_recent_checkins(user_id, days=7)
        trend = self._analyze_trend(recent_checkins, compliance_score)

        prompt = f"""Write a short support add-on for a daily check-in response.

CHECK-IN SIGNALS:
- Compliance: {compliance_score}%
- Self-rating: {self_rating}/10
- Rating reason: "{rating_reason}"
- Challenges: "{challenges}"
- Sleep met: {tier1.sleep}
- Training done: {tier1.training}
- Deep work done: {tier1.deep_work}
- Skill building done: {tier1.skill_building}
- Current streak: {current_streak} days
- Recent trend: {trend}

TASK:
- Write 70-120 words max.
- Give calm, specific guidance tied to today's signals.
- Focus on one concrete next step for tonight or tomorrow.
- Mention stress/overwhelm ONLY if the user's wording clearly supports it.

DO NOT:
- Do not use therapy scripts like "I hear you" or "your feelings are valid."
- Do not use numbered CBT steps.
- Do not ask multiple questions.
- Do not repeat generic lines like "stress is a signal, not weakness."

STYLE:
- Direct, grounded, supportive.
- Written as a short in-line coaching note for the main check-in summary.

Return only the support note text."""

        guidance = await self.llm.generate_text(
            prompt=prompt,
            max_output_tokens=220,
            temperature=0.5
        )
        return guidance.strip()
    
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
            
            # Extract metrics AND qualitative data. The trend analysis
            # only uses compliance_score, but the feedback prompt now
            # uses challenges/priorities/tier1 for yesterday comparisons.
            recent_data = []
            for checkin in checkins:
                entry = {
                    'date': checkin.date,
                    'compliance_score': checkin.compliance_score,
                    'rating': None,
                }
                if hasattr(checkin, 'responses') and checkin.responses:
                    entry['rating'] = checkin.responses.rating
                    entry['challenges'] = checkin.responses.challenges
                    entry['rating_reason'] = checkin.responses.rating_reason
                    entry['tomorrow_priority'] = checkin.responses.tomorrow_priority
                    entry['tomorrow_obstacle'] = checkin.responses.tomorrow_obstacle
                if hasattr(checkin, 'tier1_non_negotiables') and checkin.tier1_non_negotiables:
                    t1 = checkin.tier1_non_negotiables
                    entry['tier1'] = {
                        'sleep': t1.sleep, 'training': t1.training,
                        'deep_work': t1.deep_work, 'skill_building': t1.skill_building,
                        'zero_porn': t1.zero_porn, 'boundaries': t1.boundaries,
                    }
                recent_data.append(entry)
            
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
        recent_checkins: List[Dict],
        yesterday_checkin: dict = None,
    ) -> str:
        """
        Build the feedback generation prompt for Gemini
        
        This is where the magic happens - the prompt structure determines
        the quality and consistency of the AI feedback.
        
        Prompt Engineering Principles Used:
        -----------------------------------
        1. <b>Clear Role</b>: "You are a constitution accountability coach"
        2. <b>Structured Data</b>: Organized input (today's data, context, trends)
        3. <b>Output Format</b>: Specific word count and sections
        4. <b>Tone Specification</b>: Direct, motivating, no fluff
        5. <b>Examples</b>: (Could add few-shot examples for better quality)
        6. <b>Constraints</b>: What to avoid (generic praise, fluff, vague advice)
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

{self._build_weekly_qualitative_section(recent_checkins)}
CONSTITUTION PRINCIPLES (reference these):
------------------------------------------
{constitution_excerpt}

{self._build_yesterday_section(yesterday_checkin)}
GENERATE FEEDBACK (150-250 words):
----------------------------------
Write feedback that:

1. <b>ACKNOWLEDGE TODAY</b> (1-2 sentences):
   - Reference exact compliance score
   - If perfect (100%): Strong praise
   - If good (80-99%): Acknowledge + note what was missed
   - If struggling (<80%): Direct but supportive

2. <b>STREAK CONTEXT</b> (1-2 sentences):
   - Mention current streak number
   - If milestone (7, 14, 30, 60, 100 days): Celebrate it
   - If near personal best: Motivate to break it
   - Connect streak to identity/systems

3. <b>PATTERN OBSERVATION</b> (1-2 sentences):
   - Note the trend (improving/declining/consistent)
   - Reference SPECIFIC recurring themes from the Weekly Qualitative Context above
   - If the same challenge or obstacle appears multiple days: call it out explicitly
   - If motivation/ratings are declining: note the pattern with specific dates

4. <b>CONSTITUTION CONNECTION</b> (1-2 sentences):
   - Reference a relevant principle from constitution
   - Connect today's actions to that principle
   - Use principle names (e.g., "Physical Sovereignty", "Create Don't Consume")

5. <b>FORWARD FOCUS</b> (1-2 sentences):
   - ONE specific action for tomorrow
   - Reference their stated priority or obstacle
   - Make it actionable and concrete

TONE REQUIREMENTS:
- Direct and clear (no corporate-speak or generic praise)
- Motivating but realistic
- Like a coach who knows the athlete well
- Use emojis sparingly (🔥, ✅, 💪, 🎯 only)
- Focus on BEHAVIOR, not feelings
- Do not turn this into therapy or emotional-support scripting
- Do not write "I hear you", "your feelings are valid", or long stress/anxiety coaching
- NO: "Great job!", "Keep it up!", "You're amazing!"
- YES: Specific observations, data, actionable guidance

WORD COUNT: 150-250 words max
FORMAT: Paragraphs, not bullet points

Feedback:"""

        return prompt
    
    def _build_yesterday_section(self, yesterday_checkin: dict = None) -> str:
        """
        Build the YESTERDAY'S CONTEXT section for the feedback prompt.
        
        When present, this gives the AI specific instructions to compare
        today's results against what the user committed to yesterday.
        This is what transforms generic feedback into personal accountability.
        """
        if not yesterday_checkin:
            return ""
        
        yc = yesterday_checkin
        tier1_str = ""
        if yc.get('tier1'):
            items = []
            for k, v in yc['tier1'].items():
                status = "done" if v else "MISSED"
                items.append(f"{k.replace('_', ' ')}: {status}")
            tier1_str = ", ".join(items)
        
        return f"""YESTERDAY'S CONTEXT (CRITICAL - REFERENCE THIS IN YOUR FEEDBACK):
------------------------------------------------------------------
Yesterday's compliance: {yc.get('compliance_score', 'N/A')}%
Yesterday's self-rating: {yc.get('rating', 'N/A')}/10
Yesterday's reason: "{yc.get('rating_reason', 'N/A')}"
Yesterday's priority for today: "{yc.get('tomorrow_priority', 'N/A')}"
Yesterday's anticipated obstacle: "{yc.get('tomorrow_obstacle', 'N/A')}"
Yesterday's challenges: "{yc.get('challenges', 'N/A')}"
Yesterday's Tier 1: {tier1_str}

INSTRUCTIONS FOR USING YESTERDAY'S CONTEXT:
- Compare today's Tier 1 results against yesterday's stated intentions
- If they said they'd fix X but X is STILL failed today: call them out DIRECTLY, reference their exact words
- If they said obstacle Y would be a problem and it was: acknowledge the struggle but push for a concrete plan
- If they improved on what they committed to improve: praise the follow-through specifically
- If they said they'd rate themselves higher today but didn't: note the gap between intention and action

"""

    def _build_weekly_qualitative_section(self, recent_checkins: List[Dict]) -> str:
        """
        Build the WEEKLY QUALITATIVE CONTEXT section for the feedback prompt.

        Includes all 7 days' qualitative data (challenges, rating reasons,
        priorities, obstacles, tier1 breakdown) so the AI can spot patterns
        like recurring stress, repeating obstacles, or declining motivation.
        """
        if not recent_checkins or len(recent_checkins) < 2:
            return ""

        lines = [
            "WEEKLY QUALITATIVE CONTEXT (All 7 Days — Use for Pattern Recognition):",
            "----------------------------------------------------------------------",
        ]

        # Format each day's entry
        for i, checkin in enumerate(recent_checkins, 1):
            day_label = "TODAY - MOST IMPORTANT" if i == len(recent_checkins) else f"Day {i}"
            date_str = checkin.get('date', 'unknown')
            score = checkin.get('compliance_score', 'N/A')
            rating = checkin.get('rating', 'N/A')

            lines.append(f"{day_label} ({date_str}): Score {score}%, Rating {rating}/10")

            # Qualitative fields
            challenges = checkin.get('challenges')
            if challenges:
                lines.append(f"  Challenges: \"{challenges}\"")

            rating_reason = checkin.get('rating_reason')
            if rating_reason:
                lines.append(f"  Reason: \"{rating_reason}\"")

            priority = checkin.get('tomorrow_priority')
            if priority:
                lines.append(f"  Priority: \"{priority}\"")

            obstacle = checkin.get('tomorrow_obstacle')
            if obstacle:
                lines.append(f"  Obstacle: \"{obstacle}\"")

            # Tier 1 breakdown
            tier1 = checkin.get('tier1')
            if tier1:
                t1_items = []
                for k, v in tier1.items():
                    icon = "✅" if v else "❌"
                    t1_items.append(f"{k.replace('_', ' ').title()} {icon}")
                lines.append(f"  Tier 1: {', '.join(t1_items)}")

            lines.append("")  # blank line between days

        lines.append("INSTRUCTIONS FOR USING WEEKLY CONTEXT:")
        lines.append("- Identify recurring themes across the week (e.g., \"stress\" mentioned 4 times)")
        lines.append("- Note if the same obstacle appears repeatedly (e.g., \"phone addiction\" on 3 days)")
        lines.append("- Compare today's priority vs what was actually achieved yesterday")
        lines.append("- Reference specific patterns from the week, not just yesterday")
        lines.append("- Give MORE weight to recent days, but don't ignore earlier signals")
        lines.append("")

        return "\n".join(lines)

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
