"""
Moduł Shortcuts v3 - System globalnych skrótów klawiszowych (jak AutoHotkey)

Napisany od zera z biblioteką 'keyboard' dla maksymalnej niezawodności.

Funkcjonalności:
- Globalne skróty klawiszowe (Ctrl+Alt+X)
- Wpisywanie tekstu / uruchamianie aplikacji
- Szablony tekstowe z podstawieniami
- Menu szablonów i skrótów
- Sekwencje kliknięć myszką
- Frazy klawiaturowe (hotstrings)

Autor: Pro Ka Po Comer
Data: 2025-11-03
Wersja: 3.0
"""

import sys
import json
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Callable

# Biblioteka keyboard - USUNIĘTA (blokowała klawiaturę!)
# Zamiast tego użyjemy pynput.Listener w osobnym wątku

# PyQt6 dla GUI
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QLineEdit, QTextEdit, QTableWidget, QTableWidgetItem,
    QComboBox, QTabWidget, QFileDialog, QMessageBox, QHeaderView,
    QGroupBox, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QColor, QCursor

# pynput do symulacji klawiatury/myszki
try:
    from pynput.keyboard import Controller as KeyboardController
    from pynput.mouse import Controller as MouseController, Button
except ImportError:
    print("BŁĄD: Brak biblioteki 'pynput'. Uruchom: pip install pynput")
    sys.exit(1)

# pyperclip do schowka
try:
    import pyperclip
except ImportError:
    print("BŁĄD: Brak biblioteki 'pyperclip'. Uruchom: pip install pyperclip")
    sys.exit(1)

# Windows API dla przechwytywania klawiszy
try:
    import win32api
    import win32con
except ImportError:
    print("BŁĄD: Brak biblioteki 'pywin32'. Uruchom: pip install pywin32")
    sys.exit(1)


# ============================================================================
# WIDGET DO PRZECHWYTYWANIA SKRÓTÓW
# ============================================================================

class ShortcutCaptureWidget(QWidget):
    """Widget do przechwytywania kombinacji klawiszy - używa przycisku zamiast pola tekstowego"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_keys = set()
        self.setup_ui()
    
    def setup_ui(self):
        """Buduje interfejs"""
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Pole tylko do odczytu - pokazuje przechwycony skrót
        self.display_field = QLineEdit()
        self.display_field.setReadOnly(True)
        self.display_field.setPlaceholderText("Kliknij 'Przechwytuj' i naciśnij kombinację...")
        self.display_field.setFixedHeight(35)
        self.display_field.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.display_field)
        
        # Przycisk do rozpoczęcia przechwytywania
        self.capture_btn = QPushButton("🎯 Przechwytuj")
        self.capture_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px;")
        self.capture_btn.setFixedHeight(35)
        self.capture_btn.setFixedWidth(140)
        self.capture_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.capture_btn.clicked.connect(self.start_capture)
        layout.addWidget(self.capture_btn)
        
        # Przycisk czyszczenia
        self.clear_btn = QPushButton("✖")
        self.clear_btn.clicked.connect(self.clear)
        self.clear_btn.setFixedWidth(40)
        self.clear_btn.setFixedHeight(35)
        self.clear_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
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
        self.display_field.setStyleSheet("background-color: #FFF9C4; font-weight: bold;")
        self.capture_btn.setText("⏹ Stop")
        self.capture_btn.setStyleSheet("background-color: #f44336; color: white; font-weight: bold; padding: 5px;")
        
        # Uruchom timer
        self.capture_timer.start(50)  # Sprawdzaj co 50ms
    
    def stop_capture(self):
        """Zatrzymuje przechwytywanie"""
        self.capturing = False
        self.capture_timer.stop()
        self.display_field.setStyleSheet("")
        self.capture_btn.setText("🎯 Przechwytuj")
        self.capture_btn.setStyleSheet("background-color: #2196F3; color: white; font-weight: bold; padding: 5px;")
    
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
        # Widget zawsze używa przycisku, więc ignorujemy ten parametr
        pass


# ============================================================================
# CZĘŚĆ 1: ZARZĄDZANIE SKRÓTAMI (HotkeyManager)
# ============================================================================

class HotkeyManager:
    """
    Menedżer globalnych skrótów klawiszowych używający pynput.Listener.
    BEZPIECZNE - nie blokuje klawiatury systemowej!
    """
    
    def __init__(self):
        self.shortcuts = {}  # {name: {'hotkey': set, 'callback': callable}}
        self.is_active = False
        self.listener = None
        self.pressed_keys = set()
        self.last_triggered = None
        self.debounce_time = 0.3  # 300ms debounce
    
    def parse_hotkey(self, hotkey_str: str) -> set:
        """
        Parsuje string skrótu na zbiór klawiszy pynput.
        'Ctrl+Alt+N' -> {Key.ctrl_l, Key.alt_l, KeyCode.from_char('n')}
        """
        from pynput.keyboard import Key, KeyCode
        
        if not hotkey_str:
            return set()
        
        keys = set()
        parts = hotkey_str.split('+')
        
        for part in parts:
            part = part.strip().lower()
            
            # Modyfikatory
            if part in ['ctrl', 'control']:
                keys.add(Key.ctrl_l)
                keys.add(Key.ctrl)
            elif part == 'alt':
                keys.add(Key.alt_l)
                keys.add(Key.alt)
            elif part == 'shift':
                keys.add(Key.shift_l)
                keys.add(Key.shift)
            elif part in ['win', 'windows', 'cmd']:
                keys.add(Key.cmd)
            # Specjalne
            elif part == 'space':
                keys.add(Key.space)
            elif part == 'enter':
                keys.add(Key.enter)
            elif part == 'tab':
                keys.add(Key.tab)
            elif part == 'backspace':
                keys.add(Key.backspace)
            elif part == 'delete':
                keys.add(Key.delete)
            elif part == 'esc' or part == 'escape':
                keys.add(Key.esc)
            elif part == 'home':
                keys.add(Key.home)
            elif part == 'end':
                keys.add(Key.end)
            elif part == 'pageup':
                keys.add(Key.page_up)
            elif part == 'pagedown':
                keys.add(Key.page_down)
            elif part == 'left':
                keys.add(Key.left)
            elif part == 'right':
                keys.add(Key.right)
            elif part == 'up':
                keys.add(Key.up)
            elif part == 'down':
                keys.add(Key.down)
            # F1-F12
            elif part.startswith('f') and len(part) <= 3:
                try:
                    num = int(part[1:])
                    if 1 <= num <= 12:
                        keys.add(getattr(Key, f'f{num}'))
                except:
                    pass
            # Normalne znaki
            elif len(part) == 1:
                keys.add(KeyCode.from_char(part))
        
        return keys
    
    def register(self, name: str, hotkey: str, callback: Callable):
        """Rejestruje skrót."""
        try:
            parsed = self.parse_hotkey(hotkey)
            if not parsed:
                print(f"❌ Nie można sparsować skrótu: {hotkey}")
                return False
            
            self.shortcuts[name] = {
                'hotkey': parsed,
                'callback': callback,
                'original': hotkey
            }
            
            print(f"✅ Zarejestrowano: {name} -> {hotkey}")
            return True
            
        except Exception as e:
            print(f"❌ Błąd rejestracji '{name}': {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def unregister(self, name: str):
        """Wyrejestrowuje skrót."""
        if name in self.shortcuts:
            del self.shortcuts[name]
            print(f"�️ Wyrejestrowano: {name}")
            return True
        return False
    
    def unregister_all(self):
        """Wyrejestrowuje wszystkie skróty."""
        self.shortcuts.clear()
        print("🗑️ Wyrejestrowano wszystkie skróty")
    
    def on_press(self, key):
        """Callback dla wciśniętego klawisza."""
        try:
            self.pressed_keys.add(key)
            self.check_shortcuts()
        except Exception as e:
            print(f"⚠️ Błąd on_press: {e}")
    
    def on_release(self, key):
        """Callback dla puszczonego klawisza."""
        try:
            if key in self.pressed_keys:
                self.pressed_keys.remove(key)
        except Exception as e:
            print(f"⚠️ Błąd on_release: {e}")
    
    def check_shortcuts(self):
        """Sprawdza czy aktualne klawisze pasują do jakiegoś skrótu."""
        import time
        
        # Debouncing
        current_time = time.time()
        if self.last_triggered and (current_time - self.last_triggered) < self.debounce_time:
            return
        
        for name, data in self.shortcuts.items():
            required_keys = data['hotkey']
            
            # Sprawdź czy wszystkie wymagane klawisze są wciśnięte
            # Bierzemy pod uwagę że Ctrl może być ctrl_l lub ctrl, podobnie Alt i Shift
            if self.keys_match(required_keys, self.pressed_keys):
                print(f"🎯 Uruchamiam skrót: {name}")
                self.last_triggered = current_time
                
                # Wykonaj w głównym wątku Qt
                try:
                    data['callback']()
                except Exception as e:
                    print(f"❌ Błąd wykonania skrótu '{name}': {e}")
                break
    
    def keys_match(self, required: set, pressed: set) -> bool:
        """Sprawdza czy wciśnięte klawisze pasują do wymaganych."""
        from pynput.keyboard import Key
        
        # Dla każdego wymaganego klawisza sprawdź czy jest wciśnięty
        for req_key in required:
            # Dla modyfikatorów sprawdź warianty (ctrl_l/ctrl_r/ctrl)
            if req_key in [Key.ctrl_l, Key.ctrl]:
                if not any(k in pressed for k in [Key.ctrl_l, Key.ctrl_r, Key.ctrl]):
                    return False
            elif req_key in [Key.alt_l, Key.alt]:
                if not any(k in pressed for k in [Key.alt_l, Key.alt_r, Key.alt]):
                    return False
            elif req_key in [Key.shift_l, Key.shift]:
                if not any(k in pressed for k in [Key.shift_l, Key.shift_r, Key.shift]):
                    return False
            else:
                if req_key not in pressed:
                    return False
        
        # Sprawdź czy liczba wciśniętych klawiszy się zgadza (±1 dla wariantów modyfikatorów)
        if abs(len(pressed) - len(required)) > 2:
            return False
        
        return True
    
    def start(self):
        """Uruchamia listener."""
        if self.listener:
            self.stop()
        
        from pynput.keyboard import Listener
        
        self.is_active = True
        self.pressed_keys.clear()
        
        # Uruchom listener w osobnym wątku (NIE suppress - nie blokuje!)
        self.listener = Listener(
            on_press=self.on_press,
            on_release=self.on_release,
            suppress=False  # WAŻNE - nie blokuj klawiatury!
        )
        self.listener.start()
        
        print("🎯 System skrótów AKTYWNY (pynput listener)")
    
    def stop(self):
        """Zatrzymuje listener."""
        if self.listener:
            self.listener.stop()
            self.listener = None
        
        self.is_active = False
        self.pressed_keys.clear()
        print("⏹️ System skrótów ZATRZYMANY")
    
    def get_count(self) -> int:
        """Zwraca liczbę zarejestrowanych skrótów."""
        return len(self.shortcuts)


# ============================================================================
# CZĘŚĆ 2: ZARZĄDZANIE KONFIGURACJĄ (ConfigManager)
# ============================================================================

class ConfigManager:
    """
    Menedżer konfiguracji - zapisuje i wczytuje skróty z pliku JSON.
    """
    
    def __init__(self, config_file: str = "shortcuts_config.json"):
        self.config_file = Path(config_file)
        self.shortcuts = []
    
    def load(self) -> List[Dict]:
        """Wczytuje konfigurację z pliku."""
        if not self.config_file.exists():
            print(f"⚠️  Plik {self.config_file} nie istnieje - tworzę pusty")
            return []
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                self.shortcuts = json.load(f)
            print(f"📂 Wczytano {len(self.shortcuts)} skrótów z {self.config_file}")
            return self.shortcuts
        except Exception as e:
            print(f"❌ Błąd wczytywania konfiguracji: {e}")
            return []
    
    def save(self, shortcuts: List[Dict]):
        """Zapisuje konfigurację do pliku."""
        try:
            self.shortcuts = shortcuts
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(shortcuts, f, indent=2, ensure_ascii=False)
            print(f"💾 Zapisano {len(shortcuts)} skrótów do {self.config_file}")
            return True
        except Exception as e:
            print(f"❌ Błąd zapisywania konfiguracji: {e}")
            return False
    
    def export_to(self, filepath: str, shortcuts: List[Dict]):
        """Eksportuje konfigurację do wskazanego pliku."""
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(shortcuts, f, indent=2, ensure_ascii=False)
            print(f"📤 Wyeksportowano do {filepath}")
            return True
        except Exception as e:
            print(f"❌ Błąd eksportu: {e}")
            return False
    
    def import_from(self, filepath: str) -> List[Dict]:
        """Importuje konfigurację ze wskazanego pliku."""
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                shortcuts = json.load(f)
            print(f"📥 Zaimportowano {len(shortcuts)} skrótów z {filepath}")
            return shortcuts
        except Exception as e:
            print(f"❌ Błąd importu: {e}")
            return []


# ============================================================================
# CZĘŚĆ 3: WYKONYWANIE AKCJI (ActionExecutor)
# ============================================================================

class ActionExecutor:
    """
    Wykonuje różne typy akcji dla skrótów.
    """
    
    def __init__(self):
        self.keyboard = KeyboardController()
        self.mouse = MouseController()
    
    def execute(self, action_type: str, action_data: Dict) -> tuple:
        """
        Wykonuje akcję na podstawie typu i danych.
        
        Returns:
            (success: bool, message: str)
        """
        try:
            if action_type == "text":
                return self.type_text(action_data.get('text', ''))
            
            elif action_type == "app":
                return self.run_application(action_data.get('path', ''))
            
            elif action_type == "file":
                return self.open_file(action_data.get('path', ''))
            
            elif action_type == "folder":
                return self.open_folder(action_data.get('path', ''))
            
            elif action_type == "template":
                return self.insert_template(action_data.get('template', ''))
            
            elif action_type == "command":
                return self.run_command(action_data.get('command', ''))
            
            elif action_type == "url":
                return self.open_url(action_data.get('url', ''))
            
            elif action_type == "menu_templates":
                return True, "Menu szablonów (do implementacji)"
            
            elif action_type == "menu_shortcuts":
                return True, "Menu skrótów (do implementacji)"
            
            elif action_type == "click_sequence":
                return True, "Sekwencja kliknięć (do implementacji)"
            
            else:
                return False, f"Nieznany typ akcji: {action_type}"
                
        except Exception as e:
            return False, f"Błąd wykonania: {str(e)}"
    
    def type_text(self, text: str) -> tuple:
        """Wpisuje tekst."""
        if not text:
            return False, "Brak tekstu do wpisania"
        
        try:
            # Małe opóźnienie dla stabilności
            time.sleep(0.1)
            self.keyboard.type(text)
            return True, f"Wpisano tekst ({len(text)} znaków)"
        except Exception as e:
            return False, f"Błąd wpisywania: {str(e)}"
    
    def run_application(self, path: str) -> tuple:
        """Uruchamia aplikację."""
        if not path:
            return False, "Brak ścieżki do aplikacji"
        
        try:
            subprocess.Popen(path, shell=True)
            return True, f"Uruchomiono: {Path(path).name}"
        except Exception as e:
            return False, f"Błąd uruchamiania: {str(e)}"
    
    def open_file(self, path: str) -> tuple:
        """Otwiera plik."""
        if not path:
            return False, "Brak ścieżki do pliku"
        
        try:
            os.startfile(path)
            return True, f"Otwarto: {Path(path).name}"
        except Exception as e:
            return False, f"Błąd otwierania: {str(e)}"
    
    def open_folder(self, path: str) -> tuple:
        """Otwiera folder."""
        if not path:
            return False, "Brak ścieżki do folderu"
        
        try:
            os.startfile(path)
            return True, f"Otwarto folder: {Path(path).name}"
        except Exception as e:
            return False, f"Błąd otwierania: {str(e)}"
    
    def insert_template(self, template: str) -> tuple:
        """Wstawia szablon z podstawieniami."""
        if not template:
            return False, "Pusty szablon"
        
        try:
            # Podstawienia
            text = template.replace('{{data}}', datetime.now().strftime('%Y-%m-%d'))
            text = text.replace('{{godzina}}', datetime.now().strftime('%H:%M'))
            text = text.replace('{{dzien}}', datetime.now().strftime('%A'))
            text = text.replace('{{miesiac}}', datetime.now().strftime('%B'))
            
            time.sleep(0.1)
            self.keyboard.type(text)
            return True, f"Wstawiono szablon ({len(text)} znaków)"
        except Exception as e:
            return False, f"Błąd szablonu: {str(e)}"
    
    def run_command(self, command: str) -> tuple:
        """Wykonuje komendę systemową."""
        if not command:
            return False, "Pusta komenda"
        
        try:
            subprocess.Popen(command, shell=True)
            return True, f"Wykonano komendę"
        except Exception as e:
            return False, f"Błąd komendy: {str(e)}"
    
    def open_url(self, url: str) -> tuple:
        """Otwiera URL w przeglądarce."""
        if not url:
            return False, "Pusty URL"
        
        try:
            import webbrowser
            webbrowser.open(url)
            return True, f"Otwarto URL: {url}"
        except Exception as e:
            return False, f"Błąd otwierania URL: {str(e)}"


# ============================================================================
# CZĘŚĆ 4: GŁÓWNE OKNO APLIKACJI (ShortcutsWindow)
# ============================================================================

class ShortcutsWindow(QMainWindow):
    """Główne okno aplikacji Shortcuts v3."""
    
    # Sygnał do bezpiecznego wykonywania akcji z wątku pynput
    shortcut_triggered = pyqtSignal(dict)
    
    def __init__(self):
        super().__init__()
        
        # Menedżery
        self.hotkey_manager = HotkeyManager()
        self.config_manager = ConfigManager()
        self.action_executor = ActionExecutor()
        
        # Dane
        self.shortcuts = []
        
        # Podłącz sygnał
        self.shortcut_triggered.connect(self.execute_shortcut_action)
        
        # UI
        self.setWindowTitle("Shortcuts v3 - System globalnych skrótów klawiszowych")
        self.setGeometry(100, 100, 1400, 900)
        
        # Ustaw czcionkę dla całej aplikacji
        app_font = QFont("Segoe UI", 11)
        self.setFont(app_font)
        
        # Wczytaj konfigurację
        self.load_config()
        
        # Inicjalizuj UI
        self.init_ui()
        
        # Ustaw styling
        self.setup_styling()
    
    def init_ui(self):
        """Inicjalizuje interfejs użytkownika."""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # ===== NAGŁÓWEK =====
        header = self.create_header()
        layout.addWidget(header)
        
        # ===== GŁÓWNA ZAWARTOŚĆ - BEZ ZAKŁADEK =====
        content = self.create_shortcuts_content()
        layout.addWidget(content)
        
        # ===== STOPKA - STATUS =====
        footer = self.create_footer()
        layout.addWidget(footer)
    
    def create_header(self) -> QWidget:
        """Tworzy nagłówek z tytułem i statusem."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Tytuł
        title = QLabel("🎯 Shortcuts v3")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        layout.addWidget(title)
        
        layout.addStretch()
        
        # Status
        self.status_label = QLabel("System NIEAKTYWNY")
        self.status_label.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.status_label.setStyleSheet(
            "background-color: #ccc; color: #333; padding: 12px 24px; "
            "border-radius: 6px; font-size: 14pt;"
        )
        layout.addWidget(self.status_label)
        
        # Przycisk Start/Stop
        self.toggle_btn = QPushButton("▶️ URUCHOM SYSTEM")
        self.toggle_btn.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        self.toggle_btn.setFixedHeight(50)
        self.toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                padding: 12px 32px;
                border-radius: 6px;
                font-size: 14pt;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        self.toggle_btn.clicked.connect(self.toggle_system)
        layout.addWidget(self.toggle_btn)
        
        return widget
    
    def create_shortcuts_content(self) -> QWidget:
        """Tworzy główną zawartość - skróty."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 10)
        
        # ===== FORMULARZ DODAWANIA =====
        form_group = QGroupBox("➕ Nowy skrót")
        form_group.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        form_layout = QHBoxLayout(form_group)
        form_layout.setSpacing(15)
        
        # Nazwa
        name_label = QLabel("Nazwa:")
        name_label.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(name_label)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("np. Wstaw email")
        self.name_input.setFixedWidth(180)
        self.name_input.setFixedHeight(35)
        self.name_input.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(self.name_input)
        
        # Rodzaj skrótu
        type_label = QLabel("Rodzaj:")
        type_label.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(type_label)
        self.shortcut_type_combo = QComboBox()
        self.shortcut_type_combo.addItems([
            "Kombinacja klawiszy",
            "Przytrzymaj klawisz",
            "Magiczna fraza"
        ])
        self.shortcut_type_combo.setFixedWidth(160)
        self.shortcut_type_combo.setFixedHeight(35)
        self.shortcut_type_combo.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(self.shortcut_type_combo)
        
        # Skrót klawiszowy
        hotkey_label = QLabel("Skrót:")
        hotkey_label.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(hotkey_label)
        self.hotkey_input = ShortcutCaptureWidget()
        form_layout.addWidget(self.hotkey_input)
        
        # Typ akcji
        action_label = QLabel("Akcja:")
        action_label.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(action_label)
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems([
            "Wpisz tekst",
            "Uruchom aplikację",
            "Otwórz plik",
            "Otwórz folder",
            "Szablon tekstowy",
            "Menu szablonów",
            "Menu skrótów",
            "Sekwencja kliknięć",
            "Komenda systemowa",
            "Otwórz URL"
        ])
        self.action_type_combo.setFixedWidth(180)
        self.action_type_combo.setFixedHeight(35)
        self.action_type_combo.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(self.action_type_combo)
        
        # Wartość
        value_label = QLabel("Wartość:")
        value_label.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(value_label)
        self.action_value_input = QLineEdit()
        self.action_value_input.setPlaceholderText("Wartość akcji...")
        self.action_value_input.setFixedHeight(35)
        self.action_value_input.setFont(QFont("Segoe UI", 11))
        form_layout.addWidget(self.action_value_input)
        
        # Przyciski
        add_btn = QPushButton("➕ Dodaj")
        add_btn.clicked.connect(self.add_shortcut)
        add_btn.setFixedWidth(100)
        add_btn.setFixedHeight(35)
        add_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        add_btn.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
        """)
        form_layout.addWidget(add_btn)
        
        layout.addWidget(form_group)
        
        # ===== TABELA SKRÓTÓW =====
        table_group = QGroupBox("📋 Lista skrótów")
        table_group.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        table_layout = QVBoxLayout(table_group)
        
        self.shortcuts_table = QTableWidget()
        self.shortcuts_table.setColumnCount(5)
        self.shortcuts_table.setHorizontalHeaderLabels([
            "Nazwa", "Rodzaj", "Skrót", "Akcja", "Wartość"
        ])
        
        # Większa czcionka w tabeli
        self.shortcuts_table.setFont(QFont("Segoe UI", 11))
        
        # Większa wysokość wierszy
        self.shortcuts_table.verticalHeader().setDefaultSectionSize(35)
        
        # Nagłówki tabeli
        header = self.shortcuts_table.horizontalHeader()
        header.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        header.setDefaultSectionSize(200)
        header.setStretchLastSection(True)
        
        self.shortcuts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.shortcuts_table.setAlternatingRowColors(True)
        table_layout.addWidget(self.shortcuts_table)
        
        # Przyciski tabeli
        table_buttons = QHBoxLayout()
        table_buttons.setSpacing(10)
        
        edit_btn = QPushButton("✏️ Edytuj")
        edit_btn.clicked.connect(self.edit_shortcut)
        edit_btn.setFixedHeight(40)
        edit_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        table_buttons.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Usuń")
        delete_btn.clicked.connect(self.delete_shortcut)
        delete_btn.setFixedHeight(40)
        delete_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        table_buttons.addWidget(delete_btn)
        
        test_btn = QPushButton("🧪 Testuj")
        test_btn.clicked.connect(self.test_shortcut)
        test_btn.setFixedHeight(40)
        test_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        table_buttons.addWidget(test_btn)
        
        table_buttons.addStretch()
        
        export_btn = QPushButton("📤 Eksport")
        export_btn.clicked.connect(self.export_config)
        export_btn.setFixedHeight(40)
        export_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        table_buttons.addWidget(export_btn)
        
        import_btn = QPushButton("📥 Import")
        import_btn.clicked.connect(self.import_config)
        import_btn.setFixedHeight(40)
        import_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        table_buttons.addWidget(import_btn)
        
        table_layout.addLayout(table_buttons)
        
        layout.addWidget(table_group)
        
        return widget
    
    def create_footer(self) -> QWidget:
        """Tworzy stopkę ze statusem."""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 5, 10, 10)
        
        self.footer_status = QLabel("Gotowy")
        self.footer_status.setFont(QFont("Segoe UI", 11))
        layout.addWidget(self.footer_status)
        
        layout.addStretch()
        
        version = QLabel("v3.1 | pynput listener (BEZPIECZNY)")
        version.setFont(QFont("Segoe UI", 10))
        version.setStyleSheet("color: #888;")
        layout.addWidget(version)
        
        return widget
    
    def setup_styling(self):
        """Ustawia globalne style aplikacji."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QWidget {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                background-color: #3c3f41;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 16px;
                padding-top: 16px;
                color: #ffffff;
                font-size: 12pt;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 12px;
                padding: 0 8px;
                color: #ffffff;
                background-color: #3c3f41;
            }
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 5px;
                font-weight: bold;
                font-size: 11pt;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
            QLineEdit, QComboBox {
                border: 2px solid #555555;
                border-radius: 5px;
                padding: 8px;
                background-color: #ffffff;
                color: #000000;
                font-size: 11pt;
            }
            QLineEdit:focus, QComboBox:focus {
                border: 2px solid #2196F3;
            }
            QLineEdit:read-only {
                background-color: #f0f0f0;
                color: #333333;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 8px solid #000000;
                margin-right: 8px;
            }
            QTableWidget {
                border: 2px solid #555555;
                border-radius: 5px;
                background-color: #ffffff;
                color: #000000;
                gridline-color: #cccccc;
                font-size: 11pt;
            }
            QTableWidget::item {
                padding: 8px;
                color: #000000;
            }
            QTableWidget::item:selected {
                background-color: #2196F3;
                color: white;
            }
            QHeaderView::section {
                background-color: #4CAF50;
                color: #ffffff;
                padding: 8px;
                border: none;
                border-bottom: 2px solid #388E3C;
                font-weight: bold;
                font-size: 11pt;
            }
            QLabel {
                color: #ffffff;
                background-color: transparent;
            }
        """)
    
    # ===== SLOT METHODS =====
    
    def add_shortcut(self):
        """Dodaje nowy skrót do listy."""
        name = self.name_input.text().strip()
        shortcut_type = self.shortcut_type_combo.currentText()
        hotkey = self.hotkey_input.text().strip()
        action_type = self.action_type_combo.currentText()
        action_value = self.action_value_input.text().strip()
        
        # Walidacja
        if not name:
            QMessageBox.warning(self, "Błąd", "Podaj nazwę skrótu!")
            return
        
        if not hotkey:
            QMessageBox.warning(self, "Błąd", "Podaj kombinację klawiszy!")
            return
        
        if not action_value:
            QMessageBox.warning(self, "Błąd", "Podaj wartość akcji!")
            return
        
        # Sprawdź duplikaty nazwy
        for s in self.shortcuts:
            if s['name'] == name:
                QMessageBox.warning(self, "Błąd", f"Skrót o nazwie '{name}' już istnieje!")
                return
        
        # Dodaj skrót
        shortcut = {
            'name': name,
            'shortcut_type': shortcut_type,
            'hotkey': hotkey,
            'action_type': action_type,
            'action_value': action_value,
            'enabled': True
        }
        
        self.shortcuts.append(shortcut)
        self.save_config()
        self.refresh_table()
        self.clear_form()
        
        # Jeśli system aktywny - zarejestruj natychmiast
        if self.hotkey_manager.is_active:
            self.register_shortcut(shortcut)
        
        self.footer_status.setText(f"✅ Dodano skrót: {name}")
    
    def edit_shortcut(self):
        """Edytuje zaznaczony skrót."""
        row = self.shortcuts_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Błąd", "Wybierz skrót do edycji!")
            return
        
        shortcut = self.shortcuts[row]
        
        # Wypełnij formularz
        self.name_input.setText(shortcut['name'])
        
        # Ustaw rodzaj skrótu
        st_index = self.shortcut_type_combo.findText(shortcut.get('shortcut_type', 'Kombinacja klawiszy'))
        if st_index >= 0:
            self.shortcut_type_combo.setCurrentIndex(st_index)
        
        self.hotkey_input.setText(shortcut['hotkey'])
        
        # Ustaw typ akcji
        index = self.action_type_combo.findText(shortcut['action_type'])
        if index >= 0:
            self.action_type_combo.setCurrentIndex(index)
        
        self.action_value_input.setText(shortcut['action_value'])
        
        # Usuń stary
        self.shortcuts.pop(row)
        self.save_config()
        self.refresh_table()
        
        if self.hotkey_manager.is_active:
            self.hotkey_manager.unregister(shortcut['name'])
        
        self.footer_status.setText(f"✏️ Edycja: {shortcut['name']}")
    
    def delete_shortcut(self):
        """Usuwa zaznaczony skrót."""
        row = self.shortcuts_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Błąd", "Wybierz skrót do usunięcia!")
            return
        
        shortcut = self.shortcuts[row]
        
        reply = QMessageBox.question(
            self, "Potwierdzenie",
            f"Czy na pewno usunąć skrót '{shortcut['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Wyrejestruj jeśli aktywny
            if self.hotkey_manager.is_active:
                self.hotkey_manager.unregister(shortcut['name'])
            
            # Usuń z listy
            self.shortcuts.pop(row)
            self.save_config()
            self.refresh_table()
            
            self.footer_status.setText(f"🗑️ Usunięto: {shortcut['name']}")
    
    def test_shortcut(self):
        """Testuje zaznaczony skrót."""
        row = self.shortcuts_table.currentRow()
        if row < 0:
            QMessageBox.warning(self, "Błąd", "Wybierz skrót do testu!")
            return
        
        shortcut = self.shortcuts[row]
        self.footer_status.setText(f"🧪 Test: {shortcut['name']}...")
        
        # Wykonaj akcję
        QTimer.singleShot(500, lambda: self.execute_shortcut_action(shortcut))
    
    def clear_form(self):
        """Czyści formularz dodawania."""
        self.name_input.clear()
        self.hotkey_input.clear()
        self.action_value_input.clear()
        self.action_type_combo.setCurrentIndex(0)
    
    def refresh_table(self):
        """Odświeża tabelę skrótów."""
        self.shortcuts_table.setRowCount(len(self.shortcuts))
        
        for row, shortcut in enumerate(self.shortcuts):
            self.shortcuts_table.setItem(row, 0, QTableWidgetItem(shortcut['name']))
            self.shortcuts_table.setItem(row, 1, QTableWidgetItem(shortcut.get('shortcut_type', 'Kombinacja klawiszy')))
            self.shortcuts_table.setItem(row, 2, QTableWidgetItem(shortcut['hotkey']))
            self.shortcuts_table.setItem(row, 3, QTableWidgetItem(shortcut['action_type']))
            
            # Skróć wartość akcji jeśli długa
            value = shortcut['action_value']
            if len(value) > 50:
                value = value[:47] + "..."
            self.shortcuts_table.setItem(row, 4, QTableWidgetItem(value))
    
    def toggle_system(self):
        """Przełącza stan systemu (włącz/wyłącz)."""
        if self.hotkey_manager.is_active:
            self.stop_system()
        else:
            self.start_system()
    
    def start_system(self):
        """Uruchamia system skrótów."""
        if not self.shortcuts:
            QMessageBox.warning(self, "Błąd", "Brak skrótów do uruchomienia!")
            return
        
        # Zarejestruj wszystkie skróty
        for shortcut in self.shortcuts:
            if shortcut.get('enabled', True):
                self.register_shortcut(shortcut)
        
        self.hotkey_manager.start()
        
        # Aktualizuj UI
        self.status_label.setText(f"System AKTYWNY ({self.hotkey_manager.get_count()} skrótów)")
        self.status_label.setStyleSheet(
            "background-color: #4CAF50; color: white; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold; font-size: 12pt;"
        )
        self.toggle_btn.setText("⏹️ ZATRZYMAJ SYSTEM")
        self.footer_status.setText("🎯 System uruchomiony!")
    
    def stop_system(self):
        """Zatrzymuje system skrótów."""
        self.hotkey_manager.stop()
        
        # Aktualizuj UI
        self.status_label.setText("System NIEAKTYWNY")
        self.status_label.setStyleSheet(
            "background-color: #ccc; color: #333; padding: 8px 16px; "
            "border-radius: 4px; font-weight: bold; font-size: 12pt;"
        )
        self.toggle_btn.setText("▶️ URUCHOM SYSTEM")
        self.footer_status.setText("⏹️ System zatrzymany")
    
    def register_shortcut(self, shortcut: Dict):
        """Rejestruje pojedynczy skrót."""
        name = shortcut['name']
        hotkey = shortcut['hotkey']
        
        # Callback dla tego skrótu - emituj sygnał Qt (bezpieczne wielowątkowo)
        def callback():
            self.shortcut_triggered.emit(shortcut)
        
        self.hotkey_manager.register(name, hotkey, callback)
    
    def execute_shortcut_action(self, shortcut: Dict):
        """Wykonuje akcję skrótu."""
        print(f"\n🎯 Wykonuję skrót: {shortcut['name']}")
        
        # Mapowanie typu akcji na typ wykonawcy
        type_map = {
            "Wpisz tekst": "text",
            "Uruchom aplikację": "app",
            "Otwórz plik": "file",
            "Otwórz folder": "folder",
            "Szablon tekstowy": "template",
            "Komenda systemowa": "command",
            "Otwórz URL": "url",
            "Menu szablonów": "menu_templates",
            "Menu skrótów": "menu_shortcuts",
            "Sekwencja kliknięć": "click_sequence"
        }
        
        action_type = type_map.get(shortcut['action_type'], "text")
        action_data = {}
        
        if action_type == "text":
            action_data = {'text': shortcut['action_value']}
        elif action_type == "template":
            action_data = {'template': shortcut['action_value']}
        elif action_type == "url":
            action_data = {'url': shortcut['action_value']}
        elif action_type == "command":
            action_data = {'command': shortcut['action_value']}
        elif action_type in ['app', 'file', 'folder']:
            action_data = {'path': shortcut['action_value']}
        
        # Wykonaj
        success, message = self.action_executor.execute(action_type, action_data)
        
        if success:
            print(f"✅ {message}")
            self.footer_status.setText(f"✅ {shortcut['name']}: {message}")
        else:
            print(f"❌ {message}")
            self.footer_status.setText(f"❌ {shortcut['name']}: {message}")
    
    def load_config(self):
        """Wczytuje konfigurację."""
        self.shortcuts = self.config_manager.load()
    
    def save_config(self):
        """Zapisuje konfigurację."""
        self.config_manager.save(self.shortcuts)
    
    def export_config(self):
        """Eksportuje konfigurację do pliku."""
        filepath, _ = QFileDialog.getSaveFileName(
            self, "Eksportuj konfigurację",
            "shortcuts_export.json",
            "JSON Files (*.json)"
        )
        
        if filepath:
            if self.config_manager.export_to(filepath, self.shortcuts):
                QMessageBox.information(self, "Sukces", f"Wyeksportowano do:\n{filepath}")
    
    def import_config(self):
        """Importuje konfigurację z pliku."""
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Importuj konfigurację",
            "",
            "JSON Files (*.json)"
        )
        
        if filepath:
            imported = self.config_manager.import_from(filepath)
            if imported:
                reply = QMessageBox.question(
                    self, "Potwierdzenie",
                    f"Zaimportowano {len(imported)} skrótów.\nZastąpić obecną konfigurację?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
                )
                
                if reply == QMessageBox.StandardButton.Yes:
                    self.shortcuts = imported
                    self.save_config()
                    self.refresh_table()
                    QMessageBox.information(self, "Sukces", "Import zakończony pomyślnie!")
    
    def closeEvent(self, event):
        """Obsługuje zamknięcie okna."""
        if self.hotkey_manager.is_active:
            self.stop_system()
        event.accept()


# ============================================================================
# MAIN
# ============================================================================

def main():
    """Funkcja główna."""
    app = QApplication(sys.argv)
    app.setApplicationName("Shortcuts v3")
    app.setOrganizationName("Pro Ka Po Comer")
    
    window = ShortcutsWindow()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
