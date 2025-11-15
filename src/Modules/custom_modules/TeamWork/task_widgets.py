"""Task table and Gantt chart view for TeamWork."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QBrush, QColor
from PyQt6.QtWidgets import (
    QCheckBox,
    QHeaderView,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)



class TaskTableWidget(QWidget):
    """Widget wyświetlający zadania w formie tabeli."""

    # Sygnały
    toggle_important = pyqtSignal(str, str, str)  # type, task_id, topic_id
    task_completed_changed = pyqtSignal(int, bool)  # task_id, completed

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        
        self.api_client = None  # TeamWorkAPIClient - ustawiony z zewnątrz

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        header_layout = QVBoxLayout()
        self.title_label = QLabel("Zadania")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        header_layout.addWidget(self.title_label)

        self.add_task_btn = QPushButton("➕ Dodaj zadanie")
        self.add_task_btn.setMaximumWidth(150)
        header_layout.addWidget(self.add_task_btn)

        layout.addLayout(header_layout)

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels([
            "ID",
            "Data dodania",
            "Temat",
            "Zadanie",
            "Dodał",
            "Odpowiedzialny",
            "Termin",
            "Status",
            "Zakończył",
            "Data realizacji",
            "Ważne",
        ])
        self.table.horizontalHeader().setStretchLastSection(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(6, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(7, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(8, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(9, QHeaderView.ResizeMode.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(10, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        layout.addWidget(self.table)
        
        self._topic_id = ""

    def set_tasks(self, tasks: List[dict], topic_title: str = "", topic_id: str = "") -> None:
        """Wypełnia tabelę zadaniami."""
        self._topic_id = topic_id
        self.table.setRowCount(0)
        self.table.setRowCount(len(tasks))

        for row, task in enumerate(tasks):
            # Obsługa zarówno struktury API (task_id, task_subject) jak i lokalnej (id, title)
            task_id = task.get("task_id") or task.get("id", "")
            task_subject = task.get("task_subject") or task.get("title", "")
            task_description = task.get("task_description") or task.get("description", "")
            created_by = task.get("created_by") or task.get("creator", "")
            assigned_to = task.get("assigned_to") or task.get("assignee", "")
            is_important = task.get("is_important") or task.get("important", False)
            
            # ID
            id_item = QTableWidgetItem(str(task_id))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 0, id_item)

            # Data dodania
            created_at = task.get("created_at")
            # Jeśli to string z API, sparsuj
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = None
            created_str = self._format_dt(created_at) if isinstance(created_at, datetime) else ""
            created_item = QTableWidgetItem(created_str)
            created_item.setFlags(created_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 1, created_item)

            # Temat
            topic_item = QTableWidgetItem(topic_title)
            topic_item.setFlags(topic_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 2, topic_item)

            # Zadanie
            title_item = QTableWidgetItem(task_subject)
            title_item.setFlags(title_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            title_item.setToolTip(task_description)
            self.table.setItem(row, 3, title_item)

            # Dodał
            creator_item = QTableWidgetItem(created_by)
            creator_item.setFlags(creator_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 4, creator_item)

            # Odpowiedzialny
            assignee_item = QTableWidgetItem(assigned_to if assigned_to else "—")
            assignee_item.setFlags(assignee_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 5, assignee_item)

            # Termin (due_date może być date lub datetime)
            deadline = task.get("due_date") or task.get("deadline")
            if isinstance(deadline, str):
                try:
                    deadline = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                except:
                    deadline = None
            deadline_str = self._format_dt(deadline) if deadline else ""
            deadline_item = QTableWidgetItem(deadline_str)
            deadline_item.setFlags(deadline_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            
            # Podświetl przeterminowane
            if deadline and not task.get("completed") and deadline < datetime.now():
                deadline_item.setBackground(QBrush(QColor("#FFCCCC")))
            
            self.table.setItem(row, 6, deadline_item)

            # Status - checkbox (Task 3.3 - podłączony do API)
            completed = task.get("completed", False)
            status_checkbox = QCheckBox()
            status_checkbox.setChecked(completed)
            status_checkbox.setEnabled(self.api_client is not None)  # Aktywny tylko gdy jest API client
            # Połącz z handlerем zmiany statusu
            status_checkbox.toggled.connect(
                lambda checked, tid=task_id: self._on_task_completed_toggled(tid, checked)
            )
            self.table.setCellWidget(row, 7, status_checkbox)

            # Zakończył
            completed_by = task.get("completed_by", "")
            completed_by_item = QTableWidgetItem(completed_by if completed else "")
            completed_by_item.setFlags(completed_by_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 8, completed_by_item)

            # Data realizacji
            completed_at = task.get("completed_at")
            if isinstance(completed_at, str):
                try:
                    completed_at = datetime.fromisoformat(completed_at.replace('Z', '+00:00'))
                except:
                    completed_at = None
            completed_str = self._format_dt(completed_at) if isinstance(completed_at, datetime) else ""
            completed_item = QTableWidgetItem(completed_str)
            completed_item.setFlags(completed_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.table.setItem(row, 9, completed_item)
            
            # Ważne - przycisk
            important_btn = QPushButton("⭐" if is_important else "☆")
            important_btn.setMaximumWidth(40)
            important_btn.setToolTip("Oznacz jako ważne" if not is_important else "Usuń z ważnych")
            important_btn.clicked.connect(
                lambda checked=False, tid=str(task_id): self._on_toggle_important(tid)
            )
            self.table.setCellWidget(row, 10, important_btn)
    
    def _on_toggle_important(self, task_id: str) -> None:
        """Emituje sygnał toggle_important."""
        self.toggle_important.emit("task", task_id, self._topic_id)
    
    def _on_task_completed_toggled(self, task_id: str, completed: bool) -> None:
        """
        Obsługuje zmianę statusu zadania (checkbox completed).
        Wywołuje API i emituje sygnał.
        """
        if not self.api_client:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Brak połączenia",
                "Nie można oznaczyć zadania - brak połączenia z API."
            )
            return
        
        # Wywołaj API
        response = self.api_client.complete_task(task_id, completed)
        
        if response.success:
            # Emituj sygnał, że zadanie zostało zaktualizowane
            self.task_completed_changed.emit(task_id, completed)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Błąd aktualizacji",
                f"Nie udało się oznaczyć zadania jako {'ukończone' if completed else 'nieukończone'}:\n{response.error}"
            )
            # Cofnij zmianę checkboxa (znajdź go i ustaw poprzedni stan)
            # TODO: Można to poprawić, przechowując odniesienie do checkboxa

    @staticmethod
    def _format_dt(value: datetime) -> str:
        return value.strftime("%Y-%m-%d")


class GanttChartWidget(QWidget):
    """Widget wyświetlający zadania w formie wykresu Gantta."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        
        self.api_client = None  # TeamWorkAPIClient - ustawiony z zewnątrz
        self.tasks = []

        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)

        # Nagłówek
        self.title_label = QLabel("Widok Gantt")
        self.title_label.setStyleSheet("font-weight: bold; font-size: 14pt;")
        layout.addWidget(self.title_label)

        # Scroll area dla wykres
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setMinimumHeight(400)
        
        self.chart_widget = QWidget()
        self.chart_layout = QVBoxLayout(self.chart_widget)
        self.chart_layout.setContentsMargins(8, 8, 8, 8)
        self.chart_layout.setSpacing(4)
        
        scroll_area.setWidget(self.chart_widget)
        layout.addWidget(scroll_area)
        
        self._show_placeholder()

    def _show_placeholder(self):
        """Wyświetla placeholder gdy brak zadań"""
        self._clear_chart()
        placeholder = QLabel("Brak zadań do wyświetlenia.\n"
                            "Dodaj zadania z określonymi terminami, aby zobaczyć wykres Gantta.")
        placeholder.setStyleSheet("color: #666; padding: 40px;")
        placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.chart_layout.addWidget(placeholder)
        self.chart_layout.addStretch()
    
    def _clear_chart(self):
        """Czyści zawartość wykresu"""
        while self.chart_layout.count():
            item = self.chart_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def set_tasks(self, tasks: List[dict], topic_title: str = "") -> None:
        """Renderuje wykres Gantta dla zadań z API"""
        self.tasks = tasks
        self.title_label.setText(f"Widok Gantt: {topic_title}")
        
        if not tasks:
            self._show_placeholder()
            return
        
        # Filtruj zadania z określonymi terminami
        tasks_with_dates = []
        for task in tasks:
            # Obsługa zarówno struktury API jak i lokalnej
            due_date = task.get("due_date") or task.get("deadline")
            created_at = task.get("created_at")
            
            # Parse dates if strings
            if isinstance(due_date, str):
                try:
                    due_date = datetime.fromisoformat(due_date.replace('Z', '+00:00'))
                except:
                    due_date = None
            
            if isinstance(created_at, str):
                try:
                    created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
                except:
                    created_at = None
            
            if due_date and created_at:
                tasks_with_dates.append({
                    'task': task,
                    'created_at': created_at,
                    'due_date': due_date
                })
        
        if not tasks_with_dates:
            self._show_placeholder()
            return
        
        # Sortuj po dacie rozpoczęcia
        tasks_with_dates.sort(key=lambda x: x['created_at'])
        
        # Znajdź zakres dat - konwertuj wszystkie na naive datetime (bez timezone)
        def to_naive(dt):
            """Konwertuje datetime na naive (bez timezone info)"""
            if dt.tzinfo is not None:
                return dt.replace(tzinfo=None)
            return dt
        
        min_date = to_naive(min(t['created_at'] for t in tasks_with_dates))
        max_date = to_naive(max(t['due_date'] for t in tasks_with_dates))
        total_days = (max_date - min_date).days + 1
        
        self._clear_chart()
        
        # Legenda
        legend = QLabel(f"📅 Zakres: {min_date.strftime('%Y-%m-%d')} → {max_date.strftime('%Y-%m-%d')} ({total_days} dni)")
        legend.setStyleSheet("color: #555; font-size: 10pt; padding: 4px;")
        self.chart_layout.addWidget(legend)
        
        # Rysuj każde zadanie
        for item in tasks_with_dates:
            task = item['task']
            created_at = to_naive(item['created_at'])
            due_date = to_naive(item['due_date'])
            
            task_subject = task.get("task_subject") or task.get("title", "Zadanie")
            assigned_to = task.get("assigned_to") or task.get("assignee", "—")
            completed = task.get("completed", False)
            
            # Oblicz pozycję i długość paska
            start_offset = (created_at - min_date).days
            duration = (due_date - created_at).days + 1
            
            # Kontener dla paska Gantta
            task_row = QWidget()
            task_row_layout = QHBoxLayout(task_row)
            task_row_layout.setContentsMargins(0, 2, 0, 2)
            task_row_layout.setSpacing(8)
            
            # Nazwa zadania (stała szerokość)
            task_label = QLabel(f"{task_subject[:30]}{'...' if len(task_subject) > 30 else ''}")
            task_label.setFixedWidth(250)
            task_label.setToolTip(f"{task_subject}\nOdpowiedzialny: {assigned_to}")
            task_row_layout.addWidget(task_label)
            
            # Pasek Gantta
            gantt_bar = QWidget()
            gantt_bar.setFixedHeight(24)
            gantt_bar.setStyleSheet(
                f"background-color: {'#90EE90' if completed else '#4682B4'}; "
                f"border: 1px solid {'#228B22' if completed else '#1E4D8B'}; "
                f"border-radius: 4px;"
            )
            gantt_bar.setToolTip(
                f"Początek: {created_at.strftime('%Y-%m-%d')}\n"
                f"Koniec: {due_date.strftime('%Y-%m-%d')}\n"
                f"Czas trwania: {duration} dni\n"
                f"Status: {'Ukończone' if completed else 'W toku'}"
            )
            
            # Oblicz szerokość proporcjonalnie (max 600px dla całego zakresu)
            max_width = 600
            bar_width = int((duration / total_days) * max_width)
            offset_width = int((start_offset / total_days) * max_width)
            
            # Spacer dla offsetu
            if offset_width > 0:
                spacer = QWidget()
                spacer.setFixedWidth(offset_width)
                task_row_layout.addWidget(spacer)
            
            gantt_bar.setFixedWidth(max(bar_width, 30))  # Min 30px
            task_row_layout.addWidget(gantt_bar)
            
            # Data końca
            end_label = QLabel(due_date.strftime('%Y-%m-%d'))
            end_label.setStyleSheet("color: #666; font-size: 9pt;")
            task_row_layout.addWidget(end_label)
            
            task_row_layout.addStretch()
            
            self.chart_layout.addWidget(task_row)
        
        self.chart_layout.addStretch()

