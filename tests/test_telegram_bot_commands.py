"""
Telegram Bot Command Handler Tests
====================================

Tests all command handlers in TelegramBotManager by mocking Telegram
Update/Context objects and the Firestore service layer.
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from datetime import datetime

from src.models.schemas import User, UserStreaks, StreakShields


# ===== Helpers =====

def _make_user(**overrides) -> User:
    defaults = dict(
        user_id="111",
        telegram_id=111,
        telegram_username="testuser",
        name="TestUser",
        timezone="Asia/Kolkata",
        constitution_mode="maintenance",
        career_mode="skill_building",
        streaks=UserStreaks(
            current_streak=10, longest_streak=20,
            last_checkin_date="2026-02-07", total_checkins=50
        ),
        streak_shields=StreakShields(total=3, used=1, available=2),
        achievements=["week_warrior"],
        accountability_partner_id=None,
        accountability_partner_name=None,
    )
    defaults.update(overrides)
    return User(**defaults)


def _make_update(user_id=111, username="testuser", first_name="TestUser",
                 text="/start"):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = username
    update.effective_user.first_name = first_name
    update.message = AsyncMock()
    update.message.text = text
    update.message.reply_text = AsyncMock()
    update.message.reply_document = AsyncMock()
    update.message.reply_photo = AsyncMock()
    update.message.message_id = 1234
    return update


def _make_context(args=None, user_data=None):
    context = MagicMock()
    context.args = args or []
    context.user_data = user_data if user_data is not None else {}
    context.bot = AsyncMock()
    context.bot.send_message = AsyncMock()
    context.bot.get_me = AsyncMock(return_value=MagicMock(username="test_bot"))
    return context


def _make_callback_update(user_id=111, data="mode_optimization"):
    update = MagicMock()
    update.effective_user = MagicMock()
    update.effective_user.id = user_id
    update.effective_user.username = "testuser"
    update.effective_user.first_name = "TestUser"
    query = AsyncMock()
    query.data = data
    query.from_user = MagicMock()
    query.from_user.id = user_id
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    query.message = AsyncMock()
    query.message.reply_text = AsyncMock()
    update.callback_query = query
    update.message = None
    return update


@pytest.fixture
def bot_manager():
    with patch('src.bot.telegram_bot.Application') as MockApp, \
         patch('src.bot.telegram_bot.settings') as mock_settings, \
         patch('src.bot.telegram_bot.firestore_service') as mock_fs, \
         patch('src.bot.telegram_bot.rate_limiter') as mock_rl, \
         patch('src.bot.telegram_bot.metrics') as mock_metrics:

        mock_app = MagicMock()
        MockApp.builder.return_value.token.return_value.build.return_value = mock_app
        mock_app.bot = AsyncMock()

        mock_settings.telegram_bot_token = "fake_token"
        mock_settings.gcp_project_id = "test-project"
        mock_settings.admin_telegram_ids = "111"

        mock_rl.check.return_value = (True, None)

        from src.bot.telegram_bot import TelegramBotManager
        manager = TelegramBotManager(token="fake_token")

        manager._mock_fs = mock_fs
        manager._mock_rl = mock_rl
        manager._mock_metrics = mock_metrics
        manager._mock_settings = mock_settings

        yield manager


class TestStartCommand:
    @pytest.mark.asyncio
    async def test_new_user_gets_onboarding(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = None
        update = _make_update()
        context = _make_context()
        await bot_manager.start_command(update, context)
        assert update.message.reply_text.call_count >= 2
        first_text = update.message.reply_text.call_args_list[0][0][0]
        assert "Welcome" in first_text

    @pytest.mark.asyncio
    async def test_returning_user_gets_stats(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user()
        update = _make_update()
        context = _make_context()
        await bot_manager.start_command(update, context)
        update.message.reply_text.assert_called_once()
        text = update.message.reply_text.call_args[0][0]
        assert "Welcome back" in text

    @pytest.mark.asyncio
    async def test_referral_code_parsed(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = None
        update = _make_update()
        context = _make_context(args=["ref_999"])
        await bot_manager.start_command(update, context)
        assert context.user_data.get("referral_user_id") == "999"


class TestHelpCommand:
    @pytest.mark.asyncio
    async def test_help_shows_commands(self, bot_manager):
        update = _make_update(text="/help")
        context = _make_context()
        with patch('src.utils.ux.generate_help_text',
                   return_value="<b>Help</b>"):
            await bot_manager.help_command(update, context)
        update.message.reply_text.assert_called_once()
        assert update.message.reply_text.call_args[1].get('parse_mode') == 'HTML'


class TestStatusCommand:
    @pytest.mark.asyncio
    async def test_user_not_found(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = None
        update = _make_update(text="/status")
        context = _make_context()
        await bot_manager.status_command(update, context)
        update.message.reply_text.assert_called_once()

    @pytest.mark.asyncio
    async def test_status_with_existing_user(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user()
        bot_manager._mock_fs.get_recent_checkins.return_value = []
        bot_manager._mock_fs.checkin_exists.return_value = False
        update = _make_update(text="/status")
        context = _make_context()
        with patch('src.utils.timezone_utils.get_current_date',
                   return_value="2026-02-07"), \
             patch('src.utils.streak.get_streak_emoji', return_value="X"):
            await bot_manager.status_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Streak" in text

    @pytest.mark.asyncio
    async def test_status_checked_in_today(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user()
        bot_manager._mock_fs.get_recent_checkins.return_value = []
        bot_manager._mock_fs.checkin_exists.return_value = True
        update = _make_update(text="/status")
        context = _make_context()
        with patch('src.utils.timezone_utils.get_current_date',
                   return_value="2026-02-07"), \
             patch('src.utils.streak.get_streak_emoji', return_value="X"):
            await bot_manager.status_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "complete" in text.lower()


class TestModeCommand:
    @pytest.mark.asyncio
    async def test_mode_no_args_shows_info(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user(
            constitution_mode="maintenance")
        update = _make_update(text="/mode")
        context = _make_context(args=[])
        await bot_manager.mode_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Maintenance" in text

    @pytest.mark.asyncio
    async def test_mode_direct_switch(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user(
            constitution_mode="maintenance")
        update = _make_update(text="/mode optimization")
        context = _make_context(args=["optimization"])
        await bot_manager.mode_command(update, context)
        bot_manager._mock_fs.update_user_mode.assert_called_once_with(
            "111", "optimization")

    @pytest.mark.asyncio
    async def test_mode_same_mode_noop(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user(
            constitution_mode="maintenance")
        update = _make_update(text="/mode maintenance")
        context = _make_context(args=["maintenance"])
        await bot_manager.mode_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "already" in text.lower()

    @pytest.mark.asyncio
    async def test_mode_invalid_value(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user()
        update = _make_update(text="/mode turbo")
        context = _make_context(args=["turbo"])
        await bot_manager.mode_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Unknown" in text or "unknown" in text.lower()

    @pytest.mark.asyncio
    async def test_mode_user_not_found(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = None
        update = _make_update(text="/mode")
        context = _make_context()
        await bot_manager.mode_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "not found" in text.lower() or "/start" in text


class TestModeChangeCallback:
    @pytest.mark.asyncio
    async def test_mode_change_via_button(self, bot_manager):
        update = _make_callback_update(data="change_mode_survival")
        context = _make_context()
        await bot_manager.mode_change_callback(update, context)
        update.callback_query.answer.assert_called_once()
        bot_manager._mock_fs.update_user_mode.assert_called_once_with(
            "111", "survival")

    @pytest.mark.asyncio
    async def test_invalid_mode_callback(self, bot_manager):
        update = _make_callback_update(data="change_mode_invalid")
        context = _make_context()
        await bot_manager.mode_change_callback(update, context)
        text = update.callback_query.edit_message_text.call_args[0][0]
        assert "Invalid" in text


class TestUseShieldCommand:
    @pytest.mark.asyncio
    async def test_no_shields_available(self, bot_manager):
        user = _make_user()
        user.streak_shields = StreakShields(total=3, used=3, available=0)
        bot_manager._mock_fs.get_user.return_value = user
        update = _make_update(text="/use_shield")
        context = _make_context()
        await bot_manager.use_shield_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "No Streak Shields" in text

    @pytest.mark.asyncio
    async def test_shield_not_needed(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user()
        bot_manager._mock_fs.checkin_exists.return_value = True
        update = _make_update(text="/use_shield")
        context = _make_context()
        with patch('src.utils.timezone_utils.get_checkin_date',
                   return_value="2026-02-07"):
            await bot_manager.use_shield_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Not Needed" in text or "already" in text.lower()

    @pytest.mark.asyncio
    async def test_shield_used_successfully(self, bot_manager):
        user = _make_user()
        updated = _make_user()
        updated.streak_shields = StreakShields(total=3, used=2, available=1)
        bot_manager._mock_fs.get_user.side_effect = [user, updated]
        bot_manager._mock_fs.checkin_exists.return_value = False
        bot_manager._mock_fs.use_streak_shield.return_value = True
        update = _make_update(text="/use_shield")
        context = _make_context()
        with patch('src.utils.timezone_utils.get_checkin_date',
                   return_value="2026-02-07"), \
             patch('src.utils.streak.calculate_days_without_checkin',
                   return_value=1):
            await bot_manager.use_shield_command(update, context)
        bot_manager._mock_fs.use_streak_shield.assert_called_once_with("111")


class TestSetPartnerCommand:
    @pytest.mark.asyncio
    async def test_no_username_provided(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user()
        update = _make_update(text="/set_partner")
        context = _make_context(args=[])
        await bot_manager.set_partner_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Format" in text or "/set_partner" in text

    @pytest.mark.asyncio
    async def test_partner_not_found(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user()
        bot_manager._mock_fs.get_user_by_telegram_username.return_value = None
        update = _make_update(text="/set_partner @unknown")
        context = _make_context(args=["@unknown"])
        await bot_manager.set_partner_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "not found" in text.lower()

    @pytest.mark.asyncio
    async def test_cannot_partner_with_self(self, bot_manager):
        user = _make_user(user_id="111")
        partner = _make_user(user_id="111", telegram_username="testuser")
        bot_manager._mock_fs.get_user.return_value = user
        bot_manager._mock_fs.get_user_by_telegram_username.return_value = partner
        update = _make_update(text="/set_partner @testuser")
        context = _make_context(args=["@testuser"])
        await bot_manager.set_partner_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "own" in text.lower() or "yourself" in text.lower()

    @pytest.mark.asyncio
    async def test_partner_request_sent(self, bot_manager):
        user = _make_user(user_id="111")
        partner = _make_user(
            user_id="222", telegram_id=222,
            telegram_username="partner_user", name="Partner")
        bot_manager._mock_fs.get_user.return_value = user
        bot_manager._mock_fs.get_user_by_telegram_username.return_value = partner
        update = _make_update(text="/set_partner @partner_user")
        context = _make_context(args=["@partner_user"])
        await bot_manager.set_partner_command(update, context)
        context.bot.send_message.assert_called_once()
        assert context.bot.send_message.call_args[1]['chat_id'] == 222


class TestPartnerCallbacks:
    @pytest.mark.asyncio
    async def test_accept_partner(self, bot_manager):
        requester = _make_user(user_id="111", telegram_id=111, name="Req")
        accepter = _make_user(user_id="222", telegram_id=222, name="Acc")
        bot_manager._mock_fs.get_user.side_effect = [requester, accepter]
        update = _make_callback_update(user_id=222, data="accept_partner:111")
        context = _make_context()
        await bot_manager.accept_partner_callback(update, context)
        assert bot_manager._mock_fs.set_accountability_partner.call_count == 2

    @pytest.mark.asyncio
    async def test_decline_partner(self, bot_manager):
        requester = _make_user(user_id="111", telegram_id=111, name="Req")
        decliner = _make_user(user_id="222", telegram_id=222, name="Dec")
        bot_manager._mock_fs.get_user.side_effect = [requester, decliner]
        update = _make_callback_update(user_id=222, data="decline_partner:111")
        context = _make_context()
        await bot_manager.decline_partner_callback(update, context)
        bot_manager._mock_fs.set_accountability_partner.assert_not_called()


class TestUnlinkPartnerCommand:
    @pytest.mark.asyncio
    async def test_no_partner(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user(
            accountability_partner_id=None)
        update = _make_update(text="/unlink_partner")
        context = _make_context()
        await bot_manager.unlink_partner_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "don" in text.lower() or "no" in text.lower()

    @pytest.mark.asyncio
    async def test_unlink_both(self, bot_manager):
        user = _make_user(accountability_partner_id="222")
        partner = _make_user(user_id="222", telegram_id=222, name="P")
        bot_manager._mock_fs.get_user.side_effect = [user, partner]
        update = _make_update(text="/unlink_partner")
        context = _make_context()
        await bot_manager.unlink_partner_command(update, context)
        assert bot_manager._mock_fs.set_accountability_partner.call_count == 2


class TestAchievementsCommand:
    @pytest.mark.asyncio
    async def test_no_achievements(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user(achievements=[])
        update = _make_update(text="/achievements")
        context = _make_context()
        await bot_manager.achievements_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "achievement" in text.lower()

    @pytest.mark.asyncio
    async def test_with_achievements(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user(
            achievements=["week_warrior", "first_step"])
        mock_ach = MagicMock()
        mock_ach.name = "Week Warrior"
        mock_ach.icon = "X"
        mock_ach.rarity = "common"
        update = _make_update(text="/achievements")
        context = _make_context()
        with patch('src.services.achievement_service.achievement_service') as mock_as:
            mock_as.get_all_achievements.return_value = {"week_warrior": mock_ach}
            mock_as.get_achievement.return_value = mock_ach
            await bot_manager.achievements_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Achievement" in text or "achievement" in text.lower()


class TestCareerCommand:
    @pytest.mark.asyncio
    async def test_career_shows_current_mode(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user(
            career_mode="skill_building")
        update = _make_update(text="/career")
        context = _make_context()
        await bot_manager.career_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Career" in text

    @pytest.mark.asyncio
    async def test_career_callback_updates_mode(self, bot_manager):
        bot_manager._mock_fs.update_user_career_mode.return_value = True
        update = _make_callback_update(data="career_job")
        context = _make_context()
        await bot_manager.career_callback(update, context)
        bot_manager._mock_fs.update_user_career_mode.assert_called_once_with(
            "111", "job_searching")

    @pytest.mark.asyncio
    async def test_career_callback_failure(self, bot_manager):
        bot_manager._mock_fs.update_user_career_mode.return_value = False
        update = _make_callback_update(data="career_employed")
        context = _make_context()
        await bot_manager.career_callback(update, context)
        text = update.callback_query.edit_message_text.call_args[0][0]
        assert "Failed" in text or "failed" in text.lower()


class TestExportCommand:
    @pytest.mark.asyncio
    async def test_export_no_format(self, bot_manager):
        update = _make_update(text="/export")
        context = _make_context(args=[])
        await bot_manager.export_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "csv" in text.lower()

    @pytest.mark.asyncio
    async def test_export_invalid_format(self, bot_manager):
        update = _make_update(text="/export xml")
        context = _make_context(args=["xml"])
        await bot_manager.export_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Invalid" in text


class TestCorrectCommand:
    @pytest.mark.asyncio
    async def test_no_checkin_to_correct(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user()
        bot_manager._mock_fs.get_checkin.return_value = None
        update = _make_update(text="/correct")
        context = _make_context()
        with patch('src.utils.timezone_utils.get_current_date',
                   return_value="2026-02-07"):
            await bot_manager.correct_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "No check-in" in text or "no check-in" in text.lower()

    @pytest.mark.asyncio
    async def test_already_corrected(self, bot_manager):
        bot_manager._mock_fs.get_user.return_value = _make_user()
        checkin = MagicMock()
        checkin.corrected_at = datetime.utcnow()
        bot_manager._mock_fs.get_checkin.return_value = checkin
        update = _make_update(text="/correct")
        context = _make_context()
        with patch('src.utils.timezone_utils.get_current_date',
                   return_value="2026-02-07"):
            await bot_manager.correct_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "already" in text.lower() or "1 correction" in text.lower()


class TestResumeCommand:
    @pytest.mark.asyncio
    async def test_no_incomplete(self, bot_manager):
        update = _make_update(text="/resume")
        context = _make_context()
        with patch('src.utils.ux.TimeoutManager') as mock_tm:
            mock_tm.get_partial_state.return_value = None
            await bot_manager.resume_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "No Incomplete" in text

    @pytest.mark.asyncio
    async def test_has_incomplete(self, bot_manager):
        update = _make_update(text="/resume")
        context = _make_context()
        with patch('src.utils.ux.TimeoutManager') as mock_tm:
            mock_tm.get_partial_state.return_value = {
                "conversation_type": "check-in"
            }
            await bot_manager.resume_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Incomplete" in text


class TestAdminStatusCommand:
    @pytest.mark.asyncio
    async def test_admin_sees_status(self, bot_manager):
        bot_manager._mock_metrics.format_admin_status.return_value = (
            "<b>Admin Status</b>")
        update = _make_update(user_id=111, text="/admin_status")
        context = _make_context()
        await bot_manager.admin_status_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Admin Status" in text

    @pytest.mark.asyncio
    async def test_non_admin_blocked(self, bot_manager):
        update = _make_update(user_id=999, text="/admin_status")
        context = _make_context()
        await bot_manager.admin_status_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "Unknown" in text


class TestGeneralMessageHandler:
    @pytest.mark.asyncio
    async def test_checkin_intent(self, bot_manager):
        update = _make_update(text="I want to check in")
        context = _make_context()
        with patch('src.agents.supervisor.SupervisorAgent') as MockSup, \
             patch('src.agents.state.create_initial_state',
                   return_value={"intent": None}):
            MockSup.return_value.classify_intent = AsyncMock(
                return_value={"intent": "checkin"})
            await bot_manager.handle_general_message(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "/checkin" in text

    @pytest.mark.asyncio
    async def test_error_handling(self, bot_manager):
        update = _make_update(text="test message")
        context = _make_context()
        with patch('src.agents.supervisor.SupervisorAgent',
                   side_effect=Exception("boom")):
            await bot_manager.handle_general_message(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "error" in text.lower() or "Sorry" in text


class TestRateLimiting:
    @pytest.mark.asyncio
    async def test_rate_limited_blocked(self, bot_manager):
        bot_manager._mock_rl.check.return_value = (False, "Please wait 5m")
        bot_manager._mock_fs.get_user.return_value = _make_user()
        update = _make_update(text="/leaderboard")
        context = _make_context()
        await bot_manager.leaderboard_command(update, context)
        text = update.message.reply_text.call_args[0][0]
        assert "wait" in text.lower()


class TestOnboardingCallbacks:
    @pytest.mark.asyncio
    async def test_mode_selection_creates_user(self, bot_manager):
        update = _make_callback_update(data="mode_optimization")
        context = _make_context()
        await bot_manager.mode_selection_callback(update, context)
        bot_manager._mock_fs.create_user.assert_called_once()
        created_user = bot_manager._mock_fs.create_user.call_args[0][0]
        assert created_user.constitution_mode == "optimization"

    @pytest.mark.asyncio
    async def test_timezone_confirm_ist(self, bot_manager):
        update = _make_callback_update(data="tz_confirm")
        context = _make_context(user_data={})
        with patch.object(bot_manager, '_finalize_timezone_onboarding',
                          new_callable=AsyncMock) as mock_fin:
            await bot_manager.timezone_confirmation_callback(update, context)
            mock_fin.assert_called_once()
