"""
Menu kontekstowe dla zadań w TaskView
"""
from __future__ import annotations
from typing import Optional, TYPE_CHECKING, List
import logging
import re

from PyQt6.QtWidgets import QMenu, QColorDialog, QMessageBox, QDialog
from PyQt6.QtGui import QAction, QClipboard
from PyQt6.QtCore import Qt

from ...ui.ai_task_communication_dialog import (
    TaskAIPlanRequestDialog,
    TaskAIPlanResultDialog,
    parse_plan_to_steps,
)
from ...utils.i18n_manager import t

if TYPE_CHECKING:
    from ...ui.task_view import TaskView

logger = logging.getLogger(__name__)

# Regex dla walidacji koloru hex (z opcjonalnym alpha channel)
HEX_COLOR_PATTERN = re.compile(r'^#[0-9A-Fa-f]{6}([0-9A-Fa-f]{2})?$')


class TaskContextMenu:
    """Zarządza menu kontekstowym dla zadań"""
    
    def __init__(self, task_view: TaskView):
        """
        Inicjalizacja menu kontekstowego
        
        Args:
            task_view: Instancja TaskView
        """
        self.task_view = task_view
        self.current_task_id: Optional[int] = None
        self.current_task_title: Optional[str] = None
        self.current_row: Optional[int] = None
    
    def show_menu(self, position) -> None:
        """
        Wyświetl menu kontekstowe
        
        Args:
            position: Pozycja kliknięcia w widżecie
        """
        # Pobierz wiersz pod kursorem
        row = self.task_view.table.rowAt(position.y())
        if row < 0:
            return
        
        # Pobierz task_id z wiersza
        task_id = self.task_view._get_task_id_from_row(row)
        if task_id is None:
            return
        
        # Pobierz dane zadania z cache
        task_data = self.task_view._row_task_map.get(row)
        if not task_data:
            return
        
        task_title = task_data.get('title', '')
        
        # Zapisz kontekst
        self.current_task_id = task_id
        self.current_task_title = task_title
        self.current_row = row
        
        # Utwórz menu
        menu = QMenu(self.task_view)
        
        # 1. Przygotuj plan z AI
        ai_plan_action = QAction(t("tasks.context_menu.ai_plan", "Przygotuj plan z AI"), menu)
        ai_plan_action.triggered.connect(self._on_ai_plan)
        menu.addAction(ai_plan_action)
        
        menu.addSeparator()
        
        # 2. Koloruj
        colorize_action = QAction(t("tasks.context_menu.colorize", "Koloruj"), menu)
        colorize_action.triggered.connect(self._on_colorize)
        menu.addAction(colorize_action)
        
        # 2b. Usuń kolor (jeśli wiersz jest kolorowy)
        if task_data.get('row_color'):
            remove_color_action = QAction(t("tasks.context_menu.clear_color", "Usuń kolor"), menu)
            remove_color_action.triggered.connect(self._on_remove_color)
            menu.addAction(remove_color_action)
        
        # 3. Edytuj zadanie
        edit_action = QAction(t("tasks.context_menu.edit", "Edytuj zadanie"), menu)
        edit_action.triggered.connect(self._on_edit_task)
        menu.addAction(edit_action)
        
        menu.addSeparator()
        
        # 4. Oznacz jako wykonane
        mark_done_action = QAction(t("tasks.context_menu.mark_done", "Oznacz jako wykonane"), menu)
        mark_done_action.triggered.connect(self._on_mark_done)
        menu.addAction(mark_done_action)

        # 5. Archiwizacja / przywracanie
        is_archived = self._is_task_archived(task_data)
        if is_archived:
            restore_action = QAction(t("tasks.context_menu.restore", "Przywróć"), menu)
            restore_action.triggered.connect(self._on_restore)
            menu.addAction(restore_action)
        else:
            archive_action = QAction(t("tasks.context_menu.archive", "Archiwizuj"), menu)
            archive_action.triggered.connect(self._on_archive)
            menu.addAction(archive_action)
        
        # 6. Usuń zadanie
        delete_action = QAction(t("tasks.context_menu.delete", "Usuń zadanie"), menu)
        delete_action.triggered.connect(self._on_delete)
        menu.addAction(delete_action)
        
        menu.addSeparator()
        
        # 7. Dodaj/otwórz notatkę
        note_action = QAction(t("tasks.context_menu.note", "Dodaj/otwórz notatkę"), menu)
        note_action.triggered.connect(self._on_note)
        menu.addAction(note_action)
        
        # 8. Przenieś do Kanban
        kanban_action = QAction(t("tasks.context_menu.kanban", "Przenieś do Kanban"), menu)
        kanban_action.triggered.connect(self._on_kanban)
        menu.addAction(kanban_action)
        
        menu.addSeparator()
        
        # 9. Kopiuj treść
        copy_action = QAction(t("tasks.context_menu.copy", "Kopiuj treść"), menu)
        copy_action.triggered.connect(self._on_copy)
        menu.addAction(copy_action)
        
        # Wyświetl menu
        viewport = self.task_view.table.viewport() if hasattr(self.task_view, 'table') else None
        if viewport is None:
            return
        menu.exec(viewport.mapToGlobal(position))
    
    def _on_ai_plan(self) -> None:
        """Przygotuj plan z AI"""
        if not self.current_task_title:
            return
        
        try:
            task_context = self._build_task_context()
            prompt_dialog = TaskAIPlanRequestDialog(
                task_title=self.current_task_title or t('kanban.card.no_title', 'Bez tytułu'),
                task_body=task_context,
                parent=self.task_view,
            )

            if prompt_dialog.exec() != QDialog.DialogCode.Accepted or not prompt_dialog.ai_response:
                return

            response_dialog = TaskAIPlanResultDialog(
                task_title=self.current_task_title or t('kanban.card.no_title', 'Bez tytułu'),
                ai_response=prompt_dialog.ai_response,
                parent=self.task_view,
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
                        self.task_view,
                        t('status.success', 'Sukces'),
                        t('ai.plan.subtasks_created', 'Utworzono {count} subzadań na podstawie planu AI.').format(count=created),
                    )
                    self.task_view.populate_table()
                else:
                    QMessageBox.warning(
                        self.task_view,
                        t('common.warning', 'Ostrzeżenie'),
                        t('ai.plan.subtasks_failed', 'Nie udało się utworzyć subzadań na podstawie odpowiedzi AI.'),
                    )
        except Exception as e:
            logger.error(f"[TaskContextMenu] Error generating AI plan: {e}")
            QMessageBox.critical(
                self.task_view,
                t('common.error', 'Błąd'),
                t('ai.plan.dialog.response_error', 'AI zwróciło błąd: {error}').format(error=e),
            )
    
    def _build_task_context(self) -> str:
        """Zbierz dodatkowe informacje o zadaniu dla promptu AI."""
        parts: List[str] = []

        row_data = {}
        if self.current_row is not None:
            row_data = self.task_view._row_task_map.get(self.current_row, {}) or {}

        if not row_data and self.current_task_id is not None:
            db_sources = []
            if self.task_view.task_logic and getattr(self.task_view.task_logic, 'db', None):
                db_sources.append(self.task_view.task_logic.db)
            if self.task_view.local_db and self.task_view.local_db not in db_sources:
                db_sources.append(self.task_view.local_db)

            for db in db_sources:
                if hasattr(db, 'get_task_by_id'):
                    try:
                        fetched = db.get_task_by_id(self.current_task_id) or {}
                        if fetched:
                            row_data = fetched
                            break
                    except Exception as exc:
                        logger.error(f"[TaskContextMenu] Failed to load task details for AI prompt: {exc}")

        description = row_data.get('description') or row_data.get('Opis') or ''
        if description:
            parts.append(str(description))

        due_date = row_data.get('due_date') or row_data.get('Termin wykonania')
        if due_date:
            parts.append(t('task.due_date', 'Termin wykonania') + f": {due_date}")

        tags = row_data.get('tags')
        if isinstance(tags, list) and tags:
            tag_names = [str(tag.get('name')) for tag in tags if isinstance(tag, dict) and tag.get('name')]
            if tag_names:
                parts.append(t('task.tags', 'Tagi') + ': ' + ', '.join(tag_names))

        if not parts:
            parts.append(self.current_task_title or '')

        return "\n".join(part for part in parts if part).strip()

    def _on_colorize(self) -> None:
        """Otwórz dialog wyboru koloru"""
        if self.current_task_id is None or self.current_row is None:
            return
        
        from PyQt6.QtGui import QColor
        
        # Pobierz aktualny kolor
        task_data = self.task_view._row_task_map.get(self.current_row)
        current_color = task_data.get('row_color') if task_data else None
        
        # Utwórz kolor początkowy dla dialogu
        initial_color = QColor(current_color) if current_color else QColor(Qt.GlobalColor.white)
        
        # Otwórz dialog wyboru koloru z opcjami
        color = QColorDialog.getColor(
            initial_color,
            self.task_view,
            "Wybierz kolor wiersza",
            QColorDialog.ColorDialogOption.ShowAlphaChannel  # Pozwól na wybór przezroczystości
        )
        
        if color.isValid():
            color_hex = color.name()
            
            # Walidacja formatu koloru przed zapisem
            if not HEX_COLOR_PATTERN.match(color_hex):
                logger.error(f"[TaskContextMenu] Invalid color format: {color_hex}")
                QMessageBox.warning(
                    self.task_view,
                    "Błąd koloru",
                    f"Nieprawidłowy format koloru: {color_hex}\nOczekiwano formatu #RRGGBB lub #RRGGBBAA"
                )
                return
            
            logger.info(f"[TaskContextMenu] Setting row color for task {self.current_task_id}: {color_hex}")
            
            # Zapisz kolor w bazie danych
            if self._update_task_color(self.current_task_id, color_hex):
                # Użyj metody z TaskView do zastosowania koloru
                if hasattr(self.task_view, '_apply_row_color'):
                    self.task_view._apply_row_color(self.current_row, color_hex)
                else:
                    # Fallback - użyj lokalnej metody
                    self._apply_row_color(self.current_row, color_hex)
                
                # Zaktualizuj cache
                if task_data:
                    task_data['row_color'] = color_hex
                    
                logger.info(f"[TaskContextMenu] Row color updated successfully")
            else:
                logger.error(f"[TaskContextMenu] Failed to update row color in database")
    
    def _on_remove_color(self) -> None:
        """Usuń kolor wiersza - przywróć domyślne tło"""
        if self.current_task_id is None or self.current_row is None:
            return
        
        logger.info(f"[TaskContextMenu] Removing row color for task {self.current_task_id}")
        
        # Zapisz NULL w bazie danych
        if self._update_task_color(self.current_task_id, None):
            # Przywróć domyślne tło korzystając z TaskView
            if hasattr(self.task_view, '_clear_row_color'):
                self.task_view._clear_row_color(self.current_row)
            else:
                from PyQt6.QtGui import QBrush
                default_bg = QBrush()
                for col in range(self.task_view.table.columnCount()):
                    item = self.task_view.table.item(self.current_row, col)
                    if item:
                        item.setBackground(default_bg)
                viewport = self.task_view.table.viewport() if hasattr(self.task_view, 'table') else None
                if viewport is not None:
                    viewport.update()
            # Zaktualizuj cache
            task_data = self.task_view._row_task_map.get(self.current_row)
            if task_data:
                task_data['row_color'] = None
                
            logger.info(f"[TaskContextMenu] Row color removed successfully")
        else:
            logger.error(f"[TaskContextMenu] Failed to remove row color from database")
    
    def _on_edit_task(self) -> None:
        """Edytuj treść zadania"""
        if self.current_task_id is None or not self.current_task_title:
            return
        
        from ...ui.ui_task_simple_dialogs import TaskEditDialog
        
        # Otwórz dialog edycji
        accepted, new_title = TaskEditDialog.prompt(
            parent=self.task_view,
            task_title=self.current_task_title
        )
        
        if accepted and new_title and new_title != self.current_task_title:
            logger.info(f"[TaskContextMenu] Updating task {self.current_task_id} title: {new_title}")
            
            # Zaktualizuj w bazie danych
            if self._update_task_title(self.current_task_id, new_title):
                # Zaktualizuj w tabeli
                if self.current_row is not None:
                    self._update_task_cell_title(self.current_row, new_title)
    
    def _on_mark_done(self) -> None:
        """Oznacz zadanie jako wykonane"""
        if self.current_task_id is None:
            return
        
        logger.info(f"[TaskContextMenu] Marking task {self.current_task_id} as done")
        
        # Znajdź checkbox Status i zaznacz go
        visible_columns = self.task_view._get_visible_columns()
        status_col_idx = next(
            (idx for idx, col in enumerate(visible_columns) if col.get('column_id') == 'Status'),
            None
        )
        
        if status_col_idx is not None and self.current_row is not None:
            # Pobierz widget checkbox
            checkbox = self.task_view.table.cellWidget(self.current_row, status_col_idx)
            if checkbox:
                from PyQt6.QtWidgets import QCheckBox
                if isinstance(checkbox, QCheckBox):
                    checkbox.setChecked(True)
    
    def _on_archive(self) -> None:
        """Archiwizuj zadanie"""
        if self.current_task_id is None:
            return
        
        logger.info(f"[TaskContextMenu] Archiving task {self.current_task_id}")
        
        # Zaktualizuj w bazie danych
        if self._update_task_archived(self.current_task_id, True):
            # Odśwież tabelę
            self.task_view.populate_table()

    def _on_restore(self) -> None:
        """Przywróć zadanie z archiwum"""
        if self.current_task_id is None:
            return

        logger.info(f"[TaskContextMenu] Restoring task {self.current_task_id} from archive")

        if self._update_task_archived(self.current_task_id, None):
            self.task_view.populate_table()
    
    def _on_delete(self) -> None:
        """Usuń zadanie z bazy danych"""
        if self.current_task_id is None:
            return
        
        # Potwierdź usunięcie
        reply = QMessageBox.question(
            self.task_view,
            "Usuń zadanie",
            f"Czy na pewno chcesz usunąć zadanie:\n\n{self.current_task_title}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            logger.info(f"[TaskContextMenu] Deleting task {self.current_task_id}")
            
            # Usuń z bazy danych
            if self._delete_task(self.current_task_id):
                # Odśwież tabelę
                self.task_view.populate_table()
    
    def _on_note(self) -> None:
        """Dodaj/otwórz notatkę"""
        if self.current_task_id is None:
            return
        
        logger.info(f"[TaskContextMenu] Opening note for task {self.current_task_id}")
        
        # Wywołaj metodę z TaskView (taka sama jak przycisk Notatka)
        if hasattr(self.task_view, 'open_task_note'):
            self.task_view.open_task_note(self.current_task_id)
    
    def _on_kanban(self) -> None:
        """Przenieś do Kanban"""
        if self.current_task_id is None:
            return
        
        logger.info(f"[TaskContextMenu] Moving task {self.current_task_id} to Kanban")
        
        # Wywołaj metodę z TaskView (taka sama jak przycisk KanBan)
        if hasattr(self.task_view, '_on_add_to_kanban'):
            self.task_view._on_add_to_kanban(self.current_task_id)
    
    def _on_copy(self) -> None:
        """Kopiuj treść zadania do schowka"""
        if not self.current_task_title:
            return
        
        from PyQt6.QtWidgets import QApplication
        
        clipboard = QApplication.clipboard()
        if clipboard:
            clipboard.setText(self.current_task_title)
        
        logger.info(f"[TaskContextMenu] Copied task title to clipboard: {self.current_task_title}")
    
    # Metody pomocnicze do komunikacji z bazą danych
    
    def _update_task_color(self, task_id: int, color: Optional[str]) -> bool:
        """Zaktualizuj kolor wiersza w bazie danych
        
        Args:
            task_id: ID zadania
            color: Kolor w formacie hex (np. "#FF5733") lub None aby usunąć kolor
        """
        try:
            db_targets = []
            if self.task_view.task_logic and getattr(self.task_view.task_logic, 'db', None):
                db_targets.append(self.task_view.task_logic.db)
            if self.task_view.local_db and self.task_view.local_db not in db_targets:
                db_targets.append(self.task_view.local_db)
            
            success = False
            for db in db_targets:
                if hasattr(db, 'update_task'):
                    try:
                        db_success = db.update_task(task_id, row_color=color)
                        success = success or db_success
                    except Exception as e:
                        logger.error(f"[TaskContextMenu] Failed to update task color in db: {e}")
            
            return success
        except Exception as e:
            logger.error(f"[TaskContextMenu] Error updating task color: {e}")
            return False
    
    def _update_task_title(self, task_id: int, title: str) -> bool:
        """Zaktualizuj tytuł zadania w bazie danych"""
        try:
            db_targets = []
            if self.task_view.task_logic and getattr(self.task_view.task_logic, 'db', None):
                db_targets.append(self.task_view.task_logic.db)
            if self.task_view.local_db and self.task_view.local_db not in db_targets:
                db_targets.append(self.task_view.local_db)
            
            success = False
            for db in db_targets:
                if hasattr(db, 'update_task'):
                    try:
                        db_success = db.update_task(task_id, title=title)
                        success = success or db_success
                    except Exception as e:
                        logger.error(f"[TaskContextMenu] Failed to update task title in db: {e}")
            
            return success
        except Exception as e:
            logger.error(f"[TaskContextMenu] Error updating task title: {e}")
            return False
    
    def _update_task_archived(self, task_id: int, archived: Optional[bool]) -> bool:
        """Zaktualizuj status archiwizacji w bazie danych"""
        try:
            db_targets = []
            if self.task_view.task_logic and getattr(self.task_view.task_logic, 'db', None):
                db_targets.append(self.task_view.task_logic.db)
            if self.task_view.local_db and self.task_view.local_db not in db_targets:
                db_targets.append(self.task_view.local_db)
            
            success = False
            for db in db_targets:
                if hasattr(db, 'update_task'):
                    try:
                        archived_value = None if archived is None else (1 if archived else 0)
                        db_success = db.update_task(task_id, archived=archived_value)
                        success = success or db_success
                    except Exception as e:
                        logger.error(f"[TaskContextMenu] Failed to update task archived status in db: {e}")
            
            return success
        except Exception as e:
            logger.error(f"[TaskContextMenu] Error updating task archived status: {e}")
            return False

    def _is_task_archived(self, task_data) -> bool:
        """Sprawdź, czy zadanie jest zarchiwizowane na podstawie danych wiersza."""
        archived_value = task_data.get('archived') if isinstance(task_data, dict) else None
        if archived_value is None:
            return False
        if isinstance(archived_value, (bool, int)):
            return bool(archived_value)
        if isinstance(archived_value, str):
            normalized = archived_value.strip().lower()
            return normalized not in {'', '0', 'false', 'none', 'null'}
        return bool(archived_value)
    
    def _delete_task(self, task_id: int) -> bool:
        """Usuń zadanie z bazy danych"""
        try:
            db_targets = []
            if self.task_view.task_logic and getattr(self.task_view.task_logic, 'db', None):
                db_targets.append(self.task_view.task_logic.db)
            if self.task_view.local_db and self.task_view.local_db not in db_targets:
                db_targets.append(self.task_view.local_db)
            
            success = False
            for db in db_targets:
                if hasattr(db, 'delete_task'):
                    try:
                        db_success = db.delete_task(task_id)
                        success = success or db_success
                    except Exception as e:
                        logger.error(f"[TaskContextMenu] Failed to delete task in db: {e}")
            
            return success
        except Exception as e:
            logger.error(f"[TaskContextMenu] Error deleting task: {e}")
            return False
    
    def _apply_row_color(self, row: int, color: str) -> None:
        """Zastosuj kolor do wiersza w tabeli"""
        try:
            from PyQt6.QtGui import QColor, QBrush
            
            q_color = QColor(color)
            for col in range(self.task_view.table.columnCount()):
                item = self.task_view.table.item(row, col)
                if item:
                    item.setBackground(QBrush(q_color))
        except Exception as e:
            logger.error(f"[TaskContextMenu] Error applying row color: {e}")
    
    def _update_task_cell_title(self, row: int, title: str) -> None:
        """Zaktualizuj tytuł zadania w komórce tabeli"""
        try:
            # Znajdź kolumnę Zadanie
            visible_columns = self.task_view._get_visible_columns()
            title_col_idx = next(
                (idx for idx, col in enumerate(visible_columns) if col.get('column_id') == 'Zadanie'),
                None
            )
            
            if title_col_idx is not None:
                item = self.task_view.table.item(row, title_col_idx)
                if item:
                    item.setText(title)
                
                # Zaktualizuj cache
                task_data = self.task_view._row_task_map.get(row)
                if task_data:
                    task_data['title'] = title
        except Exception as e:
            logger.error(f"[TaskContextMenu] Error updating task cell title: {e}")
    
    def _create_note_with_content(self, title: str, content: str) -> None:
        """Utwórz nową notatkę z treścią i przejdź do widoku notatki"""
        try:
            # Utwórz notatkę w bazie danych
            note_id = None
            
            db_targets = []
            if self.task_view.local_db and hasattr(self.task_view.local_db, 'create_note'):
                db_targets.append(self.task_view.local_db)
            
            for db in db_targets:
                try:
                    note_id = db.create_note(
                        user_id=1,  # TODO: Pobrać aktualnego user_id
                        title=title,
                        content=content
                    )
                    if note_id:
                        break
                except Exception as e:
                    logger.error(f"[TaskContextMenu] Failed to create note in db: {e}")
            
            if note_id:
                # Powiąż notatkę z zadaniem
                if self.current_task_id:
                    self._update_task_note(self.current_task_id, note_id)
                
                # Przejdź do widoku notatki
                if hasattr(self.task_view, 'open_task_note'):
                    self.task_view.open_task_note(self.current_task_id if self.current_task_id else note_id)
                
                logger.info(f"[TaskContextMenu] Created note {note_id} with AI plan")
            else:
                logger.error("[TaskContextMenu] Failed to create note")
                QMessageBox.warning(
                    self.task_view,
                    t("common.warning", "Ostrzeżenie"),
                    "Nie udało się utworzyć notatki."
                )
        
        except Exception as e:
            logger.error(f"[TaskContextMenu] Error creating note: {e}")
            QMessageBox.critical(
                self.task_view,
                t("common.error", "Błąd"),
                f"Błąd podczas tworzenia notatki: {str(e)}"
            )

    def _create_subtasks_from_plan(self, parent_id: int, steps: List[str]) -> int:
        """Create subtasks for the given parent based on AI plan steps."""
        if not steps:
            return 0

        db_targets = []
        if self.task_view.task_logic and getattr(self.task_view.task_logic, 'db', None):
            db_targets.append(self.task_view.task_logic.db)
        if self.task_view.local_db and self.task_view.local_db not in db_targets:
            db_targets.append(self.task_view.local_db)

        created = 0
        for step in steps:
            clean_step = step.strip()
            if not clean_step:
                continue
            for db in db_targets:
                if hasattr(db, 'add_task'):
                    try:
                        subtask_id = db.add_task(title=clean_step, parent_id=parent_id)
                        if subtask_id:
                            created += 1
                            break
                    except Exception as exc:
                        logger.error(f"[TaskContextMenu] Failed to create subtask '{clean_step}': {exc}")
        return created
    
    def _update_task_note(self, task_id: int, note_id: int) -> bool:
        """Powiąż notatkę z zadaniem"""
        try:
            db_targets = []
            if self.task_view.task_logic and getattr(self.task_view.task_logic, 'db', None):
                db_targets.append(self.task_view.task_logic.db)
            if self.task_view.local_db and self.task_view.local_db not in db_targets:
                db_targets.append(self.task_view.local_db)
            
            success = False
            for db in db_targets:
                if hasattr(db, 'update_task'):
                    try:
                        db_success = db.update_task(task_id, note_id=note_id)
                        success = success or db_success
                    except Exception as e:
                        logger.error(f"[TaskContextMenu] Failed to update task note in db: {e}")
            
            return success
        except Exception as e:
            logger.error(f"[TaskContextMenu] Error updating task note: {e}")
            return False
