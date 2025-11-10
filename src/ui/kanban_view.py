"""
KanBan View - Widok tablicy KanBan do zarządzania zadaniami
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QComboBox, QSpinBox, QScrollArea, QFrame,
    QMessageBox, QGroupBox, QToolButton, QMenu
)
from PyQt6.QtCore import Qt, pyqtSignal, QEvent, QObject
from PyQt6.QtGui import QFont, QAction, QMouseEvent
from loguru import logger
from typing import Optional, Dict, Any, List, Callable, Tuple
from datetime import datetime
from ..utils.i18n_manager import t, get_i18n
from ..utils import get_theme_manager
from ..Modules.task_module.kanban_context_menu import KanbanContextMenu
from .kanban_log_dialog import KanbanLogDialog
from .ui_task_simple_dialogs import TaskEditDialog


class KanBanView(QWidget):
    """Widok tablicy KanBan"""
    
    # Sygnały
    task_moved = pyqtSignal(int, str, int)  # task_id, column_type, position
    settings_changed = pyqtSignal(dict)  # nowe ustawienia
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.task_logic = None
        self.db = None
        
        self._theme_manager = get_theme_manager()
        self._current_colors = self._theme_manager.get_current_colors()
        self._i18n = get_i18n()

        # Ustawienia
        self.settings = {
            'max_in_progress': 3,
            'hide_completed_after': 0,
            'show_on_hold': False,
            'show_review': False,
            'show_todo': True,
            'show_done': True
        }
        
        # Kolumny KanBan
        self.columns = {}

        # Callbacki przekazywane przez MainWindow
        self.open_task_note: Callable[[int], None] = lambda task_id: logger.info(
            f"[KanBanView] Note handler not set for task {task_id}"
        )
        self.add_subtask: Optional[Callable[[int], None]] = None
        self.context_menu = KanbanContextMenu(self)
        self._log_button: Optional[QPushButton] = None
        
        # Drag & Drop Manager (inicjalizacja po set_task_logic)
        self.drag_drop_manager = None
        
        # Flaga zapobiegająca rekurencyjnemu refresh podczas drag & drop
        self._is_refreshing = False
        
        self._setup_ui()
        self._i18n.language_changed.connect(self._on_language_changed)
        self.update_translations()
        self.apply_theme(refresh=False)
        logger.info("[KanBanView] Initialized")
    
    def _setup_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(10)
        
        # Pasek zarządzania
        control_bar = self._create_control_bar()
        layout.addWidget(control_bar)
        
        # Sekcja główna z kolumnami
        columns_widget = self._create_columns_section()
        layout.addWidget(columns_widget, 1)
        
        self.setLayout(layout)
    
    def _create_control_bar(self) -> QWidget:
        """Utwórz pasek zarządzania u góry"""
        bar = QWidget()
        bar.setObjectName("KanbanControlBar")
        bar_layout = QHBoxLayout(bar)
        bar_layout.setContentsMargins(0, 0, 0, 0)
        self._control_bar = bar
        
        # Lewa strona - opcje ukrywania i limit
        left_panel = QWidget()
        left_layout = QHBoxLayout(left_panel)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        # Lista "Ukryj zakończone"
        self._hide_label = QLabel(t("kanban.settings.hide_completed"))
        left_layout.addWidget(self._hide_label)

        self.hide_completed_combo = QComboBox()
        self.hide_completed_combo.currentIndexChanged.connect(self._on_hide_completed_changed)
        left_layout.addWidget(self.hide_completed_combo)
        self._populate_hide_combo(self.settings.get('hide_completed_after', 0))
        
        left_layout.addSpacing(20)
        
        # Maksymalna ilość zadań w trakcie
        self._max_label = QLabel(t("kanban.settings.max_in_progress"))
        left_layout.addWidget(self._max_label)

        self.max_in_progress_spin = QSpinBox()
        self.max_in_progress_spin.setMinimum(1)
        self.max_in_progress_spin.setMaximum(20)
        self.max_in_progress_spin.setValue(self.settings.get('max_in_progress', 3))
        self.max_in_progress_spin.valueChanged.connect(self._on_max_in_progress_changed)
        left_layout.addWidget(self.max_in_progress_spin)
        
        left_layout.addStretch()
        
        # Prawa strona - dodatkowe kolumny
        right_panel = QWidget()
        right_layout = QHBoxLayout(right_panel)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        right_layout.addStretch()

        self._log_button = QPushButton(t('kanban.log.button', 'Log'))
        self._log_button.setObjectName("KanbanLogButton")
        self._log_button.setEnabled(False)
        self._log_button.clicked.connect(self._on_log_button_clicked)
        right_layout.addWidget(self._log_button)

        # Checkbox "Do sprawdzenia"
        self.review_check = QCheckBox(t("kanban.column.review", "Do sprawdzenia"))
        self.review_check.stateChanged.connect(self._on_review_toggled)
        right_layout.addWidget(self.review_check)
        
        # Checkbox "Odłożone"
        self.on_hold_check = QCheckBox(t("kanban.column.on_hold", "Odłożone"))
        self.on_hold_check.stateChanged.connect(self._on_hold_toggled)
        right_layout.addWidget(self.on_hold_check)

        # Checkbox "Do wykonania" (domyślnie widoczna)
        self.todo_check = QCheckBox(t("kanban.column.todo", "Do wykonania"))
        self.todo_check.setChecked(True)
        self.todo_check.stateChanged.connect(self._on_todo_toggled)
        right_layout.addWidget(self.todo_check)

        # Checkbox "Ukończone" (domyślnie widoczna)
        self.done_check = QCheckBox(t("kanban.column.done", "Ukończone"))
        self.done_check.setChecked(True)
        self.done_check.stateChanged.connect(self._on_done_toggled)
        right_layout.addWidget(self.done_check)
        
        # Połącz panele
        bar_layout.addWidget(left_panel, 3)
        bar_layout.addWidget(right_panel, 2)
        
        return bar
    
    def _create_columns_section(self) -> QWidget:
        """Utwórz sekcję z kolumnami KanBan"""
        container = QWidget()
        container_layout = QHBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(10)
        
        # Zapisz referencję do layoutu dla późniejszego rebuildu
        self.columns_layout = container_layout
        
        # Kolumna 1: Do wykonania (TODO)
        self.todo_column = self._create_column("todo")
        container_layout.addWidget(self.todo_column)
        
        # Kolumna 2: W trakcie (IN PROGRESS)
        self.in_progress_column = self._create_column("in_progress")
        container_layout.addWidget(self.in_progress_column)
        
        # Kolumna 3: Zakończone (DONE)
        self.done_column = self._create_column("done")
        container_layout.addWidget(self.done_column)
        
        # Kolumna 4: Odłożone (ON HOLD) - opcjonalna
        self.on_hold_column = self._create_column("on_hold")
        self.on_hold_column.hide()
        container_layout.addWidget(self.on_hold_column)
        
        # Kolumna 5: Do sprawdzenia (REVIEW) - opcjonalna
        self.review_column = self._create_column("review")
        self.review_column.hide()
        container_layout.addWidget(self.review_column)
        
        # Zapisz referencje do kolumn
        self.columns = {
            'todo': self.todo_column,
            'in_progress': self.in_progress_column,
            'done': self.done_column,
            'on_hold': self.on_hold_column,
            'review': self.review_column
        }
        
        return container
    
    def _create_column(self, column_type: str) -> QGroupBox:
        """
        Utwórz pojedynczą kolumnę KanBan z drop zone support
        
        Args:
            column_type: Typ kolumny (todo, in_progress, done, on_hold, review)
        """
        title_key = self._get_column_title_key(column_type)
        column = QGroupBox(t(title_key, self._get_column_fallback(column_type)))
        column.setProperty('column_type', column_type)
        self._style_column(column, column_type)
        
        # Layout kolumny
        column_layout = QVBoxLayout()
        column_layout.setContentsMargins(5, 15, 5, 5)
        column_layout.setSpacing(5)
        
        # Scroll area dla zadań
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        # WAŻNE: QScrollArea musi też akceptować drops, aby przekazać je do child widget
        scroll.setAcceptDrops(True)
        if scroll.viewport():
            scroll.viewport().setAcceptDrops(True)
        
        # Kontener na karty zadań - z drop zone support
        if self.drag_drop_manager:
            from ..Modules.task_module.kanban_drag_and_drop_logic import DropZoneColumn
            tasks_container = DropZoneColumn(column_type)
            # Podłącz sygnał drop
            tasks_container.task_dropped.connect(self.drag_drop_manager.handle_task_dropped)
            logger.info(f"[KanBanView] Created DropZoneColumn for '{column_type}' with acceptDrops={tasks_container.acceptDrops()}")
        else:
            # Fallback gdy manager nie jest dostępny
            tasks_container = QWidget()
            logger.warning(f"[KanBanView] No drag_drop_manager - using plain QWidget for '{column_type}'")
        
        tasks_container.setObjectName(f"{column_type}_tasks")
        tasks_layout = QVBoxLayout(tasks_container)
        tasks_layout.setContentsMargins(0, 0, 0, 0)
        tasks_layout.setSpacing(5)
        tasks_layout.addStretch()
        
        scroll.setWidget(tasks_container)
        column_layout.addWidget(scroll)
        
        column.setLayout(column_layout)
        return column

    def _get_column_title_key(self, column_type: str) -> str:
        mapping = {
            'todo': 'kanban.column.todo',
            'in_progress': 'kanban.column.in_progress',
            'done': 'kanban.column.done',
            'on_hold': 'kanban.column.on_hold',
            'review': 'kanban.column.review',
        }
        return mapping.get(column_type, 'kanban.column.todo')

    def _get_column_fallback(self, column_type: str) -> str:
        return {
            'todo': 'Do wykonania',
            'in_progress': 'W trakcie',
            'done': 'Zakończone',
            'on_hold': 'Odłożone',
            'review': 'Do sprawdzenia',
        }.get(column_type, 'Do wykonania')

    def _get_hide_completed_options(self) -> List[Tuple[int, str]]:
        return [
            (0, t('kanban.settings.hide_never', 'Nigdy')),
            (1, t('kanban.settings.hide_1day', 'Po 1 dniu')),
            (5, t('kanban.settings.hide_5days', 'Po 5 dniach')),
            (14, t('kanban.settings.hide_14days', 'Po 14 dniach')),
            (-1, t('kanban.settings.hide_archived', 'Po archiwizacji')),
        ]

    def _populate_hide_combo(self, selected_value: int) -> None:
        options = self._get_hide_completed_options()
        self.hide_completed_combo.blockSignals(True)
        self.hide_completed_combo.clear()
        for value, label in options:
            self.hide_completed_combo.addItem(label, value)
        target_index = next((idx for idx, (value, _) in enumerate(options) if value == selected_value), 0)
        if target_index < 0 or target_index >= self.hide_completed_combo.count():
            target_index = 0
        self.hide_completed_combo.setCurrentIndex(target_index)
        self.hide_completed_combo.blockSignals(False)

    def update_translations(self) -> None:
        self._hide_label.setText(t('kanban.settings.hide_completed', 'Ukryj zakończone'))
        current_value = self.settings.get('hide_completed_after', self.hide_completed_combo.currentData() or 0)
        self._populate_hide_combo(current_value)

        self._max_label.setText(t('kanban.settings.max_in_progress', 'Maksymalnie w trakcie'))
        self.review_check.setText(t('kanban.column.review', 'Do sprawdzenia'))
        self.on_hold_check.setText(t('kanban.column.on_hold', 'Odłożone'))
        self.todo_check.setText(t('kanban.column.todo', 'Do wykonania'))
        self.done_check.setText(t('kanban.column.done', 'Ukończone'))
        if self._log_button:
            self._log_button.setText(t('kanban.log.button', 'Log'))

        for column_type, column in self.columns.items():
            column.setTitle(t(self._get_column_title_key(column_type), self._get_column_fallback(column_type)))

    def _on_language_changed(self, _: str) -> None:
        self.update_translations()

    def _on_log_button_clicked(self) -> None:
        if not self.db:
            return
        try:
            dialog = KanbanLogDialog(self.db, self)
            dialog.exec()
        except Exception as exc:
            logger.error(f"[KanBanView] Failed to open Kanban log dialog: {exc}")
    
    # ============================================================================
    # DRAG & DROP CALLBACKS
    # ============================================================================
    
    def _on_card_drag_finished(self, task_id: int, source_column: str, success: bool):
        """Callback po zakończeniu drag (success lub cancel)"""
        if not success:
            logger.debug(f"[KanBanView] Drag cancelled for task {task_id}")
        # Można dodać animację powrotu karty jeśli cancel
    
    def _on_drag_drop_success(self, task_id: int, from_column: str, to_column: str, position: int):
        """Callback po udanym przeniesieniu zadania przez drag & drop"""
        logger.info(f"[KanBanView] Drag & Drop success: task {task_id} moved {from_column} → {to_column}")
        
        # Odśwież board aby pokazać nową pozycję
        logger.debug(f"[KanBanView] Calling refresh_board() after drag & drop, _is_refreshing={self._is_refreshing}")
        self.refresh_board()
        
        # Emituj sygnał task_moved (dla synchronizacji)
        self.task_moved.emit(task_id, to_column, position)
    
    def _on_drag_drop_failed(self, task_id: int, from_column: str, to_column: str, reason: str):
        """Callback gdy przeniesienie przez drag & drop nie powiodło się"""
        logger.warning(f"[KanBanView] Drag & Drop failed: {reason}")
        
        # Pokaż komunikat błędu użytkownikowi
        QMessageBox.warning(
            self,
            t('kanban.drag.failed_title', 'Nie można przenieść'),
            t('kanban.drag.failed_message', f'Powód: {reason}')
        )

    def apply_theme(self, *, refresh: bool = True) -> None:
        self._current_colors = self._theme_manager.get_current_colors()
        self._apply_theme()
        if refresh and self.db:
            self.refresh_board()

    def _apply_theme(self) -> None:
        bg_main = self._color('bg_main', '#FFFFFF')
        text_primary = self._color('text_primary', '#1A1A1A')
        self.setStyleSheet(f"KanBanView {{ background-color: {bg_main}; color: {text_primary}; }}")
        self._apply_control_bar_theme()

        for column_type, column in self.columns.items():
            self._style_column(column, column_type)

    def _apply_control_bar_theme(self) -> None:
        control_bar = getattr(self, '_control_bar', None)
        if not control_bar:
            return

        bg_secondary = self._color('bg_secondary', '#F5F5F5')
        border = self._color('border_light', '#CCCCCC')
        text_primary = self._color('text_primary', '#1A1A1A')
        text_secondary = self._color('text_secondary', '#666666')
        accent = self._color('accent_primary', '#3B82F6')
        accent_hover = self._color('accent_hover', accent)

        control_bar.setStyleSheet(
            f"""
            QWidget#KanbanControlBar {{
                background-color: {bg_secondary};
                border-bottom: 1px solid {border};
            }}
            QLabel {{
                color: {text_secondary};
            }}
            QPushButton#KanbanLogButton {{
                background-color: {accent};
                color: #FFFFFF;
                border-radius: 6px;
                padding: 6px 14px;
                border: none;
            }}
            QPushButton#KanbanLogButton:hover:!disabled {{
                background-color: {accent_hover};
            }}
            QPushButton#KanbanLogButton:disabled {{
                background-color: {border};
                color: {text_secondary};
            }}
            """
        )

        combo_style = f"""
            QComboBox {{
                padding: 4px;
                border: 1px solid {border};
                border-radius: 4px;
                background-color: {self._color('bg_main', '#FFFFFF')};
                color: {text_primary};
            }}
            QComboBox QAbstractItemView {{
                background-color: {self._color('bg_main', '#FFFFFF')};
                color: {text_primary};
                selection-background-color: {self._color('accent_primary', '#2196F3')};
                selection-color: #FFFFFF;
            }}
        """
        self.hide_completed_combo.setStyleSheet(combo_style)

        spin_style = f"""
            QSpinBox {{
                padding: 4px 8px;
                border: 1px solid {border};
                border-radius: 4px;
                background-color: {self._color('bg_main', '#FFFFFF')};
                color: {text_primary};
            }}
        """
        self.max_in_progress_spin.setStyleSheet(spin_style)

        checkbox_style = f"QCheckBox {{ color: {text_primary}; }}"
        for checkbox in (self.review_check, self.on_hold_check, self.todo_check, self.done_check):
            checkbox.setStyleSheet(checkbox_style)

    def _style_column(self, column: QGroupBox, column_type: str) -> None:
        palette = self._resolve_column_palette(column_type)
        bg_secondary = self._color('bg_secondary', '#F5F5F5')
        column.setStyleSheet(
            f"""
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {palette['border']};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {bg_secondary};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                background-color: {palette['header_bg']};
                color: {palette['header_text']};
                border-radius: 3px;
            }}
        """
        )

    def _resolve_column_palette(self, column_type: str) -> Dict[str, str]:
        accent_primary = self._color('accent_primary', '#2196F3')
        accent_hover = self._color('accent_hover', '#1976D2')
        accent_pressed = self._color('accent_pressed', '#0D47A1')
        border_light = self._color('border_light', '#CCCCCC')
        border_dark = self._color('border_dark', '#999999')
        text_secondary = self._color('text_secondary', '#666666')

        if column_type == 'todo':
            header_bg = accent_primary
        elif column_type == 'in_progress':
            header_bg = accent_hover
        elif column_type == 'done':
            header_bg = accent_pressed
        elif column_type == 'review':
            header_bg = accent_primary
        else:  # on_hold and fallback
            header_bg = border_dark

        border_color = header_bg if column_type in {'todo', 'in_progress', 'done', 'review'} else border_dark
        header_text = '#000000' if self._is_color_bright(header_bg) else '#FFFFFF'
        if column_type == 'on_hold':
            header_text = '#000000' if self._is_color_bright(header_bg) else '#FFFFFF'
            border_color = border_light
        if column_type == 'review':
            border_color = accent_hover

        return {
            'border': border_color,
            'header_bg': header_bg,
            'header_text': header_text,
        }

    def _apply_card_theme(self, card: QFrame, column_type: Optional[str] = None, *, highlighted: bool = False) -> None:
        card_type = column_type or card.property('column_type') or 'todo'
        base_bg = self._color('bg_secondary', '#FFFFFF')
        border = self._color('border_light', '#CCCCCC')
        hover_border = self._resolve_column_palette(card_type)['border']

        if card_type == 'done' or highlighted:
            base_bg = self._color('bg_secondary', '#F5F5F5')
            border = self._color('border_dark', '#E0E0E0')

        card.setStyleSheet(
            f"""
            QFrame {{
                background-color: {base_bg};
                border: 1px solid {border};
                border-radius: 5px;
                padding: 10px;
            }}
            QFrame:hover {{
                border: 2px solid {hover_border};
            }}
        """
        )

    def _color(self, key: str, fallback: str) -> str:
        colors = self._current_colors or {}
        return colors.get(key, fallback)

    def _is_color_bright(self, hex_color: str) -> bool:
        try:
            value = hex_color.lstrip('#')
            if len(value) != 6:
                return False
            r = int(value[0:2], 16)
            g = int(value[2:4], 16)
            b = int(value[4:6], 16)
            brightness = (r * 299 + g * 587 + b * 114) / 1000
            return brightness > 186
        except (ValueError, TypeError):
            return False
    
    def set_task_logic(self, task_logic):
        """Ustaw logikę zadań"""
        self.task_logic = task_logic
        if hasattr(task_logic, 'db'):
            self.db = task_logic.db
            self._load_settings()
            
            # Inicjalizacja Drag & Drop Manager
            if self.db and not self.drag_drop_manager:
                from ..Modules.task_module.kanban_drag_and_drop_logic import KanbanDragDropManager
                self.drag_drop_manager = KanbanDragDropManager(self.db, self.settings, self)
                self.drag_drop_manager.task_moved_successfully.connect(self._on_drag_drop_success)
                self.drag_drop_manager.task_move_failed.connect(self._on_drag_drop_failed)
                logger.info("[KanBanView] Drag & Drop Manager initialized")
                
                # WAŻNE: Przebuduj kolumny aby używały DropZoneColumn
                self._rebuild_columns()
            
            self.refresh_board()
            if self._log_button:
                self._log_button.setEnabled(self.db is not None)
        elif self._log_button:
            self._log_button.setEnabled(False)
        logger.info("[KanBanView] Task logic set")
    
    def _load_settings(self):
        """Wczytaj ustawienia KanBan z bazy"""
        if not self.db:
            return
        
        try:
            settings = self.db.get_kanban_settings()

            # Zaktualizuj ustawienia w pamięci uwzględniając nowe przełączniki widoczności
            self.settings.update(settings)
            if 'show_todo' not in self.settings:
                self.settings['show_todo'] = True
            if 'show_done' not in self.settings:
                self.settings['show_done'] = True
            
            # Aktualizuj UI
            self.max_in_progress_spin.setValue(settings.get('max_in_progress', 3))
            
            hide_days = settings.get('hide_completed_after', 0)
            if hide_days == 0:
                self.hide_completed_combo.setCurrentText(t("kanban.settings.hide_never"))
            elif hide_days == 1:
                self.hide_completed_combo.setCurrentText(t("kanban.settings.hide_1day"))
            elif hide_days == 5:
                self.hide_completed_combo.setCurrentText(t("kanban.settings.hide_5days"))
            elif hide_days == 14:
                self.hide_completed_combo.setCurrentText(t("kanban.settings.hide_14days"))
            elif hide_days == -1:
                self.hide_completed_combo.setCurrentText(t("kanban.settings.hide_archived"))
            
            show_on_hold = self.settings.get('show_on_hold', False)
            self.on_hold_check.blockSignals(True)
            self.on_hold_check.setChecked(show_on_hold)
            self.on_hold_check.blockSignals(False)
            if show_on_hold:
                self.on_hold_column.show()
            else:
                self.on_hold_column.hide()
            
            show_review = self.settings.get('show_review', False)
            self.review_check.blockSignals(True)
            self.review_check.setChecked(show_review)
            self.review_check.blockSignals(False)
            if show_review:
                self.review_column.show()
            else:
                self.review_column.hide()

            show_todo = self.settings.get('show_todo', True)
            self.todo_check.blockSignals(True)
            self.todo_check.setChecked(show_todo)
            self.todo_check.blockSignals(False)
            self.todo_column.setVisible(show_todo)

            show_done = self.settings.get('show_done', True)
            self.done_check.blockSignals(True)
            self.done_check.setChecked(show_done)
            self.done_check.blockSignals(False)
            self.done_column.setVisible(show_done)
            
            logger.info(f"[KanBanView] Settings loaded: {settings}")
            
        except Exception as e:
            logger.error(f"[KanBanView] Failed to load settings: {e}")
    
    def _save_settings(self):
        """Zapisz ustawienia KanBan do bazy"""
        if not self.db:
            return
        
        try:
            self.db.update_kanban_settings(self.settings)
            self.settings_changed.emit(self.settings)
            
            # Update drag_drop_manager settings
            if self.drag_drop_manager:
                self.drag_drop_manager.settings = self.settings
                logger.debug("[KanBanView] DragDropManager settings updated")
            
            logger.info(f"[KanBanView] Settings saved: {self.settings}")
        except Exception as e:
            logger.error(f"[KanBanView] Failed to save settings: {e}")
    
    def _rebuild_columns(self):
        """Przebuduj kolumny aby używały DropZoneColumn po inicjalizacji managera"""
        logger.info("[KanBanView] Rebuilding columns with Drag & Drop support")
        
        # Usuń stare kolumny z layoutu
        while self.columns_layout.count():
            item = self.columns_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        self.columns.clear()
        
        # Utwórz kolumny na nowo (tym razem z DropZoneColumn)
        column_types = ['todo', 'in_progress', 'done', 'on_hold', 'review']
        for col_type in column_types:
            column = self._create_column(col_type)
            self.columns[col_type] = column
            self.columns_layout.addWidget(column)
            
            # Ustaw widoczność na podstawie ustawień
            show_key = f'show_{col_type}'
            if show_key in self.settings:
                column.setVisible(self.settings[show_key])
        
        logger.info("[KanBanView] Columns rebuilt successfully")
    
    def refresh_board(self):
        """Odśwież wszystkie kolumny"""
        # Zapobiegnij rekurencyjnemu odświeżaniu
        if self._is_refreshing:
            logger.debug("[KanBanView] Refresh already in progress, skipping")
            return
            
        if not self.db:
            logger.warning("[KanBanView] Cannot refresh board - no database")
            return
        
        try:
            self._is_refreshing = True
            
            # Pobierz wszystkie zadania z KanBan
            items = self.db.get_kanban_items()

            # Zsynchronizuj kolumny z aktualnym statusem zadań
            if self._sync_task_status_with_columns(items):
                items = self.db.get_kanban_items()
            
            # Grupuj według kolumn
            columns_data = {
                'todo': [],
                'in_progress': [],
                'done': [],
                'on_hold': [],
                'review': []
            }
            
            for item in items:
                col_type = item.get('column_type', 'todo')
                if col_type in columns_data:
                    columns_data[col_type].append(item)
            
            # Odśwież każdą kolumnę
            total_items = 0
            for col_type, column_items in columns_data.items():
                self._populate_column(col_type, column_items)
                total_items += len(column_items)

            logger.info(f"[KanBanView] Board refreshed with {total_items} total items")
            
        except Exception as e:
            logger.error(f"[KanBanView] Failed to refresh board: {e}")
        finally:
            # Zawsze resetuj flagę po zakończeniu
            self._is_refreshing = False

    def _sync_task_status_with_columns(self, items: List[Dict[str, Any]]) -> bool:
        """Ensure KanBan columns match task completion status."""
        if not self.db:
            return False

        # Zbierz wszystkie zmiany przed wykonaniem
        pending_moves = []
        
        for item in items:
            task_id = item.get('task_id')
            if not task_id:
                continue

            column_type = item.get('column_type', 'todo')
            status_flag = bool(item.get('status'))

            if status_flag and column_type != 'done':
                pending_moves.append({
                    'task_id': task_id,
                    'from_column': column_type,
                    'to_column': 'done',
                    'reason': 'completion'
                })
            elif not status_flag and column_type == 'done':
                target_column = self._select_reopen_column(item)
                pending_moves.append({
                    'task_id': task_id,
                    'from_column': 'done',
                    'to_column': target_column,
                    'reason': 'reopen'
                })

        # Wykonaj wszystkie zmiany po obliczeniu pozycji
        changes_made = False
        for move in pending_moves:
            # Oblicz pozycję tuż przed zapisem
            position = self._get_next_position(move['to_column'])
            
            if self.db.move_kanban_item(move['task_id'], move['to_column'], position):
                changes_made = True
                logger.info(
                    f"[KanBanView] Auto-moved task {move['task_id']} from '{move['from_column']}' to '{move['to_column']}' ({move['reason']})"
                )
                self.task_moved.emit(move['task_id'], move['from_column'], move['to_column'])
            else:
                logger.warning(
                    f"[KanBanView] Failed to auto-move task {move['task_id']} from '{move['from_column']}' to '{move['to_column']}'"
                )

        return changes_made

    def _select_reopen_column(self, item: Dict[str, Any]) -> str:
        """Pick target column for a task that left the done state."""
        preferred_column = None
        custom_data = item.get('custom_data') or {}

        if isinstance(custom_data, dict):
            preferred_column = custom_data.get('kanban_previous_column')

        if preferred_column == 'done':
            preferred_column = None

        if preferred_column not in self.columns:
            preferred_column = None

        if preferred_column:
            return preferred_column

        for candidate in ('in_progress', 'todo', 'review', 'on_hold'):
            if candidate in self.columns and candidate != 'done':
                return candidate

        for name in self.columns:
            if name != 'done':
                return name

        return 'todo'
    
    def _populate_column(self, column_type: str, items: List[Dict[str, Any]]):
        """
        Wypełnij kolumnę kartami zadań
        
        Args:
            column_type: Typ kolumny
            items: Lista zadań do wyświetlenia
        """
        column = self.columns.get(column_type)
        if not column:
            return
        
        # Znajdź kontener zadań
        tasks_container = column.findChild(QWidget, f"{column_type}_tasks")
        if not tasks_container:
            return
        
        # Wyczyść istniejące karty
        layout = tasks_container.layout()
        if layout is None:
            return

        while layout.count() > 1:  # Zostaw stretch na końcu
            item = layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()
        
        # Filtruj zadania - tylko główne zadania (bez parent_id) lub subtaski jeśli są dodane bezpośrednio
        # Pobierz pełne informacje o zadaniach
        if self.db:
            main_tasks: List[Dict[str, Any]] = []
            for task_item in items:
                task_id = task_item.get('task_id')
                # Pobierz pełne dane zadania
                full_task = self.db.get_task_by_id(task_id)
                if full_task:
                    # Sprawdź czy to główne zadanie (parent_id is None)
                    # Jeśli ma parent_id, ale parent NIE jest na KanBan, to też wyświetl
                    parent_id = full_task.get('parent_id')
                    if parent_id is None:
                        # Główne zadanie - zawsze wyświetl
                        enriched_item = dict(task_item)
                        enriched_item['full_task'] = full_task
                        main_tasks.append(enriched_item)
                    else:
                        # Subtask - wyświetl tylko jeśli parent NIE jest na KanBan
                        parent_on_kanban = any(item.get('task_id') == parent_id for item in items)
                        if not parent_on_kanban:
                            enriched_item = dict(task_item)
                            enriched_item['full_task'] = full_task
                            main_tasks.append(enriched_item)
        else:
            main_tasks = items
        
        # Zastosuj filtry
        filtered_tasks = self._apply_column_filters(column_type, main_tasks)
        
        # Dodaj karty zadań
        for task_item in sorted(filtered_tasks, key=lambda x: x.get('position', 0)):
            card = self._create_task_card(column_type, task_item)
            if isinstance(layout, QVBoxLayout):
                layout.insertWidget(layout.count() - 1, card)
            else:
                layout.addWidget(card)
        
        logger.debug(f"[KanBanView] Populated column '{column_type}' with {len(filtered_tasks)} cards ({len(items)} total items)")

    def _apply_column_filters(self, column_type: str, tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Zastosuj filtry do zadań w kolumnie
        
        Args:
            column_type: Typ kolumny
            tasks: Lista zadań do przefiltrowania
            
        Returns:
            Przefiltrowana lista zadań
        """
        filtered = list(tasks)
        
        # Filtr 1: Ukryj zakończone po określonym czasie (tylko dla kolumny 'done')
        if column_type == 'done':
            hide_after_days = self.settings.get('hide_completed_after', 0)
            
            if hide_after_days == -1:
                # Ukryj wszystkie zarchiwizowane
                filtered = [t for t in filtered if not t.get('full_task', {}).get('archived', False)]
            elif hide_after_days > 0:
                # Ukryj zadania zakończone ponad X dni temu
                from datetime import datetime, timedelta
                now = datetime.now()
                cutoff_date = now - timedelta(days=hide_after_days)
                
                remaining = []
                for task in filtered:
                    full_task = task.get('full_task', {})
                    completion_date_str = full_task.get('completion_date') or task.get('completion_date')
                    
                    if completion_date_str:
                        try:
                            # Parsuj datę zakończenia
                            if 'T' in str(completion_date_str):
                                completion_date = datetime.fromisoformat(completion_date_str.replace('Z', '+00:00'))
                            elif ' ' in str(completion_date_str):
                                completion_date = datetime.strptime(completion_date_str, '%Y-%m-%d %H:%M:%S')
                            else:
                                completion_date = datetime.strptime(completion_date_str, '%Y-%m-%d')
                            
                            # Zachowaj tylko zadania zakończone po cutoff_date
                            if completion_date >= cutoff_date:
                                remaining.append(task)
                        except (ValueError, AttributeError) as e:
                            logger.debug(f"[KanBanView] Could not parse completion_date '{completion_date_str}': {e}")
                            # Jeśli nie można sparsować, zachowaj zadanie
                            remaining.append(task)
                    else:
                        # Brak daty zakończenia - zachowaj
                        remaining.append(task)
                
                filtered = remaining
        
        # Filtr 2: Limit zadań w kolumnie "W trakcie"
        if column_type == 'in_progress':
            max_in_progress = self.settings.get('max_in_progress', 3)
            if max_in_progress > 0 and len(filtered) > max_in_progress:
                # Ogranicz do max_in_progress (zachowaj pierwsze według position)
                filtered = filtered[:max_in_progress]
                logger.info(f"[KanBanView] Limited 'in_progress' to {max_in_progress} tasks")
        
        return filtered

    
    def _create_task_card(self, column_type: str, task: Dict[str, Any]) -> QFrame:
        """Zbuduj kartę zadania dopasowaną do typu kolumny."""
        if column_type == 'todo':
            return self._build_todo_card(task)
        if column_type == 'in_progress':
            return self._build_in_progress_card(task)
        if column_type == 'done':
            return self._build_done_card(task)
        return self._build_generic_card(column_type, task)

    def _create_base_card(self, column_type: str, task_id: Optional[int]) -> Tuple[QFrame, QVBoxLayout]:
        """Utwórz bazową kartę - z drag&drop jeśli dostępne"""
        
        # Utwórz kartę z drag&drop support jeśli manager jest dostępny
        if task_id and self.drag_drop_manager:
            from ..Modules.task_module.kanban_drag_and_drop_logic import DraggableTaskCard
            card = DraggableTaskCard(task_id, column_type)
            # Podłącz sygnały drag
            card.drag_started.connect(self.drag_drop_manager.handle_drag_started)
            card.drag_finished.connect(self._on_card_drag_finished)
        else:
            # Fallback dla kart bez task_id lub gdy manager nie jest dostępny
            card = QFrame()
        
        card.setFrameShape(QFrame.Shape.StyledPanel)
        card.setProperty('task_id', task_id)
        card.setProperty('column_type', column_type)
        self._apply_card_theme(card, column_type)
        
        layout = QVBoxLayout()
        layout.setContentsMargins(6, 6, 6, 6)
        layout.setSpacing(6)
        card.setLayout(layout)
        return card, layout

    def _build_todo_card(self, task: Dict[str, Any]) -> QFrame:
        full_task = task.get('full_task') or {}
        task_id = task.get('task_id') or full_task.get('id')
        if not task_id:
            return self._build_generic_card('todo', task)

        card, layout = self._create_base_card('todo', task_id)

        primary_text = self._color('text_primary', '#1A1A1A')
        secondary_text = self._color('text_secondary', '#757575')
        accent_primary = self._color('accent_primary', '#1E88E5')
        accent_hover = self._color('accent_hover', '#1565C0')
        danger_color = self._color('danger', '#E53935')
        danger_hover = self._color('danger_hover', '#D32F2F')
        danger_text = '#000000' if self._is_color_bright(danger_color) else '#FFFFFF'
        accent_text = '#000000' if self._is_color_bright(accent_primary) else '#FFFFFF'

        created_at = self._format_datetime(task.get('task_created_at'))
        created_label = QLabel(t('kanban.card.added_at').format(created_at))
        created_label.setStyleSheet(f"color: {secondary_text}; font-size: 11px;")
        layout.addWidget(created_label)

        row_layout = QHBoxLayout()
        row_layout.setSpacing(6)

        title_label = QLabel(task.get('title', t('kanban.card.no_title')))
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {primary_text};")
        row_layout.addWidget(title_label, 1)

        remove_btn = QPushButton("←")
        remove_btn.setToolTip(t('kanban.card.remove'))
        remove_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {danger_color};
                color: {danger_text};
                border: none;
                border-radius: 4px;
                padding: 4px;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }}
            QPushButton:hover {{
                background-color: {danger_hover};
            }}
        """
        )
        remove_btn.clicked.connect(
            lambda _, tid=task_id, src=task.get('column_type', 'todo'): self._on_remove_from_kanban(tid, src)
        )
        row_layout.addWidget(remove_btn)

        move_btn = QPushButton("→")
        move_btn.setToolTip(t('kanban.card.move_to_in_progress'))
        move_btn.setStyleSheet(
            f"""
            QPushButton {{
                background-color: {accent_primary};
                color: {accent_text};
                border: none;
                border-radius: 4px;
                padding: 4px;
                min-width: 28px;
                max-width: 28px;
                min-height: 28px;
                max-height: 28px;
            }}
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
        """
        )
        move_btn.clicked.connect(
            lambda _, tid=task_id, src=task.get('column_type', 'todo'): self._on_move_task(tid, src, 'in_progress')
        )
        row_layout.addWidget(move_btn)

        layout.addLayout(row_layout)

        task_payload = dict(task)
        task_payload['column_type'] = 'todo'
        task_payload.setdefault('task_id', task_id)
        if full_task:
            task_payload.setdefault('full_task', full_task)
            task_payload.setdefault('title', full_task.get('title', task.get('title')))
        self._attach_card_context_menu(card, task_payload)
        self._register_card_double_click(card, task_payload)
        return card

    def _build_in_progress_card(self, task: Dict[str, Any]) -> QFrame:
        full_task = task.get('full_task') or {}
        task_id = task.get('task_id') or full_task.get('id')
        if not task_id:
            return self._build_generic_card('in_progress', task)

        card, layout = self._create_base_card('in_progress', task_id)

        primary_text = self._color('text_primary', '#1A1A1A')
        secondary_text = self._color('text_secondary', '#757575')
        accent_primary = self._color('accent_primary', '#1E88E5')
        accent_hover = self._color('accent_hover', '#1565C0')
        accent_text = '#000000' if self._is_color_bright(accent_primary) else '#FFFFFF'
        toggle_bg = self._color('bg_main', '#FFFFFF')
        border = self._color('border_light', '#CCCCCC')

        header_layout = QHBoxLayout()
        header_layout.setSpacing(6)

        toggle_btn = QToolButton()
        toggle_btn.setText("⬇")
        toggle_btn.setToolTip(t('kanban.card.toggle_subtasks'))
        toggle_btn.setPopupMode(QToolButton.ToolButtonPopupMode.MenuButtonPopup)
        toggle_btn.setStyleSheet(
            f"QToolButton {{ background-color: {toggle_bg}; border: 1px solid {border}; border-radius: 4px; padding: 4px; color: {primary_text}; }}"
        )
        toggle_btn.clicked.connect(
            lambda _, tid=task_id, c=card: self._toggle_subtasks_in_card(tid, c)
        )
        menu = QMenu(toggle_btn)
        add_action = QAction(t('kanban.card.add_subtask'), toggle_btn)
        add_action.triggered.connect(lambda _, tid=task_id: self._on_add_subtask_requested(tid))
        menu.addAction(add_action)
        toggle_btn.setMenu(menu)
        header_layout.addWidget(toggle_btn)

        title_label = QLabel(task.get('title', t('kanban.card.no_title')))
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"font-weight: 600; font-size: 13px; color: {primary_text};")
        header_layout.addWidget(title_label, 1)

        header_layout.addStretch()

        note_button = self._create_note_button(full_task)
        if note_button is not None:
            header_layout.addWidget(note_button)

        status_checkbox = QCheckBox()
        status_checkbox.setToolTip(t('kanban.card.mark_done'))
        status_checkbox.blockSignals(True)
        status_checkbox.setChecked(bool(full_task.get('status')))
        status_checkbox.blockSignals(False)
        status_checkbox.setStyleSheet(f"QCheckBox {{ color: {primary_text}; }}")
        status_checkbox.stateChanged.connect(
            lambda state, tid=task_id, src=task.get('column_type', 'in_progress'): self._on_progress_status_changed(tid, state, src)
        )
        header_layout.addWidget(status_checkbox)

        layout.addLayout(header_layout)

        created_at = self._format_datetime(task.get('task_created_at'))
        created_label = QLabel(t('kanban.card.added_at').format(created_at))
        created_label.setStyleSheet(f"color: {secondary_text}; font-size: 11px;")
        layout.addWidget(created_label)

        subtasks_container = QWidget()
        subtasks_container.setObjectName(f"subtasks_{task_id}")
        subtasks_container.setVisible(False)
        subtasks_layout = QVBoxLayout()
        subtasks_layout.setContentsMargins(16, 4, 0, 4)
        subtasks_layout.setSpacing(3)
        subtasks_container.setLayout(subtasks_layout)
        layout.addWidget(subtasks_container)

        task_payload = dict(task)
        task_payload['column_type'] = 'in_progress'
        task_payload.setdefault('task_id', task_id)
        if full_task:
            task_payload.setdefault('full_task', full_task)
            task_payload.setdefault('title', full_task.get('title', task.get('title')))
        self._attach_card_context_menu(card, task_payload)
        self._register_card_double_click(card, task_payload)

        return card

    def _build_done_card(self, task: Dict[str, Any]) -> QFrame:
        full_task = task.get('full_task') or {}
        task_id = task.get('task_id') or full_task.get('id')
        if not task_id:
            return self._build_generic_card('done', task)

        card, layout = self._create_base_card('done', task_id)
        card.setStyleSheet("""
            QFrame {
                background-color: #F5F5F5;
                border: 1px solid #E0E0E0;
                border-radius: 5px;
                padding: 10px;
            }
        """)

        title_label = QLabel(task.get('title', t('kanban.card.no_title')))
        title_label.setWordWrap(True)
        title_label.setStyleSheet("color: #616161; text-decoration: line-through; font-style: italic;")
        layout.addWidget(title_label)

        completion_raw = task.get('completion_date') or full_task.get('completion_date')
        completion_label = QLabel(t('kanban.card.completed_at').format(self._format_datetime(completion_raw)))
        completion_label.setStyleSheet("color: #757575; font-size: 11px;")
        layout.addWidget(completion_label)

        layout.addStretch()

        task_payload = dict(task)
        task_payload['column_type'] = 'done'
        task_payload.setdefault('task_id', task_id)
        if full_task:
            task_payload.setdefault('full_task', full_task)
            task_payload.setdefault('title', full_task.get('title', task.get('title')))
        self._attach_card_context_menu(card, task_payload)
        self._register_card_double_click(card, task_payload)

        return card

    def _build_generic_card(self, column_type: str, task: Dict[str, Any]) -> QFrame:
        task_id = task.get('task_id') or (task.get('full_task') or {}).get('id') or 0
        card, layout = self._create_base_card(column_type, task_id)

        title_label = QLabel(task.get('title', t('kanban.card.no_title')))
        title_label.setWordWrap(True)
        title_label.setStyleSheet("font-weight: 600; font-size: 13px;")
        layout.addWidget(title_label)

        info_label = QLabel(f"{t('kanban.card.id')} {task_id}")
        info_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info_label)

        layout.addStretch()

        task_payload = dict(task)
        task_payload.setdefault('column_type', column_type)
        task_payload.setdefault('task_id', task_id)
        if task.get('full_task'):
            task_payload.setdefault('full_task', task.get('full_task'))
            task_payload.setdefault('title', task.get('full_task').get('title', task.get('title')))
        self._attach_card_context_menu(card, task_payload)
        self._register_card_double_click(card, task_payload)

        return card

    def _attach_card_context_menu(self, card: QFrame, task_data: Dict[str, Any]) -> None:
        if not self.context_menu:
            return
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, frame=card, data=dict(task_data): self._show_card_context_menu(frame, pos, data)
        )

    def _register_card_double_click(self, card: QFrame, task_data: Dict[str, Any]) -> None:
        """Podłącz obsługę podwójnego kliknięcia do karty zadania."""
        if not card:
            return

        payload = dict(task_data or {})
        if 'task_id' not in payload or not payload.get('task_id'):
            payload['task_id'] = card.property('task_id')

        full_task = payload.get('full_task') if isinstance(payload.get('full_task'), dict) else None
        if not payload.get('title'):
            if full_task:
                payload['title'] = full_task.get('title', '')
            else:
                payload['title'] = task_data.get('title', '') if isinstance(task_data, dict) else ''

        card.setProperty('task_payload', payload)
        card.installEventFilter(self)
        for child in card.findChildren(QWidget):
            if isinstance(child, (QPushButton, QToolButton, QCheckBox)):
                continue
            child.setProperty('task_card_ref', card)
            child.installEventFilter(self)

    def _show_card_context_menu(self, card: QFrame, pos, task_data: Dict[str, Any]) -> None:
        if not self.context_menu:
            return
        global_pos = card.mapToGlobal(pos)
        payload = dict(task_data or {})
        if 'column_type' not in payload or not payload['column_type']:
            payload['column_type'] = card.property('column_type')
        if 'task_id' not in payload or not payload['task_id']:
            payload['task_id'] = card.property('task_id')
        self.context_menu.show_menu(card, global_pos, payload)

    def eventFilter(self, watched: QObject, event: QEvent) -> bool:  # type: ignore[override]
        target_card: Optional[QFrame] = None
        if isinstance(watched, QFrame):
            target_card = watched
        elif isinstance(watched, QWidget):
            parent_card = watched.property('task_card_ref') if hasattr(watched, 'property') else None
            if isinstance(parent_card, QFrame):
                target_card = parent_card

        if target_card and event and event.type() == QEvent.Type.MouseButtonDblClick:
            if isinstance(event, QMouseEvent) and event.button() == Qt.MouseButton.LeftButton:
                payload = target_card.property('task_payload') or {}
                self._handle_card_double_click(target_card, payload if isinstance(payload, dict) else {})
                return True
        return super().eventFilter(watched, event)

    def _handle_card_double_click(self, card: QFrame, task_payload: Dict[str, Any]) -> None:
        """Obsłuż edycję zadania po podwójnym kliknięciu."""
        if not task_payload:
            logger.debug("[KanBanView] Double-click ignored: empty task payload")
            return

        task_id = (
            task_payload.get('task_id')
            or task_payload.get('id')
            or (task_payload.get('full_task') or {}).get('id')
        )

        if not task_id:
            logger.warning("[KanBanView] Cannot edit task without valid task_id")
            return

        current_title = task_payload.get('title')
        if not current_title and isinstance(task_payload.get('full_task'), dict):
            current_title = task_payload['full_task'].get('title', '')
        current_title = current_title or ''

        accepted, new_title = TaskEditDialog.prompt(self, task_title=current_title)
        if not accepted:
            return

        new_title = (new_title or '').strip()
        if not new_title:
            QMessageBox.warning(
                self,
                t('kanban.edit.validation_title', 'Nieprawidłowa treść'),
                t('kanban.edit.validation_message', 'Treść zadania nie może być pusta.'),
            )
            return

        if new_title == current_title.strip():
            logger.debug("[KanBanView] Task title unchanged; skipping update")
            return

        if not self.db:
            QMessageBox.warning(
                self,
                t('kanban.edit.db_missing_title', 'Baza niedostępna'),
                t('kanban.edit.db_missing_message', 'Lokalna baza zadań jest niedostępna.'),
            )
            return

        try:
            update_success = self.db.update_task(task_id, title=new_title)
        except Exception as exc:
            logger.error(f"[KanBanView] Failed to update task {task_id}: {exc}")
            QMessageBox.critical(
                self,
                t('kanban.edit.update_error_title', 'Błąd aktualizacji'),
                t('kanban.edit.update_error_message', 'Nie udało się zapisać zmian zadania.'),
            )
            return

        if not update_success:
            logger.error(f"[KanBanView] Database declined task update for {task_id}")
            QMessageBox.warning(
                self,
                t('kanban.edit.update_failed_title', 'Aktualizacja nie powiodła się'),
                t('kanban.edit.update_failed_message', 'Nie udało się zaktualizować zadania.'),
            )
            return

        if self.task_logic and hasattr(self.task_logic, 'update_task'):
            try:
                self.task_logic.update_task(task_id, {'title': new_title})
            except Exception as exc:
                logger.debug(f"[KanBanView] task_logic update_task raised: {exc}")

        card_payload = dict(task_payload)
        card_payload['title'] = new_title
        card.setProperty('task_payload', card_payload)

        logger.info(f"[KanBanView] Task {task_id} title updated via double-click")
        self.refresh_board()

    def _create_note_button(self, task_data: Dict[str, Any]) -> Optional[QPushButton]:
        task_id = task_data.get('id') if isinstance(task_data, dict) else None
        if not task_id:
            return None

        btn = QPushButton("📝")
        btn.setFixedSize(32, 28)

        note_id = task_data.get('note_id')
        if note_id:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #4CAF50;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #45A049;
                }
            """)
            btn.setToolTip(t('tasks.note.open'))
        else:
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #2196F3;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    font-size: 14px;
                }
                QPushButton:hover {
                    background-color: #1976D2;
                }
                QPushButton:pressed {
                    background-color: #0D47A1;
                }
            """)
            btn.setToolTip(t('tasks.note.create'))

        btn.clicked.connect(lambda _, tid=task_id: self.open_task_note(tid))
        return btn

    def _format_datetime(self, value: Optional[Any]) -> str:
        if value in (None, ""):
            return "-"

        if isinstance(value, datetime):
            dt = value
        else:
            str_value = str(value).strip()
            if str_value.endswith('Z'):
                str_value = str_value[:-1]
            try:
                dt = datetime.fromisoformat(str_value)
            except ValueError:
                try:
                    dt = datetime.strptime(str_value, "%Y-%m-%d %H:%M:%S.%f")
                except ValueError:
                    try:
                        dt = datetime.strptime(str_value, "%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        return str_value
        return dt.strftime("%d.%m.%Y %H:%M")

    def _on_remove_from_kanban(self, task_id: Optional[int], source_column: str):
        if not task_id or not self.db:
            return
        if self.db.remove_task_from_kanban(task_id):
            logger.info(f"[KanBanView] Removed task {task_id} from KanBan")
            self.refresh_board()
            self.task_moved.emit(task_id, source_column, '')
        else:
            logger.error(f"[KanBanView] Failed to remove task {task_id} from KanBan")

    def _on_move_task(self, task_id: Optional[int], source_column: str, target_column: str):
        if not task_id or not self.db:
            return
        position = self._get_next_position(target_column)
        if self.db.move_kanban_item(task_id, target_column, position):
            logger.info(f"[KanBanView] Moved task {task_id} to column '{target_column}'")
            self.refresh_board()
            self.task_moved.emit(task_id, source_column, target_column)
        else:
            logger.error(f"[KanBanView] Failed to move task {task_id} to column '{target_column}'")

    def _get_next_position(self, column_type: str) -> int:
        if not self.db:
            return 0
        items = self.db.get_kanban_items(column_type)
        if not items:
            return 0
        try:
            return max(int(item.get('position', 0)) for item in items) + 1
        except Exception:
            return len(items)

    def _on_progress_status_changed(self, task_id: Optional[int], state: int, source_column: str):
        if state == Qt.CheckState.Checked.value:
            self._mark_task_done(task_id, source_column)

    def _mark_task_done(self, task_id: Optional[int], source_column: str):
        if not task_id or not self.db:
            return
        try:
            update_success = self.db.update_task(task_id, status=1)
        except Exception as exc:
            logger.error(f"[KanBanView] Failed to update task status for {task_id}: {exc}")
            return

        if not update_success:
            logger.error(f"[KanBanView] Database declined status update for task {task_id}")
            return

        position = self._get_next_position('done')
        if not self.db.move_kanban_item(task_id, 'done', position):
            logger.error(f"[KanBanView] Failed to move task {task_id} to 'done' column")
            return

        logger.info(f"[KanBanView] Task {task_id} marked as done")
        self.refresh_board()
        self.task_moved.emit(task_id, source_column, 'done')

    def _on_add_subtask_requested(self, parent_task_id: Optional[int]):
        if not parent_task_id:
            return
        if self.add_subtask:
            try:
                self.add_subtask(parent_task_id)
            except Exception as exc:
                logger.error(f"[KanBanView] Failed to add subtask for task {parent_task_id}: {exc}")
            finally:
                self.refresh_board()
        else:
            logger.info(f"[KanBanView] Subtask handler not set for task {parent_task_id}")
    
    def _toggle_subtasks_in_card(self, task_id: int, card: QFrame):
        """
        Rozwiń/zwiń subtaski w karcie zadania
        
        Args:
            task_id: ID głównego zadania
            card: Karta (QFrame) zadania
        """
        if not self.db:
            return
            
        try:
            # Znajdź kontener subtasków
            subtasks_container = card.findChild(QWidget, f"subtasks_{task_id}")
            if not subtasks_container:
                logger.warning(f"[KanBanView] Subtasks container not found for task {task_id}")
                return
            
            # Toggle widoczności
            is_visible = subtasks_container.isVisible()
            
            if is_visible:
                # Zwiń subtaski
                subtasks_container.setVisible(False)
                logger.debug(f"[KanBanView] Collapsed subtasks for task {task_id}")
            else:
                # Rozwiń subtaski - pobierz i wyświetl
                subtasks = self.db.get_tasks(parent_id=task_id, include_archived=False)
                
                # Wyczyść poprzednie subtaski
                layout = subtasks_container.layout()
                if layout is None:
                    return
                while layout.count():
                    item = layout.takeAt(0)
                    widget = item.widget() if item else None
                    if widget:
                        widget.deleteLater()
                
                # Dodaj etykiety dla każdego subtaska
                for subtask in subtasks:
                    prefix = t("tasks.subtask.prefix")
                    subtask_label = QLabel(f"   {prefix} {subtask.get('title', t('kanban.card.no_title'))}")
                    subtask_label.setStyleSheet("color: gray; font-size: 11px; padding-left: 10px;")
                    subtask_label.setWordWrap(True)
                    layout.addWidget(subtask_label)
                
                subtasks_container.setVisible(True)
                logger.debug(f"[KanBanView] Expanded {len(subtasks)} subtasks for task {task_id}")
                
        except Exception as e:
            logger.error(f"[KanBanView] Error toggling subtasks: {e}")
            import traceback
            traceback.print_exc()
    
    # ---------- Handlery zdarzeń ----------
    
    def _on_hide_completed_changed(self, index: int):
        """Zmiana opcji ukrywania zakończonych zadań"""
        # Pobierz wartość z data() zamiast tekstu
        value = self.hide_completed_combo.itemData(index)
        if value is not None:
            self.settings['hide_completed_after'] = value
            self._save_settings()
            self.refresh_board()
            logger.info(f"[KanBanView] Hide completed after changed to {value} days")
    
    def _on_max_in_progress_changed(self, value: int):
        """Zmiana maksymalnej liczby zadań w trakcie"""
        self.settings['max_in_progress'] = value
        self._save_settings()
        
        # Odśwież tablicę aby zastosować nowy limit
        self.refresh_board()
        
        logger.info(f"[KanBanView] Max in progress changed to {value}")
    
    def _on_review_toggled(self, state: int):
        """Przełączenie widoczności kolumny 'Do sprawdzenia'"""
        show = (state == Qt.CheckState.Checked.value)
        self.settings['show_review'] = show
        
        # Bezpieczna manipulacja kolumną (może być usunięta przez Qt)
        try:
            if show:
                self.review_column.show()
            else:
                self.review_column.hide()
        except RuntimeError as e:
            logger.warning(f"[KanBanView] Review column widget deleted: {e}")
            return
        
        self._save_settings()
        self.refresh_board()  # Odśwież tablicę aby załadować zadania
    
    def _on_hold_toggled(self, state: int):
        """Przełączenie widoczności kolumny 'Odłożone'"""
        show = (state == Qt.CheckState.Checked.value)
        self.settings['show_on_hold'] = show
        
        # Bezpieczna manipulacja kolumną
        try:
            if show:
                self.on_hold_column.show()
            else:
                self.on_hold_column.hide()
        except RuntimeError as e:
            logger.warning(f"[KanBanView] On-hold column widget deleted: {e}")
            return
        
        self._save_settings()
        self.refresh_board()  # Odśwież tablicę aby załadować zadania

    def _on_todo_toggled(self, state: int):
        """Przełączenie widoczności kolumny 'Do wykonania'"""
        show = (state == Qt.CheckState.Checked.value)
        self.settings['show_todo'] = show

        # Bezpieczna manipulacja kolumną
        try:
            if show:
                self.todo_column.show()
            else:
                self.todo_column.hide()
        except RuntimeError as e:
            logger.warning(f"[KanBanView] Todo column widget deleted: {e}")
            return

        self._save_settings()
        self.refresh_board()  # Odśwież tablicę aby załadować zadania

    def _on_done_toggled(self, state: int):
        """Przełączenie widoczności kolumny 'Ukończone'"""
        show = (state == Qt.CheckState.Checked.value)
        self.settings['show_done'] = show

        # Bezpieczna manipulacja kolumną
        try:
            if show:
                self.done_column.show()
            else:
                self.done_column.hide()
        except RuntimeError as e:
            logger.warning(f"[KanBanView] Done column widget deleted: {e}")
            return

        self._save_settings()
        self.refresh_board()  # Odśwież tablicę aby załadować zadania
    
    # ======================================================================
    # Assistant voice command endpoints
    # ======================================================================
    
    def assistant_show_column(self, column_name: str) -> bool:
        """
        Pokaż kolumnę przez asystenta głosowego.
        
        Args:
            column_name: Internal column name ('todo', 'done', 'review', 'on_hold', 'in_progress')
            
        Returns:
            True jeśli kolumna była ukryta (zmiana), False jeśli już widoczna
        """
        # Note: kolumna 'in_progress' zawsze widoczna, nie ma checkboxa
        if column_name == 'in_progress':
            logger.info("[KanbanView] Column 'in_progress' is always visible")
            return False
        
        checkbox_map = {
            'todo': self.todo_check,
            'done': self.done_check,
            'review': self.review_check,
            'on_hold': self.on_hold_check,
        }
        
        checkbox = checkbox_map.get(column_name)
        if not checkbox:
            logger.warning(f"[KanbanView] Unknown column name: {column_name}")
            return False
        
        # Sprawdź czy już zaznaczony
        if checkbox.isChecked():
            logger.debug(f"[KanbanView] Column '{column_name}' already visible")
            return False
        
        # Zaznacz checkbox (to automatycznie wywoła odpowiedni _on_*_toggled)
        checkbox.setChecked(True)
        logger.info(f"[KanbanView] Column '{column_name}' shown by assistant")
        return True
    
    def assistant_hide_column(self, column_name: str) -> bool:
        """
        Ukryj kolumnę przez asystenta głosowego.
        
        Args:
            column_name: Internal column name ('todo', 'done', 'review', 'on_hold', 'in_progress')
            
        Returns:
            True jeśli kolumna była widoczna (zmiana), False jeśli już ukryta
        """
        # Note: kolumna 'in_progress' zawsze widoczna
        if column_name == 'in_progress':
            logger.warning("[KanbanView] Cannot hide 'in_progress' column - always visible")
            return False
        
        checkbox_map = {
            'todo': self.todo_check,
            'done': self.done_check,
            'review': self.review_check,
            'on_hold': self.on_hold_check,
        }
        
        checkbox = checkbox_map.get(column_name)
        if not checkbox:
            logger.warning(f"[KanbanView] Unknown column name: {column_name}")
            return False
        
        # Sprawdź czy już odznaczony
        if not checkbox.isChecked():
            logger.debug(f"[KanbanView] Column '{column_name}' already hidden")
            return False
        
        # Odznacz checkbox (to automatycznie wywoła odpowiedni _on_*_toggled)
        checkbox.setChecked(False)
        logger.info(f"[KanbanView] Column '{column_name}' hidden by assistant")
        return True
    
    def assistant_show_all_columns(self) -> None:
        """Pokaż wszystkie kolumny (zaznacz wszystkie checkboxy)."""
        checkboxes = [
            self.todo_check,
            self.done_check,
            self.review_check,
            self.on_hold_check,
        ]
        
        for checkbox in checkboxes:
            if not checkbox.isChecked():
                checkbox.setChecked(True)
        
        logger.info("[KanbanView] All columns shown by assistant")
