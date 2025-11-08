"""
Assistant Database Schema - Schemat bazy danych asystenta
=============================================================================
Zarządzanie frazami wywołującymi funkcje asystenta w bazie danych.

Struktura:
- Tabela assistant_phrases: przechowuje wszystkie frazy
- Dynamiczne ładowanie bez hardcoded stringów
- Wsparcie wielojęzyczności
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass, asdict
from loguru import logger
import sqlite3
import json
from pathlib import Path


@dataclass
class AssistantPhrase:
    """Model frazy asystenta."""
    id: Optional[int] = None
    module: str = ""  # np. 'task', 'note', 'alarm', 'pomodoro', 'kanban', etc.
    action: str = ""  # np. 'create', 'delete', 'open', 'edit', 'list'
    phrase: str = ""  # Tekst frazy (może zawierać {entity} jako placeholder)
    language: str = "pl"  # Kod języka (pl, en, de, etc.)
    priority: int = 5  # Priorytet 1-10 (wyższy = sprawdzany wcześniej)
    is_active: bool = True  # Czy fraza jest aktywna
    is_custom: bool = False  # Czy to fraza użytkownika (False = domyślna)
    extract_entity: bool = False  # Czy ekstraktować nazwę własną
    description: str = ""  # Opis frazy (dla UI)
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwersja do słownika."""
        return asdict(self)


class AssistantDatabase:
    """Zarządza bazą danych fraz asystenta."""
    
    def __init__(self, db_path: str = "data/assistant.db"):
        """
        Inicjalizacja bazy danych.
        
        Args:
            db_path: Ścieżka do pliku bazy danych
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._init_database()
        logger.info(f"[ASSISTANT_DB] Initialized: {self.db_path}")
    
    def _init_database(self):
        """Inicjalizuje strukturę bazy danych."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Tabela fraz
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS assistant_phrases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    module TEXT NOT NULL,
                    action TEXT NOT NULL,
                    phrase TEXT NOT NULL,
                    language TEXT NOT NULL DEFAULT 'pl',
                    priority INTEGER NOT NULL DEFAULT 5,
                    is_active INTEGER NOT NULL DEFAULT 1,
                    is_custom INTEGER NOT NULL DEFAULT 0,
                    extract_entity INTEGER NOT NULL DEFAULT 0,
                    description TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(phrase, language)
                )
            """)
            
            # Indeksy dla wydajności
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_module_action 
                ON assistant_phrases(module, action)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_language 
                ON assistant_phrases(language)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_active 
                ON assistant_phrases(is_active)
            """)
            
            conn.commit()
            logger.debug("[ASSISTANT_DB] Database schema created")
    
    def add_phrase(self, phrase: AssistantPhrase) -> int:
        """
        Dodaje nową frazę do bazy.
        
        Args:
            phrase: Obiekt AssistantPhrase
            
        Returns:
            ID dodanej frazy
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            try:
                cursor.execute("""
                    INSERT INTO assistant_phrases 
                    (module, action, phrase, language, priority, is_active, is_custom, extract_entity, description)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    phrase.module,
                    phrase.action,
                    phrase.phrase,
                    phrase.language,
                    phrase.priority,
                    1 if phrase.is_active else 0,
                    1 if phrase.is_custom else 0,
                    1 if phrase.extract_entity else 0,
                    phrase.description
                ))
                
                conn.commit()
                phrase_id = cursor.lastrowid
                logger.debug(f"[ASSISTANT_DB] Added phrase ID={phrase_id}: {phrase.phrase}")
                return phrase_id
                
            except sqlite3.IntegrityError as e:
                logger.warning(f"[ASSISTANT_DB] Phrase already exists: {phrase.phrase} ({e})")
                return -1
    
    def update_phrase(self, phrase: AssistantPhrase) -> bool:
        """
        Aktualizuje istniejącą frazę.
        
        Args:
            phrase: Obiekt AssistantPhrase z ID
            
        Returns:
            True jeśli zaktualizowano
        """
        if not phrase.id:
            logger.error("[ASSISTANT_DB] Cannot update phrase without ID")
            return False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE assistant_phrases 
                SET module = ?, action = ?, phrase = ?, language = ?, 
                    priority = ?, is_active = ?, extract_entity = ?, description = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                phrase.module,
                phrase.action,
                phrase.phrase,
                phrase.language,
                phrase.priority,
                1 if phrase.is_active else 0,
                1 if phrase.extract_entity else 0,
                phrase.description,
                phrase.id
            ))
            
            conn.commit()
            updated = cursor.rowcount > 0
            
            if updated:
                logger.debug(f"[ASSISTANT_DB] Updated phrase ID={phrase.id}")
            
            return updated
    
    def delete_phrase(self, phrase_id: int) -> bool:
        """
        Usuwa frazę (tylko custom phrases).
        
        Args:
            phrase_id: ID frazy
            
        Returns:
            True jeśli usunięto
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Sprawdź czy to custom phrase
            cursor.execute("SELECT is_custom FROM assistant_phrases WHERE id = ?", (phrase_id,))
            row = cursor.fetchone()
            
            if not row:
                logger.warning(f"[ASSISTANT_DB] Phrase ID={phrase_id} not found")
                return False
            
            if not row[0]:
                logger.warning(f"[ASSISTANT_DB] Cannot delete default phrase ID={phrase_id}")
                return False
            
            cursor.execute("DELETE FROM assistant_phrases WHERE id = ?", (phrase_id,))
            conn.commit()
            
            logger.debug(f"[ASSISTANT_DB] Deleted phrase ID={phrase_id}")
            return True
    
    def toggle_phrase(self, phrase_id: int) -> bool:
        """
        Przełącza aktywność frazy.
        
        Args:
            phrase_id: ID frazy
            
        Returns:
            True jeśli przełączono
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE assistant_phrases 
                SET is_active = NOT is_active,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (phrase_id,))
            
            conn.commit()
            updated = cursor.rowcount > 0
            
            if updated:
                logger.debug(f"[ASSISTANT_DB] Toggled phrase ID={phrase_id}")
            
            return updated
    
    def get_phrases(
        self, 
        module: Optional[str] = None,
        action: Optional[str] = None,
        language: Optional[str] = None,
        active_only: bool = True
    ) -> List[AssistantPhrase]:
        """
        Pobiera frazy z bazy z opcjonalnymi filtrami.
        
        Args:
            module: Filtr po module (None = wszystkie)
            action: Filtr po action (None = wszystkie)
            language: Filtr po języku (None = wszystkie)
            active_only: Czy tylko aktywne frazy
            
        Returns:
            Lista obiektów AssistantPhrase
        """
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            query = "SELECT * FROM assistant_phrases WHERE 1=1"
            params = []
            
            if module:
                query += " AND module = ?"
                params.append(module)
            
            if action:
                query += " AND action = ?"
                params.append(action)
            
            if language:
                query += " AND language = ?"
                params.append(language)
            
            if active_only:
                query += " AND is_active = 1"
            
            # Sortuj po priorytecie (malejąco)
            query += " ORDER BY priority DESC, id ASC"
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            phrases = []
            for row in rows:
                phrase = AssistantPhrase(
                    id=row['id'],
                    module=row['module'],
                    action=row['action'],
                    phrase=row['phrase'],
                    language=row['language'],
                    priority=row['priority'],
                    is_active=bool(row['is_active']),
                    is_custom=bool(row['is_custom']),
                    extract_entity=bool(row['extract_entity']),
                    description=row['description'] or ""
                )
                phrases.append(phrase)
            
            logger.debug(f"[ASSISTANT_DB] Retrieved {len(phrases)} phrases")
            return phrases
    
    def get_phrase_by_id(self, phrase_id: int) -> Optional[AssistantPhrase]:
        """Pobiera pojedynczą frazę po ID."""
        phrases = self.get_phrases(active_only=False)
        for phrase in phrases:
            if phrase.id == phrase_id:
                return phrase
        return None
    
    def get_available_modules(self) -> List[str]:
        """Pobiera listę dostępnych modułów."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT module FROM assistant_phrases ORDER BY module")
            return [row[0] for row in cursor.fetchall()]
    
    def get_available_actions(self, module: str) -> List[str]:
        """Pobiera listę dostępnych akcji dla modułu."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT DISTINCT action FROM assistant_phrases WHERE module = ? ORDER BY action",
                (module,)
            )
            return [row[0] for row in cursor.fetchall()]
    
    def init_default_phrases(self):
        """
        Inicjalizuje domyślne frazy dla wszystkich modułów.
        Wywoływane tylko przy pierwszym uruchomieniu.
        """
        # Sprawdź czy już są jakieś frazy
        existing = self.get_phrases(active_only=False)
        if existing:
            logger.info("[ASSISTANT_DB] Default phrases already initialized")
            return
        
        default_phrases = self._get_default_phrases()
        
        for phrase_data in default_phrases:
            phrase = AssistantPhrase(**phrase_data)
            self.add_phrase(phrase)
        
        logger.info(f"[ASSISTANT_DB] Initialized {len(default_phrases)} default phrases")
    
    def _get_default_phrases(self) -> List[Dict[str, Any]]:
        """
        Zwraca listę domyślnych fraz.
        Te frazy są ładowane z pliku JSON lub definiowane tutaj.
        """
        # Możemy później przenieść do pliku JSON
        return [
            # === TASK MODULE ===
            # Polish
            {"module": "task", "action": "create", "phrase": "utwórz zadanie", "language": "pl", "priority": 8, "extract_entity": True, "description": "Tworzy nowe zadanie"},
            {"module": "task", "action": "create", "phrase": "dodaj zadanie", "language": "pl", "priority": 8, "extract_entity": True, "description": "Tworzy nowe zadanie"},
            {"module": "task", "action": "create", "phrase": "nowe zadanie", "language": "pl", "priority": 8, "extract_entity": True, "description": "Tworzy nowe zadanie"},
            {"module": "task", "action": "delete", "phrase": "usuń zadanie", "language": "pl", "priority": 8, "extract_entity": True, "description": "Usuwa zadanie"},
            {"module": "task", "action": "open", "phrase": "otwórz zadanie", "language": "pl", "priority": 7, "extract_entity": True, "description": "Otwiera zadanie"},
            {"module": "task", "action": "list", "phrase": "pokaż zadania", "language": "pl", "priority": 6, "extract_entity": False, "description": "Wyświetla listę zadań"},
            # English
            {"module": "task", "action": "create", "phrase": "create task", "language": "en", "priority": 8, "extract_entity": True, "description": "Creates new task"},
            {"module": "task", "action": "create", "phrase": "add task", "language": "en", "priority": 8, "extract_entity": True, "description": "Creates new task"},
            {"module": "task", "action": "delete", "phrase": "delete task", "language": "en", "priority": 8, "extract_entity": True, "description": "Deletes task"},
            
            # === NOTE MODULE ===
            # Polish
            {"module": "note", "action": "create", "phrase": "utwórz notatkę", "language": "pl", "priority": 8, "extract_entity": True, "description": "Tworzy nową notatkę"},
            {"module": "note", "action": "create", "phrase": "nowa notatka", "language": "pl", "priority": 8, "extract_entity": True, "description": "Tworzy nową notatkę"},
            {"module": "note", "action": "delete", "phrase": "usuń notatkę", "language": "pl", "priority": 8, "extract_entity": True, "description": "Usuwa notatkę"},
            {"module": "note", "action": "open", "phrase": "otwórz notatkę", "language": "pl", "priority": 7, "extract_entity": True, "description": "Otwiera notatkę"},
            # English
            {"module": "note", "action": "create", "phrase": "create note", "language": "en", "priority": 8, "extract_entity": True, "description": "Creates new note"},
            {"module": "note", "action": "open", "phrase": "open note", "language": "en", "priority": 7, "extract_entity": True, "description": "Opens note"},
            
            # === ALARM MODULE ===
            # Polish
            {"module": "alarm", "action": "create", "phrase": "ustaw alarm", "language": "pl", "priority": 8, "extract_entity": True, "description": "Ustawia nowy alarm"},
            {"module": "alarm", "action": "create", "phrase": "nowy alarm", "language": "pl", "priority": 8, "extract_entity": True, "description": "Ustawia nowy alarm"},
            {"module": "alarm", "action": "delete", "phrase": "usuń alarm", "language": "pl", "priority": 8, "extract_entity": True, "description": "Usuwa alarm"},
            {"module": "alarm", "action": "list", "phrase": "pokaż alarmy", "language": "pl", "priority": 6, "extract_entity": False, "description": "Wyświetla listę alarmów"},
            # English
            {"module": "alarm", "action": "create", "phrase": "set alarm", "language": "en", "priority": 8, "extract_entity": True, "description": "Sets new alarm"},
            {"module": "alarm", "action": "delete", "phrase": "delete alarm", "language": "en", "priority": 8, "extract_entity": True, "description": "Deletes alarm"},
            
            # === POMODORO MODULE ===
            # Polish - Open
            {"module": "pomodoro", "action": "open", "phrase": "otwórz pomodoro", "language": "pl", "priority": 7, "extract_entity": False, "description": "Otwiera widok pomodoro"},
            {"module": "pomodoro", "action": "open", "phrase": "pomodoro", "language": "pl", "priority": 5, "extract_entity": False, "description": "Otwiera widok pomodoro"},
            # Polish - Start
            {"module": "pomodoro", "action": "start", "phrase": "uruchom pomodoro", "language": "pl", "priority": 7, "extract_entity": False, "description": "Rozpoczyna sesję pomodoro"},
            {"module": "pomodoro", "action": "start", "phrase": "start pomodoro", "language": "pl", "priority": 7, "extract_entity": False, "description": "Rozpoczyna sesję pomodoro"},
            {"module": "pomodoro", "action": "start", "phrase": "rozpocznij pomodoro", "language": "pl", "priority": 7, "extract_entity": False, "description": "Rozpoczyna sesję pomodoro"},
            {"module": "pomodoro", "action": "start", "phrase": "pomodoro start", "language": "pl", "priority": 6, "extract_entity": False, "description": "Rozpoczyna sesję pomodoro"},
            # Polish - Pause
            {"module": "pomodoro", "action": "pause", "phrase": "pauza pomodoro", "language": "pl", "priority": 7, "extract_entity": False, "description": "Pauzuje sesję pomodoro"},
            {"module": "pomodoro", "action": "pause", "phrase": "zapauzuj pomodoro", "language": "pl", "priority": 7, "extract_entity": False, "description": "Pauzuje sesję pomodoro"},
            {"module": "pomodoro", "action": "pause", "phrase": "pomodoro pauza", "language": "pl", "priority": 6, "extract_entity": False, "description": "Pauzuje sesję pomodoro"},
            {"module": "pomodoro", "action": "pause", "phrase": "wstrzymaj pomodoro", "language": "pl", "priority": 7, "extract_entity": False, "description": "Pauzuje sesję pomodoro"},
            # Polish - Stop
            {"module": "pomodoro", "action": "stop", "phrase": "zatrzymaj pomodoro", "language": "pl", "priority": 7, "extract_entity": False, "description": "Zatrzymuje sesję pomodoro"},
            {"module": "pomodoro", "action": "stop", "phrase": "zakończ pomodoro", "language": "pl", "priority": 7, "extract_entity": False, "description": "Zatrzymuje sesję pomodoro"},
            {"module": "pomodoro", "action": "stop", "phrase": "pomodoro stop", "language": "pl", "priority": 6, "extract_entity": False, "description": "Zatrzymuje sesję pomodoro"},
            {"module": "pomodoro", "action": "stop", "phrase": "zakończ sesję pomodoro", "language": "pl", "priority": 8, "extract_entity": False, "description": "Zatrzymuje sesję pomodoro"},
            # English - Open
            {"module": "pomodoro", "action": "open", "phrase": "open pomodoro", "language": "en", "priority": 7, "extract_entity": False, "description": "Opens pomodoro view"},
            {"module": "pomodoro", "action": "open", "phrase": "pomodoro", "language": "en", "priority": 5, "extract_entity": False, "description": "Opens pomodoro view"},
            # English - Start
            {"module": "pomodoro", "action": "start", "phrase": "start pomodoro", "language": "en", "priority": 7, "extract_entity": False, "description": "Starts pomodoro session"},
            {"module": "pomodoro", "action": "start", "phrase": "pomodoro start", "language": "en", "priority": 6, "extract_entity": False, "description": "Starts pomodoro session"},
            {"module": "pomodoro", "action": "start", "phrase": "begin pomodoro", "language": "en", "priority": 7, "extract_entity": False, "description": "Starts pomodoro session"},
            # English - Pause
            {"module": "pomodoro", "action": "pause", "phrase": "pause pomodoro", "language": "en", "priority": 7, "extract_entity": False, "description": "Pauses pomodoro session"},
            {"module": "pomodoro", "action": "pause", "phrase": "pomodoro pause", "language": "en", "priority": 6, "extract_entity": False, "description": "Pauses pomodoro session"},
            # English - Stop
            {"module": "pomodoro", "action": "stop", "phrase": "stop pomodoro", "language": "en", "priority": 7, "extract_entity": False, "description": "Stops pomodoro session"},
            {"module": "pomodoro", "action": "stop", "phrase": "pomodoro stop", "language": "en", "priority": 6, "extract_entity": False, "description": "Stops pomodoro session"},
            {"module": "pomodoro", "action": "stop", "phrase": "end pomodoro", "language": "en", "priority": 7, "extract_entity": False, "description": "Stops pomodoro session"},
            {"module": "pomodoro", "action": "stop", "phrase": "end pomodoro session", "language": "en", "priority": 8, "extract_entity": False, "description": "Stops pomodoro session"},
            
            # === KANBAN MODULE ===
            # Polish - Open
            {"module": "kanban", "action": "open", "phrase": "otwórz kanban", "language": "pl", "priority": 7, "extract_entity": False, "description": "Otwiera widok kanban"},
            {"module": "kanban", "action": "open", "phrase": "kanban", "language": "pl", "priority": 5, "extract_entity": False, "description": "Otwiera widok kanban"},
            # Polish - Show all
            {"module": "kanban", "action": "show_all", "phrase": "pokaż wszystkie", "language": "pl", "priority": 6, "extract_entity": False, "description": "Pokazuje wszystkie kolumny"},
            {"module": "kanban", "action": "show_all", "phrase": "kanban pokaż wszystkie", "language": "pl", "priority": 7, "extract_entity": False, "description": "Pokazuje wszystkie kolumny"},
            # Polish - Show columns
            {"module": "kanban", "action": "show_column", "phrase": "pokaż w trakcie", "language": "pl", "priority": 7, "extract_entity": True, "description": "Pokazuje kolumnę W trakcie"},
            {"module": "kanban", "action": "show_column", "phrase": "kanban pokaż w trakcie", "language": "pl", "priority": 8, "extract_entity": True, "description": "Pokazuje kolumnę W trakcie"},
            {"module": "kanban", "action": "show_column", "phrase": "pokaż do wykonania", "language": "pl", "priority": 7, "extract_entity": True, "description": "Pokazuje kolumnę Do wykonania"},
            {"module": "kanban", "action": "show_column", "phrase": "kanban pokaż do wykonania", "language": "pl", "priority": 8, "extract_entity": True, "description": "Pokazuje kolumnę Do wykonania"},
            {"module": "kanban", "action": "show_column", "phrase": "pokaż zakończone", "language": "pl", "priority": 7, "extract_entity": True, "description": "Pokazuje kolumnę Zakończone"},
            {"module": "kanban", "action": "show_column", "phrase": "kanban pokaż zakończone", "language": "pl", "priority": 8, "extract_entity": True, "description": "Pokazuje kolumnę Zakończone"},
            {"module": "kanban", "action": "show_column", "phrase": "pokaż do sprawdzenia", "language": "pl", "priority": 7, "extract_entity": True, "description": "Pokazuje kolumnę Do sprawdzenia"},
            {"module": "kanban", "action": "show_column", "phrase": "kanban pokaż do sprawdzenia", "language": "pl", "priority": 8, "extract_entity": True, "description": "Pokazuje kolumnę Do sprawdzenia"},
            {"module": "kanban", "action": "show_column", "phrase": "pokaż wstrzymane", "language": "pl", "priority": 7, "extract_entity": True, "description": "Pokazuje kolumnę Wstrzymane"},
            {"module": "kanban", "action": "show_column", "phrase": "kanban pokaż wstrzymane", "language": "pl", "priority": 8, "extract_entity": True, "description": "Pokazuje kolumnę Wstrzymane"},
            # Polish - Hide columns
            {"module": "kanban", "action": "hide_column", "phrase": "ukryj w trakcie", "language": "pl", "priority": 7, "extract_entity": True, "description": "Ukrywa kolumnę W trakcie"},
            {"module": "kanban", "action": "hide_column", "phrase": "kanban ukryj w trakcie", "language": "pl", "priority": 8, "extract_entity": True, "description": "Ukrywa kolumnę W trakcie"},
            {"module": "kanban", "action": "hide_column", "phrase": "ukryj do wykonania", "language": "pl", "priority": 7, "extract_entity": True, "description": "Ukrywa kolumnę Do wykonania"},
            {"module": "kanban", "action": "hide_column", "phrase": "kanban ukryj do wykonania", "language": "pl", "priority": 8, "extract_entity": True, "description": "Ukrywa kolumnę Do wykonania"},
            {"module": "kanban", "action": "hide_column", "phrase": "ukryj zakończone", "language": "pl", "priority": 7, "extract_entity": True, "description": "Ukrywa kolumnę Zakończone"},
            {"module": "kanban", "action": "hide_column", "phrase": "kanban ukryj zakończone", "language": "pl", "priority": 8, "extract_entity": True, "description": "Ukrywa kolumnę Zakończone"},
            {"module": "kanban", "action": "hide_column", "phrase": "ukryj do sprawdzenia", "language": "pl", "priority": 7, "extract_entity": True, "description": "Ukrywa kolumnę Do sprawdzenia"},
            {"module": "kanban", "action": "hide_column", "phrase": "kanban ukryj do sprawdzenia", "language": "pl", "priority": 8, "extract_entity": True, "description": "Ukrywa kolumnę Do sprawdzenia"},
            {"module": "kanban", "action": "hide_column", "phrase": "ukryj wstrzymane", "language": "pl", "priority": 7, "extract_entity": True, "description": "Ukrywa kolumnę Wstrzymane"},
            {"module": "kanban", "action": "hide_column", "phrase": "kanban ukryj wstrzymane", "language": "pl", "priority": 8, "extract_entity": True, "description": "Ukrywa kolumnę Wstrzymane"},
            # English - Open
            {"module": "kanban", "action": "open", "phrase": "open kanban", "language": "en", "priority": 7, "extract_entity": False, "description": "Opens kanban view"},
            {"module": "kanban", "action": "open", "phrase": "kanban", "language": "en", "priority": 5, "extract_entity": False, "description": "Opens kanban view"},
            # English - Show all
            {"module": "kanban", "action": "show_all", "phrase": "show all", "language": "en", "priority": 6, "extract_entity": False, "description": "Shows all columns"},
            {"module": "kanban", "action": "show_all", "phrase": "kanban show all", "language": "en", "priority": 7, "extract_entity": False, "description": "Shows all columns"},
            # English - Show/Hide columns (przykładowe)
            {"module": "kanban", "action": "show_column", "phrase": "show in progress", "language": "en", "priority": 7, "extract_entity": True, "description": "Shows In Progress column"},
            {"module": "kanban", "action": "hide_column", "phrase": "hide in progress", "language": "en", "priority": 7, "extract_entity": True, "description": "Hides In Progress column"},
            
            # === SETTINGS MODULE ===
            # Polish
            {"module": "settings", "action": "open", "phrase": "otwórz ustawienia", "language": "pl", "priority": 6, "extract_entity": False, "description": "Otwiera panel ustawień"},
            {"module": "settings", "action": "open", "phrase": "pokaż ustawienia", "language": "pl", "priority": 6, "extract_entity": False, "description": "Otwiera panel ustawień"},
            # English
            {"module": "settings", "action": "open", "phrase": "open settings", "language": "en", "priority": 6, "extract_entity": False, "description": "Opens settings panel"},
        ]


__all__ = ['AssistantDatabase', 'AssistantPhrase']
