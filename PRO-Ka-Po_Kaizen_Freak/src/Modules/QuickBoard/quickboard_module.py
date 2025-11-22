"""
Moduł Clipboard Manager - Zaawansowany menedżer schowka

Funkcjonalność:
- Historia schowka (ostatnie 50 elementów)
- Podgląd tekstów, obrazów, plików
- Wyszukiwanie w historii
- Przypinanie ważnych elementów
- Kategorie (Teksty, Obrazy, Linki, Kod, Pliki)
- Formatowanie (plain text, HTML, Markdown)
- Snippety z parametrami {{nazwa}}, {{data}}
- Globalny skrót Ctrl+Shift+V

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-05
"""

import sys
import json
import os
import re
from datetime import datetime
from pathlib import Path

try:
    import pyperclip
except ImportError:
    print("BŁĄD: Biblioteka pyperclip nie jest zainstalowana. Uruchom: pip install pyperclip")
    sys.exit(1)

try:
    import keyboard  # Dla globalnych skrótów
except ImportError:
    print("BŁĄD: Biblioteka keyboard nie jest zainstalowana. Uruchom: pip install keyboard")
    sys.exit(1)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTableWidget, QTableWidgetItem, QLabel, QLineEdit,
    QTextEdit, QMessageBox, QFileDialog, QSplitter, QMenu,
    QGroupBox, QCheckBox, QHeaderView, QComboBox, QListWidget, QListWidgetItem,
    QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QObject, QThread, QMimeData, QUrl, QByteArray, QBuffer, QIODevice
from PyQt6.QtGui import QIcon, QFont, QColor, QPixmap, QImage, QClipboard, QCloseEvent

try:
    from src.utils.theme_manager import get_theme_manager
except Exception:  # pragma: no cover - ThemeManager optional in some contexts
    get_theme_manager = None

try:
    from src.utils.i18n_manager import get_i18n
except Exception:  # pragma: no cover - i18n optional in some contexts
    get_i18n = None


class ClipboardMonitor(QThread):
    """Wątek monitorujący schowek w tle"""
    clipboard_changed = pyqtSignal(str, object, object)  # (typ, zawartość_text, zawartość_binary)
    
    def __init__(self, clipboard):
        super().__init__()
        self.clipboard = clipboard
        self.running = False
        self.last_content = ""
        self.last_image_data = None
        self.last_urls = []
    
    def run(self):
        """Monitoruje schowek co 300ms (zoptymalizowane)"""
        self.running = True
        
        while self.running:
            try:
                mime_data = self.clipboard.mimeData()
                
                if not mime_data:
                    self.msleep(300)
                    continue
                
                # Sprawdź obrazy (priorytet 1 - najczęstsze)
                if mime_data.hasImage():
                    image = self.clipboard.image()
                    if not image.isNull():
                        # Optymalizacja: porównaj tylko rozmiar zamiast pełnych danych
                        current_size = (image.width(), image.height())
                        if current_size != getattr(self, '_last_image_size', None):
                            self._last_image_size = current_size
                            # Zapisz pełne dane tylko przy emisji sygnału
                            byte_array = QByteArray()
                            buffer = QBuffer(byte_array)
                            buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                            image.save(buffer, "PNG")
                            self.last_image_data = byte_array.data()
                            self.clipboard_changed.emit("Obraz", None, image)
                
                # Sprawdź pliki/URL-e
                elif mime_data.hasUrls():
                    urls = mime_data.urls()
                    # Optymalizacja: utwórz listę tylko raz
                    url_strings = [url.toLocalFile() if url.isLocalFile() else url.toString() for url in urls]
                    
                    if url_strings != self.last_urls:
                        self.last_urls = url_strings.copy()  # Kopiuj listę
                        files_text = "\n".join(url_strings)
                        self.clipboard_changed.emit("Pliki", files_text, url_strings)
                
                # Sprawdź tekst
                elif mime_data.hasText():
                    current = mime_data.text()
                    
                    # Optymalizacja: sprawdź długość przed strip()
                    if current and current != self.last_content:
                        stripped = current.strip()
                        if stripped:
                            self.last_content = current
                            content_type = self.detect_content_type(stripped)
                            self.clipboard_changed.emit(content_type, current, None)
                
            except Exception as e:
                print(f"Błąd monitora schowka: {e}")
            
            # Zoptymalizowany interwał 300ms (lepszy balans CPU vs responsywność)
            self.msleep(300)
    
    def detect_content_type(self, text):
        """Wykrywa typ zawartości (zoptymalizowane)"""
        # Optymalizacja: sprawdź długość - długie teksty rzadko są emailem/linkiem
        text_len = len(text)
        
        # Email (tylko dla krótkich tekstów bez spacji)
        if text_len < 100 and ' ' not in text and '@' in text:
            if re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', text):
                return "Email"
        
        # URL/Link (sprawdź szybsze warunki przed regex)
        if text_len < 500:
            if text.startswith(('http://', 'https://', 'www.')):
                return "Link"
        
        # Ścieżka pliku (tylko dla tekstów bez nowej linii)
        if text_len < 300 and '\n' not in text:
            # Optymalizacja: sprawdź czy wygląda jak ścieżka przed os.path.exists
            if ('\\' in text or '/' in text) and os.path.exists(text):
                return "Plik"
        
        # Kod (sprawdź wskaźniki w jednym przebiegu)
        if any(indicator in text for indicator in ('import ', 'function ', 'class ', 'def ', '<?php', '#!/', '{\n', '\n}')):
            return "Kod"
        
        # Domyślnie tekst
        return "Tekst"
    
    def stop(self):
        """Zatrzymuje monitoring"""
        self.running = False


class ClipboardItem:
    """Klasa reprezentująca element schowka"""
    
    def __init__(self, content, content_type="Tekst", pinned=False, binary_data=None):
        self.content = content  # Tekst lub None dla obrazów
        self.content_type = content_type
        self.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.pinned = pinned
        self.binary_data = binary_data  # QImage dla obrazów, lista URL dla plików
        self.preview = self.generate_preview()
    
    def generate_preview(self):
        """Generuje podgląd (zoptymalizowane)"""
        if self.content_type == "Obraz":
            if isinstance(self.binary_data, QImage):
                return f"Obraz {self.binary_data.width()}x{self.binary_data.height()}px"
            return "Obraz"
        
        if self.content_type == "Pliki":
            if isinstance(self.binary_data, list) and self.binary_data:
                count = len(self.binary_data)
                first_file = Path(self.binary_data[0]).name
                return first_file if count == 1 else f"{first_file} (+{count-1} więcej)"
            return "Pliki"
        
        # Optymalizacja dla tekstów: użyj str.translate dla szybszego zastąpienia
        if self.content:
            # Zamień \n i \r na spacje w jednym kroku
            preview = self.content.replace('\n', ' ').replace('\r', '')
            return preview[:50] + "..." if len(preview) > 50 else preview
        
        return ""
    
    def to_dict(self):
        """Konwertuje do słownika (do zapisu JSON) - zoptymalizowane"""
        data = {
            'type': self.content_type,
            'timestamp': self.timestamp,
            'pinned': self.pinned,
            'preview': self.preview
        }
        
        if self.content_type == "Obraz":
            # Optymalizacja: zapisuj obrazy w niższej jakości dla oszczędności miejsca
            if isinstance(self.binary_data, QImage):
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                # Użyj JPG zamiast PNG dla mniejszego rozmiaru (jakość 85%)
                scaled_image = self.binary_data
                # Jeśli obraz bardzo duży, zmniejsz przed zapisem
                if scaled_image.width() > 800 or scaled_image.height() > 800:
                    scaled_image = scaled_image.scaled(800, 800, Qt.AspectRatioMode.KeepAspectRatio, 
                                                       Qt.TransformationMode.SmoothTransformation)
                scaled_image.save(buffer, "JPEG", 85)
                import base64
                data['content'] = base64.b64encode(byte_array.data()).decode('utf-8')
                data['image_size'] = f"{self.binary_data.width()}x{self.binary_data.height()}"
        elif self.content_type == "Pliki":
            data['content'] = self.content  # Lista ścieżek jako tekst
            if isinstance(self.binary_data, list):
                data['files'] = self.binary_data
        else:
            data['content'] = self.content
        
        return data
    
    @staticmethod
    def from_dict(data):
        """Tworzy obiekt z słownika (zoptymalizowane)"""
        content_type = data.get('type', 'Tekst')
        binary_data = None
        content = data.get('content', '')
        
        if content_type == "Obraz":
            # Optymalizacja: lazy loading - nie ładuj obrazów od razu
            # Obrazy będą ładowane dopiero przy wyświetlaniu
            try:
                import base64
                image_bytes = base64.b64decode(content)
                image = QImage()
                if image.loadFromData(image_bytes):
                    binary_data = image
                else:
                    # Fallback - jeśli nie można załadować
                    content_type = "Tekst"
                    content = f"[Obraz {data.get('image_size', 'nieznany rozmiar')}]"
                content = None  # Obrazy nie mają content tekstowego
            except Exception as e:
                print(f"Błąd ładowania obrazu: {e}")
                content_type = "Tekst"
                content = "[Błąd ładowania obrazu]"
        elif content_type == "Pliki":
            binary_data = data.get('files', [])
        
        item = ClipboardItem(
            content=content,
            content_type=content_type,
            pinned=data.get('pinned', False),
            binary_data=binary_data
        )
        item.timestamp = data.get('timestamp', item.timestamp)
        item.preview = data.get('preview', item.generate_preview())
        return item


class ClipboardManager(QMainWindow):
    """Główny moduł Clipboard Manager"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Clipboard Manager - Historia Schowka")
        self.setMinimumSize(900, 600)
        
        # Dane
        self.history = []  # Lista ClipboardItem
        self.max_history = 50
        self.monitor = None
        self.monitoring_active = False
        self.current_selected_item = None  # Aktualnie wybrany element
        self.theme_manager = get_theme_manager() if get_theme_manager else None
        self._i18n = None
        self._themed_widgets = []
        self._pinned_color_cache = None
        
        # Ścieżki do plików danych
        self.data_dir = Path(__file__).parent
        self.history_file = self.data_dir / "clipboard_history.json"
        self.settings_file = self.data_dir / "clipboard_settings.json"
        
        # Ładowanie danych
        self.load_data()
        
        # UI
        self.init_ui()
        self._initialize_i18n_support()
        self.apply_theme()
        
        # Uruchom monitoring
        self.start_monitoring()
        
        # Globalny skrót (opcjonalny - odkomentuj jeśli chcesz)
        # self.register_global_hotkey()
    
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        central_widget = QWidget()
        central_widget.setObjectName("quickboardRoot")
        self.root_widget = central_widget
        self.setCentralWidget(central_widget)
        self._register_themed_widget(central_widget)

        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)

        # Nagłówek
        header_layout = QHBoxLayout()

        self.header_label = QLabel("📋 Historia Schowka")
        header_font = QFont(self.header_label.font())
        header_font.setPointSize(16)
        header_font.setBold(True)
        self.header_label.setFont(header_font)
        self.header_label.setObjectName("quickboardHeaderLabel")
        self.header_label.setContentsMargins(8, 8, 8, 8)
        self._register_themed_widget(self.header_label)
        header_layout.addWidget(self.header_label)

        header_layout.addStretch()

        # Status monitoringu
        self.status_label = QLabel("🟢 Monitoring WŁĄCZONY")
        self.status_label.setObjectName("quickboardStatusLabel")
        self.status_label.setProperty("quickboardState", "active")
        self._register_themed_widget(self.status_label)
        header_layout.addWidget(self.status_label)

        # Przycisk monitoring
        self.toggle_monitor_btn = QPushButton("⏸ Wstrzymaj")
        self.toggle_monitor_btn.setObjectName("quickboardToggleMonitorButton")
        self.toggle_monitor_btn.setProperty("quickboardState", "active")
        self.toggle_monitor_btn.clicked.connect(self.toggle_monitoring)
        self._register_themed_widget(self.toggle_monitor_btn)
        header_layout.addWidget(self.toggle_monitor_btn)

        main_layout.addLayout(header_layout)

        # Splitter
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # LEWA SEKCJA - Lista historii
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)

        # PRAWA SEKCJA - Podgląd
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)

        # Proporcje 60:40
        splitter.setStretchFactor(0, 60)
        splitter.setStretchFactor(1, 40)

        main_layout.addWidget(splitter)
        
        # Pasek statusu
        self._show_status_message(f"Historia: {len(self.history)} elementów")
    
    def _register_themed_widget(self, widget):
        """Zapamiętuje widget wymagający repolishowania przy zmianie motywu"""
        if not widget:
            return
        if widget not in self._themed_widgets:
            self._themed_widgets.append(widget)

    @staticmethod
    def _polish_widget(widget):
        """Ponownie aplikuje style QSS na podanym widżecie"""
        if not widget:
            return
        style = widget.style()
        if style:
            style.unpolish(widget)
            style.polish(widget)
        widget.update()

    def _repolish_widgets(self):
        for widget in self._themed_widgets:
            self._polish_widget(widget)

    def _show_status_message(self, message, timeout=0):
        status_bar = self.statusBar()
        if status_bar:
            status_bar.showMessage(message, timeout)

    def _set_quickboard_state(self, widget, state):
        """Ustawia stan motywu dla widgetu (np. aktywny/nieaktywny)"""
        if not widget:
            return
        if widget.property("quickboardState") != state:
            widget.setProperty("quickboardState", state)
        self._polish_widget(widget)

    def apply_theme(self, refresh_history=True):
        """Aplikuje aktualny motyw do zarejestrowanych widżetów"""
        self._pinned_color_cache = None
        self._repolish_widgets()
        if refresh_history:
            self.refresh_history_list()

    def _build_pinned_color(self):
        if self.theme_manager:
            try:
                colors = self.theme_manager.get_current_colors() or {}
            except Exception:
                colors = {}
            accent_hex = colors.get('accent_primary', '#FFD54F')
            color = QColor(accent_hex)
            color.setAlpha(70)
            return color
        palette = self.palette()
        if palette is not None:
            base_color = palette.highlight().color()
            color = QColor(base_color)
            color.setAlpha(90)
            return color
        return QColor(255, 248, 220)

    def _get_pinned_color(self):
        if getattr(self, '_pinned_color_cache', None) is None:
            self._pinned_color_cache = self._build_pinned_color()
        if not isinstance(self._pinned_color_cache, QColor):
            self._pinned_color_cache = QColor('#FFF8DC')
        return self._pinned_color_cache

    def _initialize_i18n_support(self):
        if not get_i18n:
            return
        try:
            self._i18n = get_i18n()
        except Exception:
            self._i18n = None
        if self._i18n:
            try:
                self._i18n.language_changed.connect(self.update_translations)
            except Exception:
                pass

    def update_translations(self):
        """Reakcja na zmianę języka/motywu w systemie"""
        self.apply_theme()

    def create_left_panel(self):
        """Tworzy lewą sekcję - lista historii"""
        panel = QGroupBox("Historia")
        panel.setProperty("quickboardPanel", "history")
        self._register_themed_widget(panel)
        layout = QVBoxLayout()
        
        # Pasek wyszukiwania i filtrów
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Szukaj w historii...")
        self.search_input.textChanged.connect(self.filter_history)
        search_layout.addWidget(self.search_input)
        
        self.type_filter = QComboBox()
        self.type_filter.addItems(["Wszystkie", "Tekst", "Link", "Kod", "Email", "Obraz", "Pliki", "Przypięte"])
        self.type_filter.currentTextChanged.connect(self.filter_history)
        search_layout.addWidget(self.type_filter)
        
        layout.addLayout(search_layout)
        
        # Lista elementów
        self.history_list = QListWidget()
        self.history_list.setObjectName("quickboardHistoryList")
        self.history_list.setAlternatingRowColors(True)
        self.history_list.itemClicked.connect(self.on_item_selected)
        self.history_list.itemDoubleClicked.connect(self.copy_to_clipboard)
        self._register_themed_widget(self.history_list)
        layout.addWidget(self.history_list)
        
        # Przyciski akcji
        buttons_layout = QHBoxLayout()
        
        btn_copy = QPushButton("📋 Kopiuj")
        btn_copy.clicked.connect(self.copy_to_clipboard)
        btn_copy.setProperty("quickboardRole", "primary")
        self._register_themed_widget(btn_copy)
        buttons_layout.addWidget(btn_copy)
        
        btn_pin = QPushButton("📌 Przypnij")
        btn_pin.clicked.connect(self.toggle_pin)
        btn_pin.setProperty("quickboardRole", "neutral")
        self._register_themed_widget(btn_pin)
        buttons_layout.addWidget(btn_pin)
        
        btn_delete = QPushButton("🗑 Usuń")
        btn_delete.clicked.connect(self.delete_item)
        btn_delete.setProperty("quickboardRole", "danger")
        self._register_themed_widget(btn_delete)
        buttons_layout.addWidget(btn_delete)
        
        btn_clear = QPushButton("🧹 Wyczyść wszystko")
        btn_clear.clicked.connect(self.clear_history)
        btn_clear.setProperty("quickboardRole", "neutral")
        self._register_themed_widget(btn_clear)
        buttons_layout.addWidget(btn_clear)
        
        layout.addLayout(buttons_layout)
        
        panel.setLayout(layout)
        return panel
    
    def create_right_panel(self):
        """Tworzy prawą sekcję - podgląd"""
        panel = QGroupBox("Podgląd")
        panel.setProperty("quickboardPanel", "preview")
        self._register_themed_widget(panel)
        layout = QVBoxLayout()

        # Info o elemencie
        self.info_label = QLabel("Wybierz element z listy")
        info_font = QFont(self.info_label.font())
        info_font.setBold(True)
        self.info_label.setFont(info_font)
        self.info_label.setObjectName("quickboardInfoLabel")
        self.info_label.setContentsMargins(6, 6, 6, 6)
        self._register_themed_widget(self.info_label)
        layout.addWidget(self.info_label)

        # Podgląd zawartości tekstowej
        self.preview_text = QTextEdit()
        self.preview_text.setReadOnly(True)
        self.preview_text.setPlaceholderText("Tutaj pojawi się zawartość wybranego elementu...")
        self.preview_text.setObjectName("quickboardPreviewText")
        self._register_themed_widget(self.preview_text)
        layout.addWidget(self.preview_text)

        # Podgląd obrazów
        self.preview_image_scroll = QScrollArea()
        self.preview_image_label = QLabel()
        self.preview_image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_image_scroll.setWidget(self.preview_image_label)
        self.preview_image_scroll.setWidgetResizable(True)
        self.preview_image_scroll.hide()
        self.preview_image_scroll.setObjectName("quickboardImageScroll")
        self._register_themed_widget(self.preview_image_scroll)
        layout.addWidget(self.preview_image_scroll)

        # Przycisk AI dla notatek (początkowo ukryty)
        self.ai_note_btn = QPushButton("🤖 Utwórz notatkę z analizą AI")
        self.ai_note_btn.setObjectName("quickboardAiButton")
        self.ai_note_btn.setProperty("quickboardRole", "ai")
        self._register_themed_widget(self.ai_note_btn)
        self.ai_note_btn.clicked.connect(self.create_ai_note)
        self.ai_note_btn.hide()  # Ukryj domyślnie
        layout.addWidget(self.ai_note_btn)

        # Statystyki
        stats_group = QGroupBox("📊 Statystyki")
        stats_group.setProperty("quickboardPanel", "stats")
        stats_layout = QVBoxLayout()

        self.stats_total = QLabel("Łącznie: 0")
        self.stats_pinned = QLabel("Przypięte: 0")
        self.stats_today = QLabel("Dzisiaj: 0")

        stats_layout.addWidget(self.stats_total)
        stats_layout.addWidget(self.stats_pinned)
        stats_layout.addWidget(self.stats_today)

        stats_group.setLayout(stats_layout)
        self._register_themed_widget(stats_group)
        layout.addWidget(stats_group)
        
        # Akcje eksportu
        export_layout = QHBoxLayout()
        
        btn_export = QPushButton("💾 Eksport")
        btn_export.clicked.connect(self.export_history)
        btn_export.setProperty("quickboardRole", "neutral")
        self._register_themed_widget(btn_export)
        export_layout.addWidget(btn_export)
        
        btn_import = QPushButton("📥 Import")
        btn_import.clicked.connect(self.import_history)
        btn_import.setProperty("quickboardRole", "neutral")
        self._register_themed_widget(btn_import)
        export_layout.addWidget(btn_import)
        
        layout.addLayout(export_layout)
        
        panel.setLayout(layout)
        return panel
    
    def start_monitoring(self):
        """Uruchamia monitoring schowka"""
        if self.monitor is None:
            clipboard = QApplication.clipboard()
            self.monitor = ClipboardMonitor(clipboard)
            self.monitor.clipboard_changed.connect(self.on_clipboard_changed)
        
        if not self.monitoring_active:
            self.monitor.start()
            self.monitoring_active = True
            self.update_monitoring_ui()
    
    def stop_monitoring(self):
        """Zatrzymuje monitoring schowka"""
        if self.monitor and self.monitoring_active:
            self.monitor.stop()
            self.monitor.wait()
            self.monitoring_active = False
            self.update_monitoring_ui()
    
    def toggle_monitoring(self):
        """Przełącza monitoring"""
        if self.monitoring_active:
            self.stop_monitoring()
        else:
            self.start_monitoring()
    
    def update_monitoring_ui(self):
        """Aktualizuje UI statusu monitoringu"""
        if self.monitoring_active:
            self.status_label.setText("🟢 Monitoring WŁĄCZONY")
            self._set_quickboard_state(self.status_label, "active")
            self.toggle_monitor_btn.setText("⏸ Wstrzymaj")
            self._set_quickboard_state(self.toggle_monitor_btn, "active")
        else:
            self.status_label.setText("🔴 Monitoring WYŁĄCZONY")
            self._set_quickboard_state(self.status_label, "inactive")
            self.toggle_monitor_btn.setText("▶ Uruchom")
            self._set_quickboard_state(self.toggle_monitor_btn, "inactive")
    
    def on_clipboard_changed(self, content_type, content_text, binary_data):
        """Wywoływane gdy schowek się zmienił (zoptymalizowane)"""
        # Optymalizacja: sprawdź duplikaty przed utworzeniem obiektu
        if self.history:
            last = self.history[0]
            # Szybkie sprawdzenie typu
            if last.content_type == content_type:
                if content_type == "Obraz":
                    # Dla obrazów porównaj rozmiary
                    if isinstance(binary_data, QImage) and isinstance(last.binary_data, QImage):
                        if (binary_data.width() == last.binary_data.width() and 
                            binary_data.height() == last.binary_data.height()):
                            return
                elif last.content == content_text:
                    return
        
        # Dodaj do historii
        item = ClipboardItem(content_text, content_type, binary_data=binary_data)
        self.history.insert(0, item)
        
        # Optymalizacja: ogranicz rozmiar tylko gdy przekroczy limit
        if len(self.history) > self.max_history:
            # Zachowaj przypięte + najnowsze nieprzypięte
            pinned = [h for h in self.history if h.pinned]
            unpinned = [h for h in self.history if not h.pinned][:self.max_history - len(pinned)]
            self.history = pinned + unpinned
        
        # Odśwież UI (zoptymalizowane - tylko nowy element)
        self.add_item_to_list(item, insert_at_top=True)
        self.update_stats()
        
        # Zapisz asynchronicznie (nie blokuj UI)
        QTimer.singleShot(1000, self.save_data)  # Opóźniony zapis co 1s
    
    def refresh_history_list(self):
        """Odświeża listę historii (zoptymalizowane)"""
        # Optymalizacja: blokuj sygnały podczas masowych zmian
        self.history_list.blockSignals(True)
        self.history_list.clear()
        
        search_text = self.search_input.text().lower()
        type_filter = self.type_filter.currentText()
        
        for item in self.history:
            # Filtruj po typie (szybkie sprawdzenie)
            if type_filter == "Przypięte":
                if not item.pinned:
                    continue
            elif type_filter != "Wszystkie" and item.content_type != type_filter:
                continue
            
            # Filtruj po wyszukiwaniu (tylko jeśli jest tekst)
            if search_text and not self._matches_search(item, search_text):
                continue
            
            # Dodaj do listy
            self.add_item_to_list(item, insert_at_top=False)
        
        # Odblokuj sygnały
        self.history_list.blockSignals(False)
    
    def _matches_search(self, item, search_text):
        """Pomocnicza funkcja sprawdzająca czy element pasuje do wyszukiwania"""
        # Dla tekstów szukaj w contencie
        if item.content and search_text in item.content.lower():
            return True
        # Dla plików szukaj w nazwach
        if item.content_type == "Pliki" and isinstance(item.binary_data, list):
            return any(search_text in str(f).lower() for f in item.binary_data)
        # Dla reszty sprawdź preview
        return search_text in item.preview.lower()
    
    def add_item_to_list(self, item, insert_at_top=False):
        """Dodaje pojedynczy element do listy (zoptymalizowane)"""
        icon = self.get_type_icon(item.content_type)
        pin_icon = "📌 " if item.pinned else ""
        
        list_item = QListWidgetItem(f"{pin_icon}{icon} {item.preview}\n   📅 {item.timestamp}")
        list_item.setData(Qt.ItemDataRole.UserRole, item)
        
        # Koloruj przypięte
        if item.pinned:
            list_item.setBackground(self._get_pinned_color())
        
        if insert_at_top:
            self.history_list.insertItem(0, list_item)
        else:
            self.history_list.addItem(list_item)
    
    def get_type_icon(self, content_type):
        """Zwraca emoji dla typu"""
        icons = {
            "Tekst": "📝",
            "Link": "🔗",
            "Kod": "💻",
            "Email": "📧",
            "Pliki": "📁",
            "Obraz": "🖼️"
        }
        return icons.get(content_type, "📄")
    
    def filter_history(self):
        """Filtruje historię"""
        self.refresh_history_list()
    
    def on_item_selected(self, item):
        """Wywoływane gdy wybrano element z listy (zoptymalizowane)"""
        clipboard_item = item.data(Qt.ItemDataRole.UserRole)
        
        if not clipboard_item:
            self.ai_note_btn.hide()
            return
        
        # Zapisz aktualnie wybrany element
        self.current_selected_item = clipboard_item
        
        # Aktualizuj info (w jednym kroku)
        content_type = clipboard_item.content_type
        
        if content_type == "Obraz":
            size_info = (f"📏 {clipboard_item.binary_data.width()}x{clipboard_item.binary_data.height()}px" 
                        if isinstance(clipboard_item.binary_data, QImage) else "Obraz")
        elif content_type == "Pliki":
            count = len(clipboard_item.binary_data) if isinstance(clipboard_item.binary_data, list) else 0
            size_info = f"📏 {count} plik(ów)"
        else:
            size_info = f"📏 {len(clipboard_item.content)} znaków" if clipboard_item.content else ""
        
        self.info_label.setText(
            f"{self.get_type_icon(content_type)} {content_type} | "
            f"📅 {clipboard_item.timestamp} | {size_info}"
        )
        
        # Aktualizuj podgląd (rozdziel obrazy vs tekst)
        if content_type == "Obraz":
            self._show_image_preview(clipboard_item)
            self.ai_note_btn.hide()  # Ukryj dla obrazów
        else:
            self._show_text_preview(clipboard_item)
            # Pokaż przycisk AI dla tekstów, kodu, plików, linków
            if content_type in ["Tekst", "Kod", "Link", "Email", "Pliki"]:
                self.ai_note_btn.show()
            else:
                self.ai_note_btn.hide()
    
    def _show_image_preview(self, clipboard_item):
        """Wyświetla podgląd obrazu"""
        self.preview_text.hide()
        self.preview_image_scroll.show()
        
        if isinstance(clipboard_item.binary_data, QImage):
            pixmap = QPixmap.fromImage(clipboard_item.binary_data)
            # Optymalizacja: skaluj tylko jeśli naprawdę potrzeba
            if pixmap.width() > 600:
                pixmap = pixmap.scaledToWidth(600, Qt.TransformationMode.SmoothTransformation)
            self.preview_image_label.setPixmap(pixmap)
        else:
            self.preview_image_label.setText("Nie można wyświetlić obrazu")
    
    def _show_text_preview(self, clipboard_item):
        """Wyświetla podgląd tekstu/plików"""
        self.preview_image_scroll.hide()
        self.preview_text.show()
        
        if clipboard_item.content_type == "Pliki" and isinstance(clipboard_item.binary_data, list):
            # Optymalizacja: buduj string zamiast listy
            files_info = []
            for file_path in clipboard_item.binary_data:
                path_obj = Path(file_path)
                if path_obj.exists():
                    if path_obj.is_file():
                        size = path_obj.stat().st_size
                        size_str = self.format_file_size(size)
                        files_info.append(f"📄 {path_obj.name}\n   📁 {path_obj.parent}\n   📏 {size_str}")
                    else:
                        files_info.append(f"📁 {path_obj.name}\n   📂 {file_path}")
                else:
                    files_info.append(f"❌ {file_path} (nie istnieje)")
            self.preview_text.setPlainText("\n\n".join(files_info))
        else:
            self.preview_text.setPlainText(clipboard_item.content or "")
    
    def copy_to_clipboard(self):
        """Kopiuje wybrany element do schowka"""
        current_item = self.history_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Błąd", "Wybierz element do skopiowania!")
            return
        
        clipboard_item = current_item.data(Qt.ItemDataRole.UserRole)
        clipboard = QApplication.clipboard()
        if clipboard is None:
            QMessageBox.warning(self, "Błąd", "Schowek jest niedostępny.")
            return
        
        # Kopiuj w zależności od typu
        if clipboard_item.content_type == "Obraz":
            if isinstance(clipboard_item.binary_data, QImage):
                clipboard.setImage(clipboard_item.binary_data)
                # Ustaw ostatnie dane aby nie zapisać ponownie
                byte_array = QByteArray()
                buffer = QBuffer(byte_array)
                buffer.open(QIODevice.OpenModeFlag.WriteOnly)
                clipboard_item.binary_data.save(buffer, "PNG")
                if self.monitor:
                    self.monitor.last_image_data = byte_array.data()
        elif clipboard_item.content_type == "Pliki":
            if isinstance(clipboard_item.binary_data, list):
                mime_data = QMimeData()
                urls = [QUrl.fromLocalFile(f) for f in clipboard_item.binary_data]
                mime_data.setUrls(urls)
                clipboard.setMimeData(mime_data)
                if self.monitor:
                    self.monitor.last_urls = clipboard_item.binary_data
        else:
            pyperclip.copy(clipboard_item.content)
            if self.monitor:
                self.monitor.last_content = clipboard_item.content
        
        self._show_status_message(f"Skopiowano: {clipboard_item.preview}", 3000)
    
    def format_file_size(self, size_bytes):
        """Formatuje rozmiar pliku"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size_bytes < 1024.0:
                return f"{size_bytes:.1f} {unit}"
            size_bytes /= 1024.0
        return f"{size_bytes:.1f} TB"
    
    def toggle_pin(self):
        """Przypina/odpina element"""
        current_item = self.history_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Błąd", "Wybierz element do przypięcia!")
            return
        
        clipboard_item = current_item.data(Qt.ItemDataRole.UserRole)
        clipboard_item.pinned = not clipboard_item.pinned
        
        self.refresh_history_list()
        self.update_stats()
        self.save_data()
        
        status = "przypięty" if clipboard_item.pinned else "odpięty"
        self._show_status_message(f"Element {status}", 2000)
    
    def delete_item(self):
        """Usuwa wybrany element"""
        current_item = self.history_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "Błąd", "Wybierz element do usunięcia!")
            return
        
        clipboard_item = current_item.data(Qt.ItemDataRole.UserRole)
        
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            "Czy na pewno chcesz usunąć ten element?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history.remove(clipboard_item)
            self.refresh_history_list()
            self.update_stats()
            self.save_data()
            self._show_status_message("Element usunięty", 2000)
    
    def clear_history(self):
        """Czyści całą historię (zachowując przypięte)"""
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            "Czy na pewno chcesz wyczyścić historię?\n(Przypięte elementy zostaną zachowane)",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.history = [item for item in self.history if item.pinned]
            self.refresh_history_list()
            self.update_stats()
            self.save_data()
            self._show_status_message("Historia wyczyszczona", 2000)
    
    def update_stats(self):
        """Aktualizuje statystyki"""
        total = len(self.history)
        pinned = sum(1 for item in self.history if item.pinned)
        
        today = datetime.now().strftime("%Y-%m-%d")
        today_count = sum(1 for item in self.history if item.timestamp.startswith(today))
        
        self.stats_total.setText(f"Łącznie: {total}")
        self.stats_pinned.setText(f"Przypięte: {pinned}")
        self.stats_today.setText(f"Dzisiaj: {today_count}")
        
        self._show_status_message(f"Historia: {total} elementów")
    
    def export_history(self):
        """Eksportuje historię do JSON"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Eksportuj historię",
            "clipboard_export.json",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                data = {
                    'exported': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    'count': len(self.history),
                    'items': [item.to_dict() for item in self.history]
                }
                
                with open(file_path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Wyeksportowano {len(self.history)} elementów do:\n{file_path}"
                )
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Błąd eksportu: {str(e)}")
    
    def import_history(self):
        """Importuje historię z JSON"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importuj historię",
            "",
            "JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                imported_items = [ClipboardItem.from_dict(item) for item in data.get('items', [])]
                
                # Dodaj na początek
                self.history = imported_items + self.history
                
                # Ogranicz
                if len(self.history) > self.max_history * 2:  # Pozwól na więcej przy imporcie
                    self.history = self.history[:self.max_history * 2]
                
                self.refresh_history_list()
                self.update_stats()
                self.save_data()
                
                QMessageBox.information(
                    self,
                    "Sukces",
                    f"Zaimportowano {len(imported_items)} elementów"
                )
            except Exception as e:
                QMessageBox.critical(self, "Błąd", f"Błąd importu: {str(e)}")
    
    def save_data(self):
        """Zapisuje historię do pliku (zoptymalizowane)"""
        try:
            # Optymalizacja: ogranicz ilość zapisywanych elementów (max 100)
            items_to_save = self.history[:100]
            
            data = {
                'saved': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'items': [item.to_dict() for item in items_to_save]
            }
            
            # Optymalizacja: zapisz z mniejszym wcięciem (mniejszy plik)
            with open(self.history_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=1, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisu danych: {e}")
    
    def load_data(self):
        """Ładuje historię z pliku (zoptymalizowane)"""
        if not self.history_file.exists():
            self.history = []
            return
        
        try:
            with open(self.history_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Optymalizacja: ogranicz ilość ładowanych elementów
            items_data = data.get('items', [])[:100]
            
            # Optymalizacja: użyj list comprehension (szybsze niż pętla)
            self.history = [ClipboardItem.from_dict(item) for item in items_data]
            
            print(f"Wczytano {len(self.history)} elementów z historii")
        except Exception as e:
            print(f"Błąd wczytywania danych: {e}")
            self.history = []
    
    def create_ai_note(self):
        """Tworzy notatkę z analizą AI na podstawie zawartości schowka"""
        if not self.current_selected_item:
            QMessageBox.warning(self, "Błąd", "Nie wybrano elementu do analizy!")
            return
        
        item = self.current_selected_item
        content_type = item.content_type
        
        # Przygotuj zawartość do analizy
        analysis_content = ""
        
        if content_type == "Pliki":
            # Dla plików - lista ścieżek i informacje
            if isinstance(item.binary_data, list):
                analysis_content = "PLIKI DO ANALIZY:\n\n"
                for file_path in item.binary_data:
                    path_obj = Path(file_path)
                    if path_obj.exists():
                        if path_obj.is_file():
                            size = path_obj.stat().st_size
                            analysis_content += f"📄 {path_obj.name}\n"
                            analysis_content += f"   Ścieżka: {file_path}\n"
                            analysis_content += f"   Rozmiar: {self.format_file_size(size)}\n"
                            
                            # Jeśli to plik tekstowy, spróbuj odczytać zawartość
                            if path_obj.suffix.lower() in ['.txt', '.md', '.py', '.js', '.json', '.xml', '.html', '.css']:
                                try:
                                    with open(file_path, 'r', encoding='utf-8') as f:
                                        file_content = f.read(5000)  # Max 5000 znaków
                                        analysis_content += f"   Zawartość (początek):\n{file_content[:500]}\n"
                                except:
                                    analysis_content += "   (Nie można odczytać zawartości)\n"
                        else:
                            analysis_content += f"📁 {path_obj.name}\n"
                            analysis_content += f"   Folder: {file_path}\n"
                    else:
                        analysis_content += f"❌ {file_path} (nie istnieje)\n"
                    analysis_content += "\n"
        else:
            # Dla tekstów, kodu, linków, emaili
            analysis_content = item.content or ""
        
        # Jeśli nie ma zawartości
        if not analysis_content.strip():
            QMessageBox.warning(self, "Błąd", "Brak zawartości do analizy!")
            return
        
        # Pokaż okno dialogowe z analizą AI
        self._show_ai_note_dialog(content_type, analysis_content)
    
    def _show_ai_note_dialog(self, content_type, content):
        """Wyświetla okno dialogowe z propozycją notatki AI"""
        from PyQt6.QtWidgets import QDialog, QDialogButtonBox, QProgressBar
        
        dialog = QDialog(self)
        dialog.setWindowTitle("🤖 Tworzenie notatki z analizą AI")
        dialog.setMinimumSize(700, 500)
        
        layout = QVBoxLayout()
        
        # Nagłówek
        header = QLabel(f"Analiza zawartości: {self.get_type_icon(content_type)} {content_type}")
        header_font = QFont(header.font())
        header_font.setPointSize(14)
        header_font.setBold(True)
        header.setFont(header_font)
        header.setObjectName("quickboardAiDialogHeader")
        header.setContentsMargins(10, 10, 10, 10)
        self._polish_widget(header)
        layout.addWidget(header)
        
        # Informacja
        info_label = QLabel(
            "💡 Poniżej znajduje się zawartość do analizy.\n"
            "Możesz skopiować ją i wkleić do ChatGPT/Claude/Gemini lub innego AI.\n"
            "Przykładowy prompt: 'Przeanalizuj poniższą zawartość i utwórz zwięzłą notatkę z kluczowymi informacjami:'"
        )
        info_label.setWordWrap(True)
        info_label.setObjectName("quickboardAiDialogInfo")
        info_label.setContentsMargins(10, 8, 10, 8)
        self._polish_widget(info_label)
        layout.addWidget(info_label)
        
        # Pole z zawartością
        content_label = QLabel("📋 Zawartość do analizy:")
        content_font = QFont(content_label.font())
        content_font.setBold(True)
        content_label.setFont(content_font)
        content_label.setObjectName("quickboardAiDialogSectionLabel")
        content_label.setContentsMargins(0, 8, 0, 4)
        self._polish_widget(content_label)
        layout.addWidget(content_label)
        
        content_text = QTextEdit()
        content_text.setPlainText(content)
        content_text.setReadOnly(False)  # Można edytować
        content_text.setObjectName("quickboardAiDialogText")
        self._polish_widget(content_text)
        layout.addWidget(content_text)
        
        # Przykładowe prompty
        prompts_group = QGroupBox("💬 Przykładowe prompty dla AI:")
        prompts_layout = QVBoxLayout()
        
        prompt_examples = [
            "Przeanalizuj poniższą zawartość i utwórz zwięzłą notatkę z najważniejszymi informacjami.",
            "Wyodrębnij kluczowe punkty z poniższego tekstu i przedstaw je w formie listy.",
            "Podsumuj główne wnioski i spostrzeżenia z poniższej zawartości.",
            "Znajdź najważniejsze daty, nazwiska i fakty z poniższego tekstu.",
        ]
        
        for i, prompt in enumerate(prompt_examples, 1):
            prompt_btn = QPushButton(f"{i}. {prompt[:60]}...")
            prompt_btn.setObjectName("quickboardAiDialogPromptButton")
            prompt_btn.setProperty("quickboardRole", "prompt")
            prompt_btn.setProperty("quickboardPromptAlign", "left")
            prompt_btn.clicked.connect(lambda checked, p=prompt: self._copy_prompt_with_content(p, content))
            self._polish_widget(prompt_btn)
            prompts_layout.addWidget(prompt_btn)
        
        prompts_group.setLayout(prompts_layout)
        prompts_group.setObjectName("quickboardAiDialogPromptGroup")
        self._polish_widget(prompts_group)
        layout.addWidget(prompts_group)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        
        btn_copy_content = QPushButton("📋 Kopiuj zawartość")
        btn_copy_content.clicked.connect(lambda: self._copy_to_clipboard_temp(content))
        btn_copy_content.setProperty("quickboardRole", "primary")
        self._polish_widget(btn_copy_content)
        buttons_layout.addWidget(btn_copy_content)
        
        btn_copy_all = QPushButton("📝 Kopiuj z promptem")
        btn_copy_all.clicked.connect(lambda: self._copy_prompt_with_content(prompt_examples[0], content))
        btn_copy_all.setProperty("quickboardRole", "success")
        self._polish_widget(btn_copy_all)
        buttons_layout.addWidget(btn_copy_all)
        
        btn_close = QPushButton("✖ Zamknij")
        btn_close.clicked.connect(dialog.close)
        btn_close.setProperty("quickboardRole", "neutral")
        self._polish_widget(btn_close)
        buttons_layout.addWidget(btn_close)
        
        layout.addLayout(buttons_layout)
        
        dialog.setLayout(layout)
        dialog.exec()
    
    def _copy_to_clipboard_temp(self, text):
        """Pomocnicza funkcja - kopiuje tekst do schowka"""
        clipboard = QApplication.clipboard()
        if clipboard is None:
            QMessageBox.warning(self, "Błąd", "Schowek jest niedostępny.")
            return
        clipboard.setText(text)
        
        # Ustaw w monitorze aby nie zapisywał ponownie
        if self.monitor:
            self.monitor.last_content = text
        
        QMessageBox.information(self, "Sukces", "Zawartość skopiowana do schowka!\nMożesz teraz wkleić ją do AI.")
    
    def _copy_prompt_with_content(self, prompt, content):
        """Kopiuje prompt wraz z zawartością"""
        full_text = f"{prompt}\n\n---\n\n{content}"
        self._copy_to_clipboard_temp(full_text)
    
    def closeEvent(self, a0: QCloseEvent | None):
        """Wywoływane przy zamykaniu okna"""
        # Zatrzymaj monitoring
        self.stop_monitoring()
        
        # Zapisz dane
        self.save_data()
        
        if a0 is not None:
            a0.accept()


def main():
    """Funkcja główna - uruchamia aplikację"""
    app = QApplication(sys.argv)
    app.setApplicationName("Clipboard Manager")
    app.setOrganizationName("Pro Ka Po Comer")
    
    window = ClipboardManager()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
