"""
Assistant Settings Tab - Karta ustawień asystenta
=============================================================================
Interfejs do zarządzania frazami wywołującymi funkcje asystenta.

Funkcje:
- Lista dostępnych funkcji asystenta
- Edycja fraz dla każdej funkcji
- Dodawanie własnych fraz
- Aktywacja/deaktywacja fraz
- Zarządzanie priorytetem
"""
from typing import Optional
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QComboBox,
    QGroupBox, QScrollArea, QMessageBox, QDialog,
    QDialogButtonBox, QSpinBox, QCheckBox, QSplitter
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont
from loguru import logger

from ..core.assisstant.assistant_settings import AssistantSettingsManager, AssistantPhrase
from ..utils.i18n_manager import t

try:
    from ..utils.theme_manager import get_theme_manager
    THEME_AVAILABLE = True
except ImportError:
    logger.warning("Theme manager not available")
    THEME_AVAILABLE = False
    get_theme_manager = lambda: None  # type: ignore


class PhraseEditDialog(QDialog):
    """Dialog edycji frazy."""
    
    def __init__(self, phrase: Optional[AssistantPhrase] = None, method_name: str = "", parent=None):
        super().__init__(parent)
        self.phrase = phrase
        self.method_name = method_name
        self.setWindowTitle(t("assistant.edit_phrase", "Edytuj frazę") if phrase else t("assistant.add_phrase", "Dodaj frazę"))
        self.setMinimumWidth(400)
        
        # Pobierz theme manager z rodzica jeśli dostępny
        self.theme_manager = None
        if THEME_AVAILABLE and parent and hasattr(parent, 'theme_manager'):
            self.theme_manager = parent.theme_manager
        
        self._setup_ui()
        
        if phrase:
            self._load_phrase_data()
        
        # Zastosuj motyw
        if self.theme_manager:
            self._apply_theme()
    
    def _apply_theme(self):
        """Aplikuje motyw do dialogu."""
        if not self.theme_manager:
            return
        
        colors = self.theme_manager.get_current_colors()
        bg_main = colors.get("bg_main", "#FFFFFF")
        bg_secondary = colors.get("bg_secondary", "#F5F5F5")
        text_primary = colors.get("text_primary", "#1A1A1A")
        text_secondary = colors.get("text_secondary", "#666666")
        accent_primary = colors.get("accent_primary", "#2196F3")
        accent_hover = colors.get("accent_hover", "#1976D2")
        border_light = colors.get("border_light", "#CCCCCC")
        
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_main};
                color: {text_primary};
            }}
            
            QLabel {{
                color: {text_primary};
            }}
            
            QLineEdit, QSpinBox, QComboBox {{
                background-color: {bg_secondary};
                color: {text_primary};
                border: 1px solid {border_light};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border: 2px solid {accent_primary};
            }}
            
            QCheckBox {{
                color: {text_primary};
            }}
            
            QPushButton {{
                background-color: {accent_primary};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
            }}
            
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
        """)
    
    def _setup_ui(self):
        """Konfiguracja interfejsu dialogu."""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Fraza
        phrase_label = QLabel(t("assistant.phrase_text", "Tekst frazy:"))
        self.phrase_input = QLineEdit()
        self.phrase_input.setPlaceholderText(t("assistant.phrase_placeholder", "np. utwórz zadanie"))
        layout.addWidget(phrase_label)
        layout.addWidget(self.phrase_input)
        
        # Język
        lang_label = QLabel(t("assistant.language", "Język:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["pl", "en", "de"])
        layout.addWidget(lang_label)
        layout.addWidget(self.lang_combo)
        
        # Priorytet
        priority_layout = QHBoxLayout()
        priority_label = QLabel(t("assistant.priority", "Priorytet (1-10):"))
        self.priority_spin = QSpinBox()
        self.priority_spin.setRange(1, 10)
        self.priority_spin.setValue(5)
        self.priority_spin.setToolTip(t("assistant.priority_tooltip", "Wyższy = ważniejszy"))
        priority_layout.addWidget(priority_label)
        priority_layout.addWidget(self.priority_spin)
        priority_layout.addStretch()
        layout.addLayout(priority_layout)
        
        # Aktywna
        self.active_checkbox = QCheckBox(t("assistant.is_active", "Fraza aktywna"))
        self.active_checkbox.setChecked(True)
        layout.addWidget(self.active_checkbox)
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
    
    def _load_phrase_data(self):
        """Załaduj dane frazy do formularza."""
        if self.phrase:
            self.phrase_input.setText(self.phrase.phrase)
            self.lang_combo.setCurrentText(self.phrase.language)
            self.priority_spin.setValue(self.phrase.priority)
            self.active_checkbox.setChecked(self.phrase.is_active)
    
    def get_phrase_data(self) -> dict:
        """Pobierz dane z formularza."""
        return {
            'phrase': self.phrase_input.text().strip(),
            'language': self.lang_combo.currentText(),
            'priority': self.priority_spin.value(),
            'is_active': self.active_checkbox.isChecked()
        }


class AssistantSettingsTab(QWidget):
    """Karta ustawień asystenta."""
    
    phrases_changed = pyqtSignal()  # Emitowane gdy frazy się zmienią
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Menedżer ustawień
        self.settings_manager = AssistantSettingsManager()
        
        # Menedżer motywów
        self.theme_manager = get_theme_manager() if THEME_AVAILABLE else None
        self.colors = {}
        
        # Stan UI
        self.current_method: str = ""  # Aktualnie wybrana funkcja
        self.current_language: Optional[str] = "pl"  # Filtr języka
        
        self._setup_ui()
        self._load_methods()
        
        # Zastosuj motyw
        if self.theme_manager:
            self.apply_theme()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu karty."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(15)

        
        # Opis
        desc = QLabel(t(
            "assistant.settings_description",
            "Zarządzaj frazami wywołującymi funkcje asystenta. "
            "Możesz dodawać własne frazy i edytować istniejące."
        ))
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Splitter: lista funkcji | lista fraz
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # === LEWA STRONA: Lista funkcji ===
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        methods_label = QLabel(t("assistant.available_functions", "Dostępne funkcje:"))
        methods_label_font = QFont()
        methods_label_font.setBold(True)
        methods_label.setFont(methods_label_font)
        left_layout.addWidget(methods_label)
        
        self.methods_list = QListWidget()
        self.methods_list.currentItemChanged.connect(self._on_method_selected)
        left_layout.addWidget(self.methods_list)
        
        splitter.addWidget(left_panel)
        
        # === PRAWA STRONA: Lista fraz ===
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        # Nagłówek i toolbar
        phrases_header = QHBoxLayout()
        
        self.phrases_label = QLabel(t("assistant.phrases", "Frazy"))
        phrases_label_font = QFont()
        phrases_label_font.setBold(True)
        self.phrases_label.setFont(phrases_label_font)
        phrases_header.addWidget(self.phrases_label)
        
        phrases_header.addStretch()
        
        # Filtr języka
        lang_label = QLabel(t("assistant.filter_language", "Język:"))
        phrases_header.addWidget(lang_label)
        
        self.lang_filter_combo = QComboBox()
        self.lang_filter_combo.addItems([
            t("assistant.all_languages", "Wszystkie"), 
            "pl", "en", "de"
        ])
        self.lang_filter_combo.currentTextChanged.connect(self._on_language_filter_changed)
        phrases_header.addWidget(self.lang_filter_combo)
        
        right_layout.addLayout(phrases_header)
        
        # Lista fraz
        self.phrases_list = QListWidget()
        self.phrases_list.itemDoubleClicked.connect(self._on_phrase_double_clicked)
        right_layout.addWidget(self.phrases_list)
        
        # Przyciski akcji
        buttons_layout = QHBoxLayout()
        
        self.btn_add_phrase = QPushButton("➕ " + t("assistant.add_phrase", "Dodaj frazę"))
        self.btn_add_phrase.clicked.connect(self._add_phrase)
        self.btn_add_phrase.setEnabled(False)
        buttons_layout.addWidget(self.btn_add_phrase)
        
        self.btn_edit_phrase = QPushButton("✏️ " + t("assistant.edit", "Edytuj"))
        self.btn_edit_phrase.clicked.connect(self._edit_phrase)
        self.btn_edit_phrase.setEnabled(False)
        buttons_layout.addWidget(self.btn_edit_phrase)
        
        self.btn_toggle_phrase = QPushButton("🔄 " + t("assistant.toggle", "Aktywuj/Deaktywuj"))
        self.btn_toggle_phrase.clicked.connect(self._toggle_phrase)
        self.btn_toggle_phrase.setEnabled(False)
        buttons_layout.addWidget(self.btn_toggle_phrase)
        
        self.btn_delete_phrase = QPushButton("🗑️ " + t("assistant.delete", "Usuń"))
        self.btn_delete_phrase.clicked.connect(self._delete_phrase)
        self.btn_delete_phrase.setEnabled(False)
        buttons_layout.addWidget(self.btn_delete_phrase)
        
        buttons_layout.addStretch()
        right_layout.addLayout(buttons_layout)
        
        splitter.addWidget(right_panel)
        
        # Ustaw proporcje: 40% funkcje, 60% frazy
        splitter.setSizes([400, 600])
        
        layout.addWidget(splitter)
        
        # Pomocnicze info na dole
        info_label = QLabel(
            t("assistant.help_text",
              "💡 Wskazówka: Kliknij dwukrotnie na frazę aby ją edytować. "
              "Domyślne frazy można dezaktywować, ale nie usuwać.")
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(info_label)
    
    def _load_methods(self):
        """Załaduj listę dostępnych funkcji asystenta."""
        self.methods_list.clear()
        
        methods = self.settings_manager.get_all_methods()
        
        for method_name, method_info in methods.items():
            # Nazwa funkcji z opisem
            display_name = method_info.get('name_pl', method_name)
            description = method_info.get('description_pl', '')
            
            item = QListWidgetItem(f"{display_name}\n{description}")
            item.setData(Qt.ItemDataRole.UserRole, method_name)
            
            self.methods_list.addItem(item)
        
        # Zaznacz pierwszą funkcję
        if self.methods_list.count() > 0:
            self.methods_list.setCurrentRow(0)
    
    def _on_method_selected(self, current: QListWidgetItem, previous: QListWidgetItem):
        """Callback gdy użytkownik wybierze funkcję."""
        if not current:
            self.current_method = ""
            self.btn_add_phrase.setEnabled(False)
            self.phrases_list.clear()
            return
        
        self.current_method = current.data(Qt.ItemDataRole.UserRole)
        self.btn_add_phrase.setEnabled(True)
        
        # Zaktualizuj nagłówek
        methods = self.settings_manager.get_all_methods()
        method_info = methods.get(self.current_method, {})
        method_name_display = method_info.get('name_pl', self.current_method)
        
        self.phrases_label.setText(
            t("assistant.phrases_for", "Frazy dla: {0}").format(method_name_display)
        )
        
        # Załaduj frazy
        self._load_phrases()
    
    def _on_language_filter_changed(self, language: str):
        """Callback gdy użytkownik zmieni filtr języka."""
        if language == t("assistant.all_languages", "Wszystkie"):
            self.current_language = None
        else:
            self.current_language = language
        
        self._load_phrases()
    
    def _load_phrases(self):
        """Załaduj frazy dla aktualnie wybranej funkcji."""
        self.phrases_list.clear()
        
        if not self.current_method:
            return
        
        # Pobierz frazy z filtrem języka
        lang_filter = None if self.current_language is None else self.current_language
        phrases = self.settings_manager.get_phrases_for_method(
            self.current_method, 
            language=lang_filter
        )
        
        for phrase in phrases:
            # Format wyświetlania: "fraza (język) [priorytet] ✓/✗"
            status = "✓" if phrase.is_active else "✗"
            custom_marker = "👤" if phrase.is_custom else "⚙️"
            
            display_text = f"{custom_marker} {phrase.phrase} ({phrase.language}) [{phrase.priority}] {status}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, phrase.id)
            
            # Kolor: aktywne = normalne, nieaktywne = szare
            if not phrase.is_active:
                item.setForeground(Qt.GlobalColor.gray)
            
            self.phrases_list.addItem(item)
        
        # Zaktualizuj stan przycisków
        self._update_buttons_state()
    
    def _update_buttons_state(self):
        """Aktualizuj stan przycisków w zależności od zaznaczenia."""
        has_selection = self.phrases_list.currentItem() is not None
        
        self.btn_edit_phrase.setEnabled(has_selection)
        self.btn_toggle_phrase.setEnabled(has_selection)
        
        # Przycisk usuń: tylko dla własnych fraz
        if has_selection:
            current_item = self.phrases_list.currentItem()
            if current_item:
                phrase_id = current_item.data(Qt.ItemDataRole.UserRole)
                phrase = self.settings_manager.get_phrase(phrase_id)
                self.btn_delete_phrase.setEnabled(bool(phrase and phrase.is_custom))
            else:
                self.btn_delete_phrase.setEnabled(False)
        else:
            self.btn_delete_phrase.setEnabled(False)
    
    def _add_phrase(self):
        """Dodaj nową frazę."""
        if not self.current_method:
            return
        
        dialog = PhraseEditDialog(method_name=self.current_method, parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_phrase_data()
            
            if not data['phrase']:
                QMessageBox.warning(
                    self,
                    t("assistant.error", "Błąd"),
                    t("assistant.phrase_empty", "Fraza nie może być pusta")
                )
                return
            
            # Rozdziel method_name na module i action
            parts = self.current_method.split(".", 1)
            if len(parts) != 2:
                logger.error(f"[AssistantSettings] Invalid method_name: {self.current_method}")
                return
            
            module, action = parts
            
            # Dodaj frazę
            self.settings_manager.add_phrase(
                module=module,
                action=action,
                phrase=data['phrase'],
                language=data['language'],
                priority=data['priority'],
                is_custom=True,
            )
            
            # Odśwież listę
            self._load_phrases()
            self.phrases_changed.emit()
            
            logger.info(f"[AssistantSettings] Added phrase: '{data['phrase']}' for {self.current_method}")
    
    def _edit_phrase(self):
        """Edytuj wybraną frazę."""
        item = self.phrases_list.currentItem()
        if not item:
            return
        
        phrase_id = item.data(Qt.ItemDataRole.UserRole)
        phrase = self.settings_manager.get_phrase(phrase_id)
        
        if not phrase:
            return
        
        dialog = PhraseEditDialog(phrase=phrase, parent=self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_phrase_data()
            
            if not data['phrase']:
                QMessageBox.warning(
                    self,
                    t("assistant.error", "Błąd"),
                    t("assistant.phrase_empty", "Fraza nie może być pusta")
                )
                return
            
            # Utwórz zaktualizowany obiekt frazy
            from dataclasses import replace
            updated_phrase = replace(
                phrase,
                phrase=data['phrase'],
                language=data['language'],
                priority=data['priority'],
                is_active=data['is_active']
            )
            
            # Aktualizuj frazę w bazie
            self.settings_manager.update_phrase(updated_phrase)
            
            # Odśwież listę
            self._load_phrases()
            self.phrases_changed.emit()
            
            logger.info(f"[AssistantSettings] Updated phrase: {phrase_id}")
    
    def _toggle_phrase(self):
        """Przełącz aktywność frazy."""
        item = self.phrases_list.currentItem()
        if not item:
            return
        
        phrase_id = item.data(Qt.ItemDataRole.UserRole)
        new_state = self.settings_manager.toggle_phrase(phrase_id)
        
        # Odśwież listę
        self._load_phrases()
        self.phrases_changed.emit()
        
        logger.info(f"[AssistantSettings] Toggled phrase {phrase_id}: {new_state}")
    
    def _delete_phrase(self):
        """Usuń wybraną frazę (tylko własne)."""
        item = self.phrases_list.currentItem()
        if not item:
            return
        
        phrase_id = item.data(Qt.ItemDataRole.UserRole)
        phrase = self.settings_manager.get_phrase(phrase_id)
        
        if not phrase or not phrase.is_custom:
            QMessageBox.warning(
                self,
                t("assistant.error", "Błąd"),
                t("assistant.cannot_delete_default", "Nie można usunąć domyślnej frazy")
            )
            return
        
        # Potwierdzenie
        reply = QMessageBox.question(
            self,
            t("assistant.confirm_delete", "Potwierdź usunięcie"),
            t("assistant.confirm_delete_phrase", "Czy na pewno usunąć frazę '{0}'?").format(phrase.phrase),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.settings_manager.delete_phrase(phrase_id)
            
            # Odśwież listę
            self._load_phrases()
            self.phrases_changed.emit()
            
            logger.info(f"[AssistantSettings] Deleted phrase: {phrase_id}")
    
    def _on_phrase_double_clicked(self, item: QListWidgetItem):
        """Callback gdy użytkownik kliknie dwukrotnie na frazę."""
        self._edit_phrase()
    
    def update_translations(self):
        """Zaktualizuj tłumaczenia."""
        # Odśwież listę metod (zawierają tłumaczenia)
        self._load_methods()
        
        # Odśwież listę fraz jeśli jest wybrana metoda
        if self.current_method:
            self._load_phrases()
    
    def apply_theme(self):
        """Aplikuje aktualny motyw do karty asystenta."""
        if not self.theme_manager:
            logger.warning("[ASSISTANT_SETTINGS] Theme manager not available")
            return
        
        # Odśwież kolory z aktualnego schematu
        self.colors = self.theme_manager.get_current_colors()
        
        # Pobierz podstawowe kolory
        bg_main = self.colors.get("bg_main", "#FFFFFF")
        bg_secondary = self.colors.get("bg_secondary", "#F5F5F5")
        text_primary = self.colors.get("text_primary", "#1A1A1A")
        text_secondary = self.colors.get("text_secondary", "#666666")
        accent_primary = self.colors.get("accent_primary", "#2196F3")
        accent_hover = self.colors.get("accent_hover", "#1976D2")
        border_light = self.colors.get("border_light", "#CCCCCC")
        
        # Stylesheet dla całej karty
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_main};
                color: {text_primary};
            }}
            
            QLabel {{
                color: {text_primary};
            }}
            
            QListWidget {{
                background-color: {bg_secondary};
                color: {text_primary};
                border: 1px solid {border_light};
                border-radius: 4px;
                padding: 4px;
            }}
            
            QListWidget::item {{
                padding: 6px;
                border-radius: 3px;
            }}
            
            QListWidget::item:selected {{
                background-color: {accent_primary};
                color: white;
            }}
            
            QListWidget::item:hover {{
                background-color: {accent_hover};
                color: white;
            }}
            
            QPushButton {{
                background-color: {accent_primary};
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 4px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
            
            QPushButton:disabled {{
                background-color: {border_light};
                color: {text_secondary};
            }}
            
            QComboBox {{
                background-color: {bg_secondary};
                color: {text_primary};
                border: 1px solid {border_light};
                border-radius: 4px;
                padding: 4px 8px;
                min-width: 100px;
            }}
            
            QComboBox:hover {{
                border: 1px solid {accent_primary};
            }}
            
            QComboBox::drop-down {{
                border: none;
            }}
            
            QComboBox QAbstractItemView {{
                background-color: {bg_secondary};
                color: {text_primary};
                selection-background-color: {accent_primary};
                selection-color: white;
                border: 1px solid {border_light};
            }}
        """)
        
        logger.info("[ASSISTANT_SETTINGS] Theme applied successfully")


__all__ = ["AssistantSettingsTab"]
