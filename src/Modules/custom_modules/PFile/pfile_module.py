"""
PFile Main Module
Main QWidget module for file and folder management with cloud sharing
"""
import os
import shutil
from typing import List
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTreeWidget, QListWidget,
    QSplitter, QLabel, QPushButton, QLineEdit, QComboBox,
    QTreeWidgetItem, QListWidgetItem, QMenu, QMessageBox, QDateEdit,
    QStackedWidget, QTableWidget, QTableWidgetItem, QScrollArea, QGridLayout,
    QHeaderView, QFrame, QFileIconProvider, QDialog, QDialogButtonBox, QTextEdit,
    QRadioButton
)
from PyQt6.QtCore import Qt, pyqtSignal, QSize, QDate, QFileInfo
from PyQt6.QtGui import QIcon, QPixmap, QColor
from loguru import logger
from datetime import datetime

try:
    from ....utils.i18n_manager import get_i18n
    from ....utils.theme_manager import get_theme_manager
except ImportError:
    # Fallback for standalone execution
    get_i18n = None
    get_theme_manager = None

# Import local modules (always required)
from .pfile_config import STYLE_CLASSES, VIEW_MODE_FOLDERS, VIEW_MODE_TAGS
from .pfile_data_manager import PFileDataManager
from .pfile_api_client import PFileAPIClient
from .tagi_folderow_dialog import TagiFolderowDialog
from .pfile_drag_drop import PFileDragDropHandler



class FileItemWidget(QFrame):
    """Widget representing a single file/folder in icon view"""
    
    clicked = pyqtSignal(dict)  # Emits file_data on click
    double_clicked = pyqtSignal(dict)  # Emits file_data on double click
    
    def __init__(self, file_data: dict, parent=None):
        super().__init__(parent)
        self.file_data = file_data
        self.is_selected = False
        
        self._setup_ui()
    
    def _setup_ui(self):
        """Setup widget UI"""
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setLineWidth(1)
        self.setMaximumWidth(120)
        self.setMinimumHeight(140)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)
        
        # Pinned star (if file is pinned)
        if self.file_data.get('pinned', False):
            star_label = QLabel("⭐")
            star_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignTop)
            star_label.setStyleSheet("font-size: 16pt;")
            layout.addWidget(star_label)
        
        # Icon
        icon_label = QLabel()
        pixmap = self._get_file_icon()
        icon_label.setPixmap(pixmap)
        icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(icon_label)
        
        # Name
        name_label = QLabel(self.file_data.get('name', ''))
        name_label.setWordWrap(True)
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setMaximumWidth(110)
        layout.addWidget(name_label)
        
        # Tags (if any)
        tags = self.file_data.get('tags', [])
        if tags:
            tags_label = QLabel(', '.join(tags[:2]))  # Show max 2 tags
            tags_label.setStyleSheet("color: #666; font-size: 8pt;")
            tags_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tags_label.setWordWrap(True)
            layout.addWidget(tags_label)
    
    def _get_file_icon(self) -> QPixmap:
        """Get icon for file/folder"""
        import os
        path = self.file_data.get('path', '')
        
        if os.path.exists(path):
            icon_provider = QFileIconProvider()
            file_info = QFileInfo(path)
            icon = icon_provider.icon(file_info)
            return icon.pixmap(QSize(64, 64))
        else:
            # Default icon for non-existent files
            icon_provider = QFileIconProvider()
            icon = icon_provider.icon(QFileIconProvider.IconType.File)
            return icon.pixmap(QSize(64, 64))
    
    def set_selected(self, selected: bool):
        """Set selection state"""
        self.is_selected = selected
        if selected:
            self.setStyleSheet("border: 3px solid #0078d4; border-radius: 5px; background-color: #e6f2ff;")
        else:
            self.setStyleSheet("border: 1px solid #ccc; border-radius: 5px;")
    
    def mousePressEvent(self, event):
        """Handle mouse press"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self.file_data)
        super().mousePressEvent(event)
    
    def mouseDoubleClickEvent(self, event):
        """Handle double click"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit(self.file_data)
        super().mouseDoubleClickEvent(event)


class FileCommentDialog(QDialog):
    """Dialog for adding/editing file comment and tag"""
    
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


class AddItemDialog(QDialog):
    """Dialog for selecting item type to add"""
    
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


class ShareFileDialog(QDialog):
    """Dialog for sharing file via email"""
    
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
        self.api_input.setText("http://localhost:8000")
        self.api_input.setPlaceholderText("http://localhost:8000 lub https://your-api.onrender.com")
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


class PFileWidget(QWidget):
    """
    P-File Module - File and Folder Management
    
    Features:
    - Folder and file management with hierarchical structure
    - Tag-based organization
    - Dual view modes (folders/files or tags)
    - Cloud sharing via Backblaze B2
    - Comments and notes
    - Context menu operations
    - History tracking
    - Search and filtering
    
    Signals:
        status_message(str): Emitted when status message should be displayed
    """
    
    status_message = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Get managers
        self.i18n = get_i18n() if get_i18n else None
        self.theme_manager = get_theme_manager() if get_theme_manager else None
        
        # Initialize data manager and API client
        self.data_manager = PFileDataManager()
        self.api_client = PFileAPIClient()
        
        # Initialize drag and drop handler
        self.drag_drop_handler = PFileDragDropHandler(self)
        self.drag_drop_handler.files_dropped.connect(self._on_files_dropped)
        
        # Tags per folder system
        self.folder_tags = {}  # {folder_name: {tag_name: color}}
        
        # State
        self.current_view_mode = self.data_manager.get_setting('view_mode', VIEW_MODE_FOLDERS)
        self.current_folder_id = None
        self.current_folder = None  # Current folder name for tags
        self.selected_items = []
        self.current_view = "list"  # "list" or "icons"
        self.quick_panel_visible = False
        
        # Filters state
        self.filter_text = ""
        self.filter_tag = ""
        self.filter_date_from = None
        self.filter_date_to = None
        
        # Setup UI
        self._setup_ui()
        self._connect_signals()
        self._load_data()
        
        # Apply theme if available (no signal connection - ThemeManager doesn't have theme_changed signal)
        if self.theme_manager:
            self._apply_theme()
        
        logger.info("PFile module initialized")
    def _setup_ui(self):
        """Setup user interface"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Navigation bar
        nav_bar = self._create_navigation_bar()
        main_layout.addLayout(nav_bar)
        
        # Filter bar
        filter_bar = self._create_filter_bar()
        main_layout.addLayout(filter_bar)
        
        # Content area with quick panel + stacked widget
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Quick actions panel (initially hidden)
        self.quick_panel = self._create_quick_panel()
        self.quick_panel.setVisible(self.quick_panel_visible)
        content_layout.addWidget(self.quick_panel)
        
        # Main content area with QStackedWidget for dual view
        self.stacked_widget = QStackedWidget()
        
        # Create table view (index 0)
        self.table_view = self._create_table_view()
        self.stacked_widget.addWidget(self.table_view)
        
        # Create icons view (index 1)
        self.icons_view = self._create_icons_view()
        self.stacked_widget.addWidget(self.icons_view)
        
        # Set default view
        self.stacked_widget.setCurrentIndex(0)  # Start with table view
        
        # Enable drag and drop for both views
        self._setup_drag_drop()
        
        content_layout.addWidget(self.stacked_widget, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        self.setLayout(main_layout)
    
    def _create_navigation_bar(self) -> QHBoxLayout:
        """Create navigation bar with folder selector and action buttons"""
        nav_layout = QHBoxLayout()
        nav_layout.setContentsMargins(10, 5, 10, 5)
        nav_layout.setSpacing(5)
        
        # Toggle quick panel button
        self.btn_toggle_quick_panel = QPushButton("◀")
        self.btn_toggle_quick_panel.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        self.btn_toggle_quick_panel.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; padding: 5px;"
        )
        self.btn_toggle_quick_panel.setToolTip(self.t("pfile.nav.toggle_quick_panel"))
        nav_layout.addWidget(self.btn_toggle_quick_panel)
        
        # Folder label
        folder_label = QLabel(self.t("pfile.nav.folder_label"))
        nav_layout.addWidget(folder_label)
        
        # Folder selector ComboBox
        self.folder_combo = QComboBox()
        self.folder_combo.setProperty("class", STYLE_CLASSES.VIEW_MODE_COMBO)
        self.folder_combo.setMinimumWidth(200)
        self.folder_combo.addItem("-- " + self.t("pfile.nav.select_folder") + " --")
        # Folders will be populated in _load_folders_list()
        nav_layout.addWidget(self.folder_combo)
        
        # New folder button
        self.btn_new_folder = QPushButton(self.t("pfile.nav.new_folder"))
        self.btn_new_folder.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        nav_layout.addWidget(self.btn_new_folder)
        
        nav_layout.addStretch()
        
        # Toggle view button (list/icons)
        self.btn_toggle_view = QPushButton("🖼️ " + self.t("pfile.nav.view_icons"))
        self.btn_toggle_view.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        self.btn_toggle_view.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 5px;"
        )
        self.btn_toggle_view.setToolTip(self.t("pfile.nav.toggle_view_tooltip"))
        nav_layout.addWidget(self.btn_toggle_view)
        
        # Add new item button
        self.add_new_btn = QPushButton(self.t("pfile.nav.add_new"))
        self.add_new_btn.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        nav_layout.addWidget(self.add_new_btn)
        
        # Remove button
        self.remove_btn = QPushButton(self.t("pfile.nav.remove"))
        self.remove_btn.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        nav_layout.addWidget(self.remove_btn)
        
        # Comment button
        self.comment_btn = QPushButton(self.t("pfile.nav.comment"))
        self.comment_btn.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        nav_layout.addWidget(self.comment_btn)
        
        # Edit tags button
        self.edit_tags_btn = QPushButton(self.t("pfile.nav.edit_tags"))
        self.edit_tags_btn.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        nav_layout.addWidget(self.edit_tags_btn)
        
        # Manage folder tags button
        self.manage_folder_tags_btn = QPushButton("🏷️ Zarządzaj tagami folderu")
        self.manage_folder_tags_btn.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        self.manage_folder_tags_btn.setStyleSheet(
            "background-color: #FF9800; color: white; font-weight: bold; padding: 5px;"
        )
        self.manage_folder_tags_btn.setToolTip("Zarządzaj tagami i kolorami dla aktualnego folderu")
        nav_layout.addWidget(self.manage_folder_tags_btn)
        
        # Share button
        self.share_btn = QPushButton(self.t("pfile.nav.share"))
        self.share_btn.setProperty("class", STYLE_CLASSES.SHARE_BUTTON)
        self.share_btn.setEnabled(False)
        nav_layout.addWidget(self.share_btn)
        
        return nav_layout
    
    def _create_filter_bar(self) -> QHBoxLayout:
        """Create filter bar with search, tag, and date filters"""
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(10, 5, 10, 5)
        filter_layout.setSpacing(5)
        
        # Search label and input
        search_label = QLabel(self.t("pfile.filter.search_label"))
        filter_layout.addWidget(search_label)
        
        self.filter_text_input = QLineEdit()
        self.filter_text_input.setProperty("class", STYLE_CLASSES.SEARCH_BAR)
        self.filter_text_input.setPlaceholderText(self.t("pfile.filter.search_placeholder"))
        self.filter_text_input.setMinimumWidth(200)
        filter_layout.addWidget(self.filter_text_input)
        
        filter_layout.addSpacing(20)
        
        # Tag filter label and combo
        tag_label = QLabel(self.t("pfile.filter.tag_label"))
        filter_layout.addWidget(tag_label)
        
        self.filter_tag_combo = QComboBox()
        self.filter_tag_combo.setProperty("class", STYLE_CLASSES.VIEW_MODE_COMBO)
        self.filter_tag_combo.setMinimumWidth(150)
        self.filter_tag_combo.addItem("-- " + self.t("pfile.filter.all_tags") + " --")
        filter_layout.addWidget(self.filter_tag_combo)
        
        filter_layout.addSpacing(20)
        
        # Date filter from
        date_from_label = QLabel(self.t("pfile.filter.date_from"))
        filter_layout.addWidget(date_from_label)
        
        self.filter_date_from_input = QDateEdit()
        self.filter_date_from_input.setCalendarPopup(True)
        self.filter_date_from_input.setDisplayFormat("yyyy-MM-dd")
        self.filter_date_from_input.setSpecialValueText("--")
        self.filter_date_from_input.setDate(QDate(2000, 1, 1))
        filter_layout.addWidget(self.filter_date_from_input)
        
        # Date filter to
        date_to_label = QLabel(self.t("pfile.filter.date_to"))
        filter_layout.addWidget(date_to_label)
        
        self.filter_date_to_input = QDateEdit()
        self.filter_date_to_input.setCalendarPopup(True)
        self.filter_date_to_input.setDisplayFormat("yyyy-MM-dd")
        self.filter_date_to_input.setSpecialValueText("--")
        self.filter_date_to_input.setDate(QDate.currentDate())
        filter_layout.addWidget(self.filter_date_to_input)
        
        filter_layout.addSpacing(20)
        
        # Clear filters button
        self.btn_clear_filters = QPushButton(self.t("pfile.filter.clear_filters"))
        self.btn_clear_filters.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        filter_layout.addWidget(self.btn_clear_filters)
        
        filter_layout.addStretch()
        
        return filter_layout
    
    def _create_quick_panel(self) -> QWidget:
        """Create quick actions panel"""
        panel = QWidget()
        panel.setProperty("class", STYLE_CLASSES.LEFT_PANEL)
        panel.setMaximumWidth(350)
        panel.setMinimumWidth(250)
        
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(5, 10, 5, 10)
        layout.setSpacing(5)
        
        # Panel title
        title = QLabel(self.t("pfile.quick.title"))
        title.setProperty("class", STYLE_CLASSES.SECTION_LABEL)
        title.setStyleSheet("font-weight: bold; font-size: 12pt; padding: 5px;")
        layout.addWidget(title)
        
        layout.addSpacing(10)
        
        # Quick action buttons (mode switchers)
        self.btn_quick_favorites = QPushButton("⭐ " + self.t("pfile.quick.favorites"))
        self.btn_quick_favorites.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        self.btn_quick_favorites.setStyleSheet("text-align: left; padding: 8px;")
        self.btn_quick_favorites.clicked.connect(lambda: self._show_quick_mode('favorites'))
        layout.addWidget(self.btn_quick_favorites)
        
        self.btn_quick_recent_folder = QPushButton("📁 " + self.t("pfile.quick.recent_folder"))
        self.btn_quick_recent_folder.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        self.btn_quick_recent_folder.setStyleSheet("text-align: left; padding: 8px;")
        self.btn_quick_recent_folder.clicked.connect(lambda: self._show_quick_mode('recent_folder'))
        layout.addWidget(self.btn_quick_recent_folder)
        
        self.btn_quick_recent_system = QPushButton("� " + self.t("pfile.quick.recent_system"))
        self.btn_quick_recent_system.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        self.btn_quick_recent_system.setStyleSheet("text-align: left; padding: 8px;")
        self.btn_quick_recent_system.clicked.connect(lambda: self._show_quick_mode('recent_system'))
        layout.addWidget(self.btn_quick_recent_system)
        
        self.btn_quick_recent_opened = QPushButton("� " + self.t("pfile.quick.recent_opened"))
        self.btn_quick_recent_opened.setProperty("class", STYLE_CLASSES.TOOLBAR_BUTTON)
        self.btn_quick_recent_opened.setStyleSheet("text-align: left; padding: 8px;")
        self.btn_quick_recent_opened.clicked.connect(lambda: self._show_quick_mode('recent_opened'))
        layout.addWidget(self.btn_quick_recent_opened)
        
        layout.addSpacing(10)
        
        # Table for results
        self.quick_panel_table = QTableWidget()
        self.quick_panel_table.setColumnCount(2)
        self.quick_panel_table.setHorizontalHeaderLabels([self.t("pfile.quick.name"), self.t("pfile.quick.date")])
        self.quick_panel_table.horizontalHeader().setStretchLastSection(True)
        self.quick_panel_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.quick_panel_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.quick_panel_table.doubleClicked.connect(self._on_quick_panel_double_click)
        self.quick_panel_table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.quick_panel_table.customContextMenuRequested.connect(self._on_quick_panel_context_menu)
        layout.addWidget(self.quick_panel_table)
        
        # Initialize current mode
        self.current_quick_mode = 'favorites'
        
        return panel
    
    def _create_table_view(self) -> QTableWidget:
        """Create table view for files"""
        table = QTableWidget()
        table.setProperty("class", STYLE_CLASSES.FILES_LIST)
        
        # Setup columns
        columns = [
            self.t("pfile.table.name"),
            self.t("pfile.table.type"),
            self.t("pfile.table.size"),
            self.t("pfile.table.modified"),
            self.t("pfile.table.tags"),
            self.t("pfile.table.comment"),
            self.t("pfile.table.last_access")
        ]
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)
        
        # Configure table
        table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        table.setSelectionMode(QTableWidget.SelectionMode.ExtendedSelection)
        table.setAlternatingRowColors(True)
        table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        
        # Set column widths
        header = table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Name
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)  # Type
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Size
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Modified
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Tags
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)  # Comment
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)  # Last access
        
        return table
    
    def _create_icons_view(self) -> QScrollArea:
        """Create icons view for files (grid of FileItem widgets)"""
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setProperty("class", STYLE_CLASSES.RIGHT_PANEL)
        
        # Container widget with grid layout
        container = QWidget()
        self.icons_grid_layout = QGridLayout(container)
        self.icons_grid_layout.setSpacing(10)
        self.icons_grid_layout.setContentsMargins(10, 10, 10, 10)
        self.icons_grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        scroll_area.setWidget(container)
        
        return scroll_area
    
    def _connect_signals(self):
        """Connect UI signals to slots"""
        # Navigation bar
        self.btn_toggle_quick_panel.clicked.connect(self._on_toggle_quick_panel)
        self.folder_combo.currentTextChanged.connect(self._on_folder_changed)
        self.btn_new_folder.clicked.connect(self._on_new_folder)
        self.btn_toggle_view.clicked.connect(self._on_toggle_view)
        self.add_new_btn.clicked.connect(self._on_add_new)
        self.remove_btn.clicked.connect(self._on_remove)
        self.comment_btn.clicked.connect(self._on_comment)
        self.edit_tags_btn.clicked.connect(self._on_edit_tags)
        self.manage_folder_tags_btn.clicked.connect(self._on_manage_folder_tags)
        self.share_btn.clicked.connect(self._on_share_file)
        
        # Filter bar
        self.filter_text_input.textChanged.connect(self._on_filter_changed)
        self.filter_tag_combo.currentTextChanged.connect(self._on_filter_changed)
        self.filter_date_from_input.dateChanged.connect(self._on_filter_changed)
        self.filter_date_to_input.dateChanged.connect(self._on_filter_changed)
        self.btn_clear_filters.clicked.connect(self._on_clear_filters)
        
        # Quick panel buttons are connected in _create_quick_panel()
        
        # Table view
        self.table_view.customContextMenuRequested.connect(self._on_file_context_menu)
        self.table_view.itemSelectionChanged.connect(self._on_table_selection_changed)
    
    def _load_data(self):
        """Load and display data"""
        # Load folders into combo
        self._populate_folder_combo()
        
        # Load tags into filter combo
        self._populate_tags_combo()
        
        # Load all files into both views by default
        files = self.data_manager.get_all_files()
        self._populate_table_view(files)
        self._populate_icons_view(files)
        
        logger.info(f"Loaded {len(files)} files")
    
    def _populate_folder_combo(self):
        """Populate folder combo with available folders"""
        self.folder_combo.clear()
        self.folder_combo.addItem(f"-- {self.t('pfile.nav.select_folder')} --")
        
        folders = self.data_manager.get_all_folders()
        for folder in folders:
            self.folder_combo.addItem(folder['name'], folder['id'])
        
        logger.debug(f"Loaded {len(folders)} folders into combo")
    
    def _populate_tags_combo(self):
        """Populate tag filter combo with all unique tags"""
        self.filter_tag_combo.clear()
        self.filter_tag_combo.addItem(f"-- {self.t('pfile.filter.all_tags')} --")
        
        # Collect all unique tags from files
        all_tags = set()
        files = self.data_manager.get_all_files()
        for file in files:
            tags = file.get('tags', [])
            all_tags.update(tags)
        
        # Add to combo sorted
        for tag in sorted(all_tags):
            self.filter_tag_combo.addItem(tag)
        
        logger.debug(f"Loaded {len(all_tags)} tags into filter combo")
    
    def _populate_table_view(self, files: list):
        """Populate table view with files"""
        self.table_view.setRowCount(0)  # Clear existing rows
        
        for file_data in files:
            row = self.table_view.rowCount()
            self.table_view.insertRow(row)
            
            # Set row height to accommodate QComboBox
            self.table_view.setRowHeight(row, 35)
            
            # Column 0: Name
            name_item = QTableWidgetItem(file_data.get('name', ''))
            name_item.setData(Qt.ItemDataRole.UserRole, file_data)
            self.table_view.setItem(row, 0, name_item)
            
            # Column 1: Type
            file_type = file_data.get('type', 'file')
            type_item = QTableWidgetItem(file_type)
            self.table_view.setItem(row, 1, type_item)
            
            # Column 2: Size
            size = file_data.get('size', 0)
            size_str = self._format_file_size(size)
            size_item = QTableWidgetItem(size_str)
            self.table_view.setItem(row, 2, size_item)
            
            # Column 3: Modified
            modified = file_data.get('modified_at', '')
            if modified:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(modified)
                    modified = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            modified_item = QTableWidgetItem(modified)
            self.table_view.setItem(row, 3, modified_item)
            
            # Column 4: Tags - ComboBox z listą tagów
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
            
            tag_combo.currentTextChanged.connect(lambda text, r=row: self._on_tag_changed(r, text))
            self.table_view.setCellWidget(row, 4, tag_combo)
            
            # Column 5: Comment
            comment = file_data.get('comment', '')
            comment_item = QTableWidgetItem(comment)
            self.table_view.setItem(row, 5, comment_item)
            
            # Column 6: Last Access
            last_access = file_data.get('last_access', '')
            if last_access:
                try:
                    from datetime import datetime
                    dt = datetime.fromisoformat(last_access)
                    last_access = dt.strftime('%Y-%m-%d %H:%M')
                except:
                    pass
            access_item = QTableWidgetItem(last_access)
            self.table_view.setItem(row, 6, access_item)
        
        logger.debug(f"Populated table with {len(files)} files")
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"
    
    def _populate_icons_view(self, files: list):
        """Populate icons view with FileItemWidgets"""
        # Clear existing widgets
        while self.icons_grid_layout.count():
            item = self.icons_grid_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Add file items in grid
        columns = 5  # Number of columns in grid
        for index, file_data in enumerate(files):
            row = index // columns
            col = index % columns
            
            file_item = FileItemWidget(file_data)
            file_item.clicked.connect(self._on_file_item_clicked)
            file_item.double_clicked.connect(self._on_file_item_double_clicked)
            
            self.icons_grid_layout.addWidget(file_item, row, col)
        
        logger.debug(f"Populated icons view with {len(files)} files")
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Format file size in human-readable format"""
        if size_bytes == 0:
            return "0 B"
        
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        unit_index = 0
        size = float(size_bytes)
        
        while size >= 1024 and unit_index < len(units) - 1:
            size /= 1024
            unit_index += 1
        
        if unit_index == 0:
            return f"{int(size)} {units[unit_index]}"
        else:
            return f"{size:.2f} {units[unit_index]}"
    
    # =========================================================================
    # SLOTS (Event Handlers)
    # =========================================================================
    
    def _on_share_file(self):
        """Handle share file button - share via email with Backblaze B2"""
        # Get selected file from table view
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            self.status_message.emit("Nie wybrano pliku do udostępnienia")
            QMessageBox.warning(self, "Błąd", "Nie zaznaczono żadnego pliku.")
            return
        
        # Get file data
        row = selected_rows[0].row()
        item = self.table_view.item(row, 0)
        if not item:
            return
        
        file_data = item.data(Qt.ItemDataRole.UserRole)
        file_path = file_data.get('path', '')
        file_name = file_data.get('name', '')
        
        # Check if file exists
        import os
        if not os.path.exists(file_path):
            QMessageBox.warning(
                self,
                "Błąd",
                f"Plik nie istnieje:\n{file_path}"
            )
            self.status_message.emit("Plik nie istnieje")
            return
        
        # Check if it's a file (not folder)
        if os.path.isdir(file_path):
            QMessageBox.warning(self, "Błąd", "Nie można udostępniać folderów.\nWybierz plik.")
            return
        
        # Check file size (max 100 MB)
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
        
        # Show share dialog
        dialog = ShareFileDialog(file_name, self)
        
        if dialog.exec():
            data = dialog.get_data()
            
            # Validation
            if not data['recipient_email']:
                QMessageBox.warning(self, "Błąd", "Podaj adres email odbiorcy.")
                return
            
            if not data['sender_name']:
                QMessageBox.warning(self, "Błąd", "Podaj swoje imię/nazwę.")
                return
            
            if not data['api_url']:
                QMessageBox.warning(self, "Błąd", "Podaj URL API.")
                return
            
            # Upload file to API
            self._upload_file_to_api(file_path, file_name, data, file_data)
    
    def _upload_file_to_api(self, file_path: str, file_name: str, share_data: dict, file_data: dict):
        """Upload file to API with email notification"""
        progress = None
        try:
            # Prepare URL
            api_url = share_data['api_url'].rstrip('/')
            endpoint = f"{api_url}/api/v1/share/upload"
            
            # Show progress dialog
            progress = QMessageBox(self)
            progress.setWindowTitle("Wysyłanie pliku")
            progress.setText(f"Wysyłanie pliku: {file_name}\nProszę czekać...")
            progress.setStandardButtons(QMessageBox.StandardButton.NoButton)
            progress.setModal(True)
            progress.show()
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            
            # Prepare data to send
            import requests
            with open(file_path, 'rb') as f:
                files = {
                    'file': (file_name, f, 'application/octet-stream')
                }
                
                # Get user email from settings
                sender_email = getattr(self, 'user_email', 'user@pro-ka-po.com')
                
                data = {
                    'recipient_email': share_data['recipient_email'],
                    'sender_email': sender_email,
                    'sender_name': share_data['sender_name'],
                    'language': share_data['language']
                }
                
                # Send request
                response = requests.post(
                    endpoint,
                    files=files,
                    data=data,
                    timeout=120  # 2 minutes timeout for large files
                )
            
            # Close and delete progress dialog
            if progress:
                progress.close()
                progress.deleteLater()
                QApplication.processEvents()
                progress = None
            
            # Handle response
            if response.status_code == 201 or response.status_code == 200:
                result = response.json()
                if result.get('success'):
                    # Update file in database
                    download_url = result.get('file_info', {}).get('download_url', '')
                    if download_url:
                        self.data_manager.update_file(
                            file_data['id'],
                            shared=True,
                            share_url=download_url,
                            share_expires_at=(datetime.now() + __import__('datetime').timedelta(hours=24)).isoformat()
                        )
                        self._apply_filters()
                    
                    QMessageBox.information(
                        self,
                        "Sukces",
                        f"Plik został udostępniony!\n\n"
                        f"Email wysłany do: {share_data['recipient_email']}\n"
                        f"Plik: {file_name}"
                    )
                    self.status_message.emit(f"Udostępniono: {file_name}")
                    logger.info(f"File shared: {file_name} -> {share_data['recipient_email']}")
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
                progress.deleteLater()
                progress = None
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
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
                progress.deleteLater()
                progress = None
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            QMessageBox.critical(
                self,
                "Przekroczono czas",
                f"Przekroczono limit czasu wysyłania pliku.\n"
                f"Plik może być za duży lub połączenie zbyt wolne."
            )
        
        except Exception as e:
            if progress:
                progress.close()
                progress.deleteLater()
                progress = None
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
            logger.error(f"Share file error: {e}")
            QMessageBox.critical(
                self,
                "Błąd",
                f"Wystąpił nieoczekiwany błąd:\n{str(e)}"
            )
    
    def _on_file_context_menu(self, position):
        """Show context menu for file in table view"""
        # Get selected row
        row = self.table_view.rowAt(position.y())
        if row < 0:
            return
        
        # Get file data
        item = self.table_view.item(row, 0)
        if not item:
            return
        
        file_data = item.data(Qt.ItemDataRole.UserRole)
        
        menu = QMenu(self)
        menu.setProperty("class", STYLE_CLASSES.CONTEXT_MENU)
        
        # Otwórz
        open_action = menu.addAction("📂 Otwórz")
        open_action.triggered.connect(lambda: self._on_file_item_double_clicked(file_data))
        
        # Otwórz folder docelowy
        open_location_action = menu.addAction("📁 Otwórz folder docelowy")
        open_location_action.triggered.connect(lambda: self._open_file_location(file_data))
        
        menu.addSeparator()
        
        # Dodaj/Usuń z ulubionych
        is_pinned = file_data.get('pinned', False)
        if is_pinned:
            favorite_action = menu.addAction("⭐ Usuń z ulubionych")
            favorite_action.triggered.connect(lambda: self._toggle_favorite(file_data, False))
        else:
            favorite_action = menu.addAction("☆ Dodaj do ulubionych")
            favorite_action.triggered.connect(lambda: self._toggle_favorite(file_data, True))
        
        menu.addSeparator()
        
        # Otwórz komentarz
        comment_action = menu.addAction("💬 Otwórz komentarz")
        comment_action.triggered.connect(lambda: self._edit_file_comment(file_data))
        
        # Zmień tag
        tags_action = menu.addAction("🏷️ Zmień tag")
        tags_action.triggered.connect(lambda: self._edit_file_tags(file_data))
        
        # Kopiuj ścieżkę
        copy_action = menu.addAction("📋 Kopiuj ścieżkę")
        copy_action.triggered.connect(lambda: self._copy_file_path(file_data))
        
        menu.addSeparator()
        
        # Udostępnij
        share_action = menu.addAction("🔗 Udostępnij")
        share_action.triggered.connect(lambda: self._share_single_file(file_data))
        
        menu.addSeparator()
        
        # Usuń z folderu aplikacji
        delete_action = menu.addAction("🗑️ Usuń z folderu aplikacji")
        delete_action.triggered.connect(lambda: self._delete_file_from_app(file_data))
        
        # Execute menu
        menu.exec(self.table_view.mapToGlobal(position))
    
    def _toggle_favorite(self, file_data: dict, pinned: bool):
        """Toggle file favorite/pinned status"""
        self.data_manager.update_file(file_data['id'], pinned=pinned)
        self._apply_filters()
        status = "dodano do" if pinned else "usunięto z"
        self.status_message.emit(f"Plik {status} ulubionych: {file_data.get('name')}")
        logger.info(f"File pinned={pinned}: {file_data.get('name')}")
    
    def _edit_file_comment(self, file_data: dict):
        """Edit file comment and tag"""
        dialog = FileCommentDialog(
            self,
            current_tag=file_data.get('tag', ''),
            current_comment=file_data.get('comment', '')
        )
        
        if dialog.exec():
            data = dialog.get_data()
            self.data_manager.update_file(
                file_data['id'],
                tag=data['tag'],
                comment=data['comment']
            )
            self._apply_filters()
            self.status_message.emit(f"Zaktualizowano komentarz: {file_data.get('name')}")
            logger.info(f"Comment/tag updated for file: {file_data.get('name')}")
    
    def _edit_file_tags(self, file_data: dict):
        """Edit file tags from available folder tags list"""
        from PyQt6.QtWidgets import QInputDialog
        
        # Get tags for current folder
        current_folder_tags = self.get_current_tags()
        tag_names = sorted(current_folder_tags.keys())
        
        if not tag_names:
            # No tags available for this folder
            QMessageBox.information(
                self,
                "Brak tagów",
                "Brak zdefiniowanych tagów dla tego folderu.\n"
                "Użyj przycisku 'Zarządzaj tagami folderu' aby dodać tagi."
            )
            return
        
        # Show selection dialog with available tags
        current_tag = file_data.get('tag', '')
        selected_tag, ok = QInputDialog.getItem(
            self,
            "Wybierz tag",
            "Dostępne tagi folderu:",
            tag_names,
            tag_names.index(current_tag) if current_tag in tag_names else 0,
            False
        )
        
        if ok:
            # Update tag (single tag, not list)
            self.data_manager.update_file(file_data['id'], tag=selected_tag if selected_tag else '')
            self._apply_filters()
            self.status_message.emit(f"Zaktualizowano tag: {file_data.get('name')}")
            logger.info(f"Tag updated for file: {file_data.get('name')} -> {selected_tag}")
    
    def _copy_file_path(self, file_data: dict):
        """Copy file path to clipboard"""
        from PyQt6.QtWidgets import QApplication
        path = file_data.get('path', '')
        clipboard = QApplication.clipboard()
        clipboard.setText(path)
        self.status_message.emit(f"Ścieżka skopiowana: {file_data.get('name')}")
        QMessageBox.information(
            self,
            "Skopiowano",
            f"Ścieżka do pliku została skopiowana do schowka:\n{path}"
        )
    
    def _open_file_location(self, file_data: dict):
        """Open folder containing the file"""
        import os
        import subprocess
        path = file_data.get('path', '')
        
        if os.path.exists(path):
            folder = os.path.dirname(path)
            if os.name == 'nt':  # Windows
                os.startfile(folder)
            elif os.name == 'posix':  # Linux/Mac
                subprocess.call(['xdg-open', folder])
            self.status_message.emit(f"Otwarto lokalizację: {folder}")
        else:
            QMessageBox.warning(
                self,
                "Błąd",
                f"Plik nie istnieje:\n{path}"
            )
    
    def _share_single_file(self, file_data: dict):
        """Share a single file - wrapper for existing share functionality"""
        # Select the file in table first
        for row in range(self.table_view.rowCount()):
            item = self.table_view.item(row, 0)
            if item and item.data(Qt.ItemDataRole.UserRole) == file_data:
                self.table_view.selectRow(row)
                break
        
        # Call existing share method
        self._on_share_file()
    
    def _delete_file_from_app(self, file_data: dict):
        """Delete file from application database"""
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć ten plik z aplikacji?\n\n{file_data.get('name')}\n\n"
            "UWAGA: Plik fizyczny NIE zostanie usunięty z dysku.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.data_manager.delete_file(file_data['id'])
            self._apply_filters()
            self.status_message.emit(f"Usunięto z aplikacji: {file_data.get('name')}")
            logger.info(f"File deleted from app: {file_data.get('name')}")
    
    # Folder tags management
    
    def get_current_tags(self):
        """Zwraca tagi dla aktualnego folderu"""
        if not self.current_folder or self.current_folder == f"-- {self.t('pfile.nav.select_folder')} --":
            return {}
        
        # Jeśli folder nie ma jeszcze tagów, utwórz pusty słownik
        if self.current_folder not in self.folder_tags:
            self.folder_tags[self.current_folder] = {}
        
        return self.folder_tags[self.current_folder]
    
    def _on_manage_folder_tags(self):
        """Otwiera dialog zarządzania tagami dla aktualnego folderu"""
        if not self.current_folder or self.current_folder == f"-- {self.t('pfile.nav.select_folder')} --":
            QMessageBox.warning(
                self,
                "Błąd",
                "Najpierw wybierz folder!"
            )
            return
        
        # Pobierz aktualne tagi dla tego folderu
        current_tags = self.get_current_tags()
        
        dialog = TagiFolderowDialog(current_tags, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Aktualizuj tagi dla aktualnego folderu
            self.folder_tags[self.current_folder] = dialog.get_tags()
            
            # Zaktualizuj listę tagów w filtrze
            self._populate_tags_combo()
            
            # Odśwież widok, aby zaktualizować kolory tagów
            self._apply_filters()
            
            QMessageBox.information(
                self,
                "Sukces",
                f"Tagi folderu '{self.current_folder}' zostały zaktualizowane!"
            )
            logger.info(f"Tags updated for folder: {self.current_folder}")
    
    def _is_dark_color(self, hex_color):
        """Sprawdza czy kolor jest ciemny (do wyboru koloru tekstu)"""
        color = QColor(hex_color)
        # Oblicz jasność koloru
        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        return brightness < 128
    
    def _on_tag_changed(self, row: int, new_tag: str):
        """Obsługa zmiany tagu w tabeli"""
        # Pobierz dane pliku z pierwszej kolumny
        name_item = self.table_view.item(row, 0)
        if not name_item:
            return
        
        file_data = name_item.data(Qt.ItemDataRole.UserRole)
        if not file_data:
            return
        
        # Zaktualizuj tag w bazie danych
        self.data_manager.update_file(file_data['id'], tag=new_tag)
        
        # Zaktualizuj kolor comboboxa
        combo = self.table_view.cellWidget(row, 4)
        current_folder_tags = self.get_current_tags()
        
        if combo and new_tag and new_tag in current_folder_tags:
            color = current_folder_tags[new_tag]
            combo.setStyleSheet(
                f"background-color: {color}; "
                f"color: {'white' if self._is_dark_color(color) else 'black'}; "
                f"font-weight: bold;"
            )
        elif combo and not new_tag:
            combo.setStyleSheet("")  # Reset style
        
        logger.debug(f"Tag changed for {file_data.get('name')}: {new_tag}")

    
    # New slots for navigation and filter bars
    
    def _on_toggle_quick_panel(self):
        """Toggle quick actions panel visibility"""
        self.quick_panel_visible = not self.quick_panel_visible
        self.quick_panel.setVisible(self.quick_panel_visible)
        
        # Update button icon
        if self.quick_panel_visible:
            self.btn_toggle_quick_panel.setText("◀")
            self._refresh_quick_panel()  # Refresh when shown
            logger.debug("Quick panel shown")
        else:
            self.btn_toggle_quick_panel.setText("▶")
            logger.debug("Quick panel hidden")
    
    def _show_quick_mode(self, mode: str):
        """Switch quick panel display mode"""
        self.current_quick_mode = mode
        self._refresh_quick_panel()
        logger.debug(f"Quick panel mode changed to: {mode}")
    
    def _refresh_quick_panel(self):
        """Refresh quick panel content based on current mode"""
        self.quick_panel_table.setRowCount(0)
        
        if self.current_quick_mode == 'favorites':
            self._show_favorites_in_panel()
        elif self.current_quick_mode == 'recent_folder':
            self._show_recent_folder_files()
        elif self.current_quick_mode == 'recent_system':
            self._show_recent_system_files()
        elif self.current_quick_mode == 'recent_opened':
            self._show_recent_opened_files()
    
    def _show_favorites_in_panel(self):
        """Display favorite/pinned files in quick panel"""
        files = self.data_manager.get_all_files()
        favorites = [f for f in files if f.get('pinned', False)]
        
        self.quick_panel_table.setRowCount(len(favorites))
        for i, file_data in enumerate(favorites):
            name_item = QTableWidgetItem(file_data.get('name', ''))
            date_item = QTableWidgetItem(file_data.get('modified_at', '')[:10] if file_data.get('modified_at') else '')
            
            # Store file data in first column
            name_item.setData(Qt.ItemDataRole.UserRole, file_data)
            
            self.quick_panel_table.setItem(i, 0, name_item)
            self.quick_panel_table.setItem(i, 1, date_item)
    
    def _show_recent_folder_files(self):
        """Display recently added files from current folder"""
        # Get current folder
        index = self.folder_combo.currentIndex()
        if index > 0:
            folder_id = self.folder_combo.itemData(index)
            files = self.data_manager.get_files_by_folder(folder_id)
        else:
            files = self.data_manager.get_all_files()
        
        # Sort by created_at (most recent first)
        sorted_files = sorted(files, key=lambda f: f.get('created_at', ''), reverse=True)
        recent_files = sorted_files[:10]  # Top 10
        
        self.quick_panel_table.setRowCount(len(recent_files))
        for i, file_data in enumerate(recent_files):
            name_item = QTableWidgetItem(file_data.get('name', ''))
            date_item = QTableWidgetItem(file_data.get('created_at', '')[:10] if file_data.get('created_at') else '')
            
            name_item.setData(Qt.ItemDataRole.UserRole, file_data)
            
            self.quick_panel_table.setItem(i, 0, name_item)
            self.quick_panel_table.setItem(i, 1, date_item)
    
    def _show_recent_system_files(self):
        """Display recently modified files from system (by modified_at)"""
        files = self.data_manager.get_all_files()
        
        # Sort by modified_at (most recent first)
        sorted_files = sorted(files, key=lambda f: f.get('modified_at', ''), reverse=True)
        recent_files = sorted_files[:10]  # Top 10
        
        self.quick_panel_table.setRowCount(len(recent_files))
        for i, file_data in enumerate(recent_files):
            name_item = QTableWidgetItem(file_data.get('name', ''))
            date_item = QTableWidgetItem(file_data.get('modified_at', '')[:10] if file_data.get('modified_at') else '')
            
            name_item.setData(Qt.ItemDataRole.UserRole, file_data)
            
            self.quick_panel_table.setItem(i, 0, name_item)
            self.quick_panel_table.setItem(i, 1, date_item)
    
    def _show_recent_opened_files(self):
        """Display recently opened files (by last_access)"""
        files = self.data_manager.get_all_files()
        
        # Filter files with last_access and sort
        accessed_files = [f for f in files if f.get('last_access')]
        sorted_files = sorted(accessed_files, key=lambda f: f.get('last_access', ''), reverse=True)
        recent_files = sorted_files[:10]  # Top 10
        
        self.quick_panel_table.setRowCount(len(recent_files))
        for i, file_data in enumerate(recent_files):
            name_item = QTableWidgetItem(file_data.get('name', ''))
            date_item = QTableWidgetItem(file_data.get('last_access', '')[:10] if file_data.get('last_access') else '')
            
            name_item.setData(Qt.ItemDataRole.UserRole, file_data)
            
            self.quick_panel_table.setItem(i, 0, name_item)
            self.quick_panel_table.setItem(i, 1, date_item)
    
    def _on_quick_panel_double_click(self):
        """Handle double click on quick panel item - open file"""
        selected_row = self.quick_panel_table.currentRow()
        if selected_row >= 0:
            name_item = self.quick_panel_table.item(selected_row, 0)
            if name_item:
                file_data = name_item.data(Qt.ItemDataRole.UserRole)
                if file_data:
                    self._on_file_item_double_clicked(file_data)
    
    def _on_quick_panel_context_menu(self, position):
        """Show context menu for quick panel item"""
        row = self.quick_panel_table.rowAt(position.y())
        if row < 0:
            return
        
        name_item = self.quick_panel_table.item(row, 0)
        if not name_item:
            return
        
        file_data = name_item.data(Qt.ItemDataRole.UserRole)
        if not file_data:
            return
        
        # Use the same context menu as table view
        menu = QMenu(self)
        
        open_action = menu.addAction("📂 " + self.t("pfile.context.open"))
        open_location_action = menu.addAction("📁 " + self.t("pfile.context.open_location"))
        menu.addSeparator()
        
        # Execute menu
        action = menu.exec(self.quick_panel_table.mapToGlobal(position))
        
        if action == open_action:
            self._on_file_item_double_clicked(file_data)
        elif action == open_location_action:
            import os
            import subprocess
            path = file_data.get('path', '')
            if os.path.exists(path):
                folder = os.path.dirname(path)
                if os.name == 'nt':  # Windows
                    os.startfile(folder)
                elif os.name == 'posix':  # Linux/Mac
                    subprocess.call(['xdg-open', folder])
    
    def _on_folder_changed(self, folder_name: str):
        """Handle folder selection from ComboBox"""
        if folder_name and folder_name != f"-- {self.t('pfile.nav.select_folder')} --":
            # Set current folder for tags
            self.current_folder = folder_name
            
            # Get folder ID from combo
            index = self.folder_combo.currentIndex()
            folder_id = self.folder_combo.itemData(index)
            
            # Initialize tags for this folder if not exists
            if folder_name not in self.folder_tags:
                self.folder_tags[folder_name] = {}
            
            if folder_id:
                # Load files for this folder
                files = self.data_manager.get_files_by_folder(folder_id)
                self._populate_table_view(files)
                self._populate_icons_view(files)
                logger.info(f"Folder changed to: {folder_name} ({len(files)} files)")
                self.status_message.emit(f"{folder_name}: {len(files)} plików")
        else:
            # No folder selected
            self.current_folder = None
            
            # Show all files
            files = self.data_manager.get_all_files()
            self._populate_table_view(files)
            self._populate_icons_view(files)
            logger.info(f"Showing all files ({len(files)})")
            self.status_message.emit(f"Wszystkie pliki: {len(files)}")
    
    def _on_new_folder(self):
        """Handle new folder button"""
        from PyQt6.QtWidgets import QInputDialog
        
        folder_name, ok = QInputDialog.getText(
            self,
            self.t("pfile.dialog.new_folder_title"),
            self.t("pfile.dialog.new_folder_prompt")
        )
        
        if ok and folder_name:
            # Create new folder in database (path can be empty for virtual folders)
            folder_data = self.data_manager.add_folder(
                name=folder_name.strip(),
                path="",  # Virtual folder
                parent_id=None
            )
            if folder_data:
                self._populate_folder_combo()
                self.status_message.emit(f"Utworzono folder: {folder_name}")
                logger.info(f"New folder created: {folder_name}")
            else:
                self.status_message.emit("Błąd tworzenia folderu")
    
    def _on_toggle_view(self):
        """Toggle between list and icon view"""
        if self.current_view == "list":
            self.current_view = "icons"
            self.btn_toggle_view.setText("📋 " + self.t("pfile.nav.view_list"))
            self.stacked_widget.setCurrentIndex(1)  # Switch to icons view
        else:
            self.current_view = "list"
            self.btn_toggle_view.setText("🖼️ " + self.t("pfile.nav.view_icons"))
            self.stacked_widget.setCurrentIndex(0)  # Switch to table view
        
        logger.debug(f"View switched to: {self.current_view}")
        self.status_message.emit(f"View: {self.current_view}")
    
    def _on_add_new(self):
        """Handle add new item button - show dialog to choose item type"""
        dialog = AddItemDialog(self)
        
        if dialog.exec():
            selection = dialog.get_selection()
            
            if selection == "file":
                self._add_files()
            elif selection == "folder":
                self._add_folder()
            elif selection == "shortcut":
                self._add_shortcut()

    
    def _add_files(self):
        """Add files from file system"""
        from PyQt6.QtWidgets import QFileDialog
        
        # Show file selection dialog
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            self.t("pfile.dialog.select_files"),
            "",
            "All Files (*.*)"
        )
        
        if file_paths:
            # Get current folder (if selected)
            parent_id = None
            current_folder_name = None
            index = self.folder_combo.currentIndex()
            if index > 0:  # Index 0 is "-- Select folder --"
                parent_id = self.folder_combo.itemData(index)
                current_folder_name = self.folder_combo.currentText()
                logger.debug(f"Adding files to folder: {current_folder_name} (ID: {parent_id})")
            else:
                logger.debug("Adding files without folder assignment")
            
            # Add files to database
            added_count = 0
            for path in file_paths:
                import os
                file_name = os.path.basename(path)
                file_size = os.path.getsize(path) if os.path.exists(path) else 0
                
                file_data = self.data_manager.add_file(
                    name=file_name,
                    path=path,
                    parent_id=parent_id if parent_id else "",  # Empty string if no folder
                    size=file_size
                )
                if file_data:
                    added_count += 1
                    logger.debug(f"Added file: {file_name} with parent_id: {parent_id if parent_id else 'None'}")
            
            if added_count > 0:
                # Refresh view to show new files
                if parent_id:
                    # If folder is selected, reload that folder's files
                    self._on_folder_changed(current_folder_name)
                else:
                    # Otherwise reload all files
                    self._apply_filters()
                
                self.status_message.emit(f"Dodano {added_count} plików")
                logger.info(f"Added {added_count} files to folder: {current_folder_name if parent_id else 'root'}")
            else:
                self.status_message.emit("Nie dodano plików")
    
    def _add_folder(self):
        """Add folder from file system"""
        from PyQt6.QtWidgets import QFileDialog
        
        # Show folder selection dialog
        folder_path = QFileDialog.getExistingDirectory(
            self,
            self.t("pfile.dialog.select_folder"),
            ""
        )
        
        if folder_path:
            import os
            folder_name = os.path.basename(folder_path)
            
            # Get current folder (if selected) as parent
            parent_id = None
            index = self.folder_combo.currentIndex()
            if index > 0:  # Index 0 is "-- Select folder --"
                parent_id = self.folder_combo.itemData(index)
                logger.debug(f"Adding folder with parent_id: {parent_id}")
            else:
                logger.debug("Adding folder without parent")
            
            # Add folder to database
            folder_data = self.data_manager.add_folder(
                name=folder_name,
                path=folder_path,
                parent_id=parent_id if parent_id else None
            )
            
            if folder_data:
                # Refresh folder list and apply filters to show new folder
                self._populate_folder_combo()
                self._apply_filters()
                self.status_message.emit(f"Dodano folder: {folder_name}")
                logger.info(f"Added folder: {folder_name} with parent_id: {parent_id if parent_id else 'None'}")
            else:
                self.status_message.emit("Błąd dodawania folderu")
    
    def _add_shortcut(self):
        """Add shortcut (.lnk file)"""
        from PyQt6.QtWidgets import QFileDialog, QInputDialog
        import os
        import pathlib
        
        # Step 1: Ask for target file/folder
        target_path, _ = QFileDialog.getOpenFileName(
            self,
            "Wybierz plik/folder docelowy",
            "",
            "All Files (*.*)"
        )
        
        if not target_path:
            return
        
        # Step 2: Ask for shortcut name
        default_name = os.path.basename(target_path)
        shortcut_name, ok = QInputDialog.getText(
            self,
            "Nazwa skrótu",
            "Podaj nazwę skrótu:",
            text=f"{default_name} - Skrót"
        )
        
        if not ok or not shortcut_name:
            return
        
        # Step 3: Ask where to save .lnk file
        save_path, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz skrót jako",
            os.path.join(os.path.expanduser("~"), "Desktop", f"{shortcut_name}.lnk"),
            "Shortcut Files (*.lnk)"
        )
        
        if not save_path:
            return
        
        # Ensure .lnk extension
        if not save_path.lower().endswith('.lnk'):
            save_path += '.lnk'
        
        # Create .lnk file (Windows shortcut)
        try:
            import win32com.client
            shell = win32com.client.Dispatch("WScript.Shell")
            shortcut = shell.CreateShortCut(save_path)
            shortcut.TargetPath = target_path
            shortcut.WorkingDirectory = os.path.dirname(target_path)
            shortcut.IconLocation = target_path
            shortcut.save()
            
            # Get current folder (if selected)
            parent_id = None
            index = self.folder_combo.currentIndex()
            if index > 0:
                parent_id = self.folder_combo.itemData(index)
            
            # Add shortcut to database
            file_data = self.data_manager.add_file(
                name=os.path.basename(save_path),
                path=save_path,
                parent_id=parent_id or "",
                size=os.path.getsize(save_path) if os.path.exists(save_path) else 0
            )
            
            if file_data:
                self._apply_filters()
                self.status_message.emit(f"Utworzono skrót: {shortcut_name}")
                logger.info(f"Created shortcut: {shortcut_name} -> {target_path}")
            else:
                self.status_message.emit("Błąd dodawania skrótu do bazy")
                
        except ImportError:
            QMessageBox.warning(
                self,
                "Brak modułu",
                "Moduł pywin32 nie jest zainstalowany.\nAby tworzyć skróty, zainstaluj: pip install pywin32"
            )
        except Exception as e:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie można utworzyć skrótu:\n{str(e)}"
            )
            logger.error(f"Error creating shortcut: {e}")
    
    def _on_remove(self):
        """Handle remove button"""
        # Get selected files from current view
        selected_files = []
        
        if self.current_view == "list":
            # Get from table
            selected_rows = self.table_view.selectionModel().selectedRows()
            for row in selected_rows:
                item = self.table_view.item(row.row(), 0)
                if item:
                    file_data = item.data(Qt.ItemDataRole.UserRole)
                    selected_files.append(file_data)
        
        if not selected_files:
            self.status_message.emit("Nie wybrano plików do usunięcia")
            return
        
        # Confirm deletion
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno usunąć {len(selected_files)} plików?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for file_data in selected_files:
                self.data_manager.delete_file(file_data['id'])
            
            # Reload view
            self._apply_filters()
            self.status_message.emit(f"Usunięto {len(selected_files)} plików")
    
    def _on_comment(self):
        """Handle comment button"""
        # Get selected file from table view
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            self.status_message.emit("Nie wybrano pliku")
            return
        
        # Get file data
        row = selected_rows[0].row()
        item = self.table_view.item(row, 0)
        if not item:
            return
        
        file_data = item.data(Qt.ItemDataRole.UserRole)
        current_comment = file_data.get('comment', '')
        current_tag = file_data.get('tag', '')
        
        # Show dialog with tag and comment
        dialog = FileCommentDialog(
            self, 
            current_tag=current_tag,
            current_comment=current_comment
        )
        
        if dialog.exec():
            data = dialog.get_data()
            # Update both tag and comment in database
            self.data_manager.update_file(
                file_data['id'], 
                tag=data['tag'],
                comment=data['comment']
            )
            self._apply_filters()
            self.status_message.emit(f"Zaktualizowano komentarz i tag: {file_data.get('name')}")
            logger.info(f"Comment and tag updated for file: {file_data.get('name')}")

    
    def _on_edit_tags(self):
        """Handle edit tags button"""
        from PyQt6.QtWidgets import QInputDialog
        
        # Get selected file from table view
        selected_rows = self.table_view.selectionModel().selectedRows()
        if not selected_rows:
            self.status_message.emit("Nie wybrano pliku")
            return
        
        # Get file data
        row = selected_rows[0].row()
        item = self.table_view.item(row, 0)
        if not item:
            return
        
        file_data = item.data(Qt.ItemDataRole.UserRole)
        current_tags = ', '.join(file_data.get('tags', []))
        
        # Show input dialog
        tags_text, ok = QInputDialog.getText(
            self,
            self.t("pfile.dialog.tags_title"),
            self.t("pfile.dialog.tags_prompt"),
            text=current_tags
        )
        
        if ok:
            # Parse tags (comma-separated)
            tags = [t.strip() for t in tags_text.split(',') if t.strip()]
            
            # Update tags in database
            self.data_manager.update_file(file_data['id'], tags=tags)
            self._populate_tags_combo()  # Refresh tag combo
            self._apply_filters()
            self.status_message.emit(f"Zaktualizowano tagi: {file_data.get('name')}")
            logger.info(f"Tags updated for file: {file_data.get('name')}")
    
    def _on_filter_changed(self):
        """Handle filter change"""
        # Update filter state
        self.filter_text = self.filter_text_input.text().strip().lower()
        
        selected_tag = self.filter_tag_combo.currentText()
        self.filter_tag = "" if selected_tag == f"-- {self.t('pfile.filter.all_tags')} --" else selected_tag
        
        # Dates
        date_from_text = self.filter_date_from_input.text()
        if date_from_text and date_from_text != "--":
            from datetime import datetime
            self.filter_date_from = datetime.strptime(date_from_text, "%Y-%m-%d")
        else:
            self.filter_date_from = None
        
        date_to_text = self.filter_date_to_input.text()
        if date_to_text and date_to_text != "--":
            self.filter_date_to = datetime.strptime(date_to_text, "%Y-%m-%d")
        else:
            self.filter_date_to = None
        
        # Apply filters and refresh view
        self._apply_filters()
        logger.debug(f"Filters: text='{self.filter_text}', tag='{self.filter_tag}'")
    
    def _apply_filters(self):
        """Apply current filters to file list"""
        # Get base files (from selected folder or all)
        index = self.folder_combo.currentIndex()
        if index > 0:  # Specific folder selected
            folder_id = self.folder_combo.itemData(index)
            files = self.data_manager.get_files_by_folder(folder_id)
        else:
            files = self.data_manager.get_all_files()
        
        # Apply text filter
        if self.filter_text:
            files = [f for f in files if self.filter_text in f.get('name', '').lower()]
        
        # Apply tag filter
        if self.filter_tag:
            files = [f for f in files if self.filter_tag in f.get('tags', [])]
        
        # Apply date filters
        if self.filter_date_from or self.filter_date_to:
            filtered = []
            for f in files:
                modified = f.get('modified_at', '')
                if modified:
                    try:
                        file_date = datetime.fromisoformat(modified)
                        if self.filter_date_from and file_date < self.filter_date_from:
                            continue
                        if self.filter_date_to and file_date > self.filter_date_to:
                            continue
                        filtered.append(f)
                    except:
                        pass
            files = filtered
        
        # Update both views
        self._populate_table_view(files)
        self._populate_icons_view(files)
        
        self.status_message.emit(f"Znaleziono: {len(files)} plików")
    
    def _on_clear_filters(self):
        """Clear all filters"""
        self.filter_text_input.clear()
        self.filter_tag_combo.setCurrentIndex(0)
        self.filter_date_from_input.setDate(QDate(2000, 1, 1))
        self.filter_date_to_input.setDate(QDate.currentDate())
        
        # Reload without filters
        self._apply_filters()
        self.status_message.emit(self.t("pfile.filter.clear_filters"))
    
    def _on_table_selection_changed(self):
        """Handle table selection change"""
        selected_items = self.table_view.selectedItems()
        if selected_items:
            # Get data from first column of selected row
            row = selected_items[0].row()
            name_item = self.table_view.item(row, 0)
            if name_item:
                file_data = name_item.data(Qt.ItemDataRole.UserRole)
                logger.debug(f"Selected file: {file_data.get('name')}")
                # Enable share button if file is selected
                self.share_btn.setEnabled(True)
        else:
            self.share_btn.setEnabled(False)
    
    def _on_file_item_clicked(self, file_data: dict):
        """Handle FileItem click"""
        logger.debug(f"File item clicked: {file_data.get('name')}")
        # TODO: Implement selection logic for multiple items
        self.share_btn.setEnabled(True)
    
    def _on_file_item_double_clicked(self, file_data: dict):
        """Handle FileItem double click"""
        import os
        import subprocess
        
        path = file_data.get('path', '')
        logger.info(f"Opening file: {path}")
        
        if os.path.exists(path):
            try:
                if os.name == 'nt':  # Windows
                    os.startfile(path)
                elif os.name == 'posix':  # Linux/Mac
                    subprocess.call(['xdg-open', path])
                
                # Update last access time
                self.data_manager.update_file(file_data['id'], last_access=datetime.now().isoformat())
                
                self.status_message.emit(f"Otwarto: {file_data.get('name')}")
            except Exception as e:
                logger.error(f"Failed to open file: {e}")
                self.status_message.emit(f"Błąd otwarcia pliku")
        else:
            self.status_message.emit(f"Plik nie istnieje: {path}")
    
    # =========================================================================
    # DRAG AND DROP METHODS
    # =========================================================================
    
    def _setup_drag_drop(self):
        """Konfiguracja drag and drop dla widoków"""
        # Włącz drop (przyjmowanie plików z zewnątrz)
        self.drag_drop_handler.enable_drop(self.table_view)
        self.drag_drop_handler.enable_drop(self.icons_view)
        
        # Włącz drag (przeciąganie plików z aplikacji)
        self.drag_drop_handler.enable_drag(
            self.table_view,
            self._get_selected_file_paths_for_drag
        )
        
        logger.info("Drag and drop enabled for PFile views")
    
    def _get_selected_file_paths_for_drag(self) -> List[str]:
        """
        Pobierz ścieżki wybranych plików do przeciągnięcia.
        
        Returns:
            Lista ścieżek plików
        """
        file_paths = []
        
        # Pobierz zaznaczone wiersze z tabeli
        selected_rows = self.table_view.selectionModel().selectedRows()
        
        for index in selected_rows:
            row = index.row()
            # Pobierz dane pliku z pierwszej kolumny
            name_item = self.table_view.item(row, 0)
            if name_item and hasattr(name_item, 'file_data'):
                file_data = name_item.file_data
                path = file_data.get('path')
                if path and os.path.exists(path):
                    file_paths.append(path)
        
        return file_paths
    
    def _on_files_dropped(self, file_paths: List[str]):
        """
        Obsługa upuszczonych plików z zewnątrz.
        
        Args:
            file_paths: Lista ścieżek plików do zaimportowania
        """
        if not file_paths:
            return
        
        # Sprawdź czy jest wybrany folder
        if not self.current_folder:
            QMessageBox.warning(
                self,
                "Brak folderu",
                "Wybierz folder, do którego chcesz dodać pliki."
            )
            return
        
        # Zapytaj użytkownika czy skopiować czy przenieść
        reply = QMessageBox.question(
            self,
            "Importuj pliki",
            f"Znaleziono {len(file_paths)} plików.\n\n"
            f"Co chcesz zrobić?\n\n"
            f"• TAK - Skopiuj pliki do folderu '{self.current_folder}'\n"
            f"• NIE - Przenieś pliki do folderu '{self.current_folder}'\n"
            f"• ANULUJ - Anuluj operację",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
        
        move_files = (reply == QMessageBox.StandardButton.No)
        
        # Pobierz folder docelowy
        folder_path = self.data_manager.get_folder_path(self.current_folder)
        
        if not folder_path or not os.path.exists(folder_path):
            QMessageBox.critical(
                self,
                "Błąd",
                f"Folder '{self.current_folder}' nie istnieje."
            )
            return
        
        # Importuj pliki
        imported_count = 0
        errors = []
        
        for file_path in file_paths:
            try:
                file_name = os.path.basename(file_path)
                dest_path = os.path.join(folder_path, file_name)
                
                # Sprawdź czy plik już istnieje
                if os.path.exists(dest_path):
                    # Zapytaj o nadpisanie
                    overwrite = QMessageBox.question(
                        self,
                        "Plik istnieje",
                        f"Plik '{file_name}' już istnieje w folderze.\n\nCzy nadpisać?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                    )
                    
                    if overwrite != QMessageBox.StandardButton.Yes:
                        continue
                
                # Skopiuj lub przenieś plik
                if move_files:
                    shutil.move(file_path, dest_path)
                    logger.info(f"Moved file: {file_path} -> {dest_path}")
                else:
                    shutil.copy2(file_path, dest_path)
                    logger.info(f"Copied file: {file_path} -> {dest_path}")
                
                imported_count += 1
                
            except Exception as e:
                error_msg = f"{os.path.basename(file_path)}: {str(e)}"
                errors.append(error_msg)
                logger.error(f"Error importing file {file_path}: {e}")
        
        # Odśwież widok
        self._load_files_for_folder(self.current_folder)
        
        # Pokaż podsumowanie
        msg = f"Zaimportowano {imported_count} z {len(file_paths)} plików."
        
        if errors:
            msg += f"\n\nBłędy:\n" + "\n".join(errors[:5])
            if len(errors) > 5:
                msg += f"\n... i {len(errors) - 5} więcej"
            
            QMessageBox.warning(self, "Import zakończony z błędami", msg)
        else:
            QMessageBox.information(self, "Import zakończony", msg)
        
        logger.info(f"Files drop completed: {imported_count} files imported")
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def _apply_theme(self):
        """Apply current theme to UI"""
        if not self.theme_manager:
            return
        
        # Apply property classes to all widgets
        if self.style():
            self.style().unpolish(self)
            self.style().polish(self)
        self.update()
        
        logger.debug("Theme applied to PFile module")
    
    def update_ui_texts(self):
        """Update all UI texts (called when language changes)"""
        # Navigation bar
        self.btn_toggle_quick_panel.setToolTip(self.t("pfile.nav.toggle_quick_panel"))
        self.folder_combo.setItemText(0, f"-- {self.t('pfile.nav.select_folder')} --")
        self.btn_new_folder.setText(self.t("pfile.nav.new_folder"))
        
        # Update view toggle button text
        if self.current_view == "list":
            self.btn_toggle_view.setText("🖼️ " + self.t("pfile.nav.view_icons"))
        else:
            self.btn_toggle_view.setText("📋 " + self.t("pfile.nav.view_list"))
        
        self.add_new_btn.setText(self.t("pfile.nav.add_new"))
        self.remove_btn.setText(self.t("pfile.nav.remove"))
        self.comment_btn.setText(self.t("pfile.nav.comment"))
        self.edit_tags_btn.setText(self.t("pfile.nav.edit_tags"))
        self.share_btn.setText(self.t("pfile.nav.share"))
        
        # Filter bar
        self.filter_text_input.setPlaceholderText(self.t("pfile.filter.search_placeholder"))
        self.filter_tag_combo.setItemText(0, f"-- {self.t('pfile.filter.all_tags')} --")
        self.btn_clear_filters.setText(self.t("pfile.filter.clear_filters"))
        
        # Reload data to update labels
        self._load_data()
        
        logger.info("PFile UI texts updated")
    
    def t(self, key: str) -> str:
        """
        Translate key to current language
        
        Args:
            key: Translation key
        
        Returns:
            Translated string or key if not found
        """
        if self.i18n:
            return self.i18n.translate(key)
        return key
    
    def closeEvent(self, a0):
        """Handle widget close - save settings"""
        # Save view mode
        self.data_manager.set_setting('current_view', self.current_view)
        
        super().closeEvent(a0)


# =============================================================================
# STANDALONE EXECUTION (for testing)
# =============================================================================

if __name__ == "__main__":
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    
    widget = PFileWidget()
    widget.setWindowTitle("PFile Module - Standalone Test")
    widget.resize(1200, 700)
    widget.show()
    
    sys.exit(app.exec())
