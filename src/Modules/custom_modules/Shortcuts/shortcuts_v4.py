"""
Shortcuts v4 - System globalnych skrótów używający CZYSTEGO Windows API
Inspirowany AutoHotkey - używa SetWindowsHookEx dla LOW LEVEL KEYBOARD HOOK

Ten moduł używa Windows API bezpośrednio przez ctypes.
Działa dokładnie jak AutoHotkey - przechwytuje klawisze na poziomie systemu.

Data: 2025-11-03
Wersja: 4.0
"""

import sys
import json
import os
import subprocess
import time
import threading
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Callable, Set
from ctypes import windll, CFUNCTYPE, c_int, c_void_p, byref, Structure, POINTER
from ctypes.wintypes import DWORD, WPARAM, LPARAM, MSG

# PyQt6 dla GUI
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QFileDialog, QMessageBox, QHeaderView, QGroupBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont

# pynput dla symulacji (bezpieczne)
try:
    from pynput.keyboard import Controller as KeyboardController
    from pynput.mouse import Controller as MouseController
except ImportError:
    print("BŁĄD: Brak biblioteki 'pynput'. Uruchom: pip install pynput")
    sys.exit(1)

# pyperclip dla schowka
try:
    import pyperclip
except ImportError:
    print("BŁĄD: Brak biblioteki 'pyperclip'. Uruchom: pip install pyperclip")
    sys.exit(1)

# Windows API do przechwytywania klawiszy
try:
    import win32api
    import win32con
except ImportError:
    print("BŁĄD: Brak biblioteki 'pywin32'. Uruchom: pip install pywin32")
    sys.exit(1)


# ============================================================================
# WINDOWS API KEYBOARD HOOK (JAK AUTOHOTKEY)
# ============================================================================

# Stałe Windows API
WH_KEYBOARD_LL = 13
WM_KEYDOWN = 0x0100
WM_KEYUP = 0x0101
WM_SYSKEYDOWN = 0x0104
WM_SYSKEYUP = 0x0105

# Kody klawiszy
VK_CONTROL = 0x11
VK_MENU = 0x12  # Alt
VK_SHIFT = 0x10
VK_LWIN = 0x5B
VK_RWIN = 0x5C

class KBDLLHOOKSTRUCT(Structure):
    _fields_ = [
        ("vkCode", DWORD),
        ("scanCode", DWORD),
        ("flags", DWORD),
        ("time", DWORD),
        ("dwExtraInfo", POINTER(DWORD))
    ]

# Typ callbacku dla hooka
HOOKPROC = CFUNCTYPE(c_int, c_int, WPARAM, POINTER(KBDLLHOOKSTRUCT))


class WindowsKeyboardHook:
    """
    Niskopoziomowy hook klawiatury Windows (jak AutoHotkey).
    Używa SetWindowsHookEx z WH_KEYBOARD_LL.
    """
    
    def __init__(self):
        self.hooked = None
        self.pressed_keys: Set[int] = set()
        self.shortcuts: Dict[str, Dict] = {}
        self.on_shortcut_callback = None
        self.running = False
        self.thread = None
        self.last_trigger_time = 0
        self.debounce = 0.3
        
    def register_shortcut(self, name: str, keys: Set[int], callback: Callable):
        """
        Rejestruje skrót.
        
        Args:
            name: Nazwa skrótu
            keys: Zbiór kodów klawiszy (VK_*)
            callback: Funkcja wywoływana po wciśnięciu
        """
        self.shortcuts[name] = {
            'keys': keys,
            'callback': callback
        }
        print(f"✅ Zarejestrowano: {name} -> {keys}")
    
    def unregister_shortcut(self, name: str):
        """Usuwa skrót."""
        if name in self.shortcuts:
            del self.shortcuts[name]
            print(f"🗑️ Usunięto: {name}")
    
    def clear_shortcuts(self):
        """Usuwa wszystkie skróty."""
        self.shortcuts.clear()
        print("🗑️ Wyczyszczono wszystkie skróty")
    
    def parse_hotkey(self, hotkey_str: str) -> Set[int]:
        """
        Parsuje string skrótu na kody VK.
        'Ctrl+Shift+A' -> {VK_CONTROL, VK_SHIFT, 0x41}
        """
        keys = set()
        parts = [p.strip().upper() for p in hotkey_str.split('+')]
        
        for part in parts:
            if part in ['CTRL', 'CONTROL']:
                keys.add(VK_CONTROL)
            elif part == 'ALT':
                keys.add(VK_MENU)
            elif part == 'SHIFT':
                keys.add(VK_SHIFT)
            elif part in ['WIN', 'WINDOWS']:
                keys.add(VK_LWIN)
            elif part == 'SPACE':
                keys.add(0x20)
            elif part == 'ENTER':
                keys.add(0x0D)
            elif part == 'TAB':
                keys.add(0x09)
            elif part == 'ESC' or part == 'ESCAPE':
                keys.add(0x1B)
            elif part.startswith('F') and len(part) <= 3:
                # F1-F12
                try:
                    num = int(part[1:])
                    if 1 <= num <= 12:
                        keys.add(0x70 + num - 1)
                except:
                    pass
            elif len(part) == 1:
                # Pojedynczy znak - konwertuj na VK
                keys.add(ord(part))
        
        return keys
    
    def check_shortcuts(self):
        """Sprawdza czy aktualne klawisze pasują do skrótu."""
        current_time = time.time()
        
        # Debouncing
        if current_time - self.last_trigger_time < self.debounce:
            return
        
        for name, data in self.shortcuts.items():
            required = data['keys']
            
            # Sprawdź czy wszystkie wymagane klawisze są wciśnięte
            if required.issubset(self.pressed_keys):
                # Sprawdź czy nie ma dodatkowych klawiszy (żeby Ctrl+A nie uruchamiało Ctrl+Alt+A)
                if len(self.pressed_keys) == len(required):
                    print(f"🎯 WYZWOLONO: {name}")
                    self.last_trigger_time = current_time
                    
                    # Wywołaj callback
                    if data['callback']:
                        try:
                            data['callback']()
                        except Exception as e:
                            print(f"❌ Błąd wykonania: {e}")
                    break
    
    def keyboard_proc(self, nCode, wParam, lParam):
        """Callback hooka klawiatury."""
        if nCode >= 0:
            kbd = lParam.contents
            vk_code = kbd.vkCode
            
            # Keydown
            if wParam in [WM_KEYDOWN, WM_SYSKEYDOWN]:
                self.pressed_keys.add(vk_code)
                self.check_shortcuts()
            
            # Keyup
            elif wParam in [WM_KEYUP, WM_SYSKEYUP]:
                if vk_code in self.pressed_keys:
                    self.pressed_keys.remove(vk_code)
        
        # Przepuść dalej (NIE blokuj!)
        return windll.user32.CallNextHookEx(self.hooked, nCode, wParam, lParam)
    
    def install_hook(self):
        """Instaluje hook klawiatury."""
        self.hook_proc = HOOKPROC(self.keyboard_proc)
        self.hooked = windll.user32.SetWindowsHookExA(
            WH_KEYBOARD_LL,
            self.hook_proc,
            windll.kernel32.GetModuleHandleW(None),
            0
        )
        
        if not self.hooked:
            print("❌ Nie udało się zainstalować hooka!")
            return False
        
        print("✅ Hook klawiatury zainstalowany (WH_KEYBOARD_LL)")
        return True
    
    def uninstall_hook(self):
        """Usuwa hook."""
        if self.hooked:
            windll.user32.UnhookWindowsHookEx(self.hooked)
            self.hooked = None
            print("🗑️ Hook odinstalowany")
    
    def message_loop(self):
        """Pętla wiadomości Windows."""
        msg = MSG()
        while self.running:
            # GetMessage blokuje dopóki nie przyjdzie wiadomość
            if windll.user32.GetMessageW(byref(msg), None, 0, 0) != 0:
                windll.user32.TranslateMessage(byref(msg))
                windll.user32.DispatchMessageW(byref(msg))
            else:
                break
    
    def start(self):
        """Uruchamia hook w osobnym wątku."""
        if self.running:
            print("⚠️ Hook już działa!")
            return
        
        self.running = True
        
        def hook_thread():
            if self.install_hook():
                self.message_loop()
            self.uninstall_hook()
        
        self.thread = threading.Thread(target=hook_thread, daemon=True)
        self.thread.start()
        print("🎯 Hook uruchomiony w osobnym wątku")
    
    def stop(self):
        """Zatrzymuje hook."""
        self.running = False
        
        # Wyślij wiadomość WM_QUIT do pętli wiadomości
        if self.thread and self.thread.is_alive():
            windll.user32.PostThreadMessageW(
                windll.kernel32.GetCurrentThreadId(),
                0x0012,  # WM_QUIT
                0, 0
            )
        
        self.pressed_keys.clear()
        print("⏹️ Hook zatrzymany")


# ============================================================================
# ZARZĄDZANIE KONFIGURACJĄ
# ============================================================================

class ConfigManager:
    """Zarządza zapisem/odczytem konfiguracji JSON."""
    
    def __init__(self, config_file: str = "shortcuts_config.json"):
        self.config_file = config_file
    
    def load(self) -> List[Dict]:
        """Wczytuje skróty z pliku."""
        if not os.path.exists(self.config_file):
            print(f"⚠️ Plik {self.config_file} nie istnieje - tworzę pusty")
            self.save([])
            return []
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                print(f"📂 Wczytano {len(data)} skrótów z {self.config_file}")
                return data
        except Exception as e:
            print(f"❌ Błąd wczytywania: {e}")
            return []
    
    def save(self, shortcuts: List[Dict]):
        """Zapisuje skróty do pliku."""
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(shortcuts, f, indent=2, ensure_ascii=False)
            print(f"💾 Zapisano {len(shortcuts)} skrótów do {self.config_file}")
        except Exception as e:
            print(f"❌ Błąd zapisu: {e}")


# ============================================================================
# WYKONAWCA AKCJI
# ============================================================================

class ActionExecutor:
    """Wykonuje różne typy akcji."""
    
    def __init__(self):
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
    
    def execute(self, action_type: str, data: Dict) -> tuple:
        """Wykonuje akcję."""
        handlers = {
            'text': lambda: self.type_text(data.get('text', '')),
            'app': lambda: self.run_app(data.get('path', '')),
            'file': lambda: self.open_file(data.get('path', '')),
            'folder': lambda: self.open_folder(data.get('path', '')),
            'command': lambda: self.run_command(data.get('command', '')),
            'url': lambda: self.open_url(data.get('url', '')),
        }
        
        handler = handlers.get(action_type)
        if handler:
            return handler()
        else:
            return False, f"Nieznany typ akcji: {action_type}"
    
    def type_text(self, text: str) -> tuple:
        """Wpisuje tekst."""
        if not text:
            return False, "Pusty tekst"
        
        try:
            time.sleep(0.1)
            self.keyboard.type(text)
            return True, f"Wpisano: {text[:30]}..."
        except Exception as e:
            return False, f"Błąd: {e}"
    
    def run_app(self, path: str) -> tuple:
        """Uruchamia aplikację."""
        if not path:
            return False, "Brak ścieżki"
        
        try:
            subprocess.Popen(path, shell=True)
            return True, f"Uruchomiono: {Path(path).name}"
        except Exception as e:
            return False, f"Błąd: {e}"
    
    def open_file(self, path: str) -> tuple:
        """Otwiera plik."""
        if not path:
            return False, "Brak ścieżki"
        
        try:
            os.startfile(path)
            return True, f"Otwarto: {Path(path).name}"
        except Exception as e:
            return False, f"Błąd: {e}"
    
    def open_folder(self, path: str) -> tuple:
        """Otwiera folder."""
        if not path:
            return False, "Brak ścieżki"
        
        try:
            os.startfile(path)
            return True, f"Otwarto: {Path(path).name}"
        except Exception as e:
            return False, f"Błąd: {e}"
    
    def run_command(self, command: str) -> tuple:
        """Wykonuje komendę."""
        if not command:
            return False, "Pusta komenda"
        
        try:
            subprocess.Popen(command, shell=True)
            return True, "Wykonano komendę"
        except Exception as e:
            return False, f"Błąd: {e}"
    
    def open_url(self, url: str) -> tuple:
        """Otwiera URL."""
        if not url:
            return False, "Pusty URL"
        
        try:
            import webbrowser
            webbrowser.open(url)
            return True, f"Otwarto: {url}"
        except Exception as e:
            return False, f"Błąd: {e}"


# ============================================================================
# WIDGET DO PRZECHWYTYWANIA SKRÓTÓW
# ============================================================================

class ShortcutCaptureWidget(QWidget):
    """Widget z przyciskiem do przechwytywania kombinacji klawiszy."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        self.display_field = QLineEdit()
        self.display_field.setReadOnly(True)
        self.display_field.setPlaceholderText("Kliknij 'Przechwytuj'...")
        self.display_field.setFixedHeight(35)
        layout.addWidget(self.display_field)
        
        self.capture_btn = QPushButton("🎯 Przechwytuj")
        self.capture_btn.setFixedHeight(35)
        self.capture_btn.setFixedWidth(140)
        self.capture_btn.clicked.connect(self.start_capture)
        layout.addWidget(self.capture_btn)
        
        self.clear_btn = QPushButton("✖")
        self.clear_btn.setFixedWidth(40)
        self.clear_btn.setFixedHeight(35)
        self.clear_btn.clicked.connect(self.clear)
        layout.addWidget(self.clear_btn)
        
        self.setLayout(layout)
        
        self.capture_timer = QTimer()
        self.capture_timer.timeout.connect(self.check_keys)
        self.capturing = False
    
    def start_capture(self):
        if self.capturing:
            self.stop_capture()
            return
        
        self.capturing = True
        self.display_field.setText("⏳ Naciśnij kombinację...")
        self.display_field.setStyleSheet("background-color: #FFF9C4;")
        self.capture_btn.setText("⏹ Stop")
        self.capture_btn.setStyleSheet("background-color: #f44336; color: white;")
        self.capture_timer.start(50)
    
    def stop_capture(self):
        self.capturing = False
        self.capture_timer.stop()
        self.display_field.setStyleSheet("")
        self.capture_btn.setText("🎯 Przechwytuj")
        self.capture_btn.setStyleSheet("")
    
    def check_keys(self):
        if not self.capturing:
            return
        
        modifiers = []
        if win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000:
            modifiers.append("Ctrl")
        if win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000:
            modifiers.append("Alt")
        if win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000:
            modifiers.append("Shift")
        
        main_key = None
        
        # A-Z
        for i in range(ord('A'), ord('Z') + 1):
            if win32api.GetAsyncKeyState(i) & 0x8000:
                main_key = chr(i)
                break
        
        # 0-9
        if not main_key:
            for i in range(ord('0'), ord('9') + 1):
                if win32api.GetAsyncKeyState(i) & 0x8000:
                    main_key = chr(i)
                    break
        
        # F1-F12
        if not main_key:
            for i in range(1, 13):
                if win32api.GetAsyncKeyState(0x70 + i - 1) & 0x8000:
                    main_key = f"F{i}"
                    break
        
        if main_key and modifiers:
            shortcut = "+".join(modifiers + [main_key])
            self.display_field.setText(shortcut)
            self.stop_capture()
    
    def clear(self):
        self.display_field.clear()
        self.stop_capture()
    
    def text(self):
        return self.display_field.text().strip()
    
    def setText(self, text):
        self.display_field.setText(text)


# ============================================================================
# GŁÓWNE OKNO
# ============================================================================

class ShortcutsWindow(QMainWindow):
    """Główne okno aplikacji."""
    
    shortcut_triggered = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
        self.hook = WindowsKeyboardHook()
        self.config_manager = ConfigManager()
        self.action_executor = ActionExecutor()
        self.shortcuts = []
        
        self.shortcut_triggered.connect(self.execute_shortcut_action)
        
        self.setWindowTitle("Shortcuts v4 - Windows Keyboard Hook (jak AutoHotkey)")
        self.setGeometry(100, 100, 1400, 900)
        
        self.load_config()
        self.init_ui()
        self.setup_styling()
    
    def init_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Header
        header = QWidget()
        h_layout = QHBoxLayout(header)
        
        title = QLabel("🎯 Shortcuts v4")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        h_layout.addWidget(title)
        
        h_layout.addStretch()
        
        self.status_label = QLabel("System NIEAKTYWNY")
        self.status_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.status_label.setStyleSheet("background-color: #ccc; color: #333; padding: 12px 24px; border-radius: 6px;")
        h_layout.addWidget(self.status_label)
        
        self.toggle_btn = QPushButton("▶️ URUCHOM")
        self.toggle_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.toggle_btn.setFixedHeight(50)
        self.toggle_btn.clicked.connect(self.toggle_system)
        h_layout.addWidget(self.toggle_btn)
        
        layout.addWidget(header)
        
        # Formularz
        form_group = QGroupBox("➕ Nowy skrót")
        form_layout = QHBoxLayout(form_group)
        
        form_layout.addWidget(QLabel("Nazwa:"))
        self.name_input = QLineEdit()
        self.name_input.setFixedWidth(150)
        self.name_input.setFixedHeight(35)
        form_layout.addWidget(self.name_input)
        
        form_layout.addWidget(QLabel("Skrót:"))
        self.hotkey_input = ShortcutCaptureWidget()
        form_layout.addWidget(self.hotkey_input)
        
        form_layout.addWidget(QLabel("Akcja:"))
        self.action_combo = QComboBox()
        self.action_combo.addItems(["Wpisz tekst", "Uruchom aplikację", "Otwórz plik", "Otwórz folder", "Komenda", "Otwórz URL"])
        self.action_combo.setFixedWidth(150)
        self.action_combo.setFixedHeight(35)
        form_layout.addWidget(self.action_combo)
        
        form_layout.addWidget(QLabel("Wartość:"))
        self.value_input = QLineEdit()
        self.value_input.setFixedHeight(35)
        form_layout.addWidget(self.value_input)
        
        add_btn = QPushButton("➕ Dodaj")
        add_btn.setFixedHeight(35)
        add_btn.clicked.connect(self.add_shortcut)
        form_layout.addWidget(add_btn)
        
        layout.addWidget(form_group)
        
        # Tabela
        table_group = QGroupBox("📋 Skróty")
        table_layout = QVBoxLayout(table_group)
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Nazwa", "Skrót", "Akcja", "Wartość"])
        self.table.horizontalHeader().setStretchLastSection(True)
        table_layout.addWidget(self.table)
        
        btn_layout = QHBoxLayout()
        
        delete_btn = QPushButton("🗑️ Usuń")
        delete_btn.clicked.connect(self.delete_shortcut)
        btn_layout.addWidget(delete_btn)
        
        test_btn = QPushButton("🧪 Test")
        test_btn.clicked.connect(self.test_shortcut)
        btn_layout.addWidget(test_btn)
        
        btn_layout.addStretch()
        
        table_layout.addLayout(btn_layout)
        layout.addWidget(table_group)
        
        # Footer
        self.footer_status = QLabel("Gotowy")
        self.footer_status.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.footer_status)
        
        self.refresh_table()
    
    def setup_styling(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #2b2b2b; }
            QWidget { background-color: #2b2b2b; color: #ffffff; }
            QGroupBox {
                background-color: #3c3f41;
                border: 2px solid #555;
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 12px;
                color: #fff;
                font-weight: bold;
            }
            QLineEdit, QComboBox {
                background-color: #fff;
                color: #000;
                border: 2px solid #555;
                border-radius: 4px;
                padding: 6px;
            }
            QTableWidget {
                background-color: #fff;
                color: #000;
                border: 2px solid #555;
            }
            QHeaderView::section {
                background-color: #4CAF50;
                color: #fff;
                font-weight: bold;
                padding: 8px;
            }
            QPushButton {
                background-color: #2196F3;
                color: #fff;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover { background-color: #1976D2; }
            QLabel { color: #fff; }
        """)
    
    def load_config(self):
        self.shortcuts = self.config_manager.load()
    
    def save_config(self):
        self.config_manager.save(self.shortcuts)
    
    def add_shortcut(self):
        name = self.name_input.text().strip()
        hotkey = self.hotkey_input.text().strip()
        action = self.action_combo.currentText()
        value = self.value_input.text().strip()
        
        if not name or not hotkey or not value:
            QMessageBox.warning(self, "Błąd", "Wypełnij wszystkie pola!")
            return
        
        type_map = {
            "Wpisz tekst": "text",
            "Uruchom aplikację": "app",
            "Otwórz plik": "file",
            "Otwórz folder": "folder",
            "Komenda": "command",
            "Otwórz URL": "url"
        }
        
        shortcut = {
            'name': name,
            'hotkey': hotkey,
            'action_type': type_map[action],
            'action_value': value
        }
        
        self.shortcuts.append(shortcut)
        self.save_config()
        self.refresh_table()
        
        self.name_input.clear()
        self.hotkey_input.clear()
        self.value_input.clear()
        
        self.footer_status.setText(f"✅ Dodano: {name}")
    
    def delete_shortcut(self):
        row = self.table.currentRow()
        if row >= 0:
            name = self.shortcuts[row]['name']
            del self.shortcuts[row]
            self.save_config()
            self.refresh_table()
            self.footer_status.setText(f"🗑️ Usunięto: {name}")
    
    def test_shortcut(self):
        row = self.table.currentRow()
        if row >= 0:
            QTimer.singleShot(500, lambda: self.execute_shortcut_action(self.shortcuts[row]))
    
    def refresh_table(self):
        self.table.setRowCount(len(self.shortcuts))
        for row, s in enumerate(self.shortcuts):
            self.table.setItem(row, 0, QTableWidgetItem(s['name']))
            self.table.setItem(row, 1, QTableWidgetItem(s['hotkey']))
            self.table.setItem(row, 2, QTableWidgetItem(s['action_type']))
            self.table.setItem(row, 3, QTableWidgetItem(s['action_value'][:50]))
    
    def toggle_system(self):
        if self.hook.running:
            self.stop_system()
        else:
            self.start_system()
    
    def start_system(self):
        if not self.shortcuts:
            QMessageBox.warning(self, "Błąd", "Brak skrótów!")
            return
        
        self.hook.clear_shortcuts()
        
        for shortcut in self.shortcuts:
            keys = self.hook.parse_hotkey(shortcut['hotkey'])
            
            def make_callback(s):
                return lambda: self.shortcut_triggered.emit(s)
            
            self.hook.register_shortcut(
                shortcut['name'],
                keys,
                make_callback(shortcut)
            )
        
        self.hook.start()
        
        self.status_label.setText("System AKTYWNY")
        self.status_label.setStyleSheet("background-color: #4CAF50; color: white; padding: 12px 24px; border-radius: 6px;")
        self.toggle_btn.setText("⏹️ ZATRZYMAJ")
        self.footer_status.setText("🎯 System uruchomiony!")
    
    def stop_system(self):
        self.hook.stop()
        
        self.status_label.setText("System NIEAKTYWNY")
        self.status_label.setStyleSheet("background-color: #ccc; color: #333; padding: 12px 24px; border-radius: 6px;")
        self.toggle_btn.setText("▶️ URUCHOM")
        self.footer_status.setText("⏹️ Zatrzymano")
    
    def execute_shortcut_action(self, shortcut: Dict):
        print(f"\n🎯 Wykonuję: {shortcut['name']}")
        
        action_data = {}
        action_type = shortcut['action_type']
        
        if action_type == 'text':
            action_data = {'text': shortcut['action_value']}
        elif action_type in ['app', 'file', 'folder']:
            action_data = {'path': shortcut['action_value']}
        elif action_type == 'command':
            action_data = {'command': shortcut['action_value']}
        elif action_type == 'url':
            action_data = {'url': shortcut['action_value']}
        
        success, message = self.action_executor.execute(action_type, action_data)
        
        if success:
            print(f"✅ {message}")
            self.footer_status.setText(f"✅ {shortcut['name']}: {message}")
        else:
            print(f"❌ {message}")
            self.footer_status.setText(f"❌ {message}")
    
    def closeEvent(self, event):
        self.hook.stop()
        event.accept()


# ============================================================================
# MAIN
# ============================================================================

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Segoe UI", 11))
    
    window = ShortcutsWindow()
    window.show()
    
    sys.exit(app.exec())
