"""
Test CheckIn Agent - AI Feedback Generation

Tests the AI-powered feedback generation for check-ins.
"""

import pytest
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.checkin_agent import get_checkin_agent, reset_checkin_agent
from src.models.schemas import Tier1NonNegotiables
from src.config import settings


@pytest.fixture
def checkin_agent():
    """Create fresh CheckIn agent for each test"""
    reset_checkin_agent()
    return get_checkin_agent(settings.gcp_project_id)


@pytest.mark.asyncio
async def test_perfect_compliance_feedback(checkin_agent):
    """
    Test feedback for perfect compliance (100%)
    
    Should include:
    - Strong praise
    - Streak reference
    - Constitution principle
    - Forward guidance
    """
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        zero_porn=True,
        boundaries=True
    )
    
    feedback = await checkin_agent.generate_feedback(
        user_id="test_user",
        compliance_score=100,
        tier1=tier1,
        current_streak=47,
        longest_streak=50,
        self_rating=9,
        rating_reason="Crushed all goals today. Felt focused and disciplined.",
        tomorrow_priority="Complete 3 LeetCode problems",
        tomorrow_obstacle="Late meeting might drain energy"
    )
    
    print(f"\n{'='*60}")
    print("PERFECT COMPLIANCE FEEDBACK (100%)")
    print('='*60)
    print(feedback)
    print('='*60)
    
    # Verify feedback quality
    assert len(feedback) > 100, "Feedback too short"
    assert len(feedback) < 1500, "Feedback too long"
    assert "47" in feedback or "streak" in feedback.lower(), "Should mention streak"
    assert "100" in feedback or "perfect" in feedback.lower() or "all" in feedback.lower(), "Should acknowledge perfect score"


@pytest.mark.asyncio
async def test_good_compliance_feedback(checkin_agent):
    """
    Test feedback for good compliance (80-99%)
    
    Should include:
    - Acknowledgment with what was missed
    - Streak reference
    - Constructive guidance
    """
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=False,  # Missed deep work
        zero_porn=True,
        boundaries=True
    )
    
    feedback = await checkin_agent.generate_feedback(
        user_id="test_user",
        compliance_score=80,
        tier1=tier1,
        current_streak=15,
        longest_streak=30,
        self_rating=7,
        rating_reason="Solid day but only got 1 hour of deep work due to meetings",
        tomorrow_priority="Block 9-11 AM for deep work",
        tomorrow_obstacle="Morning standup at 9:30"
    )
    
    print(f"\n{'='*60}")
    print("GOOD COMPLIANCE FEEDBACK (80%)")
    print('='*60)
    print(feedback)
    print('='*60)
    
    # Verify feedback quality
    assert len(feedback) > 100, "Feedback too short"
    assert "deep work" in feedback.lower() or "work" in feedback.lower(), "Should mention missed item"
    assert "15" in feedback or "streak" in feedback.lower(), "Should mention streak"


@pytest.mark.asyncio
async def test_struggling_compliance_feedback(checkin_agent):
    """
    Test feedback for struggling (<70%)
    
    Should include:
    - Direct acknowledgment of struggles
    - Specific guidance for improvement
    - Supportive but firm tone
    """
    tier1 = Tier1NonNegotiables(
        sleep=False,  # Missed
        training=False,  # Missed
        deep_work=True,
        zero_porn=True,
        boundaries=False  # Missed
    )
    
    feedback = await checkin_agent.generate_feedback(
        user_id="test_user",
        compliance_score=40,
        tier1=tier1,
        current_streak=3,
        longest_streak=10,
        self_rating=4,
        rating_reason="Rough day. Only got 5 hours sleep, missed workout, had argument with roommate",
        tomorrow_priority="Get full 8 hours sleep",
        tomorrow_obstacle="Late night gaming habit"
    )
    
    print(f"\n{'='*60}")
    print("STRUGGLING COMPLIANCE FEEDBACK (40%)")
    print('='*60)
    print(feedback)
    print('='*60)
    
    # Verify feedback quality
    assert len(feedback) > 100, "Feedback too short"
    assert any(word in feedback.lower() for word in ["sleep", "training", "boundaries"]), "Should mention missed items"
    assert "tomorrow" in feedback.lower() or "focus" in feedback.lower(), "Should give forward guidance"


@pytest.mark.asyncio
async def test_milestone_streak_feedback(checkin_agent):
    """
    Test feedback for milestone streak (30 days)
    
    Should include:
    - Celebration of milestone
    - Connection to consistency/systems
    """
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        zero_porn=True,
        boundaries=True
    )
    
    feedback = await checkin_agent.generate_feedback(
        user_id="test_user",
        compliance_score=100,
        tier1=tier1,
        current_streak=30,  # 30-day milestone!
        longest_streak=25,  # New record!
        self_rating=10,
        rating_reason="Hit 30 days! This is the longest streak I've ever maintained",
        tomorrow_priority="Keep the momentum",
        tomorrow_obstacle="None - I'm in the zone"
    )
    
    print(f"\n{'='*60}")
    print("MILESTONE STREAK FEEDBACK (30 days)")
    print('='*60)
    print(feedback)
    print('='*60)
    
    # Verify feedback quality
    assert len(feedback) > 100, "Feedback too short"
    # LLM may write "30" or spell out "thirty" - accept either
    assert "30" in feedback or "thirty" in feedback.lower(), "Should mention 30-day streak"
    assert any(word in feedback.lower() for word in ["milestone", "record", "momentum", "consistent", "streak"]), "Should celebrate milestone"


@pytest.mark.asyncio
async def test_feedback_references_user_input(checkin_agent):
    """
    Test that feedback references user's own words (rating reason, priorities)
    
    This verifies personalization.
    """
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        zero_porn=True,
        boundaries=True
    )
    
    specific_priority = "Finish Algorithm Design chapter 7"
    specific_obstacle = "Afternoon energy crash around 3 PM"
    
    feedback = await checkin_agent.generate_feedback(
        user_id="test_user",
        compliance_score=90,
        tier1=tier1,
        current_streak=12,
        longest_streak=20,
        self_rating=8,
        rating_reason="Great focus today on algorithms",
        tomorrow_priority=specific_priority,
        tomorrow_obstacle=specific_obstacle
    )
    
    print(f"\n{'='*60}")
    print("PERSONALIZATION TEST")
    print('='*60)
    print(feedback)
    print('='*60)
    
    # Check if feedback references user's specific inputs
    # (May not always include exact text, but should be contextually relevant)
    feedback_lower = feedback.lower()
    
    # Should reference either the priority or obstacle or both
    has_reference = (
        "algorithm" in feedback_lower or
        "chapter" in feedback_lower or
        "energy" in feedback_lower or
        "afternoon" in feedback_lower or
        "tomorrow" in feedback_lower  # At minimum should mention tomorrow
    )
    
    assert has_reference, "Feedback should reference user's stated priority or obstacle"


@pytest.mark.asyncio
async def test_feedback_token_cost(checkin_agent):
    """
    Test that feedback generation stays under token budget
    
    Target: <1000 tokens total (~$0.002 per check-in)
    """
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        zero_porn=True,
        boundaries=True
    )
    
    feedback = await checkin_agent.generate_feedback(
        user_id="test_user",
        compliance_score=85,
        tier1=tier1,
        current_streak=20,
        longest_streak=25,
        self_rating=8,
        rating_reason="Good day overall",
        tomorrow_priority="Focus on morning routine",
        tomorrow_obstacle="Early meeting"
    )
    
    # Rough token estimate: 1 token ≈ 4 characters
    estimated_output_tokens = len(feedback) // 4
    
    print(f"\n{'='*60}")
    print("TOKEN COST ANALYSIS")
    print('='*60)
    print(f"Feedback length: {len(feedback)} characters")
    print(f"Estimated output tokens: {estimated_output_tokens}")
    print(f"Estimated cost: ${(estimated_output_tokens / 1_000_000) * 0.50:.6f}")
    print('='*60)
    
    # Output should be roughly 150-250 words = 200-350 tokens
    assert estimated_output_tokens < 500, "Output too long (token budget exceeded)"


if __name__ == "__main__":
    """
    Run tests directly
    
    Usage:
    python -m pytest tests/test_checkin_agent.py -v -s
    """
    pytest.main([__file__, "-v", "-s"])
