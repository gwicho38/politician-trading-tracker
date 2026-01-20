import os
import requests

# Get Supabase URL and key
url = os.getenv('VITE_SUPABASE_URL')
anon_key = os.getenv('VITE_SUPABASE_ANON_KEY')

if not url or not anon_key:
    print("❌ Missing environment variables")
    exit(1)

print("🔍 Testing trading signals endpoint...")

# Test the simple test endpoint first
test_url = f"{url}/functions/v1/trading-signals/test"
headers = {
    'Authorization': f'Bearer {anon_key}',
    'Content-Type': 'application/json'
}

try:
    response = requests.get(test_url, headers=headers)
    print(f"Test endpoint status: {response.status_code}")
    if response.status_code == 200:
        print("✅ Function is responding")
        print(f"Response: {response.json()}")
    else:
        print(f"❌ Test failed: {response.text}")
except Exception as e:
    print(f"❌ Connection error: {e}")

# Test the actual get-signals endpoint
print("\n🔍 Testing get-signals endpoint...")
signals_url = f"{url}/functions/v1/trading-signals/get-signals?limit=10"

try:
    response = requests.get(signals_url, headers=headers)
    print(f"Get-signals status: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print("✅ Success!")
        print(f"Signals returned: {len(data.get('signals', []))}")
    else:
        print(f"❌ Error: {response.text}")
except Exception as e:
    print(f"❌ Connection error: {e}")
