"""
Global Shortcuts Manager - Obsługa globalnych skrótów klawiszowych dla modułów
"""
from loguru import logger
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QKeySequence, QShortcut
from PyQt6.QtCore import Qt, QObject, pyqtSignal


class GlobalShortcutsManager(QObject):
    """Manager globalnych skrótów klawiszowych dla modułów aplikacji"""
    
    # Signal emitowany gdy skrót zostanie użyty
    shortcut_activated = pyqtSignal(str)  # module_id
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.shortcuts = {}  # {module_id: QShortcut}
        logger.info("GlobalShortcutsManager initialized")
    
    def register_shortcut(self, module_id: str, key_sequence: str):
        """
        Rejestruj skrót klawiszowy dla modułu
        
        Args:
            module_id: ID modułu (np. 'tasks', 'pomodoro')
            key_sequence: Sekwencja klawiszy (np. 'Ctrl+Alt+T', 'F1')
        """
        if not key_sequence or key_sequence.strip() == "":
            logger.debug(f"Empty shortcut for module {module_id}, skipping")
            return
        
        # Usuń poprzedni skrót jeśli istnieje
        self.unregister_shortcut(module_id)
        
        try:
            # Utwórz QShortcut
            shortcut = QShortcut(QKeySequence(key_sequence), self.main_window)
            shortcut.activated.connect(lambda: self._on_shortcut_activated(module_id))
            
            # Zapisz skrót
            self.shortcuts[module_id] = shortcut
            
            logger.info(f"Registered global shortcut '{key_sequence}' for module '{module_id}'")
            
        except Exception as e:
            logger.error(f"Failed to register shortcut '{key_sequence}' for module '{module_id}': {e}")
    
    def unregister_shortcut(self, module_id: str):
        """Wyrejestruj skrót dla modułu"""
        if module_id in self.shortcuts:
            shortcut = self.shortcuts[module_id]
            shortcut.activated.disconnect()
            shortcut.setParent(None)
            del self.shortcuts[module_id]
            logger.debug(f"Unregistered shortcut for module '{module_id}'")
    
    def unregister_all(self):
        """Wyrejestruj wszystkie skróty"""
        for module_id in list(self.shortcuts.keys()):
            self.unregister_shortcut(module_id)
        logger.info("All shortcuts unregistered")
    
    def load_shortcuts_from_config(self, buttons_config: list):
        """
        Załaduj skróty klawiszowe z konfiguracji przycisków
        
        Args:
            buttons_config: Lista konfiguracji przycisków z user_settings
        """
        # Wyczyść poprzednie skróty
        self.unregister_all()
        
        # Załaduj nowe skróty
        for button in buttons_config:
            module_id = button.get('id')
            shortcut = button.get('shortcut', '')
            
            if module_id and shortcut:
                self.register_shortcut(module_id, shortcut)
        
        logger.info(f"Loaded {len(self.shortcuts)} shortcuts from config")
    
    def _on_shortcut_activated(self, module_id: str):
        """
        Obsługa aktywacji skrótu
        
        Wywołuje okno aplikacji i przełącza na moduł
        """
        logger.info(f"Shortcut activated for module: {module_id}")
        
        # Sprawdź czy okno jest zminimalizowane lub ukryte
        if self.main_window.isMinimized() or self.main_window.isHidden():
            # Przywróć okno
            self.main_window.show()
            self.main_window.activateWindow()
            if self.main_window.isMinimized():
                self.main_window.showNormal()
            logger.debug("Window restored from minimized/hidden state")
        else:
            # Okno jest widoczne, ale może być w tle - przenieś na wierzch
            self.main_window.raise_()
            self.main_window.activateWindow()
            logger.debug("Window brought to front")
        
        # Emituj signal aby przełączyć widok
        self.shortcut_activated.emit(module_id)
    
    def get_shortcut_for_module(self, module_id: str) -> str:
        """Pobierz sekwencję klawiszy dla modułu"""
        if module_id in self.shortcuts:
            return self.shortcuts[module_id].key().toString()
        return ""
    
    def validate_shortcut(self, key_sequence: str) -> bool:
        """
        Sprawdź czy sekwencja klawiszy jest poprawna
        
        Returns:
            True jeśli sekwencja jest poprawna, False w przeciwnym razie
        """
        if not key_sequence or key_sequence.strip() == "":
            return True  # Puste jest OK (brak skrótu)
        
        try:
            seq = QKeySequence(key_sequence)
            return not seq.isEmpty()
        except:
            return False
    
    def is_shortcut_used(self, key_sequence: str, exclude_module: str = None) -> str | None:
        """
        Sprawdź czy skrót jest już używany przez inny moduł
        
        Args:
            key_sequence: Sekwencja do sprawdzenia
            exclude_module: ID modułu do pominięcia (np. przy edycji)
        
        Returns:
            ID modułu który używa tego skrótu, lub None jeśli wolny
        """
        if not key_sequence or key_sequence.strip() == "":
            return None
        
        for module_id, shortcut in self.shortcuts.items():
            if exclude_module and module_id == exclude_module:
                continue
            
            if shortcut.key().toString() == key_sequence:
                return module_id
        
        return None


# Singleton instance
_shortcuts_manager_instance = None


def get_shortcuts_manager(main_window=None):
    """Pobierz singleton instance GlobalShortcutsManager"""
    global _shortcuts_manager_instance
    
    if _shortcuts_manager_instance is None:
        if main_window is None:
            raise ValueError("main_window required for first initialization")
        _shortcuts_manager_instance = GlobalShortcutsManager(main_window)
    
    return _shortcuts_manager_instance


def reset_shortcuts_manager():
    """Reset singleton instance (do testów)"""
    global _shortcuts_manager_instance
    if _shortcuts_manager_instance:
        _shortcuts_manager_instance.unregister_all()
    _shortcuts_manager_instance = None
