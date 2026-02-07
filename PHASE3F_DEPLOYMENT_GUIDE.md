# Phase 3F Deployment Guide

**Status:** ✅ Ready to deploy  
**Prerequisites:** Docker verification passed (12/12 tests)  
**Date:** February 7, 2026

---

## Pre-Deployment Checklist

Before deploying, verify:

✅ **Local tests passed:** 152/152 Phase 3F tests  
✅ **Docker build successful:** `accountability-agent:phase3f` image created  
✅ **Docker verification passed:** 12/12 environment tests  
✅ **Dockerfile updated:** System dependencies for matplotlib/Pillow added  
✅ **requirements.txt updated:** Phase 3F libraries included  
✅ **No secrets in code:** `.env` files excluded, credentials via Secret Manager  

---

## Step 1: Build and Push Docker Image

### 1.1 Tag for Google Container Registry

```bash
docker tag accountability-agent:phase3f \
  gcr.io/accountability-agent/constitution-agent:phase3f
```

**Theory: Image Tagging**  
Docker tags are like Git tags - they're human-readable labels for specific image versions. The format `gcr.io/PROJECT/IMAGE:TAG` tells Docker:
- `gcr.io` - Google Container Registry (where to push)
- `accountability-agent` - GCP project ID
- `constitution-agent` - Image name
- `phase3f` - Version tag

### 1.2 Push to GCR

```bash
docker push gcr.io/accountability-agent/constitution-agent:phase3f
```

**Expected output:**
```
The push refers to repository [gcr.io/accountability-agent/constitution-agent]
phase3f: digest: sha256:abc123... size: 2847
```

**Time:** ~2-5 minutes depending on network speed (744MB upload)

### 1.3 Verify Image in GCR

```bash
gcloud container images list --repository=gcr.io/accountability-agent
gcloud container images describe gcr.io/accountability-agent/constitution-agent:phase3f
```

---

## Step 2: Deploy to Cloud Run

### 2.1 Deploy New Version

```bash
gcloud run deploy constitution-agent \
  --image gcr.io/accountability-agent/constitution-agent:phase3f \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --memory 1Gi \
  --cpu 1 \
  --timeout 300s \
  --max-instances 10 \
  --set-env-vars ENVIRONMENT=production
```

**Parameter Explanations:**

| Parameter | Value | Why |
|---|---|---|
| `--image` | phase3f tag | Specifies the new Docker image to deploy |
| `--region` | us-central1 | Low latency to India, cost-effective |
| `--memory` | 1Gi | matplotlib + graph generation needs RAM |
| `--cpu` | 1 | 1 vCPU sufficient for current load |
| `--timeout` | 300s | Graph generation + PDF can take time |
| `--max-instances` | 10 | Limit concurrent instances (cost control) |
| `--allow-unauthenticated` | - | Telegram webhook doesn't use auth |

**Expected output:**
```
Deploying container to Cloud Run service [constitution-agent]...
✓ Deploying... Done.
  ✓ Creating Revision...
  ✓ Routing traffic...
Done.
Service [constitution-agent] revision [constitution-agent-00042-abc] has been deployed and is serving 100 percent of traffic.
Service URL: https://constitution-agent-XXXXX-uc.a.run.app
```

**Time:** ~3-5 minutes

### 2.2 Verify Deployment

```bash
# Check service status
gcloud run services describe constitution-agent --region us-central1

# Test health endpoint
curl https://YOUR-SERVICE-URL/health

# Expected response:
# {"status": "healthy", "timestamp": "2026-02-07T..."}
```

### 2.3 Update Telegram Webhook

```bash
# Get the new Cloud Run URL
SERVICE_URL=$(gcloud run services describe constitution-agent \
  --region us-central1 \
  --format 'value(status.url)')

# Update Telegram webhook
curl -X POST "https://api.telegram.org/bot${BOT_TOKEN}/setWebhook" \
  -H "Content-Type: application/json" \
  -d "{\"url\": \"${SERVICE_URL}/webhook\"}"
```

**Expected response:**
```json
{"ok": true, "result": true, "description": "Webhook was set"}
```

---

## Step 3: Set Up Cloud Scheduler (Weekly Reports)

### 3.1 Create Scheduler Job

```bash
gcloud scheduler jobs create http weekly-report-trigger \
  --location us-central1 \
  --schedule "0 9 * * 0" \
  --time-zone "Asia/Kolkata" \
  --uri "https://YOUR-SERVICE-URL/trigger/weekly-report" \
  --http-method POST \
  --oidc-service-account-email YOUR-SERVICE-ACCOUNT@accountability-agent.iam.gserviceaccount.com \
  --oidc-audience https://YOUR-SERVICE-URL
```

**Schedule Breakdown:**
- `0 9 * * 0` - Cron format: minute=0, hour=9, day=*, month=*, weekday=0 (Sunday)
- **Time:** Every Sunday at 9:00 AM IST
- **Why Sunday?** Start of the week, users review last week's performance

**OIDC Authentication:**
Cloud Scheduler uses OIDC (OpenID Connect) to authenticate with Cloud Run. The service account must have the **Cloud Run Invoker** role.

### 3.2 Grant Service Account Permissions

```bash
# Get the service account email
SA_EMAIL=$(gcloud iam service-accounts list \
  --filter="displayName:Compute Engine default service account" \
  --format="value(email)")

# Grant Cloud Run Invoker role
gcloud run services add-iam-policy-binding constitution-agent \
  --region us-central1 \
  --member "serviceAccount:${SA_EMAIL}" \
  --role "roles/run.invoker"
```

### 3.3 Test Scheduler Job Manually

```bash
# Trigger the job manually (don't wait for Sunday)
gcloud scheduler jobs run weekly-report-trigger --location us-central1

# Check Cloud Run logs
gcloud run logs read constitution-agent \
  --region us-central1 \
  --limit 50 \
  | grep "Weekly report"
```

**Expected log output:**
```
📊 Weekly report triggered by: weekly-report-trigger
✅ Weekly reports complete: 1 sent, 0 failed
```

---

## Step 4: Manual Testing (Critical!)

Test each new command via Telegram:

### 4.1 Export Commands

```
/export csv
```
✅ **Verify:** CSV file downloads, opens in Excel/Sheets, data is complete

```
/export json
```
✅ **Verify:** JSON file downloads, valid JSON structure, all fields present

```
/export pdf
```
✅ **Verify:** PDF file downloads, formatted correctly, tables render

### 4.2 Report Command

```
/report
```
✅ **Verify:**
- Summary message with stats appears
- 4 graphs sent as photos (sleep, training, compliance, radar)
- AI insights are relevant and data-grounded
- Graphs render correctly on mobile

### 4.3 Social Commands

```
/leaderboard
```
✅ **Verify:** Rankings shown, your rank highlighted, top 3 have medals

```
/invite
```
✅ **Verify:** Referral link in format `t.me/botname?start=ref_USERID`, stats shown

```
/share
```
✅ **Verify:** Shareable stats image generates, QR code visible, stats accurate

### 4.4 Resume Command

```
1. Start /checkin
2. Answer first question
3. Wait (don't finish)
4. Send /resume
```
✅ **Verify:** Partial state restored, conversation continues from where you left off

### 4.5 Referral Flow (End-to-End)

```
1. User A sends /invite → gets link
2. User B clicks link → /start ref_USERA
3. Check Firestore: User B document has referred_by="USERA"
4. User A sends /invite again → stats show 1 total referral
```

---

## Step 5: Monitor First Automated Report

**Date:** Sunday, February 9, 2026  
**Time:** 9:00 AM IST (3:30 AM UTC)

### 5.1 Watch Cloud Run Logs

```bash
# Tail logs in real-time
gcloud run logs tail constitution-agent --region us-central1

# Or check after execution
gcloud run logs read constitution-agent \
  --region us-central1 \
  --limit 100 \
  --format "table(timestamp, textPayload)" \
  | grep -A 5 "Weekly report"
```

**Expected log sequence:**
```
📊 Weekly report triggered by: weekly-report-trigger
📊 Starting weekly reports for N users
✅ Weekly report sent to USER1 (Name): 4/4 graphs
✅ Weekly report sent to USER2 (Name): 4/4 graphs
...
✅ Weekly reports complete: N sent, 0 failed
```

### 5.2 Verify User Received Report

Check your Telegram:
- Summary message with week stats
- 4 graph images (sleep, training, compliance, radar)
- AI insights referencing your actual data

### 5.3 Check for Errors

```bash
# Check for any errors in the last hour
gcloud run logs read constitution-agent \
  --region us-central1 \
  --limit 200 \
  | grep -i "error\|failed\|exception"
```

**If errors found:**
- Check if specific graphs failed (fallback should still send report)
- Check if Telegram rate limits hit (>30 messages/second)
- Check if LLM API quota exceeded (fallback insights should work)

---

## Rollback Plan (If Issues Found)

### Quick Rollback to Phase 3E

```bash
# Deploy previous working version
gcloud run deploy constitution-agent \
  --image gcr.io/accountability-agent/constitution-agent:phase3e \
  --region us-central1
```

**When to rollback:**
- Critical errors in production logs
- Users unable to complete check-ins
- Webhook stops responding
- Memory/CPU limits exceeded

**When NOT to rollback:**
- Minor graph rendering issues (fallback works)
- Single user reports failing (others work)
- Cosmetic formatting issues (not blocking)

---

## Monitoring Metrics

### Key Metrics to Watch (First 48 Hours)

| Metric | Where | Good | Warning | Critical |
|---|---|---|---|---|
| **Error Rate** | Cloud Run logs | <1% | 1-5% | >5% |
| **Response Time** | Cloud Run metrics | <2s | 2-5s | >5s |
| **Memory Usage** | Cloud Run metrics | <800MB | 800-950MB | >950MB |
| **CPU Usage** | Cloud Run metrics | <60% | 60-80% | >80% |
| **Weekly Report Success** | Logs (Sunday) | 100% | 90-99% | <90% |

### Commands to Check Metrics

```bash
# Response time (p95)
gcloud run services describe constitution-agent \
  --region us-central1 \
  --format "value(status.latestReadyRevisionName)"

# Memory usage
gcloud monitoring time-series list \
  --filter 'metric.type="run.googleapis.com/container/memory/utilizations"' \
  --format "table(metric.labels.service_name, points[0].value.double_value)"

# Error count
gcloud run logs read constitution-agent \
  --region us-central1 \
  --limit 1000 \
  | grep -c "ERROR"
```

---

## Success Criteria

Phase 3F deployment is **successful** when:

✅ Cloud Run deployment completes without errors  
✅ Health endpoint responds  
✅ Telegram webhook receives updates  
✅ All 7 new commands work in manual testing  
✅ First automated Sunday report delivers successfully  
✅ No critical errors in logs for 24 hours  
✅ Memory usage stays under 950MB  
✅ Response times stay under 5 seconds  

---

## Deployment Timeline

| Step | Duration | Cumulative |
|---|---|---|
| 1. Push image to GCR | 3-5 min | 5 min |
| 2. Deploy to Cloud Run | 3-5 min | 10 min |
| 3. Update Telegram webhook | 1 min | 11 min |
| 4. Create Cloud Scheduler job | 2 min | 13 min |
| 5. Manual testing (7 commands) | 15 min | 28 min |
| 6. Monitor logs (initial) | 10 min | 38 min |

**Total:** ~40 minutes for complete deployment and initial verification

**First automated test:** Sunday, February 9, 2026 at 9:00 AM IST

---

## Post-Deployment Tasks

1. ✅ **Update documentation** - Mark Phase 3F as deployed in plan files
2. ✅ **Notify users** - Optional: Send announcement about new features
3. ✅ **Monitor for 48 hours** - Watch for any unexpected issues
4. ✅ **Collect feedback** - Note any UX improvements needed
5. ✅ **Plan Phase 3G** - Move to next phase after stability confirmed

---

## Commands Quick Reference

```bash
# Build
docker build -t accountability-agent:phase3f .

# Tag for GCR
docker tag accountability-agent:phase3f \
  gcr.io/accountability-agent/constitution-agent:phase3f

# Push
docker push gcr.io/accountability-agent/constitution-agent:phase3f

# Deploy
gcloud run deploy constitution-agent \
  --image gcr.io/accountability-agent/constitution-agent:phase3f \
  --region us-central1

# Create scheduler
gcloud scheduler jobs create http weekly-report-trigger \
  --schedule "0 9 * * 0" \
  --time-zone "Asia/Kolkata" \
  --uri "https://YOUR-URL/trigger/weekly-report" \
  --http-method POST \
  --oidc-service-account-email YOUR-SA@PROJECT.iam.gserviceaccount.com

# Test scheduler
gcloud scheduler jobs run weekly-report-trigger --location us-central1

# View logs
gcloud run logs read constitution-agent --region us-central1 --limit 50

# Rollback if needed
gcloud run deploy constitution-agent \
  --image gcr.io/accountability-agent/constitution-agent:phase3e \
  --region us-central1
```

---

## Ready to Deploy? 🚀

All verification complete. Proceed with Step 1 when ready.
