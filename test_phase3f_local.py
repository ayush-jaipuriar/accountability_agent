"""
Phase 3F Local Test Script
===========================

Tests all Phase 3F components locally without requiring:
- Firestore connection
- Telegram bot
- Cloud Run deployment

Each test creates mock data and verifies the output.

Usage:
    python test_phase3f_local.py
"""

import io
import json
import csv
import sys
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

# Add project root to path
sys.path.insert(0, '.')


def create_mock_user():
    """Create a mock User object for testing."""
    from src.models.schemas import User, UserStreaks, StreakShields
    return User(
        user_id="123456789",
        telegram_id=123456789,
        telegram_username="test_user",
        name="TestUser",
        timezone="Asia/Kolkata",
        constitution_mode="maintenance",
        career_mode="skill_building",
        streaks=UserStreaks(
            current_streak=47,
            longest_streak=47,
            last_checkin_date="2026-02-06",
            total_checkins=100,
        ),
        streak_shields=StreakShields(total=3, used=0, available=3),
        achievements=["week_warrior", "month_master"],
        level=5,
        xp=500,
    )


def create_mock_checkins(days=7):
    """Create mock DailyCheckIn objects for testing."""
    from src.models.schemas import (
        DailyCheckIn, Tier1NonNegotiables, CheckInResponses
    )
    
    checkins = []
    for i in range(days):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        checkins.append(DailyCheckIn(
            date=date,
            user_id="123456789",
            mode="maintenance",
            tier1_non_negotiables=Tier1NonNegotiables(
                sleep=i % 3 != 0,  # Miss every 3rd day
                sleep_hours=7.5 - (i * 0.3),
                training=i % 4 != 0,
                is_rest_day=i % 7 == 6,
                training_type="workout" if i % 4 != 0 else "skipped",
                deep_work=True,
                deep_work_hours=2.5 + (i * 0.2),
                skill_building=i % 2 == 0,
                skill_building_hours=2.0 if i % 2 == 0 else 0,
                zero_porn=True,
                boundaries=i != 3,  # Miss one day
            ),
            responses=CheckInResponses(
                challenges=f"Day {i} challenges: Focused on consistency and improvement this day",
                rating=max(1, min(10, 8 - i // 2)),
                rating_reason=f"Day {i} rating: Good progress on most fronts despite minor setbacks",
                tomorrow_priority=f"Day {i} priority: Continue building momentum on key initiatives",
                tomorrow_obstacle=f"Day {i} obstacle: Time management with multiple competing tasks",
            ),
            compliance_score=max(40, 100 - i * 8),
            is_quick_checkin=i == 5,
        ))
    
    return checkins


def test_csv_export():
    """Test CSV export generation."""
    print("\n" + "=" * 60)
    print("TEST 1: CSV Export")
    print("=" * 60)
    
    from src.services.export_service import generate_csv_export
    
    user = create_mock_user()
    checkins = create_mock_checkins(7)
    
    buffer = generate_csv_export(checkins, user)
    
    # Verify it's valid CSV
    content = buffer.read().decode('utf-8-sig')
    reader = csv.DictReader(io.StringIO(content))
    rows = list(reader)
    
    assert len(rows) == 7, f"Expected 7 rows, got {len(rows)}"
    assert 'date' in rows[0], "Missing 'date' column"
    assert 'compliance_score' in rows[0], "Missing 'compliance_score' column"
    assert 'sleep_hours' in rows[0], "Missing 'sleep_hours' column"
    
    print(f"  CSV rows: {len(rows)}")
    print(f"  Columns: {list(rows[0].keys())}")
    print(f"  File size: {len(content)} bytes")
    print("  PASSED")


def test_json_export():
    """Test JSON export generation."""
    print("\n" + "=" * 60)
    print("TEST 2: JSON Export")
    print("=" * 60)
    
    from src.services.export_service import generate_json_export
    
    user = create_mock_user()
    checkins = create_mock_checkins(7)
    
    buffer = generate_json_export(checkins, user)
    
    # Verify it's valid JSON
    content = buffer.read().decode('utf-8')
    data = json.loads(content)
    
    assert 'export_metadata' in data, "Missing export_metadata"
    assert 'user_profile' in data, "Missing user_profile"
    assert 'check_ins' in data, "Missing check_ins"
    assert len(data['check_ins']) == 7, f"Expected 7 check-ins, got {len(data['check_ins'])}"
    assert data['user_profile']['name'] == 'TestUser'
    
    print(f"  Check-ins: {len(data['check_ins'])}")
    print(f"  User: {data['user_profile']['name']}")
    print(f"  Date range: {data['export_metadata']['date_range']}")
    print(f"  File size: {len(content)} bytes")
    print("  PASSED")


def test_pdf_export():
    """Test PDF export generation."""
    print("\n" + "=" * 60)
    print("TEST 3: PDF Export")
    print("=" * 60)
    
    from src.services.export_service import generate_pdf_export
    
    user = create_mock_user()
    checkins = create_mock_checkins(14)
    
    buffer = generate_pdf_export(checkins, user)
    
    # Verify it's a valid PDF (starts with %PDF)
    content = buffer.read()
    assert content[:4] == b'%PDF', "Not a valid PDF file"
    assert len(content) > 1000, "PDF seems too small"
    
    print(f"  PDF size: {len(content)} bytes ({len(content)/1024:.1f} KB)")
    print(f"  Starts with: {content[:10]}")
    print("  PASSED")


def test_sleep_chart():
    """Test sleep trend chart generation."""
    print("\n" + "=" * 60)
    print("TEST 4: Sleep Trend Chart")
    print("=" * 60)
    
    from src.services.visualization_service import generate_sleep_chart
    
    checkins = create_mock_checkins(7)
    
    buffer = generate_sleep_chart(checkins)
    content = buffer.read()
    
    # Verify it's a valid PNG
    assert content[:8] == b'\x89PNG\r\n\x1a\n', "Not a valid PNG file"
    assert len(content) > 5000, "Image seems too small"
    
    print(f"  Image size: {len(content)} bytes ({len(content)/1024:.1f} KB)")
    print("  PASSED")


def test_training_chart():
    """Test training frequency chart generation."""
    print("\n" + "=" * 60)
    print("TEST 5: Training Frequency Chart")
    print("=" * 60)
    
    from src.services.visualization_service import generate_training_chart
    
    checkins = create_mock_checkins(7)
    
    buffer = generate_training_chart(checkins)
    content = buffer.read()
    
    assert content[:8] == b'\x89PNG\r\n\x1a\n', "Not a valid PNG file"
    assert len(content) > 5000, "Image seems too small"
    
    print(f"  Image size: {len(content)} bytes ({len(content)/1024:.1f} KB)")
    print("  PASSED")


def test_compliance_chart():
    """Test compliance scores chart generation."""
    print("\n" + "=" * 60)
    print("TEST 6: Compliance Scores Chart")
    print("=" * 60)
    
    from src.services.visualization_service import generate_compliance_chart
    
    checkins = create_mock_checkins(7)
    
    buffer = generate_compliance_chart(checkins)
    content = buffer.read()
    
    assert content[:8] == b'\x89PNG\r\n\x1a\n', "Not a valid PNG file"
    assert len(content) > 5000, "Image seems too small"
    
    print(f"  Image size: {len(content)} bytes ({len(content)/1024:.1f} KB)")
    print("  PASSED")


def test_radar_chart():
    """Test domain radar chart generation."""
    print("\n" + "=" * 60)
    print("TEST 7: Domain Radar Chart")
    print("=" * 60)
    
    from src.services.visualization_service import generate_domain_radar
    
    checkins = create_mock_checkins(7)
    
    buffer = generate_domain_radar(checkins)
    content = buffer.read()
    
    assert content[:8] == b'\x89PNG\r\n\x1a\n', "Not a valid PNG file"
    assert len(content) > 5000, "Image seems too small"
    
    print(f"  Image size: {len(content)} bytes ({len(content)/1024:.1f} KB)")
    print("  PASSED")


def test_all_graphs():
    """Test generating all 4 graphs at once."""
    print("\n" + "=" * 60)
    print("TEST 8: All 4 Graphs (Weekly Report)")
    print("=" * 60)
    
    from src.services.visualization_service import generate_weekly_graphs
    
    checkins = create_mock_checkins(7)
    
    graphs = generate_weekly_graphs(checkins)
    
    assert len(graphs) == 4, f"Expected 4 graphs, got {len(graphs)}"
    assert 'sleep' in graphs
    assert 'training' in graphs
    assert 'compliance' in graphs
    assert 'radar' in graphs
    
    total_size = sum(g.getbuffer().nbytes for g in graphs.values())
    
    print(f"  Graphs generated: {len(graphs)}/4")
    for name, buf in graphs.items():
        print(f"  - {name}: {buf.getbuffer().nbytes/1024:.1f} KB")
    print(f"  Total size: {total_size/1024:.1f} KB")
    print("  PASSED")


def test_shareable_stats():
    """Test shareable stats image generation."""
    print("\n" + "=" * 60)
    print("TEST 9: Shareable Stats Image")
    print("=" * 60)
    
    from src.services.social_service import generate_shareable_stats_image
    
    user = create_mock_user()
    checkins = create_mock_checkins(30)
    
    buffer = generate_shareable_stats_image(user, checkins)
    content = buffer.read()
    
    assert content[:8] == b'\x89PNG\r\n\x1a\n', "Not a valid PNG file"
    assert len(content) > 5000, "Image seems too small"
    
    print(f"  Image size: {len(content)} bytes ({len(content)/1024:.1f} KB)")
    print("  PASSED")


def test_ux_error_messages():
    """Test UX error message formatting."""
    print("\n" + "=" * 60)
    print("TEST 10: UX Error Messages")
    print("=" * 60)
    
    from src.utils.ux import ErrorMessages
    
    messages = [
        ("user_not_found", ErrorMessages.user_not_found()),
        ("no_checkins", ErrorMessages.no_checkins("last 7 days")),
        ("already_checked_in", ErrorMessages.already_checked_in("2026-02-07")),
        ("rate_limited", ErrorMessages.rate_limited(30)),
        ("service_unavailable", ErrorMessages.service_unavailable()),
        ("export_failed", ErrorMessages.export_failed("csv")),
        ("generic_error", ErrorMessages.generic_error()),
    ]
    
    for name, msg in messages:
        assert len(msg) > 20, f"Message '{name}' seems too short"
        assert "<b>" in msg, f"Message '{name}' missing bold formatting"
        print(f"  {name}: {len(msg)} chars")
    
    print("  All error messages properly formatted")
    print("  PASSED")


def test_ux_help_text():
    """Test help text generation."""
    print("\n" + "=" * 60)
    print("TEST 11: Help Text")
    print("=" * 60)
    
    from src.utils.ux import generate_help_text
    
    help_text = generate_help_text()
    
    assert "/checkin" in help_text
    assert "/export" in help_text
    assert "/leaderboard" in help_text
    assert "/report" in help_text
    assert "/share" in help_text
    assert "/invite" in help_text
    assert "/resume" in help_text
    
    print(f"  Help text length: {len(help_text)} chars")
    print(f"  Contains all Phase 3F commands")
    print("  PASSED")


def test_report_message_builder():
    """Test report message building."""
    print("\n" + "=" * 60)
    print("TEST 12: Report Message Builder")
    print("=" * 60)
    
    from src.agents.reporting_agent import _build_report_message
    
    user = create_mock_user()
    checkins = create_mock_checkins(7)
    
    message = _build_report_message(checkins, user, "Great week with 92% compliance.")
    
    assert "Weekly Report" in message
    assert "Quick Summary" in message
    assert "AI Insights" in message
    assert "47" in message  # Streak
    
    print(f"  Message length: {len(message)} chars")
    print("  Contains all required sections")
    print("  PASSED")


def test_referral_link():
    """Test referral link generation."""
    print("\n" + "=" * 60)
    print("TEST 13: Referral Link Generation")
    print("=" * 60)
    
    from src.services.social_service import generate_referral_link
    
    link = generate_referral_link("123456789", "constitution_bot")
    
    assert "t.me/constitution_bot" in link
    assert "ref_123456789" in link
    
    print(f"  Link: {link}")
    print("  PASSED")


def test_data_models():
    """Test new Phase 3F schema fields."""
    print("\n" + "=" * 60)
    print("TEST 14: Data Models (Phase 3F Fields)")
    print("=" * 60)
    
    from src.models.schemas import User
    
    user = User(
        user_id="test",
        telegram_id=123,
        name="Test",
        leaderboard_opt_in=True,
        referred_by="456",
        referral_code="ref_test",
    )
    
    assert user.leaderboard_opt_in is True
    assert user.referred_by == "456"
    assert user.referral_code == "ref_test"
    
    # Test Firestore serialization includes new fields
    data = user.to_firestore()
    assert "leaderboard_opt_in" in data
    assert "referred_by" in data
    assert "referral_code" in data
    
    print(f"  leaderboard_opt_in: {user.leaderboard_opt_in}")
    print(f"  referred_by: {user.referred_by}")
    print(f"  referral_code: {user.referral_code}")
    print(f"  Firestore serialization includes all 3F fields")
    print("  PASSED")


if __name__ == "__main__":
    print("=" * 60)
    print("  PHASE 3F LOCAL TESTS")
    print("  Testing: Export, Visualization, Reports, Social, UX")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    tests = [
        test_csv_export,
        test_json_export,
        test_pdf_export,
        test_sleep_chart,
        test_training_chart,
        test_compliance_chart,
        test_radar_chart,
        test_all_graphs,
        test_shareable_stats,
        test_ux_error_messages,
        test_ux_help_text,
        test_report_message_builder,
        test_referral_link,
        test_data_models,
    ]
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"  FAILED: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
    
    print("\n" + "=" * 60)
    print(f"  RESULTS: {passed}/{len(tests)} passed, {failed} failed")
    print("=" * 60)
    
    if failed > 0:
        sys.exit(1)
    else:
        print("\n  ALL TESTS PASSED!")
        sys.exit(0)
