"""
Main entry point for PRO-Ka-Po Kaizen Freak Application
"""
import sys
from pathlib import Path

# WAŻNE: Import QtWebEngine PRZED utworzeniem QApplication
# Musi być na samym początku, przed innymi importami PyQt6
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineProfile
except ImportError:
    # QtWebEngine nie jest zainstalowany - aplikacja będzie działać bez modułu P-Web
    pass

from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt
from loguru import logger
import faulthandler

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
        level="DEBUG",  # TYMCZASOWO dla debugowania email scanera
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
    # Enable faulthandler and periodically dump thread stacks to a file so
    # we can diagnose hangs. Keep the file handle alive in a module-global
    # variable to avoid it being closed by GC.
    try:
        stack_file = config.LOGS_DIR / "stacktraces.log"
        # open in append mode so previous traces are preserved
        fh = open(stack_file, "a", encoding="utf-8")
        faulthandler.enable(file=fh)
        # Dump tracebacks every 30s if the interpreter is blocked
        faulthandler.dump_traceback_later(30, repeat=True, file=fh)
        # store reference so file isn't closed
        global _faulthandler_file
        _faulthandler_file = fh
        logger.info(f"Faulthandler enabled - periodic stack dumps -> {stack_file}")
    except Exception as e:
        logger.warning(f"Failed to enable faulthandler periodic dumps: {e}")


def save_tokens(access_token: str, refresh_token: str, user_data: dict | None = None) -> None:
    """
    Zapisz tokeny do pliku tokens.json i zaktualizuj WebSocket connections.
    
    Args:
        access_token: Nowy access token
        refresh_token: Nowy refresh token
        user_data: Opcjonalne dane użytkownika (jeśli None, zachowa istniejące)
    """
    import json
    
    tokens_file = config.DATA_DIR / "tokens.json"
    
    # Jeśli user_data nie podano, spróbuj zachować istniejące
    if user_data is None and tokens_file.exists():
        try:
            with open(tokens_file, 'r') as f:
                existing_data = json.load(f)
                user_data = existing_data.get('user_data', {})
        except:
            user_data = {}
    
    # Zapisz nowe tokeny
    token_data = {
        'access_token': access_token,
        'refresh_token': refresh_token,
        'user_data': user_data or {}
    }
    
    tokens_file.parent.mkdir(parents=True, exist_ok=True)
    with open(tokens_file, 'w') as f:
        json.dump(token_data, f, indent=2)
    
    logger.info("✅ Tokens saved to file")
    
    # 🔧 DODAJ: Powiadom wszystkie aktywne WebSocket connections o nowym tokenie
    try:
        from PyQt6.QtWidgets import QApplication
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            # Znajdź główne okno aplikacji i zaktualizuj WebSocket connections
            main_windows = [w for w in app.topLevelWidgets() if w.__class__.__name__ == 'MainWindow']
            
            for main_window in main_windows:
                # MainWindow -> alarms_view -> alarms_logic -> ws_client
                alarms_view = getattr(main_window, 'alarms_view', None)
                if alarms_view:
                    alarms_logic = getattr(alarms_view, 'alarms_logic', None)
                    if alarms_logic:
                        ws_client = getattr(alarms_logic, 'ws_client', None)
                        if ws_client:
                            ws_client.update_token(access_token)
                            logger.info("🔗 Updated Alarms WebSocket token")
                        
                # MainWindow -> pomodoro_view -> logic -> ws_client (jeśli istnieje)
                pomodoro_view = getattr(main_window, 'pomodoro_view', None)
                if pomodoro_view:
                    pomodoro_logic = getattr(pomodoro_view, 'logic', None)
                    if pomodoro_logic:
                        ws_client = getattr(pomodoro_logic, 'ws_client', None)
                        if ws_client:
                            ws_client.update_token(access_token)
                            logger.info("🔗 Updated Pomodoro WebSocket token")
                        
    except Exception as e:
        logger.warning(f"⚠️ Failed to update WebSocket tokens: {e}")
        
    logger.success("🔄 Token refresh completed - all WebSocket connections updated")


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
                        # Dodaj access_token i refresh_token do user_data aby umożliwić synchronizację
                        user_data['access_token'] = token_data.get('access_token')
                        user_data['refresh_token'] = token_data.get('refresh_token')
                        logger.info(f"User already logged in: {user_data.get('email', 'Unknown')}")
            except Exception as e:
                logger.warning(f"Failed to load tokens: {e}")
        
        # If not logged in, show auth window first
        if not user_logged_in:
            logger.info("No valid login found, showing authentication window")
            auth_window = AuthWindow()
            
            # Create main window but don't show it yet
            main_window = MainWindow(on_token_refreshed=save_tokens)
            
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
            main_window = MainWindow(on_token_refreshed=save_tokens)
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
