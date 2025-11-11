"""
P-Web View V2 - Interfejs użytkownika z drzewem grup

Widok zintegrowany z:
- Systemem i18n (tłumaczenia)
- Theme Managerem (zarządzanie kolorami)
- P-Web Logic (logika biznesowa)
- Drzewem zakładek z grupami i tagami
- Menu kontekstowym (integracja z notatkami i zadaniami)

UWAGA: Wymaga PyQt6-WebEngine (pip install PyQt6-WebEngine)
"""

import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QMessageBox, QSplitter
)
from PyQt6.QtCore import Qt, QUrl, QTimer
from PyQt6.QtGui import QColor

# Warunkowy import QtWebEngine - może nie być zainstalowany
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    QWebEngineView = type('QWebEngineView', (QWidget,), {})
    QWebEngineProfile = type('QWebEngineProfile', (), {})
    QWebEngineSettings = type('QWebEngineSettings', (), {})

from loguru import logger

from ..Modules.p_web.p_web_logic import PWebLogic
from ..Modules.p_web.p_web_tree_widget import PWebTreeWidget
from ..Modules.p_web.p_web_context_menu import CustomWebEnginePage
from ..utils.i18n_manager import t, get_i18n
from .simple_pweb_dialogs import (
    GroupManagerDialog, TagManagerDialog, QuickOpenDialog, AddBookmarkDialog,
    SplitViewSelectDialog
)


class PWebView(QWidget):
    """Widok P-Web - Przeglądarka internetowa z drzewem grup"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Sprawdź czy QtWebEngine jest dostępny
        if not WEBENGINE_AVAILABLE:
            logger.error("[PWebView] QtWebEngine not available - P-Web module disabled")
            self._show_webengine_error()
            return
        
        # Logika biznesowa
        self.logic = PWebLogic()
        
        # Stan UI
        self.tree_visible = False  # Czy drzewo jest rozwinięte
        self.current_bookmark = None  # Aktualnie wybrana zakładka
        
        # Theme manager - pobierz singleton
        try:
            from src.utils.theme_manager import get_theme_manager
            self.theme_manager = get_theme_manager()
        except Exception as e:
            logger.warning(f"[PWebView] Could not get theme manager: {e}")
            self.theme_manager = None
        
        # UI
        self._setup_ui()
        self._connect_signals()
        
        # Połącz z i18n
        get_i18n().language_changed.connect(self.update_translations)
        
        # Załaduj początkowe tłumaczenia i motyw
        self.update_translations()
        
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
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # === Pasek narzędzi ===
        toolbar_layout = QHBoxLayout()
        
        # Przycisk Wstecz
        self.btn_back = QPushButton()
        self.btn_back.setObjectName("pweb_back_button")
        toolbar_layout.addWidget(self.btn_back)
        
        # Przycisk "Twoje strony" (toggle drzewa)
        self.btn_toggle_tree = QPushButton()
        self.btn_toggle_tree.setObjectName("pweb_toggle_tree_button")
        self.btn_toggle_tree.setCheckable(True)
        toolbar_layout.addWidget(self.btn_toggle_tree)
        
        # Przycisk Odśwież
        self.btn_refresh = QPushButton()
        self.btn_refresh.setObjectName("pweb_refresh_button")
        toolbar_layout.addWidget(self.btn_refresh)
        
        # Separator
        toolbar_layout.addStretch()
        
        # Przycisk Split View
        self.btn_split_toggle = QPushButton()
        self.btn_split_toggle.setObjectName("pweb_split_toggle_button")
        self.btn_split_toggle.setCheckable(True)
        toolbar_layout.addWidget(self.btn_split_toggle)
        
        # Przycisk Dodaj stronę
        self.btn_add = QPushButton()
        self.btn_add.setObjectName("pweb_add_button")
        toolbar_layout.addWidget(self.btn_add)
        
        # Przycisk Usuń stronę
        self.btn_delete = QPushButton()
        self.btn_delete.setObjectName("pweb_delete_button")
        toolbar_layout.addWidget(self.btn_delete)
        
        main_layout.addLayout(toolbar_layout)
        
        # === Splitter główny: Drzewo | Przeglądarki ===
        self.main_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.main_splitter.setObjectName("pweb_main_splitter")
        
        # Widget drzewa
        self.tree_widget = PWebTreeWidget(self.logic, self)
        self.tree_widget.setObjectName("pweb_tree_widget")
        self.tree_widget.setMaximumWidth(400)  # Maksymalna szerokość 400px
        self.tree_widget.hide()  # Początkowo ukryte
        self.main_splitter.addWidget(self.tree_widget)
        
        # === Splitter przeglądarek: Lewa | Prawa ===
        self.browser_splitter = QSplitter(Qt.Orientation.Horizontal)
        self.browser_splitter.setObjectName("pweb_browser_splitter")
        
        # Główny widok przeglądarki (lewy)
        self.web_view = QWebEngineView()
        self.web_view.setObjectName("pweb_web_view")
        self.web_view.setUrl(QUrl("about:blank"))
        self.browser_splitter.addWidget(self.web_view)
        
        # Dodatkowy widok przeglądarki (prawy) - początkowo ukryty
        self.web_view_split = QWebEngineView()
        self.web_view_split.setObjectName("pweb_web_view_split")
        self.web_view_split.setUrl(QUrl("about:blank"))
        self.web_view_split.hide()
        self.browser_splitter.addWidget(self.web_view_split)
        
        # Overlay: przyciski zamykania kart (na obu przeglądarkach)
        # Tworzymy je jako dzieci widoków przeglądarki, będą pozycjonowane dynamicznie
        self.btn_close_left = QPushButton("✖", self.web_view)
        self.btn_close_left.setObjectName("pweb_close_left_button")
        self.btn_close_left.setFixedSize(28, 28)
        self.btn_close_left.setVisible(False)
        self.btn_close_left.setToolTip(t("pweb.split_view_close"))
        self.btn_close_left.clicked.connect(self._close_left_pane)
        self.btn_close_left.setStyleSheet("background: rgba(0,0,0,0.6); color: white; border: none; border-radius: 14px;")
        
        self.btn_close_right = QPushButton("✖", self.web_view_split)
        self.btn_close_right.setObjectName("pweb_close_right_button")
        self.btn_close_right.setFixedSize(28, 28)
        self.btn_close_right.setVisible(False)
        self.btn_close_right.setToolTip(t("pweb.split_view_close"))
        self.btn_close_right.clicked.connect(self._close_right_pane)
        self.btn_close_right.setStyleSheet("background: rgba(0,0,0,0.6); color: white; border: none; border-radius: 14px;")
        
        # Proporcje browser_splitter (50% / 50% gdy widoczne)
        self.browser_splitter.setStretchFactor(0, 1)
        self.browser_splitter.setStretchFactor(1, 1)
        
        self.main_splitter.addWidget(self.browser_splitter)
        
        # Proporcje main_splitter (25% drzewo, 75% przeglądarki)
        self.main_splitter.setStretchFactor(0, 1)
        self.main_splitter.setStretchFactor(1, 3)
        
        main_layout.addWidget(self.main_splitter)
        
        # Stan split view
        self.split_view_active = False
        
        # Konfiguruj profil przeglądarki
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
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setPersistentStoragePath(profile_path)
        self.profile.setCachePath(os.path.join(profile_path, "cache"))
        self.profile.setPersistentCookiesPolicy(
            QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies
        )
        
        # Konfiguruj ustawienia przeglądarki
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        # Synchronizuj z aktualnym motywem aplikacji
        self._apply_browser_theme()
        
        # Utwórz własne strony z menu kontekstowym dla obu przeglądarek
        if CustomWebEnginePage:
            # Główna przeglądarka (lewa)
            self.web_page = CustomWebEnginePage(self, self.profile)
            self.web_view.setPage(self.web_page)
            
            # Dodatkowa przeglądarka (prawa) - używa tego samego profilu
            self.web_page_split = CustomWebEnginePage(self, self.profile)
            self.web_view_split.setPage(self.web_page_split)
    
    def _apply_browser_theme(self):
        """Stosuje motyw aplikacji do przeglądarki"""
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'web_view'):
            return
        
        try:
            from PyQt6.QtGui import QPalette
            
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
                    # Użyj koloru z motywu jako ostateczny fallback
                    colors = self.theme_manager.get_current_colors() if self.theme_manager else {}
                    bg_color = colors.get('bg_main', '#FFFFFF')
            
            # Ustaw kolor tła dla przeglądarki
            self.web_view.page().setBackgroundColor(QColor(bg_color))
            
            logger.debug(f"[PWebView] Applied browser theme with background: {bg_color}")
        except Exception as e:
            logger.warning(f"[PWebView] Could not apply browser theme: {e}")
    
    def _connect_signals(self):
        """Połączenia sygnałów"""
        # Toolbar
        self.btn_back.clicked.connect(self._go_back)
        self.btn_toggle_tree.clicked.connect(self._toggle_tree)
        self.btn_refresh.clicked.connect(self._refresh_page)
        self.btn_split_toggle.clicked.connect(self._toggle_split_view)
        self.btn_add.clicked.connect(self._add_bookmark)
        self.btn_delete.clicked.connect(self._delete_bookmark)
        
        # Drzewo
        self.tree_widget.bookmark_selected.connect(self._on_bookmark_selected)
        self.tree_widget.edit_groups_requested.connect(self._edit_groups)
        self.tree_widget.edit_tags_requested.connect(self._edit_tags)
        self.tree_widget.toggle_favorite_requested.connect(self._toggle_favorite)
        self.tree_widget.open_in_split_requested.connect(self._open_bookmark_in_split)
        
        # Menu kontekstowe głównej przeglądarki
        if hasattr(self, 'web_page'):
            self.web_page.create_note_requested.connect(self._create_note_from_selection)
            self.web_page.create_task_requested.connect(self._create_task_from_selection)
            self.web_page.toggle_favorite_requested.connect(self._toggle_favorite_from_menu)
            self.web_page.open_in_split_requested.connect(self._open_url_in_split)
            self.web_page.open_in_split_prompt_requested.connect(self._on_open_split_prompt)
        
        # Menu kontekstowe dodatkowej przeglądarki
        if hasattr(self, 'web_page_split'):
            self.web_page_split.create_note_requested.connect(self._create_note_from_selection)
            self.web_page_split.create_task_requested.connect(self._create_task_from_selection)
            self.web_page_split.open_in_split_requested.connect(self._open_url_in_split)
    
    # ======================
    # Akcje toolbar
    # ======================
    
    def _toggle_tree(self):
        """Przełącza widoczność drzewa"""
        self.tree_visible = not self.tree_visible
        
        if self.tree_visible:
            self.tree_widget.show()
            self.tree_widget.refresh_tree()
            
            # Ustaw początkową szerokość na ~25% szerokości okna
            total_width = self.main_splitter.width()
            tree_width = int(total_width * 0.25)
            tree_width = min(tree_width, 400)  # Maksymalnie 400px
            
            self.main_splitter.setSizes([tree_width, total_width - tree_width])
            
            logger.debug("[PWebView] Tree expanded")
        else:
            self.tree_widget.hide()
            logger.debug("[PWebView] Tree collapsed")
        
        self.btn_toggle_tree.setChecked(self.tree_visible)
    
    def _go_back(self):
        """Wraca do poprzedniej strony w historii"""
        if self.web_view.history().canGoBack():
            self.web_view.back()
            logger.debug("[PWebView] Navigated back")
    
    def _refresh_page(self):
        """Odświeża aktualną stronę"""
        self.web_view.reload()
        logger.debug("[PWebView] Page refreshed")
    
    def _toggle_split_view(self):
        """Przełącza podzielony widok - z dialogiem wyboru strony przy włączaniu"""
        if not self.split_view_active:
            # Włączanie: pokaż dialog wyboru strony
            dialog = SplitViewSelectDialog(self.logic, self)
            if dialog.exec() == dialog.DialogCode.Accepted:
                url = dialog.get_url()
                
                if url:
                    # Włącz split-view
                    self.split_view_active = True
                    self.web_view_split.show()
                    
                    # Otwórz wybraną stronę
                    normalized_url = PWebLogic.normalize_url(url)
                    self.web_view_split.setUrl(QUrl(normalized_url))
                    
                    # Zaktualizuj przycisk
                    self.btn_split_toggle.setChecked(True)
                    self.btn_split_toggle.setText(t("pweb.split_view_close"))
                    
                    # Pokaż przyciski overlay X
                    self.btn_close_left.setVisible(True)
                    self.btn_close_right.setVisible(True)
                    self.btn_close_left.raise_()
                    self.btn_close_right.raise_()
                    QTimer.singleShot(50, self._position_overlay_buttons)
                    
                    logger.info(f"[PWebView] Split view enabled with URL: {normalized_url}")
        else:
            # Wyłączanie: zamknij split-view
            self.split_view_active = False
            self.web_view_split.hide()
            self.web_view_split.setUrl(QUrl("about:blank"))
            
            # Ukryj przyciski overlay X
            self.btn_close_left.setVisible(False)
            self.btn_close_right.setVisible(False)
            
            # Zaktualizuj przycisk
            self.btn_split_toggle.setChecked(False)
            self.btn_split_toggle.setText(t("pweb.split_view_toggle"))
            
            logger.debug("[PWebView] Split view disabled")
    
    def _add_bookmark(self):
        """Dodaje nową zakładkę"""
        dialog = AddBookmarkDialog(self.logic, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            # Dodanie przez logikę
            success, error = self.logic.add_bookmark(
                data['name'],
                data['url'],
                data['color'],
                data['group_id'],
                data['tags'],
                data['favorite']
            )
            
            if success:
                # Odśwież drzewo jeśli widoczne
                if self.tree_visible:
                    self.tree_widget.refresh_tree()
                
                # Otwórz zakładkę
                self._open_bookmark(data)
                
                logger.info(f"[PWebView] Added bookmark: {data['name']}")
            else:
                # Obsługa błędów
                if error == "no_name":
                    QMessageBox.warning(self, t("pweb.title"), t("pweb.error_no_name"))
                elif error == "no_url":
                    QMessageBox.warning(self, t("pweb.title"), t("pweb.error_no_url"))
                elif error.startswith("save_error:"):
                    save_error = error.split(":", 1)[1]
                    QMessageBox.critical(self, t("pweb.title"), 
                                       t("pweb.error_save_json").format(save_error))
                
                logger.error(f"[PWebView] Failed to add bookmark: {error}")
    
    def _delete_bookmark(self):
        """Usuwa aktualnie wybraną zakładkę"""
        if not self.current_bookmark:
            QMessageBox.information(self, t("pweb.title"), t("pweb.error_no_bookmark_selected"))
            return
        
        # Potwierdzenie
        reply = QMessageBox.question(
            self,
            t("pweb.title"),
            t("pweb.confirm_delete_bookmark").format(name=self.current_bookmark['name']),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, error = self.logic.delete_bookmark_by_data(self.current_bookmark)
            
            if success:
                self.current_bookmark = None
                self.web_view.setUrl(QUrl("about:blank"))
                
                # Odśwież drzewo jeśli widoczne
                if self.tree_visible:
                    self.tree_widget.refresh_tree()
                
                logger.info("[PWebView] Deleted bookmark")
            else:
                QMessageBox.critical(self, t("pweb.title"), 
                                   t("pweb.error_save_json").format(error))
    
    # ======================
    # Akcje drzewa
    # ======================
    
    def _on_bookmark_selected(self, bookmark: dict):
        """Obsługa wyboru zakładki z drzewa"""
        self.current_bookmark = bookmark
        self._open_bookmark(bookmark)
    
    def _open_bookmark(self, bookmark: dict):
        """Otwiera zakładkę w przeglądarce"""
        url = PWebLogic.normalize_url(bookmark['url'])
        self.web_view.setUrl(QUrl(url))
        logger.debug(f"[PWebView] Opened bookmark: {bookmark['name']}")
    
    def _edit_groups(self):
        """Otwiera dialog zarządzania grupami"""
        dialog = GroupManagerDialog(self.logic, self)
        dialog.exec()
        
        # Odśwież drzewo
        if self.tree_visible:
            self.tree_widget.refresh_tree()
    
    def _edit_tags(self):
        """Otwiera dialog zarządzania tagami"""
        dialog = TagManagerDialog(self.logic, self)
        dialog.exec()
        
        # Odśwież drzewo
        if self.tree_visible:
            self.tree_widget.refresh_tree()
    
    def _toggle_favorite(self, bookmark: dict):
        """Przełącza status ulubionej dla zakładki"""
        success, result = self.logic.toggle_favorite(bookmark)
        
        if success:
            # Aktualizuj current_bookmark jeśli to ta sama
            if self.current_bookmark and self.current_bookmark['name'] == bookmark['name']:
                self.current_bookmark['favorite'] = (result == 'True')
            
            # Odśwież drzewo
            if self.tree_visible:
                self.tree_widget.refresh_tree()
            
            logger.info(f"[PWebView] Toggled favorite for: {bookmark['name']} -> {result}")
        else:
            QMessageBox.warning(self, t("pweb.title"), t("pweb.error_toggle_favorite"))
    
    def _toggle_favorite_from_menu(self):
        """Przełącza status ulubionej z menu kontekstowego"""
        if self.current_bookmark:
            self._toggle_favorite(self.current_bookmark)
    
    def _open_bookmark_in_split(self, bookmark: dict):
        """Otwiera zakładkę w podzielonym widoku"""
        # Włącz split view jeśli wyłączony
        if not self.split_view_active:
            self.split_view_active = True
            self.web_view_split.show()
            self.btn_split_toggle.setChecked(True)
            self.btn_split_toggle.setText(t("pweb.split_view_close"))
            
            # Pokaż przyciski overlay X
            self.btn_close_left.setVisible(True)
            self.btn_close_right.setVisible(True)
            self.btn_close_left.raise_()
            self.btn_close_right.raise_()
            QTimer.singleShot(50, self._position_overlay_buttons)
        
        # Otwórz zakładkę w prawej przeglądarce
        url = PWebLogic.normalize_url(bookmark['url'])
        self.web_view_split.setUrl(QUrl(url))
        logger.info(f"[PWebView] Opened in split view: {bookmark['name']}")
    
    def _open_url_in_split(self, url: str):
        """Otwiera URL w podzielonym widoku"""
        # Włącz split view jeśli wyłączony
        if not self.split_view_active:
            self.split_view_active = True
            self.web_view_split.show()
            self.btn_split_toggle.setChecked(True)
            self.btn_split_toggle.setText(t("pweb.split_view_close"))
            
            # Pokaż przyciski overlay X
            self.btn_close_left.setVisible(True)
            self.btn_close_right.setVisible(True)
            self.btn_close_left.raise_()
            self.btn_close_right.raise_()
            QTimer.singleShot(50, self._position_overlay_buttons)
        
        # Otwórz URL w prawej przeglądarce
        normalized_url = PWebLogic.normalize_url(url)
        self.web_view_split.setUrl(QUrl(normalized_url))
        logger.info(f"[PWebView] Opened URL in split view: {normalized_url}")
    
    def _quick_open(self):
        """Szybkie otwarcie URL bez zapisywania"""
        dialog = QuickOpenDialog(self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            url = dialog.get_url()
            
            if url:
                normalized_url = PWebLogic.normalize_url(url)
                self.web_view.setUrl(QUrl(normalized_url))
                logger.info(f"[PWebView] Quick opened: {normalized_url}")
    
    def _on_open_split_prompt(self):
        """Pokazuje dialog wyboru strony do otwarcia w podzielonym widoku"""
        dialog = SplitViewSelectDialog(self.logic, self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            url = dialog.get_url()
            
            if url:
                # Włącz podzielony widok jeśli nie jest aktywny
                if not self.split_view_active:
                    self._toggle_split_view()
                
                # Otwórz URL w prawej przeglądarce
                normalized_url = PWebLogic.normalize_url(url)
                self.web_view_split.setUrl(QUrl(normalized_url))
                logger.info(f"[PWebView] Opened URL in split view from prompt: {normalized_url}")
    
    # ======================
    # Integracja z aplikacją
    # ======================
    
    def _create_note_from_selection(self, selected_text: str):
        """Tworzy notatkę z zaznaczonego tekstu"""
        if not selected_text or not selected_text.strip():
            logger.warning("[PWebView] No text selected for note creation")
            return
        
        # Pobierz główne okno
        main_window = self._get_main_window()
        if not main_window or not hasattr(main_window, 'notes_view'):
            QMessageBox.warning(self, t('pweb.title'), t('pweb.error.no_notes_view'))
            return
        
        # Przygotuj dane notatki
        words = selected_text.strip().split()
        title_words = words[:3]
        note_title = " ".join(title_words)
        
        if len(note_title) < 10:
            note_title = note_title + "..."
        
        # Zawartość
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
            colors = self.theme_manager.get_current_colors() if self.theme_manager else {}
            note_color = colors.get('accent_primary', '#2196F3')
            new_note_id = main_window.notes_view.db.create_note(
                title=note_title,
                content=note_content,
                color=note_color
            )
            
            logger.info(f"[PWebView] Created note {new_note_id} from selection")
            
            # Przełącz na widok notatek
            main_window._on_view_changed("notes")
            
            # Odśwież i wybierz
            QTimer.singleShot(100, lambda: self._select_note(main_window, new_note_id))
            
            QMessageBox.information(self, t('pweb.title'), 
                                  t('pweb.success.note_created').format(title=note_title))
        except Exception as e:
            logger.error(f"[PWebView] Error creating note: {e}")
            QMessageBox.warning(self, t('pweb.title'), 
                              t('pweb.error.note_creation_failed').format(error=str(e)))
    
    def _create_task_from_selection(self, selected_text: str):
        """Otwiera quick task bar z zaznaczonym tekstem"""
        if not selected_text or not selected_text.strip():
            logger.warning("[PWebView] No text selected for task creation")
            return
        
        # Pobierz główne okno
        main_window = self._get_main_window()
        if not main_window or not hasattr(main_window, 'quick_task_dialog'):
            QMessageBox.warning(self, t('pweb.title'), t('pweb.error.no_quick_task'))
            return
        
        # Przygotuj tekst zadania
        task_text = selected_text.strip()
        if len(task_text) > 200:
            task_text = task_text[:197] + "..."
        
        try:
            # Otwórz quick task dialog
            main_window.quick_task_dialog.clear_inputs()
            main_window.quick_task_dialog.reload_configuration()
            
            # Wstaw tekst do pola zadania
            main_window.quick_task_dialog.task_bar.task_input.setText(task_text)
            
            # Pokaż i aktywuj dialog
            main_window.quick_task_dialog.show()
            main_window.quick_task_dialog.raise_()
            main_window.quick_task_dialog.activateWindow()
            
            # Ustaw focus na polu zadania
            main_window.quick_task_dialog.task_bar.task_input.setFocus()
            main_window.quick_task_dialog.task_bar.task_input.selectAll()
            
            logger.info(f"[PWebView] Opened quick task bar with text: {task_text[:50]}...")
        except Exception as e:
            logger.error(f"[PWebView] Error opening quick task bar: {e}")
            QMessageBox.warning(self, t('pweb.title'), 
                              t('pweb.error.quick_task_failed').format(error=str(e)))
    
    def _get_main_window(self):
        """Pobiera główne okno aplikacji"""
        content_stack = self.parent()
        central_widget = content_stack.parent() if content_stack else None
        main_window = central_widget.parent() if central_widget else None
        return main_window
    
    def _select_note(self, main_window, note_id):
        """Wybiera notatkę w drzewie (helper)"""
        main_window.notes_view.refresh_tree()
        main_window.notes_view.select_note_in_tree(str(note_id))

    # ======================
    # Overlay close buttons (split panes)
    # ======================

    def _close_right_pane(self):
        """Zamyka prawą kartę i rozszerza lewą (jeśli była)"""
        if not self.split_view_active:
            return

        # Ukryj prawą przeglądarkę
        try:
            self.split_view_active = False
            self.web_view_split.hide()
            self.web_view_split.setUrl(QUrl("about:blank"))
            self.btn_close_left.setVisible(False)
            self.btn_close_right.setVisible(False)
            self.btn_split_toggle.setChecked(False)
            self.btn_split_toggle.setText(t("pweb.split_view_toggle"))
            logger.info("[PWebView] Right split pane closed")
        except Exception as e:
            logger.error(f"[PWebView] Error closing right pane: {e}")

    def _close_left_pane(self):
        """Zamyka lewą kartę: jeśli prawa zawiera stronę, przenosi ją do głównego widoku,
        następnie zamyka split-view."""
        if not self.split_view_active:
            return

        try:
            # Jeśli prawa zawiera URL, przenieś go do głównego widoku
            right_url = self.web_view_split.url().toString() if hasattr(self.web_view_split, 'url') else ''
            if right_url and right_url != 'about:blank':
                self.web_view.setUrl(QUrl(right_url))

        except Exception as e:
            logger.debug(f"[PWebView] Could not transfer URL from right pane: {e}")

        # Reuse zamknięcie prawej karty
        self._close_right_pane()

    def _position_overlay_buttons(self):
        """Pozycjonuje przyciski X w prawym górnym rogu obu widoków przeglądarki."""
        try:
            if hasattr(self, 'btn_close_left') and self.btn_close_left and hasattr(self, 'web_view'):
                w = self.web_view.width()
                btn = self.btn_close_left
                btn.move(max(4, w - btn.width() - 8), 8)

            if hasattr(self, 'btn_close_right') and self.btn_close_right and hasattr(self, 'web_view_split'):
                w2 = self.web_view_split.width()
                btn2 = self.btn_close_right
                btn2.move(max(4, w2 - btn2.width() - 8), 8)
        except Exception:
            pass

    def resizeEvent(self, event):
        """Nadpisz resizeEvent, aby pozycjonować overlay przyciski"""
        try:
            super().resizeEvent(event)
        except Exception:
            # Dla bezpieczeństwa, jeśli super ma inne sygnatury
            QWidget.resizeEvent(self, event)

        QTimer.singleShot(0, self._position_overlay_buttons)
    
    # ======================
    # Tłumaczenia
    # ======================
    
    def update_translations(self):
        """Aktualizuje tłumaczenia w widoku"""
        if not WEBENGINE_AVAILABLE or not hasattr(self, 'btn_back'):
            return
        
        self.btn_back.setText(t("pweb.back"))
        self.btn_toggle_tree.setText(t("pweb.toggle_tree"))
        self.btn_refresh.setText(t("pweb.refresh"))
        
        # Tekst przycisku split-view w zależności od stanu
        if self.split_view_active:
            self.btn_split_toggle.setText(t("pweb.split_view_close"))
        else:
            self.btn_split_toggle.setText(t("pweb.split_view_toggle"))
        
        self.btn_add.setText(t("pweb.add_page"))
        self.btn_delete.setText(t("pweb.delete_page"))
        
        # Aktualizuj motyw przeglądarki
        self._apply_browser_theme()
        
        logger.debug("[PWebView] Translations updated")
