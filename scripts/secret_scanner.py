#!/usr/bin/env python3
"""
Secret Scanner & Leak Prevention
================================
Scans staged git changes or the entire repository for accidentally exposed
secrets, API keys, and sensitive environment/credential files.

Usage:
    python3 scripts/secret_scanner.py --staged   # Scan only staged git changes (for pre-commit)
    python3 scripts/secret_scanner.py --all      # Scan all tracked files in the repo
"""

import sys
import os
import re
import argparse
import subprocess
from pathlib import Path

# Patterns indicating hardcoded secrets
SECRET_PATTERNS = [
    (
        "Telegram Bot Token",
        re.compile(r"\b[0-9]{8,10}:[A-Za-z0-9_-]{35}\b"),
        re.compile(r"(?:1234567890:ABC|YOUR_TELEGRAM_BOT_TOKEN|example|placeholder|\.\.\.)", re.IGNORECASE),
    ),
    (
        "Google / Gemini API Key",
        re.compile(r"\bAIzaSy[A-Za-z0-9_-]{33}\b"),
        re.compile(r"(?:AIzaSyDummy|AIzaSyExample|YOUR_API_KEY|\.\.\.)", re.IGNORECASE),
    ),
    (
        "Private Key",
        re.compile(r"-----BEGIN (?:[A-Z0-9_-]+ )?PRIVATE KEY-----"),
        None,
    ),
    (
        "GCP Service Account Credential",
        re.compile(r'"type":\s*"service_account"'),
        re.compile(r"(?:example|placeholder)", re.IGNORECASE),
    ),
]

# Sensitive files that should never be staged
SENSITIVE_FILE_PATTERNS = [
    re.compile(r"(?:^|/)\.env(?:\..+)?$"),
    re.compile(r"\.(?:predeploy|postdeploy)\.yaml$"),
    re.compile(r"service_account(?:.*)?\.json$"),
]

ALLOWED_FILE_PATTERNS = [
    re.compile(r"\.env\.example$"),
]


def is_sensitive_file(filename: str) -> bool:
    for allowed in ALLOWED_FILE_PATTERNS:
        if allowed.search(filename):
            return False
    for pat in SENSITIVE_FILE_PATTERNS:
        if pat.search(filename):
            return True
    return False


def scan_text(text: str, filename: str) -> list:
    """Scan text for secrets and return list of violation descriptions."""
    violations = []
    lines = text.splitlines()
    for lineno, line in enumerate(lines, 1):
        for desc, pattern, ignore in SECRET_PATTERNS:
            match = pattern.search(line)
            if match:
                matched_str = match.group(0)
                if ignore and ignore.search(matched_str):
                    continue
                if ignore and ignore.search(line):
                    continue
                # Mask secret for display
                masked = matched_str[:8] + "..." + matched_str[-4:] if len(matched_str) > 12 else "***"
                violations.append(f"{filename}:{lineno} - {desc} found: {masked}")
    return violations


def scan_staged() -> int:
    """Scan staged changes via git diff --cached."""
    print("🔍 Scanning staged changes for secrets...")
    violations = []

    # 1. Check staged filenames
    res = subprocess.run(["git", "diff", "--cached", "--name-only"], capture_output=True, text=True)
    if res.returncode != 0:
        print("❌ Error: git diff --cached failed")
        return 1

    staged_files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
    for f in staged_files:
        if is_sensitive_file(f):
            violations.append(f"STAGED FILE ERROR: Attempting to commit sensitive file '{f}'")

    # 2. Check staged content additions
    diff_res = subprocess.run(["git", "diff", "--cached", "-U0"], capture_output=True, text=True)
    current_file = "unknown"
    for line in diff_res.stdout.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[6:].strip()
        elif line.startswith("+") and not line.startswith("+++"):
            added_content = line[1:]
            for desc, pattern, ignore in SECRET_PATTERNS:
                match = pattern.search(added_content)
                if match:
                    matched_str = match.group(0)
                    if ignore and ignore.search(matched_str):
                        continue
                    if ignore and ignore.search(added_content):
                        continue
                    masked = matched_str[:8] + "..." + matched_str[-4:] if len(matched_str) > 12 else "***"
                    violations.append(f"{current_file} - Staged addition contains {desc}: {masked}")

    if violations:
        print("\n❌ CRITICAL: Secrets or sensitive files detected in staged changes!")
        for v in violations:
            print(f"   🚨 {v}")
        print("\n👉 Please remove secrets or replace with environment variables before committing.")
        return 1

    print("✅ Staged secret scan passed! No secrets detected.")
    return 0


def scan_all() -> int:
    """Scan all tracked files in git."""
    print("🔍 Scanning all tracked files for secrets...")
    res = subprocess.run(["git", "ls-files"], capture_output=True, text=True)
    if res.returncode != 0:
        print("❌ Error: git ls-files failed")
        return 1

    files = [f.strip() for f in res.stdout.splitlines() if f.strip()]
    violations = []

    for f in files:
        if is_sensitive_file(f):
            violations.append(f"TRACKED FILE: Sensitive file tracked in repository: '{f}'")
            continue

        p = Path(f)
        if not p.is_file():
            continue

        # Skip binary files or large data
        try:
            content = p.read_text(encoding="utf-8", errors="ignore")
            v = scan_text(content, f)
            violations.extend(v)
        except Exception:
            continue

    if violations:
        print("\n❌ CRITICAL: Secrets found in repository files!")
        for v in violations:
            print(f"   🚨 {v}")
        return 1

    print("✅ Full repository secret scan passed! No secrets detected.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Secret scanner for git changes and repository")
    parser.add_argument("--staged", action="store_true", help="Scan only staged changes")
    parser.add_argument("--all", action="store_true", help="Scan all tracked files")
    args = parser.parse_args()

    if args.staged:
        return scan_staged()
    elif args.all:
        return scan_all()
    else:
        # Default to staged scan
        return scan_staged()


if __name__ == "__main__":
    sys.exit(main())
