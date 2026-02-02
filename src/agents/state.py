"""
LangGraph State Schema

This module defines the state structure for our multi-agent workflow.

What is State in LangGraph?
-----------------------------
State is a dictionary that flows through the agent workflow. Each agent can:
1. **Read** any field in the state
2. **Update** specific fields
3. **Pass** the state to the next agent

Think of it like a shared context object that gets passed around:
- User message comes in → State created with user_id, message
- Supervisor adds intent → State updated with intent field
- CheckIn agent adds response → State updated with response field
- Final response sent → State contains full conversation context

Key Concepts:
-------------
1. **TypedDict**: Python type annotation for dictionary structures
   - Required by LangGraph for type checking
   - Defines which fields exist and their types
   
2. **Annotated**: Adds metadata to types
   - Used to specify HOW fields should be updated
   - Example: Annotated[list, add] means "append new items to list"
   
3. **Reducer Functions** (from operator module):
   - `add`: Appends/merges values (for lists and dicts)
   - Default: Replaces old value with new value
   
4. **Optional Fields**: Fields that may or may not be populated
   - Not every agent sets every field
   - Example: intent is None until Supervisor classifies it

Example State Flow:
-------------------
1. Initial state (from webhook):
   {
       "user_id": "123456789",
       "message": "I want to check in",
       "message_id": 456,
       "timestamp": datetime.now()
   }

2. After Supervisor:
   {
       ...previous fields,
       "intent": "checkin",
       "intent_confidence": 0.95
   }

3. After CheckIn Agent:
   {
       ...previous fields,
       "checkin_answers": {"tier1": "All complete", "sleep": 8, ...},
       "compliance_score": 100,
       "streak": 47,
       "response": "Excellent work! 100% compliance today...",
       "next_action": "send_message"
   }
"""

from typing import TypedDict, Annotated, Optional, List, Dict, Any
from operator import add
from datetime import datetime


class ConstitutionState(TypedDict):
    """
    State object passed through LangGraph workflow
    
    This represents ALL the data available to any agent in the graph.
    Each agent can read any field and update specific fields.
    
    Field Categories:
    -----------------
    1. User Context: Who is the user?
    2. Message Data: What did they send?
    3. Intent Classification: What do they want?
    4. Check-in Data: Check-in conversation state
    5. Pattern Detection: Detected violations
    6. Response: What to send back
    7. Error Handling: Track failures
    """
    
    # --- User Context ---
    user_id: str
    """Telegram user ID (e.g., "123456789")"""
    
    username: Optional[str]
    """Telegram username (e.g., "@ayush", may be None if user hasn't set one)"""
    
    # --- Message Data ---
    message: str
    """User's message text (e.g., "I want to check in")"""
    
    message_id: int
    """Telegram message ID (used for replying to specific message)"""
    
    timestamp: datetime
    """When the message was received (UTC)"""
    
    # --- Intent Classification ---
    intent: Optional[str]
    """
    Classified intent (one of: checkin, emotional, query, command)
    
    - checkin: User wants to do daily check-in
    - emotional: User expressing difficult emotions
    - query: Questions about stats/constitution
    - command: Bot commands (/status, /help)
    
    Set by: Supervisor Agent
    Used by: Routing logic to determine which agent runs next
    """
    
    intent_confidence: Optional[float]
    """
    Confidence score for intent classification (0.0-1.0)
    Note: Gemini doesn't return confidence, so this is a placeholder
    """
    
    # --- Check-in Conversation State ---
    checkin_step: Optional[int]
    """
    Which question we're on in the check-in flow (1, 2, 3, or 4)
    
    Questions:
    1. Tier 1 non-negotiables (yes/no for each)
    2. Sleep hours (number)
    3. Training done? (yes/no)
    4. Deep work hours (number)
    """
    
    checkin_answers: Annotated[Dict[str, Any], add]
    """
    Answers collected so far in check-in
    
    Example:
    {
        "tier1": "All complete",
        "sleep": 8,
        "training": "Yes",
        "deep_work": 3
    }
    
    Note: Annotated[dict, add] means new answers are MERGED (not replaced)
    """
    
    compliance_score: Optional[int]
    """
    Calculated compliance score (0-100)
    
    Calculation:
    - Tier 1 items: 20% each (5 items = 100%)
    - Sleep 7+ hours: Bonus points
    - Training: Bonus points
    - Deep work 2+ hours: Bonus points
    
    Set by: CheckIn Agent after all 4 questions answered
    """
    
    streak: Optional[int]
    """Current check-in streak (consecutive days)"""
    
    # --- Pattern Detection ---
    detected_patterns: Annotated[List[Dict[str, Any]], add]
    """
    List of patterns detected by Pattern Detection Agent
    
    Example:
    [
        {
            "type": "sleep_degradation",
            "severity": "high",
            "data": {"avg_sleep": 5.3, "consecutive_days": 3}
        }
    ]
    
    Note: Annotated[list, add] means new patterns are APPENDED (not replaced)
    """
    
    # --- Response Generation ---
    response: Optional[str]
    """
    Final response text to send to user
    
    Set by: CheckIn Agent, Emotional Agent, Query Handler, etc.
    Used by: Telegram bot to send message
    """
    
    next_action: Optional[str]
    """
    What to do after processing (e.g., "send_message", "ask_next_question", "wait_for_input")
    
    Used by: Workflow coordinator to determine next step
    """
    
    # --- Error Handling ---
    error: Optional[str]
    """
    Error message if something failed
    
    If this field is set, the workflow should:
    1. Log the error
    2. Send a fallback message to user
    3. Abort the current flow gracefully
    """


# --- Helper Functions for State Management ---

def create_initial_state(
    user_id: str,
    message: str,
    message_id: int,
    username: Optional[str] = None
) -> ConstitutionState:
    """
    Create initial state from incoming webhook message
    
    This is called when a new message arrives from Telegram.
    It creates the base state that will be passed to the Supervisor.
    
    Args:
        user_id: Telegram user ID
        message: Message text
        message_id: Telegram message ID
        username: Optional Telegram username
        
    Returns:
        Initial ConstitutionState
    """
    return ConstitutionState(
        user_id=user_id,
        username=username,
        message=message,
        message_id=message_id,
        timestamp=datetime.utcnow(),
        intent=None,
        intent_confidence=None,
        checkin_step=None,
        checkin_answers={},
        compliance_score=None,
        streak=None,
        detected_patterns=[],
        response=None,
        next_action=None,
        error=None
    )


def is_state_valid(state: ConstitutionState) -> bool:
    """
    Validate that state has required fields
    
    Used to catch bugs where agents forget to set critical fields.
    
    Args:
        state: State to validate
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ["user_id", "message", "message_id", "timestamp"]
    
    for field in required_fields:
        if field not in state or state[field] is None:
            return False
    
    return True


def merge_state(base: ConstitutionState, updates: dict) -> ConstitutionState:
    """
    Merge updates into base state
    
    Theory - State Updates in LangGraph:
    ------------------------------------
    When an agent updates the state, LangGraph needs to know HOW to merge
    the new values with the existing state.
    
    For fields with `Annotated[T, add]`:
    - Lists: Append new items (old + new)
    - Dicts: Merge keys (old.update(new))
    
    For regular fields:
    - Replace old value with new value
    
    Args:
        base: Current state
        updates: Fields to update
        
    Returns:
        Merged state
    """
    merged = base.copy()
    
    for key, value in updates.items():
        if key in merged:
            # Check if field uses `add` reducer
            if key in ["checkin_answers", "detected_patterns"]:
                # Merge for dicts and lists
                if isinstance(merged[key], dict) and isinstance(value, dict):
                    merged[key].update(value)
                elif isinstance(merged[key], list) and isinstance(value, list):
                    merged[key].extend(value)
            else:
                # Replace for regular fields
                merged[key] = value
        else:
            merged[key] = value
    
    return merged
