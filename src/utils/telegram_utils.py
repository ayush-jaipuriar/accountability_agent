"""
Telegram Bot Utilities
======================

Safe wrappers for common Telegram bot operations.

These helpers prevent common mistakes that caused production bugs:
- update.message being None in callbacks
- Unescaped HTML causing parse errors
- Inconsistent parse_mode usage
"""

import html
import re
from telegram import Update


# Allowed Telegram HTML tags
ALLOWED_HTML_TAGS = {"b", "i", "u", "s", "code", "pre", "a", "tg-spoiler", "blockquote"}


def _escape_unsafe_html(text: str) -> str:
    """
    Escape any '<', '>', '&' that are NOT part of an allowed Telegram HTML tag.

    This prevents "unsupported start tag" and parse errors when user data contains
    characters like '<6' or '&' which Telegram interprets as HTML entities/tags.

    Strategy:
        1. Escape ALL <, >, & to &lt;, &gt;, &amp;
        2. Restore strictly valid Telegram tags and allowed attributes
    """
    if not text:
        return text

    # Step 1: Escape everything
    escaped = html.escape(text)

    # Step 2: Restore valid simple tags without attributes
    # <b>, <i>, <u>, <s>, <pre>, <tg-spoiler>, <blockquote>, <code>, <a> closing tags
    simple_tags = r"(/?(?:b|i|u|s|pre|tg-spoiler|blockquote|code|a))"
    escaped = re.sub(rf"&lt;{simple_tags}&gt;", r"<\1>", escaped, flags=re.IGNORECASE)

    # Restore allowed attribute variants:
    # <a href="...">
    escaped = re.sub(
        r"&lt;a\s+href=(&quot;|&#x27;|&#39;)(.*?)\1&gt;",
        lambda m: f'<a href="{m.group(2)}">' if m.group(1) == '&quot;' else f"<a href='{m.group(2)}'>",
        escaped,
        flags=re.IGNORECASE
    )
    # <blockquote expandable>
    escaped = re.sub(
        r"&lt;blockquote\s+expandable&gt;",
        r"<blockquote expandable>",
        escaped,
        flags=re.IGNORECASE
    )
    # <code class="language-...">
    escaped = re.sub(
        r"&lt;code\s+class=(&quot;|&#x27;|&#39;)(language-[a-zA-Z0-9_-]+)\1&gt;",
        r'<code class="\2">',
        escaped,
        flags=re.IGNORECASE
    )

    return escaped


def safe_reply_html(message, text: str, **kwargs) -> None:
    """
    Safely send an HTML-formatted message.

    Automatically escapes any '<' characters that aren't allowed Telegram
    HTML tags. Always sets parse_mode='HTML'.

    Usage:
        safe_reply_html(update.message, f"<b>Hello</b> {user_name}")
        safe_reply_html(query.message, f"<i>Progress:</i> {progress}%")

    Args:
        message: telegram.Message object (from update.message or query.message)
        text: Text to send. Can contain allowed HTML tags.
        **kwargs: Additional arguments for reply_text
    """
    safe_text = _escape_unsafe_html(text)
    kwargs["parse_mode"] = "HTML"
    return message.reply_text(safe_text, **kwargs)


def safe_edit_html(message, text: str, **kwargs) -> None:
    """
    Safely edit a message with HTML formatting.

    Same escaping as safe_reply_html but for edit_message_text.

    Usage:
        safe_edit_html(query.message, "<b>Updated!</b> Progress: 50%")
    """
    safe_text = _escape_unsafe_html(text)
    kwargs["parse_mode"] = "HTML"
    return message.edit_text(safe_text, **kwargs)


def get_message_from_update(update: Update):
    """
    Safely get the message object from a Telegram Update.

    When called from a callback query handler (inline button tap),
    update.message is None. This helper falls back to callback_query.message.

    Returns:
        telegram.Message or None
    """
    if update.message:
        return update.message
    if update.callback_query and update.callback_query.message:
        return update.callback_query.message
    return None


def get_user_from_update(update: Update):
    """
    Safely get the user object from a Telegram Update.

    Works for both message updates and callback query updates.
    """
    if update.message:
        return update.message.from_user
    if update.callback_query and update.callback_query.from_user:
        return update.callback_query.from_user
    return None
