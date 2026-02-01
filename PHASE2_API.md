# Phase 2: API Specification

**Version:** 1.0  
**Date:** February 1, 2026  
**Base URL:** https://constitution-agent-450357249483.asia-south1.run.app

---

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Endpoints](#endpoints)
4. [Data Models](#data-models)
5. [Error Handling](#error-handling)
6. [Rate Limits](#rate-limits)
7. [Examples](#examples)

---

## Overview

Phase 2 adds new endpoints for pattern detection and maintains backward compatibility with Phase 1 endpoints.

### API Design Principles

1. **RESTful:** Standard HTTP methods (GET, POST)
2. **JSON:** All requests/responses in JSON format
3. **Stateless:** Each request contains all necessary information
4. **Idempotent:** Repeated requests produce same result
5. **Secure:** Authentication via headers and secrets

### Endpoint Summary

| Endpoint | Method | Phase | Purpose |
|----------|--------|-------|---------|
| `/health` | GET | 1 | Health check |
| `/` | GET | 1 | Service info |
| `/webhook/telegram` | POST | 1 | Telegram updates |
| `/trigger/pattern-scan` | POST | 2 | Manual pattern scan |

---

## Authentication

### Webhook Authentication

**Telegram Webhook:**
- Telegram signs all webhook requests
- Verify signature using bot token
- Implemented by `python-telegram-bot` library automatically

**Pattern Scan Endpoint:**
- Requires `X-CloudScheduler-JobName` header
- Only accepts requests from Cloud Scheduler
- Prevents unauthorized pattern scans

```http
X-CloudScheduler-JobName: pattern-scan-job
```

---

## Endpoints

### 1. Health Check

**Endpoint:** `GET /health`

**Purpose:** Verify service is running and healthy

**Authentication:** None (public)

**Request:**
```http
GET /health HTTP/1.1
Host: constitution-agent-450357249483.asia-south1.run.app
```

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "constitution-agent",
  "version": "1.0.0",
  "environment": "production",
  "checks": {
    "firestore": "ok",
    "vertex_ai": "ok"
  },
  "timestamp": "2026-02-01T10:30:00Z"
}
```

**Response (503 Service Unavailable):**
```json
{
  "status": "unhealthy",
  "checks": {
    "firestore": "error",
    "vertex_ai": "ok"
  },
  "error": "Firestore connection failed"
}
```

**Use Cases:**
- Cloud Run health probes
- Monitoring systems
- Pre-deployment checks

---

### 2. Service Info

**Endpoint:** `GET /`

**Purpose:** Get service information and available endpoints

**Authentication:** None (public)

**Request:**
```http
GET / HTTP/1.1
Host: constitution-agent-450357249483.asia-south1.run.app
```

**Response (200 OK):**
```json
{
  "service": "Constitution Accountability Agent",
  "version": "2.0.0",
  "phase": "Phase 2: LangGraph + Pattern Detection",
  "status": "running",
  "environment": "production",
  "features": {
    "ai_feedback": true,
    "pattern_detection": true,
    "scheduled_scanning": true,
    "emotional_processing": false
  },
  "endpoints": {
    "health": "/health",
    "webhook": "/webhook/telegram",
    "pattern_scan": "/trigger/pattern-scan",
    "docs": "disabled"
  },
  "support": {
    "telegram_bot": "@constitution_ayush_bot",
    "documentation": "https://github.com/..."
  }
}
```

**Use Cases:**
- API discovery
- Version checking
- Feature detection

---

### 3. Telegram Webhook

**Endpoint:** `POST /webhook/telegram`

**Purpose:** Receive updates from Telegram (messages, commands, button clicks)

**Authentication:** Telegram signature verification

**Request:**
```http
POST /webhook/telegram HTTP/1.1
Host: constitution-agent-450357249483.asia-south1.run.app
Content-Type: application/json

{
  "update_id": 123456789,
  "message": {
    "message_id": 1001,
    "from": {
      "id": 8448348678,
      "is_bot": false,
      "first_name": "Ayush",
      "username": "ayushjaipuriar"
    },
    "chat": {
      "id": 8448348678,
      "first_name": "Ayush",
      "username": "ayushjaipuriar",
      "type": "private"
    },
    "date": 1738401234,
    "text": "/checkin"
  }
}
```

**Response (200 OK):**
```json
{
  "ok": true,
  "update_id": 123456789,
  "processed_by": "supervisor_agent",
  "intent": "checkin",
  "processing_time_ms": 245
}
```

**Response (200 OK - Error Handled):**
```json
{
  "ok": false,
  "error": "User not found",
  "update_id": 123456789
}
```

**Flow:**
1. Telegram sends update → Webhook
2. Webhook → Supervisor Agent
3. Supervisor classifies intent → Routes to sub-agent
4. Agent processes → Sends response via Telegram
5. Webhook returns 200 OK (acknowledges receipt)

**Note:** Even on errors, returns 200 OK to prevent Telegram from retrying

**Use Cases:**
- All user interactions with bot
- Commands: `/start`, `/checkin`, `/status`, `/help`
- Free-text messages
- Button callbacks

---

### 4. Pattern Scan Trigger (NEW in Phase 2)

**Endpoint:** `POST /trigger/pattern-scan`

**Purpose:** Trigger pattern detection scan for all active users

**Authentication:** Cloud Scheduler header required

**Request:**
```http
POST /trigger/pattern-scan HTTP/1.1
Host: constitution-agent-450357249483.asia-south1.run.app
Content-Type: application/json
X-CloudScheduler-JobName: pattern-scan-job

{}
```

**Response (200 OK):**
```json
{
  "status": "scan_complete",
  "timestamp": "2026-02-01T12:00:00Z",
  "scan_duration_ms": 1234,
  "results": {
    "users_scanned": 5,
    "patterns_detected": 2,
    "interventions_sent": 2,
    "errors": 0
  },
  "patterns_by_type": {
    "sleep_degradation": 1,
    "training_abandonment": 0,
    "porn_relapse": 0,
    "compliance_decline": 1,
    "deep_work_collapse": 0
  },
  "intervention_details": [
    {
      "user_id": "8448348678",
      "pattern_type": "sleep_degradation",
      "severity": "high",
      "intervention_sent": true,
      "timestamp": "2026-02-01T12:00:05Z"
    },
    {
      "user_id": "1034585649",
      "pattern_type": "compliance_decline",
      "severity": "medium",
      "intervention_sent": true,
      "timestamp": "2026-02-01T12:00:08Z"
    }
  ]
}
```

**Response (403 Forbidden):**
```json
{
  "error": "Unauthorized",
  "message": "Missing or invalid X-CloudScheduler-JobName header"
}
```

**Response (500 Internal Server Error):**
```json
{
  "status": "scan_failed",
  "error": "Firestore connection timeout",
  "users_scanned": 3,
  "patterns_detected": 1,
  "interventions_sent": 1
}
```

**Query Parameters:** None

**Scheduled Execution:**
- Runs every 6 hours: 0:00, 6:00, 12:00, 18:00 IST
- Cloud Scheduler job: `pattern-scan-job`
- Location: `asia-south1`

**Use Cases:**
- Scheduled pattern detection
- Manual scan trigger (for testing/debugging)
- Batch processing of all users

**Security:**
- Only accepts requests with valid `X-CloudScheduler-JobName` header
- Prevents abuse/unauthorized scans
- Logs all scan requests

---

## Data Models

### Intent Classification Response

```typescript
interface IntentClassificationResult {
  intent: "checkin" | "emotional" | "query" | "command";
  confidence: number; // 0.0 - 1.0
  user_context: {
    user_id: string;
    current_streak: number;
    last_checkin_date: string;
    constitution_mode: string;
  };
}
```

**Example:**
```json
{
  "intent": "checkin",
  "confidence": 0.95,
  "user_context": {
    "user_id": "8448348678",
    "current_streak": 47,
    "last_checkin_date": "2026-01-31",
    "constitution_mode": "Optimization"
  }
}
```

---

### Pattern Detection Result

```typescript
interface Pattern {
  type: "sleep_degradation" | "training_abandonment" | "porn_relapse" | "compliance_decline" | "deep_work_collapse";
  severity: "low" | "medium" | "high" | "critical";
  detected_at: string; // ISO 8601 timestamp
  data: {
    // Pattern-specific data
    [key: string]: any;
  };
}
```

**Example (Sleep Degradation):**
```json
{
  "type": "sleep_degradation",
  "severity": "high",
  "detected_at": "2026-02-01T10:30:00Z",
  "data": {
    "avg_sleep_hours": 5.2,
    "consecutive_nights": 3,
    "threshold": 6.0,
    "dates": ["2026-01-30", "2026-01-31", "2026-02-01"]
  }
}
```

**Example (Training Abandonment):**
```json
{
  "type": "training_abandonment",
  "severity": "medium",
  "detected_at": "2026-02-01T10:30:00Z",
  "data": {
    "consecutive_days_missed": 3,
    "last_training_date": "2026-01-28",
    "dates": ["2026-01-29", "2026-01-30", "2026-01-31"]
  }
}
```

---

### Intervention Record

```typescript
interface Intervention {
  intervention_id: string;
  user_id: string;
  pattern: Pattern;
  message: string;
  sent_at: string; // ISO 8601 timestamp
  acknowledged: boolean | null;
  acknowledged_at: string | null;
}
```

**Example:**
```json
{
  "intervention_id": "intv_abc123def456",
  "user_id": "8448348678",
  "pattern": {
    "type": "sleep_degradation",
    "severity": "high",
    "detected_at": "2026-02-01T10:30:00Z",
    "data": {
      "avg_sleep_hours": 5.2,
      "consecutive_nights": 3
    }
  },
  "message": "🚨 PATTERN ALERT: Sleep Degradation Detected\n\nLast 3 nights: 5.5hrs, 5hrs, 5.2hrs...",
  "sent_at": "2026-02-01T10:30:15Z",
  "acknowledged": null,
  "acknowledged_at": null
}
```

---

### AI Feedback Response

```typescript
interface AIFeedbackResponse {
  feedback: string;
  context_used: {
    current_streak: number;
    recent_pattern: string;
    constitution_mode: string;
    relevant_principles: string[];
  };
  token_usage: {
    input_tokens: number;
    output_tokens: number;
    total_tokens: number;
    estimated_cost: number; // in USD
  };
  generation_time_ms: number;
}
```

**Example:**
```json
{
  "feedback": "Excellent work! 100% compliance today - you're locked in. 🔥\n\nYour 47-day streak is now in the top 1% territory. The consistency you're building here is exactly what Principle 3 (Systems Over Willpower) is about - you've made excellence automatic...",
  "context_used": {
    "current_streak": 47,
    "recent_pattern": "consistent_high_compliance",
    "constitution_mode": "Optimization",
    "relevant_principles": [
      "Principle 1: Physical Sovereignty",
      "Principle 3: Systems Over Willpower"
    ]
  },
  "token_usage": {
    "input_tokens": 520,
    "output_tokens": 145,
    "total_tokens": 665,
    "estimated_cost": 0.001455
  },
  "generation_time_ms": 1823
}
```

---

## Error Handling

### Standard Error Response

```typescript
interface ErrorResponse {
  error: string; // Error code
  message: string; // Human-readable message
  details?: any; // Additional context
  timestamp: string;
  request_id?: string;
}
```

### HTTP Status Codes

| Code | Meaning | When Used |
|------|---------|-----------|
| 200 | OK | Request successful |
| 400 | Bad Request | Invalid request data |
| 401 | Unauthorized | Missing authentication |
| 403 | Forbidden | Invalid authentication |
| 404 | Not Found | Endpoint doesn't exist |
| 429 | Too Many Requests | Rate limit exceeded |
| 500 | Internal Server Error | Unexpected server error |
| 503 | Service Unavailable | Service down/unhealthy |

### Error Examples

**400 Bad Request:**
```json
{
  "error": "validation_error",
  "message": "Invalid request body",
  "details": {
    "field": "user_id",
    "issue": "Required field missing"
  },
  "timestamp": "2026-02-01T10:30:00Z"
}
```

**403 Forbidden:**
```json
{
  "error": "unauthorized",
  "message": "Missing or invalid X-CloudScheduler-JobName header",
  "timestamp": "2026-02-01T10:30:00Z"
}
```

**500 Internal Server Error:**
```json
{
  "error": "internal_error",
  "message": "Failed to connect to Firestore",
  "details": {
    "service": "firestore",
    "error_code": "UNAVAILABLE"
  },
  "timestamp": "2026-02-01T10:30:00Z",
  "request_id": "req_abc123"
}
```

---

## Rate Limits

### Telegram Webhook

**Limits:**
- No explicit rate limit (handled by Telegram)
- Telegram sends updates at max ~30/second per bot
- Cloud Run auto-scales to handle load

**Best Practices:**
- Return 200 OK quickly (<5s)
- Process async where possible
- Don't retry on 200 OK

---

### Pattern Scan Endpoint

**Limits:**
- 4 requests/day (via Cloud Scheduler)
- Additional manual triggers allowed but monitored
- Max 1 concurrent scan

**Rate Limit Response (429):**
```json
{
  "error": "rate_limit_exceeded",
  "message": "Pattern scan already in progress",
  "retry_after_seconds": 300
}
```

---

### Gemini API

**Limits:**
- 60 requests/minute (Vertex AI default)
- Requests queued if limit exceeded
- Exponential backoff implemented

---

## Examples

### Example 1: Complete Check-In Flow

**Step 1: User sends `/checkin`**

```http
POST /webhook/telegram HTTP/1.1
Content-Type: application/json

{
  "update_id": 123,
  "message": {
    "from": {"id": 8448348678, "first_name": "Ayush"},
    "text": "/checkin"
  }
}
```

**Step 2: Bot asks Question 1**

Bot sends via Telegram API (not through our webhook):
```
📋 Daily Check-In (Question 1/4)

Did you complete your Tier 1 non-negotiables?

[Yes] [No]
```

**Step 3: User clicks [Yes]**

```http
POST /webhook/telegram HTTP/1.1
Content-Type: application/json

{
  "update_id": 124,
  "callback_query": {
    "from": {"id": 8448348678},
    "message": {...},
    "data": "tier1_yes"
  }
}
```

**Step 4: Bot asks Question 2**

```
How many hours did you sleep last night?

(Enter a number, e.g., 7.5)
```

**Step 5: User responds "7.5"**

```http
POST /webhook/telegram HTTP/1.1
Content-Type: application/json

{
  "update_id": 125,
  "message": {
    "from": {"id": 8448348678},
    "text": "7.5"
  }
}
```

**Step 6: Questions 3 & 4 completed...**

**Step 7: Bot generates AI feedback**

Internal call to Gemini (not via our API):
```python
feedback = await checkin_agent.generate_feedback(
    user_id="8448348678",
    checkin=checkin_data,
    context=user_context
)
```

**Step 8: Bot sends feedback**

```
✅ Check-in complete!

Excellent work! 100% compliance today - you're locked in. 🔥

Your 47-day streak is now in the top 1% territory. The consistency you're building here is exactly what Principle 3 (Systems Over Willpower) is about - you've made excellence automatic.

Sleep (7.5hrs), training, deep work (3hrs), zero porn, boundaries - all green. This is what Physical Sovereignty looks like in practice.

Tomorrow's focus: Protect that morning deep work slot. You're building momentum - don't let anything interrupt it.

Keep going. 💪
```

**Step 9: Pattern detection runs**

Checks for patterns, none found (all green).

**Response to Telegram:**
```json
{
  "ok": true,
  "update_id": 125,
  "processed_by": "checkin_agent",
  "intent": "checkin",
  "processing_time_ms": 3245
}
```

---

### Example 2: Pattern Detected & Intervention Sent

**Scenario:** User has <6 hours sleep for 3 nights

**Step 1: Cloud Scheduler triggers scan**

```http
POST /trigger/pattern-scan HTTP/1.1
X-CloudScheduler-JobName: pattern-scan-job
Content-Type: application/json

{}
```

**Step 2: Scan detects pattern**

Internal processing:
```python
# Get recent check-ins
checkins = firestore_service.get_recent_checkins(user_id, days=7)

# Detect patterns
patterns = pattern_detection_agent.detect_patterns(checkins)

# Found: sleep_degradation
pattern = {
  "type": "sleep_degradation",
  "severity": "high",
  "data": {
    "avg_sleep_hours": 5.2,
    "consecutive_nights": 3
  }
}
```

**Step 3: Generate intervention**

```python
intervention = await intervention_agent.generate_intervention(
    user_id=user_id,
    pattern=pattern
)
```

**Step 4: Send intervention via Telegram**

```
🚨 PATTERN ALERT: Sleep Degradation Detected

Last 3 nights: 5.5hrs, 5hrs, 5.2hrs (average: 5.2hrs)
Your constitution requires 7+ hours minimum.

This violates Principle 1: Physical Sovereignty.
"My body is my primary asset. No external pressure compromises my long-term health."

If this continues:
- Cognitive performance drops 20-30%
- Training recovery suffers
- You're sacrificing tomorrow for today
- Your 47-day streak is at risk

ACTION REQUIRED:
Tonight: In bed by 11 PM, no exceptions.
Set alarm for 6:30 AM (7.5 hours sleep).
Block calendar 10:30-11 PM as "Sleep Prep" - non-negotiable.

Your streak proves you can maintain consistency. Apply that same discipline to sleep.
```

**Step 5: Log intervention**

Stored in Firestore:
```
interventions/8448348678/interventions/intv_abc123
```

**Response:**
```json
{
  "status": "scan_complete",
  "users_scanned": 5,
  "patterns_detected": 1,
  "interventions_sent": 1,
  "intervention_details": [
    {
      "user_id": "8448348678",
      "pattern_type": "sleep_degradation",
      "severity": "high",
      "intervention_sent": true
    }
  ]
}
```

---

### Example 3: Manual Pattern Scan (Testing)

**Request:**
```bash
curl -X POST \
  https://constitution-agent-450357249483.asia-south1.run.app/trigger/pattern-scan \
  -H "X-CloudScheduler-JobName: pattern-scan-job" \
  -H "Content-Type: application/json" \
  -d '{}'
```

**Response:**
```json
{
  "status": "scan_complete",
  "timestamp": "2026-02-01T14:30:00Z",
  "scan_duration_ms": 2156,
  "results": {
    "users_scanned": 5,
    "patterns_detected": 3,
    "interventions_sent": 3,
    "errors": 0
  },
  "patterns_by_type": {
    "sleep_degradation": 1,
    "training_abandonment": 1,
    "porn_relapse": 0,
    "compliance_decline": 1,
    "deep_work_collapse": 0
  },
  "intervention_details": [
    {
      "user_id": "8448348678",
      "pattern_type": "sleep_degradation",
      "severity": "high",
      "intervention_sent": true,
      "timestamp": "2026-02-01T14:30:05Z"
    },
    {
      "user_id": "1034585649",
      "pattern_type": "training_abandonment",
      "severity": "medium",
      "intervention_sent": true,
      "timestamp": "2026-02-01T14:30:08Z"
    },
    {
      "user_id": "9876543210",
      "pattern_type": "compliance_decline",
      "severity": "medium",
      "intervention_sent": true,
      "timestamp": "2026-02-01T14:30:11Z"
    }
  ]
}
```

---

### Example 4: Health Check Integration

**Monitoring Script:**
```bash
#!/bin/bash

# Health check script for monitoring

URL="https://constitution-agent-450357249483.asia-south1.run.app/health"

response=$(curl -s -o /dev/null -w "%{http_code}" $URL)

if [ $response -eq 200 ]; then
    echo "✅ Service healthy"
    exit 0
elif [ $response -eq 503 ]; then
    echo "❌ Service unhealthy"
    # Send alert
    exit 1
else
    echo "⚠️ Unexpected response: $response"
    exit 2
fi
```

**Kubernetes/Cloud Run Probe:**
```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 10
  periodSeconds: 30
  timeoutSeconds: 5
  failureThreshold: 3
```

---

## Integration Guide

### Integrating with Phase 2 API

**Step 1: Update Webhook URL**

```bash
BOT_TOKEN="your_bot_token"
CLOUD_RUN_URL="https://constitution-agent-450357249483.asia-south1.run.app"

curl "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook?url=${CLOUD_RUN_URL}/webhook/telegram"
```

**Step 2: Set Up Cloud Scheduler**

```bash
gcloud scheduler jobs create http pattern-scan-job \
  --schedule="0 */6 * * *" \
  --uri="${CLOUD_RUN_URL}/trigger/pattern-scan" \
  --http-method=POST \
  --headers="X-CloudScheduler-JobName=pattern-scan-job" \
  --location=asia-south1
```

**Step 3: Monitor Health**

```bash
# Add to monitoring system
curl ${CLOUD_RUN_URL}/health
```

**Step 4: Test Pattern Scan**

```bash
# Manual trigger for testing
curl -X POST ${CLOUD_RUN_URL}/trigger/pattern-scan \
  -H "X-CloudScheduler-JobName: pattern-scan-job"
```

---

## Versioning

### API Version Strategy

**Current Version:** 2.0.0

**Version Format:** MAJOR.MINOR.PATCH

- **MAJOR:** Breaking changes (e.g., 1.x → 2.x)
- **MINOR:** New features, backward compatible (e.g., 2.0 → 2.1)
- **PATCH:** Bug fixes (e.g., 2.0.0 → 2.0.1)

**Backward Compatibility:**
- Phase 1 endpoints remain unchanged
- New Phase 2 endpoints are additive
- Deprecation notice: 6 months before removal

---

## Support

### Getting Help

**Issues:**
- GitHub Issues: [Link to repo]
- Email: support@...

**Documentation:**
- Main Spec: `PHASE2_SPEC.md`
- Architecture: `PHASE2_ARCHITECTURE.md`
- Prompts: `PHASE2_PROMPTS.md`

**Monitoring:**
- Cloud Logging: [GCP Console Link]
- Cloud Monitoring: [GCP Console Link]
- Error Reporting: [GCP Console Link]

---

**Document Version:** 1.0  
**Last Updated:** February 1, 2026  
**Status:** Production Ready
