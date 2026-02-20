# Phase 3: Fuzzy Command Matching + Natural Language Routing

## Summary

Phase 3 addresses the **rigid command matching** problem where commands required exact spelling (e.g., `/partner_status`), failing on typos or natural language. The solution adds three layers of intelligence:

1. **Fuzzy matching** for misspelled `/commands` using `difflib.SequenceMatcher`
2. **Keyword matching** for natural-language phrases (e.g., "how is my partner")
3. **"Did you mean?"** inline button suggestions for ambiguous matches

## Changes Made

### File: `src/bot/telegram_bot.py`

#### New Imports
- `difflib` (stdlib) for `SequenceMatcher`
- `typing.Optional`, `typing.Tuple` for type hints

#### New Class Attributes (on `TelegramBotManager`)

| Attribute | Purpose |
|-----------|---------|
| `REGISTERED_COMMANDS` | List of all 28 valid slash-command names |
| `COMMAND_KEYWORDS` | Dict mapping command names to natural-language keyword phrases (10 commands covered) |
| `AUTO_EXECUTE_THRESHOLD` | Score >= 0.85: auto-execute (obvious typo) |
| `SUGGEST_THRESHOLD` | Score >= 0.60: offer "Did you mean /X?" button |

#### New Methods

**`_fuzzy_match_command(text: str) -> Tuple[Optional[str], float]`**
- Strips the `/` and any `@bot` suffix from the attempted command
- Compares against all `REGISTERED_COMMANDS` using `SequenceMatcher.ratio()`
- Returns `(best_command_name, similarity_score)` or `(None, 0.0)`

**`_get_command_handler_map() -> dict`**
- Returns a dict mapping command name strings to their actual handler methods
- Used by both `handle_unknown_command` and `fuzzy_command_callback` to dispatch programmatically

**`_match_command_keywords(message: str) -> Optional[str]`**
- Scans the message for known keyword phrases
- Uses longest-match-wins strategy for specificity (e.g., "partner status" beats "status" when both match)
- Returns the matched command name or `None`

**`handle_unknown_command(update, context)` [async, group 2 handler]**
- Catch-all for any `/command` that didn't match a registered `CommandHandler`
- Three-tier response based on fuzzy score:
  - `>= 0.85`: Auto-correct and execute (e.g., `/staus` -> `/status`)
  - `0.60 - 0.84`: Show "Did you mean /X?" with inline button
  - `< 0.60`: Generic "unknown command, try /help" message

**`fuzzy_command_callback(update, context)` [async, callback handler for `fuzzy_cmd:*`]**
- Handles the inline button press from "Did you mean?" suggestions
- Dispatches to the matched command handler

#### Modified: `handle_general_message()`
- Added keyword matching check **before** the rate-limit check and LLM supervisor call
- If a keyword matches, the corresponding command handler is invoked directly, **saving an API call to Gemini**

#### Modified: `_register_handlers()`
- Added `MessageHandler(filters.COMMAND, self.handle_unknown_command)` at **group 2**
- Added `CallbackQueryHandler(self.fuzzy_command_callback, pattern="^fuzzy_cmd:")` at group 0

### Handler Priority Chain

```
Group 0: ConversationHandler (/checkin, /quickcheckin)
         26 CommandHandlers (exact matches)
         8 CallbackQueryHandlers (incl. new fuzzy_cmd: callback)
Group 1: MessageHandler (non-command text -> keyword match -> LLM supervisor)
Group 2: MessageHandler (unrecognized /commands -> fuzzy matching)
```

## How It Works

### Scenario 1: User types `/parner_status` (missing 't')

1. Telegram sends update with text `/parner_status`
2. Group 0 `CommandHandler("partner_status", ...)` does NOT match (different string)
3. Group 2 `handle_unknown_command` fires
4. `_fuzzy_match_command("/parner_status")` returns `("partner_status", 0.963)`
5. Score >= 0.85 -> auto-execute: calls `partner_status_command(update, context)`
6. User sees "Auto-correcting to /partner_status..." then the actual response

### Scenario 2: User types `/helo` (ambiguous)

1. No exact CommandHandler matches
2. `_fuzzy_match_command("/helo")` returns `("help", 0.75)`
3. Score between 0.60-0.85 -> show "Did you mean /help?" inline button
4. User taps button -> `fuzzy_command_callback` runs `/help`

### Scenario 3: User sends "how is my partner" (natural language)

1. Not a command -> goes to group 1 `handle_general_message`
2. `_match_command_keywords("how is my partner")` matches "how is my partner" keyword -> `partner_status`
3. `partner_status_command` is called directly
4. No Gemini API call needed (cost saving)

### Scenario 4: User types `/xyzabc` (gibberish)

1. `_fuzzy_match_command("/xyzabc")` returns score 0.33
2. Score < 0.60 -> "I don't recognize that command. Type /help"

## Test Results

### Fuzzy Command Matching (11/11 passed)
- `/staus` -> `/status` (0.909, AUTO)
- `/stauts` -> `/status` (0.833, SUGGEST)
- `/parner_status` -> `/partner_status` (0.963, AUTO)
- `/achivements` -> `/achievements` (0.957, AUTO)
- `/chckin` -> `/checkin` (0.923, AUTO)
- `/helo` -> `/help` (0.750, SUGGEST)
- `/reportt` -> `/report` (0.923, AUTO)
- `/weelky` -> `/weekly` (0.833, SUGGEST)
- `/use_sheild` -> `/use_shield` (0.900, AUTO)
- `/xyzabc` -> REJECTED (0.333 < 0.60)
- `/partner_stauts` -> `/partner_status` (0.929, AUTO)

### Keyword Matching (10/10 passed)
- "How is my partner doing?" -> /partner_status
- "show me my status" -> /status
- "I want to check in" -> /checkin
- "give me a report please" -> /report
- "show partner status" -> /partner_status (longest-match wins over /status)
- "what can you do?" -> /help
- "my achievements" -> /achievements
- "random unrelated message" -> None (correctly falls through)
- "I feel sad today" -> None (correctly falls through to LLM)
- "weekly stats please" -> /weekly

## Key Design Decisions

1. **Two thresholds instead of one**: Auto-executing on a low-confidence match would be confusing. The 0.85/0.60 split ensures users only get auto-corrected for obvious typos, while ambiguous cases get a confirmation button.

2. **Keyword matching before LLM**: Checking a small local dictionary is essentially free. This saves Gemini API calls for the most common natural-language patterns, while still falling through to the LLM supervisor for anything not covered.

3. **Longest-match-wins**: Prevents "partner status" from incorrectly matching "status" instead of "partner_status" when the message says "show partner status".

4. **Group 2 for unknown commands**: Using handler groups ensures the catch-all ONLY fires when no exact CommandHandler matched. This is critical - we never want fuzzy matching to intercept a valid command.

5. **Fail-open on gibberish**: If the score is too low, we just show a helpful message with `/help` rather than guessing wrong.

## Next Steps

- **Phase 4**: Deeper Per-Metric Tracking (Tier 1 breakdown in /status, new /metrics command)
- **Phase 5**: Automated Reports Every 3 Days
