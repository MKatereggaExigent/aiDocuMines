import requests
import json

# Configuration
dashboard_url = "https://captain.aidocumines.com"
password = "Micho#25"
login_url = f"{dashboard_url}/api/v2/login"

try:
    print(f"🔐 Logging in to {dashboard_url}...")
    response = requests.post(login_url, json={"password": password})
    response.raise_for_status()
    
    print("✅ Login response:")
    print(json.dumps(response.json(), indent=4))

    # FIX: access the token from data
    token = response.json().get("data", {}).get("token")
    if token:
        print(f"\n🔑 Auth Token:\n{token}")
    else:
        print("⚠️ Token not found in response. Check structure.")
except requests.exceptions.RequestException as e:
    print(f"❌ Request failed: {e}")

