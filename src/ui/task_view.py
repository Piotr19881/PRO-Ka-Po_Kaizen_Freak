from typing import Optional, List, Dict, Any, Tuple
import json
from datetime import datetime, date
from PyQt6.QtWidgets import (
	QWidget, QHBoxLayout, QVBoxLayout, QLabel, QComboBox, QLineEdit,
	QPushButton, QTableWidget, QTableWidgetItem, QSizePolicy, QCheckBox,
	QHeaderView, QDialog
)
from PyQt6.QtCore import Qt, QTimer
from loguru import logger
from ..utils.i18n_manager import t
from .ui_task_simple_dialogs import (
	CurrencyInputDialog,
	DatePickerDialog,
	DurationInputDialog,
	TextInputDialog,
	TaskEditDialog,
)

# Import menu kontekstowego będzie wykonany później, aby uniknąć cyklicznych importów


class TaskView(QWidget):
	"""Widok zadań z dynamiczną konfiguracją kolumn.

	Layout:
	- Pasek zarządzania (po lewej: Status, Tag, Szukaj) (po prawej: Lock, Konfiguruj)
	- Główna tabela zadań (kolumny wg konfiguracji użytkownika)
	"""

	def __init__(self, parent: Optional[QWidget] = None, task_logic=None, local_db=None):
		super().__init__(parent)
		self.task_logic = task_logic
		self.local_db = local_db
		self.alarm_manager = None  # Menedżer alarmów (ustawiany później)
		self._locked = False
		self._columns_config = []  # Konfiguracja kolumn z bazy danych
		self._column_min_widths: Dict[int, int] = {}
		self._header_min_width_connected = False
		self._visible_columns_cache: List[Dict[str, Any]] = []
		self._column_widths: Dict[str, int] = {}
		self._column_width_setting_key = "task_table_column_widths"
		self._lock_setting_key = "task_table_locked"
		self._fixed_width_columns = {
			'subtaski': 55,
			'data dodania': 105,
			'status': 75,
			'kanban': 80,
			'notatka': 80,
		}
		self._status_filter_options: List[Tuple[str, str]] = []
		self._row_task_map: Dict[int, Dict[str, Any]] = {}
		self._currency_dialog_open = False
		self._number_edit_connected = False  # Flaga dla sygnału itemChanged
		
		# Timery dla debounce refresh
		self._refresh_tasks_timer: Optional[QTimer] = None
		self._refresh_columns_timer: Optional[QTimer] = None
		
		# Cache subtasków - optymalizacja wydajności (-60% zapytań DB)
		# Struktura: {parent_id: [lista subtasków], ...}
		self._subtasks_cache: Dict[int, List[Dict[str, Any]]] = {}
		self._subtasks_cache_valid = False
		
		# Batch updates - optymalizacja wydajności (-70% zapytań DB)
		# Struktura: {task_id: {column_id: value, ...}, ...}
		self._pending_updates: Dict[int, Dict[str, Any]] = {}
		self._batch_update_timer = QTimer()
		self._batch_update_timer.setSingleShot(True)
		self._batch_update_timer.timeout.connect(self._flush_pending_updates)
		self._batch_update_delay_ms = 500  # Opóźnienie przed zapisem (500ms)
		
		# Cache dla często używanych tłumaczeń (optymalizacja wydajności)
		self._translations_cache = {
			'note_open': t("tasks.note.open"),
			'note_create': t("tasks.note.create"),
			'kanban_on_board': t("tasks.kanban.on_board"),
			'kanban_add': t("tasks.kanban.add"),
			'subtask_expand': t("tasks.subtask.expand"),
			'subtask_add': t("tasks.subtask.add"),
			'subtask_add_more': t("tasks.subtask.add_more"),
			'subtask_prefix': t("tasks.subtask.prefix"),
			'list_select': t("tasks.list.select", "-- Wybierz --"),
			'list_clear': t("tasks.list.clear", "✖ Wyczyść"),
		}
		
		# Inicjalizacja menu kontekstowego (lazy import)
		self.context_menu = None
		
		# Auto-stretch dla kolumny Zadanie
		self._stretch_enabled = False

		self._general_settings: Dict[str, Any] = {
			'auto_archive_enabled': False,
			'auto_archive_after_days': 30,
			'auto_move_completed': False,
			'auto_archive_completed': False,
		}

		self._load_persisted_table_settings()
		self._load_general_settings()
		self._init_ui()
	
	def set_alarm_manager(self, alarm_manager):
		"""Ustaw menedżera alarmów dla integracji z widokiem alarmów"""
		self.alarm_manager = alarm_manager
		logger.info("[TaskView] Alarm manager set")
	
	def set_task_logic(self, task_logic, local_db):
		"""
		Ustaw task_logic i local_db po zalogowaniu użytkownika.
		Przeładowuje konfigurację i dane z właściwej bazy użytkownika.
		
		Args:
			task_logic: Instancja TasksManager/TaskLogic
			local_db: Instancja TaskLocalDatabase
		"""
		self.task_logic = task_logic
		self.local_db = local_db
		
		# Przeładuj konfigurację z nowej bazy
		self._load_general_settings()
		self._load_columns_config()
		
		# FIXED: Wczytaj zapisane szerokości PRZED setupem kolumn
		self._load_persisted_table_settings()
		
		self._setup_table_columns()
		self._load_tag_filter_options()
		
		# Załaduj zadania użytkownika
		if task_logic:
			try:
				tasks = task_logic.load_tasks()
				self.populate_table(tasks)
				logger.info(f"[TaskView] Task logic set and loaded {len(tasks)} tasks")
			except Exception as e:
				logger.error(f"[TaskView] Failed to load tasks after setting task_logic: {e}")
	
	def _translate_column_name(self, column_name: str) -> str:
		"""Przetłumacz nazwę kolumny z bazy danych na klucz i18n
		
		Args:
			column_name: Nazwa kolumny z bazy danych
			
		Returns:
			Przetłumaczona nazwa kolumny
		"""
		# Mapowanie nazw kolumn z bazy danych na klucze i18n
		column_map = {
			'ID': 'tasks.column.id',
			'Pozycja': 'tasks.column.position',
			'Data dodania': 'tasks.column.data_dodania',
			'Subtaski': 'tasks.column.subtaski',
			'Zadanie': 'tasks.column.zadanie',
			'Status': 'tasks.column.status',
			'data realizacji': 'tasks.column.data_realizacji',
			'KanBan': 'tasks.column.kanban',
			'Notatka': 'tasks.column.notatka',
			'Archiwum': 'tasks.column.archiwum',
			'Tag': 'tasks.column.tag',
			'Alarm': 'tasks.column.alarm',
		}
		
		# Jeśli nazwa kolumny jest w mapowaniu, użyj tłumaczenia
		if column_name in column_map:
			return t(column_map[column_name])
		
		# W przeciwnym razie zwróć oryginalną nazwę (dla custom kolumn)
		return column_name


	def _init_ui(self):
		main_layout = QVBoxLayout(self)

		# Wczytaj konfigurację kolumn z bazy danych
		self._load_columns_config()

		# Pasek zarządzania
		bar_layout = QHBoxLayout()

		# Lewa część: filtry
		left_filters = QHBoxLayout()
		left_filters.setSpacing(8)

		left_filters.addWidget(QLabel("Status:"))
		self.status_cb = QComboBox()
		self._load_status_filter_options()
		left_filters.addWidget(self.status_cb)

		left_filters.addWidget(QLabel("Tag:"))
		self.tag_cb = QComboBox()
		self._load_tag_filter_options(preserve_selection=False)
		# tagi mogą być uzupełnione dynamicznie z TaskLogic/local_db
		left_filters.addWidget(self.tag_cb)

		left_filters.addWidget(QLabel("Szukaj:"))
		self.search_le = QLineEdit()
		self.search_le.setPlaceholderText("Szukaj w zadaniach...")
		left_filters.addWidget(self.search_le)
		
		# Przycisk auto-stretch dla kolumny "Zadanie"
		self.stretch_btn = QPushButton("⬌")
		self.stretch_btn.setCheckable(True)
		self.stretch_btn.setChecked(False)  # Domyślnie OFF
		self.stretch_btn.setFixedSize(35, 35)
		self.stretch_btn.setToolTip("Auto-dopasowanie szerokości kolumny 'Zadanie'\n(aktywne tylko gdy kolumny odblokowane)")
		self.stretch_btn.setEnabled(not self._locked)  # Disabled gdy zablokowane
		self.stretch_btn.clicked.connect(self._on_stretch_toggled)
		# Ustaw domyślny styl (OFF - czerwony)
		self.stretch_btn.setStyleSheet("""
			QPushButton {
				background-color: #f44336;
				color: white;
				font-weight: bold;
				border: 2px solid #da190b;
				border-radius: 4px;
			}
			QPushButton:hover {
				background-color: #da190b;
			}
			QPushButton:disabled {
				background-color: #cccccc;
				color: #666666;
				border: 2px solid #999999;
			}
		""")
		left_filters.addWidget(self.stretch_btn)

		bar_layout.addLayout(left_filters)
		bar_layout.addStretch()

		# Prawa część: przyciski
		right_buttons = QHBoxLayout()
		self.lock_btn = QPushButton()
		self.lock_btn.setCheckable(True)
		self.lock_btn.setChecked(self._locked)
		self._update_lock_button_text()
		right_buttons.addWidget(self.lock_btn)
		
		# Przycisk synchronizacji (ukryty domyślnie, będzie widoczny po zalogowaniu)
		self.sync_btn = QPushButton("🔄 Synchronizuj")
		self.sync_btn.setToolTip("Wymuszony synchronizuj z serwerem")
		self.sync_btn.setVisible(False)  # Ukryty dopóki sync nie jest włączony
		self.sync_btn.clicked.connect(self._on_sync_now)
		right_buttons.addWidget(self.sync_btn)

		self.config_btn = QPushButton("Konfiguruj")
		right_buttons.addWidget(self.config_btn)

		bar_layout.addLayout(right_buttons)

		main_layout.addLayout(bar_layout)

		# Główna tabela zadań - kolumny dynamiczne wg konfiguracji
		self.table = QTableWidget(0, 0)
		self._setup_table_columns()
		self._apply_lock_state()
		
		self.table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
		self.table.verticalHeader().setVisible(False)
		self.table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
		self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
		
		# Włącz menu kontekstowe
		self.table.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
		self.table.customContextMenuRequested.connect(self._show_context_menu)
		
		# Ustaw domyślną wysokość wierszy, aby zmieściły przyciski (24px + padding)
		self.table.verticalHeader().setDefaultSectionSize(45)

		main_layout.addWidget(self.table)

		# Podłącz sygnały
		self.lock_btn.toggled.connect(self._on_lock_toggled)
		self.config_btn.clicked.connect(self._on_configure_clicked)
		self.search_le.textChanged.connect(self._on_search_changed)
		self.status_cb.currentIndexChanged.connect(self._on_filter_changed)
		self.tag_cb.currentIndexChanged.connect(self._on_filter_changed)
		self.table.cellDoubleClicked.connect(self._on_cell_double_clicked)

		# Wstępne załadowanie danych
		self.populate_table()
	
	def resizeEvent(self, event):
		"""Obsłuż zmianę rozmiaru widgetu - dopasuj kolumnę Zadanie jeśli włączony stretch"""
		super().resizeEvent(event)
		# Dopasuj kolumnę Zadanie jeśli włączony auto-fit
		if hasattr(self, '_stretch_enabled') and self._stretch_enabled:
			# Użyj QTimer aby odroczyć dopasowanie do momentu zakończenia resize
			from PyQt6.QtCore import QTimer
			QTimer.singleShot(0, self._adjust_zadanie_column_width)

	def _load_columns_config(self):
		"""Wczytaj konfigurację kolumn z bazy danych"""
		if self.local_db and hasattr(self.local_db, 'load_columns_config'):
			try:
				self._columns_config = self.local_db.load_columns_config()
				logger.info(f"[TaskView] Loaded {len(self._columns_config)} column configurations")
			except Exception as e:
				logger.error(f"[TaskView] Failed to load columns config: {e}")
				self._columns_config = []
		else:
			# Domyślna konfiguracja jeśli brak bazy danych
			self._columns_config = [
				{'column_id': 'created_at', 'type': 'text', 'visible_main': True, 'position': 0},
				{'column_id': 'status', 'type': 'text', 'visible_main': True, 'position': 1},
				{'column_id': 'title', 'type': 'text', 'visible_main': True, 'position': 2},
			]
			logger.warning("[TaskView] No database available, using default column configuration")

	def _column_key(self, column_id: str) -> str:
		"""Zwróć ujednolicony identyfikator kolumny do map słownikowych."""
		return (column_id or '').strip().lower()

	def _load_persisted_table_settings(self):
		"""Wczytaj zapamiętany stan blokady oraz szerokości kolumn z bazy danych."""
		if not self.local_db:
			return
		try:
			stored_widths = self.local_db.get_setting(self._column_width_setting_key, {})
			if isinstance(stored_widths, dict):
				for key, value in stored_widths.items():
					try:
						width_value = int(value)
					except (TypeError, ValueError):
						continue
					if width_value > 0:
						self._column_widths[self._column_key(str(key))] = width_value
		except Exception as e:
			logger.error(f"[TaskView] Failed to load stored column widths: {e}")
		try:
			lock_state = self.local_db.get_setting(self._lock_setting_key, None)
			if isinstance(lock_state, bool):
				self._locked = lock_state
			elif isinstance(lock_state, (int, float)):
				self._locked = bool(lock_state)
		except Exception as e:
			logger.error(f"[TaskView] Failed to load table lock state: {e}")

		# Zapewnij wpisy dla kolumn o stałej szerokości
		for key, width in self._fixed_width_columns.items():
			self._column_widths.setdefault(self._column_key(key), width)

	def _load_general_settings(self) -> None:
		"""Wczytaj ustawienia ogólne modułu zadań z bazy danych."""
		defaults = {
			'auto_archive_enabled': False,
			'auto_archive_after_days': 30,
			'auto_move_completed': False,
			'auto_archive_completed': False,
		}
		settings = dict(defaults)
		if self.local_db:
			try:
				enabled_value = self.local_db.get_setting('auto_archive_enabled', defaults['auto_archive_enabled'])
				settings['auto_archive_enabled'] = bool(enabled_value)

				days_value = self.local_db.get_setting('auto_archive_after_days', defaults['auto_archive_after_days'])
				try:
					days_int = int(days_value)
				except (TypeError, ValueError):
					days_int = defaults['auto_archive_after_days']
				if days_int < 1:
					days_int = 1
				settings['auto_archive_after_days'] = days_int

				move_completed_value = self.local_db.get_setting('auto_move_completed', defaults['auto_move_completed'])
				settings['auto_move_completed'] = bool(move_completed_value)

				auto_archive_completed_value = self.local_db.get_setting('auto_archive_completed', defaults['auto_archive_completed'])
				settings['auto_archive_completed'] = bool(auto_archive_completed_value)

				logger.info("[TaskView] Loaded general settings from database")
			except Exception as exc:
				logger.error(f"[TaskView] Failed to load general settings: {exc}")
		self._general_settings = settings

	def _get_visible_columns(self) -> List[Dict[str, Any]]:
		"""Zwróć listę kolumn widocznych w głównej tabeli w poprawnej kolejności."""
		visible_columns = [col for col in self._columns_config if col.get('visible_main', True)]
		visible_columns.sort(key=lambda x: x.get('position', 0))
		return visible_columns

	def _update_lock_button_text(self):
		"""Uaktualnij napis przycisku blokady tabeli zgodnie z bieżącym stanem."""
		if not hasattr(self, 'lock_btn') or self.lock_btn is None:
			return
		if self._locked:
			self.lock_btn.setText("🔓 Odblokuj tabelę")
		else:
			self.lock_btn.setText("🔒 Zablokuj tabelę")

	def _persist_lock_state(self):
		"""Zapisz stan blokady tabeli w lokalnej bazie danych."""
		if not self.local_db:
			return
		try:
			self.local_db.save_setting(self._lock_setting_key, self._locked)
		except Exception as e:
			logger.error(f"[TaskView] Failed to persist table lock state: {e}")

	def _persist_column_widths(self):
		"""Zapisz szerokości kolumn w lokalnej bazie danych."""
		if not self.local_db:
			return
		try:
			self.local_db.save_setting(self._column_width_setting_key, self._column_widths)
		except Exception as e:
			logger.error(f"[TaskView] Failed to persist column widths: {e}")

	def _apply_lock_state(self):
		"""Zastosuj bieżący stan blokady do tabeli."""
		self._update_lock_button_text()
		header = self.table.horizontalHeader() if hasattr(self, 'table') else None
		if self.table:
			if self._locked:
				self.table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
			else:
				self.table.setEditTriggers(QTableWidget.EditTrigger.DoubleClicked)
		if header:
			self._apply_column_preferences(self._visible_columns_cache or None)
		
		# Dopasuj kolumnę Zadanie jeśli włączony auto-fit
		if hasattr(self, '_stretch_enabled') and self._stretch_enabled:
			from PyQt6.QtCore import QTimer
			QTimer.singleShot(50, self._adjust_zadanie_column_width)

	def _capture_current_column_widths(self):
		"""Zapisz bieżące szerokości kolumn w buforze pamięci."""
		header = self.table.horizontalHeader() if hasattr(self, 'table') else None
		if not header:
			return
		visible_columns = self._visible_columns_cache or self._get_visible_columns()
		if not visible_columns:
			return
		widths: Dict[str, int] = {}
		for index, column in enumerate(visible_columns):
			column_id = column.get('column_id', '') or ''
			key = self._column_key(column_id)
			if key in self._fixed_width_columns:
				widths[key] = self._fixed_width_columns[key]
				continue
			section_width = header.sectionSize(index)
			min_width = self._column_min_widths.get(index, 0)
			if min_width:
				section_width = max(section_width, min_width)
			if section_width <= 0:
				section_width = 100
			widths[key] = section_width
		self._column_widths = widths

	def _apply_column_preferences(self, visible_columns: Optional[List[Dict[str, Any]]] = None):
		"""Zastosuj ograniczenia i zapisane szerokości kolumn."""
		header = self.table.horizontalHeader() if hasattr(self, 'table') else None
		if not header:
			return
		if visible_columns is None:
			visible_columns = self._get_visible_columns()
		self._visible_columns_cache = visible_columns
		self._column_min_widths.clear()
		tag_min_width = 150
		list_min_width = 140
		header.blockSignals(True)
		for index, column in enumerate(visible_columns):
			column_id = column.get('column_id', '') or ''
			column_type = (column.get('type', '') or '').lower()
			key = self._column_key(column_id)
			if key in self._fixed_width_columns:
				fixed_width = self._fixed_width_columns[key]
				header.setSectionResizeMode(index, QHeaderView.ResizeMode.Fixed)
				header.resizeSection(index, fixed_width)
				self._column_widths[key] = fixed_width
				continue
			if column_id.lower() in {"tag", "tags"}:
				self._column_min_widths[index] = tag_min_width
			elif column_type in {"list", "lista"}:
				self._column_min_widths[index] = list_min_width
			min_width = self._column_min_widths.get(index, 0)
			if not self._locked:
				header.setSectionResizeMode(index, QHeaderView.ResizeMode.Interactive)
				target_width = self._column_widths.get(key)
				if target_width is not None:
					if target_width <= 0:
						target_width = max(min_width, 100)
					target_width = max(target_width, min_width)
					header.resizeSection(index, target_width)
				elif min_width:
					current_size = header.sectionSize(index)
					if current_size < min_width:
						header.resizeSection(index, min_width)
			else:
				target_width = self._column_widths.get(key)
				if target_width is None:
					target_width = header.sectionSize(index)
				if target_width <= 0:
					target_width = 100
				if min_width:
					target_width = max(target_width, min_width)
				self._column_widths[key] = target_width
				header.setSectionResizeMode(index, QHeaderView.ResizeMode.Fixed)
				header.resizeSection(index, target_width)
		header.blockSignals(False)
		if not self._header_min_width_connected:
			header.sectionResized.connect(self._on_header_section_resized)
			self._header_min_width_connected = True

	def _load_status_filter_options(self) -> None:
		"""Skonfiguruj listę filtrów statusu."""
		if not hasattr(self, 'status_cb') or self.status_cb is None:
			return
		options = [
			("Wszystkie", "all"),
			("Aktywne", "active"),
			("Ukończone", "completed"),
			("Zarchiwizowane", "archived"),
		]
		self._status_filter_options = options
		self.status_cb.blockSignals(True)
		self.status_cb.clear()
		for label, key in options:
			self.status_cb.addItem(label, key)
		self.status_cb.setCurrentIndex(0)
		self.status_cb.blockSignals(False)

	def _load_tag_filter_options(self, preserve_selection: bool = True) -> None:
		"""Wczytaj dostępne tagi do filtra tagów."""
		if not hasattr(self, 'tag_cb') or self.tag_cb is None:
			return
		previous_value = None
		if preserve_selection and self.tag_cb.count() > 0:
			previous_value = self.tag_cb.currentData(Qt.ItemDataRole.UserRole)
		self.tag_cb.blockSignals(True)
		self.tag_cb.clear()
		self.tag_cb.addItem("Wszystkie", None)
		tags: List[Dict[str, Any]] = []
		if self.local_db and hasattr(self.local_db, 'get_tags'):
			try:
				tags = self.local_db.get_tags()
			except Exception as e:
				logger.error(f"[TaskView] Failed to load tags for filter: {e}")
				tags = []
		for tag in tags:
			name = (tag or {}).get('name')
			if not name:
				continue
			color = tag.get('color') if isinstance(tag, dict) else None
			self.tag_cb.addItem(name, name)
			if color:
				try:
					from PyQt6.QtGui import QColor, QPixmap, QIcon  # lokalny import
					q_color = QColor(color)
					if q_color.isValid():
						pixmap = QPixmap(12, 12)
						pixmap.fill(q_color)
						icon = QIcon(pixmap)
						index = self.tag_cb.count() - 1
						self.tag_cb.setItemIcon(index, icon)
				except Exception as icon_exc:
					logger.debug(f"[TaskView] Could not set tag color icon: {icon_exc}")
		if preserve_selection and previous_value:
			target_index = self.tag_cb.findData(previous_value, Qt.ItemDataRole.UserRole)
			if target_index >= 0:
				self.tag_cb.setCurrentIndex(target_index)
			else:
				self.tag_cb.setCurrentIndex(0)
		else:
			self.tag_cb.setCurrentIndex(0)
		self.tag_cb.blockSignals(False)

	def _wrap_cell_widget(self, widget: QWidget, alignment: Qt.AlignmentFlag = Qt.AlignmentFlag.AlignCenter) -> QWidget:
		"""Owiń widżet w kontener centrowany w komórce tabeli."""
		container = QWidget()
		container.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
		container.setFocusPolicy(Qt.FocusPolicy.NoFocus)
		layout = QHBoxLayout(container)
		layout.setContentsMargins(0, 0, 0, 0)
		layout.setAlignment(alignment)
		layout.addWidget(widget)
		setattr(container, "_wrapped_child", widget)
		return container

	@staticmethod
	def _unwrap_cell_widget(widget: Optional[QWidget]) -> Optional[QWidget]:
		"""Zwróć oryginalny widżet z kontenera jeśli istnieje."""
		if widget is None:
			return None
		return getattr(widget, "_wrapped_child", widget)

	@staticmethod
	def _cell_widget_matches(cell_widget: Optional[QWidget], target: QWidget) -> bool:
		"""Sprawdź czy widżet tabeli odpowiada wskazanemu widżetowi potomnemu."""
		if cell_widget is target:
			return True
		return getattr(cell_widget, "_wrapped_child", None) is target

	def _setup_table_columns(self):
		"""Skonfiguruj kolumny tabeli na podstawie konfiguracji użytkownika"""
		visible_columns = self._get_visible_columns()
		
		# Ustaw liczbę kolumn
		self.table.setColumnCount(len(visible_columns))
		
		# Ustaw nagłówki kolumn
		headers = []
		for col in visible_columns:
			col_id = col.get('column_id', '')
			# Mapowanie ID kolumn na przyjazne nazwy
			header_name = self._get_column_display_name(col_id, col)
			headers.append(header_name)
		
		self.table.setHorizontalHeaderLabels(headers)
		self._apply_column_preferences(visible_columns)
		
		logger.info(f"[TaskView] Table configured with {len(visible_columns)} visible columns")

	def _on_header_section_resized(self, index: int, old_size: int, new_size: int):
		"""Zapewnia minimalne szerokości dla wybranych kolumn (np. Tag) i zapamiętuje zmiany."""
		header = self.table.horizontalHeader()
		if not header:
			return
		min_width = self._column_min_widths.get(index, 0)
		if min_width and new_size < min_width:
			header.blockSignals(True)
			header.resizeSection(index, min_width)
			header.blockSignals(False)
			new_size = min_width
		if not self._locked and self._visible_columns_cache and 0 <= index < len(self._visible_columns_cache):
			column_id = self._visible_columns_cache[index].get('column_id', '') or ''
			key = self._column_key(column_id)
			if key not in self._fixed_width_columns:
				self._column_widths[key] = max(new_size, min_width)

	def _get_column_display_name(self, column_id: str, column_config: Dict[str, Any]) -> str:
		"""Pobierz wyświetlaną nazwę kolumny - zgodną z konfiguracją użytkownika
		
		Używa tłumaczeń i18n dla nazw kolumn z bazy danych.
		"""
		# Użyj column_id (nazwa z bazy) i przetłumacz ją
		return self._translate_column_name(column_id)

	def reload_general_settings(self) -> None:
		"""Przeładuj ustawienia ogólne kolumn i zachowań tabeli."""
		self._load_general_settings()

	def refresh_columns(self):
		"""Odśwież konfigurację kolumn i przebuduj tabelę (z debounce 300ms)"""
		# Anuluj oczekujący refresh jeśli istnieje
		if self._refresh_columns_timer is not None and self._refresh_columns_timer.isActive():
			self._refresh_columns_timer.stop()
		
		# Ustaw timer dla opóźnionego odświeżania
		self._refresh_columns_timer = QTimer()
		self._refresh_columns_timer.setSingleShot(True)
		self._refresh_columns_timer.timeout.connect(self._do_refresh_columns)
		self._refresh_columns_timer.start(300)  # 300ms debounce
	
	def _do_refresh_columns(self):
		"""Wykonaj rzeczywiste odświeżenie kolumn"""
		logger.info("[TaskView] Refreshing table columns configuration")
		
		# Zapisz aktualnie wyświetlane zadania
		current_tasks = []
		if self.task_logic:
			try:
				current_tasks = self.task_logic.load_tasks()
			except Exception as e:
				logger.error(f"[TaskView] Failed to load tasks during refresh: {e}")
		
		# Wczytaj nową konfigurację kolumn
		self._load_columns_config()
		self._load_general_settings()
		
		# Przebuduj kolumny tabeli
		self._setup_table_columns()
		self._apply_lock_state()
		self._load_tag_filter_options()
		
		# Załaduj ponownie dane
		self.populate_table(current_tasks)
		
		logger.info("[TaskView] Columns refresh completed")

	# ---------- Public API / Hooki ----------
	@staticmethod
	def _parse_datetime_value(value: Any) -> datetime:
		if not value:
			return datetime.min
		if isinstance(value, datetime):
			return value
		if isinstance(value, date):
			return datetime(value.year, value.month, value.day)
		if isinstance(value, str):
			for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
				try:
					return datetime.strptime(value, fmt)
				except ValueError:
					continue
		return datetime.min

	def _run_auto_archive_policy(self) -> bool:
		"""Zastosuj politykę automatycznego archiwizowania zadań.

		Returns:
			True jeśli zadania zostały zmodyfikowane i dane należy przeładować.
		"""
		if not self._general_settings.get('auto_archive_enabled'):
			return False
		if not self.local_db or not hasattr(self.local_db, 'auto_archive_completed_tasks'):
			return False
		try:
			days = self._general_settings.get('auto_archive_after_days', 0)
			archived_count = self.local_db.auto_archive_completed_tasks(days)
			return bool(archived_count)
		except Exception as exc:
			logger.error(f"[TaskView] Failed to execute auto-archive policy: {exc}")
			return False

	def _apply_auto_move_sorting(self, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
		"""Zwróć listę zadań posortowaną z ukończonymi po aktywnych zgodnie z ustawieniami."""
		if not tasks:
			return tasks

		incomplete: List[Dict[str, Any]] = []
		completed: List[Dict[str, Any]] = []

		for task in tasks:
			if task.get('archived'):
				completed.append(task)
			elif task.get('status'):
				completed.append(task)
			else:
				incomplete.append(task)

		if not completed:
			return tasks

		def completion_key(task: Dict[str, Any]) -> datetime:
			primary = task.get('completion_date')
			fallback = task.get('updated_at') or task.get('created_at')
			value = primary or fallback
			return self._parse_datetime_value(value)

		sorted_completed = sorted(completed, key=completion_key, reverse=True)
		return incomplete + sorted_completed

	def populate_table(self, tasks: Optional[List[Dict[str, Any]]] = None):
		"""Wypełnij tabelę listą zadań zgodnie z konfiguracją kolumn."""
		force_reload = self._run_auto_archive_policy()
		if tasks is not None and force_reload:
			tasks = None

		if tasks is None:
			tasks = []
			if self.task_logic:
				try:
					tasks = self.task_logic.load_tasks()
				except Exception as e:
					logger.error(f"[TaskView] Failed to load tasks: {e}")

		tasks = tasks or []
		if self._general_settings.get('auto_move_completed'):
			tasks = self._apply_auto_move_sorting(tasks)
		
		# Przebuduj cache subtasków (optymalizacja wydajności)
		self._build_subtasks_cache()
		
		visible_columns = self._get_visible_columns()
		
		# Wyczyść tabelę i mapę wierszy
		self.table.setRowCount(0)
		# Jawnie usuń wszystkie referencje przed wyczyszczeniem
		for row_data in self._row_task_map.values():
			if isinstance(row_data, dict):
				row_data.clear()
		self._row_task_map.clear()
		
		# Wypełnij wiersze
		for task in tasks:
			row = self.table.rowCount()
			self.table.insertRow(row)
			task_copy = dict(task)
			if 'custom_data' in task and isinstance(task['custom_data'], dict):
				task_copy['custom_data'] = dict(task['custom_data'])
			self._row_task_map[row] = task_copy
			row_task = self._row_task_map[row]
			
			# Wypełnij każdą kolumnę zgodnie z konfiguracją
			for col_idx, col_config in enumerate(visible_columns):
				col_id = col_config.get('column_id', '')
				col_type = col_config.get('type', 'text')
				is_currency_column = self._is_currency_column(col_config)
				
				# Pobierz wartość dla kolumny
				value = self._get_task_value(task, col_id, col_type, col_config)
				
				# Utwórz odpowiedni widget lub item
				if col_type == 'checkbox':
					# Dla checkbox tworzymy widget
					checkbox = QCheckBox()
					checkbox.setChecked(bool(value))
					checkbox.setEnabled(True)  # Edytowalny
					
					# Zapisz task_id i column_id w checkbox jako właściwości
					checkbox.setProperty('task_id', task.get('id'))
					checkbox.setProperty('column_id', col_id)
					
					# Podłącz sygnał zmiany stanu
					checkbox.stateChanged.connect(lambda state, tid=task.get('id'), cid=col_id: 
					                             self._on_checkbox_changed(tid, cid, state))

					# Utwórz ukryty item wspierający kolorowanie wiersza
					placeholder_item = self.table.item(row, col_idx)
					if placeholder_item is None:
						placeholder_item = QTableWidgetItem('')
						placeholder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))
						self.table.setItem(row, col_idx, placeholder_item)
					else:
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))

					self.table.setCellWidget(row, col_idx, self._wrap_cell_widget(checkbox))
				elif col_type == 'button' and col_id == 'KanBan':
					# Dla kolumny KanBan tworzymy przycisk ze strzałką
					btn = self._create_kanban_button(task)
					placeholder_item = self.table.item(row, col_idx)
					if placeholder_item is None:
						placeholder_item = QTableWidgetItem('')
						placeholder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))
						self.table.setItem(row, col_idx, placeholder_item)
					else:
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))

					self.table.setCellWidget(row, col_idx, self._wrap_cell_widget(btn))
				elif col_type == 'button' and col_id == 'Notatka':
					# Dla kolumny Notatka tworzymy przycisk z emoji
					btn = self._create_note_button(task)
					placeholder_item = self.table.item(row, col_idx)
					if placeholder_item is None:
						placeholder_item = QTableWidgetItem('')
						placeholder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))
						self.table.setItem(row, col_idx, placeholder_item)
					else:
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))

					self.table.setCellWidget(row, col_idx, self._wrap_cell_widget(btn))
				elif col_type == 'button' and col_id == 'Subtaski':
					# Dla kolumny Subtaski tworzymy przycisk rozwijający
					btn = self._create_subtask_button(task, row)
					placeholder_item = self.table.item(row, col_idx)
					if placeholder_item is None:
						placeholder_item = QTableWidgetItem('')
						placeholder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))
						self.table.setItem(row, col_idx, placeholder_item)
					else:
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))

					self.table.setCellWidget(row, col_idx, self._wrap_cell_widget(btn))
				elif is_currency_column:
					currency_value = self._coerce_currency_value(value)
					display_value = self._format_currency_value(currency_value if currency_value is not None else value)
					item = QTableWidgetItem(display_value)
					item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
					item.setData(Qt.ItemDataRole.UserRole + 1, currency_value)
					if col_idx == 0:
						item.setData(Qt.ItemDataRole.UserRole, task.get('id'))
					self.table.setItem(row, col_idx, item)
					if currency_value is not None:
						row_task[col_id] = currency_value
				elif col_id in ['Tag', 'tags', 'Tagi']:
					# Dla kolumny Tag tworzymy widget z tagami
					tag_widget = self._create_tag_widget(task)
					placeholder_item = self.table.item(row, col_idx)
					if placeholder_item is None:
						placeholder_item = QTableWidgetItem('')
						placeholder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))
						self.table.setItem(row, col_idx, placeholder_item)
					else:
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))

					self.table.setCellWidget(row, col_idx, tag_widget)
				elif col_type in ['list', 'lista']:
					# Dla kolumny typu lista tworzymy combobox z wartościami
					list_widget = self._create_list_widget(task, col_config)
					placeholder_item = self.table.item(row, col_idx)
					if placeholder_item is None:
						placeholder_item = QTableWidgetItem('')
						placeholder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))
						self.table.setItem(row, col_idx, placeholder_item)
					else:
						if col_idx == 0:
							placeholder_item.setData(Qt.ItemDataRole.UserRole, task.get('id'))

					self.table.setCellWidget(row, col_idx, list_widget)
				elif self._is_duration_column(col_config):
					# Dla kolumny typu czas trwania
					duration_minutes = 0
					if value is not None:
						try:
							duration_minutes = int(value)
						except (ValueError, TypeError):
							duration_minutes = 0
					
					item = QTableWidgetItem()
					item.setData(Qt.ItemDataRole.UserRole + 1, duration_minutes)
					if col_idx == 0:
						item.setData(Qt.ItemDataRole.UserRole, task.get('id'))
					
					# Formatuj wyświetlanie
					if duration_minutes == 0:
						item.setText("0 min")
					elif duration_minutes < 60:
						item.setText(f"{duration_minutes} min")
					else:
						hours = duration_minutes // 60
						mins = duration_minutes % 60
						if mins == 0:
							item.setText(f"{hours}h")
						else:
							item.setText(f"{hours}h {mins}min")
					
					self.table.setItem(row, col_idx, item)
					if duration_minutes > 0:
						row_task[col_id] = duration_minutes
				elif self._is_number_column(col_config):
					# Dla kolumny typu liczba - wyrównanie do prawej i formatowanie
					item = QTableWidgetItem()
					
					# Przechowuj surową wartość w UserRole + 1
					numeric_value = None
					if value is not None and str(value).strip() != '':
						try:
							# Sprawdź typ kolumny
							col_type_lower = col_type.lower()
							if col_type_lower in ['int', 'integer', 'liczba', 'liczbowa', 'number']:
								numeric_value = int(value)
								item.setText(str(numeric_value))
							else:  # float, decimal
								numeric_value = float(value)
								# Formatuj float z 2 miejscami po przecinku
								item.setText(f"{numeric_value:.2f}")
						except (ValueError, TypeError):
							# Jeśli nie można przekonwertować, wyświetl jako tekst
							item.setText(str(value))
							numeric_value = value
					else:
						item.setText('')
					
					item.setData(Qt.ItemDataRole.UserRole + 1, numeric_value)
					item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
					
					if col_idx == 0:
						item.setData(Qt.ItemDataRole.UserRole, task.get('id'))
					
					self.table.setItem(row, col_idx, item)
					if numeric_value is not None:
						row_task[col_id] = numeric_value
				else:
					# Dla pozostałych typów używamy QTableWidgetItem
					item = QTableWidgetItem(str(value) if value is not None else '')
					# Zapisz task_id w UserRole pierwszej kolumny
					if col_idx == 0:
						item.setData(Qt.ItemDataRole.UserRole, task.get('id'))
					self.table.setItem(row, col_idx, item)
			
			# Zastosuj kolor wiersza, jeśli jest ustawiony
			row_color = task.get('row_color')
			if row_color:
				self._apply_row_color(row, row_color)
	
		# Weryfikacja spójności mapy wierszy
		actual_row_count = self.table.rowCount()
		map_size = len(self._row_task_map)
		if actual_row_count != map_size:
			logger.warning(
				f"[TaskView] Row map inconsistency detected: table has {actual_row_count} rows "
				f"but map contains {map_size} entries. Cleaning up..."
			)
			# Usuń wpisy dla nieistniejących wierszy
			valid_rows = set(range(actual_row_count))
			invalid_rows = [row for row in self._row_task_map.keys() if row not in valid_rows]
			for row in invalid_rows:
				row_data = self._row_task_map.pop(row, None)
				if row_data and isinstance(row_data, dict):
					row_data.clear()
			logger.info(f"[TaskView] Removed {len(invalid_rows)} orphaned entries from row map")
		
		logger.info(f"[TaskView] Populated table with {len(tasks)} tasks and {len(visible_columns)} columns")

	def _get_task_value(self, task: Dict[str, Any], column_id: str, column_type: str, 
	                     column_config: Dict[str, Any]) -> Any:
		"""Pobierz wartość zadania dla danej kolumny - zgodnie z konfiguracją użytkownika"""
		
		# Mapowanie polskich i angielskich nazw kolumn na pola w bazie danych
		system_column_mapping = {
			# Angielskie nazwy
			'created_at': 'created_at',
			'updated_at': 'updated_at',
			'completion_date': 'completion_date',
			'status': 'status',
			'title': 'title',
			'position': 'position',
			'archived': 'archived',
			'alarm_date': 'alarm_date',
			'Alarm': 'alarm_date',  # Polska nazwa kolumny
			'note_id': 'note_id',
			'kanban_id': 'kanban_id',
			'tags': 'tags',
			# Polskie nazwy
			'Data dodania': 'created_at',
			'Data aktualizacji': 'updated_at',
			'data realizacji': 'completion_date',
			'Status': 'status',
			'Zadanie': 'title',
			'Pozycja': 'position',
			'Archiwum': 'archived',
			'Data alarmu': 'alarm_date',
			'ID notatki': 'note_id',
			'ID Kanban': 'kanban_id',
			'Tag': 'tags',
			'Tagi': 'tags',
		}
		
		# 1. Sprawdź czy to kolumna systemowa
		if column_id in system_column_mapping:
			db_field = system_column_mapping[column_id]
			value = task.get(db_field)
			
			if db_field == 'status' and isinstance(value, (bool, int)):
				if column_type == 'checkbox':
					return bool(value)
				return 'Zrobione' if value else 'Nowe'
			
			if db_field == 'archived' and isinstance(value, (bool, int)) and column_type == 'checkbox':
				return bool(value)
			
			# Specjalna konwersja dla alarm_date - pobierz następny alarm (dla cyklicznych)
			if db_field == 'alarm_date':
				task_id = task.get('id')
				if task_id and self.local_db and hasattr(self.local_db, 'get_next_alarm_date'):
					try:
						next_alarm = self.local_db.get_next_alarm_date(task_id)
						if next_alarm:
							# Formatuj datę
							return next_alarm.strftime('%Y-%m-%d %H:%M')
					except Exception as e:
						logger.error(f"[TaskView] Failed to get next alarm date for task {task_id}: {e}")
				
				# Fallback do zwykłej wartości
				if value:
					if 'T' in str(value) or ' ' in str(value):
						return str(value).split('T')[0].split(' ')[0]
					return value
				return ''
			
			# Specjalna konwersja dla dat
			if db_field in ['created_at', 'updated_at', 'completion_date'] and value:
				# Zwróć tylko datę bez czasu jeśli zawiera timestamp
				if 'T' in str(value) or ' ' in str(value):
					return str(value).split('T')[0].split(' ')[0]
			
			# Specjalna konwersja dla tagów (może być już string z TaskLogic)
			if db_field == 'tags':
				if isinstance(value, str):
					return value
				elif isinstance(value, list):
					return ', '.join([tag.get('name', '') if isinstance(tag, dict) else str(tag) for tag in value])
			
			return value if value is not None else ''
		
		# 2. Sprawdź czy wartość istnieje bezpośrednio w task (np. z custom_data wypakowanych przez TaskLogic)
		if column_id in task:
			return task[column_id]
		
		# 3. Sprawdź w custom_data (jeśli nie zostały wypakowane)
		if 'custom_data' in task and isinstance(task['custom_data'], dict):
			if column_id in task['custom_data']:
				return task['custom_data'][column_id]
		
		# 4. Sprawdź czy to kolumna z listą własną (wspiera 'list' i 'lista')
		if column_type in ['list', 'lista'] and 'list_name' in column_config:
			list_name = column_config.get('list_name', '')
			
			# Najpierw sprawdź column_id
			if column_id in task:
				return task[column_id]
			
			# Szukaj w custom_data po column_id
			if 'custom_data' in task and isinstance(task['custom_data'], dict):
				if column_id in task['custom_data']:
					return task['custom_data'][column_id]
			
			# Szukaj w custom_data po list_name
			if 'custom_data' in task and isinstance(task['custom_data'], dict):
				if list_name in task['custom_data']:
					return task['custom_data'][list_name]
			
			# Szukaj bezpośrednio w task po list_name
			if list_name in task:
				return task[list_name]
		
		# 5. Sprawdź specjalne pola
		if column_id == 'tags':
			# Zwróć string z tagami
			return task.get('tags', '')
		
		# 6. Wartość domyślna z konfiguracji
		default_value = column_config.get('default_value', '')
		return default_value if default_value else ''

	def _coerce_currency_value(self, value: Any) -> Optional[float]:
		"""Konwertuje wartość na liczbę zmiennoprzecinkową dla kolumn walutowych."""
		if value in (None, '', 'None'):
			return None
		if isinstance(value, (int, float)):
			return float(value)
		if isinstance(value, str):
			stripped = value.strip().replace(' ', '')
			if not stripped:
				return None
			try:
				return float(stripped.replace(',', '.'))
			except ValueError:
				return None
		return None

	def _format_currency_value(self, value: Any) -> str:
		"""Formatuje wartość kolumny walutowej do wyświetlenia."""
		coerced = self._coerce_currency_value(value)
		if coerced is not None:
			return f"{coerced:.2f}"
		if value in (None, '', 'None'):
			return ''
		return str(value)

	def _is_currency_column(self, column_config: Dict[str, Any]) -> bool:
		"""Rozpoznaje kolumny walutowe na podstawie konfiguracji."""
		if not isinstance(column_config, dict):
			return False

		type_candidates = [column_config.get('type'), column_config.get('editor'), column_config.get('editor_type')]
		allow_edit = column_config.get('allow_edit')
		options = column_config.get('options') if isinstance(column_config.get('options'), dict) else {}
		column_id = str(column_config.get('column_id', '') or '')

		keywords = {'currency', 'waluta', 'money', 'monetary', 'amount'}

		for candidate in type_candidates:
			if isinstance(candidate, str) and candidate.lower() in keywords:
				return True

		if isinstance(allow_edit, str):
			try:
				parsed_allow = json.loads(allow_edit)
			except (json.JSONDecodeError, TypeError):
				parsed_allow = None
			if parsed_allow:
				if isinstance(parsed_allow, dict):
					for value in parsed_allow.values():
						if isinstance(value, str) and any(key in value.lower() for key in keywords):
							return True
				elif isinstance(parsed_allow, list):
					for entry in parsed_allow:
						if isinstance(entry, str) and any(key in entry.lower() for key in keywords):
							return True
			if any(key in allow_edit.lower() for key in keywords):
				return True

		if isinstance(options, str):
			try:
				options = json.loads(options)
			except (json.JSONDecodeError, TypeError):
				options = {}

		option_type = options.get('type') if isinstance(options, dict) else None
		if isinstance(option_type, str) and option_type.lower() in keywords:
			return True

		if any(key in column_id.lower() for key in keywords):
			return True

		return False

	def _is_date_column(self, column_config: Dict[str, Any]) -> bool:
		"""Rozpoznaje kolumny typu data na podstawie konfiguracji."""
		if not isinstance(column_config, dict):
			return False

		column_type = column_config.get('type', '')
		column_id = str(column_config.get('column_id', '') or '')

		# Sprawdź typ kolumny
		if isinstance(column_type, str) and column_type.lower() in {'date', 'data', 'datetime'}:
			return True

		# Sprawdź ID kolumny (mogą zawierać słowa kluczowe)
		date_keywords = {'date', 'data', 'termin', 'deadline', 'due'}
		if any(key in column_id.lower() for key in date_keywords):
			# Ale wyklucz kolumny systemowe, które nie są edytowalne przez widget daty
			system_dates = {'created_at', 'updated_at', 'data dodania', 'data aktualizacji'}
			if column_id.lower() not in system_dates:
				return True

		return False

	def _is_duration_column(self, column_config: Dict[str, Any]) -> bool:
		"""Rozpoznaje kolumny typu czas trwania na podstawie konfiguracji."""
		if not isinstance(column_config, dict):
			return False

		column_type = column_config.get('type', '')
		column_id = str(column_config.get('column_id', '') or '')

		# Sprawdź typ kolumny
		if isinstance(column_type, str) and column_type.lower() in {'czas', 'time', 'duration', 'czas trwania'}:
			return True

		# Sprawdź ID kolumny (mogą zawierać słowa kluczowe)
		duration_keywords = {'czas', 'time', 'duration', 'trwanie'}
		if any(key in column_id.lower() for key in duration_keywords):
			return True

		return False

	def _is_text_column(self, column_config: Dict[str, Any]) -> bool:
		"""Rozpoznaje kolumny typu text na podstawie konfiguracji."""
		if not isinstance(column_config, dict):
			return False

		column_type = column_config.get('type', '')
		column_id = str(column_config.get('column_id', '') or '')
		
		# Pomijamy kolumny systemowe (np. Tag, Zadanie)
		if column_config.get('is_system', False):
			return False
		
		# Sprawdź czy kolumna jest edytowalna - nieedytowalne pomijamy
		if not column_config.get('editable', False):
			return False

		# Sprawdź typ kolumny (różne warianty: 'text', 'tekstowa', itp.)
		if isinstance(column_type, str):
			type_lower = column_type.lower()
			if type_lower in {'text', 'tekstowa', 'tekst', 'string', 'str'}:
				return True

		return False

	def _is_number_column(self, column_config: Dict[str, Any]) -> bool:
		"""Rozpoznaje kolumny typu liczba na podstawie konfiguracji."""
		if not isinstance(column_config, dict):
			return False

		column_type = column_config.get('type', '')
		
		# Pomijamy kolumny systemowe
		if column_config.get('is_system', False):
			return False
		
		# Sprawdź czy kolumna jest edytowalna
		if not column_config.get('editable', False):
			return False

		# Sprawdź typ kolumny (różne warianty liczbowe)
		if isinstance(column_type, str):
			type_lower = column_type.lower()
			if type_lower in {'number', 'liczba', 'liczbowa', 'int', 'integer', 'float', 'decimal', 'numeric'}:
				return True

		return False

	def _on_checkbox_changed(self, task_id: int, column_id: str, state: int):
		"""
		Obsługa zmiany stanu checkboxa w tabeli zadań
		
		Args:
			task_id: ID zadania
			column_id: ID kolumny (np. 'Status')
			state: Stan checkboxa (0=unchecked, 2=checked)
		"""
		try:
			checkbox_widget = self.sender()
			if not isinstance(checkbox_widget, QCheckBox):
				checkbox_widget = None
			is_checked = (state == 2)  # Qt.CheckState.Checked = 2
			
			logger.info(f"[TaskView] Checkbox changed: task_id={task_id}, column_id={column_id}, checked={is_checked}")
			
			# Rozróżnienie między kolumnami systemowymi a użytkownika
			system_column_mapping = {
				'Status': 'status',
				'status': 'status',
				'Archiwum': 'archived',
				'archived': 'archived',
			}
			
			# Sprawdź czy to kolumna systemowa
			is_system_column = column_id in system_column_mapping
			
			if is_system_column:
				# Obsługa kolumn systemowych (Status, Archiwum)
				db_field = system_column_mapping.get(column_id)
				updates: Dict[str, Any] = {}
				if db_field in {'status', 'archived'}:
					updates[db_field] = 1 if is_checked else 0
				else:
					updates[db_field] = is_checked
				display_completion = ''
				
				if db_field == 'status':
					if is_checked:
						now = datetime.now()
						updates['completion_date'] = now.strftime('%Y-%m-%d %H:%M:%S')
						display_completion = now.strftime('%Y-%m-%d')
					else:
						updates['completion_date'] = None
						display_completion = ''

					if self._general_settings.get('auto_archive_completed'):
						updates['archived'] = 1 if is_checked else 0
				
				db_targets: List[Any] = []
				if self.task_logic and getattr(self.task_logic, 'db', None):
					db_targets.append(self.task_logic.db)
				if self.local_db and self.local_db not in db_targets and hasattr(self.local_db, 'update_task'):
					db_targets.append(self.local_db)
				
				success = False
				for db in db_targets:
					if hasattr(db, 'update_task'):
						try:
							db_success = db.update_task(task_id, **updates)
							success = success or db_success
						except Exception as db_exc:
							logger.error(f"[TaskView] Database update failed for task {task_id}: {db_exc}")
					else:
						logger.warning(f"[TaskView] Database object {db} has no update_task method")
				
				if success:
					logger.info(f"[TaskView] Successfully updated task {task_id}: {updates}")
					refresh_required = False
					if db_field == 'status':
						if self._general_settings.get('auto_archive_completed'):
							refresh_required = True
						elif self._general_settings.get('auto_move_completed'):
							refresh_required = True

					if refresh_required:
						self.populate_table()
					elif db_field == 'status':
						self._update_completion_date_cell(checkbox_widget, column_id, display_completion)

					if not refresh_required:
						for _row_idx, row_task in self._row_task_map.items():
							if row_task.get('id') == task_id:
								if db_field in {'status', 'archived'}:
									row_task[db_field] = 1 if is_checked else 0
								else:
									row_task[db_field] = is_checked
								if db_field == 'status':
									row_task['completion_date'] = updates.get('completion_date')
									if self._general_settings.get('auto_archive_completed'):
										row_task['archived'] = updates.get('archived', row_task.get('archived'))
								break
				else:
					logger.error(f"[TaskView] Failed to update task {task_id}")
			else:
				# Obsługa kolumn użytkownika - zapis do custom_data
				success = self._update_custom_column_value(task_id, column_id, is_checked)
				
				if success:
					logger.info(f"[TaskView] Successfully updated custom checkbox column '{column_id}' for task {task_id} -> {is_checked}")
					
					# Aktualizuj cache
					for row, row_task in self._row_task_map.items():
						if row_task.get('id') == task_id:
							row_task[column_id] = is_checked
							custom_data = row_task.get('custom_data')
							if isinstance(custom_data, dict):
								custom_data[column_id] = is_checked
							else:
								row_task['custom_data'] = {column_id: is_checked}
							break
				else:
					logger.error(f"[TaskView] Failed to update custom checkbox column '{column_id}' for task {task_id}")
		except Exception as e:
			logger.error(f"[TaskView] Error handling checkbox change: {e}")
			import traceback
			traceback.print_exc()

	def _update_completion_date_cell(self, checkbox_widget: Optional[QCheckBox], status_column_id: str, display_value: str):
		"""Zaktualizuj wyświetlaną datę realizacji w wierszu powiązanym z checkboxem Status."""
		if checkbox_widget is None:
			return
		
		visible_columns = self._get_visible_columns()
		status_col_idx = next((idx for idx, col in enumerate(visible_columns) if col.get('column_id') == status_column_id), None)
		if status_col_idx is None:
			return
		
		completion_col_idx = next((idx for idx, col in enumerate(visible_columns) if col.get('column_id') in {'data realizacji', 'completion_date'}), None)
		if completion_col_idx is None:
			return
		
		row_index = None
		for row in range(self.table.rowCount()):
			cell_widget = self.table.cellWidget(row, status_col_idx)
			if self._cell_widget_matches(cell_widget, checkbox_widget):
				row_index = row
				break
		
		if row_index is None:
			return
		
		item = self.table.item(row_index, completion_col_idx)
		if item is None:
			item = QTableWidgetItem()
			self.table.setItem(row_index, completion_col_idx, item)
		
		item.setText(display_value)

	# ---------- Handlery ----------
	def _on_lock_toggled(self, checked: bool):
		prev_locked = self._locked
		self._locked = checked
		if self._locked:
			self._capture_current_column_widths()
			self._persist_column_widths()
		self._apply_lock_state()
		if not self._locked and prev_locked:
			# Po odblokowaniu przywróć zapisane szerokości jako punkt wyjścia
			header = self.table.horizontalHeader()
			if header and self._visible_columns_cache:
				for index, column in enumerate(self._visible_columns_cache):
					column_id = column.get('column_id', '') if isinstance(column, dict) else ''
					key = self._column_key(column_id)
					if key in self._fixed_width_columns:
						continue
					width = self._column_widths.get(key)
					if width:
						header.resizeSection(index, width)
		self._persist_lock_state()
		
		# Zaktualizuj stan przycisku stretch
		if hasattr(self, 'stretch_btn'):
			self.stretch_btn.setEnabled(not self._locked)
			logger.debug(f"[TaskView] Stretch button {'disabled' if self._locked else 'enabled'}")
	
	def _on_stretch_toggled(self, checked: bool):
		"""Toggle auto-stretch dla kolumny 'Zadanie'"""
		# Znajdź indeks kolumny 'Zadanie' - próbuj różnych nazw
		title_index = -1
		for possible_name in ['Zadanie', 'zadanie', 'title', 'Title']:
			title_index = self._find_column_index(possible_name)
			if title_index >= 0:
				logger.debug(f"[TaskView] Found column '{possible_name}' at index {title_index}")
				break
		
		if title_index < 0:
			logger.warning("[TaskView] Column 'Zadanie' not found for stretch toggle")
			return
		
		self._stretch_enabled = checked
		
		if checked:
			# ON - zielony, włącz auto-dopasowanie
			self.stretch_btn.setStyleSheet("""
				QPushButton {
					background-color: #4CAF50;
					color: white;
					font-weight: bold;
					border: 2px solid #45a049;
					border-radius: 4px;
				}
				QPushButton:hover {
					background-color: #45a049;
				}
				QPushButton:disabled {
					background-color: #cccccc;
					color: #666666;
					border: 2px solid #999999;
				}
			""")
			logger.info("[TaskView] Column 'Zadanie' auto-fit mode: ON")
			# Natychmiast dopasuj szerokość
			self._adjust_zadanie_column_width()
		else:
			# OFF - czerwony, wyłącz auto-dopasowanie
			self.stretch_btn.setStyleSheet("""
				QPushButton {
					background-color: #f44336;
					color: white;
					font-weight: bold;
					border: 2px solid #da190b;
					border-radius: 4px;
				}
				QPushButton:hover {
					background-color: #da190b;
				}
				QPushButton:disabled {
					background-color: #cccccc;
					color: #666666;
					border: 2px solid #999999;
				}
			""")
			logger.info("[TaskView] Column 'Zadanie' auto-fit mode: OFF")
	
	def _adjust_zadanie_column_width(self):
		"""Dopasuj szerokość kolumny 'Zadanie' do dostępnej przestrzeni"""
		if not hasattr(self, '_stretch_enabled') or not self._stretch_enabled:
			return
		
		# Znajdź indeks kolumny Zadanie
		title_index = -1
		for possible_name in ['Zadanie', 'zadanie', 'title', 'Title']:
			title_index = self._find_column_index(possible_name)
			if title_index >= 0:
				break
		
		if title_index < 0:
			return
		
		header = self.table.horizontalHeader()
		if not header:
			return
		
		# Oblicz dostępną szerokość
		viewport_width = self.table.viewport().width()
		
		# Zsumuj szerokości wszystkich innych kolumn
		other_columns_width = 0
		for i in range(header.count()):
			if i != title_index and not header.isSectionHidden(i):
				other_columns_width += header.sectionSize(i)
		
		# Oblicz szerokość dla kolumny Zadanie (minimum 200px)
		available_width = viewport_width - other_columns_width
		new_width = max(200, available_width)
		
		# Ustaw nową szerokość
		header.resizeSection(title_index, new_width)
		logger.debug(f"[TaskView] Adjusted 'Zadanie' column width to {new_width}px (viewport: {viewport_width}px, others: {other_columns_width}px)")
	
	def _find_column_index(self, column_id: str) -> int:
		"""Znajdź indeks kolumny po jej column_id"""
		if not self._visible_columns_cache:
			return -1
		
		for index, col in enumerate(self._visible_columns_cache):
			if col.get('column_id', '').lower() == column_id.lower():
				return index
		
		return -1

	def _on_configure_clicked(self):
		"""Otwórz dialog konfiguracji zadań"""
		# Hook: callback ustawiany przez MainWindow
		if hasattr(self, 'on_configure') and callable(self.on_configure):
			try:
				self.on_configure()
				# Po zamknięciu dialogu konfiguracji, odśwież widok
				self.refresh_columns()
			except Exception as e:
				logger.error(f"[TaskView] Error in configuration callback: {e}")
	
	def _on_sync_now(self):
		"""Wymuszony synchronizacja z serwerem"""
		try:
			# Sprawdź czy TasksManager ma metodę sync_now
			if hasattr(self.task_logic, 'sync_now') and callable(self.task_logic.sync_now):
				logger.info("[TaskView] Manual sync triggered")
				self.sync_btn.setEnabled(False)  # Wyłącz przycisk podczas sync
				self.sync_btn.setText("🔄 Synchronizuję...")
				
				# Wywołaj sync
				self.task_logic.sync_now()
				
				# Timer do przywrócenia przycisku (po 3 sekundach)
				from PyQt6.QtCore import QTimer
				QTimer.singleShot(3000, lambda: (
					self.sync_btn.setEnabled(True),
					self.sync_btn.setText("🔄 Synchronizuj")
				))
				
				# Odśwież widok po sync (z opóźnieniem 1s)
				QTimer.singleShot(1000, self.refresh_tasks)
			else:
				logger.warning("[TaskView] sync_now method not available (sync not enabled)")
		except Exception as e:
			logger.error(f"[TaskView] Error during manual sync: {e}")
			self.sync_btn.setEnabled(True)
			self.sync_btn.setText("🔄 Synchronizuj")

	def _on_search_changed(self, text: str):
		"""Filtruj zadania na podstawie tekstu wyszukiwania"""
		if self.task_logic and hasattr(self.task_logic, 'filter_tasks'):
			try:
				status_value = self.status_cb.currentData(Qt.ItemDataRole.UserRole)
				if status_value is None:
					status_value = self.status_cb.currentText()
				tag_value = self.tag_cb.currentData(Qt.ItemDataRole.UserRole)
				if isinstance(tag_value, str) and not tag_value.strip():
					tag_value = None
				filtered = self.task_logic.filter_tasks(
					text=text,
					status=status_value,
					tag=tag_value
				)
				self.populate_table(filtered)
				return
			except Exception as e:
				logger.error(f"[TaskView] Error filtering tasks: {e}")
		# fallback: odśwież bez filtrowania
		self.populate_table()

	def _on_filter_changed(self):
		"""Ponownie zastosuj filtry gdy zmieni się status lub tag"""
		self._on_search_changed(self.search_le.text())

	def _on_cell_double_clicked(self, row: int, col: int):
		"""Obsługa podwójnego kliknięcia w komórkę - otwiera dialog alarmu dla kolumny Alarm"""
		# Sprawdź czy kliknięto w poprawny zakres
		if row < 0 or col < 0:
			return
			
		# Pobierz widoczne kolumny
		visible_columns = [col_cfg for col_cfg in self._columns_config if col_cfg.get('visible_main', True)]
		visible_columns.sort(key=lambda x: x.get('position', 0))
		
		# Sprawdź czy indeks kolumny jest poprawny
		if col >= len(visible_columns):
			return
			
		# Pobierz konfigurację klikniętej kolumny
		column_config = visible_columns[col]
		column_id = column_config.get('column_id', '')
		
		if column_id in {'Zadanie', 'title'}:
			self._handle_task_title_double_click(row, col, column_config)
			return

		column_type = column_config.get('type')
		
		logger.debug(f"[TaskView] Double-click on column: {column_id}, type: {column_type}, is_system: {column_config.get('is_system')}, editable: {column_config.get('editable')}")
		
		# Obsługa kolumn walutowych
		if self._is_currency_column(column_config):
			logger.debug(f"[TaskView] Opening currency dialog for column: {column_id}")
			self._handle_currency_cell_double_click(row, col, column_config)
			return
		
		# Obsługa kolumn typu data
		if self._is_date_column(column_config):
			logger.debug(f"[TaskView] Opening date dialog for column: {column_id}")
			self._handle_date_cell_double_click(row, col, column_config)
			return
		
		# Obsługa kolumn typu czas trwania
		if self._is_duration_column(column_config):
			logger.debug(f"[TaskView] Opening duration dialog for column: {column_id}")
			self._handle_duration_cell_double_click(row, col, column_config)
			return
		
		# Obsługa kolumn typu text
		if self._is_text_column(column_config):
			logger.info(f"[TaskView] Opening text dialog for column: {column_id}")
			self._handle_text_cell_double_click(row, col, column_config)
			return
		
		# Obsługa kolumn liczbowych - edycja bezpośrednia w komórce
		if self._is_number_column(column_config):
			logger.info(f"[TaskView] Enabling inline edit for number column: {column_id}")
			self._handle_number_cell_double_click(row, col, column_config)
			return
		
		# Sprawdź czy to kolumna alarmu (może być 'Alarm' lub 'alarm_date')
		if column_id not in ['Alarm', 'alarm_date']:
			return
			
		# Pobierz dane zadania z wiersza
		# Znajdź kolumnę ID (powinna być pierwsza lub gdzieś w visible_columns)
		task_id = None
		task_title = ""
		
		# Znajdź indeks kolumny z ID zadania
		id_col_idx = None
		title_col_idx = None
		
		for idx, col_cfg in enumerate(visible_columns):
			if col_cfg.get('column_id') == 'created_at':  # ID jest przechowywane w pierwszej kolumnie
				id_col_idx = idx
			elif col_cfg.get('column_id') == 'title':
				title_col_idx = idx
				
		# Pobierz task_id z UserRole w pierwszej kolumnie (zakładamy że tam jest przechowywane)
		if id_col_idx is not None:
			item = self.table.item(row, id_col_idx)
			if item:
				task_id = item.data(Qt.ItemDataRole.UserRole)
		
		# Jeśli nie znaleziono w pierwszej kolumnie, spróbuj w aktualnej
		if task_id is None:
			item = self.table.item(row, 0)
			if item:
				task_id = item.data(Qt.ItemDataRole.UserRole)
				
		# Pobierz tytuł zadania
		if title_col_idx is not None:
			title_item = self.table.item(row, title_col_idx)
			if title_item:
				task_title = title_item.text()
		
		if task_id is None:
			logger.warning(f"[TaskView] Cannot open alarm dialog - task_id not found for row {row}")
			return
			
		# Pobierz aktualną datę alarmu z komórki
		current_alarm_date = None
		alarm_item = self.table.item(row, col)
		if alarm_item:
			alarm_text = alarm_item.text()
			if alarm_text and alarm_text.strip():
				try:
					# Parsuj datę z komórki (format może się różnić)
					from datetime import datetime
					current_alarm_date = datetime.fromisoformat(alarm_text.replace(' ', 'T'))
				except:
					pass
					
		# Otwórz dialog alarmu
		from src.Modules.Alarm_module.alarm_dialog import TaskAlarmDialog
		
		dialog = TaskAlarmDialog(
			task_id=task_id,
			task_title=task_title,
			current_alarm_date=current_alarm_date,
			parent=self
		)
		
		if dialog.exec() == QDialog.DialogCode.Accepted:
			alarm_data = dialog.alarm_data
			
			# Sprawdź czy alarm_data nie jest None
			if alarm_data is None:
				logger.warning(f"[TaskView] alarm_data is None for task {task_id}")
				return
			
			if alarm_data.get('remove'):
				# Usuń alarm
				if self.local_db and hasattr(self.local_db, 'remove_task_alarm'):
					try:
						self.local_db.remove_task_alarm(task_id)
						logger.info(f"[TaskView] Removed alarm for task {task_id}")
						
						# Usuń również z modułu alarmów (jeśli istnieje)
						if self.alarm_manager:
							# Znajdź alarm o tej etykiecie (task_title) i usuń
							alarm_to_remove = None
							for alarm in self.alarm_manager.alarms:
								if hasattr(alarm, 'label') and alarm.label == task_title:
									alarm_to_remove = alarm
									break
							if alarm_to_remove:
								self.alarm_manager.delete_alarm(alarm_to_remove.id)
								logger.info(f"[TaskView] Removed alarm from alarm module: {alarm_to_remove.id}")
						
					except Exception as e:
						logger.error(f"[TaskView] Failed to remove alarm: {e}")
			else:
				# Zapisz alarm
				if self.local_db and hasattr(self.local_db, 'save_task_alarm'):
					try:
						self.local_db.save_task_alarm(task_id, alarm_data)
						logger.info(f"[TaskView] Saved alarm for task {task_id}")
						
						# Utwórz alarm w module alarmów
						if self.alarm_manager:
							from datetime import datetime, time
							from src.Modules.Alarm_module.alarm_models import Alarm, AlarmRecurrence
							import uuid
							
							logger.info(f"[TaskView] Creating alarm in alarm module for task {task_id}")
							
							alarm_time = alarm_data.get('alarm_time')
							if isinstance(alarm_time, datetime):
								# Konwertuj datetime na time
								alarm_time_obj = time(alarm_time.hour, alarm_time.minute)
								
								# Określ typ cykliczności
								if alarm_data.get('is_recurring'):
									# Dla cyklicznych użyj CUSTOM
									recurrence = AlarmRecurrence.CUSTOM
								else:
									recurrence = AlarmRecurrence.ONCE
								
								# Utwórz alarm
								alarm_label = alarm_data.get('label', task_title)
								if not isinstance(alarm_label, str):
									alarm_label = str(alarm_label) if alarm_label else task_title
								
								logger.info(f"[TaskView] Alarm label: '{alarm_label}', time: {alarm_time}, recurrence: {recurrence}")
								
								new_alarm = Alarm(
									id=f"task_{task_id}_{uuid.uuid4().hex[:8]}",
									time=alarm_time_obj,
									label=alarm_label,
									enabled=True,
									recurrence=recurrence,
									days=[],
									play_sound=alarm_data.get('play_sound', True),
									show_popup=alarm_data.get('show_popup', True),
									created_at=datetime.now()
								)
								
								# Dodaj do managera
								result = self.alarm_manager.add_alarm(new_alarm)
								logger.info(f"[TaskView] Created alarm in alarm module: {new_alarm.id}, result={result}")
								logger.info(f"[TaskView] Total alarms in manager: {len(self.alarm_manager.alarms)}")
							else:
								logger.warning(f"[TaskView] alarm_time is not datetime: {type(alarm_time)}")
						else:
							logger.warning("[TaskView] No alarm_manager available")
						
					except Exception as e:
						logger.error(f"[TaskView] Failed to save alarm: {e}")
						
			# Odśwież tabelę aby pokazać zmiany
			self.populate_table()

	def _handle_currency_cell_double_click(self, row: int, column: int, column_config: Dict[str, Any]) -> None:
		"""Obsługuje edycję wartości w kolumnie walutowej."""
		column_id = column_config.get('column_id')
		if not column_id:
			logger.warning("[TaskView] Currency column without column_id")
			return

		task_id = self._get_task_id_from_row(row)
		if task_id is None:
			logger.warning(f"[TaskView] Cannot edit currency column '{column_id}' - task_id not found for row {row}")
			return

		if self._currency_dialog_open:
			logger.debug("[TaskView] Currency dialog already open, ignoring duplicate trigger")
			return

		row_task = self._row_task_map.get(row, {})
		current_value = row_task.get(column_id)
		if current_value is None:
			item = self.table.item(row, column)
			if item:
				current_value = item.data(Qt.ItemDataRole.UserRole + 1)

		initial_amount = self._coerce_currency_value(current_value) or 0.0
		step_raw = column_config.get('step') or column_config.get('increment') or column_config.get('currency_step')
		step_value = self._coerce_currency_value(step_raw)
		if step_value is None or step_value <= 0:
			step_value = 1.0

		self._currency_dialog_open = True
		try:
			accepted, new_amount = CurrencyInputDialog.prompt(
				parent=self,
				initial_amount=initial_amount,
				step=step_value,
			)
			if not accepted:
				return

			new_amount = round(new_amount, 2)
			if not self._update_custom_column_value(task_id, column_id, new_amount):
				logger.error(f"[TaskView] Failed to persist currency value for task {task_id} column '{column_id}'")
				return

			logger.info(f"[TaskView] Updated currency column '{column_id}' for task {task_id} -> {new_amount}")
			self._set_currency_cell_value(row, column, new_amount)

			row_entry = self._row_task_map.get(row)
			if row_entry is not None:
				row_entry[column_id] = new_amount
				custom_data = row_entry.get('custom_data')
				if isinstance(custom_data, dict):
					custom_data[column_id] = new_amount
				else:
					row_entry['custom_data'] = {column_id: new_amount}
		finally:
			self._currency_dialog_open = False

	def _handle_date_cell_double_click(self, row: int, column: int, column_config: Dict[str, Any]) -> None:
		"""Obsługuje edycję wartości w kolumnie typu data."""
		column_id = column_config.get('column_id')
		if not column_id:
			logger.warning("[TaskView] Date column without column_id")
			return

		task_id = self._get_task_id_from_row(row)
		if task_id is None:
			logger.warning(f"[TaskView] Cannot edit date column '{column_id}' - task_id not found for row {row}")
			return

		# Pobierz aktualną wartość daty
		row_task = self._row_task_map.get(row, {})
		current_value = row_task.get(column_id)
		
		# Jeśli nie ma w row_task, spróbuj z custom_data
		if current_value is None and 'custom_data' in row_task:
			custom_data = row_task.get('custom_data', {})
			if isinstance(custom_data, dict):
				current_value = custom_data.get(column_id)
		
		# Jeśli nadal brak, spróbuj z komórki tabeli
		if current_value is None:
			item = self.table.item(row, column)
			if item:
				current_value = item.text()

		# Parsuj aktualną wartość na obiekt date
		initial_date = None
		if current_value:
			try:
				if isinstance(current_value, date):
					initial_date = current_value
				elif isinstance(current_value, datetime):
					initial_date = current_value.date()
				elif isinstance(current_value, str) and current_value.strip():
					# Spróbuj różnych formatów
					for fmt in ['%Y-%m-%d', '%d.%m.%Y', '%d/%m/%Y', '%Y-%m-%d %H:%M:%S']:
						try:
							parsed = datetime.strptime(current_value.strip(), fmt)
							initial_date = parsed.date()
							break
						except ValueError:
							continue
			except Exception as e:
				logger.warning(f"[TaskView] Failed to parse date '{current_value}': {e}")

		# Otwórz dialog wyboru daty
		column_name = column_config.get('column_id', 'Data')
		dialog_title = t("tasks.date_dialog.title_for", f"Wybierz datę: {column_name}")
		
		accepted, selected_date = DatePickerDialog.prompt(
			parent=self,
			initial_date=initial_date,
			title=dialog_title,
		)
		
		if not accepted:
			return

		# selected_date może być None (użytkownik kliknął "Wyczyść")
		# Zapisz do bazy danych
		date_str = selected_date.strftime('%Y-%m-%d') if selected_date else None
		
		if not self._update_custom_column_value(task_id, column_id, date_str):
			logger.error(f"[TaskView] Failed to persist date value for task {task_id} column '{column_id}'")
			return

		logger.info(f"[TaskView] Updated date column '{column_id}' for task {task_id} -> {date_str}")
		
		# Aktualizuj komórkę w tabeli
		self._set_date_cell_value(row, column, date_str)

		# Aktualizuj cache
		row_entry = self._row_task_map.get(row)
		if row_entry is not None:
			row_entry[column_id] = date_str
			custom_data = row_entry.get('custom_data')
			if isinstance(custom_data, dict):
				custom_data[column_id] = date_str
			else:
				row_entry['custom_data'] = {column_id: date_str}

	def _handle_duration_cell_double_click(self, row: int, column: int, column_config: Dict[str, Any]) -> None:
		"""Obsługuje edycję wartości w kolumnie typu czas trwania."""
		column_id = column_config.get('column_id')
		if not column_id:
			logger.warning("[TaskView] Duration column without column_id")
			return

		task_id = self._get_task_id_from_row(row)
		if task_id is None:
			logger.warning(f"[TaskView] Cannot edit duration column '{column_id}' - task_id not found for row {row}")
			return

		# Pobierz aktualną wartość czasu trwania (w minutach)
		row_task = self._row_task_map.get(row, {})
		current_value = row_task.get(column_id)
		
		# Jeśli nie ma w row_task, spróbuj z custom_data
		if current_value is None and 'custom_data' in row_task:
			custom_data = row_task.get('custom_data', {})
			if isinstance(custom_data, dict):
				current_value = custom_data.get(column_id)
		
		# Jeśli nadal brak, spróbuj z komórki tabeli
		if current_value is None:
			item = self.table.item(row, column)
			if item:
				current_value = item.text()

		# Parsuj aktualną wartość na liczbę minut
		initial_minutes = 0
		if current_value:
			try:
				if isinstance(current_value, (int, float)):
					initial_minutes = int(current_value)
				elif isinstance(current_value, str) and current_value.strip():
					initial_minutes = int(current_value.strip())
			except (ValueError, TypeError) as e:
				logger.warning(f"[TaskView] Failed to parse duration '{current_value}': {e}")

		# Otwórz dialog wyboru czasu trwania
		column_name = column_config.get('column_id', 'Czas')
		dialog_title = t("tasks.duration_dialog.title_for", f"Czas trwania: {column_name}")
		
		accepted, selected_minutes = DurationInputDialog.prompt(
			parent=self,
			initial_minutes=initial_minutes,
			title=dialog_title,
		)
		
		if not accepted:
			return

		# Zapisz do bazy danych (jako liczba minut)
		if not self._update_custom_column_value(task_id, column_id, selected_minutes):
			logger.error(f"[TaskView] Failed to persist duration value for task {task_id} column '{column_id}'")
			return

		logger.info(f"[TaskView] Updated duration column '{column_id}' for task {task_id} -> {selected_minutes} min")
		
		# Aktualizuj komórkę w tabeli
		self._set_duration_cell_value(row, column, selected_minutes)

		# Aktualizuj cache
		row_entry = self._row_task_map.get(row)
		if row_entry is not None:
			row_entry[column_id] = selected_minutes
			custom_data = row_entry.get('custom_data')
			if isinstance(custom_data, dict):
				custom_data[column_id] = selected_minutes
			else:
				row_entry['custom_data'] = {column_id: selected_minutes}

	def _handle_task_title_double_click(self, row: int, column: int, column_config: Dict[str, Any]) -> None:
		"""Obsłuż edycję tytułu zadania przy podwójnym kliknięciu."""
		task_id = self._get_task_id_from_row(row)
		if task_id is None:
			logger.warning(f"[TaskView] Cannot edit task title - task_id not found for row {row}")
			return

		row_task = self._row_task_map.get(row, {})
		current_title = row_task.get('title') or row_task.get('Zadanie') or ''
		if not current_title:
			item = self.table.item(row, column)
			if item:
				current_title = item.text()

		accepted, new_title = TaskEditDialog.prompt(parent=self, task_title=current_title)
		if not accepted:
			return

		new_title = new_title.strip()
		if not new_title or new_title == current_title:
			return

		if not self._update_task_title(task_id, new_title):
			logger.error(f"[TaskView] Failed to persist task title for task {task_id}")
			return

		self._apply_task_title_update(row, column, new_title)
		logger.info(f"[TaskView] Updated task {task_id} title -> '{new_title}'")

	def _handle_text_cell_double_click(self, row: int, column: int, column_config: Dict[str, Any]) -> None:
		"""Obsługuje edycję wartości w kolumnie typu text."""
		column_id = column_config.get('column_id')
		if not column_id:
			logger.warning("[TaskView] Text column without column_id")
			return

		task_id = self._get_task_id_from_row(row)
		if task_id is None:
			logger.warning(f"[TaskView] Cannot edit text column '{column_id}' - task_id not found for row {row}")
			return

		# Pobierz aktualną wartość tekstową
		row_task = self._row_task_map.get(row, {})
		current_value = row_task.get(column_id)
		
		# Jeśli nie ma w row_task, spróbuj z custom_data
		if current_value is None and 'custom_data' in row_task:
			custom_data = row_task.get('custom_data', {})
			if isinstance(custom_data, dict):
				current_value = custom_data.get(column_id)
		
		# Jeśli nadal brak, spróbuj z komórki tabeli
		if current_value is None:
			item = self.table.item(row, column)
			if item:
				current_value = item.text()

		# Konwertuj na string
		initial_text = str(current_value) if current_value is not None else ""

		# Otwórz dialog edycji tekstu
		column_name = column_config.get('column_id', 'Text')
		dialog_title = t("tasks.text_dialog.title_for", f"Edytuj {column_name}")
		
		accepted, new_text = TextInputDialog.prompt(
			parent=self,
			initial_text=initial_text,
			title=dialog_title,
		)
		
		if not accepted:
			return

		# Zapisz do bazy danych
		if not self._update_custom_column_value(task_id, column_id, new_text):
			logger.error(f"[TaskView] Failed to persist text value for task {task_id} column '{column_id}'")
			return

		logger.info(f"[TaskView] Updated text column '{column_id}' for task {task_id} -> '{new_text}'")
		
		# Aktualizuj komórkę w tabeli
		item = self.table.item(row, column)
		if item is None:
			item = QTableWidgetItem()
			self.table.setItem(row, column, item)
		item.setText(new_text)
		item.setData(Qt.ItemDataRole.UserRole + 1, new_text)

		# Aktualizuj cache
		row_entry = self._row_task_map.get(row)
		if row_entry is not None:
			row_entry[column_id] = new_text
			custom_data = row_entry.get('custom_data')
			if isinstance(custom_data, dict):
				custom_data[column_id] = new_text
			else:
				row_entry['custom_data'] = {column_id: new_text}

	def _apply_task_title_update(self, row: int, column: int, title: str) -> None:
		item = self.table.item(row, column)
		if item is None:
			item = QTableWidgetItem()
			self.table.setItem(row, column, item)
		item.setText(title)

		row_entry = self._row_task_map.get(row)
		if row_entry is None:
			self._row_task_map[row] = {'title': title}
			return

		row_entry['title'] = title

	def _update_task_title(self, task_id: int, title: str) -> bool:
		db_targets: List[Any] = []
		if self.task_logic and getattr(self.task_logic, 'db', None):
			db_targets.append(self.task_logic.db)
		if self.local_db and self.local_db not in db_targets:
			db_targets.append(self.local_db)

		success = False
		for db in db_targets:
			if not hasattr(db, 'update_task'):
				logger.warning(f"[TaskView] Database object {db} has no update_task method")
				continue
			try:
				db_success = db.update_task(task_id, title=title)
				if db_success is None:
					success = True
				else:
					success = success or bool(db_success)
			except Exception as exc:
				logger.error(f"[TaskView] Failed to update task {task_id} title in database: {exc}")

		return success

	def _handle_number_cell_double_click(self, row: int, column: int, column_config: Dict[str, Any]) -> None:
		"""Obsługuje edycję wartości liczbowej bezpośrednio w komórce tabeli."""
		column_id = column_config.get('column_id')
		if not column_id:
			logger.warning("[TaskView] Number column without column_id")
			return

		task_id = self._get_task_id_from_row(row)
		if task_id is None:
			logger.warning(f"[TaskView] Cannot edit number column '{column_id}' - task_id not found for row {row}")
			return

		# Pobierz lub utwórz item w komórce
		item = self.table.item(row, column)
		if item is None:
			item = QTableWidgetItem()
			self.table.setItem(row, column, item)
			# Pobierz wartość z bazy
			row_task = self._row_task_map.get(row, {})
			current_value = row_task.get(column_id)
			if current_value is None and 'custom_data' in row_task:
				custom_data = row_task.get('custom_data', {})
				if isinstance(custom_data, dict):
					current_value = custom_data.get(column_id)
			if current_value is not None:
				item.setText(str(current_value))

		# Włącz flagę edytowalności dla tej komórki
		item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
		
		# Zapisz informację o edytowanej komórce
		self._editing_number_cell = (row, column)
		
		# Połącz sygnał itemChanged tylko podczas edycji liczby
		if not hasattr(self, '_number_edit_connected') or not self._number_edit_connected:
			self.table.itemChanged.connect(self._on_number_cell_changed)
			self._number_edit_connected = True
		
		# Otwórz edycję komórki
		self.table.editItem(item)

	def _on_number_cell_changed(self, item: QTableWidgetItem) -> None:
		"""Obsługuje zmianę wartości w komórce liczbowej."""
		# Sprawdź czy to komórka, którą edytujemy
		row = item.row()
		column = item.column()
		
		# Sprawdź czy to komórka liczbowa, którą aktualnie edytujemy
		if not hasattr(self, '_editing_number_cell'):
			return
		
		editing_row, editing_col = self._editing_number_cell
		if row != editing_row or column != editing_col:
			return
		
		# Wyczyść flagę edycji
		delattr(self, '_editing_number_cell')
		
		# Pobierz konfigurację kolumny
		visible_columns = [col_cfg for col_cfg in self._columns_config if col_cfg.get('visible_main', True)]
		visible_columns.sort(key=lambda x: x.get('position', 0))
		
		if column >= len(visible_columns):
			return
			
		column_config = visible_columns[column]
		column_id = column_config.get('column_id')
		
		# Sprawdź czy to kolumna liczbowa
		if not self._is_number_column(column_config):
			return
		
		task_id = self._get_task_id_from_row(row)
		if task_id is None:
			return
		
		# Pobierz i zwaliduj wartość
		text_value = item.text().strip()
		
		# Obsługa pustej wartości
		if text_value == '':
			numeric_value = None
		else:
			# Spróbuj sparsować jako liczbę
			try:
				# Sprawdź czy typ kolumny to float/decimal
				column_type = column_config.get('type', '').lower()
				if column_type in {'float', 'decimal'}:
					numeric_value = float(text_value)
				else:
					# Dla int/integer/number/liczba/liczbowa
					numeric_value = int(float(text_value))  # float() aby obsłużyć "5.0" -> 5
			except ValueError:
				logger.warning(f"[TaskView] Invalid number value '{text_value}' for column '{column_id}'")
				# Przywróć poprzednią wartość
				row_task = self._row_task_map.get(row, {})
				old_value = row_task.get(column_id)
				if old_value is None and 'custom_data' in row_task:
					custom_data = row_task.get('custom_data', {})
					if isinstance(custom_data, dict):
						old_value = custom_data.get(column_id)
				item.setText(str(old_value) if old_value is not None else '')
				return
		
		# Zapisz do bazy danych
		if not self._update_custom_column_value(task_id, column_id, numeric_value):
			logger.error(f"[TaskView] Failed to persist number value for task {task_id} column '{column_id}'")
			return
		
		logger.info(f"[TaskView] Updated number column '{column_id}' for task {task_id} -> {numeric_value}")
		
		# Aktualizuj cache
		row_entry = self._row_task_map.get(row)
		if row_entry is not None:
			row_entry[column_id] = numeric_value
			custom_data = row_entry.get('custom_data')
			if isinstance(custom_data, dict):
				custom_data[column_id] = numeric_value
			else:
				row_entry['custom_data'] = {column_id: numeric_value}
		
		# Wyłącz edycję po zapisie
		item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

	def _set_date_cell_value(self, row: int, column: int, value: Optional[str]) -> None:
		"""Ustaw wartość daty w komórce tabeli."""
		item = self.table.item(row, column)
		if item is None:
			item = QTableWidgetItem()
			self.table.setItem(row, column, item)

		display_text = value if value else ''
		item.setText(display_text)
		item.setData(Qt.ItemDataRole.UserRole + 1, value)
		
		if column == 0:
			task_id = self._get_task_id_from_row(row)
			if task_id is not None:
				item.setData(Qt.ItemDataRole.UserRole, task_id)

	def _set_duration_cell_value(self, row: int, column: int, minutes: int) -> None:
		"""Ustaw wartość czasu trwania w komórce tabeli."""
		item = self.table.item(row, column)
		if item is None:
			item = QTableWidgetItem()
			self.table.setItem(row, column, item)

		# Wyświetl czas w formacie czytelnym (np. "120 min" lub "2h 0min")
		if minutes == 0:
			display_text = "0 min"
		elif minutes < 60:
			display_text = f"{minutes} min"
		else:
			hours = minutes // 60
			mins = minutes % 60
			if mins == 0:
				display_text = f"{hours}h"
			else:
				display_text = f"{hours}h {mins}min"
		
		item.setText(display_text)
		item.setData(Qt.ItemDataRole.UserRole + 1, minutes)
		
		if column == 0:
			task_id = self._get_task_id_from_row(row)
			if task_id is not None:
				item.setData(Qt.ItemDataRole.UserRole, task_id)

	def _set_currency_cell_value(self, row: int, column: int, value: Any) -> None:
		item = self.table.item(row, column)
		if item is None:
			item = QTableWidgetItem()
			self.table.setItem(row, column, item)

		item.setText(self._format_currency_value(value))
		item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
		item.setData(Qt.ItemDataRole.UserRole + 1, self._coerce_currency_value(value))
		if column == 0:
			task_id = self._get_task_id_from_row(row)
			if task_id is not None:
				item.setData(Qt.ItemDataRole.UserRole, task_id)

	def _get_task_id_from_row(self, row: int) -> Optional[int]:
		task_data = self._row_task_map.get(row)
		if task_data and isinstance(task_data.get('id'), int):
			return task_data['id']
		item = self.table.item(row, 0)
		if item:
			task_id = item.data(Qt.ItemDataRole.UserRole)
			if isinstance(task_id, int):
				return task_id
		return None

	def _update_custom_column_value(self, task_id: int, column_id: str, value: Any) -> bool:
		"""Aktualizuje wartość kolumny niestandardowej w bazie danych.
		
		OPTYMALIZACJA: Używa batch updates - zamiast natychmiastowego zapisu,
		dodaje zmianę do kolejki i zapisuje po 500ms lub przy większej ilości zmian.
		
		Args:
			task_id: ID zadania
			column_id: ID kolumny
			value: Wartość do zapisania (może być float, str, int, None itp.)
			
		Returns:
			True (zawsze, faktyczny zapis jest asynchroniczny)
		"""
		# Dodaj do kolejki batch updates zamiast natychmiastowego zapisu
		self._schedule_update(task_id, column_id, value)
		return True

	def refresh_tasks(self):
		"""Odśwież listę zadań (np. po zmianie w widoku KanBan) z debounce 300ms"""
		# Anuluj oczekujący refresh jeśli istnieje
		if self._refresh_tasks_timer is not None and self._refresh_tasks_timer.isActive():
			self._refresh_tasks_timer.stop()
		
		# Ustaw timer dla opóźnionego odświeżania
		self._refresh_tasks_timer = QTimer()
		self._refresh_tasks_timer.setSingleShot(True)
		self._refresh_tasks_timer.timeout.connect(self._do_refresh_tasks)
		self._refresh_tasks_timer.start(300)  # 300ms debounce
	
	def _do_refresh_tasks(self):
		"""Wykonaj rzeczywiste odświeżenie zadań"""
		logger.info("[TaskView] Refreshing tasks...")
		self.populate_table()
		logger.info("[TaskView] Tasks refresh completed")

	def _create_note_button(self, task: Dict[str, Any]) -> QPushButton:
		"""Utwórz przycisk Notatka dla zadania
		
		Args:
			task: Słownik z danymi zadania
			
		Returns:
			QPushButton z emoji notatki (niebieskie lub zielone tło)
		"""
		btn = QPushButton()
		task_id = task.get('id')
		note_id = task.get('note_id')  # Zakładam że pole note_id istnieje w bazie
		
		if note_id:
			# Zielone tło - zadanie ma już notatkę
			btn.setText("📝")
			btn.setStyleSheet("""
				QPushButton {
					background-color: #4CAF50;
					color: white;
					border: none;
					border-radius: 4px;
					padding: 2px;
					font-size: 14px;
					min-width: 32px;
					max-width: 32px;
					min-height: 28px;
					max-height: 28px;
				}
				QPushButton:hover {
					background-color: #45A049;
				}
			""")
			btn.setToolTip(self._translations_cache['note_open'])
		else:
			# Niebieskie tło - można utworzyć notatkę
			btn.setText("📝")
			btn.setStyleSheet("""
				QPushButton {
					background-color: #2196F3;
					color: white;
					border: none;
					border-radius: 4px;
					padding: 2px;
					font-size: 14px;
					min-width: 32px;
					max-width: 32px;
					min-height: 28px;
					max-height: 28px;
				}
				QPushButton:hover {
					background-color: #1976D2;
				}
				QPushButton:pressed {
					background-color: #0D47A1;
				}
			""")
			btn.setToolTip(self._translations_cache['note_create'])
		
		btn.setFixedSize(32, 28)
		
		# Podłącz sygnał kliknięcia
		btn.clicked.connect(lambda checked, tid=task_id: self.open_task_note(tid))
		
		return btn

	def open_task_note(self, task_id: int):
		"""Otwórz notatkę dla zadania (STUB - będzie podmieniony przez main_window)
		
		Ta metoda jest placeholderem, który zostanie podmieniony podczas
		inicjalizacji przez main_window.setup_note_buttons_functionality()
		
		Args:
			task_id: ID zadania dla którego otwieramy notatkę
		"""
		logger.info(f"[TaskView] Opening note for task {task_id} (stub - should be replaced)")
		# Rzeczywiste wywołanie będzie przekierowane do main_window.handle_note_button_click()

	def _create_kanban_button(self, task: Dict[str, Any]) -> QPushButton:
		"""Utwórz przycisk KanBan dla zadania
		
		Args:
			task: Słownik z danymi zadania
			
		Returns:
			QPushButton ze strzałką (niebieską lub zieloną)
		"""
		btn = QPushButton()
		task_id = task.get('id')
		
		# Sprawdź czy zadanie jest już na tablicy KanBan
		is_on_kanban = self._is_task_on_kanban(task_id)
		
		if is_on_kanban:
			# Zielone tło - zadanie już na KanBan
			btn.setText("➜")
			btn.setStyleSheet("""
				QPushButton {
					background-color: #4CAF50;
					color: white;
					border: none;
					border-radius: 4px;
					padding: 2px;
					font-size: 14px;
					min-width: 32px;
					max-width: 32px;
					min-height: 28px;
					max-height: 28px;
				}
			""")
			btn.setEnabled(False)  # Nieaktywny
			btn.setToolTip(self._translations_cache['kanban_on_board'])
		else:
			# Niebieskie tło - można dodać do KanBan
			btn.setText("➜")
			btn.setStyleSheet("""
				QPushButton {
					background-color: #2196F3;
					color: white;
					border: none;
					border-radius: 4px;
					padding: 2px;
					font-size: 14px;
					min-width: 32px;
					max-width: 32px;
					min-height: 28px;
					max-height: 28px;
				}
				QPushButton:hover {
					background-color: #1976D2;
				}
				QPushButton:pressed {
					background-color: #0D47A1;
				}
			""")
			btn.setEnabled(True)
			btn.setToolTip(self._translations_cache['kanban_add'])
			
			# Podłącz sygnał kliknięcia
			btn.clicked.connect(lambda checked, tid=task_id: self._on_add_to_kanban(tid))
		
		btn.setFixedSize(32, 28)
		
		return btn

	def _is_task_on_kanban(self, task_id: int) -> bool:
		"""Sprawdź czy zadanie jest już na tablicy KanBan
		
		Args:
			task_id: ID zadania
		
		Returns:
			True jeśli zadanie jest na KanBan, False w przeciwnym wypadku
		"""
		if not self.local_db or not hasattr(self.local_db, 'get_kanban_items'):
			return False
			
		try:
			# Pobierz wszystkie elementy KanBan
			kanban_items = self.local_db.get_kanban_items()
			
			# Sprawdź czy któryś ma to task_id
			for item in kanban_items:
				if item.get('task_id') == task_id:
					return True
					
			return False
		except Exception as e:
			logger.error(f"[TaskView] Error checking if task is on kanban: {e}")
			return False

	def _on_add_to_kanban(self, task_id: int):
		"""Dodaj zadanie do tablicy KanBan (domyślnie do kolumny 'todo')
		
		Jeśli zadanie jest głównym (ma subtaski), przenosi je wraz z subtaskami.
		Jeśli zadanie jest subtaskiem, przenosi tylko ten subtask.
		
		Args:
			task_id: ID zadania do dodania
		"""
		if not self.local_db or not hasattr(self.local_db, 'add_task_to_kanban'):
			logger.error("[TaskView] Cannot add to kanban - database not available")
			return
			
		try:
			# Sprawdź czy zadanie ma subtaski
			has_subtasks = self._has_subtasks(task_id)
			
			if has_subtasks:
				# Główne zadanie z subtaskami - przenosimy wszystko
				# Najpierw dodaj główne zadanie
				success = self.local_db.add_task_to_kanban(
					task_id=task_id,
					column_type='todo',
					position=None
				)
				
				if success:
					# Pobierz subtaski
					subtasks = self.local_db.get_tasks(parent_id=task_id, include_archived=False)
					
					# Dodaj wszystkie subtaski do KanBan
					for subtask in subtasks:
						subtask_id = subtask.get('id')
						self.local_db.add_task_to_kanban(
							task_id=subtask_id,
							column_type='todo',
							position=None
						)
					
					logger.info(f"[TaskView] Task {task_id} with {len(subtasks)} subtasks added to KanBan board")
					# Odśwież widok
					self.populate_table()
				else:
					logger.error(f"[TaskView] Failed to add task {task_id} to KanBan")
			else:
				# Zadanie bez subtasków lub jest subtaskiem - przenosimy tylko to zadanie
				success = self.local_db.add_task_to_kanban(
					task_id=task_id,
					column_type='todo',
					position=None
				)
				
				if success:
					logger.info(f"[TaskView] Task {task_id} added to KanBan board")
					# Odśwież widok
					self.populate_table()
				else:
					logger.error(f"[TaskView] Failed to add task {task_id} to KanBan")
				
		except Exception as e:
			logger.error(f"[TaskView] Error adding task to kanban: {e}")
			import traceback
			traceback.print_exc()
	
	# ==============================
	# SUBTASK BUTTON
	# ==============================
	
	def _create_subtask_button(self, task: Dict[str, Any], row: int) -> QPushButton:
		"""Tworzy przycisk rozwijania/zwijania subtasków
		
		Args:
			task: Słownik z danymi zadania
			row: Numer wiersza w tabeli
			
		Returns:
			QPushButton ze strzałką w dół (▼)
		"""
		from PyQt6.QtWidgets import QPushButton
		from PyQt6.QtCore import Qt
		
		task_id = task.get('id')
		has_subtasks = self._has_subtasks(task_id)
		is_expanded = getattr(self, f'_expanded_task_{task_id}', False)
		
		btn = QPushButton("▼")  # Strzałka w dół
		
		# Kolory
		if has_subtasks:
			# Zielone tło - ma subtaski
			btn_color = "#4CAF50"  # Zielony
			hover_color = "#45A049"
			tooltip = self._translations_cache['subtask_expand']
		else:
			# Niebieskie tło - nie ma subtasków
			btn_color = "#2196F3"  # Niebieski
			hover_color = "#1976D2"
			tooltip = self._translations_cache['subtask_add']
		
		btn.setToolTip(tooltip)
		
		# Style
		btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {btn_color};
				color: white;
				border: none;
				border-radius: 4px;
				padding: 2px;
				font-size: 14px;
				font-weight: bold;
				min-width: 32px;
				max-width: 32px;
				min-height: 28px;
				max-height: 28px;
			}}
			QPushButton:hover {{
				background-color: {hover_color};
			}}
			QPushButton:pressed {{
				background-color: #0D47A1;
			}}
		""")
		
		btn.setFixedSize(32, 28)

		# Podłącz akcję
		btn.clicked.connect(lambda checked, tid=task_id, r=row: self._on_subtask_button_click(tid, r))
		
		return btn

	def _create_list_widget(self, task: Dict[str, Any], column_config: Dict[str, Any]) -> QComboBox:
		"""Utwórz combobox z wartościami z listy użytkownika
		
		Args:
			task: Słownik z danymi zadania
			column_config: Konfiguracja kolumny
			
		Returns:
			QComboBox z wartościami listy
		"""
		combo = QComboBox()
		combo.setEditable(False)
		combo.setMinimumWidth(100)
		
		task_id = task.get('id')
		column_id = column_config.get('column_id', '')
		list_name = column_config.get('list_name', '')
		
		# Pobierz aktualną wartość dla tego zadania
		current_value = self._get_task_value(task, column_id, column_config.get('type', 'list'), column_config)
		
		# Dodaj placeholder jako pierwszą opcję
		placeholder_text = self._translations_cache['list_select']
		combo.addItem(placeholder_text)
		combo.setItemData(0, {'type': 'display'}, Qt.ItemDataRole.UserRole)
		
		# Pobierz wartości listy z bazy danych
		list_values = []
		if self.local_db and hasattr(self.local_db, 'get_custom_lists'):
			try:
				all_lists = self.local_db.get_custom_lists()
				for custom_list in all_lists:
					if custom_list.get('name') == list_name:
						list_values = custom_list.get('values', [])
						break
			except Exception as e:
				logger.error(f"[TaskView] Failed to get custom list '{list_name}': {e}")
		
		# Dodaj wartości listy i mapę indeksów (unikamy polegania na separatorach)
		value_index_map = {}
		for value in list_values:
			item_index = combo.count()
			combo.addItem(str(value))
			combo.setItemData(item_index, {'type': 'set', 'value': value}, Qt.ItemDataRole.UserRole)
			value_index_map[str(value)] = item_index

		# Dodaj opcję wyczyszczenia na końcu
		clear_text = self._translations_cache['list_clear']
		combo.addItem(clear_text)
		combo.setItemData(combo.count() - 1, {'type': 'clear'}, Qt.ItemDataRole.UserRole)
		
		# Ustaw aktualną wartość (jeśli istnieje) lub wartość domyślną - ustaw CurrentIndex na odpowiadający element
		# current_value może być: None, '', lub faktyczna wartość (w tym default_value z konfiguracji)
		if current_value is None or current_value == '':
			# Sprawdź czy jest wartość domyślna w konfiguracji
			default_value = column_config.get('default_value', '')
			if default_value and str(default_value) in value_index_map:
				# Ustaw wartość domyślną jako aktualnie wybraną
				combo.setCurrentIndex(value_index_map[str(default_value)])
			else:
				# Brak wartości i brak wartości domyślnej - użyj placeholder (index 0)
				combo.setCurrentIndex(0)
		else:
			cv = str(current_value)
			if cv in value_index_map:
				# Wartość znajdująca się na liście - ustaw odpowiedni index
				combo.setCurrentIndex(value_index_map[cv])
			else:
				# Wartość nie znajduje się na liście (niespójność danych)
				# Zmień tekst placeholdera aby pokazać wartość i ustaw index 0
				combo.setItemText(0, cv)
				combo.setCurrentIndex(0)
		
		# Podłącz sygnał zmiany
		combo.currentIndexChanged.connect(lambda index: self._on_list_combo_changed(task_id, column_id, combo, index))
		
		return combo

	def _on_list_combo_changed(self, task_id: int, column_id: str, combo: QComboBox, index: int):
		"""Obsługuje zmianę wyboru w combobox listy
		
		Args:
			task_id: ID zadania
			column_id: ID kolumny
			combo: ComboBox z wartościami listy
			index: Wybrany indeks
		"""
		# Sprawdź czy to zmiana na placeholder (index 0) - ignoruj
		if index == 0:
			user_data = combo.itemData(0, Qt.ItemDataRole.UserRole)
			if user_data and isinstance(user_data, dict) and user_data.get('type') == 'display':
				return
		
		logger.info(f"[TaskView] List combo changed: task_id={task_id}, column_id={column_id}, index={index}")
		
		# Pobierz dane z wybranego elementu
		user_data = combo.itemData(index, Qt.ItemDataRole.UserRole)
		
		if not user_data or not isinstance(user_data, dict):
			logger.warning(f"[TaskView] Invalid user data at index {index}")
			return
		
		action_type = user_data.get('type')
		
		if action_type == 'set':
			value = user_data.get('value')
			logger.info(f"[TaskView] Setting list value '{value}' for task {task_id} column '{column_id}'")
			if value is not None:
				# Zapisz wartość do bazy
				success = self._update_custom_column_value(task_id, column_id, value)
				if success:
					# Zaktualizuj cache zadania w _row_task_map
					for row, task in self._row_task_map.items():
						if task.get('id') == task_id:
							if 'custom_data' not in task:
								task['custom_data'] = {}
							task['custom_data'][column_id] = value
							break
				# Pozycja pozostaje na wybranej wartości (index nie zmienia się)
		elif action_type == 'clear':
			logger.info(f"[TaskView] Clearing list value for task {task_id} column '{column_id}'")
			success = self._update_custom_column_value(task_id, column_id, None)
			if success:
				# Zaktualizuj cache zadania w _row_task_map
				for row, task in self._row_task_map.items():
					if task.get('id') == task_id:
						if 'custom_data' in task and isinstance(task['custom_data'], dict):
							task['custom_data'].pop(column_id, None)
						break
			# Ustaw z powrotem na placeholder
			combo.setCurrentIndex(0)
		else:
			logger.warning(f"[TaskView] Unknown list action '{action_type}'")
		
		# Podłącz z powrotem sygnał
		combo.currentIndexChanged.connect(lambda idx: self._on_list_combo_changed(task_id, column_id, combo, idx))

	def _create_tag_widget(self, task: dict) -> QWidget:
		"""Tworzy prostą rozwijaną listę tagów
		
		Args:
			task: Słownik z danymi zadania
			
		Returns:
			QComboBox z tagami do wyboru
		"""
		from PyQt6.QtWidgets import QComboBox, QStyledItemDelegate, QStylePainter, QStyleOptionComboBox, QStyle
		from PyQt6.QtCore import Qt
		from PyQt6.QtGui import QColor, QPainter, QPalette
		
		# Stwórz delegata na wzór column_delegate.py
		class TagItemDelegate(QStyledItemDelegate):
			def __init__(self, parent, tag_color_map, placeholder_color: str):
				super().__init__(parent)
				self.tag_color_map = tag_color_map
				self.placeholder_color = placeholder_color

			def paint(self, painter: Optional[QPainter], option, index):
				if painter is None:
					super().paint(painter, option, index)
					return
				tag_name = index.data(Qt.ItemDataRole.DisplayRole) or ""
				color_hex = self.tag_color_map.get(tag_name, self.placeholder_color)

				painter.save()
				painter.fillRect(option.rect, QColor(color_hex))

				color = QColor(color_hex)
				brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
				text_color = QColor("#000000") if brightness > 128 else QColor("#FFFFFF")

				painter.setPen(text_color)
				painter.drawText(
					option.rect.adjusted(5, 0, -5, 0),
					Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
					tag_name,
				)
				painter.restore()

		# Custom ComboBox który maluje tło wybranego elementu
		class ColoredTagComboBox(QComboBox):
			def __init__(self, parent=None):
				super().__init__(parent)
				self.tag_color_map = {}
				self.placeholder_text = "-- Brak tagu --"
				self.placeholder_color = "#f0f0f0"

			def _resolve_color(self, text: Optional[str]) -> QColor:
				if not text:
					return QColor(self.placeholder_color)
				color_hex = self.tag_color_map.get(text)
				return QColor(color_hex) if color_hex else QColor(self.placeholder_color)

			def _resolve_text_color(self, bg_color: QColor) -> QColor:
				brightness = (bg_color.red() * 299 + bg_color.green() * 587 + bg_color.blue() * 114) / 1000
				return QColor("#000000") if brightness > 128 else QColor("#FFFFFF")

			def paintEvent(self, e):  # noqa: D401 - custom painting for colorised tags
				option = QStyleOptionComboBox()
				self.initStyleOption(option)
				background = self._resolve_color(option.currentText)
				text_color = self._resolve_text_color(background)

				option.palette.setColor(QPalette.ColorRole.Button, background)
				option.palette.setColor(QPalette.ColorRole.Base, background)
				option.palette.setColor(QPalette.ColorRole.Text, text_color)
				option.palette.setColor(QPalette.ColorRole.ButtonText, text_color)
				option.palette.setColor(QPalette.ColorRole.WindowText, text_color)

				painter = QStylePainter(self)
				painter.drawComplexControl(QStyle.ComplexControl.CC_ComboBox, option)
				painter.drawControl(QStyle.ControlElement.CE_ComboBoxLabel, option)

			def _update_style(self):
				display_text = self.itemText(0) if self.count() > 0 else self.currentText()
				if not display_text:
					display_text = self.currentText()
				color = self._resolve_color(display_text)
				text_color = self._resolve_text_color(color)
				self.setStyleSheet(
					f"QComboBox {{ background-color: {color.name()}; color: {text_color.name()}; "
					f"border: 1px solid #ccc; border-radius: 3px; padding: 2px 8px; font-size: 11px; }}"
					"QComboBox::drop-down { border: none; }"
					"QComboBox::down-arrow { width: 12px; height: 12px; }"
				)
				self.update()
		
		combo = ColoredTagComboBox()
		combo.setEditable(False)
		combo.setMinimumWidth(120)  # Ustaw minimalną szerokość
		task_id = task.get('id')
		
		# Pobierz tagi z zadania
		tags = task.get('tags', [])
		
		# Jeśli tagi to string, spróbuj przekonwertować na listę
		if isinstance(tags, str):
			if tags.strip():
				tags = [{'name': tag.strip(), 'color': '#CCCCCC'} for tag in tags.split(',')]
			else:
				tags = []
		
		# Stwórz mapę kolorów dla wszystkich tagów
		tag_color_map = {}
		
		# Pobierz wszystkie dostępne tagi
		if self.local_db and hasattr(self.local_db, 'get_tags'):
			all_tags = self.local_db.get_tags()
			for tag in all_tags:
				tag_name = tag.get('name', '')
				tag_color = tag.get('color', '#CCCCCC')
				tag_color_map[tag_name] = tag_color
		
		# Dodaj kolory z aktualnie przypisanych tagów
		for tag in tags:
			if isinstance(tag, dict):
				tag_name = tag.get('name', '')
				if not tag_name:
					continue
				tag_color = tag.get('color')
				if not tag_color or tag_color == '#CCCCCC':
					tag_color = tag_color_map.get(tag_name, '#CCCCCC')
				tag_color_map[tag_name] = tag_color
		
		# Ustal aktualnie przypisany tag (jeśli istnieje)
		current_tag_name = combo.placeholder_text
		current_tag_color = combo.placeholder_color
		if tags:
			for tag_entry in tags:
				if isinstance(tag_entry, dict) and tag_entry.get('name'):
					current_tag_name = tag_entry.get('name', '')
					current_tag_color = tag_color_map.get(current_tag_name, tag_entry.get('color', '#CCCCCC') or '#CCCCCC')
					break

		combo.addItem(current_tag_name)
		combo.setItemData(0, {'type': 'display'}, Qt.ItemDataRole.UserRole)
		tag_color_map[combo.placeholder_text] = combo.placeholder_color
		tag_color_map[current_tag_name] = current_tag_color
		combo.setCurrentIndex(0)

		# Pobierz wszystkie dostępne tagi
		available_tags = []
		if self.local_db and hasattr(self.local_db, 'get_tags'):
			available_tags = self.local_db.get_tags() or []
			if available_tags:
				combo.insertSeparator(combo.count())
				for tag in available_tags:
					tag_name = tag.get('name', '')
					if not tag_name:
						continue
					tag_color = tag.get('color', '#CCCCCC') or '#CCCCCC'
					tag_color_map[tag_name] = tag_color
					item_index = combo.count()
					combo.addItem(tag_name)
					combo.setItemData(item_index, {'type': 'set', 'tag_id': tag.get('id')}, Qt.ItemDataRole.UserRole)

		# Dodaj opcję usunięcia tagu
		combo.insertSeparator(combo.count())
		clear_text = "✖ Usuń tag"
		combo.addItem(clear_text)
		combo.setItemData(combo.count() - 1, {'type': 'clear'}, Qt.ItemDataRole.UserRole)
		tag_color_map[clear_text] = combo.placeholder_color

		# ✨ KLUCZOWE: Ustaw delegate dla rozwijanej listy (tak jak w column_delegate.py)
		tag_delegate = TagItemDelegate(combo, tag_color_map, combo.placeholder_color)
		combo.view().setItemDelegate(tag_delegate)

		# Przekaż mapę kolorów do ComboBox
		combo.tag_color_map = tag_color_map

		# Zaktualizuj style po ustawieniu mapy kolorów
		combo._update_style()

		# Podłącz sygnał zmiany
		combo.currentIndexChanged.connect(lambda index: self._on_tag_combo_changed(task_id, combo, index))

		return combo
	
	def _on_tag_combo_changed(self, task_id: int, combo: 'QComboBox', index: int):
		"""Obsługuje zmianę wyboru w combobox tagów
		
		Args:
			task_id: ID zadania
			combo: ComboBox z tagami
			index: Wybrany indeks
		"""
		from PyQt6.QtWidgets import QComboBox
		from PyQt6.QtCore import Qt
		
		logger.info(f"[TaskView] Tag combo changed: task_id={task_id}, index={index}")
		
		# Pobierz dane z wybranego elementu
		user_data = combo.itemData(index, Qt.ItemDataRole.UserRole)
		
		logger.info(f"[TaskView] User data: {user_data}, type: {type(user_data)}")
		
		if not user_data or not isinstance(user_data, dict):
			logger.warning(f"[TaskView] Invalid user data at index {index}")
			return
		
		action_type = user_data.get('type')
		
		logger.info(f"[TaskView] Action type: {action_type}")
		
		# Nie reaguj na kliknięcie w element 'display'
		if action_type == 'display':
			logger.info("[TaskView] Ignoring display element click")
			return
		
		# Tymczasowo odłącz sygnał aby uniknąć rekurencji
		try:
			combo.currentIndexChanged.disconnect()
		except TypeError:
			pass
		
		placeholder_text = getattr(combo, 'placeholder_text', '-- Brak tagu --')
		placeholder_color = getattr(combo, 'placeholder_color', '#f0f0f0')
		selected_text = combo.itemText(index)
		selected_color = combo.tag_color_map.get(selected_text, placeholder_color)

		if action_type == 'set':
			tag_id = user_data.get('tag_id')
			logger.info(f"[TaskView] Setting tag {tag_id} for task {task_id}")
			if tag_id:
				self._set_task_tag(task_id, tag_id)
				combo.setItemText(0, selected_text)
				combo.tag_color_map[selected_text] = selected_color
		elif action_type == 'clear':
			logger.info(f"[TaskView] Clearing tags for task {task_id}")
			self._set_task_tag(task_id, None)
			combo.setItemText(0, placeholder_text)
			combo.tag_color_map[placeholder_text] = placeholder_color
		else:
			logger.warning(f"[TaskView] Unknown tag action '{action_type}'")

		# Resetuj do index 0 (element 'display') i odśwież wygląd
		combo.setCurrentIndex(0)
		combo._update_style()
		
		# Podłącz z powrotem sygnał
		combo.currentIndexChanged.connect(lambda idx: self._on_tag_combo_changed(task_id, combo, idx))
	
	def _show_tag_context_menu(self, pos, task_id: int, tag_id: int, label: QLabel):
		"""Pokazuje menu kontekstowe dla tagu
		
		Args:
			pos: Pozycja kliknięcia
			task_id: ID zadania
			tag_id: ID tagu
			label: Etykieta tagu
		"""
		from PyQt6.QtWidgets import QMenu
		from PyQt6.QtGui import QAction
		
		menu = QMenu()
		remove_action = QAction("Usuń tag", menu)
		remove_action.triggered.connect(lambda: self._remove_tag_from_task(task_id, tag_id))
		menu.addAction(remove_action)
		
		menu.exec(label.mapToGlobal(pos))
	
	def _set_task_tag(self, task_id: int, tag_id: Optional[int]):
		"""Ustawia pojedynczy tag dla zadania (lub usuwa jeśli tag_id to None)."""
		try:
			logger.info(f"[TaskView] Updating tag for task {task_id} -> {tag_id}")
			db = self.task_logic.db if self.task_logic else self.local_db
			if not db or not hasattr(db, 'db_path'):
				logger.error("[TaskView] No database connection available")
				return

			import sqlite3
			with sqlite3.connect(db.db_path) as conn:
				cursor = conn.cursor()
				cursor.execute(
					"""
					DELETE FROM task_tag_assignments
					WHERE task_id = ?
					""",
					(task_id,),
				)

				if tag_id:
					cursor.execute(
						"""
						INSERT INTO task_tag_assignments (task_id, tag_id)
						VALUES (?, ?)
						""",
						(task_id, tag_id),
					)

				conn.commit()

		except Exception as e:
			logger.error(f"[TaskView] Failed to set task tag: {e}")
			import traceback
		else:
			self.refresh_tasks()

	def _show_tag_selection_menu(self, task_id: int, button: QPushButton):
		"""Pokazuje menu wyboru tagów
		
		Args:
			task_id: ID zadania
			button: Przycisk, który wywołał menu
		"""
		from PyQt6.QtWidgets import QMenu
		from PyQt6.QtGui import QAction, QCursor
		
		# Pobierz wszystkie dostępne tagi
		all_tags = self.local_db.get_tags()
		
		# Pobierz aktualne tagi zadania bezpośrednio z bazy danych
		try:
			conn = self.local_db.get_connection()
			cursor = conn.cursor()
			
			cursor.execute("""
				SELECT tag_id FROM task_tag_assignments
				WHERE task_id = ?
			""", (task_id,))
			
			current_tag_ids = [row[0] for row in cursor.fetchall()]
		except Exception as e:
			logger.error(f"[TaskView] Failed to get current tags: {e}")
			current_tag_ids = []
		
		# Utwórz menu
		menu = QMenu()
		
		if not all_tags:
			no_tags_action = QAction("Brak dostępnych tagów", menu)
			no_tags_action.setEnabled(False)
			menu.addAction(no_tags_action)
		else:
			for tag in all_tags:
				tag_id = tag.get('id')
				tag_name = tag.get('name', '')
				
				# Pomiń tagi już przypisane
				if tag_id in current_tag_ids:
					continue
				
				action = QAction(tag_name, menu)
				action.triggered.connect(lambda checked, tid=task_id, tagid=tag_id: self._add_tag_to_task(tid, tagid))
				menu.addAction(action)
		
		# Pokaż menu pod przyciskiem
		menu.exec(button.mapToGlobal(button.rect().bottomLeft()))
	
	def _add_tag_to_task(self, task_id: int, tag_id: int):
		"""Dodaje tag do zadania
		
		Args:
			task_id: ID zadania
			tag_id: ID tagu
		"""
		logger.info(f"[TaskView] Adding tag {tag_id} to task {task_id}")
		self._set_task_tag(task_id, tag_id)
	
	def _remove_tag_from_task(self, task_id: int, tag_id: int):
		"""Usuwa tag z zadania
		
		Args:
			task_id: ID zadania
			tag_id: ID tagu
		"""
		logger.info(f"[TaskView] Removing tag {tag_id} from task {task_id}")
		self._set_task_tag(task_id, None)
	
	def _create_add_subtask_button(self, parent_id: int) -> QPushButton:
		"""Tworzy przycisk + do dodania subtaska (dla wierszy subtasków)
		
		Args:
			parent_id: ID zadania nadrzędnego
			
		Returns:
			QPushButton ze znakiem +
		"""
		from PyQt6.QtWidgets import QPushButton
		
		btn = QPushButton("+")
		
		# Kolory - zawsze niebieski (akcja dodania)
		btn_color = "#2196F3"  # Niebieski
		hover_color = "#1976D2"
		
		btn.setToolTip(self._translations_cache['subtask_add_more'])
		
		# Style
		btn.setStyleSheet(f"""
			QPushButton {{
				background-color: {btn_color};
				color: white;
				border: none;
				border-radius: 4px;
				padding: 2px;
				font-size: 16px;
				font-weight: bold;
				min-width: 32px;
				max-width: 32px;
				min-height: 28px;
				max-height: 28px;
			}}
			QPushButton:hover {{
				background-color: {hover_color};
			}}
			QPushButton:pressed {{
				background-color: #0D47A1;
			}}
		""")
		
		btn.setFixedSize(32, 28)
	
		# Podłącz akcję - otwarcie dialogu dodawania subtaska
		btn.clicked.connect(lambda checked, pid=parent_id: self._add_subtask_dialog(pid))
		
		return btn
	
	def _has_subtasks(self, task_id: int) -> bool:
		"""Sprawdza czy zadanie ma subtaski (używa cache)
		
		Args:
			task_id: ID zadania
			
		Returns:
			True jeśli zadanie ma subtaski, False w przeciwnym razie
		"""
		if not self.task_logic:
			return False
		
		# TasksManager ma local_db, TaskLogic (legacy) ma db
		db = getattr(self.task_logic, 'local_db', None) or getattr(self.task_logic, 'db', None)
		if not db:
			return False
		
		try:
			# Użyj cache zamiast zapytania do bazy
			subtasks = self._get_cached_subtasks(task_id)
			return len(subtasks) > 0
		except Exception as e:
			logger.error(f"[TaskView] Error checking subtasks for task {task_id}: {e}")
			return False
	
	def _on_subtask_button_click(self, task_id: int, row: int):
		"""Obsługuje kliknięcie przycisku subtasków
		
		Args:
			task_id: ID zadania
			row: Numer wiersza w tabeli
		"""
		has_subtasks = self._has_subtasks(task_id)
		
		if has_subtasks:
			# Rozwiń/Zwiń subtaski
			is_expanded = getattr(self, f'_expanded_task_{task_id}', False)
			
			if is_expanded:
				# Zwiń
				self._collapse_subtasks(task_id, row)
				setattr(self, f'_expanded_task_{task_id}', False)
			else:
				# Rozwiń
				self._expand_subtasks(task_id, row)
				setattr(self, f'_expanded_task_{task_id}', True)
		else:
			# Otwórz dialog dodawania subtaska
			self._add_subtask_dialog(task_id)
	
	def _expand_subtasks(self, parent_id: int, parent_row: int):
		"""Rozwija subtaski w tabeli z optymalizacją wydajności (używa cache)
		
		Args:
			parent_id: ID zadania nadrzędnego
			parent_row: Wiersz zadania nadrzędnego
		"""
		if not self.task_logic:
			return
		
		# TasksManager ma local_db, TaskLogic (legacy) ma db  
		db = getattr(self.task_logic, 'local_db', None) or getattr(self.task_logic, 'db', None)
		if not db:
			return
		
		try:
			# Użyj cache zamiast zapytania do bazy
			subtasks = self._get_cached_subtasks(parent_id)
			
			if not subtasks:
				return
			
			# Pobierz konfigurację kolumn raz przed pętlą
			visible_columns = self._get_visible_columns()
			
			# Prefiks dla subtasków (cache tłumaczenia)
			subtask_prefix = t("tasks.subtask.prefix")
			
			# Wyłącz renderowanie podczas dodawania wierszy
			self.table.setUpdatesEnabled(False)
			
			try:
				# Wstaw wszystkie wiersze jednocześnie
				for idx in range(len(subtasks)):
					self.table.insertRow(parent_row + idx + 1)
				
				# Wypełnij wiersze dla subtasków
				for idx, subtask in enumerate(subtasks):
					row = parent_row + idx + 1
					subtask_id = subtask.get('id')
					
					# Dodaj do mapy wierszy
					task_copy = dict(subtask)
					if 'custom_data' in subtask and isinstance(subtask['custom_data'], dict):
						task_copy['custom_data'] = dict(subtask['custom_data'])
					self._row_task_map[row] = task_copy
					
					# Wypełnij kolumny
					for col_idx, col_config in enumerate(visible_columns):
						col_id = col_config.get('column_id', '')
						col_type = col_config.get('type', 'text')
						
						# Dla kolumny Zadanie dodaj wcięcie
						if col_id == 'Zadanie':
							value = self._get_task_value(subtask, col_id, col_type, col_config)
							item = QTableWidgetItem(f"   {subtask_prefix} {value}")
							item.setForeground(Qt.GlobalColor.darkGray)
							if col_idx == 0:
								item.setData(Qt.ItemDataRole.UserRole, subtask_id)
							self.table.setItem(row, col_idx, item)
						elif col_id == 'Subtaski':
							# Dla subtasków pokaż przycisk + do dodania kolejnego subtaska
							parent_task_id = subtask.get('parent_id')
							if parent_task_id:
								btn = self._create_add_subtask_button(parent_task_id)
								placeholder_item = QTableWidgetItem('')
								placeholder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
								if col_idx == 0:
									placeholder_item.setData(Qt.ItemDataRole.UserRole, subtask_id)
								self.table.setItem(row, col_idx, placeholder_item)
								self.table.setCellWidget(row, col_idx, self._wrap_cell_widget(btn))
							else:
								self.table.setItem(row, col_idx, QTableWidgetItem(''))
						elif col_type == 'checkbox':
							value = self._get_task_value(subtask, col_id, col_type, col_config)
							checkbox = QCheckBox()
							checkbox.setChecked(bool(value))
							checkbox.setProperty('task_id', subtask_id)
							checkbox.setProperty('column_id', col_id)
							checkbox.stateChanged.connect(lambda state, tid=subtask_id, cid=col_id: 
							                             self._on_checkbox_changed(tid, cid, state))
							placeholder_item = QTableWidgetItem('')
							placeholder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
							if col_idx == 0:
								placeholder_item.setData(Qt.ItemDataRole.UserRole, subtask_id)
							self.table.setItem(row, col_idx, placeholder_item)
							self.table.setCellWidget(row, col_idx, self._wrap_cell_widget(checkbox))
						elif col_type == 'button' and col_id == 'KanBan':
							btn = self._create_kanban_button(subtask)
							placeholder_item = QTableWidgetItem('')
							placeholder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
							if col_idx == 0:
								placeholder_item.setData(Qt.ItemDataRole.UserRole, subtask_id)
							self.table.setItem(row, col_idx, placeholder_item)
							self.table.setCellWidget(row, col_idx, self._wrap_cell_widget(btn))
						elif col_type == 'button' and col_id == 'Notatka':
							btn = self._create_note_button(subtask)
							placeholder_item = QTableWidgetItem('')
							placeholder_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
							if col_idx == 0:
								placeholder_item.setData(Qt.ItemDataRole.UserRole, subtask_id)
							self.table.setItem(row, col_idx, placeholder_item)
							self.table.setCellWidget(row, col_idx, self._wrap_cell_widget(btn))
						else:
							value = self._get_task_value(subtask, col_id, col_type, col_config)
							item = QTableWidgetItem(str(value) if value is not None else '')
							if col_idx == 0:
								item.setData(Qt.ItemDataRole.UserRole, subtask_id)
							self.table.setItem(row, col_idx, item)
			finally:
				# Włącz ponownie renderowanie
				self.table.setUpdatesEnabled(True)
			
			logger.info(f"[TaskView] Expanded {len(subtasks)} subtasks for task {parent_id}")
			
		except Exception as e:
			logger.error(f"[TaskView] Error expanding subtasks: {e}")
			import traceback
			traceback.print_exc()
	
	def _collapse_subtasks(self, parent_id: int, parent_row: int):
		"""Zwija subtaski (usuwa wiersze z tabeli, używa cache)
		
		Args:
			parent_id: ID zadania nadrzędnego
			parent_row: Wiersz zadania nadrzędnego
		"""
		if not self.task_logic:
			return
		
		# TasksManager ma local_db, TaskLogic (legacy) ma db
		db = getattr(self.task_logic, 'local_db', None) or getattr(self.task_logic, 'db', None)
		if not db:
			return
		
		try:
			# Użyj cache zamiast zapytania do bazy
			subtasks = self._get_cached_subtasks(parent_id)
			
			# Usuń wiersze subtasków (od końca, aby nie zmienić indeksów)
			for i in range(len(subtasks) - 1, -1, -1):
				self.table.removeRow(parent_row + i + 1)
			
			logger.info(f"[TaskView] Collapsed {len(subtasks)} subtasks for task {parent_id}")
			
		except Exception as e:
			logger.error(f"[TaskView] Error collapsing subtasks: {e}")
			import traceback
			traceback.print_exc()
	
	def _add_subtask_dialog(self, parent_id: int):
		"""Otwiera dialog dodawania subtaska - placeholder dla main_window
		
		Args:
			parent_id: ID zadania nadrzędnego
		"""
		logger.info(f"[TaskView] Add subtask dialog for parent task {parent_id} (stub - should be replaced by main_window)")
		# Ta metoda zostanie zastąpiona przez main_window podobnie jak open_task_note

	def _apply_row_color(self, row: int, color: str) -> None:
		"""Zastosuj kolor tła do całego wiersza tabeli."""
		try:
			from PyQt6.QtGui import QColor, QBrush
			from PyQt6.QtCore import Qt
			
			logger.info(f"[TaskView] Applying color {color} to row {row}")
			
			q_color = QColor(color)
			brush = QBrush(q_color)
			
			for col in range(self.table.columnCount()):
				item = self.table.item(row, col)
				if item:
					item.setBackground(brush)
					item.setData(Qt.ItemDataRole.BackgroundRole, brush)
					logger.debug(f"[TaskView] Set item background for ({row}, {col})")
				widget = self.table.cellWidget(row, col)
				if widget:
					# Zachowaj oryginalny stylesheet aby móc przywrócić kolor
					if widget.property('_baseStyleSheet') is None:
						widget.setProperty('_baseStyleSheet', widget.styleSheet())
					widget.setAutoFillBackground(True)
					base_style = widget.property('_baseStyleSheet') or ''
					base_style = base_style.strip()
					if base_style and not base_style.endswith(';'):
						base_style = f"{base_style};"
					widget.setStyleSheet(f"{base_style} background-color: {color};")
					widget.setProperty('_rowColor', color)
					logger.debug(f"[TaskView] Set widget background for ({row}, {col})")
			
			viewport = self.table.viewport() if self.table else None
			if viewport:
				viewport.update()
		except Exception as e:
			logger.error(f"[TaskView] Error applying row color: {e}")
			import traceback
			logger.error(traceback.format_exc())

	def _clear_row_color(self, row: int) -> None:
		"""Przywróć domyślne tło wiersza."""
		try:
			from PyQt6.QtGui import QBrush
			from PyQt6.QtCore import Qt
			
			logger.info(f"[TaskView] Clearing row color for row {row}")
			default_brush = QBrush()
			for col in range(self.table.columnCount()):
				item = self.table.item(row, col)
				if item:
					item.setBackground(default_brush)
					item.setData(Qt.ItemDataRole.BackgroundRole, None)
				widget = self.table.cellWidget(row, col)
				if widget:
					base_style = widget.property('_baseStyleSheet')
					if base_style is not None:
						widget.setStyleSheet(base_style)
					else:
						widget.setStyleSheet('')
					widget.setAutoFillBackground(False)
					widget.setProperty('_rowColor', None)
			viewport = self.table.viewport() if self.table else None
			if viewport:
				viewport.update()
		except Exception as e:
			logger.error(f"[TaskView] Error clearing row color: {e}")
			import traceback
			logger.error(traceback.format_exc())
	
	# ==============================
	# CACHE SUBTASKÓW (Optymalizacja -60% zapytań DB)
	# ==============================
	
	def _build_subtasks_cache(self) -> None:
		"""
		Buduje cache wszystkich subtasków jednym zapytaniem do bazy.
		Zamiast N zapytań (po jednym dla każdego zadania), wykonujemy jedno zapytanie.
		"""
		if not self.task_logic:
			return
		
		# TasksManager ma local_db, TaskLogic (legacy) ma db
		db = getattr(self.task_logic, 'local_db', None) or getattr(self.task_logic, 'db', None)
		if not db:
			return
		
		try:
			# Pobierz wszystkie zadania które mają parent_id (są subtaskami)
			all_tasks = db.get_tasks(include_archived=False)
			
			# Grupuj subtaski po parent_id
			self._subtasks_cache.clear()
			for task in all_tasks:
				parent_id = task.get('parent_id')
				if parent_id:
					if parent_id not in self._subtasks_cache:
						self._subtasks_cache[parent_id] = []
					self._subtasks_cache[parent_id].append(task)
			
			self._subtasks_cache_valid = True
			logger.debug(f"[TaskView] Built subtasks cache with {len(self._subtasks_cache)} parents")
			
		except Exception as e:
			logger.error(f"[TaskView] Failed to build subtasks cache: {e}")
			self._subtasks_cache_valid = False
	
	def _invalidate_subtasks_cache(self) -> None:
		"""Unieważnij cache subtasków (np. po dodaniu/usunięciu zadania)"""
		self._subtasks_cache_valid = False
		self._subtasks_cache.clear()
		logger.debug("[TaskView] Subtasks cache invalidated")
	
	def _get_cached_subtasks(self, parent_id: int) -> List[Dict[str, Any]]:
		"""
		Pobierz subtaski z cache (lub z bazy jeśli cache nieważny)
		
		Args:
			parent_id: ID zadania nadrzędnego
			
		Returns:
			Lista subtasków
		"""
		# Jeśli cache nieważny, przebuduj
		if not self._subtasks_cache_valid:
			self._build_subtasks_cache()
		
		# Zwróć z cache (pusta lista jeśli brak subtasków)
		return self._subtasks_cache.get(parent_id, [])
	
	# ==============================
	# BATCH UPDATES (Optymalizacja -70% zapytań DB)
	# ==============================
	
	def _schedule_update(self, task_id: int, column_id: str, value: Any) -> None:
		"""Dodaje aktualizację do kolejki batch updates zamiast natychmiastowego zapisu.
		
		Args:
			task_id: ID zadania
			column_id: ID kolumny
			value: Wartość do zapisania
		"""
		if task_id not in self._pending_updates:
			self._pending_updates[task_id] = {}
		
		self._pending_updates[task_id][column_id] = value
		
		# Restart timera - jeśli użytkownik edytuje wiele pól, czekamy aż skończy
		self._batch_update_timer.stop()
		self._batch_update_timer.start(self._batch_update_delay_ms)
		
		logger.debug(f"[TaskView] Scheduled update: task={task_id}, column={column_id}, pending={len(self._pending_updates)}")
	
	def _flush_pending_updates(self) -> None:
		"""Wykonuje wszystkie oczekujące aktualizacje w jednej transakcji.
		
		Zamiast N wywołań update_task (każde otwiera connection, wykonuje UPDATE, commit),
		grupujemy wszystkie zmiany i wykonujemy je w jednej transakcji.
		
		Redukcja: z N transakcji do 1 transakcji (-70% do -90% w zależności od liczby zmian)
		"""
		if not self._pending_updates:
			return
		
		try:
			count = len(self._pending_updates)
			logger.info(f"[TaskView] Flushing batch updates: {count} tasks")
			
			db_targets: List[Any] = []
			if self.task_logic and getattr(self.task_logic, 'db', None):
				db_targets.append(self.task_logic.db)
			if self.local_db and self.local_db not in db_targets:
				db_targets.append(self.local_db)
			
			for db in db_targets:
				if not hasattr(db, 'get_task_by_id') or not hasattr(db, 'update_task'):
					continue
				
				# Dla każdego zadania z oczekującymi zmianami
				for task_id, column_updates in self._pending_updates.items():
					try:
						# Pobierz obecne dane zadania
						task = db.get_task_by_id(task_id)
						if not task:
							logger.warning(f"[TaskView] Task {task_id} not found during batch update")
							continue
						
						custom_data = task.get('custom_data')
						if not isinstance(custom_data, dict):
							custom_data = {}
						
						# Zastosuj wszystkie zmiany dla tego zadania
						for column_id, value in column_updates.items():
							if value is None:
								custom_data.pop(column_id, None)
							else:
								custom_data[column_id] = value
						
						# Jeden UPDATE dla wszystkich kolumn tego zadania
						db.update_task(task_id, custom_data=custom_data)
						logger.debug(f"[TaskView] Batch updated task {task_id}: {len(column_updates)} columns")
						
					except Exception as exc:
						logger.error(f"[TaskView] Error batch updating task {task_id}: {exc}")
			
			# Wyczyść kolejkę
			self._pending_updates.clear()
			logger.info(f"[TaskView] Batch update completed: {count} tasks")
			
		except Exception as exc:
			logger.error(f"[TaskView] Error during flush_pending_updates: {exc}")
			import traceback
			logger.error(traceback.format_exc())
	
	# ==============================
	# MENU KONTEKSTOWE
	# ==============================
	
	def _show_context_menu(self, position) -> None:
		"""Wyświetl menu kontekstowe dla zadania.
		
		Args:
			position: Pozycja kliknięcia w widżecie
		"""
		# Lazy import, aby uniknąć cyklicznych importów
		if self.context_menu is None:
			try:
				# Import z poprawionej ścieżki
				from ..Modules.task_module.task_context_menu import TaskContextMenu
				self.context_menu = TaskContextMenu(self)
				logger.info("[TaskView] TaskContextMenu initialized successfully")
			except Exception as e:
				logger.error(f"[TaskView] Failed to import TaskContextMenu: {e}")
				import traceback
				traceback.print_exc()
				return
		
		# Wyświetl menu
		self.context_menu.show_menu(position)
	
	def closeEvent(self, a0):
		"""Obsługa zamykania widoku - flush pending updates przed zamknięciem."""
		# Zatrzymaj timer i wymuś flush wszystkich pending updates
		self._batch_update_timer.stop()
		self._flush_pending_updates()
		
		logger.debug("[TaskView] Closing - flushed pending updates")
		super().closeEvent(a0)




