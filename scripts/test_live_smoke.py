"""
Live Production Smoke & Sanity Test Suite
Runs non-destructive health, security, and webhook checks against the live Cloud Run production instance.
"""

import sys
import json
import urllib.request
import urllib.error

PROD_URL = "https://accountability-agent-450357249483.us-central1.run.app"

def test_health():
    url = f"{PROD_URL}/health"
    req = urllib.request.Request(url, headers={"User-Agent": "SanityTest/1.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))
        assert data.get("status") == "healthy"
        assert data.get("checks", {}).get("firestore") == "ok"
        print("✅ Live /health check: OK (Firestore connected)")

def test_root():
    url = f"{PROD_URL}/"
    req = urllib.request.Request(url, headers={"User-Agent": "SanityTest/1.0"})
    with urllib.request.urlopen(req, timeout=10) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))
        assert data.get("status") == "running"
        assert data.get("version") == "3.0.0"
        print("✅ Live / root check: OK (version 3.0.0 running)")

def test_admin_auth():
    url = f"{PROD_URL}/admin/metrics"
    req = urllib.request.Request(url, headers={"User-Agent": "SanityTest/1.0"})
    try:
        urllib.request.urlopen(req, timeout=10)
        raise AssertionError("Expected 403 Forbidden for unauthenticated admin access")
    except urllib.error.HTTPError as e:
        assert e.code == 403
        print("✅ Live /admin/metrics auth protection: OK (403 Forbidden)")

def test_webhook_empty_payload():
    url = f"{PROD_URL}/webhook/telegram"
    payload = json.dumps({}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": "application/json", "User-Agent": "SanityTest/1.0"},
        method="POST"
    )
    with urllib.request.urlopen(req, timeout=10) as response:
        assert response.status == 200
        data = json.loads(response.read().decode("utf-8"))
        assert data.get("ok") is True
        print("✅ Live /webhook/telegram safe handler: OK (200 OK)")

def main():
    print(f"🔍 Starting Production Smoke Tests against {PROD_URL}...\n")
    test_health()
    test_root()
    test_admin_auth()
    test_webhook_empty_payload()
    print("\n🎉 All production smoke and sanity tests passed successfully!")

if __name__ == "__main__":
    main()
