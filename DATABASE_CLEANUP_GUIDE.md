# Database Cleanup Guide

**Date:** February 9, 2026  
**Purpose:** Clear all user data to start fresh after rate limit changes

---

## 🎯 What This Does

Clears all user data from Firestore:

- ✅ User profiles (`users` collection)
- ✅ Check-in records (`daily_checkins/*/checkins` subcollection)
- ✅ Interventions (`interventions/*/interventions` subcollection)
- ✅ Reminder status (`reminder_status/*/dates` subcollection)
- ✅ Emotional interactions (`emotional_interactions` collection)
- ✅ Pattern detection data (`patterns` collection)

---

## ⚠️ Important Warnings

**This is IRREVERSIBLE!**

- ❌ All user data will be permanently deleted
- ❌ No built-in recovery or undo
- ❌ Backups must be created manually (see below)

**When to use this:**

- ✅ After major schema changes
- ✅ When starting fresh with new features
- ✅ During development/testing
- ❌ NEVER on production with real users (unless you really mean it!)

---

## 📋 Two Options

### Option 1: Clear WITHOUT Backup (Fastest)

**Use when:** You don't need the old data at all.

```bash
cd /Users/ayushjaipuriar/Documents/GitHub/accountability_agent
python3 scripts/clear_database.py
```

**Steps:**
1. Shows current database statistics
2. Asks for confirmation: Type `DELETE ALL DATA`
3. Asks for double confirmation: Type `YES`
4. Deletes all data
5. Verifies cleanup

**Time:** ~30 seconds (depending on data volume)

---

### Option 2: Backup THEN Clear (Safer)

**Use when:** You might want to restore data later.

**Step 1: Create backup**
```bash
cd /Users/ayushjaipuriar/Documents/GitHub/accountability_agent
python3 scripts/backup_database.py
```

This creates: `backups/firestore_backup_YYYY-MM-DD_HH-MM-SS.json`

**Step 2: Clear database**
```bash
python3 scripts/clear_database.py
```

**Time:** ~1-2 minutes (backup + cleanup)

---

## 🔍 What the Scripts Do

### `clear_database.py`

**Theory:** Batch deletion for efficiency

The script uses Firestore batch operations (100 docs at a time) to efficiently delete large amounts of data. It follows this order:

1. **Delete subcollections under known parents first** (check-ins, interventions, reminders)
   - Why: Clears expected nested data before parent cleanup
   - How: Iterates through parent docs, deletes each subcollection

2. **Delete main collections** (users, emotional_interactions, patterns)
   - Why: Clean up primary data
   - How: Batch deletes 100 docs at a time

3. **Delete empty parent documents** (daily_checkins, interventions, reminder_status)
   - Why: Remove container documents
   - How: Final cleanup pass

4. **Collection-group orphan sweep** (`checkins`, `interventions`, `dates`)
   - Why: Firestore can retain orphaned subcollection docs if parents were deleted earlier
   - How: Deletes collection-group docs directly, regardless of parent presence

**Safety features:**
- Shows stats before deletion
- Requires explicit confirmation (twice!)
- Logs every deletion
- Verifies cleanup after completion

### `backup_database.py`

**Theory:** JSON export for portability

Creates a JSON file with all data:

```json
{
  "timestamp": "2026-02-09T19:30:00",
  "collections": {
    "users": [
      {"id": "123456", "data": {...}},
      ...
    ],
    "daily_checkins": {
      "123456": [
        {"id": "2026-02-09", "data": {...}},
        ...
      ]
    }
  }
}
```

**Why JSON?**
- Human-readable
- Easy to inspect
- Can be imported into other tools
- Version control friendly (can diff changes)

---

## 📊 Example Output

### Backup Output

```
📦 Firestore Database Backup Tool
==============================================================

📦 Creating database backup...
   Backing up users...
   Backing up emotional_interactions...
   Backing up patterns...
   Backing up check-ins...
   Backing up interventions...
   Backing up reminder_status...

✅ Backup complete!
📁 Saved to: backups/firestore_backup_2026-02-09_19-30-00.json
📊 Total documents backed up: 1,247
```

### Cleanup Output

```
🗑️  Firestore Database Cleanup Tool
==============================================================

📊 Current Database Statistics
==============================================================

📁 Main Collections:
   Users:                         3 documents
   Emotional Interactions:       45 documents
   Patterns:                     12 documents

📂 Subcollections:
   Check-ins:                   156 documents
   Interventions:                89 documents
   Reminder Status:              67 documents

📊 Total Documents:             372
==============================================================

⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ 
⚠️  WARNING: IRREVERSIBLE OPERATION
⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ ⚠️ 

This will PERMANENTLY DELETE all user data from Firestore:
  • All user profiles
  • All check-in records
  • All interventions
  • All emotional interactions
  • All pattern detection data
  • All reminder status

❌ This action CANNOT be undone!
❌ There is NO backup or recovery option!

🔴 Type 'DELETE ALL DATA' to confirm (or anything else to cancel): DELETE ALL DATA

⚠️  Last chance to cancel!
🔴 Type 'YES' to proceed with deletion: YES

==============================================================
🧹 Starting Database Cleanup
==============================================================

📂 Deleting subcollections...
   Deleted 156 documents from daily_checkins/checkins
✅ Deleted 156 documents from daily_checkins/checkins
   Deleted 89 documents from interventions/interventions
✅ Deleted 89 documents from interventions/interventions
   Deleted 67 documents from reminder_status/dates
✅ Deleted 67 documents from reminder_status/dates

📁 Deleting main collections...
   Deleted 3 documents from users...
✅ Deleted 3 documents from users
   Deleted 45 documents from emotional_interactions...
✅ Deleted 45 documents from emotional_interactions
   Deleted 12 documents from patterns...
✅ Deleted 12 documents from patterns

🗑️  Cleaning up empty parent documents...
   Deleted 3 documents from daily_checkins...
✅ Deleted 3 documents from daily_checkins
   Deleted 3 documents from interventions...
✅ Deleted 3 documents from interventions
   Deleted 3 documents from reminder_status...
✅ Deleted 3 documents from reminder_status

==============================================================
✅ Database Cleanup Complete!
==============================================================

📊 Total documents deleted: 381
⏱️  Time taken: 12.34 seconds

💡 The database is now empty and ready for fresh data.

📊 Verifying cleanup...

📊 Current Database Statistics
==============================================================

📁 Main Collections:
   Users:                         0 documents
   Emotional Interactions:        0 documents
   Patterns:                      0 documents

📂 Subcollections:
   Check-ins:                     0 documents
   Interventions:                 0 documents
   Reminder Status:               0 documents

📊 Total Documents:               0
==============================================================

✅ Verification passed: Database is completely empty.
```

---

## 🚨 Troubleshooting

### Error: "Failed to connect to Firestore"

**Cause:** Missing credentials

**Fix:**
```bash
# Check if credentials are set
echo $GOOGLE_APPLICATION_CREDENTIALS

# If empty, set it:
export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"

# Or check your .env file
cat .env | grep GOOGLE_APPLICATION_CREDENTIALS
```

### Error: "Permission denied"

**Cause:** Service account lacks permissions

**Fix:**
1. Go to GCP Console → IAM
2. Find your service account
3. Add role: `Cloud Datastore User` or `Cloud Datastore Owner`

### Script hangs or is very slow

**Cause:** Large amount of data

**Solution:** This is normal. The script processes 100 documents at a time. For 10,000 documents, expect ~2-3 minutes.

---

## 🔄 Restoring from Backup (If Needed)

If you backed up and need to restore:

**Option 1: Manual restore (for small datasets)**

1. Open the backup JSON file
2. Use Firebase Console to manually recreate documents
3. Copy/paste data from JSON

**Option 2: Create restore script (for large datasets)**

Create `scripts/restore_database.py`:

```python
import json
from google.cloud import firestore

def restore_backup(backup_file):
    db = firestore.Client()
    
    with open(backup_file) as f:
        backup = json.load(f)
    
    # Restore users
    for doc in backup['collections']['users']:
        db.collection('users').document(doc['id']).set(doc['data'])
    
    # Restore check-ins
    for user_id, checkins in backup['collections']['daily_checkins'].items():
        for checkin in checkins:
            db.collection('daily_checkins').document(user_id)\
              .collection('checkins').document(checkin['id']).set(checkin['data'])
    
    # ... restore other collections

restore_backup('backups/firestore_backup_2026-02-09_19-30-00.json')
```

---

## ✅ Post-Cleanup Checklist

After clearing the database:

- [ ] Verify database is empty (script does this automatically)
- [ ] Test bot with `/start` command (should create new user)
- [ ] Test check-in flow (should create new check-in)
- [ ] Verify rate limits are working (try multiple commands)
- [ ] Check Cloud Run logs for errors
- [ ] Monitor for 24 hours

---

## 📚 Why Clear the Database?

**After rate limit changes:**

While rate limits don't affect the database schema, clearing data is useful when:

1. **Testing new limits:** Start fresh to verify behavior
2. **Clean slate:** Remove test data from development
3. **Performance baseline:** Measure performance with empty DB
4. **User experience:** Ensure new users get the updated experience

**Not required but recommended** when making significant changes.

---

## 🎓 Learning: Firestore Batch Operations

**Why batch operations?**

```python
# ❌ Slow: One delete at a time
for doc in docs:
    doc.reference.delete()  # 1 network call per doc

# ✅ Fast: Batch delete
batch = db.batch()
for doc in docs:
    batch.delete(doc.reference)  # Queued
batch.commit()  # 1 network call for all
```

**Benefits:**
- 100x faster for large datasets
- Fewer network round trips
- Atomic operations (all succeed or all fail)
- Lower costs (fewer API calls)

**Limitations:**
- Max 500 operations per batch
- Our script uses 100 for safety margin

---

*Guide created: February 9, 2026*  
*Scripts: `clear_database.py`, `backup_database.py`*  
*Status: Ready to use*
