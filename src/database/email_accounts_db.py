"""
Email Accounts Database Manager
================================

Zarządzanie bazą danych kont e-mail dla modułu CallCryptor.
Obsługuje bezpieczne przechowywanie credentials (szyfrowanie haseł).

Features:
- CRUD operations dla kont e-mail
- Szyfrowanie haseł (keyring)
- Synchronizacja z serwerem (offline-first)
- Multi-user support

Database Location: ~/.pro_ka_po/email_accounts.db
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional
from loguru import logger
import keyring
from cryptography.fernet import Fernet
import json


class EmailAccountsDatabase:
    """Manager bazy danych kont e-mail"""
    
    # Keyring service name
    KEYRING_SERVICE = "PRO-Ka-Po_EmailAccounts"
    
    def __init__(self, db_path: str):
        """
        Args:
            db_path: Ścieżka do pliku bazy danych
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Initialize database
        self._init_database()
        logger.info(f"[EmailAccountsDB] Initialized at: {self.db_path}")
    
    def _get_connection(self):
        """Pobierz połączenie z bazą danych"""
        return sqlite3.connect(str(self.db_path))
    
    def _init_database(self):
        """Utwórz tabele jeśli nie istnieją"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela kont e-mail
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS email_accounts (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    
                    -- Dane konta
                    account_name TEXT NOT NULL,
                    email_address TEXT NOT NULL,
                    
                    -- Konfiguracja serwera
                    server_type TEXT NOT NULL,
                    server_address TEXT NOT NULL,
                    server_port INTEGER NOT NULL,
                    
                    -- Credentials (username stored here, password in keyring)
                    username TEXT NOT NULL,
                    password_key TEXT,  -- Key do keyring
                    
                    -- Opcje
                    use_ssl BOOLEAN DEFAULT 1,
                    use_tls BOOLEAN DEFAULT 0,
                    fetch_limit INTEGER DEFAULT 50,  -- Liczba pobieranych wiadomości
                    
                    -- Status
                    is_active BOOLEAN DEFAULT 1,
                    last_connection_at TEXT,
                    connection_error TEXT,
                    
                    -- Timestamps
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    
                    -- Synchronizacja
                    is_synced BOOLEAN DEFAULT 0,
                    synced_at TEXT,
                    version INTEGER DEFAULT 1
                )
            """)
            
            # Indeksy
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_accounts_user 
                ON email_accounts(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_email_accounts_active 
                ON email_accounts(is_active)
            """)
            
            # Migracja: dodaj fetch_limit jeśli nie istnieje
            cursor.execute("PRAGMA table_info(email_accounts)")
            columns = [col[1] for col in cursor.fetchall()]
            if 'fetch_limit' not in columns:
                cursor.execute("""
                    ALTER TABLE email_accounts 
                    ADD COLUMN fetch_limit INTEGER DEFAULT 50
                """)
                logger.info("[EmailAccountsDB] Added fetch_limit column")
            
            conn.commit()
            logger.debug("[EmailAccountsDB] Database schema initialized")
    
    # =========================================================================
    # CRUD OPERATIONS
    # =========================================================================
    
    def add_account(self, account_data: Dict, user_id: str) -> str:
        """
        Dodaj nowe konto e-mail.
        
        Args:
            account_data: {
                'account_name': str,
                'email_address': str,
                'server_type': 'IMAP' | 'POP3',
                'server_address': str,
                'server_port': int,
                'username': str,
                'password': str,
                'use_ssl': bool,
                'use_tls': bool (optional)
            }
            user_id: ID użytkownika
            
        Returns:
            ID utworzonego konta
        """
        account_id = str(uuid.uuid4())
        now = datetime.utcnow().isoformat()
        
        # Zapisz hasło w keyring
        password = account_data['password']
        password_key = f"{user_id}_{account_id}"
        self._save_password(password_key, password)
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO email_accounts (
                    id, user_id, account_name, email_address,
                    server_type, server_address, server_port,
                    username, password_key,
                    use_ssl, use_tls, fetch_limit,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                account_id, user_id,
                account_data['account_name'],
                account_data['email_address'],
                account_data['server_type'],
                account_data['server_address'],
                account_data['server_port'],
                account_data['username'],
                password_key,
                account_data.get('use_ssl', True),
                account_data.get('use_tls', False),
                account_data.get('fetch_limit', 50),
                now, now
            ))
            conn.commit()
        
        logger.info(f"[EmailAccountsDB] Added account: {account_data['account_name']}")
        return account_id
    
    def update_account(self, account_id: str, account_data: Dict) -> bool:
        """
        Zaktualizuj istniejące konto.
        
        Args:
            account_id: ID konta
            account_data: Dane do aktualizacji (częściowe)
            
        Returns:
            True jeśli sukces
        """
        now = datetime.utcnow().isoformat()
        
        # Build update query dynamically
        update_fields = []
        values = []
        
        # Mapowanie pól
        field_mapping = {
            'account_name': 'account_name',
            'email_address': 'email_address',
            'server_type': 'server_type',
            'server_address': 'server_address',
            'server_port': 'server_port',
            'username': 'username',
            'use_ssl': 'use_ssl',
            'use_tls': 'use_tls',
            'fetch_limit': 'fetch_limit'
        }
        
        for key, db_field in field_mapping.items():
            if key in account_data:
                update_fields.append(f"{db_field} = ?")
                values.append(account_data[key])
        
        # Update password if provided
        if 'password' in account_data:
            account = self.get_account(account_id)
            if account:
                self._save_password(account['password_key'], account_data['password'])
        
        if not update_fields:
            return True  # Nothing to update
        
        # Always update timestamp and version
        update_fields.append("updated_at = ?")
        update_fields.append("version = version + 1")
        update_fields.append("is_synced = 0")
        values.append(now)
        values.append(account_id)
        
        query = f"""
            UPDATE email_accounts 
            SET {', '.join(update_fields)}
            WHERE id = ?
        """
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, values)
            conn.commit()
            success = cursor.rowcount > 0
        
        if success:
            logger.info(f"[EmailAccountsDB] Updated account: {account_id}")
        
        return success
    
    def delete_account(self, account_id: str) -> bool:
        """
        Usuń konto e-mail.
        
        Args:
            account_id: ID konta
            
        Returns:
            True jeśli sukces
        """
        # Get password_key before deleting
        account = self.get_account(account_id)
        if not account:
            return False
        
        # Delete from keyring
        try:
            self._delete_password(account['password_key'])
        except Exception as e:
            logger.warning(f"[EmailAccountsDB] Could not delete password from keyring: {e}")
        
        # Delete from database
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM email_accounts WHERE id = ?", (account_id,))
            conn.commit()
            success = cursor.rowcount > 0
        
        if success:
            logger.info(f"[EmailAccountsDB] Deleted account: {account_id}")
        
        return success
    
    def get_account(self, account_id: str) -> Optional[Dict]:
        """
        Pobierz konto po ID.
        
        Returns:
            Dict z danymi konta (z hasłem!) lub None
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM email_accounts WHERE id = ?
            """, (account_id,))
            row = cursor.fetchone()
        
        if not row:
            return None
        
        account = self._row_to_dict(cursor, row)
        
        # Pobierz hasło z keyring
        password = self._get_password(account['password_key'])
        account['password'] = password
        
        return account
    
    def get_all_accounts(self, user_id: str, active_only: bool = False) -> List[Dict]:
        """
        Pobierz wszystkie konta użytkownika.
        
        Args:
            user_id: ID użytkownika
            active_only: Tylko aktywne konta
            
        Returns:
            Lista kont (bez haseł!)
        """
        query = "SELECT * FROM email_accounts WHERE user_id = ?"
        params = [user_id]
        
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY account_name"
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
        
        accounts = []
        for row in rows:
            account = self._row_to_dict(cursor, row)
            # NIE dodawaj hasła do listy wszystkich kont (bezpieczeństwo)
            account['password'] = '***'
            accounts.append(account)
        
        return accounts
    
    def get_account_config(self, account_id: str) -> Optional[Dict]:
        """
        Pobierz konfigurację konta gotową do użycia w EmailConnector.
        
        Returns: {
            'account_id': str,
            'server_type': str,
            'server_address': str,
            'server_port': int,
            'username': str,
            'password': str,
            'use_ssl': bool,
            'use_tls': bool
        }
        """
        account = self.get_account(account_id)
        if not account:
            return None
        
        return {
            'account_id': account['id'],
            'server_type': account['server_type'],
            'server_address': account['server_address'],
            'server_port': account['server_port'],
            'username': account['username'],
            'password': account['password'],
            'use_ssl': bool(account['use_ssl']),
            'use_tls': bool(account['use_tls'])
        }
    
    # =========================================================================
    # CONNECTION STATUS
    # =========================================================================
    
    def update_connection_status(
        self,
        account_id: str,
        success: bool,
        error: Optional[str] = None
    ) -> bool:
        """
        Zaktualizuj status połączenia konta.
        
        Args:
            account_id: ID konta
            success: Czy połączenie udane
            error: Komunikat błędu (jeśli failed)
            
        Returns:
            True jeśli sukces
        """
        now = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE email_accounts
                SET last_connection_at = ?,
                    connection_error = ?
                WHERE id = ?
            """, (
                now if success else None,
                error if not success else None,
                account_id
            ))
            conn.commit()
            return cursor.rowcount > 0
    
    def set_active(self, account_id: str, is_active: bool) -> bool:
        """Ustaw status aktywności konta"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE email_accounts
                SET is_active = ?, updated_at = ?, is_synced = 0
                WHERE id = ?
            """, (is_active, datetime.utcnow().isoformat(), account_id))
            conn.commit()
            return cursor.rowcount > 0
    
    # =========================================================================
    # PASSWORD MANAGEMENT (KEYRING)
    # =========================================================================
    
    def _save_password(self, password_key: str, password: str):
        """Zapisz hasło w keyring"""
        try:
            keyring.set_password(self.KEYRING_SERVICE, password_key, password)
            logger.debug(f"[EmailAccountsDB] Password saved to keyring: {password_key}")
        except Exception as e:
            logger.error(f"[EmailAccountsDB] Failed to save password to keyring: {e}")
            raise
    
    def _get_password(self, password_key: str) -> Optional[str]:
        """Pobierz hasło z keyring"""
        try:
            password = keyring.get_password(self.KEYRING_SERVICE, password_key)
            if password is None:
                logger.warning(f"[EmailAccountsDB] Password not found in keyring: {password_key}")
            return password
        except Exception as e:
            logger.error(f"[EmailAccountsDB] Failed to get password from keyring: {e}")
            return None
    
    def _delete_password(self, password_key: str):
        """Usuń hasło z keyring"""
        try:
            keyring.delete_password(self.KEYRING_SERVICE, password_key)
            logger.debug(f"[EmailAccountsDB] Password deleted from keyring: {password_key}")
        except Exception as e:
            logger.warning(f"[EmailAccountsDB] Failed to delete password from keyring: {e}")
    
    # =========================================================================
    # SYNCHRONIZATION
    # =========================================================================
    
    def get_unsynced_accounts(self, user_id: str) -> List[Dict]:
        """Pobierz konta wymagające synchronizacji"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM email_accounts 
                WHERE user_id = ? AND is_synced = 0
            """, (user_id,))
            rows = cursor.fetchall()
        
        accounts = []
        for row in rows:
            account = self._row_to_dict(cursor, row)
            # Dodaj hasło dla synchronizacji
            account['password'] = self._get_password(account['password_key'])
            accounts.append(account)
        
        return accounts
    
    def mark_as_synced(self, account_id: str) -> bool:
        """Oznacz konto jako zsynchronizowane"""
        now = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE email_accounts
                SET is_synced = 1, synced_at = ?
                WHERE id = ?
            """, (now, account_id))
            conn.commit()
            return cursor.rowcount > 0
    
    # =========================================================================
    # UTILITIES
    # =========================================================================
    
    def _row_to_dict(self, cursor, row) -> Dict:
        """Konwertuj wiersz SQL na słownik"""
        columns = [col[0] for col in cursor.description]
        return dict(zip(columns, row))
    
    def account_exists(self, email_address: str, user_id: str) -> bool:
        """Sprawdź czy konto o danym adresie już istnieje"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM email_accounts
                WHERE email_address = ? AND user_id = ?
            """, (email_address, user_id))
            count = cursor.fetchone()[0]
        
        return count > 0
    
    def get_account_by_email(self, email_address: str, user_id: str) -> Optional[Dict]:
        """Pobierz konto po adresie e-mail"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM email_accounts
                WHERE email_address = ? AND user_id = ?
            """, (email_address, user_id))
            row = cursor.fetchone()
        
        if not row:
            return None
        
        account = self._row_to_dict(cursor, row)
        account['password'] = self._get_password(account['password_key'])
        
        return account
