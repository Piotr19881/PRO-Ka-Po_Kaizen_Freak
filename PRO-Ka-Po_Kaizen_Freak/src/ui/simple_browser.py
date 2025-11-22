"""
Simple Browser Widget - Prosta przeglądarka z przyciskami odśwież i wstecz
"""

from PyQt6.QtCore import QUrl
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QToolBar
from PyQt6.QtWebEngineWidgets import QWebEngineView
from loguru import logger


class SimpleBrowserWidget(QWidget):
    """Prosta przeglądarka internetowa z podstawowymi kontrolkami"""
    
    def __init__(self, url: str, parent=None):
        """
        Args:
            url: Adres URL strony do załadowania
            parent: Widget rodzica
        """
        super().__init__(parent)
        self.url = url
        self._setup_ui()
        self._load_url()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Toolbar z przyciskami
        toolbar = QToolBar()
        toolbar.setMovable(False)
        toolbar.setStyleSheet("""
            QToolBar {
                background-color: #f0f0f0;
                border-bottom: 1px solid #ccc;
                spacing: 5px;
                padding: 5px;
            }
            QPushButton {
                background-color: #ffffff;
                border: 1px solid #ccc;
                border-radius: 4px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #e8e8e8;
                border-color: #999;
            }
            QPushButton:pressed {
                background-color: #d0d0d0;
            }
        """)
        
        # Przycisk Wstecz
        self.back_button = QPushButton("⬅ Wstecz")
        self.back_button.clicked.connect(self._on_back_clicked)
        toolbar.addWidget(self.back_button)
        
        # Przycisk Odśwież
        self.refresh_button = QPushButton("🔄 Odśwież")
        self.refresh_button.clicked.connect(self._on_refresh_clicked)
        toolbar.addWidget(self.refresh_button)
        
        layout.addWidget(toolbar)
        
        # Widok przeglądarki
        self.browser = QWebEngineView()
        self.browser.loadFinished.connect(self._on_load_finished)
        layout.addWidget(self.browser)
        
        logger.info(f"SimpleBrowserWidget initialized for URL: {self.url}")
    
    def _load_url(self):
        """Załaduj URL do przeglądarki"""
        try:
            qurl = QUrl(self.url)
            if not qurl.scheme():
                # Jeśli brak schematu, dodaj https://
                qurl = QUrl(f"https://{self.url}")
            
            self.browser.setUrl(qurl)
            logger.info(f"Loading URL: {qurl.toString()}")
        except Exception as e:
            logger.error(f"Error loading URL {self.url}: {e}")
    
    def _on_back_clicked(self):
        """Obsługa przycisku Wstecz"""
        if self.browser.history().canGoBack():
            self.browser.back()
            logger.debug("Navigated back")
        else:
            logger.debug("Cannot go back - no history")
    
    def _on_refresh_clicked(self):
        """Obsługa przycisku Odśwież"""
        self.browser.reload()
        logger.debug("Page refreshed")
    
    def _on_load_finished(self, success: bool):
        """Obsługa zakończenia ładowania strony"""
        if success:
            logger.info(f"Page loaded successfully: {self.browser.url().toString()}")
            
            # Aktualizuj stan przycisku Wstecz
            self.back_button.setEnabled(self.browser.history().canGoBack())
        else:
            logger.warning(f"Failed to load page: {self.browser.url().toString()}")
