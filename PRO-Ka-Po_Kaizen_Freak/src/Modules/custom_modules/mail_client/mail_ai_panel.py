"""
Moduł panelu sztucznej inteligencji dla klienta email

Funkcjonalność:
- Generowanie odpowiedzi email za pomocą AI
- Konfiguracja promptów (podstawowy i własny)
- Załączanie kontekstu (konwersacje, maile, pliki)
- Zarządzanie źródłami prawdy (pliki PDF, TXT) przez dedykowany dialog

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-11
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QCheckBox,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QProgressBar,
)

try:
    from ...AI_module.promail_ai_connector import get_promail_ai_connector
    from .truth_sources_dialog import TruthSourcesDialog
except ImportError:
    try:
        from src.Modules.AI_module.promail_ai_connector import get_promail_ai_connector
        from src.Modules.custom_modules.mail_client.truth_sources_dialog import TruthSourcesDialog
    except ImportError:
        # Fallback dla testów
        get_promail_ai_connector = None
        TruthSourcesDialog = None


class TruthSourcesManager:
    """Prosty manager do dostępu do źródeł prawdy"""
    
    def __init__(self, sources_file: Optional[Path] = None):
        # Resolve sources file using packaging-aware helper when possible
        if sources_file:
            self.sources_file = Path(sources_file)
        else:
            try:
                from src.utils.paths import resource_path
                self.sources_file = Path(resource_path('data', 'pro_mail_truth_sources.json'))
            except Exception:
                # Fallback for tests or when src package isn't available on sys.path
                self.sources_file = Path("data/pro_mail_truth_sources.json")

        self.sources = self._load_sources()
    
    def _load_sources(self) -> Dict[str, Any]:
        """Wczytuje źródła prawdy z pliku"""
        if self.sources_file.exists():
            try:
                with open(self.sources_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {"folders": [], "files": []}
        return {"folders": [], "files": []}
    
    def reload(self):
        """Przeładowuje źródła z pliku"""
        self.sources = self._load_sources()
    
    def get_checked_files(self) -> List[str]:
        """Zwraca ścieżki zaznaczonych plików"""
        checked = []
        for file_data in self.sources.get("files", []):
            if file_data.get("checked", False):
                checked.append(file_data["path"])
        return checked


class AIGenerationThread(QThread):
    """Wątek do generowania odpowiedzi AI w tle"""
    finished = pyqtSignal(bool, str, dict)  # (success, text, metadata)
    progress = pyqtSignal(int)  # 0-100
    
    def __init__(self, connector, email_content, config, email_context=None):
        super().__init__()
        self.connector = connector
        self.email_content = email_content
        self.config = config
        self.email_context = email_context
    
    def run(self):
        """Wykonuje generowanie w tle"""
        try:
            self.progress.emit(25)
            
            # Wywołaj connector AI
            success, result, metadata = self.connector.generate_quick_response(
                email_content=self.email_content,
                base_prompt=self.config.get("base_prompt"),
                additional_prompt=self.config.get("custom_prompt"),
                truth_sources=self.config.get("truth_sources", []),
                email_context=self.email_context
            )
            
            self.progress.emit(100)
            self.finished.emit(success, result, metadata)
            
        except Exception as e:
            self.progress.emit(100)
            self.finished.emit(False, f"Błąd generowania: {str(e)}", {})


class AIPanel(QWidget):
    """Panel AI w oknie nowej wiadomości"""
    
    response_generated = pyqtSignal(str)  # Emituje wygenerowaną odpowiedź
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.truth_manager = TruthSourcesManager()
        self.ai_connector = get_promail_ai_connector() if get_promail_ai_connector else None
        self.generation_thread = None
        self.init_ui()
        self.refresh_truth_sources()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(8)
        
        # Nagłówek
        header_label = QLabel("🤖 Asystent AI")
        header_label.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        layout.addWidget(header_label)
        
        # Sekcja 1: Prompt podstawowy
        layout.addWidget(QLabel("Prompt podstawowy:"))
        self.base_prompt = QTextEdit()
        self.base_prompt.setPlainText("Przygotuj profesjonalną odpowiedź na poniższą wiadomość email.")
        self.base_prompt.setMaximumHeight(60)
        layout.addWidget(self.base_prompt)
        
        # Sekcja 2: Prompt własny
        layout.addWidget(QLabel("Dodatkowe instrukcje:"))
        self.custom_prompt = QTextEdit()
        self.custom_prompt.setPlaceholderText("np. 'Odpowiedź powinna być zwięzła i merytoryczna...'")
        self.custom_prompt.setMaximumHeight(80)
        layout.addWidget(self.custom_prompt)
        
        # Sekcja 3: Checkboxy kontekstu
        layout.addWidget(QLabel("Załącz do kontekstu:"))
        
        self.attach_conversation_cb = QCheckBox("Załącz całą konwersację")
        self.attach_conversation_cb.setToolTip("Dołącz wszystkie wiadomości z wątku")
        layout.addWidget(self.attach_conversation_cb)
        
        self.attach_all_mails_cb = QCheckBox("Załącz wszystkie maile")
        self.attach_all_mails_cb.setToolTip("Dołącz wszystkie maile z folderu")
        layout.addWidget(self.attach_all_mails_cb)
        
        self.attach_files_cb = QCheckBox("Załącz pliki z wiadomości")
        self.attach_files_cb.setToolTip("Dołącz załączniki z wiadomości jako kontekst")
        layout.addWidget(self.attach_files_cb)
        
        # Separator
        separator = QLabel()
        separator.setStyleSheet("background-color: #ccc; margin: 5px 0;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Sekcja 4: Źródła prawdy
        truth_header = QHBoxLayout()
        truth_label = QLabel("📚 Źródła prawdy:")
        truth_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        truth_header.addWidget(truth_label)
        
        manage_sources_btn = QPushButton("⚙️ Zarządzaj")
        manage_sources_btn.setToolTip("Otwórz dialog zarządzania źródłami prawdy")
        manage_sources_btn.setMaximumWidth(100)
        manage_sources_btn.clicked.connect(self.open_truth_sources_dialog)
        truth_header.addWidget(manage_sources_btn)
        
        layout.addLayout(truth_header)
        
        # Lista zaznaczonych źródeł
        self.truth_list = QLabel("Brak zaznaczonych źródeł")
        self.truth_list.setStyleSheet("padding: 5px; background-color: #f5f5f5; border-radius: 3px; font-size: 9pt;")
        self.truth_list.setWordWrap(True)
        self.truth_list.setMaximumHeight(80)
        layout.addWidget(self.truth_list)
        
        # Progress bar (ukryty domyślnie)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)
        
        # Przycisk generowania
        self.generate_btn = QPushButton("✨ Generuj odpowiedź AI")
        self.generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 10px;
                border-radius: 4px;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #cccccc;
                color: #666666;
            }
        """)
        self.generate_btn.clicked.connect(self.generate_response)
        layout.addWidget(self.generate_btn)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)
        
        layout.addStretch()
        self.setLayout(layout)
    
    def open_truth_sources_dialog(self):
        """Otwiera dialog zarządzania źródłami prawdy"""
        if not TruthSourcesDialog:
            QMessageBox.warning(self, "Błąd", "Dialog źródeł prawdy nie jest dostępny")
            return
        
        dialog = TruthSourcesDialog(sources_file=self.truth_manager.sources_file, parent=self)
        if dialog.exec():
            # Przeładuj źródła po zamknięciu dialogu
            self.truth_manager.reload()
            self.refresh_truth_sources()
    
    def refresh_truth_sources(self):
        """Odświeża listę zaznaczonych źródeł prawdy"""
        checked_files = self.truth_manager.get_checked_files()
        
        if not checked_files:
            self.truth_list.setText("Brak zaznaczonych źródeł")
        else:
            file_names = [os.path.basename(f) for f in checked_files[:5]]
            text = "\n".join([f"✓ {name}" for name in file_names])
            if len(checked_files) > 5:
                text += f"\n... i {len(checked_files) - 5} więcej"
            self.truth_list.setText(text)
    
    def generate_response(self):
        """Generuje odpowiedź AI"""
        # Sprawdź czy AI connector jest dostępny
        if not self.ai_connector:
            QMessageBox.warning(
                self,
                "Błąd konfiguracji",
                "Moduł AI nie jest dostępny. Upewnij się że aplikacja jest poprawnie zainstalowana."
            )
            return
        
        # Pobierz treść emaila do odpowiedzi
        email_content = self._get_email_content()
        if not email_content:
            QMessageBox.warning(
                self,
                "Brak kontekstu",
                "Nie można znaleźć wiadomości do odpowiedzi. Upewnij się że odpowiadasz na istniejącą wiadomość."
            )
            return
        
        # Zbierz konfigurację
        config = self.get_ai_config()
        
        # Zbierz kontekst email (nadawca, temat, itp.)
        email_context = self._build_email_context()
        
        # Wyłącz przycisk i pokaż progress
        self.generate_btn.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        self.status_label.setText("🔄 Generowanie odpowiedzi...")
        
        # Uruchom wątek generowania
        self.generation_thread = AIGenerationThread(
            connector=self.ai_connector,
            email_content=email_content,
            config=config,
            email_context=email_context
        )
        self.generation_thread.progress.connect(self._on_progress)
        self.generation_thread.finished.connect(self._on_generation_finished)
        self.generation_thread.start()
    
    def _get_email_content(self) -> str:
        """Pobiera treść emaila do odpowiedzi"""
        if not self.parent_window:
            return ""
        
        # Jeśli jest to odpowiedź, pobierz treść oryginalnej wiadomości
        if hasattr(self.parent_window, 'reply_to') and self.parent_window.reply_to:
            mail = self.parent_window.reply_to
            return mail.get('Body', '')
        
        # W przeciwnym razie sprawdź czy jest jakikolwiek mail
        if hasattr(self.parent_window, 'forward') and self.parent_window.forward:
            return self.parent_window.forward.get('Body', '')
        
        return ""
    
    def _build_email_context(self) -> Optional[Dict[str, Any]]:
        """Buduje kontekst emaila"""
        if not self.parent_window:
            return None
        
        context = {}
        
        # Pobierz informacje z reply_to lub forward
        source_mail = None
        if hasattr(self.parent_window, 'reply_to') and self.parent_window.reply_to:
            source_mail = self.parent_window.reply_to
            context['type'] = 'reply'
        elif hasattr(self.parent_window, 'forward') and self.parent_window.forward:
            source_mail = self.parent_window.forward
            context['type'] = 'forward'
        
        if source_mail:
            context['sender'] = source_mail.get('From', '')
            context['subject'] = source_mail.get('Subject', '')
            context['date'] = source_mail.get('Date', '')
            context['to'] = source_mail.get('To', '')
        
        # Dodaj informacje z formularza
        if hasattr(self.parent_window, 'to_input'):
            context['recipient'] = self.parent_window.to_input.text()
        if hasattr(self.parent_window, 'subject_input'):
            context['subject_reply'] = self.parent_window.subject_input.text()
        
        return context if context else None
    
    def _on_progress(self, value: int):
        """Aktualizuje progress bar"""
        self.progress_bar.setValue(value)
    
    def _on_generation_finished(self, success: bool, text: str, metadata: dict):
        """Obsługuje zakończenie generowania"""
        # Włącz przycisk i ukryj progress
        self.generate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            # Wstaw wygenerowaną odpowiedź do body
            if hasattr(self.parent_window, 'body_input'):
                self.parent_window.body_input.setPlainText(text)
            
            # Aktualizuj status
            provider = metadata.get('provider', 'AI')
            model = metadata.get('model', '')
            tokens = metadata.get('tokens_used', 0)
            self.status_label.setText(
                f"✅ Odpowiedź wygenerowana ({provider} {model}, {tokens} tokenów)"
            )
            
            # Emituj sygnał
            self.response_generated.emit(text)
        else:
            # Pokaż błąd
            self.status_label.setText(f"❌ Błąd: {text}")
            QMessageBox.critical(
                self,
                "Błąd generowania",
                f"Nie udało się wygenerować odpowiedzi:\n\n{text}"
            )
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Zwraca konfigurację AI"""
        checked_files = self.truth_manager.get_checked_files()
        
        return {
            "base_prompt": self.base_prompt.toPlainText(),
            "custom_prompt": self.custom_prompt.toPlainText(),
            "attach_conversation": self.attach_conversation_cb.isChecked(),
            "attach_all_mails": self.attach_all_mails_cb.isChecked(),
            "attach_files": self.attach_files_cb.isChecked(),
            "truth_sources": checked_files
        }
