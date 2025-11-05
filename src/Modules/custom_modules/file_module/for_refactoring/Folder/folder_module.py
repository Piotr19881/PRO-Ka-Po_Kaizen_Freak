"""
Moduł Folder - Zarządzanie plikami z możliwością dodawania komentarzy i tagów

Funkcjonalność:
- Tworzenie wielu folderów do organizacji plików
- Dodawanie skrótów do plików, folderów i skrótów (.lnk)
- System tagów z kolorami
- Dwa tryby wyświetlania: lista i ikony
- Menu kontekstowe z różnymi opcjami
- Automatyczne zapisywanie ikon
- Dwukrotne kliknięcie do otwierania plików

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-02
"""

import sys
import json
import os
import shutil
import subprocess
import ctypes
import requests
from datetime import datetime
from pathlib import Path
from ctypes import wintypes

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QComboBox, QPushButton, QTableWidget, QTableWidgetItem, QFileDialog,
    QDialog, QLabel, QLineEdit, QTextEdit, QDialogButtonBox, QMessageBox,
    QListWidget, QListWidgetItem, QStackedWidget, QGridLayout, QFrame,
    QFileIconProvider, QButtonGroup, QRadioButton, QMenu, QHeaderView,
    QDateEdit, QGroupBox
)
from PyQt6.QtCore import Qt, QSize, QFileInfo, QUrl, QDate
from PyQt6.QtGui import QIcon, QPixmap, QColor, QAction, QDesktopServices

from tagi_folderow_dialog import TagiFolderowDialog


class AddItemDialog(QDialog):
    """Dialog do wyboru typu elementu do dodania"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj element")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Opis
        desc_label = QLabel("Wybierz typ elementu do dodania:")
        layout.addWidget(desc_label)
        
        # Radio buttons
        self.file_radio = QRadioButton("Plik")
        self.folder_radio = QRadioButton("Folder")
        self.shortcut_radio = QRadioButton("Skrót (.lnk)")
        
        self.file_radio.setChecked(True)
        
        layout.addWidget(self.file_radio)
        layout.addWidget(self.folder_radio)
        layout.addWidget(self.shortcut_radio)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(buttons)
        self.setLayout(layout)
    
    def get_selection(self):
        """Zwraca wybrany typ"""
        if self.file_radio.isChecked():
            return "file"
        elif self.folder_radio.isChecked():
            return "folder"
        else:
            return "shortcut"


class FileCommentDialog(QDialog):
    """Dialog do dodawania/edycji komentarza i tagu"""
    
    def __init__(self, parent=None, current_tag="", current_comment=""):
        super().__init__(parent)
        self.setWindowTitle("Dodaj komentarz i tag")
        self.setMinimumWidth(400)
        
        layout = QVBoxLayout()
        
        # Tag
        tag_label = QLabel("Tag:")
        self.tag_input = QLineEdit()
        self.tag_input.setText(current_tag)
        self.tag_input.setPlaceholderText("np. Projekt, Dokumenty, Zdjęcia...")
        
        # Komentarz
        comment_label = QLabel("Komentarz:")
        self.comment_input = QTextEdit()
        self.comment_input.setPlainText(current_comment)
        self.comment_input.setPlaceholderText("Dodaj swój komentarz...")
        self.comment_input.setMaximumHeight(100)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        
        layout.addWidget(tag_label)
        layout.addWidget(self.tag_input)
        layout.addWidget(comment_label)
        layout.addWidget(self.comment_input)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_data(self):
        """Zwraca wprowadzone dane"""
        return {
            'tag': self.tag_input.text().strip(),
            'comment': self.comment_input.toPlainText().strip()
        }


class ShareFileDialog(QDialog):
    """Dialog do udostępniania pliku przez email"""
    
    def __init__(self, file_name, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Udostępnij plik")
        self.setMinimumWidth(450)
        
        layout = QVBoxLayout()
        
        # Info o pliku
        info_label = QLabel(f"Udostępniasz plik: <b>{file_name}</b>")
        layout.addWidget(info_label)
        
        layout.addSpacing(10)
        
        # Email odbiorcy
        email_label = QLabel("Email odbiorcy:")
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("odbiorca@example.com")
        layout.addWidget(email_label)
        layout.addWidget(self.email_input)
        
        # Twoje imię/nazwa
        name_label = QLabel("Twoje imię/nazwa:")
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Jan Kowalski")
        layout.addWidget(name_label)
        layout.addWidget(self.name_input)
        
        # Język emaila
        lang_label = QLabel("Język emaila:")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["Polski (pl)", "English (en)", "Deutsch (de)"])
        layout.addWidget(lang_label)
        layout.addWidget(self.lang_combo)
        
        layout.addSpacing(10)
        
        # URL API
        api_label = QLabel("URL API:")
        self.api_input = QLineEdit()
        self.api_input.setText("http://localhost:9000")
        self.api_input.setPlaceholderText("http://localhost:9000 lub https://your-api.onrender.com")
        layout.addWidget(api_label)
        layout.addWidget(self.api_input)
        
        layout.addSpacing(10)
        
        # Info
        info_text = QLabel(
            "<small>Plik zostanie przesłany do chmury Backblaze B2, "
            "a odbiorca otrzyma email z linkiem do pobrania.</small>"
        )
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #666;")
        layout.addWidget(info_text)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setLayout(layout)
    
    def get_data(self):
        """Zwraca wprowadzone dane"""
        lang_map = {
            0: "pl",
            1: "en",
            2: "de"
        }
        
        return {
            'recipient_email': self.email_input.text().strip(),
            'sender_name': self.name_input.text().strip(),
            'language': lang_map.get(self.lang_combo.currentIndex(), "pl"),
            'api_url': self.api_input.text().strip()
        }


class FileItem(QFrame):
    """Widget reprezentujący pojedynczy plik w widoku ikon"""
    
    def __init__(self, file_data, icons_dir, tag_color=None, parent=None, main_window=None):
        super().__init__(parent)
        self.file_data = file_data
        self.icons_dir = icons_dir
        self.tag_color = tag_color
        self.main_window = main_window  # Referencja do głównego okna
        self.is_selected = False  # Stan zaznaczenia
        
        # Ustaw ramkę w kolorze tagu jeśli istnieje
        if tag_color:
            self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            self.setLineWidth(3)
            self.setStyleSheet(f"border: 3px solid {tag_color}; border-radius: 5px;")
        else:
            self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
            self.setLineWidth(1)
        
        self.setMaximumWidth(120)
        self.setMinimumHeight(160)
        
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Etykieta tagu na górze (jeśli istnieje)
        if file_data.get('tag') and tag_color:
            tag_label = QLabel(file_data['tag'])
            tag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            is_dark = self.is_dark_color(tag_color)
            tag_label.setStyleSheet(
                f"background-color: {tag_color}; "
                f"color: {'white' if is_dark else 'black'}; "
                f"font-weight: bold; padding: 2px; border-radius: 3px; font-size: 9pt;"
            )
            tag_label.setWordWrap(True)
            tag_label.setMaximumWidth(110)
            layout.addWidget(tag_label)
        
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Kontener na ikonę z gwiazdką
        icon_container = QWidget()
        icon_container.setFixedSize(82, 82)
        
        # Ikona pliku - wczytanie z zapisanej kopii lub z systemu
        icon_label = QLabel(icon_container)
        icon_path = file_data.get('icon_path', '')
        
        if icon_path and os.path.exists(icon_path):
            pixmap = QPixmap(icon_path)
            if not pixmap.isNull():
                pixmap = pixmap.scaled(
                    64,
                    64,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            else:
                pixmap = self._get_system_icon(file_data['path'])
        else:
            pixmap = self._get_system_icon(file_data['path'])
        
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon_label.setGeometry(9, 9, 64, 64)
        
        # Gwiazdka w lewym górnym rogu (jeśli plik jest ulubiony)
        self.star_label = None
        if file_data.get('pinned', False):
            self.star_label = QLabel("⭐", icon_container)
            self.star_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(255, 255, 255, 220);
                    border-radius: 14px;
                    padding: 4px;
                    font-size: 20pt;
                }
            """)
            self.star_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.star_label.setFixedSize(32, 32)
            self.star_label.move(2, 2)  # Lewy górny róg
        
        layout.addWidget(icon_container)
        
        # Nazwa pliku
        name_label = QLabel(file_data['name'])
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setMaximumWidth(110)
        
        layout.addWidget(name_label)
        
        self.setLayout(layout)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _get_system_icon(self, path):
        """Pobiera systemową ikonę dla pliku/folderu"""
        icon_provider = QFileIconProvider()
        file_info = QFileInfo(path)
        icon = icon_provider.icon(file_info)
        return icon.pixmap(QSize(64, 64))
    
    def is_dark_color(self, hex_color):
        """Sprawdza czy kolor jest ciemny"""
        color = QColor(hex_color)
        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        return brightness < 128
    
    def set_selected(self, selected):
        """Ustawia stan zaznaczenia"""
        self.is_selected = selected
        self.update_style()
    
    def update_style(self):
        """Aktualizuje styl w zależności od stanu zaznaczenia"""
        if self.is_selected:
            # Zaznaczony - niebieski border
            if self.tag_color:
                self.setStyleSheet(
                    f"border: 3px solid #0078d4; border-radius: 5px; background-color: #e6f2ff;"
                )
            else:
                self.setStyleSheet(
                    "border: 3px solid #0078d4; border-radius: 5px; background-color: #e6f2ff;"
                )
        else:
            # Niezaznaczony - normalny styl
            if self.tag_color:
                self.setStyleSheet(f"border: 3px solid {self.tag_color}; border-radius: 5px;")
            else:
                self.setStyleSheet("")
    
    def mousePressEvent(self, a0):
        """Obsługa kliknięcia"""
        if a0 and a0.button() == Qt.MouseButton.RightButton:
            # Menu kontekstowe
            if self.main_window:
                self.main_window.show_context_menu(self, a0.globalPosition().toPoint())
        elif a0 and a0.button() == Qt.MouseButton.LeftButton:
            # Obsługa zaznaczania
            if self.main_window:
                modifiers = QApplication.keyboardModifiers()
                self.main_window.handle_icon_selection(self, modifiers)
        super().mousePressEvent(a0)
    
    def mouseDoubleClickEvent(self, a0):
        """Obsługa dwukrotnego kliknięcia - otwiera plik"""
        if a0 and a0.button() == Qt.MouseButton.LeftButton:
            if self.main_window:
                self.main_window.open_file(self.file_data)
        super().mouseDoubleClickEvent(a0)


class FolderModule(QMainWindow):
    """Główny moduł Folder"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Moduł Folder")
        self.setMinimumSize(900, 600)
        
        # Dane
        self.folders = {}  # Słownik folderów: {nazwa: [pliki]}
        self.current_folder = None
        self.current_view = "icons"  # icons lub list
        self.selected_file = None
        self.tags_colors = {}  # GLOBALNY słownik tagów (dla kompatybilności wstecz)
        self.folder_tags = {}  # Słownik tagów per folder: {nazwa_folderu: {nazwa_tagu: kolor}}
        self.selected_icon_items = []  # Lista zaznaczonych FileItem w widoku ikon
        self.folder_view_preferences = {}  # Słownik preferencji widoku: {nazwa_folderu: "icons" lub "list"}
        self.file_access_history = []  # Historia otwarć plików: [(file_path, timestamp)]
        self.quick_panel_visible = False  # Stan panelu bocznego
        self.display_row_mapping = []  # Mapowanie wierszy tabeli -> indeksy w danych
        
        # Filtry
        self.filter_text = ""
        self.filter_tag = ""
        self.filter_date_from = None
        self.filter_date_to = None
        
        # Katalog na ikony
        self.icons_dir = os.path.join(os.path.dirname(__file__), "icons_cache")
        os.makedirs(self.icons_dir, exist_ok=True)
        
        # Ładowanie danych
        self.load_data()
        
        # UI
        self.init_ui()
        
        # Jeśli są foldery, wybierz pierwszy
        if self.folders:
            first_folder = list(self.folders.keys())[0]
            self.folder_combo.setCurrentText(first_folder)
            self.current_folder = first_folder
            self.refresh_view()
    
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Pasek nawigacyjny
        nav_bar = self.create_navigation_bar()
        main_layout.addLayout(nav_bar)
        
        # Pasek filtrów
        filter_bar = self.create_filter_bar()
        main_layout.addLayout(filter_bar)
        
        # Główny kontener z panelem bocznym i widokiem głównym
        content_layout = QHBoxLayout()
        
        # Panel boczny "Szybkie akcje" (początkowo ukryty)
        self.quick_panel = self.create_quick_actions_panel()
        self.quick_panel.setMaximumWidth(350)
        self.quick_panel.hide()
        content_layout.addWidget(self.quick_panel)
        
        # Sekcja główna - StackedWidget dla dwóch widoków
        self.stacked_widget = QStackedWidget()
        
        # Widok tabeli
        self.table_view = QTableWidget()
        self.table_view.setColumnCount(7)  # Dodano kolumnę Ulubione
        self.table_view.setHorizontalHeaderLabels([
            "⭐", "Nazwa", "Tag", "Komentarz", "Data utworzenia", 
            "Data modyfikacji", "Ścieżka"
        ])
        self.table_view.setSelectionBehavior(
            QTableWidget.SelectionBehavior.SelectRows
        )
        self.table_view.setSelectionMode(
            QTableWidget.SelectionMode.ExtendedSelection
        )
        self.table_view.itemSelectionChanged.connect(self.on_table_selection_changed)
        self.table_view.cellChanged.connect(self.on_cell_changed)
        self.table_view.cellDoubleClicked.connect(self.on_cell_double_clicked)
        self.table_view.cellClicked.connect(self.on_cell_clicked)
        self.table_view.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.table_view.customContextMenuRequested.connect(self.show_table_context_menu)
        
        # Automatyczne rozciąganie kolumn z możliwością manualnej zmiany
        header = self.table_view.horizontalHeader()
        header.setStretchLastSection(True)  # Ostatnia kolumna (Ścieżka) rozciąga się
        
        # Wszystkie kolumny można zmieniać ręcznie
        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
        
        # Opcjonalnie: ustaw minimalne szerokości kolumn dla lepszej czytelności
        self.table_view.setColumnWidth(0, 40)   # Ulubione (ikona)
        self.table_view.setColumnWidth(1, 150)  # Nazwa
        self.table_view.setColumnWidth(2, 120)  # Tag
        self.table_view.setColumnWidth(3, 200)  # Komentarz
        self.table_view.setColumnWidth(4, 150)  # Data utworzenia
        self.table_view.setColumnWidth(5, 150)  # Data modyfikacji
        # Kolumna 6 (Ścieżka) rozciąga się automatycznie
        
        # Widok ikon
        self.icon_view_widget = QWidget()
        self.icon_view_layout = QGridLayout()
        self.icon_view_widget.setLayout(self.icon_view_layout)
        
        # Scrollable area wrapper
        from PyQt6.QtWidgets import QScrollArea
        scroll_area = QScrollArea()
        scroll_area.setWidget(self.icon_view_widget)
        scroll_area.setWidgetResizable(True)
        
        self.stacked_widget.addWidget(self.table_view)
        self.stacked_widget.addWidget(scroll_area)
        
        content_layout.addWidget(self.stacked_widget)
        main_layout.addLayout(content_layout)
    
    def create_navigation_bar(self):
        """Tworzy pasek nawigacyjny"""
        nav_layout = QHBoxLayout()
        
        # ComboBox z folderami
        self.folder_combo = QComboBox()
        self.folder_combo.setMinimumWidth(200)
        self.folder_combo.addItem("-- Wybierz folder --")
        self.folder_combo.addItems(list(self.folders.keys()))
        self.folder_combo.currentTextChanged.connect(self.on_folder_changed)
        
        # Przycisk nowy folder
        btn_new_folder = QPushButton("Nowy folder")
        btn_new_folder.clicked.connect(self.create_new_folder)
        
        # Przycisk przełączania widoku (lista/ikony)
        self.btn_toggle_view = QPushButton("🖼️ Widok ikon")
        self.btn_toggle_view.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;"
        )
        self.btn_toggle_view.setToolTip("Przełącz między widokiem listy a ikon")
        self.btn_toggle_view.clicked.connect(self.toggle_view)
        
        # Przycisk dodaj plik
        btn_add_file = QPushButton("Dodaj nowy")
        btn_add_file.clicked.connect(self.add_new_file)
        
        # Przycisk usuń plik
        btn_remove_file = QPushButton("Usuń")
        btn_remove_file.clicked.connect(self.remove_file)
        
        # Przycisk komentarz
        btn_comment = QPushButton("Komentarz")
        btn_comment.clicked.connect(self.add_comment)
        
        # Przycisk edytuj tagi
        btn_edit_tags = QPushButton("Edytuj tagi")
        btn_edit_tags.clicked.connect(self.edit_tags)
        
        # Przycisk udostępnij
        btn_share = QPushButton("Udostępnij")
        btn_share.clicked.connect(self.share_selected_files)
        
        # Przycisk panel szybkich akcji
        self.btn_toggle_quick_panel = QPushButton("◀")
        self.btn_toggle_quick_panel.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; padding: 5px;"
        )
        self.btn_toggle_quick_panel.clicked.connect(self.toggle_quick_panel)
        
        # Dodanie do layoutu
        nav_layout.addWidget(self.btn_toggle_quick_panel)
        nav_layout.addWidget(QLabel("Folder:"))
        nav_layout.addWidget(self.folder_combo)
        nav_layout.addWidget(btn_new_folder)
        nav_layout.addStretch()
        nav_layout.addWidget(self.btn_toggle_view)
        nav_layout.addWidget(btn_add_file)
        nav_layout.addWidget(btn_remove_file)
        nav_layout.addWidget(btn_comment)
        nav_layout.addWidget(btn_edit_tags)
        nav_layout.addWidget(btn_share)
        
        return nav_layout
    
    def create_filter_bar(self):
        """Tworzy pasek filtrów"""
        filter_layout = QHBoxLayout()
        
        # Pole wyszukiwania tekstowego
        filter_layout.addWidget(QLabel("Szukaj:"))
        self.filter_text_input = QLineEdit()
        self.filter_text_input.setPlaceholderText("Wpisz frazę do wyszukania...")
        self.filter_text_input.setMinimumWidth(200)
        self.filter_text_input.textChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_text_input)
        
        filter_layout.addSpacing(20)
        
        # Filtr tagu
        filter_layout.addWidget(QLabel("Tag:"))
        self.filter_tag_combo = QComboBox()
        self.filter_tag_combo.setMinimumWidth(150)
        self.filter_tag_combo.addItem("-- Wszystkie --")
        # Tagi będą dodane po wybraniu folderu
        self.filter_tag_combo.currentTextChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_tag_combo)
        
        filter_layout.addSpacing(20)
        
        # Filtr dat
        filter_layout.addWidget(QLabel("Data od:"))
        self.filter_date_from_input = QDateEdit()
        self.filter_date_from_input.setCalendarPopup(True)
        self.filter_date_from_input.setDisplayFormat("yyyy-MM-dd")
        self.filter_date_from_input.setSpecialValueText("--")
        self.filter_date_from_input.setDate(QDate(2000, 1, 1))
        self.filter_date_from_input.clearMinimumDate()
        self.filter_date_from_input.dateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_date_from_input)
        
        filter_layout.addWidget(QLabel("do:"))
        self.filter_date_to_input = QDateEdit()
        self.filter_date_to_input.setCalendarPopup(True)
        self.filter_date_to_input.setDisplayFormat("yyyy-MM-dd")
        self.filter_date_to_input.setSpecialValueText("--")
        self.filter_date_to_input.setDate(QDate.currentDate())
        self.filter_date_to_input.dateChanged.connect(self.on_filter_changed)
        filter_layout.addWidget(self.filter_date_to_input)
        
        filter_layout.addSpacing(20)
        
        # Przycisk wyczyść filtry
        btn_clear_filters = QPushButton("Wyczyść filtry")
        btn_clear_filters.clicked.connect(self.clear_filters)
        filter_layout.addWidget(btn_clear_filters)
        
        filter_layout.addStretch()
        
        return filter_layout
    
    def on_filter_changed(self):
        """Obsługa zmiany filtrów"""
        # Aktualizuj wartości filtrów
        self.filter_text = self.filter_text_input.text().strip().lower()
        
        selected_tag = self.filter_tag_combo.currentText()
        self.filter_tag = "" if selected_tag == "-- Wszystkie --" else selected_tag
        
        # Daty
        date_from_text = self.filter_date_from_input.text()
        date_to_text = self.filter_date_to_input.text()
        
        if date_from_text and date_from_text != "--":
            self.filter_date_from = self.filter_date_from_input.date().toPyDate()
        else:
            self.filter_date_from = None
        
        if date_to_text and date_to_text != "--":
            self.filter_date_to = self.filter_date_to_input.date().toPyDate()
        else:
            self.filter_date_to = None
        
        # Odśwież widok
        self.refresh_view()
    
    def clear_filters(self):
        """Czyści wszystkie filtry"""
        self.filter_text_input.clear()
        self.filter_tag_combo.setCurrentIndex(0)
        self.filter_date_from_input.setDate(QDate(2000, 1, 1))
        self.filter_date_to_input.setDate(QDate.currentDate())
    
    def create_new_folder(self):
        """Tworzy nowy folder"""
        from PyQt6.QtWidgets import QInputDialog
        
        folder_name, ok = QInputDialog.getText(
            self, 
            "Nowy folder", 
            "Podaj nazwę nowego folderu:"
        )
        
        if ok and folder_name:
            if folder_name in self.folders:
                QMessageBox.warning(
                    self, 
                    "Błąd", 
                    "Folder o tej nazwie już istnieje!"
                )
                return
            
            self.folders[folder_name] = []
            self.folder_combo.addItem(folder_name)
            self.folder_combo.setCurrentText(folder_name)
            
            # Ustaw domyślną preferencję widoku dla nowego folderu (ikony)
            self.folder_view_preferences[folder_name] = "icons"
            
            # Utwórz pustą listę tagów dla nowego folderu
            self.folder_tags[folder_name] = {}
            
            self.save_data()
    
    def get_current_tags(self):
        """Zwraca tagi dla aktualnego folderu"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            return {}
        
        # Jeśli folder nie ma jeszcze tagów, utwórz pusty słownik
        if self.current_folder not in self.folder_tags:
            self.folder_tags[self.current_folder] = {}
        
        return self.folder_tags[self.current_folder]
    
    def on_folder_changed(self, folder_name):
        """Obsługa zmiany folderu"""
        if folder_name and folder_name != "-- Wybierz folder --":
            self.current_folder = folder_name
            
            # Zaktualizuj listę tagów dla tego folderu
            self.update_filter_tags_list()
            
            # Przywróć preferowany widok dla tego folderu
            preferred_view = self.folder_view_preferences.get(folder_name, "icons")
            if preferred_view == "list":
                self.current_view = "list"
                self.stacked_widget.setCurrentIndex(0)
            else:
                self.current_view = "icons"
                self.stacked_widget.setCurrentIndex(1)
            
            # Zaktualizuj przycisk widoku
            self.update_view_button()
            
            self.refresh_view()
    
    def toggle_view(self):
        """Przełącza między widokiem listy a ikon"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            QMessageBox.warning(
                self, 
                "Błąd", 
                "Najpierw wybierz lub utwórz folder!"
            )
            return
        
        # Przełącz widok
        if self.current_view == "list":
            self.show_icon_view()
        else:
            self.show_list_view()
        
        # Zaktualizuj tekst i kolor przycisku
        self.update_view_button()
    
    def update_view_button(self):
        """Aktualizuje tekst i kolor przycisku przełączania widoku"""
        if self.current_view == "list":
            self.btn_toggle_view.setText("🖼️ Widok ikon")
            self.btn_toggle_view.setStyleSheet(
                "background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;"
            )
        else:
            self.btn_toggle_view.setText("📋 Widok listy")
            self.btn_toggle_view.setStyleSheet(
                "background-color: #2196F3; color: white; font-weight: bold; padding: 5px;"
            )
    
    def show_list_view(self):
        """Przełącza na widok listy"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            QMessageBox.warning(
                self, 
                "Błąd", 
                "Najpierw wybierz lub utwórz folder!"
            )
            return
        
        self.current_view = "list"
        self.stacked_widget.setCurrentIndex(0)
        
        # Zapisz preferencję widoku dla aktualnego folderu
        if self.current_folder and self.current_folder != "-- Wybierz folder --":
            self.folder_view_preferences[self.current_folder] = "list"
            self.save_data()
        
        # Zaktualizuj przycisk
        self.update_view_button()
        
        self.refresh_view()
    
    def show_icon_view(self):
        """Przełącza na widok ikon"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            QMessageBox.warning(
                self, 
                "Błąd", 
                "Najpierw wybierz lub utwórz folder!"
            )
            return
        
        self.current_view = "icons"
        self.stacked_widget.setCurrentIndex(1)
        
        # Zapisz preferencję widoku dla aktualnego folderu
        if self.current_folder and self.current_folder != "-- Wybierz folder --":
            self.folder_view_preferences[self.current_folder] = "icons"
            self.save_data()
        
        # Zaktualizuj przycisk
        self.update_view_button()
        
        self.refresh_view()
    
    def refresh_view(self):
        """Odświeża aktualny widok"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            return
        
        # Wyczyść zaznaczenie ikon
        for item in self.selected_icon_items:
            item.set_selected(False)
        self.selected_icon_items.clear()
        
        files = self.folders.get(self.current_folder, [])
        
        # Filtruj pliki
        filtered_files = self.apply_filters(files)
        
        if self.current_view == "list":
            self.refresh_table_view(filtered_files)
        else:
            self.display_row_mapping = []
            self.refresh_icon_view(filtered_files)
    
    def apply_filters(self, files):
        """Filtruje pliki według ustawionych filtrów"""
        filtered = []
        
        for file_data in files:
            # Filtr tekstowy (nazwa lub komentarz lub ścieżka)
            if self.filter_text:
                name_match = self.filter_text in file_data['name'].lower()
                comment_match = self.filter_text in file_data.get('comment', '').lower()
                path_match = self.filter_text in file_data['path'].lower()
                
                if not (name_match or comment_match or path_match):
                    continue
            
            # Filtr tagu
            if self.filter_tag:
                if file_data.get('tag', '') != self.filter_tag:
                    continue
            
            # Filtr dat
            if self.filter_date_from or self.filter_date_to:
                # Użyj daty modyfikacji z file_data lub z pliku
                date_str = file_data.get('modified', '')
                if date_str:
                    try:
                        # Format: "YYYY-MM-DD HH:MM:SS"
                        file_date = datetime.strptime(date_str.split()[0], "%Y-%m-%d").date()
                        
                        if self.filter_date_from and file_date < self.filter_date_from:
                            continue
                        
                        if self.filter_date_to and file_date > self.filter_date_to:
                            continue
                    except:
                        # Jeśli nie można sparsować daty, pomiń filtr dat dla tego pliku
                        pass
            
            # Plik przeszedł wszystkie filtry
            filtered.append(file_data)
        
        return filtered
    
    def refresh_table_view(self, files):
        """Odświeża widok tabeli"""
        # Tymczasowo odłącz sygnał cellChanged
        self.table_view.cellChanged.disconnect(self.on_cell_changed)
        
        self.table_view.setRowCount(0)
        
        # Przygotuj mapowanie indeksów oryginalnych plików
        all_files = self.folders.get(self.current_folder, []) if self.current_folder else []
        index_map = {id(f): idx for idx, f in enumerate(all_files)}
        self.display_row_mapping = []
        
        # Sortuj pliki - ulubione na górze
        sorted_files = sorted(files, key=lambda f: (not f.get('pinned', False), f['name'].lower()))
        
        for file_data in sorted_files:
            row = self.table_view.rowCount()
            self.table_view.insertRow(row)
            
            original_index = index_map.get(id(file_data), -1)
            self.display_row_mapping.append(original_index)
            
            # Kolumna 0: Gwiazdka (ulubione)
            star_char = "★" if file_data.get('pinned', False) else "☆"
            star_item = QTableWidgetItem(star_char)
            star_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            star_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            star_item.setToolTip("Kliknij, aby dodać/usuń z ulubionych")
            star_item.setData(Qt.ItemDataRole.UserRole, original_index)
            self.table_view.setItem(row, 0, star_item)
            
            # Kolumna 1: Nazwa
            self.table_view.setItem(row, 1, QTableWidgetItem(file_data['name']))
            
            # Kolumna 2: Tag - ComboBox z listą tagów
            tag_combo = QComboBox()
            tag_combo.addItem("")  # Pusta opcja
            
            # Pobierz tagi dla aktualnego folderu
            current_folder_tags = self.get_current_tags()
            tag_combo.addItems(sorted(current_folder_tags.keys()))
            
            current_tag = file_data.get('tag', '')
            if current_tag:
                index = tag_combo.findText(current_tag)
                if index >= 0:
                    tag_combo.setCurrentIndex(index)
                    # Ustaw kolor tła
                    color = current_folder_tags.get(current_tag, '#FFFFFF')
                    tag_combo.setStyleSheet(
                        f"background-color: {color}; "
                        f"color: {'white' if self._is_dark_color(color) else 'black'}; "
                        f"font-weight: bold;"
                    )
            
            tag_combo.currentTextChanged.connect(lambda text, r=row: self.on_tag_changed(r, text))
            self.table_view.setCellWidget(row, 2, tag_combo)
            
            # Komentarz, daty, ścieżka
            self.table_view.setItem(row, 3, QTableWidgetItem(file_data.get('comment', '')))
            self.table_view.setItem(row, 4, QTableWidgetItem(file_data.get('created', '')))
            self.table_view.setItem(row, 5, QTableWidgetItem(file_data.get('modified', '')))
            self.table_view.setItem(row, 6, QTableWidgetItem(file_data['path']))
        
        # Nie zmieniamy szerokości kolumn - są ustawione automatycznie w init_ui
        
        # Podłącz ponownie sygnał
        self.table_view.cellChanged.connect(self.on_cell_changed)
    
    def get_file_data_from_row(self, row):
        """Zwraca krotkę (file_data, original_index) dla wiersza tabeli"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            return None, None
        if row < 0 or row >= len(self.display_row_mapping):
            return None, None
        original_index = self.display_row_mapping[row]
        if original_index is None or original_index < 0:
            return None, None
        files = self.folders.get(self.current_folder, [])
        if original_index >= len(files):
            return None, None
        return files[original_index], original_index

    def on_tag_changed(self, row, new_tag):
        """Obsługa zmiany tagu w tabeli"""
        file_data, _ = self.get_file_data_from_row(row)
        if not file_data:
            return
        
        file_data['tag'] = new_tag
        
        combo = self.table_view.cellWidget(row, 2)
        current_folder_tags = self.get_current_tags()
        
        if combo and new_tag and new_tag in current_folder_tags:
            color = current_folder_tags[new_tag]
            combo.setStyleSheet(
                f"background-color: {color}; "
                f"color: {'white' if self._is_dark_color(color) else 'black'}; "
                f"font-weight: bold;"
            )
        elif combo:
            combo.setStyleSheet("")
        
        self.save_data()
        if self.current_view == "icons":
            self.refresh_view()
    
    def on_cell_changed(self, row, column):
        """Obsługa zmiany komórki w tabeli"""
        if column != 3:
            return
        
        file_data, _ = self.get_file_data_from_row(row)
        if not file_data:
            return
        
        item = self.table_view.item(row, column)
        if not item:
            return
        
        file_data['comment'] = item.text()
        self.save_data()
    
    def _is_dark_color(self, hex_color):
        """Sprawdza czy kolor jest ciemny"""
        color = QColor(hex_color)
        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        return brightness < 128

    def on_cell_clicked(self, row, column):
        """Obsługa kliknięcia komórki tabeli"""
        if column != 0:
            return
        
        file_data, _ = self.get_file_data_from_row(row)
        if not file_data:
            return
        
        new_state = not file_data.get('pinned', False)
        file_data['pinned'] = new_state
        self.save_data()
        self.refresh_view()
        if self.quick_panel_visible:
            self.refresh_quick_panel()
    
    def create_quick_actions_panel(self):
        """Tworzy panel szybkich akcji"""
        panel = QGroupBox("Szybkie akcje")
        panel.setMaximumWidth(300)
        panel.setStyleSheet("""
            QGroupBox {
            background-color: #f5f5f5;
            border: 1px solid #ccc;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
            }
            QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 5 5px;
            color: #000000;
            }
        """)
        
        layout = QVBoxLayout()
        panel.setLayout(layout)
        
        # Przyciski do zmiany trybu
        btn_favorites = QPushButton("⭐ Ulubione")
        btn_favorites.clicked.connect(lambda: self.show_quick_mode('favorites'))
        
        btn_recent_folder = QPushButton("📁 Ostatnio dodane (folder)")
        btn_recent_folder.clicked.connect(lambda: self.show_quick_mode('recent_folder'))
        
        btn_recent_system = QPushButton("💻 Ostatnio dodane (system)")
        btn_recent_system.clicked.connect(lambda: self.show_quick_mode('recent_system'))
        
        btn_recent_opened = QPushButton("📂 Ostatnio otwierane")
        btn_recent_opened.clicked.connect(lambda: self.show_quick_mode('recent_opened'))
        
        # Dodaj przyciski do layoutu
        layout.addWidget(btn_favorites)
        layout.addWidget(btn_recent_folder)
        layout.addWidget(btn_recent_system)
        layout.addWidget(btn_recent_opened)
        
        # Tabela z wynikami
        self.quick_panel_table = QTableWidget()
        self.quick_panel_table.setColumnCount(2)
        self.quick_panel_table.setHorizontalHeaderLabels(["Nazwa", "Data"])
        self.quick_panel_table.horizontalHeader().setStretchLastSection(True)
        self.quick_panel_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.quick_panel_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.quick_panel_table.doubleClicked.connect(self.on_quick_panel_double_click)
        self.quick_panel_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.quick_panel_table.customContextMenuRequested.connect(self.show_quick_panel_context_menu)
        layout.addWidget(self.quick_panel_table)
        
        # Rozpocznij od widoku ulubionych
        self.current_quick_mode = 'favorites'
        
        return panel
    
    def toggle_quick_panel(self):
        """Przełącza widoczność panelu szybkich akcji"""
        self.quick_panel_visible = not self.quick_panel_visible
        
        if self.quick_panel_visible:
            self.quick_panel.show()
            self.btn_toggle_quick_panel.setText("▶ Szybkie akcje")
            self.refresh_quick_panel()
        else:
            self.quick_panel.hide()
            self.btn_toggle_quick_panel.setText("◀")
    
    def show_quick_mode(self, mode):
        """Zmienia tryb wyświetlania panelu szybkich akcji"""
        self.current_quick_mode = mode
        self.refresh_quick_panel()
    
    def refresh_quick_panel(self):
        """Odświeża zawartość panelu szybkich akcji"""
        self.quick_panel_table.setRowCount(0)
        
        if self.current_quick_mode == 'favorites':
            self.show_favorites_in_panel()
        elif self.current_quick_mode == 'recent_folder':
            self.show_recent_folder_files()
        elif self.current_quick_mode == 'recent_system':
            self.show_recent_system_files()
        elif self.current_quick_mode == 'recent_opened':
            self.show_recent_opened_files()
    
    def show_favorites_in_panel(self):
        """Wyświetla ulubione pliki w panelu"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            return
        
        files = self.folders.get(self.current_folder, [])
        favorites = [f for f in files if f.get('pinned', False)]
        
        self.quick_panel_table.setRowCount(len(favorites))
        for i, file_data in enumerate(favorites):
            name_item = QTableWidgetItem(file_data['name'])
            date_item = QTableWidgetItem(file_data.get('added_date', ''))
            
            self.quick_panel_table.setItem(i, 0, name_item)
            self.quick_panel_table.setItem(i, 1, date_item)
    
    def show_recent_folder_files(self):
        """Wyświetla ostatnio dodane pliki z folderu"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            return
        
        files = self.folders.get(self.current_folder, [])
        # Sortuj według daty dodania (najnowsze pierwsze)
        sorted_files = sorted(files, key=lambda f: f.get('added_date', ''), reverse=True)
        recent_files = sorted_files[:10]  # Tylko 10 najnowszych
        
        self.quick_panel_table.setRowCount(len(recent_files))
        for i, file_data in enumerate(recent_files):
            name_item = QTableWidgetItem(file_data['name'])
            date_item = QTableWidgetItem(file_data.get('added_date', ''))
            
            self.quick_panel_table.setItem(i, 0, name_item)
            self.quick_panel_table.setItem(i, 1, date_item)
    
    def show_recent_system_files(self):
        """Wyświetla ostatnio używane pliki z systemu Windows"""
        recent_files = self.get_windows_recent_files()
        
        self.quick_panel_table.setRowCount(len(recent_files))
        for i, (path, date) in enumerate(recent_files):
            name = os.path.basename(path)
            name_item = QTableWidgetItem(name)
            date_item = QTableWidgetItem(date)
            
            self.quick_panel_table.setItem(i, 0, name_item)
            self.quick_panel_table.setItem(i, 1, date_item)
    
    def show_recent_opened_files(self):
        """Wyświetla ostatnio otwierane pliki z historii"""
        # Sortuj według daty (najnowsze pierwsze)
        sorted_history = sorted(self.file_access_history, key=lambda x: x[1], reverse=True)
        recent_opens = sorted_history[:10]  # Tylko 10 najnowszych
        
        self.quick_panel_table.setRowCount(len(recent_opens))
        for i, (path, timestamp) in enumerate(recent_opens):
            name = os.path.basename(path)
            date_str = timestamp.strftime("%Y-%m-%d %H:%M:%S")
            
            name_item = QTableWidgetItem(name)
            date_item = QTableWidgetItem(date_str)
            
            self.quick_panel_table.setItem(i, 0, name_item)
            self.quick_panel_table.setItem(i, 1, date_item)
    
    def get_windows_recent_files(self):
        """Pobiera listę ostatnio używanych plików z Windows"""
        recent_files = []
        recent_folder = os.path.join(os.environ['APPDATA'], 'Microsoft', 'Windows', 'Recent')
        
        try:
            if os.path.exists(recent_folder):
                # Pobierz pliki .lnk z folderu Recent
                files = []
                for file in os.listdir(recent_folder):
                    if file.endswith('.lnk'):
                        file_path = os.path.join(recent_folder, file)
                        try:
                            mtime = os.path.getmtime(file_path)
                            date_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
                            # Usuń rozszerzenie .lnk z nazwy
                            original_name = file[:-4]
                            files.append((original_name, date_str, mtime))
                        except:
                            continue
                
                # Sortuj według czasu modyfikacji (najnowsze pierwsze)
                files.sort(key=lambda x: x[2], reverse=True)
                
                # Zwróć tylko 10 najnowszych (bez timestamp)
                recent_files = [(name, date) for name, date, _ in files[:10]]
        except Exception as e:
            print(f"Błąd podczas odczytu ostatnich plików: {e}")
        
        return recent_files
    
    def on_quick_panel_double_click(self, index):
        """Obsługuje podwójne kliknięcie w panelu szybkich akcji"""
        row = index.row()
        
        if self.current_quick_mode == 'favorites':
            # Otwórz ulubiony plik
            if not self.current_folder or self.current_folder == "-- Wybierz folder --":
                return
            
            files = self.folders.get(self.current_folder, [])
            favorites = [f for f in files if f.get('pinned', False)]
            
            if row < len(favorites):
                file_data = favorites[row]
                self.open_file(file_data['path'])
        
        elif self.current_quick_mode == 'recent_folder':
            # Otwórz ostatnio dodany plik z folderu
            if not self.current_folder or self.current_folder == "-- Wybierz folder --":
                return
            
            files = self.folders.get(self.current_folder, [])
            sorted_files = sorted(files, key=lambda f: f.get('added_date', ''), reverse=True)
            recent_files = sorted_files[:10]
            
            if row < len(recent_files):
                file_data = recent_files[row]
                self.open_file(file_data['path'])
        
        elif self.current_quick_mode == 'recent_opened':
            # Otwórz ostatnio otwierany plik
            sorted_history = sorted(self.file_access_history, key=lambda x: x[1], reverse=True)
            recent_opens = sorted_history[:10]
            
            if row < len(recent_opens):
                path = recent_opens[row][0]
                self.open_file(path)
        
        # recent_system nie obsługujemy otwarcia, bo to tylko linki
    
    def show_quick_panel_context_menu(self, pos):
        """Wyświetla menu kontekstowe dla panelu szybkich akcji"""
        row = self.quick_panel_table.currentRow()
        if row < 0:
            return
        
        menu = QMenu(self)
        
        # Otwórz
        action_open = QAction("Otwórz", self)
        action_open.triggered.connect(lambda: self.on_quick_panel_double_click(self.quick_panel_table.currentIndex()))
        menu.addAction(action_open)
        
        # Opcje specyficzne dla trybu
        if self.current_quick_mode == 'favorites':
            # Usuń z ulubionych
            action_remove_fav = QAction("⭐ Usuń z ulubionych", self)
            action_remove_fav.triggered.connect(lambda: self.remove_favorite_from_quick_panel(row))
            menu.addAction(action_remove_fav)
            
            menu.addSeparator()
            
            # Kopiuj ścieżkę
            action_copy_path = QAction("Kopiuj ścieżkę", self)
            action_copy_path.triggered.connect(lambda: self.copy_path_from_quick_panel(row))
            menu.addAction(action_copy_path)
            
            # Otwórz folder docelowy
            action_open_folder = QAction("Otwórz folder docelowy", self)
            action_open_folder.triggered.connect(lambda: self.open_folder_from_quick_panel(row))
            menu.addAction(action_open_folder)
        
        elif self.current_quick_mode in ('recent_folder', 'recent_opened'):
            menu.addSeparator()
            
            # Kopiuj ścieżkę
            action_copy_path = QAction("Kopiuj ścieżkę", self)
            action_copy_path.triggered.connect(lambda: self.copy_path_from_quick_panel(row))
            menu.addAction(action_copy_path)
            
            # Otwórz folder docelowy
            action_open_folder = QAction("Otwórz folder docelowy", self)
            action_open_folder.triggered.connect(lambda: self.open_folder_from_quick_panel(row))
            menu.addAction(action_open_folder)
        
        menu.exec(self.quick_panel_table.viewport().mapToGlobal(pos))
    
    def remove_favorite_from_quick_panel(self, row):
        """Usuwa plik z ulubionych poprzez panel szybkich akcji"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            return
        
        files = self.folders.get(self.current_folder, [])
        favorites = [f for f in files if f.get('pinned', False)]
        
        if row < len(favorites):
            file_data = favorites[row]
            file_data['pinned'] = False
            self.save_data()
            self.refresh_view()
            self.refresh_quick_panel()
    
    def copy_path_from_quick_panel(self, row):
        """Kopiuje ścieżkę pliku do schowka z panelu szybkich akcji"""
        path = self.get_path_from_quick_panel(row)
        if path:
            QApplication.clipboard().setText(path)
            QMessageBox.information(self, "Sukces", "Ścieżka skopiowana do schowka")
    
    def open_folder_from_quick_panel(self, row):
        """Otwiera folder zawierający plik z panelu szybkich akcji"""
        path = self.get_path_from_quick_panel(row)
        if path and os.path.exists(path):
            folder_path = os.path.dirname(path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        else:
            QMessageBox.warning(self, "Błąd", "Plik nie istnieje")
    
    def get_path_from_quick_panel(self, row):
        """Pobiera ścieżkę pliku z panelu szybkich akcji"""
        if self.current_quick_mode == 'favorites':
            if not self.current_folder or self.current_folder == "-- Wybierz folder --":
                return None
            
            files = self.folders.get(self.current_folder, [])
            favorites = [f for f in files if f.get('pinned', False)]
            
            if row < len(favorites):
                return favorites[row]['path']
        
        elif self.current_quick_mode == 'recent_folder':
            if not self.current_folder or self.current_folder == "-- Wybierz folder --":
                return None
            
            files = self.folders.get(self.current_folder, [])
            sorted_files = sorted(files, key=lambda f: f.get('added_date', ''), reverse=True)
            recent_files = sorted_files[:10]
            
            if row < len(recent_files):
                return recent_files[row]['path']
        
        elif self.current_quick_mode == 'recent_opened':
            sorted_history = sorted(self.file_access_history, key=lambda x: x[1], reverse=True)
            recent_opens = sorted_history[:10]
            
            if row < len(recent_opens):
                return recent_opens[row][0]
        
        return None
    
    def refresh_icon_view(self, files):
        """Odświeża widok ikon"""
        # Usuń wszystkie widgety
        while self.icon_view_layout.count():
            item = self.icon_view_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        
        # Dodaj nowe
        row, col = 0, 0
        max_cols = 6
        
        # Pobierz tagi dla aktualnego folderu
        current_folder_tags = self.get_current_tags()
        
        for file_data in files:
            # Pobierz kolor tagu jeśli istnieje
            tag = file_data.get('tag', '')
            tag_color = current_folder_tags.get(tag) if tag else None
            
            file_item = FileItem(file_data, self.icons_dir, tag_color, main_window=self)
            self.icon_view_layout.addWidget(file_item, row, col)
            
            col += 1
            if col >= max_cols:
                col = 0
                row += 1
        
        # Dodaj stretch na końcu
        self.icon_view_layout.setRowStretch(row + 1, 1)
    
    def add_new_file(self):
        """Dodaje nowy plik/folder/skrót"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            QMessageBox.warning(
                self, 
                "Błąd", 
                "Najpierw wybierz lub utwórz folder!"
            )
            return
        
        # Dialog wyboru typu
        dialog = AddItemDialog(self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        
        selection_type = dialog.get_selection()
        item_path = None
        
        if selection_type == "file":
            item_path, _ = QFileDialog.getOpenFileName(
                self,
                "Wybierz plik",
                "",
                "Wszystkie pliki (*.*)"
            )
        elif selection_type == "folder":
            item_path = QFileDialog.getExistingDirectory(
                self,
                "Wybierz folder",
                ""
            )
        elif selection_type == "shortcut":
            item_path, _ = QFileDialog.getOpenFileName(
                self,
                "Wybierz skrót",
                "",
                "Skróty (*.lnk);;Wszystkie pliki (*.*)"
            )
        
        if item_path:
            # Sprawdź czy element już istnieje w folderze
            for file_data in self.folders[self.current_folder]:
                if file_data['path'] == item_path:
                    QMessageBox.warning(
                        self,
                        "Błąd",
                        "Ten element już istnieje w tym folderze!"
                    )
                    return
            
            file_info = QFileInfo(item_path)
            
            # Zapisz kopię ikony
            icon_path = self._save_icon(item_path, file_info.fileName())
            
            file_data = {
                'name': file_info.fileName() if file_info.isFile() else os.path.basename(item_path),
                'path': item_path,
                'type': selection_type,
                'tag': '',
                'comment': '',
                'icon_path': icon_path,
                'created': file_info.birthTime().toString("yyyy-MM-dd HH:mm:ss") if file_info.birthTime().isValid() else datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'modified': file_info.lastModified().toString("yyyy-MM-dd HH:mm:ss") if file_info.lastModified().isValid() else datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            }
            
            self.folders[self.current_folder].append(file_data)
            self.save_data()
            self.refresh_view()
    
    def _save_icon(self, item_path, item_name):
        """Zapisuje kopię ikony elementu"""
        try:
            icon_provider = QFileIconProvider()
            file_info = QFileInfo(item_path)
            icon = icon_provider.icon(file_info)
            pixmap = icon.pixmap(QSize(64, 64))
            
            # Utwórz unikalną nazwę pliku ikony
            safe_name = "".join(c if c.isalnum() or c in ('-', '_') else '_' for c in item_name)
            icon_filename = f"{safe_name}_{abs(hash(item_path)) % 1000000}.png"
            icon_path = os.path.join(self.icons_dir, icon_filename)
            
            # Zapisz ikonę
            pixmap.save(icon_path, "PNG")
            return icon_path
        except Exception as e:
            print(f"Błąd podczas zapisywania ikony: {e}")
            return ""
    
    def remove_file(self):
        """Usuwa zaznaczony plik"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            return
        
        if self.current_view == "list":
            selected_rows = self.table_view.selectedIndexes()
            if not selected_rows:
                QMessageBox.warning(self, "Błąd", "Zaznacz plik do usunięcia!")
                return
            
            row = selected_rows[0].row()
            item = self.table_view.item(row, 0)
            if item is None:
                return
            
            file_name = item.text()
            
            reply = QMessageBox.question(
                self,
                "Potwierdzenie",
                f"Czy na pewno chcesz usunąć skrót do pliku '{file_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del self.folders[self.current_folder][row]
                self.save_data()
                self.refresh_view()
    
    def add_comment(self):
        """Dodaje/edytuje komentarz do zaznaczonego pliku"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            return
        
        if self.current_view == "list":
            selected_rows = self.table_view.selectedIndexes()
            if not selected_rows:
                QMessageBox.warning(self, "Błąd", "Zaznacz plik!")
                return
            
            row = selected_rows[0].row()
            file_data = self.folders[self.current_folder][row]
            
            dialog = FileCommentDialog(
                self,
                file_data.get('tag', ''),
                file_data.get('comment', '')
            )
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                data = dialog.get_data()
                file_data['tag'] = data['tag']
                file_data['comment'] = data['comment']
                self.save_data()
                self.refresh_view()
    
    def edit_tags(self):
        """Otwiera dialog zarządzania tagami dla aktualnego folderu"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw wybierz lub utwórz folder!"
            )
            return
        
        # Pobierz aktualne tagi dla tego folderu
        current_tags = self.get_current_tags()
        
        dialog = TagiFolderowDialog(current_tags, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Aktualizuj tagi dla aktualnego folderu
            self.folder_tags[self.current_folder] = dialog.get_tags()
            self.save_data()
            
            # Zaktualizuj listę tagów w filtrze
            self.update_filter_tags_list()
            
            self.refresh_view()
            
            QMessageBox.information(
                self,
                "Sukces",
                f"Tagi dla folderu '{self.current_folder}' zostały zaktualizowane!"
            )
    
    def update_filter_tags_list(self):
        """Aktualizuje listę tagów w filtrze dla aktualnego folderu"""
        current_selection = self.filter_tag_combo.currentText()
        
        self.filter_tag_combo.clear()
        self.filter_tag_combo.addItem("-- Wszystkie --")
        
        # Pobierz tagi dla aktualnego folderu
        current_tags = self.get_current_tags()
        self.filter_tag_combo.addItems(sorted(current_tags.keys()))
        
        # Przywróć poprzednie zaznaczenie jeśli tag nadal istnieje
        if current_selection and current_selection != "-- Wszystkie --":
            index = self.filter_tag_combo.findText(current_selection)
            if index >= 0:
                self.filter_tag_combo.setCurrentIndex(index)
    
    def on_table_selection_changed(self):
        """Obsługa zmiany zaznaczenia w tabeli"""
        selected_rows = self.table_view.selectedIndexes()
        if selected_rows:
            self.selected_file = selected_rows[0].row()
    
    def on_cell_double_clicked(self, row, column):
        """Obsługa dwukrotnego kliknięcia w komórkę tabeli"""
        if column == 0:
            self.on_cell_clicked(row, column)
            return
        
        file_data, _ = self.get_file_data_from_row(row)
        if not file_data:
            return
        
        if column == 1:
            self.open_file(file_data)
        elif column == 2:
            self.change_tag_context(file_data)
        elif column == 3:
            self.open_note(file_data)
        elif column in (4, 5):
            self.show_file_properties(file_data)
        elif column == 6:
            self.open_target_folder(file_data)

    def show_file_properties(self, file_data):
        """Otwiera systemowe okno właściwości pliku używając Windows API"""
        path = file_data['path']
        
        if not os.path.exists(path):
            QMessageBox.warning(self, "Błąd", f"Plik nie istnieje:\n{path}")
            return
        
        try:
            SEE_MASK_INVOKEIDLIST = 0x0000000C

            class SHELLEXECUTEINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", wintypes.DWORD),
                    ("fMask", ctypes.c_ulong),
                    ("hwnd", wintypes.HWND),
                    ("lpVerb", wintypes.LPCWSTR),
                    ("lpFile", wintypes.LPCWSTR),
                    ("lpParameters", wintypes.LPCWSTR),
                    ("lpDirectory", wintypes.LPCWSTR),
                    ("nShow", ctypes.c_int),
                    ("hInstApp", wintypes.HINSTANCE),
                    ("lpIDList", ctypes.c_void_p),
                    ("lpClass", wintypes.LPCWSTR),
                    ("hKeyClass", wintypes.HKEY),
                    ("dwHotKey", wintypes.DWORD),
                    ("hIconOrMonitor", wintypes.HANDLE),
                ]

            sei = SHELLEXECUTEINFO()
            sei.cbSize = ctypes.sizeof(sei)
            sei.fMask = SEE_MASK_INVOKEIDLIST
            sei.hwnd = None
            sei.lpVerb = "properties"
            sei.lpFile = os.path.normpath(path)
            sei.lpParameters = None
            sei.lpDirectory = None
            sei.nShow = 1
            sei.hInstApp = None

            ctypes.windll.shell32.ShellExecuteExW(ctypes.byref(sei))

        except Exception as e:
            try:
                subprocess.Popen(['explorer', '/select,', os.path.normpath(path)])
            except Exception:
                QMessageBox.warning(self, "Błąd", f"Nie udało się otworzyć właściwości:\n{str(e)}")
    
    def show_context_menu(self, file_item, pos):
        """Wyświetla menu kontekstowe dla elementu w widoku ikon"""
        if not file_item or not file_item.file_data:
            return
        
        file_data = file_item.file_data
        
        menu = QMenu(self)
        
        # Dodaj/usuń z ulubionych
        is_pinned = file_data.get('pinned', False)
        if is_pinned:
            action_favorite = QAction("⭐ Usuń z ulubionych", self)
            action_favorite.triggered.connect(lambda: self.toggle_favorite(file_data, False))
        else:
            action_favorite = QAction("⭐ Dodaj do ulubionych", self)
            action_favorite.triggered.connect(lambda: self.toggle_favorite(file_data, True))
        menu.addAction(action_favorite)
        
        menu.addSeparator()
        
        # Otwórz
        action_open = QAction("Otwórz", self)
        action_open.triggered.connect(lambda: self.open_file(file_data))
        menu.addAction(action_open)
        
        # Otwórz folder docelowy
        action_open_folder = QAction("Otwórz folder docelowy", self)
        action_open_folder.triggered.connect(lambda: self.open_target_folder(file_data))
        menu.addAction(action_open_folder)
        
        # Otwórz komentarz
        action_open_note = QAction("Otwórz komentarz", self)
        action_open_note.triggered.connect(lambda: self.open_note(file_data))
        menu.addAction(action_open_note)
        
        menu.addSeparator()
        
        # Zmień tag
        action_change_tag = QAction("Zmień tag", self)
        action_change_tag.triggered.connect(lambda: self.change_tag_context(file_data))
        menu.addAction(action_change_tag)
        
        # Kopiuj ścieżkę
        action_copy_path = QAction("Kopiuj ścieżkę", self)
        action_copy_path.triggered.connect(lambda: self.copy_path(file_data))
        menu.addAction(action_copy_path)
        
        menu.addSeparator()
        
        # Udostępnij
        action_share = QAction("Udostępnij", self)
        action_share.triggered.connect(lambda: self.share_file(file_data))
        menu.addAction(action_share)
        
        menu.addSeparator()
        
        # Przenieś do innego folderu
        if len(self.folders) > 1:
            move_menu = QMenu("Przenieś do innego folderu", self)
            for folder_name in sorted(self.folders.keys()):
                if folder_name != self.current_folder:
                    action = QAction(folder_name, self)
                    action.triggered.connect(lambda checked, fn=folder_name: self.move_to_folder(file_data, fn))
                    move_menu.addAction(action)
            menu.addMenu(move_menu)
        
        menu.addSeparator()
        
        # Usuń z folderu aplikacji
        action_remove_from_app = QAction("Usuń z folderu aplikacji", self)
        action_remove_from_app.triggered.connect(lambda: self.remove_from_app_folder(file_data))
        menu.addAction(action_remove_from_app)
        
        # Usuń w miejscu docelowym
        action_delete_target = QAction("Usuń w miejscu docelowym", self)
        action_delete_target.triggered.connect(lambda: self.delete_target_file(file_data))
        menu.addAction(action_delete_target)
        
        menu.exec(pos)
    
    def open_file(self, file_data_or_path):
        """Otwiera plik/folder/skrót"""
        # Obsługa zarówno file_data (dict) jak i path (str)
        if isinstance(file_data_or_path, dict):
            path = file_data_or_path['path']
        else:
            path = file_data_or_path
        
        if os.path.exists(path):
            # Dodaj do historii otwierania
            self.file_access_history.append((path, datetime.now()))
            # Ogranicz historię do 50 ostatnich wpisów
            if len(self.file_access_history) > 50:
                self.file_access_history = self.file_access_history[-50:]
            self.save_data()
            
            # Odśwież panel jeśli jest widoczny i w trybie ostatnio otwieranych
            if self.quick_panel_visible and self.current_quick_mode == 'recent_opened':
                self.refresh_quick_panel()
            
            QDesktopServices.openUrl(QUrl.fromLocalFile(path))
        else:
            QMessageBox.warning(self, "Błąd", f"Plik nie istnieje:\n{path}")
    
    def open_target_folder(self, file_data):
        """Otwiera folder zawierający plik"""
        path = file_data['path']
        if os.path.exists(path):
            folder_path = os.path.dirname(path)
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder_path))
        else:
            QMessageBox.warning(self, "Błąd", f"Ścieżka nie istnieje:\n{path}")
    
    def open_note(self, file_data):
        """Otwiera okno z notatką (komentarzem)"""
        current_comment = file_data.get('comment', '')
        current_tag = file_data.get('tag', '')
        
        dialog = FileCommentDialog(self, current_tag, current_comment)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            file_data['tag'] = data['tag']
            file_data['comment'] = data['comment']
            self.save_data()
            self.refresh_view()
    
    def toggle_favorite(self, file_data, is_pinned):
        """Przełącza status ulubionego dla pliku"""
        file_data['pinned'] = is_pinned
        self.save_data()
        self.refresh_view()
        
        # Odśwież panel jeśli jest widoczny i w trybie ulubionych
        if self.quick_panel_visible and self.current_quick_mode == 'favorites':
            self.refresh_quick_panel()
    
    def change_tag_context(self, file_data):
        """Zmienia tag dla pliku (z menu kontekstowego)"""
        from PyQt6.QtWidgets import QInputDialog
        
        # Pobierz listę tagów dla aktualnego folderu
        current_folder_tags = self.get_current_tags()
        tags_list = [""] + sorted(current_folder_tags.keys())
        current_tag = file_data.get('tag', '')
        
        tag, ok = QInputDialog.getItem(
            self,
            "Zmień tag",
            "Wybierz tag:",
            tags_list,
            tags_list.index(current_tag) if current_tag in tags_list else 0,
            False
        )
        
        if ok:
            file_data['tag'] = tag
            self.save_data()
            self.refresh_view()
    
    def copy_path(self, file_data):
        """Kopiuje ścieżkę do schowka"""
        path = file_data['path']
        clipboard = QApplication.clipboard()
        if clipboard is not None:
            clipboard.setText(path)
            QMessageBox.information(self, "Sukces", f"Ścieżka skopiowana do schowka:\n{path}")
        else:
            QMessageBox.warning(self, "Błąd", "Nie można uzyskać dostępu do schowka")
    
    def handle_icon_selection(self, file_item, modifiers):
        """Obsługuje zaznaczanie ikon z Ctrl i Shift"""
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            # Ctrl - dodaj/usuń z zaznaczenia
            if file_item in self.selected_icon_items:
                self.selected_icon_items.remove(file_item)
                file_item.set_selected(False)
            else:
                self.selected_icon_items.append(file_item)
                file_item.set_selected(True)
        elif modifiers & Qt.KeyboardModifier.ShiftModifier:
            # Shift - zaznacz zakres (nie implementujemy teraz, zachowaj jako przyszłą opcję)
            # Na razie działamy jak Ctrl
            if file_item in self.selected_icon_items:
                self.selected_icon_items.remove(file_item)
                file_item.set_selected(False)
            else:
                self.selected_icon_items.append(file_item)
                file_item.set_selected(True)
        else:
            # Bez modyfikatorów - zaznacz tylko ten element
            for item in self.selected_icon_items:
                item.set_selected(False)
            self.selected_icon_items.clear()
            self.selected_icon_items.append(file_item)
            file_item.set_selected(True)
    
    def show_table_context_menu(self, pos):
        """Wyświetla menu kontekstowe dla widoku tabeli"""
        # Pobierz zaznaczony wiersz
        selected_rows = self.table_view.selectionModel().selectedRows()
        
        if not selected_rows:
            return
        
        # Jeśli zaznaczono tylko jeden wiersz, pokaż pełne menu
        if len(selected_rows) == 1:
            row = selected_rows[0].row()
            if row < 0 or row >= len(self.folders[self.current_folder]):
                return
            
            file_data = self.folders[self.current_folder][row]
            
            menu = QMenu(self)
            
            # Otwórz
            action_open = QAction("Otwórz", self)
            action_open.triggered.connect(lambda: self.open_file(file_data))
            menu.addAction(action_open)
            
            # Otwórz folder docelowy
            action_open_folder = QAction("Otwórz folder docelowy", self)
            action_open_folder.triggered.connect(lambda: self.open_target_folder(file_data))
            menu.addAction(action_open_folder)
            
            # Otwórz komentarz
            action_open_note = QAction("Otwórz komentarz", self)
            action_open_note.triggered.connect(lambda: self.open_note(file_data))
            menu.addAction(action_open_note)
            
            menu.addSeparator()
            
            # Zmień tag
            action_change_tag = QAction("Zmień tag", self)
            action_change_tag.triggered.connect(lambda: self.change_tag_context(file_data))
            menu.addAction(action_change_tag)
            
            # Kopiuj ścieżkę
            action_copy_path = QAction("Kopiuj ścieżkę", self)
            action_copy_path.triggered.connect(lambda: self.copy_path(file_data))
            menu.addAction(action_copy_path)
            
            menu.addSeparator()
            
            # Udostępnij
            action_share = QAction("Udostępnij", self)
            action_share.triggered.connect(lambda: self.share_selected_files())
            menu.addAction(action_share)
            
            menu.addSeparator()
            
            # Przenieś do innego folderu
            if len(self.folders) > 1:
                move_menu = QMenu("Przenieś do innego folderu", self)
                for folder_name in sorted(self.folders.keys()):
                    if folder_name != self.current_folder:
                        action = QAction(folder_name, self)
                        action.triggered.connect(lambda checked, fn=folder_name: self.move_to_folder(file_data, fn))
                        move_menu.addAction(action)
                menu.addMenu(move_menu)
            
            menu.addSeparator()
            
            # Usuń z folderu aplikacji
            action_remove_from_app = QAction("Usuń z folderu aplikacji", self)
            action_remove_from_app.triggered.connect(lambda: self.remove_from_app_folder(file_data))
            menu.addAction(action_remove_from_app)
            
            # Usuń w miejscu docelowym
            action_delete_target = QAction("Usuń w miejscu docelowym", self)
            action_delete_target.triggered.connect(lambda: self.delete_target_file(file_data))
            menu.addAction(action_delete_target)
            
            # Właściwości
            action_properties = QAction("Właściwości", self)
            action_properties.triggered.connect(lambda: self.show_file_properties(file_data))
            menu.addAction(action_properties)
            
            menu.exec(self.table_view.viewport().mapToGlobal(pos))
        else:
            # Dla wielu zaznaczonych wierszy - uproszczone menu
            menu = QMenu(self)
            
            action_share = QAction(f"Udostępnij ({len(selected_rows)} plików)", self)
            action_share.triggered.connect(lambda: self.share_selected_files())
            menu.addAction(action_share)
            
            menu.addSeparator()
            
            # Przenieś do innego folderu
            if len(self.folders) > 1:
                move_menu = QMenu("Przenieś do innego folderu", self)
                for folder_name in sorted(self.folders.keys()):
                    if folder_name != self.current_folder:
                        action = QAction(folder_name, self)
                        action.triggered.connect(lambda checked, fn=folder_name: self.move_selected_to_folder(fn))
                        move_menu.addAction(action)
                menu.addMenu(move_menu)
            
            menu.addSeparator()
            
            action_remove = QAction(f"Usuń z folderu aplikacji ({len(selected_rows)} plików)", self)
            action_remove.triggered.connect(lambda: self.remove_selected_from_app())
            menu.addAction(action_remove)
            
            menu.exec(self.table_view.viewport().mapToGlobal(pos))
    
    def get_selected_files(self):
        """Zwraca listę zaznaczonych plików w zależności od aktualnego widoku"""
        selected_files = []
        
        if self.current_view == "list":
            # Widok tabeli
            selected_rows = self.table_view.selectionModel().selectedRows()
            for row_index in selected_rows:
                row = row_index.row()
                if row < len(self.folders[self.current_folder]):
                    selected_files.append(self.folders[self.current_folder][row])
        else:
            # Widok ikon
            for item in self.selected_icon_items:
                if item.file_data:
                    selected_files.append(item.file_data)
        
        return selected_files
    
    def share_selected_files(self):
        """Udostępnia zaznaczone pliki"""
        selected_files = self.get_selected_files()
        
        if not selected_files:
            QMessageBox.warning(self, "Błąd", "Nie zaznaczono żadnego pliku.")
            return
        
        # Sprawdź czy wszystkie zaznaczone elementy to pliki (nie foldery)
        invalid_items = []
        for file_data in selected_files:
            file_path = file_data['path']
            if not os.path.exists(file_path):
                invalid_items.append(f"{file_data['name']} (nie istnieje)")
            elif os.path.isdir(file_path):
                invalid_items.append(f"{file_data['name']} (folder)")
        
        if invalid_items:
            QMessageBox.warning(
                self, 
                "Błąd", 
                "Następujące elementy nie mogą być udostępnione:\n" + "\n".join(invalid_items)
            )
            return
        
        # Sprawdź rozmiar plików (max 100 MB każdy)
        max_size = 100 * 1024 * 1024  # 100 MB
        oversized_files = []
        for file_data in selected_files:
            file_size = os.path.getsize(file_data['path'])
            if file_size > max_size:
                oversized_files.append(
                    f"{file_data['name']} ({file_size / (1024*1024):.1f} MB)"
                )
        
        if oversized_files:
            QMessageBox.warning(
                self,
                "Błąd",
                f"Następujące pliki przekraczają limit 100 MB:\n" + "\n".join(oversized_files)
            )
            return
        
        # Otwórz dialog do wprowadzenia danych (dla wszystkich plików)
        file_names = ", ".join([f['name'] for f in selected_files[:3]])
        if len(selected_files) > 3:
            file_names += f" i {len(selected_files) - 3} więcej..."
        
        dialog = ShareFileDialog(file_names, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            # Walidacja
            if not data['recipient_email']:
                QMessageBox.warning(self, "Błąd", "Podaj adres email odbiorcy.")
                return
            
            if not data['sender_name']:
                QMessageBox.warning(self, "Błąd", "Podaj swoje imię/nazwę.")
                return
            
            if not data['api_url']:
                QMessageBox.warning(self, "Błąd", "Podaj URL API.")
                return
            
            # Wyślij wszystkie pliki
            for file_data in selected_files:
                file_path = file_data['path']
                file_name = os.path.basename(file_path)
                self.upload_file_to_api(file_path, file_name, data)
    
    def share_file(self, file_data):
        """Udostępnia plik przez API (Backblaze B2 + Email)"""
        file_path = file_data['path']
        
        # Sprawdź czy plik istnieje
        if not os.path.exists(file_path):
            QMessageBox.warning(self, "Błąd", f"Plik nie istnieje:\n{file_path}")
            return
        
        # Sprawdź czy to plik (nie folder)
        if os.path.isdir(file_path):
            QMessageBox.warning(self, "Błąd", "Nie można udostępniać folderów.\nWybierz plik.")
            return
        
        # Sprawdź rozmiar pliku (max 100 MB)
        file_size = os.path.getsize(file_path)
        max_size = 100 * 1024 * 1024  # 100 MB
        if file_size > max_size:
            QMessageBox.warning(
                self, 
                "Błąd", 
                f"Plik jest za duży ({file_size / (1024*1024):.1f} MB).\n"
                f"Maksymalny rozmiar: {max_size / (1024*1024):.0f} MB"
            )
            return
        
        # Otwórz dialog do wprowadzenia danych
        file_name = os.path.basename(file_path)
        dialog = ShareFileDialog(file_name, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            # Walidacja
            if not data['recipient_email']:
                QMessageBox.warning(self, "Błąd", "Podaj adres email odbiorcy.")
                return
            
            if not data['sender_name']:
                QMessageBox.warning(self, "Błąd", "Podaj swoje imię/nazwę.")
                return
            
            if not data['api_url']:
                QMessageBox.warning(self, "Błąd", "Podaj URL API.")
                return
            
            # Wyślij plik do API
            self.upload_file_to_api(file_path, file_name, data)
    
    def upload_file_to_api(self, file_path, file_name, share_data):
        """Wysyła plik do API"""
        progress = None
        try:
            # Przygotuj URL
            api_url = share_data['api_url'].rstrip('/')
            endpoint = f"{api_url}/api/v1/share/upload"
            
            # Pokazuj dialog postępu
            progress = QMessageBox(self)
            progress.setWindowTitle("Wysyłanie pliku")
            progress.setText(f"Wysyłanie pliku: {file_name}\nProszę czekać...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.show()
            QApplication.processEvents()
            
            # Przygotuj dane do wysłania
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_name, f, 'application/octet-stream')
                }
                
                data = {
                    'recipient_email': share_data['recipient_email'],
                    'sender_email': 'user@pro-ka-po.com',  # Można dodać dialog do tego
                    'sender_name': share_data['sender_name'],
                    'language': share_data['language']
                }
                
                # Wyślij request
                response = requests.post(
                    endpoint,
                    files=files,
                    data=data,
                    timeout=120  # 2 minuty timeout dla dużych plików
                )
            
            if progress:
                progress.close()
            
            # Obsługa odpowiedzi
            if response.status_code == 201:
                result = response.json()
                if result.get('success'):
                    QMessageBox.information(
                        self,
                        "Sukces",
                        f"Plik został udostępniony!\n\n"
                        f"Email wysłany do: {share_data['recipient_email']}\n"
                        f"Plik: {file_name}"
                    )
                else:
                    QMessageBox.warning(
                        self,
                        "Ostrzeżenie",
                        f"Plik został przesłany, ale:\n{result.get('message', 'Nieznany błąd')}"
                    )
            else:
                error_msg = "Nieznany błąd"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('detail', str(error_data))
                except:
                    error_msg = response.text or f"HTTP {response.status_code}"
                
                QMessageBox.critical(
                    self,
                    "Błąd",
                    f"Nie udało się udostępnić pliku.\n\n"
                    f"Status: {response.status_code}\n"
                    f"Błąd: {error_msg}"
                )
        
        except requests.exceptions.ConnectionError:
            if progress:
                progress.close()
            QMessageBox.critical(
                self,
                "Błąd połączenia",
                f"Nie można połączyć się z API:\n{share_data['api_url']}\n\n"
                f"Sprawdź:\n"
                f"1. Czy adres URL jest poprawny\n"
                f"2. Czy serwer API jest uruchomiony\n"
                f"3. Czy masz połączenie z internetem"
            )
        
        except requests.exceptions.Timeout:
            if progress:
                progress.close()
            QMessageBox.critical(
                self,
                "Przekroczono czas",
                f"Przekroczono limit czasu wysyłania pliku.\n"
                f"Plik może być za duży lub połączenie zbyt wolne."
            )
        
        except Exception as e:
            if progress:
                progress.close()
            QMessageBox.critical(
                self,
                "Błąd",
                f"Wystąpił nieoczekiwany błąd:\n{str(e)}"
            )
    
    def move_to_folder(self, file_data, target_folder):
        """Przenosi element do innego folderu"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            return
        
        # Sprawdź czy element już istnieje w folderze docelowym
        for existing_file in self.folders[target_folder]:
            if existing_file['path'] == file_data['path']:
                QMessageBox.warning(
                    self,
                    "Błąd",
                    f"Ten element już istnieje w folderze '{target_folder}'!"
                )
                return
        
        # Usuń z aktualnego folderu
        self.folders[self.current_folder].remove(file_data)
        
        # Dodaj do folderu docelowego
        self.folders[target_folder].append(file_data)
        
        self.save_data()
        self.refresh_view()
        
        QMessageBox.information(
            self,
            "Sukces",
            f"Element przeniesiony do folderu '{target_folder}'"
        )
    
    def move_selected_to_folder(self, target_folder):
        """Przenosi zaznaczone elementy do innego folderu"""
        selected_files = self.get_selected_files()
        
        if not selected_files:
            QMessageBox.warning(self, "Błąd", "Nie zaznaczono żadnego pliku.")
            return
        
        moved_count = 0
        skipped_count = 0
        
        for file_data in selected_files:
            # Sprawdź czy element już istnieje w folderze docelowym
            already_exists = False
            for existing_file in self.folders[target_folder]:
                if existing_file['path'] == file_data['path']:
                    already_exists = True
                    break
            
            if already_exists:
                skipped_count += 1
                continue
            
            # Usuń z aktualnego folderu
            self.folders[self.current_folder].remove(file_data)
            
            # Dodaj do folderu docelowego
            self.folders[target_folder].append(file_data)
            moved_count += 1
        
        self.save_data()
        self.refresh_view()
        
        # Wyczyść zaznaczenie
        self.selected_icon_items.clear()
        
        message = f"Przeniesiono {moved_count} element(ów) do folderu '{target_folder}'"
        if skipped_count > 0:
            message += f"\nPominięto {skipped_count} element(ów) (już istnieją w docelowym folderze)"
        
        QMessageBox.information(self, "Sukces", message)
    
    def remove_from_app_folder(self, file_data):
        """Usuwa element z folderu aplikacji (tylko skrót)"""
        if not self.current_folder or self.current_folder == "-- Wybierz folder --":
            return
        
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć skrót do '{file_data['name']}' z folderu aplikacji?\n\n"
            f"(Plik źródłowy pozostanie nienaruszony)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.folders[self.current_folder].remove(file_data)
            self.save_data()
            self.refresh_view()
            
            QMessageBox.information(
                self,
                "Sukces",
                "Skrót został usunięty z folderu aplikacji"
            )
    
    def remove_selected_from_app(self):
        """Usuwa zaznaczone elementy z folderu aplikacji"""
        selected_files = self.get_selected_files()
        
        if not selected_files:
            QMessageBox.warning(self, "Błąd", "Nie zaznaczono żadnego pliku.")
            return
        
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć {len(selected_files)} element(ów) z folderu aplikacji?\n\n"
            f"(Pliki źródłowe pozostaną nieruszone)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for file_data in selected_files:
                if file_data in self.folders[self.current_folder]:
                    self.folders[self.current_folder].remove(file_data)
            
            self.save_data()
            self.refresh_view()
            
            # Wyczyść zaznaczenie
            self.selected_icon_items.clear()
            
            QMessageBox.information(
                self,
                "Sukces",
                f"Usunięto {len(selected_files)} element(ów) z folderu aplikacji"
            )
    
    def delete_target_file(self, file_data):
        """Usuwa plik w miejscu docelowym"""
        path = file_data['path']

        if not os.path.exists(path):
            QMessageBox.warning(self, "Błąd", f"Plik nie istnieje:\n{path}")
            return

        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            (
                "⚠️ UWAGA! ⚠️\n\n"
                "Czy na pewno chcesz TRWALE USUNĄĆ plik/folder:\n"
                f"{path}\n\n"
                "Ta operacja jest NIEODWRACALNA!\n"
                "Plik zostanie usunięty z dysku!"
            ),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        try:
            if os.path.isdir(path):
                shutil.rmtree(path)
            else:
                os.remove(path)

            if self.current_folder and self.current_folder != "-- Wybierz folder --":
                if file_data in self.folders.get(self.current_folder, []):
                    self.folders[self.current_folder].remove(file_data)
                    self.save_data()
                    self.refresh_view()

            QMessageBox.information(self, "Sukces", "Plik został trwale usunięty")
        except Exception as exc:
            QMessageBox.critical(self, "Błąd", f"Nie udało się usunąć pliku:\n{exc}")

    def save_data(self):
        """Zapisuje dane modułu do pliku JSON"""
        data = {
            'folders': self.folders,
            'tags_colors': self.tags_colors,
            'folder_tags': self.folder_tags,
            'folder_view_preferences': self.folder_view_preferences,
            'file_access_history': [
                (path, ts.isoformat())
                for path, ts in self.file_access_history
            ],
        }

        data_file = os.path.join(os.path.dirname(__file__), "folder_data.json")
        with open(data_file, 'w', encoding='utf-8') as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)

    def load_data(self):
        """Ładuje dane modułu z pliku JSON"""
        data_file = os.path.join(os.path.dirname(__file__), "folder_data.json")
        if not os.path.exists(data_file):
            return

        try:
            with open(data_file, 'r', encoding='utf-8') as handle:
                data = json.load(handle)

            if isinstance(data, dict):
                self.folders = data.get('folders', {})
                self.tags_colors = data.get('tags_colors', {})
                self.folder_tags = data.get('folder_tags', {})
                self.folder_view_preferences = data.get('folder_view_preferences', {})

                history = data.get('file_access_history', [])
                self.file_access_history = []
                for entry in history:
                    try:
                        path, timestamp_str = entry
                        self.file_access_history.append((path, datetime.fromisoformat(timestamp_str)))
                    except Exception:
                        continue

                if self.tags_colors and not self.folder_tags:
                    for folder_name in self.folders.keys():
                        self.folder_tags[folder_name] = dict(self.tags_colors)
            else:
                self.folders = data
        except Exception as exc:
            print(f"Błąd podczas ładowania danych: {exc}")
            self.folders = {}
            self.tags_colors = {}
            self.folder_tags = {}
            self.folder_view_preferences = {}
            self.file_access_history = []


def main():
    """Funkcja główna - uruchamia aplikację"""
    app = QApplication(sys.argv)
    app.setApplicationName("Moduł Folder")
    app.setOrganizationName("Pro Ka Po Comer")
    window = FolderModule()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
