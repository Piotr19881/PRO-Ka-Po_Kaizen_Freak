"""
System cache'owania i lokalnej bazy danych dla maili i kontaktów

Funkcjonalność:
- Cache maili w pamięci i na dysku (SQLite)
- Cache kontaktów
- Szybkie wczytywanie przy starcie aplikacji
- Synchronizacja w tle
- Automatyczne odświeżanie cache
"""

import json
import sqlite3
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import pickle


class MailCache:
    """Cache dla wiadomości email z SQLite i pamięcią"""
    
    def __init__(self, db_path: str = "mail_client/mail_cache.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.memory_cache: Dict[str, List[Dict[str, Any]]] = {}
        self.contacts_cache: Dict[str, Dict[str, Any]] = {}
        self.cache_lock = threading.Lock()
        
        self._init_database()
    
    def _init_database(self):
        """Inicjalizuje bazę danych SQLite"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Tabela maili
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS mails (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                uid TEXT UNIQUE NOT NULL,
                folder TEXT NOT NULL,
                account TEXT,
                mail_from TEXT,
                mail_to TEXT,
                subject TEXT,
                date TEXT,
                body TEXT,
                size TEXT,
                starred INTEGER DEFAULT 0,
                read INTEGER DEFAULT 0,
                attachments TEXT,
                json_data TEXT,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indeksy dla szybszego wyszukiwania
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_folder ON mails(folder)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_uid ON mails(uid)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_from ON mails(mail_from)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_date ON mails(date)")
        
        # Tabela kontaktów
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT UNIQUE NOT NULL,
                name TEXT,
                tags TEXT,
                color TEXT,
                last_contact TIMESTAMP,
                mail_count INTEGER DEFAULT 0,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_email ON contacts(email)")
        
        # Tabela metadanych (śledzenie synchronizacji)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_metadata (
                key TEXT PRIMARY KEY,
                value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
    
    def save_mails_to_cache(self, folder: str, mails: List[Dict[str, Any]], account: str = "local"):
        """Zapisuje maile do cache (pamięć + dysk)"""
        with self.cache_lock:
            # Zapisz do pamięci
            cache_key = f"{account}:{folder}"
            self.memory_cache[cache_key] = mails
            
            # Zapisz do SQLite
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            for mail in mails:
                uid = mail.get("_uid", f"mail-{hash(str(mail))}")
                
                try:
                    cursor.execute("""
                        INSERT OR REPLACE INTO mails 
                        (uid, folder, account, mail_from, mail_to, subject, date, body, 
                         size, starred, read, attachments, json_data, last_accessed)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """, (
                        uid,
                        folder,
                        account,
                        mail.get("from", ""),
                        mail.get("to", ""),
                        mail.get("subject", ""),
                        mail.get("date", ""),
                        mail.get("body", ""),
                        mail.get("size", ""),
                        1 if mail.get("starred") else 0,
                        1 if mail.get("read") else 0,
                        json.dumps(mail.get("attachments", [])),
                        json.dumps(mail)  # Pełny JSON jako backup
                    ))
                except Exception as e:
                    print(f"Błąd zapisu maila do cache: {e}")
            
            conn.commit()
            conn.close()
    
    def load_mails_from_cache(self, folder: str, account: str = "local") -> Optional[List[Dict[str, Any]]]:
        """Ładuje maile z cache (najpierw pamięć, potem dysk)"""
        with self.cache_lock:
            cache_key = f"{account}:{folder}"
            
            # Sprawdź cache w pamięci
            if cache_key in self.memory_cache:
                return self.memory_cache[cache_key]
            
            # Załaduj z SQLite
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT json_data FROM mails 
                WHERE folder = ? AND account = ?
                ORDER BY date DESC
            """, (folder, account))
            
            rows = cursor.fetchall()
            conn.close()
            
            if rows:
                mails = []
                for row in rows:
                    try:
                        mail = json.loads(row[0])
                        mails.append(mail)
                    except:
                        pass
                
                # Zapisz do pamięci dla przyszłych wywołań
                self.memory_cache[cache_key] = mails
                return mails
            
            return None
    
    def load_all_mails_from_cache(self) -> Dict[str, List[Dict[str, Any]]]:
        """Ładuje wszystkie maile z cache - szybkie wczytanie przy starcie"""
        result = {}
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Pobierz listę wszystkich folderów
        cursor.execute("SELECT DISTINCT folder FROM mails")
        folders = [row[0] for row in cursor.fetchall()]
        
        for folder in folders:
            cursor.execute("""
                SELECT json_data FROM mails 
                WHERE folder = ?
                ORDER BY date DESC
            """, (folder,))
            
            mails = []
            for row in cursor.fetchall():
                try:
                    mail = json.loads(row[0])
                    mails.append(mail)
                except:
                    pass
            
            if mails:
                result[folder] = mails
        
        conn.close()
        
        # Zapisz do pamięci
        with self.cache_lock:
            for folder, mails in result.items():
                self.memory_cache[f"local:{folder}"] = mails
        
        return result
    
    def update_mail_in_cache(self, uid: str, updates: Dict[str, Any]):
        """Aktualizuje konkretny mail w cache"""
        with self.cache_lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            # Pobierz aktualny mail
            cursor.execute("SELECT json_data FROM mails WHERE uid = ?", (uid,))
            row = cursor.fetchone()
            
            if row:
                try:
                    mail = json.loads(row[0])
                    mail.update(updates)
                    
                    # Aktualizuj w bazie
                    cursor.execute("""
                        UPDATE mails 
                        SET starred = ?, read = ?, json_data = ?, last_accessed = CURRENT_TIMESTAMP
                        WHERE uid = ?
                    """, (
                        1 if mail.get("starred") else 0,
                        1 if mail.get("read") else 0,
                        json.dumps(mail),
                        uid
                    ))
                    
                    conn.commit()
                    
                    # Aktualizuj w pamięci
                    for cache_key, mails in self.memory_cache.items():
                        for i, m in enumerate(mails):
                            if m.get("_uid") == uid:
                                mails[i].update(updates)
                                break
                
                except Exception as e:
                    print(f"Błąd aktualizacji maila: {e}")
            
            conn.close()
    
    def save_contact_to_cache(self, email: str, name: str = "", tags: Optional[List[str]] = None, color: str = ""):
        """Zapisuje kontakt do cache"""
        if tags is None:
            tags = []
        
        with self.cache_lock:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO contacts 
                    (email, name, tags, color, last_contact)
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    email,
                    name,
                    json.dumps(tags or []),
                    color
                ))
                
                conn.commit()
                
                # Zapisz do pamięci
                self.contacts_cache[email] = {
                    "email": email,
                    "name": name,
                    "tags": tags or [],
                    "color": color
                }
            
            except Exception as e:
                print(f"Błąd zapisu kontaktu: {e}")
            
            conn.close()
    
    def load_all_contacts_from_cache(self) -> Dict[str, Dict[str, Any]]:
        """Ładuje wszystkie kontakty z cache"""
        with self.cache_lock:
            if self.contacts_cache:
                return self.contacts_cache
            
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            cursor.execute("SELECT email, name, tags, color FROM contacts")
            
            contacts = {}
            for row in cursor.fetchall():
                email = row[0]
                contacts[email] = {
                    "email": email,
                    "name": row[1] or "",
                    "tags": json.loads(row[2]) if row[2] else [],
                    "color": row[3] or ""
                }
            
            conn.close()
            
            self.contacts_cache = contacts
            return contacts
    
    def increment_contact_mail_count(self, email: str):
        """Zwiększa licznik maili dla kontaktu"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE contacts 
            SET mail_count = mail_count + 1, last_contact = CURRENT_TIMESTAMP
            WHERE email = ?
        """, (email,))
        
        conn.commit()
        conn.close()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Zwraca statystyki cache"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("SELECT COUNT(*) FROM mails")
        mail_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM contacts")
        contact_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(DISTINCT folder) FROM mails")
        folder_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "mails": mail_count,
            "contacts": contact_count,
            "folders": folder_count,
            "memory_cache_size": len(self.memory_cache)
        }
    
    def clear_old_cache(self, days: int = 30):
        """Usuwa stare wpisy z cache (starsze niż X dni)"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute("""
            DELETE FROM mails 
            WHERE last_accessed < ? AND starred = 0
        """, (cutoff_date,))
        
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted
    
    def get_last_sync_time(self, account: str = "local") -> Optional[str]:
        """Pobiera czas ostatniej synchronizacji"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT value FROM sync_metadata WHERE key = ?
        """, (f"last_sync:{account}",))
        
        row = cursor.fetchone()
        conn.close()
        
        return row[0] if row else None
    
    def set_last_sync_time(self, account: str = "local"):
        """Ustawia czas ostatniej synchronizacji"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO sync_metadata (key, value, updated_at)
            VALUES (?, ?, CURRENT_TIMESTAMP)
        """, (f"last_sync:{account}", datetime.now().isoformat()))
        
        conn.commit()
        conn.close()


class BackgroundSyncManager:
    """Zarządza synchronizacją w tle"""
    
    def __init__(self, cache: MailCache, mail_view):
        self.cache = cache
        self.mail_view = mail_view
        self.sync_thread = None
        self.stop_sync = False
    
    def start_background_sync(self, interval_minutes: int = 5):
        """Rozpoczyna synchronizację w tle"""
        if self.sync_thread and self.sync_thread.is_alive():
            return
        
        self.stop_sync = False
        self.sync_thread = threading.Thread(
            target=self._sync_loop,
            args=(interval_minutes,),
            daemon=True
        )
        self.sync_thread.start()
    
    def _sync_loop(self, interval_minutes: int):
        """Pętla synchronizacji"""
        import time
        
        while not self.stop_sync:
            try:
                # Synchronizuj dane
                self._perform_sync()
                
                # Czekaj przed następną synchronizacją
                for _ in range(interval_minutes * 60):
                    if self.stop_sync:
                        break
                    time.sleep(1)
            
            except Exception as e:
                print(f"Błąd synchronizacji w tle: {e}")
                time.sleep(60)  # Poczekaj minutę przed ponowną próbą
    
    def _perform_sync(self):
        """Wykonuje synchronizację"""
        # Zapisz aktualne maile do cache
        if hasattr(self.mail_view, 'sample_mails'):
            for folder, mails in self.mail_view.sample_mails.items():
                self.cache.save_mails_to_cache(folder, mails)
        
        # Zapisz kontakty
        if hasattr(self.mail_view, 'contact_colors'):
            for email, color in self.mail_view.contact_colors.items():
                tags = self.mail_view.contact_tags.get(email, [])
                self.cache.save_contact_to_cache(email, "", tags, color.name() if hasattr(color, 'name') else str(color))
        
        # Oznacz czas synchronizacji
        self.cache.set_last_sync_time()
    
    def stop_background_sync(self):
        """Zatrzymuje synchronizację w tle"""
        self.stop_sync = True
        if self.sync_thread:
            self.sync_thread.join(timeout=5)


# Singleton cache instance
_mail_cache_instance = None

def get_mail_cache() -> MailCache:
    """Zwraca globalną instancję cache"""
    global _mail_cache_instance
    if _mail_cache_instance is None:
        _mail_cache_instance = MailCache()
    return _mail_cache_instance
