"""
Main entry point for PRO-Ka-Po Kaizen Freak Application
"""
import sys
from pathlib import Path

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from loguru import logger

# Add src directory to path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.config import config, ensure_directories
from src.utils.theme_manager import ThemeManager
from src.utils.i18n_manager import I18nManager


def setup_logging() -> None:
    """Configure application logging"""
    # Remove default logger
    logger.remove()
    
    # Add console logger
    logger.add(
        sys.stderr,
        format=config.LOG_FORMAT,
        level=config.LOG_LEVEL,
        colorize=True,
    )
    
    # Add file logger
    log_file = config.LOGS_DIR / "kaizen_freak.log"
    logger.add(
        log_file,
        format=config.LOG_FORMAT,
        level=config.LOG_LEVEL,
        rotation=config.LOG_ROTATION,
        retention=config.LOG_RETENTION,
        encoding="utf-8",
    )
    
    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")


def main() -> int:
    """Main application entry point"""
    try:
        # Setup
        ensure_directories()
        setup_logging()
        
        # Create application
        app = QApplication(sys.argv)
        app.setApplicationName(config.APP_NAME)
        app.setApplicationVersion(config.APP_VERSION)
        app.setOrganizationName(config.APP_AUTHOR)
        
        # Initialize managers
        theme_manager = ThemeManager()
        i18n_manager = I18nManager()
        
        # Load saved settings to get color schemes
        from src.core.config import load_settings
        settings = load_settings()
        
        # Set layout schemes from settings
        layout1_scheme = settings.get('color_scheme_1', 'light')
        layout2_scheme = settings.get('color_scheme_2', 'dark')
        theme_manager.set_layout_scheme(1, layout1_scheme)
        theme_manager.set_layout_scheme(2, layout2_scheme)
        
        # Apply saved layout (default to 1 if not set)
        current_layout = settings.get('current_layout', 1)
        theme_manager.apply_layout(current_layout)
        
        # Set language from settings
        saved_language = settings.get('language', config.DEFAULT_LANGUAGE)
        i18n_manager.set_language(saved_language)
        
        logger.info("Application initialized successfully")
        logger.info(f"Layout: {current_layout}, Language: {saved_language}")
        
        # Check if user is logged in
        from src.ui.auth_window import AuthWindow
        from src.ui.main_window import MainWindow
        import json
        
        tokens_file = config.DATA_DIR / "tokens.json"
        user_logged_in = False
        user_data = None
        
        if tokens_file.exists():
            try:
                with open(tokens_file, 'r') as f:
                    token_data = json.load(f)
                    if token_data.get('access_token'):
                        user_logged_in = True
                        user_data = token_data.get('user_data', {})
                        logger.info(f"User already logged in: {user_data.get('email', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Failed to load tokens: {e}")
        
        # If not logged in, show auth window first
        if not user_logged_in:
            logger.info("No valid login found, showing authentication window")
            auth_window = AuthWindow()
            
            # Create main window but don't show it yet
            main_window = MainWindow()
            
            def on_login_success(user_data):
                logger.info(f"User logged in: {user_data.get('email', 'Unknown')}")
                auth_window.close()
                main_window.set_user_data(user_data)  # Przekaż dane użytkownika
                main_window.show()
            
            auth_window.login_successful.connect(on_login_success)
            auth_window.show()
        else:
            # User already logged in, show main window directly
            logger.info("User already authenticated, showing main window")
            main_window = MainWindow()
            if user_data:
                main_window.set_user_data(user_data)
            main_window.show()
        
        # Run application
        return app.exec()
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
