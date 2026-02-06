"""
Quick test to verify thinking_budget=0 works with google-genai SDK
"""
import os
from google import genai
from google.genai import types

# Set environment for Vertex AI
os.environ["GOOGLE_CLOUD_PROJECT"] = "accountability-agent"
os.environ["GOOGLE_CLOUD_LOCATION"] = "asia-south1"
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

print("Testing ThinkingConfig with thinking_budget=0...")

try:
    client = genai.Client()
    
    config = types.GenerateContentConfig(
        temperature=0.7,
        max_output_tokens=100,
        thinking_config=types.ThinkingConfig(
            thinking_budget=0  # Disable thinking
        )
    )
    
    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents="What is 2+2?",
        config=config
    )
    
    print(f"✅ SUCCESS! Response: {response.text}")
    
    if hasattr(response, 'usage_metadata') and response.usage_metadata:
        print(f"Prompt tokens: {response.usage_metadata.prompt_token_count}")
        print(f"Output tokens: {response.usage_metadata.candidates_token_count}")
        # Check for thinking tokens
        if hasattr(response.usage_metadata, 'thoughts_token_count'):
            print(f"Thinking tokens: {response.usage_metadata.thoughts_token_count}")
        else:
            print("No thinking_token_count attribute (good - thinking disabled)")
    
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()
