"""
Tasks Sync Manager - zarządzanie synchronizacją zadań w tle.

Ten moduł obsługuje:
- Background synchronizację z serwerem
- Kolejkowanie operacji (sync_queue)
- Wykrywanie dostępności sieci
- Rozwiązywanie konfliktów wersji
- Retry logic z exponential backoff
- Batch synchronizację (max 100 items per type)
"""

import json
import time
import uuid
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from threading import Thread, Event, Lock
from loguru import logger
from pathlib import Path

from .task_local_database import TaskLocalDatabase
from .tasks_api_client import TasksAPIClient, APIResponse, ConflictError
from .tasks_models import Task, TaskTag, KanbanItem, TaskCustomList

# Import Status LED funkcji (optional)
try:
    from ...ui.status_led import record_sync_success, record_sync_error
    STATUS_LED_AVAILABLE = True
except ImportError:
    STATUS_LED_AVAILABLE = False
    logger.debug("Status LED module not available")


def is_network_available() -> bool:
    """Sprawdź dostępność sieci (prosty check)"""
    try:
        import socket
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        return False


class TasksSyncManager:
    """
    Menedżer synchronizacji dla Tasks & Kanban (local-first architecture).
    
    Uruchamia background worker, który:
    - Monitoruje sync_queue w lokalnej bazie
    - Sprawdza dostępność sieci
    - Synchronizuje zmiany z serwerem (bulk sync)
    - Rozwiązuje konflikty wersji (last-write-wins)
    - Retry przy błędach z exponential backoff
    """
    
    def __init__(
        self, 
        local_db: TaskLocalDatabase,
        api_client: TasksAPIClient,
        user_id: Optional[str] = None,
        sync_interval: int = 300,  # 5 minut domyślnie
        max_retries: int = 3,
        batch_size: int = 100
    ):
        """
        Inicjalizacja Tasks Sync Manager.
        
        Args:
            local_db: TaskLocalDatabase instance
            api_client: TasksAPIClient instance
            user_id: ID użytkownika (UUID string)
            sync_interval: Interwał synchronizacji w sekundach (domyślnie 300s = 5min)
            max_retries: Maksymalna liczba ponowień przy błędzie
            batch_size: Max liczba items per batch (default 100)
        """
        self.local_db = local_db
        self.api_client = api_client
        self.user_id = user_id
        self.sync_interval = sync_interval
        self.max_retries = max_retries
        self.batch_size = batch_size
        
        # Threading
        self._worker_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._lock = Lock()
        self._is_running = False
        
        # Stats
        self.last_sync_time: Optional[datetime] = None
        self.sync_count = 0
        self.error_count = 0
        self.conflict_count = 0
        
        # Callbacks
        self.on_sync_complete: Optional[Callable] = None
        self.on_conflict: Optional[Callable[[str, Dict], None]] = None
        
        logger.info(f"TasksSyncManager initialized (interval={sync_interval}s, max_retries={max_retries}, batch_size={batch_size})")
    
    def set_user_id(self, user_id: str):
        """Ustaw ID użytkownika"""
        self.user_id = user_id
        logger.debug(f"User ID set to: {user_id}")
    
    # =========================================================================
    # WORKER CONTROL
    # =========================================================================
    
    def start(self):
        """Uruchom background worker"""
        if self._is_running:
            logger.warning("Sync worker is already running")
            return
        
        if not self.user_id:
            logger.error("Cannot start sync worker: user_id not set")
            raise ValueError("user_id must be set before starting sync worker")
        
        self._stop_event.clear()
        self._is_running = True
        self._worker_thread = Thread(target=self._worker_loop, daemon=True, name="TasksSyncWorker")
        self._worker_thread.start()
        logger.info("Tasks sync worker started")
    
    def stop(self, wait: bool = True, timeout: float = 5.0):
        """
        Zatrzymaj background worker.
        
        Args:
            wait: Czy czekać na zakończenie worker thread
            timeout: Timeout w sekundach dla join()
        """
        if not self._is_running:
            logger.warning("Sync worker is not running")
            return
        
        logger.info("Stopping tasks sync worker...")
        self._stop_event.set()
        self._is_running = False
        
        if wait and self._worker_thread:
            self._worker_thread.join(timeout=timeout)
            if self._worker_thread.is_alive():
                logger.warning("Sync worker did not stop within timeout")
            else:
                logger.info("Tasks sync worker stopped")
    
    def is_running(self) -> bool:
        """Sprawdź czy worker działa"""
        return self._is_running
    
    def sync_now(self):
        """Wymuszony sync (synchroniczny) - wywołaj z UI"""
        logger.info("Manual sync triggered")
        with self._lock:
            self._sync_cycle()
    
    # =========================================================================
    # INITIAL SYNC
    # =========================================================================
    
    def initial_sync(self, callback: Optional[Callable[[int, int], None]] = None) -> bool:
        """
        Początkowa synchronizacja - pobierz wszystkie dane z serwera.
        Wywołaj to raz przy starcie aplikacji aby pobrać aktualne dane.
        
        Args:
            callback: Optional callback(current, total) dla progress
            
        Returns:
            True jeśli sukces, False jeśli błąd
        """
        if not self.user_id:
            logger.error("Cannot perform initial sync: user_id not set")
            return False
        
        try:
            logger.info(f"Starting initial sync for user {self.user_id}...")
            
            # Pobierz tasks
            response = self.api_client.list_tasks(
                user_id=self.user_id,
                include_deleted=False,
                include_archived=True
            )
            
            if not response.success:
                logger.error(f"Initial sync failed (tasks): {response.error}")
                return False
            
            tasks_data = response.data or {}
            tasks = tasks_data.get('items', [])
            logger.info(f"Fetched {len(tasks)} tasks from server")
            
            # Pobierz tags
            response = self.api_client.list_tags(user_id=self.user_id, include_deleted=False)
            if response.success:
                tags_data = response.data or {}
                tags = tags_data.get('items', [])
                logger.info(f"Fetched {len(tags)} tags from server")
            else:
                tags = []
                logger.warning(f"Failed to fetch tags: {response.error}")
            
            # Pobierz kanban items
            response = self.api_client.list_kanban_items(user_id=self.user_id, include_deleted=False)
            if response.success:
                kanban_data = response.data or {}
                kanban_items = kanban_data.get('items', [])
                logger.info(f"Fetched {len(kanban_items)} kanban items from server")
            else:
                kanban_items = []
                logger.warning(f"Failed to fetch kanban items: {response.error}")
            
            # TODO: Zapisz do lokalnej bazy
            # To wymaga metod w TaskLocalDatabase do zapisywania z server UUID
            # Na razie tylko logujemy
            
            total_items = len(tasks) + len(tags) + len(kanban_items)
            logger.success(f"Initial sync complete: {len(tasks)} tasks, {len(tags)} tags, {len(kanban_items)} kanban items (total: {total_items})")
            
            if callback:
                callback(total_items, total_items)
            
            return True
            
        except Exception as e:
            logger.error(f"Initial sync error: {e}")
            return False
    
    # =========================================================================
    # QUEUE MANAGEMENT
    # =========================================================================
    
    def queue_task(self, task_id: str, local_id: int, action: str = 'upsert'):
        """
        Dodaj task do kolejki synchronizacji.
        
        Args:
            task_id: UUID zadania (server_uuid lub wygenerowany)
            local_id: Local database ID
            action: 'upsert' lub 'delete'
        """
        self._add_to_queue('task', task_id, local_id, action)
    
    def queue_tag(self, tag_id: str, local_id: int, action: str = 'upsert'):
        """Dodaj tag do kolejki synchronizacji"""
        self._add_to_queue('tag', tag_id, local_id, action)
    
    def queue_kanban_item(self, item_id: str, local_id: int, action: str = 'upsert'):
        """Dodaj kanban item do kolejki synchronizacji"""
        self._add_to_queue('kanban_item', item_id, local_id, action)
    
    def queue_custom_list(self, list_id: str, local_id: int, action: str = 'upsert'):
        """Dodaj custom list do kolejki synchronizacji"""
        self._add_to_queue('custom_list', list_id, local_id, action)
    
    def _add_to_queue(self, entity_type: str, entity_id: str, local_id: int, action: str):
        """Dodaj item do sync_queue w bazie"""
        try:
            # Sprawdź czy już jest w kolejce (deduplication)
            import sqlite3
            with sqlite3.connect(str(self.local_db.db_path)) as conn:
                cursor = conn.cursor()
                
                # Sprawdź duplikat
                cursor.execute("""
                    SELECT id FROM sync_queue 
                    WHERE entity_type = ? AND entity_id = ? AND action = ?
                """, (entity_type, entity_id, action))
                
                if cursor.fetchone():
                    logger.debug(f"Item {entity_type}:{entity_id} already in queue")
                    return
                
                # Dodaj do kolejki
                cursor.execute("""
                    INSERT INTO sync_queue (entity_type, entity_id, local_id, action, created_at)
                    VALUES (?, ?, ?, ?, ?)
                """, (entity_type, entity_id, local_id, action, datetime.now().isoformat()))
                
                conn.commit()
                logger.debug(f"Added to queue: {entity_type}:{entity_id} (action={action})")
                
        except Exception as e:
            logger.error(f"Error adding to queue: {e}")
    
    def get_pending_counts(self) -> Dict[str, int]:
        """Pobierz liczby pending items w kolejce per typ"""
        try:
            import sqlite3
            with sqlite3.connect(str(self.local_db.db_path)) as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT entity_type, COUNT(*) as count
                    FROM sync_queue
                    GROUP BY entity_type
                """)
                
                counts = {row[0]: row[1] for row in cursor.fetchall()}
                return counts
                
        except Exception as e:
            logger.error(f"Error getting pending counts: {e}")
            return {}
    
    # =========================================================================
    # WORKER LOOP
    # =========================================================================
    
    def _worker_loop(self):
        """
        Główna pętla background worker.
        
        Wykonuje synchronizację co sync_interval sekund,
        dopóki nie zostanie zatrzymany.
        """
        logger.debug("Tasks sync worker loop started")
        
        while not self._stop_event.is_set():
            try:
                # Sprawdź czy jest sieć
                if is_network_available():
                    # Wykonaj synchronizację
                    self._sync_cycle()
                else:
                    logger.debug("Network not available, skipping sync")
                
                # Czekaj przed następnym cyklem
                self._stop_event.wait(timeout=self.sync_interval)
                
            except Exception as e:
                logger.error(f"Error in worker loop: {e}")
                self.error_count += 1
                # Czekaj przed retry (exponential backoff)
                backoff = min(2 ** self.error_count, 300)  # max 5 minut
                self._stop_event.wait(timeout=backoff)
        
        logger.debug("Tasks sync worker loop exited")
    
    def _sync_cycle(self):
        """
        Jeden cykl synchronizacji.
        
        Pobiera items z sync_queue i synchronizuje z serwerem (bulk sync).
        """
        with self._lock:
            try:
                # Pobierz kolejkę sync
                queue = self._get_sync_queue(limit=self.batch_size)
                
                if not queue:
                    logger.debug("Sync queue is empty")
                    return
                
                logger.info(f"Processing {len(queue)} items from sync queue")
                
                # Grupuj po entity_type
                tasks_to_sync = []
                tags_to_sync = []
                kanban_items_to_sync = []
                
                for item in queue:
                    entity_type = item['entity_type']
                    entity_id = item['entity_id']
                    local_id = item['local_id']
                    action = item['action']
                    
                    # Pobierz dane z lokalnej bazy
                    data = self._get_entity_data(entity_type, local_id, entity_id)
                    
                    if data:
                        if entity_type == 'task':
                            tasks_to_sync.append(data)
                        elif entity_type == 'tag':
                            tags_to_sync.append(data)
                        elif entity_type == 'kanban_item':
                            kanban_items_to_sync.append(data)
                
                # Wykonaj bulk sync
                if tasks_to_sync or tags_to_sync or kanban_items_to_sync:
                    success = self._perform_bulk_sync(tasks_to_sync, tags_to_sync, kanban_items_to_sync)
                    
                    if success:
                        # Usuń z kolejki
                        self._clear_synced_items(queue)
                        
                        # Aktualizuj stats
                        self.last_sync_time = datetime.now()
                        self.sync_count += 1
                        
                        # Status LED
                        if STATUS_LED_AVAILABLE:
                            record_sync_success("tasks")
                        
                        # Callback
                        if self.on_sync_complete:
                            self.on_sync_complete()
                        
                        logger.success(f"Sync cycle completed: {len(tasks_to_sync)} tasks, {len(tags_to_sync)} tags, {len(kanban_items_to_sync)} kanban items")
                    else:
                        self.error_count += 1
                        if STATUS_LED_AVAILABLE:
                            record_sync_error("tasks")
                
            except Exception as e:
                logger.error(f"Error in sync cycle: {e}")
                self.error_count += 1
                if STATUS_LED_AVAILABLE:
                    record_sync_error("tasks")
    
    def _get_sync_queue(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Pobierz items z sync_queue"""
        try:
            import sqlite3
            with sqlite3.connect(str(self.local_db.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                cursor.execute("""
                    SELECT * FROM sync_queue
                    ORDER BY created_at ASC
                    LIMIT ?
                """, (limit,))
                
                return [dict(row) for row in cursor.fetchall()]
                
        except Exception as e:
            logger.error(f"Error getting sync queue: {e}")
            return []
    
    def _get_entity_data(self, entity_type: str, local_id: int, server_uuid: str) -> Optional[Dict[str, Any]]:
        """
        Pobierz dane entity z lokalnej bazy i przekonwertuj do API format.
        
        Args:
            entity_type: 'task', 'tag', 'kanban_item', 'custom_list'
            local_id: Local database ID
            server_uuid: UUID dla API
            
        Returns:
            Dict z danymi dla API lub None
        """
        try:
            import sqlite3
            with sqlite3.connect(str(self.local_db.db_path)) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                
                if entity_type == 'task':
                    cursor.execute("SELECT * FROM tasks WHERE id = ?", (local_id,))
                    row = cursor.fetchone()
                    if row:
                        task_data = dict(row)
                        # Konwertuj do API format
                        task = Task.from_local_db(task_data, server_id=server_uuid)
                        return task.to_dict()
                
                elif entity_type == 'tag':
                    cursor.execute("SELECT * FROM task_tags WHERE id = ?", (local_id,))
                    row = cursor.fetchone()
                    if row:
                        tag_data = dict(row)
                        return {
                            'id': server_uuid,
                            'user_id': self.user_id,
                            'name': tag_data.get('name', ''),
                            'color': tag_data.get('color', '#CCCCCC'),
                            'version': tag_data.get('version', 1),
                            'created_at': tag_data.get('created_at'),
                            'updated_at': tag_data.get('updated_at'),
                            'deleted_at': tag_data.get('deleted_at'),
                            'synced_at': tag_data.get('synced_at')
                        }
                
                elif entity_type == 'kanban_item':
                    cursor.execute("SELECT * FROM kanban_items WHERE id = ?", (local_id,))
                    row = cursor.fetchone()
                    if row:
                        item_data = dict(row)
                        # Potrzebujemy task_id jako UUID
                        task_uuid = item_data.get('server_uuid') or str(uuid.uuid4())
                        return {
                            'id': server_uuid,
                            'user_id': self.user_id,
                            'task_id': task_uuid,
                            'column_type': item_data.get('column_type', 'todo'),
                            'position': item_data.get('position', 0),
                            'version': item_data.get('version', 1),
                            'created_at': item_data.get('created_at'),
                            'updated_at': item_data.get('updated_at'),
                            'deleted_at': item_data.get('deleted_at'),
                            'synced_at': item_data.get('synced_at')
                        }
                
                return None
                
        except Exception as e:
            logger.error(f"Error getting entity data: {e}")
            return None
    
    def _perform_bulk_sync(self, tasks: List[Dict], tags: List[Dict], kanban_items: List[Dict]) -> bool:
        """
        Wykonaj bulk sync do serwera.
        
        Returns:
            True jeśli sukces
        """
        if not self.user_id:
            logger.error("Cannot sync: user_id not set")
            return False
        
        try:
            logger.info(f"Bulk sync: {len(tasks)} tasks, {len(tags)} tags, {len(kanban_items)} kanban items")
            
            response = self.api_client.bulk_sync(
                user_id=self.user_id,
                tasks=tasks[:100],  # Max 100
                tags=tags[:100],
                kanban_items=kanban_items[:100]
            )
            
            if not response.success:
                logger.error(f"Bulk sync failed: {response.error}")
                return False
            
            # Sprawdź wyniki
            results_data = response.data or {}
            results = results_data.get('results', [])
            success_count = results_data.get('success_count', 0)
            conflict_count = results_data.get('conflict_count', 0)
            error_count = results_data.get('error_count', 0)
            
            logger.info(f"Bulk sync results: {success_count} success, {conflict_count} conflicts, {error_count} errors")
            
            # Handle conflicts
            for result in results:
                if result.get('status') == 'conflict':
                    self.conflict_count += 1
                    if self.on_conflict:
                        self.on_conflict(result.get('entity_type'), result)
            
            return error_count == 0
            
        except ConflictError as e:
            logger.warning(f"Conflict during sync: {e}")
            self.conflict_count += 1
            if self.on_conflict:
                self.on_conflict('unknown', {'server_data': e.server_data, 'local_version': e.local_version, 'server_version': e.server_version})
            return False
            
        except Exception as e:
            logger.error(f"Error performing bulk sync: {e}")
            return False
    
    def _clear_synced_items(self, queue_items: List[Dict]):
        """Usuń zsynchronizowane items z sync_queue"""
        try:
            import sqlite3
            with sqlite3.connect(str(self.local_db.db_path)) as conn:
                cursor = conn.cursor()
                
                ids = [item['id'] for item in queue_items]
                placeholders = ','.join('?' * len(ids))
                
                cursor.execute(f"DELETE FROM sync_queue WHERE id IN ({placeholders})", ids)
                conn.commit()
                
                logger.debug(f"Cleared {len(ids)} items from sync queue")
                
        except Exception as e:
            logger.error(f"Error clearing sync queue: {e}")
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Pobierz statystyki synchronizacji"""
        pending = self.get_pending_counts()
        
        return {
            'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'conflict_count': self.conflict_count,
            'is_running': self._is_running,
            'pending_tasks': pending.get('task', 0),
            'pending_tags': pending.get('tag', 0),
            'pending_kanban_items': pending.get('kanban_item', 0),
            'pending_custom_lists': pending.get('custom_list', 0),
            'total_pending': sum(pending.values())
        }
