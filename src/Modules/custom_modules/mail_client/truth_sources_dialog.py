"""
Dialog zarządzania źródłami prawdy dla AI

Funkcjonalność:
- Tworzenie i edycja grup plików (foldery logiczne)
- Dodawanie plików: PDF, TXT, CSV, JSON
- Usuwanie plików i folderów
- Organizacja hierarchiczna (foldery -> pliki)
- Zaznaczanie checkboxami które pliki wysłać do AI

Autor: PRO-Ka-Po_Kaizen_Freak
Data: 2025-11-11
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QIcon
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QFileDialog,
    QMessageBox,
    QInputDialog,
    QWidget,
    QDialogButtonBox,
    QFrame,
)

try:
    from src.utils.theme_manager import get_theme_manager
except ImportError:
    get_theme_manager = None


class TruthSourcesDialog(QDialog):
    """Dialog do zarządzania źródłami prawdy (pliki kontekstowe dla AI)"""
    
    sources_updated = pyqtSignal()  # Sygnał emitowany po zmianach
    
    def __init__(self, sources_file: Optional[Path] = None, parent=None):
        """
        Args:
            sources_file: Ścieżka do pliku JSON ze źródłami prawdy
            parent: Widget rodzica
        """
        super().__init__(parent)
        
        self.sources_file = sources_file or Path("mail_client/ai_truth_sources.json")
        self.sources_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.sources = self._load_sources()
        self.theme_manager = get_theme_manager() if get_theme_manager else None
        
        self.init_ui()
        self.refresh_tree()
        
    def init_ui(self):
        """Inicjalizuje interfejs użytkownika"""
        self.setWindowTitle("Zarządzanie źródłami prawdy AI")
        self.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Nagłówek
        header = self._create_header()
        layout.addWidget(header)
        
        # Opis
        desc_label = QLabel(
            "Źródła prawdy to pliki kontekstowe, które mogą być załączane do promptów AI.\n"
            "Organizuj pliki w foldery logiczne i zaznaczaj które mają być używane."
        )
        desc_label.setWordWrap(True)
        layout.addWidget(desc_label)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
        
        # Toolbar z przyciskami akcji
        toolbar = self._create_toolbar()
        layout.addWidget(toolbar)
        
        # Drzewo źródeł prawdy
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Nazwa", "Typ", "Ścieżka"])
        self.tree.setColumnWidth(0, 250)
        self.tree.setColumnWidth(1, 100)
        self.tree.setAlternatingRowColors(True)
        self.tree.itemChanged.connect(self._on_item_checked)
        layout.addWidget(self.tree)
        
        # Przyciski dialogu
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        self.apply_theme()
        
    def _create_header(self) -> QWidget:
        """Tworzy widget nagłówka"""
        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        
        title_label = QLabel("📚 Źródła prawdy AI")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        title_label.setFont(font)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        
        header_widget.setLayout(header_layout)
        return header_widget
        
    def _create_toolbar(self) -> QWidget:
        """Tworzy toolbar z przyciskami akcji"""
        toolbar = QWidget()
        toolbar_layout = QHBoxLayout()
        toolbar_layout.setContentsMargins(0, 0, 0, 0)
        toolbar_layout.setSpacing(8)
        
        # Przycisk dodawania folderu
        self.btn_add_folder = QPushButton("📁 Dodaj folder")
        self.btn_add_folder.clicked.connect(self._add_folder)
        toolbar_layout.addWidget(self.btn_add_folder)
        
        # Przycisk dodawania plików
        self.btn_add_files = QPushButton("📄 Dodaj pliki")
        self.btn_add_files.clicked.connect(self._add_files)
        toolbar_layout.addWidget(self.btn_add_files)
        
        toolbar_layout.addSpacing(20)
        
        # Przycisk usuwania
        self.btn_remove = QPushButton("🗑️ Usuń")
        self.btn_remove.clicked.connect(self._remove_selected)
        toolbar_layout.addWidget(self.btn_remove)
        
        toolbar_layout.addStretch()
        
        # Statystyki
        self.stats_label = QLabel()
        self.stats_label.setStyleSheet("color: gray;")
        toolbar_layout.addWidget(self.stats_label)
        
        toolbar.setLayout(toolbar_layout)
        return toolbar
        
    def _load_sources(self) -> Dict[str, Any]:
        """Wczytuje źródła prawdy z pliku"""
        if self.sources_file.exists():
            try:
                with open(self.sources_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return {"folders": [], "files": []}
        return {"folders": [], "files": []}
        
    def _save_sources(self):
        """Zapisuje źródła prawdy do pliku"""
        try:
            with open(self.sources_file, 'w', encoding='utf-8') as f:
                json.dump(self.sources, f, ensure_ascii=False, indent=2)
            self.sources_updated.emit()
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie udało się zapisać: {e}")
            
    def refresh_tree(self):
        """Odświeża drzewo źródeł prawdy"""
        self.tree.clear()
        self.tree.itemChanged.disconnect(self._on_item_checked)
        
        # Najpierw dodaj główne foldery (bez parenta)
        folder_items = {}
        for folder in self.sources.get("folders", []):
            if not folder.get("parent"):
                item = self._create_folder_item(folder)
                self.tree.addTopLevelItem(item)
                folder_items[folder["name"]] = item
        
        # Potem dodaj podfoldery
        for folder in self.sources.get("folders", []):
            if folder.get("parent"):
                parent_item = folder_items.get(folder["parent"])
                if parent_item:
                    item = self._create_folder_item(folder)
                    parent_item.addChild(item)
                    folder_items[folder["name"]] = item
        
        # Na końcu dodaj pliki do odpowiednich folderów
        for file_data in self.sources.get("files", []):
            folder_name = file_data.get("folder", "")
            if folder_name and folder_name in folder_items:
                item = self._create_file_item(file_data)
                folder_items[folder_name].addChild(item)
            else:
                # Plik bez folderu - dodaj na najwyższym poziomie
                item = self._create_file_item(file_data)
                self.tree.addTopLevelItem(item)
        
        self.tree.expandAll()
        self.tree.itemChanged.connect(self._on_item_checked)
        self._update_stats()
        
    def _create_folder_item(self, folder: Dict) -> QTreeWidgetItem:
        """Tworzy element drzewa dla folderu"""
        item = QTreeWidgetItem([folder["name"], "Folder", ""])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if folder.get("checked", False) else Qt.CheckState.Unchecked)
        item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "data": folder})
        
        # Ikona folderu
        font = item.font(0)
        font.setBold(True)
        item.setFont(0, font)
        
        return item
        
    def _create_file_item(self, file_data: Dict) -> QTreeWidgetItem:
        """Tworzy element drzewa dla pliku"""
        file_path = Path(file_data["path"])
        file_type = file_path.suffix.upper().replace(".", "") or "FILE"
        
        item = QTreeWidgetItem([file_data["name"], file_type, file_data["path"]])
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Checked if file_data.get("checked", False) else Qt.CheckState.Unchecked)
        item.setData(0, Qt.ItemDataRole.UserRole, {"type": "file", "data": file_data})
        
        # Sprawdź czy plik istnieje
        if not file_path.exists():
            item.setForeground(0, Qt.GlobalColor.red)
            item.setToolTip(0, "⚠️ Plik nie istnieje")
        
        return item
        
    def _add_folder(self):
        """Dodaje nowy folder"""
        name, ok = QInputDialog.getText(
            self, 
            "Nowy folder", 
            "Nazwa folderu:",
            text="Nowy folder"
        )
        
        if ok and name:
            # Sprawdź czy nazwa już istnieje
            if any(f["name"] == name for f in self.sources.get("folders", [])):
                QMessageBox.warning(self, "Błąd", "Folder o tej nazwie już istnieje")
                return
            
            # Sprawdź czy jest zaznaczony folder (dla zagnieżdżenia)
            parent = ""
            current = self.tree.currentItem()
            if current:
                data = current.data(0, Qt.ItemDataRole.UserRole)
                if data and data["type"] == "folder":
                    parent = data["data"]["name"]
            
            folder = {
                "name": name,
                "parent": parent,
                "checked": False
            }
            
            if "folders" not in self.sources:
                self.sources["folders"] = []
            self.sources["folders"].append(folder)
            
            self._save_sources()
            self.refresh_tree()
            
    def _add_files(self):
        """Dodaje nowe pliki"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Wybierz pliki źródeł prawdy",
            "",
            "Wszystkie obsługiwane (*.txt *.pdf *.csv *.json *.md);;Pliki tekstowe (*.txt *.md);;PDF (*.pdf);;CSV (*.csv);;JSON (*.json)"
        )
        
        if not file_paths:
            return
        
        # Sprawdź czy jest zaznaczony folder
        folder = ""
        current = self.tree.currentItem()
        if current:
            data = current.data(0, Qt.ItemDataRole.UserRole)
            if data and data["type"] == "folder":
                folder = data["data"]["name"]
        
        # Dodaj pliki
        if "files" not in self.sources:
            self.sources["files"] = []
            
        for file_path in file_paths:
            # Sprawdź czy plik już istnieje
            if any(f["path"] == file_path for f in self.sources["files"]):
                continue
                
            file_data = {
                "path": file_path,
                "name": os.path.basename(file_path),
                "folder": folder,
                "checked": False
            }
            self.sources["files"].append(file_data)
        
        self._save_sources()
        self.refresh_tree()
        
    def _remove_selected(self):
        """Usuwa zaznaczony element"""
        current = self.tree.currentItem()
        if not current:
            QMessageBox.information(self, "Info", "Wybierz element do usunięcia")
            return
        
        data = current.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        # Potwierdzenie
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno usunąć '{current.text(0)}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        if data["type"] == "folder":
            folder_name = data["data"]["name"]
            # Usuń folder
            self.sources["folders"] = [f for f in self.sources.get("folders", []) if f["name"] != folder_name]
            # Usuń wszystkie pliki w folderze
            self.sources["files"] = [f for f in self.sources.get("files", []) if f.get("folder") != folder_name]
            # Usuń podfoldery
            self.sources["folders"] = [f for f in self.sources.get("folders", []) if f.get("parent") != folder_name]
        else:
            file_path = data["data"]["path"]
            self.sources["files"] = [f for f in self.sources.get("files", []) if f["path"] != file_path]
        
        self._save_sources()
        self.refresh_tree()
        
    def _on_item_checked(self, item: QTreeWidgetItem, column: int):
        """Obsługuje zmianę stanu checkboxa"""
        if column != 0:
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        checked = item.checkState(0) == Qt.CheckState.Checked
        
        if data["type"] == "folder":
            folder_name = data["data"]["name"]
            # Zmień stan folderu
            for folder in self.sources.get("folders", []):
                if folder["name"] == folder_name:
                    folder["checked"] = checked
                    break
            
            # Zmień stan wszystkich plików w folderze
            for file_data in self.sources.get("files", []):
                if file_data.get("folder") == folder_name:
                    file_data["checked"] = checked
            
            # Zmień stan wszystkich dzieci w drzewie
            self._set_children_checked(item, checked)
            
        else:
            file_path = data["data"]["path"]
            for file_data in self.sources.get("files", []):
                if file_data["path"] == file_path:
                    file_data["checked"] = checked
                    break
        
        self._save_sources()
        self._update_stats()
        
    def _set_children_checked(self, item: QTreeWidgetItem, checked: bool):
        """Rekurencyjnie ustawia stan dzieci"""
        for i in range(item.childCount()):
            child = item.child(i)
            child.setCheckState(0, Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            self._set_children_checked(child, checked)
            
    def _update_stats(self):
        """Aktualizuje statystyki"""
        total_files = len(self.sources.get("files", []))
        checked_files = sum(1 for f in self.sources.get("files", []) if f.get("checked", False))
        total_folders = len(self.sources.get("folders", []))
        
        self.stats_label.setText(
            f"Foldery: {total_folders} | Pliki: {checked_files}/{total_files} zaznaczonych"
        )
        
    def get_checked_files(self) -> List[str]:
        """Zwraca ścieżki zaznaczonych plików"""
        return [f["path"] for f in self.sources.get("files", []) if f.get("checked", False)]
        
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
        """)
        
    def accept(self):
        """Zapisuje i zamyka dialog"""
        self._save_sources()
        super().accept()


if __name__ == "__main__":
    """Test dialogu"""
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = TruthSourcesDialog()
    dialog.show()
    sys.exit(app.exec())
