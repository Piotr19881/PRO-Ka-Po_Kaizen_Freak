"""
Minimalistyczny widget przeglądarki internetowej.
Prosty widok z dwoma przyciskami: Odśwież i Wstecz.
"""

from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QApplication
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineSettings

# Ensure QtWebEngine can be imported by setting the required attribute
# This must be done before QApplication is created
try:
    QApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)
except:
    # Attribute might already be set or QApplication already exists
    pass


class MinimalBrowserWidget(QWidget):
    """Minimalistyczny widget przeglądarki z podstawowymi kontrolkami."""
    
    def __init__(self, url: str = "", parent=None):
        """
        Inicjalizacja minimalistycznej przeglądarki.
        
        Args:
            url: Adres URL strony do załadowania
            parent: Widget rodzica
        """
        super().__init__(parent)
        self.url = url
        self._init_ui()
        
        # Załaduj stronę jeśli URL został podany
        if self.url:
            self.load_url(self.url)
    
    def _init_ui(self):
        """Inicjalizacja interfejsu użytkownika."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Panel z przyciskami kontrolnymi
        toolbar = QHBoxLayout()
        toolbar.setContentsMargins(5, 5, 5, 5)
        toolbar.setSpacing(10)
        
        # Przycisk Wstecz
        self.back_button = QPushButton("← Wstecz")
        self.back_button.setMinimumHeight(35)
        self.back_button.clicked.connect(self._on_back)
        self.back_button.setToolTip("Wróć do poprzedniej strony")
        toolbar.addWidget(self.back_button)
        
        # Przycisk Odśwież
        self.refresh_button = QPushButton("🔄 Odśwież")
        self.refresh_button.setMinimumHeight(35)
        self.refresh_button.clicked.connect(self._on_refresh)
        self.refresh_button.setToolTip("Odśwież bieżącą stronę")
        toolbar.addWidget(self.refresh_button)
        
        # Spacer aby przyciski były po lewej stronie
        toolbar.addStretch()
        
        layout.addLayout(toolbar)
        
        # Widget przeglądarki
        self.browser = QWebEngineView()
        layout.addWidget(self.browser)

        # Konfiguracja ustawień przeglądarki dla dostępu do lokalnych plików
        settings = self.browser.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)

        # Połącz sygnały przeglądarki
        self.browser.urlChanged.connect(self._on_url_changed)
        self.browser.loadFinished.connect(self._on_load_finished)
    
    def load_url(self, url: str):
        """
        Załaduj URL w przeglądarce.

        Args:
            url: Adres URL do załadowania
        """
        # Jeśli to już file:// URL, użyj go bezpośrednio
        if url.startswith('file://'):
            self.url = url
            self.browser.setUrl(QUrl(url))
        # Jeśli to ścieżka do pliku, skonwertuj na file:// URL
        elif url.startswith('/') or (len(url) > 1 and url[1] == ':'):  # Windows path or Unix absolute path
            # Konwertuj ścieżkę na URL file://
            file_url = f"file:///{url.replace('\\', '/')}"
            self.url = file_url
            self.browser.setUrl(QUrl(file_url))
        # Dodaj protokół https jeśli brakuje
        else:
            if not url.startswith(('http://', 'https://')):
                url = 'https://' + url
            self.url = url
            self.browser.setUrl(QUrl(url))
    
    def _on_back(self):
        """Obsługa przycisku Wstecz."""
        if self.browser.history().canGoBack():
            self.browser.back()
    
    def _on_refresh(self):
        """Obsługa przycisku Odśwież."""
        self.browser.reload()
    
    def _on_url_changed(self, url: QUrl):
        """
        Obsługa zmiany URL.
        
        Args:
            url: Nowy adres URL
        """
        # Aktualizuj dostępność przycisku Wstecz
        self.back_button.setEnabled(self.browser.history().canGoBack())
    
    def _on_load_finished(self, success: bool):
        """
        Obsługa zakończenia ładowania strony.

        Args:
            success: True jeśli strona załadowała się poprawnie
        """
        # Aktualizuj dostępność przycisku Wstecz
        self.back_button.setEnabled(self.browser.history().canGoBack())

        if not success:
            # Jeśli ładowanie nie powiodło się, pokaż komunikat błędu
            error_html = f"""
            <html>
            <body style="font-family: Arial, sans-serif; text-align: center; padding: 50px;">
                <h2>Błąd ładowania strony</h2>
                <p>Nie udało się załadować strony: {self.url}</p>
                <p>Sprawdź czy plik istnieje i czy ścieżka jest prawidłowa.</p>
            </body>
            </html>
            """
            self.browser.setHtml(error_html)
            print(f"[MinimalBrowserWidget] Failed to load URL: {self.url}")
        else:
            print(f"[MinimalBrowserWidget] Successfully loaded URL: {self.url}")
