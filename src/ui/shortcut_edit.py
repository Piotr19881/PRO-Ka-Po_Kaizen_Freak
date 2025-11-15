"""
Shortcut Editor Widget - Widget do przechwytywania skrótów klawiszowych
"""
from PyQt6.QtWidgets import QLineEdit
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent, QKeySequence
from loguru import logger


class ShortcutEdit(QLineEdit):
    """Widget do przechwytywania i edycji skrótów klawiszowych"""
    
    shortcut_changed = pyqtSignal(str)  # Emitowany gdy skrót się zmienia
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setPlaceholderText("Kliknij i naciśnij kombinację klawiszy...")
        self.setReadOnly(True)  # Nie pozwalaj na zwykłe wpisywanie
        self._recording = False
        
    def keyPressEvent(self, event: QKeyEvent):
        """Przechwytuj naciśnięcia klawiszy i konwertuj na skrót"""
        # Ignoruj samo-modyfikatory (Shift, Ctrl, Alt, Meta)
        if event.key() in (
            Qt.Key.Key_Shift,
            Qt.Key.Key_Control,
            Qt.Key.Key_Alt,
            Qt.Key.Key_Meta,
            Qt.Key.Key_AltGr
        ):
            return
        
        # Pobierz modyfikatory
        modifiers = event.modifiers()
        key = event.key()
        
        # Zbuduj sekwencję klawiszy
        key_combo = 0
        
        if modifiers & Qt.KeyboardModifier.ControlModifier:
            key_combo |= Qt.KeyboardModifier.ControlModifier.value
        if modifiers & Qt.KeyboardModifier.AltModifier:
            key_combo |= Qt.KeyboardModifier.AltModifier.value
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            key_combo |= Qt.KeyboardModifier.ShiftModifier.value
        if modifiers & Qt.KeyboardModifier.MetaModifier:
            key_combo |= Qt.KeyboardModifier.MetaModifier.value
        
        key_combo |= key
        
        # Utwórz QKeySequence
        sequence = QKeySequence(key_combo)
        shortcut_text = sequence.toString()
        
        # Specjalne klawisze funkcyjne (F1-F12) mogą być bez modyfikatorów
        is_function_key = Qt.Key.Key_F1 <= key <= Qt.Key.Key_F12
        
        # Wymagaj modyfikatora dla zwykłych klawiszy (nie dla F1-F12, Esc, etc.)
        if not is_function_key and not (modifiers & (
            Qt.KeyboardModifier.ControlModifier |
            Qt.KeyboardModifier.AltModifier |
            Qt.KeyboardModifier.MetaModifier
        )):
            # Pojedyncza litera/cyfra bez modyfikatora - ignoruj
            self.setText("")
            self.setPlaceholderText("Użyj Ctrl/Alt/Shift + klawisz lub F1-F12")
            return
        
        # Ustaw tekst i emituj sygnał
        self.setText(shortcut_text)
        self.shortcut_changed.emit(shortcut_text)
        logger.debug(f"Shortcut recorded: {shortcut_text}")
        
    def focusInEvent(self, event):
        """Gdy pole dostaje focus - rozpocznij nagrywanie"""
        super().focusInEvent(event)
        self._recording = True
        self.setStyleSheet("background-color: #FFFACD;")  # Żółty bg
        
    def focusOutEvent(self, event):
        """Gdy pole traci focus - zatrzymaj nagrywanie"""
        super().focusOutEvent(event)
        self._recording = False
        self.setStyleSheet("")
        
    def mousePressEvent(self, event):
        """Kliknięcie - wyczyść obecny skrót i rozpocznij nagrywanie"""
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton:
            self.clear()
            self.setFocus()
            self.setPlaceholderText("Naciśnij kombinację klawiszy...")
