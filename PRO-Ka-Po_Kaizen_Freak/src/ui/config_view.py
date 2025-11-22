"""
Settings View - Widok ustawień aplikacji
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QComboBox, QPushButton, QCheckBox,
    QLineEdit, QGroupBox, QScrollArea, QFrame,
    QMessageBox, QDialog, QFileDialog, QFormLayout
)
from PyQt6.QtCore import Qt, pyqtSignal, QUrl
from PyQt6.QtGui import QFont, QKeySequence
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from loguru import logger
import os

from ..utils.i18n_manager import t, get_i18n
from ..core.config import config, save_settings, load_settings
from .style_creator_dialog import StyleCreatorDialog
from ..utils.theme_manager import get_theme_manager
from .ai_settings import AISettingsTab
from .assistant_settings_tab import AssistantSettingsTab
from .email_settings_card import EmailSettingsCard
from .shortcut_edit import ShortcutEdit


class GeneralSettingsTab(QWidget):
    """Karta ustawień ogólnych"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        
        # Inicjalizacja odtwarzacza audio
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.5)  # 50% głośności
        
        # Lista własnych dźwięków
        self.custom_sounds = {}  # {nazwa: ścieżka}
        
        self._setup_ui()
        self._load_settings()
        self._connect_signals()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu karty ogólnej"""
        # Główny layout z scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget wewnątrz scroll area
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        # === SEKCJA: Kolorystyka ===
        self.colors_group = QGroupBox(t('settings.colors'))
        colors_layout = QVBoxLayout()
        
        # Wybierz układ 1
        layout1_row = QHBoxLayout()
        self.layout1_label = QLabel(t('settings.color_scheme_1'))
        self.layout1_label.setMinimumWidth(150)
        self.combo_layout1 = QComboBox()
        # Wypełnij dostępnymi motywami
        available_themes = self.theme_manager.get_available_themes()
        self.combo_layout1.addItems(available_themes)
        layout1_row.addWidget(self.layout1_label)
        layout1_row.addWidget(self.combo_layout1, stretch=1)
        colors_layout.addLayout(layout1_row)
        
        # Wybierz układ 2
        layout2_row = QHBoxLayout()
        self.layout2_label = QLabel(t('settings.color_scheme_2'))
        self.layout2_label.setMinimumWidth(150)
        self.combo_layout2 = QComboBox()
        self.combo_layout2.addItems(available_themes)
        layout2_row.addWidget(self.layout2_label)
        layout2_row.addWidget(self.combo_layout2, stretch=1)
        colors_layout.addLayout(layout2_row)
        
        # Przycisk własnej kompozycji
        self.btn_custom_colors = QPushButton(t('settings.create_custom_scheme'))
        self.btn_custom_colors.clicked.connect(self._open_color_dialog)
        colors_layout.addWidget(self.btn_custom_colors)
        
        self.colors_group.setLayout(colors_layout)
        scroll_layout.addWidget(self.colors_group)
        
        # === SEKCJA: Język ===
        self.language_group = QGroupBox(t('settings.language'))
        language_layout = QHBoxLayout()
        
        self.language_label = QLabel(t('settings.select_language'))
        self.language_label.setMinimumWidth(150)
        self.combo_language = QComboBox()
        self.combo_language.addItems([
            "Polski",
            "English",
            "Deutsch",
            "Español",
            "日本語",
            "中文",
        ])
        language_layout.addWidget(self.language_label)
        language_layout.addWidget(self.combo_language, stretch=1)
        
        self.language_group.setLayout(language_layout)
        scroll_layout.addWidget(self.language_group)
        
        # === SEKCJA: Ustawienia systemowe ===
        self.system_group = QGroupBox(t('settings.system'))
        system_layout = QVBoxLayout()
        
        self.check_autostart = QCheckBox(t('settings.autostart'))
        system_layout.addWidget(self.check_autostart)
        
        self.check_background = QCheckBox(t('settings.run_in_background'))
        system_layout.addWidget(self.check_background)
        
        self.check_notifications = QCheckBox(t('settings.enable_notifications'))
        system_layout.addWidget(self.check_notifications)
        
        self.check_sound = QCheckBox(t('settings.enable_sound'))
        system_layout.addWidget(self.check_sound)
        
        self.system_group.setLayout(system_layout)
        scroll_layout.addWidget(self.system_group)
        
        # === SEKCJA: Dźwięki ===
        self.sounds_group = QGroupBox(t('settings.sounds'))
        sounds_layout = QVBoxLayout()
        
        # Dźwięk 1 (np. powiadomienie o zadaniu)
        sound1_row = QHBoxLayout()
        self.sound1_label = QLabel(t('settings.sound_notification'))
        self.sound1_label.setMinimumWidth(200)
        self.combo_sound1 = QComboBox()
        self.combo_sound1.setMinimumWidth(200)
        self.btn_sound1_browse = QPushButton("📁")
        self.btn_sound1_browse.setFixedWidth(40)
        self.btn_sound1_browse.setToolTip(t('settings.browse_sound'))
        self.btn_sound1_browse.clicked.connect(lambda: self._browse_sound(1))
        self.btn_sound1_play = QPushButton("▶")
        self.btn_sound1_play.setFixedWidth(40)
        self.btn_sound1_play.setToolTip(t('settings.play_sound'))
        self.btn_sound1_play.clicked.connect(lambda: self._play_sound(1))
        sound1_row.addWidget(self.sound1_label)
        sound1_row.addWidget(self.combo_sound1, stretch=1)
        sound1_row.addWidget(self.btn_sound1_browse)
        sound1_row.addWidget(self.btn_sound1_play)
        sounds_layout.addLayout(sound1_row)
        
        # Dźwięk 2 (np. alarm/przypomnienie)
        sound2_row = QHBoxLayout()
        self.sound2_label = QLabel(t('settings.sound_alarm'))
        self.sound2_label.setMinimumWidth(200)
        self.combo_sound2 = QComboBox()
        self.combo_sound2.setMinimumWidth(200)
        self.btn_sound2_browse = QPushButton("📁")
        self.btn_sound2_browse.setFixedWidth(40)
        self.btn_sound2_browse.setToolTip(t('settings.browse_sound'))
        self.btn_sound2_browse.clicked.connect(lambda: self._browse_sound(2))
        self.btn_sound2_play = QPushButton("▶")
        self.btn_sound2_play.setFixedWidth(40)
        self.btn_sound2_play.setToolTip(t('settings.play_sound'))
        self.btn_sound2_play.clicked.connect(lambda: self._play_sound(2))
        sound2_row.addWidget(self.sound2_label)
        sound2_row.addWidget(self.combo_sound2, stretch=1)
        sound2_row.addWidget(self.btn_sound2_browse)
        sound2_row.addWidget(self.btn_sound2_play)
        sounds_layout.addLayout(sound2_row)
        
        # Wypełnij combo boxy dźwiękami systemowymi
        self._populate_sound_combos()
        
        self.sounds_group.setLayout(sounds_layout)
        scroll_layout.addWidget(self.sounds_group)
        
        # === SEKCJA: Skróty klawiszowe ===
        self.shortcuts_group = QGroupBox(t('settings.shortcuts'))
        shortcuts_layout = QVBoxLayout()
        
        # Szybkie dodawanie zadań
        quick_add_row = QHBoxLayout()
        self.quick_add_label = QLabel(t('settings.shortcut_quick_add'))
        self.quick_add_label.setMinimumWidth(200)
        self.input_shortcut_quick_add = QLineEdit()
        self.input_shortcut_quick_add.setPlaceholderText("Ctrl+N")
        quick_add_row.addWidget(self.quick_add_label)
        quick_add_row.addWidget(self.input_shortcut_quick_add, stretch=1)
        shortcuts_layout.addLayout(quick_add_row)
        
        # Wywołanie okna głównego
        show_main_row = QHBoxLayout()
        self.show_main_label = QLabel(t('settings.shortcut_show_main'))
        self.show_main_label.setMinimumWidth(200)
        self.input_shortcut_show_main = QLineEdit()
        self.input_shortcut_show_main.setPlaceholderText("Ctrl+Shift+K")
        show_main_row.addWidget(self.show_main_label)
        show_main_row.addWidget(self.input_shortcut_show_main, stretch=1)
        shortcuts_layout.addLayout(show_main_row)
        
        self.shortcuts_group.setLayout(shortcuts_layout)
        scroll_layout.addWidget(self.shortcuts_group)
        
        # Dodaj stretch na końcu
        scroll_layout.addStretch()
        
        # Ustaw scroll widget
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        # === PRZYCISK ZAPISZ (na dole, poza scroll) ===
        self.btn_save = QPushButton(t('button.save'))
        self.btn_save.setMinimumHeight(45)
        self.btn_save.setObjectName("saveButton")
        self.btn_save.clicked.connect(self._save_settings)
        main_layout.addWidget(self.btn_save)
    
    def _open_color_dialog(self):
        """Otwórz dialog tworzenia własnej kompozycji"""
        dialog = StyleCreatorDialog(self)
        
        # NAPRAWIONE: Podłącz sygnał zapisania stylu do odświeżania listy
        dialog.style_saved.connect(self._on_custom_style_saved)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            logger.info("Custom color scheme created successfully")
            
            QMessageBox.information(
                self,
                t('dialog.info'),
                t('style_creator.scheme_created')
            )
    
    def _on_custom_style_saved(self, style_name: str):
        """Obsługa zapisu nowego własnego stylu"""
        logger.info(f"[GeneralSettingsTab] Custom style saved: {style_name}")
        
        # Odśwież listę motywów
        self.refresh_theme_list()
        
        # Ustaw nowy styl jako aktywny w layout1
        index = self.combo_layout1.findText(f"⭐ {style_name}")
        if index >= 0:
            self.combo_layout1.setCurrentIndex(index)
            logger.info(f"[GeneralSettingsTab] Set new custom style as active in layout1")
        
        # Zastosuj nowy motyw do aplikacji
        self.theme_manager.apply_theme(style_name)
        logger.info(f"[GeneralSettingsTab] Applied new theme: {style_name}")
        
        # Odśwież UI
        self.apply_theme()
        
        # Emituj sygnał o zmianie ustawień (propagacja do całej aplikacji)
        from ..core.config import load_settings
        settings = load_settings()
        self.settings_changed.emit(settings)
    
    def _refresh_theme_lists(self):
        """Odśwież listy dostępnych motywów"""
        # Zapisz aktualne wybory
        current_layout1 = self.combo_layout1.currentText()
        current_layout2 = self.combo_layout2.currentText()
        
        # Wyczyść listy
        self.combo_layout1.clear()
        self.combo_layout2.clear()
        
        # Pobierz aktualizowaną listę motywów
        available_themes = self.theme_manager.get_available_themes()
        self.combo_layout1.addItems(available_themes)
        self.combo_layout2.addItems(available_themes)
        
        # Przywróć poprzednie wybory
        index1 = self.combo_layout1.findText(current_layout1)
        if index1 >= 0:
            self.combo_layout1.setCurrentIndex(index1)
        
        index2 = self.combo_layout2.findText(current_layout2)
        if index2 >= 0:
            self.combo_layout2.setCurrentIndex(index2)
    
    def _load_settings(self):
        """Wczytaj ustawienia"""
        settings = load_settings()
        
        # Mapowanie języków
        language_map = {
            'pl': 0,
            'en': 1,
            'de': 2,
            'es': 3,
            'ja': 4,
            'zh': 5,
        }
        
        # Ustaw wartości
        lang_index = language_map.get(settings.get('language', 'pl'), 0)
        self.combo_language.setCurrentIndex(lang_index)
        
        # NAPRAWIONE: Wyczyść combo przed dodaniem motywów (unikaj duplikatów)
        self.combo_layout1.clear()
        self.combo_layout2.clear()
        
        # Pobierz i dodaj dostępne motywy
        available_themes = self.theme_manager.get_available_themes()
        self.combo_layout1.addItems(available_themes)
        self.combo_layout2.addItems(available_themes)
        
        # Ustaw schematy kolorów
        scheme1 = settings.get('color_scheme_1', 'light')
        scheme2 = settings.get('color_scheme_2', 'dark')
        
        # Usuń prefix ⭐ jeśli jest w zapisanych ustawieniach
        scheme1_clean = scheme1.replace("⭐ ", "")
        scheme2_clean = scheme2.replace("⭐ ", "")
        
        # Znajdź i ustaw schemat 1
        index1 = self.combo_layout1.findText(scheme1_clean)
        if index1 >= 0:
            self.combo_layout1.setCurrentIndex(index1)
        else:
            # Może być z prefiksem ⭐
            index1 = self.combo_layout1.findText(f"⭐ {scheme1_clean}")
            if index1 >= 0:
                self.combo_layout1.setCurrentIndex(index1)
            else:
                # Ustaw pierwszy dostępny motyw
                if self.combo_layout1.count() > 0:
                    self.combo_layout1.setCurrentIndex(0)
        
        # Znajdź i ustaw schemat 2
        index2 = self.combo_layout2.findText(scheme2_clean)
        if index2 >= 0:
            self.combo_layout2.setCurrentIndex(index2)
        else:
            # Może być z prefiksem ⭐
            index2 = self.combo_layout2.findText(f"⭐ {scheme2_clean}")
            if index2 >= 0:
                self.combo_layout2.setCurrentIndex(index2)
            else:
                # Ustaw drugi dostępny motyw (jeśli jest) lub pierwszy
                if self.combo_layout2.count() > 1:
                    self.combo_layout2.setCurrentIndex(1)
                elif self.combo_layout2.count() > 0:
                    self.combo_layout2.setCurrentIndex(0)
        
        # Ustaw schematy w theme_manager
        self.theme_manager.set_layout_scheme(1, self.combo_layout1.currentText())
        self.theme_manager.set_layout_scheme(2, self.combo_layout2.currentText())
        
        self.check_autostart.setChecked(settings.get('auto_start', False))
        self.check_background.setChecked(settings.get('run_in_background', True))
        self.check_notifications.setChecked(settings.get('enable_notifications', True))
        self.check_sound.setChecked(settings.get('enable_sound', True))
        
        # Załaduj wybrane dźwięki
        sound1 = settings.get('sound_notification', 'Beep (domyślny)')
        sound2 = settings.get('sound_alarm', 'Exclamation')
        
        # Ustaw dźwięk 1
        index1 = self.combo_sound1.findText(sound1)
        if index1 >= 0:
            self.combo_sound1.setCurrentIndex(index1)
        
        # Ustaw dźwięk 2
        index2 = self.combo_sound2.findText(sound2)
        if index2 >= 0:
            self.combo_sound2.setCurrentIndex(index2)
        
        self.input_shortcut_quick_add.setText(settings.get('shortcut_quick_add', 'Ctrl+N'))
        self.input_shortcut_show_main.setText(settings.get('shortcut_show_main', 'Ctrl+Shift+K'))
        
        logger.info("Settings loaded")
    
    def _connect_signals(self):
        """Połącz sygnały z slotami"""
        # Zmiana układu 1 - od razu aplikuj
        self.combo_layout1.currentTextChanged.connect(self._on_layout1_changed)
        
        # Zmiana układu 2 - od razu aplikuj
        self.combo_layout2.currentTextChanged.connect(self._on_layout2_changed)
        
        # Zapisz zmiany po wyborze języka
        self.combo_language.currentIndexChanged.connect(self._on_settings_changed)
        
        # Ustawienia systemowe - natychmiastowa aplikacja
        self.check_autostart.stateChanged.connect(self._on_autostart_changed)
        self.check_background.stateChanged.connect(self._on_background_changed)
        self.check_notifications.stateChanged.connect(self._on_notifications_changed)
        self.check_sound.stateChanged.connect(self._on_sound_changed)
    
    def _on_layout1_changed(self, scheme_name: str):
        """Obsługa zmiany schematu dla układu 1"""
        if scheme_name:
            self.theme_manager.set_layout_scheme(1, scheme_name)
            logger.info(f"Layout 1 scheme changed to: {scheme_name}")
            
            # Jeśli aktualnie jest układ 1, zastosuj zmianę
            if self.theme_manager.get_current_layout() == 1:
                self.theme_manager.apply_theme(scheme_name)
    
    def _on_layout2_changed(self, scheme_name: str):
        """Obsługa zmiany schematu dla układu 2"""
        if scheme_name:
            self.theme_manager.set_layout_scheme(2, scheme_name)
            logger.info(f"Layout 2 scheme changed to: {scheme_name}")
            
            # Jeśli aktualnie jest układ 2, zastosuj zmianę
            if self.theme_manager.get_current_layout() == 2:
                self.theme_manager.apply_theme(scheme_name)
    
    def _on_autostart_changed(self, state):
        """Obsługa zmiany autostartu aplikacji"""
        is_enabled = (state == 2)  # Qt.CheckState.Checked = 2
        logger.info(f"Autostart changed to: {is_enabled}")
        
        if is_enabled:
            self._enable_autostart()
        else:
            self._disable_autostart()
        
        # Zapisz ustawienie
        settings = load_settings()
        settings['auto_start'] = is_enabled
        save_settings(settings)
    
    def _on_background_changed(self, state):
        """Obsługa zmiany uruchamiania w tle"""
        is_enabled = (state == 2)
        logger.info(f"Run in background changed to: {is_enabled}")
        
        # Zapisz ustawienie
        settings = load_settings()
        settings['run_in_background'] = is_enabled
        save_settings(settings)
        
        # Informacja dla użytkownika
        if is_enabled:
            logger.info("Application will minimize to system tray when closed")
        else:
            logger.info("Application will exit completely when closed")
    
    def _on_notifications_changed(self, state):
        """Obsługa zmiany powiadomień"""
        is_enabled = (state == 2)
        logger.info(f"Notifications changed to: {is_enabled}")
        
        # Zapisz ustawienie
        settings = load_settings()
        settings['enable_notifications'] = is_enabled
        save_settings(settings)
        
        # Emituj signal o zmianie
        self.settings_changed.emit({'enable_notifications': is_enabled})
    
    def _on_sound_changed(self, state):
        """Obsługa zmiany dźwięków"""
        is_enabled = (state == 2)
        logger.info(f"Sound notifications changed to: {is_enabled}")
        
        # Zapisz ustawienie
        settings = load_settings()
        settings['enable_sound'] = is_enabled
        save_settings(settings)
        
        # Emituj signal o zmianie
        self.settings_changed.emit({'enable_sound': is_enabled})
    
    def _populate_sound_combos(self):
        """Wypełnij combo boxy dźwiękami z resources/sounds i własnymi"""
        # Resolve sounds dir in a packaging-aware way (resource_path or config)
        try:
            from src.utils.paths import resource_path
            from pathlib import Path
            sounds_dir = Path(resource_path('resources', 'sounds'))
        except Exception:
            # Fallback to config.RESOURCES_DIR if available, otherwise relative path
            try:
                from ..core.config import config as _cfg
                from pathlib import Path
                sounds_dir = Path(_cfg.RESOURCES_DIR) / 'sounds'
            except Exception:
                from pathlib import Path
                sounds_dir = Path(__file__).resolve().parent.parent.parent / "resources" / "sounds"
        
        if sounds_dir.exists():
            sound_files = sorted(sounds_dir.glob("*.m4r"))
            for sound_file in sound_files:
                # Użyj nazwy pliku bez rozszerzenia jako wyświetlanej nazwy
                name = sound_file.stem
                self.combo_sound1.addItem(name)
                self.combo_sound2.addItem(name)
                # Zapisz pełną ścieżkę
                self.custom_sounds[name] = str(sound_file.absolute())
        
        # Załaduj dodatkowe własne dźwięki z ustawień
        settings = load_settings()
        custom_sounds = settings.get('custom_sounds', {})
        
        for name, path in custom_sounds.items():
            if os.path.exists(path) and name not in self.custom_sounds:
                self.combo_sound1.addItem(f"⭐ {name}")
                self.combo_sound2.addItem(f"⭐ {name}")
                self.custom_sounds[name] = path
    
    def _browse_sound(self, sound_number: int):
        """Przeglądaj i dodaj własny plik dźwiękowy"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t('settings.select_sound_file'),
            "",
            "Audio Files (*.wav *.mp3 *.ogg *.m4r);;All Files (*.*)"
        )
        
        if file_path:
            # Pobierz nazwę pliku bez rozszerzenia
            file_name = os.path.splitext(os.path.basename(file_path))[0]
            
            # Dodaj do własnych dźwięków
            self.custom_sounds[file_name] = file_path
            
            # Dodaj do combo z gwiazdką
            combo = self.combo_sound1 if sound_number == 1 else self.combo_sound2
            item_text = f"⭐ {file_name}"
            
            # Sprawdź czy już nie istnieje
            if combo.findText(item_text) == -1:
                combo.addItem(item_text)
            
            # Ustaw jako aktualny
            combo.setCurrentText(item_text)
            
            # Zapisz do ustawień
            settings = load_settings()
            if 'custom_sounds' not in settings:
                settings['custom_sounds'] = {}
            settings['custom_sounds'][file_name] = file_path
            save_settings(settings)
            
            logger.info(f"Custom sound added: {file_name} -> {file_path}")
    
    def _play_sound(self, sound_number: int):
        """Odtwórz wybrany dźwięk"""
        combo = self.combo_sound1 if sound_number == 1 else self.combo_sound2
        sound_name = combo.currentText()
        
        if not sound_name:
            return
        
        # Usuń prefix ⭐ jeśli istnieje
        sound_name_clean = sound_name.replace("⭐ ", "")
        
        # Sprawdź czy to własny dźwięk
        if sound_name_clean in self.custom_sounds:
            sound_path = self.custom_sounds[sound_name_clean]
            self._play_audio_file(sound_path)
        else:
            # Dźwięk systemowy
            self._play_system_sound(sound_name_clean)
    
    def _play_audio_file(self, file_path: str):
        """Odtwórz plik audio"""
        if os.path.exists(file_path):
            self.media_player.setSource(QUrl.fromLocalFile(file_path))
            self.media_player.play()
            logger.info(f"Playing audio file: {file_path}")
        else:
            logger.warning(f"Audio file not found: {file_path}")
            QMessageBox.warning(
                self,
                t('error'),
                t('settings.sound_file_not_found')
            )
    
    def _play_system_sound(self, sound_name: str):
        """Odtwórz dźwięk systemowy"""
        import winsound
        
        # Mapowanie nazw na dźwięki Windows
        sound_map = {
            "beep": winsound.MB_OK,
            "ding": winsound.MB_OK,
            "chord": winsound.MB_OK,
            "pop": winsound.MB_OK,
            "notify": winsound.MB_ICONASTERISK,
            "asterisk": winsound.MB_ICONASTERISK,
            "exclamation": winsound.MB_ICONEXCLAMATION,
            "question": winsound.MB_ICONQUESTION,
            "critical": winsound.MB_ICONHAND,
        }
        
        # Pobierz typ dźwięku (domyślnie MB_OK)
        sound_key = sound_name.lower().split('(')[0].strip()
        sound_type = sound_map.get(sound_key, winsound.MB_OK)
        
        try:
            winsound.MessageBeep(sound_type)
            logger.info(f"Playing system sound: {sound_name}")
        except Exception as e:
            logger.error(f"Failed to play system sound: {e}")
    
    def _enable_autostart(self):
        """Włącz autostart aplikacji w systemie"""
        import sys
        
        try:
            if sys.platform == 'win32':
                # Windows - dodaj do rejestru
                import winreg
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                app_name = "PRO-Ka-Po_Kaizen_Freak"
                app_path = os.path.abspath(sys.argv[0])
                
                # Otwórz klucz rejestru
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                winreg.SetValueEx(key, app_name, 0, winreg.REG_SZ, f'"{app_path}"')
                winreg.CloseKey(key)
                
                logger.info(f"Autostart enabled: {app_path}")
                
            elif sys.platform == 'darwin':
                # macOS - utwórz plik .plist
                logger.warning("Autostart on macOS not yet implemented")
                
            elif sys.platform.startswith('linux'):
                # Linux - utwórz plik .desktop w autostart
                logger.warning("Autostart on Linux not yet implemented")
                
        except Exception as e:
            logger.error(f"Failed to enable autostart: {e}")
    
    def _disable_autostart(self):
        """Wyłącz autostart aplikacji w systemie"""
        import sys
        
        try:
            if sys.platform == 'win32':
                # Windows - usuń z rejestru
                import winreg
                key_path = r"Software\Microsoft\Windows\CurrentVersion\Run"
                app_name = "PRO-Ka-Po_Kaizen_Freak"
                
                try:
                    key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
                    winreg.DeleteValue(key, app_name)
                    winreg.CloseKey(key)
                    logger.info("Autostart disabled")
                except FileNotFoundError:
                    # Klucz nie istnieje - już jest wyłączony
                    pass
                    
            elif sys.platform == 'darwin':
                # macOS - usuń plik .plist
                logger.warning("Autostart on macOS not yet implemented")
                
            elif sys.platform.startswith('linux'):
                # Linux - usuń plik .desktop
                logger.warning("Autostart on Linux not yet implemented")
                
        except Exception as e:
            logger.error(f"Failed to disable autostart: {e}")
    
    def _on_settings_changed(self):
        """Obsługa zmiany ustawień"""
        # Możesz tu dodać dodatkową logikę jeśli potrzeba
        pass
    
    def showEvent(self, a0):
        """Wywoływane gdy widok jest pokazywany - odśwież combo języka"""
        super().showEvent(a0)
        # Odśwież combo języka aby pokazywał aktualną wartość
        current_language = get_i18n().get_current_language()
        language_map = {
            'pl': 0,
            'en': 1,
            'de': 2,
            'es': 3,
            'ja': 4,
            'zh': 5,
        }
        lang_index = language_map.get(current_language, 0)
        self.combo_language.setCurrentIndex(lang_index)
    
    def _save_settings(self):
        """Zapisz ustawienia"""
        from PyQt6.QtWidgets import QMessageBox
        # Mapowanie języków
        language_codes = ['pl', 'en', 'de', 'es', 'ja', 'zh']
        selected_language = language_codes[self.combo_language.currentIndex()]
        current_language = get_i18n().get_current_language()

        settings = {
            'language': selected_language,
            'auto_start': self.check_autostart.isChecked(),
            'run_in_background': self.check_background.isChecked(),
            'enable_notifications': self.check_notifications.isChecked(),
            'enable_sound': self.check_sound.isChecked(),
            'sound_notification': self.combo_sound1.currentText(),
            'sound_alarm': self.combo_sound2.currentText(),
            'shortcut_quick_add': self.input_shortcut_quick_add.text(),
            'shortcut_show_main': self.input_shortcut_show_main.text(),
            'color_scheme_1': self.combo_layout1.currentText(),
            'color_scheme_2': self.combo_layout2.currentText(),
        }

        if save_settings(settings):
            # Zmień język jeśli został zmieniony
            if selected_language != current_language:
                get_i18n().set_language(selected_language)
                logger.info(f"Language changed to: {selected_language}")

            self.settings_changed.emit(settings)
            QMessageBox.information(
                self,
                "Sukces",
                "Ustawienia zostały zapisane!\n\nUI zostanie odświeżone."
            )
            logger.info("Settings saved successfully")
        else:
            QMessageBox.critical(
                self,
                "Błąd",
                "Nie udało się zapisać ustawień!"
            )
    
    def update_translations(self):
        """Odśwież tłumaczenia w karcie ustawień ogólnych"""
        # Grupy
        self.colors_group.setTitle(t('settings.colors'))
        self.language_group.setTitle(t('settings.language'))
        self.system_group.setTitle(t('settings.system'))
        self.sounds_group.setTitle(t('settings.sounds'))
        self.shortcuts_group.setTitle(t('settings.shortcuts'))
        
        # Etykiety kolorystyki
        self.layout1_label.setText(t('settings.color_scheme_1'))
        self.layout2_label.setText(t('settings.color_scheme_2'))
        self.btn_custom_colors.setText(t('settings.create_custom_scheme'))
        
        # Etykiety języka
        self.language_label.setText(t('settings.select_language'))
        
        # Checkboxy systemowe
        self.check_autostart.setText(t('settings.autostart'))
        self.check_background.setText(t('settings.run_in_background'))
        self.check_notifications.setText(t('settings.enable_notifications'))
        self.check_sound.setText(t('settings.enable_sound'))
        
        # Dźwięki
        self.sound1_label.setText(t('settings.sound_notification'))
        self.sound2_label.setText(t('settings.sound_alarm'))
        self.btn_sound1_browse.setToolTip(t('settings.browse_sound'))
        self.btn_sound2_browse.setToolTip(t('settings.browse_sound'))
        self.btn_sound1_play.setToolTip(t('settings.play_sound'))
        self.btn_sound2_play.setToolTip(t('settings.play_sound'))
        
        # Skróty klawiszowe
        self.quick_add_label.setText(t('settings.shortcut_quick_add'))
        self.show_main_label.setText(t('settings.shortcut_show_main'))
        
        # Przycisk zapisz
        self.btn_save.setText(t('button.save'))
        
        # NAPRAWIONE: Odśwież listę motywów (unikaj duplikatów)
        current_scheme1 = self.combo_layout1.currentText()
        current_scheme2 = self.combo_layout2.currentText()
        
        self.combo_layout1.clear()
        self.combo_layout2.clear()
        
        available_themes = self.theme_manager.get_available_themes()
        self.combo_layout1.addItems(available_themes)
        self.combo_layout2.addItems(available_themes)
        
        # Przywróć poprzednie wybory
        index1 = self.combo_layout1.findText(current_scheme1)
        if index1 >= 0:
            self.combo_layout1.setCurrentIndex(index1)
        
        index2 = self.combo_layout2.findText(current_scheme2)
        if index2 >= 0:
            self.combo_layout2.setCurrentIndex(index2)
        
        logger.info("Settings tab translations updated")
    
    def refresh_theme_list(self):
        """Odśwież listę dostępnych motywów (np. po dodaniu własnego stylu)"""
        try:
            # Zapamiętaj aktualne wybory
            current_scheme1 = self.combo_layout1.currentText()
            current_scheme2 = self.combo_layout2.currentText()
            
            # Wyczyść i załaduj ponownie
            self.combo_layout1.clear()
            self.combo_layout2.clear()
            
            # Odśwież listę motywów w theme_manager (jeśli metoda istnieje)
            # W przeciwnym razie po prostu pobierz ponownie listę
            available_themes = self.theme_manager.get_available_themes()
            self.combo_layout1.addItems(available_themes)
            self.combo_layout2.addItems(available_themes)
            
            # Przywróć poprzednie wybory (jeśli nadal istnieją)
            index1 = self.combo_layout1.findText(current_scheme1)
            if index1 >= 0:
                self.combo_layout1.setCurrentIndex(index1)
            elif self.combo_layout1.count() > 0:
                self.combo_layout1.setCurrentIndex(0)
            
            index2 = self.combo_layout2.findText(current_scheme2)
            if index2 >= 0:
                self.combo_layout2.setCurrentIndex(index2)
            elif self.combo_layout2.count() > 1:
                self.combo_layout2.setCurrentIndex(1)
            elif self.combo_layout2.count() > 0:
                self.combo_layout2.setCurrentIndex(0)
            
            logger.info("[GeneralSettingsTab] Theme list refreshed successfully")
            
        except Exception as e:
            logger.error(f"[GeneralSettingsTab] Error refreshing theme list: {e}")
    
    def apply_theme(self):
        """Zastosuj aktualny motyw do widgetów w karcie ustawień ogólnych"""
        if not self.theme_manager:
            return

        try:
            colors = self.theme_manager.get_current_colors()

            bg_main = colors.get("bg_main", "#FFFFFF")
            bg_secondary = colors.get("bg_secondary", "#F5F5F5")
            text_primary = colors.get("text_primary", "#000000")
            text_secondary = colors.get("text_secondary", "#666666")
            accent_primary = colors.get("accent_primary", "#2196F3")
            accent_hover = colors.get("accent_hover", "#1976D2")
            accent_pressed = colors.get("accent_pressed", "#0D47A1")
            border_light = colors.get("border_light", "#CCCCCC")
            border_dark = colors.get("border_dark", "#888888")
            disabled_bg = colors.get("disabled_bg", "#cccccc")
            disabled_text = colors.get("disabled_text", "#666666")

            # Style dla głównych grup
            group_style = f"""
                QGroupBox {{
                    background-color: {bg_main};
                    color: {text_primary};
                    border: 2px solid {border_light};
                    border-radius: 6px;
                    margin-top: 12px;
                    padding-top: 15px;
                    font-weight: 600;
                }}
                QGroupBox::title {{
                    subcontrol-origin: margin;
                    subcontrol-position: top left;
                    padding: 0 10px;
                    background-color: {bg_main};
                    color: {text_primary};
                }}
            """

            self.colors_group.setStyleSheet(group_style)
            self.language_group.setStyleSheet(group_style)
            self.system_group.setStyleSheet(group_style)
            self.sounds_group.setStyleSheet(group_style)
            self.shortcuts_group.setStyleSheet(group_style)

            # Style dla przycisków
            button_style = f"""
                QPushButton {{
                    background-color: {accent_primary};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {accent_hover};
                }}
                QPushButton:pressed {{
                    background-color: {accent_pressed};
                }}
                QPushButton:disabled {{
                    background-color: {disabled_bg};
                    color: {disabled_text};
                }}
            """

            self.btn_custom_colors.setStyleSheet(button_style)
            self.btn_save.setStyleSheet(button_style)

            # Style dla combo boxów
            combo_style = f"""
                QComboBox {{
                    background-color: {bg_main};
                    color: {text_primary};
                    border: 2px solid {border_light};
                    border-radius: 4px;
                    padding: 4px 8px;
                }}
                QComboBox:hover {{
                    border-color: {accent_primary};
                }}
                QComboBox:focus {{
                    border-color: {accent_primary};
                }}
                QComboBox::drop-down {{
                    border: none;
                    width: 20px;
                }}
                QComboBox::down-arrow {{
                    image: none;
                    border-left: 4px solid transparent;
                    border-right: 4px solid transparent;
                    border-top: 6px solid {text_primary};
                    margin-right: 5px;
                }}
                QComboBox:disabled {{
                    background-color: {disabled_bg};
                    color: {disabled_text};
                }}
            """

            self.combo_layout1.setStyleSheet(combo_style)
            self.combo_layout2.setStyleSheet(combo_style)
            self.combo_language.setStyleSheet(combo_style)
            self.combo_sound1.setStyleSheet(combo_style)
            self.combo_sound2.setStyleSheet(combo_style)

            # Style dla checkboxów
            checkbox_style = f"""
                QCheckBox {{
                    color: {text_primary};
                    spacing: 8px;
                }}
                QCheckBox::indicator {{
                    width: 18px;
                    height: 18px;
                    border: 2px solid {border_dark};
                    border-radius: 3px;
                    background-color: {bg_main};
                }}
                QCheckBox::indicator:checked {{
                    background-color: {accent_primary};
                    border-color: {accent_primary};
                }}
                QCheckBox::indicator:hover {{
                    border-color: {accent_hover};
                }}
                QCheckBox::indicator:disabled {{
                    background-color: {disabled_bg};
                    border-color: {disabled_bg};
                }}
            """

            self.check_autostart.setStyleSheet(checkbox_style)
            self.check_background.setStyleSheet(checkbox_style)
            self.check_notifications.setStyleSheet(checkbox_style)
            self.check_sound.setStyleSheet(checkbox_style)

            # Style dla input fields
            input_style = f"""
                QLineEdit {{
                    background-color: {bg_main};
                    color: {text_primary};
                    border: 2px solid {border_light};
                    border-radius: 4px;
                    padding: 4px 8px;
                }}
                QLineEdit:focus {{
                    border-color: {accent_primary};
                }}
                QLineEdit:disabled {{
                    background-color: {disabled_bg};
                    color: {disabled_text};
                }}
            """

            self.input_shortcut_quick_add.setStyleSheet(input_style)
            self.input_shortcut_show_main.setStyleSheet(input_style)

            # Style dla małych przycisków (browse, play)
            small_button_style = f"""
                QPushButton {{
                    background-color: {bg_secondary};
                    color: {text_primary};
                    border: 1px solid {border_light};
                    border-radius: 4px;
                    padding: 4px 8px;
                }}
                QPushButton:hover {{
                    background-color: {accent_hover};
                    color: white;
                    border-color: {accent_hover};
                }}
                QPushButton:pressed {{
                    background-color: {accent_pressed};
                    color: white;
                }}
                QPushButton:disabled {{
                    background-color: {disabled_bg};
                    color: {disabled_text};
                }}
            """

            self.btn_sound1_browse.setStyleSheet(small_button_style)
            self.btn_sound2_browse.setStyleSheet(small_button_style)
            self.btn_sound1_play.setStyleSheet(small_button_style)
            self.btn_sound2_play.setStyleSheet(small_button_style)

            # Style dla etykiet
            label_style = f"""
                QLabel {{
                    color: {text_primary};
                }}
            """
            for widget in self.findChildren(QLabel):
                widget.setStyleSheet(label_style)

            logger.debug("[GeneralSettingsTab] Theme applied successfully")

        except Exception as e:
            logger.error(f"[GeneralSettingsTab] Error applying theme: {e}")


class EnvironmentSettingsTab(QWidget):
    """Karta ustawień środowiska - pozycje pasków, widoczność, konfiguracja przycisków"""
    
    settings_changed = pyqtSignal(dict)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self._setup_ui()
        self._load_settings()
        self._connect_signals()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu karty środowiska"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget wewnątrz scroll area
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(15)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        
        # === SEKCJA: Układ aplikacji ===
        layout_group = QGroupBox(t('environment.layout_title', 'Układ aplikacji'))
        layout_layout = QVBoxLayout()
        
        # Info
        info_label = QLabel(t('environment.layout_info', 
            'Wybierz układ pasków nawigacji i szybkiego dodawania zadań:'))
        info_label.setWordWrap(True)
        layout_layout.addWidget(info_label)
        
        # Radio buttons dla pozycji
        from PyQt6.QtWidgets import QRadioButton, QButtonGroup
        
        self.layout_button_group = QButtonGroup()
        
        # Opcja 1: Przyciski góra, Zadania dół
        self.layout_nav_top_task_bottom = QRadioButton(
            t('environment.layout_nav_top_task_bottom', '🔼 Przyciski nawigacji na górze, pasek zadań na dole')
        )
        self.layout_button_group.addButton(self.layout_nav_top_task_bottom, 1)
        layout_layout.addWidget(self.layout_nav_top_task_bottom)
        
        # Opcja 2: Zadania góra, Przyciski dół
        self.layout_task_top_nav_bottom = QRadioButton(
            t('environment.layout_task_top_nav_bottom', '🔽 Pasek zadań na górze, przyciski nawigacji na dole')
        )
        self.layout_button_group.addButton(self.layout_task_top_nav_bottom, 2)
        layout_layout.addWidget(self.layout_task_top_nav_bottom)
        
        # Checkbox dla widoczności paska zadań
        self.taskbar_visible_check = QCheckBox(
            t('environment.taskbar_visible_check', '✅ Pokaż pasek szybkiego dodawania zadań')
        )
        self.taskbar_visible_check.setStyleSheet("margin-top: 10px; font-weight: bold;")
        layout_layout.addWidget(self.taskbar_visible_check)
        
        # Info o QuickTaskDialog
        quick_dialog_info = QLabel(
            t('environment.quick_dialog_info', 
              'ℹ️ Pasek zadań można zawsze wywołać skrótem klawiszowym (domyślnie Ctrl+N)')
        )
        quick_dialog_info.setStyleSheet("color: #666; font-style: italic; margin-top: 5px;")
        quick_dialog_info.setWordWrap(True)
        layout_layout.addWidget(quick_dialog_info)
        
        layout_group.setLayout(layout_layout)
        scroll_layout.addWidget(layout_group)
        
        # === SEKCJA: Skróty klawiszowe ===
        shortcuts_group = QGroupBox(t('environment.shortcuts_title', 'Skróty klawiszowe'))
        shortcuts_layout = QFormLayout()
        
        # Skrót dla toggle drugiego rzędu przycisków
        shortcut_row = QHBoxLayout()
        self.toggle_nav_shortcut_edit = QLineEdit()
        self.toggle_nav_shortcut_edit.setPlaceholderText("np. Ctrl+Shift+N")
        self.toggle_nav_shortcut_edit.setMinimumWidth(150)
        shortcut_row.addWidget(self.toggle_nav_shortcut_edit)
        shortcut_row.addStretch()
        
        shortcuts_layout.addRow(
            t('environment.shortcut_toggle_nav', 'Rozwiń/zwiń dodatkowe przyciski:'),
            shortcut_row
        )
        
        shortcuts_group.setLayout(shortcuts_layout)
        scroll_layout.addWidget(shortcuts_group)
        
        # === SEKCJA: Konfiguracja przycisków nawigacji ===
        buttons_group = QGroupBox(t('environment.buttons_config_title', 'Konfiguracja przycisków nawigacji'))
        buttons_layout = QVBoxLayout()
        
        # Podsekcja: Siatka przycisków
        grid_layout = QHBoxLayout()
        
        # Ilość rzędów
        rows_label = QLabel(t('environment.rows_count', 'Liczba rzędów:'))
        grid_layout.addWidget(rows_label)
        
        from PyQt6.QtWidgets import QSpinBox
        self.rows_spinbox = QSpinBox()
        self.rows_spinbox.setMinimum(1)
        self.rows_spinbox.setMaximum(6)
        self.rows_spinbox.setValue(2)  # Domyślnie 2 rzędy
        self.rows_spinbox.setToolTip(t('environment.rows_count_tooltip', 'Liczba rzędów przycisków (1-6)'))
        grid_layout.addWidget(self.rows_spinbox)
        
        grid_layout.addSpacing(20)
        
        # Ilość przycisków w rzędzie
        buttons_per_row_label = QLabel(t('environment.buttons_per_row', 'Przycisków w rzędzie:'))
        grid_layout.addWidget(buttons_per_row_label)
        
        self.buttons_per_row_spinbox = QSpinBox()
        self.buttons_per_row_spinbox.setMinimum(5)
        self.buttons_per_row_spinbox.setMaximum(8)
        self.buttons_per_row_spinbox.setValue(8)  # Domyślnie 8
        self.buttons_per_row_spinbox.setToolTip(t('environment.buttons_per_row_tooltip', 'Liczba przycisków w rzędzie (5-8)'))
        grid_layout.addWidget(self.buttons_per_row_spinbox)
        
        grid_layout.addStretch()
        buttons_layout.addLayout(grid_layout)
        
        # Label z dynamicznym ostrzeżeniem
        self.grid_warning_label = QLabel()
        self.grid_warning_label.setWordWrap(True)
        self.grid_warning_label.setStyleSheet("color: #FF9800; font-weight: bold; margin-top: 5px;")
        self.grid_warning_label.hide()  # Początkowo ukryty
        buttons_layout.addWidget(self.grid_warning_label)
        
        # Info
        info_text = QLabel(t('environment.buttons_info', 
            'Konfiguruj widoczność i etykiety przycisków nawigacji.\n'
            'Przycisk "Zadania" jest zawsze widoczny (główny widok aplikacji).'))
        info_text.setWordWrap(True)
        info_text.setStyleSheet("color: #666; margin-top: 10px; margin-bottom: 10px;")
        buttons_layout.addWidget(info_text)
        
        # Tabela konfiguracji przycisków wbudowanych
        from PyQt6.QtWidgets import QTableWidget, QTableWidgetItem, QHeaderView
        
        self.buttons_table = QTableWidget()
        self.buttons_table.setColumnCount(6)
        self.buttons_table.setHorizontalHeaderLabels([
            t('environment.table_module', 'Moduł'),
            t('environment.table_label', 'Tekst na przycisku'),
            t('environment.table_description', 'Opis'),
            t('environment.table_shortcut', 'Skrót'),
            t('environment.table_visible', 'Widoczność'),
            t('environment.table_actions', 'Akcje')
        ])
        
        # Lista wbudowanych modułów (tasks jest non-editable)
        self.builtin_modules = [
            {'id': 'tasks', 'label': 'Zadania', 'description': 'Główny widok zadań i projektów', 'visible': True, 'locked': True},
            {'id': 'kanban', 'label': 'Kanban', 'description': 'Tablica Kanban do zarządzania przepływem pracy', 'visible': True, 'locked': False},
            {'id': 'pomodoro', 'label': 'Pomodoro', 'description': 'Timer Pomodoro do produktywnej pracy', 'visible': True, 'locked': False},
            {'id': 'habit_tracker', 'label': 'Habit Tracker', 'description': 'Śledzenie nawyków i rutyn dziennych', 'visible': True, 'locked': False},
            {'id': 'notes', 'label': 'Notatki', 'description': 'Notatki i dokumenty', 'visible': True, 'locked': False},
            {'id': 'callcryptor', 'label': 'CallCryptor', 'description': 'Szyfrowanie połączeń i komunikacji', 'visible': True, 'locked': False},
            {'id': 'alarms', 'label': 'Alarmy', 'description': 'Alarmy i przypomnienia', 'visible': True, 'locked': False},
            {'id': 'teamwork', 'label': 'TeamWork', 'description': 'Współpraca zespołowa i zarządzanie projektami', 'visible': True, 'locked': False},
            {'id': 'fastkey', 'label': 'FastKey', 'description': 'Szybkie skróty klawiszowe', 'visible': False, 'locked': False},
            {'id': 'promail', 'label': 'Pro-Mail', 'description': 'Zaawansowane zarządzanie pocztą', 'visible': False, 'locked': False},
            {'id': 'pfile', 'label': 'P-File', 'description': 'Menedżer plików i dokumentów', 'visible': False, 'locked': False},
            {'id': 'pweb', 'label': 'P-Web', 'description': 'Przeglądarka i narzędzia webowe', 'visible': False, 'locked': False},
            {'id': 'quickboard', 'label': 'QuickBoard', 'description': 'Menedżer historii schowka', 'visible': True, 'locked': False},
            {'id': 'proapp', 'label': 'Pro-App', 'description': 'Zarządzanie aplikacjami', 'visible': False, 'locked': False},
        ]
        
        self.buttons_table.setRowCount(len(self.builtin_modules))
        
        for row, module in enumerate(self.builtin_modules):
            # Kolumna 0: Moduł (read-only)
            module_item = QTableWidgetItem(module['label'])
            module_item.setFlags(module_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            module_item.setData(Qt.ItemDataRole.UserRole, module['id'])  # Zapisz ID
            self.buttons_table.setItem(row, 0, module_item)
            
            # Kolumna 1: Tekst przycisku (editable)
            label_item = QTableWidgetItem(module['label'])
            if module['locked']:
                label_item.setFlags(label_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                label_item.setToolTip(t('environment.locked_tooltip', 'Ten przycisk jest wymagany'))
            self.buttons_table.setItem(row, 1, label_item)
            
            # Kolumna 2: Opis (editable)
            description_item = QTableWidgetItem(module.get('description', ''))
            if module['locked']:
                description_item.setFlags(description_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.buttons_table.setItem(row, 2, description_item)
            
            # Kolumna 3: Skrót klawiszowy (ShortcutEdit widget)
            shortcut_widget = ShortcutEdit()
            shortcut_widget.setToolTip(t('environment.shortcut_tooltip', 
                'Globalny skrót klawiszowy (np. Ctrl+Alt+T, F1)\nPo naciśnięciu aplikacja zostanie wywołana i przełączona na ten moduł'))
            shortcut_widget.setMinimumHeight(30)
            # Podłącz sygnał zmiany skrótu do walidacji konfliktów
            shortcut_widget.shortcut_changed.connect(lambda text, r=row: self._on_shortcut_changed(r, text))
            self.buttons_table.setCellWidget(row, 3, shortcut_widget)
            
            # Kolumna 4: Widoczność (checkbox - wyśrodkowany)
            visible_item = QTableWidgetItem()
            visible_item.setCheckState(Qt.CheckState.Checked if module['visible'] else Qt.CheckState.Unchecked)
            visible_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            visible_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            if module['locked']:
                visible_item.setFlags(visible_item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
                visible_item.setToolTip(t('environment.locked_tooltip', 'Ten przycisk jest wymagany'))
            self.buttons_table.setItem(row, 4, visible_item)
            
            # Kolumna 5: Akcje (pusta dla wbudowanych modułów)
            action_item = QTableWidgetItem('')
            action_item.setFlags(Qt.ItemFlag.NoItemFlags)
            self.buttons_table.setItem(row, 5, action_item)
        
        # Dopasuj szerokości kolumn
        header = self.buttons_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
            header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
            header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)  # Skrót
            header.setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)  # Widoczność
            header.setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)  # Akcje
        self.buttons_table.setMinimumHeight(400)
        
        buttons_layout.addWidget(self.buttons_table)
        
        # Przycisk dodawania custom buttons
        add_custom_btn_layout = QHBoxLayout()
        add_custom_btn_layout.addStretch()
        
        self.add_custom_button_btn = QPushButton(t('environment.add_custom_button', '+ Dodaj własny przycisk'))
        self.add_custom_button_btn.setToolTip(t('environment.add_custom_button_tooltip', 
            'Dodaj przycisk dla aplikacji zewnętrznej lub własnego widoku Python'))
        self.add_custom_button_btn.clicked.connect(self._on_add_custom_button)
        add_custom_btn_layout.addWidget(self.add_custom_button_btn)
        
        add_custom_btn_layout.addStretch()
        buttons_layout.addLayout(add_custom_btn_layout)
        
        buttons_group.setLayout(buttons_layout)
        scroll_layout.addWidget(buttons_group)
        
        # === PRZYCISKI AKCJI ===
        scroll_layout.addStretch()
        
        buttons_row = QHBoxLayout()
        buttons_row.addStretch()
        
        self.reset_btn = QPushButton(t('environment.reset_defaults', 'Przywróć domyślne'))
        self.reset_btn.clicked.connect(self._reset_to_defaults)
        buttons_row.addWidget(self.reset_btn)
        
        self.save_btn = QPushButton(t('environment.save', 'Zapisz'))
        self.save_btn.setObjectName("primaryButton")
        self.save_btn.clicked.connect(self._save_settings)
        buttons_row.addWidget(self.save_btn)
        
        scroll_layout.addLayout(buttons_row)
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        logger.info("Environment settings tab initialized")
    
    def _connect_signals(self):
        """Połącz sygnały"""
        # Radio buttons automatycznie obsługują zmianę stanu w grupie
        
        # Podłącz zmiany spinboxów do walidacji
        self.rows_spinbox.valueChanged.connect(self._validate_grid_capacity)
        self.buttons_per_row_spinbox.valueChanged.connect(self._validate_grid_capacity)
        
        # Podłącz zmiany w tabeli (checkbox widoczności)
        self.buttons_table.itemChanged.connect(self._validate_grid_capacity)
    
    def _on_shortcut_changed(self, row: int, shortcut_text: str):
        """
        Obsługa zmiany skrótu klawiszowego - walidacja konfliktów
        
        Args:
            row: Numer wiersza w tabeli
            shortcut_text: Nowy skrót klawiszowy
        """
        if not shortcut_text or shortcut_text.strip() == "":
            # Pusty skrót - OK, wyczyść style
            shortcut_widget = self.buttons_table.cellWidget(row, 3)
            if shortcut_widget:
                shortcut_widget.setStyleSheet("")
            return
        
        # Pobierz ID modułu dla tego wiersza
        module_item = self.buttons_table.item(row, 0)
        if not module_item:
            return
        
        current_module_id = module_item.data(Qt.ItemDataRole.UserRole)
        
        # Sprawdź konflikty z innymi skrótami w tabeli
        conflict_found = False
        conflict_module = None
        
        for check_row in range(self.buttons_table.rowCount()):
            if check_row == row:
                continue  # Pomiń aktualny wiersz
            
            check_widget = self.buttons_table.cellWidget(check_row, 3)
            if check_widget and isinstance(check_widget, ShortcutEdit):
                check_shortcut = check_widget.text()
                if check_shortcut and check_shortcut == shortcut_text:
                    # Znaleziono konflikt!
                    conflict_found = True
                    check_module_item = self.buttons_table.item(check_row, 0)
                    if check_module_item:
                        conflict_module = check_module_item.text()
                    break
        
        # Zastosuj visual feedback
        shortcut_widget = self.buttons_table.cellWidget(row, 3)
        if shortcut_widget:
            if conflict_found:
                # Czerwone tło dla konfliktu
                shortcut_widget.setStyleSheet("""
                    QLineEdit {
                        background-color: #ffcccc;
                        border: 2px solid #ff0000;
                    }
                """)
                shortcut_widget.setToolTip(
                    f"⚠️ KONFLIKT: Ten skrót jest już używany przez moduł '{conflict_module}'!\n\n"
                    f"Globalny skrót klawiszowy (np. Ctrl+Alt+T, F1)\n"
                    f"Po naciśnięciu aplikacja zostanie wywołana i przełączona na ten moduł"
                )
                logger.warning(f"Shortcut conflict detected: '{shortcut_text}' already used by '{conflict_module}'")
            else:
                # Zielone tło dla poprawnego skrótu
                shortcut_widget.setStyleSheet("""
                    QLineEdit {
                        background-color: #ccffcc;
                        border: 2px solid #00aa00;
                    }
                """)
                shortcut_widget.setToolTip(
                    f"✓ Skrót dostępny\n\n"
                    f"Globalny skrót klawiszowy (np. Ctrl+Alt+T, F1)\n"
                    f"Po naciśnięciu aplikacja zostanie wywołana i przełączona na ten moduł"
                )
                logger.debug(f"Shortcut '{shortcut_text}' is available for module '{current_module_id}'")
    
    def _validate_grid_capacity(self):
        """Waliduj czy liczba widocznych przycisków mieści się w siatce"""
        rows_count = self.rows_spinbox.value()
        buttons_per_row = self.buttons_per_row_spinbox.value()
        max_available_slots = rows_count * buttons_per_row

        # Zlicz widoczne przyciski
        visible_buttons_count = 0
        for row in range(self.buttons_table.rowCount()):
            visible_item = self.buttons_table.item(row, 4)  # Column 4 is visibility
            if visible_item and visible_item.checkState() == Qt.CheckState.Checked:
                visible_buttons_count += 1

        # Pokaż ostrzeżenie jeśli przekracza limit
        if visible_buttons_count > max_available_slots:
            self.grid_warning_label.setText(
                f"⚠️ UWAGA: Masz {visible_buttons_count} widocznych przycisków, "
                f"ale dostępne są tylko {max_available_slots} miejsca! "
                f"Ukryj {visible_buttons_count - max_available_slots} przycisk(ów) lub zwiększ siatkę."
            )
            self.grid_warning_label.show()
            logger.warning(f"Grid capacity exceeded: {visible_buttons_count} > {max_available_slots}")
        else:
            self.grid_warning_label.hide()
            # Opcjonalnie pokaż info o wolnych miejscach
            free_slots = max_available_slots - visible_buttons_count
            if free_slots > 0:
                self.grid_warning_label.setStyleSheet("color: #4CAF50; font-weight: normal; margin-top: 5px;")
                self.grid_warning_label.setText(
                    f"✓ Dostępne miejsca: {free_slots} / {max_available_slots}"
                )
                self.grid_warning_label.show()
            else:
                self.grid_warning_label.hide()
    
    def _on_setting_changed(self):
        """Obsługa zmiany ustawienia (oznacz jako zmienione)"""
        # Można dodać visual feedback że są niezapisane zmiany
        pass
    
    def _on_add_custom_button(self):
        """Otwórz dialog dodawania własnego przycisku"""
        from .custom_button_dialog import CustomButtonDialog
        from PyQt6.QtWidgets import QMessageBox
        
        # WALIDACJA: Sprawdź czy jest dostępne miejsce na kolejny przycisk
        rows_count = self.rows_spinbox.value()
        buttons_per_row = self.buttons_per_row_spinbox.value()
        max_available_slots = rows_count * buttons_per_row
        
        # Zlicz obecnie widoczne przyciski
        visible_buttons_count = 0
        for row in range(self.buttons_table.rowCount()):
            visible_item = self.buttons_table.item(row, 4)
            if visible_item and visible_item.checkState() == Qt.CheckState.Checked:
                visible_buttons_count += 1
        
        # Sprawdź czy dodanie nowego przycisku przekroczy limit
        if visible_buttons_count >= max_available_slots:
            QMessageBox.warning(
                self,
                t('environment.validation_error_title', '⚠️ Błąd walidacji'),
                t('environment.validation_no_space', 
                  f'Brak miejsca na kolejny przycisk!\n\n'
                  f'Dostępne sloty: {max_available_slots}\n'
                  f'Widoczne przyciski: {visible_buttons_count}\n\n'
                  f'Zwiększ liczbę rzędów lub przycisków w rzędzie, albo ukryj istniejące przyciski.')
            )
            logger.warning(f"Cannot add custom button: {visible_buttons_count}/{max_available_slots} slots used")
            return
        
        dialog = CustomButtonDialog(parent=self)
        if dialog.exec() == CustomButtonDialog.DialogCode.Accepted:
            # Pobierz dane z dialogu
            button_data = dialog.get_button_data()
            
            # Dodaj do tabeli jako nowy wiersz
            row = self.buttons_table.rowCount()
            self.buttons_table.insertRow(row)
            
            # Wygeneruj unikalne ID dla custom przycisku
            custom_id = f"custom_{row}_{button_data['label'].lower().replace(' ', '_')}"
            
            # Kolumna 0: Nazwa modułu (pokazujemy etykietę)
            from PyQt6.QtWidgets import QTableWidgetItem
            module_item = QTableWidgetItem(f"[Custom] {button_data['label']}")
            module_item.setFlags(module_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            module_item.setData(Qt.ItemDataRole.UserRole, custom_id)  # Zapisz ID
            # Zapisz pełne dane custom przycisku
            module_item.setData(Qt.ItemDataRole.UserRole + 1, button_data)
            self.buttons_table.setItem(row, 0, module_item)
            
            # Kolumna 1: Tekst przycisku (edytowalny)
            label_item = QTableWidgetItem(button_data['label'])
            self.buttons_table.setItem(row, 1, label_item)
            
            # Kolumna 2: Opis (edytowalny)
            description_item = QTableWidgetItem(button_data.get('description', ''))
            self.buttons_table.setItem(row, 2, description_item)
            
            # Kolumna 4: Widoczność (checkbox - wyśrodkowany)
            visible_item = QTableWidgetItem()
            visible_item.setCheckState(Qt.CheckState.Checked if button_data.get('visible', True) else Qt.CheckState.Unchecked)
            visible_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            visible_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.buttons_table.setItem(row, 4, visible_item)
            
            # Kolumna 4: Przycisk usuwania
            self._add_delete_button(row)
            
            logger.info(f"Added custom button: {button_data['label']} ({button_data['custom_type']})")
            
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.information(
                self,
                t('custom_button.added_title', 'Przycisk dodany'),
                t('custom_button.added_message', f'Dodano przycisk "{button_data["label"]}".\n\nNie zapomnij zapisać ustawień!')
            )
    
    def _add_delete_button(self, row):
        """Dodaj przycisk usuwania do custom button row"""
        from PyQt6.QtWidgets import QPushButton, QWidget, QHBoxLayout
        
        # Utwórz widget kontenera dla przycisku
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(0)
        
        # Przycisk usuwania
        delete_btn = QPushButton("🗑️")
        delete_btn.setToolTip(t('environment.delete_button', 'Usuń przycisk'))
        delete_btn.setMaximumWidth(30)
        delete_btn.setMinimumHeight(25)
        colors = self.theme_manager.get_current_colors() if self.theme_manager else {}
        error_bg = colors.get('error_bg', '#dc3545')
        error_hover = colors.get('error_hover', '#c82333')
        delete_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {error_bg};
                color: white;
                border: none;
                border-radius: 3px;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {error_hover};
            }}
        """)
        delete_btn.clicked.connect(lambda: self._on_delete_custom_button(row))
        
        layout.addWidget(delete_btn)
        layout.addStretch()
        
        self.buttons_table.setCellWidget(row, 5, container)
    
    def _on_delete_custom_button(self, row):
        """Usuń custom button z tabeli"""
        from PyQt6.QtWidgets import QMessageBox
        
        # Pobierz dane przycisku
        module_item = self.buttons_table.item(row, 0)
        if not module_item:
            return

        label_item = self.buttons_table.item(row, 1)
        button_label = label_item.text() if label_item else "Unknown"
        
        # Potwierdzenie usunięcia
        reply = QMessageBox.question(
            self,
            t('environment.delete_confirm_title', 'Potwierdź usunięcie'),
            t('environment.delete_confirm_message', f'Czy na pewno chcesz usunąć przycisk "{button_label}"?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.buttons_table.removeRow(row)
            logger.info(f"Deleted custom button at row {row}: {button_label}")
    
    def _load_settings(self):
        """Wczytaj ustawienia z pliku konfiguracyjnego"""
        settings = load_settings()
        env_config = settings.get('environment', {})
        
        # Odczytaj ustawienia
        navbar_pos = env_config.get('navbar_position', 'top')
        taskbar_pos = env_config.get('taskbar_position', 'bottom')
        taskbar_visible = env_config.get('taskbar_visible', False)
        toggle_nav_shortcut = env_config.get('shortcut_toggle_nav', 'Ctrl+Shift+N')
        rows_count = env_config.get('rows_count', 2)
        buttons_per_row = env_config.get('buttons_per_row', 8)
        buttons_config = env_config.get('buttons_config', [])
        
        # Ustaw radio button na podstawie pozycji
        if navbar_pos == 'top' and taskbar_pos == 'bottom':
            # Przyciski góra, Zadania dół - opcja 1
            self.layout_nav_top_task_bottom.setChecked(True)
        elif navbar_pos == 'bottom' and taskbar_pos == 'top':
            # Zadania góra, Przyciski dół - opcja 2
            self.layout_task_top_nav_bottom.setChecked(True)
        else:
            # Domyślnie opcja 1
            self.layout_nav_top_task_bottom.setChecked(True)
        
        # Ustaw checkbox widoczności
        self.taskbar_visible_check.setChecked(taskbar_visible)
        
        # Ustaw skrót klawiszowy
        self.toggle_nav_shortcut_edit.setText(toggle_nav_shortcut)
        
        # Ustaw siatk przyci przycisków
        self.rows_spinbox.setValue(rows_count)
        self.buttons_per_row_spinbox.setValue(buttons_per_row)
        
        # Wczytaj konfigurację przycisków z pliku (jeśli istnieje)
        if buttons_config:
            # Mapa module_id -> config
            config_map = {btn['id']: btn for btn in buttons_config if 'id' in btn}
            
            # Zaktualizuj tabelę na podstawie konfiguracji wbudowanych przycisków
            for row in range(self.buttons_table.rowCount()):
                module_item = self.buttons_table.item(row, 0)
                if not module_item:
                    continue
                
                module_id = module_item.data(Qt.ItemDataRole.UserRole)
                if module_id in config_map:
                    config = config_map[module_id]
                    
                    # Zaktualizuj etykietę
                    label_item = self.buttons_table.item(row, 1)
                    if label_item and not self.builtin_modules[row]['locked']:
                        label_item.setText(config.get('label', self.builtin_modules[row]['label']))
                    
                    # Zaktualizuj opis
                    description_item = self.buttons_table.item(row, 2)
                    if description_item:
                        description_item.setText(config.get('description', self.builtin_modules[row].get('description', '')))
                    
                    # Zaktualizuj skrót (teraz to widget ShortcutEdit)
                    shortcut_widget = self.buttons_table.cellWidget(row, 3)
                    if shortcut_widget and isinstance(shortcut_widget, ShortcutEdit):
                        shortcut_widget.setText(config.get('shortcut', ''))
                    
                    # Zaktualizuj widoczność
                    visible_item = self.buttons_table.item(row, 4)
                    if visible_item and not self.builtin_modules[row]['locked']:
                        is_visible = config.get('visible', True)
                        visible_item.setCheckState(Qt.CheckState.Checked if is_visible else Qt.CheckState.Unchecked)
            
            # Dodaj custom buttons do tabeli
            custom_buttons = [btn for btn in buttons_config if btn.get('is_custom', False)]
            for custom_btn in custom_buttons:
                row = self.buttons_table.rowCount()
                self.buttons_table.insertRow(row)
                
                from PyQt6.QtWidgets import QTableWidgetItem
                
                # Kolumna 0: Nazwa modułu
                module_item = QTableWidgetItem(f"[Custom] {custom_btn['label']}")
                module_item.setFlags(module_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
                module_item.setData(Qt.ItemDataRole.UserRole, custom_btn['id'])
                # Zapisz pełne dane custom przycisku
                module_item.setData(Qt.ItemDataRole.UserRole + 1, custom_btn)
                self.buttons_table.setItem(row, 0, module_item)
                
                # Kolumna 1: Tekst przycisku
                label_item = QTableWidgetItem(custom_btn['label'])
                self.buttons_table.setItem(row, 1, label_item)
                
                # Kolumna 2: Opis
                description_item = QTableWidgetItem(custom_btn.get('description', ''))
                self.buttons_table.setItem(row, 2, description_item)
                
                # Kolumna 3: Skrót klawiszowy (ShortcutEdit widget)
                shortcut_widget = ShortcutEdit()
                shortcut_widget.setText(custom_btn.get('shortcut', ''))
                shortcut_widget.setToolTip(t('environment.shortcut_tooltip', 
                    'Globalny skrót klawiszowy (np. Ctrl+Alt+T, F1)\nPo naciśnięciu aplikacja zostanie wywołana i przełączona na ten moduł'))
                shortcut_widget.setMinimumHeight(30)
                # Podłącz sygnał zmiany skrótu do walidacji konfliktów
                shortcut_widget.shortcut_changed.connect(lambda text, r=row: self._on_shortcut_changed(r, text))
                self.buttons_table.setCellWidget(row, 3, shortcut_widget)
                
                # Kolumna 4: Widoczność (wyśrodkowana)
                visible_item = QTableWidgetItem()
                visible_item.setCheckState(Qt.CheckState.Checked if custom_btn.get('visible', True) else Qt.CheckState.Unchecked)
                visible_item.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                visible_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                self.buttons_table.setItem(row, 4, visible_item)
                
                # Kolumna 5: Przycisk usuwania
                self._add_delete_button(row)
                
                logger.debug(f"Loaded custom button: {custom_btn['label']}")
        
        logger.info("Environment settings loaded")
    
    def _save_settings(self):
        """Zapisz ustawienia do pliku"""
        settings = load_settings()

        # Mapuj wybrany radio button na konfigurację
        checked_id = self.layout_button_group.checkedId()
        taskbar_visible = self.taskbar_visible_check.isChecked()
        toggle_nav_shortcut = self.toggle_nav_shortcut_edit.text().strip() or 'Ctrl+Shift+N'
        rows_count = self.rows_spinbox.value()
        buttons_per_row = self.buttons_per_row_spinbox.value()

        # Oblicz maksymalną liczbę dostępnych slotów
        max_available_slots = rows_count * buttons_per_row

        # Zbierz konfigurację przycisków z tabeli
        buttons_config = []
        visible_buttons_count = 0

        for row in range(self.buttons_table.rowCount()):
            module_item = self.buttons_table.item(row, 0)
            label_item = self.buttons_table.item(row, 1)
            description_item = self.buttons_table.item(row, 2)
            shortcut_item = self.buttons_table.item(row, 3)
            visible_item = self.buttons_table.item(row, 4)

            if module_item and label_item and description_item and shortcut_item and visible_item:
                module_id = module_item.data(Qt.ItemDataRole.UserRole)

                # Pomiń przyciski pomocy (help buttons) - są dodawane dynamicznie
                if module_id and module_id.startswith('help_'):
                    continue

                label = label_item.text()
                description = description_item.text()
                shortcut_widget = self.buttons_table.cellWidget(row, 3)
                shortcut = ""
                if shortcut_widget and isinstance(shortcut_widget, ShortcutEdit):
                    shortcut = shortcut_widget.text().strip()
                visible = visible_item.checkState() == Qt.CheckState.Checked

                # Zlicz widoczne przyciski
                if visible:
                    visible_buttons_count += 1

                # Sprawdź czy to custom button (ma dodatkowe dane)
                custom_data = module_item.data(Qt.ItemDataRole.UserRole + 1)

                if custom_data:
                    # Custom button - zachowaj wszystkie dane
                    button_config = {
                        'id': module_id,
                        'label': label,
                        'description': description,
                        'shortcut': shortcut,
                        'visible': visible,
                        'is_custom': True,
                        'custom_type': custom_data.get('custom_type'),
                        'custom_path': custom_data.get('custom_path')
                    }
                else:
                    # Wbudowany button
                    button_config = {
                        'id': module_id,
                        'label': label,
                        'description': description,
                        'shortcut': shortcut,
                        'visible': visible,
                        'is_custom': False
                    }

                buttons_config.append(button_config)

        # WALIDACJA: Sprawdź czy liczba widocznych przycisków nie przekracza dostępnych slotów
        if visible_buttons_count > max_available_slots:
            QMessageBox.warning(
                self,
                t('environment.validation_error_title', '⚠️ Błąd walidacji'),
                t('environment.validation_too_many_buttons',
                  f'Liczba widocznych przycisków ({visible_buttons_count}) przekracza dostępne miejsce ({max_available_slots}).\n\n'
                  f'Zwiększ liczbę rzędów lub przycisków w rzędzie, albo ukryj niektóre przyciski.')
            )
            logger.warning(f"Validation failed: {visible_buttons_count} visible buttons > {max_available_slots} available slots")
            return  # Nie zapisuj

        if checked_id == 1:
            # Przyciski góra, Zadania dół
            env_config = {
                'navbar_position': 'top',
                'taskbar_position': 'bottom',
                'taskbar_visible': taskbar_visible,
                'shortcut_toggle_nav': toggle_nav_shortcut,
                'rows_count': rows_count,
                'buttons_per_row': buttons_per_row,
                'buttons_config': buttons_config
            }
        elif checked_id == 2:
            # Zadania góra, Przyciski dół
            env_config = {
                'navbar_position': 'bottom',
                'taskbar_position': 'top',
                'taskbar_visible': taskbar_visible,
                'shortcut_toggle_nav': toggle_nav_shortcut,
                'rows_count': rows_count,
                'buttons_per_row': buttons_per_row,
                'buttons_config': buttons_config
            }
        else:
            # Domyślnie opcja 1
            env_config = {
                'navbar_position': 'top',
                'taskbar_position': 'bottom',
                'taskbar_visible': taskbar_visible,
                'shortcut_toggle_nav': toggle_nav_shortcut,
                'rows_count': rows_count,
                'buttons_per_row': buttons_per_row,
                'buttons_config': buttons_config
            }

        settings['environment'] = env_config
        save_settings(settings)

        # Emituj sygnał o zmianie
        self.settings_changed.emit({'environment': env_config})

        # Przeładuj globalne skróty klawiszowe
        self._reload_global_shortcuts(buttons_config)

        logger.info(f"Environment settings saved: {env_config}")

        # Pokaż komunikat
        QMessageBox.information(
            self,
            t('environment.saved_title', 'Zapisano'),
            t('environment.saved_message', 'Ustawienia środowiska zostały zapisane.\nGlobalne skróty klawiszowe zostały zaktualizowane.')
        )
    
    def _reload_global_shortcuts(self, buttons_config):
        """Przeładuj globalne skróty klawiszowe"""
        try:
            from ..utils.global_shortcuts import get_shortcuts_manager
            
            # Pobierz manager (jeśli już istnieje)
            shortcuts_manager = get_shortcuts_manager()
            
            # Załaduj nowe skróty
            shortcuts_manager.load_shortcuts_from_config(buttons_config)
            
            logger.info("Global shortcuts reloaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to reload global shortcuts: {e}")
    
    def _reset_to_defaults(self):
        """Przywróć domyślne ustawienia"""
        reply = QMessageBox.question(
            self,
            t('environment.reset_title', 'Przywróć domyślne'),
            t('environment.reset_message', 'Czy na pewno chcesz przywrócić domyślne ustawienia środowiska?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Domyślnie: Przyciski góra, Zadania dół, widoczny, skrót Ctrl+Shift+N
            self.layout_nav_top_task_bottom.setChecked(True)
            self.taskbar_visible_check.setChecked(True)
            self.toggle_nav_shortcut_edit.setText('Ctrl+Shift+N')
            self.rows_spinbox.setValue(2)
            self.buttons_per_row_spinbox.setValue(8)
            
            # Przywróć domyślne etykiety i widoczność przycisków
            for row, module in enumerate(self.builtin_modules):
                label_item = self.buttons_table.item(row, 1)
                description_item = self.buttons_table.item(row, 2)
                visible_item = self.buttons_table.item(row, 4)

                if label_item and not module['locked']:
                    label_item.setText(module['label'])

                if description_item and not module['locked']:
                    description_item.setText(module.get('description', ''))

                if visible_item and not module['locked']:
                    visible_item.setCheckState(Qt.CheckState.Checked if module['visible'] else Qt.CheckState.Unchecked)
            
            # Zapisz
            self._save_settings()
            
            logger.info("Environment settings reset to defaults")
    
    def update_translations(self):
        """Odśwież tłumaczenia"""
        # TODO: Zaimplementuj pełne odświeżanie wszystkich tekstów
        # Na razie tylko podstawowe elementy z fallbackami są już zaimplementowane w _setup_ui()
        logger.debug("Environment tab translations updated")
    
    def apply_theme(self):
        """Zastosuj aktualny motyw do widgetów w karcie środowiska"""
        from ..utils.theme_manager import get_theme_manager
        
        theme_manager = get_theme_manager()
        if not theme_manager:
            return
        
        try:
            colors = theme_manager.get_current_colors()
            
            # Style dla przycisków akcji
            button_style = f"""
                QPushButton {{
                    background-color: {colors.get('accent_primary', '#FF9800')};
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 16px;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {colors.get('accent_hover', '#F57C00')};
                }}
                QPushButton:pressed {{
                    background-color: {colors.get('accent_pressed', '#E65100')};
                }}
            """
            
            if hasattr(self, 'save_btn'):
                self.save_btn.setStyleSheet(button_style)
            
            if hasattr(self, 'reset_btn'):
                reset_style = f"""
                    QPushButton {{
                        background-color: {colors.get('bg_secondary', '#F5F5F5')};
                        color: {colors.get('text_primary', '#000000')};
                        border: 2px solid {colors.get('border_light', '#DDD')};
                        border-radius: 4px;
                        padding: 8px 16px;
                        font-weight: 600;
                    }}
                    QPushButton:hover {{
                        background-color: {colors.get('border_light', '#DDD')};
                    }}
                """
                self.reset_btn.setStyleSheet(reset_style)
            
            if hasattr(self, 'add_custom_button_btn'):
                self.add_custom_button_btn.setStyleSheet(button_style)
            
            logger.debug("[EnvironmentSettingsTab] Theme applied successfully")
            
        except Exception as e:
            logger.error(f"[EnvironmentSettingsTab] Error applying theme: {e}")


class AboutTab(QWidget):
    """Karta O aplikacji"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu karty O aplikacji"""
        # Główny layout z scroll area
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        # Widget wewnątrz scroll area
        scroll_widget = QWidget()
        scroll_layout = QVBoxLayout(scroll_widget)
        scroll_layout.setSpacing(20)
        scroll_layout.setContentsMargins(20, 20, 20, 20)
        
        # === LOGO I NAZWA ===
        header_layout = QVBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Nazwa aplikacji
        app_name = QLabel("PRO-Ka-Po")
        app_name_font = QFont()
        app_name_font.setPointSize(28)
        app_name_font.setBold(True)
        app_name.setFont(app_name_font)
        app_name.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(app_name)
        
        # Podtytuł
        subtitle = QLabel("Kaizen Freak Edition")
        subtitle_font = QFont()
        subtitle_font.setPointSize(14)
        subtitle_font.setItalic(True)
        subtitle.setFont(subtitle_font)
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(subtitle)
        
        # Wersja
        self.version_label = QLabel("Wersja 1.0.0")
        version_font = QFont()
        version_font.setPointSize(10)
        self.version_label.setFont(version_font)
        self.version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_layout.addWidget(self.version_label)
        
        scroll_layout.addLayout(header_layout)
        scroll_layout.addSpacing(20)
        
        # === OPIS ===
        desc_group = QGroupBox("O aplikacji")
        desc_layout = QVBoxLayout()
        
        self.description_label = QLabel(
            "PRO-Ka-Po to zestaw minimalistycznych narzędzi do organizacji pracy i zadań, "
            "pozwalający utrzymać wszystko w porządku. Idealna aplikacja do prac biurowych.\n\n"
            "Stworzona z myślą o pasjonatach KAIZEN i Lean Management."
        )
        self.description_label.setWordWrap(True)
        desc_font = QFont()
        desc_font.setPointSize(10)
        self.description_label.setFont(desc_font)
        desc_layout.addWidget(self.description_label)
        
        desc_group.setLayout(desc_layout)
        scroll_layout.addWidget(desc_group)
        
        # === AUTOR ===
        author_group = QGroupBox("Autor")
        author_layout = QVBoxLayout()
        
        self.author_label = QLabel(
            "<b>Piotr Prokop</b><br>"
            "📧 <a href='mailto:piotr.prokop@promirbud.eu' style='color: #2196F3;'>piotr.prokop@promirbud.eu</a>"
        )
        self.author_label.setOpenExternalLinks(True)
        self.author_label.setWordWrap(True)
        author_font = QFont()
        author_font.setPointSize(10)
        self.author_label.setFont(author_font)
        author_layout.addWidget(self.author_label)
        
        author_group.setLayout(author_layout)
        scroll_layout.addWidget(author_group)
        
        # === OPEN SOURCE ===
        opensource_group = QGroupBox("Open Source")
        opensource_layout = QVBoxLayout()
        
        self.opensource_label = QLabel(
            "Ta aplikacja ma otwarte źródło - zapraszam do rozwoju! 🚀\n\n"
            "Kod dostępny jest w repozytorium, możesz zgłaszać błędy, "
            "proponować nowe funkcje lub bezpośrednio współtworzyć projekt."
        )
        self.opensource_label.setWordWrap(True)
        opensource_font = QFont()
        opensource_font.setPointSize(10)
        self.opensource_label.setFont(opensource_font)
        opensource_layout.addWidget(self.opensource_label)
        
        opensource_group.setLayout(opensource_layout)
        scroll_layout.addWidget(opensource_group)
        
        # === WSPARCIE PROJEKTU ===
        support_group = QGroupBox("💝 Wsparcie projektu")
        support_layout = QVBoxLayout()
        
        self.support_label = QLabel(
            "Jeśli aplikacja Ci się podoba i chcesz wyrazić wdzięczność:\n\n"
            "Gdy będziesz rozglądał się za nowym domem lub innym budynkiem, "
            "odwiedź moją stronę - jestem producentem budynków modułowych:"
        )
        self.support_label.setWordWrap(True)
        support_font = QFont()
        support_font.setPointSize(10)
        self.support_label.setFont(support_font)
        support_layout.addWidget(self.support_label)
        
        # Link do strony
        website_btn = QPushButton("🏠 www.promir-bud.eu")
        website_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        website_btn.setMinimumHeight(40)
        website_btn.clicked.connect(lambda: self._open_website("https://www.promir-bud.eu"))
        support_layout.addWidget(website_btn)
        
        support_group.setLayout(support_layout)
        scroll_layout.addWidget(support_group)
        
        # === TECHNOLOGIE ===
        tech_group = QGroupBox("Technologie")
        tech_layout = QVBoxLayout()
        
        self.tech_label = QLabel(
            "• Python 3.11+\n"
            "• PyQt6 (GUI)\n"
            "• PostgreSQL (baza danych)\n"
            "• FastAPI (backend API)\n"
            "• OpenAI, Google Gemini, Groq (AI)"
        )
        self.tech_label.setWordWrap(True)
        tech_font = QFont()
        tech_font.setPointSize(10)
        self.tech_label.setFont(tech_font)
        tech_layout.addWidget(self.tech_label)
        
        tech_group.setLayout(tech_layout)
        scroll_layout.addWidget(tech_group)
        
        # === LICENCJA ===
        license_group = QGroupBox("Licencja")
        license_layout = QVBoxLayout()
        
        self.license_label = QLabel(
            "© 2025 Piotr Prokop\n\n"
            "Aplikacja udostępniona na licencji Open Source.\n"
            "Szczegóły w pliku LICENSE w katalogu projektu."
        )
        self.license_label.setWordWrap(True)
        license_font = QFont()
        license_font.setPointSize(9)
        self.license_label.setFont(license_font)
        license_layout.addWidget(self.license_label)
        
        license_group.setLayout(license_layout)
        scroll_layout.addWidget(license_group)
        
        # Spacer na końcu
        scroll_layout.addStretch()
        
        scroll.setWidget(scroll_widget)
        main_layout.addWidget(scroll)
        
        logger.info("[AboutTab] About tab initialized")
    
    def _open_website(self, url: str):
        """Otwórz stronę w przeglądarce"""
        from PyQt6.QtGui import QDesktopServices
        QDesktopServices.openUrl(QUrl(url))
        logger.info(f"[AboutTab] Opening website: {url}")
    
    def update_translations(self):
        """Odśwież tłumaczenia (obecnie tylko polski)"""
        # Placeholder dla przyszłych tłumaczeń
        pass
    
    def apply_theme(self):
        """Zastosuj motyw do karty About"""
        try:
            theme_manager = get_theme_manager()
            colors = theme_manager.get_current_colors()
            
            # Style dla przycisków
            button_style = f"""
                QPushButton {{
                    background-color: {colors.get('accent', '#2196F3')};
                    color: white;
                    border: none;
                    border-radius: 6px;
                    padding: 10px 20px;
                    font-size: 12pt;
                    font-weight: 600;
                }}
                QPushButton:hover {{
                    background-color: {colors.get('accent_hover', '#1976D2')};
                }}
                QPushButton:pressed {{
                    background-color: {colors.get('accent_pressed', '#0D47A1')};
                }}
            """
            
            # Zastosuj do wszystkich przycisków w widoku
            for button in self.findChildren(QPushButton):
                button.setStyleSheet(button_style)
            
            logger.debug("[AboutTab] Theme applied successfully")
            
        except Exception as e:
            logger.error(f"[AboutTab] Error applying theme: {e}")


class SettingsView(QWidget):
    """Główny widok ustawień z kartami"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu widoku ustawień"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget
        self.tabs = QTabWidget()
        
        # Karty
        self.tab_general = GeneralSettingsTab()
        self.tab_assistant = AssistantSettingsTab()
        self.tab_ai = AISettingsTab()
        self.tab_email = EmailSettingsCard()
        self.tab_environment = EnvironmentSettingsTab()
        self.tab_about = AboutTab()
        
        # Dodaj karty (zgodnie z menu użytkownika)
        self.tabs.addTab(self.tab_general, "Ogólne")
        self.tabs.addTab(self.tab_assistant, "Asystent")
        self.tabs.addTab(self.tab_ai, "AI")
        self.tabs.addTab(self.tab_email, "Konta E-mail")
        self.tabs.addTab(self.tab_environment, "Środowisko")
        self.tabs.addTab(self.tab_about, "O aplikacji")
        
        layout.addWidget(self.tabs)
        
        # Połącz sygnał zmiany ustawień Environment
        if hasattr(self.tab_environment, 'settings_changed'):
            self.tab_environment.settings_changed.connect(self._on_environment_changed)
        
        logger.info("Settings view initialized")
    
    def _on_environment_changed(self, changes: dict):
        """Przekaż zmiany environment do main_window przez tab_general"""
        if hasattr(self.tab_general, 'settings_changed'):
            self.tab_general.settings_changed.emit(changes)
            logger.info(f"Environment settings propagated to main window: {changes}")
    
    def _create_placeholder_tab(self, name: str) -> QWidget:
        """Utwórz placeholder dla karty"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        label = QLabel(f"Ustawienia {name}\n(W przygotowaniu)")
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont()
        font.setPointSize(14)
        label.setFont(font)
        
        layout.addWidget(label)
        
        return widget
    
    def update_translations(self):
        """Odśwież tłumaczenia w widoku ustawień"""
        # Nazwy zakładek (zgodne z indeksami w menu użytkownika)
        self.tabs.setTabText(0, t('settings.general', 'Ogólne'))
        self.tabs.setTabText(1, t('settings.assistant', 'Asystent'))
        self.tabs.setTabText(2, t('settings.ai', 'AI'))
        self.tabs.setTabText(3, t('settings.email_accounts', 'Konta E-mail'))
        self.tabs.setTabText(4, t('settings.environment', 'Środowisko'))
        self.tabs.setTabText(5, t('settings.about', 'O aplikacji'))
        
        # Odśwież karty
        self.tab_general.update_translations()
        self.tab_assistant.update_translations()
        self.tab_ai.update_translations()
        self.tab_environment.update_translations()
        self.tab_about.update_translations()
        
        logger.info("Settings view translations updated")
    
    def apply_theme(self):
        """Zastosuj motyw do widoku ustawień i wszystkich kart"""
        try:
            # Zastosuj motyw do każdej karty, która ma metodę apply_theme
            if hasattr(self.tab_general, 'apply_theme'):
                self.tab_general.apply_theme()
                logger.debug("[SettingsView] Applied theme to General tab")
            
            if hasattr(self.tab_assistant, 'apply_theme'):
                self.tab_assistant.apply_theme()
                logger.debug("[SettingsView] Applied theme to Assistant tab")
            
            if hasattr(self.tab_ai, 'apply_theme'):
                self.tab_ai.apply_theme()
                logger.debug("[SettingsView] Applied theme to AI tab")
            
            if hasattr(self.tab_email, 'apply_theme'):
                self.tab_email.apply_theme()
                logger.debug("[SettingsView] Applied theme to Email tab")
            
            if hasattr(self.tab_environment, 'apply_theme'):
                self.tab_environment.apply_theme()
                logger.debug("[SettingsView] Applied theme to Environment tab")
            
            if hasattr(self.tab_about, 'apply_theme'):
                self.tab_about.apply_theme()
                logger.debug("[SettingsView] Applied theme to About tab")
            
            logger.info("[SettingsView] Theme applied to all tabs successfully")
        except Exception as e:
            logger.error(f"[SettingsView] Error applying theme: {e}")
    
    def show_email_settings(self):
        """Przełącz na kartę ustawień kont e-mail"""
        # Znajdź indeks karty "Konta E-mail" (tab_email)
        for i in range(self.tabs.count()):
            if self.tabs.widget(i) == self.tab_email:
                self.tabs.setCurrentIndex(i)
                logger.info("[SettingsView] Switched to Email Accounts tab")
                break
