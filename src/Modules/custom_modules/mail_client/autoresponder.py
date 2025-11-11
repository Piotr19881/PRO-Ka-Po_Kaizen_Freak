"""
Moduł autorespondera dla klienta pocztowego
Automatycznie odpowiada na wiadomości na podstawie zdefiniowanych reguł
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QListWidget, QListWidgetItem, QLineEdit, QTextEdit,
    QComboBox, QCheckBox, QSpinBox, QGroupBox, QMessageBox,
    QDialogButtonBox
)
from PyQt6.QtCore import Qt
from typing import Dict, List, Any
import json
from pathlib import Path
from datetime import datetime, timedelta


class AutoresponderRule:
    """Klasa reprezentująca regułę autorespondera"""
    
    def __init__(self, data: Dict[str, Any] = None):
        if data is None:
            data = {}
        
        self.enabled = data.get("enabled", True)
        self.name = data.get("name", "Nowa reguła")
        self.condition_type = data.get("condition_type", "sender")  # sender, subject, body, all
        self.condition_value = data.get("condition_value", "")
        self.response_subject = data.get("response_subject", "Automatyczna odpowiedź")
        self.response_body = data.get("response_body", "Dziękuję za wiadomość. Odpowiem jak najszybciej.")
        self.max_responses_per_sender = data.get("max_responses_per_sender", 1)  # Ile razy odpowiedzieć temu samemu nadawcy
        self.active_days = data.get("active_days", [0, 1, 2, 3, 4])  # 0=Pon, 6=Niedz
        self.active_hours_start = data.get("active_hours_start", 0)  # 0-23
        self.active_hours_end = data.get("active_hours_end", 23)  # 0-23
        self.responded_to = data.get("responded_to", {})  # email -> timestamp ostatniej odpowiedzi
    
    def to_dict(self) -> Dict[str, Any]:
        """Konwertuje regułę do słownika"""
        return {
            "enabled": self.enabled,
            "name": self.name,
            "condition_type": self.condition_type,
            "condition_value": self.condition_value,
            "response_subject": self.response_subject,
            "response_body": self.response_body,
            "max_responses_per_sender": self.max_responses_per_sender,
            "active_days": self.active_days,
            "active_hours_start": self.active_hours_start,
            "active_hours_end": self.active_hours_end,
            "responded_to": self.responded_to
        }
    
    def matches_mail(self, mail: Dict[str, Any]) -> bool:
        """Sprawdza czy mail pasuje do warunku reguły"""
        if not self.enabled:
            return False
        
        # Sprawdź dzień tygodnia
        now = datetime.now()
        if now.weekday() not in self.active_days:
            return False
        
        # Sprawdź godziny
        current_hour = now.hour
        if not (self.active_hours_start <= current_hour <= self.active_hours_end):
            return False
        
        # Sprawdź warunek
        if self.condition_type == "all":
            return True
        elif self.condition_type == "sender":
            sender = mail.get("from", "").lower()
            return self.condition_value.lower() in sender
        elif self.condition_type == "subject":
            subject = mail.get("subject", "").lower()
            return self.condition_value.lower() in subject
        elif self.condition_type == "body":
            body = mail.get("body", "").lower()
            return self.condition_value.lower() in body
        
        return False
    
    def can_respond_to(self, sender_email: str) -> bool:
        """Sprawdza czy można wysłać odpowiedź do tego nadawcy"""
        if sender_email not in self.responded_to:
            return True
        
        responses_count = len(self.responded_to[sender_email])
        if responses_count >= self.max_responses_per_sender:
            # Sprawdź czy ostatnia odpowiedź była dawno (> 7 dni)
            last_response = max(self.responded_to[sender_email])
            last_date = datetime.fromisoformat(last_response)
            if datetime.now() - last_date > timedelta(days=7):
                # Resetuj licznik
                self.responded_to[sender_email] = []
                return True
            return False
        
        return True
    
    def mark_responded(self, sender_email: str):
        """Oznacza że wysłano odpowiedź do nadawcy"""
        if sender_email not in self.responded_to:
            self.responded_to[sender_email] = []
        self.responded_to[sender_email].append(datetime.now().isoformat())


class AutoresponderDialog(QDialog):
    """Dialog do zarządzania regułami autorespondera"""
    
    def __init__(self, parent=None, rules: List[AutoresponderRule] = None):
        super().__init__(parent)
        self.setWindowTitle("🤖 Autoresponder - Automatyczne odpowiedzi")
        self.resize(900, 600)
        
        self.rules = rules if rules else []
        
        self.setup_ui()
        self.populate_rules_list()
    
    def setup_ui(self):
        """Tworzy interfejs dialogu"""
        layout = QVBoxLayout(self)
        
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
        
        self.rules_list = QListWidget()
        self.rules_list.currentRowChanged.connect(self.on_rule_selected)
        left_panel.addWidget(self.rules_list)
        
        # Przyciski zarządzania regułami
        rules_buttons = QHBoxLayout()
        
        btn_add_rule = QPushButton("➕ Dodaj")
        btn_add_rule.clicked.connect(self.add_rule)
        rules_buttons.addWidget(btn_add_rule)
        
        btn_remove_rule = QPushButton("❌ Usuń")
        btn_remove_rule.clicked.connect(self.remove_rule)
        rules_buttons.addWidget(btn_remove_rule)
        
        btn_duplicate = QPushButton("📋 Duplikuj")
        btn_duplicate.clicked.connect(self.duplicate_rule)
        rules_buttons.addWidget(btn_duplicate)
        
        left_panel.addLayout(rules_buttons)
        
        # Prawa strona - szczegóły reguły
        right_panel = QVBoxLayout()
        
        # Grupa: Podstawowe ustawienia
        basic_group = QGroupBox("Podstawowe ustawienia")
        basic_layout = QVBoxLayout()
        
        # Checkbox włącz/wyłącz
        self.enabled_check = QCheckBox("✓ Reguła włączona")
        self.enabled_check.setChecked(True)
        basic_layout.addWidget(self.enabled_check)
        
        # Nazwa reguły
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nazwa reguły:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("np. Odpowiedź dla klientów")
        name_layout.addWidget(self.name_input)
        basic_layout.addLayout(name_layout)
        
        basic_group.setLayout(basic_layout)
        right_panel.addWidget(basic_group)
        
        # Grupa: Warunki
        condition_group = QGroupBox("Warunki wyzwalające")
        condition_layout = QVBoxLayout()
        
        cond_type_layout = QHBoxLayout()
        cond_type_layout.addWidget(QLabel("Gdy w polu:"))
        self.condition_type_combo = QComboBox()
        self.condition_type_combo.addItems([
            "Wszystkie wiadomości",
            "Nadawca (FROM)",
            "Temat (SUBJECT)",
            "Treść wiadomości"
        ])
        self.condition_type_combo.setCurrentIndex(0)
        cond_type_layout.addWidget(self.condition_type_combo)
        condition_layout.addLayout(cond_type_layout)
        
        cond_value_layout = QHBoxLayout()
        cond_value_layout.addWidget(QLabel("Zawiera tekst:"))
        self.condition_value_input = QLineEdit()
        self.condition_value_input.setPlaceholderText("np. @firma.pl, urgent, zapytanie")
        cond_value_layout.addWidget(self.condition_value_input)
        condition_layout.addLayout(cond_value_layout)
        
        condition_group.setLayout(condition_layout)
        right_panel.addWidget(condition_group)
        
        # Grupa: Odpowiedź
        response_group = QGroupBox("Treść automatycznej odpowiedzi")
        response_layout = QVBoxLayout()
        
        subject_layout = QHBoxLayout()
        subject_layout.addWidget(QLabel("Temat:"))
        self.response_subject_input = QLineEdit()
        self.response_subject_input.setPlaceholderText("Re: Automatyczna odpowiedź")
        subject_layout.addWidget(self.response_subject_input)
        response_layout.addLayout(subject_layout)
        
        response_layout.addWidget(QLabel("Treść wiadomości:"))
        self.response_body_input = QTextEdit()
        self.response_body_input.setPlaceholderText(
            "Witam,\n\n"
            "Dziękuję za wiadomość. Odpowiem w ciągu 24 godzin.\n\n"
            "Pozdrawiam,\n"
            "Bot"
        )
        self.response_body_input.setMaximumHeight(120)
        response_layout.addWidget(self.response_body_input)
        
        response_group.setLayout(response_layout)
        right_panel.addWidget(response_group)
        
        # Grupa: Ograniczenia
        limits_group = QGroupBox("Ograniczenia i harmonogram")
        limits_layout = QVBoxLayout()
        
        # Maksymalna liczba odpowiedzi
        max_resp_layout = QHBoxLayout()
        max_resp_layout.addWidget(QLabel("Max odpowiedzi na nadawcę:"))
        self.max_responses_spin = QSpinBox()
        self.max_responses_spin.setMinimum(1)
        self.max_responses_spin.setMaximum(100)
        self.max_responses_spin.setValue(1)
        self.max_responses_spin.setToolTip("Ile razy wysłać automatyczną odpowiedź temu samemu nadawcy")
        max_resp_layout.addWidget(self.max_responses_spin)
        max_resp_layout.addStretch()
        limits_layout.addLayout(max_resp_layout)
        
        # Dni tygodnia
        days_layout = QHBoxLayout()
        days_layout.addWidget(QLabel("Aktywne dni:"))
        self.day_checks = {}
        days = ["Pon", "Wt", "Śr", "Czw", "Pt", "Sob", "Niedz"]
        for i, day in enumerate(days):
            check = QCheckBox(day)
            check.setChecked(i < 5)  # Domyślnie Pon-Pt
            self.day_checks[i] = check
            days_layout.addWidget(check)
        limits_layout.addLayout(days_layout)
        
        # Godziny
        hours_layout = QHBoxLayout()
        hours_layout.addWidget(QLabel("Aktywne godziny:"))
        self.hours_start_spin = QSpinBox()
        self.hours_start_spin.setMinimum(0)
        self.hours_start_spin.setMaximum(23)
        self.hours_start_spin.setValue(0)
        self.hours_start_spin.setSuffix(":00")
        hours_layout.addWidget(self.hours_start_spin)
        hours_layout.addWidget(QLabel("-"))
        self.hours_end_spin = QSpinBox()
        self.hours_end_spin.setMinimum(0)
        self.hours_end_spin.setMaximum(23)
        self.hours_end_spin.setValue(23)
        self.hours_end_spin.setSuffix(":00")
        hours_layout.addWidget(self.hours_end_spin)
        hours_layout.addStretch()
        limits_layout.addLayout(hours_layout)
        
        limits_group.setLayout(limits_layout)
        right_panel.addWidget(limits_group)
        
        # Przycisk zapisz zmiany
        save_rule_btn = QPushButton("💾 Zapisz zmiany w regule")
        save_rule_btn.clicked.connect(self.save_current_rule)
        save_rule_btn.setStyleSheet("font-weight: bold; padding: 8px;")
        right_panel.addWidget(save_rule_btn)
        
        right_panel.addStretch()
        
        # Dodaj panele do głównego layoutu
        main_layout.addLayout(left_panel, 1)
        main_layout.addLayout(right_panel, 2)
        
        layout.addLayout(main_layout)
        
        # Przyciski dialogu
        btn_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        btn_box.accepted.connect(self.accept)
        btn_box.rejected.connect(self.reject)
        layout.addWidget(btn_box)
    
    def populate_rules_list(self):
        """Wypełnia listę reguł"""
        self.rules_list.clear()
        for rule in self.rules:
            status = "✓" if rule.enabled else "✗"
            item = QListWidgetItem(f"{status} {rule.name}")
            self.rules_list.addItem(item)
        
        if self.rules:
            self.rules_list.setCurrentRow(0)
    
    def on_rule_selected(self, index: int):
        """Obsługuje wybór reguły z listy"""
        if index < 0 or index >= len(self.rules):
            return
        
        rule = self.rules[index]
        
        # Wypełnij pola danymi reguły
        self.enabled_check.setChecked(rule.enabled)
        self.name_input.setText(rule.name)
        
        # Typ warunku
        type_map = {"all": 0, "sender": 1, "subject": 2, "body": 3}
        self.condition_type_combo.setCurrentIndex(type_map.get(rule.condition_type, 0))
        
        self.condition_value_input.setText(rule.condition_value)
        self.response_subject_input.setText(rule.response_subject)
        self.response_body_input.setPlainText(rule.response_body)
        self.max_responses_spin.setValue(rule.max_responses_per_sender)
        
        # Dni tygodnia
        for i in range(7):
            self.day_checks[i].setChecked(i in rule.active_days)
        
        self.hours_start_spin.setValue(rule.active_hours_start)
        self.hours_end_spin.setValue(rule.active_hours_end)
    
    def save_current_rule(self):
        """Zapisuje zmiany w aktualnie wybranej regule"""
        current_row = self.rules_list.currentRow()
        if current_row < 0 or current_row >= len(self.rules):
            QMessageBox.warning(self, "Brak wyboru", "Wybierz regułę do edycji")
            return
        
        rule = self.rules[current_row]
        
        # Zapisz dane z formularza
        rule.enabled = self.enabled_check.isChecked()
        rule.name = self.name_input.text() or "Bez nazwy"
        
        type_map = {0: "all", 1: "sender", 2: "subject", 3: "body"}
        rule.condition_type = type_map[self.condition_type_combo.currentIndex()]
        
        rule.condition_value = self.condition_value_input.text()
        rule.response_subject = self.response_subject_input.text()
        rule.response_body = self.response_body_input.toPlainText()
        rule.max_responses_per_sender = self.max_responses_spin.value()
        
        # Dni tygodnia
        rule.active_days = [i for i in range(7) if self.day_checks[i].isChecked()]
        
        rule.active_hours_start = self.hours_start_spin.value()
        rule.active_hours_end = self.hours_end_spin.value()
        
        # Odśwież listę
        self.populate_rules_list()
        self.rules_list.setCurrentRow(current_row)
        
        QMessageBox.information(self, "Zapisano", f"Reguła '{rule.name}' została zaktualizowana")
    
    def add_rule(self):
        """Dodaje nową regułę"""
        new_rule = AutoresponderRule()
        new_rule.name = f"Reguła {len(self.rules) + 1}"
        self.rules.append(new_rule)
        self.populate_rules_list()
        self.rules_list.setCurrentRow(len(self.rules) - 1)
    
    def remove_rule(self):
        """Usuwa wybraną regułę"""
        current_row = self.rules_list.currentRow()
        if current_row < 0 or current_row >= len(self.rules):
            QMessageBox.warning(self, "Brak wyboru", "Wybierz regułę do usunięcia")
            return
        
        rule_name = self.rules[current_row].name
        reply = QMessageBox.question(
            self,
            "Potwierdzenie",
            f"Czy na pewno usunąć regułę '{rule_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.rules[current_row]
            self.populate_rules_list()
    
    def duplicate_rule(self):
        """Duplikuje wybraną regułę"""
        current_row = self.rules_list.currentRow()
        if current_row < 0 or current_row >= len(self.rules):
            QMessageBox.warning(self, "Brak wyboru", "Wybierz regułę do zduplikowania")
            return
        
        original = self.rules[current_row]
        duplicate = AutoresponderRule(original.to_dict())
        duplicate.name = f"{original.name} (kopia)"
        duplicate.responded_to = {}  # Resetuj historię odpowiedzi
        
        self.rules.append(duplicate)
        self.populate_rules_list()
        self.rules_list.setCurrentRow(len(self.rules) - 1)
    
    def get_rules(self) -> List[AutoresponderRule]:
        """Zwraca listę reguł"""
        return self.rules


class AutoresponderManager:
    """Menadżer autorespondera - zarządza regułami i wysyłaniem odpowiedzi"""
    
    def __init__(self, config_file: Path):
        self.config_file = config_file
        self.rules: List[AutoresponderRule] = []
        self.load_rules()
    
    def load_rules(self):
        """Wczytuje reguły z pliku"""
        if self.config_file.exists():
            try:
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.rules = [AutoresponderRule(rule_data) for rule_data in data]
            except Exception as e:
                print(f"Błąd wczytywania reguł autorespondera: {e}")
                self.rules = []
        else:
            self.rules = []
    
    def save_rules(self):
        """Zapisuje reguły do pliku"""
        try:
            self.config_file.parent.mkdir(parents=True, exist_ok=True)
            data = [rule.to_dict() for rule in self.rules]
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"Błąd zapisywania reguł autorespondera: {e}")
    
    def process_mail(self, mail: Dict[str, Any]) -> List[Dict[str, str]]:
        """
        Przetwarza mail i zwraca listę odpowiedzi do wysłania
        Każda odpowiedź to dict z kluczami: to, subject, body
        """
        responses = []
        
        sender = mail.get("from", "")
        sender_email = self._extract_email(sender)
        
        if not sender_email:
            return responses
        
        for rule in self.rules:
            if not rule.matches_mail(mail):
                continue
            
            if not rule.can_respond_to(sender_email):
                continue
            
            # Utwórz odpowiedź
            response = {
                "to": sender,
                "subject": rule.response_subject,
                "body": rule.response_body
            }
            
            responses.append(response)
            rule.mark_responded(sender_email)
            
            # Zapisz zmiany (zaktualizowana historia responded_to)
            self.save_rules()
        
        return responses
    
    def _extract_email(self, from_field: str) -> str:
        """Wydobywa adres email z pola FROM"""
        import re
        match = re.search(r'<(.+?)>', from_field)
        if match:
            return match.group(1).strip()
        return from_field.strip()
    
    def open_dialog(self, parent=None) -> bool:
        """Otwiera dialog zarządzania regułami, zwraca True jeśli zapisano"""
        dialog = AutoresponderDialog(parent, self.rules)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.rules = dialog.get_rules()
            self.save_rules()
            return True
        return False
