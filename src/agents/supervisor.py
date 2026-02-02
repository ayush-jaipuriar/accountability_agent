"""
Supervisor Agent - Intent Classification and Routing

This is the FIRST agent that processes every incoming message.
Its job is to understand what the user wants and route to the appropriate sub-agent.

Flow:
-----
1. User message arrives → Supervisor receives it
2. Supervisor calls Gemini to classify intent
3. Intent classification returns one of: checkin, emotional, query, command
4. LangGraph routes message to appropriate sub-agent based on intent

Why We Need This:
-----------------
Without the Supervisor, we'd need hardcoded rules like:
- If message contains "check in" → go to CheckIn agent
- If message contains "lonely" → go to Emotional agent
- etc.

But users don't always use exact keywords! Examples:
- "Let's do this" (means: checkin)
- "I'm struggling today" (means: emotional)
- "How am I doing?" (means: query)

The Supervisor uses Gemini's language understanding to classify these correctly.

Intent Types:
-------------
1. **checkin**: User wants to do daily check-in
   - Examples: "I'm ready to check in", "let's go", "checking in"
   
2. **emotional**: User expressing difficult emotions
   - Examples: "I'm feeling lonely", "had urges today", "struggling"
   
3. **query**: Questions about stats, constitution, bot functionality
   - Examples: "what's my streak?", "show stats", "how does this work?"
   
4. **command**: Bot commands
   - Examples: "/start", "/help", "/status", "/mode"

Key Concepts:
-------------
1. **Zero-shot Classification**: 
   - LLM can classify intents without being trained on labeled examples
   - We just provide a clear prompt with intent descriptions
   - Gemini's pre-training allows it to understand intent from context
   
2. **Temperature = 0.1** (very low):
   - Makes classification deterministic
   - Same input → same output (consistency)
   - Reduces randomness/creativity (we want accuracy, not creativity here)
   
3. **Context Injection**:
   - We pass user's streak and last check-in date to help classification
   - Example: If user says "let's continue" and has a streak going,
     it's likely "checkin" intent

4. **Fallback Strategy**:
   - If Gemini returns invalid intent → default to "query"
   - If API fails → default to "query"
   - "query" is safest because it just answers questions (no state changes)

Cost Analysis:
--------------
- Prompt: ~200 tokens
- Response: 1 token (just the intent word)
- Total: ~201 tokens per classification
- Cost: (201 / 1,000,000) × $0.25 = $0.00005 per classification
- Daily: 3 messages × $0.00005 = $0.00015/day (~$0.0045/month)
"""

from src.agents.state import ConstitutionState
from src.services.llm_service import get_llm_service
from src.services.firestore_service import firestore_service
from src.config import settings
import logging
from typing import Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SupervisorAgent:
    """
    Intent classification and routing agent
    
    Workflow:
    1. Receive user message (in state)
    2. Load user context (streak, last check-in)
    3. Call Gemini to classify intent
    4. Update state with intent
    5. Return state (LangGraph routes based on intent field)
    """
    
    def __init__(self, project_id: str):
        """
        Initialize Supervisor Agent
        
        Args:
            project_id: GCP project ID (for LLM service)
        """
        self.llm = get_llm_service(
            project_id=project_id,
            location=settings.vertex_ai_location,
            model_name=settings.gemini_model
        )
        logger.info("Supervisor Agent initialized")
    
    async def classify_intent(self, state: ConstitutionState) -> ConstitutionState:
        """
        Classify user message intent
        
        This is the main entry point for the Supervisor.
        It takes the current state, classifies the intent, and returns updated state.
        
        Args:
            state: Current conversation state
            
        Returns:
            Updated state with 'intent' field populated
            
        Theory - Why async?
        -------------------
        This method is async because:
        1. LLM calls involve network I/O (calling Vertex AI API)
        2. Async allows other requests to be processed while waiting for API
        3. FastAPI is async-native, so this integrates cleanly
        
        In practice:
        - User A sends message → await classify_intent (waiting for API)
        - While waiting, User B sends message → can start processing immediately
        - User A's API returns → continue processing User A
        """
        user_id = state["user_id"]
        message = state["message"]
        
        logger.info(f"Classifying intent for user {user_id}: '{message[:50]}...'")
        
        # Get user context to help classification
        user_context = self._get_user_context(user_id)
        
        # Build classification prompt
        prompt = self._build_intent_prompt(
            message=message,
            user_context=user_context
        )
        
        # Call Gemini for intent classification
        try:
            intent_response = await self.llm.generate_text(
                prompt=prompt,
                max_output_tokens=2048,  # Use higher limit for gemini-2.5
                temperature=0.1  # Low temperature = deterministic
            )
            
            # Extract and validate intent
            intent = self._parse_intent(intent_response)
            
            logger.info(f"Intent classified: {intent} for message: '{message[:50]}...'")
            
            # Update state
            state["intent"] = intent
            state["intent_confidence"] = 0.9  # Placeholder (Gemini doesn't return confidence)
            
            return state
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}", exc_info=True)
            # Fallback to 'query' intent (safest)
            state["intent"] = "query"
            state["error"] = f"Intent classification error: {str(e)}"
            return state
    
    def _get_user_context(self, user_id: str) -> dict:
        """
        Get user context to help with intent classification
        
        Context helps the LLM make better decisions. For example:
        - User with 0-day streak saying "let's go" → probably "checkin"
        - User with 47-day streak saying "let's go" → definitely "checkin"
        - User saying "how am I doing?" → needs streak data → "query"
        
        Args:
            user_id: Telegram user ID
            
        Returns:
            Dictionary with user context (streak, last check-in, etc.)
        """
        try:
            user_profile = firestore_service.get_user_profile(user_id)
            
            if user_profile:
                return {
                    "current_streak": user_profile.current_streak,
                    "last_checkin_date": user_profile.last_checkin_date,
                    "longest_streak": user_profile.longest_streak,
                    "constitution_mode": user_profile.constitution_mode
                }
            else:
                # New user (no profile yet)
                return {
                    "current_streak": 0,
                    "last_checkin_date": None,
                    "longest_streak": 0,
                    "constitution_mode": "standard"
                }
        except Exception as e:
            logger.warning(f"Failed to get user context: {e}")
            return {
                "current_streak": 0,
                "last_checkin_date": None,
                "longest_streak": 0,
                "constitution_mode": "standard"
            }
    
    def _build_intent_prompt(self, message: str, user_context: dict) -> str:
        """
        Build the intent classification prompt
        
        Prompt Engineering Principles:
        ------------------------------
        1. **Clear Instructions**: Tell model exactly what to do
        2. **Context**: Provide relevant user information
        3. **Examples**: Show what each intent looks like
        4. **Constraints**: Specify output format (one word only)
        5. **Structure**: Use clear sections and formatting
        
        Why This Works:
        ---------------
        Gemini (and all LLMs) are trained on massive amounts of text, including:
        - Customer support conversations (intent classification)
        - Chatbot interactions (routing)
        - Task classification examples
        
        By structuring our prompt similarly, we tap into this pre-training.
        
        Args:
            message: User's message text
            user_context: User context dictionary
            
        Returns:
            Formatted prompt string
        """
        streak = user_context.get("current_streak", 0)
        last_checkin = user_context.get("last_checkin_date")
        
        # Format last check-in date for readability
        if last_checkin:
            if isinstance(last_checkin, str):
                last_checkin_str = last_checkin
            else:
                last_checkin_str = last_checkin.strftime("%Y-%m-%d")
        else:
            last_checkin_str = "Never"
        
        prompt = f"""Classify the user's intent from this message.

MESSAGE: "{message}"

USER CONTEXT:
- Current streak: {streak} days
- Last check-in: {last_checkin_str}

INTENT OPTIONS:

1. **checkin** - User wants to start/continue their daily check-in
   Examples:
   - "I'm ready to check in"
   - "Let's do this"
   - "Checking in for today"
   - "Let's go"
   - "Ready"

2. **emotional** - User is expressing difficult emotions or seeking support
   Examples:
   - "I'm feeling lonely today"
   - "Having urges to watch porn"
   - "Feeling anxious"
   - "I'm struggling"
   - "Need help"

3. **query** - User is asking questions about their stats, constitution, or how the bot works
   Examples:
   - "What's my streak?"
   - "Show my stats"
   - "What are the constitution rules?"
   - "How does this work?"
   - "/status"

4. **command** - User is issuing a bot command
   Examples:
   - "/start"
   - "/help"
   - "/mode"
   - "/export"

INSTRUCTIONS:
Respond with EXACTLY ONE WORD: checkin, emotional, query, or command

No explanation, no punctuation, just the intent word in lowercase.

Intent:"""

        return prompt
    
    def _parse_intent(self, intent_response: str) -> str:
        """
        Parse and validate intent from LLM response
        
        Why We Need This:
        -----------------
        LLMs can sometimes return:
        - Extra whitespace: "  checkin  "
        - Capitalization: "Checkin" or "CHECKIN"
        - Explanation: "The intent is checkin because..."
        - Invalid intent: "check-in" or "unknown"
        
        This function handles all these cases and ensures we get a valid intent.
        
        Args:
            intent_response: Raw LLM response
            
        Returns:
            Validated intent (one of: checkin, emotional, query, command)
        """
        # Clean up response
        intent = intent_response.strip().lower()
        
        # Extract first word if LLM provided explanation
        if " " in intent:
            intent = intent.split()[0]
        
        # Remove punctuation
        intent = intent.rstrip('.,!?;:')
        
        # Validate against allowed intents
        valid_intents = ["checkin", "emotional", "query", "command"]
        
        if intent in valid_intents:
            return intent
        
        # Handle common variations
        intent_mapping = {
            "check-in": "checkin",
            "check_in": "checkin",
            "emotion": "emotional",
            "emotions": "emotional",
            "question": "query",
            "cmd": "command",
            "commands": "command"
        }
        
        if intent in intent_mapping:
            mapped_intent = intent_mapping[intent]
            logger.warning(f"Mapped non-standard intent '{intent}' to '{mapped_intent}'")
            return mapped_intent
        
        # Default to 'query' if intent is unrecognized
        logger.warning(f"Unrecognized intent '{intent}', defaulting to 'query'")
        return "query"


# --- Global Instance Management (Singleton Pattern) ---

_supervisor_agent_instance: Optional[SupervisorAgent] = None


def get_supervisor_agent(project_id: str) -> SupervisorAgent:
    """
    Get or create supervisor agent instance (singleton)
    
    Args:
        project_id: GCP project ID
        
    Returns:
        SupervisorAgent instance
    """
    global _supervisor_agent_instance
    
    if _supervisor_agent_instance is None:
        logger.info("Creating new SupervisorAgent instance (singleton)")
        _supervisor_agent_instance = SupervisorAgent(project_id)
    else:
        logger.debug("Returning existing SupervisorAgent instance")
    
    return _supervisor_agent_instance


def reset_supervisor_agent():
    """
    Reset supervisor agent instance (useful for testing)
    """
    global _supervisor_agent_instance
    _supervisor_agent_instance = None
    logger.info("Supervisor agent instance reset")
