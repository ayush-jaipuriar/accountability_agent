"""
Basic LLM Service Test Script

This is a simple script to test if the LLM service can connect to Vertex AI
and perform basic intent classification.

Run this before the full test suite to catch environment/setup issues.

Usage:
    python test_llm_basic.py
"""

import asyncio
import sys
import os

# Add src to path
sys.path.insert(0, os.path.dirname(__file__))

from src.services.llm_service import get_llm_service, reset_llm_service
from src.agents.supervisor import get_supervisor_agent, reset_supervisor_agent
from src.agents.state import create_initial_state
from src.config import settings


async def test_llm_connection():
    """Test basic LLM service connection"""
    print("\n" + "="*60)
    print("🧪 Testing LLM Service Connection")
    print("="*60)
    
    try:
        # Reset any existing instances
        reset_llm_service()
        
        # Create LLM service
        llm = get_llm_service(
            project_id=settings.gcp_project_id,
            location=settings.vertex_ai_location,
            model_name=settings.gemini_model
        )
        
        print(f"\n✅ LLM Service initialized")
        print(f"   Project: {settings.gcp_project_id}")
        print(f"   Location: {settings.vertex_ai_location}")
        print(f"   Model: {settings.gemini_model}")
        
        # Test basic generation
        print(f"\n🔄 Testing text generation...")
        response = await llm.generate_text(
            prompt="Respond with just the word: Hello",
            max_output_tokens=50,  # Increased from 10
            temperature=0.1
        )
        
        print(f"✅ LLM Response: '{response}'")
        print(f"\n✅ LLM Service is working correctly!")
        return True
        
    except Exception as e:
        print(f"\n❌ LLM Service test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_intent_classification():
    """Test intent classification with Supervisor agent"""
    print("\n" + "="*60)
    print("🧪 Testing Intent Classification")
    print("="*60)
    
    try:
        # Reset supervisor
        reset_supervisor_agent()
        
        # Create supervisor
        supervisor = get_supervisor_agent(project_id=settings.gcp_project_id)
        
        print(f"\n✅ Supervisor Agent initialized")
        
        # Test cases
        test_messages = [
            ("I want to check in", "checkin"),
            ("I'm feeling lonely today", "emotional"),
            ("What's my streak?", "query"),
            ("/help", "command")
        ]
        
        print(f"\n🔄 Testing intent classification on {len(test_messages)} messages...")
        
        results = []
        for message, expected_intent in test_messages:
            print(f"\n  Testing: '{message}'")
            
            # Create state
            state = create_initial_state(
                user_id="test_user",
                message=message,
                message_id=1
            )
            
            # Classify intent
            result = await supervisor.classify_intent(state)
            
            classified_intent = result["intent"]
            is_correct = classified_intent == expected_intent
            
            emoji = "✅" if is_correct else "❌"
            print(f"  {emoji} Expected: {expected_intent}, Got: {classified_intent}")
            
            results.append(is_correct)
        
        # Calculate accuracy
        correct = sum(results)
        total = len(results)
        accuracy = (correct / total) * 100
        
        print(f"\n📊 Accuracy: {accuracy}% ({correct}/{total} correct)")
        
        if accuracy >= 75:
            print(f"\n✅ Intent classification is working well!")
            return True
        else:
            print(f"\n⚠️  Accuracy is lower than expected (expected >= 75%)")
            return False
        
    except Exception as e:
        print(f"\n❌ Intent classification test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all basic tests"""
    print("\n" + "🚀"*30)
    print("   PHASE 2 - LangGraph Foundation Tests")
    print("🚀"*30)
    
    print(f"\n📝 Configuration:")
    print(f"   Environment: {settings.environment}")
    print(f"   GCP Project: {settings.gcp_project_id}")
    print(f"   GCP Region: {settings.gcp_region}")
    print(f"   Vertex AI Location: {settings.vertex_ai_location}")
    print(f"   Gemini Model: {settings.gemini_model}")
    
    # Run tests
    llm_ok = await test_llm_connection()
    
    if llm_ok:
        intent_ok = await test_intent_classification()
    else:
        print("\n⚠️  Skipping intent classification test (LLM service failed)")
        intent_ok = False
    
    # Summary
    print("\n" + "="*60)
    print("📊 Test Summary")
    print("="*60)
    print(f"   LLM Service Connection: {'✅ PASS' if llm_ok else '❌ FAIL'}")
    print(f"   Intent Classification: {'✅ PASS' if intent_ok else '❌ FAIL'}")
    
    if llm_ok and intent_ok:
        print(f"\n🎉 All tests passed! Phase 2 foundation is working!")
        print(f"\n✨ Next steps:")
        print(f"   1. Run full test suite: pytest tests/test_intent_classification.py -v -s")
        print(f"   2. Build CheckIn Agent with AI feedback")
        print(f"   3. Implement Pattern Detection Agent")
    else:
        print(f"\n❌ Some tests failed. Please fix issues before continuing.")
        print(f"\n🔍 Troubleshooting:")
        print(f"   1. Check .env file exists and has TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID")
        print(f"   2. Check service account key exists at: {settings.google_application_credentials}")
        print(f"   3. Verify Vertex AI API is enabled in GCP project")
        print(f"   4. Check network connectivity to Vertex AI API")
    
    print("\n" + "="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
