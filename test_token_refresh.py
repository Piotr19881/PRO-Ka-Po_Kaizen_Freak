"""
Test automatycznego odświeżania tokena
"""
import json
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent))

from src.Modules.Alarm_module.alarm_api_client import AlarmsAPIClient
from loguru import logger

# Usuń domyślny logger
logger.remove()
logger.add(sys.stderr, level="DEBUG", colorize=True)

def test_token_refresh():
    """Test automatycznego odświeżania tokena po wygaśnięciu"""
    
    # Wczytaj dane z tokens.json
    tokens_file = Path("data/tokens.json")
    with open(tokens_file, 'r') as f:
        token_data = json.load(f)
    
    access_token = token_data.get('access_token')
    refresh_token = token_data.get('refresh_token')
    user_id = token_data.get('user_data', {}).get('id')
    
    print(f"\n{'='*60}")
    print("TEST: Automatyczne odświeżanie tokena")
    print(f"{'='*60}\n")
    
    print(f"📋 User ID: {user_id}")
    print(f"📋 Original access_token (last 20 chars): ...{access_token[-20:]}")
    print(f"📋 Refresh token available: {'✓' if refresh_token else '✗'}\n")
    
    # Zmodyfikuj access token na nieprawidłowy (symulacja wygaśnięcia)
    invalid_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.INVALID_TOKEN.INVALID_SIGNATURE"
    
    print("🔧 Modifying access_token to invalid (simulating expiration)...")
    print(f"   Invalid token: {invalid_token[:50]}...\n")
    
    # Callback do zapisywania nowego tokena
    new_tokens = {}
    def save_new_token(new_access, new_refresh):
        print(f"\n✅ TOKEN REFRESH CALLBACK CALLED!")
        print(f"   New access_token (last 20): ...{new_access[-20:]}")
        print(f"   New refresh_token (last 20): ...{new_refresh[-20:]}")
        new_tokens['access'] = new_access
        new_tokens['refresh'] = new_refresh
        
        # Zapisz do pliku
        token_data['access_token'] = new_access
        token_data['refresh_token'] = new_refresh
        with open(tokens_file, 'w') as f:
            json.dump(token_data, f, indent=2)
        print(f"   ✓ Tokens saved to {tokens_file}\n")
    
    # Stwórz API Client z nieprawidłowym access_token ale prawidłowym refresh_token
    client = AlarmsAPIClient(
        base_url="http://127.0.0.1:8000",
        auth_token=invalid_token,  # Nieprawidłowy token!
        refresh_token=refresh_token,
        on_token_refreshed=save_new_token
    )
    
    print("🚀 Attempting to fetch items (should trigger 401 and auto-refresh)...\n")
    
    # Wykonaj request który zwróci 401 i automatycznie odświeży token
    response = client.fetch_all(user_id=user_id)
    
    print(f"\n📊 RESULTS:")
    print(f"{'='*60}")
    print(f"Response success: {response.success}")
    print(f"Response status: {response.status_code}")
    
    if response.success:
        print(f"✅ SUCCESS! Request completed after token refresh")
        items = response.data.get('items', []) if isinstance(response.data, dict) else []
        print(f"   Retrieved {len(items)} items from server")
    else:
        print(f"❌ FAILED: {response.error}")
    
    print(f"\n🔑 Token Refresh Check:")
    if new_tokens:
        print(f"   ✓ New access token received and saved")
        print(f"   ✓ New refresh token received and saved")
        print(f"   ✓ Auto-refresh WORKING! 🎉")
    else:
        print(f"   ✗ No new tokens - refresh may have failed")
    
    print(f"\n{'='*60}\n")
    
    return response.success and bool(new_tokens)


if __name__ == "__main__":
    try:
        success = test_token_refresh()
        sys.exit(0 if success else 1)
    except Exception as e:
        logger.exception(f"Test failed: {e}")
        sys.exit(1)
