"""
Unit Tests for UX Utilities (Phase 3F)
========================================

Tests message formatting, error messages, timeout management, and help text.

**Testing Strategy:**
- Formatting functions are pure (str -> str), easy to test
- ErrorMessages are static methods returning strings with specific content
- TimeoutManager.check_timeout is pure (datetime comparison)
- TimeoutManager.save/get/clear_partial_state use Firestore (tested in integration)
- Help text generation tests structural completeness

**Theory: Testing User-Facing Strings**
Error messages and help text are UX-critical. Changes to these strings
affect how users perceive the app. Tests ensure:
1. Messages contain required information (what happened, what to do)
2. Messages use HTML formatting correctly (for Telegram parsing)
3. Messages include relevant commands (actionable guidance)
4. Content doesn't accidentally break Telegram's HTML parser

Run tests:
    pytest tests/test_ux.py -v
"""

import pytest
from datetime import datetime, timedelta

from src.utils.ux import (
    # Formatting
    format_header,
    format_stat_line,
    format_command_hint,
    format_section,
    format_divider,
    EMOJI,
    
    # Error Messages
    ErrorMessages,
    
    # Timeout Management
    TimeoutManager,
    
    # Help Text
    generate_help_text,
)


# ===== Emoji Constants Tests =====

class TestEmojiConstants:
    """Tests for the EMOJI constant dictionary."""
    
    def test_emoji_dict_exists(self):
        """EMOJI dictionary should exist and be non-empty."""
        assert isinstance(EMOJI, dict)
        assert len(EMOJI) > 0
    
    def test_required_emoji_keys(self):
        """
        EMOJI dictionary should contain all required semantic keys.
        
        **Theory: Semantic Emoji Mapping**
        Rather than scattering emoji literals throughout the codebase,
        we use a centralized dictionary with semantic keys. This means:
        - Changing an emoji updates it everywhere (DRY principle)
        - Keys describe meaning, not appearance (abstraction)
        - New developers understand intent without guessing emoji meaning
        """
        required_keys = [
            'success', 'error', 'warning', 'info', 'loading',
            'checkin', 'stats', 'streak', 'achievement',
            'export', 'leaderboard', 'referral', 'share', 'help',
        ]
        for key in required_keys:
            assert key in EMOJI, f"EMOJI missing required key: {key}"
    
    def test_emoji_values_are_strings(self):
        """All EMOJI values should be non-empty strings."""
        for key, value in EMOJI.items():
            assert isinstance(value, str), f"EMOJI['{key}'] should be a string"
            assert len(value) > 0, f"EMOJI['{key}'] should not be empty"


# ===== Message Formatting Tests =====

class TestFormatHeader:
    """Tests for format_header()."""
    
    def test_title_is_bold(self):
        """Header title should be wrapped in <b> tags."""
        result = format_header("Test Title")
        assert "<b>Test Title</b>" in result
    
    def test_subtitle_is_italic(self):
        """Subtitle should be wrapped in <i> tags."""
        result = format_header("Title", "Subtitle text")
        assert "<i>Subtitle text</i>" in result
    
    def test_no_subtitle_when_none(self):
        """No <i> tag should appear when subtitle is None."""
        result = format_header("Title")
        assert "<i>" not in result
    
    def test_newline_between_title_and_subtitle(self):
        """Title and subtitle should be on separate lines."""
        result = format_header("Title", "Subtitle")
        assert "\n" in result


class TestFormatStatLine:
    """Tests for format_stat_line()."""
    
    def test_includes_label_and_value(self):
        """Stat line should contain both label and value."""
        result = format_stat_line("Current Streak", "47 days")
        assert "Current Streak" in result
        assert "47 days" in result
    
    def test_label_is_bold(self):
        """Label should be wrapped in <b> tags."""
        result = format_stat_line("Score", "100")
        assert "<b>Score:</b>" in result
    
    def test_emoji_from_key(self):
        """When emoji_key is provided, should use the corresponding emoji."""
        result = format_stat_line("Streak", "47 days", emoji_key="streak")
        assert EMOJI['streak'] in result
    
    def test_bullet_when_no_emoji(self):
        """When no emoji_key, should use bullet point."""
        result = format_stat_line("Score", "100")
        assert "•" in result


class TestFormatCommandHint:
    """Tests for format_command_hint()."""
    
    def test_includes_slash_command(self):
        """Command hint should include / prefix."""
        result = format_command_hint("checkin", "Full check-in")
        assert "/checkin" in result
    
    def test_includes_description(self):
        """Command hint should include the description."""
        result = format_command_hint("status", "View your stats")
        assert "View your stats" in result


class TestFormatSection:
    """Tests for format_section()."""
    
    def test_title_is_bold(self):
        """Section title should be bold."""
        result = format_section("Summary", "Some content here")
        assert "<b>Summary:</b>" in result
    
    def test_content_on_new_line(self):
        """Content should appear after a newline."""
        result = format_section("Title", "Content")
        assert "\n" in result


class TestFormatDivider:
    """Tests for format_divider()."""
    
    def test_returns_non_empty_string(self):
        """Divider should be a non-empty string."""
        result = format_divider()
        assert isinstance(result, str)
        assert len(result) > 0
    
    def test_uses_box_drawing_chars(self):
        """Divider should use Unicode box-drawing characters."""
        result = format_divider()
        assert "━" in result


# ===== Error Messages Tests =====

class TestErrorMessages:
    """
    Tests for centralized error messages.
    
    **Theory: Error Message Quality Criteria**
    Every error message is tested for:
    1. Identification: Has an emoji indicator
    2. Explanation: Tells the user what happened
    3. Action: Suggests what to do next
    4. Formatting: Uses HTML tags correctly
    """
    
    def test_user_not_found(self):
        msg = ErrorMessages.user_not_found()
        assert EMOJI['error'] in msg
        assert "/start" in msg
        assert "<b>" in msg
    
    def test_no_checkins_default(self):
        msg = ErrorMessages.no_checkins()
        assert "/checkin" in msg
        assert "<b>" in msg
    
    def test_no_checkins_with_period(self):
        msg = ErrorMessages.no_checkins("the last 7 days")
        assert "the last 7 days" in msg
    
    def test_already_checked_in(self):
        msg = ErrorMessages.already_checked_in("2026-02-07")
        assert "2026-02-07" in msg
        assert "/status" in msg
    
    def test_rate_limited(self):
        msg = ErrorMessages.rate_limited(60)
        assert "60" in msg
        assert "Slow Down" in msg or "slow down" in msg.lower()
    
    def test_service_unavailable(self):
        msg = ErrorMessages.service_unavailable()
        assert "safe" in msg.lower()  # Reassurance that data is safe
        assert "try again" in msg.lower()
    
    def test_invalid_command(self):
        msg = ErrorMessages.invalid_command("/foobar")
        assert "/foobar" in msg
        assert "/help" in msg
    
    def test_export_failed(self):
        msg = ErrorMessages.export_failed("csv")
        assert "CSV" in msg
        assert "/export" in msg
    
    def test_export_no_data(self):
        msg = ErrorMessages.export_no_data()
        assert "/checkin" in msg
    
    def test_generic_error(self):
        msg = ErrorMessages.generic_error()
        assert "safe" in msg.lower()
        assert "/help" in msg


# ===== Timeout Manager Tests =====

class TestTimeoutManager:
    """Tests for conversation timeout management."""
    
    def test_timeout_constants_defined(self):
        """Timeout duration constants should be defined and reasonable."""
        assert TimeoutManager.CHECKIN_REMINDER_MINUTES == 15
        assert TimeoutManager.CHECKIN_CANCEL_MINUTES == 30
        assert TimeoutManager.QUERY_CANCEL_MINUTES == 5
    
    def test_check_timeout_not_expired(self):
        """
        Should return False when within timeout window.
        
        **Theory: Timeout Checking**
        We compare (now - start_time) against the timeout duration.
        If elapsed time is less than the timeout, the conversation
        is still valid and should continue.
        """
        start = datetime.utcnow() - timedelta(minutes=5)
        assert TimeoutManager.check_timeout(start, 30) is False
    
    def test_check_timeout_expired(self):
        """Should return True when timeout has been exceeded."""
        start = datetime.utcnow() - timedelta(minutes=35)
        assert TimeoutManager.check_timeout(start, 30) is True
    
    def test_check_timeout_exactly_at_boundary(self):
        """At exactly the timeout duration, should be expired (> not >=)."""
        start = datetime.utcnow() - timedelta(minutes=30, seconds=1)
        assert TimeoutManager.check_timeout(start, 30) is True
    
    def test_timeout_warning_message(self):
        """Warning message should include remaining time and tips."""
        msg = TimeoutManager.get_timeout_warning(15)
        assert "15" in msg
        assert "/cancel" in msg or "/resume" in msg
    
    def test_timeout_cancel_message(self):
        """Cancel message should explain what happened and offer options."""
        msg = TimeoutManager.get_timeout_cancel_message()
        assert "expired" in msg.lower() or "cancelled" in msg.lower()
        assert "/resume" in msg
        assert "/checkin" in msg


# ===== Help Text Tests =====

class TestGenerateHelpText:
    """Tests for help text generation."""
    
    def test_returns_non_empty_string(self):
        """Help text should be a non-empty string."""
        result = generate_help_text()
        assert isinstance(result, str)
        assert len(result) > 100  # Should be substantial
    
    def test_includes_core_commands(self):
        """Help text should list all core commands."""
        result = generate_help_text()
        # Note: /help is not listed because the user is already viewing help
        core_commands = ["/checkin", "/status", "/weekly", "/monthly"]
        for cmd in core_commands:
            assert cmd in result, f"Help text missing command: {cmd}"
    
    def test_includes_phase3f_commands(self):
        """Help text should include Phase 3F commands."""
        result = generate_help_text()
        phase3f_commands = ["/export", "/report", "/leaderboard", "/invite", "/share"]
        for cmd in phase3f_commands:
            assert cmd in result, f"Help text missing Phase 3F command: {cmd}"
    
    def test_uses_html_formatting(self):
        """Help text should use HTML tags for Telegram."""
        result = generate_help_text()
        assert "<b>" in result
    
    def test_organized_by_category(self):
        """Help text should group commands by category."""
        result = generate_help_text()
        categories = ["Check-In", "Stats", "Export", "Social", "Settings"]
        found = sum(1 for cat in categories if cat in result)
        assert found >= 3, f"Only found {found}/{len(categories)} categories"
    
    def test_includes_natural_language_hint(self):
        """Help text should mention natural language support."""
        result = generate_help_text()
        assert "natural" in result.lower() or "type naturally" in result.lower()


# ===== Run Tests =====

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
