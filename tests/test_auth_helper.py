"""
Helper do autentykacji w testach
Loguje się i pobiera JWT token
"""
import requests
import json
from pathlib import Path
from typing import Optional, Dict


def login_and_get_token(
    base_url: str,
    email: str,
    password: str
) -> Optional[Dict[str, str]]:
    """
    Loguje się do API i zwraca token + user_id
    
    Args:
        base_url: URL serwera API
        email: Email użytkownika
        password: Hasło
        
    Returns:
        Dict z access_token, refresh_token, user_id, email lub None jeśli błąd
    """
    try:
        # Endpoint logowania
        login_url = f"{base_url}/api/v1/auth/login"
        
        # Dane logowania
        login_data = {
            "email": email,
            "password": password
        }
        
        # Wyślij request
        print(f"Logging in as {email}...")
        response = requests.post(login_url, json=login_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            user_data = data.get('user', {})
            
            print(f"[OK] Login successful!")
            print(f"  User ID: {user_data.get('id')}")
            print(f"  Email: {user_data.get('email')}")
            print(f"  Name: {user_data.get('name')}")
            
            return {
                'access_token': data.get('access_token'),
                'refresh_token': data.get('refresh_token'),
                'user_id': user_data.get('id'),
                'email': user_data.get('email'),
                'name': user_data.get('name')
            }
        else:
            print(f"[BLAD] Login failed: {response.status_code}")
            print(f"  Response: {response.text}")
            return None
            
    except Exception as e:
        print(f"[BLAD] Error during login: {e}")
        return None


if __name__ == "__main__":
    # Test logowania
    BASE_URL = "http://127.0.0.1:8000"
    EMAIL = "piotr.prokop@promirbud.eu"
    PASSWORD = "testtest1"
    
    auth_data = login_and_get_token(BASE_URL, EMAIL, PASSWORD)
    
    if auth_data:
        print("\n=== Authentication Data ===")
        print(f"Access Token: {auth_data['access_token'][:50]}...")
        print(f"User ID: {auth_data['user_id']}")
        print(f"Email: {auth_data['email']}")
        
        # Zapisz token do tokens.json
        tokens_path = Path(__file__).parent.parent / "data" / "tokens.json"
        tokens_path.parent.mkdir(parents=True, exist_ok=True)
        
        tokens_data = {
            "access_token": auth_data['access_token'],
            "refresh_token": auth_data['refresh_token'],
            "user_data": {
                "id": auth_data['user_id'],
                "email": auth_data['email'],
                "name": auth_data.get('name', ''),
                "language": "pl",
                "timezone": "Europe/Warsaw",
                "theme": "light"
            }
        }
        
        with open(tokens_path, 'w', encoding='utf-8') as f:
            json.dump(tokens_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n✓ Token saved to: {tokens_path}")
    else:
        print("\n✗ Authentication failed")
