"""
Dialog szybkich odpowiedzi AI dla ProMail

Funkcjonalność:
- Wyświetlanie treści otrzymanego emaila (readonly)
- Edycja promptu podstawowego
- Edycja promptu dodatkowego  
- Tabela źródeł prawdy z checkboxami
- Generowanie odpowiedzi za pomocą AI
- Kopiowanie/wstawianie wygenerowanej odpowiedzi

Autor: PRO-Ka-Po_Kaizen_Freak
Data: 2025-11-11
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTextEdit,
    QTreeWidget,
    QTreeWidgetItem,
    QMessageBox,
    QWidget,
    QFrame,
    QSplitter,
    QProgressBar,
    QApplication,
    QCheckBox,
)

try:
    from src.utils.theme_manager import get_theme_manager
    from src.Modules.AI_module.promail_ai_connector import get_promail_ai_connector
    from .truth_sources_dialog import TruthSourcesDialog
except ImportError:
    get_theme_manager = None
    get_promail_ai_connector = None
    TruthSourcesDialog = None


class AIGenerationThread(QThread):
    """Wątek do generowania odpowiedzi AI w tle"""
    
    finished = pyqtSignal(bool, str, dict)  # success, response, metadata
    progress = pyqtSignal(int)  # progress percentage
    
    def __init__(
        self,
        email_content: str,
        base_prompt: str,
        additional_prompt: str,
        truth_sources: List[str],
        email_context: Optional[Dict[str, Any]] = None,
        include_thread: bool = False,
        thread_emails: Optional[List[Dict]] = None
    ):
        super().__init__()
        self.email_content = email_content
        self.base_prompt = base_prompt
        self.additional_prompt = additional_prompt
        self.truth_sources = truth_sources
        self.email_context = email_context
        self.include_thread = include_thread
        self.thread_emails = thread_emails or []
        
    def run(self):
        """Wykonuje generowanie w tle"""
        try:
            self.progress.emit(10)
            
            # Przygotuj pełną treść z wątkiem jeśli zaznaczono
            full_content = self.email_content
            if self.include_thread and self.thread_emails:
                self.progress.emit(20)
                thread_text = self._build_thread_context()
                full_content = f"{thread_text}\n\n{'='*50}\nNAJNOWSZA WIADOMOŚĆ:\n{self.email_content}"
            
            self.progress.emit(40)
            
            connector = get_promail_ai_connector()
            
            self.progress.emit(60)
            
            success, response, metadata = connector.generate_quick_response(
                email_content=full_content,
                base_prompt=self.base_prompt,
                additional_prompt=self.additional_prompt if self.additional_prompt.strip() else None,
                truth_sources=self.truth_sources if self.truth_sources else None,
                email_context=self.email_context
            )
            
            self.progress.emit(100)
            self.finished.emit(success, response, metadata)
        except Exception as e:
            self.finished.emit(False, f"Error: {str(e)}", {})
    
    def _build_thread_context(self) -> str:
        """Buduje kontekst konwersacji z wątku"""
        if not self.thread_emails:
            return ""
        
        lines = ["KONTEKST KONWERSACJI (wątek emaili):"]
        lines.append("="*50)
        
        for i, email_data in enumerate(self.thread_emails, 1):
            lines.append(f"\n--- Email #{i} ---")
            if email_data.get("from"):
                lines.append(f"Od: {email_data['from']}")
            if email_data.get("to"):
                lines.append(f"Do: {email_data['to']}")
            if email_data.get("date"):
                lines.append(f"Data: {email_data['date']}")
            if email_data.get("subject"):
                lines.append(f"Temat: {email_data['subject']}")
            lines.append("")
            lines.append(email_data.get("content", ""))
            lines.append("")
        
        return "\n".join(lines)


class AIQuickResponseDialog(QDialog):
    """Dialog do generowania szybkich odpowiedzi AI na emaile"""
    
    response_generated = pyqtSignal(str, dict)  # response, email_context
    
    def __init__(
        self, 
        email_content: str,
        email_context: Optional[Dict[str, Any]] = None,
        thread_emails: Optional[List[Dict]] = None,
        parent=None
    ):
        """
        Args:
            email_content: Treść emaila do odpowiedzi
            email_context: Kontekst emaila (from, to, subject, date)
            thread_emails: Lista emaili z wątku (dla kontekstu)
            parent: Widget rodzica
        """
        super().__init__(parent)
        
        self.email_content = email_content
        self.email_context = email_context or {}
        self.thread_emails = thread_emails or []
        self.generated_response = ""
        
        self.theme_manager = get_theme_manager() if get_theme_manager else None
        self.sources_file = Path("mail_client/ai_truth_sources.json")
        self.sources = self._load_sources()
        
        self.generation_thread: Optional[AIGenerationThread] = None
        
        self.init_ui()
        self.refresh_truth_tree()
        
    def init_ui(self):
        """Inicjalizuje interfejs użytkownika"""
        self.setWindowTitle("🪄 Szybka odpowiedź AI")
        self.setMinimumSize(900, 700)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(12)
        
        # Nagłówek
        header = self._create_header()
        layout.addWidget(header)
        
        # Główny splitter (pionowy)
        main_splitter = QSplitter(Qt.Orientation.Vertical)
        
        # === SEKCJA 1: Treść emaila ===
        email_section = self._create_email_section()
        main_splitter.addWidget(email_section)
        
        # === SEKCJA 2: Prompty ===
        prompts_section = self._create_prompts_section()
        main_splitter.addWidget(prompts_section)
        
        # === SEKCJA 3: Źródła prawdy ===
        truth_section = self._create_truth_section()
        main_splitter.addWidget(truth_section)
        
        # Proporcje sekcji (bez sekcji odpowiedzi - auto-otwieranie okna)
        main_splitter.setSizes([150, 250, 200])
        layout.addWidget(main_splitter)
        
        # Progress bar (ukryty początkowo)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setRange(0, 100)  # 0-100%
        self.progress_bar.setTextVisible(True)
        layout.addWidget(self.progress_bar)
        
        # Przyciski akcji
        actions = self._create_actions()
        layout.addWidget(actions)
        
        self.setLayout(layout)
        self.apply_theme()
        
    def _create_header(self) -> QWidget:
        """Tworzy nagłówek dialogu"""
        header = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 10)
        
        title = QLabel("🪄 Generowanie odpowiedzi AI")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title.setFont(font)
        
        # Kontekst emaila
        context_text = []
        if self.email_context.get("from"):
            context_text.append(f"Od: {self.email_context['from']}")
        if self.email_context.get("subject"):
            context_text.append(f"Temat: {self.email_context['subject']}")
        
        if context_text:
            context_label = QLabel(" | ".join(context_text))
            context_label.setStyleSheet("color: gray; font-size: 10pt;")
        else:
            context_label = None
        
        header_layout.addWidget(title)
        header_layout.addStretch()
        if context_label:
            header_layout.addWidget(context_label)
        
        header.setLayout(header_layout)
        return header
        
    def _create_email_section(self) -> QWidget:
        """Tworzy sekcję z treścią emaila"""
        section = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        label = QLabel("📧 Treść wiadomości:")
        font = QFont()
        font.setBold(True)
        label.setFont(font)
        layout.addWidget(label)
        
        self.email_text = QTextEdit()
        self.email_text.setPlainText(self.email_content)
        self.email_text.setReadOnly(True)
        self.email_text.setMaximumHeight(150)
        layout.addWidget(self.email_text)
        
        section.setLayout(layout)
        return section
        
    def _create_prompts_section(self) -> QWidget:
        """Tworzy sekcję z promptami"""
        section = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # Prompt podstawowy
        base_label = QLabel("🎯 Prompt podstawowy:")
        font = QFont()
        font.setBold(True)
        base_label.setFont(font)
        layout.addWidget(base_label)
        
        self.base_prompt = QTextEdit()
        self.base_prompt.setPlainText(
            "Jesteś profesjonalnym asystentem email. "
            "Przeanalizuj poniższą wiadomość i wygeneruj odpowiednią, uprzejmą i zwięzłą odpowiedź. "
            "Dostosuj ton do kontekstu wiadomości."
        )
        self.base_prompt.setMaximumHeight(80)
        layout.addWidget(self.base_prompt)
        
        # Prompt dodatkowy
        additional_label = QLabel("✏️ Prompt dodatkowy (opcjonalny):")
        additional_label.setFont(font)
        layout.addWidget(additional_label)
        
        desc = QLabel("Dodaj własne instrukcje, np. styl odpowiedzi, konkretne informacje do uwzględnienia, język, itp.")
        desc.setStyleSheet("color: gray; font-size: 9pt;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        self.additional_prompt = QTextEdit()
        self.additional_prompt.setPlaceholderText("Np.: Odpowiedź w formie krótkiej listy punktów. Użyj formalnego tonu.")
        self.additional_prompt.setMaximumHeight(60)
        layout.addWidget(self.additional_prompt)
        
        section.setLayout(layout)
        return section
        
    def _create_truth_section(self) -> QWidget:
        """Tworzy sekcję ze źródłami prawdy"""
        section = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Nagłówek z przyciskiem zarządzania
        header_layout = QHBoxLayout()
        
        label = QLabel("📚 Źródła prawdy (kontekst dla AI):")
        font = QFont()
        font.setBold(True)
        label.setFont(font)
        header_layout.addWidget(label)
        
        header_layout.addStretch()
        
        self.btn_manage_sources = QPushButton("⚙️ Zarządzaj")
        self.btn_manage_sources.clicked.connect(self._manage_truth_sources)
        header_layout.addWidget(self.btn_manage_sources)
        
        layout.addLayout(header_layout)
        
        desc = QLabel("Zaznacz pliki, które mają być wysłane jako kontekst do AI")
        desc.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(desc)
        
        # Drzewo źródeł prawdy
        self.truth_tree = QTreeWidget()
        self.truth_tree.setHeaderLabels(["Nazwa", "Typ"])
        self.truth_tree.setColumnWidth(0, 300)
        self.truth_tree.setMaximumHeight(120)
        self.truth_tree.itemChanged.connect(self._on_truth_item_checked)
        layout.addWidget(self.truth_tree)
        
        # Statystyki
        self.truth_stats = QLabel()
        self.truth_stats.setStyleSheet("color: gray; font-size: 9pt;")
        layout.addWidget(self.truth_tree)
        
        # Checkbox załączania wątku
        self.include_thread_checkbox = QCheckBox(
            f"📎 Załącz całą konwersację z wątku ({len(self.thread_emails)} emaili)"
        )
        self.include_thread_checkbox.setEnabled(len(self.thread_emails) > 0)
        if len(self.thread_emails) > 0:
            self.include_thread_checkbox.setToolTip(
                "AI otrzyma pełny kontekst konwersacji, co pozwoli na lepsze zrozumienie sytuacji"
            )
        else:
            self.include_thread_checkbox.setToolTip("Brak innych emaili w wątku")
        layout.addWidget(self.include_thread_checkbox)
        
        section.setLayout(layout)
        return section
        
    def _create_actions(self) -> QWidget:
        """Tworzy przyciski akcji"""
        actions = QWidget()
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 10, 0, 0)
        layout.setSpacing(8)
        
        layout.addStretch()
        
        self.btn_generate = QPushButton("🪄 Generuj")
        self.btn_generate.clicked.connect(self._generate_response)
        self.btn_generate.setMinimumHeight(35)
        self.btn_generate.setMinimumWidth(120)
        layout.addWidget(self.btn_generate)
        
        self.btn_cancel = QPushButton("❌ Anuluj")
        self.btn_cancel.clicked.connect(self.reject)
        self.btn_cancel.setMinimumHeight(35)
        self.btn_cancel.setMinimumWidth(120)
        layout.addWidget(self.btn_cancel)
        
        actions.setLayout(layout)
        return actions
        
    def _load_sources(self) -> Dict[str, Any]:
        """Wczytuje źródła prawdy"""
        if self.sources_file.exists():
            try:
                with open(self.sources_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {"folders": [], "files": []}
        return {"folders": [], "files": []}
        
    def refresh_truth_tree(self):
        """Odświeża drzewo źródeł prawdy"""
        self.truth_tree.clear()
        self.truth_tree.itemChanged.disconnect(self._on_truth_item_checked)
        
        # Dodaj foldery i pliki
        folder_items = {}
        for folder in self.sources.get("folders", []):
            if not folder.get("parent"):
                item = QTreeWidgetItem([folder["name"], "Folder"])
                item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
                item.setCheckState(0, Qt.CheckState.Checked if folder.get("checked", False) else Qt.CheckState.Unchecked)
                item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": folder["name"]})
                font = item.font(0)
                font.setBold(True)
                item.setFont(0, font)
                self.truth_tree.addTopLevelItem(item)
                folder_items[folder["name"]] = item
        
        # Dodaj pliki
        for file_data in self.sources.get("files", []):
            file_path = Path(file_data["path"])
            file_type = file_path.suffix.upper().replace(".", "") or "FILE"
            
            item = QTreeWidgetItem([file_data["name"], file_type])
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(0, Qt.CheckState.Checked if file_data.get("checked", False) else Qt.CheckState.Unchecked)
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "path": file_data["path"]})
            
            folder_name = file_data.get("folder", "")
            if folder_name and folder_name in folder_items:
                folder_items[folder_name].addChild(item)
            else:
                self.truth_tree.addTopLevelItem(item)
        
        self.truth_tree.expandAll()
        self.truth_tree.itemChanged.connect(self._on_truth_item_checked)
        self._update_truth_stats()
        
    def _on_truth_item_checked(self, item: QTreeWidgetItem, column: int):
        """Obsługuje zmianę stanu checkboxa źródła prawdy"""
        if column != 0:
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        checked = item.checkState(0) == Qt.CheckState.Checked
        
        if data["type"] == "folder":
            # Zaznacz/odznacz wszystkie dzieci
            for i in range(item.childCount()):
                child = item.child(i)
                child.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
        
        self._update_truth_stats()
        
    def _update_truth_stats(self):
        """Aktualizuje statystyki źródeł prawdy"""
        checked = self._get_checked_files()
        total = len(self.sources.get("files", []))
        self.truth_stats.setText(f"Zaznaczono: {len(checked)}/{total} plików")
        
    def _get_checked_files(self) -> List[str]:
        """Zwraca listę zaznaczonych plików"""
        checked_files = []
        
        def check_item(item: QTreeWidgetItem):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if data and data["type"] == "file":
                if item.checkState(0) == Qt.CheckState.Checked:
                    checked_files.append(data["path"])
            
            for i in range(item.childCount()):
                check_item(item.child(i))
        
        for i in range(self.truth_tree.topLevelItemCount()):
            check_item(self.truth_tree.topLevelItem(i))
        
        return checked_files
        
    def _manage_truth_sources(self):
        """Otwiera dialog zarządzania źródłami prawdy"""
        if not TruthSourcesDialog:
            QMessageBox.warning(self, "Błąd", "Dialog zarządzania źródłami prawdy jest niedostępny")
            return
        
        dialog = TruthSourcesDialog(self.sources_file, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.sources = self._load_sources()
            self.refresh_truth_tree()
            
    def _generate_response(self):
        """Generuje odpowiedź AI"""
        if not get_promail_ai_connector:
            QMessageBox.warning(self, "Błąd", "Konektor AI nie jest dostępny")
            return
        
        # Pobierz dane
        base_prompt = self.base_prompt.toPlainText().strip()
        additional_prompt = self.additional_prompt.toPlainText().strip()
        truth_sources = self._get_checked_files()
        include_thread = self.include_thread_checkbox.isChecked()
        
        if not base_prompt:
            QMessageBox.warning(self, "Błąd", "Prompt podstawowy nie może być pusty")
            return
        
        # Zablokuj interfejs
        self.btn_generate.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 100)  # Progress bar z wartościami
        
        # Uruchom generowanie w tle
        self.generation_thread = AIGenerationThread(
            email_content=self.email_content,
            base_prompt=base_prompt,
            additional_prompt=additional_prompt,
            truth_sources=truth_sources,
            email_context=self.email_context,
            include_thread=include_thread,
            thread_emails=self.thread_emails if include_thread else None
        )
        self.generation_thread.progress.connect(self.progress_bar.setValue)
        self.generation_thread.finished.connect(self._on_generation_finished)
        self.generation_thread.start()
        
    def _on_generation_finished(self, success: bool, response: str, metadata: Dict[str, Any]):
        """Obsługuje zakończenie generowania"""
        self.btn_generate.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        if success:
            # Sukces - przygotuj kontekst dla odpowiedzi i emituj sygnał
            self.generated_response = response
            
            # Przygotuj kontekst dla nowej wiadomości (odpowiedź)
            reply_context = {
                "from": self.email_context.get("to", ""),  # Odwrócone
                "to": self.email_context.get("from", ""),
                "subject": f"Re: {self.email_context.get('subject', '')}",
                "in_reply_to": self.email_context.get("message_id", ""),
                "ai_metadata": metadata,
                "body": response  # Wygenerowana treść
            }
            
            # Emituj sygnał i zamknij dialog
            self.response_generated.emit(response, reply_context)
            self.accept()  # Zamyka dialog
        else:
            # Błąd - pokaż komunikat
            QMessageBox.critical(
                self, 
                "Błąd generowania", 
                f"Nie udało się wygenerować odpowiedzi:\n\n{response}"
            )
            
    def apply_theme(self):
        """Aplikuje motyw"""
        if not self.theme_manager:
            return
        
        colors = self.theme_manager.get_current_colors()
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {colors.get('bg_main', '#ffffff')};
                color: {colors.get('text_primary', '#000000')};
            }}
            QTextEdit {{
                background-color: {colors.get('bg_secondary', '#f5f5f5')};
                border: 1px solid {colors.get('border_light', '#e0e0e0')};
                border-radius: 4px;
                padding: 5px;
            }}
            QTextEdit[readOnly="true"] {{
                background-color: {colors.get('disabled_bg', '#f0f0f0')};
            }}
            QTreeWidget {{
                background-color: {colors.get('bg_secondary', '#f5f5f5')};
                border: 1px solid {colors.get('border_light', '#e0e0e0')};
                border-radius: 4px;
            }}
            QPushButton {{
                background-color: {colors.get('accent_primary', '#2196F3')};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors.get('accent_hover', '#1976D2')};
            }}
            QPushButton:disabled {{
                background-color: {colors.get('disabled_bg', '#cccccc')};
                color: {colors.get('disabled_text', '#999999')};
            }}
        """)


if __name__ == "__main__":
    """Test dialogu"""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    
    email_content = """Dzień dobry,

Czy moglibyśmy umówić się na spotkanie w przyszłym tygodniu, aby omówić projekt?

Pozdrawiam,
Jan Kowalski"""
    
    email_context = {
        "from": "jan.kowalski@example.com",
        "subject": "Spotkanie - omówienie projektu",
        "date": "2025-11-11"
    }
    
    dialog = AIQuickResponseDialog(email_content, email_context)
    dialog.response_generated.connect(lambda resp: print(f"Generated: {resp}"))
    dialog.show()
    
    sys.exit(app.exec())
