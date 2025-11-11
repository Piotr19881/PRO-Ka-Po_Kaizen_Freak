"""Dialogs supporting AI planning flows for task and Kanban context menus."""

from __future__ import annotations

import html
import re
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor, QFont
from PyQt6.QtWidgets import (
	QDialog,
	QHBoxLayout,
	QLabel,
	QProgressBar,
	QPushButton,
	QTextEdit,
	QToolButton,
	QVBoxLayout,
	QWidget,
	QMessageBox,
)

from src.Modules.AI_module.ai_logic import (
	AIResponse,
	configure_ai_manager_from_settings,
)
from src.Modules.Note_module.ai_note_connector import AIGenerationThread
from src.utils.i18n_manager import t
from src.utils.theme_manager import get_theme_manager


class TaskAIPlanRequestDialog(QDialog):
	"""Collects prompt details, triggers AI generation, shows inline progress."""

	def __init__(self, task_title: str, task_body: str, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self._task_title = task_title
		self._task_body = task_body.strip() or task_title
		self.ai_response: Optional[AIResponse] = None
		self._generation_thread: Optional[AIGenerationThread] = None
		self._settings: dict = {}
		self.theme_manager = get_theme_manager()
		self.setWindowTitle(t('ai.plan.dialog.title', 'Plan AI dla zadania'))
		self.setModal(True)
		self.setMinimumWidth(520)
		self._build_ui()
		self.apply_theme()

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)
		layout.setSpacing(12)

		title_label = QLabel(self._task_title or t('ai.plan.dialog.untitled', 'Bez tytułu'))
		title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		title_label.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
		layout.addWidget(title_label)

		layout.addWidget(QLabel(t('ai.plan.dialog.task_label', 'Treść zadania')))
		self.task_preview = QTextEdit()
		self.task_preview.setReadOnly(True)
		self.task_preview.setPlainText(self._task_body)
		self.task_preview.setMinimumHeight(90)
		layout.addWidget(self.task_preview)

		layout.addWidget(QLabel(t('ai.plan.dialog.base_prompt', 'Prompt główny')))
		self.base_prompt_edit = QTextEdit()
		self.base_prompt_edit.setPlainText(
			t('ai.plan.dialog.base_prompt_default', 'ułóż plan wykonania zadania w punktach')
		)
		self.base_prompt_edit.setMinimumHeight(70)
		layout.addWidget(self.base_prompt_edit)

		layout.addWidget(QLabel(t('ai.plan.dialog.additional_prompt', 'Dodatkowy prompt')))
		self.additional_prompt_edit = QTextEdit()
		self.additional_prompt_edit.setPlaceholderText(
			t('ai.plan.dialog.additional_prompt_placeholder', 'Opcjonalnie dodaj dodatkowe wskazówki dla AI...')
		)
		self.additional_prompt_edit.setMinimumHeight(60)
		layout.addWidget(self.additional_prompt_edit)

		self.progress_bar = QProgressBar()
		self.progress_bar.setRange(0, 0)
		self.progress_bar.setVisible(False)
		layout.addWidget(self.progress_bar)

		buttons_layout = QHBoxLayout()
		buttons_layout.addStretch()

		cancel_button = QPushButton(t('common.cancel', 'Anuluj'))
		cancel_button.clicked.connect(self.reject)
		buttons_layout.addWidget(cancel_button)

		self.send_button = QPushButton(t('ai.plan.dialog.send', 'Wyślij do analizy'))
		self.send_button.setDefault(True)
		self.send_button.clicked.connect(self._on_send_clicked)
		buttons_layout.addWidget(self.send_button)

		layout.addLayout(buttons_layout)

	def _on_send_clicked(self) -> None:
		if self._generation_thread is not None:
			return

		base_prompt = self.base_prompt_edit.toPlainText().strip()
		if not base_prompt:
			QMessageBox.warning(self, t('common.warning', 'Ostrzeżenie'), t('ai.plan.dialog.empty_prompt', 'Prompt nie może być pusty.'))
			return

		manager, settings, error = configure_ai_manager_from_settings()
		if error:
			if error == 'missing_api_key':
				QMessageBox.warning(
					self,
					t('common.warning', 'Ostrzeżenie'),
					t('ai.plan.dialog.missing_key', 'AI nie jest skonfigurowane. Dodaj klucz w ustawieniach AI.'),
				)
			elif error.startswith('unsupported_provider'):
				QMessageBox.critical(
					self,
					t('common.error', 'Błąd'),
					t('ai.plan.dialog.unsupported_provider', 'Wybrany dostawca AI jest nieobsługiwany.'),
				)
			else:
				QMessageBox.critical(
					self,
					t('common.error', 'Błąd'),
					t('ai.plan.dialog.configuration_error', 'Nie udało się skonfigurować AI: {error}').format(error=error),
				)
			return

		if manager is None:
			QMessageBox.critical(
				self,
				t('common.error', 'Błąd'),
				t('ai.plan.dialog.configuration_error', 'Nie udało się skonfigurować AI: {error}').format(error=t('common.error', 'Błąd')),
			)
			return

		self._settings = settings
		additional_prompt = self.additional_prompt_edit.toPlainText().strip()
		system_prompt = settings.get('system_prompt') or ''
		final_prompt = self._compose_prompt(base_prompt, additional_prompt, system_prompt)

		self._generation_thread = AIGenerationThread(manager, final_prompt)
		self._generation_thread.finished.connect(self._on_generation_finished)
		self._generation_thread.error.connect(self._on_generation_error)
		self._generation_thread.start()

		self._set_ui_busy(True)

	def _compose_prompt(self, base: str, additional: str, system_prompt: str) -> str:
		parts = []
		if system_prompt.strip():
			parts.append(system_prompt.strip())
		parts.append(base.strip())
		if additional:
			parts.append(additional.strip())
		task_label = t('ai.plan.dialog.task_context_label', 'Treść zadania:')
		parts.append(f"{task_label}\n{self._task_body}")
		return "\n\n".join(parts)

	def _set_ui_busy(self, busy: bool) -> None:
		self.base_prompt_edit.setEnabled(not busy)
		self.additional_prompt_edit.setEnabled(not busy)
		self.send_button.setEnabled(not busy)
		self.progress_bar.setVisible(busy)

	def _on_generation_finished(self, response: AIResponse) -> None:
		self.ai_response = response
		self._cleanup_thread()
		if response.error:
			QMessageBox.critical(
				self,
				t('common.error', 'Błąd'),
				t('ai.plan.dialog.response_error', 'AI zwróciło błąd: {error}').format(error=response.error),
			)
			self._set_ui_busy(False)
			return

		if not response.text:
			QMessageBox.warning(
				self,
				t('common.warning', 'Ostrzeżenie'),
				t('ai.plan.dialog.empty_response', 'AI nie zwróciło żadnej treści.'),
			)
			self._set_ui_busy(False)
			return

		self.accept()

	def _on_generation_error(self, message: str) -> None:
		self._cleanup_thread()
		QMessageBox.critical(
			self,
			t('common.error', 'Błąd'),
			t('ai.plan.dialog.response_error', 'AI zwróciło błąd: {error}').format(error=message),
		)
		self._set_ui_busy(False)

	def _cleanup_thread(self) -> None:
		if self._generation_thread:
			self._generation_thread.wait()
			self._generation_thread.deleteLater()
			self._generation_thread = None

	def reject(self) -> None:  # type: ignore[override]
		self._cleanup_thread()
		super().reject()

	def apply_theme(self) -> None:
		"""Apply current theme colors to dialog elements."""
		if not self.theme_manager:
			return

		colors = self.theme_manager.get_current_colors()
		
		# Style the dialog background
		bg_main = colors.get('bg_main', '#ffffff')
		text_primary = colors.get('text_primary', '#000000')
		
		self.setStyleSheet(f"""
			QDialog {{
				background-color: {bg_main};
				color: {text_primary};
			}}
		""")


class TaskAIPlanResultDialog(QDialog):
	"""Displays AI response with simple highlighting tools and action buttons."""

	def __init__(self, task_title: str, ai_response: AIResponse, parent: Optional[QWidget] = None):
		super().__init__(parent)
		self._task_title = task_title
		self.ai_response = ai_response
		self.selected_action: Optional[str] = None
		self.theme_manager = get_theme_manager()
		self.setWindowTitle(t('ai.plan.result.title', 'Odpowiedź AI'))
		self.setMinimumSize(600, 420)
		self._build_ui()
		self.apply_theme()

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)
		layout.setSpacing(12)

		title_label = QLabel(self._task_title or t('ai.plan.dialog.untitled', 'Bez tytułu'))
		title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		title_label.setFont(QFont('Segoe UI', 11, QFont.Weight.Bold))
		layout.addWidget(title_label)

		info = QLabel(
			f"🤖 {self.ai_response.provider.value} | {self.ai_response.model}"
		)
		info.setAlignment(Qt.AlignmentFlag.AlignCenter)
		info.setObjectName("aiInfoLabel")  # For theme styling
		layout.addWidget(info)

		toolbar = QHBoxLayout()
		toolbar.addWidget(QLabel(t('ai.plan.result.highlight', 'Podświetl zaznaczenie:')))

		# Use theme-compatible highlight colors
		colors = self.theme_manager.get_current_colors() if self.theme_manager else {}
		border_color = colors.get('border_light', '#bdbdbd')
		
		for color, tooltip in [
			('#FFF9C4', t('ai.plan.result.highlight_yellow', 'Żółty')),
			('#C8E6C9', t('ai.plan.result.highlight_green', 'Zielony')),
			('#BBDEFB', t('ai.plan.result.highlight_blue', 'Niebieski')),
		]:
			btn = QToolButton()
			btn.setStyleSheet(f'background-color: {color}; border: 1px solid {border_color};')
			btn.setToolTip(tooltip)
			btn.clicked.connect(lambda _, c=color: self._apply_highlight(c))
			toolbar.addWidget(btn)

		clear_btn = QToolButton()
		clear_btn.setText(t('ai.plan.result.highlight_clear', 'Usuń'))
		clear_btn.clicked.connect(lambda: self._apply_highlight(None))
		toolbar.addWidget(clear_btn)
		toolbar.addStretch()
		layout.addLayout(toolbar)

		self.result_edit = QTextEdit()
		self.result_edit.setAcceptRichText(True)
		self.result_edit.setHtml(html.escape(self.ai_response.text).replace('\n', '<br>'))
		self.result_edit.setFont(QFont('Segoe UI', 10))
		layout.addWidget(self.result_edit, 1)

		buttons = QHBoxLayout()
		cancel_btn = QPushButton(t('common.cancel', 'Anuluj'))
		cancel_btn.clicked.connect(self.reject)
		buttons.addWidget(cancel_btn)

		self.note_btn = QPushButton(t('ai.plan.result.create_note', 'Utwórz notatkę'))
		self.note_btn.clicked.connect(lambda: self._select_action('note'))
		buttons.addWidget(self.note_btn)

		self.subtasks_btn = QPushButton(t('ai.plan.result.create_subtasks', 'Utwórz subzadania'))
		self.subtasks_btn.clicked.connect(lambda: self._select_action('subtasks'))
		buttons.addWidget(self.subtasks_btn)

		layout.addLayout(buttons)

	def _apply_highlight(self, color: Optional[str]) -> None:
		cursor = self.result_edit.textCursor()
		if not cursor.hasSelection():
			return
		fmt = QTextCharFormat()
		if color:
			fmt.setBackground(QColor(color))
		else:
			fmt.clearBackground()
		cursor.mergeCharFormat(fmt)
		self.result_edit.mergeCurrentCharFormat(fmt)

	def _select_action(self, action: str) -> None:
		self.selected_action = action
		self.accept()

	def get_plain_text(self) -> str:
		return self.result_edit.toPlainText()

	def get_html(self) -> str:
		return self.result_edit.toHtml()

	def apply_theme(self) -> None:
		"""Apply current theme colors to dialog elements."""
		if not self.theme_manager:
			return

		colors = self.theme_manager.get_current_colors()
		
		# Style the dialog background
		bg_main = colors.get('bg_main', '#ffffff')
		text_primary = colors.get('text_primary', '#000000')
		text_secondary = colors.get('text_secondary', '#6b6b6b')
		
		self.setStyleSheet(f"""
			QDialog {{
				background-color: {bg_main};
				color: {text_primary};
			}}
			QLabel#aiInfoLabel {{
				color: {text_secondary};
				font-size: 11px;
			}}
		""")


def parse_plan_to_steps(plan_text: str) -> List[str]:
	"""Extract individual steps from AI plan text."""

	steps: List[str] = []
	for raw_line in plan_text.splitlines():
		line = raw_line.strip()
		if not line:
			continue
		# Remove numbering, bullet points, and leading punctuation
		normalized = re.sub(r'^[\d]+[\.)\-\s]*', '', line)
		normalized = normalized.lstrip('-•*\t ')
		normalized = normalized.strip()
		if not normalized:
			continue
		steps.append(normalized)
	return steps
