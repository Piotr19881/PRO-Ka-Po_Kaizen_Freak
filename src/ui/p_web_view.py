"""
P-Web View - Interfejs użytkownika modułu przeglądarki internetowej

Widok zintegrowany z:
- Systemem i18n (tłumaczenia)
- Theme Managerem (zarządzanie kolorami)
- P-Web Logic (logika biznesowa)
- Menu kontekstowym (integracja z notatkami i zadaniami)

UWAGA: Wymaga PyQt6-WebEngine (pip install PyQt6-WebEngine)
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QComboBox,
    QLabel, QDialog, QDialogButtonBox, QLineEdit, QMessageBox,
    QColorDialog, QListWidget, QListWidgetItem, QStyledItemDelegate,
    QMenu
)
from PyQt6.QtCore import Qt, QUrl, QPoint
from PyQt6.QtGui import QColor, QPainter, QAction

# Warunkowy import QtWebEngine - może nie być zainstalowany
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEnginePage
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    # Fallback - używamy pustej klasy
    QWebEngineView = type('QWebEngineView', (QWidget,), {})
    QWebEngineProfile = type('QWebEngineProfile', (), {})
    QWebEnginePage = type('QWebEnginePage', (), {})

from loguru import logger

from ..Modules.p_web.p_web_logic import PWebLogic
from ..utils.i18n_manager import t, get_i18n


# CustomWebEnginePage - tylko jeśli WebEngine jest dostępny
if WEBENGINE_AVAILABLE:
    class CustomWebEnginePage(QWebEnginePage):
        """Własna klasa QWebEnginePage z menu kontekstowym"""
        
        def __init__(self, parent_view, profile, parent=None):
            super().__init__(profile, parent)
            self.parent_view = parent_view
        
        def createStandardContextMenu(self):
            """Tworzy własne menu kontekstowe z dodatkowymi opcjami"""
            menu = QMenu()
            
            # Pobierz zaznaczony tekst i dane kontekstu
            selected_text = self.selectedText()
            hit_test_result = self.contextMenuData()
            link_url = hit_test_result.linkUrl().toString() if hit_test_result.linkUrl().isValid() else None
            
            # Kopiuj (jeśli jest zaznaczony tekst)
            if selected_text:
                copy_action = menu.addAction(t("pweb.context.copy"))
                copy_action.triggered.connect(lambda: self.triggerAction(QWebEnginePage.WebAction.Copy))
            
            # Wklej
            paste_action = menu.addAction(t("pweb.context.paste"))
            paste_action.triggered.connect(lambda: self.triggerAction(QWebEnginePage.WebAction.Paste))
            
            # Kopiuj link (jeśli kursor jest nad linkiem)
            if link_url:
                menu.addSeparator()
                copy_link_action = menu.addAction(t("pweb.context.copy_link"))
                copy_link_action.triggered.connect(lambda: self._copy_link_to_clipboard(link_url))
                
                # Otwórz link w domyślnej przeglądarce
                open_link_action = menu.addAction(t("pweb.context.open_link_external"))
                open_link_action.triggered.connect(lambda: self._open_link_in_external_browser(link_url))
            
            # Otwórz stronę w domyślnej przeglądarce
            menu.addSeparator()
            current_url = self.url().toString()
            if current_url and current_url != "about:blank":
                open_page_action = menu.addAction(t("pweb.context.open_page_external"))
                open_page_action.triggered.connect(lambda: self._open_link_in_external_browser(current_url))
            
            # Akcje integracji z aplikacją (jeśli jest zaznaczony tekst)
            if selected_text:
                menu.addSeparator()
                # Utwórz notatkę
                create_note_action = QAction(t("pweb.context.create_note"), menu)
                create_note_action.triggered.connect(
                    lambda: self.parent_view._create_note_from_selection(selected_text)
                )
                menu.addAction(create_note_action)
                
                # Utwórz zadanie
                create_task_action = QAction(t("pweb.context.create_task"), menu)
                create_task_action.triggered.connect(
                    lambda: self.parent_view._create_task_from_selection(selected_text)
                )
                menu.addAction(create_task_action)
            
            return menu
        
        def _copy_link_to_clipboard(self, url: str):
            """Kopiuje URL do schowka"""
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(url)
        
        def _open_link_in_external_browser(self, url: str):
            """Otwiera URL w domyślnej przeglądarce systemowej"""
            import webbrowser
            webbrowser.open(url)
else:
    # Fallback - pusta klasa
    CustomWebEnginePage = None


class ColoredComboBoxDelegate(QStyledItemDelegate):
    """Delegat dla kolorowych elementów ComboBox"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.colors = {}
    
    def set_item_color(self, index: int, color: QColor):
        """Ustawia kolor dla elementu o podanym indeksie"""
        self.colors[index] = color
    
    def clear_colors(self):
        """Czyści wszystkie kolory"""
        self.colors.clear()
    
    def paint(self, painter, option, index):
        """Rysuje element z kolorowym tłem"""
        if index.row() in self.colors:
            color = self.colors[index.row()]
            painter.fillRect(option.rect, color)
            
            # Dobór koloru tekstu (jasny/ciemny) w zależności od tła
            if PWebLogic.is_dark_color(color.name()):
                text_color = QColor(255, 255, 255)
            else:
                text_color = QColor(0, 0, 0)
            
            painter.setPen(text_color)
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft, 
                           " " + index.data(Qt.ItemDataRole.DisplayRole))
        else:
            super().paint(painter, option, index)


class AddBookmarkDialog(QDialog):
    """Dialog do dodawania nowych zakładek"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.resize(500, 200)
        
        # Domyślny kolor
        self.selected_color = QColor("#4CAF50")
        
        self._setup_ui()
        
        # Połącz z i18n
        get_i18n().language_changed.connect(self.update_translations)
        self.update_translations()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        layout = QVBoxLayout(self)
        
        # Nazwa strony
        self.name_label = QLabel()
        self.name_label.setObjectName("pweb_add_name_label")
        layout.addWidget(self.name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setObjectName("pweb_add_name_input")
        layout.addWidget(self.name_input)
        
        # Adres URL
        self.url_label = QLabel()
        self.url_label.setObjectName("pweb_add_url_label")
        layout.addWidget(self.url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setObjectName("pweb_add_url_input")
        layout.addWidget(self.url_input)
        
        # Wybór koloru
        color_layout = QHBoxLayout()
        
        self.color_label = QLabel()
        self.color_label.setObjectName("pweb_add_color_label")
        color_layout.addWidget(self.color_label)
        
        self.color_preview = QWidget()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.setObjectName("pweb_color_preview")
        self.update_color_preview()
        color_layout.addWidget(self.color_preview)
        
        self.color_button = QPushButton()
        self.color_button.setObjectName("pweb_choose_color_button")
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_button)
        
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # Przyciski
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.setObjectName("pweb_add_button_box")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def choose_color(self):
        """Otwiera dialog wyboru koloru"""
        color = QColorDialog.getColor(self.selected_color, self, t("pweb.add_dialog_choose_color"))
        if color.isValid():
            self.selected_color = color
            self.update_color_preview()
    
    def update_color_preview(self):
        """Aktualizuje podgląd wybranego koloru"""
        self.color_preview.setStyleSheet(
            f"background-color: {self.selected_color.name()}; border: 1px solid #000;"
        )
    
    def get_data(self):
        """Zwraca wprowadzone dane"""
        return {
            'name': self.name_input.text().strip(),
            'url': self.url_input.text().strip(),
            'color': self.selected_color.name()
        }
    
    def update_translations(self):
        """Aktualizuje tłumaczenia w dialogu"""
        self.setWindowTitle(t("pweb.add_dialog_title"))
        self.name_label.setText(t("pweb.add_dialog_name_label"))
        self.name_input.setPlaceholderText(t("pweb.add_dialog_name_placeholder"))
        self.url_label.setText(t("pweb.add_dialog_url_label"))
        self.url_input.setPlaceholderText(t("pweb.add_dialog_url_placeholder"))
        self.color_label.setText(t("pweb.add_dialog_color_label"))
        self.color_button.setText(t("pweb.add_dialog_choose_color"))
        self.color_button.setToolTip(t("pweb.add_dialog_color_tooltip"))


class DeleteBookmarkDialog(QDialog):
    """Dialog do usuwania zapisanych zakładek"""
    
    def __init__(self, bookmarks, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.resize(400, 300)
        
        self.bookmarks = bookmarks
        self.selected_bookmark = None
        
        self._setup_ui()
        self._populate_list()
        
        # Połącz z i18n
        get_i18n().language_changed.connect(self.update_translations)
        self.update_translations()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        layout = QVBoxLayout(self)
        
        self.info_label = QLabel()
        self.info_label.setObjectName("pweb_delete_info_label")
        layout.addWidget(self.info_label)
        
        # Lista zakładek
        self.bookmark_list = QListWidget()
        self.bookmark_list.setObjectName("pweb_delete_list")
        layout.addWidget(self.bookmark_list)
        
        # Przyciski
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.setObjectName("pweb_delete_button_box")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def _populate_list(self):
        """Wypełnia listę zakładkami"""
        self.bookmark_list.clear()
        
        for bookmark in self.bookmarks:
            item = QListWidgetItem(bookmark['name'])
            item.setData(Qt.ItemDataRole.UserRole, bookmark)
            
            # Ustawienie koloru tła
            color = QColor(bookmark['color'])
            item.setBackground(color)
            
            # Dobór koloru tekstu (jasny/ciemny) w zależności od tła
            if PWebLogic.is_dark_color(bookmark['color']):
                item.setForeground(QColor(255, 255, 255))
            else:
                item.setForeground(QColor(0, 0, 0))
            
            self.bookmark_list.addItem(item)
    
    def accept(self):
        """Zapisuje wybraną zakładkę przed zamknięciem"""
        current_item = self.bookmark_list.currentItem()
        if current_item:
            self.selected_bookmark = current_item.data(Qt.ItemDataRole.UserRole)
            super().accept()
        else:
            QMessageBox.warning(self, t("pweb.delete_dialog_title"), t("pweb.error_select_page"))
    
    def update_translations(self):
        """Aktualizuje tłumaczenia w dialogu"""
        self.setWindowTitle(t("pweb.delete_dialog_title"))
        self.info_label.setText(t("pweb.delete_dialog_label"))


class PWebView(QWidget):
    """Widok P-Web - Przeglądarka internetowa z kolorowymi zakładkami"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Sprawdź czy QtWebEngine jest dostępny
        if not WEBENGINE_AVAILABLE:
            logger.error("[PWebView] QtWebEngine not available - P-Web module disabled")
            self._show_webengine_error()
            return
        
        # Logika biznesowa
        self.logic = PWebLogic()
        
        # Theme manager - pobierz singleton
        try:
            from src.utils.theme_manager import get_theme_manager
            self.theme_manager = get_theme_manager()
        except Exception as e:
            logger.warning(f"[PWebView] Could not get theme manager: {e}")
            self.theme_manager = None
        
        # UI
        self._setup_ui()
        
        # Połącz z i18n
        get_i18n().language_changed.connect(self.update_translations)
        
        # Załaduj początkowe tłumaczenia i motyw
        self.update_translations()
        
        # Wczytaj zakładki
        self._load_bookmarks()
        
        logger.info("[PWebView] Initialized")
    
    def _show_webengine_error(self):
        """Pokazuje komunikat o braku QtWebEngine"""
        layout = QVBoxLayout(self)
        
        error_label = QLabel()
        error_label.setObjectName("pweb_error_label")
        error_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        error_label.setWordWrap(True)
        error_label.setText(
            "<h2>⚠️ Moduł P-Web niedostępny</h2>"
            "<p>Brak wymaganego pakietu <b>PyQt6-WebEngine</b></p>"
            "<p>Aby korzystać z przeglądarki P-Web, zainstaluj pakiet:</p>"
            "<pre>pip install PyQt6-WebEngine</pre>"
            "<p>Następnie uruchom aplikację ponownie.</p>"
        )
        layout.addWidget(error_label)
        self.update_translations()
        
        # Wczytaj zakładki
        self._load_bookmarks()
        
        logger.info("[PWebView] Initialized")
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Pasek narzędzi
        toolbar_layout = QHBoxLayout()
        
        # Przycisk Wstecz (po lewej)
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("pweb_back_button")
        self.btn_back.clicked.connect(self._go_back)
        toolbar_layout.addWidget(self.btn_back)
        
        # Lista zapisanych stron (ComboBox)
        self.page_label = QLabel()
        self.page_label.setObjectName("pweb_page_label")
        toolbar_layout.addWidget(self.page_label)
        
        self.page_combo = QComboBox()
        self.page_combo.setObjectName("pweb_page_combo")
        self.page_combo.setMinimumWidth(200)
        self.page_combo.currentIndexChanged.connect(self._on_page_selected)
        
        # Ustawienie delegata dla kolorowych elementów
        self.combo_delegate = ColoredComboBoxDelegate(self.page_combo)
        self.page_combo.setItemDelegate(self.combo_delegate)
        
        toolbar_layout.addWidget(self.page_combo)
        
        # Przycisk Odśwież
        self.btn_refresh = QPushButton()
        self.btn_refresh.setObjectName("pweb_refresh_button")
        self.btn_refresh.clicked.connect(self._refresh_page)
        toolbar_layout.addWidget(self.btn_refresh)
        
        # Separator - reszta przycisków po prawej
        toolbar_layout.addStretch()
        
        # Przycisk Dodaj stronę (po prawej)
        self.btn_add = QPushButton()
        self.btn_add.setObjectName("pweb_add_button")
        self.btn_add.clicked.connect(self._add_bookmark)
        toolbar_layout.addWidget(self.btn_add)
        
        # Przycisk Usuń stronę (po prawej)
        self.btn_delete = QPushButton()
        self.btn_delete.setObjectName("pweb_delete_button")
        self.btn_delete.clicked.connect(self._delete_bookmark)
        toolbar_layout.addWidget(self.btn_delete)
        
        main_layout.addLayout(toolbar_layout)
        
        # Widok przeglądarki z trwałym profilem
        self.web_view = QWebEngineView()
        self.web_view.setObjectName("pweb_web_view")
        self.web_view.setUrl(QUrl("about:blank"))
        main_layout.addWidget(self.web_view)
        
        # Konfiguruj profil AFTER creating web_view
        self._setup_browser_profile()
    
    def _setup_browser_profile(self):
        """Konfiguracja profilu przeglądarki do zapisywania danych"""
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'web_view'):
            return
            
        # Ścieżka do katalogu profilu przeglądarki
        profile_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'data', 'browser_profile'
        )
        os.makedirs(profile_path, exist_ok=True)
        
        # Konfiguracja domyślnego profilu
        from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setPersistentStoragePath(profile_path)
        self.profile.setCachePath(os.path.join(profile_path, "cache"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        
        # Konfiguruj ustawienia przeglądarki dla obsługi motywów
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        # Synchronizuj z aktualnym motywem aplikacji
        self._apply_browser_theme()
        
        # Utwórz własną stronę z menu kontekstowym
        if CustomWebEnginePage:
            self.web_page = CustomWebEnginePage(self, self.profile)
            self.web_view.setPage(self.web_page)
    
    def _apply_browser_theme(self):
        """Stosuje motyw aplikacji do przeglądarki"""
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'web_view'):
            return
        
        try:
            from PyQt6.QtGui import QColor, QPalette
            
            # Pobierz kolory z aktualnego motywu
            if self.theme_manager:
                colors = self.theme_manager.get_current_colors()
                bg_color = colors.get('bg_main', '#FFFFFF')
            else:
                # Fallback - próba odczytania z palety aplikacji
                from PyQt6.QtWidgets import QApplication
                app = QApplication.instance()
                if app:
                    palette = app.palette()
                    bg_color = palette.color(QPalette.ColorRole.Base).name()
                else:
                    bg_color = '#FFFFFF'
            
            # Ustaw kolor tła dla przeglądarki
            self.web_view.page().setBackgroundColor(QColor(bg_color))
            
            logger.debug(f"[PWebView] Applied browser theme with background: {bg_color}")
        except Exception as e:
            logger.warning(f"[PWebView] Could not apply browser theme: {e}")
    
    def _load_bookmarks(self):
        """Wczytuje zakładki i aktualizuje interfejs"""
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'logic'):
            return
            
        success, error = self.logic.load_bookmarks()
        
        if not success:
            QMessageBox.warning(
                self,
                t("pweb.title"),
                t("pweb.error_load_json")
            )
            logger.warning(f"[PWebView] Failed to load bookmarks: {error}")
        
        self._update_bookmark_combo()
    
    def _update_bookmark_combo(self):
        """Aktualizuje listę rozwijaną z zakładkami"""
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'page_combo'):
            return
            
        self.page_combo.blockSignals(True)
        self.page_combo.clear()
        
        # Czyszczenie kolorów w delegacie
        self.combo_delegate.clear_colors()
        
        bookmarks = self.logic.get_bookmarks()
        for i, bookmark in enumerate(bookmarks):
            self.page_combo.addItem(bookmark['name'], bookmark)
            color = QColor(bookmark['color'])
            
            # Ustawienie koloru w delegacie
            self.combo_delegate.set_item_color(i, color)
        
        self.page_combo.blockSignals(False)
    
    def _on_page_selected(self, index: int):
        """Obsługa wyboru zakładki z listy"""
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'web_view'):
            return
            
        if index >= 0:
            bookmark = self.logic.get_bookmark(index)
            if bookmark:
                url = PWebLogic.normalize_url(bookmark['url'])
                self.web_view.setUrl(QUrl(url))
                logger.debug(f"[PWebView] Navigating to: {url}")
    
    def _add_bookmark(self):
        """Dodaje nową zakładkę"""
        if not WEBENGINE_AVAILABLE:
            return
            
        dialog = AddBookmarkDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            # Dodanie przez logikę
            success, error = self.logic.add_bookmark(
                data['name'],
                data['url'],
                data['color']
            )
            
            if success:
                self._update_bookmark_combo()
                # Automatyczne przejście do nowo dodanej zakładki
                new_index = len(self.logic.get_bookmarks()) - 1
                self.page_combo.setCurrentIndex(new_index)
                
                # Jawnie załaduj stronę (na wypadek gdyby sygnał currentIndexChanged nie został wywołany)
                bookmark = self.logic.get_bookmark(new_index)
                if bookmark:
                    url = PWebLogic.normalize_url(bookmark['url'])
                    self.web_view.setUrl(QUrl(url))
                    logger.debug(f"[PWebView] Navigating to newly added bookmark: {url}")
                
                logger.info(f"[PWebView] Added bookmark: {data['name']}")
            else:
                # Obsługa błędów
                if error == "no_name":
                    QMessageBox.warning(self, t("pweb.title"), t("pweb.error_no_name"))
                elif error == "no_url":
                    QMessageBox.warning(self, t("pweb.title"), t("pweb.error_no_url"))
                elif error.startswith("save_error:"):
                    save_error = error.split(":", 1)[1]
                    QMessageBox.critical(self, t("pweb.title"), t("pweb.error_save_json").format(save_error))
                
                logger.error(f"[PWebView] Failed to add bookmark: {error}")
    
    def _delete_bookmark(self):
        """Usuwa wybraną zakładkę"""
        if not WEBENGINE_AVAILABLE:
            return
            
        bookmarks = self.logic.get_bookmarks()
        
        if not bookmarks:
            QMessageBox.information(self, t("pweb.title"), t("pweb.info_no_pages"))
            return
        
        dialog = DeleteBookmarkDialog(bookmarks, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected_bookmark:
                success, error = self.logic.delete_bookmark_by_data(dialog.selected_bookmark)
                
                if success:
                    self._update_bookmark_combo()
                    
                    # Wczytanie pierwszej zakładki lub pustej strony
                    if self.logic.get_bookmarks():
                        self.page_combo.setCurrentIndex(0)
                    else:
                        self.web_view.setUrl(QUrl("about:blank"))
                    
                    logger.info(f"[PWebView] Deleted bookmark: {dialog.selected_bookmark['name']}")
                else:
                    if error.startswith("save_error:"):
                        save_error = error.split(":", 1)[1]
                        QMessageBox.critical(self, t("pweb.title"), t("pweb.error_save_json").format(save_error))
                    
                    logger.error(f"[PWebView] Failed to delete bookmark: {error}")
    
    def _refresh_page(self):
        """Odświeża aktualną stronę"""
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'web_view'):
            return
            
        self.web_view.reload()
        logger.debug("[PWebView] Page refreshed")
    
    def _go_back(self):
        """Wraca do poprzedniej strony w historii"""
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'web_view'):
            return
            
        if self.web_view.history().canGoBack():
            self.web_view.back()
            logger.debug("[PWebView] Navigated back")
    
    def update_translations(self):
        """Aktualizuje tłumaczenia w widoku"""
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'btn_back'):
            return
            
        self.btn_back.setText(t("pweb.back"))
        self.page_label.setText(t("pweb.page_label"))
        self.btn_refresh.setText(t("pweb.refresh"))
        self.btn_add.setText(t("pweb.add_page"))
        self.btn_delete.setText(t("pweb.delete_page"))
        
        # Aktualizuj motyw przeglądarki (może się zmienić przy zmianie języka/motywu)
        self._apply_browser_theme()
        
        logger.debug("[PWebView] Translations updated")
    
    def _create_note_from_selection(self, selected_text: str):
        """
        Tworzy notatkę z zaznaczonego tekstu
        Pierwsze 3 słowa → tytuł, cała treść → zawartość notatki
        """
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'web_view'):
            logger.warning("[PWebView] Cannot create note - WebEngine not available")
            return
            
        if not selected_text or not selected_text.strip():
            logger.warning("[PWebView] No text selected for note creation")
            return
        
        # Pobierz główne okno (PWebView -> QStackedWidget -> central_widget -> MainWindow)
        content_stack = self.parent()
        central_widget = content_stack.parent() if content_stack else None
        main_window = central_widget.parent() if central_widget else None
        
        logger.info(f"[PWebView] content_stack={content_stack}, type={type(content_stack)}")
        logger.info(f"[PWebView] central_widget={central_widget}, type={type(central_widget)}")
        logger.info(f"[PWebView] main_window={main_window}, type={type(main_window)}")
        
        if not main_window:
            logger.error("[PWebView] Cannot access main_window - parent chain broken")
            QMessageBox.warning(
                self,
                t('pweb.title'),
                t('pweb.error.no_main_window')
            )
            return
        
        if not hasattr(main_window, 'notes_view'):
            logger.error("[PWebView] notes_view attribute not found on main_window")
            QMessageBox.warning(
                self,
                t('pweb.title'),
                t('pweb.error.no_notes_view')
            )
            return
        
        # Przygotuj dane notatki
        words = selected_text.strip().split()
        title_words = words[:3]
        note_title = " ".join(title_words)
        
        # Jeśli tytuł jest za krótki, dodaj "..."
        if len(note_title) < 10:
            note_title = note_title + "..."
        
        # Zawartość - cały zaznaczony tekst
        note_content = f"<p>{selected_text.replace(chr(10), '</p><p>')}</p>"
        
        # Dodaj metadane
        current_url = self.web_view.url().toString()
        current_page_title = self.web_view.title()
        
        note_content = (
            f"<p><b>Źródło:</b> <a href='{current_url}'>{current_page_title}</a></p>"
            f"<hr>"
            f"{note_content}"
        )
        
        try:
            # Utwórz notatkę
            new_note_id = main_window.notes_view.db.create_note(
                title=note_title,
                content=note_content,
                color="#2196F3"  # Niebieski dla notatek z przeglądarki
            )
            
            logger.info(f"[PWebView] Created note {new_note_id} from selection: '{note_title}'")
            
            # Przełącz na widok notatek
            main_window._on_view_changed("notes")
            
            # Odśwież drzewo notatek i wybierz nową notatkę
            def open_new_note():
                main_window.notes_view.refresh_tree()
                main_window.notes_view.select_note_in_tree(str(new_note_id))
            
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, open_new_note)
            
            # Pokaż komunikat o sukcesie
            QMessageBox.information(
                self,
                t('pweb.title'),
                t('pweb.success.note_created').format(title=note_title)
            )
            
        except Exception as e:
            logger.error(f"[PWebView] Error creating note: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.warning(
                self,
                t('pweb.title'),
                t('pweb.error.note_creation_failed').format(error=str(e))
            )
    
    def _create_task_from_selection(self, selected_text: str):
        """
        Tworzy zadanie z zaznaczonego tekstu
        Cały zaznaczony tekst → tytuł zadania
        """
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'web_view'):
            logger.warning("[PWebView] Cannot create task - WebEngine not available")
            return
            
        if not selected_text or not selected_text.strip():
            logger.warning("[PWebView] No text selected for task creation")
            return
        
        # Pobierz główne okno
        content_stack = self.parent()
        central_widget = content_stack.parent() if content_stack else None
        main_window = central_widget.parent() if central_widget else None
        
        if not main_window:
            logger.error("[PWebView] Cannot access main_window")
            QMessageBox.warning(
                self,
                t('pweb.title'),
                t('pweb.error.no_main_window')
            )
            return
        
        if not hasattr(main_window, 'task_view'):
            logger.error("[PWebView] task_view attribute not found on main_window")
            QMessageBox.warning(
                self,
                t('pweb.title'),
                t('pweb.error.no_task_view')
            )
            return
        
        # Przygotuj dane zadania
        task_title = selected_text.strip()
        
        # Ogranicz długość tytułu
        if len(task_title) > 100:
            task_title = task_title[:97] + "..."
        
        # Pobierz URL źródłowy
        current_url = self.web_view.url().toString()
        task_description = f"Źródło: {current_url}"
        
        try:
            # Utwórz zadanie przez task_view
            task_view = main_window.task_view
            
            # Dodaj zadanie do bazy danych
            task_id = task_view.db.add_task(
                title=task_title,
                description=task_description,
                priority=1,  # Normalny priorytet
                status='todo'
            )
            
            logger.info(f"[PWebView] Created task {task_id} from selection: '{task_title}'")
            
            # Przełącz na widok zadań
            main_window._on_view_changed("tasks")
            
            # Odśwież widok zadań
            from PyQt6.QtCore import QTimer
            QTimer.singleShot(100, task_view.load_tasks)
            
            # Pokaż komunikat o sukcesie
            QMessageBox.information(
                self,
                t('pweb.title'),
                t('pweb.success.task_created').format(title=task_title)
            )
            
        except Exception as e:
            logger.error(f"[PWebView] Error creating task: {e}")
            import traceback
            logger.error(traceback.format_exc())
            QMessageBox.warning(
                self,
                t('pweb.title'),
                t('pweb.error.task_creation_failed').format(error=str(e))
            )

