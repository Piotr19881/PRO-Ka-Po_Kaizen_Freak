"""
Moduł konfiguracji klienta pocztowego

Funkcjonalność:
- Zarządzanie kontami email (dodawanie, edycja, usuwanie)
- Konfiguracja serwerów SMTP/IMAP
- Zapisywanie i wczytywanie ustawień
- Testowanie połączenia z serwerem

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-06
"""

import json
import os
import re
import socket
import smtplib
import imaplib
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QSpinBox, QCheckBox,
    QListWidget, QGroupBox, QMessageBox, QTabWidget, QWidget,
    QTextEdit, QListWidgetItem, QComboBox
)
from PyQt6.QtCore import Qt


FILTER_FIELDS = [
    ("from", "Nadawca (FROM)"),
    ("to", "Adresat (TO)"),
    ("subject", "Temat (SUBJECT)"),
    ("body", "Treść (BODY)")
]

FILTER_OPERATORS = [
    ("contains", "zawiera"),
    ("not_contains", "nie zawiera"),
    ("starts_with", "zaczyna się od"),
    ("ends_with", "kończy się na"),
    ("equals", "jest równe")
]

FIELD_LABELS = {value: label for value, label in FILTER_FIELDS}
OPERATOR_LABELS = {value: label for value, label in FILTER_OPERATORS}

ACCOUNT_DEFAULTS = {
    "name": "",
    "email": "",
    "password": "",
    "user_name": "",
    "imap_server": "",
    "imap_port": 993,
    "imap_ssl": True,
    "smtp_server": "",
    "smtp_port": 587,
    "smtp_ssl": True,
}


def _to_bool(value, default):
    """Konwertuje różne reprezentacje wartości logicznych."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "tak", "on"}:
            return True
        if lowered in {"false", "0", "no", "nie", "off"}:
            return False
        return default
    if value is None:
        return default
    return bool(value)


class FilterConditionDialog(QDialog):
    """Prosty dialog do tworzenia i edycji pojedynczego warunku filtra"""

    def __init__(self, parent=None, condition=None):
        super().__init__(parent)
        self.setWindowTitle("Warunek filtra")
        self.setModal(True)

        layout = QVBoxLayout()
        form_layout = QFormLayout()

        self.field_combo = QComboBox()
        for value, label in FILTER_FIELDS:
            self.field_combo.addItem(label, value)
        form_layout.addRow("Pole wiadomości:", self.field_combo)

        self.operator_combo = QComboBox()
        for value, label in FILTER_OPERATORS:
            self.operator_combo.addItem(label, value)
        form_layout.addRow("Warunek:", self.operator_combo)

        self.value_edit = QLineEdit()
        self.value_edit.setPlaceholderText("Wpisz szukaną frazę")
        form_layout.addRow("Wartość:", self.value_edit)

        layout.addLayout(form_layout)

        buttons_layout = QHBoxLayout()
        self.btn_ok = QPushButton("Zapisz")
        self.btn_ok.clicked.connect(self.accept)
        buttons_layout.addWidget(self.btn_ok)

        self.btn_cancel = QPushButton("Anuluj")
        self.btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(self.btn_cancel)

        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)

        self.setLayout(layout)

        if condition:
            field_index = self.field_combo.findData(condition.get("field"))
            if field_index >= 0:
                self.field_combo.setCurrentIndex(field_index)

            operator_index = self.operator_combo.findData(condition.get("operator"))
            if operator_index >= 0:
                self.operator_combo.setCurrentIndex(operator_index)

            self.value_edit.setText(condition.get("value", ""))

    def accept(self):
        if not self.value_edit.text().strip():
            QMessageBox.warning(self, "Błąd", "Wartość warunku nie może być pusta!")
            return
        super().accept()

    def get_condition(self):
        return {
            "field": self.field_combo.currentData(),
            "operator": self.operator_combo.currentData(),
            "value": self.value_edit.text().strip()
        }


class MailConfigDialog(QDialog):
    """Okno dialogowe konfiguracji kont email"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config_file = Path("mail_client/mail_accounts.json")
        self.signatures_file = Path("mail_client/mail_signatures.json")
        self.filters_file = Path("mail_client/mail_filters.json")
        self.accounts = []
        self.signatures = []
        self.filters = []
        self.editing_conditions = []
        self.current_account = None
        self.current_signature = None
        self.current_filter = None
        self.is_filter_editing = False
        self.is_account_editing = False
        self.is_loading_account = False
        self.init_ui()
        self.load_accounts()
        self.load_signatures()
        self.load_filters()
        
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        self.setWindowTitle("Konfiguracja kont pocztowych")
        self.setMinimumSize(700, 500)
        
        main_layout = QHBoxLayout()
        
        # Lewa strona - lista kont
        left_panel = QVBoxLayout()
        
        left_label = QLabel("Konta email:")
        left_label.setStyleSheet("font-weight: bold; font-size: 11pt;")
        left_panel.addWidget(left_label)
        
        self.accounts_list = QListWidget()
        self.accounts_list.currentRowChanged.connect(self.on_account_selected)
        left_panel.addWidget(self.accounts_list)
        
        # Przyciski zarządzania kontami
        btn_layout = QVBoxLayout()
        
        self.btn_new = QPushButton("+ Nowe konto")
        self.btn_new.clicked.connect(self.new_account)
        btn_layout.addWidget(self.btn_new)
        
        self.btn_delete = QPushButton("- Usuń konto")
        self.btn_delete.clicked.connect(self.delete_account)
        self.btn_delete.setEnabled(False)
        btn_layout.addWidget(self.btn_delete)
        
        btn_layout.addStretch()
        left_panel.addLayout(btn_layout)
        
        # Prawa strona - szczegóły konta
        right_panel = QVBoxLayout()
        
        # Zakładki dla różnych ustawień
        self.tabs = QTabWidget()
        
        account_tab = self.create_account_settings_tab()
        self.tabs.addTab(account_tab, "Ustawienia konta")
        
        # Zakładka: Podpisy
        signatures_tab = self.create_signatures_tab()
        self.tabs.addTab(signatures_tab, "Podpisy")
        
        # Zakładka: Filtry poczty
        filters_tab = self.create_filters_tab()
        self.tabs.addTab(filters_tab, "Filtry")

        right_panel.addWidget(self.tabs)
        
        # Przyciski akcji
        action_layout = QHBoxLayout()
        
        self.btn_test = QPushButton("Testuj połączenie")
        self.btn_test.clicked.connect(self.test_connection)
        self.btn_test.setEnabled(False)
        action_layout.addWidget(self.btn_test)
        
        action_layout.addStretch()
        
        self.btn_save = QPushButton("Zapisz")
        self.btn_save.clicked.connect(self.save_account)
        self.btn_save.setEnabled(False)
        action_layout.addWidget(self.btn_save)
        
        self.btn_cancel = QPushButton("Anuluj")
        self.btn_cancel.clicked.connect(self.cancel_edit)
        self.btn_cancel.setEnabled(False)
        action_layout.addWidget(self.btn_cancel)
        
        right_panel.addLayout(action_layout)
        
        # Dodaj panele do głównego layoutu
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)
        
        # Przyciski dialogu
        dialog_buttons = QHBoxLayout()
        dialog_buttons.addStretch()
        
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        btn_close.setFixedWidth(100)
        dialog_buttons.addWidget(btn_close)
        
        # Główny layout
        final_layout = QVBoxLayout()
        final_layout.addLayout(main_layout)
        final_layout.addLayout(dialog_buttons)
        
        self.setLayout(final_layout)
        self._register_account_field_signals()
        self.update_account_actions()

    def _register_account_field_signals(self) -> None:
        """Podpina aktualizację przy zmianach pól konta."""
        line_edits = [
            self.account_name,
            self.email_address,
            self.password,
            self.user_name,
            self.imap_server,
            self.smtp_server,
        ]
        for edit in line_edits:
            edit.textChanged.connect(self.on_account_field_changed)

        self.imap_port.valueChanged.connect(self.on_account_field_changed)
        self.smtp_port.valueChanged.connect(self.on_account_field_changed)
        self.imap_ssl.toggled.connect(self.on_account_field_changed)
        self.smtp_ssl.toggled.connect(self.on_account_field_changed)

    def on_account_field_changed(self, *_args) -> None:
        """Reaguje na zmiany pól konta."""
        if self.is_loading_account:
            return

        if self.current_account is None:
            self.is_account_editing = self._collect_account_form_data() != ACCOUNT_DEFAULTS
        else:
            self.is_account_editing = not self._current_form_matches_account()

        self.update_account_actions()

    def update_account_actions(self) -> None:
        """Aktualizuje dostępność przycisków zapisu i testu."""
        if not hasattr(self, "btn_save"):
            return

        required_fields = (
            self.account_name.text().strip(),
            self.email_address.text().strip(),
            self.password.text().strip(),
            self.imap_server.text().strip(),
            self.smtp_server.text().strip(),
        )
        required_filled = all(required_fields)
        has_selected_account = self.current_account is not None

        self.btn_save.setEnabled(self.is_account_editing and required_filled)
        self.btn_cancel.setEnabled(self.is_account_editing)
        self.btn_test.setEnabled(required_filled or has_selected_account)

    def _normalize_account_data(self, data: dict) -> dict:
        """Zwraca dane konta uzupełnione o wartości domyślne."""
        normalized = dict(ACCOUNT_DEFAULTS)
        if isinstance(data, dict):
            normalized.update({
                "name": data.get("name", ""),
                "email": data.get("email", ""),
                "password": data.get("password", ""),
                "user_name": data.get("user_name", ""),
                "imap_server": data.get("imap_server", ""),
                "imap_port": int(data.get("imap_port", ACCOUNT_DEFAULTS["imap_port"])),
                "imap_ssl": _to_bool(data.get("imap_ssl", ACCOUNT_DEFAULTS["imap_ssl"]), ACCOUNT_DEFAULTS["imap_ssl"]),
                "smtp_server": data.get("smtp_server", ""),
                "smtp_port": int(data.get("smtp_port", ACCOUNT_DEFAULTS["smtp_port"])),
                "smtp_ssl": _to_bool(data.get("smtp_ssl", ACCOUNT_DEFAULTS["smtp_ssl"]), ACCOUNT_DEFAULTS["smtp_ssl"]),
            })
        return normalized

    def _collect_account_form_data(self) -> dict:
        """Odczytuje wartości pól formularza konta."""
        return {
            "name": self.account_name.text().strip(),
            "email": self.email_address.text().strip(),
            "password": self.password.text(),
            "user_name": self.user_name.text().strip(),
            "imap_server": self.imap_server.text().strip(),
            "imap_port": self.imap_port.value(),
            "imap_ssl": self.imap_ssl.isChecked(),
            "smtp_server": self.smtp_server.text().strip(),
            "smtp_port": self.smtp_port.value(),
            "smtp_ssl": self.smtp_ssl.isChecked(),
        }

    def _apply_account_to_form(self, account_data: dict) -> None:
        """Wypełnia formularz danymi konta."""
        self.is_loading_account = True
        data = self._normalize_account_data(account_data)

        self.account_name.setText(data["name"])
        self.email_address.setText(data["email"])
        self.password.setText(data["password"])
        self.user_name.setText(data["user_name"])

        self.imap_server.setText(data["imap_server"])
        self.imap_port.setValue(data["imap_port"])
        self.imap_ssl.setChecked(data["imap_ssl"])

        self.smtp_server.setText(data["smtp_server"])
        self.smtp_port.setValue(data["smtp_port"])
        self.smtp_ssl.setChecked(data["smtp_ssl"])

        self.is_loading_account = False

    def _current_form_matches_account(self) -> bool:
        """Sprawdza czy formularz odpowiada zapisanym danym."""
        form_data = self._collect_account_form_data()
        if self.current_account is None or self.current_account >= len(self.accounts):
            return form_data == ACCOUNT_DEFAULTS
        stored = self._normalize_account_data(self.accounts[self.current_account])
        return form_data == stored

    def create_account_settings_tab(self):
        """Buduje kartę z ustawieniami konta pocztowego."""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setSpacing(12)

        account_group = QGroupBox("Dane konta")
        account_form = QFormLayout()

        self.account_name = QLineEdit()
        self.account_name.setPlaceholderText("Np. Praca, Gmail osobisty...")
        account_form.addRow("Nazwa konta:", self.account_name)

        self.email_address = QLineEdit()
        self.email_address.setPlaceholderText("adres@email.com")
        account_form.addRow("Adres email:", self.email_address)

        self.password = QLineEdit()
        self.password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password.setPlaceholderText("Hasło do konta")
        account_form.addRow("Hasło:", self.password)

        self.user_name = QLineEdit()
        self.user_name.setPlaceholderText("Twoje imię i nazwisko")
        account_form.addRow("Twoja nazwa:", self.user_name)

        account_group.setLayout(account_form)
        layout.addWidget(account_group)

        imap_group = QGroupBox("Serwer IMAP (odbieranie)")
        imap_form = QFormLayout()

        self.imap_server = QLineEdit()
        self.imap_server.setPlaceholderText("imap.gmail.com")
        imap_form.addRow("Serwer IMAP:", self.imap_server)

        self.imap_port = QSpinBox()
        self.imap_port.setRange(1, 65535)
        self.imap_port.setValue(993)
        imap_form.addRow("Port IMAP:", self.imap_port)

        self.imap_ssl = QCheckBox("Użyj SSL/TLS")
        self.imap_ssl.setChecked(True)
        imap_form.addRow("", self.imap_ssl)

        imap_group.setLayout(imap_form)
        layout.addWidget(imap_group)

        smtp_group = QGroupBox("Serwer SMTP (wysyłanie)")
        smtp_form = QFormLayout()

        self.smtp_server = QLineEdit()
        self.smtp_server.setPlaceholderText("smtp.gmail.com")
        smtp_form.addRow("Serwer SMTP:", self.smtp_server)

        self.smtp_port = QSpinBox()
        self.smtp_port.setRange(1, 65535)
        self.smtp_port.setValue(587)
        smtp_form.addRow("Port SMTP:", self.smtp_port)

        self.smtp_ssl = QCheckBox("Użyj STARTTLS")
        self.smtp_ssl.setChecked(True)
        smtp_form.addRow("", self.smtp_ssl)

        smtp_group.setLayout(smtp_form)
        layout.addWidget(smtp_group)

        layout.addStretch()
        tab.setLayout(layout)
        return tab
        
    def create_signatures_tab(self):
        """Tworzy zakładkę z podpisami"""
        tab = QWidget()
        layout = QHBoxLayout()
        
        # Lewa strona - lista podpisów
        left_layout = QVBoxLayout()
        
        sig_label = QLabel("Moje podpisy:")
        sig_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(sig_label)
        
        self.signatures_list = QListWidget()
        self.signatures_list.currentRowChanged.connect(self.on_signature_selected)
        left_layout.addWidget(self.signatures_list)
        
        # Przyciski zarządzania podpisami
        sig_btn_layout = QVBoxLayout()
        
        self.btn_new_sig = QPushButton("+ Nowy podpis")
        self.btn_new_sig.clicked.connect(self.new_signature)
        sig_btn_layout.addWidget(self.btn_new_sig)
        
        self.btn_delete_sig = QPushButton("- Usuń podpis")
        self.btn_delete_sig.clicked.connect(self.delete_signature)
        self.btn_delete_sig.setEnabled(False)
        sig_btn_layout.addWidget(self.btn_delete_sig)
        
        sig_btn_layout.addStretch()
        left_layout.addLayout(sig_btn_layout)
        
        # Prawa strona - edytor podpisu
        right_layout = QVBoxLayout()
        
        # Nazwa podpisu
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nazwa:"))
        self.sig_name = QLineEdit()
        self.sig_name.setPlaceholderText("Np. Służbowy, Przyjacielski...")
        self.sig_name.setReadOnly(True)
        name_layout.addWidget(self.sig_name)
        right_layout.addLayout(name_layout)
        
        # Treść podpisu
        sig_content_label = QLabel("Treść podpisu:")
        sig_content_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        right_layout.addWidget(sig_content_label)
        
        self.sig_content = QTextEdit()
        self.sig_content.setPlaceholderText(
            "Przykład:\n\n"
            "Pozdrawiam,\n"
            "Jan Kowalski\n"
            "Specjalista ds. IT\n"
            "Tel: +48 123 456 789\n"
            "email: jan.kowalski@firma.pl"
        )
        self.sig_content.setReadOnly(True)
        right_layout.addWidget(self.sig_content)
        
        # Checkbox - domyślny podpis
        self.sig_default = QCheckBox("Użyj jako domyślny podpis")
        self.sig_default.setEnabled(False)
        right_layout.addWidget(self.sig_default)
        
        # Przyciski akcji
        sig_action_layout = QHBoxLayout()
        
        self.btn_save_sig = QPushButton("Zapisz podpis")
        self.btn_save_sig.clicked.connect(self.save_signature)
        self.btn_save_sig.setEnabled(False)
        sig_action_layout.addWidget(self.btn_save_sig)
        
        self.btn_cancel_sig = QPushButton("Anuluj")
        self.btn_cancel_sig.clicked.connect(self.cancel_signature_edit)
        self.btn_cancel_sig.setEnabled(False)
        sig_action_layout.addWidget(self.btn_cancel_sig)
        
        sig_action_layout.addStretch()
        right_layout.addLayout(sig_action_layout)
        
        # Połącz lewą i prawą stronę
        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 2)
        
        tab.setLayout(layout)
        return tab
        
    def create_filters_tab(self):
        """Tworzy zakładkę z filtrami poczty"""
        tab = QWidget()
        layout = QHBoxLayout()

        left_layout = QVBoxLayout()
        filters_label = QLabel("Zdefiniowane filtry:")
        filters_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(filters_label)

        self.filters_list = QListWidget()
        self.filters_list.currentRowChanged.connect(self.on_filter_selected)
        left_layout.addWidget(self.filters_list)

        filters_btn_layout = QVBoxLayout()
        self.btn_new_filter = QPushButton("+ Nowy filtr")
        self.btn_new_filter.clicked.connect(self.new_filter)
        filters_btn_layout.addWidget(self.btn_new_filter)

        self.btn_edit_filter = QPushButton("Edytuj filtr")
        self.btn_edit_filter.clicked.connect(self.edit_filter)
        self.btn_edit_filter.setEnabled(False)
        filters_btn_layout.addWidget(self.btn_edit_filter)

        self.btn_delete_filter = QPushButton("- Usuń filtr")
        self.btn_delete_filter.clicked.connect(self.delete_filter)
        self.btn_delete_filter.setEnabled(False)
        filters_btn_layout.addWidget(self.btn_delete_filter)

        filters_btn_layout.addStretch()
        left_layout.addLayout(filters_btn_layout)

        right_layout = QVBoxLayout()

        form_layout = QFormLayout()
        self.filter_name = QLineEdit()
        self.filter_name.setPlaceholderText("Np. Newslettery")
        self.filter_name.setReadOnly(True)
        form_layout.addRow("Nazwa filtra:", self.filter_name)

        self.filter_account = QComboBox()
        self.filter_account.setEnabled(False)
        form_layout.addRow("Konto pocztowe:", self.filter_account)

        self.filter_enabled = QCheckBox("Filtr aktywny")
        self.filter_enabled.setEnabled(False)
        form_layout.addRow("", self.filter_enabled)

        right_layout.addLayout(form_layout)

        conditions_group = QGroupBox("Warunki filtrowania")
        conditions_layout = QVBoxLayout()

        self.conditions_list = QListWidget()
        self.conditions_list.currentRowChanged.connect(self.update_conditions_button_state)
        self.conditions_list.itemDoubleClicked.connect(self.on_condition_double_clicked)
        conditions_layout.addWidget(self.conditions_list)

        conditions_buttons = QHBoxLayout()
        self.btn_add_condition = QPushButton("Dodaj warunek")
        self.btn_add_condition.clicked.connect(self.add_condition)
        self.btn_add_condition.setEnabled(False)
        conditions_buttons.addWidget(self.btn_add_condition)

        self.btn_edit_condition = QPushButton("Edytuj")
        self.btn_edit_condition.clicked.connect(self.edit_condition)
        self.btn_edit_condition.setEnabled(False)
        conditions_buttons.addWidget(self.btn_edit_condition)

        self.btn_remove_condition = QPushButton("Usuń")
        self.btn_remove_condition.clicked.connect(self.remove_condition)
        self.btn_remove_condition.setEnabled(False)
        conditions_buttons.addWidget(self.btn_remove_condition)

        conditions_buttons.addStretch()
        conditions_layout.addLayout(conditions_buttons)

        conditions_group.setLayout(conditions_layout)
        right_layout.addWidget(conditions_group)

        actions_layout = QFormLayout()

        self.filter_target_folder = QLineEdit()
        self.filter_target_folder.setPlaceholderText("Np. Newslettery")
        self.filter_target_folder.setReadOnly(True)
        actions_layout.addRow("Docelowy folder:", self.filter_target_folder)

        self.filter_tags = QLineEdit()
        self.filter_tags.setPlaceholderText("Np. VIP, Sprzedaż")
        self.filter_tags.setReadOnly(True)
        actions_layout.addRow("Tagi (przecinki):", self.filter_tags)

        self.filter_forward_to = QLineEdit()
        self.filter_forward_to.setPlaceholderText("adres1@firma.pl, adres2@firma.pl")
        self.filter_forward_to.setReadOnly(True)
        actions_layout.addRow("Przekaż dalej:", self.filter_forward_to)

        self.filter_export_pdf = QCheckBox("Eksportuj wiadomość do PDF")
        self.filter_export_pdf.setEnabled(False)
        actions_layout.addRow("", self.filter_export_pdf)

        self.filter_mark_read = QCheckBox("Oznacz wiadomość jako przeczytaną")
        self.filter_mark_read.setEnabled(False)
        actions_layout.addRow("", self.filter_mark_read)

        right_layout.addLayout(actions_layout)

        filters_action_layout = QHBoxLayout()
        self.btn_save_filter = QPushButton("Zapisz filtr")
        self.btn_save_filter.clicked.connect(self.save_filter)
        self.btn_save_filter.setEnabled(False)
        filters_action_layout.addWidget(self.btn_save_filter)

        self.btn_cancel_filter = QPushButton("Anuluj")
        self.btn_cancel_filter.clicked.connect(self.cancel_filter_edit)
        self.btn_cancel_filter.setEnabled(False)
        filters_action_layout.addWidget(self.btn_cancel_filter)

        filters_action_layout.addStretch()
        right_layout.addLayout(filters_action_layout)

        layout.addLayout(left_layout, 1)
        layout.addLayout(right_layout, 2)

        tab.setLayout(layout)
        return tab

    def load_signatures(self):
        """Wczytuje podpisy z pliku JSON"""
        if self.signatures_file.exists():
            try:
                with open(self.signatures_file, 'r', encoding='utf-8') as f:
                    self.signatures = json.load(f)
                self.update_signatures_list()
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie można wczytać podpisów: {e}")
        else:
            # Utwórz przykładowe podpisy
            self.signatures = [
                {
                    "name": "Służbowy",
                    "content": "Pozdrawiam,\nJan Kowalski\nDział IT",
                    "default": True
                },
                {
                    "name": "Krótki",
                    "content": "Pozdrawiam\nJan",
                    "default": False
                }
            ]
            self.save_signatures_to_file()
            
    def update_signatures_list(self):
        """Aktualizuje listę podpisów"""
        self.signatures_list.clear()
        for sig in self.signatures:
            default_marker = " ⭐" if sig.get('default', False) else ""
            self.signatures_list.addItem(f"{sig['name']}{default_marker}")
            
    def on_signature_selected(self, index):
        """Obsługa wyboru podpisu z listy"""
        if index >= 0 and index < len(self.signatures):
            self.current_signature = index
            self.load_signature_details(self.signatures[index])
            self.btn_delete_sig.setEnabled(True)
            self.enable_signature_editing(False)
        else:
            self.btn_delete_sig.setEnabled(False)
            
    def load_signature_details(self, signature):
        """Ładuje szczegóły podpisu do formularza"""
        self.sig_name.setText(signature.get('name', ''))
        self.sig_content.setPlainText(signature.get('content', ''))
        self.sig_default.setChecked(signature.get('default', False))
        
    def new_signature(self):
        """Tworzy nowy podpis"""
        self.current_signature = None
        self.clear_signature_form()
        self.enable_signature_editing(True)
        self.btn_save_sig.setEnabled(True)
        self.btn_cancel_sig.setEnabled(True)
        
    def clear_signature_form(self):
        """Czyści formularz podpisu"""
        self.sig_name.clear()
        self.sig_content.clear()
        self.sig_default.setChecked(False)
        
    def enable_signature_editing(self, enabled):
        """Włącza/wyłącza edycję pól podpisu"""
        self.sig_name.setReadOnly(not enabled)
        self.sig_content.setReadOnly(not enabled)
        self.sig_default.setEnabled(enabled)
        
        if not enabled:
            self.btn_save_sig.setEnabled(False)
            self.btn_cancel_sig.setEnabled(False)
            
    def save_signature(self):
        """Zapisuje podpis"""
        # Walidacja
        if not self.sig_name.text().strip():
            QMessageBox.warning(self, "Błąd", "Podaj nazwę podpisu!")
            return
            
        if not self.sig_content.toPlainText().strip():
            QMessageBox.warning(self, "Błąd", "Podpis nie może być pusty!")
            return
            
        # Przygotuj dane
        signature_data = {
            'name': self.sig_name.text().strip(),
            'content': self.sig_content.toPlainText().strip(),
            'default': self.sig_default.isChecked()
        }
        
        # Jeśli ustawiono jako domyślny, usuń flagę z innych
        if signature_data['default']:
            for sig in self.signatures:
                sig['default'] = False
        
        # Dodaj lub zaktualizuj
        if self.current_signature is None:
            self.signatures.append(signature_data)
        else:
            self.signatures[self.current_signature] = signature_data
            
        # Zapisz do pliku
        self.save_signatures_to_file()
        self.update_signatures_list()
        self.enable_signature_editing(False)
        QMessageBox.information(self, "Sukces", "Podpis został zapisany!")
        
    def save_signatures_to_file(self):
        """Zapisuje podpisy do pliku JSON"""
        try:
            with open(self.signatures_file, 'w', encoding='utf-8') as f:
                json.dump(self.signatures, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać podpisów: {e}")
            
    def cancel_signature_edit(self):
        """Anuluje edycję podpisu"""
        if self.current_signature is not None:
            self.load_signature_details(self.signatures[self.current_signature])
        else:
            self.clear_signature_form()
        self.enable_signature_editing(False)
        
    def delete_signature(self):
        """Usuwa podpis"""
        if self.current_signature is not None:
            reply = QMessageBox.question(
                self, 
                "Potwierdzenie", 
                f"Czy na pewno chcesz usunąć podpis '{self.signatures[self.current_signature]['name']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del self.signatures[self.current_signature]
                self.save_signatures_to_file()
                self.update_signatures_list()
                self.clear_signature_form()
                self.current_signature = None
        
    def load_filters(self):
        """Wczytuje filtry z pliku JSON"""
        if self.filters_file.exists():
            try:
                with open(self.filters_file, 'r', encoding='utf-8') as f:
                    raw_filters = json.load(f)
                self.filters = []
                for filter_data in raw_filters:
                    if isinstance(filter_data, dict):
                        self.filters.append(self.normalize_filter_definition(filter_data))
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie można wczytać filtrów: {e}")
                self.filters = []
        else:
            sample_filter = self.normalize_filter_definition({
                "name": "Newslettery",
                "enabled": True,
                "account_email": None,
                "conditions": [
                    {
                        "field": "subject",
                        "operator": "contains",
                        "value": "newsletter"
                    }
                ],
                "target_folder": "Newslettery",
                "tags": ["newsletter"],
                "forward_to": [],
                "export_pdf": False,
                "mark_as_read": False
            })
            self.filters = [sample_filter]
            self.save_filters_to_file()

        self.current_filter = None
        self.clear_filter_form()
        self.update_filters_list()

    def save_filters_to_file(self):
        """Zapisuje filtry do pliku JSON"""
        try:
            self.filters_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self.filters_file, 'w', encoding='utf-8') as f:
                json.dump(self.filters, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać filtrów: {e}")

    def normalize_filter_definition(self, filter_data):
        """Zapewnia zgodność struktury filtra z aktualnym formatem"""
        normalized = dict(filter_data)

        legacy_field = normalized.pop('field', None)
        legacy_operator = normalized.pop('operator', 'contains')
        legacy_value = normalized.pop('value', '')

        conditions = normalized.get('conditions')
        if not conditions:
            conditions = []
            if legacy_field:
                conditions.append({
                    'field': legacy_field,
                    'operator': legacy_operator,
                    'value': legacy_value
                })
        normalized['conditions'] = [
            {
                'field': condition.get('field', 'subject'),
                'operator': condition.get('operator', 'contains'),
                'value': condition.get('value', '')
            }
            for condition in conditions
            if isinstance(condition, dict)
        ]

        if not normalized['conditions']:
            normalized['conditions'].append({
                'field': 'subject',
                'operator': 'contains',
                'value': ''
            })

        forward_to = normalized.get('forward_to', [])
        if isinstance(forward_to, str):
            forward_to = [addr.strip() for addr in re.split(r'[;,]', forward_to) if addr.strip()]
        normalized['forward_to'] = forward_to

        tags = normalized.get('tags', [])
        if isinstance(tags, str):
            tags = [tag.strip() for tag in re.split(r'[;,]', tags) if tag.strip()]
        elif isinstance(tags, list):
            tags = [str(tag).strip() for tag in tags if str(tag).strip()]
        else:
            tags = []
        normalized['tags'] = tags

        account_email = normalized.get('account_email') or normalized.get('account')
        normalized['account_email'] = account_email if account_email else None

        normalized.setdefault('name', 'Nowy filtr')
        normalized.setdefault('enabled', True)
        normalized.setdefault('target_folder', '')
        normalized.setdefault('tags', [])
        normalized.setdefault('mark_as_read', False)
        normalized.setdefault('export_pdf', False)

        return normalized

    def update_filters_list(self):
        """Aktualizuje listę filtrów"""
        if not hasattr(self, 'filters_list'):
            return

        self.filters_list.blockSignals(True)
        self.filters_list.clear()

        for filter_data in self.filters:
            status = " [ON]" if filter_data.get('enabled', True) else " [OFF]"
            account_label = self.resolve_account_label(filter_data.get('account_email'))
            tags = filter_data.get('tags') or []
            tags_suffix = " " + " ".join(f"#{tag}" for tag in tags) if tags else ""
            self.filters_list.addItem(f"{filter_data['name']}{status} – {account_label}{tags_suffix}")

        self.filters_list.blockSignals(False)

        if self.current_filter is not None and 0 <= self.current_filter < self.filters_list.count():
            self.filters_list.setCurrentRow(self.current_filter)
        elif self.filters_list.count() > 0:
            self.filters_list.setCurrentRow(0)
        else:
            self.on_filter_selected(-1)

        self.update_filter_buttons()

    def on_filter_selected(self, index):
        """Obsługuje wybór filtra z listy"""
        if self.is_filter_editing:
            return

        if index is not None and 0 <= index < len(self.filters):
            self.current_filter = index
            self.load_filter_details(self.filters[index])
        else:
            self.current_filter = None
            self.clear_filter_form()

        self.update_filter_buttons()

    def load_filter_details(self, filter_data):
        """Ładuje dane filtra do formularza"""
        self.filter_name.setText(filter_data.get('name', ''))
        self.filter_enabled.setChecked(filter_data.get('enabled', True))

        account_email = filter_data.get('account_email')
        account_index = self.filter_account.findData(account_email)
        if account_index >= 0:
            self.filter_account.setCurrentIndex(account_index)
        else:
            self.filter_account.setCurrentIndex(0)

        self.editing_conditions = [dict(condition) for condition in filter_data.get('conditions', [])]
        self.update_conditions_list_widget()

        self.filter_target_folder.setText(filter_data.get('target_folder', ''))
        tags = filter_data.get('tags', [])
        if isinstance(tags, list):
            tags_text = ', '.join(tags)
        else:
            tags_text = str(tags)
        self.filter_tags.setText(tags_text)
        forward_to = filter_data.get('forward_to', [])
        if isinstance(forward_to, list):
            forward_text = ', '.join(forward_to)
        else:
            forward_text = str(forward_to)
        self.filter_forward_to.setText(forward_text)
        self.filter_export_pdf.setChecked(filter_data.get('export_pdf', False))
        self.filter_mark_read.setChecked(filter_data.get('mark_as_read', False))

    def new_filter(self):
        """Tworzy nowy filtr"""
        if self.is_filter_editing:
            return

        self.current_filter = None
        self.filters_list.blockSignals(True)
        self.filters_list.clearSelection()
        self.filters_list.blockSignals(False)

        self.clear_filter_form()
        self.enable_filter_editing(True)
        self.filter_name.setFocus()

    def edit_filter(self):
        """Rozpoczyna edycję istniejącego filtra"""
        if self.is_filter_editing or self.current_filter is None:
            return

        self.enable_filter_editing(True)
        self.filter_name.setFocus()

    def clear_filter_form(self):
        """Czyści formularz filtra"""
        self.filter_name.clear()
        self.filter_account.setCurrentIndex(0)
        self.filter_enabled.setChecked(True)
        self.editing_conditions = []
        self.update_conditions_list_widget()
        self.filter_target_folder.clear()
        self.filter_tags.clear()
        self.filter_forward_to.clear()
        self.filter_export_pdf.setChecked(False)
        self.filter_mark_read.setChecked(False)

    def enable_filter_editing(self, enabled):
        """Włącza/wyłącza edycję pól filtra"""
        self.is_filter_editing = enabled

        self.filter_name.setReadOnly(not enabled)
        self.filter_account.setEnabled(enabled)
        self.filter_enabled.setEnabled(enabled)
        self.filter_target_folder.setReadOnly(not enabled)
        self.filter_tags.setReadOnly(not enabled)
        self.filter_forward_to.setReadOnly(not enabled)
        self.filter_export_pdf.setEnabled(enabled)
        self.filter_mark_read.setEnabled(enabled)

        self.filters_list.setEnabled(not enabled)
        self.btn_save_filter.setEnabled(enabled)
        self.btn_cancel_filter.setEnabled(enabled)
        self.btn_add_condition.setEnabled(enabled)

        self.update_conditions_button_state()
        self.update_filter_buttons()

    def save_filter(self):
        """Zapisuje filtr"""
        if not self.filter_name.text().strip():
            QMessageBox.warning(self, "Błąd", "Podaj nazwę filtra!")
            return

        if not self.editing_conditions:
            QMessageBox.warning(self, "Błąd", "Dodaj przynajmniej jeden warunek!")
            return

        forward_raw = self.filter_forward_to.text().strip()
        if forward_raw:
            forward_to = [addr.strip() for addr in re.split(r'[;,]', forward_raw) if addr.strip()]
        else:
            forward_to = []

        tags_raw = self.filter_tags.text().strip()
        if tags_raw:
            tags_list = [tag.strip() for tag in re.split(r'[;,]', tags_raw) if tag.strip()]
        else:
            tags_list = []

        filter_data = {
            'name': self.filter_name.text().strip(),
            'enabled': self.filter_enabled.isChecked(),
            'account_email': self.filter_account.currentData(),
            'conditions': [dict(condition) for condition in self.editing_conditions],
            'target_folder': self.filter_target_folder.text().strip(),
            'tags': tags_list,
            'forward_to': forward_to,
            'export_pdf': self.filter_export_pdf.isChecked(),
            'mark_as_read': self.filter_mark_read.isChecked()
        }

        if self.current_filter is None:
            self.filters.append(filter_data)
            self.current_filter = len(self.filters) - 1
        else:
            self.filters[self.current_filter] = filter_data

        self.save_filters_to_file()
        self.update_filters_list()
        self.enable_filter_editing(False)

        if self.current_filter is not None:
            self.load_filter_details(self.filters[self.current_filter])

        QMessageBox.information(self, "Sukces", "Filtr został zapisany!")

    def cancel_filter_edit(self):
        """Anuluje edycję filtra"""
        if self.current_filter is not None and self.current_filter < len(self.filters):
            self.load_filter_details(self.filters[self.current_filter])
        else:
            self.clear_filter_form()

        self.enable_filter_editing(False)

    def delete_filter(self):
        """Usuwa filtr"""
        if self.current_filter is None or self.is_filter_editing:
            return

        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno chcesz usunąć filtr '{self.filters[self.current_filter]['name']}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )

        if reply == QMessageBox.StandardButton.Yes:
            deleted_index = self.current_filter
            del self.filters[deleted_index]
            self.save_filters_to_file()

            if self.filters:
                self.current_filter = min(deleted_index, len(self.filters) - 1)
            else:
                self.current_filter = None

            self.update_filters_list()

            if self.current_filter is not None:
                self.load_filter_details(self.filters[self.current_filter])
            else:
                self.clear_filter_form()

            self.enable_filter_editing(False)

    def update_filter_accounts(self):
        """Aktualizuje listę kont dostępnych w filtrach"""
        if not hasattr(self, 'filter_account'):
            return

        current_value = self.filter_account.currentData() if self.filter_account.count() else None

        self.filter_account.blockSignals(True)
        self.filter_account.clear()
        self.filter_account.addItem("Dowolne konto", None)

        for account in self.accounts:
            email = account.get('email', '')
            name = account.get('name') or email or "Konto"
            label = f"{name} ({email})" if email else name
            self.filter_account.addItem(label, email or None)

        if current_value is not None:
            index = self.filter_account.findData(current_value)
        else:
            index = 0

        if index == -1:
            index = 0

        self.filter_account.setCurrentIndex(index)
        self.filter_account.blockSignals(False)

    def update_filter_buttons(self):
        """Aktualizuje stan przycisków operujących na filtrach"""
        has_selection = self.current_filter is not None and not self.is_filter_editing

        self.btn_new_filter.setEnabled(not self.is_filter_editing)
        self.btn_edit_filter.setEnabled(has_selection)
        self.btn_delete_filter.setEnabled(has_selection)

    def update_conditions_list_widget(self):
        """Odświeża listę warunków filtra"""
        if not hasattr(self, 'conditions_list'):
            return

        self.conditions_list.blockSignals(True)
        self.conditions_list.clear()

        for condition in self.editing_conditions:
            self.conditions_list.addItem(self.format_condition(condition))

        self.conditions_list.blockSignals(False)
        self.update_conditions_button_state()

    def update_conditions_button_state(self):
        """Aktualizuje stan przycisków edycji warunków"""
        has_selection = self.conditions_list.currentRow() >= 0
        self.btn_edit_condition.setEnabled(self.is_filter_editing and has_selection)
        self.btn_remove_condition.setEnabled(self.is_filter_editing and has_selection)

    def format_condition(self, condition):
        """Zwraca czytelny opis warunku"""
        field_label = FIELD_LABELS.get(condition.get('field'), condition.get('field', ''))
        operator_label = OPERATOR_LABELS.get(condition.get('operator'), condition.get('operator', ''))
        value = condition.get('value', '')
        return f"{field_label} {operator_label} \"{value}\""

    def resolve_account_label(self, account_email):
        """Buduje etykietę konta dla listy filtrów"""
        if not account_email:
            return "Dowolne konto"

        for account in self.accounts:
            if account.get('email') == account_email:
                name = account.get('name')
                if name and name != account_email:
                    return f"{name} ({account_email})"
                return account_email

        return f"{account_email} (brak w konfiguracji)"

    def on_condition_double_clicked(self, _item):
        """Obsługuje dwuklik na warunku"""
        if self.is_filter_editing:
            self.edit_condition()

    def add_condition(self):
        """Dodaje nowy warunek do filtra"""
        if not self.is_filter_editing:
            return

        dialog = FilterConditionDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.editing_conditions.append(dialog.get_condition())
            self.update_conditions_list_widget()

    def edit_condition(self):
        """Edytuje zaznaczony warunek"""
        if not self.is_filter_editing:
            return

        index = self.conditions_list.currentRow()
        if index < 0 or index >= len(self.editing_conditions):
            return

        dialog = FilterConditionDialog(self, self.editing_conditions[index])
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.editing_conditions[index] = dialog.get_condition()
            self.update_conditions_list_widget()
            self.conditions_list.setCurrentRow(index)

    def remove_condition(self):
        """Usuwa zaznaczony warunek"""
        if not self.is_filter_editing:
            return

        index = self.conditions_list.currentRow()
        if 0 <= index < len(self.editing_conditions):
            del self.editing_conditions[index]
            self.update_conditions_list_widget()

    def load_accounts(self):
        """Wczytuje konta z pliku JSON"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    raw_accounts = json.load(f)
                self.accounts = [
                    self._normalize_account_data(account)
                    for account in raw_accounts
                    if isinstance(account, dict)
                ]
                self.update_accounts_list()
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie można wczytać kont: {e}")
        else:
            # Utwórz folder jeśli nie istnieje
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            
    def update_accounts_list(self):
        """Aktualizuje listę kont"""
        self.accounts_list.blockSignals(True)
        self.accounts_list.clear()
        for account in self.accounts:
            self.accounts_list.addItem(f"{account['name']} ({account['email']})")
        self.accounts_list.blockSignals(False)

        self.update_filter_accounts()

        if self.accounts:
            target_row = self.current_account if self.current_account is not None else 0
            target_row = max(0, min(target_row, self.accounts_list.count() - 1))
            self.accounts_list.setCurrentRow(target_row)
        else:
            self.accounts_list.clearSelection()
            self.current_account = None
            self.enable_editing(True)
            self.clear_form()
            
    def on_account_selected(self, index):
        """Obsługa wyboru konta z listy"""
        if index >= 0 and index < len(self.accounts):
            self.current_account = index
            self.load_account_details(self.accounts[index])
            self.btn_delete.setEnabled(True)
            self.is_account_editing = False
            self.enable_editing(True)
            self.update_account_actions()
        else:
            self.current_account = None
            self.btn_delete.setEnabled(False)
            self.enable_editing(True)
            self.clear_form()
            
    def load_account_details(self, account):
        """Ładuje szczegóły konta do formularza"""
        self._apply_account_to_form(account)
        
    def new_account(self):
        """Tworzy nowe konto"""
        self.current_account = None
        self.accounts_list.clearSelection()
        self.clear_form()
        self.enable_editing(True)
        self.btn_delete.setEnabled(False)
        self.is_account_editing = False
        self.update_account_actions()
        
    def clear_form(self):
        """Czyści formularz"""
        self._apply_account_to_form(ACCOUNT_DEFAULTS)
        self.is_account_editing = False
        self.update_account_actions()
        
    def enable_editing(self, enabled):
        """Włącza/wyłącza edycję pól"""
        self.account_name.setReadOnly(not enabled)
        self.email_address.setReadOnly(not enabled)
        self.password.setReadOnly(not enabled)
        self.user_name.setReadOnly(not enabled)
        self.imap_server.setReadOnly(not enabled)
        self.imap_port.setReadOnly(not enabled)
        self.smtp_server.setReadOnly(not enabled)
        self.smtp_port.setReadOnly(not enabled)
        self.imap_ssl.setEnabled(enabled)
        self.smtp_ssl.setEnabled(enabled)
        self.update_account_actions()
            
    def save_account(self):
        """Zapisuje konto"""
        # Walidacja
        if not self.account_name.text().strip():
            QMessageBox.warning(self, "Błąd", "Podaj nazwę konta!")
            return
            
        if not self.email_address.text().strip():
            QMessageBox.warning(self, "Błąd", "Podaj adres email!")
            return
            
        account_data = self._normalize_account_data(self._collect_account_form_data())

        # Dodaj lub zaktualizuj
        if self.current_account is None:
            self.accounts.append(account_data)
            self.current_account = len(self.accounts) - 1
        else:
            self.accounts[self.current_account] = account_data
            
        # Zapisz do pliku
        try:
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(self.accounts, f, indent=2, ensure_ascii=False)
            
            self.update_accounts_list()
            self.is_account_editing = False
            self._apply_account_to_form(account_data)
            self.update_account_actions()
            QMessageBox.information(self, "Sukces", "Konto zostało zapisane!")
            
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie można zapisać konta: {e}")
            
    def cancel_edit(self):
        """Anuluje edycję"""
        if self.current_account is not None:
            self.load_account_details(self.accounts[self.current_account])
        else:
            self.clear_form()
        self.is_account_editing = False
        self.enable_editing(True)
        self.btn_delete.setEnabled(self.current_account is not None)
        self.update_account_actions()
        
    def delete_account(self):
        """Usuwa konto"""
        if self.current_account is not None:
            reply = QMessageBox.question(
                self, 
                "Potwierdzenie", 
                f"Czy na pewno chcesz usunąć konto '{self.accounts[self.current_account]['name']}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                del self.accounts[self.current_account]
                
                try:
                    with open(self.config_file, 'w', encoding='utf-8') as f:
                        json.dump(self.accounts, f, indent=2, ensure_ascii=False)
                    
                    self.update_accounts_list()
                    self.clear_form()
                    self.current_account = None
                    
                except Exception as e:
                    QMessageBox.critical(self, "Błąd", f"Nie można usunąć konta: {e}")
                    
    def test_connection(self):
        """Testuje połączenie z serwerem"""
        account_data = self._collect_account_form_data()

        missing = []
        field_labels = {
            "name": "Nazwa konta",
            "email": "Adres email",
            "password": "Hasło",
            "imap_server": "Serwer IMAP",
            "smtp_server": "Serwer SMTP",
        }

        for key, label in field_labels.items():
            if not account_data.get(key):
                missing.append(label)

        if missing:
            QMessageBox.warning(
                self,
                "Brak danych",
                "Uzupełnij wymagane pola przed testem połączenia:\n- " + "\n- ".join(missing),
            )
            return

        normalized = self._normalize_account_data(account_data)

        self.btn_test.setEnabled(False)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        try:
            imap_ok, imap_error = self._test_imap_connection(normalized)
            smtp_ok, smtp_error = self._test_smtp_connection(normalized)
        finally:
            QApplication.restoreOverrideCursor()
            self.btn_test.setEnabled(True)

        messages = []
        if imap_ok:
            messages.append("✅ Połączenie IMAP zakończone pomyślnie.")
        else:
            messages.append("❌ IMAP: " + imap_error)

        if smtp_ok:
            messages.append("✅ Połączenie SMTP zakończone pomyślnie.")
        else:
            messages.append("❌ SMTP: " + smtp_error)

        if imap_ok and smtp_ok:
            QMessageBox.information(
                self,
                "Test połączenia",
                "\n".join(messages),
            )
        else:
            QMessageBox.warning(
                self,
                "Problemy z połączeniem",
                "\n".join(messages),
            )

    def _test_imap_connection(self, account_data):
        """Próbuje nawiązać połączenie IMAP i zalogować użytkownika."""
        try:
            if account_data["imap_ssl"]:
                imap = imaplib.IMAP4_SSL(
                    account_data["imap_server"],
                    account_data["imap_port"],
                    timeout=10,
                )
            else:
                imap = imaplib.IMAP4(
                    account_data["imap_server"],
                    account_data["imap_port"],
                    timeout=10,
                )

            try:
                imap.login(account_data["email"], account_data["password"])
            finally:
                try:
                    imap.logout()
                except Exception:
                    pass

            return True, ""
        except (socket.timeout, socket.gaierror, imaplib.IMAP4.error, OSError) as exc:
            return False, str(exc)

    def _test_smtp_connection(self, account_data):
        """Próbuje nawiązać połączenie SMTP i zalogować użytkownika."""
        server = None
        try:
            if account_data["smtp_ssl"] and account_data["smtp_port"] == 465:
                server = smtplib.SMTP_SSL(
                    account_data["smtp_server"],
                    account_data["smtp_port"],
                    timeout=10,
                )
                server.ehlo()
            else:
                server = smtplib.SMTP(
                    account_data["smtp_server"],
                    account_data["smtp_port"],
                    timeout=10,
                )
                server.ehlo()
                if account_data["smtp_ssl"]:
                    server.starttls()
                    server.ehlo()

            server.login(account_data["email"], account_data["password"])
            server.quit()
            return True, ""
        except (socket.timeout, socket.gaierror, smtplib.SMTPException, OSError) as exc:
            if server is not None:
                try:
                    server.quit()
                except Exception:
                    pass
            return False, str(exc)
        
    def get_accounts(self):
        """Zwraca listę kont"""
        return self.accounts
    
    def get_signatures(self):
        """Zwraca listę podpisów"""
        return self.signatures
    
    def get_default_signature(self):
        """Zwraca domyślny podpis"""
        for sig in self.signatures:
            if sig.get('default', False):
                return sig.get('content', '')
        return ''

    def get_filters(self):
        """Zwraca listę filtrów"""
        return self.filters


def show_config_dialog(parent=None):
    """Funkcja pomocnicza do wyświetlenia okna konfiguracji"""
    dialog = MailConfigDialog(parent)
    dialog.exec()
    return dialog.get_accounts()


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setApplicationName("Konfiguracja poczty")
    dialog = MailConfigDialog()
    dialog.exec()
    sys.exit()
