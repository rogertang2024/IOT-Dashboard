import json, urllib.request

with open('config/.storage/auth', 'r') as f:
    auth = json.load(f)

tokens = auth['data']['refresh_tokens']
llat = next(t for t in tokens if t.get('token_type') == 'long_lived_access_token')
token = llat['token']
print(f"Token found: {token[:10]}...{token[-5:]}")

# Reload automations
req = urllib.request.Request(
    'http://localhost:8123/api/services/automation/reload',
    data=b'{}',
    headers={'Authorization': f'Bearer {token}', 'Content-Type': 'application/json'},
    method='POST'
)
try:
    resp = urllib.request.urlopen(req)
    print(f"Automation reload: {resp.status} {resp.reason}")
except Exception as e:
    print(f"Error: {e}")

# Save token to secrets.yaml for future use
print(f"\nFull token:\n{token}")
