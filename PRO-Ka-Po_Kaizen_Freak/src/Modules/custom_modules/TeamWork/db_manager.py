"""
Moduł zarządzania bazą danych dla TeamWork.
Obsługuje połączenia i wykonywanie zapytań SQL.
"""

import sqlite3
from typing import Any, Optional
from pathlib import Path
from datetime import datetime


class DatabaseManager:
    """Menedżer połączeń i operacji na bazie danych SQLite."""

    def __init__(self, db_path: str = "teamwork.db") -> None:
        """
        Inicjalizuje menedżera bazy danych.
        
        Args:
            db_path: Ścieżka do pliku bazy danych SQLite
        """
        self.db_path = db_path
        self.connection: Optional[sqlite3.Connection] = None
        
    def connect(self) -> sqlite3.Connection:
        """
        Nawiązuje połączenie z bazą danych.
        
        Returns:
            Obiekt połączenia SQLite
        """
        if self.connection is None:
            self.connection = sqlite3.connect(self.db_path)
            self.connection.row_factory = sqlite3.Row  # Umożliwia dostęp do kolumn po nazwie
        return self.connection
    
    def close(self) -> None:
        """Zamyka połączenie z bazą danych."""
        if self.connection:
            self.connection.close()
            self.connection = None
    
    def execute_query(self, query: str, params: tuple = ()) -> list[sqlite3.Row]:
        """
        Wykonuje zapytanie SELECT i zwraca wyniki.
        
        Args:
            query: Zapytanie SQL
            params: Parametry zapytania (tuple)
            
        Returns:
            Lista wierszy wynikowych
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        return cursor.fetchall()
    
    def execute_update(self, query: str, params: tuple = ()) -> int:
        """
        Wykonuje zapytanie INSERT/UPDATE/DELETE.
        
        Args:
            query: Zapytanie SQL
            params: Parametry zapytania (tuple)
            
        Returns:
            ID ostatnio wstawionego wiersza (dla INSERT) lub liczba zmienionych wierszy
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.execute(query, params)
        conn.commit()
        return cursor.lastrowid if query.strip().upper().startswith("INSERT") else cursor.rowcount
    
    def execute_many(self, query: str, params_list: list[tuple]) -> int:
        """
        Wykonuje wiele operacji INSERT/UPDATE/DELETE.
        
        Args:
            query: Zapytanie SQL
            params_list: Lista tupli z parametrami
            
        Returns:
            Liczba zmienionych wierszy
        """
        conn = self.connect()
        cursor = conn.cursor()
        cursor.executemany(query, params_list)
        conn.commit()
        return cursor.rowcount
    
    def initialize_database(self, schema_file: str = "database_schema.sql") -> None:
        """
        Inicjalizuje bazę danych używając pliku ze schematem.
        
        Args:
            schema_file: Ścieżka do pliku SQL ze schematem
        """
        schema_path = Path(__file__).parent / schema_file
        
        if not schema_path.exists():
            raise FileNotFoundError(f"Plik schematu nie został znaleziony: {schema_path}")
        
        with open(schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        conn = self.connect()
        cursor = conn.cursor()
        cursor.executescript(schema_sql)
        conn.commit()
        
        print(f"Baza danych została zainicjalizowana: {self.db_path}")
    
    def __enter__(self):
        """Umożliwia użycie menedżera w bloku 'with'."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Automatycznie zamyka połączenie po wyjściu z bloku 'with'."""
        self.close()


# ============================================================================
# KLASY POMOCNICZE DO OPERACJI NA TABELACH
# ============================================================================

class UserManager:
    """Zarządzanie użytkownikami."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def create_user(self, email: str, first_name: str, last_name: str) -> int:
        """Tworzy nowego użytkownika."""
        query = "INSERT INTO users (email, first_name, last_name) VALUES (?, ?, ?)"
        return self.db.execute_update(query, (email, first_name, last_name))
    
    def get_all_users(self) -> list[sqlite3.Row]:
        """Pobiera wszystkich aktywnych użytkowników."""
        query = """
            SELECT user_id, email, first_name, last_name, created_at, is_active
            FROM users
            WHERE is_active = 1
            ORDER BY last_name, first_name
        """
        return self.db.execute_query(query)
    
    def find_user_by_email(self, email: str) -> Optional[sqlite3.Row]:
        """Znajduje użytkownika po emailu."""
        query = "SELECT user_id, email, first_name, last_name FROM users WHERE email = ? AND is_active = 1"
        results = self.db.execute_query(query, (email,))
        return results[0] if results else None
    
    def update_user(self, user_id: int, first_name: str, last_name: str) -> int:
        """Aktualizuje dane użytkownika."""
        query = "UPDATE users SET first_name = ?, last_name = ? WHERE user_id = ?"
        return self.db.execute_update(query, (first_name, last_name, user_id))
    
    def deactivate_user(self, user_id: int) -> int:
        """Dezaktywuje użytkownika (soft delete)."""
        query = "UPDATE users SET is_active = 0 WHERE user_id = ?"
        return self.db.execute_update(query, (user_id,))


class TeamManager:
    """Zarządzanie zespołami."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def create_team(self, team_name: str, description: str, created_by: int) -> int:
        """Tworzy nowy zespół."""
        query = "INSERT INTO teams (team_name, description, created_by) VALUES (?, ?, ?)"
        return self.db.execute_update(query, (team_name, description, created_by))
    
    def get_all_teams(self) -> list[sqlite3.Row]:
        """Pobiera wszystkie zespoły z liczbą członków."""
        query = """
            SELECT t.team_id, t.team_name, t.description, t.created_at,
                   u.first_name || ' ' || u.last_name AS created_by_name,
                   COUNT(tm.user_id) AS members_count
            FROM teams t
            LEFT JOIN users u ON t.created_by = u.user_id
            LEFT JOIN team_members tm ON t.team_id = tm.team_id
            GROUP BY t.team_id
            ORDER BY t.team_name
        """
        return self.db.execute_query(query)
    
    def add_team_member(self, team_id: int, user_id: int) -> int:
        """Dodaje członka do zespołu."""
        query = "INSERT INTO team_members (team_id, user_id) VALUES (?, ?)"
        return self.db.execute_update(query, (team_id, user_id))
    
    def remove_team_member(self, team_id: int, user_id: int) -> int:
        """Usuwa członka z zespołu."""
        query = "DELETE FROM team_members WHERE team_id = ? AND user_id = ?"
        return self.db.execute_update(query, (team_id, user_id))
    
    def get_team_members(self, team_id: int) -> list[sqlite3.Row]:
        """Pobiera członków zespołu."""
        query = """
            SELECT u.user_id, u.email, u.first_name, u.last_name, tm.added_at
            FROM team_members tm
            JOIN users u ON tm.user_id = u.user_id
            WHERE tm.team_id = ?
            ORDER BY u.last_name, u.first_name
        """
        return self.db.execute_query(query, (team_id,))


class GroupManager:
    """Zarządzanie grupami roboczymi."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def create_group(self, group_name: str, description: str, created_by: int, team_id: Optional[int] = None) -> int:
        """Tworzy nową grupę roboczą."""
        query = "INSERT INTO work_groups (group_name, description, team_id, created_by) VALUES (?, ?, ?, ?)"
        return self.db.execute_update(query, (group_name, description, team_id, created_by))
    
    def get_user_groups(self, user_id: int) -> list[sqlite3.Row]:
        """Pobiera grupy użytkownika."""
        query = """
            SELECT wg.group_id, wg.group_name, wg.description, wg.created_at,
                   COUNT(DISTINCT gm.user_id) AS members_count
            FROM work_groups wg
            LEFT JOIN group_members gm ON wg.group_id = gm.group_id
            WHERE wg.is_active = 1 
              AND (wg.created_by = ? OR gm.user_id = ?)
            GROUP BY wg.group_id
            ORDER BY wg.group_name
        """
        return self.db.execute_query(query, (user_id, user_id))
    
    def add_group_member(self, group_id: int, user_id: int, role: str = 'member') -> int:
        """Dodaje członka do grupy."""
        query = "INSERT INTO group_members (group_id, user_id, role) VALUES (?, ?, ?)"
        return self.db.execute_update(query, (group_id, user_id, role))
    
    def remove_group_member(self, group_id: int, user_id: int) -> int:
        """Usuwa członka z grupy."""
        query = "DELETE FROM group_members WHERE group_id = ? AND user_id = ?"
        return self.db.execute_update(query, (group_id, user_id))
    
    def is_member(self, group_id: int, user_id: int) -> bool:
        """Sprawdza czy użytkownik jest członkiem grupy."""
        query = "SELECT COUNT(*) AS is_member FROM group_members WHERE group_id = ? AND user_id = ?"
        result = self.db.execute_query(query, (group_id, user_id))
        return result[0]['is_member'] > 0 if result else False


class InvitationManager:
    """Zarządzanie zaproszeniami."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def send_invitation(self, group_id: int, invited_email: str, invited_by: int) -> int:
        """Wysyła zaproszenie do grupy."""
        query = "INSERT INTO group_invitations (group_id, invited_email, invited_by) VALUES (?, ?, ?)"
        return self.db.execute_update(query, (group_id, invited_email, invited_by))
    
    def get_user_invitations(self, email: str) -> list[sqlite3.Row]:
        """Pobiera oczekujące zaproszenia dla użytkownika."""
        query = """
            SELECT gi.invitation_id, gi.invitation_status, gi.invited_at,
                   wg.group_id, wg.group_name, wg.description,
                   u.first_name || ' ' || u.last_name AS invited_by_name
            FROM group_invitations gi
            JOIN work_groups wg ON gi.group_id = wg.group_id
            JOIN users u ON gi.invited_by = u.user_id
            WHERE gi.invited_email = ? 
              AND gi.invitation_status = 'pending'
            ORDER BY gi.invited_at DESC
        """
        return self.db.execute_query(query, (email,))
    
    def accept_invitation(self, invitation_id: int) -> int:
        """Akceptuje zaproszenie."""
        query = "UPDATE group_invitations SET invitation_status = 'accepted', responded_at = CURRENT_TIMESTAMP WHERE invitation_id = ?"
        return self.db.execute_update(query, (invitation_id,))
    
    def reject_invitation(self, invitation_id: int) -> int:
        """Odrzuca zaproszenie."""
        query = "UPDATE group_invitations SET invitation_status = 'rejected', responded_at = CURRENT_TIMESTAMP WHERE invitation_id = ?"
        return self.db.execute_update(query, (invitation_id,))


class TopicManager:
    """Zarządzanie wątkami."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def create_topic(self, group_id: int, topic_name: str, created_by: int) -> int:
        """Tworzy nowy wątek."""
        query = "INSERT INTO topics (group_id, topic_name, created_by) VALUES (?, ?, ?)"
        return self.db.execute_update(query, (group_id, topic_name, created_by))
    
    def get_group_topics(self, group_id: int) -> list[sqlite3.Row]:
        """Pobiera wątki z grupy."""
        query = """
            SELECT t.topic_id, t.topic_name, t.created_at,
                   u.first_name || ' ' || u.last_name AS created_by_name,
                   COUNT(DISTINCT m.message_id) AS messages_count,
                   MAX(m.created_at) AS last_activity
            FROM topics t
            JOIN users u ON t.created_by = u.user_id
            LEFT JOIN messages m ON t.topic_id = m.topic_id
            WHERE t.group_id = ? AND t.is_active = 1
            GROUP BY t.topic_id
            ORDER BY last_activity DESC, t.created_at DESC
        """
        return self.db.execute_query(query, (group_id,))


class MessageManager:
    """Zarządzanie wiadomościami."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def add_message(self, topic_id: int, user_id: int, content: str, 
                   background_color: str = '#FFFFFF', is_important: bool = False) -> int:
        """Dodaje wiadomość do wątku."""
        query = "INSERT INTO messages (topic_id, user_id, content, background_color, is_important) VALUES (?, ?, ?, ?, ?)"
        return self.db.execute_update(query, (topic_id, user_id, content, background_color, int(is_important)))
    
    def get_topic_messages(self, topic_id: int) -> list[sqlite3.Row]:
        """Pobiera wiadomości z wątku."""
        query = """
            SELECT m.message_id, m.content, m.background_color, m.is_important,
                   m.created_at, m.edited_at,
                   u.user_id, u.first_name || ' ' || u.last_name AS author_name
            FROM messages m
            JOIN users u ON m.user_id = u.user_id
            WHERE m.topic_id = ?
            ORDER BY m.created_at ASC
        """
        return self.db.execute_query(query, (topic_id,))
    
    def toggle_important(self, message_id: int, is_important: bool) -> int:
        """Oznacza wiadomość jako ważną/nieważną."""
        query = "UPDATE messages SET is_important = ? WHERE message_id = ?"
        return self.db.execute_update(query, (int(is_important), message_id))


class TaskManager:
    """Zarządzanie zadaniami."""
    
    def __init__(self, db: DatabaseManager):
        self.db = db
    
    def create_task(self, topic_id: int, task_subject: str, task_description: str,
                   assigned_to: Optional[int], created_by: int, due_date: Optional[str],
                   is_important: bool = False) -> int:
        """Tworzy nowe zadanie."""
        query = """
            INSERT INTO tasks (topic_id, task_subject, task_description, assigned_to, created_by, due_date, is_important)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """
        return self.db.execute_update(query, (topic_id, task_subject, task_description, assigned_to, created_by, due_date, int(is_important)))
    
    def get_topic_tasks(self, topic_id: int) -> list[sqlite3.Row]:
        """Pobiera zadania z wątku."""
        query = """
            SELECT t.task_id, t.task_subject, t.task_description, t.due_date, t.completed,
                   t.created_at, t.completed_at, t.is_important,
                   u_created.first_name || ' ' || u_created.last_name AS created_by_name,
                   u_assigned.first_name || ' ' || u_assigned.last_name AS assigned_to_name,
                   u_completed.first_name || ' ' || u_completed.last_name AS completed_by_name
            FROM tasks t
            JOIN users u_created ON t.created_by = u_created.user_id
            LEFT JOIN users u_assigned ON t.assigned_to = u_assigned.user_id
            LEFT JOIN users u_completed ON t.completed_by = u_completed.user_id
            WHERE t.topic_id = ?
            ORDER BY t.completed ASC, t.due_date ASC, t.created_at DESC
        """
        return self.db.execute_query(query, (topic_id,))
    
    def complete_task(self, task_id: int, completed_by: int) -> int:
        """Oznacza zadanie jako ukończone."""
        query = "UPDATE tasks SET completed = 1, completed_by = ?, completed_at = CURRENT_TIMESTAMP WHERE task_id = ?"
        return self.db.execute_update(query, (completed_by, task_id))
    
    def uncomplete_task(self, task_id: int) -> int:
        """Oznacza zadanie jako nieukończone."""
        query = "UPDATE tasks SET completed = 0, completed_by = NULL, completed_at = NULL WHERE task_id = ?"
        return self.db.execute_update(query, (task_id,))
    
    def toggle_important(self, task_id: int, is_important: bool) -> int:
        """Oznacza zadanie jako ważne/nieważne."""
        query = "UPDATE tasks SET is_important = ? WHERE task_id = ?"
        return self.db.execute_update(query, (int(is_important), task_id))


# ============================================================================
# PRZYKŁAD UŻYCIA
# ============================================================================

if __name__ == "__main__":
    # Inicjalizacja bazy danych
    db = DatabaseManager("teamwork_test.db")
    
    try:
        # Utwórz schemat
        db.initialize_database()
        
        # Przykładowe operacje
        user_mgr = UserManager(db)
        team_mgr = TeamManager(db)
        
        # Dodaj użytkowników
        user1_id = user_mgr.create_user("jan.kowalski@example.com", "Jan", "Kowalski")
        user2_id = user_mgr.create_user("anna.nowak@example.com", "Anna", "Nowak")
        
        print(f"Utworzono użytkowników: {user1_id}, {user2_id}")
        
        # Utwórz zespół
        team_id = team_mgr.create_team("Zespół Rozwoju", "Główny zespół programistów", user1_id)
        team_mgr.add_team_member(team_id, user1_id)
        team_mgr.add_team_member(team_id, user2_id)
        
        print(f"Utworzono zespół: {team_id}")
        
        # Pobierz wszystkich użytkowników
        users = user_mgr.get_all_users()
        print("\nUżytkownicy:")
        for user in users:
            print(f"  - {user['first_name']} {user['last_name']} ({user['email']})")
        
    finally:
        db.close()
