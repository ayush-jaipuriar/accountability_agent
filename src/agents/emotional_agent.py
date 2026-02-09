"""
Emotional Support Agent - CBT-Style Emotional Support (Phase 3B)

This agent provides Cognitive Behavioral Therapy (CBT) inspired emotional support
for users experiencing difficult moments.

What is CBT-Style Support?
---------------------------
CBT focuses on the connection between thoughts, emotions, and behaviors.
Instead of just validating emotions, CBT helps users:
1. Identify the emotion (what am I feeling?)
2. Identify the trigger (what caused this?)
3. Reframe the thought (is this thought helpful?)
4. Take action (what can I do right now?)

Supported Emotion Types:
------------------------
1. <b>Loneliness</b> - User feeling isolated during intentional celibacy phase
2. <b>Porn Urge</b> - Sexual urges threatening streak
3. <b>Breakup Thoughts</b> - Missing ex, considering reaching out
4. <b>Stress/Anxiety</b> - General overwhelm, work pressure
5. <b>General</b> - Other emotions not fitting above categories

4-Step Protocol Structure:
--------------------------
Every emotional response follows this structure:

1. <b>VALIDATE</b> (2 sentences)
   - Acknowledge the emotion
   - Normalize the feeling (not weakness)
   - Example: "Loneliness is real and temporary. You're not broken for feeling this."

2. <b>REFRAME</b> (2 sentences)
   - Connect to constitution principles
   - Provide perspective shift
   - Example: "Your intentional celibacy is by design, not default. You're building 
              the foundation for the life partner you deserve."

3. <b>TRIGGER</b> (1 question)
   - Ask what caused this feeling
   - Helps user identify patterns
   - Example: "What specifically triggered this feeling right now?"

4. <b>ACTION</b> (3 specific steps)
   - Concrete, immediate actions
   - Numbered list (1, 2, 3)
   - Example: "1. Text one friend: 'Hey, what's up?' 
              2. Go to gym or cafe (public place)
              3. If you can't leave: 20 pushups"

Theory - Why This Works:
-------------------------
1. <b>Validation prevents defensiveness</b> - User feels heard, not judged
2. <b>Reframing provides perspective</b> - Connects temporary emotion to long-term goals
3. <b>Trigger identification</b> - Helps prevent future episodes
4. <b>Action breaks rumination</b> - Physical action interrupts emotional spiral

Example Response:
-----------------
User: "I'm feeling really lonely tonight"

Bot: "I hear you. Loneliness is real and it's temporary. Your intentional celibacy 
      phase is by design, not default. You're building the foundation for the life 
      partner you deserve. This is strategic isolation, not abandonment.

      What specifically triggered this feeling right now? Time of day? Something you saw?

      Here's what you need to do RIGHT NOW:
      1. Text one friend: 'Hey, what's up?' (Don't isolate further)
      2. Go to gym, cafe, or any public place (Physical presence helps)
      3. If you can't leave: 20 pushups, cold shower, or call someone

      Your 47-day streak proves you can handle difficult moments. This feeling is 
      temporary. Your mission is permanent."

Cost Optimization:
------------------
- Emotion classification: ~50 tokens (~$0.000013/call)
- Response generation: ~300 tokens (~$0.000075/call)
- Total: ~$0.00009/emotional interaction
- Expected: 5 uses per user per month = $0.00045/user/month
- 10 users = $0.0045/month (negligible cost)
"""

from typing import Optional
from datetime import datetime
import logging

from src.agents.state import ConstitutionState
from src.services.llm_service import get_llm_service
from src.services.firestore_service import firestore_service
from src.config import settings

logger = logging.getLogger(__name__)


class EmotionalSupportAgent:
    """
    Provides CBT-style emotional support using constitution protocols.
    
    Protocol Structure:
    1. VALIDATE - Acknowledge emotion (not dismiss)
    2. REFRAME - Tie to constitution principles  
    3. TRIGGER - Ask what caused it
    4. ACTION - 3 immediate concrete actions
    """
    
    def __init__(self):
        """
        Initialize Emotional Support Agent.
        
        The agent uses:
        - LLM service for emotion classification and response generation
        - Constitution service for emotional protocols
        - Firestore service for logging interactions
        """
        self.llm = get_llm_service(
            project_id=settings.gcp_project_id,
            location=settings.vertex_ai_location,
            model_name=settings.gemini_model
        )
        logger.info("✅ Emotional Support Agent initialized")
    
    async def process(self, state: ConstitutionState) -> ConstitutionState:
        """
        Process emotional support request.
        
        <b>Flow:</b>
        1. Classify emotion type (loneliness, porn_urge, breakup, stress, general)
        2. Load appropriate protocol from constitution
        3. Get user context (streak, mode, partner)
        4. Generate personalized response using Gemini
        5. Log interaction in Firestore
        6. Return updated state with response
        
        <b>Theory - Why Personalization Matters:</b>
        Generic response: "Don't be sad, things will get better"
        Personalized response: "Your 47-day streak proves you can handle this"
        
        Personal reference = 10x more effective (research-backed)
        
        Args:
            state: Current conversation state with user message
            
        Returns:
            Updated state with emotional support response
            
        Example:
            >>> state = ConstitutionState(
            ...     user_id="user_123",
            ...     message="I'm feeling really lonely tonight",
            ...     intent="emotional"
            ... )
            >>> updated_state = await emotional_agent.process(state)
            >>> print(updated_state.response)
            "I hear you. Loneliness is real..."
        """
        logger.info(f"Processing emotional support for user {state['user_id']}")
        
        try:
            # 1. Classify emotion type
            emotion_type = await self._classify_emotion(state["message"])
            logger.info(f"Classified emotion: {emotion_type}")
            
            # 2. Load protocol from constitution
            protocol = self._get_emotional_protocol(emotion_type)
            
            if not protocol:
                # Fallback for unknown emotions
                protocol = self._get_emotional_protocol("general")
            
            # 3. Get user context for personalization
            user = firestore_service.get_user(state["user_id"])
            
            # 4. Generate personalized response
            response = await self._generate_emotional_response(
                emotion_type=emotion_type,
                user_message=state["message"],
                protocol=protocol,
                user=user
            )
            
            # 5. Log emotional interaction
            firestore_service.store_emotional_interaction(
                user_id=state["user_id"],
                emotion_type=emotion_type,
                user_message=state["message"],
                bot_response=response,
                timestamp=datetime.utcnow()
            )
            
            logger.info(f"✅ Emotional support provided: {emotion_type}")
            
            # Update state with response (state is TypedDict, need to create new dict)
            updated_state = state.copy()
            updated_state["response"] = response
            return updated_state
        
        except Exception as e:
            logger.error(f"❌ Error in emotional support: {e}", exc_info=True)
            
            # Fallback response (safety net)
            updated_state = state.copy()
            updated_state["response"] = (
                "I hear that you're going through something difficult. "
                "While I want to help, this is a moment where talking to a real person "
                "might be more valuable.\n\n"
                "Consider:\n"
                "• Texting a friend\n"
                "• Calling someone you trust\n"
                "• If urgent: Crisis hotline (988 in US)\n\n"
                "Your constitution reminds you: difficult moments pass, "
                "your long-term goals remain."
            )
            return updated_state
    
    async def _classify_emotion(self, message: str) -> str:
        """
        Classify user's emotion from their message.
        
        <b>How This Works:</b>
        Uses Gemini to analyze the user's message and determine which emotion
        category it falls into. This is a lightweight classification task.
        
        <b>Why AI Classification?</b>
        - Emotions are nuanced (not simple keyword matching)
        - "I miss her" could be loneliness OR breakup thoughts
        - "Feeling urges" could be porn urges OR general stress
        - AI understands context better than rules
        
        <b>Cost:</b>
        - Input: ~50 tokens
        - Output: 1 token (just the emotion word)
        - Cost: $0.000013 per classification
        
        Args:
            message: User's message expressing emotion
            
        Returns:
            Emotion type: "loneliness" | "porn_urge" | "breakup" | "stress" | "general"
            
        Example:
            >>> await _classify_emotion("I'm feeling really lonely tonight")
            "loneliness"
            
            >>> await _classify_emotion("Having strong urges right now")
            "porn_urge"
        """
        prompt = f"""Classify the emotion in this message into ONE category:

Message: "{message}"

Categories:
- loneliness: Feeling alone, isolated, wanting companionship, missing social connection
- porn_urge: Sexual urges, temptation to view porn, struggling with urges
- breakup: Missing ex, thinking about getting back together, breakup sadness
- stress: General stress, anxiety, overwhelm, work pressure, feeling overwhelmed
- general: Other emotions not fitting above (sadness, frustration, anger, etc.)

Respond with ONLY the category word (lowercase, no punctuation).
"""
        
        response = await self.llm.generate_text(
            prompt=prompt,
            max_output_tokens=75,  # Increased 1.5x from 50 (gemini-2.5 with thinking disabled)
            temperature=0.3  # Low temperature for classification (deterministic)
        )
        
        emotion = response.strip().lower()
        
        # Validate response
        valid_emotions = ["loneliness", "porn_urge", "breakup", "stress", "general"]
        if emotion not in valid_emotions:
            logger.warning(f"Invalid emotion classification: '{emotion}', defaulting to 'general'")
            emotion = "general"
        
        return emotion
    
    def _get_emotional_protocol(self, emotion_type: str) -> dict:
        """
        Get emotional support protocol from constitution.
        
        <b>What Are Protocols?</b>
        Pre-defined frameworks for each emotion type that tell the AI how to respond.
        Think of them as "response templates" with specific guidance.
        
        <b>Why Pre-Defined Protocols?</b>
        - Consistency: Same emotion always gets similar structure
        - Safety: No hallucination risk (protocols are vetted)
        - Quality: Protocols written with CBT principles
        - Cost: Smaller prompts (protocols define structure)
        
        <b>Protocol Structure:</b>
        Each protocol has 4 components:
        1. validate: How to acknowledge the emotion
        2. reframe: How to connect to constitution
        3. trigger: What question to ask
        4. actions: What concrete steps to suggest
        
        Args:
            emotion_type: Type of emotion (loneliness, porn_urge, etc.)
            
        Returns:
            Dictionary with protocol keys: validate, reframe, trigger, actions
            
        Example:
            >>> protocol = _get_emotional_protocol("loneliness")
            >>> protocol["validate"]
            "Loneliness is real and temporary. Your intentional celibacy phase..."
        """
        protocols = {
            "loneliness": {
                "validate": "Loneliness is real and temporary. Your intentional celibacy phase is by design, not default.",
                "reframe": "You're building the foundation for the life partner you deserve. This is strategic isolation, not abandonment.",
                "trigger": "What specifically triggered this feeling right now? Time of day? Something you saw?",
                "actions": [
                    "Text one friend: 'Hey, what's up?' (Don't isolate further)",
                    "Go to gym or cafe (public place, no isolating)",
                    "If you can't leave: 20 pushups or cold shower"
                ]
            },
            "porn_urge": {
                "validate": "The urge is normal. Acknowledging it is strength, not weakness.",
                "reframe": "Porn is the enemy. One relapse = 7-day reset minimum. Your streak is worth more than 10 minutes of dopamine.",
                "trigger": "What triggered this? Boredom? Loneliness? Stress? Late-night scrolling?",
                "actions": [
                    "Cold shower RIGHT NOW (interrupt pattern)",
                    "Text accountability partner: 'Having urges, need support'",
                    "Leave room, go to public place immediately"
                ]
            },
            "breakup": {
                "validate": "Missing her is natural. The relationship mattered. Your feelings are valid.",
                "reframe": "Feb 2025: 6-month spiral after reaching out. Your constitution says relationships disrupting sleep/training are violations.",
                "trigger": "What triggered this thought? Saw something? Feeling lonely? Specific memory?",
                "actions": [
                    "Review journal from Feb-Aug 2025 (reality check)",
                    "Text a friend about how you're feeling (not her)",
                    "Gym session or 30-minute walk"
                ]
            },
            "stress": {
                "validate": "Stress is your body's response to demands. It's a signal, not weakness.",
                "reframe": "Your constitution handles stress through systems, not emotion. Career stress? LeetCode. Physical stress? Training. Mental stress? Deep work.",
                "trigger": "What specifically is causing this stress? Is it actionable? What's the next smallest step?",
                "actions": [
                    "Brain dump: Write down every stressor",
                    "Identify ONE action for next 15 minutes",
                    "Execute that action, then reassess"
                ]
            },
            "general": {
                "validate": "Whatever you're feeling is valid. Emotions are data, not directives.",
                "reframe": "Your constitution gives framework when emotions are loud. Return to principles: Physical sovereignty, Create don't consume, Evidence over emotion.",
                "trigger": "What's the feeling? What triggered it? What does it want you to do?",
                "actions": [
                    "Physical reset: Cold shower or 10-min walk",
                    "Write it out: Journal for 5 minutes",
                    "Constitution check: Which principle applies?"
                ]
            }
        }
        
        return protocols.get(emotion_type, protocols["general"])
    
    async def _generate_emotional_response(
        self,
        emotion_type: str,
        user_message: str,
        protocol: dict,
        user
    ) -> str:
        """
        Generate personalized emotional support response using Gemini.
        
        <b>Prompt Engineering for Emotional Support:</b>
        
        The prompt must:
        1. Provide the protocol (structure)
        2. Provide user context (personalization)
        3. Demand specific structure (4-step format)
        4. Set appropriate tone (coach, not therapist)
        
        <b>Why Gemini for Generation?</b>
        - Personalization: Can reference user's streak, mode, partner
        - Natural language: Flows better than templates
        - Adaptation: Can adjust tone based on severity
        - Quality: Better than rule-based generation
        
        <b>Cost:</b>
        - Input: ~400 tokens (protocol + context + instructions)
        - Output: ~200 tokens (response)
        - Cost: $0.000075 per response
        
        Args:
            emotion_type: Classified emotion
            user_message: User's original message
            protocol: Constitution protocol for this emotion
            user: User object for personalization
            
        Returns:
            Emotional support response string (200-300 words)
            
        Example Output:
            "I hear you. Loneliness is real and temporary. Your intentional celibacy
             phase is by design, not default. You're building the foundation for the
             life partner you deserve. This is strategic isolation, not abandonment.
             
             What specifically triggered this feeling right now?
             
             Here's what you need to do RIGHT NOW:
             1. Text one friend: 'Hey, what's up?'
             2. Go to gym or cafe (public place)
             3. If you can't leave: 20 pushups
             
             Your 47-day streak proves you can handle difficult moments."
        """
        # Build context for personalization
        context_parts = []
        
        if user and hasattr(user, 'streaks'):
            if user.streaks.current_streak > 0:
                context_parts.append(f"Current streak: {user.streaks.current_streak} days")
        
        if user and hasattr(user, 'constitution_mode'):
            if user.constitution_mode:
                context_parts.append(f"Mode: {user.constitution_mode}")
        
        if user and hasattr(user, 'accountability_partner_name'):
            if user.accountability_partner_name:
                context_parts.append(f"Has accountability partner: {user.accountability_partner_name}")
        
        context = ". ".join(context_parts) if context_parts else "No additional context"
        
        prompt = f"""You are Ayush's constitution AI agent providing emotional support.

User emotion: {emotion_type}
User message: "{user_message}"
User context: {context}

Constitution protocol for {emotion_type}:
VALIDATE: {protocol.get('validate', 'N/A')}
REFRAME: {protocol.get('reframe', 'N/A')}
TRIGGER: {protocol.get('trigger', 'N/A')}
ACTIONS: {', '.join(protocol.get('actions', []))}

Generate a response using this EXACT structure:

1. VALIDATE (2 sentences): Acknowledge the emotion using the protocol's validation text. Personalize slightly but keep the core message.

2. REFRAME (2 sentences): Reframe using constitution principles from the protocol. Connect to their current situation.

3. TRIGGER (1 question): Ask what specifically triggered this feeling right now. Use protocol's trigger question.

4. ACTION (3 specific steps): List 3 immediate concrete actions from the protocol. Number them clearly.

Requirements:
- Tone: Firm but compassionate. Like a coach, not a therapist.
- Length: 200-300 words total
- Structure: Must follow 4-step protocol exactly
- Personalization: Reference their streak/mode if relevant
- Direct: No fluff, no platitudes
- Action-oriented: End with clear next steps

Generate the response now:
"""
        
        response = await self.llm.generate_text(
            prompt=prompt,
            max_output_tokens=1200,  # Increased 1.5x from 800 (gemini-2.5 with thinking disabled)
            temperature=0.7  # Slightly creative for natural language
        )
        
        return response.strip()


# Global instance
_emotional_agent_instance: Optional[EmotionalSupportAgent] = None


def get_emotional_agent() -> EmotionalSupportAgent:
    """
    Get or create Emotional Support agent instance (singleton).
    
    Returns:
        EmotionalSupportAgent instance
    """
    global _emotional_agent_instance
    
    if _emotional_agent_instance is None:
        logger.info("Creating new EmotionalSupportAgent instance (singleton)")
        _emotional_agent_instance = EmotionalSupportAgent()
    else:
        logger.debug("Returning existing EmotionalSupportAgent instance")
    
    return _emotional_agent_instance


def reset_emotional_agent():
    """Reset Emotional agent instance (for testing)"""
    global _emotional_agent_instance
    _emotional_agent_instance = None
    logger.info("Emotional agent instance reset")
