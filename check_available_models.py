"""
Check Available Gemini Models in Vertex AI

This script lists all available Gemini models in your GCP project
to help diagnose which model names and versions are accessible.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from google.cloud import aiplatform
from src.config import settings

def check_available_models():
    """List available models in Vertex AI"""
    print("\n" + "="*60)
    print("🔍 Checking Available Gemini Models")
    print("="*60)
    
    print(f"\n📝 Configuration:")
    print(f"   Project: {settings.gcp_project_id}")
    print(f"   Region: {settings.vertex_ai_location}")
    
    # Try different regions
    regions_to_check = [
        settings.vertex_ai_location,  # Current region from config
        "us-central1",  # Most reliable region for Gemini
        "us-east1",
        "europe-west1",
        "asia-northeast1"
    ]
    
    print(f"\n🌍 Checking model availability across regions...")
    
    for region in regions_to_check:
        print(f"\n📍 Region: {region}")
        print("-" * 40)
        
        try:
            # Initialize Vertex AI for this region
            aiplatform.init(project=settings.gcp_project_id, location=region)
            
            # Try to list models
            # Note: Vertex AI doesn't have a direct "list models" API
            # So we'll try to access specific models
            
            models_to_try = [
                "gemini-1.5-pro",
                "gemini-1.5-flash",
                "gemini-1.0-pro",
                "gemini-pro",
                "gemini-pro-vision"
            ]
            
            available_models = []
            
            for model_name in models_to_try:
                try:
                    from vertexai.generative_models import GenerativeModel
                    model = GenerativeModel(model_name)
                    # If we can create the model object, it's likely available
                    available_models.append(model_name)
                    print(f"   ✅ {model_name} - Available")
                except Exception as e:
                    if "not found" in str(e).lower():
                        print(f"   ❌ {model_name} - Not found")
                    else:
                        print(f"   ⚠️  {model_name} - Error: {str(e)[:50]}...")
            
            if available_models:
                print(f"\n   ✨ {len(available_models)} model(s) available in {region}")
            else:
                print(f"   ⚠️  No models available in {region}")
                
        except Exception as e:
            print(f"   ❌ Error checking {region}: {e}")
    
    print("\n" + "="*60)
    print("\n💡 Recommendations:")
    print("   1. Use the region where models are available")
    print("   2. Update VERTEX_AI_LOCATION in .env file")
    print("   3. Update GEMINI_MODEL to an available model name")
    print("\n" + "="*60)

if __name__ == "__main__":
    try:
        check_available_models()
    except Exception as e:
        print(f"\n❌ Script failed: {e}")
        import traceback
        traceback.print_exc()
