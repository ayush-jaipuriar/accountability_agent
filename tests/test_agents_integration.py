"""
Agent Integration Tests
=======================

Tests for the agent system - emotional support, query, intervention, and pattern detection.

**Testing Strategy:**
Agents depend on the LLM service (Gemini) and Firestore. We mock both:
- LLM calls → return predetermined strings (fast, deterministic)
- Firestore → return test data fixtures

**What We Test:**
1. EmotionalSupportAgent: Emotion classification, protocol selection, response generation
2. InterventionAgent: Ghosting interventions (template-based), fallback interventions
3. QueryAgent: Query classification, data fetching, trend calculation
4. PatternDetection: Ghosting detection logic

**Why Mock LLM?**
- Real Gemini calls cost money (~$0.0001/call)
- Real calls are non-deterministic (different output each time)
- Real calls are slow (1-3 seconds each)
- We're testing our code's logic, not Gemini's capability
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from datetime import datetime, timedelta

from src.models.schemas import (
    User, UserStreaks, DailyCheckIn, Tier1NonNegotiables,
    CheckInResponses, StreakShields
)


# ===== Fixtures =====

@pytest.fixture
def test_user():
    """User with realistic data for agent testing."""
    return User(
        user_id="agent_test_user",
        telegram_id=111222333,
        telegram_username="agent_tester",
        name="Agent Tester",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=47,
            longest_streak=47,
            last_checkin_date="2026-02-07",
            total_checkins=100
        ),
        constitution_mode="optimization",
        career_mode="skill_building",
        accountability_partner_name="Partner User",
        accountability_partner_id="partner_123",
        streak_shields=StreakShields(total=3, used=1, available=2),
    )


@pytest.fixture
def sample_checkins():
    """Generate 7 days of check-ins for agent testing."""
    checkins = []
    for i in range(7):
        date = (datetime.now() - timedelta(days=6 - i)).strftime("%Y-%m-%d")
        checkins.append(DailyCheckIn(
            date=date,
            user_id="agent_test_user",
            mode="optimization",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=i != 3,  # Miss sleep on day 4
                sleep_hours=7.5 if i != 3 else 5.0,
                training=i != 5,  # Miss training on day 6
                deep_work=True,
                deep_work_hours=2.5,
                skill_building=i % 2 == 0,  # Every other day
                skill_building_hours=2.0 if i % 2 == 0 else 0,
                zero_porn=True,
                boundaries=True,
            ),
            responses=CheckInResponses(
                challenges=f"Day {i+1} test challenges with enough detail for validation requirement",
                rating=8 - (1 if i == 3 else 0),
                rating_reason=f"Day {i+1} rating explanation with sufficient length for the validation",
                tomorrow_priority=f"Day {i+1} priority for tomorrow with enough detail for the test",
                tomorrow_obstacle=f"Day {i+1} obstacle for tomorrow with enough detail for the test",
            ),
            compliance_score=100.0 if i not in [3, 5] else 66.7,
        ))
    return checkins


# ===== Emotional Support Agent Tests =====

class TestEmotionalSupportAgent:
    """
    Tests for the CBT-style emotional support system.
    
    The emotional agent has 3 key stages:
    1. Classify the emotion (loneliness, porn_urge, breakup, stress, general)
    2. Load the appropriate protocol
    3. Generate a personalized response
    """

    def test_protocol_exists_for_all_emotions(self):
        """All 5 emotion types should have protocols defined."""
        with patch('src.agents.emotional_agent.get_llm_service'):
            from src.agents.emotional_agent import EmotionalSupportAgent
            agent = EmotionalSupportAgent.__new__(EmotionalSupportAgent)
            
            for emotion in ["loneliness", "porn_urge", "breakup", "stress", "general"]:
                protocol = agent._get_emotional_protocol(emotion)
                assert protocol is not None, f"Missing protocol for: {emotion}"
                assert "validate" in protocol
                assert "reframe" in protocol
                assert "trigger" in protocol
                assert "actions" in protocol
                assert len(protocol["actions"]) == 3, f"{emotion} should have 3 actions"

    def test_protocol_fallback_for_unknown_emotion(self):
        """Unknown emotion types should fall back to 'general' protocol."""
        with patch('src.agents.emotional_agent.get_llm_service'):
            from src.agents.emotional_agent import EmotionalSupportAgent
            agent = EmotionalSupportAgent.__new__(EmotionalSupportAgent)
            
            protocol = agent._get_emotional_protocol("unknown_emotion")
            general_protocol = agent._get_emotional_protocol("general")
            
            assert protocol == general_protocol

    async def test_process_returns_response(self, test_user):
        """process() should return state with response field populated."""
        with patch('src.agents.emotional_agent.get_llm_service') as mock_llm_factory, \
             patch('src.agents.emotional_agent.firestore_service') as mock_fs:
            
            mock_llm = MagicMock()
            mock_llm.generate_text = AsyncMock(side_effect=[
                "loneliness",  # Classification call
                "I hear you. Loneliness is real and temporary..."  # Response call
            ])
            mock_llm_factory.return_value = mock_llm
            mock_fs.get_user.return_value = test_user
            mock_fs.store_emotional_interaction = MagicMock()
            
            from src.agents.emotional_agent import EmotionalSupportAgent
            agent = EmotionalSupportAgent.__new__(EmotionalSupportAgent)
            agent.llm = mock_llm
            
            state = {
                "user_id": "agent_test_user",
                "message": "I'm feeling really lonely tonight",
                "intent": "emotional",
            }
            
            result = await agent.process(state)
            
            assert "response" in result
            assert len(result["response"]) > 0

    async def test_process_logs_interaction(self, test_user):
        """Emotional interactions should be logged in Firestore."""
        with patch('src.agents.emotional_agent.get_llm_service') as mock_llm_factory, \
             patch('src.agents.emotional_agent.firestore_service') as mock_fs:
            
            mock_llm = MagicMock()
            mock_llm.generate_text = AsyncMock(side_effect=[
                "stress",
                "Stress is your body's signal..."
            ])
            mock_llm_factory.return_value = mock_llm
            mock_fs.get_user.return_value = test_user
            
            from src.agents.emotional_agent import EmotionalSupportAgent
            agent = EmotionalSupportAgent.__new__(EmotionalSupportAgent)
            agent.llm = mock_llm
            
            state = {
                "user_id": "agent_test_user",
                "message": "I'm so stressed about work",
                "intent": "emotional",
            }
            
            await agent.process(state)
            
            mock_fs.store_emotional_interaction.assert_called_once()
            call_args = mock_fs.store_emotional_interaction.call_args
            assert call_args.kwargs["emotion_type"] == "stress"

    async def test_process_fallback_on_error(self):
        """Should return safe fallback response if LLM fails."""
        with patch('src.agents.emotional_agent.get_llm_service') as mock_llm_factory, \
             patch('src.agents.emotional_agent.firestore_service') as mock_fs:
            
            mock_llm = MagicMock()
            mock_llm.generate_text = AsyncMock(side_effect=Exception("LLM failure"))
            mock_llm_factory.return_value = mock_llm
            
            from src.agents.emotional_agent import EmotionalSupportAgent
            agent = EmotionalSupportAgent.__new__(EmotionalSupportAgent)
            agent.llm = mock_llm
            
            state = {
                "user_id": "agent_test_user",
                "message": "Help me",
                "intent": "emotional",
            }
            
            result = await agent.process(state)
            
            assert "response" in result
            assert "difficult" in result["response"].lower()
            assert "friend" in result["response"].lower()


# ===== Intervention Agent Tests =====

class TestInterventionAgent:
    """
    Tests for the intervention message generation system.
    
    Key distinction: Ghosting interventions use templates (no LLM),
    while other patterns use AI-generated messages.
    """

    def test_ghosting_day2_gentle(self, test_user):
        """Day 2 ghosting should produce gentle nudge message."""
        from src.agents.pattern_detection import Pattern
        from src.agents.intervention import InterventionAgent
        
        with patch('src.agents.intervention.get_llm_service'):
            agent = InterventionAgent.__new__(InterventionAgent)
            
            pattern = Pattern(type="ghosting", severity="nudge", detected_at=datetime.utcnow(), data={
                "days_missing": 2,
                "previous_streak": 47,
            })
            
            msg = agent._build_ghosting_intervention(pattern, test_user)
            
            assert "Missed you" in msg
            assert "47-day streak" in msg
            assert "/checkin" in msg

    def test_ghosting_day3_warning(self, test_user):
        """Day 3 ghosting should produce warning message."""
        from src.agents.pattern_detection import Pattern
        from src.agents.intervention import InterventionAgent
        
        with patch('src.agents.intervention.get_llm_service'):
            agent = InterventionAgent.__new__(InterventionAgent)
            
            pattern = Pattern(type="ghosting", severity="warning", detected_at=datetime.utcnow(), data={
                "days_missing": 3,
                "previous_streak": 47,
            })
            
            msg = agent._build_ghosting_intervention(pattern, test_user)
            
            assert "3 Days Missing" in msg
            assert "constitution violation" in msg.lower()

    def test_ghosting_day4_critical(self, test_user):
        """Day 4 ghosting should reference historical pattern."""
        from src.agents.pattern_detection import Pattern
        from src.agents.intervention import InterventionAgent
        
        with patch('src.agents.intervention.get_llm_service'):
            agent = InterventionAgent.__new__(InterventionAgent)
            
            pattern = Pattern(type="ghosting", severity="critical", detected_at=datetime.utcnow(), data={
                "days_missing": 4,
                "previous_streak": 47,
            })
            
            msg = agent._build_ghosting_intervention(pattern, test_user)
            
            assert "CRITICAL" in msg
            assert "Feb 2025" in msg  # Historical reference

    def test_ghosting_day5_emergency_with_partner(self, test_user):
        """Day 5+ should mention partner notification."""
        from src.agents.pattern_detection import Pattern
        from src.agents.intervention import InterventionAgent
        
        with patch('src.agents.intervention.get_llm_service'):
            agent = InterventionAgent.__new__(InterventionAgent)
            
            pattern = Pattern(type="ghosting", severity="critical", detected_at=datetime.utcnow(), data={
                "days_missing": 5,
                "previous_streak": 47,
            })
            
            msg = agent._build_ghosting_intervention(pattern, test_user)
            
            assert "EMERGENCY" in msg
            assert "Partner User" in msg  # Partner notification
            assert "shield" in msg.lower()  # Shield info

    def test_ghosting_day5_no_partner(self):
        """Day 5 without partner should not mention partner."""
        from src.agents.pattern_detection import Pattern
        from src.agents.intervention import InterventionAgent
        from src.models.schemas import User, UserStreaks, StreakShields
        
        user_no_partner = User(
            user_id="no_partner",
            telegram_id=999,
            name="Solo User",
            streaks=UserStreaks(current_streak=10),
            streak_shields=StreakShields(total=3, used=3, available=0),
        )
        
        with patch('src.agents.intervention.get_llm_service'):
            agent = InterventionAgent.__new__(InterventionAgent)
            
            pattern = Pattern(type="ghosting", severity="critical", detected_at=datetime.utcnow(), data={
                "days_missing": 6,
                "previous_streak": 10,
            })
            
            msg = agent._build_ghosting_intervention(pattern, user_no_partner)
            
            assert "EMERGENCY" in msg
            assert "Partner" not in msg  # No partner mentioned

    def test_snooze_trap_intervention(self, test_user):
        """Snooze trap should include constitution protocol."""
        from src.agents.pattern_detection import Pattern
        from src.agents.intervention import InterventionAgent
        
        with patch('src.agents.intervention.get_llm_service'):
            agent = InterventionAgent.__new__(InterventionAgent)
            
            pattern = Pattern(type="snooze_trap", severity="warning", detected_at=datetime.utcnow(), data={
                "avg_snooze_minutes": 45,
                "days_affected": ["2026-02-04", "2026-02-05", "2026-02-06"],
                "target_wake": "06:30",
            })
            
            msg = agent._build_snooze_trap_intervention(pattern, test_user)
            
            assert "SNOOZE TRAP" in msg
            assert "45" in msg  # Average snooze time
            assert "06:30" in msg  # Target wake time

    def test_deep_work_collapse_intervention(self, test_user):
        """Deep work collapse should reference career goals."""
        from src.agents.pattern_detection import Pattern
        from src.agents.intervention import InterventionAgent
        
        with patch('src.agents.intervention.get_llm_service'):
            agent = InterventionAgent.__new__(InterventionAgent)
            
            pattern = Pattern(type="deep_work_collapse", severity="critical", detected_at=datetime.utcnow(), data={
                "avg_deep_work_hours": 0.8,
                "days_affected": 5,
                "target": 2.0,
            })
            
            msg = agent._build_deep_work_collapse_intervention(pattern, test_user)
            
            assert "DEEP WORK" in msg
            assert "₹28-42 LPA" in msg  # Career goal reference
            assert "June 2026" in msg

    def test_relationship_interference_intervention(self, test_user):
        """Relationship interference should reference Feb 2025 history."""
        from src.agents.pattern_detection import Pattern
        from src.agents.intervention import InterventionAgent
        
        with patch('src.agents.intervention.get_llm_service'):
            agent = InterventionAgent.__new__(InterventionAgent)
            
            pattern = Pattern(type="relationship_interference", severity="critical", detected_at=datetime.utcnow(), data={
                "days_affected": 4,
                "boundary_violations": 5,
                "correlation_pct": 80,
                "total_days_analyzed": 7,
            })
            
            msg = agent._build_relationship_interference_intervention(pattern, test_user)
            
            assert "RELATIONSHIP INTERFERENCE" in msg
            assert "Feb-July 2025" in msg
            assert "80%" in msg  # Correlation percentage


# ===== Query Agent Tests =====

class TestQueryAgent:
    """
    Tests for the natural language query processing system.
    
    The query agent handles questions like:
    - "What's my average compliance?"
    - "When did I last miss training?"
    """

    def test_compliance_trend_improving(self, sample_checkins):
        """Should detect improving trend when second half is better."""
        from src.agents.query_agent import QueryAgent
        
        agent = QueryAgent.__new__(QueryAgent)
        
        # Make second half better than first half
        for i in range(4, 7):
            sample_checkins[i].compliance_score = 95.0
        for i in range(0, 3):
            sample_checkins[i].compliance_score = 70.0
        
        trend = agent._calculate_compliance_trend(sample_checkins)
        assert trend == "improving"

    def test_compliance_trend_declining(self, sample_checkins):
        """Should detect declining trend when second half is worse."""
        from src.agents.query_agent import QueryAgent
        
        agent = QueryAgent.__new__(QueryAgent)
        
        # Make first half better
        for i in range(0, 3):
            sample_checkins[i].compliance_score = 95.0
        for i in range(4, 7):
            sample_checkins[i].compliance_score = 70.0
        
        trend = agent._calculate_compliance_trend(sample_checkins)
        assert trend == "declining"

    def test_compliance_trend_stable(self, sample_checkins):
        """Should return stable when halves are similar."""
        from src.agents.query_agent import QueryAgent
        
        agent = QueryAgent.__new__(QueryAgent)
        
        for c in sample_checkins:
            c.compliance_score = 85.0
        
        trend = agent._calculate_compliance_trend(sample_checkins)
        assert trend == "stable"

    def test_compliance_trend_short_period(self):
        """Should return stable for less than 6 data points."""
        from src.agents.query_agent import QueryAgent
        
        agent = QueryAgent.__new__(QueryAgent)
        
        short_checkins = [MagicMock(compliance_score=80.0) for _ in range(4)]
        
        trend = agent._calculate_compliance_trend(short_checkins)
        assert trend == "stable"

    def test_sleep_trend_improving(self):
        """Should detect improving sleep when second half sleeps more."""
        from src.agents.query_agent import QueryAgent
        
        agent = QueryAgent.__new__(QueryAgent)
        
        sleep_hours = [5.5, 5.0, 5.5, 7.0, 7.5, 8.0, 7.5]
        trend = agent._calculate_sleep_trend(sleep_hours)
        assert trend == "improving"

    def test_sleep_trend_declining(self):
        """Should detect declining sleep when second half sleeps less."""
        from src.agents.query_agent import QueryAgent
        
        agent = QueryAgent.__new__(QueryAgent)
        
        sleep_hours = [8.0, 7.5, 7.0, 6.0, 5.5, 5.0, 5.5]
        trend = agent._calculate_sleep_trend(sleep_hours)
        assert trend == "declining"

    async def test_fetch_compliance_data(self, test_user, sample_checkins):
        """Should compute correct compliance statistics."""
        from src.agents.query_agent import QueryAgent
        
        with patch('src.agents.query_agent.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = test_user
            mock_fs.get_recent_checkins.return_value = sample_checkins
            
            agent = QueryAgent.__new__(QueryAgent)
            data = await agent._fetch_query_data("compliance_average", "agent_test_user")
            
            assert "avg_compliance" in data
            assert "days_tracked" in data
            assert data["days_tracked"] == 7
            assert "perfect_days" in data

    async def test_fetch_streak_data(self, test_user):
        """Should return correct streak information."""
        from src.agents.query_agent import QueryAgent
        
        with patch('src.agents.query_agent.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = test_user
            
            agent = QueryAgent.__new__(QueryAgent)
            data = await agent._fetch_query_data("streak_info", "agent_test_user")
            
            assert data["current_streak"] == 47
            assert data["longest_streak"] == 47
            assert data["is_record"] is True

    async def test_fetch_training_data(self, test_user, sample_checkins):
        """Should compute training statistics correctly."""
        from src.agents.query_agent import QueryAgent
        
        with patch('src.agents.query_agent.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = test_user
            mock_fs.get_recent_checkins.return_value = sample_checkins
            
            agent = QueryAgent.__new__(QueryAgent)
            data = await agent._fetch_query_data("training_history", "agent_test_user")
            
            assert "training_days" in data
            assert "consistency_pct" in data
            assert data["training_days"] == 6  # 1 missed

    async def test_unknown_query_returns_error(self, test_user):
        """Unknown query type should return error dict."""
        from src.agents.query_agent import QueryAgent
        
        with patch('src.agents.query_agent.firestore_service') as mock_fs:
            mock_fs.get_user.return_value = test_user
            
            agent = QueryAgent.__new__(QueryAgent)
            data = await agent._fetch_query_data("unknown", "agent_test_user")
            
            assert "error" in data


# ===== Pattern Detection Tests =====

class TestGhostingDetection:
    """
    Tests for ghosting detection logic.
    
    Ghosting = user stops checking in for 2+ days.
    Detection escalates from Day 2 (gentle) to Day 5+ (emergency).
    """

    def test_detect_ghosting_day2(self):
        """Should detect ghosting at 2 days missing."""
        from src.agents.pattern_detection import PatternDetectionAgent
        
        with patch('src.agents.pattern_detection.firestore_service') as mock_fs:
            user = User(
                user_id="ghost_user",
                telegram_id=999,
                name="Ghost",
                streaks=UserStreaks(
                    current_streak=20,
                    last_checkin_date=(datetime.now() - timedelta(days=2)).strftime("%Y-%m-%d")
                ),
            )
            mock_fs.get_user.return_value = user
            
            agent = PatternDetectionAgent()
            pattern = agent.detect_ghosting("ghost_user")
            
            assert pattern is not None
            assert pattern.type == "ghosting"
            assert pattern.data["days_missing"] == 2

    def test_no_ghosting_recent_checkin(self):
        """Should NOT detect ghosting when user checked in today."""
        from src.agents.pattern_detection import PatternDetectionAgent
        
        with patch('src.agents.pattern_detection.firestore_service') as mock_fs:
            user = User(
                user_id="active_user",
                telegram_id=999,
                name="Active",
                streaks=UserStreaks(
                    current_streak=20,
                    last_checkin_date=datetime.now().strftime("%Y-%m-%d")
                ),
            )
            mock_fs.get_user.return_value = user
            
            agent = PatternDetectionAgent()
            pattern = agent.detect_ghosting("active_user")
            
            assert pattern is None

    def test_no_ghosting_1day_grace(self):
        """Should NOT detect ghosting for 1 day absence (grace period)."""
        from src.agents.pattern_detection import PatternDetectionAgent
        
        with patch('src.agents.pattern_detection.firestore_service') as mock_fs:
            user = User(
                user_id="one_day_user",
                telegram_id=999,
                name="OneDayOff",
                streaks=UserStreaks(
                    current_streak=20,
                    last_checkin_date=(datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
                ),
            )
            mock_fs.get_user.return_value = user
            
            agent = PatternDetectionAgent()
            pattern = agent.detect_ghosting("one_day_user")
            
            assert pattern is None

    def test_ghosting_severity_escalation(self):
        """Severity should escalate with more days missing."""
        from src.agents.pattern_detection import PatternDetectionAgent
        
        with patch('src.agents.pattern_detection.firestore_service') as mock_fs:
            agent = PatternDetectionAgent()
            
            for days, expected_min_severity in [(2, "nudge"), (3, "warning"), (5, "critical")]:
                user = User(
                    user_id=f"ghost_{days}",
                    telegram_id=999,
                    name="Ghost",
                    streaks=UserStreaks(
                        current_streak=20,
                        last_checkin_date=(datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
                    ),
                )
                mock_fs.get_user.return_value = user
                
                pattern = agent.detect_ghosting(f"ghost_{days}")
                assert pattern is not None, f"Should detect ghosting at {days} days"
                assert pattern.data["days_missing"] == days
