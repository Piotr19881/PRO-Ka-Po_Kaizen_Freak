"""
Pro-App View - Interfejs użytkownika modułu kompilacji i wykonywania skryptów Python

Widok zintegrowany z:
- Systemem i18n (tłumaczenia)
- Theme Managerem (zarządzanie kolorami)
- Pro-App Logic (logika biznesowa)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTextEdit,
    QPlainTextEdit, QTableWidget, QTableWidgetItem, QFileDialog,
    QMessageBox, QSplitter, QLabel, QHeaderView, QStackedWidget,
    QScrollArea
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QTextCursor, QColor, QPainter

from loguru import logger

from ..Modules.pro_app.pro_app_logic import ProAppLogic
from ..Modules.pro_app.testbox import TestBoxView
from ..utils.i18n_manager import t, get_i18n


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


class ProAppView(QWidget):
    """Widok Pro-App - Pseudokompilator Python"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Logika biznesowa
        self.logic = ProAppLogic()
        
        # UI
        self._setup_ui()
        
        # Połącz z i18n
        get_i18n().language_changed.connect(self.update_translations)
        
        # Załaduj początkowe tłumaczenia
        self.update_translations()
        
        logger.info("[ProAppView] Initialized")
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        # Główny layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Stacked widget do przełączania między edytorem a widokiem testowym
        self.stacked_widget = QStackedWidget()
        
        # === STRONA 1: EDYTOR (indeks 0) ===
        self.editor_widget = self._create_editor_page()
        self.stacked_widget.addWidget(self.editor_widget)
        
        # === STRONA 2: WIDOK TESTOWY (indeks 1) ===
        self.testbox_view = TestBoxView(parent=self)
        self.testbox_view.return_to_editor.connect(self._return_to_editor)
        self.stacked_widget.addWidget(self.testbox_view)
        
        # Domyślnie pokaż edytor
        self.stacked_widget.setCurrentIndex(0)
        
        main_layout.addWidget(self.stacked_widget)
    
    def _create_editor_page(self) -> QWidget:
        """Tworzy stronę edytora"""
        widget = QWidget()
        main_layout = QVBoxLayout(widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Scroll Area dla całego widoku
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget wewnętrzny w scroll area
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(5)
        
        # === NAGŁÓWEK EDYTORA ===
        self.header_label = QLabel()
        self.header_label.setObjectName("sectionHeader")
        font = self.header_label.font()
        font.setPointSize(11)
        font.setBold(True)
        self.header_label.setFont(font)
        layout.addWidget(self.header_label)
        
        # === EDYTOR KODU ===
        self.code_editor = CodeEditor()
        self.code_editor.setObjectName("codeEditor")
        self.code_editor.setMinimumHeight(250)
        layout.addWidget(self.code_editor)
        
        # === PRZYCISKI AKCJI ===
        buttons_layout = self._create_action_buttons()
        layout.addLayout(buttons_layout)
        
        # === SEKCJA KONSOLI I BIBLIOTEK (POZIOMY PODZIAŁ) ===
        bottom_section = QHBoxLayout()
        bottom_section.setSpacing(10)
        
        # --- LEWA STRONA: KONSOLA LOGÓW ---
        logs_section = QVBoxLayout()
        
        self.logs_label = QLabel()
        self.logs_label.setObjectName("sectionHeader")
        font = self.logs_label.font()
        font.setPointSize(10)
        font.setBold(True)
        self.logs_label.setFont(font)
        logs_section.addWidget(self.logs_label)
        
        self.log_console = QTextEdit()
        self.log_console.setReadOnly(True)
        self.log_console.setMinimumHeight(200)
        font_log = QFont("Consolas", 9)
        self.log_console.setFont(font_log)
        self.log_console.setObjectName("logConsole")
        logs_section.addWidget(self.log_console)
        
        bottom_section.addLayout(logs_section, 1)  # 50% szerokości
        
        # --- PRAWA STRONA: BIBLIOTEKI ---
        libs_section = QVBoxLayout()
        
        self.libs_label = QLabel()
        self.libs_label.setObjectName("sectionHeader")
        font = self.libs_label.font()
        font.setPointSize(10)
        font.setBold(True)
        self.libs_label.setFont(font)
        libs_section.addWidget(self.libs_label)
        
        self.libs_table = QTableWidget()
        self.libs_table.setColumnCount(4)
        self.libs_table.setMinimumHeight(200)
        self.libs_table.setObjectName("libsTable")
        
        # Ustaw autodopasowanie kolumn
        header = self.libs_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
            self.libs_table.setColumnWidth(3, 100)
        
        libs_section.addWidget(self.libs_table)
        
        bottom_section.addLayout(libs_section, 1)  # 50% szerokości
        
        layout.addLayout(bottom_section)
        
        # Ustaw scroll content
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        return widget
    
    def _create_action_buttons(self) -> QHBoxLayout:
        """Tworzy przyciski akcji"""
        layout = QHBoxLayout()
        layout.setSpacing(5)
        
        # Testuj - zawsze aktywny
        self.btn_test = QPushButton()
        self.btn_test.setObjectName("btnPrimary")
        self.btn_test.clicked.connect(self._on_test_syntax)
        layout.addWidget(self.btn_test, 1)
        
        # Włącz - aktywny po teście
        self.btn_run = QPushButton()
        self.btn_run.setObjectName("btnSuccess")
        self.btn_run.clicked.connect(self._on_run_code)
        self.btn_run.setEnabled(False)
        layout.addWidget(self.btn_run, 1)
        
        # Testuj jako moduł - aktywny po teście
        self.btn_test_module = QPushButton()
        self.btn_test_module.setObjectName("btnInfo")
        self.btn_test_module.clicked.connect(self._on_test_as_module)
        self.btn_test_module.setEnabled(False)
        layout.addWidget(self.btn_test_module, 1)
        
        # Zapisz jako moduł - aktywny po teście
        self.btn_save_module = QPushButton()
        self.btn_save_module.setObjectName("btnSuccess")
        self.btn_save_module.clicked.connect(self._on_save_module)
        self.btn_save_module.setEnabled(False)
        layout.addWidget(self.btn_save_module, 1)
        
        # Zapisz jako BAT
        self.btn_save_bat = QPushButton()
        self.btn_save_bat.setObjectName("btnWarning")
        self.btn_save_bat.clicked.connect(self._on_save_bat)
        self.btn_save_bat.setEnabled(False)
        layout.addWidget(self.btn_save_bat, 1)
        
        # Zapisz jako skrypt Python
        self.btn_save_py = QPushButton()
        self.btn_save_py.setObjectName("btnInfo")
        self.btn_save_py.clicked.connect(self._on_save_python)
        self.btn_save_py.setEnabled(False)
        layout.addWidget(self.btn_save_py, 1)
        
        # Wyczyść
        self.btn_clear = QPushButton()
        self.btn_clear.clicked.connect(self._on_clear_all)
        layout.addWidget(self.btn_clear, 1)
        
        # Pomoc
        self.btn_help = QPushButton()
        self.btn_help.setObjectName("btnInfo")
        self.btn_help.clicked.connect(self._on_show_help)
        layout.addWidget(self.btn_help, 1)
        
        return layout
    
    def _log(self, message: str, color: str = "black"):
        """Dodaje wiadomość do konsoli logów"""
        self.log_console.setTextColor(QColor(color))
        self.log_console.append(message)
        cursor = self.log_console.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        self.log_console.setTextCursor(cursor)
    
    def _on_test_syntax(self):
        """Obsługa testowania składni"""
        code = self.code_editor.toPlainText().strip()
        
        if not code:
            QMessageBox.warning(self, t('proapp.error', 'Błąd'), 
                              t('proapp.editor_empty', 'Edytor jest pusty! Wklej kod do testowania.'))
            return
        
        self._log("\n" + "="*60)
        self._log(t('proapp.testing_syntax', '🔍 Testowanie składni...'), "blue")
        self._log("="*60)
        
        # Wyłącz przyciski
        self.btn_run.setEnabled(False)
        self.btn_test_module.setEnabled(False)
        self.btn_save_module.setEnabled(False)
        self.btn_save_bat.setEnabled(False)
        self.btn_save_py.setEnabled(False)
        
        # Wyczyść tabelę
        self.libs_table.setRowCount(0)
        
        # Testuj składnię
        success, error_msg = self.logic.test_syntax(code)
        
        if success:
            self._log(t('proapp.syntax_ok', '✅ Składnia poprawna!'), "green")
            
            # Wykryj importy
            imports_info = self.logic.detect_imports(code)
            self._detect_and_display_imports(imports_info)
            
            # Włącz przyciski
            self.btn_run.setEnabled(True)
            self.btn_test_module.setEnabled(True)
            self.btn_save_module.setEnabled(True)
            self.btn_save_bat.setEnabled(True)
            self.btn_save_py.setEnabled(True)
            
            self._log(t('proapp.ready_to_run', '✅ Kod gotowy do uruchomienia!'), "green")
        else:
            self._log(f"❌ {error_msg}", "red")
            QMessageBox.critical(self, t('proapp.syntax_error', 'Błąd składni'), error_msg)
    
    def _detect_and_display_imports(self, imports_info: dict):
        """Wykrywa i wyświetla informacje o importach"""
        all_imports = imports_info['all']
        available = imports_info['available']
        missing = imports_info['missing']
        
        if all_imports:
            self._log(f"\n{t('proapp.detecting_imports', '🔎 Wykrywanie bibliotek...')}", "blue")
            self._log(f"📦 {t('proapp.found_imports', 'Znaleziono')} {len(all_imports)} {t('proapp.imports', 'importów')}: {', '.join(sorted(all_imports))}", "darkblue")
            
            if available:
                self._log(f"✅ {t('proapp.available', 'Dostępne')} ({len(available)}): {', '.join(available)}", "green")
            
            if missing:
                self._log(f"❌ {t('proapp.missing', 'Brakujące')} ({len(missing)}): {', '.join(missing)}", "red")
            
            # Wypełnij tabelę
            self._populate_libs_table(all_imports, available, missing)
        else:
            self._log(f"ℹ️ {t('proapp.no_external_imports', 'Nie znaleziono importów bibliotek zewnętrznych')}", "gray")
    
    def _populate_libs_table(self, all_modules: list, available: list, missing: list):
        """Wypełnia tabelę wszystkimi bibliotekami"""
        self.libs_table.setRowCount(0)
        
        for module_name in sorted(all_modules):
            row = self.libs_table.rowCount()
            self.libs_table.insertRow(row)
            
            is_available = module_name in available
            
            # Kolumna 0: Nazwa
            name_item = QTableWidgetItem(module_name)
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            name_item.setForeground(QColor("green" if is_available else "red"))
            self.libs_table.setItem(row, 0, name_item)
            
            # Kolumna 1: Wersja
            if is_available:
                version = self.logic.get_package_version(module_name)
                version_item = QTableWidgetItem(version)
                version_item.setForeground(QColor("green"))
            else:
                version_item = QTableWidgetItem("---")
                version_item.setForeground(QColor("gray"))
            version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.libs_table.setItem(row, 1, version_item)
            
            # Kolumna 2: Status
            status_item = QTableWidgetItem("✓" if is_available else "✗")
            status_item.setForeground(QColor("green" if is_available else "red"))
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.libs_table.setItem(row, 2, status_item)
            
            # Kolumna 3: Akcja
            if is_available:
                label = QLabel(t('proapp.lib_available', '✓ Dostępna'))
                label.setStyleSheet("color: green; font-weight: bold; padding: 4px;")
                label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                self.libs_table.setCellWidget(row, 3, label)
            else:
                btn = QPushButton(t('proapp.install', '⬇️ Zainstaluj'))
                btn.setObjectName("btnSuccess")
                btn.setStyleSheet("padding: 4px;")
                btn.clicked.connect(lambda checked, m=module_name, r=row: self._install_module(m, r))
                self.libs_table.setCellWidget(row, 3, btn)
    
    def _install_module(self, module_name: str, row: int):
        """Instaluje moduł"""
        self._log(f"\n📥 {t('proapp.installing', 'Instalowanie')}: {module_name}...", "blue")
        
        success, message = self.logic.install_module(module_name)
        
        if success:
            self._log(f"✅ {message}", "green")
            
            # Aktualizuj tabelę
            version = self.logic.get_package_version(module_name)
            version_item = QTableWidgetItem(version)
            version_item.setFlags(version_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            version_item.setForeground(QColor("green"))
            self.libs_table.setItem(row, 1, version_item)
            
            status_item = QTableWidgetItem("✓")
            status_item.setForeground(QColor("green"))
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.libs_table.setItem(row, 2, status_item)
            
            btn = self.libs_table.cellWidget(row, 3)
            if btn and isinstance(btn, QPushButton):
                btn.setEnabled(False)
                btn.setText("✓ OK")
                btn.setStyleSheet("background-color: #888; color: white; padding: 4px;")
        else:
            self._log(f"❌ {message}", "red")
            QMessageBox.critical(self, t('proapp.installation_error', 'Błąd instalacji'), message)
    
    def _on_run_code(self):
        """Obsługa uruchamiania kodu"""
        code = self.code_editor.toPlainText().strip()
        
        self._log("\n" + "="*60)
        self._log(t('proapp.running_code', '▶️ Uruchamianie kodu...'), "blue")
        self._log("="*60)
        
        result = self.logic.run_code(code)
        
        if result['stdout']:
            self._log(f"\n📤 {t('proapp.output', 'Wyjście programu')}:", "green")
            self._log(result['stdout'], "black")
        
        if result['stderr']:
            if "ModuleNotFoundError" in result['stderr'] or "ImportError" in result['stderr']:
                self._log(f"\n⚠️ {t('proapp.errors', 'Błędy')}:", "orange")
            else:
                self._log(f"\n❌ {t('proapp.errors', 'Błędy')}:", "red")
            self._log(result['stderr'], "darkred")
        
        if result['success']:
            self._log(f"\n✅ {t('proapp.completed_success', 'Program zakończony pomyślnie')} (kod: 0)", "green")
        else:
            self._log(f"\n⚠️ {t('proapp.completed_error', 'Program zakończony z kodem')}: {result['returncode']}", "orange")
    
    def _on_test_as_module(self):
        """Obsługa testowania kodu jako moduł w widoku testowym"""
        code = self.code_editor.toPlainText().strip()
        
        if not code:
            QMessageBox.warning(self, t('proapp.error', 'Błąd'), 
                              t('proapp.editor_empty', 'Edytor jest pusty!'))
            return
        
        logger.info("[ProAppView] Switching to test module view")
        
        # Przełącz na widok testowy
        self.stacked_widget.setCurrentIndex(1)
        
        # Uruchom kod w widoku testowym
        self.testbox_view.run_code(code)
    
    def _return_to_editor(self):
        """Powrót do widoku edytora"""
        logger.info("[ProAppView] Returning to editor view")
        self.stacked_widget.setCurrentIndex(0)
    
    def _on_save_bat(self):
        """Obsługa zapisywania jako BAT"""
        reply = QMessageBox.question(
            self,
            t('proapp.bat_type', 'Typ pliku BAT'),
            t('proapp.bat_question', 'Czy plik .bat ma otwierać konsolę?\n\nTAK - Konsola będzie widoczna\nNIE - Program uruchomi się bez konsoli'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
        )
        
        if reply == QMessageBox.StandardButton.Cancel:
            return
        
        with_console = (reply == QMessageBox.StandardButton.Yes)
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t('proapp.save_as_bat', 'Zapisz jako plik BAT'),
            "",
            "Pliki BAT (*.bat);;Wszystkie pliki (*.*)"
        )
        
        if not file_path:
            return
        
        code = self.code_editor.toPlainText().strip()
        success, message = self.logic.save_as_bat(code, file_path, with_console)
        
        if success:
            self._log(f"\n✅ {message}", "green")
            QMessageBox.information(self, t('proapp.success', 'Sukces'), message)
        else:
            self._log(f"\n❌ {message}", "red")
            QMessageBox.critical(self, t('proapp.error', 'Błąd'), message)
    
    def _on_save_python(self):
        """Obsługa zapisywania jako Python"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t('proapp.save_as_python', 'Zapisz jako skrypt Python'),
            "",
            "Pliki Python (*.py);;Wszystkie pliki (*.*)"
        )
        
        if not file_path:
            return
        
        code = self.code_editor.toPlainText().strip()
        success, message = self.logic.save_as_python(code, file_path)
        
        if success:
            self._log(f"\n✅ {message}", "green")
            QMessageBox.information(self, t('proapp.success', 'Sukces'), message)
        else:
            self._log(f"\n❌ {message}", "red")
            QMessageBox.critical(self, t('proapp.error', 'Błąd'), message)
    
    def _on_save_module(self):
        """Obsługa zapisywania jako moduł .pro"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            t('proapp.save_as_module', 'Zapisz jako moduł Pro-App'),
            "",
            "Moduły Pro-App (*.pro);;Wszystkie pliki (*.*)"
        )
        
        if not file_path:
            return
        
        # Dodaj rozszerzenie .pro jeśli nie ma
        if not file_path.endswith('.pro'):
            file_path += '.pro'
        
        code = self.code_editor.toPlainText().strip()
        
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(code)
            
            message = t('proapp.module_saved', f'Moduł zapisany jako: {file_path}')
            self._log(f"\n✅ {message}", "green")
            QMessageBox.information(
                self, 
                t('proapp.success', 'Sukces'), 
                t('proapp.module_saved_info', f'Moduł został zapisany!\n\nŚcieżka: {file_path}\n\nMożesz teraz dodać go jako własny przycisk w Ustawieniach → Środowisko.')
            )
            logger.info(f"[ProAppView] Module saved to: {file_path}")
        except Exception as e:
            message = t('proapp.save_error', f'Błąd zapisu: {str(e)}')
            self._log(f"\n❌ {message}", "red")
            QMessageBox.critical(self, t('proapp.error', 'Błąd'), message)
            logger.error(f"[ProAppView] Error saving module: {e}")
    
    def _on_clear_all(self):
        """Obsługa czyszczenia edytora"""
        reply = QMessageBox.question(
            self,
            t('proapp.confirm', 'Potwierdzenie'),
            t('proapp.clear_confirm', 'Czy na pewno chcesz wyczyścić edytor i logi?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.code_editor.clear()
            self.log_console.clear()
            self.libs_table.setRowCount(0)
            self.logic.reset()
            
            self.btn_run.setEnabled(False)
            self.btn_save_bat.setEnabled(False)
            self.btn_save_py.setEnabled(False)
            
            self._log(t('proapp.cleared', '🗑️ Edytor i logi wyczyszczone'), "blue")
    
    def _on_show_help(self):
        """Wyświetla okno pomocy z pliku HTML"""
        import os
        import webbrowser
        from pathlib import Path
        
        try:
            # Ścieżka do pliku pomocy
            help_file = Path(__file__).parent.parent.parent / "help_files" / "pro_app.html"
            
            if not help_file.exists():
                # Fallback - pokaż podstawową pomoc w dialogu
                self._show_basic_help()
                return
            
            # Otwórz plik HTML w domyślnej przeglądarce
            webbrowser.open(help_file.as_uri())
            logger.info(f"[ProAppView] Opening help file: {help_file}")
            
        except Exception as e:
            logger.error(f"[ProAppView] Error opening help file: {e}")
            # Fallback - pokaż podstawową pomoc
            self._show_basic_help()
    
    def _show_basic_help(self):
        """Wyświetla podstawową pomoc w oknie dialogowym (fallback)"""
        from PyQt6.QtWidgets import QDialog
        
        help_text = t('proapp.help_content', """
        <h2>Pro-App - Kompilator Python</h2>
        <p>Moduł do testowania, uruchamiania i zarządzania skryptami Python.</p>
        <h3>Podstawowe funkcje:</h3>
        <ul>
            <li>🔍 <b>Testuj składnię</b> - Sprawdza poprawność kodu i wykrywa biblioteki</li>
            <li>▶️ <b>Włącz</b> - Uruchamia kod w konsoli</li>
            <li>🧪 <b>Testuj jako moduł</b> - Wyświetla widgety w widoku testowym</li>
            <li>💾 <b>Zapisz jako moduł</b> - Zapisuje kod jako plik .pro</li>
        </ul>
        <p><b>Uwaga:</b> Twój moduł musi tworzyć zmienną <code>widget</code> zawierającą instancję QWidget.</p>
        """)
        
        dialog = QDialog(self)
        dialog.setWindowTitle(t('proapp.help_title', 'Pomoc - Pro-App'))
        dialog.setMinimumSize(750, 600)
        
        layout = QVBoxLayout()
        
        text_edit = QTextEdit()
        text_edit.setReadOnly(True)
        text_edit.setHtml(help_text)
        
        ok_button = QPushButton(t('proapp.ok', 'OK'))
        ok_button.clicked.connect(dialog.accept)
        ok_button.setFixedWidth(100)
        
        layout.addWidget(text_edit)
        layout.addWidget(ok_button, 0, Qt.AlignmentFlag.AlignCenter)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def update_translations(self):
        """Aktualizuje tłumaczenia UI"""
        self.header_label.setText(t('proapp.code_editor', '📝 Edytor kodu Python'))
        self.code_editor.setPlaceholderText(t('proapp.editor_placeholder', 'Wklej tutaj kod Python do testowania...'))
        
        self.btn_test.setText(t('proapp.test_syntax', '🔍 Testuj składnię'))
        self.btn_test.setToolTip(t('proapp.test_tooltip', 'Sprawdź składnię kodu Python'))
        
        self.btn_run.setText(t('proapp.run', '▶️ Włącz'))
        self.btn_run.setToolTip(t('proapp.run_tooltip', 'Uruchom kod w konsoli'))
        
        self.btn_test_module.setText(t('proapp.test_module', '🧪 Testuj jako moduł'))
        self.btn_test_module.setToolTip(t('proapp.test_module_tooltip', 'Uruchom kod w widoku testowym aplikacji'))
        
        self.btn_save_module.setText(t('proapp.save_module', '💾 Zapisz jako moduł'))
        self.btn_save_module.setToolTip(t('proapp.save_module_tooltip', 'Zapisz kod jako moduł .pro'))
        
        self.btn_save_bat.setText(t('proapp.save_bat', '📦 Zapisz jako BAT'))
        self.btn_save_bat.setToolTip(t('proapp.save_bat_tooltip', 'Utwórz plik .bat do uruchomienia kodu'))
        
        self.btn_save_py.setText(t('proapp.save_python', '💾 Zapisz jako Python'))
        self.btn_save_py.setToolTip(t('proapp.save_python_tooltip', 'Zapisz kod jako plik .py'))
        
        self.btn_clear.setText(t('proapp.clear', '🗑️ Wyczyść'))
        self.btn_clear.setToolTip(t('proapp.clear_tooltip', 'Wyczyść edytor i logi'))
        
        self.btn_help.setText(t('proapp.help', '❓ Pomoc'))
        self.btn_help.setToolTip(t('proapp.help_tooltip', 'Wyświetl pomoc o module'))
        
        self.logs_label.setText(t('proapp.log_console', '📋 Konsola logów'))
        self.log_console.setPlaceholderText(t('proapp.log_placeholder', 'Tutaj pojawią się logi testowania i uruchamiania...'))
        
        self.libs_label.setText(t('proapp.missing_libs', '📚 Brakujące biblioteki'))
        self.libs_table.setHorizontalHeaderLabels([
            t('proapp.lib_name', 'Nazwa biblioteki'),
            t('proapp.lib_version', 'Wersja'),
            t('proapp.lib_status', '✓/✗'),
            t('proapp.lib_action', 'Akcja')
        ])
        
        logger.debug("[ProAppView] Translations updated")
    
    def apply_theme(self):
        """Zastosuj bieżący motyw"""
        # Theme manager automatycznie aplikuje style przez ObjectName
        logger.debug("[ProAppView] Theme applied")
