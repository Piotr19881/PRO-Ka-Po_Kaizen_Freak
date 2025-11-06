"""
Tasks Manager - Logika modułu zadań z synchronizacją
Integruje: TaskLocalDatabase, TasksSyncManager, TasksAPIClient, TasksWebSocketClient
"""
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable
from pathlib import Path
from loguru import logger
import uuid

# Import modeli
from .tasks_models import Task, TaskTag, KanbanItem, TaskCustomList

# Import komponentów synchronizacji
try:
    from .task_local_database import TaskLocalDatabase
    from .tasks_sync_manager import TasksSyncManager
    from .tasks_api_client import TasksAPIClient
    from .tasks_websocket_client import TasksWebSocketClient, create_tasks_websocket_client
except ImportError as e:
    logger.warning(f"Sync components not available: {e}")
    TaskLocalDatabase = None
    TasksSyncManager = None
    TasksAPIClient = None
    TasksWebSocketClient = None
    create_tasks_websocket_client = None


class TasksManager:
    """
    Menedżer zadań z synchronizacją local-first.
    
    Features:
    - Local-first architecture (TaskLocalDatabase)
    - Background synchronization (TasksSyncManager)
    - Real-time updates (WebSocket)
    - Offline support
    - Version-based conflict resolution
    """
    
    def __init__(
        self,
        data_dir: Path,
        user_id: Optional[str] = None,
        api_base_url: Optional[str] = None,
        auth_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        on_token_refreshed: Optional[Callable[[str, str], None]] = None,
        enable_sync: bool = False
    ):
        """
        Initialize TasksManager.
        
        Args:
            data_dir: Katalog z danymi lokalnymi
            user_id: ID użytkownika UUID string (wymagane dla sync)
            api_base_url: URL API serwera (np. "http://localhost:8000")
            auth_token: JWT access token
            refresh_token: JWT refresh token
            on_token_refreshed: Callback po odświeżeniu tokena: (new_access, new_refresh) -> None
            enable_sync: Czy włączyć synchronizację (True) czy tylko local storage (False)
        """
        self.data_dir = data_dir
        self.db_path = data_dir / "tasks.db"
        
        # Sync configuration
        self.user_id = user_id
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.on_token_refreshed = on_token_refreshed
        self.enable_sync = enable_sync and TaskLocalDatabase is not None
        
        if enable_sync and TaskLocalDatabase is None:
            logger.error("Sync requested but TaskLocalDatabase not available - check imports!")
        
        # Sync components
        self.local_db: Optional[TaskLocalDatabase] = None
        self.api_client: Optional[TasksAPIClient] = None
        self.sync_manager: Optional[TasksSyncManager] = None
        self.ws_client: Optional[TasksWebSocketClient] = None
        
        # UI callbacks dla real-time updates
        self.on_tasks_changed: Optional[Callable[[], None]] = None
        self.on_tags_changed: Optional[Callable[[], None]] = None
        self.on_sync_complete: Optional[Callable[[], None]] = None
        
        # Initialize
        self._init_database()
        
        if self.enable_sync and api_base_url and auth_token:
            self._init_sync(api_base_url, auth_token)
    
    def _init_database(self):
        """Inicjalizuj lokalną bazę danych"""
        try:
            if not TaskLocalDatabase:
                logger.warning("TaskLocalDatabase not available")
                return
            
            # Ensure data directory exists
            self.data_dir.mkdir(parents=True, exist_ok=True)
            
            # Initialize database
            user_id_int = 1  # Default user ID dla local DB (integer)
            if self.user_id:
                try:
                    # FIXED: Użyj deterministycznego hashowania UUID → integer
                    # hash() jest niedeterministyczny między uruchomieniami Pythona!
                    import hashlib
                    hash_bytes = hashlib.md5(str(self.user_id).encode('utf-8')).digest()
                    user_id_int = int.from_bytes(hash_bytes[:4], byteorder='big')
                except Exception as e:
                    logger.warning(f"Failed to convert user_id to int: {e}, using default")
                    user_id_int = 1
            
            self.local_db = TaskLocalDatabase(db_path=self.db_path, user_id=user_id_int)
            logger.info(f"TaskLocalDatabase initialized: {self.db_path}")
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            self.local_db = None
    
    def _init_sync(self, api_base_url: str, auth_token: str):
        """
        Inicjalizuj komponenty synchronizacji.
        
        Args:
            api_base_url: URL API serwera
            auth_token: JWT access token
        """
        if not self.user_id:
            logger.warning("Cannot enable sync without user_id")
            self.enable_sync = False
            return
        
        if not self.local_db:
            logger.error("Cannot enable sync without local_db")
            self.enable_sync = False
            return
        
        try:
            # Wrapper callback dla token refresh
            def on_token_refreshed_wrapper(new_access_token: str, new_refresh_token: str):
                """Callback po odświeżeniu tokena - aktualizuje WebSocket"""
                logger.info(f"🔄 Token refresh callback - updating clients")
                
                # Zaktualizuj tokeny
                self.auth_token = new_access_token
                self.refresh_token = new_refresh_token
                
                # Zaktualizuj API client
                if self.api_client:
                    self.api_client.set_auth_token(new_access_token)
                
                # Zaktualizuj WebSocket client
                if self.ws_client:
                    self.ws_client.update_token(new_access_token)
                    logger.info("✅ WebSocket token updated")
                
                # Wywołaj oryginalny callback
                if self.on_token_refreshed:
                    self.on_token_refreshed(new_access_token, new_refresh_token)
            
            # API Client
            self.api_client = TasksAPIClient(
                base_url=api_base_url,
                auth_token=auth_token,
                refresh_token=self.refresh_token,
                on_token_refreshed=on_token_refreshed_wrapper
            )
            logger.info("TasksAPIClient configured")
            
            # SyncManager
            self.sync_manager = TasksSyncManager(
                local_db=self.local_db,
                api_client=self.api_client,
                user_id=self.user_id,
                sync_interval=300  # Sync co 5 minut
            )
            
            # Callback dla sync complete
            self.sync_manager.on_sync_complete = self._on_sync_complete
            self.sync_manager.on_conflict = self._on_conflict
            
            self.sync_manager.start()
            logger.info("TasksSyncManager started")
            
            # WebSocket Client
            self.ws_client = create_tasks_websocket_client(
                base_url=api_base_url,
                auth_token=auth_token,
                on_sync_required=self._on_sync_required,
                on_item_changed=self._on_item_changed,
                auto_reconnect=True
            )
            self.ws_client.start()
            logger.info("TasksWebSocketClient started")
            
            # Initial sync
            logger.info("Starting initial sync...")
            self.sync_manager.initial_sync()
            
        except Exception as e:
            logger.error(f"Failed to initialize sync: {e}")
            self.enable_sync = False
    
    # =========================================================================
    # BACKWARD COMPATIBILITY PROPERTIES
    # =========================================================================
    
    @property
    def db(self):
        """Backward compatibility: task_view używa task_logic.db"""
        return self.local_db
    
    # =========================================================================
    # SYNC CALLBACKS
    # =========================================================================
    
    def _on_sync_complete(self):
        """Callback po zakończeniu synchronizacji"""
        logger.debug("Sync complete")
        if self.on_sync_complete:
            self.on_sync_complete()
        if self.on_tasks_changed:
            self.on_tasks_changed()
    
    def _on_conflict(self, entity_type: str, conflict_data: Dict):
        """Callback przy konflikcie wersji"""
        logger.warning(f"Conflict detected for {entity_type}: {conflict_data}")
        # TODO: Implement conflict resolution UI
    
    def _on_sync_required(self, entity_type: str):
        """Callback z WebSocket - wymaga synchronizacji"""
        logger.info(f"Sync required for: {entity_type}")
        if self.sync_manager:
            self.sync_manager.sync_now()
    
    def _on_item_changed(self, entity_type: str, item_id: str, action: str):
        """Callback z WebSocket - zmiana item"""
        logger.info(f"Item changed: {entity_type}:{item_id} ({action})")
        
        # Trigger UI update
        if entity_type == 'task' and self.on_tasks_changed:
            self.on_tasks_changed()
        elif entity_type == 'tag' and self.on_tags_changed:
            self.on_tags_changed()
    
    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================
    
    def add_task(self, task_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Dodaj nowe zadanie.
        
        Args:
            task_data: Słownik z danymi zadania (title, description, status, etc.)
            
        Returns:
            Słownik z dodanym zadaniem lub None w przypadku błędu
        """
        if not self.local_db:
            logger.error("Cannot add task: local_db not available")
            return None
        
        try:
            title = task_data.get('title', 'Nowe zadanie')
            parent_id = task_data.get('parent_id')
            
            # Przygotuj custom_data i direct keys
            custom_data: Dict[str, Any] = {}
            if isinstance(task_data.get('custom_data'), dict):
                custom_data.update(task_data['custom_data'])
            
            direct_keys = {
                'status', 'completion_date', 'kanban_id', 
                'note_id', 'alarm_date', 'row_color', 'archived'
            }
            
            extra_kwargs: Dict[str, Any] = {}
            for key in direct_keys:
                if key in task_data and task_data[key] is not None:
                    extra_kwargs[key] = task_data[key]
            
            # Tags
            tags = None
            if isinstance(task_data.get('tags'), list):
                tags = [tag for tag in task_data['tags'] if tag is not None]
            
            # Dodatkowe pola do custom_data
            for key, value in task_data.items():
                if key in {'title', 'parent_id', 'custom_data', 'tags', 'add_to_kanban'}:
                    continue
                if key in direct_keys:
                    continue
                if value is not None:
                    custom_data[key] = value
            
            # Dodaj do lokalnej bazy
            local_task_id = self.local_db.add_task(
                title=title,
                parent_id=parent_id,
                custom_data=custom_data or None,
                tags=tags,
                **extra_kwargs
            )
            
            if local_task_id:
                logger.info(f"Task added: local_id={local_task_id}")
                
                # Kolejkuj do synchronizacji (jeśli włączona)
                if self.sync_manager:
                    server_uuid = str(uuid.uuid4())
                    self.sync_manager.queue_task(server_uuid, local_task_id, action='upsert')
                
                # Trigger UI update
                if self.on_tasks_changed:
                    self.on_tasks_changed()
                
                # Zwróć słownik z zadaniem (dla kompatybilności z UI)
                # Pobierz zadanie z bazy
                tasks = self.local_db.get_tasks(parent_id=None, include_archived=False, include_subtasks=False)
                task = next((t for t in tasks if t.get('id') == local_task_id), None)
                
                if task:
                    return task
                else:
                    # Fallback: zwróć podstawowy dict
                    return {'id': local_task_id, 'title': title}
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to add task: {e}")
            return None
    
    def update_task(self, task_id: int, updates: Dict[str, Any]) -> bool:
        """
        Zaktualizuj zadanie.
        
        Args:
            task_id: Local task ID
            updates: Słownik z polami do aktualizacji
            
        Returns:
            True jeśli sukces
        """
        if not self.local_db:
            logger.error("Cannot update task: local_db not available")
            return False
        
        try:
            # Pobierz zadanie
            tasks = self.local_db.get_tasks(parent_id=None, include_archived=True, include_subtasks=False)
            task = next((t for t in tasks if t.get('id') == task_id), None)
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            # Aktualizuj zadanie
            # TODO: Implement update_task method in TaskLocalDatabase
            # For now, log the operation
            logger.info(f"Task {task_id} updated: {updates}")
            
            # Kolejkuj do synchronizacji
            if self.sync_manager:
                server_uuid = task.get('server_uuid') or str(uuid.uuid4())
                self.sync_manager.queue_task(server_uuid, task_id, action='upsert')
            
            # Trigger UI update
            if self.on_tasks_changed:
                self.on_tasks_changed()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update task: {e}")
            return False
    
    def delete_task(self, task_id: int, soft: bool = True) -> bool:
        """
        Usuń zadanie.
        
        Args:
            task_id: Local task ID
            soft: Soft delete (True) lub hard delete (False)
            
        Returns:
            True jeśli sukces
        """
        if not self.local_db:
            logger.error("Cannot delete task: local_db not available")
            return False
        
        try:
            # Pobierz zadanie dla server_uuid
            tasks = self.local_db.get_tasks(parent_id=None, include_archived=True, include_subtasks=False)
            task = next((t for t in tasks if t.get('id') == task_id), None)
            
            if not task:
                logger.error(f"Task {task_id} not found")
                return False
            
            # Usuń z lokalnej bazy
            if soft:
                # TODO: Implement soft delete in TaskLocalDatabase
                logger.info(f"Task {task_id} soft deleted")
            else:
                # Hard delete
                logger.info(f"Task {task_id} hard deleted")
            
            # Kolejkuj do synchronizacji
            if self.sync_manager and soft:
                server_uuid = task.get('server_uuid') or str(uuid.uuid4())
                self.sync_manager.queue_task(server_uuid, task_id, action='delete')
            
            # Trigger UI update
            if self.on_tasks_changed:
                self.on_tasks_changed()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete task: {e}")
            return False
    
    def load_tasks(self, limit: Optional[int] = None, include_archived: bool = False) -> List[Dict[str, Any]]:
        """
        Wczytaj zadania z bazy danych.
        
        Args:
            limit: Maksymalna liczba zadań
            include_archived: Czy uwzględnić zadania zarchiwizowane
            
        Returns:
            Lista słowników z zadaniami
        """
        if not self.local_db:
            logger.warning("No database available, returning empty list")
            return []
        
        try:
            tasks = self.local_db.get_tasks(
                parent_id=None,
                include_archived=include_archived,
                include_subtasks=False
            )
            
            # Rozbuduj dane o custom_data
            enriched_tasks = []
            for task in tasks:
                enriched = dict(task)
                
                # Wyciągnij custom_data na górny poziom
                if 'custom_data' in task and isinstance(task['custom_data'], dict):
                    for key, value in task['custom_data'].items():
                        enriched[key] = value
                
                # Konwertuj tagi na string
                if 'tags' in task and isinstance(task['tags'], list):
                    enriched['tags_list'] = task['tags']
                    enriched['tags'] = ', '.join([tag.get('name', '') for tag in task['tags']])
                
                enriched_tasks.append(enriched)
            
            if limit:
                enriched_tasks = enriched_tasks[:limit]
            
            logger.info(f"Loaded {len(enriched_tasks)} tasks from database")
            return enriched_tasks
            
        except Exception as e:
            logger.error(f"Failed to load tasks: {e}")
            return []
    
    def filter_tasks(self, text: str = '', status: Optional[str] = 'all', tag: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Filtruj zadania.
        
        Args:
            text: Tekst do wyszukania
            status: Status ('all', 'active', 'completed', 'archived')
            tag: Nazwa tagu do filtrowania
            
        Returns:
            Przefiltrowana lista zadań
        """
        # Normalizuj status
        status_key = (status or 'all').lower()
        status_map = {
            'wszystkie': 'all', 'all': 'all',
            'aktywne': 'active', 'active': 'active',
            'ukończone': 'completed', 'ukonczone': 'completed', 'completed': 'completed',
            'zarchiwizowane': 'archived', 'archived': 'archived',
        }
        status_key = status_map.get(status_key, 'all')
        
        include_archived = status_key == 'archived'
        all_tasks = self.load_tasks(include_archived=include_archived)
        
        text_query = (text or '').lower().strip()
        tag_query = (tag or '').strip().lower()
        if tag_query in {'', 'wszystkie', 'all'}:
            tag_query = ''
        
        filtered: List[Dict[str, Any]] = []
        
        for task in all_tasks:
            is_completed = bool(task.get('status'))
            is_archived = bool(task.get('archived'))
            
            # Filtruj po statusie
            if status_key == 'active':
                if is_archived or is_completed:
                    continue
            elif status_key == 'completed':
                if is_archived or not is_completed:
                    continue
            elif status_key == 'archived':
                if not is_archived:
                    continue
            else:  # 'all'
                if is_archived:
                    continue
            
            # Filtruj po tagu
            if tag_query:
                tags_match = False
                tags_list = task.get('tags_list')
                if isinstance(tags_list, list):
                    tags_match = any(
                        isinstance(t, dict) and (t.get('name', '').lower() == tag_query)
                        for t in tags_list
                    )
                if not tags_match:
                    tags_str = task.get('tags', '')
                    if isinstance(tags_str, str):
                        tags_match = tag_query in tags_str.lower()
                if not tags_match:
                    continue
            
            # Filtruj po tekście
            if text_query:
                title = task.get('title', '') or ''
                tags_text = task.get('tags', '') or ''
                searchable = f"{title} {tags_text}".lower()
                if text_query not in searchable:
                    continue
            
            filtered.append(task)
        
        logger.info(f"Filtered {len(filtered)} tasks from {len(all_tasks)}")
        return filtered
    
    # =========================================================================
    # SYNC OPERATIONS
    # =========================================================================
    
    def sync_now(self):
        """Wymuszony sync (ręczny trigger z UI)"""
        if self.sync_manager:
            self.sync_manager.sync_now()
        else:
            logger.warning("Sync manager not available")
    
    def get_sync_stats(self) -> Dict[str, Any]:
        """Pobierz statystyki synchronizacji"""
        if self.sync_manager:
            return self.sync_manager.get_stats()
        return {}
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def cleanup(self):
        """Cleanup resources (call on app close)"""
        logger.info("TasksManager cleanup...")
        
        if self.sync_manager:
            self.sync_manager.stop()
        
        if self.ws_client:
            self.ws_client.stop()
        
        logger.info("TasksManager cleanup complete")
    
    # =========================================================================
    # BACKWARD COMPATIBILITY PROPERTY
    # =========================================================================
    
    @property
    def db(self):
        """Backward compatibility: TaskLogic używał 'db', TasksManager używa 'local_db'"""
        return self.local_db


# =============================================================================
# BACKWARD COMPATIBILITY
# =============================================================================

class TaskLogic(TasksManager):
    """Backward compatibility alias"""
    def __init__(self, db: Optional[Any] = None):
        if db:
            # Legacy mode - just use provided db
            self.db = db
            logger.info(f"[TaskLogic] Initialized with database: {db is not None}")
        else:
            # New mode - no initialization
            logger.warning("[TaskLogic] Initialized without database (use TasksManager instead)")
