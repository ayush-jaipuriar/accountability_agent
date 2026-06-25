"""
Unit Tests for Telegram Utilities
=================================

Tests the HTML escaping and restoration logic in telegram_utils.py.
"""

import pytest
from src.utils.telegram_utils import _escape_unsafe_html


def test_escape_unsafe_html_none():
    assert _escape_unsafe_html("") == ""
    assert _escape_unsafe_html(None) is None


def test_escape_unsafe_html_no_tags():
    # Regular text without HTML tags should be escaped normally if they contain <, >, &
    assert _escape_unsafe_html("Sleep <6 hours") == "Sleep &lt;6 hours"
    assert _escape_unsafe_html("A & B > C") == "A &amp; B &gt; C"


def test_escape_unsafe_html_allowed_tags():
    # Allowed tags should be preserved intact
    assert _escape_unsafe_html("<b>Bold Text</b>") == "<b>Bold Text</b>"
    assert _escape_unsafe_html("<i>Italic Text</i>") == "<i>Italic Text</i>"
    assert _escape_unsafe_html("<code>x = 42</code>") == "<code>x = 42</code>"
    assert _escape_unsafe_html("<tg-spoiler>Secret</tg-spoiler>") == "<tg-spoiler>Secret</tg-spoiler>"
    assert _escape_unsafe_html("<blockquote>My blockquote</blockquote>") == "<blockquote>My blockquote</blockquote>"


def test_escape_unsafe_html_allowed_tags_with_attributes():
    # Tags with attributes (like links and expandable blockquotes) should be restored
    assert _escape_unsafe_html("<blockquote expandable>Collapsed</blockquote>") == "<blockquote expandable>Collapsed</blockquote>"
    assert _escape_unsafe_html('<a href="https://example.com">Visit site</a>') == '<a href="https://example.com">Visit site</a>'
    assert _escape_unsafe_html("<a href='https://example.com'>Visit site</a>") == "<a href='https://example.com'>Visit site</a>"
    assert _escape_unsafe_html('<pre><code class="language-python">print("Hi")</code></pre>') == '<pre><code class="language-python">print(&quot;Hi&quot;)</code></pre>'


def test_escape_unsafe_html_mixed_and_invalid_tags():
    # Invalid tags should remain escaped
    assert _escape_unsafe_html("<div>Invalid</div>") == "&lt;div&gt;Invalid&lt;/div&gt;"
    assert _escape_unsafe_html("<b>Valid</b> and <h1>Invalid</h1>") == "<b>Valid</b> and &lt;h1&gt;Invalid&lt;/h1&gt;"
    
    # Combined allowed tags with unsafe text
    assert _escape_unsafe_html("<b>Sleep <6 hours</b>") == "<b>Sleep &lt;6 hours</b>"
    assert _escape_unsafe_html("<blockquote>A & B > C</blockquote>") == "<blockquote>A &amp; B &gt; C</blockquote>"
