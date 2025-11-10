"""
Module Viewer - Uniwersalny widok do wyświetlania modułów użytkownika (.pro)

Ten moduł ładuje i wyświetla aplikacje użytkownika bez interfejsu testowego.
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QMessageBox
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from loguru import logger
import sys
from io import StringIO
import traceback


class ModuleViewer(QWidget):
    """Uniwersalny widok do wyświetlania modułów użytkownika"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        self.user_widget = None
        self.module_code = ""
        
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Kontener na widget użytkownika (cały obszar)
        self.widget_container = QWidget()
        self.widget_container.setObjectName("moduleContainer")
        self.widget_container_layout = QVBoxLayout(self.widget_container)
        self.widget_container_layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.widget_container, 1)
        
    def load_module(self, file_path: str):
        """Ładuje i uruchamia moduł z pliku .pro"""
        try:
            # Wczytaj kod z pliku
            with open(file_path, 'r', encoding='utf-8') as f:
                self.module_code = f.read()
            
            logger.info(f"[ModuleViewer] Loading module from: {file_path}")
            
            # Wyczyść poprzedni widget
            self._clear_user_widget()
            
            # Wykonaj kod modułu
            success = self._execute_module()
            
            return success
            
        except FileNotFoundError:
            error_msg = f"Nie znaleziono pliku modułu: {file_path}"
            logger.error(f"[ModuleViewer] {error_msg}")
            self._show_error(error_msg)
            return False
            
        except Exception as e:
            error_msg = f"Błąd podczas ładowania modułu: {str(e)}"
            logger.error(f"[ModuleViewer] {error_msg}\n{traceback.format_exc()}")
            self._show_error(error_msg)
            return False
    
    def load_module_from_code(self, code: str):
        """Ładuje i uruchamia moduł z kodu"""
        self.module_code = code
        logger.info("[ModuleViewer] Loading module from code")
        
        # Wyczyść poprzedni widget
        self._clear_user_widget()
        
        # Wykonaj kod modułu
        self._execute_module()
    
    def _execute_module(self):
        """Wykonuje kod modułu"""
        # Przechwytywanie stdout i stderr (ukryte)
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
            
            # Wykonaj kod
            exec(self.module_code, namespace)
            
            # Szukaj utworzonych widgetów w namespace
            self._extract_and_display_widget(namespace)
            
            logger.info("[ModuleViewer] Module executed successfully")
            return True
            
        except Exception as e:
            error_msg = f"Błąd wykonania modułu:\n\n{type(e).__name__}: {str(e)}"
            logger.error(f"[ModuleViewer] {error_msg}\n{traceback.format_exc()}")
            self._show_error(error_msg)
            return False
            
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
                    logger.info(f"[ModuleViewer] Found user widget: {var_name} ({type(var_value).__name__})")
                    
                    # Ustaw rodzica na kontener
                    var_value.setParent(self.widget_container)
                    
                    # Dodaj do layoutu kontenera
                    self.widget_container_layout.addWidget(var_value)
                    
                    # Zapisz referencję
                    self.user_widget = var_value
                    
                    # Zakończ po znalezieniu pierwszego widgetu
                    break
        
        if not self.user_widget:
            logger.warning("[ModuleViewer] No widget found in module")
            self._show_info("Nie znaleziono widgetu w module.\n\nUpewnij się, że kod tworzy widget i przypisuje go do zmiennej.")
    
    def _clear_user_widget(self):
        """Usuwa poprzedni widget użytkownika z kontenera"""
        if self.user_widget:
            logger.debug("[ModuleViewer] Clearing previous user widget")
            self.widget_container_layout.removeWidget(self.user_widget)
            self.user_widget.deleteLater()
            self.user_widget = None
    
    def _show_error(self, message: str):
        """Wyświetla komunikat o błędzie"""
        error_label = QLabel(f"❌ Błąd\n\n{message}")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(11)
        error_label.setFont(font)
        error_label.setStyleSheet("color: #F44336; padding: 20px;")
        
        self.widget_container_layout.addWidget(error_label)
    
    def _show_info(self, message: str):
        """Wyświetla komunikat informacyjny"""
        info_label = QLabel(f"ℹ️ Informacja\n\n{message}")
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info_label.setWordWrap(True)
        font = QFont()
        font.setPointSize(11)
        info_label.setFont(font)
        info_label.setStyleSheet("color: #2196F3; padding: 20px;")
        
        self.widget_container_layout.addWidget(info_label)
    
    def reload_module(self):
        """Przeładowuje moduł (uruchamia ponownie)"""
        logger.info("[ModuleViewer] Reloading module")
        self._clear_user_widget()
        self._execute_module()
