"""
Main Window - Główne okno aplikacji
"""
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame,
    QLineEdit, QTableWidget, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QPoint, QTimer
from PyQt6.QtGui import QFont, QMouseEvent, QAction, QKeySequence, QShortcut
from loguru import logger

from ..utils.i18n_manager import t, get_i18n
from ..core.config import config
from .config_view import SettingsView
from .alarms_view import AlarmsView
from .pomodoro_view import PomodoroView
from .note_view import NoteView
from .callcryptor_view import CallCryptorView
from .status_led import StatusLED, get_status_led_manager
from .task_view import TaskView
from .task_config_dialog import TaskConfigDialog
from .kanban_view import KanBanView
from .task_bar import TaskBar
from .quick_task_bar import QuickTaskDialog
from ..Modules.habbit_tracker_module import HabbitTrackerView


class CustomTitleBar(QWidget):
    """Własny pasek tytułowy z przyciskami okna"""
    
    # Sygnały
    logout_requested = pyqtSignal()
    settings_tab_requested = pyqtSignal(int)  # index karty w ustawieniach
    help_requested = pyqtSignal()
    toggle_nav_requested = pyqtSignal()  # nowy signal do rozwijania nawigacji
    
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
        
        # === LEWA STRONA: Użytkownik + Motyw + Rozwiń nawigację ===
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
        
        # Przycisk rozwijania/zwijania nawigacji
        self.nav_toggle_btn = QPushButton("▼")
        self.nav_toggle_btn.setFixedSize(35, 35)
        self.nav_toggle_btn.setObjectName("navToggleButton")
        self.nav_toggle_btn.setToolTip(t('nav.show_more'))
        self.nav_toggle_btn.clicked.connect(self._on_nav_toggle)
        left_layout.addWidget(self.nav_toggle_btn)
        
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
        
        # === PRAWA STRONA: Status LED + Przyciski okna (Minimize/Maximize/Close) ===
        right_layout = QHBoxLayout()
        right_layout.setSpacing(0)
        
        # Status LED
        self.status_led = StatusLED()
        self.status_led.setFixedSize(25, 25)
        self.status_led.setToolTip("Status połączenia z bazą danych\nDwukrotne kliknięcie: otwórz konsolę sieciową")
        right_layout.addWidget(self.status_led)
        
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
            (t('user_menu.settings.callcryptor'), 4),
            (t('user_menu.settings.assistant'), 5),
            (t('user_menu.settings.ai'), 6),
            (t('user_menu.settings.email_accounts'), 7),
            (t('user_menu.settings.about'), 8),
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
    
    def _on_nav_toggle(self):
        """Przełącz widoczność drugiego rzędu nawigacji"""
        self.toggle_nav_requested.emit()
    
    def update_nav_toggle_button(self, is_visible: bool):
        """Zaktualizuj ikonę przycisku nawigacji"""
        if is_visible:
            self.nav_toggle_btn.setText("▲")
            self.nav_toggle_btn.setToolTip(t('nav.hide_more'))
        else:
            self.nav_toggle_btn.setText("▼")
            self.nav_toggle_btn.setToolTip(t('nav.show_more'))
    
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
        
        # Zaktualizuj tooltip przycisku nawigacji
        if hasattr(self, 'nav_toggle_btn'):
            # Sprawdź obecny stan z NavigationBar jeśli dostępny
            tooltip = t('nav.hide_more') if self.nav_toggle_btn.text() == "▲" else t('nav.show_more')
            self.nav_toggle_btn.setToolTip(tooltip)


class NavigationBar(QWidget):
    """Górny pasek nawigacyjny z przyciskami zmiany widoków"""
    
    view_changed = pyqtSignal(str)  # Signal emitowany przy zmianie widoku
    second_row_toggled = pyqtSignal(bool)  # Signal emitowany przy zmianie widoczności drugiego rzędu
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.second_row_visible = False
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu paska nawigacyjnego"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # ========== PIERWSZY RZĄD ==========
        first_row_container = QWidget()
        first_row_layout = QHBoxLayout(first_row_container)
        first_row_layout.setContentsMargins(0, 0, 0, 0)
        first_row_layout.setSpacing(2)
        
        # Lista przycisków nawigacyjnych - klucze dla i18n
        self.nav_keys = [
            'tasks',
            'kanban', 
            'pomodoro',
            'habit_tracker',
            'notes',
            'callcryptor',
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
            first_row_layout.addWidget(btn, stretch=1)  # Równomierne rozciąganie
            self.buttons[key] = btn
        
        main_layout.addWidget(first_row_container)
        
        # ========== DRUGI RZĄD (ukryty domyślnie) ==========
        self.second_row_container = QWidget()
        second_row_layout = QHBoxLayout(self.second_row_container)
        second_row_layout.setContentsMargins(0, 2, 0, 0)  # Mały margines góra
        second_row_layout.setSpacing(2)
        
        # 8 pustych przycisków w drugim rzędzie
        self.second_row_buttons = {}
        self.second_row_keys = []
        
        for i in range(8):
            key = f'custom_{i+1}'
            self.second_row_keys.append(key)
            btn = QPushButton(f"Blank {i+1}")  # Domyślna nazwa
            btn.setCheckable(True)
            btn.setMinimumHeight(40)
            btn.setObjectName("navButton")
            btn.clicked.connect(lambda checked, k=key: self._on_button_clicked(k))
            second_row_layout.addWidget(btn, stretch=1)
            self.second_row_buttons[key] = btn
        
        # Domyślnie ukryj drugi rząd
        self.second_row_container.setVisible(False)
        main_layout.addWidget(self.second_row_container)
        
        # Domyślnie zaznacz pierwszy przycisk
        self.buttons['tasks'].setChecked(True)
    
    def toggle_second_row(self):
        """Przełącz widoczność drugiego rzędu przycisków (publiczna metoda)"""
        self.second_row_visible = not self.second_row_visible
        self.second_row_container.setVisible(self.second_row_visible)
        
        # Emituj signal z nowym stanem
        self.second_row_toggled.emit(self.second_row_visible)
        
        logger.info(f"Second navigation row {'shown' if self.second_row_visible else 'hidden'}")
        
        return self.second_row_visible
    
    def _on_button_clicked(self, view_name: str):
        """Obsługa kliknięcia przycisku nawigacyjnego"""
        # Odznacz wszystkie przyciski z pierwszego rzędu
        for btn in self.buttons.values():
            btn.setChecked(False)
        
        # Odznacz wszystkie przyciski z drugiego rzędu
        for btn in self.second_row_buttons.values():
            btn.setChecked(False)
        
        # Zaznacz kliknięty przycisk
        if view_name in self.buttons:
            self.buttons[view_name].setChecked(True)
        elif view_name in self.second_row_buttons:
            self.second_row_buttons[view_name].setChecked(True)
        
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
            'callcryptor': t('nav.callcryptor'),
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
    
    def __init__(self, on_token_refreshed=None):
        super().__init__()
        self.user_data = None  # Dane zalogowanego użytkownika
        self.on_token_refreshed = on_token_refreshed  # Callback dla odświeżonych tokenów
        self._quick_add_shortcut: QShortcut | None = None
        
        # Inicjalizacja asystenta głosowego
        self._assistant_core = None
        self._assistant_watcher = None
        self._quick_task_watcher = None
        self._task_assistant_module = None
        
        self._setup_window()
        self._setup_ui()
        self._connect_signals()
        self._initialize_theme_icon()
        self._initialize_status_led()
        self._initialize_assistant()
    
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
    
    def _initialize_status_led(self):
        """Inicjalizuj Status LED Manager i podłącz do modułów"""
        # Pobierz singleton manager
        self.status_led_manager = get_status_led_manager()
        
        # Podłącz LED widget z title bar
        self.status_led_manager.set_led_widget(self.title_bar.status_led)
        
        # Ustaw początkowy status jako disconnected
        self.status_led_manager.set_status('disconnected')
        
        logger.info("Status LED Manager initialized")
    
    def set_user_data(self, user_data: dict):
        """Ustaw dane zalogowanego użytkownika"""
        self.user_data = user_data
        email = user_data.get('email', 'Unknown')
        logger.info(f"User data set: {email}")
        
        # Zaktualizuj UI z danymi użytkownika
        if hasattr(self, 'title_bar'):
            name = user_data.get('name', '')
            self.title_bar.user_btn.setToolTip(f"{name}\n{email}\nKliknij aby się wylogować")
        
        # Przekaż dane użytkownika do AlarmsView aby włączyć synchronizację
        if hasattr(self, 'alarms_view'):
            self.alarms_view.set_user_data(user_data, on_token_refreshed=self.on_token_refreshed)
            # Podłącz sygnały synchronizacji do Status LED
            self._connect_alarms_to_status_led()
        
        # Przekaż dane użytkownika do PomodoroView z callbackiem dla tokenów
        if hasattr(self, 'pomodoro_view'):
            self.pomodoro_view.set_user_data(user_data, on_token_refreshed=self.on_token_refreshed)
            # Podłącz sygnały synchronizacji do Status LED
            self._connect_pomodoro_to_status_led()
        
        # Przekaż dane użytkownika do NoteView aby włączyć synchronizację
        if hasattr(self, 'notes_view'):
            self.notes_view.set_user_data(user_data, on_token_refreshed=self.on_token_refreshed)
        
        # Przekaż dane użytkownika do CallCryptorView
        if hasattr(self, 'callcryptor_view'):
            self.callcryptor_view.set_user_data(user_data)
            logger.info("[MAIN] ✅ CallCryptor initialized")
        
        # Przekaż dane użytkownika do HabitTrackerView aby włączyć synchronizację
        if hasattr(self, 'habit_view'):
            self.habit_view.set_user_data(user_data)
            logger.info("[MAIN] ✅ Habit tracker synchronization enabled")
        
        # Przekaż dane użytkownika do TasksManager aby włączyć synchronizację
        if hasattr(self, 'tasks_manager'):
            self._enable_tasks_sync(user_data)
            # Podłącz sygnały synchronizacji do Status LED
            self._connect_tasks_to_status_led()
        
        # Przekaż dane użytkownika do Email Settings Card
        if hasattr(self, 'settings_view') and hasattr(self.settings_view, 'tab_email'):
            self.settings_view.tab_email.set_user_data(user_data)
            logger.info("[MAIN] ✅ Email settings initialized")
        
        # Status LED: user logged in, connected
        if hasattr(self, 'status_led_manager'):
            self.status_led_manager.set_status('connected_idle')
            self.status_led_manager._on_log_message(f"✓ User logged in: {email}")
        
        # NIE nadpisuj języka - używamy zapisanego w user_settings.json
        # Język jest już ustawiony w main.py przed utworzeniem okna
        # theme = user_data.get('theme', 'light')
    
    def _logout(self):
        """Wyloguj użytkownika"""
        from ..core.config import config
        import json
        
        logger.info("User logging out")
        
        # Cleanup TasksManager sync przed wylogowaniem
        if hasattr(self, 'tasks_manager') and self.tasks_manager:
            logger.info("Stopping tasks sync...")
            self.tasks_manager.cleanup()
        
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
        
        # 🎨 ODŚWIEŻ MOTYWY WSZYSTKICH WIDOKÓW
        # Upewnij się, że wszystkie widoki aktualizują swoje style
        self._refresh_all_views_theme()
        
        # Zapisz aktualny layout
        save_settings({'current_layout': new_layout})
    
    def _refresh_all_views_theme(self):
        """Odśwież motywy wszystkich widoków po zmianie motywu"""
        try:
            logger.info(f"🎨 [MAIN] _refresh_all_views_theme() called")
            
            # Notes View
            if hasattr(self, 'notes_view') and self.notes_view:
                logger.info(f"[MAIN] Found notes_view: {self.notes_view}")
                if hasattr(self.notes_view, 'apply_theme'):
                    logger.info(f"[MAIN] Calling notes_view.apply_theme()")
                    try:
                        self.notes_view.apply_theme()
                        logger.info(f"[MAIN] notes_view.apply_theme() completed successfully")
                    except Exception as e:
                        logger.error(f"[MAIN] Exception in notes_view.apply_theme(): {e}")
                        import traceback
                        logger.error(f"[MAIN] Traceback: {traceback.format_exc()}")
                    logger.debug("Refreshed notes_view theme")
                else:
                    logger.warning(f"[MAIN] notes_view has no apply_theme method!")
            else:
                logger.warning(f"[MAIN] notes_view not found! hasattr={hasattr(self, 'notes_view')}")
            
            # 🎨 Pomodoro View
            if hasattr(self, 'pomodoro_view') and self.pomodoro_view:
                if hasattr(self.pomodoro_view, 'apply_theme'):
                    self.pomodoro_view.apply_theme()
                    logger.debug("Refreshed pomodoro_view theme")
            
            # 🎨 Alarms View
            if hasattr(self, 'alarms_view') and self.alarms_view:
                if hasattr(self.alarms_view, 'apply_theme'):
                    self.alarms_view.apply_theme()
                    logger.debug("Refreshed alarms_view theme")
                    
            # 🎨 Settings View
            if hasattr(self, 'settings_view') and self.settings_view:
                if hasattr(self.settings_view, 'apply_theme'):
                    self.settings_view.apply_theme()
                    logger.debug("Refreshed settings_view theme")
            
            # 🎨 Habit Tracker View
            if hasattr(self, 'habit_view') and self.habit_view:
                if hasattr(self.habit_view, 'apply_theme'):
                    try:
                        self.habit_view.apply_theme()
                        logger.info("[MAIN] habit_view.apply_theme() completed successfully")
                    except Exception as e:
                        logger.error(f"[MAIN] Exception in habit_view.apply_theme(): {e}")
                        import traceback
                        logger.error(f"[MAIN] Traceback: {traceback.format_exc()}")
                    logger.debug("Refreshed habit_view theme")
                else:
                    logger.warning("[MAIN] habit_view has no apply_theme method!")
            else:
                logger.warning(f"[MAIN] habit_view not found! hasattr={hasattr(self, 'habit_view')}")
            
            # 🎨 CallCryptor View
            if hasattr(self, 'callcryptor_view') and self.callcryptor_view:
                if hasattr(self.callcryptor_view, 'apply_theme'):
                    try:
                        self.callcryptor_view.apply_theme()
                        logger.info("[MAIN] callcryptor_view.apply_theme() completed successfully")
                    except Exception as e:
                        logger.error(f"[MAIN] Exception in callcryptor_view.apply_theme(): {e}")
                        import traceback
                        logger.error(f"[MAIN] Traceback: {traceback.format_exc()}")
                    logger.debug("Refreshed callcryptor_view theme")
                else:
                    logger.warning("[MAIN] callcryptor_view has no apply_theme method!")
            else:
                logger.warning(f"[MAIN] callcryptor_view not found! hasattr={hasattr(self, 'callcryptor_view')}")
            
            if getattr(self, 'quick_task_dialog', None):
                self.quick_task_dialog.apply_theme()
                    
        except Exception as e:
            logger.error(f"Error refreshing view themes: {e}")
    
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
        self.title_bar.toggle_nav_requested.connect(self._on_nav_toggle)  # Nowe połączenie
        
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
        
        # Widok alarmów
        self.alarms_view = AlarmsView(get_i18n(), config.DATA_DIR)
        self.content_stack.addWidget(self.alarms_view)
        
        # Widok Pomodoro
        self.pomodoro_view = PomodoroView()
        self.content_stack.addWidget(self.pomodoro_view)
        
        # Widok Notatek
        self.notes_view = NoteView()
        self.content_stack.addWidget(self.notes_view)
        
        # Widok CallCryptor
        self.callcryptor_view = CallCryptorView(parent=self)
        self.content_stack.addWidget(self.callcryptor_view)
        
        # Widok Zadań (nasz nowy TaskView)
        try:
            # Import TasksManager (nowa wersja z sync) oraz backward-compatible TaskLogic
            from ..Modules.task_module.task_logic import TasksManager, TaskLogic
            from ..Modules.task_module.task_local_database import TaskLocalDatabase
            
            # Utwórz ścieżkę do bazy danych zadań
            db_dir = Path(__file__).parent.parent / 'database'
            db_dir.mkdir(exist_ok=True)
            
            # DELAY: Nie inicjalizuj TasksManager tutaj - zostanie utworzony w set_user_data()
            # Tymczasowo ustaw None - TaskView obsłuży brak task_logic
            self.tasks_manager = None
            self.task_logic = None
            self.task_local_db = None
            
            # Utwórz TaskView bez task_logic (zostanie ustawiony w set_user_data)
            self.task_view = TaskView(task_logic=None, local_db=None)
            
            # Przekaż alarm_manager do TaskView
            if hasattr(self, 'alarms_view') and hasattr(self.alarms_view, 'alarm_manager'):
                logger.info(f"[MainWindow] Passing alarm_manager to TaskView: {self.alarms_view.alarm_manager}")
                self.task_view.set_alarm_manager(self.alarms_view.alarm_manager)
            else:
                logger.warning("[MainWindow] Could not pass alarm_manager to TaskView - alarms_view not ready")
            
            # pozwól TaskView zgłaszać prośbę o konfigurację
            self.task_view.on_configure = lambda: self._open_task_config_dialog()
            self.content_stack.addWidget(self.task_view)
            
            # Widok KanBan - używa tej samej logiki i bazy co TaskView
            self.kanban_view = KanBanView()
            self.kanban_view.set_task_logic(self.task_logic)
            # Zapewnij obsługę notatek i podzadań zgodną z TaskView
            self.kanban_view.open_task_note = lambda task_id: self._handle_note_button_click(task_id)
            self.kanban_view.add_subtask = lambda parent_id: self._handle_add_subtask(parent_id)
            self.content_stack.addWidget(self.kanban_view)
            
            # Połącz sygnały między widokami
            # Gdy zadanie zostanie przeniesione w KanBan, odśwież widok zadań
            self.kanban_view.task_moved.connect(lambda: self.task_view.refresh_tasks())
            
            # Podmień metodę open_task_note aby obsługiwała integrację z notatkami
            self.task_view.open_task_note = lambda task_id: self._handle_note_button_click(task_id)
            
            # Podmień metodę _add_subtask_dialog aby obsługiwała dodawanie subtasków
            self.task_view._add_subtask_dialog = lambda parent_id: self._handle_add_subtask(parent_id)
            
            # TasksManager zostanie zainicjalizowany w set_user_data()
            logger.info("TaskView initialized (TasksManager will be set after login)")
        except Exception as e:
            logger.error(f"Failed to initialize TaskView: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.task_view = None
            self.kanban_view = None
            self.task_local_db = None
            self.task_logic = None
        
        # Widok Habit Tracker
        try:
            from ..Modules.habbit_tracker_module.habit_database import HabitDatabase
            
            # Utwórz ścieżkę do bazy danych habit tracker
            db_dir = Path(__file__).parent.parent / 'database'
            db_dir.mkdir(exist_ok=True)
            habit_db_path = db_dir / 'habit_tracker.db'
            
            # Utwórz bazę danych nawyków (user_id będzie ustawiony w set_user_data)
            self.habit_db = HabitDatabase(habit_db_path, user_id=1)
            
            # Utwórz HabbitTrackerView z bazą danych
            self.habit_view = HabbitTrackerView(db_manager=self.habit_db)
            self.content_stack.addWidget(self.habit_view)
            
            logger.info("HabbitTrackerView initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize HabbitTrackerView: {e}")
            import traceback
            logger.error(traceback.format_exc())
            self.habit_view = None
            self.habit_db = None
        
        main_layout.addWidget(self.content_stack, stretch=1)
        
        # Separator
        separator2 = QFrame()
        separator2.setFrameShape(QFrame.Shape.HLine)
        separator2.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator2)
        
        # 3. Sekcja dolna - Szybkie wprowadzanie
        task_logic_ref = getattr(self, 'task_logic', None)
        local_db_ref = getattr(self, 'task_local_db', None)
        self.quick_input = TaskBar(task_logic=task_logic_ref, local_db=local_db_ref)
        main_layout.addWidget(self.quick_input)

        try:
            self.quick_task_dialog = QuickTaskDialog(
                task_logic=task_logic_ref,
                local_db=local_db_ref,
                parent=self,
            )
            self.quick_task_dialog.task_bar.task_added.connect(self._on_task_added)
            self.quick_task_dialog.task_bar.note_requested.connect(self._on_quick_note_requested)
        except Exception as exc:  # pragma: no cover - defensive logging
            self.quick_task_dialog = None
            logger.error(f"Failed to initialize QuickTaskDialog: {exc}")

        self._install_quick_add_shortcut(config.SHORTCUT_QUICK_ADD)
        
        logger.info("Main window UI setup completed")

        QTimer.singleShot(0, self._select_default_view)
    
    def _connect_signals(self):
        """Połączenie sygnałów i slotów"""
        self.navigation_bar.view_changed.connect(self._on_view_changed)
        self.navigation_bar.second_row_toggled.connect(self._on_nav_row_toggled)  # Nowe połączenie
        self.quick_input.task_added.connect(self._on_task_added)
        self.quick_input.note_requested.connect(self._on_quick_note_requested)
        if hasattr(self.settings_view, 'tab_general'):
            self.settings_view.tab_general.settings_changed.connect(self._on_settings_updated)
        
        # Połącz sygnał zmiany języka
        get_i18n().language_changed.connect(self._on_language_changed)

    def _install_quick_add_shortcut(self, shortcut_text: str) -> None:
        sequence_text = (shortcut_text or "").strip()
        if not sequence_text:
            return

        sequence = QKeySequence(sequence_text)
        if sequence == QKeySequence():
            logger.warning(f"[MainWindow] Ignoring invalid quick add shortcut: '{shortcut_text}'")
            return

        if self._quick_add_shortcut is None:
            self._quick_add_shortcut = QShortcut(sequence, self)
            self._quick_add_shortcut.setContext(Qt.ShortcutContext.ApplicationShortcut)
            self._quick_add_shortcut.activated.connect(self._show_quick_add_dialog)
        else:
            self._quick_add_shortcut.setKey(sequence)
        logger.info(f"[MainWindow] Quick add shortcut set to: {sequence.toString()}")

    def _show_quick_add_dialog(self) -> None:
        if not getattr(self, 'quick_task_dialog', None):
            logger.warning("[MainWindow] QuickTaskDialog is not available")
            return

        self.quick_task_dialog.clear_inputs()
        self.quick_task_dialog.reload_configuration()
        self.quick_task_dialog.apply_theme()
        self.quick_task_dialog.update_translations()
        self.quick_task_dialog.show()
        self.quick_task_dialog.raise_()
        self.quick_task_dialog.activateWindow()

    def _on_settings_updated(self, changes: dict) -> None:
        if not isinstance(changes, dict):
            return
        shortcut = changes.get('shortcut_quick_add')
        if shortcut is not None:
            self._install_quick_add_shortcut(shortcut)

    def _select_default_view(self) -> None:
        """Ustaw domyślny widok na listę zadań po starcie aplikacji."""
        try:
            if hasattr(self, "navigation_bar") and "tasks" in getattr(self.navigation_bar, "buttons", {}):
                self.navigation_bar.buttons["tasks"].setChecked(True)
            self._on_view_changed("tasks")
        except Exception as exc:  # pragma: no cover - log only
            logger.error(f"[MainWindow] Failed to select default view: {exc}")
    
    def _on_nav_toggle(self):
        """Obsługa kliknięcia przycisku rozwijania nawigacji"""
        is_visible = self.navigation_bar.toggle_second_row()
        self.title_bar.update_nav_toggle_button(is_visible)
    
    def _on_nav_row_toggled(self, is_visible: bool):
        """Obsługa zmiany widoczności drugiego rzędu (z NavigationBar)"""
        self.title_bar.update_nav_toggle_button(is_visible)
    
    def _on_view_changed(self, view_name: str):
        """Obsługa zmiany widoku"""
        logger.info(f"View changed to: {view_name}")
        
        # Przełącz widok w zależności od wybranego przycisku
        if view_name == 'settings':
            self.content_stack.setCurrentWidget(self.settings_view)
            self.quick_input.setVisible(False)  # Ukryj quick input tylko w ustawieniach
        elif view_name == 'alarms':
            self.content_stack.setCurrentWidget(self.alarms_view)
            self.quick_input.setVisible(True)  # Pokaż quick input w alarmach
        elif view_name == 'pomodoro':
            self.content_stack.setCurrentWidget(self.pomodoro_view)
            self.quick_input.setVisible(True)  # Pokaż quick input w pomodoro
        elif view_name == 'notes':
            self.content_stack.setCurrentWidget(self.notes_view)
            self.quick_input.setVisible(True)  # Pokaż quick input w notatkach
        elif view_name == 'callcryptor':
            if hasattr(self, 'callcryptor_view') and self.callcryptor_view:
                self.content_stack.setCurrentWidget(self.callcryptor_view)
                self.quick_input.setVisible(True)  # Pokaż quick input w CallCryptor
            else:
                logger.warning("CallCryptorView not initialized")
                self.content_stack.setCurrentWidget(self.main_content)
                self.quick_input.setVisible(True)
        elif view_name == 'tasks':
            if hasattr(self, 'task_view') and self.task_view:
                self.content_stack.setCurrentWidget(self.task_view)
                self.quick_input.setVisible(True)
            else:
                logger.warning("TaskView not initialized")
                self.content_stack.setCurrentWidget(self.main_content)
                self.quick_input.setVisible(True)
        elif view_name == 'kanban':
            if hasattr(self, 'kanban_view') and self.kanban_view:
                self.content_stack.setCurrentWidget(self.kanban_view)
                self.quick_input.setVisible(True)
                # Odśwież tablicę KanBan przy każdym wejściu
                self.kanban_view.refresh_board()
            else:
                logger.warning("KanBanView not initialized")
                self.content_stack.setCurrentWidget(self.main_content)
                self.quick_input.setVisible(True)
        elif view_name == 'habit_tracker':
            if hasattr(self, 'habit_view') and self.habit_view:
                self.content_stack.setCurrentWidget(self.habit_view)
                self.quick_input.setVisible(True)
                # Odśwież widok nawyków przy każdym wejściu
                self.habit_view.refresh_table()
            else:
                logger.warning("HabbitTrackerView not initialized")
                self.content_stack.setCurrentWidget(self.main_content)
                self.quick_input.setVisible(True)
        else:
            self.content_stack.setCurrentWidget(self.main_content)
            self.quick_input.setVisible(True)  # Pokaż quick input w innych widokach
            # TODO: W przyszłości tutaj będziemy ładować odpowiednie moduły
    
    def _on_task_added(self, payload: dict):
        """Obsługuje dodanie zadania z paska szybkiego wprowadzania."""
        if not isinstance(payload, dict):
            logger.warning(f"[MainWindow] Ignoring malformed quick task payload: {payload}")
            return

        title = str(payload.get('title', '')).strip()
        if not title:
            return

        if not getattr(self, 'task_logic', None):
            logger.warning("[MainWindow] Cannot add task – task logic not ready")
            return
        
        # TasksManager ma local_db, TaskLogic (legacy) ma db
        has_db = getattr(self.task_logic, 'local_db', None) or getattr(self.task_logic, 'db', None)
        if not has_db:
            logger.warning("[MainWindow] Cannot add task – database not ready")
            return

        source = self.sender()
        source_task_bar = source if isinstance(source, TaskBar) else None
        checkbox_selected = source_task_bar.is_kanban_selected() if source_task_bar else False
        quick_dialog_bar = getattr(getattr(self, 'quick_task_dialog', None), 'task_bar', None)

        add_to_kanban = bool(payload.get('add_to_kanban'))
        task_data = dict(payload)
        task_data.pop('add_to_kanban', None)

        new_task = self.task_logic.add_task(task_data)
        if not new_task:
            logger.error(f"[MainWindow] Failed to add quick task: {title}")
            return

        task_id = new_task.get('id')
        logger.debug(f"[MainWindow] Task added with id={task_id}, add_to_kanban={add_to_kanban}, checkbox_selected={checkbox_selected}")
        
        task_view = getattr(self, 'task_view', None)
        if task_view:
            task_view.refresh_tasks()
            should_send_to_kanban = add_to_kanban or checkbox_selected
            logger.debug(f"[MainWindow] should_send_to_kanban={should_send_to_kanban}")
            if should_send_to_kanban and task_id:
                try:
                    logger.info(f"[MainWindow] Sending task {task_id} to KanBan...")
                    task_view._on_add_to_kanban(task_id)
                except Exception as exc:
                    logger.error(f"[MainWindow] Failed to send task {task_id} to KanBan: {exc}")

        if source_task_bar:
            source_task_bar.clear_inputs()
        else:
            self.quick_input.clear_inputs()

        if quick_dialog_bar and source_task_bar is quick_dialog_bar:
            self.quick_task_dialog.hide()
        logger.info(f"[MainWindow] Quick task added with id {task_id}")

    def _on_quick_note_requested(self, note_title: str):
        """Tworzy nową notatkę i przełącza widok, gdy użytkownik wybierze przycisk notatki."""
        source = self.sender()
        source_task_bar = source if isinstance(source, TaskBar) else None
        quick_dialog_bar = getattr(getattr(self, 'quick_task_dialog', None), 'task_bar', None)
        if not getattr(self, 'notes_view', None):
            logger.warning("[MainWindow] Notes view not initialized; cannot create quick note")
            return

        title = note_title.strip() or t('notes.quick_note_default', 'Szybka notatka')
        content = "<p></p>"
        try:
            note_id = self.notes_view.db.create_note(title=title, content=content, color="#2196F3")
        except Exception as exc:
            logger.error(f"[MainWindow] Failed to create quick note: {exc}")
            return

        if source_task_bar:
            source_task_bar.clear_inputs()
        else:
            self.quick_input.clear_inputs()
        if quick_dialog_bar and source_task_bar is quick_dialog_bar:
            self.quick_task_dialog.hide()
        self._on_view_changed("notes")
        self.notes_view.refresh_tree()
        QTimer.singleShot(150, lambda: self.notes_view.select_note_in_tree(note_id))
        logger.info(f"[MainWindow] Quick note created with id {note_id}")
    
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
        self.alarms_view.update_translations()
        if getattr(self, 'quick_task_dialog', None):
            self.quick_task_dialog.update_translations()
        
        # Odśwież widok Pomodoro jeśli istnieje
        if hasattr(self, 'pomodoro_view'):
            # PomodoroView nie ma jeszcze update_translations, ale ma _t() dla runtime
            pass
        
        logger.info("UI translations refreshed successfully")
    
    def _connect_alarms_to_status_led(self):
        """Podłącz sygnały modułu Alarms do Status LED"""
        try:
            # Alarms logic jest w alarms_view.logic
            if hasattr(self.alarms_view, 'logic') and self.alarms_view.logic:
                logic = self.alarms_view.logic
                
                # Podłącz do sync manager jeśli istnieje
                if hasattr(logic, 'sync_manager') and logic.sync_manager:
                    sync_mgr = logic.sync_manager
                    
                    # Symuluj podłączenie do eventów synchronizacji
                    # Ponieważ SyncManager nie ma gotowych sygnałów, będziemy monitorować w NetworkMonitor
                    logger.info("Alarms module connected to Status LED monitoring")
                else:
                    logger.warning("Alarms sync_manager not found")
        except Exception as e:
            logger.error(f"Failed to connect Alarms to Status LED: {e}")
    
    def _connect_pomodoro_to_status_led(self):
        """Podłącz sygnały modułu Pomodoro do Status LED"""
        try:
            # Pomodoro logic jest w pomodoro_view.logic
            if hasattr(self.pomodoro_view, 'logic') and self.pomodoro_view.logic:
                logic = self.pomodoro_view.logic
                
                # Podłącz do sync manager jeśli istnieje
                if hasattr(logic, 'sync_manager') and logic.sync_manager:
                    sync_mgr = logic.sync_manager
                    
                    # Symuluj podłączenie do eventów synchronizacji
                    logger.info("Pomodoro module connected to Status LED monitoring")
                else:
                    logger.warning("Pomodoro sync_manager not found")
        except Exception as e:
            logger.error(f"Failed to connect Pomodoro to Status LED: {e}")
    
    def _enable_tasks_sync(self, user_data: dict):
        """
        Włącz synchronizację dla modułu Tasks.
        Tworzy TasksManager z prawdziwym user_id i włączoną synchronizacją.
        
        Args:
            user_data: Słownik z danymi użytkownika (id/user_id, email, access_token, refresh_token)
        """
        try:
            # Pobierz dane do synchronizacji
            user_id = user_data.get('user_id') or user_data.get('id')
            access_token = user_data.get('access_token')
            refresh_token = user_data.get('refresh_token')
            
            if not user_id or not access_token:
                logger.warning("Cannot enable tasks sync: missing user_id or access_token")
                return
            
            # Jeśli TasksManager już istnieje i ma sync włączony, zatrzymaj go
            if hasattr(self, 'tasks_manager') and self.tasks_manager and self.tasks_manager.enable_sync:
                logger.info("Stopping previous tasks sync...")
                self.tasks_manager.cleanup()
            
            # Przygotuj ścieżkę do bazy danych
            from ..Modules.task_module.task_logic import TasksManager
            from pathlib import Path
            
            db_dir = Path(__file__).parent.parent / 'database'
            db_dir.mkdir(exist_ok=True)
            
            # Stwórz nowy TasksManager z user_id i synchronizacją
            logger.info(f"Creating TasksManager for user_id={user_id}")
            self.tasks_manager = TasksManager(
                data_dir=db_dir,
                user_id=str(user_id),
                api_base_url="http://127.0.0.1:8000",  # TODO: z configu
                auth_token=access_token,
                refresh_token=refresh_token,
                on_token_refreshed=self.on_token_refreshed,
                enable_sync=True
            )
            
            # Ustaw callbacks dla real-time updates
            self.tasks_manager.on_tasks_changed = self._on_tasks_updated
            self.tasks_manager.on_sync_complete = self._on_tasks_sync_complete
            
            # Zaktualizuj referencje
            self.task_logic = self.tasks_manager  # Backward compatibility
            self.task_local_db = self.tasks_manager.local_db
            
            # Zaktualizuj task_view z nowym manager (używamy set_task_logic dla pełnej inicjalizacji)
            if hasattr(self, 'task_view') and self.task_view:
                self.task_view.set_task_logic(self.task_logic, self.task_local_db)
                
                # Pokaż przycisk synchronizacji
                if hasattr(self.task_view, 'sync_btn'):
                    self.task_view.sync_btn.setVisible(True)
                    logger.info("[TaskView] Sync button enabled")
            
            # Zaktualizuj kanban_view z nowym manager
            if hasattr(self, 'kanban_view') and self.kanban_view:
                self.kanban_view.set_task_logic(self.task_logic)
            
            # FIXED: Zaktualizuj quick_input używając set_data_sources() (przeładowuje konfigurację)
            if hasattr(self, 'quick_input') and self.quick_input:
                self.quick_input.set_data_sources(
                    task_logic=self.task_logic, 
                    local_db=self.task_local_db
                )
                logger.info("[TaskBar] Data sources updated and configuration reloaded")
            
            logger.info(f"✅ Tasks sync enabled for user: {user_data.get('email')}")
            
        except Exception as e:
            logger.error(f"Failed to enable tasks sync: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def _connect_tasks_to_status_led(self):
        """Podłącz sygnały modułu Tasks do Status LED"""
        try:
            if hasattr(self, 'tasks_manager') and self.tasks_manager:
                # Podłącz do sync manager jeśli istnieje
                if hasattr(self.tasks_manager, 'sync_manager') and self.tasks_manager.sync_manager:
                    sync_mgr = self.tasks_manager.sync_manager
                    logger.info("Tasks module connected to Status LED monitoring")
                else:
                    logger.warning("Tasks sync_manager not found")
        except Exception as e:
            logger.error(f"Failed to connect Tasks to Status LED: {e}")
    
    def _on_tasks_updated(self):
        """Callback wywoływany gdy zadania zostały zaktualizowane przez WebSocket"""
        logger.info("Tasks updated via WebSocket")
        if hasattr(self, 'task_view') and self.task_view:
            self.task_view.refresh_tasks()
        if hasattr(self, 'kanban_view') and self.kanban_view:
            self.kanban_view.refresh_board()
    
    def _on_tasks_sync_complete(self):
        """Callback wywoływany po zakończeniu synchronizacji zadań"""
        logger.debug("Tasks sync complete")
        # Opcjonalnie: pokazać notyfikację lub zaktualizować status

    
    def _open_task_config_dialog(self):
        """Otwórz dialog konfiguracji zadania"""
        try:
            import traceback
            
            # Przekaż local_db do dialogu
            local_db = getattr(self, 'task_local_db', None)
            dialog = TaskConfigDialog(self, local_db=local_db)
            result = dialog.exec()
            
            # Po zamknięciu dialogu (niezależnie od Save/Cancel), odśwież widok zadań
            # gdyż konfiguracja kolumn mogła się zmienić
            if hasattr(self, 'task_view') and self.task_view:
                try:
                    self.task_view.refresh_columns()
                    logger.info("Task view columns refreshed after config dialog")
                except Exception as e:
                    logger.error(f"Failed to refresh task view columns: {e}")

            if hasattr(self, 'quick_input') and self.quick_input:
                try:
                    self.quick_input.reload_configuration()
                    logger.info("Quick input bar reloaded after config dialog")
                except Exception as exc:
                    logger.error(f"Failed to reload quick input bar: {exc}")
            if getattr(self, 'quick_task_dialog', None):
                try:
                    self.quick_task_dialog.reload_configuration()
                    logger.info("Quick add dialog reloaded after config dialog")
                except Exception as exc:
                    logger.error(f"Failed to reload quick-add dialog: {exc}")
            
            if result:
                # Użytkownik kliknął Save
                config_data = dialog.get_config()
                logger.info(f"Task config saved: {len(config_data.get('columns', []))} columns, "
                           f"{len(config_data.get('tags', []))} tags, "
                           f"{len(config_data.get('custom_lists', []))} lists")
                
                # Dodaj zadanie przez logic (jeśli konfiguracja zawiera dane zadania)
                if hasattr(self, 'task_logic') and self.task_logic and 'title' in config_data:
                    import datetime
                    task = {
                        'title': config_data.get('title', ''),
                        'status': config_data.get('status', 'Nowe'),
                        'tags': config_data.get('tags', ''),
                        'created_at': datetime.date.today().isoformat()
                    }
                    self.task_logic.add_task(task)
                    
                    # Odśwież tabelę w task_view (dane, nie kolumny - już odświeżone wyżej)
                    if hasattr(self, 'task_view') and self.task_view:
                        self.task_view.populate_table()
        except Exception as e:
            import traceback
            logger.error(f"Failed to open task config dialog: {e}")
            logger.error(traceback.format_exc())

    def _handle_note_button_click(self, task_id: int):
        """Obsługuje kliknięcie przycisku notatki - główna logika integracji zadań z notatkami
        
        Args:
            task_id: ID zadania dla którego obsługujemy notatkę
        """
        try:
            if not self.task_logic or not self.task_logic.db:
                logger.error("[MainWindow] No database connection available for notes")
                return
            
            if not hasattr(self, 'notes_view') or not self.notes_view:
                logger.error("[MainWindow] Notes view not initialized")
                return
            
            # Pobierz dane zadania
            tasks = self.task_logic.db.get_tasks()
            task = next((t for t in tasks if t.get('id') == task_id), None)
            
            if not task:
                logger.error(f"[MainWindow] Task {task_id} not found")
                return
            
            task_title = task.get('title', f'Zadanie {task_id}')
            note_id = task.get('note_id')
            
            if note_id:
                # SCENARIUSZ 1: Notatka już istnieje - otwórz ją
                logger.info(f"[MainWindow] Opening existing note {note_id} for task {task_id}")
                self._on_view_changed("notes")
                
                # Wybierz notatkę w drzewie po przełączeniu widoku
                QTimer.singleShot(100, lambda: self.notes_view.select_note_in_tree(str(note_id)))
            else:
                # SCENARIUSZ 2: Utwórz nową notatkę
                logger.info(f"[MainWindow] Creating new note for task {task_id}: {task_title}")
                from datetime import datetime
                
                # Utwórz notatkę w bazie danych notatek
                note_title = f"Notatka - {task_title}"
                note_content = (
                    f"<p><strong>Notatka do zadania:</strong> {task_title}</p>"
                    f"<p><em>Data utworzenia: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</em></p>"
                    f"<p><br></p>"
                )
                
                # Użyj bazy danych z notes_view
                new_note_id = self.notes_view.db.create_note(
                    title=note_title,
                    content=note_content,
                    color="#2196F3"  # Niebieski kolor dla notatek z zadań
                )
                
                if new_note_id:
                    # Połącz zadanie z notatką
                    self.task_logic.db.update_task(task_id, note_id=new_note_id)
                    logger.info(f"[MainWindow] Created note {new_note_id} and linked to task {task_id}")
                    
                    # Przełącz na widok notatek
                    self._on_view_changed("notes")
                    
                    # Odśwież drzewo notatek i wybierz nową notatkę
                    def open_new_note():
                        self.notes_view.refresh_tree()
                        self.notes_view.select_note_in_tree(str(new_note_id))
                    
                    QTimer.singleShot(100, open_new_note)
                    
                    # Odśwież widok zadań aby zaktualizować kolor przycisku (niebieski → zielony)
                    if hasattr(self, 'task_view') and self.task_view:
                        QTimer.singleShot(200, self.task_view.populate_table)
                else:
                    logger.error("[MainWindow] Failed to create note in database")
                
        except Exception as e:
            logger.error(f"[MainWindow] Error handling note button click: {e}")
            import traceback
            traceback.print_exc()
    
    def _handle_add_subtask(self, parent_id: int):
        """Obsługuje dodawanie subtaska do zadania
        
        Args:
            parent_id: ID zadania nadrzędnego
        """
        from PyQt6.QtWidgets import QInputDialog
        
        try:
            if not self.task_logic or not self.task_logic.db:
                logger.error("[MainWindow] No database connection available for subtasks")
                return
            
            # Pobierz dane zadania nadrzędnego
            tasks = self.task_logic.db.get_tasks()
            parent_task = next((t for t in tasks if t.get('id') == parent_id), None)
            
            if not parent_task:
                logger.error(f"[MainWindow] Parent task {parent_id} not found")
                return
            
            parent_title = parent_task.get('title', f'Zadanie {parent_id}')
            
            # Dialog wprowadzania tytułu subtaska
            subtask_title, ok = QInputDialog.getText(
                self,
                "Dodaj subtask",
                f"Wprowadź tytuł subtaska dla zadania:\n{parent_title}",
                text=""
            )
            
            if ok and subtask_title.strip():
                # Utwórz subtask w bazie danych
                logger.info(f"[MainWindow] Creating subtask '{subtask_title}' for parent task {parent_id}")
                
                subtask_id = self.task_logic.db.add_task(
                    title=subtask_title.strip(),
                    parent_id=parent_id
                )
                
                if subtask_id:
                    logger.info(f"[MainWindow] Subtask {subtask_id} created successfully")
                    
                    # Odśwież widok zadań
                    if hasattr(self, 'task_view') and self.task_view:
                        self.task_view.populate_table()
                        
                        # Automatycznie rozwiń subtaski dla tego zadania
                        # Znajdź wiersz zadania nadrzędnego w tabeli
                        for row in range(self.task_view.table.rowCount()):
                            # Pobierz ID zadania z pierwszej kolumny (zakładając że tam jest)
                            # lub użyj innego sposobu identyfikacji wiersza
                            pass  # TODO: Lepszy mechanizm identyfikacji wiersza
                        
                        # Na razie po prostu odśwież tabelę
                        # Przycisk subtasków zmieni kolor na zielony
                else:
                    logger.error("[MainWindow] Failed to create subtask in database")
            
        except Exception as e:
            logger.error(f"[MainWindow] Error handling add subtask: {e}")
            import traceback
            traceback.print_exc()
    
    def closeEvent(self, event):
        """Obsługa zamknięcia okna - cleanup zasobów"""
        logger.info("MainWindow closing - cleaning up resources...")
        
        try:
            # Cleanup TasksManager (stop sync workers, WebSocket)
            if hasattr(self, 'tasks_manager') and self.tasks_manager:
                logger.info("Cleaning up TasksManager...")
                self.tasks_manager.cleanup()
            
            # Cleanup AlarmManager (jeśli ma cleanup)
            if hasattr(self, 'alarms_view') and hasattr(self.alarms_view, 'alarm_manager'):
                if hasattr(self.alarms_view.alarm_manager, 'cleanup'):
                    logger.info("Cleaning up AlarmManager...")
                    self.alarms_view.alarm_manager.cleanup()
            
            logger.info("Cleanup complete")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
        
        # Wywołaj oryginalny closeEvent
        super().closeEvent(event)
    
    # =========================================================================
    # ASSISTANT INTEGRATION
    # =========================================================================
    def _initialize_assistant(self) -> None:
        """Inicjalizuj system asystenta głosowego."""
        try:
            logger.info("[MainWindow] Initializing voice assistant...")
            
            from ..core.assisstant.assistant_core import AssistantCore
            from ..core.assisstant.assistant_database import AssistantDatabase
            from ..core.assisstant.modules.task_assist import TaskAssistantModule
            from ..core.assisstant.input_watcher import AssistantInputWatcher
            
            logger.info("[MainWindow] Assistant imports successful")
            
            # Utwórz bazę danych asystenta
            db_path = config.DATA_DIR / "assistant.db"
            logger.info(f"[MainWindow] Creating assistant database at: {db_path}")
            
            assistant_db = AssistantDatabase(db_path=str(db_path))
            assistant_db.init_default_phrases()
            
            logger.info("[MainWindow] Assistant database initialized")
            
            # Utwórz rdzeń asystenta
            self._assistant_core = AssistantCore(
                database=assistant_db,
                language_provider=lambda: get_i18n().get_current_language(),
            )
            
            logger.info("[MainWindow] Assistant core created")
            
            # Załaduj frazy do cache
            self._assistant_core.refresh_cache()
            
            logger.info("[MainWindow] Phrases cache refreshed")
            
            # Utwórz moduł asystenta zadań
            self._task_assistant_module = TaskAssistantModule(task_controller=self)
            
            logger.info("[MainWindow] Task assistant module created")
            
            # Zarejestruj moduł w rdzeniu asystenta
            self._assistant_core.register_module(self._task_assistant_module)
            
            logger.info("[MainWindow] Task module registered in core")
            
            # Utwórz i zarejestruj moduł asystenta kanban
            from ..core.assisstant.modules.kanban_assist import KanbanAssistantModule
            
            self._kanban_assistant_module = KanbanAssistantModule(kanban_controller=self)
            self._assistant_core.register_module(self._kanban_assistant_module)
            
            logger.info("[MainWindow] Kanban module registered in core")
            
            # Utwórz i zarejestruj moduł asystenta pomodoro
            from ..core.assisstant.modules.pomodoro_assist import PomodoroAssistantModule
            
            self._pomodoro_assistant_module = PomodoroAssistantModule(pomodoro_controller=self.pomodoro_view)
            self._assistant_core.register_module(self._pomodoro_assistant_module)
            
            logger.info("[MainWindow] Pomodoro module registered in core")
            
            # Podłącz watcher do pola quick input (dolny pasek)
            if hasattr(self, 'quick_input'):
                logger.info("[MainWindow] quick_input found, checking task_input...")
                
                if hasattr(self.quick_input, 'task_input'):
                    logger.info("[MainWindow] task_input found, creating watcher...")
                    
                    self._assistant_watcher = AssistantInputWatcher(
                        line_edit=self.quick_input.task_input,
                        assistant=self._assistant_core,
                        debounce_ms=1200,
                        context_name="quick_task_bar",
                    )
                    logger.info("[MainWindow] Assistant watcher attached to quick_input")
                else:
                    logger.warning("[MainWindow] quick_input.task_input not found!")
            else:
                logger.warning("[MainWindow] quick_input not found!")
            
            # Podłącz watcher do QuickTaskDialog (floating window)
            if hasattr(self, 'quick_task_dialog') and self.quick_task_dialog:
                logger.info("[MainWindow] quick_task_dialog found, checking task_bar...")
                
                if hasattr(self.quick_task_dialog, 'task_bar') and hasattr(self.quick_task_dialog.task_bar, 'task_input'):
                    logger.info("[MainWindow] task_bar.task_input found, creating watcher...")
                    
                    self._quick_task_watcher = AssistantInputWatcher(
                        line_edit=self.quick_task_dialog.task_bar.task_input,
                        assistant=self._assistant_core,
                        debounce_ms=1200,
                        context_name="floating_quick_task",
                    )
                    logger.info("[MainWindow] Assistant watcher attached to QuickTaskDialog")
                else:
                    logger.warning("[MainWindow] quick_task_dialog.task_bar.task_input not found!")
            else:
                logger.warning("[MainWindow] quick_task_dialog not available!")
            
            logger.success("[MainWindow] Voice assistant initialized successfully")
            
        except Exception as exc:
            logger.error(f"[MainWindow] Failed to initialize assistant: {exc}")
            import traceback
            logger.error(traceback.format_exc())
    
    def handle_assistant_task_create(self, command, title: str) -> None:
        """
        Obsługuje tworzenie zadania przez asystenta głosowego.
        
        Args:
            command: Sparsowana komenda ParsedCommand
            title: Tytuł zadania
        """
        if not title:
            logger.warning("[MainWindow] Assistant create task: empty title")
            return
        
        # Deleguj do istniejącej logiki dodawania zadań
        payload = {"title": title}
        self._on_task_added(payload)
        
        logger.success(f"[MainWindow] Assistant created task: '{title}'")
    
    # ======================================================================
    # Assistant - Kanban handlers
    # ======================================================================
    
    def handle_assistant_kanban_open(self, command) -> None:
        """
        Otwiera widok kanban przez asystenta głosowego.
        
        Args:
            command: Sparsowana komenda ParsedCommand
        """
        if not hasattr(self, 'kanban_view') or not self.kanban_view:
            logger.warning("[MainWindow] Kanban view not available")
            return
        
        # Przełącz na widok kanban
        self.content_stack.setCurrentWidget(self.kanban_view)
        
        # Odśwież tablicę
        self.kanban_view.refresh_board()
        
        logger.success("[MainWindow] Assistant opened kanban view")
    
    def handle_assistant_kanban_show_all(self, command) -> None:
        """
        Pokazuje wszystkie kolumny kanban przez asystenta głosowego.
        
        Args:
            command: Sparsowana komenda ParsedCommand
        """
        if not hasattr(self, 'kanban_view') or not self.kanban_view:
            logger.warning("[MainWindow] Kanban view not available")
            return
        
        # Przełącz na widok kanban jeśli nie jesteśmy już tam
        current_is_kanban = self.content_stack.currentWidget() == self.kanban_view
        if not current_is_kanban:
            self.content_stack.setCurrentWidget(self.kanban_view)
            # Odśwież tylko przy pierwszym wejściu do widoku
            self.kanban_view.refresh_board()
        
        # Pokaż wszystkie kolumny (bez refresh - checkboxy same pokażą kolumny)
        self.kanban_view.assistant_show_all_columns()
        
        logger.success("[MainWindow] Assistant showed all kanban columns")
    
    def handle_assistant_kanban_show_column(self, command, column_name: str) -> None:
        """
        Pokazuje konkretną kolumnę kanban przez asystenta głosowego.
        
        Args:
            command: Sparsowana komenda ParsedCommand
            column_name: Internal column name ('todo', 'done', 'review', 'on_hold', 'in_progress')
        """
        if not hasattr(self, 'kanban_view') or not self.kanban_view:
            logger.warning("[MainWindow] Kanban view not available")
            return
        
        # Przełącz na widok kanban jeśli nie jesteśmy już tam
        current_is_kanban = self.content_stack.currentWidget() == self.kanban_view
        if not current_is_kanban:
            self.content_stack.setCurrentWidget(self.kanban_view)
            # Odśwież tylko przy pierwszym wejściu do widoku
            self.kanban_view.refresh_board()
        
        # Pokaż kolumnę
        changed = self.kanban_view.assistant_show_column(column_name)
        
        if changed:
            logger.success(f"[MainWindow] Assistant showed kanban column: {column_name}")
        else:
            logger.info(f"[MainWindow] Kanban column '{column_name}' already visible")
    
    def handle_assistant_kanban_hide_column(self, command, column_name: str) -> None:
        """
        Ukrywa konkretną kolumnę kanban przez asystenta głosowego.
        
        Args:
            command: Sparsowana komenda ParsedCommand
            column_name: Internal column name ('todo', 'done', 'review', 'on_hold')
        """
        if not hasattr(self, 'kanban_view') or not self.kanban_view:
            logger.warning("[MainWindow] Kanban view not available")
            return
        
        # Przełącz na widok kanban jeśli nie jesteśmy już tam
        current_is_kanban = self.content_stack.currentWidget() == self.kanban_view
        if not current_is_kanban:
            self.content_stack.setCurrentWidget(self.kanban_view)
            # Odśwież tylko przy pierwszym wejściu do widoku
            self.kanban_view.refresh_board()
        
        
        # Ukryj kolumnę (bez refresh - checkbox sam ukryje kolumnę)
        changed = self.kanban_view.assistant_hide_column(column_name)
        
        if changed:
            logger.success(f"[MainWindow] Assistant hid kanban column: {column_name}")
        else:
            logger.info(f"[MainWindow] Kanban column '{column_name}' already hidden")
    
    # ========== POMODORO ASSISTANT HANDLERS ==========
    
    def handle_assistant_pomodoro_open(self, command) -> None:
        """
        Otwiera widok Pomodoro przez asystenta głosowego.
        
        Args:
            command: Sparsowana komenda ParsedCommand
        """
        if not hasattr(self, 'pomodoro_view') or not self.pomodoro_view:
            logger.warning("[MainWindow] Pomodoro view not available")
            return
        
        # Przełącz na widok pomodoro
        self.content_stack.setCurrentWidget(self.pomodoro_view)
        logger.success("[MainWindow] Assistant opened pomodoro view")
    
    def handle_assistant_pomodoro_start(self, command) -> None:
        """
        Rozpoczyna sesję Pomodoro przez asystenta głosowego.
        
        Args:
            command: Sparsowana komenda ParsedCommand
        """
        if not hasattr(self, 'pomodoro_view') or not self.pomodoro_view:
            logger.warning("[MainWindow] Pomodoro view not available")
            return
        
        # Przełącz na widok pomodoro jeśli nie jesteśmy już tam
        current_is_pomodoro = self.content_stack.currentWidget() == self.pomodoro_view
        if not current_is_pomodoro:
            self.content_stack.setCurrentWidget(self.pomodoro_view)
        
        # Rozpocznij sesję
        self.pomodoro_view.assistant_start()
        logger.success("[MainWindow] Assistant started pomodoro session")
    
    def handle_assistant_pomodoro_pause(self, command) -> None:
        """
        Pauzuje sesję Pomodoro przez asystenta głosowego.
        
        Args:
            command: Sparsowana komenda ParsedCommand
        """
        if not hasattr(self, 'pomodoro_view') or not self.pomodoro_view:
            logger.warning("[MainWindow] Pomodoro view not available")
            return
        
        # Pauzuj sesję
        self.pomodoro_view.assistant_pause()
        logger.success("[MainWindow] Assistant paused pomodoro session")
    
    def handle_assistant_pomodoro_stop(self, command) -> None:
        """
        Zatrzymuje sesję Pomodoro przez asystenta głosowego.
        
        Args:
            command: Sparsowana komenda ParsedCommand
        """
        if not hasattr(self, 'pomodoro_view') or not self.pomodoro_view:
            logger.warning("[MainWindow] Pomodoro view not available")
            return
        
        # Zatrzymaj sesję
        self.pomodoro_view.assistant_stop()
        logger.success("[MainWindow] Assistant stopped pomodoro session")



