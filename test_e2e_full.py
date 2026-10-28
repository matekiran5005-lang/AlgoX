#!/usr/bin/env python3
"""Self-contained test: starts Flask server, runs E2E tests, writes results to file."""
import subprocess
import sys
import os
import time
import requests
import json

RESULTS_FILE = "/tmp/algox_test_results.txt"

# Kill any existing server
os.system("kill $(pgrep -f 'python3.*app.py') 2>/dev/null")
time.sleep(1)

# Start server in background
env = os.environ.copy()
env["PORT"] = "3000"
proc = subprocess.Popen(
    [sys.executable, "app.py"],
    cwd="/Users/apple/.cline/data/workspaces/chat/AlgoX",
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
)

# Wait for server to start
print("Waiting for server to start...", file=open(RESULTS_FILE, "w"))
for i in range(15):
    try:
        r = requests.get("http://localhost:3000/api/health", timeout=3)
        if r.status_code == 200:
            print(f"Server is up! (attempt {i+1})", file=open(RESULTS_FILE, "a"))
            break
    except:
        time.sleep(1)
else:
    print("Server failed to start!", file=open(RESULTS_FILE, "a"))
    sys.exit(1)

BASE = "http://localhost:3000"
results = []

def test(name, url, method="GET", data=None):
    try:
        if method == "GET":
            r = requests.get(f"{BASE}{url}", timeout=10)
        else:
            r = requests.post(f"{BASE}{url}", json=data, timeout=10)
        status = "✓" if r.status_code < 400 else "✗"
        results.append(f"{status} {name:35s} → {r.status_code}")
        try:
            body = json.dumps(r.json())[:300]
            results.append(f"   {body}")
        except:
            results.append(f"   {r.text[:300]}")
    except Exception as e:
        results.append(f"✗ {name:35s} → ERROR: {e}")

# Run tests
test("Health Check", "/api/health")
test("Demo Login", "/api/login", "POST",
     {"client_id": "demo_user_1", "access_token": "demo-token", "is_demo": True})
test("Dashboard", "/api/dashboard/demo_user_1")
test("Toggle Algo ON", "/api/strategy/toggle", "POST",
     {"user_id": "demo_user_1", "active": True})
test("Strategy Config (GET)", "/api/strategy/config")
test("Users List", "/api/users")
test("Users Count", "/api/users/count")
test("Alerts", "/api/alerts")
test("Trade History", "/api/trade-history/demo_user_1")
test("Demo Toggle", "/api/demo/toggle", "POST",
     {"user_id": "demo_user_1", "is_demo": True})

# Test React app
try:
    r = requests.get(f"{BASE}/app", timeout=10)
    status = "✓" if r.status_code < 400 else "✗"
    results.append(f"{status} React App (/app)                   → {r.status_code}")
    if "root" in r.text or "React" in r.text:
        results.append("   ✓ React app HTML served correctly")
except Exception as e:
    results.append(f"✗ React App (/app)                   → ERROR: {e}")

# Write results
output = ["=" * 70, "AlgoX End-to-End Tests", "=" * 70, ""]
output.extend(results)
output.append("")
output.append("=" * 70)
output.append("✅ All tests completed!")
output.append("=" * 70)

with open(RESULTS_FILE, "w") as f:
    f.write("\n".join(output))

print("\n".join(output))

# Shutdown server
proc.terminate()
proc.wait()
