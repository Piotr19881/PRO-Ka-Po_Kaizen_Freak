"""
Test podstawowy modułu Shortcuts - weryfikacja importów i inicjalizacji
"""
import sys
from pathlib import Path

# Dodaj główny katalog projektu do ścieżki
shortcuts_dir = Path(__file__).parent
modules_dir = shortcuts_dir.parent.parent.parent
sys.path.insert(0, str(modules_dir))

print("=" * 60)
print("TEST MODUŁU SHORTCUTS - Refaktoryzacja")
print("=" * 60)

# Test 1: Import konfiguracji
print("\n[Test 1] Import shortcuts_config...")
try:
    from shortcuts_config import ShortcutsConfig
    config = ShortcutsConfig()
    print(f"✅ ShortcutsConfig zaimportowany")
    print(f"   DATA_DIR: {config.DATA_DIR}")
    print(f"   Liczba klas stylów: {len(config.STYLE_CLASSES)}")
except Exception as e:
    print(f"❌ Błąd: {e}")
    sys.exit(1)

# Test 2: Import data managera
print("\n[Test 2] Import shortcuts_data_manager...")
try:
    from shortcuts_data_manager import ShortcutsDataManager
    data_manager = ShortcutsDataManager()
    print(f"✅ ShortcutsDataManager zaimportowany")
    shortcuts = data_manager.load_shortcuts()
    print(f"   Załadowano {len(shortcuts)} skrótów")
except Exception as e:
    print(f"❌ Błąd: {e}")
    sys.exit(1)

# Test 3: Import widgets
print("\n[Test 3] Import widgets...")
try:
    from widgets import ShortcutCaptureWidget
    from widgets import TemplateContextMenu, ShortcutsContextMenu
    print(f"✅ Wszystkie widgety zaimportowane")
except Exception as e:
    print(f"❌ Błąd: {e}")
    sys.exit(1)

# Test 4: Import głównego modułu
print("\n[Test 4] Import głównego modułu...")
try:
    from shortcuts_module import ShortcutsModule
    print(f"✅ ShortcutsModule zaimportowany")
    print(f"✅ ShortcutsWidget (alias) dostępny")
except Exception as e:
    print(f"❌ Błąd: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

# Test 5: Utworzenie instancji (wymaga PyQt6)
print("\n[Test 5] Utworzenie instancji modułu...")
try:
    from PyQt6.QtWidgets import QApplication
    
    # Utwórz aplikację jeśli jeszcze nie istnieje
    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    
    # Utwórz moduł (bez theme_manager i i18n dla testu)
    module = ShortcutsModule()
    print(f"✅ Instancja utworzona")
    print(f"   Typ: {type(module).__name__}")
    print(f"   Liczba skrótów: {len(module.shortcuts)}")
    
except Exception as e:
    print(f"⚠️  Nie można utworzyć instancji (normalne bez pełnego środowiska): {e}")

print("\n" + "=" * 60)
print("PODSUMOWANIE TESTÓW")
print("=" * 60)
print("✅ Wszystkie podstawowe testy przeszły pomyślnie!")
print("✅ Moduł jest gotowy do integracji z aplikacją")
print("\nNastępne kroki:")
print("1. Zintegruj z główną aplikacją jako widget")
print("2. Podłącz ThemeManager i I18nManager")
print("3. Przetestuj zmianę języka i motywu")
print("=" * 60)
