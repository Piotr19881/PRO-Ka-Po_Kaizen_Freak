"""
TeamWork Sync Manager - Phase 5
Synchronizacja danych między lokalną bazą SQLite a API
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from loguru import logger


class SyncManager:
    """
    Zarządza synchronizacją danych TeamWork między lokalną bazą a API.
    
    Obsługuje:
    - Push lokalnych zmian do API
    - Pull zmian z API do lokalnej bazy
    - Wykrywanie i rozwiązywanie konfliktów
    - Metadane synchronizacji
    """
    
    def __init__(self, db_path: str, api_client):
        """
        Args:
            db_path: Ścieżka do lokalnej bazy SQLite
            api_client: TeamWorkAPIClient dla komunikacji z API
        """
        self.db_path = db_path
        self.api_client = api_client
        self.conn: Optional[sqlite3.Connection] = None
    
    def connect(self):
        """Połącz z bazą danych"""
        if not self.conn:
            self.conn = sqlite3.connect(self.db_path)
            self.conn.row_factory = sqlite3.Row
            logger.info(f"[SyncManager] Connected to database: {self.db_path}")
    
    def disconnect(self):
        """Rozłącz z bazą danych"""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.info("[SyncManager] Disconnected from database")
    
    def __enter__(self):
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()
    
    # =========================================================================
    # TASK 5.2: SYNC PUSH - Upload lokalnych zmian do API
    # =========================================================================
    
    def push_all(self) -> Dict[str, any]:
        """
        Wysyła wszystkie lokalne zmiany do API.
        
        Returns:
            Słownik z wynikami synchronizacji dla każdego typu encji
        """
        results = {
            'groups': {'pushed': 0, 'errors': 0},
            'topics': {'pushed': 0, 'errors': 0},
            'messages': {'pushed': 0, 'errors': 0},
            'tasks': {'pushed': 0, 'errors': 0},
            'files': {'pushed': 0, 'errors': 0}
        }
        
        try:
            # Synchronizuj w odpowiedniej kolejności (zależności)
            results['groups'] = self.push_groups()
            results['topics'] = self.push_topics()
            results['messages'] = self.push_messages()
            results['tasks'] = self.push_tasks()
            # Pliki nie wymagają push (upload przez FileUploadDialog)
            
            # Aktualizuj metadane
            self._update_sync_metadata('push')
            
            logger.success(f"[SyncManager] Push completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"[SyncManager] Push failed: {e}")
            raise
    
    def push_groups(self) -> Dict[str, int]:
        """Synchronizuj grupy"""
        cursor = self.conn.cursor()
        
        # Znajdź grupy do wysłania (modified_locally=1 lub sync_status='pending')
        cursor.execute("""
            SELECT * FROM work_groups 
            WHERE modified_locally = 1 OR sync_status = 'pending'
        """)
        
        groups = cursor.fetchall()
        pushed = 0
        errors = 0
        
        for group in groups:
            try:
                group_data = {
                    'group_name': group['group_name'],
                    'description': group['description'],
                    'is_active': group['is_active']
                }
                
                if group['server_id']:
                    # UPDATE - grupa już istnieje na serwerze
                    response = self.api_client.update_group(group['server_id'], group_data)
                else:
                    # CREATE - nowa grupa
                    response = self.api_client.create_group(group_data)
                
                if response.success:
                    server_data = response.data
                    # Aktualizuj lokalne metadane
                    cursor.execute("""
                        UPDATE work_groups 
                        SET server_id = ?,
                            last_synced = ?,
                            sync_status = 'synced',
                            modified_locally = 0,
                            version = ?
                        WHERE group_id = ?
                    """, (
                        server_data.get('group_id'),
                        datetime.now(),
                        server_data.get('version', group['version']),
                        group['group_id']
                    ))
                    pushed += 1
                else:
                    logger.error(f"[SyncManager] Failed to push group {group['group_id']}: {response.error}")
                    cursor.execute("""
                        UPDATE work_groups 
                        SET sync_status = 'error'
                        WHERE group_id = ?
                    """, (group['group_id'],))
                    errors += 1
                    
            except Exception as e:
                logger.error(f"[SyncManager] Error pushing group {group['group_id']}: {e}")
                errors += 1
        
        self.conn.commit()
        return {'pushed': pushed, 'errors': errors}
    
    def push_topics(self) -> Dict[str, int]:
        """Synchronizuj tematy"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM topics 
            WHERE modified_locally = 1 OR sync_status = 'pending'
        """)
        
        topics = cursor.fetchall()
        pushed = 0
        errors = 0
        
        for topic in topics:
            try:
                # Znajdź server_id grupy
                cursor.execute("SELECT server_id FROM work_groups WHERE group_id = ?", (topic['group_id'],))
                group_row = cursor.fetchone()
                
                if not group_row or not group_row['server_id']:
                    logger.warning(f"[SyncManager] Cannot push topic {topic['topic_id']} - parent group not synced")
                    continue
                
                topic_data = {
                    'group_id': group_row['server_id'],
                    'topic_name': topic['topic_name'],
                    'is_active': topic['is_active']
                }
                
                if topic['server_id']:
                    # UPDATE
                    response = self.api_client.update_topic(topic['server_id'], topic_data)
                else:
                    # CREATE
                    response = self.api_client.create_topic(topic_data)
                
                if response.success:
                    server_data = response.data
                    cursor.execute("""
                        UPDATE topics 
                        SET server_id = ?,
                            last_synced = ?,
                            sync_status = 'synced',
                            modified_locally = 0,
                            version = ?
                        WHERE topic_id = ?
                    """, (
                        server_data.get('topic_id'),
                        datetime.now(),
                        server_data.get('version', topic['version']),
                        topic['topic_id']
                    ))
                    pushed += 1
                else:
                    logger.error(f"[SyncManager] Failed to push topic {topic['topic_id']}: {response.error}")
                    cursor.execute("UPDATE topics SET sync_status = 'error' WHERE topic_id = ?", (topic['topic_id'],))
                    errors += 1
                    
            except Exception as e:
                logger.error(f"[SyncManager] Error pushing topic {topic['topic_id']}: {e}")
                errors += 1
        
        self.conn.commit()
        return {'pushed': pushed, 'errors': errors}
    
    def push_messages(self) -> Dict[str, int]:
        """Synchronizuj wiadomości"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM messages 
            WHERE modified_locally = 1 OR sync_status = 'pending'
        """)
        
        messages = cursor.fetchall()
        pushed = 0
        errors = 0
        
        for message in messages:
            try:
                # Znajdź server_id topicu
                cursor.execute("SELECT server_id FROM topics WHERE topic_id = ?", (message['topic_id'],))
                topic_row = cursor.fetchone()
                
                if not topic_row or not topic_row['server_id']:
                    logger.warning(f"[SyncManager] Cannot push message {message['message_id']} - parent topic not synced")
                    continue
                
                message_data = {
                    'topic_id': topic_row['server_id'],
                    'content': message['content'],
                    'background_color': message['background_color'],
                    'is_important': message['is_important']
                }
                
                if message['server_id']:
                    # UPDATE - wiadomości raczej nie są edytowane, ale obsłużmy
                    response = self.api_client.update_message(message['server_id'], message_data)
                else:
                    # CREATE
                    response = self.api_client.create_message(message_data)
                
                if response.success:
                    server_data = response.data
                    cursor.execute("""
                        UPDATE messages 
                        SET server_id = ?,
                            last_synced = ?,
                            sync_status = 'synced',
                            modified_locally = 0,
                            version = ?
                        WHERE message_id = ?
                    """, (
                        server_data.get('message_id'),
                        datetime.now(),
                        server_data.get('version', message['version']),
                        message['message_id']
                    ))
                    pushed += 1
                else:
                    logger.error(f"[SyncManager] Failed to push message {message['message_id']}: {response.error}")
                    cursor.execute("UPDATE messages SET sync_status = 'error' WHERE message_id = ?", (message['message_id'],))
                    errors += 1
                    
            except Exception as e:
                logger.error(f"[SyncManager] Error pushing message {message['message_id']}: {e}")
                errors += 1
        
        self.conn.commit()
        return {'pushed': pushed, 'errors': errors}
    
    def push_tasks(self) -> Dict[str, int]:
        """Synchronizuj zadania"""
        cursor = self.conn.cursor()
        
        cursor.execute("""
            SELECT * FROM tasks 
            WHERE modified_locally = 1 OR sync_status = 'pending'
        """)
        
        tasks = cursor.fetchall()
        pushed = 0
        errors = 0
        
        for task in tasks:
            try:
                # Znajdź server_id topicu
                cursor.execute("SELECT server_id FROM topics WHERE topic_id = ?", (task['topic_id'],))
                topic_row = cursor.fetchone()
                
                if not topic_row or not topic_row['server_id']:
                    logger.warning(f"[SyncManager] Cannot push task {task['task_id']} - parent topic not synced")
                    continue
                
                task_data = {
                    'topic_id': topic_row['server_id'],
                    'task_subject': task['task_subject'],
                    'task_description': task['task_description'],
                    'assigned_to': task['assigned_to'],
                    'due_date': task['due_date'],
                    'is_important': task['is_important']
                }
                
                if task['server_id']:
                    # UPDATE
                    response = self.api_client.update_task(task['server_id'], task_data)
                else:
                    # CREATE
                    response = self.api_client.create_task(task_data)
                
                if response.success:
                    server_data = response.data
                    cursor.execute("""
                        UPDATE tasks 
                        SET server_id = ?,
                            last_synced = ?,
                            sync_status = 'synced',
                            modified_locally = 0,
                            version = ?
                        WHERE task_id = ?
                    """, (
                        server_data.get('task_id'),
                        datetime.now(),
                        server_data.get('version', task['version']),
                        task['task_id']
                    ))
                    pushed += 1
                else:
                    logger.error(f"[SyncManager] Failed to push task {task['task_id']}: {response.error}")
                    cursor.execute("UPDATE tasks SET sync_status = 'error' WHERE task_id = ?", (task['task_id'],))
                    errors += 1
                    
            except Exception as e:
                logger.error(f"[SyncManager] Error pushing task {task['task_id']}: {e}")
                errors += 1
        
        self.conn.commit()
        return {'pushed': pushed, 'errors': errors}
    
    # =========================================================================
    # TASK 5.3: SYNC PULL - Pobierz zmiany z API
    # =========================================================================
    
    def pull_all(self) -> Dict[str, any]:
        """
        Pobiera wszystkie zmiany z API do lokalnej bazy.
        
        Returns:
            Słownik z wynikami synchronizacji dla każdego typu encji
        """
        results = {
            'groups': {'pulled': 0, 'conflicts': 0},
            'topics': {'pulled': 0, 'conflicts': 0},
            'messages': {'pulled': 0, 'conflicts': 0},
            'tasks': {'pulled': 0, 'conflicts': 0},
            'files': {'pulled': 0, 'conflicts': 0}
        }
        
        try:
            # Synchronizuj w odpowiedniej kolejności
            results['groups'] = self.pull_groups()
            results['topics'] = self.pull_topics()
            results['messages'] = self.pull_messages()
            results['tasks'] = self.pull_tasks()
            results['files'] = self.pull_files()
            
            # Aktualizuj metadane
            self._update_sync_metadata('pull')
            
            logger.success(f"[SyncManager] Pull completed: {results}")
            return results
            
        except Exception as e:
            logger.error(f"[SyncManager] Pull failed: {e}")
            raise
    
    def pull_groups(self) -> Dict[str, int]:
        """Pobierz grupy z API"""
        cursor = self.conn.cursor()
        
        response = self.api_client.get_user_groups()
        if not response.success:
            logger.error(f"[SyncManager] Failed to pull groups: {response.error}")
            return {'pulled': 0, 'conflicts': 0}
        
        groups = response.data or []
        pulled = 0
        conflicts = 0
        
        for group_data in groups:
            server_id = group_data.get('group_id')
            
            # Sprawdź czy grupa już istnieje lokalnie
            cursor.execute("SELECT * FROM work_groups WHERE server_id = ?", (server_id,))
            local_group = cursor.fetchone()
            
            if local_group:
                # Grupa istnieje - sprawdź konflikty (Task 5.4)
                if self._detect_conflict(local_group, group_data):
                    self._handle_conflict('groups', local_group, group_data)
                    conflicts += 1
                else:
                    # Aktualizuj dane
                    cursor.execute("""
                        UPDATE work_groups 
                        SET group_name = ?,
                            description = ?,
                            is_active = ?,
                            last_synced = ?,
                            sync_status = 'synced',
                            version = ?
                        WHERE group_id = ?
                    """, (
                        group_data.get('group_name'),
                        group_data.get('description'),
                        group_data.get('is_active'),
                        datetime.now(),
                        group_data.get('version', 1),
                        local_group['group_id']
                    ))
                    pulled += 1
            else:
                # Nowa grupa - dodaj
                cursor.execute("""
                    INSERT INTO work_groups (
                        server_id, group_name, description, is_active, owner_id,
                        last_synced, sync_status, version, modified_locally
                    ) VALUES (?, ?, ?, ?, ?, ?, 'synced', ?, 0)
                """, (
                    server_id,
                    group_data.get('group_name'),
                    group_data.get('description'),
                    group_data.get('is_active'),
                    group_data.get('owner_id'),
                    datetime.now(),
                    group_data.get('version', 1)
                ))
                pulled += 1
        
        self.conn.commit()
        return {'pulled': pulled, 'conflicts': conflicts}
    
    def pull_topics(self) -> Dict[str, int]:
        """Pobierz tematy dla wszystkich grup"""
        cursor = self.conn.cursor()
        
        # Pobierz wszystkie grupy z server_id
        cursor.execute("SELECT server_id FROM work_groups WHERE server_id IS NOT NULL")
        groups = cursor.fetchall()
        
        total_pulled = 0
        total_conflicts = 0
        
        for group in groups:
            response = self.api_client.get_group_topics(group['server_id'])
            if not response.success:
                continue
            
            topics = response.data or []
            
            for topic_data in topics:
                server_id = topic_data.get('topic_id')
                
                cursor.execute("SELECT * FROM topics WHERE server_id = ?", (server_id,))
                local_topic = cursor.fetchone()
                
                if local_topic:
                    if self._detect_conflict(local_topic, topic_data):
                        self._handle_conflict('topics', local_topic, topic_data)
                        total_conflicts += 1
                    else:
                        cursor.execute("""
                            UPDATE topics 
                            SET topic_name = ?,
                                is_active = ?,
                                last_synced = ?,
                                sync_status = 'synced',
                                version = ?
                            WHERE topic_id = ?
                        """, (
                            topic_data.get('topic_name'),
                            topic_data.get('is_active'),
                            datetime.now(),
                            topic_data.get('version', 1),
                            local_topic['topic_id']
                        ))
                        total_pulled += 1
                else:
                    # Znajdź local group_id
                    cursor.execute("SELECT group_id FROM work_groups WHERE server_id = ?", (topic_data.get('group_id'),))
                    local_group = cursor.fetchone()
                    
                    if local_group:
                        cursor.execute("""
                            INSERT INTO topics (
                                server_id, group_id, topic_name, is_active, created_by,
                                last_synced, sync_status, version, modified_locally
                            ) VALUES (?, ?, ?, ?, ?, ?, 'synced', ?, 0)
                        """, (
                            server_id,
                            local_group['group_id'],
                            topic_data.get('topic_name'),
                            topic_data.get('is_active'),
                            topic_data.get('created_by'),
                            datetime.now(),
                            topic_data.get('version', 1)
                        ))
                        total_pulled += 1
        
        self.conn.commit()
        return {'pulled': total_pulled, 'conflicts': total_conflicts}
    
    def pull_messages(self) -> Dict[str, int]:
        """Pobierz wiadomości dla wszystkich tematów"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT server_id FROM topics WHERE server_id IS NOT NULL")
        topics = cursor.fetchall()
        
        total_pulled = 0
        total_conflicts = 0
        
        for topic in topics:
            response = self.api_client.get_topic_messages(topic['server_id'])
            if not response.success:
                continue
            
            messages = response.data or []
            
            for msg_data in messages:
                server_id = msg_data.get('message_id')
                
                cursor.execute("SELECT * FROM messages WHERE server_id = ?", (server_id,))
                local_msg = cursor.fetchone()
                
                if local_msg:
                    if self._detect_conflict(local_msg, msg_data):
                        self._handle_conflict('messages', local_msg, msg_data)
                        total_conflicts += 1
                    else:
                        cursor.execute("""
                            UPDATE messages 
                            SET content = ?,
                                background_color = ?,
                                is_important = ?,
                                last_synced = ?,
                                sync_status = 'synced',
                                version = ?
                            WHERE message_id = ?
                        """, (
                            msg_data.get('content'),
                            msg_data.get('background_color'),
                            msg_data.get('is_important'),
                            datetime.now(),
                            msg_data.get('version', 1),
                            local_msg['message_id']
                        ))
                        total_pulled += 1
                else:
                    cursor.execute("SELECT topic_id FROM topics WHERE server_id = ?", (msg_data.get('topic_id'),))
                    local_topic = cursor.fetchone()
                    
                    if local_topic:
                        cursor.execute("""
                            INSERT INTO messages (
                                server_id, topic_id, content, author, background_color, is_important,
                                last_synced, sync_status, version, modified_locally
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'synced', ?, 0)
                        """, (
                            server_id,
                            local_topic['topic_id'],
                            msg_data.get('content'),
                            msg_data.get('author'),
                            msg_data.get('background_color'),
                            msg_data.get('is_important'),
                            datetime.now(),
                            msg_data.get('version', 1)
                        ))
                        total_pulled += 1
        
        self.conn.commit()
        return {'pulled': total_pulled, 'conflicts': total_conflicts}
    
    def pull_tasks(self) -> Dict[str, int]:
        """Pobierz zadania dla wszystkich tematów"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT server_id FROM topics WHERE server_id IS NOT NULL")
        topics = cursor.fetchall()
        
        total_pulled = 0
        total_conflicts = 0
        
        for topic in topics:
            response = self.api_client.get_topic_tasks(topic['server_id'])
            if not response.success:
                continue
            
            tasks = response.data or []
            
            for task_data in tasks:
                server_id = task_data.get('task_id')
                
                cursor.execute("SELECT * FROM tasks WHERE server_id = ?", (server_id,))
                local_task = cursor.fetchone()
                
                if local_task:
                    if self._detect_conflict(local_task, task_data):
                        self._handle_conflict('tasks', local_task, task_data)
                        total_conflicts += 1
                    else:
                        cursor.execute("""
                            UPDATE tasks 
                            SET task_subject = ?,
                                task_description = ?,
                                assigned_to = ?,
                                due_date = ?,
                                completed = ?,
                                is_important = ?,
                                last_synced = ?,
                                sync_status = 'synced',
                                version = ?
                            WHERE task_id = ?
                        """, (
                            task_data.get('task_subject'),
                            task_data.get('task_description'),
                            task_data.get('assigned_to'),
                            task_data.get('due_date'),
                            task_data.get('completed'),
                            task_data.get('is_important'),
                            datetime.now(),
                            task_data.get('version', 1),
                            local_task['task_id']
                        ))
                        total_pulled += 1
                else:
                    cursor.execute("SELECT topic_id FROM topics WHERE server_id = ?", (task_data.get('topic_id'),))
                    local_topic = cursor.fetchone()
                    
                    if local_topic:
                        cursor.execute("""
                            INSERT INTO tasks (
                                server_id, topic_id, task_subject, task_description, 
                                assigned_to, due_date, completed, is_important, created_by,
                                last_synced, sync_status, version, modified_locally
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'synced', ?, 0)
                        """, (
                            server_id,
                            local_topic['topic_id'],
                            task_data.get('task_subject'),
                            task_data.get('task_description'),
                            task_data.get('assigned_to'),
                            task_data.get('due_date'),
                            task_data.get('completed'),
                            task_data.get('is_important'),
                            task_data.get('created_by'),
                            datetime.now(),
                            task_data.get('version', 1)
                        ))
                        total_pulled += 1
        
        self.conn.commit()
        return {'pulled': total_pulled, 'conflicts': total_conflicts}
    
    def pull_files(self) -> Dict[str, int]:
        """Pobierz metadane plików (same pliki są w B2)"""
        cursor = self.conn.cursor()
        
        cursor.execute("SELECT server_id FROM topics WHERE server_id IS NOT NULL")
        topics = cursor.fetchall()
        
        total_pulled = 0
        total_conflicts = 0
        
        for topic in topics:
            response = self.api_client.get_topic_files(topic['server_id'])
            if not response.success:
                continue
            
            files = response.data or []
            
            for file_data in files:
                server_id = file_data.get('file_id')
                
                cursor.execute("SELECT * FROM topic_files WHERE server_id = ?", (server_id,))
                local_file = cursor.fetchone()
                
                if local_file:
                    # Pliki są read-only po uploadzadzie (tylko is_important się zmienia)
                    cursor.execute("""
                        UPDATE topic_files 
                        SET is_important = ?,
                            last_synced = ?,
                            sync_status = 'synced'
                        WHERE file_id = ?
                    """, (
                        file_data.get('is_important'),
                        datetime.now(),
                        local_file['file_id']
                    ))
                    total_pulled += 1
                else:
                    cursor.execute("SELECT topic_id FROM topics WHERE server_id = ?", (file_data.get('topic_id'),))
                    local_topic = cursor.fetchone()
                    
                    if local_topic:
                        cursor.execute("""
                            INSERT INTO topic_files (
                                server_id, topic_id, file_name, content_type, file_size,
                                download_url, is_important, uploaded_by,
                                last_synced, sync_status, modified_locally
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'synced', 0)
                        """, (
                            server_id,
                            local_topic['topic_id'],
                            file_data.get('file_name'),
                            file_data.get('content_type'),
                            file_data.get('file_size'),
                            file_data.get('download_url'),
                            file_data.get('is_important'),
                            file_data.get('uploaded_by'),
                            datetime.now()
                        ))
                        total_pulled += 1
        
        self.conn.commit()
        return {'pulled': total_pulled, 'conflicts': total_conflicts}
    
    # =========================================================================
    # TASK 5.4: CONFLICT RESOLUTION - Wykrywanie i rozwiązywanie konfliktów
    # =========================================================================
    
    def _detect_conflict(self, local_row: sqlite3.Row, server_data: dict) -> bool:
        """
        Wykrywa konflikt między lokalną wersją a wersją z serwera.
        
        Konflikt występuje gdy:
        - local_row.modified_locally = 1 (zmiana lokalna)
        - server_data.version > local_row.version (zmiana na serwerze)
        
        Returns:
            True jeśli wykryto konflikt
        """
        if not local_row.get('modified_locally'):
            return False
        
        local_version = local_row.get('version', 1)
        server_version = server_data.get('version', 1)
        
        return server_version > local_version
    
    def _handle_conflict(self, entity_type: str, local_row: sqlite3.Row, server_data: dict):
        """
        Zapisuje konflikt do tabeli sync_conflicts.
        UI może później wyświetlić konflikty i pozwolić użytkownikowi wybrać rozwiązanie.
        
        Args:
            entity_type: Typ encji (groups, topics, messages, tasks, files)
            local_row: Lokalna wersja danych
            server_data: Wersja z serwera
        """
        cursor = self.conn.cursor()
        
        # Konwertuj row na dict
        local_dict = dict(local_row)
        
        cursor.execute("""
            INSERT INTO sync_conflicts (
                entity_type, entity_local_id, entity_server_id,
                local_version, server_version,
                local_data, server_data
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            entity_type,
            local_dict.get('group_id') or local_dict.get('topic_id') or local_dict.get('message_id') or local_dict.get('task_id') or local_dict.get('file_id'),
            local_dict.get('server_id'),
            local_dict.get('version', 1),
            server_data.get('version', 1),
            json.dumps(local_dict, default=str),
            json.dumps(server_data, default=str)
        ))
        
        # Oznacz encję jako konfliktową
        table_name = {
            'groups': 'work_groups',
            'topics': 'topics',
            'messages': 'messages',
            'tasks': 'tasks',
            'files': 'topic_files'
        }[entity_type]
        
        id_column = {
            'groups': 'group_id',
            'topics': 'topic_id',
            'messages': 'message_id',
            'tasks': 'task_id',
            'files': 'file_id'
        }[entity_type]
        
        cursor.execute(f"""
            UPDATE {table_name} 
            SET sync_status = 'conflict'
            WHERE {id_column} = ?
        """, (local_dict.get(id_column),))
        
        self.conn.commit()
        logger.warning(f"[SyncManager] Conflict detected for {entity_type} ID={local_dict.get(id_column)}")
    
    def get_unresolved_conflicts(self) -> List[sqlite3.Row]:
        """
        Pobiera listę nierozwiązanych konfliktów.
        
        Returns:
            Lista konfliktów
        """
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM sync_conflicts 
            WHERE resolved_at IS NULL
            ORDER BY conflict_detected_at DESC
        """)
        return cursor.fetchall()
    
    def resolve_conflict(self, conflict_id: int, strategy: str, user_id: int):
        """
        Rozwiązuje konflikt według wybranej strategii.
        
        Args:
            conflict_id: ID konfliktu
            strategy: 'keep_local', 'keep_remote', 'merge'
            user_id: ID użytkownika rozwiązującego konflikt
        """
        cursor = self.conn.cursor()
        
        # Pobierz konflikt
        cursor.execute("SELECT * FROM sync_conflicts WHERE conflict_id = ?", (conflict_id,))
        conflict = cursor.fetchone()
        
        if not conflict:
            return
        
        local_data = json.loads(conflict['local_data'])
        server_data = json.loads(conflict['server_data'])
        
        table_name = {
            'groups': 'work_groups',
            'topics': 'topics',
            'messages': 'messages',
            'tasks': 'tasks',
            'files': 'topic_files'
        }[conflict['entity_type']]
        
        id_column = {
            'groups': 'group_id',
            'topics': 'topic_id',
            'messages': 'message_id',
            'tasks': 'task_id',
            'files': 'file_id'
        }[conflict['entity_type']]
        
        if strategy == 'keep_local':
            # Zachowaj lokalną wersję, wyślij do serwera
            cursor.execute(f"""
                UPDATE {table_name} 
                SET sync_status = 'pending',
                    modified_locally = 1
                WHERE {id_column} = ?
            """, (conflict['entity_local_id'],))
            
        elif strategy == 'keep_remote':
            # Zastąp lokalną wersję wersją z serwera
            # Implementacja zależy od typu encji - tutaj uproszczony przykład
            cursor.execute(f"""
                UPDATE {table_name} 
                SET sync_status = 'synced',
                    modified_locally = 0,
                    version = ?
                WHERE {id_column} = ?
            """, (server_data.get('version'), conflict['entity_local_id']))
            
        elif strategy == 'merge':
            # Merge wymaga implementacji specyficznej dla typu encji
            # TODO: Implement merge logic
            pass
        
        # Oznacz konflikt jako rozwiązany
        cursor.execute("""
            UPDATE sync_conflicts 
            SET resolved_at = ?,
                resolution_strategy = ?,
                resolved_by = ?
            WHERE conflict_id = ?
        """, (datetime.now(), strategy, user_id, conflict_id))
        
        self.conn.commit()
        logger.info(f"[SyncManager] Conflict {conflict_id} resolved with strategy: {strategy}")
    
    # =========================================================================
    # UTILITY METHODS
    # =========================================================================
    
    def _update_sync_metadata(self, sync_type: str):
        """
        Aktualizuje metadane synchronizacji.
        
        Args:
            sync_type: 'push' lub 'pull'
        """
        cursor = self.conn.cursor()
        
        timestamp = datetime.now()
        
        for entity_type in ['groups', 'topics', 'messages', 'tasks', 'files']:
            if sync_type == 'push':
                cursor.execute("""
                    INSERT OR REPLACE INTO sync_metadata (entity_type, last_push_timestamp)
                    VALUES (?, ?)
                """, (entity_type, timestamp))
            else:  # pull
                cursor.execute("""
                    INSERT OR REPLACE INTO sync_metadata (entity_type, last_pull_timestamp)
                    VALUES (?, ?)
                """, (entity_type, timestamp))
        
        self.conn.commit()
    
    def get_sync_status(self) -> Dict[str, any]:
        """
        Pobiera status synchronizacji dla wszystkich typów encji.
        
        Returns:
            Słownik ze statusem synchronizacji
        """
        cursor = self.conn.cursor()
        
        status = {}
        
        for entity_type in ['groups', 'topics', 'messages', 'tasks', 'files']:
            cursor.execute("""
                SELECT * FROM sync_metadata 
                WHERE entity_type = ?
            """, (entity_type,))
            
            row = cursor.fetchone()
            status[entity_type] = dict(row) if row else None
        
        # Policz nierozwiązane konflikty
        cursor.execute("SELECT COUNT(*) as count FROM sync_conflicts WHERE resolved_at IS NULL")
        status['unresolved_conflicts'] = cursor.fetchone()['count']
        
        return status
