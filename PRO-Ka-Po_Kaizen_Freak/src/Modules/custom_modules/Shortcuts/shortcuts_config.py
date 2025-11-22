"""
Shortcuts Module Configuration
Konfiguracja modułu skrótów klawiszowych
"""
from pathlib import Path
from typing import Dict

try:
    from ....core.config import config
except ImportError:
    # Fallback dla standalone execution
    class ConfigFallback:
        DATA_DIR = Path("data")
    config = ConfigFallback()


class ShortcutsConfig:
    """Konfiguracja modułu skrótów klawiszowych"""
    
    # ==================== ŚCIEŻKI ====================
    # Główny katalog danych modułu
    DATA_DIR = config.DATA_DIR / "shortcuts"
    
    # Plik z danymi skrótów użytkownika
    DATA_FILE = DATA_DIR / "shortcuts_data.json"
    
    # Plik z historią wykonanych skrótów (opcjonalnie)
    HISTORY_FILE = DATA_DIR / "shortcuts_history.json"
    
    # ==================== KLASY STYLÓW ====================
    # Mapowanie komponentów UI na klasy CSS używane przez ThemeManager
    STYLE_CLASSES: Dict[str, str] = {
        # Header i status
        'header_label': 'shortcuts-header',
        'status_active': 'shortcuts-status-active',
        'status_inactive': 'shortcuts-status-inactive',
        
        # Przyciski główne
        'btn_start': 'shortcuts-btn-start',
        'btn_stop': 'shortcuts-btn-stop',
        'btn_primary': 'shortcuts-btn-primary',
        'btn_secondary': 'shortcuts-btn-secondary',
        'btn_danger': 'shortcuts-btn-danger',
        'btn_success': 'shortcuts-btn-success',
        
        # Kontenery
        'group_box': 'shortcuts-group-box',
        'left_panel': 'shortcuts-left-panel',
        'right_panel': 'shortcuts-right-panel',
        
        # Specjalne widgety
        'capture_widget': 'shortcuts-capture-widget',
        'capture_widget_active': 'shortcuts-capture-widget-active',
        'capture_btn': 'shortcuts-capture-btn',
        'capture_btn_active': 'shortcuts-capture-btn-active',
        'clear_btn': 'shortcuts-clear-btn',
        
        # Tabele
        'table': 'shortcuts-table',
        'table_header': 'shortcuts-table-header',
        
        # Overlay
        'overlay': 'shortcuts-overlay',
        'overlay_instruction': 'shortcuts-overlay-instruction',
        
        # Menu kontekstowe
        'context_menu': 'shortcuts-context-menu',
        'context_menu_item': 'shortcuts-context-menu-item',
        'template_menu': 'shortcuts-template-menu',
        'shortcuts_menu': 'shortcuts-shortcuts-menu',
        
        # Przyciski specyficzne
        'btn_test': 'shortcuts-btn-test',
        'btn_test_clicks': 'shortcuts-btn-test-clicks',
        'btn_add': 'shortcuts-btn-add',
        'btn_add_template': 'shortcuts-btn-add-template',
        'btn_delete_template': 'shortcuts-btn-delete-template',
        'btn_add_menu_item': 'shortcuts-btn-add-menu-item',
        'btn_delete_menu_item': 'shortcuts-btn-delete-menu-item',
        
        # Nagłówki sekcji
        'templates_header': 'shortcuts-templates-header',
        'shortcuts_menu_header': 'shortcuts-menu-header',
        
        # Pola
        'display_field': 'shortcuts-display-field',
        'display_field_capturing': 'shortcuts-display-field-capturing',
    }
    
    # ==================== WARTOŚCI DOMYŚLNE ====================
    # Maksymalna długość magicznej frazy
    MAX_PHRASE_LENGTH = 50
    
    # Timeout dla przechwytywania klawiszy (ms)
    CAPTURE_TIMEOUT_MS = 50
    
    # Minimalna szerokość okna
    MIN_WINDOW_WIDTH = 1000
    MIN_WINDOW_HEIGHT = 600
    
    # Timeout dla poleceń PowerShell/CMD (sekundy)
    DEFAULT_COMMAND_TIMEOUT = 30
    
    # Delay między kliknięciami w sekwencji (ms)
    CLICK_SEQUENCE_DELAY_MS = 100
    
    # Maksymalna liczba kliknięć w sekwencji
    MAX_CLICK_SEQUENCE_LENGTH = 100
    
    # ==================== TYPY SKRÓTÓW ====================
    SHORTCUT_TYPES = [
        "Kombinacja klawiszy",
        "Przytrzymaj klawisz",
        "Magiczna fraza"
    ]
    
    # ==================== TYPY AKCJI ====================
    ACTION_TYPES = [
        "Wklej tekst",
        "Menu z szablonami",
        "Menu skrótów",
        "Otwórz aplikację",
        "Otwórz plik",
        "Polecenie PowerShell",
        "Polecenie wiersza poleceń",
        "Wykonaj sekwencję kliknięć"
    ]
    
    # ==================== MAPOWANIE KLAWISZY ====================
    # Mapowanie nazw klawiszy dla różnych systemów
    KEY_MAP = {
        'CTRL': 'ctrl',
        'ALT': 'alt',
        'SHIFT': 'shift',
        'WIN': 'windows',
        'SPACE': 'space',
        'ENTER': 'enter',
        'TAB': 'tab',
        'BACKSPACE': 'backspace',
        'DELETE': 'delete',
        'INSERT': 'insert',
        'HOME': 'home',
        'END': 'end',
        'PAGEUP': 'page up',
        'PAGEDOWN': 'page down',
        'LEFT': 'left',
        'UP': 'up',
        'RIGHT': 'right',
        'DOWN': 'down',
        'ESC': 'escape',
        'ESCAPE': 'escape',
    }
    
    # Klawisze funkcyjne F1-F12
    for i in range(1, 13):
        KEY_MAP[f'F{i}'] = f'f{i}'
    
    # ==================== IGNOROWANE KLAWISZE DLA FRAZ ====================
    # Klawisze ignorowane przy detekcji magicznych fraz
    PHRASE_IGNORED_KEYS = {
        'shift', 'left shift', 'right shift',
        'ctrl', 'left ctrl', 'right ctrl',
        'alt', 'left alt', 'right alt',
        'windows', 'left windows', 'right windows',
        'caps lock'
    }
    
    # Klawisze resetujące bufor fraz
    PHRASE_RESET_KEYS = {
        'esc', 'escape', 'up', 'down', 'left', 'right',
        'home', 'end', 'page up', 'page down', 'delete'
    }
    
    # Mapowanie specjalnych znaków dla fraz
    PHRASE_CHAR_MAP = {
        'comma': ',',
        'dot': '.',
        'period': '.',
        'decimal': '.',
        'minus': '-',
        'dash': '-',
        'slash': '/',
        'backslash': '\\',
        'semicolon': ';',
        'apostrophe': "'",
        'quote': '"',
        'left bracket': '[',
        'right bracket': ']',
        'left brace': '{',
        'right brace': '}',
    }
    
    # ==================== METODY POMOCNICZE ====================
    
    @classmethod
    def ensure_data_dir(cls) -> None:
        """Upewnij się że katalog danych istnieje"""
        cls.DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    @classmethod
    def get_style_class(cls, component: str) -> str:
        """
        Pobierz klasę stylu dla komponentu
        
        Args:
            component: Nazwa komponentu (np. 'header_label', 'btn_start')
            
        Returns:
            Nazwa klasy CSS lub pusty string jeśli nie znaleziono
        """
        return cls.STYLE_CLASSES.get(component, '')
    
    @classmethod
    def get_data_file_path(cls) -> Path:
        """Zwraca ścieżkę do pliku danych"""
        cls.ensure_data_dir()
        return cls.DATA_FILE
    
    @classmethod
    def get_history_file_path(cls) -> Path:
        """Zwraca ścieżkę do pliku historii"""
        cls.ensure_data_dir()
        return cls.HISTORY_FILE


# Automatycznie utwórz katalog danych przy imporcie
ShortcutsConfig.ensure_data_dir()
