"""
Moduł zarządzania szablonami odpowiedzi email

Funkcjonalność:
- Panel boczny z drzewem szablonów
- Kategoryzowanie szablonów z kolorami
- Wstawianie szablonów do treści lub kopiowanie do schowka
- Zarządzanie szablonami i kategoriami

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-08
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QBrush
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QCheckBox,
    QDialog,
    QLineEdit,
    QTextEdit,
    QFormLayout,
    QComboBox,
    QColorDialog,
    QMessageBox,
    QLabel,
)


class TemplateManager:
    """Zarządza zapisem i odczytem szablonów"""
    
    def __init__(self):
        self.templates_file = Path("mail_client/mail_templates.json")
        self.templates_file.parent.mkdir(parents=True, exist_ok=True)
        
        self.templates = self.load_templates()
        self.categories = self.load_categories()
    
    def load_templates(self) -> List[Dict[str, Any]]:
        """Wczytuje szablony z pliku"""
        if self.templates_file.exists():
            try:
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("templates", [])
            except Exception:
                return []
        return []
    
    def load_categories(self) -> List[Dict[str, str]]:
        """Wczytuje kategorie z pliku"""
        if self.templates_file.exists():
            try:
                with open(self.templates_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return data.get("categories", [])
            except Exception:
                return []
        return []
    
    def save_data(self):
        """Zapisuje szablony i kategorie do pliku"""
        try:
            data = {
                "templates": self.templates,
                "categories": self.categories
            }
            with open(self.templates_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Error saving templates: {e}")
    
    def add_template(self, name: str, content: str, category: str = ""):
        """Dodaje nowy szablon"""
        template = {
            "name": name,
            "content": content,
            "category": category
        }
        self.templates.append(template)
        self.save_data()
    
    def update_template(self, old_name: str, name: str, content: str, category: str = ""):
        """Aktualizuje istniejący szablon"""
        for template in self.templates:
            if template["name"] == old_name:
                template["name"] = name
                template["content"] = content
                template["category"] = category
                break
        self.save_data()
    
    def delete_template(self, name: str):
        """Usuwa szablon"""
        self.templates = [t for t in self.templates if t["name"] != name]
        self.save_data()
    
    def add_category(self, name: str, color: str = "#808080"):
        """Dodaje nową kategorię"""
        category = {
            "name": name,
            "color": color
        }
        self.categories.append(category)
        self.save_data()
    
    def update_category(self, old_name: str, name: str, color: str):
        """Aktualizuje kategorię"""
        for category in self.categories:
            if category["name"] == old_name:
                category["name"] = name
                category["color"] = color
                # Aktualizuj szablony używające tej kategorii
                for template in self.templates:
                    if template.get("category") == old_name:
                        template["category"] = name
                break
        self.save_data()
    
    def delete_category(self, name: str):
        """Usuwa kategorię"""
        self.categories = [c for c in self.categories if c["name"] != name]
        # Usuń kategorię z szablonów
        for template in self.templates:
            if template.get("category") == name:
                template["category"] = ""
        self.save_data()
    
    def get_category_color(self, category_name: str) -> str:
        """Zwraca kolor kategorii"""
        for category in self.categories:
            if category["name"] == category_name:
                return category.get("color", "#808080")
        return "#808080"


class TemplateDialog(QDialog):
    """Dialog dodawania/edycji szablonu"""
    
    def __init__(self, parent=None, template_manager=None, template=None):
        super().__init__(parent)
        self.template_manager = template_manager
        self.template = template
        self.setWindowTitle("Szablon" if template else "Nowy szablon")
        self.setMinimumSize(500, 400)
        self.init_ui()
        
        if template:
            self.load_template_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Nazwa szablonu")
        form_layout.addRow("Nazwa:", self.name_field)
        
        self.category_combo = QComboBox()
        self.category_combo.addItem("(bez kategorii)", "")
        if self.template_manager:
            for category in self.template_manager.categories:
                self.category_combo.addItem(category["name"], category["name"])
        form_layout.addRow("Kategoria:", self.category_combo)
        
        layout.addLayout(form_layout)
        
        layout.addWidget(QLabel("Treść szablonu:"))
        self.content_field = QTextEdit()
        self.content_field.setPlaceholderText("Treść szablonu...")
        layout.addWidget(self.content_field)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Zapisz")
        save_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def load_template_data(self):
        """Wczytuje dane szablonu do pól"""
        if self.template:
            self.name_field.setText(self.template.get("name", ""))
            self.content_field.setPlainText(self.template.get("content", ""))
            
            category = self.template.get("category", "")
            index = self.category_combo.findData(category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
    
    def get_template_data(self) -> Dict[str, str]:
        """Zwraca dane z formularza"""
        return {
            "name": self.name_field.text().strip(),
            "content": self.content_field.toPlainText(),
            "category": self.category_combo.currentData() or ""
        }


class CategoryDialog(QDialog):
    """Dialog dodawania/edycji kategorii"""
    
    def __init__(self, parent=None, category=None):
        super().__init__(parent)
        self.category = category
        self.selected_color = category.get("color", "#808080") if category else "#808080"
        self.setWindowTitle("Kategoria" if category else "Nowa kategoria")
        self.setMinimumSize(400, 150)
        self.init_ui()
        
        if category:
            self.load_category_data()
    
    def init_ui(self):
        layout = QVBoxLayout()
        
        form_layout = QFormLayout()
        
        self.name_field = QLineEdit()
        self.name_field.setPlaceholderText("Nazwa kategorii")
        form_layout.addRow("Nazwa:", self.name_field)
        
        color_layout = QHBoxLayout()
        self.color_btn = QPushButton("Wybierz kolor")
        self.color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_btn)
        
        self.color_preview = QLabel("     ")
        self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #ccc;")
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()
        
        form_layout.addRow("Kolor:", color_layout)
        
        layout.addLayout(form_layout)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        
        save_btn = QPushButton("💾 Zapisz")
        save_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(save_btn)
        
        cancel_btn = QPushButton("❌ Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)
        self.setLayout(layout)
    
    def choose_color(self):
        """Otwiera dialog wyboru koloru"""
        color = QColorDialog.getColor(QColor(self.selected_color), self)
        if color.isValid():
            self.selected_color = color.name()
            self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #ccc;")
    
    def load_category_data(self):
        """Wczytuje dane kategorii do pól"""
        if self.category:
            self.name_field.setText(self.category.get("name", ""))
            self.selected_color = self.category.get("color", "#808080")
            self.color_preview.setStyleSheet(f"background-color: {self.selected_color}; border: 1px solid #ccc;")
    
    def get_category_data(self) -> Dict[str, str]:
        """Zwraca dane z formularza"""
        return {
            "name": self.name_field.text().strip(),
            "color": self.selected_color
        }


class TemplatesPanel(QWidget):
    """Panel szablonów w oknie nowej wiadomości"""
    
    template_selected = pyqtSignal(str)  # Emituje treść szablonu
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.template_manager = TemplateManager()
        self.init_ui()
        self.refresh_tree()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Nagłówek
        header_label = QLabel("📋 Szablony")
        header_label.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        layout.addWidget(header_label)
        
        # Przyciski zarządzania szablonami
        templates_btn_layout = QHBoxLayout()
        
        add_template_btn = QPushButton("➕")
        add_template_btn.setToolTip("Dodaj szablon")
        add_template_btn.setMaximumWidth(40)
        add_template_btn.clicked.connect(self.add_template)
        templates_btn_layout.addWidget(add_template_btn)
        
        edit_template_btn = QPushButton("✏️")
        edit_template_btn.setToolTip("Edytuj szablon")
        edit_template_btn.setMaximumWidth(40)
        edit_template_btn.clicked.connect(self.edit_template)
        templates_btn_layout.addWidget(edit_template_btn)
        
        delete_template_btn = QPushButton("🗑️")
        delete_template_btn.setToolTip("Usuń szablon")
        delete_template_btn.setMaximumWidth(40)
        delete_template_btn.clicked.connect(self.delete_template)
        templates_btn_layout.addWidget(delete_template_btn)
        
        templates_btn_layout.addStretch()
        layout.addLayout(templates_btn_layout)
        
        # Przyciski zarządzania kategoriami
        categories_btn_layout = QHBoxLayout()
        
        add_category_btn = QPushButton("📁➕")
        add_category_btn.setToolTip("Dodaj kategorię")
        add_category_btn.clicked.connect(self.add_category)
        categories_btn_layout.addWidget(add_category_btn)
        
        edit_category_btn = QPushButton("📁✏️")
        edit_category_btn.setToolTip("Edytuj kategorię")
        edit_category_btn.clicked.connect(self.edit_category)
        categories_btn_layout.addWidget(edit_category_btn)
        
        delete_category_btn = QPushButton("📁🗑️")
        delete_category_btn.setToolTip("Usuń kategorię")
        delete_category_btn.clicked.connect(self.delete_category)
        categories_btn_layout.addWidget(delete_category_btn)
        
        layout.addLayout(categories_btn_layout)
        
        # Checkbox "Wstaw"
        self.insert_checkbox = QCheckBox("Wstaw do treści (w przeciwnym razie kopiuj)")
        self.insert_checkbox.setChecked(True)
        layout.addWidget(self.insert_checkbox)
        
        # Drzewo szablonów
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Szablon"])
        self.tree.setAlternatingRowColors(True)
        self.tree.itemDoubleClicked.connect(self.on_template_double_clicked)
        layout.addWidget(self.tree)
        
        self.setLayout(layout)
    
    def refresh_tree(self):
        """Odświeża drzewo szablonów"""
        self.tree.clear()
        
        # Grupuj szablony według kategorii
        templates_by_category: Dict[str, List[Dict]] = {}
        for template in self.template_manager.templates:
            category = template.get("category", "")
            if category not in templates_by_category:
                templates_by_category[category] = []
            templates_by_category[category].append(template)
        
        # Dodaj kategorie i szablony
        for category_name in sorted(templates_by_category.keys()):
            if category_name:
                # Kategoria z kolorem
                category_item = QTreeWidgetItem(self.tree, [category_name])
                category_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "category", "name": category_name})
                
                color = self.template_manager.get_category_color(category_name)
                category_item.setForeground(0, QBrush(QColor(color)))
                category_item.setExpanded(True)
                
                # Szablony w kategorii
                for template in templates_by_category[category_name]:
                    template_item = QTreeWidgetItem(category_item, [template["name"]])
                    template_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "template", "data": template})
            else:
                # Szablony bez kategorii
                for template in templates_by_category[category_name]:
                    template_item = QTreeWidgetItem(self.tree, [template["name"]])
                    template_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "template", "data": template})
    
    def on_template_double_clicked(self, item, column):
        """Obsługuje dwukrotne kliknięcie na szablon"""
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "template":
            return
        
        template = data.get("data")
        if not template:
            return
        
        content = template.get("content", "")
        
        if self.insert_checkbox.isChecked():
            # Wstaw do treści
            self.template_selected.emit(content)
        else:
            # Kopiuj do schowka
            clipboard = QApplication.clipboard()
            if clipboard:
                clipboard.setText(content)
                QMessageBox.information(self, "Skopiowano", "Szablon został skopiowany do schowka")
    
    def add_template(self):
        """Dodaje nowy szablon"""
        dialog = TemplateDialog(self, self.template_manager)
        if dialog.exec():
            data = dialog.get_template_data()
            if data["name"]:
                self.template_manager.add_template(data["name"], data["content"], data["category"])
                self.refresh_tree()
    
    def edit_template(self):
        """Edytuje wybrany szablon"""
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Błąd", "Wybierz szablon do edycji")
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "template":
            QMessageBox.warning(self, "Błąd", "Wybierz szablon do edycji")
            return
        
        template = data.get("data")
        dialog = TemplateDialog(self, self.template_manager, template)
        if dialog.exec():
            new_data = dialog.get_template_data()
            if new_data["name"]:
                self.template_manager.update_template(
                    template["name"],
                    new_data["name"],
                    new_data["content"],
                    new_data["category"]
                )
                self.refresh_tree()
    
    def delete_template(self):
        """Usuwa wybrany szablon"""
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Błąd", "Wybierz szablon do usunięcia")
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "template":
            QMessageBox.warning(self, "Błąd", "Wybierz szablon do usunięcia")
            return
        
        template = data.get("data")
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć szablon '{template['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.template_manager.delete_template(template["name"])
            self.refresh_tree()
    
    def add_category(self):
        """Dodaje nową kategorię"""
        dialog = CategoryDialog(self)
        if dialog.exec():
            data = dialog.get_category_data()
            if data["name"]:
                self.template_manager.add_category(data["name"], data["color"])
                self.refresh_tree()
    
    def edit_category(self):
        """Edytuje wybraną kategorię"""
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Błąd", "Wybierz kategorię do edycji")
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "category":
            QMessageBox.warning(self, "Błąd", "Wybierz kategorię do edycji")
            return
        
        category_name = data.get("name")
        category = next((c for c in self.template_manager.categories if c["name"] == category_name), None)
        
        if not category:
            return
        
        dialog = CategoryDialog(self, category)
        if dialog.exec():
            new_data = dialog.get_category_data()
            if new_data["name"]:
                self.template_manager.update_category(category["name"], new_data["name"], new_data["color"])
                self.refresh_tree()
    
    def delete_category(self):
        """Usuwa wybraną kategorię"""
        item = self.tree.currentItem()
        if not item:
            QMessageBox.warning(self, "Błąd", "Wybierz kategorię do usunięcia")
            return
        
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not data or data.get("type") != "category":
            QMessageBox.warning(self, "Błąd", "Wybierz kategorię do usunięcia")
            return
        
        category_name = data.get("name")
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć kategorię '{category_name}'?\n"
            "Szablony w tej kategorii nie zostaną usunięte.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.template_manager.delete_category(category_name)
            self.refresh_tree()
