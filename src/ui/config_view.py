"""
Settings View - Widok ustawień aplikacji
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QLabel, QComboBox, QPushButton, QCheckBox,
    QLineEdit, QGroupBox, QScrollArea, QFrame,
    QMessageBox, QDialog, QFileDialog
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
        if dialog.exec() == QDialog.DialogCode.Accepted:
            logger.info("Custom color scheme created successfully")
            
            # Odśwież listę dostępnych motywów
            self._refresh_theme_lists()
            
            QMessageBox.information(
                self,
                t('dialog.info'),
                t('style_creator.scheme_created')
            )
    
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
        }
        
        # Ustaw wartości
        lang_index = language_map.get(settings.get('language', 'pl'), 0)
        self.combo_language.setCurrentIndex(lang_index)
        
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
        """Wypełnij combo boxy dźwiękami systemowymi i własnymi"""
        # Dźwięki systemowe (Windows)
        system_sounds = [
            ("Beep (domyślny)", "beep"),
            ("Ding", "ding"),
            ("Chord", "chord"),
            ("Pop", "pop"),
            ("Notify", "notify"),
            ("Asterisk", "asterisk"),
            ("Exclamation", "exclamation"),
            ("Question", "question"),
            ("Critical Stop", "critical"),
        ]
        
        # Dodaj dźwięki systemowe do obu combo
        for name, _ in system_sounds:
            self.combo_sound1.addItem(name)
            self.combo_sound2.addItem(name)
        
        # Załaduj własne dźwięki z ustawień
        settings = load_settings()
        custom_sounds = settings.get('custom_sounds', {})
        
        for name, path in custom_sounds.items():
            if os.path.exists(path):
                self.combo_sound1.addItem(f"⭐ {name}")
                self.combo_sound2.addItem(f"⭐ {name}")
                self.custom_sounds[name] = path
    
    def _browse_sound(self, sound_number: int):
        """Przeglądaj i dodaj własny plik dźwiękowy"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            t('settings.select_sound_file'),
            "",
            "Audio Files (*.wav *.mp3 *.ogg);;All Files (*.*)"
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
    
    def showEvent(self, event):
        """Wywoływane gdy widok jest pokazywany - odśwież combo języka"""
        super().showEvent(event)
        # Odśwież combo języka aby pokazywał aktualną wartość
        current_language = get_i18n().get_current_language()
        language_map = {
            'pl': 0,
            'en': 1,
            'de': 2,
        }
        lang_index = language_map.get(current_language, 0)
        self.combo_language.setCurrentIndex(lang_index)
    
    def _save_settings(self):
        """Zapisz ustawienia"""
        # Mapowanie języków
        language_codes = ['pl', 'en', 'de']
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
        self.show_main_label.setText(t('settings.shortcut_show_main'))
        
        # Przycisk zapisz
        self.btn_save.setText(t('button.save'))
        
        logger.info("Settings tab translations updated")


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
        self.tabs.addTab(self.tab_general, "Ogólne")
        
        # Placeholder dla pozostałych kart
        self.tabs.addTab(self._create_placeholder_tab("Zadania"), "Zadania")
        self.tabs.addTab(self._create_placeholder_tab("Kanban"), "Kanban")
        self.tabs.addTab(self._create_placeholder_tab("Własne"), "Własne")
        self.tabs.addTab(self._create_placeholder_tab("Transkryptor"), "Transkryptor")
        self.tabs.addTab(self._create_placeholder_tab("AI"), "AI")
        self.tabs.addTab(self._create_placeholder_tab("O aplikacji"), "O aplikacji")
        
        layout.addWidget(self.tabs)
        
        logger.info("Settings view initialized")
    
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
        # Nazwy zakładek
        self.tabs.setTabText(0, t('settings.general'))
        self.tabs.setTabText(1, t('settings.tasks'))
        self.tabs.setTabText(2, t('settings.kanban'))
        self.tabs.setTabText(3, t('settings.custom'))
        self.tabs.setTabText(4, t('settings.transcriptor'))
        self.tabs.setTabText(5, t('settings.ai'))
        self.tabs.setTabText(6, t('settings.about'))
        
        # Odśwież kartę ogólną
        self.tab_general.update_translations()
        
        logger.info("Settings view translations updated")
