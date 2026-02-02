"""
Test CheckIn Agent Feedback Generation

Simple test script to verify AI feedback works.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.agents.checkin_agent import get_checkin_agent, reset_checkin_agent
from src.models.schemas import Tier1NonNegotiables
from src.config import settings


async def test_perfect_compliance():
    """Test perfect 100% compliance feedback"""
    print("\n" + "="*60)
    print("TEST 1: Perfect Compliance (100%)")
    print("="*60)
    
    reset_checkin_agent()
    agent = get_checkin_agent(settings.gcp_project_id)
    
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        zero_porn=True,
        boundaries=True
    )
    
    feedback = await agent.generate_feedback(
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
    
    print("\n📝 FEEDBACK:")
    print("-" * 60)
    print(feedback)
    print("-" * 60)
    print(f"\n✅ Length: {len(feedback)} chars")
    print(f"✅ Estimated tokens: ~{len(feedback) // 4}")
    print(f"✅ Estimated cost: ${(len(feedback) // 4 / 1_000_000) * 0.50:.6f}")
    
    return feedback


async def test_good_compliance():
    """Test good 80% compliance feedback"""
    print("\n" + "="*60)
    print("TEST 2: Good Compliance (80%)")
    print("="*60)
    
    reset_checkin_agent()
    agent = get_checkin_agent(settings.gcp_project_id)
    
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=False,  # Missed
        zero_porn=True,
        boundaries=True
    )
    
    feedback = await agent.generate_feedback(
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
    
    print("\n📝 FEEDBACK:")
    print("-" * 60)
    print(feedback)
    print("-" * 60)
    print(f"\n✅ Length: {len(feedback)} chars")
    
    return feedback


async def test_milestone_streak():
    """Test 30-day milestone feedback"""
    print("\n" + "="*60)
    print("TEST 3: Milestone Streak (30 days - NEW RECORD!)")
    print("="*60)
    
    reset_checkin_agent()
    agent = get_checkin_agent(settings.gcp_project_id)
    
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        zero_porn=True,
        boundaries=True
    )
    
    feedback = await agent.generate_feedback(
        user_id="test_user",
        compliance_score=100,
        tier1=tier1,
        current_streak=30,  # Milestone!
        longest_streak=25,  # New record!
        self_rating=10,
        rating_reason="Hit 30 days! Longest streak ever",
        tomorrow_priority="Keep the momentum",
        tomorrow_obstacle="None - I'm in the zone"
    )
    
    print("\n📝 FEEDBACK:")
    print("-" * 60)
    print(feedback)
    print("-" * 60)
    print(f"\n✅ Length: {len(feedback)} chars")
    
    return feedback


async def main():
    """Run all tests"""
    print("\n" + "🚀"*30)
    print("   CheckIn Agent - AI Feedback Tests")
    print("🚀"*30)
    
    try:
        feedback1 = await test_perfect_compliance()
        feedback2 = await test_good_compliance()
        feedback3 = await test_milestone_streak()
        
        print("\n" + "="*60)
        print("✅ ALL TESTS PASSED!")
        print("="*60)
        print("\n📊 Summary:")
        print(f"   • Perfect compliance feedback: {len(feedback1)} chars")
        print(f"   • Good compliance feedback: {len(feedback2)} chars")
        print(f"   • Milestone streak feedback: {len(feedback3)} chars")
        print("\n🎉 CheckIn Agent is working perfectly!")
        print("\n✨ Next steps:")
        print("   1. Pattern Detection Agent")
        print("   2. Intervention Agent")
        print("   3. Deploy Phase 2 to production")
        print("="*60 + "\n")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
