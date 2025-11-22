"""
Habit Database - zarządzanie lokalną bazą danych nawyków
Obsługuje kolumny nawyków i rekordy z wartościami dla każdego dnia
"""
import sqlite3
import json
import uuid
from pathlib import Path
from typing import List, Dict, Any, Optional, Callable
from datetime import datetime, date
from loguru import logger


class HabitDatabase:
    """Manager lokalnej bazy danych SQLite dla modułu Habit Tracker"""
    
    def __init__(self, db_path: Path, user_id: int = 1):
        """
        Inicjalizacja bazy danych nawyków
        
        Args:
            db_path: Ścieżka do pliku bazy danych
            user_id: ID użytkownika
        """
        self.db_path = db_path
        self.user_id = user_id
        self._sync_trigger: Optional[Callable[[str, str], None]] = None
        self._init_database()
        logger.info(f"[HABIT DB] Initialized for user {user_id} at {db_path}")
    
    def _migrate_database(self):
        """Migracja istniejącej bazy danych do nowej struktury z sync"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Sprawdź czy tabela habit_columns istnieje
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='habit_columns'
            """)
            table_exists = cursor.fetchone() is not None

            if table_exists:
                try:
                    # Sprawdź czy kolumny sync już istnieją w habit_columns
                    cursor.execute("PRAGMA table_info(habit_columns)")
                    columns = [col[1] for col in cursor.fetchall()]

                    # Dodaj kolumny sync do habit_columns jeśli nie istnieją
                    if 'remote_id' not in columns:
                        logger.info("[HABIT DB] Migrating habit_columns - adding sync columns")
                        # SQLite nie pozwala na UNIQUE przy ALTER TABLE, dodamy bez UNIQUE
                        try:
                            cursor.execute("ALTER TABLE habit_columns ADD COLUMN remote_id TEXT")
                            cursor.execute("ALTER TABLE habit_columns ADD COLUMN synced_at TIMESTAMP")
                            cursor.execute("ALTER TABLE habit_columns ADD COLUMN version INTEGER DEFAULT 1")
                            cursor.execute("ALTER TABLE habit_columns ADD COLUMN is_synced BOOLEAN DEFAULT 0")
                        except sqlite3.OperationalError as e:
                            logger.warning(f"[HABIT DB] Failed to alter habit_columns: {e}")
                            # Jeśli ALTER nie działa, tabela może być uszkodzona - spróbuj ją odtworzyć
                            try:
                                cursor.execute("DROP TABLE habit_columns")
                                logger.info("[HABIT DB] Dropped corrupted habit_columns table")
                            except sqlite3.OperationalError:
                                pass  # Nie udało się usunąć, tabela może nie istnieć

                        # Dodaj indeks UNIQUE osobno (może się nie udać, ale to nie problem)
                        try:
                            cursor.execute("CREATE UNIQUE INDEX idx_habit_columns_remote_unique ON habit_columns(remote_id)")
                        except sqlite3.OperationalError:
                            pass  # Indeks już istnieje lub remote_id ma duplikaty

                    # Dodaj is_synced jeśli istnieje remote_id ale nie ma is_synced
                    if 'remote_id' in columns and 'is_synced' not in columns:
                        logger.info("[HABIT DB] Adding is_synced column to habit_columns")
                        try:
                            cursor.execute("ALTER TABLE habit_columns ADD COLUMN is_synced BOOLEAN DEFAULT 0")
                        except sqlite3.OperationalError as e:
                            logger.warning(f"[HABIT DB] Failed to add is_synced to habit_columns: {e}")

                except sqlite3.OperationalError as e:
                    logger.error(f"[HABIT DB] Error during habit_columns migration: {e}")
                    # Jeśli migracja się nie udała, tabela może być uszkodzona
                    try:
                        cursor.execute("DROP TABLE IF EXISTS habit_columns")
                        logger.info("[HABIT DB] Dropped potentially corrupted habit_columns table")
                    except sqlite3.OperationalError:
                        pass

            # Sprawdź czy tabela habit_records istnieje
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name='habit_records'
            """)
            table_exists = cursor.fetchone() is not None

            if table_exists:
                # Sprawdź habit_records
                cursor.execute("PRAGMA table_info(habit_records)")
                columns = [col[1] for col in cursor.fetchall()]

                # Dodaj kolumny sync do habit_records jeśli nie istnieją
                if 'remote_id' not in columns:
                    logger.info("[HABIT DB] Migrating habit_records - adding sync columns")
                    cursor.execute("ALTER TABLE habit_records ADD COLUMN remote_id TEXT")
                    cursor.execute("ALTER TABLE habit_records ADD COLUMN synced_at TIMESTAMP")
                    cursor.execute("ALTER TABLE habit_records ADD COLUMN version INTEGER DEFAULT 1")
                    cursor.execute("ALTER TABLE habit_records ADD COLUMN is_synced BOOLEAN DEFAULT 0")

                    # Dodaj indeks UNIQUE osobno
                    try:
                        cursor.execute("CREATE UNIQUE INDEX idx_habit_records_remote_unique ON habit_records(remote_id)")
                    except sqlite3.OperationalError:
                        pass  # Indeks już istnieje lub remote_id ma duplikaty

                # Dodaj is_synced jeśli istnieje remote_id ale nie ma is_synced
                if 'remote_id' in columns and 'is_synced' not in columns:
                    logger.info("[HABIT DB] Adding is_synced column to habit_records")
                    cursor.execute("ALTER TABLE habit_records ADD COLUMN is_synced BOOLEAN DEFAULT 0")

            conn.commit()
            logger.info("[HABIT DB] Database migration completed")

    def _init_database(self):
        """Inicjalizacja struktury bazy danych z sync metadata"""
        # Najpierw przeprowadź migrację istniejących tabel
        self._migrate_database()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # ========== TABELA: habit_columns (z sync metadata) ==========
            # Przechowuje definicje kolumn nawyków
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habit_columns (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    scale_max INTEGER DEFAULT 10,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP,
                    synced_at TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    is_synced BOOLEAN DEFAULT 0,
                    remote_id TEXT UNIQUE,
                    UNIQUE(user_id, name)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_habit_columns_user 
                ON habit_columns(user_id, deleted_at, position)
            """)
            
            # ========== TABELA: habit_records (z sync metadata) ==========
            # Przechowuje wartości nawyków dla konkretnych dni
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habit_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    habit_id INTEGER NOT NULL,
                    date TEXT NOT NULL,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    synced_at TIMESTAMP,
                    version INTEGER DEFAULT 1,
                    is_synced BOOLEAN DEFAULT 0,
                    remote_id TEXT UNIQUE,
                    FOREIGN KEY (habit_id) REFERENCES habit_columns(id) ON DELETE CASCADE,
                    UNIQUE(user_id, habit_id, date)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_habit_records_user_date 
                ON habit_records(user_id, habit_id, date)
            """)
            
            # ========== TABELA: habit_settings (TYLKO LOKALNA - bez sync) ==========
            # Przechowuje ustawienia użytkownika (szerokości kolumn, blokady itp.)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS habit_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    setting_key TEXT NOT NULL,
                    setting_value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, setting_key)
                )
            """)
            
            # ========== INDEXY DLA SYNC ==========
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_habit_columns_remote 
                ON habit_columns(remote_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_habit_records_remote 
                ON habit_records(remote_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_habit_columns_sync 
                ON habit_columns(synced_at, updated_at)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_habit_records_sync 
                ON habit_records(synced_at, updated_at)
            """)
            
            # ========== TRIGGERY updated_at ==========
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_habit_columns_timestamp 
                AFTER UPDATE ON habit_columns
                BEGIN
                    UPDATE habit_columns SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END;
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_habit_records_timestamp 
                AFTER UPDATE ON habit_records
                BEGIN
                    UPDATE habit_records SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END;
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS update_habit_settings_timestamp 
                AFTER UPDATE ON habit_settings
                BEGIN
                    UPDATE habit_settings SET updated_at = CURRENT_TIMESTAMP 
                    WHERE id = NEW.id;
                END;
            """)
            
            # ========== TABELA: sync_queue ==========
            # Przechowuje kolejkę operacji do synchronizacji z serwerem
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,  -- 'habit_column' or 'habit_record'
                    entity_id TEXT NOT NULL,
                    action TEXT NOT NULL,       -- 'create', 'update', 'delete'
                    data TEXT,                  -- JSON data
                    retry_count INTEGER DEFAULT 0,
                    error_message TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_queue_entity 
                ON sync_queue(entity_type, entity_id)
            """)

            # Sprawdź czy istnieją istniejące tabele i dodaj brakujące kolumny
            self._migrate_existing_tables(cursor)
            
            conn.commit()
            logger.info("[HABIT DB] Database schema initialized with sync metadata")
    
    def _migrate_existing_tables(self, cursor):
        """
        Migracja istniejących tabel - dodaje brakujące kolumny sync metadata
        """
        try:
            # Sprawdź kolumny w habit_columns
            cursor.execute("PRAGMA table_info(habit_columns)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'synced_at' not in columns:
                cursor.execute("ALTER TABLE habit_columns ADD COLUMN synced_at TIMESTAMP")
                logger.info("[HABIT DB] Added synced_at to habit_columns")
            
            if 'version' not in columns:
                cursor.execute("ALTER TABLE habit_columns ADD COLUMN version INTEGER DEFAULT 1")
                logger.info("[HABIT DB] Added version to habit_columns")
            
            if 'remote_id' not in columns:
                cursor.execute("ALTER TABLE habit_columns ADD COLUMN remote_id TEXT UNIQUE")
                logger.info("[HABIT DB] Added remote_id to habit_columns")
            
            # Sprawdź kolumny w habit_records
            cursor.execute("PRAGMA table_info(habit_records)")
            columns = [col[1] for col in cursor.fetchall()]
            
            if 'synced_at' not in columns:
                cursor.execute("ALTER TABLE habit_records ADD COLUMN synced_at TIMESTAMP")
                logger.info("[HABIT DB] Added synced_at to habit_records")
            
            if 'version' not in columns:
                cursor.execute("ALTER TABLE habit_records ADD COLUMN version INTEGER DEFAULT 1")
                logger.info("[HABIT DB] Added version to habit_records")
            
            if 'remote_id' not in columns:
                cursor.execute("ALTER TABLE habit_records ADD COLUMN remote_id TEXT UNIQUE")
                logger.info("[HABIT DB] Added remote_id to habit_records")
                
        except Exception as e:
            logger.error(f"[HABIT DB] Migration error: {e}")
    
    # ========== CRUD: Habit Columns ==========
    
    def add_habit_column(self, name: str, habit_type: str, scale_max: int = 10) -> int:
        """
        Dodaje nową kolumnę nawyku
        
        Args:
            name: Nazwa nawyku
            habit_type: Typ nawyku (checkbox, counter, duration, time, scale, text)
            scale_max: Maksymalna wartość dla typu 'scale'
            
        Returns:
            ID nowo utworzonej kolumny
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Pobierz ostatnią pozycję
            cursor.execute("""
                SELECT COALESCE(MAX(position), -1) + 1
                FROM habit_columns
                WHERE user_id = ? AND deleted_at IS NULL
            """, (self.user_id,))
            position = cursor.fetchone()[0]
            
            # Generuj remote_id dla nowej kolumny
            remote_id = str(uuid.uuid4())
            
            cursor.execute("""
                INSERT INTO habit_columns (user_id, name, type, position, scale_max, remote_id, version, is_synced)
                VALUES (?, ?, ?, ?, ?, ?, 1, 0)
            """, (self.user_id, name, habit_type, position, scale_max, remote_id))
            
            last_id = cursor.lastrowid
            if last_id is None:
                raise RuntimeError("Failed to retrieve habit column ID after insert")
            habit_id = int(last_id)
            conn.commit()
            
            # Dodaj do sync queue
            self.add_to_sync_queue('habit_column', remote_id, 'create')
            
            logger.info(f"[HABIT DB] Added habit column: {name} (ID: {habit_id}, Type: {habit_type}, Remote: {remote_id})")
            return habit_id
    
    def get_habit_columns(self) -> List[Dict[str, Any]]:
        """
        Pobiera wszystkie aktywne kolumny nawyków
        
        Returns:
            Lista słowników z danymi kolumn
        """
        # Mapowanie polskich nazw typów na angielskie (dla kompatybilności)
        type_mapping = {
            "Checkbox": "checkbox",
            "Licznik": "counter",
            "Czas trwania": "duration",
            "Godzina": "time",
            "Skala": "scale",
            "Tekst": "text",
            # Zachowaj też oryginalne angielskie dla kompatybilności wstecznej
            "checkbox": "checkbox",
            "counter": "counter",
            "duration": "duration",
            "time": "time",
            "scale": "scale",
            "text": "text"
        }
        
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, type, position, scale_max, created_at, updated_at
                FROM habit_columns
                WHERE user_id = ? AND deleted_at IS NULL
                ORDER BY position
            """, (self.user_id,))
            
            columns = []
            for row in cursor.fetchall():
                column_dict = dict(row)
                # Normalizuj typ do angielskiego lowercase
                original_type = column_dict.get('type', '')
                normalized_type = type_mapping.get(original_type, original_type.lower())
                column_dict['type'] = normalized_type
                columns.append(column_dict)
            
            logger.debug(f"[HABIT DB] Retrieved {len(columns)} habit columns")
            return columns
    
    def remove_habit_column(self, habit_id: int) -> bool:
        """
        Usuwa kolumnę nawyku (soft delete)
        
        Args:
            habit_id: ID kolumny do usunięcia
            
        Returns:
            True jeśli usunięto, False w przeciwnym razie
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Pobierz remote_id przed usunięciem
            cursor.execute("""
                SELECT remote_id FROM habit_columns 
                WHERE id = ? AND user_id = ? AND deleted_at IS NULL
            """, (habit_id, self.user_id))
            
            remote_row = cursor.fetchone()
            if not remote_row:
                logger.warning(f"[HABIT DB] Column {habit_id} not found or already deleted")
                return False
            
            remote_id = remote_row[0]
            
            cursor.execute("""
                UPDATE habit_columns
                SET deleted_at = CURRENT_TIMESTAMP,
                    is_synced = 0,
                    updated_at = CURRENT_TIMESTAMP,
                    version = version + 1
                WHERE id = ? AND user_id = ? AND deleted_at IS NULL
            """, (habit_id, self.user_id))
            
            rows_affected = cursor.rowcount
            conn.commit()
            
            if rows_affected > 0:
                # Dodaj do sync queue jako delete
                if remote_id:
                    self.add_to_sync_queue('habit_column', remote_id, 'delete')
                
                logger.info(f"[HABIT DB] Removed habit column ID: {habit_id} (Remote: {remote_id})")
                return True
            else:
                logger.warning(f"[HABIT DB] Failed to remove habit column ID: {habit_id}")
                return False
    
    def update_habit_column(self, habit_id: int, name: Optional[str] = None, 
                           habit_type: Optional[str] = None, 
                           scale_max: Optional[int] = None) -> bool:
        """
        Aktualizuje kolumnę nawyku
        
        Args:
            habit_id: ID kolumny
            name: Nowa nazwa (opcjonalna)
            habit_type: Nowy typ (opcjonalny)
            scale_max: Nowa wartość max dla skali (opcjonalna)
            
        Returns:
            True jeśli zaktualizowano
        """
        updates = []
        params = []
        
        if name is not None:
            updates.append("name = ?")
            params.append(name)
        if habit_type is not None:
            updates.append("type = ?")
            params.append(habit_type)
        if scale_max is not None:
            updates.append("scale_max = ?")
            params.append(scale_max)
        
        if not updates:
            return False
        
        updates.append("is_synced = 0")  # Lokalna zmiana
        updates.append("updated_at = CURRENT_TIMESTAMP")
        updates.append("version = version + 1")
        params.extend([habit_id, self.user_id])
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Pobierz remote_id przed aktualizacją
            cursor.execute("""
                SELECT remote_id FROM habit_columns 
                WHERE id = ? AND user_id = ? AND deleted_at IS NULL
            """, (habit_id, self.user_id))
            
            remote_row = cursor.fetchone()
            if not remote_row:
                return False
            
            remote_id = remote_row[0]
            
            query = f"""
                UPDATE habit_columns
                SET {', '.join(updates)}
                WHERE id = ? AND user_id = ? AND deleted_at IS NULL
            """
            
            cursor.execute(query, params)
            rows_affected = cursor.rowcount
            conn.commit()
            
            if rows_affected > 0:
                # Dodaj do sync queue
                if remote_id:
                    self.add_to_sync_queue('habit_column', remote_id, 'update')
                
                logger.info(f"[HABIT DB] Updated habit column ID: {habit_id} (Remote: {remote_id})")
                return True
            return False
    
    def reorder_habit_columns(self, column_order: List[int]) -> bool:
        """
        Zmienia kolejność kolumn nawyków
        
        Args:
            column_order: Lista ID kolumn w nowej kolejności
            
        Returns:
            True jeśli zaktualizowano
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for position, habit_id in enumerate(column_order):
                cursor.execute("""
                    UPDATE habit_columns
                    SET position = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                """, (position, habit_id, self.user_id))
            
            conn.commit()
            logger.info(f"[HABIT DB] Reordered {len(column_order)} habit columns")
            return True
    
    # ========== CRUD: Habit Records ==========
    
    def get_habit_record(self, habit_id: int, record_date: str) -> Optional[str]:
        """
        Pobiera wartość nawyku dla konkretnego dnia
        
        Args:
            habit_id: ID nawyku
            record_date: Data w formacie YYYY-MM-DD
            
        Returns:
            Wartość nawyku lub None
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT value
                FROM habit_records
                WHERE user_id = ? AND habit_id = ? AND date = ?
            """, (self.user_id, habit_id, record_date))
            
            row = cursor.fetchone()
            return row[0] if row else None
    
    def set_habit_record(self, habit_id: int, record_date: str, value: str) -> bool:
        """
        Ustawia wartość nawyku dla konkretnego dnia
        
        Args:
            habit_id: ID nawyku
            record_date: Data w formacie YYYY-MM-DD
            value: Wartość do zapisania
            
        Returns:
            True jeśli zapisano
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sprawdź czy rekord już istnieje
            cursor.execute("""
                SELECT id, remote_id FROM habit_records 
                WHERE user_id = ? AND habit_id = ? AND date = ?
            """, (self.user_id, habit_id, record_date))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update istniejącego rekordu - ustaw is_synced=0 (lokalna zmiana)
                cursor.execute("""
                    UPDATE habit_records 
                    SET value = ?, is_synced = 0, updated_at = CURRENT_TIMESTAMP, version = version + 1
                    WHERE id = ?
                """, (value, existing[0]))
                
                record_remote_id = existing[1]
                action = 'update'
                
            else:
                # Wstaw nowy rekord z remote_id i is_synced=0 (lokalna zmiana)
                record_remote_id = str(uuid.uuid4())
                
                cursor.execute("""
                    INSERT INTO habit_records (user_id, habit_id, date, value, remote_id, version, is_synced)
                    VALUES (?, ?, ?, ?, ?, 1, 0)
                """, (self.user_id, habit_id, record_date, value, record_remote_id))
                
                action = 'create'
            
            conn.commit()
            
            # Dodaj do sync queue
            self.add_to_sync_queue('habit_record', record_remote_id, action)
            
            logger.debug(f"[HABIT DB] Set record for habit {habit_id} on {record_date}: {value} (Remote: {record_remote_id})")
            return True
    
    def get_habit_records_for_month(self, habit_id: int, year: int, month: int) -> Dict[str, str]:
        """
        Pobiera wszystkie rekordy nawyku dla danego miesiąca
        
        Args:
            habit_id: ID nawyku
            year: Rok
            month: Miesiąc (1-12)
            
        Returns:
            Słownik {data: wartość}
        """
        # Oblicz zakres dat
        start_date = f"{year:04d}-{month:02d}-01"
        if month == 12:
            end_date = f"{year+1:04d}-01-01"
        else:
            end_date = f"{year:04d}-{month+1:02d}-01"
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT date, value
                FROM habit_records
                WHERE user_id = ? AND habit_id = ? 
                    AND date >= ? AND date < ?
            """, (self.user_id, habit_id, start_date, end_date))
            
            records = {row[0]: row[1] for row in cursor.fetchall()}
            logger.debug(f"[HABIT DB] Retrieved {len(records)} records for habit {habit_id} in {year}-{month:02d}")
            return records
    
    def delete_habit_record(self, habit_id: int, record_date: str) -> bool:
        """
        Usuwa rekord nawyku dla konkretnego dnia
        
        Args:
            habit_id: ID nawyku
            record_date: Data w formacie YYYY-MM-DD
            
        Returns:
            True jeśli usunięto
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Pobierz remote_id przed usunięciem
            cursor.execute("""
                SELECT remote_id FROM habit_records 
                WHERE user_id = ? AND habit_id = ? AND date = ?
            """, (self.user_id, habit_id, record_date))
            
            remote_row = cursor.fetchone()
            if not remote_row:
                logger.warning(f"[HABIT DB] Record for habit {habit_id} on {record_date} not found")
                return False
            
            remote_id = remote_row[0]
            
            cursor.execute("""
                DELETE FROM habit_records
                WHERE user_id = ? AND habit_id = ? AND date = ?
            """, (self.user_id, habit_id, record_date))
            
            rows_affected = cursor.rowcount
            conn.commit()
            
            if rows_affected > 0:
                # Dodaj do sync queue jako delete (jeśli ma remote_id)
                if remote_id:
                    self.add_to_sync_queue('habit_record', remote_id, 'delete')
                
                logger.info(f"[HABIT DB] Deleted record for habit {habit_id} on {record_date} (Remote: {remote_id})")
                return True
            return False
    
    # ========== Settings Management ==========
    
    def get_setting(self, setting_key: str, default_value: Optional[str] = None) -> Optional[str]:
        """
        Pobiera ustawienie użytkownika
        
        Args:
            setting_key: Klucz ustawienia
            default_value: Domyślna wartość jeśli brak
            
        Returns:
            Wartość ustawienia lub default_value
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT setting_value
                FROM habit_settings
                WHERE user_id = ? AND setting_key = ?
            """, (self.user_id, setting_key))
            
            row = cursor.fetchone()
            return row[0] if row else default_value
    
    def set_setting(self, setting_key: str, setting_value: str) -> bool:
        """
        Zapisuje ustawienie użytkownika
        
        Args:
            setting_key: Klucz ustawienia
            setting_value: Wartość
            
        Returns:
            True jeśli zapisano
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO habit_settings (user_id, setting_key, setting_value)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id, setting_key) 
                DO UPDATE SET 
                    setting_value = excluded.setting_value,
                    updated_at = CURRENT_TIMESTAMP
            """, (self.user_id, setting_key, setting_value))
            
            conn.commit()
            logger.debug(f"[HABIT DB] Set setting: {setting_key} = {setting_value}")
            return True
    
    # ========== Utility Methods ==========
    
    def get_statistics(self, habit_id: int, start_date: str, end_date: str) -> Dict[str, Any]:
        """
        Pobiera statystyki nawyku dla zakresu dat
        
        Args:
            habit_id: ID nawyku
            start_date: Data początkowa YYYY-MM-DD
            end_date: Data końcowa YYYY-MM-DD
            
        Returns:
            Słownik ze statystykami
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Pobierz wszystkie rekordy w zakresie
            cursor.execute("""
                SELECT date, value
                FROM habit_records
                WHERE user_id = ? AND habit_id = ? 
                    AND date >= ? AND date <= ?
                ORDER BY date
            """, (self.user_id, habit_id, start_date, end_date))
            
            records = cursor.fetchall()
            
            # Podstawowe statystyki
            stats = {
                'total_records': len(records),
                'start_date': start_date,
                'end_date': end_date,
                'records': records
            }
            
            # Dla typu checkbox - oblicz streak
            if records:
                values = [r[1] for r in records]
                if all(v in ['0', '1', ''] for v in values):
                    # To checkbox - oblicz najdłuższy streak
                    current_streak = 0
                    max_streak = 0
                    for val in values:
                        if val == '1':
                            current_streak += 1
                            max_streak = max(max_streak, current_streak)
                        else:
                            current_streak = 0
                    
                    stats['max_streak'] = max_streak
                    stats['current_streak'] = current_streak
                    stats['completion_rate'] = values.count('1') / len(values) if values else 0
            
            return stats
    
    def export_all_data(self) -> Dict[str, Any]:
        """
        Eksportuje wszystkie dane użytkownika do słownika
        
        Returns:
            Słownik z pełnymi danymi
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            # Pobierz kolumny
            cursor.execute("""
                SELECT * FROM habit_columns
                WHERE user_id = ? AND deleted_at IS NULL
            """, (self.user_id,))
            columns = [dict(row) for row in cursor.fetchall()]
            
            # Pobierz wszystkie rekordy
            cursor.execute("""
                SELECT r.* FROM habit_records r
                JOIN habit_columns c ON r.habit_id = c.id
                WHERE r.user_id = ? AND c.deleted_at IS NULL
            """, (self.user_id,))
            records = [dict(row) for row in cursor.fetchall()]
            
            # Pobierz ustawienia
            cursor.execute("""
                SELECT * FROM habit_settings
                WHERE user_id = ?
            """, (self.user_id,))
            settings = [dict(row) for row in cursor.fetchall()]
            
            data = {
                'columns': columns,
                'records': records,
                'settings': settings,
                'exported_at': datetime.now().isoformat()
            }
            
            logger.info(f"[HABIT DB] Exported data: {len(columns)} columns, {len(records)} records")
            return data
    
    # =========================================================================
    # SYNC QUEUE MANAGEMENT
    # =========================================================================
    
    def set_sync_trigger(self, callback: Optional[Callable[[str, str], None]]):
        """Zarejestruj callback wywoływany po dodaniu elementu do kolejki sync."""
        self._sync_trigger = callback

    def add_to_sync_queue(self, entity_type: str, entity_id: str, action: str, data: Optional[Dict] = None, *, trigger_sync: bool = True):
        """Dodaj operację do kolejki synchronizacji"""
        
        logger.info(f"🔄 [HABIT DB] SYNC QUEUE: Dodaję {entity_type} {entity_id} action={action}")
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Usuń istniejące wpisy dla tej samej entity (unikanie duplikatów)
            cursor.execute("""
                DELETE FROM sync_queue 
                WHERE entity_type = ? AND entity_id = ?
            """, (entity_type, entity_id))
            
            # Dodaj nowy wpis
            cursor.execute("""
                INSERT INTO sync_queue (entity_type, entity_id, action, data)
                VALUES (?, ?, ?, ?)
            """, (entity_type, entity_id, action, json.dumps(data) if data else None))
            
            conn.commit()
            logger.info(f"✅ [HABIT SYNC] Dodano do sync queue: {entity_type} {entity_id} ({action})")

        if trigger_sync and self._sync_trigger:
            try:
                self._sync_trigger(entity_type, action)
            except Exception as exc:
                logger.error(f"[HABIT DB] Sync trigger callback failed: {exc}")
    
    def get_sync_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Pobierz elementy z kolejki synchronizacji"""
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, entity_type, entity_id, action, data, retry_count, error_message,
                       created_at, updated_at
                FROM sync_queue 
                ORDER BY created_at ASC 
                LIMIT ?
            """, (limit,))
            
            rows = cursor.fetchall()
            
            return [{
                'id': row[0],
                'entity_type': row[1],
                'entity_id': row[2],
                'action': row[3],
                'data': json.loads(row[4]) if row[4] else None,
                'retry_count': row[5],
                'error_message': row[6],
                'created_at': row[7],
                'updated_at': row[8]
            } for row in rows]
    
    def remove_from_sync_queue(self, queue_id: int) -> bool:
        """Usuń element z kolejki synchronizacji"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM sync_queue WHERE id = ?", (queue_id,))
            conn.commit()
            
            return cursor.rowcount > 0
    
    def update_sync_queue_error(self, queue_id: int, error: str) -> bool:
        """Zaktualizuj błąd w kolejce synchronizacji"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE sync_queue 
                SET retry_count = retry_count + 1, 
                    error_message = ?, 
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (error, queue_id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def clear_sync_queue(self):
        """Wyczyść całą kolejkę synchronizacji"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM sync_queue")
            conn.commit()
            logger.info("[HABIT SYNC] Cleared sync queue")

    def requeue_unsynced_items(self) -> Dict[str, int]:
        """Ponownie dodaj niezsynchronizowane kolumny i rekordy do kolejki, ale tylko jeśli nie są już w kolejce."""

        stats = {'columns': 0, 'records': 0}

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()

            # Pobierz już istniejące wpisy w kolejce, aby uniknąć duplikatów
            cursor.execute("SELECT entity_type, entity_id FROM sync_queue")
            queued = {(row[0], row[1]) for row in cursor.fetchall()}

            # Dodaj kolumny tylko jeśli nie są już w kolejce
            cursor.execute(
                """
                    SELECT id, remote_id, deleted_at
                    FROM habit_columns
                    WHERE user_id = ? AND is_synced = 0
                """,
                (self.user_id,),
            )

            for local_id, remote_id, deleted_at in cursor.fetchall():
                entity_id = str(remote_id or local_id)
                key = ('habit_column', entity_id)
                if key in queued:
                    continue  # Pomiń jeśli już w kolejce

                action = 'delete' if deleted_at else 'update'
                self.add_to_sync_queue('habit_column', entity_id, action, trigger_sync=False)
                queued.add(key)
                stats['columns'] += 1

            # Dodaj rekordy tylko jeśli nie są już w kolejce
            cursor.execute(
                """
                    SELECT id, remote_id
                    FROM habit_records
                    WHERE user_id = ? AND is_synced = 0
                """,
                (self.user_id,),
            )

            for local_id, remote_id in cursor.fetchall():
                entity_id = str(remote_id or local_id)
                key = ('habit_record', entity_id)
                if key in queued:
                    continue  # Pomiń jeśli już w kolejce

                self.add_to_sync_queue('habit_record', entity_id, 'update', trigger_sync=False)
                queued.add(key)
                stats['records'] += 1

        if stats['columns'] or stats['records']:
            logger.info(
                f"[HABIT SYNC] Requeued {stats['columns']} columns and {stats['records']} records (avoided duplicates)"
            )

        return stats

    def mark_all_for_resync(self) -> Dict[str, int]:
        """Ustaw flagę is_synced=0 dla wszystkich lokalnych danych."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                    UPDATE habit_columns
                    SET is_synced = 0
                    WHERE user_id = ? AND deleted_at IS NULL
                """,
                (self.user_id,),
            )
            columns_marked = cursor.rowcount

            cursor.execute(
                """
                    UPDATE habit_records
                    SET is_synced = 0
                    WHERE user_id = ?
                """,
                (self.user_id,),
            )
            records_marked = cursor.rowcount

            conn.commit()

        logger.info(
            f"[HABIT SYNC] Marked {columns_marked} columns and {records_marked} records for resync"
        )

        return {'columns': columns_marked, 'records': records_marked}

    def mark_all_synced(self):
        """Oznacz wszystkie lokalne dane jako zsynchronizowane."""

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            cursor.execute(
                """
                    UPDATE habit_columns
                    SET is_synced = 1, synced_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND deleted_at IS NULL
                """,
                (self.user_id,),
            )

            cursor.execute(
                """
                    UPDATE habit_records
                    SET is_synced = 1, synced_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                """,
                (self.user_id,),
            )

            conn.commit()

        logger.info("[HABIT SYNC] Marked all local habit data as synced")
    
    # =========================================================================
    # GET UNSYNCED ITEMS (analogicznie do Pomodoro)
    # =========================================================================
    
    def get_unsynced_columns(self) -> List[Dict[str, Any]]:
        """
        Pobierz niezsynchronizowane kolumny (is_synced = 0).
        
        Returns:
            Lista słowników z danymi kolumn
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, user_id, name, type, scale_max, created_at, updated_at, 
                       version, remote_id, is_synced
                FROM habit_columns 
                WHERE user_id = ? AND is_synced = 0 AND deleted_at IS NULL
                ORDER BY created_at
            """, (self.user_id,))
            
            columns = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"[HABIT DB] Found {len(columns)} unsynced columns")
            return columns
    
    def get_unsynced_records(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Pobierz niezsynchronizowane rekordy (is_synced = 0).
        
        Args:
            limit: Maksymalna liczba rekordów do pobrania
            
        Returns:
            Lista słowników z danymi rekordów
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT r.id, r.user_id, r.habit_id, r.date, r.value, 
                       r.created_at, r.updated_at, r.version, r.remote_id, r.is_synced,
                       c.remote_id as column_remote_id
                FROM habit_records r
                JOIN habit_columns c ON r.habit_id = c.id
                WHERE r.user_id = ? AND r.is_synced = 0
                ORDER BY r.created_at
                LIMIT ?
            """, (self.user_id, limit))
            
            records = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"[HABIT DB] Found {len(records)} unsynced records")
            return records
    
    # =========================================================================
    # SYNC DATA METHODS
    # =========================================================================
    
    def get_column_sync_data(self, column_id: str) -> Optional[Dict[str, Any]]:
        """Pobierz dane kolumny do synchronizacji"""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, type, position, scale_max, created_at, updated_at, version, remote_id
                FROM habit_columns 
                WHERE (id = ? OR remote_id = ?) AND user_id = ? AND deleted_at IS NULL
            """, (column_id, column_id, self.user_id))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            remote_id = row['remote_id'] or str(row['id'])
            return {
                'id': remote_id,
                'name': row['name'],
                'habit_type': row['type'],
                'position': row['position'],
                'scale_max': row['scale_max'],
                'created_at': row['created_at'],
                'updated_at': row['updated_at'],
                'version': row['version']
            }
    
    def get_record_sync_data(self, record_id: str) -> Optional[Dict[str, Any]]:
        """Pobierz dane rekordu do synchronizacji"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT r.id, r.habit_id, r.date, r.value, r.created_at, r.updated_at, 
                       r.version, r.remote_id, c.remote_id as column_remote_id
                FROM habit_records r
                JOIN habit_columns c ON r.habit_id = c.id
                WHERE (r.id = ? OR r.remote_id = ?) AND r.user_id = ?
            """, (record_id, record_id, self.user_id))
            
            row = cursor.fetchone()
            if not row:
                return None
            
            return {
                'id': row[7] or str(row[0]),  # Use remote_id if available, else local id
                'column_id': row[8] or str(row[1]),  # Use column's remote_id if available
                'record_date': row[2],
                'value': row[3],
                'notes': '',  # Habit tracker doesn't have notes field yet
                'created_at': row[4],
                'updated_at': row[5],
                'version': row[6]
            }
    
    def get_all_columns(self) -> List[Dict[str, Any]]:
        """Pobierz wszystkie aktywne kolumny"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, remote_id FROM habit_columns 
                WHERE user_id = ? AND deleted_at IS NULL
            """, (self.user_id,))
            
            return [{'id': row[1] or str(row[0])} for row in cursor.fetchall()]
    
    def get_all_records(self) -> List[Dict[str, Any]]:
        """Pobierz wszystkie rekordy"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, remote_id FROM habit_records 
                WHERE user_id = ?
            """, (self.user_id,))
            
            return [{'id': row[1] or str(row[0])} for row in cursor.fetchall()]
    
    # =========================================================================
    # SYNC STATUS METHODS
    # =========================================================================
    
    def mark_column_synced(self, column_id: str):
        """Oznacz kolumnę jako zsynchronizowaną"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE habit_columns 
                SET is_synced = 1, synced_at = CURRENT_TIMESTAMP
                WHERE (id = ? OR remote_id = ?) AND user_id = ?
            """, (column_id, column_id, self.user_id))
            
            conn.commit()
    
    def mark_record_synced(self, record_id: str):
        """Oznacz rekord jako zsynchronizowany"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE habit_records 
                SET is_synced = 1, synced_at = CURRENT_TIMESTAMP
                WHERE (id = ? OR remote_id = ?) AND user_id = ?
            """, (record_id, record_id, self.user_id))
            
            conn.commit()
    
    def update_column_version(self, column_id: str, version: int):
        """Zaktualizuj wersję kolumny"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE habit_columns 
                SET version = ?, updated_at = CURRENT_TIMESTAMP
                WHERE (id = ? OR remote_id = ?) AND user_id = ?
            """, (version, column_id, column_id, self.user_id))
            
            conn.commit()
    
    def update_record_version(self, record_id: str, version: int):
        """Zaktualizuj wersję rekordu"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE habit_records 
                SET version = ?, updated_at = CURRENT_TIMESTAMP
                WHERE (id = ? OR remote_id = ?) AND user_id = ?
            """, (version, record_id, record_id, self.user_id))
            
            conn.commit()
    
    # =========================================================================
    # SYNC-AWARE CRUD METHODS
    # =========================================================================
    
    def save_habit_column(self, column_id: str, name: str, habit_type: str, 
                         color: str = '#3498db', is_active: bool = True, 
                         scale_max: Optional[int] = None, is_synced: int = 1):
        """
        Zapisz kolumnę z sync metadata
        
        Args:
            column_id: Remote ID kolumny (UUID)
            name: Nazwa nawyku
            habit_type: Typ nawyku
            color: Kolor nawyku
            is_active: Czy kolumna jest aktywna
            scale_max: Maksymalna wartość dla typu 'scale' (opcjonalnie)
            is_synced: Czy dane pochodzą z serwera (1) czy lokalne (0), domyślnie 1
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sprawdź czy kolumna już istnieje (najpierw po remote_id, potem po name)
            cursor.execute("""
                SELECT id, remote_id FROM habit_columns 
                WHERE (remote_id = ? OR name = ?) AND user_id = ?
            """, (column_id, name, self.user_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update istniejącej kolumny - zaktualizuj remote_id jeśli było NULL
                cursor.execute("""
                    UPDATE habit_columns 
                    SET name = ?, type = ?, scale_max = ?, remote_id = ?, is_synced = ?, 
                        updated_at = CURRENT_TIMESTAMP, version = version + 1
                    WHERE id = ?
                """, (name, habit_type, scale_max, column_id, is_synced, existing[0]))
                
                local_id = existing[0]
            else:
                # Wstaw nową kolumnę - użyj is_synced z parametru
                cursor.execute("""
                    SELECT COALESCE(MAX(position), 0) + 1 FROM habit_columns 
                    WHERE user_id = ? AND deleted_at IS NULL
                """, (self.user_id,))
                next_position = cursor.fetchone()[0]
                
                cursor.execute("""
                    INSERT INTO habit_columns (user_id, name, type, position, scale_max, remote_id, version, is_synced)
                    VALUES (?, ?, ?, ?, ?, ?, 1, ?)
                """, (self.user_id, name, habit_type, next_position, scale_max, column_id, is_synced))
                
                local_id = cursor.lastrowid
            
            conn.commit()
            
            # Dodaj do sync queue TYLKO jeśli to lokalna zmiana (is_synced = 0)
            if is_synced == 0 and not existing:  # Nowa kolumna lokalna
                self.add_to_sync_queue('habit_column', column_id, 'create')
            
            return local_id
    
    def save_habit_record(self, column_id: str, record_date: date, value: str, 
                         notes: str = '', is_synced: int = 1):
        """
        Zapisz rekord z sync metadata
        
        Args:
            column_id: UUID kolumny
            record_date: Data rekordu
            value: Wartość
            notes: Notatki
            is_synced: Czy dane pochodzą z serwera (1) czy lokalne (0), domyślnie 1
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Znajdź local habit_id na podstawie remote_id kolumny
            cursor.execute("""
                SELECT id FROM habit_columns 
                WHERE (id = ? OR remote_id = ?) AND user_id = ? AND deleted_at IS NULL
            """, (column_id, column_id, self.user_id))
            
            column_row = cursor.fetchone()
            if not column_row:
                logger.error(f"[HABIT SYNC] Column {column_id} not found")
                return None
            
            local_habit_id = column_row[0]
            date_str = record_date.isoformat()
            
            # Sprawdź czy rekord już istnieje
            cursor.execute("""
                SELECT id, remote_id FROM habit_records 
                WHERE habit_id = ? AND date = ? AND user_id = ?
            """, (local_habit_id, date_str, self.user_id))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update istniejącego rekordu - zachowaj is_synced z parametru
                cursor.execute("""
                    UPDATE habit_records 
                    SET value = ?, is_synced = ?, updated_at = CURRENT_TIMESTAMP, version = version + 1
                    WHERE id = ?
                """, (value, is_synced, existing[0]))
                
                record_id = existing[1] or str(existing[0])
                action = 'update'
            else:
                # Wstaw nowy rekord
                remote_id = str(uuid.uuid4())
                
                cursor.execute("""
                    INSERT INTO habit_records (user_id, habit_id, date, value, remote_id, version, is_synced)
                    VALUES (?, ?, ?, ?, ?, 1, ?)
                """, (self.user_id, local_habit_id, date_str, value, remote_id, is_synced))
                
                record_id = remote_id
                action = 'create'
            
            conn.commit()
            
            # Dodaj do sync queue TYLKO jeśli to lokalna zmiana (is_synced = 0)
            if is_synced == 0:
                self.add_to_sync_queue('habit_record', record_id, action)
            
            return record_id
            
            return record_id
    
    # =========================================================================
    # CLEANUP METHODS
    # =========================================================================
    
    def cleanup_deleted_columns(self, cutoff_date: datetime) -> int:
        """Usuń stare soft-deleted kolumny"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                DELETE FROM habit_columns 
                WHERE user_id = ? AND deleted_at IS NOT NULL AND deleted_at < ?
            """, (self.user_id, cutoff_date.isoformat()))
            
            count = cursor.rowcount
            conn.commit()
            return count
    
    def cleanup_deleted_records(self, cutoff_date: datetime) -> int:
        """Usuń stare rekordy (habit tracker nie używa soft delete dla rekordów)"""
        # W habit trackerze rekordy nie mają deleted_at, więc nie ma nic do czyszczenia
        return 0

    def close(self):
        """Zamyka połączenie z bazą danych"""
        logger.info(f"[HABIT DB] Database connection closed for user {self.user_id}")
