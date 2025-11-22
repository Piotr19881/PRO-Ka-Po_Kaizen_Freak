"""
TestBox - Widok testowy do uruchamiania kodu Python jako moduł w aplikacji

Ten moduł pozwala na testowanie kodu Python bezpośrednio w interfejsie aplikacji
z możliwością powrotu do edytora.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit, QLabel,
    QFileDialog, QMessageBox
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from loguru import logger
import sys
from io import StringIO
import traceback


class TestBoxView(QWidget):
    """Widok testowy do uruchamiania kodu Python"""
    
    # Sygnał powrotu do edytora
    return_to_editor = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.code_to_run = ""
        
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # === PASEK GÓRNY Z PRZYCISKIEM POWROTU ===
        top_bar = QHBoxLayout()
        
        # Przycisk powrotu
        self.btn_return = QPushButton("⬅ Wróć do edytora")
        self.btn_return.setObjectName("btnPrimary")
        self.btn_return.setFixedHeight(40)
        self.btn_return.setMinimumWidth(150)
        self.btn_return.setStyleSheet("""
            QPushButton {
                background-color: #2196F3;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #1976D2;
            }
            QPushButton:pressed {
                background-color: #0D47A1;
            }
        """)
        self.btn_return.clicked.connect(self._on_return_clicked)
        top_bar.addWidget(self.btn_return)
        
        # Tytuł
        self.title_label = QLabel("🧪 Widok testowy modułu")
        self.title_label.setObjectName("sectionHeader")
        font = self.title_label.font()
        font.setPointSize(12)
        font.setBold(True)
        self.title_label.setFont(font)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        top_bar.addWidget(self.title_label, 1)
        
        # Przycisk zapisz jako moduł
        self.btn_save_module = QPushButton("💾 Zapisz jako moduł")
        self.btn_save_module.setObjectName("btnSuccess")
        self.btn_save_module.setFixedHeight(40)
        self.btn_save_module.setMinimumWidth(150)
        self.btn_save_module.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #218838;
            }
            QPushButton:pressed {
                background-color: #1e7e34;
            }
        """)
        self.btn_save_module.clicked.connect(self._on_save_module)
        top_bar.addWidget(self.btn_save_module)
        
        layout.addLayout(top_bar)
        
        # === OBSZAR WIDGETU UŻYTKOWNIKA ===
        self.widget_label = QLabel("🎨 Widok aplikacji:")
        self.widget_label.setObjectName("sectionHeader")
        font = self.widget_label.font()
        font.setPointSize(10)
        font.setBold(True)
        self.widget_label.setFont(font)
        layout.addWidget(self.widget_label)
        
        # Kontener na widget użytkownika
        self.widget_container = QWidget()
        self.widget_container.setObjectName("codeEditor")
        self.widget_container.setMinimumHeight(200)
        self.widget_container_layout = QVBoxLayout(self.widget_container)
        self.widget_container_layout.setContentsMargins(5, 5, 5, 5)
        layout.addWidget(self.widget_container, 3)  # większy stretch dla widgetu
        
        # === KONSOLA WYJŚCIA ===
        self.output_label = QLabel("📋 Wyjście programu:")
        self.output_label.setObjectName("sectionHeader")
        font = self.output_label.font()
        font.setPointSize(10)
        font.setBold(True)
        self.output_label.setFont(font)
        layout.addWidget(self.output_label)
        
        self.output_console = QTextEdit()
        self.output_console.setReadOnly(True)
        self.output_console.setMaximumHeight(150)
        font_console = QFont("Consolas", 9)
        self.output_console.setFont(font_console)
        self.output_console.setObjectName("logConsole")
        layout.addWidget(self.output_console, 1)
        
        # === INFORMACJA O STATUSIE ===
        self.status_label = QLabel("Status: Gotowy do uruchomienia")
        self.status_label.setObjectName("sectionHeader")
        layout.addWidget(self.status_label)
        
        # Widget użytkownika (przechowywany dla późniejszego czyszczenia)
        self.user_widget = None
        
    def _on_return_clicked(self):
        """Obsługa powrotu do edytora"""
        logger.info("[TestBox] Returning to editor")
        
        # Wyczyść poprzedni widget użytkownika
        self._clear_user_widget()
        
        self.return_to_editor.emit()
    
    def _on_save_module(self):
        """Obsługa zapisywania kodu jako moduł .pro"""
        if not self.code_to_run:
            QMessageBox.warning(self, "Błąd", "Brak kodu do zapisania!")
            return
        
        # Otwórz dialog zapisu pliku
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz jako moduł Pro-App",
            "",
            "Moduły Pro-App (*.pro);;Wszystkie pliki (*.*)"
        )
        
        if not file_path:
            return
        
        # Upewnij się, że ma rozszerzenie .pro
        if not file_path.endswith('.pro'):
            file_path += '.pro'
        
        try:
            # Zapisz czysty kod Python
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.code_to_run)
            
            logger.info(f"[TestBox] Module saved to: {file_path}")
            self._log(f"\n💾 Moduł zapisany: {file_path}", "green")
            
            QMessageBox.information(
                self,
                "Sukces",
                f"Moduł został zapisany pomyślnie!\n\n{file_path}"
            )
            
        except Exception as e:
            error_msg = f"Błąd podczas zapisywania: {str(e)}"
            logger.error(f"[TestBox] {error_msg}")
            self._log(f"\n❌ {error_msg}", "red")
            
            QMessageBox.critical(
                self,
                "Błąd",
                error_msg
            )
    
    def _clear_user_widget(self):
        """Usuwa poprzedni widget użytkownika z kontenera"""
        if self.user_widget:
            logger.debug("[TestBox] Clearing previous user widget")
            self.widget_container_layout.removeWidget(self.user_widget)
            self.user_widget.deleteLater()
            self.user_widget = None
        
    def run_code(self, code: str):
        """Uruchamia kod Python w widoku testowym"""
        self.code_to_run = code
        self.output_console.clear()
        self.status_label.setText("Status: Uruchamianie kodu...")
        
        # Wyczyść poprzedni widget użytkownika
        self._clear_user_widget()
        
        # Przechwytywanie stdout i stderr
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        
        stdout_capture = StringIO()
        stderr_capture = StringIO()
        
        # Namespace dla wykonania kodu
        namespace = {'__name__': '__main__'}
        
        try:
            # Przekieruj stdout i stderr
            sys.stdout = stdout_capture
            sys.stderr = stderr_capture
            
            self._log("="*60, "blue")
            self._log("🚀 Uruchamianie kodu jako moduł...", "blue")
            self._log("="*60, "blue")
            
            # Wykonaj kod
            exec(code, namespace)
            
            # Pobierz wyjście
            stdout_text = stdout_capture.getvalue()
            stderr_text = stderr_capture.getvalue()
            
            # Szukaj utworzonych widgetów w namespace
            self._extract_and_display_widget(namespace)
            
            if stdout_text:
                self._log("\n📤 STDOUT:", "green")
                self._log(stdout_text, "black")
            
            if stderr_text:
                self._log("\n⚠️ STDERR:", "orange")
                self._log(stderr_text, "orange")
            
            self._log("\n" + "="*60, "green")
            self._log("✅ Kod wykonany pomyślnie!", "green")
            self._log("="*60, "green")
            
            self.status_label.setText("Status: ✅ Wykonano pomyślnie")
            
        except Exception as e:
            # Pobierz wyjście przed błędem
            stdout_text = stdout_capture.getvalue()
            stderr_text = stderr_capture.getvalue()
            
            if stdout_text:
                self._log("\n📤 STDOUT (przed błędem):", "blue")
                self._log(stdout_text, "black")
            
            if stderr_text:
                self._log("\n⚠️ STDERR (przed błędem):", "orange")
                self._log(stderr_text, "orange")
            
            # Wyświetl błąd
            self._log("\n" + "="*60, "red")
            self._log("❌ BŁĄD WYKONANIA:", "red")
            self._log("="*60, "red")
            self._log(f"\n{type(e).__name__}: {str(e)}", "red")
            self._log("\nTraceback:", "red")
            self._log(traceback.format_exc(), "red")
            
            self.status_label.setText(f"Status: ❌ Błąd - {type(e).__name__}")
            
        finally:
            # Przywróć stdout i stderr
            sys.stdout = old_stdout
            sys.stderr = old_stderr
    
    def _extract_and_display_widget(self, namespace: dict):
        """Wyciąga widget z namespace i wyświetla go w kontenerze"""
        from PyQt6.QtWidgets import QWidget as QtWidget
        
        # Szukaj zmiennych będących QWidget (ale nie QMainWindow, QDialog)
        for var_name, var_value in namespace.items():
            if isinstance(var_value, QtWidget) and not var_name.startswith('_'):
                # Sprawdź czy to nie jest QMainWindow ani QDialog
                if type(var_value).__name__ not in ['QMainWindow', 'QDialog', 'QApplication']:
                    logger.info(f"[TestBox] Found user widget: {var_name} ({type(var_value).__name__})")
                    
                    # Ustaw rodzica na kontener
                    var_value.setParent(self.widget_container)
                    
                    # Dodaj do layoutu kontenera
                    self.widget_container_layout.addWidget(var_value)
                    
                    # Zapisz referencję
                    self.user_widget = var_value
                    
                    self._log(f"\n🎨 Widget '{var_name}' wyświetlony w widoku testowym", "blue")
                    
                    # Zakończ po znalezieniu pierwszego widgetu
                    break
            
    def _log(self, message: str, color: str = "black"):
        """Dodaje wiadomość do konsoli wyjścia"""
        from PyQt6.QtGui import QColor, QTextCursor
        
        self.output_console.setTextColor(QColor(color))
        self.output_console.append(message)
        cursor = self.output_console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.output_console.setTextCursor(cursor)
