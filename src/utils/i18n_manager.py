"""
Internationalization (i18n) Manager Module
Handles multi-language support
"""
import json
from pathlib import Path
from typing import Dict, Optional
from loguru import logger
from PyQt6.QtCore import QObject, pyqtSignal

from ..core.config import config


class I18nManager(QObject):
    """Manager for application internationalization"""
    
    language_changed = pyqtSignal(str)  # Sygnał emitowany przy zmianie języka
    
    def __init__(self):
        super().__init__()
        self.current_language: str = config.DEFAULT_LANGUAGE
        self.i18n_dir: Path = config.I18N_DIR
        self._translations: Dict[str, Dict[str, str]] = {}
        self._load_all_translations()
    
    def _load_all_translations(self) -> None:
        """Load all available translation files"""
        for lang in config.AVAILABLE_LANGUAGES:
            self._load_language(lang)
    
    def _load_language(self, language_code: str) -> bool:
        """
        Load translation file for specified language
        
        Args:
            language_code: Language code (e.g., 'en', 'pl', 'de')
            
        Returns:
            True if loaded successfully
        """
        lang_file = self.i18n_dir / f"{language_code}.json"
        
        if not lang_file.exists():
            logger.warning(f"Translation file not found: {lang_file}")
            # Create default translation file
            self._create_default_translation(language_code)
            return False
        
        try:
            with open(lang_file, "r", encoding="utf-8") as f:
                self._translations[language_code] = json.load(f)
                logger.info(f"Loaded translations for: {language_code}")
                return True
        except Exception as e:
            logger.error(f"Error loading translations for {language_code}: {e}")
            return False
    
    def _create_default_translation(self, language_code: str) -> None:
        """
        Create default translation file
        
        Args:
            language_code: Language code
        """
        default_translations = self._get_default_translations(language_code)
        
        lang_file = self.i18n_dir / f"{language_code}.json"
        try:
            with open(lang_file, "w", encoding="utf-8") as f:
                json.dump(default_translations, f, ensure_ascii=False, indent=2)
                self._translations[language_code] = default_translations
                logger.info(f"Created default translation file: {lang_file}")
        except Exception as e:
            logger.error(f"Error creating default translation file: {e}")
    
    def _get_default_translations(self, language_code: str) -> Dict[str, str]:
        """
        Get default translations for a language
        
        Args:
            language_code: Language code
            
        Returns:
            Dictionary with default translations
        """
        translations = {
            "pl": {
                "app.title": "Menedżer Zadań",
                "app.welcome": "Witaj w Menedżerze Zadań",
                "menu.file": "&Plik",
                "menu.edit": "&Edycja",
                "menu.view": "&Widok",
                "menu.tools": "&Narzędzia",
                "menu.help": "Pomo&c",
                "menu.exit": "Wyjście",
                "menu.settings": "Ustawienia",
                "nav.tasks": "Zadania",
                "nav.calendar": "Kalendarz",
                "nav.reports": "Raporty",
                "nav.settings": "Ustawienia",
                "auth.login": "Zaloguj się",
                "auth.register": "Zarejestruj się",
                "auth.logout": "Wyloguj",
                "auth.username": "Nazwa użytkownika",
                "auth.password": "Hasło",
                "auth.email": "Email",
                "button.save": "Zapisz",
                "button.cancel": "Anuluj",
                "button.delete": "Usuń",
                "button.edit": "Edytuj",
                "button.add": "Dodaj",
                "button.close": "Zamknij",
                "status.ready": "Gotowy",
                "status.loading": "Ładowanie...",
                "error.general": "Wystąpił błąd",
                # Pomodoro
                "pomodoro.session_title": "Sesja pracy",
                "pomodoro.short_break_title": "Krótka przerwa",
                "pomodoro.long_break_title": "Długa przerwa",
                "pomodoro.general_topic": "Ogólna",
                "pomodoro.set_title_btn": "Nadaj tytuł",
                "pomodoro.today_sessions": "Dziś wykonano {count} długich sesji",
                "pomodoro.short_session": "Sesja krótka {current}/{total}",
                "pomodoro.btn_start": "▶ Start",
                "pomodoro.btn_pause": "⏸ Pauza",
                "pomodoro.btn_reset": "↻ Reset",
                "pomodoro.btn_skip": "⏭ Pomiń",
                "pomodoro.btn_stop": "⏹ Stop",
                "pomodoro.times_section": "Czasy sesji",
                "pomodoro.work_duration": "Czas pracy:",
                "pomodoro.short_break": "Krótka przerwa:",
                "pomodoro.long_break": "Długa przerwa:",
                "pomodoro.sessions_count": "Sesje do długiej przerwy:",
                "pomodoro.auto_section": "Opcje automatyczne",
                "pomodoro.auto_breaks": "Automatycznie rozpoczynaj przerwy",
                "pomodoro.auto_pomodoro": "Automatycznie rozpoczynaj następne Pomodoro",
                "pomodoro.sounds_section": "Powiadomienia",
                "pomodoro.sound_work_end": "Odtwarzaj dźwięk po zakończeniu sesji pracy",
                "pomodoro.sound_break_end": "Odtwarzaj dźwięk po zakończeniu przerwy",
                "pomodoro.popup_timer": "Otwórz licznik w popup",
                "pomodoro.stats_today": "Statystyki dzisiejsze",
                "pomodoro.completed_sessions": "Ukończone sesje",
                "pomodoro.total_focus_time": "Całkowity czas skupienia",
                "pomodoro.show_logs": "Pokaż logi",
                "pomodoro.motivation_1": "Mały postęp każdego dnia prowadzi do wielkich rezultatów",
                "pomodoro.motivation_2": "Skupienie to klucz do mistrzostwa",
                "pomodoro.motivation_3": "Każda sesja przybliża Cię do celu",
                "pomodoro.motivation_4": "Konsekwencja bije talent",
                "pomodoro.motivation_5": "Jedna rzecz na raz - to jest droga",
            },
            "en": {
                "app.title": "Task Manager",
                "app.welcome": "Welcome to Task Manager",
                "menu.file": "&File",
                "menu.edit": "&Edit",
                "menu.view": "&View",
                "menu.tools": "&Tools",
                "menu.help": "&Help",
                "menu.exit": "Exit",
                "menu.settings": "Settings",
                "nav.tasks": "Tasks",
                "nav.calendar": "Calendar",
                "nav.reports": "Reports",
                "nav.settings": "Settings",
                "auth.login": "Login",
                "auth.register": "Register",
                "auth.logout": "Logout",
                "auth.username": "Username",
                "auth.password": "Password",
                "auth.email": "Email",
                "button.save": "Save",
                "button.cancel": "Cancel",
                "button.delete": "Delete",
                "button.edit": "Edit",
                "button.add": "Add",
                "status.ready": "Ready",
                "status.loading": "Loading...",
                "error.general": "An error occurred",
            },
            "de": {
                "app.title": "Aufgabenmanager",
                "app.welcome": "Willkommen beim Aufgabenmanager",
                "menu.file": "&Datei",
                "menu.edit": "&Bearbeiten",
                "menu.view": "&Ansicht",
                "menu.tools": "&Werkzeuge",
                "menu.help": "&Hilfe",
                "menu.exit": "Beenden",
                "menu.settings": "Einstellungen",
                "nav.tasks": "Aufgaben",
                "nav.calendar": "Kalender",
                "nav.reports": "Berichte",
                "nav.settings": "Einstellungen",
                "auth.login": "Anmelden",
                "auth.register": "Registrieren",
                "auth.logout": "Abmelden",
                "auth.username": "Benutzername",
                "auth.password": "Passwort",
                "auth.email": "E-Mail",
                "button.save": "Speichern",
                "button.cancel": "Abbrechen",
                "button.delete": "Löschen",
                "button.edit": "Bearbeiten",
                "button.add": "Hinzufügen",
                "status.ready": "Bereit",
                "status.loading": "Lädt...",
                "error.general": "Ein Fehler ist aufgetreten",
            },
        }
        
        return translations.get(language_code, translations["en"])
    
    def get_available_languages(self) -> list[str]:
        """Get list of available language codes"""
        return config.AVAILABLE_LANGUAGES
    
    def set_language(self, language_code: str) -> bool:
        """
        Set current application language
        
        Args:
            language_code: Language code to set
            
        Returns:
            True if language was set successfully
        """
        if language_code not in self.get_available_languages():
            logger.warning(f"Language {language_code} not available")
            return False
        
        if language_code not in self._translations:
            self._load_language(language_code)
        
        old_language = self.current_language
        self.current_language = language_code
        
        # Zapisz do konfiguracji
        config.DEFAULT_LANGUAGE = language_code
        
        logger.info(f"Language changed from {old_language} to: {language_code}")
        
        # Emituj sygnał o zmianie języka
        self.language_changed.emit(language_code)
        
        return True
    
    def translate(self, key: str, default: Optional[str] = None) -> str:
        """
        Get translation for a key
        
        Args:
            key: Translation key (e.g., 'app.title')
            default: Default value if translation not found
            
        Returns:
            Translated string or default value
        """
        translations = self._translations.get(self.current_language, {})
        return translations.get(key, default or key)
    
    def t(self, key: str, default: Optional[str] = None) -> str:
        """
        Shorthand for translate()
        
        Args:
            key: Translation key
            default: Default value if translation not found
            
        Returns:
            Translated string
        """
        return self.translate(key, default)
    
    def get_current_language(self) -> str:
        """Get current language code"""
        return self.current_language


# Global i18n instance
_i18n_instance: Optional[I18nManager] = None


def get_i18n() -> I18nManager:
    """Get global i18n manager instance"""
    global _i18n_instance
    if _i18n_instance is None:
        _i18n_instance = I18nManager()
    return _i18n_instance


def t(key: str, default: Optional[str] = None) -> str:
    """
    Global translation function
    
    Args:
        key: Translation key
        default: Default value if translation not found
        
    Returns:
        Translated string
    """
    return get_i18n().translate(key, default)
