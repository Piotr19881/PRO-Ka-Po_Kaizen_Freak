"""
Moduł Shortcuts (FastKey) - Zarządzanie globalnymi skrótami klawiszowymi

Funkcjonalność:
- Tworzenie niestandardowych skrótów klawiszowych
- Uruchamianie aplikacji, skryptów, komend
- Lista wszystkich utworzonych skrótów
- Aktywacja/deaktywacja skrótów
- Import/Export konfiguracji
- Magiczne frazy (trigger phrases)
- Sekwencje kliknięć myszką

Autor: PRO-Ka-Po Commercial Application
Data: 2025-11-12
Wersja: 2.0.0 - Zrefaktoryzowany jako QWidget z integracją i18n i ThemeManager
"""

from .shortcuts_module import ShortcutsModule

# Alias dla kompatybilności
ShortcutsWidget = ShortcutsModule

__all__ = ['ShortcutsModule', 'ShortcutsWidget']
__version__ = '2.0.0'
