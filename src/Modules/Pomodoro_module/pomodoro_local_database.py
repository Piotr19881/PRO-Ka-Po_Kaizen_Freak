"""
Lokalna baza danych SQLite dla modułu Pomodoro.
Przechowuje tematy sesji i logi sesji.
"""

import sqlite3
import json
from pathlib import Path
from typing import List, Optional, Dict, Any
from datetime import datetime, date
from loguru import logger


class PomodoroLocalDatabase:
    """Manager lokalnej bazy SQLite dla Pomodoro"""
    
    def __init__(self, db_path: str, user_id: str):
        """
        Inicjalizacja lokalnej bazy danych.
        
        Args:
            db_path: Ścieżka do pliku bazy SQLite
            user_id: ID użytkownika (UUID)
        """
        self.db_path = Path(db_path)
        self.user_id = user_id
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        logger.info(f"[POMODORO] Local database initialized: {self.db_path}")
    
    def _init_database(self):
        """Tworzy tabele jeśli nie istnieją"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela: session_topics
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_topics (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    color TEXT,
                    icon TEXT,
                    description TEXT,
                    total_sessions INTEGER DEFAULT 0,
                    total_work_time INTEGER DEFAULT 0,
                    total_break_time INTEGER DEFAULT 0,
                    sort_order INTEGER DEFAULT 0,
                    is_active BOOLEAN DEFAULT 1,
                    is_favorite BOOLEAN DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    synced_at TEXT,
                    deleted_at TEXT,
                    version INTEGER DEFAULT 1
                )
            """)
            
            # Tabela: session_logs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS session_logs (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    topic_id TEXT,
                    session_date TEXT NOT NULL,
                    started_at TEXT NOT NULL,
                    ended_at TEXT,
                    work_duration INTEGER NOT NULL,
                    short_break_duration INTEGER NOT NULL,
                    long_break_duration INTEGER NOT NULL,
                    actual_work_time INTEGER DEFAULT 0,
                    actual_break_time INTEGER DEFAULT 0,
                    session_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    pomodoro_count INTEGER DEFAULT 1,
                    notes TEXT,
                    tags TEXT,
                    productivity_rating INTEGER,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    synced_at TEXT,
                    deleted_at TEXT,
                    version INTEGER DEFAULT 1,
                    FOREIGN KEY (topic_id) REFERENCES session_topics (id)
                )
            """)
            
            # Tabela: user_settings (ustawienia użytkownika)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id TEXT PRIMARY KEY,
                    work_duration INTEGER DEFAULT 25,
                    short_break_duration INTEGER DEFAULT 5,
                    long_break_duration INTEGER DEFAULT 15,
                    sessions_count INTEGER DEFAULT 4,
                    auto_start_breaks BOOLEAN DEFAULT 0,
                    auto_start_pomodoro BOOLEAN DEFAULT 0,
                    sound_work_end BOOLEAN DEFAULT 1,
                    sound_break_end BOOLEAN DEFAULT 1,
                    popup_timer BOOLEAN DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Indeksy
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_topics_user 
                ON session_topics(user_id, deleted_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_user_date 
                ON session_logs(user_id, session_date, deleted_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_logs_topic 
                ON session_logs(topic_id, deleted_at)
            """)
            
            # Tabela: sync_queue (kolejka synchronizacji)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    type TEXT NOT NULL,
                    data TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_queue_user 
                ON sync_queue(user_id, created_at)
            """)
            
            # Migracja: Dodaj kolumnę is_synced jeśli nie istnieje
            # Sprawdź czy kolumna już istnieje w session_topics
            cursor.execute("PRAGMA table_info(session_topics)")
            topics_columns = [col[1] for col in cursor.fetchall()]
            if 'is_synced' not in topics_columns:
                logger.info("[POMODORO] Adding is_synced column to session_topics")
                cursor.execute("""
                    ALTER TABLE session_topics 
                    ADD COLUMN is_synced BOOLEAN DEFAULT 0
                """)
            
            # Sprawdź czy kolumna już istnieje w session_logs
            cursor.execute("PRAGMA table_info(session_logs)")
            logs_columns = [col[1] for col in cursor.fetchall()]
            if 'is_synced' not in logs_columns:
                logger.info("[POMODORO] Adding is_synced column to session_logs")
                cursor.execute("""
                    ALTER TABLE session_logs 
                    ADD COLUMN is_synced BOOLEAN DEFAULT 0
                """)
            
            # Sprawdź czy kolumna topic_name już istnieje w session_logs
            cursor.execute("PRAGMA table_info(session_logs)")
            logs_columns = [col[1] for col in cursor.fetchall()]
            if 'topic_name' not in logs_columns:
                logger.info("[POMODORO] Adding topic_name column to session_logs")
                cursor.execute("""
                    ALTER TABLE session_logs 
                    ADD COLUMN topic_name TEXT DEFAULT ''
                """)
            
            conn.commit()
    
    # ==================== SESSION TOPICS ====================
    
    def save_topic(self, topic_data: Dict[str, Any]) -> bool:
        """
        Zapisuje lub aktualizuje temat sesji.
        
        Args:
            topic_data: Słownik z danymi tematu
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Sprawdź czy istnieje
                cursor.execute(
                    "SELECT id FROM session_topics WHERE id = ?",
                    (topic_data['id'],)
                )
                exists = cursor.fetchone()
                
                # LOCAL-FIRST: Jeśli dane pochodzą z serwera (mają synced_at),
                # zachowaj is_synced. W przeciwnym razie ustaw is_synced = 0 (dirty)
                is_synced_value = topic_data.get('is_synced', 0)
                if topic_data.get('synced_at'):
                    is_synced_value = 1  # Dane z serwera = zsynchronizowane
                
                if exists:
                    # UPDATE
                    cursor.execute("""
                        UPDATE session_topics SET
                            name = ?,
                            color = ?,
                            icon = ?,
                            description = ?,
                            total_sessions = ?,
                            total_work_time = ?,
                            total_break_time = ?,
                            sort_order = ?,
                            is_active = ?,
                            is_favorite = ?,
                            updated_at = ?,
                            synced_at = ?,
                            deleted_at = ?,
                            version = ?,
                            is_synced = ?
                        WHERE id = ?
                    """, (
                        topic_data['name'],
                        topic_data.get('color'),
                        topic_data.get('icon'),
                        topic_data.get('description'),
                        topic_data.get('total_sessions', 0),
                        topic_data.get('total_work_time', 0),
                        topic_data.get('total_break_time', 0),
                        topic_data.get('sort_order', 0),
                        topic_data.get('is_active', True),
                        topic_data.get('is_favorite', False),
                        topic_data['updated_at'],
                        topic_data.get('synced_at'),
                        topic_data.get('deleted_at'),
                        topic_data.get('version', 1),
                        is_synced_value,
                        topic_data['id']
                    ))
                else:
                    # INSERT
                    cursor.execute("""
                        INSERT INTO session_topics (
                            id, user_id, name, color, icon, description,
                            total_sessions, total_work_time, total_break_time,
                            sort_order, is_active, is_favorite,
                            created_at, updated_at, synced_at, deleted_at, version, is_synced
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        topic_data['id'],
                        topic_data['user_id'],
                        topic_data['name'],
                        topic_data.get('color'),
                        topic_data.get('icon'),
                        topic_data.get('description'),
                        topic_data.get('total_sessions', 0),
                        topic_data.get('total_work_time', 0),
                        topic_data.get('total_break_time', 0),
                        topic_data.get('sort_order', 0),
                        topic_data.get('is_active', True),
                        topic_data.get('is_favorite', False),
                        topic_data['created_at'],
                        topic_data['updated_at'],
                        topic_data.get('synced_at'),
                        topic_data.get('deleted_at'),
                        topic_data.get('version', 1),
                        is_synced_value
                    ))
                
                conn.commit()
                logger.debug(f"[POMODORO] Topic saved: {topic_data['id']}")
                return True
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to save topic: {e}")
            return False
    
    def get_topic(self, topic_id: str) -> Optional[Dict[str, Any]]:
        """Pobiera temat po ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM session_topics 
                    WHERE id = ? AND user_id = ? AND deleted_at IS NULL
                """, (topic_id, self.user_id))
                
                row = cursor.fetchone()
                return dict(row) if row else None
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get topic: {e}")
            return None
    
    def get_all_topics(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """Pobiera wszystkie tematy użytkownika"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                query = "SELECT * FROM session_topics WHERE user_id = ?"
                params = [self.user_id]
                
                if not include_deleted:
                    query += " AND deleted_at IS NULL"
                
                query += " ORDER BY sort_order, name"
                
                cursor.execute(query, params)
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get topics: {e}")
            return []
    
    def delete_topic(self, topic_id: str, hard_delete: bool = False) -> bool:
        """Usuwa temat (soft delete lub hard delete)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if hard_delete:
                    cursor.execute(
                        "DELETE FROM session_topics WHERE id = ? AND user_id = ?",
                        (topic_id, self.user_id)
                    )
                else:
                    cursor.execute("""
                        UPDATE session_topics 
                        SET deleted_at = ?, updated_at = ?
                        WHERE id = ? AND user_id = ?
                    """, (
                        datetime.utcnow().isoformat(),
                        datetime.utcnow().isoformat(),
                        topic_id,
                        self.user_id
                    ))
                
                conn.commit()
                logger.debug(f"[POMODORO] Topic deleted: {topic_id}")
                return True
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to delete topic: {e}")
            return False
    
    # ==================== SESSION LOGS ====================
    
    def save_session(self, session_data: Dict[str, Any]) -> bool:
        """
        Zapisuje log sesji Pomodoro.
        
        Args:
            session_data: Słownik z danymi sesji (z SessionData.to_dict())
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Sprawdź czy istnieje
                cursor.execute(
                    "SELECT id FROM session_logs WHERE id = ?",
                    (session_data['id'],)
                )
                exists = cursor.fetchone()
                
                # Przygotuj tags (lista → JSON string)
                tags_json = json.dumps(session_data.get('tags', []))
                
                # LOCAL-FIRST: Jeśli dane pochodzą z serwera (mają synced_at),
                # zachowaj is_synced. W przeciwnym razie ustaw is_synced = 0 (dirty)
                is_synced_value = session_data.get('is_synced', 0)
                if session_data.get('synced_at'):
                    is_synced_value = 1  # Dane z serwera = zsynchronizowane
                
                if exists:
                    # UPDATE
                    cursor.execute("""
                        UPDATE session_logs SET
                            topic_id = ?,
                            topic_name = ?,
                            ended_at = ?,
                            actual_work_time = ?,
                            actual_break_time = ?,
                            status = ?,
                            notes = ?,
                            tags = ?,
                            productivity_rating = ?,
                            updated_at = ?,
                            synced_at = ?,
                            deleted_at = ?,
                            version = ?,
                            is_synced = ?
                        WHERE id = ?
                    """, (
                        session_data.get('topic_id'),
                        session_data.get('topic_name', ''),
                        session_data.get('ended_at'),
                        session_data.get('actual_work_time', 0),
                        session_data.get('actual_break_time', 0),
                        session_data['status'],
                        session_data.get('notes'),
                        tags_json,
                        session_data.get('productivity_rating'),
                        session_data['updated_at'],
                        session_data.get('synced_at'),
                        session_data.get('deleted_at'),
                        session_data.get('version', 1),
                        is_synced_value,
                        session_data['id']
                    ))
                else:
                    # INSERT
                    cursor.execute("""
                        INSERT INTO session_logs (
                            id, user_id, topic_id, topic_name, session_date, started_at, ended_at,
                            work_duration, short_break_duration, long_break_duration,
                            actual_work_time, actual_break_time,
                            session_type, status, pomodoro_count,
                            notes, tags, productivity_rating,
                            created_at, updated_at, synced_at, deleted_at, version, is_synced
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        session_data['id'],
                        session_data['user_id'],
                        session_data.get('topic_id'),
                        session_data.get('topic_name', ''),
                        session_data['session_date'],
                        session_data['started_at'],
                        session_data.get('ended_at'),
                        session_data['work_duration'],
                        session_data['short_break_duration'],
                        session_data['long_break_duration'],
                        session_data.get('actual_work_time', 0),
                        session_data.get('actual_break_time', 0),
                        session_data['session_type'],
                        session_data['status'],
                        session_data.get('pomodoro_count', 1),
                        session_data.get('notes'),
                        tags_json,
                        session_data.get('productivity_rating'),
                        session_data['created_at'],
                        session_data['updated_at'],
                        session_data.get('synced_at'),
                        session_data.get('deleted_at'),
                        session_data.get('version', 1),
                        is_synced_value
                    ))
                
                conn.commit()
                logger.debug(f"[POMODORO] Session saved: {session_data['id']}")
                return True
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to save session: {e}")
            return False
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Pobiera sesję po ID"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM session_logs 
                    WHERE id = ? AND user_id = ? AND deleted_at IS NULL
                """, (session_id, self.user_id))
                
                row = cursor.fetchone()
                if row:
                    data = dict(row)
                    # Parse JSON tags (używamy centralnej funkcji)
                    data['tags'] = self._parse_tags(data.get('tags'))
                    return data
                return None
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get session: {e}")
            return None
    
    def get_sessions_by_date(self, target_date: date) -> List[Dict[str, Any]]:
        """Pobiera sesje z konkretnej daty"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM session_logs 
                    WHERE user_id = ? 
                      AND session_date = ? 
                      AND deleted_at IS NULL
                    ORDER BY started_at
                """, (self.user_id, target_date.isoformat()))
                
                sessions = []
                for row in cursor.fetchall():
                    data = dict(row)
                    data['tags'] = self._parse_tags(data.get('tags'))
                    sessions.append(data)
                
                return sessions
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get sessions by date: {e}")
            return []
    
    def get_today_stats(self) -> Dict[str, int]:
        """
        Pobiera statystyki dzisiejszych sesji.
        
        Returns:
            {
                'total_sessions': int,
                'long_sessions': int,
                'total_work_time': int (sekundy),
                'total_break_time': int (sekundy)
            }
        """
        try:
            today = date.today().isoformat()
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Liczba wszystkich ukończonych sesji
                cursor.execute("""
                    SELECT COUNT(*) FROM session_logs
                    WHERE user_id = ? 
                      AND session_date = ?
                      AND status = 'completed'
                      AND deleted_at IS NULL
                """, (self.user_id, today))
                total_sessions = cursor.fetchone()[0]
                
                # Liczba długich przerw (= liczba ukończonych cykli)
                cursor.execute("""
                    SELECT COUNT(*) FROM session_logs
                    WHERE user_id = ? 
                      AND session_date = ?
                      AND session_type = 'long_break'
                      AND status = 'completed'
                      AND deleted_at IS NULL
                """, (self.user_id, today))
                long_sessions = cursor.fetchone()[0]
                
                # Suma czasu pracy
                cursor.execute("""
                    SELECT COALESCE(SUM(actual_work_time), 0) FROM session_logs
                    WHERE user_id = ? 
                      AND session_date = ?
                      AND session_type = 'work'
                      AND deleted_at IS NULL
                """, (self.user_id, today))
                total_work_time = cursor.fetchone()[0]
                
                # Suma czasu przerw
                cursor.execute("""
                    SELECT COALESCE(SUM(actual_break_time), 0) FROM session_logs
                    WHERE user_id = ? 
                      AND session_date = ?
                      AND session_type IN ('short_break', 'long_break')
                      AND deleted_at IS NULL
                """, (self.user_id, today))
                total_break_time = cursor.fetchone()[0]
                
                return {
                    'total_sessions': total_sessions,
                    'long_sessions': long_sessions,
                    'total_work_time': total_work_time,
                    'total_break_time': total_break_time
                }
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get today stats: {e}")
            return {
                'total_sessions': 0,
                'long_sessions': 0,
                'total_work_time': 0,
                'total_break_time': 0
            }
    
    def get_sessions_by_topic(self, topic_id: str, limit: int = 100) -> List[Dict[str, Any]]:
        """Pobiera sesje dla konkretnego tematu"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM session_logs 
                    WHERE user_id = ? 
                      AND topic_id = ? 
                      AND deleted_at IS NULL
                    ORDER BY started_at DESC
                    LIMIT ?
                """, (self.user_id, topic_id, limit))
                
                sessions = []
                for row in cursor.fetchall():
                    data = dict(row)
                    data['tags'] = self._parse_tags(data.get('tags'))
                    sessions.append(data)
                
                return sessions
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get sessions by topic: {e}")
            return []
    
    # ==================== SYNCHRONIZACJA ====================
    
    def get_unsynced_items(self) -> List[Dict[str, Any]]:
        """Pobiera wszystkie niezsynchronizowane elementy (topics + logs)"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                items = []
                
                # Topics
                cursor.execute("""
                    SELECT * FROM session_topics 
                    WHERE user_id = ? 
                      AND (synced_at IS NULL OR updated_at > synced_at)
                """, (self.user_id,))
                
                for row in cursor.fetchall():
                    data = dict(row)
                    data['_table'] = 'session_topics'
                    items.append(data)
                
                # Logs
                cursor.execute("""
                    SELECT * FROM session_logs 
                    WHERE user_id = ? 
                      AND (synced_at IS NULL OR updated_at > synced_at)
                """, (self.user_id,))
                
                for row in cursor.fetchall():
                    data = dict(row)
                    data['tags'] = self._parse_tags(data.get('tags'))
                    data['_table'] = 'session_logs'
                    items.append(data)
                
                logger.debug(f"[POMODORO] Found {len(items)} unsynced items")
                return items
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get unsynced items: {e}")
            return []
    
    def mark_as_synced(self, item_ids: List[str], table: str):
        """Oznacza elementy jako zsynchronizowane"""
        # SECURITY: Whitelist dozwolonych tabel (SQL injection prevention)
        if table not in ['session_topics', 'session_logs']:
            raise ValueError(f"Invalid table name: {table}")
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                now = datetime.utcnow().isoformat()
                
                for item_id in item_ids:
                    cursor.execute(f"""
                        UPDATE {table}
                        SET synced_at = ?
                        WHERE id = ?
                    """, (now, item_id))
                
                conn.commit()
                logger.debug(f"[POMODORO] Marked {len(item_ids)} items as synced in {table}")
                return True
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to mark as synced: {e}")
            return False
    
    # REMOVED: get_all_items() - nieużywana metoda (dead code)
    # REMOVED: _get_all_logs() - używana tylko przez get_all_items (dead code)
    
    # ==================== USER SETTINGS ====================
    
    def save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Zapisuje ustawienia użytkownika.
        
        Args:
            settings: Słownik z ustawieniami (work_duration, short_break_duration, etc.)
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                now = datetime.utcnow().isoformat()
                
                cursor.execute("""
                    INSERT INTO user_settings (
                        user_id, work_duration, short_break_duration,
                        long_break_duration, sessions_count,
                        auto_start_breaks, auto_start_pomodoro,
                        sound_work_end, sound_break_end, popup_timer,
                        updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(user_id) DO UPDATE SET
                        work_duration = excluded.work_duration,
                        short_break_duration = excluded.short_break_duration,
                        long_break_duration = excluded.long_break_duration,
                        sessions_count = excluded.sessions_count,
                        auto_start_breaks = excluded.auto_start_breaks,
                        auto_start_pomodoro = excluded.auto_start_pomodoro,
                        sound_work_end = excluded.sound_work_end,
                        sound_break_end = excluded.sound_break_end,
                        popup_timer = excluded.popup_timer,
                        updated_at = excluded.updated_at
                """, (
                    self.user_id,
                    settings.get('work_duration', 25),
                    settings.get('short_break_duration', 5),
                    settings.get('long_break_duration', 15),
                    settings.get('sessions_count', 4),
                    1 if settings.get('auto_start_breaks', False) else 0,
                    1 if settings.get('auto_start_pomodoro', False) else 0,
                    1 if settings.get('sound_work_end', True) else 0,
                    1 if settings.get('sound_break_end', True) else 0,
                    1 if settings.get('popup_timer', False) else 0,
                    now
                ))
                
                conn.commit()
                logger.info(f"[POMODORO] Settings saved for user {self.user_id}")
                return True
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to save settings: {e}")
            return False
    
    def get_settings(self) -> Optional[Dict[str, Any]]:
        """
        Pobiera ustawienia użytkownika.
        
        Returns:
            Słownik z ustawieniami lub None jeśli nie znaleziono
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM user_settings 
                    WHERE user_id = ?
                """, (self.user_id,))
                
                row = cursor.fetchone()
                if row:
                    settings = dict(row)
                    # Konwersja BOOLEAN (SQLite przechowuje jako INTEGER 0/1)
                    settings['auto_start_breaks'] = bool(settings['auto_start_breaks'])
                    settings['auto_start_pomodoro'] = bool(settings['auto_start_pomodoro'])
                    settings['sound_work_end'] = bool(settings['sound_work_end'])
                    settings['sound_break_end'] = bool(settings['sound_break_end'])
                    settings['popup_timer'] = bool(settings['popup_timer'])
                    logger.debug(f"[POMODORO] Settings loaded for user {self.user_id}")
                    return settings
                
                logger.debug(f"[POMODORO] No settings found for user {self.user_id}")
                return None
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get settings: {e}")
            return None
    
    # ========================================================================
    # METODY DLA SYNC MANAGER (LOCAL-FIRST ARCHITECTURE)
    # ========================================================================
    
    def _parse_tags(self, tags_value: Any) -> List[str]:
        """
        Centralna funkcja parsowania tags.
        Konwertuje różne formaty tags (str, list, None) na list[str].
        
        Args:
            tags_value: Tags w dowolnym formacie
            
        Returns:
            Lista stringów (może być pusta)
        """
        if not tags_value:
            return []
        
        if isinstance(tags_value, list):
            return tags_value
        
        if isinstance(tags_value, str):
            try:
                parsed = json.loads(tags_value)
                return parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                return []
        
        return []
    
    def get_unsynced_topics(self) -> List[Dict[str, Any]]:
        """
        Pobiera wszystkie tematy oznaczone jako is_synced = 0 (niezsynchronizowane).
        
        To są "brudne" rekordy które zostały utworzone/zmodyfikowane offline
        i czekają na wysłanie do serwera.
        
        Returns:
            Lista słowników z danymi tematów
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM session_topics
                    WHERE user_id = ? AND is_synced = 0 AND deleted_at IS NULL
                    ORDER BY created_at ASC
                """, (self.user_id,))
                
                topics = [dict(row) for row in cursor.fetchall()]
                logger.debug(f"[POMODORO] Found {len(topics)} unsynced topics")
                return topics
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get unsynced topics: {e}")
            return []
    
    def get_unsynced_sessions(self) -> List[Dict[str, Any]]:
        """
        Pobiera wszystkie sesje oznaczone jako is_synced = 0 (niezsynchronizowane).
        
        Returns:
            Lista słowników z danymi sesji
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM session_logs
                    WHERE user_id = ? AND is_synced = 0 AND deleted_at IS NULL
                    ORDER BY created_at ASC
                """, (self.user_id,))
                
                sessions = []
                for row in cursor.fetchall():
                    session_dict = dict(row)
                    
                    # CENTRALNA konwersja tags (JSON string → list)
                    session_dict['tags'] = self._parse_tags(session_dict.get('tags'))
                    
                    # Upewnij się że pomodoro_count >= 1 (API wymaga)
                    if session_dict.get('pomodoro_count', 0) < 1:
                        session_dict['pomodoro_count'] = 1
                    
                    sessions.append(session_dict)
                
                logger.debug(f"[POMODORO] Found {len(sessions)} unsynced sessions")
                return sessions
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get unsynced sessions: {e}")
            return []
    
    def mark_topic_as_synced(self, topic_id: str) -> bool:
        """
        Oznacza temat jako zsynchronizowany (is_synced = 1).
        
        Args:
            topic_id: ID tematu
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE session_topics
                    SET is_synced = 1, synced_at = ?
                    WHERE id = ? AND user_id = ?
                """, (datetime.utcnow().isoformat(), topic_id, self.user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[POMODORO] Failed to mark topic as synced: {e}")
            return False
    
    def mark_session_as_synced(self, session_id: str) -> bool:
        """
        Oznacza sesję jako zsynchronizowaną (is_synced = 1).
        
        Args:
            session_id: ID sesji
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE session_logs
                    SET is_synced = 1, synced_at = ?
                    WHERE id = ? AND user_id = ?
                """, (datetime.utcnow().isoformat(), session_id, self.user_id))
                conn.commit()
                return cursor.rowcount > 0
        except Exception as e:
            logger.error(f"[POMODORO] Failed to mark session as synced: {e}")
            return False
    
    # REMOVED: get_sync_queue() - nieużywana metoda (dead code)
    # REMOVED: remove_from_sync_queue() - nieużywana metoda (dead code)
    # Sync queue nie jest używana - zamiast tego używamy is_synced flag
    
    def get_topic_by_local_id(self, local_id: str) -> Optional[Any]:
        """
        Pobiera temat po local_id.
        
        Args:
            local_id: Local ID tematu
            
        Returns:
            PomodoroTopic lub None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM session_topics
                    WHERE user_id = ? AND id = ?
                """, (self.user_id, local_id))
                
                row = cursor.fetchone()
                if row:
                    from .pomodoro_models import PomodoroTopic
                    topic_data = dict(row)
                    return PomodoroTopic.from_dict(topic_data)
                
                return None
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get topic by local_id: {e}")
            return None
    
    def get_session_by_local_id(self, local_id: str) -> Optional[Any]:
        """
        Pobiera sesję po local_id.
        
        Args:
            local_id: Local ID sesji
            
        Returns:
            PomodoroSession lub None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM session_logs
                    WHERE user_id = ? AND id = ?
                """, (self.user_id, local_id))
                
                row = cursor.fetchone()
                if row:
                    from .pomodoro_models import PomodoroSession
                    session_data = dict(row)
                    return PomodoroSession.from_dict(session_data)
                
                return None
                
        except Exception as e:
            logger.error(f"[POMODORO] Failed to get session by local_id: {e}")
            return None
    
    def close(self):
        """Zamyka połączenie (cleanup)"""
        logger.debug("[POMODORO] LocalDatabase closed")