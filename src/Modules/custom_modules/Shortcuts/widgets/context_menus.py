"""
Menu kontekstowe z szablonami tekstowymi i skrótami dla modułu Shortcuts
"""
import subprocess
from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
import pyperclip

try:
    from ..shortcuts_config import ShortcutsConfig
except ImportError:
    # Standalone execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from shortcuts_config import ShortcutsConfig

config = ShortcutsConfig()


class TemplateContextMenu(QMenu):
    """Menu kontekstowe z szablonami tekstowymi"""
    
    def __init__(self, templates, parent=None):
        super().__init__(parent)
        self.setProperty('class', config.get_style_class('template_menu'))
        
        # Dodaj szablony do menu
        for template in templates:
            name = template.get('name', 'Bez nazwy')
            content = template.get('content', '')
            
            action = QAction(name, self)
            action.setData(content)  # Przechowuj treść w action
            action.triggered.connect(lambda checked, c=content: self.copy_to_clipboard(c))
            self.addAction(action)
    
    def copy_to_clipboard(self, text):
        """Kopiuje tekst do schowka i wkleja"""
        try:
            pyperclip.copy(text)
            # Symuluj Ctrl+V
            import keyboard
            keyboard.send('ctrl+v')
        except Exception as e:
            print(f"Błąd kopiowania do schowka: {e}")


class ShortcutsContextMenu(QMenu):
    """Menu kontekstowe ze skrótami do plików/folderów/akcji"""
    
    def __init__(self, menu_items, parent=None):
        super().__init__(parent)
        self.setProperty('class', config.get_style_class('shortcuts_menu'))
        
        # Dodaj pozycje do menu
        for item in menu_items:
            name = item.get('name', 'Bez nazwy')
            item_type = item.get('type', 'Otwórz plik')
            path = item.get('path', '')
            
            # Wybierz emoji/ikonę w zależności od typu
            icon = self.get_icon_for_type(item_type)
            display_name = f"{icon} {name}"
            
            action = QAction(display_name, self)
            action.setData({'type': item_type, 'path': path})
            action.triggered.connect(lambda checked, t=item_type, p=path: self.execute_menu_action(t, p))
            self.addAction(action)
    
    def get_icon_for_type(self, item_type):
        """Zwraca emoji dla danego typu pozycji"""
        icons = {
            "Folder": "📁",
            "Otwórz plik": "📄",
            "Otwórz aplikację": "🚀",
            "URL": "🌐",
            "Polecenie": "⚡"
        }
        return icons.get(item_type, "📌")
    
    def execute_menu_action(self, item_type, path):
        """Wykonuje akcję dla pozycji menu"""
        try:
            if item_type in ["Folder", "Otwórz plik", "Otwórz aplikację"]:
                # Otwórz w Eksploratorze / uruchom aplikację
                subprocess.Popen(['explorer', path])
            elif item_type == "URL":
                # Otwórz w przeglądarce
                import webbrowser
                webbrowser.open(path)
            elif item_type == "Polecenie":
                # Uruchom polecenie
                subprocess.Popen(path, shell=True)
            
            print(f"[Menu] Wykonano: {item_type} -> {path}")
        except Exception as e:
            print(f"Błąd wykonywania akcji menu: {e}")
