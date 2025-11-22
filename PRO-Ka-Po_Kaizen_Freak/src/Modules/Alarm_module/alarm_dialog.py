"""
Dialog do ustawiania alarmu/timera dla zadania
Integracja z modułem alarmów
"""

import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, 
    QPushButton, QDateTimeEdit, QCheckBox, QComboBox,
    QSpinBox, QButtonGroup, QRadioButton, QGroupBox,
    QDialogButtonBox, QMessageBox, QLineEdit
)
from PyQt6.QtCore import QDateTime, Qt

from src.utils.i18n_manager import get_i18n

logger = logging.getLogger(__name__)

class TaskAlarmDialog(QDialog):
    """Dialog do ustawiania alarmu/timera dla zadania"""
    
    def __init__(self, task_id: int, task_title: str, current_alarm_date: Optional[datetime] = None, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.task_title = task_title
        self.current_alarm_date = current_alarm_date
        self.i18n = get_i18n()
        
        self.alarm_data = None
        
        logger.info(f"[TaskAlarmDialog] Initializing for task_id={task_id}, task_title='{task_title}'")
        
        self.setWindowTitle(self.i18n.t('alarm.dialog.title', 'Ustaw alarm dla zadania'))
        self.setMinimumWidth(500)
        self.setup_ui()
        
        if current_alarm_date:
            self.load_alarm_data(current_alarm_date)
    
    def setup_ui(self):
        """Inicjalizacja UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Tytuł zadania
        title_label = QLabel(f"<b>{self.i18n.t('alarm.dialog.task', 'Zadanie')}: {self.task_title}</b>")
        title_label.setWordWrap(True)
        layout.addWidget(title_label)
        
        # Etykieta alarmu (opcjonalna)
        label_layout = QHBoxLayout()
        label_layout.addWidget(QLabel(self.i18n.t('alarm.dialog.label', 'Etykieta alarmu:')))
        self.alarm_label = QLineEdit()
        self.alarm_label.setText(self.task_title)  # Domyślnie tytuł zadania
        self.alarm_label.setPlaceholderText(self.i18n.t('alarm.dialog.label_placeholder', 'np. Deadline projektu'))
        label_layout.addWidget(self.alarm_label)
        layout.addLayout(label_layout)
        
        # Typ alarmu: jednorazowy / cykliczny
        type_group = QGroupBox(self.i18n.t('alarm.dialog.type', 'Typ alarmu'))
        type_layout = QVBoxLayout()
        
        self.type_group = QButtonGroup()
        self.radio_once = QRadioButton(self.i18n.t('alarm.dialog.type.once', 'Jednorazowy'))
        self.radio_recurring = QRadioButton(self.i18n.t('alarm.dialog.type.recurring', 'Cykliczny'))
        self.type_group.addButton(self.radio_once, 0)
        self.type_group.addButton(self.radio_recurring, 1)
        
        type_layout.addWidget(self.radio_once)
        type_layout.addWidget(self.radio_recurring)
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        self.radio_once.setChecked(True)
        self.radio_once.toggled.connect(self._on_type_changed)
        
        # Data i czas alarmu
        datetime_layout = QHBoxLayout()
        datetime_layout.addWidget(QLabel(self.i18n.t('alarm.dialog.datetime', 'Data i czas:')))
        self.datetime_edit = QDateTimeEdit()
        self.datetime_edit.setDateTime(QDateTime.currentDateTime().addSecs(3600))  # +1h
        self.datetime_edit.setCalendarPopup(True)
        self.datetime_edit.setDisplayFormat("yyyy-MM-dd HH:mm")
        datetime_layout.addWidget(self.datetime_edit)
        layout.addLayout(datetime_layout)
        
        # Opcje cykliczne (początkowo ukryte)
        self.recurring_widget = QGroupBox(self.i18n.t('alarm.dialog.recurring_options', 'Opcje cykliczne'))
        recurring_layout = QVBoxLayout()
        
        # Powtarzanie
        repeat_layout = QHBoxLayout()
        repeat_layout.addWidget(QLabel(self.i18n.t('alarm.dialog.repeat_every', 'Powtarzaj co:')))
        self.repeat_count = QSpinBox()
        self.repeat_count.setMinimum(1)
        self.repeat_count.setMaximum(365)
        self.repeat_count.setValue(1)
        repeat_layout.addWidget(self.repeat_count)
        
        self.repeat_unit = QComboBox()
        self.repeat_unit.addItems([
            self.i18n.t('alarm.dialog.unit.minutes', 'minut'),
            self.i18n.t('alarm.dialog.unit.hours', 'godzin'),
            self.i18n.t('alarm.dialog.unit.days', 'dni'),
            self.i18n.t('alarm.dialog.unit.weeks', 'tygodni'),
            self.i18n.t('alarm.dialog.unit.months', 'miesięcy')
        ])
        self.repeat_unit.setCurrentIndex(2)  # dni
        repeat_layout.addWidget(self.repeat_unit)
        repeat_layout.addStretch()
        recurring_layout.addLayout(repeat_layout)
        
        # Data zakończenia (opcjonalna)
        end_layout = QHBoxLayout()
        self.end_date_check = QCheckBox(self.i18n.t('alarm.dialog.end_date', 'Zakończ po dacie:'))
        end_layout.addWidget(self.end_date_check)
        self.end_date_edit = QDateTimeEdit()
        self.end_date_edit.setDateTime(QDateTime.currentDateTime().addDays(30))
        self.end_date_edit.setCalendarPopup(True)
        self.end_date_edit.setDisplayFormat("yyyy-MM-dd")
        self.end_date_edit.setEnabled(False)
        end_layout.addWidget(self.end_date_edit)
        end_layout.addStretch()
        recurring_layout.addLayout(end_layout)
        
        self.end_date_check.toggled.connect(self.end_date_edit.setEnabled)
        
        self.recurring_widget.setLayout(recurring_layout)
        self.recurring_widget.setVisible(False)
        layout.addWidget(self.recurring_widget)
        
        # Opcje powiadomień
        notification_group = QGroupBox(self.i18n.t('alarm.dialog.notification', 'Powiadomienia'))
        notification_layout = QVBoxLayout()
        
        self.sound_check = QCheckBox(self.i18n.t('alarm.dialog.play_sound', 'Odtwórz dźwięk'))
        self.sound_check.setChecked(True)
        notification_layout.addWidget(self.sound_check)
        
        self.popup_check = QCheckBox(self.i18n.t('alarm.dialog.show_popup', 'Pokaż popup'))
        self.popup_check.setChecked(True)
        notification_layout.addWidget(self.popup_check)
        
        notification_group.setLayout(notification_layout)
        layout.addWidget(notification_group)
        
        # Przyciski
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        # Przycisk "Usuń alarm"
        remove_btn = QPushButton(self.i18n.t('alarm.dialog.remove', 'Usuń alarm'))
        remove_btn.clicked.connect(self.remove_alarm)
        button_box.addButton(remove_btn, QDialogButtonBox.ButtonRole.DestructiveRole)
        
        layout.addWidget(button_box)
    
    def _on_type_changed(self, checked):
        """Przełączanie między jednorazowym a cyklicznym"""
        self.recurring_widget.setVisible(self.radio_recurring.isChecked())
    
    def load_alarm_data(self, alarm_date: datetime):
        """Ładuje dane istniejącego alarmu"""
        # Ustawienie daty i czasu
        qdt = QDateTime(alarm_date)
        self.datetime_edit.setDateTime(qdt)
        
        # Domyślnie jednorazowy (bez dodatkowych danych nie wiemy czy cykliczny)
        self.radio_once.setChecked(True)
    
    def get_alarm_data(self) -> Optional[Dict[str, Any]]:
        """Zwraca dane alarmu do zapisu"""
        if not self.validate():
            return None
        
        alarm_datetime = self.datetime_edit.dateTime().toPyDateTime()
        
        data = {
            'task_id': self.task_id,
            'label': self.alarm_label.text() or self.task_title,
            'alarm_time': alarm_datetime,
            'play_sound': self.sound_check.isChecked(),
            'show_popup': self.popup_check.isChecked(),
            'is_recurring': self.radio_recurring.isChecked()
        }
        
        if self.radio_recurring.isChecked():
            # Konwersja jednostki na minuty
            unit_index = self.repeat_unit.currentIndex()
            count = self.repeat_count.value()
            
            interval_minutes = 0
            if unit_index == 0:  # minuty
                interval_minutes = count
            elif unit_index == 1:  # godziny
                interval_minutes = count * 60
            elif unit_index == 2:  # dni
                interval_minutes = count * 24 * 60
            elif unit_index == 3:  # tygodnie
                interval_minutes = count * 7 * 24 * 60
            elif unit_index == 4:  # miesiące (przybliżone 30 dni)
                interval_minutes = count * 30 * 24 * 60
            
            data['recurrence'] = 'custom'
            data['interval_minutes'] = interval_minutes
            
            if self.end_date_check.isChecked():
                data['end_date'] = self.end_date_edit.dateTime().toPyDateTime()
        
        return data
    
    def validate(self) -> bool:
        """Walidacja danych"""
        alarm_time = self.datetime_edit.dateTime().toPyDateTime()
        
        # Sprawdź czy data nie jest w przeszłości
        if alarm_time <= datetime.now():
            QMessageBox.warning(
                self,
                self.i18n.t('alarm.dialog.error', 'Błąd'),
                self.i18n.t('alarm.dialog.error.past_date', 'Data alarmu nie może być w przeszłości!')
            )
            return False
        
        # Dla cyklicznych sprawdź datę zakończenia
        if self.radio_recurring.isChecked() and self.end_date_check.isChecked():
            end_date = self.end_date_edit.dateTime().toPyDateTime()
            if end_date <= alarm_time:
                QMessageBox.warning(
                    self,
                    self.i18n.t('alarm.dialog.error', 'Błąd'),
                    self.i18n.t('alarm.dialog.error.end_before_start', 
                               'Data zakończenia musi być późniejsza niż data rozpoczęcia!')
                )
                return False
        
        return True
    
    def remove_alarm(self):
        """Usuwa alarm"""
        reply = QMessageBox.question(
            self,
            self.i18n.t('alarm.dialog.remove', 'Usuń alarm'),
            self.i18n.t('alarm.dialog.remove_confirm', 'Czy na pewno chcesz usunąć alarm dla tego zadania?'),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.alarm_data = {'remove': True}
            self.accept()
    
    def accept(self):
        """Zaakceptowanie dialogu"""
        if self.alarm_data and self.alarm_data.get('remove'):
            # Usuwanie alarmu
            super().accept()
        else:
            # Zapisywanie alarmu
            self.alarm_data = self.get_alarm_data()
            if self.alarm_data:
                super().accept()
