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
        
        **Phase 3D Update:**
        Now includes specific template builders for new patterns:
        - snooze_trap → _build_snooze_trap_intervention()
        - consumption_vortex → _build_consumption_vortex_intervention()
        
        Args:
            pattern: Detected pattern
            current_streak: User's current streak
            
        Returns:
            Template-based intervention message (pattern-specific if available)
        """
        # Phase 3D: Use specific template builders for new patterns
        # These provide better interventions than generic template
        if pattern.type == "snooze_trap":
            # Need user object for personalization - create minimal user
            from src.models.schemas import User, UserStreaks
            user = User(
                user_id="",
                telegram_id=0,
                name="User",
                streaks=UserStreaks(current_streak=current_streak)
            )
            return self._build_snooze_trap_intervention(pattern, user)
        
        if pattern.type == "consumption_vortex":
            from src.models.schemas import User, UserStreaks
            user = User(
                user_id="",
                telegram_id=0,
                name="User",
                streaks=UserStreaks(current_streak=current_streak)
            )
            return self._build_consumption_vortex_intervention(pattern, user)
        
        if pattern.type == "deep_work_collapse":
            from src.models.schemas import User, UserStreaks
            user = User(
                user_id="",
                telegram_id=0,
                name="User",
                streaks=UserStreaks(current_streak=current_streak)
            )
            return self._build_deep_work_collapse_intervention(pattern, user)
        
        if pattern.type == "relationship_interference":
            from src.models.schemas import User, UserStreaks
            user = User(
                user_id="",
                telegram_id=0,
                name="User",
                streaks=UserStreaks(current_streak=current_streak)
            )
            return self._build_relationship_interference_intervention(pattern, user)
        
        # Generic fallback for other patterns
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
    
    def _build_snooze_trap_intervention(self, pattern: Pattern, user) -> str:
        """
        Build snooze trap intervention message (Phase 3D).
        
        **What is Snooze Trap?**
        Pattern of waking >30min late for 3+ consecutive days.
        This is an early warning sign that leads to:
        - Rushed mornings → no deep work
        - Sleep debt accumulation
        - Discipline erosion → other habits slip
        
        **Constitution Reference:**
        Section G - Interrupt Pattern 2: "The Snooze Trap"
        - Each snooze = 15min earlier bedtime (forced debt repayment)
        - 3 snoozes/week = Maintenance Mode warning
        
        **Message Strategy:**
        1. Show evidence (avg snooze time, worst day)
        2. Connect to career goal (June 2026 ₹28-42 LPA)
        3. Reference historical pattern (Feb 2025 snooze → spiral)
        4. ONE specific action: Move alarm across room TONIGHT
        
        Args:
            pattern: Snooze trap pattern data
            user: User object for personalization
            
        Returns:
            Template-based intervention message
        """
        avg_snooze = pattern.data.get("avg_snooze_minutes", 0)
        days = len(pattern.data.get("days_affected", []))
        worst_day = pattern.data.get("worst_day", {})
        target_wake = pattern.data.get("target_wake", "06:30")
        
        return f"""⚠️ **SNOOZE TRAP DETECTED**

You've snoozed for {avg_snooze}+ minutes for {days} consecutive days.

**This pattern leads to:**
• Rushed mornings → missed deep work sessions
• Sleep debt accumulation → worse performance
• Compliance decline → discipline erosion
• Energy drain throughout day

**Constitution Protocol:**
1. **TONIGHT:** Move alarm across room (physical distance)
2. Sleep 30min earlier (target: 10:30 PM → 7hrs sleep)
3. **TOMORROW:** No snooze button - stand up immediately
4. Morning routine: Bathroom → Water → Natural light

**Your June 2026 goal (₹28-42 LPA) depends on morning execution.**

Target wake time: {target_wake}
Tomorrow: NO SNOOZE. Execute your constitution.

*Historical note: Feb 2025 snooze trap led to 3-month stall.*
Don't repeat history. Break the pattern NOW."""
    
    def _build_consumption_vortex_intervention(self, pattern: Pattern, user) -> str:
        """
        Build consumption vortex intervention message (Phase 3D).
        
        **What is Consumption Vortex?**
        Pattern of >3 hours daily consumption for 5+ days.
        Indicates shift from creator → consumer mode.
        
        **Constitution Reference:**
        Section G - Interrupt Pattern 3: "The Consumption Vortex"
        Principle 2: "Create Don't Consume"
        - Time is irreplaceable
        - Consumption >2hrs/day = warning sign
        
        **Why This Matters:**
        - 21 hours/week = 1260 minutes of life
        - Time that could go to skill building → wasted
        - Dopamine hijacking → makes deep work harder
        - Avoidance behavior → what are you avoiding?
        
        **Message Strategy:**
        1. Quantify the loss (total hours, minutes of life)
        2. Quote Principle 2 ("Create Don't Consume")
        3. Reference historical pattern (Jan 2025 consumption → job search stall)
        4. Action: Install blockers + delete apps
        
        Args:
            pattern: Consumption vortex pattern data
            user: User object for personalization
            
        Returns:
            Template-based intervention message
        """
        days = pattern.data.get("days_affected", 0)
        avg_hours = pattern.data.get("avg_consumption_hours", 0)
        total_hours = pattern.data.get("total_weekly_hours", 0)
        
        # Calculate minutes of life
        total_minutes = int(total_hours * 60)
        
        return f"""⚠️ **CONSUMPTION VORTEX DETECTED**

You've averaged {avg_hours} hours of consumption for {days} days.
**Total this week: {total_hours} hours = {total_minutes} minutes of life.**

**You're becoming a consumer, not a creator.**

**Constitution Violation:**
• Principle 2: "Create Don't Consume"
• Your time is irreplaceable
• {total_hours} hours = potential for 2-3 LeetCode problems/day
• That's what separates ₹28 LPA from your current path

**Actions NOW:**
1. **TODAY:** Install blockers (Freedom app, Cold Turkey)
2. Delete time-sink apps from phone (YouTube, Reddit, Twitter)
3. **TOMORROW:** Schedule 2-hour creation block (morning: 6:30-8:30 AM)
4. Track consumption daily (accountability prevents drift)

**Historical Pattern:**
Jan 2025: 15hrs/week consumption → job search stalled → 3-month spiral → opportunity lost

**Your ₹28-42 LPA goal requires creation, not consumption.**

Tomorrow: <2 hours consumption. No exceptions.
Block apps NOW. Don't wait.

*What are you avoiding? That's what you should be working on.*"""
    
    def _build_deep_work_collapse_intervention(self, pattern: Pattern, user) -> str:
        """
        Build deep work collapse intervention message (Phase 3D Enhanced).
        
        **What is Deep Work Collapse?**
        Pattern of <1.5 hours deep work for 5+ consecutive days.
        This is CRITICAL severity because it directly impacts June 2026 career goal.
        
        **Why This is CRITICAL (Phase 3D Upgrade):**
        - Constitution mandates 2+ hours daily deep work
        - Your ₹28-42 LPA goal by June 2026 requires daily skill building
        - Without deep work: No LeetCode progress, no system design mastery
        - Historical: Jan 2025 collapse → 3-month spiral → opportunity lost
        
        **Constitution Reference:**
        Section III.C: Daily AI Check-In
        - "2+ hours focused work/study" (Tier 1 non-negotiable)
        Principle 2: "Create Don't Consume"
        Section III.B: Career Goal (₹28-42 LPA by June 2026)
        
        **Message Strategy:**
        1. Show evidence (avg hours, days affected)
        2. Connect to specific goal (June 2026 career)
        3. Reference historical pattern (Jan 2025)
        4. Root cause analysis (what's blocking deep work?)
        5. ONE specific action: Block 2-hour morning slot
        
        Args:
            pattern: Deep work collapse pattern data
            user: User object for personalization
            
        Returns:
            Template-based intervention message
        """
        days = pattern.data.get("days_affected", 0)
        avg_hours = pattern.data.get("avg_deep_work_hours", 0)
        target = pattern.data.get("target", 2.0)
        
        return f"""🚨 **DEEP WORK COLLAPSE**

You've averaged {avg_hours} hours deep work for {days} days.
**Constitution target: {target}+ hours.**

**This is how you miss June 2026 career goals (₹28-42 LPA).**

**Historical Pattern:**
• Jan 2025: Deep work collapse → no job offers
• Recovery took 3 months
• You've seen this movie before

**Root Cause Analysis:**
What's blocking deep work?
• Meetings eating your calendar?
• Distractions (phone, notifications)?
• Energy/motivation low?
• Avoiding difficult tasks (LeetCode hard problems)?

**Actions NOW:**
1. **Block calendar:** 2-hour morning slot (6:30-8:30 AM) - NON-NEGOTIABLE
2. Phone on airplane mode during deep work
3. Track specific output (LeetCode problems solved, not just "hours")
4. Identify #1 distraction → remove it TODAY

**Tomorrow's Deep Work:**
2+ hours, no excuses. Your ₹28-42 LPA goal depends on it.

**If you don't fix this by Friday → Maintenance Mode warning.**

*Your future self will either thank you or regret this week. Choose.*"""
    
    def _build_relationship_interference_intervention(self, pattern: Pattern, user) -> str:
        """
        Build relationship interference intervention message (Phase 3D).
        
        **What is Relationship Interference?**
        CRITICAL pattern where boundary violations correlate (>70%) with 
        sleep/training failures. This is the EXACT pattern from toxic relationship
        (Feb-July 2025) that caused 6-month regression.
        
        **Why This is CRITICAL:**
        Historical evidence from constitution:
        - Feb-July 2025: Boundary violations → sleep/training failures
        - 6-month regression (job search stalled, fitness declined)
        - Pattern ended in breakup anyway (fear of loss = loss happened)
        - Constitution Principle 5 violation: "Fear of loss is not a reason to stay"
        
        **Constitution Reference:**
        Section G - Interrupt Pattern 4: "The Boundary Violation (Relationship)"
        Principle 5: "Fear of Loss is Not a Reason to Stay"
        - Quote: "I do not tolerate toxic relationships out of fear of losing them"
        
        **Detection Method:**
        Correlation-based (not simple threshold):
        - Boundary violation days: X
        - Days where violation → sleep/training failure: Y
        - Correlation: Y/X > 70% → PATTERN DETECTED
        
        **Message Strategy:**
        1. Show evidence (correlation percentage, days affected)
        2. Reference EXACT historical pattern (Feb-July 2025)
        3. Quote Constitution Principle 5
        4. Ask critical questions (are you sacrificing constitution?)
        5. Action: Set boundary TODAY, observe reaction
        
        Args:
            pattern: Relationship interference pattern data
            user: User object for personalization
            
        Returns:
            Template-based intervention message
        """
        days = pattern.data.get("days_affected", 0)
        boundary_violations = pattern.data.get("boundary_violations", 0)
        correlation = pattern.data.get("correlation_pct", 0)
        total = pattern.data.get("total_days_analyzed", 0)
        
        return f"""🚨 **RELATIONSHIP INTERFERENCE PATTERN DETECTED**

{days}/{boundary_violations} boundary violations → Sleep/Training failures
**Correlation: {correlation}% (threshold: 70%)**

**This is the EXACT pattern from your toxic relationship (Feb-July 2025).**

**Constitution Principle 5:**
"Fear of loss is not a reason to stay."
"I do not tolerate toxic relationships, jobs, or situations out of fear of losing them."

**Historical Consequences:**
• Feb-July 2025: 6-month regression
• Sacrificed sleep for 1-1.5hr calls about partying
• Missed workouts due to exhaustion
• Job search stalled → opportunity lost
• Ended in breakup anyway (feared loss happened regardless)

**Critical Questions:**
1. Are you sacrificing constitution for this person?
2. Do they respect your boundaries when you set them?
3. Are you afraid to enforce boundaries? ⚠️ RED FLAG
4. Is this relationship making you better or worse?

**Actions NOW:**
1. **Set boundary TODAY:** "I need my sleep/training time, non-negotiable."
2. Observe reaction: Supportive? Or guilt-trip?
3. If guilt-trip → Relationship audit required
4. If pattern continues 3 more days → Serious conversation needed

**This is your system telling you something is wrong.**

Listen to it. Your future self will thank you.

*You already know what you need to do. The question is: will you do it?*"""


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
