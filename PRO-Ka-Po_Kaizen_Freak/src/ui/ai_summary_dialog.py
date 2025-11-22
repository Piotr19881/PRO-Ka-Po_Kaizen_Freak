"""
AI Summary Dialog - Dialog podsumowania rozmowy przez AI
==========================================================

Dialog z dwoma fazami:
1. Faza zapytania - konfiguracja promptów i generowanie
2. Faza wyników - wyświetlanie podsumowania i zadań

Integracja:
- Theme Manager dla dynamicznego motywu
- i18n Manager dla wielojęzyczności
- AI Manager dla generowania podsumowań
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTextEdit, QProgressBar, QTabWidget,
    QWidget, QCheckBox, QScrollArea, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
from loguru import logger
import json
import re
from typing import Optional, Dict, List

from ..utils.i18n_manager import t
from ..utils.theme_manager import get_theme_manager


class AIGenerationThread(QThread):
    """Wątek do generowania podsumowania AI w tle"""
    
    finished = pyqtSignal(dict)  # {'summary': str, 'tasks': List[str]}
    error = pyqtSignal(str)
    progress = pyqtSignal(str)  # Status progress
    
    def __init__(self, ai_manager, recording: dict, standard_prompt: str, additional_prompt: str):
        super().__init__()
        self.ai_manager = ai_manager
        self.recording = recording
        self.standard_prompt = standard_prompt
        self.additional_prompt = additional_prompt
    
    def run(self):
        """Wykonaj generowanie podsumowania"""
        try:
            # Sprawdź czy jest transkrypcja
            transcription_text = self.recording.get('transcription_text') or ''
            transcription = transcription_text.strip()
            
            if transcription:
                # ŚCIEŻKA 1: Mamy transkrypcję - użyj jej
                self.progress.emit("Przygotowywanie promptu...")
                logger.info("[AISummary] Using existing transcription")
                
                # Skonstruuj pełny prompt
                full_prompt = f"{self.standard_prompt}\n\n"
                if self.additional_prompt.strip():
                    full_prompt += f"Dodatkowe instrukcje: {self.additional_prompt}\n\n"
                full_prompt += f"Transkrypcja rozmowy:\n{transcription}"
                
                self.progress.emit("Wysyłanie do AI...")
                
                # Wywołaj AI
                response = self.ai_manager.generate(full_prompt, use_cache=False)
                
                if response.error:
                    self.error.emit(f"Błąd AI: {response.error}")
                    return
                
                self.progress.emit("Przetwarzanie odpowiedzi...")
                
                # Parsuj odpowiedź
                summary_text, tasks = self._parse_ai_response(response.text)
                
            else:
                # ŚCIEŻKA 2: Brak transkrypcji - wyślij plik audio bezpośrednio
                file_path = self.recording.get('file_path') or ''
                if not file_path:
                    self.error.emit("Brak ścieżki do pliku audio")
                    return
                
                self.progress.emit("Wczytywanie pliku audio...")
                logger.info(f"[AISummary] No transcription, sending audio file: {file_path}")
                
                # Sprawdź czy plik istnieje
                from pathlib import Path
                audio_path = Path(file_path)
                if not audio_path.exists():
                    self.error.emit(f"Nie znaleziono pliku audio: {file_path}")
                    return
                
                self.progress.emit("Wysyłanie audio do AI (może potrwać dłużej)...")
                
                # Wyślij audio bezpośrednio do podsumowania
                try:
                    result_text = self.ai_manager.summarize_audio(
                        audio_file_path=str(audio_path),
                        additional_prompt=self.additional_prompt
                    )
                    
                    self.progress.emit("Przetwarzanie odpowiedzi...")
                    
                    # Parsuj odpowiedź
                    summary_text, tasks = self._parse_ai_response(result_text)
                    
                except Exception as e:
                    logger.error(f"[AISummary] Audio processing error: {e}")
                    self.error.emit(f"Błąd podczas przetwarzania audio: {str(e)}")
                    return
            
            # Wyślij wynik
            self.finished.emit({
                'summary': summary_text,
                'tasks': tasks,
                'raw_response': summary_text
            })
            
        except Exception as e:
            logger.error(f"[AISummary] Error generating summary: {e}")
            self.error.emit(str(e))
    
    def _parse_ai_response(self, response: str) -> tuple[str, List[str]]:
        """
        Parsuj odpowiedź AI i wyodrębnij podsumowanie oraz zadania
        
        Returns:
            (summary_text, tasks_list)
        """
        # Najpierw spróbuj sparsować jako JSON
        try:
            # Sprawdź czy odpowiedź zawiera JSON
            if '{' in response and '"summary"' in response:
                # Wyodrębnij JSON (może być w bloku kodu markdown)
                json_match = re.search(r'```json\s*(\{.+?\})\s*```', response, re.DOTALL)
                if json_match:
                    json_str = json_match.group(1)
                else:
                    # Spróbuj znaleźć JSON bez markdown
                    json_match = re.search(r'\{.+\}', response, re.DOTALL)
                    if json_match:
                        json_str = json_match.group(0)
                    else:
                        json_str = None
                
                if json_str:
                    data = json.loads(json_str)
                    summary = data.get('summary', '').strip()
                    tasks = data.get('tasks', [])
                    
                    # Jeśli tasks jest string, spróbuj sparsować jako listę
                    if isinstance(tasks, str):
                        tasks = [t.strip() for t in tasks.split('\n') if t.strip()]
                    
                    logger.info(f"[AISummary] Parsed JSON response: {len(summary)} chars, {len(tasks)} tasks")
                    return summary.strip(), tasks
        except json.JSONDecodeError as e:
            logger.warning(f"[AISummary] Failed to parse JSON response: {e}, falling back to text parsing")
        except Exception as e:
            logger.warning(f"[AISummary] Error parsing JSON: {e}, falling back to text parsing")
        
        # Jeśli JSON się nie udał, użyj parsowania tekstowego
        # Szukaj sekcji z zadaniami (różne formaty)
        tasks = []
        summary = response
        
        # Wzorce dla zadań
        task_patterns = [
            r'[-*]\s+(.+?)(?:\n|$)',  # - Zadanie lub * Zadanie
            r'\d+\.\s+(.+?)(?:\n|$)',  # 1. Zadanie
            r'TODO:\s*(.+?)(?:\n|$)',  # TODO: Zadanie
            r'Zadanie \d+:\s*(.+?)(?:\n|$)',  # Zadanie 1: ...
        ]
        
        # Próbuj znaleźć sekcję z zadaniami
        task_section_markers = [
            'zadania do wykonania',
            'lista zadań',
            'action items',
            'to do',
            'tasks',
            'do zrobienia'
        ]
        
        # Znajdź początek sekcji zadań
        task_section_start = -1
        for marker in task_section_markers:
            idx = response.lower().find(marker)
            if idx != -1:
                task_section_start = idx
                break
        
        if task_section_start != -1:
            # Podziel na podsumowanie i zadania
            summary = response[:task_section_start].strip()
            tasks_text = response[task_section_start:]
            
            # Wyodrębnij zadania
            for pattern in task_patterns:
                matches = re.findall(pattern, tasks_text, re.MULTILINE)
                if matches:
                    tasks.extend([task.strip() for task in matches if task.strip()])
                    break
        
        # Usuń duplikaty zachowując kolejność
        seen = set()
        tasks = [task for task in tasks if not (task in seen or seen.add(task))]
        
        return summary.strip(), tasks


class AISummaryDialog(QDialog):
    """
    Dialog do generowania i wyświetlania podsumowania AI rozmowy
    """
    
    summary_completed = pyqtSignal(dict)  # {'summary': str, 'tasks': List[str]}
    
    def __init__(self, recording: dict, ai_manager, db_manager=None, parent=None):
        """
        Args:
            recording: Słownik z danymi nagrania
            ai_manager: AIManager instance do wywołania AI
            db_manager: Manager bazy danych CallCryptor
            parent: Widget rodzica
        """
        super().__init__(parent)
        
        self.recording = recording
        self.ai_manager = ai_manager
        self.db_manager = db_manager
        self.theme_manager = get_theme_manager()
        
        self.summary_data = None  # Przechowuje wyniki AI
        self.generation_thread = None
        
        # Sprawdź czy już istnieje podsumowanie
        existing_summary = recording.get('ai_summary_text')
        existing_tasks = recording.get('ai_summary_tasks')
        
        if existing_summary:
            # Załaduj istniejące podsumowanie
            try:
                tasks_list = json.loads(existing_tasks) if existing_tasks else []
            except:
                tasks_list = []
            
            self.summary_data = {
                'summary': existing_summary,
                'tasks': tasks_list,
                'raw_response': existing_summary
            }
        
        self._setup_ui()
        self.apply_theme()
        
        logger.info(f"[AISummary] Dialog opened for recording {recording.get('id')}")
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        self.setWindowTitle(t('callcryptor.ai_summary.dialog_title'))
        self.setMinimumSize(800, 600)
        
        layout = QVBoxLayout(self)
        
        if self.summary_data:
            # FAZA 2: Wyświetl istniejące podsumowanie
            self._create_results_view(layout)
        else:
            # FAZA 1: Formularz generowania
            self._create_generation_view(layout)
    
    def _create_generation_view(self, layout: QVBoxLayout):
        """Tworzy widok generowania (Faza 1)"""
        
        # === Nagłówek ===
        title_label = QLabel(t('callcryptor.ai_summary.dialog_title'))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # === Treść rozmowy (readonly) ===
        content_label = QLabel(f"{t('callcryptor.ai_summary.conversation_content')}:")
        layout.addWidget(content_label)
        
        self.content_text = QTextEdit()
        self.content_text.setReadOnly(True)
        self.content_text.setMaximumHeight(150)
        
        # Załaduj transkrypcję lub informację o nagraniu
        conversation_content = self.recording.get('transcription_text') or ''
        if not conversation_content:
            conversation_content = (
                f"Nagranie: {self.recording.get('contact_info', 'Nieznany')}\n"
                f"Data: {self.recording.get('recorded_date', 'N/A')}\n"
                f"Czas trwania: {self.recording.get('duration', 0)}s\n\n"
                f"[Brak transkrypcji - podsumowanie zostanie wygenerowane na podstawie analizy audio]"
            )
        
        self.content_text.setPlainText(conversation_content)
        layout.addWidget(self.content_text)
        
        # === Prompt standardowy ===
        standard_label = QLabel(f"{t('callcryptor.ai_summary.standard_prompt')}:")
        layout.addWidget(standard_label)
        
        self.standard_prompt_text = QTextEdit()
        self.standard_prompt_text.setMaximumHeight(120)
        self.standard_prompt_text.setPlainText(
            t('callcryptor.ai_summary.standard_prompt_default')
        )
        layout.addWidget(self.standard_prompt_text)
        
        # === Prompt dodatkowy ===
        additional_label = QLabel(f"{t('callcryptor.ai_summary.additional_prompt')}:")
        layout.addWidget(additional_label)
        
        self.additional_prompt_text = QTextEdit()
        self.additional_prompt_text.setMaximumHeight(80)
        self.additional_prompt_text.setPlaceholderText(
            "np. Skoncentruj się na aspektach technicznych..."
        )
        layout.addWidget(self.additional_prompt_text)
        
        # === Progress bar (ukryty początkowo) ===
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Nieokreślony progress
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel()
        self.progress_label.setVisible(False)
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress_label)
        
        # === Przyciski ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.generate_btn = QPushButton(t('callcryptor.ai_summary.generate'))
        self.generate_btn.clicked.connect(self._on_generate)
        self.generate_btn.setMinimumWidth(150)
        button_layout.addWidget(self.generate_btn)
        
        self.cancel_btn = QPushButton(t('common.cancel', 'Anuluj'))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _create_results_view(self, layout: QVBoxLayout):
        """Tworzy widok wyników (Faza 2)"""
        
        # === Nagłówek ===
        title_label = QLabel(t('callcryptor.ai_summary.dialog_title'))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        layout.addWidget(title_label)
        
        # === Zakładki ===
        self.tabs = QTabWidget()
        
        # Karta 1: Podsumowanie
        summary_tab = self._create_summary_tab()
        self.tabs.addTab(summary_tab, t('callcryptor.ai_summary.tab_summary'))
        
        # Karta 2: Zadania
        tasks_tab = self._create_tasks_tab()
        self.tabs.addTab(tasks_tab, t('callcryptor.ai_summary.tab_tasks'))
        
        layout.addWidget(self.tabs)
        
        # === Przycisk zamknięcia ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        close_btn = QPushButton(t('common.close', 'Zamknij'))
        close_btn.clicked.connect(self.accept)
        button_layout.addWidget(close_btn)
        
        layout.addLayout(button_layout)
    
    def _create_summary_tab(self) -> QWidget:
        """Tworzy kartę podsumowania"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Tekst podsumowania
        self.summary_text = QTextEdit()
        self.summary_text.setReadOnly(True)
        self.summary_text.setPlainText(self.summary_data.get('summary', ''))
        layout.addWidget(self.summary_text)
        
        # Przycisk utworzenia notatki
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        create_note_btn = QPushButton(f"📒 {t('callcryptor.ai_summary.create_note')}")
        create_note_btn.clicked.connect(self._on_create_note_from_summary)
        create_note_btn.setMinimumWidth(200)
        btn_layout.addWidget(create_note_btn)
        
        layout.addLayout(btn_layout)
        
        return tab
    
    def _create_tasks_tab(self) -> QWidget:
        """Tworzy kartę zadań z checkboxami"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Scroll area dla listy zadań
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        self.task_checkboxes = []
        self.task_texts = []  # Lista tekstów zadań (w tej samej kolejności co checkboxy)
        tasks = self.summary_data.get('tasks', [])
        
        if tasks:
            for i, task in enumerate(tasks):
                # Utwórz checkbox bez tekstu
                checkbox = QCheckBox()
                checkbox.setChecked(False)
                
                # Utwórz label z tekstem zadania (obsługuje word wrap)
                task_label = QLabel(task)
                task_label.setWordWrap(True)
                
                # Połącz w layout poziomy
                task_layout = QHBoxLayout()
                task_layout.addWidget(checkbox)
                task_layout.addWidget(task_label, 1)  # stretch factor = 1
                task_layout.setContentsMargins(0, 5, 0, 5)
                
                scroll_layout.addLayout(task_layout)
                self.task_checkboxes.append(checkbox)
                self.task_texts.append(task)  # Zapisz tekst zadania
        else:
            no_tasks_label = QLabel(t('callcryptor.ai_summary.no_tasks'))
            no_tasks_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            scroll_layout.addWidget(no_tasks_label)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Przycisk dodania zadań
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        self.add_tasks_btn = QPushButton(f"✅ {t('callcryptor.ai_summary.add_tasks')}")
        self.add_tasks_btn.clicked.connect(self._on_add_tasks)
        self.add_tasks_btn.setMinimumWidth(250)
        self.add_tasks_btn.setEnabled(len(tasks) > 0)
        btn_layout.addWidget(self.add_tasks_btn)
        
        layout.addLayout(btn_layout)
        
        return tab
    
    def _on_generate(self):
        """Rozpocznij generowanie podsumowania AI"""
        
        # Walidacja - nie wymaga już transkrypcji
        # Jeśli nie ma transkrypcji, sprawdź czy jest plik audio
        conversation_text = self.content_text.toPlainText().strip()
        transcription_text = self.recording.get('transcription_text') or ''
        has_transcription = transcription_text.strip()
        file_path = self.recording.get('file_path') or ''
        has_audio_file = file_path.strip()
        
        if not has_transcription and not has_audio_file:
            QMessageBox.warning(
                self,
                t('callcryptor.ai_summary.dialog_title'),
                "Brak transkrypcji i pliku audio. Nie można wygenerować podsumowania."
            )
            return
        
        standard_prompt = self.standard_prompt_text.toPlainText().strip()
        additional_prompt = self.additional_prompt_text.toPlainText().strip()
        
        # Dezaktywuj przycisk i pokaż progress
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_label.setText(t('callcryptor.ai_summary.generating'))
        self.progress_label.setVisible(True)
        
        # Uruchom wątek generowania - przekaż ai_manager zamiast callback
        self.generation_thread = AIGenerationThread(
            self.ai_manager,
            self.recording,
            standard_prompt,
            additional_prompt
        )
        self.generation_thread.finished.connect(self._on_generation_finished)
        self.generation_thread.error.connect(self._on_generation_error)
        self.generation_thread.progress.connect(self._on_generation_progress)
        self.generation_thread.start()
    
    def _on_generation_progress(self, status: str):
        """Aktualizuj status generowania"""
        self.progress_label.setText(status)
    
    def _on_generation_finished(self, result: dict):
        """Obsługa zakończenia generowania"""
        logger.info("[AISummary] Generation completed successfully")
        
        self.summary_data = result
        
        # Zapisz do bazy danych
        if self.db_manager and self.recording.get('id'):
            from datetime import datetime
            self.db_manager.update_recording(self.recording['id'], {
                'ai_summary_text': result['summary'],
                'ai_summary_tasks': json.dumps(result['tasks'], ensure_ascii=False),
                'ai_summary_status': 'completed',
                'ai_summary_date': datetime.now().isoformat()
            })
        
        # Emit sygnał
        self.summary_completed.emit(result)
        
        # Przebuduj UI na widok wyników
        self._rebuild_to_results_view()
    
    def _on_generation_error(self, error_msg: str):
        """Obsługa błędu generowania"""
        logger.error(f"[AISummary] Generation error: {error_msg}")
        
        self.progress_bar.setVisible(False)
        self.progress_label.setVisible(False)
        self.generate_btn.setEnabled(True)
        
        QMessageBox.critical(
            self,
            t('callcryptor.ai_summary.dialog_title'),
            f"{t('callcryptor.ai_summary.error')}: {error_msg}"
        )
    
    def _rebuild_to_results_view(self):
        """Przebuduj dialog na widok wyników"""
        # Usuń obecny layout
        layout = self.layout()
        while layout.count():
            child = layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Stwórz widok wyników
        self._create_results_view(layout)
        self.apply_theme()
    
    def _on_create_note_from_summary(self):
        """Utwórz notatkę z podsumowania"""
        if not self.summary_data:
            return
        
        # Sprawdź czy parent ma dostęp do main_window
        # AISummaryDialog.parent() → CallCryptorView
        # CallCryptorView.parent() → QStackedWidget
        # QStackedWidget.parent() → central_widget (QWidget)
        # central_widget.parent() → MainWindow
        callcryptor_view = self.parent()
        logger.info(f"[AISummary] callcryptor_view={callcryptor_view}, type={type(callcryptor_view)}")
        
        if not callcryptor_view:
            logger.error("[AISummary] Cannot access CallCryptorView - parent() returned None")
            QMessageBox.warning(
                self,
                t('callcryptor.ai_summary.dialog_title'),
                "Nie można otworzyć widoku notatek (brak CallCryptorView)"
            )
            return
        
        content_stack = callcryptor_view.parent()
        logger.info(f"[AISummary] content_stack={content_stack}, type={type(content_stack)}")
        
        central_widget = content_stack.parent() if content_stack else None
        logger.info(f"[AISummary] central_widget={central_widget}, type={type(central_widget)}")
        
        main_window = central_widget.parent() if central_widget else None
        logger.info(f"[AISummary] main_window={main_window}, type={type(main_window)}")
        
        has_notes_view = hasattr(main_window, 'notes_view') if main_window else False
        logger.info(f"[AISummary] has_notes_view={has_notes_view}")
        
        if not main_window or not has_notes_view:
            logger.error("[AISummary] Cannot access notes view - main window not found or no notes_view")
            QMessageBox.warning(
                self,
                t('callcryptor.ai_summary.dialog_title'),
                "Nie można otworzyć widoku notatek (brak main_window lub notes_view)"
            )
            return
        
        contact_name = self.recording.get('contact_info', 'Nieznany kontakt')
        note_title = f"PODSUMOWANIE: {contact_name}"
        
        # Sformatuj treść notatki
        summary_text = self.summary_data.get('summary', '')
        tasks = self.summary_data.get('tasks', [])
        
        note_content = f"<h2>Podsumowanie rozmowy</h2><p>{summary_text.replace(chr(10), '</p><p>')}</p>"
        
        if tasks:
            note_content += "<h3>Zadania do wykonania:</h3><ul>"
            for task in tasks:
                note_content += f"<li>{task}</li>"
            note_content += "</ul>"
        
        # Dodaj metadane
        call_date = self.recording.get('recorded_date', 'nieznana data')
        note_content = (
            f"<p><b>Kontakt:</b> {contact_name}</p>"
            f"<p><b>Data:</b> {call_date}</p>"
            f"<hr>"
            f"{note_content}"
        )
        
        # Get accent color from theme for AI summaries
        colors = self.theme_manager.get_current_colors() if hasattr(self, 'theme_manager') and self.theme_manager else {}
        note_color = colors.get('accent_primary', '#9C27B0')  # Fallback to purple
        
        try:
            new_note_id = main_window.notes_view.db.create_note(
                title=note_title,
                content=note_content,
                color=note_color  # Use theme color for AI summaries
            )
            
            logger.info(f"[AISummary] Created note {new_note_id} from summary")
            
            # Zamknij dialog
            self.accept()
            
            # Przełącz na widok notatek
            main_window._on_view_changed("notes")
            
            # Odśwież drzewo i wybierz notatkę
            from PyQt6.QtCore import QTimer
            def open_note():
                main_window.notes_view.refresh_tree()
                main_window.notes_view.select_note_in_tree(str(new_note_id))
            
            QTimer.singleShot(100, open_note)
            
        except Exception as e:
            logger.error(f"[AISummary] Error creating note: {e}")
            QMessageBox.warning(
                self,
                t('callcryptor.ai_summary.dialog_title'),
                f"Błąd: {str(e)}"
            )
    
    def _on_add_tasks(self):
        """Otwórz dialog szybkiego dodawania zadania dla zaznaczonych zadań"""
        # Pobierz indeksy zaznaczonych zadań
        selected_indices = [
            i for i, checkbox in enumerate(self.task_checkboxes) if checkbox.isChecked()
        ]
        
        if not selected_indices:
            QMessageBox.information(
                self,
                t('callcryptor.ai_summary.dialog_title'),
                "Nie zaznaczono żadnych zadań"
            )
            return
        
        # Pobierz MainWindow przez parent chain (3 poziomy)
        try:
            callcryptor_view = self.parent()
            if not callcryptor_view:
                logger.error("[AISummary] Cannot get CallCryptorView parent")
                return
            
            content_stack = callcryptor_view.parent()
            if not content_stack:
                logger.error("[AISummary] Cannot get QStackedWidget parent")
                return
            
            central_widget = content_stack.parent()
            if not central_widget:
                logger.error("[AISummary] Cannot get central_widget parent")
                return
            
            main_window = central_widget.parent()
            if not main_window:
                logger.error("[AISummary] Cannot get MainWindow parent")
                return
            
            # Pobierz QuickTaskDialog z MainWindow
            quick_task_dialog = getattr(main_window, 'quick_task_dialog', None)
            if not quick_task_dialog:
                logger.warning("[AISummary] QuickTaskDialog not available")
                QMessageBox.warning(
                    self,
                    t('callcryptor.ai_summary.dialog_title'),
                    "Dialog szybkiego dodawania zadania nie jest dostępny"
                )
                return
            
            # Otwórz dialog dla każdego zaznaczonego zadania
            for idx in selected_indices:
                task_text = self.task_texts[idx]
                
                # Ustaw tekst zadania w dialogu
                quick_task_dialog.set_task_text(task_text)
                quick_task_dialog.clear_inputs()  # Wyczyść pozostałe pola
                quick_task_dialog.set_task_text(task_text)  # Ustaw ponownie tekst (po wyczyszczeniu)
                
                # Zastosuj motyw i tłumaczenia
                quick_task_dialog.apply_theme()
                quick_task_dialog.update_translations()
                
                # Ukryj/zamknij dialog AI Summary, aby QuickTaskDialog był widoczny
                self.hide()
                
                # Pokaż dialog
                quick_task_dialog.show()
                quick_task_dialog.raise_()
                quick_task_dialog.activateWindow()
                quick_task_dialog.focus_input()
                
                logger.info(f"[AISummary] Opened QuickTaskDialog for task: {task_text}")
                
                # Otwórz tylko pierwszy zaznaczony - użytkownik może zaznaczyć kolejne po dodaniu
                break
            
            logger.info(f"[AISummary] Opened QuickTaskDialog for {len(selected_indices)} selected tasks")
            
        except Exception as e:
            logger.error(f"[AISummary] Error opening QuickTaskDialog: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.critical(
                self,
                t('callcryptor.ai_summary.dialog_title'),
                f"Błąd podczas otwierania dialogu: {str(e)}"
            )
    
    def apply_theme(self):
        """Aplikuj aktualny motyw"""
        colors = self.theme_manager.get_current_colors()
        
        # Style dla dialogu
        self.setStyleSheet(f"""
            QDialog {{
                background: {colors['bg_main']};
                color: {colors['text_primary']};
            }}
            QLabel {{
                color: {colors['text_primary']};
            }}
            QTextEdit {{
                background: {colors['bg_secondary']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_light']};
                border-radius: 4px;
                padding: 5px;
            }}
            QTextEdit:read-only {{
                background: {colors['bg_secondary']};
            }}
            QPushButton {{
                background: {colors['accent_primary']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background: {colors['accent_hover']};
            }}
            QPushButton:pressed {{
                background: {colors['accent_pressed']};
            }}
            QPushButton:disabled {{
                background: {colors['border_light']};
                color: {colors['text_secondary']};
            }}
            QProgressBar {{
                border: 1px solid {colors['border_light']};
                border-radius: 4px;
                text-align: center;
                background: {colors['bg_secondary']};
            }}
            QProgressBar::chunk {{
                background: {colors['accent_primary']};
            }}
            QTabWidget::pane {{
                border: 1px solid {colors['border_light']};
                background: {colors['bg_main']};
            }}
            QTabBar::tab {{
                background: {colors['bg_secondary']};
                color: {colors['text_primary']};
                padding: 8px 16px;
                border: 1px solid {colors['border_light']};
                border-bottom: none;
            }}
            QTabBar::tab:selected {{
                background: {colors['accent_primary']};
                color: white;
            }}
            QCheckBox {{
                color: {colors['text_primary']};
                spacing: 8px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {colors['border_light']};
                border-radius: 3px;
                background: {colors['bg_secondary']};
            }}
            QCheckBox::indicator:checked {{
                background: {colors['accent_primary']};
                border-color: {colors['accent_primary']};
            }}
            QScrollArea {{
                border: none;
                background: {colors['bg_main']};
            }}
        """)
