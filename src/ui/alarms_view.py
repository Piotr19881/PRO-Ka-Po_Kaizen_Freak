"""
Alarms View - Widok alarmów i timerów
"""
from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                              QPushButton, QSplitter, QScrollArea,
                              QTimeEdit, QSpinBox, QLineEdit, QCheckBox, QComboBox,
                              QGroupBox, QFormLayout, QMessageBox, QSpacerItem, QSizePolicy,
                              QProgressBar, QFileDialog)
from PyQt6.QtCore import Qt, QTimer, QTime, pyqtSignal, QUrl
from PyQt6.QtGui import QFont
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from datetime import time, datetime
import uuid
from pathlib import Path
from loguru import logger
import winsound

from src.Modules.Alarm_module.alarms_logic import AlarmManager
from src.Modules.Alarm_module.alarm_models import Alarm, Timer, AlarmRecurrence
from ..utils.i18n_manager import I18nManager, t



class TimerPopup(QWidget):
    """Popup z odliczaniem timera"""
    
    stop_requested = pyqtSignal(str)  # timer_id
    pause_requested = pyqtSignal(str)
    
    def __init__(self, timer: Timer, parent=None):
        super().__init__(parent)
        self.timer = timer
        self.is_paused = False
        
        self.setWindowTitle(f"{t('timers.popup_title')}: {timer.label}")
        self.setWindowFlags(Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.resize(400, 250)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Etykieta timera
        label = QLabel(timer.label)
        label_font = QFont()
        label_font.setPointSize(14)
        label_font.setBold(True)
        label.setFont(label_font)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        
        # Duży wyświetlacz czasu - CZERWONE CYFRY 32pt pogrubione
        self.time_display = QLabel("00:00:00")
        time_font = QFont()
        time_font.setPointSize(32)
        time_font.setBold(True)
        self.time_display.setFont(time_font)
        self.time_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.time_display.setStyleSheet("color: #D32F2F;")  # Czerwony kolor
        layout.addWidget(self.time_display)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(timer.duration)
        self.progress_bar.setValue(timer.remaining if timer.remaining else timer.duration)
        self.progress_bar.setTextVisible(False)
        self.progress_bar.setFixedHeight(20)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #ccc;
                border-radius: 5px;
                background-color: #f0f0f0;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        layout.addWidget(self.progress_bar)
        
        # Przyciski kontrolne
        btn_layout = QHBoxLayout()
        
        self.pause_btn = QPushButton(t('timers.pause'))
        self.pause_btn.setFixedHeight(35)
        self.pause_btn.clicked.connect(self._on_pause)
        btn_layout.addWidget(self.pause_btn)
        
        stop_btn = QPushButton(t('timers.stop'))
        stop_btn.setFixedHeight(35)
        stop_btn.clicked.connect(self._on_stop)
        btn_layout.addWidget(stop_btn)
        
        layout.addLayout(btn_layout)
        
        self.update_display()
    
    def update_display(self):
        """Zaktualizuj wyświetlany czas i progressbar"""
        if self.timer.remaining is not None:
            hours = self.timer.remaining // 3600
            minutes = (self.timer.remaining % 3600) // 60
            seconds = self.timer.remaining % 60
            self.time_display.setText(f"{hours:02d}:{minutes:02d}:{seconds:02d}")
            
            # Aktualizuj progressbar (odwrotnie - maleje gdy czas ucieka)
            self.progress_bar.setValue(self.timer.remaining)
            
            # Zmień kolor progressbara gdy mało czasu
            if self.timer.remaining <= 10:
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid #ccc;
                        border-radius: 5px;
                        background-color: #f0f0f0;
                    }
                    QProgressBar::chunk {
                        background-color: #F44336;
                        border-radius: 3px;
                    }
                """)
            elif self.timer.remaining <= 60:
                self.progress_bar.setStyleSheet("""
                    QProgressBar {
                        border: 2px solid #ccc;
                        border-radius: 5px;
                        background-color: #f0f0f0;
                    }
                    QProgressBar::chunk {
                        background-color: #FF9800;
                        border-radius: 3px;
                    }
                """)
    
    def _on_pause(self):
        """Obsłuż pauzę"""
        self.is_paused = not self.is_paused
        if self.is_paused:
            self.pause_btn.setText(t('timers.resume'))
        else:
            self.pause_btn.setText(t('timers.pause'))
        self.pause_requested.emit(self.timer.id)
    
    def _on_stop(self):
        """Obsłuż stop"""
        self.stop_requested.emit(self.timer.id)
        self.close()


class AlarmsView(QWidget):
    """Widok alarmów i timerów"""
    
    def __init__(self, i18n_manager: I18nManager, data_dir: Path, parent=None):
        super().__init__(parent)
        self.i18n = i18n_manager
        self.alarm_manager = AlarmManager(data_dir)
        
        # Media player dla dźwięków
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        
        # Niestandardowe dźwięki dla alarmów i timerów
        self.custom_alarm_sound: str | None = None
        self.custom_timer_sound: str | None = None
        
        # Timery Qt
        self.check_timer = QTimer()
        self.check_timer.timeout.connect(self._check_alarms_and_timers)
        self.check_timer.start(1000)  # Co sekundę
        
        # Otwarte popupy timerów
        self.timer_popups: dict[str, TimerPopup] = {}
        
        self._init_ui()
        self._load_data()
    
    def set_user_data(self, user_data: dict, on_token_refreshed=None):
        """
        Ustaw dane użytkownika i włącz synchronizację.
        
        Args:
            user_data: Słownik z danymi użytkownika (id/user_id, email, access_token, refresh_token)
            on_token_refreshed: Callback wywoływany po odświeżeniu tokena: (new_access_token, new_refresh_token) -> None
        """
        # user_id może być zapisany jako 'id' lub 'user_id'
        user_id = user_data.get('user_id') or user_data.get('id')
        access_token = user_data.get('access_token')
        refresh_token = user_data.get('refresh_token')
        
        if user_id and access_token:
            # Odtwórz AlarmManager z włączoną synchronizacją
            data_dir = self.alarm_manager.alarms_file.parent
            
            # Przenieś istniejące dane
            old_alarms = self.alarm_manager.alarms.copy()
            old_timers = self.alarm_manager.timers.copy()
            
            # Stwórz nowy AlarmManager z synchronizacją
            self.alarm_manager = AlarmManager(
                data_dir=data_dir,
                user_id=user_id,
                api_base_url="http://127.0.0.1:8000",  # TODO: z configu
                auth_token=access_token,
                refresh_token=refresh_token,
                on_token_refreshed=on_token_refreshed,
                enable_sync=True
            )
            
            # Przywróć dane (zostaną automatycznie zsynchronizowane)
            self.alarm_manager.alarms = old_alarms
            self.alarm_manager.timers = old_timers
            
            # Ustaw callbacks dla real-time updates
            self.alarm_manager.set_ui_callbacks(
                on_alarm_changed=self._on_alarm_updated,
                on_timer_changed=self._on_timer_updated
            )
            
            logger.info(f"Sync enabled for user: {user_data.get('email')}")
        else:
            logger.warning("Cannot enable sync: missing user_id or access_token")
    
    def _on_alarm_updated(self, alarm: Alarm):
        """Callback wywoływany gdy alarm zostanie zaktualizowany przez WebSocket"""
        logger.info(f"Alarm updated via WebSocket: {alarm.label}")
        self._load_data()  # Odśwież UI
    
    def _on_timer_updated(self, timer: Timer):
        """Callback wywoływany gdy timer zostanie zaktualizowany przez WebSocket"""
        logger.info(f"Timer updated via WebSocket: {timer.label}")
        self._load_data()  # Odśwież UI
    
    def showEvent(self, a0):
        """
        Wywołane gdy widok jest pokazywany.
        Odświeżamy dane z serwera (serwer = źródło prawdy).
        """
        super().showEvent(a0)
        
        # Odśwież dane z serwera przy każdym pokazaniu widoku
        if hasattr(self, 'alarm_manager'):
            logger.info("View shown - refreshing data from server...")
            self.alarm_manager.refresh_from_server()
            self._load_data()  # Odśwież UI
    
    def _init_ui(self):
        """Inicjalizuj interfejs"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Splitter poziomy: Alarmy (lewo) | Timery (prawo)
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === SEKCJA ALARMÓW ===
        alarms_widget = self._create_alarms_section()
        splitter.addWidget(alarms_widget)
        
        # === SEKCJA TIMERÓW ===
        timers_widget = self._create_timers_section()
        splitter.addWidget(timers_widget)
        
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)
        
        layout.addWidget(splitter)
    
    def _create_alarms_section(self) -> QWidget:
        """Utwórz sekcję alarmów"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Nagłówek
        header = QLabel(t('alarms.header'))
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Kontener na listę alarmów
        self.alarms_container = QWidget()
        self.alarms_layout = QVBoxLayout(self.alarms_container)
        self.alarms_layout.setContentsMargins(0, 0, 0, 0)
        self.alarms_layout.setSpacing(2)
        
        # ScrollArea dla alarmów
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.alarms_container)
        layout.addWidget(scroll, 3)
        
        # Formularz dodawania alarmu
        form_group = QGroupBox(t('alarms.add_new'))
        form_layout = QFormLayout(form_group)
        
        self.alarm_time_edit = QTimeEdit()
        self.alarm_time_edit.setDisplayFormat("HH:mm")
        self.alarm_time_edit.setTime(QTime.currentTime())
        form_layout.addRow(t('alarms.time') + ":", self.alarm_time_edit)
        
        self.alarm_label_edit = QLineEdit()
        self.alarm_label_edit.setPlaceholderText(t('alarms.label_placeholder'))
        form_layout.addRow(t('alarms.label') + ":", self.alarm_label_edit)
        
        self.alarm_recurrence_combo = QComboBox()
        self.alarm_recurrence_combo.addItems([
            t('alarms.recurrence.once'),
            t('alarms.recurrence.daily'),
            t('alarms.recurrence.weekdays'),
            t('alarms.recurrence.weekends'),
            t('alarms.recurrence.custom')
        ])
        self.alarm_recurrence_combo.currentIndexChanged.connect(self._on_recurrence_changed)
        form_layout.addRow(t('alarms.recurrence') + ":", self.alarm_recurrence_combo)
        
        # Widget wyboru dni tygodnia (ukryty domyślnie)
        self.days_widget = QWidget()
        days_layout = QHBoxLayout(self.days_widget)
        days_layout.setContentsMargins(0, 0, 0, 0)
        
        self.day_checkboxes = []
        days_names = ['Pn', 'Wt', 'Śr', 'Cz', 'Pt', 'So', 'Nd']
        for i, day_name in enumerate(days_names):
            checkbox = QCheckBox(day_name)
            checkbox.setProperty("day_index", i)
            self.day_checkboxes.append(checkbox)
            days_layout.addWidget(checkbox)
        
        self.days_widget.setVisible(False)
        form_layout.addRow("", self.days_widget)
        
        checkboxes_layout = QHBoxLayout()
        self.alarm_sound_check = QCheckBox(t('alarms.play_sound'))
        self.alarm_sound_check.setChecked(True)
        checkboxes_layout.addWidget(self.alarm_sound_check)
        
        self.alarm_popup_check = QCheckBox(t('alarms.show_popup'))
        self.alarm_popup_check.setChecked(True)
        checkboxes_layout.addWidget(self.alarm_popup_check)
        
        form_layout.addRow(t('alarms.options') + ":", checkboxes_layout)
        
        # Przycisk wyboru niestandardowego dźwięku
        self.alarm_custom_sound_btn = QPushButton(t('alarms.custom_sound'))
        self.alarm_custom_sound_btn.clicked.connect(self._select_alarm_custom_sound)
        form_layout.addRow("", self.alarm_custom_sound_btn)
        
        add_alarm_btn = QPushButton(t('alarms.add_button'))
        add_alarm_btn.clicked.connect(self._add_alarm)
        form_layout.addRow("", add_alarm_btn)
        
        layout.addWidget(form_group, 2)
        
        return widget
    
    def _create_timers_section(self) -> QWidget:
        """Utwórz sekcję timerów"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Nagłówek
        header = QLabel(t('timers.header'))
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Kontener na listę timerów
        self.timers_container = QWidget()
        self.timers_layout = QVBoxLayout(self.timers_container)
        self.timers_layout.setContentsMargins(0, 0, 0, 0)
        self.timers_layout.setSpacing(2)
        
        # ScrollArea dla timerów
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.timers_container)
        layout.addWidget(scroll, 3)
        
        # Formularz dodawania timera
        form_group = QGroupBox(t('timers.add_new'))
        form_layout = QFormLayout(form_group)
        
        duration_layout = QHBoxLayout()
        
        self.timer_hours_spin = QSpinBox()
        self.timer_hours_spin.setRange(0, 23)
        self.timer_hours_spin.setSuffix(" " + t('timers.hours'))
        duration_layout.addWidget(self.timer_hours_spin)
        
        self.timer_minutes_spin = QSpinBox()
        self.timer_minutes_spin.setRange(0, 59)
        self.timer_minutes_spin.setValue(5)
        self.timer_minutes_spin.setSuffix(" " + t('timers.minutes'))
        duration_layout.addWidget(self.timer_minutes_spin)
        
        self.timer_seconds_spin = QSpinBox()
        self.timer_seconds_spin.setRange(0, 59)
        self.timer_seconds_spin.setSuffix(" " + t('timers.seconds'))
        duration_layout.addWidget(self.timer_seconds_spin)
        
        form_layout.addRow(t('timers.duration') + ":", duration_layout)
        
        self.timer_label_edit = QLineEdit()
        self.timer_label_edit.setPlaceholderText(t('timers.label_placeholder'))
        form_layout.addRow(t('timers.label') + ":", self.timer_label_edit)
        
        checkboxes_layout = QHBoxLayout()
        self.timer_sound_check = QCheckBox(t('timers.play_sound'))
        self.timer_sound_check.setChecked(True)
        checkboxes_layout.addWidget(self.timer_sound_check)
        
        self.timer_popup_check = QCheckBox(t('timers.show_popup'))
        self.timer_popup_check.setChecked(True)
        checkboxes_layout.addWidget(self.timer_popup_check)
        
        self.timer_repeat_check = QCheckBox(t('timers.repeat'))
        self.timer_repeat_check.setChecked(False)
        checkboxes_layout.addWidget(self.timer_repeat_check)
        
        form_layout.addRow(t('timers.options') + ":", checkboxes_layout)
        
        # Przycisk wyboru niestandardowego dźwięku
        self.timer_custom_sound_btn = QPushButton(t('timers.custom_sound'))
        self.timer_custom_sound_btn.clicked.connect(self._select_timer_custom_sound)
        form_layout.addRow("", self.timer_custom_sound_btn)
        
        add_timer_btn = QPushButton(t('timers.add_button'))
        add_timer_btn.clicked.connect(self._add_timer)
        form_layout.addRow("", add_timer_btn)
        
        layout.addWidget(form_group, 2)
        
        return widget
    
    def _load_data(self):
        """Załaduj alarmy i timery"""
        self._refresh_alarms_list()
        self._refresh_timers_list()
    
    def _select_alarm_custom_sound(self):
        """Wybierz niestandardowy dźwięk dla alarmu"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t('alarms.select_sound_file'),
            "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a);;All Files (*.*)"
        )
        
        if file_path:
            self.custom_alarm_sound = file_path
            filename = Path(file_path).name
            # Zaktualizuj tekst przycisku
            self.alarm_custom_sound_btn.setText(
                t('alarms.custom_sound_selected').replace('{filename}', filename)
            )
            logger.info(f"Selected custom alarm sound: {file_path}")
    
    def _select_timer_custom_sound(self):
        """Wybierz niestandardowy dźwięk dla timera"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t('alarms.select_sound_file'),
            "",
            "Audio Files (*.wav *.mp3 *.ogg *.flac *.m4a);;All Files (*.*)"
        )
        
        if file_path:
            self.custom_timer_sound = file_path
            filename = Path(file_path).name
            # Zaktualizuj tekst przycisku
            self.timer_custom_sound_btn.setText(
                t('timers.custom_sound_selected').replace('{filename}', filename)
            )
            logger.info(f"Selected custom timer sound: {file_path}")
    
    def _on_recurrence_changed(self, index: int):
        """Obsługa zmiany cykliczności alarmu"""
        # Pokaż wybór dni tylko dla opcji "Niestandardowo" (index 4)
        if index == 4:  # CUSTOM
            self.days_widget.setVisible(True)
            # Odznacz wszystkie dni
            for checkbox in self.day_checkboxes:
                checkbox.setChecked(False)
        else:
            self.days_widget.setVisible(False)
            
            # Automatycznie zaznacz odpowiednie dni dla predefiniowanych opcji
            if index == 2:  # WEEKDAYS (Pn-Pt)
                for i, checkbox in enumerate(self.day_checkboxes):
                    checkbox.setChecked(i < 5)  # 0-4 = Pn-Pt
            elif index == 3:  # WEEKENDS (So-Nd)
                for i, checkbox in enumerate(self.day_checkboxes):
                    checkbox.setChecked(i >= 5)  # 5-6 = So-Nd
    
    def _refresh_alarms_list(self):
        """Odśwież listę alarmów"""
        # Wyczyść obecny layout
        while self.alarms_layout.count():
            child = self.alarms_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Dodaj każdy alarm jako widget z przyciskami
        for alarm in self.alarm_manager.alarms:
            alarm_widget = self._create_alarm_item(alarm)
            self.alarms_layout.addWidget(alarm_widget)
        
        # Dodaj spacer na końcu
        self.alarms_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
    
    def _create_alarm_item(self, alarm: Alarm) -> QWidget:
        """Utwórz widget dla pojedynczego alarmu z przyciskami"""
        item_widget = QWidget()
        item_widget.setObjectName("alarmItem")
        
        # Ustaw klasy CSS zamiast hard-kodowanych kolorów
        if alarm.enabled:
            item_widget.setProperty("active", "true")
        else:
            item_widget.setProperty("active", "false")
        
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Informacje o alarmie
        info_layout = QVBoxLayout()
        
        # Czas i status
        time_str = alarm.time.strftime("%H:%M")
        status_icon = "✓" if alarm.enabled else "✗"
        time_label = QLabel(f"{status_icon} {time_str}")
        time_font = QFont()
        time_font.setPointSize(14)
        time_font.setBold(True)
        time_label.setFont(time_font)
        info_layout.addWidget(time_label)
        
        # Etykieta i cykliczność
        rec_map = {
            AlarmRecurrence.ONCE: t('alarms.recurrence.once'),
            AlarmRecurrence.DAILY: t('alarms.recurrence.daily'),
            AlarmRecurrence.WEEKDAYS: t('alarms.recurrence.weekdays'),
            AlarmRecurrence.WEEKENDS: t('alarms.recurrence.weekends'),
            AlarmRecurrence.CUSTOM: t('alarms.recurrence.custom')
        }
        recurrence = rec_map.get(alarm.recurrence, "")
        detail_label = QLabel(f"{alarm.label} ({recurrence})")
        info_layout.addWidget(detail_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Przyciski akcji
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        # Przycisk włącz/wyłącz
        toggle_btn = QPushButton(t('alarms.disable') if alarm.enabled else t('alarms.enable'))
        toggle_btn.setMaximumWidth(100)
        toggle_btn.clicked.connect(lambda: self._toggle_alarm_state(alarm.id))
        btn_layout.addWidget(toggle_btn)
        
        # Przycisk edytuj
        edit_btn = QPushButton(t('alarms.edit'))
        edit_btn.setMaximumWidth(80)
        edit_btn.clicked.connect(lambda: self._edit_alarm_item(alarm.id))
        btn_layout.addWidget(edit_btn)
        
        # Przycisk usuń
        delete_btn = QPushButton(t('alarms.delete'))
        delete_btn.setMaximumWidth(80)
        delete_btn.setObjectName("deleteButton")
        delete_btn.clicked.connect(lambda: self._delete_alarm(alarm.id))
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        
        return item_widget
    
    def _refresh_timers_list(self):
        """Odśwież listę timerów"""
        # Wyczyść obecny layout
        while self.timers_layout.count():
            child = self.timers_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Dodaj każdy timer jako widget z przyciskami
        for timer in self.alarm_manager.timers:
            timer_widget = self._create_timer_item(timer)
            self.timers_layout.addWidget(timer_widget)
        
        # Dodaj spacer na końcu
        self.timers_layout.addItem(QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding))
    
    def _create_timer_item(self, timer: Timer) -> QWidget:
        """Utwórz widget dla pojedynczego timera z przyciskami"""
        item_widget = QWidget()
        item_widget.setObjectName("timerItem")
        
        # Ustaw klasy CSS zamiast hard-kodowanych kolorów
        if timer.enabled:
            item_widget.setProperty("active", "true")
        else:
            item_widget.setProperty("active", "false")
        
        layout = QHBoxLayout(item_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Informacje o timerze
        info_layout = QVBoxLayout()
        
        # Czas i status
        status_icon = "▶" if timer.enabled else "⏸"
        
        # Formatuj czas
        if timer.enabled and timer.remaining is not None:
            hours = timer.remaining // 3600
            minutes = (timer.remaining % 3600) // 60
            seconds = timer.remaining % 60
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        else:
            hours = timer.duration // 3600
            minutes = (timer.duration % 3600) // 60
            seconds = timer.duration % 60
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
        time_label = QLabel(f"{status_icon} {time_str}")
        time_font = QFont()
        time_font.setPointSize(14)
        time_font.setBold(True)
        time_label.setFont(time_font)
        info_layout.addWidget(time_label)
        
        # Etykieta i opcje
        repeat_indicator = "🔁 " if timer.repeat else ""
        detail_label = QLabel(f"{repeat_indicator}{timer.label}")
        info_layout.addWidget(detail_label)
        
        layout.addLayout(info_layout, stretch=1)
        
        # Przyciski akcji
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        # Przycisk włącz/wyłącz
        toggle_btn = QPushButton(t('timers.disable') if timer.enabled else t('timers.enable'))
        toggle_btn.setMaximumWidth(100)
        toggle_btn.clicked.connect(lambda: self._toggle_timer_state(timer.id))
        btn_layout.addWidget(toggle_btn)
        
        # Przycisk otwórz okno (tylko dla aktywnych)
        if timer.enabled:
            popup_btn = QPushButton(t('timers.open_popup'))
            popup_btn.setMaximumWidth(100)
            popup_btn.clicked.connect(lambda: self._open_timer_popup(timer.id))
            btn_layout.addWidget(popup_btn)
        
        # Przycisk edytuj
        edit_btn = QPushButton(t('timers.edit'))
        edit_btn.setMaximumWidth(80)
        edit_btn.clicked.connect(lambda: self._edit_timer_item(timer.id))
        btn_layout.addWidget(edit_btn)
        
        # Przycisk usuń
        delete_btn = QPushButton(t('timers.delete'))
        delete_btn.setMaximumWidth(80)
        delete_btn.setObjectName("deleteButton")
        delete_btn.clicked.connect(lambda: self._delete_timer(timer.id))
        btn_layout.addWidget(delete_btn)
        
        layout.addLayout(btn_layout)
        
        return item_widget
    
    def _add_alarm(self):
        """Dodaj nowy alarm"""
        q_time = self.alarm_time_edit.time()
        alarm_time = time(q_time.hour(), q_time.minute())
        label = self.alarm_label_edit.text().strip()
        
        if not label:
            QMessageBox.warning(self, t('common.error'), t('alarms.error_no_label'))
            return
        
        # Mapowanie cykliczności
        rec_index = self.alarm_recurrence_combo.currentIndex()
        rec_map = [
            AlarmRecurrence.ONCE,
            AlarmRecurrence.DAILY,
            AlarmRecurrence.WEEKDAYS,
            AlarmRecurrence.WEEKENDS,
            AlarmRecurrence.CUSTOM
        ]
        
        # Zbierz wybrane dni dla opcji niestandardowej lub predefiniowanych
        selected_days = []
        if rec_index == 4:  # CUSTOM
            selected_days = [i for i, cb in enumerate(self.day_checkboxes) if cb.isChecked()]
            if not selected_days:
                QMessageBox.warning(self, t('common.error'), t('alarms.error_no_days'))
                return
        elif rec_index == 2:  # WEEKDAYS
            selected_days = [0, 1, 2, 3, 4]  # Pn-Pt
        elif rec_index == 3:  # WEEKENDS
            selected_days = [5, 6]  # So-Nd
        elif rec_index == 1:  # DAILY
            selected_days = [0, 1, 2, 3, 4, 5, 6]  # Wszystkie dni
        # ONCE nie ma dni (selected_days pozostaje puste)
        
        alarm = Alarm(
            id=str(uuid.uuid4()),
            time=alarm_time,
            label=label,
            enabled=True,
            recurrence=rec_map[rec_index],
            days=selected_days,
            play_sound=self.alarm_sound_check.isChecked(),
            show_popup=self.alarm_popup_check.isChecked(),
            custom_sound=self.custom_alarm_sound
        )
        
        if self.alarm_manager.add_alarm(alarm):
            self._refresh_alarms_list()
            self.alarm_label_edit.clear()
            # Resetuj niestandardowy dźwięk
            self.custom_alarm_sound = None
            self.alarm_custom_sound_btn.setText(t('alarms.custom_sound'))
            logger.info(f"Added alarm: {label} at {alarm_time}")
        else:
            QMessageBox.critical(self, t('common.error'), t('alarms.error_add_failed'))
    
    def _add_timer(self):
        """Dodaj nowy timer"""
        hours = self.timer_hours_spin.value()
        minutes = self.timer_minutes_spin.value()
        seconds = self.timer_seconds_spin.value()
        duration = hours * 3600 + minutes * 60 + seconds
        
        label = self.timer_label_edit.text().strip()
        
        if duration == 0:
            QMessageBox.warning(self, t('common.error'), t('timers.error_no_duration'))
            return
        
        if not label:
            QMessageBox.warning(self, t('common.error'), t('timers.error_no_label'))
            return
        
        timer = Timer(
            id=str(uuid.uuid4()),
            duration=duration,
            label=label,
            enabled=False,
            play_sound=self.timer_sound_check.isChecked(),
            show_popup=self.timer_popup_check.isChecked(),
            repeat=self.timer_repeat_check.isChecked(),
            custom_sound=self.custom_timer_sound
        )
        
        if self.alarm_manager.add_timer(timer):
            self._refresh_timers_list()
            self.timer_label_edit.clear()
            # Resetuj niestandardowy dźwięk
            self.custom_timer_sound = None
            self.timer_custom_sound_btn.setText(t('timers.custom_sound'))
            logger.info(f"Added timer: {label} ({duration}s)")
        else:
            QMessageBox.critical(self, t('common.error'), t('timers.error_add_failed'))
    
    # === AKCJE DLA ALARMÓW ===
    
    def _toggle_alarm_state(self, alarm_id: str):
        """Przełącz stan alarmu (włącz/wyłącz)"""
        self.alarm_manager.toggle_alarm(alarm_id)
        self._refresh_alarms_list()
        logger.info(f"Toggled alarm: {alarm_id}")
    
    def _edit_alarm_item(self, alarm_id: str):
        """Edytuj alarm"""
        # TODO: Implementacja okna dialogowego edycji alarmu
        logger.info(f"Edit alarm requested: {alarm_id}")
        QMessageBox.information(self, t('alarms.edit'), "Funkcja edycji będzie dostępna wkrótce")
    
    def _delete_alarm(self, alarm_id: str):
        """Usuń alarm z potwierdzeniem"""
        reply = QMessageBox.question(
            self, 
            t('alarms.delete_title'),
            t('alarms.confirm_delete'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            if self.alarm_manager.delete_alarm(alarm_id):
                self._refresh_alarms_list()
                logger.info(f"Deleted alarm: {alarm_id}")
            else:
                QMessageBox.critical(self, t('common.error'), "Nie udało się usunąć alarmu")
    
    # === AKCJE DLA TIMERÓW ===
    
    def _toggle_timer_state(self, timer_id: str):
        """Przełącz stan timera (uruchom/zatrzymaj)"""
        # Znajdź timer
        timer = next((t for t in self.alarm_manager.timers if t.id == timer_id), None)
        if not timer:
            return
        
        if timer.enabled:
            # Zatrzymaj
            self.alarm_manager.stop_timer(timer_id)
            if timer_id in self.timer_popups:
                self.timer_popups[timer_id].close()
                del self.timer_popups[timer_id]
        else:
            # Uruchom
            self.alarm_manager.start_timer(timer_id)
            
            # Pokaż popup jeśli włączone
            if timer.show_popup:
                popup = TimerPopup(timer, self)
                popup.stop_requested.connect(self._stop_timer_from_popup)
                popup.show()
                self.timer_popups[timer_id] = popup
        
        self._refresh_timers_list()
        logger.info(f"Toggled timer: {timer_id}")
    
    def _open_timer_popup(self, timer_id: str):
        """Otwórz okno odliczania dla aktywnego timera"""
        timer = next((t for t in self.alarm_manager.timers if t.id == timer_id), None)
        if not timer or not timer.enabled:
            return
        
        # Jeśli popup już istnieje, pokaż go
        if timer_id in self.timer_popups:
            self.timer_popups[timer_id].show()
            self.timer_popups[timer_id].activateWindow()
        else:
            # Utwórz nowy popup
            popup = TimerPopup(timer, self)
            popup.stop_requested.connect(self._stop_timer_from_popup)
            popup.show()
            self.timer_popups[timer_id] = popup
        
        logger.info(f"Opened timer popup: {timer_id}")
    
    def _edit_timer_item(self, timer_id: str):
        """Edytuj timer"""
        # TODO: Implementacja okna dialogowego edycji timera
        logger.info(f"Edit timer requested: {timer_id}")
        QMessageBox.information(self, t('timers.edit'), "Funkcja edycji będzie dostępna wkrótce")
    
    def _delete_timer(self, timer_id: str):
        """Usuń timer z potwierdzeniem"""
        reply = QMessageBox.question(
            self, 
            t('timers.delete_title'),
            t('timers.confirm_delete'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Zamknij popup jeśli istnieje
            if timer_id in self.timer_popups:
                self.timer_popups[timer_id].close()
                del self.timer_popups[timer_id]
            
            if self.alarm_manager.delete_timer(timer_id):
                self._refresh_timers_list()
                logger.info(f"Deleted timer: {timer_id}")
            else:
                QMessageBox.critical(self, t('common.error'), "Nie udało się usunąć timera")
    
    def _toggle_timer(self, item):
        """Stara metoda - już nie używana"""
        pass
    
    def _stop_timer_from_popup(self, timer_id: str):
        """Zatrzymaj timer z popupu"""
        self.alarm_manager.stop_timer(timer_id)
        if timer_id in self.timer_popups:
            del self.timer_popups[timer_id]
        self._refresh_timers_list()
    
    def _check_alarms_and_timers(self):
        """Sprawdź alarmy i timery (wywoływane co sekundę)"""
        now = datetime.now()
        
        # Sprawdź alarmy
        for alarm in self.alarm_manager.get_active_alarms():
            if self._should_trigger_alarm(alarm, now):
                self._trigger_alarm(alarm)
        
        # Zaktualizuj timery
        for timer in self.alarm_manager.get_active_timers():
            if timer.started_at and timer.remaining is not None:
                elapsed = (now - timer.started_at).total_seconds()
                remaining = max(0, timer.duration - int(elapsed))
                
                self.alarm_manager.update_timer_remaining(timer.id, remaining)
                
                # Zaktualizuj popup
                if timer.id in self.timer_popups:
                    self.timer_popups[timer.id].update_display()
                
                # Sprawdź czy koniec
                if remaining == 0:
                    self._trigger_timer(timer)
        
        self._refresh_timers_list()
    
    def _should_trigger_alarm(self, alarm: Alarm, now: datetime) -> bool:
        """Sprawdź czy alarm powinien zostać wywołany"""
        # Sprawdź czy godzina i minuta się zgadzają
        if not (now.hour == alarm.time.hour and now.minute == alarm.time.minute and now.second == 0):
            return False
        
        # Sprawdź cykliczność
        if alarm.recurrence == AlarmRecurrence.ONCE:
            # Jednorazowy - zawsze się uruchamia (potem zostanie wyłączony)
            return True
        
        elif alarm.recurrence == AlarmRecurrence.DAILY:
            # Codziennie - zawsze się uruchamia
            return True
        
        elif alarm.recurrence == AlarmRecurrence.WEEKDAYS:
            # Dni robocze (Pn-Pt = 0-4)
            return now.weekday() in [0, 1, 2, 3, 4]
        
        elif alarm.recurrence == AlarmRecurrence.WEEKENDS:
            # Weekendy (So-Nd = 5-6)
            return now.weekday() in [5, 6]
        
        elif alarm.recurrence == AlarmRecurrence.CUSTOM:
            # Niestandardowo - sprawdź zapisane dni
            return now.weekday() in alarm.days
        
        return False
    
    def _trigger_alarm(self, alarm: Alarm):
        """Wywołaj alarm"""
        logger.info(f"Triggering alarm: {alarm.label}")
        
        if alarm.show_popup:
            QMessageBox.information(self, t('alarms.triggered'), f"{alarm.label}")
        
        if alarm.play_sound:
            # Użyj niestandardowego dźwięku jeśli dostępny
            if alarm.custom_sound and Path(alarm.custom_sound).exists():
                self.media_player.setSource(QUrl.fromLocalFile(alarm.custom_sound))
                self.media_player.play()
                logger.info(f"Playing custom alarm sound: {alarm.custom_sound}")
            else:
                self._play_alarm_sound()
        
        # Jeśli jednorazowy, wyłącz
        if alarm.recurrence == AlarmRecurrence.ONCE:
            self.alarm_manager.toggle_alarm(alarm.id)
            self._refresh_alarms_list()
    
    def _trigger_timer(self, timer: Timer):
        """Wywołaj timer"""
        logger.info(f"Timer finished: {timer.label}")
        
        if timer.show_popup:
            QMessageBox.information(self, t('timers.popup_title'), f"{t('timers.finished')}:\n{timer.label}")
        
        if timer.play_sound:
            # Użyj niestandardowego dźwięku jeśli dostępny
            if timer.custom_sound and Path(timer.custom_sound).exists():
                self.media_player.setSource(QUrl.fromLocalFile(timer.custom_sound))
                self.media_player.play()
                logger.info(f"Playing custom timer sound: {timer.custom_sound}")
            else:
                self._play_notification_sound()
        
        # Zamknij popup
        if timer.id in self.timer_popups:
            self.timer_popups[timer.id].close()
            del self.timer_popups[timer.id]
        
        self._refresh_timers_list()
    
    def _play_alarm_sound(self):
        """Odtwórz dźwięk alarmu z ustawień"""
        from ..core.config import load_settings
        settings = load_settings()
        
        if not settings.get('enable_sound', True):
            return
        
        sound_name = settings.get('sound_alarm', 'Beep (domyślny)')
        self._play_sound_from_settings(sound_name)
    
    def _play_notification_sound(self):
        """Odtwórz dźwięk powiadomienia z ustawień"""
        from ..core.config import load_settings
        settings = load_settings()
        
        if not settings.get('enable_sound', True):
            return
        
        sound_name = settings.get('sound_notification', 'Beep (domyślny)')
        self._play_sound_from_settings(sound_name)
    
    def _play_sound_from_settings(self, sound_name: str):
        """Odtwórz dźwięk na podstawie nazwy z ustawień"""
        from ..core.config import load_settings
        
        settings = load_settings()
        custom_sounds = settings.get('custom_sounds', {})
        
        # Sprawdź czy to custom sound (oznaczony ⭐)
        if sound_name.startswith('⭐ '):
            actual_name = sound_name[2:]  # Usuń ⭐ 
            if actual_name in custom_sounds:
                file_path = custom_sounds[actual_name]
                if Path(file_path).exists():
                    self.media_player.setSource(QUrl.fromLocalFile(file_path))
                    self.media_player.play()
                    logger.info(f"Playing custom sound: {file_path}")
                else:
                    logger.warning(f"Custom sound file not found: {file_path}")
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
        
        if sound_name in system_sounds:
            try:
                winsound.MessageBeep(system_sounds[sound_name])
                logger.info(f"Playing system sound: {sound_name}")
            except Exception as e:
                logger.error(f"Failed to play system sound: {e}")
    
    def update_translations(self):
        """Odśwież tłumaczenia po zmianie języka"""
        # Odśwież listy (włącznie z przetłumaczonymi tekstami cykliczności)
        self._refresh_alarms_list()
        self._refresh_timers_list()
        
        # TODO: W przyszłości można dodać odświeżanie etykiet i przycisków
        # jeśli będą one przechowywane jako atrybuty
        logger.info("Alarms view translations updated")
