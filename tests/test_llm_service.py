"""
Tests for src/services/llm_service.py
======================================
Comprehensive unit tests for Vertex AI LLMService wrapper.
"""

import os
import pytest
from unittest.mock import MagicMock, patch

from src.services.llm_service import (
    LLMService,
    get_llm_service,
    reset_llm_service,
)


@pytest.fixture(autouse=True)
def clean_llm_singleton():
    reset_llm_service()
    yield
    reset_llm_service()


@pytest.fixture
def mock_genai_client():
    with patch("src.services.llm_service.genai.Client") as mock_cls:
        client_instance = MagicMock()
        mock_cls.return_value = client_instance
        yield client_instance


class TestLLMServiceInit:

    def test_init_sets_environment_variables(self, mock_genai_client):
        service = LLMService(
            project_id="test-project",
            location="us-central1",
            model_name="gemini-2.5-flash-lite",
        )
        assert os.environ.get("GOOGLE_CLOUD_PROJECT") == "test-project"
        assert os.environ.get("GOOGLE_CLOUD_LOCATION") == "us-central1"
        assert os.environ.get("GOOGLE_GENAI_USE_VERTEXAI") == "True"
        assert service.model_name == "gemini-2.5-flash-lite"


class TestLLMServiceGenerateText:

    @pytest.mark.asyncio
    async def test_generate_text_success_with_thinking_budget_zero(self, mock_genai_client):
        service = LLMService("test-project")

        mock_response = MagicMock()
        mock_response.text = "Check-in processed successfully."
        mock_response.usage_metadata = MagicMock(
            prompt_token_count=20,
            candidates_token_count=10,
        )
        mock_genai_client.models.generate_content.return_value = mock_response

        result = await service.generate_text("Test prompt", temperature=0.5)

        assert result == "Check-in processed successfully."
        mock_genai_client.models.generate_content.assert_called_once()
        call_kwargs = mock_genai_client.models.generate_content.call_args[1]
        config = call_kwargs["config"]
        assert config.temperature == 0.5
        assert config.thinking_config.thinking_budget == 0

    @pytest.mark.asyncio
    async def test_generate_text_fallback_token_estimates_without_metadata(self, mock_genai_client):
        service = LLMService("test-project")

        mock_response = MagicMock()
        mock_response.text = "Fallback token response."
        mock_response.usage_metadata = None
        mock_genai_client.models.generate_content.return_value = mock_response

        result = await service.generate_text("Prompt without usage metadata")
        assert result == "Fallback token response."

    @pytest.mark.asyncio
    async def test_generate_text_empty_response_raises(self, mock_genai_client):
        service = LLMService("test-project")

        mock_response = MagicMock()
        mock_response.text = ""
        mock_response.candidates = []
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(ValueError, match="LLM returned empty response"):
            await service.generate_text("Empty prompt")

    @pytest.mark.asyncio
    async def test_generate_text_safety_block_raises(self, mock_genai_client):
        service = LLMService("test-project")

        mock_candidate = MagicMock()
        mock_candidate.finish_reason = 3  # SAFETY
        mock_response = MagicMock()
        mock_response.text = None
        mock_response.candidates = [mock_candidate]
        mock_genai_client.models.generate_content.return_value = mock_response

        with pytest.raises(ValueError, match="Response blocked by safety filters"):
            await service.generate_text("Unsafe prompt")

    @pytest.mark.asyncio
    async def test_generate_text_api_error_propagates(self, mock_genai_client):
        service = LLMService("test-project")
        mock_genai_client.models.generate_content.side_effect = RuntimeError("Vertex AI Quota Exceeded")

        with pytest.raises(RuntimeError, match="Vertex AI Quota Exceeded"):
            await service.generate_text("Error prompt")


class TestLLMServiceUtilities:

    def test_count_tokens_approximation(self, mock_genai_client):
        service = LLMService("test-project")
        assert service._count_tokens("abcd") == 1
        assert service._count_tokens("abcdefgh") == 2
        assert service._count_tokens("") == 1  # max(1, 0)

    def test_get_model_info(self, mock_genai_client):
        service = LLMService("test-project", model_name="gemini-2.5-flash-lite")
        info = service.get_model_info()
        assert info["model_name"] == "gemini-2.5-flash-lite"
        assert "pricing" in info
        assert "limits" in info


class TestLLMServiceSingleton:

    def test_get_llm_service_singleton(self, mock_genai_client):
        s1 = get_llm_service("proj-1")
        s2 = get_llm_service("proj-1")
        assert s1 is s2

        reset_llm_service()
        s3 = get_llm_service("proj-2")
        assert s3 is not s1
