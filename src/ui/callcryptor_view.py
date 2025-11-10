"""
CallCryptor View - Widok zarządzania nagraniami rozmów
========================================================

Główny widok modułu CallCryptor z funkcjonalnościami:
- Wybór źródła nagrań (folder lokalny / konto e-mail)
- Lista nagrań w formie tabeli
- Akcje: transkrypcja, AI summary, tworzenie notatek/zadań
- Filtrowanie i wyszukiwanie
- Archiwizacja

Integracja:
- Theme Manager dla dynamicznego motywu
- i18n Manager dla wielojęzyczności
- Database Manager dla persystencji danych
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QComboBox, QTableWidget, QTableWidgetItem,
    QHeaderView, QMessageBox, QLineEdit, QFrame, QDialog, QCheckBox
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
from loguru import logger
import json

from .tag_manager_dialog import TagManagerDialog
from .transcription_dialog import TranscriptionDialog
from .ai_summary_dialog import AISummaryDialog
from ..Modules.CallCryptor_module.recorder_dialog import RecorderDialog
from typing import Optional, Dict, List
from pathlib import Path
import os
import json

from ..utils.i18n_manager import t
from ..utils.theme_manager import get_theme_manager
from ..Modules.CallCryptor_module.callcryptor_database import CallCryptorDatabase
from ..Modules.AI_module.ai_logic import get_ai_manager, AIProvider


class CallCryptorView(QWidget):
    """
    Główny widok modułu CallCryptor.
    
    Signals:
        source_changed: Emitowany gdy użytkownik zmieni źródło
        recording_selected: Emitowany gdy użytkownik wybierze nagranie
    """
    
    source_changed = pyqtSignal(str)  # source_id
    recording_selected = pyqtSignal(str)  # recording_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.db_manager = None
        self.user_id = None
        self.current_source_id = None
        
        # Sync infrastructure
        self.api_client = None
        self.sync_manager = None
        
        # Queue mode state
        self.queue_mode_active = False
        self.selected_items = {
            'transcribe': set(),  # Set of recording_ids
            'summarize': set()    # Set of recording_ids
        }
        
        self._setup_ui()
        self.apply_theme()
        
        logger.info("[CallCryptor] View initialized")
    
    def set_user_data(self, user_data: dict):
        """
        Ustaw dane użytkownika i zainicjalizuj bazę danych.
        
        Args:
            user_data: {'id': str, 'email': str, 'access_token': str, 'refresh_token': str, ...}
        """
        self.user_id = user_data.get('id')
        self.user_data = user_data  # Zapisz user_data dla sync infrastructure
        
        # Inicjalizuj bazę danych
        from ..core.config import config
        db_path = config.DATA_DIR / "callcryptor.db"
        self.db_manager = CallCryptorDatabase(str(db_path))
        
        # Inicjalizuj API client i sync manager
        self._init_sync_infrastructure(config)
        
        logger.info(f"[CallCryptor] Initialized for user: {self.user_id}")
        
        # Załaduj źródła
        self._load_sources()
    
    def _init_sync_infrastructure(self, config):
        """Inicjalizuj API client i sync manager"""
        try:
            logger.info("[CallCryptor] Starting sync infrastructure initialization...")
            from ..Modules.CallCryptor_module.recording_api_client import RecordingsAPIClient
            from ..Modules.CallCryptor_module.recordings_sync_manager import RecordingsSyncManager
            
            # Pobierz tokeny z user_data (przekazane w set_user_data)
            auth_token = None
            refresh_token = None
            
            if hasattr(self, 'user_data') and self.user_data:
                auth_token = self.user_data.get('access_token')
                refresh_token = self.user_data.get('refresh_token')
            
            logger.debug(f"[CallCryptor] Auth token present: {bool(auth_token)}")
            logger.debug(f"[CallCryptor] Refresh token present: {bool(refresh_token)}")
            
            # API Base URL z config
            api_base_url = getattr(config, 'API_BASE_URL', 'http://localhost:8000')
            logger.info(f"[CallCryptor] API Base URL: {api_base_url}")
            
            # Inicjalizuj API client
            logger.debug("[CallCryptor] Creating RecordingsAPIClient...")
            self.api_client = RecordingsAPIClient(
                base_url=api_base_url,
                auth_token=auth_token,
                refresh_token=refresh_token,
                on_token_refreshed=self._on_token_refreshed
            )
            logger.info("[CallCryptor] API client created successfully")
            
            # Inicjalizuj sync manager
            settings_path = Path(config.BASE_DIR) / "user_settings.json"
            logger.debug(f"[CallCryptor] Settings path: {settings_path}")
            logger.debug(f"[CallCryptor] User ID: {self.user_id}")
            logger.debug(f"[CallCryptor] DB manager: {self.db_manager}")
            
            logger.debug("[CallCryptor] Creating RecordingsSyncManager...")
            self.sync_manager = RecordingsSyncManager(
                db_manager=self.db_manager,
                api_client=self.api_client,
                user_id=self.user_id,
                config_path=settings_path,
                on_sync_complete=self._on_sync_complete
            )
            logger.info("[CallCryptor] Sync manager created successfully")
            
            # Zaktualizuj kolor przycisku sync
            self._update_sync_button_state()
            
            logger.info("[CallCryptor] Sync infrastructure initialized successfully!")
            
        except Exception as e:
            logger.error(f"[CallCryptor] Error initializing sync: {e}")
            import traceback
            logger.error(f"[CallCryptor] Traceback: {traceback.format_exc()}")
            # Sync opcjonalna - nie blokuj reszty funkcjonalności
    
    def _on_token_refreshed(self, access_token: str, refresh_token: str):
        """Callback po odświeżeniu tokena"""
        try:
            # Zaktualizuj user_data z nowymi tokenami
            if hasattr(self, 'user_data') and self.user_data:
                self.user_data['access_token'] = access_token
                self.user_data['refresh_token'] = refresh_token
                logger.debug("[CallCryptor] Tokens updated in user_data")
            
            # Zapisz do pliku tokens.json (kompatybilność z innymi modułami)
            from ..core.config import config
            tokens_file = config.DATA_DIR / "tokens.json"
            try:
                import json
                tokens_data = {}
                if tokens_file.exists():
                    with open(tokens_file, 'r', encoding='utf-8') as f:
                        tokens_data = json.load(f)
                
                tokens_data['access_token'] = access_token
                tokens_data['refresh_token'] = refresh_token
                
                with open(tokens_file, 'w', encoding='utf-8') as f:
                    json.dump(tokens_data, f, indent=4)
                
                logger.info("[CallCryptor] Tokens saved to tokens.json")
            except Exception as e:
                logger.error(f"[CallCryptor] Error saving tokens: {e}")
                
        except Exception as e:
            logger.error(f"[CallCryptor] Error in token refresh callback: {e}")
    
    def _on_sync_complete(self, success: bool, message: str):
        """Callback po zakończeniu synchronizacji"""
        try:
            if success:
                logger.success(f"[CallCryptor] Sync complete: {message}")
                # Opcjonalnie: odśwież listę nagrań
                # self._load_recordings()
            else:
                logger.error(f"[CallCryptor] Sync failed: {message}")
                # Opcjonalnie: pokaż notyfikację użytkownikowi
        except Exception as e:
            logger.error(f"[CallCryptor] Error in sync complete callback: {e}")
    
    def _update_sync_button_state(self):
        """Zaktualizuj kolor przycisku sync według stanu"""
        if not self.sync_manager:
            return
        
        try:
            if self.sync_manager.sync_enabled:
                # Zielony - sync włączona
                self.sync_btn.setStyleSheet("background-color: #4CAF50; color: white; font-size: 16px;")
                self.sync_btn.setToolTip(t('callcryptor.sync.enabled_tooltip'))
            else:
                # Pomarańczowy - sync wyłączona
                self.sync_btn.setStyleSheet("background-color: #FF8C00; color: white; font-size: 16px;")
                self.sync_btn.setToolTip(t('callcryptor.sync.disabled_tooltip'))
        except Exception as e:
            logger.error(f"[CallCryptor] Error updating sync button: {e}")
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # === NAGŁÓWEK ===
        header_layout = QHBoxLayout()
        
        # Tytuł
        title_label = QLabel(t('callcryptor.title'))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # === TOOLBAR ===
        toolbar_layout = QHBoxLayout()
        
        # Wybór źródła
        source_label = QLabel(f"{t('callcryptor.source')}:")
        source_label.setMinimumWidth(60)
        toolbar_layout.addWidget(source_label)
        
        self.source_combo = QComboBox()
        self.source_combo.setMinimumWidth(250)
        self.source_combo.addItem(t('callcryptor.all_recordings'), None)
        self.source_combo.addItem("⭐ " + t('callcryptor.folder.favorites'), "favorites")
        self.source_combo.currentIndexChanged.connect(self._on_source_changed)
        toolbar_layout.addWidget(self.source_combo)
        
        toolbar_layout.addSpacing(20)
        
        # Przyciski akcji - tylko emoji z tooltipami
        self.add_source_btn = QPushButton("➕")
        self.add_source_btn.setToolTip(t('callcryptor.add_source_tooltip'))
        self.add_source_btn.setMaximumWidth(45)
        self.add_source_btn.clicked.connect(self._add_source)
        toolbar_layout.addWidget(self.add_source_btn)

        self.remove_source_btn = QPushButton("➖")
        self.remove_source_btn.setToolTip(t('callcryptor.tooltip.remove_source'))
        self.remove_source_btn.setMaximumWidth(45)
        self.remove_source_btn.clicked.connect(self._remove_source)
        self.remove_source_btn.setEnabled(False)  # Włączy się gdy wybrane źródło
        toolbar_layout.addWidget(self.remove_source_btn)
        
        
        self.edit_source_btn = QPushButton("🛠️")
        self.edit_source_btn.setToolTip(t('callcryptor.tooltip.edit_source'))
        self.edit_source_btn.setMaximumWidth(45)
        self.edit_source_btn.clicked.connect(self._edit_source)
        self.edit_source_btn.setEnabled(False)  # Włączy się gdy wybrane źródło
        toolbar_layout.addWidget(self.edit_source_btn)
        
      
        
        toolbar_layout.addSpacing(10)
        
        self.refresh_btn = QPushButton("🔄")
        self.refresh_btn.setToolTip(t('callcryptor.refresh_tooltip'))
        self.refresh_btn.setMaximumWidth(45)
        self.refresh_btn.clicked.connect(self._scan_source)
        self.refresh_btn.setEnabled(False)  # Włączy się gdy wybrane źródło
        toolbar_layout.addWidget(self.refresh_btn)
        
       
        
        self.record_btn = QPushButton("⏺️")
        self.record_btn.setToolTip(t('callcryptor.record_tooltip'))
        self.record_btn.setMaximumWidth(45)
        self.record_btn.clicked.connect(self._start_recording)
        toolbar_layout.addWidget(self.record_btn)
        
        self.queue_btn = QPushButton("👥")
        self.queue_btn.setToolTip(t('callcryptor.queue_tooltip'))
        self.queue_btn.setMaximumWidth(45)
        self.queue_btn.clicked.connect(self._manage_queue)
        toolbar_layout.addWidget(self.queue_btn)
        
        self.export_btn = QPushButton("💾")
        self.export_btn.setToolTip(t('callcryptor.export_tooltip'))
        self.export_btn.setMaximumWidth(45)
        self.export_btn.clicked.connect(self._export_recordings)
        toolbar_layout.addWidget(self.export_btn)
        
        self.tags_btn = QPushButton("🏷️")
        self.tags_btn.setToolTip(t('callcryptor.edit_tags_tooltip'))
        self.tags_btn.setMaximumWidth(45)
        self.tags_btn.clicked.connect(self._edit_tags)
        toolbar_layout.addWidget(self.tags_btn)
        
        # Przycisk synchronizacji - pomarańczowy (OFF) / zielony (ON)
        self.sync_btn = QPushButton("📨")
        self.sync_btn.setToolTip(t('callcryptor.sync.disabled_tooltip'))
        self.sync_btn.setMaximumWidth(45)
        self.sync_btn.clicked.connect(self._on_sync_clicked)
        # Domyślnie pomarańczowy (sync wyłączona)
        self.sync_btn.setStyleSheet("background-color: #FF8C00; color: white; font-size: 16px;")
        toolbar_layout.addWidget(self.sync_btn)
        
        toolbar_layout.addStretch()
        
        layout.addLayout(toolbar_layout)
        
        # === WYSZUKIWARKA I FILTRY (jeden wiersz) ===
        search_layout = QHBoxLayout()
        
        # Wyszukiwarka
        search_label = QLabel("🔎")
        search_label.setFont(QFont("Segoe UI Emoji", 14))
        search_layout.addWidget(search_label)
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t('callcryptor.search_placeholder'))
        self.search_input.textChanged.connect(self._on_search)
        self.search_input.setMinimumWidth(300)
        search_layout.addWidget(self.search_input)
        
        search_layout.addSpacing(20)
        
        # Filtr tagów
        tag_label = QLabel(f"🏷️ {t('callcryptor.filter.tag')}:")
        search_layout.addWidget(tag_label)
        
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.setMinimumWidth(150)
        self.tag_filter_combo.addItem(t('callcryptor.filter.all_tags'), None)
        self.tag_filter_combo.currentIndexChanged.connect(self._apply_filters)
        search_layout.addWidget(self.tag_filter_combo)
        
        search_layout.addSpacing(20)
        
        # Filtr daty
        date_label = QLabel(f"📅 {t('callcryptor.filter.date')}:")
        search_layout.addWidget(date_label)
        
        self.date_filter_combo = QComboBox()
        self.date_filter_combo.setMinimumWidth(150)
        self.date_filter_combo.addItem(t('callcryptor.filter.all_dates'), None)
        self.date_filter_combo.addItem(t('callcryptor.filter.today'), "today")
        self.date_filter_combo.addItem(t('callcryptor.filter.yesterday'), "yesterday")
        self.date_filter_combo.addItem(t('callcryptor.filter.last_7_days'), "last_7_days")
        self.date_filter_combo.addItem(t('callcryptor.filter.last_30_days'), "last_30_days")
        self.date_filter_combo.addItem(t('callcryptor.filter.this_month'), "this_month")
        self.date_filter_combo.addItem(t('callcryptor.filter.last_month'), "last_month")
        self.date_filter_combo.currentIndexChanged.connect(self._apply_filters)
        search_layout.addWidget(self.date_filter_combo)
        
        search_layout.addStretch()
        
        layout.addLayout(search_layout)
        
        # === SEPARATOR ===
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # === TABELA NAGRAŃ ===
        self.recordings_table = QTableWidget()
        self.recordings_table.setColumnCount(12)
        self.recordings_table.setHorizontalHeaderLabels([
            "⭐",  # Favorite
            t('callcryptor.table.contact'),
            t('callcryptor.table.duration'),
            t('callcryptor.table.date'),
            t('callcryptor.table.tag'),
            "▶️",  # Play button - przeniesiony za Tag
            t('callcryptor.table.transcribe'),
            t('callcryptor.table.ai_summary'),
            t('callcryptor.table.note'),
            t('callcryptor.table.task'),
            t('callcryptor.table.archive'),
            t('callcryptor.table.delete')
        ])
        
        # Konfiguracja tabeli
        self.recordings_table.setAlternatingRowColors(True)
        self.recordings_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.recordings_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.recordings_table.verticalHeader().setVisible(False)
        
        # Zwiększ wysokość wierszy aby pomieścić gwiazdki i combobox
        self.recordings_table.verticalHeader().setDefaultSectionSize(45)
        
        # Rozciągnij kolumny
        header = self.recordings_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Favorite
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Contact
        for i in range(2, 12):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        
        # Podłącz sygnały
        self.recordings_table.itemSelectionChanged.connect(self._on_recording_selected)
        self.recordings_table.itemDoubleClicked.connect(self._on_recording_double_clicked)
        
        layout.addWidget(self.recordings_table)
        
        # === STATUS BAR ===
        status_layout = QHBoxLayout()
        
        self.status_label = QLabel(t('callcryptor.status.ready'))
        self.status_label.setStyleSheet("color: #666; font-style: italic;")
        status_layout.addWidget(self.status_label)
        
        status_layout.addStretch()
        
        self.count_label = QLabel("")
        self.count_label.setStyleSheet("color: #666;")
        status_layout.addWidget(self.count_label)
        
        layout.addLayout(status_layout)
    
    def _load_sources(self):
        """Załaduj źródła do combo boxa"""
        if not self.db_manager or not self.user_id:
            return
        
        # Sprawdź i utwórz systemowy folder "Nagrania" jeśli nie istnieje
        self._ensure_recordings_folder_source()
        
        # Zapisz poprzedni wybór
        previous_source_id = self.current_source_id
        
        # Wyczyść combo
        self.source_combo.clear()
        
        # Dodaj stałe foldery systemowe (nieusuwalne)
        self.source_combo.addItem(t('callcryptor.all_recordings'), None)
        self.source_combo.addItem("⭐ " + t('callcryptor.folder.favorites'), "favorites")
        
        # Pobierz źródła z bazy
        sources = self.db_manager.get_all_sources(self.user_id, active_only=True)
        
        # Załaduj tagi do filtra
        self._load_tags_filter()
    
    def _load_tags_filter(self):
        """Załaduj tagi do filtru tagów"""
        if not self.db_manager or not self.user_id:
            return
        
        # Zapisz aktualny wybór
        current_tag = self.tag_filter_combo.currentData()
        
        # Wyczyść combo tagów
        self.tag_filter_combo.clear()
        self.tag_filter_combo.addItem(t('callcryptor.filter.all_tags'), None)
        
        # Dodaj opcję "Ulubione"
        self.tag_filter_combo.addItem("⭐ " + t('callcryptor.folder.favorites'), "favorites")
        
        # Pobierz wszystkie unikalne tagi z nagrań
        recordings = self.db_manager.get_all_recordings(self.user_id)
        if not recordings:
            recordings = []
        
        all_tags = set()
        
        for recording in recordings:
            tags = recording.get('tags', [])
            # Jeśli tags jest JSON stringiem, sparsuj
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = []
            
            # Upewnij się, że tags jest listą
            if not tags:
                tags = []
            if not isinstance(tags, list):
                tags = []
            
            for tag in tags:
                if tag:
                    all_tags.add(tag)
        
        # Dodaj tagi do combo (posortowane alfabetycznie)
        for tag in sorted(all_tags):
            self.tag_filter_combo.addItem(f"🏷️ {tag}", tag)
        
        # Przywróć poprzedni wybór jeśli istnieje
        if current_tag:
            index = self.tag_filter_combo.findData(current_tag)
            if index >= 0:
                self.tag_filter_combo.setCurrentIndex(index)
    
    def _ensure_recordings_folder_source(self):
        """
        Sprawdź i utwórz systemowe źródło 'Nagrania' jeśli nie istnieje.
        To źródło jest automatycznie dodawane dla każdego użytkownika.
        """
        if not self.db_manager or not self.user_id:
            return
        
        try:
            # Ścieżka do folderu Nagrania
            app_dir = Path(__file__).parent.parent.parent
            recordings_folder = app_dir / "Nagrania"
            
            # Sprawdź czy źródło już istnieje w bazie
            sources = self.db_manager.get_all_sources(self.user_id, active_only=True)
            recordings_source_exists = False
            recordings_source_id = None
            
            for source in sources:
                if source.get('source_name') == 'Nagrania':
                    # Źródło już istnieje
                    recordings_source_exists = True
                    recordings_source_id = source.get('id')
                    logger.debug("[CallCryptor] Recordings folder source already exists")
                    break
            
            if recordings_source_exists:
                # Sprawdź czy folder ma jakieś nagrania w bazie
                if recordings_source_id:
                    recordings = self.db_manager.get_recordings_by_source(recordings_source_id)
                    if len(recordings) == 0 and recordings_folder.exists():
                        # Źródło istnieje, ale nie ma nagrań - może wymaga skanowania
                        audio_files = list(recordings_folder.glob('*.[wW][aA][vV]')) + \
                                     list(recordings_folder.glob('*.[mM][pP]3')) + \
                                     list(recordings_folder.glob('*.[mM]4[aA]')) + \
                                     list(recordings_folder.glob('*.[oO][gG][gG]'))
                        
                        if len(audio_files) > 0:
                            self._scan_recordings_folder_silently(recordings_source_id, recordings_folder)
                return
            
            # Utwórz folder fizycznie jeśli nie istnieje
            if not recordings_folder.exists():
                recordings_folder.mkdir(parents=True, exist_ok=True)
            
            # Dodaj źródło do bazy danych
            source_data = {
                'source_name': 'Nagrania',
                'source_type': 'folder',
                'folder_path': str(recordings_folder.absolute()),
                'file_extensions': ['.wav', '.mp3', '.m4a', '.ogg'],
                'scan_depth': 1,
                'auto_scan': False,
                'is_active': True
            }
            
            source_id = self.db_manager.add_source(source_data, self.user_id)
            
            # Automatycznie zeskanuj folder jeśli zawiera pliki
            audio_files = list(recordings_folder.glob('*.[wW][aA][vV]')) + \
                         list(recordings_folder.glob('*.[mM][pP]3')) + \
                         list(recordings_folder.glob('*.[mM]4[aA]')) + \
                         list(recordings_folder.glob('*.[oO][gG][gG]'))
            
            if len(audio_files) > 0:
                self._scan_recordings_folder_silently(source_id, recordings_folder)
            
        except Exception as e:
            logger.error(f"[CallCryptor] Error ensuring recordings folder source: {e}")
    
    def _scan_recordings_folder_silently(self, source_id: str, folder_path: Path):
        """
        Cicho zeskanuj folder Nagrania w tle (bez dialogu postępu).
        
        Args:
            source_id: ID źródła Nagrania
            folder_path: Ścieżka do folderu
        """
        try:
            from ..Modules.CallCryptor_module.source_scanner import FolderScanner
            
            scanner = FolderScanner(self.db_manager)
            results = scanner.scan_folder(
                source_id=source_id,
                folder_path=str(folder_path.absolute()),
                extensions=['.wav', '.mp3', '.m4a', '.ogg'],
                max_depth=1,
                progress_callback=None  # Brak callbacku = brak UI
            )
            
            if results:
                logger.info(f"[CallCryptor] Auto-scan completed: "
                           f"{results.get('added', 0)} added, {results.get('updated', 0)} updated")
            
        except Exception as e:
            logger.error(f"[CallCryptor] Error auto-scanning Nagrania folder: {e}")
    
    def _get_available_tags(self) -> dict:
        """
        Pobierz wszystkie dostępne tagi z ich kolorami.
        
        Returns:
            dict: {tag_name: tag_color}
        """
        # TODO: Pobierz z bazy danych gdy będzie implementacja
        # Na razie zwracamy przykładowe tagi
        return {
            t('callcryptor.tags.important'): "#e74c3c",
            t('callcryptor.tags.work'): "#3498db",
            t('callcryptor.tags.personal'): "#2ecc71",
            t('callcryptor.tags.to_review'): "#f39c12"
        }
    
    def _on_source_changed(self, index: int):
        """Obsługa zmiany źródła"""
        source_id = self.source_combo.itemData(index)
        self.current_source_id = source_id
        
        # Włącz/wyłącz przyciski zarządzania źródłem
        # Przyciski są aktywne tylko dla prawdziwych źródeł (nie dla "Wszystkie" i "Ulubione")
        has_real_source = source_id is not None and source_id != "favorites"
        
        self.refresh_btn.setEnabled(has_real_source)
        self.edit_source_btn.setEnabled(has_real_source)
        self.remove_source_btn.setEnabled(has_real_source)
        
        # Załaduj nagrania
        self._load_recordings()
        
        # Emituj sygnał tylko dla prawdziwych źródeł (nie dla "favorites")
        if source_id and source_id != "favorites":
            self.source_changed.emit(source_id)
    
    def _load_recordings(self):
        """Załaduj nagrania do tabeli"""
        if not self.db_manager or not self.user_id:
            logger.warning("[CallCryptor] Cannot load recordings - no db_manager or user_id")
            return
        
        # Załaduj tagi do filtra przed załadowaniem nagrań
        self._load_tags_filter()
        
        # Pobierz nagrania według źródła
        if self.current_source_id == "favorites":
            recordings = self.db_manager.get_favorite_recordings(self.user_id)
        elif self.current_source_id:
            recordings = self.db_manager.get_recordings_by_source(self.current_source_id)
        else:
            recordings = self.db_manager.get_all_recordings(self.user_id)
        
        # Wypełnij tabelę
        self._populate_table(recordings)
        
        # Aktualizuj licznik
        self._update_count_label(len(recordings))
    
    def _on_recording_selected(self):
        """Obsługa wyboru nagrania"""
        selected_rows = self.recordings_table.selectedItems()
        if selected_rows:
            row = selected_rows[0].row()
            # ID jest w kolumnie 1 (Contact) - po Favorite
            recording_id = self.recordings_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
            self.recording_selected.emit(recording_id)
    
    def _on_recording_double_clicked(self, item):
        """
        Obsługa podwójnego kliknięcia - otwórz folder z plikiem.
        
        Args:
            item: QTableWidgetItem który został kliknięty
        """
        if not self.db_manager:
            return
        
        row = item.row()
        # Pobierz ID nagrania z kolumny Contact
        recording_id = self.recordings_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        
        if not recording_id:
            return
        
        # Pobierz nagranie z bazy
        recording = self.db_manager.get_recording(recording_id)
        if not recording:
            return
        
        file_path = recording.get('file_path')
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                t('warning.general'),
                t('callcryptor.warning.file_not_found')
            )
            return
        
        try:
            import platform
            import subprocess
            
            # Otwórz folder i zaznacz plik
            system = platform.system()
            
            if system == 'Windows':
                # Windows: explorer /select,"path"
                subprocess.run(['explorer', '/select,', file_path])
            elif system == 'Darwin':  # macOS
                # macOS: open -R "path"
                subprocess.run(['open', '-R', file_path])
            else:  # Linux
                # Linux: otwórz folder w menedżerze plików
                folder_path = os.path.dirname(file_path)
                subprocess.run(['xdg-open', folder_path])
            
            logger.info(f"[CallCryptor] Opened folder for: {file_path}")
            self._set_status(f"📁 Otwarto folder: {os.path.basename(file_path)}", success=True)
        
        except Exception as e:
            logger.error(f"[CallCryptor] Failed to open folder: {e}")
            QMessageBox.critical(
                self,
                t('error.general'),
                f"Nie udało się otworzyć folderu:\n{str(e)}"
            )
    
    def _play_recording(self, recording: Dict):
        """
        Odtwórz nagranie.
        
        Args:
            recording: Dict z danymi nagrania (zawiera file_path)
        """
        file_path = recording.get('file_path')
        
        if not file_path or not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                t('warning.general'),
                t('callcryptor.warning.file_not_found')
            )
            logger.warning(f"[CallCryptor] Recording file not found: {file_path}")
            return
        
        try:
            # Otwórz plik w domyślnym odtwarzaczu systemu
            import platform
            import subprocess
            
            system = platform.system()
            
            if system == 'Windows':
                os.startfile(file_path)
            elif system == 'Darwin':  # macOS
                subprocess.run(['open', file_path])
            else:  # Linux
                subprocess.run(['xdg-open', file_path])
            
            logger.info(f"[CallCryptor] Playing: {file_path}")
            self._set_status(f"{t('callcryptor.status.playing')}: {recording.get('file_name', '')}", success=True)
        
        except Exception as e:
            logger.error(f"[CallCryptor] Failed to play recording: {e}")
            QMessageBox.critical(
                self,
                t('error.general'),
                f"{t('callcryptor.error.playback_failed')}:\n{str(e)}"
            )
    
    def _on_search(self, text: str):
        """Filtrowanie tabeli na podstawie wyszukiwania"""
        for row in range(self.recordings_table.rowCount()):
            match = False
            for col in range(4):  # Szukaj w pierwszych 4 kolumnach
                item = self.recordings_table.item(row, col)
                if item and text.lower() in item.text().lower():
                    match = True
                    break
            self.recordings_table.setRowHidden(row, not match)
    
    def _add_source(self):
        """Dodaj nowe źródło nagrań"""
        from .callcryptor_dialogs import AddSourceDialog
        
        dialog = AddSourceDialog(self)
        if dialog.exec():
            source_data = dialog.get_source_data()
            
            try:
                source_id = self.db_manager.add_source(source_data, self.user_id)
                logger.success(f"[CallCryptor] Source added: {source_id}")
                
                # Odśwież listę źródeł
                self._load_sources()
                
                # Wybierz nowe źródło
                for i in range(self.source_combo.count()):
                    if self.source_combo.itemData(i) == source_id:
                        self.source_combo.setCurrentIndex(i)
                        break
                
                self._set_status(t('callcryptor.status.source_added'), success=True)
                
                # Automatyczne skanowanie folderu po dodaniu
                if source_data.get('source_type') == 'folder':
                    self._scan_source()
                
            except Exception as e:
                logger.error(f"[CallCryptor] Failed to add source: {e}")
                QMessageBox.critical(
                    self,
                    t('error.general'),
                    f"{t('callcryptor.error.add_source_failed')}:\n{str(e)}"
                )
    
    def _edit_source(self):
        """Edytuj wybrane źródło"""
        source_id = self.source_combo.currentData()
        if not source_id or source_id in ['favorites']:
            QMessageBox.warning(
                self,
                t('warning.general'),
                t('callcryptor.warning.select_source_to_edit')
            )
            return
        
        # TODO: Implementacja edycji źródła
        # 1. Pobierz dane źródła z bazy
        # 2. Otwórz dialog z wypełnionymi danymi
        # 3. Zapisz zmiany
        
        QMessageBox.information(
            self,
            t('callcryptor.dialog.edit_source'),
            t('callcryptor.message.edit_source_coming_soon')
        )
    
    def _remove_source(self):
        """Usuń wybrane źródło"""
        source_id = self.source_combo.currentData()
        if not source_id or source_id in ['favorites']:
            QMessageBox.warning(
                self,
                t('warning.general'),
                t('callcryptor.warning.select_source_to_delete')
            )
            return
        
        # Pobierz nazwę źródła
        source = self.db_manager.get_source(source_id)
        if not source:
            QMessageBox.critical(
                self,
                t('error.general'),
                t('callcryptor.error.source_not_found')
            )
            return
        
        # Potwierdzenie
        reply = QMessageBox.question(
            self,
            t('callcryptor.dialog.remove_source'),
            t('callcryptor.confirm.remove_source').format(
                source_name=source['source_name']
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                # Usuń źródło
                self.db_manager.delete_source(source_id)
                
                # Odśwież listę źródeł
                self._load_sources()
                
                # Przełącz na "Wszystkie nagrania"
                self.source_combo.setCurrentIndex(0)
                
                self._set_status(f"Usunięto źródło: {source['source_name']}", success=True)
                
                QMessageBox.information(
                    self,
                    t('callcryptor.dialog.source_removed'),
                    t('callcryptor.message.source_removed_success').format(
                        source_name=source['source_name']
                    )
                )
                
            except Exception as e:
                logger.error(f"[CallCryptor] Failed to remove source: {e}")
                QMessageBox.critical(
                    self,
                    t('error.general'),
                    t('callcryptor.error.source_removal_failed').format(error=str(e))
                )
    
    def _refresh_recordings(self):
        """Odśwież listę nagrań"""
        self._load_recordings()
        self._set_status(t('callcryptor.status.refreshed'), success=True)
    
    def _scan_source(self):
        """Skanuj źródło w poszukiwaniu nagrań"""
        # Sprawdź czy wybrano źródło
        source_id = self.source_combo.currentData()
        if not source_id:
            QMessageBox.warning(
                self,
                t('warning.general'),
                t('callcryptor.warning.no_source_selected')
            )
            return
        
        # Pobierz źródło z bazy
        source = self.db_manager.get_source(source_id)
        if not source:
            QMessageBox.critical(
                self,
                t('error.general'),
                t('callcryptor.error.source_not_found')
            )
            return
        
        from ..Modules.CallCryptor_module.source_scanner import FolderScanner, EmailScanner
        from PyQt6.QtWidgets import QProgressDialog
        from PyQt6.QtCore import Qt
        
        # Dialog postępu
        progress = QProgressDialog(
            t('callcryptor.scanning.in_progress'),
            t('button.cancel'),
            0, 100,
            self
        )
        progress.setWindowTitle(t('callcryptor.scan'))
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setMinimumDuration(0)
        
        results = None
        
        try:
            if source['source_type'] == 'folder':
                # Skanuj folder
                scanner = FolderScanner(self.db_manager)
                
                # Pobierz rozszerzenia (mogą być już sparsowane lub jako JSON string)
                import json
                file_ext = source.get('file_extensions', ["mp3"])
                extensions = json.loads(file_ext) if isinstance(file_ext, str) else file_ext
                
                def update_progress(current, total, filename):
                    if progress.wasCanceled():
                        return
                    progress.setMaximum(total)
                    progress.setValue(current)
                    progress.setLabelText(f"{t('callcryptor.scanning.processing')}: {filename}")
                
                results = scanner.scan_folder(
                    source_id=source_id,
                    folder_path=source['folder_path'],
                    extensions=extensions,
                    max_depth=source.get('scan_depth', 1),
                    progress_callback=update_progress
                )
            
            elif source['source_type'] == 'email':
                # Skanuj email - DWUETAPOWO
                scanner = EmailScanner(self.db_manager)
                
                # Pobierz konfigurację konta email
                from ..database.email_accounts_db import EmailAccountsDatabase
                from ..core.config import config
                email_db_path = config.DATA_DIR / "email_accounts.db"
                email_db = EmailAccountsDatabase(str(email_db_path))
                email_config = email_db.get_account_config(source['email_account_id'])
                
                if not email_config:
                    QMessageBox.critical(
                        self,
                        t('error.general'),
                        t('callcryptor.error.email_account_not_found')
                    )
                    return
                
                # ETAP 1: PREVIEW - szybkie skanowanie bez pobierania załączników
                progress.setLabelText(t('callcryptor.progress.checking_messages'))
                progress.setMaximum(0)  # Nieokreślony postęp
                
                # Callback dla preview - sprawdza anulowanie
                preview_cancelled = False
                def check_preview_cancel(current, total, message):
                    nonlocal preview_cancelled
                    if progress.wasCanceled():
                        preview_cancelled = True
                        raise InterruptedError(t('callcryptor.error.scan_cancelled_by_user'))
                
                try:
                    preview_results = scanner.scan_email_account(
                        source_id=source_id,
                        email_config=email_config,
                        search_phrase=source.get('search_phrase', 'ALL'),
                        target_folder=source.get('target_folder', 'INBOX'),
                        attachment_pattern=source.get('attachment_pattern', r'.*\.(mp3|wav|m4a|ogg|flac)$'),
                        progress_callback=check_preview_cancel,
                        preview_only=True
                    )
                except (InterruptedError, Exception) as e:
                    progress.close()
                    if preview_cancelled or "anulowane" in str(e).lower():
                        logger.info("[CallCryptor] Preview cancelled by user")
                        return
                    else:
                        raise
                
                progress.close()
                
                # Sprawdź czy znaleziono wiadomości
                if preview_results.get('total_messages', 0) == 0:
                    QMessageBox.information(
                        self,
                        t('callcryptor.scan'),
                        t('callcryptor.message.no_messages_found')
                    )
                    return
                
                # Pokaż dialog wyboru zakresu dat
                from .callcryptor_dialogs import EmailDateRangeDialog
                date_dialog = EmailDateRangeDialog(
                    total_messages=preview_results.get('total_messages', 0),
                    oldest_date=preview_results.get('date_range', {}).get('oldest'),
                    newest_date=preview_results.get('date_range', {}).get('newest'),
                    parent=self
                )
                
                if date_dialog.exec() != QDialog.DialogCode.Accepted:
                    return  # Użytkownik anulował
                
                selected_date_range = date_dialog.get_date_range()
                
                # ETAP 2: DOWNLOAD - pobierz załączniki z wybranego zakresu
                progress = QProgressDialog(
                    t('callcryptor.scanning.in_progress'),
                    t('button.cancel'),
                    0, 100,
                    self
                )
                progress.setWindowTitle(t('callcryptor.scan'))
                progress.setWindowModality(Qt.WindowModality.WindowModal)
                progress.setMinimumDuration(0)
                
                download_cancelled = False
                def update_progress(current, total, message):
                    nonlocal download_cancelled
                    if progress.wasCanceled():
                        download_cancelled = True
                        raise InterruptedError(t('callcryptor.error.download_cancelled_by_user'))
                    progress.setMaximum(total)
                    progress.setValue(current)
                    progress.setLabelText(f"{t('callcryptor.scanning.processing')}: {message}")
                
                try:
                    results = scanner.scan_email_account(
                        source_id=source_id,
                        email_config=email_config,
                        search_phrase=source.get('search_phrase', 'ALL'),
                        target_folder=source.get('target_folder', 'INBOX'),
                        attachment_pattern=source.get('attachment_pattern', r'.*\.(mp3|wav|m4a|ogg|flac)$'),
                        progress_callback=update_progress,
                        preview_only=False,
                        date_range=selected_date_range
                    )
                except (InterruptedError, Exception) as e:
                    if download_cancelled or "anulowane" in str(e).lower():
                        logger.info("[CallCryptor] Download cancelled by user")
                        results = None
                    else:
                        raise
        
        except Exception as e:
            logger.error(f"[CallCryptor] Scan failed: {e}")
            QMessageBox.critical(
                self,
                t('error.general'),
                f"{t('callcryptor.error.scan_failed')}:\n{str(e)}"
            )
            results = None
        
        finally:
            progress.close()
        
        # Pokaż wyniki
        if results:
            # Odśwież listę źródeł (zaktualizuj liczniki)
            self._load_sources()
            
            # Ustaw combo box na przeskanowane źródło
            for i in range(self.source_combo.count()):
                if self.source_combo.itemData(i) == source_id:
                    self.source_combo.setCurrentIndex(i)
                    break
            
            # _on_source_changed() załaduje nagrania automatycznie
            
            # Komunikat z wynikami
            message = f"{t('callcryptor.scanning.results')}:\n\n"
            message += f"📁 {t('callcryptor.scanning.found')}: {results['found']}\n"
            message += f"✅ {t('callcryptor.scanning.added')}: {results['added']}\n"
            message += f"🔄 {t('callcryptor.scanning.duplicates')}: {results['duplicates']}\n"
            
            if results['errors']:
                message += f"\n⚠️ {t('callcryptor.scanning.errors')}: {len(results['errors'])}\n"
                # Pokaż pierwsze 3 błędy
                for error in results['errors'][:3]:
                    message += f"  • {error}\n"
                if len(results['errors']) > 3:
                    message += t('callcryptor.message.and_x_more_errors').format(count=len(results['errors']) - 3)
            
            QMessageBox.information(
                self,
                t('callcryptor.scan'),
                message
            )
            
            self._set_status(
                f"{t('callcryptor.status.scan_complete')}: {results['added']} {t('callcryptor.scanning.new')}",
                success=True
            )
    
    def _export_recordings(self):
        """Eksportuj nagrania do pliku"""
        # TODO: Implementacja w przyszłości
        QMessageBox.information(
            self,
            t('callcryptor.export'),
            t('callcryptor.message.export_coming_soon')
        )
    
    def _edit_tags(self):
        """Zarządzaj tagami"""
        try:
            dialog = TagManagerDialog(self.db_manager, self.user_id, self)
            
            # Odśwież filtry po zamknięciu dialogu jeśli coś się zmieniło
            dialog.tags_changed.connect(self._load_tags_filter)
            
            dialog.exec()
            
        except Exception as e:
            logger.error(f"[CallCryptor] Error opening tag manager: {e}")
            QMessageBox.critical(
                self,
                t('error.general'),
                t('callcryptor.error.tag_manager_failed').format(error=str(e))
            )
    
    def _on_sync_clicked(self):
        """Obsługa kliknięcia przycisku synchronizacji"""
        try:
            from .callcryptor_dialogs import SyncConsentDialog, SyncStatusDialog
            
            if not self.sync_manager:
                QMessageBox.warning(
                    self,
                    t('callcryptor.sync.title'),
                    "Sync manager not initialized"
                )
                return
            
            if not self.sync_manager.sync_enabled:
                # Sync wyłączona - pokazuj dialog zgody
                dialog = SyncConsentDialog(self)
                
                if dialog.exec():
                    # Użytkownik zgodził się
                    auto_sync = dialog.auto_sync_enabled
                    dont_show = dialog.dont_show_again
                    
                    # Włącz synchronizację
                    self.sync_manager.enable_sync(auto_sync=auto_sync)
                    
                    # Zaktualizuj kolor przycisku na zielony
                    self._update_sync_button_state()
                    
                    # Uruchom pierwszą synchronizację
                    logger.info("[CallCryptor] Starting initial sync...")
                    success = self.sync_manager.sync_now()
                    
                    if success:
                        QMessageBox.information(
                            self,
                            t('callcryptor.sync.title'),
                            f"Synchronizacja włączona!\nAuto-sync: {'TAK' if auto_sync else 'NIE'}"
                        )
                    else:
                        QMessageBox.warning(
                            self,
                            t('callcryptor.sync.title'),
                            "Synchronizacja włączona, ale wystąpił błąd podczas pierwszej synchronizacji"
                        )
            else:
                # Sync włączona - pokazuj dialog statusu
                stats = self.sync_manager.get_stats()
                
                # Pobierz dodatkowo statystyki z API
                if self.api_client:
                    response = self.api_client.get_sync_stats()
                    if response.success and response.data and isinstance(response.data, dict):
                        stats.update(response.data)
                
                dialog = SyncStatusDialog(stats, self)
                
                if dialog.exec():
                    # Użytkownik kliknął "Synchronizuj teraz"
                    disable = dialog.disable_sync
                    auto_sync_changed = dialog.auto_sync_checkbox.isChecked() != self.sync_manager.auto_sync_enabled
                    
                    if disable:
                        # Wyłącz synchronizację
                        self.sync_manager.disable_sync()
                        self._update_sync_button_state()
                        
                        QMessageBox.information(
                            self,
                            t('callcryptor.sync.title'),
                            "Synchronizacja wyłączona"
                        )
                    else:
                        # Zaktualizuj auto-sync jeśli zmieniono
                        if auto_sync_changed:
                            new_auto_sync = dialog.auto_sync_checkbox.isChecked()
                            self.sync_manager.auto_sync_enabled = new_auto_sync
                            self.sync_manager._save_settings()
                            
                            if new_auto_sync and not self.sync_manager.is_auto_sync_running():
                                self.sync_manager.start_auto_sync()
                            elif not new_auto_sync and self.sync_manager.is_auto_sync_running():
                                self.sync_manager.stop_auto_sync()
                        
                        # Uruchom synchronizację
                        logger.info("[CallCryptor] Manual sync triggered...")
                        success = self.sync_manager.sync_now()
                        
                        if success:
                            QMessageBox.information(
                                self,
                                t('callcryptor.sync.title'),
                                "Synchronizacja zakończona pomyślnie!"
                            )
                        else:
                            QMessageBox.warning(
                                self,
                                t('callcryptor.sync.title'),
                                "Wystąpił błąd podczas synchronizacji"
                            )
                    
        except Exception as e:
            logger.error(f"[CallCryptor] Error handling sync button: {e}")
            QMessageBox.critical(
                self,
                t('error.general'),
                f"Błąd synchronizacji: {str(e)}"
            )
    
    def _format_duration(self, seconds: int) -> str:
        """Formatuj czas trwania (sekundy -> MM:SS)"""
        if not seconds:
            return "0:00"
        
        minutes = seconds // 60
        secs = seconds % 60
        return f"{minutes}:{secs:02d}"
    
    def _format_date(self, date_str: str) -> str:
        """Formatuj datę do czytelnej formy"""
        if not date_str:
            return ""
        
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_str)
            return dt.strftime("%Y-%m-%d %H:%M")
        except:
            return date_str[:16]  # Fallback
    
    def _update_count_label(self, count: int):
        """Aktualizuj licznik nagrań"""
        self.count_label.setText(
            t('callcryptor.status.recordings_count').format(count=count)
        )
    
    def _set_status(self, message: str, success: bool = False):
        """Ustaw wiadomość w statusie"""
        self.status_label.setText(message)
        if success:
            self.status_label.setStyleSheet("color: #4CAF50; font-style: italic;")
        else:
            self.status_label.setStyleSheet("color: #666; font-style: italic;")
    
    def apply_theme(self):
        """Aplikuj motyw"""
        if not self.theme_manager:
            return
        
        colors = self.theme_manager.get_current_colors()
        
        # Style dla tabeli
        table_style = f"""
            QTableWidget {{
                background-color: {colors.get('bg_main', '#FFFFFF')};
                alternate-background-color: {colors.get('bg_secondary', '#F5F5F5')};
                gridline-color: {colors.get('border_light', '#CCCCCC')};
                color: {colors.get('text_primary', '#000000')};
                border: 1px solid {colors.get('border_light', '#CCCCCC')};
            }}
            QTableWidget::item:selected {{
                background-color: {colors.get('accent_primary', '#2196F3')};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {colors.get('bg_secondary', '#F5F5F5')};
                color: {colors.get('text_primary', '#000000')};
                border: 1px solid {colors.get('border_light', '#CCCCCC')};
                padding: 5px;
                font-weight: bold;
            }}
        """
        self.recordings_table.setStyleSheet(table_style)
        
        # Style dla przycisków
        btn_style = f"""
            QPushButton {{
                background-color: {colors.get('accent_primary', '#2196F3')};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors.get('accent_hover', '#1976D2')};
            }}
            QPushButton:pressed {{
                background-color: {colors.get('accent_pressed', '#0D47A1')};
            }}
            QPushButton:disabled {{
                background-color: {colors.get('border_light', '#CCCCCC')};
                color: {colors.get('text_secondary', '#999999')};
            }}
        """
        for btn in [self.add_source_btn, self.refresh_btn,
                    self.record_btn, self.queue_btn, self.export_btn, self.tags_btn]:
            btn.setStyleSheet(btn_style)
        
        # Style dla wyszukiwarki
        search_style = f"""
            QLineEdit {{
                background-color: {colors.get('bg_main', '#FFFFFF')};
                color: {colors.get('text_primary', '#000000')};
                border: 2px solid {colors.get('border_light', '#CCCCCC')};
                border-radius: 4px;
                padding: 8px;
            }}
            QLineEdit:focus {{
                border: 2px solid {colors.get('accent_primary', '#2196F3')};
            }}
        """
        self.search_input.setStyleSheet(search_style)
    
    def _transcribe_recording(self, recording: dict):
        """
        Uruchom transkrypcję nagrania lub pokaż gotową transkrypcję
        """
        try:
            # Sprawdź czy transkrypcja już istnieje
            if recording.get('transcription_status') == 'completed':
                transcription_text = recording.get('transcription_text', '')
                if transcription_text:
                    # Pokaż gotową transkrypcję w dialogu (tryb readonly)
                    # TranscriptionDialog już zaimportowane na górze pliku
                    
                    # Callback który po prostu zwraca gotowy tekst
                    def show_existing_transcription(audio_path: str) -> str:
                        return transcription_text
                    
                    file_path = recording.get('file_path', '')
                    dialog = TranscriptionDialog(
                        file_path, 
                        show_existing_transcription, 
                        self,
                        recording=recording,
                        db_manager=self.db_manager
                    )
                    dialog.setWindowTitle(t('callcryptor.dialog.ready_transcription'))
                    dialog.exec()
                    return
            
            # Pobierz ścieżkę do pliku
            file_path = recording.get('file_path')
            if not file_path or not Path(file_path).exists():
                QMessageBox.warning(
                    self,
                    t('error.general'),
                    t('callcryptor.error.recording_file_not_found')
                )
                return
            
            # Pobierz AI manager
            ai_manager = get_ai_manager()
            
            # Załaduj ustawienia AI
            from ..Modules.AI_module.ai_logic import load_ai_settings
            settings = load_ai_settings()
            api_keys = settings.get('api_keys', {})
            
            # Sprawdź dostępne providery obsługujące transkrypcję
            supported_providers = []
            
            # Gemini (obsługuje audio w modelach 1.5)
            if api_keys.get('gemini'):
                supported_providers.append(('gemini', AIProvider.GEMINI, 'Google Gemini'))
            
            # OpenAI (Whisper)
            if api_keys.get('openai'):
                supported_providers.append(('openai', AIProvider.OPENAI, 'OpenAI Whisper'))
            
            # Jeśli brak kluczy API
            if not supported_providers:
                QMessageBox.warning(
                    self,
                    t('callcryptor.error.no_ai_configuration'),
                    t('callcryptor.error.missing_api_keys_transcription')
                )
                return
            
            # Użyj pierwszego dostępnego providera (preferowany: Gemini)
            provider_key, provider_enum, provider_name = supported_providers[0]
            
            # Konfiguruj wybranego providera
            current_provider = ai_manager.get_current_provider()
            if current_provider != provider_enum:
                logger.info(f"[CallCryptor] Switching to {provider_name} for transcription")
                
                # Pobierz model z ustawień użytkownika
                selected_model = settings.get('models', {}).get(provider_key)
                
                ai_manager.set_provider(
                    provider=provider_enum,
                    api_key=api_keys.get(provider_key),
                    model=selected_model
                )
            
            # Funkcja callback dla transkrypcji
            def transcribe_audio(audio_path: str) -> str:
                try:
                    return ai_manager.transcribe_audio(audio_path, language="pl")
                except ValueError as e:
                    # Provider nie obsługuje transkrypcji
                    error_msg = str(e)
                    if "does not support" in error_msg:
                        # Spróbuj z innym providerem
                        for alt_key, alt_provider, alt_name in supported_providers[1:]:
                            try:
                                logger.info(f"[CallCryptor] Trying alternative provider: {alt_name}")
                                # Pobierz model z ustawień dla alternatywnego providera
                                alt_model = settings.get('models', {}).get(alt_key)
                                ai_manager.set_provider(
                                    provider=alt_provider,
                                    api_key=api_keys.get(alt_key),
                                    model=alt_model
                                )
                                return ai_manager.transcribe_audio(audio_path, language="pl")
                            except:
                                continue
                        
                        # Wszystkie providery nie obsługują
                        raise ValueError(
                            "Żaden skonfigurowany dostawca AI nie obsługuje transkrypcji audio.\n\n"
                            "Polecani dostawcy:\n"
                            "• Google Gemini (gemini-1.5-pro, gemini-1.5-flash)\n"
                            "• OpenAI Whisper\n\n"
                            "Skonfiguruj klucz API w Ustawieniach → AI"
                        )
                    raise
            
            # Otwórz dialog transkrypcji
            dialog = TranscriptionDialog(
                file_path, 
                transcribe_audio, 
                self,
                recording=recording,
                db_manager=self.db_manager
            )
            
            # Zapisz transkrypcję do bazy danych po zakończeniu
            def on_transcription_completed(transcription_text: str):
                from datetime import datetime
                try:
                    self.db_manager.update_recording(recording['id'], {
                        'transcription_text': transcription_text,
                        'transcription_status': 'completed',
                        'transcription_date': datetime.now().isoformat()
                    })
                    logger.info(f"[CallCryptor] Transcription saved for recording {recording['id']}")
                    # Odśwież tabelę aby pokazać zielony status
                    self._load_recordings()
                except Exception as e:
                    logger.error(f"[CallCryptor] Failed to save transcription: {e}")
            
            dialog.transcription_completed.connect(on_transcription_completed)
            dialog.exec()
            
        except Exception as e:
            logger.error(f"[CallCryptor] Transcription error: {e}")
            QMessageBox.critical(
                self,
                t('callcryptor.error.transcription_error'),
                t('callcryptor.error.transcription_start_failed').format(error=str(e))
            )
    
    def _ai_summary(self, recording: dict, open_tasks_tab: bool = False):
        """
        Generuj lub wyświetl podsumowanie AI dla nagrania
        
        Args:
            recording: Słownik z danymi nagrania
            open_tasks_tab: Czy otworzyć bezpośrednio zakładkę zadań (default: False)
        """
        # Przygotuj i skonfiguruj AI Manager
        try:
            from ..Modules.AI_module.ai_logic import load_ai_settings
            
            ai_manager = get_ai_manager()
            settings = load_ai_settings()
            
            # Pobierz aktywnego providera z ustawień
            active_provider = settings.get('provider')
            api_keys = settings.get('api_keys', {})
            
            # Jeśli brak providera lub brak kluczy API
            if not active_provider:
                QMessageBox.warning(
                    self,
                    t('callcryptor.title'),
                    t('callcryptor.warning.no_active_provider')
                )
                return
            
            # Sprawdź czy jest klucz API dla aktywnego providera
            api_key = api_keys.get(active_provider, '')
            if not api_key:
                QMessageBox.warning(
                    self,
                    t('callcryptor.title'),
                    t('callcryptor.warning.missing_api_key_for_provider').format(provider=active_provider)
                )
                return
            
            # Mapuj klucz na enum
            provider_map = {
                'openai': AIProvider.OPENAI,
                'gemini': AIProvider.GEMINI,
                'claude': AIProvider.CLAUDE,
                'grok': AIProvider.GROK,
                'deepseek': AIProvider.DEEPSEEK
            }
            
            provider = provider_map.get(active_provider)
            if not provider:
                QMessageBox.warning(
                    self,
                    t('callcryptor.title'),
                    t('callcryptor.warning.unknown_provider').format(provider=active_provider)
                )
                return
            
            # Pobierz model
            model = settings.get('models', {}).get(active_provider, '')
            
            # Skonfiguruj providera
            ai_manager.set_provider(
                provider=provider,
                api_key=api_key,
                model=model
            )
            
        except Exception as e:
            logger.error(f"[CallCryptor] AI configuration error: {e}")
            QMessageBox.critical(
                self,
                t('callcryptor.title'),
                t('callcryptor.error.ai_configuration_failed').format(error=str(e))
            )
            return
        
        # Otwórz dialog AI Summary
        dialog = AISummaryDialog(
            recording=recording,
            ai_manager=ai_manager,
            db_manager=self.db_manager,
            parent=self
        )
        
        # Jeśli trzeba otworzyć zakładkę zadań, zrób to po otwarciu dialogu
        if open_tasks_tab:
            # Ustaw zakładkę zadań jako aktywną (zakładając że dialog ma tab_widget)
            QTimer.singleShot(50, lambda: self._switch_to_tasks_tab(dialog))
        
        # Połącz sygnał zakończenia
        dialog.summary_completed.connect(lambda result: self._load_recordings())
        
        dialog.exec()
    
    def _switch_to_tasks_tab(self, dialog):
        """Przełącz dialog AI Summary na zakładkę zadań"""
        try:
            if hasattr(dialog, 'tab_widget'):
                # Znajdź indeks zakładki "Zadania"
                for i in range(dialog.tab_widget.count()):
                    if dialog.tab_widget.tabText(i) in ["Zadania", "Tasks"]:
                        dialog.tab_widget.setCurrentIndex(i)
                        logger.info("[CallCryptor] Switched to tasks tab in AI Summary dialog")
                        break
        except Exception as e:
            logger.error(f"[CallCryptor] Error switching to tasks tab: {e}")

    
    def _create_note(self, recording: dict):
        """
        Utwórz notatkę z nagrania lub otwórz istniejącą
        """
        import uuid
        from datetime import datetime
        
        note_id = recording.get('note_id')
        contact_name = recording.get('contact_info', 'Nieznany kontakt')
        
        # CallCryptorView -> QStackedWidget -> central_widget (QWidget) -> MainWindow
        # Musimy wywołać parent() TRZY razy!
        content_stack = self.parent()
        central_widget = content_stack.parent() if content_stack else None
        main_window = central_widget.parent() if central_widget else None
        
        logger.info(f"[CallCryptor] content_stack={content_stack}, type={type(content_stack)}")
        logger.info(f"[CallCryptor] central_widget={central_widget}, type={type(central_widget)}")
        logger.info(f"[CallCryptor] main_window={main_window}, type={type(main_window)}")
        
        if not main_window:
            logger.error("[CallCryptor] Cannot access main_window - parent().parent() returned None")
            QMessageBox.warning(
                self,
                t('callcryptor.title'),
                t('callcryptor.error.no_main_window')
            )
            return
        
        has_notes_view = hasattr(main_window, 'notes_view')
        logger.info(f"[CallCryptor] hasattr(main_window, 'notes_view')={has_notes_view}")
        
        if has_notes_view:
            notes_view = getattr(main_window, 'notes_view')
            logger.info(f"[CallCryptor] notes_view={notes_view}, type={type(notes_view)}")
        
        if not has_notes_view:
            logger.error("[CallCryptor] notes_view attribute not found on main_window")
            QMessageBox.warning(
                self,
                t('callcryptor.title'),
                t('callcryptor.error.no_notes_view')
            )
            return
        
        if note_id:
            # SCENARIUSZ 1: Notatka już istnieje - otwórz ją
            logger.info(f"[CallCryptor] Opening existing note {note_id} for recording {recording['id']}")
            
            # Przełącz na widok notatek
            main_window._on_view_changed("notes")
            
            # Wybierz notatkę w drzewie po przełączeniu widoku
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, lambda: main_window.notes_view.select_note_in_tree(str(note_id)))
        else:
            # SCENARIUSZ 2: Utwórz nową notatkę
            logger.info(f"[CallCryptor] Creating new note for recording {recording['id']}: {contact_name}")
            
            # Pobierz transkrypcję jeśli istnieje
            transcription_text = recording.get('transcription_text', '')
            if transcription_text:
                note_content = f"<h3>Transkrypcja rozmowy</h3><p>{transcription_text.replace(chr(10), '</p><p>')}</p>"
            else:
                note_content = "<p>Brak transkrypcji</p>"
            
            # Dodaj metadane
            call_date = recording.get('recorded_date', 'nieznana data')
            duration = recording.get('duration', 0)
            note_content = (
                f"<p><b>Data:</b> {call_date}</p>"
                f"<p><b>Kontakt:</b> {contact_name}</p>"
                f"<p><b>Czas trwania:</b> {duration}s</p>"
                f"<hr>"
                f"{note_content}"
            )
            
            # Utwórz notatkę w bazie danych notatek
            note_title = f"ROZMOWA: {contact_name}"
            try:
                new_note_id = main_window.notes_view.db.create_note(
                    title=note_title,
                    content=note_content,
                    color="#FF5722"  # Pomarańczowy dla notatek z rozmów
                )
                
                # Zapisz note_id w nagraniu
                self.db_manager.update_recording(recording['id'], {'note_id': new_note_id})
                
                # Odśwież tabelę aby pokazać zielone podświetlenie
                self._load_recordings()
                
                # Przełącz na widok notatek
                main_window._on_view_changed("notes")
                
                # Odśwież drzewo notatek i wybierz nową notatkę
                def open_new_note():
                    main_window.notes_view.refresh_tree()
                    main_window.notes_view.select_note_in_tree(str(new_note_id))
                
                from PyQt6.QtCore import QTimer
                QTimer.singleShot(100, open_new_note)
                
                logger.info(f"[CallCryptor] Created note {new_note_id} for recording {recording['id']}")
            except Exception as e:
                logger.error(f"[CallCryptor] Error creating note: {e}")
                QMessageBox.warning(
                    self,
                    t('callcryptor.title'),
                    t('callcryptor.error.note_creation_failed').format(error=str(e))
                )
    
    def _create_task(self, recording: dict):
        """
        Utwórz zadanie z nagrania - otwiera dialog AI Summary na zakładce zadań
        """
        # Sprawdź czy jest podsumowanie AI z zadaniami
        ai_summary_tasks = recording.get('ai_summary_tasks')
        has_tasks = False
        
        if ai_summary_tasks:
            try:
                tasks_list = json.loads(ai_summary_tasks) if isinstance(ai_summary_tasks, str) else ai_summary_tasks
                has_tasks = isinstance(tasks_list, list) and len(tasks_list) > 0
            except (json.JSONDecodeError, TypeError):
                pass
        
        if not has_tasks:
            # Brak zadań - poinformuj użytkownika
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                t('callcryptor.title'),
                t('callcryptor.message.no_tasks_in_summary')
            )
            return
        
        # Otwórz dialog AI Summary na zakładce zadań
        self._ai_summary(recording, open_tasks_tab=True)
    
    def _archive_recording(self, recording: dict):
        """
        Archiwizuj nagranie
        """
        from PyQt6.QtWidgets import QMessageBox
        
        # Potwierdź archiwizację
        reply = QMessageBox.question(
            self,
            t('callcryptor.title'),
            t('callcryptor.confirm.archive_recording').format(
                contact=recording.get('contact_info', t('common.unknown')),
                date=recording.get('recording_date', 'N/A')
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        try:
            # Użyj metody archive_recording z db_manager
            recording_id = recording.get('id')
            if not recording_id:
                logger.error("[CallCryptor] Cannot archive: missing recording ID")
                return
            
            # Archiwizuj w bazie danych
            self.db_manager.archive_recording(recording_id)
            
            # Odśwież tabelę
            self._load_recordings()
            
            logger.info(f"[CallCryptor] Recording {recording_id} archived successfully")
            
            QMessageBox.information(
                self,
                t('callcryptor.title'),
                t('callcryptor.message.recording_archived')
            )
            
        except Exception as e:
            logger.error(f"[CallCryptor] Error archiving recording: {e}")
            QMessageBox.critical(
                self,
                t('callcryptor.title'),
                t('callcryptor.error.archive_failed').format(error=str(e))
            )
    
    def _delete_recording(self, recording: dict):
        """
        Usuń nagranie
        TODO: Implementacja z potwierdzeniem
        """
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            t('callcryptor.title'),
            t('callcryptor.confirm.delete_recording').format(
                contact=recording.get('contact_info', t('common.unknown')),
                date=recording.get('date', 'N/A')
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # TODO: Implementacja usuwania z bazy danych
            QMessageBox.information(
                self,
                t('callcryptor.title'),
                t('callcryptor.message.delete_coming_soon')
            )
    
    def _start_recording(self):
        """
        Rozpocznij nowe nagranie.
        Otwiera dialog nagrywania w folderze systemowym 'Nagrania'.
        """
        try:
            # Ścieżka do systemowego folderu Nagrania
            app_dir = Path(__file__).parent.parent.parent
            recordings_folder = app_dir / "Nagrania"
            
            # Upewnij się, że folder istnieje (na wypadek gdyby został usunięty)
            if not recordings_folder.exists():
                recordings_folder.mkdir(parents=True, exist_ok=True)
                logger.info(f"[CallCryptor] Recreated recordings folder: {recordings_folder}")
            
            # Otwórz dialog nagrywania
            dialog = RecorderDialog(recordings_folder, self)
            
            # Połącz sygnał zapisu nagrania
            dialog.recording_saved.connect(self._on_recording_saved)
            
            # Pokaż dialog
            dialog.exec()
            
        except Exception as e:
            logger.error(f"[CallCryptor] Error starting recorder: {e}")
            QMessageBox.critical(
                self,
                t('common.error'),
                t('callcryptor.recorder.error_start') + f"\n{str(e)}"
            )
    
    def _on_recording_saved(self, file_path: str):
        """
        Obsłuż zapisanie nagrania.
        Automatycznie odświeża listę nagrań jeśli folder Nagrania jest aktywnym źródłem.
        
        Args:
            file_path: Ścieżka do zapisanego pliku
        """
        logger.info(f"[CallCryptor] Recording saved: {file_path}")
        
        # Sprawdź czy obecnie wyświetlane jest źródło "Nagrania"
        if self.current_source_id:
            try:
                source = self.db_manager.get_source(self.current_source_id)
                if source and source.get('source_name') == 'Nagrania':
                    # Odśwież listę nagrań
                    logger.info("[CallCryptor] Auto-refreshing recordings list")
                    self._scan_source()
            except Exception as e:
                logger.error(f"[CallCryptor] Error auto-refreshing after recording: {e}")
    
    def _manage_queue(self):
        """Zarządzaj kolejką przetwarzania - przełącz tryb lub uruchom"""
        
        # Sprawdź czy źródło jest wybrane
        if not self.current_source_id:
            QMessageBox.warning(
                self,
                t('callcryptor.title'),
                "Najpierw wybierz źródło nagrań z listy rozwijanej."
            )
            return
        
        if not self.queue_mode_active:
            # Aktywuj tryb kolejki
            self._toggle_queue_mode(True)
        else:
            # Sprawdź co wybrano
            transcribe_count = len(self.selected_items['transcribe'])
            summarize_count = len(self.selected_items['summarize'])
            
            if transcribe_count == 0 and summarize_count == 0:
                QMessageBox.warning(
                    self,
                    t('callcryptor.title'),
                    t('callcryptor.queue.no_files_selected')
                )
                return
            
            # Pokaż dialog potwierdzenia
            reply = QMessageBox.question(
                self,
                t('callcryptor.queue.confirm_title'),
                t('callcryptor.queue.confirm_message').format(
                    transcription_count=transcribe_count,
                    summary_count=summarize_count
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Przygotuj zadania
                tasks = []
                
                # Dodaj zadania transkrypcji
                for rec_id in self.selected_items['transcribe']:
                    recording = self._get_recording_by_id(rec_id)
                    if recording:
                        tasks.append({
                            'action': 'transcribe',
                            'recording_id': rec_id,
                            'file_path': recording.get('file_path', '')
                        })
                
                # Dodaj zadania podsumowania
                for rec_id in self.selected_items['summarize']:
                    recording = self._get_recording_by_id(rec_id)
                    if recording:
                        tasks.append({
                            'action': 'summarize',
                            'recording_id': rec_id,
                            'file_path': recording.get('file_path', '')
                        })
                
                # Wyłącz tryb kolejki
                self._toggle_queue_mode(False)
                
                # Uruchom dialog przetwarzania
                from ..Modules.CallCryptor_module.queue_dialog import ProcessingQueueDialog
                dialog = ProcessingQueueDialog(tasks, self, self.theme_manager, t)
                dialog.exec()
                
                # Odśwież listę po zakończeniu
                self._refresh_table()
    
    def _toggle_queue_mode(self, active: bool):
        """
        Przełącz tryb kolejki
        
        Args:
            active: True = włącz tryb kolejki, False = wyłącz
        """
        self.queue_mode_active = active
        
        if active:
            # Aktywuj tryb kolejki
            self.queue_btn.setText(t('callcryptor.queue.button_execute'))  # "Wykonaj kolejkę"
            self.queue_btn.setStyleSheet("background-color: #FF8C00; color: white; font-weight: bold;")  # Orange
            self.queue_btn.setMaximumWidth(150)  # Zwiększ szerokość dla tekstu
            self.selected_items['transcribe'].clear()
            self.selected_items['summarize'].clear()
            
            # Ukryj zbędne kolumny w trybie kolejki
            # Kolumny: 0-⭐, 1-Contact, 2-Duration, 3-Date, 4-Tag, 5-Play, 6-Transcribe, 7-AI, 8-Note, 9-Task, 10-Archive, 11-Delete
            self.recordings_table.setColumnHidden(5, True)   # Play
            self.recordings_table.setColumnHidden(8, True)   # Note
            self.recordings_table.setColumnHidden(9, True)   # Task
            self.recordings_table.setColumnHidden(10, True)  # Archive
            self.recordings_table.setColumnHidden(11, True)  # Delete
            
            # Ustaw stałą szerokość dla kolumn z checkboxami
            header = self.recordings_table.horizontalHeader()
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)  # Transcribe checkbox
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.Fixed)  # Summarize checkbox
            self.recordings_table.setColumnWidth(6, 80)  # 80px dla checkboxa transkrypcji
            self.recordings_table.setColumnWidth(7, 80)  # 80px dla checkboxa podsumowania
        else:
            # Dezaktywuj tryb kolejki
            self.queue_btn.setText("👥")
            self.queue_btn.setStyleSheet("")  # Reset to theme default
            self.queue_btn.setToolTip(t('callcryptor.queue_tooltip'))
            self.queue_btn.setMaximumWidth(45)  # Przywróć małą szerokość
            self.selected_items['transcribe'].clear()
            self.selected_items['summarize'].clear()
            
            # Pokaż wszystkie kolumny z powrotem
            self.recordings_table.setColumnHidden(5, False)   # Play
            self.recordings_table.setColumnHidden(8, False)   # Note
            self.recordings_table.setColumnHidden(9, False)   # Task
            self.recordings_table.setColumnHidden(10, False)  # Archive
            self.recordings_table.setColumnHidden(11, False)  # Delete
            
            # Przywróć automatyczne dopasowanie szerokości kolumn
            header = self.recordings_table.horizontalHeader()
            header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Transcribe
            header.setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)  # AI Summary
        
        # Przeładuj tabelę z nowymi kolumnami
        self._refresh_table()
    
    def _refresh_table(self):
        """Odśwież tabelę z obecnymi nagraniami"""
        if not self.db_manager or not self.current_source_id:
            logger.warning("[CallCryptor] Cannot refresh - no db_manager or current_source_id")
            return
        
        try:
            recordings = self.db_manager.get_recordings_by_source(self.current_source_id)
            self._populate_table(recordings)
        except Exception as e:
            logger.error(f"[CallCryptor] Error refreshing table: {e}")
    
    def _get_recording_by_id(self, recording_id: str) -> Optional[dict]:
        """
        Pobierz dane nagrania po ID
        
        Args:
            recording_id: ID nagrania
            
        Returns:
            Dict z danymi nagrania lub None
        """
        if not self.db_manager:
            return None
        
        try:
            # Szukaj w całej bazie, nie tylko w aktualnym źródle
            all_recordings = self.db_manager.get_all_recordings(self.user_id)
            for rec in all_recordings:
                if str(rec.get('id')) == str(recording_id):
                    return rec
        except Exception as e:
            logger.error(f"[CallCryptor] Error getting recording {recording_id}: {e}")
        
        return None
    
    def _toggle_favorite(self, recording: dict):
        """
        Przełącz status ulubionego dla nagrania.
        
        Args:
            recording: Dict z danymi nagrania
        """
        if not self.db_manager:
            return
        
        try:
            recording_id = recording.get('id')
            if not recording_id:
                return
            
            # Przełącz status w bazie danych
            new_status = self.db_manager.toggle_favorite(recording_id)
            
            # Odśwież tabelę
            self._load_recordings()
            
            # Pokaż subtelne powiadomienie w status bar
            if new_status:
                self._set_status("⭐ Dodano do ulubionych", success=True)
            else:
                self._set_status("Usunięto z ulubionych", success=True)
            
            logger.info(f"Recording favorite toggled: {recording_id} -> {new_status}")
            
        except Exception as e:
            logger.error(f"Error toggling favorite: {e}")
            QMessageBox.warning(
                self,
                t('callcryptor.title'),
                t('callcryptor.error.favorite_failed')
            )
    
    def _on_tag_changed(self, recording: dict, tag_combo: QComboBox):
        """
        Obsługa zmiany tagu dla nagrania.
        
        Args:
            recording: Dict z danymi nagrania
            tag_combo: QComboBox z którego zmieniono tag
        """
        if not self.db_manager:
            return
        
        try:
            recording_id = recording.get('id')
            if not recording_id:
                return
            
            # Pobierz wybrany tag
            selected_tag = tag_combo.currentData()
            
            # Zaktualizuj tag w bazie danych
            if selected_tag:
                # Zapisz tag jako JSON array z jednym elementem
                tags_json = json.dumps([selected_tag])
                # TODO: Zaimplementuj metodę update_recording_tags w db_manager
                # self.db_manager.update_recording_tags(recording_id, tags_json)
                
                # Zmień kolor tła comboboxa
                available_tags = self._get_available_tags()
                tag_color = available_tags.get(selected_tag, "#FFFFFF")
                tag_combo.setStyleSheet(f"""
                    QComboBox {{
                        background-color: {tag_color};
                        border: 1px solid #999;
                        padding: 3px;
                        border-radius: 3px;
                    }}
                    QComboBox:hover {{
                        border: 2px solid #666;
                    }}
                """)
                
                self._set_status(f"🏷️ Tag zmieniony: {selected_tag}", success=True)
            else:
                # Usuń tag
                # TODO: Zaimplementuj metodę update_recording_tags w db_manager
                # self.db_manager.update_recording_tags(recording_id, json.dumps([]))
                
                # Resetuj styl
                tag_combo.setStyleSheet("")
                
                self._set_status("🏷️ Tag usunięty", success=True)
            
            logger.info(f"Recording tag changed: {recording_id} -> {selected_tag}")
            
        except Exception as e:
            logger.error(f"Error changing tag: {e}")
            QMessageBox.warning(
                self,
                t('error.general'),
                t('callcryptor.error.tag_change_failed').format(error=str(e))
            )
    
    def _apply_filters(self):
        """Zastosuj filtry daty i tagów do listy nagrań"""
        if not self.db_manager or not self.user_id:
            return
        
        # Pobierz wybrane filtry
        date_filter = self.date_filter_combo.currentData()
        tag_filter = self.tag_filter_combo.currentData()
        
        # Pobierz nagrania według źródła
        if self.current_source_id == "favorites":
            recordings = self.db_manager.get_favorite_recordings(self.user_id)
        elif self.current_source_id:
            recordings = self.db_manager.get_recordings_by_source(self.current_source_id)
        else:
            recordings = self.db_manager.get_all_recordings(self.user_id)
        
        # Filtruj po dacie
        if date_filter:
            recordings = self._filter_by_date(recordings, date_filter)
        
        # Filtruj po tagu
        if tag_filter:
            recordings = self._filter_by_tag(recordings, tag_filter)
        
        # Zaktualizuj tabelę
        self._populate_table(recordings)
    
    def _filter_by_date(self, recordings: List[Dict], date_filter: str) -> List[Dict]:
        """
        Filtruj nagrania po dacie.
        
        Args:
            recordings: Lista nagrań
            date_filter: Typ filtra ('today', 'yesterday', 'last_7_days', etc.)
            
        Returns:
            Przefiltrowana lista nagrań
        """
        from datetime import datetime, timedelta
        
        today = datetime.now().date()
        filtered = []
        
        for recording in recordings:
            recording_date_str = recording.get('recording_date') or recording.get('created_at')
            if not recording_date_str:
                continue
            
            try:
                # Parse ISO datetime
                recording_date = datetime.fromisoformat(recording_date_str.replace('Z', '+00:00')).date()
                
                if date_filter == 'today':
                    if recording_date == today:
                        filtered.append(recording)
                elif date_filter == 'yesterday':
                    if recording_date == today - timedelta(days=1):
                        filtered.append(recording)
                elif date_filter == 'last_7_days':
                    if recording_date >= today - timedelta(days=7):
                        filtered.append(recording)
                elif date_filter == 'last_30_days':
                    if recording_date >= today - timedelta(days=30):
                        filtered.append(recording)
                elif date_filter == 'this_month':
                    if recording_date.year == today.year and recording_date.month == today.month:
                        filtered.append(recording)
                elif date_filter == 'last_month':
                    last_month = today.replace(day=1) - timedelta(days=1)
                    if recording_date.year == last_month.year and recording_date.month == last_month.month:
                        filtered.append(recording)
            except (ValueError, AttributeError) as e:
                logger.debug(f"Error parsing date: {e}")
                continue
        
        return filtered
    
    def _filter_by_tag(self, recordings: List[Dict], tag_name: str) -> List[Dict]:
        """
        Filtruj nagrania po tagu.
        
        Args:
            recordings: Lista nagrań
            tag_name: Nazwa tagu lub "favorites" dla ulubionych
            
        Returns:
            Przefiltrowana lista nagrań
        """
        filtered = []
        
        # Filtr dla ulubionych
        if tag_name == "favorites":
            for recording in recordings:
                if recording.get('is_favorite'):
                    filtered.append(recording)
            return filtered
        
        # Filtr dla tagów
        for recording in recordings:
            tags = recording.get('tags', [])
            # Jeśli tags jest JSON stringiem, sparsuj
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags)
                except:
                    tags = []
            
            if tag_name in tags:
                filtered.append(recording)
        
        return filtered
    
    def _populate_table(self, recordings: List[Dict]):
        """
        Wypełnij tabelę nagraniami (helper dla filtrowania).
        
        Args:
            recordings: Lista nagrań do wyświetlenia
        """
        self.recordings_table.setRowCount(len(recordings))
        
        # Pobierz dostępne tagi RAZ przed pętlą (optymalizacja)
        available_tags = self._get_available_tags()
        
        for row, recording in enumerate(recordings):
            # Przycisk Ulubione (Gwiazdka) - KOLUMNA 0
            is_favorite = recording.get('is_favorite', False)
            favorite_btn = QPushButton("\u2605")  # Unicode star character
            favorite_btn.setToolTip(t('callcryptor.tooltip.favorite'))
            favorite_btn.setMaximumWidth(40)
            favorite_btn.setMinimumHeight(30)
            favorite_btn.setFlat(True)
            favorite_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            
            # Ustaw kolor gwiazdki - złota dla ulubionego, szara dla zwykłego
            if is_favorite:
                favorite_btn.setStyleSheet("""
                    QPushButton {
                        font-size: 22px;
                        font-weight: bold;
                        border: none;
                        background: transparent;
                        color: #FFD700;  /* Gold */
                        padding: 0;
                    }
                    QPushButton:hover {
                        color: #FFA500;  /* Orange on hover */
                        background: rgba(255, 215, 0, 0.1);
                    }
                    QPushButton:pressed {
                        color: #FF8C00;  /* Dark orange on press */
                    }
                """)
            else:
                favorite_btn.setStyleSheet("""
                    QPushButton {
                        font-size: 22px;
                        font-weight: bold;
                        border: none;
                        background: transparent;
                        color: #CCCCCC;  /* Light gray */
                        padding: 0;
                    }
                    QPushButton:hover {
                        color: #FFD700;  /* Gold on hover */
                        background: rgba(255, 215, 0, 0.1);
                    }
                    QPushButton:pressed {
                        color: #FFA500;
                    }
                """)
            
            favorite_btn.clicked.connect(lambda checked, r=recording: self._toggle_favorite(r))
            self.recordings_table.setCellWidget(row, 0, favorite_btn)
            
            # Kontakt - KOLUMNA 1
            contact = recording.get('contact_name') or recording.get('file_name') or "Unknown"
            contact_item = QTableWidgetItem(contact)
            contact_item.setData(Qt.ItemDataRole.UserRole, recording['id'])
            self.recordings_table.setItem(row, 1, contact_item)
            
            # Czas trwania - KOLUMNA 2
            duration = recording.get('duration_seconds', 0)
            duration_str = self._format_duration(duration)
            self.recordings_table.setItem(row, 2, QTableWidgetItem(duration_str))
            
            # Data - KOLUMNA 3
            date = recording.get('call_date', '') or recording.get('created_at', '')
            date_str = self._format_date(date)
            self.recordings_table.setItem(row, 3, QTableWidgetItem(date_str))
            
            # Tagi - KOLUMNA 4 (QComboBox z kolorowym tłem)
            tags = recording.get('tags', [])
            # Jeśli tags jest JSON stringiem, sparsuj
            if isinstance(tags, str):
                try:
                    tags = json.loads(tags) if tags else []
                except:
                    tags = []
            
            # Stwórz QComboBox z tagami
            tag_combo = QComboBox()
            tag_combo.setMinimumHeight(35)
            tag_combo.addItem("-- Brak tagu --", None)
            
            # Użyj wcześniej pobranych tagów (optymalizacja)
            for tag_name, tag_color in available_tags.items():
                tag_combo.addItem(f"🏷️ {tag_name}", tag_name)
            
            # Ustaw aktualny tag jeśli istnieje
            current_tag = tags[0] if tags else None
            if current_tag:
                index = tag_combo.findData(current_tag)
                if index >= 0:
                    tag_combo.setCurrentIndex(index)
                    # Ustaw kolor tła komórki
                    tag_color = available_tags.get(current_tag, "#FFFFFF")
                    tag_combo.setStyleSheet(f"""
                        QComboBox {{
                            background-color: {tag_color};
                            border: 1px solid #999;
                            padding: 3px;
                            border-radius: 3px;
                        }}
                        QComboBox:hover {{
                            border: 2px solid #666;
                        }}
                    """)
            
            # Połącz sygnał zmiany
            tag_combo.currentIndexChanged.connect(
                lambda idx, r=recording, combo=tag_combo: self._on_tag_changed(r, combo)
            )
            
            self.recordings_table.setCellWidget(row, 4, tag_combo)
            
            # Przycisk Play - KOLUMNA 5 (przeniesiony za Tag)
            play_btn = self._create_emoji_button(
                "▶️",
                t('callcryptor.play_recording'),
                lambda: self._play_recording(recording)
            )
            self.recordings_table.setCellWidget(row, 5, play_btn)
            
            # Przyciski akcji (kolumny 6-11)
            self._add_action_buttons(row, recording)
    
    def _create_emoji_button(self, emoji: str, tooltip: str, callback, success=False) -> QPushButton:
        """
        Stwórz przycisk z emoji bez ramki, dobrze dopasowany do komórki.
        
        Args:
            emoji: Znak emoji
            tooltip: Tekst tooltipa
            callback: Funkcja wywoływana przy kliknięciu
            success: Czy przycisk ma zielone tło (dla ukończonych akcji)
            
        Returns:
            QPushButton: Skonfigurowany przycisk
        """
        btn = QPushButton(emoji)
        btn.setToolTip(tooltip)
        btn.setFlat(True)
        btn.setCursor(Qt.CursorShape.PointingHandCursor)
        btn.setFixedSize(35, 35)  # Stały rozmiar przycisku aby zmieścił się w komórce
        
        if success:
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 18px;
                    border: none;
                    background: rgba(76, 175, 80, 0.2);  /* Light green */
                    padding: 0;
                    margin: 0;
                    border-radius: 4px;
                }
                QPushButton:hover {
                    background: rgba(76, 175, 80, 0.3);
                }
                QPushButton:pressed {
                    background: rgba(76, 175, 80, 0.4);
                }
            """)
        else:
            btn.setStyleSheet("""
                QPushButton {
                    font-size: 18px;
                    border: none;
                    background: transparent;
                    padding: 0;
                    margin: 0;
                }
                QPushButton:hover {
                    background: rgba(0, 0, 0, 0.05);
                    border-radius: 4px;
                }
                QPushButton:pressed {
                    background: rgba(0, 0, 0, 0.1);
                }
            """)
        btn.clicked.connect(callback)
        return btn
    
    def _add_action_buttons(self, row: int, recording: dict):
        """Dodaj przyciski akcji lub checkboxy do wiersza tabeli"""
        
        if self.queue_mode_active:
            # Tryb kolejki - pokaż checkboxy zamiast przycisków
            
            # Kolumna 6: Checkbox transkrypcji
            transcribe_checkbox = QCheckBox()
            transcribe_checkbox.setStyleSheet("""
                QCheckBox {
                    margin-left: 10px;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                }
            """)
            recording_id = recording.get('id')
            transcribe_checkbox.setChecked(recording_id in self.selected_items['transcribe'])
            transcribe_checkbox.stateChanged.connect(
                lambda state, rid=recording_id: self._on_transcribe_checkbox_changed(rid, state)
            )
            
            widget = QWidget()
            layout = QHBoxLayout(widget)
            layout.addWidget(transcribe_checkbox)
            layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.recordings_table.setCellWidget(row, 6, widget)
            
            # Kolumna 7: Checkbox podsumowania AI
            summarize_checkbox = QCheckBox()
            summarize_checkbox.setStyleSheet("""
                QCheckBox {
                    margin-left: 10px;
                }
                QCheckBox::indicator {
                    width: 20px;
                    height: 20px;
                }
            """)
            summarize_checkbox.setChecked(recording_id in self.selected_items['summarize'])
            summarize_checkbox.stateChanged.connect(
                lambda state, rid=recording_id: self._on_summarize_checkbox_changed(rid, state)
            )
            
            widget2 = QWidget()
            layout2 = QHBoxLayout(widget2)
            layout2.addWidget(summarize_checkbox)
            layout2.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout2.setContentsMargins(0, 0, 0, 0)
            self.recordings_table.setCellWidget(row, 7, widget2)
            
            # Kolumny 8-11: Puste w trybie kolejki
            for col in range(8, 12):
                self.recordings_table.setCellWidget(row, col, None)
        else:
            # Normalny tryb - przyciski akcji
            
            # Kolumna 6: Transkrypcja
            has_transcription = recording.get('transcription_status') == 'completed'
            transcribe_btn = self._create_emoji_button(
                "📝",
                t('callcryptor.tooltip.transcribe'),
                lambda: self._transcribe_recording(recording),
                success=has_transcription
            )
            self.recordings_table.setCellWidget(row, 6, transcribe_btn)
            
            # Kolumna 7: AI Summary
            has_ai_summary = recording.get('ai_summary_status') == 'completed'
            ai_btn = self._create_emoji_button(
                "🪄",
                t('callcryptor.tooltip.ai_summary'),
                lambda: self._ai_summary(recording),
                success=has_ai_summary
            )
            self.recordings_table.setCellWidget(row, 7, ai_btn)
            
            # Kolumna 8: Utwórz notatkę
            has_note = recording.get('note_id') is not None
            note_btn = self._create_emoji_button(
                "📒",
                t('callcryptor.tooltip.create_note'),
                lambda: self._create_note(recording),
                success=has_note
            )
            self.recordings_table.setCellWidget(row, 8, note_btn)
            
            # Kolumna 9: Utwórz zadanie
            # Sprawdź czy są zadania w podsumowaniu AI
            has_ai_tasks = False
            ai_summary_tasks = recording.get('ai_summary_tasks')
            if ai_summary_tasks:
                try:
                    tasks_list = json.loads(ai_summary_tasks) if isinstance(ai_summary_tasks, str) else ai_summary_tasks
                    has_ai_tasks = isinstance(tasks_list, list) and len(tasks_list) > 0
                except (json.JSONDecodeError, TypeError):
                    pass
            
            task_btn = self._create_emoji_button(
                "✅",
                t('callcryptor.tooltip.create_task'),
                lambda: self._create_task(recording),
                success=has_ai_tasks  # Podświetl na zielono jeśli są zadania
            )
            self.recordings_table.setCellWidget(row, 9, task_btn)
            
            # Kolumna 10: Archiwizuj
            archive_btn = self._create_emoji_button(
                "📦",
                t('callcryptor.tooltip.archive'),
                lambda: self._archive_recording(recording)
            )
            self.recordings_table.setCellWidget(row, 10, archive_btn)
            
            # Kolumna 11: Usuń
            delete_btn = self._create_emoji_button(
                "🗑️",
                t('callcryptor.tooltip.delete'),
                lambda: self._delete_recording(recording)
            )
            self.recordings_table.setCellWidget(row, 11, delete_btn)
    
    def _on_transcribe_checkbox_changed(self, recording_id: str, state: int):
        """Obsługa zmiany checkboxa transkrypcji"""
        if state == Qt.CheckState.Checked.value:
            self.selected_items['transcribe'].add(recording_id)
        else:
            self.selected_items['transcribe'].discard(recording_id)
    
    def _on_summarize_checkbox_changed(self, recording_id: str, state: int):
        """Obsługa zmiany checkboxa podsumowania"""
        if state == Qt.CheckState.Checked.value:
            self.selected_items['summarize'].add(recording_id)
        else:
            self.selected_items['summarize'].discard(recording_id)
    
    def update_translations(self):
        """Odśwież tłumaczenia"""
        # TODO: Implementacja po dodaniu wszystkich kluczy i18n
        pass
