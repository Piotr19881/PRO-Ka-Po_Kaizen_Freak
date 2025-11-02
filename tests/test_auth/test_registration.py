"""
Test Registration - Rejestracja nowego użytkownika
Wysyła żądanie rejestracji do API i wyświetla wynik
"""
import requests
import json

# Konfiguracja
API_URL = "http://localhost:8000"

# Dane nowego użytkownika
new_user = {
    "email": "test@example.com",
    "password": "SecurePassword123!",
    "name": "Jan Kowalski",
    "language": "pl",
    "timezone": "Europe/Warsaw",
    "phone": "+48 123 456 789"
}

print("\n" + "="*60)
print("TEST REJESTRACJI NOWEGO UŻYTKOWNIKA")
print("="*60)

print(f"\nDane użytkownika:")
print(f"  Email: {new_user['email']}")
print(f"  Imię: {new_user['name']}")
print(f"  Język: {new_user['language']}")
print(f"  Strefa czasowa: {new_user['timezone']}")
print(f"  Telefon: {new_user['phone']}")

print(f"\nWysyłam żądanie rejestracji do: {API_URL}/api/v1/auth/register")
print("Proszę czekać...")

try:
    # Wyślij żądanie rejestracji
    response = requests.post(
        f"{API_URL}/api/v1/auth/register",
        json=new_user,
        headers={"Content-Type": "application/json"}
    )
    
    print(f"\nStatus HTTP: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2, ensure_ascii=False)}")
    
    if response.status_code == 201:
        result = response.json()
        print("\n" + "="*60)
        print("✅ REJESTRACJA ZAKOŃCZONA SUKCESEM!")
        print("="*60)
        print(f"\nUser ID: {result['user_id']}")
        print(f"Email: {result['email']}")
        print(f"\n{result['message']}")
        print("\n📧 Sprawdź swoją skrzynkę pocztową!")
        print(f"   Email został wysłany na adres: {new_user['email']}")
        print("   Powinieneś otrzymać 6-cyfrowy kod weryfikacyjny.")
        print("\nKod będzie ważny przez 15 minut.")
        print("\n" + "="*60)
        
        # Zapytaj o kod weryfikacyjny
        print("\nAby zweryfikować email, uruchom test_verify_email.py")
        
    else:
        print("\n" + "="*60)
        print("❌ BŁĄD REJESTRACJI")
        print("="*60)
        error_detail = response.json().get('detail', 'Unknown error')
        print(f"Szczegóły: {error_detail}")
        
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
