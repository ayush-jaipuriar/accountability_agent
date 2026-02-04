"""
Intervention Agent - Generate Warning Messages for Detected Patterns

When Pattern Detection Agent finds a violation pattern, this agent generates
a personalized intervention message to send to the user.

What is an Intervention?
------------------------
An intervention is a proactive warning message that:
1. Alerts user to a detected pattern
2. Shows evidence (data)
3. References violated constitution principle
4. Explains consequences if pattern continues
5. Provides ONE specific action to break the pattern

Example Intervention (Sleep Degradation):
------------------------------------------
🚨 PATTERN ALERT: Sleep Degradation Detected

Last 3 nights: 5.5hrs, 5hrs, 5.2hrs (avg: 5.2hrs)
Your constitution requires 7+ hours minimum.

This violates Principle 1: Physical Sovereignty.
"My body is my primary asset. No external pressure compromises my long-term health."

If this continues:
• Cognitive performance drops
• Training recovery suffers
• You're sacrificing tomorrow for today

Action Required:
Tonight: In bed by 11 PM, no exceptions. Set alarm for 6:30 AM (7.5hrs).
Block calendar 10:30-11 PM as "Sleep Prep" - non-negotiable.

Your 47-day streak is at risk. Protect it by protecting your sleep.

Key Concepts:
-------------
1. **Firmness + Support**: 
   - Not: "Maybe consider getting more sleep?"
   - Yes: "Action Required: In bed by 11 PM, no exceptions."
   
2. **Evidence-Based**:
   - Shows actual numbers (5.2 hrs average, not "you're sleeping poorly")
   - References specific dates
   - Quantifiable data

3. **Constitution-Connected**:
   - Quotes relevant principle
   - Reminds user of their own rules
   - "This is what YOU decided"

4. **Consequence-Aware**:
   - Not scare tactics
   - But honest about what happens if pattern continues
   - Based on user's historical patterns

5. **Action-Oriented**:
   - ONE specific action (not 5 vague suggestions)
   - Time-bound (tonight, tomorrow)
   - Concrete (11 PM, not "earlier")

Intervention Structure:
-----------------------
1. **Alert** (1 line): Clear statement of pattern
2. **Evidence** (2-3 lines): Data showing the pattern
3. **Constitution Reference** (2-3 lines): Which principle violated
4. **Consequences** (3-4 lines): What happens if continues
5. **Action Required** (2-3 lines): Specific next step
6. **Motivation** (1 line): Reference streak/progress at stake

Token Budget:
-------------
- Input: ~600 tokens (pattern data + constitution + context)
- Output: ~200 tokens (intervention message)
- Total: ~800 tokens per intervention
- Cost: ~$0.002 per intervention
"""

from src.agents.pattern_detection import Pattern
from src.services.llm_service import get_llm_service
from src.services.constitution_service import constitution_service
from src.services.firestore_service import firestore_service
from src.config import settings
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class InterventionAgent:
    """
    Generates intervention messages for detected patterns
    """
    
    def __init__(self, project_id: str):
        """
        Initialize Intervention Agent
        
        Args:
            project_id: GCP project ID for LLM service
        """
        self.llm = get_llm_service(
            project_id=project_id,
            location=settings.vertex_ai_location,
            model_name=settings.gemini_model
        )
        logger.info("Intervention Agent initialized")
    
    async def generate_intervention(
        self,
        user_id: str,
        pattern: Pattern
    ) -> str:
        """
        Generate intervention message for detected pattern
        
        Phase 3B Update: Ghosting patterns use template-based messages (no LLM).
        Other patterns use AI generation for personalization.
        
        Args:
            user_id: User ID
            pattern: Detected pattern object
            
        Returns:
            Intervention message text (200-300 words)
        """
        try:
            # Get user context
            user = firestore_service.get_user(user_id)
            if user:
                current_streak = user.streaks.current_streak
                mode = user.constitution_mode
            else:
                current_streak = 0
                mode = "maintenance"
            
            # Phase 3B: Ghosting patterns use template-based messages
            if pattern.type == "ghosting":
                logger.info(f"Generating ghosting intervention for user {user_id}: Day {pattern.data.get('days_missing', 0)}")
                intervention = self._build_ghosting_intervention(pattern, user)
                logger.info(f"✅ Generated ghosting intervention: {len(intervention)} chars")
                return intervention
            
            # Other patterns: Use AI generation
            # Get relevant constitution section
            constitution_text = self._get_relevant_principle(pattern.type)
            
            # Build intervention prompt
            prompt = self._build_intervention_prompt(
                pattern=pattern,
                current_streak=current_streak,
                mode=mode,
                constitution_text=constitution_text
            )
            
            # Generate intervention with AI
            logger.info(f"Generating {pattern.severity} intervention for user {user_id}: {pattern.type}")
            
            intervention = await self.llm.generate_text(
                prompt=prompt,
                max_output_tokens=3072,  # Increased 1.5x from 2048 (gemini-2.5 with thinking disabled)
                temperature=0.6  # Slightly lower than feedback (more serious tone)
            )
            
            logger.info(f"✅ Generated intervention for {pattern.type}: {len(intervention)} chars")
            
            return intervention.strip()
            
        except Exception as e:
            logger.error(f"❌ Intervention generation failed: {e}", exc_info=True)
            # Fallback to template-based intervention
            return self._fallback_intervention(pattern, current_streak if 'current_streak' in locals() else 0)
    
    def _build_intervention_prompt(
        self,
        pattern: Pattern,
        current_streak: int,
        mode: str,
        constitution_text: str
    ) -> str:
        """
        Build intervention generation prompt
        
        Prompt Engineering for Interventions:
        -------------------------------------
        1. **Severity-Appropriate Tone**:
           - CRITICAL: Firm, urgent ("Action required NOW")
           - HIGH: Direct, serious ("This is a problem")
           - MEDIUM: Concerned, supportive ("Let's address this")
        
        2. **Evidence First**:
           - Start with data (numbers, dates)
           - Then interpretation
           - Then consequences
        
        3. **Constitution as Authority**:
           - Quote the rule the user wrote
           - "YOUR constitution says..."
           - Not judgment, just accountability to self
        """
        # Map severity to emoji and tone
        severity_config = {
            "critical": {
                "emoji": "🚨🚨🚨",
                "tone": "URGENT and FIRM. This is a crisis-level pattern that requires immediate action."
            },
            "high": {
                "emoji": "🚨",
                "tone": "SERIOUS and DIRECT. This is a significant problem that needs addressing."
            },
            "medium": {
                "emoji": "⚠️",
                "tone": "CONCERNED but SUPPORTIVE. This is worth addressing before it gets worse."
            },
            "low": {
                "emoji": "ℹ️",
                "tone": "INFORMATIVE and OBSERVATIONAL. Worth monitoring."
            }
        }
        
        config = severity_config.get(pattern.severity, severity_config["medium"])
        emoji = config["emoji"]
        tone_instruction = config["tone"]
        
        # Build pattern evidence summary
        evidence = pattern.data.get("message", str(pattern.data))
        
        prompt = f"""Generate an intervention message for this detected constitution violation pattern.

{emoji} PATTERN DETECTED:
Type: {pattern.type.replace('_', ' ').title()}
Severity: {pattern.severity.upper()}
Evidence: {evidence}
Data: {pattern.data}

USER CONTEXT:
Current Streak: {current_streak} days
Constitution Mode: {mode}

VIOLATED PRINCIPLE/RULE:
{constitution_text}

GENERATE INTERVENTION (200-300 words):
--------------------------------------
Write an intervention message with this structure:

1. **ALERT** (1 line with {emoji}):
   "🚨 PATTERN ALERT: [Pattern Name]"

2. **EVIDENCE** (2-3 lines):
   Show the data:
   - Specific numbers (hours, days, scores)
   - Dates when applicable
   - What the constitution requires vs what happened

3. **CONSTITUTION REFERENCE** (2-3 lines):
   - Quote the relevant principle
   - Connect today's data to the rule violated
   - Remind: "This is what YOU decided"

4. **CONSEQUENCES** (3-4 bullet points):
   "If this pattern continues:"
   - What happens to performance
   - What happens to other areas (cascade effects)
   - Historical context if relevant

5. **ACTION REQUIRED** (2-4 lines):
   "Action Required:"
   - ONE specific action
   - Time-bound (tonight, tomorrow, next 24 hours)
   - Concrete and measurable
   - Remove obstacles (e.g., "Delete app", "Block calendar", "Text friend")

6. **MOTIVATION** (1 line):
   Reference streak at stake:
   "Your {current_streak}-day streak is at risk. Protect it by [protecting X]."

TONE: {tone_instruction}
- Use direct language (no softening: "maybe", "consider", "might want to")
- Be specific (times, numbers, actions)
- Not judgmental, but not apologetic either
- Like a coach calling out a problem, demanding a fix

FORMAT: Use {emoji} at start, **bold** for "Action Required" heading

Intervention:"""

        return prompt
    
    def _get_relevant_principle(self, pattern_type: str) -> str:
        """
        Map pattern type to relevant constitution principle
        
        Args:
            pattern_type: Type of pattern detected
            
        Returns:
            Relevant excerpt from constitution
        """
        # Get abbreviated constitution
        constitution_text = constitution_service.get_constitution_summary(max_chars=1000)
        
        # Map pattern to principle (for reference in prompt)
        principle_mapping = {
            "sleep_degradation": "Principle 1: Physical Sovereignty - Sleep is non-negotiable",
            "training_abandonment": "Principle 1: Physical Sovereignty - Training maintains discipline",
            "porn_relapse_pattern": "Tier 1 Non-Negotiables: Zero Porn (absolute rule)",
            "compliance_decline": "Systems Over Willpower - Consistency is the foundation",
            "deep_work_collapse": "Principle 2: Create Don't Consume - Deep work over consumption"
        }
        
        relevant_principle = principle_mapping.get(pattern_type, "Constitution Violation")
        
        return f"{relevant_principle}\n\n{constitution_text[:500]}..."
    
    def _fallback_intervention(self, pattern: Pattern, current_streak: int) -> str:
        """
        Fallback template-based intervention if AI generation fails
        
        Args:
            pattern: Detected pattern
            current_streak: User's current streak
            
        Returns:
            Basic intervention message
        """
        severity_emoji = {
            "critical": "🚨🚨🚨",
            "high": "🚨",
            "medium": "⚠️",
            "low": "ℹ️"
        }
        emoji = severity_emoji.get(pattern.severity, "⚠️")
        
        pattern_name = pattern.type.replace('_', ' ').title()
        evidence = pattern.data.get("message", str(pattern.data))
        
        message = f"""{emoji} PATTERN ALERT: {pattern_name}

Pattern detected in your recent check-ins:
{evidence}

This violates your constitution.

Action Required: Review your last 3-7 days and identify what needs to change. 
Your {current_streak}-day streak is at risk.

Reply with your plan to break this pattern.

(Note: AI intervention temporarily unavailable - using basic template)"""
        
        return message
    
    def _build_ghosting_intervention(self, pattern: Pattern, user) -> str:
        """
        Build escalating ghosting intervention message (Phase 3B).
        
        **What is This?**
        When a user disappears (ghosts) after missing check-ins, we send
        escalating intervention messages based on how long they've been gone.
        
        **Why Escalating Messages?**
        - Day 2: Gentle nudge (empathy first)
        - Day 3: Firm warning (accountability)
        - Day 4: Critical with historical reference (evidence-based urgency)
        - Day 5+: Emergency with partner escalation (social support)
        
        **Message Structure:**
        Each message includes:
        1. Severity indicator (emoji)
        2. Days missing count
        3. Appropriate tone for severity level
        4. Action prompt (/checkin command)
        5. Context (streak at risk, shields available, etc.)
        
        **Theory - Progressive Escalation:**
        Based on crisis intervention research:
        - Start gentle (avoid defensiveness)
        - Build urgency gradually
        - Reference personal history (Feb 2025 spiral)
        - Activate social support at Day 5 (partner notification)
        
        Args:
            pattern: Ghosting pattern with days_missing, previous_streak, etc.
            user: User object for personalization (streak, shields, partner)
            
        Returns:
            Intervention message string (ready to send via Telegram)
            
        Example Output (Day 2):
            "👋 **Missed you yesterday!**
            
            You had a 47-day streak going. Everything okay?
            
            Quick check-in: /checkin"
        """
        days = pattern.data["days_missing"]
        streak = pattern.data.get("previous_streak", 0)
        
        # Day 2: Gentle Nudge
        if days == 2:
            return (
                "👋 **Missed you yesterday!**\n\n"
                f"You had a {streak}-day streak going. Everything okay?\n\n"
                "Quick check-in: /checkin"
            )
        
        # Day 3: Firm Warning
        elif days == 3:
            return (
                "⚠️ **3 Days Missing**\n\n"
                f"Your {streak}-day streak is at risk. This is a constitution violation.\n\n"
                "Check in NOW to save your progress: /checkin"
            )
        
        # Day 4: Critical with Historical Reference
        elif days == 4:
            return (
                "🚨 **4-Day Absence - CRITICAL**\n\n"
                f"You had a {streak}-day streak. Last time this happened (Feb 2025): "
                "6-month spiral.\n\n"
                "**Don't let history repeat.** Check in immediately: /checkin"
            )
        
        # Day 5+: Emergency with Partner/Shield Info
        else:  # 5+
            # Add streak shield info if available
            shield_text = ""
            if hasattr(user, 'streak_shields') and user.streak_shields.available > 0:
                shield_text = (
                    f"\n\n🛡️ You have {user.streak_shields.available} streak shield(s) available. "
                    "Use one: /use_shield"
                )
            
            # Add partner notification info if partner exists
            partner_text = ""
            if hasattr(user, 'accountability_partner_name') and user.accountability_partner_name:
                partner_text = (
                    f"\n\n👥 I'm notifying your accountability partner "
                    f"({user.accountability_partner_name})."
                )
            
            return (
                "🔴 **EMERGENCY - 5+ Days Missing**\n\n"
                f"Your {streak}-day streak is gone. This is exactly how the Feb 2025 "
                "regression started.\n\n"
                "**You need help. Do this NOW:**\n"
                "1. Check in: /checkin\n"
                "2. Text a friend\n"
                "3. Review your constitution"
                f"{shield_text}"
                f"{partner_text}"
            )


# Global instance
_intervention_agent_instance: Optional[InterventionAgent] = None


def get_intervention_agent(project_id: str) -> InterventionAgent:
    """
    Get or create Intervention agent instance (singleton)
    
    Args:
        project_id: GCP project ID
        
    Returns:
        InterventionAgent instance
    """
    global _intervention_agent_instance
    
    if _intervention_agent_instance is None:
        logger.info("Creating new InterventionAgent instance (singleton)")
        _intervention_agent_instance = InterventionAgent(project_id)
    else:
        logger.debug("Returning existing InterventionAgent instance")
    
    return _intervention_agent_instance


def reset_intervention_agent():
    """Reset Intervention agent instance (for testing)"""
    global _intervention_agent_instance
    _intervention_agent_instance = None
    logger.info("Intervention agent instance reset")
