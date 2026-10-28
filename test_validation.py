#!/usr/bin/env python3
"""Run validation and write results to file."""
import subprocess, sys, os, time, json, requests

os.chdir("/Users/apple/.cline/data/workspaces/chat/AlgoX")
output = []

def log(msg):
    output.append(msg)
    print(msg)

# Kill stale server
try:
    subprocess.run(["pkill", "-f", "python3.*app.py"], capture_output=True, timeout=5)
    log("Killed stale processes")
except:
    log("No stale processes")
time.sleep(2)

# Start server
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
log(f"Server PID: {server_proc.pid}")

# Wait for server
BASE = "http://localhost:3000"
for i in range(20):
    try:
        r = requests.get(f"{BASE}/api/health", timeout=3)
        if r.status_code == 200:
            log(f"Server ready!")
            break
    except:
        pass
    time.sleep(1)
else:
    log("Server FAILED to start!")
    with open("/tmp/algox_results.txt", "w") as f:
        f.write("\n".join(output))
    sys.exit(1)

passed = 0
failed = 0

def test(name, url, method="GET", data=None):
    global passed, failed
    try:
        r = requests.post(f"{BASE}{url}", json=data, timeout=15) if method == "POST" else requests.get(f"{BASE}{url}", timeout=15)
        if r.status_code >= 400:
            log(f"FAIL {name}: {r.status_code}")
            failed += 1
        else:
            log(f"PASS {name}: {r.status_code}")
            passed += 1
        try:
            j = r.json()
            if isinstance(j, dict) and "user_id" in j:
                log(f"  -> user={j['user_id']}, capital={j.get('capital')}, demo={j.get('is_demo')}")
            elif isinstance(j, dict) and "config" in j:
                c = j["config"]
                log(f"  -> name={c.get('name')}, lot_qty={c.get('lot_qty')}, open={c.get('market_open')}, close={c.get('market_close')}")
            elif isinstance(j, dict) and "users" in j:
                log(f"  -> {len(j['users'])} users, algo_active={j['users'][0].get('algo_active') if j['users'] else 'N/A'}")
            elif isinstance(j, dict) and "alerts" in j:
                log(f"  -> {len(j['alerts'])} alerts")
            elif isinstance(j, dict) and "trades" in j:
                log(f"  -> {len(j['trades'])} trades")
            elif isinstance(j, dict) and "count" in j:
                log(f"  -> count={j.get('count')}")
        except: pass
    except Exception as e:
        log(f"FAIL {name}: {e}")
        failed += 1

# Run all tests
log("\n=== Testing Components ===")
test("1. Login Page (demo)", "/api/login", "POST", {"client_id": "demo_user_1", "access_token": "demo-token", "is_demo": True})
test("2. Dashboard", "/api/dashboard/demo_user_1")
test("3. Demo Switch OFF", "/api/demo/toggle", "POST", {"user_id": "demo_user_1", "is_demo": False})
test("3. Demo Switch ON", "/api/demo/toggle", "POST", {"user_id": "demo_user_1", "is_demo": True})
test("4. ON Button", "/api/strategy/toggle", "POST", {"user_id": "demo_user_1", "active": True})
test("4. OFF Button", "/api/strategy/toggle", "POST", {"user_id": "demo_user_1", "active": False})
test("4. ON Button (back)", "/api/strategy/toggle", "POST", {"user_id": "demo_user_1", "active": True})
test("5. Trade List", "/api/trade-history/demo_user_1")
test("6. Alerts", "/api/alerts")
test("7. Users", "/api/users")
test("8. Strategy Config GET", "/api/strategy/config")
test("9. Strategy Config POST", "/api/strategy/config", "POST", {"lot_qty": 75, "budget": 15000})

# Test React app
try:
    r = requests.get(f"{BASE}/app", timeout=10)
    if r.status_code == 200 and "root" in r.text:
        log(f"PASS React App (/app): {r.status_code}")
        passed += 1
    else:
        log(f"FAIL React App: {r.status_code}")
        failed += 1
except Exception as e:
    log(f"FAIL React App: {e}")
    failed += 1

# Check build files
build_dir = os.path.join(os.getcwd(), "frontend", "build")
if os.path.exists(build_dir):
    files = []
    for root, dirs, fnames in os.walk(build_dir):
        for f in fnames:
            files.append(os.path.relpath(os.path.join(root, f), build_dir))
    log(f"PASS Frontend build: {len(files)} files")
    for f in sorted(files)[:5]:
        log(f"  - {f}")
    passed += 1
else:
    log("FAIL Frontend build: not found")
    failed += 1

log(f"\n{'='*50}")
log(f"TOTAL: {passed} passed, {failed} failed")
log(f"{'*='*50}")

# Write to file
with open("/tmp/algox_results.txt", "w") as f:
    f.write("\n".join(output))

# Shutdown
server_proc.terminate()
server_proc.wait()
log("\nServer shut down cleanly")
