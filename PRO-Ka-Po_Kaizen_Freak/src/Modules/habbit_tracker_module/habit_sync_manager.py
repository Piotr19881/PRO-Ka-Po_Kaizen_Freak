"""
Habit Sync Manager - zarządzanie synchronizacją habit trackera w tle.

Ten moduł obsługuje:
- Background synchronizację kolumn i rekordów habit trackera z serwerem
- Kolejkowanie operacji
- Wykrywanie dostępności sieci
- Rozwiązywanie konfliktów
- Retry logic z exponential backoff
- Batch synchronizację
"""

import json
import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta, date
from threading import Thread, Event, Lock
from loguru import logger

from .habit_database import HabitDatabase
from .habit_api_client import HabitAPIClient, APIResponse, ConflictError, is_network_available

# Import Status LED funkcji (optional - jeśli moduł UI nie jest dostępny, nie zepsuje się)
try:
    from ...ui.status_led import record_sync_success, record_sync_error
    STATUS_LED_AVAILABLE = True
except ImportError:
    STATUS_LED_AVAILABLE = False
    logger.debug("Status LED module not available")


class HabitSyncManager:
    """
    Menedżer synchronizacji dla habit tracker local-first architecture.
    
    Uruchamia background worker, który:
    - Monitoruje sync_queue
    - Sprawdza dostępność sieci
    - Synchronizuje zmiany z serwerem
    - Rozwiązuje konflikty
    - Retry przy błędach z exponential backoff
    """
    
    def __init__(
        self,
        habit_db: HabitDatabase,
        api_client: HabitAPIClient,
        user_id: Optional[str] = None,
        sync_interval: int = 300,
        max_retries: int = 3
    ):
        """
        Inicjalizacja Habit Sync Manager.
        
        Args:
            habit_db: HabitDatabase instance
            api_client: HabitAPIClient instance
            user_id: ID użytkownika (jeśli None, musi być ustawiony później)
            sync_interval: Interwał synchronizacji w sekundach (domyślnie 30s)
            max_retries: Maksymalna liczba ponowień przy błędzie
        """
        self.habit_db = habit_db
        self.api_client = api_client
        self.user_id = user_id
        self.sync_interval = sync_interval
        self.max_retries = max_retries
        
        # Threading
        self._worker_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._sync_now_event = Event()
        self._lock = Lock()
        self._is_running = False
        
        # Stats
        self.last_sync_time: Optional[datetime] = None
        self.sync_count = 0
        self.error_count = 0
        self.conflict_count = 0
        
        logger.info(f"HabitSyncManager initialized (interval={sync_interval}s, max_retries={max_retries})")
    
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
            logger.warning("Habit sync worker is already running")
            return
        
        if not self.user_id:
            logger.error("Cannot start habit sync worker: user_id not set")
            raise ValueError("user_id must be set before starting habit sync worker")
        
        self._stop_event.clear()
        self._sync_now_event.clear()
        self._is_running = True
        self._worker_thread = Thread(target=self._worker_loop, daemon=True, name="HabitSyncWorker")
        self._worker_thread.start()
        logger.info(f"🚀 [HABIT SYNC] Worker started for user {self.user_id}, interval={self.sync_interval}s")
    
    def stop(self, wait: bool = True, timeout: float = 5.0):
        """
        Zatrzymaj background worker.
        
        Args:
            wait: Czy czekać na zakończenie worker thread
            timeout: Timeout w sekundach dla join()
        """
        if not self._is_running:
            logger.warning("Habit sync worker is not running")
            return
        
        logger.info("Stopping habit sync worker...")
        self._stop_event.set()
        self._sync_now_event.set()
        self._is_running = False
        
        if wait and self._worker_thread:
            self._worker_thread.join(timeout=timeout)
            if self._worker_thread.is_alive():
                logger.warning("Habit sync worker did not stop within timeout")
            else:
                logger.info("Habit sync worker stopped")

    def request_immediate_sync(self, reason: str = "manual"):
        """
        Obudź worker aby wykonać synchronizację jak najszybciej.

        Args:
            reason: Kontekst zdarzenia uruchamiającego synchronizację (logi)
        """
        if not self._is_running:
            logger.debug(f"[HABIT SYNC] Immediate sync requested ({reason}) but worker is not running")
            return

        logger.debug(f"[HABIT SYNC] Immediate sync requested ({reason})")
        self._sync_now_event.set()
    
    def is_running(self) -> bool:
        """Sprawdź czy worker działa"""
        return self._is_running
    
    def initial_sync(self) -> bool:
        """
        Wykonaj początkową synchronizację - pobierz wszystkie dane z serwera.
        
        Returns:
            True jeśli synchronizacja się udała
        """
        if not self.user_id:
            logger.error("Cannot perform initial sync: user_id not set")
            return False
        
        try:
            logger.info("Starting initial habit tracker sync...")
            
            # Mapowanie type (angielski -> polski) dla lokalnej bazy
            type_mapping_reverse = {
                'checkbox': 'Checkbox',
                'counter': 'Licznik',
                'scale': 'Skala',
                'duration': 'Czas trwania',
                'text': 'Tekst',
                'time': 'time'
            }
            
            # Pobierz kolumny z serwera
            columns_response = self.api_client.fetch_habit_columns(self.user_id)
            columns_count = 0
            
            if columns_response.success:
                # API zwraca: {"items": [...], "count": N, "last_sync": "..."}
                response_data = columns_response.data or {}
                columns = response_data.get('items', []) if isinstance(response_data, dict) else []
                logger.info(f"Fetched {len(columns)} habit columns from server")
                
                for column_data in columns:
                    # API zwraca 'type', ale lokalna baza używa 'habit_type' (polski)
                    habit_type_en = column_data.get('type', 'text')
                    habit_type_pl = type_mapping_reverse.get(habit_type_en, 'Tekst')
                    
                    # Zapisz kolumnę do lokalnej bazy z is_synced=1 (dane z serwera)
                    self.habit_db.save_habit_column(
                        column_id=column_data['id'],
                        name=column_data['name'],
                        habit_type=habit_type_pl,  # Użyj polskiej nazwy
                        color=column_data.get('color', '#3498db'),
                        is_active=column_data.get('is_active', True),
                        scale_max=column_data.get('scale_max'),
                        is_synced=1  # Dane z serwera = zsynchronizowane
                    )
                    # Dodatkowo oznacz jako zsynchronizowane (redundantne, ale bezpieczne)
                    self.habit_db.mark_column_synced(column_data['id'])
                    columns_count += 1
            
            # Pobierz rekordy z serwera (ostatnie 3 miesiące)
            records_response = self.api_client.fetch_habit_records(self.user_id)
            records_count = 0
            
            if records_response.success:
                # API zwraca: {"items": [...], "count": N, "last_sync": "..."}
                response_data = records_response.data or {}
                records = response_data.get('items', []) if isinstance(response_data, dict) else []
                logger.info(f"Fetched {len(records)} habit records from server")
                
                for record_data in records:
                    # API zwraca 'habit_id' i 'date', ale lokalna baza używa 'column_id' i 'record_date'
                    column_id = record_data.get('habit_id')
                    record_date_str = record_data.get('date')
                    
                    if column_id and record_date_str:
                        record_date = date.fromisoformat(record_date_str)
                        self.habit_db.save_habit_record(
                            column_id=column_id,
                            record_date=record_date,
                            value=record_data['value'],
                            notes=record_data.get('notes', ''),
                            is_synced=1  # Dane z serwera = zsynchronizowane
                        )
                        # Dodatkowo oznacz jako zsynchronizowany (redundantne, ale bezpieczne)
                        record_id = record_data.get('id')
                        if record_id:
                            self.habit_db.mark_record_synced(record_id)
                        records_count += 1
            
            logger.success(f"Initial habit sync complete: {columns_count} columns, {records_count} records")
            return True
            
        except Exception as e:
            logger.error(f"Failed to perform initial habit sync: {e}")
            import traceback
            logger.error(traceback.format_exc())
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
        logger.info(f"🔄 [HABIT SYNC] Worker loop started for user {self.user_id}")
        
        while not self._stop_event.is_set():
            try:
                # Sprawdź czy jest sieć
                if is_network_available():
                    logger.debug(f"🌐 [HABIT SYNC] Network available, executing sync cycle...")
                    # Wykonaj synchronizację
                    self._sync_cycle()
                else:
                    logger.debug("📡 [HABIT SYNC] Network not available, skipping sync")
                
                # Czekaj przed następnym cyklem lub do czasu otrzymania sygnału natychmiastowej synchronizacji
                logger.debug(f"⏱️  [HABIT SYNC] Waiting up to {self.sync_interval}s before next cycle...")
                wait_deadline = datetime.utcnow() + timedelta(seconds=self.sync_interval)
                while not self._stop_event.is_set():
                    remaining = (wait_deadline - datetime.utcnow()).total_seconds()
                    if remaining <= 0:
                        break

                    triggered = self._sync_now_event.wait(timeout=min(1.0, max(0.05, remaining)))
                    if triggered:
                        logger.debug("⚡ [HABIT SYNC] Immediate sync trigger received - resuming now")
                        self._sync_now_event.clear()
                        break
                
            except Exception as e:
                logger.error(f"❌ [HABIT SYNC] Error in worker loop: {e}")
                self.error_count += 1
                # Czekaj przed retry
                wait_timeout = min(self.sync_interval, 10)
                logger.debug(f"⏳ [HABIT SYNC] Cooling down for {wait_timeout}s due to error")
                self._stop_event.wait(timeout=wait_timeout)
        
        logger.info("🛑 [HABIT SYNC] Worker loop exited")
    
    def _sync_cycle(self):
        """
        Jeden cykl synchronizacji.
        
        Pobiera items z sync_queue i synchronizuje z serwerem.
        WAŻNE: Najpierw synchronizuje kolumny, potem rekordy (foreign key dependency).
        """
        if not self.user_id:
            logger.error("[HABIT SYNC] Cannot execute sync cycle without user_id")
            return

        user_id = self.user_id

        with self._lock:
            try:
                requeue_stats = self.habit_db.requeue_unsynced_items()
                if requeue_stats.get('columns') or requeue_stats.get('records'):
                    logger.debug(
                        f"📥 [HABIT SYNC] Requeued {requeue_stats['columns']} columns and {requeue_stats['records']} records"
                    )

                # Pobierz kolejkę sync (dla habit trackera)
                queue = self.habit_db.get_sync_queue(limit=20)
                
                if not queue:
                    logger.debug("📭 [HABIT SYNC] Queue is empty, nothing to sync")
                    return
                
                # SORTUJ KOLEJKĘ: habit_column PRZED habit_record (foreign key dependency)
                # Najpierw kolumny muszą być na serwerze, zanim zapiszemy rekordy
                queue_sorted = sorted(queue, key=lambda x: 0 if x['entity_type'] == 'habit_column' else 1)
                
                logger.info(f"📦 [HABIT SYNC] Processing {len(queue_sorted)} items from sync queue")
                
                success_count = 0
                failed_count = 0
                
                for item in queue_sorted:
                    try:
                        logger.debug(f"🔄 [HABIT SYNC] Syncing: {item['entity_type']} {item['entity_id']} ({item['action']})")
                        result = self._sync_item(item)
                        if result:
                            success_count += 1
                            logger.debug(f"✅ [HABIT SYNC] Success: {item['entity_id']}")
                        else:
                            failed_count += 1
                            logger.warning(f"⚠️ [HABIT SYNC] Failed: {item['entity_id']}")
                    except Exception as e:
                        logger.error(f"❌ [HABIT SYNC] Error syncing {item['entity_id']}: {e}")
                        failed_count += 1
                
                self.last_sync_time = datetime.now()
                self.sync_count += 1
                
                # Rejestruj event w Status LED
                if STATUS_LED_AVAILABLE and 'record_sync_success' in globals() and 'record_sync_error' in globals():
                    if failed_count == 0 and success_count > 0:
                        record_sync_success("habits")
                    elif failed_count > 0:
                        record_sync_error("habits")
                
                logger.info(f"✨ [HABIT SYNC] Cycle completed: {success_count} ✅ success, {failed_count} ❌ failed")
                
            except Exception as e:
                logger.error(f"❌ [HABIT SYNC] Error in sync cycle: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.error_count += 1
    
    def _sync_item(self, queue_item: Dict[str, Any]) -> bool:
        """
        Synchronizuj pojedynczy element z kolejki.
        
        Args:
            queue_item: Element z sync_queue
            
        Returns:
            True jeśli synchronizacja się udała
        """
        entity_type = queue_item['entity_type']  # 'habit_column' lub 'habit_record'
        entity_id = queue_item['entity_id']
        action = queue_item['action']  # 'create', 'update', 'delete'
        
        logger.debug(f"Syncing habit {entity_type} {entity_id} ({action})")
        
        if not self.user_id:
            logger.error("[HABIT SYNC] Skipping sync item because user_id is not set")
            self.habit_db.remove_from_sync_queue(queue_item['id'])
            return False

        try:
            # Pobierz dane z lokalnej bazy
            if entity_type == 'habit_column':
                if action == 'delete':
                    # Dla soft delete, wyślij tylko ID
                    response = self.api_client.delete_habit_column(entity_id, soft=True)
                else:
                    # Pobierz dane kolumny
                    data = self.habit_db.get_column_sync_data(entity_id)
                    if not data:
                        logger.warning(f"Habit column {entity_id} not found locally, removing from queue")
                        self.habit_db.remove_from_sync_queue(queue_item['id'])
                        return False
                    
                    response = self.api_client.sync_habit_column(data, self.user_id)
            
            elif entity_type == 'habit_record':
                if action == 'delete':
                    # Dla soft delete, wyślij tylko ID
                    response = self.api_client.delete_habit_record(entity_id, soft=True)
                else:
                    # Pobierz dane rekordu
                    data = self.habit_db.get_record_sync_data(entity_id)
                    if not data:
                        logger.warning(f"Habit record {entity_id} not found locally, removing from queue")
                        self.habit_db.remove_from_sync_queue(queue_item['id'])
                        return False
                    
                    response = self.api_client.sync_habit_record(data, self.user_id)
            
            else:
                logger.error(f"Unknown habit entity type: {entity_type}")
                self.habit_db.remove_from_sync_queue(queue_item['id'])
                return False
            
            if response.success:
                logger.info(f"Successfully synced habit {entity_id} to server")
                
                # Zaktualizuj wersję z odpowiedzi serwera
                if response.data and 'version' in response.data:
                    new_version = response.data['version']
                    logger.debug(f"Updating local version to {new_version} for {entity_id}")
                    
                    if entity_type == 'habit_column':
                        self.habit_db.update_column_version(entity_id, new_version)
                        self.habit_db.mark_column_synced(entity_id)
                    else:  # habit_record
                        self.habit_db.update_record_version(entity_id, new_version)
                        self.habit_db.mark_record_synced(entity_id)
                
                # Usuń z kolejki sync
                self.habit_db.remove_from_sync_queue(queue_item['id'])
                return True
            else:
                if response.status_code == 404 and action == 'delete':
                    logger.info(
                        f"Habit {entity_type} {entity_id} already missing on backend; marking as synced and dropping queue entry"
                    )
                    if entity_type == 'habit_column':
                        self.habit_db.mark_column_synced(entity_id)
                    else:
                        self.habit_db.mark_record_synced(entity_id)
                    self.habit_db.remove_from_sync_queue(queue_item['id'])
                    return True

                logger.error(f"Failed to sync habit {entity_id}: {response.error}")
                
                # Zwiększ retry_count
                retry_count = queue_item.get('retry_count', 0) + 1
                
                if retry_count >= self.max_retries:
                    logger.error(f"Max retries exceeded for habit {entity_id}, removing from queue")
                    self.habit_db.remove_from_sync_queue(queue_item['id'])
                else:
                    # Zaktualizuj retry count i error
                    self.habit_db.update_sync_queue_error(queue_item['id'], response.error or 'Unknown error')
                
                return False
                
        except ConflictError as e:
            logger.warning(f"Version conflict for habit {entity_id}: {e}")
            self.conflict_count += 1
            
            # Spróbuj rozwiązać konflikt
            try:
                resolved = self._resolve_conflict(entity_type, entity_id, e.server_data)
                if resolved:
                    # Usuń z kolejki po rozwiązaniu konfliktu
                    self.habit_db.remove_from_sync_queue(queue_item['id'])
                    return True
                else:
                    # Konflikt nierozwiązany, usuń z kolejki
                    self.habit_db.remove_from_sync_queue(queue_item['id'])
                    return False
            except Exception as resolve_error:
                logger.error(f"Error resolving habit conflict: {resolve_error}")
                self.habit_db.remove_from_sync_queue(queue_item['id'])
                return False
                
        except Exception as e:
            logger.error(f"Unexpected error syncing habit {entity_id}: {e}")
            
            # Zwiększ retry_count
            retry_count = queue_item.get('retry_count', 0) + 1
            
            if retry_count >= self.max_retries:
                logger.error(f"Max retries exceeded for habit {entity_id}, removing from queue")
                self.habit_db.remove_from_sync_queue(queue_item['id'])
            else:
                self.habit_db.update_sync_queue_error(queue_item['id'], str(e))
            
            return False
    
    # =========================================================================
    # CONFLICT RESOLUTION
    # =========================================================================
    
    def _resolve_conflict(
        self, 
        entity_type: str, 
        entity_id: str, 
        server_data: Dict[str, Any]
    ) -> bool:
        """
        Rozwiąż konflikt wersji używając strategii last-write-wins.
        
        Args:
            entity_type: Typ entity ('habit_column' lub 'habit_record')
            entity_id: ID entity
            server_data: Dane z serwera
            
        Returns:
            True jeśli konflikt został rozwiązany
        """
        try:
            logger.info(f"Resolving habit conflict for {entity_type} {entity_id}")
            
            # Pobierz lokalne dane
            if entity_type == 'habit_column':
                local_data = self.habit_db.get_column_sync_data(entity_id)
            else:  # habit_record
                local_data = self.habit_db.get_record_sync_data(entity_id)
            
            if not local_data:
                logger.warning(f"Local data not found for {entity_id}, accepting server version")
                # Zapisz dane z serwera do lokalnej bazy
                self._apply_server_data(entity_type, server_data)
                return True
            
            # Użyj API client do rozwiązania konfliktu
            resolved_data, winner = self.api_client.resolve_conflict(
                local_data, server_data, strategy='last_write_wins'
            )
            
            if winner == 'server':
                logger.info(f"Conflict resolved: accepting server version for {entity_id}")
                # Zaktualizuj lokalną bazę danymi z serwera
                self._apply_server_data(entity_type, resolved_data)
            else:
                logger.info(f"Conflict resolved: keeping local version for {entity_id}")
                # Ponów synchronizację z aktualnymi lokalnymi danymi
                # (worker spróbuje ponownie w następnym cyklu)
            
            return True
            
        except Exception as e:
            logger.error(f"Error resolving habit conflict for {entity_id}: {e}")
            return False
    
    def _apply_server_data(self, entity_type: str, server_data: Dict[str, Any]):
        """
        Zastosuj dane z serwera do lokalnej bazy.
        
        Args:
            entity_type: Typ entity ('habit_column' lub 'habit_record')
            server_data: Dane z serwera
        """
        try:
            if entity_type == 'habit_column':
                self.habit_db.save_habit_column(
                    column_id=server_data['id'],
                    name=server_data['name'],
                    habit_type=server_data['habit_type'],
                    color=server_data.get('color', '#3498db'),
                    is_active=server_data.get('is_active', True)
                )
                self.habit_db.mark_column_synced(server_data['id'])
                
            else:  # habit_record
                # API zwraca 'date', nie 'record_date'
                record_date_str = server_data.get('date') or server_data.get('record_date')
                if not record_date_str:
                    logger.error(f"Missing date field in server data for record {server_data.get('id')}")
                    return

                record_date = date.fromisoformat(record_date_str)
                self.habit_db.save_habit_record(
                    column_id=server_data['habit_id'],  # API używa 'habit_id'
                    record_date=record_date,
                    value=server_data['value'],
                    notes=server_data.get('notes', '')
                )
                self.habit_db.mark_record_synced(server_data['id'])
                
            logger.info(f"Applied server data for {entity_type} {server_data['id']}")
            
        except Exception as e:
            logger.error(f"Error applying server data: {e}")
    
    # =========================================================================
    # MANUAL SYNC
    # =========================================================================
    
    def sync_now(self) -> bool:
        """
        Wymuś natychmiastową synchronizację (manual trigger).
        
        Returns:
            True jeśli synchronizacja się powiodła
        """
        logger.info("Manual habit sync triggered")
        
        if not is_network_available():
            logger.warning("Network not available for manual habit sync")
            return False
        
        with self._lock:
            try:
                self._sync_cycle()
                return True
            except Exception as e:
                logger.error(f"Error in manual habit sync: {e}")
                return False
    
    def full_sync(self) -> bool:
        """
        Wykonaj pełną synchronizację - wyślij wszystkie dane na serwer.
        
        Returns:
            True jeśli synchronizacja się powiodła
        """
        if not self.user_id:
            logger.error("Cannot perform full habit sync: user_id not set")
            return False
        
        try:
            logger.info("Starting full habit sync...")
            
            # Pobierz wszystkie kolumny i rekordy
            columns = self.habit_db.get_all_columns()
            records = self.habit_db.get_all_records()
            
            # Przygotuj dane do bulk sync
            columns_data = []
            for column in columns:
                columns_data.append(self.habit_db.get_column_sync_data(column['id']))
            
            records_data = []
            for record in records:
                records_data.append(self.habit_db.get_record_sync_data(record['id']))
            
            # Wykonaj bulk sync
            response = self.api_client.bulk_sync(
                user_id=self.user_id,
                columns=columns_data,
                records=records_data,
                last_sync=self.last_sync_time
            )
            
            if response.success:
                logger.success("Full habit sync completed successfully")
                # Wyczyść kolejkę sync po udanej pełnej synchronizacji
                self.habit_db.clear_sync_queue()
                self.habit_db.mark_all_synced()
                return True
            else:
                logger.error(f"Full habit sync failed: {response.error}")
                return False
                
        except Exception as e:
            logger.error(f"Error in full habit sync: {e}")
            return False

    def force_full_resync(self) -> bool:
        """Wymuś pełną synchronizację wszystkich danych habit trackera."""

        if not self.user_id:
            logger.error("Cannot force habit resync: user_id not set")
            return False

        with self._lock:
            try:
                logger.info("Forcing full habit resync (marking all data unsynced)")
                marked = self.habit_db.mark_all_for_resync()
                logger.debug(
                    f"Marked {marked['columns']} columns and {marked['records']} records for resync"
                )
                self.habit_db.requeue_unsynced_items()
                success = self.full_sync()
            except Exception as err:
                logger.error(f"Failed to prepare data for force resync: {err}")
                return False

        if success:
            logger.success("Force full habit resync completed")
        else:
            logger.error("Force full habit resync failed during bulk sync")

        return success
    
    # =========================================================================
    # STATS & MONITORING
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Pobierz statystyki synchronizacji.
        
        Returns:
            Dict ze statystykami
        """
        queue = self.habit_db.get_sync_queue(limit=1000)
        
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
        return self.habit_db.get_sync_queue(limit=100)
    
    # =========================================================================
    # CLEANUP
    # =========================================================================
    
    def cleanup_old_deleted(self, days: int = 30):
        """
        Wyczyść stare soft-deleted rekordy starsze niż podana liczba dni.
        
        Args:
            days: Liczba dni (domyślnie 30)
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            
            # Usuń stare soft-deleted kolumny
            deleted_columns = self.habit_db.cleanup_deleted_columns(cutoff_date)
            
            # Usuń stare soft-deleted rekordy
            deleted_records = self.habit_db.cleanup_deleted_records(cutoff_date)
            
            logger.info(f"Cleaned up {deleted_columns} old deleted columns and {deleted_records} old deleted records")
            
        except Exception as e:
            logger.error(f"Error cleaning up old deleted habit data: {e}")


# =========================================================================
# CONTEXT MANAGER SUPPORT
# =========================================================================

class HabitSyncManagerContext:
    """Context manager dla HabitSyncManager"""
    
    def __init__(self, sync_manager: HabitSyncManager):
        self.sync_manager = sync_manager
    
    def __enter__(self):
        self.sync_manager.start()
        return self.sync_manager
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.sync_manager.stop()
        return False