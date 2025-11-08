"""
CallCryptor Database Manager
=============================

Zarządzanie bazą danych nagrań rozmów telefonicznych.

Tabele:
- recording_sources: Źródła nagrań (foldery lokalne, konta e-mail)
- recordings: Nagrania z metadanymi, transkrypcją i AI summary
- recording_tags: Tagi dla organizacji nagrań

Features:
- CRUD operations dla wszystkich tabel
- Sync support (is_synced, server_id)
- Deduplication (file_hash)
- Foreign key constraints
- Indeksy dla wydajności
"""

import sqlite3
import uuid
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from loguru import logger
import json


class CallCryptorDatabase:
    """Menedżer bazy danych CallCryptor"""
    
    def __init__(self, db_path: str):
        """
        Inicjalizacja połączenia z bazą danych.
        
        Args:
            db_path: Ścieżka do pliku bazy danych SQLite
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self.conn = sqlite3.connect(str(self.db_path))
        self.conn.row_factory = sqlite3.Row  # Dostęp do kolumn po nazwach
        self.conn.execute("PRAGMA foreign_keys = ON")  # Włącz foreign keys
        
        self._create_tables()
        self._migrate_database()  # Dodaj migracje
        logger.info(f"[CallCryptorDB] Database initialized: {self.db_path}")
    
    def _migrate_database(self):
        """Migracje bazy danych"""
        cursor = self.conn.cursor()
        
        # Sprawdź czy kolumny search_type i search_all_folders istnieją w recording_sources
        cursor.execute("PRAGMA table_info(recording_sources)")
        columns = [row[1] for row in cursor.fetchall()]
        
        if 'search_type' not in columns:
            logger.info("[CallCryptorDB] Adding search_type column...")
            cursor.execute("ALTER TABLE recording_sources ADD COLUMN search_type TEXT DEFAULT 'SUBJECT'")
            self.conn.commit()
        
        if 'search_all_folders' not in columns:
            logger.info("[CallCryptorDB] Adding search_all_folders column...")
            cursor.execute("ALTER TABLE recording_sources ADD COLUMN search_all_folders BOOLEAN DEFAULT 0")
            self.conn.commit()
        
        if 'contact_ignore_words' not in columns:
            logger.info("[CallCryptorDB] Adding contact_ignore_words column...")
            cursor.execute("ALTER TABLE recording_sources ADD COLUMN contact_ignore_words TEXT")
            self.conn.commit()
        
        # Sprawdź kolumny w tabeli recordings
        cursor.execute("PRAGMA table_info(recordings)")
        recording_columns = [row[1] for row in cursor.fetchall()]
        
        if 'ai_summary_tasks' not in recording_columns:
            logger.info("[CallCryptorDB] Adding ai_summary_tasks column to recordings...")
            cursor.execute("ALTER TABLE recordings ADD COLUMN ai_summary_tasks TEXT")  # JSON array
            self.conn.commit()
    
    def _create_tables(self):
        """Utwórz tabele jeśli nie istnieją"""
        cursor = self.conn.cursor()
        
        # ==================== RECORDING SOURCES ====================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recording_sources (
                -- Identyfikatory
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                
                -- Podstawowe info
                source_name TEXT NOT NULL,
                source_type TEXT NOT NULL CHECK(source_type IN ('folder', 'email')),
                
                -- Opcje dla source_type = 'folder'
                folder_path TEXT,
                file_extensions TEXT,              -- JSON: ["mp3", "wav", "m4a"]
                scan_depth INTEGER DEFAULT 1,
                
                -- Opcje dla source_type = 'email'
                email_account_id TEXT,
                search_phrase TEXT,
                target_folder TEXT DEFAULT 'INBOX',
                attachment_pattern TEXT,            -- Regex dla nazw załączników
                
                -- Metadata
                is_active BOOLEAN DEFAULT 1,
                last_scan_at TEXT,
                recordings_count INTEGER DEFAULT 0,
                
                -- Timestamps
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                
                -- Synchronizacja
                is_synced BOOLEAN DEFAULT 0,
                synced_at TEXT,
                server_id TEXT,
                version INTEGER DEFAULT 1
                
                -- Note: email_account_id references email_accounts.db (separate database)
                -- Foreign key constraint removed - different database file
            )
        """)
        
        # Indeksy dla recording_sources
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sources_user 
            ON recording_sources(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sources_type 
            ON recording_sources(source_type)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_sources_active 
            ON recording_sources(is_active)
        """)
        
        # ==================== RECORDINGS ====================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recordings (
                -- Identyfikatory
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                source_id TEXT NOT NULL,
                
                -- Info o pliku
                file_name TEXT NOT NULL,
                file_path TEXT,
                file_size INTEGER,                  -- W bajtach
                file_hash TEXT,                     -- MD5/SHA256 dla deduplication
                
                -- Info z e-mail (jeśli applicable)
                email_message_id TEXT,
                email_subject TEXT,
                email_sender TEXT,
                
                -- Metadata nagrania
                contact_name TEXT,
                contact_phone TEXT,
                duration INTEGER,                   -- Czas trwania w sekundach
                recording_date TEXT,
                
                -- Organizacja
                tags TEXT,                          -- JSON: ["tag1", "tag2"]
                notes TEXT,
                
                -- Transkrypcja
                transcription_status TEXT DEFAULT 'pending' 
                    CHECK(transcription_status IN ('pending', 'processing', 'completed', 'failed')),
                transcription_text TEXT,
                transcription_language TEXT,
                transcription_confidence REAL,       -- 0.0 - 1.0
                transcription_date TEXT,
                transcription_error TEXT,
                
                -- AI Summary
                ai_summary_status TEXT DEFAULT 'pending'
                    CHECK(ai_summary_status IN ('pending', 'processing', 'completed', 'failed')),
                ai_summary_text TEXT,
                ai_summary_date TEXT,
                ai_summary_error TEXT,
                ai_key_points TEXT,                 -- JSON: ["punkt1", "punkt2"]
                ai_action_items TEXT,               -- JSON: [{"action": "...", "priority": "..."}]
                
                -- Linki do innych modułów
                note_id TEXT,
                task_id TEXT,
                
                -- Archiwizacja
                is_archived BOOLEAN DEFAULT 0,
                archived_at TEXT,
                archive_reason TEXT,
                
                -- Ulubione
                is_favorite BOOLEAN DEFAULT 0,
                favorited_at TEXT,
                
                -- Timestamps
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                
                -- Synchronizacja
                is_synced BOOLEAN DEFAULT 0,
                synced_at TEXT,
                server_id TEXT,
                version INTEGER DEFAULT 1,
                
                -- Foreign Keys
                FOREIGN KEY (source_id) REFERENCES recording_sources(id) ON DELETE CASCADE
            )
        """)
        
        # Indeksy dla recordings
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recordings_user 
            ON recordings(user_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recordings_source 
            ON recordings(source_id)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recordings_date 
            ON recordings(recording_date)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recordings_trans_status 
            ON recordings(transcription_status)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recordings_archived 
            ON recordings(is_archived)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recordings_favorite 
            ON recordings(is_favorite)
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_recordings_hash 
            ON recordings(file_hash)
        """)
        
        # ==================== RECORDING TAGS ====================
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS recording_tags (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                tag_name TEXT NOT NULL,
                tag_color TEXT DEFAULT '#2196F3',
                tag_icon TEXT,
                usage_count INTEGER DEFAULT 0,
                created_at TEXT NOT NULL,
                
                UNIQUE(user_id, tag_name)
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_tags_user 
            ON recording_tags(user_id)
        """)
        
        self.conn.commit()
        logger.info("[CallCryptorDB] Tables created successfully")
    
    # ==================== RECORDING SOURCES: CRUD ====================
    
    def add_source(self, source_data: Dict, user_id: str) -> str:
        """
        Dodaj nowe źródło nagrań.
        
        Args:
            source_data: {
                'source_name': str,
                'source_type': 'folder' | 'email',
                # Dla folder:
                'folder_path': str (optional),
                'file_extensions': List[str] (optional),
                'scan_depth': int (optional),
                # Dla email:
                'email_account_id': str (optional),
                'search_phrase': str (optional),
                'target_folder': str (optional),
                'attachment_pattern': str (optional)
            }
            user_id: ID użytkownika
            
        Returns:
            ID utworzonego źródła
        """
        source_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Konwertuj file_extensions do JSON jeśli lista
        file_extensions = source_data.get('file_extensions')
        if isinstance(file_extensions, list):
            file_extensions = json.dumps(file_extensions)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO recording_sources (
                id, user_id, source_name, source_type,
                folder_path, file_extensions, scan_depth,
                email_account_id, search_phrase, target_folder, attachment_pattern,
                contact_ignore_words,
                is_active, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            source_id,
            user_id,
            source_data['source_name'],
            source_data['source_type'],
            source_data.get('folder_path'),
            file_extensions,
            source_data.get('scan_depth', 1),
            source_data.get('email_account_id'),
            source_data.get('search_phrase'),
            source_data.get('target_folder', 'INBOX'),
            source_data.get('attachment_pattern'),
            source_data.get('contact_ignore_words'),
            source_data.get('is_active', True),
            now,
            now
        ))
        
        self.conn.commit()
        logger.info(f"[CallCryptorDB] Source added: {source_id}")
        return source_id
    
    def get_source(self, source_id: str) -> Optional[Dict]:
        """Pobierz źródło po ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM recording_sources WHERE id = ?", (source_id,))
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            # Parse JSON fields
            if data.get('file_extensions'):
                try:
                    data['file_extensions'] = json.loads(data['file_extensions'])
                except json.JSONDecodeError:
                    data['file_extensions'] = []
            return data
        return None
    
    def get_all_sources(self, user_id: str, active_only: bool = False) -> List[Dict]:
        """
        Pobierz wszystkie źródła użytkownika.
        
        Args:
            user_id: ID użytkownika
            active_only: Czy tylko aktywne źródła
            
        Returns:
            Lista słowników z danymi źródeł
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM recording_sources WHERE user_id = ?"
        params = [user_id]
        
        if active_only:
            query += " AND is_active = 1"
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        sources = []
        for row in rows:
            data = dict(row)
            # Parse JSON fields
            if data.get('file_extensions'):
                try:
                    data['file_extensions'] = json.loads(data['file_extensions'])
                except json.JSONDecodeError:
                    data['file_extensions'] = []
            sources.append(data)
        
        return sources
    
    def update_source(self, source_id: str, updates: Dict):
        """
        Zaktualizuj źródło.
        
        Args:
            source_id: ID źródła
            updates: Słownik z polami do zaktualizowania
        """
        updates['updated_at'] = datetime.now().isoformat()
        updates['is_synced'] = False
        
        # Konwertuj file_extensions do JSON jeśli lista
        if 'file_extensions' in updates and isinstance(updates['file_extensions'], list):
            updates['file_extensions'] = json.dumps(updates['file_extensions'])
        
        # Buduj zapytanie SQL
        fields = ', '.join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [source_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE recording_sources SET {fields} WHERE id = ?", values)
        self.conn.commit()
        
        logger.info(f"[CallCryptorDB] Source updated: {source_id}")
    
    def delete_source(self, source_id: str):
        """Usuń źródło (cascade delete nagrań)"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM recording_sources WHERE id = ?", (source_id,))
        self.conn.commit()
        
        logger.info(f"[CallCryptorDB] Source deleted: {source_id}")
    
    def update_source_stats(self, source_id: str, new_recordings: int = 0):
        """
        Aktualizuj statystyki źródła po skanowaniu.
        
        Args:
            source_id: ID źródła
            new_recordings: Liczba nowo dodanych nagrań
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE recording_sources 
            SET last_scan_at = ?, 
                recordings_count = recordings_count + ?, 
                updated_at = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            new_recordings,
            datetime.now().isoformat(),
            source_id
        ))
        self.conn.commit()
        logger.info(f"[CallCryptorDB] Updated source stats: {source_id}, +{new_recordings} recordings")
    
    def update_source_scan_time(self, source_id: str, recordings_count: int):
        """Zaktualizuj czas ostatniego skanowania i liczbę nagrań"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE recording_sources 
            SET last_scan_at = ?, recordings_count = ?, updated_at = ?
            WHERE id = ?
        """, (
            datetime.now().isoformat(),
            recordings_count,
            datetime.now().isoformat(),
            source_id
        ))
        self.conn.commit()
    
    # ==================== RECORDINGS: CRUD ====================
    
    def add_recording(self, recording_data: Dict, user_id: str) -> str:
        """
        Dodaj nowe nagranie.
        
        Args:
            recording_data: {
                'source_id': str,
                'file_name': str,
                'file_path': str (optional),
                'file_size': int (optional),
                'file_hash': str (optional),
                'contact_name': str (optional),
                'contact_phone': str (optional),
                'duration': int (optional),
                'recording_date': str (optional) - ISO format date,
                'tags': List[str] (optional),
                'notes': str (optional),
                # Email fields (optional):
                'email_message_id': str,
                'email_subject': str,
                'email_sender': str
            }
            user_id: ID użytkownika
            
        Returns:
            ID utworzonego nagrania
        """
        recording_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        # Użyj daty z recording_data jeśli istnieje, w przeciwnym razie użyj now
        recording_date = recording_data.get('recording_date') or now
        
        # Konwertuj tags do JSON jeśli lista
        tags = recording_data.get('tags')
        if isinstance(tags, list):
            tags = json.dumps(tags)
        
        cursor = self.conn.cursor()
        cursor.execute("""
            INSERT INTO recordings (
                id, user_id, source_id,
                file_name, file_path, file_size, file_hash,
                email_message_id, email_subject, email_sender,
                contact_name, contact_phone, duration, recording_date,
                tags, notes,
                created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            recording_id,
            user_id,
            recording_data['source_id'],
            recording_data['file_name'],
            recording_data.get('file_path'),
            recording_data.get('file_size'),
            recording_data.get('file_hash'),
            recording_data.get('email_message_id'),
            recording_data.get('email_subject'),
            recording_data.get('email_sender'),
            recording_data.get('contact_name'),
            recording_data.get('contact_phone'),
            recording_data.get('duration'),
            recording_date,  # Używamy daty z pliku/emaila lub now
            tags,
            recording_data.get('notes'),
            now,
            now
        ))
        
        self.conn.commit()
        logger.info(f"[CallCryptorDB] Recording added: {recording_id}")
        return recording_id
    
    def get_recording(self, recording_id: str) -> Optional[Dict]:
        """Pobierz nagranie po ID"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM recordings WHERE id = ?", (recording_id,))
        row = cursor.fetchone()
        
        if row:
            data = dict(row)
            # Parse JSON fields
            for field in ['tags', 'ai_key_points', 'ai_action_items']:
                if data.get(field):
                    try:
                        data[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        data[field] = []
            return data
        return None
    
    def get_recordings_by_source(
        self,
        source_id: str,
        include_archived: bool = False
    ) -> List[Dict]:
        """
        Pobierz nagrania z danego źródła.
        
        Args:
            source_id: ID źródła
            include_archived: Czy uwzględnić zarchiwizowane
            
        Returns:
            Lista nagrań
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM recordings WHERE source_id = ?"
        params = [source_id]
        
        if not include_archived:
            query += " AND is_archived = 0"
        
        query += " ORDER BY recording_date DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [self._parse_recording_row(row) for row in rows]
    
    def get_all_recordings(
        self,
        user_id: str,
        include_archived: bool = False,
        tags: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Pobierz wszystkie nagrania użytkownika.
        
        Args:
            user_id: ID użytkownika
            include_archived: Czy uwzględnić zarchiwizowane
            tags: Filtruj po tagach (optional)
            
        Returns:
            Lista nagrań
        """
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM recordings WHERE user_id = ?"
        params = [user_id]
        
        if not include_archived:
            query += " AND is_archived = 0"
        
        query += " ORDER BY recording_date DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        recordings = [self._parse_recording_row(row) for row in rows]
        
        # Filtruj po tagach jeśli podane
        if tags:
            recordings = [
                r for r in recordings
                if r.get('tags') and any(tag in r['tags'] for tag in tags)
            ]
        
        return recordings
    
    def _parse_recording_row(self, row) -> Dict:
        """Pomocnicza funkcja do parsowania wiersza nagrania"""
        data = dict(row)
        # Parse JSON fields
        for field in ['tags', 'ai_key_points', 'ai_action_items']:
            if data.get(field):
                try:
                    data[field] = json.loads(data[field])
                except json.JSONDecodeError:
                    data[field] = []
        return data
    
    def update_recording(self, recording_id: str, updates: Dict):
        """
        Zaktualizuj nagranie.
        
        Args:
            recording_id: ID nagrania
            updates: Słownik z polami do zaktualizowania
        """
        updates['updated_at'] = datetime.now().isoformat()
        updates['is_synced'] = False
        
        # Konwertuj listy do JSON
        for field in ['tags', 'ai_key_points', 'ai_action_items']:
            if field in updates and isinstance(updates[field], list):
                updates[field] = json.dumps(updates[field])
        
        # Buduj zapytanie SQL
        fields = ', '.join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [recording_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE recordings SET {fields} WHERE id = ?", values)
        self.conn.commit()
        
        logger.info(f"[CallCryptorDB] Recording updated: {recording_id}")
    
    def delete_recording(self, recording_id: str):
        """Usuń nagranie"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM recordings WHERE id = ?", (recording_id,))
        self.conn.commit()
        
        logger.info(f"[CallCryptorDB] Recording deleted: {recording_id}")
    
    def archive_recording(self, recording_id: str, reason: str = None):
        """Zarchiwizuj nagranie"""
        self.update_recording(recording_id, {
            'is_archived': True,
            'archived_at': datetime.now().isoformat(),
            'archive_reason': reason
        })
    
    def unarchive_recording(self, recording_id: str):
        """Przywróć nagranie z archiwum"""
        self.update_recording(recording_id, {
            'is_archived': False,
            'archived_at': None,
            'archive_reason': None
        })
    
    def toggle_favorite(self, recording_id: str) -> bool:
        """
        Przełącz status ulubionego dla nagrania.
        
        Args:
            recording_id: ID nagrania
            
        Returns:
            Nowy status is_favorite (True/False)
        """
        recording = self.get_recording(recording_id)
        if not recording:
            raise ValueError(f"Recording not found: {recording_id}")
        
        new_status = not recording.get('is_favorite', False)
        self.update_recording(recording_id, {
            'is_favorite': new_status,
            'favorited_at': datetime.now().isoformat() if new_status else None
        })
        
        logger.info(f"[CallCryptorDB] Recording favorite toggled: {recording_id} -> {new_status}")
        return new_status
    
    def get_favorite_recordings(self, user_id: str, limit: int = None) -> List[Dict]:
        """
        Pobierz wszystkie ulubione nagrania użytkownika.
        
        Args:
            user_id: ID użytkownika
            limit: Maksymalna liczba wyników
            
        Returns:
            Lista słowników z danymi nagrań
        """
        cursor = self.conn.cursor()
        query = """
            SELECT * FROM recordings 
            WHERE user_id = ? AND is_favorite = 1
            ORDER BY favorited_at DESC
        """
        
        if limit:
            query += f" LIMIT {limit}"
        
        cursor.execute(query, (user_id,))
        return [dict(row) for row in cursor.fetchall()]
    
    def recording_exists_by_hash(self, file_hash: str, user_id: str) -> bool:
        """Sprawdź czy nagranie z takim hashem już istnieje (deduplication)"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT COUNT(*) FROM recordings 
            WHERE file_hash = ? AND user_id = ?
        """, (file_hash, user_id))
        
        count = cursor.fetchone()[0]
        return count > 0
    
    # ==================== TAGS: CRUD ====================
    
    def add_tag(self, tag_data: Dict, user_id: str) -> str:
        """
        Dodaj nowy tag.
        
        Args:
            tag_data: {
                'tag_name': str,
                'tag_color': str (optional),
                'tag_icon': str (optional)
            }
            user_id: ID użytkownika
            
        Returns:
            ID utworzonego tagu
        """
        tag_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        cursor = self.conn.cursor()
        try:
            cursor.execute("""
                INSERT INTO recording_tags (
                    id, user_id, tag_name, tag_color, tag_icon, created_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                tag_id,
                user_id,
                tag_data['tag_name'],
                tag_data.get('tag_color', '#2196F3'),
                tag_data.get('tag_icon'),
                now
            ))
            
            self.conn.commit()
            logger.info(f"[CallCryptorDB] Tag added: {tag_id}")
            return tag_id
        except sqlite3.IntegrityError:
            logger.warning(f"[CallCryptorDB] Tag already exists: {tag_data['tag_name']}")
            # Zwróć istniejący tag
            cursor.execute("""
                SELECT id FROM recording_tags 
                WHERE user_id = ? AND tag_name = ?
            """, (user_id, tag_data['tag_name']))
            return cursor.fetchone()[0]
    
    def get_all_tags(self, user_id: str) -> List[Dict]:
        """Pobierz wszystkie tagi użytkownika"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM recording_tags 
            WHERE user_id = ? 
            ORDER BY usage_count DESC, tag_name ASC
        """, (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def update_tag(self, tag_id: str, updates: Dict):
        """Zaktualizuj tag"""
        fields = ', '.join([f"{key} = ?" for key in updates.keys()])
        values = list(updates.values()) + [tag_id]
        
        cursor = self.conn.cursor()
        cursor.execute(f"UPDATE recording_tags SET {fields} WHERE id = ?", values)
        self.conn.commit()
        
        logger.info(f"[CallCryptorDB] Tag updated: {tag_id}")
    
    def delete_tag(self, tag_id: str):
        """Usuń tag"""
        cursor = self.conn.cursor()
        cursor.execute("DELETE FROM recording_tags WHERE id = ?", (tag_id,))
        self.conn.commit()
        
        logger.info(f"[CallCryptorDB] Tag deleted: {tag_id}")
    
    def increment_tag_usage(self, tag_name: str, user_id: str):
        """Zwiększ licznik użycia tagu"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE recording_tags 
            SET usage_count = usage_count + 1 
            WHERE user_id = ? AND tag_name = ?
        """, (user_id, tag_name))
        self.conn.commit()
    
    # ==================== SYNC OPERATIONS ====================
    
    def get_unsynced_sources(self, user_id: str) -> List[Dict]:
        """Pobierz niesynchronizowane źródła"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM recording_sources 
            WHERE user_id = ? AND is_synced = 0
        """, (user_id,))
        
        return [dict(row) for row in cursor.fetchall()]
    
    def get_unsynced_recordings(self, user_id: str) -> List[Dict]:
        """Pobierz niesynchronizowane nagrania"""
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM recordings 
            WHERE user_id = ? AND is_synced = 0
        """, (user_id,))
        
        return [self._parse_recording_row(row) for row in cursor.fetchall()]
    
    def mark_source_synced(self, source_id: str, server_id: str = None):
        """Oznacz źródło jako zsynchronizowane"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE recording_sources 
            SET is_synced = 1, synced_at = ?, server_id = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), server_id, source_id))
        self.conn.commit()
    
    def mark_recording_synced(self, recording_id: str, server_id: str = None):
        """Oznacz nagranie jako zsynchronizowane"""
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE recordings 
            SET is_synced = 1, synced_at = ?, server_id = ?
            WHERE id = ?
        """, (datetime.now().isoformat(), server_id, recording_id))
        self.conn.commit()
    
    # ==================== UTILITIES ====================
    
    def close(self):
        """Zamknij połączenie z bazą"""
        if self.conn:
            self.conn.close()
            logger.info("[CallCryptorDB] Database connection closed")
    
    def __enter__(self):
        """Context manager support"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager cleanup"""
        self.close()
