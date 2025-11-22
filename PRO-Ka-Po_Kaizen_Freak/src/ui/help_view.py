"""
Help View - Widok pomocy aplikacji
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea, QFrame
from PyQt6.QtCore import Qt
from loguru import logger

from ..utils.i18n_manager import t, get_i18n


class HelpView(QWidget):
    """Widok pomocy aplikacji - placeholder"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
        
        # Połącz z menedżerem i18n
        get_i18n().language_changed.connect(self.update_translations)
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(20)
        
        # Tytuł
        title_label = QLabel(t('help.title', 'Pomoc'))
        title_label.setObjectName("helpTitle")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = title_label.font()
        font.setPointSize(18)
        font.setBold(True)
        title_label.setFont(font)
        main_layout.addWidget(title_label)
        self.title_label = title_label
        
        # Separator
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(separator)
        
        # Scroll area dla treści pomocy
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        # Container dla treści
        content_widget = QWidget()
        content_layout = QVBoxLayout(content_widget)
        content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        content_layout.setSpacing(15)
        
        # Placeholder treść
        placeholder_label = QLabel(t('help.placeholder', '📖 Widok pomocy w przygotowaniu...\n\nW tym miejscu znajdziesz:\n• Dokumentację funkcji aplikacji\n• Przewodnik użytkownika\n• Skróty klawiszowe\n• FAQ'))
        placeholder_label.setObjectName("helpPlaceholder")
        placeholder_label.setWordWrap(True)
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = placeholder_label.font()
        font.setPointSize(12)
        placeholder_label.setFont(font)
        content_layout.addWidget(placeholder_label)
        self.placeholder_label = placeholder_label
        
        # Dodaj stretch na dole
        content_layout.addStretch()
        
        scroll_area.setWidget(content_widget)
        main_layout.addWidget(scroll_area)
        
        logger.info("HelpView initialized")
    
    def update_translations(self):
        """Odśwież tłumaczenia"""
        self.title_label.setText(t('help.title', 'Pomoc'))
        self.placeholder_label.setText(t('help.placeholder', '📖 Widok pomocy w przygotowaniu...\n\nW tym miejscu znajdziesz:\n• Dokumentację funkcji aplikacji\n• Przewodnik użytkownika\n• Skróty klawiszowe\n• FAQ'))
        logger.debug("HelpView translations updated")
