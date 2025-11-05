"""
Test integracji TextInputDialog z Theme Manager i i18n

Sprawdza:
1. Integrację z Theme Manager (dynamiczne kolory)
2. Integrację z i18n (tłumaczenia PL/EN/DE)
3. Podstawową funkcjonalność dialogu
"""

import sys
import os
from pathlib import Path

# Dodaj ścieżkę do src
project_root = Path(__file__).parent / "PRO-Ka-Po_Kaizen_Freak"
sys.path.insert(0, str(project_root))

# Ustaw zmienną środowiskową dla bazy danych
db_path = project_root / "src" / "database" / "tasks.db"
os.environ["DB_PATH"] = str(db_path)

from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QLabel
from src.ui.ui_task_simple_dialogs import TextInputDialog
from src.utils.i18n_manager import get_i18n, t
from src.utils.theme_manager import get_theme_manager

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test TextInputDialog - Integracja z Theme i i18n")
        self.setGeometry(100, 100, 600, 400)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        
        # Info
        info = QLabel("Test integracji TextInputDialog z Theme Manager i i18n")
        info.setStyleSheet("font-weight: bold; font-size: 14px; margin: 10px;")
        layout.addWidget(info)
        
        # Sprawdzenie Theme Manager
        theme_manager = get_theme_manager()
        colors = theme_manager.get_current_colors()
        theme_info = QLabel(f"✅ Theme Manager zintegrowany\n"
                           f"   Bieżący motyw: {theme_manager.current_layout}\n"
                           f"   Kolory: bg_main={colors.get('bg_main', 'N/A')}")
        theme_info.setStyleSheet("margin: 10px; padding: 10px; background: #2a2a2a; border-radius: 4px;")
        layout.addWidget(theme_info)
        
        # Sprawdzenie i18n
        i18n = get_i18n()
        current_lang = i18n.current_language if hasattr(i18n, 'current_language') else 'pl'
        i18n_test = t("tasks.text_dialog.title", "Fallback")
        i18n_info = QLabel(f"✅ i18n zintegrowane\n"
                          f"   Bieżący język: {current_lang}\n"
                          f"   Test klucza: '{i18n_test}'")
        i18n_info.setStyleSheet("margin: 10px; padding: 10px; background: #2a2a2a; border-radius: 4px;")
        layout.addWidget(i18n_info)
        
        # Przyciski testowe
        btn1 = QPushButton("Test 1: Dialog z pustą wartością")
        btn1.clicked.connect(self.test_empty_dialog)
        layout.addWidget(btn1)
        
        btn2 = QPushButton("Test 2: Dialog z wartością początkową")
        btn2.clicked.connect(self.test_with_initial_value)
        layout.addWidget(btn2)
        
        btn3 = QPushButton("Test 3: Dialog z własnym tytułem")
        btn3.clicked.connect(self.test_custom_title)
        layout.addWidget(btn3)
        
        # Wynik
        self.result_label = QLabel("Wynik pojawi się tutaj...")
        self.result_label.setStyleSheet("margin: 10px; padding: 10px; background: #2a2a2a; border-radius: 4px; min-height: 60px;")
        layout.addWidget(self.result_label)
        
        layout.addStretch()
        
    def test_empty_dialog(self):
        accepted, text = TextInputDialog.prompt(
            parent=self,
            initial_text="",
            title=None  # Użyje domyślnego tłumaczenia
        )
        self.result_label.setText(
            f"✅ Test 1 - Dialog z pustą wartością\n"
            f"   Zaakceptowano: {accepted}\n"
            f"   Wprowadzony tekst: '{text}'\n"
            f"   Długość: {len(text)} znaków"
        )
    
    def test_with_initial_value(self):
        # Test z wieloliniowym tekstem
        initial = """Wartość testowa XYZ
Linia druga
Linia trzecia z dłuższym tekstem
Możemy mieć wiele linii tekstu w tym polu!"""
        
        accepted, text = TextInputDialog.prompt(
            parent=self,
            initial_text=initial,
            title=t("tasks.text_dialog.title_for", "Edytuj Tag")
        )
        lines = text.split('\n')
        self.result_label.setText(
            f"✅ Test 2 - Dialog z wartością początkową (wieloliniowy)\n"
            f"   Zaakceptowano: {accepted}\n"
            f"   Liczba linii: {len(lines)}\n"
            f"   Długość całkowita: {len(text)} znaków\n"
            f"   Pierwsze 50 znaków: '{text[:50]}...'"
        )
    
    def test_custom_title(self):
        accepted, text = TextInputDialog.prompt(
            parent=self,
            initial_text="",
            title="Własny tytuł dialogu - Test integracji"
        )
        self.result_label.setText(
            f"✅ Test 3 - Dialog z własnym tytułem\n"
            f"   Zaakceptowano: {accepted}\n"
            f"   Wprowadzony tekst: '{text}'\n"
            f"   Długość: {len(text)} znaków"
        )

def main():
    print("\n" + "="*60)
    print("TEST INTEGRACJI TextInputDialog")
    print("="*60)
    
    app = QApplication(sys.argv)
    
    # Test 1: Theme Manager
    print("\n1. Sprawdzanie integracji z Theme Manager...")
    theme_manager = get_theme_manager()
    colors = theme_manager.get_current_colors()
    print(f"   ✅ Theme Manager dostępny")
    print(f"   ✅ Kolory pobrane: {len(colors)} kluczy")
    print(f"   ✅ bg_main: {colors.get('bg_main', 'N/A')}")
    print(f"   ✅ accent_primary: {colors.get('accent_primary', 'N/A')}")
    
    # Test 2: i18n
    print("\n2. Sprawdzanie integracji z i18n...")
    i18n = get_i18n()
    
    # Test wszystkich kluczy
    keys_to_test = [
        "tasks.text_dialog.title",
        "tasks.text_dialog.title_for",
        "tasks.text_dialog.prompt",
        "tasks.text_dialog.placeholder",
        "tasks.text_dialog.ok",
        "tasks.text_dialog.cancel"
    ]
    
    print("   Testowanie kluczy tłumaczeń:")
    for key in keys_to_test:
        value = t(key, "BRAK")
        status = "✅" if value != "BRAK" else "❌"
        print(f"   {status} {key}: '{value}'")
    
    # Test 3: Uruchom okno testowe
    print("\n3. Uruchamianie okna testowego...")
    print("   ✅ Możesz teraz przetestować dialog interaktywnie")
    print("\n" + "="*60)
    
    window = TestWindow()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
