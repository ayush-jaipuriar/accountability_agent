"""
Telegram Bot Command Handler Tests
====================================

Tests all command handlers in TelegramBotManager.

**Testing Strategy - Mocking python-telegram-bot:**

The python-telegram-bot library uses two key objects passed to every handler:

1. **Update**: Represents an incoming message or button press from Telegram.
   - `update.effective_user`: The Telegram user who sent the message
   - `update.message`: The message sent (with `.reply_text()` to respond)
   - `update.callback_query`: For inline keyboard button presses

2. **Context (CallbackContext)**: Bot state and user-specific data.
   - `context.args`: Command arguments (e.g., /mode optimization → args=["optimization"])
   - `context.user_data`: Dictionary persisted per-user within a conversation
   - `context.bot`: The bot instance for sending proactive messages

**Why We Don't Use the Real Bot:**
- Telegram API calls require a valid bot token and network connection
- Tests must be deterministic (no external dependencies)
- We want to verify *logic* in handlers, not Telegram's API behavior

**How We Test:**
1. Create mock Update/Context objects with expected attributes
2. Patch `firestore_service` to control data layer responses
3. Call handler methods directly and assert on mock calls (reply_text, etc.)
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from src.models.schemas import User, UserStreaks, StreakShields


# ===== Mock Factory Helpers =====
# These create realistic mock objects matching python-telegram-bot's API.


def _make_update(
    user_id=123456789,
    username="test_user",
    first_name="Test",
    text="/start",
):
    """
    Create a mock Telegram Update object.

    Simulates what Telegram sends to the bot when a user sends a command.
    """
    update = MagicMock()

    # effective_user: who sent the message
    update.effective_user.id = user_id
    update.effective_user.username = username
    update.effective_user.first_name = first_name

    # message: the actual message
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.message.reply_document = AsyncMock()
    update.message.reply_photo = AsyncMock()
    update.message.delete = AsyncMock()
    update.message.message_id = 1

    return update


def _make_callback_update(
    user_id=123456789,
    username="test_user",
    first_name="Test",
    data="mode_optimization",
):
    """
    Create a mock Telegram callback query Update.

    Simulates what Telegram sends when a user presses an inline keyboard button.
    The `data` field carries the payload we set in InlineKeyboardButton(callback_data=...).
    """
    update = MagicMock()

    # effective_user
    update.effective_user.id = user_id
    update.effective_user.username = username
    update.effective_user.first_name = first_name

    # callback_query: inline keyboard response
    update.callback_query.data = data
    update.callback_query.answer = AsyncMock()
    update.callback_query.edit_message_text = AsyncMock()
    update.callback_query.from_user.id = user_id
    update.callback_query.message.reply_text = AsyncMock()

    return update


def _make_context(args=None, user_data=None):
    """
    Create a mock Telegram CallbackContext.

    The context carries per-user state (user_data) and the bot instance
    for sending proactive messages.
    """
    context = MagicMock()
    context.args = args or []
    context.user_data = user_data if user_data is not None else {}
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    context.bot.get_me = AsyncMock()
    return context


def _make_user(
    user_id="123456789",
    streak=10,
    partner_id=None,
    achievements=None,
    career_mode="skill_building",
    shields_available=3,
):
    """Create a test User object with sensible defaults."""
    return User(
        user_id=user_id,
        telegram_id=int(user_id),
        telegram_username="test_user",
        name="Test User",
        timezone="Asia/Kolkata",
        streaks=UserStreaks(
            current_streak=streak,
            longest_streak=max(streak, 47),
            last_checkin_date="2026-02-06",
            total_checkins=100,
        ),
        constitution_mode="maintenance",
        achievements=achievements or [],
        career_mode=career_mode,
        accountability_partner_id=partner_id,
        accountability_partner_name="Partner" if partner_id else None,
        streak_shields=StreakShields(
            total=3,
            used=3 - shields_available,
            available=shields_available,
        ),
    )


# ===== Fixture: Create a TelegramBotManager without real Telegram API =====


@pytest.fixture
def bot_mgr():
    """
    Create a TelegramBotManager instance without calling the real constructor.

    **Why __new__?**
    The constructor calls `Application.builder().token(token).build()` which
    requires a valid Telegram bot token and network access. Using __new__ gives
    us the class instance with all its methods but without executing __init__.

    We manually set `self.bot` (the only attribute handlers use from `self`).
    """
    from src.bot.telegram_bot import TelegramBotManager

    mgr = TelegramBotManager.__new__(TelegramBotManager)
    mgr.token = "fake:token"
    mgr.application = MagicMock()
    mgr.bot = AsyncMock()
    return mgr


@pytest.fixture
def mock_fs():
    """Patch firestore_service used by telegram_bot module."""
    with patch("src.bot.telegram_bot.firestore_service") as mock:
        yield mock


# ===== /start Command =====


class TestStartCommand:
    """
    Tests for /start - the entry point for all users.

    The start command has two branches:
    1. New user → Full onboarding (welcome, mode selection, timezone)
    2. Returning user → Quick stats summary
    """

    @pytest.mark.asyncio
    async def test_start_returning_user_shows_stats(self, bot_mgr, mock_fs):
        """Returning user should see their streak and stats."""
        update = _make_update(text="/start")
        context = _make_context()

        mock_fs.get_user.return_value = _make_user(streak=47)

        await bot_mgr.start_command(update, context)

        # Should call reply_text with stats
        update.message.reply_text.assert_called_once()
        reply_text = update.message.reply_text.call_args[0][0]
        assert "Welcome back" in reply_text
        assert "47" in reply_text  # streak

    @pytest.mark.asyncio
    async def test_start_new_user_shows_onboarding(self, bot_mgr, mock_fs):
        """New user should see welcome message + mode selection keyboard."""
        update = _make_update(text="/start")
        context = _make_context()

        mock_fs.get_user.return_value = None  # User not found

        await bot_mgr.start_command(update, context)

        # Should send 2 messages: welcome + mode selection
        assert update.message.reply_text.call_count == 2

        # First message: welcome
        first_call = update.message.reply_text.call_args_list[0]
        assert "Welcome" in first_call[0][0]

        # Second message: mode selection with InlineKeyboard
        second_call = update.message.reply_text.call_args_list[1]
        assert "Choose Your Mode" in second_call[0][0]
        assert "reply_markup" in second_call[1]  # Has inline keyboard

    @pytest.mark.asyncio
    async def test_start_with_referral_stores_code(self, bot_mgr, mock_fs):
        """Starting with ?start=ref_USERID should store referral code."""
        update = _make_update(text="/start ref_987654321")
        context = _make_context(args=["ref_987654321"])

        mock_fs.get_user.return_value = None

        await bot_mgr.start_command(update, context)

        # Referral should be stored in context.user_data
        assert context.user_data.get("referral_user_id") == "987654321"


# ===== /help Command =====


class TestHelpCommand:
    """Tests for /help - shows available commands."""

    @pytest.mark.asyncio
    async def test_help_sends_help_text(self, bot_mgr, mock_fs):
        """Should send help text with all available commands."""
        update = _make_update(text="/help")
        context = _make_context()

        with patch("src.utils.ux.generate_help_text", return_value="<b>Help</b> content"):
            await bot_mgr.help_command(update, context)

        update.message.reply_text.assert_called_once()
        call_kwargs = update.message.reply_text.call_args[1]
        assert call_kwargs.get("parse_mode") == "HTML"


# ===== /status Command =====


class TestStatusCommand:
    """
    Tests for /status - user's current stats.

    Shows: streak, compliance, shields, recent check-ins, encouragement.
    """

    @pytest.mark.asyncio
    async def test_status_no_user(self, bot_mgr, mock_fs):
        """Unregistered user should see error message."""
        update = _make_update(text="/status")
        context = _make_context()
        mock_fs.get_user.return_value = None

        with patch("src.utils.ux.ErrorMessages") as MockErrors:
            MockErrors.user_not_found.return_value = "User not found"
            await bot_mgr.status_command(update, context)

        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_existing_user(self, bot_mgr, mock_fs):
        """Registered user should see streak, shields, compliance."""
        update = _make_update(text="/status")
        context = _make_context()
        user = _make_user(streak=10)
        mock_fs.get_user.return_value = user

        # Mock recent check-ins with proper tier1 attributes for analytics
        mock_checkin = MagicMock()
        mock_checkin.compliance_score = 85.0
        mock_checkin.tier1_non_negotiables.sleep = True
        mock_checkin.tier1_non_negotiables.sleep_hours = 7.5
        mock_checkin.tier1_non_negotiables.training = True
        mock_checkin.tier1_non_negotiables.deep_work = True
        mock_checkin.tier1_non_negotiables.deep_work_hours = 2.0
        mock_checkin.tier1_non_negotiables.skill_building = False
        mock_checkin.tier1_non_negotiables.skill_building_hours = 0
        mock_checkin.tier1_non_negotiables.zero_porn = True
        mock_checkin.tier1_non_negotiables.boundaries = True
        mock_fs.get_recent_checkins.return_value = [mock_checkin] * 5

        # Mock today's check-in existence
        mock_fs.checkin_exists.return_value = True

        with patch("src.models.schemas.get_current_date_ist", return_value="2026-02-07"), \
             patch("src.utils.streak.get_streak_emoji", return_value="💪"):
            await bot_mgr.status_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "10 days" in reply  # streak
        assert "check-in complete" in reply.lower() or "✅" in reply

    @pytest.mark.asyncio
    async def test_status_shows_encouragement_for_long_streak(self, bot_mgr, mock_fs):
        """User with 30+ day streak should see motivational message."""
        update = _make_update(text="/status")
        context = _make_context()
        mock_fs.get_user.return_value = _make_user(streak=35)
        mock_fs.get_recent_checkins.return_value = []
        mock_fs.checkin_exists.return_value = False

        with patch("src.models.schemas.get_current_date_ist", return_value="2026-02-07"), \
             patch("src.utils.streak.get_streak_emoji", return_value="🚀"):
            await bot_mgr.status_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "fire" in reply.lower() or "🚀" in reply


# ===== /mode Command =====


class TestModeCommand:
    """Tests for /mode - view and change constitution mode."""

    @pytest.mark.asyncio
    async def test_mode_shows_current(self, bot_mgr, mock_fs):
        """Should display current mode and available options."""
        update = _make_update(text="/mode")
        context = _make_context()
        mock_fs.get_user.return_value = _make_user()

        await bot_mgr.mode_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "Maintenance" in reply
        assert "Optimization" in reply

    @pytest.mark.asyncio
    async def test_mode_no_user(self, bot_mgr, mock_fs):
        """Unregistered user should see error."""
        update = _make_update(text="/mode")
        context = _make_context()
        mock_fs.get_user.return_value = None

        await bot_mgr.mode_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "not found" in reply.lower() or "/start" in reply


# ===== /career Command =====


class TestCareerCommand:
    """
    Tests for /career - career phase tracking (Phase 3D).

    Career mode determines how the Tier 1 skill building question is phrased:
    - skill_building: "Did you do 2+ hours skill building?"
    - job_searching: "Did you make job search progress?"
    - employed: "Did you work toward promotion/raise?"
    """

    @pytest.mark.asyncio
    async def test_career_shows_current_mode(self, bot_mgr, mock_fs):
        """Should show current career mode and selection buttons."""
        update = _make_update(text="/career")
        context = _make_context()
        mock_fs.get_user.return_value = _make_user(career_mode="skill_building")

        await bot_mgr.career_command(update, context)

        reply_text = update.message.reply_text.call_args[0][0]
        assert "Skill Building" in reply_text
        # Should have inline keyboard
        call_kwargs = update.message.reply_text.call_args[1]
        assert "reply_markup" in call_kwargs

    @pytest.mark.asyncio
    async def test_career_no_user(self, bot_mgr, mock_fs):
        """Unregistered user should see error."""
        update = _make_update(text="/career")
        context = _make_context()
        mock_fs.get_user.return_value = None

        await bot_mgr.career_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "/start" in reply


# ===== /use_shield Command =====


class TestUseShieldCommand:
    """
    Tests for /use_shield - streak shield protection (Phase 3A).

    Rules:
    - 3 shields per 30 days
    - Can only use if not already checked in today
    - Shield protects streak from breaking
    """

    @pytest.mark.asyncio
    async def test_use_shield_no_user(self, bot_mgr, mock_fs):
        """Unregistered user should see error."""
        update = _make_update(text="/use_shield")
        context = _make_context()
        mock_fs.get_user.return_value = None

        await bot_mgr.use_shield_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "/start" in reply

    @pytest.mark.asyncio
    async def test_use_shield_no_shields_available(self, bot_mgr, mock_fs):
        """User with 0 shields should see 'no shields' message."""
        update = _make_update(text="/use_shield")
        context = _make_context()
        mock_fs.get_user.return_value = _make_user(shields_available=0)

        await bot_mgr.use_shield_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "No Streak Shields" in reply or "no" in reply.lower()

    @pytest.mark.asyncio
    async def test_use_shield_already_checked_in(self, bot_mgr, mock_fs):
        """If user already checked in, shield is not needed."""
        update = _make_update(text="/use_shield")
        context = _make_context()
        mock_fs.get_user.return_value = _make_user(shields_available=2)
        mock_fs.checkin_exists.return_value = True

        with patch("src.utils.timezone_utils.get_checkin_date", return_value="2026-02-07"):
            await bot_mgr.use_shield_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "Not Needed" in reply or "already" in reply.lower()

    @pytest.mark.asyncio
    async def test_use_shield_success(self, bot_mgr, mock_fs):
        """Should use a shield and show confirmation."""
        update = _make_update(text="/use_shield")
        context = _make_context()
        user = _make_user(shields_available=2)
        mock_fs.get_user.side_effect = [
            user,  # First call: check user
            _make_user(shields_available=1),  # Second call: after shield use
        ]
        mock_fs.checkin_exists.return_value = False
        mock_fs.use_streak_shield.return_value = True

        with patch("src.utils.timezone_utils.get_checkin_date", return_value="2026-02-07"), \
             patch("src.utils.streak.calculate_days_without_checkin", return_value=1):
            await bot_mgr.use_shield_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "Shield Activated" in reply or "protected" in reply.lower()
        mock_fs.use_streak_shield.assert_called_once()


# ===== /set_partner Command =====


class TestSetPartnerCommand:
    """
    Tests for /set_partner - accountability partner system (Phase 3B).

    Partners are linked bidirectionally. When one ghosts for 5+ days,
    the other gets notified.
    """

    @pytest.mark.asyncio
    async def test_set_partner_no_args(self, bot_mgr, mock_fs):
        """Missing @username should show usage error."""
        update = _make_update(text="/set_partner")
        context = _make_context(args=[])
        mock_fs.get_user.return_value = _make_user()

        await bot_mgr.set_partner_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "Format" in reply or "@username" in reply

    @pytest.mark.asyncio
    async def test_set_partner_not_found(self, bot_mgr, mock_fs):
        """Partner username not registered should show error."""
        update = _make_update(text="/set_partner @unknown_user")
        context = _make_context(args=["@unknown_user"])
        mock_fs.get_user.return_value = _make_user()
        mock_fs.get_user_by_telegram_username.return_value = None

        await bot_mgr.set_partner_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "not found" in reply.lower()

    @pytest.mark.asyncio
    async def test_set_partner_self(self, bot_mgr, mock_fs):
        """Can't partner with yourself."""
        update = _make_update(text="/set_partner @test_user")
        context = _make_context(args=["@test_user"])
        user = _make_user()
        mock_fs.get_user.return_value = user
        mock_fs.get_user_by_telegram_username.return_value = user  # Same user

        await bot_mgr.set_partner_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "own" in reply.lower() or "yourself" in reply.lower()

    @pytest.mark.asyncio
    async def test_set_partner_success(self, bot_mgr, mock_fs):
        """Should send invite to partner and confirm to requester."""
        update = _make_update(text="/set_partner @partner_user")
        context = _make_context(args=["@partner_user"])

        requester = _make_user(user_id="123456789")
        partner = _make_user(user_id="987654321")

        mock_fs.get_user.return_value = requester
        mock_fs.get_user_by_telegram_username.return_value = partner

        await bot_mgr.set_partner_command(update, context)

        # Should send invite to partner via bot
        context.bot.send_message.assert_called_once()
        invite_call = context.bot.send_message.call_args
        assert invite_call[1]["chat_id"] == partner.telegram_id

        # Should confirm to requester
        reply = update.message.reply_text.call_args[0][0]
        assert "request sent" in reply.lower()


# ===== /unlink_partner Command =====


class TestUnlinkPartnerCommand:
    """Tests for /unlink_partner - remove accountability partnership."""

    @pytest.mark.asyncio
    async def test_unlink_no_partner(self, bot_mgr, mock_fs):
        """User without partner should see error."""
        update = _make_update(text="/unlink_partner")
        context = _make_context()
        mock_fs.get_user.return_value = _make_user(partner_id=None)

        await bot_mgr.unlink_partner_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "don't have" in reply.lower() or "no" in reply.lower()

    @pytest.mark.asyncio
    async def test_unlink_success(self, bot_mgr, mock_fs):
        """Should unlink both users bidirectionally."""
        update = _make_update(text="/unlink_partner")
        context = _make_context()

        user = _make_user(partner_id="987654321")
        partner = _make_user(user_id="987654321")
        mock_fs.get_user.side_effect = [user, partner]

        await bot_mgr.unlink_partner_command(update, context)

        # Both users should be unlinked
        assert mock_fs.set_accountability_partner.call_count == 2
        # Notification sent to partner
        context.bot.send_message.assert_called_once()


# ===== /achievements Command =====


class TestAchievementsCommand:
    """
    Tests for /achievements - view unlocked badges (Phase 3C).

    Achievement display is grouped by rarity:
    legendary → epic → rare → common
    """

    @pytest.mark.asyncio
    async def test_no_achievements(self, bot_mgr, mock_fs):
        """User with no achievements should see motivation message."""
        update = _make_update(text="/achievements")
        context = _make_context()
        mock_fs.get_user.return_value = _make_user(achievements=[])

        await bot_mgr.achievements_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "No achievements" in reply or "no achievements" in reply.lower()

    @pytest.mark.asyncio
    async def test_with_achievements(self, bot_mgr, mock_fs):
        """User with achievements should see them grouped by rarity."""
        update = _make_update(text="/achievements")
        context = _make_context()
        mock_fs.get_user.return_value = _make_user(
            streak=10, achievements=["week_warrior", "first_step"]
        )

        # Mock achievement_service
        with patch("src.services.achievement_service.achievement_service") as mock_as:
            # Mock get_all_achievements
            mock_as.get_all_achievements.return_value = {
                "first_step": MagicMock(),
                "week_warrior": MagicMock(),
            }

            # Mock individual achievement lookups
            mock_achievement = MagicMock()
            mock_achievement.rarity = "common"
            mock_achievement.name = "Week Warrior"
            mock_achievement.icon = "🏅"
            mock_as.get_achievement.return_value = mock_achievement

            await bot_mgr.achievements_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "Achievement" in reply or "🏆" in reply


# ===== /export Command =====


class TestExportCommand:
    """
    Tests for /export - data export (Phase 3F).

    Supports: /export csv, /export json, /export pdf
    """

    @pytest.mark.asyncio
    async def test_export_no_args_shows_options(self, bot_mgr, mock_fs):
        """No format specified should show available formats."""
        update = _make_update(text="/export")
        context = _make_context(args=[])

        with patch("src.bot.telegram_bot.rate_limiter") as mock_rl:
            mock_rl.check.return_value = (True, None)
            await bot_mgr.export_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "csv" in reply.lower()
        assert "json" in reply.lower()
        assert "pdf" in reply.lower()

    @pytest.mark.asyncio
    async def test_export_invalid_format(self, bot_mgr, mock_fs):
        """Invalid format should show error."""
        update = _make_update(text="/export xml")
        context = _make_context(args=["xml"])

        with patch("src.bot.telegram_bot.rate_limiter") as mock_rl:
            mock_rl.check.return_value = (True, None)
            await bot_mgr.export_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "Invalid" in reply or "invalid" in reply.lower()

    @pytest.mark.asyncio
    async def test_export_csv_success(self, bot_mgr, mock_fs):
        """Should generate CSV and send as document."""
        update = _make_update(text="/export csv")
        context = _make_context(args=["csv"])

        # Mock the status message
        status_msg = AsyncMock()
        update.message.reply_text.return_value = status_msg

        mock_result = {
            "buffer": MagicMock(),
            "filename": "export_2026-02-07.csv",
            "checkin_count": 30,
        }

        with patch("src.bot.telegram_bot.rate_limiter") as mock_rl, \
             patch(
                "src.services.export_service.export_user_data",
                new_callable=AsyncMock,
                return_value=mock_result,
             ):
            mock_rl.check.return_value = (True, None)
            await bot_mgr.export_command(update, context)

        # Should send a document
        update.message.reply_document.assert_called_once()


# ===== /leaderboard Command =====


class TestLeaderboardCommand:
    """Tests for /leaderboard - weekly rankings (Phase 3F)."""

    @pytest.mark.asyncio
    async def test_leaderboard_success(self, bot_mgr, mock_fs):
        """Should show formatted leaderboard."""
        update = _make_update(text="/leaderboard")
        context = _make_context()
        mock_fs.get_user.return_value = _make_user()

        with patch("src.services.social_service.calculate_leaderboard", return_value=[]), \
             patch("src.services.social_service.format_leaderboard_message", return_value="<b>Leaderboard</b>"):
            await bot_mgr.leaderboard_command(update, context)

        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_leaderboard_no_user(self, bot_mgr, mock_fs):
        """Unregistered user should see error."""
        update = _make_update(text="/leaderboard")
        context = _make_context()
        mock_fs.get_user.return_value = None

        with patch("src.utils.ux.ErrorMessages") as MockErrors:
            MockErrors.user_not_found.return_value = "Not found"
            await bot_mgr.leaderboard_command(update, context)

        update.message.reply_text.assert_called_once()


# ===== /invite Command =====


class TestInviteCommand:
    """Tests for /invite - referral link generation (Phase 3F)."""

    @pytest.mark.asyncio
    async def test_invite_shows_referral(self, bot_mgr, mock_fs):
        """Should generate and show referral link."""
        update = _make_update(text="/invite")
        context = _make_context()
        mock_fs.get_user.return_value = _make_user()

        # Mock bot.get_me for bot username
        bot_info = MagicMock()
        bot_info.username = "test_bot"
        bot_mgr.bot.get_me = AsyncMock(return_value=bot_info)

        with patch("src.services.social_service.generate_referral_link", return_value="https://t.me/test_bot?start=ref_123"), \
             patch("src.services.social_service.get_referral_stats", return_value={"total": 0}), \
             patch("src.services.social_service.format_referral_message", return_value="<b>Referral</b> link"):
            await bot_mgr.invite_command(update, context)

        update.message.reply_text.assert_called_once()


# ===== /resume Command =====


class TestResumeCommand:
    """Tests for /resume - resume incomplete check-in (Phase 3F)."""

    @pytest.mark.asyncio
    async def test_resume_no_partial_state(self, bot_mgr, mock_fs):
        """No incomplete check-in should inform user."""
        update = _make_update(text="/resume")
        context = _make_context()

        with patch("src.utils.ux.TimeoutManager") as MockTM:
            MockTM.get_partial_state.return_value = None
            await bot_mgr.resume_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "No Incomplete" in reply or "no" in reply.lower()

    @pytest.mark.asyncio
    async def test_resume_with_partial_state(self, bot_mgr, mock_fs):
        """With incomplete check-in, should show resume option."""
        update = _make_update(text="/resume")
        context = _make_context()

        with patch("src.utils.ux.TimeoutManager") as MockTM:
            MockTM.get_partial_state.return_value = {
                "conversation_type": "check-in",
                "step": 2,
            }
            await bot_mgr.resume_command(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "Incomplete" in reply or "unfinished" in reply.lower()


# ===== Callback Handlers =====


class TestModeSelectionCallback:
    """
    Tests for mode selection during onboarding.

    When a new user presses a mode button (e.g., "Optimization"),
    their profile is created with that mode.
    """

    @pytest.mark.asyncio
    async def test_mode_selection_creates_user(self, bot_mgr, mock_fs):
        """Selecting a mode should create user profile in Firestore."""
        update = _make_callback_update(data="mode_optimization")
        context = _make_context()

        await bot_mgr.mode_selection_callback(update, context)

        # User should be created
        mock_fs.create_user.assert_called_once()
        created_user = mock_fs.create_user.call_args[0][0]
        assert created_user.constitution_mode == "optimization"

        # Should acknowledge button press
        update.callback_query.answer.assert_called_once()

    @pytest.mark.asyncio
    async def test_mode_selection_shows_timezone_confirmation(self, bot_mgr, mock_fs):
        """After mode selection, should show timezone confirmation."""
        update = _make_callback_update(data="mode_maintenance")
        context = _make_context()

        await bot_mgr.mode_selection_callback(update, context)

        # Should send timezone message
        context.bot.send_message.assert_called_once()
        tz_msg = context.bot.send_message.call_args[1]["text"]
        assert "Timezone" in tz_msg or "IST" in tz_msg


class TestTimezoneConfirmationCallback:
    """Tests for timezone confirmation during onboarding."""

    @pytest.mark.asyncio
    async def test_timezone_confirmed(self, bot_mgr, mock_fs):
        """Confirming timezone during onboarding should set IST and complete onboarding."""
        update = _make_callback_update(data="tz_confirm")
        context = _make_context()

        await bot_mgr.timezone_confirmation_callback(update, context)

        # Should edit message to confirm timezone set
        update.callback_query.edit_message_text.assert_called_once()
        confirm_text = update.callback_query.edit_message_text.call_args[0][0]
        # Phase B: message now says "Timezone Set" instead of "Confirmed"
        assert "Timezone Set" in confirm_text or "India" in confirm_text

        # Should send streak explanation + first checkin prompt (2 messages)
        assert context.bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_timezone_change_request(self, bot_mgr, mock_fs):
        """Requesting timezone change during onboarding should show region picker."""
        update = _make_callback_update(data="tz_change")
        context = _make_context()

        await bot_mgr.timezone_confirmation_callback(update, context)

        edit_text = update.callback_query.edit_message_text.call_args[0][0]
        # Phase B: Now shows a region picker instead of "coming soon"
        assert "Region" in edit_text or "region" in edit_text
        # Should include inline keyboard with regions
        call_kwargs = update.callback_query.edit_message_text.call_args[1]
        assert "reply_markup" in call_kwargs

    @pytest.mark.asyncio
    async def test_timezone_region_selection(self, bot_mgr, mock_fs):
        """Selecting a region should show city picker."""
        update = _make_callback_update(data="tz_region_americas")
        context = _make_context()

        await bot_mgr.timezone_confirmation_callback(update, context)

        edit_text = update.callback_query.edit_message_text.call_args[0][0]
        # Should show city options for Americas
        assert "Americas" in edit_text or "City" in edit_text or "Choose" in edit_text

    @pytest.mark.asyncio
    async def test_timezone_set_custom(self, bot_mgr, mock_fs):
        """Setting a custom timezone during onboarding should save it."""
        update = _make_callback_update(data="tz_set_America/New_York")
        context = _make_context()

        await bot_mgr.timezone_confirmation_callback(update, context)

        # Should update user timezone in Firestore
        mock_fs.update_user.assert_called_once_with(
            str(update.callback_query.from_user.id),
            {"timezone": "America/New_York"}
        )

        # Should send streak + first check-in messages (onboarding flow)
        assert context.bot.send_message.call_count == 2

    @pytest.mark.asyncio
    async def test_timezone_cancel(self, bot_mgr, mock_fs):
        """Cancelling timezone change should keep current timezone."""
        update = _make_callback_update(data="tz_cancel")
        context = _make_context()

        await bot_mgr.timezone_confirmation_callback(update, context)

        edit_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "unchanged" in edit_text.lower()


class TestCareerCallback:
    """Tests for career mode selection callback (Phase 3D)."""

    @pytest.mark.asyncio
    async def test_career_skill_building(self, bot_mgr, mock_fs):
        """Selecting skill_building should update career mode."""
        update = _make_callback_update(data="career_skill")
        context = _make_context()
        mock_fs.update_user_career_mode.return_value = True

        await bot_mgr.career_callback(update, context)

        mock_fs.update_user_career_mode.assert_called_once_with(
            str(update.callback_query.from_user.id), "skill_building"
        )

    @pytest.mark.asyncio
    async def test_career_job_searching(self, bot_mgr, mock_fs):
        """Selecting job_searching should update career mode."""
        update = _make_callback_update(data="career_job")
        context = _make_context()
        mock_fs.update_user_career_mode.return_value = True

        await bot_mgr.career_callback(update, context)

        mock_fs.update_user_career_mode.assert_called_once_with(
            str(update.callback_query.from_user.id), "job_searching"
        )

    @pytest.mark.asyncio
    async def test_career_invalid_callback(self, bot_mgr, mock_fs):
        """Invalid career callback should show error."""
        update = _make_callback_update(data="career_invalid")
        context = _make_context()

        await bot_mgr.career_callback(update, context)

        edit_text = update.callback_query.edit_message_text.call_args[0][0]
        assert "Invalid" in edit_text or "❌" in edit_text


class TestPartnerCallbacks:
    """Tests for partner request accept/decline callbacks (Phase 3B)."""

    @pytest.mark.asyncio
    async def test_accept_partner(self, bot_mgr, mock_fs):
        """Accepting should link both users bidirectionally."""
        update = _make_callback_update(data="accept_partner:987654321")
        context = _make_context()

        requester = _make_user(user_id="987654321")
        accepter = _make_user(user_id="123456789")

        mock_fs.get_user.side_effect = [requester, accepter]

        await bot_mgr.accept_partner_callback(update, context)

        # Both users should be linked
        assert mock_fs.set_accountability_partner.call_count == 2
        # Notification sent to requester
        context.bot.send_message.assert_called_once()

    @pytest.mark.asyncio
    async def test_decline_partner(self, bot_mgr, mock_fs):
        """Declining should notify requester."""
        update = _make_callback_update(data="decline_partner:987654321")
        context = _make_context()

        requester = _make_user(user_id="987654321")
        decliner = _make_user(user_id="123456789")

        mock_fs.get_user.side_effect = [decliner, requester]

        await bot_mgr.decline_partner_callback(update, context)

        # Should edit message
        update.callback_query.edit_message_text.assert_called_once()
        # Should notify requester
        context.bot.send_message.assert_called_once()


# ===== General Message Handler =====


class TestGeneralMessageHandler:
    """
    Tests for handle_general_message - routes non-command messages.

    The handler uses a SupervisorAgent to classify intent:
    - "emotional" → Emotional Support Agent
    - "query" → Query Agent
    - "checkin" → Suggest /checkin command
    """

    @pytest.mark.asyncio
    async def test_emotional_intent(self, bot_mgr, mock_fs):
        """Emotional message should route to emotional agent."""
        update = _make_update(text="I'm feeling really lonely today")
        context = _make_context()

        with patch("src.agents.supervisor.SupervisorAgent") as MockSupervisor, \
             patch("src.agents.emotional_agent.get_emotional_agent") as mock_ea, \
             patch("src.agents.state.create_initial_state") as mock_state, \
             patch("src.bot.telegram_bot.settings") as mock_settings, \
             patch("src.bot.telegram_bot.rate_limiter") as mock_rl:

            mock_settings.gcp_project_id = "test"
            mock_rl.check.return_value = (True, None)

            # Supervisor classifies as emotional
            mock_supervisor = MockSupervisor.return_value
            mock_supervisor.classify_intent = AsyncMock(
                return_value={"intent": "emotional"}
            )

            # Emotional agent responds
            mock_agent = mock_ea.return_value
            mock_agent.process = AsyncMock(
                return_value={"response": "I hear you. Let's talk."}
            )

            mock_state.return_value = {}

            await bot_mgr.handle_general_message(update, context)

        update.message.reply_text.assert_called_once()
        reply = update.message.reply_text.call_args[0][0]
        assert "hear you" in reply.lower() or "talk" in reply.lower()

    @pytest.mark.asyncio
    async def test_checkin_intent(self, bot_mgr, mock_fs):
        """Checkin intent should suggest /checkin command."""
        update = _make_update(text="Ready to check in")
        context = _make_context()

        with patch("src.agents.supervisor.SupervisorAgent") as MockSupervisor, \
             patch("src.agents.state.create_initial_state") as mock_state, \
             patch("src.bot.telegram_bot.settings") as mock_settings, \
             patch("src.bot.telegram_bot.rate_limiter") as mock_rl:

            mock_settings.gcp_project_id = "test"
            mock_rl.check.return_value = (True, None)

            mock_supervisor = MockSupervisor.return_value
            mock_supervisor.classify_intent = AsyncMock(
                return_value={"intent": "checkin"}
            )

            mock_state.return_value = {}

            await bot_mgr.handle_general_message(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "/checkin" in reply

    @pytest.mark.asyncio
    async def test_error_handling(self, bot_mgr, mock_fs):
        """Handler should catch exceptions and show friendly error."""
        update = _make_update(text="Some message")
        context = _make_context()

        with patch("src.agents.supervisor.SupervisorAgent", side_effect=Exception("API error")), \
             patch("src.agents.state.create_initial_state"), \
             patch("src.bot.telegram_bot.settings") as mock_settings, \
             patch("src.bot.telegram_bot.rate_limiter") as mock_rl:

            mock_settings.gcp_project_id = "test"
            mock_rl.check.return_value = (True, None)

            await bot_mgr.handle_general_message(update, context)

        reply = update.message.reply_text.call_args[0][0]
        assert "error" in reply.lower() or "sorry" in reply.lower()
