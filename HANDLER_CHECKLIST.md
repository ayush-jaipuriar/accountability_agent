# Handler Code Review Checklist

**Use this checklist for EVERY pull request that touches:**
- `src/bot/telegram_bot.py`
- `src/bot/conversation.py`
- `src/bot/handlers/` (if created)
- Any callback query handler
- Any new `/command`

---

## Adding a New Command

- [ ] Added command name to `REGISTERED_COMMANDS`
- [ ] Added `CommandHandler("cmd_name", self.cmd_name_command)` in `_register_handlers()`
- [ ] Added handler method to `_get_command_handler_map()` dict
- [ ] Added natural language keywords to `COMMAND_KEYWORDS` (if applicable)
- [ ] Added rate limiting tier in `_check_rate_limit()` (defaults to `standard`)
- [ ] Added test in `tests/test_telegram_bot_commands.py`
- [ ] Added command to `/help` output

## Message Safety

- [ ] If message contains HTML tags (`<b>`, `<i>`, `<code>`), `parse_mode='HTML'` is set
- [ ] If `parse_mode='HTML'` is used, all `<` and `>` from user data are escaped with `html.escape()`
- [ ] No raw `message.reply_text(..., parse_mode='HTML')` — use `safe_reply_html()` instead
- [ ] No `update.message.reply_text()` inside callback query handlers
- [ ] Callback handlers use `_get_message_from_update(update)` for safe message access

## Callback Query Handlers

- [ ] Handler starts with `query = update.callback_query` and `await query.answer()`
- [ ] Never access `update.message` directly — always use `query.message` or `_get_message_from_update()`
- [ ] `edit_message_text` or `reply_text` is called on `query.message`, not `update.message`
- [ ] Callback data prefix is unique and doesn't conflict with existing prefixes

## Feature Flags

- [ ] If this is a new feature, it's gated behind a feature flag in `config.py`
- [ ] Handler registration is conditional: `if settings.enable_feature:`
- [ ] Flag default is `False` for risky features, `True` for stable ones
- [ ] Feature can be disabled without code deploy (env var toggle)

## Code Quality

- [ ] No nested imports inside functions that shadow module-level imports
- [ ] No bare `except:` clauses (use `except Exception:` minimum)
- [ ] All async functions have at least one `await` call
- [ ] No mutable default arguments (`def f(x=[])`)
- [ ] All user-facing strings use `safe_reply_html()` or have `parse_mode` explicitly set

## Testing

- [ ] Unit test added for service/business logic
- [ ] Integration test added for handler flow (if state machine involved)
- [ ] Callback path tested separately from command path
- [ ] HTML parse mode tested with edge cases (`<`, `>`, `&`)
- [ ] Test run with `pytest tests/` passes

## Documentation

- [ ] `AGENTS.md` updated if deployment process changed
- [ ] `DEPLOYMENT_LOG_*.md` will be created/updated after deploy
- [ ] `CHANGELOG.md` updated with user-facing description

---

## Quick Reference: Common Mistakes

| Mistake | Why It Breaks | Fix |
|---------|--------------|-----|
| `update.message.reply_text()` in callback | `update.message` is `None` for callbacks | Use `_get_message_from_update(update)` |
| `<b>text</b>` without `parse_mode='HTML'` | Users see raw `<b>` tags | Always set `parse_mode='HTML'` or use `safe_reply_html()` |
| Unescaped `<` in HTML parse_mode | Telegram rejects: "unsupported start tag" | Use `html.escape()` on user data |
| Missing command in `_get_command_handler_map()` | Fuzzy matching breaks for this command | Add to map when adding command |
| Nested import shadowing module-level | `UnboundLocalError` at runtime | Remove nested import, use module-level |
| Handler in group >0 for commands | Fires after real handler, double-responds | Add guard: check if command already in REGISTERED_COMMANDS |
| Hardcoded model name | Model deprecated → 404 errors | Centralize in `config.py` |

---

**Before merging any PR touching handlers, a second person must verify this checklist.**
