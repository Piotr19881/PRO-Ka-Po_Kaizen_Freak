"""
Moduł Pseudokompilator - Testowanie i uruchamianie kodu Python

Funkcjonalność:
- Edytor kodu z numeracją wierszy
- Testowanie składni kodu Python
- Uruchamianie kodu w konsoli
- Tworzenie plików .bat (z/bez konsoli)
- Zapisywanie jako skrypt .py
- Automatyczna detekcja brakujących bibliotek
- Instalacja bibliotek przez pip

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-05
"""

import sys
import os
import ast
import subprocess
import re
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QPlainTextEdit, QTableWidget, QTableWidgetItem,
    QFileDialog, QMessageBox, QSplitter, QLabel, QFrame
)
from PyQt6.QtCore import Qt, QProcess, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor, QColor, QTextCharFormat


class LineNumberArea(QWidget):
    """Widget do wyświetlania numerów wierszy"""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor
        
    def sizeHint(self):
        return self.editor.lineNumberAreaWidth()
    
    def paintEvent(self, event):
        self.editor.lineNumberAreaPaintEvent(event)


class CodeEditor(QPlainTextEdit):
    """Edytor kodu z numeracją wierszy"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Ustawienia czcionki
        font = QFont("Consolas", 10)
        font.setFixedPitch(True)
        self.setFont(font)
        
        # Numeracja wierszy
        self.lineNumberArea = LineNumberArea(self)
        
        # Połączenia sygnałów
        self.blockCountChanged.connect(self.updateLineNumberAreaWidth)
        self.updateRequest.connect(self.updateLineNumberArea)
        
        self.updateLineNumberAreaWidth(0)
        
        # Wcięcia
        self.setTabStopDistance(40)  # 4 spacje
    
    def lineNumberAreaWidth(self):
        """Oblicza szerokość obszaru numerów wierszy"""
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space
    
    def updateLineNumberAreaWidth(self, newBlockCount):
        """Aktualizuje szerokość obszaru numerów wierszy"""
        self.setViewportMargins(self.lineNumberAreaWidth(), 0, 0, 0)
    
    def updateLineNumberArea(self, rect, dy):
        """Aktualizuje obszar numerów wierszy przy przewijaniu"""
        if dy:
            self.lineNumberArea.scroll(0, dy)
        else:
            self.lineNumberArea.update(0, rect.y(), self.lineNumberArea.width(), rect.height())
        
        if rect.contains(self.viewport().rect()):
            self.updateLineNumberAreaWidth(0)
    
    def resizeEvent(self, event):
        """Obsługa zmiany rozmiaru"""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.lineNumberArea.setGeometry(cr.left(), cr.top(), self.lineNumberAreaWidth(), cr.height())
    
    def lineNumberAreaPaintEvent(self, event):
        """Rysuje numery wierszy"""
        from PyQt6.QtGui import QPainter
        
        painter = QPainter(self.lineNumberArea)
        painter.fillRect(event.rect(), QColor(240, 240, 240))
        
        block = self.firstVisibleBlock()
        blockNumber = block.blockNumber()
        top = self.blockBoundingGeometry(block).translated(self.contentOffset()).top()
        bottom = top + self.blockBoundingRect(block).height()
        
        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(blockNumber + 1)
                painter.setPen(QColor(100, 100, 100))
                painter.drawText(
                    0, int(top), 
                    self.lineNumberArea.width() - 3, 
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight, 
                    number
                )
            
            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            blockNumber += 1


class PseudoCompilerModule(QMainWindow):
    """Główny moduł Pseudokompilatora"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Pseudokompilator Python")
        self.setMinimumSize(900, 700)
        
        # Stan
        self.syntax_ok = False
        self.missing_modules = []
        self.last_code = ""
        
        # UI
        self.init_ui()
    
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Splitter główny (góra: edytor, dół: logi + tabela)
        splitter = QSplitter(Qt.Orientation.Vertical)
        
        # === GÓRNA CZĘŚĆ: Edytor kodu ===
        editor_widget = QWidget()
        editor_layout = QVBoxLayout()
        editor_widget.setLayout(editor_layout)
        
        # Nagłówek
        header_label = QLabel("📝 Edytor kodu Python")
        header_label.setStyleSheet("font-size: 14pt; font-weight: bold; padding: 5px;")
        editor_layout.addWidget(header_label)
        
        # Edytor
        self.code_editor = CodeEditor()
        self.code_editor.setPlaceholderText("Wklej tutaj kod Python do testowania...")
        editor_layout.addWidget(self.code_editor)
        
        # Przyciski akcji
        buttons_layout = QHBoxLayout()
        buttons_layout.setSpacing(5)
        
        # Testuj - zawsze aktywny
        self.btn_test = QPushButton("🔍 Testuj składnię")
        self.btn_test.setStyleSheet(
            "background-color: #2196F3; color: white; font-weight: bold; padding: 8px; font-size: 11pt;"
        )
        self.btn_test.clicked.connect(self.test_syntax)
        self.btn_test.setToolTip("Sprawdź składnię kodu Python")
        self.btn_test.setSizePolicy(self.btn_test.sizePolicy().horizontalPolicy(), self.btn_test.sizePolicy().verticalPolicy())
        
        # Włącz - aktywny po teście
        self.btn_run = QPushButton("▶️ Włącz")
        self.btn_run.setStyleSheet(
            "background-color: #4CAF50; color: white; font-weight: bold; padding: 8px; font-size: 11pt;"
        )
        self.btn_run.clicked.connect(self.run_code)
        self.btn_run.setEnabled(False)
        self.btn_run.setToolTip("Uruchom kod w konsoli")
        self.btn_run.setSizePolicy(self.btn_run.sizePolicy().horizontalPolicy(), self.btn_run.sizePolicy().verticalPolicy())
        
        # Zapisz jako BAT
        self.btn_save_bat = QPushButton("📦 Zapisz jako BAT")
        self.btn_save_bat.setStyleSheet(
            "background-color: #FF9800; color: white; font-weight: bold; padding: 8px; font-size: 11pt;"
        )
        self.btn_save_bat.clicked.connect(self.save_as_bat)
        self.btn_save_bat.setEnabled(False)
        self.btn_save_bat.setToolTip("Utwórz plik .bat do uruchomienia kodu")
        self.btn_save_bat.setSizePolicy(self.btn_save_bat.sizePolicy().horizontalPolicy(), self.btn_save_bat.sizePolicy().verticalPolicy())
        
        # Zapisz jako skrypt Python
        self.btn_save_py = QPushButton("💾 Zapisz jako Python")
        self.btn_save_py.setStyleSheet(
            "background-color: #9C27B0; color: white; font-weight: bold; padding: 8px; font-size: 11pt;"
        )
        self.btn_save_py.clicked.connect(self.save_as_python)
        self.btn_save_py.setEnabled(False)
        self.btn_save_py.setToolTip("Zapisz kod jako plik .py")
        self.btn_save_py.setSizePolicy(self.btn_save_py.sizePolicy().horizontalPolicy(), self.btn_save_py.sizePolicy().verticalPolicy())
        
        # Wyczyść
        btn_clear = QPushButton("🗑️ Wyczyść")
        btn_clear.setStyleSheet("padding: 8px; font-size: 11pt;")
        btn_clear.clicked.connect(self.clear_all)
        btn_clear.setToolTip("Wyczyść edytor i logi")
        btn_clear.setSizePolicy(btn_clear.sizePolicy().horizontalPolicy(), btn_clear.sizePolicy().verticalPolicy())
        
        # Pomoc
        btn_help = QPushButton("❓ Pomoc")
        btn_help.setStyleSheet(
            "background-color: #00BCD4; color: white; font-weight: bold; padding: 8px; font-size: 11pt;"
        )
        btn_help.clicked.connect(self.show_help)
        btn_help.setToolTip("Wyświetl pomoc o module")
        btn_help.setSizePolicy(btn_help.sizePolicy().horizontalPolicy(), btn_help.sizePolicy().verticalPolicy())
        
        # Dodaj przyciski z równomiernym rozłożeniem (stretch=1 dla każdego)
        buttons_layout.addWidget(self.btn_test, 1)
        buttons_layout.addWidget(self.btn_run, 1)
        buttons_layout.addWidget(self.btn_save_bat, 1)
        buttons_layout.addWidget(self.btn_save_py, 1)
        buttons_layout.addWidget(btn_clear, 1)
        buttons_layout.addWidget(btn_help, 1)
        
        editor_layout.addLayout(buttons_layout)
        
        splitter.addWidget(editor_widget)
        
        # === DOLNA CZĘŚĆ: Logi + Tabela bibliotek ===
        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout()
        bottom_widget.setLayout(bottom_layout)
        
        # Konsola logów
        logs_label = QLabel("📋 Konsola logów")
        logs_label.setStyleSheet("font-size: 12pt; font-weight: bold; padding: 5px;")
        bottom_layout.addWidget(logs_label)
        
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMaximumHeight(200)
        font_log = QFont("Consolas", 9)
        self.log_console.setFont(font_log)
        self.log_console.setPlaceholderText("Tutaj pojawią się logi testowania i uruchamiania...")
        bottom_layout.addWidget(self.log_console)
        
        # Tabela brakujących bibliotek
        libs_label = QLabel("📚 Brakujące biblioteki")
        libs_label.setStyleSheet("font-size: 12pt; font-weight: bold; padding: 5px;")
        bottom_layout.addWidget(libs_label)
        
        self.libs_table = QTableWidget()
        self.libs_table.setColumnCount(4)
        self.libs_table.setHorizontalHeaderLabels(["Nazwa biblioteki", "Wersja", "✓/✗", "Akcja"])
        self.libs_table.setMaximumHeight(200)
        
        # Ustaw autodopasowanie kolumn z różnymi proporcjami
        from PyQt6.QtWidgets import QHeaderView
        header = self.libs_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)  # Nazwa - rozciągliwa (szeroka)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)  # Wersja - rozciągliwa (szeroka)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Fixed)    # Status - stała (wąska)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # Akcja - stała (wąska)
        
        # Ustaw minimalne szerokości dla kolumn rozciągliwych i stałe dla wąskich
        self.libs_table.setColumnWidth(0, 250)  # Nazwa - minimalna
        self.libs_table.setColumnWidth(1, 150)  # Wersja - minimalna
        self.libs_table.setColumnWidth(2, 50)   # Status - stała (wąska)
        self.libs_table.setColumnWidth(3, 120)  # Akcja - stała (wąska)
        
        bottom_layout.addWidget(self.libs_table)
        
        splitter.addWidget(bottom_widget)
        
        # Proporcje splitter: 60% edytor, 40% logi+tabela
        splitter.setSizes([400, 300])
        
        main_layout.addWidget(splitter)
    
    def log(self, message, color="black"):
        """Dodaje wiadomość do konsoli logów"""
        self.log_console.setTextColor(QColor(color))
        self.log_console.append(message)
        # Przewiń na dół
        cursor = self.log_console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_console.setTextCursor(cursor)
    
    def test_syntax(self):
        """Testuje składnię kodu Python"""
        code = self.code_editor.toPlainText().strip()
        
        if not code:
            QMessageBox.warning(self, "Błąd", "Edytor jest pusty! Wklej kod do testowania.")
            return
        
        self.log("\n" + "="*60)
        self.log("🔍 Testowanie składni...", "blue")
        self.log("="*60)
        
        # Resetuj stan
        self.syntax_ok = False
        self.missing_modules = []
        self.last_code = code
        
        # Wyłącz przyciski
        self.btn_run.setEnabled(False)
        self.btn_save_bat.setEnabled(False)
        self.btn_save_py.setEnabled(False)
        
        # Wyczyść tabelę bibliotek
        self.libs_table.setRowCount(0)
        
        # Sprawdź składnię
        try:
            ast.parse(code)
            self.log("✅ Składnia poprawna!", "green")
            self.syntax_ok = True
            
            # Wykryj używane moduły
            self.detect_imports(code)
            
            # Włącz przyciski
            self.btn_run.setEnabled(True)
            self.btn_save_bat.setEnabled(True)
            self.btn_save_py.setEnabled(True)
            
            self.log("✅ Kod gotowy do uruchomienia!", "green")
            
        except SyntaxError as e:
            self.syntax_ok = False
            self.log(f"❌ Błąd składni w linii {e.lineno}:", "red")
            self.log(f"   {e.msg}", "red")
            if e.text:
                self.log(f"   {e.text.strip()}", "darkred")
            QMessageBox.critical(
                self, 
                "Błąd składni",
                f"Znaleziono błąd składni w linii {e.lineno}:\n{e.msg}"
            )
        
        except Exception as e:
            self.syntax_ok = False
            self.log(f"❌ Błąd: {str(e)}", "red")
            QMessageBox.critical(self, "Błąd", f"Wystąpił błąd:\n{str(e)}")
    
    def detect_imports(self, code):
        """Wykrywa importowane moduły w kodzie i sprawdza ich dostępność"""
        self.log("\n🔎 Wykrywanie importowanych bibliotek...", "blue")
        
        import_pattern = r'^\s*(?:import|from)\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        imports = set()
        
        for line in code.split('\n'):
            match = re.match(import_pattern, line)
            if match:
                module_name = match.group(1)
                # Pomiń standardowe biblioteki Pythona
                if module_name not in ['sys', 'os', 're', 'json', 'datetime', 'time', 
                                       'math', 'random', 'collections', 'itertools',
                                       'functools', 'pathlib', 'subprocess', 'threading',
                                       'multiprocessing', 'logging', 'argparse', 'unittest',
                                       'ast', 'copy', 'pickle', 'shelve', 'sqlite3',
                                       'csv', 'xml', 'html', 'http', 'urllib', 'email',
                                       'hashlib', 'hmac', 'secrets', 'typing', 'dataclasses']:
                    imports.add(module_name)
        
        if imports:
            self.log(f"📦 Znaleziono {len(imports)} importów bibliotek zewnętrznych: {', '.join(sorted(imports))}", "darkblue")
            
            # Sprawdź dostępność każdej biblioteki
            available = []
            missing = []
            
            for module_name in sorted(imports):
                if self.check_module_available(module_name):
                    available.append(module_name)
                else:
                    missing.append(module_name)
            
            if available:
                self.log(f"✅ Dostępne biblioteki ({len(available)}): {', '.join(available)}", "green")
            
            if missing:
                self.log(f"❌ Brakujące biblioteki ({len(missing)}): {', '.join(missing)}", "red")
                self.missing_modules = missing
            else:
                self.missing_modules = []
            
            # Wyświetl wszystkie w tabeli
            self.populate_libs_table_with_all(list(imports), available, missing)
        else:
            self.log("ℹ️ Nie znaleziono importów bibliotek zewnętrznych", "gray")
            self.missing_modules = []
    
    def check_module_available(self, module_name):
        """Sprawdza czy moduł jest dostępny w systemie"""
        try:
            __import__(module_name)
            return True
        except ImportError:
            return False
    
    def run_code(self):
        """Uruchamia kod w konsoli"""
        if not self.syntax_ok:
            QMessageBox.warning(self, "Błąd", "Najpierw przetestuj składnię!")
            return
        
        code = self.last_code
        
        self.log("\n" + "="*60)
        self.log("▶️ Uruchamianie kodu...", "blue")
        self.log("="*60)
        
        # Zapisz kod do tymczasowego pliku
        temp_file = "temp_pseudocompiler.py"
        try:
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(code)
            
            # Uruchom kod
            python_path = sys.executable
            
            self.log(f"🐍 Używam interpretera: {python_path}", "darkblue")
            
            result = subprocess.run(
                [python_path, temp_file],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            # Wyświetl wynik
            if result.stdout:
                self.log("\n📤 Wyjście programu:", "green")
                self.log(result.stdout, "black")
            
            if result.stderr:
                # Sprawdź, czy błąd dotyczy brakujących modułów
                self.check_missing_modules(result.stderr)
                
                if "ModuleNotFoundError" in result.stderr or "ImportError" in result.stderr:
                    self.log("\n⚠️ Błędy:", "orange")
                else:
                    self.log("\n❌ Błędy:", "red")
                self.log(result.stderr, "darkred")
            
            if result.returncode == 0:
                self.log("\n✅ Program zakończony pomyślnie (kod: 0)", "green")
            else:
                self.log(f"\n⚠️ Program zakończony z kodem: {result.returncode}", "orange")
            
            # Usuń plik tymczasowy
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        except subprocess.TimeoutExpired:
            self.log("\n❌ Przekroczono limit czasu (30s)!", "red")
            if os.path.exists(temp_file):
                os.remove(temp_file)
        
        except Exception as e:
            self.log(f"\n❌ Błąd podczas uruchamiania: {str(e)}", "red")
            if os.path.exists(temp_file):
                os.remove(temp_file)
    
    def check_missing_modules(self, error_text):
        """Sprawdza brakujące moduły w błędach"""
        # Wzorce dla ModuleNotFoundError i ImportError
        patterns = [
            r"ModuleNotFoundError: No module named '([^']+)'",
            r"ImportError: No module named ([^\s]+)",
        ]
        
        missing = set()
        for pattern in patterns:
            matches = re.findall(pattern, error_text)
            missing.update(matches)
        
        if missing:
            self.log(f"\n📚 Wykryto brakujące biblioteki: {', '.join(sorted(missing))}", "orange")
            self.missing_modules = list(missing)
            self.populate_libs_table()
    
    def populate_libs_table_with_all(self, all_modules, available, missing):
        """Wypełnia tabelę wszystkimi bibliotekami (dostępnymi i brakującymi)"""
        self.libs_table.setRowCount(0)
        
        for module_name in sorted(all_modules):
            row = self.libs_table.rowCount()
            self.libs_table.insertRow(row)
            
            is_available = module_name in available
            
            # Kolumna 0: Nazwa biblioteki
            name_item = QTableWidgetItem(module_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            if is_available:
                name_item.setForeground(QColor("green"))
            else:
                name_item.setForeground(QColor("red"))
            self.libs_table.setItem(row, 0, name_item)
            
            # Kolumna 1: Wersja
            if is_available:
                version = self.get_package_version(module_name)
                version_item = QTableWidgetItem(version)
                version_item.setForeground(QColor("green"))
            else:
                version_item = QTableWidgetItem("---")
                version_item.setForeground(QColor("gray"))
            
            version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.libs_table.setItem(row, 1, version_item)
            
            # Kolumna 2: Status (✓/✗)
            if is_available:
                status_item = QTableWidgetItem("✓")
                status_item.setForeground(QColor("green"))
            else:
                status_item = QTableWidgetItem("✗")
                status_item.setForeground(QColor("red"))
            
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.libs_table.setItem(row, 2, status_item)
            
            # Kolumna 3: Przycisk instalacji (tylko dla brakujących)
            if is_available:
                # Dostępna - brak przycisku, tylko tekst
                available_label = QLabel("✓ Dostępna")
                available_label.setStyleSheet(
                    "color: green; font-weight: bold; padding: 4px;"
                )
                available_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.libs_table.setCellWidget(row, 3, available_label)
            else:
                # Brakująca - przycisk instalacji
                install_btn = QPushButton("⬇️ Zainstaluj")
                install_btn.setStyleSheet(
                    "background-color: #4CAF50; color: white; font-weight: bold; padding: 4px;"
                )
                install_btn.clicked.connect(lambda checked, m=module_name, r=row: self.install_module(m, r))
                self.libs_table.setCellWidget(row, 3, install_btn)
    
    def populate_libs_table(self):
        """Wypełnia tabelę brakującymi bibliotekami"""
        self.libs_table.setRowCount(0)
        
        for module_name in self.missing_modules:
            row = self.libs_table.rowCount()
            self.libs_table.insertRow(row)
            
            # Kolumna 0: Nazwa biblioteki
            name_item = QTableWidgetItem(module_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.libs_table.setItem(row, 0, name_item)
            
            # Kolumna 1: Wersja (na razie pusta, będzie uzupełniona po instalacji)
            version_item = QTableWidgetItem("---")
            version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            version_item.setForeground(QColor("gray"))
            self.libs_table.setItem(row, 1, version_item)
            
            # Kolumna 2: Status (✓/✗)
            status_item = QTableWidgetItem("✗")
            status_item.setForeground(QColor("red"))
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.libs_table.setItem(row, 2, status_item)
            
            # Kolumna 3: Przycisk instalacji
            install_btn = QPushButton("⬇️ Zainstaluj")
            install_btn.setStyleSheet(
                "background-color: #4CAF50; color: white; font-weight: bold; padding: 4px;"
            )
            install_btn.clicked.connect(lambda checked, m=module_name, r=row: self.install_module(m, r))
            self.libs_table.setCellWidget(row, 3, install_btn)
    
    def install_module(self, module_name, row):
        """Instaluje bibliotekę przez pip"""
        self.log(f"\n📥 Instalowanie biblioteki: {module_name}...", "blue")
        
        python_path = sys.executable
        
        try:
            result = subprocess.run(
                [python_path, "-m", "pip", "install", module_name],
                capture_output=True,
                text=True,
                timeout=120
            )
            
            if result.returncode == 0:
                self.log(f"✅ Biblioteka {module_name} zainstalowana pomyślnie!", "green")
                
                # Sprawdź wersję zainstalowanej biblioteki
                version = self.get_package_version(module_name)
                
                # Kolumna 1: Wersja
                version_item = QTableWidgetItem(version)
                version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                version_item.setForeground(QColor("green"))
                self.libs_table.setItem(row, 1, version_item)
                
                # Kolumna 2: Status (✓)
                status_item = QTableWidgetItem("✓")
                status_item.setForeground(QColor("green"))
                status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.libs_table.setItem(row, 2, status_item)
                
                # Kolumna 3: Wyłącz przycisk
                btn = self.libs_table.cellWidget(row, 3)
                if btn and isinstance(btn, QPushButton):
                    btn.setEnabled(False)
                    btn.setText("✓ OK")
                    btn.setStyleSheet(
                        "background-color: #888; color: white; font-weight: bold; padding: 4px;"
                    )
            else:
                self.log(f"❌ Błąd podczas instalacji {module_name}:", "red")
                self.log(result.stderr, "darkred")
                QMessageBox.critical(
                    self,
                    "Błąd instalacji",
                    f"Nie udało się zainstalować {module_name}:\n{result.stderr}"
                )
        
        except subprocess.TimeoutExpired:
            self.log(f"❌ Przekroczono limit czasu instalacji {module_name}!", "red")
        
        except Exception as e:
            self.log(f"❌ Błąd: {str(e)}", "red")
            QMessageBox.critical(self, "Błąd", f"Wystąpił błąd:\n{str(e)}")
    
    def get_package_version(self, package_name):
        """Pobiera wersję zainstalowanego pakietu"""
        try:
            result = subprocess.run(
                [sys.executable, "-m", "pip", "show", package_name],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode == 0:
                # Szukaj linii "Version: x.y.z"
                for line in result.stdout.split('\n'):
                    if line.startswith('Version:'):
                        return line.split(':', 1)[1].strip()
            
            return "???"
        except Exception:
            return "???"
    
    def save_as_bat(self):
        """Zapisuje kod jako plik .bat"""
        if not self.syntax_ok:
            QMessageBox.warning(self, "Błąd", "Najpierw przetestuj składnię!")
            return
        
        # Dialog: z konsolą czy bez
        reply = QMessageBox.question(
            self,
            "Typ pliku BAT",
            "Czy plik .bat ma otwierać konsolę?\n\n"
            "TAK - Konsola będzie widoczna\n"
            "NIE - Program uruchomi się bez konsoli",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
        
        with_console = (reply == QMessageBox.StandardButton.Yes)
        
        # Wybór miejsca zapisu
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz jako plik BAT",
            "",
            "Pliki BAT (*.bat);;Wszystkie pliki (*.*)"
        )
        
        if not file_path:
            return
        
        if not file_path.endswith('.bat'):
            file_path += '.bat'
        
        try:
            # Zapisz kod Python w tym samym katalogu
            bat_dir = os.path.dirname(file_path)
            bat_name = os.path.splitext(os.path.basename(file_path))[0]
            py_file = os.path.join(bat_dir, f"{bat_name}.py")
            
            with open(py_file, 'w', encoding='utf-8') as f:
                f.write(self.last_code)
            
            # Utwórz plik .bat
            python_path = sys.executable
            
            if with_console:
                bat_content = f'@echo off\n"{python_path}" "%~dp0{bat_name}.py"\npause\n'
            else:
                bat_content = f'@echo off\nstart /B "" "{python_path}" "%~dp0{bat_name}.py"\n'
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(bat_content)
            
            self.log(f"\n✅ Zapisano plik BAT: {file_path}", "green")
            self.log(f"✅ Zapisano skrypt Python: {py_file}", "green")
            
            QMessageBox.information(
                self,
                "Sukces",
                f"Pliki zostały zapisane:\n\n"
                f"BAT: {file_path}\n"
                f"Python: {py_file}"
            )
        
        except Exception as e:
            self.log(f"❌ Błąd podczas zapisywania: {str(e)}", "red")
            QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać pliku:\n{str(e)}")
    
    def save_as_python(self):
        """Zapisuje kod jako plik .py"""
        if not self.syntax_ok:
            QMessageBox.warning(self, "Błąd", "Najpierw przetestuj składnię!")
            return
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Zapisz jako skrypt Python",
            "",
            "Pliki Python (*.py);;Wszystkie pliki (*.*)"
        )
        
        if not file_path:
            return
        
        if not file_path.endswith('.py'):
            file_path += '.py'
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(self.last_code)
            
            self.log(f"\n✅ Zapisano skrypt Python: {file_path}", "green")
            
            QMessageBox.information(
                self,
                "Sukces",
                f"Skrypt został zapisany:\n{file_path}"
            )
        
        except Exception as e:
            self.log(f"❌ Błąd podczas zapisywania: {str(e)}", "red")
            QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać pliku:\n{str(e)}")
    
    def clear_all(self):
        """Czyści edytor i logi"""
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            "Czy na pewno chcesz wyczyścić edytor i logi?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.code_editor.clear()
            self.log_console.clear()
            self.libs_table.setRowCount(0)
            self.syntax_ok = False
            self.missing_modules = []
            self.last_code = ""
            
            # Wyłącz przyciski
            self.btn_run.setEnabled(False)
            self.btn_save_bat.setEnabled(False)
            self.btn_save_py.setEnabled(False)
            
            self.log("🗑️ Edytor i logi wyczyszczone", "blue")
    
    def show_help(self):
        """Wyświetla okno pomocy z opisem modułu"""
        help_text = """
<h2>Pseudokompilator Python - Twoja Supermoc!</h2>

<h3 style="color: #2196F3;">Po co ten moduł?</h3>
<p style="font-size: 11pt;">
<b>Twórz potężne narzędzia BEZ specjalistycznej wiedzy!</b><br>
Ten moduł to <b>REWOLUCJA</b> - pozwala każdemu tworzyć użyteczne skrypty Python 
i przypisywać je do przycisków w aplikacji. <b>Żadnego programowania!</b>
</p>

<h3 style="color: #4CAF50;">Czym są skrypty Python?</h3>
<p>
<b>Skrypty Python to małe programy</b>, które wykonują konkretne zadania - od prostych 
(jak zmiana nazw plików) po zaawansowane (generowanie raportów, przetwarzanie danych).<br><br>

<b>Najlepsza wiadomość?</b> Możesz je <b>tworzyć za pomocą ChatGPT/Claude/Gemini!</b><br>
<ul style="margin-top: 5px;">
  <li>Powiedz AI czego potrzebujesz (np. "napisz skrypt do zmiany nazw plików")</li>
  <li>Skopiuj wygenerowany kod</li>
  <li>Wklej tutaj i przetestuj jednym kliknięciem!</li>
  <li><b>GOTOWE!</b> Masz działające narzędzie!</li>
</ul>
</p>

<h3 style="color: #FF9800;">Czym są biblioteki Python?</h3>
<p>
<b>Biblioteki to gotowe zestawy narzędzi</b>, które rozszerzają możliwości Pythona:<br>
<ul style="margin-top: 5px;">
  <li><b>requests</b> - pobieranie danych z internetu</li>
  <li><b>pandas</b> - analiza danych w Excelu i CSV</li>
  <li><b>pillow</b> - edycja zdjęć</li>
  <li><b>openpyxl</b> - praca z plikami Excel</li>
  <li><b>...i TYSIĄCE innych!</b></li>
</ul>

<b style="color: #4CAF50;">MAGIA NASZEJ APLIKACJI:</b><br>
Wykrywamy automatycznie które biblioteki są potrzebne i instalujemy je <b>JEDNYM KLIKNIĘCIEM!</b><br>
<span style="color: #666;">Zielone = już dostępne | Czerwone = kliknij "Zainstaluj"</span>
</p>

<h3 style="color: #9C27B0;">Dlaczego nasza aplikacja jest ZAJEBISTA?</h3>
<div style="background-color: #f0f0f0; padding: 10px; border-radius: 5px; margin: 10px 0;">
<b>Wszystko w jednym miejscu:</b>
<ul>
  <li><b>Testuj</b> - sprawdź czy kod jest poprawny (bez błędów!)</li>
  <li><b>Uruchom</b> - zobacz czy działa jak chcesz</li>
  <li><b>Zainstaluj</b> - automatycznie dodaj brakujące biblioteki</li>
  <li><b>Zapisz</b> - zachowaj jako .py lub .bat do późniejszego użycia</li>
  <li><b>Przypisz</b> - dodaj do przycisków w aplikacji głównej!</li>
</ul>
</div>

<h3 style="color: #00BCD4;">Praktyczne przykłady - co możesz stworzyć?</h3>
<ul>
  <li><b>Organizator plików</b> - sortowanie po dacie/typie/nazwie</li>
  <li><b>Generator raportów</b> - automatyczne zestawienia z Excela</li>
  <li><b>Konwerter obrazów</b> - zmiana formatu/rozmiaru setek zdjęć</li>
  <li><b>Wysyłka emaili</b> - masowa korespondencja</li>
  <li><b>Scraper</b> - pobieranie danych ze stron www</li>
  <li><b>Automatyzacja dokumentów</b> - generowanie PDF/Word</li>
  <li><b>...i WSZYSTKO co wymyślisz!</b></li>
</ul>

<h3 style="color: #E91E63;">Workflow - jak to działa?</h3>
<div style="background-color: #e3f2fd; padding: 10px; border-radius: 5px;">
<ol style="font-size: 10pt; line-height: 1.6;">
  <li><b>Zapytaj AI</b>: "Stwórz skrypt do [twoje zadanie]"</li>
  <li><b>Skopiuj kod</b> wygenerowany przez AI</li>
  <li><b>Wklej tutaj</b> w edytor</li>
  <li><b>Testuj</b> - sprawdź składnię (błędy? popraw z AI!)</li>
  <li><b>Zainstaluj biblioteki</b> - kliknij zielone przyciski</li>
  <li><b>Uruchom</b> - zobacz efekty na żywo!</li>
  <li><b>Zapisz</b> - jako .py lub .bat</li>
  <li><b>Dodaj do aplikacji</b> - przypisz do przycisku!</li>
</ol>
</div>

<h3 style="color: #795548;">Twórz podręczne narzędzia ZERO wysiłku!</h3>
<p style="font-size: 11pt;">
<b>NIE MUSISZ UMIEĆ PROGRAMOWAĆ!</b><br>
AI pisze kod → Ty testujesz → Nasza aplikacja instaluje biblioteki → Gotowe!<br><br>

<b style="color: #4CAF50;">To jak mieć własnego programistę 24/7!</b><br>
<span style="color: #666; font-size: 9pt;">
(ale lepiej, bo nie musisz go karmić kawą i pizzą)
</span>
</p>

<div style="background-color: #fff3e0; padding: 15px; border-left: 4px solid #FF9800; margin: 15px 0;">
<b style="color: #FF9800; font-size: 12pt;">BONUS - Ekosystem narzędzi:</b><br>
<span style="font-size: 10pt;">
Utworzone skrypty możesz przypisać do przycisków w aplikacji głównej, 
połączyć z menedżerem schowka, folderami, skrótami... 
<b>Zbuduj swój własny zestaw super-narzędzi!</b>
</span>
</div>

<p style="margin-top: 20px; text-align: center; color: #666; font-size: 9pt;">
<i>Pseudokompilator Python - Część ekosystemu "Pro Ka Po Comer"<br>
Gdzie automatyzacja spotyka prostotę!</i>
</p>
"""
        
        # Stwórz dialog z możliwością przewijania
        from PyQt6.QtWidgets import QDialog
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Pomoc - Pseudokompilator Python")
        dialog.setMinimumSize(750, 600)
        
        # Layout dla dialogu
        layout = QVBoxLayout()
        
        # QTextEdit z suwakiem
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(help_text)
        
        # Przycisk OK
        ok_button = QPushButton("OK")
        ok_button.clicked.connect(dialog.accept)
        ok_button.setFixedWidth(100)
        
        # Dodaj widgety do layoutu
        layout.addWidget(text_edit)
        layout.addWidget(ok_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        dialog.setLayout(layout)
        dialog.exec()


def main():
    """Funkcja główna - uruchamia aplikację"""
    app = QApplication(sys.argv)
    app.setApplicationName("Pseudokompilator Python")
    app.setOrganizationName("Pro Ka Po Comer")
    window = PseudoCompilerModule()
    window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
