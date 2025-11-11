"""
Moduł panelu sztucznej inteligencji dla klienta email

Funkcjonalność:
- Generowanie odpowiedzi email za pomocą AI
- Konfiguracja promptów (podstawowy i własny)
- Załączanie kontekstu (konwersacje, maile, pliki)
- Zarządzanie źródłami prawdy (pliki PDF, TXT)

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-08
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt
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
)


class TruthSourcesManager:
    """Zarządza źródłami prawdy (pliki PDF, TXT)"""
    
    def __init__(self):
        self.sources_file = Path("mail_client/ai_truth_sources.json")
        self.sources_file.parent.mkdir(parents=True, exist_ok=True)
        self.sources = self.load_sources()
    
    def load_sources(self) -> Dict[str, Any]:
        """Wczytuje źródła prawdy z pliku"""
        if self.sources_file.exists():
            try:
                with open(self.sources_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {"folders": [], "files": []}
        return {"folders": [], "files": []}
    
    def save_sources(self):
        """Zapisuje źródła prawdy do pliku"""
        try:
            with open(self.sources_file, 'w', encoding='utf-8') as f:
                json.dump(self.sources, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving truth sources: {e}")
    
    def add_folder(self, name: str, parent: str = ""):
        """Dodaje folder"""
        folder = {
            "name": name,
            "parent": parent,
            "checked": False
        }
        self.sources["folders"].append(folder)
        self.save_sources()
    
    def add_file(self, path: str, folder: str = ""):
        """Dodaje plik"""
        file_entry = {
            "path": path,
            "name": os.path.basename(path),
            "folder": folder,
            "checked": False
        }
        self.sources["files"].append(file_entry)
        self.save_sources()
    
    def remove_folder(self, name: str):
        """Usuwa folder i wszystkie pliki w nim"""
        self.sources["folders"] = [f for f in self.sources["folders"] if f["name"] != name]
        self.sources["files"] = [f for f in self.sources["files"] if f["folder"] != name]
        self.save_sources()
    
    def remove_file(self, path: str):
        """Usuwa plik"""
        self.sources["files"] = [f for f in self.sources["files"] if f["path"] != path]
        self.save_sources()
    
    def set_folder_checked(self, name: str, checked: bool):
        """Ustawia stan checkboxa folderu"""
        for folder in self.sources["folders"]:
            if folder["name"] == name:
                folder["checked"] = checked
                break
        
        # Zaznacz/odznacz wszystkie pliki w folderze
        for file in self.sources["files"]:
            if file["folder"] == name:
                file["checked"] = checked
        
        self.save_sources()
    
    def set_file_checked(self, path: str, checked: bool):
        """Ustawia stan checkboxa pliku"""
        for file in self.sources["files"]:
            if file["path"] == path:
                file["checked"] = checked
                break
        self.save_sources()
    
    def get_checked_files(self) -> List[str]:
        """Zwraca ścieżki zaznaczonych plików"""
        return [f["path"] for f in self.sources["files"] if f.get("checked", False)]


class AIPanel(QWidget):
    """Panel AI w oknie nowej wiadomości"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.truth_manager = TruthSourcesManager()
        self.init_ui()
        self.refresh_truth_tree()
    
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
        self.base_prompt.setPlainText("Przygotuj odpowiedź na wiadomość e-mail")
        self.base_prompt.setMaximumHeight(60)
        layout.addWidget(self.base_prompt)
        
        # Sekcja 2: Prompt własny
        layout.addWidget(QLabel("Prompt własny:"))
        self.custom_prompt = QTextEdit()
        self.custom_prompt.setPlaceholderText("Dodatkowe instrukcje dla AI...")
        self.custom_prompt.setMaximumHeight(80)
        layout.addWidget(self.custom_prompt)
        
        # Sekcja 3: Checkboxy
        layout.addWidget(QLabel("Załącz do kontekstu:"))
        
        self.attach_conversation_cb = QCheckBox("Załącz całą konwersację")
        layout.addWidget(self.attach_conversation_cb)
        
        self.attach_all_mails_cb = QCheckBox("Załącz wszystkie maile")
        layout.addWidget(self.attach_all_mails_cb)
        
        self.attach_files_cb = QCheckBox("Załącz pliki z wiadomości")
        layout.addWidget(self.attach_files_cb)
        
        # Separator
        separator = QLabel()
        separator.setStyleSheet("background-color: #ccc; margin: 5px 0;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Sekcja 4: Źródła prawdy
        truth_label = QLabel("📚 Źródła prawdy:")
        truth_label.setStyleSheet("font-weight: bold; margin-top: 5px;")
        layout.addWidget(truth_label)
        
        # Przyciski zarządzania źródłami
        truth_btn_layout = QHBoxLayout()
        
        add_file_btn = QPushButton("📄+")
        add_file_btn.setToolTip("Dodaj plik")
        add_file_btn.setMaximumWidth(40)
        add_file_btn.clicked.connect(self.add_truth_file)
        truth_btn_layout.addWidget(add_file_btn)
        
        add_folder_btn = QPushButton("📁+")
        add_folder_btn.setToolTip("Dodaj folder")
        add_folder_btn.setMaximumWidth(40)
        add_folder_btn.clicked.connect(self.add_truth_folder)
        truth_btn_layout.addWidget(add_folder_btn)
        
        remove_btn = QPushButton("🗑️")
        remove_btn.setToolTip("Usuń")
        remove_btn.setMaximumWidth(40)
        remove_btn.clicked.connect(self.remove_truth_item)
        truth_btn_layout.addWidget(remove_btn)
        
        truth_btn_layout.addStretch()
        layout.addLayout(truth_btn_layout)
        
        # Drzewo źródeł prawdy
        self.truth_tree = QTreeWidget()
        self.truth_tree.setHeaderLabels(["Źródło"])
        self.truth_tree.setAlternatingRowColors(True)
        self.truth_tree.itemChanged.connect(self.on_truth_item_changed)
        layout.addWidget(self.truth_tree)
        
        # Przycisk generowania
        generate_btn = QPushButton("✨ Generuj odpowiedź AI")
        generate_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                padding: 8px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        generate_btn.clicked.connect(self.generate_response)
        layout.addWidget(generate_btn)
        
        # Placeholder info
        info_label = QLabel("ℹ️ Funkcja AI w przygotowaniu")
        info_label.setStyleSheet("color: #666; font-size: 9pt; padding: 5px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        self.setLayout(layout)
    
    def refresh_truth_tree(self):
        """Odświeża drzewo źródeł prawdy"""
        self.truth_tree.blockSignals(True)
        self.truth_tree.clear()
        
        # Grupuj pliki według folderów
        folders_dict = {}
        for folder in self.truth_manager.sources.get("folders", []):
            folder_item = QTreeWidgetItem(self.truth_tree, [folder["name"]])
            folder_item.setCheckState(0, Qt.CheckState.Checked if folder.get("checked", False) else Qt.CheckState.Unchecked)
            folder_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": folder["name"]})
            folder_item.setExpanded(True)
            folders_dict[folder["name"]] = folder_item
        
        # Dodaj pliki
        for file in self.truth_manager.sources.get("files", []):
            folder_name = file.get("folder", "")
            file_name = file.get("name", os.path.basename(file["path"]))
            
            if folder_name and folder_name in folders_dict:
                # Plik w folderze
                file_item = QTreeWidgetItem(folders_dict[folder_name], [file_name])
            else:
                # Plik bez folderu
                file_item = QTreeWidgetItem(self.truth_tree, [file_name])
            
            file_item.setCheckState(0, Qt.CheckState.Checked if file.get("checked", False) else Qt.CheckState.Unchecked)
            file_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "path": file["path"]})
        
        self.truth_tree.blockSignals(False)
    
    def on_truth_item_changed(self, item, column):
        """Obsługuje zmianę stanu checkboxa"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        checked = item.checkState(0) == Qt.CheckState.Checked
        
        if data["type"] == "folder":
            self.truth_manager.set_folder_checked(data["name"], checked)
            self.refresh_truth_tree()
        elif data["type"] == "file":
            self.truth_manager.set_file_checked(data["path"], checked)
    
    def add_truth_file(self):
        """Dodaje plik do źródeł prawdy"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik źródłowy",
            "",
            "Pliki tekstowe i PDF (*.txt *.pdf);;Wszystkie pliki (*.*)"
        )
        
        if file_path:
            # Zapytaj o folder (opcjonalnie)
            folders = [f["name"] for f in self.truth_manager.sources.get("folders", [])]
            if folders:
                folder, ok = QInputDialog.getItem(
                    self,
                    "Wybierz folder",
                    "Umieść plik w folderze (lub anuluj dla głównego poziomu):",
                    ["(główny poziom)"] + folders,
                    0,
                    False
                )
                if ok and folder != "(główny poziom)":
                    self.truth_manager.add_file(file_path, folder)
                else:
                    self.truth_manager.add_file(file_path)
            else:
                self.truth_manager.add_file(file_path)
            
            self.refresh_truth_tree()
    
    def add_truth_folder(self):
        """Dodaje folder do źródeł prawdy"""
        folder_name, ok = QInputDialog.getText(
            self,
            "Nowy folder",
            "Nazwa folderu:"
        )
        
        if ok and folder_name:
            self.truth_manager.add_folder(folder_name)
            self.refresh_truth_tree()
    
    def remove_truth_item(self):
        """Usuwa wybrany element"""
        item = self.truth_tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Błąd", "Wybierz element do usunięcia")
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        if data["type"] == "folder":
            reply = QMessageBox.question(
                self,
                "Potwierdzenie",
                f"Czy na pewno chcesz usunąć folder '{data['name']}' i wszystkie pliki w nim?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.truth_manager.remove_folder(data["name"])
                self.refresh_truth_tree()
        
        elif data["type"] == "file":
            self.truth_manager.remove_file(data["path"])
            self.refresh_truth_tree()
    
    def generate_response(self):
        """Generuje odpowiedź AI (placeholder)"""
        # Zbierz konfigurację
        base_prompt = self.base_prompt.toPlainText()
        custom_prompt = self.custom_prompt.toPlainText()
        attach_conversation = self.attach_conversation_cb.isChecked()
        attach_all_mails = self.attach_all_mails_cb.isChecked()
        attach_files = self.attach_files_cb.isChecked()
        checked_files = self.truth_manager.get_checked_files()
        
        # Placeholder - w przyszłości tutaj będzie integracja z API AI
        info = f"""
Konfiguracja AI:

Prompt podstawowy: {base_prompt}
Prompt własny: {custom_prompt}

Załącz konwersację: {attach_conversation}
Załącz wszystkie maile: {attach_all_mails}
Załącz pliki: {attach_files}

Źródła prawdy ({len(checked_files)}):
{chr(10).join(['- ' + os.path.basename(f) for f in checked_files])}

Funkcja generowania AI będzie zaimplementowana w przyszłości.
        """
        
        QMessageBox.information(self, "AI - Placeholder", info.strip())
    
    def get_ai_config(self) -> Dict[str, Any]:
        """Zwraca konfigurację AI"""
        return {
            "base_prompt": self.base_prompt.toPlainText(),
            "custom_prompt": self.custom_prompt.toPlainText(),
            "attach_conversation": self.attach_conversation_cb.isChecked(),
            "attach_all_mails": self.attach_all_mails_cb.isChecked(),
            "attach_files": self.attach_files_cb.isChecked(),
            "truth_sources": self.truth_manager.get_checked_files()
        }
