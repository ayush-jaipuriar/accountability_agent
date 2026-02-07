# 🎓 Cursor Rules Created - Security Learning

**Date:** February 7, 2026  
**Purpose:** Codify security learnings to prevent future incidents

---

## 📚 Rules Created

I've created **2 comprehensive global rules** in `.cursor/rules/` that will help prevent security issues going forward:

### 1. `security-secrets-prevention.mdc`
**Purpose:** Prevent secrets, API keys, and credentials from being committed

**What it covers:**
- ✅ Mandatory pre-commit security checks
- ✅ Patterns to never commit (.env*, credentials, keys)
- ✅ Safe alternatives (environment variables, placeholders)
- ✅ Required .gitignore patterns
- ✅ Detection patterns for bot tokens, API keys
- ✅ What to do if secrets are detected
- ✅ Reference to today's incident (Feb 7, 2026)

**Key features:**
- Always applies (`alwaysApply: true`)
- Specific detection patterns for common secrets
- Concrete examples (✅ good vs ❌ bad)
- Emergency procedures

### 2. `git-workflow-safety.mdc`
**Purpose:** Safe git practices to prevent accidents

**What it covers:**
- ✅ Safe pre-commit workflow (status, diff, review)
- ✅ Handling backup files created by tools
- ✅ Untracked files warning signs
- ✅ Safe adding strategies (avoid `git add .`)
- ✅ Staging area verification
- ✅ Documentation file best practices
- ✅ Recovery procedures
- ✅ Lesson from Feb 7, 2026 incident

**Key features:**
- Always applies (`alwaysApply: true`)
- Step-by-step checklists
- Command examples
- Real incident reference

---

## 🤖 How Cursor Will Use These Rules

**Every time you work with git, the AI will:**

1. **Before suggesting commits:**
   - Check for secrets in staged files
   - Warn about suspicious untracked files
   - Remind you to run `git diff --cached`

2. **When editing documentation:**
   - Flag hardcoded tokens/keys
   - Suggest environment variable placeholders
   - Ensure examples use fake values

3. **When creating files:**
   - Verify .gitignore covers new patterns
   - Warn about backup file creation
   - Suggest safe alternatives

4. **When you mention git operations:**
   - Remind you of pre-commit checklist
   - Suggest safe adding strategies
   - Warn about dangerous force operations

---

## 📋 What the AI Will Check

### Automatic Checks:

**1. Secret Detection:**
- Bot tokens: `\d{10}:[A-Za-z0-9_-]{35}`
- API keys: `AIza...`, `sk-...`, `AKIA...`
- Service accounts: `*-abc123def456.json`

**2. File Patterns:**
- `.env*` files in staging area
- Backup files (`.bak`, `.backup`, `.orig`)
- Credential files (`.key`, `.pem`, `.p12`)

**3. Documentation:**
- Hardcoded secrets in markdown
- Missing placeholders in examples
- Real tokens in curl commands

**4. Git Operations:**
- `git add .` usage (will suggest safer alternatives)
- Force operations on main branch
- Commits without review

---

## 🎯 Benefits

**1. Proactive Prevention:**
- AI will catch issues BEFORE you commit
- No more secrets slipping through
- Automatic pattern detection

**2. Education:**
- Learn safe practices through examples
- Understand why certain patterns are dangerous
- Reference real incidents

**3. Consistency:**
- Same checks every time
- No forgetting steps
- Standardized workflow

**4. Fast Response:**
- Immediate warnings when issues detected
- Recovery procedures readily available
- No need to search for solutions

---

## 🧪 Testing the Rules

You can verify the rules are working:

### 1. Check Rules Are Loaded:
- Open any file in Cursor
- The rules should automatically apply (they're global)
- AI should be aware of security patterns

### 2. Test Secret Detection:
Try asking: "Should I commit this file?" (while having sensitive data staged)
- AI should warn you and suggest checking for secrets

### 3. Test Git Workflow:
Ask: "How should I commit these changes?"
- AI should recommend `git status` and `git diff --cached` first

### 4. Test Documentation:
Add a curl command with a token in a .md file
- AI should suggest using `${VARIABLE}` instead

---

## 📖 Rule Structure

Both rules use this format:

```markdown
---
description: Brief description
alwaysApply: true
---

# Rule Title

## Section 1
Content with examples...

## Section 2
More guidance...
```

**Key features:**
- `alwaysApply: true` means they work in EVERY session
- Concrete examples (✅/❌ format)
- Checklists for easy reference
- Real incident learning

---

## 🔄 Updating Rules

As you learn more, you can update these rules:

```bash
# Edit rules directly:
code .cursor/rules/security-secrets-prevention.mdc
code .cursor/rules/git-workflow-safety.mdc

# Changes take effect immediately
# No restart needed
```

**When to update:**
- New security patterns discovered
- Additional best practices learned
- More detailed examples needed
- After any security incident

---

## 📚 Rule Locations

```
.cursor/rules/
├── security-secrets-prevention.mdc   # Secrets prevention
├── git-workflow-safety.mdc           # Git safety
├── local-testing-before-deploy.mdc   # Existing rule
└── progress-tracking.mdc             # Existing rule
```

All rules work together to provide comprehensive guidance!

---

## 🎓 Key Learnings Codified

### From Today's Incident:

**Problem:** `.env.bak` and bot token in docs nearly committed

**Root Causes:**
1. `sed -i.bak` created unignored backup
2. Documentation had hardcoded tokens
3. Didn't check `git status` carefully enough

**Solutions Now in Rules:**
1. ✅ Check for backup files before commit
2. ✅ Scan docs for hardcoded secrets
3. ✅ Always review `git diff --cached`
4. ✅ Enhanced .gitignore patterns
5. ✅ Use placeholders in documentation

**Impact:**
- AI will catch these patterns automatically
- You'll be warned before committing
- Safe practices become default

---

## 🚀 What Changed

### Before These Rules:
- Manual security checks (easy to forget)
- No systematic detection
- Reactive (find issues after commit)

### After These Rules:
- ✅ Automatic security awareness
- ✅ Proactive detection
- ✅ Consistent enforcement
- ✅ Educational examples
- ✅ Emergency procedures ready

---

## 💡 Usage Examples

**Example 1: Committing Code**
```
You: "I'm ready to commit"

AI: "Before committing, let me check:
     1. Run: git diff --cached
     2. Scan for secrets
     3. Verify .gitignore
     
     Have you run these checks?"
```

**Example 2: Documentation**
```
You: "Add this curl example: curl https://api.../bot123456:ABC..."

AI: "⚠️ That contains a real bot token. 
     Use placeholder instead:
     curl https://api.../bot${TELEGRAM_BOT_TOKEN}/..."
```

**Example 3: Backup Files**
```
You: "I see .env.bak in untracked files"

AI: "⚠️ That's a backup with secrets!
     1. Add *.bak to .gitignore
     2. Delete .env.bak
     3. Never commit backup files"
```

---

## ✅ Verification

To confirm rules are working:

1. **Check files exist:**
   ```bash
   ls -la .cursor/rules/
   # Should see:
   # - security-secrets-prevention.mdc
   # - git-workflow-safety.mdc
   ```

2. **Verify format:**
   ```bash
   head -5 .cursor/rules/security-secrets-prevention.mdc
   # Should show YAML frontmatter with alwaysApply: true
   ```

3. **Test in Cursor:**
   - Open any file
   - Ask about git/security
   - AI should reference these rules

---

## 🎉 Summary

**Created:** 2 comprehensive security rules  
**Type:** Global (always apply)  
**Purpose:** Prevent secrets exposure, ensure safe git workflow  
**Coverage:** Detection, prevention, recovery, best practices  
**Learning:** Based on real incident (Feb 7, 2026)  

**Impact:** The AI will now automatically help you maintain security best practices in every conversation! 🛡️

---

**Your Cursor workspace is now equipped with institutional knowledge about security! 🎓**
