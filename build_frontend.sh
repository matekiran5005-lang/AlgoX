#!/bin/bash
cd /Users/apple/.cline/data/workspaces/chat/AlgoX/frontend
echo "=== Building React app ==="
npx vite build 2>&1
echo "=== Build exit code: $? ==="
echo "=== Check build output ==="
ls -la build/ 2>&1
ls -la build/assets/ 2>&1 | head -5
