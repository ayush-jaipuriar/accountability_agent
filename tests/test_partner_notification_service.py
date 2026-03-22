"""
Tests for partner check-in notification formatting and delivery.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.models.schemas import Tier1NonNegotiables, User, UserStreaks
from src.services.partner_notification_service import (
    build_partner_checkin_message,
    send_partner_checkin_notification,
)


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
            current_streak=10,
            longest_streak=20,
            last_checkin_date="2026-03-21",
            total_checkins=50,
        ),
        accountability_partner_id="222",
        accountability_partner_name="Partner",
        partner_checkin_notifications_enabled=True,
    )
    defaults.update(overrides)
    return User(**defaults)


def test_build_partner_checkin_message_excludes_private_fields():
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=False,
        deep_work=True,
        skill_building=False,
        zero_porn=False,
        boundaries=False,
    )

    message = build_partner_checkin_message("Ayush", tier1)

    assert "Sleep: met" in message
    assert "Training: missed" in message
    assert "Deep work: done" in message
    assert "Skill building: missed" in message
    assert "Porn" not in message
    assert "Boundaries" not in message


@pytest.mark.asyncio
async def test_send_partner_checkin_notification_initial():
    sender = _make_user()
    partner = _make_user(
        user_id="222",
        telegram_id=222,
        name="Partner",
        accountability_partner_id="111",
        accountability_partner_name="TestUser",
    )
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=False,
        skill_building=True,
        zero_porn=True,
        boundaries=True,
    )
    bot = AsyncMock()

    with patch("src.services.partner_notification_service.firestore_service") as mock_fs:
        mock_fs.get_user.return_value = partner
        mock_fs.get_partner_checkin_notification_status.return_value = None
        mock_fs.mark_partner_checkin_notification_sent.return_value = True

        result = await send_partner_checkin_notification(
            bot=bot,
            sender=sender,
            tier1=tier1,
            date="2026-03-22",
        )

    assert result["sent"] is True
    assert result["event_type"] == "initial"
    bot.send_message.assert_awaited_once()
    mock_fs.mark_partner_checkin_notification_sent.assert_called_once_with(
        user_id="111",
        date="2026-03-22",
        partner_id="222",
        event_type="initial",
    )


@pytest.mark.asyncio
async def test_send_partner_checkin_notification_update_after_correction():
    sender = _make_user()
    partner = _make_user(
        user_id="222",
        telegram_id=222,
        name="Partner",
        accountability_partner_id="111",
        accountability_partner_name="TestUser",
    )
    tier1 = Tier1NonNegotiables(
        sleep=False,
        training=True,
        deep_work=True,
        skill_building=True,
        zero_porn=True,
        boundaries=True,
    )
    bot = AsyncMock()

    with patch("src.services.partner_notification_service.firestore_service") as mock_fs:
        mock_fs.get_user.return_value = partner
        mock_fs.get_partner_checkin_notification_status.return_value = {
            "initial_sent": True,
            "updated_sent": False,
        }
        mock_fs.mark_partner_checkin_notification_sent.return_value = True

        result = await send_partner_checkin_notification(
            bot=bot,
            sender=sender,
            tier1=tier1,
            date="2026-03-22",
            is_update=True,
        )

    assert result["sent"] is True
    assert result["event_type"] == "updated"
    sent_text = bot.send_message.await_args.kwargs["text"]
    assert "updated today's check-in" in sent_text


@pytest.mark.asyncio
async def test_send_partner_checkin_notification_respects_disabled_setting():
    sender = _make_user(partner_checkin_notifications_enabled=False)
    tier1 = Tier1NonNegotiables(
        sleep=True,
        training=True,
        deep_work=True,
        skill_building=True,
        zero_porn=True,
        boundaries=True,
    )
    bot = AsyncMock()

    with patch("src.services.partner_notification_service.firestore_service") as mock_fs:
        result = await send_partner_checkin_notification(
            bot=bot,
            sender=sender,
            tier1=tier1,
            date="2026-03-22",
        )

    assert result["sent"] is False
    assert result["reason"] == "disabled"
    bot.send_message.assert_not_awaited()
