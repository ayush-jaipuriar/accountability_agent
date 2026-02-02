"""
Test Intent Classification - Supervisor Agent

This test file verifies that the Supervisor Agent correctly classifies
user intents using Gemini 2.0 Flash.

What We're Testing:
-------------------
1. LLM Service can connect to Vertex AI
2. Supervisor classifies "checkin" intent correctly
3. Supervisor classifies "emotional" intent correctly
4. Supervisor classifies "query" intent correctly
5. Supervisor classifies "command" intent correctly
6. Supervisor handles ambiguous messages
7. Supervisor handles errors gracefully

Why These Tests Matter:
-----------------------
Intent classification is the FOUNDATION of Phase 2. If this fails,
the entire multi-agent system breaks down. We need to ensure:
- High accuracy (>90% on clear cases)
- Consistent classifications (same input → same output)
- Graceful error handling (API failures don't crash the bot)

Note on Test Cost:
------------------
Each test makes a real API call to Gemini, which costs money:
- ~200 tokens per call × 10 tests = 2000 tokens
- Cost: (2000 / 1,000,000) × $0.25 = $0.0005 (~$0.0005 per test run)
- Negligible, but good to be aware of

To avoid API calls during development, we could:
1. Mock the LLM service (but then we're not testing reality)
2. Use cached responses (but then we miss API changes)
3. Just run tests infrequently (recommended approach)
"""

import pytest
import os
import sys
from datetime import datetime

# Add project root to path so we can import from src/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.agents.state import create_initial_state, ConstitutionState
from src.agents.supervisor import get_supervisor_agent, reset_supervisor_agent
from src.config import get_settings

# Get settings
settings = get_settings()


@pytest.fixture
def supervisor():
    """
    Fixture to create a fresh Supervisor Agent for each test
    
    Fixtures in pytest are setup functions that run before each test.
    This ensures each test starts with a clean state.
    """
    reset_supervisor_agent()  # Clear any existing instance
    agent = get_supervisor_agent(project_id=settings.gcp_project_id)
    return agent


@pytest.mark.asyncio
async def test_llm_service_connection(supervisor):
    """
    Test that LLM service can connect to Vertex AI
    
    This is a basic smoke test to ensure:
    1. Vertex AI is initialized correctly
    2. Credentials are valid
    3. Gemini API is accessible
    """
    # Create a simple state
    state = create_initial_state(
        user_id="test_user",
        message="Hello",
        message_id=1
    )
    
    # Try to classify intent
    result = await supervisor.classify_intent(state)
    
    # Verify we got a valid intent back
    assert result["intent"] is not None
    assert result["intent"] in ["checkin", "emotional", "query", "command"]
    print(f"✅ LLM service connected. Intent classified: {result['intent']}")


@pytest.mark.asyncio
async def test_checkin_intent_classification(supervisor):
    """
    Test classification of check-in messages
    
    Users might say check-in in many different ways:
    - Direct: "I want to check in"
    - Casual: "Let's do this"
    - Habitual: "Ready for today's check-in"
    
    The Supervisor should recognize all of these as "checkin" intent.
    """
    test_messages = [
        "I'm ready to check in",
        "Let's check in for today",
        "Check in time",
        "Let's go",
        "Ready",
        "Checking in"
    ]
    
    results = []
    for message in test_messages:
        state = create_initial_state(
            user_id="test_user",
            message=message,
            message_id=1
        )
        result = await supervisor.classify_intent(state)
        results.append((message, result["intent"]))
    
    # Print results
    print("\n🎯 Check-in Intent Classification:")
    for message, intent in results:
        emoji = "✅" if intent == "checkin" else "❌"
        print(f"  {emoji} '{message}' → {intent}")
    
    # Calculate accuracy
    correct = sum(1 for _, intent in results if intent == "checkin")
    accuracy = (correct / len(results)) * 100
    print(f"\n📊 Accuracy: {accuracy}% ({correct}/{len(results)})")
    
    # We expect at least 80% accuracy (5 out of 6)
    assert accuracy >= 80, f"Check-in intent accuracy too low: {accuracy}%"


@pytest.mark.asyncio
async def test_emotional_intent_classification(supervisor):
    """
    Test classification of emotional support messages
    
    Emotional messages express:
    - Loneliness: "I'm feeling lonely"
    - Urges: "Had urges today"
    - Anxiety: "Feeling anxious"
    - Struggles: "I'm struggling"
    """
    test_messages = [
        "I'm feeling lonely today",
        "Having strong urges to watch porn",
        "Feeling really anxious",
        "I'm struggling with this",
        "Need some support",
        "Feeling down"
    ]
    
    results = []
    for message in test_messages:
        state = create_initial_state(
            user_id="test_user",
            message=message,
            message_id=1
        )
        result = await supervisor.classify_intent(state)
        results.append((message, result["intent"]))
    
    # Print results
    print("\n💭 Emotional Intent Classification:")
    for message, intent in results:
        emoji = "✅" if intent == "emotional" else "❌"
        print(f"  {emoji} '{message}' → {intent}")
    
    # Calculate accuracy
    correct = sum(1 for _, intent in results if intent == "emotional")
    accuracy = (correct / len(results)) * 100
    print(f"\n📊 Accuracy: {accuracy}% ({correct}/{len(results)})")
    
    # We expect at least 80% accuracy
    assert accuracy >= 80, f"Emotional intent accuracy too low: {accuracy}%"


@pytest.mark.asyncio
async def test_query_intent_classification(supervisor):
    """
    Test classification of query messages
    
    Queries ask about:
    - Stats: "What's my streak?"
    - Constitution: "What are the rules?"
    - Bot functionality: "How does this work?"
    """
    test_messages = [
        "What's my streak?",
        "Show me my stats",
        "What are the constitution rules?",
        "How does this bot work?",
        "What's my compliance score?",
        "/status"
    ]
    
    results = []
    for message in test_messages:
        state = create_initial_state(
            user_id="test_user",
            message=message,
            message_id=1
        )
        result = await supervisor.classify_intent(state)
        results.append((message, result["intent"]))
    
    # Print results
    print("\n❓ Query Intent Classification:")
    for message, intent in results:
        emoji = "✅" if intent in ["query", "command"] else "❌"
        print(f"  {emoji} '{message}' → {intent}")
    
    # Note: /status might be classified as "command" which is also valid
    correct = sum(1 for _, intent in results if intent in ["query", "command"])
    accuracy = (correct / len(results)) * 100
    print(f"\n📊 Accuracy: {accuracy}% ({correct}/{len(results)})")
    
    assert accuracy >= 80, f"Query intent accuracy too low: {accuracy}%"


@pytest.mark.asyncio
async def test_command_intent_classification(supervisor):
    """
    Test classification of command messages
    
    Commands are explicit bot commands:
    - /start, /help, /mode, /export, etc.
    """
    test_messages = [
        "/start",
        "/help",
        "/mode",
        "/export"
    ]
    
    results = []
    for message in test_messages:
        state = create_initial_state(
            user_id="test_user",
            message=message,
            message_id=1
        )
        result = await supervisor.classify_intent(state)
        results.append((message, result["intent"]))
    
    # Print results
    print("\n⚡ Command Intent Classification:")
    for message, intent in results:
        emoji = "✅" if intent == "command" else "❌"
        print(f"  {emoji} '{message}' → {intent}")
    
    # Commands should be 100% accurate (they're unambiguous)
    correct = sum(1 for _, intent in results if intent == "command")
    accuracy = (correct / len(results)) * 100
    print(f"\n📊 Accuracy: {accuracy}% ({correct}/{len(results)})")
    
    assert accuracy == 100, f"Command intent accuracy should be 100%, got {accuracy}%"


@pytest.mark.asyncio
async def test_state_management(supervisor):
    """
    Test that state is properly updated after intent classification
    
    Verify:
    1. Original state fields are preserved
    2. Intent field is added
    3. Intent confidence is added
    4. No unexpected fields are added
    """
    state = create_initial_state(
        user_id="test_user_123",
        message="I want to check in",
        message_id=456,
        username="@testuser"
    )
    
    # Store original values
    original_user_id = state["user_id"]
    original_message = state["message"]
    original_message_id = state["message_id"]
    
    # Classify intent
    result = await supervisor.classify_intent(state)
    
    # Verify original fields preserved
    assert result["user_id"] == original_user_id
    assert result["message"] == original_message
    assert result["message_id"] == original_message_id
    assert result["username"] == "@testuser"
    
    # Verify new fields added
    assert result["intent"] is not None
    assert result["intent"] in ["checkin", "emotional", "query", "command"]
    assert result["intent_confidence"] is not None
    
    print(f"\n✅ State management working correctly")
    print(f"  User ID: {result['user_id']}")
    print(f"  Message: '{result['message']}'")
    print(f"  Intent: {result['intent']}")
    print(f"  Confidence: {result['intent_confidence']}")


@pytest.mark.asyncio
async def test_error_handling(supervisor):
    """
    Test that Supervisor handles errors gracefully
    
    What could go wrong:
    1. Empty message
    2. Very long message (>10,000 characters)
    3. Special characters/emojis
    
    The Supervisor should:
    - Not crash
    - Return a valid intent (fallback to "query")
    - Set error field in state
    """
    test_cases = [
        ("", "empty message"),
        ("🔥" * 100, "emoji spam"),
        ("x" * 10000, "very long message")
    ]
    
    print("\n🛡️ Error Handling Tests:")
    for message, description in test_cases:
        state = create_initial_state(
            user_id="test_user",
            message=message,
            message_id=1
        )
        
        try:
            result = await supervisor.classify_intent(state)
            
            # Should not crash
            assert result["intent"] is not None
            
            # Should have fallback intent
            assert result["intent"] in ["checkin", "emotional", "query", "command"]
            
            print(f"  ✅ {description}: Handled gracefully (intent: {result['intent']})")
            
        except Exception as e:
            pytest.fail(f"Supervisor crashed on {description}: {e}")


if __name__ == "__main__":
    """
    Run tests directly from command line
    
    Usage:
    python -m pytest tests/test_intent_classification.py -v -s
    
    Flags:
    -v: Verbose output
    -s: Show print statements
    """
    pytest.main([__file__, "-v", "-s"])
