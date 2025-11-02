"""
Theme Manager Module
Handles application themes and styling
"""
from pathlib import Path
from typing import Optional
import json
from PyQt6.QtWidgets import QApplication
from loguru import logger

from ..core.config import config


class ThemeManager:
    """Manager for application themes and styling"""
    
    def __init__(self):
        self.current_theme: str = config.DEFAULT_THEME
        self.themes_dir: Path = config.THEMES_DIR
        self.custom_themes_dir: Path = self.themes_dir / "custom"
        self.custom_themes_dir.mkdir(parents=True, exist_ok=True)
        self._style_cache: dict[str, str] = {}
        
        # Layout management
        self.current_layout: int = 1  # 1 lub 2
        self.layout1_scheme: str = "light"  # Schemat dla układu 1
        self.layout2_scheme: str = "dark"   # Schemat dla układu 2
    
    def get_available_themes(self) -> list[str]:
        """Get list of available theme names (built-in + custom)"""
        themes = []
        
        # Built-in themes z plików .qss
        for qss_file in self.themes_dir.glob("*.qss"):
            theme_name = qss_file.stem
            themes.append(theme_name)
            logger.debug(f"Found built-in theme: {theme_name}")
        
        # Custom themes z folderu custom/
        if self.custom_themes_dir.exists():
            for qss_file in self.custom_themes_dir.glob("*.qss"):
                theme_name = qss_file.stem
                
                # Sprawdź metadata
                metadata_file = qss_file.parent / f"{theme_name}_metadata.json"
                if metadata_file.exists():
                    try:
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                            display_name = metadata.get('name', theme_name)
                            themes.append(f"⭐ {display_name}")
                            logger.debug(f"Found custom theme: {display_name}")
                    except Exception as e:
                        logger.error(f"Error reading metadata for {theme_name}: {e}")
                        themes.append(f"⭐ {theme_name}")
                else:
                    themes.append(f"⭐ {theme_name}")
        
        return themes
    
    def load_theme_file(self, theme_name: str) -> Optional[str]:
        """
        Load theme stylesheet from file
        
        Args:
            theme_name: Name of the theme (może zawierać prefix ⭐)
            
        Returns:
            QSS stylesheet content or None if not found
        """
        # Usuń prefix jeśli istnieje
        clean_name = theme_name.replace("⭐ ", "")
        
        # Check cache first
        if clean_name in self._style_cache:
            return self._style_cache[clean_name]
        
        # Sprawdź najpierw w custom themes
        custom_theme_file = self.custom_themes_dir / f"{clean_name}.qss"
        if custom_theme_file.exists():
            try:
                with open(custom_theme_file, "r", encoding="utf-8") as f:
                    stylesheet = f.read()
                    self._style_cache[clean_name] = stylesheet
                    logger.info(f"Loaded custom theme: {clean_name}")
                    return stylesheet
            except Exception as e:
                logger.error(f"Error loading custom theme {clean_name}: {e}")
        
        # Jeśli nie ma w custom, sprawdź built-in
        theme_file = self.themes_dir / f"{clean_name}.qss"
        
        if not theme_file.exists():
            logger.warning(f"Theme file not found: {theme_file}")
            return None
        
        try:
            with open(theme_file, "r", encoding="utf-8") as f:
                stylesheet = f.read()
                self._style_cache[clean_name] = stylesheet
                logger.info(f"Loaded built-in theme: {clean_name}")
                return stylesheet
        except Exception as e:
            logger.error(f"Error loading theme {clean_name}: {e}")
            return None
    
    def apply_theme(self, theme_name: str) -> bool:
        """
        Apply theme to the application
        
        Args:
            theme_name: Name of the theme to apply
            
        Returns:
            True if theme was applied successfully
        """
        stylesheet = self.load_theme_file(theme_name)
        
        if stylesheet is None:
            # Use default built-in style
            clean_name = theme_name.replace("⭐ ", "")
            stylesheet = self._get_default_stylesheet(clean_name)
        
        app = QApplication.instance()
        if app and isinstance(app, QApplication):
            app.setStyleSheet(stylesheet)
            self.current_theme = theme_name.replace("⭐ ", "")
            logger.info(f"Applied theme: {theme_name}")
            return True
        
        return False
    
    def _get_default_stylesheet(self, theme_name: str) -> str:
        """
        Get default built-in stylesheet
        
        Args:
            theme_name: Name of the theme
            
        Returns:
            Default QSS stylesheet
        """
        if theme_name == "dark":
            return self._get_dark_theme()
        elif theme_name == "light":
            return self._get_light_theme()
        else:
            return ""
    
    def _get_light_theme(self) -> str:
        """Get default light theme stylesheet"""
        return """
        /* Light Theme */
        QMainWindow {
            background-color: #f5f5f5;
        }
        
        QWidget {
            background-color: #ffffff;
            color: #212121;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
        }
        
        QPushButton {
            background-color: #2196F3;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #1976D2;
        }
        
        QPushButton:pressed {
            background-color: #0D47A1;
        }
        
        QPushButton:disabled {
            background-color: #BDBDBD;
        }
        
        QLineEdit {
            background-color: white;
            border: 1px solid #BDBDBD;
            border-radius: 4px;
            padding: 6px;
            color: #212121;
        }
        
        QLineEdit:focus {
            border: 2px solid #2196F3;
        }
        
        QTableView {
            background-color: white;
            alternate-background-color: #f5f5f5;
            gridline-color: #e0e0e0;
            border: 1px solid #BDBDBD;
        }
        
        QTableView::item:selected {
            background-color: #2196F3;
            color: white;
        }
        
        QHeaderView::section {
            background-color: #eeeeee;
            color: #212121;
            padding: 8px;
            border: none;
            border-bottom: 2px solid #2196F3;
            font-weight: bold;
        }
        
        QMenuBar {
            background-color: #ffffff;
            border-bottom: 1px solid #e0e0e0;
        }
        
        QMenuBar::item:selected {
            background-color: #e3f2fd;
        }
        
        QStatusBar {
            background-color: #f5f5f5;
            border-top: 1px solid #e0e0e0;
        }
        """
    
    def _get_dark_theme(self) -> str:
        """Get default dark theme stylesheet"""
        return """
        /* Dark Theme */
        QMainWindow {
            background-color: #1e1e1e;
        }
        
        QWidget {
            background-color: #2b2b2b;
            color: #e0e0e0;
            font-family: 'Segoe UI', Arial, sans-serif;
            font-size: 10pt;
        }
        
        QPushButton {
            background-color: #0d7377;
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
            min-width: 80px;
        }
        
        QPushButton:hover {
            background-color: #14FFEC;
            color: #1e1e1e;
        }
        
        QPushButton:pressed {
            background-color: #0a5a5d;
        }
        
        QPushButton:disabled {
            background-color: #424242;
            color: #757575;
        }
        
        QLineEdit {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 6px;
            color: #e0e0e0;
        }
        
        QLineEdit:focus {
            border: 2px solid #0d7377;
        }
        
        QTableView {
            background-color: #2b2b2b;
            alternate-background-color: #323232;
            gridline-color: #444444;
            border: 1px solid #555555;
            color: #e0e0e0;
        }
        
        QTableView::item:selected {
            background-color: #0d7377;
            color: white;
        }
        
        QHeaderView::section {
            background-color: #363636;
            color: #e0e0e0;
            padding: 8px;
            border: none;
            border-bottom: 2px solid #0d7377;
            font-weight: bold;
        }
        
        QMenuBar {
            background-color: #2b2b2b;
            border-bottom: 1px solid #444444;
        }
        
        QMenuBar::item:selected {
            background-color: #3c3c3c;
        }
        
        QStatusBar {
            background-color: #1e1e1e;
            border-top: 1px solid #444444;
        }
        """
    
    def get_current_theme(self) -> str:
        """Get name of currently applied theme"""
        return self.current_theme
    
    # === Layout Management ===
    
    def set_layout_scheme(self, layout_number: int, scheme_name: str):
        """
        Ustawia schemat dla danego układu
        
        Args:
            layout_number: Numer układu (1 lub 2)
            scheme_name: Nazwa schematu (może zawierać prefix ⭐)
        """
        clean_name = scheme_name.replace("⭐ ", "")
        if layout_number == 1:
            self.layout1_scheme = clean_name
            logger.debug(f"Set layout 1 scheme to: {clean_name}")
            # Zapisz do konfiguracji
            config.COLOR_SCHEME_1 = clean_name
        elif layout_number == 2:
            self.layout2_scheme = clean_name
            logger.debug(f"Set layout 2 scheme to: {clean_name}")
            # Zapisz do konfiguracji
            config.COLOR_SCHEME_2 = clean_name
    
    def get_layout_scheme(self, layout_number: int) -> str:
        """
        Pobiera schemat dla danego układu
        
        Args:
            layout_number: Numer układu (1 lub 2)
        
        Returns:
            Nazwa schematu
        """
        if layout_number == 1:
            return self.layout1_scheme
        return self.layout2_scheme
    
    def toggle_layout(self) -> int:
        """
        Przełącza między układem 1 a 2
        
        Returns:
            Numer aktualnego układu po przełączeniu
        """
        # Przełącz układ
        self.current_layout = 2 if self.current_layout == 1 else 1
        
        # Zastosuj odpowiedni schemat
        scheme = self.get_layout_scheme(self.current_layout)
        self.apply_theme(scheme)
        
        logger.info(f"Toggled to layout {self.current_layout} with scheme: {scheme}")
        
        return self.current_layout
    
    def get_current_layout(self) -> int:
        """Zwraca numer aktualnego układu (1 lub 2)"""
        return self.current_layout
    
    def apply_layout(self, layout_number: int):
        """
        Aplikuje konkretny układ
        
        Args:
            layout_number: Numer układu (1 lub 2)
        """
        self.current_layout = layout_number
        scheme = self.get_layout_scheme(layout_number)
        self.apply_theme(scheme)
        logger.info(f"Applied layout {layout_number} with scheme: {scheme}")


# Global singleton instance
_theme_manager_instance: Optional[ThemeManager] = None


def get_theme_manager() -> ThemeManager:
    """Get or create the global ThemeManager instance"""
    global _theme_manager_instance
    if _theme_manager_instance is None:
        _theme_manager_instance = ThemeManager()
    return _theme_manager_instance
