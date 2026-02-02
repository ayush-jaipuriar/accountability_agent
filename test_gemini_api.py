"""
Test Direct Gemini API (Alternative to Vertex AI)

This script tests the direct Gemini API using an API key.
This is simpler than Vertex AI and should work immediately.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.services.llm_service_gemini import get_gemini_llm_service, reset_gemini_llm_service
from src.agents.state import create_initial_state
from src.config import settings


async def test_gemini_api():
    """Test direct Gemini API"""
    print("\n" + "="*60)
    print("🧪 Testing Direct Gemini API")
    print("="*60)
    
    # Check if API key exists
    if not settings.gemini_api_key:
        print("\n❌ GEMINI_API_KEY not found in .env file")
        print("   Please add: GEMINI_API_KEY=your_key_here")
        return False
    
    print(f"\n✅ API key found (length: {len(settings.gemini_api_key)})")
    
    try:
        # Reset any existing instance
        reset_gemini_llm_service()
        
        # Create Gemini service
        gemini = get_gemini_llm_service(
            api_key=settings.gemini_api_key,
            model_name="gemini-1.5-flash"
        )
        
        print(f"\n✅ Gemini API initialized")
        print(f"   Model: gemini-1.5-flash")
        
        # Test basic generation
        print(f"\n🔄 Testing text generation...")
        response = await gemini.generate_text(
            prompt="Say 'Hello' in one word.",
            max_output_tokens=10,
            temperature=0.1
        )
        
        print(f"✅ Gemini Response: '{response}'")
        
        # Test intent classification
        print(f"\n🔄 Testing intent classification...")
        
        test_messages = [
            ("I want to check in", "checkin"),
            ("I'm feeling lonely", "emotional"),
            ("What's my streak?", "query"),
            ("/help", "command")
        ]
        
        results = []
        for message, expected in test_messages:
            prompt = f"""Classify user intent: "{message}"

Options: checkin, emotional, query, command

Respond with ONE WORD only:"""
            
            intent = await gemini.generate_text(
                prompt=prompt,
                max_output_tokens=10,
                temperature=0.1
            )
            
            intent = intent.strip().lower()
            is_correct = intent == expected
            results.append(is_correct)
            
            emoji = "✅" if is_correct else "❌"
            print(f"  {emoji} '{message}' → {intent} (expected: {expected})")
        
        # Calculate accuracy
        accuracy = (sum(results) / len(results)) * 100
        print(f"\n📊 Accuracy: {accuracy}% ({sum(results)}/{len(results)})")
        
        if accuracy >= 75:
            print(f"\n🎉 Direct Gemini API is working great!")
            return True
        else:
            print(f"\n⚠️  Accuracy lower than expected")
            return False
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run test"""
    print("\n" + "🚀"*30)
    print("   Direct Gemini API Test")
    print("🚀"*30)
    
    success = await test_gemini_api()
    
    print("\n" + "="*60)
    if success:
        print("✅ SUCCESS! Direct Gemini API is working!")
        print("\nNext steps:")
        print("1. This API key approach is simpler than Vertex AI")
        print("2. We can use this for Phase 2 implementation")
        print("3. Ready to build CheckIn Agent with AI feedback!")
    else:
        print("❌ Test failed - check error messages above")
    print("="*60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
