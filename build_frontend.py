#!/usr/bin/env python3
"""Build the React frontend using vite."""
import subprocess
import os
import sys

frontend_dir = "/Users/apple/.cline/data/workspaces/chat/AlgoX/frontend"

# Run vite build
print("=== Running vite build ===")
result = subprocess.run(
    ["npx", "vite", "build"],
    cwd=frontend_dir,
    capture_output=True,
    text=True,
    timeout=120
)
if result.returncode != 0:
    print(f"BUILD FAILED (exit code {result.returncode})")
    print("STDOUT:", result.stdout[-2000:] if result.stdout else "(empty)")
    print("STDERR:", result.stderr[-2000:] if result.stderr else "(empty)")
    sys.exit(1)
else:
    print("BUILD SUCCESSFUL")
    print(result.stdout[-500:] if result.stdout else "(no stdout)")

# Check build output
build_dir = os.path.join(frontend_dir, "build")
if os.path.exists(build_dir):
    files = os.listdir(build_dir)
    print(f"=== Build output: {len(files)} files ===")
    for f in files:
        fpath = os.path.join(build_dir, f)
        if os.path.isdir(fpath):
            print(f"  {f}/: {len(os.listdir(fpath))} files")
        else:
            print(f"  {f} ({os.path.getsize(fpath)} bytes)")
else:
    print("ERROR: build/ directory not created")
    sys.exit(1)
