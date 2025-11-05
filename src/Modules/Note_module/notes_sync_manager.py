"""
Notes Sync Manager - Zarządzanie synchronizacją notatek z serwerem
Background worker (QThread) dla automatycznej synchronizacji
"""
import logging
from typing import Optional, Dict, Any, List, Callable, Callable
from datetime import datetime
from PyQt6.QtCore import QThread, pyqtSignal, QTimer, QObject

from .note_module_logic import NoteDatabase
from .notes_api_client import NotesAPIClient
from .note_websocket_client import NoteWebSocketClient

logger = logging.getLogger(__name__)


class SyncStatus:
    """Statusy synchronizacji"""
    SYNCED = "synced"           # 🟢 Wszystko zsynchronizowane
    PENDING = "pending"         # 🟡 Oczekujące operacje w kolejce
    SYNCING = "syncing"         # 🔵 Trwa synchronizacja
    ERROR = "error"             # 🔴 Błąd synchronizacji
    OFFLINE = "offline"         # ⚫ Brak połączenia z serwerem


class NotesSyncManager(QObject):
    """
    Manager synchronizacji notatek
    Koordynuje API Client, WebSocket Client i lokalną bazę danych
    """
    
    # Sygnały statusu synchronizacji
    sync_status_changed = pyqtSignal(str)           # SyncStatus enum
    sync_progress = pyqtSignal(int, int)            # (current, total)
    sync_completed = pyqtSignal(int, int)           # (success_count, error_count)
    sync_error = pyqtSignal(str)                    # error_message
    
    # Sygnały dla UI updates (od WebSocket)
    note_created_remotely = pyqtSignal(dict)
    note_updated_remotely = pyqtSignal(dict)
    note_deleted_remotely = pyqtSignal(str)
    
    def __init__(self, user_id: str, auth_token: str, db: NoteDatabase, 
                 refresh_token: Optional[str] = None,
                 on_token_refreshed: Optional[Callable[[str, str], None]] = None):
        """
        Inicjalizacja Sync Manager
        
        Args:
            user_id: UUID użytkownika
            auth_token: JWT token autoryzacyjny
            db: Instancja NoteDatabase
            refresh_token: Refresh token do odświeżania access tokena
            on_token_refreshed: Callback wywoływany po odświeżeniu tokena (access, refresh)
        """
        super().__init__()
        
        self.user_id = user_id
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.on_token_refreshed = on_token_refreshed
        self.db = db
        
        # Status synchronizacji
        self.current_status = SyncStatus.OFFLINE
        self.is_syncing = False
        
        # API Client
        self.api_client: Optional[NotesAPIClient] = None
        
        # WebSocket Client
        self.ws_client: Optional[NoteWebSocketClient] = None
        
        # Sync worker thread
        self.sync_worker: Optional[SyncWorker] = None
        
        # Auto-sync timer
        self.auto_sync_timer = QTimer()
        self.auto_sync_timer.timeout.connect(self.sync_all)
        self.auto_sync_interval = 30000  # 30 sekund
        
        logger.info(f"NotesSyncManager initialized for user {user_id}")
    
    def start(self):
        """Uruchamia sync manager (API client, WebSocket, auto-sync)"""
        logger.info("Starting NotesSyncManager...")
        
        # Inicjalizuj API Client
        self._init_api_client()
        
        # Inicjalizuj WebSocket Client (teraz z mechanizmem odświeżania tokena)
        self._init_websocket_client()
        
        # Uruchom auto-sync timer
        self.auto_sync_timer.start(self.auto_sync_interval)
        
        # Wykonaj pierwszą synchronizację
        self.sync_all()
        
        logger.info("✅ NotesSyncManager started")
    
    def stop(self):
        """Zatrzymuje sync manager"""
        logger.info("Stopping NotesSyncManager...")
        
        # Zatrzymaj auto-sync
        self.auto_sync_timer.stop()
        
        # Zatrzymaj sync worker
        if self.sync_worker and self.sync_worker.isRunning():
            self.sync_worker.stop()
            self.sync_worker.wait(3000)
        
        # Zamknij WebSocket
        if self.ws_client:
            self.ws_client.cleanup()
        
        # Zamknij API Client
        if self.api_client:
            self.api_client.close()
        
        self._update_status(SyncStatus.OFFLINE)
        logger.info("✅ NotesSyncManager stopped")
    
    def sync_all(self):
        """Uruchamia pełną synchronizację (upload pending → download remote)"""
        if self.is_syncing:
            logger.warning("Sync already in progress, skipping...")
            return
        
        if not self.api_client:
            logger.warning("API Client not initialized, cannot sync")
            self._update_status(SyncStatus.OFFLINE)
            return
        
        # Sprawdź połączenie z API
        if not self.api_client.test_connection():
            logger.warning("Cannot connect to API server")
            self._update_status(SyncStatus.OFFLINE)
            return
        
        logger.info("🔄 Starting sync cycle...")
        self.is_syncing = True
        self._update_status(SyncStatus.SYNCING)
        
        # Uruchom sync worker w tle
        self.sync_worker = SyncWorker(
            db=self.db,
            api_client=self.api_client,
            user_id=self.user_id
        )
        
        # Podłącz sygnały
        self.sync_worker.progress.connect(self._on_sync_progress)
        self.sync_worker.completed.connect(self._on_sync_completed)
        self.sync_worker.error.connect(self._on_sync_error)
        
        # Uruchom worker
        self.sync_worker.start()
    
    def sync_note(self, note_id: str):
        """
        Synchronizuje pojedynczą notatkę
        
        Args:
            note_id: UUID notatki do synchronizacji
        """
        if not self.api_client:
            logger.warning("API Client not initialized")
            return
        
        logger.info(f"Syncing single note: {note_id}")
        
        try:
            # Pobierz notatkę z lokalnej bazy
            note = self.db.get_note(note_id)
            if not note:
                logger.error(f"Note {note_id} not found in local DB")
                return
            
            # Przygotuj dane do synchronizacji
            note_data = {
                "local_id": note['id'],
                "user_id": note['user_id'],
                "parent_id": note['parent_id'],
                "title": note['title'],
                "content": note['content'],
                "color": note['color'],
                "version": note.get('version', 1),
                "synced_at": note.get('synced_at')
            }
            
            # Wyślij do serwera
            result = self.api_client.sync_note(note_data)
            
            # Oznacz jako zsynchronizowane
            self.db.mark_note_synced(
                local_id=note['id'],
                server_id=result['id'],
                version=result['version']
            )
            
            logger.info(f"✅ Note {note_id} synced successfully")
            
        except Exception as e:
            logger.error(f"Failed to sync note {note_id}: {e}")
            self.sync_error.emit(str(e))
    
    def set_auto_sync_interval(self, seconds: int):
        """
        Ustawia interwał auto-sync
        
        Args:
            seconds: Liczba sekund między synchronizacjami
        """
        self.auto_sync_interval = seconds * 1000
        if self.auto_sync_timer.isActive():
            self.auto_sync_timer.setInterval(self.auto_sync_interval)
        logger.info(f"Auto-sync interval set to {seconds}s")
    
    # =============================================================================
    # PRIVATE METHODS
    # =============================================================================
    
    def _init_api_client(self):
        """Inicjalizuje API Client z callback do odświeżania tokena"""
        from .notes_api_client import create_api_client
        
        # Wrapper callback - aktualizuje WebSocket token gdy API token jest odświeżany
        def on_token_refreshed_wrapper(new_access_token: str, new_refresh_token: str):
            """Aktualizuje token w WebSocket i przekazuje dalej do głównego callbacka"""
            self.auth_token = new_access_token
            
            # Zaktualizuj token w WebSocket (jeśli istnieje)
            if self.ws_client:
                self.ws_client.update_token(new_access_token)
                logger.info("✓ WebSocket token updated after refresh")
            
            # Przekaż dalej do głównego callbacka (który zaktualizuje UI/main_window)
            if self.on_token_refreshed:
                self.on_token_refreshed(new_access_token, new_refresh_token)
        
        self.api_client = create_api_client(
            user_id=self.user_id,
            auth_token=self.auth_token,
            refresh_token=self.refresh_token,
            on_token_refreshed=on_token_refreshed_wrapper
        )
        logger.info("API Client initialized with token refresh callback")
    
    def _init_websocket_client(self):
        """Inicjalizuje WebSocket Client i podłącza sygnały"""
        from .note_websocket_client import create_websocket_client
        
        self.ws_client = create_websocket_client(
            user_id=self.user_id,
            auth_token=self.auth_token
        )
        
        # Podłącz sygnały WebSocket do lokalnych handlerów
        self.ws_client.note_created.connect(self._on_remote_note_created)
        self.ws_client.note_updated.connect(self._on_remote_note_updated)
        self.ws_client.note_deleted.connect(self._on_remote_note_deleted)
        self.ws_client.link_created.connect(self._on_remote_link_created)
        
        self.ws_client.connected.connect(self._on_websocket_connected)
        self.ws_client.disconnected.connect(self._on_websocket_disconnected)
        self.ws_client.connection_error.connect(self._on_websocket_error)
        
        # Połącz z serwerem
        self.ws_client.connect_to_server()
        
        logger.info("WebSocket Client initialized")
    
    def _update_status(self, status: str):
        """Aktualizuje i emituje status synchronizacji"""
        if self.current_status != status:
            self.current_status = status
            self.sync_status_changed.emit(status)
            logger.debug(f"Sync status changed: {status}")
    
    def _on_sync_progress(self, current: int, total: int):
        """Handler progress synchronizacji"""
        self.sync_progress.emit(current, total)
    
    def _on_sync_completed(self, success_count: int, error_count: int):
        """Handler zakończenia synchronizacji"""
        self.is_syncing = False
        
        if error_count == 0:
            self._update_status(SyncStatus.SYNCED)
            logger.info(f"✅ Sync completed: {success_count} items synced")
        else:
            self._update_status(SyncStatus.ERROR)
            logger.warning(f"⚠️ Sync completed with errors: {success_count} success, {error_count} errors")
        
        self.sync_completed.emit(success_count, error_count)
        
        # Wyczyść stare zakończone operacje
        self.db.clear_completed_sync_operations(older_than_days=7)
    
    def _on_sync_error(self, error_message: str):
        """Handler błędu synchronizacji"""
        self.is_syncing = False
        self._update_status(SyncStatus.ERROR)
        self.sync_error.emit(error_message)
        logger.error(f"Sync error: {error_message}")
    
    # =============================================================================
    # WEBSOCKET EVENT HANDLERS
    # =============================================================================
    
    def _on_websocket_connected(self):
        """WebSocket połączony"""
        logger.info("WebSocket connected")
        if not self.is_syncing:
            self._update_status(SyncStatus.SYNCED)
    
    def _on_websocket_disconnected(self):
        """WebSocket rozłączony"""
        logger.warning("WebSocket disconnected")
        if not self.is_syncing:
            self._update_status(SyncStatus.OFFLINE)
    
    def _on_websocket_error(self, error: str):
        """Błąd WebSocket"""
        logger.error(f"WebSocket error: {error}")
    
    def _on_remote_note_created(self, note_data: Dict[str, Any]):
        """Notatka utworzona na innym urządzeniu"""
        logger.info(f"Remote note created: {note_data.get('id')}")
        
        # Sprawdź czy notatka już istnieje lokalnie
        local_note = self.db.get_note(note_data.get('id', ''))
        
        if not local_note:
            # Utwórz lokalnie
            try:
                note_id = self.db.create_note(
                    title=note_data.get('title', ''),
                    content=note_data.get('content', ''),
                    parent_id=note_data.get('parent_id'),
                    color=note_data.get('color', '#e3f2fd')
                )
                
                # Oznacz jako zsynchronizowane
                self.db.mark_note_synced(
                    local_id=note_id,
                    server_id=note_data.get('id'),
                    version=note_data.get('version', 1)
                )
                
                # Emituj sygnał do UI
                self.note_created_remotely.emit(note_data)
                
            except Exception as e:
                logger.error(f"Failed to create remote note locally: {e}")
    
    def _on_remote_note_updated(self, note_data: Dict[str, Any]):
        """Notatka zaktualizowana na innym urządzeniu"""
        logger.info(f"Remote note updated: {note_data.get('id')}")
        
        # Conflict resolution: last-write-wins
        server_version = note_data.get('version', 1)
        server_id = note_data.get('id')
        
        # Znajdź lokalną notatkę po server_id
        all_notes = self.db.get_all_notes()
        local_note = next(
            (n for n in all_notes if n.get('server_id') == server_id),
            None
        )
        
        if local_note:
            local_version = local_note.get('version', 1)
            
            # Jeśli wersja z serwera jest nowsza, zaktualizuj lokalnie
            if server_version >= local_version:
                try:
                    self.db.update_note(
                        note_id=local_note['id'],
                        title=note_data.get('title'),
                        content=note_data.get('content'),
                        color=note_data.get('color'),
                        parent_id=note_data.get('parent_id')
                    )
                    
                    # Zaktualizuj wersję i sync timestamp
                    self.db.mark_note_synced(
                        local_id=local_note['id'],
                        server_id=server_id,
                        version=server_version
                    )
                    
                    # Emituj sygnał do UI
                    self.note_updated_remotely.emit(note_data)
                    
                except Exception as e:
                    logger.error(f"Failed to update remote note locally: {e}")
            else:
                logger.info(f"Local version ({local_version}) newer than server ({server_version}), skipping update")
    
    def _on_remote_note_deleted(self, note_id: str):
        """Notatka usunięta na innym urządzeniu"""
        logger.info(f"Remote note deleted: {note_id}")
        
        # Znajdź lokalną notatkę po server_id
        all_notes = self.db.get_all_notes()
        local_note = next(
            (n for n in all_notes if n.get('server_id') == note_id),
            None
        )
        
        if local_note:
            try:
                self.db.delete_note(local_note['id'], soft=True)
                self.note_deleted_remotely.emit(note_id)
            except Exception as e:
                logger.error(f"Failed to delete remote note locally: {e}")
    
    def _on_remote_link_created(self, link_data: Dict[str, Any]):
        """Link utworzony na innym urządzeniu"""
        logger.info(f"Remote link created: {link_data.get('id')}")
        
        # TODO: Implementacja synchronizacji linków
        # Podobnie jak dla notatek, ale dla tabeli note_links


class SyncWorker(QThread):
    """Worker thread dla synchronizacji w tle"""
    
    progress = pyqtSignal(int, int)             # (current, total)
    completed = pyqtSignal(int, int)            # (success_count, error_count)
    error = pyqtSignal(str)                     # error_message
    
    def __init__(self, db: NoteDatabase, api_client: NotesAPIClient, user_id: str):
        super().__init__()
        self.db = db
        self.api_client = api_client
        self.user_id = user_id
        self.should_stop = False
    
    def run(self):
        """Główna logika synchronizacji"""
        success_count = 0
        error_count = 0
        
        try:
            # KROK 1: Synchronizuj oczekujące operacje z sync_queue
            pending_operations = self.db.get_pending_sync_operations(limit=100)
            total_operations = len(pending_operations)
            
            logger.info(f"Processing {total_operations} pending operations...")
            
            for idx, operation in enumerate(pending_operations):
                if self.should_stop:
                    break
                
                self.progress.emit(idx + 1, total_operations)
                
                try:
                    self._process_sync_operation(operation)
                    self.db.mark_sync_operation_completed(operation['id'])
                    success_count += 1
                    
                except Exception as e:
                    logger.error(f"Failed to process operation {operation['id']}: {e}")
                    self.db.mark_sync_operation_failed(operation['id'], str(e))
                    error_count += 1
            
            # KROK 2: Synchronizuj notatki które zostały zmodyfikowane lokalnie
            unsynced_notes = self.db.get_unsynced_notes()
            
            # Sortuj notatki: najpierw rodzice (parent_id = NULL), potem dzieci
            # To zapobiega błędom "Parent note does not exist"
            unsynced_notes_sorted = sorted(
                unsynced_notes,
                key=lambda n: (n.get('parent_id') is not None, n.get('created_at', ''))
            )
            
            logger.info(f"Syncing {len(unsynced_notes_sorted)} unsynced notes...")
            
            for note in unsynced_notes_sorted:
                if self.should_stop:
                    break
                
                try:
                    self._sync_note(note)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to sync note {note['id']}: {e}")
                    error_count += 1
            
            # KROK 3: Synchronizuj linki
            unsynced_links = self.db.get_unsynced_links()
            
            logger.info(f"Syncing {len(unsynced_links)} unsynced links...")
            
            for link in unsynced_links:
                if self.should_stop:
                    break
                
                try:
                    self._sync_link(link)
                    success_count += 1
                except Exception as e:
                    logger.error(f"Failed to sync link {link['id']}: {e}")
                    error_count += 1
            
            # Emituj sygnał zakończenia
            self.completed.emit(success_count, error_count)
            
        except Exception as e:
            logger.error(f"Sync worker error: {e}")
            self.error.emit(str(e))
    
    def stop(self):
        """Zatrzymuje worker"""
        self.should_stop = True
    
    def _process_sync_operation(self, operation: Dict[str, Any]):
        """Przetwarza pojedynczą operację z sync_queue"""
        operation_type = operation['operation_type']
        entity_type = operation['entity_type']
        entity_id = operation['entity_id']
        
        if entity_type == 'note':
            note = self.db.get_note(entity_id)
            if not note:
                logger.warning(f"Note {entity_id} not found, skipping")
                return
            
            if operation_type in ['create', 'update']:
                self._sync_note(note)
            elif operation_type == 'delete':
                # Usuń na serwerze jeśli ma server_id
                if note.get('server_id'):
                    self.api_client.delete_note(note['server_id'])
        
        elif entity_type == 'link':
            links = self.db.get_links_for_note(entity_id)
            link = next((l for l in links if l['id'] == entity_id), None)
            
            if link and operation_type in ['create', 'update']:
                self._sync_link(link)
    
    def _sync_note(self, note: Dict[str, Any]):
        """Synchronizuje pojedynczą notatkę"""
        note_data = {
            "local_id": note['id'],
            "user_id": note['user_id'],
            "parent_id": note['parent_id'],
            "title": note['title'],
            "content": note['content'],
            "color": note['color'],
            "version": note.get('version', 1),
            "synced_at": note.get('synced_at')
        }
        
        result = self.api_client.sync_note(note_data)
        
        # Oznacz jako zsynchronizowane
        self.db.mark_note_synced(
            local_id=note['id'],
            server_id=result['id'],
            version=result['version']
        )
    
    def _sync_link(self, link: Dict[str, Any]):
        """Synchronizuje pojedynczy link"""
        link_data = {
            "local_id": link['id'],
            "source_note_id": link['source_note_id'],
            "target_note_id": link['target_note_id'],
            "link_text": link['link_text'],
            "start_position": link['start_position'],
            "end_position": link['end_position']
        }
        
        result = self.api_client.sync_note_link(link_data)
        
        # Oznacz jako zsynchronizowany
        self.db.mark_link_synced(
            local_id=link['id'],
            server_id=result['id']
        )
