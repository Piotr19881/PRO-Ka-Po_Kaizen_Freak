"""
P-Web Context Menu
Menu kontekstowe przeglądarki z rozszerzonymi opcjami
"""

from PyQt6.QtWidgets import QMenu
from PyQt6.QtGui import QAction
from PyQt6.QtCore import pyqtSignal, QObject

try:
    from PyQt6.QtWebEngineCore import QWebEnginePage
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False
    QWebEnginePage = object

from loguru import logger
from ...utils.i18n_manager import t


class PWebContextMenu(QObject):
    """Klasa zarządzająca menu kontekstowym przeglądarki"""
    
    # Sygnały
    create_note_requested = pyqtSignal(str)  # text
    create_task_requested = pyqtSignal(str)  # text - quick task bar
    toggle_favorite_requested = pyqtSignal()
    open_in_split_requested = pyqtSignal(str)  # url - otwiera w split-view
    open_in_split_prompt_requested = pyqtSignal()  # brak URL - pokaż dialog wyboru
    
    def __init__(self, parent=None):
        super().__init__(parent)
    
    def create_menu(self, web_page, selected_text: str, link_url: str, 
                    current_url: str, is_favorite: bool) -> QMenu:
        """
        Tworzy menu kontekstowe
        
        Args:
            web_page: QWebEnginePage
            selected_text: Zaznaczony tekst
            link_url: URL linku (jeśli kursor nad linkiem)
            current_url: Aktualny URL strony
            is_favorite: Czy strona jest ulubiona
        
        Returns:
            QMenu: Przygotowane menu kontekstowe
        """
        menu = QMenu()
        
        # === Podstawowe akcje ===
        
        # Kopiuj (jeśli jest zaznaczony tekst)
        if selected_text:
            copy_action = menu.addAction(t("pweb.context.copy"))
            copy_action.triggered.connect(
                lambda: web_page.triggerAction(QWebEnginePage.WebAction.Copy)
            )
        
        # Wklej
        paste_action = menu.addAction(t("pweb.context.paste"))
        paste_action.triggered.connect(
            lambda: web_page.triggerAction(QWebEnginePage.WebAction.Paste)
        )
        
        # === Akcje linku (jeśli kursor nad linkiem) ===
        
        if link_url:
            menu.addSeparator()
            
            # Kopiuj link
            copy_link_action = menu.addAction(t("pweb.context.copy_link"))
            copy_link_action.triggered.connect(
                lambda: self._copy_link_to_clipboard(link_url)
            )
            
            # Otwórz link w podzielonym widoku
            split_action = menu.addAction(t("pweb.context.open_in_split"))
            split_action.triggered.connect(
                lambda: self.open_in_split_requested.emit(link_url)
            )
        
        # === Akcje strony ===
        
        menu.addSeparator()
        
        # Otwórz w podzielonym widoku (dla bieżącej strony lub dialog)
        if current_url and current_url != "about:blank":
            # Mamy stronę - otwórz ją
            split_action = menu.addAction(t("pweb.context.open_in_split"))
            split_action.triggered.connect(
                lambda: self.open_in_split_requested.emit(current_url)
            )
        else:
            # Pusta strona - pokaż dialog wyboru
            split_action = menu.addAction(t("pweb.context.open_in_split_prompt"))
            split_action.triggered.connect(self.open_in_split_prompt_requested.emit)
        
        # Otwórz stronę w domyślnej przeglądarce
        if current_url and current_url != "about:blank":
            open_page_action = menu.addAction(t("pweb.context.open_page_external"))
            open_page_action.triggered.connect(
                lambda: self._open_in_external_browser(current_url)
            )
        
        # === Integracja z aplikacją (jeśli jest zaznaczony tekst) ===
        
        if selected_text:
            menu.addSeparator()
            
            # Utwórz notatkę z zaznaczenia
            create_note_action = QAction(t("pweb.context.create_note"), menu)
            create_note_action.triggered.connect(
                lambda: self.create_note_requested.emit(selected_text)
            )
            menu.addAction(create_note_action)
            
            # Dodaj zadanie (quick task bar)
            create_task_action = QAction(t("pweb.context.create_task"), menu)
            create_task_action.triggered.connect(
                lambda: self.create_task_requested.emit(selected_text)
            )
            menu.addAction(create_task_action)
        
        # === Ulubiona ===
        
        menu.addSeparator()
        
        # Oznacz/odznacz jako ulubioną
        if is_favorite:
            favorite_text = t("pweb.context.remove_favorite")
        else:
            favorite_text = t("pweb.context.add_favorite")
        
        favorite_action = menu.addAction(favorite_text)
        favorite_action.triggered.connect(self.toggle_favorite_requested.emit)
        
        return menu
    
    def _copy_link_to_clipboard(self, url: str):
        """Kopiuje URL do schowka"""
        from PyQt6.QtWidgets import QApplication
        clipboard = QApplication.clipboard()
        clipboard.setText(url)
        logger.debug(f"[PWebContextMenu] Copied link to clipboard: {url}")
    
    def _open_in_external_browser(self, url: str):
        """Otwiera URL w domyślnej przeglądarce systemowej"""
        import webbrowser
        webbrowser.open(url)
        logger.debug(f"[PWebContextMenu] Opened in external browser: {url}")


if WEBENGINE_AVAILABLE:
    class CustomWebEnginePage(QWebEnginePage):
        """Własna klasa QWebEnginePage z menu kontekstowym"""
        
        # Sygnały
        create_note_requested = pyqtSignal(str)
        create_task_requested = pyqtSignal(str)
        toggle_favorite_requested = pyqtSignal()
        open_in_split_requested = pyqtSignal(str)
        open_in_split_prompt_requested = pyqtSignal()
        
        def __init__(self, parent_view, profile, parent=None):
            super().__init__(profile, parent)
            self.parent_view = parent_view
            self.context_menu_manager = PWebContextMenu(self)
            
            # Przekieruj sygnały
            self.context_menu_manager.create_note_requested.connect(
                self.create_note_requested.emit
            )
            self.context_menu_manager.create_task_requested.connect(
                self.create_task_requested.emit
            )
            self.context_menu_manager.toggle_favorite_requested.connect(
                self.toggle_favorite_requested.emit
            )
            self.context_menu_manager.open_in_split_requested.connect(
                self.open_in_split_requested.emit
            )
            self.context_menu_manager.open_in_split_prompt_requested.connect(
                self.open_in_split_prompt_requested.emit
            )
        
        def createStandardContextMenu(self):
            """Tworzy własne menu kontekstowe z dodatkowymi opcjami"""
            # Pobierz dane kontekstu
            selected_text = self.selectedText()
            hit_test_result = self.contextMenuData()
            link_url = hit_test_result.linkUrl().toString() if hit_test_result.linkUrl().isValid() else None
            current_url = self.url().toString()
            
            # Sprawdź czy strona jest ulubiona
            is_favorite = False
            if hasattr(self.parent_view, 'current_bookmark') and self.parent_view.current_bookmark:
                is_favorite = self.parent_view.current_bookmark.get('favorite', False)
            
            # Utwórz menu
            return self.context_menu_manager.create_menu(
                self,
                selected_text,
                link_url,
                current_url,
                is_favorite
            )
else:
    # Fallback - pusta klasa
    CustomWebEnginePage = None
