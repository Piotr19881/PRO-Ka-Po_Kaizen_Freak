"""
Transcription Dialog
====================

Dialog do transkrypcji nagrań audio z wykorzystaniem AI.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTextEdit, QProgressBar, QMessageBox, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
from pathlib import Path
from typing import Optional, Callable
from loguru import logger
import traceback

from ..utils.theme_manager import get_theme_manager


class TranscriptionWorker(QThread):
    """Worker thread dla transkrypcji audio"""
    
    progress = pyqtSignal(int, str)  # (progress_value, status_message)
    finished = pyqtSignal(str)  # transcription_text
    error = pyqtSignal(str)  # error_message
    
    def __init__(self, audio_file_path: str, transcribe_callback: Callable):
        """
        Args:
            audio_file_path: Ścieżka do pliku audio
            transcribe_callback: Funkcja wykonująca transkrypcję (zwraca tekst)
        """
        super().__init__()
        self.audio_file_path = audio_file_path
        self.transcribe_callback = transcribe_callback
        self._is_cancelled = False
    
    def run(self):
        """Wykonaj transkrypcję w osobnym wątku"""
        try:
            # Sprawdź czy plik istnieje
            if not Path(self.audio_file_path).exists():
                self.error.emit(f"Plik nie istnieje: {self.audio_file_path}")
                return
            
            # Rozpocznij transkrypcję
            self.progress.emit(10, "Przesyłanie pliku audio...")
            
            if self._is_cancelled:
                return
            
            self.progress.emit(30, "Transkrypcja w toku...")
            
            # Wykonaj transkrypcję
            transcription_text = self.transcribe_callback(self.audio_file_path)
            
            if self._is_cancelled:
                return
            
            self.progress.emit(90, "Finalizowanie...")
            
            # Zwróć wynik
            if transcription_text:
                self.finished.emit(transcription_text)
            else:
                self.error.emit("Transkrypcja nie zwróciła żadnego tekstu")
            
        except Exception as e:
            logger.error(f"[TranscriptionWorker] Error: {e}\n{traceback.format_exc()}")
            self.error.emit(f"Błąd transkrypcji: {str(e)}")
    
    def cancel(self):
        """Anuluj transkrypcję"""
        self._is_cancelled = True


class TranscriptionDialog(QDialog):
    """Dialog transkrypcji nagrań audio"""
    
    transcription_completed = pyqtSignal(str)  # Emitowany gdy transkrypcja się powiedzie
    
    def __init__(self, audio_file_path: str, transcribe_callback: Callable, parent=None, recording=None, db_manager=None):
        """
        Args:
            audio_file_path: Ścieżka do pliku audio
            transcribe_callback: Funkcja wykonująca transkrypcję
            parent: Widget rodzica
            recording: Słownik z danymi nagrania (opcjonalny)
            db_manager: Manager bazy danych (opcjonalny)
        """
        super().__init__(parent)
        self.audio_file_path = audio_file_path
        self.transcribe_callback = transcribe_callback
        self.transcription_text = ""
        self.worker: Optional[TranscriptionWorker] = None
        self.recording = recording or {}
        self.db_manager = db_manager
        
        # Theme manager
        self.theme_manager = get_theme_manager()
        
        self.setWindowTitle("🎙️ Transkrypcja nagrania")
        self.setMinimumWidth(700)
        self.setMinimumHeight(500)
        self.setModal(True)
        
        self._setup_ui()
        self.apply_theme()
        self._start_transcription()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === NAGŁÓWEK ===
        self.header = QLabel("Transkrypcja nagrania audio")
        layout.addWidget(self.header)
        
        # Ścieżka pliku
        self.file_label = QLabel(f"📁 {Path(self.audio_file_path).name}")
        layout.addWidget(self.file_label)
        
        # === PROGRESS BAR ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setMinimum(0)
        self.progress_bar.setMaximum(100)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Status message
        self.status_label = QLabel("Inicjalizacja...")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # === SEPARATOR ===
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep)
        
        # === POLE TEKSTOWE NA TRANSKRYPCJĘ ===
        self.text_label = QLabel("Tekst transkrypcji:")
        layout.addWidget(self.text_label)
        
        self.transcription_text_edit = QTextEdit()
        self.transcription_text_edit.setReadOnly(True)
        self.transcription_text_edit.setPlaceholderText("Transkrypcja pojawi się tutaj...")
        self.transcription_text_edit.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.transcription_text_edit)
        
        # === SEPARATOR ===
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep2)
        
        # === PRZYCISKI ===
        buttons_layout = QHBoxLayout()
        
        # Przycisk Podsumuj
        self.summarize_btn = QPushButton("📝 Podsumuj")
        self.summarize_btn.setEnabled(False)
        self.summarize_btn.setMinimumHeight(35)
        self.summarize_btn.clicked.connect(self._on_summarize)
        buttons_layout.addWidget(self.summarize_btn)
        
        # Przycisk Utwórz notatkę
        self.create_note_btn = QPushButton("📒 Utwórz notatkę")
        self.create_note_btn.setEnabled(False)
        self.create_note_btn.setMinimumHeight(35)
        self.create_note_btn.clicked.connect(self._on_create_note)
        buttons_layout.addWidget(self.create_note_btn)
        
        buttons_layout.addStretch()
        
        # Przycisk Zamknij
        self.close_btn = QPushButton("Zamknij")
        self.close_btn.setMinimumHeight(35)
        self.close_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
    
    def _start_transcription(self):
        """Rozpocznij transkrypcję w osobnym wątku"""
        self.worker = TranscriptionWorker(self.audio_file_path, self.transcribe_callback)
        self.worker.progress.connect(self._on_progress)
        self.worker.finished.connect(self._on_finished)
        self.worker.error.connect(self._on_error)
        self.worker.start()
    
    def _on_progress(self, value: int, message: str):
        """Aktualizuj progress bar"""
        self.progress_bar.setValue(value)
        self.status_label.setText(message)
    
    def _on_finished(self, transcription_text: str):
        """Obsługa zakończonej transkrypcji"""
        self.transcription_text = transcription_text
        self.transcription_text_edit.setPlainText(transcription_text)
        
        self.progress_bar.setValue(100)
        self.status_label.setText("✅ Transkrypcja zakończona")
        
        # Włącz przyciski akcji
        self.summarize_btn.setEnabled(True)
        self.create_note_btn.setEnabled(True)
        
        # Emituj sygnał
        self.transcription_completed.emit(transcription_text)
        
        logger.info(f"[TranscriptionDialog] Transcription completed: {len(transcription_text)} chars")
    
    def _on_error(self, error_message: str):
        """Obsługa błędu transkrypcji"""
        self.progress_bar.setValue(0)
        self.status_label.setText(f"❌ {error_message}")
        self.transcription_text_edit.setPlainText(f"Błąd:\n{error_message}")
        
        QMessageBox.critical(self, "Błąd transkrypcji", error_message)
        
        logger.error(f"[TranscriptionDialog] Transcription error: {error_message}")
    
    def _on_summarize(self):
        """Podsumuj transkrypcję za pomocą AI"""
        if not self.transcription_text:
            QMessageBox.warning(
                self,
                "Brak transkrypcji",
                "Nie można podsumować - brak transkrypcji."
            )
            return
        
        try:
            # Zamknij dialog transkrypcji
            self.accept()
            
            # Pobierz CallCryptorView (parent)
            callcryptor_view = self.parent()
            if not callcryptor_view:
                logger.error("[TranscriptionDialog] Cannot access CallCryptorView")
                return
            
            # Wywołaj funkcję AI Summary z callcryptor_view
            callcryptor_view._ai_summary(self.recording)
            
        except Exception as e:
            logger.error(f"[TranscriptionDialog] Error opening AI summary: {e}")
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się otworzyć podsumowania AI:\n{str(e)}"
            )
    
    def _on_create_note(self):
        """Utwórz notatkę z transkrypcji"""
        if not self.transcription_text:
            QMessageBox.warning(
                self,
                "Brak transkrypcji",
                "Nie można utworzyć notatki - brak transkrypcji."
            )
            return
        
        try:
            from datetime import datetime
            
            # Pobierz nazwę kontaktu
            contact_name = self.recording.get('contact_info') or self.recording.get('contact_name') or self.recording.get('file_name') or "Nieznany"
            
            # Sprawdź czy notatka już istnieje
            if self.recording.get('note_id'):
                # Zamknij dialog i otwórz istniejącą notatkę
                self.accept()
                
                # Pobierz CallCryptorView i wywołaj _create_note
                callcryptor_view = self.parent()
                if callcryptor_view:
                    callcryptor_view._create_note(self.recording)
                return
            
            # Pobierz CallCryptorView -> QStackedWidget -> central_widget -> MainWindow
            # TranscriptionDialog.parent() → CallCryptorView
            # CallCryptorView.parent() → QStackedWidget
            # QStackedWidget.parent() → central_widget (QWidget)
            # central_widget.parent() → MainWindow
            callcryptor_view = self.parent()
            logger.info(f"[TranscriptionDialog] callcryptor_view={callcryptor_view}, type={type(callcryptor_view)}")
            
            if not callcryptor_view:
                logger.error("[TranscriptionDialog] Cannot access CallCryptorView")
                QMessageBox.warning(self, "Błąd", "Nie można otworzyć widoku notatek (brak CallCryptorView)")
                return
            
            content_stack = callcryptor_view.parent()
            logger.info(f"[TranscriptionDialog] content_stack={content_stack}, type={type(content_stack)}")
            
            central_widget = content_stack.parent() if content_stack else None
            logger.info(f"[TranscriptionDialog] central_widget={central_widget}, type={type(central_widget)}")
            
            main_window = central_widget.parent() if central_widget else None
            logger.info(f"[TranscriptionDialog] main_window={main_window}, type={type(main_window)}")
            
            has_notes_view = hasattr(main_window, 'notes_view') if main_window else False
            logger.info(f"[TranscriptionDialog] has_notes_view={has_notes_view}")
            
            if not main_window or not has_notes_view:
                logger.error("[TranscriptionDialog] Cannot access notes view - main window not found or no notes_view")
                QMessageBox.warning(self, "Błąd", "Nie można otworzyć widoku notatek (brak main_window lub notes_view)")
                return
            
            # Utwórz treść notatki
            note_title = f"ROZMOWA: {contact_name}"
            note_content = f"<h3>Transkrypcja rozmowy</h3><p>{self.transcription_text.replace(chr(10), '</p><p>')}</p>"
            
            # Dodaj metadane
            call_date = self.recording.get('recorded_date', 'nieznana data')
            duration = self.recording.get('duration', 0)
            note_content = (
                f"<p><b>Data:</b> {call_date}</p>"
                f"<p><b>Kontakt:</b> {contact_name}</p>"
                f"<p><b>Czas trwania:</b> {duration}s</p>"
                f"<hr>"
                f"{note_content}"
            )
            
            # Utwórz notatkę
            new_note_id = main_window.notes_view.db.create_note(
                title=note_title,
                content=note_content,
                color="#FF5722"  # Pomarańczowy dla notatek z rozmów
            )
            
            # Zapisz note_id do nagrania
            if self.db_manager:
                self.db_manager.update_recording(self.recording['id'], {'note_id': new_note_id})
            
            logger.info(f"[TranscriptionDialog] Created note {new_note_id} for recording {self.recording['id']}")
            
            # Zamknij dialog
            self.accept()
            
            # Przełącz na widok notatek i wybierz notatkę
            main_window._on_view_changed("notes")
            
            from PyQt6.QtCore import QTimer
            def open_note():
                main_window.notes_view.refresh_tree()
                main_window.notes_view.select_note_in_tree(str(new_note_id))
            
            QTimer.singleShot(100, open_note)
                
        except Exception as e:
            logger.error(f"[TranscriptionDialog] Error creating note: {e}")
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się utworzyć notatki:\n{str(e)}"
            )
    
    def get_transcription(self) -> str:
        """Pobierz tekst transkrypcji"""
        return self.transcription_text
    
    def apply_theme(self):
        """Zastosuj aktualny motyw"""
        if not self.theme_manager:
            return
        
        colors = self.theme_manager.get_current_colors()
        
        # Tło dialogu
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors['bg_main']};
            }}
        """)
        
        # Nagłówek
        if hasattr(self, 'header'):
            self.header.setStyleSheet(f"font-size: 16px; font-weight: bold; color: {colors['text_primary']};")
        
        # Etykieta pliku
        if hasattr(self, 'file_label'):
            self.file_label.setStyleSheet(f"color: {colors['text_secondary']}; font-style: italic;")
        
        # Progress bar
        if hasattr(self, 'progress_bar'):
            self.progress_bar.setStyleSheet(f"""
                QProgressBar {{
                    border: 2px solid {colors['border_light']};
                    border-radius: 5px;
                    text-align: center;
                    background-color: {colors['bg_secondary']};
                    color: {colors['text_primary']};
                }}
                QProgressBar::chunk {{
                    background: qlineargradient(
                        x1:0, y1:0, x2:1, y2:0,
                        stop:0 {colors['accent_primary']}, stop:1 {colors['accent_hover']}
                    );
                    border-radius: 3px;
                }}
            """)
        
        # Status label
        if hasattr(self, 'status_label'):
            self.status_label.setStyleSheet(f"color: {colors['text_secondary']}; font-size: 12px;")
        
        # Text label
        if hasattr(self, 'text_label'):
            self.text_label.setStyleSheet(f"font-weight: bold; color: {colors['text_primary']};")
        
        # Pole tekstowe transkrypcji
        if hasattr(self, 'transcription_text_edit'):
            self.transcription_text_edit.setStyleSheet(f"""
                QTextEdit {{
                    border: 1px solid {colors['border_light']};
                    border-radius: 5px;
                    padding: 10px;
                    background-color: {colors['bg_secondary']};
                    color: {colors['text_primary']};
                }}
            """)
        
        # Przyciski
        if hasattr(self, 'summarize_btn'):
            self.summarize_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors['accent_primary']};
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 10px 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {colors['accent_hover']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['accent_pressed']};
                }}
                QPushButton:disabled {{
                    background-color: {colors['bg_secondary']};
                    color: {colors['text_secondary']};
                }}
            """)
        
        if hasattr(self, 'create_note_btn'):
            self.create_note_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors['accent_primary']};
                    color: white;
                    border: none;
                    border-radius: 5px;
                    padding: 10px 20px;
                    font-weight: bold;
                }}
                QPushButton:hover {{
                    background-color: {colors['accent_hover']};
                }}
                QPushButton:pressed {{
                    background-color: {colors['accent_pressed']};
                }}
                QPushButton:disabled {{
                    background-color: {colors['bg_secondary']};
                    color: {colors['text_secondary']};
                }}
            """)
        
        if hasattr(self, 'close_btn'):
            self.close_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {colors['bg_secondary']};
                    color: {colors['text_primary']};
                    border: 1px solid {colors['border_light']};
                    border-radius: 5px;
                    padding: 10px 20px;
                }}
                QPushButton:hover {{
                    background-color: {colors['accent_primary']};
                    color: white;
                }}
                QPushButton:pressed {{
                    background-color: {colors['accent_pressed']};
                    color: white;
                }}
            """)
    
    def closeEvent(self, event):
        """Obsługa zamknięcia okna"""
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.worker.wait(2000)  # Czekaj max 2s
        event.accept()
