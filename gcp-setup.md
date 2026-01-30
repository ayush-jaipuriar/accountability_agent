# GCP Project Configuration

## ✅ Project Setup Complete

**Last Updated:** January 30, 2026

### Project Details

- **Project ID:** `accountability-agent`
- **Project Name:** Accountability Agent
- **Region:** `asia-south1` (Mumbai)
- **Time Zone:** Asia/Kolkata (IST)

### Service Account

- **Email:** `constitution-agent-sa@accountability-agent.iam.gserviceaccount.com`
- **Key File:** `.credentials/accountability-agent-9256adc55379.json`
- **Roles Granted:**
  - Firestore User
  - Vertex AI User
  - Storage Object Admin
  - Cloud Run Invoker

### APIs Enabled ✅

- ✅ Cloud Run API
- ✅ Firestore API (Native mode)
- ✅ Vertex AI API
- ✅ Cloud Scheduler API
- ✅ Cloud Storage API
- ✅ Cloud Logging API
- ✅ Secret Manager API

### Firestore Database

- **Mode:** Native (NOT Datastore mode)
- **Location:** asia-south1
- **Status:** ✅ Active

### Next Steps

1. ✅ Create Telegram bot via @BotFather
2. ⬜ Store bot token in GCP Secret Manager
3. ⬜ Set up local Python environment
4. ⬜ Deploy to Cloud Run

### Useful Commands

```bash
# Set default project
gcloud config set project accountability-agent

# Authenticate with service account (for local development)
export GOOGLE_APPLICATION_CREDENTIALS="/Users/ayushjaipuriar/Documents/GitHub/accountability_agent/.credentials/accountability-agent-9256adc55379.json"

# Check current project
gcloud config get-value project

# View Firestore collections
gcloud firestore operations list

# View Cloud Run services
gcloud run services list --region asia-south1
```

### Cost Monitoring

- **Budget Alert:** Set up budget alert at $5/month
- **Current Spend:** Track daily in GCP Console → Billing
- **Expected Cost:** ~$0.55/month (within free tier limits)

### Security Notes

- ⚠️ **NEVER commit `.credentials/` folder to Git**
- ⚠️ Service account key file is in `.gitignore`
- ⚠️ For production, use Secret Manager or Workload Identity instead of JSON key files
- ⚠️ Rotate service account keys every 90 days

### Resources

- **GCP Console:** https://console.cloud.google.com/home/dashboard?project=accountability-agent
- **Firestore Console:** https://console.cloud.google.com/firestore/databases/-default-/data?project=accountability-agent
- **Cloud Run Console:** https://console.cloud.google.com/run?project=accountability-agent
- **Billing Console:** https://console.cloud.google.com/billing?project=accountability-agent
