"""
Moduł szyfrowania haseł dla klienta pocztowego
Używa Fernet (symetryczne szyfrowanie) z kluczem przechowywanym w systemie
"""

import os
import base64
from pathlib import Path
from cryptography.fernet import Fernet
import getpass
import base64
import os

# Try to use the system keyring for secure, portable storage of the encryption key.
try:
    import keyring
    _HAS_KEYRING = True
except Exception:
    keyring = None
    _HAS_KEYRING = False


class PasswordEncryption:
    """Klasa do szyfrowania i deszyfrowania haseł"""
    
    def __init__(self):
        self.key_file = Path("mail_client/.key")
        self._fernet = None
        # Service name used for keyring entry
        self._keyring_service = "PRO-Ka-Po-Mail-Encryption"
        self._keyring_user = getpass.getuser() or "default-user"
    
    def _get_or_create_key(self) -> bytes:
        """Pobiera lub tworzy klucz szyfrowania.

        Najpierw próbuje użyć systemowego `keyring` (polecane).
        Jeśli keyring nie jest dostępny, tworzy losowy klucz i zapisuje go
        do pliku `mail_client/.key` (bez powiązania ze sprzętem).
        """
        # 1) Keyring backend (najbezpieczniejsza i przenośna opcja)
        if _HAS_KEYRING and keyring is not None:
            try:
                existing = keyring.get_password(self._keyring_service, self._keyring_user)
                if existing:
                    return existing.encode('utf-8')
                # generate key and store
                new_key = Fernet.generate_key()
                # store as utf-8 str
                keyring.set_password(self._keyring_service, self._keyring_user, new_key.decode('utf-8'))
                return new_key
            except Exception:
                # Fall through to file fallback if keyring fails
                pass

        # 2) File fallback - create a random key and store it in mail_client/.key
        if self.key_file.exists():
            with open(self.key_file, 'rb') as f:
                return f.read()
        else:
            new_key = Fernet.generate_key()
            self.key_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.key_file, 'wb') as f:
                f.write(new_key)
            return new_key
    
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
