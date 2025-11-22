"""
PFile Configuration Module
Configuration constants, paths, and theme style classes for P-File module
"""
import os
from pathlib import Path
from typing import Dict


# =============================================================================
# DIRECTORY PATHS
# =============================================================================

# Base directory for P-File data
BASE_DIR = Path(__file__).resolve().parent.parent.parent.parent.parent
DATA_DIR = BASE_DIR / "data" / "pfile"
ICONS_DIR = BASE_DIR / "resources" / "icons"

# Ensure data directory exists
DATA_DIR.mkdir(parents=True, exist_ok=True)


# =============================================================================
# FILE PATHS
# =============================================================================

FOLDERS_DATA_FILE = DATA_DIR / "folders_data.json"
TAGS_DATA_FILE = DATA_DIR / "tags_data.json"
HISTORY_DATA_FILE = DATA_DIR / "history_data.json"
SETTINGS_FILE = DATA_DIR / "pfile_settings.json"


# =============================================================================
# CONFIGURATION CONSTANTS
# =============================================================================

# File size limits
MAX_FILE_SIZE_MB = 100  # Maximum file size for sharing (MB)
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

# File sharing
FILE_EXPIRE_DAYS = 7  # Default expiration for shared files

# UI Constants
ICON_SIZE = 24
BUTTON_ICON_SIZE = 20
TREE_ICON_SIZE = 16
MIN_COLUMN_WIDTH = 150
MAX_RECENT_ITEMS = 10

# View modes
VIEW_MODE_FOLDERS = "folders"
VIEW_MODE_TAGS = "tags"

# Item types
ITEM_TYPE_FOLDER = "folder"
ITEM_TYPE_FILE = "file"

# Tag colors (default palette)
TAG_COLORS = [
    "#FF6B6B", "#4ECDC4", "#45B7D1", "#FFA07A", 
    "#98D8C8", "#F7DC6F", "#BB8FCE", "#85C1E2",
    "#F8B739", "#52B788", "#E76F51", "#8AB17D"
]


# =============================================================================
# THEME STYLE CLASSES
# =============================================================================

class STYLE_CLASSES:
    """Theme property classes for P-File module UI elements"""
    
    # Main container
    MAIN_CONTAINER = "pfile-main-container"
    
    # Toolbar
    TOOLBAR = "pfile-toolbar"
    TOOLBAR_BUTTON = "pfile-toolbar-button"
    TOOLBAR_BUTTON_ACTIVE = "pfile-toolbar-button-active"
    TOOLBAR_SEPARATOR = "pfile-toolbar-separator"
    SEARCH_BAR = "pfile-search-bar"
    
    # Tree widgets
    FOLDERS_TREE = "pfile-folders-tree"
    TAGS_TREE = "pfile-tags-tree"
    
    # Lists
    FILES_LIST = "pfile-files-list"
    QUICK_ACCESS_LIST = "pfile-quick-access-list"
    
    # Panels
    LEFT_PANEL = "pfile-left-panel"
    RIGHT_PANEL = "pfile-right-panel"
    DETAILS_PANEL = "pfile-details-panel"
    
    # Labels
    SECTION_LABEL = "pfile-section-label"
    INFO_LABEL = "pfile-info-label"
    PATH_LABEL = "pfile-path-label"
    
    # Buttons
    PRIMARY_BUTTON = "pfile-primary-button"
    SECONDARY_BUTTON = "pfile-secondary-button"
    ICON_BUTTON = "pfile-icon-button"
    ADD_BUTTON = "pfile-add-button"
    REMOVE_BUTTON = "pfile-remove-button"
    SHARE_BUTTON = "pfile-share-button"
    
    # Input fields
    TEXT_EDIT = "pfile-text-edit"
    LINE_EDIT = "pfile-line-edit"
    
    # Tags
    TAG_WIDGET = "pfile-tag-widget"
    TAG_LABEL = "pfile-tag-label"
    TAG_REMOVE_BUTTON = "pfile-tag-remove-button"
    
    # Status
    STATUS_BAR = "pfile-status-bar"
    
    # Dialogs
    DIALOG = "pfile-dialog"
    DIALOG_TITLE = "pfile-dialog-title"
    DIALOG_CONTENT = "pfile-dialog-content"
    DIALOG_BUTTON_BOX = "pfile-dialog-button-box"
    
    # Context menu
    CONTEXT_MENU = "pfile-context-menu"
    CONTEXT_MENU_ITEM = "pfile-context-menu-item"
    
    # Splitter
    SPLITTER = "pfile-splitter"
    
    # View mode selector
    VIEW_MODE_COMBO = "pfile-view-mode-combo"
    
    # Filter panel
    FILTER_PANEL = "pfile-filter-panel"
    FILTER_CHECKBOX = "pfile-filter-checkbox"


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_data_file_path(filename: str) -> Path:
    """
    Returns full path to data file
    
    Args:
        filename: Name of the data file
    
    Returns:
        Path object to the data file
    """
    return DATA_DIR / filename


def ensure_data_files_exist():
    """Creates default data files if they don't exist"""
    default_data = {
        'folders': [],
        'files': [],
        'metadata': {
            'version': '1.0.0',
            'created_at': None,
            'last_modified': None
        }
    }
    
    default_tags = {
        'tags': [],
        'metadata': {
            'version': '1.0.0',
            'created_at': None
        }
    }
    
    default_history = {
        'history': [],
        'max_entries': 100
    }
    
    default_settings = {
        'view_mode': VIEW_MODE_FOLDERS,
        'show_hidden': False,
        'sort_by': 'name',
        'sort_order': 'asc',
        'last_path': None,
        'splitter_sizes': [300, 700, 250],
        'window_geometry': None
    }
    
    import json
    
    if not FOLDERS_DATA_FILE.exists():
        with open(FOLDERS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_data, f, indent=2, ensure_ascii=False)
    
    if not TAGS_DATA_FILE.exists():
        with open(TAGS_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_tags, f, indent=2, ensure_ascii=False)
    
    if not HISTORY_DATA_FILE.exists():
        with open(HISTORY_DATA_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_history, f, indent=2, ensure_ascii=False)
    
    if not SETTINGS_FILE.exists():
        with open(SETTINGS_FILE, 'w', encoding='utf-8') as f:
            json.dump(default_settings, f, indent=2, ensure_ascii=False)


def format_file_size(size_bytes: int) -> str:
    """
    Formats file size in human-readable format
    
    Args:
        size_bytes: Size in bytes
    
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    else:
        return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"


def get_icon_path(icon_name: str) -> str:
    """
    Returns path to icon file
    
    Args:
        icon_name: Name of the icon file (with extension)
    
    Returns:
        String path to icon
    """
    icon_path = ICONS_DIR / icon_name
    if icon_path.exists():
        return str(icon_path)
    return ""


# Initialize data files on module import
ensure_data_files_exist()
