"""
Moduł szyfrowania haseł dla klienta pocztowego
Używa Fernet (symetryczne szyfrowanie) z kluczem przechowywanym w systemie
"""

import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2
from cryptography.hazmat.backends import default_backend


class PasswordEncryption:
    """Klasa do szyfrowania i deszyfrowania haseł"""
    
    def __init__(self):
        self.key_file = Path("mail_client/.key")
        self.salt_file = Path("mail_client/.salt")
        self._fernet = None
    
    def _get_or_create_salt(self) -> bytes:
        """Pobiera lub tworzy sól dla KDF"""
        if self.salt_file.exists():
            with open(self.salt_file, 'rb') as f:
                return f.read()
        else:
            # Generuj nową sól
            salt = os.urandom(16)
            self.salt_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.salt_file, 'wb') as f:
                f.write(salt)
            return salt
    
    def _get_or_create_key(self) -> bytes:
        """Pobiera lub tworzy klucz szyfrowania"""
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            # Generuj nowy klucz z hasła systemowego
            # W produkcji lepiej użyć system keyring, ale dla uproszczenia:
            salt = self._get_or_create_salt()
            
            # Użyj identyfikatora maszyny jako "hasła"
            import platform
            import hashlib
            machine_id = platform.node() + platform.machine()
            password = hashlib.sha256(machine_id.encode()).digest()
            
            # Derive key używając PBKDF2
            kdf = PBKDF2(
                algorithm=hashes.SHA256(),
                length=32,
                salt=salt,
                iterations=100000,
                backend=default_backend()
            )
            key = base64.urlsafe_b64encode(kdf.derive(password))
            
            # Zapisz klucz
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_file, 'wb') as f:
                f.write(key)
            
            return key
    
    def _get_fernet(self) -> Fernet:
        """Lazy initialization Fernet cipher"""
        if self._fernet is None:
            key = self._get_or_create_key()
            self._fernet = Fernet(key)
        return self._fernet
    
    def encrypt(self, plaintext: str) -> str:
        """Szyfruje tekst jawny i zwraca jako base64 string"""
        if not plaintext:
            return ""
        
        try:
            fernet = self._get_fernet()
            encrypted_bytes = fernet.encrypt(plaintext.encode('utf-8'))
            return base64.urlsafe_b64encode(encrypted_bytes).decode('utf-8')
        except Exception as e:
            print(f"Błąd szyfrowania: {e}")
            return plaintext  # Fallback - zwróć plain text
    
    def decrypt(self, encrypted: str) -> str:
        """Deszyfruje zaszyfrowany tekst"""
        if not encrypted:
            return ""
        
        try:
            fernet = self._get_fernet()
            encrypted_bytes = base64.urlsafe_b64decode(encrypted.encode('utf-8'))
            decrypted_bytes = fernet.decrypt(encrypted_bytes)
            return decrypted_bytes.decode('utf-8')
        except Exception as e:
            # Może to być niezaszyfrowane hasło (legacy)
            print(f"Błąd deszyfrowania (prawdopodobnie plain text): {e}")
            return encrypted  # Zwróć jako plain text
    
    def is_encrypted(self, text: str) -> bool:
        """Sprawdza czy tekst jest zaszyfrowany"""
        if not text:
            return False
        
        try:
            # Spróbuj zdekodować base64
            base64.urlsafe_b64decode(text.encode('utf-8'))
            # Jeśli się udało, prawdopodobnie zaszyfrowane
            return True
        except Exception:
            return False


# Singleton instance
_password_encryption = None

def get_password_encryption() -> PasswordEncryption:
    """Zwraca singleton instancję PasswordEncryption"""
    global _password_encryption
    if _password_encryption is None:
        _password_encryption = PasswordEncryption()
    return _password_encryption
