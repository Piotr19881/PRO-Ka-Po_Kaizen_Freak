from __future__ import annotations

from typing import Optional, List, Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QHeaderView,
)

from ..Modules.task_module.task_local_database import TaskLocalDatabase
from ..utils import get_theme_manager
from ..utils.i18n_manager import t, get_i18n


class KanbanLogDialog(QDialog):
    """Dialog presenting Kanban performance logs with basic filters."""

    def __init__(self, db: Optional[TaskLocalDatabase], parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.setObjectName("KanbanLogDialog")

        self._db = db
        self._theme_manager = get_theme_manager()
        self._i18n = get_i18n()
        self._i18n.language_changed.connect(self._on_language_changed)

        self._build_ui()
        self._apply_theme()
        self._update_texts()
        self.refresh_data()

    # ----------------------- UI SETUP -----------------------

    def _build_ui(self) -> None:
        self.setWindowTitle(t('kanban.log.title', 'Kanban log'))
        self.resize(1000, 560)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(16, 16, 16, 16)
        main_layout.setSpacing(12)

        # Filter row
        filter_layout = QHBoxLayout()
        filter_layout.setContentsMargins(0, 0, 0, 0)
        filter_layout.setSpacing(8)

        self._filter_label = QLabel(self)
        filter_layout.addWidget(self._filter_label)

        self._filter_combo = QComboBox(self)
        self._filter_combo.currentIndexChanged.connect(self.refresh_data)
        filter_layout.addWidget(self._filter_combo, 1)

        filter_layout.addStretch()
        main_layout.addLayout(filter_layout)

        # Table setup
        self._table = QTableWidget(self)
        self._table.setColumnCount(6)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.setSortingEnabled(True)

        header = self._table.horizontalHeader()
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for col in range(1, 6):
            header.setSectionResizeMode(col, QHeaderView.ResizeMode.ResizeToContents)
        vertical_header = self._table.verticalHeader()
        if vertical_header:
            vertical_header.setVisible(False)

        main_layout.addWidget(self._table, 1)

        self._empty_label = QLabel(self)
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_label.setWordWrap(True)
        self._empty_label.hide()
        main_layout.addWidget(self._empty_label)

    # ----------------------- DATA HANDLING -----------------------

    def refresh_data(self) -> None:
        """Reload table data from database according to active filter."""
        self._table.setSortingEnabled(False)

        mode = self._filter_combo.currentData()
        if mode not in {'completed', 'archived'}:
            mode = 'completed'

        entries: List[Dict[str, object]] = []
        if self._db:
            entries = self._db.get_kanban_log_entries(mode)

        self._table.setRowCount(len(entries))
        if not entries:
            self._empty_label.show()
        else:
            self._empty_label.hide()

        minutes_suffix = t('kanban.log.minutes_suffix', 'min')

        for row_idx, entry in enumerate(entries):
            self._table.setItem(row_idx, 0, self._create_item(entry.get('title')))
            self._table.setItem(row_idx, 1, self._create_item(self._format_datetime(entry.get('kanban_added_at'))))
            self._table.setItem(row_idx, 2, self._create_item(self._format_datetime(entry.get('kanban_started_at'))))
            completed_value = entry.get('kanban_completed_at') or entry.get('completion_date')
            self._table.setItem(row_idx, 3, self._create_item(self._format_datetime(completed_value)))

            time_to_start = self._format_duration_hm(entry.get('time_to_start_minutes'))
            self._table.setItem(row_idx, 4, self._create_item(time_to_start))

            time_to_finish = self._format_duration_minutes(entry.get('time_to_finish_minutes'), minutes_suffix)
            self._table.setItem(row_idx, 5, self._create_item(time_to_finish))

        self._table.setSortingEnabled(True)
        self._table.sortItems(3, Qt.SortOrder.DescendingOrder)

    # ----------------------- HELPERS -----------------------

    def _create_item(self, value: Optional[str]) -> QTableWidgetItem:
        text = value if value not in (None, "") else "-"
        item = QTableWidgetItem(text)
        item.setFlags(item.flags() ^ Qt.ItemFlag.ItemIsEditable)
        return item

    def _format_datetime(self, raw_value: Optional[str]) -> str:
        dt = TaskLocalDatabase._parse_datetime(raw_value) if raw_value else None
        if not dt:
            return "-"
        return dt.strftime("%d.%m.%Y %H:%M")

    def _format_duration_hm(self, minutes_value: Optional[int]) -> str:
        if minutes_value is None or minutes_value < 0:
            return "-"
        hours = minutes_value // 60
        minutes = minutes_value % 60
        return f"{hours:02d}:{minutes:02d}"

    def _format_duration_minutes(self, minutes_value: Optional[int], suffix: str) -> str:
        if minutes_value is None or minutes_value < 0:
            return "-"
        return f"{minutes_value} {suffix}".strip()

    # ----------------------- INTERNATIONALIZATION -----------------------

    def _update_texts(self) -> None:
        self.setWindowTitle(t('kanban.log.title', 'Kanban log'))
        self._filter_label.setText(t('kanban.log.filter.label', 'Show:'))

        current_mode = self._filter_combo.currentData()
        options = [
            ('completed', t('kanban.log.filter.completed', 'Completed tasks')),
            ('archived', t('kanban.log.filter.archived', 'Archived tasks')),
        ]

        self._filter_combo.blockSignals(True)
        self._filter_combo.clear()
        for value, label in options:
            self._filter_combo.addItem(label, value)

        values = [value for value, _ in options]
        if current_mode in values:
            index = values.index(current_mode)
        else:
            index = 0
        self._filter_combo.setCurrentIndex(index)
        self._filter_combo.blockSignals(False)

        headers = [
            t('kanban.log.column.title', 'Task title'),
            t('kanban.log.column.added', 'Added to Kanban'),
            t('kanban.log.column.started', 'In progress since'),
            t('kanban.log.column.completed', 'Completed at'),
            t('kanban.log.column.time_to_start', 'Lead time (HH:MM)'),
            t('kanban.log.column.time_to_finish', 'Cycle time (min)'),
        ]
        self._table.setHorizontalHeaderLabels(headers)

        self._empty_label.setText(t('kanban.log.empty', 'No Kanban log entries to display.'))

    def _on_language_changed(self, _: str) -> None:
        self._update_texts()
        self.refresh_data()

    # ----------------------- THEME -----------------------

    def _apply_theme(self) -> None:
        colors = self._theme_manager.get_current_colors() if self._theme_manager else {}
        bg_main = colors.get('bg_main', '#FFFFFF')
        text_primary = colors.get('text_primary', '#1A1A1A')
        bg_secondary = colors.get('bg_secondary', '#F5F5F5')
        border = colors.get('border_light', '#CCCCCC')

        self.setStyleSheet(
            f"""
            QDialog#KanbanLogDialog {{
                background-color: {bg_main};
                color: {text_primary};
            }}
            QLabel {{
                color: {text_primary};
            }}
            QComboBox {{
                background-color: {bg_main};
                color: {text_primary};
                border: 1px solid {border};
                border-radius: 6px;
                padding: 4px 8px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QTableWidget {{
                background-color: {bg_main};
                alternate-background-color: {bg_secondary};
                gridline-color: {border};
                color: {text_primary};
            }}
            QHeaderView::section {{
                background-color: {bg_secondary};
                color: {text_primary};
                padding: 6px;
                border: none;
            }}
            """
        )

    def closeEvent(self, event) -> None:  # type: ignore[override]
        try:
            self._i18n.language_changed.disconnect(self._on_language_changed)
        except Exception:
            pass
        super().closeEvent(event)
