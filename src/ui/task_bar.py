"""Dolny pasek szybkiego wprowadzania zadań i notatek."""

from __future__ import annotations

import json
import platform
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Callable, Dict, List, Optional

from loguru import logger
from PyQt6.QtCore import QEvent, QObject, Qt, pyqtSignal
from PyQt6.QtGui import QKeyEvent
from PyQt6.QtWidgets import (
	QCheckBox,
	QComboBox,
	QDoubleSpinBox,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QPushButton,
	QSpinBox,
	QVBoxLayout,
	QWidget,
)

from ..utils.i18n_manager import t
from .ui_task_simple_dialogs import DatePickerDialog


@dataclass
class QuickField:
	"""Opisuje pojedyncze pole konfigurowane w pasku szybkiego wprowadzania."""

	column_id: str
	storage_key: str
	storage_category: str  # 'system' lub 'custom'
	config: Dict[str, Any]
	container: QWidget
	label: QLabel
	widget: QWidget
	getter: Callable[[], Optional[Any]]
	reset: Callable[[], None]


class TaskBar(QWidget):
	"""Pasek dodawania zadań z dodatkowymi polami użytkownika."""

	task_added = pyqtSignal(dict)
	note_requested = pyqtSignal(str)

	_SYSTEM_FIELD_MAP = {
		"status": "status",
		"data realizacji": "completion_date",
		"completion_date": "completion_date",
		"alarm": "alarm_date",
		"alarm_date": "alarm_date",
		"tag": "tags",
		"tags": "tags",
	}

	_BLOCKED_COLUMNS = {
		"zadanie",
		"kanban",
		"id",
		"position",
		"subtaski",
		"notatka",
		"archiwum",
		"data dodania",
		"data aktualizacji",
		"id notatki",
		"id kanban",
	}

	def __init__(
		self,
		parent: Optional[QWidget] = None,
		*,
		task_logic: Any | None = None,
		local_db: Any | None = None,
	) -> None:
		super().__init__(parent)
		self.task_logic = task_logic
		self.local_db = local_db
		self._custom_lists: Dict[str, List[str]] = {}
		self._tags: List[Dict[str, Any]] = []
		self._quick_columns: List[Dict[str, Any]] = []
		self._fields: List[QuickField] = []

		self._setup_ui()
		self.reload_configuration()

	def set_data_sources(self, *, task_logic: Any | None = None, local_db: Any | None = None) -> None:
		"""Aktualizuje referencje do logiki zadań oraz lokalnej bazy danych."""
		if task_logic is not None:
			self.task_logic = task_logic
		if local_db is not None:
			self.local_db = local_db
		self.reload_configuration()

	def _setup_ui(self) -> None:
		main_layout = QVBoxLayout(self)
		main_layout.setContentsMargins(5, 5, 5, 5)
		main_layout.setSpacing(5)

		row1_layout = QHBoxLayout()
		row1_layout.setSpacing(5)

		self.task_input = QLineEdit()
		self.task_input.setPlaceholderText(t("quick_input.placeholder"))
		self.task_input.setMinimumHeight(35)
		self.task_input.installEventFilter(self)
		row1_layout.addWidget(self.task_input, stretch=10)

		self.btn_add = QPushButton("+")
		self.btn_add.setFixedSize(35, 35)
		self.btn_add.setObjectName("quickAddButton")
		self.btn_add.setToolTip(t("quick_input.add"))
		self.btn_add.clicked.connect(self._on_add_clicked)
		row1_layout.addWidget(self.btn_add)

		self.btn_note = QPushButton("📝")
		self.btn_note.setFixedSize(35, 35)
		self.btn_note.setObjectName("quickNoteButton")
		self.btn_note.clicked.connect(self._on_note_clicked)
		row1_layout.addWidget(self.btn_note)

		self.btn_microphone = QPushButton("🎤")
		self.btn_microphone.setFixedSize(50, 35)
		self.btn_microphone.setObjectName("quickMicButton")
		self.btn_microphone.setToolTip(t("quick_input.voice_typing"))
		self.btn_microphone.clicked.connect(self._on_microphone_clicked)
		row1_layout.addWidget(self.btn_microphone)

		main_layout.addLayout(row1_layout)

		self.row2_layout = QHBoxLayout()
		self.row2_layout.setSpacing(5)

		self.checkbox_kanban = QCheckBox()
		self.checkbox_kanban.setMinimumSize(30, 30)
		self.checkbox_kanban.setObjectName("bigCheckbox")
		self.checkbox_kanban.setToolTip(t("quick_input.add_to_kanban"))

		self.kanban_container = QWidget()
		kanban_layout = QVBoxLayout(self.kanban_container)
		kanban_layout.setContentsMargins(0, 0, 0, 0)
		kanban_layout.setSpacing(2)
		self.kanban_label = QLabel("Kanban")
		self.kanban_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
		kanban_layout.addWidget(self.kanban_label)
		kanban_layout.addWidget(self.checkbox_kanban, alignment=Qt.AlignmentFlag.AlignCenter)

		main_layout.addLayout(self.row2_layout)

	def reload_configuration(self) -> None:
		"""Wczytuje konfigurację kolumn i odbudowuje pola."""
		self._load_auxiliary_data()
		self._quick_columns = self._load_quick_columns()
		self._rebuild_field_widgets()

	def _load_auxiliary_data(self) -> None:
		self._custom_lists = {}
		self._tags = []
		if self.local_db is None:
			logger.warning("[TaskBar] No database available for auxiliary data")
			return
		if hasattr(self.local_db, "get_custom_lists"):
			try:
				lists = self.local_db.get_custom_lists()
				self._custom_lists = {
					str(lst.get("name", "")): lst.get("values", []) for lst in lists
				}
				logger.info(f"[TaskBar] Loaded {len(self._custom_lists)} custom list(s)")
			except Exception as exc:  # pragma: no cover - log only
				logger.error(f"[TaskBar] Failed to load custom lists: {exc}")
		if hasattr(self.local_db, "get_tags"):
			try:
				self._tags = self.local_db.get_tags()
				logger.info(f"[TaskBar] Loaded {len(self._tags)} tag(s): {[t.get('name') for t in self._tags]}")
			except Exception as exc:  # pragma: no cover - log only
				logger.error(f"[TaskBar] Failed to load tags: {exc}")

	def _load_quick_columns(self) -> List[Dict[str, Any]]:
		if self.local_db is None or not hasattr(self.local_db, "load_columns_config"):
			return []
		try:
			columns = self.local_db.load_columns_config()
		except Exception as exc:  # pragma: no cover - log only
			logger.error(f"[TaskBar] Failed to load column configuration: {exc}")
			return []

		sorted_columns = sorted(columns, key=lambda col: col.get("position", 0))
		allowed_system = set(self._SYSTEM_FIELD_MAP.keys())

		quick_columns: List[Dict[str, Any]] = []
		for column in sorted_columns:
			column_id = self._normalize_column_id(column)
			lower_id = column_id.lower()

			if not column.get("visible_bar", False):
				continue
			if lower_id in self._BLOCKED_COLUMNS:
				continue
			if column.get("system", column.get("is_system", False)) and lower_id not in allowed_system:
				continue
			quick_columns.append(column)
			if len(quick_columns) >= 5:
				break

		logger.info(f"[TaskBar] Quick input configured with {len(quick_columns)} column(s)")
		return quick_columns

	def _rebuild_field_widgets(self) -> None:
		if not hasattr(self, "row2_layout"):
			return

		self.kanban_container.setParent(None)

		while self.row2_layout.count():
			item = self.row2_layout.takeAt(0)
			if item is None:
				continue
			widget = item.widget()
			if widget is not None:
				widget.deleteLater()

		self._fields.clear()

		for column in self._quick_columns:
			field = self._create_field(column)
			if field is None:
				continue
			self.row2_layout.addWidget(field.container, stretch=1)
			self._fields.append(field)

		self.row2_layout.addWidget(self.kanban_container)

	def _create_field(self, column: Dict[str, Any]) -> Optional[QuickField]:
		column_id = self._normalize_column_id(column)
		storage_key, storage_category = self._resolve_storage(column_id, column)
		if storage_key is None:
			return None

		display_name = column.get("name") or column_id
		field_type = str(column.get("type", "")).lower()
		list_name_lower = str(column.get("list_name", "")).strip().lower()
		is_tag_field = column_id.lower() in {"tag", "tags"} or list_name_lower == "tags"
		if is_tag_field and field_type not in {"lista", "list"}:
			logger.debug(
				f"[TaskBar] Forcing field '{column_id}' to list type due to tag configuration"
			)
			field_type = "lista"
		
		logger.debug(f"[TaskBar] Creating field for '{column_id}': type={field_type}, storage_key={storage_key}, category={storage_category}")

		container = QWidget()
		layout = QVBoxLayout(container)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setSpacing(2)

		label = QLabel(display_name)
		label.setAlignment(Qt.AlignmentFlag.AlignLeft)
		layout.addWidget(label)

		widget: QWidget
		getter: Callable[[], Optional[Any]]
		reset: Callable[[], None]

		default_value = column.get("default_value")

		if field_type in {"text", "tekstowa", "tekst", "string", "str"}:
			logger.debug(f"[TaskBar] Creating TEXT field for '{column_id}'")
			widget = QLineEdit()
			widget.setMinimumHeight(28)
			widget.setPlaceholderText(display_name)
			widget.setText(str(default_value or ""))

			def _getter_text(line=widget) -> Optional[str]:
				value = line.text().strip()
				return value or None

			def _reset_text(line=widget, default=widget.text()) -> None:
				line.setText(default)

			getter = _getter_text
			reset = _reset_text
			layout.addWidget(widget)

		elif field_type in {"data", "date", "datetime", "alarm"}:
			logger.debug(f"[TaskBar] Creating DATE field for '{column_id}'")
			date_container = QWidget()
			date_layout = QHBoxLayout(date_container)
			date_layout.setContentsMargins(0, 0, 0, 0)
			date_layout.setSpacing(4)

			date_line = QLineEdit()
			date_line.setMinimumHeight(28)
			date_line.setPlaceholderText(t("tasks.date_dialog.placeholder", "YYYY-MM-DD"))
			date_line.setReadOnly(True)

			default_text = self._format_default_date(default_value, storage_key)
			if default_text:
				date_line.setText(default_text)

			pick_button = QPushButton("📅")
			pick_button.setFixedWidth(32)
			pick_button.setToolTip(t("tasks.date_dialog.title", "Wybierz datę"))

			def _open_calendar() -> None:
				initial = self._date_to_object(date_line.text()) or date.today()
				accepted, selected_date = DatePickerDialog.prompt(
					self,
					initial_date=initial,
					title=display_name,
				)
				if accepted:
					if selected_date is None:
						date_line.clear()
					else:
						date_line.setText(selected_date.isoformat())

			pick_button.clicked.connect(_open_calendar)

			date_layout.addWidget(date_line, 1)
			date_layout.addWidget(pick_button)
			layout.addWidget(date_container)

			def _getter_date(line=date_line) -> Optional[str]:
				value = line.text().strip()
				return value or None

			def _reset_date(line=date_line, default=default_text) -> None:
				if default:
					line.setText(default)
				else:
					line.clear()

			widget = date_container
			getter = _getter_date
			reset = _reset_date

		elif field_type in {"lista", "list"}:
			logger.debug(f"[TaskBar] Creating LIST field for '{column_id}'")
			widget = QComboBox()
			widget.setMinimumHeight(28)
			widget.addItem("—", None)
			values = self._get_list_values(column_id, column)
			default_index = 0
			for idx, item in enumerate(values, start=1):
				widget.addItem(item["label"], item["value"])
				if default_value is not None and item["value"] == default_value:
					default_index = idx
			widget.setCurrentIndex(default_index)

			lowered = column_id.lower()

			def _getter_combo(combo=widget) -> Optional[Any]:
				data = combo.currentData()
				if lowered in {"tag", "tags"}:
					return [data] if data else []
				return data

			def _reset_combo(combo=widget, index=default_index) -> None:
				combo.setCurrentIndex(index)

			getter = _getter_combo
			reset = _reset_combo
			layout.addWidget(widget)

		elif field_type == "checkbox":
			widget = QCheckBox()
			widget.setChecked(str(default_value).lower() in {"1", "true", "yes"})

			def _getter_checkbox(box=widget) -> Optional[bool]:
				checked = box.isChecked()
				if storage_category == "system" and storage_key == "status":
					return True if checked else None
				return True if checked else None

			def _reset_checkbox(box=widget, default=widget.isChecked()) -> None:
				box.setChecked(default)

			getter = _getter_checkbox
			reset = _reset_checkbox
			layout.addWidget(widget, alignment=Qt.AlignmentFlag.AlignCenter)

		elif field_type in {"waluta", "currency"}:
			widget = QDoubleSpinBox()
			widget.setDecimals(2)
			widget.setMinimum(-1_000_000)
			widget.setMaximum(1_000_000)
			widget.setSingleStep(1.0)
			if default_value is not None:
				try:
					default_float = float(default_value)
				except (TypeError, ValueError):
					default_float = 0.0
			else:
				default_float = 0.0
			widget.setValue(default_float)

			def _getter_currency(spin=widget, default=default_float) -> Optional[float]:
				value = spin.value()
				return value if value != default else None

			def _reset_currency(spin=widget, default=default_float) -> None:
				spin.setValue(default)

			getter = _getter_currency
			reset = _reset_currency
			layout.addWidget(widget)

		elif field_type in {"liczbowa", "number", "numeric", "int", "integer", "float", "decimal"}:
			widget = QDoubleSpinBox()
			widget.setDecimals(0 if field_type in {"int", "integer"} else 2)
			widget.setMinimum(-1_000_000)
			widget.setMaximum(1_000_000)
			widget.setSingleStep(1.0)
			if default_value is not None:
				try:
					default_num = float(default_value)
				except (TypeError, ValueError):
					default_num = 0.0
			else:
				default_num = 0.0
			widget.setValue(default_num)

			def _getter_number(spin=widget, default=default_num) -> Optional[float]:
				value = spin.value()
				return value if value != default else None

			def _reset_number(spin=widget, default=default_num) -> None:
				spin.setValue(default)

			getter = _getter_number
			reset = _reset_number
			layout.addWidget(widget)

		elif field_type in {"czas trwania", "duration", "czas", "time"}:
			widget = QSpinBox()
			widget.setMinimum(0)
			widget.setMaximum(10_000)
			widget.setSingleStep(5)
			widget.setSuffix(" min")
			if default_value is not None:
				try:
					default_minutes = int(default_value)
				except (TypeError, ValueError):
					default_minutes = 0
			else:
				default_minutes = 0
			widget.setValue(default_minutes)

			def _getter_duration(spin=widget, default=default_minutes) -> Optional[int]:
				value = int(spin.value())
				return value if value != default else None

			def _reset_duration(spin=widget, default=default_minutes) -> None:
				spin.setValue(default)

			getter = _getter_duration
			reset = _reset_duration
			layout.addWidget(widget)

		else:
			logger.debug(f"[TaskBar] Unsupported quick input column '{column_id}' of type '{field_type}'")
			container.deleteLater()
			return None

		layout.addStretch()

		return QuickField(
			column_id=column_id,
			storage_key=storage_key,
			storage_category=storage_category,
			config=column,
			container=container,
			label=label,
			widget=widget,
			getter=getter,
			reset=reset,
		)

	def _normalize_column_id(self, column: Dict[str, Any]) -> str:
		value = column.get("column_id") or column.get("id") or ""
		return str(value).strip()

	def _resolve_storage(self, column_id: str, column: Dict[str, Any]) -> tuple[Optional[str], str]:
		lowered = column_id.lower()
		is_system = column.get("system", column.get("is_system", False))
		if is_system:
			for key, mapped in self._SYSTEM_FIELD_MAP.items():
				if lowered == key:
					return mapped, "system"
			return None, "system"
		return column_id, "custom"

	def _get_list_values(self, column_id: str, column: Dict[str, Any]) -> List[Dict[str, Any]]:
		lowered = column_id.lower()
		list_name = str(column.get("list_name", "")).strip()
		
		logger.debug(f"[TaskBar] Getting list values for '{column_id}': list_name='{list_name}', lowered='{lowered}'")

		if lowered in {"tag", "tags"} or list_name == "tags":
			logger.info(f"[TaskBar] Returning {len(self._tags)} tag(s) for field '{column_id}'")
			return [
				{"label": tag.get("name", ""), "value": tag.get("id")}
				for tag in self._tags
			]

		if list_name and list_name in self._custom_lists:
			values = self._custom_lists[list_name]
			logger.info(f"[TaskBar] Returning {len(values)} value(s) from custom list '{list_name}'")
			return [
				{"label": str(value), "value": value}
				for value in values
			]

		options = column.get("options")
		if isinstance(options, list):
			return [{"label": str(opt), "value": opt} for opt in options]
		if isinstance(options, str):
			try:
				decoded = json.loads(options)
				if isinstance(decoded, list):
					return [{"label": str(opt), "value": opt} for opt in decoded]
			except json.JSONDecodeError:
				pass

		if column.get("default_value"):
			value = column.get("default_value")
			return [{"label": str(value), "value": value}]

		logger.warning(f"[TaskBar] No values found for list field '{column_id}'")
		return []

	def _collect_task_payload(self, title: str) -> Dict[str, Any]:
		payload: Dict[str, Any] = {"title": title}
		custom_data: Dict[str, Any] = {}
		system_fields: Dict[str, Any] = {}
		collected_tags: List[int] = []

		for field in self._fields:
			value = field.getter()
			if value is None or value == "":
				continue

			if field.storage_category == "system":
				key = field.storage_key
				if key == "tags":
					if isinstance(value, list):
						collected_tags.extend([tag for tag in value if tag is not None])
				elif key in {"completion_date", "alarm_date"}:
					normalized = self._normalize_date_value(str(value), key)
					if normalized:
						system_fields[key] = normalized
				else:
					system_fields[key] = value
			else:
				custom_data[field.storage_key] = value

		if custom_data:
			payload["custom_data"] = custom_data
		if system_fields:
			payload.update(system_fields)
		if collected_tags:
			payload["tags"] = collected_tags

		payload["add_to_kanban"] = self.checkbox_kanban.isChecked()
		return payload

	def _format_default_date(self, default_value: Any, storage_key: Optional[str]) -> Optional[str]:
		"""Konwertuje wartość domyślną daty na tekstowe ISO."""
		if default_value is None:
			return None

		key = storage_key or "completion_date"
		if isinstance(default_value, datetime):
			if key == "alarm_date":
				return default_value.strftime("%Y-%m-%d %H:%M")
			return default_value.date().isoformat()
		if isinstance(default_value, date):
			return default_value.isoformat()
		if isinstance(default_value, str):
			return self._normalize_date_value(default_value, key)

		return None

	def _date_to_object(self, value: Optional[str]) -> Optional[date]:
		"""Buduje obiekt date z tekstu, obsługując słowa kluczowe."""
		if not value:
			return None

		text = value.strip()
		if not text:
			return None

		lowered = text.lower()
		if lowered in {"today", "dzis", "dziś"}:
			return datetime.now().date()
		if lowered in {"tomorrow", "jutro"}:
			return datetime.now().date() + timedelta(days=1)

		for pattern in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
			try:
				return datetime.strptime(text, pattern).date()
			except ValueError:
				continue

		try:
			return datetime.fromisoformat(text).date()
		except ValueError:
			return None

	def _normalize_date_value(self, raw: str, key: str) -> Optional[str]:
		text = raw.strip()
		if not text:
			return None

		lowered = text.lower()
		today = datetime.now().date()
		if lowered in {"today", "dzis", "dziś"}:
			return today.isoformat()
		if lowered in {"tomorrow", "jutro"}:
			return (today + timedelta(days=1)).isoformat()

		patterns = ["%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"]
		for fmt in patterns:
			try:
				dt = datetime.strptime(text, fmt)
				if "time" in fmt or "%H" in fmt or key == "alarm_date":
					return dt.strftime("%Y-%m-%d %H:%M")
				return dt.date().isoformat()
			except ValueError:
				continue

		try:
			parsed = datetime.fromisoformat(text)
			if parsed.time().hour or parsed.time().minute:
				return parsed.strftime("%Y-%m-%d %H:%M")
			return parsed.date().isoformat()
		except ValueError:
			logger.debug(f"[TaskBar] Could not normalize date value '{text}' for '{key}'")
			return text

	def _on_add_clicked(self) -> None:
		task_text = self.task_input.text().strip()
		if not task_text:
			return

		payload = self._collect_task_payload(task_text)
		self.task_added.emit(payload)
		logger.info(f"[TaskBar] Quick task payload prepared for '{task_text}'")
		
		# Wyczyść pola natychmiast po emit (nie czekaj na callback)
		self.clear_inputs()

	def _on_microphone_clicked(self) -> None:
		self.task_input.setFocus()
		if platform.system().lower() != "windows":
			logger.warning("[TaskBar] Voice typing shortcut is only available on Windows")
			return
		try:
			self._send_win_h_hotkey()
			logger.info("[TaskBar] Triggered Windows voice typing shortcut (Win+H)")
		except Exception as exc:
			logger.error(f"[TaskBar] Failed to trigger voice typing: {exc}")

	def _on_note_clicked(self) -> None:
		note_title = self.task_input.text().strip()
		self.note_requested.emit(note_title)
		logger.info(f"[TaskBar] Note requested with title: {note_title}")

	def eventFilter(self, source: Optional[QObject], event: Optional[QEvent]) -> bool:  # type: ignore[override]
		if source is self.task_input and isinstance(event, QEvent) and event.type() == QEvent.Type.KeyPress:
			if isinstance(event, QKeyEvent) and event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
				if event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
					self._on_note_clicked()
				else:
					self._on_add_clicked()
				return True
		return super().eventFilter(source, event)

	@staticmethod
	def _send_win_h_hotkey() -> None:
		import ctypes

		user32 = ctypes.windll.user32
		VK_LWIN = 0x5B
		VK_H = 0x48
		KEYEVENTF_KEYUP = 0x0002

		user32.keybd_event(VK_LWIN, 0, 0, 0)
		user32.keybd_event(VK_H, 0, 0, 0)
		user32.keybd_event(VK_H, 0, KEYEVENTF_KEYUP, 0)
		user32.keybd_event(VK_LWIN, 0, KEYEVENTF_KEYUP, 0)

	def update_translations(self) -> None:
		self.task_input.setPlaceholderText(t("quick_input.placeholder"))
		self.btn_add.setToolTip(t("quick_input.add"))
		self.btn_microphone.setToolTip(t("quick_input.voice_typing"))
		self.checkbox_kanban.setToolTip(t("quick_input.add_to_kanban"))
		self.kanban_label.setText(t("tasks.column.kanban", "Kanban"))
		for field in self._fields:
			display_name = field.config.get("name") or field.column_id
			field.label.setText(display_name)
			if isinstance(field.widget, QLineEdit):
				field.widget.setPlaceholderText(display_name)

	def clear_inputs(self) -> None:
		self.task_input.clear()
		for field in self._fields:
			field.reset()
		self.checkbox_kanban.setChecked(False)
		self.task_input.setFocus()

	def is_kanban_selected(self) -> bool:
		return self.checkbox_kanban.isChecked()

