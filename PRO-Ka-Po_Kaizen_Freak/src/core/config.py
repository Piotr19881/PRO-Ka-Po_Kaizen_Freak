"""
Application Configuration Module
"""
import sys
import json
from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field
from loguru import logger

# Determine BASE_DIR in a packaging-aware way (works for dev and PyInstaller 'frozen' exe)
if getattr(sys, "frozen", False):
    # Running as a bundled executable (PyInstaller)
    _BASE_DIR = Path(sys.executable).parent
else:
    # Running from source (DEV)
    _BASE_DIR = Path(__file__).resolve().parent.parent.parent


class AppConfig(BaseSettings):
    """Application configuration settings"""
    
    # Application Info
    APP_NAME: str = "PRO-Ka-Po Kaizen Freak"
    APP_VERSION: str = "0.1.0"
    APP_AUTHOR: str = "PRO-Ka-Po Team"
    
    # Paths
    BASE_DIR: Path = _BASE_DIR
    RESOURCES_DIR: Path = BASE_DIR / "resources"
    I18N_DIR: Path = RESOURCES_DIR / "i18n"
    THEMES_DIR: Path = RESOURCES_DIR / "themes"
    ICONS_DIR: Path = RESOURCES_DIR / "icons"
    DATA_DIR: Path = BASE_DIR / "data"
    LOGS_DIR: Path = BASE_DIR / "logs"
    
    # Database
    # Ensure DATABASE_URL points to the packaging-aware data folder
    DATABASE_URL: str = Field(
        default=f"sqlite:///{str(_BASE_DIR / 'data' / 'kaizen_freak.db')}",
        description="Database connection URL"
    )

    # API Base URL (for tasks sync)
    API_BASE_URL: str = Field(
        default="https://prokapo-server-render-1.onrender.com",
        description="API base URL for server communication"
    )
    
    # UI Settings
    DEFAULT_LANGUAGE: str = "pl"
    AVAILABLE_LANGUAGES: list = ["pl", "en", "de", "es", "ja", "zh"]
    DEFAULT_THEME: str = "light"
    AVAILABLE_THEMES: list = ["light", "dark", "custom"]
    
    # Window Settings
    WINDOW_TITLE: str = "PRO-Ka-Po Kaizen Freak"
    WINDOW_MIN_WIDTH: int = 1024
    WINDOW_MIN_HEIGHT: int = 768
    WINDOW_DEFAULT_WIDTH: int = 1280
    WINDOW_DEFAULT_HEIGHT: int = 900
    
    # Security
    SECRET_KEY: str = Field(
        default="change-me-in-production",
        description="Secret key for encryption"
    )
    SESSION_TIMEOUT: int = Field(
        default=3600,
        description="Session timeout in seconds"
    )
    PASSWORD_MIN_LENGTH: int = 8
    PASSWORD_REQUIRE_UPPERCASE: bool = True
    PASSWORD_REQUIRE_LOWERCASE: bool = True
    PASSWORD_REQUIRE_NUMBERS: bool = True
    PASSWORD_REQUIRE_SPECIAL: bool = True
    
    # Logging
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan> - <level>{message}</level>"
    LOG_ROTATION: str = "10 MB"
    LOG_RETENTION: str = "1 month"
    
    # System Settings
    AUTO_START: bool = False
    RUN_IN_BACKGROUND: bool = True
    ENABLE_NOTIFICATIONS: bool = True
    ENABLE_SOUND: bool = True
    
    # Keyboard Shortcuts
    SHORTCUT_QUICK_ADD: str = "Ctrl+N"
    SHORTCUT_SHOW_MAIN: str = "Ctrl+Shift+K"
    
    # Color Schemes (presets)
    COLOR_SCHEME_1: str = "default"
    COLOR_SCHEME_2: str = "default"
    CUSTOM_COLOR_SCHEME: dict = {}
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = True
        extra = "allow"  # Pozwól na dodatkowe pola z .env


# Global configuration instance
config = AppConfig()


def get_config() -> AppConfig:
    """Get application configuration instance"""
    return config


def ensure_directories() -> None:
    """Create necessary directories if they don't exist"""
    directories = [
        config.DATA_DIR,
        config.LOGS_DIR,
        config.I18N_DIR,
        config.THEMES_DIR,
        config.ICONS_DIR,
    ]
    
    for directory in directories:
        directory.mkdir(parents=True, exist_ok=True)


# Initialize directories on import
ensure_directories()


def save_settings(settings_dict: dict) -> bool:
    """
    Save settings to configuration file
    
    Args:
        settings_dict: Dictionary with settings to save
        
    Returns:
        True if saved successfully
    """
    try:
        settings_file = config.BASE_DIR / "user_settings.json"
        
        # Load existing settings or create new
        existing_settings = {}
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                existing_settings = json.load(f)
        
        # Update with new settings
        existing_settings.update(settings_dict)
        
        # Save to file
        with open(settings_file, 'w', encoding='utf-8') as f:
            json.dump(existing_settings, f, indent=4, ensure_ascii=False)
        
        # Update config instance
        if 'language' in settings_dict:
            config.DEFAULT_LANGUAGE = settings_dict['language']
        if 'theme' in settings_dict:
            config.DEFAULT_THEME = settings_dict['theme']
        if 'auto_start' in settings_dict:
            config.AUTO_START = settings_dict['auto_start']
        if 'run_in_background' in settings_dict:
            config.RUN_IN_BACKGROUND = settings_dict['run_in_background']
        if 'enable_notifications' in settings_dict:
            config.ENABLE_NOTIFICATIONS = settings_dict['enable_notifications']
        if 'enable_sound' in settings_dict:
            config.ENABLE_SOUND = settings_dict['enable_sound']
        if 'shortcut_quick_add' in settings_dict:
            config.SHORTCUT_QUICK_ADD = settings_dict['shortcut_quick_add']
        if 'shortcut_show_main' in settings_dict:
            config.SHORTCUT_SHOW_MAIN = settings_dict['shortcut_show_main']
        if 'color_scheme_1' in settings_dict:
            config.COLOR_SCHEME_1 = settings_dict['color_scheme_1']
        if 'color_scheme_2' in settings_dict:
            config.COLOR_SCHEME_2 = settings_dict['color_scheme_2']
        
        logger.info(f"Settings saved successfully to {settings_file}")
        return True
    except Exception as e:
        logger.error(f"Error saving settings: {e}")
        return False


def load_settings() -> dict:
    """
    Load settings from configuration file
    
    Returns:
        Dictionary with current settings
    """
    try:
        settings_file = config.BASE_DIR / "user_settings.json"
        
        # Default current_layout
        current_layout = 1
        remember_me = False
        
        # Load from file if exists
        if settings_file.exists():
            with open(settings_file, 'r', encoding='utf-8') as f:
                saved_settings = json.load(f)
                
            # Update config instance
            if 'language' in saved_settings:
                config.DEFAULT_LANGUAGE = saved_settings['language']
            if 'theme' in saved_settings:
                config.DEFAULT_THEME = saved_settings['theme']
            if 'auto_start' in saved_settings:
                config.AUTO_START = saved_settings['auto_start']
            if 'run_in_background' in saved_settings:
                config.RUN_IN_BACKGROUND = saved_settings['run_in_background']
            if 'enable_notifications' in saved_settings:
                config.ENABLE_NOTIFICATIONS = saved_settings['enable_notifications']
            if 'enable_sound' in saved_settings:
                config.ENABLE_SOUND = saved_settings['enable_sound']
            if 'shortcut_quick_add' in saved_settings:
                config.SHORTCUT_QUICK_ADD = saved_settings['shortcut_quick_add']
            if 'shortcut_show_main' in saved_settings:
                config.SHORTCUT_SHOW_MAIN = saved_settings['shortcut_show_main']
            if 'color_scheme_1' in saved_settings:
                config.COLOR_SCHEME_1 = saved_settings['color_scheme_1']
            if 'color_scheme_2' in saved_settings:
                config.COLOR_SCHEME_2 = saved_settings['color_scheme_2']
            if 'current_layout' in saved_settings:
                current_layout = saved_settings['current_layout']
            if 'remember_me' in saved_settings:
                remember_me = saved_settings['remember_me']
            
            # Return all saved settings (including environment)
            logger.debug(f"Loaded settings from file: {saved_settings}")
            return saved_settings
        
        # Return default settings if file doesn't exist
        logger.warning("Settings file not found, using defaults")
        return {
            'language': config.DEFAULT_LANGUAGE,
            'theme': config.DEFAULT_THEME,
            'current_layout': current_layout,
            'remember_me': remember_me,
            'auto_start': config.AUTO_START,
            'run_in_background': config.RUN_IN_BACKGROUND,
            'enable_notifications': config.ENABLE_NOTIFICATIONS,
            'enable_sound': config.ENABLE_SOUND,
            'shortcut_quick_add': config.SHORTCUT_QUICK_ADD,
            'shortcut_show_main': config.SHORTCUT_SHOW_MAIN,
            'color_scheme_1': config.COLOR_SCHEME_1,
            'color_scheme_2': config.COLOR_SCHEME_2,
        }
    except Exception as e:
        logger.error(f"Error loading settings: {e}")
        return {
            'language': 'pl',
            'theme': 'light',
            'current_layout': 1,
            'remember_me': False,
            'auto_start': False,
            'run_in_background': True,
            'enable_notifications': True,
            'enable_sound': True,
            'shortcut_quick_add': 'Ctrl+N',
            'shortcut_show_main': 'Ctrl+Shift+K',
            'color_scheme_1': 'default',
            'color_scheme_2': 'default',
        }
