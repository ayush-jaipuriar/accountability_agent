"""
Debug Intent Classification

See exactly what Gemini is returning for intent classification.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from src.services.llm_service import get_llm_service, reset_llm_service
from src.config import settings

async def debug_intent():
    """Test intent classification and see raw responses"""
    print("\n" + "="*60)
    print("🔍 Debug Intent Classification")
    print("="*60)
    
    reset_llm_service()
    llm = get_llm_service(
        project_id=settings.gcp_project_id,
        location=settings.vertex_ai_location,
        model_name=settings.gemini_model
    )
    
    test_cases = [
        "I want to check in",
        "I'm feeling lonely",
        "What's my streak?",
        "/help"
    ]
    
    for message in test_cases:
        print(f"\n📝 Message: '{message}'")
        print("-" * 60)
        
        prompt = f"""Classify user intent: "{message}"

Options: checkin, emotional, query, command

Respond with ONLY ONE WORD:"""
        
        print(f"Prompt:\n{prompt}\n")
        
        # Try without max_output_tokens limit
        try:
            response = await llm.generate_text(
                prompt=prompt,
                max_output_tokens=8192,  # Use model's max
                temperature=0.1
            )
        except Exception as e:
            print(f"❌ Error: {e}")
            continue
        
        print(f"✅ Raw Response: '{response}'")
        print(f"   Length: {len(response)} chars")
        print(f"   Cleaned: '{response.strip().lower()}'")

if __name__ == "__main__":
    asyncio.run(debug_intent())
