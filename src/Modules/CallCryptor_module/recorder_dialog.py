"""
Recorder Dialog - Dialog nagrywania rozmów
==========================================

Dialog umożliwiający nagrywanie rozmów z mikrofonu:
- Wybór urządzenia audio
- Kontrola nagrywania (start/pause/stop)
- Wizualizacja poziomu głośności
- Timer nagrywania
- Automatyczne zapisywanie do folderu Nagrania
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QProgressBar,
    QFrame, QMessageBox, QWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from loguru import logger
from pathlib import Path
from datetime import datetime, timedelta
from typing import Optional

from ...utils.i18n_manager import t
from ...utils.theme_manager import get_theme_manager
from ...utils.audio_recorder import AudioRecorder


class RecorderDialog(QDialog):
    """
    Dialog do nagrywania rozmów z mikrofonu.
    
    Signals:
        recording_saved: Emitowany gdy nagranie zostanie zapisane (ścieżka do pliku)
    """
    
    recording_saved = pyqtSignal(str)  # Ścieżka do zapisanego pliku
    
    def __init__(self, recordings_folder: Path, parent=None):
        """
        Inicjalizacja dialogu nagrywania.
        
        Args:
            recordings_folder: Ścieżka do folderu, w którym będą zapisywane nagrania
            parent: Widget rodzica
        """
        super().__init__(parent)
        self.recordings_folder = recordings_folder
        self.recorder: Optional[AudioRecorder] = None
        self.recording_start_time: Optional[datetime] = None
        self.elapsed_seconds = 0
        self.is_paused = False
        
        self.theme_manager = get_theme_manager()
        
        self._setup_ui()
        self._apply_theme()
        self._load_audio_devices()
        
        # Timer do aktualizacji czasu nagrywania
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_duration)
        
        logger.info(f"RecorderDialog initialized with folder: {recordings_folder}")
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika."""
        self.setWindowTitle(t('callcryptor.recorder.title'))
        self.setModal(True)
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # === Status nagrywania ===
        status_frame = QFrame()
        status_frame.setFrameShape(QFrame.Shape.StyledPanel)
        status_layout = QVBoxLayout(status_frame)
        
        self.status_label = QLabel(t('callcryptor.recorder.status_ready'))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        status_font = QFont()
        status_font.setPointSize(14)
        status_font.setBold(True)
        self.status_label.setFont(status_font)
        status_layout.addWidget(self.status_label)
        
        # Timer
        self.duration_label = QLabel("00:00:00")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        duration_font = QFont()
        duration_font.setPointSize(24)
        duration_font.setBold(True)
        self.duration_label.setFont(duration_font)
        status_layout.addWidget(self.duration_label)
        
        layout.addWidget(status_frame)
        
        # === Poziom głośności ===
        volume_layout = QVBoxLayout()
        volume_label = QLabel(t('callcryptor.recorder.volume_level'))
        volume_layout.addWidget(volume_label)
        
        self.volume_bar = QProgressBar()
        self.volume_bar.setRange(0, 100)
        self.volume_bar.setValue(0)
        self.volume_bar.setTextVisible(False)
        self.volume_bar.setMaximumHeight(20)
        volume_layout.addWidget(self.volume_bar)
        
        layout.addLayout(volume_layout)
        
        # === Nazwa pliku ===
        filename_layout = QHBoxLayout()
        filename_label = QLabel(t('callcryptor.recorder.file_name') + ":")
        filename_layout.addWidget(filename_label)
        
        self.filename_input = QLineEdit()
        self.filename_input.setPlaceholderText(t('callcryptor.recorder.file_name_placeholder'))
        # Domyślna nazwa z datą i godziną
        default_name = datetime.now().strftime("nagranie_%Y%m%d_%H%M%S")
        self.filename_input.setText(default_name)
        filename_layout.addWidget(self.filename_input)
        
        layout.addLayout(filename_layout)
        
        # === Wybór urządzenia audio ===
        device_layout = QHBoxLayout()
        device_label = QLabel(t('callcryptor.recorder.device') + ":")
        device_layout.addWidget(device_label)
        
        self.device_combo = QComboBox()
        device_layout.addWidget(self.device_combo)
        
        layout.addLayout(device_layout)
        
        # === Separator ===
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # === Przyciski kontroli ===
        controls_layout = QHBoxLayout()
        
        self.start_btn = QPushButton(t('callcryptor.recorder.start'))
        self.start_btn.setMinimumHeight(40)
        self.start_btn.clicked.connect(self._on_start)
        controls_layout.addWidget(self.start_btn)
        
        self.pause_btn = QPushButton(t('callcryptor.recorder.pause'))
        self.pause_btn.setMinimumHeight(40)
        self.pause_btn.clicked.connect(self._on_pause)
        self.pause_btn.setEnabled(False)
        controls_layout.addWidget(self.pause_btn)
        
        self.stop_btn = QPushButton(t('callcryptor.recorder.stop'))
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.clicked.connect(self._on_stop)
        self.stop_btn.setEnabled(False)
        controls_layout.addWidget(self.stop_btn)
        
        layout.addLayout(controls_layout)
        
        # === Przyciski akcji ===
        actions_layout = QHBoxLayout()
        actions_layout.addStretch()
        
        self.cancel_btn = QPushButton(t('callcryptor.recorder.cancel'))
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.clicked.connect(self._on_cancel)
        actions_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(actions_layout)
        
        self.setLayout(layout)
    
    def _apply_theme(self):
        """Zastosuj aktualny motyw."""
        colors = self.theme_manager.get_current_colors()
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors['bg_main']};
                color: {colors['text_primary']};
            }}
            QLabel {{
                color: {colors['text_primary']};
            }}
            QLineEdit, QComboBox {{
                background-color: {colors['bg_secondary']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_light']};
                border-radius: 4px;
                padding: 5px;
            }}
            QPushButton {{
                background-color: {colors['accent_primary']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors['accent_hover']};
            }}
            QPushButton:pressed {{
                background-color: {colors['accent_pressed']};
            }}
            QPushButton:disabled {{
                background-color: {colors['border_light']};
                color: {colors['text_secondary']};
            }}
            QProgressBar {{
                border: 1px solid {colors['border_light']};
                border-radius: 4px;
                text-align: center;
                background-color: {colors['bg_secondary']};
            }}
            QProgressBar::chunk {{
                background-color: #4CAF50;
                border-radius: 3px;
            }}
            QFrame {{
                background-color: {colors['bg_secondary']};
                border: 1px solid {colors['border_light']};
                border-radius: 4px;
            }}
        """)
    
    def _load_audio_devices(self):
        """Załaduj listę dostępnych urządzeń audio."""
        try:
            devices = AudioRecorder.get_available_devices()
            
            if not devices:
                logger.warning("No audio input devices found")
                self.device_combo.addItem("Brak dostępnych urządzeń", None)
                self.start_btn.setEnabled(False)
                return
            
            # Dodaj urządzenia do listy
            for device in devices:
                device_name = f"{device['name']} ({int(device['sample_rate'])} Hz)"
                self.device_combo.addItem(device_name, device['index'])
            
            # Ustaw domyślne urządzenie
            default_device = AudioRecorder.get_default_device()
            if default_device:
                # Znajdź index domyślnego urządzenia
                for i in range(self.device_combo.count()):
                    if default_device['name'] in self.device_combo.itemText(i):
                        self.device_combo.setCurrentIndex(i)
                        break
            
            logger.info(f"Loaded {len(devices)} audio devices")
            
        except Exception as e:
            logger.error(f"Error loading audio devices: {e}")
            QMessageBox.critical(
                self,
                t('common.error'),
                t('callcryptor.recorder.error_device')
            )
    
    def _on_start(self):
        """Rozpocznij nagrywanie."""
        try:
            # Sprawdź nazwę pliku
            filename = self.filename_input.text().strip()
            if not filename:
                QMessageBox.warning(
                    self,
                    t('common.warning'),
                    "Wprowadź nazwę pliku"
                )
                return
            
            # Dodaj rozszerzenie .wav jeśli nie ma
            if not filename.endswith('.wav'):
                filename += '.wav'
            
            # Pełna ścieżka do pliku
            output_path = self.recordings_folder / filename
            
            # Sprawdź czy plik już istnieje
            if output_path.exists():
                reply = QMessageBox.question(
                    self,
                    t('common.warning'),
                    f"Plik {filename} już istnieje. Czy chcesz nadpisać?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                if reply == QMessageBox.StandardButton.No:
                    return
            
            # Utwórz recorder
            self.recorder = AudioRecorder(sample_rate=44100, channels=1)
            
            # Ustaw callback dla poziomu głośności
            self.recorder.set_level_callback(self._update_volume_level)
            
            # Rozpocznij nagrywanie
            self.recorder.start_recording(output_path)
            
            # Aktualizuj UI
            self.recording_start_time = datetime.now()
            self.elapsed_seconds = 0
            self.is_paused = False
            
            self.status_label.setText(t('callcryptor.recorder.status_recording'))
            self.status_label.setStyleSheet("color: #F44336;")  # Czerwony
            
            self.start_btn.setEnabled(False)
            self.pause_btn.setEnabled(True)
            self.stop_btn.setEnabled(True)
            self.filename_input.setEnabled(False)
            self.device_combo.setEnabled(False)
            
            # Uruchom timer
            self.timer.start(1000)  # Aktualizuj co sekundę
            
            logger.info(f"Recording started: {output_path}")
            
        except Exception as e:
            logger.error(f"Error starting recording: {e}")
            QMessageBox.critical(
                self,
                t('common.error'),
                t('callcryptor.recorder.error_start') + f"\n{str(e)}"
            )
    
    def _on_pause(self):
        """Wstrzymaj lub wznów nagrywanie."""
        if not self.recorder:
            return
        
        try:
            if self.is_paused:
                # Wznów nagrywanie
                self.recorder.resume_recording()
                self.is_paused = False
                self.status_label.setText(t('callcryptor.recorder.status_recording'))
                self.status_label.setStyleSheet("color: #F44336;")  # Czerwony
                self.pause_btn.setText(t('callcryptor.recorder.pause'))
                self.timer.start(1000)
                logger.info("Recording resumed")
            else:
                # Wstrzymaj nagrywanie
                self.recorder.pause_recording()
                self.is_paused = True
                self.status_label.setText(t('callcryptor.recorder.status_paused'))
                self.status_label.setStyleSheet("color: #FF9800;")  # Pomarańczowy
                self.pause_btn.setText(t('callcryptor.recorder.resume'))
                self.timer.stop()
                logger.info("Recording paused")
                
        except Exception as e:
            logger.error(f"Error pausing/resuming recording: {e}")
            QMessageBox.critical(
                self,
                t('common.error'),
                str(e)
            )
    
    def _on_stop(self):
        """Zatrzymaj nagrywanie i zapisz."""
        if not self.recorder:
            return
        
        try:
            # Zatrzymaj timer
            self.timer.stop()
            
            # Zatrzymaj nagrywanie i zapisz
            output_path = self.recorder.stop_recording()
            
            logger.info(f"Recording stopped and saved: {output_path}")
            
            # Pokaż komunikat
            QMessageBox.information(
                self,
                t('callcryptor.recorder.title'),
                t('callcryptor.recorder.recording_saved') + f"\n{output_path.name}"
            )
            
            # Emituj sygnał
            self.recording_saved.emit(str(output_path))
            
            # Zamknij dialog
            self.accept()
            
        except Exception as e:
            logger.error(f"Error stopping recording: {e}")
            QMessageBox.critical(
                self,
                t('common.error'),
                t('callcryptor.recorder.error_save') + f"\n{str(e)}"
            )
    
    def _on_cancel(self):
        """Anuluj nagrywanie."""
        # Jeśli nagrywanie w toku, potwierdź anulowanie
        if self.recorder and self.recorder.is_recording:
            reply = QMessageBox.question(
                self,
                t('callcryptor.recorder.warning_cancel_title'),
                t('callcryptor.recorder.warning_cancel'),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                try:
                    self.timer.stop()
                    self.recorder.cancel_recording()
                    logger.info("Recording cancelled by user")
                except Exception as e:
                    logger.error(f"Error cancelling recording: {e}")
                
                self.reject()
        else:
            self.reject()
    
    def _update_duration(self):
        """Aktualizuj wyświetlany czas trwania nagrywania."""
        if self.recorder and self.recorder.is_recording and not self.is_paused:
            self.elapsed_seconds += 1
            
            # Konwertuj sekundy na format HH:MM:SS
            duration = timedelta(seconds=self.elapsed_seconds)
            hours = duration.seconds // 3600
            minutes = (duration.seconds % 3600) // 60
            seconds = duration.seconds % 60
            
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.duration_label.setText(time_str)
    
    def _update_volume_level(self, level: float):
        """
        Aktualizuj wizualizację poziomu głośności.
        
        Args:
            level: Poziom głośności (0.0-1.0)
        """
        # Konwertuj na wartość 0-100 dla progress bara
        volume_percent = int(level * 100)
        self.volume_bar.setValue(volume_percent)
        
        # Zmień kolor w zależności od poziomu
        if volume_percent < 30:
            color = "#4CAF50"  # Zielony - niski poziom
        elif volume_percent < 70:
            color = "#FF9800"  # Pomarańczowy - średni poziom
        else:
            color = "#F44336"  # Czerwony - wysoki poziom
        
        self.volume_bar.setStyleSheet(f"""
            QProgressBar::chunk {{
                background-color: {color};
                border-radius: 3px;
            }}
        """)
    
    def closeEvent(self, event):
        """Obsłuż zamknięcie dialogu."""
        # Jeśli nagrywanie w toku, zatrzymaj je
        if self.recorder and self.recorder.is_recording:
            self._on_cancel()
            event.ignore()
        else:
            event.accept()
