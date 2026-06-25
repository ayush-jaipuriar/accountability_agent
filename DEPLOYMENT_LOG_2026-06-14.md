# Deployment Log: v2.3 Telegram HTML Blockquotes & Sanitizer Upgrade

**Date:** 2026-06-14  
**Release:** v2.3 (Minor/Patch)  
**Phases Deployed:** Regex HTML Sanitizer Upgrade, Collapsible & Standard Blockquote Formatting, AI Coaching Prompt Updates, Interactive Mode layout cleanup.  
**Test Count:** 1057 passed, 0 failed  
**Pre-Deploy Check:** 16/16 passed  
**Image Tag:** `manual-20260614-204500`  
**Revision:** `accountability-agent-00016-jdt`  
**Deployed At:** 2026-06-14 15:15:46 UTC  

---

## Deployment Summary

This release upgrades the Telegram HTML formatting capabilities of the accountability agent. It fixes the simplified HTML tag restorer in `telegram_utils.py` by introducing a regex-based parser that preserves allowed tags while supporting single-quoted, double-quoted, and unquoted attributes (enabling links and expandable blockquotes to be transmitted safely).
It applies collapsible blockquotes (`<blockquote expandable>`) to verbose user-facing content like error safeguards, inactivity timeouts, the `/mode` command handbook, and the emotional support agent's step-by-step actions to maintain a clean chat layout on mobile devices.

---

## Features Deployed

### 1. Regex HTML Sanitizer & Sanitization Update
* Updated `src/utils/telegram_utils.py` to add `"blockquote"` to `ALLOWED_HTML_TAGS` whitelist.
* Replaced the simplified opening-tag restoration with a robust regex-based HTML entity restorer. This matches opening/closing tags of allowed elements and correctly unescapes single quotes, double quotes, and ampersands inside their attributes (enabling `<blockquote expandable>` and `<a href="url?a=1&b=2">` to pass through safely while escaping other raw characters).

### 2. Centralized UX Error & Warning Layouts
* Updated `src/utils/ux.py` to place detailed technical details and troubleshooting steps inside `<blockquote expandable>...</blockquote>` for `ErrorMessages.service_unavailable()`, `ErrorMessages.generic_error()`, and `TimeoutManager.get_timeout_warning()`.

### 3. AI Coaching Prompt Engineering
* Updated the prompt instructions in `src/agents/emotional_agent.py` to guide Gemini to wrap the detailed step-by-step action instructions in `<blockquote expandable>` tags.

### 4. Interactive Mode Info Refactoring
* Refactored the `/mode` command handler in `src/bot/telegram_bot.py` so that details of the three different constitution modes (Optimization, Maintenance, Survival) are wrapped in a single collapsible blockquote, displaying the active mode clearly at the top.

---

## Files Changed

### Modified Files
* `src/utils/telegram_utils.py` — Upgraded `_escape_unsafe_html` and whitelisted `blockquote`
* `src/utils/ux.py` — Configured error messages and timeout warnings with expandable blockquotes
* `src/agents/emotional_agent.py` — Updated LLM prompt template to output expandable blockquotes for action items
* `src/bot/telegram_bot.py` — Wrapped mode rules in an expandable blockquote for the `/mode` command

### New Files
* `tests/test_telegram_utils.py` — Unit tests for the HTML sanitizer (escaping, restoration, attributes)

---

## Deployment Commands Executed

```bash
# Verify active GCP project
gcloud config set project accountability-agent

# Snapshot current configuration
gcloud run services describe accountability-agent --platform=managed --region=us-central1 --format=export > /tmp/accountability-agent.predeploy.yaml

# Run project test gate
pytest tests

# Pre-deploy checks
python3 scripts/pre_deploy_check.py

# Cloud Build submission (remote compilation)
gcloud builds submit --tag us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260614-204500

# Service revision rollout in-place
gcloud run services update accountability-agent \
  --platform=managed \
  --region=us-central1 \
  --image us-central1-docker.pkg.dev/accountability-agent/cloud-run-source-deploy/accountability-agent:manual-20260614-204500
```

---

## Post-Deploy Verification Results

- [x] Health endpoint returns 200: `{"status":"healthy","service":"constitution-agent",...}`
- [x] Only one production service active (`accountability-agent` in `us-central1`)
- [x] New revision `accountability-agent-00016-jdt` serving 100% traffic
- [x] Runtime shape fully preserved (compared pre- and post-deploy configurations)

---

**Deployed by:** Antigravity Agent  
**Reviewed by:** Antigravity Agent (self-review)
