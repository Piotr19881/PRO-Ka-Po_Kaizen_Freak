"""
Test Email Verification - Weryfikacja emaila
Wysyła kod weryfikacyjny do API i weryfikuje konto
"""
import requests
import json

# Konfiguracja
API_URL = "http://localhost:8000"

print("\n" + "="*60)
print("TEST WERYFIKACJI EMAILA")
print("="*60)

# Pobierz dane od użytkownika
email = input("\nPodaj email: ").strip()
if not email:
    email = "test@example.com"
    print(f"Używam domyślnego: {email}")

code = input("Podaj 6-cyfrowy kod z emaila: ").strip()

if len(code) != 6 or not code.isdigit():
    print("❌ BŁĄD: Kod musi być 6-cyfrowy!")
    exit(1)

verify_data = {
    "email": email,
    "code": code
}

print(f"\nWysyłam żądanie weryfikacji do: {API_URL}/api/v1/auth/verify-email")
print("Proszę czekać...")

try:
    # Wyślij żądanie weryfikacji
    response = requests.post(
        f"{API_URL}/api/v1/auth/verify-email",
        json=verify_data,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nStatus HTTP: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n" + "="*60)
        print("✅ WERYFIKACJA ZAKOŃCZONA SUKCESEM!")
        print("="*60)
        print(f"\n{result['message']}")
        print("\n🔐 Otrzymane tokeny:")
        print(f"\nAccess Token (ważny 15 min):")
        print(f"{result['access_token'][:50]}...")
        print(f"\nRefresh Token (ważny 7 dni):")
        print(f"{result['refresh_token'][:50]}...")
        print(f"\nToken Type: {result['token_type']}")
        print("\n" + "="*60)
        print("Możesz teraz zalogować się do aplikacji!")
        print("="*60)
        
        # Zapisz tokeny do pliku
        with open("tokens.json", "w") as f:
            json.dump({
                "access_token": result['access_token'],
                "refresh_token": result['refresh_token'],
                "token_type": result['token_type']
            }, f, indent=2)
        print("\n✅ Tokeny zapisane w pliku: tokens.json")
        
    else:
        print("\n" + "="*60)
        print("❌ BŁĄD WERYFIKACJI")
        print("="*60)
        error_detail = response.json().get('detail', 'Unknown error')
        print(f"Szczegóły: {error_detail}")
        print("\nMożliwe przyczyny:")
        print("  - Nieprawidłowy kod weryfikacyjny")
        print("  - Kod wygasł (ważny tylko 15 minut)")
        print("  - Email już zweryfikowany")
        
except requests.exceptions.ConnectionError:
    print("\n❌ BŁĄD: Nie można połączyć się z serwerem API")
    print("Upewnij się, że serwer FastAPI jest uruchomiony:")
    print("  cd Render_upload")
    print("  uvicorn app.main:app --reload")
    
except Exception as e:
    print(f"\n❌ BŁĄD: {e}")
    import traceback
    traceback.print_exc()

print()
