from typing import Optional, List, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QDialogButtonBox, QLabel, QScrollArea, QWidget, QTableWidget, 
    QTableWidgetItem, QPushButton, QCheckBox, QSpinBox, QGroupBox,
    QColorDialog, QHeaderView, QMessageBox, QListWidget, QFileDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QFont
from loguru import logger

from ..utils.i18n_manager import get_i18n, t
from ..utils.theme_manager import get_theme_manager
from ..core.csv_import_export import (
    export_tasks_and_kanban_to_csv,
    import_tasks_and_kanban_from_csv,
)


class AddTagDialog(QDialog):
    """Dialog dodawania nowego tagu"""
    
    def __init__(self, parent: Optional[QWidget] = None, existing_tags: Optional[List[str]] = None):
        super().__init__(parent)
        self.existing_tags = existing_tags or []
        self.selected_color = "#3498db"  # Domyślny niebieski
        
        self._init_ui()
        self._apply_theme()
    
    def _init_ui(self):
        self.setWindowTitle(t('tasks.dialog.add_tag.title'))
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout(self)
        
        # Formularz
        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
        
        # Nazwa tagu
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t('tasks.dialog.tag.name_placeholder'))
        self.name_input.setMinimumWidth(300)
        form.addRow(t('tasks.dialog.tag.name_label'), self.name_input)
        
        # Wybór koloru
        color_layout = QHBoxLayout()
        
        self.color_preview = QLabel("      ")
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #ccc; border-radius: 3px;")
        self.color_preview.setFixedSize(60, 25)
        color_layout.addWidget(self.color_preview)
        
        self.color_button = QPushButton(t('tasks.dialog.tag.choose_color'))
        self.color_button.clicked.connect(self._on_choose_color)
        color_layout.addWidget(self.color_button)
        
        color_layout.addStretch()
        
        form.addRow(t('tasks.dialog.tag.color_label'), color_layout)
        
        layout.addLayout(form)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _apply_theme(self):
        """Zastosuj motyw - integracja z theme managerem"""
        # Theme manager automatycznie zastosuje aktualny motyw globalnie
        pass  # Dialogi dziedziczą motyw z aplikacji
    
    def _on_choose_color(self):
        """Otwórz dialog wyboru koloru"""
        color = QColorDialog.getColor(QColor(self.selected_color), self, t('tasks.dialog.tag.choose_color'))
        
        if color.isValid():
            self.selected_color = color.name()
            self.color_preview.setStyleSheet(
                f"background-color: {self.selected_color}; border: 1px solid #ccc; border-radius: 3px;"
            )
    
    def _on_accept(self):
        """Walidacja przed zaakceptowaniem"""
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, t('tasks.error.no_selection'), t('tasks.error.provide_tag_name'))
            return
        
        if name in self.existing_tags:
            QMessageBox.warning(self, t('tasks.error.no_selection'), 
                              t('tasks.error.duplicate_tag').replace('{0}', name))
            return
        
        self.accept()
    
    def get_tag_data(self) -> Dict[str, Any]:
        """Zwróć dane nowego tagu"""
        return {
            'name': self.name_input.text().strip(),
            'color': self.selected_color
        }


class EditTagDialog(QDialog):
    """Dialog edycji istniejącego tagu"""
    
    def __init__(self, parent: Optional[QWidget] = None, tag: Optional[Dict[str, Any]] = None,
             existing_tags: Optional[List[str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Edytuj tag")
        self.setMinimumWidth(400)
        
        self.tag = tag or {}
        self.original_name = tag.get('name', '')
        self.existing_tags = [t for t in (existing_tags or []) if t != self.original_name]
        self.selected_color = tag.get('color', '#3498db')
        
        self._init_ui()
        self._load_tag_data()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Formularz
        form = QFormLayout()
        
        # Nazwa tagu
        self.name_input = QLineEdit()
        self.name_input.setText(self.tag.get('name', ''))
        form.addRow("Nazwa tagu:", self.name_input)
        
        # Wybór koloru
        color_layout = QHBoxLayout()
        
        self.color_preview = QLabel("      ")
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #ccc; border-radius: 3px;")
        self.color_preview.setFixedSize(60, 25)
        color_layout.addWidget(self.color_preview)
        
        self.color_button = QPushButton("Wybierz kolor...")
        self.color_button.clicked.connect(self._on_choose_color)
        color_layout.addWidget(self.color_button)
        
        color_layout.addStretch()
        
        form.addRow("Kolor:", color_layout)
        
        layout.addLayout(form)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_tag_data(self):
        """Załaduj dane tagu do formularza"""
        self.name_input.setText(self.tag.get('name', ''))
        self.selected_color = self.tag.get('color', '#3498db')
        self.color_preview.setStyleSheet(
            f"background-color: {self.selected_color}; border: 1px solid #ccc; border-radius: 3px;"
        )
    
    def _on_choose_color(self):
        """Otwórz dialog wyboru koloru"""
        color = QColorDialog.getColor(QColor(self.selected_color), self, "Wybierz kolor tagu")
        
        if color.isValid():
            self.selected_color = color.name()
            self.color_preview.setStyleSheet(
                f"background-color: {self.selected_color}; border: 1px solid #ccc; border-radius: 3px;"
            )
    
    def _on_accept(self):
        """Walidacja przed zaakceptowaniem"""
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Błąd", "Podaj nazwę tagu")
            return
        
        if name in self.existing_tags:
            QMessageBox.warning(self, "Błąd", f"Tag '{name}' już istnieje")
            return
        
        self.accept()
    
    def get_tag_data(self) -> Dict[str, Any]:
        """Zwróć zaktualizowane dane tagu"""
        return {
            'name': self.name_input.text().strip(),
            'color': self.selected_color
        }


class AddListDialog(QDialog):
    """Dialog dodawania nowej listy własnej"""
    
    def __init__(self, parent: Optional[QWidget] = None, existing_lists: Optional[List[str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj listę własną")
        self.setMinimumWidth(500)
        
        self.existing_lists = existing_lists or []
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Formularz
        form = QFormLayout()
        
        # Nazwa listy
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("np. Priorytety, Statusy, Kategorie...")
        form.addRow("Nazwa listy:", self.name_input)
        
        layout.addLayout(form)
        
        # Wartości listy
        values_group = QGroupBox("Wartości listy")
        values_layout = QVBoxLayout(values_group)
        
        # Lista wartości
        self.values_list = QListWidget()
        self.values_list.setMinimumHeight(150)
        values_layout.addWidget(self.values_list)
        
        # Przyciski zarządzania wartościami
        values_buttons = QHBoxLayout()
        
        self.add_value_input = QLineEdit()
        self.add_value_input.setPlaceholderText("Nowa wartość...")
        self.add_value_input.returnPressed.connect(self._on_add_value)
        values_buttons.addWidget(self.add_value_input)
        
        self.btn_add_value = QPushButton("Dodaj")
        self.btn_add_value.clicked.connect(self._on_add_value)
        values_buttons.addWidget(self.btn_add_value)
        
        self.btn_remove_value = QPushButton("Usuń")
        self.btn_remove_value.clicked.connect(self._on_remove_value)
        values_buttons.addWidget(self.btn_remove_value)
        
        self.btn_move_up = QPushButton("▲")
        self.btn_move_up.setMaximumWidth(40)
        self.btn_move_up.clicked.connect(self._on_move_value_up)
        values_buttons.addWidget(self.btn_move_up)
        
        self.btn_move_down = QPushButton("▼")
        self.btn_move_down.setMaximumWidth(40)
        self.btn_move_down.clicked.connect(self._on_move_value_down)
        values_buttons.addWidget(self.btn_move_down)
        
        values_layout.addLayout(values_buttons)
        
        layout.addWidget(values_group)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _on_add_value(self):
        """Dodaj wartość do listy"""
        value = self.add_value_input.text().strip()
        
        if not value:
            return
        
        # Sprawdź duplikaty
        for i in range(self.values_list.count()):
            item = self.values_list.item(i)
            if item and item.text() == value:
                QMessageBox.warning(self, "Błąd", f"Wartość '{value}' już istnieje")
                return
        
        self.values_list.addItem(value)
        self.add_value_input.clear()
    
    def _on_remove_value(self):
        """Usuń wybraną wartość"""
        current_row = self.values_list.currentRow()
        if current_row >= 0:
            self.values_list.takeItem(current_row)
    
    def _on_move_value_up(self):
        """Przenieś wartość w górę"""
        current_row = self.values_list.currentRow()
        if current_row > 0:
            item = self.values_list.takeItem(current_row)
            self.values_list.insertItem(current_row - 1, item)
            self.values_list.setCurrentRow(current_row - 1)
    
    def _on_move_value_down(self):
        """Przenieś wartość w dół"""
        current_row = self.values_list.currentRow()
        if current_row < self.values_list.count() - 1 and current_row >= 0:
            item = self.values_list.takeItem(current_row)
            self.values_list.insertItem(current_row + 1, item)
            self.values_list.setCurrentRow(current_row + 1)
    
    def _on_accept(self):
        """Walidacja przed zaakceptowaniem"""
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Błąd", "Podaj nazwę listy")
            return
        
        if name in self.existing_lists:
            QMessageBox.warning(self, "Błąd", f"Lista '{name}' już istnieje")
            return
        
        if self.values_list.count() == 0:
            QMessageBox.warning(self, "Błąd", "Dodaj przynajmniej jedną wartość do listy")
            return
        
        self.accept()
    
    def get_list_data(self) -> Dict[str, Any]:
        """Zwróć dane nowej listy"""
        values = []
        for i in range(self.values_list.count()):
            item = self.values_list.item(i)
            if item:
                values.append(item.text())
        
        return {
            'name': self.name_input.text().strip(),
            'values': values
        }


class EditListDialog(QDialog):
    """Dialog edycji istniejącej listy własnej"""
    
    def __init__(self, parent: Optional[QWidget] = None, list_data: Optional[Dict[str, Any]] = None,
             existing_lists: Optional[List[str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Edytuj listę własną")
        self.setMinimumWidth(500)
        
        self.list_data = list_data or {}
        self.original_name = list_data.get('name', '')
        self.existing_lists = [l for l in (existing_lists or []) if l != self.original_name]
        
        self._init_ui()
        self._load_list_data()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Formularz
        form = QFormLayout()
        
        # Nazwa listy
        self.name_input = QLineEdit()
        self.name_input.setText(self.list_data.get('name', ''))
        form.addRow("Nazwa listy:", self.name_input)
        
        layout.addLayout(form)
        
        # Wartości listy
        values_group = QGroupBox("Wartości listy")
        values_layout = QVBoxLayout(values_group)
        
        # Lista wartości
        self.values_list = QListWidget()
        self.values_list.setMinimumHeight(150)
        values_layout.addWidget(self.values_list)
        
        # Przyciski zarządzania wartościami
        values_buttons = QHBoxLayout()
        
        self.add_value_input = QLineEdit()
        self.add_value_input.setPlaceholderText("Nowa wartość...")
        self.add_value_input.returnPressed.connect(self._on_add_value)
        values_buttons.addWidget(self.add_value_input)
        
        self.btn_add_value = QPushButton("Dodaj")
        self.btn_add_value.clicked.connect(self._on_add_value)
        values_buttons.addWidget(self.btn_add_value)
        
        self.btn_remove_value = QPushButton("Usuń")
        self.btn_remove_value.clicked.connect(self._on_remove_value)
        values_buttons.addWidget(self.btn_remove_value)
        
        self.btn_move_up = QPushButton("▲")
        self.btn_move_up.setMaximumWidth(40)
        self.btn_move_up.clicked.connect(self._on_move_value_up)
        values_buttons.addWidget(self.btn_move_up)
        
        self.btn_move_down = QPushButton("▼")
        self.btn_move_down.setMaximumWidth(40)
        self.btn_move_down.clicked.connect(self._on_move_value_down)
        values_buttons.addWidget(self.btn_move_down)
        
        values_layout.addLayout(values_buttons)
        
        layout.addWidget(values_group)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_list_data(self):
        """Załaduj dane listy do formularza"""
        self.name_input.setText(self.list_data.get('name', ''))
        
        values = self.list_data.get('values', [])
        for value in values:
            self.values_list.addItem(value)
    
    def _on_add_value(self):
        """Dodaj wartość do listy"""
        value = self.add_value_input.text().strip()
        
        if not value:
            return
        
        # Sprawdź duplikaty
        for i in range(self.values_list.count()):
            item = self.values_list.item(i)
            if item and item.text() == value:
                QMessageBox.warning(self, "Błąd", f"Wartość '{value}' już istnieje")
                return
        
        self.values_list.addItem(value)
        self.add_value_input.clear()
    
    def _on_remove_value(self):
        """Usuń wybraną wartość"""
        current_row = self.values_list.currentRow()
        if current_row >= 0:
            self.values_list.takeItem(current_row)
    
    def _on_move_value_up(self):
        """Przenieś wartość w górę"""
        current_row = self.values_list.currentRow()
        if current_row > 0:
            item = self.values_list.takeItem(current_row)
            self.values_list.insertItem(current_row - 1, item)
            self.values_list.setCurrentRow(current_row - 1)
    
    def _on_move_value_down(self):
        """Przenieś wartość w dół"""
        current_row = self.values_list.currentRow()
        if current_row < self.values_list.count() - 1 and current_row >= 0:
            item = self.values_list.takeItem(current_row)
            self.values_list.insertItem(current_row + 1, item)
            self.values_list.setCurrentRow(current_row + 1)
    
    def _on_accept(self):
        """Walidacja przed zaakceptowaniem"""
        name = self.name_input.text().strip()
        
        if not name:
            QMessageBox.warning(self, "Błąd", "Podaj nazwę listy")
            return
        
        if name in self.existing_lists:
            QMessageBox.warning(self, "Błąd", f"Lista '{name}' już istnieje")
            return
        
        if self.values_list.count() == 0:
            QMessageBox.warning(self, "Błąd", "Lista musi zawierać przynajmniej jedną wartość")
            return
        
        self.accept()
    
    def get_list_data(self) -> Dict[str, Any]:
        """Zwróć zaktualizowane dane listy"""
        values = []
        for i in range(self.values_list.count()):
            item = self.values_list.item(i)
            if item:
                values.append(item.text())
        
        return {
            'name': self.name_input.text().strip(),
            'values': values
        }


class EditColumnDialog(QDialog):
    """Dialog edycji istniejącej kolumny"""
    
    def __init__(self, parent: Optional[QWidget] = None, column: Optional[Dict[str, Any]] = None,
                 existing_columns: Optional[List[str]] = None, available_lists: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent)
        self.setWindowTitle("Edytuj kolumnę")
        self.setMinimumWidth(500)
        
        self.column = column or {}
        self.original_name = column.get('id', '')
        self.existing_columns = [c for c in (existing_columns or []) if c != self.original_name]
        self.available_lists = available_lists or []
        
        self._init_ui()
        self._load_column_data()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Informacja o ograniczeniach dla kolumn systemowych
        if self.column.get('system'):
            info_label = QLabel("⚠️ Kolumna systemowa - możesz edytować tylko niektóre właściwości")
            info_label.setStyleSheet("color: orange; font-weight: bold;")
            layout.addWidget(info_label)
        
        # Formularz
        form = QFormLayout()
        
        # Nazwa kolumny
        self.name_input = QLineEdit()
        self.name_input.setText(self.column.get('id', ''))
        
        # Zablokuj edycję nazwy dla kolumn systemowych
        if self.column.get('system'):
            self.name_input.setEnabled(False)
        
        form.addRow("Nazwa kolumny:", self.name_input)
        
        # Typ kolumny (tylko do odczytu)
        self.type_label = QLabel(self.column.get('type', ''))
        self.type_label.setStyleSheet("font-weight: bold;")
        form.addRow("Typ kolumny:", self.type_label)
        
        # Wartość domyślna
        self.default_value_input = QLineEdit()
        self.default_value_combo = QComboBox()
        
        default_layout = QHBoxLayout()
        default_layout.addWidget(self.default_value_input)
        default_layout.addWidget(self.default_value_combo)
        
        # Pokaż odpowiedni widget w zależności od typu
        column_type = self.column.get('type', '')
        if column_type == 'lista':
            self.default_value_input.setVisible(False)
            self.default_value_combo.setVisible(True)
        elif column_type == 'checkbox':
            self.default_value_input.setVisible(False)
            self.default_value_combo.setVisible(True)
            self.default_value_combo.addItems(["Odznaczone", "Zaznaczone"])
        else:
            self.default_value_input.setVisible(True)
            self.default_value_combo.setVisible(False)
        
        form.addRow("Wartość domyślna:", default_layout)
        
        # Lista własna (dla typu "lista")
        if column_type == 'lista':
            self.list_combo = QComboBox()
            for lst in self.available_lists:
                self.list_combo.addItem(lst.get('name', ''))
            self.list_combo.currentTextChanged.connect(self._update_list_values)
            form.addRow("Lista:", self.list_combo)
        
        layout.addLayout(form)
        
        # Opcje widoczności
        visibility_group = QGroupBox("Widoczność")
        visibility_layout = QVBoxLayout(visibility_group)
        
        self.visible_main_check = QCheckBox("Widoczna w głównym widoku zadań")
        visibility_layout.addWidget(self.visible_main_check)
        
        self.visible_bar_check = QCheckBox("Widoczna w pasku dolnym (quick input)")
        visibility_layout.addWidget(self.visible_bar_check)
        
        # Sprawdź czy można edytować widoczność dla kolumn systemowych
        allow_edit = self.column.get('allow_edit', [])
        if self.column.get('system'):
            if 'visible_main' not in allow_edit:
                self.visible_main_check.setEnabled(False)
            if 'visible_bar' not in allow_edit:
                self.visible_bar_check.setEnabled(False)
        
        layout.addWidget(visibility_group)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_column_data(self):
        """Załaduj dane kolumny do formularza"""
        # Wartość domyślna
        default_value = self.column.get('default_value', '')
        column_type = self.column.get('type', '')
        
        if column_type == 'checkbox':
            if default_value == 'true' or default_value is True:
                self.default_value_combo.setCurrentText("Zaznaczone")
            else:
                self.default_value_combo.setCurrentText("Odznaczone")
        elif column_type == 'lista':
            # Ustaw listę
            list_name = self.column.get('list_name', '')
            if hasattr(self, 'list_combo'):
                idx = self.list_combo.findText(list_name)
                if idx >= 0:
                    self.list_combo.setCurrentIndex(idx)
                # Zaktualizuj wartości w combo
                self._update_list_values(list_name)
                # Ustaw wartość domyślną
                if default_value:
                    idx = self.default_value_combo.findText(str(default_value))
                    if idx >= 0:
                        self.default_value_combo.setCurrentIndex(idx)
        else:
            self.default_value_input.setText(str(default_value))
        
        # Widoczność
        self.visible_main_check.setChecked(self.column.get('visible_main', True))
        self.visible_bar_check.setChecked(self.column.get('visible_bar', False))
    
    def _update_list_values(self, list_name: str):
        """Zaktualizuj dostępne wartości domyślne dla wybranej listy"""
        selected_list = next((lst for lst in self.available_lists if lst.get('name') == list_name), None)
        
        if selected_list and hasattr(self, 'default_value_combo'):
            current_value = self.default_value_combo.currentText()
            self.default_value_combo.clear()
            values = selected_list.get('values', [])
            self.default_value_combo.addItems(values)
            
            # Przywróć poprzednią wartość jeśli istnieje
            if current_value in values:
                self.default_value_combo.setCurrentText(current_value)
    
    def _on_accept(self):
        """Walidacja przed zaakceptowaniem"""
        name = self.name_input.text().strip()
        
        # Walidacja nazwy (jeśli można edytować)
        if not self.column.get('system'):
            if not name:
                QMessageBox.warning(self, "Błąd", "Podaj nazwę kolumny")
                return
            
            if name in self.existing_columns:
                QMessageBox.warning(self, "Błąd", f"Kolumna '{name}' już istnieje")
                return
        
        self.accept()
    
    def get_column_data(self) -> Dict[str, Any]:
        """Zwróć zaktualizowane dane kolumny"""
        column_type = self.column.get('type', '')
        
        # Pobierz wartość domyślną
        if column_type == 'lista':
            default_value = self.default_value_combo.currentText()
        elif column_type == 'checkbox':
            default_value = "false" if self.default_value_combo.currentText() == "Odznaczone" else "true"
        else:
            default_value = self.default_value_input.text().strip()
        
        # Zaktualizuj dane kolumny
        updated_column = dict(self.column)
        
        if not self.column.get('system'):
            updated_column['id'] = self.name_input.text().strip()
        
        updated_column['default_value'] = default_value
        updated_column['visible_main'] = self.visible_main_check.isChecked()
        updated_column['visible_bar'] = self.visible_bar_check.isChecked()
        
        # Dla typu lista - zaktualizuj list_name
        if column_type == 'lista' and hasattr(self, 'list_combo'):
            updated_column['list_name'] = self.list_combo.currentText()
        
        return updated_column


class AddColumnDialog(QDialog):
    """Dialog dodawania nowej kolumny użytkownika"""
    
    def __init__(self, parent: Optional[QWidget] = None, existing_columns: Optional[List[str]] = None,
                 available_lists: Optional[List[Dict[str, Any]]] = None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj nową kolumnę")
        self.setMinimumWidth(500)
        
        self.existing_columns = existing_columns or []
        self.available_lists = available_lists or []
        
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Formularz
        form = QFormLayout()
        
        # Nazwa kolumny
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("np. Kategoria, Budżet, Deadline...")
        form.addRow("Nazwa kolumny:", self.name_input)
        
        # Typ kolumny
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            "tekstowa",
            "Waluta",
            "data",
            "Czas trwania",
            "lista",
            "checkbox",
            "liczbowa"
        ])
        self.type_combo.currentTextChanged.connect(self._on_type_changed)
        form.addRow("Typ kolumny:", self.type_combo)
        
        # Wartość domyślna (zmienia się w zależności od typu)
        self.default_value_label = QLabel("Wartość domyślna:")
        self.default_value_input = QLineEdit()
        self.default_value_combo = QComboBox()
        self.default_value_combo.setVisible(False)
        
        default_layout = QHBoxLayout()
        default_layout.addWidget(self.default_value_input)
        default_layout.addWidget(self.default_value_combo)
        form.addRow(self.default_value_label, default_layout)
        
        # Lista własna (tylko dla typu "lista")
        self.list_label = QLabel("Wybierz listę:")
        self.list_combo = QComboBox()
        self.list_combo.addItem("(wybierz listę)")
        for lst in self.available_lists:
            self.list_combo.addItem(lst.get('name', ''))
        self.list_label.setVisible(False)
        self.list_combo.setVisible(False)
        form.addRow(self.list_label, self.list_combo)
        
        layout.addLayout(form)
        
        # Opcje widoczności
        visibility_group = QGroupBox("Widoczność")
        visibility_layout = QVBoxLayout(visibility_group)
        
        self.visible_main_check = QCheckBox("Widoczna w głównym widoku zadań")
        self.visible_main_check.setChecked(True)
        visibility_layout.addWidget(self.visible_main_check)
        
        self.visible_bar_check = QCheckBox("Widoczna w pasku dolnym (quick input)")
        visibility_layout.addWidget(self.visible_bar_check)
        
        layout.addWidget(visibility_group)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._on_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        # Inicjalizacja widoku dla pierwszego typu
        self._on_type_changed(self.type_combo.currentText())
    
    def _on_type_changed(self, column_type: str):
        """Dostosuj pola do wybranego typu kolumny"""
        # Ukryj wszystkie opcjonalne pola
        self.default_value_input.setVisible(True)
        self.default_value_combo.setVisible(False)
        self.list_label.setVisible(False)
        self.list_combo.setVisible(False)
        
        # Dostosuj placeholder i widoczność w zależności od typu
        if column_type == "tekstowa":
            self.default_value_input.setPlaceholderText("np. Do zrobienia")
            self.default_value_label.setText("Wartość domyślna:")
            
        elif column_type == "Waluta":
            self.default_value_input.setPlaceholderText("np. 0.00")
            self.default_value_label.setText("Wartość domyślna (PLN):")
            
        elif column_type == "data":
            self.default_value_input.setPlaceholderText("np. 2025-11-04 lub 'today'")
            self.default_value_label.setText("Wartość domyślna:")
            
        elif column_type == "Czas trwania":
            self.default_value_input.setPlaceholderText("np. 2h, 30m, 1d")
            self.default_value_label.setText("Wartość domyślna:")
            
        elif column_type == "lista":
            # Dla typu lista - pokaż ComboBox z wartościami
            self.default_value_input.setVisible(False)
            self.default_value_combo.setVisible(True)
            self.list_label.setVisible(True)
            self.list_combo.setVisible(True)
            self.default_value_label.setText("Wartość domyślna:")
            
            # Podłącz zmianę listy do aktualizacji wartości domyślnych
            self.list_combo.currentTextChanged.connect(self._update_list_values)
            
        elif column_type == "checkbox":
            self.default_value_input.setVisible(False)
            self.default_value_combo.setVisible(True)
            self.default_value_combo.clear()
            self.default_value_combo.addItems(["Odznaczone", "Zaznaczone"])
            self.default_value_label.setText("Stan domyślny:")
            
        elif column_type == "liczbowa":
            self.default_value_input.setPlaceholderText("np. 0")
            self.default_value_label.setText("Wartość domyślna:")
    
    def _update_list_values(self, list_name: str):
        """Zaktualizuj dostępne wartości domyślne dla wybranej listy"""
        if list_name == "(wybierz listę)":
            self.default_value_combo.clear()
            return
        
        # Znajdź wybraną listę
        selected_list = next((lst for lst in self.available_lists if lst.get('name') == list_name), None)
        
        if selected_list:
            self.default_value_combo.clear()
            values = selected_list.get('values', [])
            self.default_value_combo.addItems(values)
    
    def _on_accept(self):
        """Walidacja przed zaakceptowaniem"""
        name = self.name_input.text().strip()
        
        # Walidacja nazwy
        if not name:
            QMessageBox.warning(self, "Błąd", "Podaj nazwę kolumny")
            return
        
        if name in self.existing_columns:
            QMessageBox.warning(self, "Błąd", f"Kolumna '{name}' już istnieje")
            return
        
        # Walidacja dla typu "lista"
        if self.type_combo.currentText() == "lista":
            if self.list_combo.currentText() == "(wybierz listę)":
                QMessageBox.warning(self, "Błąd", "Wybierz listę dla kolumny typu 'lista'")
                return
        
        self.accept()
    
    def get_column_data(self) -> Dict[str, Any]:
        """Zwróć dane nowej kolumny"""
        column_type = self.type_combo.currentText()
        
        # Pobierz wartość domyślną
        default_value = ""
        if column_type == "lista":
            default_value = self.default_value_combo.currentText()
        elif column_type == "checkbox":
            default_value = "false" if self.default_value_combo.currentText() == "Odznaczone" else "true"
        else:
            default_value = self.default_value_input.text().strip()
        
        # Pobierz nazwę listy dla typu "lista"
        list_name = ""
        if column_type == "lista":
            list_name = self.list_combo.currentText()
        
        return {
            'id': self.name_input.text().strip(),
            'type': column_type,
            'visible_main': self.visible_main_check.isChecked(),
            'visible_bar': self.visible_bar_check.isChecked(),
            'default_value': default_value,
            'list_name': list_name,
            'system': False,
            'editable': True
        }


class TaskConfigDialog(QDialog):
    """Dialog konfiguracji tabeli zadań - kolumny, tagi, listy, ustawienia."""
    
    # Typy kolumn dostępne dla użytkownika
    COLUMN_TYPES = [
        "tekstowa",
        "Waluta", 
        "data",
        "Czas trwania",
        "lista",
        "checkbox",
        "liczbowa"
    ]
    
    # Kolumny systemowe (niemodyfikowalne lub częściowo modyfikowalne)
    SYSTEM_COLUMNS = [
        {
            'id': 'id',
            'position': 0,
            'type': 'int',
            'visible_main': False,
            'visible_bar': False,
            'default_value': '',
            'editable': False,
            'system': True
        },
        {
            'id': 'position',
            'position': 1,
            'type': 'int',
            'visible_main': False,
            'visible_bar': False,
            'default_value': '',
            'editable': False,
            'system': True
        },
        {
            'id': 'Data dodania',
            'position': 2,
            'type': 'data',
            'visible_main': True,
            'visible_bar': False,
            'default_value': 'today',
            'editable': True,  # Może modyfikować widoczność
            'system': True,
            'allow_edit': ['visible_main'],
            'locked_position': True  # Zablokowana pozycja
        },
        {
            'id': 'Subtaski',
            'position': 3,
            'type': 'button',
            'visible_main': True,
            'visible_bar': False,  # Nigdy nie pokazuj w pasku dolnym
            'default_value': '',
            'editable': False,  # Nie można edytować w ogóle
            'system': True,
            'locked_position': True,  # Zablokowana pozycja
            'locked_visibility': True  # Zablokowana widoczność - zawsze visible_main=True
        },
        {
            'id': 'Zadanie',
            'position': 4,
            'type': 'text',
            'visible_main': True,
            'visible_bar': True,
            'default_value': '',
            'editable': False,
            'system': True,
            'locked_position': True  # Zablokowana pozycja
        },
        {
            'id': 'Status',
            'position': 5,
            'type': 'checkbox',
            'visible_main': True,
            'visible_bar': False,
            'default_value': 'false',
            'editable': True,
            'system': True,
            'allow_edit': ['visible_main', 'position'],
            'locked_visibility': True
        },
        {
            'id': 'data realizacji',
            'position': 6,
            'type': 'data',
            'visible_main': True,
            'visible_bar': False,
            'default_value': '',
            'editable': True,
            'system': True,
            'allow_edit': ['visible_main', 'position'],
            'locked_visibility': True
        },
        {
            'id': 'KanBan',
            'position': 7,
            'type': 'button',
            'visible_main': True,
            'visible_bar': True,
            'default_value': '',
            'editable': True,
            'system': True,
            'allow_edit': ['visible_main', 'position']
        },
        {
            'id': 'Notatka',
            'position': 8,
            'type': 'button',
            'visible_main': True,
            'visible_bar': False,
            'default_value': '',
            'editable': True,
            'system': True,
            'allow_edit': ['visible_main', 'position']
        },
        {
            'id': 'Archiwum',
            'position': 9,
            'type': 'boolean',
            'visible_main': False,
            'visible_bar': False,
            'default_value': 'false',
            'editable': False,
            'system': True
        },
        {
            'id': 'Tag',
            'position': 9,
            'type': 'lista',
            'visible_main': True,
            'visible_bar': True,
            'default_value': '',
            'list_name': 'tags',  # Odniesienie do listy tagów
            'editable': True,
            'system': True,
            'allow_edit': ['visible_main', 'visible_bar', 'position']
        },
        {
            'id': 'Alarm',
            'position': 10,
            'type': 'data',
            'visible_main': True,
            'visible_bar': True,
            'default_value': '',
            'editable': True,
            'system': True,
            'allow_edit': ['visible_main', 'visible_bar', 'position']
        }
    ]

    def __init__(self, parent: Optional[QWidget] = None, local_db=None):
        super().__init__(parent)
        
        # Baza danych lokalna
        self.local_db = local_db
        
        # Dane konfiguracji - wczytaj z bazy lub użyj domyślnych
        self.columns = []
        self.tags = []
        self.custom_lists = []
        self.settings = {
            'auto_archive_after_days': 30,
            'auto_archive_enabled': False,
            'auto_move_completed': False,
            'auto_archive_completed': False
        }
        
        # Wczytaj dane z bazy danych
        self._load_from_database()
        self._load_settings_from_database()
        
        self._init_ui()
        self._apply_theme()
        self._populate_columns_table()
        self._populate_tags_table()
        self._populate_lists_table()

    def _load_from_database(self):
        """Wczytaj konfigurację z bazy danych"""
        if self.local_db:
            try:
                # Wczytaj kolumny
                db_columns = self.local_db.load_columns_config()
                if db_columns:
                    self.columns = db_columns
                    self._enforce_system_column_constraints()
                    logger.info(f"[TaskConfigDialog] Loaded {len(self.columns)} columns from database")
                else:
                    # Użyj domyślnych kolumn systemowych
                    self.columns = list(self.SYSTEM_COLUMNS)
                    self._enforce_system_column_constraints()
                    logger.info("[TaskConfigDialog] Using default system columns")
                
                # Wczytaj tagi
                db_tags = self.local_db.load_tags()
                if db_tags:
                    self.tags = db_tags
                    logger.info(f"[TaskConfigDialog] Loaded {len(self.tags)} tags from database")
                else:
                    # Domyślne tagi
                    self.tags = [
                        {'name': 'Pilne', 'color': '#FF0000'},
                        {'name': 'Ważne', 'color': '#FFA500'},
                        {'name': 'Praca', 'color': '#0000FF'},
                        {'name': 'Dom', 'color': '#00FF00'}
                    ]
                
                # Wczytaj listy własne
                db_lists = self.local_db.load_custom_lists()
                if db_lists:
                    self.custom_lists = db_lists
                    logger.info(f"[TaskConfigDialog] Loaded {len(self.custom_lists)} custom lists from database")
                else:
                    # Domyślne listy
                    self.custom_lists = [
                        {'name': 'Priorytet', 'values': ['Niski', 'Średni', 'Wysoki', 'Krytyczny']},
                        {'name': 'Kategoria', 'values': ['Rozwój', 'Naprawy', 'Dokumentacja', 'Testowanie']}
                    ]
                
            except Exception as e:
                logger.error(f"[TaskConfigDialog] Failed to load from database: {e}")
                # Użyj domyślnych wartości
                self.columns = list(self.SYSTEM_COLUMNS)
                self._enforce_system_column_constraints()
                self.tags = [
                    {'name': 'Pilne', 'color': '#FF0000'},
                    {'name': 'Ważne', 'color': '#FFA500'}
                ]
                self.custom_lists = [
                    {'name': 'Priorytet', 'values': ['Niski', 'Średni', 'Wysoki']}
                ]
        else:
            # Brak bazy danych - użyj domyślnych wartości
            self.columns = list(self.SYSTEM_COLUMNS)
            self._enforce_system_column_constraints()
            self.tags = [
                {'name': 'Pilne', 'color': '#FF0000'},
                {'name': 'Ważne', 'color': '#FFA500'}
            ]
            self.custom_lists = [
                {'name': 'Priorytet', 'values': ['Niski', 'Średni', 'Wysoki']}
            ]
            logger.warning("[TaskConfigDialog] No database provided, using defaults")

    def _load_settings_from_database(self) -> None:
        """Wczytaj ustawienia ogólne z bazy danych."""
        if not self.local_db:
            return

        try:
            enabled = self.local_db.get_setting('auto_archive_enabled', self.settings['auto_archive_enabled'])
            self.settings['auto_archive_enabled'] = bool(enabled)

            days_value = self.local_db.get_setting('auto_archive_after_days', self.settings['auto_archive_after_days'])
            try:
                days_int = int(days_value)
            except (TypeError, ValueError):
                days_int = self.settings['auto_archive_after_days']
            if days_int < 1:
                days_int = 1
            self.settings['auto_archive_after_days'] = days_int

            move_completed = self.local_db.get_setting('auto_move_completed', self.settings['auto_move_completed'])
            self.settings['auto_move_completed'] = bool(move_completed)

            auto_archive_completed = self.local_db.get_setting('auto_archive_completed', self.settings['auto_archive_completed'])
            self.settings['auto_archive_completed'] = bool(auto_archive_completed)

            logger.info("[TaskConfigDialog] Loaded general settings from database")
        except Exception as exc:
            logger.error(f"[TaskConfigDialog] Failed to load general settings: {exc}")

    def _enforce_system_column_constraints(self) -> None:
        """Wymuś z góry zdefiniowane ograniczenia widoczności dla kolumn systemowych."""
        if not self.columns:
            return

        locked_false_columns = {
            'Data dodania': False,
            'Status': False,
            'data realizacji': False,
        }

        for column in self.columns:
            column_id = column.get('id')
            if not column.get('system'):
                continue

            if column_id in locked_false_columns:
                column['visible_bar'] = locked_false_columns[column_id]

                allow_edit = list(column.get('allow_edit') or [])
                if 'visible_bar' in allow_edit:
                    allow_edit = [item for item in allow_edit if item != 'visible_bar']
                    column['allow_edit'] = allow_edit

                column.setdefault('locked_visibility', True)


    def _init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        self.setWindowTitle(t('tasks.config.title'))
        self.setMinimumSize(900, 700)
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        
        # Scroll area dla całego contentu
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        scroll_layout.setSpacing(28)
        
        # ========== SEKCJA 1: Zarządzanie kolumnami ==========
        self._add_section_header(scroll_layout, t('tasks.config.section_columns'))
        self._create_columns_section(scroll_layout)
        
        # ========== SEKCJA 2: Zarządzanie tagami ==========
        self._add_section_header(scroll_layout, t('tasks.config.section_tags'))
        self._create_tags_section(scroll_layout)
        
        # ========== SEKCJA 3: Zarządzanie listami ==========
        self._add_section_header(scroll_layout, t('tasks.config.section_lists'))
        self._create_lists_section(scroll_layout)
        
        # ========== SEKCJA 4: Ustawienia ogólne ==========
        self._add_section_header(scroll_layout, t('tasks.config.section_settings'))
        self._create_settings_section(scroll_layout)

        self._create_csv_buttons(scroll_layout)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # Przyciski dialogu
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Save | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
    
    def _apply_theme(self):
        """Zastosuj motyw - integracja z theme managerem"""
        # Theme manager automatycznie zastosuje aktualny motyw
        # Nie przekazujemy parametru - używa aktualnie ustawionego motywu
        pass  # Theme jest już zastosowany globalnie

    def _add_section_header(self, parent_layout: QVBoxLayout, text: str) -> None:
        """Dodaje nagłówek sekcji z większym fontem i wyśrodkowaniem."""
        header = QLabel(text)
        header_font = QFont()
        header_font.setPointSize(15)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setContentsMargins(0, 6, 0, 4)
        parent_layout.addWidget(header)

    def _create_columns_section(self, parent_layout: QVBoxLayout):
        """Sekcja zarządzania kolumnami"""
        group = QGroupBox()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)
        
        # Tabela kolumn: Pozycja / Typ / Nazwa / Widoczna / Widoczna w pasku / Wartość domyślna
        self.columns_table = QTableWidget(0, 6)
        self.columns_table.setHorizontalHeaderLabels([
            t('tasks.config.column.position'),      # Pozycja
            t('tasks.config.column.type'),          # Typ
            t('tasks.config.column.name'),          # Nazwa
            t('tasks.config.column.visible_main'),  # Widoczna
            t('tasks.config.column.visible_bar'),   # Widoczna w pasku
            t('tasks.config.column.default_value')  # Wartość domyślna
        ])
        # Ustaw szerokości kolumn
        header = self.columns_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(0, 70)	  # Pozycja - wąska kolumna (int)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(1, 100)	# Typ
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)	# Nazwa - rozciągliwa
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(3, 90)	  # Widoczna (checkbox)
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(4, 130)	# Widoczna w pasku (checkbox)
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(5, 150)	# Wartość domyślna
        
        self.columns_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.columns_table.setMinimumHeight(320)
        layout.addWidget(self.columns_table)
        
        # Pasek przycisków
        btn_layout = QHBoxLayout()
        
        # Lewe przyciski
        self.btn_add_col = QPushButton(t('tasks.config.button.add_column'))
        self.btn_add_col.clicked.connect(self._on_add_column)
        btn_layout.addWidget(self.btn_add_col)
        
        self.btn_edit_col = QPushButton(t('tasks.config.button.edit_column'))
        self.btn_edit_col.clicked.connect(self._on_edit_column)
        btn_layout.addWidget(self.btn_edit_col)
        
        self.btn_delete_col = QPushButton(t('tasks.config.button.delete_column'))
        self.btn_delete_col.clicked.connect(self._on_delete_column)
        btn_layout.addWidget(self.btn_delete_col)
        
        btn_layout.addStretch()
        
        # Prawe przyciski
        self.btn_move_up = QPushButton(t('tasks.config.button.move_up'))
        self.btn_move_up.clicked.connect(self._on_move_column_up)
        btn_layout.addWidget(self.btn_move_up)
        
        self.btn_move_down = QPushButton(t('tasks.config.button.move_down'))
        self.btn_move_down.clicked.connect(self._on_move_column_down)
        btn_layout.addWidget(self.btn_move_down)
        
        layout.addLayout(btn_layout)
        
        parent_layout.addWidget(group)

    def _create_tags_section(self, parent_layout: QVBoxLayout):
        """Sekcja zarządzania tagami"""
        group = QGroupBox()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)
        
        # Tabela tagów
        self.tags_table = QTableWidget(0, 2)
        self.tags_table.setHorizontalHeaderLabels([
            t('tasks.config.tag.name'),
            t('tasks.config.tag.color')
        ])
        header = self.tags_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        
        self.tags_table.setMinimumHeight(220)
        layout.addWidget(self.tags_table)
        
        # Przyciski
        btn_layout = QHBoxLayout()
        self.btn_add_tag = QPushButton(t('tasks.config.button.add_tag'))
        self.btn_add_tag.clicked.connect(self._on_add_tag)
        btn_layout.addWidget(self.btn_add_tag)
        
        self.btn_edit_tag = QPushButton(t('tasks.config.button.edit_tag'))
        self.btn_edit_tag.clicked.connect(self._on_edit_tag)
        btn_layout.addWidget(self.btn_edit_tag)
        
        self.btn_delete_tag = QPushButton(t('tasks.config.button.delete_tag'))
        self.btn_delete_tag.clicked.connect(self._on_delete_tag)
        btn_layout.addWidget(self.btn_delete_tag)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        parent_layout.addWidget(group)

    def _create_lists_section(self, parent_layout: QVBoxLayout):
        """Sekcja zarządzania listami własnymi"""
        group = QGroupBox()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)
        
        # Tabela list
        self.lists_table = QTableWidget(0, 3)
        self.lists_table.setHorizontalHeaderLabels([
            t('tasks.config.list.name'),
            t('tasks.config.list.values'),
            ""
        ])
        header = self.lists_table.horizontalHeader()
        if header is not None:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Interactive)
            header.resizeSection(0, 220)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)
            header.resizeSection(2, 120)
        
        self.lists_table.setMinimumHeight(220)
        layout.addWidget(self.lists_table)
        
        # Przyciski
        btn_layout = QHBoxLayout()
        self.btn_add_list = QPushButton(t('tasks.config.button.add_list'))
        self.btn_add_list.clicked.connect(self._on_add_list)
        btn_layout.addWidget(self.btn_add_list)
        
        self.btn_edit_list = QPushButton(t('tasks.config.button.edit_list'))
        self.btn_edit_list.clicked.connect(self._on_edit_list)
        btn_layout.addWidget(self.btn_edit_list)
        
        self.btn_delete_list = QPushButton(t('tasks.config.button.delete_list'))
        self.btn_delete_list.clicked.connect(self._on_delete_list)
        btn_layout.addWidget(self.btn_delete_list)
        btn_layout.addStretch()
        
        layout.addLayout(btn_layout)
        parent_layout.addWidget(group)

    def _create_settings_section(self, parent_layout: QVBoxLayout):
        """Sekcja ustawień ogólnych"""
        group = QGroupBox()
        layout = QVBoxLayout(group)
        layout.setContentsMargins(18, 16, 18, 18)
        layout.setSpacing(14)
        
        # Archiwizuj ukończone po X dniach
        archive_layout = QHBoxLayout()
        self.chk_auto_archive = QCheckBox(t('tasks.config.settings.auto_archive_label'))
        self.chk_auto_archive.setChecked(self.settings['auto_archive_enabled'])
        archive_layout.addWidget(self.chk_auto_archive)
        
        self.spin_archive_days = QSpinBox()
        self.spin_archive_days.setMinimum(1)
        self.spin_archive_days.setMaximum(365)
        self.spin_archive_days.setValue(self.settings['auto_archive_after_days'])
        self.spin_archive_days.setSuffix(t('tasks.config.settings.auto_archive_suffix'))
        self.spin_archive_days.setEnabled(self.settings['auto_archive_enabled'])
        self.chk_auto_archive.toggled.connect(self.spin_archive_days.setEnabled)
        archive_layout.addWidget(self.spin_archive_days)
        archive_layout.addStretch()
        layout.addLayout(archive_layout)
        
        # Automatycznie przenoś ukończone pod nieukończone
        self.chk_auto_move = QCheckBox(t('tasks.config.settings.auto_move_completed'))
        self.chk_auto_move.setChecked(self.settings['auto_move_completed'])
        layout.addWidget(self.chk_auto_move)
        
        # Automatycznie archiwizuj ukończone
        self.chk_auto_archive_completed = QCheckBox(t('tasks.config.settings.auto_archive_completed'))
        self.chk_auto_archive_completed.setChecked(self.settings['auto_archive_completed'])
        layout.addWidget(self.chk_auto_archive_completed)
        
        parent_layout.addWidget(group)

    def _create_csv_buttons(self, parent_layout: QVBoxLayout) -> None:
        """Dodaje przyciski importu/eksportu CSV (placeholder)."""
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(12)

        self.btn_import_csv = QPushButton(t('tasks.config.button.import_csv', 'Importuj z CSV'))
        self.btn_import_csv.clicked.connect(self._on_import_csv)
        buttons_layout.addWidget(self.btn_import_csv)

        self.btn_export_csv = QPushButton(t('tasks.config.button.export_csv', 'Eksportuj do CSV'))
        self.btn_export_csv.clicked.connect(self._on_export_csv)
        buttons_layout.addWidget(self.btn_export_csv)

        buttons_layout.addStretch()
        parent_layout.addLayout(buttons_layout)

    def _on_import_csv(self) -> None:
        if not self.local_db:
            QMessageBox.warning(
                self,
                t('tasks.config.csv.import_title', 'Import z CSV'),
                t('tasks.config.csv.import_no_db', 'Brak połączenia z bazą danych.')
            )
            return

        directory = QFileDialog.getExistingDirectory(
            self,
            t('tasks.config.csv.import_select_dir', 'Wybierz katalog z plikami CSV')
        )
        if not directory:
            return

        proceed = QMessageBox.question(
            self,
            t('tasks.config.csv.import_title', 'Import z CSV'),
            t(
                'tasks.config.csv.import_confirm',
                'Import zastąpi bieżące dane użytkownika. Kontynuować?'
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if proceed != QMessageBox.StandardButton.Yes:
            return

        try:
            result = import_tasks_and_kanban_from_csv(self.local_db, directory)
        except Exception as exc:  # noqa: BLE001 - prezentujemy błąd użytkownikowi
            logger.error(f"[TaskConfigDialog] CSV import failed: {exc}")
            QMessageBox.critical(
                self,
                t('tasks.config.csv.import_title', 'Import z CSV'),
                t('tasks.config.csv.import_error', 'Nie udało się zaimportować danych z CSV.')
            )
            return

        summary_lines = [f"{name}: {count}" for name, count in sorted(result.items())]
        summary_text = '\n'.join(summary_lines) if summary_lines else t(
            'tasks.config.csv.import_empty',
            'Nie znaleziono danych do importu.',
        )

        QMessageBox.information(
            self,
            t('tasks.config.csv.import_title', 'Import z CSV'),
            t('tasks.config.csv.import_success', 'Import zakończony powodzeniem.') + '\n' + summary_text
        )

    def _on_export_csv(self) -> None:
        if not self.local_db:
            QMessageBox.warning(
                self,
                t('tasks.config.csv.export_title', 'Eksport do CSV'),
                t('tasks.config.csv.export_no_db', 'Brak połączenia z bazą danych do eksportu.')
            )
            return

        directory = QFileDialog.getExistingDirectory(
            self,
            t('tasks.config.csv.export_select_dir', 'Wybierz katalog docelowy eksportu')
        )
        if not directory:
            return

        try:
            result = export_tasks_and_kanban_to_csv(self.local_db, directory)
        except Exception as exc:  # noqa: BLE001 - pokazujemy błąd użytkownikowi
            logger.error(f"[TaskConfigDialog] CSV export failed: {exc}")
            QMessageBox.critical(
                self,
                t('tasks.config.csv.export_title', 'Eksport do CSV'),
                t('tasks.config.csv.export_error', 'Nie udało się wyeksportować danych do CSV.')
            )
            return

        summary_lines = [f"{name}: {count}" for name, count in sorted(result.items())]
        summary_text = '\n'.join(summary_lines) if summary_lines else t(
            'tasks.config.csv.export_empty',
            'Brak danych do zapisania.',
        )

        QMessageBox.information(
            self,
            t('tasks.config.csv.export_title', 'Eksport do CSV'),
            t('tasks.config.csv.export_success', 'Eksport zakończony powodzeniem.') + '\n' + summary_text
        )

    def _populate_columns_table(self):
        """Wypełnij tabelę kolumnami"""
        self.columns_table.setRowCount(0)
        
        logger.info(f"[TaskConfigDialog] Populating table with {len(self.columns)} columns")
        
        for col in sorted(self.columns, key=lambda x: x['position']):
            row = self.columns_table.rowCount()
            self.columns_table.insertRow(row)
            
            # DEBUG: Wypisz zawartość kolumny
            logger.info(f"[TaskConfigDialog] Row {row}: col = {col}")
            
            # KOLUMNA 0: Pozycja (int)
            position_item = QTableWidgetItem(str(col['position']))
            position_item.setFlags(position_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Tylko do odczytu
            self.columns_table.setItem(row, 0, position_item)
            
            # KOLUMNA 1: Typ
            col_type = col.get('type', 'text')
            # Tłumacz typ kolumny jeśli możliwe
            type_key = f'tasks.config.column_type.{col_type}'
            translated_type = t(type_key)
            # Jeśli tłumaczenie nie istnieje, zostaw oryginalny typ
            if translated_type == type_key:
                translated_type = col_type
            type_item = QTableWidgetItem(translated_type)
            type_item.setFlags(type_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Tylko do odczytu
            self.columns_table.setItem(row, 1, type_item)
            
            # KOLUMNA 2: Nazwa - POPRAWKA: używamy 'id' jako głównego źródła nazwy
            col_name = col.get('id', col.get('name', col.get('column_id', '')))
            logger.info(f"[TaskConfigDialog] Row {row}: Extracted name = '{col_name}'")
            name_item = QTableWidgetItem(col_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)  # Nazwa kolumny nie jest edytowalna
            self.columns_table.setItem(row, 2, name_item)
            
            # KOLUMNA 3: Widoczna w głównym widoku (checkbox)
            chk_visible_main = QCheckBox()
            chk_visible_main.setChecked(col.get('visible_main', False))
            # Sprawdź czy użytkownik może edytować tę właściwość
            if col.get('system') and not col.get('editable'):
                chk_visible_main.setEnabled(False)
            elif col.get('allow_edit') and 'visible_main' not in col.get('allow_edit', []):
                chk_visible_main.setEnabled(False)
            self.columns_table.setCellWidget(row, 3, chk_visible_main)
            
            # KOLUMNA 4: Widoczna w pasku dolnym (checkbox)
            chk_visible_bar = QCheckBox()
            chk_visible_bar.setChecked(col.get('visible_bar', False))
            # Sprawdź czy użytkownik może edytować tę właściwość
            if col.get('system') and not col.get('editable'):
                chk_visible_bar.setEnabled(False)
            elif col.get('allow_edit') and 'visible_bar' not in col.get('allow_edit', []):
                chk_visible_bar.setEnabled(False)
            # Sprawdź limit kolumn w pasku
            chk_visible_bar.toggled.connect(self._check_bar_columns_limit)
            self.columns_table.setCellWidget(row, 4, chk_visible_bar)
            
            # KOLUMNA 5: Wartość domyślna - edytowalna tylko dla text i lista
            col_type = col['type']
            default_val = col.get('default_value', '')
            
            if col_type in ['text', 'tekstowa']:
                # Pole tekstowe dla typów tekstowych
                default_input = QLineEdit(str(default_val))
                self.columns_table.setCellWidget(row, 5, default_input)
            elif col_type == 'lista':
                # ComboBox dla typu lista - wartości z listy własnej
                default_combo = QComboBox()
                list_name = col.get('list_name', '')
                
                # Pobierz wartości z odpowiedniej listy własnej
                list_values = self._get_list_values(list_name)
                if list_values:
                    default_combo.addItems(list_values)
                    if default_val in list_values:
                        default_combo.setCurrentText(str(default_val))
                else:
                    default_combo.addItem("(brak listy)")
                
                self.columns_table.setCellWidget(row, 5, default_combo)
            else:
                # Dla innych typów - tylko wyświetlanie (niemodyfikowalne)
                default_item = QTableWidgetItem(str(default_val))
                default_item.setFlags(default_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                self.columns_table.setItem(row, 5, default_item)
    
    def _get_list_values(self, list_name: str) -> List[str]:
        """Pobierz wartości z listy własnej na podstawie nazwy"""
        for custom_list in self.custom_lists:
            if custom_list.get('name') == list_name:
                return custom_list.get('values', [])
        
        # Dla kolumny Tag zwróć dostępne tagi
        if list_name == 'tags' or list_name == '':
            return [tag.get('name', '') for tag in self.tags]
        
        return []

    @staticmethod
    def _item_text(table: QTableWidget, row: int, column: int) -> str:
        item = table.item(row, column)
        return item.text() if item is not None else ""

    def _populate_tags_table(self):
        """Wypełnij tabelę tagami"""
        self.tags_table.setRowCount(0)
        
        for tag in self.tags:
            row = self.tags_table.rowCount()
            self.tags_table.insertRow(row)
            
            # Nazwa tagu
            self.tags_table.setItem(row, 0, QTableWidgetItem(tag.get('name', '')))
            
            # Kolor
            color_item = QTableWidgetItem()
            color = tag.get('color', '#FFFFFF')
            color_item.setBackground(QColor(color))
            color_item.setText(color)
            self.tags_table.setItem(row, 1, color_item)
            
    
    def _populate_lists_table(self):
        """Wypełnij tabelę listami własnymi"""
        self.lists_table.setRowCount(0)
        
        for custom_list in self.custom_lists:
            row = self.lists_table.rowCount()
            self.lists_table.insertRow(row)
            
            # Nazwa listy
            self.lists_table.setItem(row, 0, QTableWidgetItem(custom_list.get('name', '')))
            
            # Elementy (wyświetl jako string oddzielony przecinkami)
            values = custom_list.get('values', [])
            values_str = ', '.join(values)
            self.lists_table.setItem(row, 1, QTableWidgetItem(values_str))
            
            # Przycisk edycji (placeholder)
            edit_btn = QPushButton("Edytuj")
            edit_btn.clicked.connect(lambda checked, r=row: self._on_edit_list_inline(r))
            self.lists_table.setCellWidget(row, 2, edit_btn)
    
    def _on_edit_tag_inline(self, row: int):
        """Szybka edycja tagu z wiersza"""
        # TODO: Otwórz dialog edycji lub pozwól edytować inline
        QMessageBox.information(self, "Edytuj tag", f"Edycja tagu w wierszu {row}")
    
    def _on_edit_list_inline(self, row: int):
        """Szybka edycja listy z wiersza"""
        # TODO: Otwórz dialog edycji listy
        QMessageBox.information(self, "Edytuj listę", f"Edycja listy w wierszu {row}")


    def _check_bar_columns_limit(self, checked):
        """Sprawdź czy nie przekroczono limitu 5 kolumn w pasku (+ 2 systemowe)"""
        # Jeśli checkbox został odznaczony, nie sprawdzamy limitu
        if not checked:
            return
            
        count = 0
        sender_checkbox = None
        
        for row in range(self.columns_table.rowCount()):
            chk = self.columns_table.cellWidget(row, 4)
            if isinstance(chk, QCheckBox) and chk.isChecked():
                col_name = self._item_text(self.columns_table, row, 2)
                # Zadanie i KanBan są zawsze
                if col_name not in ['Zadanie', 'KanBan']:
                    count += 1
                # Znajdź checkbox który wywołał sygnał
                if chk == self.sender():
                    sender_checkbox = chk
        
        # Jeśli przekroczono limit, odznacz checkbox który został zaznaczony
        if count > 5 and sender_checkbox:
            sender_checkbox.blockSignals(True)  # Zablokuj sygnały żeby nie wywołać pętli
            sender_checkbox.setChecked(False)
            sender_checkbox.blockSignals(False)
            
            QMessageBox.warning(
                self,
                "Limit kolumn",
                "Możesz mieć maksymalnie 5 dodatkowych kolumn widocznych w pasku dolnym\n"
                "(poza polami 'Zadanie' i 'KanBan' które są zawsze widoczne)."
            )

    # ========== HANDLERY KOLUMN ==========
    def _on_add_column(self):
        """Dodaj nową kolumnę użytkownika"""
        # Pobierz listę istniejących nazw kolumn
        existing_columns = [col['id'] for col in self.columns]
        
        # Otwórz dialog dodawania kolumny
        dialog = AddColumnDialog(
            self,
            existing_columns=existing_columns,
            available_lists=self.custom_lists
        )
        
        if dialog.exec():
            # Pobierz dane nowej kolumny
            new_column = dialog.get_column_data()
            
            # Ustaw pozycję na końcu
            max_position = max((col['position'] for col in self.columns), default=0)
            new_column['position'] = max_position + 1
            
            # Dodaj do listy kolumn
            self.columns.append(new_column)
            
            # Odśwież tabelę
            self._populate_columns_table()
            
            # Zaznacz nową kolumnę
            for row in range(self.columns_table.rowCount()):
                if self._item_text(self.columns_table, row, 2) == new_column['id']:
                    self.columns_table.selectRow(row)
                    break
            
            QMessageBox.information(
                self,
                "Sukces",
                f"Dodano nową kolumnę '{new_column['id']}'"
            )

    def _on_edit_column(self):
        """Edytuj wybraną kolumnę"""
        row = self.columns_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Brak zaznaczenia", "Zaznacz kolumnę do edycji")
            return
        
        # Pobierz nazwę kolumny z tabeli
        col_name = self._item_text(self.columns_table, row, 2)
        
        # Znajdź kolumnę w self.columns
        column = next((col for col in self.columns if col['id'] == col_name), None)
        if not column:
            QMessageBox.warning(self, "Błąd", "Nie znaleziono kolumny")
            return
        
        # Pobierz listę istniejących nazw kolumn (bez aktualnej)
        existing_columns = [col['id'] for col in self.columns if col['id'] != col_name]
        
        # Otwórz dialog edycji
        dialog = EditColumnDialog(self, column, existing_columns, self.custom_lists)
        
        if dialog.exec():
            # Zaktualizuj kolumnę
            updated_column = dialog.get_column_data()
            
            # Znajdź i zaktualizuj w liście
            for i, col in enumerate(self.columns):
                if col['id'] == col_name:
                    self.columns[i] = updated_column
                    break
            
            # Odśwież tabelę
            self._populate_columns_table()
            
            # Znajdź i zaznacz zaktualizowaną kolumnę
            for row in range(self.columns_table.rowCount()):
                if self._item_text(self.columns_table, row, 2) == updated_column['id']:
                    self.columns_table.selectRow(row)
                    break
            
            QMessageBox.information(self, "Sukces", f"Kolumna '{updated_column['id']}' została zaktualizowana")

    def _on_delete_column(self):
        """Usuń wybraną kolumnę (tylko niestandardowe)"""
        row = self.columns_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Brak zaznaczenia", "Zaznacz kolumnę do usunięcia")
            return
        
        col_name = self._item_text(self.columns_table, row, 2)
        col = next((c for c in self.columns if c['id'] == col_name), None)
        
        if col and col.get('system'):
            QMessageBox.warning(self, "Błąd", "Nie można usunąć kolumny systemowej")
            return
        
        # Potwierdź usunięcie
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć kolumnę '{col_name}'?\n\n"
            "Wszystkie dane w tej kolumnie zostaną utracone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Usuń kolumnę z listy
            self.columns = [c for c in self.columns if c['id'] != col_name]
            
            # Odśwież tabelę
            self._populate_columns_table()
            
            QMessageBox.information(self, "Sukces", f"Kolumna '{col_name}' została usunięta")
        QMessageBox.information(self, "Usuń kolumnę", "Funkcja w przygotowaniu")

    def _on_move_column_up(self):
        """Przesuń kolumnę w górę"""
        row = self.columns_table.currentRow()
        if row <= 0:
            return
        
        # Pobierz nazwę kolumny
        col_name = self._item_text(self.columns_table, row, 2)
        col_above = self._item_text(self.columns_table, row - 1, 2)
        
        # Znajdź kolumny w liście
        current_col = next((c for c in self.columns if c['id'] == col_name), None)
        above_col = next((c for c in self.columns if c['id'] == col_above), None)
        
        # Sprawdź czy którakolwiek ma zablokowaną pozycję
        if current_col and current_col.get('locked_position'):
            QMessageBox.warning(self, "Zablokowane", 
                              f"Kolumna '{col_name}' ma zablokowaną pozycję i nie może być przesunięta.")
            return
        
        if above_col and above_col.get('locked_position'):
            QMessageBox.warning(self, "Zablokowane", 
                              f"Nie można przesunąć powyżej kolumny '{col_above}' - ma zablokowaną pozycję.")
            return
        
        # Zamień pozycje
        for c in self.columns:
            if c['id'] == col_name:
                c['position'] -= 1
            elif c['id'] == col_above:
                c['position'] += 1
        
        self._populate_columns_table()
        self.columns_table.selectRow(row - 1)

    def _on_move_column_down(self):
        """Przesuń kolumnę w dół"""
        row = self.columns_table.currentRow()
        if row < 0 or row >= self.columns_table.rowCount() - 1:
            return
        
        # Pobierz nazwę kolumny
        col_name = self._item_text(self.columns_table, row, 2)
        col_below = self._item_text(self.columns_table, row + 1, 2)
        
        # Znajdź kolumny w liście
        current_col = next((c for c in self.columns if c['id'] == col_name), None)
        below_col = next((c for c in self.columns if c['id'] == col_below), None)
        
        # Sprawdź czy którakolwiek ma zablokowaną pozycję
        if current_col and current_col.get('locked_position'):
            QMessageBox.warning(self, "Zablokowane", 
                              f"Kolumna '{col_name}' ma zablokowaną pozycję i nie może być przesunięta.")
            return
        
        if below_col and below_col.get('locked_position'):
            QMessageBox.warning(self, "Zablokowane", 
                              f"Nie można przesunąć poniżej kolumny '{col_below}' - ma zablokowaną pozycję.")
            return
        
        # Zamień pozycje
        for c in self.columns:
            if c['id'] == col_name:
                c['position'] += 1
            elif c['id'] == col_below:
                c['position'] -= 1
        
        self._populate_columns_table()
        self.columns_table.selectRow(row + 1)

    # ========== HANDLERY TAGÓW ==========
    def _on_add_tag(self):
        """Dodaj nowy tag"""
        # Pobierz listę istniejących nazw tagów
        existing_tags = [tag['name'] for tag in self.tags]
        
        # Otwórz dialog dodawania
        dialog = AddTagDialog(self, existing_tags)
        
        if dialog.exec():
            # Pobierz dane nowego tagu
            new_tag = dialog.get_tag_data()
            
            # Dodaj do listy
            self.tags.append(new_tag)
            
            # Odśwież tabelę
            self._populate_tags_table()
            
            # Zaznacz nowo dodany tag
            for row in range(self.tags_table.rowCount()):
                if self._item_text(self.tags_table, row, 0) == new_tag['name']:
                    self.tags_table.selectRow(row)
                    break
            
            QMessageBox.information(self, "Sukces", f"Tag '{new_tag['name']}' został dodany")

    def _on_edit_tag(self):
        """Edytuj tag"""
        row = self.tags_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Brak zaznaczenia", "Zaznacz tag do edycji")
            return
        
        # Pobierz nazwę tagu z tabeli
        tag_name = self._item_text(self.tags_table, row, 0)
        
        # Znajdź tag w self.tags
        tag = next((t for t in self.tags if t['name'] == tag_name), None)
        if not tag:
            QMessageBox.warning(self, "Błąd", "Nie znaleziono tagu")
            return
        
        # Pobierz listę istniejących nazw tagów (bez aktualnego)
        existing_tags = [t['name'] for t in self.tags if t['name'] != tag_name]
        
        # Otwórz dialog edycji
        dialog = EditTagDialog(self, tag, existing_tags)
        
        if dialog.exec():
            # Zaktualizuj tag
            updated_tag = dialog.get_tag_data()
            
            # Znajdź i zaktualizuj w liście
            for i, t in enumerate(self.tags):
                if t['name'] == tag_name:
                    self.tags[i] = updated_tag
                    break
            
            # Odśwież tabelę
            self._populate_tags_table()
            
            # Zaznacz zaktualizowany tag
            for row in range(self.tags_table.rowCount()):
                if self._item_text(self.tags_table, row, 0) == updated_tag['name']:
                    self.tags_table.selectRow(row)
                    break
            
            QMessageBox.information(self, "Sukces", f"Tag '{updated_tag['name']}' został zaktualizowany")

    def _on_delete_tag(self):
        """Usuń tag"""
        row = self.tags_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Brak zaznaczenia", "Zaznacz tag do usunięcia")
            return
        
        tag_name = self._item_text(self.tags_table, row, 0)
        
        # Potwierdź usunięcie
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć tag '{tag_name}'?\n\n"
            "Tag zostanie również usunięty ze wszystkich zadań, które go używają.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Usuń tag z listy
            self.tags = [t for t in self.tags if t['name'] != tag_name]
            
            # Odśwież tabelę
            self._populate_tags_table()
            
            QMessageBox.information(self, "Sukces", f"Tag '{tag_name}' został usunięty")

    # ========== HANDLERY LIST ==========
    def _on_add_list(self):
        """Dodaj nową listę"""
        # Pobierz listę istniejących nazw list
        existing_lists = [lst['name'] for lst in self.custom_lists]
        
        # Otwórz dialog dodawania
        dialog = AddListDialog(self, existing_lists)
        
        if dialog.exec():
            # Pobierz dane nowej listy
            new_list = dialog.get_list_data()
            
            # Dodaj do listy
            self.custom_lists.append(new_list)
            
            # Odśwież tabelę
            self._populate_lists_table()
            
            # Zaznacz nowo dodaną listę
            for row in range(self.lists_table.rowCount()):
                if self._item_text(self.lists_table, row, 0) == new_list['name']:
                    self.lists_table.selectRow(row)
                    break
            
            QMessageBox.information(self, "Sukces", f"Lista '{new_list['name']}' została dodana")

    def _on_edit_list(self):
        """Edytuj listę"""
        row = self.lists_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Brak zaznaczenia", "Zaznacz listę do edycji")
            return
        
        # Pobierz nazwę listy z tabeli
        list_name = self._item_text(self.lists_table, row, 0)
        
        # Znajdź listę w self.custom_lists
        list_data = next((l for l in self.custom_lists if l['name'] == list_name), None)
        if not list_data:
            QMessageBox.warning(self, "Błąd", "Nie znaleziono listy")
            return
        
        # Pobierz listę istniejących nazw list (bez aktualnej)
        existing_lists = [l['name'] for l in self.custom_lists if l['name'] != list_name]
        
        # Otwórz dialog edycji
        dialog = EditListDialog(self, list_data, existing_lists)
        
        if dialog.exec():
            # Zaktualizuj listę
            updated_list = dialog.get_list_data()
            
            # Znajdź i zaktualizuj w liście
            for i, l in enumerate(self.custom_lists):
                if l['name'] == list_name:
                    self.custom_lists[i] = updated_list
                    break
            
            # Odśwież tabelę
            self._populate_lists_table()
            
            # Zaznacz zaktualizowaną listę
            for row in range(self.lists_table.rowCount()):
                if self._item_text(self.lists_table, row, 0) == updated_list['name']:
                    self.lists_table.selectRow(row)
                    break
            
            # Jeśli zmieniono nazwę listy, zaktualizuj również kolumny używające tej listy
            if list_name != updated_list['name']:
                for col in self.columns:
                    if col.get('list_name') == list_name:
                        col['list_name'] = updated_list['name']
                self._populate_columns_table()
            
            QMessageBox.information(self, "Sukces", f"Lista '{updated_list['name']}' została zaktualizowana")

    def _on_delete_list(self):
        """Usuń listę"""
        row = self.lists_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Brak zaznaczenia", "Zaznacz listę do usunięcia")
            return
        
        list_name = self._item_text(self.lists_table, row, 0)
        
        # Sprawdź czy lista jest używana przez jakieś kolumny
        used_by = []
        for col in self.columns:
            if col.get('list_name') == list_name:
                used_by.append(col['id'])
        
        if used_by:
            QMessageBox.warning(
                self,
                "Nie można usunąć",
                f"Lista '{list_name}' jest używana przez następujące kolumny:\n" +
                ", ".join(used_by) + "\n\n" +
                "Usuń lub zmień typ tych kolumn przed usunięciem listy."
            )
            return
        
        # Potwierdź usunięcie
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć listę '{list_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Usuń listę z listy
            self.custom_lists = [l for l in self.custom_lists if l['name'] != list_name]
            
            # Odśwież tabelę
            self._populate_lists_table()
            
            QMessageBox.information(self, "Sukces", f"Lista '{list_name}' została usunięta")

    def get_config(self) -> Dict[str, Any]:
        """Zwróć pełną konfigurację"""
        # Zaktualizuj kolumny z tabeli
        for row in range(self.columns_table.rowCount()):
            col_name = self._item_text(self.columns_table, row, 2)
            # Szukaj kolumny po 'name' lub 'id' (oba powinny być takie same)
            col = next((c for c in self.columns if c.get('name', c.get('id')) == col_name or c.get('id') == col_name), None)
            if col:
                # Widoczność w głównym widoku
                chk_main = self.columns_table.cellWidget(row, 3)
                if isinstance(chk_main, QCheckBox):
                    col['visible_main'] = chk_main.isChecked()
                
                # Widoczność w pasku
                chk_bar = self.columns_table.cellWidget(row, 4)
                if isinstance(chk_bar, QCheckBox):
                    col['visible_bar'] = chk_bar.isChecked()
                
                # Wartość domyślna
                default_widget = self.columns_table.cellWidget(row, 5)
                if isinstance(default_widget, QLineEdit):
                    # Dla typów tekstowych
                    col['default_value'] = default_widget.text()
                elif isinstance(default_widget, QComboBox):
                    # Dla typów lista
                    col['default_value'] = default_widget.currentText()
                else:
                    # Dla innych typów pobierz z QTableWidgetItem
                    default_item = self.columns_table.item(row, 5)
                    if default_item:
                        col['default_value'] = default_item.text()
        
        # Zaktualizuj ustawienia
        self.settings['auto_archive_enabled'] = self.chk_auto_archive.isChecked()
        self.settings['auto_archive_after_days'] = self.spin_archive_days.value()
        self.settings['auto_move_completed'] = self.chk_auto_move.isChecked()
        self.settings['auto_archive_completed'] = self.chk_auto_archive_completed.isChecked()
        
        return {
            'columns': self.columns,
            'tags': self.tags,
            'custom_lists': self.custom_lists,
            'settings': self.settings
        }

    def accept(self):
        """Zapisz konfigurację do bazy danych i zamknij dialog"""
        if self.local_db:
            try:
                # Pobierz aktualną konfigurację
                config = self.get_config()
                
                # Zapisz kolumny
                if self.local_db.save_columns_config(config['columns']):
                    logger.info("[TaskConfigDialog] Columns configuration saved successfully")
                else:
                    logger.error("[TaskConfigDialog] Failed to save columns configuration")
                
                # Zapisz tagi
                if self.local_db.save_tags(config['tags']):
                    logger.info("[TaskConfigDialog] Tags saved successfully")
                else:
                    logger.error("[TaskConfigDialog] Failed to save tags")
                
                # Zapisz listy własne
                if self.local_db.save_custom_lists(config['custom_lists']):
                    logger.info("[TaskConfigDialog] Custom lists saved successfully")
                else:
                    logger.error("[TaskConfigDialog] Failed to save custom lists")

                # Zapisz ustawienia ogólne
                settings_saved = True
                for key, value in config.get('settings', {}).items():
                    if not self.local_db.save_setting(key, value):
                        settings_saved = False
                        logger.error(f"[TaskConfigDialog] Failed to save setting '{key}'")
                if settings_saved:
                    logger.info("[TaskConfigDialog] General settings saved successfully")
                
                logger.info("[TaskConfigDialog] Configuration saved to database")
                
            except Exception as e:
                logger.error(f"[TaskConfigDialog] Failed to save configuration: {e}")
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.warning(
                    self, 
                    "Błąd", 
                    f"Nie udało się zapisać konfiguracji:\n{str(e)}"
                )
                return  # Nie zamykaj dialogu jeśli zapis się nie powiódł
        else:
            logger.warning("[TaskConfigDialog] No database available, configuration not saved")
        
        # Wywołaj oryginalną metodę accept() z QDialog
        super().accept()
