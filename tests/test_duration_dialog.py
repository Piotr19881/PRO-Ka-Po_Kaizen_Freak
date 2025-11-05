"""
Test Duration Input Dialog
"""
import sys
import os

# Dodaj ścieżkę do katalogu głównego projektu
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'PRO-Ka-Po_Kaizen_Freak'))

from PyQt6.QtWidgets import QApplication, QPushButton, QVBoxLayout, QWidget, QLabel
from src.ui.ui_task_simple_dialogs import DurationInputDialog

class TestWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test DurationInputDialog")
        layout = QVBoxLayout(self)
        
        self.result_label = QLabel("Naciśnij przycisk aby otworzyć dialog")
        layout.addWidget(self.result_label)
        
        button = QPushButton("Otwórz Dialog Czasu Trwania")
        button.clicked.connect(self.open_dialog)
        layout.addWidget(button)
        
        self.resize(400, 150)
    
    def open_dialog(self):
        accepted, minutes = DurationInputDialog.prompt(
            parent=self,
            initial_minutes=30,
            title="Testowy dialog czasu"
        )
        
        if accepted:
            self.result_label.setText(f"✓ Zaakceptowano: {minutes} minut")
        else:
            self.result_label.setText("✗ Anulowano")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
