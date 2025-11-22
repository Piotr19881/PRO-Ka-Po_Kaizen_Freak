"""
Moduł konfiguracji ProMail

Funkcjonalność:
- Zarządzanie podpisami email
- Konfiguracja filtrów poczty
- Ustawienia autorespondera
- Układ kolumn tabeli
- Zarządzanie tagami

Uwaga: Konta email są zarządzane przez główną aplikację (email_settings_card.py)

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-11
"""

import json
import os
import re
from pathlib import Path
from datetime import datetime, timedelta
from PyQt6.QtWidgets import (
    QApplication, QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
    QLineEdit, QPushButton, QLabel, QSpinBox, QCheckBox,
    QListWidget, QGroupBox, QMessageBox, QTabWidget, QWidget,
    QTextEdit, QListWidgetItem, QComboBox, QDialogButtonBox,
    QAbstractItemView, QHeaderView, QColorDialog
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor
from typing import Dict, List, Any
from .autoresponder import AutoresponderRule


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
    """Okno dialogowe konfiguracji ProMail (bez kont email - te są w głównych ustawieniach)"""
    
    def __init__(self, parent=None, mail_view_parent=None):
        super().__init__(parent)
        self.mail_view_parent = mail_view_parent  # Referencja do MailView dla interakcji z tagami/kolumnami
        self.signatures_file = Path("mail_client/mail_signatures.json")
        self.filters_file = Path("mail_client/mail_filters.json")
        self.autoresponder_file = Path("mail_client/autoresponder_rules.json")
        self.signatures = []
        self.filters = []
        self.autoresponder_rules = []
        self.editing_conditions = []
        self.current_signature = None
        self.current_filter = None
        self.is_filter_editing = False
        self.init_ui()
        self.load_signatures()
        self.load_filters()
        self.load_autoresponder_rules()
        
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        self.setWindowTitle("⚙️ Konfiguracja ProMail")
        self.setMinimumSize(900, 600)
        
        layout = QVBoxLayout()
        
        # Zakładki dla różnych ustawień
        self.tabs = QTabWidget()
        
        # Zakładka: Podpisy
        signatures_tab = self.create_signatures_tab()
        self.tabs.addTab(signatures_tab, "✍️ Podpisy")
        
        # Zakładka: Filtry poczty
        filters_tab = self.create_filters_tab()
        self.tabs.addTab(filters_tab, "🔍 Filtry")
        
        # Zakładka: Autoresponder
        autoresponder_tab = self.create_autoresponder_tab()
        self.tabs.addTab(autoresponder_tab, "🤖 Autoresponder")
        
        # Zakładka: Układ kolumn
        columns_tab = self.create_columns_tab()
        self.tabs.addTab(columns_tab, "📋 Układ kolumn")
        
        # Zakładka: Tagi
        tags_tab = self.create_tags_tab()
        self.tabs.addTab(tags_tab, "🏷️ Tagi")

        layout.addWidget(self.tabs)
        
        # Przyciski dialogu
        dialog_buttons = QHBoxLayout()
        dialog_buttons.addStretch()
        
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        btn_close.setFixedWidth(100)
        dialog_buttons.addWidget(btn_close)
        
        layout.addLayout(dialog_buttons)
        
        self.setLayout(layout)

    def create_signatures_tab(self):
        """Tworzy zakład kę z podpisami"""
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
    
    def create_autoresponder_tab(self):
        """Tworzy zakładkę autorespondera"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Nagłówek
        header = QLabel("Zarządzaj automatycznymi odpowiedziami na wiadomości")
        header.setStyleSheet("font-size: 14px; font-weight: bold; padding: 10px;")
        layout.addWidget(header)
        
        # Główny układ (lista reguł + szczegóły)
        main_layout = QHBoxLayout()
        
        # Lewa strona - lista reguł
        left_panel = QVBoxLayout()
        
        rules_label = QLabel("Reguły autorespondera:")
        rules_label.setStyleSheet("font-weight: bold;")
        left_panel.addWidget(rules_label)
        
        self.autoresponder_rules_list = QListWidget()
        self.autoresponder_rules_list.currentRowChanged.connect(self.on_autoresponder_rule_selected)
        left_panel.addWidget(self.autoresponder_rules_list)
        
        # Przyciski zarządzania regułami
        rules_buttons = QHBoxLayout()
        
        btn_add_rule = QPushButton("➕ Dodaj")
        btn_add_rule.clicked.connect(self.add_autoresponder_rule)
        rules_buttons.addWidget(btn_add_rule)
        
        btn_remove_rule = QPushButton("❌ Usuń")
        btn_remove_rule.clicked.connect(self.remove_autoresponder_rule)
        rules_buttons.addWidget(btn_remove_rule)
        
        btn_duplicate = QPushButton("📋 Duplikuj")
        btn_duplicate.clicked.connect(self.duplicate_autoresponder_rule)
        rules_buttons.addWidget(btn_duplicate)
        
        left_panel.addLayout(rules_buttons)
        
        # Prawa strona - szczegóły reguły
        right_panel = QVBoxLayout()
        
        # Grupa: Podstawowe ustawienia
        basic_group = QGroupBox("Podstawowe ustawienia")
        basic_layout = QVBoxLayout()
        
        # Checkbox włącz/wyłącz
        self.autoresponder_enabled_check = QCheckBox("✓ Reguła włączona")
        self.autoresponder_enabled_check.setChecked(True)
        basic_layout.addWidget(self.autoresponder_enabled_check)
        
        # Nazwa reguły
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nazwa reguły:"))
        self.autoresponder_name_input = QLineEdit()
        self.autoresponder_name_input.setPlaceholderText("np. Odpowiedź dla klientów")
        name_layout.addWidget(self.autoresponder_name_input)
        basic_layout.addLayout(name_layout)
        
        basic_group.setLayout(basic_layout)
        right_panel.addWidget(basic_group)
        
        # Grupa: Warunki
        condition_group = QGroupBox("Warunki wyzwalające")
        condition_layout = QVBoxLayout()
        
        cond_type_layout = QHBoxLayout()
        cond_type_layout.addWidget(QLabel("Gdy w polu:"))
        self.autoresponder_condition_type_combo = QComboBox()
        self.autoresponder_condition_type_combo.addItems([
            "Wszystkie wiadomości",
            "Nadawca (FROM)",
            "Temat (SUBJECT)",
            "Treść wiadomości"
        ])
        self.autoresponder_condition_type_combo.setCurrentIndex(0)
        cond_type_layout.addWidget(self.autoresponder_condition_type_combo)
        condition_layout.addLayout(cond_type_layout)
        
        cond_value_layout = QHBoxLayout()
        cond_value_layout.addWidget(QLabel("Zawiera tekst:"))
        self.autoresponder_condition_value_input = QLineEdit()
        self.autoresponder_condition_value_input.setPlaceholderText("np. @firma.pl, urgent, zapytanie")
        cond_value_layout.addWidget(self.autoresponder_condition_value_input)
        condition_layout.addLayout(cond_value_layout)
        
        condition_group.setLayout(condition_layout)
        right_panel.addWidget(condition_group)
        
        # Grupa: Odpowiedź
        response_group = QGroupBox("Treść automatycznej odpowiedzi")
        response_layout = QVBoxLayout()
        
        subject_layout = QHBoxLayout()
        subject_layout.addWidget(QLabel("Temat:"))
        self.autoresponder_response_subject_input = QLineEdit()
        self.autoresponder_response_subject_input.setPlaceholderText("Re: Automatyczna odpowiedź")
        subject_layout.addWidget(self.autoresponder_response_subject_input)
        response_layout.addLayout(subject_layout)
        
        response_layout.addWidget(QLabel("Treść wiadomości:"))
        self.autoresponder_response_body_input = QTextEdit()
        self.autoresponder_response_body_input.setPlaceholderText(
            "Witam,\n\n"
            "Dziękuję za wiadomość. Odpowiem w ciągu 24 godzin.\n\n"
            "Pozdrawiam,\n"
            "Bot"
        )
        self.autoresponder_response_body_input.setMaximumHeight(120)
        response_layout.addWidget(self.autoresponder_response_body_input)
        
        response_group.setLayout(response_layout)
        right_panel.addWidget(response_group)
        
        # Grupa: Ograniczenia
        limits_group = QGroupBox("Ograniczenia i harmonogram")
        limits_layout = QVBoxLayout()
        
        # Maksymalna liczba odpowiedzi
        max_resp_layout = QHBoxLayout()
        max_resp_layout.addWidget(QLabel("Max odpowiedzi na nadawcę:"))
        self.autoresponder_max_responses_spin = QSpinBox()
        self.autoresponder_max_responses_spin.setMinimum(1)
        self.autoresponder_max_responses_spin.setMaximum(100)
        self.autoresponder_max_responses_spin.setValue(1)
        self.autoresponder_max_responses_spin.setToolTip("Ile razy wysłać automatyczną odpowiedź temu samemu nadawcy")
        max_resp_layout.addWidget(self.autoresponder_max_responses_spin)
        max_resp_layout.addStretch()
        limits_layout.addLayout(max_resp_layout)
        
        # Dni tygodnia
        days_layout = QHBoxLayout()
        days_layout.addWidget(QLabel("Aktywne dni:"))
        self.autoresponder_day_checks = {}
        days = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Niedz"]
        for i, day in enumerate(days):
            check = QCheckBox(day)
            check.setChecked(i < 5)  # Domyślnie Pon-Pt
            self.autoresponder_day_checks[i] = check
            days_layout.addWidget(check)
        limits_layout.addLayout(days_layout)
        
        # Godziny
        hours_layout = QHBoxLayout()
        hours_layout.addWidget(QLabel("Aktywne godziny:"))
        self.autoresponder_hours_start_spin = QSpinBox()
        self.autoresponder_hours_start_spin.setMinimum(0)
        self.autoresponder_hours_start_spin.setMaximum(23)
        self.autoresponder_hours_start_spin.setValue(0)
        self.autoresponder_hours_start_spin.setSuffix(":00")
        hours_layout.addWidget(self.autoresponder_hours_start_spin)
        hours_layout.addWidget(QLabel("-"))
        self.autoresponder_hours_end_spin = QSpinBox()
        self.autoresponder_hours_end_spin.setMinimum(0)
        self.autoresponder_hours_end_spin.setMaximum(23)
        self.autoresponder_hours_end_spin.setValue(23)
        self.autoresponder_hours_end_spin.setSuffix(":00")
        hours_layout.addWidget(self.autoresponder_hours_end_spin)
        hours_layout.addStretch()
        limits_layout.addLayout(hours_layout)
        
        limits_group.setLayout(limits_layout)
        right_panel.addWidget(limits_group)
        
        # Przycisk zapisz zmiany
        save_rule_btn = QPushButton("💾 Zapisz zmiany w regule")
        save_rule_btn.clicked.connect(self.save_current_autoresponder_rule)
        save_rule_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        right_panel.addWidget(save_rule_btn)
        
        right_panel.addStretch()
        
        # Dodaj panele do głównego layoutu
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)
        
        layout.addLayout(main_layout)
        
        tab.setLayout(layout)
        return tab
    
    def create_columns_tab(self):
        """Tworzy zakładkę układu kolumn"""
        tab = QWidget()
        main_layout = QVBoxLayout()
        
        main_layout.addWidget(QLabel("Zarządzaj kolejnością i widocznością kolumn:"))
        
        # Sprawdź czy mamy referencję do mail_view
        if not self.mail_view_parent:
            info_label = QLabel(
                "⚠️ Brak połączenia z modułem ProMail.\n\n"
                "Karta Układ kolumn wymaga aktywnego modułu ProMail aby zarządzać kolumnami."
            )
            info_label.setWordWrap(True)
            info_label.setStyleSheet("padding: 20px; font-size: 11pt; color: orange;")
            main_layout.addWidget(info_label)
            main_layout.addStretch()
            tab.setLayout(main_layout)
            return tab
        
        # Kontener z listą i przyciskami
        content_layout = QHBoxLayout()
        
        # Lista kolumn
        self.columns_list = QListWidget()
        self.columns_list.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        
        # Pobierz aktualną kolejność kolumn (jeśli istnieje) lub użyj domyślnej
        if not hasattr(self.mail_view_parent, 'column_order'):
            self.mail_view_parent.column_order = list(range(12))  # 0-11
        
        # Wypełnij listę według aktualnej kolejności
        for col_idx in self.mail_view_parent.column_order:
            item = QListWidgetItem()
            is_visible = self.mail_view_parent.column_visibility.get(col_idx, True)
            checkbox_text = "✓" if is_visible else "✗"
            item.setText(f"{checkbox_text} {self.mail_view_parent.column_names[col_idx]}")
            item.setData(Qt.ItemDataRole.UserRole, col_idx)
            # Zaznacz/odznacz w zależności od widoczności
            if is_visible:
                item.setCheckState(Qt.CheckState.Checked)
            else:
                item.setCheckState(Qt.CheckState.Unchecked)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            self.columns_list.addItem(item)
        
        content_layout.addWidget(self.columns_list)
        
        # Przyciski do zmiany kolejności
        buttons_layout = QVBoxLayout()
        
        move_up_btn = QPushButton("⬆️ W górę")
        move_up_btn.setToolTip("Przesuń wybraną kolumnę w górę")
        buttons_layout.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("⬇️ W dół")
        move_down_btn.setToolTip("Przesuń wybraną kolumnę w dół")
        buttons_layout.addWidget(move_down_btn)
        
        buttons_layout.addSpacing(20)
        
        toggle_btn = QPushButton("🔄 Przełącz widoczność")
        toggle_btn.setToolTip("Przełącz widoczność wybranej kolumny")
        buttons_layout.addWidget(toggle_btn)
        
        buttons_layout.addStretch()
        
        # Funkcje obsługi przycisków
        def move_up():
            current_row = self.columns_list.currentRow()
            if current_row > 0:
                item = self.columns_list.takeItem(current_row)
                self.columns_list.insertItem(current_row - 1, item)
                self.columns_list.setCurrentRow(current_row - 1)
        
        def move_down():
            current_row = self.columns_list.currentRow()
            if current_row < self.columns_list.count() - 1 and current_row >= 0:
                item = self.columns_list.takeItem(current_row)
                self.columns_list.insertItem(current_row + 1, item)
                self.columns_list.setCurrentRow(current_row + 1)
        
        def toggle_visibility():
            current_item = self.columns_list.currentItem()
            if current_item:
                if current_item.checkState() == Qt.CheckState.Checked:
                    current_item.setCheckState(Qt.CheckState.Unchecked)
                    col_idx = current_item.data(Qt.ItemDataRole.UserRole)
                    current_item.setText(f"✗ {self.mail_view_parent.column_names[col_idx]}")
                else:
                    current_item.setCheckState(Qt.CheckState.Checked)
                    col_idx = current_item.data(Qt.ItemDataRole.UserRole)
                    current_item.setText(f"✓ {self.mail_view_parent.column_names[col_idx]}")
        
        move_up_btn.clicked.connect(move_up)
        move_down_btn.clicked.connect(move_down)
        toggle_btn.clicked.connect(toggle_visibility)
        
        content_layout.addLayout(buttons_layout)
        main_layout.addLayout(content_layout)
        
        main_layout.addWidget(QLabel("\n💡 Wskazówka: Możesz także przeciągać kolumny myszką aby zmienić ich kolejność."))
        
        # Przycisk zastosuj zmiany
        apply_btn = QPushButton("✔️ Zastosuj zmiany")
        apply_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        apply_btn.setToolTip("Zastosuj nową kolejność i widoczność kolumn")
        apply_btn.clicked.connect(self.apply_column_settings)
        main_layout.addWidget(apply_btn)
        
        tab.setLayout(main_layout)
        return tab
    
    def apply_column_settings(self):
        """Stosuje ustawienia kolumn do mail_view"""
        if not self.mail_view_parent or not hasattr(self, 'columns_list'):
            return
        
        # Zapisz nową kolejność i widoczność
        new_order = []
        for i in range(self.columns_list.count()):
            item = self.columns_list.item(i)
            col_idx = item.data(Qt.ItemDataRole.UserRole)
            new_order.append(col_idx)
            self.mail_view_parent.column_visibility[col_idx] = (item.checkState() == Qt.CheckState.Checked)
        
        self.mail_view_parent.column_order = new_order
        
        # Przebuduj tabelę z nową kolejnością
        if hasattr(self.mail_view_parent, 'rebuild_mail_table_with_order'):
            self.mail_view_parent.rebuild_mail_table_with_order()
        
        QMessageBox.information(self, "Sukces", "Ustawienia kolumn zostały zastosowane!")

    
    def create_tags_tab(self):
        """Tworzy zakładkę tagów"""
        tab = QWidget()
        layout = QVBoxLayout()
        
        # Sprawdź czy mamy referencję do mail_view
        if not self.mail_view_parent:
            info_label = QLabel(
                "⚠️ Brak połączenia z modułem ProMail.\n\n"
                "Karta Tagi wymaga aktywnego modułu ProMail aby zarządzać tagami."
            )
            info_label.setWordWrap(True)
            info_label.setStyleSheet("padding: 20px; font-size: 11pt; color: orange;")
            layout.addWidget(info_label)
            layout.addStretch()
            tab.setLayout(layout)
            return tab
        
        # Tabs dla tagów wiadomości i kontaktów
        tabs = QTabWidget()
        layout.addWidget(tabs)
        
        # Tab 1: Tagi wiadomości
        mail_tags_widget = QWidget()
        mail_tags_layout = QVBoxLayout(mail_tags_widget)
        
        mail_tags_label = QLabel("Tagi dla wiadomości e-mail:")
        mail_tags_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        mail_tags_layout.addWidget(mail_tags_label)
        
        mail_tags_list = QListWidget()
        mail_tags_list.setObjectName("mail_tags_list")
        for tag in self.mail_view_parent.mail_tags:
            tag_name = tag.get("name", "")
            tag_color = tag.get("color")
            item = QListWidgetItem(f"🏷️ {tag_name}")
            if tag_color:
                item.setBackground(QColor(tag_color))
                # Dostosuj kolor tekstu w zależności od jasności tła
                if QColor(tag_color).lightness() < 128:
                    item.setForeground(QColor("white"))
            mail_tags_list.addItem(item)
        mail_tags_layout.addWidget(mail_tags_list)
        
        mail_tags_btn_layout = QHBoxLayout()
        
        btn_add_mail_tag = QPushButton("➕ Dodaj tag wiadomości")
        btn_add_mail_tag.clicked.connect(lambda: self.mail_view_parent.add_tag_from_manager(mail_tags_list, "mail"))
        mail_tags_btn_layout.addWidget(btn_add_mail_tag)
        
        btn_edit_mail_tag = QPushButton("✏️ Edytuj")
        btn_edit_mail_tag.clicked.connect(lambda: self.mail_view_parent.edit_tag_from_manager(mail_tags_list, "mail"))
        mail_tags_btn_layout.addWidget(btn_edit_mail_tag)
        
        btn_delete_mail_tag = QPushButton("🗑️ Usuń")
        btn_delete_mail_tag.clicked.connect(lambda: self.mail_view_parent.delete_tag_from_manager(mail_tags_list, "mail"))
        mail_tags_btn_layout.addWidget(btn_delete_mail_tag)
        
        mail_tags_layout.addLayout(mail_tags_btn_layout)
        tabs.addTab(mail_tags_widget, "📧 Tagi wiadomości")
        
        # Tab 2: Definicje tagów kontaktów
        contact_tag_def_widget = QWidget()
        contact_tag_def_layout = QVBoxLayout(contact_tag_def_widget)
        
        contact_tag_def_label = QLabel("Definicje tagów dla kontaktów:")
        contact_tag_def_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        contact_tag_def_layout.addWidget(contact_tag_def_label)
        
        contact_tag_def_list = QListWidget()
        contact_tag_def_list.setObjectName("contact_tag_def_list")
        for tag in self.mail_view_parent.contact_tag_definitions:
            tag_name = tag.get("name", "")
            tag_color = tag.get("color")
            item = QListWidgetItem(f"🏷️ {tag_name}")
            if tag_color:
                item.setBackground(QColor(tag_color))
                if QColor(tag_color).lightness() < 128:
                    item.setForeground(QColor("white"))
            contact_tag_def_list.addItem(item)
        contact_tag_def_layout.addWidget(contact_tag_def_list)
        
        contact_tag_def_btn_layout = QHBoxLayout()
        
        btn_add_contact_tag_def = QPushButton("➕ Dodaj tag kontaktu")
        btn_add_contact_tag_def.clicked.connect(lambda: self.mail_view_parent.add_tag_from_manager(contact_tag_def_list, "contact"))
        contact_tag_def_btn_layout.addWidget(btn_add_contact_tag_def)
        
        btn_edit_contact_tag_def = QPushButton("✏️ Edytuj")
        btn_edit_contact_tag_def.clicked.connect(lambda: self.mail_view_parent.edit_tag_from_manager(contact_tag_def_list, "contact"))
        contact_tag_def_btn_layout.addWidget(btn_edit_contact_tag_def)
        
        btn_delete_contact_tag_def = QPushButton("🗑️ Usuń")
        btn_delete_contact_tag_def.clicked.connect(lambda: self.mail_view_parent.delete_tag_from_manager(contact_tag_def_list, "contact"))
        contact_tag_def_btn_layout.addWidget(btn_delete_contact_tag_def)
        
        contact_tag_def_layout.addLayout(contact_tag_def_btn_layout)
        tabs.addTab(contact_tag_def_widget, "🏷️ Tagi kontaktów")
        
        # Tab 3: Przypisanie tagów do kontaktów
        contact_assignment_widget = QWidget()
        contact_assignment_layout = QVBoxLayout(contact_assignment_widget)
        
        contact_assignment_label = QLabel("Przypisz tagi do kontaktów:")
        contact_assignment_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        contact_assignment_layout.addWidget(contact_assignment_label)
        
        contact_list = QListWidget()
        contact_list.setObjectName("contact_list")
        # Pobierz wszystkie unikalne adresy email z maili
        all_emails = set()
        for folder_mails in self.mail_view_parent.sample_mails.values():
            for mail in folder_mails:
                email = self.mail_view_parent.extract_email_address(mail.get("from", ""))
                if email:
                    all_emails.add(email)
        
        for email in sorted(all_emails):
            name = self.mail_view_parent.extract_display_name_for_email(email)
            display = f"{name} <{email}>" if name else email
            item = QListWidgetItem(f"👤 {display}")
            item.setData(Qt.ItemDataRole.UserRole, email)
            
            # Dodaj tagi do tooltipa i tekstu
            if email in self.mail_view_parent.contact_tags and self.mail_view_parent.contact_tags[email]:
                tags_str = ", ".join(self.mail_view_parent.contact_tags[email])
                item.setToolTip(f"Tagi: {tags_str}")
                item.setText(f"👤 {display} [{tags_str}]")
            
            contact_list.addItem(item)
        contact_assignment_layout.addWidget(contact_list)
        
        contact_assignment_btn_layout = QHBoxLayout()
        
        btn_add_contact_tag = QPushButton("🏷️ Dodaj tag")
        btn_add_contact_tag.clicked.connect(lambda: self.mail_view_parent.add_contact_tag(contact_list))
        contact_assignment_btn_layout.addWidget(btn_add_contact_tag)
        
        btn_remove_contact_tag = QPushButton("❌ Usuń tag")
        btn_remove_contact_tag.clicked.connect(lambda: self.mail_view_parent.remove_contact_tag(contact_list))
        contact_assignment_btn_layout.addWidget(btn_remove_contact_tag)
        
        contact_assignment_layout.addLayout(contact_assignment_btn_layout)
        tabs.addTab(contact_assignment_widget, "👥 Przypisanie")
        
        # Tab 4: Kolory kontaktów
        contact_colors_widget = QWidget()
        contact_colors_layout = QVBoxLayout(contact_colors_widget)
        
        contact_colors_label = QLabel("Kolory dla kontaktów:")
        contact_colors_label.setStyleSheet("font-weight: bold; font-size: 12px;")
        contact_colors_layout.addWidget(contact_colors_label)
        
        contact_colors_list = QListWidget()
        contact_colors_list.setObjectName("contact_colors_list")
        
        for email in sorted(all_emails):
            name = self.mail_view_parent.extract_display_name_for_email(email)
            display = f"{name} <{email}>" if name else email
            item = QListWidgetItem(f"👤 {display}")
            item.setData(Qt.ItemDataRole.UserRole, email)
            
            # Zastosuj kolor jeśli jest ustawiony
            if email in self.mail_view_parent.contact_colors:
                item.setBackground(self.mail_view_parent.contact_colors[email])
                if self.mail_view_parent.contact_colors[email].lightness() < 128:
                    item.setForeground(QColor("white"))
            
            contact_colors_list.addItem(item)
        contact_colors_layout.addWidget(contact_colors_list)
        
        contact_colors_btn_layout = QHBoxLayout()
        
        btn_set_color = QPushButton("🎨 Ustaw kolor")
        btn_set_color.clicked.connect(lambda: self.mail_view_parent.set_contact_color(contact_colors_list))
        contact_colors_btn_layout.addWidget(btn_set_color)
        
        btn_clear_color = QPushButton("🔄 Wyczyść kolor")
        btn_clear_color.clicked.connect(lambda: self.mail_view_parent.clear_contact_color(contact_colors_list))
        contact_colors_btn_layout.addWidget(btn_clear_color)
        
        contact_colors_layout.addLayout(contact_colors_btn_layout)
        tabs.addTab(contact_colors_widget, "🎨 Kolory")
        
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
                    normalized = self.normalize_filter_definition(filter_data)
                    self.filters.append(normalized)
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
        """Aktualizuje listę kont dostępnych w filtrach - pobiera z głównej aplikacji"""
        if not hasattr(self, 'filter_account'):
            return

        current_value = self.filter_account.currentData() if self.filter_account.count() else None

        self.filter_account.blockSignals(True)
        self.filter_account.clear()
        self.filter_account.addItem("Dowolne konto", None)
        
        # TODO: Pobierz konta z EmailAccountsDatabase zamiast z self.accounts
        # from src.database.email_accounts_db import EmailAccountsDatabase
        # db = EmailAccountsDatabase()
        # accounts = db.get_all_accounts()
        # for account in accounts:
        #     email = account.get('email', '')
        #     name = account.get('name') or email or "Konto"
        #     label = f"{name} ({email})" if email else name
        #     self.filter_account.addItem(label, email or None)

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
        
        # TODO: Pobierz konta z EmailAccountsDatabase
        return f"{account_email}"

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
    
    # ==================== AUTORESPONDER METHODS ====================
    
    def load_autoresponder_rules(self):
        """Wczytuje reguły autorespondera z pliku"""
        if self.autoresponder_file.exists():
            try:
                with open(self.autoresponder_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.autoresponder_rules = [AutoresponderRule(rule_data) for rule_data in data]
            except Exception as e:
                print(f"Błąd wczytywania reguł autorespondera: {e}")
                self.autoresponder_rules = []
        else:
            self.autoresponder_rules = []
        
        # Odśwież listę po wczytaniu
        if hasattr(self, 'autoresponder_rules_list'):
            self.populate_autoresponder_rules_list()
    
    def save_autoresponder_rules(self):
        """Zapisuje reguły autorespondera do pliku"""
        try:
            self.autoresponder_file.parent.mkdir(parents=True, exist_ok=True)
            data = [rule.to_dict() for rule in self.autoresponder_rules]
            with open(self.autoresponder_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisywania reguł autorespondera: {e}")
    
    def populate_autoresponder_rules_list(self):
        """Wypełnia listę reguł autorespondera"""
        self.autoresponder_rules_list.clear()
        for rule in self.autoresponder_rules:
            status = "✓" if rule.enabled else "✗"
            item = QListWidgetItem(f"{status} {rule.name}")
            self.autoresponder_rules_list.addItem(item)
        
        if self.autoresponder_rules:
            self.autoresponder_rules_list.setCurrentRow(0)
    
    def on_autoresponder_rule_selected(self, index: int):
        """Obsługuje wybór reguły z listy"""
        if index < 0 or index >= len(self.autoresponder_rules):
            return
        
        rule = self.autoresponder_rules[index]
        
        # Wypełnij pola danymi reguły
        self.autoresponder_enabled_check.setChecked(rule.enabled)
        self.autoresponder_name_input.setText(rule.name)
        
        # Typ warunku
        type_map = {"all": 0, "sender": 1, "subject": 2, "body": 3}
        self.autoresponder_condition_type_combo.setCurrentIndex(type_map.get(rule.condition_type, 0))
        
        self.autoresponder_condition_value_input.setText(rule.condition_value)
        self.autoresponder_response_subject_input.setText(rule.response_subject)
        self.autoresponder_response_body_input.setPlainText(rule.response_body)
        self.autoresponder_max_responses_spin.setValue(rule.max_responses_per_sender)
        
        # Dni tygodnia
        for i in range(7):
            self.autoresponder_day_checks[i].setChecked(i in rule.active_days)
        
        self.autoresponder_hours_start_spin.setValue(rule.active_hours_start)
        self.autoresponder_hours_end_spin.setValue(rule.active_hours_end)
    
    def save_current_autoresponder_rule(self):
        """Zapisuje zmiany w aktualnie wybranej regule"""
        current_row = self.autoresponder_rules_list.currentRow()
        if current_row < 0 or current_row >= len(self.autoresponder_rules):
            QMessageBox.warning(self, "Brak wyboru", "Wybierz regułę do edycji")
            return
        
        rule = self.autoresponder_rules[current_row]
        
        # Zapisz dane z formularza
        rule.enabled = self.autoresponder_enabled_check.isChecked()
        rule.name = self.autoresponder_name_input.text() or "Bez nazwy"
        
        type_map = {0: "all", 1: "sender", 2: "subject", 3: "body"}
        rule.condition_type = type_map[self.autoresponder_condition_type_combo.currentIndex()]
        
        rule.condition_value = self.autoresponder_condition_value_input.text()
        rule.response_subject = self.autoresponder_response_subject_input.text()
        rule.response_body = self.autoresponder_response_body_input.toPlainText()
        rule.max_responses_per_sender = self.autoresponder_max_responses_spin.value()
        
        # Dni tygodnia
        rule.active_days = [i for i in range(7) if self.autoresponder_day_checks[i].isChecked()]
        
        rule.active_hours_start = self.autoresponder_hours_start_spin.value()
        rule.active_hours_end = self.autoresponder_hours_end_spin.value()
        
        # Zapisz do pliku
        self.save_autoresponder_rules()
        
        # Odśwież listę
        self.populate_autoresponder_rules_list()
        self.autoresponder_rules_list.setCurrentRow(current_row)
        
        QMessageBox.information(self, "Zapisano", f"Reguła '{rule.name}' została zaktualizowana")
    
    def add_autoresponder_rule(self):
        """Dodaje nową regułę autorespondera"""
        new_rule = AutoresponderRule()
        new_rule.name = f"Reguła {len(self.autoresponder_rules) + 1}"
        self.autoresponder_rules.append(new_rule)
        self.save_autoresponder_rules()
        self.populate_autoresponder_rules_list()
        self.autoresponder_rules_list.setCurrentRow(len(self.autoresponder_rules) - 1)
    
    def remove_autoresponder_rule(self):
        """Usuwa wybraną regułę"""
        current_row = self.autoresponder_rules_list.currentRow()
        if current_row < 0 or current_row >= len(self.autoresponder_rules):
            QMessageBox.warning(self, "Brak wyboru", "Wybierz regułę do usunięcia")
            return
        
        rule_name = self.autoresponder_rules[current_row].name
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno usunąć regułę '{rule_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.autoresponder_rules[current_row]
            self.save_autoresponder_rules()
            self.populate_autoresponder_rules_list()
    
    def duplicate_autoresponder_rule(self):
        """Duplikuje wybraną regułę"""
        current_row = self.autoresponder_rules_list.currentRow()
        if current_row < 0 or current_row >= len(self.autoresponder_rules):
            QMessageBox.warning(self, "Brak wyboru", "Wybierz regułę do zduplikowania")
            return
        
        original = self.autoresponder_rules[current_row]
        duplicate = AutoresponderRule(original.to_dict())
        duplicate.name = f"{original.name} (kopia)"
        duplicate.responded_to = {}  # Resetuj historię odpowiedzi
        
        self.autoresponder_rules.append(duplicate)
        self.save_autoresponder_rules()
        self.populate_autoresponder_rules_list()
        self.autoresponder_rules_list.setCurrentRow(len(self.autoresponder_rules) - 1)
    
    def get_autoresponder_rules(self) -> List[AutoresponderRule]:
        """Zwraca listę reguł autorespondera"""
        return self.autoresponder_rules
    
    # ==================== END AUTORESPONDER METHODS ====================
    
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


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    app.setApplicationName("Konfiguracja ProMail")
    dialog = MailConfigDialog()
    dialog.exec()
    sys.exit()
