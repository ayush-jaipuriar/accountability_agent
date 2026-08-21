#!/usr/bin/env python3
"""
Production Verification Test Suite
==================================
Runs automated end-to-end sanity tests directly against live Cloud Run production endpoints.
"""

import sys
import time
import requests

PROD_URL = "https://accountability-agent-450357249483.us-central1.run.app"

def test_endpoint(method: str, path: str, expected_status: int = 200, json_payload: dict = None) -> dict:
    url = f"{PROD_URL}{path}"
    start = time.time()
    try:
        if method.upper() == "GET":
            resp = requests.get(url, timeout=10)
        elif method.upper() == "POST":
            resp = requests.post(url, json=json_payload or {}, timeout=15)
        else:
            raise ValueError(f"Unsupported method: {method}")
        latency_ms = (time.time() - start) * 1000
        
        passed = resp.status_code == expected_status
        status_icon = "✅" if passed else "❌"
        print(f"{status_icon} {method.upper()} {path} [{resp.status_code}] ({latency_ms:.1f}ms)")
        
        try:
            body = resp.json()
        except Exception:
            body = resp.text
            
        if not passed:
            print(f"   Expected: {expected_status}, Got: {resp.status_code}, Body: {body}")
            
        return {
            "path": path,
            "method": method,
            "status_code": resp.status_code,
            "latency_ms": latency_ms,
            "passed": passed,
            "body": body
        }
    except Exception as e:
        latency_ms = (time.time() - start) * 1000
        print(f"❌ {method.upper()} {path} [EXCEPTION] ({latency_ms:.1f}ms): {e}")
        return {
            "path": path,
            "method": method,
            "status_code": 0,
            "latency_ms": latency_ms,
            "passed": False,
            "error": str(e)
        }

def main():
    print("=" * 65)
    print(f"🚀 Running Live Production Automated Verification Suite")
    print(f"Target: {PROD_URL}")
    print("=" * 65)
    
    results = []
    
    # 1. Health & Root & Security
    results.append(test_endpoint("GET", "/health", 200))
    results.append(test_endpoint("GET", "/", 200))
    # Security test: verify /admin/metrics blocks unauthorized requests with 403
    results.append(test_endpoint("GET", "/admin/metrics", 403))
    
    # 2. Cron & Trigger Endpoints
    results.append(test_endpoint("POST", "/cron/morning_briefing", 200))
    results.append(test_endpoint("POST", "/cron/midday_nudge", 200))
    results.append(test_endpoint("POST", "/cron/churn_prevention", 200))
    results.append(test_endpoint("POST", "/cron/predictive_intervention", 200))
    results.append(test_endpoint("POST", "/cron/weekly_nps", 200))
    results.append(test_endpoint("POST", "/cron/reminder_tz_aware", 200))
    results.append(test_endpoint("POST", "/cron/reset_quick_checkins", 200))
    results.append(test_endpoint("POST", "/trigger/pattern-scan", 200))
    
    # 3. Webhook endpoint with empty/malformed payload (should reject safely, not crash)
    results.append(test_endpoint("POST", "/webhook/telegram", 200, json_payload={}))
    
    print("=" * 65)
    passed_count = sum(1 for r in results if r["passed"])
    total_count = len(results)
    avg_latency = sum(r["latency_ms"] for r in results) / total_count
    
    print(f"📊 Summary: {passed_count}/{total_count} Live Tests Passed")
    print(f"⚡ Average Latency: {avg_latency:.1f}ms")
    print("=" * 65)
    
    if passed_count == total_count:
        print("🎉 ALL PRODUCTION LIVE ENDPOINTS ARE FULLY OPERATIONAL AND HEALTHY!")
        return 0
    else:
        print(f"🚨 {total_count - passed_count} endpoints failed live check.")
        return 1

if __name__ == "__main__":
    sys.exit(main())
