"""Quick task dialog providing floating access to the TaskBar widget."""

from __future__ import annotations

from typing import Any, Optional

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import QDialog, QVBoxLayout, QWidget

from ..utils.i18n_manager import get_i18n, t
from ..utils.theme_manager import get_theme_manager
from .task_bar import TaskBar


class QuickTaskDialog(QDialog):
	"""Floating dialog that mirrors the bottom quick task bar."""

	task_added = pyqtSignal(dict)
	note_requested = pyqtSignal(str)

	def __init__(
		self,
		parent: Optional[QWidget] = None,
		*,
		task_logic: Any | None = None,
		local_db: Any | None = None,
	) -> None:
		super().__init__(parent)
		self.setObjectName("QuickTaskDialog")
		self.setModal(False)
		self.setWindowFlag(Qt.WindowType.Tool)

		self._theme_manager = get_theme_manager()
		self._i18n = get_i18n()
		self._i18n.language_changed.connect(self._on_language_changed)

		self.task_bar = TaskBar(task_logic=task_logic, local_db=local_db)
		self.task_bar.task_added.connect(self._emit_task_added)
		self.task_bar.note_requested.connect(self.note_requested.emit)

		layout = QVBoxLayout(self)
		layout.setContentsMargins(8, 8, 8, 8)
		layout.setSpacing(4)
		layout.addWidget(self.task_bar)

		self.setMinimumWidth(760)
		self._apply_theme()
		self.update_translations()

	def _emit_task_added(self, payload: dict) -> None:
		self.task_added.emit(payload)

	def _apply_theme(self) -> None:
		colors = self._theme_manager.get_current_colors()
		panel_bg = colors.get("bg_secondary", "#F5F5F5")
		border_color = colors.get("border_light", "#CCCCCC")
		self.setStyleSheet(
			f"""
			QDialog#QuickTaskDialog {{
				background-color: {panel_bg};
				border: 1px solid {border_color};
				border-radius: 10px;
			}}
			"""
		)

	def update_translations(self) -> None:
		self.setWindowTitle(t("quick_task_dialog.title", "Szybkie dodawanie zadania"))
		self.task_bar.update_translations()

	def _on_language_changed(self, _: str) -> None:
		self.update_translations()

	def set_data_sources(self, *, task_logic: Any | None = None, local_db: Any | None = None) -> None:
		self.task_bar.set_data_sources(task_logic=task_logic, local_db=local_db)

	def reload_configuration(self) -> None:
		self.task_bar.reload_configuration()

	def focus_input(self) -> None:
		self.task_bar.task_input.setFocus()
		self.task_bar.task_input.selectAll()

	def clear_inputs(self) -> None:
		self.task_bar.clear_inputs()

	def set_task_text(self, text: str) -> None:
		"""Ustaw tekst zadania w polu wprowadzania"""
		self.task_bar.task_input.setText(text)

	def apply_theme(self) -> None:
		self._apply_theme()

	def showEvent(self, event) -> None:  # type: ignore[override]
		super().showEvent(event)
		self._apply_theme()
		self.update_translations()
		QTimer.singleShot(0, self.focus_input)

	def closeEvent(self, event) -> None:  # type: ignore[override]
		super().closeEvent(event)
		self.task_bar.clear_inputs()
