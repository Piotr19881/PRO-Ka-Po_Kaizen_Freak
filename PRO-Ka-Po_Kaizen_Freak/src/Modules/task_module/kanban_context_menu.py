"""
Menu kontekstowe dla kart w widoku KanBan
"""
from __future__ import annotations

from typing import Optional, Dict, Any, TYPE_CHECKING, List

from PyQt6.QtWidgets import QMenu, QMessageBox, QApplication, QDialog
from PyQt6.QtGui import QAction
from PyQt6.QtCore import QPoint
from loguru import logger

from ...utils.i18n_manager import t
from ...ui.ai_task_communication_dialog import (
	TaskAIPlanRequestDialog,
	TaskAIPlanResultDialog,
	parse_plan_to_steps,
)

if TYPE_CHECKING:
	from ...ui.kanban_view import KanBanView


class KanbanContextMenu:
	"""Zarządza menu kontekstowym dla kart KanBan."""

	def __init__(self, kanban_view: KanBanView):
		self.kanban_view = kanban_view
		self.current_task_id: Optional[int] = None
		self.current_task_title: str = ""
		self.current_column: str = ""
		self.current_task: Dict[str, Any] = {}
		self.full_task: Dict[str, Any] = {}

	def show_menu(self, parent_widget, global_pos: QPoint, task_data: Dict[str, Any]) -> None:
		if not task_data:
			return

		task_id = task_data.get('task_id') or (task_data.get('full_task') or {}).get('id')
		if not task_id:
			return

		self.current_task_id = int(task_id)
		self.current_task_title = task_data.get('title') or task_data.get('full_task', {}).get('title', "")
		self.current_column = task_data.get('column_type', '') or parent_widget.property('column_type') or ''
		self.current_task = dict(task_data)
		self.full_task = task_data.get('full_task') or {}

		menu = QMenu(parent_widget)

		ai_action = QAction(t("kanban.context_menu.ai_plan", "Utwórz plan z AI"), menu)
		ai_action.triggered.connect(self._on_ai_plan)
		menu.addAction(ai_action)

		edit_action = QAction(t("kanban.context_menu.edit", "Edytuj zadanie"), menu)
		edit_action.triggered.connect(self._on_edit_task)
		menu.addAction(edit_action)

		note_action = QAction(t("kanban.context_menu.note", "Otwórz/utwórz notatkę"), menu)
		note_action.triggered.connect(self._on_note)
		menu.addAction(note_action)

		mark_done_action = QAction(t("kanban.context_menu.mark_done", "Oznacz jako ukończone"), menu)
		mark_done_action.triggered.connect(self._on_mark_done)
		menu.addAction(mark_done_action)

		menu.addSeparator()

		move_todo_action = QAction(t("kanban.context_menu.move_todo", "Przenieś do wykonania"), menu)
		move_todo_action.triggered.connect(lambda: self._on_move('todo'))
		menu.addAction(move_todo_action)

		move_review_action = QAction(t("kanban.context_menu.move_review", "Przenieś do sprawdzenia"), menu)
		move_review_action.triggered.connect(lambda: self._on_move('review'))
		menu.addAction(move_review_action)

		move_hold_action = QAction(t("kanban.context_menu.move_hold", "Przenieś do oczekujących"), menu)
		move_hold_action.triggered.connect(lambda: self._on_move('on_hold'))
		menu.addAction(move_hold_action)

		menu.addSeparator()

		if self._is_task_archived(self.current_task or self.full_task):
			restore_action = QAction(t("kanban.context_menu.restore", "Przywróć"), menu)
			restore_action.triggered.connect(lambda: self._on_archive(restore=True))
			menu.addAction(restore_action)
		else:
			archive_action = QAction(t("kanban.context_menu.archive", "Archiwizuj"), menu)
			archive_action.triggered.connect(lambda: self._on_archive(restore=False))
			menu.addAction(archive_action)

		delete_action = QAction(t("kanban.context_menu.delete", "Usuń"), menu)
		delete_action.triggered.connect(self._on_delete)
		menu.addAction(delete_action)

		menu.addSeparator()

		copy_action = QAction(t("kanban.context_menu.copy", "Kopiuj treść"), menu)
		copy_action.triggered.connect(self._on_copy)
		menu.addAction(copy_action)

		menu.exec(global_pos)

	def _on_ai_plan(self) -> None:
		if not self.current_task_title:
			return

		try:
			task_context = self._build_task_context()
			prompt_dialog = TaskAIPlanRequestDialog(
				task_title=self.current_task_title or t('kanban.card.no_title', 'Bez tytułu'),
				task_body=task_context,
				parent=self.kanban_view,
			)

			if prompt_dialog.exec() != QDialog.DialogCode.Accepted or not prompt_dialog.ai_response:
				return

			response_dialog = TaskAIPlanResultDialog(
				task_title=self.current_task_title or t('kanban.card.no_title', 'Bez tytułu'),
				ai_response=prompt_dialog.ai_response,
				parent=self.kanban_view,
			)

			if response_dialog.exec() != QDialog.DialogCode.Accepted:
				return

			if response_dialog.selected_action == 'note':
				self._create_note_with_content(
					f"Plan AI: {self.current_task_title}",
					response_dialog.get_html(),
				)
			elif response_dialog.selected_action == 'subtasks' and self.current_task_id:
				steps = parse_plan_to_steps(response_dialog.get_plain_text())
				created = self._create_subtasks_from_plan(self.current_task_id, steps)
				if created:
					QMessageBox.information(
						self.kanban_view,
						t('status.success', 'Sukces'),
						t('ai.plan.subtasks_created', 'Utworzono {count} subzadań na podstawie planu AI.').format(count=created),
					)
					self.kanban_view.refresh_board()
				else:
					QMessageBox.warning(
						self.kanban_view,
						t('common.warning', 'Ostrzeżenie'),
						t('ai.plan.subtasks_failed', 'Nie udało się utworzyć subzadań na podstawie odpowiedzi AI.'),
					)
		except Exception as exc:
			logger.error(f"[KanbanContextMenu] Failed to generate AI plan: {exc}")
			QMessageBox.critical(
				self.kanban_view,
				t("common.error", "Błąd"),
				t("kanban.context_menu.ai_error", "Błąd podczas generowania planu AI: {error}").format(error=exc),
			)

	def _build_task_context(self) -> str:
		"""Compile context string for the selected Kanban task."""
		parts: List[str] = []
		task_data = self.full_task or {}

		description = task_data.get('description') or ''
		if description:
			parts.append(str(description))

		due_date = task_data.get('due_date')
		if due_date:
			parts.append(t('task.due_date', 'Termin wykonania') + f": {due_date}")

		tags = task_data.get('tags')
		if isinstance(tags, list) and tags:
			tag_names = [str(tag.get('name')) for tag in tags if isinstance(tag, dict) and tag.get('name')]
			if tag_names:
				parts.append(t('task.tags', 'Tagi') + ': ' + ', '.join(tag_names))

		if not parts:
			parts.append(self.current_task_title or '')

		return "\n".join(part for part in parts if part).strip()

	def _on_edit_task(self) -> None:
		if self.current_task_id is None or not self.current_task_title:
			return

		try:
			from ...ui.ui_task_simple_dialogs import TaskEditDialog

			accepted, new_title = TaskEditDialog.prompt(
				parent=self.kanban_view,
				task_title=self.current_task_title,
			)
		except Exception as exc:
			logger.error(f"[KanbanContextMenu] Failed to open edit dialog: {exc}")
			return

		if accepted and new_title and new_title != self.current_task_title:
			if self._update_task(title=new_title):
				self.current_task_title = new_title
				self.kanban_view.refresh_board()

	def _on_mark_done(self) -> None:
		if self.current_task_id is None:
			return
		self.kanban_view._mark_task_done(self.current_task_id, self.current_column)

	def _on_move(self, target_column: str) -> None:
		if self.current_task_id is None:
			return
		source = self.current_column or target_column
		if source == target_column:
			return
		self.kanban_view._on_move_task(self.current_task_id, source, target_column)

	def _on_archive(self, restore: bool) -> None:
		if self.current_task_id is None:
			return
		archived_value = None if restore else 1
		if self._update_task(archived=archived_value):
			db = getattr(self.kanban_view, 'db', None)
			if not restore and db and hasattr(db, 'remove_task_from_kanban'):
				try:
					db.remove_task_from_kanban(self.current_task_id)
				except Exception as exc:
					logger.error(f"[KanbanContextMenu] Failed to pull task {self.current_task_id} from KanBan: {exc}")
			self.kanban_view.refresh_board()

	def _on_delete(self) -> None:
		if self.current_task_id is None or not self.current_task_title:
			return

		reply = QMessageBox.question(
			self.kanban_view,
			t("kanban.context_menu.delete_title", "Usuń zadanie"),
			t("kanban.context_menu.delete_confirm", "Czy na pewno chcesz usunąć zadanie:\n\n{title}?").format(
				title=self.current_task_title
			),
			QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
			QMessageBox.StandardButton.No,
		)

		if reply != QMessageBox.StandardButton.Yes:
			return

		try:
			db = getattr(self.kanban_view, 'db', None)
			if db and hasattr(db, 'delete_task') and db.delete_task(self.current_task_id):
				self.kanban_view.refresh_board()
		except Exception as exc:
			logger.error(f"[KanbanContextMenu] Failed to delete task {self.current_task_id}: {exc}")

	def _on_note(self) -> None:
		if self.current_task_id is None:
			return
		try:
			self.kanban_view.open_task_note(self.current_task_id)
		except Exception as exc:
			logger.error(f"[KanbanContextMenu] Failed to open note for task {self.current_task_id}: {exc}")

	def _on_copy(self) -> None:
		if not self.current_task_title:
			return
		clipboard = QApplication.clipboard()
		if clipboard:
			clipboard.setText(self.current_task_title)

	def _update_task(self, **kwargs) -> bool:
		if self.current_task_id is None or not getattr(self.kanban_view, 'db', None):
			return False
		try:
			db = getattr(self.kanban_view, 'db', None)
			if not db or not hasattr(db, 'update_task'):
				return False
			return bool(db.update_task(self.current_task_id, **kwargs))
		except Exception as exc:
			logger.error(f"[KanbanContextMenu] Failed to update task {self.current_task_id}: {exc}")
			return False

	def _create_note_with_content(self, title: str, content: str) -> None:
		db = getattr(self.kanban_view, 'db', None)
		if not db or not hasattr(db, 'create_note'):
			logger.warning("[KanbanContextMenu] Database cannot create notes")
			return

		note_id: Optional[int] = None
		try:
			note_id = db.create_note(user_id=getattr(db, 'user_id', 1), title=title, content=content)
		except Exception as exc:
			logger.error(f"[KanbanContextMenu] Failed to create note: {exc}")

		if not note_id:
			QMessageBox.warning(
				self.kanban_view,
				t("common.warning", "Ostrzeżenie"),
				t("kanban.context_menu.note_error", "Nie udało się utworzyć notatki."),
			)
			return

		if self.current_task_id is not None:
			self._update_task(note_id=note_id)

		try:
			self.kanban_view.open_task_note(self.current_task_id or note_id)
		except Exception as exc:
			logger.error(f"[KanbanContextMenu] Failed to open created note {note_id}: {exc}")

	def _is_task_archived(self, task_data: Dict[str, Any]) -> bool:
		value = (task_data or {}).get('archived')
		if value is None:
			return False
		if isinstance(value, (bool, int)):
			return bool(value)
		if isinstance(value, str):
			normalized = value.strip().lower()
			return normalized not in {'', '0', 'false', 'none', 'null'}
		return bool(value)

	def _create_subtasks_from_plan(self, parent_id: int, steps: List[str]) -> int:
		"""Create subtasks using the Kanban view database."""
		db = getattr(self.kanban_view, 'db', None)
		if not db or not hasattr(db, 'add_task'):
			return 0

		created = 0
		for step in steps:
			clean_step = step.strip()
			if not clean_step:
				continue
			try:
				subtask_id = db.add_task(title=clean_step, parent_id=parent_id)
				if subtask_id:
					created += 1
			except Exception as exc:
				logger.error(f"[KanbanContextMenu] Failed to create subtask '{clean_step}': {exc}")

		return created
