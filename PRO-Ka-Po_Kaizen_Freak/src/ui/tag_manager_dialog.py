"""
Tag Manager Dialog
==================

Dialog do zarządzania tagami nagrań - dodawanie, edycja, usuwanie i kolorowanie.
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QColorDialog,
    QMessageBox, QWidget, QFormLayout, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter
from typing import List, Dict, Optional
from loguru import logger
import json

from ..utils.theme_manager import get_theme_manager


class TagManagerDialog(QDialog):
    """Dialog zarządzania tagami"""
    
    tags_changed = pyqtSignal()  # Sygnał emitowany gdy tagi się zmienią
    
    def __init__(self, db_manager, user_id: str, parent=None):
        """
        Inicjalizacja dialogu.
        
        Args:
            db_manager: CallCryptorDatabase instance
            user_id: ID użytkownika
            parent: Widget rodzica
        """
        super().__init__(parent)
        self.db_manager = db_manager
        self.user_id = user_id
        self.current_tags = {}  # {tag_name: color}
        self.theme_manager = get_theme_manager()
        
        self.setWindowTitle("🏷️ Zarządzanie tagami")
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        self.setModal(True)
        
        self._load_tags()
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === NAGŁÓWEK ===
        header = QLabel("Zarządzaj tagami dla swoich nagrań")
        header.setStyleSheet("font-size: 14px; font-weight: bold; color: #333;")
        layout.addWidget(header)
        
        # === GŁÓWNA SEKCJA ===
        main_layout = QHBoxLayout()
        
        # LISTA TAGÓW (lewa strona)
        left_panel = QVBoxLayout()
        
        list_label = QLabel("Istniejące tagi:")
        list_label.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(list_label)
        
        self.tags_list = QListWidget()
        self.tags_list.setMinimumWidth(250)
        self.tags_list.currentItemChanged.connect(self._on_tag_selected)
        left_panel.addWidget(self.tags_list)
        
        # Przyciski pod listą
        list_buttons = QHBoxLayout()
        
        self.delete_btn = QPushButton("🗑️ Usuń")
        self.delete_btn.setEnabled(False)
        self.delete_btn.clicked.connect(self._delete_tag)
        list_buttons.addWidget(self.delete_btn)
        
        list_buttons.addStretch()
        
        left_panel.addLayout(list_buttons)
        
        main_layout.addLayout(left_panel)
        
        # SEPARATOR
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.VLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)
        
        # PANEL EDYCJI (prawa strona)
        right_panel = QVBoxLayout()
        
        # Nowy tag
        new_tag_label = QLabel("Dodaj nowy tag:")
        new_tag_label.setStyleSheet("font-weight: bold;")
        right_panel.addWidget(new_tag_label)
        
        new_tag_form = QFormLayout()
        
        self.new_tag_input = QLineEdit()
        self.new_tag_input.setPlaceholderText("Nazwa tagu (np. Ważne)")
        self.new_tag_input.returnPressed.connect(self._add_tag)
        new_tag_form.addRow("Nazwa:", self.new_tag_input)
        
        # Wybór koloru
        color_layout = QHBoxLayout()
        
        self.new_color_btn = QPushButton("Wybierz kolor")
        self.new_color_btn.setMinimumHeight(35)
        self.new_color_btn.clicked.connect(self._pick_new_color)
        color_layout.addWidget(self.new_color_btn)
        
        self.new_color_preview = QLabel()
        self.new_color_preview.setFixedSize(35, 35)
        self.new_color_preview.setStyleSheet("border: 1px solid #ccc; border-radius: 3px;")
        color_layout.addWidget(self.new_color_preview)
        
        color_layout.addStretch()
        
        new_tag_form.addRow("Kolor:", color_layout)
        
        right_panel.addLayout(new_tag_form)
        
        self.add_tag_btn = QPushButton("➕ Dodaj tag")
        self.add_tag_btn.clicked.connect(self._add_tag)
        self.add_tag_btn.setMinimumHeight(35)
        colors = self.theme_manager.get_current_colors() if self.theme_manager else {}
        success_bg = colors.get('success_bg', '#4CAF50')
        success_hover = colors.get('success_hover', '#45a049')
        self.add_tag_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {success_bg};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {success_hover};
            }}
        """)
        right_panel.addWidget(self.add_tag_btn)
        
        right_panel.addSpacing(20)
        
        # Edycja istniejącego
        edit_tag_label = QLabel("Edytuj wybrany tag:")
        edit_tag_label.setStyleSheet("font-weight: bold;")
        right_panel.addWidget(edit_tag_label)
        
        self.edit_panel = QWidget()
        edit_layout = QFormLayout(self.edit_panel)
        
        self.edit_tag_input = QLineEdit()
        self.edit_tag_input.setEnabled(False)
        edit_layout.addRow("Nazwa:", self.edit_tag_input)
        
        # Edycja koloru
        edit_color_layout = QHBoxLayout()
        
        self.edit_color_btn = QPushButton("Zmień kolor")
        self.edit_color_btn.setMinimumHeight(35)
        self.edit_color_btn.setEnabled(False)
        self.edit_color_btn.clicked.connect(self._pick_edit_color)
        edit_color_layout.addWidget(self.edit_color_btn)
        
        self.edit_color_preview = QLabel()
        self.edit_color_preview.setFixedSize(35, 35)
        self.edit_color_preview.setStyleSheet("border: 1px solid #ccc; border-radius: 3px;")
        edit_color_layout.addWidget(self.edit_color_preview)
        
        edit_color_layout.addStretch()
        
        edit_layout.addRow("Kolor:", edit_color_layout)
        
        right_panel.addWidget(self.edit_panel)
        
        self.save_edit_btn = QPushButton("💾 Zapisz zmiany")
        self.save_edit_btn.setEnabled(False)
        self.save_edit_btn.clicked.connect(self._save_tag_edit)
        self.save_edit_btn.setMinimumHeight(35)
        colors = self.theme_manager.get_current_colors() if self.theme_manager else {}
        accent_bg = colors.get('accent_primary', '#2196F3')
        accent_hover = colors.get('accent_hover', '#0b7dda')
        disabled_bg = colors.get('disabled_bg', '#cccccc')
        self.save_edit_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {accent_bg};
                color: white;
                border: none;
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
            QPushButton:disabled {{
                background-color: {disabled_bg};
            }}
        """)
        right_panel.addWidget(self.save_edit_btn)
        
        right_panel.addStretch()
        
        main_layout.addLayout(right_panel)
        
        layout.addLayout(main_layout)
        
        # === SEPARATOR ===
        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(sep2)
        
        # === PRZYCISKI DIALOGU ===
        buttons_layout = QHBoxLayout()
        
        buttons_layout.addStretch()
        
        self.close_btn = QPushButton("Zamknij")
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setMinimumHeight(35)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
        # Ustaw domyślny kolor dla nowego tagu
        self.new_tag_color = "#3498db"  # Niebieski
        self._update_color_preview(self.new_color_preview, self.new_tag_color)
        
        # Załaduj tagi do listy
        self._populate_tags_list()
    
    def _load_tags(self):
        """Załaduj tagi z bazy danych"""
        # TODO: Zaimplementuj metodę get_all_tags w CallCryptorDatabase
        # Na razie używamy pustego słownika
        self.current_tags = {}
        
        # Przykładowe tagi (usuń to gdy będzie DB)
        self.current_tags = {
            "Ważne": "#e74c3c",
            "Praca": "#3498db",
            "Osobiste": "#2ecc71",
            "Do przesłuchania": "#f39c12"
        }
    
    def _populate_tags_list(self):
        """Wypełnij listę tagów"""
        self.tags_list.clear()
        
        for tag_name, color in sorted(self.current_tags.items()):
            item = QListWidgetItem()
            item.setText(tag_name)
            item.setData(Qt.ItemDataRole.UserRole, color)
            
            # Stwórz kolorową ikonę
            icon = self._create_color_icon(color)
            item.setIcon(icon)
            
            self.tags_list.addItem(item)
    
    def _create_color_icon(self, color: str) -> QIcon:
        """Stwórz ikonę z kolorowym kwadratem"""
        pixmap = QPixmap(16, 16)
        pixmap.fill(QColor(color))
        
        # Dodaj obramowanie
        painter = QPainter(pixmap)
        painter.setPen(QColor("#666"))
        painter.drawRect(0, 0, 15, 15)
        painter.end()
        
        return QIcon(pixmap)
    
    def _update_color_preview(self, preview_label: QLabel, color: str):
        """Zaktualizuj podgląd koloru"""
        preview_label.setStyleSheet(f"""
            background-color: {color};
            border: 1px solid #999;
            border-radius: 3px;
        """)
    
    def _on_tag_selected(self, current, previous):
        """Obsługa wyboru tagu z listy"""
        if current:
            tag_name = current.text()
            color = current.data(Qt.ItemDataRole.UserRole)
            
            # Włącz edycję
            self.edit_tag_input.setEnabled(True)
            self.edit_tag_input.setText(tag_name)
            
            self.edit_color_btn.setEnabled(True)
            self.edit_tag_color = color
            self._update_color_preview(self.edit_color_preview, color)
            
            self.save_edit_btn.setEnabled(True)
            self.delete_btn.setEnabled(True)
        else:
            # Wyłącz edycję
            self.edit_tag_input.setEnabled(False)
            self.edit_tag_input.clear()
            
            self.edit_color_btn.setEnabled(False)
            self.save_edit_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
    
    def _pick_new_color(self):
        """Wybierz kolor dla nowego tagu"""
        color = QColorDialog.getColor(QColor(self.new_tag_color), self, "Wybierz kolor tagu")
        
        if color.isValid():
            self.new_tag_color = color.name()
            self._update_color_preview(self.new_color_preview, self.new_tag_color)
    
    def _pick_edit_color(self):
        """Wybierz kolor dla edytowanego tagu"""
        color = QColorDialog.getColor(QColor(self.edit_tag_color), self, "Wybierz kolor tagu")
        
        if color.isValid():
            self.edit_tag_color = color.name()
            self._update_color_preview(self.edit_color_preview, self.edit_tag_color)
    
    def _add_tag(self):
        """Dodaj nowy tag"""
        tag_name = self.new_tag_input.text().strip()
        
        if not tag_name:
            QMessageBox.warning(self, "Błąd", "Wprowadź nazwę tagu")
            return
        
        if tag_name in self.current_tags:
            QMessageBox.warning(self, "Błąd", f"Tag '{tag_name}' już istnieje")
            return
        
        # Dodaj tag
        self.current_tags[tag_name] = self.new_tag_color
        
        # TODO: Zapisz do bazy danych
        # self.db_manager.add_tag(tag_name, self.new_tag_color, self.user_id)
        
        # Odśwież listę
        self._populate_tags_list()
        
        # Wyczyść input
        self.new_tag_input.clear()
        
        # Reset koloru na niebieski
        self.new_tag_color = "#3498db"
        self._update_color_preview(self.new_color_preview, self.new_tag_color)
        
        # Emituj sygnał zmiany
        self.tags_changed.emit()
        
        logger.info(f"[TagManager] Added tag: {tag_name} ({self.new_tag_color})")
    
    def _save_tag_edit(self):
        """Zapisz edycję tagu"""
        current_item = self.tags_list.currentItem()
        if not current_item:
            return
        
        old_name = current_item.text()
        new_name = self.edit_tag_input.text().strip()
        
        if not new_name:
            QMessageBox.warning(self, "Błąd", "Nazwa tagu nie może być pusta")
            return
        
        # Jeśli nazwa się zmieniła, sprawdź czy nie istnieje
        if new_name != old_name and new_name in self.current_tags:
            QMessageBox.warning(self, "Błąd", f"Tag '{new_name}' już istnieje")
            return
        
        # Usuń stary wpis (jeśli nazwa się zmieniła)
        if new_name != old_name:
            del self.current_tags[old_name]
        
        # Zapisz nowy/zaktualizowany
        self.current_tags[new_name] = self.edit_tag_color
        
        # TODO: Zaktualizuj w bazie danych
        # self.db_manager.update_tag(old_name, new_name, self.edit_tag_color, self.user_id)
        
        # Odśwież listę
        self._populate_tags_list()
        
        # Emituj sygnał zmiany
        self.tags_changed.emit()
        
        logger.info(f"[TagManager] Updated tag: {old_name} -> {new_name} ({self.edit_tag_color})")
    
    def _delete_tag(self):
        """Usuń wybrany tag"""
        current_item = self.tags_list.currentItem()
        if not current_item:
            return
        
        tag_name = current_item.text()
        
        # Potwierdzenie
        reply = QMessageBox.question(
            self,
            "Usuń tag",
            f"Czy na pewno chcesz usunąć tag '{tag_name}'?\n\n"
            "Tag zostanie usunięty ze wszystkich nagrań.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Usuń z lokalnego słownika
            del self.current_tags[tag_name]
            
            # TODO: Usuń z bazy danych
            # self.db_manager.delete_tag(tag_name, self.user_id)
            
            # Odśwież listę
            self._populate_tags_list()
            
            # Emituj sygnał zmiany
            self.tags_changed.emit()
            
            logger.info(f"[TagManager] Deleted tag: {tag_name}")
    
    def get_tags(self) -> Dict[str, str]:
        """Pobierz wszystkie tagi {nazwa: kolor}"""
        return self.current_tags.copy()
