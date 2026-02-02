# Phase 2 Implementation Plan - LangGraph Multi-Agent System

## 🎯 Overview

This document provides the **step-by-step implementation guide** for Phase 2, building on top of the completed Phase 1 MVP. Phase 2 transforms the bot from a simple check-in system into an intelligent AI-powered accountability agent.

**What we're adding:**
1. **LangGraph Supervisor** - Routes messages to specialized agents based on intent
2. **AI-Powered Feedback** - Replaces hardcoded responses with personalized Gemini-generated feedback
3. **Pattern Detection** - Automatically identifies constitution violations
4. **Intervention System** - Proactively sends warnings when patterns are detected
5. **Scheduled Scanning** - Runs pattern detection every 6 hours

**Architecture Evolution:**
```
Phase 1: User → Webhook → Hardcoded Handler → Firestore → Hardcoded Response
Phase 2: User → Webhook → Supervisor Agent → Sub-Agents → Gemini AI → Personalized Response
                              ↓
                      Pattern Detection Agent (scheduled)
                              ↓
                      Intervention Agent → Gemini AI → Warning Messages
```

---

## 📁 New Files We'll Create

```
accountability_agent/
├── src/
│   ├── agents/                     # NEW - LangGraph agents
│   │   ├── __init__.py
│   │   ├── state.py                # LangGraph state schema
│   │   ├── supervisor.py           # Intent classification & routing
│   │   ├── checkin_agent.py        # Check-in with AI feedback
│   │   ├── pattern_detection.py    # Pattern detection rules
│   │   └── intervention.py         # Intervention generation
│   │
│   ├── services/
│   │   ├── llm_service.py          # NEW - Vertex AI/Gemini wrapper
│   │   └── (existing files...)
│   │
│   └── prompts/                    # NEW - LLM prompt templates
│       ├── __init__.py
│       ├── intent_classification.py
│       ├── checkin_feedback.py
│       └── intervention_prompts.py
│
├── tests/
│   ├── test_pattern_detection.py   # NEW - Pattern detection tests
│   ├── test_intervention.py        # NEW - Intervention tests
│   └── integration/                # NEW - Integration tests
│       └── test_phase2_flow.py
│
├── requirements.txt                # UPDATED - Add langgraph, langchain
└── PHASE2_IMPLEMENTATION.md        # This file
```

---

## 🧩 Component Deep Dive

### Component 1: LLM Service (`src/services/llm_service.py`)

**Purpose:** Wrapper around Google's Vertex AI to call Gemini 2.0 Flash for text generation.

**Why Gemini 2.0 Flash:**
- **Cost-effective:** $0.25 per 1M input tokens, $0.50 per 1M output tokens
- **Fast:** <2 second response times
- **Smart enough:** Can handle intent classification, feedback generation, pattern analysis

**Key Concepts:**
- **Vertex AI:** Google Cloud's unified AI platform (equivalent to OpenAI API but for Google models)
- **GenerativeModel:** The Python client for calling Gemini models
- **Token Counting:** Track usage to stay under budget

**Implementation:**
```python
from google.cloud import aiplatform
from vertexai.generative_models import GenerativeModel
import logging

logger = logging.getLogger(__name__)

class LLMService:
    """Wrapper for Vertex AI Gemini API calls"""
    
    def __init__(self, project_id: str, location: str = "asia-south1"):
        """
        Initialize Vertex AI client
        
        Args:
            project_id: GCP project ID (accountability-agent)
            location: GCP region (asia-south1 for Mumbai)
        """
        aiplatform.init(project=project_id, location=location)
        self.model = GenerativeModel("gemini-2.0-flash-exp")
        
    async def generate_text(
        self,
        prompt: str,
        max_output_tokens: int = 200,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text using Gemini
        
        Args:
            prompt: The prompt to send to the model
            max_output_tokens: Maximum response length
            temperature: Creativity (0.0 = deterministic, 1.0 = creative)
            
        Returns:
            Generated text response
        """
        try:
            # Count input tokens for cost tracking
            input_tokens = self._count_tokens(prompt)
            logger.info(f"LLM request - Input tokens: {input_tokens}")
            
            # Generate response
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "max_output_tokens": max_output_tokens,
                    "temperature": temperature,
                }
            )
            
            output_text = response.text
            output_tokens = self._count_tokens(output_text)
            
            # Calculate cost (Gemini 2.0 Flash pricing)
            input_cost = (input_tokens / 1_000_000) * 0.25
            output_cost = (output_tokens / 1_000_000) * 0.50
            total_cost = input_cost + output_cost
            
            logger.info(f"LLM response - Output tokens: {output_tokens}, Cost: ${total_cost:.6f}")
            
            return output_text
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            raise
    
    def _count_tokens(self, text: str) -> int:
        """Estimate token count (rough approximation: 1 token ≈ 4 characters)"""
        return len(text) // 4

# Global instance
llm_service = None

def get_llm_service(project_id: str) -> LLMService:
    """Get or create LLM service instance (singleton pattern)"""
    global llm_service
    if llm_service is None:
        llm_service = LLMService(project_id)
    return llm_service
```

**Why This Design:**
- **Singleton Pattern:** Only one LLM service instance across the app (avoids re-initializing Vertex AI)
- **Cost Tracking:** Logs every API call with token count and cost
- **Error Handling:** Gracefully handles API failures
- **Async-Ready:** Returns coroutine for use in async handlers

---

### Component 2: LangGraph State Schema (`src/agents/state.py`)

**Purpose:** Define the data structure that flows through the LangGraph workflow.

**What is LangGraph:**
LangGraph is a framework for building **stateful, multi-agent workflows** using LLMs. Think of it as a state machine where:
- **State:** Data that gets passed between agents (user message, context, current intent)
- **Nodes:** Agents that process the state (Supervisor, CheckIn, Intervention)
- **Edges:** Routing logic that determines which agent runs next

**Key Concepts:**
- **TypedDict:** Python type annotation for dictionary structures (used by LangGraph)
- **Annotated:** Adds metadata to types (LangGraph uses this for state merging)
- **Reducer:** Function that determines how state updates are combined

**Implementation:**
```python
from typing import TypedDict, Annotated, Optional, List
from operator import add
from datetime import datetime

class ConstitutionState(TypedDict):
    """
    State object passed through LangGraph workflow
    
    This represents ALL the data available to any agent in the graph.
    Each agent can read any field and update specific fields.
    """
    
    # User context
    user_id: str                           # Telegram user ID
    username: Optional[str]                 # Telegram username
    
    # Message data
    message: str                            # User's message text
    message_id: int                         # Telegram message ID
    timestamp: datetime                     # When message was received
    
    # Intent classification
    intent: Optional[str]                   # classified intent (checkin, emotional, query, command)
    intent_confidence: Optional[float]      # Confidence score (0.0-1.0)
    
    # Check-in specific data
    checkin_step: Optional[int]             # Which question we're on (1-4)
    checkin_answers: Annotated[dict, add]   # Answers collected so far
    compliance_score: Optional[int]         # Calculated score (0-100)
    streak: Optional[int]                   # Current streak
    
    # Pattern detection
    detected_patterns: Annotated[List[dict], add]  # Patterns found
    
    # Response generation
    response: Optional[str]                 # Final response to send to user
    next_action: Optional[str]              # What to do next (send_message, ask_next_question, etc.)
    
    # Error handling
    error: Optional[str]                    # Error message if something failed
```

**Why This Structure:**
- **User Context:** Every agent knows who the user is
- **Intent Field:** Supervisor classifies intent, other agents use it
- **Annotated with `add`:** For lists/dicts, new values are appended (not replaced)
- **Optional Fields:** Not all fields are populated in every workflow
- **next_action:** Tells the workflow what to do after processing (continue conversation vs send message)

---

### Component 3: Supervisor Agent (`src/agents/supervisor.py`)

**Purpose:** First agent in the workflow. Classifies user intent and routes to the appropriate sub-agent.

**Intent Classification Logic:**
```
User: "I'm checking in"           → Intent: checkin
User: "I'm feeling lonely today"  → Intent: emotional
User: "What's my streak?"         → Intent: query
User: "/status"                   → Intent: command
```

**Key Concepts:**
- **Zero-shot Classification:** LLM classifies intent without training data (just examples in prompt)
- **Routing:** Based on intent, we call different agents
- **Context Injection:** Pass user's streak, last check-in date to help classification

**Implementation:**
```python
from src.agents.state import ConstitutionState
from src.services.llm_service import get_llm_service
from src.services.firestore_service import firestore_service
import logging

logger = logging.getLogger(__name__)

class SupervisorAgent:
    """
    Intent classification and routing agent
    
    Workflow:
    1. Receive user message
    2. Load user context (streak, last check-in)
    3. Call Gemini to classify intent
    4. Update state with intent
    5. Return state (LangGraph routes based on intent field)
    """
    
    def __init__(self, project_id: str):
        self.llm = get_llm_service(project_id)
    
    async def classify_intent(self, state: ConstitutionState) -> ConstitutionState:
        """
        Classify user message intent
        
        Returns updated state with 'intent' field populated
        """
        user_id = state["user_id"]
        message = state["message"]
        
        # Get user context
        user_profile = firestore_service.get_user_profile(user_id)
        if user_profile:
            streak = user_profile.current_streak
            last_checkin = user_profile.last_checkin_date
        else:
            streak = 0
            last_checkin = None
        
        # Build prompt
        prompt = self._build_intent_prompt(
            message=message,
            streak=streak,
            last_checkin=last_checkin
        )
        
        # Call Gemini
        try:
            intent_response = await self.llm.generate_text(
                prompt=prompt,
                max_output_tokens=10,  # Just one word response
                temperature=0.1  # Low temperature = more deterministic
            )
            
            intent = intent_response.strip().lower()
            
            # Validate intent
            valid_intents = ["checkin", "emotional", "query", "command"]
            if intent not in valid_intents:
                logger.warning(f"Invalid intent '{intent}', defaulting to 'query'")
                intent = "query"
            
            logger.info(f"Classified intent: {intent} for message: '{message[:50]}...'")
            
            # Update state
            state["intent"] = intent
            state["intent_confidence"] = 0.9  # Placeholder (Gemini doesn't return confidence)
            
            return state
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            state["intent"] = "query"  # Safe fallback
            state["error"] = str(e)
            return state
    
    def _build_intent_prompt(
        self,
        message: str,
        streak: int,
        last_checkin: Optional[str]
    ) -> str:
        """Build the intent classification prompt"""
        return f"""Classify the user's intent from this message:

Message: "{message}"

User Context:
- Current streak: {streak} days
- Last check-in: {last_checkin or "Never"}

Intent Options:
1. **checkin** - User wants to start/continue daily check-in
   Examples: "let's check in", "I'm ready", "checking in", "start check-in"

2. **emotional** - User expressing difficult emotions
   Examples: "I'm feeling lonely", "I had urges today", "feeling anxious", "struggling"

3. **query** - Questions about stats, constitution, how bot works
   Examples: "what's my streak?", "show my stats", "what are the rules?", "/status"

4. **command** - Bot commands
   Examples: "/start", "/help", "/mode", "/export"

Respond with ONLY ONE WORD: checkin, emotional, query, or command"""

# Global instance
supervisor_agent = None

def get_supervisor_agent(project_id: str) -> SupervisorAgent:
    """Get or create supervisor agent (singleton)"""
    global supervisor_agent
    if supervisor_agent is None:
        supervisor_agent = SupervisorAgent(project_id)
    return supervisor_agent
```

**Why This Design:**
- **Context-Aware:** Knows user's streak and last check-in to make better classifications
- **Low Token Count:** Prompt is ~200 tokens, response is 1 token = ~$0.000025 per classification
- **Error Handling:** Falls back to "query" intent if classification fails
- **Deterministic:** Low temperature (0.1) ensures consistent classifications

---

### Component 4: CheckIn Agent with AI Feedback (`src/agents/checkin_agent.py`)

**Purpose:** Handles check-in conversation flow and generates personalized AI feedback.

**What Changes from Phase 1:**
- **Phase 1:** Hardcoded response: "Check-in complete! Score: 80%"
- **Phase 2:** AI-generated feedback referencing user's streak, patterns, constitution

**Implementation:**
```python
from src.agents.state import ConstitutionState
from src.services.llm_service import get_llm_service
from src.services.firestore_service import firestore_service
from src.services.constitution_service import get_constitution_service
from src.utils.compliance import calculate_compliance
import logging

logger = logging.getLogger(__name__)

class CheckInAgent:
    """
    Check-in conversation handler with AI-generated feedback
    """
    
    def __init__(self, project_id: str):
        self.llm = get_llm_service(project_id)
        self.constitution = get_constitution_service()
    
    async def generate_feedback(self, state: ConstitutionState) -> ConstitutionState:
        """
        Generate personalized check-in feedback using Gemini
        
        Called after all 4 check-in questions are answered
        """
        user_id = state["user_id"]
        answers = state["checkin_answers"]
        
        # Calculate compliance score
        compliance_score = calculate_compliance(answers)
        
        # Get user profile
        user_profile = firestore_service.get_user_profile(user_id)
        current_streak = user_profile.current_streak if user_profile else 0
        longest_streak = user_profile.longest_streak if user_profile else 0
        
        # Get recent check-ins for pattern analysis
        recent_checkins = firestore_service.get_recent_checkins(user_id, days=7)
        
        # Build feedback prompt
        prompt = self._build_feedback_prompt(
            answers=answers,
            compliance_score=compliance_score,
            current_streak=current_streak,
            longest_streak=longest_streak,
            recent_checkins=recent_checkins
        )
        
        # Generate feedback
        try:
            feedback = await self.llm.generate_text(
                prompt=prompt,
                max_output_tokens=250,
                temperature=0.7  # Moderate creativity
            )
            
            # Update state
            state["compliance_score"] = compliance_score
            state["streak"] = current_streak
            state["response"] = feedback
            state["next_action"] = "send_message"
            
            logger.info(f"Generated feedback for user {user_id}: {compliance_score}% compliance")
            
            return state
            
        except Exception as e:
            logger.error(f"Feedback generation failed: {e}")
            # Fallback to Phase 1 hardcoded response
            fallback_msg = f"Check-in complete! ✅\n\nCompliance Score: {compliance_score}%\nStreak: {current_streak} days"
            state["response"] = fallback_msg
            state["error"] = str(e)
            return state
    
    def _build_feedback_prompt(
        self,
        answers: dict,
        compliance_score: int,
        current_streak: int,
        longest_streak: int,
        recent_checkins: list
    ) -> str:
        """Build personalized feedback generation prompt"""
        
        # Extract answers
        tier1_summary = answers.get("tier1", "")
        sleep_hours = answers.get("sleep", 0)
        training = answers.get("training", "No")
        deep_work = answers.get("deep_work", 0)
        
        # Analyze recent trend
        if len(recent_checkins) >= 3:
            recent_scores = [c.compliance_score for c in recent_checkins[-3:]]
            if all(s >= 80 for s in recent_scores):
                trend = "consistent high compliance (3+ days >80%)"
            elif recent_scores[-1] > recent_scores[0]:
                trend = "improving"
            elif recent_scores[-1] < recent_scores[0]:
                trend = "declining"
            else:
                trend = "stable"
        else:
            trend = "new check-in routine"
        
        # Get relevant constitution principles
        constitution_text = self.constitution.get_full_text()
        
        prompt = f"""Generate personalized check-in feedback for this user.

TODAY'S CHECK-IN:
- Tier 1 Non-Negotiables: {tier1_summary}
- Sleep: {sleep_hours} hours
- Training: {training}
- Deep Work: {deep_work} hours
- Compliance Score: {compliance_score}%

USER CONTEXT:
- Current Streak: {current_streak} days
- Longest Streak: {longest_streak} days
- Recent Trend (last 7 days): {trend}

CONSTITUTION PRINCIPLES (reference these):
{constitution_text[:1000]}... (excerpt)

Generate feedback (150-200 words) that:
1. **Acknowledges today's performance** (praise if >80%, constructive if <80%)
2. **References their streak milestone** (especially if reaching 7, 14, 30, 60, 100 days)
3. **Notes the trend** (improving, declining, or consistent)
4. **Connects to constitution principles** (Physical Sovereignty for sleep/training, Create Don't Consume for deep work)
5. **Provides specific guidance for tomorrow** (one actionable focus area)

TONE: Direct, motivating, no fluff. Like a coach who knows the athlete well.
Use emojis sparingly (🔥, ✅, 💪, 🎯 only).
Focus on BEHAVIOR, not feelings.

Feedback:"""

        return prompt

# Global instance
checkin_agent = None

def get_checkin_agent(project_id: str) -> CheckInAgent:
    """Get or create check-in agent (singleton)"""
    global checkin_agent
    if checkin_agent is None:
        checkin_agent = CheckInAgent(project_id)
    return checkin_agent
```

**Why This Design:**
- **Context-Rich Prompts:** Includes today's data + 7-day trend + constitution text
- **Fallback Safety:** If AI fails, falls back to Phase 1 hardcoded message
- **Token Budget:** ~600 input + ~200 output = ~800 tokens per check-in (~$0.002 per check-in)
- **Tone Specification:** Explicit instructions on tone ensure consistent quality

---

### Component 5: Pattern Detection Agent (`src/agents/pattern_detection.py`)

**Purpose:** Analyze check-in history to detect constitution violations.

**Detection Rules:**
1. **Sleep Degradation:** <6 hours for 3+ consecutive nights
2. **Training Abandonment:** 3+ missed training days in a row
3. **Porn Relapse Pattern:** 3+ violations in 7 days
4. **Compliance Decline:** <70% for 3+ consecutive days
5. **Deep Work Collapse:** <1.5 hours for 5+ days

**Key Concepts:**
- **Sliding Window Analysis:** Look at last N days to detect patterns
- **Rule-Based Detection:** No ML needed - simple threshold checks
- **Severity Levels:** Critical > High > Medium > Low (determines urgency of intervention)

**Implementation:**
```python
from typing import List, Optional
from datetime import datetime, timedelta
from src.models.schemas import CheckIn, Pattern
import logging

logger = logging.getLogger(__name__)

class PatternDetectionAgent:
    """
    Analyzes check-in history to detect constitution violation patterns
    """
    
    def detect_patterns(self, checkins: List[CheckIn]) -> List[Pattern]:
        """
        Run all pattern detection rules
        
        Args:
            checkins: Recent check-ins (sorted oldest to newest)
            
        Returns:
            List of detected patterns
        """
        patterns = []
        
        # Run each detection rule
        if pattern := self._detect_sleep_degradation(checkins):
            patterns.append(pattern)
        
        if pattern := self._detect_training_abandonment(checkins):
            patterns.append(pattern)
        
        if pattern := self._detect_porn_relapse(checkins):
            patterns.append(pattern)
        
        if pattern := self._detect_compliance_decline(checkins):
            patterns.append(pattern)
        
        if pattern := self._detect_deep_work_collapse(checkins):
            patterns.append(pattern)
        
        logger.info(f"Pattern detection complete: {len(patterns)} patterns found")
        return patterns
    
    def _detect_sleep_degradation(self, checkins: List[CheckIn]) -> Optional[Pattern]:
        """
        Detect: <6 hours sleep for 3+ consecutive nights
        Severity: High (impacts Physical Sovereignty)
        """
        if len(checkins) < 3:
            return None
        
        recent_3 = checkins[-3:]
        low_sleep_nights = [c for c in recent_3 if c.sleep_hours < 6]
        
        if len(low_sleep_nights) >= 3:
            avg_sleep = sum(c.sleep_hours for c in recent_3) / 3
            return Pattern(
                type="sleep_degradation",
                severity="high",
                detected_at=datetime.utcnow(),
                data={
                    "avg_sleep_hours": round(avg_sleep, 1),
                    "consecutive_days": 3,
                    "threshold": 6,
                    "dates": [c.date for c in recent_3]
                }
            )
        return None
    
    def _detect_training_abandonment(self, checkins: List[CheckIn]) -> Optional[Pattern]:
        """
        Detect: 3+ missed training days in a row (excluding rest days)
        Severity: Medium
        """
        if len(checkins) < 3:
            return None
        
        recent_3 = checkins[-3:]
        missed_training = [c for c in recent_3 if not c.training_done]
        
        if len(missed_training) >= 3:
            return Pattern(
                type="training_abandonment",
                severity="medium",
                detected_at=datetime.utcnow(),
                data={
                    "consecutive_missed_days": 3,
                    "dates": [c.date for c in missed_training]
                }
            )
        return None
    
    def _detect_porn_relapse(self, checkins: List[CheckIn]) -> Optional[Pattern]:
        """
        Detect: 3+ porn violations in last 7 days
        Severity: Critical (Tier 1 non-negotiable)
        """
        if len(checkins) < 3:
            return None
        
        last_7_days = checkins[-7:] if len(checkins) >= 7 else checkins
        porn_violations = [c for c in last_7_days if c.porn_violation]
        
        if len(porn_violations) >= 3:
            return Pattern(
                type="porn_relapse_pattern",
                severity="critical",
                detected_at=datetime.utcnow(),
                data={
                    "violations_count": len(porn_violations),
                    "window_days": len(last_7_days),
                    "dates": [c.date for c in porn_violations]
                }
            )
        return None
    
    def _detect_compliance_decline(self, checkins: List[CheckIn]) -> Optional[Pattern]:
        """
        Detect: <70% compliance for 3+ consecutive days
        Severity: Medium (overall system breakdown)
        """
        if len(checkins) < 3:
            return None
        
        recent_3 = checkins[-3:]
        low_compliance_days = [c for c in recent_3 if c.compliance_score < 70]
        
        if len(low_compliance_days) >= 3:
            avg_compliance = sum(c.compliance_score for c in recent_3) / 3
            return Pattern(
                type="compliance_decline",
                severity="medium",
                detected_at=datetime.utcnow(),
                data={
                    "avg_compliance": round(avg_compliance, 1),
                    "consecutive_days": 3,
                    "threshold": 70,
                    "scores": [c.compliance_score for c in recent_3]
                }
            )
        return None
    
    def _detect_deep_work_collapse(self, checkins: List[CheckIn]) -> Optional[Pattern]:
        """
        Detect: <1.5 hours deep work for 5+ days
        Severity: Medium (violates Create Don't Consume)
        """
        if len(checkins) < 5:
            return None
        
        recent_5 = checkins[-5:]
        low_deep_work_days = [c for c in recent_5 if c.deep_work_hours < 1.5]
        
        if len(low_deep_work_days) >= 5:
            avg_deep_work = sum(c.deep_work_hours for c in recent_5) / 5
            return Pattern(
                type="deep_work_collapse",
                severity="medium",
                detected_at=datetime.utcnow(),
                data={
                    "avg_deep_work_hours": round(avg_deep_work, 1),
                    "consecutive_days": 5,
                    "threshold": 1.5,
                    "hours": [c.deep_work_hours for c in recent_5]
                }
            )
        return None

# Global instance
pattern_detection_agent = PatternDetectionAgent()
```

**Why This Design:**
- **Simple Rules:** No ML complexity - just threshold checks
- **Severity Levels:** Prioritizes critical issues (porn relapse) over medium (deep work)
- **Evidence Included:** Pattern data contains exact dates/values for intervention message
- **No False Positives:** Requires 3-5 consecutive violations before triggering

---

### Component 6: Intervention Agent (`src/agents/intervention.py`)

**Purpose:** Generate intervention messages when patterns are detected.

**Implementation:**
```python
from src.models.schemas import Pattern
from src.services.llm_service import get_llm_service
from src.services.constitution_service import get_constitution_service
from src.services.firestore_service import firestore_service
import logging

logger = logging.getLogger(__name__)

class InterventionAgent:
    """
    Generates intervention messages for detected patterns
    """
    
    def __init__(self, project_id: str):
        self.llm = get_llm_service(project_id)
        self.constitution = get_constitution_service()
    
    async def generate_intervention(
        self,
        user_id: str,
        pattern: Pattern
    ) -> str:
        """
        Generate intervention message for detected pattern
        
        Args:
            user_id: User ID
            pattern: Detected pattern object
            
        Returns:
            Intervention message text
        """
        # Get user context
        user_profile = firestore_service.get_user_profile(user_id)
        streak = user_profile.current_streak if user_profile else 0
        mode = user_profile.constitution_mode if user_profile else "standard"
        
        # Get relevant constitution section
        constitution_text = self._get_relevant_principle(pattern.type)
        
        # Build prompt
        prompt = self._build_intervention_prompt(
            pattern=pattern,
            streak=streak,
            mode=mode,
            constitution_text=constitution_text
        )
        
        # Generate intervention
        try:
            intervention_msg = await self.llm.generate_text(
                prompt=prompt,
                max_output_tokens=300,
                temperature=0.6  # Slightly lower than feedback (more serious tone)
            )
            
            logger.info(f"Generated {pattern.severity} intervention for user {user_id}: {pattern.type}")
            return intervention_msg
            
        except Exception as e:
            logger.error(f"Intervention generation failed: {e}")
            # Fallback to template-based intervention
            return self._fallback_intervention(pattern, streak)
    
    def _build_intervention_prompt(
        self,
        pattern: Pattern,
        streak: int,
        mode: str,
        constitution_text: str
    ) -> str:
        """Build intervention generation prompt"""
        
        severity_emoji = {
            "critical": "🚨🚨🚨",
            "high": "🚨",
            "medium": "⚠️",
            "low": "ℹ️"
        }
        
        emoji = severity_emoji.get(pattern.severity, "⚠️")
        
        prompt = f"""Generate an intervention message for this detected pattern.

{emoji} PATTERN DETECTED:
- Type: {pattern.type}
- Severity: {pattern.severity}
- Data: {pattern.data}

USER CONTEXT:
- Current Streak: {streak} days
- Constitution Mode: {mode}

VIOLATED PRINCIPLE:
{constitution_text}

Generate intervention (200-300 words) that:
1. **Alert** - Clearly state the pattern detected with evidence
2. **Constitution Reference** - Quote the violated principle
3. **Consequences** - Explain what happens if pattern continues
4. **Action Required** - ONE specific action to break the pattern (tonight/tomorrow)
5. **Motivation** - Reference their streak/progress at stake

TONE: Firm but supportive. Like a coach calling out a problem.
Use direct language. No sugarcoating, but not judgmental.
Format: Use emojis {emoji} at start, bold for **Action Required** section.

Intervention:"""

        return prompt
    
    def _get_relevant_principle(self, pattern_type: str) -> str:
        """Map pattern type to constitution principle"""
        constitution = self.constitution.get_full_text()
        
        mapping = {
            "sleep_degradation": "Principle 1: Physical Sovereignty",
            "training_abandonment": "Principle 1: Physical Sovereignty",
            "porn_relapse_pattern": "Tier 1 Non-Negotiables: Zero Porn",
            "compliance_decline": "Systems Over Willpower",
            "deep_work_collapse": "Principle 2: Create Don't Consume"
        }
        
        relevant_section = mapping.get(pattern_type, "Constitution")
        # Extract relevant section from constitution text
        # (simplified - in production, use semantic search)
        return f"{relevant_section}\n\n{constitution[:500]}..."
    
    def _fallback_intervention(self, pattern: Pattern, streak: int) -> str:
        """Fallback template if AI generation fails"""
        severity_emoji = {
            "critical": "🚨🚨🚨",
            "high": "🚨",
            "medium": "⚠️",
            "low": "ℹ️"
        }
        emoji = severity_emoji.get(pattern.severity, "⚠️")
        
        return f"""{emoji} PATTERN ALERT: {pattern.type.replace('_', ' ').title()}

Pattern detected in your recent check-ins:
{pattern.data}

Your {streak}-day streak is at risk. This violates your constitution.

Action Required: Review your last 3 days and identify what needs to change.

Reply with your plan to break this pattern."""

# Global instance
intervention_agent = None

def get_intervention_agent(project_id: str) -> InterventionAgent:
    """Get or create intervention agent (singleton)"""
    global intervention_agent
    if intervention_agent is None:
        intervention_agent = InterventionAgent(project_id)
    return intervention_agent
```

**Why This Design:**
- **Severity-Aware:** Uses different emojis/tone based on severity
- **Evidence-Based:** Includes actual data (e.g., "5.2 hrs average sleep")
- **Actionable:** Always includes ONE specific action to take
- **Streak Motivation:** References user's streak to motivate compliance

---

## 🚀 Implementation Timeline

### ✅ Day 1-2: LangGraph Foundation (TODAY)

**Tasks:**
1. Install dependencies (langgraph, langchain, google-cloud-aiplatform)
2. Create `src/services/llm_service.py` (Vertex AI wrapper)
3. Create `src/agents/state.py` (LangGraph state schema)
4. Create `src/agents/supervisor.py` (intent classification)
5. Test intent classification with sample messages

**Acceptance Criteria:**
- Dependencies installed successfully
- LLM service can call Gemini API
- Supervisor agent classifies intents correctly (>90% accuracy on test cases)
- Token usage logged for cost tracking

---

### Day 3-4: AI Check-In Feedback

**Tasks:**
1. Create `src/agents/checkin_agent.py` with AI feedback generation
2. Update `src/bot/conversation.py` to route through CheckIn agent
3. Test AI feedback with various scenarios:
   - Perfect compliance (100%)
   - Good compliance (80-99%)
   - Low compliance (<70%)
   - Different streak milestones (7, 30, 100 days)
4. Validate token usage (<800 tokens per check-in)

**Acceptance Criteria:**
- AI feedback is personalized (references streak, patterns, constitution)
- Feedback quality is better than Phase 1 hardcoded messages
- Token usage <800 per check-in (~$0.002 per check-in)
- Fallback works if AI fails

---

### Day 5-6: Pattern Detection + Interventions

**Tasks:**
1. Add Pattern and Intervention models to `src/models/schemas.py`
2. Create `src/agents/pattern_detection.py` with all 5 detection rules
3. Create `src/agents/intervention.py` with intervention generation
4. Add Firestore methods for logging interventions
5. Create `/trigger/pattern-scan` endpoint in `src/main.py`
6. Test pattern detection with historical check-in data

**Acceptance Criteria:**
- All 5 pattern detection rules work correctly
- Interventions generated with evidence and actionable steps
- Pattern scan endpoint processes all users without errors
- Interventions logged in Firestore

---

### Day 7: Deployment + Monitoring

**Tasks:**
1. Deploy updated code to Cloud Run
2. Set up Cloud Scheduler job (every 6 hours)
3. Configure Vertex AI cost alerts
4. End-to-end testing:
   - Complete check-in → verify AI feedback
   - Simulate sleep degradation → verify intervention sent
   - Trigger pattern scan → verify runs successfully
5. Monitor token usage and costs for 24 hours

**Acceptance Criteria:**
- Deployment successful, no errors
- Cloud Scheduler job running every 6 hours
- End-to-end flows working
- Daily cost <$0.02

---

## 🧪 Testing Strategy

### Unit Tests

```python
# tests/test_pattern_detection.py
def test_sleep_degradation_detection():
    """Test sleep degradation pattern detection"""
    checkins = [
        CheckIn(sleep_hours=5.5, ...),
        CheckIn(sleep_hours=5.0, ...),
        CheckIn(sleep_hours=5.2, ...)
    ]
    pattern = pattern_detection_agent._detect_sleep_degradation(checkins)
    assert pattern is not None
    assert pattern.type == "sleep_degradation"
    assert pattern.severity == "high"

def test_no_pattern_when_compliant():
    """Test that no pattern is detected when compliant"""
    checkins = [
        CheckIn(sleep_hours=8, ...),
        CheckIn(sleep_hours=7.5, ...),
        CheckIn(sleep_hours=8, ...)
    ]
    pattern = pattern_detection_agent._detect_sleep_degradation(checkins)
    assert pattern is None
```

### Integration Tests

```python
# tests/integration/test_phase2_flow.py
@pytest.mark.asyncio
async def test_ai_feedback_generation():
    """Test complete check-in flow with AI feedback"""
    state = {
        "user_id": "test_user",
        "checkin_answers": {
            "tier1": "All complete",
            "sleep": 8,
            "training": "Yes",
            "deep_work": 3
        }
    }
    
    result = await checkin_agent.generate_feedback(state)
    
    assert result["compliance_score"] == 100
    assert result["response"] is not None
    assert len(result["response"]) > 100  # Non-trivial response
    assert "streak" in result["response"].lower()  # References streak
```

---

## 📊 Cost Tracking

**Token Budget (per day):**

| Operation | Frequency | Tokens | Cost |
|-----------|-----------|--------|------|
| Intent Classification | 3x | 300 | $0.000075 |
| Check-In Feedback | 1x | 800 | $0.002 |
| Pattern Scan | 4x | 2000 | $0.005 |
| Intervention | 0.5x | 800 | $0.001 |
| **TOTAL** | - | **3900** | **$0.008/day** |

**Monthly:** $0.008 × 30 = **$0.24/month**

**Total (Phase 1 + Phase 2):** $0.15 + $0.24 = **$0.39/month** ✅

---

## 🎯 Success Criteria

**Functional:**
- ✅ Intent classification >90% accurate
- ✅ AI feedback is personalized (references context)
- ✅ All 5 pattern types detected correctly
- ✅ Interventions sent within 6 hours of detection
- ✅ Pattern scan runs every 6 hours

**Performance:**
- ✅ Check-in response time <5 seconds
- ✅ Pattern scan completes <30 seconds for 50 users
- ✅ Token usage <1000 per check-in

**Cost:**
- ✅ Daily cost <$0.02
- ✅ Monthly cost <$0.60
- ✅ Total (Phase 1 + 2) <$1

**Quality:**
- ✅ AI feedback is actionable
- ✅ Interventions reference constitution
- ✅ No false positive patterns
- ✅ No duplicate interventions

---

## 📋 Next Steps

Now that you have the complete implementation plan, let's start building! We'll begin with **Day 1-2: LangGraph Foundation**.

**Starting with:**
1. Update `requirements.txt` with new dependencies
2. Create `src/services/llm_service.py`
3. Create `src/agents/state.py`
4. Create `src/agents/supervisor.py`
5. Test intent classification

Are you ready to begin? 🚀
