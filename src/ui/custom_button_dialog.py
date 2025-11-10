"""
Custom Button Dialog - Dialog do tworzenia własnych przycisków nawigacji
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QRadioButton, QButtonGroup, QFileDialog, QGroupBox
)
from PyQt6.QtCore import Qt
from loguru import logger

from ..utils.i18n_manager import t


class CustomButtonDialog(QDialog):
    """Dialog do konfiguracji własnego przycisku nawigacji"""
    
    def __init__(self, parent=None, button_data=None):
        """
        Args:
            parent: Widget rodzica
            button_data: Dane przycisku do edycji (None dla nowego przycisku)
                {
                    'id': 'custom_1',
                    'label': 'Nazwa przycisku',
                    'is_custom': True,
                    'custom_type': 'python_view' | 'external_app',
                    'custom_path': '/path/to/file.py',
                    'visible': True
                }
        """
        super().__init__(parent)
        self.button_data = button_data or {}
        self.selected_file = self.button_data.get('custom_path', '')
        
        self._setup_ui()
        self._load_data()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu dialogu"""
        self.setWindowTitle(t('custom_button.title', 'Dodaj własny przycisk'))
        self.setMinimumWidth(500)
        self.setModal(True)
        
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(15)
        
        # === NAZWA PRZYCISKU ===
        name_label = QLabel(t('custom_button.name_label', 'Nazwa przycisku:'))
        main_layout.addWidget(name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t('custom_button.name_placeholder', 'Wpisz nazwę przycisku'))
        self.name_input.setMinimumHeight(35)
        main_layout.addWidget(self.name_input)
        
        # === OPIS PRZYCISKU ===
        desc_label = QLabel(t('custom_button.description_label', 'Opis (opcjonalnie):'))
        main_layout.addWidget(desc_label)
        
        self.description_input = QLineEdit()
        self.description_input.setPlaceholderText(t('custom_button.description_placeholder', 'Wpisz krótki opis przycisku'))
        self.description_input.setMinimumHeight(35)
        main_layout.addWidget(self.description_input)
        
        # === TYP PRZYCISKU ===
        type_group = QGroupBox(t('custom_button.type_title', 'Typ przycisku'))
        type_layout = QVBoxLayout()
        
        self.type_button_group = QButtonGroup()
        
        # Opcja 1: Moduł Python (.pro)
        self.python_view_radio = QRadioButton(
            t('custom_button.python_module', '� Moduł Python (.pro)')
        )
        self.python_view_radio.setToolTip(
            t('custom_button.python_module_tooltip', 
              'Załaduje moduł .pro jako nowy widok w aplikacji')
        )
        self.type_button_group.addButton(self.python_view_radio, 1)
        type_layout.addWidget(self.python_view_radio)
        
        python_info = QLabel(
            t('custom_button.python_module_info',
              'ℹ️ Plik .pro musi zawierać kod Python tworzący widget (np. z Pro-App)')
        )
        python_info.setStyleSheet("color: #666; font-size: 10px; margin-left: 25px; margin-bottom: 10px;")
        python_info.setWordWrap(True)
        type_layout.addWidget(python_info)
        
        # Opcja 2: Aplikacja zewnętrzna
        self.external_app_radio = QRadioButton(
            t('custom_button.external_app', '🚀 Wywołanie aplikacji zewnętrznej (.exe, .bat, etc.)')
        )
        self.external_app_radio.setToolTip(
            t('custom_button.external_app_tooltip',
              'Uruchomi aplikację zewnętrzną po kliknięciu przycisku')
        )
        self.type_button_group.addButton(self.external_app_radio, 2)
        type_layout.addWidget(self.external_app_radio)
        
        external_info = QLabel(
            t('custom_button.external_app_info',
              'ℹ️ Obsługiwane formaty: .exe, .bat, .cmd, .py, .sh')
        )
        external_info.setStyleSheet("color: #666; font-size: 10px; margin-left: 25px;")
        external_info.setWordWrap(True)
        type_layout.addWidget(external_info)
        
        type_group.setLayout(type_layout)
        main_layout.addWidget(type_group)
        
        # === WYBÓR PLIKU ===
        file_group = QGroupBox(t('custom_button.file_title', 'Plik'))
        file_layout = QVBoxLayout()
        
        file_row = QHBoxLayout()
        
        self.file_path_input = QLineEdit()
        self.file_path_input.setPlaceholderText(t('custom_button.file_placeholder', 'Wybierz plik...'))
        self.file_path_input.setReadOnly(True)
        self.file_path_input.setMinimumHeight(35)
        file_row.addWidget(self.file_path_input, stretch=1)
        
        self.browse_button = QPushButton(t('custom_button.browse', 'Przeglądaj...'))
        self.browse_button.setMinimumHeight(35)
        self.browse_button.clicked.connect(self._on_browse_clicked)
        file_row.addWidget(self.browse_button)
        
        file_layout.addLayout(file_row)
        file_group.setLayout(file_layout)
        main_layout.addWidget(file_group)
        
        # === PRZYCISKI AKCJI ===
        main_layout.addStretch()
        
        buttons_row = QHBoxLayout()
        buttons_row.addStretch()
        
        self.cancel_button = QPushButton(t('button.cancel', 'Anuluj'))
        self.cancel_button.setMinimumHeight(35)
        self.cancel_button.clicked.connect(self.reject)
        buttons_row.addWidget(self.cancel_button)
        
        self.save_button = QPushButton(t('button.save', 'Zapisz'))
        self.save_button.setMinimumHeight(35)
        self.save_button.setObjectName("primaryButton")
        self.save_button.clicked.connect(self._on_save_clicked)
        buttons_row.addWidget(self.save_button)
        
        main_layout.addLayout(buttons_row)
        
        # Domyślnie zaznacz pierwszy typ
        self.python_view_radio.setChecked(True)
        
        # Połącz sygnały
        self.type_button_group.buttonClicked.connect(self._on_type_changed)
        
        logger.info("CustomButtonDialog initialized")
    
    def _load_data(self):
        """Wczytaj dane przycisku do edycji"""
        if not self.button_data:
            return
        
        # Nazwa przycisku
        self.name_input.setText(self.button_data.get('label', ''))
        
        # Opis przycisku
        self.description_input.setText(self.button_data.get('description', ''))
        
        # Typ przycisku
        custom_type = self.button_data.get('custom_type', 'python_module')
        if custom_type == 'python_module':
            self.python_view_radio.setChecked(True)
        elif custom_type == 'external_app':
            self.external_app_radio.setChecked(True)
        
        # Ścieżka do pliku
        if self.selected_file:
            self.file_path_input.setText(self.selected_file)
        
        logger.debug(f"Loaded button data: {self.button_data}")
    
    def _on_type_changed(self):
        """Obsługa zmiany typu przycisku"""
        # Można tutaj dostosować UI w zależności od wybranego typu
        logger.debug(f"Button type changed: {self._get_selected_type()}")
    
    def _get_selected_type(self):
        """Pobierz wybrany typ przycisku"""
        checked_id = self.type_button_group.checkedId()
        if checked_id == 1:
            return 'python_module'
        elif checked_id == 2:
            return 'external_app'
        return 'python_module'
    
    def _on_browse_clicked(self):
        """Obsługa przycisku przeglądania plików"""
        selected_type = self._get_selected_type()
        
        if selected_type == 'python_module':
            # File dialog dla plików .pro
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                t('custom_button.select_module_file', 'Wybierz moduł Python'),
                '',
                t('custom_button.module_filter', 'Moduły Pro-App (*.pro);;Pliki Python (*.py)')
            )
        else:  # external_app
            # File dialog dla aplikacji zewnętrznych
            file_path, _ = QFileDialog.getOpenFileName(
                self,
                t('custom_button.select_executable', 'Wybierz aplikację'),
                '',
                t('custom_button.executable_filter', 
                  'Aplikacje (*.exe *.bat *.cmd *.py *.sh);;Wszystkie pliki (*.*)')
            )
        
        if file_path:
            self.selected_file = file_path
            self.file_path_input.setText(file_path)
            logger.info(f"Selected file: {file_path}")
    
    def _on_save_clicked(self):
        """Obsługa przycisku zapisz - walidacja i zamknięcie"""
        # Walidacja
        name = self.name_input.text().strip()
        if not name:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                t('custom_button.validation_error', 'Błąd walidacji'),
                t('custom_button.name_required', 'Nazwa przycisku jest wymagana.')
            )
            self.name_input.setFocus()
            return
        
        if not self.selected_file:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                t('custom_button.validation_error', 'Błąd walidacji'),
                t('custom_button.file_required', 'Plik jest wymagany.')
            )
            self.browse_button.setFocus()
            return
        
        # Sprawdź czy plik istnieje
        from pathlib import Path
        if not Path(self.selected_file).exists():
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                t('custom_button.validation_error', 'Błąd walidacji'),
                t('custom_button.file_not_exists', 'Wybrany plik nie istnieje.')
            )
            return
        
        logger.info(f"Custom button saved: name={name}, type={self._get_selected_type()}, file={self.selected_file}")
        self.accept()
    
    def get_button_data(self):
        """
        Pobierz dane skonfigurowanego przycisku
        
        Returns:
            dict: Dane przycisku w formacie:
                {
                    'label': str,
                    'description': str,
                    'is_custom': True,
                    'custom_type': 'python_module' | 'external_app',
                    'custom_path': str,
                    'visible': True
                }
        """
        return {
            'label': self.name_input.text().strip(),
            'description': self.description_input.text().strip(),
            'is_custom': True,
            'custom_type': self._get_selected_type(),
            'custom_path': self.selected_file,
            'visible': True
        }
