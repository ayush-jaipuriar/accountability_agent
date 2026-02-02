# Enable Vertex AI for Phase 2

## 🎯 Goal
Enable access to Google's Gemini models via Vertex AI API so the Phase 2 implementation can run.

---

## ⚡ Quick Fix (Recommended)

Run these commands to enable the APIs:

```bash
# 1. Enable Vertex AI API
gcloud services enable aiplatform.googleapis.com --project=accountability-agent

# 2. Enable Generative Language API (for Gemini)
gcloud services enable generativelanguage.googleapis.com --project=accountability-agent

# 3. Grant service account permissions
gcloud projects add-iam-policy-binding accountability-agent \
  --member="serviceAccount:bot-service-account@accountability-agent.iam.gserviceaccount.com" \
  --role="roles/aiplatform.user"

# 4. Test if it works
cd /Users/ayushjaipuriar/Documents/GitHub/accountability_agent
source venv/bin/activate
python3 test_llm_basic.py
```

**If this works:** ✅ You're done! Proceed with Phase 2 implementation.

**If this doesn't work:** Try the manual steps below.

---

## 🔧 Manual Setup (Google Cloud Console)

### Step 1: Enable Vertex AI API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Select project: **accountability-agent**
3. Navigate to: **APIs & Services** → **Library**
4. Search for: "Vertex AI API"
5. Click **ENABLE**

### Step 2: Enable Generative Language API

1. Still in **APIs & Services** → **Library**
2. Search for: "Generative Language API"
3. Click **ENABLE**

### Step 3: Accept Gemini Terms of Service

1. Navigate to: **Vertex AI** → **Generative AI** → **Language**
2. You may see a prompt to **"Enable Generative AI"** or **"Accept Terms"**
3. Click **Enable** or **Accept**
4. Wait for activation (may take a few minutes)

### Step 4: Grant Service Account Permissions

1. Navigate to: **IAM & Admin** → **IAM**
2. Find your service account: `bot-service-account@accountability-agent.iam.gserviceaccount.com`
3. Click **Edit** (pencil icon)
4. Click **ADD ANOTHER ROLE**
5. Add: **Vertex AI User** (`roles/aiplatform.user`)
6. Click **SAVE**

### Step 5: Test

```bash
cd /Users/ayushjaipuriar/Documents/GitHub/accountability_agent
source venv/bin/activate
python3 test_llm_basic.py
```

**Expected output if working:**
```
✅ LLM Service initialized
🔄 Testing text generation...
✅ LLM Response: 'Hello'
✅ LLM Service is working correctly!

🔄 Testing intent classification...
✅ Intent classification is working well!
Accuracy: 100% (4/4 correct)
```

---

## 🌍 Regional Availability

If you still get 404 errors, Gemini may not be available in `asia-south1` (Mumbai).

### Try US Central 1:

**Edit `.env`:**
```bash
VERTEX_AI_LOCATION=us-central1
```

**Test again:**
```bash
python3 test_llm_basic.py
```

### Available Regions for Gemini:
- `us-central1` (Iowa, USA) - **Recommended, most reliable**
- `us-east1` (South Carolina, USA)
- `europe-west1` (Belgium)
- `europe-west4` (Netherlands)
- `asia-northeast1` (Tokyo, Japan)
- `asia-south1` (Mumbai, India) - **May have limited availability**

**Note:** Using `us-central1` adds ~200-300ms latency but is most reliable.

---

## 🔍 Troubleshooting

### Error: "API not enabled"
```
ERROR: (gcloud.services.enable) FAILED_PRECONDITION: 
Service aiplatform.googleapis.com can't be enabled for consumer ...
```

**Solution:** Project may not have billing enabled.
1. Go to [Billing](https://console.cloud.google.com/billing)
2. Link a billing account to `accountability-agent`

### Error: "Permission denied"
```
ERROR: User [your-email@gmail.com] does not have permission to access project 
[accountability-agent] (or it may not exist)
```

**Solution:** You're not the project owner.
1. Ask project owner to grant you **Owner** or **Editor** role
2. Or ask them to enable the APIs for you

### Error: "Quota exceeded"
```
ERROR: Quota exceeded for quota metric 'aiplatform.googleapis.com/generate_content_requests_per_minute'
```

**Solution:** You hit the free tier limit.
1. Wait a few minutes for quota to reset
2. Or request quota increase in GCP Console

### Error: "Model not found" (still after enabling)
```
404 Publisher Model ... was not found
```

**Possible causes:**
1. **API not fully activated yet** - Wait 5-10 minutes, try again
2. **Wrong region** - Try `us-central1` instead of `asia-south1`
3. **Model name typo** - Verify model name is exactly `gemini-1.5-flash`

**Debug steps:**
```bash
# Check if API is enabled
gcloud services list --enabled --project=accountability-agent | grep aiplatform

# Should show:
# aiplatform.googleapis.com           Vertex AI API

# Check service account permissions
gcloud projects get-iam-policy accountability-agent \
  --flatten="bindings[].members" \
  --filter="bindings.members:serviceAccount:bot-service-account@accountability-agent.iam.gserviceaccount.com" \
  --format="table(bindings.role)"

# Should include:
# roles/aiplatform.user
```

---

## 🚀 Alternative: Use Direct Gemini API (Simpler)

If Vertex AI is too complex, we can use the direct Gemini API instead:

### Pros:
- ✅ Simpler setup (just need API key)
- ✅ No GCP project configuration needed
- ✅ Faster to get working

### Cons:
- ❌ Less enterprise features
- ❌ Different pricing structure
- ❌ Requires code changes

### How to Switch:

1. **Get Gemini API Key:**
   - Go to [Google AI Studio](https://makersuite.google.com/app/apikey)
   - Create API key
   - Add to `.env`: `GEMINI_API_KEY=your_key_here`

2. **Update LLM Service:**
   - Modify `src/services/llm_service.py` to use `google.generativeai` instead of `vertexai`

**Should we do this?** Only if Vertex AI continues to be problematic.

---

## ✅ Success Criteria

You'll know Vertex AI is working when:

1. ✅ `python3 test_llm_basic.py` shows:
   ```
   ✅ LLM Service initialized
   ✅ LLM Response: 'Hello'
   ✅ Intent classification is working well!
   ```

2. ✅ No 404 errors in the output

3. ✅ Intent classification accuracy >80%

4. ✅ Token usage and costs are logged

---

## 📞 Still Stuck?

If none of the above works:

1. **Check GCP Console Logs:**
   - Navigation: **Logging** → **Logs Explorer**
   - Filter: `resource.type="aiplatform.googleapis.com"`
   - Look for error messages

2. **Verify Credentials:**
   ```bash
   # Check if credentials file exists
   ls -la .credentials/accountability-agent-9256adc55379.json
   
   # Test authentication
   gcloud auth application-default print-access-token
   ```

3. **Try Different Model:**
   - Update `.env`: `GEMINI_MODEL=gemini-pro`
   - Test again

4. **Contact Support:**
   - [Google Cloud Support](https://cloud.google.com/support)
   - Or use [Stack Overflow](https://stackoverflow.com/questions/tagged/google-vertex-ai)

---

## 🎯 Next Steps

Once Vertex AI is working:

1. ✅ Run full test suite: `pytest tests/test_intent_classification.py -v -s`
2. ✅ Verify >80% accuracy
3. ✅ Monitor costs (should be <$0.001 per test run)
4. 🚀 Proceed to Day 3-4: Build CheckIn Agent with AI feedback!

Good luck! 💪
