"""
Okna dialogowe dla Habbit Tracker
Zawiera różne typy dialogów do edycji nawyków oraz zarządzania kolumnami
"""

import os
from datetime import datetime, date
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QPushButton, QCheckBox, QSpinBox, QTimeEdit, QTextEdit,
    QSlider, QRadioButton, QButtonGroup, QDateEdit, QComboBox,
    QMessageBox, QDialogButtonBox, QFormLayout, QGroupBox, QWidget
)
from PyQt6.QtCore import Qt, QDate, QTime, pyqtSignal
from PyQt6.QtGui import QIntValidator

# Import i18n
from ...utils.i18n_manager import t


class BaseHabbitDialog(QDialog):
    """Bazowa klasa dialogu z wyborem daty"""
    
    def __init__(self, parent=None, habit_name="", current_value="", max_date=None):
        super().__init__(parent)
        self.habit_name = habit_name
        self.current_value = current_value
        self.max_date = max_date or date.today()
        
        self.setModal(True)
        self.setMinimumWidth(300)
        self.setup_base_ui()
        
    def setup_base_ui(self):
        """Tworzy podstawowy layout z datą"""
        main_layout = QVBoxLayout(self)
        
        # Nagłówek
        title_label = QLabel(t("habit.dialog.edit_title", "Edytuj nawyk: {name}").format(name=self.habit_name))
        title_label.setStyleSheet("font-weight: bold; font-size: 14px; margin-bottom: 10px;")
        main_layout.addWidget(title_label)
        
        # Wybór daty
        date_group = QGroupBox(t("habit.dialog.date", "Data"))
        date_layout = QFormLayout(date_group)
        
        self.date_edit = QDateEdit()
        self.date_edit.setDate(QDate.currentDate())
        self.date_edit.setMaximumDate(QDate(self.max_date.year, self.max_date.month, self.max_date.day))
        self.date_edit.setCalendarPopup(True)
        date_layout.addRow(t("habit.dialog.select_date", "Wybierz datę:"), self.date_edit)
        
        main_layout.addWidget(date_group)
        
        # Miejsce na kontrolki specyficzne dla typu
        self.content_layout = QVBoxLayout()
        main_layout.addLayout(self.content_layout)
        
        # Przyciski
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        main_layout.addWidget(self.button_box)
        
    def get_selected_date(self):
        """Zwraca wybraną datę jako string YYYY-MM-DD"""
        return self.date_edit.date().toString("yyyy-MM-dd")
    
    def get_value(self) -> str:
        """Metoda do nadpisania w klasach pochodnych"""
        return ""


class CheckboxHabbitDialog(BaseHabbitDialog):
    """Dialog dla nawyku typu checkbox (odznacz)"""
    
    def __init__(self, parent=None, habit_name="", current_value="", max_date=None):
        super().__init__(parent, habit_name, current_value, max_date)
        self.setWindowTitle(t("habit.type.checkbox", "Checkbox"))
        self.setup_content()
        
    def setup_content(self):
        """Tworzy kontrolki dla typu checkbox"""
        info_group = QGroupBox(t("habit.dialog.value", "Wartość"))
        info_layout = QVBoxLayout(info_group)
        
        info_label = QLabel(t("habit.message.checkbox_info", "Naciśnięcie OK oznacza wykonanie tego nawyku w wybranym dniu."))
        info_label.setWordWrap(True)
        info_layout.addWidget(info_label)
        
        # Status aktualny
        current_status = t("habit.status.done", "Wykonano") if self.current_value == "1" else t("habit.status.not_done", "Nie wykonano")
        status_label = QLabel(f"{t('habit.dialog.current_status', 'Aktualny status')}: {current_status}")
        status_label.setStyleSheet("font-weight: bold;")
        info_layout.addWidget(status_label)
        
        self.content_layout.addWidget(info_group)
        
    def get_value(self) -> str:
        """Zwraca '1' dla zaznaczenia"""
        return "1"


class CounterHabbitDialog(BaseHabbitDialog):
    """Dialog dla nawyku typu licznik (ile razy)"""
    
    def __init__(self, parent=None, habit_name="", current_value="", max_date=None):
        super().__init__(parent, habit_name, current_value, max_date)
        self.setWindowTitle(t("habit.type.counter", "Counter"))
        self.current_count = int(current_value) if current_value.isdigit() else 0
        self.setup_content()
        
    def setup_content(self):
        """Tworzy kontrolki dla typu licznik"""
        counter_group = QGroupBox(t("habit.dialog.value", "Wartość"))
        counter_layout = QFormLayout(counter_group)
        
        # Aktualna wartość
        current_label = QLabel(f"{t('habit.dialog.current_value', 'Aktualna wartość')}: {self.current_count}")
        current_label.setStyleSheet("font-weight: bold;")
        counter_layout.addRow(current_label)
        
        # Zmiana wartości
        self.value_spinbox = QSpinBox()
        self.value_spinbox.setRange(-999, 999)
        self.value_spinbox.setValue(1)
        self.value_spinbox.setMinimumHeight(40)
        counter_layout.addRow(t("habit.dialog.add_subtract", "Dodaj/odejmij:"), self.value_spinbox)
        
        self.content_layout.addWidget(counter_group)
        
        # Zmień tekst przycisku OK na "+"
        ok_button = self.button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_button:
            ok_button.setText(t("habit.dialog.add_button", "+ Dodaj"))
        
    def get_value(self) -> str:
        """Zwraca nową wartość licznika"""
        new_value = self.current_count + self.value_spinbox.value()
        return str(max(0, new_value))  # Nie pozwalaj na wartości ujemne


class DurationHabbitDialog(BaseHabbitDialog):
    """Dialog dla nawyku typu czas trwania"""
    
    def __init__(self, parent=None, habit_name="", current_value="", max_date=None):
        super().__init__(parent, habit_name, current_value, max_date)
        self.setWindowTitle(t("habit.type.duration", "Duration"))
        self.current_duration = self.parse_duration(current_value)
        self.setup_content()
        
    def parse_duration(self, duration_str):
        """Parsuje string HH:MM:SS do sekund"""
        if not duration_str or duration_str == "":
            return 0
        try:
            parts = duration_str.split(":")
            if len(parts) == 3:
                hours, minutes, seconds = map(int, parts)
                return hours * 3600 + minutes * 60 + seconds
        except ValueError:
            pass
        return 0
        
    def seconds_to_duration(self, seconds):
        """Konwertuje sekundy do HH:MM:SS"""
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        seconds = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        
    def setup_content(self):
        """Tworzy kontrolki dla typu czas trwania"""
        duration_group = QGroupBox(t("habit.dialog.duration", "Czas trwania"))
        duration_layout = QFormLayout(duration_group)
        
        # Aktualny czas
        current_time = self.seconds_to_duration(self.current_duration)
        current_label = QLabel(f"{t('habit.dialog.current_value', 'Aktualny czas')}: {current_time}")
        current_label.setStyleSheet("font-weight: bold;")
        duration_layout.addRow(current_label)
        
        # Szybkie przyciski
        quick_group = QGroupBox(t("habit.dialog.quick_add", "Szybkie dodawanie"))
        quick_layout = QHBoxLayout(quick_group)
        
        self.quick_buttons = QButtonGroup()
        self.quick_times = [("1m", 60), ("5m", 300), ("15m", 900), ("1h", 3600)]
        
        for text, seconds in self.quick_times:
            btn = QRadioButton(text)
            btn.setMinimumHeight(40)
            self.quick_buttons.addButton(btn)
            quick_layout.addWidget(btn)
            
        # Domyślnie wybierz 1m
        self.quick_buttons.buttons()[0].setChecked(True)
        
        duration_layout.addRow(quick_group)
        
        # Ręczne wprowadzanie
        manual_group = QGroupBox(t("habit.dialog.manual_entry", "Lub wprowadź ręcznie"))
        manual_layout = QFormLayout(manual_group)
        
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("hh:mm:ss")
        self.time_edit.setTime(QTime(0, 1, 0))  # Domyślnie 1 minuta
        self.time_edit.setMinimumHeight(40)
        manual_layout.addRow(t("habit.dialog.time", "Czas:"), self.time_edit)
        
        duration_layout.addRow(manual_group)
        self.content_layout.addWidget(duration_group)
        
    def get_value(self) -> str:
        """Zwraca nowy czas w formacie HH:MM:SS"""
        # Sprawdź czy wybrano szybki przycisk
        checked_button = self.quick_buttons.checkedButton()
        if checked_button:
            # Znajdź odpowiadające sekundy na podstawie tekstu
            button_text = checked_button.text()
            add_seconds = 0
            for text, seconds in self.quick_times:
                if text == button_text:
                    add_seconds = seconds
                    break
        else:
            # Użyj ręcznego wprowadzania
            time = self.time_edit.time()
            add_seconds = time.hour() * 3600 + time.minute() * 60 + time.second()
            
        new_duration = self.current_duration + add_seconds
        return self.seconds_to_duration(new_duration)


class TimeHabbitDialog(BaseHabbitDialog):
    """Dialog dla nawyku typu godzina"""
    
    def __init__(self, parent=None, habit_name="", current_value="", max_date=None):
        super().__init__(parent, habit_name, current_value, max_date)
        self.setWindowTitle(t("habit.type.time", "Time"))
        self.setup_content()
        
    def setup_content(self):
        """Tworzy kontrolki dla typu godzina"""
        time_group = QGroupBox(t("habit.dialog.time", "Godzina"))
        time_layout = QFormLayout(time_group)
        
        # Aktualna wartość
        if self.current_value:
            current_label = QLabel(f"{t('habit.dialog.current_value', 'Aktualna godzina')}: {self.current_value}")
            current_label.setStyleSheet("font-weight: bold;")
            time_layout.addRow(current_label)
        
        # Wybór godziny
        self.time_edit = QTimeEdit()
        self.time_edit.setDisplayFormat("hh:mm")
        
        # Ustaw aktualną wartość jeśli istnieje
        if self.current_value:
            try:
                parts = self.current_value.split(":")
                if len(parts) >= 2:
                    hour, minute = int(parts[0]), int(parts[1])
                    self.time_edit.setTime(QTime(hour, minute))
            except ValueError:
                pass
        else:
            self.time_edit.setTime(QTime.currentTime())
            
        self.time_edit.setMinimumHeight(50)
        time_layout.addRow(t("habit.dialog.new_value", "Nowa godzina:"), self.time_edit)
        
        self.content_layout.addWidget(time_group)
        
    def get_value(self) -> str:
        """Zwraca godzinę w formacie HH:MM"""
        return self.time_edit.time().toString("hh:mm")


class ScaleHabbitDialog(BaseHabbitDialog):
    """Dialog dla nawyku typu skala"""
    
    def __init__(self, parent=None, habit_name="", current_value="", scale_max=10, max_date=None):
        super().__init__(parent, habit_name, current_value, max_date)
        self.scale_max = scale_max
        self.setWindowTitle(t("habit.type.scale", "Scale"))
        self.setup_content()
        
    def setup_content(self):
        """Tworzy kontrolki dla typu skala"""
        scale_group = QGroupBox(t("habit.type.scale", "Skala"))
        scale_layout = QFormLayout(scale_group)
        
        # Aktualna wartość
        if self.current_value:
            current_label = QLabel(f"{t('habit.dialog.current_value', 'Aktualna wartość')}: {self.current_value}")
            current_label.setStyleSheet("font-weight: bold;")
            scale_layout.addRow(current_label)
        
        # Suwak
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(0, self.scale_max)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.setMinimumHeight(50)
        
        # Ustaw aktualną wartość jeśli istnieje
        current_val = 0
        if self.current_value and "/" in self.current_value:
            try:
                current_val = int(self.current_value.split("/")[0])
            except ValueError:
                pass
        self.slider.setValue(current_val)
        
        # Label z wartością
        self.value_label = QLabel(f"{current_val}/{self.scale_max}")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setStyleSheet("font-size: 16px; font-weight: bold; margin: 10px;")
        
        # Połącz suwak z labellem
        self.slider.valueChanged.connect(lambda v: self.value_label.setText(f"{v}/{self.scale_max}"))
        
        scale_layout.addRow(t("habit.dialog.value", "Wartość:"), self.value_label)
        scale_layout.addRow(t("habit.dialog.select", "Wybierz:"), self.slider)
        
        self.content_layout.addWidget(scale_group)
        
    def get_value(self) -> str:
        """Zwraca wartość w formacie X/Y"""
        return f"{self.slider.value()}/{self.scale_max}"


class TextHabbitDialog(BaseHabbitDialog):
    """Dialog dla nawyku typu tekst"""
    
    def __init__(self, parent=None, habit_name="", current_value="", max_date=None):
        super().__init__(parent, habit_name, current_value, max_date)
        self.setWindowTitle(t("habit.type.text", "Text"))
        self.setup_content()
        
    def setup_content(self):
        """Tworzy kontrolki dla typu tekst"""
        text_group = QGroupBox(t("habit.dialog.text_note", "Notatka"))
        text_layout = QVBoxLayout(text_group)
        
        # Pole tekstowe
        self.text_edit = QTextEdit()
        self.text_edit.setMinimumHeight(150)
        self.text_edit.setPlainText(self.current_value)
        text_layout.addWidget(self.text_edit)
        
        # Licznik znaków
        self.char_count_label = QLabel()
        self.update_char_count()
        self.text_edit.textChanged.connect(self.update_char_count)
        text_layout.addWidget(self.char_count_label)
        
        self.content_layout.addWidget(text_group)
        
    def update_char_count(self):
        """Aktualizuje licznik znaków"""
        count = len(self.text_edit.toPlainText())
        self.char_count_label.setText(t("habit.dialog.char_count", "Liczba znaków: {count}").format(count=count))
        
    def get_value(self) -> str:
        """Zwraca tekst"""
        return self.text_edit.toPlainText()


class AddHabbitDialog(QDialog):
    """Dialog do dodawania nowego nawyku"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(t("habit.dialog.add_title", "Dodaj nowy nawyk"))
        self.setModal(True)
        self.setMinimumWidth(400)
        self.setup_ui()
        
    def setup_ui(self):
        """Tworzy UI dialogu"""
        layout = QVBoxLayout(self)
        
        # Formularz
        form_group = QGroupBox(t("habit.dialog.new_habit", "Nowy nawyk"))
        form_layout = QFormLayout(form_group)
        
        # Nazwa nawyku
        self.name_edit = QLineEdit()
        self.name_edit.setMinimumHeight(35)
        self.name_edit.setPlaceholderText(t("habit.dialog.name_placeholder", "Np. Ćwiczenia, Czytanie, Medytacja..."))
        form_layout.addRow(t("habit.dialog.habit_name", "Nazwa nawyku:"), self.name_edit)
        
        # Typ nawyku
        self.type_combo = QComboBox()
        self.type_combo.addItems([
            t("habit.type.checkbox", "odznacz"),
            t("habit.type.counter", "Ile razy"), 
            t("habit.type.duration", "czas trwania"),
            t("habit.type.time", "Godzina"),
            t("habit.type.scale", "Skala"),
            t("habit.type.text", "tekst")
        ])
        self.type_combo.setMinimumHeight(35)
        form_layout.addRow(t("habit.dialog.habit_type", "Typ nawyku:"), self.type_combo)
        
        # Skala max (tylko dla typu skala)
        self.scale_spinbox = QSpinBox()
        self.scale_spinbox.setRange(2, 100)
        self.scale_spinbox.setValue(10)
        self.scale_spinbox.setMinimumHeight(35)
        self.scale_spinbox.setEnabled(False)
        form_layout.addRow(t("habit.dialog.max_scale", "Maksymalna skala:"), self.scale_spinbox)
        
        # Połącz zmianę typu z włączaniem/wyłączaniem skali
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        
        layout.addWidget(form_group)
        
        # Opis typów
        info_group = QGroupBox(t("habit.dialog.type_description", "Opis typów"))
        info_layout = QVBoxLayout(info_group)
        
        info_text = f"""
• {t('habit.type.checkbox', 'odznacz')} - {t('habit.dialog.checkbox_desc', 'Checkbox do zaznaczania wykonania')}
• {t('habit.type.counter', 'Ile razy')} - {t('habit.dialog.counter_desc', 'Licznik zwiększany przy każdym wykonaniu')}  
• {t('habit.type.duration', 'czas trwania')} - {t('habit.dialog.duration_desc', 'Śledzenie czasu spędzonego na nawyku')}
• {t('habit.type.time', 'Godzina')} - {t('habit.dialog.time_desc', 'Zapisywanie konkretnej godziny wykonania')}
• {t('habit.type.scale', 'Skala')} - {t('habit.dialog.scale_desc', 'Ocena jakości/intensywności (np. 7/10)')}
• {t('habit.type.text', 'tekst')} - {t('habit.dialog.text_desc', 'Notatki tekstowe związane z nawykiem')}
        """
        info_label = QLabel(info_text.strip())
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        info_layout.addWidget(info_label)
        
        layout.addWidget(info_group)
        
        # Przyciski
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Walidacja
        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setEnabled(False)
        self.name_edit.textChanged.connect(self.validate_form)
        
    def on_type_changed(self, type_name):
        """Obsługuje zmianę typu nawyku"""
        self.scale_spinbox.setEnabled(type_name == "Skala")
        
    def validate_form(self):
        """Waliduje formularz"""
        valid = len(self.name_edit.text().strip()) > 0
        # Znajdź przycisk OK
        buttons = self.findChildren(QDialogButtonBox)
        if buttons:
            ok_btn = buttons[0].button(QDialogButtonBox.StandardButton.Ok)
            if ok_btn:
                ok_btn.setEnabled(valid)
        
    def get_habit_data(self):
        """Zwraca dane nowego nawyku"""
        return {
            'name': self.name_edit.text().strip(),
            'type': self.type_combo.currentText(),
            'scale_max': self.scale_spinbox.value() if self.type_combo.currentText() == "Skala" else None
        }


class RemoveHabbitDialog(QDialog):
    """Dialog do usuwania nawyku"""
    
    def __init__(self, parent=None, habits_list=None):
        super().__init__(parent)
        self.habits_list = habits_list or []
        self.setWindowTitle(t("habit.dialog.remove_title", "Usuń nawyk"))
        self.setModal(True)
        self.setMinimumWidth(300)
        self.setup_ui()
        
    def setup_ui(self):
        """Tworzy UI dialogu"""
        layout = QVBoxLayout(self)
        
        if not self.habits_list:
            label = QLabel(t("habit.message.no_habits_to_remove", "Brak nawyków do usunięcia."))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(label)
            
            close_btn = QPushButton(t("common.close", "Zamknij"))
            close_btn.clicked.connect(self.reject)
            layout.addWidget(close_btn)
            return
        
        # Wybór nawyku
        habit_group = QGroupBox(t("habit.dialog.select_habit", "Wybierz nawyk do usunięcia"))
        habit_layout = QFormLayout(habit_group)
        
        self.habit_combo = QComboBox()
        self.habit_combo.setMinimumHeight(35)
        
        for habit in self.habits_list:
            display_text = f"{habit['name']} ({habit['type']})"
            self.habit_combo.addItem(display_text, habit['id'])
            
        habit_layout.addRow(t("habit.dialog.habit", "Nawyk:"), self.habit_combo)
        layout.addWidget(habit_group)
        
        # Ostrzeżenie
        warning_group = QGroupBox(t("common.warning", "Uwaga"))
        warning_layout = QVBoxLayout(warning_group)
        
        warning_text = QLabel(t("habit.message.delete_warning", "⚠️ Usunięcie nawyku spowoduje trwałe usunięcie wszystkich powiązanych danych!"))
        warning_text.setWordWrap(True)
        warning_text.setStyleSheet("color: #d32f2f; font-weight: bold;")
        warning_layout.addWidget(warning_text)
        
        layout.addWidget(warning_group)
        
        # Przyciski
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        if ok_btn:
            ok_btn.setText(t("common.delete", "Usuń"))
            ok_btn.setStyleSheet("background-color: #d32f2f; color: white;")
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
    def get_selected_habit_id(self):
        """Zwraca ID wybranego nawyku"""
        if self.habit_combo.currentData():
            return self.habit_combo.currentData()
        return None


# ===== NOWE UPROSZCZONE DIALOGI BEZ WYBORU DATY =====

class SimpleCellEditDialog(QDialog):
    """Bazowy dialog do edycji pojedynczej komórki (bez wyboru daty)"""
    
    def __init__(self, parent=None, habit_name="", habit_date="", current_value=""):
        super().__init__(parent)
        self.habit_name = habit_name
        self.habit_date = habit_date
        self.current_value = current_value
        
        self.setModal(True)
        self.setMinimumWidth(300)
        self.setup_base_ui()
        
    def setup_base_ui(self):
        """Tworzy podstawowy layout"""
        main_layout = QVBoxLayout(self)
        
        # Nagłówek
        title_label = QLabel(f"Edytuj wartość: {self.habit_name}")
        title_label.setStyleSheet("font-weight: bold; font-size: 14px;")
        main_layout.addWidget(title_label)
        
        # Data (tylko informacyjnie)
        date_label = QLabel(f"Data: {self.habit_date}")
        date_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        main_layout.addWidget(date_label)
        
        # Miejsce na kontrolki specyficzne dla typu
        self.content_layout = QVBoxLayout()
        main_layout.addLayout(self.content_layout)
        
        # Przyciski
        button_layout = QHBoxLayout()
        
        self.ok_btn = QPushButton("Zapisz")
        self.ok_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Anuluj")
        self.cancel_btn.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_btn)
        button_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(button_layout)
        
    def get_value(self):
        """Zwraca wprowadzoną wartość - do przesłonięcia"""
        return str()


class SimpleCheckboxDialog(SimpleCellEditDialog):
    """Dialog do edycji wartości checkbox"""
    
    def __init__(self, parent=None, habit_name="", habit_date="", current_value=""):
        super().__init__(parent, habit_name, habit_date, current_value)
        self.setWindowTitle("Edytuj nawyk - Checkbox")
        self.setup_content()
        
    def setup_content(self):
        """Tworzy kontrolki dla checkbox z dużym przyciskiem"""
        # Label "Status:"
        status_label = QLabel("Status:")
        status_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        self.content_layout.addWidget(status_label)
        
        # Layout dla dużego checkboxa
        checkbox_layout = QHBoxLayout()
        checkbox_layout.setSpacing(20)
        
        # Duży checkbox
        self.checkbox = QCheckBox("")
        self.checkbox.setStyleSheet("""
            QCheckBox::indicator {
                width: 60px;
                height: 60px;
                border: 3px solid #3498db;
                border-radius: 10px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                background-color: #27ae60;
                border-color: #27ae60;
            }
            QCheckBox::indicator:hover {
                border-color: #2980b9;
                background-color: #ecf0f1;
            }
            QCheckBox::indicator:checked:hover {
                background-color: #229954;
            }
        """)
        
        # Ustaw stan checkboxa
        is_checked = self.current_value.lower() in ['1', 'true', 'tak', 'yes'] if self.current_value else False
        self.checkbox.setChecked(is_checked)
        
        checkbox_layout.addWidget(self.checkbox)
        
        # Label wykonane/niewykonane
        self.status_label = QLabel("Wykonane" if is_checked else "Niewykonane")
        self.update_status_label()  # Ustaw odpowiedni styl
            
        checkbox_layout.addWidget(self.status_label)
        checkbox_layout.addStretch()
        
        # Podłącz sygnał do aktualizacji labela
        self.checkbox.stateChanged.connect(self.update_status_label)
        
        self.content_layout.addLayout(checkbox_layout)
        
        # Spacer
        self.content_layout.addSpacing(20)
        
        # Nazwa nawyku
        habit_label = QLabel(f"{self.habit_name}")
        habit_label.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 20px;")
        habit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(habit_label)
        
    def update_status_label(self):
        """Aktualizuje label statusu gdy checkbox się zmienia"""
        if self.checkbox.isChecked():
            self.status_label.setText("Wykonane")
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: #27ae60;
                    padding: 15px;
                }
            """)
        else:
            self.status_label.setText("Niewykonane")
            self.status_label.setStyleSheet("""
                QLabel {
                    font-size: 20px;
                    font-weight: bold;
                    color: #e74c3c;
                    padding: 15px;
                }
            """)
        
    def get_value(self):
        """Zwraca wartość checkbox"""
        return "1" if self.checkbox.isChecked() else "0"


class SimpleCounterDialog(SimpleCellEditDialog):
    """Dialog do edycji wartości licznika"""
    
    def __init__(self, parent=None, habit_name="", habit_date="", current_value=""):
        super().__init__(parent, habit_name, habit_date, current_value)
        # Przechowuj oryginalną wartość z bazy
        try:
            self.original_value = int(current_value) if current_value else 0
        except ValueError:
            self.original_value = 0
        # Wartość do dodania (domyślnie 1)
        self.value_to_add = 1
        self.setWindowTitle("Edytuj nawyk - Licznik")
        self.setup_content()
        
    def setup_content(self):
        """Tworzy kontrolki dla licznika z dużymi przyciskami +/-"""
        # Tekst "dodaj:"
        add_label = QLabel("Dodaj:")
        add_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        self.content_layout.addWidget(add_label)
        
        # Layout dla przycisków i wartości
        counter_layout = QHBoxLayout()
        counter_layout.setSpacing(15)
        
        # Przycisk minus (duży)
        self.minus_btn = QPushButton("−")
        self.minus_btn.setMinimumSize(60, 60)
        self.minus_btn.setMaximumSize(60, 60)
        self.minus_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                font-weight: bold;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.minus_btn.clicked.connect(self.decrement_value)
        counter_layout.addWidget(self.minus_btn)
        
        # Wartość (duża, w środku)
        # Wyświetlaj wartość do dodania (domyślnie 1)
        self.value_label = QLabel(str(self.value_to_add))
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                font-weight: bold;
                color: #333;
                background-color: #f5f5f5;
                border: 2px solid #ddd;
                border-radius: 10px;
                padding: 10px;
                min-width: 100px;
                text-align: center;
            }
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumSize(120, 80)
        counter_layout.addWidget(self.value_label)
        
        # Przycisk plus (duży)
        self.plus_btn = QPushButton("+")
        self.plus_btn.setMinimumSize(60, 60)
        self.plus_btn.setMaximumSize(60, 60)
        self.plus_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                font-weight: bold;
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:pressed {
                background-color: #2e7d32;
            }
        """)
        self.plus_btn.clicked.connect(self.increment_value)
        counter_layout.addWidget(self.plus_btn)
        
        self.content_layout.addLayout(counter_layout)
        
        # Spacer
        self.content_layout.addSpacing(20)
        
        # Informacja o aktualnej wartości i rezultacie
        self.info_label = QLabel()
        self.update_info_label()
        self.info_label.setStyleSheet("""
            QLabel {
                font-size: 12px;
                color: #666;
                background-color: #f9f9f9;
                border: 1px solid #ddd;
                border-radius: 5px;
                padding: 10px;
                margin: 5px;
            }
        """)
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.info_label)
        
        # Tekst z nazwą nawyku
        habit_label = QLabel(f"{self.habit_name}")
        habit_label.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 20px;")
        habit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(habit_label)
        
    def update_info_label(self):
        """Aktualizuje label z informacjami o wartościach"""
        result = self.original_value + self.value_to_add
        self.info_label.setText(f"Aktualna wartość: {self.original_value} | Dodajesz: {self.value_to_add} | Rezultat: {result}")
        
    def increment_value(self):
        """Zwiększa wartość do dodania o 1"""
        self.value_to_add += 1
        self.value_label.setText(str(self.value_to_add))
        self.update_info_label()
        
    def decrement_value(self):
        """Zmniejsza wartość do dodania o 1 (może być ujemna)"""
        self.value_to_add -= 1
        self.value_label.setText(str(self.value_to_add))
        self.update_info_label()
        
    def get_value(self):
        """Zwraca nową wartość (oryginalna + dodana)"""
        new_value = self.original_value + self.value_to_add
        return str(new_value)


class SimpleDurationDialog(SimpleCellEditDialog):
    """Dialog do edycji czasu trwania"""
    
    def __init__(self, parent=None, habit_name="", habit_date="", current_value=""):
        super().__init__(parent, habit_name, habit_date, current_value)
        # Przechowuj oryginalną wartość z bazy (w minutach)
        try:
            self.original_minutes = int(current_value) if current_value else 0
        except ValueError:
            self.original_minutes = 0
        # Wartość do dodania (domyślnie 15 min)
        self.minutes_to_add = 15
        # Interwał dodawania
        self.interval = 15  # 1, 5, 15 min lub 60 (1h)
        self.setWindowTitle("Edytuj nawyk - Czas trwania")
        self.setup_content()
        
    def setup_content(self):
        """Tworzy kontrolki dla czasu trwania z dużymi przyciskami +/-"""
        # Tekst "Dodaj czas:"
        add_label = QLabel("Dodaj czas:")
        add_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        self.content_layout.addWidget(add_label)
        
        # Layout dla przycisków i wartości
        duration_layout = QHBoxLayout()
        duration_layout.setSpacing(15)
        
        # Przycisk minus (duży)
        self.minus_btn = QPushButton("−")
        self.minus_btn.setMinimumSize(60, 60)
        self.minus_btn.setMaximumSize(60, 60)
        self.minus_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                font-weight: bold;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.minus_btn.clicked.connect(self.decrement_time)
        duration_layout.addWidget(self.minus_btn)
        
        # Wartość (duża, w środku) - wyświetlaj czas do dodania
        self.value_label = QLabel(self.format_minutes(self.minutes_to_add))
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 28px;
                font-weight: bold;
                color: #333;
                background-color: #f5f5f5;
                border: 2px solid #ddd;
                border-radius: 10px;
                padding: 10px;
                min-width: 120px;
                text-align: center;
            }
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumSize(140, 80)
        duration_layout.addWidget(self.value_label)
        
        # Przycisk plus (duży)
        self.plus_btn = QPushButton("+")
        self.plus_btn.setMinimumSize(60, 60)
        self.plus_btn.setMaximumSize(60, 60)
        self.plus_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                font-weight: bold;
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:pressed {
                background-color: #2e7d32;
            }
        """)
        self.plus_btn.clicked.connect(self.increment_time)
        duration_layout.addWidget(self.plus_btn)
        
        self.content_layout.addLayout(duration_layout)
        
        # Spacer
        self.content_layout.addSpacing(15)
        
        # Radio buttons dla interwału
        interval_label = QLabel("Interwał:")
        interval_label.setStyleSheet("font-size: 12px; font-weight: bold; margin-bottom: 5px;")
        self.content_layout.addWidget(interval_label)
        
        interval_layout = QHBoxLayout()
        self.interval_group = QButtonGroup()
        
        intervals = [
            (1, "1min"),
            (5, "5min"), 
            (15, "15min"),
            (60, "1h")
        ]
        
        for minutes, text in intervals:
            radio = QRadioButton(text)
            radio.setStyleSheet("font-size: 11px; margin: 2px;")
            if minutes == 15:  # Domyślnie 15 min
                radio.setChecked(True)
            radio.toggled.connect(lambda checked, m=minutes: self.set_interval(m) if checked else None)
            self.interval_group.addButton(radio)
            interval_layout.addWidget(radio)
            
        interval_layout.addStretch()
        self.content_layout.addLayout(interval_layout)
        
        # Spacer
        self.content_layout.addSpacing(15)
        
        # Informacja o wartościach
        self.info_label = QLabel()
        self.info_label.setStyleSheet("font-size: 10px; color: #666; margin-bottom: 10px;")
        self.info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.info_label)
        self.update_info_label()
        
        # Nazwa nawyku
        habit_label = QLabel(f"{self.habit_name}")
        habit_label.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 20px;")
        habit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(habit_label)
        
    def format_minutes(self, total_minutes):
        """Formatuje minuty do postaci 'XhYmin' lub 'Ymin'"""
        if total_minutes < 60:
            return f"{total_minutes}min"
        else:
            hours = total_minutes // 60
            minutes = total_minutes % 60
            if minutes == 0:
                return f"{hours}h"
            else:
                return f"{hours}h{minutes}min"
                
    def set_interval(self, minutes):
        """Ustawia interwał dodawania"""
        self.interval = minutes
        
    def update_info_label(self):
        """Aktualizuje label z informacjami o wartościach"""
        current_formatted = self.format_minutes(self.original_minutes)
        add_formatted = self.format_minutes(self.minutes_to_add)
        result_minutes = self.original_minutes + self.minutes_to_add
        result_formatted = self.format_minutes(result_minutes)
        self.info_label.setText(f"Aktualnie: {current_formatted} | Dodajesz: {add_formatted} | Rezultat: {result_formatted}")
        
    def increment_time(self):
        """Zwiększa czas do dodania o wybrany interwał"""
        self.minutes_to_add += self.interval
        self.value_label.setText(self.format_minutes(self.minutes_to_add))
        self.update_info_label()
        
    def decrement_time(self):
        """Zmniejsza czas do dodania o wybrany interwał (może być ujemny)"""
        self.minutes_to_add -= self.interval
        self.value_label.setText(self.format_minutes(self.minutes_to_add))
        self.update_info_label()
        
    def get_value(self):
        """Zwraca nową wartość (oryginalna + dodana) w minutach"""
        new_minutes = self.original_minutes + self.minutes_to_add
        return str(max(0, new_minutes))  # Nie może być ujemna


class SimpleTimeDialog(SimpleCellEditDialog):
    """Dialog do edycji godziny"""
    
    def __init__(self, parent=None, habit_name="", habit_date="", current_value=""):
        super().__init__(parent, habit_name, habit_date, current_value)
        # Jeśli nie ma wartości, ustaw aktualną godzinę zaokrągloną do 5 min w dół
        if not current_value:
            from datetime import datetime
            now = datetime.now()
            # Zaokrąglij w dół do 5 minut
            rounded_minutes = (now.minute // 5) * 5
            self.current_minutes = now.hour * 60 + rounded_minutes
        else:
            self.current_minutes = self.parse_time_to_minutes(current_value)
        # Interwał dodawania
        self.interval = 15  # 1, 5, 15 min lub 60 (1h)
        self.setWindowTitle("Edytuj nawyk - Godzina")
        self.setup_content()
        
    def parse_time_to_minutes(self, time_str):
        """Konwertuje czas w formacie HH:MM na minuty od północy"""
        if not time_str:
            return 0
        try:
            time_parts = time_str.split(':')
            if len(time_parts) >= 2:
                hours = int(time_parts[0])
                minutes = int(time_parts[1])
                return hours * 60 + minutes
        except ValueError:
            pass
        return 0
        
    def minutes_to_time_string(self, total_minutes):
        """Konwertuje minuty od północy na format HH:MM"""
        # Zapewnij że czas jest w zakresie 0-1439 (24h)
        total_minutes = total_minutes % (24 * 60)
        if total_minutes < 0:
            total_minutes = (24 * 60) + total_minutes
            
        hours = total_minutes // 60
        minutes = total_minutes % 60
        return f"{hours:02d}:{minutes:02d}"
        
    def setup_content(self):
        """Tworzy kontrolki dla godziny z dużymi przyciskami +/-"""
        # Tekst "Godzina:"
        time_label = QLabel("Godzina:")
        time_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        self.content_layout.addWidget(time_label)
        
        # Layout dla przycisków i wartości
        time_layout = QHBoxLayout()
        time_layout.setSpacing(15)
        
        # Przycisk minus (duży)
        self.minus_btn = QPushButton("−")
        self.minus_btn.setMinimumSize(60, 60)
        self.minus_btn.setMaximumSize(60, 60)
        self.minus_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                font-weight: bold;
                background-color: #f44336;
                color: white;
                border: none;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: #d32f2f;
            }
            QPushButton:pressed {
                background-color: #b71c1c;
            }
        """)
        self.minus_btn.clicked.connect(self.decrement_time)
        time_layout.addWidget(self.minus_btn)
        
        # Wartość (duża, w środku) - wyświetlaj aktualny czas
        self.value_label = QLabel(self.minutes_to_time_string(self.current_minutes))
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #333;
                background-color: #f5f5f5;
                border: 2px solid #ddd;
                border-radius: 10px;
                padding: 15px;
                min-width: 140px;
                text-align: center;
            }
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.value_label.setMinimumSize(160, 80)
        time_layout.addWidget(self.value_label)
        
        # Przycisk plus (duży)
        self.plus_btn = QPushButton("+")
        self.plus_btn.setMinimumSize(60, 60)
        self.plus_btn.setMaximumSize(60, 60)
        self.plus_btn.setStyleSheet("""
            QPushButton {
                font-size: 24px;
                font-weight: bold;
                background-color: #4caf50;
                color: white;
                border: none;
                border-radius: 30px;
            }
            QPushButton:hover {
                background-color: #388e3c;
            }
            QPushButton:pressed {
                background-color: #2e7d32;
            }
        """)
        self.plus_btn.clicked.connect(self.increment_time)
        time_layout.addWidget(self.plus_btn)
        
        self.content_layout.addLayout(time_layout)
        
        # Spacer
        self.content_layout.addSpacing(15)
        
        # Radio buttons dla interwału
        interval_label = QLabel("Interwał:")
        interval_label.setStyleSheet("font-size: 12px; font-weight: bold; margin-bottom: 5px;")
        self.content_layout.addWidget(interval_label)
        
        interval_layout = QHBoxLayout()
        self.interval_group = QButtonGroup()
        
        intervals = [
            (1, "1min"),
            (5, "5min"), 
            (15, "15min"),
            (60, "1h")
        ]
        
        for minutes, text in intervals:
            radio = QRadioButton(text)
            radio.setStyleSheet("font-size: 11px; margin: 2px;")
            if minutes == 15:  # Domyślnie 15 min
                radio.setChecked(True)
            radio.toggled.connect(lambda checked, m=minutes: self.set_interval(m) if checked else None)
            self.interval_group.addButton(radio)
            interval_layout.addWidget(radio)
            
        interval_layout.addStretch()
        self.content_layout.addLayout(interval_layout)
        
        # Spacer
        self.content_layout.addSpacing(20)
        
        # Nazwa nawyku
        habit_label = QLabel(f"{self.habit_name}")
        habit_label.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 20px;")
        habit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(habit_label)
        
    def set_interval(self, minutes):
        """Ustawia interwał dodawania"""
        self.interval = minutes
        
    def increment_time(self):
        """Zwiększa czas o wybrany interwał"""
        self.current_minutes += self.interval
        # Zawijanie do 24h
        self.current_minutes = self.current_minutes % (24 * 60)
        self.value_label.setText(self.minutes_to_time_string(self.current_minutes))
        
    def decrement_time(self):
        """Zmniejsza czas o wybrany interwał"""
        self.current_minutes -= self.interval
        # Zawijanie do 24h (obsługa ujemnych wartości)
        if self.current_minutes < 0:
            self.current_minutes = (24 * 60) + self.current_minutes
        self.value_label.setText(self.minutes_to_time_string(self.current_minutes))
        
    def get_value(self):
        """Zwraca czas w formacie HH:MM"""
        return self.minutes_to_time_string(self.current_minutes)


class SimpleScaleDialog(SimpleCellEditDialog):
    """Dialog do edycji skali (1-10)"""
    
    def __init__(self, parent=None, habit_name="", habit_date="", current_value="", scale_max=10):
        self.scale_max = scale_max
        super().__init__(parent, habit_name, habit_date, current_value)
        self.setWindowTitle("Edytuj nawyk - Skala")
        self.setup_content()
        
    def setup_content(self):
        """Tworzy kontrolki dla skali z dużym suwakiem"""
        # Label "Ocena:"
        ocena_label = QLabel("Ocena:")
        ocena_label.setStyleSheet("font-size: 14px; font-weight: bold; margin-bottom: 10px;")
        self.content_layout.addWidget(ocena_label)
        
        # Ustaw aktualną wartość
        try:
            current_val = int(self.current_value) if self.current_value else 1
            current_val = max(1, min(self.scale_max, current_val))
        except ValueError:
            current_val = 1
        
        # Duża wartość nad suwakiem
        self.value_label = QLabel(f"{current_val}/{self.scale_max}")
        self.value_label.setStyleSheet("""
            QLabel {
                font-size: 32px;
                font-weight: bold;
                color: #333;
                background-color: #f5f5f5;
                border: 2px solid #ddd;
                border-radius: 10px;
                padding: 15px;
                margin: 10px;
                text-align: center;
            }
        """)
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(self.value_label)
        
        # Duży slider
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setMinimum(1)
        self.slider.setMaximum(self.scale_max)
        self.slider.setValue(current_val)
        self.slider.setTickPosition(QSlider.TickPosition.TicksBelow)
        self.slider.setTickInterval(1)
        self.slider.setStyleSheet("""
            QSlider::groove:horizontal {
                border: 2px solid #bdc3c7;
                height: 20px;
                background: #ecf0f1;
                margin: 2px 0;
                border-radius: 10px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                border: 2px solid #2980b9;
                width: 40px;
                height: 40px;
                margin: -15px 0;
                border-radius: 20px;
            }
            QSlider::handle:horizontal:hover {
                background: #2980b9;
            }
            QSlider::handle:horizontal:pressed {
                background: #21618c;
            }
            QSlider::sub-page:horizontal {
                background: #27ae60;
                border: 2px solid #229954;
                height: 20px;
                border-radius: 10px;
            }
        """)
        self.slider.setMinimumHeight(60)
        
        # Podłącz sygnał do aktualizacji labela
        self.slider.valueChanged.connect(self.update_value_label)
        
        self.content_layout.addWidget(self.slider)
        
        # Spacer
        self.content_layout.addSpacing(20)
        
        # Nazwa nawyku
        habit_label = QLabel(f"{self.habit_name}")
        habit_label.setStyleSheet("font-size: 12px; color: #666; margin-bottom: 20px;")
        habit_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(habit_label)
        
    def update_value_label(self):
        """Aktualizuje label z wartością gdy suwak się zmienia"""
        current_val = self.slider.value()
        self.value_label.setText(f"{current_val}/{self.scale_max}")
        
    def get_value(self):
        """Zwraca wartość skali"""
        return str(self.slider.value())


class SimpleTextDialog(SimpleCellEditDialog):
    """Dialog do edycji tekstu"""
    
    def __init__(self, parent=None, habit_name="", habit_date="", current_value=""):
        super().__init__(parent, habit_name, habit_date, current_value)
        self.setWindowTitle("Edytuj nawyk - Tekst")
        self.setup_content()
        
    def setup_content(self):
        """Tworzy kontrolki dla tekstu"""
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Notatka:"))
        
        self.text_edit = QTextEdit()
        self.text_edit.setMaximumHeight(100)
        self.text_edit.setPlainText(self.current_value)
        
        layout.addWidget(self.text_edit)
        
        self.content_layout.addLayout(layout)
        
    def get_value(self):
        """Zwraca tekst"""
        return self.text_edit.toPlainText()
