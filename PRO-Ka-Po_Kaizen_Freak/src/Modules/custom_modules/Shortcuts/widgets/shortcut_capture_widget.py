"""
Widget do przechwytywania kombinacji klawiszy dla modułu Shortcuts
"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QPushButton, QLineEdit
from PyQt6.QtCore import QTimer

try:
    import win32api
    import win32con
except ImportError:
    print("BŁĄD: Biblioteka pywin32 nie jest zainstalowana. Uruchom: pip install pywin32")
    import sys
    sys.exit(1)

try:
    from ..shortcuts_config import ShortcutsConfig
except ImportError:
    # Standalone execution
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from shortcuts_config import ShortcutsConfig

config = ShortcutsConfig()


class ShortcutCaptureWidget(QWidget):
    """Widget do przechwytywania kombinacji klawiszy - NOWE BEZPIECZNE PODEJŚCIE"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_keys = set()
        self.magic_phrase_mode = False  # Tryb magicznej frazy
        self.setup_ui()
    
    def setup_ui(self):
        """Buduje interfejs"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Pole - pokazuje przechwycony skrót lub edytowalna fraza
        self.display_field = QLineEdit()
        self.display_field.setReadOnly(True)
        self.display_field.setPlaceholderText("Kliknij 'Przechwytuj' i naciśnij kombinację...")
        layout.addWidget(self.display_field)
        
        # Przycisk do rozpoczęcia przechwytywania
        self.capture_btn = QPushButton("🎯 Przechwytuj")
        self.capture_btn.setProperty('class', config.get_style_class('capture_btn'))
        self.capture_btn.style().unpolish(self.capture_btn)
        self.capture_btn.style().polish(self.capture_btn)
        self.capture_btn.clicked.connect(self.start_capture)
        layout.addWidget(self.capture_btn)
        
        # Przycisk czyszczenia
        self.clear_btn = QPushButton("✖")
        self.clear_btn.clicked.connect(self.clear)
        self.clear_btn.setMaximumWidth(40)
        layout.addWidget(self.clear_btn)
        
        self.setLayout(layout)
        
        # Timer do monitorowania klawiszy
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.check_keys)
        self.capturing = False
    
    def start_capture(self):
        """Rozpoczyna przechwytywanie kombinacji klawiszy"""
        if self.capturing:
            self.stop_capture()
            return
        
        self.capturing = True
        self.current_keys.clear()
        self.display_field.setText("⏳ Naciśnij kombinację klawiszy...")
        self.display_field.setProperty('class', config.get_style_class('display_field_capturing'))
        self.display_field.style().unpolish(self.display_field)
        self.display_field.style().polish(self.display_field)
        self.capture_btn.setText("⏹ Stop")
        self.capture_btn.setProperty('class', config.get_style_class('capture_btn_active'))
        self.capture_btn.style().unpolish(self.capture_btn)
        self.capture_btn.style().polish(self.capture_btn)
        
        # Uruchom timer
        self.capture_timer.start(50)  # Sprawdzaj co 50ms
    
    def stop_capture(self):
        """Zatrzymuje przechwytywanie"""
        self.capturing = False
        self.capture_timer.stop()
        self.display_field.setProperty('class', config.get_style_class('display_field'))
        self.display_field.style().unpolish(self.display_field)
        self.display_field.style().polish(self.display_field)
        self.capture_btn.setText("🎯 Przechwytuj")
        self.capture_btn.setProperty('class', config.get_style_class('capture_btn'))
        self.capture_btn.style().unpolish(self.capture_btn)
        self.capture_btn.style().polish(self.capture_btn)
    
    def check_keys(self):
        """Sprawdza aktualnie wciśnięte klawisze używając Windows API"""
        if not self.capturing:
            return
        
        # Sprawdź modyfikatory
        modifiers = []
        if win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000:
            modifiers.append("Ctrl")
        if win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000:  # Alt
            modifiers.append("Alt")
        if win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000:
            modifiers.append("Shift")
        if win32api.GetAsyncKeyState(win32con.VK_LWIN) & 0x8000 or win32api.GetAsyncKeyState(win32con.VK_RWIN) & 0x8000:
            modifiers.append("Win")
        
        # Sprawdź klawisze funkcyjne i specjalne
        main_key = None
        
        # Litery A-Z
        for i in range(ord('A'), ord('Z') + 1):
            if win32api.GetAsyncKeyState(i) & 0x8000:
                main_key = chr(i)
                break
        
        # Cyfry 0-9
        if not main_key:
            for i in range(ord('0'), ord('9') + 1):
                if win32api.GetAsyncKeyState(i) & 0x8000:
                    main_key = chr(i)
                    break
        
        # Klawisze funkcyjne F1-F12
        if not main_key:
            for i in range(1, 13):
                if win32api.GetAsyncKeyState(0x70 + i - 1) & 0x8000:  # VK_F1 = 0x70
                    main_key = f"F{i}"
                    break
        
        # Inne specjalne klawisze
        if not main_key:
            special_keys = {
                win32con.VK_SPACE: "Space",
                win32con.VK_RETURN: "Enter",
                win32con.VK_BACK: "Backspace",
                win32con.VK_DELETE: "Delete",
                win32con.VK_TAB: "Tab",
                win32con.VK_ESCAPE: "Esc",
                win32con.VK_INSERT: "Insert",
                win32con.VK_HOME: "Home",
                win32con.VK_END: "End",
                win32con.VK_PRIOR: "PageUp",
                win32con.VK_NEXT: "PageDown",
                win32con.VK_LEFT: "Left",
                win32con.VK_UP: "Up",
                win32con.VK_RIGHT: "Right",
                win32con.VK_DOWN: "Down",
            }
            
            for vk_code, name in special_keys.items():
                if win32api.GetAsyncKeyState(vk_code) & 0x8000:
                    main_key = name
                    break
        
        # Jeśli znaleziono główny klawisz - zakończ przechwytywanie
        if main_key and len(modifiers) > 0:
            shortcut = "+".join(modifiers + [main_key])
            self.display_field.setText(shortcut)
            self.stop_capture()
        elif main_key and len(modifiers) == 0:
            # Tylko główny klawisz bez modyfikatorów - też akceptujemy
            self.display_field.setText(main_key)
            self.stop_capture()
    
    def clear(self):
        """Czyści pole"""
        self.display_field.clear()
        self.stop_capture()
    
    def text(self):
        """Zwraca aktualnie ustawiony skrót - kompatybilność z QLineEdit"""
        return self.display_field.text().strip()
    
    def setText(self, text):
        """Ustawia skrót - kompatybilność z QLineEdit"""
        self.display_field.setText(text)
    
    def setPlaceholderText(self, text):
        """Ustawia tekst zastępczy - kompatybilność z QLineEdit"""
        self.display_field.setPlaceholderText(text)
    
    def setReadOnly(self, readonly):
        """Ustawia tryb tylko-do-odczytu - kompatybilność z QLineEdit"""
        # Dla magicznej frazy pozwól na edycję ręczną
        self.display_field.setReadOnly(readonly)
    
    def set_magic_phrase_mode(self, enabled):
        """Przełącza między trybem przechwytywania klawiszy a trybem wpisywania frazy"""
        self.magic_phrase_mode = enabled
        
        if enabled:
            # Tryb magicznej frazy - pole edytowalne, przycisk ukryty
            self.display_field.setReadOnly(False)
            self.display_field.setPlaceholderText("Wpisz frazę tekstową (np. 'hello', ';podpis')...")
            self.capture_btn.setVisible(False)
        else:
            # Tryb kombinacji klawiszy - pole readonly, przycisk widoczny
            self.display_field.setReadOnly(True)
            self.display_field.setPlaceholderText("Kliknij 'Przechwytuj' i naciśnij kombinację...")
            self.capture_btn.setVisible(True)
