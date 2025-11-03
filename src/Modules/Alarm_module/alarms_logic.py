"""
Alarm Module Logic - Logika alarmów i timerów z synchronizacją
"""
from datetime import datetime, time, timedelta
from typing import List, Dict, Optional, Callable
from pathlib import Path
from loguru import logger
import json

# Import modeli
from .alarm_models import Alarm, Timer, AlarmRecurrence

# Import komponentów synchronizacji
try:
    from .alarm_local_database import LocalDatabase
    from .alarms_sync_manager import SyncManager
    from .alarm_api_client import create_api_client
    from .alarm_websocket_client import create_websocket_client, WebSocketClient
except ImportError as e:
    # Fallback dla backward compatibility
    logger.warning(f"Sync components not available: {e}")
    LocalDatabase = None
    SyncManager = None
    create_api_client = None
    create_websocket_client = None
    WebSocketClient = None


class AlarmManager:
    """
    Menedżer alarmów i timerów z synchronizacją local-first.
    
    Features:
    - Local-first architecture (LocalDatabase + JSON fallback)
    - Background synchronization (SyncManager)
    - Real-time updates (WebSocket)
    - Offline support
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
        Initialize AlarmManager.
        
        Args:
            data_dir: Katalog z danymi lokalnymi
            user_id: ID użytkownika (wymagane dla sync)
            api_base_url: URL API serwera (np. "http://localhost:8000")
            auth_token: JWT access token
            refresh_token: JWT refresh token do automatycznego odświeżania
            on_token_refreshed: Callback wywoływany po odświeżeniu tokena: (new_access_token, new_refresh_token) -> None
            enable_sync: Czy włączyć synchronizację (True) czy tylko local storage (False)
        """
        self.data_dir = data_dir
        self.alarms_file = data_dir / "alarms.json"
        self.timers_file = data_dir / "timers.json"
        
        self.alarms: List[Alarm] = []
        self.timers: List[Timer] = []
        
        # Sync configuration
        self.user_id = user_id
        self.refresh_token = refresh_token
        self.auth_token = auth_token  # Przechowuj aktualny token
        self.on_token_refreshed = on_token_refreshed
        self.enable_sync = enable_sync and LocalDatabase is not None
        
        if enable_sync and LocalDatabase is None:
            logger.error("Sync requested but LocalDatabase not available - check imports!")
        
        # Sync components (inicjalizowane później)
        self.local_db: Optional[LocalDatabase] = None
        self.sync_manager: Optional[SyncManager] = None
        self.ws_client: Optional[WebSocketClient] = None
        
        # UI callbacks dla real-time updates
        self.on_alarm_changed: Optional[Callable[[Alarm], None]] = None
        self.on_timer_changed: Optional[Callable[[Timer], None]] = None
        
        # Initialize
        self._load_data()
        
        if self.enable_sync:
            self._init_sync(api_base_url, auth_token)
    
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
        
        try:
            # Wrapper callback dla token refresh
            def on_token_refreshed_wrapper(new_access_token: str, new_refresh_token: str):
                """Callback wywoływany po odświeżeniu tokena - aktualizuje WebSocket"""
                # Zaktualizuj token w tym obiekcie
                self.auth_token = new_access_token
                self.refresh_token = new_refresh_token
                
                # Zaktualizuj token w WebSocket client (jeśli już istnieje)
                if self.ws_client:
                    self.ws_client.update_token(new_access_token)
                    logger.info("✓ WebSocket token updated after refresh - will use new token on next reconnect")
                
                # Wywołaj oryginalny callback (np. do zapisu w main.py)
                if self.on_token_refreshed:
                    self.on_token_refreshed(new_access_token, new_refresh_token)
            
            # LocalDatabase
            db_path = self.data_dir / "alarms.db"
            self.local_db = LocalDatabase(db_path)
            logger.info(f"LocalDatabase initialized: {db_path}")
            
            # API Client z wrapper callback
            api_client = create_api_client(
                base_url=api_base_url,
                auth_token=auth_token,
                refresh_token=self.refresh_token,
                on_token_refreshed=on_token_refreshed_wrapper  # Użyj wrappera
            )
            logger.info("API Client configured")
            
            # SyncManager
            self.sync_manager = SyncManager(
                local_db=self.local_db,
                api_client=api_client,
                user_id=self.user_id,
                sync_interval=30  # Sync co 30 sekund
            )
            self.sync_manager.start()
            logger.info("SyncManager started")
            
            # Initial sync - pobierz dane z serwera
            logger.info("Performing initial sync from server...")
            if self.sync_manager.initial_sync():
                logger.success("Initial sync completed successfully")
            else:
                logger.warning("Initial sync failed - will retry in background")
            
            # WebSocket Client
            self.ws_client = create_websocket_client(
                base_url=api_base_url,
                auth_token=auth_token,
                on_alarm_updated=self._handle_alarm_ws_update,
                on_timer_updated=self._handle_timer_ws_update,
                on_sync_required=self._handle_sync_required,
                auto_reconnect=True
            )
            self.ws_client.start()
            logger.info("WebSocket client started")
            
            # Load initial data from LocalDatabase
            self._load_from_local_db()
            
            logger.success("Sync enabled: LocalDB + SyncManager + WebSocket")
        
        except Exception as e:
            logger.error(f"Failed to initialize sync: {e}")
            self.enable_sync = False
            # Fallback to JSON files
    
    def _load_data(self):
        """Załaduj alarmy i timery z plików JSON (fallback)"""
        # Załaduj alarmy
        if self.alarms_file.exists():
            try:
                with open(self.alarms_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.alarms = [Alarm.from_dict(item) for item in data]
                logger.info(f"Loaded {len(self.alarms)} alarms from JSON")
            except Exception as e:
                logger.error(f"Failed to load alarms: {e}")
        
        # Załaduj timery
        if self.timers_file.exists():
            try:
                with open(self.timers_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.timers = [Timer.from_dict(item) for item in data]
                logger.info(f"Loaded {len(self.timers)} timers from JSON")
            except Exception as e:
                logger.error(f"Failed to load timers: {e}")
    
    def _load_from_local_db(self):
        """Załaduj dane z LocalDatabase (priorytet nad JSON)"""
        if not self.local_db:
            return
        
        try:
            # Load alarms
            db_alarms = self.local_db.get_all_alarms()
            if db_alarms:
                # get_all_alarms() już zwraca obiekty Alarm, nie dicts
                self.alarms = db_alarms
                logger.info(f"Loaded {len(self.alarms)} alarms from LocalDatabase")
            
            # Load timers
            db_timers = self.local_db.get_all_timers()
            if db_timers:
                # get_all_timers() już zwraca obiekty Timer, nie dicts
                self.timers = db_timers
                
                logger.info(f"Loaded {len(self.timers)} timers from LocalDatabase")
        
        except Exception as e:
            logger.error(f"Failed to load from LocalDatabase: {e}")
    
    def refresh_from_server(self) -> bool:
        """
        Odśwież dane z serwera (wywołaj przy wejściu w widok alarmów).
        Serwer jest źródłem prawdy - pobierz latest i merge przez updated_at.
        
        Returns:
            True jeśli sukces, False jeśli błąd
        """
        if not self.sync_manager:
            logger.warning("Sync not enabled - cannot refresh from server")
            return False
        
        logger.info("Refreshing data from server...")
        
        # Wykonaj initial sync (pobierze najnowsze dane z serwera)
        if self.sync_manager.initial_sync():
            # Przeładuj z LocalDatabase (zawiera teraz merged data)
            self._load_from_local_db()
            logger.success("Data refreshed from server")
            return True
        else:
            logger.error("Failed to refresh from server")
            return False
    
    def _handle_alarm_ws_update(self, alarm_data: dict):
        """
        Obsłuż WebSocket update dla alarmu.
        
        Args:
            alarm_data: Dane alarmu z WebSocket
        """
        logger.info(f"WebSocket alarm event: {alarm_data.get('id')}")
        
        try:
            alarm_id = alarm_data.get('id')
            if not alarm_id:
                logger.warning("WebSocket alarm event without id, ignoring")
                return
            
            # Check if this is a delete event (only has id and deleted_at)
            if 'deleted_at' in alarm_data and 'alarm_time' not in alarm_data:
                # Handle delete: remove from memory
                self.alarms = [a for a in self.alarms if a.id != alarm_id]
                
                # Callback do UI
                if self.on_alarm_deleted:
                    self.on_alarm_deleted(alarm_id)
                
                logger.success(f"Alarm deleted from WebSocket: {alarm_id}")
                return
            
            # Regular create/update event
            # Konwertuj na Alarm object
            alarm = Alarm(
                id=alarm_id,
                time=datetime.strptime(alarm_data['alarm_time'], '%H:%M').time(),
                label=alarm_data['label'],
                enabled=alarm_data['enabled'],
                recurrence=AlarmRecurrence(alarm_data.get('recurrence', 'once')),
                days=alarm_data.get('days', []),
                play_sound=alarm_data.get('play_sound', True),
                show_popup=alarm_data.get('show_popup', True),
                custom_sound=alarm_data.get('custom_sound')
            )
            
            # Update w pamięci
            found = False
            for i, a in enumerate(self.alarms):
                if a.id == alarm.id:
                    self.alarms[i] = alarm
                    found = True
                    break
            
            if not found:
                self.alarms.append(alarm)
            
            # Callback do UI
            if self.on_alarm_changed:
                self.on_alarm_changed(alarm)
            
            logger.success(f"Alarm updated from WebSocket: {alarm.label}")
        
        except Exception as e:
            logger.error(f"Failed to handle alarm WS update: {e}")
    
    def _handle_timer_ws_update(self, timer_data: dict):
        """Obsłuż WebSocket update dla timera (create/update/delete)"""
        logger.info(f"WebSocket timer event: {timer_data.get('id')}")
        
        try:
            timer_id = timer_data.get('id')
            if not timer_id:
                logger.warning("WebSocket timer event without id, ignoring")
                return
            
            # Check if this is a delete event (only has id and deleted_at)
            if 'deleted_at' in timer_data and 'duration' not in timer_data:
                # Handle delete: remove from memory
                self.timers = [t for t in self.timers if t.id != timer_id]
                
                # Callback do UI
                if self.on_timer_deleted:
                    self.on_timer_deleted(timer_id)
                
                logger.success(f"Timer deleted from WebSocket: {timer_id}")
                return
            
            # Regular create/update event
            timer = Timer(
                id=timer_id,
                duration=timer_data['duration'],
                label=timer_data['label'],
                enabled=timer_data['enabled'],
                remaining=timer_data.get('remaining'),
                play_sound=timer_data.get('play_sound', True),
                show_popup=timer_data.get('show_popup', True),
                repeat=timer_data.get('repeat', False),
                custom_sound=timer_data.get('custom_sound')
            )
            
            # Update w pamięci
            found = False
            for i, t in enumerate(self.timers):
                if t.id == timer.id:
                    self.timers[i] = timer
                    found = True
                    break
            
            if not found:
                self.timers.append(timer)
            
            # Callback do UI
            if self.on_timer_changed:
                self.on_timer_changed(timer)
            
            logger.success(f"Timer updated from WebSocket: {timer.label}")
        
        except Exception as e:
            logger.error(f"Failed to handle timer WS update: {e}")
    
    def _handle_sync_required(self, reason: str):
        """Obsłuż WebSocket sync_required event"""
        logger.warning(f"Sync required: {reason}")
        
        if self.sync_manager:
            self.sync_manager.sync_now()
            logger.info("Manual sync triggered by WebSocket")
    
    def set_ui_callbacks(
        self,
        on_alarm_changed: Optional[Callable[[Alarm], None]] = None,
        on_timer_changed: Optional[Callable[[Timer], None]] = None
    ):
        """
        Ustaw callbacki dla UI updates.
        
        Args:
            on_alarm_changed: Callback wywoływany gdy alarm się zmieni (create/update/delete)
            on_timer_changed: Callback wywoływany gdy timer się zmieni
        
        Example:
            def refresh_alarm_list(alarm: Alarm):
                # Odśwież widok alarmów w UI
                self.alarm_view.refresh()
            
            alarm_manager.set_ui_callbacks(
                on_alarm_changed=refresh_alarm_list
            )
        """
        self.on_alarm_changed = on_alarm_changed
        self.on_timer_changed = on_timer_changed
        logger.info("UI callbacks registered")
    
    def save_alarms(self):
        """Zapisz alarmy do pliku JSON (fallback gdy sync wyłączony)"""
        if self.enable_sync:
            # Gdy sync włączony, dane są w LocalDatabase
            logger.debug("Skipping JSON save - using LocalDatabase")
            return True
        
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.alarms_file, 'w', encoding='utf-8') as f:
                data = [alarm.to_dict() for alarm in self.alarms]
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.alarms)} alarms to JSON")
            return True
        except Exception as e:
            logger.error(f"Failed to save alarms: {e}")
            return False
    
    def save_timers(self):
        """Zapisz timery do pliku JSON (fallback gdy sync wyłączony)"""
        if self.enable_sync:
            # Gdy sync włączony, dane są w LocalDatabase
            logger.debug("Skipping JSON save - using LocalDatabase")
            return True
        
        try:
            self.data_dir.mkdir(parents=True, exist_ok=True)
            with open(self.timers_file, 'w', encoding='utf-8') as f:
                data = [timer.to_dict() for timer in self.timers]
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.info(f"Saved {len(self.timers)} timers to JSON")
            return True
        except Exception as e:
            logger.error(f"Failed to save timers: {e}")
            return False
    
    # === ALARMY ===
    
    def add_alarm(self, alarm: Alarm) -> bool:
        """
        Dodaj nowy alarm.
        
        - Gdy sync włączony: zapisz do LocalDatabase (auto-queue dla sync)
        - Gdy sync wyłączony: zapisz do JSON
        """
        self.alarms.append(alarm)
        
        if self.enable_sync and self.local_db:
            try:
                self.local_db.save_alarm(alarm, user_id=self.user_id)
                logger.info(f"Alarm saved to LocalDatabase (will sync): {alarm.label}")
                return True
            except Exception as e:
                logger.error(f"Failed to save alarm to LocalDatabase: {e}")
                return False
        else:
            return self.save_alarms()
    
    def update_alarm(self, alarm: Alarm) -> bool:
        """Zaktualizuj istniejący alarm"""
        for i, a in enumerate(self.alarms):
            if a.id == alarm.id:
                self.alarms[i] = alarm
                
                if self.enable_sync and self.local_db:
                    try:
                        self.local_db.save_alarm(alarm, user_id=self.user_id)
                        logger.info(f"Alarm updated in LocalDatabase: {alarm.label}")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to update alarm: {e}")
                        return False
                else:
                    return self.save_alarms()
        return False
    
    def delete_alarm(self, alarm_id: str) -> bool:
        """Usuń alarm"""
        self.alarms = [a for a in self.alarms if a.id != alarm_id]
        
        if self.enable_sync and self.local_db:
            try:
                self.local_db.delete_alarm(alarm_id, soft=True)  # Soft delete dla sync
                logger.info(f"Alarm soft deleted from LocalDatabase: {alarm_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete alarm: {e}")
                return False
        else:
            return self.save_alarms()
    
    def toggle_alarm(self, alarm_id: str) -> bool:
        """Przełącz stan alarmu (włącz/wyłącz)"""
        for alarm in self.alarms:
            if alarm.id == alarm_id:
                alarm.enabled = not alarm.enabled
                
                if self.enable_sync and self.local_db:
                    try:
                        self.local_db.save_alarm(alarm, user_id=self.user_id)
                        return True
                    except Exception as e:
                        logger.error(f"Failed to toggle alarm: {e}")
                        return False
                else:
                    return self.save_alarms()
        return False
    
    def get_active_alarms(self) -> List[Alarm]:
        """Pobierz aktywne alarmy"""
        return [a for a in self.alarms if a.enabled]
    
    # === TIMERY ===
    
    def add_timer(self, timer: Timer) -> bool:
        """
        Dodaj nowy timer.
        
        - Gdy sync włączony: zapisz do LocalDatabase (auto-queue dla sync)
        - Gdy sync wyłączony: zapisz do JSON
        """
        self.timers.append(timer)
        
        if self.enable_sync and self.local_db:
            try:
                self.local_db.save_timer(timer, user_id=self.user_id)
                logger.info(f"Timer saved to LocalDatabase (will sync): {timer.label}")
                return True
            except Exception as e:
                logger.error(f"Failed to save timer to LocalDatabase: {e}")
                return False
        else:
            return self.save_timers()
    
    def update_timer(self, timer: Timer) -> bool:
        """Zaktualizuj istniejący timer"""
        for i, t in enumerate(self.timers):
            if t.id == timer.id:
                self.timers[i] = timer
                
                if self.enable_sync and self.local_db:
                    try:
                        self.local_db.save_timer(timer, user_id=self.user_id)
                        logger.info(f"Timer updated in LocalDatabase: {timer.label}")
                        return True
                    except Exception as e:
                        logger.error(f"Failed to update timer: {e}")
                        return False
                else:
                    return self.save_timers()
        return False
    
    def delete_timer(self, timer_id: str) -> bool:
        """Usuń timer"""
        self.timers = [t for t in self.timers if t.id != timer_id]
        
        if self.enable_sync and self.local_db:
            try:
                self.local_db.delete_timer(timer_id, soft=True)
                logger.info(f"Timer soft deleted from LocalDatabase: {timer_id}")
                return True
            except Exception as e:
                logger.error(f"Failed to delete timer: {e}")
                return False
        else:
            return self.save_timers()
    
    def start_timer(self, timer_id: str) -> bool:
        """Uruchom timer"""
        for timer in self.timers:
            if timer.id == timer_id:
                timer.enabled = True
                timer.started_at = datetime.now()
                timer.remaining = timer.duration
                
                if self.enable_sync and self.local_db:
                    try:
                        self.local_db.save_timer(timer, user_id=self.user_id)
                        return True
                    except Exception as e:
                        logger.error(f"Failed to start timer: {e}")
                        return False
                else:
                    return self.save_timers()
        return False
    
    def stop_timer(self, timer_id: str) -> bool:
        """Zatrzymaj timer"""
        for timer in self.timers:
            if timer.id == timer_id:
                timer.enabled = False
                timer.started_at = None
                timer.remaining = None
                
                if self.enable_sync and self.local_db:
                    try:
                        self.local_db.save_timer(timer, user_id=self.user_id)
                        return True
                    except Exception as e:
                        logger.error(f"Failed to stop timer: {e}")
                        return False
                else:
                    return self.save_timers()
        return False
    
    def update_timer_remaining(self, timer_id: str, remaining: int) -> bool:
        """Zaktualizuj pozostały czas timera"""
        for timer in self.timers:
            if timer.id == timer_id:
                timer.remaining = remaining
                if remaining <= 0:
                    if timer.repeat:
                        # Restart timera
                        timer.started_at = datetime.now()
                        timer.remaining = timer.duration
                    else:
                        timer.enabled = False
                        timer.started_at = None
                        timer.remaining = None
                
                if self.enable_sync and self.local_db:
                    try:
                        self.local_db.save_timer(timer, user_id=self.user_id)
                        return True
                    except Exception as e:
                        logger.error(f"Failed to update timer remaining: {e}")
                        return False
                else:
                    return self.save_timers()
        return False
    
    def get_active_timers(self) -> List[Timer]:
        """Pobierz aktywne timery"""
        return [t for t in self.timers if t.enabled]
    
    # === SYNC MANAGEMENT ===
    
    def sync_now(self) -> bool:
        """
        Wymusz natychmiastową synchronizację.
        
        Returns:
            True jeśli sync się udał, False otherwise
        """
        if not self.enable_sync or not self.sync_manager:
            logger.warning("Sync not enabled")
            return False
        
        try:
            self.sync_manager.sync_now()
            logger.info("Manual sync triggered")
            return True
        except Exception as e:
            logger.error(f"Failed to trigger sync: {e}")
            return False
    
    def get_sync_stats(self) -> Optional[dict]:
        """
        Pobierz statystyki synchronizacji.
        
        Returns:
            Dict ze statystykami lub None jeśli sync wyłączony
        """
        if not self.enable_sync or not self.sync_manager:
            return None
        
        return self.sync_manager.get_stats()
    
    def is_websocket_connected(self) -> bool:
        """Sprawdź czy WebSocket jest połączony"""
        if not self.enable_sync or not self.ws_client:
            return False
        
        return self.ws_client.is_connected()
    
    def cleanup(self):
        """
        Zatrzymaj wszystkie komponenty synchronizacji.
        
        Wywołaj przy zamykaniu aplikacji.
        """
        logger.info("Cleaning up AlarmManager...")
        
        if self.ws_client:
            try:
                self.ws_client.stop()
                logger.info("WebSocket client stopped")
            except Exception as e:
                logger.error(f"Error stopping WebSocket: {e}")
        
        if self.sync_manager:
            try:
                self.sync_manager.stop()
                logger.info("SyncManager stopped")
            except Exception as e:
                logger.error(f"Error stopping SyncManager: {e}")
        
        logger.success("AlarmManager cleanup complete")
