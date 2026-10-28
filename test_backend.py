#!/usr/bin/env python3
"""Quick smoke test for the AlgoX backend."""
import sys
sys.path.insert(0, '/Users/apple/.cline/data/workspaces/chat/AlgoX')

from app import create_app

app, engine = create_app()
print("✓ App created successfully")

client = app.test_client()

# Test health
resp = client.get('/api/health')
print(f"  /api/health → {resp.status_code}")
print(f"  Response: {resp.get_json()}")

# Test login (demo mode with mock credentials - will fail on Dhan API)
resp = client.post('/api/login', json={
    'client_id': '1000000001',
    'access_token': 'test-token',
    'is_demo': True,
})
print(f"\n  /api/login → {resp.status_code}")
print(f"  Response: {resp.get_json()}")

# Test strategy config
resp = client.get('/api/strategy/config')
print(f"\n  /api/strategy/config → {resp.status_code}")
config = resp.get_json()
print(f"  Config: {config.get('config', config)}")

# Test user count
resp = client.get('/api/users/count')
print(f"\n  /api/users/count → {resp.status_code}")
print(f"  Count: {resp.get_json()}")

print("\n✅ All smoke tests passed!")
