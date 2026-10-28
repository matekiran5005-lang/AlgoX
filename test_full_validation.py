#!/usr/bin/env python3
"""Comprehensive AlgoX validation script."""
import subprocess
import sys
import os
import time
import json

os.chdir("/Users/apple/.cline/data/workspaces/chat/AlgoX")

# Kill stale processes
subprocess.run(["pkill", "-f", "python3.*app.py"], capture_output=True, timeout=5)
time.sleep(2)

# Start Flask server
env = os.environ.copy()
env["PORT"] = "3000"
env["FLASK_DEBUG"] = "false"
server_proc = subprocess.Popen(
    [sys.executable, "app.py"],
    cwd="/Users/apple/.cline/data/workspaces/chat/AlgoX",
    env=env,
    stdout=subprocess.DEVNULL,
    stderr=subprocess.DEVNULL,
    start_new_session=True,
)
print(f"Server PID: {server_proc.pid}")

# Wait for server
import requests
BASE = "http://localhost:3000"
server_ready = False
for i in range(20):
    try:
        r = requests.get(f"{BASE}/api/health", timeout=3)
        if r.status_code == 200:
            print(f"✓ Server ready! {r.json()}")
            server_ready = True
            break
    except:
        pass
    time.sleep(1)

if not server_ready:
    print("✗ Server failed to start!")
    sys.exit(1)

passed = 0
failed = 0

def test_api(name, url, method="GET", data=None, expect_status=200):
    global passed, failed
    try:
        if method == "GET":
            r = requests.get(f"{BASE}{url}", timeout=15)
        elif method == "POST":
            r = requests.post(f"{BASE}{url}", json=data, timeout=15)
        if expect_status and r.status_code != expect_status:
            print(f"✗ {name:40s} → {r.status_code}")
            failed += 1
            return None
        print(f"✓ {name:40s} → {r.status_code}")
        try:
            j = r.json()
            if isinstance(j, dict):
                print(f"   keys: {list(j.keys())[:6]}")
            return r.json()
        except:
            return r.text
    except Exception as e:
        print(f"✗ {name:40s} → ERROR: {e}")
        failed += 1
        return None

# 1. Login (demo)
result = test_api("Login (demo mode)", "/api/login", "POST",
                  {"client_id": "demo_user_1", "access_token": "demo-token", "is_demo": True})
if result and result.get("user_id"):
    print(f"   user_id={result['user_id']}, capital={result.get('capital')}, demo={result.get('is_demo')}")
    passed += 1
else:
    failed += 1

# 2. Dashboard
result = test_api("Dashboard", "/api/dashboard/demo_user_1")
if result and not result.get("error"):
    print(f"   capital={result.get('capital')}, is_demo={result.get('is_demo')}, algo_active={result.get('algo_active')}")
    passed += 1
else:
    failed += 1

# 3. Demo switch
result = test_api("Demo Switch OFF", "/api/demo/toggle", "POST",
                  {"user_id": "demo_user_1", "is_demo": False})
if result and result.get("status") == "success":
    print(f"   {result.get('message')}")
    passed += 1
else:
    failed += 1
test_api("Demo Switch ON", "/api/demo/toggle", "POST",
         {"user_id": "demo_user_1", "is_demo": True})

# 4. ON/OFF button
result = test_api("Algo ON", "/api/strategy/toggle", "POST",
                  {"user_id": "demo_user_1", "active": True})
if result and result.get("algo_active") == True:
    print(f"   Algo switched ON")
    passed += 1
else:
    failed += 1
test_api("Algo OFF", "/api/strategy/toggle", "POST",
         {"user_id": "demo_user_1", "active": False})
test_api("Algo ON (back)", "/api/strategy/toggle", "POST",
         {"user_id": "demo_user_1", "active": True})

# 5. Trade List
result = test_api("Trade History", "/api/trade-history/demo_user_1")
if result and result.get("status") == "success":
    print(f"   {len(result.get('trades', []))} trades")
    passed += 1
else:
    failed += 1

# 6. Alerts
result = test_api("Alerts", "/api/alerts")
if result and result.get("status") == "success":
    print(f"   {len(result.get('alerts', []))} alerts")
    passed += 1
else:
    failed += 1

# 7. Users
result = test_api("Users List", "/api/users")
if result and result.get("status") == "success":
    print(f"   {len(result.get('users', []))} users")
    passed += 1
else:
    failed += 1

# 8. Strategy Config
result = test_api("Strategy Config GET", "/api/strategy/config")
if result and result.get("status") == "success":
    cfg = result.get("config", {})
    print(f"   name={cfg.get('name')}, lot_qty={cfg.get('lot_qty')}, open={cfg.get('market_open')}, close={cfg.get('market_close')}")
    passed += 1
else:
    failed += 1

# 9. Update config
result = test_api("Strategy Config POST", "/api/strategy/config", "POST",
                  {"lot_qty": 75, "budget": 15000})
if result and result.get("status") == "success":
    print(f"   Config updated")
    passed += 1
else:
    failed += 1

# 10. React app
print("\n--- Frontend ---")
try:
    r = requests.get(f"{BASE}/app", timeout=10)
    if r.status_code == 200 and ("root" in r.text or "React" in r.text):
        print("✓ React app served at /app")
        passed += 1
    else:
        print(f"✗ React app: status={r.status_code}")
        failed += 1
except Exception as e:
    print(f"✗ React app error: {e}")
    failed += 1

# Build files
build_dir = os.path.join(os.getcwd(), "frontend", "build")
if os.path.exists(build_dir):
    files = []
    for root, dirs, fnames in os.walk(build_dir):
        for f in fnames:
            files.append(os.path.relpath(os.path.join(root, f), build_dir))
    print(f"✓ Build dir: {len(files)} files")
    for f in sorted(files)[:5]:
        print(f"  - {f}")
    passed += 1
else:
    print("✗ Build dir not found")
    failed += 1

print(f"\n{'='*50}")
print(f"Results: {passed} passed, {failed} failed")
print(f"{'='*50}")

server_proc.terminate()
server_proc.wait()
print("✓ Server shut down")
