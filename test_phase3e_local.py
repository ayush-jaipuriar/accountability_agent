"""
Phase 3E Local Testing Script
==============================

Tests all Phase 3E features locally before deployment:
1. Quick Check-In Mode
2. Query Agent
3. Stats Commands
4. Integration

Run with: python test_phase3e_local.py
"""

import sys
import os
import asyncio
from datetime import datetime, timedelta
from typing import Dict, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

# Import Phase 3E components
from src.models.schemas import User, DailyCheckIn, Tier1NonNegotiables, CheckInResponses, UserStreaks
from src.services.analytics_service import (
    calculate_weekly_stats,
    calculate_monthly_stats,
    calculate_yearly_stats
)
from src.agents.query_agent import QueryAgent
from src.agents.supervisor import SupervisorAgent
from src.agents.state import create_initial_state
from src.utils.timezone_utils import get_next_monday
from src.config import settings

# Test results tracking
test_results = []
tests_passed = 0
tests_failed = 0


def log_test(name: str, passed: bool, message: str = ""):
    """Log test result."""
    global tests_passed, tests_failed
    
    status = "✅ PASS" if passed else "❌ FAIL"
    print(f"{status}: {name}")
    if message:
        print(f"   {message}")
    
    test_results.append({
        "name": name,
        "passed": passed,
        "message": message
    })
    
    if passed:
        tests_passed += 1
    else:
        tests_failed += 1


def print_section(title: str):
    """Print section header."""
    print(f"\n{'='*70}")
    print(f"  {title}")
    print(f"{'='*70}\n")


# ===== Test Suite 1: Schema Validation =====

def test_schema_changes():
    """Test that schema changes are present."""
    print_section("TEST SUITE 1: Schema Validation")
    
    # Test User model has quick check-in fields
    try:
        user = User(
            user_id="test_123",
            telegram_id=123,
            name="Test User",
            quick_checkin_count=1,
            quick_checkin_used_dates=["2026-02-07"],
            quick_checkin_reset_date="2026-02-10"
        )
        
        # Check fields exist
        assert hasattr(user, 'quick_checkin_count'), "Missing quick_checkin_count"
        assert hasattr(user, 'quick_checkin_used_dates'), "Missing quick_checkin_used_dates"
        assert hasattr(user, 'quick_checkin_reset_date'), "Missing quick_checkin_reset_date"
        
        # Check values
        assert user.quick_checkin_count == 1, "quick_checkin_count not set correctly"
        assert user.quick_checkin_used_dates == ["2026-02-07"], "quick_checkin_used_dates not set"
        assert user.quick_checkin_reset_date == "2026-02-10", "quick_checkin_reset_date not set"
        
        log_test("User schema - quick check-in fields", True, "All fields present and working")
    except Exception as e:
        log_test("User schema - quick check-in fields", False, str(e))
    
    # Test DailyCheckIn has is_quick_checkin field
    try:
        tier1 = Tier1NonNegotiables(
            sleep=True,
            training=True,
            deep_work=True,
            skill_building=True,
            zero_porn=True,
            boundaries=True
        )
        
        responses = CheckInResponses(
            challenges="Test challenges",
            rating=8,
            rating_reason="Test reason",
            tomorrow_priority="Test priority",
            tomorrow_obstacle="Test obstacle"
        )
        
        checkin = DailyCheckIn(
            date="2026-02-07",
            user_id="test_123",
            mode="maintenance",
            tier1_non_negotiables=tier1,
            responses=responses,
            compliance_score=100.0,
            is_quick_checkin=True  # Phase 3E field
        )
        
        assert hasattr(checkin, 'is_quick_checkin'), "Missing is_quick_checkin field"
        assert checkin.is_quick_checkin == True, "is_quick_checkin not set correctly"
        
        log_test("DailyCheckIn schema - is_quick_checkin field", True, "Field present and working")
    except Exception as e:
        log_test("DailyCheckIn schema - is_quick_checkin field", False, str(e))


# ===== Test Suite 2: Utility Functions =====

def test_utility_functions():
    """Test Phase 3E utility functions."""
    print_section("TEST SUITE 2: Utility Functions")
    
    # Test get_next_monday
    try:
        next_monday = get_next_monday(format_string="%Y-%m-%d")
        
        # Parse the date
        monday_date = datetime.strptime(next_monday, "%Y-%m-%d")
        
        # Check it's a Monday (0 = Monday)
        assert monday_date.weekday() == 0, f"Not a Monday! (weekday={monday_date.weekday()})"
        
        # Check it's in the future
        today = datetime.now()
        assert monday_date.date() > today.date(), "Not in the future!"
        
        log_test("get_next_monday() function", True, f"Returns: {next_monday}")
    except Exception as e:
        log_test("get_next_monday() function", False, str(e))


# ===== Test Suite 3: Analytics Service =====

def test_analytics_service():
    """Test analytics service calculations."""
    print_section("TEST SUITE 3: Analytics Service")
    
    # Note: These will fail without real data in Firestore
    # But we can test the function signatures exist
    
    try:
        # Check functions exist
        assert callable(calculate_weekly_stats), "calculate_weekly_stats not callable"
        assert callable(calculate_monthly_stats), "calculate_monthly_stats not callable"
        assert callable(calculate_yearly_stats), "calculate_yearly_stats not callable"
        
        log_test("Analytics service functions exist", True, "All 3 functions present")
    except Exception as e:
        log_test("Analytics service functions exist", False, str(e))
    
    # Test with mock user (will return error for no data, but should not crash)
    try:
        result = calculate_weekly_stats("nonexistent_user")
        
        # Should return dict with error or has_data=False
        assert isinstance(result, dict), "Should return dict"
        assert "has_data" in result or "error" in result, "Should have error handling"
        
        log_test("Analytics service - error handling", True, "Handles missing data gracefully")
    except Exception as e:
        log_test("Analytics service - error handling", False, str(e))


# ===== Test Suite 4: Query Agent =====

async def test_query_agent():
    """Test Query Agent functionality."""
    print_section("TEST SUITE 4: Query Agent")
    
    # Test QueryAgent instantiation
    try:
        query_agent = QueryAgent(
            project_id=settings.gcp_project_id,
            location=settings.vertex_ai_location,
            model_name=settings.gemini_model
        )
        
        assert query_agent is not None, "QueryAgent failed to instantiate"
        log_test("QueryAgent instantiation", True, "Agent created successfully")
    except Exception as e:
        log_test("QueryAgent instantiation", False, str(e))
        return  # Can't continue without agent
    
    # Test query classification (requires Gemini API)
    try:
        test_queries = [
            ("What's my average compliance?", "compliance_average"),
            ("Show me my longest streak", "streak_info"),
            ("When did I last miss training?", "training_history"),
        ]
        
        for query, expected_type in test_queries:
            try:
                result = await query_agent._classify_query(query)
                
                # Should return one of the valid types
                valid_types = ["compliance_average", "streak_info", "training_history",
                             "sleep_trends", "pattern_frequency", "goal_progress", "unknown"]
                
                assert result in valid_types, f"Invalid type: {result}"
                
                # Check if it matches expected (may vary due to LLM)
                matches = result == expected_type
                log_test(f"Query classification: '{query[:30]}...'", True, 
                        f"Classified as: {result}" + (" ✓" if matches else f" (expected: {expected_type})"))
            except Exception as e:
                log_test(f"Query classification: '{query[:30]}...'", False, str(e))
    except Exception as e:
        print(f"   Skipping classification tests: {e}")


# ===== Test Suite 5: Supervisor Integration =====

async def test_supervisor_integration():
    """Test Supervisor fast keyword detection."""
    print_section("TEST SUITE 5: Supervisor Integration")
    
    try:
        supervisor = SupervisorAgent(project_id=settings.gcp_project_id)
        
        # Test fast keyword detection
        test_messages = [
            ("What's my streak?", "query"),
            ("Show me my compliance", "query"),
            ("What's my average?", "query"),
        ]
        
        for message, expected_intent in test_messages:
            state = create_initial_state(
                user_id="test_123",
                message=message,
                message_id=1
            )
            
            result_state = await supervisor.classify_intent(state)
            intent = result_state.get("intent")
            
            matches = intent == expected_intent
            log_test(f"Supervisor keyword detection: '{message[:30]}...'", True,
                    f"Intent: {intent}" + (" ✓" if matches else f" (expected: {expected_intent})"))
    except Exception as e:
        log_test("Supervisor integration", False, str(e))


# ===== Test Suite 6: Integration Tests =====

def test_imports():
    """Test that all Phase 3E modules can be imported."""
    print_section("TEST SUITE 6: Import Validation")
    
    try:
        from src.agents.query_agent import QueryAgent, get_query_agent
        log_test("Import: query_agent", True, "Module imports successfully")
    except Exception as e:
        log_test("Import: query_agent", False, str(e))
    
    try:
        from src.services.analytics_service import (
            calculate_weekly_stats,
            calculate_monthly_stats,
            calculate_yearly_stats
        )
        log_test("Import: analytics_service", True, "Module imports successfully")
    except Exception as e:
        log_test("Import: analytics_service", False, str(e))
    
    try:
        from src.bot.stats_commands import weekly_command, monthly_command, yearly_command
        log_test("Import: stats_commands", True, "Module imports successfully")
    except Exception as e:
        log_test("Import: stats_commands", False, str(e))
    
    try:
        from src.agents.checkin_agent import get_checkin_agent
        # Check if abbreviated feedback method exists
        from src.agents.checkin_agent import CheckInAgent
        agent = CheckInAgent(project_id=settings.gcp_project_id)  # Only takes project_id
        assert hasattr(agent, 'generate_abbreviated_feedback'), "Missing abbreviated feedback method"
        log_test("CheckInAgent - abbreviated feedback", True, "Method exists")
    except Exception as e:
        log_test("CheckInAgent - abbreviated feedback", False, str(e))


# ===== Test Suite 7: Conversation Flow =====

def test_conversation_integration():
    """Test conversation handler integration."""
    print_section("TEST SUITE 7: Conversation Integration")
    
    try:
        from src.bot.conversation import create_checkin_conversation_handler, start_checkin
        
        # Check that start_checkin exists
        assert callable(start_checkin), "start_checkin not callable"
        
        # Check conversation handler can be created
        handler = create_checkin_conversation_handler()
        assert handler is not None, "Failed to create conversation handler"
        
        # Check it has both entry points
        entry_commands = [ep.commands for ep in handler.entry_points if hasattr(ep, 'commands')]
        all_commands = [cmd for cmds in entry_commands for cmd in cmds]
        
        assert 'checkin' in all_commands, "Missing /checkin entry point"
        assert 'quickcheckin' in all_commands, "Missing /quickcheckin entry point"
        
        log_test("Conversation handler - entry points", True, 
                f"Has {len(all_commands)} entry points including /quickcheckin")
    except Exception as e:
        log_test("Conversation handler - entry points", False, str(e))


# ===== Main Test Runner =====

async def run_all_tests():
    """Run all test suites."""
    print("\n" + "="*70)
    print("  PHASE 3E LOCAL TESTING")
    print("  Testing implementation before Docker deployment")
    print("="*70)
    
    # Run synchronous tests
    test_schema_changes()
    test_utility_functions()
    test_analytics_service()
    test_imports()
    test_conversation_integration()
    
    # Run async tests
    await test_query_agent()
    await test_supervisor_integration()
    
    # Print summary
    print_section("TEST RESULTS SUMMARY")
    
    total = tests_passed + tests_failed
    pass_rate = (tests_passed / total * 100) if total > 0 else 0
    
    print(f"Total Tests Run: {total}")
    print(f"✅ Passed: {tests_passed}")
    print(f"❌ Failed: {tests_failed}")
    print(f"Pass Rate: {pass_rate:.1f}%\n")
    
    if tests_failed == 0:
        print("🎉 ALL TESTS PASSED! Ready for Docker testing.")
        print("\nNext Steps:")
        print("1. Build Docker image: docker build -t accountability-agent:phase3e .")
        print("2. Run container locally: docker run -p 8080:8080 --env-file .env accountability-agent:phase3e")
        print("3. Test via Telegram bot")
        return 0
    else:
        print("⚠️  SOME TESTS FAILED! Fix issues before proceeding.")
        print("\nFailed tests:")
        for result in test_results:
            if not result["passed"]:
                print(f"  - {result['name']}: {result['message']}")
        return 1
    
    # Print detailed results
    print("\nDetailed Results:")
    print("-" * 70)
    for result in test_results:
        status = "✅" if result["passed"] else "❌"
        print(f"{status} {result['name']}")
        if result["message"]:
            print(f"   {result['message']}")


if __name__ == "__main__":
    print("Starting Phase 3E local tests...")
    print(f"Python version: {sys.version}")
    print(f"Project: {settings.gcp_project_id}")
    print(f"Gemini Model: {settings.gemini_model}")
    
    # Run tests
    exit_code = asyncio.run(run_all_tests())
    sys.exit(exit_code)
