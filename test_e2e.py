#!/usr/bin/env python3
"""End-to-end test for the AlgoX backend via HTTP requests."""
import requests
import json
import sys

BASE = "http://localhost:3000"

def test(name, url, method="GET", data=None):
    try:
        if method == "GET":
            r = requests.get(f"{BASE}{url}", timeout=10)
        else:
            r = requests.post(f"{BASE}{url}", json=data, timeout=10)
        print(f"{'✓' if r.status_code < 400 else '✗'} {name:30s} → {r.status_code}")
        try:
            print(f"  {json.dumps(r.json(), indent=2)[:200]}")
        except:
            print(f"  {r.text[:200]}")
    except Exception as e:
        print(f"✗ {name:30s} → ERROR: {e}")

print("=" * 60)
print("AlgoX End-to-End Tests")
print("=" * 60)

test("Health Check", "/api/health")
test("Demo Login", "/api/login", "POST", 
     {"client_id": "demo_user_1", "access_token": "demo-token", "is_demo": True})
test("Dashboard", "/api/dashboard/demo_user_1")
test("Toggle Algo ON", "/api/strategy/toggle", "POST",
     {"user_id": "demo_user_1", "active": True})
test("Strategy Config (GET)", "/api/strategy/config")
test("Users List", "/api/users", "GET")
test("Users Count", "/api/users/count")
test("Alerts", "/api/alerts")
test("Trade History", "/api/trade-history/demo_user_1")
test("Demo Mode Toggle", "/api/demo/toggle", "POST",
     {"user_id": "demo_user_1", "is_demo": True})
test("Option Chain CE", "/api/optionchain/nearest-ce/demo_user_1")

# Test React app serving
try:
    r = requests.get(f"{BASE}/app", timeout=10)
    print(f"{'✓' if r.status_code < 400 else '✗'} {'React App (/app)':30s} → {r.status_code}")
    if "root" in r.text or "React" in r.text:
        print("  ✓ React app HTML served correctly")
except Exception as e:
    print(f"✗ React App (/app)              → ERROR: {e}")

print()
print("=" * 60)
print("✅ All tests completed!")
print("=" * 60)
