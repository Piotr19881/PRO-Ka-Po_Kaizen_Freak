"""Dialog for creating and editing tasks in TeamWork."""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
)


class TaskDialog(QDialog):
    """Dialog tworzenia/edycji zadania."""

    def __init__(
        self,
        members: List[str],
        topic_title: str = "",
        task_data: Optional[dict] = None,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Nowe zadanie" if task_data is None else "Edytuj zadanie")
        self.setModal(True)
        self.setMinimumSize(480, 400)
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

        self._members = members
        self._task_data = task_data or {}

        layout = QVBoxLayout(self)

        form = QFormLayout()

        # Temat (read-only)
        self.topic_label = QLabel(topic_title or "—")
        form.addRow("Temat:", self.topic_label)

        # Tytuł zadania
        self.title_edit = QLineEdit()
        self.title_edit.setPlaceholderText("Krótki opis zadania")
        self.title_edit.setText(self._task_data.get("title", ""))
        form.addRow("Zadanie:", self.title_edit)

        # Opis szczegółowy
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Szczegółowy opis zadania...")
        self.description_edit.setPlainText(self._task_data.get("description", ""))
        self.description_edit.setMaximumHeight(120)
        form.addRow("Opis:", self.description_edit)

        # Dodał (read-only dla edycji)
        self.creator_combo = QComboBox()
        self.creator_combo.addItems(self._members)
        creator_val = self._task_data.get("creator")
        if creator_val and creator_val in self._members:
            self.creator_combo.setCurrentText(creator_val)
        form.addRow("Dodał:", self.creator_combo)

        # Odpowiedzialny
        self.assignee_combo = QComboBox()
        self.assignee_combo.addItem("(Nieprzypisane)")
        self.assignee_combo.addItems(self._members)
        assignee_val = self._task_data.get("assignee")
        if assignee_val:
            self.assignee_combo.setCurrentText(assignee_val)
        form.addRow("Odpowiedzialny:", self.assignee_combo)

        # Termin realizacji
        self.deadline_edit = QDateEdit()
        self.deadline_edit.setCalendarPopup(True)
        deadline_val = self._task_data.get("deadline")
        if isinstance(deadline_val, datetime):
            from PyQt6.QtCore import QDate
            self.deadline_edit.setDate(QDate(deadline_val.year, deadline_val.month, deadline_val.day))
        else:
            from PyQt6.QtCore import QDate
            self.deadline_edit.setDate(QDate.currentDate().addDays(7))
        form.addRow("Termin realizacji:", self.deadline_edit)

        # Status (checkbox)
        self.status_checkbox = QCheckBox("Wykonane")
        self.status_checkbox.setChecked(self._task_data.get("completed", False))
        form.addRow("Status:", self.status_checkbox)

        layout.addLayout(form)

        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def get_task_data(self) -> dict:
        """Zwraca dane zadania w formie słownika."""
        from PyQt6.QtCore import QDate

        deadline_qdate: QDate = self.deadline_edit.date()
        deadline_dt = datetime(deadline_qdate.year(), deadline_qdate.month(), deadline_qdate.day())

        assignee_text = self.assignee_combo.currentText()
        assignee = None if assignee_text == "(Nieprzypisane)" else assignee_text

        completed = self.status_checkbox.isChecked()
        completed_at = datetime.now() if completed and not self._task_data.get("completed") else self._task_data.get("completed_at")

        return {
            "id": self._task_data.get("id", f"task-{datetime.now().timestamp()}"),
            "title": self.title_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "creator": self.creator_combo.currentText(),
            "assignee": assignee,
            "deadline": deadline_dt,
            "completed": completed,
            "created_at": self._task_data.get("created_at", datetime.now()),
            "completed_at": completed_at,
        }
