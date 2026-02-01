# Phase 2: LangGraph Multi-Agent System with AI Pattern Detection

**Product Requirements Document & Technical Specification**

---

## Document Information

**Version:** 1.0  
**Date:** February 1, 2026  
**Author:** Constitution Agent Team  
**Status:** Approved for Implementation  
**Estimated Implementation Time:** 7 days  
**Target Cost:** <$0.02/day (<$0.60/month)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current State Analysis](#current-state-analysis)
3. [Product Requirements](#product-requirements)
4. [System Architecture](#system-architecture)
5. [Feature Specifications](#feature-specifications)
6. [Implementation Plan](#implementation-plan)
7. [Data Models](#data-models)
8. [Cost Analysis](#cost-analysis)
9. [Testing Strategy](#testing-strategy)
10. [Success Criteria](#success-criteria)
11. [Risks & Mitigations](#risks--mitigations)
12. [Rollout Plan](#rollout-plan)

---

## Executive Summary

### What We're Building

Phase 2 transforms the Phase 1 MVP from a basic check-in tracker into an intelligent accountability system powered by AI. We're adding:

1. **LangGraph Multi-Agent System** - Supervisor routes messages to specialized agents
2. **AI-Generated Feedback** - Personalized responses using Gemini 2.0 Flash
3. **Pattern Detection** - Automatic identification of constitution violations
4. **Proactive Interventions** - AI-generated warnings sent when patterns detected
5. **Scheduled Scanning** - Pattern detection runs every 6 hours

### Why This Matters

**Phase 1 Limitations:**
- Hardcoded feedback ("Check-in complete! Score: 80%") - no personalization
- Reactive only - waits for user to check in, doesn't catch violations between check-ins
- No intelligence - can't detect patterns or provide context-aware guidance
- Generic responses - doesn't reference user's specific constitution or history

**Phase 2 Benefits:**
- **Personalized:** Feedback references your streak, patterns, constitution principles
- **Proactive:** Detects violations (sleep <6hrs for 3 nights) and intervenes automatically
- **Intelligent:** Understands context, provides relevant guidance
- **Scalable:** Multi-agent architecture ready for Phase 3+ features (emotional processing, reports)

### Success Metrics

**Functional:**
- ✅ AI feedback includes user context (streak, patterns, constitution)
- ✅ All 5 pattern types detected correctly
- ✅ Interventions sent within 6 hours of pattern detection
- ✅ Intent classification >90% accuracy

**Performance:**
- ✅ Check-in response time <5 seconds
- ✅ Pattern scan <30 seconds for 50 users
- ✅ Token usage <1000 tokens per check-in

**Cost:**
- ✅ Daily cost <$0.02/day
- ✅ Monthly cost <$0.60/month
- ✅ Total system (Phase 1 + 2) <$1/month

### Timeline

**Week 1 Implementation:**
- Days 1-2: LangGraph foundation + Supervisor agent
- Days 3-4: AI check-in feedback
- Days 5-6: Pattern detection + Interventions
- Day 7: Deployment + Testing

---

## Current State Analysis

### Phase 1 Architecture

```
User → Telegram → Webhook → FastAPI
                               ↓
                          Bot Handler
                               ↓
                    Conversation State Machine
                               ↓
                    Hardcoded Feedback ("Check-in complete!")
                               ↓
                          Firestore
```

### Phase 1 Check-In Flow

1. User sends `/checkin`
2. Bot asks 4 questions (Tier 1, sleep, training, deep work)
3. Responses stored in Firestore
4. Compliance score calculated (% of 5 items completed)
5. Streak updated (increment if <48hrs since last, reset otherwise)
6. **Hardcoded feedback:** "✅ Check-in complete! Score: 80%. Streak: 5 days."

### Phase 1 Limitations

**No Personalization:**
```python
# Current Phase 1 feedback (hardcoded)
feedback = f"✅ Check-in complete!\n\n"
feedback += f"📊 Today's Score: {score}%\n"
feedback += f"🔥 Streak: {streak} days\n"
# Same message for everyone, every time
```

**No Pattern Detection:**
- If user has <6 hours sleep for 3 nights → no alert
- If user skips training 4 days in a row → no intervention
- If compliance drops to 40% for a week → no warning
- System is **reactive only** - waits for user to check in

**No Context Awareness:**
- Doesn't know if 5-day streak is impressive (for new user) or concerning (dropped from 60 days)
- Doesn't reference constitution principles
- Doesn't provide guidance based on patterns

### What Phase 2 Adds

**Intelligent Feedback:**
```python
# Phase 2 feedback (AI-generated, personalized)
feedback = await checkin_agent.generate_feedback(
    user_id=user_id,
    checkin_data=checkin,
    context={
        "current_streak": 47,
        "recent_pattern": "sleep declining",
        "constitution_mode": "Optimization",
        "recent_checkins": last_7_days
    }
)

# Example output:
# "Solid day - 80% compliance. Your 47-day streak is now in top 1% territory.
#  But I noticed deep work dropped to 1 hour today. What blocked you?
#  Remember Principle 2: Create Don't Consume. That missing hour likely went
#  to consumption. Tomorrow: block 9-11 AM, phone on airplane mode. 🎯"
```

**Proactive Pattern Detection:**
```python
# Runs every 6 hours automatically
patterns = pattern_detection_agent.detect_patterns(recent_checkins)

# Example patterns:
# - sleep_degradation: <6hrs for 3+ nights
# - training_abandonment: 3+ missed workouts
# - compliance_decline: <70% for 3+ days

if patterns:
    intervention = await intervention_agent.generate_intervention(pattern)
    await bot.send_message(user_id, intervention)
```

---

## Product Requirements

### PR-1: LangGraph Supervisor Agent

**User Story:**  
As a user, I want the bot to understand different types of messages (check-in, emotional distress, general questions) and route them to the appropriate handler.

**Requirements:**
- **PR-1.1:** Classify incoming messages into 4 intents: `checkin`, `emotional`, `query`, `command`
- **PR-1.2:** Route classified messages to appropriate sub-agent
- **PR-1.3:** Use Gemini 2.0 Flash for intent classification
- **PR-1.4:** Intent classification completes in <2 seconds
- **PR-1.5:** Classification accuracy >90% on test set

**Acceptance Criteria:**
- [ ] `/checkin` → routed to CheckIn agent
- [ ] "I'm feeling really lonely" → routed to Emotional agent (Phase 4)
- [ ] "What's my streak?" → routed to Query agent
- [ ] "/status" → routed to Command handler
- [ ] Supervisor logs intent classification for monitoring

**Priority:** P0 (Critical - foundation for all other agents)

---

### PR-2: AI-Powered Check-In Feedback

**User Story:**  
As a user, I want personalized feedback after check-ins that references my streak, patterns, and constitution principles, not just a generic "Check-in complete" message.

**Requirements:**
- **PR-2.1:** Generate feedback using Gemini 2.0 Flash
- **PR-2.2:** Include user context: streak, recent patterns, constitution mode
- **PR-2.3:** Reference relevant constitution principles
- **PR-2.4:** Provide specific guidance for tomorrow
- **PR-2.5:** Feedback length: 100-200 words
- **PR-2.6:** Token usage <700 per check-in

**Acceptance Criteria:**
- [ ] Feedback mentions current streak milestone
- [ ] Feedback notes patterns (improving/declining/consistent)
- [ ] Feedback references at least one constitution principle
- [ ] Feedback provides actionable guidance
- [ ] No generic phrases like "Good job!" without context
- [ ] Response generated in <3 seconds

**Example Scenarios:**

*Scenario 1: Perfect compliance, 47-day streak*
```
Expected: Acknowledges 100%, celebrates 47-day milestone, 
          references "Systems Over Willpower", encourages 
          protecting the streak
```

*Scenario 2: Missed deep work, 5-day streak*
```
Expected: Acknowledges 80%, notes missing deep work, asks
          what blocked user, references "Create Don't Consume",
          provides specific action for tomorrow
```

**Priority:** P0 (Critical - core value proposition of Phase 2)

---

### PR-3: Pattern Detection System

**User Story:**  
As a user, I want the system to automatically detect when I'm violating my constitution (sleep degradation, training abandonment, etc.) without me having to recognize the pattern myself.

**Requirements:**
- **PR-3.1:** Detect 5 pattern types (see specs below)
- **PR-3.2:** Patterns detected based on last 7 days of check-ins
- **PR-3.3:** Each pattern has severity level: low, medium, high, critical
- **PR-3.4:** Pattern detection runs on-demand (after check-in) and scheduled (every 6 hours)
- **PR-3.5:** No false positives - patterns require 3+ occurrences

**Pattern Specifications:**

**Pattern 1: Sleep Degradation**
- **Trigger:** <6 hours sleep for 3+ consecutive nights
- **Severity:** High
- **Data:** Average sleep hours, consecutive days
- **Constitution Violation:** Principle 1 (Physical Sovereignty)

**Pattern 2: Training Abandonment**
- **Trigger:** 3+ missed training days in a row (excluding designated rest days)
- **Severity:** Medium
- **Data:** Days missed, last training date
- **Constitution Violation:** Principle 1 (Physical Sovereignty)

**Pattern 3: Porn Relapse Pattern**
- **Trigger:** 3+ porn violations in 7 days
- **Severity:** Critical
- **Data:** Violation count, dates
- **Constitution Violation:** Principle 2 (Create Don't Consume)

**Pattern 4: Compliance Decline**
- **Trigger:** <70% compliance for 3+ consecutive days
- **Severity:** Medium
- **Data:** Average compliance, trend
- **Constitution Violation:** Multiple principles

**Pattern 5: Deep Work Collapse**
- **Trigger:** <1.5 hours deep work for 5+ days
- **Severity:** Medium
- **Data:** Average deep work hours, days below threshold
- **Constitution Violation:** Principle 2 (Create Don't Consume)

**Acceptance Criteria:**
- [ ] All 5 patterns detected correctly with test data
- [ ] No false positives (pattern requires threshold met)
- [ ] Pattern data includes specific evidence (hours, days, dates)
- [ ] Patterns logged in Firestore for tracking

**Priority:** P0 (Critical - enables proactive interventions)

---

### PR-4: Intervention Agent

**User Story:**  
As a user, when a pattern is detected, I want to receive a clear, actionable intervention message that explains the pattern, references my constitution, and tells me exactly what to do next.

**Requirements:**
- **PR-4.1:** Generate interventions using Gemini 2.0 Flash
- **PR-4.2:** Include: alert, evidence, constitution reference, consequence, action
- **PR-4.3:** Tone: firm but supportive (coach, not judge)
- **PR-4.4:** Length: 150-250 words
- **PR-4.5:** Token usage <800 per intervention
- **PR-4.6:** Interventions sent via Telegram immediately after detection

**Intervention Structure:**
1. **Alert:** 🚨 PATTERN ALERT: [Pattern Name] Detected
2. **Evidence:** Data showing the pattern (hours, days, specific dates)
3. **Constitution Reference:** Which principle is being violated
4. **Consequence:** What happens if pattern continues
5. **Action:** ONE specific next step to break pattern

**Acceptance Criteria:**
- [ ] Intervention clearly states pattern detected
- [ ] Intervention shows data evidence
- [ ] Intervention references specific constitution section
- [ ] Intervention provides exactly ONE actionable step
- [ ] Intervention logged in Firestore with timestamp
- [ ] User receives intervention within 5 seconds of detection

**Priority:** P0 (Critical - delivers value of pattern detection)

---

### PR-5: Scheduled Pattern Scanning

**User Story:**  
As a user, I want pattern detection to run automatically every 6 hours so violations are caught quickly, even if I haven't checked in recently.

**Requirements:**
- **PR-5.1:** Create `/trigger/pattern-scan` FastAPI endpoint
- **PR-5.2:** Set up Cloud Scheduler job (0 */6 * * * - every 6 hours)
- **PR-5.3:** Scan all "active" users (checked in within last 7 days)
- **PR-5.4:** Send interventions for any detected patterns
- **PR-5.5:** Log scan results (users scanned, patterns found, interventions sent)

**Acceptance Criteria:**
- [ ] Endpoint secured (requires Cloud Scheduler header)
- [ ] Scan completes in <30 seconds for 50 users
- [ ] Patterns detected only if new data since last scan
- [ ] Interventions sent successfully via Telegram
- [ ] Scan results logged to Cloud Logging

**Priority:** P1 (High - enables proactive detection between check-ins)

---

## System Architecture

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      User (Telegram)                        │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                  Telegram Webhook (FastAPI)                 │
│  POST /webhook/telegram                                     │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│               Supervisor Agent (LangGraph)                  │
│  - Classify intent using Gemini                             │
│  - Route to appropriate sub-agent                           │
└──────┬────────────┬─────────────┬───────────────┬──────────┘
       │            │             │               │
       ↓            ↓             ↓               ↓
┌───────────┐ ┌──────────┐ ┌─────────┐ ┌─────────────────┐
│ CheckIn   │ │Emotional │ │  Query  │ │    Command      │
│  Agent    │ │  Agent   │ │  Agent  │ │    Handler      │
│ (Phase 2) │ │(Phase 4) │ │(Phase 3)│ │   (Phase 1)     │
└─────┬─────┘ └──────────┘ └─────────┘ └─────────────────┘
      │
      ↓
┌─────────────────────────────────────────────────────────────┐
│           Gemini 2.0 Flash (Vertex AI)                      │
│  - Generate personalized feedback                           │
│  - Reference constitution + user context                    │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│                 Firestore (Data Storage)                    │
│  - users/                                                   │
│  - daily_checkins/                                          │
│  - interventions/ (new)                                     │
└─────────────────────────────────────────────────────────────┘


                    PARALLEL PATH: PATTERN DETECTION
                            
┌─────────────────────────────────────────────────────────────┐
│     Cloud Scheduler (every 6 hours: 0, 6, 12, 18)          │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         POST /trigger/pattern-scan (FastAPI)                │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓
┌─────────────────────────────────────────────────────────────┐
│         Pattern Detection Agent                             │
│  - Fetch recent check-ins (7 days)                          │
│  - Run detection rules for all 5 patterns                   │
│  - Return detected patterns with severity                   │
└───────────────────────────┬─────────────────────────────────┘
                            │
                            ↓ (if patterns found)
┌─────────────────────────────────────────────────────────────┐
│         Intervention Agent                                  │
│  - Generate intervention with Gemini                        │
│  - Reference constitution + pattern data                    │
│  - Send via Telegram                                        │
│  - Log to Firestore                                         │
└─────────────────────────────────────────────────────────────┘
```

### Component Interaction Flow

**Flow 1: User Check-In with AI Feedback**

```
1. User: /checkin
2. Telegram → Webhook → Supervisor Agent
3. Supervisor: classify_intent("checkin") → Intent.CHECKIN
4. Supervisor: route to CheckIn Agent
5. CheckIn Agent: run conversation (4 questions)
6. User: completes all questions
7. CheckIn Agent:
   - Calculate compliance score
   - Update streak
   - Fetch context (recent check-ins, patterns, mode)
   - Generate feedback with Gemini:
     * Input: checkin data + user context + constitution
     * Output: personalized feedback (100-200 words)
8. CheckIn Agent: send feedback to user via Telegram
9. CheckIn Agent: store check-in in Firestore
10. CheckIn Agent: trigger on-demand pattern detection
11. Pattern Detection: scan for patterns, send interventions if found
```

**Flow 2: Scheduled Pattern Detection**

```
1. Cloud Scheduler: triggers at 0, 6, 12, 18 hours
2. POST /trigger/pattern-scan
3. Endpoint:
   - Get all active users (checked in within 7 days)
   - For each user:
     a. Fetch recent check-ins (7 days)
     b. Run pattern detection (5 rules)
     c. If patterns found:
        - Generate intervention with Gemini
        - Send intervention via Telegram
        - Log intervention in Firestore
4. Return: scan results (users scanned, patterns found, interventions sent)
```

### Data Flow Diagram

```
User Check-In Data Flow:

[User] → [Telegram] → [Webhook] → [Supervisor]
                                       ↓
                                  [CheckIn Agent]
                                       ↓
                          ┌────────────┴────────────┐
                          ↓                         ↓
                   [Conversation State]      [Gemini API]
                          ↓                         ↓
                   [Store Responses]      [Generate Feedback]
                          ↓                         ↓
                     [Firestore] ← [Combined] → [Telegram]
                          ↓
                   [Pattern Detection]
                          ↓
                   [Intervention?]
```

---

## Feature Specifications

### Feature 1: LangGraph State Management

**File:** `src/agents/state.py`

**Purpose:** Define shared state schema for all agents

**Implementation:**

```python
from typing import TypedDict, Optional, List, Dict, Any
from enum import Enum
from datetime import datetime

class Intent(str, Enum):
    """User message intent types"""
    CHECKIN = "checkin"
    EMOTIONAL = "emotional"
    QUERY = "query"
    COMMAND = "command"

class ConstitutionState(TypedDict):
    """
    Shared state passed between agents in LangGraph.
    
    This state is immutable - each agent returns updated state.
    """
    # Request context
    user_id: str
    message: str
    telegram_update: Any  # telegram.Update object
    
    # Classification
    intent: Optional[Intent]
    confidence: Optional[float]
    
    # User context (loaded by supervisor)
    user_data: Optional[Dict[str, Any]]  # User profile from Firestore
    recent_checkins: Optional[List[Dict[str, Any]]]  # Last 7 days
    current_streak: Optional[int]
    constitution_mode: Optional[str]
    
    # Response
    response: Optional[str]
    next_action: Optional[str]
    
    # Metadata
    timestamp: datetime
    processing_time_ms: Optional[int]

class AgentResponse(TypedDict):
    """Standard response format from agents"""
    success: bool
    message: str
    data: Optional[Dict[str, Any]]
    error: Optional[str]
```

**Key Concepts:**
- **TypedDict:** Provides type hints for state shape
- **Immutable State:** Each agent returns new state (functional programming)
- **Context Loading:** Supervisor loads user data once, shared by all agents
- **Intent Classification:** Determines routing to sub-agents

---

### Feature 2: Vertex AI Service Wrapper

**File:** `src/services/llm_service.py`

**Purpose:** Centralized wrapper for Gemini API calls with error handling and token counting

**Implementation:**

```python
import vertexai
from vertexai.generative_models import GenerativeModel, GenerationConfig
import logging
from typing import Optional, Dict, Any
from src.config import settings

logger = logging.getLogger(__name__)

class LLMService:
    """
    Wrapper for Vertex AI Gemini API.
    
    Handles:
    - Model initialization
    - Token counting
    - Error handling
    - Rate limiting
    - Cost tracking
    """
    
    def __init__(self):
        # Initialize Vertex AI
        vertexai.init(
            project=settings.gcp_project_id,
            location=settings.gcp_region
        )
        
        # Create model instance
        self.model = GenerativeModel("gemini-2.0-flash-exp")
        
        # Generation config
        self.config = GenerationConfig(
            temperature=0.7,  # Balance creativity and consistency
            top_p=0.9,
            top_k=40,
            max_output_tokens=300,  # Limit response length
        )
        
        logger.info("✅ LLM Service initialized (Gemini 2.0 Flash)")
    
    async def generate_text(
        self,
        prompt: str,
        max_tokens: int = 300,
        temperature: float = 0.7
    ) -> str:
        """
        Generate text from prompt.
        
        Args:
            prompt: Input prompt
            max_tokens: Maximum output tokens
            temperature: Sampling temperature (0-1)
            
        Returns:
            Generated text
            
        Raises:
            Exception: If API call fails
        """
        try:
            # Update config
            config = GenerationConfig(
                temperature=temperature,
                max_output_tokens=max_tokens
            )
            
            # Generate
            response = self.model.generate_content(
                prompt,
                generation_config=config
            )
            
            # Extract text
            text = response.text.strip()
            
            # Count tokens (for monitoring)
            input_tokens = self._count_tokens(prompt)
            output_tokens = self._count_tokens(text)
            
            logger.info(f"LLM call: {input_tokens} in + {output_tokens} out = {input_tokens + output_tokens} total tokens")
            
            return text
            
        except Exception as e:
            logger.error(f"❌ LLM generation failed: {e}", exc_info=True)
            raise
    
    def _count_tokens(self, text: str) -> int:
        """
        Estimate token count.
        
        Rough estimate: 1 token ≈ 4 characters
        (More accurate counting available via Vertex AI API if needed)
        """
        return len(text) // 4
    
    async def classify_intent(self, message: str, context: Dict[str, Any]) -> str:
        """
        Classify user message intent.
        
        Returns: "checkin", "emotional", "query", or "command"
        """
        prompt = f"""Classify user intent from this message:
"{message}"

Context:
- User ID: {context.get('user_id')}
- Current streak: {context.get('current_streak', 0)} days
- Last check-in: {context.get('last_checkin_date', 'Never')}

Intents:
- checkin: User wants to do daily check-in
- emotional: User expressing difficult emotions (lonely, sad, urge)
- query: Questions about stats, constitution, how bot works
- command: Bot commands like /status, /help

Respond with ONE word ONLY: checkin, emotional, query, or command"""

        try:
            intent = await self.generate_text(prompt, max_tokens=10, temperature=0.3)
            intent = intent.lower().strip()
            
            # Validate
            valid_intents = ["checkin", "emotional", "query", "command"]
            if intent not in valid_intents:
                logger.warning(f"Invalid intent '{intent}', defaulting to query")
                return "query"
            
            return intent
            
        except Exception as e:
            logger.error(f"Intent classification failed: {e}")
            return "query"  # Safe default

# Global instance
llm_service = LLMService()
```

**Key Features:**
- Token counting for cost monitoring
- Error handling with fallbacks
- Temperature control (lower for classification, higher for creative feedback)
- Logging for debugging

---

### Feature 3: Supervisor Agent

**File:** `src/agents/supervisor.py`

**Purpose:** Classify intent and route to appropriate sub-agent

**Implementation:**

```python
from src.agents.state import ConstitutionState, Intent
from src.services.llm_service import llm_service
from src.services.firestore_service import firestore_service
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class SupervisorAgent:
    """
    Supervisor agent that:
    1. Loads user context
    2. Classifies message intent
    3. Routes to appropriate sub-agent
    """
    
    async def process(self, state: ConstitutionState) -> ConstitutionState:
        """
        Process incoming message.
        
        Steps:
        1. Load user context from Firestore
        2. Classify intent using LLM
        3. Update state with intent + context
        4. Return updated state for routing
        """
        logger.info(f"📊 Supervisor processing message from {state['user_id']}")
        
        try:
            # Load user context
            user = firestore_service.get_user(state['user_id'])
            recent_checkins = firestore_service.get_recent_checkins(
                state['user_id'], 
                days=7
            )
            
            # Build context for intent classification
            context = {
                'user_id': state['user_id'],
                'current_streak': user.streaks.current_streak if user else 0,
                'last_checkin_date': user.streaks.last_checkin_date if user else 'Never',
                'total_checkins': user.streaks.total_checkins if user else 0
            }
            
            # Classify intent
            intent_str = await llm_service.classify_intent(
                state['message'], 
                context
            )
            
            # Map to Intent enum
            intent = Intent(intent_str)
            
            logger.info(f"✅ Intent classified: {intent.value}")
            
            # Update state
            state['intent'] = intent
            state['user_data'] = user.dict() if user else None
            state['recent_checkins'] = [c.dict() for c in recent_checkins]
            state['current_streak'] = user.streaks.current_streak if user else 0
            state['constitution_mode'] = user.constitution_mode if user else "Maintenance"
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Supervisor failed: {e}", exc_info=True)
            # Fallback: default to query intent
            state['intent'] = Intent.QUERY
            return state
    
    def route(self, state: ConstitutionState) -> str:
        """
        Determine next agent based on intent.
        
        Returns: Agent name for LangGraph routing
        """
        intent = state.get('intent')
        
        if intent == Intent.CHECKIN:
            return "checkin_agent"
        elif intent == Intent.EMOTIONAL:
            return "emotional_agent"
        elif intent == Intent.QUERY:
            return "query_agent"
        else:  # COMMAND
            return "command_handler"

# Global instance
supervisor_agent = SupervisorAgent()
```

**Routing Logic:**
- `checkin` → CheckIn Agent (Phase 2)
- `emotional` → Emotional Agent (Phase 4)
- `query` → Query Agent (Phase 3)
- `command` → Command Handler (Phase 1)

---

### Feature 4: AI Check-In Agent

**File:** `src/agents/checkin_agent.py`

**Purpose:** Handle check-in flow and generate personalized AI feedback

**Implementation:**

```python
from src.agents.state import ConstitutionState, AgentResponse
from src.services.llm_service import llm_service
from src.services.firestore_service import firestore_service
from src.services.constitution_service import constitution_service
from src.utils.compliance import calculate_compliance_score
from src.utils.streak import update_streak_data
from src.models.schemas import CheckIn
from datetime import datetime
import pytz
import logging

logger = logging.getLogger(__name__)

class CheckInAgent:
    """
    CheckIn agent that:
    1. Runs check-in conversation (reuses Phase 1 conversation handler)
    2. Calculates compliance + streak
    3. Generates personalized feedback with Gemini
    4. Triggers pattern detection
    """
    
    async def generate_feedback(
        self,
        user_id: str,
        checkin: CheckIn,
        context: dict
    ) -> str:
        """
        Generate personalized feedback using Gemini.
        
        Args:
            user_id: User ID
            checkin: Today's check-in data
            context: User context (streak, recent patterns, mode)
            
        Returns:
            Personalized feedback message (100-200 words)
        """
        try:
            # Build prompt
            prompt = self._build_feedback_prompt(checkin, context)
            
            # Generate with Gemini
            feedback = await llm_service.generate_text(
                prompt,
                max_tokens=250,
                temperature=0.8  # Slightly creative
            )
            
            logger.info(f"✅ AI feedback generated for {user_id}")
            
            return feedback
            
        except Exception as e:
            logger.error(f"❌ Feedback generation failed: {e}")
            # Fallback to Phase 1 style feedback
            return self._fallback_feedback(checkin, context)
    
    def _build_feedback_prompt(self, checkin: CheckIn, context: dict) -> str:
        """Build prompt for feedback generation"""
        
        # Summarize Tier 1 completion
        tier1 = checkin.tier1_responses
        tier1_summary = []
        if tier1.sleep: tier1_summary.append("✅ Sleep (7+ hrs)")
        else: tier1_summary.append("❌ Sleep")
        if tier1.training: tier1_summary.append("✅ Training")
        else: tier1_summary.append("❌ Training")
        if tier1.deep_work: tier1_summary.append("✅ Deep Work (2+ hrs)")
        else: tier1_summary.append("❌ Deep Work")
        if tier1.zero_porn: tier1_summary.append("✅ Zero Porn")
        else: tier1_summary.append("❌ Porn violation")
        if tier1.boundaries: tier1_summary.append("✅ Boundaries")
        else: tier1_summary.append("❌ Boundary violation")
        
        # Recent trend
        recent_checkins = context.get('recent_checkins', [])
        if len(recent_checkins) >= 3:
            recent_scores = [c['compliance_score'] for c in recent_checkins[-3:]]
            avg_recent = sum(recent_scores) / len(recent_scores)
            if avg_recent > context.get('compliance_score', 0):
                trend = "declining"
            elif avg_recent < context.get('compliance_score', 0):
                trend = "improving"
            else:
                trend = "consistent"
        else:
            trend = "new user"
        
        # Load relevant constitution section
        constitution_text = constitution_service.get_constitution_text()
        # For Phase 2, include first 500 chars of constitution
        constitution_snippet = constitution_text[:500] + "..."
        
        prompt = f"""Generate personalized check-in feedback for this user.

TODAY'S CHECK-IN:
- Tier 1 Compliance: {', '.join(tier1_summary)}
- Sleep: {checkin.sleep_hours} hours
- Training: {'Yes' if checkin.training_completed else 'No/Rest Day'}
- Deep Work: {checkin.deep_work_hours} hours
- Compliance Score: {context.get('compliance_score', 0)}%

USER CONTEXT:
- Current Streak: {context.get('current_streak', 0)} days
- Longest Streak: {context.get('longest_streak', 0)} days
- Total Check-ins: {context.get('total_checkins', 0)}
- Constitution Mode: {context.get('constitution_mode', 'Maintenance')}
- Recent Trend: {trend}

CONSTITUTION PRINCIPLES (snippet):
{constitution_snippet}

Generate feedback (100-200 words) that:
1. Acknowledges today's performance (specific, not generic)
2. References their streak milestone (if significant)
3. Notes any patterns or trends
4. Connects to relevant constitution principle
5. Provides ONE specific action for tomorrow

Tone: Direct, motivating, no fluff. Like a coach who knows their athlete well.
Use emojis sparingly (1-2 max).
Focus on what matters - don't praise trivial things."""

        return prompt
    
    def _fallback_feedback(self, checkin: CheckIn, context: dict) -> str:
        """Fallback to hardcoded feedback if AI fails"""
        score = context.get('compliance_score', 0)
        streak = context.get('current_streak', 0)
        
        return f"""✅ Check-in complete!

📊 Today's Score: {score}%
🔥 Streak: {streak} days

Keep going! 💪"""

# Global instance
checkin_agent = CheckInAgent()
```

**Integration with Phase 1:**
- Reuse existing `conversation.py` for 4-question flow
- Replace hardcoded feedback with `checkin_agent.generate_feedback()`
- Trigger pattern detection after check-in completion

---

### Feature 5: Pattern Detection Agent

**File:** `src/agents/pattern_detection.py`

**Purpose:** Detect constitution violations from check-in history

**Implementation:**

```python
from typing import List, Optional
from src.models.schemas import CheckIn, Pattern
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)

class PatternDetectionAgent:
    """
    Detects 5 pattern types:
    1. Sleep degradation
    2. Training abandonment
    3. Porn relapse
    4. Compliance decline
    5. Deep work collapse
    """
    
    def detect_patterns(self, checkins: List[CheckIn]) -> List[Pattern]:
        """
        Run all pattern detection rules.
        
        Args:
            checkins: Recent check-ins (7 days recommended)
            
        Returns:
            List of detected patterns
        """
        if not checkins:
            return []
        
        patterns = []
        
        # Run each detection rule
        pattern = self.detect_sleep_degradation(checkins)
        if pattern:
            patterns.append(pattern)
        
        pattern = self.detect_training_abandonment(checkins)
        if pattern:
            patterns.append(pattern)
        
        pattern = self.detect_porn_relapse(checkins)
        if pattern:
            patterns.append(pattern)
        
        pattern = self.detect_compliance_decline(checkins)
        if pattern:
            patterns.append(pattern)
        
        pattern = self.detect_deep_work_collapse(checkins)
        if pattern:
            patterns.append(pattern)
        
        logger.info(f"Pattern detection: {len(patterns)} patterns found")
        
        return patterns
    
    def detect_sleep_degradation(self, checkins: List[CheckIn]) -> Optional[Pattern]:
        """
        Detect <6 hours sleep for 3+ consecutive nights.
        
        Severity: High
        """
        if len(checkins) < 3:
            return None
        
        # Check last 3 nights
        recent_3 = checkins[-3:]
        low_sleep_nights = [c for c in recent_3 if c.sleep_hours < 6]
        
        if len(low_sleep_nights) >= 3:
            avg_sleep = sum(c.sleep_hours for c in recent_3) / 3
            
            return Pattern(
                type="sleep_degradation",
                severity="high",
                detected_at=datetime.now(),
                data={
                    "avg_sleep_hours": round(avg_sleep, 1),
                    "consecutive_nights": 3,
                    "threshold": 6,
                    "dates": [c.date for c in recent_3]
                }
            )
        
        return None
    
    def detect_training_abandonment(self, checkins: List[CheckIn]) -> Optional[Pattern]:
        """
        Detect 3+ missed training days in a row.
        
        Severity: Medium
        """
        if len(checkins) < 3:
            return None
        
        # Check last 3 days
        recent_3 = checkins[-3:]
        missed_days = [c for c in recent_3 if not c.training_completed]
        
        if len(missed_days) >= 3:
            last_training_date = None
            for c in reversed(checkins):
                if c.training_completed:
                    last_training_date = c.date
                    break
            
            return Pattern(
                type="training_abandonment",
                severity="medium",
                detected_at=datetime.now(),
                data={
                    "consecutive_days_missed": 3,
                    "last_training_date": last_training_date,
                    "dates": [c.date for c in recent_3]
                }
            )
        
        return None
    
    def detect_porn_relapse(self, checkins: List[CheckIn]) -> Optional[Pattern]:
        """
        Detect 3+ porn violations in 7 days.
        
        Severity: Critical
        """
        if len(checkins) < 3:
            return None
        
        # Check all available checkins (up to 7 days)
        violations = [c for c in checkins if not c.tier1_responses.zero_porn]
        
        if len(violations) >= 3:
            return Pattern(
                type="porn_relapse",
                severity="critical",
                detected_at=datetime.now(),
                data={
                    "violation_count": len(violations),
                    "days_span": len(checkins),
                    "dates": [c.date for c in violations]
                }
            )
        
        return None
    
    def detect_compliance_decline(self, checkins: List[CheckIn]) -> Optional[Pattern]:
        """
        Detect <70% compliance for 3+ consecutive days.
        
        Severity: Medium
        """
        if len(checkins) < 3:
            return None
        
        # Check last 3 days
        recent_3 = checkins[-3:]
        low_compliance_days = [c for c in recent_3 if c.compliance_score < 70]
        
        if len(low_compliance_days) >= 3:
            avg_compliance = sum(c.compliance_score for c in recent_3) / 3
            
            return Pattern(
                type="compliance_decline",
                severity="medium",
                detected_at=datetime.now(),
                data={
                    "avg_compliance": round(avg_compliance, 1),
                    "consecutive_days": 3,
                    "threshold": 70,
                    "dates": [c.date for c in recent_3]
                }
            )
        
        return None
    
    def detect_deep_work_collapse(self, checkins: List[CheckIn]) -> Optional[Pattern]:
        """
        Detect <1.5 hours deep work for 5+ days.
        
        Severity: Medium
        """
        if len(checkins) < 5:
            return None
        
        # Check last 5 days
        recent_5 = checkins[-5:]
        low_deep_work_days = [c for c in recent_5 if c.deep_work_hours < 1.5]
        
        if len(low_deep_work_days) >= 5:
            avg_deep_work = sum(c.deep_work_hours for c in recent_5) / 5
            
            return Pattern(
                type="deep_work_collapse",
                severity="medium",
                detected_at=datetime.now(),
                data={
                    "avg_deep_work_hours": round(avg_deep_work, 1),
                    "consecutive_days": 5,
                    "threshold": 1.5,
                    "dates": [c.date for c in recent_5]
                }
            )
        
        return None

# Global instance
pattern_detection_agent = PatternDetectionAgent()
```

**Detection Thresholds:**
- All patterns require 3+ occurrences (no false positives)
- Sleep: <6 hours for 3 nights
- Training: 3 consecutive missed days
- Porn: 3 violations in 7 days
- Compliance: <70% for 3 days
- Deep Work: <1.5 hours for 5 days

---

### Feature 6: Intervention Agent

**File:** `src/agents/intervention.py`

**Purpose:** Generate and send intervention messages

**Implementation:**

```python
from src.models.schemas import Pattern
from src.services.llm_service import llm_service
from src.services.constitution_service import constitution_service
from src.services.firestore_service import firestore_service
import logging

logger = logging.getLogger(__name__)

class InterventionAgent:
    """
    Generates intervention messages when patterns detected.
    
    Intervention structure:
    1. Alert (clear statement of pattern)
    2. Evidence (data showing pattern)
    3. Constitution reference (violated principle)
    4. Consequence (what happens if continues)
    5. Action (ONE specific next step)
    """
    
    async def generate_intervention(
        self,
        user_id: str,
        pattern: Pattern
    ) -> str:
        """
        Generate intervention message for detected pattern.
        
        Args:
            user_id: User ID
            pattern: Detected pattern with data
            
        Returns:
            Intervention message (150-250 words)
        """
        try:
            # Load user context
            user = firestore_service.get_user(user_id)
            
            # Build prompt
            prompt = self._build_intervention_prompt(pattern, user)
            
            # Generate with Gemini
            intervention = await llm_service.generate_text(
                prompt,
                max_tokens=300,
                temperature=0.7
            )
            
            logger.info(f"✅ Intervention generated for {user_id}: {pattern.type}")
            
            # Log intervention in Firestore
            firestore_service.log_intervention(
                user_id=user_id,
                pattern=pattern,
                message=intervention
            )
            
            return intervention
            
        except Exception as e:
            logger.error(f"❌ Intervention generation failed: {e}")
            return self._fallback_intervention(pattern)
    
    def _build_intervention_prompt(self, pattern: Pattern, user: Any) -> str:
        """Build prompt for intervention generation"""
        
        # Map pattern type to constitution principle
        principle_map = {
            "sleep_degradation": "Principle 1: Physical Sovereignty",
            "training_abandonment": "Principle 1: Physical Sovereignty",
            "porn_relapse": "Principle 2: Create Don't Consume",
            "compliance_decline": "Multiple principles violated",
            "deep_work_collapse": "Principle 2: Create Don't Consume"
        }
        
        violated_principle = principle_map.get(pattern.type, "Your constitution")
        
        # Load constitution section
        constitution = constitution_service.get_constitution_text()
        constitution_snippet = constitution[:800]
        
        prompt = f"""Generate an intervention message for this detected pattern.

PATTERN DETECTED:
- Type: {pattern.type.replace('_', ' ').title()}
- Severity: {pattern.severity.upper()}
- Data: {pattern.data}

USER CONTEXT:
- Current Streak: {user.streaks.current_streak if user else 0} days
- Longest Streak: {user.streaks.longest_streak if user else 0} days
- Total Check-ins: {user.streaks.total_checkins if user else 0}
- Constitution Mode: {user.constitution_mode if user else 'Maintenance'}

VIOLATED PRINCIPLE:
{violated_principle}

CONSTITUTION (snippet):
{constitution_snippet}

Generate intervention (150-250 words) with this structure:
1. 🚨 PATTERN ALERT: [Pattern Name] Detected
2. Evidence: Show the data (specific numbers, dates)
3. Constitution: Quote the violated principle
4. Consequence: What happens if this continues
5. Action: ONE specific step to break pattern (be very specific - time, place, what to do)

Tone: Firm but supportive. Like a coach calling out a problem.
Use direct language. No sugarcoating, no fluff.
Make the action step CONCRETE (not "sleep more" - but "Tonight: in bed by 11 PM")."""

        return prompt
    
    def _fallback_intervention(self, pattern: Pattern) -> str:
        """Fallback intervention if AI fails"""
        return f"""🚨 PATTERN ALERT: {pattern.type.replace('_', ' ').title()} Detected

Your recent check-ins show a concerning pattern:
{pattern.data}

This violates your constitution. Take action to break this pattern.

Check in daily to track improvement. 💪"""

# Global instance
intervention_agent = InterventionAgent()
```

**Example Generated Intervention:**

```
🚨 PATTERN ALERT: Sleep Degradation Detected

Last 3 nights: 5.5hrs, 5hrs, 5.2hrs (average: 5.2hrs)
Your constitution requires 7+ hours minimum.

This violates Principle 1: Physical Sovereignty.
"My body is my primary asset. No external pressure compromises my long-term health."

If this continues:
- Cognitive performance drops 20-30%
- Training recovery suffers
- You're sacrificing tomorrow for today
- Your 47-day streak is at risk

ACTION REQUIRED:
Tonight: In bed by 11 PM, no exceptions.
Set alarm for 6:30 AM (7.5 hours sleep).
Block calendar 10:30-11 PM as "Sleep Prep" - non-negotiable.

Your streak proves you can maintain consistency. Apply that same discipline to sleep.
```

---

## Implementation Plan

### Day 1: LangGraph Foundation

**Goals:**
- Install dependencies
- Create state schema
- Set up LLM service wrapper
- Test Gemini API connection

**Tasks:**

1. **Update requirements.txt:**
```txt
# Add to requirements.txt
google-cloud-aiplatform==1.42.0
langchain==0.1.0
langgraph==0.0.40
```

2. **Install locally:**
```bash
pip install -r requirements.txt
```

3. **Create files:**
- `src/agents/__init__.py`
- `src/agents/state.py` (state schema)
- `src/services/llm_service.py` (Gemini wrapper)

4. **Test LLM service:**
```bash
python -c "from src.services.llm_service import llm_service; print(llm_service.model)"
```

5. **Test Gemini API:**
```python
# tests/test_llm_service.py
async def test_gemini_connection():
    result = await llm_service.generate_text("Say hello")
    assert len(result) > 0
```

**Success Criteria:**
- ✅ Dependencies installed
- ✅ LLM service initializes without errors
- ✅ Can generate text with Gemini

**Estimated Time:** 2-3 hours

---

### Day 2: Supervisor Agent

**Goals:**
- Implement Supervisor agent
- Test intent classification
- Validate routing logic

**Tasks:**

1. **Create `src/agents/supervisor.py`:**
- Load user context from Firestore
- Classify intent with LLM
- Route to appropriate agent

2. **Test intent classification:**
```python
# tests/test_supervisor.py
async def test_intent_classification():
    state = {
        'user_id': '123',
        'message': '/checkin'
    }
    result = await supervisor_agent.process(state)
    assert result['intent'] == Intent.CHECKIN
```

3. **Test with sample messages:**
- "/checkin" → checkin
- "I'm feeling lonely" → emotional
- "What's my streak?" → query
- "/status" → command

4. **Validate token usage:**
- Intent classification should use <100 tokens

**Success Criteria:**
- ✅ Supervisor classifies intent correctly (>90% accuracy on test cases)
- ✅ User context loaded from Firestore
- ✅ Routing logic works

**Estimated Time:** 3-4 hours

---

### Day 3: AI Check-In Feedback

**Goals:**
- Create CheckIn agent
- Implement feedback generation
- Integrate with Phase 1 conversation

**Tasks:**

1. **Create `src/agents/checkin_agent.py`:**
- Implement `generate_feedback()` method
- Build prompts with user context
- Test with sample check-ins

2. **Update `src/bot/conversation.py`:**
```python
# Replace hardcoded feedback
# OLD:
feedback = f"✅ Check-in complete! Score: {score}%"

# NEW:
feedback = await checkin_agent.generate_feedback(
    user_id=user_id,
    checkin=checkin,
    context=context
)
```

3. **Test feedback generation:**
```python
# Manual test
checkin_data = {
    'tier1_responses': {...},
    'sleep_hours': 7.5,
    'training_completed': True,
    'deep_work_hours': 3
}
context = {
    'current_streak': 47,
    'compliance_score': 100
}
feedback = await checkin_agent.generate_feedback('123', checkin_data, context)
print(feedback)
```

4. **Validate feedback quality:**
- References streak
- Notes patterns
- Mentions constitution
- Provides actionable guidance

**Success Criteria:**
- ✅ Feedback is personalized (mentions user data)
- ✅ Token usage <700 per check-in
- ✅ Generation time <3 seconds
- ✅ Fallback works if API fails

**Estimated Time:** 4-5 hours

---

### Day 4: Feedback Testing & Refinement

**Goals:**
- Test AI feedback with various scenarios
- Refine prompts for better quality
- Optimize token usage

**Tasks:**

1. **Create test scenarios:**
- Perfect compliance (100%), long streak
- Low compliance (40%), broken streak
- Partial compliance (80%), specific violations
- New user (first check-in)

2. **Evaluate feedback quality:**
- Is it personalized?
- Does it provide value?
- Is tone appropriate?
- Are actions specific?

3. **Refine prompts:**
- Adjust temperature
- Add/remove context
- Optimize token usage

4. **Load testing:**
- Test with 10 check-ins in a row
- Measure response time
- Calculate token usage

**Success Criteria:**
- ✅ Feedback quality meets requirements
- ✅ Token usage optimized (<650 avg)
- ✅ Response time <3 seconds
- ✅ No generic responses

**Estimated Time:** 3-4 hours

---

### Day 5: Pattern Detection

**Goals:**
- Implement pattern detection rules
- Create Pattern and Intervention models
- Test with historical data

**Tasks:**

1. **Update `src/models/schemas.py`:**
```python
class Pattern(BaseModel):
    type: str
    severity: str
    detected_at: datetime
    data: dict

class Intervention(BaseModel):
    user_id: str
    pattern: Pattern
    message: str
    sent_at: datetime
```

2. **Create `src/agents/pattern_detection.py`:**
- Implement all 5 detection rules
- Test each rule individually

3. **Test pattern detection:**
```python
# tests/test_pattern_detection.py
def test_sleep_degradation():
    checkins = [
        CheckIn(sleep_hours=5.5, ...),
        CheckIn(sleep_hours=5.0, ...),
        CheckIn(sleep_hours=5.2, ...)
    ]
    pattern = pattern_detection_agent.detect_sleep_degradation(checkins)
    assert pattern is not None
    assert pattern.type == "sleep_degradation"
    assert pattern.severity == "high"
```

4. **Test with real historical data:**
- Create check-ins that trigger each pattern
- Verify detection logic
- Check for false positives

**Success Criteria:**
- ✅ All 5 patterns detected correctly
- ✅ No false positives
- ✅ Pattern data includes evidence
- ✅ Unit tests passing

**Estimated Time:** 4-5 hours

---

### Day 6: Intervention Agent

**Goals:**
- Implement intervention generation
- Test intervention messages
- Add Firestore logging

**Tasks:**

1. **Create `src/agents/intervention.py`:**
- Implement `generate_intervention()` method
- Build intervention prompts
- Test with detected patterns

2. **Add Firestore collection:**
```python
# src/services/firestore_service.py
def log_intervention(user_id: str, pattern: Pattern, message: str):
    """Log intervention in Firestore"""
    intervention_ref = db.collection('interventions') \
        .document(user_id) \
        .collection('interventions') \
        .document()
    
    intervention_ref.set({
        'pattern_type': pattern.type,
        'severity': pattern.severity,
        'detected_at': pattern.detected_at,
        'data': pattern.data,
        'message': message,
        'sent_at': datetime.now(),
        'acknowledged': None
    })
```

3. **Test intervention generation:**
```python
pattern = Pattern(
    type="sleep_degradation",
    severity="high",
    data={"avg_sleep": 5.2, "consecutive_nights": 3}
)
intervention = await intervention_agent.generate_intervention('123', pattern)
print(intervention)
```

4. **Validate intervention structure:**
- Has alert
- Shows evidence
- References constitution
- Explains consequences
- Provides action

**Success Criteria:**
- ✅ Interventions generated correctly
- ✅ Token usage <800 per intervention
- ✅ Structure matches requirements
- ✅ Logged in Firestore

**Estimated Time:** 3-4 hours

---

### Day 7: Scheduled Scanning & Deployment

**Goals:**
- Create pattern scan endpoint
- Set up Cloud Scheduler
- Deploy to Cloud Run
- End-to-end testing

**Tasks:**

1. **Create `/trigger/pattern-scan` endpoint:**
```python
# src/main.py
@app.post("/trigger/pattern-scan")
async def pattern_scan_trigger(request: Request):
    # Verify Cloud Scheduler header
    scheduler_header = request.headers.get("X-CloudScheduler-JobName")
    if scheduler_header != "pattern-scan-job":
        raise HTTPException(403, "Unauthorized")
    
    # Get active users
    active_users = firestore_service.get_active_users(days=7)
    
    patterns_detected = 0
    interventions_sent = 0
    
    for user in active_users:
        checkins = firestore_service.get_recent_checkins(user.user_id, days=7)
        patterns = pattern_detection_agent.detect_patterns(checkins)
        
        for pattern in patterns:
            patterns_detected += 1
            intervention = await intervention_agent.generate_intervention(
                user.user_id, 
                pattern
            )
            await bot_manager.send_message(user.user_id, intervention)
            interventions_sent += 1
    
    return {
        "status": "scan_complete",
        "users_scanned": len(active_users),
        "patterns_detected": patterns_detected,
        "interventions_sent": interventions_sent
    }
```

2. **Deploy to Cloud Run:**
```bash
# Build image
gcloud builds submit --tag gcr.io/accountability-agent/constitution-agent:phase2

# Deploy
gcloud run deploy constitution-agent \
  --image gcr.io/accountability-agent/constitution-agent:phase2 \
  --region asia-south1 \
  --platform managed \
  --allow-unauthenticated \
  --set-env-vars "ENVIRONMENT=production,GCP_PROJECT_ID=accountability-agent,GCP_REGION=asia-south1,WEBHOOK_URL=https://constitution-agent-450357249483.asia-south1.run.app"
```

3. **Set up Cloud Scheduler:**
```bash
# Enable API
gcloud services enable cloudscheduler.googleapis.com

# Create job (runs every 6 hours: 0, 6, 12, 18)
gcloud scheduler jobs create http pattern-scan-job \
  --schedule="0 */6 * * *" \
  --uri="https://constitution-agent-450357249483.asia-south1.run.app/trigger/pattern-scan" \
  --http-method=POST \
  --headers="X-CloudScheduler-JobName=pattern-scan-job" \
  --location=asia-south1
```

4. **Test end-to-end:**
- Complete check-in → verify AI feedback
- Create 3 low-sleep check-ins → verify pattern detected
- Trigger pattern scan → verify intervention sent
- Check Firestore → verify data logged

5. **Monitor costs:**
- Check Vertex AI console
- Verify token usage
- Validate cost <$0.02/day

**Success Criteria:**
- ✅ Deployment successful
- ✅ Cloud Scheduler job created
- ✅ Pattern scan works end-to-end
- ✅ Cost within budget

**Estimated Time:** 5-6 hours

---

## Data Models

### Existing Models (Phase 1)

```python
# src/models/schemas.py

class Tier1Responses(BaseModel):
    sleep: bool
    training: bool
    deep_work: bool
    zero_porn: bool
    boundaries: bool

class CheckIn(BaseModel):
    user_id: str
    date: str  # YYYY-MM-DD
    tier1_responses: Tier1Responses
    sleep_hours: float
    training_completed: bool
    deep_work_hours: float
    compliance_score: float
    created_at: datetime

class Streaks(BaseModel):
    current_streak: int = 0
    longest_streak: int = 0
    total_checkins: int = 0
    last_checkin_date: Optional[str] = None

class User(BaseModel):
    user_id: str
    telegram_username: Optional[str]
    first_name: str
    created_at: datetime
    streaks: Streaks
    constitution_mode: str = "Maintenance"
```

### New Models (Phase 2)

```python
# Add to src/models/schemas.py

class Pattern(BaseModel):
    """Detected constitution violation pattern"""
    type: str  # sleep_degradation, training_abandonment, etc.
    severity: str  # low, medium, high, critical
    detected_at: datetime
    data: Dict[str, Any]  # Pattern-specific data
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class Intervention(BaseModel):
    """Intervention sent to user"""
    intervention_id: str
    user_id: str
    pattern: Pattern
    message: str
    sent_at: datetime
    acknowledged: Optional[bool] = None
    acknowledged_at: Optional[datetime] = None
    
    class Config:
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

class ConstitutionState(TypedDict):
    """LangGraph state (TypedDict for immutability)"""
    user_id: str
    message: str
    telegram_update: Any
    intent: Optional[str]
    confidence: Optional[float]
    user_data: Optional[Dict[str, Any]]
    recent_checkins: Optional[List[Dict[str, Any]]]
    current_streak: Optional[int]
    constitution_mode: Optional[str]
    response: Optional[str]
    next_action: Optional[str]
    timestamp: datetime
    processing_time_ms: Optional[int]
```

### Firestore Schema Updates

**New Collection: interventions**

```
interventions/
└── {user_id}/
    └── interventions/
        └── {intervention_id}/
            ├── pattern_type: string
            ├── severity: string
            ├── detected_at: timestamp
            ├── data: map
            ├── message: string
            ├── sent_at: timestamp
            ├── acknowledged: boolean (nullable)
            └── acknowledged_at: timestamp (nullable)
```

**Example Document:**

```json
{
  "pattern_type": "sleep_degradation",
  "severity": "high",
  "detected_at": "2026-02-05T10:30:00Z",
  "data": {
    "avg_sleep_hours": 5.2,
    "consecutive_nights": 3,
    "threshold": 6,
    "dates": ["2026-02-03", "2026-02-04", "2026-02-05"]
  },
  "message": "🚨 PATTERN ALERT: Sleep Degradation...",
  "sent_at": "2026-02-05T10:30:15Z",
  "acknowledged": null,
  "acknowledged_at": null
}
```

---

## Cost Analysis

### Token Usage Estimates

**Gemini 2.0 Flash Pricing:**
- Input: $0.00025 per 1K tokens
- Output: $0.001 per 1K tokens

**Daily Operations:**

| Operation | Frequency | Input Tokens | Output Tokens | Cost/Call | Daily Cost |
|-----------|-----------|--------------|---------------|-----------|------------|
| Intent Classification | 3 msgs/day | 80 | 5 | $0.000025 | $0.000075 |
| Check-In Feedback | 1/day | 500 | 150 | $0.001625 | $0.001625 |
| Pattern Scan | 4 scans/day | 400 | 0 | $0.0001 | $0.0004 |
| Intervention | 0.5/day avg | 600 | 200 | $0.00035 | $0.000175 |
| **DAILY TOTAL** | - | - | - | - | **$0.00228** |

**Monthly Cost:**
- Gemini API: $0.00228 × 30 = **$0.068/month**
- Cloud Scheduler: $0.10/month (3 jobs)
- **Phase 2 Total: $0.17/month**

**Combined Phase 1 + 2:**
- Phase 1 (Cloud Run + Firestore): $0.15/month
- Phase 2 (Gemini + Scheduler): $0.17/month
- **Total: $0.32/month** ✅ (Target: <$5/month)

### Cost Optimization Strategies

**1. Prompt Caching (Phase 2.1):**
- Cache constitution text (1000 tokens)
- Reduces input tokens by 60%
- Saves ~$0.01/month

**2. Batch Pattern Scans:**
- Scan all users in one job (not per-user jobs)
- Reduces Cloud Scheduler costs

**3. Skip Scans with No New Data:**
- Only scan if user has checked in since last scan
- Reduces unnecessary API calls

**4. Shorter Classification Prompts:**
- Intent classification: 80 tokens → 50 tokens
- Saves ~$0.0001/day

**Optimized Monthly Cost:** ~$0.25/month

---

## Testing Strategy

### Unit Tests

**File:** `tests/test_pattern_detection.py`

```python
import pytest
from src.agents.pattern_detection import pattern_detection_agent
from src.models.schemas import CheckIn, Tier1Responses
from datetime import datetime

def create_checkin(sleep_hours, training, deep_work, porn=True, compliance=80):
    """Helper to create test check-in"""
    return CheckIn(
        user_id="123",
        date="2026-02-01",
        tier1_responses=Tier1Responses(
            sleep=sleep_hours >= 7,
            training=training,
            deep_work=deep_work >= 2,
            zero_porn=porn,
            boundaries=True
        ),
        sleep_hours=sleep_hours,
        training_completed=training,
        deep_work_hours=deep_work,
        compliance_score=compliance,
        created_at=datetime.now()
    )

def test_sleep_degradation_detected():
    """Test sleep degradation pattern detection"""
    checkins = [
        create_checkin(5.5, True, 3),
        create_checkin(5.0, True, 2.5),
        create_checkin(5.2, True, 2)
    ]
    
    pattern = pattern_detection_agent.detect_sleep_degradation(checkins)
    
    assert pattern is not None
    assert pattern.type == "sleep_degradation"
    assert pattern.severity == "high"
    assert pattern.data['avg_sleep_hours'] < 6
    assert pattern.data['consecutive_nights'] == 3

def test_sleep_degradation_not_detected_when_good():
    """Test no false positive when sleep is good"""
    checkins = [
        create_checkin(7.5, True, 3),
        create_checkin(8.0, True, 2.5),
        create_checkin(7.2, True, 2)
    ]
    
    pattern = pattern_detection_agent.detect_sleep_degradation(checkins)
    
    assert pattern is None

def test_training_abandonment_detected():
    """Test training abandonment pattern"""
    checkins = [
        create_checkin(7, False, 3),
        create_checkin(7.5, False, 2.5),
        create_checkin(8, False, 2)
    ]
    
    pattern = pattern_detection_agent.detect_training_abandonment(checkins)
    
    assert pattern is not None
    assert pattern.type == "training_abandonment"
    assert pattern.severity == "medium"

def test_porn_relapse_detected():
    """Test porn relapse pattern"""
    checkins = [
        create_checkin(7, True, 3, porn=False, compliance=80),
        create_checkin(7.5, True, 2.5, porn=False, compliance=80),
        create_checkin(8, True, 2, porn=False, compliance=80),
    ]
    
    pattern = pattern_detection_agent.detect_porn_relapse(checkins)
    
    assert pattern is not None
    assert pattern.type == "porn_relapse"
    assert pattern.severity == "critical"
    assert pattern.data['violation_count'] == 3

def test_compliance_decline_detected():
    """Test compliance decline pattern"""
    checkins = [
        create_checkin(6, False, 1, compliance=60),
        create_checkin(6.5, False, 1.2, compliance=65),
        create_checkin(6.2, False, 1.5, compliance=62)
    ]
    
    pattern = pattern_detection_agent.detect_compliance_decline(checkins)
    
    assert pattern is not None
    assert pattern.type == "compliance_decline"
    assert pattern.severity == "medium"
    assert pattern.data['avg_compliance'] < 70

def test_deep_work_collapse_detected():
    """Test deep work collapse pattern"""
    checkins = [
        create_checkin(7, True, 1.0),
        create_checkin(7.5, True, 1.2),
        create_checkin(8, True, 1.1),
        create_checkin(7.2, True, 1.3),
        create_checkin(7.5, True, 1.0)
    ]
    
    pattern = pattern_detection_agent.detect_deep_work_collapse(checkins)
    
    assert pattern is not None
    assert pattern.type == "deep_work_collapse"
    assert pattern.severity == "medium"
    assert pattern.data['avg_deep_work_hours'] < 1.5

def test_all_patterns_none_when_compliant():
    """Test no patterns detected when all compliant"""
    checkins = [
        create_checkin(7.5, True, 3, porn=True, compliance=100),
        create_checkin(8.0, True, 2.5, porn=True, compliance=100),
        create_checkin(7.2, True, 2.8, porn=True, compliance=100)
    ]
    
    patterns = pattern_detection_agent.detect_patterns(checkins)
    
    assert len(patterns) == 0
```

### Integration Tests

**File:** `tests/integration/test_phase2_flow.py`

```python
import pytest
from src.agents.supervisor import supervisor_agent
from src.agents.checkin_agent import checkin_agent
from src.agents.pattern_detection import pattern_detection_agent
from src.agents.intervention import intervention_agent

@pytest.mark.asyncio
async def test_checkin_with_ai_feedback():
    """Test complete check-in flow with AI feedback"""
    # TODO: Implement
    pass

@pytest.mark.asyncio
async def test_pattern_detection_to_intervention():
    """Test pattern detection triggers intervention"""
    # TODO: Implement
    pass

@pytest.mark.asyncio
async def test_supervisor_intent_routing():
    """Test supervisor routes messages correctly"""
    # TODO: Implement
    pass
```

### Manual Testing Checklist

**AI Feedback Quality:**
- [ ] Complete perfect check-in (100%) → verify feedback celebrates streak
- [ ] Complete low check-in (40%) → verify feedback identifies issues
- [ ] Complete partial check-in (80%) → verify feedback is balanced
- [ ] First-time user check-in → verify feedback welcomes and guides
- [ ] Broken streak check-in → verify feedback acknowledges reset

**Pattern Detection:**
- [ ] Create 3 low-sleep check-ins → verify sleep degradation detected
- [ ] Create 3 missed training → verify training abandonment detected
- [ ] Create 3 porn violations → verify porn relapse detected
- [ ] Create 3 low compliance → verify compliance decline detected
- [ ] Create 5 low deep work → verify deep work collapse detected

**Interventions:**
- [ ] Verify intervention sent within 5 seconds of detection
- [ ] Verify intervention references constitution principle
- [ ] Verify intervention provides specific action
- [ ] Verify intervention logged in Firestore
- [ ] Verify no duplicate interventions for same pattern

**Performance:**
- [ ] Check-in response time <5 seconds
- [ ] Pattern scan completes <30 seconds (with 10+ users)
- [ ] Token usage <1000 per check-in

**Cost:**
- [ ] Daily cost <$0.02
- [ ] Vertex AI usage tracked
- [ ] No unexpected API calls

---

## Success Criteria

### Functional Requirements

**F1: Intent Classification**
- [ ] Supervisor classifies intent >90% accuracy
- [ ] `/checkin` → routed to CheckIn agent
- [ ] Emotional messages → routed to Emotional agent
- [ ] Questions → routed to Query agent
- [ ] Commands → routed to Command handler

**F2: AI Feedback**
- [ ] Feedback mentions user's streak
- [ ] Feedback notes patterns (improving/declining/consistent)
- [ ] Feedback references constitution principle
- [ ] Feedback provides actionable guidance
- [ ] No generic responses ("Good job!" without context)

**F3: Pattern Detection**
- [ ] All 5 patterns detected correctly
- [ ] No false positives (requires 3+ occurrences)
- [ ] Pattern data includes evidence
- [ ] Patterns detected within 6 hours of occurrence

**F4: Interventions**
- [ ] Intervention sent within 5 seconds of detection
- [ ] Intervention has all 5 components (alert, evidence, constitution, consequence, action)
- [ ] Intervention logged in Firestore
- [ ] No duplicate interventions

**F5: Scheduled Scanning**
- [ ] Cloud Scheduler job runs every 6 hours
- [ ] Pattern scan endpoint secured (requires header)
- [ ] Scan completes successfully
- [ ] Results logged

### Performance Requirements

**P1: Response Time**
- [ ] Intent classification <2 seconds
- [ ] AI feedback generation <3 seconds
- [ ] Total check-in flow <5 seconds
- [ ] Pattern scan <30 seconds for 50 users

**P2: Token Usage**
- [ ] Intent classification <100 tokens
- [ ] Check-in feedback <700 tokens
- [ ] Intervention generation <800 tokens
- [ ] Pattern scan <500 tokens per user

**P3: Reliability**
- [ ] AI generation success rate >95%
- [ ] Fallback feedback works if API fails
- [ ] No crashes or unhandled exceptions

### Cost Requirements

**C1: Daily Cost**
- [ ] Gemini API <$0.01/day
- [ ] Total Phase 2 <$0.02/day
- [ ] Combined Phase 1+2 <$0.03/day

**C2: Monthly Cost**
- [ ] Phase 2 <$0.60/month
- [ ] Total system <$1/month

**C3: Monitoring**
- [ ] Vertex AI costs tracked
- [ ] Token usage logged
- [ ] Budget alert set ($1/month)

### Quality Requirements

**Q1: Feedback Quality**
- [ ] Personalized (mentions user-specific data)
- [ ] Relevant (addresses actual issues)
- [ ] Actionable (provides specific guidance)
- [ ] Consistent (tone matches constitution)

**Q2: Intervention Quality**
- [ ] Clear (user understands problem)
- [ ] Evidence-based (shows data)
- [ ] Principled (references constitution)
- [ ] Actionable (provides ONE specific step)

**Q3: Code Quality**
- [ ] All code has docstrings
- [ ] Type hints throughout
- [ ] Error handling implemented
- [ ] Logging for debugging

---

## Risks & Mitigations

### R1: Token Costs Exceed Budget

**Risk Level:** High  
**Impact:** Budget overrun, need to reduce functionality

**Mitigation:**
1. Implement prompt caching (saves 60% on input tokens)
2. Monitor token usage daily
3. Set up Vertex AI budget alerts ($0.02/day threshold)
4. Optimize prompts (reduce unnecessary context)
5. Batch operations where possible

**Contingency:**
- If cost >$0.03/day for 3 days → reduce scan frequency to 12 hours
- If cost >$0.05/day → disable scheduled scanning, keep on-demand only

---

### R2: AI Feedback is Generic/Unhelpful

**Risk Level:** Medium  
**Impact:** Users don't value AI feedback, Phase 2 doesn't deliver ROI

**Mitigation:**
1. Iterate on prompts with real check-ins
2. A/B test different prompt styles
3. Add more user context to prompts
4. Tune temperature (0.7-0.9)
5. Collect user feedback

**Contingency:**
- Implement feedback rating system (`/rate feedback`)
- If rating <70% → revert to Phase 1 hardcoded feedback
- Continue iterating on prompts offline

---

### R3: Pattern Detection False Positives

**Risk Level:** Medium  
**Impact:** Users annoyed by incorrect interventions, trust eroded

**Mitigation:**
1. Require 3+ occurrences for all patterns
2. Test with historical data
3. Add pattern confidence scores
4. Log all detections for analysis
5. Allow users to dismiss false positives

**Contingency:**
- If >20% interventions marked as false positives → increase thresholds
- Add cooldown period (don't send same pattern intervention within 24 hours)

---

### R4: Cloud Scheduler Fails

**Risk Level:** Low  
**Impact:** Patterns not detected between check-ins

**Mitigation:**
1. Monitor Cloud Scheduler job status
2. Set up alert if job fails 3+ times
3. Implement retry logic in endpoint
4. Run on-demand scan after each check-in (backup)

**Contingency:**
- Manual trigger available: `POST /trigger/pattern-scan` (with auth)
- If scheduler unreliable → move to scheduled Cloud Function

---

### R5: Gemini API Rate Limits

**Risk Level:** Low  
**Impact:** API calls fail, features unavailable

**Mitigation:**
1. Implement exponential backoff
2. Add retry logic (3 attempts)
3. Cache results where appropriate
4. Use fallback responses

**Contingency:**
- If rate limit hit → fall back to Phase 1 hardcoded responses
- Queue API calls and process in batches

---

## Rollout Plan

### Phase 2.0: Soft Launch (Days 1-3)

**Goal:** Deploy AI feedback only, no pattern detection yet

**Steps:**
1. Deploy Phase 2 code to Cloud Run
2. Enable Supervisor + CheckIn agent only
3. Pattern detection disabled (commented out)
4. Monitor token usage and costs
5. Collect feedback quality data

**Success Criteria:**
- ✅ AI feedback working for all check-ins
- ✅ Token usage <$0.01/day
- ✅ No errors in logs
- ✅ Feedback quality validated

**Rollback Plan:**
- If errors >5% → revert to Phase 1 (hardcoded feedback)
- If cost >$0.02/day → disable AI, investigate

---

### Phase 2.1: Pattern Detection (Days 4-5)

**Goal:** Enable pattern detection and interventions

**Steps:**
1. Enable pattern detection in code
2. Run on-demand scan after each check-in
3. Monitor for false positives
4. Validate intervention quality
5. Test with 3-5 users

**Success Criteria:**
- ✅ Patterns detected correctly
- ✅ Interventions sent successfully
- ✅ No false positives
- ✅ Users acknowledge interventions

**Rollback Plan:**
- If false positives >20% → increase thresholds
- If interventions not helpful → iterate on prompts

---

### Phase 2.2: Scheduled Scanning (Days 6-7)

**Goal:** Enable Cloud Scheduler for proactive detection

**Steps:**
1. Create Cloud Scheduler job
2. Enable `/trigger/pattern-scan` endpoint
3. Run first scheduled scan manually
4. Monitor scan results
5. Verify interventions sent

**Success Criteria:**
- ✅ Scheduler job runs every 6 hours
- ✅ Scan completes successfully
- ✅ Patterns detected and interventions sent
- ✅ Cost within budget

**Rollback Plan:**
- If scheduler unreliable → disable, use on-demand only
- If cost spike → reduce frequency to 12 hours

---

### Phase 2.3: Full Production (Week 2)

**Goal:** Monitor and optimize for 7 days

**Activities:**
1. Monitor token usage daily
2. Analyze intervention effectiveness
3. Tune pattern detection thresholds
4. Optimize prompts for token reduction
5. Collect user feedback

**Optimization Targets:**
- Reduce token usage by 20% (prompt caching)
- Improve feedback quality score >80%
- Zero false positive interventions

**Next Steps:**
- Phase 3: Reports + Dashboard
- Phase 4: Emotional Processing Agent

---

## Appendices

### Appendix A: Prompt Templates

**See:** `PHASE2_PROMPTS.md`

---

### Appendix B: API Documentation

**See:** `PHASE2_API.md`

---

### Appendix C: Architecture Diagrams

**See:** `PHASE2_ARCHITECTURE.md`

---

### Appendix D: Cost Calculator

**Gemini 2.0 Flash Pricing:**
- Input: $0.00025 per 1K tokens
- Output: $0.001 per 1K tokens

**Monthly Cost Formula:**
```
Monthly Cost = (Daily Operations × 30) + Fixed Costs

Daily Operations:
- Intent Classification: 3 × $0.000025 = $0.000075
- Check-In Feedback: 1 × $0.001625 = $0.001625
- Pattern Scans: 4 × $0.0001 = $0.0004
- Interventions: 0.5 × $0.00035 = $0.000175

Daily Total: $0.002275

Monthly Gemini: $0.002275 × 30 = $0.068

Fixed Costs:
- Cloud Scheduler: $0.10/month

Phase 2 Total: $0.17/month
```

---

**END OF SPECIFICATION**

---

**Document Version:** 1.0  
**Last Updated:** February 1, 2026  
**Status:** Ready for Implementation  
**Approved By:** Constitution Agent Team  
**Next Review:** After Phase 2 completion
