"""
Pomodoro View - Interfejs użytkownika dla modułu Pomodoro
==========================================
Wykorzystuje technikkę Pomodoro do zarządzania czasem pracy i przerw.

Funkcjonalności:
- Timer z licznikiem czasu pracy/przerwy
- Automatyczne lub manualne przełączanie między sesjami
- Tematy sesji (edytowalne)
- Statystyki dzienne i historia logów
- Powiadomienia dźwiękowe
- Pełna integracja z systemem motywów i i18n
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QSpinBox, QCheckBox, QProgressBar, QGroupBox, QDialog,
    QLineEdit, QDialogButtonBox, QFrame, QSizePolicy, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QTime, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
import random
from typing import Optional
from pathlib import Path
import winsound
from loguru import logger

from ..utils.i18n_manager import t
from ..config import POMODORO_API_BASE_URL  # Configuration
from ..Modules.Pomodoro_module import (
    PomodoroLogic,
    PomodoroSettings,
    SessionData,
    SessionType,
    SessionStatus,
)
from ..Modules.Pomodoro_module.pomodoro_local_database import PomodoroLocalDatabase
from ..Modules.Pomodoro_module.pomodoro_models import PomodoroSession
from ..Modules.Pomodoro_module.pomodoro_api_client import PomodoroAPIClient
from ..Modules.Pomodoro_module.pomodoro_sync_manager import PomodoroSyncManager
from ..Modules.Pomodoro_module.pomodoro_api_client import PomodoroAPIClient
from ..Modules.Pomodoro_module.pomodoro_sync_manager import PomodoroSyncManager


class PomodoroView(QWidget):
    """Główny widok modułu Pomodoro"""
    
    # Sygnały
    session_started = pyqtSignal()
    session_paused = pyqtSignal()
    session_stopped = pyqtSignal()
    session_completed = pyqtSignal(str)  # typ sesji (work/short_break/long_break)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_data = None
        self.current_theme = "light"
        
        # Callback do zapisu odświeżonych tokenów (przekazany z main.py)
        self.on_token_refreshed_callback = None
        
        # Manager logiki Pomodoro (inicjalizowany w set_user_data)
        self.pomodoro_logic: Optional[PomodoroLogic] = None
        
        # Lokalna baza danych (inicjalizowana w set_user_data)
        self.local_db: Optional[PomodoroLocalDatabase] = None
        
        # API client do synchronizacji z backendem (inicjalizowany w set_user_data)
        self.api_client: Optional['PomodoroAPIClient'] = None
        
        # Sync manager (inicjalizowany w set_user_data)
        self.sync_manager: Optional['PomodoroSyncManager'] = None
        
        # Popup timer window
        self.popup_window: Optional['PomodoroTimerPopup'] = None
        
        # Media player dla dźwięków
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)  # 70% volume
        
        # Timer UI
        self.timer = QTimer()
        self.timer.timeout.connect(self._on_timer_tick)
        self.remaining_seconds = 25 * 60  # 25 minut domyślnie
        self.total_seconds = 25 * 60
        
        # Cytaty motywacyjne
        self.motivation_quotes = [
            "pomodoro.motivation_1",
            "pomodoro.motivation_2",
            "pomodoro.motivation_3",
            "pomodoro.motivation_4",
            "pomodoro.motivation_5",
        ]
        
        self._init_ui()
        self._apply_theme()
        
    def _init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # ========== LEWA SEKCJA (1/3) - AKCJE ==========
        left_section = self._create_action_section()
        main_layout.addWidget(left_section, 1)
        
        # ========== PRAWA SEKCJA (2/3) - USTAWIENIA ==========
        right_section = self._create_settings_section()
        main_layout.addWidget(right_section, 2)
        
    def _create_action_section(self) -> QWidget:
        """Tworzy lewą sekcję z akcjami i timerem"""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setSpacing(15)
        
        # ===== NAGŁÓWEK SESJI =====
        header_layout = QVBoxLayout()
        header_layout.setSpacing(10)
        
        # Tytuł "Sesja pracy"
        self.session_title_label = QLabel(t("pomodoro.session_title"))
        self.session_title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        self.session_title_label.setFont(title_font)
        header_layout.addWidget(self.session_title_label)
        
        # Temat sesji
        self.topic_label = QLabel("Ogólna")  # Domyślna wartość
        self.topic_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        topic_font = QFont()
        topic_font.setPointSize(14)
        self.topic_label.setFont(topic_font)
        self.topic_label.setStyleSheet("color: #666;")
        header_layout.addWidget(self.topic_label)
        
        # Przycisk "Nadaj tytuł"
        self.set_title_btn = QPushButton(t("pomodoro.set_title_btn"))
        self.set_title_btn.clicked.connect(self._on_set_title_clicked)
        self.set_title_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        header_layout.addWidget(self.set_title_btn)
        
        layout.addLayout(header_layout)
        
        # ===== LICZNIKI SESJI =====
        counters_layout = QVBoxLayout()
        counters_layout.setSpacing(5)
        
        # "Dziś wykonano N długich sesji"
        self.long_sessions_label = QLabel(
            t("pomodoro.today_sessions").format(count=0)
        )
        self.long_sessions_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        counters_layout.addWidget(self.long_sessions_label)
        
        # "Sesja krótka N/X"
        self.short_session_label = QLabel(
            t("pomodoro.short_session").format(current=0, total=4)
        )
        self.short_session_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        counters_layout.addWidget(self.short_session_label)
        
        layout.addLayout(counters_layout)
        
        # ===== ZEGAR ODLICZAJĄCY =====
        timer_layout = QVBoxLayout()
        timer_layout.setSpacing(15)
        
        # Duży zegar - wypełnia dostępne miejsce
        self.timer_display = QLabel("25:00")
        self.timer_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        timer_font = QFont()
        timer_font.setPointSize(120)  # BARDZO duży rozmiar
        timer_font.setBold(True)
        self.timer_display.setFont(timer_font)
        self.timer_display.setStyleSheet("""
            color: #FF6B6B; 
            padding: 40px;
            background-color: rgba(255, 107, 107, 0.1);
            border-radius: 15px;
            font-size: 120pt;
        """)
        self.timer_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.timer_display.setMinimumHeight(200)  # Minimum wysokości
        timer_layout.addWidget(self.timer_display, stretch=1)
        
        # Progress Bar - większy i bardziej widoczny
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setFormat("%p%")
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ddd;
                border-radius: 10px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #FF6B6B;
                border-radius: 8px;
            }
        """)
        timer_layout.addWidget(self.progress_bar)
        
        layout.addLayout(timer_layout)
        
        # ===== PRZYCISKI KONTROLI =====
        control_layout = QHBoxLayout()
        control_layout.setSpacing(10)
        
        # Start/Pauza
        self.start_pause_btn = QPushButton(t("pomodoro.btn_start"))
        self.start_pause_btn.clicked.connect(self._on_start_pause_clicked)
        control_layout.addWidget(self.start_pause_btn)
        
        # Reset
        self.reset_btn = QPushButton(t("pomodoro.btn_reset"))
        self.reset_btn.clicked.connect(self._on_reset_clicked)
        control_layout.addWidget(self.reset_btn)
        
        # Pomiń
        self.skip_btn = QPushButton(t("pomodoro.btn_skip"))
        self.skip_btn.clicked.connect(self._on_skip_clicked)
        control_layout.addWidget(self.skip_btn)
        
        # Stop
        self.stop_btn = QPushButton(t("pomodoro.btn_stop"))
        self.stop_btn.clicked.connect(self._on_stop_clicked)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        layout.addLayout(control_layout)
        
        # ===== MOTYWACJA KAIZEN =====
        layout.addStretch()
        
        self.motivation_label = QLabel(self._get_random_motivation())
        self.motivation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.motivation_label.setWordWrap(True)
        motivation_font = QFont()
        motivation_font.setItalic(True)
        motivation_font.setPointSize(10)
        self.motivation_label.setFont(motivation_font)
        self.motivation_label.setStyleSheet("color: #888; padding: 10px;")
        layout.addWidget(self.motivation_label)
        
        return container
        
    def _create_settings_section(self) -> QWidget:
        """Tworzy prawą sekcję z ustawieniami"""
        container = QWidget()
        main_layout = QVBoxLayout(container)
        main_layout.setSpacing(15)
        
        # ===== PODSEKCJA: CZASY SESJI =====
        times_group = QGroupBox(t("pomodoro.times_section"))
        times_layout = QVBoxLayout(times_group)
        times_layout.setSpacing(10)
        
        # Czas pracy
        work_layout = QHBoxLayout()
        work_layout.addWidget(QLabel(t("pomodoro.work_duration")))
        work_layout.addStretch()
        self.work_duration_spin = QSpinBox()
        self.work_duration_spin.setRange(1, 60)
        self.work_duration_spin.setValue(25)
        self.work_duration_spin.setSuffix(" min")
        self.work_duration_spin.valueChanged.connect(self._on_work_duration_changed)
        work_layout.addWidget(self.work_duration_spin)
        times_layout.addLayout(work_layout)
        
        # Krótka przerwa
        short_break_layout = QHBoxLayout()
        short_break_layout.addWidget(QLabel(t("pomodoro.short_break")))
        short_break_layout.addStretch()
        self.short_break_spin = QSpinBox()
        self.short_break_spin.setRange(1, 30)
        self.short_break_spin.setValue(5)
        self.short_break_spin.setSuffix(" min")
        self.short_break_spin.valueChanged.connect(self._on_short_break_duration_changed)
        short_break_layout.addWidget(self.short_break_spin)
        times_layout.addLayout(short_break_layout)
        
        # Długa przerwa
        long_break_layout = QHBoxLayout()
        long_break_layout.addWidget(QLabel(t("pomodoro.long_break")))
        long_break_layout.addStretch()
        self.long_break_spin = QSpinBox()
        self.long_break_spin.setRange(5, 60)
        self.long_break_spin.setValue(15)
        self.long_break_spin.setSuffix(" min")
        self.long_break_spin.valueChanged.connect(self._on_long_break_duration_changed)
        long_break_layout.addWidget(self.long_break_spin)
        times_layout.addLayout(long_break_layout)
        
        # Sesje do długiej przerwy
        sessions_layout = QHBoxLayout()
        sessions_layout.addWidget(QLabel(t("pomodoro.sessions_count")))
        sessions_layout.addStretch()
        self.sessions_count_spin = QSpinBox()
        self.sessions_count_spin.setRange(1, 10)
        self.sessions_count_spin.setValue(4)
        self.sessions_count_spin.valueChanged.connect(self._on_sessions_count_changed)
        sessions_layout.addWidget(self.sessions_count_spin)
        times_layout.addLayout(sessions_layout)
        
        main_layout.addWidget(times_group)
        
        # ===== PODSEKCJA: OPCJE AUTOMATYCZNE =====
        auto_group = QGroupBox(t("pomodoro.auto_section"))
        auto_layout = QVBoxLayout(auto_group)
        auto_layout.setSpacing(10)
        
        # Auto-start przerw
        self.auto_breaks_check = QCheckBox(t("pomodoro.auto_breaks"))
        self.auto_breaks_check.setChecked(False)
        self.auto_breaks_check.stateChanged.connect(self._on_auto_breaks_changed)
        auto_layout.addWidget(self.auto_breaks_check)
        
        # Auto-start pomodoro
        self.auto_pomodoro_check = QCheckBox(t("pomodoro.auto_pomodoro"))
        self.auto_pomodoro_check.setChecked(False)
        self.auto_pomodoro_check.stateChanged.connect(self._on_auto_pomodoro_changed)
        auto_layout.addWidget(self.auto_pomodoro_check)
        
        main_layout.addWidget(auto_group)
        
        # ===== PODSEKCJA: POWIADOMIENIA DŹWIĘKOWE =====
        sounds_group = QGroupBox(t("pomodoro.sounds_section"))
        sounds_layout = QVBoxLayout(sounds_group)
        sounds_layout.setSpacing(10)
        
        # Checkbox: Odtwarzaj dźwięk po zakończeniu sesji pracy
        self.sound_work_end_check = QCheckBox(t("pomodoro.sound_work_end"))
        self.sound_work_end_check.setChecked(True)
        self.sound_work_end_check.stateChanged.connect(self._on_sound_settings_changed)
        sounds_layout.addWidget(self.sound_work_end_check)
        
        # Checkbox: Odtwarzaj dźwięk po zakończeniu przerwy
        self.sound_break_end_check = QCheckBox(t("pomodoro.sound_break_end"))
        self.sound_break_end_check.setChecked(True)
        self.sound_break_end_check.stateChanged.connect(self._on_sound_settings_changed)
        sounds_layout.addWidget(self.sound_break_end_check)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        sounds_layout.addWidget(line)
        
        # Checkbox: Otwórz licznik w popup
        self.popup_timer_check = QCheckBox(t("pomodoro.popup_timer"))
        self.popup_timer_check.setChecked(False)
        self.popup_timer_check.stateChanged.connect(self._on_popup_timer_toggled)
        sounds_layout.addWidget(self.popup_timer_check)
        
        main_layout.addWidget(sounds_group)
        
        # ===== PODSEKCJA: STATYSTYKI DZISIEJSZE =====
        stats_group = QGroupBox(t("pomodoro.stats_today"))
        stats_layout = QVBoxLayout(stats_group)
        stats_layout.setSpacing(10)
        
        # Ukończone sesje
        self.completed_sessions_label = QLabel(
            t("pomodoro.completed_sessions") + ": 0"
        )
        stats_layout.addWidget(self.completed_sessions_label)
        
        # Całkowity czas skupienia
        self.total_focus_label = QLabel(
            t("pomodoro.total_focus_time") + ": 0 min"
        )
        stats_layout.addWidget(self.total_focus_label)
        
        # Przycisk "Pokaż logi"
        self.show_logs_btn = QPushButton(t("pomodoro.show_logs"))
        self.show_logs_btn.clicked.connect(self._on_show_logs_clicked)
        stats_layout.addWidget(self.show_logs_btn)
        
        main_layout.addWidget(stats_group)
        
        # Spacer na końcu
        main_layout.addStretch()
        
        return container
        
    # ========== SLOT HANDLERS ==========
    
    def _on_set_title_clicked(self):
        """Otwiera dialog do ustawienia tytułu sesji"""
        if not self.pomodoro_logic:
            return
        
        # Nie pozwól zmieniać podczas aktywnej sesji
        if self.pomodoro_logic.is_session_active():
            return
        
        current_topic = self.pomodoro_logic.get_current_topic()
        dialog = SessionTitleDialog(current_topic[1], self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            new_topic = dialog.get_title()
            
            # Ustaw w logice (topic_id będzie None dla "Ogólna")
            self.pomodoro_logic.set_topic(topic_id=None, topic_name=new_topic)
            
            # Aktualizuj UI
            self.topic_label.setText(new_topic)
    
    def _on_popup_timer_toggled(self, state):
        """Obsługa zmiany stanu checkbox popup timer"""
        if not self.pomodoro_logic:
            return
        
        is_checked = (state == Qt.CheckState.Checked.value)
        self.pomodoro_logic.settings.popup_timer = is_checked
        
        logger.debug(f"[POMODORO] Popup timer setting changed to: {is_checked}")
        self._save_current_settings()
        
        # Jeśli odznaczamy checkbox podczas aktywnej sesji, zamknij popup
        if not is_checked and self.popup_window:
            self.popup_window.close()
            self.popup_window = None
            logger.debug("[POMODORO] ✅ Popup timer closed")
    
    def _on_sound_settings_changed(self, state):
        """Obsługa zmiany ustawień dźwięku"""
        if not self.pomodoro_logic:
            return
        
        # Aktualizuj ustawienia w logice
        self.pomodoro_logic.settings.sound_work_end = self.sound_work_end_check.isChecked()
        self.pomodoro_logic.settings.sound_break_end = self.sound_break_end_check.isChecked()
        
        logger.debug(f"[POMODORO] Sound settings changed: work={self.pomodoro_logic.settings.sound_work_end}, break={self.pomodoro_logic.settings.sound_break_end}")
        self._save_current_settings()
            
    def _open_popup_if_enabled(self):
        """Otwiera popup timer jeśli checkbox jest zaznaczony"""
        if not self.pomodoro_logic:
            return
        
        # Sprawdź czy popup jest włączony w ustawieniach
        if self.pomodoro_logic.settings.popup_timer and not self.popup_window:
            session_title = self.topic_label.text()
            session_type = (
                self.pomodoro_logic.current_session.session_type 
                if self.pomodoro_logic.current_session 
                else SessionType.WORK
            )
            
            self.popup_window = PomodoroTimerPopup(session_title, session_type, self)
            self.popup_window.pause_requested.connect(self._on_start_pause_clicked)
            self.popup_window.stop_requested.connect(self._on_stop_clicked)
            
            # Aktualizuj wyświetlacz
            self.popup_window.update_display(self.remaining_seconds, self.total_seconds)
            self.popup_window.show()
            
            print("[POMODORO] ✅ Popup timer opened")
    
    def _on_start_pause_clicked(self):
        """Start lub pauza sesji"""
        print(f"[POMODORO] Start/Pause clicked, logic exists: {self.pomodoro_logic is not None}")
        
        if not self.pomodoro_logic:
            print(f"[POMODORO] ERROR: Logic not initialized!")
            return
        
        # START - rozpocznij nową sesję
        if not self.pomodoro_logic.is_session_active():
            print(f"[POMODORO] Starting new session...")
            # Rozpocznij nową sesję (logika automatycznie określi typ)
            session_data = self.pomodoro_logic.start_new_session()
            
            print(f"[POMODORO] Session started: {session_data.session_type.value}, duration: {session_data.planned_duration}min")
            
            # Ustaw timer na odpowiedni czas
            self.total_seconds = self.pomodoro_logic.get_session_duration_seconds()
            self.remaining_seconds = self.total_seconds
            
            print(f"[POMODORO] Timer set to {self.total_seconds} seconds")
            
            # Uruchom timer UI
            self.timer.start(1000)
            
            # Aktualizuj UI
            self.start_pause_btn.setText(t("pomodoro.btn_pause"))
            self.stop_btn.setEnabled(True)
            self.set_title_btn.setEnabled(False)
            self._update_session_title(session_data.session_type)
            self._update_display()
            self._update_counters()
            
            # Otwórz popup jeśli checkbox jest zaznaczony
            self._open_popup_if_enabled()
            
            # Aktualizuj popup jeśli już istnieje
            if self.popup_window:
                self.popup_window.update_display(self.remaining_seconds, self.total_seconds)
                self.popup_window.update_pause_button(t("pomodoro.btn_pause"))
            
            # Sygnał
            self.session_started.emit()
        
        # PAUZA - zapauzuj bieżącą sesję
        elif (self.pomodoro_logic.current_session and 
              self.pomodoro_logic.current_session.status == SessionStatus.RUNNING):
            print(f"[POMODORO] Pausing session...")
            self.pomodoro_logic.pause_session()
            self.timer.stop()
            
            self.start_pause_btn.setText(t("pomodoro.btn_start"))
            self._update_display()
            
            # Aktualizuj popup jeśli istnieje
            if self.popup_window:
                self.popup_window.update_pause_button(t("pomodoro.btn_start"))
            
            self.session_paused.emit()
        
        # WZNOWIENIE - kontynuuj zapauzowaną sesję
        elif (self.pomodoro_logic.current_session and 
              self.pomodoro_logic.current_session.status == SessionStatus.PAUSED):
            print(f"[POMODORO] Resuming session...")
            self.pomodoro_logic.resume_session()
            self.timer.start(1000)
            
            self.start_pause_btn.setText(t("pomodoro.btn_pause"))
            
            # Aktualizuj popup jeśli istnieje
            if self.popup_window:
                self.popup_window.update_pause_button(t("pomodoro.btn_pause"))
            self._update_display()
            
    def _on_reset_clicked(self):
        """Reset timera do początkowego czasu"""
        if not self.pomodoro_logic:
            return
        
        # Reset sesji w logice
        self.pomodoro_logic.reset_session()
        
        # Reset timer UI
        self.total_seconds = self.pomodoro_logic.get_session_duration_seconds()
        self.remaining_seconds = self.total_seconds
        
        # Stop timer jeśli był uruchomiony
        self.timer.stop()
        
        # Aktualizuj UI
        self.start_pause_btn.setText(t("pomodoro.btn_start"))
        self.stop_btn.setEnabled(False)
        self.set_title_btn.setEnabled(True)
        self._update_display()
        
    def _on_skip_clicked(self):
        """Pomija aktualną sesję i przechodzi do kolejnej"""
        if not self.pomodoro_logic or not self.pomodoro_logic.is_session_active():
            return
        
        # Zakończ bieżącą jako pominiętą
        session_data = self.pomodoro_logic.skip_session()
        
        # Stop timer UI
        self.timer.stop()
        
        # Zapisz do bazy (TODO)
        # self._save_session_to_db(session_data)
        
        # Rozpocznij kolejną sesję jeśli auto-start
        if self.pomodoro_logic.should_auto_start_next():
            self._start_next_session()
        else:
            # Manual mode - reset UI i czekaj
            self.start_pause_btn.setText(t("pomodoro.btn_start"))
            self.stop_btn.setEnabled(False)
            self.set_title_btn.setEnabled(True)
            self._reset_timer()
            # TODO: Pokaż pytanie o start następnej sesji
            print("Manual mode: waiting for user to start next session")
        
    def _on_stop_clicked(self):
        """Zatrzymuje całą sesję"""
        if not self.pomodoro_logic or not self.pomodoro_logic.is_session_active():
            return
        
        # Oblicz przepracowany czas
        elapsed_seconds = self.total_seconds - self.remaining_seconds
        
        # Przerwij sesję w logice
        session_data = self.pomodoro_logic.interrupt_session(elapsed_seconds)
        
        # Stop timer UI
        self.timer.stop()
        
        # Zapisz do bazy (TODO)
        # self._save_session_to_db(session_data)
        
        # Reset UI
        self.start_pause_btn.setText(t("pomodoro.btn_start"))
        self.stop_btn.setEnabled(False)
        self.set_title_btn.setEnabled(True)
        self._reset_timer()
        self._update_counters()
        
        self.session_stopped.emit()
        
    def _on_work_duration_changed(self, value):
        """Zmiana czasu pracy"""
        if not self.pomodoro_logic:
            return
        
        self.pomodoro_logic.settings.work_duration = value
        
        # Jeśli nie ma aktywnej sesji i typ to work, zaktualizuj timer
        if not self.pomodoro_logic.is_session_active():
            current_type = self.pomodoro_logic.get_current_session_type()
            if current_type is None or current_type == SessionType.WORK:
                self.total_seconds = value * 60
                self.remaining_seconds = self.total_seconds
                self._update_display()
        
        logger.debug(f"[POMODORO] Work duration changed to: {value} min")
        self._save_current_settings()
    
    def _on_short_break_duration_changed(self, value):
        """Zmiana czasu krótkiej przerwy"""
        if not self.pomodoro_logic:
            return
        
        self.pomodoro_logic.settings.short_break_duration = value
        
        # Jeśli nie ma aktywnej sesji i typ to short break, zaktualizuj timer
        if not self.pomodoro_logic.is_session_active():
            current_type = self.pomodoro_logic.get_current_session_type()
            if current_type == SessionType.SHORT_BREAK:
                self.total_seconds = value * 60
                self.remaining_seconds = self.total_seconds
                self._update_display()
        
        logger.debug(f"[POMODORO] Short break duration changed to: {value} min")
        self._save_current_settings()
    
    def _on_long_break_duration_changed(self, value):
        """Zmiana czasu długiej przerwy"""
        if not self.pomodoro_logic:
            return
        
        self.pomodoro_logic.settings.long_break_duration = value
        
        # Jeśli nie ma aktywnej sesji i typ to long break, zaktualizuj timer
        if not self.pomodoro_logic.is_session_active():
            current_type = self.pomodoro_logic.get_current_session_type()
            if current_type == SessionType.LONG_BREAK:
                self.total_seconds = value * 60
                self.remaining_seconds = self.total_seconds
                self._update_display()
        
        logger.debug(f"[POMODORO] Long break duration changed to: {value} min")
        self._save_current_settings()
            
    def _on_sessions_count_changed(self, value):
        """Zmiana liczby sesji do długiej przerwy"""
        if not self.pomodoro_logic:
            return
        
        self.pomodoro_logic.settings.sessions_count = value
        self._update_counters()
        self._save_current_settings()
    
    def _on_auto_breaks_changed(self, state):
        """Zmiana auto-start przerw"""
        if not self.pomodoro_logic:
            return
        
        is_checked = (state == Qt.CheckState.Checked.value)
        self.pomodoro_logic.settings.auto_start_breaks = is_checked
        
        logger.debug(f"[POMODORO] Auto-start breaks: {is_checked}")
        self._save_current_settings()
    
    def _on_auto_pomodoro_changed(self, state):
        """Zmiana auto-start pomodoro"""
        if not self.pomodoro_logic:
            return
        
        is_checked = (state == Qt.CheckState.Checked.value)
        self.pomodoro_logic.settings.auto_start_pomodoro = is_checked
        
        logger.debug(f"[POMODORO] Auto-start pomodoro: {is_checked}")
        self._save_current_settings()
        
    def _on_show_logs_clicked(self):
        """Pokazuje dialog z logami sesji"""
        if not self.local_db:
            print("⚠️ Local database not initialized")
            return
            
        # Pobierz ostatnie sesje z bazy danych
        sessions = self.local_db.get_recent_sessions(100)
        
        if not sessions:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                "Brak sesji",
                "Nie znaleziono żadnych sesji Pomodoro.\nRozpocznij pierwszą sesję, aby zobaczyć tutaj historię."
            )
            return
        
        # Otwórz dialog z logami
        dialog = SessionLogsDialog(sessions, self)
        dialog.exec()
        
    def _on_timer_tick(self):
        """Odliczanie timera"""
        if self.remaining_seconds > 0:
            self.remaining_seconds -= 1
            self._update_display()
            
            # Aktualizuj popup jeśli istnieje
            if self.popup_window:
                self.popup_window.update_display(self.remaining_seconds, self.total_seconds)
            
            # Debug co 10 sekund
            if self.remaining_seconds % 10 == 0:
                minutes = self.remaining_seconds // 60
                seconds = self.remaining_seconds % 60
                print(f"[POMODORO] Timer: {minutes:02d}:{seconds:02d} remaining")
        else:
            # Koniec sesji
            print(f"[POMODORO] Timer finished! Completing session...")
            self.timer.stop()
            self._finish_current_session(status=SessionStatus.COMPLETED)
            
    # ========== HELPER METHODS ==========
    
    def _reset_timer(self):
        """Resetuje timer do ustawień"""
        if not self.pomodoro_logic:
            self.total_seconds = 25 * 60
            self.remaining_seconds = self.total_seconds
            self._update_display()
            return
        
        # Pobierz czas z logiki
        self.total_seconds = self.pomodoro_logic.get_session_duration_seconds()
        self.remaining_seconds = self.total_seconds
        self._update_display()
        
    def _update_display(self):
        """Aktualizuje wyświetlanie timera i progress bar"""
        minutes = self.remaining_seconds // 60
        seconds = self.remaining_seconds % 60
        self.timer_display.setText(f"{minutes:02d}:{seconds:02d}")
        
        # Progress bar - pokazuje postęp od 0% do 100%
        if self.total_seconds > 0:
            elapsed = self.total_seconds - self.remaining_seconds
            progress = (elapsed / self.total_seconds) * 100
            self.progress_bar.setValue(int(progress))
        else:
            self.progress_bar.setValue(0)
        
        # Zmiana koloru zegara w zależności od typu sesji
        if self.pomodoro_logic and self.pomodoro_logic.current_session:
            session_type = self.pomodoro_logic.current_session.session_type
            if session_type == SessionType.WORK:
                color = "#FF6B6B"  # Czerwony dla pracy
            else:
                color = "#4ECDC4"  # Niebieski dla przerwy
        else:
            color = "#FF6B6B"  # Domyślnie czerwony
        
        self.timer_display.setStyleSheet(f"""
            color: {color}; 
            padding: 40px;
            background-color: rgba({self._hex_to_rgb(color)}, 0.1);
            border-radius: 15px;
            font-size: 120pt;
            font-weight: bold;
        """)
        
        # Aktualizuj kolor progress bar
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #ddd;
                border-radius: 10px;
                text-align: center;
                font-weight: bold;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 8px;
            }}
        """)
    
    def _hex_to_rgb(self, hex_color: str) -> str:
        """Konwertuje kolor HEX na RGB string"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
    
    def _update_session_title(self, session_type: SessionType):
        """Aktualizuje tytuł sesji na podstawie typu"""
        if session_type == SessionType.WORK:
            self.session_title_label.setText(t("pomodoro.session_title"))
        elif session_type == SessionType.SHORT_BREAK:
            self.session_title_label.setText(t("pomodoro.short_break_title"))
        elif session_type == SessionType.LONG_BREAK:
            self.session_title_label.setText(t("pomodoro.long_break_title"))
            
    def _update_counters(self):
        """Aktualizuje liczniki sesji"""
        if not self.pomodoro_logic:
            # Domyślne wartości jeśli logika nie jest jeszcze zainicjalizowana
            self.long_sessions_label.setText(
                t("pomodoro.today_sessions").format(count=0)
            )
            self.short_session_label.setText(
                t("pomodoro.short_session").format(current=0, total=4)
            )
            return
        
        stats = self.pomodoro_logic.get_today_stats()
        progress = self.pomodoro_logic.get_cycle_progress()
        
        # "Dziś wykonano N długich sesji"
        self.long_sessions_label.setText(
            t("pomodoro.today_sessions").format(count=stats['long_sessions'])
        )
        
        # "Sesja krótka N/X"
        self.short_session_label.setText(
            t("pomodoro.short_session").format(
                current=progress[0],
                total=progress[1]
            )
        )
        
    def _finish_current_session(self, status: SessionStatus):
        """Kończy aktualną sesję i zapisuje do logów"""
        if not self.pomodoro_logic or not self.pomodoro_logic.is_session_active():
            return
        
        # Oblicz rzeczywisty czas
        elapsed_seconds = self.total_seconds - self.remaining_seconds
        
        # Zakończ w logice
        if status == SessionStatus.COMPLETED:
            session_data = self.pomodoro_logic.complete_session(elapsed_seconds)
        else:
            session_data = self.pomodoro_logic.interrupt_session(elapsed_seconds)
        
        # Odtwórz dźwięk
        if session_data.session_type == SessionType.WORK:
            if self.pomodoro_logic.settings.sound_work_end and self.sound_work_end_check.isChecked():
                self._play_sound("work_end")
        else:
            if self.pomodoro_logic.settings.sound_break_end and self.sound_break_end_check.isChecked():
                self._play_sound("break_end")
        
        # Zapisz do bazy (TODO)
        # self._save_session_to_db(session_data)
        
        # Emit sygnał
        self.session_completed.emit(session_data.session_type.value)
        
        # Automatyczne przejście lub pytanie
        if self.pomodoro_logic.should_auto_start_next():
            self._start_next_session()
        else:
            # Manual mode - reset UI
            self.start_pause_btn.setText(t("pomodoro.btn_start"))
            self.stop_btn.setEnabled(False)
            self.set_title_btn.setEnabled(True)
            
            # Zamknij popup w trybie manualnym (czekamy na użytkownika)
            if self.popup_window:
                self.popup_window.close()
                self.popup_window = None
                print("[POMODORO] ✅ Popup closed (manual mode)")
            
            # TODO: Pokaż pytanie o start następnej sesji
            print("Manual mode: waiting for user confirmation")
        
    def _start_next_session(self):
        """Rozpoczyna kolejną sesję w cyklu"""
        if not self.pomodoro_logic:
            return
        
        # Rozpocznij nową sesję (logika automatycznie określi typ)
        session_data = self.pomodoro_logic.start_new_session()
        
        # Ustaw timer
        self.total_seconds = self.pomodoro_logic.get_session_duration_seconds()
        self.remaining_seconds = self.total_seconds
        
        # Uruchom timer
        self.timer.start(1000)
        
        # Aktualizuj UI
        self._update_session_title(session_data.session_type)
        self._update_display()
        self._update_counters()
        
        # Przyciski
        self.start_pause_btn.setText(t("pomodoro.btn_pause"))
        self.stop_btn.setEnabled(True)
        self.set_title_btn.setEnabled(False)
        
        # Otwórz popup jeśli checkbox jest zaznaczony
        self._open_popup_if_enabled()
        
        # Aktualizuj popup jeśli już istnieje
        if self.popup_window:
            self.popup_window.update_display(self.remaining_seconds, self.total_seconds)
            self.popup_window.update_pause_button(t("pomodoro.btn_pause"))
        
        self.session_started.emit()
            
    def _play_sound(self, sound_type: str):
        """Odtwarza dźwięk powiadomienia"""
        print(f"[POMODORO] Playing sound: {sound_type}")
        
        from ..core.config import load_settings
        
        settings = load_settings()
        custom_sounds = settings.get('custom_sounds', {})
        
        # Mapowanie typu dźwięku Pomodoro na nazwę z ustawień
        # work_end -> sound_alarm (ważniejszy, kończy pracę)
        # break_end -> sound_notification (mniej ważny, kończy przerwę)
        sound_mapping = {
            'work_end': settings.get('sound_alarm', 'Chord'),
            'break_end': settings.get('sound_notification', 'Ding'),
        }
        
        sound_name = sound_mapping.get(sound_type, 'Beep (domyślny)')
        print(f"[POMODORO] Sound name from settings: {sound_name}")
        
        # Sprawdź czy to custom sound (oznaczony ⭐)
        if sound_name.startswith('⭐ '):
            actual_name = sound_name[2:]  # Usuń ⭐
            if actual_name in custom_sounds:
                file_path = custom_sounds[actual_name]
                if Path(file_path).exists():
                    self.media_player.setSource(QUrl.fromLocalFile(file_path))
                    self.media_player.play()
                    print(f"[POMODORO] ✅ Playing custom sound: {file_path}")
                else:
                    print(f"[POMODORO] ⚠️ WARNING: Custom sound file not found: {file_path}")
                    # Fallback
                    winsound.MessageBeep(winsound.MB_OK)
            return
        
        # System sounds mapping
        system_sounds = {
            'Beep (domyślny)': winsound.MB_OK,
            'Ding': winsound.MB_OK,
            'Chord': winsound.MB_ICONASTERISK,
            'Pop': winsound.MB_OK,
            'Notify': winsound.MB_ICONASTERISK,
            'Asterisk': winsound.MB_ICONASTERISK,
            'Exclamation': winsound.MB_ICONEXCLAMATION,
            'Question': winsound.MB_ICONQUESTION,
            'Critical Stop': winsound.MB_ICONHAND
        }
        
        sound_flag = system_sounds.get(sound_name, winsound.MB_OK)
        
        try:
            winsound.MessageBeep(sound_flag)
            print(f"[POMODORO] ✅ System sound played: {sound_name}")
        except Exception as e:
            print(f"[POMODORO] ❌ ERROR playing sound: {e}")
            # Fallback - prosty beep
            winsound.MessageBeep(winsound.MB_OK)
        
    def _get_random_motivation(self) -> str:
        """Zwraca losowy cytat motywacyjny"""
        key = random.choice(self.motivation_quotes)
        return t(key)
        
    def _apply_theme(self):
        """Aplikuje motyw kolorystyczny"""
        # TODO: Integracja z systemem motywów
        if self.current_theme == "dark":
            self.setStyleSheet("""
                QWidget {
                    background-color: #1e1e1e;
                    color: #ffffff;
                }
                QGroupBox {
                    border: 1px solid #444;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
                QGroupBox::title {
                    color: #ffffff;
                }
            """)
        else:
            self.setStyleSheet("""
                QGroupBox {
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    margin-top: 10px;
                    padding-top: 10px;
                }
            """)
            
    # ========== PUBLIC METHODS ==========
    
    def set_user_data(self, user_data: dict, on_token_refreshed=None):
        """
        Ustawia dane użytkownika i inicjalizuje logikę Pomodoro
        
        Args:
            user_data: Słownik z danymi użytkownika (id, email, access_token, refresh_token, etc.)
            on_token_refreshed: Callback wywoływany po odświeżeniu tokenów (access_token, refresh_token)
        """
        self.user_data = user_data
        self.on_token_refreshed_callback = on_token_refreshed  # Zapisz callback z main.py
        
        print(f"[POMODORO] set_user_data called for user: {user_data.get('id', 'unknown')}")
        
        # Inicjalizuj lokalną bazę danych
        db_path = Path.home() / ".pro_ka_po" / "pomodoro.db"
        self.local_db = PomodoroLocalDatabase(
            db_path=str(db_path),
            user_id=user_data['id']
        )
        print(f"[POMODORO] LocalDatabase initialized: {db_path}")
        
        # Inicjalizuj API client i sync manager jeśli mamy tokeny
        access_token = user_data.get('access_token')
        refresh_token = user_data.get('refresh_token')
        
        if access_token:
            try:
                self.api_client = PomodoroAPIClient(
                    base_url=POMODORO_API_BASE_URL,  # Z config (env variable)
                    auth_token=access_token,
                    refresh_token=refresh_token,
                    on_token_refreshed=self._on_token_refreshed
                )
                print(f"[POMODORO] PomodoroAPIClient initialized with base_url: {POMODORO_API_BASE_URL}")
                
                # Inicjalizuj sync manager
                self.sync_manager = PomodoroSyncManager(
                    local_db=self.local_db,
                    api_client=self.api_client,
                    auto_sync_interval=300  # 5 minut
                )
                
                # Podłącz sygnały synchronizacji
                self.sync_manager.sync_started.connect(self._on_sync_started)
                self.sync_manager.sync_completed.connect(self._on_sync_completed)
                self.sync_manager.conflict_detected.connect(self._on_sync_conflict)
                
                # Uruchom automatyczną synchronizację
                self.sync_manager.start_auto_sync()
                print(f"[POMODORO] SyncManager initialized and auto-sync started")
                
            except Exception as e:
                print(f"[POMODORO] Failed to initialize sync: {e}")
                logger.warning(f"Pomodoro sync initialization failed: {e}")
        else:
            print(f"[POMODORO] No access token - running in offline mode")
        
        # Utwórz ustawienia (TODO: load z localStorage/DB)
        settings = self._load_settings()
        
        print(f"[POMODORO] Settings loaded: work={settings.work_duration}min, breaks={settings.sessions_count}")
        
        # Inicjalizuj manager logiki
        self.pomodoro_logic = PomodoroLogic(
            user_id=user_data['id'],
            settings=settings
        )
        
        print(f"[POMODORO] PomodoroLogic initialized successfully")
        
        # Podłącz callbacki
        self.pomodoro_logic.on_session_end = self._on_logic_session_end
        self.pomodoro_logic.on_cycle_complete = self._on_logic_cycle_complete
        
        # Załaduj statystyki dzienne z bazy danych
        self._load_today_stats()
        
        # Aktualizuj UI
        self._update_counters()
        self._update_display()
        
        print(f"[POMODORO] Initialization complete!")
    
    def _load_settings(self) -> PomodoroSettings:
        """Ładuje ustawienia z lokalnej bazy danych"""
        # Jeśli baza danych nie jest zainicjalizowana, użyj domyślnych wartości
        if not self.local_db:
            logger.warning("[POMODORO] LocalDB not initialized, using default settings")
            return PomodoroSettings()
        
        # Spróbuj załadować zapisane ustawienia
        saved_settings = self.local_db.get_settings()
        
        if saved_settings:
            # Zastosuj zapisane ustawienia do kontrolek UI
            self.work_duration_spin.setValue(saved_settings.get('work_duration', 25))
            self.short_break_spin.setValue(saved_settings.get('short_break_duration', 5))
            self.long_break_spin.setValue(saved_settings.get('long_break_duration', 15))
            self.sessions_count_spin.setValue(saved_settings.get('sessions_count', 4))
            self.auto_breaks_check.setChecked(saved_settings.get('auto_start_breaks', False))
            self.auto_pomodoro_check.setChecked(saved_settings.get('auto_start_pomodoro', False))
            self.sound_work_end_check.setChecked(saved_settings.get('sound_work_end', True))
            self.sound_break_end_check.setChecked(saved_settings.get('sound_break_end', True))
            self.popup_timer_check.setChecked(saved_settings.get('popup_timer', False))
            
            logger.info("[POMODORO] Settings loaded from database")
            return PomodoroSettings.from_dict(saved_settings)
        else:
            # Brak zapisanych ustawień - użyj domyślnych
            logger.info("[POMODORO] No saved settings, using defaults")
            return PomodoroSettings()
    
    def _save_current_settings(self):
        """Zapisuje aktualne ustawienia do bazy danych"""
        if not self.local_db:
            return
        
        settings_dict = {
            'work_duration': self.work_duration_spin.value(),
            'short_break_duration': self.short_break_spin.value(),
            'long_break_duration': self.long_break_spin.value(),
            'sessions_count': self.sessions_count_spin.value(),
            'auto_start_breaks': self.auto_breaks_check.isChecked(),
            'auto_start_pomodoro': self.auto_pomodoro_check.isChecked(),
            'sound_work_end': self.sound_work_end_check.isChecked(),
            'sound_break_end': self.sound_break_end_check.isChecked(),
            'popup_timer': self.popup_timer_check.isChecked(),
        }
        
        self.local_db.save_settings(settings_dict)
        logger.debug("[POMODORO] Settings saved to database")
    
    def _load_today_stats(self):
        """Ładuje statystyki dzienne z bazy danych"""
        if not self.local_db:
            print("[POMODORO] LocalDB not initialized, skipping stats load")
            return
        
        try:
            stats = self.local_db.get_today_stats()
            
            # Aktualizuj liczniki w logice (jeśli istnieją sesje z dzisiaj)
            if self.pomodoro_logic and stats['long_sessions'] > 0:
                self.pomodoro_logic.today_long_sessions = stats['long_sessions']
            
            print(f"[POMODORO] Today stats loaded: {stats}")
            
        except Exception as e:
            print(f"[POMODORO] Failed to load today stats: {e}")
    
    def _on_logic_session_end(self, session_data: SessionData):
        """Callback wywoływany przez logikę po zakończeniu sesji"""
        print(f"Sesja zakończona: {session_data.session_type.value} - {session_data.status.value}")
        
        # Zapisz do bazy danych
        if not self.local_db or not self.user_data or not self.pomodoro_logic:
            print("[POMODORO] ⚠️ LocalDB or user_data not initialized, session not saved")
            return
        
        try:
            # Konwertuj SessionData na słownik dla DB
            session_dict = {
                'id': session_data.id,
                'user_id': self.user_data['id'],
                'topic_id': session_data.topic_id,
                'topic_name': session_data.topic_name if hasattr(session_data, 'topic_name') else '',
                'session_type': session_data.session_type.value,
                'status': session_data.status.value,
                'session_date': session_data.session_date.date().isoformat() if session_data.session_date else '',
                'started_at': session_data.started_at.isoformat() if session_data.started_at else '',
                'ended_at': session_data.ended_at.isoformat() if session_data.ended_at else None,
                'work_duration': self.pomodoro_logic.settings.work_duration,
                'short_break_duration': self.pomodoro_logic.settings.short_break_duration,
                'long_break_duration': self.pomodoro_logic.settings.long_break_duration,
                'actual_work_time': 0,  # Oblicz na podstawie ended_at - started_at
                'actual_break_time': 0,
                'pomodoro_count': session_data.pomodoro_count,
                'notes': session_data.notes,
                'tags': session_data.tags if session_data.tags else [],
                'productivity_rating': session_data.productivity_rating,
                'created_at': session_data.started_at.isoformat() if session_data.started_at else '',
                'updated_at': session_data.ended_at.isoformat() if session_data.ended_at else (session_data.started_at.isoformat() if session_data.started_at else ''),
            }
            
            # Oblicz rzeczywisty czas
            if session_data.ended_at and session_data.started_at:
                duration_seconds = int((session_data.ended_at - session_data.started_at).total_seconds())
                if session_data.session_type == SessionType.WORK:
                    session_dict['actual_work_time'] = duration_seconds
                else:
                    session_dict['actual_break_time'] = duration_seconds
            
            success = self.local_db.save_session(session_dict)
            if success:
                print(f"[POMODORO] ✅ Session saved to LocalDB: {session_data.id}")
                
                # Trigger immediate sync after saving session
                if self.sync_manager:
                    print(f"[POMODORO] Triggering immediate sync...")
                    try:
                        self.sync_manager.sync_all(force=True)
                    except Exception as sync_error:
                        print(f"[POMODORO] Sync failed: {sync_error}")
                        logger.warning(f"Immediate sync failed: {sync_error}")
            else:
                print(f"[POMODORO] ❌ Failed to save session to LocalDB")
                
        except Exception as e:
            print(f"[POMODORO] ERROR saving session: {e}")
    
    def _on_logic_cycle_complete(self):
        """Callback wywoływany po ukończeniu pełnego cyklu (4 pomodoros)"""
        print("🎉 Gratulacje! Ukończono pełny cykl Pomodoro!")
        
        # TODO: Pokaż komunikat gratulacyjny
        # TODO: Zaproponuj długą przerwę
        
    def set_theme(self, theme: str):
        """Ustawia motyw kolorystyczny"""
        self.current_theme = theme
        self._apply_theme()
    
    # ============================================================
    # SYNC HANDLERS
    # ============================================================
    
    def _on_token_refreshed(self, new_access_token: str, new_refresh_token: str):
        """Callback wywoływany gdy tokeny zostaną odświeżone"""
        print(f"[POMODORO] Tokens refreshed")
        
        # Zaktualizuj user_data w pamięci
        if self.user_data:
            self.user_data['access_token'] = new_access_token
            self.user_data['refresh_token'] = new_refresh_token
        
        # Zapisz nowe tokeny do pliku przez callback z main.py
        if self.on_token_refreshed_callback:
            try:
                self.on_token_refreshed_callback(
                    new_access_token,
                    new_refresh_token,
                    self.user_data
                )
                print(f"[POMODORO] Tokens saved to file")
            except Exception as e:
                logger.error(f"[POMODORO] Failed to save tokens: {e}")
                print(f"[POMODORO] Error saving tokens: {e}")
    
    def _on_sync_started(self):
        """Obsłuż rozpoczęcie synchronizacji"""
        print(f"[POMODORO] Sync started")
        # TODO: Opcjonalnie pokaż wskaźnik synchronizacji w UI
    
    def _on_sync_completed(self, success: bool, message: str):
        """Obsłuż zakończenie synchronizacji"""
        if success:
            print(f"[POMODORO] Sync completed successfully: {message}")
            # Odśwież statystyki po synchronizacji
            self._load_today_stats()
            self._update_counters()
        else:
            print(f"[POMODORO] Sync failed: {message}")
            logger.warning(f"Pomodoro sync failed: {message}")
        # TODO: Opcjonalnie pokaż status w UI
    
    def _on_sync_conflict(self, item_type: str, local_data: dict, server_data: dict):
        """Obsłuż wykrycie konfliktu synchronizacji"""
        print(f"[POMODORO] Sync conflict detected: {item_type}")
        print(f"  Local version: {local_data.get('version', 'unknown')}")
        print(f"  Server version: {server_data.get('version', 'unknown')}")
        # Sync manager automatycznie rozwiązuje konflikty ("server wins")
        # To jest tylko informacja dla debugowania
        logger.info(f"Sync conflict for {item_type}: server version accepted")
    
    # ========== ASYSTENT GŁOSOWY ==========
    
    def assistant_open(self):
        """Otwiera widok pomodoro (wywoływane przez asystenta głosowego)"""
        logger.debug("[PomodoroView] Assistant: Opening pomodoro view")
        # Ta metoda jest wywoływana przez handler w MainWindow
        # który już przełączył widok - więc nic nie robimy
        pass
    
    def assistant_start(self):
        """Rozpoczyna sesję pomodoro (wywoływane przez asystenta głosowego)"""
        logger.debug("[PomodoroView] Assistant: Starting pomodoro session")
        
        # Jeśli sesja jest aktywna lub w pauzie, ignoruj
        if self.pomodoro_logic and self.pomodoro_logic.current_session:
            status = self.pomodoro_logic.current_session.status
            if status == SessionStatus.ACTIVE:
                logger.info("[PomodoroView] Session already active, ignoring start command")
                return
            elif status == SessionStatus.PAUSED:
                # Wznowienie zapauzowanej sesji
                self._on_start_pause_clicked()
                return
        
        # Rozpocznij nową sesję
        self._on_start_pause_clicked()
    
    def assistant_pause(self):
        """Pauzuje sesję pomodoro (wywoływane przez asystenta głosowego)"""
        logger.debug("[PomodoroView] Assistant: Pausing pomodoro session")
        
        # Tylko jeśli sesja jest aktywna
        if self.pomodoro_logic and self.pomodoro_logic.current_session:
            status = self.pomodoro_logic.current_session.status
            if status == SessionStatus.ACTIVE:
                self._on_start_pause_clicked()
            else:
                logger.info("[PomodoroView] No active session to pause")
        else:
            logger.info("[PomodoroView] No active session to pause")
    
    def assistant_stop(self):
        """Zatrzymuje sesję pomodoro (wywoływane przez asystenta głosowego)"""
        logger.debug("[PomodoroView] Assistant: Stopping pomodoro session")
        
        # Tylko jeśli sesja istnieje
        if self.pomodoro_logic and self.pomodoro_logic.current_session:
            self._on_stop_clicked()
        else:
            logger.info("[PomodoroView] No active session to stop")


class PomodoroTimerPopup(QWidget):
    """Popup z odliczaniem timera Pomodoro"""
    
    stop_requested = pyqtSignal()
    pause_requested = pyqtSignal()
    
    def __init__(self, session_title: str, session_type: SessionType, parent=None):
        super().__init__(parent)
        self.session_type = session_type
        
        # Tytuł okna
        self.setWindowTitle(f"Pomodoro: {session_title}")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.resize(350, 220)  # Zmniejszone okno
        
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(15, 5, 15, 15)  # Zmniejszone górne marginesy z 10 na 5
        
        # ===== ETYKIETA SESJI =====
        label = QLabel(session_title)
        label_font = QFont()
        label_font.setPointSize(10)  # Zmniejszone z 11 na 10
        label_font.setBold(True)
        label.setFont(label_font)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setFixedHeight(20)  # Zmniejszone z 25 na 20
        label.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(label, 0)  # Stretch factor = 0 (nie rozciąga się)
        
        # ===== DUŻY WYŚWIETLACZ CZASU =====
        self.time_display = QLabel("25:00")
        time_font = QFont()
        time_font.setPointSize(72)  # Zwiększone z 48 na 72
        time_font.setBold(True)
        self.time_display.setFont(time_font)
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_display.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        # Kolor w zależności od typu sesji
        if session_type == SessionType.WORK:
            color = "#FF6B6B"  # Czerwony dla pracy
        else:
            color = "#4ECDC4"  # Cyan dla przerwy
        
        self.time_display.setStyleSheet(f"""
            color: {color};
            padding: 5px;
            background-color: rgba({self._hex_to_rgb(color)}, 0.1);
            border-radius: 10px;
        """)
        layout.addWidget(self.time_display, 1)  # Stretch factor = 1 (wypełnia dostępną przestrzeń)
        
        # ===== PROGRESS BAR =====
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(25)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid #ddd;
                border-radius: 5px;
                background-color: #f0f0f0;
            }}
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.progress_bar)
        
        # ===== PRZYCISKI KONTROLNE =====
        btn_layout = QHBoxLayout()
        
        self.pause_btn = QPushButton(t('pomodoro.btn_pause'))
        self.pause_btn.setFixedHeight(40)
        self.pause_btn.clicked.connect(self._on_pause)
        btn_layout.addWidget(self.pause_btn)
        
        stop_btn = QPushButton(t('pomodoro.btn_stop'))
        stop_btn.setFixedHeight(40)
        stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(stop_btn)
        
        layout.addLayout(btn_layout)
    
    def _hex_to_rgb(self, hex_color: str) -> str:
        """Konwertuje kolor HEX na RGB string"""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"{r}, {g}, {b}"
    
    def update_display(self, remaining_seconds: int, total_seconds: int):
        """Zaktualizuj wyświetlany czas i progressbar"""
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        self.time_display.setText(f"{minutes:02d}:{seconds:02d}")
        
        # Progress bar - pokazuje postęp od 0% do 100%
        if total_seconds > 0:
            elapsed = total_seconds - remaining_seconds
            progress = (elapsed / total_seconds) * 100
            self.progress_bar.setValue(int(progress))
        else:
            self.progress_bar.setValue(0)
    
    def update_pause_button(self, text: str):
        """Zaktualizuj tekst przycisku pauzy"""
        self.pause_btn.setText(text)
    
    def _on_pause(self):
        """Obsłuż pauzę"""
        self.pause_requested.emit()
    
    def _on_stop(self):
        """Obsłuż stop"""
        self.stop_requested.emit()


class SessionTitleDialog(QDialog):
    """Dialog do ustawiania tytułu sesji"""
    
    def __init__(self, current_title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nadaj tytuł sesji")
        self.setModal(True)
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Pole tekstowe
        self.title_input = QLineEdit()
        self.title_input.setText(current_title)
        self.title_input.setPlaceholderText("Wpisz tytuł sesji...")
        self.title_input.selectAll()
        layout.addWidget(QLabel("Tytuł sesji:"))
        layout.addWidget(self.title_input)
        
        # Przyciski
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def get_title(self) -> str:
        """Zwraca wprowadzony tytuł"""
        title = self.title_input.text().strip()
        return title if title else "Ogólna"


class SessionLogsDialog(QDialog):
    """Dialog pokazujący logi sesji Pomodoro"""
    
    def __init__(self, sessions_data: list, parent=None):
        super().__init__(parent)
        self.sessions_data = sessions_data
        self._setup_ui()
        
    def _setup_ui(self):
        """Konfiguruje interfejs dialogu"""
        from PyQt6.QtCore import Qt
        
        self.setWindowTitle("Historia sesji Pomodoro")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        layout = QVBoxLayout(self)
        
        # Informacje podsumowujące
        summary_group = QGroupBox("Podsumowanie")
        summary_layout = QVBoxLayout(summary_group)
        
        total_sessions = len(self.sessions_data)
        completed_sessions = len([s for s in self.sessions_data if s.get('status') == 'completed'])
        total_work_time = sum(s.get('actual_duration', 0) for s in self.sessions_data 
                             if s.get('session_type') == 'work')
        
        summary_layout.addWidget(QLabel(f"📊 Łączna liczba sesji: {total_sessions}"))
        summary_layout.addWidget(QLabel(f"✅ Sesje ukończone: {completed_sessions}"))
        summary_layout.addWidget(QLabel(f"⏱️ Łączny czas pracy: {total_work_time // 60}h {total_work_time % 60}m"))
        
        layout.addWidget(summary_group)
        
        # Tabela z sesjami
        table_group = QGroupBox("Ostatnie sesje")
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels([
            "Data", "Typ sesji", "Temat", "Czas", "Status", "Uwagi"
        ])
        
        # Konfiguracja tabeli
        header = self.table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Data
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Typ
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)           # Temat
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Czas
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Status
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)           # Uwagi
        
        self._populate_table()
        
        table_layout.addWidget(self.table)
        layout.addWidget(table_group)
        
        # Przyciski
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        button_box.rejected.connect(self.close)
        layout.addWidget(button_box)
    
    def _populate_table(self):
        """Wypełnia tabelę danymi sesji"""
        from PyQt6.QtCore import Qt
        from datetime import datetime
        
        self.table.setRowCount(len(self.sessions_data))
        
        for row, session in enumerate(self.sessions_data):
            # Data
            started_at = session.get('started_at', '')
            if started_at:
                try:
                    dt = datetime.fromisoformat(started_at.replace('Z', '+00:00'))
                    date_str = dt.strftime("%Y-%m-%d %H:%M")
                except:
                    date_str = started_at
            else:
                date_str = "N/A"
            
            self.table.setItem(row, 0, QTableWidgetItem(date_str))
            
            # Typ sesji
            session_type = session.get('session_type', 'unknown')
            type_icons = {
                'work': '🍅 Praca',
                'short_break': '☕ Krótka przerwa', 
                'long_break': '🌟 Długa przerwa'
            }
            self.table.setItem(row, 1, QTableWidgetItem(type_icons.get(session_type, session_type)))
            
            # Temat
            topic_name = session.get('topic_name', 'Brak tematu')
            self.table.setItem(row, 2, QTableWidgetItem(topic_name))
            
            # Czas
            actual_duration = session.get('actual_duration', 0)
            planned_duration = session.get('planned_duration', 0)
            time_str = f"{actual_duration // 60}:{actual_duration % 60:02d}"
            if planned_duration and actual_duration != planned_duration:
                time_str += f" / {planned_duration // 60}:{planned_duration % 60:02d}"
            self.table.setItem(row, 3, QTableWidgetItem(time_str))
            
            # Status
            status = session.get('status', 'unknown')
            status_icons = {
                'completed': '✅ Ukończona',
                'interrupted': '⏹️ Przerwana',
                'skipped': '⏭️ Pominięta'
            }
            self.table.setItem(row, 4, QTableWidgetItem(status_icons.get(status, status)))
            
            # Uwagi
            notes = session.get('notes', '') or ''
            self.table.setItem(row, 5, QTableWidgetItem(notes[:50] + '...' if len(notes) > 50 else notes))
