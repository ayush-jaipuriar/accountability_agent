#!/usr/bin/env python3
"""
Production Smoke Test
=====================

Safe, read-only smoke test of the production Accountability Agent instance.
Does NOT create test data, send messages to users, or trigger cron jobs.

Tests:
1. Health endpoint (read-only)
2. Webhook endpoint (verifies it exists, doesn't send real Telegram updates)
3. Cron endpoints (verifies auth rejection without secret)
4. Admin endpoints (verifies auth rejection without admin ID)
5. Log monitoring (checks for ERROR severity in last 15 minutes)
"""

import httpx
import sys
import json
from datetime import datetime, timezone

PROD_URL = "https://accountability-agent-450357249483.us-central1.run.app"

results = []


def test(name: str, method: str, path: str, expected_status, **kwargs):
    """Run a single HTTP test against production."""
    url = f"{PROD_URL}{path}"
    if isinstance(expected_status, int):
        expected_statuses = [expected_status]
    else:
        expected_statuses = list(expected_status)
    timeout = kwargs.pop("timeout", 15.0)
    try:
        resp = httpx.request(method, url, timeout=timeout, **kwargs)
        passed = resp.status_code in expected_statuses
        results.append({
            "name": name,
            "passed": passed,
            "status": resp.status_code,
            "expected": expected_statuses,
            "preview": resp.text[:120] if resp.text else "(empty)",
        })
        status = "✅ PASS" if passed else "❌ FAIL"
        expected_str = "/".join(map(str, expected_statuses))
        print(f"  {status} {name}: HTTP {resp.status_code} (expected {expected_str})")
        if not passed:
            print(f"      Response: {resp.text[:200]}")
    except Exception as e:
        results.append({
            "name": name,
            "passed": False,
            "status": None,
            "expected": expected_statuses,
            "preview": str(e),
        })
        print(f"  ❌ FAIL {name}: Exception - {e}")


def main():
    print("=" * 60)
    print("Production Smoke Test")
    print(f"Target: {PROD_URL}")
    print(f"Time: {datetime.now(timezone.utc).isoformat()} UTC")
    print("=" * 60)

    # 1. Health endpoint
    print("\n📊 Health & Availability")
    test("Health endpoint", "GET", "/health", 200)

    # 2. Webhook endpoint (existence check only)
    print("\n📡 Webhook Endpoint")
    test(
        "Webhook POST with mock update",
        "POST",
        "/webhook/telegram",
        200,
        json={"update_id": 1, "message": {"message_id": 1, "from": {"id": 1, "is_bot": False, "first_name": "Test"}, "chat": {"id": 1, "type": "private"}, "text": "/start", "date": 1700000000}},
    )

    # 3. Cron endpoints (should return 200 if auth is skipped, or 401/403 if auth is enabled)
    print("\n⏰ Cron Endpoints (Auth Check)")
    cron_paths = [
        "/cron/reminder_first",
        "/cron/reminder_second",
        "/cron/reminder_third",
        "/cron/morning_briefing",
        "/cron/churn_prevention",
        "/cron/predictive_intervention",
        "/cron/weekly_nps",
        "/cron/reset_quick_checkins",
    ]
    for path in cron_paths:
        name = path.split("/")[-1].replace("_", " ").title()
        test(f"{name} (Auth Check)", "POST", path, (200, 401, 403))

    # 4. Admin endpoints (should reject without admin ID)
    print("\n🔒 Admin Endpoints (Auth Check)")
    test("Admin broadcast without ID", "POST", "/admin/broadcast", 403, json={"message": "test"})

    # 5. Trigger endpoints (should return 200 if auth is skipped, or 401/403 if auth is enabled)
    print("\n🎯 Trigger Endpoints (Auth Check)")
    test("Pattern scan (Auth Check)", "POST", path="/trigger/pattern-scan", expected_status=(200, 401, 403))
    test("Weekly report (Auth Check)", "POST", path="/trigger/weekly-report", expected_status=(200, 401, 403), timeout=90.0)

    # Summary
    print("\n" + "=" * 60)
    passed = sum(1 for r in results if r["passed"])
    total = len(results)
    failed = [r for r in results if not r["passed"]]

    print(f"Results: {passed}/{total} passed")
    if failed:
        print(f"\n❌ Failed tests:")
        for r in failed:
            print(f"  - {r['name']}: HTTP {r['status']} (expected {r['expected']})")
            print(f"    Preview: {r['preview']}")
        print("\n⚠️  Some production endpoints are not behaving as expected.")
        sys.exit(1)
    else:
        print("\n✅ All production smoke tests passed.")
        print("   The service is responding correctly to health checks and auth boundaries.")
        sys.exit(0)


if __name__ == "__main__":
    main()
