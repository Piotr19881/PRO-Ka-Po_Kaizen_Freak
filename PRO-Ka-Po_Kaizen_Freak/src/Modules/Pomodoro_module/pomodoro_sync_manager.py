"""
Sync Manager dla synchronizacji danych Pomodoro między lokalną bazą a serwerem.

Koordynuje przepływ danych:
- Lokalna baza (SQLite) ← sync → Serwer (PostgreSQL)
- Automatyczna synchronizacja w tle
- Obsługa konfliktów wersji
- Retry logic przy błędach sieciowych
"""

import threading
import time
from typing import Optional, Callable, List, Dict, Any, Union
from datetime import datetime
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal

from .pomodoro_local_database import PomodoroLocalDatabase
from .pomodoro_api_client import PomodoroAPIClient, ConflictError, APIResponse
from .pomodoro_models import PomodoroTopic, PomodoroSession, parse_datetime_field

# Import Status LED funkcji (optional)
try:
    from ...ui.status_led import record_sync_success, record_sync_error
    STATUS_LED_AVAILABLE = True
except ImportError:
    STATUS_LED_AVAILABLE = False
    logger.debug("Status LED module not available for Pomodoro")


# REMOVED: _parse_date() - duplikat parse_datetime_field() z pomodoro_models.py
# Używamy parse_datetime_field zamiast _parse_date


class SyncStatus:
    """Status synchronizacji"""
    IDLE = "idle"
    SYNCING = "syncing"
    ERROR = "error"
    SUCCESS = "success"
    CONFLICT = "conflict"


class PomodoroSyncManager(QObject):
    """
    Menedżer synchronizacji danych Pomodoro.
    
    Koordynuje przepływ danych między lokalną bazą SQLite a serwerem PostgreSQL.
    Działa w tle, automatycznie synchronizując dane w ustalonych interwałach.
    
    Signals:
        sync_started: Emitowany gdy rozpoczyna się synchronizacja
        sync_completed: Emitowany gdy synchronizacja zakończona (success: bool, message: str)
        conflict_detected: Emitowany gdy wykryto konflikt (item_type: str, local_data: dict, server_data: dict)
    """
    
    # Sygnały Qt
    sync_started = pyqtSignal()
    sync_completed = pyqtSignal(bool, str)  # success, message
    conflict_detected = pyqtSignal(str, dict, dict)  # item_type, local_data, server_data
    
    def __init__(
        self,
        local_db: PomodoroLocalDatabase,
        api_client: PomodoroAPIClient,
        auto_sync_interval: int = 300  # 5 minut
    ):
        """
        Inicjalizacja Sync Manager.
        
        Args:
            local_db: Instancja lokalnej bazy danych
            api_client: Instancja API client
            auto_sync_interval: Interwał auto-sync w sekundach (domyślnie 300s = 5min)
        """
        super().__init__()
        
        self.local_db = local_db
        self.api_client = api_client
        self.auto_sync_interval = auto_sync_interval
        
        self.status = SyncStatus.IDLE
        self.last_sync_time: Optional[datetime] = None
        self.is_running = False
        self.sync_thread: Optional[threading.Thread] = None
        
        # THREAD SAFETY: Lock do zapobiegania race condition
        self._sync_lock = threading.Lock()
        
        # Statystyki
        self.stats = {
            "topics_synced": 0,
            "sessions_synced": 0,
            "topics_failed": 0,
            "sessions_failed": 0,
            "conflicts_resolved": 0,
        }
        
        logger.info("[POMODORO SYNC] Sync Manager initialized")
    
    def start_auto_sync(self):
        """Uruchom automatyczną synchronizację w tle"""
        if self.is_running:
            logger.warning("[POMODORO SYNC] Auto-sync already running")
            return
        
        self.is_running = True
        self.sync_thread = threading.Thread(target=self._auto_sync_loop, daemon=True)
        self.sync_thread.start()
        logger.info(f"[POMODORO SYNC] Auto-sync started (interval: {self.auto_sync_interval}s)")
    
    def stop_auto_sync(self):
        """Zatrzymaj automatyczną synchronizację"""
        self.is_running = False
        if self.sync_thread:
            self.sync_thread.join(timeout=2.0)
        logger.info("[POMODORO SYNC] Auto-sync stopped")
    
    def _auto_sync_loop(self):
        """Pętla auto-sync w osobnym wątku"""
        while self.is_running:
            try:
                # Czekaj interwał
                for _ in range(self.auto_sync_interval):
                    if not self.is_running:
                        break
                    time.sleep(1)
                
                if self.is_running:
                    logger.debug("[POMODORO SYNC] Auto-sync triggered")
                    self.sync_all()
                    
            except Exception as e:
                logger.error(f"[POMODORO SYNC] Error in auto-sync loop: {e}")
                time.sleep(10)  # Czekaj 10s przed retry
    
    def sync_all(self, force: bool = False) -> bool:
        """
        Synchronizuj wszystkie dane (LOCAL-FIRST ARCHITECTURE).
        
        STRATEGIA:
        1. PULL: Pobierz wszystkie dane z serwera (źródło prawdy) i nadpisz lokalne
        2. PUSH: Wyślij lokalne "brudne" rekordy (is_synced = 0) do serwera
        3. MARK: Oznacz wysłane rekordy jako zsynchronizowane (is_synced = 1)
        
        Obsługa konfliktów: "Last Write Wins" - serwer decyduje na podstawie updated_at
        
        Args:
            force: Wymuś sync nawet jeśli nie ma niezsynchronizowanych rekordów
            
        Returns:
            True jeśli sync zakończony sukcesem, False w przeciwnym razie
        """
        # THREAD SAFETY: Użyj lock zamiast prostego sprawdzenia
        if not self._sync_lock.acquire(blocking=False):
            logger.warning("[POMODORO SYNC] Sync already in progress (locked)")
            return False
        
        try:
            self.sync_started.emit()
            self.status = SyncStatus.SYNCING
            
            logger.info("[POMODORO SYNC] ===== Starting LOCAL-FIRST sync =====")
            
            # KROK 1: PULL - Pobierz wszystkie dane z serwera (źródło prawdy)
            logger.info("[POMODORO SYNC] Step 1/3: PULL - Fetching from server (source of truth)...")
            pull_success = self._pull_server_data()
            
            if not pull_success:
                logger.warning("[POMODORO SYNC] Pull failed, continuing with push...")
            
            # KROK 2: PUSH - Pobierz niezsynchronizowane ("brudne") rekordy
            logger.info("[POMODORO SYNC] Step 2/3: PUSH - Sending local changes...")
            
            unsynced_topics = self.local_db.get_unsynced_topics()
            unsynced_sessions = self.local_db.get_unsynced_sessions()
            
            total_unsynced = len(unsynced_topics) + len(unsynced_sessions)
            
            if total_unsynced == 0 and not force:
                logger.info("[POMODORO SYNC] No local changes to push")
                self.status = SyncStatus.SUCCESS
                self.last_sync_time = datetime.now()
                self.sync_completed.emit(True, "Already synced")
                return True
            
            logger.info(f"[POMODORO SYNC] Found {len(unsynced_topics)} unsynced topics, {len(unsynced_sessions)} unsynced sessions")
            
            # KROK 2a: Wyślij tematy
            topics_success, topics_msg = self._push_topics(unsynced_topics)
            
            # KROK 2b: Wyślij sesje
            sessions_success, sessions_msg = self._push_sessions(unsynced_sessions)
            
            # KROK 3: Wynik
            overall_success = topics_success and sessions_success
            message = f"Pushed {len(unsynced_topics)} topics, {len(unsynced_sessions)} sessions. {topics_msg}, {sessions_msg}"
            
            self.status = SyncStatus.SUCCESS if overall_success else SyncStatus.ERROR
            self.last_sync_time = datetime.now()
            
            # Rejestruj event w Status LED
            if STATUS_LED_AVAILABLE:
                if overall_success:
                    record_sync_success("pomodoro")
                else:
                    record_sync_error("pomodoro")
            
            logger.info(f"[POMODORO SYNC] ===== Sync completed: {message} =====")
            self.sync_completed.emit(overall_success, message)
            
            return overall_success
            
        except Exception as e:
            logger.error(f"[POMODORO SYNC] Sync failed: {e}")
            self.status = SyncStatus.ERROR
            self.sync_completed.emit(False, f"Error: {str(e)}")
            
            # Rejestruj błąd w Status LED
            if STATUS_LED_AVAILABLE:
                record_sync_error("pomodoro")
            
            return False
        
        finally:
            # ZAWSZE zwolnij lock
            self._sync_lock.release()
    
    def _push_topics(self, unsynced_topics: List[Dict[str, Any]]) -> tuple[bool, str]:
        """
        Wyślij niezsynchronizowane tematy do serwera (PUSH w architekturze Local-First).
        
        Dla każdego tematu z is_synced = 0:
        1. Wyślij do serwera
        2. Jeśli sukces -> oznacz jako is_synced = 1
        3. Jeśli konflikt -> zastosuj "Last Write Wins" (serwer wygrywa)
        
        Args:
            unsynced_topics: Lista słowników z tematami (is_synced = 0)
            
        Returns:
            (success, message)
        """
        if not unsynced_topics:
            return True, "No topics to push"
        
        success_count = 0
        failed_count = 0
        
        for topic_data in unsynced_topics:
            topic = None
            try:
                topic = PomodoroTopic.from_dict(topic_data)
                
                # Wyślij temat do serwera
                response = self.api_client.sync_topic(topic.to_dict(), user_id=topic.user_id)
                
                if response.success:
                    # Sukces - oznacz jako zsynchronizowany
                    self.local_db.mark_topic_as_synced(topic.id)
                    success_count += 1
                    self.stats['topics_synced'] += 1
                    logger.debug(f"[POMODORO SYNC] Topic pushed & marked synced: {topic.id}")
                else:
                    failed_count += 1
                    self.stats['topics_failed'] += 1
                    logger.warning(f"[POMODORO SYNC] Topic push failed: {response.error}")
                    
            except ConflictError as e:
                # Konflikt - zastosuj "Last Write Wins"
                self.stats['conflicts_resolved'] += 1
                topic_id = topic.id if topic else topic_data.get('id', 'unknown')
                logger.warning(f"[POMODORO SYNC] Topic conflict (Last Write Wins): {topic_id}")
                self.conflict_detected.emit('topic', topic_data, e.server_data)
                
                # Serwer wygrywa - zapisz wersję z serwera i oznacz jako synced
                server_topic = PomodoroTopic.from_dict(e.server_data)
                self.local_db.save_topic(server_topic.to_dict())  # to ustawi is_synced = 1
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                self.stats['topics_failed'] += 1
                logger.error(f"[POMODORO SYNC] Error pushing topic: {e}")
        
        message = f"{success_count}/{len(unsynced_topics)} pushed"
        return failed_count == 0, message
    
    def _push_sessions(self, unsynced_sessions: List[Dict[str, Any]]) -> tuple[bool, str]:
        """
        Wyślij niezsynchronizowane sesje do serwera (PUSH w architekturze Local-First).
        
        Args:
            unsynced_sessions: Lista słowników z sesjami (is_synced = 0)
            
        Returns:
            (success, message)
        """
        if not unsynced_sessions:
            return True, "No sessions to push"
        
        success_count = 0
        failed_count = 0
        
        for session_data in unsynced_sessions:
            session = None
            try:
                session = PomodoroSession.from_dict(session_data)
                
                # Wyślij sesję do serwera
                response = self.api_client.sync_session(session.to_dict(), user_id=session.user_id)
                
                if response.success:
                    # Sukces - oznacz jako zsynchronizowaną
                    self.local_db.mark_session_as_synced(session.id)
                    success_count += 1
                    self.stats['sessions_synced'] += 1
                    logger.debug(f"[POMODORO SYNC] Session pushed & marked synced: {session.id}")
                else:
                    failed_count += 1
                    self.stats['sessions_failed'] += 1
                    logger.warning(f"[POMODORO SYNC] Session push failed: {response.error}")
                    
            except ConflictError as e:
                # Konflikt - zastosuj "Last Write Wins"
                self.stats['conflicts_resolved'] += 1
                logger.warning(f"[POMODORO SYNC] Session conflict (Last Write Wins): {session.id if session else 'unknown'}")
                self.conflict_detected.emit('session', session_data, e.server_data)
                
                # Serwer wygrywa - zapisz wersję z serwera i oznacz jako synced
                server_session = PomodoroSession.from_dict(e.server_data)
                self.local_db.save_session(server_session.to_dict())  # to ustawi is_synced = 1
                success_count += 1
                
            except Exception as e:
                failed_count += 1
                self.stats['sessions_failed'] += 1
                logger.error(f"[POMODORO SYNC] Error pushing session: {e}")
        
        message = f"{success_count}/{len(unsynced_sessions)} pushed"
        return failed_count == 0, message
    
    def _pull_server_data(self) -> bool:
        """
        Pobierz dane z serwera (źródło prawdy).
        
        STRATEGIA: Baza sieciowa nadpisuje lokalną na podstawie daty updated_at
        - Dla każdego rekordu z serwera, sprawdź datę updated_at
        - Jeśli serwer ma nowszą datę LUB rekord nie istnieje lokalnie -> NADPISZ
        - Jeśli brak daty -> użyj created_at
        
        Returns:
            True jeśli sukces, False w przypadku błędu
        """
        try:
            logger.debug("[POMODORO SYNC] Pulling data from server (source of truth)...")
            
            # Pobierz wszystkie dane z serwera
            response = self.api_client.fetch_all(user_id=self.local_db.user_id)
            
            if not response.success:
                logger.warning(f"[POMODORO SYNC] Failed to pull server data: {response.error}")
                return False
            
            data = response.data
            
            # Przekonwertuj dane z serwera - mapuj server_id → id
            topics_raw = data.get('topics', [])
            sessions_raw = data.get('sessions', [])
            
            # Fix: Backend zwraca 'server_id', ale model oczekuje 'id'
            for topic in topics_raw:
                if 'server_id' in topic and 'id' not in topic:
                    topic['id'] = topic['local_id']  # Użyj local_id jako id
            
            for session in sessions_raw:
                if 'server_id' in session and 'id' not in session:
                    session['id'] = session['local_id']  # Użyj local_id jako id
            
            topics = [PomodoroTopic.from_dict(t) for t in topics_raw]
            sessions = [PomodoroSession.from_dict(s) for s in sessions_raw]
            
            topics_updated = 0
            sessions_updated = 0
            
            # Przetwórz tematy z serwera
            for server_topic in topics:
                should_update = False
                existing = self.local_db.get_topic_by_local_id(server_topic.local_id)
                
                if not existing:
                    # Nowy rekord z serwera
                    should_update = True
                    logger.debug(f"[POMODORO SYNC] New topic from server: {server_topic.local_id}")
                else:
                    # Porównaj daty (updated_at lub created_at)
                    server_date_raw = server_topic.updated_at or server_topic.created_at
                    local_date_raw = existing.updated_at or existing.created_at
                    
                    server_date = parse_datetime_field(server_date_raw)
                    local_date = parse_datetime_field(local_date_raw)
                    
                    if server_date and local_date:
                        if server_date >= local_date:
                            should_update = True
                            logger.debug(f"[POMODORO SYNC] Server topic is newer: {server_topic.local_id}")
                    else:
                        # Brak dat - zaktualizuj z serwera (źródło prawdy)
                        should_update = True
                
                if should_update:
                    self.local_db.save_topic(server_topic.to_dict())
                    topics_updated += 1
            
            # Przetwórz sesje z serwera
            for server_session in sessions:
                should_update = False
                existing = self.local_db.get_session_by_local_id(server_session.local_id)
                
                if not existing:
                    # Nowa sesja z serwera
                    should_update = True
                    logger.debug(f"[POMODORO SYNC] New session from server: {server_session.local_id}")
                else:
                    # Porównaj daty
                    server_date_raw = server_session.updated_at or server_session.created_at
                    local_date_raw = existing.updated_at or existing.created_at
                    
                    server_date = parse_datetime_field(server_date_raw)
                    local_date = parse_datetime_field(local_date_raw)
                    
                    if server_date and local_date:
                        if server_date >= local_date:
                            should_update = True
                            logger.debug(f"[POMODORO SYNC] Server session is newer: {server_session.local_id}")
                    else:
                        # Brak dat - zaktualizuj z serwera (źródło prawdy)
                        should_update = True
                
                if should_update:
                    self.local_db.save_session(server_session.to_dict())
                    sessions_updated += 1
            
            logger.info(f"[POMODORO SYNC] Pulled from server: {topics_updated}/{len(topics)} topics, {sessions_updated}/{len(sessions)} sessions updated")
            return True
            
        except Exception as e:
            logger.error(f"[POMODORO SYNC] Error pulling server data: {e}")
            return False
    
    def _resolve_topic_conflict(self, local_topic: PomodoroTopic, server_data: Dict[str, Any]):
        """
        Rozwiąż konflikt tematu.
        
        Strategia: Server wins - użyj wersji z serwera
        """
        try:
            server_topic = PomodoroTopic.from_dict(server_data)
            
            # Zapisz wersję z serwera lokalnie
            self.local_db.save_topic(server_topic.to_dict())
            
            logger.info(f"[POMODORO SYNC] Conflict resolved for topic {local_topic.local_id}: server wins")
            
        except Exception as e:
            logger.error(f"[POMODORO SYNC] Error resolving topic conflict: {e}")
    
    def _resolve_session_conflict(self, local_session: PomodoroSession, server_data: Dict[str, Any]):
        """
        Rozwiąż konflikt sesji.
        
        Strategia: Server wins - użyj wersji z serwera
        """
        try:
            server_session = PomodoroSession.from_dict(server_data)
            
            # Zapisz wersję z serwera lokalnie
            self.local_db.save_session(server_session.to_dict())
            
            logger.info(f"[POMODORO SYNC] Conflict resolved for session {local_session.local_id}: server wins")
            
        except Exception as e:
            logger.error(f"[POMODORO SYNC] Error resolving session conflict: {e}")
    
    def sync_now(self) -> bool:
        """
        Wykonaj natychmiastową synchronizację.
        
        Returns:
            True jeśli sukces, False w przeciwnym razie
        """
        logger.info("[POMODORO SYNC] Manual sync triggered")
        return self.sync_all(force=True)
    
    def get_stats(self) -> Dict[str, Any]:
        """Pobierz statystyki synchronizacji"""
        return {
            **self.stats,
            "status": self.status,
            "last_sync": self.last_sync_time.isoformat() if self.last_sync_time else None,
            "is_running": self.is_running,
        }
    
    def reset_stats(self):
        """Zresetuj statystyki"""
        self.stats = {
            "topics_synced": 0,
            "sessions_synced": 0,
            "topics_failed": 0,
            "sessions_failed": 0,
            "conflicts_resolved": 0,
        }
        logger.debug("[POMODORO SYNC] Stats reset")
