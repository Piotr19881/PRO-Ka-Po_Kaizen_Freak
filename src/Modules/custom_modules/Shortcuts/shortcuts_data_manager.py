"""
Shortcuts Data Manager
Zarządzanie danymi skrótów klawiszowych
"""
import json
from typing import List, Dict, Any, Optional
from pathlib import Path
from datetime import datetime

try:
    from loguru import logger
except ImportError:
    # Fallback dla standalone execution
    import logging
    logger = logging.getLogger(__name__)

try:
    from .shortcuts_config import ShortcutsConfig
except ImportError:
    # Standalone execution
    from shortcuts_config import ShortcutsConfig


class ShortcutsDataManager:
    """
    Klasa zarządzająca danymi skrótów klawiszowych
    
    Odpowiedzialności:
    - Ładowanie/zapisywanie skrótów z/do pliku JSON
    - Walidacja danych
    - Import/Export konfiguracji
    - Historia wykonanych skrótów (opcjonalnie)
    """
    
    def __init__(self):
        """Inicjalizacja menedżera danych"""
        self.data_file = ShortcutsConfig.get_data_file_path()
        self.history_file = ShortcutsConfig.get_history_file_path()
        self._shortcuts_cache: Optional[List[Dict[str, Any]]] = None
    
    def load_shortcuts(self) -> List[Dict[str, Any]]:
        """
        Ładuje skróty z pliku
        
        Returns:
            Lista słowników z danymi skrótów
        """
        # Sprawdź cache
        if self._shortcuts_cache is not None:
            logger.debug("Loading shortcuts from cache")
            return self._shortcuts_cache.copy()
        
        # Załaduj z pliku
        if not self.data_file.exists():
            logger.info("Shortcuts data file not found, creating new")
            return []
        
        try:
            with open(self.data_file, 'r', encoding='utf-8') as f:
                shortcuts = json.load(f)
                
                # Walidacja podstawowa
                if not isinstance(shortcuts, list):
                    logger.error("Invalid shortcuts data format (not a list)")
                    return []
                
                # Walidacja każdego skrótu
                validated_shortcuts = []
                for shortcut in shortcuts:
                    if self._validate_shortcut(shortcut):
                        validated_shortcuts.append(shortcut)
                    else:
                        logger.warning(f"Invalid shortcut skipped: {shortcut.get('name', 'unknown')}")
                
                self._shortcuts_cache = validated_shortcuts.copy()
                logger.info(f"Loaded {len(validated_shortcuts)} shortcuts")
                return validated_shortcuts
        
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error loading shortcuts: {e}")
            return []
        except Exception as e:
            logger.error(f"Error loading shortcuts: {e}")
            return []
    
    def save_shortcuts(self, shortcuts: List[Dict[str, Any]]) -> bool:
        """
        Zapisuje skróty do pliku
        
        Args:
            shortcuts: Lista słowników z danymi skrótów
            
        Returns:
            True jeśli sukces, False w przypadku błędu
        """
        try:
            # Walidacja przed zapisem
            validated_shortcuts = []
            for shortcut in shortcuts:
                if self._validate_shortcut(shortcut):
                    validated_shortcuts.append(shortcut)
                else:
                    logger.warning(f"Invalid shortcut not saved: {shortcut.get('name', 'unknown')}")
            
            # Zapisz do pliku
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(validated_shortcuts, f, ensure_ascii=False, indent=2)
            
            # Aktualizuj cache
            self._shortcuts_cache = validated_shortcuts.copy()
            
            logger.info(f"Saved {len(validated_shortcuts)} shortcuts")
            return True
        
        except Exception as e:
            logger.error(f"Error saving shortcuts: {e}")
            return False
    
    def _validate_shortcut(self, shortcut: Dict[str, Any]) -> bool:
        """
        Waliduje pojedynczy skrót
        
        Args:
            shortcut: Słownik z danymi skrótu
            
        Returns:
            True jeśli skrót jest poprawny
        """
        if not isinstance(shortcut, dict):
            return False
        
        # Wymagane pola
        required_fields = ['name', 'action_type']
        for field in required_fields:
            if field not in shortcut:
                logger.warning(f"Shortcut missing required field: {field}")
                return False
        
        # Opcjonalne pola z wartościami domyślnymi
        shortcut.setdefault('enabled', True)
        shortcut.setdefault('description', '')
        shortcut.setdefault('shortcut_type', 'Kombinacja klawiszy')
        
        return True
    
    def add_shortcut(self, shortcut: Dict[str, Any]) -> bool:
        """
        Dodaje nowy skrót
        
        Args:
            shortcut: Słownik z danymi skrótu
            
        Returns:
            True jeśli sukces
        """
        if not self._validate_shortcut(shortcut):
            logger.error("Cannot add invalid shortcut")
            return False
        
        shortcuts = self.load_shortcuts()
        
        # Sprawdź czy nazwa już istnieje
        existing_names = [s.get('name') for s in shortcuts]
        if shortcut.get('name') in existing_names:
            logger.warning(f"Shortcut with name '{shortcut['name']}' already exists")
            return False
        
        shortcuts.append(shortcut)
        return self.save_shortcuts(shortcuts)
    
    def update_shortcut(self, index: int, updated_shortcut: Dict[str, Any]) -> bool:
        """
        Aktualizuje istniejący skrót
        
        Args:
            index: Indeks skrótu do zaktualizowania
            updated_shortcut: Zaktualizowane dane skrótu
            
        Returns:
            True jeśli sukces
        """
        if not self._validate_shortcut(updated_shortcut):
            logger.error("Cannot update with invalid shortcut data")
            return False
        
        shortcuts = self.load_shortcuts()
        
        if index < 0 or index >= len(shortcuts):
            logger.error(f"Invalid shortcut index: {index}")
            return False
        
        shortcuts[index] = updated_shortcut
        return self.save_shortcuts(shortcuts)
    
    def delete_shortcut(self, index: int) -> bool:
        """
        Usuwa skrót
        
        Args:
            index: Indeks skrótu do usunięcia
            
        Returns:
            True jeśli sukces
        """
        shortcuts = self.load_shortcuts()
        
        if index < 0 or index >= len(shortcuts):
            logger.error(f"Invalid shortcut index: {index}")
            return False
        
        deleted_name = shortcuts[index].get('name', 'unknown')
        shortcuts.pop(index)
        
        success = self.save_shortcuts(shortcuts)
        if success:
            logger.info(f"Deleted shortcut: {deleted_name}")
        
        return success
    
    def import_shortcuts(self, file_path: Path) -> Optional[List[Dict[str, Any]]]:
        """
        Importuje skróty z pliku
        
        Args:
            file_path: Ścieżka do pliku JSON
            
        Returns:
            Lista zaimportowanych skrótów lub None w przypadku błędu
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            if not isinstance(imported_data, list):
                logger.error("Imported file is not a list of shortcuts")
                return None
            
            # Walidacja i filtracja
            valid_shortcuts = []
            for shortcut in imported_data:
                if self._validate_shortcut(shortcut):
                    valid_shortcuts.append(shortcut)
            
            logger.info(f"Imported {len(valid_shortcuts)} shortcuts from {file_path}")
            return valid_shortcuts
        
        except Exception as e:
            logger.error(f"Error importing shortcuts from {file_path}: {e}")
            return None
    
    def export_shortcuts(self, file_path: Path, shortcuts: Optional[List[Dict[str, Any]]] = None) -> bool:
        """
        Eksportuje skróty do pliku
        
        Args:
            file_path: Ścieżka docelowa
            shortcuts: Lista skrótów do eksportu (None = wszystkie)
            
        Returns:
            True jeśli sukces
        """
        try:
            if shortcuts is None:
                shortcuts = self.load_shortcuts()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(shortcuts, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Exported {len(shortcuts)} shortcuts to {file_path}")
            return True
        
        except Exception as e:
            logger.error(f"Error exporting shortcuts to {file_path}: {e}")
            return False
    
    def log_execution(self, shortcut_name: str, success: bool, message: str = "") -> None:
        """
        Loguje wykonanie skrótu (opcjonalnie do pliku historii)
        
        Args:
            shortcut_name: Nazwa skrótu
            success: Czy wykonanie powiodło się
            message: Dodatkowy komunikat
        """
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'shortcut_name': shortcut_name,
            'success': success,
            'message': message
        }
        
        # Log do konsoli/logów
        if success:
            logger.info(f"Shortcut executed: {shortcut_name}")
        else:
            logger.error(f"Shortcut failed: {shortcut_name} - {message}")
        
        # Opcjonalnie: zapis do pliku historii
        # (implementacja zależna od wymagań)
    
    def clear_cache(self) -> None:
        """Czyści cache skrótów"""
        self._shortcuts_cache = None
        logger.debug("Shortcuts cache cleared")
    
    def get_active_shortcuts(self) -> List[Dict[str, Any]]:
        """
        Zwraca listę aktywnych (enabled=True) skrótów
        
        Returns:
            Lista aktywnych skrótów
        """
        shortcuts = self.load_shortcuts()
        return [s for s in shortcuts if s.get('enabled', True)]
    
    def get_shortcut_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Znajduje skrót po nazwie
        
        Args:
            name: Nazwa skrótu
            
        Returns:
            Słownik ze skrótem lub None jeśli nie znaleziono
        """
        shortcuts = self.load_shortcuts()
        for shortcut in shortcuts:
            if shortcut.get('name') == name:
                return shortcut
        return None
