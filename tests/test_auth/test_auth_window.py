"""
Test Auth Window - Test okna autoryzacji
Uruchamia okno logowania/rejestracji
"""
import sys
import os

# Dodaj ścieżkę do modułu src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from PyQt6.QtWidgets import QApplication
from src.ui.auth_window import AuthWindow
from src.utils.theme_manager import get_theme_manager

def main():
    """Uruchom okno autoryzacji"""
    app = QApplication(sys.argv)
    
    # Zastosuj motyw
    theme_manager = get_theme_manager()
    theme_manager.apply_layout(1)
    
    # Utwórz i pokaż okno
    window = AuthWindow()
    
    # Callback po zalogowaniu
    def on_login_success(user_data):
        print(f"\n{'='*60}")
        print(f"✅ LOGOWANIE ZAKOŃCZONE SUKCESEM!")
        print(f"{'='*60}")
        print(f"Imię: {user_data.get('name', 'Brak')}")
        print(f"Email: {user_data.get('email', 'Brak')}")
        print(f"Język: {user_data.get('language', 'Brak')}")
        print(f"Strefa czasowa: {user_data.get('timezone', 'Brak')}")
        print(f"{'='*60}")
        print("\n✅ Tokeny zostały zapisane!")
        print("\nOkno autoryzacji zostanie zamknięte za 3 sekundy...")
        print("W prawdziwej aplikacji teraz otworzyłoby się główne okno.\n")
        
        # Zamknij okno po 3 sekundach
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(3000, window.close)
    
    window.login_successful.connect(on_login_success)
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
