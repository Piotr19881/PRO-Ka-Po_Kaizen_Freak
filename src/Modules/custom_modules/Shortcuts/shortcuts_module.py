"""
Moduł Shortcuts - Zarządzanie skrótami klawiszowymi (podobne do AutoHotkey)

Funkcjonalność:
- Tworzenie niestandardowych skrótów klawiszowych
- Uruchamianie aplikacji, skryptów, komend
- Lista wszystkich utworzonych skrótów
- Aktywacja/deaktywacja skrótów
- Import/Export konfiguracji

Używa biblioteki 'keyboard' - działa jak AutoHotkey (Windows keyboard hook)

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-03
"""

import sys
import json
import os
import subprocess
import time
import threading
from datetime import datetime
from pathlib import Path

try:
    import keyboard  # Globalne skróty (Windows keyboard hook)
except ImportError:
    print("BŁĄD: Biblioteka keyboard nie jest zainstalowana. Uruchom: pip install keyboard")
    sys.exit(1)

try:
    import win32api  # Używane przez ShortcutCaptureWidget do GetAsyncKeyState
    import win32con
except ImportError:
    print("BŁĄD: Biblioteka pywin32 nie jest zainstalowana. Uruchom: pip install pywin32")
    sys.exit(1)
    sys.exit(1)

try:
    from pynput.keyboard import Key, Controller as KeyboardController
    from pynput.mouse import Button, Controller as MouseController
except ImportError:
    print("BŁĄD: Biblioteka pynput nie jest zainstalowana. Uruchom: pip install pynput")
    sys.exit(1)

import pyperclip

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
    QTextEdit, QComboBox, QMessageBox, QFileDialog, QSplitter,
    QGroupBox, QCheckBox, QHeaderView, QMenu
)
from typing import Optional
from PyQt6.QtCore import Qt, QSize, QTimer, QTime, QPoint, pyqtSignal, QObject, QEvent
from PyQt6.QtGui import (
    QKeySequence, QAction, QIcon, QPainter, QColor, QPen, QFont, QScreen, QCursor,
    QKeyEvent, QFocusEvent, QShowEvent, QPaintEvent, QMouseEvent
)

# Import modułów lokalnych
try:
    from .shortcuts_config import ShortcutsConfig
    # TODO: Po usunięciu duplikatów klas z tego pliku, odkomentuj:
    # from .widgets import ShortcutCaptureWidget, TemplateContextMenu, ShortcutsContextMenu
except ImportError:
    # Standalone execution
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


class TemplateMenuSignal(QObject):
    """Klasa pomocnicza do komunikacji między wątkami"""
    show_menu = pyqtSignal(list, QPoint)


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
            action.setData(content)  # Przechowaj treść w action
            action.triggered.connect(lambda checked, c=content: self.copy_to_clipboard(c))
            self.addAction(action)
    
    def copy_to_clipboard(self, text):
        """Kopiuje tekst do schowka"""
        try:
            success, message = ActionExecutor.paste_text(text)
            if not success:
                print(f"[Templates] {message}")
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
            "Plik": "📄",
            "Skrót": "⤴️"
        }
        return icons.get(item_type, "▪")
    
    def execute_menu_action(self, item_type, path):
        """Wykonuje akcję wybraną z menu"""
        try:
            if item_type == "Folder":
                os.startfile(path)
            elif item_type == "Plik":
                os.startfile(path)
            elif item_type == "Skrót":
                subprocess.Popen(path, shell=True)
        except Exception as e:
            print(f"Błąd wykonania akcji menu: {e}")


class ClickRecorderOverlay(QWidget):
    """Nakładka na cały ekran do nagrywania sekwencji kliknięć"""
    
    recording_finished = pyqtSignal(list)  # Sygnał z listą kliknięć
    
    def __init__(self):
        super().__init__()
        self.clicks = []  # Lista kliknięć: [{x, y, button, time_offset}]
        self.red_dots = []  # Lista czerwonych punktów do wyświetlenia
        self.recording = False
        self.start_time = None
        self.elapsed_timer = QTimer()
        self.elapsed_timer.timeout.connect(self.update)
        self.elapsed_time = QTime(0, 0, 0)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Konfiguracja interfejsu nakładki"""
        # Ustawienia okna - pełny ekran, zawsze na wierzchu
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        # Pobierz rozmiar WSZYSTKICH ekranów
        screens = QApplication.screens()
        if screens:
            # Znajdź całkowity obszar wszystkich ekranów
            min_x = min(screen.geometry().x() for screen in screens)
            min_y = min(screen.geometry().y() for screen in screens)
            max_x = max(screen.geometry().x() + screen.geometry().width() for screen in screens)
            max_y = max(screen.geometry().y() + screen.geometry().height() for screen in screens)
            
            # Ustaw geometrię na cały obszar
            from PyQt6.QtCore import QRect
            total_geometry = QRect(min_x, min_y, max_x - min_x, max_y - min_y)
            self.setGeometry(total_geometry)
        
        # Przezroczyste tło z delikatną mgłą
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setProperty('class', config.get_style_class('overlay'))
        
        # Włącz śledzenie myszy
        self.setMouseTracking(True)
        
        # Przechwytuj klawiaturę
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def showEvent(self, event):
        """Gdy okno się pojawia"""
        super().showEvent(event)
        self.setFocus()
        self.activateWindow()
    
    def paintEvent(self, event):
        """Rysuje nakładkę"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Rysuj półprzezroczystą mgłę
        fog_color = QColor(200, 200, 200, 150)  # Jasna mgła
        painter.fillRect(self.rect(), fog_color)
        
        # Rysuj czerwone punkty kliknięć
        painter.setPen(QPen(QColor(255, 0, 0), 2))
        painter.setBrush(QColor(255, 0, 0, 200))
        for dot in self.red_dots:
            painter.drawEllipse(dot, 8, 8)
        
        # Tekst instrukcji lub stoper
        painter.setPen(QColor(0, 0, 0))
        font = QFont("Arial", 24, QFont.Weight.Bold)
        painter.setFont(font)
        
        if not self.recording:
            # Instrukcja początkowa
            text = "Naciśnij ENTER aby rozpocząć nagrywanie\nlub naciśnij ESC aby zakończyć"
            painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
        else:
            # Stoper w prawym górnym rogu
            elapsed_text = f"⏱ Czas: {self.elapsed_time.toString('mm:ss.zzz')}"
            painter.setPen(QColor(255, 255, 255))
            painter.fillRect(self.width() - 350, 20, 330, 60, QColor(0, 0, 0, 180))
            painter.setPen(QColor(255, 255, 0))
            painter.drawText(self.width() - 340, 20, 310, 60, 
                           Qt.AlignmentFlag.AlignCenter, elapsed_text)
            
            # Licznik kliknięć
            clicks_text = f"Kliknięć: {len(self.clicks)}"
            painter.setPen(QColor(255, 255, 255))
            painter.fillRect(self.width() - 350, 90, 330, 50, QColor(0, 0, 0, 180))
            painter.setPen(QColor(0, 255, 0))
            font_small = QFont("Arial", 18, QFont.Weight.Bold)
            painter.setFont(font_small)
            painter.drawText(self.width() - 340, 90, 310, 50,
                           Qt.AlignmentFlag.AlignCenter, clicks_text)
            
            # Instrukcja ESC
            painter.setPen(QColor(255, 100, 100))
            font_small2 = QFont("Arial", 14)
            painter.setFont(font_small2)
            painter.drawText(self.width() - 340, 150, 310, 40,
                           Qt.AlignmentFlag.AlignCenter, "Naciśnij ESC aby zakończyć")
    
    def keyPressEvent(self, event):
        """Obsługa klawiszy"""
        if event.key() == Qt.Key.Key_Return or event.key() == Qt.Key.Key_Enter:
            if not self.recording:
                self.start_recording()
        elif event.key() == Qt.Key.Key_Escape:
            if self.recording:
                self.stop_recording()
            else:
                # Anuluj bez nagrywania
                self.recording_finished.emit([])
                self.close()
    
    def mousePressEvent(self, event):
        """Rejestruje kliknięcia"""
        if not self.recording or not self.start_time:
            return
        
        # Pobierz pozycję kliknięcia
        pos = event.globalPosition().toPoint()
        
        # Pobierz czas od rozpoczęcia
        time_offset = self.start_time.msecsTo(QTime.currentTime())
        
        # Określ przycisk myszy
        button = "left"
        if event.button() == Qt.MouseButton.RightButton:
            button = "right"
        elif event.button() == Qt.MouseButton.MiddleButton:
            button = "middle"
        
        # Dodaj kliknięcie
        click_data = {
            'x': pos.x(),
            'y': pos.y(),
            'button': button,
            'time_offset': time_offset
        }
        self.clicks.append(click_data)
        
        # Dodaj czerwony punkt (w pozycji lokalnej)
        local_pos = self.mapFromGlobal(pos)
        self.red_dots.append(local_pos)
        
        self.update()
    
    def start_recording(self):
        """Rozpoczyna nagrywanie"""
        self.recording = True
        self.clicks = []
        self.red_dots = []
        self.start_time = QTime.currentTime()
        self.elapsed_time = QTime(0, 0, 0)
        
        # Uruchom timer aktualizacji stopera
        self.elapsed_timer.start(10)  # Aktualizuj co 10ms
        
        self.update()
    
    def stop_recording(self):
        """Zatrzymuje nagrywanie"""
        self.recording = False
        self.elapsed_timer.stop()
        
        # Wyślij sygnał z nagranymi kliknięciami
        self.recording_finished.emit(self.clicks)
        self.close()
    
    def update(self):
        """Aktualizuje wyświetlanie"""
        if self.recording and self.start_time:
            # Aktualizuj czas
            msecs = self.start_time.msecsTo(QTime.currentTime())
            self.elapsed_time = QTime(0, 0, 0).addMSecs(msecs)
        
        super().update()


class ClickTestOverlay(QWidget):
    """Nakładka do testowania sekwencji kliknięć - pokazuje gdzie aplikacja kliknie"""
    
    test_finished = pyqtSignal()
    
    def __init__(self, clicks):
        super().__init__()
        self.clicks = clicks  # Lista kliknięć do wyświetlenia
        self.current_index = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.show_next_click)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Konfiguracja interfejsu nakładki testowej"""
        # Ustawienia okna - pełny ekran na wszystkich monitorach
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        # Pobierz rozmiar WSZYSTKICH ekranów
        screens = QApplication.screens()
        if screens:
            min_x = min(screen.geometry().x() for screen in screens)
            min_y = min(screen.geometry().y() for screen in screens)
            max_x = max(screen.geometry().x() + screen.geometry().width() for screen in screens)
            max_y = max(screen.geometry().y() + screen.geometry().height() for screen in screens)
            
            from PyQt6.QtCore import QRect
            total_geometry = QRect(min_x, min_y, max_x - min_x, max_y - min_y)
            self.setGeometry(total_geometry)
        
        # Przezroczyste tło z delikatną mgłą
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        # Przechwytuj klawiaturę
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def showEvent(self, a0):
        """Gdy okno się pojawia - rozpocznij animację"""
        super().showEvent(a0)
        self.setFocus()
        self.activateWindow()
        # Rozpocznij pokazywanie kliknięć po 500ms
        QTimer.singleShot(500, self.start_animation)
    
    def start_animation(self):
        """Rozpoczyna animację pokazywania kliknięć"""
        self.current_index = 0
        # Pokaż pierwsze kliknięcie natychmiast
        self.show_next_click()
    
    def show_next_click(self):
        """Pokazuje następne kliknięcie"""
        if self.current_index >= len(self.clicks):
            # Koniec animacji
            self.animation_timer.stop()
            # Zamknij po 2 sekundach
            QTimer.singleShot(2000, self.finish_test)
            return
        
        # Pokaż obecne kliknięcie
        self.update()
        
        # Przejdź do następnego
        self.current_index += 1
        
        # Ustaw timer na następne kliknięcie
        if self.current_index < len(self.clicks):
            # Oblicz delay do następnego kliknięcia
            current_time = self.clicks[self.current_index - 1].get('time_offset', 0)
            next_time = self.clicks[self.current_index].get('time_offset', current_time + 500)
            delay = max(100, next_time - current_time)  # Minimum 100ms
            self.animation_timer.start(delay)
    
    def paintEvent(self, a0):
        """Rysuje nakładkę z punktami kliknięć"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Rysuj półprzezroczystą mgłę
        fog_color = QColor(200, 200, 200, 150)
        painter.fillRect(self.rect(), fog_color)
        
        # Rysuj wszystkie kliknięcia do obecnego indexu
        for i in range(self.current_index):
            click = self.clicks[i]
            x = click.get('x', 0)
            y = click.get('y', 0)
            
            # Konwertuj globalną pozycję na lokalną
            global_pos = QPoint(x, y)
            local_pos = self.mapFromGlobal(global_pos)
            
            # Rysuj czerwony punkt z numerem
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.setBrush(QColor(255, 0, 0, 220))
            painter.drawEllipse(local_pos, 12, 12)
            
            # Rysuj numer kliknięcia
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 10, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(local_pos.x() - 20, local_pos.y() - 20, 40, 40,
                           Qt.AlignmentFlag.AlignCenter, str(i + 1))
        
        # Instrukcja
        painter.setPen(QColor(0, 0, 0))
        font_large = QFont("Arial", 20, QFont.Weight.Bold)
        painter.setFont(font_large)
        text = f"Test sekwencji kliknięć: {self.current_index}/{len(self.clicks)}\nNaciśnij ESC aby zakończyć"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
    
    def keyPressEvent(self, a0):
        """Obsługa klawiszy"""
        if a0 and a0.key() == Qt.Key.Key_Escape:
            self.finish_test()
    
    def finish_test(self):
        """Kończy test"""
        self.animation_timer.stop()
        self.test_finished.emit()
        self.close()


class ActionExecutor:
    """Klasa odpowiedzialna za wykonywanie akcji skrótów"""
    
    menu_signal = None  # Zostanie ustawiony przez ShortcutsModule
    
    @staticmethod
    def execute(shortcut):
        """
        Główny dispatcher wykonywania akcji
        
        Args:
            shortcut: Słownik ze skrótem zawierający action_type i action_value
            
        Returns:
            tuple: (success: bool, message: str)
        """
        action_type = shortcut.get('action_type', '')
        action_value = shortcut.get('action_value', '')
        
        try:
            if action_type == "Wklej tekst":
                return ActionExecutor.paste_text(action_value)
            elif action_type == "Menu z szablonami":
                return ActionExecutor.show_template_menu(action_value)
            elif action_type == "Menu skrótów":
                return ActionExecutor.show_shortcuts_menu(action_value)
            elif action_type == "Otwórz aplikację":
                return ActionExecutor.open_application(action_value)
            elif action_type == "Otwórz plik":
                return ActionExecutor.open_file(action_value)
            elif action_type == "Polecenie PowerShell":
                return ActionExecutor.run_powershell(action_value)
            elif action_type == "Polecenie wiersza poleceń":
                return ActionExecutor.run_cmd(action_value)
            elif action_type == "Wykonaj sekwencję kliknięć":
                return ActionExecutor.execute_click_sequence(action_value)
            else:
                return False, f"Nieznany typ akcji: {action_type}"
        except Exception as e:
            return False, f"Błąd wykonania: {str(e)}"
    
    @staticmethod
    def show_template_menu(templates_json):
        """Pokazuje menu z szablonami przy kursorze"""
        try:
            # Parsuj JSON z szablonami
            templates = json.loads(templates_json) if templates_json else []
            
            if not templates or not isinstance(templates, list):
                return False, "Brak szablonów do wyświetlenia"
            
            # Pobierz pozycję kursora
            cursor_pos = QCursor.pos()
            
            # Wyślij sygnał do głównego wątku GUI
            if ActionExecutor.menu_signal:
                ActionExecutor.menu_signal.show_menu.emit(templates, cursor_pos)
                return True, f"Pokazano menu z {len(templates)} szablonami"
            else:
                return False, "Menu signal nie został zainicjalizowany"
        except json.JSONDecodeError as e:
            return False, f"Błąd parsowania szablonów: {str(e)}"
        except Exception as e:
            return False, f"Błąd pokazywania menu: {str(e)}"
    
    @staticmethod
    def show_shortcuts_menu(menu_items_json):
        """Pokazuje menu ze skrótami przy kursorze"""
        try:
            # Parsuj JSON z pozycjami menu
            menu_items = json.loads(menu_items_json) if menu_items_json else []
            
            if not menu_items or not isinstance(menu_items, list):
                return False, "Brak pozycji menu do wyświetlenia"
            
            # Pobierz pozycję kursora
            cursor_pos = QCursor.pos()
            
            # Wyślij sygnał do głównego wątku GUI
            if ActionExecutor.menu_signal:
                ActionExecutor.menu_signal.show_menu.emit(menu_items, cursor_pos)
                return True, f"Pokazano menu z {len(menu_items)} pozycjami"
            else:
                return False, "Menu signal nie został zainicjalizowany"
        except json.JSONDecodeError as e:
            return False, f"Błąd parsowania menu: {str(e)}"
        except Exception as e:
            return False, f"Błąd pokazywania menu: {str(e)}"
    
    @staticmethod
    def paste_text(text):
        """Wkleja tekst używając schowka"""
        try:
            # Zapisz aktualną zawartość schowka
            old_clipboard = ""
            try:
                old_clipboard = pyperclip.paste()
            except:
                pass
            
            # Skopiuj nowy tekst
            pyperclip.copy(text)
            
            # Poczekaj chwilę
            time.sleep(0.1)
            
            # Symuluj Ctrl+V
            keyboard = KeyboardController()
            keyboard.press(Key.ctrl)
            keyboard.press('v')
            keyboard.release('v')
            keyboard.release(Key.ctrl)
            
            # Poczekaj na wklejenie
            time.sleep(0.1)
            
            # Opcjonalnie przywróć stary schowek
            # pyperclip.copy(old_clipboard)
            
            return True, f"Wklejono tekst ({len(text)} znaków)"
        except Exception as e:
            return False, f"Błąd wklejania: {str(e)}"
    
    @staticmethod
    def open_application(path):
        """Otwiera aplikację"""
        try:
            if not os.path.exists(path):
                return False, f"Nie znaleziono pliku: {path}"
            
            subprocess.Popen(path, shell=True)
            return True, f"Uruchomiono: {os.path.basename(path)}"
        except Exception as e:
            return False, f"Błąd uruchamiania: {str(e)}"
    
    @staticmethod
    def open_file(path):
        """Otwiera plik"""
        try:
            if not os.path.exists(path):
                return False, f"Nie znaleziono pliku: {path}"
            
            os.startfile(path)
            return True, f"Otwarto: {os.path.basename(path)}"
        except Exception as e:
            return False, f"Błąd otwierania: {str(e)}"
    
    @staticmethod
    def run_powershell(command, timeout=30):
        """Wykonuje polecenie PowerShell w tle (nie blokuje UI)"""
        try:
            # Uruchom w osobnym procesie bez czekania - POKAŻ okno konsoli
            subprocess.Popen(
                ['powershell', '-NoExit', '-Command', command]
            )
            return True, f"PowerShell uruchomiono w nowym oknie"
        except Exception as e:
            return False, f"Błąd PowerShell: {str(e)}"
    
    @staticmethod
    def run_cmd(command, timeout=30):
        """Wykonuje polecenie CMD w tle (nie blokuje UI)"""
        try:
            # Uruchom w osobnym procesie bez czekania - POKAŻ okno konsoli
            subprocess.Popen(
                ['cmd', '/k', command]
            )
            return True, f"CMD uruchomiono w nowym oknie"
        except Exception as e:
            return False, f"Błąd CMD: {str(e)}"
    
    @staticmethod
    def execute_click_sequence(sequence_json):
        """Wykonuje sekwencję kliknięć myszy"""
        try:
            # Parsuj JSON
            clicks = json.loads(sequence_json)
            if not isinstance(clicks, list) or len(clicks) == 0:
                return False, "Sekwencja musi być niepustą listą"
            
            # Inicjalizuj kontroler myszy
            mouse = MouseController()
            start_time = time.time()
            
            # Wykonaj każde kliknięcie
            for i, click in enumerate(clicks):
                # Czekaj do właściwego czasu
                target_time = click.get('time_offset', 0) / 1000.0  # ms -> s
                current_elapsed = time.time() - start_time
                
                if target_time > current_elapsed:
                    time.sleep(target_time - current_elapsed)
                
                # Przesuń mysz
                x = click.get('x', 0)
                y = click.get('y', 0)
                mouse.position = (x, y)
                
                # Małe opóźnienie po przesunięciu
                time.sleep(0.05)
                
                # Określ przycisk
                button = Button.left
                button_name = click.get('button', 'left').lower()
                if button_name == 'right':
                    button = Button.right
                elif button_name == 'middle':
                    button = Button.middle
                
                # Kliknij
                mouse.click(button, 1)
            
            return True, f"Wykonano sekwencję {len(clicks)} kliknięć"
        except json.JSONDecodeError as e:
            return False, f"Błąd parsowania JSON: {str(e)}"
        except Exception as e:
            return False, f"Błąd wykonania sekwencji: {str(e)}"


class HotkeyListener(QObject):
    """
    Listener globalnych skrótów klawiszowych używający biblioteki 'keyboard'.
    Działa jak AutoHotkey - używa Windows keyboard hook (SetWindowsHookEx).
    """
    hotkey_triggered = pyqtSignal(str)

    _PHRASE_IGNORED_KEYS = {
        'shift', 'left shift', 'right shift',
        'ctrl', 'left ctrl', 'right ctrl',
        'alt', 'left alt', 'right alt',
        'windows', 'left windows', 'right windows',
        'caps lock'
    }

    _PHRASE_RESET_KEYS = {
        'esc', 'escape', 'up', 'down', 'left', 'right',
        'home', 'end', 'page up', 'page down', 'delete'
    }

    _PHRASE_CHAR_MAP = {
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

    def __init__(self, shortcuts_callback, parent=None):
        super().__init__(parent)
        self.shortcuts_callback = shortcuts_callback
        self.running = False
        self.registered_hotkeys = {}
        self.phrase_listener = None
        self.magic_phrases = {}  # phrase_lower -> {'name': name, 'phrase': phrase}
        self._typed_history = ""
        self._pending_phrase_triggers = {}
        self._phrase_suppression_depth = 0

    def normalize_shortcut(self, shortcut_str):
        """
        Normalizuje skrót do formatu biblioteki keyboard.
        Zamienia 'Ctrl+Alt+N' na 'ctrl+alt+n'
        """
        if not shortcut_str:
            return None
        
        # Mapowanie nazw klawiszy
        key_map = {
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
        }
        
        # Dodaj klawisze F1-F12
        for i in range(1, 13):
            key_map[f'F{i}'] = f'f{i}'
        
        keys = shortcut_str.upper().split('+')
        normalized_keys = []
        
        for key in keys:
            if key in key_map:
                normalized_keys.append(key_map[key])
            else:
                normalized_keys.append(key.lower())
        
        return '+'.join(normalized_keys)

    def register_hotkey(self, name, shortcut_str, shortcut_type="Kombinacja klawiszy"):
        """Rejestruje pojedynczy skrót, frazę lub klawisz przytrzymania."""
        try:
            if shortcut_type == "Magiczna fraza":
                self._register_magic_phrase(name, shortcut_str)
                return
            
            if shortcut_type == "Przytrzymaj klawisz":
                self._register_hold_key(name, shortcut_str)
                return

            normalized = self.normalize_shortcut(shortcut_str)
            if not normalized:
                return

            if name in self.registered_hotkeys:
                self.unregister_hotkey(name)

            def callback():
                self.hotkey_triggered.emit(name)

            import keyboard
            handler = None
            try:
                handler = keyboard.add_hotkey(
                    normalized,
                    callback,
                    suppress=True,
                    trigger_on_release=True,
                )
            except Exception as hook_error:
                print(f"[Hotkeys] suppress=True failed for '{normalized}': {hook_error}. Retrying without suppression.")
                handler = keyboard.add_hotkey(
                    normalized,
                    callback,
                    suppress=False,
                    trigger_on_release=True,
                )
            self.registered_hotkeys[name] = {
                "handler": handler,
                "shortcut": normalized,
                "type": "combo",
            }
            print(f"[Hotkeys] Zarejestrowano skrót: {shortcut_str} -> {normalized}")

        except Exception as e:
            print(f"[Hotkeys] Błąd rejestracji skrótu '{shortcut_str}': {e}")

    def _register_magic_phrase(self, name, phrase):
        """Rejestruje magiczną frazę rozpoznawaną po wpisaniu tekstu."""
        phrase = (phrase or "").strip()
        if not phrase:
            return

        if name in self.registered_hotkeys:
            self.unregister_hotkey(name)

        phrase_lower = phrase.lower()
        # Zapamiętaj frazę
        self.magic_phrases[phrase_lower] = {
            "name": name,
            "phrase": phrase,
        }

        self.registered_hotkeys[name] = {
            "handler": None,
            "shortcut": phrase,
            "type": "phrase",
            "phrase_lower": phrase_lower,
        }

        self._sync_phrase_listener()
        print(f"[Hotkeys] Zarejestrowano magiczną frazę: {phrase}")

    def _register_hold_key(self, name, key_str):
        """Rejestruje skrót typu 'przytrzymaj klawisz' - wykonuje akcję przy wciśnięciu i puszczeniu."""
        key = (key_str or "").strip()
        if not key:
            return

        if name in self.registered_hotkeys:
            self.unregister_hotkey(name)

        normalized = self.normalize_shortcut(key)
        if not normalized:
            return

        import keyboard

        # Callback dla wciśnięcia klawisza (press)
        def on_press():
            self.hotkey_triggered.emit(f"{name}:press")

        # Callback dla puszczenia klawisza (release)
        def on_release():
            self.hotkey_triggered.emit(f"{name}:release")

        try:
            # Zarejestruj oba eventy
            press_handler = keyboard.on_press_key(normalized, lambda _: on_press())
            release_handler = keyboard.on_release_key(normalized, lambda _: on_release())

            self.registered_hotkeys[name] = {
                "handler": (press_handler, release_handler),  # Tuple z oboma handlerami
                "shortcut": key,
                "type": "hold",
                "normalized": normalized,
            }

            print(f"[Hotkeys] Zarejestrowano klawisz przytrzymania: {key} -> {normalized}")
        except Exception as e:
            print(f"[Hotkeys] Błąd rejestracji klawisza przytrzymania '{key}': {e}")

    def _sync_phrase_listener(self):
        """Zapewnia aktywność nasłuchiwania fraz tylko gdy są potrzebne."""
        import keyboard

        if self.magic_phrases and self.phrase_listener is None:
            self.phrase_listener = keyboard.on_release(self._handle_phrase_key_release)
        elif not self.magic_phrases and self.phrase_listener is not None:
            keyboard.unhook(self.phrase_listener)
            self.phrase_listener = None

    def _reset_phrase_state(self):
        """Resetuje tymczasowy stan analizowania fraz."""
        self._typed_history = ""
        self._pending_phrase_triggers.clear()
        self._phrase_suppression_depth = 0

    def _handle_phrase_key_release(self, event):
        """Analizuje wpisywane znaki w poszukiwaniu magicznych fraz."""
        if self._phrase_suppression_depth > 0:
            return

        if event.event_type != 'up':
            return

        name = (event.name or '').lower()
        if not name:
            return

        if name == 'backspace':
            self._typed_history = self._typed_history[:-1]
            return

        if name in {'space', 'enter', 'tab'}:
            self._process_phrase_trigger(name)
            return

        if name in self._PHRASE_IGNORED_KEYS:
            return

        if name in self._PHRASE_RESET_KEYS:
            self._typed_history = ""
            return

        char = self._name_to_char(name)
        if char:
            self._typed_history += char
            self._trim_typed_history()

    def _name_to_char(self, name):
        """Konwertuje nazwę klawisza na pojedynczy znak (jeśli możliwe)."""
        if len(name) == 1:
            return name
        return self._PHRASE_CHAR_MAP.get(name)

    def _trim_typed_history(self, limit=80):
        """Utrzymuje bufor wpisanych znaków w rozsądnym rozmiarze."""
        if len(self._typed_history) > limit:
            self._typed_history = self._typed_history[-limit:]

    def _process_phrase_trigger(self, trigger_key):
        """Sprawdza czy przed kluczem wyzwalającym wpisano magiczną frazę."""
        buffer_lower = self._typed_history.lower()
        matched = False

        for phrase_lower, meta in sorted(self.magic_phrases.items(), key=lambda item: len(item[0]), reverse=True):
            if phrase_lower and buffer_lower.endswith(phrase_lower):
                matched = True
                self._typed_history = self._typed_history[:-len(phrase_lower)]
                self._fire_magic_phrase(meta['name'], phrase_lower, trigger_key)
                break

        if not matched:
            if trigger_key == 'space':
                self._typed_history += ' '
            elif trigger_key == 'tab':
                self._typed_history += '\t'
            elif trigger_key == 'enter':
                self._typed_history = ""

            self._trim_typed_history()

    def _fire_magic_phrase(self, name, phrase_lower, trigger_key):
        """Usuwa wpisaną frazę z pola i emituje sygnał wykonania."""
        import keyboard

        backspaces = len(phrase_lower)
        if trigger_key in {'space', 'tab'}:
            backspaces += 1

        def send_backspaces():
            for _ in range(backspaces):
                keyboard.send('backspace')
                time.sleep(0.01)

        self.run_with_phrase_suppressed(send_backspaces)

        if trigger_key in {'space', 'tab'}:
            self._pending_phrase_triggers[name] = trigger_key
        else:
            self._pending_phrase_triggers.pop(name, None)

        self.hotkey_triggered.emit(name)

    def run_with_phrase_suppressed(self, func, *args, **kwargs):
        """Wykonuje operację nie wywołując ponownie analizy fraz."""
        self._phrase_suppression_depth += 1
        try:
            return func(*args, **kwargs)
        finally:
            self._phrase_suppression_depth = max(0, self._phrase_suppression_depth - 1)

    def pop_phrase_trigger(self, name):
        """Zwraca i usuwa informację o kluczu wyzwalającym dla frazy."""
        return self._pending_phrase_triggers.pop(name, None)

    def unregister_hotkey(self, name):
        """Wyrejestrowuje pojedynczy skrót."""
        if name in self.registered_hotkeys:
            try:
                import keyboard
                data = self.registered_hotkeys.pop(name)
                entry_type = data.get("type", "combo")

                if entry_type == "phrase":
                    phrase_lower = data.get("phrase_lower") or (data.get("shortcut", "") or "").lower()
                    if phrase_lower:
                        self.magic_phrases.pop(phrase_lower, None)
                    self._pending_phrase_triggers.pop(name, None)
                    print(f"Wyrejestrowano magiczną frazę: {name}")
                
                elif entry_type == "hold":
                    # Dla klawisza przytrzymania mamy tuple (press_handler, release_handler)
                    handler = data.get("handler")
                    if handler and isinstance(handler, tuple):
                        press_handler, release_handler = handler
                        if press_handler:
                            keyboard.unhook(press_handler)
                        if release_handler:
                            keyboard.unhook(release_handler)
                    print(f"Wyrejestrowano klawisz przytrzymania: {name}")
                
                else:
                    handler = data.get("handler")
                    shortcut = data.get("shortcut")

                    if handler is not None:
                        keyboard.remove_hotkey(handler)
                    elif shortcut:
                        keyboard.remove_hotkey(shortcut)

                    print(f"Wyrejestrowano skrót: {name}")

                self._sync_phrase_listener()
            except Exception as e:
                print(f"Błąd wyrejestrowania skrótu '{name}': {e}")

    def register_all_hotkeys(self):
        """Rejestruje wszystkie aktywne skróty."""
        self.registered_hotkeys.clear()
        self.magic_phrases.clear()
        self._reset_phrase_state()
        self._sync_phrase_listener()

        shortcuts = self.shortcuts_callback()
        for shortcut in shortcuts:
            if not shortcut.get('enabled', True):
                continue

            shortcut_type = shortcut.get('shortcut_type', 'Kombinacja klawiszy')
            shortcut_value = shortcut.get('shortcut_value')

            if shortcut_type == 'Przytrzymaj klawisz':
                # TODO: obsłużyć dedykowane skróty przytrzymania w osobnym zadaniu
                continue

            self.register_hotkey(shortcut['name'], shortcut_value, shortcut_type)

    def unregister_all_hotkeys(self):
        """Wyrejestrowuje wszystkie aktualnie zarejestrowane skróty."""
        try:
            import keyboard
            # Wyrejestruj każdy skrót osobno
            for name in list(self.registered_hotkeys.keys()):
                self.unregister_hotkey(name)
        except Exception as e:
            print(f"Błąd podczas wyrejestrowywania skrótów: {e}")
        finally:
            self.registered_hotkeys.clear()
            self.magic_phrases.clear()
            self._reset_phrase_state()
            self._sync_phrase_listener()

    def update_hotkeys(self):
        """Aktualizuje zarejestrowane skróty (przeładowuje z nową konfiguracją)."""
        if self.running:
            self.unregister_all_hotkeys()
            self.register_all_hotkeys()

    def start(self):
        """Uruchamia nasłuchiwanie globalnych skrótów."""
        if not self.running:
            self.running = True
            self.register_all_hotkeys()
            print("[Hotkeys] Uruchomiono nasłuchiwanie skrótów (keyboard library - Windows Hook)")

    def stop(self):
        """Zatrzymuje nasłuchiwanie."""
        if self.running:
            self.running = False
            self.unregister_all_hotkeys()
            print("[Hotkeys] Zatrzymano nasłuchiwanie skrótów")


class ClickTestOverlay(QWidget):
    """Nakładka do testowania sekwencji kliknięć - pokazuje gdzie aplikacja kliknie"""
    
    test_finished = pyqtSignal()
    
    def __init__(self, clicks):
        super().__init__()
        self.clicks = clicks  # Lista kliknięć do wyświetlenia
        self.current_index = 0
        self.animation_timer = QTimer()
        self.animation_timer.timeout.connect(self.show_next_click)
        
        self.setup_ui()
    
    def setup_ui(self):
        """Konfiguracja interfejsu nakładki testowej"""
        # Ustawienia okna - pełny ekran na wszystkich monitorach
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint |
            Qt.WindowType.Tool
        )
        
        # Pobierz rozmiar WSZYSTKICH ekranów
        screens = QApplication.screens()
        if screens:
            min_x = min(screen.geometry().x() for screen in screens)
            min_y = min(screen.geometry().y() for screen in screens)
            max_x = max(screen.geometry().x() + screen.geometry().width() for screen in screens)
            max_y = max(screen.geometry().y() + screen.geometry().height() for screen in screens)
            
            from PyQt6.QtCore import QRect
            total_geometry = QRect(min_x, min_y, max_x - min_x, max_y - min_y)
            self.setGeometry(total_geometry)
        
        # Przezroczyste tło z delikatną mgłą
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setStyleSheet("background: transparent;")
        
        # Przechwytuj klawiaturę
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    
    def showEvent(self, a0):
        """Gdy okno się pojawia - rozpocznij animację"""
        super().showEvent(a0)
        self.setFocus()
        self.activateWindow()
        # Rozpocznij pokazywanie kliknięć po 500ms
        QTimer.singleShot(500, self.start_animation)
    
    def start_animation(self):
        """Rozpoczyna animację pokazywania kliknięć"""
        self.current_index = 0
        # Pokaż pierwsze kliknięcie natychmiast
        self.show_next_click()
    
    def show_next_click(self):
        """Pokazuje następne kliknięcie"""
        if self.current_index >= len(self.clicks):
            # Koniec animacji
            self.animation_timer.stop()
            # Zamknij po 2 sekundach
            QTimer.singleShot(2000, self.finish_test)
            return
        
        # Pokaż obecne kliknięcie
        self.update()
        
        # Przejdź do następnego
        self.current_index += 1
        
        # Ustaw timer na następne kliknięcie
        if self.current_index < len(self.clicks):
            # Oblicz delay do następnego kliknięcia
            current_time = self.clicks[self.current_index - 1].get('time_offset', 0)
            next_time = self.clicks[self.current_index].get('time_offset', current_time + 500)
            delay = max(100, next_time - current_time)  # Minimum 100ms
            self.animation_timer.start(delay)
    
    def paintEvent(self, a0):
        """Rysuje nakładkę z punktami kliknięć"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Rysuj półprzezroczystą mgłę
        fog_color = QColor(200, 200, 200, 150)
        painter.fillRect(self.rect(), fog_color)
        
        # Rysuj wszystkie kliknięcia do obecnego indexu
        for i in range(self.current_index):
            click = self.clicks[i]
            x = click.get('x', 0)
            y = click.get('y', 0)
            
            # Konwertuj globalną pozycję na lokalną
            global_pos = QPoint(x, y)
            local_pos = self.mapFromGlobal(global_pos)
            
            # Rysuj czerwony punkt z numerem
            painter.setPen(QPen(QColor(255, 0, 0), 3))
            painter.setBrush(QColor(255, 0, 0, 220))
            painter.drawEllipse(local_pos, 12, 12)
            
            # Rysuj numer kliknięcia
            painter.setPen(QColor(255, 255, 255))
            font = QFont("Arial", 10, QFont.Weight.Bold)
            painter.setFont(font)
            painter.drawText(local_pos.x() - 20, local_pos.y() - 20, 40, 40,
                           Qt.AlignmentFlag.AlignCenter, str(i + 1))
        
        # Instrukcja
        painter.setPen(QColor(0, 0, 0))
        font_large = QFont("Arial", 20, QFont.Weight.Bold)
        painter.setFont(font_large)
        text = f"Test sekwencji kliknięć: {self.current_index}/{len(self.clicks)}\nNaciśnij ESC aby zakończyć"
        painter.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, text)
    
    def keyPressEvent(self, a0):
        """Obsługa klawiszy"""
        if a0 and a0.key() == Qt.Key.Key_Escape:
            self.finish_test()
    
    def finish_test(self):
        """Kończy test"""
        self.animation_timer.stop()
        self.test_finished.emit()
        self.close()


class ShortcutsModule(QWidget):
    """Główny moduł Shortcuts - zrefaktoryzowany jako Widget"""
    
    # Sygnały dla komunikacji z głównym oknem
    status_message = pyqtSignal(str, int)  # message, timeout
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Integracja z menedżerami aplikacji
        try:
            from ....utils import get_theme_manager, get_i18n
            self.theme_manager = get_theme_manager()
            self.i18n = get_i18n()
        except ImportError:
            # Fallback dla standalone execution
            self.theme_manager = None
            self.i18n = None
        
        # Menedżer danych
        try:
            from .shortcuts_data_manager import ShortcutsDataManager
            from .shortcuts_config import ShortcutsConfig
        except ImportError:
            # Standalone execution
            from shortcuts_data_manager import ShortcutsDataManager
            from shortcuts_config import ShortcutsConfig
        
        self.data_manager = ShortcutsDataManager()
        self.config = ShortcutsConfig
        
        # Dane
        self.shortcuts = self.data_manager.load_shortcuts()
        self.editing_index = None  # Indeks edytowanego skrótu (None = dodawanie nowego)
        
        # System skrótów
        self.system_active = False
        self.hotkey_listener = None
        
        # Sygnał dla menu (komunikacja między wątkami)
        self.menu_signal = TemplateMenuSignal()
        self.menu_signal.show_menu.connect(self.display_dynamic_menu)
        ActionExecutor.menu_signal = self.menu_signal
        
        # UI
        self.init_ui()
        
        # Inicjalizacja listenera
        self.hotkey_listener = HotkeyListener(self.get_active_shortcuts)
        self.hotkey_listener.hotkey_triggered.connect(self.on_hotkey_triggered)
        
        # Połączenia sygnałów menedżerów
        if self.i18n:
            self.i18n.language_changed.connect(self.update_ui_texts)
        if self.theme_manager:
            # Theme manager może mieć różne nazwy sygnału
            try:
                self.theme_manager.theme_changed.connect(self.apply_theme)
            except:
                pass
        
        # Odśwież listę po uruchomieniu
        self.refresh_shortcuts_list()
        
        # Zastosuj początkowy motyw i teksty
        self.apply_theme()
        self.update_ui_texts()

    def on_hotkey_triggered(self, name):
        """Wywoływane po wykryciu globalnego skrótu klawiszowego."""
        print(f"Wykryto skrót: {name}")
        
        # Sprawdź czy to klawisz przytrzymania (ma sufiks :press lub :release)
        hold_event = None
        original_name = name
        
        if ':press' in name:
            original_name = name.replace(':press', '')
            hold_event = 'press'
        elif ':release' in name:
            original_name = name.replace(':release', '')
            hold_event = 'release'
        
        # Znajdź skrót po nazwie
        shortcut_to_run = None
        for s in self.shortcuts:
            if s.get('name') == original_name:
                shortcut_to_run = s
                break
        
        if shortcut_to_run:
            # Dla klawisza przytrzymania - wykonaj akcję tylko przy PRESS
            if hold_event == 'release':
                # Ignoruj eventy RELEASE - użytkownik może utworzyć osobny skrót jeśli potrzebuje
                return
            
            delimiter = None
            if (
                shortcut_to_run.get('shortcut_type') == 'Magiczna fraza'
                and self.hotkey_listener
            ):
                delimiter = self.hotkey_listener.pop_phrase_trigger(original_name)

            self.emit_status(f"Wykonywanie skrótu: {original_name}...", 2000)
            success, message = ActionExecutor.execute(shortcut_to_run)
            if success:
                self.emit_status(f"Skrót '{original_name}' wykonany: {message}", 4000)
            else:
                self.emit_status(f"Błąd skrótu '{original_name}': {message}", 5000)

            if shortcut_to_run.get('shortcut_type') == 'Magiczna fraza':
                self._reinsert_magic_delimiter(delimiter, shortcut_to_run)
        else:
            self.emit_status(f"Nie znaleziono skrótu o nazwie: {original_name}", 3000)

    def _reinsert_magic_delimiter(self, delimiter, shortcut):
        """Odtwarza naciśnięty klawisz wyzwalający po wykonaniu akcji magicznej frazy."""
        if not delimiter:
            return
        
        # Odtwórz delimiter dla WSZYSTKICH typów akcji, nie tylko "Wklej tekst"
        # (może być przydatne dla separacji po każdej akcji)

        if not self.hotkey_listener:
            return

        import keyboard

        try:
            if delimiter == 'space':
                self.hotkey_listener.run_with_phrase_suppressed(lambda: keyboard.write(' '))
            elif delimiter == 'tab':
                self.hotkey_listener.run_with_phrase_suppressed(lambda: keyboard.send('tab'))
        except Exception as e:
            print(f"Błąd przy odtwarzaniu delimitera '{delimiter}': {e}")

    def get_active_shortcuts(self):
        """Zwraca listę aktywnych skrótów dla listenera."""
        return [s for s in self.shortcuts if s.get('enabled', True)]

    def display_dynamic_menu(self, items, position):
        """Wyświetla menu kontekstowe (szablony lub skróty) przy kursorze."""
        if not items:
            return
        
        # Sprawdź typ pierwszego elementu, aby zdecydować, które menu utworzyć
        first_item = items[0]
        
        # Walidacja typu menu
        if 'content' in first_item:
            # Menu szablonów - sprawdź czy wszystkie mają wymagane pola
            if not all('name' in item and 'content' in item for item in items):
                print("Błąd: Nieprawidłowa struktura menu szablonów!")
                return
            menu = TemplateContextMenu(items, self)
        elif 'type' in first_item and 'path' in first_item:
            # Menu skrótów - sprawdź czy wszystkie mają wymagane pola
            if not all('name' in item and 'type' in item and 'path' in item for item in items):
                print("Błąd: Nieprawidłowa struktura menu skrótów!")
                return
            menu = ShortcutsContextMenu(items, self)
        else:
            print(f"Błąd: Nierozpoznany format menu! Pierwszy element: {first_item}")
            return
            
        menu.exec(position)
    
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        # Główny layout bezpośrednio na widget (nie przez central_widget)
        main_layout = QVBoxLayout(self)
        
        # Nagłówek z przyciskiem sterowania
        header_layout = QHBoxLayout()
        
        self.header_label = QLabel("Zarządzanie skrótami klawiszowymi")
        self.header_label.setProperty('class', self.config.get_style_class('header_label'))
        header_layout.addWidget(self.header_label)
        
        header_layout.addStretch()
        
        # Status systemu
        self.system_status_label = QLabel("System WYŁĄCZONY")
        self.system_status_label.setProperty('class', self.config.get_style_class('status_inactive'))
        header_layout.addWidget(self.system_status_label)
        
        # Przycisk włącz/wyłącz
        self.toggle_system_btn = QPushButton("▶ URUCHOM SYSTEM")
        self.toggle_system_btn.setProperty('class', self.config.get_style_class('btn_start'))
        self.toggle_system_btn.clicked.connect(self.toggle_system)
        header_layout.addWidget(self.toggle_system_btn)
        
        main_layout.addLayout(header_layout)
        
        # Splitter - podział pionowy
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # LEWA SEKCJA - Tworzenie skrótów
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # PRAWA SEKCJA - Lista skrótów
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Proporcje 40:60
        splitter.setStretchFactor(0, 40)
        splitter.setStretchFactor(1, 60)
        
        main_layout.addWidget(splitter)
        
        # Status początkowy
        self.emit_status("Gotowy")
    
    def create_left_panel(self):
        """Tworzy lewą sekcję - formularz dodawania skrótu"""
        panel = QGroupBox("Nowy skrót klawiszowy")
        layout = QVBoxLayout()
        
        # Nazwa skrótu
        self.label_name = QLabel("Nazwa skrótu:")
        layout.addWidget(self.label_name)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("np. Otwórz Notatnik")
        layout.addWidget(self.name_input)
        
        layout.addSpacing(10)
        
        # Rodzaj skrótu
        self.label_shortcut_type = QLabel("Rodzaj skrótu:")
        layout.addWidget(self.label_shortcut_type)
        self.shortcut_type_combo = QComboBox()
        self.shortcut_type_combo.addItems([
            "Kombinacja klawiszy",
            "Przytrzymaj klawisz",
            "Magiczna fraza"
        ])
        self.shortcut_type_combo.currentTextChanged.connect(self.on_shortcut_type_changed)
        layout.addWidget(self.shortcut_type_combo)
        
        layout.addSpacing(10)
        
        # Skrót/fraza
        self.label_shortcut = QLabel("Skrót/Fraza:")
        layout.addWidget(self.label_shortcut)
        
        # Nowy widget do przechwytywania skrótów (z przyciskiem)
        self.shortcut_input = ShortcutCaptureWidget()
        layout.addWidget(self.shortcut_input)
        
        layout.addSpacing(10)
        
        # Tryb skrótu
        self.label_action_type = QLabel("Tryb skrótu:")
        layout.addWidget(self.label_action_type)
        self.action_type_combo = QComboBox()
        self.action_type_combo.addItems([
            "Wklej tekst",
            "Menu z szablonami",
            "Menu skrótów",
            "Otwórz aplikację",
            "Otwórz plik",
            "Polecenie PowerShell",
            "Polecenie wiersza poleceń",
            "Wykonaj sekwencję kliknięć"
        ])
        self.action_type_combo.currentTextChanged.connect(self.on_action_type_changed)
        layout.addWidget(self.action_type_combo)
        
        layout.addSpacing(10)
        
        # Wartość akcji (tekst/ścieżka/komenda/sekwencja)
        self.label_action_value = QLabel("Wartość akcji:")
        layout.addWidget(self.label_action_value)
        action_layout = QHBoxLayout()
        
        self.action_input = QTextEdit()
        self.action_input.setMaximumHeight(100)
        self.action_input.setPlaceholderText("Wprowadź tekst, ścieżkę lub komendę...")
        action_layout.addWidget(self.action_input)
        
        action_buttons_layout = QVBoxLayout()
        self.btn_browse = QPushButton("Przeglądaj...")
        self.btn_browse.clicked.connect(self.browse_file)
        action_buttons_layout.addWidget(self.btn_browse)
        
        self.btn_record_clicks = QPushButton("Nagraj kliknięcia")
        self.btn_record_clicks.clicked.connect(self.record_click_sequence)
        self.btn_record_clicks.setVisible(False)
        action_buttons_layout.addWidget(self.btn_record_clicks)
        
        self.btn_test_clicks = QPushButton("Testuj sekwencję")
        self.btn_test_clicks.clicked.connect(self.test_click_sequence)
        self.btn_test_clicks.setVisible(False)
        self.btn_test_clicks.setProperty('class', config.get_style_class('btn_test_clicks'))
        action_buttons_layout.addWidget(self.btn_test_clicks)
        
        action_buttons_layout.addStretch()
        
        action_layout.addLayout(action_buttons_layout)
        
        layout.addLayout(action_layout)
        
        # Widget dla szablonów menu (początkowo ukryty)
        self.templates_widget = QWidget()
        templates_layout = QVBoxLayout()
        self.templates_widget.setLayout(templates_layout)
        self.templates_widget.setVisible(False)
        
        self.templates_header = QLabel("Szablony tekstowe w menu:")
        self.templates_header.setProperty('class', config.get_style_class('templates_header'))
        templates_layout.addWidget(self.templates_header)
        
        # Tabela szablonów
        self.templates_table = QTableWidget()
        self.templates_table.setColumnCount(2)
        self.templates_table.setHorizontalHeaderLabels(["Nazwa w menu", "Treść szablonu"])
        self.templates_table.setMaximumHeight(150)
        self.templates_table.horizontalHeader().setStretchLastSection(True)
        templates_layout.addWidget(self.templates_table)
        
        # Przyciski zarządzania szablonami
        templates_buttons = QHBoxLayout()
        
        self.btn_add_template = QPushButton("➕ Dodaj szablon")
        self.btn_add_template.clicked.connect(self.add_template)
        self.btn_add_template.setProperty('class', config.get_style_class('btn_add_template'))
        templates_buttons.addWidget(self.btn_add_template)
        
        self.btn_edit_template = QPushButton("✏ Edytuj")
        self.btn_edit_template.clicked.connect(self.edit_template)
        templates_buttons.addWidget(self.btn_edit_template)
        
        self.btn_delete_template = QPushButton("🗑 Usuń")
        self.btn_delete_template.clicked.connect(self.delete_template)
        self.btn_delete_template.setProperty('class', config.get_style_class('btn_delete_template'))
        templates_buttons.addWidget(self.btn_delete_template)
        
        templates_layout.addLayout(templates_buttons)
        
        layout.addWidget(self.templates_widget)
        
        # Widget dla menu skrótów (początkowo ukryty)
        self.shortcuts_menu_widget = QWidget()
        shortcuts_menu_layout = QVBoxLayout()
        self.shortcuts_menu_widget.setLayout(shortcuts_menu_layout)
        self.shortcuts_menu_widget.setVisible(False)
        
        self.shortcuts_menu_header = QLabel("Pozycje w menu skrótów:")
        self.shortcuts_menu_header.setProperty('class', config.get_style_class('shortcuts_menu_header'))
        shortcuts_menu_layout.addWidget(self.shortcuts_menu_header)
        
        # Tabela pozycji menu
        self.shortcuts_menu_table = QTableWidget()
        self.shortcuts_menu_table.setColumnCount(3)
        self.shortcuts_menu_table.setHorizontalHeaderLabels(["Nazwa w menu", "Typ", "Ścieżka/Akcja"])
        self.shortcuts_menu_table.setMaximumHeight(150)
        header_sm = self.shortcuts_menu_table.horizontalHeader()
        if header_sm:
            header_sm.setStretchLastSection(True)
        shortcuts_menu_layout.addWidget(self.shortcuts_menu_table)
        
        # Przyciski zarządzania pozycjami menu
        shortcuts_menu_buttons = QHBoxLayout()
        
        self.btn_add_menu_item = QPushButton("➕ Dodaj pozycję")
        self.btn_add_menu_item.clicked.connect(self.add_shortcuts_menu_item)
        self.btn_add_menu_item.setProperty('class', config.get_style_class('btn_add_menu_item'))
        shortcuts_menu_buttons.addWidget(self.btn_add_menu_item)
        
        self.btn_edit_menu_item = QPushButton("✏ Edytuj")
        self.btn_edit_menu_item.clicked.connect(self.edit_shortcuts_menu_item)
        shortcuts_menu_buttons.addWidget(self.btn_edit_menu_item)
        
        self.btn_delete_menu_item = QPushButton("🗑 Usuń")
        self.btn_delete_menu_item.clicked.connect(self.delete_shortcuts_menu_item)
        self.btn_delete_menu_item.setProperty('class', config.get_style_class('btn_delete_menu_item'))
        shortcuts_menu_buttons.addWidget(self.btn_delete_menu_item)
        
        shortcuts_menu_layout.addLayout(shortcuts_menu_buttons)
        
        layout.addWidget(self.shortcuts_menu_widget)
        
        layout.addSpacing(10)
        
        # Dodatkowy opis
        layout.addWidget(QLabel("Opis (opcjonalnie):"))
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(80)
        self.description_input.setPlaceholderText("Dodatkowy opis skrótu...")
        layout.addWidget(self.description_input)
        
        layout.addSpacing(10)
        
        # Aktywny
        self.enabled_checkbox = QCheckBox("Aktywny (włączony)")
        self.enabled_checkbox.setChecked(True)
        layout.addWidget(self.enabled_checkbox)
        
        layout.addSpacing(20)
        
        # Przyciski akcji
        buttons_layout = QHBoxLayout()
        
        self.btn_test = QPushButton("🧪 Testuj akcję")
        self.btn_test.setProperty('class', config.get_style_class('btn_test'))
        self.btn_test.clicked.connect(self.test_action)
        buttons_layout.addWidget(self.btn_test)
        
        self.btn_add = QPushButton("Dodaj skrót")
        self.btn_add.setProperty('class', config.get_style_class('btn_add'))
        self.btn_add.clicked.connect(self.add_shortcut)
        buttons_layout.addWidget(self.btn_add)
        
        self.btn_clear = QPushButton("Wyczyść formularz")
        self.btn_clear.clicked.connect(self.clear_form)
        buttons_layout.addWidget(self.btn_clear)
        
        layout.addLayout(buttons_layout)
        
        layout.addStretch()
        
        panel.setLayout(layout)
        return panel
    
    def create_right_panel(self):
        """Tworzy prawą sekcję - tabela z listą skrótów"""
        panel = QGroupBox("Lista skrótów")
        layout = QVBoxLayout()
        
        # Pasek narzędzi
        toolbar_layout = QHBoxLayout()
        
        self.btn_refresh = QPushButton("Odśwież")
        self.btn_refresh.clicked.connect(self.refresh_shortcuts_list)
        toolbar_layout.addWidget(self.btn_refresh)
        
        self.btn_edit = QPushButton("Edytuj")
        self.btn_edit.clicked.connect(self.edit_shortcut)
        toolbar_layout.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton("Usuń")
        self.btn_delete.clicked.connect(self.delete_shortcut)
        toolbar_layout.addWidget(self.btn_delete)
        
        toolbar_layout.addStretch()
        
        self.btn_import = QPushButton("Import")
        self.btn_import.clicked.connect(self.import_shortcuts)
        toolbar_layout.addWidget(self.btn_import)
        
        self.btn_export = QPushButton("Export")
        self.btn_export.clicked.connect(self.export_shortcuts)
        toolbar_layout.addWidget(self.btn_export)
        
        layout.addLayout(toolbar_layout)
        
        # Tabela
        self.shortcuts_table = QTableWidget()
        self.shortcuts_table.setColumnCount(5)
        self.shortcuts_table.setHorizontalHeaderLabels([
            "Lp", "Nazwa", "Skrót/Fraza", "Tryb akcji", "Status"
        ])
        
        # Konfiguracja tabeli
        self.shortcuts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.shortcuts_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        self.shortcuts_table.doubleClicked.connect(self.edit_shortcut)
        
        # Automatyczne rozciąganie kolumn
        header = self.shortcuts_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)  # Lp
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Nazwa
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)  # Skrót
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)  # Typ akcji
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Status
        
        layout.addWidget(self.shortcuts_table)
        
        # Informacja o liczbie skrótów
        self.count_label = QLabel("Skrótów: 0")
        layout.addWidget(self.count_label)
        
        panel.setLayout(layout)
        return panel
    
    def on_shortcut_type_changed(self, shortcut_type):
        """Obsługa zmiany rodzaju skrótu"""
        if shortcut_type == "Magiczna fraza":
            # Przełącz widget w tryb wpisywania tekstu
            self.shortcut_input.set_magic_phrase_mode(True)
        else:
            # Przełącz widget w tryb przechwytywania klawiszy
            self.shortcut_input.set_magic_phrase_mode(False)
    
    def on_action_type_changed(self, action_type):
        """Obsługa zmiany trybu skrótu"""
        # Ukryj/pokaż odpowiednie przyciski i widgety
        if action_type == "Wklej tekst":
            self.action_input.setPlaceholderText("Wprowadź tekst do wklejenia...")
            self.action_input.setVisible(True)
            self.btn_browse.setVisible(False)
            self.btn_record_clicks.setVisible(False)
            self.btn_test_clicks.setVisible(False)
            self.templates_widget.setVisible(False)
            self.shortcuts_menu_widget.setVisible(False)
        elif action_type == "Menu z szablonami":
            self.action_input.setVisible(False)
            self.btn_browse.setVisible(False)
            self.btn_record_clicks.setVisible(False)
            self.btn_test_clicks.setVisible(False)
            self.templates_widget.setVisible(True)
            self.shortcuts_menu_widget.setVisible(False)
        elif action_type == "Menu skrótów":
            self.action_input.setVisible(False)
            self.btn_browse.setVisible(False)
            self.btn_record_clicks.setVisible(False)
            self.btn_test_clicks.setVisible(False)
            self.templates_widget.setVisible(False)
            self.shortcuts_menu_widget.setVisible(True)
        elif action_type == "Otwórz aplikację":
            self.action_input.setPlaceholderText("Ścieżka do pliku .exe...")
            self.action_input.setVisible(True)
            self.btn_browse.setVisible(True)
            self.btn_record_clicks.setVisible(False)
            self.btn_test_clicks.setVisible(False)
            self.templates_widget.setVisible(False)
            self.shortcuts_menu_widget.setVisible(False)
        elif action_type == "Otwórz plik":
            self.action_input.setPlaceholderText("Ścieżka do pliku...")
            self.action_input.setVisible(True)
            self.btn_browse.setVisible(True)
            self.btn_record_clicks.setVisible(False)
            self.btn_test_clicks.setVisible(False)
            self.templates_widget.setVisible(False)
            self.shortcuts_menu_widget.setVisible(False)
        elif action_type == "Polecenie PowerShell":
            self.action_input.setPlaceholderText("Polecenie PowerShell, np.:\nGet-Process | Where-Object {$_.CPU -gt 100}\nStart-Process notepad")
            self.action_input.setVisible(True)
            self.btn_browse.setVisible(False)
            self.btn_record_clicks.setVisible(False)
            self.btn_test_clicks.setVisible(False)
            self.templates_widget.setVisible(False)
            self.shortcuts_menu_widget.setVisible(False)
        elif action_type == "Polecenie wiersza poleceń":
            self.action_input.setPlaceholderText("Polecenie CMD, np.:\ndir /s\nipconfig /all\nping google.com")
            self.action_input.setVisible(True)
            self.btn_browse.setVisible(False)
            self.btn_record_clicks.setVisible(False)
            self.btn_test_clicks.setVisible(False)
            self.templates_widget.setVisible(False)
            self.shortcuts_menu_widget.setVisible(False)
        elif action_type == "Wykonaj sekwencję kliknięć":
            self.action_input.setPlaceholderText("Sekwencja kliknięć (nagraj lub wprowadź manualnie)...")
            self.action_input.setVisible(True)
            self.btn_browse.setVisible(False)
            self.btn_record_clicks.setVisible(True)
            # Pokaż przycisk testowania tylko jeśli jest jakaś sekwencja
            has_sequence = bool(self.action_input.toPlainText().strip())
            self.btn_test_clicks.setVisible(has_sequence)
            self.templates_widget.setVisible(False)
            self.shortcuts_menu_widget.setVisible(False)
    
    def clear_shortcut(self):
        """Czyści pole skrótu klawiszowego"""
        self.shortcut_input.clear()
    
    def add_template(self):
        """Dodaje nowy szablon do tabeli szablonów"""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        
        # Dialog do dodawania szablonu
        dialog = QDialog(self)
        dialog.setWindowTitle("Dodaj szablon")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Nazwa w menu:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("np. Powitanie, Podpis email, Adres...")
        layout.addWidget(name_input)
        
        layout.addSpacing(10)
        
        layout.addWidget(QLabel("Treść szablonu:"))
        content_input = QTextEdit()
        content_input.setPlaceholderText("Wprowadź tekst szablonu...")
        content_input.setMinimumHeight(150)
        layout.addWidget(content_input)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            content = content_input.toPlainText().strip()
            
            if not name or not content:
                QMessageBox.warning(self, "Błąd", "Podaj nazwę i treść szablonu!")
                return
            
            # Dodaj do tabeli
            row = self.templates_table.rowCount()
            self.templates_table.insertRow(row)
            self.templates_table.setItem(row, 0, QTableWidgetItem(name))
            self.templates_table.setItem(row, 1, QTableWidgetItem(content))
    
    def edit_template(self):
        """Edytuje wybrany szablon"""
        selected_rows = self.templates_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Błąd", "Wybierz szablon do edycji!")
            return
        
        row = selected_rows[0].row()
        
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edytuj szablon")
        dialog.setMinimumWidth(500)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Nazwa w menu:"))
        name_input = QLineEdit()
        name_input.setText(self.templates_table.item(row, 0).text())
        layout.addWidget(name_input)
        
        layout.addSpacing(10)
        
        layout.addWidget(QLabel("Treść szablonu:"))
        content_input = QTextEdit()
        content_input.setPlainText(self.templates_table.item(row, 1).text())
        content_input.setMinimumHeight(150)
        layout.addWidget(content_input)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            content = content_input.toPlainText().strip()
            
            if not name or not content:
                QMessageBox.warning(self, "Błąd", "Podaj nazwę i treść szablonu!")
                return
            
            self.templates_table.setItem(row, 0, QTableWidgetItem(name))
            self.templates_table.setItem(row, 1, QTableWidgetItem(content))
    
    def delete_template(self):
        """Usuwa wybrany szablon"""
        selected_rows = self.templates_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Błąd", "Wybierz szablon do usunięcia!")
            return
        
        row = selected_rows[0].row()
        template_name = self.templates_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć szablon '{template_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.templates_table.removeRow(row)
    
    def add_shortcuts_menu_item(self):
        """Dodaje nową pozycję do menu skrótów"""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        
        # Dialog do dodawania pozycji menu
        dialog = QDialog(self)
        dialog.setWindowTitle("Dodaj pozycję menu")
        dialog.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Nazwa w menu:"))
        name_input = QLineEdit()
        name_input.setPlaceholderText("np. Otwórz Dokumenty, Uruchom Chrome, Pokaż Kalend arz...")
        layout.addWidget(name_input)
        
        layout.addSpacing(10)
        
        layout.addWidget(QLabel("Typ pozycji:"))
        type_combo = QComboBox()
        type_combo.addItems([
            "Folder",
            "Plik",
            "Skrót"
        ])
        layout.addWidget(type_combo)
        
        layout.addSpacing(10)
        
        layout.addWidget(QLabel("Ścieżka/Akcja:"))
        path_layout = QHBoxLayout()
        path_input = QLineEdit()
        path_input.setPlaceholderText("Ścieżka do pliku/folderu lub polecenie/tekst...")
        path_layout.addWidget(path_input)
        
        browse_btn = QPushButton("📁 Przeglądaj")
        browse_btn.clicked.connect(lambda: self.browse_for_menu_item(type_combo.currentText(), path_input))
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            item_type = type_combo.currentText()
            path = path_input.text().strip()
            
            if not name or not path:
                QMessageBox.warning(self, "Błąd", "Podaj nazwę i ścieżkę/akcję!")
                return
            
            # Dodaj do tabeli
            row = self.shortcuts_menu_table.rowCount()
            self.shortcuts_menu_table.insertRow(row)
            self.shortcuts_menu_table.setItem(row, 0, QTableWidgetItem(name))
            self.shortcuts_menu_table.setItem(row, 1, QTableWidgetItem(item_type))
            self.shortcuts_menu_table.setItem(row, 2, QTableWidgetItem(path))
    
    def edit_shortcuts_menu_item(self):
        """Edytuje wybraną pozycję menu skrótów"""
        selected_rows = self.shortcuts_menu_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Błąd", "Wybierz pozycję do edycji!")
            return
        
        row = selected_rows[0].row()
        
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Edytuj pozycję menu")
        dialog.setMinimumWidth(600)
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Nazwa w menu:"))
        name_input = QLineEdit()
        name_item = self.shortcuts_menu_table.item(row, 0)
        if name_item:
            name_input.setText(name_item.text())
        layout.addWidget(name_input)
        
        layout.addSpacing(10)
        
        layout.addWidget(QLabel("Typ pozycji:"))
        type_combo = QComboBox()
        type_combo.addItems([
            "Folder",
            "Plik",
            "Skrót"
        ])
        type_item = self.shortcuts_menu_table.item(row, 1)
        if type_item:
            idx = type_combo.findText(type_item.text())
            if idx >= 0:
                type_combo.setCurrentIndex(idx)
        layout.addWidget(type_combo)
        
        layout.addSpacing(10)
        
        layout.addWidget(QLabel("Ścieżka/Akcja:"))
        path_layout = QHBoxLayout()
        path_input = QLineEdit()
        path_item = self.shortcuts_menu_table.item(row, 2)
        if path_item:
            path_input.setText(path_item.text())
        path_layout.addWidget(path_input)
        
        browse_btn = QPushButton("📁 Przeglądaj")
        browse_btn.clicked.connect(lambda: self.browse_for_menu_item(type_combo.currentText(), path_input))
        path_layout.addWidget(browse_btn)
        
        layout.addLayout(path_layout)
        
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addWidget(buttons)
        
        dialog.setLayout(layout)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            name = name_input.text().strip()
            item_type = type_combo.currentText()
            path = path_input.text().strip()
            
            if not name or not path:
                QMessageBox.warning(self, "Błąd", "Podaj nazwę i ścieżkę/akcję!")
                return
            
            self.shortcuts_menu_table.setItem(row, 0, QTableWidgetItem(name))
            self.shortcuts_menu_table.setItem(row, 1, QTableWidgetItem(item_type))
            self.shortcuts_menu_table.setItem(row, 2, QTableWidgetItem(path))
    
    def delete_shortcuts_menu_item(self):
        """Usuwa wybraną pozycję z menu skrótów"""
        selected_rows = self.shortcuts_menu_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Błąd", "Wybierz pozycję do usunięcia!")
            return
        
        row = selected_rows[0].row()
        name_item = self.shortcuts_menu_table.item(row, 0)
        item_name = name_item.text() if name_item else "tę pozycję"
        
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć '{item_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.shortcuts_menu_table.removeRow(row)
    
    def browse_for_menu_item(self, item_type, line_edit):
        """Pomocnicza funkcja do wyboru pliku/folderu dla pozycji menu"""
        if item_type == "Folder":
            path = QFileDialog.getExistingDirectory(self, "Wybierz folder")
        elif item_type == "Plik":
            path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik", "", "Wszystkie pliki (*.*)")
        elif item_type == "Skrót":
            path, _ = QFileDialog.getOpenFileName(
                self, "Wybierz skrót/aplikację", "", "Pliki wykonywalne (*.exe *.lnk);;Wszystkie pliki (*.*)"
            )
        else:
            return
        
        if path:
            line_edit.setText(path)
    
    def record_click_sequence(self):
        """Nagrywa sekwencję kliknięć"""
        # Minimalizuj główne okno
        self.setWindowState(Qt.WindowState.WindowMinimized)
        
        # Stwórz i pokaż nakładkę
        self.recorder_overlay = ClickRecorderOverlay()
        self.recorder_overlay.recording_finished.connect(self.on_recording_finished)
        self.recorder_overlay.showFullScreen()
    
    def on_recording_finished(self, clicks):
        """Obsługa zakończenia nagrywania"""
        # Przywróć okno
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.activateWindow()
        
        if not clicks:
            # Użytkownik anulował
            return
        
        # Konwertuj kliknięcia do JSON
        clicks_json = json.dumps(clicks, indent=2)
        self.action_input.setPlainText(clicks_json)
        
        # Pokaż przycisk testowania
        self.btn_test_clicks.setVisible(True)
        
        QMessageBox.information(
            self,
            "Sukces",
            f"Nagrano {len(clicks)} kliknięć!\n\n"
            f"Sekwencja została zapisana w polu akcji."
        )
    
    def test_click_sequence(self):
        """Testuje sekwencję kliknięć - pokazuje gdzie aplikacja kliknie"""
        # Pobierz sekwencję z pola tekstowego
        sequence_text = self.action_input.toPlainText().strip()
        if not sequence_text:
            QMessageBox.warning(self, "Błąd", "Brak sekwencji do przetestowania!")
            return
        
        try:
            # Parsuj JSON
            clicks = json.loads(sequence_text)
            if not isinstance(clicks, list) or len(clicks) == 0:
                raise ValueError("Sekwencja musi być niepustą listą")
            
            # Walidacja struktury każdego kliknięcia
            for i, click in enumerate(clicks):
                if not isinstance(click, dict):
                    raise ValueError(f"Kliknięcie {i+1} musi być obiektem (słownikiem)")
                
                # Sprawdź wymagane pola
                required_fields = ['x', 'y', 'button', 'time_offset']
                for field in required_fields:
                    if field not in click:
                        raise ValueError(f"Kliknięcie {i+1} nie ma pola '{field}'")
                
                # Sprawdź typy danych
                if not isinstance(click['x'], (int, float)):
                    raise ValueError(f"Kliknięcie {i+1}: 'x' musi być liczbą")
                if not isinstance(click['y'], (int, float)):
                    raise ValueError(f"Kliknięcie {i+1}: 'y' musi być liczbą")
                if not isinstance(click['button'], str):
                    raise ValueError(f"Kliknięcie {i+1}: 'button' musi być tekstem")
                if not isinstance(click['time_offset'], (int, float)):
                    raise ValueError(f"Kliknięcie {i+1}: 'time_offset' musi być liczbą")
                
        except Exception as e:
            QMessageBox.warning(
                self,
                "Błąd",
                f"Nie można sparsować sekwencji:\n{str(e)}\n\n"
                f"Upewnij się, że format jest poprawny (JSON)."
            )
            return
        
        # Minimalizuj główne okno
        self.setWindowState(Qt.WindowState.WindowMinimized)
        
        # Stwórz nakładkę testową
        self.test_overlay = ClickTestOverlay(clicks)
        self.test_overlay.test_finished.connect(self.on_test_finished)
        self.test_overlay.showFullScreen()
    
    def on_test_finished(self):
        """Obsługa zakończenia testu"""
        # Przywróć okno
        self.setWindowState(Qt.WindowState.WindowNoState)
        self.activateWindow()
    
    def test_action(self):
        """Testuje akcję bez zapisywania skrótu"""
        # Pobierz dane z formularza
        action_type = self.action_type_combo.currentText()
        action_value = self.action_input.toPlainText().strip()
        
        if not action_value:
            QMessageBox.warning(self, "Błąd", "Wprowadź wartość akcji do przetestowania!")
            return
        
        # Stwórz tymczasowy skrót do testowania
        test_shortcut = {
            'name': 'TEST',
            'action_type': action_type,
            'action_value': action_value
        }
        
        # Wykonaj akcję
        self.emit_status("Wykonywanie akcji testowej...")
        success, message = ActionExecutor.execute(test_shortcut)
        
        # Pokaż wynik
        if success:
            self.emit_status(f"Test OK: {message}", 5000)
            QMessageBox.information(
                self,
                "Test akcji - Sukces ✓",
                f"Akcja wykonana pomyślnie!\n\n{message}"
            )
        else:
            self.emit_status(f"Test FAILED: {message}", 5000)
            QMessageBox.warning(
                self,
                "Test akcji - Błąd ✗",
                f"Nie udało się wykonać akcji:\n\n{message}"
            )
    
    def browse_file(self):
        """Otwiera dialog wyboru pliku"""
        action_type = self.action_type_combo.currentText()
        
        if action_type == "Otwórz aplikację":
            path, _ = QFileDialog.getOpenFileName(
                self, "Wybierz aplikację", "", "Pliki wykonywalne (*.exe);;Wszystkie pliki (*.*)"
            )
        elif action_type == "Otwórz plik":
            path, _ = QFileDialog.getOpenFileName(
                self, "Wybierz plik", "", "Wszystkie pliki (*.*)"
            )
        else:
            return
        
        if path:
            self.action_input.setPlainText(path)
    
    def clear_form(self):
        """Czyści formularz"""
        self.name_input.clear()
        self.shortcut_input.clear()
        self.action_input.clear()
        self.description_input.clear()
        self.shortcut_type_combo.setCurrentIndex(0)
        self.action_type_combo.setCurrentIndex(0)
        self.enabled_checkbox.setChecked(True)
        self.templates_table.setRowCount(0)  # Wyczyść tabelę szablonów
        self.shortcuts_menu_table.setRowCount(0)  # Wyczyść tabelę menu skrótów
        self.editing_index = None  # Anuluj tryb edycji
    
    def add_shortcut(self):
        """Dodaje nowy skrót do listy lub aktualizuje edytowany"""
        # Walidacja
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "Błąd", "Podaj nazwę skrótu!")
            return
        
        shortcut_value = self.shortcut_input.text().strip()
        if not shortcut_value:
            QMessageBox.warning(self, "Błąd", "Zdefiniuj skrót/frazę!")
            return
        
        action_type = self.action_type_combo.currentText()
        
        # Pobierz wartość akcji w zależności od typu
        if action_type == "Menu z szablonami":
            # Zbierz szablony z tabeli
            templates = []
            for row in range(self.templates_table.rowCount()):
                template_name = self.templates_table.item(row, 0)
                template_content = self.templates_table.item(row, 1)
                
                if template_name and template_content:
                    templates.append({
                        'name': template_name.text(),
                        'content': template_content.text()
                    })
            
            if not templates:
                QMessageBox.warning(self, "Błąd", "Dodaj przynajmniej jeden szablon do menu!")
                return
            
            # Konwertuj szablony do JSON
            action_value = json.dumps(templates, ensure_ascii=False, indent=2)
        
        elif action_type == "Menu skrótów":
            # Zbierz pozycje menu z tabeli
            menu_items = []
            for row in range(self.shortcuts_menu_table.rowCount()):
                item_name = self.shortcuts_menu_table.item(row, 0)
                item_type = self.shortcuts_menu_table.item(row, 1)
                item_path = self.shortcuts_menu_table.item(row, 2)
                
                if item_name and item_type and item_path:
                    menu_items.append({
                        'name': item_name.text(),
                        'type': item_type.text(),
                        'path': item_path.text()
                    })
            
            if not menu_items:
                QMessageBox.warning(self, "Błąd", "Dodaj przynajmniej jedną pozycję do menu skrótów!")
                return
            
            # Konwertuj pozycje menu do JSON
            action_value = json.dumps(menu_items, ensure_ascii=False, indent=2)
        
        else:
            action_value = self.action_input.toPlainText().strip()
            if not action_value:
                QMessageBox.warning(self, "Błąd", "Podaj wartość akcji!")
                return
        
        # Sprawdź czy skrót już istnieje (pomiń sprawdzanie jeśli edytujemy ten sam skrót)
        for idx, s in enumerate(self.shortcuts):
            # Pomiń sprawdzanie jeśli to edytowany skrót
            if self.editing_index is not None and idx == self.editing_index:
                continue
            
            if s['shortcut_value'] == shortcut_value:
                QMessageBox.warning(
                    self, 
                    "Błąd", 
                    f"Skrót '{shortcut_value}' jest już używany przez '{s['name']}'!"
                )
                return
        
        # Utwórz obiekt skrótu
        shortcut_data = {
            'name': name,
            'shortcut_type': self.shortcut_type_combo.currentText(),
            'shortcut_value': shortcut_value,
            'action_type': action_type,
            'action_value': action_value,
            'description': self.description_input.toPlainText().strip(),
            'enabled': self.enabled_checkbox.isChecked(),
            'created': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
        # Tryb edycji - zaktualizuj istniejący skrót
        if self.editing_index is not None:
            # Zachowaj datę utworzenia
            old_shortcut = self.shortcuts[self.editing_index]
            shortcut_data['created'] = old_shortcut.get('created', shortcut_data['created'])
            
            # Zastąp stary skrót
            self.shortcuts[self.editing_index] = shortcut_data
            
            self.save_data()
            self.refresh_shortcuts_list()
            self.clear_form()
            
            QMessageBox.information(
                self,
                "Sukces",
                f"Skrót '{name}' został zaktualizowany!"
            )
        else:
            # Tryb dodawania - dodaj nowy skrót
            self.shortcuts.append(shortcut_data)
            
            self.save_data()
            self.refresh_shortcuts_list()
            self.clear_form()
            
            QMessageBox.information(
                self,
                "Sukces",
                f"Skrót '{name}' został dodany!"
            )
    
    def refresh_shortcuts_list(self):
        """Odświeża listę skrótów w tabeli"""
        self.shortcuts_table.setRowCount(0)
        
        for idx, shortcut in enumerate(self.shortcuts, 1):
            row = self.shortcuts_table.rowCount()
            self.shortcuts_table.insertRow(row)
            
            # Lp
            self.shortcuts_table.setItem(row, 0, QTableWidgetItem(str(idx)))
            
            # Nazwa
            self.shortcuts_table.setItem(row, 1, QTableWidgetItem(shortcut['name']))
            
            # Skrót/Fraza
            shortcut_display = f"{shortcut.get('shortcut_type', 'Kombinacja klawiszy')}: {shortcut.get('shortcut_value', '')}"
            self.shortcuts_table.setItem(row, 2, QTableWidgetItem(shortcut_display))
            
            # Tryb akcji
            self.shortcuts_table.setItem(row, 3, QTableWidgetItem(shortcut['action_type']))
            
            # Status
            status = "✓ Aktywny" if shortcut.get('enabled', True) else "✗ Nieaktywny"
            status_item = QTableWidgetItem(status)
            if shortcut.get('enabled', True):
                status_item.setForeground(Qt.GlobalColor.darkGreen)
            else:
                status_item.setForeground(Qt.GlobalColor.red)
            self.shortcuts_table.setItem(row, 4, status_item)
        
        self.count_label.setText(f"Skrótów: {len(self.shortcuts)}")
    
    def edit_shortcut(self):
        """Edytuje wybrany skrót - ładuje dane do formularza"""
        selected_rows = self.shortcuts_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Błąd", "Wybierz skrót do edycji!")
            return
        
        row = selected_rows[0].row()
        if row >= len(self.shortcuts):
            return
        
        # Ustaw tryb edycji
        self.editing_index = row
        
        shortcut = self.shortcuts[row]
        
        # Załaduj dane do formularza
        self.name_input.setText(shortcut['name'])
        
        # Ustaw rodzaj skrótu
        shortcut_type = shortcut.get('shortcut_type', 'Kombinacja klawiszy')
        index = self.shortcut_type_combo.findText(shortcut_type)
        if index >= 0:
            self.shortcut_type_combo.setCurrentIndex(index)
        
        self.shortcut_input.setText(shortcut.get('shortcut_value', ''))
        
        # Ustaw tryb akcji
        action_type = shortcut['action_type']
        index = self.action_type_combo.findText(action_type)
        if index >= 0:
            self.action_type_combo.setCurrentIndex(index)
        
        # Załaduj wartość akcji
        if action_type == "Menu z szablonami":
            # Parsuj JSON i załaduj szablony do tabeli
            try:
                templates = json.loads(shortcut['action_value'])
                self.templates_table.setRowCount(0)
                
                for template in templates:
                    row_idx = self.templates_table.rowCount()
                    self.templates_table.insertRow(row_idx)
                    self.templates_table.setItem(row_idx, 0, QTableWidgetItem(template.get('name', '')))
                    self.templates_table.setItem(row_idx, 1, QTableWidgetItem(template.get('content', '')))
            except:
                pass
        elif action_type == "Menu skrótów":
            # Parsuj JSON i załaduj pozycje menu do tabeli
            try:
                menu_items = json.loads(shortcut['action_value'])
                self.shortcuts_menu_table.setRowCount(0)
                
                for item in menu_items:
                    row_idx = self.shortcuts_menu_table.rowCount()
                    self.shortcuts_menu_table.insertRow(row_idx)
                    self.shortcuts_menu_table.setItem(row_idx, 0, QTableWidgetItem(item.get('name', '')))
                    self.shortcuts_menu_table.setItem(row_idx, 1, QTableWidgetItem(item.get('type', '')))
                    self.shortcuts_menu_table.setItem(row_idx, 2, QTableWidgetItem(item.get('path', '')))
            except:
                pass
        else:
            self.action_input.setPlainText(shortcut['action_value'])
        
        self.description_input.setPlainText(shortcut.get('description', ''))
        self.enabled_checkbox.setChecked(shortcut.get('enabled', True))
        
        # Informacja dla użytkownika
        QMessageBox.information(
            self,
            "Tryb edycji",
            f"Edytujesz skrót: {shortcut['name']}\n\n"
            "Wprowadź zmiany i kliknij 'Dodaj skrót' aby zapisać.\n"
            "Kliknij 'Wyczyść formularz' aby anulować edycję."
        )
    
    def delete_shortcut(self):
        """Usuwa wybrany skrót"""
        selected_rows = self.shortcuts_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Błąd", "Wybierz skrót do usunięcia!")
            return
        
        row = selected_rows[0].row()
        if row >= len(self.shortcuts):
            return
        
        shortcut = self.shortcuts[row]
        
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć skrót '{shortcut['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.shortcuts.pop(row)
            self.save_data()
            self.refresh_shortcuts_list()
            QMessageBox.information(self, "Sukces", "Skrót został usunięty!")
    
    def import_shortcuts(self):
        """Importuje skróty z pliku JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importuj skróty",
            "",
            "Pliki JSON (*.json);;Wszystkie pliki (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    imported = json.load(f)
                
                if isinstance(imported, list):
                    self.shortcuts.extend(imported)
                    self.save_data()
                    self.refresh_shortcuts_list()
                    QMessageBox.information(
                        self,
                        "Sukces",
                        f"Zaimportowano {len(imported)} skrótów!"
                    )
                else:
                    QMessageBox.warning(self, "Błąd", "Nieprawidłowy format pliku!")
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie udało się zaimportować:\n{str(e)}")
    
    def export_shortcuts(self):
        """Eksportuje skróty do pliku JSON"""
        if not self.shortcuts:
            QMessageBox.warning(self, "Błąd", "Brak skrótów do eksportu!")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksportuj skróty",
            "shortcuts_export.json",
            "Pliki JSON (*.json);;Wszystkie pliki (*.*)"
        )
        
        if file_path:
            try:
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(self.shortcuts, f, ensure_ascii=False, indent=2)
                
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Wyeksportowano {len(self.shortcuts)} skrótów do:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Nie udało się wyeksportować:\n{str(e)}")
    
    def save_data(self):
        """Zapisuje dane do pliku JSON używając DataManager"""
        self.data_manager.save_shortcuts(self.shortcuts)
    
    def load_data(self):
        """Ładuje dane z pliku JSON używając DataManager - DEPRECATED, używaj konstruktora"""
        # Metoda pozostawiona dla kompatybilności wstecznej
        # W nowej wersji dane są ładowane w __init__ przez data_manager
        pass
    
    def toggle_system(self):
        """Przełącza stan systemu skrótów"""
        if self.system_active:
            self.stop_system()
        else:
            self.start_system()
    
    def start_system(self):
        """Uruchamia system globalnych skrótów"""
        # Sprawdź czy są jakieś aktywne skróty
        active_shortcuts = [s for s in self.shortcuts if s.get('enabled', True)]
        
        if not active_shortcuts:
            QMessageBox.warning(
                self,
                "Brak aktywnych skrótów",
                "Nie ma żadnych włączonych skrótów do aktywacji!\n\n"
                "Dodaj skróty i upewnij się, że są włączone."
            )
            return
        
        # Uruchom (lub utwórz) listener
        if not self.hotkey_listener:
            self.hotkey_listener = HotkeyListener(self.get_active_shortcuts)
            self.hotkey_listener.hotkey_triggered.connect(self.on_hotkey_triggered)

        self.hotkey_listener.start()
        
        # Zaktualizuj UI
        self.system_active = True
        self.update_system_status_ui()
        
        QMessageBox.information(
            self,
            "System uruchomiony",
            f"System skrótów został uruchomiony!\n\n"
            f"Aktywnych skrótów: {len(active_shortcuts)}\n\n"
            f"Globalne skróty klawiszowe są teraz aktywne."
        )
    
    def stop_system(self):
        """Zatrzymuje system globalnych skrótów"""
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
                # Czekaj dłużej na zakończenie
                import time
                time.sleep(0.1)  # Krótkie oczekiwanie na zakończenie wątków
            except Exception as e:
                print(f"Błąd podczas zatrzymywania listenera: {e}")
        
        # Zaktualizuj UI
        self.system_active = False
        self.update_system_status_ui()
        
        self.emit_status("System skrótów zatrzymany", 3000)
    
    def update_system_status_ui(self):
        """Aktualizuje interfejs statusu systemu"""
        def t(key, **kwargs):
            return self.i18n.translate(key, **kwargs) if self.i18n else key
        
        if self.system_active:
            active_count = len([s for s in self.shortcuts if s.get('enabled', True)])
            self.system_status_label.setText(t("shortcuts.status_active", count=active_count))
            self.system_status_label.setProperty('class', config.get_style_class('status_active'))
            self.system_status_label.style().unpolish(self.system_status_label)
            self.system_status_label.style().polish(self.system_status_label)
            
            self.toggle_system_btn.setText(t("shortcuts.btn_stop_system"))
            self.toggle_system_btn.setProperty('class', config.get_style_class('btn_stop'))
            self.toggle_system_btn.style().unpolish(self.toggle_system_btn)
            self.toggle_system_btn.style().polish(self.toggle_system_btn)
        else:
            self.system_status_label.setText(t("shortcuts.status_inactive"))
            self.system_status_label.setProperty('class', config.get_style_class('status_inactive'))
            self.system_status_label.style().unpolish(self.system_status_label)
            self.system_status_label.style().polish(self.system_status_label)
            
            self.toggle_system_btn.setText(t("shortcuts.btn_start_system"))
            self.toggle_system_btn.setProperty('class', config.get_style_class('btn_start'))
            self.toggle_system_btn.style().unpolish(self.toggle_system_btn)
            self.toggle_system_btn.style().polish(self.toggle_system_btn)
    
    def get_active_shortcuts(self):
        """Zwraca listę aktywnych skrótów dla listenera"""
        return [s for s in self.shortcuts if s.get('enabled', True)]
    
    def display_template_menu(self, templates, position):
        """Wyświetla menu z szablonami lub skrótami przy kursorze (wywoływane z wątku głównego)"""
        # Sprawdź czy to są szablony tekstowe czy pozycje menu skrótów
        if templates and len(templates) > 0:
            first_item = templates[0]
            # Szablony mają 'content', pozycje menu mają 'type' i 'path'
            if 'content' in first_item:
                menu = TemplateContextMenu(templates, self)
            elif 'type' in first_item and 'path' in first_item:
                menu = ShortcutsContextMenu(templates, self)
            else:
                return  # Nieznany format
            
            menu.exec(position)
    
    def apply_theme(self):
        """Aplikuje aktualny motyw z ThemeManager"""
        if not self.theme_manager:
            return
        
        # ThemeManager automatycznie aplikuje style poprzez property classes
        # Tutaj możemy dodać dodatkową logikę jeśli potrzeba
        try:
            # Opcjonalnie: pobierz kolory motywu dla dynamicznych elementów
            colors = self.theme_manager.get_current_colors()
            # Możemy użyć colors do dynamicznych elementów jeśli potrzeba
        except:
            pass
    
    def update_ui_texts(self):
        """Aktualizuje wszystkie teksty UI po zmianie języka"""
        if not self.i18n:
            return
        
        # Helper function dla tłumaczeń
        def t(key, **kwargs):
            return self.i18n.translate(key, **kwargs) if self.i18n else key
        
        # Header
        self.header_label.setText(t("shortcuts.header"))
        
        # Status i przyciski systemu - wywołuje update_system_status_ui()
        self.update_system_status_ui()
        
        # Labels formularza
        self.label_name.setText(t("shortcuts.label_name"))
        self.label_shortcut_type.setText(t("shortcuts.label_shortcut_type"))
        self.label_shortcut.setText(t("shortcuts.label_shortcut"))
        self.label_action_type.setText(t("shortcuts.label_action_type"))
        self.label_action_value.setText(t("shortcuts.label_action_value"))
        
        # Placeholders
        self.name_input.setPlaceholderText(t("shortcuts.placeholder_name"))
        self.action_input.setPlaceholderText(t("shortcuts.placeholder_action"))
        
        # Przyciski formularza
        self.btn_browse.setText(t("shortcuts.btn_browse"))
        self.btn_record_clicks.setText(t("shortcuts.btn_record_clicks"))
        self.btn_test_clicks.setText(t("shortcuts.btn_test_sequence"))
        self.btn_test.setText(t("shortcuts.btn_test_action"))
        self.btn_add.setText(t("shortcuts.btn_add_shortcut"))
        self.btn_clear.setText(t("shortcuts.btn_clear_form"))
        
        # Nagłówki sekcji
        self.templates_header.setText(t("shortcuts.templates_header"))
        self.shortcuts_menu_header.setText(t("shortcuts.shortcuts_menu_header"))
        
        # Przyciski szablonów i menu
        self.btn_add_template.setText(t("shortcuts.btn_add_template"))
        self.btn_edit_template.setText(t("shortcuts.btn_edit"))
        self.btn_delete_template.setText(t("shortcuts.btn_delete"))
        self.btn_add_menu_item.setText(t("shortcuts.btn_add_menu_item"))
        self.btn_edit_menu_item.setText(t("shortcuts.btn_edit"))
        self.btn_delete_menu_item.setText(t("shortcuts.btn_delete"))
        
        # Przyciski toolbar
        self.btn_refresh.setText(t("shortcuts.btn_refresh"))
        self.btn_edit.setText(t("shortcuts.btn_edit"))
        self.btn_delete.setText(t("shortcuts.btn_delete"))
        self.btn_import.setText(t("shortcuts.btn_import"))
        self.btn_export.setText(t("shortcuts.btn_export"))
        
        # Checkbox
        self.enabled_checkbox.setText(t("shortcuts.checkbox_enabled"))
        
        # Count label
        if hasattr(self, 'count_label'):
            count = len(self.shortcuts)
            # I18nManager nie obsługuje parametrów - używamy formatowania
            count_text = t("shortcuts.shortcuts_count").replace("{count}", str(count))
            self.count_label.setText(count_text)
        
        # ComboBox items - trzeba je przeładować
        self.shortcut_type_combo.clear()
        self.shortcut_type_combo.addItems([
            t("shortcuts.type_key_combo"),
            t("shortcuts.type_hold_key"),
            t("shortcuts.type_magic_phrase")
        ])
        
        self.action_type_combo.clear()
        self.action_type_combo.addItems([
            t("shortcuts.action_paste_text"),
            t("shortcuts.action_template_menu"),
            t("shortcuts.action_shortcuts_menu"),
            t("shortcuts.action_open_app"),
            t("shortcuts.action_open_file"),
            t("shortcuts.action_powershell"),
            t("shortcuts.action_cmd"),
            t("shortcuts.action_click_sequence")
        ])
    
    def emit_status(self, message: str, timeout: int = 3000):
        """
        Emituje sygnał ze statusem (zamiast używania statusBar)
        
        Args:
            message: Komunikat do wyświetlenia
            timeout: Czas wyświetlania w ms
        """
        self.status_message.emit(message, timeout)
        print(f"[Status] {message}")  # Backup do konsoli
    
    def closeEvent(self, a0):
        """Obsługa zamykania widgetu - zatrzymaj system"""
        # KRYTYCZNE: Zatrzymaj system PRZED zamknięciem
        if self.system_active:
            self.stop_system()
        
        # Upewnij się że listener został zatrzymany
        if self.hotkey_listener:
            try:
                self.hotkey_listener.stop()
            except:
                pass
            self.hotkey_listener = None
        
        # Zapisz dane
        self.save_data()
        
        # Wywołaj oryginalny closeEvent
        super().closeEvent(a0)


def main():
    """Funkcja główna - uruchamia aplikację"""
    app = QApplication(sys.argv)
    app.setApplicationName("Moduł Shortcuts")
    app.setOrganizationName("Pro Ka Po Comer")
    window = ShortcutsModule()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
