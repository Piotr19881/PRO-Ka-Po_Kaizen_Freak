"""
Moduł dialogu zarządzania grupami plików

Funkcjonalność:
- Wyświetlanie listy grup
- Dodawanie nowych grup
- Edycja nazw grup
- Usuwanie grup
- Przypisywanie ikon/kolorów do grup
- Import/Export grup

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-06
"""

import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QPushButton,
    QMessageBox, QInputDialog, QLabel, QWidget, QListWidgetItem,
    QColorDialog, QComboBox, QFormLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QBrush, QFont


class FileGroupManagerDialog(QDialog):
    """Okno dialogowe do zarządzania grupami plików"""
    
    def __init__(self, parent=None, current_groups=None):
        super().__init__(parent)
        self.groups_file = Path("mail_client/file_groups.json")
        self.current_groups = current_groups if current_groups else []
        self.groups = self.load_groups()
        self.init_ui()
        self.populate_groups_list()
        
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        self.setWindowTitle("Zarządzanie grupami plików")
        self.setMinimumSize(900, 700)  # Zwiększone okno
        
        layout = QVBoxLayout()
        layout.setSpacing(5)  # Minimalne odstępy
        layout.setContentsMargins(10, 10, 10, 10)  # Zmniejszone marginesy
        
        # Nagłówek
        header = QLabel("Słownik grup plików")
        header_font = QFont()
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Opis
        desc = QLabel(
            "Zarządzaj nazwami grup dla organizacji ulubionych plików. Każda grupa może mieć własny kolor i ikonę."
        )
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet("color: #666; margin: 0px; padding: 2px;")
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Główna sekcja - lista grup i przyciski
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        
        # Lewa strona - lista grup
        left_layout = QVBoxLayout()
        left_layout.setSpacing(3)  # Minimalne odstępy
        
        groups_label = QLabel("Lista grup:")
        groups_label.setStyleSheet("font-weight: bold; margin: 0px; padding: 2px;")
        left_layout.addWidget(groups_label)
        
        self.groups_list = QListWidget()
        self.groups_list.currentRowChanged.connect(self.on_group_selected)
        self.groups_list.setStyleSheet("""
            QListWidget::item {
                padding: 8px;
                border-bottom: 1px solid #e0e0e0;
            }
            QListWidget::item:selected {
                background-color: #2196F3;
                color: white;
                border: 2px solid #1976D2;
            }
            QListWidget::item:hover {
                background-color: #E3F2FD;
            }
        """)
        left_layout.addWidget(self.groups_list)
        
        # Statystyki
        self.stats_label = QLabel("Grup: 0")
        self.stats_label.setStyleSheet("color: #666; font-size: 9pt; margin: 0px; padding: 2px;")
        left_layout.addWidget(self.stats_label)
        
        main_layout.addLayout(left_layout, 2)
        
        # Prawa strona - przyciski akcji
        right_layout = QVBoxLayout()
        right_layout.setSpacing(3)  # Minimalne odstępy między przyciskami
        
        btn_add = QPushButton("➕ Dodaj grupę")
        btn_add.clicked.connect(self.add_group)
        btn_add.setMinimumHeight(32)
        btn_add.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        right_layout.addWidget(btn_add)
        
        self.btn_edit = QPushButton("✏️ Edytuj nazwę")
        self.btn_edit.clicked.connect(self.edit_group)
        self.btn_edit.setEnabled(False)
        self.btn_edit.setMinimumHeight(32)
        right_layout.addWidget(self.btn_edit)
        
        self.btn_color = QPushButton("🎨 Zmień kolor")
        self.btn_color.clicked.connect(self.change_color)
        self.btn_color.setEnabled(False)
        self.btn_color.setMinimumHeight(32)
        right_layout.addWidget(self.btn_color)
        
        self.btn_icon = QPushButton("📂 Zmień ikonę")
        self.btn_icon.clicked.connect(self.change_icon)
        self.btn_icon.setEnabled(False)
        self.btn_icon.setMinimumHeight(32)
        right_layout.addWidget(self.btn_icon)
        
        right_layout.addSpacing(10)  # Zmniejszone
        
        self.btn_delete = QPushButton("🗑️ Usuń grupę")
        self.btn_delete.clicked.connect(self.delete_group)
        self.btn_delete.setEnabled(False)
        self.btn_delete.setMinimumHeight(32)
        self.btn_delete.setStyleSheet("""
            QPushButton {
                background-color: #f44336;
                color: white;
                font-weight: bold;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #da190b;
            }
        """)
        right_layout.addWidget(self.btn_delete)
        
        right_layout.addStretch()
        
        # Dodatkowe opcje
        btn_import = QPushButton("📥 Importuj grupy")
        btn_import.clicked.connect(self.import_groups)
        btn_import.setMinimumHeight(28)
        right_layout.addWidget(btn_import)
        
        btn_export = QPushButton("📤 Exportuj grupy")
        btn_export.clicked.connect(self.export_groups)
        btn_export.setMinimumHeight(28)
        right_layout.addWidget(btn_export)
        
        main_layout.addLayout(right_layout, 1)
        
        layout.addLayout(main_layout)
        
        # Separator
        separator = QLabel()
        separator.setStyleSheet("background-color: #cccccc; margin: 3px 0px;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Przyciski dialogu
        dialog_buttons = QHBoxLayout()
        dialog_buttons.setSpacing(10)
        
        btn_reset = QPushButton("🔄 Przywróć domyślne")
        btn_reset.clicked.connect(self.reset_to_defaults)
        btn_reset.setMinimumHeight(32)
        dialog_buttons.addWidget(btn_reset)
        
        dialog_buttons.addStretch()
        
        btn_close = QPushButton("✅ Zamknij")
        btn_close.clicked.connect(self.accept)
        btn_close.setMinimumWidth(100)
        btn_close.setMinimumHeight(32)
        btn_close.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                font-weight: bold;
                border-radius: 3px;
                padding: 5px;
            }
            QPushButton:hover {
                background-color: #0b7dda;
            }
        """)
        dialog_buttons.addWidget(btn_close)
        
        layout.addLayout(dialog_buttons)
        
        self.setLayout(layout)
        
    def load_groups(self):
        """Wczytuje grupy z pliku JSON"""
        if self.groups_file.exists():
            try:
                with open(self.groups_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return self.get_default_groups()
        else:
            return self.get_default_groups()
    
    def get_default_groups(self):
        """Zwraca domyślne grupy"""
        return [
            {"name": "Dokumenty", "icon": "📄", "color": "#2196F3"},
            {"name": "Faktury", "icon": "💰", "color": "#4CAF50"},
            {"name": "Projekty", "icon": "📁", "color": "#FF9800"},
            {"name": "Obrazy", "icon": "🖼️", "color": "#E91E63"},
            {"name": "Archiwum", "icon": "📦", "color": "#9E9E9E"},
            {"name": "Ważne", "icon": "⭐", "color": "#FFC107"},
            {"name": "Bez grupy", "icon": "📂", "color": "#607D8B"}
        ]
    
    def save_groups(self):
        """Zapisuje grupy do pliku JSON"""
        try:
            # Utwórz folder jeśli nie istnieje
            self.groups_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.groups_file, 'w', encoding='utf-8') as f:
                json.dump(self.groups, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać grup: {e}")
            return False
    
    def populate_groups_list(self):
        """Wypełnia listę grup"""
        self.groups_list.clear()
        
        for group in self.groups:
            item_text = f"{group.get('icon', '📂')} {group['name']}"
            item = QListWidgetItem(item_text)
            
            # Ustaw wyraźny kolor tła dla lepszej widoczności
            color = QColor(group.get('color', '#FFFFFF'))
            color.setAlpha(150)  # Zwiększona przezroczystość dla lepszej widoczności
            item.setBackground(QBrush(color))
            
            # Pogrubiona czcionka
            font = QFont()
            font.setBold(True)
            font.setPointSize(10)
            item.setFont(font)
            
            # Ustaw dane
            item.setData(Qt.ItemDataRole.UserRole, group)
            
            self.groups_list.addItem(item)
        
        # Aktualizuj statystyki
        self.stats_label.setText(f"Grup: {len(self.groups)}")
    
    def on_group_selected(self, row):
        """Obsługa wyboru grupy"""
        enabled = row >= 0
        self.btn_edit.setEnabled(enabled)
        self.btn_color.setEnabled(enabled)
        self.btn_icon.setEnabled(enabled)
        self.btn_delete.setEnabled(enabled)
    
    def add_group(self):
        """Dodaje nową grupę"""
        name, ok = QInputDialog.getText(
            self,
            "Nowa grupa",
            "Podaj nazwę grupy:",
            text="Nowa grupa"
        )
        
        if ok and name.strip():
            # Sprawdź czy grupa już istnieje
            if any(g['name'].lower() == name.strip().lower() for g in self.groups):
                QMessageBox.warning(
                    self,
                    "Błąd",
                    "Grupa o tej nazwie już istnieje!"
                )
                return
            
            # Dodaj grupę
            new_group = {
                "name": name.strip(),
                "icon": "📁",
                "color": "#2196F3"
            }
            
            self.groups.append(new_group)
            
            if self.save_groups():
                self.populate_groups_list()
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Grupa '{name.strip()}' została dodana!"
                )
    
    def edit_group(self):
        """Edytuje nazwę wybranej grupy"""
        current_row = self.groups_list.currentRow()
        if current_row < 0:
            return
        
        group = self.groups[current_row]
        
        name, ok = QInputDialog.getText(
            self,
            "Edytuj grupę",
            "Podaj nową nazwę grupy:",
            text=group['name']
        )
        
        if ok and name.strip():
            # Sprawdź czy nowa nazwa nie jest zajęta
            if any(i != current_row and g['name'].lower() == name.strip().lower() 
                   for i, g in enumerate(self.groups)):
                QMessageBox.warning(
                    self,
                    "Błąd",
                    "Grupa o tej nazwie już istnieje!"
                )
                return
            
            group['name'] = name.strip()
            
            if self.save_groups():
                self.populate_groups_list()
                self.groups_list.setCurrentRow(current_row)
    
    def change_color(self):
        """Zmienia kolor wybranej grupy"""
        current_row = self.groups_list.currentRow()
        if current_row < 0:
            return
        
        group = self.groups[current_row]
        current_color = QColor(group.get('color', '#FFFFFF'))
        
        color = QColorDialog.getColor(current_color, self, "Wybierz kolor grupy")
        
        if color.isValid():
            group['color'] = color.name()
            
            if self.save_groups():
                self.populate_groups_list()
                self.groups_list.setCurrentRow(current_row)
    
    def change_icon(self):
        """Zmienia ikonę wybranej grupy"""
        current_row = self.groups_list.currentRow()
        if current_row < 0:
            return
        
        group = self.groups[current_row]
        
        # Dialog z wyborem ikony
        icons = [
            "📁", "📂", "📄", "📝", "📋", "📊", "📈", "📉",
            "💼", "💰", "💳", "💸", "🏦", "🏢", "🏠", "🏪",
            "📦", "📮", "📬", "📭", "📪", "📫", "✉️", "📧",
            "🖼️", "🎨", "🎭", "🎪", "🎬", "🎯", "🎲", "🎰",
            "⭐", "🌟", "✨", "💫", "🔥", "💡", "🔔", "🔕",
            "📌", "📍", "🔖", "🏷️", "💾", "💿", "📀", "🗂️"
        ]
        
        icon, ok = QInputDialog.getItem(
            self,
            "Wybierz ikonę",
            "Wybierz ikonę dla grupy:",
            icons,
            icons.index(group.get('icon', '📁')),
            False
        )
        
        if ok:
            group['icon'] = icon
            
            if self.save_groups():
                self.populate_groups_list()
                self.groups_list.setCurrentRow(current_row)
    
    def delete_group(self):
        """Usuwa wybraną grupę"""
        current_row = self.groups_list.currentRow()
        if current_row < 0:
            return
        
        group = self.groups[current_row]
        
        # Sprawdź czy grupa jest używana
        used_count = sum(1 for g in self.current_groups if g == group['name'])
        
        warning_msg = f"Czy na pewno chcesz usunąć grupę '{group['name']}'?"
        if used_count > 0:
            warning_msg += f"\n\nUwaga: Ta grupa jest używana przez {used_count} plik(ów).\n"
            warning_msg += "Pliki zostaną przeniesione do grupy 'Bez grupy'."
        
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            warning_msg,
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.groups[current_row]
            
            if self.save_groups():
                self.populate_groups_list()
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Grupa '{group['name']}' została usunięta!"
                )
    
    def reset_to_defaults(self):
        """Przywraca domyślne grupy"""
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            "Czy na pewno chcesz przywrócić domyślne grupy?\n\n"
            "Wszystkie własne grupy zostaną usunięte!",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.groups = self.get_default_groups()
            
            if self.save_groups():
                self.populate_groups_list()
                QMessageBox.information(
                    self,
                    "Sukces",
                    "Grupy zostały przywrócone do ustawień domyślnych!"
                )
    
    def import_groups(self):
        """Importuje grupy z pliku JSON"""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importuj grupy",
            "",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported_groups = json.load(f)
                
                # Walidacja
                if not isinstance(imported_groups, list):
                    raise ValueError("Nieprawidłowy format danych")
                
                # Dodaj importowane grupy (unikaj duplikatów)
                added = 0
                for group in imported_groups:
                    if 'name' in group:
                        if not any(g['name'].lower() == group['name'].lower() 
                                 for g in self.groups):
                            self.groups.append({
                                "name": group['name'],
                                "icon": group.get('icon', '📁'),
                                "color": group.get('color', '#2196F3')
                            })
                            added += 1
                
                if self.save_groups():
                    self.populate_groups_list()
                    QMessageBox.information(
                        self,
                        "Sukces",
                        f"Zaimportowano {added} grup(y)!"
                    )
                    
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można zaimportować grup: {e}"
                )
    
    def export_groups(self):
        """Exportuje grupy do pliku JSON"""
        from PyQt6.QtWidgets import QFileDialog
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exportuj grupy",
            "grupy_plikow.json",
            "JSON Files (*.json);;All Files (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.groups, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Grupy zostały wyexportowane do:\n{file_path}"
                )
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie można wyexportować grup: {e}"
                )
    
    def get_groups(self):
        """Zwraca aktualną listę grup"""
        return self.groups


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    dialog = FileGroupManagerDialog()
    dialog.exec()
    sys.exit()
