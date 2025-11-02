"""
Style Creator Dialog - Dialog do tworzenia własnych kompozycji kolorystycznych
"""
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QLineEdit, QScrollArea,
    QWidget, QGroupBox, QColorDialog, QMessageBox,
    QTabWidget, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont
from loguru import logger

from ..utils.i18n_manager import t, get_i18n
from ..core.config import config


class ColorPickerWidget(QWidget):
    """Widget do wyboru koloru z podglądem"""
    
    color_changed = pyqtSignal(str)  # Sygnał z nowym kolorem w formacie hex
    
    def __init__(self, label: str, initial_color: str = "#FFFFFF", parent=None):
        super().__init__(parent)
        self.current_color = initial_color
        self.label_text = label
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja widgetu"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Etykieta
        self.label = QLabel(self.label_text)
        self.label.setMinimumWidth(200)
        layout.addWidget(self.label)
        
        # Pole tekstowe z kodem koloru
        self.color_input = QLineEdit(self.current_color)
        self.color_input.setMaximumWidth(100)
        self.color_input.textChanged.connect(self._on_text_changed)
        layout.addWidget(self.color_input)
        
        # Przycisk z podglądem koloru
        self.color_button = QPushButton()
        self.color_button.setFixedSize(40, 30)
        self.color_button.clicked.connect(self._open_color_dialog)
        self._update_button_color()
        layout.addWidget(self.color_button)
        
        layout.addStretch()
    
    def _update_button_color(self):
        """Aktualizuj kolor przycisku"""
        self.color_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {self.current_color};
                border: 2px solid #888;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #555;
            }}
        """)
    
    def _on_text_changed(self, text: str):
        """Obsługa zmiany tekstu w polu"""
        if text.startswith('#') and len(text) in [4, 7]:
            self.current_color = text
            self._update_button_color()
            self.color_changed.emit(text)
    
    def _open_color_dialog(self):
        """Otwórz dialog wyboru koloru"""
        color = QColorDialog.getColor(
            QColor(self.current_color),
            self,
            t('style_creator.select_color')
        )
        
        if color.isValid():
            self.current_color = color.name()
            self.color_input.setText(self.current_color)
            self._update_button_color()
            self.color_changed.emit(self.current_color)
    
    def get_color(self) -> str:
        """Pobierz aktualny kolor"""
        return self.current_color
    
    def set_color(self, color: str):
        """Ustaw kolor"""
        self.current_color = color
        self.color_input.setText(color)
        self._update_button_color()
    
    def update_translation(self):
        """Odśwież tłumaczenie etykiety"""
        # Ta metoda będzie wywoływana przy zmianie języka
        pass


class StyleCreatorDialog(QDialog):
    """Dialog do tworzenia własnych kompozycji kolorystycznych"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.color_pickers = {}
        self.scheme_name = ""
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_window(self):
        """Konfiguracja okna dialogu"""
        self.setWindowTitle(t('style_creator.title'))
        self.setMinimumSize(800, 600)
        self.resize(900, 700)
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(10)
        
        # === NAGŁÓWEK ===
        header_layout = QVBoxLayout()
        
        title_label = QLabel(t('style_creator.title'))
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(title_label)
        
        desc_label = QLabel(t('style_creator.description'))
        desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc_label.setWordWrap(True)
        header_layout.addWidget(desc_label)
        
        main_layout.addLayout(header_layout)
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator1)
        
        # === NAZWA SCHEMATU ===
        name_layout = QHBoxLayout()
        self.name_label = QLabel(t('style_creator.scheme_name'))
        self.name_label.setMinimumWidth(150)
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t('style_creator.enter_name'))
        name_layout.addWidget(self.name_label)
        name_layout.addWidget(self.name_input, stretch=1)
        main_layout.addLayout(name_layout)
        
        # === ZAKŁADKI Z KOLORAMI ===
        self.tabs = QTabWidget()
        
        # Zakładka: Kolory główne
        self.tab_main = self._create_main_colors_tab()
        self.tabs.addTab(self.tab_main, t('style_creator.tab_main'))
        
        # Zakładka: Przyciski nawigacji
        self.tab_navigation = self._create_navigation_tab()
        self.tabs.addTab(self.tab_navigation, t('style_creator.tab_navigation'))
        
        # Zakładka: Przyciski akcji
        self.tab_buttons = self._create_buttons_tab()
        self.tabs.addTab(self.tab_buttons, t('style_creator.tab_buttons'))
        
        # Zakładka: Tabele i listy
        self.tab_tables = self._create_tables_tab()
        self.tabs.addTab(self.tab_tables, t('style_creator.tab_tables'))
        
        main_layout.addWidget(self.tabs)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator2)
        
        # === PRZYCISKI AKCJI ===
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        self.btn_preview = QPushButton(t('style_creator.preview'))
        self.btn_preview.clicked.connect(self._preview_style)
        buttons_layout.addWidget(self.btn_preview)
        
        self.btn_cancel = QPushButton(t('button.cancel'))
        self.btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(self.btn_cancel)
        
        self.btn_save = QPushButton(t('button.save'))
        self.btn_save.setObjectName("saveButton")
        self.btn_save.clicked.connect(self._save_style)
        buttons_layout.addWidget(self.btn_save)
        
        main_layout.addLayout(buttons_layout)
    
    def _create_main_colors_tab(self) -> QWidget:
        """Utwórz zakładkę z głównymi kolorami"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Grupa: Tło i tekst
        bg_group = QGroupBox(t('style_creator.group_background'))
        bg_layout = QVBoxLayout()
        
        self.color_pickers['bg_main'] = ColorPickerWidget(
            t('style_creator.bg_main'), "#FFFFFF"
        )
        bg_layout.addWidget(self.color_pickers['bg_main'])
        
        self.color_pickers['bg_secondary'] = ColorPickerWidget(
            t('style_creator.bg_secondary'), "#F5F5F5"
        )
        bg_layout.addWidget(self.color_pickers['bg_secondary'])
        
        self.color_pickers['text_primary'] = ColorPickerWidget(
            t('style_creator.text_primary'), "#2C3E50"
        )
        bg_layout.addWidget(self.color_pickers['text_primary'])
        
        self.color_pickers['text_secondary'] = ColorPickerWidget(
            t('style_creator.text_secondary'), "#7F8C8D"
        )
        bg_layout.addWidget(self.color_pickers['text_secondary'])
        
        bg_group.setLayout(bg_layout)
        scroll_layout.addWidget(bg_group)
        
        # Grupa: Kolory akcentujące
        accent_group = QGroupBox(t('style_creator.group_accent'))
        accent_layout = QVBoxLayout()
        
        self.color_pickers['accent_primary'] = ColorPickerWidget(
            t('style_creator.accent_primary'), "#FF9800"
        )
        accent_layout.addWidget(self.color_pickers['accent_primary'])
        
        self.color_pickers['accent_hover'] = ColorPickerWidget(
            t('style_creator.accent_hover'), "#F57C00"
        )
        accent_layout.addWidget(self.color_pickers['accent_hover'])
        
        self.color_pickers['accent_pressed'] = ColorPickerWidget(
            t('style_creator.accent_pressed'), "#E65100"
        )
        accent_layout.addWidget(self.color_pickers['accent_pressed'])
        
        accent_group.setLayout(accent_layout)
        scroll_layout.addWidget(accent_group)
        
        # Grupa: Obramowania
        border_group = QGroupBox(t('style_creator.group_borders'))
        border_layout = QVBoxLayout()
        
        self.color_pickers['border_light'] = ColorPickerWidget(
            t('style_creator.border_light'), "#DDD"
        )
        border_layout.addWidget(self.color_pickers['border_light'])
        
        self.color_pickers['border_dark'] = ColorPickerWidget(
            t('style_creator.border_dark'), "#888"
        )
        border_layout.addWidget(self.color_pickers['border_dark'])
        
        border_group.setLayout(border_layout)
        scroll_layout.addWidget(border_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_navigation_tab(self) -> QWidget:
        """Utwórz zakładkę dla przycisków nawigacji"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        nav_group = QGroupBox(t('style_creator.group_navigation'))
        nav_layout = QVBoxLayout()
        
        self.color_pickers['nav_bg'] = ColorPickerWidget(
            t('style_creator.nav_bg'), "#F5F5F5"
        )
        nav_layout.addWidget(self.color_pickers['nav_bg'])
        
        self.color_pickers['nav_text'] = ColorPickerWidget(
            t('style_creator.nav_text'), "#2C3E50"
        )
        nav_layout.addWidget(self.color_pickers['nav_text'])
        
        self.color_pickers['nav_hover_bg'] = ColorPickerWidget(
            t('style_creator.nav_hover_bg'), "#E8E8E8"
        )
        nav_layout.addWidget(self.color_pickers['nav_hover_bg'])
        
        self.color_pickers['nav_checked_bg'] = ColorPickerWidget(
            t('style_creator.nav_checked_bg'), "#FF9800"
        )
        nav_layout.addWidget(self.color_pickers['nav_checked_bg'])
        
        self.color_pickers['nav_checked_text'] = ColorPickerWidget(
            t('style_creator.nav_checked_text'), "#FFFFFF"
        )
        nav_layout.addWidget(self.color_pickers['nav_checked_text'])
        
        nav_group.setLayout(nav_layout)
        scroll_layout.addWidget(nav_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_buttons_tab(self) -> QWidget:
        """Utwórz zakładkę dla przycisków akcji"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        # Przyciski dodawania
        add_group = QGroupBox(t('style_creator.group_add_button'))
        add_layout = QVBoxLayout()
        
        self.color_pickers['btn_add_bg'] = ColorPickerWidget(
            t('style_creator.btn_bg'), "#4CAF50"
        )
        add_layout.addWidget(self.color_pickers['btn_add_bg'])
        
        self.color_pickers['btn_add_hover'] = ColorPickerWidget(
            t('style_creator.btn_hover'), "#45A049"
        )
        add_layout.addWidget(self.color_pickers['btn_add_hover'])
        
        add_group.setLayout(add_layout)
        scroll_layout.addWidget(add_group)
        
        # Przyciski edycji
        edit_group = QGroupBox(t('style_creator.group_edit_button'))
        edit_layout = QVBoxLayout()
        
        self.color_pickers['btn_edit_bg'] = ColorPickerWidget(
            t('style_creator.btn_bg'), "#2196F3"
        )
        edit_layout.addWidget(self.color_pickers['btn_edit_bg'])
        
        self.color_pickers['btn_edit_hover'] = ColorPickerWidget(
            t('style_creator.btn_hover'), "#1976D2"
        )
        edit_layout.addWidget(self.color_pickers['btn_edit_hover'])
        
        edit_group.setLayout(edit_layout)
        scroll_layout.addWidget(edit_group)
        
        # Przyciski usuwania
        delete_group = QGroupBox(t('style_creator.group_delete_button'))
        delete_layout = QVBoxLayout()
        
        self.color_pickers['btn_delete_bg'] = ColorPickerWidget(
            t('style_creator.btn_bg'), "#F44336"
        )
        delete_layout.addWidget(self.color_pickers['btn_delete_bg'])
        
        self.color_pickers['btn_delete_hover'] = ColorPickerWidget(
            t('style_creator.btn_hover'), "#D32F2F"
        )
        delete_layout.addWidget(self.color_pickers['btn_delete_hover'])
        
        delete_group.setLayout(delete_layout)
        scroll_layout.addWidget(delete_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def _create_tables_tab(self) -> QWidget:
        """Utwórz zakładkę dla tabel i list"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        
        table_group = QGroupBox(t('style_creator.group_table'))
        table_layout = QVBoxLayout()
        
        self.color_pickers['table_header_bg'] = ColorPickerWidget(
            t('style_creator.table_header_bg'), "#F5F5F5"
        )
        table_layout.addWidget(self.color_pickers['table_header_bg'])
        
        self.color_pickers['table_header_text'] = ColorPickerWidget(
            t('style_creator.table_header_text'), "#2C3E50"
        )
        table_layout.addWidget(self.color_pickers['table_header_text'])
        
        self.color_pickers['table_row_bg'] = ColorPickerWidget(
            t('style_creator.table_row_bg'), "#FFFFFF"
        )
        table_layout.addWidget(self.color_pickers['table_row_bg'])
        
        self.color_pickers['table_row_alt'] = ColorPickerWidget(
            t('style_creator.table_row_alt'), "#F9F9F9"
        )
        table_layout.addWidget(self.color_pickers['table_row_alt'])
        
        self.color_pickers['table_selection'] = ColorPickerWidget(
            t('style_creator.table_selection'), "#E3F2FD"
        )
        table_layout.addWidget(self.color_pickers['table_selection'])
        
        table_group.setLayout(table_layout)
        scroll_layout.addWidget(table_group)
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_widget)
        layout.addWidget(scroll)
        
        return widget
    
    def _connect_signals(self):
        """Połącz sygnały"""
        # Połącz sygnał zmiany języka
        get_i18n().language_changed.connect(self._on_language_changed)
    
    def _generate_qss(self) -> str:
        """Generuj kod QSS na podstawie wybranych kolorów"""
        qss = f"""
/* === Custom Color Scheme Generated by Style Creator === */

/* Main Window */
QMainWindow {{
    background-color: {self.color_pickers['bg_main'].get_color()};
    color: {self.color_pickers['text_primary'].get_color()};
}}

/* === Custom Title Bar === */
QWidget#customTitleBar {{
    background-color: {self.color_pickers['accent_primary'].get_color()};
    border: none;
}}

QLabel#titleBarLabel {{
    color: white;
    font-size: 12pt;
    font-weight: bold;
}}

QPushButton#titleBarUserButton,
QPushButton#titleBarThemeButton {{
    background-color: rgba(255, 255, 255, 0.1);
    color: white;
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 4px;
    font-size: 16pt;
}}

QPushButton#titleBarUserButton:hover,
QPushButton#titleBarThemeButton:hover {{
    background-color: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.5);
}}

QPushButton#minimizeButton,
QPushButton#maximizeButton {{
    background-color: transparent;
    color: white;
    border: none;
    font-size: 14pt;
}}

QPushButton#minimizeButton:hover,
QPushButton#maximizeButton:hover {{
    background-color: rgba(255, 255, 255, 0.2);
}}

QPushButton#closeButton {{
    background-color: transparent;
    color: white;
    border: none;
    font-size: 14pt;
}}

QPushButton#closeButton:hover {{
    background-color: #e81123;
}}

/* === Menu === */
QMenu {{
    background-color: {self.color_pickers['bg_main'].get_color()};
    border: 1px solid {self.color_pickers['border_light'].get_color()};
    border-radius: 6px;
    padding: 6px;
}}

QMenu::item {{
    padding: 10px 30px 10px 10px;
    border-radius: 4px;
    color: {self.color_pickers['text_primary'].get_color()};
}}

QMenu::item:selected {{
    background-color: {self.color_pickers['accent_hover'].get_color()};
    color: {self.color_pickers['accent_primary'].get_color()};
}}

QMenu::separator {{
    height: 1px;
    background-color: {self.color_pickers['border_light'].get_color()};
    margin: 6px 10px;
}}

/* Navigation Buttons */
QPushButton#navButton {{
    background-color: {self.color_pickers['nav_bg'].get_color()};
    color: {self.color_pickers['nav_text'].get_color()};
    border: 1px solid {self.color_pickers['border_light'].get_color()};
    border-radius: 5px;
    padding: 8px 15px;
    font-weight: 700;
}}

QPushButton#navButton:hover {{
    background-color: {self.color_pickers['nav_hover_bg'].get_color()};
}}

QPushButton#navButton:checked {{
    background-color: {self.color_pickers['nav_checked_bg'].get_color()};
    color: {self.color_pickers['nav_checked_text'].get_color()};
}}

/* Add Button */
QPushButton {{
    background-color: {self.color_pickers['btn_add_bg'].get_color()};
    color: white;
    border-radius: 4px;
    padding: 6px 12px;
}}

QPushButton:hover {{
    background-color: {self.color_pickers['btn_add_hover'].get_color()};
}}

/* Tables */
QTableWidget {{
    background-color: {self.color_pickers['table_row_bg'].get_color()};
    alternate-background-color: {self.color_pickers['table_row_alt'].get_color()};
    selection-background-color: {self.color_pickers['table_selection'].get_color()};
    gridline-color: {self.color_pickers['border_light'].get_color()};
}}

QHeaderView::section {{
    background-color: {self.color_pickers['table_header_bg'].get_color()};
    color: {self.color_pickers['table_header_text'].get_color()};
    border: 1px solid {self.color_pickers['border_light'].get_color()};
    padding: 5px;
}}

/* Input Fields */
QLineEdit, QTextEdit {{
    background-color: {self.color_pickers['bg_main'].get_color()};
    color: {self.color_pickers['text_primary'].get_color()};
    border: 2px solid {self.color_pickers['border_light'].get_color()};
    border-radius: 4px;
    padding: 4px;
}}

QLineEdit:focus, QTextEdit:focus {{
    border-color: {self.color_pickers['accent_primary'].get_color()};
}}

/* GroupBox */
QGroupBox {{
    font-weight: 600;
    color: {self.color_pickers['text_primary'].get_color()};
    border: 2px solid {self.color_pickers['border_light'].get_color()};
    border-radius: 6px;
    margin-top: 12px;
    padding-top: 15px;
}}

QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 10px;
    background-color: {self.color_pickers['bg_main'].get_color()};
}}
"""
        return qss
    
    def _preview_style(self):
        """Podgląd stylu"""
        if not self.name_input.text().strip():
            QMessageBox.warning(
                self,
                t('dialog.warning'),
                t('style_creator.error_no_name')
            )
            return
        
        qss = self._generate_qss()
        
        # Zastosuj styl do dialogu jako podgląd
        self.setStyleSheet(qss)
        
        QMessageBox.information(
            self,
            t('dialog.info'),
            t('style_creator.preview_applied')
        )
        
        logger.info("Style preview applied")
    
    def _save_style(self):
        """Zapisz styl do pliku"""
        scheme_name = self.name_input.text().strip()
        
        if not scheme_name:
            QMessageBox.warning(
                self,
                t('dialog.warning'),
                t('style_creator.error_no_name')
            )
            return
        
        # Generuj QSS
        qss = self._generate_qss()
        
        # Zapisz do pliku
        custom_themes_dir = config.THEMES_DIR / "custom"
        custom_themes_dir.mkdir(exist_ok=True)
        
        # Bezpieczna nazwa pliku
        safe_name = "".join(c for c in scheme_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_').lower()
        
        theme_file = custom_themes_dir / f"{safe_name}.qss"
        
        try:
            with open(theme_file, 'w', encoding='utf-8') as f:
                f.write(qss)
            
            # Zapisz metadane
            metadata = {
                'name': scheme_name,
                'colors': {key: picker.get_color() for key, picker in self.color_pickers.items()},
                'created_at': __import__('datetime').datetime.now().isoformat()
            }
            
            metadata_file = custom_themes_dir / f"{safe_name}.json"
            with open(metadata_file, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)
            
            QMessageBox.information(
                self,
                t('dialog.info'),
                t('style_creator.success_saved').format(name=scheme_name)
            )
            
            logger.info(f"Custom style saved: {scheme_name} -> {theme_file}")
            
            self.accept()
            
        except Exception as e:
            logger.error(f"Error saving style: {e}")
            QMessageBox.critical(
                self,
                t('dialog.error'),
                t('style_creator.error_saving').format(error=str(e))
            )
    
    def _on_language_changed(self, language_code: str):
        """Obsługa zmiany języka"""
        logger.info(f"Updating style creator translations for: {language_code}")
        
        # Odśwież tytuł okna
        self.setWindowTitle(t('style_creator.title'))
        
        # Odśwież etykiety zakładek
        self.tabs.setTabText(0, t('style_creator.tab_main'))
        self.tabs.setTabText(1, t('style_creator.tab_navigation'))
        self.tabs.setTabText(2, t('style_creator.tab_buttons'))
        self.tabs.setTabText(3, t('style_creator.tab_tables'))
        
        # Odśwież przyciski
        self.btn_preview.setText(t('style_creator.preview'))
        self.btn_cancel.setText(t('button.cancel'))
        self.btn_save.setText(t('button.save'))
        
        # Odśwież etykiety
        self.name_label.setText(t('style_creator.scheme_name'))
        self.name_input.setPlaceholderText(t('style_creator.enter_name'))
        
        logger.info("Style creator translations updated")
