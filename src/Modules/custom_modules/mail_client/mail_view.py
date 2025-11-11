"""
Moduł głównego widoku klienta pocztowego

Funkcjonalność:
- Trójpanelowy interfejs (drzewo folderów | lista maili | treść)
- Wyświetlanie folderów email (Odebrane, Wysłane, Spam, itp.)
- Lista wiadomości z podglądem
- Podgląd wybranej wiadomości
- Podstawowe operacje (nowy mail, odpowiedz, usuń)

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-06
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import imaplib
import email
from email.header import decode_header
from collections import defaultdict
from datetime import datetime
from functools import partial
from pathlib import Path
from typing import Any, Dict, List, Optional, cast
from loguru import logger

from PyQt6.QtCore import Qt, QMimeData, QUrl, QEvent, QTimer
from PyQt6.QtGui import (
    QAction,
    QColor,
    QFont,
    QBrush,
    QDrag,
    QDragEnterEvent,
    QDragMoveEvent,
    QDropEvent,
)
from PyQt6.QtWidgets import (
    QApplication,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QLabel,
    QTreeWidget,
    QTreeWidgetItem,
    QTabWidget,
    QPushButton,
    QFrame,
    QLineEdit,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QTextEdit,
    QMenu,
    QMessageBox,
    QInputDialog,
    QFileDialog,
    QAbstractItemView,
    QSpinBox,
    QListWidget,
    QListWidgetItem,
    QDialog,
    QCheckBox,
    QDialogButtonBox,
    QHeaderView,
    QScrollArea,
)

# Import ThemeManager i i18n
try:
    from src.utils.theme_manager import get_theme_manager
    from src.utils.i18n_manager import get_i18n, t
    from src.database.email_accounts_db import EmailAccountsDatabase
    from src.core.config import config
except ImportError:
    # Fallback dla uruchomienia standalone
    get_theme_manager = None
    get_i18n = None
    t = lambda key, **kwargs: kwargs.get('default', key)
    EmailAccountsDatabase = None
    config = None

# Obsługa importów - zarówno dla uruchomienia jako moduł, jak i skrypt
if __name__ == '__main__':
    # Uruchomienie jako skrypt - dodaj katalog nadrzędny do ścieżki
    import sys
    from pathlib import Path
    parent_dir = Path(__file__).parent.parent
    if str(parent_dir) not in sys.path:
        sys.path.insert(0, str(parent_dir))
    
    from mail_client.autoresponder import AutoresponderManager
    from mail_client.queue_view import QueueView
    from mail_client.cache_integration import integrate_cache_with_mail_view
    from mail_client.mail_widgets import (
        MailTableWidget,
        FolderTreeWidget,
        FavoritesTreeWidget,
        RecentFavoritesListWidget,
    )
else:
    # Uruchomienie jako moduł - użyj importów względnych
    from .autoresponder import AutoresponderManager
    from .queue_view import QueueView
    from .cache_integration import integrate_cache_with_mail_view
    from .mail_widgets import (
        MailTableWidget,
        FolderTreeWidget,
        FavoritesTreeWidget,
        RecentFavoritesListWidget,
    )


class MailViewModule(QWidget):
    """Główny widok klienta pocztowego z listą maili i podglądem treści."""

    LAYOUT_DESCRIPTIONS: Dict[int, str] = {
        1: "Treść na górze, maile na dole",
        2: "Treść na dole, maile u góry",
        3: "Treść po lewej, maile po prawej",
        4: "Maile po lewej, treść po prawej",
    }

    favorite_files: List[Dict[str, Any]]
    mail_tags: List[Dict[str, Any]]
    sample_mails: Dict[str, List[Dict[str, Any]]]
    current_folder_mails: List[Dict[str, Any]]
    displayed_mails: List[Dict[str, Any]]
    current_mail: Optional[Dict[str, Any]]
    layout_actions: Dict[int, QAction]
    protected_folders: set[str]
    mail_uid_map: Dict[str, Dict[str, Any]]
    mail_uid_counter: int

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        # Inicjalizacja menedżerów z bezpiecznym wywołaniem
        try:
            self.theme_manager = get_theme_manager()
        except:
            self.theme_manager = None
        
        try:
            self.i18n = get_i18n()
        except:
            self.i18n = None
        
        # User ID - będzie ustawiony przez set_user_data()
        self.user_id = None
        
        # Inicjalizacja bazy danych kont email (centralna baza aplikacji)
        try:
            if EmailAccountsDatabase and config:
                db_path = config.DATA_DIR / "email_accounts.db"
                self.email_accounts_db = EmailAccountsDatabase(str(db_path))
                logger.info("[ProMail] Connected to central EmailAccountsDatabase")
            else:
                self.email_accounts_db = None
                logger.warning("[ProMail] EmailAccountsDatabase not available")
        except Exception as e:
            logger.error(f"[ProMail] Failed to initialize EmailAccountsDatabase: {e}")
            self.email_accounts_db = None

        self.tags_file = Path("mail_client/mail_tags.json")
        self.contact_tags_file = Path("mail_client/contact_tags.json")
        self.contact_colors_file = Path("mail_client/contact_colors.json")
        self.contact_tag_assignments_file = Path("mail_client/contact_tag_assignments.json")
        self.column_order_file = Path("mail_client/column_order.json")
        # Usunięto: self.accounts_file - teraz używamy EmailAccountsDatabase
        self.favorite_files = self.load_favorite_files()
        self.mail_tags = self.load_mail_tags()
        self.mail_accounts = self.get_accounts_from_db()  # Nowa metoda pobierająca z DB
        self.mail_uid_counter = 0
        self.mail_uid_map: Dict[str, Dict[str, Any]] = {}
        
        # Cache dla optymalizacji wydajności - musi być PRZED prepare_mail_objects()
        self._email_parse_cache = {}  # from_string -> (email, display_name)
        self._qcolor_cache = {}  # color_string -> QColor object
        self._last_user_activity = datetime.now()  # Timestamp ostatniej aktywności użytkownika
        self._mail_index = {}  # uid -> (folder, mail_object) - szybkie wyszukiwanie
        
        self.sample_mails = self.generate_sample_mails()
        self.real_mails: Dict[str, List[Dict[str, Any]]] = {}
        self.protected_folders = {"Ulubione", "Odebrane", "Wysłane", "Szkice", "Spam", "Kosz"}
        
        # Cache - integracja dla szybkiego ładowania
        self.cache_integration = integrate_cache_with_mail_view(self)
        
        # Limit maili w pamięci (zapobiega wyczerpaniu RAM)
        self.MAX_MAILS_PER_FOLDER = 1000
        self.MAX_TOTAL_MAILS = 5000
        
        self.prepare_mail_objects()
        self.current_folder_mails = []
        self.displayed_mails = []
        self.current_mail = None
        self.email_fetcher = None  # Referencja do wątku pobierającego maile
        self.mail_scope = "folder"
        self.mail_filter_enabled = True
        self.view_mode = "folders"
        self.layout_mode = 1
        self.layout_actions = {}
        self.imap_folders = {}  # account_email -> lista folderów IMAP
        
        # Stan drzewa folderów (zapamiętywanie rozwinięcia sekcji)
        self.tree_expansion_state = {
            "smart": True,
            "folders": True,
        }
        
        # Wątki konwersacji
        self.threads_enabled = True  # Czy grupować w wątki
        self.mail_threads: Dict[str, List[Dict[str, Any]]] = {}  # thread_id -> lista maili
        self.collapsed_threads: set = set()  # Zwinięte wątki
        
        # Podgląd maili
        self.expanded_preview_rows: Dict[int, int] = {}  # mail_row -> preview_row (mapowanie wierszy z podglądem)
        
        # Zoom settings
        self.mail_table_zoom = 100  # Procent (100 = normalny rozmiar)
        self.mail_body_zoom = 100   # Procent
        
        # Tagi i kolory kontaktów
        self.contact_tag_definitions = self.load_contact_tag_definitions()  # Lista definicji tagów kontaktów
        self.contact_colors = self.load_contact_colors()  # email -> kolor (QColor)
        self.contact_tags = self.load_contact_tag_assignments()    # email -> lista tagów
        
        # Ustawienia widoczności kolumn (indeksy kolumn)
        # 0: ⭐, 1: Adres, 2: Imię/Nazwisko, 3: Odpowiedz, 4: ▶️, 5: Tytuł, 
        # 6: Data, 7: Rozmiar, 8: Wątków, 9: Tag, 10: Notatka
        self.column_visibility = {
            0: True,  # ⭐
            1: True,  # Adres mail
            2: True,  # Imię/Nazwisko
            3: True,  # Odpowiedz
            4: True,  # ▶️
            5: True,  # Tytuł
            6: True,  # Data
            7: True,  # Rozmiar
            8: True,  # Wątków
            9: True,  # Tag
            10: True, # Notatka
            11: True, # 🪄
        }
        self.column_names = {
            0: "⭐ Gwiazdka",
            1: "Adres mail",
            2: "Imię/Nazwisko",
            3: "Odpowiedz",
            4: "▶️ Rozwiń",
            5: "Tytuł",
            6: "Data",
            7: "Rozmiar",
            8: "Wątków",
            9: "Tag",
            10: "Notatka",
            11: "🪄 Magiczna różdżka",
        }
        # Domyślna kolejność kolumn - wczytaj zapisany układ
        self.column_order = self.load_column_order()
        
        # Szerokości kolumn - domyślne wartości
        self.column_widths_file = Path("mail_client/column_widths.json")
        self.column_widths = self.load_column_widths()

        # Status label (zastępuje QStatusBar)
        self.status_label = QLabel()
        self.status_label.setObjectName("mail_status_label")
        
        # Autoresponder
        autoresponder_file = Path("mail_client/autoresponder_rules.json")
        self.autoresponder = AutoresponderManager(autoresponder_file)
        
        # Timer do automatycznego odświeżania poczty (co 3 minuty = 180000 ms)
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.auto_refresh_mails)
        self.refresh_timer.start(180000)  # 3 minuty

        # Załaduj dane z cache (asynchronicznie w tle)
        self.cache_integration.load_from_cache_at_startup()

        # NIE pobieraj maili automatycznie przy starcie - użytkownik może nie używać ProMail
        # Maile będą pobrane gdy użytkownik otworzy moduł ProMail i kliknie Odśwież
        # self.fetch_real_emails_async()

        # Inicjalizacja UI
        self.init_ui()
        
        # Połącz z i18n dla auto-update tłumaczeń i motywu
        if self.i18n and hasattr(self.i18n, 'language_changed'):
            self.i18n.language_changed.connect(self.update_translations)
        
        # Aplikuj motyw i tłumaczenia
        self.apply_theme()
        self.update_translations()
        
        logger.info("[ProMail] MailViewModule initialized successfully")

    def init_ui(self) -> None:
        """Inicjalizuje interfejs użytkownika"""
        # Główny layout z odpowiednimi marginesami
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(8)
        
        # Toolbar jako panel przycisków (zastępuje QToolBar)
        toolbar_widget = self.create_toolbar()
        main_layout.addWidget(toolbar_widget)
        
        # Główny splitter
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(False)
        main_layout.addWidget(self.main_splitter)

        self.folder_tree_container = self.create_folder_tree()
        self.main_splitter.addWidget(self.folder_tree_container)

        self.content_splitter = QSplitter(Qt.Orientation.Vertical)
        self.content_splitter.setChildrenCollapsible(False)

        self.mail_content_container = self.create_mail_content()
        self.mail_list_container = self.create_mail_list()

        self.content_splitter.addWidget(self.mail_content_container)
        self.content_splitter.addWidget(self.mail_list_container)
        self.main_splitter.addWidget(self.content_splitter)

        # Utwórz widok kolejki (początkowo ukryty)
        self.queue_view = QueueView(self)
        self.queue_view.hide()
        self.main_splitter.addWidget(self.queue_view)

        self.main_splitter.setStretchFactor(0, 0)
        self.main_splitter.setStretchFactor(1, 1)
        
        # Status label usunięty - niepotrzebny

        self.apply_layout_mode(self.layout_mode, initial=True)

        if self.tree.topLevelItemCount() > 0:
            first_item = self.tree.topLevelItem(0)
            if first_item is not None:
                self.tree.setCurrentItem(first_item)
                self.load_folder_mails(first_item.text(0))
    
    def create_toolbar(self) -> QWidget:
        """Tworzy toolbar z przyciskami (zastępuje QToolBar)"""
        toolbar_widget = QWidget()
        toolbar_widget.setObjectName("mail_toolbar")
        toolbar_widget.setMaximumHeight(50)
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(8, 6, 8, 6)
        toolbar_layout.setSpacing(6)
        
        # Przycisk układu
        self.layout_button = QPushButton("⬛⬜ Układ 1", self)
        self.layout_button.setObjectName("mail_layout_btn")
        self.layout_menu = QMenu(self.layout_button)
        layout_options = [
            (1, "Układ 1: treść na górze, maile na dole"),
            (2, "Układ 2: treść na dole, maile u góry"),
            (3, "Układ 3: treść po lewej, maile po prawej"),
            (4, "Układ 4: maile po lewej, treść po prawej"),
        ]
        for mode, label in layout_options:
            action = QAction(label, self)
            action.setData(mode)
            action.setCheckable(True)
            self.layout_menu.addAction(action)
            self.layout_actions[mode] = action
        self.layout_menu.triggered.connect(self.on_layout_menu_triggered)
        self.layout_button.setMenu(self.layout_menu)
        toolbar_layout.addWidget(self.layout_button)
        
        # Przycisk kolejki
        self.toggle_queue_btn = QPushButton("📋 Pokaż kolejkę")
        self.toggle_queue_btn.setObjectName("mail_toggle_queue_btn")
        self.toggle_queue_btn.setCheckable(True)
        self.toggle_queue_btn.clicked.connect(self.toggle_queue_view)
        toolbar_layout.addWidget(self.toggle_queue_btn)
        
        # Separator (stretch)
        toolbar_layout.addSpacing(10)
        
        # Przyciski akcji
        self.new_mail_btn = QPushButton("📧 Nowy")
        self.new_mail_btn.setObjectName("mail_new_btn")
        self.new_mail_btn.setToolTip("Utwórz nową wiadomość")
        self.new_mail_btn.clicked.connect(self.new_mail)
        toolbar_layout.addWidget(self.new_mail_btn)
        
        self.reply_btn = QPushButton("↩️ Odpowiedz")
        self.reply_btn.setObjectName("mail_reply_btn")
        self.reply_btn.setToolTip("Odpowiedz na wybraną wiadomość")
        self.reply_btn.clicked.connect(self.reply_mail)
        toolbar_layout.addWidget(self.reply_btn)
        
        self.forward_btn = QPushButton("➡️ Przekaż")
        self.forward_btn.setObjectName("mail_forward_btn")
        self.forward_btn.setToolTip("Przekaż wybraną wiadomość")
        self.forward_btn.clicked.connect(self.forward_mail)
        toolbar_layout.addWidget(self.forward_btn)
        
        self.refresh_btn = QPushButton("🔄 Odśwież")
        self.refresh_btn.setObjectName("mail_refresh_btn")
        self.refresh_btn.setToolTip("Odśwież listę wiadomości")
        self.refresh_btn.clicked.connect(self.refresh_mails)
        toolbar_layout.addWidget(self.refresh_btn)
        
        toolbar_layout.addSpacing(10)
        
        # Ustawienia - wszystko w jednym przycisku konfiguracji
        self.config_btn = QPushButton("⚙️ Konfiguracja")
        self.config_btn.setObjectName("mail_config_btn")
        self.config_btn.setToolTip("Otwórz konfigurację ProMail (podpisy, filtry, autoresponder, kolumny, tagi)")
        self.config_btn.clicked.connect(self.open_config)
        toolbar_layout.addWidget(self.config_btn)
        
        toolbar_layout.addStretch()
        
        return toolbar_widget

    def create_mail_content(self):
        """Tworzy panel podglądu maila"""
        container = QWidget()
        container.setObjectName("mail_content_container")
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        container.setLayout(layout)

        header_widget = QWidget()
        header_widget.setObjectName("mail_header_widget")
        header_layout = QVBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(4)
        header_widget.setLayout(header_layout)
        header_widget.setMaximumHeight(140)

        self.mail_subject = QLabel("(Wybierz wiadomość)")
        self.mail_subject.setObjectName("mail_subject_label")
        subject_font = QFont()
        subject_font.setBold(True)
        subject_font.setPointSize(12)
        self.mail_subject.setFont(subject_font)
        header_layout.addWidget(self.mail_subject)

        self.mail_from = QLabel("")
        self.mail_from.setObjectName("mail_from_label")
        header_layout.addWidget(self.mail_from)

        self.mail_to = QLabel("")
        self.mail_to.setObjectName("mail_to_label")
        header_layout.addWidget(self.mail_to)

        self.mail_date = QLabel("")
        self.mail_date.setObjectName("mail_date_label")
        header_layout.addWidget(self.mail_date)

        self.mail_tag_label = QLabel("Tagi:")
        self.mail_tag_label.setObjectName("mail_tag_label")
        self.mail_tag_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        header_layout.addWidget(self.mail_tag_label)
        
        # ComboBox do zarządzania tagami wyświetlanego maila
        self.mail_tag_selector = QComboBox()
        self.mail_tag_selector.setMinimumWidth(150)
        self.mail_tag_selector.setMinimumHeight(28)  # Zwiększona wysokość dla lepszej czytelności
        self.mail_tag_selector.setPlaceholderText("Wybierz tag...")
        self.mail_tag_selector.currentIndexChanged.connect(self.on_mail_tag_selected)
        header_layout.addWidget(self.mail_tag_selector)

        self.mail_note_label = QLabel("")
        self.mail_note_label.setObjectName("mail_note_label")
        header_layout.addWidget(self.mail_note_label)

        header_layout.addStretch()
        layout.addWidget(header_widget)

        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)

        self.mail_body = QTextEdit()
        self.mail_body.setObjectName("mail_body_text")
        self.mail_body.setReadOnly(True)
        self.mail_body.installEventFilter(self)  # Zainstaluj filtr do obsługi Ctrl+Scroll
        layout.addWidget(self.mail_body)

        # Sekcja załączników - zwijanalna
        self.attachments_toggle_btn = QPushButton("▶️ Załączniki")
        self.attachments_toggle_btn.setCheckable(True)
        self.attachments_toggle_btn.setChecked(False)  # Domyślnie zwinięte
        self.attachments_toggle_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 5px;
                border: none;
                background-color: transparent;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.05);
            }
        """)
        self.attachments_toggle_btn.clicked.connect(self.toggle_attachments_section)
        layout.addWidget(self.attachments_toggle_btn)
        
        self.attachments_container = QWidget()
        self.attachments_container.setObjectName("mail_attachments_container")
        self.attachments_layout = QVBoxLayout(self.attachments_container)
        self.attachments_layout.setContentsMargins(0, 0, 0, 0)
        self.attachments_layout.setSpacing(5)
        layout.addWidget(self.attachments_container)
        self.attachments_container.hide()  # Ukryj domyślnie

        return container

    def on_layout_menu_triggered(self, action):
        """Obsługuje wybór układu z menu"""
        if action is None:
            return
        mode = action.data()
        if mode is None:
            return
        try:
            mode = int(mode)
        except (TypeError, ValueError):
            return
        self.apply_layout_mode(mode)

    def apply_layout_mode(self, mode, initial=False):
        """Zmienia układ listy maili i treści"""
        if mode not in self.LAYOUT_DESCRIPTIONS:
            return
        self.layout_mode = mode

        # Jeśli splitter nie jest jeszcze gotowy (np. podczas inicjalizacji), tylko uaktualnij UI
        if not hasattr(self, "content_splitter"):
            self.update_layout_ui_state()
            return

        vertical_mode = mode in (1, 2)
        self.content_splitter.setOrientation(
            Qt.Orientation.Vertical if vertical_mode else Qt.Orientation.Horizontal
        )

        if mode == 1:
            order = [self.mail_content_container, self.mail_list_container]
            sizes = [600, 400]
        elif mode == 2:
            order = [self.mail_list_container, self.mail_content_container]
            sizes = [400, 600]
        elif mode == 3:
            order = [self.mail_content_container, self.mail_list_container]
            sizes = [600, 400]
        else:
            order = [self.mail_list_container, self.mail_content_container]
            sizes = [400, 600]

        self._set_splitter_order(order)

        if sizes and len(sizes) == self.content_splitter.count():
            self.content_splitter.setSizes(sizes)

        self.update_layout_ui_state()

        if not initial:
            description = self.LAYOUT_DESCRIPTIONS.get(mode, "")
            self.show_status_message(
                f"Aktywny układ {mode}: {description}",
                2500,
            )

    def _set_splitter_order(self, widgets):
        """Ustawia kolejność widgetów w splitterze"""
        for index, widget in enumerate(widgets):
            if widget is None:
                continue
            self.content_splitter.insertWidget(index, widget)

    def show_status_message(self, message: str, timeout: int = 2000) -> None:
        """Wyświetla komunikat w labelu statusu."""
        if hasattr(self, 'status_label'):
            self.status_label.setText(message)
            # Timer do czyszczenia komunikatu po timeout
            QTimer.singleShot(timeout, lambda: self.status_label.setText(""))

    def update_layout_ui_state(self):
        """Aktualizuje zaznaczenie menu i opis przycisku układu"""
        if hasattr(self, "layout_actions"):
            for mode, action in self.layout_actions.items():
                action.setChecked(mode == self.layout_mode)

        if hasattr(self, "layout_button"):
            description = self.LAYOUT_DESCRIPTIONS.get(self.layout_mode, "")
            self.layout_button.setText(f"⬛⬜ Układ {self.layout_mode}")
            self.layout_button.setToolTip(
                f"Zmień układ paneli (obecnie: {description})"
            )
        
    def create_folder_tree(self):
        """Tworzy drzewo folderów z przyciskiem przełączania widoku"""
        container = QWidget()
        layout = QVBoxLayout()
        container.setLayout(layout)
        container.setMaximumWidth(300)
        
        # Wybór konta email
        account_layout = QHBoxLayout()
        account_layout.setContentsMargins(0, 0, 0, 4)
        
        account_label = QLabel("Konto:")
        account_label.setStyleSheet("font-weight: bold;")
        account_layout.addWidget(account_label)
        
        self.account_filter_combo = QComboBox()
        self.account_filter_combo.setMinimumWidth(140)
        self.account_filter_combo.currentIndexChanged.connect(self.on_account_filter_changed)
        account_layout.addWidget(self.account_filter_combo)
        
        # Przycisk odświeżania kont
        reload_accounts_btn = QPushButton("🔄")
        reload_accounts_btn.setToolTip("Odśwież listę kont z ustawień")
        reload_accounts_btn.setFixedWidth(30)
        reload_accounts_btn.clicked.connect(self.reload_accounts)
        reload_accounts_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 4px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
        """)
        account_layout.addWidget(reload_accounts_btn)
        
        layout.addLayout(account_layout)
        
        # Przyciski przełączania widoku
        view_buttons_layout = QHBoxLayout()
        view_buttons_layout.setSpacing(2)
        
        self.view_folders_btn = QPushButton("📁 Foldery")
        self.view_folders_btn.setCheckable(True)
        self.view_folders_btn.setChecked(True)
        self.view_folders_btn.clicked.connect(lambda: self.switch_view_mode("folders"))
        self.view_folders_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 8px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
            QPushButton:checked {
                background-color: #2196F3;
            }
        """)
        view_buttons_layout.addWidget(self.view_folders_btn)
        
        self.view_contacts_btn = QPushButton("👥 Kontakty")
        self.view_contacts_btn.setCheckable(True)
        self.view_contacts_btn.clicked.connect(lambda: self.switch_view_mode("contacts"))
        self.view_contacts_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 8px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
            QPushButton:checked {
                background-color: #4CAF50;
            }
        """)
        view_buttons_layout.addWidget(self.view_contacts_btn)
        
        self.view_threads_btn = QPushButton("💬 Wątki")
        self.view_threads_btn.setCheckable(True)
        self.view_threads_btn.clicked.connect(lambda: self.switch_view_mode("threads"))
        self.view_threads_btn.setStyleSheet("""
            QPushButton {
                background-color: #607D8B;
                color: white;
                font-weight: bold;
                border: none;
                padding: 6px 8px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #546E7A;
            }
            QPushButton:checked {
                background-color: #FF9800;
            }
        """)
        view_buttons_layout.addWidget(self.view_threads_btn)
        
        layout.addLayout(view_buttons_layout)
        
        # Drzewo folderów/kontaktów/wątków
        self.tree = FolderTreeWidget(self)
        self.tree.setHeaderLabel("Foldery")
        
        # Nagłówek folderów
        font = QFont()
        font.setBold(True)
        font.setPointSize(10)
        header_item = self.tree.headerItem()
        if header_item is not None:
            header_item.setFont(0, font)
        
        # Główne foldery
        self.populate_folders_tree()
        
        # Obsługa kliknięcia
        self.tree.itemClicked.connect(self.on_folder_clicked)
        self.tree.currentItemChanged.connect(self.on_tree_current_item_changed)
        
        layout.addWidget(self.tree)

        folder_buttons = QHBoxLayout()
        folder_buttons.setContentsMargins(0, 0, 0, 0)
        folder_buttons.setSpacing(4)

        self.btn_add_folder = QPushButton("➕")
        self.btn_add_folder.setToolTip("Dodaj nowy folder")
        self.btn_add_folder.setFixedSize(28, 28)
        self.btn_add_folder.clicked.connect(self.add_folder)
        folder_buttons.addWidget(self.btn_add_folder)

        self.btn_rename_folder = QPushButton("✏️")
        self.btn_rename_folder.setToolTip("Zmień nazwę folderu")
        self.btn_rename_folder.setFixedSize(28, 28)
        self.btn_rename_folder.clicked.connect(self.rename_folder)
        folder_buttons.addWidget(self.btn_rename_folder)

        self.btn_delete_folder = QPushButton("🗑️")
        self.btn_delete_folder.setToolTip("Usuń folder")
        self.btn_delete_folder.setFixedSize(28, 28)
        self.btn_delete_folder.clicked.connect(self.delete_folder)
        folder_buttons.addWidget(self.btn_delete_folder)

        folder_buttons.addStretch()
        layout.addLayout(folder_buttons)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Sekcja ulubionych plików (rozwijalna)
        self.favorites_section = self.create_favorites_section()
        layout.addWidget(self.favorites_section)
        
        self.folder_tree = self.tree
        self.update_folder_button_states()
        self.populate_account_filter()
        return container
    
    def create_mail_list(self):
        """Tworzy listę maili"""
        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)
        container.setLayout(layout)

        header_widget = QWidget()
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(8)
        header_widget.setLayout(header_layout)

        header_font = QFont()
        header_font.setBold(True)
        header_font.setPointSize(11)

        self.folder_label = QLabel("Odebrane")
        self.folder_label.setFont(header_font)
        header_layout.addWidget(self.folder_label)

        header_layout.addStretch()

        self.mail_search_input = QLineEdit()
        self.mail_search_input.setPlaceholderText("Filtruj po frazie...")
        self.mail_search_input.setClearButtonEnabled(True)
        self.mail_search_input.textChanged.connect(self.on_mail_filter_changed)
        header_layout.addWidget(self.mail_search_input)

        self.mail_tag_filter = QComboBox()
        self.mail_tag_filter.setMinimumWidth(150)
        self.mail_tag_filter.currentIndexChanged.connect(self.on_mail_filter_changed)
        header_layout.addWidget(self.mail_tag_filter)

        layout.addWidget(header_widget)
        
        # Druga linia nagłówka - kontrolki podglądu
        preview_header_widget = QWidget()
        preview_header_layout = QHBoxLayout()
        preview_header_layout.setContentsMargins(0, 0, 0, 0)
        preview_header_widget.setLayout(preview_header_layout)
        
        # Jeden przycisk przełączalny zamiast dwóch osobnych
        self.toggle_all_previews_btn = QPushButton("🔽 Rozwiń wszystkie")
        self.toggle_all_previews_btn.setCheckable(True)
        self.toggle_all_previews_btn.setChecked(False)
        self.toggle_all_previews_btn.setToolTip("Rozwiń/zwiń podgląd wszystkich maili")
        self.toggle_all_previews_btn.clicked.connect(self.toggle_all_previews)
        preview_header_layout.addWidget(self.toggle_all_previews_btn)
        
        preview_header_layout.addWidget(QLabel("Linie podglądu:"))
        
        self.mail_preview_lines_spinner = QSpinBox()
        self.mail_preview_lines_spinner.setMinimum(1)
        self.mail_preview_lines_spinner.setMaximum(10)
        self.mail_preview_lines_spinner.setValue(3)
        self.mail_preview_lines_spinner.setToolTip("Liczba linii treści wyświetlanych w podglądzie")
        self.mail_preview_lines_spinner.valueChanged.connect(self.on_preview_lines_changed)
        self.mail_preview_lines = 3  # Domyślna wartość
        preview_header_layout.addWidget(self.mail_preview_lines_spinner)
        
        preview_header_layout.addStretch()
        
        layout.addWidget(preview_header_widget)

        table = MailTableWidget(self)
        table.setColumnCount(12)  # Zmieniono na 12 kolumn (dodano 🪄)
        table.setHorizontalHeaderLabels([
            "⭐", "Adres mail", "Imię/Nazwisko", "Odpowiedz", "▶️", "Tytuł", 
            "Data", "Rozmiar", "Wątków", "Tag", "Notatka", "🪄"
        ])

        table_header = table.horizontalHeader()
        if table_header:
            table_header.setStretchLastSection(True)  # Ostatnia kolumna rozciąga się
            table_header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            # Ustaw tryb rozciągania dla kolumn
            table_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            # Kolumny o stałej szerokości (nie można zmieniać)
            table_header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)  # ⭐
            table_header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)  # Odpowiedz
            table_header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)  # ▶️
            table_header.setSectionResizeMode(11, QHeaderView.ResizeMode.Fixed)  # 🪄
            # Kolumny Adres (1), Imię/Nazwisko (2), Tytuł (5) - użytkownik może regulować szerokość
            table_header.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)  # Adres - można zmieniać
            table_header.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)  # Imię/Nazwisko - można zmieniać
            table_header.setSectionResizeMode(5, QHeaderView.ResizeMode.Interactive)  # Tytuł - można zmieniać
            
            # Podłącz sygnał do zapisywania szerokości kolumn
            table_header.sectionResized.connect(self.on_column_resized)
            
            # Podłącz sygnał do zapisywania kolejności kolumn
            table_header.sectionMoved.connect(self.on_column_moved)

        # Zastosuj szerokości kolumn (domyślne lub załadowane z pliku)
        for index, width in self.column_widths.items():
            table.setColumnWidth(index, width)
        
        # Zastosuj kolejność kolumn (domyślne lub załadowane z pliku)
        for visual_idx, logical_idx in enumerate(self.column_order):
            table_header.moveSection(table_header.visualIndex(logical_idx), visual_idx)

        vertical_header = table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

        table.cellClicked.connect(self.on_mail_clicked)
        table.cellDoubleClicked.connect(self.on_mail_cell_double_clicked)
        table.itemChanged.connect(self.on_mail_item_changed)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_mail_context_menu)

        layout.addWidget(table)

        self.mail_list = table
        self.refresh_tag_filter_options(initial=True)
        self.set_mail_filter_controls_enabled(True)
        
        # Zastosuj ustawienia widoczności kolumn
        self.apply_column_visibility()

        return container

    def populate_folders_tree(self):
        """Wypełnia drzewo widoku folderów."""
        if not hasattr(self, "tree"):
            return

        # Batch updates - wyłącz odświeżanie podczas budowania drzewa
        self.tree.setUpdatesEnabled(False)

        # Zapisz obecny stan rozwinięcia sekcji przed czyszczeniem
        if self.tree.topLevelItemCount() > 0:
            for i in range(self.tree.topLevelItemCount()):
                item = self.tree.topLevelItem(i)
                if item:
                    item_data = item.data(0, Qt.ItemDataRole.UserRole)
                    if item_data and item_data.get("type") == "section":
                        section_name = item_data.get("name")
                        self.tree_expansion_state[section_name] = item.isExpanded()

        self.tree.clear()
        icon_map = {
            "Ulubione": "⭐",
            "Odebrane": "📥",
            "Wysłane": "📤",
            "Szkice": "📝",
            "Spam": "🚫",
            "Kosz": "🗑️",
        }
        
        # Inteligentne foldery
        smart_folder_icon_map = {
            "Nieodczytane": "📬",
            "Z załącznikami": "📎",
            "Ostatnie 7 dni": "📅",
            "Oznaczone gwiazdką": "⭐",
            "Duże wiadomości": "📦",
        }
        
        # Sekcja: Inteligentne foldery
        smart_section = QTreeWidgetItem(["🔥 INTELIGENTNE FOLDERY"])
        smart_section.setData(0, Qt.ItemDataRole.UserRole, {"type": "section", "name": "smart"})
        smart_section.setExpanded(self.tree_expansion_state.get("smart", True))
        font = smart_section.font(0)
        font.setBold(True)
        smart_section.setFont(0, font)
        self.tree.addTopLevelItem(smart_section)
        
        # Dodaj predefiniowane inteligentne foldery
        for smart_name, smart_icon in smart_folder_icon_map.items():
            mails = self.get_smart_folder_mails(smart_name)
            item_text = f"{smart_icon} {smart_name} ({len(mails)})"
            item = QTreeWidgetItem([item_text])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "smart_folder", "name": smart_name})
            smart_section.addChild(item)
        
        # Sekcja: Zwykłe foldery
        folders_section = QTreeWidgetItem(["📁 FOLDERY"])
        folders_section.setData(0, Qt.ItemDataRole.UserRole, {"type": "section", "name": "folders"})
        folders_section.setExpanded(self.tree_expansion_state.get("folders", True))
        font = folders_section.font(0)
        font.setBold(True)
        folders_section.setFont(0, font)
        self.tree.addTopLevelItem(folders_section)

        ordered_folders = ["Ulubione", "Odebrane", "Wysłane", "Szkice", "Spam", "Kosz"]
        remaining = [name for name in self.sample_mails.keys() if name not in ordered_folders]
        for folder_name in ordered_folders + remaining:
            if folder_name == "Ulubione":
                mails = self.get_starred_mails()
            else:
                mails = self.sample_mails.get(folder_name, [])
            icon = icon_map.get(folder_name, "📁")
            item_text = f"{icon} {folder_name} ({len(mails)})"
            item = QTreeWidgetItem([item_text])
            item.setData(0, Qt.ItemDataRole.UserRole, {"type": "folder", "name": folder_name})
            folders_section.addChild(item)
        
        # Dodaj foldery IMAP jeśli są dostępne
        if hasattr(self, 'imap_folders') and self.imap_folders:
            for account_email, imap_folder_list in self.imap_folders.items():
                for imap_folder in imap_folder_list:
                    # Pomiń INBOX (już mamy jako "Odebrane")
                    if imap_folder == "INBOX":
                        continue
                    # Pomiń foldery które już mamy
                    if imap_folder in ordered_folders:
                        continue
                    
                    # Dodaj folder IMAP do drzewa
                    mails = self.sample_mails.get(imap_folder, [])
                    item_text = f"📁 {imap_folder} ({len(mails)})"
                    item = QTreeWidgetItem([item_text])
                    item.setData(0, Qt.ItemDataRole.UserRole, {
                        "type": "imap_folder", 
                        "name": imap_folder,
                        "account": account_email
                    })
                    folders_section.addChild(item)

        self.tree.setUpdatesEnabled(True)  # Włącz odświeżanie po zakończeniu
        
        # Automatyczne rozwijanie sekcji "FOLDERY" i zaznaczanie "Odebrane"
        folders_section.setExpanded(True)
        for i in range(folders_section.childCount()):
            child = folders_section.child(i)
            data = child.data(0, Qt.ItemDataRole.UserRole)
            if data and data.get("name") == "Odebrane":
                self.tree.setCurrentItem(child)
                # Wywołaj też metodę kliknięcia, aby wyświetlić zawartość
                self.on_folder_clicked(child, 0)
                break
        
        self.update_folder_button_states()

    def get_starred_mails(self) -> List[Dict[str, Any]]:
        """Zwraca listę wszystkich oznaczonych gwiazdką wiadomości."""
        starred: List[Dict[str, Any]] = []
        for folder_name, mails in self.sample_mails.items():
            if folder_name in {"Ulubione", "Kosz"}:
                continue
            for mail in mails:
                if mail.get("starred"):
                    starred.append(mail)
        return starred
    
    def get_smart_folder_mails(self, smart_folder_name: str) -> List[Dict[str, Any]]:
        """Zwraca maile dla danego inteligentnego folderu"""
        from datetime import datetime, timedelta
        
        all_mails = []
        for folder_name, mails in self.sample_mails.items():
            if folder_name == "Kosz":  # Pomiń kosz
                continue
            all_mails.extend(mails)
        
        if smart_folder_name == "Nieodczytane":
            # Maile bez flagi przeczytania lub jawnie nieprzeczytane
            return [m for m in all_mails if not m.get("read", False)]
        
        elif smart_folder_name == "Z załącznikami":
            # Maile z załącznikami
            return [m for m in all_mails if m.get("attachments")]
        
        elif smart_folder_name == "Ostatnie 7 dni":
            # Maile z ostatnich 7 dni
            cutoff = datetime.now() - timedelta(days=7)
            filtered = []
            for m in all_mails:
                date_str = m.get("date", "")
                try:
                    # Parsuj datę (format może się różnić)
                    if date_str:
                        # Przykładowy format: "2024-01-15 10:30"
                        mail_date = datetime.strptime(date_str[:16], "%Y-%m-%d %H:%M")
                        if mail_date >= cutoff:
                            filtered.append(m)
                except:
                    pass
            return filtered
        
        elif smart_folder_name == "Oznaczone gwiazdką":
            # To samo co Ulubione
            return self.get_starred_mails()
        
        elif smart_folder_name == "Duże wiadomości":
            # Maile większe niż 1MB
            filtered = []
            for m in all_mails:
                size_str = m.get("size", "")
                try:
                    # Parsuj rozmiar (np. "1.5 MB", "500 KB")
                    if "MB" in size_str:
                        size_mb = float(size_str.replace("MB", "").strip())
                        if size_mb >= 1.0:
                            filtered.append(m)
                except:
                    pass
            return filtered
        
        return []

    def update_favorites_folder_item(self) -> None:
        """Aktualizuje licznik w folderze Ulubione."""
        if getattr(self, "view_mode", "folders") != "folders":
            return
        if not hasattr(self, "tree"):
            return
        item = self.find_folder_item("Ulubione")
        if not isinstance(item, QTreeWidgetItem):
            return
        count = len(self.get_starred_mails())
        item.setText(0, f"⭐ Ulubione ({count})")

    def handle_mail_drop(self, mail_uid: str, target_folder: str) -> bool:
        """Przenosi wiadomość do wskazanego folderu."""
        mail = self.mail_uid_map.get(mail_uid)
        target_folder = target_folder.strip()
        if mail is None or not target_folder:
            return False

        if target_folder == "Ulubione":
            self.show_status_message("Folder 'Ulubione' tworzony jest automatycznie na podstawie gwiazdek.", 2500)
            return False

        source_folder = mail.get("_folder")
        if source_folder == target_folder:
            self.show_status_message("Wiadomość już znajduje się w tym folderze.", 2000)
            return False

        if target_folder not in self.sample_mails:
            self.sample_mails[target_folder] = []

        if source_folder and source_folder in self.sample_mails:
            try:
                self.sample_mails[source_folder].remove(mail)
            except ValueError:
                pass

        mail["_folder"] = target_folder
        if mail not in self.sample_mails[target_folder]:
            self.sample_mails[target_folder].append(mail)

        previous_folder = getattr(self, "current_folder", None)
        self.populate_folders_tree()

        if previous_folder and self.find_folder_item(previous_folder):
            self.select_folder_by_name(previous_folder)
        else:
            self.select_folder_by_name(target_folder)

        if self.current_mail is mail and self.current_folder != target_folder:
            self.clear_mail_view()

        self.show_status_message(
            f"Przeniesiono wiadomość do folderu '{target_folder}'.",
            2500,
        )
        return True

    def handle_favorite_drop(self, file_paths: List[str], group_name: Optional[str]) -> bool:
        """Dodaje pliki przeciągnięte do sekcji ulubionych."""
        if not file_paths:
            return False

        target_group = (group_name or "Bez grupy").strip() or "Bez grupy"
        added_files: List[str] = []
        skipped_missing: List[str] = []
        skipped_existing: List[str] = []

        for raw_path in file_paths:
            if not raw_path:
                continue

            normalized_path = os.path.normcase(os.path.abspath(raw_path))
            if not os.path.exists(raw_path):
                skipped_missing.append(raw_path)
                continue

            duplicate = False
            for favorite in self.favorite_files:
                existing_path = favorite.get("path")
                if not existing_path:
                    continue
                existing_normalized = os.path.normcase(os.path.abspath(existing_path))
                if existing_normalized == normalized_path:
                    duplicate = True
                    break

            if duplicate:
                skipped_existing.append(raw_path)
                continue

            path_obj = Path(raw_path)
            favorite_entry = {
                "name": path_obj.name,
                "path": str(path_obj),
                "group": target_group,
                "tags": [],
                "added_at": datetime.utcnow().isoformat(),
                "last_used_at": datetime.utcnow().isoformat(),
            }

            self.favorite_files.append(favorite_entry)
            added_files.append(path_obj.name)

        if not added_files:
            if skipped_existing and not skipped_missing:
                self.show_status_message("Wszystkie pliki już znajdują się w ulubionych.", 2500)
            elif skipped_missing and not skipped_existing:
                self.show_status_message("Nie znaleziono wskazanych plików.", 2500)
            elif skipped_existing or skipped_missing:
                self.show_status_message("Żaden z plików nie został dodany do ulubionych.", 2500)
            return False

        self.save_favorite_files()
        self.populate_favorites_tree()

        if skipped_existing or skipped_missing:
            details = []
            if skipped_existing:
                details.append(f"pominięto {len(skipped_existing)} (już na liście)")
            if skipped_missing:
                details.append(f"nie znaleziono {len(skipped_missing)}")
            detail_msg = ", ".join(details)
            self.show_status_message(f"Dodano {len(added_files)} pliki, {detail_msg}.", 3000)
        else:
            if target_group == "Bez grupy":
                self.show_status_message(f"Dodano {len(added_files)} pliki do ulubionych.", 2500)
            else:
                self.show_status_message(
                    f"Dodano {len(added_files)} pliki do grupy '{target_group}'.",
                    2500,
                )

        return True

    def populate_contacts_tree(self):
        """Buduje drzewo kontaktów pogrupowane według tagów."""
        if not hasattr(self, "tree"):
            return

        # Batch updates - wyłącz odświeżanie podczas budowania drzewa
        self.tree.setUpdatesEnabled(False)
        self.tree.clear()
        
        # Zbierz wszystkie kontakty
        contacts_data = {}  # email -> {name, subjects, mails}
        for mails in self.sample_mails.values():
            for mail in mails:
                sender_full = mail.get("from", "Nieznany nadawca")
                email = self.extract_email_address(sender_full)
                name = self.extract_display_name(sender_full) or email
                subject = mail.get("subject", "(brak tematu)")
                
                if email not in contacts_data:
                    contacts_data[email] = {
                        "name": name,
                        "email": email,
                        "subjects": defaultdict(list)
                    }
                contacts_data[email]["subjects"][subject].append(mail)
        
        # Grupuj według tagów
        tagged_contacts = defaultdict(list)  # tag_name -> list of emails
        untagged_contacts = []
        
        for email, data in contacts_data.items():
            if email in self.contact_tags and self.contact_tags[email]:
                # Dodaj do wszystkich tagów tego kontaktu
                for tag in self.contact_tags[email]:
                    tagged_contacts[tag].append(email)
            else:
                untagged_contacts.append(email)
        
        # Najpierw dodaj pogrupowane po tagach
        for tag_def in self.contact_tag_definitions:
            tag_name = tag_def["name"]
            if tag_name not in tagged_contacts:
                continue
                
            tag_color = QColor(tag_def.get("color", "#E0E0E0"))
            
            # Sekcja tagu
            tag_section = QTreeWidgetItem([f"🏷️ {tag_name} ({len(tagged_contacts[tag_name])})"])
            tag_section.setBackground(0, tag_color)
            if tag_color.lightness() < 128:
                tag_section.setForeground(0, QColor("white"))
            font = tag_section.font(0)
            font.setBold(True)
            tag_section.setFont(0, font)
            
            # Dodaj kontakty z tym tagiem
            for email in sorted(tagged_contacts[tag_name]):
                data = contacts_data[email]
                display_name = f"{data['name']} <{email}>" if data['name'] != email else email
                contact_item = QTreeWidgetItem([f"👤 {display_name}"])
                
                # Zastosuj kolor kontaktu jeśli ustawiony
                if email in self.contact_colors:
                    contact_item.setForeground(0, self.contact_colors[email])
                
                # Dodaj konwersacje
                for subject, mails in sorted(data["subjects"].items(), key=lambda item: item[0].lower()):
                    subject_item = QTreeWidgetItem([f"💬 {subject} ({len(mails)})"])
                    for mail in sorted(mails, key=lambda m: m.get("date", ""), reverse=True):
                        mail_item = QTreeWidgetItem([f"📧 {mail.get('date', '')}"])
                        mail_item.setData(0, Qt.ItemDataRole.UserRole, mail)
                        subject_item.addChild(mail_item)
                    contact_item.addChild(subject_item)
                
                tag_section.addChild(contact_item)
            
            self.tree.addTopLevelItem(tag_section)
        
        # Sekcja bez tagów
        if untagged_contacts:
            untagged_section = QTreeWidgetItem([f"� Bez tagów ({len(untagged_contacts)})"])
            font = untagged_section.font(0)
            font.setBold(True)
            untagged_section.setFont(0, font)
            untagged_section.setForeground(0, QColor("#757575"))
            
            for email in sorted(untagged_contacts):
                data = contacts_data[email]
                display_name = f"{data['name']} <{email}>" if data['name'] != email else email
                contact_item = QTreeWidgetItem([f"👤 {display_name}"])
                
                # Zastosuj kolor kontaktu jeśli ustawiony
                if email in self.contact_colors:
                    contact_item.setForeground(0, self.contact_colors[email])
                
                # Dodaj konwersacje
                for subject, mails in sorted(data["subjects"].items(), key=lambda item: item[0].lower()):
                    subject_item = QTreeWidgetItem([f"💬 {subject} ({len(mails)})"])
                    for mail in sorted(mails, key=lambda m: m.get("date", ""), reverse=True):
                        mail_item = QTreeWidgetItem([f"📧 {mail.get('date', '')}"])
                        mail_item.setData(0, Qt.ItemDataRole.UserRole, mail)
                        subject_item.addChild(mail_item)
                    contact_item.addChild(subject_item)
                
                untagged_section.addChild(contact_item)
            
            self.tree.addTopLevelItem(untagged_section)

        self.tree.setUpdatesEnabled(True)  # Włącz odświeżanie po zakończeniu
        self.update_folder_button_states()
    
    def switch_view_mode(self, mode: str):
        """Przełącza między widokami: folders, contacts, threads"""
        # Odznacz wszystkie przyciski
        self.view_folders_btn.setChecked(False)
        self.view_contacts_btn.setChecked(False)
        self.view_threads_btn.setChecked(False)
        
        # Zaznacz odpowiedni przycisk
        if mode == "folders":
            self.view_folders_btn.setChecked(True)
            self.view_mode = "folders"
            self.tree.setHeaderLabel("Foldery")
            self.populate_folders_tree()
        elif mode == "contacts":
            self.view_contacts_btn.setChecked(True)
            self.view_mode = "contacts"
            self.tree.setHeaderLabel("Kontakty")
            self.populate_contacts_tree()
        elif mode == "threads":
            self.view_threads_btn.setChecked(True)
            self.view_mode = "threads"
            self.tree.setHeaderLabel("Wątki konwersacji")
            self.populate_threads_tree()
        
        self.update_folder_button_states()
    
    def toggle_queue_view(self):
        """Przełącza między tradycyjnym układem a widokiem kolejki"""
        if self.toggle_queue_btn.isChecked():
            # Przełącz na widok kolejki
            self.toggle_queue_btn.setText("📁 Tradycyjny układ")
            
            # Ukryj tradycyjne sekcje
            self.folder_tree_container.hide()
            self.content_splitter.hide()
            
            # Pokaż widok kolejki
            self.queue_view.show()
            self.queue_view.refresh()
        else:
            # Przełącz na tradycyjny układ
            self.toggle_queue_btn.setText("📋 Pokaż kolejkę")
            
            # Ukryj widok kolejki
            self.queue_view.hide()
            
            # Pokaż tradycyjne sekcje
            self.folder_tree_container.show()
            self.content_splitter.show()
    
    def populate_threads_tree(self):
        """Buduje drzewo wątków konwersacji w porządku chronologicznym"""
        if not hasattr(self, "tree"):
            return

        self.tree.clear()
        
        # Zbierz wszystkie konwersacje (według tematu)
        conversations = defaultdict(list)  # normalized_subject -> list of mails
        
        for folder_mails in self.sample_mails.values():
            for mail in folder_mails:
                # Normalizuj temat (usuń Re:, Fwd: itp.)
                subject = self.normalize_subject(mail.get("subject", ""))
                if not subject:
                    subject = "(brak tematu)"
                conversations[subject].append(mail)
        
        # Posortuj konwersacje według daty najnowszego maila
        sorted_conversations = []
        for subject, mails in conversations.items():
            # Sortuj maile w konwersacji chronologicznie
            sorted_mails = sorted(mails, key=lambda m: m.get("date", ""), reverse=True)
            latest_date = sorted_mails[0].get("date", "") if sorted_mails else ""
            sorted_conversations.append((subject, sorted_mails, latest_date))
        
        # Sortuj konwersacje według najnowszej daty
        sorted_conversations.sort(key=lambda x: x[2], reverse=True)
        
        # Buduj drzewo
        for subject, mails, _ in sorted_conversations:
            # Nagłówek konwersacji
            thread_count = len(mails)
            
            # Pobierz uczestników konwersacji
            participants = set()
            for mail in mails:
                email = self.extract_email_address(mail.get("from", ""))
                if email:
                    participants.add(email)
            
            # Wyświetl oryginalny temat (z pierwszego maila)
            original_subject = mails[-1].get("subject", subject) if mails else subject
            
            thread_item = QTreeWidgetItem([f"💬 {original_subject} ({thread_count})"])
            thread_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "thread", "subject": subject})
            
            # Wyróżnij wątki z wieloma mailami
            if thread_count > 1:
                font = thread_item.font(0)
                font.setBold(True)
                thread_item.setFont(0, font)
                thread_item.setForeground(0, QColor("#1976D2"))
            
            # Tooltip z uczestnikami
            if participants:
                participants_str = ", ".join(sorted(participants)[:5])
                if len(participants) > 5:
                    participants_str += f" (+{len(participants) - 5} innych)"
                thread_item.setToolTip(0, f"Uczestnicy: {participants_str}")
            
            # Dodaj maile w kolejności chronologicznej (od najstarszego)
            for i, mail in enumerate(reversed(mails)):
                from_full = mail.get("from", "Nieznany")
                email = self.extract_email_address(from_full)
                name = self.extract_display_name(from_full) or email
                date = mail.get("date", "")
                
                # Ikona zależna od pozycji w wątku
                if i == 0:
                    icon = "📩"  # Pierwszy mail w wątku
                elif i == len(mails) - 1:
                    icon = "📬"  # Ostatni mail w wątku
                else:
                    icon = "📧"  # Mail pośredni
                
                mail_text = f"{icon} {name} - {date}"
                mail_item = QTreeWidgetItem([mail_text])
                mail_item.setData(0, Qt.ItemDataRole.UserRole, mail)
                
                # Zastosuj kolor kontaktu jeśli ustawiony
                if email in self.contact_colors:
                    mail_item.setForeground(0, self.contact_colors[email])
                
                # Tooltip z podglądem treści
                body_preview = mail.get("body", "")[:100]
                if len(mail.get("body", "")) > 100:
                    body_preview += "..."
                mail_item.setToolTip(0, f"{mail.get('subject', '')}\n\n{body_preview}")
                
                thread_item.addChild(mail_item)
            
            self.tree.addTopLevelItem(thread_item)
        
        self.update_folder_button_states()
    
    def toggle_view_mode(self, checked):
        """Przełącza między widokiem folderów a kontaktów (stara funkcja - dla kompatybilności)"""
        if checked:
            self.switch_view_mode("contacts")
        else:
            self.switch_view_mode("folders")

    def on_tree_current_item_changed(self, *_items):
        """Aktualizuje dostępność przycisków po zmianie zaznaczenia"""
        self.update_folder_button_states()

    def update_folder_button_states(self):
        """Włącza lub wyłącza przyciski folderów zależnie od widoku i wyboru"""
        buttons = getattr(self, "btn_add_folder", None), getattr(self, "btn_rename_folder", None), getattr(self, "btn_delete_folder", None)
        if not all(buttons):
            return

        is_folder_view = self.view_mode == "folders"
        self.btn_add_folder.setEnabled(is_folder_view)

        selected_item = self.tree.currentItem() if is_folder_view and hasattr(self, "tree") else None
        allow_edit = False
        if isinstance(selected_item, QTreeWidgetItem):
            data = selected_item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and data.get("type") == "folder":
                folder_name = data.get("name")
                allow_edit = folder_name not in self.protected_folders

        self.btn_rename_folder.setEnabled(is_folder_view and allow_edit)
        self.btn_delete_folder.setEnabled(is_folder_view and allow_edit)

    def find_folder_item(self, folder_name: str) -> Optional[QTreeWidgetItem]:
        """Wyszukuje element odpowiadający nazwie folderu"""
        if not hasattr(self, "tree"):
            return None
        for index in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(index)
            if not isinstance(item, QTreeWidgetItem):
                continue
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict) and data.get("type") == "folder" and data.get("name") == folder_name:
                return item
        return None

    def select_folder_by_name(self, folder_name: str) -> None:
        """Zaznacza i ładuje wskazany folder"""
        item = self.find_folder_item(folder_name)
        if item is None:
            return
        self.tree.setCurrentItem(item)
        self.tree.scrollToItem(item)
        self.load_folder_mails(item.text(0))

    def add_folder(self):
        """Dodaje nowy folder do listy"""
        if self.view_mode != "folders":
            QMessageBox.information(self, "Widok kontaktów", "Dodawanie folderów dostępne jest tylko w widoku folderów.")
            return

        name, ok = QInputDialog.getText(self, "Nowy folder", "Podaj nazwę folderu:")
        if not ok:
            return

        name = name.strip()
        if not name:
            QMessageBox.warning(self, "Błąd", "Nazwa folderu nie może być pusta.")
            return

        if name in self.sample_mails:
            QMessageBox.warning(self, "Błąd", "Folder o takiej nazwie już istnieje.")
            return

        self.sample_mails[name] = []
        self.populate_folders_tree()
        self.select_folder_by_name(name)
        self.show_status_message(f"Dodano folder '{name}'.", 2500)

    def rename_folder(self):
        """Zmienia nazwę wybranego folderu"""
        if self.view_mode != "folders":
            return

        current_item = self.tree.currentItem()
        if not isinstance(current_item, QTreeWidgetItem):
            QMessageBox.information(self, "Wybierz folder", "Najpierw zaznacz folder do zmiany nazwy.")
            return
        item: QTreeWidgetItem = current_item

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict) or data.get("type") != "folder":
            QMessageBox.information(self, "Nieobsługiwany element", "Zmień widok na foldery, aby edytować folder.")
            return

        old_name = data.get("name", "")
        if old_name in self.protected_folders:
            QMessageBox.information(self, "Folder chroniony", "Tego folderu nie można zmienić.")
            return

        new_name, ok = QInputDialog.getText(self, "Zmień nazwę", "Wpisz nową nazwę:", text=old_name)
        if not ok:
            return

        new_name = new_name.strip()
        if not new_name:
            QMessageBox.warning(self, "Błąd", "Nazwa folderu nie może być pusta.")
            return

        if new_name == old_name:
            return

        if new_name in self.sample_mails:
            QMessageBox.warning(self, "Błąd", "Folder o takiej nazwie już istnieje.")
            return

        self.sample_mails[new_name] = self.sample_mails.pop(old_name)
        if getattr(self, "current_folder", None) == old_name:
            self.current_folder = new_name

        self.populate_folders_tree()
        self.select_folder_by_name(new_name)
        self.show_status_message(f"Zmieniono nazwę folderu na '{new_name}'.", 2500)

    def delete_folder(self):
        """Usuwa wybrany folder"""
        if self.view_mode != "folders":
            return

        current_item = self.tree.currentItem()
        if not isinstance(current_item, QTreeWidgetItem):
            QMessageBox.information(self, "Wybierz folder", "Najpierw zaznacz folder do usunięcia.")
            return
        item: QTreeWidgetItem = current_item

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict) or data.get("type") != "folder":
            QMessageBox.information(self, "Nieobsługiwany element", "Zmień widok na foldery, aby usunąć folder.")
            return

        folder_name = data.get("name", "")
        if folder_name in self.protected_folders:
            QMessageBox.information(self, "Folder chroniony", "Tego folderu nie można usunąć.")
            return

        reply = QMessageBox.question(
            self,
            "Usuń folder",
            f"Czy na pewno chcesz usunąć folder '{folder_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply != QMessageBox.StandardButton.Yes:
            return

        self.sample_mails.pop(folder_name, None)
        remove_current = getattr(self, "current_folder", None) == folder_name

        self.populate_folders_tree()

        if remove_current:
            self.current_folder = None

        if self.current_folder and self.find_folder_item(self.current_folder):
            self.select_folder_by_name(self.current_folder)
        elif self.tree.topLevelItemCount() > 0:
            first_item = self.tree.topLevelItem(0)
            if first_item is not None:
                self.current_folder = None
                self.tree.setCurrentItem(first_item)
                self.load_folder_mails(first_item.text(0))
        else:
            self.current_folder = None
            self.current_folder_mails = []
            self.displayed_mails = []
            if hasattr(self, "mail_list"):
                self.mail_list.setRowCount(0)
            self.clear_mail_view()

        self.update_folder_button_states()

        self.show_status_message(f"Usunięto folder '{folder_name}'.", 2500)
    
    def toggle_attachments_section(self):
        """Przełącza widoczność sekcji załączników"""
        is_expanded = self.attachments_toggle_btn.isChecked()
        if is_expanded:
            self.attachments_toggle_btn.setText("🔽 Załączniki")
            self.attachments_container.show()
        else:
            self.attachments_toggle_btn.setText("▶️ Załączniki")
            self.attachments_container.hide()
    
    def create_favorites_section(self):
        """Tworzy rozwijaną sekcję ulubionych plików"""
        section = QWidget()
        section_layout = QVBoxLayout()
        section_layout.setContentsMargins(0, 0, 0, 0)
        section_layout.setSpacing(1)
        section.setLayout(section_layout)
        
        # Przycisk rozwijania/zwijania
        self.favorites_toggle = QPushButton("⭐ Ulubione pliki ▼")
        self.favorites_toggle.setCheckable(True)
        self.favorites_toggle.clicked.connect(self.toggle_favorites)
        self.favorites_toggle.setStyleSheet("""
            QPushButton {
                background-color: #FFA726;
                color: white;
                font-weight: bold;
                border: none;
                padding: 4px;
                text-align: left;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #FB8C00;
            }
        """)
        section_layout.addWidget(self.favorites_toggle)
        
        # Obszar z ulubionymi plikami (początkowo ukryty)
        self.favorites_content = QWidget()
        favorites_layout = QVBoxLayout()
        favorites_layout.setContentsMargins(0, 0, 0, 0)
        favorites_layout.setSpacing(1)
        self.favorites_content.setLayout(favorites_layout)
        self.favorites_content.setVisible(False)

        # Przyciski akcji
        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(1)

        btn_add = QPushButton("➕")
        btn_add.setToolTip("Dodaj plik")
        btn_add.setFixedSize(26, 26)
        btn_add.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
        btn_add.clicked.connect(self.add_favorite_file)
        btn_layout.addWidget(btn_add)

        btn_add_from_mail = QPushButton("📧")
        btn_add_from_mail.setToolTip("Opcja będzie dostępna po wdrożeniu obsługi załączników")
        btn_add_from_mail.setFixedSize(26, 26)
        btn_add_from_mail.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
        btn_add_from_mail.setEnabled(False)
        btn_add_from_mail.setVisible(False)
        btn_layout.addWidget(btn_add_from_mail)

        btn_manage_groups = QPushButton("⚙️")
        btn_manage_groups.setToolTip("Zarządzaj grupami")
        btn_manage_groups.setFixedSize(26, 26)
        btn_manage_groups.setStyleSheet("QPushButton { padding: 0px; margin: 0px; }")
        btn_manage_groups.clicked.connect(self.manage_file_groups)
        btn_layout.addWidget(btn_manage_groups)

        btn_layout.addStretch()
        favorites_layout.addLayout(btn_layout)
        
        # Zakładki z ulubionymi
        self.favorites_tabs = QTabWidget()
        self.favorites_tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.favorites_tabs.setElideMode(Qt.TextElideMode.ElideRight)
        favorites_layout.addWidget(self.favorites_tabs)

        # Zakładka grup
        groups_tab = QWidget()
        groups_layout = QVBoxLayout()
        groups_layout.setContentsMargins(0, 0, 0, 0)
        groups_layout.setSpacing(1)

        self.favorites_tree = FavoritesTreeWidget(self)
        self.favorites_tree.setHeaderLabels(["Plik", "Grupa/Tag"])
        self.favorites_tree.setColumnWidth(0, 180)
        self.favorites_tree.setMaximumHeight(400)
        self.favorites_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.favorites_tree.customContextMenuRequested.connect(self.show_favorites_context_menu)
        self.favorites_tree.itemDoubleClicked.connect(self.open_favorite_file)
        self.favorites_tree.itemClicked.connect(self.on_favorite_item_clicked)
        groups_layout.addWidget(self.favorites_tree)

        groups_tab.setLayout(groups_layout)
        self.favorites_tabs.addTab(groups_tab, "Grupy")

        # Zakładka ostatnio używane
        recent_tab = QWidget()
        recent_layout = QVBoxLayout()
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(1)

        self.recent_favorites_list = RecentFavoritesListWidget(self)
        self.recent_favorites_list.setMaximumHeight(400)
        self.recent_favorites_list.itemDoubleClicked.connect(self.on_recent_favorite_double_clicked)
        recent_layout.addWidget(self.recent_favorites_list)

        recent_tab.setLayout(recent_layout)
        self.favorites_tabs.addTab(recent_tab, "Ostatnie")
        
        section_layout.addWidget(self.favorites_content)
        
        # Załaduj ulubione pliki
        self.populate_favorites_tree()
        
        return section
    
    def toggle_favorites(self, checked):
        """Przełącza widoczność sekcji ulubionych"""
        self.favorites_content.setVisible(checked)
        if checked:
            self.favorites_toggle.setText("⭐ Ulubione pliki ▲")
        else:
            self.favorites_toggle.setText("⭐ Ulubione pliki ▼")
    
    def load_favorite_files(self):
        """Wczytuje ulubione pliki z JSON"""
        favorites_file = Path("mail_client/favorite_files.json")
        if favorites_file.exists():
            try:
                with open(favorites_file, 'r', encoding='utf-8') as f:
                    raw_data = json.load(f)
                    if not isinstance(raw_data, list):
                        return []

                    normalized: List[Dict[str, Any]] = []
                    for entry in raw_data:
                        if isinstance(entry, dict):
                            normalized_entry = self._normalize_favorite_entry(entry)
                            if normalized_entry is not None:
                                normalized.append(normalized_entry)

                    return normalized
            except Exception:
                return []
        return []

    def _normalize_favorite_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalizuje wpis ulubionego pliku do spójnego formatu."""
        path_value = entry.get("path")
        if not path_value:
            return None

        path = str(Path(path_value))
        name = entry.get("name") or Path(path).name
        group = entry.get("group") or "Bez grupy"

        tags_raw = entry.get("tags")
        if isinstance(tags_raw, list):
            tags = [str(tag).strip() for tag in tags_raw if str(tag).strip()]
        else:
            tags = []

        added_at = entry.get("added_at") if isinstance(entry.get("added_at"), str) else None
        if added_at:
            try:
                datetime.fromisoformat(added_at)
            except ValueError:
                added_at = None
        if not added_at:
            added_at = "1970-01-01T00:00:00"

        last_used_at = entry.get("last_used_at") if isinstance(entry.get("last_used_at"), str) else None
        if last_used_at:
            try:
                datetime.fromisoformat(last_used_at)
            except ValueError:
                last_used_at = None
        if not last_used_at:
            last_used_at = added_at

        return {
            "name": name,
            "path": path,
            "group": group,
            "tags": tags,
            "added_at": added_at,
            "last_used_at": last_used_at,
        }
    
    def save_favorite_files(self):
        """Zapisuje ulubione pliki do JSON"""
        favorites_file = Path("mail_client/favorite_files.json")
        try:
            with open(favorites_file, 'w', encoding='utf-8') as f:
                json.dump(self.favorite_files, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można zapisać ulubionych: {e}")

    def load_mail_tags(self):
        """Wczytuje tagi maili z pliku"""
        if self.tags_file.exists():
            try:
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return [
            {"name": "Priorytet", "color": "#FF7043"},
            {"name": "Klient", "color": "#42A5F5"},
            {"name": "Finanse", "color": "#66BB6A"},
            {"name": "Newsletter", "color": "#AB47BC"},
        ]

    def save_mail_tags(self):
        """Zapisuje tagi maili do JSON"""
        try:
            self.tags_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(self.mail_tags, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można zapisać tagów: {e}")
    
    def load_contact_tag_definitions(self):
        """Wczytuje definicje tagów kontaktów z pliku"""
        contact_tags_file = Path("mail_client/contact_tags.json")
        if contact_tags_file.exists():
            try:
                with open(contact_tags_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    if isinstance(data, list):
                        return data
            except Exception:
                pass
        return [
            {"name": "VIP", "color": "#FFD700"},
            {"name": "Klient", "color": "#4CAF50"},
            {"name": "Dostawca", "color": "#2196F3"},
            {"name": "Rodzina", "color": "#E91E63"},
            {"name": "Znajomy", "color": "#9C27B0"},
        ]
    
    def save_contact_tag_definitions(self):
        """Zapisuje definicje tagów kontaktów do JSON"""
        try:
            contact_tags_file = Path("mail_client/contact_tags.json")
            contact_tags_file.parent.mkdir(parents=True, exist_ok=True)
            with open(contact_tags_file, 'w', encoding='utf-8') as f:
                json.dump(self.contact_tag_definitions, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można zapisać tagów kontaktów: {e}")
    
    def limit_mails_in_memory(self):
        """Limituje liczbę maili w pamięci aby zapobiec wyczerpaniu RAM"""
        total_mails = sum(len(mails) for mails in self.sample_mails.values())
        
        if total_mails <= self.MAX_TOTAL_MAILS:
            return  # W granicach limitu
        
        # Sortuj foldery według priorytetu (chronione ostatnie)
        folders_to_trim = []
        for folder, mails in self.sample_mails.items():
            priority = 0 if folder in self.protected_folders else 1
            folders_to_trim.append((priority, folder, mails))
        
        folders_to_trim.sort(key=lambda x: x[0])
        
        # Przytnij maile zachowując najnowsze
        mails_to_remove = total_mails - self.MAX_TOTAL_MAILS
        
        for priority, folder, mails in folders_to_trim:
            if mails_to_remove <= 0:
                break
            
            current_count = len(mails)
            if current_count > self.MAX_MAILS_PER_FOLDER:
                # Sortuj po dacie (najnowsze zostają)
                mails.sort(key=lambda m: m.get('date', ''), reverse=True)
                trim_count = min(mails_to_remove, current_count - self.MAX_MAILS_PER_FOLDER)
                # Usuń najstarsze
                del mails[-trim_count:]
                mails_to_remove -= trim_count
        
        print(f"Ograniczono maile w pamięci do {sum(len(m) for m in self.sample_mails.values())}")

    def load_contact_colors(self):
        """Wczytuje kolory kontaktów z pliku"""
        if self.contact_colors_file.exists():
            try:
                with open(self.contact_colors_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Walidacja: musi być słownikiem
                    if not isinstance(data, dict):
                        print(f"Nieprawidłowy format contact_colors.json - oczekiwano dict")
                        return {}
                    result = {}
                    for email, color_str in data.items():
                        # Walidacja typów
                        if isinstance(email, str) and isinstance(color_str, str):
                            color = QColor(color_str)
                            if color.isValid():
                                result[email] = color
                            else:
                                print(f"Nieprawidłowy kolor dla {email}: {color_str}")
                    return result
            except (json.JSONDecodeError, IOError, ValueError) as e:
                print(f"Błąd wczytywania kolorów kontaktów: {e}")
                return {}
        return {}
    
    def save_contact_colors(self):
        """Zapisuje kolory kontaktów do pliku"""
        try:
            self.contact_colors_file.parent.mkdir(parents=True, exist_ok=True)
            data = {}
            for email, color in self.contact_colors.items():
                if isinstance(color, QColor):
                    data[email] = color.name()
            with open(self.contact_colors_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można zapisać kolorów kontaktów: {e}")
    
    def load_contact_tag_assignments(self):
        """Wczytuje przypisania tagów do kontaktów z pliku"""
        if self.contact_tag_assignments_file.exists():
            try:
                with open(self.contact_tag_assignments_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Walidacja: musi być słownikiem
                    if not isinstance(data, dict):
                        print(f"Nieprawidłowy format contact_tag_assignments.json")
                        return {}
                    # Walidacja struktury: email -> lista stringów
                    result = {}
                    for email, tags in data.items():
                        if isinstance(email, str) and isinstance(tags, list):
                            # Filtruj tylko stringi w tagach
                            result[email] = [t for t in tags if isinstance(t, str)]
                    return result
            except (json.JSONDecodeError, IOError) as e:
                print(f"Błąd wczytywania tagów kontaktów: {e}")
                return {}
        return {}
    
    def save_contact_tag_assignments(self):
        """Zapisuje przypisania tagów do kontaktów do pliku"""
        try:
            self.contact_tag_assignments_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.contact_tag_assignments_file, 'w', encoding='utf-8') as f:
                json.dump(self.contact_tags, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można zapisać przypisań tagów: {e}")
    
    def load_column_order(self):
        """Wczytuje kolejność kolumn z pliku"""
        default_order = list(range(12))  # [0, 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11]
        
        if self.column_order_file.exists():
            try:
                with open(self.column_order_file, 'r', encoding='utf-8') as f:
                    saved_order = json.load(f)
                    # Walidacja: musi być listą 12 elementów z unikalnymi wartościami 0-11
                    if isinstance(saved_order, list) and len(saved_order) == 12:
                        if set(saved_order) == set(range(12)):
                            return saved_order
            except (json.JSONDecodeError, IOError) as e:
                logger.warning(f"Błąd wczytywania kolejności kolumn: {e}")
        
        return default_order
    
    def save_column_order(self):
        """Zapisuje kolejność kolumn do pliku"""
        try:
            self.column_order_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.column_order_file, 'w', encoding='utf-8') as f:
                json.dump(self.column_order, f, indent=2, ensure_ascii=False)
            logger.info(f"Zapisano kolejność kolumn: {self.column_order}")
        except Exception as e:
            logger.error(f"Błąd zapisywania kolejności kolumn: {e}")
    
    def load_column_widths(self):
        """Wczytuje szerokości kolumn z pliku"""
        default_widths = {
            0: 40,   # ⭐
            1: 200,  # Adres mail
            2: 150,  # Imię/Nazwisko
            3: 80,   # Odpowiedz
            4: 35,   # ▶️
            5: 250,  # Tytuł
            6: 130,  # Data
            7: 90,   # Rozmiar
            8: 100,  # Wątków
            9: 140,  # Tag
            10: 220, # Notatka
            11: 40,  # 🪄
        }
        
        if self.column_widths_file.exists():
            try:
                with open(self.column_widths_file, 'r', encoding='utf-8') as f:
                    saved_widths = json.load(f)
                    # Walidacja: musi być słownikiem
                    if not isinstance(saved_widths, dict):
                        print(f"Nieprawidłowy format column_widths.json")
                        return default_widths
                    # Konwertuj klucze ze stringów na int i waliduj wartości
                    result = {}
                    for k, v in saved_widths.items():
                        try:
                            col_idx = int(k)
                            width = int(v)
                            # Waliduj rozsądne wartości (20-2000 px)
                            if 20 <= width <= 2000 and 0 <= col_idx <= 11:
                                result[col_idx] = width
                        except (ValueError, TypeError):
                            continue
                    return result if result else default_widths
            except (json.JSONDecodeError, IOError) as e:
                print(f"Błąd wczytywania szerokości kolumn: {e}")
                return default_widths
        
        return default_widths
    
    def save_column_widths(self):
        """Zapisuje szerokości kolumn do pliku"""
        if not hasattr(self, 'mail_list'):
            return
        
        try:
            self.column_widths_file.parent.mkdir(parents=True, exist_ok=True)
            widths = {}
            for i in range(self.mail_list.columnCount()):
                widths[i] = self.mail_list.columnWidth(i)
            
            with open(self.column_widths_file, 'w', encoding='utf-8') as f:
                json.dump(widths, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisywania szerokości kolumn: {e}")

    def get_accounts_from_db(self):
        """
        Pobiera konta pocztowe z centralnej bazy danych EmailAccountsDatabase
        
        Returns:
            Lista słowników z danymi kont w formacie kompatybilnym z ProMail
        """
        if not self.email_accounts_db:
            logger.warning("[ProMail] EmailAccountsDatabase not available, returning empty list")
            return []
        
        if not self.user_id:
            logger.warning("[ProMail] User ID not set, returning empty list. Call set_user_data() first.")
            return []
        
        try:
            # Pobierz konta z bazy (tylko aktywne)
            accounts = self.email_accounts_db.get_all_accounts(self.user_id, active_only=True)
            
            logger.info(f"[ProMail] Loaded {len(accounts)} accounts for user_id: {self.user_id}")
            
            # Konwertuj format bazy danych na format używany przez ProMail
            mail_accounts = []
            for account in accounts:
                # Pobierz pełną konfigurację z hasłem
                account_config = self.email_accounts_db.get_account_config(account['id'])
                
                if not account_config:
                    logger.warning(f"[ProMail] Could not get config for account {account['id']}")
                    continue
                
                # Mapuj na format oczekiwany przez fetch_from_account()
                mail_account = {
                    # Podstawowe info
                    "id": account['id'],
                    "name": account['account_name'],
                    "email": account['email_address'],
                    
                    # Dane logowania
                    "username": account_config['username'],
                    "password": account_config['password'],
                    
                    # Serwer (IMAP)
                    "imap_server": account_config['server_address'],
                    "imap_port": account_config['server_port'],
                    "imap_ssl": account_config['use_ssl'],
                    
                    # Opcje pobierania
                    "fetch_limit": account.get('fetch_limit', 50),
                    
                    # Dla kompatybilności
                    "server": account_config['server_address'],
                    "port": account_config['server_port'],
                    "server_type": account_config['server_type'].lower(),
                    "use_ssl": account_config['use_ssl'],
                    "use_tls": account_config['use_tls'],
                }
                mail_accounts.append(mail_account)
            
            logger.info(f"[ProMail] Configured {len(mail_accounts)} accounts with credentials for IMAP")
            return mail_accounts
            
        except Exception as e:
            logger.error(f"[ProMail] Error loading accounts from database: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return []

    def reload_accounts(self):
        """Ponownie wczytuje konta z bazy danych i aktualizuje UI"""
        try:
            logger.info("[ProMail] Reloading accounts from database...")
            
            # Pobierz konta z bazy
            self.mail_accounts = self.get_accounts_from_db()
            
            # Odśwież listę rozwijaną
            self.populate_account_filter()
            
            # Pokaż komunikat
            count = len(self.mail_accounts)
            self.show_status_message(f"Odświeżono: znaleziono {count} kont", 3000)
            
            logger.info(f"[ProMail] Reloaded {count} accounts successfully")
            
        except Exception as e:
            logger.error(f"[ProMail] Error reloading accounts: {e}")
            QMessageBox.warning(
                self,
                "Błąd",
                f"Nie można odświeżyć listy kont:\n{e}"
            )

    def set_user_data(self, user_data: dict, **kwargs):
        """
        Ustawia dane użytkownika i wczytuje jego konta pocztowe.
        
        Ta metoda jest wywoływana przez główną aplikację podczas inicjalizacji modułu.
        
        Args:
            user_data: Słownik z danymi użytkownika (musi zawierać 'id')
            **kwargs: Dodatkowe parametry (ignorowane)
        """
        try:
            self.user_id = user_data.get('id')
            logger.info(f"[ProMail] User ID set to: {self.user_id}")
            
            # Wczytaj konta użytkownika
            self.mail_accounts = self.get_accounts_from_db()
            
            # Zaktualizuj UI
            self.populate_account_filter()
            
            logger.info(f"[ProMail] Loaded {len(self.mail_accounts)} accounts for user")
            
        except Exception as e:
            logger.error(f"[ProMail] Error in set_user_data: {e}")
            self.user_id = None
            self.mail_accounts = []

    def populate_account_filter(self):
        """Wypełnia listę filtrowania kont"""
        if not hasattr(self, "account_filter_combo"):
            return
        
        self.account_filter_combo.blockSignals(True)
        self.account_filter_combo.clear()
        
        # Opcja "Wszystkie"
        self.account_filter_combo.addItem("📧 Wszystkie konta", None)
        
        # Dodaj konta
        for account in self.mail_accounts:
            email = account.get("email", "")
            name = account.get("name", email)
            if email:
                self.account_filter_combo.addItem(f"📨 {name}", email)
        
        self.account_filter_combo.blockSignals(False)
        self.account_filter_combo.setCurrentIndex(0)

    def on_account_filter_changed(self, index):
        """Obsługuje zmianę filtra konta"""
        selected_email = self.account_filter_combo.currentData()
        
        # Przefiltruj maile według wybranego konta
        if self.mail_scope == "folder" and hasattr(self, "current_folder"):
            self.load_folder_mails(self.current_folder)
        else:
            self.apply_mail_filters()
    
    def on_column_resized(self, column_index: int, old_size: int, new_size: int):
        """Obsługuje zmianę szerokości kolumny przez użytkownika"""
        # Zapisz nową szerokość
        self.column_widths[column_index] = new_size
        self.save_column_widths()

    def refresh_tag_filter_options(self, initial=False):
        """Aktualizuje listę tagów w filtrze"""
        if not hasattr(self, "mail_tag_filter"):
            return
        current = None if initial else self.mail_tag_filter.currentData()
        self.mail_tag_filter.blockSignals(True)
        self.mail_tag_filter.clear()
        self.mail_tag_filter.addItem("Wszystkie tagi", None)
        for tag in self.mail_tags:
            self.mail_tag_filter.addItem(tag["name"], tag["name"])
        # Dodaj opcję Ulubione na końcu
        self.mail_tag_filter.addItem("⭐ Ulubione", "__favorites__")
        if current is not None:
            index = self.mail_tag_filter.findData(current)
            if index >= 0:
                self.mail_tag_filter.setCurrentIndex(index)
        self.mail_tag_filter.blockSignals(False)

    def set_mail_filter_controls_enabled(self, enabled):
        """Włącza lub wyłącza kontrolki filtrów"""
        self.mail_filter_enabled = enabled
        if hasattr(self, "mail_search_input"):
            self.mail_search_input.setEnabled(enabled)
        if hasattr(self, "mail_tag_filter"):
            self.mail_tag_filter.setEnabled(enabled)

    def on_column_resized(self, logical_index: int, old_size: int, new_size: int):
        """Zapisuje szerokość kolumny po zmianie przez użytkownika"""
        if not hasattr(self, 'column_widths'):
            return
        self.column_widths[logical_index] = new_size
        self.save_column_widths()
    
    def on_column_moved(self, logical_index: int, old_visual_index: int, new_visual_index: int):
        """Zapisuje kolejność kolumn po przesunięciu przez użytkownika"""
        if not hasattr(self, 'column_order') or not hasattr(self, 'mail_list'):
            return
        
        # Aktualizuj column_order na podstawie aktualnego stanu nagłówka
        header = self.mail_list.horizontalHeader()
        if header:
            new_order = []
            for visual_idx in range(header.count()):
                logical_idx = header.logicalIndex(visual_idx)
                new_order.append(logical_idx)
            self.column_order = new_order
            self.save_column_order()
            logger.info(f"Kolumna przesunięta: {logical_index} z {old_visual_index} na {new_visual_index}")
            logger.info(f"Nowa kolejność: {self.column_order}")
    
    def on_mail_filter_changed(self, *_args):
        """Reaguje na zmianę filtrów listy maili"""
        if not self.mail_filter_enabled or self.mail_scope != "folder":
            return
        self.apply_mail_filters()

    def apply_mail_filters(self):
        """Stosuje filtry do listy maili"""
        if not hasattr(self, "mail_list"):
            return
        if self.mail_scope != "folder":
            return
        text_filter = ""
        if hasattr(self, "mail_search_input") and self.mail_search_input.isEnabled():
            text_filter = self.mail_search_input.text().strip().lower()
        tag_filter = None
        if hasattr(self, "mail_tag_filter") and self.mail_tag_filter.isEnabled():
            tag_filter = self.mail_tag_filter.currentData()
        filtered = []
        for mail in self.current_folder_mails:
            tags = self.get_mail_tags(mail)
            if text_filter:
                haystack = " ".join([
                    mail.get("subject", ""),
                    mail.get("from", ""),
                    mail.get("note", ""),
                ]).lower()
                if text_filter not in haystack:
                    continue
            # Specjalna obsługa filtra "Ulubione"
            if tag_filter == "__favorites__":
                if not mail.get("starred"):
                    continue
            elif tag_filter and tag_filter not in tags:
                continue
            filtered.append(mail)
        self.populate_mail_table(filtered)

    def populate_mail_table(self, mails):
        """Wypełnia tabelę maili"""
        if not hasattr(self, "mail_list"):
            return
        
        # Wyczyść mapowanie rozwiniętych wierszy przy odświeżaniu
        self.expanded_preview_rows = {}
        
        # Ustaw domyślną kolejność jeśli nie istnieje
        if not hasattr(self, 'column_order'):
            self.column_order = list(range(12))
        
        # Grupuj maile w wątki jeśli włączone
        if self.threads_enabled:
            self.mail_threads = self.group_mails_into_threads(mails)
            # Przygotuj listę do wyświetlenia: tylko najnowsze maile z każdego wątku
            display_mails = []
            for thread_id, thread_mails in self.mail_threads.items():
                # Najnowszy mail jest pierwszy (sortowanie reverse=True)
                newest_mail = thread_mails[0]
                newest_mail["_is_thread_parent"] = True
                newest_mail["_thread_count"] = len(thread_mails)
                display_mails.append(newest_mail)
            # Sortuj wątki według daty najnowszego maila
            display_mails.sort(key=lambda m: m.get("date", ""), reverse=True)
        else:
            display_mails = mails
            self.mail_threads = {}
        
        self.displayed_mails = display_mails
        
        # Batch UI updates - wyłącz odświeżanie podczas wypełniania
        self.mail_list.setUpdatesEnabled(False)
        self.mail_list.blockSignals(True)
        self.mail_list.clearContents()
        self.mail_list.setRowCount(len(display_mails))

        for row, mail in enumerate(display_mails):
            self.mail_list.setRowHeight(row, 36)  # Zwiększono z 26 na 36 dla lepszej czytelności
            self.ensure_mail_uid(mail)
            if "_folder" not in mail and self.mail_scope == "folder":
                mail["_folder"] = getattr(self, "current_folder", None)
            
            # Inicjalizuj stan rozwinięcia dla tego maila
            if "_expanded" not in mail:
                mail["_expanded"] = False

            # Przygotuj dane dla wszystkich kolumn
            from_address = mail.get("from", "")
            email_only = self.extract_email_address(from_address)
            name = self.extract_display_name(from_address)
            
            # Wypełnij kolumny według aktualnej kolejności
            for visual_idx, col_idx in enumerate(self.column_order):
                self.populate_mail_cell(row, visual_idx, col_idx, mail, email_only, name)

        self.mail_list.blockSignals(False)
        self.mail_list.setUpdatesEnabled(True)  # Włącz odświeżanie po zakończeniu
        self.mail_list.clearSelection()
        self.displayed_mails = list(mails)
    
    def populate_mail_cell(self, row: int, visual_idx: int, col_idx: int, mail: dict, email_only: str, name: str):
        """Wypełnia pojedynczą komórkę tabeli maili"""
        if col_idx == 0:  # Gwiazdka
            star_item = QTableWidgetItem("⭐" if mail.get("starred") else "")
            star_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            star_item.setFlags(star_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mail_list.setItem(row, visual_idx, star_item)
        
        elif col_idx == 1:  # Adres mail
            from_item = QTableWidgetItem(email_only)
            from_item.setFlags(from_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # Zastosuj kolor kontaktu jeśli ustawiony
            if email_only in self.contact_colors:
                from_item.setBackground(self.contact_colors[email_only])
                if self.contact_colors[email_only].lightness() < 128:
                    from_item.setForeground(QColor("white"))
            # Dodaj tagi do tooltipa
            if email_only in self.contact_tags and self.contact_tags[email_only]:
                tags_str = ", ".join(self.contact_tags[email_only])
                from_item.setToolTip(f"Tagi: {tags_str}")
            self.mail_list.setItem(row, visual_idx, from_item)
        
        elif col_idx == 2:  # Imię/Nazwisko
            name_item = QTableWidgetItem(name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # Zastosuj kolor kontaktu jeśli ustawiony
            if email_only in self.contact_colors:
                name_item.setBackground(self.contact_colors[email_only])
                if self.contact_colors[email_only].lightness() < 128:
                    name_item.setForeground(QColor("white"))
            # Dodaj tagi do tooltipa
            if email_only in self.contact_tags and self.contact_tags[email_only]:
                tags_str = ", ".join(self.contact_tags[email_only])
                name_item.setToolTip(f"Tagi: {tags_str}")
            self.mail_list.setItem(row, visual_idx, name_item)
        
        elif col_idx == 3:  # Emoji Odpowiedz (klikalne)
            reply_item = QTableWidgetItem("↩️")
            reply_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            reply_item.setFlags(reply_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            reply_item.setToolTip("Kliknij aby odpowiedzieć")
            reply_item.setData(Qt.ItemDataRole.UserRole, {"action": "reply", "mail": mail})
            self.mail_list.setItem(row, visual_idx, reply_item)
        
        elif col_idx == 4:  # Emoji strzałki (rozwiń/zwiń) - klikalne
            expand_item = QTableWidgetItem("▶️" if not mail.get("_expanded") else "🔽")
            expand_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            expand_item.setFlags(expand_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            expand_item.setToolTip("Kliknij aby rozwinąć/zwinąć podgląd")
            expand_item.setData(Qt.ItemDataRole.UserRole, {"action": "expand", "row": row})
            self.mail_list.setItem(row, visual_idx, expand_item)
        
        elif col_idx == 5:  # Tytuł
            subject_item = QTableWidgetItem(mail.get("subject", ""))
            subject_item.setFlags(subject_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mail_list.setItem(row, visual_idx, subject_item)
        
        elif col_idx == 6:  # Data
            date_item = QTableWidgetItem(mail.get("date", ""))
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.mail_list.setItem(row, visual_idx, date_item)
        
        elif col_idx == 7:  # Rozmiar
            size_item = QTableWidgetItem(mail.get("size", ""))
            size_item.setFlags(size_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if mail.get("attachments"):
                size_item.setForeground(QColor("#FF8C00"))  # Pomarańczowy
            self.mail_list.setItem(row, visual_idx, size_item)
        
        elif col_idx == 8:  # Wątki
            # Jeśli włączone są wątki, pokaż liczbę maili w wątku
            if self.threads_enabled and mail.get("_is_thread_parent"):
                conv_count = str(mail.get("_thread_count", 1))
            else:
                conv_count = str(mail.get("conversation_count", 1))
            conv_item = QTableWidgetItem(conv_count)
            conv_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            conv_item.setFlags(conv_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            # Wyróżnij wątki z wieloma mailami
            if self.threads_enabled and mail.get("_thread_count", 1) > 1:
                conv_item.setForeground(QColor("#0066CC"))  # Niebieski
                conv_item.setToolTip(f"Wątek zawiera {mail['_thread_count']} wiadomości")
            self.mail_list.setItem(row, visual_idx, conv_item)
        
        elif col_idx == 9:  # Tag
            tags = self.get_mail_tags(mail)
            if tags:
                # Utwórz etykietę z tagami oddzielonymi przecinkami
                tags_text = ", ".join(tags)
                tag_item = QTableWidgetItem(tags_text)
            else:
                tag_item = QTableWidgetItem("")
            
            tag_item.setFlags(tag_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            tag_item.setToolTip(tags_text if tags else "Brak tagów - kliknij prawym aby dodać")
            self.mail_list.setItem(row, visual_idx, tag_item)
        
        elif col_idx == 10:  # Notatka
            note_item = QTableWidgetItem(mail.get("note", ""))
            note_item.setFlags(note_item.flags() | Qt.ItemFlag.ItemIsEditable)
            note_item.setToolTip(mail.get("note", ""))
            self.mail_list.setItem(row, visual_idx, note_item)
        
        elif col_idx == 11:  # 🪄 (Magiczna różdżka)
            magic_item = QTableWidgetItem("🪄")
            magic_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            magic_item.setFlags(magic_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            magic_item.setToolTip("Magiczna różdżka")
            self.mail_list.setItem(row, visual_idx, magic_item)

    def extract_display_name(self, from_field: str) -> str:
        """Wyodrębnia nazwę/imię z pola 'from' (np. 'Jan Kowalski <jan@example.com>' → 'Jan Kowalski')"""
        if not from_field:
            return ""
        # Sprawdź czy jest w formacie: Name <email>
        import re
        match = re.match(r'^(.+?)\s*<(.+)>$', from_field.strip())
        if match:
            name = match.group(1).strip()
            # Usuń cudzysłowy jeśli są
            name = name.strip('"\'')
            return name
        return ""
    
    def extract_email_address(self, from_field: str) -> str:
        """Wyodrębnia sam adres email z pola 'from' (np. 'Jan Kowalski <jan@example.com>' → 'jan@example.com')"""
        if not from_field:
            return ""
        
        # Sprawdź cache
        if from_field in self._email_parse_cache:
            return self._email_parse_cache[from_field][0]
        
        # Parsuj i zapisz w cache
        import re
        match = re.match(r'^(.+?)\s*<(.+)>$', from_field.strip())
        if match:
            email = match.group(2).strip()
            display_name = match.group(1).strip()
        else:
            email = from_field.strip()
            display_name = ""
        
        self._email_parse_cache[from_field] = (email, display_name)
        return email
    
    def extract_display_name(self, from_field: str) -> str:
        """Wyodrębnia nazwę wyświetlaną z pola 'from'"""
        if not from_field:
            return ""
        
        # Sprawdź cache
        if from_field in self._email_parse_cache:
            return self._email_parse_cache[from_field][1]
        
        # Jeśli nie w cache, wywołaj extract_email_address aby zapisać w cache
        self.extract_email_address(from_field)
        return self._email_parse_cache.get(from_field, ("", ""))[1]
    
    def get_qcolor(self, color_str: str) -> QColor:
        """Zwraca QColor z cache (optymalizacja)"""
        if color_str not in self._qcolor_cache:
            self._qcolor_cache[color_str] = QColor(color_str)
        return self._qcolor_cache[color_str]
    
    def sanitize_html(self, text: str) -> str:
        """Sanityzuje HTML aby zapobiec XSS (Cross-Site Scripting)"""
        if not text:
            return ""
        
        # Podstawowa sanityzacja - escape HTML
        from html import escape
        safe_text = escape(text)
        
        # Usuń potencjalnie niebezpieczne tagi
        dangerous_patterns = [
            r'<script[^>]*>.*?</script>',
            r'<iframe[^>]*>.*?</iframe>',
            r'javascript:',
            r'on\w+\s*=',  # onevent handlers
        ]
        
        import re
        for pattern in dangerous_patterns:
            safe_text = re.sub(pattern, '', safe_text, flags=re.IGNORECASE | re.DOTALL)
        
        return safe_text

    def toggle_mail_preview(self, row: int):
        """Rozwija/zwija podgląd treści maila"""
        if not hasattr(self, "mail_list"):
            return
        
        mail = self.get_mail_by_row(row)
        if not mail:
            return
        
        # Ustaw domyślną kolejność jeśli nie istnieje
        if not hasattr(self, 'column_order'):
            self.column_order = list(range(12))
        
        # Znajdź wizualny indeks dla kolumny 4 (strzałka)
        expand_visual_idx = self.column_order.index(4) if 4 in self.column_order else -1
        
        # Przełącz stan rozwinięcia
        is_expanded = mail.get("_expanded", False)
        mail["_expanded"] = not is_expanded
        
        # Zaktualizuj emoji w komórce
        if expand_visual_idx >= 0:
            expand_item = self.mail_list.item(row, expand_visual_idx)
            if expand_item:
                expand_item.setText("🔽" if mail["_expanded"] else "▶️")
                expand_item.setData(Qt.ItemDataRole.UserRole, {"action": "expand", "row": row})
        
        # Dodaj lub usuń wiersz podglądu
        if mail["_expanded"]:
            # Dodaj nowy wiersz pod aktualnym mailem
            preview_row = row + 1
            self.mail_list.insertRow(preview_row)
            
            # Pobierz liczbę linii z ustawień
            preview_lines = getattr(self, "mail_preview_lines", 3)
            
            # Parsuj treść maila
            body_preview = self.get_mail_body_preview(mail, preview_lines)
            
            # Sprawdź czy jest ciemny motyw
            is_dark = False
            if self.theme_manager:
                try:
                    is_dark = self.theme_manager.get_current_theme() == "dark"
                except:
                    pass
            
            # Utwórz widget z podglądem treści (połączone kolumny)
            preview_widget = QLabel(body_preview)
            preview_widget.setWordWrap(True)
            
            if is_dark:
                preview_widget.setStyleSheet("""
                    QLabel {
                        background-color: #2C2C2C;
                        padding: 8px;
                        border-left: 3px solid #64B5F6;
                        color: #E0E0E0;
                        font-size: 11px;
                    }
                """)
            else:
                preview_widget.setStyleSheet("""
                    QLabel {
                        background-color: #F5F5F5;
                        padding: 8px;
                        border-left: 3px solid #2196F3;
                        color: #333;
                        font-size: 11px;
                    }
                """)
            
            preview_widget.setTextInteractionFlags(
                Qt.TextInteractionFlag.TextSelectableByMouse | 
                Qt.TextInteractionFlag.TextSelectableByKeyboard
            )
            
            # Ustaw widget rozciągnięty na wszystkie kolumny
            self.mail_list.setSpan(preview_row, 0, 1, self.mail_list.columnCount())
            self.mail_list.setCellWidget(preview_row, 0, preview_widget)
            
            # Dostosuj wysokość wiersza do treści
            content_height = min(preview_lines * 20 + 16, 200)  # max 200px
            self.mail_list.setRowHeight(preview_row, content_height)
            
            # Zapisz mapowanie
            self.expanded_preview_rows[row] = preview_row
        else:
            # Usuń wiersz podglądu jeśli istnieje
            if row in self.expanded_preview_rows:
                preview_row = self.expanded_preview_rows[row]
                self.mail_list.removeRow(preview_row)
                del self.expanded_preview_rows[row]
                
                # Zaktualizuj mapowanie dla pozostałych wierszy
                updated_mapping = {}
                for mail_row, prev_row in self.expanded_preview_rows.items():
                    if prev_row > preview_row:
                        updated_mapping[mail_row] = prev_row - 1
                    else:
                        updated_mapping[mail_row] = prev_row
                self.expanded_preview_rows = updated_mapping
    
    def get_mail_body_preview(self, mail: Dict[str, Any], lines: int = 3) -> str:
        """Zwraca podgląd treści maila z normalizacją białych znaków"""
        body = mail.get("body", "")
        if not body:
            return "(brak treści)"
        
        # Usuń HTML tags jeśli są
        import re
        body = re.sub(r'<[^>]+>', '', body)
        
        # Normalizuj białe znaki - zamień wielokrotne spacje/taby na pojedyncze
        body = re.sub(r'[ \t]+', ' ', body)
        
        # Podziel na linie, usuń puste i weź pierwsze N niepustych
        body_lines = [line.strip() for line in body.split('\n') if line.strip()]
        preview_lines = body_lines[:lines]
        preview = '\n'.join(preview_lines)
        
        # Skróć jeśli za długie
        if len(preview) > 400:
            preview = preview[:400] + "..."
        
        return preview

    def toggle_all_previews(self):
        """Przełącza stan wszystkich podglądów (rozwiń/zwiń)"""
        is_expanding = self.toggle_all_previews_btn.isChecked()
        
        if is_expanding:
            # Rozwiń wszystkie
            self.toggle_all_previews_btn.setText("▶️ Zwiń wszystkie")
            self.expand_all_previews()
        else:
            # Zwiń wszystkie
            self.toggle_all_previews_btn.setText("🔽 Rozwiń wszystkie")
            self.collapse_all_previews()
    
    def expand_all_previews(self):
        """Rozwija wszystkie podglądy maili"""
        # Iteruj od końca, aby uniknąć problemów z dodawaniem wierszy
        for i in range(len(self.displayed_mails) - 1, -1, -1):
            mail = self.displayed_mails[i]
            if not mail.get("_expanded", False):
                # Znajdź fizyczny wiersz dla tego maila
                preview_rows_before = sum(1 for mail_row, _ in self.expanded_preview_rows.items() if mail_row <= i)
                physical_row = i + preview_rows_before
                self.toggle_mail_preview(physical_row)
    
    def collapse_all_previews(self):
        """Zwija wszystkie podglądy maili"""
        # Iteruj od końca, aby uniknąć problemów z usuwaniem wierszy
        expanded_rows = sorted(self.expanded_preview_rows.keys(), reverse=True)
        for mail_row in expanded_rows:
            # Znajdź fizyczny wiersz
            preview_rows_before = sum(1 for mr, _ in self.expanded_preview_rows.items() if mr < mail_row)
            physical_row = mail_row + preview_rows_before
            self.toggle_mail_preview(physical_row)
    
    def on_preview_lines_changed(self, value: int):
        """Reaguje na zmianę liczby linii podglądu"""
        self.mail_preview_lines = value
        
        # Odśwież wszystkie rozwinięte podglądy
        for mail_row, preview_row in list(self.expanded_preview_rows.items()):
            mail = self.displayed_mails[mail_row] if mail_row < len(self.displayed_mails) else None
            if not mail:
                continue
            
            # Pobierz widget podglądu
            preview_widget = self.mail_list.cellWidget(preview_row, 0)
            if isinstance(preview_widget, QLabel):
                # Zaktualizuj treść
                body_preview = self.get_mail_body_preview(mail, value)
                preview_widget.setText(body_preview)
                
                # Zaktualizuj wysokość
                content_height = min(value * 20 + 16, 200)
                self.mail_list.setRowHeight(preview_row, content_height)

    def get_mail_by_row(self, row: int) -> Optional[Dict[str, Any]]:
        """Zwraca maila powiązanego z wierszem tabeli."""
        # Sprawdź czy to wiersz podglądu
        if row in self.expanded_preview_rows.values():
            return None  # To jest wiersz podglądu, nie mail
        
        # Przelicz fizyczny wiersz na indeks w displayed_mails
        # Musim policzyć ile wierszy podglądu jest przed tym wierszem
        preview_rows_before = sum(1 for prev_row in self.expanded_preview_rows.values() if prev_row < row)
        mail_index = row - preview_rows_before
        
        if 0 <= mail_index < len(self.displayed_mails):
            return self.displayed_mails[mail_index]
        return None

    def ensure_mail_uid(self, mail: Dict[str, Any]) -> str:
        """Gwarantuje istnienie identyfikatora dla wiadomości."""
        uid = mail.get("_uid")
        if not uid:
            self.mail_uid_counter += 1
            uid = f"mail-{self.mail_uid_counter}"
            mail["_uid"] = uid
        self.mail_uid_map[uid] = mail
        
        # Dodaj do indeksu dla szybkiego wyszukiwania
        folder = mail.get("_folder", "Unknown")
        self._mail_index[uid] = (folder, mail)
        
        return uid
    
    def find_mail_by_uid(self, uid: str) -> tuple[str, Dict[str, Any]] | None:
        """Szybko znajduje mail po UID używając indeksu"""
        return self._mail_index.get(uid)
    
    def normalize_subject(self, subject: str) -> str:
        """Normalizuje temat maila usuwając Re:, Fwd: itp."""
        import re
        if not subject:
            return ""
        # Usuń prefiksy Re:, Fwd:, RE:, FW: itd.
        normalized = re.sub(r'^(Re|Fwd|RE|FW|Odp|Przekaż):\s*', '', subject, flags=re.IGNORECASE)
        normalized = normalized.strip()
        return normalized.lower()
    
    def get_thread_id(self, mail: Dict[str, Any]) -> str:
        """Generuje identyfikator wątku dla maila na podstawie tematu i uczestników"""
        subject = self.normalize_subject(mail.get("subject", ""))
        # Pobierz uczestników (nadawca + odbiorcy)
        participants = set()
        from_addr = self.extract_email_address(mail.get("from", "")).lower()
        if from_addr:
            participants.add(from_addr)
        to_addr = mail.get("to", "")
        if to_addr:
            participants.add(to_addr.lower())
        
        # Posortuj uczestników dla konsystencji
        participants_str = ",".join(sorted(participants))
        
        # Thread ID = hash(subject + participants)
        import hashlib
        thread_key = f"{subject}:{participants_str}"
        thread_id = hashlib.md5(thread_key.encode()).hexdigest()[:16]
        return thread_id
    
    def group_mails_into_threads(self, mails: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Grupuje maile w wątki konwersacji"""
        threads: Dict[str, List[Dict[str, Any]]] = {}
        
        for mail in mails:
            thread_id = self.get_thread_id(mail)
            mail["_thread_id"] = thread_id
            
            if thread_id not in threads:
                threads[thread_id] = []
            threads[thread_id].append(mail)
        
        # Sortuj maile w każdym wątku według daty
        for thread_id in threads:
            threads[thread_id].sort(key=lambda m: m.get("date", ""), reverse=True)
        
        return threads
    
    def get_thread_mails(self, thread_id: str) -> List[Dict[str, Any]]:
        """Zwraca wszystkie maile z danego wątku"""
        return self.mail_threads.get(thread_id, [])

    def get_tag_color(self, tag_name):
        """Zwraca kolor przypisany do tagu"""
        if not tag_name:
            return None
        for tag in self.mail_tags:
            if tag.get("name") == tag_name and tag.get("color"):
                try:
                    return QColor(tag["color"])
                except Exception:
                    return None
        return None

    def build_tag_combobox(self, mail, row):
        """Tworzy combobox do wyboru tagu dla konkretnego maila"""
        combo = QComboBox()
        combo.setEditable(False)
        combo.setProperty("mail_row", row)

        combo.addItem("Brak tagu", None)
        known_tags = [tag.get("name") for tag in self.mail_tags if tag.get("name")]
        for tag_name in known_tags:
            combo.addItem(tag_name, tag_name)

        current_tags = self.get_mail_tags(mail)
        for tag_name in current_tags:
            if tag_name and tag_name not in known_tags:
                combo.addItem(tag_name, tag_name)

        selected = current_tags[0] if current_tags else None
        combo.blockSignals(True)
        index = combo.findData(selected)
        combo.setCurrentIndex(index if index >= 0 else 0)
        combo.blockSignals(False)

        combo.currentIndexChanged.connect(partial(self.on_mail_tag_changed, row))
        return combo

    def update_tag_item_display(self, row, visual_idx, tags):
        """Aktualizuje wygląd komórki z tagiem"""
        item = self.mail_list.item(row, visual_idx) if hasattr(self, "mail_list") else None
        if item is None:
            return

        tag_text = ", ".join(tags)
        item.setText(tag_text)
        item.setToolTip(tag_text or "Brak tagu")

        if tags:
            color = self.get_tag_color(tags[0])
            if color:
                item.setBackground(QBrush(color))
                text_color = Qt.GlobalColor.white if color.lightness() < 128 else Qt.GlobalColor.black
                item.setForeground(QBrush(text_color))
                return

        item.setBackground(QBrush())
        item.setForeground(QBrush())

    def get_mail_tags(self, mail):
        """Zwraca listę tagów wiadomości i normalizuje strukturę danych"""
        tags = mail.get("tags")
        if isinstance(tags, list):
            cleaned = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            single = mail.get("tag")
            cleaned = [str(single).strip()] if single and str(single).strip() else []

        self.set_mail_tags(mail, cleaned)
        return cleaned

    def set_mail_tags(self, mail, tags):
        """Utrzymuje spójną reprezentację tagów (lista i pojedyncza wartość)"""
        cleaned = [str(tag).strip() for tag in tags if str(tag).strip()]
        mail["tags"] = cleaned
        mail["tag"] = cleaned[0] if cleaned else ""
    
    def on_mail_tag_selected(self, index):
        """Obsługuje wybór tagu z listy rozwijanej w nagłówku maila"""
        if index <= 0:  # "-- Wybierz tag --"
            return
        
        if not self.current_mail:
            return
        
        selected_tag = self.mail_tag_selector.itemData(index)
        if not selected_tag:
            return
        
        # Pobierz aktualne tagi
        current_tags = self.get_mail_tags(self.current_mail)
        
        # Jeśli tag już jest na liście, usuń go; jeśli nie ma, dodaj
        if selected_tag in current_tags:
            current_tags.remove(selected_tag)
            self.show_status_message(f"Usunięto tag: {selected_tag}", 2000)
        else:
            current_tags.append(selected_tag)
            self.show_status_message(f"Dodano tag: {selected_tag}", 2000)
        
        # Zapisz zmiany
        self.set_mail_tags(self.current_mail, current_tags)
        
        # Odśwież wyświetlanie
        self.display_mail(self.current_mail)
        
        # Odśwież wiersz w tabeli jeśli mail jest widoczny
        for row in range(self.mail_list.rowCount()):
            mail = self.get_mail_by_row(row)
            if mail and mail.get("_uid") == self.current_mail.get("_uid"):
                # Znajdź kolumnę tagów (col_idx == 9)
                if not hasattr(self, 'column_order'):
                    self.column_order = list(range(12))
                visual_idx = self.column_order.index(9) if 9 in self.column_order else -1
                if visual_idx >= 0:
                    tags_text = ", ".join(current_tags) if current_tags else ""
                    tag_item = self.mail_list.item(row, visual_idx)
                    if tag_item:
                        tag_item.setText(tags_text)
                        tag_item.setToolTip(tags_text if tags_text else "Brak tagów - kliknij prawym aby dodać")
                break

    def toggle_mail_star(self, row: int, mail: Optional[Dict[str, Any]] = None) -> Optional[bool]:
        """Przełącza stan gwiazdki dla wskazanego wiersza."""
        if not hasattr(self, "mail_list"):
            return None

        if mail is None:
            mail = self.get_mail_by_row(row)
        if mail is None:
            return None

        new_state = not mail.get("starred", False)
        mail["starred"] = new_state
        
        # Aktualizuj cache
        if hasattr(self, 'cache_integration'):
            uid = mail.get("_uid")
            if uid:
                self.cache_integration.update_mail_cache(uid, {"starred": new_state})

        # Znajdź wizualny indeks kolumny gwiazdki (col_idx == 0)
        if not hasattr(self, 'column_order'):
            self.column_order = list(range(12))
        
        visual_idx = self.column_order.index(0) if 0 in self.column_order else 0
        
        item = self.mail_list.item(row, visual_idx)
        if item is not None:
            item.setText("⭐" if new_state else "")

        if self.current_folder == "Ulubione" and not new_state:
            if 0 <= row < len(self.displayed_mails):
                self.displayed_mails.pop(row)
            self.current_folder_mails = [m for m in self.current_folder_mails if m is not mail]
            if 0 <= row < self.mail_list.rowCount():
                self.mail_list.removeRow(row)
            if self.current_mail is mail:
                self.clear_mail_view()
        else:
            if self.mail_scope == "folder":
                self.current_folder_mails = [m if m is not mail else mail for m in self.current_folder_mails]
            if 0 <= row < len(self.displayed_mails):
                self.displayed_mails[row] = mail
            if self.current_mail is mail:
                self.display_mail(mail)

        self.update_favorites_folder_item()

        return new_state

    def on_mail_tag_changed(self, row, _index):
        """Aktualizuje tag maila po zmianie w comboboxie"""
        if not hasattr(self, "mail_list"):
            return
        combo = self.mail_list.cellWidget(row, 6)
        if not isinstance(combo, QComboBox):
            return

        new_value = combo.currentData()
        tags_list = [new_value] if new_value else []

        if not (0 <= row < len(self.displayed_mails)):
            return
        mail = self.displayed_mails[row]
        self.set_mail_tags(mail, tags_list)

        active_tag_filter = None
        if self.mail_filter_enabled and hasattr(self, "mail_tag_filter"):
            active_tag_filter = self.mail_tag_filter.currentData()

        if self.mail_scope == "folder" and active_tag_filter and active_tag_filter not in tags_list:
            if self.current_mail is mail:
                self.display_mail(mail)
            self.apply_mail_filters()
            return

        self.update_tag_item_display(row, tags_list)
        if self.current_mail is mail:
            self.display_mail(mail)

    def on_mail_cell_double_clicked(self, row, column):
        """Pozwala edytować notatkę po dwukrotnym kliknięciu"""
        if column != 7 or not hasattr(self, "mail_list"):
            return
        item = self.mail_list.item(row, column)
        if item is not None:
            self.mail_list.openPersistentEditor(item)

    def on_mail_item_changed(self, item):
        """Zapisuje zmiany w notatce i domyka edytor"""
        if item is None or not hasattr(self, "mail_list"):
            return
        index = self.mail_list.indexFromItem(item)
        if not index.isValid() or index.column() != 7:
            return

        row = index.row()
        if not (0 <= row < len(self.displayed_mails)):
            return

        note_text = item.text()
        mail = self.displayed_mails[row]
        mail["note"] = note_text
        item.setToolTip(note_text)
        self.mail_list.closePersistentEditor(item)

        if self.current_mail is mail:
            if note_text:
                self.mail_note_label.setText(f"Notatka: {note_text}")
            else:
                self.mail_note_label.setText("")
    
    def populate_favorites_tree(self):
        """Wypełnia drzewo ulubionych plików"""
        self.favorites_tree.clear()
        
        # Załaduj grupy ze słownika
        groups_dict = {}
        groups_file = Path("mail_client/file_groups.json")
        if groups_file.exists():
            try:
                with open(groups_file, 'r', encoding='utf-8') as f:
                    groups_data = json.load(f)
                    for g in groups_data:
                        groups_dict[g['name']] = {
                            'icon': g.get('icon', '📂'),
                            'color': g.get('color', '#FFFFFF')
                        }
            except Exception:
                pass
        
        # Grupuj pliki po tagach/grupach
        groups = {}
        for fav in self.favorite_files:
            group = fav.get("group", "Bez grupy")
            if group not in groups:
                groups[group] = []
            groups[group].append(fav)
        
        # Buduj drzewo
        from PyQt6.QtGui import QColor, QBrush
        
        for group_name, files in groups.items():
            # Pobierz ikonę i kolor z słownika
            group_info = groups_dict.get(group_name, {'icon': '📂', 'color': '#FFFFFF'})
            
            group_item = QTreeWidgetItem([f"{group_info['icon']} {group_name}", ""])
            group_item.setData(0, Qt.ItemDataRole.UserRole, {
                "type": "group",
                "name": group_name,
                "color": group_info['color'],
            })
            
            # Ustaw wyraźniejszy kolor tła grupy
            color = QColor(group_info['color'])
            color.setAlpha(120)  # Zwiększona przezroczystość dla lepszej widoczności
            group_item.setBackground(0, QBrush(color))
            group_item.setBackground(1, QBrush(color))
            
            # Pogrubiona czcionka dla grup
            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)
            
            for file in files:
                file_item = QTreeWidgetItem([
                    f"📄 {file['name']}", 
                    ", ".join(file.get('tags', []))
                ])
                file_item.setData(0, Qt.ItemDataRole.UserRole, file)
                
                # Delikatniejszy kolor dla plików w grupie
                file_color = QColor(group_info['color'])
                file_color.setAlpha(40)
                file_item.setBackground(0, QBrush(file_color))
                file_item.setBackground(1, QBrush(file_color))
                
                group_item.addChild(file_item)
            
            self.favorites_tree.addTopLevelItem(group_item)
            group_item.setExpanded(True)

        self.populate_recent_favorites()
    
    def populate_recent_favorites(self, limit: int = 15) -> None:
        """Aktualizuje listę ostatnio używanych ulubionych."""
        recent_widget = getattr(self, "recent_favorites_list", None)
        if recent_widget is None:
            return

        recent_widget.clear()

        favorites_with_ts: List[tuple[datetime, Dict[str, Any]]] = []
        for favorite in self.favorite_files:
            time_str = favorite.get("last_used_at") or favorite.get("added_at")
            timestamp = datetime.min
            if isinstance(time_str, str):
                try:
                    timestamp = datetime.fromisoformat(time_str)
                except ValueError:
                    timestamp = datetime.min
            favorites_with_ts.append((timestamp, favorite))

        favorites_with_ts.sort(key=lambda item: item[0], reverse=True)

        for _, favorite in favorites_with_ts[:limit]:
            display_name = favorite.get("name", "Plik")
            group_name = favorite.get("group", "Bez grupy")
            if group_name and group_name != "Bez grupy":
                text = f"📄 {display_name} ({group_name})"
            else:
                text = f"📄 {display_name}"

            list_item = QListWidgetItem(text)
            list_item.setData(Qt.ItemDataRole.UserRole, favorite)
            list_item.setToolTip(favorite.get("path", ""))
            recent_widget.addItem(list_item)

    def add_favorite_file(self):
        """Dodaje plik do ulubionych"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik do dodania do ulubionych",
            "",
            "Wszystkie pliki (*.*)"
        )
        
        if file_path:
            # Załaduj dostępne grupy
            available_groups = self.load_available_groups()
            
            # Zapytaj o grupę
            group, ok = QInputDialog.getItem(
                self,
                "Grupa",
                "Wybierz grupę dla pliku:",
                available_groups,
                0,
                False
            )
            
            if ok:
                # Zapytaj o tagi
                tags_str, ok = QInputDialog.getText(
                    self,
                    "Tagi",
                    "Podaj tagi oddzielone przecinkami:"
                )
                
                tags = [t.strip() for t in tags_str.split(",") if t.strip()] if ok and tags_str else []
                
                # Dodaj do listy
                self.favorite_files.append({
                    "name": Path(file_path).name,
                    "path": file_path,
                    "group": group if group else "Bez grupy",
                    "tags": tags,
                    "added_at": datetime.utcnow().isoformat(),
                    "last_used_at": datetime.utcnow().isoformat(),
                })
                
                self.save_favorite_files()
                self.populate_favorites_tree()
                self.show_status_message(f"Dodano plik: {Path(file_path).name}", 3000)
    
    def load_available_groups(self):
        """Ładuje dostępne grupy z pliku słownika"""
        groups_file = Path("mail_client/file_groups.json")
        if groups_file.exists():
            try:
                with open(groups_file, 'r', encoding='utf-8') as f:
                    groups_data = json.load(f)
                    return [g['name'] for g in groups_data]
            except Exception:
                pass
        
        # Domyślne grupy
        return ["Dokumenty", "Faktury", "Projekty", "Obrazy", "Archiwum", "Ważne", "Bez grupy"]
    
    def manage_file_groups(self):
        """Otwiera okno zarządzania grupami plików"""
        from mail_client.file_list_dialog import FileGroupManagerDialog
        
        # Zbierz wszystkie grupy używane aktualnie
        current_groups = list(set(f.get('group', 'Bez grupy') for f in self.favorite_files))
        
        dialog = FileGroupManagerDialog(self, current_groups)
        if dialog.exec():
            # Po zamknięciu dialogu odśwież drzewo ulubionych
            self.populate_favorites_tree()
            self.show_status_message("Grupy zostały zaktualizowane", 2000)
    
    def on_favorite_item_clicked(self, item, column):
        """Zmienia tło sekcji ulubionych na kolor wybranej grupy"""
        # Sprawdź czy to element grupy (bez rodzica) czy plik
        if item.parent() is None:
            # To jest grupa
            group_text = item.text(0)
            # Wyciągnij nazwę grupy (usuń emoji)
            group_name = group_text.split(" ", 1)[1] if " " in group_text else group_text
            
            # Załaduj kolor grupy
            groups_file = Path("mail_client/file_groups.json")
            if groups_file.exists():
                try:
                    with open(groups_file, 'r', encoding='utf-8') as f:
                        groups_data = json.load(f)
                        for g in groups_data:
                            if g['name'] == group_name:
                                color = g.get('color', '#FFFFFF')
                                # Ustaw kolor tła dla całej sekcji ulubionych
                                from PyQt6.QtGui import QColor
                                qcolor = QColor(color)
                                # Jasny odcień koloru jako tło
                                qcolor.setAlpha(30)
                                rgb = qcolor.getRgb()
                                self.favorites_content.setStyleSheet(
                                    f"QWidget {{ background-color: rgba({rgb[0]}, {rgb[1]}, {rgb[2]}, {rgb[3]}); border-radius: 5px; }}"
                                )
                                return
                except Exception:
                    pass
        else:
            # To jest plik - pobierz kolor z grupy rodzica
            parent_item = item.parent()
            if parent_item:
                self.on_favorite_item_clicked(parent_item, column)
    
    def add_attachment_from_mail(self):
        """Dodaje załącznik z wybranego maila do ulubionych"""
        QMessageBox.information(
            self,
            "Info",
            "Ta funkcja pozwoli dodać załączniki z wybranego maila.\n\n"
            "Po implementacji obsługi prawdziwych załączników będzie działać."
        )
    
    def show_favorites_context_menu(self, pos):
        """Wyświetla menu kontekstowe dla ulubionych"""
        item = self.favorites_tree.itemAt(pos)
        if not item:
            return
        
        # Sprawdź czy to plik czy grupa
        file_data = item.data(0, Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        
        if file_data:  # To jest plik
            menu.addAction("📂 Otwórz", lambda: self.open_favorite_file(item, 0))
            menu.addAction("📁 Pokaż w folderze", lambda: self.show_in_folder(file_data))
            menu.addSeparator()
            menu.addAction("✏️ Zmień grupę", lambda: self.change_file_group(item))
            menu.addAction("🏷️ Edytuj tagi", lambda: self.edit_file_tags(item))
            menu.addSeparator()
            menu.addAction("❌ Usuń z ulubionych", lambda: self.remove_favorite(item))
        else:  # To jest grupa
            menu.addAction("✏️ Zmień nazwę grupy", lambda: self.rename_group(item))

        viewport = self.favorites_tree.viewport() if self.favorites_tree is not None else None
        if viewport is not None:
            menu.exec(viewport.mapToGlobal(pos))
    
    def open_favorite_file(self, item, column):
        """Otwiera ulubiony plik"""
        if item is None:
            return
        file_data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(file_data, dict):
            path = file_data.get("path", "")
            self._open_favorite_path(path)
            if path:
                self.mark_favorite_used(path)
    
    def show_in_folder(self, file_data):
        """Pokazuje plik w eksploratorze"""
        import subprocess
        path = file_data.get('path') if isinstance(file_data, dict) else None
        try:
            if path and os.path.exists(path):
                subprocess.run(['explorer', '/select,', path])
            else:
                QMessageBox.warning(self, "Błąd", "Plik nie istnieje!")
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można pokazać pliku: {e}")

    def mark_favorite_used(self, file_path: str) -> None:
        """Aktualizuje znacznik ostatniego użycia ulubionego pliku."""
        if not file_path:
            return

        normalized = os.path.normcase(os.path.abspath(file_path))
        updated = False
        for favorite in self.favorite_files:
            existing_path = favorite.get("path")
            if not existing_path:
                continue
            if os.path.normcase(os.path.abspath(existing_path)) == normalized:
                favorite["last_used_at"] = datetime.utcnow().isoformat()
                updated = True
                break

        if updated:
            self.save_favorite_files()
            self.populate_recent_favorites()

    def _open_favorite_path(self, file_path: str) -> None:
        """Uruchamia wskazany plik ulubiony."""
        if not file_path:
            return

        try:
            if os.path.exists(file_path):
                os.startfile(file_path)
            else:
                QMessageBox.warning(self, "Błąd", "Plik nie istnieje!")
        except Exception as exc:  # noqa: B902 - szeroka obsługa błędów w GUI
            QMessageBox.warning(self, "Błąd", f"Nie można otworzyć pliku: {exc}")

    def on_recent_favorite_double_clicked(self, item):
        """Otwiera plik z listy ostatnich ulubionych."""
        if item is None:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            path = data.get("path", "")
            self._open_favorite_path(path)
            if path:
                self.mark_favorite_used(path)
    def on_recent_favorite_double_clicked(self, item):
        """Otwiera plik z listy ostatnich ulubionych."""
        if item is None:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict):
            path = data.get("path", "")
            self._open_favorite_path(path)
            if path:
                self.mark_favorite_used(path)
    
    def change_file_group(self, item):
        """Zmienia grupę pliku"""
        file_data = item.data(0, Qt.ItemDataRole.UserRole)
        if file_data:
            current_group = file_data.get('group', 'Bez grupy')
            group, ok = QInputDialog.getText(
                self,
                "Zmień grupę",
                "Podaj nową nazwę grupy:",
                text=current_group
            )
            
            if ok:
                file_data['group'] = group if group else "Bez grupy"
                self.save_favorite_files()
                self.populate_favorites_tree()
    
    def edit_file_tags(self, item):
        """Edytuje tagi pliku"""
        file_data = item.data(0, Qt.ItemDataRole.UserRole)
        if file_data:
            current_tags = ", ".join(file_data.get('tags', []))
            tags_str, ok = QInputDialog.getText(
                self,
                "Edytuj tagi",
                "Podaj tagi oddzielone przecinkami:",
                text=current_tags
            )
            
            if ok:
                file_data['tags'] = [t.strip() for t in tags_str.split(",") if t.strip()]
                self.save_favorite_files()
                self.populate_favorites_tree()
    
    def remove_favorite(self, item):
        """Usuwa plik z ulubionych"""
        file_data = item.data(0, Qt.ItemDataRole.UserRole)
        if file_data:
            reply = QMessageBox.question(
                self,
                "Potwierdzenie",
                f"Czy na pewno chcesz usunąć '{file_data['name']}' z ulubionych?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.favorite_files.remove(file_data)
                self.save_favorite_files()
                self.populate_favorites_tree()
    
    def rename_group(self, item):
        """Zmienia nazwę grupy"""
        old_name = item.text(0).replace("📂 ", "")
        new_name, ok = QInputDialog.getText(
            self,
            "Zmień nazwę grupy",
            "Podaj nową nazwę grupy:",
            text=old_name
        )
        
        if ok and new_name:
            # Zaktualizuj wszystkie pliki w tej grupie
            for file in self.favorite_files:
                if file.get('group') == old_name:
                    file['group'] = new_name
            
            self.save_favorite_files()
            self.populate_favorites_tree()
        
    def prepare_mail_objects(self) -> None:
        """Uzupełnia metadane wiadomości o folder i identyfikator."""
        for folder_name, mails in self.sample_mails.items():
            for mail in mails:
                mail["_folder"] = folder_name
                self.ensure_mail_uid(mail)
        
        # Ogranicz maile w pamięci
        self.limit_mails_in_memory()

    def generate_sample_mails(self):
        """Generuje przykładowe wiadomości"""
        return {
            "Odebrane": [
                {
                    "from": "jan.kowalski@firma.pl",
                    "subject": "Raport miesięczny - Październik 2025",
                    "date": "2025-11-05 14:32",
                    "size": "245 KB",
                    "body": "Witaj,\n\nW załączeniu przesyłam raport miesięczny za październik 2025.\n\nPozdrawiam,\nJan Kowalski",
                    "starred": True,
                    "tag": "Finanse",
                    "tags": ["Finanse"],
                    "conversation_count": 3,
                    "note": "Sprawdź załączniki przed końcem dnia.",
                    "attachments": [
                        {
                            "filename": "Raport_pazdziernik_2025.pdf",
                            "size": 245760,
                            "data": b"",  # Pusty dla przykładowych danych
                            "content_type": "application/pdf"
                        }
                    ]
                },
                {
                    "from": "anna.nowak@email.com",
                    "subject": "Spotkanie w przyszły wtorek",
                    "date": "2025-11-05 10:15",
                    "size": "12 KB",
                    "body": "Cześć,\n\nCzy moglibyśmy się spotkać w przyszły wtorek o 15:00?\n\nPozdrawiam,\nAnna",
                    "starred": False,
                    "tag": "Klient",
                    "tags": ["Klient"],
                    "conversation_count": 2,
                    "note": "Przygotuj agendę spotkania."
                },
                {
                    "from": "biuro@sklep.pl",
                    "subject": "Twoje zamówienie zostało wysłane",
                    "date": "2025-11-04 16:45",
                    "size": "8 KB",
                    "body": "Dzień dobry,\n\nTwoje zamówienie #12345 zostało wysłane.\nNumer przesyłki: 1234567890\n\nPozdrawiamy",
                    "starred": False,
                    "tag": "Newsletter",
                    "tags": ["Newsletter"],
                    "conversation_count": 1,
                    "note": "Sprawdź status przesyłki jutro."
                },
                {
                    "from": "newsletter@tech.com",
                    "subject": "Najnowsze technologie w AI",
                    "date": "2025-11-04 08:00",
                    "size": "156 KB",
                    "body": "Witaj,\n\nW tym wydaniu newslettera:\n- Najnowsze modele językowe\n- Przyszłość AI w biznesie\n- Automatyzacja procesów\n\nZapraszamy do lektury!",
                    "starred": False,
                    "tag": "Newsletter",
                    "tags": ["Newsletter"],
                    "conversation_count": 5,
                    "note": "Prześlij artykuł do zespołu R&D.",
                    "attachments": [
                        {
                            "filename": "AI_trends_2025.pdf",
                            "size": 102400,
                            "data": b"",
                            "content_type": "application/pdf"
                        },
                        {
                            "filename": "automation_guide.docx",
                            "size": 51200,
                            "data": b"",
                            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                        }
                    ]
                },
            ],
            "Wysłane": [
                {
                    "from": "ja@mojmail.pl",
                    "subject": "Re: Spotkanie projektowe",
                    "date": "2025-11-05 09:00",
                    "size": "15 KB",
                    "body": "Potwierdzam udział w spotkaniu.\n\nPozdrawiam",
                    "starred": True,
                    "tag": "Priorytet",
                    "tags": ["Priorytet"],
                    "conversation_count": 4,
                    "note": "Wyślij podsumowanie po spotkaniu."
                },
            ],
            "Szkice": [
                {
                    "from": "ja@mojmail.pl",
                    "subject": "(brak tematu)",
                    "date": "2025-11-04 20:30",
                    "size": "2 KB",
                    "body": "Rozpoczęta wiadomość...",
                    "starred": False,
                    "tag": "",
                    "tags": [],
                    "conversation_count": 1,
                    "note": "Do uzupełnienia i wysłania jutro."
                },
            ]
        }
        
    def load_folder_mails(self, folder_name):
        """Ładuje maile z wybranego folderu"""
        # Sprawdź czy interfejs jest w pełni zainicjalizowany
        if not hasattr(self, 'folder_label') or not hasattr(self, 'mail_list'):
            return
        
        # Usuń emoji z nazwy folderu
        clean_folder = folder_name.split()[1] if len(folder_name.split()) > 1 else folder_name
        clean_folder = clean_folder.split('(')[0].strip()
        
        self.current_folder = clean_folder
        self.folder_label.setText(clean_folder)
        
        # Przygotuj filtry
        self.mail_scope = "folder"
        self.set_mail_filter_controls_enabled(True)
        if clean_folder == "Ulubione":
            mails_source = self.get_starred_mails()
        else:
            mails_source = self.sample_mails.get(clean_folder, [])
        
        # Filtruj według wybranego konta
        selected_account = None
        if hasattr(self, "account_filter_combo"):
            selected_account = self.account_filter_combo.currentData()
        
        self.current_folder_mails = []
        for mail in mails_source:
            if selected_account is None:  # "Wszystkie"
                self.current_folder_mails.append(mail)
            elif mail.get("_account") == selected_account:
                self.current_folder_mails.append(mail)
        
        for mail in self.current_folder_mails:
            if clean_folder != "Ulubione":
                mail["_folder"] = self.current_folder
            self.ensure_mail_uid(mail)
        self.apply_mail_filters()
        self.clear_mail_view()
        if clean_folder == "Ulubione":
            self.update_favorites_folder_item()
    
    def load_imap_folder_mails(self, folder_name: str, account_email: str):
        """Ładuje maile z folderu IMAP"""
        # Sprawdź czy interfejs jest w pełni zainicjalizowany
        if not hasattr(self, 'folder_label') or not hasattr(self, 'mail_list'):
            return
        
        self.current_folder = folder_name
        self.folder_label.setText(f"📁 {folder_name}")
        
        # TODO: Implementacja pobierania maili z konkretnego folderu IMAP
        # Na razie wyświetl placeholder
        self.mail_scope = "folder"
        self.set_mail_filter_controls_enabled(True)
        
        # Sprawdź czy mamy już maile z tego folderu
        mails_source = self.sample_mails.get(folder_name, [])
        
        self.current_folder_mails = []
        for mail in mails_source:
            if mail.get("_account") == account_email:
                self.current_folder_mails.append(mail)
                mail["_folder"] = folder_name
                self.ensure_mail_uid(mail)
        
        self.apply_mail_filters()
        self.clear_mail_view()
        
        # Jeśli brak maili, pokaż komunikat
        if not self.current_folder_mails:
            self.show_status_message(f"Folder {folder_name} jest pusty lub nie został jeszcze zsynchronizowany")
    
    def load_smart_folder_mails(self, smart_folder_name: str):
        """Ładuje maile z inteligentnego folderu"""
        # Sprawdź czy interfejs jest w pełni zainicjalizowany
        if not hasattr(self, 'folder_label') or not hasattr(self, 'mail_list'):
            return
        
        self.current_folder = smart_folder_name
        self.folder_label.setText(f"🔥 {smart_folder_name}")
        
        # Ustaw zakres i pobierz maile
        self.mail_scope = "smart"
        self.set_mail_filter_controls_enabled(False)  # Inteligentne foldery mają swoje własne filtry
        
        # Pobierz maile z inteligentnego folderu
        mails = self.get_smart_folder_mails(smart_folder_name)
        
        # Filtruj według wybranego konta
        selected_account = None
        if hasattr(self, "account_filter_combo"):
            selected_account = self.account_filter_combo.currentData()
        
        self.current_folder_mails = []
        for mail in mails:
            if selected_account is None:  # "Wszystkie"
                self.current_folder_mails.append(mail)
            elif mail.get("_account") == selected_account:
                self.current_folder_mails.append(mail)
        
        # Zapewnij UID dla każdego maila
        for mail in self.current_folder_mails:
            self.ensure_mail_uid(mail)
        
        # Wyświetl maile
        self.populate_mail_table(self.current_folder_mails)
        self.clear_mail_view()
        
    def load_conversation_mails(self, subject_item):
        """Ładuje wszystkie maile z konwersacji do listy"""
        mails = []
        for i in range(subject_item.childCount()):
            child = subject_item.child(i)
            mail_data = child.data(0, Qt.ItemDataRole.UserRole)
            if mail_data:
                mails.append(mail_data)
        
        self.mail_scope = "custom"
        self.set_mail_filter_controls_enabled(False)
        self.populate_mail_table(mails)
    
    def load_tree_branch_mails(self, item):
        """Ładuje wszystkie maile z gałęzi drzewa (kontakt lub temat)"""
        mails = []
        
        # Rekurencyjnie zbierz wszystkie maile z poddrzewa
        def collect_mails(tree_item):
            for i in range(tree_item.childCount()):
                child = tree_item.child(i)
                mail_data = child.data(0, Qt.ItemDataRole.UserRole)
                if mail_data:
                    mails.append(mail_data)
                else:
                    collect_mails(child)
        
        collect_mails(item)
        
        # Wypełnij tabelę
        if mails:
            self.mail_scope = "custom"
            self.set_mail_filter_controls_enabled(False)
            self.populate_mail_table(mails)
            self.current_mail = mails[0]
            self.display_mail(mails[0])
        
    def on_folder_clicked(self, item, column):
        """Obsługa kliknięcia w folder, kontakt lub wątek"""
        if self.view_mode == "folders":
            # Sprawdź typ elementu
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data:
                item_type = item_data.get("type")
                item_name = item_data.get("name")
                
                # Pomiń kliknięcia w sekcje nagłówków
                if item_type == "section":
                    return
                
                # Obsługa inteligentnych folderów
                if item_type == "smart_folder":
                    self.load_smart_folder_mails(item_name)
                    self.show_status_message(f"Inteligentny folder: {item_name}")
                    return
                
                # Obsługa zwykłych folderów
                if item_type == "folder":
                    self.load_folder_mails(item_name)
                    self.show_status_message(f"Folder: {item_name}")
                    return
                
                # Obsługa folderów IMAP
                if item_type == "imap_folder":
                    account_email = item_data.get("account")
                    self.load_imap_folder_mails(item_name, account_email)
                    self.show_status_message(f"Folder IMAP: {item_name}")
                    return
            
            # Fallback - stary sposób (jeśli UserRole nie jest ustawiony)
            folder_name = item.text(0)
            self.load_folder_mails(folder_name)
            self.show_status_message(f"Folder: {folder_name}")
        
        elif self.view_mode == "threads":
            # W widoku wątków
            item_data = item.data(0, Qt.ItemDataRole.UserRole)
            if item_data:
                if isinstance(item_data, dict):
                    # Kliknięto konkretną wiadomość
                    if "subject" in item_data and "from" in item_data:
                        self.current_mail = item_data
                        self.display_mail(item_data)
                        # Załaduj cały wątek
                        parent = item.parent()
                        if parent:
                            self.load_conversation_mails(parent)
                    # Kliknięto nagłówek wątku
                    elif item_data.get("type") == "thread":
                        self.load_conversation_mails(item)
            else:
                # Kliknięto nagłówek wątku - pokaż wszystkie maile
                self.load_conversation_mails(item)
        
        else:  # view_mode == "contacts"
            # W widoku kontaktów - sprawdź czy kliknięto mail
            mail_data = item.data(0, Qt.ItemDataRole.UserRole)
            if mail_data:
                # Kliknięto konkretną wiadomość
                self.current_mail = mail_data
                self.display_mail(mail_data)
                # Opcjonalnie załaduj wszystkie maile z tej konwersacji
                parent = item.parent()
                if parent:
                    self.load_conversation_mails(parent)
            else:
                # Kliknięto kontakt lub temat - pokaż wszystkie maile
                self.load_tree_branch_mails(item)
        
    def on_mail_clicked(self, row, column):
        """Obsługa kliknięcia w mail"""
        # Zapisz aktywność użytkownika
        self._last_user_activity = datetime.now()
        
        if not (0 <= row < len(self.displayed_mails)):
            return

        mail = self.displayed_mails[row]

        # Sprawdź czy kliknięto w emoji z akcją (kolumny 3 lub 4)
        item = self.mail_list.item(row, column)
        if item and item.data(Qt.ItemDataRole.UserRole):
            action_data = item.data(Qt.ItemDataRole.UserRole)
            if action_data.get("action") == "reply":
                self.reply_to_mail(action_data["mail"])
                return
            elif action_data.get("action") == "expand":
                self.toggle_mail_preview(action_data["row"])
                return

        # Sprawdź czy kliknięto w kolumnę gwiazdki
        if not hasattr(self, 'column_order'):
            self.column_order = list(range(12))
        
        # Znajdź logiczny indeks kolumny na podstawie wizualnego indeksu
        logical_col_idx = self.column_order[column] if column < len(self.column_order) else -1
        
        if logical_col_idx == 0:  # Gwiazdka
            self.current_mail = mail
            new_state = self.toggle_mail_star(row, mail)
            if new_state is not None:
                self.show_status_message(
                    "Dodano gwiazdkę" if new_state else "Usunięto gwiazdkę",
                    1500,
                )
            return
        
        # Jeśli kliknięto w kolumnę wątków i są włączone wątki
        if logical_col_idx == 8 and self.threads_enabled and mail.get("_is_thread_parent"):
            thread_count = mail.get("_thread_count", 1)
            if thread_count > 1:
                # Pokaż dialog z wszystkimi mailami w wątku
                self.show_thread_dialog(mail)
                return

        self.current_mail = mail
        self.display_mail(mail)
            
    def display_mail(self, mail):
        """Wyświetla treść wybranego maila"""
        self.mail_subject.setText(mail["subject"])
        self.mail_from.setText(f"Od: {mail['from']}")
        self.mail_to.setText(f"Do: ja@mojmail.pl")
        self.mail_date.setText(f"Data: {mail['date']}")
        
        # Wypełnij combobox tagów
        self.mail_tag_selector.blockSignals(True)  # Blokuj sygnały podczas wypełniania
        self.mail_tag_selector.clear()
        self.mail_tag_selector.addItem("-- Wybierz tag --", None)
        
        # Dodaj wszystkie dostępne tagi (mail_tags to lista słowników)
        if isinstance(self.mail_tags, list):
            for tag_data in self.mail_tags:
                if isinstance(tag_data, dict):
                    tag_name = tag_data.get("name", "")
                    if tag_name:
                        self.mail_tag_selector.addItem(tag_name, tag_name)
        
        # Zaznacz aktualnie przypisane tagi (jeśli są)
        current_tags = self.get_mail_tags(mail)
        if current_tags:
            # Ustaw pierwszy tag jako wybrany
            index = self.mail_tag_selector.findData(current_tags[0])
            if index >= 0:
                self.mail_tag_selector.setCurrentIndex(index)
        
        self.mail_tag_selector.blockSignals(False)
        
        # Stary label tagów - możemy go ukryć lub zostawić jako podgląd
        tags = self.get_mail_tags(mail)
        if tags:
            self.mail_tag_label.setText(f"Tagi: {', '.join(tags)}")
        else:
            self.mail_tag_label.setText("Tagi:")

        note_text = mail.get("note", "")
        if note_text:
            self.mail_note_label.setText(f"Notatka: {note_text}")
        else:
            self.mail_note_label.setText("")
        
        # Sanityzuj treść przed wyświetleniem (zapobiega XSS)
        body_text = mail.get("body", "")
        safe_body = self.sanitize_html(body_text)
        self.mail_body.setPlainText(safe_body)
        
        # Wyświetl załączniki
        self.display_attachments(mail.get("attachments", []))
    
    def display_attachments(self, attachments):
        """Wyświetla listę załączników"""
        # Wyczyść poprzednie załączniki
        while self.attachments_layout.count():
            child = self.attachments_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        if not attachments:
            self.attachments_toggle_btn.hide()
            self.attachments_container.hide()
            return
        
        # Pokaż przycisk z liczbą załączników
        count = len(attachments)
        self.attachments_toggle_btn.setText(f"▶️ Załączniki ({count})")
        self.attachments_toggle_btn.show()
        self.attachments_toggle_btn.setChecked(False)  # Domyślnie zwinięte
        self.attachments_container.hide()
        
        for attachment in attachments:
            att_widget = QWidget()
            att_layout = QHBoxLayout(att_widget)
            att_layout.setContentsMargins(5, 2, 5, 2)
            
            # Ikona pliku
            icon_label = QLabel("📄")
            att_layout.addWidget(icon_label)
            
            # Nazwa i rozmiar
            filename = attachment.get("filename", "unknown")
            size_bytes = attachment.get("size", 0)
            size_kb = size_bytes / 1024
            if size_kb < 1024:
                size_str = f"{size_kb:.1f} KB"
            else:
                size_str = f"{size_kb/1024:.1f} MB"
            
            info_label = QLabel(f"{filename} ({size_str})")
            info_label.setStyleSheet("color: #333;")
            att_layout.addWidget(info_label)
            att_layout.addStretch()
            
            # Przycisk Zapisz
            save_btn = QPushButton("💾 Zapisz")
            save_btn.setFixedWidth(100)
            save_btn.clicked.connect(lambda checked, att=attachment: self.save_attachment(att))
            att_layout.addWidget(save_btn)
            
            # Przycisk Otwórz
            open_btn = QPushButton("📂 Otwórz")
            open_btn.setFixedWidth(100)
            open_btn.clicked.connect(lambda checked, att=attachment: self.open_attachment(att))
            att_layout.addWidget(open_btn)
            
            self.attachments_layout.addWidget(att_widget)
    
    def show_thread_dialog(self, parent_mail):
        """Pokazuje dialog z wszystkimi mailami w wątku"""
        thread_id = parent_mail.get("_thread_id")
        if not thread_id:
            return
        
        thread_mails = self.get_thread_mails(thread_id)
        if not thread_mails:
            return
        
        # Utwórz dialog
        dialog = QDialog(self)
        dialog.setWindowTitle(f"Wątek konwersacji - {parent_mail.get('subject', '(brak tematu)')}")
        dialog.setMinimumWidth(800)
        dialog.setMinimumHeight(600)
        
        layout = QVBoxLayout(dialog)
        
        # Nagłówek z informacjami o wątku
        header = QLabel(f"📧 {len(thread_mails)} wiadomości w wątku")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 5px; background-color: #E3F2FD;")
        layout.addWidget(header)
        
        # Lista maili w wątku
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setSpacing(10)
        
        # Dodaj każdy mail w wątku
        for i, mail in enumerate(thread_mails):
            mail_frame = QFrame()
            mail_frame.setFrameShape(QFrame.Shape.StyledPanel)
            mail_frame.setStyleSheet("""
                QFrame {
                    background-color: white;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    padding: 10px;
                }
                QFrame:hover {
                    border-color: #0066CC;
                }
            """)
            
            mail_layout = QVBoxLayout(mail_frame)
            
            # Nagłówek maila
            from_address = mail.get("from", "")
            email_only = self.extract_email_address(from_address)
            name = self.extract_display_name(from_address) or email_only
            
            header_layout = QHBoxLayout()
            
            # Numer w wątku
            num_label = QLabel(f"#{i+1}")
            num_label.setStyleSheet("font-weight: bold; color: #0066CC; min-width: 30px;")
            header_layout.addWidget(num_label)
            
            # Od kogo
            from_label = QLabel(f"📤 {name}")
            from_label.setStyleSheet("font-weight: bold;")
            header_layout.addWidget(from_label)
            
            header_layout.addStretch()
            
            # Data
            date_label = QLabel(mail.get("date", ""))
            date_label.setStyleSheet("color: #666;")
            header_layout.addWidget(date_label)
            
            # Gwiazdka jeśli jest
            if mail.get("starred"):
                star_label = QLabel("⭐")
                header_layout.addWidget(star_label)
            
            mail_layout.addLayout(header_layout)
            
            # Temat (jeśli różni się od głównego)
            subject = mail.get("subject", "")
            if subject and subject != parent_mail.get("subject", ""):
                subject_label = QLabel(f"Temat: {subject}")
                subject_label.setStyleSheet("font-style: italic; color: #555;")
                mail_layout.addWidget(subject_label)
            
            # Podgląd treści
            body = mail.get("body", "")
            preview = body[:200] + "..." if len(body) > 200 else body
            body_label = QLabel(preview)
            body_label.setWordWrap(True)
            body_label.setStyleSheet("color: #333; margin-top: 5px;")
            mail_layout.addWidget(body_label)
            
            # Załączniki
            attachments = mail.get("attachments", [])
            if attachments:
                att_label = QLabel(f"📎 {len(attachments)} załącznik(ów)")
                att_label.setStyleSheet("color: #FF8C00; margin-top: 5px;")
                mail_layout.addWidget(att_label)
            
            # Przyciski akcji
            btn_layout = QHBoxLayout()
            btn_layout.addStretch()
            
            view_btn = QPushButton("👁️ Pokaż pełną treść")
            view_btn.clicked.connect(lambda checked, m=mail: (dialog.close(), self.display_mail(m)))
            btn_layout.addWidget(view_btn)
            
            reply_btn = QPushButton("↩️ Odpowiedz")
            reply_btn.clicked.connect(lambda checked, m=mail: (dialog.close(), self.reply_to_mail(m)))
            btn_layout.addWidget(reply_btn)
            
            mail_layout.addLayout(btn_layout)
            content_layout.addWidget(mail_frame)
        
        content_layout.addStretch()
        scroll.setWidget(content_widget)
        layout.addWidget(scroll)
        
        # Przyciski zamknięcia
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)
        
        dialog.exec()
    
    def save_attachment(self, attachment):
        """Zapisuje załącznik do pliku"""
        filename = attachment.get("filename", "attachment")
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz załącznik",
            filename,
            "Wszystkie pliki (*.*)"
        )
        
        if filepath:
            try:
                with open(filepath, "wb") as f:
                    f.write(attachment.get("data", b""))
                QMessageBox.information(self, "Sukces", f"Załącznik zapisany:\n{filepath}")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie można zapisać załącznika:\n{str(e)}")
    
    def open_attachment(self, attachment):
        """Otwiera załącznik w domyślnej aplikacji"""
        import tempfile
        import os
        import subprocess
        
        filename = attachment.get("filename", "attachment")
        temp_dir = tempfile.gettempdir()
        temp_path = os.path.join(temp_dir, filename)
        
        try:
            # Zapisz do pliku tymczasowego
            with open(temp_path, "wb") as f:
                f.write(attachment.get("data", b""))
            
            # Otwórz w domyślnej aplikacji
            if sys.platform == "win32":
                os.startfile(temp_path)
            elif sys.platform == "darwin":
                subprocess.run(["open", temp_path])
            else:
                subprocess.run(["xdg-open", temp_path])
                
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można otworzyć załącznika:\n{str(e)}")
        
    def clear_mail_view(self):
        """Czyści podgląd maila"""
        self.mail_subject.setText("(Wybierz wiadomość)")
        self.mail_from.setText("")
        self.mail_to.setText("")
        self.mail_date.setText("")
        self.mail_tag_label.setStyleSheet("color: #555;")
        self.mail_tag_label.setText("")
        self.mail_note_label.setText("")
        self.mail_body.clear()
        self.display_attachments([])  # Wyczyść załączniki
        self.current_mail = None
        
    def show_mail_context_menu(self, pos):
        """Wyświetla menu kontekstowe dla maila"""
        if not hasattr(self, "mail_list"):
            return

        index = self.mail_list.indexAt(pos)
        if index.isValid():
            row = index.row()
            if 0 <= row < len(self.displayed_mails):
                self.mail_list.selectRow(row)
                self.current_mail = self.displayed_mails[row]
                self.display_mail(self.current_mail)
        elif not self.current_mail:
            return

        menu = QMenu(self)

        menu.addAction("📧 Nowy mail", self.new_mail)
        menu.addSeparator()
        menu.addAction("↩️ Odpowiedz", self.reply_mail)
        menu.addAction("➡️ Przekaż", self.forward_mail)
        menu.addSeparator()
        menu.addAction("⭐ Oznacz", self.mark_mail)
        menu.addAction("📁 Przenieś do...", self.move_mail)
        menu.addSeparator()
        menu.addAction("🗑️ Usuń", self.delete_mail)

        viewport = self.mail_list.viewport()
        if viewport is not None:
            menu.exec(viewport.mapToGlobal(pos))
        
    # === AKCJE ===
    
    def new_mail(self):
        """Otwiera okno nowej wiadomości"""
        try:
            from new_mail_window import NewMailWindow
        except ImportError:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from new_mail_window import NewMailWindow
        window = NewMailWindow(self)
        window.exec()
        
    def reply_mail(self):
        """Odpowiada na wiadomość"""
        if self.current_mail:
            self.reply_to_mail(self.current_mail)
        else:
            QMessageBox.information(self, "Info", "Wybierz wiadomość do odpowiedzi")
    
    def reply_to_mail(self, mail):
        """Odpowiada na konkretną wiadomość"""
        try:
            from new_mail_window import NewMailWindow
        except ImportError:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from new_mail_window import NewMailWindow
        window = NewMailWindow(self, reply_to=mail)
        window.exec()
            
    def forward_mail(self):
        """Przekazuje wiadomość"""
        if self.current_mail:
            try:
                from new_mail_window import NewMailWindow
            except ImportError:
                import sys
                import os
                sys.path.insert(0, os.path.dirname(__file__))
                from new_mail_window import NewMailWindow
            window = NewMailWindow(self, forward=self.current_mail)
            window.exec()
        else:
            QMessageBox.information(self, "Info", "Wybierz wiadomość do przekazania")
            
    def delete_mail(self):
        """Usuwa wiadomość"""
        if self.current_mail is None:
            QMessageBox.information(self, "Info", "Wybierz wiadomość do usunięcia")
            return

        mail = self.current_mail
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            "Czy na pewno chcesz usunąć tę wiadomość?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        source_folder = mail.get("_folder")
        uid = self.ensure_mail_uid(mail)

        if source_folder == "Kosz":
            if source_folder and source_folder in self.sample_mails:
                try:
                    self.sample_mails[source_folder].remove(mail)
                except ValueError:
                    pass
            self.mail_uid_map.pop(uid, None)
            self.current_folder_mails = [m for m in self.current_folder_mails if m is not mail]
            self.displayed_mails = [m for m in self.displayed_mails if m is not mail]

            if self.mail_scope == "folder":
                current_folder = getattr(self, "current_folder", None)
                self.populate_folders_tree()
                if current_folder and self.find_folder_item(current_folder):
                    self.select_folder_by_name(current_folder)
                elif self.tree.topLevelItemCount() > 0:
                    first_item = self.tree.topLevelItem(0)
                    if first_item is not None:
                        self.tree.setCurrentItem(first_item)
                        self.load_folder_mails(first_item.text(0))
                else:
                    if hasattr(self, "mail_list"):
                        self.mail_list.setRowCount(0)
                    self.clear_mail_view()
            else:
                self.populate_mail_table(self.displayed_mails)
                if self.view_mode == "contacts":
                    self.populate_contacts_tree()

            self.clear_mail_view()
            self.current_mail = None
            self.show_status_message("Wiadomość usunięta na stałe", 3000)
            return

        moved = self.handle_mail_drop(uid, "Kosz")
        if moved:
            if self.mail_scope != "folder":
                self.displayed_mails = [m for m in self.displayed_mails if m is not mail]
                self.populate_mail_table(self.displayed_mails)
                if self.view_mode == "contacts":
                    self.populate_contacts_tree()
            self.clear_mail_view()
            self.current_mail = None
            self.show_status_message("Przeniesiono wiadomość do kosza.", 3000)
            
    def mark_mail(self):
        """Oznacza wiadomość"""
        if self.current_mail:
            try:
                row = self.displayed_mails.index(self.current_mail)
            except ValueError:
                row = -1
            new_state = self.toggle_mail_star(row) if row >= 0 else None
            if new_state is None:
                new_state = not self.current_mail.get("starred", False)
                self.current_mail["starred"] = new_state
                if self.mail_scope == "folder":
                    self.apply_mail_filters()
                else:
                    self.populate_mail_table(self.displayed_mails)
                self.update_favorites_folder_item()
            self.show_status_message(
                "Dodano gwiazdkę" if new_state else "Usunięto gwiazdkę",
                2000,
            )
            
    def move_mail(self):
        """Przenosi wiadomość do innego folderu"""
        if self.current_mail is None:
            QMessageBox.information(self, "Info", "Wybierz wiadomość do przeniesienia")
            return

        mail = self.current_mail
        available_folders = sorted(name for name in self.sample_mails.keys() if name != "Ulubione")
        if not available_folders:
            QMessageBox.warning(self, "Brak folderów", "Nie znaleziono żadnych folderów docelowych.")
            return

        source_folder = mail.get("_folder")
        initial_index = available_folders.index(source_folder) if source_folder in available_folders else 0
        target_folder, ok = QInputDialog.getItem(
            self,
            "Przenieś wiadomość",
            "Wybierz folder docelowy:",
            available_folders,
            initial_index,
            False,
        )

        if not ok or not target_folder:
            return

        if target_folder == source_folder:
            self.show_status_message("Wiadomość już znajduje się w tym folderze.", 2500)
            return

        uid = self.ensure_mail_uid(mail)
        moved = self.handle_mail_drop(uid, target_folder)
        if moved:
            if self.mail_scope != "folder":
                self.displayed_mails = [m for m in self.displayed_mails if m is not mail]
                self.populate_mail_table(self.displayed_mails)
            self.current_mail = None
            self.clear_mail_view()

    def refresh_mails(self):
        """Odświeża listę wiadomości"""
        self.show_status_message("Odświeżanie wiadomości...", 0)
        self.fetch_real_emails_async()
        self.prepare_mail_objects()

        if self.view_mode == "folders":
            current_folder = getattr(self, "current_folder", None)
            self.populate_folders_tree()
            if current_folder and self.find_folder_item(current_folder):
                self.select_folder_by_name(current_folder)
            elif self.tree.topLevelItemCount() > 0:
                first_item = self.tree.topLevelItem(0)
                if first_item is not None:
                    self.tree.setCurrentItem(first_item)
                    self.load_folder_mails(first_item.text(0))
            else:
                if hasattr(self, "mail_list"):
                    self.mail_list.setRowCount(0)
                self.clear_mail_view()
        else:
            self.populate_contacts_tree()
            if self.displayed_mails:
                self.populate_mail_table(self.displayed_mails)
            elif hasattr(self, "mail_list"):
                self.mail_list.setRowCount(0)
                self.mail_list.clearContents()

        self.show_status_message("Wiadomości zostały odświeżone.", 2000)
    
    def auto_refresh_mails(self):
        """Automatyczne odświeżanie poczty (wywoływane przez timer)"""
        # Debounce: nie odświeżaj jeśli użytkownik aktywnie pracuje
        time_since_activity = (datetime.now() - self._last_user_activity).seconds
        if time_since_activity < 30:  # 30 sekund od ostatniej aktywności
            self.show_status_message("Odświeżanie odłożone - wykryto aktywność użytkownika", 2000)
            return
        
        self.show_status_message("Automatyczne odświeżanie poczty...", 2000)
        self.refresh_mails()
        
        # Opcjonalnie: przetwórz nowe maile przez autoresponder
        # (tutaj można dodać logikę sprawdzania nowych maili i wysyłania odpowiedzi)
    
    def open_autoresponder_dialog(self):
        """Otwiera dialog konfiguracji autorespondera - karta Autoresponder"""
        self.open_config(tab_index=2)  # Karta 2: Autoresponder (0=Podpisy, 1=Filtry, 2=Autoresponder)

    def fetch_real_emails_async(self):
        """Pobiera maile z IMAP w tle"""
        # Zamknij poprzedni wątek jeśli istnieje (zapobiega memory leak)
        if hasattr(self, 'email_fetcher') and self.email_fetcher is not None:
            try:
                if self.email_fetcher.isRunning():
                    self.email_fetcher.quit()
                    self.email_fetcher.wait(1000)  # Czekaj max 1 sekundę
            except RuntimeError:
                pass  # Wątek już zakończony
        
        from PyQt6.QtCore import QThread, pyqtSignal

        class EmailFetcher(QThread):
            finished = pyqtSignal(dict)

            def __init__(self, accounts):
                super().__init__()
                self.accounts = accounts

            def run(self):
                result = {}
                for account in self.accounts:
                    try:
                        mails = self.fetch_from_account(account)
                        if mails:
                            result[account.get("email", "Unknown")] = mails
                    except Exception:
                        pass
                self.finished.emit(result)

            def fetch_from_account(self, account):
                """Pobiera maile z pojedynczego konta"""
                try:
                    if account.get("imap_ssl"):
                        imap = imaplib.IMAP4_SSL(
                            account["imap_server"],
                            account.get("imap_port", 993),
                            timeout=15
                        )
                    else:
                        imap = imaplib.IMAP4(
                            account["imap_server"],
                            account.get("imap_port", 143),
                            timeout=15
                        )

                    imap.login(account["email"], account["password"])
                    
                    # Pobierz listę folderów IMAP
                    try:
                        status, folder_list = imap.list()
                        if status == "OK":
                            imap_folders = []
                            for folder_line in folder_list:
                                # Parsuj linię folderu: b'(\\HasNoChildren) "/" "INBOX"'
                                if isinstance(folder_line, bytes):
                                    folder_line = folder_line.decode('utf-8', errors='ignore')
                                # Wyciągnij nazwę folderu (ostatnia część w cudzysłowach)
                                import re
                                match = re.search(r'"([^"]+)"$', folder_line)
                                if match:
                                    folder_name = match.group(1)
                                    imap_folders.append(folder_name)
                            
                            # Zapisz foldery dla tego konta
                            self.imap_folders[account.get("email")] = imap_folders
                    except Exception as e:
                        logger.warning(f"Nie udało się pobrać listy folderów IMAP: {e}")
                        self.imap_folders[account.get("email")] = ["INBOX"]
                    
                    imap.select("INBOX")

                    # Pobierz maile (liczba z ustawień konta)
                    fetch_limit = account.get("fetch_limit", 50)
                    _, messages = imap.search(None, "ALL")
                    email_ids = messages[0].split()
                    email_ids = email_ids[-fetch_limit:] if len(email_ids) > fetch_limit else email_ids

                    mails = []
                    for email_id in reversed(email_ids):
                        try:
                            _, msg_data = imap.fetch(email_id, "(RFC822)")
                            email_body = msg_data[0][1]
                            message = email.message_from_bytes(email_body)

                            subject = self.decode_email_header(message.get("Subject", ""))
                            from_addr = self.decode_email_header(message.get("From", ""))
                            date_str = message.get("Date", "")
                            
                            # Parsuj datę
                            try:
                                from email.utils import parsedate_to_datetime
                                date_obj = parsedate_to_datetime(date_str)
                                formatted_date = date_obj.strftime("%Y-%m-%d %H:%M")
                            except Exception:
                                formatted_date = date_str[:16] if len(date_str) > 16 else date_str

                            # Pobierz treść i załączniki
                            body = ""
                            attachments = []
                            
                            if message.is_multipart():
                                for part in message.walk():
                                    content_type = part.get_content_type()
                                    content_disposition = str(part.get("Content-Disposition", ""))
                                    
                                    # Treść tekstowa
                                    if content_type == "text/plain" and "attachment" not in content_disposition:
                                        if not body:
                                            try:
                                                body = part.get_payload(decode=True).decode("utf-8", errors="ignore")
                                            except Exception:
                                                pass
                                    
                                    # Załączniki
                                    elif "attachment" in content_disposition or part.get_filename():
                                        filename = part.get_filename()
                                        if filename:
                                            filename = self.decode_email_header(filename)
                                            try:
                                                attachment_data = part.get_payload(decode=True)
                                                attachments.append({
                                                    "filename": filename,
                                                    "size": len(attachment_data),
                                                    "data": attachment_data,
                                                    "content_type": content_type
                                                })
                                            except Exception:
                                                pass
                            else:
                                try:
                                    body = message.get_payload(decode=True).decode("utf-8", errors="ignore")
                                except Exception:
                                    body = str(message.get_payload())

                            mails.append({
                                "subject": subject or "(Bez tematu)",
                                "from": from_addr,
                                "date": formatted_date,
                                "body": body[:500],  # Tylko początek
                                "size": f"{len(email_body) // 1024} KB",
                                "starred": False,
                                "conversation_count": 1,
                                "_folder": "Odebrane",
                                "_account": account.get("email"),
                                "attachments": attachments,
                            })
                        except Exception:
                            continue

                    imap.logout()
                    return mails

                except Exception:
                    return []

            def decode_email_header(self, header_text):
                """Dekoduje nagłówek emaila"""
                if not header_text:
                    return ""
                decoded_parts = decode_header(header_text)
                result = []
                for part, encoding in decoded_parts:
                    if isinstance(part, bytes):
                        try:
                            result.append(part.decode(encoding or "utf-8", errors="ignore"))
                        except Exception:
                            result.append(part.decode("utf-8", errors="ignore"))
                    else:
                        result.append(str(part))
                return " ".join(result)

        # Jeśli brak kont, po prostu nie pobieraj - bez denerwującego dialogu
        if not self.mail_accounts:
            logger.info("[ProMail] No email accounts configured - skipping mail fetch")
            return

        # Jeśli poprzedni wątek nadal działa, poczekaj na jego zakończenie
        if hasattr(self, 'email_fetcher') and self.email_fetcher is not None:
            try:
                if self.email_fetcher.isRunning():
                    self.email_fetcher.quit()
                    self.email_fetcher.wait()
            except RuntimeError:
                pass  # Obiekt już usunięty
            self.email_fetcher = None

        self.email_fetcher = EmailFetcher(self.mail_accounts)
        self.email_fetcher.finished.connect(self.on_real_emails_fetched)
        self.email_fetcher.finished.connect(self.email_fetcher.deleteLater)
        self.email_fetcher.start()

    def on_real_emails_fetched(self, emails_by_account):
        """Obsługuje pobrane maile"""
        self.real_mails = emails_by_account
        
        # Połącz prawdziwe maile z przykładowymi
        for account_email, mails in self.real_mails.items():
            if "Odebrane" not in self.sample_mails:
                self.sample_mails["Odebrane"] = []
            
            # Dodaj prawdziwe maile na początek listy
            for mail in reversed(mails):
                if mail not in self.sample_mails["Odebrane"]:
                    self.sample_mails["Odebrane"].insert(0, mail)
        
        # Odśwież widok
        self.prepare_mail_objects()
        if self.view_mode == "folders":
            self.populate_folders_tree()
            if hasattr(self, "current_folder") and self.current_folder == "Odebrane":
                self.load_folder_mails("Odebrane")
        
        total_count = sum(len(mails) for mails in self.real_mails.values())
        if total_count > 0:
            self.show_status_message(f"Pobrano {total_count} wiadomości z serwerów IMAP", 3000)
        
    def open_config(self, tab_index=None):
        """Otwiera dialog konfiguracji ProMail z opcjonalną kartą"""
        try:
            from .mail_config import MailConfigDialog
            
            dialog = MailConfigDialog(self, mail_view_parent=self)
            
            # Jeśli podano indeks karty, przełącz na nią
            if tab_index is not None and hasattr(dialog, 'tabs'):
                dialog.tabs.setCurrentIndex(tab_index)
            
            dialog.exec()
            
            logger.info("[ProMail] Opened ProMail configuration dialog")
            self.show_status_message("Zamknięto konfigurację ProMail", 2000)
            
        except Exception as e:
            logger.error(f"[ProMail] Error opening config: {e}")
            QMessageBox.warning(
                self,
                "Błąd",
                f"Nie można otworzyć konfiguracji ProMail:\n{e}"
            )
    
    def open_column_settings(self):
        """Otwiera dialog ustawień widoczności i kolejności kolumn - karta Kolumny"""
        self.open_config(tab_index=3)  # Karta 3: Układ kolumn
    
    def rebuild_mail_table_with_order(self):
        """Przebudowuje tabelę maili z nową kolejnością kolumn"""
        if not hasattr(self, "mail_list"):
            return
        
        # Zapisz aktualnie wyświetlane maile
        current_mails = self.displayed_mails.copy() if hasattr(self, 'displayed_mails') else []
        
        # Usuń starą tabelę
        old_table = self.mail_list
        parent_layout = old_table.parent().layout()
        
        # Znajdź indeks starej tabeli w layoucie
        table_index = -1
        for i in range(parent_layout.count()):
            if parent_layout.itemAt(i).widget() == old_table:
                table_index = i
                break
        
        # Usuń starą tabelę
        parent_layout.removeWidget(old_table)
        old_table.deleteLater()
        
        # Utwórz nową tabelę
        table = MailTableWidget(self)
        table.setColumnCount(11)
        
        # Utwórz nagłówki według nowej kolejności
        headers = []
        for col_idx in self.column_order:
            headers.append(self.get_column_header_short(col_idx))
        table.setHorizontalHeaderLabels(headers)
        
        table_header = table.horizontalHeader()
        if table_header:
            table_header.setStretchLastSection(True)  # Ostatnia kolumna rozciąga się
            table_header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            # Ustaw tryb rozciągania dla kolumn według ich logicznego indeksu
            table_header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            
            # Znajdź wizualne pozycje dla kolumn które powinny mieć specjalny tryb
            for visual_idx, col_idx in enumerate(self.column_order):
                if col_idx == 0:  # ⭐
                    table_header.setSectionResizeMode(visual_idx, QHeaderView.ResizeMode.Fixed)
                elif col_idx == 3:  # Odpowiedz
                    table_header.setSectionResizeMode(visual_idx, QHeaderView.ResizeMode.Fixed)
                elif col_idx == 4:  # ▶️
                    table_header.setSectionResizeMode(visual_idx, QHeaderView.ResizeMode.Fixed)
                elif col_idx in [1, 2, 5]:  # Adres, Imię/Nazwisko, Tytuł
                    table_header.setSectionResizeMode(visual_idx, QHeaderView.ResizeMode.Stretch)
        
        # Ustaw szerokości według nowej kolejności
        default_widths = {0: 40, 1: 200, 2: 150, 3: 80, 4: 35, 5: 250, 6: 130, 7: 90, 8: 100, 9: 140, 10: 220}
        for visual_idx, col_idx in enumerate(self.column_order):
            table.setColumnWidth(visual_idx, default_widths.get(col_idx, 100))
        
        vertical_header = table.verticalHeader()
        if vertical_header is not None:
            vertical_header.setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        table.cellClicked.connect(self.on_mail_clicked)
        table.cellDoubleClicked.connect(self.on_mail_cell_double_clicked)
        table.itemChanged.connect(self.on_mail_item_changed)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        table.customContextMenuRequested.connect(self.show_mail_context_menu)
        
        # Wstaw nową tabelę w to samo miejsce
        if table_index >= 0:
            parent_layout.insertWidget(table_index, table)
        else:
            parent_layout.addWidget(table)
        
        self.mail_list = table
        
        # Zastosuj widoczność kolumn
        self.apply_column_visibility()
        
        # Przywróć maile
        if current_mails:
            self.populate_mail_table(current_mails)
    
    def get_column_header_short(self, col_idx: int) -> str:
        """Zwraca krótką nazwę nagłówka dla kolumny"""
        headers_short = {
            0: "⭐",
            1: "Adres mail",
            2: "Imię/Nazwisko",
            3: "Odpowiedz",
            4: "▶️",
            5: "Tytuł",
            6: "Data",
            7: "Rozmiar",
            8: "Wątków",
            9: "Tag",
            10: "Notatka",
        }
        return headers_short.get(col_idx, "")
    
    def apply_column_visibility(self):
        """Stosuje ustawienia widoczności kolumn"""
        if not hasattr(self, "mail_list"):
            return
        
        # Zastosuj widoczność według nowej kolejności
        for visual_idx, col_idx in enumerate(self.column_order):
            visible = self.column_visibility.get(col_idx, True)
            self.mail_list.setColumnHidden(visual_idx, not visible)
    
    def zoom_mail_table(self, percentage: int):
        """Zmienia rozmiar czcionki w tabeli maili
        Args:
            percentage: Procent zmiany (np. 110 = powiększ o 10%, 90 = pomniejsz o 10%)
        """
        # Zaktualizuj zoom
        self.mail_table_zoom = max(50, min(200, int(self.mail_table_zoom * percentage / 100)))
        
        # Zastosuj nowy rozmiar czcionki
        font = self.mail_list.font()
        base_size = 9  # Bazowy rozmiar czcionki
        new_size = int(base_size * self.mail_table_zoom / 100)
        font.setPointSize(new_size)
        self.mail_list.setFont(font)
        
        # Zaktualizuj wysokość wierszy
        base_height = 26
        new_height = int(base_height * self.mail_table_zoom / 100)
        for row in range(self.mail_list.rowCount()):
            mail = self.get_mail_by_row(row)
            if mail and mail.get("_expanded"):
                # Zachowaj proporcje dla rozwiniętych maili
                preview_lines = getattr(self, "mail_preview_lines", 3)
                expanded_height = new_height + (preview_lines * 18 * self.mail_table_zoom // 100)
                self.mail_list.setRowHeight(row, expanded_height)
            else:
                self.mail_list.setRowHeight(row, new_height)
        
        # Pokaż komunikat
        self.show_status_message(f"Zoom tabeli: {self.mail_table_zoom}%", 1000)
    
    def zoom_mail_body(self, percentage: int):
        """Zmienia rozmiar czcionki w podglądzie treści maila
        Args:
            percentage: Procent zmiany (np. 110 = powiększ o 10%, 90 = pomniejsz o 10%)
        """
        # Zaktualizuj zoom
        self.mail_body_zoom = max(50, min(300, int(self.mail_body_zoom * percentage / 100)))
        
        # Zastosuj nowy rozmiar czcionki
        font = self.mail_body.font()
        base_size = 10  # Bazowy rozmiar czcionki dla treści
        new_size = int(base_size * self.mail_body_zoom / 100)
        font.setPointSize(new_size)
        self.mail_body.setFont(font)
        
        # Pokaż komunikat
        self.show_status_message(f"Zoom podglądu: {self.mail_body_zoom}%", 1000)
    
    def eventFilter(self, obj, event):
        """Filtruje eventy - obsługuje Ctrl+Scroll dla mail_body"""
        try:
            if obj == self.mail_body and event and event.type() == QEvent.Type.Wheel:
                # Sprawdź czy wciśnięty Ctrl
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    delta = event.angleDelta().y()
                    if delta > 0:
                        self.zoom_mail_body(110)  # Powiększ o 10%
                    else:
                        self.zoom_mail_body(90)   # Pomniejsz o 10%
                    return True  # Event obsłużony
            return super().eventFilter(obj, event)
        except Exception as e:
            print(f"Błąd w eventFilter: {e}")
            return False
    
    def open_tag_manager(self):
        """Otwiera dialog zarządzania tagami - karta Tagi"""
        self.open_config(tab_index=4)  # Karta 4: Tagi
    
    def extract_display_name_for_email(self, email: str) -> str:
        """Znajduje nazwę wyświetlaną dla danego adresu email"""
        for folder_mails in self.sample_mails.values():
            for mail in folder_mails:
                mail_email = self.extract_email_address(mail.get("from", ""))
                if mail_email == email:
                    name = self.extract_display_name(mail.get("from", ""))
                    if name:
                        return name
        return ""
    
    def add_tag_from_manager(self, list_widget: QListWidget, tag_type: str):
        """Dodaje nowy tag dla wiadomości lub kontaktów"""
        from PyQt6.QtWidgets import QColorDialog
        
        tag_name, ok = QInputDialog.getText(self, "Nowy tag", "Nazwa tagu:")
        if ok and tag_name:
            # Wybierz kolor
            color = QColorDialog.getColor(QColor("#FFEB3B"), self, "Wybierz kolor tagu")
            if color.isValid():
                # Dodaj do odpowiedniej listy tagów
                new_tag = {"name": tag_name, "color": color.name()}
                if tag_type == "mail":
                    self.mail_tags.append(new_tag)
                    self.save_mail_tags()
                elif tag_type == "contact":
                    self.contact_tag_definitions.append(new_tag)
                    self.save_contact_tag_definitions()
                
                # Dodaj do listy w dialogu
                item = QListWidgetItem(f"🏷️ {tag_name}")
                item.setBackground(color)
                if color.lightness() < 128:
                    item.setForeground(QColor("white"))
                list_widget.addItem(item)
                
                self.show_status_message(f"Dodano tag: {tag_name}", 2000)
    
    def edit_tag_from_manager(self, list_widget: QListWidget, tag_type: str):
        """Edytuje wybrany tag"""
        from PyQt6.QtWidgets import QColorDialog
        
        current_item = list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz tag do edycji")
            return
        
        current_index = list_widget.currentRow()
        tag_list = self.mail_tags if tag_type == "mail" else self.contact_tag_definitions
        
        if current_index < 0 or current_index >= len(tag_list):
            return
        
        tag = tag_list[current_index]
        old_name = tag.get("name", "")
        
        # Edytuj nazwę
        new_name, ok = QInputDialog.getText(self, "Edytuj tag", "Nowa nazwa tagu:", text=old_name)
        if ok and new_name:
            # Wybierz nowy kolor
            old_color = QColor(tag.get("color", "#FFEB3B"))
            new_color = QColorDialog.getColor(old_color, self, "Wybierz nowy kolor tagu")
            if new_color.isValid():
                tag["name"] = new_name
                tag["color"] = new_color.name()
                if tag_type == "mail":
                    self.save_mail_tags()
                else:
                    self.save_contact_tag_definitions()
                
                # Zaktualizuj item
                current_item.setText(f"🏷️ {new_name}")
                current_item.setBackground(new_color)
                if new_color.lightness() < 128:
                    current_item.setForeground(QColor("white"))
                else:
                    current_item.setForeground(QColor("black"))
                
                self.show_status_message(f"Zaktualizowano tag: {new_name}", 2000)
    
    def delete_tag_from_manager(self, list_widget: QListWidget, tag_type: str):
        """Usuwa wybrany tag"""
        current_item = list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz tag do usunięcia")
            return
        
        current_index = list_widget.currentRow()
        tag_list = self.mail_tags if tag_type == "mail" else self.contact_tag_definitions
        
        if current_index < 0 or current_index >= len(tag_list):
            return
        
        tag_name = tag_list[current_index].get("name", "")
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno usunąć tag '{tag_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del tag_list[current_index]
            if tag_type == "mail":
                self.save_mail_tags()
            else:
                self.save_contact_tag_definitions()
            list_widget.takeItem(current_index)
            self.show_status_message(f"Usunięto tag: {tag_name}", 2000)
    
    def set_contact_color(self, contact_list: QListWidget):
        """Ustawia kolor dla wybranego kontaktu"""
        from PyQt6.QtWidgets import QColorDialog
        
        current_item = contact_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz kontakt")
            return
        
        email = current_item.data(Qt.ItemDataRole.UserRole)
        if not email:
            return
        
        # Pobierz obecny kolor lub użyj domyślnego
        current_color = self.contact_colors.get(email, QColor("#E3F2FD"))
        
        color = QColorDialog.getColor(current_color, self, "Wybierz kolor dla kontaktu")
        if color.isValid():
            self.contact_colors[email] = color
            current_item.setBackground(color)
            if color.lightness() < 128:
                current_item.setForeground(QColor("white"))
            else:
                current_item.setForeground(QColor("black"))
            
            self.save_contact_colors()  # Zapisz kolory do pliku
            
            # Zapisz do cache
            if hasattr(self, 'cache_integration'):
                tags = self.contact_tags.get(email, [])
                self.cache_integration.cache.save_contact_to_cache(email, "", tags, color.name())
            
            self.show_status_message(f"Ustawiono kolor dla: {email}", 2000)
    
    def add_contact_tag(self, contact_list: QListWidget):
        """Dodaje tag do wybranego kontaktu z listy zdefiniowanych tagów"""
        current_item = contact_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz kontakt")
            return
        
        email = current_item.data(Qt.ItemDataRole.UserRole)
        if not email:
            return
        
        # Pobierz listę dostępnych tagów
        available_tags = [tag["name"] for tag in self.contact_tag_definitions]
        
        if not available_tags:
            QMessageBox.warning(
                self, 
                "Brak tagów", 
                "Najpierw utwórz tagi kontaktów w zakładce 'Tagi kontaktów'"
            )
            return
        
        tag_name, ok = QInputDialog.getItem(
            self,
            "Dodaj tag",
            "Wybierz tag dla kontaktu:",
            available_tags,
            0,
            False
        )
        
        if ok and tag_name:
            if email not in self.contact_tags:
                self.contact_tags[email] = []
            
            if tag_name not in self.contact_tags[email]:
                self.contact_tags[email].append(tag_name)
                
                # Zaktualizuj wyświetlanie w liście
                name = self.extract_display_name_for_email(email)
                display = f"{name} <{email}>" if name else email
                tags_str = ", ".join(self.contact_tags[email])
                current_item.setText(f"👤 {display} [{tags_str}]")
                current_item.setToolTip(f"Tagi: {tags_str}")
                
                self.save_contact_tag_assignments()  # Zapisz przypisania tagów
                
                # Zapisz do cache
                if hasattr(self, 'cache_integration'):
                    color = self.contact_colors.get(email)
                    color_str = color.name() if color and hasattr(color, 'name') else ""
                    self.cache_integration.cache.save_contact_to_cache(email, "", self.contact_tags[email], color_str)
                
                self.show_status_message(f"Dodano tag '{tag_name}' do {email}", 2000)
            else:
                QMessageBox.information(self, "Tag istnieje", "Ten tag już został dodany do kontaktu")
    
    def remove_contact_tag(self, contact_list: QListWidget):
        """Usuwa tag z wybranego kontaktu"""
        current_item = contact_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz kontakt")
            return
        
        email = current_item.data(Qt.ItemDataRole.UserRole)
        if not email or email not in self.contact_tags or not self.contact_tags[email]:
            QMessageBox.information(self, "Brak tagów", "Ten kontakt nie ma żadnych tagów")
            return
        
        tag_to_remove, ok = QInputDialog.getItem(
            self,
            "Usuń tag",
            "Wybierz tag do usunięcia:",
            self.contact_tags[email],
            0,
            False
        )
        
        if ok and tag_to_remove:
            self.contact_tags[email].remove(tag_to_remove)
            
            # Zaktualizuj wyświetlanie
            name = self.extract_display_name_for_email(email)
            display = f"{name} <{email}>" if name else email
            
            if self.contact_tags[email]:
                tags_str = ", ".join(self.contact_tags[email])
                current_item.setText(f"👤 {display} [{tags_str}]")
                current_item.setToolTip(f"Tagi: {tags_str}")
            else:
                current_item.setText(f"👤 {display}")
                current_item.setToolTip("")
            
            self.save_contact_tag_assignments()  # Zapisz przypisania tagów
            
            # Zapisz do cache
            if hasattr(self, 'cache_integration'):
                color = self.contact_colors.get(email)
                color_str = color.name() if color and hasattr(color, 'name') else ""
                self.cache_integration.cache.save_contact_to_cache(email, "", self.contact_tags[email], color_str)
            
            self.show_status_message(f"Usunięto tag '{tag_to_remove}' z {email}", 2000)
    
    def clear_contact_color(self, contact_list: QListWidget):
        """Usuwa kolor z wybranego kontaktu"""
        current_item = contact_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz kontakt")
            return
        
        email = current_item.data(Qt.ItemDataRole.UserRole)
        if not email:
            return
        
        if email in self.contact_colors:
            del self.contact_colors[email]
            current_item.setBackground(QColor("white"))
            current_item.setForeground(QColor("black"))
            self.save_contact_colors()  # Zapisz kolory do pliku
            
            # Aktualizuj cache (usuń kolor)
            if hasattr(self, 'cache_integration'):
                tags = self.contact_tags.get(email, [])
                self.cache_integration.cache.save_contact_to_cache(email, "", tags, "")
            
            self.show_status_message(f"Wyczyszczono kolor dla: {email}", 2000)

    def cleanup(self):
        """Cleanup przy zamykaniu widoku"""
        # Zapisz cache przed zamknięciem
        if hasattr(self, 'cache_integration'):
            print("[MailView] Zapisywanie danych do cache...")
            self.cache_integration.shutdown()
        
        # Zatrzymaj timer odświeżania
        if hasattr(self, 'refresh_timer'):
            self.refresh_timer.stop()
        
        # Zatrzymaj wątki
        if hasattr(self, 'email_fetcher') and self.email_fetcher is not None:
            try:
                if self.email_fetcher.isRunning():
                    self.email_fetcher.quit()
                    self.email_fetcher.wait(2000)  # Czekaj max 2 sekundy
            except RuntimeError:
                pass  # Obiekt już usunięty
        
        # Odłącz sygnały
        try:
            if self.i18n and hasattr(self.i18n, 'language_changed'):
                self.i18n.language_changed.disconnect(self.update_translations)
        except:
            pass

    def closeEvent(self, event):
        """Obsługuje zamknięcie okna - wywoływane tylko jeśli uruchomione jako standalone"""
        self.cleanup()
        event.accept()
    
    def apply_theme(self):
        """Aplikuje aktualny motyw"""
        if not self.theme_manager:
            logger.debug("[ProMail] ThemeManager not available, skipping theme application")
            return
        
        colors = self.theme_manager.get_current_colors()
        
        logger.debug(f"[ProMail] Applying theme with colors: bg_main={colors.get('bg_main')}")
        
        # Przekaż motyw do sub-widgetów
        if hasattr(self, 'queue_view'):
            self.queue_view.apply_theme()
        
        # Pełny stylesheet dla modułu ProMail
        self.setStyleSheet(f"""
            /* Główny widget */
            QWidget#mail_toolbar {{
                background-color: {colors['bg_secondary']};
                border-bottom: 1px solid {colors['border_light']};
            }}
            
            /* Przyciski toolbar */
            QPushButton#mail_new_btn,
            QPushButton#mail_reply_btn,
            QPushButton#mail_forward_btn,
            QPushButton#mail_refresh_btn {{
                background-color: {colors['accent_primary']};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
            
            QPushButton#mail_new_btn:hover,
            QPushButton#mail_reply_btn:hover,
            QPushButton#mail_forward_btn:hover,
            QPushButton#mail_refresh_btn:hover {{
                background-color: {colors['accent_hover']};
            }}
            
            QPushButton#mail_toggle_queue_btn {{
                background-color: #9C27B0;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
            
            QPushButton#mail_toggle_queue_btn:hover {{
                background-color: #7B1FA2;
            }}
            
            QPushButton#mail_toggle_queue_btn:checked {{
                background-color: #E91E63;
            }}
            
            QPushButton#mail_config_btn {{
                background-color: {colors['bg_main']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_light']};
                padding: 6px 12px;
                border-radius: 4px;
            }}
            
            QPushButton#mail_config_btn:hover {{
                background-color: {colors['bg_secondary']};
            }}
            
            QPushButton#mail_layout_btn {{
                background-color: {colors['bg_main']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_light']};
                padding: 4px 10px;
                font-weight: bold;
            }}
            
            /* Panel zawartości maila */
            QWidget#mail_content_container {{
                background-color: {colors['bg_main']};
            }}
            
            QLabel#mail_subject_label {{
                color: {colors['text_primary']};
                font-weight: bold;
                font-size: 12pt;
            }}
            
            QLabel#mail_from_label,
            QLabel#mail_to_label,
            QLabel#mail_date_label {{
                color: {colors['text_secondary']};
            }}
            
            QLabel#mail_tag_label,
            QLabel#mail_note_label {{
                color: {colors['text_secondary']};
            }}
            
            QTextEdit#mail_body_text {{
                background-color: {colors['bg_main']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_light']};
                padding: 8px;
            }}
            
            /* Status label */
            QLabel#mail_status_label {{
                color: {colors['text_secondary']};
                padding: 4px 8px;
                background-color: {colors['bg_secondary']};
            }}
            
            /* Drzewo folderów i listy */
            QTreeWidget {{
                background-color: {colors['bg_main']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_light']};
                alternate-background-color: {colors['bg_secondary']};
            }}
            
            QTreeWidget::item:selected {{
                background-color: {colors['accent_primary']};
                color: white;
            }}
            
            QTreeWidget::item:hover {{
                background-color: {colors['bg_secondary']};
            }}
            
            QTableWidget {{
                background-color: {colors['bg_main']};
                color: {colors['text_primary']};
                gridline-color: {colors['border_light']};
                border: 1px solid {colors['border_light']};
                alternate-background-color: {colors['bg_secondary']};
            }}
            
            QTableWidget::item:selected {{
                background-color: {colors['accent_primary']};
                color: white;
            }}
            
            QTableWidget::item:hover {{
                background-color: {colors['bg_secondary']};
            }}
            
            QHeaderView::section {{
                background-color: {colors['bg_secondary']};
                color: {colors['text_primary']};
                padding: 5px;
                border: 1px solid {colors['border_light']};
            }}
            
            /* Pola wejściowe */
            QLineEdit, QComboBox {{
                background-color: {colors['bg_main']};
                color: {colors['text_primary']};
                border: 1px solid {colors['border_light']};
                padding: 5px;
                border-radius: 3px;
            }}
            
            QLineEdit:focus, QComboBox:focus {{
                border: 1px solid {colors['accent_primary']};
            }}
        """)
    
    def update_translations(self):
        """Aktualizuje wszystkie teksty po zmianie języka"""
        if not self.i18n:
            return
        
        # Przyciski toolbar
        if hasattr(self, 'new_mail_btn'):
            self.new_mail_btn.setText(t('promail.button.new_mail', default='📧 Nowy'))
            self.new_mail_btn.setToolTip(t('promail.button.new_mail', default='Utwórz nową wiadomość'))
        
        if hasattr(self, 'reply_btn'):
            self.reply_btn.setText(t('promail.button.reply', default='↩️ Odpowiedz'))
            self.reply_btn.setToolTip(t('promail.button.reply', default='Odpowiedz na wybraną wiadomość'))
        
        if hasattr(self, 'forward_btn'):
            self.forward_btn.setText(t('promail.button.forward', default='➡️ Przekaż'))
            self.forward_btn.setToolTip(t('promail.button.forward', default='Przekaż wybraną wiadomość'))
        
        if hasattr(self, 'refresh_btn'):
            self.refresh_btn.setText(t('promail.button.refresh', default='🔄 Odśwież'))
            self.refresh_btn.setToolTip(t('promail.button.refresh', default='Odśwież listę wiadomości'))
        
        if hasattr(self, 'config_btn'):
            self.config_btn.setText(t('promail.button.settings', default='⚙️ Konfiguracja'))
            self.config_btn.setToolTip(t('promail.button.settings_tooltip', default='Otwórz konfigurację ProMail (podpisy, filtry, autoresponder, kolumny, tagi)'))
        
        if hasattr(self, 'toggle_queue_btn'):
            is_checked = self.toggle_queue_btn.isChecked()
            if is_checked:
                self.toggle_queue_btn.setText(t('promail.button.hide_queue', default='📋 Ukryj kolejkę'))
            else:
                self.toggle_queue_btn.setText(t('promail.button.show_queue', default='📋 Pokaż kolejkę'))
        
        # Status
        if hasattr(self, 'status_label') and hasattr(self, 'displayed_mails'):
            count = len(self.displayed_mails)
            text = t('promail.status.mails_count', default='{count} wiadomości')
            self.status_label.setText(text.format(count=count))
        
        # Foldery - odśwież drzewo folderów
        if hasattr(self, 'tree'):
            self.update_folder_labels()
        
        # Aktualizuj motyw (kolory mogły się zmienić przy zmianie języka lub motywu)
        self.apply_theme()
        
        logger.debug("[ProMail] Translations and theme updated")
    
    def update_folder_labels(self):
        """Aktualizuje etykiety folderów w drzewie"""
        if not hasattr(self, 'tree'):
            return
        
        # Mapa nazw folderów na klucze tłumaczeń
        folder_translations = {
            "Odebrane": "promail.folder.inbox",
            "Wysłane": "promail.folder.sent",
            "Szkice": "promail.folder.drafts",
            "Spam": "promail.folder.spam",
            "Kosz": "promail.folder.trash",
            "Archiwum": "promail.folder.archive",
            "Ulubione": "promail.folder.favorites"
        }
        
        # Aktualizuj nazwy głównych folderów
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item:
                current_text = item.text(0)
                # Usuń emoji jeśli jest
                folder_name = current_text.split(" ", 1)[-1] if " " in current_text else current_text
                
                if folder_name in folder_translations:
                    translated = t(folder_translations[folder_name], default=folder_name)
                    # Zachowaj emoji jeśli było
                    if " " in current_text:
                        emoji = current_text.split(" ", 1)[0]
                        item.setText(0, f"{emoji} {translated}")
                    else:
                        item.setText(0, translated)


def main():
    """Funkcja główna - uruchamia aplikację"""
    app = QApplication(sys.argv)
    app.setApplicationName("Klient pocztowy")
    app.setOrganizationName("Pro Ka Po Comer")
    window = MailViewModule()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
