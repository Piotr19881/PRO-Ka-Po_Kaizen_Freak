"""
Main Window - Główne okno aplikacji
"""
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QLineEdit, QCheckBox, QComboBox, QTableWidget, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint
from PyQt6.QtGui import QFont, QMouseEvent, QAction
from loguru import logger

from ..utils.i18n_manager import t, get_i18n
from ..core.config import config
from .config_view import SettingsView


class CustomTitleBar(QWidget):
    """Własny pasek tytułowy z przyciskami okna"""
    
    # Sygnały
    logout_requested = pyqtSignal()
    settings_tab_requested = pyqtSignal(int)  # index karty w ustawieniach
    help_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.dragging = False
        self.drag_position = QPoint()
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja paska tytułowego"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(10)
        
        # === LEWA STRONA: Użytkownik + Motyw ===
        left_layout = QHBoxLayout()
        left_layout.setSpacing(5)
        
        # Przycisk użytkownika z menu
        self.user_btn = QPushButton("👤")
        self.user_btn.setFixedSize(35, 35)
        self.user_btn.setObjectName("titleBarUserButton")
        self.user_btn.setToolTip("Menu użytkownika")
        self.user_btn.clicked.connect(self._show_user_menu)
        left_layout.addWidget(self.user_btn)
        
        # Przycisk zmiany motywu
        self.theme_btn = QPushButton("☀")
        self.theme_btn.setFixedSize(35, 35)
        self.theme_btn.setObjectName("titleBarThemeButton")
        self.theme_btn.setToolTip("Zmień motyw")
        left_layout.addWidget(self.theme_btn)
        
        layout.addLayout(left_layout)
        
        # === ŚRODEK: Nazwa aplikacji ===
        layout.addStretch()
        
        self.title_label = QLabel("📒 PRO-Ka-Po Kaizen Freak")
        self.title_label.setObjectName("titleBarLabel")
        title_font = QFont()
        title_font.setPointSize(12)
        title_font.setBold(True)
        self.title_label.setFont(title_font)
        layout.addWidget(self.title_label)
        
        layout.addStretch()
        
        # === PRAWA STRONA: Przyciski okna (Minimize/Maximize/Close) ===
        right_layout = QHBoxLayout()
        right_layout.setSpacing(0)
        
        # Minimize
        self.minimize_btn = QPushButton("−")
        self.minimize_btn.setFixedSize(45, 35)
        self.minimize_btn.setObjectName("minimizeButton")
        self.minimize_btn.setToolTip("Minimalizuj")
        self.minimize_btn.clicked.connect(self._on_minimize)
        right_layout.addWidget(self.minimize_btn)
        
        # Maximize/Restore
        self.maximize_btn = QPushButton("□")
        self.maximize_btn.setFixedSize(45, 35)
        self.maximize_btn.setObjectName("maximizeButton")
        self.maximize_btn.setToolTip("Maksymalizuj")
        self.maximize_btn.clicked.connect(self._on_maximize)
        right_layout.addWidget(self.maximize_btn)
        
        # Close
        self.close_btn = QPushButton("✕")
        self.close_btn.setFixedSize(45, 35)
        self.close_btn.setObjectName("closeButton")
        self.close_btn.setToolTip("Zamknij")
        self.close_btn.clicked.connect(self._on_close)
        right_layout.addWidget(self.close_btn)
        
        layout.addLayout(right_layout)
        
        # Ustaw wysokość paska
        self.setFixedHeight(45)
        self.setObjectName("customTitleBar")
    
    def _show_user_menu(self):
        """Pokaż menu użytkownika"""
        menu = QMenu(self)
        
        # === WYLOGUJ ===
        logout_action = QAction(f"🚪 {t('user_menu.logout')}", self)
        logout_action.triggered.connect(self.logout_requested.emit)
        menu.addAction(logout_action)
        
        # Separator
        menu.addSeparator()
        
        # === USTAWIENIA (z podmenu) ===
        settings_menu = menu.addMenu(f"⚙️ {t('user_menu.settings')}")
        
        # Lista kart ustawień (zgodna z config_view.py)
        settings_tabs = [
            (t('user_menu.settings.general'), 0),
            (t('user_menu.settings.tasks'), 1),
            (t('user_menu.settings.kanban'), 2),
            (t('user_menu.settings.custom'), 3),
            (t('user_menu.settings.transcriptor'), 4),
            (t('user_menu.settings.ai'), 5),
            (t('user_menu.settings.about'), 6),
        ]
        
        for tab_name, tab_index in settings_tabs:
            action = QAction(tab_name, self)
            action.triggered.connect(lambda checked, idx=tab_index: self.settings_tab_requested.emit(idx))
            settings_menu.addAction(action)
        
        # Separator
        menu.addSeparator()
        
        # === POMOC ===
        help_action = QAction(f"❓ {t('user_menu.help')}", self)
        help_action.triggered.connect(self.help_requested.emit)
        menu.addAction(help_action)
        
        # Pokaż menu pod przyciskiem
        menu.exec(self.user_btn.mapToGlobal(self.user_btn.rect().bottomLeft()))
    
    def _on_minimize(self):
        """Minimalizuj okno"""
        if self.parent_window:
            self.parent_window.showMinimized()
    
    def _on_maximize(self):
        """Maksymalizuj/Przywróć okno"""
        if self.parent_window:
            if self.parent_window.isMaximized():
                self.parent_window.showNormal()
                self.maximize_btn.setText("□")
                self.maximize_btn.setToolTip("Maksymalizuj")
            else:
                self.parent_window.showMaximized()
                self.maximize_btn.setText("❐")
                self.maximize_btn.setToolTip("Przywróć")
    
    def _on_close(self):
        """Zamknij okno"""
        if self.parent_window:
            self.parent_window.close()
    
    def mousePressEvent(self, event: QMouseEvent):
        """Rozpocznij przeciąganie okna"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = True
            self.drag_position = event.globalPosition().toPoint() - self.parent_window.frameGeometry().topLeft()
            event.accept()
    
    def mouseMoveEvent(self, event: QMouseEvent):
        """Przeciągnij okno"""
        if self.dragging and event.buttons() == Qt.MouseButton.LeftButton:
            if not self.parent_window.isMaximized():
                self.parent_window.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()
    
    def mouseReleaseEvent(self, event: QMouseEvent):
        """Zakończ przeciąganie okna"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.dragging = False
            event.accept()
    
    def mouseDoubleClickEvent(self, event: QMouseEvent):
        """Podwójne kliknięcie maksymalizuje/przywraca okno"""
        if event.button() == Qt.MouseButton.LeftButton:
            self._on_maximize()
            event.accept()
    
    def update_translations(self):
        """Odśwież tłumaczenia tooltipów"""
        self.user_btn.setToolTip(t('user_menu.settings'))
        self.theme_btn.setToolTip(t('settings.theme'))
        self.minimize_btn.setToolTip(t('button.minimize') if 'button.minimize' in dir(t) else "Minimalizuj")
        self.maximize_btn.setToolTip(t('button.maximize') if 'button.maximize' in dir(t) else "Maksymalizuj")
        self.close_btn.setToolTip(t('button.close'))


class NavigationBar(QWidget):
    """Górny pasek nawigacyjny z przyciskami zmiany widoków"""
    
    view_changed = pyqtSignal(str)  # Signal emitowany przy zmianie widoku
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu paska nawigacyjnego"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)
        
        # Lista przycisków nawigacyjnych - klucze dla i18n
        self.nav_keys = [
            'tasks',
            'kanban', 
            'pomodoro',
            'habit_tracker',
            'notes',
            'transcriptor',
            'alarms',
            'hotkey',
        ]
        
        self.buttons = {}
        
        for key in self.nav_keys:
            btn = QPushButton(t(f'nav.{key}'))  # Użyj tłumaczenia od razu
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setObjectName("navButton")
            btn.clicked.connect(lambda checked, k=key: self._on_button_clicked(k))
            layout.addWidget(btn, stretch=1)  # Równomierne rozciąganie
            self.buttons[key] = btn
        
        # Domyślnie zaznacz pierwszy przycisk
        self.buttons['tasks'].setChecked(True)
    
    def _on_button_clicked(self, view_name: str):
        """Obsługa kliknięcia przycisku nawigacyjnego"""
        # Odznacz wszystkie przyciski
        for btn in self.buttons.values():
            btn.setChecked(False)
        
        # Zaznacz kliknięty przycisk
        self.buttons[view_name].setChecked(True)
        
        # Emituj signal zmiany widoku
        self.view_changed.emit(view_name)
        logger.info(f"View changed to: {view_name}")
    
    def update_translations(self):
        """Odśwież tłumaczenia przycisków nawigacji"""
        translations = {
            'tasks': t('nav.tasks'),
            'kanban': t('nav.kanban'),
            'pomodoro': t('nav.pomodoro'),
            'habit_tracker': t('nav.habit_tracker'),
            'notes': t('nav.notes'),
            'transcriptor': t('nav.transcriptor'),
            'alarms': t('nav.alarms'),
            'hotkey': t('nav.hotkey'),
        }
        
        for key, btn in self.buttons.items():
            if key in translations:
                btn.setText(translations[key])
        
        logger.info("Navigation bar translations updated")


class ManagementBar(QWidget):
    """Pasek zarządzania - indywidualny dla każdego widoku"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja paska zarządzania"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Przykładowe przyciski zarządzania (będą różne dla każdego widoku)
        self.btn_add = QPushButton(t('button.add'))
        self.btn_edit = QPushButton(t('button.edit'))
        self.btn_delete = QPushButton(t('button.delete'))
        
        layout.addWidget(self.btn_add)
        layout.addWidget(self.btn_edit)
        layout.addWidget(self.btn_delete)
        layout.addStretch()
        
        # Dodatkowe kontrolki
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(t('button.search'))
        self.search_input.setMaximumWidth(200)
        layout.addWidget(self.search_input)
    
    def update_translations(self):
        """Odśwież tłumaczenia"""
        self.btn_add.setText(t('button.add'))
        self.btn_edit.setText(t('button.edit'))
        self.btn_delete.setText(t('button.delete'))
        self.search_input.setPlaceholderText(t('button.search'))


class DataDisplayArea(QWidget):
    """Obszar wyświetlania danych - tabele lub inne widoki"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja obszaru wyświetlania"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Placeholder - tabela
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels([
            t('task.title'),
            t('task.status'),
            t('task.priority'),
            t('task.due_date'),
            t('task.category')
        ])
        
        layout.addWidget(self.table)
    
    def update_translations(self):
        """Odśwież tłumaczenia nagłówków tabeli"""
        self.table.setHorizontalHeaderLabels([
            t('task.title'),
            t('task.status'),
            t('task.priority'),
            t('task.due_date'),
            t('task.category')
        ])


class QuickInputSection(QWidget):
    """Sekcja szybkiego wprowadzania zadań"""
    
    task_added = pyqtSignal(str)  # Signal emitowany przy dodaniu zadania
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja sekcji szybkiego wprowadzania"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)
        
        # Wiersz 1: Pole tekstowe + przyciski
        row1_layout = QHBoxLayout()
        
        # Pole tekstowe (szeroka kolumna)
        self.task_input = QLineEdit()
        self.task_input.setPlaceholderText(t('quick_input.placeholder'))
        self.task_input.setMinimumHeight(35)
        row1_layout.addWidget(self.task_input, stretch=10)
        
        # Przycisk dodawania (wąska kolumna)
        self.btn_add = QPushButton("+")
        self.btn_add.setFixedSize(35, 35)
        self.btn_add.setObjectName("quickAddButton")
        self.btn_add.clicked.connect(self._on_add_clicked)
        row1_layout.addWidget(self.btn_add)
        
        # Przycisk notatki (wąska kolumna)
        self.btn_note = QPushButton("📝")
        self.btn_note.setFixedSize(35, 35)
        self.btn_note.setObjectName("quickNoteButton")
        row1_layout.addWidget(self.btn_note)
        
        main_layout.addLayout(row1_layout)
        
        # Wiersz 2: Listy rozwijane + checkbox
        row2_layout = QHBoxLayout()
        
        # 5 list rozwijanych (blank na razie)
        self.combo_boxes = []
        combo_labels = ['Osoba', 'Narzędzia', 'Sprzęt/Obiekty', 'Czas', 'Oferta']
        
        for i, label in enumerate(combo_labels):
            combo = QComboBox()
            combo.addItem(label)
            combo.setMinimumHeight(30)
            row2_layout.addWidget(combo, stretch=1)
            self.combo_boxes.append(combo)
        
        # Duży checkbox (ostatnia kolumna)
        self.checkbox_kanban = QCheckBox()
        self.checkbox_kanban.setMinimumSize(30, 30)
        self.checkbox_kanban.setObjectName("bigCheckbox")
        self.checkbox_kanban.setToolTip("Dodaj do Kanban")
        row2_layout.addWidget(self.checkbox_kanban)
        
        main_layout.addLayout(row2_layout)
    
    def _on_add_clicked(self):
        """Obsługa kliknięcia przycisku dodawania"""
        task_text = self.task_input.text().strip()
        if task_text:
            self.task_added.emit(task_text)
            self.task_input.clear()
            logger.info(f"Quick task added: {task_text}")
    
    def update_translations(self):
        """Odśwież tłumaczenia"""
        self.task_input.setPlaceholderText(t('quick_input.placeholder'))
        self.checkbox_kanban.setToolTip(t('quick_input.add_to_kanban'))


class MainContentArea(QWidget):
    """Główna zawartość - pasek zarządzania + obszar danych"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja głównej zawartości"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Pasek zarządzania
        self.management_bar = ManagementBar()
        layout.addWidget(self.management_bar)
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Obszar wyświetlania danych
        self.data_area = DataDisplayArea()
        layout.addWidget(self.data_area)


class MainWindow(QMainWindow):
    """Główne okno aplikacji"""
    
    def __init__(self):
        super().__init__()
        self.user_data = None  # Dane zalogowanego użytkownika
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        self._initialize_theme_icon()
    
    def _initialize_theme_icon(self):
        """Ustaw ikonę motywu zgodnie z aktualnym layoutem"""
        from ..utils.theme_manager import get_theme_manager
        from ..core.config import load_settings
        
        settings = load_settings()
        current_layout = settings.get('current_layout', 1)
        
        if current_layout == 1:
            self.title_bar.theme_btn.setText("☀")
        else:
            self.title_bar.theme_btn.setText("🌙")
    
    def set_user_data(self, user_data: dict):
        """Ustaw dane zalogowanego użytkownika"""
        self.user_data = user_data
        logger.info(f"User data set: {user_data.get('email', 'Unknown')}")
        
        # Zaktualizuj UI z danymi użytkownika
        if hasattr(self, 'title_bar'):
            email = user_data.get('email', '')
            name = user_data.get('name', '')
            self.title_bar.user_btn.setToolTip(f"{name}\n{email}\nKliknij aby się wylogować")
        
        # NIE nadpisuj języka - używamy zapisanego w user_settings.json
        # Język jest już ustawiony w main.py przed utworzeniem okna
        # theme = user_data.get('theme', 'light')
    
    def _logout(self):
        """Wyloguj użytkownika"""
        from ..core.config import config
        import json
        
        logger.info("User logging out")
        
        # Usuń zapisane tokeny
        tokens_file = config.DATA_DIR / "tokens.json"
        if tokens_file.exists():
            tokens_file.unlink()
            logger.info("Tokens file deleted")
        
        # Zamknij główne okno
        self.close()
        
        # Pokaż okno logowania ponownie
        from .auth_window import AuthWindow
        auth_window = AuthWindow()
        auth_window.login_successful.connect(lambda user_data: (
            auth_window.close(),
            self.set_user_data(user_data),
            self.show()
        ))
        auth_window.show()
    
    def _on_theme_toggle(self):
        """Obsługa przełączania między układem 1 a 2"""
        from ..utils.theme_manager import get_theme_manager
        from ..core.config import save_settings
        
        theme_manager = get_theme_manager()
        new_layout = theme_manager.toggle_layout()
        
        # Zmień ikonę w zależności od układu
        if new_layout == 1:
            self.title_bar.theme_btn.setText("☀")
            logger.info("Switched to layout 1 (light mode)")
        else:
            self.title_bar.theme_btn.setText("🌙")
            logger.info("Switched to layout 2 (dark mode)")
        
        # Zapisz aktualny layout
        save_settings({'current_layout': new_layout})
    
    def _open_settings_tab(self, tab_index: int):
        """Otwórz widok ustawień na konkretnej karcie"""
        logger.info(f"Opening settings tab: {tab_index}")
        
        # Przełącz na widok ustawień
        self.content_stack.setCurrentWidget(self.settings_view)
        
        # Ustaw odpowiednią kartę
        self.settings_view.tabs.setCurrentIndex(tab_index)
        
        # Odznacz wszystkie przyciski nawigacji (ustawienia są teraz w menu)
        for btn in self.navigation_bar.buttons.values():
            btn.setChecked(False)
        
        # Ukryj quick input w ustawieniach
        self.quick_input.setVisible(False)
    
    def _show_help(self):
        """Pokaż okno pomocy"""
        logger.info("Help requested")
        # TODO: Implementacja okna pomocy
        from PyQt6.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            t('help.title'),
            t('help.coming_soon')
        )
    
    def _setup_window(self):
        """Konfiguracja okna"""
        self.setWindowTitle(config.WINDOW_TITLE)
        self.setMinimumSize(config.WINDOW_MIN_WIDTH, config.WINDOW_MIN_HEIGHT)
        self.resize(config.WINDOW_DEFAULT_WIDTH, config.WINDOW_DEFAULT_HEIGHT)
        
        # Usuń standardową ramkę Windows
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        # Włącz cień dla okna (Windows 10/11)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        # Centralny widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Główny layout
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # 0. Własny pasek tytułowy
        self.title_bar = CustomTitleBar(self)
        main_layout.addWidget(self.title_bar)
        
        # Podłącz sygnały paska tytułowego
        self.title_bar.logout_requested.connect(self._logout)
        self.title_bar.settings_tab_requested.connect(self._open_settings_tab)
        self.title_bar.help_requested.connect(self._show_help)
        self.title_bar.theme_btn.clicked.connect(self._on_theme_toggle)
        
        # Separator
        separator0 = QFrame()
        separator0.setFrameShape(QFrame.Shape.HLine)
        separator0.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator0)
        
        # 1. Sekcja górna - Nawigacja
        self.navigation_bar = NavigationBar()
        main_layout.addWidget(self.navigation_bar)
        
        # Separator
        separator1 = QFrame()
        separator1.setFrameShape(QFrame.Shape.HLine)
        separator1.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator1)
        
        # 2. Sekcja główna - Zmienna zawartość (StackedWidget)
        self.content_stack = QStackedWidget()
        
        # Główny widok (domyślny)
        self.main_content = MainContentArea()
        self.content_stack.addWidget(self.main_content)
        
        # Widok ustawień
        self.settings_view = SettingsView()
        self.content_stack.addWidget(self.settings_view)
        
        main_layout.addWidget(self.content_stack, stretch=1)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator2)
        
        # 3. Sekcja dolna - Szybkie wprowadzanie
        self.quick_input = QuickInputSection()
        main_layout.addWidget(self.quick_input)
        
        logger.info("Main window UI setup completed")
    
    def _connect_signals(self):
        """Połączenie sygnałów i slotów"""
        self.navigation_bar.view_changed.connect(self._on_view_changed)
        self.quick_input.task_added.connect(self._on_task_added)
        
        # Połącz sygnał zmiany języka
        get_i18n().language_changed.connect(self._on_language_changed)
    
    def _on_view_changed(self, view_name: str):
        """Obsługa zmiany widoku"""
        logger.info(f"View changed to: {view_name}")
        
        # Przełącz widok w zależności od wybranego przycisku
        if view_name == 'settings':
            self.content_stack.setCurrentWidget(self.settings_view)
            self.quick_input.setVisible(False)  # Ukryj quick input w ustawieniach
        else:
            self.content_stack.setCurrentWidget(self.main_content)
            self.quick_input.setVisible(True)  # Pokaż quick input w innych widokach
            # TODO: W przyszłości tutaj będziemy ładować odpowiednie moduły
    
    def _on_task_added(self, task_text: str):
        """Obsługa dodania nowego zadania"""
        logger.info(f"Task added: {task_text}")
        # TODO: Implementacja dodawania zadania do bazy
    
    def _on_language_changed(self, language_code: str):
        """Obsługa zmiany języka - odśwież wszystkie tłumaczenia"""
        logger.info(f"Refreshing UI translations for language: {language_code}")
        
        # Odśwież tytuł okna
        self.setWindowTitle(t('app.title'))
        
        # Odśwież komponenty
        self.title_bar.update_translations()
        self.navigation_bar.update_translations()
        self.main_content.management_bar.update_translations()
        self.main_content.data_area.update_translations()
        self.quick_input.update_translations()
        self.settings_view.update_translations()
        
        logger.info("UI translations refreshed successfully")
