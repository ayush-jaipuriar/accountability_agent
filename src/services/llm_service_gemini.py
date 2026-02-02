"""
LLM Service - Direct Gemini API (Alternative to Vertex AI)

This is an alternative implementation that uses the direct Gemini API
instead of Vertex AI. It's simpler and works with just an API key.

Key Differences from Vertex AI approach:
- Simpler: Just need an API key (no GCP project setup)
- Faster setup: No need to enable Vertex AI features
- Same functionality: Still uses Gemini models
- Different package: Uses google.generativeai instead of vertexai

Usage:
------
1. Get API key from https://makersuite.google.com/app/apikey
2. Add to .env: GEMINI_API_KEY=your_key_here
3. Use this service instead of llm_service.py
"""

import google.generativeai as genai
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class GeminiLLMService:
    """
    Wrapper for direct Gemini API calls (not Vertex AI)
    
    Simpler alternative that works with just an API key.
    """
    
    def __init__(self, api_key: str, model_name: str = "gemini-1.5-flash"):
        """
        Initialize Gemini API client
        
        Args:
            api_key: Gemini API key from Google AI Studio
            model_name: Model to use (gemini-1.5-flash, gemini-1.5-pro, etc.)
        """
        logger.info(f"Initializing Gemini API - Model: {model_name}")
        
        # Configure API key
        genai.configure(api_key=api_key)
        
        # Create model instance
        self.model = genai.GenerativeModel(model_name)
        self.model_name = model_name
        
        logger.info("Gemini API initialized successfully")
    
    async def generate_text(
        self,
        prompt: str,
        max_output_tokens: int = 200,
        temperature: float = 0.7,
        top_p: float = 0.95,
        top_k: int = 40
    ) -> str:
        """
        Generate text using Gemini
        
        Args:
            prompt: The prompt to send to the model
            max_output_tokens: Maximum response length
            temperature: Creativity level (0.0-1.0)
            top_p: Nucleus sampling threshold
            top_k: Top-k sampling
            
        Returns:
            Generated text response
        """
        try:
            # Count input tokens
            input_tokens = self._count_tokens(prompt)
            logger.info(f"Gemini API request - Input tokens: {input_tokens}")
            
            # Generate response (this is synchronous in the google.generativeai SDK)
            response = self.model.generate_content(
                prompt,
                generation_config=genai.GenerationConfig(
                    max_output_tokens=max_output_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    top_k=top_k
                )
            )
            
            # Extract text
            output_text = response.text
            output_tokens = self._count_tokens(output_text)
            
            # Calculate cost (same pricing as Vertex AI)
            input_cost = (input_tokens / 1_000_000) * 0.25
            output_cost = (output_tokens / 1_000_000) * 0.50
            total_cost = input_cost + output_cost
            
            logger.info(
                f"Gemini API response - Output tokens: {output_tokens}, "
                f"Cost: ${total_cost:.6f}"
            )
            
            return output_text
            
        except Exception as e:
            logger.error(f"Gemini API generation failed: {e}", exc_info=True)
            raise
    
    def _count_tokens(self, text: str) -> int:
        """Estimate token count"""
        return max(1, len(text) // 4)
    
    def get_model_info(self) -> dict:
        """Get model information"""
        return {
            "model_name": self.model_name,
            "api": "Direct Gemini API (not Vertex AI)",
            "pricing": {
                "input_tokens": "$0.25 per 1M tokens",
                "output_tokens": "$0.50 per 1M tokens"
            }
        }


# Global instance
_gemini_llm_service_instance: Optional[GeminiLLMService] = None


def get_gemini_llm_service(api_key: str, model_name: str = "gemini-1.5-flash") -> GeminiLLMService:
    """
    Get or create Gemini LLM service instance (singleton)
    
    Args:
        api_key: Gemini API key
        model_name: Model to use
        
    Returns:
        GeminiLLMService instance
    """
    global _gemini_llm_service_instance
    
    if _gemini_llm_service_instance is None:
        logger.info("Creating new GeminiLLMService instance (singleton)")
        _gemini_llm_service_instance = GeminiLLMService(api_key=api_key, model_name=model_name)
    else:
        logger.debug("Returning existing GeminiLLMService instance")
    
    return _gemini_llm_service_instance


def reset_gemini_llm_service():
    """Reset service instance (for testing)"""
    global _gemini_llm_service_instance
    _gemini_llm_service_instance = None
    logger.info("Gemini LLM service instance reset")
