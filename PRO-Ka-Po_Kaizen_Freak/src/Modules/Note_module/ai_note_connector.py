"""
AI Note Connector - Integracja AI z modułem notatek
Zapewnia funkcjonalność podsumowań AI i własnych promptów dla notatek
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QRadioButton,
    QLineEdit, QComboBox, QPushButton, QTextEdit,
    QLabel, QButtonGroup, QProgressBar, QMessageBox,
    QWidget
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor
from typing import Optional
import logging

from src.Modules.AI_module.ai_logic import AIManager, AIProvider, AIResponse


class AIGenerationThread(QThread):
    """Wątek do asynchronicznego generowania odpowiedzi AI"""
    
    finished = pyqtSignal(object)  # AIResponse
    error = pyqtSignal(str)
    
    def __init__(self, ai_manager: AIManager, prompt: str, model: Optional[str] = None):
        super().__init__()
        self.ai_manager = ai_manager
        self.prompt = prompt
        self.model = model
        self.logger = logging.getLogger("AIGenerationThread")
    
    def run(self):
        """Wykonuje generowanie w osobnym wątku"""
        try:
            # Jeśli określono model, tymczasowo go ustaw
            if self.model:
                current_config = self.ai_manager._config
                if current_config:
                    # Zachowaj oryginalne ustawienia
                    original_model = current_config.model
                    current_config.model = self.model
                    
                    response = self.ai_manager.generate(self.prompt, use_cache=False)
                    
                    # Przywróć oryginalny model
                    current_config.model = original_model
                else:
                    response = self.ai_manager.generate(self.prompt, use_cache=False)
            else:
                response = self.ai_manager.generate(self.prompt, use_cache=False)
            
            if response.error:
                self.error.emit(response.error)
            else:
                self.finished.emit(response)
                
        except Exception as e:
            self.logger.error(f"AI generation error: {e}")
            self.error.emit(str(e))


class AIPromptDialog(QDialog):
    """Dialog do wyboru typu podsumowania i modelu AI"""
    
    def __init__(self, ai_manager: AIManager, note_content: str, i18n, parent=None):
        super().__init__(parent)
        self.ai_manager = ai_manager
        self.note_content = note_content
        self.i18n = i18n
        self.selected_action = None
        self.selected_model = None
        self.custom_prompt_text = ""
        
        self.setWindowTitle(self.i18n.t("notes.ai_dialog_title", "Podsumowanie AI"))
        self.setMinimumWidth(500)
        self.setup_ui()
    
    def setup_ui(self):
        """Tworzy interfejs dialogu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === Wybór typu akcji ===
        action_label = QLabel(self.i18n.t("notes.ai_action_type", "Wybierz akcję:"))
        action_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(action_label)
        
        # Radio buttons
        self.action_group = QButtonGroup(self)
        
        self.summarize_radio = QRadioButton(
            self.i18n.t("notes.ai_summarize", "Podsumuj notatkę")
        )
        self.summarize_radio.setChecked(True)
        self.action_group.addButton(self.summarize_radio, 0)
        layout.addWidget(self.summarize_radio)
        
        self.custom_radio = QRadioButton(
            self.i18n.t("notes.ai_custom_prompt", "Własny prompt")
        )
        self.action_group.addButton(self.custom_radio, 1)
        layout.addWidget(self.custom_radio)
        
        # Pole na własny prompt
        self.custom_prompt_input = QLineEdit()
        self.custom_prompt_input.setPlaceholderText(
            self.i18n.t("notes.ai_custom_prompt_placeholder", 
                       "Wpisz własne polecenie dla AI...")
        )
        self.custom_prompt_input.setEnabled(False)
        layout.addWidget(self.custom_prompt_input)
        
        # Połącz zmianę radio buttonów z włączeniem/wyłączeniem pola
        self.custom_radio.toggled.connect(self.custom_prompt_input.setEnabled)
        
        # === Wybór modelu ===
        model_label = QLabel(self.i18n.t("notes.ai_select_model", "Wybierz model:"))
        model_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        layout.addWidget(model_label)
        
        self.model_combo = QComboBox()
        self.populate_models()
        layout.addWidget(self.model_combo)
        
        # === Przyciski ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.ok_button = QPushButton(self.i18n.t("common.ok", "OK"))
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        buttons_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton(self.i18n.t("common.cancel", "Anuluj"))
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
    
    def populate_models(self):
        """Wypełnia listę dostępnych modeli"""
        try:
            models = self.ai_manager.get_available_models()
            
            if not models:
                # Brak modeli - pokaż domyślne
                current_provider = self.ai_manager.get_current_provider()
                if current_provider == AIProvider.GEMINI:
                    models = ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"]
                elif current_provider == AIProvider.OPENAI:
                    models = ["gpt-4o", "gpt-4-turbo-preview", "gpt-3.5-turbo"]
                elif current_provider == AIProvider.CLAUDE:
                    models = ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229"]
                else:
                    models = ["default"]
            
            for model in models:
                self.model_combo.addItem(model)
                
        except Exception as e:
            logging.getLogger("AIPromptDialog").error(f"Error loading models: {e}")
            self.model_combo.addItem("default")
    
    def accept(self):
        """Obsługuje zatwierdzenie dialogu"""
        # Sprawdź czy wybrano własny prompt i czy pole nie jest puste
        if self.custom_radio.isChecked():
            custom_text = self.custom_prompt_input.text().strip()
            if not custom_text:
                QMessageBox.warning(
                    self,
                    self.i18n.t("common.warning", "Ostrzeżenie"),
                    self.i18n.t("notes.ai_custom_prompt_empty", 
                               "Pole własnego promptu nie może być puste!")
                )
                return
            self.custom_prompt_text = custom_text
            self.selected_action = "custom"
        else:
            self.selected_action = "summarize"
        
        self.selected_model = self.model_combo.currentText()
        super().accept()


class AIResultDialog(QDialog):
    """Dialog wyświetlający wynik generowania AI z opcjami akcji"""
    
    def __init__(self, ai_response: AIResponse, i18n, parent=None):
        super().__init__(parent)
        self.ai_response = ai_response
        self.i18n = i18n
        self.selected_action = None
        
        self.setWindowTitle(
            self.i18n.t("notes.ai_result_title", "Wynik AI")
        )
        self.setMinimumSize(600, 400)
        self.setup_ui()
    
    def setup_ui(self):
        """Tworzy interfejs dialogu wyników"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Informacja o modelu i providerze
        info_label = QLabel(
            f"🤖 {self.ai_response.provider.value} | "
            f"Model: {self.ai_response.model}"
        )
        info_label.setStyleSheet("color: #666; font-size: 10px;")
        layout.addWidget(info_label)
        
        # Pole tekstowe z wynikiem
        self.result_text = QTextEdit()
        self.result_text.setPlainText(self.ai_response.text)
        self.result_text.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.result_text)
        
        # Przyciski akcji
        buttons_layout = QHBoxLayout()
        
        self.paste_button = QPushButton(
            self.i18n.t("notes.ai_paste_current", "Wklej do bieżącej")
        )
        self.paste_button.clicked.connect(lambda: self.select_action("paste"))
        buttons_layout.addWidget(self.paste_button)
        
        self.subchapter_button = QPushButton(
            self.i18n.t("notes.ai_create_subchapter", "Utwórz podrozdział")
        )
        self.subchapter_button.clicked.connect(lambda: self.select_action("subchapter"))
        buttons_layout.addWidget(self.subchapter_button)
        
        self.new_note_button = QPushButton(
            self.i18n.t("notes.ai_create_new", "Utwórz nowy notatnik")
        )
        self.new_note_button.clicked.connect(lambda: self.select_action("new_note"))
        buttons_layout.addWidget(self.new_note_button)
        
        buttons_layout.addStretch()
        
        self.cancel_button = QPushButton(
            self.i18n.t("common.cancel", "Anuluj")
        )
        self.cancel_button.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_button)
        
        layout.addLayout(buttons_layout)
    
    def select_action(self, action: str):
        """Wybiera akcję i zamyka dialog"""
        self.selected_action = action
        self.accept()
    
    def get_result_text(self) -> str:
        """Zwraca edytowalny tekst wyniku"""
        return self.result_text.toPlainText()


class AIProcessingDialog(QDialog):
    """Dialog pokazujący progress bar podczas generowania"""
    
    def __init__(self, i18n, parent=None):
        super().__init__(parent)
        self.i18n = i18n
        self.setWindowTitle(
            self.i18n.t("notes.ai_processing", "Przetwarzanie...")
        )
        self.setMinimumWidth(400)
        self.setModal(True)
        self.setup_ui()
    
    def setup_ui(self):
        """Tworzy interfejs z progress barem"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Label informacyjny
        self.info_label = QLabel(
            "🤖 " + self.i18n.t("notes.ai_generating", 
                               "Generowanie odpowiedzi AI...")
        )
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.info_label)
        
        # Progress bar (nieokreślony)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate progress
        layout.addWidget(self.progress_bar)
        
        # Opcjonalny przycisk anuluj (TODO: implementacja przerwania)
        # cancel_button = QPushButton(self.i18n.t("common.cancel", "Anuluj"))
        # cancel_button.clicked.connect(self.reject)
        # layout.addWidget(cancel_button)


def execute_ai_summarization(note_view, note_content: str, current_note_id: Optional[str] = None):
    """
    Główna funkcja wykonująca podsumowanie AI
    
    Args:
        note_view: Instancja NoteView
        note_content: Treść notatki do przetworzenia
        current_note_id: ID bieżącej notatki (opcjonalne)
    """
    from src.Modules.AI_module.ai_logic import get_ai_manager
    
    ai_manager = get_ai_manager()
    
    # Sprawdź czy AI jest skonfigurowane
    if ai_manager.get_current_provider() is None:
        QMessageBox.warning(
            note_view,
            note_view.i18n.t("common.warning", "Ostrzeżenie"),
            note_view.i18n.t("notes.ai_not_configured", 
                           "AI nie jest skonfigurowane. Przejdź do Ustawień → AI aby skonfigurować asystenta.")
        )
        return
    
    # Krok 1: Dialog wyboru akcji i modelu
    prompt_dialog = AIPromptDialog(ai_manager, note_content, note_view.i18n, note_view)
    
    if prompt_dialog.exec() != QDialog.DialogCode.Accepted:
        return  # Użytkownik anulował
    
    # Przygotuj prompt
    if prompt_dialog.selected_action == "summarize":
        # Usuń tagi HTML z treści
        import re
        clean_content = re.sub('<[^<]+?>', '', note_content)
        prompt_template = note_view.i18n.t(
            "notes.ai_summarize_prompt", 
            "Podsumuj następującą notatkę w sposób zwięzły i przejrzysty:"
        )
        prompt = f"{prompt_template}\n\n{clean_content}"
    else:
        # Własny prompt
        import re
        clean_content = re.sub('<[^<]+?>', '', note_content)
        note_content_label = note_view.i18n.t("notes.ai_note_content", "Treść notatki:")
        prompt = f"{prompt_dialog.custom_prompt_text}\n\n{note_content_label}\n{clean_content}"
    
    # Krok 2: Pokaż dialog przetwarzania
    processing_dialog = AIProcessingDialog(note_view.i18n, note_view)
    processing_dialog.show()
    
    # Krok 3: Utwórz i uruchom wątek generowania
    generation_thread = AIGenerationThread(
        ai_manager, 
        prompt, 
        prompt_dialog.selected_model
    )
    
    # Przechowuj referencję do wątku w note_view, aby nie został zniszczony
    note_view._ai_thread = generation_thread
    
    def cleanup_thread():
        """Cleanup po zakończeniu wątku"""
        if hasattr(note_view, '_ai_thread'):
            note_view._ai_thread.wait()  # Poczekaj na zakończenie
            note_view._ai_thread.deleteLater()
            delattr(note_view, '_ai_thread')
    
    def on_generation_finished(response: AIResponse):
        """Callback po zakończeniu generowania"""
        processing_dialog.close()
        
        # Krok 4: Pokaż dialog z wynikiem
        result_dialog = AIResultDialog(response, note_view.i18n, note_view)
        
        if result_dialog.exec() == QDialog.DialogCode.Accepted:
            result_text = result_dialog.get_result_text()
            action = result_dialog.selected_action
            
            # Wykonaj wybraną akcję
            if action == "paste":
                # Wklej do bieżącej notatki
                if current_note_id:
                    cursor = note_view.text_editor.textCursor()
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    ai_summary_heading = note_view.i18n.t("notes.ai_summary_heading", "Podsumowanie AI:")
                    cursor.insertHtml(f"<p><br></p><h3>{ai_summary_heading}</h3><p>{result_text}</p>")
                    note_view.text_editor.setTextCursor(cursor)
                    
            elif action == "subchapter":
                # Utwórz podrozdział
                if current_note_id:
                    ai_summary_title = note_view.i18n.t("notes.ai_summary_title", "Podsumowanie AI")
                    child_note_id = note_view.db.create_note(
                        title=ai_summary_title,
                        content=f"<p>{result_text}</p>",
                        parent_id=current_note_id,
                        color="#4CAF50"  # Zielony dla AI
                    )
                    note_view.refresh_tree()
                    note_view.select_note_in_tree(child_note_id)
                    
            elif action == "new_note":
                # Utwórz nową notatkę główną
                ai_summary_title = note_view.i18n.t("notes.ai_summary_title", "Podsumowanie AI")
                new_note_id = note_view.db.create_note(
                    title=ai_summary_title,
                    content=f"<p>{result_text}</p>",
                    color="#4CAF50"  # Zielony dla AI
                )
                note_view.refresh_tree()
                note_view.select_note_in_tree(new_note_id)
        
        # Cleanup wątku
        cleanup_thread()
    
    def on_generation_error(error_msg: str):
        """Callback w przypadku błędu"""
        processing_dialog.close()
        QMessageBox.critical(
            note_view,
            note_view.i18n.t("common.error", "Błąd"),
            note_view.i18n.t("notes.ai_summary_error", "❌ Błąd generowania podsumowania") + 
            f"\n\n{error_msg}"
        )
        
        # Cleanup wątku
        cleanup_thread()
    
    generation_thread.finished.connect(on_generation_finished)
    generation_thread.error.connect(on_generation_error)
    generation_thread.start()
