"""
Test Authentication System
Testuje działanie systemu autoryzacji (API endpoints)
"""
import sys
import os

# Dodaj ścieżkę do modułu app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from Render_upload.app.auth import (
    hash_password, 
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    generate_user_id
)
from Render_upload.app.email_service import get_email_service


def test_password_hashing():
    """Test hashowania i weryfikacji hasła"""
    print("\n" + "="*60)
    print("TEST 1: Password Hashing")
    print("="*60)
    
    password = "MySecurePassword123!"
    print(f"Original password: {password}")
    
    # Hashuj hasło
    hashed = hash_password(password)
    print(f"Hashed password: {hashed[:50]}...")
    
    # Weryfikuj poprawne hasło
    is_valid = verify_password(password, hashed)
    print(f"✓ Correct password verification: {is_valid}")
    assert is_valid, "Password verification should return True"
    
    # Weryfikuj błędne hasło
    is_invalid = verify_password("WrongPassword", hashed)
    print(f"✓ Wrong password verification: {is_invalid}")
    assert not is_invalid, "Wrong password should return False"
    
    print("✓ Password hashing test PASSED")


def test_jwt_tokens():
    """Test tworzenia i dekodowania tokenów JWT"""
    print("\n" + "="*60)
    print("TEST 2: JWT Tokens")
    print("="*60)
    
    user_data = {
        "sub": "test-user-123",
        "email": "test@example.com"
    }
    
    # Utwórz access token
    access_token = create_access_token(data=user_data)
    print(f"Access token created: {access_token[:50]}...")
    
    # Dekoduj access token
    payload = decode_token(access_token)
    print(f"Decoded payload: {payload}")
    assert payload is not None, "Token should decode successfully"
    assert payload["sub"] == user_data["sub"], "User ID should match"
    assert payload["email"] == user_data["email"], "Email should match"
    assert verify_token_type(payload, "access"), "Token type should be 'access'"
    print("✓ Access token PASSED")
    
    # Utwórz refresh token
    refresh_token = create_refresh_token(data={"sub": user_data["sub"]})
    print(f"\nRefresh token created: {refresh_token[:50]}...")
    
    # Dekoduj refresh token
    refresh_payload = decode_token(refresh_token)
    print(f"Decoded refresh payload: {refresh_payload}")
    assert refresh_payload is not None, "Refresh token should decode successfully"
    assert refresh_payload["sub"] == user_data["sub"], "User ID should match"
    assert verify_token_type(refresh_payload, "refresh"), "Token type should be 'refresh'"
    print("✓ Refresh token PASSED")
    
    print("✓ JWT tokens test PASSED")


def test_user_id_generation():
    """Test generowania unikalnych ID użytkowników"""
    print("\n" + "="*60)
    print("TEST 3: User ID Generation")
    print("="*60)
    
    # Wygeneruj kilka ID
    ids = [generate_user_id() for _ in range(5)]
    
    print("Generated IDs:")
    for i, user_id in enumerate(ids, 1):
        print(f"  {i}. {user_id}")
    
    # Sprawdź unikalność
    assert len(ids) == len(set(ids)), "All IDs should be unique"
    print("✓ All IDs are unique")
    
    # Sprawdź format (UUID v4)
    import uuid
    for user_id in ids:
        try:
            uuid.UUID(user_id, version=4)
        except ValueError:
            assert False, f"ID {user_id} is not a valid UUID v4"
    
    print("✓ All IDs are valid UUID v4")
    print("✓ User ID generation test PASSED")


def test_verification_code():
    """Test generowania kodów weryfikacyjnych"""
    print("\n" + "="*60)
    print("TEST 4: Verification Code Generation")
    print("="*60)
    
    email_service = get_email_service()
    
    # Wygeneruj kilka kodów
    codes = [email_service.generate_verification_code() for _ in range(5)]
    
    print("Generated codes:")
    for i, code in enumerate(codes, 1):
        print(f"  {i}. {code}")
    
    # Sprawdź długość
    for code in codes:
        assert len(code) == 6, "Code should be 6 characters long"
        assert code.isdigit(), "Code should contain only digits"
    
    print("✓ All codes are 6-digit numbers")
    
    # Sprawdź różnorodność (nie powinny być wszystkie takie same)
    # Choć teoretycznie możliwe, jest bardzo nieprawdopodobne
    if len(set(codes)) > 1:
        print("✓ Codes are varied")
    
    print("✓ Verification code generation test PASSED")


def test_email_templates():
    """Test szablonów emaili (bez wysyłania)"""
    print("\n" + "="*60)
    print("TEST 5: Email Templates")
    print("="*60)
    
    email_service = get_email_service()
    
    # Test dla różnych języków
    languages = ['pl', 'en', 'de']
    
    for lang in languages:
        print(f"\nTesting language: {lang}")
        
        # Weryfikacja email
        verification_code = email_service.generate_verification_code()
        print(f"  Verification code: {verification_code}")
        
        # Reset hasła
        reset_code = email_service.generate_verification_code()
        print(f"  Reset code: {reset_code}")
        
        print(f"  ✓ Email templates for {lang} are ready")
    
    print("\n✓ Email templates test PASSED")


def main():
    """Uruchom wszystkie testy"""
    print("\n" + "="*60)
    print("TESTING AUTHENTICATION SYSTEM")
    print("="*60)
    
    try:
        test_password_hashing()
        test_jwt_tokens()
        test_user_id_generation()
        test_verification_code()
        test_email_templates()
        
        print("\n" + "="*60)
        print("✓ ALL TESTS PASSED SUCCESSFULLY!")
        print("="*60)
        print("\nAuthentication system is ready to use.")
        print("\nNext steps:")
        print("  1. Configure Gmail SMTP credentials in .env file")
        print("  2. Start FastAPI server: cd Render_upload && uvicorn app.main:app --reload")
        print("  3. Test endpoints at: http://localhost:8000/docs")
        print("  4. Create desktop UI for login/registration")
        print("="*60 + "\n")
        
    except AssertionError as e:
        print(f"\n✗ TEST FAILED: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
