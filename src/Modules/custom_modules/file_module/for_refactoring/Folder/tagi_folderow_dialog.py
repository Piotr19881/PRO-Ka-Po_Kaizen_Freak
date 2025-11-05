"""
Dialog do zarządzania tagami folderów z kolorami
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget, QListWidgetItem,
    QLineEdit, QPushButton, QLabel, QColorDialog, QWidget, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor


class ColoredTagItem(QWidget):
    """Widget reprezentujący tag z kolorem"""
    
    def __init__(self, tag_name, color, parent=None):
        super().__init__(parent)
        self.tag_name = tag_name
        self.color = color
        
        layout = QHBoxLayout()
        layout.setContentsMargins(5, 2, 5, 2)
        
        # Kolorowy kwadrat
        color_label = QLabel()
        color_label.setFixedSize(20, 20)
        color_label.setStyleSheet(f"background-color: {color}; border: 1px solid #000;")
        
        # Nazwa tagu
        text_label = QLabel(tag_name)
        text_label.setStyleSheet(f"color: {color}; font-weight: bold;")
        
        layout.addWidget(color_label)
        layout.addWidget(text_label)
        layout.addStretch()
        
        self.setLayout(layout)


class TagiFolderowDialog(QDialog):
    """Dialog do zarządzania tagami z kolorami"""
    
    def __init__(self, tags_dict, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zarządzanie tagami")
        self.setMinimumSize(500, 400)
        
        # Słownik tagów: {nazwa: kolor}
        self.tags_dict = tags_dict.copy()
        self.selected_color = "#FF5733"  # Domyślny kolor
        
        self.init_ui()
        self.load_tags()
    
    def init_ui(self):
        """Inicjalizacja interfejsu"""
        main_layout = QVBoxLayout()
        
        # Nagłówek
        header_label = QLabel("Lista tagów:")
        header_label.setStyleSheet("font-weight: bold; font-size: 12pt;")
        main_layout.addWidget(header_label)
        
        # Lista tagów
        self.tags_list = QListWidget()
        self.tags_list.setAlternatingRowColors(True)
        main_layout.addWidget(self.tags_list)
        
        # Sekcja dodawania nowego tagu
        add_section_label = QLabel("Nowy tag:")
        add_section_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        main_layout.addWidget(add_section_label)
        
        # Layout dla nowego tagu
        new_tag_layout = QHBoxLayout()
        
        # Pole tekstowe
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("Nazwa nowego tagu...")
        new_tag_layout.addWidget(self.new_tag_input)
        
        # Przycisk wyboru koloru
        self.color_button = QPushButton("Wybierz kolor")
        self.color_button.clicked.connect(self.choose_color)
        self.update_color_button()
        new_tag_layout.addWidget(self.color_button)
        
        main_layout.addLayout(new_tag_layout)
        
        # Przyciski akcji
        buttons_layout = QHBoxLayout()
        
        # Przycisk Dodaj
        btn_add = QPushButton("Dodaj")
        btn_add.clicked.connect(self.add_tag)
        btn_add.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; padding: 8px;")
        buttons_layout.addWidget(btn_add)
        
        # Przycisk Usuń
        btn_remove = QPushButton("Usuń")
        btn_remove.clicked.connect(self.remove_tag)
        btn_remove.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 8px;")
        buttons_layout.addWidget(btn_remove)
        
        main_layout.addLayout(buttons_layout)
        
        # Przycisk Zamknij
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        btn_close.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 10px; margin-top: 10px;")
        main_layout.addWidget(btn_close)
        
        self.setLayout(main_layout)
    
    def load_tags(self):
        """Ładuje tagi do listy"""
        self.tags_list.clear()
        
        for tag_name, color in sorted(self.tags_dict.items()):
            item = QListWidgetItem(self.tags_list)
            widget = ColoredTagItem(tag_name, color)
            item.setSizeHint(widget.sizeHint())
            self.tags_list.addItem(item)
            self.tags_list.setItemWidget(item, widget)
    
    def choose_color(self):
        """Otwiera dialog wyboru koloru"""
        color = QColorDialog.getColor(QColor(self.selected_color), self, "Wybierz kolor tagu")
        
        if color.isValid():
            self.selected_color = color.name()
            self.update_color_button()
    
    def update_color_button(self):
        """Aktualizuje wygląd przycisku koloru"""
        self.color_button.setStyleSheet(
            f"background-color: {self.selected_color}; "
            f"color: {'white' if self.is_dark_color(self.selected_color) else 'black'}; "
            f"font-weight: bold; padding: 5px;"
        )
    
    def is_dark_color(self, hex_color):
        """Sprawdza czy kolor jest ciemny"""
        color = QColor(hex_color)
        # Oblicz jasność koloru
        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        return brightness < 128
    
    def add_tag(self):
        """Dodaje nowy tag"""
        tag_name = self.new_tag_input.text().strip()
        
        if not tag_name:
            QMessageBox.warning(self, "Błąd", "Wprowadź nazwę tagu!")
            return
        
        if tag_name in self.tags_dict:
            QMessageBox.warning(self, "Błąd", "Tag o tej nazwie już istnieje!")
            return
        
        # Dodaj tag
        self.tags_dict[tag_name] = self.selected_color
        self.load_tags()
        
        # Wyczyść pole
        self.new_tag_input.clear()
        
        QMessageBox.information(self, "Sukces", f"Tag '{tag_name}' został dodany!")
    
    def remove_tag(self):
        """Usuwa zaznaczony tag"""
        current_item = self.tags_list.currentItem()
        
        if not current_item:
            QMessageBox.warning(self, "Błąd", "Zaznacz tag do usunięcia!")
            return
        
        # Pobierz widget i nazwę tagu
        widget = self.tags_list.itemWidget(current_item)
        if widget:
            tag_name = widget.tag_name
            
            reply = QMessageBox.question(
                self,
                "Potwierdzenie",
                f"Czy na pewno chcesz usunąć tag '{tag_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del self.tags_dict[tag_name]
                self.load_tags()
                QMessageBox.information(self, "Sukces", f"Tag '{tag_name}' został usunięty!")
    
    def get_tags(self):
        """Zwraca słownik tagów"""
        return self.tags_dict
