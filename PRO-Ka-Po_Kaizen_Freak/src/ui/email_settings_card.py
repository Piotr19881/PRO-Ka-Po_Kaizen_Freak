"""
Email Settings Card - UI dla zarządzania kontami e-mail
========================================================

Karta ustawień kont e-mail dla modułu CallCryptor.
Zintegrowana z i18n, Theme Manager i bazą danych.

Features:
- Lista kont e-mail użytkownika
- Dodawanie nowego konta
- Edycja istniejącego konta
- Usuwanie konta
- Test połączenia
- Aktywacja/deaktywacja konta
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QDialog, QLineEdit,
    QComboBox, QCheckBox, QMessageBox, QGroupBox,
    QFormLayout, QSpinBox, QProgressDialog, QFrame
)
from PyQt6.QtCore import Qt, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QIcon
from loguru import logger
from typing import Optional, Dict
from pathlib import Path

from ..utils.i18n_manager import t
from ..utils.theme_manager import get_theme_manager
from ..database.email_accounts_db import EmailAccountsDatabase
from ..core.assisstant.modules.email_helper import EmailConnector, test_email_connection


class ConnectionTester(QThread):
    """Background thread to run test_email_connection without blocking the UI"""
    finished = pyqtSignal(bool, str)

    def __init__(self, config):
        super().__init__()
        self.config = config

    def run(self):
        try:
            success, message = test_email_connection(self.config)
        except Exception as e:
            success, message = False, str(e)
        # Emit the result back to the UI thread
        self.finished.emit(success, message)


class EmailAccountDialog(QDialog):
    """Dialog dodawania/edycji konta e-mail"""
    
    def __init__(self, parent=None, account_data: Optional[Dict] = None):
        super().__init__(parent)
        self.account_data = account_data  # None = dodawanie, Dict = edycja
        self.theme_manager = get_theme_manager()
        
        self.setWindowTitle(
            t('settings.email.edit_account') if account_data 
            else t('settings.email.add_account')
        )
        self.setMinimumWidth(500)
        self.setModal(True)
        
        self._setup_ui()
        self._load_data()
        self.apply_theme()
    
    def _setup_ui(self):
        """Konfiguracja UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === Formularz ===
        form_group = QGroupBox(t('settings.email.account_details'))
        form_layout = QFormLayout()
        form_layout.setSpacing(10)
        
        # Nazwa konta
        self.account_name_input = QLineEdit()
        self.account_name_input.setPlaceholderText(t('settings.email.account_name_placeholder'))
        form_layout.addRow(t('settings.email.account_name') + ":", self.account_name_input)
        
        # Adres e-mail
        self.email_address_input = QLineEdit()
        self.email_address_input.setPlaceholderText("user@example.com")
        form_layout.addRow(t('settings.email.email_address') + ":", self.email_address_input)
        
        form_group.setLayout(form_layout)
        layout.addWidget(form_group)
        
        # === Konfiguracja serwera ===
        server_group = QGroupBox(t('settings.email.server_config'))
        server_layout = QFormLayout()
        server_layout.setSpacing(10)
        
        # Typ serwera
        self.server_type_combo = QComboBox()
        self.server_type_combo.addItems(['IMAP', 'POP3'])
        self.server_type_combo.currentTextChanged.connect(self._on_server_type_changed)
        server_layout.addRow(t('settings.email.server_type') + ":", self.server_type_combo)
        
        # Adres serwera
        self.server_address_input = QLineEdit()
        self.server_address_input.setPlaceholderText("imap.gmail.com")
        server_layout.addRow(t('settings.email.server_address') + ":", self.server_address_input)
        
        # Port
        self.server_port_input = QSpinBox()
        self.server_port_input.setRange(1, 65535)
        self.server_port_input.setValue(993)  # Default IMAP SSL
        server_layout.addRow(t('settings.email.server_port') + ":", self.server_port_input)
        
        # SSL/TLS
        ssl_layout = QHBoxLayout()
        self.use_ssl_checkbox = QCheckBox(t('settings.email.use_ssl'))
        self.use_ssl_checkbox.setChecked(True)
        self.use_tls_checkbox = QCheckBox(t('settings.email.use_tls'))
        ssl_layout.addWidget(self.use_ssl_checkbox)
        ssl_layout.addWidget(self.use_tls_checkbox)
        ssl_layout.addStretch()
        server_layout.addRow("", ssl_layout)
        
        server_group.setLayout(server_layout)
        layout.addWidget(server_group)
        
        # === Credentials ===
        creds_group = QGroupBox(t('settings.email.credentials'))
        creds_layout = QFormLayout()
        creds_layout.setSpacing(10)
        
        # Nazwa użytkownika
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText(t('settings.email.username_placeholder'))
        creds_layout.addRow(t('settings.email.username') + ":", self.username_input)
        
        # Hasło
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_input.setPlaceholderText(t('settings.email.password_placeholder'))
        creds_layout.addRow(t('settings.email.password') + ":", self.password_input)
        
        creds_group.setLayout(creds_layout)
        layout.addWidget(creds_group)
        
        # === Ustawienia pobierania ===
        fetch_group = QGroupBox(t('settings.email.fetch_settings'))
        fetch_layout = QFormLayout()
        fetch_layout.setSpacing(10)
        
        # Liczba pobieranych wiadomości
        self.fetch_limit_input = QSpinBox()
        self.fetch_limit_input.setRange(10, 1000)
        self.fetch_limit_input.setValue(50)  # Domyślnie 50 wiadomości
        self.fetch_limit_input.setSuffix(" " + t('settings.email.messages'))
        self.fetch_limit_input.setToolTip(t('settings.email.fetch_limit_tooltip'))
        fetch_layout.addRow(t('settings.email.fetch_limit') + ":", self.fetch_limit_input)
        
        fetch_group.setLayout(fetch_layout)
        layout.addWidget(fetch_group)
        
        # === Przyciski ===
        buttons_layout = QHBoxLayout()
        
        self.test_btn = QPushButton(t('settings.email.test_connection'))
        self.test_btn.clicked.connect(self._test_connection)
        buttons_layout.addWidget(self.test_btn)
        
        buttons_layout.addStretch()
        
        self.cancel_btn = QPushButton(t('button.cancel'))
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)
        
        self.save_btn = QPushButton(t('button.save'))
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setDefault(True)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
    
    def _load_data(self):
        """Załaduj dane do formularza (jeśli edycja)"""
        if not self.account_data:
            return
        
        self.account_name_input.setText(self.account_data.get('account_name', ''))
        self.email_address_input.setText(self.account_data.get('email_address', ''))
        self.server_type_combo.setCurrentText(self.account_data.get('server_type', 'IMAP'))
        self.server_address_input.setText(self.account_data.get('server_address', ''))
        self.server_port_input.setValue(self.account_data.get('server_port', 993))
        self.username_input.setText(self.account_data.get('username', ''))
        self.use_ssl_checkbox.setChecked(bool(self.account_data.get('use_ssl', True)))
        self.use_tls_checkbox.setChecked(bool(self.account_data.get('use_tls', False)))
        self.fetch_limit_input.setValue(self.account_data.get('fetch_limit', 50))
        
        # Hasło nie jest ładowane ze względów bezpieczeństwa
        self.password_input.setPlaceholderText(t('settings.email.password_unchanged'))
    
    def _on_server_type_changed(self, server_type: str):
        """Automatycznie dostosuj port po zmianie typu serwera"""
        if server_type == 'IMAP':
            self.server_port_input.setValue(993 if self.use_ssl_checkbox.isChecked() else 143)
        else:  # POP3
            self.server_port_input.setValue(995 if self.use_ssl_checkbox.isChecked() else 110)
    
    def _test_connection(self):
        """Testuj połączenie z serwerem"""
        # Walidacja
        if not self._validate_form():
            return
        
        # Przygotuj konfigurację
        config = self._get_form_data()
        
        # Show progress dialog while running test in background thread
        progress = QProgressDialog(
            t('settings.email.testing_connection'),
            t('button.cancel'),
            0, 0,
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButtonText(t('button.cancel'))
        progress.show()

        # Start background tester
        self._tester = ConnectionTester(config)

        def _on_finished(success: bool, message: str):
            progress.close()
            # Clean up thread reference
            try:
                self._tester.finished.disconnect()
            except Exception:
                pass
            self._tester = None

            if success:
                QMessageBox.information(
                    self,
                    t('settings.email.test_success'),
                    t('settings.email.connection_successful')
                )
            else:
                QMessageBox.warning(
                    self,
                    t('settings.email.test_failed'),
                    f"{t('settings.email.connection_failed')}:\n{message}"
                )

        self._tester.finished.connect(_on_finished)
        self._tester.start()
    
    def _validate_form(self) -> bool:
        """Walidacja formularza"""
        if not self.account_name_input.text().strip():
            QMessageBox.warning(self, t('error.general'), t('settings.email.error.account_name_required'))
            return False
        
        if not self.email_address_input.text().strip():
            QMessageBox.warning(self, t('error.general'), t('settings.email.error.email_required'))
            return False
        
        if not self.server_address_input.text().strip():
            QMessageBox.warning(self, t('error.general'), t('settings.email.error.server_address_required'))
            return False
        
        if not self.username_input.text().strip():
            QMessageBox.warning(self, t('error.general'), t('settings.email.error.username_required'))
            return False
        
        # Hasło wymagane tylko przy dodawaniu nowego konta
        if not self.account_data and not self.password_input.text():
            QMessageBox.warning(self, t('error.general'), t('settings.email.error.password_required'))
            return False
        
        return True
    
    def _save(self):
        """Zapisz dane"""
        if not self._validate_form():
            return
        
        self.accept()
    
    def _get_form_data(self) -> Dict:
        """Pobierz dane z formularza"""
        data = {
            'account_name': self.account_name_input.text().strip(),
            'email_address': self.email_address_input.text().strip(),
            'server_type': self.server_type_combo.currentText(),
            'server_address': self.server_address_input.text().strip(),
            'server_port': self.server_port_input.value(),
            'username': self.username_input.text().strip(),
            'use_ssl': self.use_ssl_checkbox.isChecked(),
            'use_tls': self.use_tls_checkbox.isChecked(),
            'fetch_limit': self.fetch_limit_input.value()
        }
        
        # Dodaj hasło jeśli zostało podane
        if self.password_input.text():
            data['password'] = self.password_input.text()
        
        return data
    
    def get_account_data(self) -> Dict:
        """Pobierz dane konta (wywołaj po accept())"""
        return self._get_form_data()
    
    def apply_theme(self):
        """Aplikuj motyw"""
        if not self.theme_manager:
            return
        
        colors = self.theme_manager.get_current_colors()
        
        # Style dla inputów
        input_style = f"""
            QLineEdit, QSpinBox {{
                background-color: {colors.get('bg_main', '#FFFFFF')};
                color: {colors.get('text_primary', '#000000')};
                border: 1px solid {colors.get('border_light', '#CCCCCC')};
                border-radius: 4px;
                padding: 5px;
            }}
            QLineEdit:focus, QSpinBox:focus {{
                border: 2px solid {colors.get('accent_primary', '#2196F3')};
            }}
        """
        self.setStyleSheet(input_style)


class EmailSettingsCard(QWidget):
    """
    Karta ustawień kont e-mail.
    Wyświetlana w Config View jako jedna z kart.
    """
    
    accounts_changed = pyqtSignal()  # Emitowany gdy lista kont się zmienia
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.db_manager = None  # Zostanie ustawiony przez set_user_data
        self.user_id = None
        
        self._setup_ui()
        self.apply_theme()
    
    def set_user_data(self, user_data: dict):
        """
        Ustaw dane użytkownika i zainicjalizuj bazę danych.
        
        Args:
            user_data: {'id': str, ...}
        """
        self.user_id = user_data.get('id')
        
        # Inicjalizuj bazę danych
        from ..core.config import config
        db_path = config.DATA_DIR / "email_accounts.db"
        self.db_manager = EmailAccountsDatabase(str(db_path))
        
        logger.info(f"[EmailSettings] Initialized for user: {self.user_id}")
        
        # Załaduj konta
        self._load_accounts()
    
    def _setup_ui(self):
        """Konfiguracja UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # === Nagłówek ===
        header_layout = QHBoxLayout()
        
        title_label = QLabel(t('settings.email_accounts'))
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title_label.setFont(title_font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        # Przycisk dodaj
        self.add_btn = QPushButton(f"➕ {t('settings.email.add_account')}")
        self.add_btn.clicked.connect(self._add_account)
        header_layout.addWidget(self.add_btn)
        
        layout.addLayout(header_layout)
        
        # === Ostrzeżenie o prywatności ===
        privacy_frame = QFrame()
        privacy_frame.setFrameShape(QFrame.Shape.StyledPanel)
        privacy_layout = QHBoxLayout(privacy_frame)
        
        privacy_icon = QLabel("🔒")
        privacy_icon.setFont(QFont("Segoe UI Emoji", 16))
        privacy_layout.addWidget(privacy_icon)
        
        privacy_text = QLabel(t('settings.email.privacy_notice'))
        privacy_text.setWordWrap(True)
        privacy_text.setStyleSheet("color: #666; font-style: italic;")
        privacy_layout.addWidget(privacy_text, stretch=1)
        
        layout.addWidget(privacy_frame)
        
        # === Lista kont ===
        self.accounts_list = QListWidget()
        self.accounts_list.itemDoubleClicked.connect(self._edit_account)
        layout.addWidget(self.accounts_list)
        
        # === Przyciski akcji ===
        buttons_layout = QHBoxLayout()
        
        self.edit_btn = QPushButton(t('button.edit'))
        self.edit_btn.clicked.connect(self._edit_account)
        self.edit_btn.setEnabled(False)
        buttons_layout.addWidget(self.edit_btn)
        
        self.delete_btn = QPushButton(t('button.delete'))
        self.delete_btn.clicked.connect(self._delete_account)
        self.delete_btn.setEnabled(False)
        buttons_layout.addWidget(self.delete_btn)
        
        self.test_btn = QPushButton(t('settings.email.test_connection'))
        self.test_btn.clicked.connect(self._test_selected_account)
        self.test_btn.setEnabled(False)
        buttons_layout.addWidget(self.test_btn)
        
        buttons_layout.addStretch()
        
        layout.addLayout(buttons_layout)
        
        # Połącz sygnały
        self.accounts_list.itemSelectionChanged.connect(self._on_selection_changed)
    
    def _load_accounts(self):
        """Załaduj listę kont z bazy danych"""
        if not self.db_manager or not self.user_id:
            return
        
        self.accounts_list.clear()
        
        accounts = self.db_manager.get_all_accounts(self.user_id)
        
        for account in accounts:
            # Format: Nazwa (email) - Typ
            display_text = f"{account['account_name']} ({account['email_address']}) - {account['server_type']}"
            
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, account['id'])
            
            # Ikona statusu
            if not account['is_active']:
                item.setText(f"⚫ {display_text}")  # Nieaktywne
            elif account['connection_error']:
                item.setText(f"⚠️ {display_text}")  # Błąd połączenia
            else:
                item.setText(f"✉️ {display_text}")  # OK
            
            self.accounts_list.addItem(item)
        
        logger.debug(f"[EmailSettings] Loaded {len(accounts)} accounts")
    
    def _on_selection_changed(self):
        """Obsługa zmiany zaznaczenia"""
        has_selection = len(self.accounts_list.selectedItems()) > 0
        self.edit_btn.setEnabled(has_selection)
        self.delete_btn.setEnabled(has_selection)
        self.test_btn.setEnabled(has_selection)
    
    def _add_account(self):
        """Dodaj nowe konto"""
        dialog = EmailAccountDialog(self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            account_data = dialog.get_account_data()
            
            try:
                # Sprawdź czy konto już istnieje
                if self.db_manager.account_exists(account_data['email_address'], self.user_id):
                    QMessageBox.warning(
                        self,
                        t('error.general'),
                        t('settings.email.error.account_exists')
                    )
                    return
                
                # Dodaj do bazy
                account_id = self.db_manager.add_account(account_data, self.user_id)
                
                logger.success(f"[EmailSettings] Added account: {account_id}")
                
                # Odśwież listę
                self._load_accounts()
                self.accounts_changed.emit()
                
                QMessageBox.information(
                    self,
                    t('settings.email.success'),
                    t('settings.email.account_added')
                )
                
            except Exception as e:
                logger.error(f"[EmailSettings] Failed to add account: {e}")
                QMessageBox.critical(
                    self,
                    t('error.general'),
                    f"{t('settings.email.error.add_failed')}:\n{str(e)}"
                )
    
    def _edit_account(self):
        """Edytuj zaznaczone konto"""
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            return
        
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        account_data = self.db_manager.get_account(account_id)
        
        if not account_data:
            QMessageBox.warning(self, t('error.general'), t('settings.email.error.account_not_found'))
            return
        
        dialog = EmailAccountDialog(self, account_data)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            updated_data = dialog.get_account_data()
            
            try:
                self.db_manager.update_account(account_id, updated_data)
                
                logger.success(f"[EmailSettings] Updated account: {account_id}")
                
                # Odśwież listę
                self._load_accounts()
                self.accounts_changed.emit()
                
                QMessageBox.information(
                    self,
                    t('settings.email.success'),
                    t('settings.email.account_updated')
                )
                
            except Exception as e:
                logger.error(f"[EmailSettings] Failed to update account: {e}")
                QMessageBox.critical(
                    self,
                    t('error.general'),
                    f"{t('settings.email.error.update_failed')}:\n{str(e)}"
                )
    
    def _delete_account(self):
        """Usuń zaznaczone konto"""
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            return
        
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        account_data = self.db_manager.get_account(account_id)
        
        if not account_data:
            return
        
        # Potwierdzenie
        reply = QMessageBox.question(
            self,
            t('settings.email.confirm_delete'),
            f"{t('settings.email.delete_message')}:\n\n{account_data['account_name']} ({account_data['email_address']})",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            try:
                self.db_manager.delete_account(account_id)
                
                logger.success(f"[EmailSettings] Deleted account: {account_id}")
                
                # Odśwież listę
                self._load_accounts()
                self.accounts_changed.emit()
                
                QMessageBox.information(
                    self,
                    t('settings.email.success'),
                    t('settings.email.account_deleted')
                )
                
            except Exception as e:
                logger.error(f"[EmailSettings] Failed to delete account: {e}")
                QMessageBox.critical(
                    self,
                    t('error.general'),
                    f"{t('settings.email.error.delete_failed')}:\n{str(e)}"
                )
    
    def _test_selected_account(self):
        """Testuj połączenie zaznaczonego konta"""
        selected_items = self.accounts_list.selectedItems()
        if not selected_items:
            return
        
        account_id = selected_items[0].data(Qt.ItemDataRole.UserRole)
        config = self.db_manager.get_account_config(account_id)
        
        if not config:
            return
        
        # Show progress dialog while running test in background thread
        progress = QProgressDialog(
            t('settings.email.testing_connection'),
            t('button.cancel'),
            0, 0,
            self
        )
        progress.setWindowModality(Qt.WindowModality.WindowModal)
        progress.setCancelButtonText(t('button.cancel'))
        progress.show()

        tester = ConnectionTester(config)

        def _on_finished(success: bool, message: str):
            progress.close()
            try:
                tester.finished.disconnect()
            except Exception:
                pass

            # Zaktualizuj status w bazie
            try:
                self.db_manager.update_connection_status(account_id, success, message if not success else None)
            except Exception as e:
                logger.error(f"[EmailSettings] Failed to update connection status: {e}")

            if success:
                QMessageBox.information(
                    self,
                    t('settings.email.test_success'),
                    t('settings.email.connection_successful')
                )
            else:
                QMessageBox.warning(
                    self,
                    t('settings.email.test_failed'),
                    f"{t('settings.email.connection_failed')}:\n{message}"
                )

            # Odśwież listę (zaktualizowany status)
            self._load_accounts()

        tester.finished.connect(_on_finished)
        tester.start()
    
    def apply_theme(self):
        """Aplikuj motyw"""
        if not self.theme_manager:
            return
        
        colors = self.theme_manager.get_current_colors()
        
        # Style dla listy
        list_style = f"""
            QListWidget {{
                background-color: {colors.get('bg_main', '#FFFFFF')};
                color: {colors.get('text_primary', '#000000')};
                border: 1px solid {colors.get('border_light', '#CCCCCC')};
                border-radius: 4px;
            }}
            QListWidget::item {{
                padding: 8px;
                border-bottom: 1px solid {colors.get('border_light', '#EEEEEE')};
            }}
            QListWidget::item:selected {{
                background-color: {colors.get('accent_primary', '#2196F3')};
                color: white;
            }}
            QListWidget::item:hover {{
                background-color: {colors.get('bg_secondary', '#F5F5F5')};
            }}
        """
        self.accounts_list.setStyleSheet(list_style)
        
        # Style dla przycisków
        btn_style = f"""
            QPushButton {{
                background-color: {colors.get('accent_primary', '#2196F3')};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                background-color: {colors.get('accent_hover', '#1976D2')};
            }}
            QPushButton:pressed {{
                background-color: {colors.get('accent_pressed', '#0D47A1')};
            }}
            QPushButton:disabled {{
                background-color: {colors.get('border_light', '#CCCCCC')};
                color: {colors.get('text_secondary', '#999999')};
            }}
        """
        for btn in [self.add_btn, self.edit_btn, self.delete_btn, self.test_btn]:
            btn.setStyleSheet(btn_style)
