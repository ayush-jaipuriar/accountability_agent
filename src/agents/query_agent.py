"""
Query Agent - Natural Language Data Queries
============================================

Phase 3E: Handles user queries about their historical data.

**Purpose:**
Users want to ask questions like:
- "What's my average compliance this month?"
- "When did I last miss training?"
- "Show me my longest streak"

Without the Query Agent, users would need to:
1. Open dashboard (requires context switch)
2. Manually filter date ranges
3. Calculate stats themselves

With Query Agent: Just ask in natural language, get instant answer.

**Architecture:**
1. Classify query intent (what data user wants)
2. Fetch relevant data from Firestore
3. Generate natural language response using Gemini

**Query Types Supported:**
- compliance_average: Average compliance over time period
- streak_info: Current/longest streak information
- training_history: Workout completion history
- sleep_trends: Sleep hours analysis
- pattern_frequency: How often patterns are detected
- goal_progress: Career goal tracking progress

Key Concepts:
-------------
1. **Intent Classification**: Use LLM to understand what user is asking
   - "what's my" → wants a stat
   - "when did" → wants historical event
   - "show me" → wants data visualization/summary

2. **Data Aggregation**: Fetch and compute stats
   - Average: mean([values])
   - Count: len([items matching criteria])
   - Percentiles: Compare to other users

3. **Natural Language Generation**: Convert numbers → human-readable
   - Input: {"avg_compliance": 87, "days": 26}
   - Output: "Your average compliance this month is 87% over 26 days."
"""

import logging
import json
from typing import Optional, Dict, List, Any
from datetime import datetime, timedelta
from statistics import mean

from src.services.firestore_service import firestore_service
from src.services.llm_service import LLMService
from src.models.schemas import Tier1NonNegotiables, DailyCheckIn, User
from src.agents.state import ConstitutionState

logger = logging.getLogger(__name__)


class QueryAgent:
    """
    Handles natural language queries about user data (Phase 3E).
    
    **Process Flow:**
    1. Receive query via LangGraph state
    2. Classify query intent using Gemini
    3. Fetch relevant data from Firestore
    4. Generate natural language response
    5. Return updated state with response
    
    **Example Interaction:**
    User: "What's my average compliance this month?"
    
    Step 1: Classify → "compliance_average"
    Step 2: Fetch → {avg: 87%, days: 26, perfect: 12}
    Step 3: Generate → "Your average compliance this month is 87%.
                       Breakdown: Days tracked: 26/31, 100% days: 12..."
    
    **Integration:**
    - Supervisor routes messages with query keywords to QueryAgent
    - QueryAgent returns response in state.response
    - Main application sends response via Telegram
    """
    
    def __init__(self, project_id: str, location: str = "us-central1", model_name: str = "gemini-2.0-flash-exp"):
        """
        Initialize Query Agent.
        
        Args:
            project_id: GCP project ID for Vertex AI
            location: Vertex AI location (default: us-central1)
            model_name: Gemini model name
        """
        self.llm = LLMService(
            project_id=project_id,
            location=location,
            model_name=model_name
        )
        logger.info("✅ Query Agent initialized")
    
    async def process(self, state: ConstitutionState) -> ConstitutionState:
        """
        Process user query and generate response.
        
        **Workflow:**
        1. Classify query intent (what type of data they want)
        2. Fetch relevant data from Firestore
        3. Generate natural language response using Gemini
        4. Return state with response field populated
        
        Args:
            state: Current LangGraph state
            
        Returns:
            Updated state with response
        """
        try:
            user_id = state["user_id"]
            query = state["message"]
            
            logger.info(f"📊 Processing query from user {user_id}: '{query}'")
            
            # Step 1: Classify query intent
            query_type = await self._classify_query(query)
            logger.info(f"📋 Query classified as: {query_type}")
            
            # Step 2: Fetch relevant data
            data = await self._fetch_query_data(query_type, user_id)
            logger.info(f"📦 Fetched data for {query_type}: {len(str(data))} chars")
            
            # Step 3: Generate natural language response
            response = await self._generate_response(
                query=query,
                query_type=query_type,
                data=data,
                user_id=user_id
            )
            
            logger.info(f"✅ Generated query response ({len(response)} chars) for user {user_id}")
            
            # Update state
            state["response"] = response
            state["next_action"] = "send_message"
            
            return state
            
        except Exception as e:
            logger.error(f"❌ Query processing failed: {e}", exc_info=True)
            
            # Fallback response
            state["response"] = (
                "❌ Sorry, I couldn't process your query right now.\n\n"
                "Try using commands instead:\n"
                "• /weekly - Last 7 days stats\n"
                "• /monthly - Last 30 days stats\n"
                "• /status - Current streak and stats"
            )
            state["next_action"] = "send_message"
            state["error"] = str(e)
            
            return state
    
    async def _classify_query(self, message: str) -> str:
        """
        Classify query intent using Gemini.
        
        **Classification Categories:**
        - compliance_average: Questions about average/overall compliance
        - streak_info: Questions about streaks (longest, current, etc.)
        - training_history: Questions about workout history
        - sleep_trends: Questions about sleep patterns
        - pattern_frequency: Questions about detected patterns
        - goal_progress: Questions about career/goal progress
        - unknown: Can't classify (fallback)
        
        **Why Use LLM for Classification:**
        Users ask questions in many ways:
        - "What's my average compliance?" → compliance_average
        - "How am I doing overall?" → compliance_average (same intent, different words!)
        - "Show me workout stats" → training_history
        - "When did I miss training?" → training_history
        
        Pattern matching would require dozens of rules.
        LLM understands semantic meaning naturally.
        
        Args:
            message: User's query text
            
        Returns:
            Query type string (one of 7 categories)
        """
        try:
            prompt = f"""Classify this user query into ONE category.

User query: "{message}"

Categories:
- compliance_average: Questions about average/overall compliance, performance, how they're doing
- streak_info: Questions about streaks (longest, current, when started, etc.)
- training_history: Questions about workout history, training frequency, last missed workout
- sleep_trends: Questions about sleep patterns, sleep hours, sleep quality
- pattern_frequency: Questions about detected patterns, violations, constitution failures
- goal_progress: Questions about career goals, June 2026 targets, progress tracking
- unknown: Can't classify or not a data query

**Examples:**
- "What's my average compliance this month?" → compliance_average
- "How am I doing?" → compliance_average
- "Show me my longest streak" → streak_info
- "When did I last miss training?" → training_history
- "How much am I sleeping?" → sleep_trends
- "How often do I get sleep degradation?" → pattern_frequency
- "Am I on track for June goals?" → goal_progress
- "Hello how are you?" → unknown

**Return ONLY the category name (no explanation).**

Category:"""

            response = await self.llm.generate_text(
                prompt=prompt,
                max_output_tokens=30,  # Very short response (just category name)
                temperature=0.1  # Low temperature for consistent classification
            )
            
            category = response.strip().lower()
            
            # Validate category
            valid_categories = [
                "compliance_average", "streak_info", "training_history",
                "sleep_trends", "pattern_frequency", "goal_progress", "unknown"
            ]
            
            if category in valid_categories:
                return category
            else:
                logger.warning(f"⚠️ Invalid category returned: {category}, defaulting to unknown")
                return "unknown"
                
        except Exception as e:
            logger.error(f"❌ Query classification failed: {e}")
            return "unknown"
    
    async def _fetch_query_data(self, query_type: str, user_id: str) -> Dict[str, Any]:
        """
        Fetch relevant data from Firestore based on query type.
        
        **Data Sources:**
        - User profile: Streak data, career mode, settings
        - Check-ins: Historical check-in records (7, 30, or 90 days)
        - Patterns: Detected violation patterns
        
        Args:
            query_type: Classification from _classify_query
            user_id: User ID to fetch data for
            
        Returns:
            Dictionary with relevant data for query type
        """
        try:
            user = firestore_service.get_user(user_id)
            
            if query_type == "compliance_average":
                # Fetch last 30 days of check-ins
                checkins = firestore_service.get_recent_checkins(user_id, days=30)
                
                if not checkins:
                    return {"error": "No check-ins found in last 30 days"}
                
                return {
                    "avg_compliance": mean([c.compliance_score for c in checkins]),
                    "days_tracked": len(checkins),
                    "total_days": 30,
                    "perfect_days": sum(1 for c in checkins if c.compliance_score == 100),
                    "good_days": sum(1 for c in checkins if 80 <= c.compliance_score < 100),
                    "poor_days": sum(1 for c in checkins if c.compliance_score < 80),
                    "trend": self._calculate_compliance_trend(checkins)
                }
            
            elif query_type == "streak_info":
                return {
                    "current_streak": user.streaks.current_streak,
                    "longest_streak": user.streaks.longest_streak,
                    "total_checkins": user.streaks.total_checkins,
                    "last_checkin_date": user.streaks.last_checkin_date,
                    "is_record": user.streaks.current_streak >= user.streaks.longest_streak,
                    "days_to_record": max(0, user.streaks.longest_streak - user.streaks.current_streak + 1)
                }
            
            elif query_type == "training_history":
                # Fetch last 30 days
                checkins = firestore_service.get_recent_checkins(user_id, days=30)
                
                if not checkins:
                    return {"error": "No training data found"}
                
                # Find last missed training day
                last_missed = None
                for c in reversed(checkins):
                    if not c.tier1_non_negotiables.training:
                        last_missed = c.date
                        break
                
                # Calculate training frequency
                training_days = sum(1 for c in checkins if c.tier1_non_negotiables.training)
                
                # Recent 7 days for detail
                recent_7 = checkins[-7:] if len(checkins) >= 7 else checkins
                recent_detail = [
                    {
                        "date": c.date,
                        "trained": c.tier1_non_negotiables.training,
                        "is_rest_day": c.tier1_non_negotiables.is_rest_day
                    }
                    for c in recent_7
                ]
                
                return {
                    "training_days": training_days,
                    "total_days": len(checkins),
                    "consistency_pct": (training_days / len(checkins)) * 100,
                    "last_missed": last_missed,
                    "recent_7_days": recent_detail,
                    "current_week_count": sum(1 for d in recent_detail[-7:] if d["trained"])
                }
            
            elif query_type == "sleep_trends":
                # Fetch last 30 days
                checkins = firestore_service.get_recent_checkins(user_id, days=30)
                
                if not checkins:
                    return {"error": "No sleep data found"}
                
                sleep_hours = [c.tier1_non_negotiables.sleep_hours 
                              for c in checkins 
                              if c.tier1_non_negotiables.sleep_hours is not None]
                
                if not sleep_hours:
                    return {"error": "No sleep hours tracked"}
                
                return {
                    "avg_sleep": mean(sleep_hours),
                    "min_sleep": min(sleep_hours),
                    "max_sleep": max(sleep_hours),
                    "days_tracked": len(sleep_hours),
                    "days_above_target": sum(1 for h in sleep_hours if h >= 7),
                    "days_below_target": sum(1 for h in sleep_hours if h < 7),
                    "target": 7.0,
                    "trend": self._calculate_sleep_trend(sleep_hours)
                }
            
            elif query_type == "pattern_frequency":
                # Fetch patterns from last 90 days
                patterns = firestore_service.get_patterns(user_id, days=90)
                
                if not patterns:
                    return {"patterns": [], "message": "No patterns detected in last 90 days! 🎉"}
                
                # Count by pattern type
                pattern_counts = {}
                for pattern in patterns:
                    pattern_type = pattern.pattern_name
                    pattern_counts[pattern_type] = pattern_counts.get(pattern_type, 0) + 1
                
                # Find most common pattern
                most_common = max(pattern_counts.items(), key=lambda x: x[1]) if pattern_counts else None
                
                return {
                    "total_patterns": len(patterns),
                    "pattern_counts": pattern_counts,
                    "most_common": most_common,
                    "days_analyzed": 90,
                    "patterns_per_month": len(patterns) / 3  # 90 days = ~3 months
                }
            
            elif query_type == "goal_progress":
                # Fetch career-related data
                checkins = firestore_service.get_recent_checkins(user_id, days=30)
                
                if not checkins:
                    return {"error": "No check-in data found"}
                
                # Calculate skill building consistency
                skill_building_days = sum(
                    1 for c in checkins 
                    if c.tier1_non_negotiables.skill_building
                )
                
                return {
                    "career_mode": user.career_mode,
                    "skill_building_days": skill_building_days,
                    "total_days": len(checkins),
                    "consistency_pct": (skill_building_days / len(checkins)) * 100,
                    "target_date": "June 2026",
                    "target_salary": "₹28-42 LPA",
                    "current_month": datetime.now().strftime("%B %Y")
                }
            
            else:
                # Unknown query type
                return {"error": "Could not understand your query"}
                
        except Exception as e:
            logger.error(f"❌ Data fetch failed for {query_type}: {e}", exc_info=True)
            return {"error": str(e)}
    
    async def _generate_response(
        self,
        query: str,
        query_type: str,
        data: Dict[str, Any],
        user_id: str
    ) -> str:
        """
        Generate natural language response from data.
        
        **Goal:** Convert raw numbers into human-readable, encouraging response.
        
        **Response Structure:**
        1. Direct answer to question
        2. Breakdown with specific numbers
        3. Context (percentile, trend, comparison)
        4. Encouragement or suggestion
        
        **Why Use LLM:**
        - Numbers → Natural language ("87%" → "a strong 87%")
        - Context-aware phrasing ("top 20%" vs "room for improvement")
        - Encouraging tone without being generic
        - Handles edge cases (no data, partial data)
        
        Args:
            query: Original user question
            query_type: Classification result
            data: Fetched data dictionary
            user_id: User ID (for logging)
            
        Returns:
            Natural language response string
        """
        try:
            # Handle error cases
            if "error" in data:
                return f"📊 {data['error']}\n\nTry /status for current stats."
            
            # Build prompt for Gemini
            prompt = f"""Generate a helpful response to this user query.

**User Query:** "{query}"

**Query Type:** {query_type}

**Data:**
{json.dumps(data, indent=2)}

**Task:** Generate a concise, helpful response (max 200 words).

**Requirements:**
1. Answer the question directly
2. Include specific numbers from data
3. Add context (percentiles, trends, comparisons)
4. End with encouragement or actionable suggestion
5. Use emojis sparingly (1-2 only)
6. Format with markdown for readability

**Response Style:**
- Friendly but data-focused
- Specific (use actual numbers, not vague terms)
- Encouraging without being generic
- Actionable (suggest next steps if relevant)

**Examples of Good Responses:**

Query: "What's my average compliance?"
Response: "📊 Your average compliance this month is 87%.

Breakdown:
• Days tracked: 26/31
• 100% days: 12
• 80-99% days: 10
• <80% days: 4

You're in the top 20% of users! 🎯"

Query: "When did I last miss training?"
Response: "Your last missed training session was 3 days ago (Feb 4).

Recent training:
• Feb 7 ✅ Workout
• Feb 6 ✅ Workout  
• Feb 5 ✅ Rest day
• Feb 4 ❌ Missed
• Feb 3 ✅ Workout

Consistency: 80% this week (4/5 workout days)"

**Your Response:**"""

            response = await self.llm.generate_text(
                prompt=prompt,
                max_output_tokens=800,  # ~200 words
                temperature=0.7  # Moderate creativity
            )
            
            return response.strip()
            
        except Exception as e:
            logger.error(f"❌ Response generation failed: {e}", exc_info=True)
            
            # Ultra-simple fallback
            return f"📊 Data retrieved for {query_type}. See /status for more details."
    
    def _calculate_compliance_trend(self, checkins: List[DailyCheckIn]) -> str:
        """
        Calculate compliance trend (improving, stable, declining).
        
        Algorithm:
        - Compare first half vs second half of period
        - If second half > first half by 5%+ → improving
        - If second half < first half by 5%+ → declining
        - Otherwise → stable
        
        Args:
            checkins: List of check-ins (ordered by date)
            
        Returns:
            "improving", "stable", or "declining"
        """
        if len(checkins) < 6:
            return "stable"  # Need at least 6 days to detect trend
        
        midpoint = len(checkins) // 2
        first_half = checkins[:midpoint]
        second_half = checkins[midpoint:]
        
        first_avg = mean([c.compliance_score for c in first_half])
        second_avg = mean([c.compliance_score for c in second_half])
        
        diff = second_avg - first_avg
        
        if diff >= 5:
            return "improving"
        elif diff <= -5:
            return "declining"
        else:
            return "stable"
    
    def _calculate_sleep_trend(self, sleep_hours: List[float]) -> str:
        """
        Calculate sleep trend (improving, stable, declining).
        
        Similar to compliance trend but for sleep hours.
        Threshold: 0.5 hours difference
        
        Args:
            sleep_hours: List of sleep hours
            
        Returns:
            "improving", "stable", or "declining"
        """
        if len(sleep_hours) < 6:
            return "stable"
        
        midpoint = len(sleep_hours) // 2
        first_avg = mean(sleep_hours[:midpoint])
        second_avg = mean(sleep_hours[midpoint:])
        
        diff = second_avg - first_avg
        
        if diff >= 0.5:
            return "improving"
        elif diff <= -0.5:
            return "declining"
        else:
            return "stable"


# Factory function for getting agent instance
_query_agent_instance = None

def get_query_agent(project_id: str) -> QueryAgent:
    """
    Get singleton QueryAgent instance.
    
    Why Singleton?
    - LLM client initialization is expensive
    - Reuse same instance across requests
    - Maintains connection pool
    
    Args:
        project_id: GCP project ID
        
    Returns:
        QueryAgent instance
    """
    global _query_agent_instance
    
    if _query_agent_instance is None:
        _query_agent_instance = QueryAgent(project_id)
        logger.info("✅ Created QueryAgent singleton instance")
    
    return _query_agent_instance
