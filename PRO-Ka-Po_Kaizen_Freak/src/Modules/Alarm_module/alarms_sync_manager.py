"""
Sync Manager - zarządzanie synchronizacją alarmów i timerów w tle.

Ten moduł obsługuje:
- Background synchronizację z serwerem
- Kolejkowanie operacji
- Wykrywanie dostępności sieci
- Rozwiązywanie konfliktów
- Retry logic z exponential backoff
- Batch synchronizację
"""

import json
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from threading import Thread, Event, Lock
from loguru import logger

from .alarm_local_database import LocalDatabase
from .alarm_api_client import AlarmsAPIClient, APIResponse, ConflictError, is_network_available

# Import Status LED funkcji (optional - jeśli moduł UI nie jest dostępny, nie zepsuje się)
try:
    from ...ui.status_led import record_sync_success, record_sync_error
    STATUS_LED_AVAILABLE = True
except ImportError:
    STATUS_LED_AVAILABLE = False
    logger.debug("Status LED module not available")


class SyncManager:
    """
    Menedżer synchronizacji dla local-first architecture.
    
    Uruchamia background worker, który:
    - Monitoruje sync_queue
    - Sprawdza dostępność sieci
    - Synchronizuje zmiany z serwerem
    - Rozwiązuje konflikty
    - Retry przy błędach z exponential backoff
    """
    
    def __init__(
        self, 
        local_db: LocalDatabase,
        api_client: AlarmsAPIClient,
        user_id: Optional[str] = None,
        sync_interval: int = 30,
        max_retries: int = 3
    ):
        """
        Inicjalizacja Sync Manager.
        
        Args:
            local_db: LocalDatabase instance
            api_client: AlarmsAPIClient instance
            user_id: ID użytkownika (jeśli None, musi być ustawiony później)
            sync_interval: Interwał synchronizacji w sekundach (domyślnie 30s)
            max_retries: Maksymalna liczba ponowień przy błędzie
        """
        self.local_db = local_db
        self.api_client = api_client
        self.user_id = user_id
        self.sync_interval = sync_interval
        self.max_retries = max_retries
        
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
        
        logger.info(f"SyncManager initialized (interval={sync_interval}s, max_retries={max_retries})")
    
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
        self._worker_thread = Thread(target=self._worker_loop, daemon=True, name="SyncWorker")
        self._worker_thread.start()
        logger.info("Sync worker started")
    
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
        """Sprawdź czy worker działa"""
        return self._is_running
    
    def initial_sync(self) -> bool:
        """
        Początkowa synchronizacja - pobierz wszystkie dane z serwera.
        Wywołaj to raz przy starcie aplikacji aby pobrać aktualne dane.
        
        Returns:
            True jeśli sukces, False jeśli błąd
        """
        if not self.user_id:
            logger.error("Cannot perform initial sync: user_id not set")
            return False
        
        try:
            logger.info(f"Starting initial sync for user {self.user_id}...")
            
            # Pobierz wszystkie alarmy i timery z serwera
            response = self.api_client.fetch_all(user_id=self.user_id)
            
            if not response.success:
                logger.error(f"Initial sync failed: {response.error}")
                return False
            
            # Serwer zwraca: {"items": [...], "count": N}
            response_data = response.data or {}
            items = response_data.get('items', [])
            logger.info(f"Fetched {len(items)} items from server")
            
            # Zapisz do lokalnej bazy
            alarm_count = 0
            timer_count = 0
            
            for item in items:
                item_type = item.get('type')
                
                if item_type == 'alarm':
                    from .alarm_models import Alarm
                    alarm = Alarm.from_dict(item)
                    self.local_db.save_alarm(alarm, self.user_id, enqueue=False)
                    self.local_db.mark_alarm_synced(alarm.id)
                    alarm_count += 1
                    
                elif item_type == 'timer':
                    from .alarm_models import Timer
                    timer = Timer.from_dict(item)
                    self.local_db.save_timer(timer, self.user_id, enqueue=False)
                    self.local_db.mark_timer_synced(timer.id)
                    timer_count += 1
            
            logger.success(f"Initial sync complete: {alarm_count} alarms, {timer_count} timers")
            return True
            
        except Exception as e:
            logger.error(f"Initial sync error: {e}")
            return False
    
    # =========================================================================
    # WORKER LOOP
    # =========================================================================
    
    def _worker_loop(self):
        """
        Główna pętla background worker.
        
        Wykonuje synchronizację co sync_interval sekund,
        dopóki nie zostanie zatrzymany.
        """
        logger.debug("Worker loop started")
        
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
                # Czekaj przed retry
                self._stop_event.wait(timeout=min(self.sync_interval, 10))
        
        logger.debug("Worker loop exited")
    
    def _sync_cycle(self):
        """
        Jeden cykl synchronizacji.
        
        Pobiera items z sync_queue i synchronizuje z serwerem.
        """
        with self._lock:
            try:
                # Pobierz kolejkę sync
                queue = self.local_db.get_sync_queue(limit=20)
                
                if not queue:
                    logger.debug("Sync queue is empty")
                    return
                
                logger.info(f"Processing {len(queue)} items from sync queue")
                
                success_count = 0
                failed_count = 0
                
                for item in queue:
                    try:
                        result = self._sync_item(item)
                        if result:
                            success_count += 1
                        else:
                            failed_count += 1
                    except Exception as e:
                        logger.error(f"Error syncing item {item['entity_id']}: {e}")
                        failed_count += 1
                
                self.last_sync_time = datetime.now()
                self.sync_count += 1
                
                # Rejestruj event w Status LED
                if STATUS_LED_AVAILABLE:
                    if failed_count == 0 and success_count > 0:
                        record_sync_success("alarms")
                    elif failed_count > 0:
                        record_sync_error("alarms")
                
                logger.info(f"Sync cycle completed: {success_count} success, {failed_count} failed")
                
            except Exception as e:
                logger.error(f"Error in sync cycle: {e}")
                self.error_count += 1
    
    def _sync_item(self, queue_item: Dict[str, Any]) -> bool:
        """
        Synchronizuj pojedynczy item z kolejki.
        
        Args:
            queue_item: Item z sync_queue
            
        Returns:
            True jeśli sukces
        """
        if not self.user_id:
            logger.error("Cannot sync: user_id not set")
            return False
        
        entity_type = queue_item['entity_type']
        entity_id = queue_item['entity_id']
        action = queue_item['action']  # Zmienione z 'operation' na 'action'
        retry_count = queue_item.get('retry_count', 0)
        
        logger.debug(f"Syncing {entity_type} {entity_id} (action={action}, retry={retry_count})")
        
        # Sprawdź max retries
        if retry_count >= self.max_retries:
            logger.warning(f"Max retries exceeded for {entity_id}, removing from queue")
            self.local_db.remove_from_sync_queue(queue_item['id'])
            return False
        
        try:
            if action == 'delete':
                # Soft delete na serwerze
                response = self.api_client.delete_item(entity_id, soft=True)

                if response.success:
                    logger.info(f"Successfully deleted {entity_id} on server")
                    self.local_db.remove_from_sync_queue(queue_item['id'])
                    return True
                elif response.status_code == 404:
                    # Item nie istnieje na serwerze - traktuj jako sukces
                    # (już jest "usunięty" z perspektywy serwera)
                    logger.info(f"Item {entity_id} not found on server (404) - treating delete as successful")
                    self.local_db.remove_from_sync_queue(queue_item['id'])
                    return True
                else:
                    # Inny błąd - zaktualizuj retry
                    error_msg = response.error or "Unknown error"
                    self.local_db.update_sync_queue_error(queue_item['id'], error_msg)
                    return False
            
            elif action == 'upsert':
                # Insert lub Update
                data = queue_item.get('data')
                if not data:
                    logger.error(f"No data for upsert action: {entity_id}")
                    self.local_db.remove_from_sync_queue(queue_item['id'])
                    return False
                
                # Parsuj JSON jeśli to string
                if isinstance(data, str):
                    import json
                    try:
                        data = json.loads(data)
                    except json.JSONDecodeError as e:
                        logger.error(f"Failed to parse data JSON: {e}")
                        self.local_db.remove_from_sync_queue(queue_item['id'])
                        return False
                
                # Wybierz metodę sync w zależności od typu
                if entity_type == 'alarm':
                    response = self.api_client.sync_alarm(data, self.user_id)
                else:  # timer
                    response = self.api_client.sync_timer(data, self.user_id)
                
                if response.success:
                    logger.info(f"Successfully synced {entity_id} to server")
                    
                    # Zaktualizuj wersję z odpowiedzi serwera
                    if response.data and 'version' in response.data:
                        new_version = response.data['version']
                        logger.debug(f"Updating local version to {new_version} for {entity_id}")
                        
                        # Zaktualizuj wersję w lokalnej bazie
                        if entity_type == 'alarm':
                            self.local_db.update_alarm_version(entity_id, new_version)
                        else:
                            self.local_db.update_timer_version(entity_id, new_version)
                    
                    # Oznacz jako zsynchronizowany w lokalnej bazie
                    if entity_type == 'alarm':
                        self.local_db.mark_alarm_synced(entity_id)
                    else:
                        self.local_db.mark_timer_synced(entity_id)
                    
                    # Usuń z kolejki
                    self.local_db.remove_from_sync_queue(queue_item['id'])
                    return True
                else:
                    # Błąd - zaktualizuj retry
                    error_msg = response.error or "Unknown error"
                    self.local_db.update_sync_queue_error(queue_item['id'], error_msg)
                    return False
            
            else:
                logger.error(f"Unknown action: {action}")
                self.local_db.remove_from_sync_queue(queue_item['id'])
                return False
        
        except ConflictError as e:
            # Konflikt wersji - rozwiąż
            logger.warning(f"Conflict detected for {entity_id}: local={e.local_version}, server={e.server_version}")
            self.conflict_count += 1
            
            local_data_str = queue_item.get('data')
            if not local_data_str:
                logger.error(f"No local data for conflict resolution: {entity_id}")
                self.local_db.remove_from_sync_queue(queue_item['id'])
                return False
            
            # Parse JSON string to dict
            try:
                local_data = json.loads(local_data_str) if isinstance(local_data_str, str) else local_data_str
            except (json.JSONDecodeError, ValueError) as json_error:
                logger.error(f"Failed to parse local data JSON: {entity_id} - {json_error}")
                self.local_db.remove_from_sync_queue(queue_item['id'])
                return False
            
            result = self._resolve_conflict(entity_type, entity_id, local_data, e.server_data)
            
            if result:
                # Konflikt rozwiązany - usuń z kolejki
                self.local_db.remove_from_sync_queue(queue_item['id'])
                return True
            else:
                # Nie udało się rozwiązać - retry
                self.local_db.update_sync_queue_error(queue_item['id'], "Conflict resolution failed")
                return False
        
        except Exception as e:
            logger.error(f"Unexpected error syncing {entity_id}: {e}")
            self.local_db.update_sync_queue_error(queue_item['id'], str(e))
            return False
    
    # =========================================================================
    # CONFLICT RESOLUTION
    # =========================================================================
    
    def _resolve_conflict(
        self, 
        entity_type: str, 
        entity_id: str, 
        local_data: Dict[str, Any],
        server_data: Dict[str, Any]
    ) -> bool:
        """
        Rozwiąż konflikt między lokalną a serwerową wersją.
        
        Args:
            entity_type: 'alarm' lub 'timer'
            entity_id: ID entity
            local_data: Lokalne dane
            server_data: Dane z serwera
            
        Returns:
            True jeśli konflikt został rozwiązany
        """
        if not self.user_id:
            logger.error("Cannot resolve conflict: user_id not set")
            return False
        
        try:
            # Użyj strategii last-write-wins
            winning_data, winner = self.api_client.resolve_conflict(
                local_data=local_data,
                server_data=server_data,
                strategy='last_write_wins'
            )
            
            logger.info(f"Conflict resolved for {entity_id}: {winner} wins")
            
            if winner == 'server':
                # Serwer wygrywa - nadpisz lokalną kopię
                if entity_type == 'alarm':
                    from .alarm_models import Alarm
                    alarm = Alarm.from_dict(winning_data)
                    self.local_db.save_alarm(alarm, self.user_id, enqueue=False)
                    # Zaktualizuj wersję z serwera
                    server_version = winning_data.get('version', 1)
                    self.local_db.update_alarm_version(entity_id, server_version)
                    self.local_db.mark_alarm_synced(entity_id)
                else:
                    from .alarm_models import Timer
                    timer = Timer.from_dict(winning_data)
                    self.local_db.save_timer(timer, self.user_id, enqueue=False)
                    # Zaktualizuj wersję z serwera
                    server_version = winning_data.get('version', 1)
                    self.local_db.update_timer_version(entity_id, server_version)
                    self.local_db.mark_timer_synced(entity_id)
                
                return True
            
            else:  # local wins
                # Lokalna wersja wygrywa - wyślij ponownie do serwera
                if entity_type == 'alarm':
                    response = self.api_client.sync_alarm(winning_data, self.user_id)
                else:
                    response = self.api_client.sync_timer(winning_data, self.user_id)
                
                if response.success:
                    if entity_type == 'alarm':
                        self.local_db.mark_alarm_synced(entity_id)
                    else:
                        self.local_db.mark_timer_synced(entity_id)
                    return True
                else:
                    logger.error(f"Failed to sync winning local data: {response.error}")
                    return False
        
        except Exception as e:
            logger.error(f"Error resolving conflict: {e}")
            return False
    
    # =========================================================================
    # MANUAL SYNC
    # =========================================================================
    
    def sync_now(self) -> bool:
        """
        Wymuś natychmiastową synchronizację (manual trigger).
        
        Returns:
            True jeśli synchronizacja się powiodła
        """
        logger.info("Manual sync triggered")
        
        if not is_network_available():
            logger.warning("Network not available for manual sync")
            return False
        
        with self._lock:
            try:
                self._sync_cycle()
                return True
            except Exception as e:
                logger.error(f"Error in manual sync: {e}")
                return False
    
    def full_sync(self) -> bool:
        """
        Pełna synchronizacja - pobierz wszystko z serwera i porównaj.
        
        Returns:
            True jeśli pełna synchronizacja się powiodła
        """
        logger.info("Full sync triggered")
        
        if not is_network_available():
            logger.warning("Network not available for full sync")
            return False
        
        if not self.user_id:
            logger.error("Cannot perform full sync: user_id not set")
            return False
        
        try:
            # Pobierz wszystko z serwera
            response = self.api_client.fetch_all(self.user_id)
            
            if not response.success:
                logger.error(f"Failed to fetch from server: {response.error}")
                return False
            
            server_items = response.data or []
            logger.info(f"Fetched {len(server_items)} items from server")
            
            # TODO: Porównaj z lokalną bazą i synchronizuj różnice
            # To wymaga bardziej zaawansowanej logiki merge
            
            # Na razie tylko log
            logger.warning("Full sync comparison not implemented yet")
            
            return True
            
        except Exception as e:
            logger.error(f"Error in full sync: {e}")
            return False
    
    # =========================================================================
    # STATS & MONITORING
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Pobierz statystyki synchronizacji.
        
        Returns:
            Dict ze statystykami
        """
        queue = self.local_db.get_sync_queue(limit=1000)
        
        return {
            'is_running': self._is_running,
            'last_sync_time': self.last_sync_time.isoformat() if self.last_sync_time else None,
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'conflict_count': self.conflict_count,
            'queue_size': len(queue),
            'network_available': is_network_available(),
            'user_id': self.user_id,
            'sync_interval': self.sync_interval
        }
    
    def get_queue_status(self) -> List[Dict[str, Any]]:
        """
        Pobierz status kolejki synchronizacji.
        
        Returns:
            Lista items w kolejce z ich statusem
        """
        return self.local_db.get_sync_queue(limit=100)
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def cleanup_old_deleted(self, days: int = 30):
        """
        Usuń stare soft-deleted items z lokalnej bazy.
        
        Args:
            days: Usuń items starsze niż X dni
        """
        # TODO: Implementacja w LocalDatabase
        logger.info(f"Cleanup of items older than {days} days not implemented yet")


# =========================================================================
# CONTEXT MANAGER SUPPORT
# =========================================================================

class SyncManagerContext:
    """Context manager dla SyncManager"""
    
    def __init__(self, sync_manager: SyncManager):
        self.sync_manager = sync_manager
    
    def __enter__(self):
        self.sync_manager.start()
        return self.sync_manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sync_manager.stop()
        return False
