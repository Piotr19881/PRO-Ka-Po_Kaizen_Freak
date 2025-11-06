"""
Task Local Database - zarządzanie lokalną bazą danych zadań
Obsługuje zadania, podzadania, konfigurowalne kolumny, tagi i listy własne
"""
import sqlite3
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from loguru import logger


class TaskLocalDatabase:
    """Manager lokalnej bazy danych SQLite dla modułu zadań"""
    
    def __init__(self, db_path: Path, user_id: int = 1):
        """
        Inicjalizacja bazy danych zadań
        
        Args:
            db_path: Ścieżka do pliku bazy danych
            user_id: ID użytkownika (dla wieloużytkownikowego środowiska)
        """
        self.db_path = db_path
        self.user_id = user_id
        self._init_database()
        logger.info(f"[TASK DB] Initialized for user {user_id} at {db_path}")
    
    def _init_database(self):
        """Inicjalizacja struktury bazy danych"""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # ========== TABELA: task_columns_config ==========
            # Przechowuje konfigurację kolumn (systemowych i użytkownika)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_columns_config (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    column_id TEXT NOT NULL,
                    position INTEGER NOT NULL,
                    type TEXT NOT NULL,
                    visible_main BOOLEAN DEFAULT 1,
                    visible_bar BOOLEAN DEFAULT 0,
                    default_value TEXT,
                    list_name TEXT,
                    is_system BOOLEAN DEFAULT 0,
                    editable BOOLEAN DEFAULT 1,
                    allow_edit TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, column_id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_columns_user 
                ON task_columns_config(user_id, position)
            """)
            
            # ========== TABELA: task_tags ==========
            # Przechowuje tagi zadań
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    color TEXT DEFAULT '#CCCCCC',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP,
                    UNIQUE(user_id, name)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tags_user 
                ON task_tags(user_id, deleted_at)
            """)
            
            # Dodaj kolumny synchronizacji do task_tags
            cursor.execute("PRAGMA table_info(task_tags)")
            tag_columns = [row[1] for row in cursor.fetchall()]
            
            if 'version' not in tag_columns:
                cursor.execute("ALTER TABLE task_tags ADD COLUMN version INTEGER DEFAULT 1")
                logger.info("[TASK DB] Added 'version' column to task_tags table")
            
            if 'synced_at' not in tag_columns:
                cursor.execute("ALTER TABLE task_tags ADD COLUMN synced_at TIMESTAMP")
                logger.info("[TASK DB] Added 'synced_at' column to task_tags table")
            
            if 'server_uuid' not in tag_columns:
                cursor.execute("ALTER TABLE task_tags ADD COLUMN server_uuid TEXT")
                logger.info("[TASK DB] Added 'server_uuid' column to task_tags table")
            
            # ========== TABELA: task_custom_lists ==========
            # Przechowuje listy własne użytkownika
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_custom_lists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    list_values TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP,
                    UNIQUE(user_id, name)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_lists_user 
                ON task_custom_lists(user_id, deleted_at)
            """)
            
            # Dodaj kolumny synchronizacji do task_custom_lists
            cursor.execute("PRAGMA table_info(task_custom_lists)")
            list_columns = [row[1] for row in cursor.fetchall()]
            
            if 'version' not in list_columns:
                cursor.execute("ALTER TABLE task_custom_lists ADD COLUMN version INTEGER DEFAULT 1")
                logger.info("[TASK DB] Added 'version' column to task_custom_lists table")
            
            if 'synced_at' not in list_columns:
                cursor.execute("ALTER TABLE task_custom_lists ADD COLUMN synced_at TIMESTAMP")
                logger.info("[TASK DB] Added 'synced_at' column to task_custom_lists table")
            
            if 'server_uuid' not in list_columns:
                cursor.execute("ALTER TABLE task_custom_lists ADD COLUMN server_uuid TEXT")
                logger.info("[TASK DB] Added 'server_uuid' column to task_custom_lists table")
            
            # ========== TABELA: tasks ==========
            # Główna tabela zadań
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    parent_id INTEGER,
                    position INTEGER DEFAULT 0,
                    title TEXT NOT NULL,
                    status BOOLEAN DEFAULT 0,
                    completion_date TIMESTAMP,
                    archived BOOLEAN DEFAULT 0,
                    archived_at TIMESTAMP,
                    note_id INTEGER,
                    kanban_id INTEGER,
                    alarm_date TIMESTAMP,
                    custom_data TEXT,
                    row_color TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    deleted_at TIMESTAMP,
                    synced BOOLEAN DEFAULT 0,
                    server_id INTEGER,
                    FOREIGN KEY (parent_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_user 
                ON tasks(user_id, deleted_at, archived)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_parent 
                ON tasks(parent_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tasks_position 
                ON tasks(user_id, position)
            """)

            # Upewnij się, że kolumna row_color istnieje (dla starszych baz)
            cursor.execute("PRAGMA table_info(tasks)")
            task_columns = [row[1] for row in cursor.fetchall()]
            if 'row_color' not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN row_color TEXT")
                logger.info("[TASK DB] Added missing column 'row_color' to tasks table")
            
            # Dodaj kolumny dla synchronizacji z serwerem (jeśli nie istnieją)
            cursor.execute("PRAGMA table_info(tasks)")
            task_columns = [row[1] for row in cursor.fetchall()]
            
            if 'version' not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN version INTEGER DEFAULT 1")
                logger.info("[TASK DB] Added 'version' column to tasks table")
            
            if 'synced_at' not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN synced_at TIMESTAMP")
                logger.info("[TASK DB] Added 'synced_at' column to tasks table")
            
            if 'server_uuid' not in task_columns:
                cursor.execute("ALTER TABLE tasks ADD COLUMN server_uuid TEXT")
                logger.info("[TASK DB] Added 'server_uuid' column to tasks table")
            
            # ========== TABELA: task_tag_assignments ==========
            # Przypisanie tagów do zadań (relacja many-to-many)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_tag_assignments (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES task_tags(id) ON DELETE CASCADE,
                    UNIQUE(task_id, tag_id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tag_assignments 
                ON task_tag_assignments(task_id, tag_id)
            """)
            
            # ========== TABELA: kanban_items ==========
            # Zadania w widoku KanBan z ich pozycją i statusem
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kanban_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    task_id INTEGER NOT NULL,
                    column_type TEXT NOT NULL,
                    position INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE,
                    UNIQUE(user_id, task_id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kanban_user_column 
                ON kanban_items(user_id, column_type, position)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_kanban_task 
                ON kanban_items(task_id)
            """)
            
            # Dodaj kolumny synchronizacji do kanban_items
            cursor.execute("PRAGMA table_info(kanban_items)")
            kanban_columns = [row[1] for row in cursor.fetchall()]
            
            if 'version' not in kanban_columns:
                cursor.execute("ALTER TABLE kanban_items ADD COLUMN version INTEGER DEFAULT 1")
                logger.info("[TASK DB] Added 'version' column to kanban_items table")
            
            if 'synced_at' not in kanban_columns:
                cursor.execute("ALTER TABLE kanban_items ADD COLUMN synced_at TIMESTAMP")
                logger.info("[TASK DB] Added 'synced_at' column to kanban_items table")
            
            if 'server_uuid' not in kanban_columns:
                cursor.execute("ALTER TABLE kanban_items ADD COLUMN server_uuid TEXT")
                logger.info("[TASK DB] Added 'server_uuid' column to kanban_items table")
            
            if 'deleted_at' not in kanban_columns:
                cursor.execute("ALTER TABLE kanban_items ADD COLUMN deleted_at TIMESTAMP")
                logger.info("[TASK DB] Added 'deleted_at' column to kanban_items table")
            
            # ========== TABELA: kanban_settings ==========
            # Ustawienia widoku KanBan dla użytkownika
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS kanban_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL UNIQUE,
                    max_in_progress INTEGER DEFAULT 3,
                    hide_completed_after INTEGER DEFAULT 0,
                    show_on_hold BOOLEAN DEFAULT 0,
                    show_review BOOLEAN DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ========== TABELA: task_history ==========
            # Historia zmian zadań (audyt) - szczególnie przesunięć w Kanban
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    task_id INTEGER NOT NULL,
                    action_type TEXT NOT NULL,
                    old_value TEXT,
                    new_value TEXT,
                    details TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_history_task 
                ON task_history(task_id, created_at DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_history_user 
                ON task_history(user_id, created_at DESC)
            """)
            
            # ========== TABELA: task_alarms ==========
            # Metadane alarmów dla zadań (dla cyklicznych i zaawansowanych opcji)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_alarms (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id INTEGER NOT NULL UNIQUE,
                    alarm_time TIMESTAMP NOT NULL,
                    is_recurring BOOLEAN DEFAULT 0,
                    interval_minutes INTEGER,
                    end_date TIMESTAMP,
                    play_sound BOOLEAN DEFAULT 1,
                    show_popup BOOLEAN DEFAULT 1,
                    label TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE CASCADE
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_alarms_task 
                ON task_alarms(task_id)
            """)
            
            # ========== TABELA: task_settings ==========
            # Ustawienia modułu zadań
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_settings (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, key)
                )
            """)
            
            # ========== TABELA: sync_queue ==========
            # Kolejka synchronizacji z serwerem
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    local_id INTEGER,
                    action TEXT NOT NULL,
                    data TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    
                    CHECK (entity_type IN ('task', 'tag', 'kanban_item', 'custom_list')),
                    CHECK (action IN ('upsert', 'delete'))
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_queue_entity 
                ON sync_queue(entity_type, entity_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_queue_created 
                ON sync_queue(created_at ASC)
            """)
            
            conn.commit()
            logger.info("[TASK DB] Database schema initialized")
            
        # Dodaj domyślne kolumny jeśli brak konfiguracji
        self._ensure_default_columns()
        
        # Dodaj przykładowe zadania jeśli baza jest pusta
        self._ensure_sample_data()

    @staticmethod
    def _now_iso() -> str:
        """Return current UTC timestamp as ISO string without microseconds."""
        return datetime.utcnow().replace(microsecond=0).isoformat()

    def _ensure_task_custom_fields(
        self,
        cursor: sqlite3.Cursor,
        task_id: int,
        fields: Dict[str, Any],
        *,
        overwrite: bool = False,
    ) -> bool:
        """Merge selected values into task custom_data column."""
        if not fields:
            return False

        cursor.execute(
            """
            SELECT custom_data FROM tasks
            WHERE user_id = ? AND id = ?
            """,
            (self.user_id, task_id),
        )
        row = cursor.fetchone()

        current: Dict[str, Any] = {}
        if row and row[0]:
            try:
                current = json.loads(row[0]) or {}
            except json.JSONDecodeError:
                current = {}

        changed = False
        for key, value in fields.items():
            if overwrite or key not in current or current.get(key) in (None, ""):
                current[key] = value
                changed = True

        if not changed:
            return False

        cursor.execute(
            """
            UPDATE tasks
            SET custom_data = ?, updated_at = CURRENT_TIMESTAMP
            WHERE user_id = ? AND id = ?
            """,
            (json.dumps(current), self.user_id, task_id),
        )
        return True
    
    def _ensure_sample_data(self):
        """Dodaj przykładowe dane jeśli baza jest pusta"""
        try:
            self.create_sample_tasks()
        except Exception as e:
            logger.warning(f"[TASK DB] Could not create sample data: {e}")
    
    def _ensure_default_columns(self):
        """Dodaj domyślne kolumny systemowe jeśli tabela jest pusta"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Sprawdź czy istnieją już kolumny dla użytkownika
                cursor.execute("""
                    SELECT COUNT(*) FROM task_columns_config WHERE user_id = ?
                """, (self.user_id,))
                
                count = cursor.fetchone()[0]
                
                if count == 0:
                    # Brak kolumn - dodaj wszystkie kolumny systemowe
                    default_columns = [
                        {
                            'id': 'id',
                            'position': 0,
                            'type': 'int',
                            'visible_main': False,
                            'visible_bar': False,
                            'default_value': '',
                            'list_name': '',
                            'system': True,
                            'editable': False,
                            'allow_edit': []
                        },
                        {
                            'id': 'position',
                            'position': 1,
                            'type': 'int',
                            'visible_main': False,
                            'visible_bar': False,
                            'default_value': '',
                            'list_name': '',
                            'system': True,
                            'editable': False,
                            'allow_edit': []
                        },
                        {
                            'id': 'Data dodania',
                            'position': 2,
                            'type': 'data',
                            'visible_main': True,
                            'visible_bar': False,
                            'default_value': 'today',
                            'list_name': '',
                            'system': True,
                            'editable': True,
                            'allow_edit': ['visible_main']  # Brak 'visible_bar' - zablokowane
                        },
                        {
                            'id': 'Subtaski',
                            'position': 3,
                            'type': 'button',
                            'visible_main': True,
                            'visible_bar': False,  # Nigdy nie pokazuj w pasku dolnym
                            'default_value': '',
                            'list_name': '',
                            'system': True,
                            'editable': False,  # Nie można edytować w ogóle
                            'allow_edit': []  # Zablokowana pozycja i widoczność
                        },
                        {
                            'id': 'Zadanie',
                            'position': 4,
                            'type': 'text',
                            'visible_main': True,
                            'visible_bar': True,
                            'default_value': '',
                            'list_name': '',
                            'system': True,
                            'editable': False,
                            'allow_edit': []  # Zawsze widoczny
                        },
                        {
                            'id': 'Status',
                            'position': 5,
                            'type': 'checkbox',
                            'visible_main': True,
                            'visible_bar': False,
                            'default_value': 'false',
                            'list_name': '',
                            'system': True,
                            'editable': True,
                            'allow_edit': ['visible_main', 'position']
                        },
                        {
                            'id': 'data realizacji',
                            'position': 6,
                            'type': 'data',
                            'visible_main': True,
                            'visible_bar': False,
                            'default_value': '',
                            'list_name': '',
                            'system': True,
                            'editable': True,
                            'allow_edit': ['visible_main', 'position']
                        },
                        {
                            'id': 'KanBan',
                            'position': 7,
                            'type': 'button',
                            'visible_main': True,
                            'visible_bar': True,
                            'default_value': '',
                            'list_name': '',
                            'system': True,
                            'editable': False,  # Zawsze widoczny
                            'allow_edit': []  # Brak edycji visible_main i visible_bar
                        },
                        {
                            'id': 'Notatka',
                            'position': 8,
                            'type': 'button',
                            'visible_main': True,
                            'visible_bar': False,
                            'default_value': '',
                            'list_name': '',
                            'system': True,
                            'editable': False,  # Zawsze widoczna
                            'allow_edit': []  # Brak edycji visible_main
                        },
                        {
                            'id': 'Archiwum',
                            'position': 9,
                            'type': 'boolean',
                            'visible_main': False,
                            'visible_bar': False,
                            'default_value': 'false',
                            'list_name': '',
                            'system': True,
                            'editable': False,
                            'allow_edit': []
                        },
                        {
                            'id': 'Tag',
                            'position': 10,
                            'type': 'lista',
                            'visible_main': True,
                            'visible_bar': True,
                            'default_value': '',
                            'list_name': 'tags',
                            'system': True,
                            'editable': True,
                            'allow_edit': ['visible_main', 'visible_bar', 'position']  # Możliwość edycji visible_bar
                        },
                        {
                            'id': 'Alarm',
                            'position': 11,
                            'type': 'data',
                            'visible_main': True,
                            'visible_bar': True,
                            'default_value': '',
                            'list_name': '',
                            'system': True,
                            'editable': True,
                            'allow_edit': ['visible_main', 'visible_bar', 'position']
                        }
                    ]
                    
                    for col in default_columns:
                        cursor.execute("""
                            INSERT INTO task_columns_config (
                                user_id, column_id, position, type, 
                                visible_main, visible_bar, default_value, 
                                list_name, is_system, editable, allow_edit
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            self.user_id,
                            col['id'],
                            col['position'],
                            col['type'],
                            col['visible_main'],
                            col['visible_bar'],
                            col.get('default_value', ''),
                            col.get('list_name', ''),
                            col['system'],
                            col['editable'],
                            json.dumps(col.get('allow_edit', []))
                        ))
                    
                    conn.commit()
                    logger.info(f"[TASK DB] Added {len(default_columns)} default columns for user {self.user_id}")
                else:
                    # Sprawdź czy istnieją wszystkie kolumny systemowe i dodaj brakujące
                    cursor.execute("""
                        SELECT column_id FROM task_columns_config WHERE user_id = ?
                    """, (self.user_id,))
                    
                    existing_columns = {row[0] for row in cursor.fetchall()}
                    all_system_columns = {'id', 'position', 'Data dodania', 'Subtaski', 'Zadanie', 'Status', 
                                        'data realizacji', 'KanBan', 'Notatka', 'Archiwum', 'Tag', 'Alarm'}
                    
                    missing_columns = all_system_columns - existing_columns
                    
                    if missing_columns:
                        logger.info(f"[TASK DB] Found {len(missing_columns)} missing system columns: {missing_columns}")
                        
                        # Definicje brakujących kolumn - ZGODNE Z WYMAGANIAMI
                        system_column_defs = {
                            'id': {'position': 0, 'type': 'int', 'visible_main': False, 'visible_bar': False, 
                                  'default_value': '', 'editable': False, 'allow_edit': []},
                            'position': {'position': 1, 'type': 'int', 'visible_main': False, 'visible_bar': False,
                                       'default_value': '', 'editable': False, 'allow_edit': []},
                            'Subtaski': {'position': 3, 'type': 'button', 'visible_main': True, 'visible_bar': False,
                                        'default_value': '', 'editable': False, 'allow_edit': []},  # Po lewej stronie
                            'Zadanie': {'position': 4, 'type': 'text', 'visible_main': True, 'visible_bar': True,
                                       'default_value': '', 'editable': False, 'allow_edit': []},  # Po prawej od Subtaski
                            'KanBan': {'position': 7, 'type': 'button', 'visible_main': True, 'visible_bar': True,
                                      'default_value': '', 'editable': False, 'allow_edit': []},  # Zawsze widoczny
                            'Notatka': {'position': 8, 'type': 'button', 'visible_main': True, 'visible_bar': False,
                                       'default_value': '', 'editable': False, 'allow_edit': []},  # Zawsze widoczna
                            'Archiwum': {'position': 9, 'type': 'boolean', 'visible_main': False, 'visible_bar': False,
                                        'default_value': 'false', 'editable': False, 'allow_edit': []},
                            'Alarm': {'position': 11, 'type': 'data', 'visible_main': True, 'visible_bar': True,
                                     'default_value': '', 'editable': True, 'allow_edit': ['visible_main', 'visible_bar', 'position']}
                        }
                        
                        for col_id in missing_columns:
                            if col_id in system_column_defs:
                                col_def = system_column_defs[col_id]
                                cursor.execute("""
                                    INSERT INTO task_columns_config (
                                        user_id, column_id, position, type, 
                                        visible_main, visible_bar, default_value, 
                                        list_name, is_system, editable, allow_edit
                                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                                """, (
                                    self.user_id,
                                    col_id,
                                    col_def['position'],
                                    col_def['type'],
                                    col_def['visible_main'],
                                    col_def['visible_bar'],
                                    col_def.get('default_value', ''),
                                    '',  # list_name
                                    True,  # is_system
                                    col_def['editable'],
                                    json.dumps(col_def.get('allow_edit', []))
                                ))
                        
                        conn.commit()
                        logger.info(f"[TASK DB] Added {len(missing_columns)} missing system columns for user {self.user_id}")
                    
                    # Napraw stare rekordy z numerycznymi column_id
                    # Stare kolumny miały ID jako numery z bazy danych (6,7,8,9,10)
                    # Musimy je zmapować na prawidłowe nazwy
                    cursor.execute("""
                        SELECT id, column_id, type, position FROM task_columns_config 
                        WHERE user_id = ? AND is_system = 0
                    """, (self.user_id,))
                    
                    old_columns = cursor.fetchall()
                    
                    # Mapa: (type, position_approx) -> (prawdziwa_nazwa, nowa_pozycja)
                    # Bazujemy na typie i pozycji, żeby znaleźć prawidłową nazwę i pozycję
                    column_mapping = {
                        ('data', 0): ('Data dodania', 2),    # type data, old pos 0 -> Data dodania, position 2
                        ('checkbox', 1): ('Status', 4),       # type checkbox, old pos 1 -> Status, position 4
                        ('text', 2): ('Zadanie', 3),         # type text, old pos 2 -> Zadanie, position 3
                        ('data', 3): ('data realizacji', 5), # type data, old pos 3 -> data realizacji, position 5
                        ('text', 4): ('Tag', 9),             # type text, old pos 4 -> Tag, position 9
                    }
                    
                    updates_made = 0
                    for row in old_columns:
                        row_id, column_id, col_type, col_position = row
                        
                        # Jeśli column_id jest liczbą (string zawierający tylko cyfry)
                        if column_id and column_id.isdigit():
                            # Znajdź prawidłową nazwę i pozycję na podstawie typu i starej pozycji
                            mapping = column_mapping.get((col_type, col_position))
                            
                            if mapping:
                                correct_name, correct_position = mapping
                                cursor.execute("""
                                    UPDATE task_columns_config 
                                    SET column_id = ?, is_system = 1, position = ?
                                    WHERE id = ?
                                """, (correct_name, correct_position, row_id))
                                updates_made += 1
                                logger.info(f"[TASK DB] Fixed column: {column_id} -> {correct_name} (type={col_type}, old_pos={col_position}, new_pos={correct_position})")
                    
                    if updates_made > 0:
                        conn.commit()
                        logger.info(f"[TASK DB] Fixed {updates_made} old columns with numeric IDs")
                    
                    # Zaktualizuj allow_edit dla systemowych kolumn zgodnie z wymaganiami
                    column_edit_rules = {
                        'Data dodania': ['visible_main'],  # Brak visible_bar
                        'Zadanie': [],  # Zawsze widoczny
                        'Status': ['visible_main', 'visible_bar', 'position'],
                        'data realizacji': ['visible_main', 'visible_bar', 'position'],
                        'KanBan': [],  # Zawsze widoczny, brak edycji
                        'Notatka': [],  # Zawsze widoczna, brak edycji
                        'Archiwum': [],
                        'Tag': ['visible_main', 'visible_bar', 'position'],
                        'Alarm': ['visible_main', 'visible_bar', 'position'],
                        'id': [],
                        'position': []
                    }
                    
                    updates_made = 0
                    for column_name, allow_edit in column_edit_rules.items():
                        cursor.execute("""
                            UPDATE task_columns_config 
                            SET allow_edit = ?, editable = ?
                            WHERE user_id = ? AND column_id = ?
                        """, (
                            json.dumps(allow_edit),
                            1 if len(allow_edit) > 0 else 0,
                            self.user_id,
                            column_name
                        ))
                        if cursor.rowcount > 0:
                            updates_made += 1
                    
                    if updates_made > 0:
                        conn.commit()
                        logger.info(f"[TASK DB] Updated allow_edit for {updates_made} system columns")
                    
        except Exception as e:
            logger.error(f"[TASK DB] Failed to ensure default columns: {e}")
    
    # ==================== ZARZĄDZANIE KONFIGURACJĄ KOLUMN ====================
    
    def save_columns_config(self, columns: List[Dict[str, Any]]) -> bool:
        """
        Zapisz konfigurację kolumn
        
        Args:
            columns: Lista słowników z konfiguracją kolumn
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # DIAGNOSTIC: Log user_id używany do zapisu
                logger.info(f"[TASK DB] Saving {len(columns)} columns config for user_id={self.user_id}")
                
                # Usuń istniejącą konfigurację użytkownika
                cursor.execute("""
                    DELETE FROM task_columns_config WHERE user_id = ?
                """, (self.user_id,))
                
                # Wstaw nową konfigurację
                for col in columns:
                    cursor.execute("""
                        INSERT INTO task_columns_config (
                            user_id, column_id, position, type, 
                            visible_main, visible_bar, default_value, 
                            list_name, is_system, editable, allow_edit
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        self.user_id,
                        col.get('id'),
                        col.get('position'),
                        col.get('type'),
                        col.get('visible_main', True),
                        col.get('visible_bar', False),
                        col.get('default_value', ''),
                        col.get('list_name', ''),
                        col.get('system', False),
                        col.get('editable', True),
                        json.dumps(col.get('allow_edit', []))
                    ))
                
                conn.commit()
                logger.info(f"[TASK DB] Saved {len(columns)} column configurations")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to save columns config: {e}")
            return False
    
    def load_columns_config(self) -> List[Dict[str, Any]]:
        """
        Wczytaj konfigurację kolumn
        
        Returns:
            Lista słowników z konfiguracją kolumn
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # DIAGNOSTIC: Log user_id używany do odczytu
                logger.info(f"[TASK DB] Loading columns config for user_id={self.user_id}")
                
                cursor.execute("""
                    SELECT * FROM task_columns_config 
                    WHERE user_id = ?
                    ORDER BY position
                """, (self.user_id,))
                
                columns = []
                for row in cursor.fetchall():
                    col = dict(row)
                    
                    # WAŻNE: Najpierw zapisz ID z bazy (auto-increment) pod inną nazwą
                    db_id = col.get('id')  # To jest auto-increment ID z bazy
                    
                    # Zamień column_id na id dla kompatybilności z dialogiem
                    if 'column_id' in col and col['column_id']:
                        col['id'] = col['column_id']
                        col['name'] = col['column_id']  # Dodaj pole name dla wyświetlania
                    else:
                        # Jeśli brak column_id, użyj db_id jako fallback (nie powinno się zdarzyć)
                        logger.warning(f"[TASK DB] Column without column_id found, db_id={db_id}")
                        col['id'] = f"column_{db_id}"
                        col['name'] = f"column_{db_id}"
                    
                    # Zamień is_system na system dla kompatybilności
                    if 'is_system' in col:
                        col['system'] = col['is_system']
                    # Parsuj allow_edit z JSON
                    if col.get('allow_edit'):
                        try:
                            col['allow_edit'] = json.loads(col['allow_edit'])
                        except:
                            col['allow_edit'] = []
                    
                    logger.debug(f"[TASK DB] Loaded column: id='{col.get('id')}', name='{col.get('name')}', type='{col.get('type')}'")
                    columns.append(col)
                
                logger.info(f"[TASK DB] Loaded {len(columns)} column configurations")
                return columns
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to load columns config: {e}")
            return []
    
    # ==================== ZARZĄDZANIE TAGAMI ====================
    
    def add_tag(self, name: str, color: str = '#CCCCCC') -> Optional[int]:
        """
        Dodaj nowy tag
        
        Args:
            name: Nazwa tagu
            color: Kolor tagu (hex)
            
        Returns:
            ID nowego tagu lub None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO task_tags (user_id, name, color)
                    VALUES (?, ?, ?)
                """, (self.user_id, name, color))
                conn.commit()
                tag_id = cursor.lastrowid
                logger.info(f"[TASK DB] Added tag '{name}' with ID {tag_id}")
                return tag_id
                
        except sqlite3.IntegrityError:
            logger.warning(f"[TASK DB] Tag '{name}' already exists")
            return None
        except Exception as e:
            logger.error(f"[TASK DB] Failed to add tag: {e}")
            return None
    
    def get_tags(self) -> List[Dict[str, Any]]:
        """
        Pobierz wszystkie aktywne tagi użytkownika
        
        Returns:
            Lista słowników z tagami
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM task_tags 
                    WHERE user_id = ? AND deleted_at IS NULL
                    ORDER BY name
                """, (self.user_id,))
                
                tags = [dict(row) for row in cursor.fetchall()]
                logger.info(f"[TASK DB] Retrieved {len(tags)} tags")
                return tags
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to get tags: {e}")
            return []
    
    def update_tag(self, tag_id: int, name: str = None, color: str = None) -> bool:
        """
        Aktualizuj tag
        
        Args:
            tag_id: ID tagu
            name: Nowa nazwa (opcjonalne)
            color: Nowy kolor (opcjonalne)
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                if color is not None:
                    updates.append("color = ?")
                    params.append(color)
                
                if not updates:
                    return False
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.extend([self.user_id, tag_id])
                
                cursor.execute(f"""
                    UPDATE task_tags 
                    SET {', '.join(updates)}
                    WHERE user_id = ? AND id = ?
                """, params)
                
                conn.commit()
                logger.info(f"[TASK DB] Updated tag {tag_id}")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to update tag: {e}")
            return False
    
    def delete_tag(self, tag_id: int, soft_delete: bool = True) -> bool:
        """
        Usuń tag
        
        Args:
            tag_id: ID tagu
            soft_delete: Czy usunięcie miękkie (domyślnie True)
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if soft_delete:
                    cursor.execute("""
                        UPDATE task_tags 
                        SET deleted_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND id = ?
                    """, (self.user_id, tag_id))
                else:
                    cursor.execute("""
                        DELETE FROM task_tags 
                        WHERE user_id = ? AND id = ?
                    """, (self.user_id, tag_id))
                
                conn.commit()
                logger.info(f"[TASK DB] Deleted tag {tag_id} (soft={soft_delete})")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to delete tag: {e}")
            return False
    
    # ==================== ZARZĄDZANIE LISTAMI WŁASNYMI ====================
    
    def add_custom_list(self, name: str, values: List[str]) -> Optional[int]:
        """
        Dodaj nową listę własną
        
        Args:
            name: Nazwa listy
            values: Lista wartości
            
        Returns:
            ID nowej listy lub None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO task_custom_lists (user_id, name, list_values)
                    VALUES (?, ?, ?)
                """, (self.user_id, name, json.dumps(values)))
                conn.commit()
                list_id = cursor.lastrowid
                logger.info(f"[TASK DB] Added custom list '{name}' with ID {list_id}")
                return list_id
                
        except sqlite3.IntegrityError:
            logger.warning(f"[TASK DB] Custom list '{name}' already exists")
            return None
        except Exception as e:
            logger.error(f"[TASK DB] Failed to add custom list: {e}")
            return None
    
    def get_custom_lists(self) -> List[Dict[str, Any]]:
        """
        Pobierz wszystkie aktywne listy własne
        
        Returns:
            Lista słowników z listami
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM task_custom_lists 
                    WHERE user_id = ? AND deleted_at IS NULL
                    ORDER BY name
                """, (self.user_id,))
                
                lists = []
                for row in cursor.fetchall():
                    list_data = dict(row)
                    # Parsuj list_values z JSON i mapuj na 'values' dla kompatybilności
                    if 'list_values' in list_data and list_data['list_values']:
                        list_data['values'] = json.loads(list_data['list_values'])
                    elif 'values' in list_data and list_data['values']:
                        # Fallback dla starszej struktury
                        list_data['values'] = json.loads(list_data['values'])
                    else:
                        list_data['values'] = []
                    lists.append(list_data)
                
                logger.info(f"[TASK DB] Retrieved {len(lists)} custom lists")
                return lists
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to get custom lists: {e}")
            return []
    
    def update_custom_list(self, list_id: int, name: str = None, values: List[str] = None) -> bool:
        """
        Aktualizuj listę własną
        
        Args:
            list_id: ID listy
            name: Nowa nazwa (opcjonalne)
            values: Nowe wartości (opcjonalne)
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                updates = []
                params = []
                
                if name is not None:
                    updates.append("name = ?")
                    params.append(name)
                if values is not None:
                    updates.append("list_values = ?")
                    params.append(json.dumps(values))
                
                if not updates:
                    return False
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.extend([self.user_id, list_id])
                
                cursor.execute(f"""
                    UPDATE task_custom_lists 
                    SET {', '.join(updates)}
                    WHERE user_id = ? AND id = ?
                """, params)
                
                conn.commit()
                logger.info(f"[TASK DB] Updated custom list {list_id}")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to update custom list: {e}")
            return False
    
    # ==================== ZARZĄDZANIE ZADANIAMI ====================
    
    def add_task(self, title: str, parent_id: int = None, custom_data: Dict[str, Any] = None, 
                 tags: List[int] = None, **kwargs) -> Optional[int]:
        """
        Dodaj nowe zadanie
        
        Args:
            title: Tytuł zadania
            parent_id: ID zadania nadrzędnego (dla podzadań)
            custom_data: Dane niestandardowych kolumn jako słownik
            tags: Lista ID tagów do przypisania
            **kwargs: Dodatkowe pola (status, alarm_date, etc.)
            
        Returns:
            ID nowego zadania lub None
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Pobierz maksymalną pozycję
                cursor.execute("""
                    SELECT COALESCE(MAX(position), 0) + 1 
                    FROM tasks 
                    WHERE user_id = ? AND parent_id IS ?
                """, (self.user_id, parent_id))
                position = cursor.fetchone()[0]
                
                # Wstaw zadanie
                cursor.execute("""
                    INSERT INTO tasks (
                        user_id, parent_id, position, title, status,
                        completion_date, note_id, kanban_id, alarm_date, custom_data,
                        row_color
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    self.user_id,
                    parent_id,
                    position,
                    title,
                    kwargs.get('status', False),
                    kwargs.get('completion_date'),
                    kwargs.get('note_id'),
                    kwargs.get('kanban_id'),
                    kwargs.get('alarm_date'),
                    json.dumps(custom_data) if custom_data else None,
                    kwargs.get('row_color')
                ))
                
                task_id = cursor.lastrowid
                
                # Przypisz tagi
                if tags:
                    for tag_id in tags:
                        cursor.execute("""
                            INSERT INTO task_tag_assignments (task_id, tag_id)
                            VALUES (?, ?)
                        """, (task_id, tag_id))
                
                conn.commit()
                logger.info(f"[TASK DB] Added task '{title}' with ID {task_id}")
                return task_id
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to add task: {e}")
            return None
    
    def get_tasks(self, parent_id: int = None, include_archived: bool = False,
                  include_subtasks: bool = True) -> List[Dict[str, Any]]:
        """
        Pobierz zadania
        
        Args:
            parent_id: ID zadania nadrzędnego (None = główne zadania)
            include_archived: Czy uwzględnić zarchiwizowane
            include_subtasks: Czy dołączyć podzadania
            
        Returns:
            Lista słowników z zadaniami
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                # Buduj query
                query = """
                    SELECT * FROM tasks 
                    WHERE user_id = ? AND deleted_at IS NULL
                """
                params = [self.user_id]
                
                if parent_id is None:
                    query += " AND parent_id IS NULL"
                else:
                    query += " AND parent_id = ?"
                    params.append(parent_id)
                
                if not include_archived:
                    query += " AND archived = 0"
                
                query += " ORDER BY position, created_at DESC"
                
                cursor.execute(query, params)
                
                tasks = []
                for row in cursor.fetchall():
                    task = dict(row)
                    
                    # Parsuj custom_data z JSON
                    if task.get('custom_data'):
                        task['custom_data'] = json.loads(task['custom_data'])
                    
                    # Pobierz tagi
                    cursor.execute("""
                        SELECT tt.* FROM task_tags tt
                        JOIN task_tag_assignments tta ON tt.id = tta.tag_id
                        WHERE tta.task_id = ?
                    """, (task['id'],))
                    task['tags'] = [dict(tag_row) for tag_row in cursor.fetchall()]
                    
                    # Pobierz podzadania rekurencyjnie
                    if include_subtasks:
                        task['subtasks'] = self.get_tasks(
                            parent_id=task['id'],
                            include_archived=include_archived,
                            include_subtasks=True
                        )
                    
                    tasks.append(task)
                
                logger.info(f"[TASK DB] Retrieved {len(tasks)} tasks")
                return tasks
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to get tasks: {e}")
            return []
    
    def get_task_by_id(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Pobierz zadanie po ID
        
        Args:
            task_id: ID zadania
            
        Returns:
            Słownik z danymi zadania lub None jeśli nie znaleziono
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM tasks 
                    WHERE id = ? AND user_id = ? AND deleted_at IS NULL
                """, (task_id, self.user_id))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                task = dict(row)
                
                # Parsuj custom_data z JSON
                if task.get('custom_data'):
                    task['custom_data'] = json.loads(task['custom_data'])
                
                # Pobierz tagi
                cursor.execute("""
                    SELECT tt.* FROM task_tags tt
                    JOIN task_tag_assignments tta ON tt.id = tta.tag_id
                    WHERE tta.task_id = ?
                """, (task_id,))
                task['tags'] = [dict(tag_row) for tag_row in cursor.fetchall()]
                
                return task
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to get task by id {task_id}: {e}")
            return None
    
    def update_task(self, task_id: int, **kwargs) -> bool:
        """
        Aktualizuj zadanie
        
        Args:
            task_id: ID zadania
            **kwargs: Pola do aktualizacji
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                allowed_fields = [
                    'title', 'status', 'completion_date', 'position',
                    'note_id', 'kanban_id', 'alarm_date', 'custom_data', 'archived',
                    'row_color'
                ]
                
                updates = []
                params = []
                
                for key, value in kwargs.items():
                    if key in allowed_fields:
                        updates.append(f"{key} = ?")
                        # Serializuj custom_data do JSON
                        if key == 'custom_data' and isinstance(value, dict):
                            value = json.dumps(value)
                        params.append(value)
                
                if not updates:
                    return False
                
                # Automatyczne wypełnianie completion_date przy zaznaczeniu status
                if 'status' in kwargs and kwargs['status'] and 'completion_date' not in kwargs:
                    updates.append("completion_date = CURRENT_TIMESTAMP")

                if 'archived' in kwargs:
                    if kwargs['archived']:
                        updates.append("archived_at = CURRENT_TIMESTAMP")
                    else:
                        updates.append("archived_at = NULL")
                
                updates.append("updated_at = CURRENT_TIMESTAMP")
                params.extend([self.user_id, task_id])
                
                cursor.execute(f"""
                    UPDATE tasks 
                    SET {', '.join(updates)}
                    WHERE user_id = ? AND id = ?
                """, params)
                
                conn.commit()
                logger.info(f"[TASK DB] Updated task {task_id}")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to update task: {e}")
            return False
    
    def delete_task(self, task_id: int, soft_delete: bool = True) -> bool:
        """
        Usuń zadanie (i wszystkie podzadania)
        
        Args:
            task_id: ID zadania
            soft_delete: Czy usunięcie miękkie (domyślnie True)
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                if soft_delete:
                    # Miękkie usunięcie zadania i podzadań
                    cursor.execute("""
                        WITH RECURSIVE subtasks AS (
                            SELECT id FROM tasks WHERE id = ?
                            UNION ALL
                            SELECT t.id FROM tasks t
                            JOIN subtasks s ON t.parent_id = s.id
                        )
                        UPDATE tasks 
                        SET deleted_at = CURRENT_TIMESTAMP
                        WHERE id IN (SELECT id FROM subtasks) AND user_id = ?
                    """, (task_id, self.user_id))
                else:
                    # Twarde usunięcie (CASCADE usunie podzadania)
                    cursor.execute("""
                        DELETE FROM tasks 
                        WHERE user_id = ? AND id = ?
                    """, (self.user_id, task_id))
                
                conn.commit()
                logger.info(f"[TASK DB] Deleted task {task_id} (soft={soft_delete})")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to delete task: {e}")
            return False
    
    # ==================== ZARZĄDZANIE USTAWIENIAMI ====================
    
    def save_setting(self, key: str, value: Any) -> bool:
        """Zapisz ustawienie"""
        try:
            # DIAGNOSTIC: Log user_id używany do zapisu ustawienia
            logger.debug(f"[TASK DB] Saving setting '{key}' for user_id={self.user_id}")
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO task_settings (user_id, key, value, updated_at)
                    VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                """, (self.user_id, key, json.dumps(value)))
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"[TASK DB] Failed to save setting: {e}")
            return False
    
    def get_setting(self, key: str, default: Any = None) -> Any:
        """Pobierz ustawienie"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT value FROM task_settings 
                    WHERE user_id = ? AND key = ?
                """, (self.user_id, key))
                row = cursor.fetchone()
                if row:
                    logger.debug(f"[TASK DB] Got setting '{key}' for user_id={self.user_id}: found")
                    return json.loads(row[0])
                logger.debug(f"[TASK DB] Got setting '{key}' for user_id={self.user_id}: not found, using default")
                return default
        except Exception as e:
            logger.error(f"[TASK DB] Failed to get setting: {e}")
            return default

    def auto_archive_completed_tasks(self, older_than_days: int) -> int:
        """Zarchiwizuj automatycznie ukończone zadania starsze niż podany próg dni."""
        if older_than_days is None:
            return 0
        try:
            days = int(older_than_days)
        except (TypeError, ValueError):
            return 0
        if days <= 0:
            return 0

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    UPDATE tasks
                    SET archived = 1,
                        archived_at = CURRENT_TIMESTAMP,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ?
                        AND deleted_at IS NULL
                        AND archived = 0
                        AND status = 1
                        AND completion_date IS NOT NULL
                        AND completion_date <= datetime('now', ?)
                    """,
                    (self.user_id, f"-{days} days")
                )
                conn.commit()
                affected = cursor.rowcount or 0
                if affected:
                    logger.info(f"[TASK DB] Auto-archived {affected} tasks older than {days} days")
                return affected
        except Exception as exc:
            logger.error(f"[TASK DB] Failed to auto-archive tasks: {exc}")
            return 0

    # ==================== METODY POMOCNICZE DLA TASK CONFIG DIALOG ====================
    
    def load_tags(self) -> List[Dict[str, Any]]:
        """
        Alias dla get_tags() - kompatybilność z TaskConfigDialog
        
        Returns:
            Lista słowników z tagami
        """
        return self.get_tags()
    
    def save_tags(self, tags: List[Dict[str, Any]]) -> bool:
        """
        Zapisz kompletną listę tagów (usuwa stare i dodaje nowe)
        
        Args:
            tags: Lista słowników z tagami [{'name': str, 'color': str}, ...]
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Usuń wszystkie istniejące tagi użytkownika (soft delete)
                cursor.execute("""
                    UPDATE task_tags 
                    SET deleted_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (self.user_id,))
                
                # Dodaj nowe tagi
                for tag in tags:
                    cursor.execute("""
                        INSERT INTO task_tags (user_id, name, color)
                        VALUES (?, ?, ?)
                    """, (self.user_id, tag.get('name', ''), tag.get('color', '#CCCCCC')))
                
                conn.commit()
                logger.info(f"[TASK DB] Saved {len(tags)} tags")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to save tags: {e}")
            return False
    
    def load_custom_lists(self) -> List[Dict[str, Any]]:
        """
        Wczytaj wszystkie własne listy użytkownika
        
        Returns:
            Lista słowników [{'name': str, 'values': List[str]}, ...]
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM task_custom_lists 
                    WHERE user_id = ? AND deleted_at IS NULL
                    ORDER BY name
                """, (self.user_id,))
                
                lists = []
                for row in cursor.fetchall():
                    list_dict = dict(row)
                    # Parsuj list_values z JSON
                    if list_dict.get('list_values'):
                        list_dict['values'] = json.loads(list_dict['list_values'])
                    else:
                        list_dict['values'] = []
                    # Usuń klucz list_values z dict (zostaw tylko values)
                    list_dict.pop('list_values', None)
                    lists.append(list_dict)
                
                logger.info(f"[TASK DB] Loaded {len(lists)} custom lists")
                return lists
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to load custom lists: {e}")
            return []
    
    def save_custom_lists(self, lists: List[Dict[str, Any]]) -> bool:
        """
        Zapisz kompletną listę własnych list (usuwa stare i dodaje nowe)
        
        Args:
            lists: Lista słowników [{'name': str, 'values': List[str]}, ...]
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Usuń wszystkie istniejące listy użytkownika (soft delete)
                cursor.execute("""
                    UPDATE task_custom_lists 
                    SET deleted_at = CURRENT_TIMESTAMP 
                    WHERE user_id = ?
                """, (self.user_id,))
                
                # Dodaj nowe listy
                for custom_list in lists:
                    values_json = json.dumps(custom_list.get('values', []))
                    cursor.execute("""
                        INSERT INTO task_custom_lists (user_id, name, list_values)
                        VALUES (?, ?, ?)
                    """, (self.user_id, custom_list.get('name', ''), values_json))
                
                conn.commit()
                logger.info(f"[TASK DB] Saved {len(lists)} custom lists")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to save custom lists: {e}")
            return False
    
    def create_sample_tasks(self) -> bool:
        """
        Tworzy przykładowe zadania do testowania (jeśli baza jest pusta)
        
        Returns:
            True jeśli przykładowe dane zostały utworzone
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Sprawdź czy już istnieją zadania
                cursor.execute("""
                    SELECT COUNT(*) FROM tasks WHERE user_id = ? AND deleted_at IS NULL
                """, (self.user_id,))
                
                count = cursor.fetchone()[0]
                
                if count == 0:
                    # Dodaj przykładowe zadania
                    sample_tasks = [
                        {
                            'title': 'Pierwsze zadanie testowe',
                            'status': False,
                            'custom_data': {}
                        },
                        {
                            'title': 'Zadanie w trakcie realizacji',
                            'status': False,
                            'custom_data': {}
                        },
                        {
                            'title': 'Zadanie ukończone',
                            'status': True,
                            'completion_date': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                            'custom_data': {}
                        },
                        {
                            'title': 'Pilne zadanie do wykonania',
                            'status': False,
                            'custom_data': {}
                        },
                        {
                            'title': 'Zadanie z priorytetem',
                            'status': False,
                            'custom_data': {}
                        }
                    ]
                    
                    for task in sample_tasks:
                        custom_data_json = json.dumps(task.get('custom_data', {}))
                        cursor.execute("""
                            INSERT INTO tasks (
                                user_id, title, status, completion_date, 
                                custom_data, row_color, created_at, updated_at
                            ) VALUES (?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)
                        """, (
                            self.user_id,
                            task['title'],
                            task['status'],
                            task.get('completion_date'),
                            custom_data_json,
                            task.get('row_color')
                        ))
                    
                    conn.commit()
                    logger.info(f"[TASK DB] Created {len(sample_tasks)} sample tasks for user {self.user_id}")
                    return True
                else:
                    logger.info(f"[TASK DB] Tasks already exist ({count}), skipping sample data")
                    return False
                    
        except Exception as e:
            logger.error(f"[TASK DB] Failed to create sample tasks: {e}")
            return False

    # ==================== ZARZĄDZANIE KANBAN ====================
    
    def get_kanban_settings(self) -> Dict[str, Any]:
        """Pobierz ustawienia widoku KanBan dla użytkownika"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM kanban_settings WHERE user_id = ?
                """, (self.user_id,))
                
                row = cursor.fetchone()
                
                if row:
                    return dict(row)
                else:
                    # Utwórz domyślne ustawienia
                    cursor.execute("""
                        INSERT INTO kanban_settings (
                            user_id, max_in_progress, hide_completed_after,
                            show_on_hold, show_review
                        ) VALUES (?, ?, ?, ?, ?)
                    """, (self.user_id, 3, 0, 0, 0))
                    conn.commit()
                    
                    return {
                        'user_id': self.user_id,
                        'max_in_progress': 3,
                        'hide_completed_after': 0,
                        'show_on_hold': False,
                        'show_review': False
                    }
                    
        except Exception as e:
            logger.error(f"[TASK DB] Failed to get kanban settings: {e}")
            return {
                'max_in_progress': 3,
                'hide_completed_after': 0,
                'show_on_hold': False,
                'show_review': False
            }
    
    def update_kanban_settings(self, settings: Dict[str, Any]) -> bool:
        """Zaktualizuj ustawienia widoku KanBan"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO kanban_settings (
                        user_id, max_in_progress, hide_completed_after,
                        show_on_hold, show_review, updated_at
                    ) VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                """, (
                    self.user_id,
                    settings.get('max_in_progress', 3),
                    settings.get('hide_completed_after', 0),
                    settings.get('show_on_hold', 0),
                    settings.get('show_review', 0)
                ))
                
                conn.commit()
                logger.info(f"[TASK DB] Updated kanban settings for user {self.user_id}")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to update kanban settings: {e}")
            return False
    
    def get_kanban_items(self, column_type: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Pobierz zadania z widoku KanBan
        
        Args:
            column_type: Typ kolumny ('todo', 'in_progress', 'done', 'on_hold', 'review')
                        None = wszystkie
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if column_type:
                    cursor.execute("""
                        SELECT k.*, t.title, t.status, t.completion_date, 
                               t.archived, t.created_at as task_created_at,
                               t.custom_data
                        FROM kanban_items k
                        JOIN tasks t ON k.task_id = t.id
                        WHERE k.user_id = ? AND k.column_type = ?
                          AND t.deleted_at IS NULL
                        ORDER BY k.position ASC
                    """, (self.user_id, column_type))
                else:
                    cursor.execute("""
                        SELECT k.*, t.title, t.status, t.completion_date,
                               t.archived, t.created_at as task_created_at,
                               t.custom_data
                        FROM kanban_items k
                        JOIN tasks t ON k.task_id = t.id
                        WHERE k.user_id = ?
                          AND t.deleted_at IS NULL
                        ORDER BY k.column_type, k.position ASC
                    """, (self.user_id,))
                
                items = []
                for row in cursor.fetchall():
                    item = dict(row)
                    # Parse custom_data
                    if item.get('custom_data'):
                        try:
                            item['custom_data'] = json.loads(item['custom_data'])
                        except:
                            item['custom_data'] = {}
                    items.append(item)
                
                logger.info(f"[TASK DB] Retrieved {len(items)} kanban items")
                return items
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to get kanban items: {e}")
            return []
    
    def add_task_to_kanban(self, task_id: int, column_type: str = 'todo', position: Optional[int] = None) -> bool:
        """
        Dodaj zadanie do widoku KanBan
        
        Args:
            task_id: ID zadania
            column_type: Typ kolumny ('todo', 'in_progress', 'done', 'on_hold', 'review')
            position: Pozycja w kolumnie (None = na końcu)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Jeśli nie podano pozycji, ustaw na końcu
                if position is None:
                    cursor.execute("""
                        SELECT COALESCE(MAX(position), -1) + 1 
                        FROM kanban_items 
                        WHERE user_id = ? AND column_type = ?
                    """, (self.user_id, column_type))
                    position = cursor.fetchone()[0]
                
                cursor.execute("""
                    INSERT OR REPLACE INTO kanban_items (
                        user_id, task_id, column_type, position
                    ) VALUES (?, ?, ?, ?)
                """, (self.user_id, task_id, column_type, position))

                timestamp = self._now_iso()
                self._ensure_task_custom_fields(
                    cursor,
                    task_id,
                    {
                        'kanban_added_at': timestamp,
                    },
                )
                self._ensure_task_custom_fields(
                    cursor,
                    task_id,
                    {
                        'kanban_last_column': column_type,
                        'kanban_last_moved_at': timestamp,
                    },
                    overwrite=True,
                )

                if column_type == 'in_progress':
                    self._ensure_task_custom_fields(
                        cursor,
                        task_id,
                        {
                            'kanban_started_at': timestamp,
                        },
                    )
                if column_type == 'done':
                    self._ensure_task_custom_fields(
                        cursor,
                        task_id,
                        {
                            'kanban_completed_at': timestamp,
                        },
                    )
                
                # Zapisz historię dodania do Kanban
                details = {
                    'to_column': column_type,
                    'position': position,
                    'timestamp': timestamp,
                    'action': 'added_to_kanban'
                }
                cursor.execute("""
                    INSERT INTO task_history 
                    (user_id, task_id, action_type, old_value, new_value, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.user_id, 
                    task_id, 
                    'kanban_add', 
                    None, 
                    column_type,
                    json.dumps(details)
                ))
                
                conn.commit()
                logger.info(f"[TASK DB] Added task {task_id} to kanban column '{column_type}' at position {position}")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to add task to kanban: {e}")
            return False
    
    def remove_task_from_kanban(self, task_id: int) -> bool:
        """Usuń zadanie z widoku KanBan"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("""
                    DELETE FROM kanban_items 
                    WHERE user_id = ? AND task_id = ?
                """, (self.user_id, task_id))

                timestamp = self._now_iso()
                self._ensure_task_custom_fields(
                    cursor,
                    task_id,
                    {
                        'kanban_removed_at': timestamp,
                        'kanban_last_column': 'removed',
                        'kanban_last_moved_at': timestamp,
                    },
                    overwrite=True,
                )
                
                # Zapisz historię usunięcia
                details = {
                    'from_column': previous_column or 'unknown',
                    'timestamp': timestamp,
                    'action': 'removed_from_kanban'
                }
                cursor.execute("""
                    INSERT INTO task_history 
                    (user_id, task_id, action_type, old_value, new_value, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (
                    self.user_id, 
                    task_id, 
                    'kanban_remove', 
                    previous_column, 
                    None,
                    json.dumps(details)
                ))
                
                conn.commit()
                logger.info(f"[TASK DB] Removed task {task_id} from kanban")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to remove task from kanban: {e}")
            return False
    
    def move_kanban_item(self, task_id: int, new_column: str, new_position: int) -> bool:
        """
        Przenieś zadanie w widoku KanBan
        
        Args:
            task_id: ID zadania
            new_column: Nowa kolumna ('todo', 'in_progress', 'done', 'on_hold', 'review')
            new_position: Nowa pozycja w kolumnie
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()

                cursor.execute(
                    """
                    SELECT column_type, created_at
                    FROM kanban_items
                    WHERE user_id = ? AND task_id = ?
                    """,
                    (self.user_id, task_id),
                )
                existing_row = cursor.fetchone()
                previous_column = existing_row[0] if existing_row else None
                created_at_value = existing_row[1] if existing_row and len(existing_row) > 1 else None
                
                # Aktualizuj pozycję i kolumnę
                cursor.execute("""
                    UPDATE kanban_items 
                    SET column_type = ?, position = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE user_id = ? AND task_id = ?
                """, (new_column, new_position, self.user_id, task_id))

                if created_at_value:
                    self._ensure_task_custom_fields(
                        cursor,
                        task_id,
                        {
                            'kanban_added_at': created_at_value,
                        },
                    )

                now_iso = self._now_iso()
                custom_updates = {
                    'kanban_last_column': new_column,
                    'kanban_last_moved_at': now_iso,
                }

                if new_column == 'in_progress' and previous_column != 'in_progress':
                    custom_updates['kanban_started_at'] = now_iso

                if new_column == 'done' and previous_column != 'done':
                    custom_updates['kanban_completed_at'] = now_iso
                    if previous_column:
                        custom_updates['kanban_previous_column'] = previous_column
                elif previous_column == 'done' and new_column != 'done':
                    custom_updates['kanban_previous_column'] = new_column

                self._ensure_task_custom_fields(
                    cursor,
                    task_id,
                    custom_updates,
                    overwrite=True,
                )
                
                # Zapisz historię przesunięcia
                if previous_column != new_column:
                    details = {
                        'from_column': previous_column or 'none',
                        'to_column': new_column,
                        'position': new_position,
                        'timestamp': now_iso
                    }
                    cursor.execute("""
                        INSERT INTO task_history 
                        (user_id, task_id, action_type, old_value, new_value, details)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        self.user_id, 
                        task_id, 
                        'kanban_move', 
                        previous_column, 
                        new_column,
                        json.dumps(details)
                    ))
                    logger.debug(f"[TASK DB] Added history: task {task_id} moved from {previous_column} to {new_column}")
                
                conn.commit()
                logger.info(f"[TASK DB] Moved task {task_id} to column '{new_column}' position {new_position}")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to move kanban item: {e}")
            return False
    
    def reorder_kanban_column(self, column_type: str, task_positions: List[tuple]) -> bool:
        """
        Zmień kolejność zadań w kolumnie KanBan
        
        Args:
            column_type: Typ kolumny
            task_positions: Lista tupli (task_id, new_position)
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                for task_id, position in task_positions:
                    cursor.execute("""
                        UPDATE kanban_items 
                        SET position = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE user_id = ? AND task_id = ? AND column_type = ?
                    """, (position, self.user_id, task_id, column_type))
                
                conn.commit()
                logger.info(f"[TASK DB] Reordered {len(task_positions)} items in column '{column_type}'")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to reorder kanban column: {e}")
            return False

    @staticmethod
    def _parse_datetime(value: Any) -> Optional[datetime]:
        if value in (None, ""):
            return None
        if isinstance(value, datetime):
            return value

        text = str(value).strip()
        if not text:
            return None
        if text.endswith('Z'):
            text = text[:-1]

        try:
            return datetime.fromisoformat(text)
        except ValueError:
            pass

        for fmt in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
            try:
                return datetime.strptime(text, fmt)
            except ValueError:
                continue
        return None

    def get_kanban_log_entries(self, filter_mode: str = 'completed') -> List[Dict[str, Any]]:
        """Return aggregated Kanban cycle data for completed or archived tasks."""
        mode = filter_mode if filter_mode in {'completed', 'archived'} else 'completed'

        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()

                base_query = (
                    """
                    SELECT id, title, status, completion_date, archived,
                           archived_at, created_at, updated_at, custom_data
                    FROM tasks
                    WHERE user_id = ? AND deleted_at IS NULL
                    """
                )

                if mode == 'archived':
                    cursor.execute(
                        base_query
                        + " AND archived = 1"
                        + " ORDER BY archived_at IS NULL, archived_at DESC, updated_at DESC",
                        (self.user_id,),
                    )
                else:
                    cursor.execute(
                        base_query
                        + " AND status = 1"
                        + " ORDER BY completion_date IS NULL, completion_date DESC, updated_at DESC",
                        (self.user_id,),
                    )

                items: List[Dict[str, Any]] = []
                for row in cursor.fetchall():
                    custom_data: Dict[str, Any] = {}
                    raw_custom = row["custom_data"]
                    if raw_custom:
                        try:
                            custom_data = json.loads(raw_custom) or {}
                        except json.JSONDecodeError:
                            custom_data = {}

                    if not (
                        custom_data.get('kanban_added_at')
                        or custom_data.get('kanban_started_at')
                        or custom_data.get('kanban_completed_at')
                    ):
                        continue

                    added_raw = custom_data.get('kanban_added_at')
                    started_raw = custom_data.get('kanban_started_at')
                    completed_raw = custom_data.get('kanban_completed_at')

                    added_dt = self._parse_datetime(added_raw)
                    started_dt = self._parse_datetime(started_raw)
                    completed_dt = self._parse_datetime(completed_raw) or self._parse_datetime(row['completion_date'])

                    # Fallbacks for missing timestamps
                    if added_dt is None:
                        added_dt = self._parse_datetime(row['created_at'])

                    time_to_start_minutes: Optional[int] = None
                    if added_dt and started_dt:
                        delta_seconds = (started_dt - added_dt).total_seconds()
                        if delta_seconds >= 0:
                            time_to_start_minutes = int(delta_seconds // 60)

                    time_to_finish_minutes: Optional[int] = None
                    if started_dt and completed_dt:
                        finish_delta = (completed_dt - started_dt).total_seconds()
                        if finish_delta >= 0:
                            time_to_finish_minutes = int(finish_delta // 60)

                    items.append(
                        {
                            'task_id': row['id'],
                            'title': row['title'] or '',
                            'task_created_at': row['created_at'],
                            'kanban_added_at': added_dt.isoformat() if added_dt else None,
                            'kanban_started_at': started_dt.isoformat() if started_dt else None,
                            'kanban_completed_at': completed_dt.isoformat() if completed_dt else None,
                            'completion_date': row['completion_date'],
                            'archived_at': row['archived_at'],
                            'status': row['status'],
                            'archived': row['archived'],
                            'time_to_start_minutes': time_to_start_minutes,
                            'time_to_finish_minutes': time_to_finish_minutes,
                        }
                    )

                return items

        except Exception as e:
            logger.error(f"[TASK DB] Failed to gather Kanban log entries: {e}")
            return []
    
    # ========== METODY ZARZĄDZANIA ALARMAMI ==========
    
    def save_task_alarm(self, task_id: int, alarm_data: Dict[str, Any]) -> bool:
        """
        Zapisz alarm dla zadania
        
        Args:
            task_id: ID zadania
            alarm_data: Dane alarmu z TaskAlarmDialog
                - alarm_time: datetime - czas alarmu
                - is_recurring: bool - czy alarm cykliczny
                - interval_minutes: int - interwał w minutach (dla cyklicznych)
                - end_date: datetime - data końca (dla cyklicznych)
                - play_sound: bool - czy odtwarzać dźwięk
                - show_popup: bool - czy pokazać popup
                - label: str - etykieta alarmu
        
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Konwertuj datetime na string ISO
                alarm_time = alarm_data.get('alarm_time')
                if not alarm_time:
                    logger.error(f"[TASK DB] alarm_time is required for task {task_id}")
                    return False
                    
                if hasattr(alarm_time, 'isoformat'):
                    alarm_time_str = alarm_time.isoformat()
                else:
                    alarm_time_str = str(alarm_time)
                
                end_date = alarm_data.get('end_date')
                end_date_str = None
                if end_date and hasattr(end_date, 'isoformat'):
                    end_date_str = end_date.isoformat()
                elif end_date:
                    end_date_str = str(end_date)
                
                # Aktualizuj lub wstaw dane alarmu
                cursor.execute("""
                    INSERT INTO task_alarms (
                        task_id, alarm_time, is_recurring, interval_minutes,
                        end_date, play_sound, show_popup, label, updated_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    ON CONFLICT(task_id) DO UPDATE SET
                        alarm_time = excluded.alarm_time,
                        is_recurring = excluded.is_recurring,
                        interval_minutes = excluded.interval_minutes,
                        end_date = excluded.end_date,
                        play_sound = excluded.play_sound,
                        show_popup = excluded.show_popup,
                        label = excluded.label,
                        updated_at = CURRENT_TIMESTAMP
                """, (
                    task_id,
                    alarm_time_str,
                    alarm_data.get('is_recurring', False),
                    alarm_data.get('interval_minutes'),
                    end_date_str,
                    alarm_data.get('play_sound', True),
                    alarm_data.get('show_popup', True),
                    alarm_data.get('label', '')
                ))
                
                # Aktualizuj również kolumnę alarm_date w tabeli tasks
                cursor.execute("""
                    UPDATE tasks 
                    SET alarm_date = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                """, (alarm_time_str, task_id, self.user_id))
                
                conn.commit()
                logger.info(f"[TASK DB] Saved alarm for task {task_id}")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to save task alarm: {e}")
            return False
    
    def get_task_alarm(self, task_id: int) -> Optional[Dict[str, Any]]:
        """
        Pobierz dane alarmu dla zadania
        
        Args:
            task_id: ID zadania
            
        Returns:
            Dict z danymi alarmu lub None jeśli nie ma alarmu
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM task_alarms WHERE task_id = ?
                """, (task_id,))
                
                row = cursor.fetchone()
                
                if row:
                    alarm = dict(row)
                    
                    # Konwertuj stringi datetime na obiekty datetime
                    if alarm.get('alarm_time'):
                        try:
                            alarm['alarm_time'] = datetime.fromisoformat(alarm['alarm_time'])
                        except:
                            pass
                    
                    if alarm.get('end_date'):
                        try:
                            alarm['end_date'] = datetime.fromisoformat(alarm['end_date'])
                        except:
                            pass
                    
                    return alarm
                
                return None
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to get task alarm: {e}")
            return None
    
    def remove_task_alarm(self, task_id: int) -> bool:
        """
        Usuń alarm dla zadania
        
        Args:
            task_id: ID zadania
            
        Returns:
            True jeśli sukces
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                
                # Usuń z tabeli task_alarms
                cursor.execute("""
                    DELETE FROM task_alarms WHERE task_id = ?
                """, (task_id,))
                
                # Wyczyść alarm_date w tabeli tasks
                cursor.execute("""
                    UPDATE tasks 
                    SET alarm_date = NULL, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ? AND user_id = ?
                """, (task_id, self.user_id))
                
                conn.commit()
                logger.info(f"[TASK DB] Removed alarm for task {task_id}")
                return True
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to remove task alarm: {e}")
            return False
    
    def get_next_alarm_date(self, task_id: int) -> Optional[datetime]:
        """
        Pobierz datę następnego alarmu (dla cyklicznych zwraca następne wystąpienie)
        
        Args:
            task_id: ID zadania
            
        Returns:
            datetime następnego alarmu lub None
        """
        try:
            alarm = self.get_task_alarm(task_id)
            
            if not alarm:
                return None
            
            alarm_time = alarm.get('alarm_time')
            if not isinstance(alarm_time, datetime):
                return None
            
            # Jeśli nie jest cykliczny, zwróć po prostu alarm_time
            if not alarm.get('is_recurring'):
                return alarm_time
            
            # Dla cyklicznych: oblicz następne wystąpienie
            from datetime import timedelta
            
            now = datetime.now()
            interval_minutes = alarm.get('interval_minutes', 0)
            
            if interval_minutes <= 0:
                return alarm_time
            
            # Jeśli alarm_time jest w przyszłości, to jest najbliższym
            if alarm_time > now:
                return alarm_time
            
            # Oblicz ile okresów minęło od alarm_time
            delta = now - alarm_time
            periods_passed = int(delta.total_seconds() / 60 / interval_minutes)
            
            # Oblicz następny alarm
            next_alarm = alarm_time + timedelta(minutes=interval_minutes * (periods_passed + 1))
            
            # Sprawdź czy nie przekroczyliśmy end_date
            end_date = alarm.get('end_date')
            if end_date and isinstance(end_date, datetime):
                if next_alarm > end_date:
                    return None  # Alarm się zakończył
            
            return next_alarm
            
        except Exception as e:
            logger.error(f"[TASK DB] Failed to calculate next alarm date: {e}")
            return None

    # ========== HISTORIA ZMIAN ==========
    
    def add_task_history(
        self, 
        task_id: int, 
        action_type: str, 
        old_value: Optional[str] = None,
        new_value: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> bool:
        """
        Dodaj wpis do historii zadania
        
        Args:
            task_id: ID zadania
            action_type: Typ akcji (np. 'kanban_move', 'status_change', 'edit')
            old_value: Poprzednia wartość
            new_value: Nowa wartość
            details: Dodatkowe szczegóły jako słownik
            
        Returns:
            True jeśli sukces
        """
        try:
            details_json = json.dumps(details) if details else None
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO task_history 
                    (user_id, task_id, action_type, old_value, new_value, details)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (self.user_id, task_id, action_type, old_value, new_value, details_json))
                conn.commit()
                
            logger.debug(f"[TASK DB] Added history entry: task={task_id}, action={action_type}")
            return True
            
        except Exception as e:
            logger.error(f"[TASK DB] Failed to add task history: {e}")
            return False
    
    def get_task_history(
        self, 
        task_id: Optional[int] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Pobierz historię zmian zadań
        
        Args:
            task_id: ID zadania (None = wszystkie zadania)
            limit: Maksymalna liczba wpisów
            
        Returns:
            Lista wpisów historii
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if task_id:
                    cursor.execute("""
                        SELECT * FROM task_history
                        WHERE task_id = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (task_id, limit))
                else:
                    cursor.execute("""
                        SELECT * FROM task_history
                        WHERE user_id = ?
                        ORDER BY created_at DESC
                        LIMIT ?
                    """, (self.user_id, limit))
                
                rows = cursor.fetchall()
                history = []
                
                for row in rows:
                    entry = dict(row)
                    # Parse details JSON if exists
                    if entry.get('details'):
                        try:
                            entry['details'] = json.loads(entry['details'])
                        except:
                            pass
                    history.append(entry)
                
                return history
                
        except Exception as e:
            logger.error(f"[TASK DB] Failed to get task history: {e}")
            return []


