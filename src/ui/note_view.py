"""
Note View - Widok systemu notatek z zagnieżdżaniem
Zawiera edytor Rich Text z narzędziami formatowania
"""

import re
import logging
import platform
import ctypes
from datetime import datetime
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QTextEdit, QTreeWidget, QTreeWidgetItem,
    QSplitter, QFrame, QMessageBox, QInputDialog,
    QApplication, QDialog, QDialogButtonBox,
    QLineEdit, QFormLayout, QColorDialog, QSpinBox,
    QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import (
    QFont, QTextCursor, QTextCharFormat, QColor,
    QTextDocument, QPageSize, QTextTableFormat, 
    QTextFrameFormat, QTextLength
)
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog

# Import modułu notatek
from src.Modules.Note_module import NoteDatabase, NoteFormatter
from src.utils import get_theme_manager, get_i18n

logger = logging.getLogger(__name__)

class NoteView(QWidget):
    """Widok systemu notatek z zagnieżdżaniem"""
    
    # Sygnały
    note_created = pyqtSignal(str)  # note_id
    note_updated = pyqtSignal(str)  # note_id
    note_deleted = pyqtSignal(str)  # note_id
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Managers
        self.theme_manager = get_theme_manager()
        self.i18n = get_i18n()
        
        # Baza danych
        self.db = NoteDatabase()
        
        # Sync Manager (None jeśli offline mode)
        self.sync_manager = None
        self.sync_enabled = False
        
        # Stan aplikacji
        self.current_note_id = None
        self.current_font_size = 13  # Domyślny rozmiar czcionki
        
        self.init_ui()
        self.load_notes()
        self.apply_theme()
        
        # Połącz z sygnałem zmiany języka
        self.i18n.language_changed.connect(self.update_translations)
        
        # Synchronizacja będzie włączona przez set_user_data() z main_window
    
    def init_ui(self):
        """Inicjalizacja UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        # Główny splitter poziomy
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setChildrenCollapsible(True)
        
        # === LEWA SEKCJA - DRZEWO NOTATEK (25-30%) ===
        self.left_widget = self.create_left_panel()
        
        # === PRAWA SEKCJA - EDYTOR + NARZĘDZIA ===
        self.right_widget = self.create_right_panel()
        
        # Dodanie sekcji do splittera
        self.main_splitter.addWidget(self.left_widget)
        self.main_splitter.addWidget(self.right_widget)
        self.main_splitter.setStretchFactor(0, 1)  # Lewa 25%
        self.main_splitter.setStretchFactor(1, 3)  # Prawa 75%
        
        layout.addWidget(self.main_splitter)
        
        # Pasek szybkiego wprowadzania (na dole)
        # TODO: Integracja z quick_input_bar
    
    def create_left_panel(self) -> QWidget:
        """Tworzy lewą sekcję z drzewem notatek"""
        widget = QWidget()
        widget.setObjectName("leftPanel")  # 🎯 ID dla stylowania
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Nagłówek z przyciskiem
        header_layout = QHBoxLayout()
        
        self.title_label = QLabel("📝 " + self.i18n.t("notes.title", "Notatki"))
        self.title_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(self.title_label)
        
        header_layout.addStretch()
        
        # Status LED synchronizacji
        self.sync_status_label = QLabel("⚫")
        self.sync_status_label.setToolTip(self.i18n.t("notes.sync_offline", "Tryb offline"))
        self.sync_status_label.setFont(QFont("Arial", 16))
        header_layout.addWidget(self.sync_status_label)
        
        self.add_note_btn = QPushButton(self.i18n.t("notes.new_notebook", "Nowy notatnik"))
        self.add_note_btn.clicked.connect(self.add_new_note)
        header_layout.addWidget(self.add_note_btn)
        
        layout.addLayout(header_layout)
        
        # Pole wyszukiwania (zamiast nagłówka drzewa)
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 " + self.i18n.t("notes.search", "Szukaj..."))
        self.search_input.textChanged.connect(self.on_search_text_changed)
        self.search_input.setClearButtonEnabled(True)
        layout.addWidget(self.search_input)
        
        # Drzewo notatek
        self.notes_tree = QTreeWidget()
        self.notes_tree.setHeaderHidden(True)  # Ukryj nagłówek, mamy pole wyszukiwania
        self.notes_tree.itemClicked.connect(self.on_note_selected)
        self.notes_tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.notes_tree.customContextMenuRequested.connect(self.show_tree_context_menu)
        
        layout.addWidget(self.notes_tree)
        
        return widget
    
    def create_right_panel(self) -> QWidget:
        """Tworzy prawą sekcję z edytorem i narzędziami"""
        widget = QWidget()
        widget.setObjectName("rightPanel")  # 🎯 ID dla stylowania
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)
        
        # === Główne pole edycji ===
        editor_layout = QVBoxLayout()
        
        # Nagłówek edytora (tytuł notatki - edytowalny)
        self.editor_title = QLineEdit()
        self.editor_title.setText(self.i18n.t("notes.select_note", "Wybierz notatkę"))
        self.editor_title.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.editor_title.setPlaceholderText(self.i18n.t("notes.title_placeholder", "Wprowadź tytuł..."))
        self.editor_title.setReadOnly(True)  # Domyślnie tylko do odczytu
        self.editor_title.textChanged.connect(self.on_title_changed)
        editor_layout.addWidget(self.editor_title)
        
        # Pole tekstowe z Rich Text
        self.text_editor = QTextEdit()
        self.text_editor.setPlaceholderText(
            self.i18n.t("notes.select_note_placeholder", 
                       "Wybierz notatkę z drzewa lub utwórz nową...")
        )
        self.text_editor.textChanged.connect(self.on_text_changed)
        self.text_editor.selectionChanged.connect(self.on_selection_changed)
        self.text_editor.setEnabled(False)
        
        # 🔗 OBSŁUGA HYPERLINKÓW - zainstaluj event filter
        self.text_editor.installEventFilter(self)
        
        # 📋 MENU KONTEKSTOWE dla tabel
        self.text_editor.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.text_editor.customContextMenuRequested.connect(self.show_editor_context_menu)
        
        # Ustaw domyślną czcionkę
        font = QFont("Segoe UI", self.current_font_size)
        self.text_editor.setFont(font)
        
        editor_layout.addWidget(self.text_editor)
        layout.addLayout(editor_layout, 3)
        
        # === PASEK NARZĘDZI (prawy) ===
        self.toolbar_widget = self.create_toolbar()
        layout.addWidget(self.toolbar_widget, 0)
        
        return widget
    
    def create_toolbar(self) -> QWidget:
        """Tworzy pasek narzędzi po prawej stronie"""
        widget = QWidget()
        widget.setMaximumWidth(100)
        toolbar_layout = QVBoxLayout(widget)
        toolbar_layout.setContentsMargins(8, 5, 8, 5)
        toolbar_layout.setSpacing(8)
        
        # Tytuł paska
        self.tools_label = QLabel(self.i18n.t("notes.tools", "Narzędzia"))
        self.tools_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        self.tools_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        toolbar_layout.addWidget(self.tools_label)
        
        # GŁÓWNA FUNKCJA: Utwórz podrozdział
        self.create_subchapter_btn = QPushButton("↘")
        self.create_subchapter_btn.setToolTip(
            self.i18n.t("notes.tooltip_create_subchapter",
                       "Utwórz zagnieżdżoną notatkę z zaznaczonego tekstu")
        )
        self.create_subchapter_btn.setEnabled(False)
        self.create_subchapter_btn.setFixedSize(80, 40)
        self.create_subchapter_btn.clicked.connect(self.create_nested_note)
        toolbar_layout.addWidget(self.create_subchapter_btn)
        
        # Separator
        toolbar_layout.addWidget(self._create_separator())
        
        # Rozmiar czcionki
        font_size_layout = QVBoxLayout()
        
        self.font_increase_btn = QPushButton("🔍+")
        self.font_increase_btn.setToolTip(self.i18n.t("notes.font_size_increase", "Powiększ"))
        self.font_increase_btn.setFixedSize(80, 30)
        self.font_increase_btn.clicked.connect(self.increase_font_size)
        font_size_layout.addWidget(self.font_increase_btn)
        
        self.font_decrease_btn = QPushButton("🔍-")
        self.font_decrease_btn.setToolTip(self.i18n.t("notes.font_size_decrease", "Pomniejsz"))
        self.font_decrease_btn.setFixedSize(80, 30)
        self.font_decrease_btn.clicked.connect(self.decrease_font_size)
        font_size_layout.addWidget(self.font_decrease_btn)
        
        toolbar_layout.addLayout(font_size_layout)
        
        # Separator
        toolbar_layout.addWidget(self._create_separator())
        
        # Formatowanie podstawowe
        self.bold_btn = QPushButton("B")
        self.bold_btn.setToolTip(self.i18n.t("notes.tooltip_bold", "Pogrubienie"))
        self.bold_btn.setFixedSize(80, 30)
        self.bold_btn.setCheckable(True)
        self.bold_btn.clicked.connect(self.toggle_bold)
        toolbar_layout.addWidget(self.bold_btn)
        
        self.italic_btn = QPushButton("I")
        self.italic_btn.setToolTip(self.i18n.t("notes.tooltip_italic", "Kursywa"))
        self.italic_btn.setFixedSize(80, 30)
        self.italic_btn.setCheckable(True)
        self.italic_btn.clicked.connect(self.toggle_italic)
        toolbar_layout.addWidget(self.italic_btn)
        
        self.underline_btn = QPushButton("U")
        self.underline_btn.setToolTip(self.i18n.t("notes.tooltip_underline", "Podkreślenie"))
        self.underline_btn.setFixedSize(80, 30)
        self.underline_btn.setCheckable(True)
        self.underline_btn.clicked.connect(self.toggle_underline)
        toolbar_layout.addWidget(self.underline_btn)
        
        self.strikethrough_btn = QPushButton("S")
        self.strikethrough_btn.setToolTip(self.i18n.t("notes.tooltip_strikethrough", "Przekreślenie"))
        self.strikethrough_btn.setFixedSize(80, 30)
        self.strikethrough_btn.setCheckable(True)
        self.strikethrough_btn.clicked.connect(self.toggle_strikethrough)
        toolbar_layout.addWidget(self.strikethrough_btn)
        
        # Separator
        toolbar_layout.addWidget(self._create_separator())
        
        # Kolory
        self.text_color_btn = QPushButton("A")
        self.text_color_btn.setToolTip(self.i18n.t("notes.tooltip_text_color", "Kolor tekstu"))
        self.text_color_btn.setFixedSize(80, 30)
        self.text_color_btn.clicked.connect(self.change_text_color)
        toolbar_layout.addWidget(self.text_color_btn)
        
        self.highlight_btn = QPushButton("🖍")
        self.highlight_btn.setToolTip(self.i18n.t("notes.tooltip_highlight", "Zakreśl tekst"))
        self.highlight_btn.setFixedSize(80, 30)
        self.highlight_btn.clicked.connect(self.highlight_text)
        toolbar_layout.addWidget(self.highlight_btn)
        
        self.clear_format_btn = QPushButton("⌫")
        self.clear_format_btn.setToolTip(self.i18n.t("notes.tooltip_clear_format", "Usuń formatowanie"))
        self.clear_format_btn.setFixedSize(80, 30)
        self.clear_format_btn.clicked.connect(self.clear_formatting)
        toolbar_layout.addWidget(self.clear_format_btn)
        
        # Separator
        toolbar_layout.addWidget(self._create_separator())
        
        # Tabela
        self.insert_table_btn = QPushButton("📊")
        self.insert_table_btn.setToolTip(self.i18n.t("notes.tooltip_insert_table", "Wstaw tabelę"))
        self.insert_table_btn.setFixedSize(80, 35)
        self.insert_table_btn.clicked.connect(self.insert_table)
        toolbar_layout.addWidget(self.insert_table_btn)
        
        # Separator
        toolbar_layout.addWidget(self._create_separator())
        
    # AI, dyktowanie i drukowanie
        self.summarize_ai_btn = QPushButton("🤖")
        self.summarize_ai_btn.setToolTip(self.i18n.t("notes.tooltip_summarize_ai", "Podsumuj AI"))
        self.summarize_ai_btn.setFixedSize(80, 35)
        self.summarize_ai_btn.clicked.connect(self.summarize_with_ai)
        toolbar_layout.addWidget(self.summarize_ai_btn)
        
        self.voice_input_btn = QPushButton("🎤")
        self.voice_input_btn.setToolTip(self.i18n.t("notes.tooltip_voice_input", "Włącz dyktowanie (Win + H)"))
        self.voice_input_btn.setFixedSize(80, 35)
        self.voice_input_btn.setEnabled(False)
        self.voice_input_btn.clicked.connect(self.start_voice_input)
        toolbar_layout.addWidget(self.voice_input_btn)
        
        self.print_btn = QPushButton("🖨")
        self.print_btn.setToolTip(self.i18n.t("notes.tooltip_print", "Drukuj"))
        self.print_btn.setFixedSize(80, 35)
        self.print_btn.clicked.connect(self.print_note)
        toolbar_layout.addWidget(self.print_btn)
        
        toolbar_layout.addStretch()
        
        return widget
    
    def _create_separator(self) -> QFrame:
        """Tworzy separator poziomy"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        return separator
    
    # ==============================
    # ZARZĄDZANIE NOTATKAMI
    # ==============================
    
    def load_notes(self):
        """Ładuje notatki z bazy danych"""
        all_notes = self.db.get_all_notes()
        
        if not all_notes:
            # Utwórz przykładową notatkę
            self.create_sample_note()
            all_notes = self.db.get_all_notes()
        
        self.refresh_tree()
    
    def create_sample_note(self):
        """Tworzy przykładową notatkę"""
        note_id = self.db.create_note(
            title="Witaj w systemie notatek!",
            content="<p>To jest Twoja pierwsza notatka.</p>"
                   "<p><b>Zaznacz ten tekst</b> i kliknij strzałkę '↘' aby utworzyć zagnieżdżoną notatkę!</p>"
                   "<p>Możesz formatować tekst, zmieniać kolory i wiele więcej.</p>"
        )
        
        # Dodaj przykładową podnotatkę
        child_id = self.db.create_note(
            title="Przykład zagnieżdżonej notatki",
            content="<p>Ta notatka została utworzona jako podnotatka.</p>"
                   "<p>Możesz tworzyć wiele poziomów zagnieżdżenia!</p>",
            parent_id=note_id,
            color="#e3f2fd"
        )
    
    def refresh_tree(self):
        """Odświeża drzewo notatek"""
        self.notes_tree.clear()
        
        # Pobierz notatki główne (bez rodzica)
        root_notes = self.db.get_children(None)
        
        for note in root_notes:
            self.add_note_to_tree(note['id'], None)
    
    def add_note_to_tree(self, note_id: str, parent_item: Optional[QTreeWidgetItem] = None):
        """Dodaje notatkę do drzewa rekurencyjnie"""
        note = self.db.get_note(note_id)
        if not note:
            return
        
        # Utwórz element drzewa
        if parent_item:
            item = QTreeWidgetItem(parent_item)
        else:
            item = QTreeWidgetItem(self.notes_tree)
        
        # Ustaw tekst i ikonę
        icon = "📘" if note.get('parent_id') is None else "📑"
        item.setText(0, f"{icon} {note['title']}")
        item.setData(0, Qt.ItemDataRole.UserRole, note_id)
        
        # Ustaw kolor czcionki (zamiast tła)
        color = QColor(note.get('color', '#1976D2'))  # Domyślny niebieski
        item.setForeground(0, color)
        
        # Pogrub czcionkę
        font = item.font(0)
        font.setBold(True)
        font.setPointSize(11)
        item.setFont(0, font)
        
        # Dodaj dzieci rekurencyjnie
        children = self.db.get_children(note_id)
        for child in children:
            self.add_note_to_tree(child['id'], item)
        
        item.setExpanded(True)
    
    def on_note_selected(self, item: QTreeWidgetItem):
        """Obsługuje wybór notatki z drzewa"""
        note_id = item.data(0, Qt.ItemDataRole.UserRole)
        note = self.db.get_note(note_id)
        
        if note:
            self.current_note_id = note_id
            
            # Aktualizuj tytuł - blokuj sygnały podczas ładowania
            self.editor_title.blockSignals(True)
            self.editor_title.setText(note['title'])
            self.editor_title.setReadOnly(False)  # Włącz edycję tytułu
            self.editor_title.blockSignals(False)
            
            # Aktualizuj treść (HTML)
            self.text_editor.blockSignals(True)
            self.text_editor.setHtml(note['content'] or "")
            self.text_editor.blockSignals(False)
            
            # Włącz edycję
            self.text_editor.setEnabled(True)
            if hasattr(self, "voice_input_btn"):
                self.voice_input_btn.setEnabled(True)
    
    def on_title_changed(self):
        """Obsługuje zmianę tytułu - automatyczny zapis"""
        if not self.current_note_id:
            return
        
        # Zapisz tytuł z debounce
        if not hasattr(self, '_title_save_timer'):
            self._title_save_timer = QTimer()
            self._title_save_timer.setSingleShot(True)
            self._title_save_timer.timeout.connect(self.save_current_note_title)
        
        self._title_save_timer.stop()
        self._title_save_timer.start(1000)
    
    def on_text_changed(self):
        """Obsługuje zmiany tekstu - automatyczny zapis"""
        if not self.current_note_id:
            return
        
        # Zapisz HTML
        content = self.text_editor.toHtml()
        
        # Debounce - zapisz po 1 sekundzie bezczynności
        if not hasattr(self, '_save_timer'):
            self._save_timer = QTimer()
            self._save_timer.setSingleShot(True)
            self._save_timer.timeout.connect(self.save_current_note)
        
        self._save_timer.stop()
        self._save_timer.start(1000)
    
    def save_current_note_title(self):
        """Zapisuje tytuł bieżącej notatki do bazy"""
        if not self.current_note_id:
            return
        
        title = self.editor_title.text().strip()
        if title:
            self.db.update_note(self.current_note_id, title=title)
            self.refresh_tree()
            self.note_updated.emit(self.current_note_id)
    
    def save_current_note(self):
        """Zapisuje bieżącą notatkę do bazy"""
        if not self.current_note_id:
            return
        
        content = self.text_editor.toHtml()
        self.db.update_note(self.current_note_id, content=content)
        self.note_updated.emit(self.current_note_id)
    
    def on_selection_changed(self):
        """Obsługuje zmianę zaznaczenia - włącz/wyłącz przycisk podrozdział"""
        cursor = self.text_editor.textCursor()
        has_selection = cursor.hasSelection()
        self.create_subchapter_btn.setEnabled(has_selection and self.current_note_id is not None)
        
        # Aktualizuj stan przycisków formatowania
        self.update_format_buttons()
    
    def update_format_buttons(self):
        """Aktualizuje stan przycisków formatowania na podstawie bieżącego formatu"""
        cursor = self.text_editor.textCursor()
        fmt = cursor.charFormat()
        
        self.bold_btn.setChecked(fmt.fontWeight() == QFont.Weight.Bold)
        self.italic_btn.setChecked(fmt.fontItalic())
        self.underline_btn.setChecked(fmt.fontUnderline())
        # PyQt6 nie ma bezpośredniego fontStrikeOut, użyj textDecoration
    
    def eventFilter(self, a0, a1):
        """🔗 OBSŁUGA HYPERLINKÓW - przechwyć kliknięcia myszą w edytorze"""
        from PyQt6.QtCore import QEvent
        from PyQt6.QtGui import QMouseEvent
        import re
        
        # Sprawdź czy to kliknięcie myszą w edytorze tekstu
        if a0 == self.text_editor and a1 is not None and a1.type() == QEvent.Type.MouseButtonPress:
            # Sprawdź czy to rzeczywiście QMouseEvent
            if isinstance(a1, QMouseEvent) and a1.button() == Qt.MouseButton.LeftButton:
                try:
                    print(f"� [DEBUG] Mouse click detected in text editor")
                    
                    # Sprawdź aktualny kursor i jego format
                    cursor = self.text_editor.textCursor()
                    fmt = cursor.charFormat()
                    
                    print(f"🔗 [DEBUG] Current cursor position: {cursor.position()}")
                    print(f"🔗 [DEBUG] Format isAnchor: {fmt.isAnchor()}")
                    
                    if fmt.isAnchor():
                        anchor_href = fmt.anchorHref()
                        print(f"🔗 [DEBUG] Found anchor: {anchor_href}")
                        
                        if anchor_href.startswith("note://"):
                            try:
                                note_id = int(anchor_href.replace("note://", ""))
                                print(f"🔗 [DEBUG] Navigating to note: {note_id}")
                                self.navigate_to_note(note_id)
                                return True  # Przechwycone
                            except ValueError:
                                print(f"⚠️ Nieprawidłowy format linku: {anchor_href}")
                    else:
                        # 🔄 BACKUP APPROACH: Sprawdź HTML content dla linków note://
                        html_content = self.text_editor.toHtml()
                        note_links = re.findall(r'<a href="note://(\d+)"[^>]*>([^<]+)</a>', html_content)
                        print(f"🔗 [DEBUG] Found {len(note_links)} note links in HTML")
                        
                        if note_links:
                            print(f"🔗 [DEBUG] Available links: {note_links}")
                            # Dla uproszczenia testowego - gdy brak anchor detection, użyj pierwszego linku
                            if len(note_links) == 1:
                                note_id = int(note_links[0][0])
                                print(f"🔗 [DEBUG] Using first link as fallback: {note_id}")
                                self.navigate_to_note(note_id)
                                return True
                                
                except Exception as e:
                    print(f"⚠️ Błąd obsługi kliknięcia na link: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Przekaż zdarzenie dalej
        return super().eventFilter(a0, a1)
    
    def navigate_to_note(self, note_id: int):
        """🔗 NAWIGACJA DO NOTATKI - przejdź do wskazanej notatki"""
        try:
            # Sprawdź czy notatka istnieje (konwertuj int na str)
            note = self.db.get_note(str(note_id))
            if not note:
                print(f"⚠️ Notatka o ID {note_id} nie istnieje")
                return
            
            # Znajdź item w drzewie i zaznacz go
            def find_note_item(parent_item, target_id):
                """Rekursywnie znajdź item notatki w drzewie"""
                if parent_item is None:
                    return None
                    
                for i in range(parent_item.childCount()):
                    child = parent_item.child(i)
                    if child and child.data(0, Qt.ItemDataRole.UserRole) == str(target_id):
                        return child
                    # Sprawdź dzieci
                    found = find_note_item(child, target_id)
                    if found:
                        return found
                return None
            
            # Szukaj w root items
            target_item = None
            for i in range(self.notes_tree.topLevelItemCount()):
                root_item = self.notes_tree.topLevelItem(i)
                if root_item and root_item.data(0, Qt.ItemDataRole.UserRole) == str(note_id):
                    target_item = root_item
                    break
                # Sprawdź dzieci
                found = find_note_item(root_item, note_id)
                if found:
                    target_item = found
                    break
            
            if target_item:
                # Rozwiń ścieżkę do notatki
                parent = target_item.parent()
                while parent:
                    parent.setExpanded(True)
                    parent = parent.parent()
                
                # Zaznacz i przewiń do notatki
                self.notes_tree.setCurrentItem(target_item)
                self.notes_tree.scrollToItem(target_item)
                
                print(f"✅ Przejście do notatki: {note['title']}")
            else:
                print(f"⚠️ Nie znaleziono notatki {note_id} w drzewie")
                
        except Exception as e:
            print(f"❌ Błąd nawigacji do notatki {note_id}: {e}")
    
    # ==============================
    # TWORZENIE I USUWANIE NOTATEK
    # ==============================
    
    def add_new_note(self):
        """Dodaje nową główną notatkę"""
        title, ok = QInputDialog.getText(
            self,
            self.i18n.t("notes.dialog_title_new", "Nowa notatka"),
            self.i18n.t("notes.title_edit", "Tytuł notatki") + ":"
        )
        
        if ok and title.strip():
            note_id = self.db.create_note(
                title=title.strip(),
                content="<p></p>",
                color="#1976D2"  # Niebieski dla głównych notatek
            )
            
            self.refresh_tree()
            self.note_created.emit(note_id)
            
            # Wybierz nowo utworzoną notatkę
            self.select_note_in_tree(note_id)
    
    def create_nested_note(self):
        """Tworzy zagnieżdżoną notatkę z zaznaczonego tekstu"""
        if not self.current_note_id:
            return
        
        cursor = self.text_editor.textCursor()
        if not cursor.hasSelection():
            QMessageBox.warning(
                self,
                self.i18n.t("notes.no_selection", "Brak zaznaczenia"),
                self.i18n.t("notes.no_selection_message", 
                           "Najpierw zaznacz tekst, który ma stać się nową notatką.")
            )
            return
        
        selected_text = cursor.selectedText()
        if not selected_text.strip():
            QMessageBox.warning(
                self,
                self.i18n.t("notes.empty_text", "Pusty tekst"),
                self.i18n.t("notes.empty_text_message", "Zaznaczony tekst jest pusty.")
            )
            return
        
        # 🔧 FIX: Pobierz pozycje PRZED wstawieniem HTML
        start_pos = cursor.selectionStart()
        end_pos = cursor.selectionEnd()
        
        # Utwórz tytuł (skróć jeśli za długi)
        title = selected_text.strip()[:50]
        if len(selected_text.strip()) > 50:
            title += "..."
        
        # Utwórz podnotatkę
        child_note_id = self.db.create_note(
            title=title,
            content=f"<p>{selected_text}</p>",
            parent_id=self.current_note_id,
            color="#7B1FA2"  # Fioletowy dla podnotatek
        )
        
        # Zamień zaznaczony tekst na hiperłącze
        # Format: <a href="note://note_id">tekst</a>
        link_html = f'<a href="note://{child_note_id}" style="color: #1976D2; text-decoration: underline;">{selected_text}</a>'
        cursor.insertHtml(link_html)
        self.db.create_link(
            source_note_id=self.current_note_id,
            target_note_id=child_note_id,
            link_text=selected_text,
            start_pos=start_pos,
            end_pos=end_pos
        )
        
        # Odśwież drzewo
        self.refresh_tree()
        self.note_created.emit(child_note_id)
        
        QMessageBox.information(
            self,
            self.i18n.t("notes.note_created", "Notatka utworzona"),
            f"{self.i18n.t('notes.note_created', 'Notatka utworzona')}: {title}"
        )
    
    def select_note_in_tree(self, note_id: str):
        """Wybiera notatkę w drzewie"""
        def find_item(item: Optional[QTreeWidgetItem] = None, target_id: str = ""):
            if not item:
                return None
            if item.data(0, Qt.ItemDataRole.UserRole) == target_id:
                return item
            for i in range(item.childCount()):
                child = item.child(i)
                if child:
                    found = find_item(child, target_id)
                    if found:
                        return found
            return None
        
        # Szukaj w elementach głównych
        for i in range(self.notes_tree.topLevelItemCount()):
            item = self.notes_tree.topLevelItem(i)
            if item:
                found = find_item(item, note_id)
                if found:
                    self.notes_tree.setCurrentItem(found)
                    self.on_note_selected(found)
                    break
    
    # ==============================
    # WYSZUKIWANIE
    # ==============================
    
    def on_search_text_changed(self, text: str):
        """Obsługuje zmianę tekstu w polu wyszukiwania"""
        search_query = text.strip()
        
        if not search_query:
            # Brak tekstu - pokaż drzewo hierarchiczne
            self.refresh_tree()
        else:
            # Są znaki - pokaż wyniki wyszukiwania jako płaską listę
            self.display_search_results(search_query)
    
    def display_search_results(self, query: str):
        """Wyświetla wyniki wyszukiwania jako płaską listę"""
        self.notes_tree.clear()
        
        # Wyszukaj notatki
        results = self.db.search_notes(query)
        
        if not results:
            # Brak wyników
            item = QTreeWidgetItem(self.notes_tree)
            item.setText(0, "🔍 " + self.i18n.t("notes.no_results", "Brak wyników"))
            item.setDisabled(True)
            return
        
        # Wyświetl wyniki jako płaską listę
        for note in results:
            item = QTreeWidgetItem(self.notes_tree)
            
            # Ikona zależna od tego czy to główna notatka czy podnotatka
            icon = "📘" if note.get('parent_id') is None else "📑"
            
            # Pokaż tytuł i fragment treści
            title = note['title']
            # Usuń tagi HTML z treści dla podglądu
            content_preview = re.sub('<[^<]+?>', '', note.get('content', ''))[:50]
            if len(content_preview) == 50:
                content_preview += "..."
            
            item.setText(0, f"{icon} {title}")
            if content_preview.strip():
                item.setToolTip(0, content_preview)
            
            item.setData(0, Qt.ItemDataRole.UserRole, note['id'])
            
            # Ustaw kolor czcionki
            color = QColor(note.get('color', '#1976D2'))
            item.setForeground(0, color)
            
            # Pogrub czcionkę
            font = item.font(0)
            font.setBold(True)
            font.setPointSize(11)
            item.setFont(0, font)
    
    # ==============================
    # MENU KONTEKSTOWE
    # ==============================
    
    def show_tree_context_menu(self, position):
        """Pokazuje menu kontekstowe dla drzewa"""
        item = self.notes_tree.itemAt(position)
        if not item:
            return
        
        menu = QMenu()
        
        # Akcje - bez duplikacji emoji (emoji są już w ikonach tekstowych)
        edit_action = menu.addAction(self.i18n.t("notes.edit_note", "Edytuj notatkę"))
        color_action = menu.addAction(self.i18n.t("notes.change_color", "Zmień kolor"))
        menu.addSeparator()
        add_child_action = menu.addAction(self.i18n.t("notes.add_child", "Dodaj podnotatkę"))
        menu.addSeparator()
        delete_action = menu.addAction(self.i18n.t("notes.delete_note", "Usuń notatkę"))
        
        action = menu.exec(self.notes_tree.mapToGlobal(position))
        
        note_id = item.data(0, Qt.ItemDataRole.UserRole)
        
        if action == edit_action:
            self.edit_note_title(note_id)
        elif action == color_action:
            self.change_note_color(note_id)
        elif action == delete_action:
            self.delete_note(note_id)
        elif action == add_child_action:
            self.add_child_note(note_id)
    
    def edit_note_title(self, note_id: str):
        """Edytuje tytuł notatki"""
        note = self.db.get_note(note_id)
        if not note:
            return
        
        title, ok = QInputDialog.getText(
            self,
            self.i18n.t("notes.dialog_title_edit", "Edytuj notatkę"),
            self.i18n.t("notes.title_edit", "Tytuł notatki") + ":",
            text=note['title']
        )
        
        if ok and title.strip():
            self.db.update_note(note_id, title=title.strip())
            self.refresh_tree()
            
            # Zaktualizuj tytuł w edytorze jeśli to bieżąca notatka
            if note_id == self.current_note_id:
                self.editor_title.setText(title.strip())
    
    def change_note_color(self, note_id: str):
        """Zmienia kolor notatki w drzewie"""
        note = self.db.get_note(note_id)
        if not note:
            return
        
        current_color = QColor(note.get('color', '#1976D2'))  # Domyślny niebieski
        
        color = QColorDialog.getColor(
            current_color,
            self,
            self.i18n.t("notes.choose_note_color", "Wybierz kolor notatki")
        )
        
        if color.isValid():
            # Zapisz nowy kolor do bazy
            self.db.update_note(note_id, color=color.name())
            
            # Odśwież drzewo
            self.refresh_tree()
            
            # Zawsze zaznacz tę notatkę po zmianie koloru
            # (bez względu na to, czy była zaznaczona wcześniej)
            self.select_note_in_tree(note_id)
    
    def delete_note(self, note_id: str):
        """Usuwa notatkę"""
        note = self.db.get_note(note_id)
        if not note:
            return
        
        # Sprawdź czy ma dzieci
        children = self.db.get_children(note_id)
        
        if children:
            # Ostrzeżenie o usunięciu z dziećmi
            reply = QMessageBox.question(
                self,
                self.i18n.t("notes.has_children", "Notatka ma podnotatki"),
                self.i18n.t("notes.delete_with_children", 
                           "Ta notatka ma {count} podnotatek. Usunięcie spowoduje również usunięcie wszystkich zagnieżdżonych notatek. Kontynuować?").format(count=len(children)),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        else:
            # Potwierdzenie usunięcia
            reply = QMessageBox.question(
                self,
                self.i18n.t("notes.delete_confirm", "Usuń notatkę"),
                f"{self.i18n.t('notes.delete_confirm', 'Usuń notatkę')}: {note['title']}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        # Usuń notatkę
        self.db.delete_note(note_id, soft=True)
        
        # Jeśli to bieżąca notatka, wyczyść edytor
        if note_id == self.current_note_id:
            self.current_note_id = None
            self.editor_title.setText(self.i18n.t("notes.select_note", "Wybierz notatkę"))
            self.text_editor.clear()
            self.text_editor.setEnabled(False)
            if hasattr(self, "voice_input_btn"):
                self.voice_input_btn.setEnabled(False)
        
        self.refresh_tree()
        self.note_deleted.emit(note_id)
    
    def add_child_note(self, parent_id: str):
        """Dodaje podnotatkę"""
        title, ok = QInputDialog.getText(
            self,
            self.i18n.t("notes.add_child", "Dodaj podnotatkę"),
            self.i18n.t("notes.title_edit", "Tytuł notatki") + ":"
        )
        
        if ok and title.strip():
            note_id = self.db.create_note(
                title=title.strip(),
                content="<p></p>",
                parent_id=parent_id,
                color="#7B1FA2"  # Fioletowy dla podnotatek
            )
            
            self.refresh_tree()
            self.note_created.emit(note_id)
            self.select_note_in_tree(note_id)
    
    # ==============================
    # FORMATOWANIE TEKSTU
    # ==============================
    
    def increase_font_size(self):
        """Powiększa czcionkę"""
        self.current_font_size += 2
        if self.current_font_size > 72:
            self.current_font_size = 72
        
        cursor = self.text_editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontPointSize(self.current_font_size)
            cursor.setCharFormat(fmt)
        else:
            font = self.text_editor.font()
            font.setPointSize(self.current_font_size)
            self.text_editor.setFont(font)
    
    def decrease_font_size(self):
        """Pomniejsza czcionkę"""
        self.current_font_size -= 2
        if self.current_font_size < 8:
            self.current_font_size = 8
        
        cursor = self.text_editor.textCursor()
        if cursor.hasSelection():
            fmt = cursor.charFormat()
            fmt.setFontPointSize(self.current_font_size)
            cursor.setCharFormat(fmt)
        else:
            font = self.text_editor.font()
            font.setPointSize(self.current_font_size)
            self.text_editor.setFont(font)
    
    def toggle_bold(self):
        """Przełącza pogrubienie"""
        cursor = self.text_editor.textCursor()
        fmt = cursor.charFormat()
        
        if fmt.fontWeight() == QFont.Weight.Bold:
            fmt.setFontWeight(QFont.Weight.Normal)
        else:
            fmt.setFontWeight(QFont.Weight.Bold)
        
        cursor.setCharFormat(fmt)
        self.text_editor.setTextCursor(cursor)
    
    def toggle_italic(self):
        """Przełącza kursywę"""
        cursor = self.text_editor.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontItalic(not fmt.fontItalic())
        cursor.setCharFormat(fmt)
        self.text_editor.setTextCursor(cursor)
    
    def toggle_underline(self):
        """Przełącza podkreślenie"""
        cursor = self.text_editor.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontUnderline(not fmt.fontUnderline())
        cursor.setCharFormat(fmt)
        self.text_editor.setTextCursor(cursor)
    
    def toggle_strikethrough(self):
        """Przełącza przekreślenie"""
        cursor = self.text_editor.textCursor()
        fmt = cursor.charFormat()
        fmt.setFontStrikeOut(not fmt.fontStrikeOut())
        cursor.setCharFormat(fmt)
        self.text_editor.setTextCursor(cursor)
    
    def change_text_color(self):
        """Zmienia kolor tekstu"""
        color = QColorDialog.getColor(
            QColor("#000000"),
            self,
            self.i18n.t("notes.choose_text_color", "Wybierz kolor tekstu")
        )
        
        if color.isValid():
            cursor = self.text_editor.textCursor()
            fmt = cursor.charFormat()
            fmt.setForeground(color)
            cursor.setCharFormat(fmt)
            self.text_editor.setTextCursor(cursor)
    
    def highlight_text(self):
        """Zakreśla tekst"""
        color = QColorDialog.getColor(
            QColor("#ffff00"),
            self,
            self.i18n.t("notes.choose_highlight_color", "Wybierz kolor zakreślenia")
        )
        
        if color.isValid():
            cursor = self.text_editor.textCursor()
            fmt = cursor.charFormat()
            fmt.setBackground(color)
            cursor.setCharFormat(fmt)
            self.text_editor.setTextCursor(cursor)
    
    def clear_formatting(self):
        """Usuwa formatowanie z zaznaczonego tekstu"""
        cursor = self.text_editor.textCursor()
        if cursor.hasSelection():
            fmt = QTextCharFormat()
            cursor.setCharFormat(fmt)
            self.text_editor.setTextCursor(cursor)
    
    # ==============================
    # FUNKCJE SPECJALNE
    # ==============================
    
    def summarize_with_ai(self):
        """Generuje podsumowanie notatki za pomocą AI"""
        if not self.current_note_id:
            QMessageBox.warning(
                self,
                self.i18n.t("common.warning", "Ostrzeżenie"),
                self.i18n.t("notes.select_note_first", "Najpierw wybierz notatkę!")
            )
            return
        
        # Pobierz treść notatki (HTML)
        content = self.text_editor.toHtml()
        
        if not content.strip():
            QMessageBox.warning(
                self,
                self.i18n.t("common.warning", "Ostrzeżenie"),
                self.i18n.t("notes.empty_note", "Notatka jest pusta!")
            )
            return
        
        # Użyj nowego connectora AI
        from src.Modules.Note_module.ai_note_connector import execute_ai_summarization
        execute_ai_summarization(self, content, self.current_note_id)
    
    def start_voice_input(self):
        """Wstawia znacznik i wywołuje systemowe dyktowanie (Win+H)"""
        if not self.current_note_id:
            QMessageBox.warning(
                self,
                self.i18n.t("common.warning", "Ostrzeżenie"),
                self.i18n.t("notes.select_note_first", "Najpierw wybierz notatkę!")
            )
            return
        
        self.text_editor.setFocus()
        cursor = self.text_editor.textCursor()
        marker = self.i18n.t("notes.voice_marker", "🎤 Dyktuj: ")
        cursor.insertText(marker)
        self.text_editor.setTextCursor(cursor)
        self._trigger_voice_typing_shortcut()
    
    def print_note(self):
        """Drukuje notatkę"""
        if not self.current_note_id:
            return
        
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            document = self.text_editor.document()
            if document:
                document.print(printer)
    
    def _trigger_voice_typing_shortcut(self):
        """Wyzwala systemowy skrót Win+H dla dyktowania na Windows"""
        if platform.system().lower() != "windows":
            QMessageBox.information(
                self,
                self.i18n.t("common.information", "Informacja"),
                self.i18n.t("notes.voice_unsupported", "Dyktowanie Win+H jest dostępne tylko w systemie Windows.")
            )
            return
        
        try:
            user32 = ctypes.windll.user32
            KEYEVENTF_KEYUP = 0x0002
            VK_LWIN = 0x5B
            VK_H = 0x48
            # Przytrzymaj Win, naciśnij H, a następnie zwolnij klawisze
            user32.keybd_event(VK_LWIN, 0, 0, 0)
            user32.keybd_event(VK_H, 0, 0, 0)
            user32.keybd_event(VK_H, 0, KEYEVENTF_KEYUP, 0)
            user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)
            logger.info("[NOTES] Win+H shortcut triggered for voice input")
        except AttributeError:
            QMessageBox.warning(
                self,
                self.i18n.t("common.warning", "Ostrzeżenie"),
                self.i18n.t("notes.voice_unsupported", "Dyktowanie Win+H jest dostępne tylko w systemie Windows.")
            )
        except Exception as exc:
            logger.error(f"[NOTES] Voice typing shortcut failed: {exc}")
            QMessageBox.warning(
                self,
                self.i18n.t("common.warning", "Ostrzeżenie"),
                self.i18n.t("notes.voice_trigger_failed", "Nie udało się uruchomić dyktowania.")
            )
    
    # ==============================
    # OBSŁUGA TABEL
    # ==============================
    
    def insert_table(self):
        """Wstawia tabelę HTML do notatki"""
        if not self.current_note_id:
            return
        
        # Dialog pytający o wymiary tabeli
        dialog = QDialog(self)
        dialog.setWindowTitle(self.i18n.t("notes.insert_table", "Wstaw tabelę"))
        dialog.setMinimumWidth(300)
        
        layout = QFormLayout(dialog)
        
        # Liczba wierszy
        rows_spin = QSpinBox()
        rows_spin.setMinimum(1)
        rows_spin.setMaximum(50)
        rows_spin.setValue(3)
        layout.addRow(self.i18n.t("notes.table_rows", "Liczba wierszy:"), rows_spin)
        
        # Liczba kolumn
        cols_spin = QSpinBox()
        cols_spin.setMinimum(1)
        cols_spin.setMaximum(20)
        cols_spin.setValue(3)
        layout.addRow(self.i18n.t("notes.table_cols", "Liczba kolumn:"), cols_spin)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            rows = rows_spin.value()
            cols = cols_spin.value()
            
            # Użyj QTextTable zamiast HTML dla lepszej kontroli
            cursor = self.text_editor.textCursor()
            
            # Formatowanie tabeli
            table_format = QTextTableFormat()
            table_format.setBorderStyle(QTextFrameFormat.BorderStyle.BorderStyle_Solid)
            table_format.setBorder(1)
            table_format.setCellPadding(8)
            table_format.setCellSpacing(0)
            table_format.setWidth(QTextLength(QTextLength.Type.PercentageLength, 100))
            
            # Wstaw tabelę
            table = cursor.insertTable(rows, cols, table_format)
            
            if table:
                # Ustaw nagłówki w pierwszym wierszu
                for col in range(cols):
                    cell = table.cellAt(0, col)
                    cell_cursor = cell.firstCursorPosition()
                    
                    # Formatowanie nagłówka
                    header_format = QTextCharFormat()
                    header_format.setFontWeight(QFont.Weight.Bold)
                    header_format.setBackground(QColor("#f0f0f0"))
                    
                    cell_cursor.setCharFormat(header_format)
                    cell_cursor.insertText(f"Kolumna {col + 1}")
                
                logger.info(f"Wstawiono tabelę QTextTable {rows}x{cols}")
    
    def _generate_table_html(self, rows: int, cols: int) -> str:
        """Generuje HTML tabeli z możliwością regulacji szerokości kolumn"""
        # Szerokość kolumny w procentach
        col_width_pct = 100 // cols
        
        # Styl tabeli - USUNIĘTY table-layout: fixed, dodana możliwość resize
        table_style = """
            border-collapse: collapse;
            width: 100%;
            margin: 10px 0;
        """
        
        # Styl dla kolumn z możliwością resize
        col_style = f"""
            width: {col_width_pct}%;
            resize: horizontal;
            overflow: auto;
        """
        
        cell_style = """
            border: 1px solid #666;
            padding: 8px;
            min-height: 20px;
            min-width: 50px;
            vertical-align: top;
            position: relative;
        """
        
        header_style = """
            border: 1px solid #666;
            padding: 8px;
            background-color: #f0f0f0;
            font-weight: bold;
            min-height: 20px;
            min-width: 50px;
            vertical-align: top;
            position: relative;
            resize: horizontal;
            overflow: auto;
        """
        
        html = f'<table style="{table_style}" class="editable-table" border="1" cellpadding="5" cellspacing="0">\n'
        
        # Definicja szerokości kolumn
        html += "  <colgroup>\n"
        for col in range(cols):
            html += f'    <col style="width: {col_width_pct}%;" />\n'
        html += "  </colgroup>\n"
        
        # Pierwszy wiersz jako nagłówek
        html += "  <thead>\n    <tr>\n"
        for col in range(cols):
            html += f'      <th style="{header_style}">Kolumna {col + 1}</th>\n'
        html += "    </tr>\n  </thead>\n"
        
        # Pozostałe wiersze
        html += "  <tbody>\n"
        for row in range(1, rows):
            html += "    <tr>\n"
            for col in range(cols):
                html += f'      <td style="{cell_style}">&nbsp;</td>\n'
            html += "    </tr>\n"
        html += "  </tbody>\n"
        
        html += "</table>\n<p><br/></p>\n"  # Dodaj pusty akapit po tabeli
        
        return html
    
    def show_editor_context_menu(self, position):
        """Pokazuje menu kontekstowe dla edytora"""
        cursor = self.text_editor.textCursor()
        
        # Sprawdź, czy kursor jest w QTextTable (natywna tabela Qt)
        current_table = cursor.currentTable()
        
        menu = QMenu(self)
        
        if current_table is not None:
            # Menu dla natywnej tabeli Qt
            current_cell = current_table.cellAt(cursor)
            row = current_cell.row()
            col = current_cell.column()
            
            add_row_above = menu.addAction(self.i18n.t("notes.table_add_row_above", "➕ Dodaj wiersz powyżej"))
            add_row_below = menu.addAction(self.i18n.t("notes.table_add_row_below", "➕ Dodaj wiersz poniżej"))
            add_col_left = menu.addAction(self.i18n.t("notes.table_add_col_left", "➕ Dodaj kolumnę z lewej"))
            add_col_right = menu.addAction(self.i18n.t("notes.table_add_col_right", "➕ Dodaj kolumnę z prawej"))
            menu.addSeparator()
            delete_row = menu.addAction(self.i18n.t("notes.table_delete_row", "🗑️ Usuń wiersz"))
            delete_col = menu.addAction(self.i18n.t("notes.table_delete_col", "🗑️ Usuń kolumnę"))
            menu.addSeparator()
            delete_table = menu.addAction(self.i18n.t("notes.table_delete", "🗑️ Usuń całą tabelę"))
            
            action = menu.exec(self.text_editor.mapToGlobal(position))
            
            if action == add_row_above:
                current_table.insertRows(row, 1)
            elif action == add_row_below:
                current_table.insertRows(row + 1, 1)
            elif action == add_col_left:
                current_table.insertColumns(col, 1)
            elif action == add_col_right:
                current_table.insertColumns(col + 1, 1)
            elif action == delete_row:
                if current_table.rows() > 1:
                    current_table.removeRows(row, 1)
                else:
                    QMessageBox.warning(self, "Błąd", "Nie można usunąć ostatniego wiersza!")
            elif action == delete_col:
                if current_table.columns() > 1:
                    current_table.removeColumns(col, 1)
                else:
                    QMessageBox.warning(self, "Błąd", "Nie można usunąć ostatniej kolumny!")
            elif action == delete_table:
                self._delete_qt_table(cursor, current_table)
        else:
            # Sprawdź, czy jesteśmy w tabeli HTML
            html = self.text_editor.toHtml()
            cursor_pos = cursor.position()
            in_html_table = self._is_cursor_in_html_table(cursor_pos, html)
            
            if in_html_table:
                # Menu dla tabeli HTML
                add_row_below = menu.addAction(self.i18n.t("notes.table_add_row_below", "➕ Dodaj wiersz poniżej"))
                add_col_right = menu.addAction(self.i18n.t("notes.table_add_col_right", "➕ Dodaj kolumnę z prawej"))
                menu.addSeparator()
                delete_table = menu.addAction(self.i18n.t("notes.table_delete", "🗑️ Usuń całą tabelę"))
                
                action = menu.exec(self.text_editor.mapToGlobal(position))
                
                if action == add_row_below:
                    self._add_table_row(cursor, above=False)
                elif action == add_col_right:
                    self._add_table_column(cursor, left=False)
                elif action == delete_table:
                    self._delete_table(cursor)
            else:
                # Standardowe menu kontekstowe
                std_menu = self.text_editor.createStandardContextMenu()
                if std_menu:
                    std_menu.exec(self.text_editor.mapToGlobal(position))
    
    def _delete_qt_table(self, cursor: QTextCursor, table):
        """Usuwa natywną tabelę QTextTable"""
        reply = QMessageBox.question(
            self,
            self.i18n.t("notes.table_delete", "Usuń tabelę"),
            self.i18n.t("notes.table_delete_confirm", "Czy na pewno chcesz usunąć tę tabelę?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Zaznacz całą tabelę i usuń
            cursor.beginEditBlock()
            
            # Przenieś kursor na początek tabeli
            first_cell = table.cellAt(0, 0)
            cursor.setPosition(first_cell.firstPosition())
            
            # Przenieś do końca tabeli z zaznaczeniem
            last_row = table.rows() - 1
            last_col = table.columns() - 1
            last_cell = table.cellAt(last_row, last_col)
            cursor.setPosition(last_cell.lastPosition(), QTextCursor.MoveMode.KeepAnchor)
            
            # Usuń zaznaczony tekst (tabelę)
            cursor.removeSelectedText()
            
            cursor.endEditBlock()
            logger.info("Usunięto tabelę QTextTable")
    
    def _is_cursor_in_html_table(self, cursor_pos: int, html: str) -> bool:
        """Sprawdza, czy kursor jest wewnątrz tabeli HTML"""
        # Uproszczona metoda - szuka tagów <table> przed i </table> po pozycji kursora
        # W prawdziwej implementacji trzeba by parsować HTML dokładniej
        try:
            # Konwertuj pozycję kursora na pozycję w HTML
            # To jest uproszczone - w prawdziwej implementacji trzeba uwzględnić różnice
            before = html[:cursor_pos + 100]  # Przybliżona pozycja
            after = html[cursor_pos:]
            
            # Szukaj najbliższego <table> przed kursorem i </table> po kursorze
            last_table_start = before.rfind('<table')
            last_table_end = before.rfind('</table>')
            next_table_end = after.find('</table>')
            
            # Jeśli znaleziono <table> przed kursorem i nie było </table> między nimi
            # oraz jest </table> po kursorze, to jesteśmy w tabeli
            if last_table_start > last_table_end and next_table_end != -1:
                return True
            
            return False
        except:
            return False
    
    def _add_table_row(self, cursor: QTextCursor, above: bool = False):
        """Dodaje wiersz do tabeli HTML"""
        try:
            html = self.text_editor.toHtml()
            cursor_pos = cursor.position()
            
            # Znajdź tabelę zawierającą kursor
            table_info = self._find_table_at_cursor(html, cursor_pos)
            if not table_info:
                return
            
            table_start, table_end, table_html = table_info
            
            # Policz liczbę kolumn w pierwszym wierszu
            cols = table_html.count('<th')
            if cols == 0:
                cols = table_html.count('<td', 0, table_html.find('</tr>'))
            
            # Wygeneruj nowy wiersz
            new_row = "    <tr>\n"
            for _ in range(cols):
                new_row += '      <td style="border: 1px solid #666; padding: 8px; min-height: 20px; vertical-align: top;">&nbsp;</td>\n'
            new_row += "    </tr>\n"
            
            # Znajdź miejsce wstawienia (po pierwszym <tbody> lub przed </tbody>)
            if above:
                # Wstaw na początku tbody
                tbody_start = table_html.find('<tbody>')
                if tbody_start != -1:
                    insert_pos = tbody_start + len('<tbody>\n')
                    modified_table = table_html[:insert_pos] + new_row + table_html[insert_pos:]
                else:
                    # Brak tbody - wstaw po nagłówku
                    thead_end = table_html.find('</thead>')
                    if thead_end != -1:
                        insert_pos = thead_end + len('</thead>\n')
                        modified_table = table_html[:insert_pos] + "  <tbody>\n" + new_row + "  </tbody>\n" + table_html[insert_pos:]
                    else:
                        return
            else:
                # Wstaw przed </tbody>
                tbody_end = table_html.rfind('</tbody>')
                if tbody_end != -1:
                    modified_table = table_html[:tbody_end] + new_row + table_html[tbody_end:]
                else:
                    # Brak tbody - dodaj przed </table>
                    table_close = table_html.rfind('</table>')
                    if table_close != -1:
                        modified_table = table_html[:table_close] + new_row + table_html[table_close:]
                    else:
                        return
            
            # Zamień starą tabelę na nową w całym HTML
            new_html = html[:table_start] + modified_table + html[table_end:]
            
            # Aktualizuj edytor
            self.text_editor.blockSignals(True)
            self.text_editor.setHtml(new_html)
            self.text_editor.blockSignals(False)
            
        except Exception as e:
            logger.error(f"Błąd dodawania wiersza: {e}")
            QMessageBox.warning(self, "Błąd", f"Nie udało się dodać wiersza: {str(e)}")
    
    def _add_table_column(self, cursor: QTextCursor, left: bool = False):
        """Dodaje kolumnę do tabeli HTML"""
        try:
            html = self.text_editor.toHtml()
            cursor_pos = cursor.position()
            
            # Znajdź tabelę zawierającą kursor
            table_info = self._find_table_at_cursor(html, cursor_pos)
            if not table_info:
                return
            
            table_start, table_end, table_html = table_info
            
            # Dodaj komórkę do każdego wiersza
            # Dla uproszczenia dodajemy na końcu każdego wiersza
            modified_table = table_html
            
            # Dodaj do nagłówka
            header_cell = '<th style="border: 1px solid #666; padding: 8px; background-color: #f0f0f0; font-weight: bold; min-height: 20px; vertical-align: top;">Nowa kolumna</th>'
            modified_table = modified_table.replace('</tr>', header_cell + '\n    </tr>', 1)
            
            # Dodaj do pozostałych wierszy
            body_cell = '<td style="border: 1px solid #666; padding: 8px; min-height: 20px; vertical-align: top;">&nbsp;</td>'
            
            # Znajdź wszystkie </tr> poza pierwszym (nagłówkiem)
            parts = modified_table.split('</tr>')
            if len(parts) > 2:  # Nagłówek + min 1 wiersz
                # Pomiń pierwszy (nagłówek już obsłużony)
                for i in range(2, len(parts)):
                    if '<td' in parts[i-1] or '<th' in parts[i-1]:  # Sprawdź, czy to wiersz danych
                        parts[i-1] += body_cell + '\n      '
                
                modified_table = '</tr>'.join(parts)
            
            # Zamień starą tabelę na nową
            new_html = html[:table_start] + modified_table + html[table_end:]
            
            # Aktualizuj edytor
            self.text_editor.blockSignals(True)
            self.text_editor.setHtml(new_html)
            self.text_editor.blockSignals(False)
            
        except Exception as e:
            logger.error(f"Błąd dodawania kolumny: {e}")
            QMessageBox.warning(self, "Błąd", f"Nie udało się dodać kolumny: {str(e)}")
    
    def _find_table_at_cursor(self, html: str, cursor_pos: int):
        """Znajduje tabelę HTML zawierającą pozycję kursora"""
        try:
            # Znajdź wszystkie tabele w dokumencie
            import re
            pattern = r'<table[^>]*>.*?</table>'
            
            for match in re.finditer(pattern, html, re.DOTALL | re.IGNORECASE):
                table_start = match.start()
                table_end = match.end()
                table_html = match.group()
                
                # Sprawdź, czy kursor jest w zakresie tabeli (przybliżenie)
                # W prawdziwej implementacji trzeba by uwzględnić konwersję pozycji
                if table_start <= cursor_pos <= table_end + 1000:  # Tolerancja dla różnic w pozycji
                    return (table_start, table_end, table_html)
            
            return None
        except Exception as e:
            logger.error(f"Błąd znajdowania tabeli: {e}")
            return None
    
    def _delete_table_row(self, cursor: QTextCursor):
        """Usuwa wiersz z tabeli"""
        QMessageBox.information(
            self,
            self.i18n.t("notes.table_edit", "Edycja tabeli"),
            self.i18n.t("notes.table_manual_edit", 
                       "Zaznacz komórki w wierszu i naciśnij Delete, aby usunąć wiersz.")
        )
    
    def _delete_table_column(self, cursor: QTextCursor):
        """Usuwa kolumnę z tabeli"""
        QMessageBox.information(
            self,
            self.i18n.t("notes.table_edit", "Edycja tabeli"),
            self.i18n.t("notes.table_manual_edit", 
                       "Zaznacz komórki w kolumnie i naciśnij Delete, aby usunąć kolumnę.")
        )
    
    def _delete_table(self, cursor: QTextCursor):
        """Usuwa całą tabelę"""
        try:
            html = self.text_editor.toHtml()
            cursor_pos = cursor.position()
            
            # Znajdź tabelę zawierającą kursor
            table_info = self._find_table_at_cursor(html, cursor_pos)
            if not table_info:
                QMessageBox.information(
                    self,
                    self.i18n.t("notes.table_delete", "Usuń tabelę"),
                    self.i18n.t("notes.table_not_found", "Nie znaleziono tabeli w tym miejscu.")
                )
                return
            
            table_start, table_end, table_html = table_info
            
            # Potwierdzenie usunięcia
            reply = QMessageBox.question(
                self,
                self.i18n.t("notes.table_delete", "Usuń tabelę"),
                self.i18n.t("notes.table_delete_confirm", "Czy na pewno chcesz usunąć tę tabelę?"),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                # Usuń tabelę z HTML
                new_html = html[:table_start] + html[table_end:]
                
                # Aktualizuj edytor
                self.text_editor.blockSignals(True)
                self.text_editor.setHtml(new_html)
                self.text_editor.blockSignals(False)
                
                logger.info("Usunięto tabelę")
                
        except Exception as e:
            logger.error(f"Błąd usuwania tabeli: {e}")
            QMessageBox.warning(self, "Błąd", f"Nie udało się usunąć tabeli: {str(e)}")
    
    # ==============================
    # MOTYW I TŁUMACZENIA
    # ==============================
    
    def apply_theme(self):
        """Aplikuje motyw do widoku - zintegrowane z ThemeManager aplikacji"""
        # print("[DEBUG] apply_theme() START!")
        logger.info(f"[NOTES] apply_theme() called!")
        # print("[DEBUG] apply_theme() AFTER LOGGER!")
        
        # print(f"[DEBUG] theme_manager value: {self.theme_manager}")
        # print("[DEBUG] Checking theme_manager...")
        if not self.theme_manager:
            logger.warning(f"[NOTES] theme_manager is None!")
            # print("[DEBUG] theme_manager is None, returning!")
            return
        
        # print("[DEBUG] theme_manager is OK, continuing...")
        # print("[DEBUG] Getting QApplication instance...")
        # Pobierz aktualny stylesheet aplikacji
        app = QApplication.instance()
        current_stylesheet = ""
        if app and isinstance(app, QApplication):
            current_stylesheet = app.styleSheet()
        
        # print("[DEBUG] Checking QApplication...")
        if not app:
            logger.warning("[NOTES] QApplication instance not found, using default theme colors")
            # print("[DEBUG] QApplication not found, returning!")
            return
            
        logger.info(f"[NOTES] QApplication stylesheet length: {len(current_stylesheet)}")
        # print(f"[DEBUG] Stylesheet length: {len(current_stylesheet)}")
        
        # Pobierz aktualny motyw
        theme = self.theme_manager.current_theme
        
        logger.info(f"[NOTES] Current theme: {theme}")
        # print(f"[DEBUG] Current theme: {theme}")
        
        # print("[DEBUG] Calling _extract_theme_colors...")
        # EKSTRAHUJ KOLORY Z AKTUALNEGO MOTYWU APLIKACJI
        # (zamiast hardkodowania używamy kolorów z ThemeManager)
        colors = self._extract_theme_colors(current_stylesheet, theme)
        # print("[DEBUG] _extract_theme_colors completed!")
        
        # HARDCODE - bezpośrednie ustalenie kolorów na podstawie layout'u
        current_layout = self.theme_manager.current_layout if self.theme_manager else 2
        # print(f"[DEBUG] Current layout: {current_layout}")
        
        if current_layout == 1:  # Layout 1 = jasny (light mode)
            panel_bg = "#ffffff"      # Białe tło dla sekcji
            main_bg = "#f8f9fa"       # Jasno szare tło główne
            text_color = "#212529"    # Ciemny tekst
            border_color = "#dee2e6"  # Jasna ramka
            button_color = "#0d6efd"  # Niebieski przycisk
        else:  # Layout 2 = ciemny (dark mode)  
            panel_bg = "#2d3748"      # Ciemno szare tło dla sekcji
            main_bg = "#1a202c"       # Bardzo ciemne tło główne
            text_color = "#e2e8f0"    # Jasny tekst
            border_color = "#4a5568"  # Ciemna ramka
            button_color = "#4299e1"  # Jasnoniebieski przycisk
            
        # print(f"[DEBUG] Using hardcoded colors: panel_bg={panel_bg}, layout={current_layout}")
        
        # Zastąp wyekstraktowane kolory hardcode'em
        bg_secondary = panel_bg
        bg_main = main_bg
        text_primary = text_color
        border_color = border_color
        primary_color = button_color
        
        # Pozostałe kolory (możemy też je hardkodować jeśli potrzeba)
        accent_color = primary_color
        active_color = "#ff6b35"
        bg_input = panel_bg
        text_secondary = "#6c757d" if current_layout == 1 else "#a0aec0"
        border_focus = primary_color
        hover_bg = "#e9ecef" if current_layout == 1 else "#374151"
        
        # === GŁÓWNY WIDGET ===
        self.setStyleSheet(f"""
            NoteView {{
                background-color: {bg_main};
                color: {text_primary};
                font-family: 'Segoe UI', 'Roboto', Arial, sans-serif;
            }}
            
            /* === SEKCJE GŁÓWNE === */
            QWidget#leftPanel {{
                background-color: {bg_secondary} !important;
                border-radius: 8px !important;
                border: 1px solid {border_color} !important;
            }}
            
            QWidget#rightPanel {{
                background-color: {bg_secondary} !important;
                border-radius: 8px !important;
                border: 1px solid {border_color} !important;
            }}
        """)
        
        # === PRZYCISKI ZGODNE Z GŁÓWNĄ APLIKACJĄ ===
        button_style = f"""
            QPushButton {{
                background-color: {primary_color};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                min-width: 70px;
                font-weight: 500;
                font-size: 10pt;
            }}
            QPushButton:hover {{
                background-color: {accent_color};
                color: {bg_secondary};
            }}
            QPushButton:pressed {{
                background-color: {accent_color};
                color: {bg_secondary};
            }}
            QPushButton:disabled {{
                background-color: {text_secondary};
                color: {bg_main};
            }}
            QPushButton:focus {{
                outline: none;
                border: 2px solid {accent_color};
            }}
        """
        
        # Zastosuj do przycisków
        self.add_note_btn.setStyleSheet(button_style)
        self.create_subchapter_btn.setStyleSheet(button_style)
        self.font_increase_btn.setStyleSheet(button_style)
        self.font_decrease_btn.setStyleSheet(button_style)
        self.bold_btn.setStyleSheet(button_style)
        self.italic_btn.setStyleSheet(button_style)
        self.underline_btn.setStyleSheet(button_style)
        self.strikethrough_btn.setStyleSheet(button_style)
        self.text_color_btn.setStyleSheet(button_style)
        self.highlight_btn.setStyleSheet(button_style)
        self.clear_format_btn.setStyleSheet(button_style)
        self.summarize_ai_btn.setStyleSheet(button_style)
        self.print_btn.setStyleSheet(button_style)
        
        # === DRZEWO NOTATEK ===
        self.notes_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {bg_input};
                color: {text_primary};
                border: 2px solid {border_color};
                border-radius: 8px;
                padding: 8px;
                font-size: 11pt;
                gridline-color: {border_color};
            }}
            QTreeWidget::item {{
                padding: 8px 12px;
                border-radius: 4px;
                margin: 1px 0px;
                min-height: 20px;
            }}
            QTreeWidget::item:hover {{
                background-color: {hover_bg};
                border: 1px solid {primary_color};
            }}
            QTreeWidget::item:selected {{
                background-color: {primary_color};
                color: white;
                border: 1px solid {accent_color};
            }}
            QTreeWidget::branch {{
                background-color: transparent;
            }}
            QTreeWidget::branch:has-children:!has-siblings:closed,
            QTreeWidget::branch:closed:has-children:has-siblings {{
                border-image: none;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTMgMS41TDcuNSA1TDMgOC41VjEuNVoiIGZpbGw9IiM3NTc1NzUiLz4KPC9zdmc+);
            }}
            QTreeWidget::branch:open:has-children:!has-siblings,
            QTreeWidget::branch:open:has-children:has-siblings {{
                border-image: none;
                image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTAiIGhlaWdodD0iMTAiIHZpZXdCb3g9IjAgMCAxMCAxMCIgZmlsbD0ibm9uZSIgeG1sbnM9Imh0dHA6Ly93d3cudzMub3JnLzIwMDAvc3ZnIj4KPHBhdGggZD0iTTEuNSAzTDUgNy41TDguNSAzSDEuNVoiIGZpbGw9IiM3NTc1NzUiLz4KPC9zdmc+);
            }}
        """)
        
        # === POLE WYSZUKIWANIA ===
        self.search_input.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_input};
                color: {text_primary};
                border: 2px solid {border_color};
                border-radius: 6px;
                padding: 8px 12px;
                font-size: 11pt;
                selection-background-color: {primary_color};
            }}
            QLineEdit:focus {{
                border: 2px solid {border_focus};
            }}
            QLineEdit:hover {{
                border: 2px solid {primary_color};
            }}
        """)
        
        # === EDYTOR TEKSTU ===
        self.text_editor.setStyleSheet(f"""
            QTextEdit {{
                background-color: {bg_input};
                color: {text_primary};
                border: 2px solid {border_color};
                border-radius: 8px;
                padding: 15px;
                font-family: "Segoe UI", "Calibri", Arial, sans-serif;
                font-size: 13px;
                line-height: 1.4;
                selection-background-color: {primary_color};
                selection-color: white;
            }}
            QTextEdit:focus {{
                border: 2px solid {border_focus};
            }}
            QTextEdit:hover {{
                border: 2px solid {primary_color};
            }}
        """)
        
        # === TYTUŁ EDYTORA ===
        self.editor_title.setStyleSheet(f"""
            QLineEdit {{
                background-color: {bg_input};
                color: {text_primary};
                border: 2px solid {border_color};
                border-radius: 6px;
                padding: 12px 15px;
                font-family: "Segoe UI", "Arial", sans-serif;
                font-size: 16px;
                font-weight: bold;
                selection-background-color: {primary_color};
            }}
            QLineEdit:focus {{
                border: 2px solid {border_focus};
            }}
            QLineEdit:read-only {{
                background-color: transparent;
                border: 1px dashed {border_color};
                color: {text_secondary};
            }}
            QLineEdit:hover:!read-only {{
                border: 2px solid {primary_color};
            }}
        """)
        
        # === ETYKIETY I NAGŁÓWKI ===
        label_style = f"""
            QLabel {{
                color: {text_primary};
                font-weight: bold;
                background-color: transparent;
            }}
        """
        self.title_label.setStyleSheet(label_style + f"font-size: 14pt; color: {primary_color};")
        self.tools_label.setStyleSheet(label_style + f"font-size: 10pt; color: {text_secondary};")
        
        # === STATUS LED ===
        self.sync_status_label.setStyleSheet(f"""
            QLabel {{
                background-color: transparent;
                color: {text_primary};
                font-size: 16pt;
                padding: 4px;
                border-radius: 8px;
            }}
        """)
        
        # === SEPARATORY ===
        separator_style = f"""
            QFrame {{
                background-color: {border_color};
                border: none;
                max-height: 1px;
                margin: 4px 0px;
            }}
        """
        
        # Zastosuj separatory do wszystkich QFrame
        for widget in self.toolbar_widget.findChildren(QFrame):
            widget.setStyleSheet(separator_style)
            
        # 🎯 BEZPOŚREDNIE ZASTOSOWANIE STYLÓW DO PANELI
        # (na wypadek gdyby selektory QSS nie działały)
        left_panel_style = f"""
            QWidget {{
                background-color: {bg_secondary};
                border-radius: 8px;
                border: 1px solid {border_color};
            }}
        """
        
        right_panel_style = f"""
            QWidget {{
                background-color: {bg_secondary};
                border-radius: 8px;
                border: 1px solid {border_color};
            }}
        """
        
        # Znajdź panele i ustaw style bezpośrednio
        if hasattr(self, 'left_widget') and self.left_widget:
            self.left_widget.setStyleSheet(left_panel_style)
            self.left_widget.update()  # Wymuś odświeżenie
            # print(f"[DEBUG] Applied style directly to left_widget: {bg_secondary}")
            
        if hasattr(self, 'right_widget') and self.right_widget:
            self.right_widget.setStyleSheet(right_panel_style)
            self.right_widget.update()  # Wymuś odświeżenie
            # print(f"[DEBUG] Applied style directly to right_widget: {bg_secondary}")
            
        # print(f"[DEBUG] apply_theme() COMPLETED! Panel colors should be: {bg_secondary}")
        logger.info(f"[NOTES] apply_theme() completed successfully with bg_secondary={bg_secondary}")
    
    def update_translations(self):
        """Aktualizuje tłumaczenia w widoku"""
        # Aktualizuj teksty w UI
        self.title_label.setText("📝 " + self.i18n.t("notes.title", "Notatki"))
        self.add_note_btn.setText(self.i18n.t("notes.new_notebook", "Nowy notatnik"))
        self.search_input.setPlaceholderText("🔍 " + self.i18n.t("notes.search", "Szukaj..."))
        
        if not self.current_note_id:
            self.editor_title.setText(self.i18n.t("notes.select_note", "Wybierz notatkę"))
            self.editor_title.setPlaceholderText(self.i18n.t("notes.title_placeholder", "Wprowadź tytuł..."))
            self.text_editor.setPlaceholderText(
                self.i18n.t("notes.select_note_placeholder", 
                           "Wybierz notatkę z drzewa lub utwórz nową...")
            )
        
        self.tools_label.setText(self.i18n.t("notes.tools", "Narzędzia"))
        
        # Aktualizuj tooltips
        self.create_subchapter_btn.setToolTip(
            self.i18n.t("notes.tooltip_create_subchapter",
                       "Utwórz zagnieżdżoną notatkę z zaznaczonego tekstu")
        )
        self.font_increase_btn.setToolTip(self.i18n.t("notes.font_size_increase", "Powiększ"))
        self.font_decrease_btn.setToolTip(self.i18n.t("notes.font_size_decrease", "Pomniejsz"))
        self.bold_btn.setToolTip(self.i18n.t("notes.tooltip_bold", "Pogrubienie"))
        self.italic_btn.setToolTip(self.i18n.t("notes.tooltip_italic", "Kursywa"))
        self.underline_btn.setToolTip(self.i18n.t("notes.tooltip_underline", "Podkreślenie"))
        self.strikethrough_btn.setToolTip(self.i18n.t("notes.tooltip_strikethrough", "Przekreślenie"))
        self.text_color_btn.setToolTip(self.i18n.t("notes.tooltip_text_color", "Kolor tekstu"))
        self.highlight_btn.setToolTip(self.i18n.t("notes.tooltip_highlight", "Zakreśl tekst"))
        self.clear_format_btn.setToolTip(self.i18n.t("notes.tooltip_clear_format", "Usuń formatowanie"))
        self.summarize_ai_btn.setToolTip(self.i18n.t("notes.tooltip_summarize_ai", "Podsumuj AI"))
        if hasattr(self, "voice_input_btn"):
            self.voice_input_btn.setToolTip(
                self.i18n.t("notes.tooltip_voice_input", "Włącz dyktowanie (Win + H)")
            )
        self.print_btn.setToolTip(self.i18n.t("notes.tooltip_print", "Drukuj"))
    
    # =============================================================================
    # SYNCHRONIZATION METHODS
    # =============================================================================
    # SYNCHRONIZACJA
    # =============================================================================
    
    def _on_sync_status_changed(self, status: str):
        """Callback zmiany statusu synchronizacji"""
        from src.Modules.Note_module.notes_sync_manager import SyncStatus
        
        # Aktualizuj LED
        status_icons = {
            SyncStatus.SYNCED: "🟢",
            SyncStatus.PENDING: "🟡",
            SyncStatus.SYNCING: "🔵",
            SyncStatus.ERROR: "🔴",
            SyncStatus.OFFLINE: "⚫"
        }
        
        status_tooltips = {
            SyncStatus.SYNCED: self.i18n.t("notes.sync_synced", "Zsynchronizowane"),
            SyncStatus.PENDING: self.i18n.t("notes.sync_pending", "Oczekujące..."),
            SyncStatus.SYNCING: self.i18n.t("notes.sync_syncing", "Synchronizacja..."),
            SyncStatus.ERROR: self.i18n.t("notes.sync_error", "Błąd synchronizacji"),
            SyncStatus.OFFLINE: self.i18n.t("notes.sync_offline", "Tryb offline")
        }
        
        self.sync_status_label.setText(status_icons.get(status, "⚫"))
        self.sync_status_label.setToolTip(status_tooltips.get(status, "Unknown"))
        
        logger.debug(f"Sync status: {status}")
    
    def _on_sync_progress(self, current: int, total: int):
        """Callback progress synchronizacji"""
        logger.debug(f"Sync progress: {current}/{total}")
        # Opcjonalnie: wyświetl progress bar
    
    def _on_sync_completed(self, success_count: int, error_count: int):
        """Callback zakończenia synchronizacji"""
        logger.info(f"Sync completed: {success_count} success, {error_count} errors")
        
        if error_count > 0:
            # Opcjonalnie: pokaż notyfikację
            pass
    
    def _on_sync_error(self, error_message: str):
        """Callback błędu synchronizacji"""
        logger.error(f"Sync error: {error_message}")
        # Opcjonalnie: pokaż komunikat użytkownikowi
    
    def _on_remote_note_created(self, note_data: dict):
        """Notatka utworzona na innym urządzeniu"""
        logger.info(f"Remote note created: {note_data.get('title')}")
        
        # Odśwież drzewo notatek
        self.refresh_tree()
    
    def _on_remote_note_updated(self, note_data: dict):
        """Notatka zaktualizowana na innym urządzeniu"""
        logger.info(f"Remote note updated: {note_data.get('title')}")
        
        # Jeśli edytujemy tę notatkę, odśwież zawartość
        if self.current_note_id:
            note = self.db.get_note(self.current_note_id)
            if note and note.get('server_id') == note_data.get('id'):
                # Ta sama notatka - odśwież edytor
                self.editor_title.setText(note['title'])
                self.text_editor.setHtml(note['content'])
                logger.info("Current note updated from remote")
        
        # Odśwież drzewo
        self.refresh_tree()
    
    def _on_remote_note_deleted(self, note_id: str):
        """Notatka usunięta na innym urządzeniu"""
        logger.info(f"Remote note deleted: {note_id}")
        
        # Jeśli edytujemy tę notatkę, wyczyść edytor
        if self.current_note_id:
            note = self.db.get_note(self.current_note_id)
            if note and note.get('server_id') == note_id:
                # Wyczyść edytor
                self.editor_title.clear()
                self.text_editor.clear()
                self.current_note_id = None
                if hasattr(self, "voice_input_btn"):
                    self.voice_input_btn.setEnabled(False)
        
        # Odśwież drzewo
        self.refresh_tree()
    
    def set_user_data(self, user_data: dict, on_token_refreshed=None):
        """
        Ustaw dane użytkownika i włącz synchronizację.
        
        Args:
            user_data: Słownik z danymi użytkownika (id/user_id, email, access_token, refresh_token)
            on_token_refreshed: Callback wywoływany po odświeżeniu tokena
        """
        # user_id może być zapisany jako 'id' lub 'user_id'
        user_id = user_data.get('user_id') or user_data.get('id')
        access_token = user_data.get('access_token')
        refresh_token = user_data.get('refresh_token')
        email = user_data.get('email', 'Unknown')
        
        logger.info(f"[NOTES] set_user_data called for user: {user_id} ({email})")
        
        if not user_id or not access_token:
            logger.warning("[NOTES] Incomplete user data, sync disabled")
            return
        
        try:
            # Zatrzymaj istniejący sync manager (jeśli był)
            if self.sync_manager:
                logger.info("[NOTES] Stopping existing sync manager...")
                self.sync_manager.stop()
                self.sync_manager = None
            
            # Inicjalizuj sync manager z danymi użytkownika
            from src.Modules.Note_module.notes_sync_manager import NotesSyncManager
            
            self.user_id = user_id
            self.sync_manager = NotesSyncManager(
                user_id=user_id,
                auth_token=access_token,
                db=self.db,
                refresh_token=refresh_token,
                on_token_refreshed=on_token_refreshed
            )
            
            # Podłącz sygnały sync manager
            self.sync_manager.sync_status_changed.connect(self._on_sync_status_changed)
            self.sync_manager.sync_progress.connect(self._on_sync_progress)
            self.sync_manager.sync_completed.connect(self._on_sync_completed)
            self.sync_manager.sync_error.connect(self._on_sync_error)
            
            # Podłącz sygnały remote updates
            self.sync_manager.note_created_remotely.connect(self._on_remote_note_created)
            self.sync_manager.note_updated_remotely.connect(self._on_remote_note_updated)
            self.sync_manager.note_deleted_remotely.connect(self._on_remote_note_deleted)
            
            # Uruchom sync manager
            self.sync_manager.start()
            self.sync_enabled = True
            
            logger.info(f"✅ [NOTES] Sync enabled for user: {email}")
            
        except Exception as e:
            logger.error(f"❌ [NOTES] Failed to enable sync: {e}")
            self.sync_manager = None
            self.sync_enabled = False
    
    def _extract_theme_colors(self, stylesheet: str, theme_name: str) -> dict:
        """
        Ekstrahuje kolory z aktualnego stylesheet'u aplikacji
        Zamiast hardkodowania używa kolorów z ThemeManager
        """
        colors = {}
        
        # 🎨 DOMYŚLNE KOLORY (fallback) zgodnie z aplikacją
        if 'dark' in theme_name.lower():
            # Dark theme defaults - zgodne z theme_manager.py
            colors = {
                'primary': '#0d7377',      # QPushButton background-color w dark theme
                'accent': '#14FFEC',       # QPushButton:hover background-color  
                'active': '#FF9800',       # Aktywne elementy
                'bg_main': '#2b2b2b',      # QWidget background-color
                'bg_input': '#3c3c3c',     # QLineEdit background-color
                'bg_secondary': '#1e1e1e', # QMainWindow background-color
                'text_primary': '#e0e0e0', # QWidget color
                'text_secondary': '#b0b0b0',
                'border': '#555555',       # QLineEdit border
                'border_focus': '#0d7377', # QLineEdit:focus border  
                'hover_bg': '#404040'
            }
        else:
            # Light theme defaults - zgodne z theme_manager.py  
            colors = {
                'primary': '#2196F3',      # QPushButton background-color w light theme
                'accent': '#1976D2',       # QPushButton:hover background-color
                'active': '#FF9800',       # Aktywne elementy
                'bg_main': '#ffffff',      # QWidget background-color
                'bg_input': '#ffffff',     # QLineEdit background-color
                'bg_secondary': '#f5f5f5', # QMainWindow background-color
                'text_primary': '#212121', # QWidget color
                'text_secondary': '#757575',
                'border': '#BDBDBD',       # QLineEdit border
                'border_focus': '#2196F3', # QLineEdit:focus border
                'hover_bg': '#E3F2FD'
            }
        
        # 🔍 SPRÓBUJ WYEKSTRAHOWAĆ KOLORY Z AKTUALNEGO STYLESHEET'U
        # (pozwala na wsparcie custom themes utworzonych przez użytkownika)
        try:
            import re
            
            # Szukaj kolorów QPushButton (primary)
            button_match = re.search(r'QPushButton\s*\{[^}]*background-color:\s*([^;]+)', stylesheet)
            if button_match:
                colors['primary'] = button_match.group(1).strip()
                
            # Szukaj kolorów QPushButton:hover (accent)  
            hover_match = re.search(r'QPushButton:hover\s*\{[^}]*background-color:\s*([^;]+)', stylesheet)
            if hover_match:
                colors['accent'] = hover_match.group(1).strip()
                
            # Szukaj QWidget background-color (bg_main)
            widget_bg_match = re.search(r'QWidget\s*\{[^}]*background-color:\s*([^;]+)', stylesheet)
            if widget_bg_match:
                colors['bg_main'] = widget_bg_match.group(1).strip()
                
            # Szukaj QWidget color (text_primary)
            widget_color_match = re.search(r'QWidget\s*\{[^}]*color:\s*([^;]+)', stylesheet)
            if widget_color_match:
                colors['text_primary'] = widget_color_match.group(1).strip()
                
            # Szukaj QLineEdit background-color (bg_input)
            input_bg_match = re.search(r'QLineEdit\s*\{[^}]*background-color:\s*([^;]+)', stylesheet)
            if input_bg_match:
                colors['bg_input'] = input_bg_match.group(1).strip()
                
            # Szukaj QLineEdit border (border)
            input_border_match = re.search(r'QLineEdit\s*\{[^}]*border:\s*[^;]*\s([^;]+)', stylesheet)
            if input_border_match:
                colors['border'] = input_border_match.group(1).strip()
                
        except Exception as e:
            logger.warning(f"Could not extract colors from stylesheet: {e}")
            # Fallback to defaults set above
            
        return colors
    
    def closeEvent(self, a0):
        """Zamknięcie widoku - zatrzymaj sync manager"""
        if self.sync_manager:
            logger.info("Stopping sync manager...")
            self.sync_manager.stop()
        
        super().closeEvent(a0)


if __name__ == "__main__":
    import sys
    app = QApplication(sys.argv)
    note_view = NoteView()
    note_view.show()
    sys.exit(app.exec())
