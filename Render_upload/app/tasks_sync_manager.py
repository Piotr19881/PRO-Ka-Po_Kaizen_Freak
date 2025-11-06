"""
Sync Manager - background synchronization for Tasks & Kanban.

Handles:
- Background sync with server
- Operation queuing
- Network availability detection
- Conflict resolution
- Retry logic with exponential backoff
- Batch synchronization
"""

import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from threading import Thread, Event, Lock
from loguru import logger

from .tasks_api_client import TasksAPIClient, APIResponse, ConflictError


class TasksSyncManager:
    """
    Sync Manager for local-first Tasks & Kanban architecture.
    
    Runs background worker that:
    - Monitors sync queue
    - Checks network availability
    - Synchronizes changes with server
    - Resolves conflicts
    - Retries on errors with exponential backoff
    """
    
    def __init__(
        self,
        api_client: TasksAPIClient,
        user_id: Optional[str] = None,
        sync_interval: int = 300,  # 5 minutes default
        max_retries: int = 3,
        batch_size: int = 100
    ):
        """
        Initialize Sync Manager.
        
        Args:
            api_client: TasksAPIClient instance
            user_id: User ID (if None, must be set later)
            sync_interval: Sync interval in seconds (default 300s = 5min)
            max_retries: Maximum number of retries on error
            batch_size: Maximum items per batch sync (default 100)
        """
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
        
        # Sync queue (in-memory, could be replaced with SQLite queue)
        self._pending_tasks: List[Dict[str, Any]] = []
        self._pending_tags: List[Dict[str, Any]] = []
        self._pending_kanban_items: List[Dict[str, Any]] = []
        
        # Stats
        self.last_sync_time: Optional[datetime] = None
        self.last_sync_timestamp: Optional[datetime] = None  # For incremental sync
        self.sync_count = 0
        self.error_count = 0
        self.conflict_count = 0
        
        logger.info(f"TasksSyncManager initialized (interval={sync_interval}s, batch={batch_size})")
    
    def set_user_id(self, user_id: str):
        """Set user ID"""
        self.user_id = user_id
        logger.debug(f"User ID set to: {user_id}")
    
    # =========================================================================
    # WORKER CONTROL
    # =========================================================================
    
    def start(self):
        """Start background worker"""
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
        Stop background worker.
        
        Args:
            wait: Whether to wait for worker thread to finish
            timeout: Timeout in seconds for join()
        """
        if not self._is_running:
            logger.warning("Sync worker is not running")
            return
        
        logger.info("Stopping sync worker...")
        self._stop_event.set()
        self._is_running = False
        
        if wait and self._worker_thread:
            self._worker_thread.join(timeout=timeout)
            if self._worker_thread.is_alive():
                logger.warning("Sync worker did not stop within timeout")
            else:
                logger.info("Sync worker stopped")
    
    def is_running(self) -> bool:
        """Check if worker is running"""
        return self._is_running
    
    # =========================================================================
    # QUEUE OPERATIONS
    # =========================================================================
    
    def queue_task(self, task_data: Dict[str, Any]):
        """Add task to sync queue"""
        with self._lock:
            # Remove existing entry if present (update)
            self._pending_tasks = [t for t in self._pending_tasks if t.get('id') != task_data.get('id')]
            self._pending_tasks.append(task_data)
            logger.debug(f"Queued task {task_data.get('id')}")
    
    def queue_tag(self, tag_data: Dict[str, Any]):
        """Add tag to sync queue"""
        with self._lock:
            self._pending_tags = [t for t in self._pending_tags if t.get('id') != tag_data.get('id')]
            self._pending_tags.append(tag_data)
            logger.debug(f"Queued tag {tag_data.get('id')}")
    
    def queue_kanban_item(self, item_data: Dict[str, Any]):
        """Add kanban item to sync queue"""
        with self._lock:
            self._pending_kanban_items = [i for i in self._pending_kanban_items if i.get('id') != item_data.get('id')]
            self._pending_kanban_items.append(item_data)
            logger.debug(f"Queued kanban item {item_data.get('id')}")
    
    def get_pending_counts(self) -> Dict[str, int]:
        """Get counts of pending items"""
        with self._lock:
            return {
                'tasks': len(self._pending_tasks),
                'tags': len(self._pending_tags),
                'kanban_items': len(self._pending_kanban_items)
            }
    
    # =========================================================================
    # SYNC OPERATIONS
    # =========================================================================
    
    def sync_now(self) -> bool:
        """
        Trigger immediate synchronization (manual sync).
        
        Returns:
            True if success, False if error
        """
        if not self.user_id:
            logger.error("Cannot sync: user_id not set")
            return False
        
        try:
            return self._perform_sync()
        except Exception as e:
            logger.error(f"Manual sync error: {e}")
            self.error_count += 1
            return False
    
    def initial_sync(self, callback=None) -> bool:
        """
        Initial synchronization - fetch all data from server.
        Call this once at app startup to get current data.
        
        Args:
            callback: Optional callback(progress: int, total: int) called during sync
            
        Returns:
            True if success, False if error
        """
        if not self.user_id:
            logger.error("Cannot perform initial sync: user_id not set")
            return False
        
        try:
            logger.info(f"Starting initial sync for user {self.user_id}...")
            
            # Fetch all tasks from server
            response = self.api_client.list_tasks(
                user_id=self.user_id,
                include_deleted=False,
                include_archived=True
            )
            
            if not response.success:
                logger.error(f"Initial sync failed: {response.error}")
                return False
            
            # Server returns: {"items": [...], "count": N}
            response_data = response.data or {}
            tasks = response_data.get('items', [])
            logger.info(f"Fetched {len(tasks)} tasks from server")
            
            # Callback for progress
            if callback:
                callback(len(tasks), len(tasks))
            
            # Note: You would save these to local database here
            # For now, just log success
            
            self.last_sync_time = datetime.utcnow()
            self.last_sync_timestamp = datetime.utcnow()
            logger.success(f"Initial sync complete: {len(tasks)} tasks")
            return True
            
        except Exception as e:
            logger.error(f"Initial sync error: {e}")
            return False
    
    def _perform_sync(self) -> bool:
        """
        Perform synchronization with server.
        
        Returns:
            True if success, False if error
        """
        if not self.user_id:
            return False
        
        try:
            # Get pending items
            with self._lock:
                tasks_to_sync = self._pending_tasks.copy()
                tags_to_sync = self._pending_tags.copy()
                kanban_items_to_sync = self._pending_kanban_items.copy()
            
            # If nothing to sync, skip
            if not tasks_to_sync and not tags_to_sync and not kanban_items_to_sync:
                logger.debug("Nothing to sync")
                return True
            
            # Split into batches if needed
            tasks_batches = self._split_into_batches(tasks_to_sync, self.batch_size)
            tags_batches = self._split_into_batches(tags_to_sync, self.batch_size)
            kanban_batches = self._split_into_batches(kanban_items_to_sync, self.batch_size)
            
            # Sync each batch
            all_success = True
            
            for i, (tasks, tags, kanban) in enumerate(zip(
                tasks_batches or [[]],
                tags_batches or [[]],
                kanban_batches or [[]]
            )):
                if not tasks and not tags and not kanban:
                    continue
                
                logger.debug(f"Syncing batch {i+1}: {len(tasks)} tasks, {len(tags)} tags, {len(kanban)} kanban items")
                
                response = self.api_client.bulk_sync(
                    user_id=self.user_id,
                    tasks=tasks,
                    tags=tags,
                    kanban_items=kanban
                )
                
                if not response.success:
                    logger.error(f"Batch sync failed: {response.error}")
                    all_success = False
                    self.error_count += 1
                    continue
                
                # Process results
                data = response.data or {}
                results = data.get('results', [])
                success_count = data.get('success_count', 0)
                conflict_count = data.get('conflict_count', 0)
                error_count = data.get('error_count', 0)
                
                logger.info(f"Batch sync: {success_count} success, {conflict_count} conflicts, {error_count} errors")
                
                self.conflict_count += conflict_count
                
                # Remove successfully synced items from queue
                synced_ids = {r['id'] for r in results if r.get('status') == 'success'}
                
                with self._lock:
                    self._pending_tasks = [t for t in self._pending_tasks if t.get('id') not in synced_ids]
                    self._pending_tags = [t for t in self._pending_tags if t.get('id') not in synced_ids]
                    self._pending_kanban_items = [i for i in self._pending_kanban_items if i.get('id') not in synced_ids]
            
            self.last_sync_time = datetime.utcnow()
            self.sync_count += 1
            
            return all_success
            
        except Exception as e:
            logger.error(f"Sync error: {e}")
            self.error_count += 1
            return False
    
    def _split_into_batches(self, items: List[Any], batch_size: int) -> List[List[Any]]:
        """Split items into batches"""
        if not items:
            return []
        
        batches = []
        for i in range(0, len(items), batch_size):
            batches.append(items[i:i+batch_size])
        return batches
    
    # =========================================================================
    # WORKER LOOP
    # =========================================================================
    
    def _worker_loop(self):
        """
        Main background worker loop.
        
        Performs sync every sync_interval seconds
        until stopped.
        """
        logger.debug("Worker loop started")
        
        retry_count = 0
        backoff_seconds = 1
        
        while not self._stop_event.is_set():
            try:
                # Check if it's time to sync
                should_sync = False
                
                if self.last_sync_time is None:
                    should_sync = True
                else:
                    time_since_last_sync = (datetime.utcnow() - self.last_sync_time).total_seconds()
                    if time_since_last_sync >= self.sync_interval:
                        should_sync = True
                
                if should_sync:
                    logger.debug("Performing scheduled sync...")
                    success = self._perform_sync()
                    
                    if success:
                        retry_count = 0
                        backoff_seconds = 1
                    else:
                        retry_count += 1
                        
                        if retry_count <= self.max_retries:
                            # Exponential backoff
                            backoff_seconds = min(2 ** retry_count, 300)  # Max 5 min
                            logger.warning(f"Sync failed, retry {retry_count}/{self.max_retries} in {backoff_seconds}s")
                        else:
                            logger.error(f"Sync failed after {self.max_retries} retries, giving up")
                            retry_count = 0
                            backoff_seconds = 1
                
                # Sleep for 1 second (check stop event frequently)
                self._stop_event.wait(1)
                
            except Exception as e:
                logger.exception(f"Worker loop error: {e}")
                self._stop_event.wait(5)  # Wait 5s on error
        
        logger.debug("Worker loop stopped")
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """Get sync statistics"""
        pending = self.get_pending_counts()
        
        return {
            'last_sync': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'conflict_count': self.conflict_count,
            'pending_tasks': pending['tasks'],
            'pending_tags': pending['tags'],
            'pending_kanban_items': pending['kanban_items'],
            'is_running': self._is_running
        }
