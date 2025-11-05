import sys
from pathlib import Path

# Dodaj ścieżkę do src
project_root = Path(__file__).parent / "PRO-Ka-Po_Kaizen_Freak"
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import QApplication
from src.ui.ui_task_simple_dialogs import TextInputDialog

def test_text_dialog():
    app = QApplication(sys.argv)
    
    # Test 1: Dialog bez wartości początkowej
    print("Test 1: Pusty dialog")
    accepted, text = TextInputDialog.prompt(
        initial_text="",
        title="Test - wprowadź tekst"
    )
    print(f"  Zaakceptowano: {accepted}")
    print(f"  Wprowadzony tekst: '{text}'")
    
    # Test 2: Dialog z wartością początkową
    print("\nTest 2: Dialog z wartością początkową")
    accepted, text = TextInputDialog.prompt(
        initial_text="Wartość testowa",
        title="Edytuj Tag"
    )
    print(f"  Zaakceptowano: {accepted}")
    print(f"  Wprowadzony tekst: '{text}'")

if __name__ == "__main__":
    test_text_dialog()
