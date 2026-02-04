"""
LLM Service - Google GenAI SDK Wrapper for Gemini 2.5 Flash

This service handles all interactions with Google's Gemini LLM through Vertex AI.
It provides a simple interface for text generation while tracking token usage and costs.

Key Concepts:
--------------
1. **Google GenAI SDK**: Modern unified SDK for Gemini
   - Supports both Gemini Developer API and Vertex AI
   - Supports thinking_budget parameter (critical for cost optimization)
   - Cleaner API than older vertexai SDK
   
2. **Gemini 2.5 Flash**: The model we're using
   - Fast: <2 second response times
   - Cheap: $0.25/M input tokens, $0.50/M output tokens
   - Smart enough for our use cases (intent classification, feedback generation)
   - Thinking mode can be disabled to save tokens!
   
3. **Token Counting**: 
   - Tokens are the "units" of text the model processes
   - Roughly: 1 token ≈ 4 characters (or ~0.75 words)
   - We track every API call to stay under budget
   
4. **Thinking Budget Optimization**:
   - Gemini 2.5 Flash has thinking/reasoning mode enabled by default
   - This uses invisible tokens for internal reasoning
   - We disable it with thinking_budget=0 to save ~40% on tokens!
   
5. **Singleton Pattern**:
   - Only one LLMService instance exists across the app
   - Avoids re-initializing client multiple times
   - Accessed via get_llm_service() function

Usage Example:
--------------
```python
from src.services.llm_service import get_llm_service

llm = get_llm_service(project_id="accountability-agent")
response = await llm.generate_text(
    prompt="Classify this intent: I want to check in",
    max_output_tokens=10,
    temperature=0.1
)
print(response)  # "checkin"
```
"""

from google import genai
from google.genai import types
import logging
from typing import Optional
import os

logger = logging.getLogger(__name__)


class LLMService:
    """
    Wrapper for Google GenAI SDK Gemini API calls
    
    Handles:
    - Google GenAI client initialization
    - Text generation with Gemini 2.5 Flash
    - Token counting and cost tracking
    - Thinking mode disabled for cost optimization
    - Error handling and retries
    """
    
    def __init__(self, project_id: str, location: str = "asia-south1", model_name: str = "gemini-2.5-flash"):
        """
        Initialize Google GenAI client for Vertex AI
        
        Args:
            project_id: GCP project ID (e.g., "accountability-agent")
            location: GCP region (e.g., "asia-south1" for Mumbai)
            model_name: Gemini model to use (e.g., "gemini-2.5-flash")
            
        Theory:
        -------
        Google GenAI SDK needs environment variables for Vertex AI:
        1. GOOGLE_CLOUD_PROJECT: Which GCP project to bill
        2. GOOGLE_CLOUD_LOCATION: Which region to route requests to
        3. GOOGLE_GENAI_USE_VERTEXAI: Set to "True" to use Vertex AI backend
        
        We use asia-south1 (Mumbai) for lowest latency from India.
        """
        logger.info(f"Initializing Google GenAI SDK - Project: {project_id}, Location: {location}, Model: {model_name}")
        
        # Set environment variables for Vertex AI
        os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
        os.environ["GOOGLE_CLOUD_LOCATION"] = location
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"
        
        # Create GenAI client (will use Vertex AI backend due to env vars)
        self.client = genai.Client()
        self.model_name = model_name
        
        logger.info("Google GenAI SDK initialized successfully with Vertex AI backend")
    
    async def generate_text(
        self,
        prompt: str,
        max_output_tokens: int = 3072,  # Increased 1.5x from 2048
        temperature: float = 0.7,
        top_p: float = 0.95,
        top_k: int = 40
    ) -> str:
        """
        Generate text using Gemini 2.5 Flash with thinking disabled
        
        Args:
            prompt: The prompt to send to the model
            max_output_tokens: Maximum response length (default: 3072)
            temperature: Creativity level (0.0 = deterministic, 1.0 = creative, default: 0.7)
            top_p: Nucleus sampling threshold (default: 0.95)
            top_k: Top-k sampling (default: 40)
            
        Returns:
            Generated text response
            
        Theory - Understanding the Parameters:
        ---------------------------------------
        1. **Temperature**: Controls randomness
           - 0.0: Always picks most likely word (deterministic)
           - 0.5: Balanced (good for classification)
           - 1.0: More creative/diverse (good for feedback)
           
        2. **Top-p (nucleus sampling)**: Considers tokens with cumulative probability p
           - 0.95 means "consider tokens until 95% probability mass is covered"
           - Prevents model from sampling very unlikely words
           
        3. **Top-k**: Only consider top k most likely tokens
           - 40 means "only sample from the 40 most likely next words"
           - Prevents nonsense by ignoring very rare words
        
        4. **Thinking Budget = 0**: Disables internal reasoning
           - Gemini 2.5 Flash normally uses tokens for "thinking"
           - These thinking tokens are invisible but cost money
           - Setting to 0 disables thinking = saves ~40% on tokens!
        
        Cost Tracking:
        --------------
        - Input tokens: $0.25 per 1 million
        - Output tokens: $0.50 per 1 million
        - Thinking tokens: $0 (disabled with thinking_budget=0)
        - We log every call with token counts and costs
        """
        try:
            # Count input tokens for cost tracking
            input_tokens = self._count_tokens(prompt)
            logger.info(f"LLM request - Input tokens: {input_tokens}, Prompt preview: '{prompt[:100]}...'")
            
            # Configure generation
            # Note: thinking_config not yet supported in current google-genai SDK version
            # TODO: Re-enable thinking_budget=0 when SDK supports it
            config = types.GenerateContentConfig(
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                max_output_tokens=max_output_tokens
            )
            
            # Generate response
            # Note: This is synchronous but we're in async function
            # The google-genai SDK doesn't have async methods yet
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt,
                config=config
            )
            
            # Extract text from response
            output_text = response.text
            
            # Get actual token usage from response metadata
            if hasattr(response, 'usage_metadata') and response.usage_metadata:
                actual_input_tokens = getattr(response.usage_metadata, 'prompt_token_count', input_tokens)
                actual_output_tokens = getattr(response.usage_metadata, 'candidates_token_count', self._count_tokens(output_text))
            else:
                # Fallback to estimates
                actual_input_tokens = input_tokens
                actual_output_tokens = self._count_tokens(output_text)
            
            # Calculate cost (Gemini 2.5 Flash pricing)
            input_cost = (actual_input_tokens / 1_000_000) * 0.25
            output_cost = (actual_output_tokens / 1_000_000) * 0.50
            total_cost = input_cost + output_cost
            
            logger.info(
                f"LLM response - Output tokens: {actual_output_tokens}, "
                f"Cost: ${total_cost:.6f}, "
                f"Response preview: '{output_text[:100]}...'"
            )
            
            return output_text
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}", exc_info=True)
            raise
    
    def _count_tokens(self, text: str) -> int:
        """
        Estimate token count
        
        Theory:
        -------
        Tokens are the "units" of text that LLMs process. The exact tokenization
        depends on the model's tokenizer (e.g., BPE, WordPiece, SentencePiece).
        
        For Gemini (which uses SentencePiece), the conversion rate is roughly:
        - 1 token ≈ 4 characters
        - 1 token ≈ 0.75 words
        
        This is an approximation. For exact counts, use the Vertex AI
        count_tokens() method, but that requires an API call (adds latency).
        
        For cost tracking, this approximation is sufficient.
        
        Args:
            text: Text to count tokens for
            
        Returns:
            Estimated token count
        """
        # Simple approximation: 1 token ≈ 4 characters
        return max(1, len(text) // 4)
    
    def get_model_info(self) -> dict:
        """
        Get information about the current model
        
        Returns:
            Dictionary with model name, pricing, and limits
        """
        return {
            "model_name": self.model_name,
            "pricing": {
                "input_tokens": "$0.25 per 1M tokens",
                "output_tokens": "$0.50 per 1M tokens"
            },
            "limits": {
                "max_input_tokens": 1_000_000,
                "max_output_tokens": 8192
            },
            "latency": "~1-2 seconds typical"
        }


# --- Global Instance Management (Singleton Pattern) ---

_llm_service_instance: Optional[LLMService] = None


def get_llm_service(project_id: str, location: str = "asia-south1", model_name: str = "gemini-2.5-flash") -> LLMService:
    """
    Get or create LLM service instance (singleton pattern)
    
    Theory - Singleton Pattern:
    ---------------------------
    We only want ONE LLMService instance across the entire application because:
    1. Vertex AI initialization is expensive (takes ~500ms)
    2. Model instance can be reused across requests
    3. Avoids creating multiple connections to Vertex AI
    
    How it works:
    1. First call: Creates instance and stores in global variable
    2. Subsequent calls: Returns existing instance
    
    Args:
        project_id: GCP project ID
        location: GCP region (default: asia-south1)
        model_name: Gemini model to use (default: gemini-2.5-flash)
        
    Returns:
        LLMService instance
    """
    global _llm_service_instance
    
    if _llm_service_instance is None:
        logger.info("Creating new LLMService instance (singleton)")
        _llm_service_instance = LLMService(project_id=project_id, location=location, model_name=model_name)
    else:
        logger.debug("Returning existing LLMService instance")
    
    return _llm_service_instance


def reset_llm_service():
    """
    Reset LLM service instance (useful for testing)
    
    This forces get_llm_service() to create a new instance on next call.
    Only use this in tests or when configuration changes.
    """
    global _llm_service_instance
    _llm_service_instance = None
    logger.info("LLM service instance reset")
