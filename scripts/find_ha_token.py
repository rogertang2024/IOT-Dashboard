import json

# Read the HA auth storage to find long-lived tokens
with open('config/.storage/auth', 'r') as f:
    auth = json.load(f)

data = auth.get('data', {})
users = data.get('users', [])
tokens = data.get('refresh_tokens', [])

print("Users:")
for u in users:
    print(f"  id={u.get('id')} name={u.get('name')} is_owner={u.get('is_owner')} is_active={u.get('is_active')}")

print("\nRefresh Tokens (long-lived access tokens):")
for t in tokens:
    if t.get('token_type') == 'long_lived_access_token':
        print(f"  id={t.get('id')} user_id={t.get('user_id')} client_name={t.get('client_name')} token={t.get('token', 'N/A')[:20]}...")
    
print("\nAll token types present:", list(set(t.get('token_type') for t in tokens)))
