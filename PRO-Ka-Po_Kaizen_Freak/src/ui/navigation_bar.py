"""
Navigation Bar - Pasek nawigacyjny aplikacji
Obsługuje dynamiczną konfigurację przycisków z user_settings.json
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton
from PyQt6.QtCore import pyqtSignal
from loguru import logger

from ..utils.i18n_manager import t, get_i18n
from ..utils.theme_manager import get_theme_manager
from ..core.config import load_settings


class NavigationBar(QWidget):
    """Górny pasek nawigacyjny z przyciskami zmiany widoków"""
    
    view_changed = pyqtSignal(str)  # Signal emitowany przy zmianie widoku
    second_row_toggled = pyqtSignal(bool)  # Signal emitowany przy zmianie widoczności drugiego rzędu
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.second_row_visible = False
        self.buttons = {}
        self.button_rows = []  # Lista wierszy przycisków
        self.theme_manager = get_theme_manager()
        self._setup_ui()
        
        # Połącz z menedżerem i18n dla automatycznego odświeżania tłumaczeń
        get_i18n().language_changed.connect(self.update_translations)
    
    def rebuild_from_config(self):
        """Przebuduj przyciski nawigacyjne na podstawie konfiguracji"""
        logger.info("Rebuilding NavigationBar from configuration...")
        
        # Usuń wszystkie istniejące widgety
        layout = self.layout()
        if layout:
            while layout.count():
                item = layout.takeAt(0)
                if item.widget():
                    item.widget().deleteLater()
        else:
            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            self.setLayout(layout)
        
        # Wyczyść stare przyciski
        self.buttons.clear()
        self.button_rows.clear()
        
        # Wczytaj konfigurację
        settings = load_settings()
        env_config = settings.get('environment', {})
        rows_count = env_config.get('rows_count', 2)
        buttons_per_row = env_config.get('buttons_per_row', 8)
        buttons_config = env_config.get('buttons_config', [])
        
        # Filtruj tylko widoczne przyciski
        visible_buttons = [btn for btn in buttons_config if btn.get('visible', True)]

        # Jeśli brak konfiguracji, użyj domyślnych
        if not visible_buttons:
            visible_buttons = [
                {'id': 'tasks', 'label': 'Zadania', 'visible': True, 'is_custom': False},
                {'id': 'kanban', 'label': 'Kanban', 'visible': True, 'is_custom': False},
                {'id': 'pomodoro', 'label': 'Pomodoro', 'visible': True, 'is_custom': False},
                {'id': 'habit_tracker', 'label': 'Habit Tracker', 'visible': True, 'is_custom': False},
                {'id': 'notes', 'label': 'Notatki', 'visible': True, 'is_custom': False},
                {'id': 'callcryptor', 'label': 'CallCryptor', 'visible': True, 'is_custom': False},
                {'id': 'alarms', 'label': 'Alarmy', 'visible': True, 'is_custom': False},
                {'id': 'teamwork', 'label': 'TeamWork', 'visible': True, 'is_custom': False},
                {'id': 'fastkey', 'label': 'FastKey', 'visible': False, 'is_custom': False},
                {'id': 'promail', 'label': 'Pro-Mail', 'visible': False, 'is_custom': False},
                {'id': 'pfile', 'label': 'P-File', 'visible': False, 'is_custom': False},
                {'id': 'pweb', 'label': 'P-Web', 'visible': False, 'is_custom': False},
                {'id': 'quickboard', 'label': 'QuickBoard', 'visible': True, 'is_custom': False},
                {'id': 'proapp', 'label': 'Pro-App', 'visible': False, 'is_custom': False},
            ]

        # Oblicz całkowitą liczbę slotów
        total_slots = rows_count * buttons_per_row

        # Dodaj pojedynczy przycisk Help tylko jeśli są wolne sloty i nie ma już przycisku pomocy
        has_help_button = any(btn.get('is_help', False) for btn in visible_buttons)
        if len(visible_buttons) < total_slots and not has_help_button:
            visible_buttons.append({
                'id': 'help',
                'label': t('nav.help', 'Pomoc'),
                'visible': True,
                'is_custom': False,
                'is_help': True
            })

        # Jeśli mamy więcej widocznych przycisków niż slotów, obetnij
        if len(visible_buttons) > total_slots:
            visible_buttons = visible_buttons[:total_slots]
        
        # Buduj rzędy
        if rows_count > 1:
            # Pierwszy rząd z przyciskiem toggle
            first_row_container = QWidget()
            first_row_layout = QHBoxLayout(first_row_container)
            first_row_layout.setContentsMargins(0, 0, 0, 0)
            first_row_layout.setSpacing(2)
            
            # Przycisk toggle
            self.toggle_second_row_btn = QPushButton("▼")
            self.toggle_second_row_btn.setCheckable(True)
            self.toggle_second_row_btn.setMinimumHeight(40)
            self.toggle_second_row_btn.setObjectName("navButton")
            self.toggle_second_row_btn.clicked.connect(self.toggle_additional_rows)
            self.toggle_second_row_btn.setStyleSheet("min-width: 25px; max-width: 25px; width: 25px; padding: 0px;")
            first_row_layout.addWidget(self.toggle_second_row_btn)
            
            # Przyciski pierwszego rzędu
            for i in range(buttons_per_row):
                if i < len(visible_buttons):
                    btn_config = visible_buttons[i]
                    btn = self._create_button(btn_config)
                    first_row_layout.addWidget(btn, stretch=1)
                    # Użyj unikalnego ID
                    btn_id = btn_config.get('id', f'button_{i}')
                    if btn_id in self.buttons:
                        btn_id = f"{btn_id}_{i}"
                    self.buttons[btn_id] = btn
            
            layout.addWidget(first_row_container)
            self.button_rows.append(first_row_container)
            
            # Dodatkowe rzędy
            for row_idx in range(1, rows_count):
                row_container = QWidget()
                row_layout = QHBoxLayout(row_container)
                row_layout.setContentsMargins(0, 2, 0, 0)
                row_layout.setSpacing(2)
                
                start_idx = row_idx * buttons_per_row
                end_idx = start_idx + buttons_per_row
                
                for i in range(start_idx, end_idx):
                    if i < len(visible_buttons):
                        btn_config = visible_buttons[i]
                        btn = self._create_button(btn_config)
                        row_layout.addWidget(btn, stretch=1)
                        btn_id = btn_config.get('id', f'button_{i}')
                        if btn_id in self.buttons:
                            btn_id = f"{btn_id}_{i}"
                        self.buttons[btn_id] = btn
                
                row_container.setVisible(False)
                layout.addWidget(row_container)
                self.button_rows.append(row_container)
        else:
            # Pojedynczy rząd
            single_row_container = QWidget()
            single_row_layout = QHBoxLayout(single_row_container)
            single_row_layout.setContentsMargins(0, 0, 0, 0)
            single_row_layout.setSpacing(2)
            
            for i in range(min(buttons_per_row, len(visible_buttons))):
                btn_config = visible_buttons[i]
                btn = self._create_button(btn_config)
                single_row_layout.addWidget(btn, stretch=1)
                btn_id = btn_config.get('id', f'button_{i}')
                self.buttons[btn_id] = btn
            
            layout.addWidget(single_row_container)
            self.button_rows.append(single_row_container)
            self.toggle_second_row_btn = None
        
        # Zaznacz przycisk tasks
        if 'tasks' in self.buttons:
            self.buttons['tasks'].setChecked(True)
        
        logger.info(f"NavigationBar rebuilt: {rows_count} rows x {buttons_per_row} buttons = {len(self.buttons)} total")
    
    def _create_button(self, btn_config):
        """Tworzy pojedynczy przycisk nawigacyjny"""
        btn_id = btn_config.get('id', 'unknown')
        btn_label = btn_config.get('label', btn_id.capitalize())
        
        # Użyj tłumaczenia dla wbudowanych modułów
        if not btn_config.get('is_custom', False) and not btn_config.get('is_help', False):
            btn_label = t(f'nav.{btn_id}', btn_label)
        
        btn = QPushButton(btn_label)
        btn.setCheckable(True)
        btn.setMinimumHeight(40)
        btn.setObjectName("navButton")
        btn.clicked.connect(lambda checked, k=btn_id: self._on_button_clicked(k))
        
        return btn
    
    def toggle_additional_rows(self):
        """Przełącz widoczność dodatkowych rzędów"""
        if len(self.button_rows) <= 1:
            return
        
        self.second_row_visible = not self.second_row_visible
        
        # Pokaż/ukryj wszystkie rzędy oprócz pierwszego
        for i in range(1, len(self.button_rows)):
            self.button_rows[i].setVisible(self.second_row_visible)
        
        # Zaktualizuj przycisk toggle
        if self.toggle_second_row_btn:
            if self.second_row_visible:
                self.toggle_second_row_btn.setText("▲")
                self.toggle_second_row_btn.setChecked(True)
            else:
                self.toggle_second_row_btn.setText("▼")
                self.toggle_second_row_btn.setChecked(False)
        
        self.second_row_toggled.emit(self.second_row_visible)
        logger.info(f"Additional navigation rows {'shown' if self.second_row_visible else 'hidden'}")
    
    def _setup_ui(self):
        """Konfiguracja interfejsu paska nawigacyjnego"""
        # Używamy rebuild_from_config() do budowy początkowej
        self.rebuild_from_config()
    
    def toggle_second_row(self):
        """Przełącz widoczność drugiego rzędu przycisków (publiczna metoda - dla zgodności)"""
        # Wywołaj nową metodę
        return self.toggle_additional_rows()
    
    def _on_button_clicked(self, view_name: str):
        """Obsługa kliknięcia przycisku nawigacyjnego"""
        # Sprawdź czy to przycisk pomocy
        if view_name == 'help':
            # Emituj specjalny signal dla pomocy zamiast standardowej zmiany widoku
            self.view_changed.emit('help')
            logger.info("Help button clicked")
            return

        # Odznacz wszystkie przyciski
        for btn in self.buttons.values():
            btn.setChecked(False)

        # Zaznacz kliknięty przycisk
        if view_name in self.buttons:
            self.buttons[view_name].setChecked(True)

        # Emituj signal zmiany widoku
        self.view_changed.emit(view_name)
        logger.info(f"View changed to: {view_name}")
    
    def switch_to_view(self, view_name: str):
        """
        Programowo przełącz widok na określony moduł
        
        Args:
            view_name: ID modułu (np. 'tasks', 'pomodoro')
        """
        if view_name in self.buttons:
            self._on_button_clicked(view_name)
            logger.info(f"Programmatically switched to view: {view_name}")
        else:
            logger.warning(f"Cannot switch to view '{view_name}': button not found")
    
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
            'teamwork': t('nav.teamwork'),
        }
        
        for key, btn in self.buttons.items():
            if key in translations:
                btn.setText(translations[key])
        
        logger.info("Navigation bar translations updated")
    
    def set_button_config(self, button_configs: list):
        """
        Ustaw konfigurację przycisków (etykiety, widoczność, kolejność)
        
        Args:
            button_configs: Lista słowników z konfiguracją przycisków
                [{'id': 'tasks', 'label': 'Zadania', 'visible': True, 'position': 0}, ...]
        """
        # TODO: Implementacja w następnym etapie - konfiguracja przycisków z settings
        logger.info(f"Button configuration updated: {len(button_configs)} buttons")
    
    def apply_theme(self):
        """Apply current theme to navigation bar"""
        if not self.theme_manager:
            return
        
        colors = self.theme_manager.get_current_colors()
        
        bg_main = colors.get('bg_main', '#ffffff')
        text_primary = colors.get('text_primary', '#000000')
        accent_primary = colors.get('accent_primary', '#2196F3')
        accent_hover = colors.get('accent_hover', '#1976D2')
        border_light = colors.get('border_light', '#e0e0e0')
        
        # Styl dla całego navigation bara
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {bg_main};
            }}
            
            QPushButton#navButton {{
                background-color: {bg_main};
                color: {text_primary};
                border: 1px solid {border_light};
                border-radius: 4px;
                padding: 8px 12px;
                font-weight: bold;
                min-height: 40px;
            }}
            
            QPushButton#navButton:hover {{
                background-color: {accent_hover};
                color: white;
                border-color: {accent_hover};
            }}
            
            QPushButton#navButton:checked {{
                background-color: {accent_primary};
                color: white;
                border-color: {accent_primary};
            }}
        """)
        
        # Ustaw styl przycisku toggle (zachowaj szerokość)
        if hasattr(self, 'toggle_second_row_btn'):
            self.toggle_second_row_btn.setStyleSheet(
                f"min-width: 25px; max-width: 25px; width: 25px; padding: 0px;"
            )
        
        logger.info("[NavigationBar] Theme applied successfully")

