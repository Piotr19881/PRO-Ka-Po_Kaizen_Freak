"""
Sync Manager - zarządzanie synchronizacją nagrań CallCryptor.
==============================================================

PRIVACY-FIRST: Synchronizuje TYLKO metadane, NIE pliki audio!

Ten moduł obsługuje:
- Opt-in synchronizację (wyłączona domyślnie)
- Manual sync trigger (przycisk 📨)
- Optional auto-sync (co 5 minut)
- Last-Write-Wins conflict resolution
- Bulk sync (max 100 nagrań)
- Background worker z retry logic
"""

import json
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, timedelta
from threading import Thread, Event, Lock
from loguru import logger
from pathlib import Path

from .recording_api_client import RecordingsAPIClient, APIResponse
from .callcryptor_database import CallCryptorDatabase


# Import Status LED (optional)
try:
    from ...ui.status_led import record_sync_success, record_sync_error
    STATUS_LED_AVAILABLE = True
except ImportError:
    STATUS_LED_AVAILABLE = False
    logger.debug("[CallCryptor Sync] Status LED module not available")


class RecordingsSyncManager:
    """
    Menedżer synchronizacji dla CallCryptor (local-first, opt-in).
    
    PRIVACY-FIRST:
    - Domyślnie wyłączona (opt-in)
    - Manual trigger via UI button
    - Optional auto-sync (checkbox)
    - Tylko metadane, NIE pliki audio
    
    Background worker (gdy auto-sync włączona):
    - Monitoruje zmiany lokalne
    - Synchronizuje co 5 minut
    - Retry z exponential backoff
    """
    
    def __init__(
        self,
        db_manager: CallCryptorDatabase,
        api_client: RecordingsAPIClient,
        user_id: str,
        config_path: Path,
        on_sync_complete: Optional[Callable[[bool, str], None]] = None
    ):
        """
        Inicjalizacja Sync Manager.
        
        Args:
            db_manager: CallCryptorDatabase instance
            api_client: RecordingsAPIClient instance
            user_id: ID użytkownika
            config_path: Ścieżka do user_settings.json
            on_sync_complete: Callback po synchronizacji: (success: bool, message: str) -> None
        """
        self.db_manager = db_manager
        self.api_client = api_client
        self.user_id = user_id
        self.config_path = config_path
        self.on_sync_complete = on_sync_complete
        
        # Sync settings (loaded from config)
        self.sync_enabled = False
        self.auto_sync_enabled = False
        self.sync_interval = 300  # 5 minut w sekundach
        self.last_sync_at: Optional[datetime] = None
        
        # Threading (tylko gdy auto-sync włączona)
        self._worker_thread: Optional[Thread] = None
        self._stop_event = Event()
        self._lock = Lock()
        self._is_running = False
        
        # Stats
        self.sync_count = 0
        self.error_count = 0
        self.conflicts_resolved = 0
        
        # Load settings
        self._load_settings()
        
        logger.info(f"[CallCryptor Sync] Manager initialized (sync={self.sync_enabled}, auto={self.auto_sync_enabled})")
    
    # =========================================================================
    # SETTINGS MANAGEMENT
    # =========================================================================
    
    def _load_settings(self):
        """Wczytaj ustawienia synchronizacji z user_settings.json"""
        try:
            if not self.config_path.exists():
                logger.debug("[CallCryptor Sync] Config file not found, using defaults")
                return
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            sync_config = config.get('callcryptor_sync', {})
            self.sync_enabled = sync_config.get('enabled', False)
            self.auto_sync_enabled = sync_config.get('auto_sync_enabled', False)
            self.sync_interval = sync_config.get('sync_interval_minutes', 5) * 60
            
            last_sync_str = sync_config.get('last_sync_at')
            if last_sync_str:
                self.last_sync_at = datetime.fromisoformat(last_sync_str)
            
            logger.info(f"[CallCryptor Sync] Settings loaded: enabled={self.sync_enabled}, auto={self.auto_sync_enabled}")
            
        except Exception as e:
            logger.error(f"[CallCryptor Sync] Error loading settings: {e}")
    
    def _save_settings(self):
        """Zapisz ustawienia synchronizacji do user_settings.json"""
        try:
            # Load existing config
            config = {}
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    config = json.load(f)
            
            # Update sync settings
            config['callcryptor_sync'] = {
                'enabled': self.sync_enabled,
                'auto_sync_enabled': self.auto_sync_enabled,
                'sync_interval_minutes': self.sync_interval // 60,
                'last_sync_at': self.last_sync_at.isoformat() if self.last_sync_at else None,
                'dont_show_warning': config.get('callcryptor_sync', {}).get('dont_show_warning', False),
                'exclude_tags': config.get('callcryptor_sync', {}).get('exclude_tags', [])
            }
            
            # Save
            with open(self.config_path, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            logger.debug("[CallCryptor Sync] Settings saved")
            
        except Exception as e:
            logger.error(f"[CallCryptor Sync] Error saving settings: {e}")
    
    def enable_sync(self, auto_sync: bool = False):
        """
        Włącz synchronizację.
        
        Args:
            auto_sync: Czy włączyć automatyczną synchronizację co 5 minut
        """
        self.sync_enabled = True
        self.auto_sync_enabled = auto_sync
        self._save_settings()
        
        if auto_sync and not self._is_running:
            self.start_auto_sync()
        
        logger.info(f"[CallCryptor Sync] Sync enabled (auto={auto_sync})")
    
    def disable_sync(self):
        """Wyłącz synchronizację"""
        self.sync_enabled = False
        self.auto_sync_enabled = False
        self._save_settings()
        
        if self._is_running:
            self.stop_auto_sync()
        
        logger.info("[CallCryptor Sync] Sync disabled")
    
    # =========================================================================
    # WORKER CONTROL (AUTO-SYNC)
    # =========================================================================
    
    def start_auto_sync(self):
        """Uruchom background worker dla auto-sync"""
        if self._is_running:
            logger.warning("[CallCryptor Sync] Auto-sync worker already running")
            return
        
        if not self.auto_sync_enabled:
            logger.warning("[CallCryptor Sync] Cannot start auto-sync: not enabled")
            return
        
        self._stop_event.clear()
        self._is_running = True
        self._worker_thread = Thread(target=self._worker_loop, daemon=True, name="CallCryptorSyncWorker")
        self._worker_thread.start()
        logger.info("[CallCryptor Sync] Auto-sync worker started")
    
    def stop_auto_sync(self, wait: bool = True, timeout: float = 5.0):
        """
        Zatrzymaj background worker.
        
        Args:
            wait: Czy czekać na zakończenie worker thread
            timeout: Timeout w sekundach
        """
        if not self._is_running:
            logger.warning("[CallCryptor Sync] Auto-sync worker not running")
            return
        
        logger.info("[CallCryptor Sync] Stopping auto-sync worker...")
        self._stop_event.set()
        self._is_running = False
        
        if wait and self._worker_thread:
            self._worker_thread.join(timeout=timeout)
            if self._worker_thread.is_alive():
                logger.warning("[CallCryptor Sync] Worker did not stop within timeout")
            else:
                logger.info("[CallCryptor Sync] Auto-sync worker stopped")
    
    def is_auto_sync_running(self) -> bool:
        """Sprawdź czy auto-sync działa"""
        return self._is_running
    
    def _worker_loop(self):
        """Background worker loop (auto-sync co 5 minut)"""
        logger.debug("[CallCryptor Sync] Worker loop started")
        
        while not self._stop_event.is_set():
            try:
                # Wykonaj synchronizację
                self.sync_now(background=True)
                
                # Czekaj 5 minut przed następnym cyklem
                self._stop_event.wait(timeout=self.sync_interval)
                
            except Exception as e:
                logger.error(f"[CallCryptor Sync] Error in worker loop: {e}")
                self.error_count += 1
                # Czekaj przed retry
                self._stop_event.wait(timeout=60)
        
        logger.debug("[CallCryptor Sync] Worker loop exited")
    
    # =========================================================================
    # MANUAL SYNC
    # =========================================================================
    
    def sync_now(self, background: bool = False) -> bool:
        """
        Wykonaj synchronizację teraz (manual trigger).
        
        Args:
            background: True jeśli wywołane z worker loop
            
        Returns:
            True jeśli sukces, False jeśli błąd
        """
        if not background:
            # Manual sync - nie wymaga enabled
            logger.info("[CallCryptor Sync] Manual sync triggered")
        else:
            # Auto-sync - sprawdź czy włączona
            if not self.sync_enabled or not self.auto_sync_enabled:
                logger.debug("[CallCryptor Sync] Auto-sync disabled, skipping")
                return False
        
        with self._lock:
            try:
                # 1. Gather local changes (recordings changed since last_sync_at)
                local_recordings = self._get_local_changes()
                
                if not local_recordings and self.last_sync_at:
                    logger.debug("[CallCryptor Sync] No local changes to sync")
                    # Pobierz zmiany z serwera anyway
                    return self._pull_from_server()
                
                # 2. Prepare related sources for this batch
                sources_payload = self._get_sources_payload(local_recordings)

                # 3. Bulk sync with server
                logger.info(
                    f"[CallCryptor Sync] Syncing {len(local_recordings)} recordings and "
                    f"{len(sources_payload)} sources..."
                )
                
                response = self.api_client.bulk_sync(
                    recordings=local_recordings,
                    sources=sources_payload,
                    tags=[],     # TODO: implement tags sync
                    last_sync_at=self.last_sync_at
                )
                
                if not response.success:
                    logger.error(f"[CallCryptor Sync] Bulk sync failed: {response.error}")
                    self.error_count += 1
                    
                    if self.on_sync_complete:
                        self.on_sync_complete(False, response.error or "Unknown error")
                    
                    if STATUS_LED_AVAILABLE:
                        record_sync_error("callcryptor")
                    
                    return False
                
                # 3. Process server response
                result = response.data
                
                recordings_created = result.get('recordings_created', 0)
                recordings_updated = result.get('recordings_updated', 0)
                recordings_deleted = result.get('recordings_deleted', 0)
                conflicts = result.get('conflicts_resolved', 0)
                
                logger.info(f"[CallCryptor Sync] Server response: created={recordings_created}, updated={recordings_updated}, deleted={recordings_deleted}, conflicts={conflicts}")
                
                # 4. Apply server changes to local DB
                server_recordings = result.get('server_recordings', [])
                self._apply_server_changes(server_recordings)
                
                # 5. Update stats
                self.last_sync_at = datetime.now()
                self.sync_count += 1
                self.conflicts_resolved += conflicts
                self._save_settings()
                
                if self.on_sync_complete:
                    message = f"Zsynchronizowano {len(local_recordings)} nagrań"
                    self.on_sync_complete(True, message)
                
                if STATUS_LED_AVAILABLE:
                    record_sync_success("callcryptor")
                
                logger.success(f"[CallCryptor Sync] Sync completed successfully")
                return True
                
            except Exception as e:
                logger.error(f"[CallCryptor Sync] Sync error: {e}")
                self.error_count += 1
                
                if self.on_sync_complete:
                    self.on_sync_complete(False, str(e))
                
                if STATUS_LED_AVAILABLE:
                    record_sync_error("callcryptor")
                
                return False
    
    def _get_local_changes(self) -> List[Dict[str, Any]]:
        """
        Pobierz lokalne zmiany (recordings changed since last_sync_at).
        
        Returns:
            Lista słowników z danymi nagrań
        """
        try:
            # Pobierz wszystkie nagrania użytkownika
            recordings = self.db_manager.get_all_recordings(self.user_id)
            
            # Filtruj tylko te zmienione od last_sync_at
            if self.last_sync_at:
                # TODO: Dodać kolumnę updated_at do recordings
                # Na razie zwracamy wszystkie
                pass
            
            # Konwertuj na format API (RecordingSyncItem)
            sync_items = []
            for rec in recordings:
                # Parse JSON fields (stored as strings in SQLite)
                tags = self._parse_json_field(rec.get('tags'), [])
                ai_summary_tasks = self._parse_json_field(rec.get('ai_summary_tasks'), None)
                ai_key_points = self._parse_json_field(rec.get('ai_key_points'), None)
                ai_action_items = self._parse_json_field(rec.get('ai_action_items'), None)
                
                # DEBUG: Log first item to verify parsing
                if len(sync_items) == 0:
                    logger.debug(f"[CallCryptor Sync] Sample parsing - ai_summary_tasks raw: {type(rec.get('ai_summary_tasks'))} = {rec.get('ai_summary_tasks')}")
                    logger.debug(f"[CallCryptor Sync] Sample parsing - ai_summary_tasks parsed: {type(ai_summary_tasks)} = {ai_summary_tasks}")
                
                # UWAGA: NIE dodawaj file_path - to lokalna ścieżka!
                sync_item = {
                    'id': rec['id'],
                    'source_id': rec['source_id'],
                    'file_name': rec['file_name'],
                    'file_hash': rec.get('file_hash'),
                    'file_size': self._safe_int(rec.get('file_size')),
                    'email_message_id': rec.get('email_message_id'),
                    'email_subject': rec.get('email_subject'),
                    'email_sender': rec.get('email_sender'),
                    'contact_name': rec.get('contact_name'),
                    'contact_phone': rec.get('contact_phone'),
                    'duration_seconds': self._safe_int(rec.get('duration')),
                    'recording_date': rec.get('recording_date'),
                    'tags': tags,
                    'notes': rec.get('notes'),
                    'transcription_status': rec.get('transcription_status', 'pending') or 'pending',
                    'transcription_text': rec.get('transcription_text'),
                    'transcription_language': rec.get('transcription_language'),
                    'transcription_confidence': self._safe_float(rec.get('transcription_confidence')),
                    'transcription_date': rec.get('transcription_date'),
                    'transcription_error': rec.get('transcription_error'),
                    'ai_summary': rec.get('ai_summary_text'),
                    'ai_summary_status': rec.get('ai_summary_status', 'pending') or 'pending',
                    'ai_summary_date': rec.get('ai_summary_date'),
                    'ai_summary_error': rec.get('ai_summary_error'),
                    'ai_summary_tasks': ai_summary_tasks,
                    'ai_key_points': ai_key_points,
                    'ai_action_items': ai_action_items,
                    'note_id': rec.get('note_id'),
                    'task_id': rec.get('task_id'),
                    'is_favorite': self._to_bool(rec.get('is_favorite'), False),
                    'favorited_at': rec.get('favorited_at'),
                    'is_archived': self._to_bool(rec.get('is_archived'), False),
                    'archived_at': rec.get('archived_at'),
                    'archive_reason': rec.get('archive_reason'),
                    'created_at': rec.get('created_at'),
                    'updated_at': rec.get('updated_at'),
                    'deleted_at': rec.get('deleted_at'),
                    'version': self._safe_int(rec.get('version'), 1)
                }
                sync_items.append(sync_item)
            
            logger.debug(f"[CallCryptor Sync] Found {len(sync_items)} local recordings")
            return sync_items[:100]  # Max 100 per sync
            
        except Exception as e:
            logger.error(f"[CallCryptor Sync] Error getting local changes: {e}")
            return []
    
    def _parse_json_field(self, value: Any, default: Any = None) -> Any:
        """
        Parse JSON field from SQLite (stored as TEXT).
        
        Args:
            value: Raw value from database (string or already parsed)
            default: Default value if parsing fails or value is None
            
        Returns:
            Parsed JSON value or default
        """
        if value is None:
            return default
        
        # Already parsed (list/dict)
        if isinstance(value, (list, dict)):
            return value
        
        # Parse JSON string
        if isinstance(value, str):
            try:
                parsed = json.loads(value)
                return parsed if parsed is not None else default
            except json.JSONDecodeError:
                logger.warning(f"[CallCryptor Sync] Failed to parse JSON: {value[:100]}")
                return default
        
        # Unknown type
        logger.warning(f"[CallCryptor Sync] Unexpected type for JSON field: {type(value)}")
        return default

    def _to_bool(self, value: Any, default: bool = False) -> bool:
        """Convert SQLite truthy values to bool."""
        if value is None:
            return default
        if isinstance(value, bool):
            return value
        if isinstance(value, (int, float)):
            return value != 0
        if isinstance(value, str):
            return value.strip().lower() in {'1', 'true', 'yes', 'y', 'on'}
        return default

    def _safe_int(self, value: Any, default: Optional[int] = None) -> Optional[int]:
        """Safely convert value to int."""
        if value is None or value == '':
            return default
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _safe_float(self, value: Any, default: Optional[float] = None) -> Optional[float]:
        """Safely convert value to float."""
        if value is None or value == '':
            return default
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _prepare_source_payload(self, source: Dict[str, Any]) -> Dict[str, Any]:
        """Map local SQLite source row to API payload structure."""
        file_extensions = source.get('file_extensions')
        if isinstance(file_extensions, str):
            try:
                file_extensions = json.loads(file_extensions)
            except json.JSONDecodeError:
                file_extensions = [ext.strip() for ext in file_extensions.split(',') if ext.strip()]
        if not isinstance(file_extensions, list):
            file_extensions = []

        payload = {
            'id': source.get('id'),
            'user_id': source.get('user_id'),
            'source_name': source.get('source_name'),
            'source_type': source.get('source_type'),
            'folder_path': source.get('folder_path'),
            'file_extensions': file_extensions,
            'scan_depth': self._safe_int(source.get('scan_depth'), 1),
            'email_account_id': source.get('email_account_id'),
            'search_phrase': source.get('search_phrase'),
            'search_type': source.get('search_type') or 'SUBJECT',
            'search_all_folders': self._to_bool(source.get('search_all_folders'), False),
            'target_folder': source.get('target_folder') or 'INBOX',
            'attachment_pattern': source.get('attachment_pattern'),
            'contact_ignore_words': source.get('contact_ignore_words'),
            'is_active': self._to_bool(source.get('is_active'), True),
            'last_scan_at': source.get('last_scan_at'),
            'recordings_count': self._safe_int(source.get('recordings_count'), 0),
            'created_at': source.get('created_at'),
            'updated_at': source.get('updated_at'),
            'deleted_at': source.get('deleted_at'),
            'version': self._safe_int(source.get('version'), 1)
        }

        return payload

    def _get_sources_payload(self, recordings: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Collect source payloads required for current sync batch."""
        try:
            if not recordings:
                return []

            source_ids = {
                rec.get('source_id')
                for rec in recordings
                if rec.get('source_id')
            }

            include_all = self.last_sync_at is None

            all_sources = self.db_manager.get_all_sources(self.user_id)
            payload = []

            for source in all_sources:
                source_id = source.get('id')
                if include_all or source_id in source_ids or not self._to_bool(source.get('is_synced'), False):
                    payload.append(self._prepare_source_payload(source))

            logger.debug(f"[CallCryptor Sync] Prepared {len(payload)} sources for sync")
            return payload
        except Exception as e:
            logger.error(f"[CallCryptor Sync] Error preparing sources payload: {e}")
            return []
    
    def _pull_from_server(self) -> bool:
        """Pobierz tylko zmiany z serwera (bez wysyłania)"""
        try:
            # TODO: Implement pull-only sync
            # Może być przydatne gdy mamy tylko remote changes
            return True
        except Exception as e:
            logger.error(f"[CallCryptor Sync] Error pulling from server: {e}")
            return False
    
    def _apply_server_changes(self, server_recordings: List[Dict[str, Any]]):
        """
        Zastosuj zmiany z serwera do lokalnej bazy.
        
        Last-Write-Wins: Porównaj updated_at i zastosuj nowsze.
        
        Args:
            server_recordings: Lista nagrań z serwera
        """
        try:
            for server_rec in server_recordings:
                rec_id = server_rec['id']
                
                # Sprawdź czy istnieje lokalnie
                local_rec = self.db_manager.get_recording(rec_id)
                
                if not local_rec:
                    # Nowe nagranie z serwera - dodaj
                    logger.debug(f"[CallCryptor Sync] New recording from server: {rec_id}")
                    # TODO: Implement add_recording_from_server
                    continue
                
                # Porównaj updated_at (Last-Write-Wins)
                server_updated = datetime.fromisoformat(server_rec['updated_at']) if isinstance(server_rec['updated_at'], str) else server_rec['updated_at']
                local_updated = datetime.fromisoformat(local_rec['updated_at']) if isinstance(local_rec['updated_at'], str) else local_rec['updated_at']
                
                if server_updated > local_updated:
                    # Server ma nowszą wersję - zaktualizuj lokalnie
                    logger.debug(f"[CallCryptor Sync] Server version newer for {rec_id}, updating local")
                    # TODO: Implement update_recording_from_server
                    self.conflicts_resolved += 1
                else:
                    logger.debug(f"[CallCryptor Sync] Local version up-to-date for {rec_id}")
                    
        except Exception as e:
            logger.error(f"[CallCryptor Sync] Error applying server changes: {e}")
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_stats(self) -> Dict[str, Any]:
        """
        Pobierz statystyki synchronizacji.
        
        Returns:
            Dict ze statystykami
        """
        return {
            'sync_enabled': self.sync_enabled,
            'auto_sync_enabled': self.auto_sync_enabled,
            'last_sync_at': self.last_sync_at,
            'sync_count': self.sync_count,
            'error_count': self.error_count,
            'conflicts_resolved': self.conflicts_resolved,
            'is_running': self._is_running
        }
