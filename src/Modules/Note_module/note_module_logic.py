"""
Note Module Logic - Zarządzanie notatkami z zagnieżdżaniem
Obsługuje tworzenie, edycję, usuwanie i nawigację po zagnieżdżonych notatkach
"""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any
from uuid import uuid4

from src.config import LOCAL_DB_DIR


class NoteDatabase:
    """Manager lokalnej bazy SQLite dla notatek"""
    
    def __init__(self, user_id: str = "default"):
        """
        Inicjalizacja bazy danych notatek
        
        Args:
            user_id: ID użytkownika (domyślnie "default" dla trybu offline)
        """
        self.user_id = user_id
        self.db_path = LOCAL_DB_DIR / 'notes.db'
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Tworzy połączenie z bazą danych"""
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row  # Wyniki jako słowniki
        return conn
    
    def _init_database(self):
        """Inicjalizuje strukturę bazy danych"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Tabela notatek z obsługą zagnieżdżania
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    parent_id TEXT,
                    title TEXT NOT NULL,
                    content TEXT,
                    color TEXT DEFAULT '#e3f2fd',
                    sort_order INTEGER DEFAULT 0,
                    is_favorite BOOLEAN DEFAULT 0,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    deleted_at TEXT,
                    version INTEGER DEFAULT 1,
                    synced_at TEXT,
                    server_id TEXT,
                    FOREIGN KEY (parent_id) REFERENCES notes (id) ON DELETE CASCADE
                )
            """)
            
            # Tabela hiperłączy (zaznaczony tekst → podnotatka)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS note_links (
                    id TEXT PRIMARY KEY,
                    source_note_id TEXT NOT NULL,
                    target_note_id TEXT NOT NULL,
                    link_text TEXT NOT NULL,
                    start_position INTEGER NOT NULL,
                    end_position INTEGER NOT NULL,
                    created_at TEXT NOT NULL,
                    server_id TEXT,
                    synced_at TEXT,
                    FOREIGN KEY (source_note_id) REFERENCES notes (id) ON DELETE CASCADE,
                    FOREIGN KEY (target_note_id) REFERENCES notes (id) ON DELETE CASCADE
                )
            """)
            
            # Tabela kolejki synchronizacji (offline operations)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sync_queue (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    operation_type TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    entity_id TEXT NOT NULL,
                    data TEXT,
                    created_at TEXT NOT NULL,
                    retry_count INTEGER DEFAULT 0,
                    last_error TEXT,
                    status TEXT DEFAULT 'pending'
                )
            """)
            
            # Indeksy dla szybkiego wyszukiwania
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_user 
                ON notes(user_id, deleted_at)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_parent 
                ON notes(parent_id, sort_order)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_links_source 
                ON note_links(source_note_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_queue_status
                ON sync_queue(status, created_at)
            """)
            
            # Migracja: dodaj nowe kolumny do istniejących tabel (jeśli nie istnieją)
            self._migrate_schema(cursor)
            
            conn.commit()
    
    def _migrate_schema(self, cursor):
        """Migracja schematu - dodaje nowe kolumny do istniejących tabel"""
        # Sprawdź kolumny w tabeli notes
        cursor.execute("PRAGMA table_info(notes)")
        existing_columns = {row[1] for row in cursor.fetchall()}
        
        # Dodaj brakujące kolumny do notes
        if 'version' not in existing_columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN version INTEGER DEFAULT 1")
        if 'synced_at' not in existing_columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN synced_at TEXT")
        if 'server_id' not in existing_columns:
            cursor.execute("ALTER TABLE notes ADD COLUMN server_id TEXT")
        
        # Sprawdź kolumny w tabeli note_links
        cursor.execute("PRAGMA table_info(note_links)")
        existing_link_columns = {row[1] for row in cursor.fetchall()}
        
        # Dodaj brakujące kolumny do note_links
        if 'server_id' not in existing_link_columns:
            cursor.execute("ALTER TABLE note_links ADD COLUMN server_id TEXT")
        if 'synced_at' not in existing_link_columns:
            cursor.execute("ALTER TABLE note_links ADD COLUMN synced_at TEXT")
    
    def create_note(self, title: str, content: str = "", parent_id: Optional[str] = None,
                    color: str = "#e3f2fd") -> str:
        """
        Tworzy nową notatkę
        
        Args:
            title: Tytuł notatki
            content: Treść notatki (HTML z formatowaniem)
            parent_id: ID notatki nadrzędnej (None = notatka główna)
            color: Kolor notatki w drzewie
            
        Returns:
            ID utworzonej notatki
        """
        note_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            # Znajdź maksymalny sort_order dla tego poziomu
            cursor.execute("""
                SELECT COALESCE(MAX(sort_order), -1) + 1
                FROM notes
                WHERE user_id = ? AND parent_id IS ?
            """, (self.user_id, parent_id))
            sort_order = cursor.fetchone()[0]
            
            cursor.execute("""
                INSERT INTO notes (
                    id, user_id, parent_id, title, content, color,
                    sort_order, is_favorite, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                note_id, self.user_id, parent_id, title, content, color,
                sort_order, False, now, now
            ))
            
            conn.commit()
        
        # Dodaj do kolejki synchronizacji
        self.add_to_sync_queue('create', 'note', note_id)
        
        return note_id
    
    def get_note(self, note_id: str) -> Optional[Dict[str, Any]]:
        """Pobiera notatkę po ID"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notes
                WHERE id = ? AND deleted_at IS NULL
            """, (note_id,))
            
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_notes(self, include_deleted: bool = False) -> List[Dict[str, Any]]:
        """Pobiera wszystkie notatki użytkownika"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            query = "SELECT * FROM notes WHERE user_id = ?"
            params = [self.user_id]
            
            if not include_deleted:
                query += " AND deleted_at IS NULL"
            
            query += " ORDER BY parent_id NULLS FIRST, sort_order, title"
            
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
    
    def get_children(self, parent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Pobiera podnotatki dla danej notatki"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notes
                WHERE user_id = ? AND parent_id IS ? AND deleted_at IS NULL
                ORDER BY sort_order, title
            """, (self.user_id, parent_id))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def update_note(self, note_id: str, **kwargs) -> bool:
        """
        Aktualizuje notatkę
        
        Args:
            note_id: ID notatki
            **kwargs: Pola do aktualizacji (title, content, color, is_favorite, etc.)
            
        Returns:
            True jeśli sukces
        """
        if not kwargs:
            return False
        
        # Automatycznie aktualizuj updated_at
        kwargs['updated_at'] = datetime.utcnow().isoformat()
        
        # Buduj zapytanie SQL
        set_clause = ", ".join([f"{key} = ?" for key in kwargs.keys()])
        values = list(kwargs.values()) + [note_id]
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(f"""
                UPDATE notes SET {set_clause}
                WHERE id = ? AND deleted_at IS NULL
            """, values)
            
            success = cursor.rowcount > 0
            conn.commit()
        
        # Dodaj do kolejki synchronizacji jeśli update się udał
        if success:
            # Inkrementuj wersję
            self.increment_note_version(note_id)
            self.add_to_sync_queue('update', 'note', note_id)
        
        return success
    
    def delete_note(self, note_id: str, soft: bool = True) -> bool:
        """
        Usuwa notatkę (i wszystkie podnotatki)
        
        Args:
            note_id: ID notatki
            soft: True = soft delete (deleted_at), False = hard delete
            
        Returns:
            True jeśli sukces
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            if soft:
                # Soft delete - oznacz jako usunięte (kaskadowo dzieci)
                now = datetime.utcnow().isoformat()
                
                # Pobierz wszystkie ID notatek do usunięcia (rekurencyjnie)
                note_ids = self._get_all_descendant_ids(note_id)
                note_ids.append(note_id)
                
                placeholders = ",".join(["?" for _ in note_ids])
                cursor.execute(f"""
                    UPDATE notes
                    SET deleted_at = ?
                    WHERE id IN ({placeholders})
                """, [now] + note_ids)
            else:
                # Hard delete
                cursor.execute("DELETE FROM notes WHERE id = ?", (note_id,))
            
            success = cursor.rowcount > 0
            conn.commit()
        
        # Dodaj do kolejki synchronizacji
        if success:
            self.add_to_sync_queue('delete', 'note', note_id)
        
        return success
    
    def _get_all_descendant_ids(self, parent_id: str) -> List[str]:
        """Rekurencyjnie pobiera wszystkie ID potomków"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT id FROM notes WHERE parent_id = ?
            """, (parent_id,))
            
            children = [row['id'] for row in cursor.fetchall()]
            
            all_descendants = children.copy()
            for child_id in children:
                all_descendants.extend(self._get_all_descendant_ids(child_id))
            
            return all_descendants
    
    def create_link(self, source_note_id: str, target_note_id: str,
                   link_text: str, start_pos: int, end_pos: int) -> str:
        """
        Tworzy hiperłącze z zaznaczonego tekstu do podnotatki
        
        Args:
            source_note_id: ID notatki źródłowej
            target_note_id: ID notatki docelowej
            link_text: Zaznaczony tekst
            start_pos: Pozycja początkowa w tekście
            end_pos: Pozycja końcowa w tekście
            
        Returns:
            ID utworzonego linku
        """
        link_id = str(uuid4())
        now = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO note_links (
                    id, source_note_id, target_note_id, link_text,
                    start_position, end_position, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                link_id, source_note_id, target_note_id, link_text,
                start_pos, end_pos, now
            ))
            
            conn.commit()
        
        # Dodaj do kolejki synchronizacji
        self.add_to_sync_queue('create', 'link', link_id)
        
        return link_id
    
    def get_links_for_note(self, source_note_id: str) -> List[Dict[str, Any]]:
        """Pobiera wszystkie linki dla danej notatki"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM note_links
                WHERE source_note_id = ?
                ORDER BY start_position
            """, (source_note_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def delete_link(self, link_id: str) -> bool:
        """Usuwa hiperłącze"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM note_links WHERE id = ?", (link_id,))
            conn.commit()
            return cursor.rowcount > 0
    
    def move_note(self, note_id: str, new_parent_id: Optional[str] = None) -> bool:
        """
        Przenosi notatkę do innego rodzica
        
        Args:
            note_id: ID przenoszonej notatki
            new_parent_id: ID nowego rodzica (None = przenieś na górny poziom)
            
        Returns:
            True jeśli sukces
        """
        return self.update_note(note_id, parent_id=new_parent_id)
    
    def reorder_notes(self, note_ids: List[str]) -> bool:
        """
        Zmienia kolejność notatek na tym samym poziomie
        
        Args:
            note_ids: Lista ID w nowej kolejności
            
        Returns:
            True jeśli sukces
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            
            for index, note_id in enumerate(note_ids):
                cursor.execute("""
                    UPDATE notes SET sort_order = ?
                    WHERE id = ?
                """, (index, note_id))
            
            conn.commit()
            return True
    
    def search_notes(self, query: str) -> List[Dict[str, Any]]:
        """
        Wyszukuje notatki zawierające podany tekst
        
        Args:
            query: Tekst do wyszukania
            
        Returns:
            Lista znalezionych notatek
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            search_pattern = f"%{query}%"
            
            cursor.execute("""
                SELECT * FROM notes
                WHERE user_id = ? 
                  AND deleted_at IS NULL
                  AND (title LIKE ? OR content LIKE ?)
                ORDER BY updated_at DESC
            """, (self.user_id, search_pattern, search_pattern))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_favorites(self) -> List[Dict[str, Any]]:
        """Pobiera ulubione notatki"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notes
                WHERE user_id = ? AND is_favorite = 1 AND deleted_at IS NULL
                ORDER BY updated_at DESC
            """, (self.user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_recent_notes(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Pobiera ostatnio edytowane notatki"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notes
                WHERE user_id = ? AND deleted_at IS NULL
                ORDER BY updated_at DESC
                LIMIT ?
            """, (self.user_id, limit))
            
            return [dict(row) for row in cursor.fetchall()]
    
    # =============================================================================
    # SYNCHRONIZATION METHODS
    # =============================================================================
    
    def add_to_sync_queue(self, operation_type: str, entity_type: str, 
                          entity_id: str, data: Optional[Dict] = None) -> int:
        """
        Dodaje operację do kolejki synchronizacji
        
        Args:
            operation_type: Typ operacji ('create', 'update', 'delete')
            entity_type: Typ encji ('note', 'link')
            entity_id: ID encji (local_id)
            data: Dodatkowe dane (opcjonalne)
            
        Returns:
            ID wpisu w kolejce
        """
        now = datetime.utcnow().isoformat()
        data_json = json.dumps(data) if data else None
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sync_queue (
                    operation_type, entity_type, entity_id, data,
                    created_at, status
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (operation_type, entity_type, entity_id, data_json, now, 'pending'))
            
            queue_id = cursor.lastrowid or 0
            conn.commit()
            return queue_id
    
    def get_pending_sync_operations(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Pobiera oczekujące operacje synchronizacji
        
        Args:
            limit: Maksymalna liczba operacji
            
        Returns:
            Lista operacji do synchronizacji
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM sync_queue
                WHERE status = 'pending'
                ORDER BY created_at ASC
                LIMIT ?
            """, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_sync_operation_completed(self, queue_id: int):
        """Oznacza operację synchronizacji jako zakończoną"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_queue
                SET status = 'completed'
                WHERE id = ?
            """, (queue_id,))
            conn.commit()
    
    def mark_sync_operation_failed(self, queue_id: int, error: str):
        """
        Oznacza operację synchronizacji jako nieudaną
        
        Args:
            queue_id: ID operacji w kolejce
            error: Komunikat błędu
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE sync_queue
                SET status = 'failed', 
                    retry_count = retry_count + 1,
                    last_error = ?
                WHERE id = ?
            """, (error, queue_id))
            conn.commit()
    
    def clear_completed_sync_operations(self, older_than_days: int = 7):
        """
        Usuwa zakończone operacje synchronizacji starsze niż X dni
        
        Args:
            older_than_days: Liczba dni
        """
        from datetime import timedelta
        
        cutoff_date = datetime.utcnow() - timedelta(days=older_than_days)
        cutoff_date = cutoff_date.replace(
            hour=0, minute=0, second=0, microsecond=0
        ).isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                DELETE FROM sync_queue
                WHERE status = 'completed' AND created_at < ?
            """, (cutoff_date,))
            conn.commit()
    
    def mark_note_synced(self, local_id: str, server_id: str, version: int):
        """
        Oznacza notatkę jako zsynchronizowaną
        
        Args:
            local_id: UUID lokalne notatki
            server_id: UUID na serwerze
            version: Numer wersji po synchronizacji
        """
        now = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE notes
                SET server_id = ?,
                    version = ?,
                    synced_at = ?
                WHERE id = ?
            """, (server_id, version, now, local_id))
            conn.commit()
    
    def mark_link_synced(self, local_id: str, server_id: str):
        """
        Oznacza link jako zsynchronizowany
        
        Args:
            local_id: UUID lokalne linka
            server_id: UUID na serwerze
        """
        now = datetime.utcnow().isoformat()
        
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE note_links
                SET server_id = ?,
                    synced_at = ?
                WHERE id = ?
            """, (server_id, now, local_id))
            conn.commit()
    
    def get_unsynced_notes(self) -> List[Dict[str, Any]]:
        """Pobiera notatki, które nie zostały jeszcze zsynchronizowane"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM notes
                WHERE user_id = ? 
                  AND deleted_at IS NULL
                  AND (synced_at IS NULL OR updated_at > synced_at)
                ORDER BY created_at ASC
            """, (self.user_id,))
            
            return [dict(row) for row in cursor.fetchall()]
    
    def get_unsynced_links(self) -> List[Dict[str, Any]]:
        """Pobiera linki, które nie zostały jeszcze zsynchronizowane"""
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM note_links
                WHERE synced_at IS NULL
            """)
            
            return [dict(row) for row in cursor.fetchall()]
    
    def increment_note_version(self, note_id: str) -> int:
        """
        Inkrementuje wersję notatki (dla conflict resolution)
        
        Args:
            note_id: UUID notatki
            
        Returns:
            Nowa wersja
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE notes
                SET version = version + 1
                WHERE id = ?
            """, (note_id,))
            
            cursor.execute("""
                SELECT version FROM notes WHERE id = ?
            """, (note_id,))
            
            row = cursor.fetchone()
            conn.commit()
            
            return row[0] if row else 1


class NoteFormatter:
    """Klasa pomocnicza do formatowania tekstu w notatkach"""
    
    @staticmethod
    def apply_bold(html: str, start: int, end: int) -> str:
        """Aplikuje pogrubienie do zaznaczonego tekstu"""
        return NoteFormatter._wrap_with_tag(html, start, end, "b")
    
    @staticmethod
    def apply_italic(html: str, start: int, end: int) -> str:
        """Aplikuje kursywę do zaznaczonego tekstu"""
        return NoteFormatter._wrap_with_tag(html, start, end, "i")
    
    @staticmethod
    def apply_underline(html: str, start: int, end: int) -> str:
        """Aplikuje podkreślenie do zaznaczonego tekstu"""
        return NoteFormatter._wrap_with_tag(html, start, end, "u")
    
    @staticmethod
    def apply_strikethrough(html: str, start: int, end: int) -> str:
        """Aplikuje przekreślenie do zaznaczonego tekstu"""
        return NoteFormatter._wrap_with_tag(html, start, end, "s")
    
    @staticmethod
    def apply_color(html: str, start: int, end: int, color: str) -> str:
        """Aplikuje kolor tekstu"""
        return NoteFormatter._wrap_with_tag(
            html, start, end, "span", f'style="color: {color};"'
        )
    
    @staticmethod
    def apply_highlight(html: str, start: int, end: int, color: str) -> str:
        """Aplikuje podświetlenie tekstu"""
        return NoteFormatter._wrap_with_tag(
            html, start, end, "span", f'style="background-color: {color};"'
        )
    
    @staticmethod
    def apply_font_size(html: str, start: int, end: int, size: int) -> str:
        """Aplikuje rozmiar czcionki"""
        return NoteFormatter._wrap_with_tag(
            html, start, end, "span", f'style="font-size: {size}pt;"'
        )
    
    @staticmethod
    def _wrap_with_tag(html: str, start: int, end: int, tag: str, 
                      attributes: str = "") -> str:
        """
        Owija zaznaczony tekst w tag HTML
        
        Args:
            html: Oryginalny HTML
            start: Pozycja początkowa
            end: Pozycja końcowa
            tag: Nazwa tagu (np. "b", "i", "span")
            attributes: Atrybuty tagu (opcjonalne)
        """
        attr_str = f" {attributes}" if attributes else ""
        before = html[:start]
        selected = html[start:end]
        after = html[end:]
        
        return f"{before}<{tag}{attr_str}>{selected}</{tag}>{after}"
    
    @staticmethod
    def remove_formatting(html: str, start: int, end: int) -> str:
        """Usuwa wszystkie formatowanie z zaznaczonego tekstu"""
        import re
        
        before = html[:start]
        selected = html[start:end]
        after = html[end:]
        
        # Usuń wszystkie tagi HTML z zaznaczonego fragmentu
        plain_text = re.sub(r'<[^>]+>', '', selected)
        
        return f"{before}{plain_text}{after}"
