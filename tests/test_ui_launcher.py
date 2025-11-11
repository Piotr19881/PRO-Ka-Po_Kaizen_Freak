"""
UI Test Launcher - Szybkie testowanie dialogów i widoków z różnymi motywami
Umożliwia uruchamianie pojedynczych komponentów UI bez ładowania całej aplikacji
"""

import sys
from pathlib import Path
from typing import Optional, Callable, Dict, Any

# Dodaj ścieżkę do src
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QScrollArea, QGroupBox, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from src.utils.theme_manager import ThemeManager, get_theme_manager
from src.utils.i18n_manager import I18nManager


class UITestLauncher(QMainWindow):
    """Okno główne launchera testów UI"""
    
    def __init__(self):
        super().__init__()
        self.theme_manager = get_theme_manager()
        self.i18n_manager = I18nManager()
        self.active_dialogs = []  # Lista otwartych dialogów
        
        self.setWindowTitle("🧪 UI Test Launcher - Theme Testing")
        self.setMinimumSize(900, 700)
        
        self._init_ui()
        self._load_available_themes()
        self.apply_theme()
        
    def _init_ui(self):
        """Inicjalizacja interfejsu"""
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("🎨 UI Component Theme Tester")
        header.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(header)
        
        # Theme selector
        theme_group = self._create_theme_selector()
        layout.addWidget(theme_group)
        
        # Scroll area dla przycisków
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(10)
        
        # Grupa 1: AI & Asystent
        self._add_group(scroll_layout, "🤖 AI & Asystent", [
            ("AI Settings", self._test_ai_settings),
            ("AI Summary Dialog", self._test_ai_summary_dialog),
            ("AI Task Communication Dialog", self._test_ai_task_communication),
            ("Assistant Settings", self._test_assistant_settings),
        ])
        
        # Grupa 2: Główne widoki
        self._add_group(scroll_layout, "📋 Główne widoki", [
            ("Main Window", self._test_main_window),
            ("Navigation Bar", self._test_navigation_bar),
            ("Task View", self._test_task_view),
            ("Kanban View", self._test_kanban_view),
            ("Note View", self._test_note_view),
            ("Pomodoro View", self._test_pomodoro_view),
            ("Alarms View", self._test_alarms_view),
            ("QuickBoard View", self._test_quickboard_view),
        ])
        
        # Grupa 3: Moduły specjalistyczne
        self._add_group(scroll_layout, "🔧 Moduły specjalistyczne", [
            ("CallCryptor View", self._test_callcryptor_view),
            ("CallCryptor Dialogs", self._test_callcryptor_dialogs),
            ("ProApp View", self._test_pro_app_view),
            ("Web View", self._test_web_view),
        ])
        
        # Grupa 4: Dialogi
        self._add_group(scroll_layout, "💬 Dialogi", [
            ("Style Creator Dialog", self._test_style_creator),
            ("Config View", self._test_config_view),
            ("Task Config Dialog", self._test_task_config),
            ("Tag Manager", self._test_tag_manager),
        ])
        
        scroll_layout.addStretch()
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        
        # Footer
        footer = QLabel("💡 Wybierz motyw i kliknij przycisk komponentu do przetestowania")
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setObjectName("footerLabel")
        layout.addWidget(footer)
        
    def _create_theme_selector(self) -> QGroupBox:
        """Tworzy grupę wyboru motywu"""
        group = QGroupBox("🎨 Wybór motywu do testowania")
        layout = QHBoxLayout(group)
        
        layout.addWidget(QLabel("Aktualny motyw:"))
        
        self.theme_combo = QComboBox()
        self.theme_combo.setMinimumWidth(250)
        layout.addWidget(self.theme_combo)
        
        apply_btn = QPushButton("✓ Zastosuj motyw")
        apply_btn.clicked.connect(self._apply_selected_theme)
        layout.addWidget(apply_btn)
        
        refresh_btn = QPushButton("🔄 Odśwież listę")
        refresh_btn.clicked.connect(self._load_available_themes)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        return group
    
    def _add_group(self, parent_layout: QVBoxLayout, title: str, buttons: list):
        """Dodaje grupę przycisków"""
        group = QGroupBox(title)
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(8)
        
        for btn_text, btn_callback in buttons:
            btn = QPushButton(f"▶ {btn_text}")
            btn.setMinimumHeight(35)
            btn.clicked.connect(btn_callback)
            group_layout.addWidget(btn)
        
        parent_layout.addWidget(group)
    
    def _load_available_themes(self):
        """Ładuje dostępne motywy"""
        self.theme_combo.clear()
        themes = self.theme_manager.get_available_themes()
        current_theme = self.theme_manager.current_theme
        
        for i, theme_name in enumerate(themes):
            self.theme_combo.addItem(f"🎨 {theme_name}", theme_name)
            if theme_name == current_theme:
                self.theme_combo.setCurrentIndex(i)
    
    def _apply_selected_theme(self):
        """Stosuje wybrany motyw"""
        theme_name = self.theme_combo.currentData()
        if theme_name:
            self.theme_manager.apply_theme(theme_name)
            self.apply_theme()
            
            # Odśwież wszystkie otwarte dialogi
            for dialog in self.active_dialogs:
                if hasattr(dialog, 'apply_theme'):
                    dialog.apply_theme()
            
            QMessageBox.information(
                self,
                "Motyw zastosowany",
                f"Motyw '{theme_name}' został zastosowany!\n\n"
                "Wszystkie otwarte dialogi zostały odświeżone."
            )
    
    def apply_theme(self):
        """Stosuje aktualny motyw do launchera"""
        colors = self.theme_manager.get_current_colors()
        
        bg_main = colors.get('bg_main', '#ffffff')
        bg_secondary = colors.get('bg_secondary', '#f5f5f5')
        text_primary = colors.get('text_primary', '#000000')
        text_secondary = colors.get('text_secondary', '#666666')
        accent_primary = colors.get('accent_primary', '#2196F3')
        accent_hover = colors.get('accent_hover', '#1976D2')
        border_light = colors.get('border_light', '#e0e0e0')
        
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {bg_main};
            }}
            QLabel {{
                color: {text_primary};
            }}
            QLabel#footerLabel {{
                color: {text_secondary};
                font-style: italic;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {border_light};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {bg_secondary};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QPushButton {{
                background-color: {accent_primary};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 15px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
            QPushButton:pressed {{
                background-color: {accent_primary};
            }}
            QComboBox {{
                border: 1px solid {border_light};
                border-radius: 4px;
                padding: 5px;
                background-color: {bg_main};
                color: {text_primary};
            }}
        """)
    
    # ==================== TEST METHODS ====================
    
    def _test_ai_settings(self):
        """Test AI Settings"""
        try:
            from src.ui.ai_settings import AISettingsTab
            dialog = QWidget()
            layout = QVBoxLayout(dialog)
            settings_tab = AISettingsTab(dialog)
            layout.addWidget(settings_tab)
            dialog.setWindowTitle("🧪 Test: AI Settings")
            dialog.resize(800, 600)
            dialog.show()
            self.active_dialogs.append(dialog)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load AI Settings:\n{str(e)}")
    
    def _test_ai_summary_dialog(self):
        """Test AI Summary Dialog"""
        try:
            from src.ui.ai_summary_dialog import AISummaryDialog
            from src.Modules.AI_module.ai_logic import get_ai_manager
            
            # Mock recording data
            mock_recording = {
                'id': 1,
                'title': 'Test Recording',
                'transcription_text': 'To jest przykładowa transkrypcja rozmowy do testowania.',
                'created_at': '2024-11-11 10:00:00'
            }
            
            ai_manager = get_ai_manager()
            dialog = AISummaryDialog(mock_recording, ai_manager, parent=self)
            dialog.show()
            self.active_dialogs.append(dialog)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load AI Summary Dialog:\n{str(e)}")
    
    def _test_ai_task_communication(self):
        """Test AI Task Communication Dialog"""
        try:
            from src.ui.ai_task_communication_dialog import TaskAIPlanResultDialog
            from src.Modules.AI_module.ai_logic import AIProvider, AIResponse
            from datetime import datetime
            
            mock_response = AIResponse(
                text="1. Przeanalizuj wymagania\n"
                     "2. Zaprojektuj rozwiązanie\n"
                     "3. Implementuj funkcjonalność\n"
                     "4. Przetestuj kod\n"
                     "5. Dodaj dokumentację",
                provider=AIProvider.OPENAI,
                model="gpt-4",
                timestamp=datetime.now(),
                error=None
            )
            
            dialog = TaskAIPlanResultDialog("Test Task", mock_response, self)
            dialog.show()
            self.active_dialogs.append(dialog)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load AI Task Dialog:\n{str(e)}")
    
    def _test_assistant_settings(self):
        """Test Assistant Settings"""
        try:
            from src.ui.assistant_settings_tab import AssistantSettingsTab
            dialog = QWidget()
            layout = QVBoxLayout(dialog)
            settings_tab = AssistantSettingsTab(dialog)
            layout.addWidget(settings_tab)
            dialog.setWindowTitle("🧪 Test: Assistant Settings")
            dialog.resize(900, 600)
            dialog.show()
            self.active_dialogs.append(dialog)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load Assistant Settings:\n{str(e)}")
    
    def _test_main_window(self):
        """Test Main Window"""
        QMessageBox.information(
            self, 
            "Main Window", 
            "✅ Main Window jest już zintegrowany z ThemeManager!\n\n"
            "Kolory notatek używają accent_primary z motywu.\n"
            "Aby przetestować, uruchom całą aplikację: python main.py"
        )
    
    def _test_navigation_bar(self):
        """Test Navigation Bar"""
        QMessageBox.information(self, "Info", "Navigation Bar - To be implemented")
    
    def _test_task_view(self):
        """Test Task View"""
        QMessageBox.information(self, "Info", "Task View - To be implemented")
    
    def _test_kanban_view(self):
        """Test Kanban View"""
        QMessageBox.information(self, "Info", "Kanban View - To be implemented")
    
    def _test_note_view(self):
        """Test Note View"""
        QMessageBox.information(self, "Info", "Note View - To be implemented")
    
    def _test_pomodoro_view(self):
        """Test Pomodoro View"""
        QMessageBox.information(self, "Info", "Pomodoro View - To be implemented")
    
    def _test_alarms_view(self):
        """Test Alarms View"""
        QMessageBox.information(self, "Info", "Alarms View - To be implemented")
    
    def _test_quickboard_view(self):
        """Test QuickBoard View"""
        QMessageBox.information(self, "Info", "QuickBoard View - To be implemented")
    
    def _test_callcryptor_view(self):
        """Test CallCryptor View"""
        QMessageBox.information(self, "Info", "CallCryptor View - To be implemented")
    
    def _test_callcryptor_dialogs(self):
        """Test CallCryptor Dialogs"""
        QMessageBox.information(self, "Info", "CallCryptor Dialogs - To be implemented")
    
    def _test_pro_app_view(self):
        """Test ProApp View"""
        QMessageBox.information(self, "Info", "ProApp View - To be implemented")
    
    def _test_web_view(self):
        """Test Web View"""
        QMessageBox.information(self, "Info", "Web View - To be implemented")
    
    def _test_style_creator(self):
        """Test Style Creator Dialog"""
        try:
            from src.ui.style_creator_dialog import StyleCreatorDialog
            dialog = StyleCreatorDialog(self)
            
            # Połącz sygnał zapisania stylu z odświeżeniem listy motywów
            dialog.style_saved.connect(self._on_style_saved)
            
            dialog.show()
            self.active_dialogs.append(dialog)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load Style Creator:\n{str(e)}")
    
    def _on_style_saved(self, theme_name: str):
        """Callback po zapisaniu nowego stylu"""
        # Odśwież listę motywów
        self._load_available_themes()
        
        # Ustaw nowo utworzony motyw jako aktywny
        for i in range(self.theme_combo.count()):
            if self.theme_combo.itemData(i) == theme_name:
                self.theme_combo.setCurrentIndex(i)
                break
        
        # Zastosuj nowy motyw
        self.theme_manager.apply_theme(theme_name)
        self.apply_theme()
        
        # Odśwież wszystkie otwarte dialogi
        for dialog in self.active_dialogs:
            if hasattr(dialog, 'apply_theme'):
                dialog.apply_theme()
        
        QMessageBox.information(
            self,
            "Motyw zapisany",
            f"✅ Motyw '{theme_name}' został zapisany i zastosowany!\n\n"
            "Wszystkie otwarte okna zostały odświeżone."
        )
    
    def _test_config_view(self):
        """Test Config View"""
        try:
            from src.ui.config_view import SettingsView
            dialog = SettingsView(self)
            dialog.show()
            self.active_dialogs.append(dialog)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load Config View:\n{str(e)}")
    
    def _test_task_config(self):
        """Test Task Config Dialog"""
        QMessageBox.information(self, "Info", "Task Config Dialog - To be implemented")
    
    def _test_tag_manager(self):
        """Test Tag Manager"""
        QMessageBox.information(self, "Info", "Tag Manager - To be implemented")


def main():
    """Uruchamia launcher testów UI"""
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    launcher = UITestLauncher()
    launcher.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
