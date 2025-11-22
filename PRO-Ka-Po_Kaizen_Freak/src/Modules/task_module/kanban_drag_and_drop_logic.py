"""
Kanban Drag & Drop Logic
========================
Moduł odpowiedzialny za obsługę przeciągania kart zadań między kolumnami Kanban.

Funkcjonalności:
- Przeciąganie kart między kolumnami (drag & drop)
- Zmiana kolejności w obrębie kolumny (reordering)
- Visual feedback (highlight drop zone, ghost card)
- Walidacja reguł biznesowych (max_in_progress, status transitions)
- Integracja z bazą danych (update positions, sync)

Architektura:
- DraggableTaskCard: QFrame z obsługą drag events
- DropZoneColumn: QWidget jako cel drop
- KanbanDragDropManager: koordynator logiki drag & drop
"""

from PyQt6.QtWidgets import QFrame, QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QMimeData, QPoint, pyqtSignal, QObject
from PyQt6.QtGui import QDrag, QPainter, QPixmap, QCursor, QMouseEvent, QDragEnterEvent, QDragMoveEvent, QDragLeaveEvent, QDropEvent, QPaintEvent
from loguru import logger
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime


# ============================================================================
# FAZA 1: DRAGGABLE TASK CARD
# ============================================================================

class DraggableTaskCard(QFrame):
    """
    Rozszerzenie QFrame z obsługą drag & drop.
    
    Features:
    - Mouse press/move/release dla drag initiation
    - Tworzenie ghost image podczas drag
    - Przechowywanie task_id, column_type w mime data
    - Visual feedback (opacity change during drag)
    
    Signals:
        drag_started: Emitowany gdy rozpoczyna się przeciąganie
        drag_finished: Emitowany gdy kończy się przeciąganie (success/cancel)
    """
    
    drag_started = pyqtSignal(int, str)  # task_id, source_column
    drag_finished = pyqtSignal(int, str, bool)  # task_id, source_column, success
    
    def __init__(self, task_id: int, column_type: str, parent=None):
        super().__init__(parent)
        self.task_id = task_id
        self.column_type = column_type
        self._drag_start_position = QPoint()
        self._is_dragging = False
        
        # Ustawienia drag & drop
        self.setAcceptDrops(False)  # Card nie przyjmuje dropów, tylko kolumna
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        
    def mousePressEvent(self, a0: Optional[QMouseEvent]):
        """Rozpoczęcie potencjalnego drag"""
        if a0 and a0.button() == Qt.MouseButton.LeftButton:
            self._drag_start_position = a0.pos()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
        super().mousePressEvent(a0)
    
    def mouseMoveEvent(self, a0: Optional[QMouseEvent]):
        """Wykrycie drag (ruch myszy z wciśniętym przyciskiem)"""
        if not a0 or not (a0.buttons() & Qt.MouseButton.LeftButton):
            return
        
        # Sprawdź czy ruch jest wystarczający do rozpoczęcia drag
        if (a0.pos() - self._drag_start_position).manhattanLength() < 10:
            return
        
        # Rozpocznij drag operation
        self._start_drag()
        super().mouseMoveEvent(a0)
    
    def mouseReleaseEvent(self, a0: Optional[QMouseEvent]):
        """Zakończenie drag lub kliknięcia"""
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        if self._is_dragging:
            self._is_dragging = False
            # Signal jest emitowany przez drag.exec()
        super().mouseReleaseEvent(a0)
    
    def _start_drag(self):
        """Rozpocznij drag & drop operation"""
        self._is_dragging = True
        logger.info(f"[DragDrop] Starting drag: task_id={self.task_id}, column={self.column_type}")
        self.drag_started.emit(self.task_id, self.column_type)
        
        # Utwórz QDrag z mime data
        drag = QDrag(self)
        mime_data = QMimeData()
        
        # Zapisz task_id i column_type w mime data
        mime_data.setText(f"{self.task_id}|{self.column_type}")
        mime_data.setData("application/x-kanban-task", 
                         f"{self.task_id}".encode('utf-8'))
        drag.setMimeData(mime_data)
        
        logger.debug(f"[DragDrop] Mime data set: text='{mime_data.text()}', formats={mime_data.formats()}")
        
        # Utwórz ghost image (snapshot karty)
        pixmap = self._create_drag_pixmap()
        drag.setPixmap(pixmap)
        drag.setHotSpot(QPoint(pixmap.width() // 2, 20))
        
        # Ustaw opacity podczas drag
        self.setWindowOpacity(0.5)
        
        # Wykonaj drag (blocking call)
        drop_action = drag.exec(Qt.DropAction.MoveAction)
        
        logger.debug(f"[DragDrop] Drag finished with action: {drop_action} (MoveAction={Qt.DropAction.MoveAction})")
        
        # Przywróć opacity
        self.setWindowOpacity(1.0)
        
        # Emituj signal o zakończeniu
        success = drop_action == Qt.DropAction.MoveAction
        logger.info(f"[DragDrop] Drag ended: task_id={self.task_id}, success={success}")
        self.drag_finished.emit(self.task_id, self.column_type, success)
        
        logger.debug(f"[DragDrop] Drag finished for task {self.task_id}: {'success' if success else 'cancelled'}")
    
    def _create_drag_pixmap(self) -> QPixmap:
        """Utwórz ghost image karty do wyświetlania podczas drag"""
        pixmap = QPixmap(self.size())
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setOpacity(0.7)
        self.render(painter)
        painter.end()
        
        return pixmap


# ============================================================================
# FAZA 2: DROP ZONE COLUMN
# ============================================================================

class DropZoneColumn(QWidget):
    """
    Widget kolumny Kanban z obsługą drop events.
    
    Features:
    - Przyjmowanie drop events z DraggableTaskCard
    - Visual feedback (highlight podczas dragEnter/dragLeave)
    - Walidacja czy drop jest dozwolony (business rules)
    - Obliczanie pozycji insert (drop między kartami)
    
    Signals:
        task_dropped: Emitowany gdy karta została upuszczona
    """
    
    task_dropped = pyqtSignal(int, str, str, int)  # task_id, from_column, to_column, position
    
    def __init__(self, column_type: str, parent=None):
        super().__init__(parent)
        self.column_type = column_type
        self._highlight = False
        self._drop_position = -1
        
        # Ustawienia drop
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, a0: Optional[QDragEnterEvent]):
        """Karta wchodzi w obszar kolumny"""
        logger.debug(f"[DragDrop] dragEnterEvent called on column '{self.column_type}'")
        
        if not a0:
            logger.warning("[DragDrop] dragEnterEvent: event is None!")
            return
            
        mime_data = a0.mimeData()
        logger.debug(f"[DragDrop] Mime data formats: {mime_data.formats() if mime_data else 'None'}")
        
        if mime_data and mime_data.hasFormat("application/x-kanban-task"):
            # Parsuj task_id z mime data
            task_data = mime_data.text().split('|')
            if len(task_data) >= 2:
                task_id = int(task_data[0])
                source_column = task_data[1]
                
                # Waliduj czy drop jest dozwolony
                if self._validate_drop(task_id, source_column, self.column_type):
                    a0.acceptProposedAction()
                    self._highlight = True
                    self.update()  # Odśwież widok (highlight)
                    logger.debug(f"[DragDrop] Drag entered column '{self.column_type}' from '{source_column}'")
                else:
                    a0.ignore()
        else:
            a0.ignore() if a0 else None
    
    def dragMoveEvent(self, a0: Optional[QDragMoveEvent]):
        """Karta porusza się w obszarze kolumny"""
        if not a0:
            return
            
        mime_data = a0.mimeData()
        if mime_data and mime_data.hasFormat("application/x-kanban-task"):
            # Oblicz pozycję insert (między którymi kartami)
            self._drop_position = self._calculate_drop_position(a0.position().toPoint() if hasattr(a0, 'position') else QPoint(0, 0))
            a0.acceptProposedAction()
            self.update()
    
    def dragLeaveEvent(self, a0: Optional[QDragLeaveEvent]):
        """Karta opuściła obszar kolumny"""
        self._highlight = False
        self._drop_position = -1
        self.update()
        logger.debug(f"[DragDrop] Drag left column '{self.column_type}'")
    
    def dropEvent(self, a0: Optional[QDropEvent]):
        """Karta została upuszczona w kolumnie"""
        if not a0:
            logger.warning("[DragDrop] dropEvent called with None event")
            return
            
        mime_data = a0.mimeData()
        
        if not mime_data:
            logger.warning("[DragDrop] No mime data in drop event")
            return
            
        logger.debug(f"[DragDrop] Drop event in column '{self.column_type}', mime formats: {mime_data.formats()}")
        
        if mime_data.hasFormat("application/x-kanban-task"):
            task_data = mime_data.text().split('|')
            logger.debug(f"[DragDrop] Parsed task_data: {task_data}")
            
            if len(task_data) >= 2:
                task_id = int(task_data[0])
                source_column = task_data[1]
                target_column = self.column_type
                position = self._drop_position if self._drop_position >= 0 else 0
                
                logger.info(f"[DragDrop] Emitting task_dropped signal: task_id={task_id}, from={source_column}, to={target_column}, pos={position}")
                
                # Emituj signal o drop
                self.task_dropped.emit(task_id, source_column, target_column, position)
                
                a0.acceptProposedAction()
                logger.info(f"[DragDrop] Task {task_id} dropped from '{source_column}' to '{target_column}' at position {position}")
            else:
                logger.warning(f"[DragDrop] Invalid task_data length: {len(task_data)}")
        else:
            logger.warning(f"[DragDrop] Mime data doesn't have kanban-task format")
        
        # Reset highlight
        self._highlight = False
        self._drop_position = -1
        self.update()
    
    def _validate_drop(self, task_id: int, source_column: str, target_column: str) -> bool:
        """
        Waliduj czy drop jest dozwolony.
        
        Reguły biznesowe:
        - Nie można dropnąć na tę samą kolumnę (tylko reorder w obrębie)
        - Sprawdź max_in_progress limit
        - Sprawdź czy transition jest dozwolony
        """
        # TODO: Implementacja walidacji reguł (będzie w FAZA 3)
        # Na razie zezwalaj na wszystkie drop (oprócz na tę samą kolumnę)
        return source_column != target_column
    
    def _calculate_drop_position(self, drop_point: QPoint) -> int:
        """
        Oblicz pozycję insert na podstawie współrzędnych drop.
        
        Returns:
            Index pozycji (0 = na początku, -1 = na końcu)
        """
        # TODO: Implementacja obliczania pozycji między kartami (FAZA 4)
        # Na razie zwróć -1 (dodaj na koniec)
        return -1
    
    def paintEvent(self, a0: Optional[QPaintEvent]):
        """Custom painting dla highlight podczas drag"""
        super().paintEvent(a0)
        
        if self._highlight:
            # TODO: Rysuj highlight border/background (FAZA 4)
            pass


# ============================================================================
# FAZA 3: DRAG & DROP MANAGER
# ============================================================================

class KanbanDragDropManager(QObject):
    """
    Główny koordynator logiki drag & drop dla Kanban.
    
    Responsibilities:
    - Obsługa sygnałów z DraggableTaskCard i DropZoneColumn
    - Walidacja reguł biznesowych (max_in_progress, transitions)
    - Aktualizacja bazy danych (move_kanban_item, update positions)
    - Synchronizacja z serwerem (via TasksManager)
    - Animacje i visual feedback
    
    Signals:
        task_moved_successfully: Emitowany po udanym przeniesieniu
        task_move_failed: Emitowany gdy przeniesienie nie powiodło się
    """
    
    task_moved_successfully = pyqtSignal(int, str, str, int)  # task_id, from, to, position
    task_move_failed = pyqtSignal(int, str, str, str)  # task_id, from, to, reason
    
    def __init__(self, db, settings: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.db = db
        self.settings = settings
        self._active_drag: Optional[Dict[str, Any]] = None
        
    def handle_drag_started(self, task_id: int, source_column: str):
        """Rozpoczęcie drag - zapisz stan"""
        self._active_drag = {
            'task_id': task_id,
            'source_column': source_column,
            'start_time': datetime.now()
        }
        logger.debug(f"[DragDropManager] Drag started: task={task_id}, column={source_column}")
    
    def handle_task_dropped(self, task_id: int, source_column: str, 
                           target_column: str, position: int):
        """Obsługa drop - walidacja i przeniesienie zadania"""
        if not self._active_drag or self._active_drag['task_id'] != task_id:
            logger.warning(f"[DragDropManager] Drop without active drag: task={task_id}")
            return
        
        # Walidacja reguł biznesowych
        validation_result = self._validate_move(task_id, source_column, target_column)
        if not validation_result['valid']:
            reason = validation_result.get('reason', 'Unknown error')
            logger.warning(f"[DragDropManager] Move validation failed: {reason}")
            self.task_move_failed.emit(task_id, source_column, target_column, reason)
            self._active_drag = None
            return
        
        # Wykonaj przeniesienie w bazie danych
        success = self._move_task_in_database(task_id, source_column, target_column, position)
        
        if success:
            logger.info(f"[DragDropManager] Task {task_id} moved successfully: {source_column} → {target_column}")
            self.task_moved_successfully.emit(task_id, source_column, target_column, position)
        else:
            logger.error(f"[DragDropManager] Database move failed for task {task_id}")
            self.task_move_failed.emit(task_id, source_column, target_column, "Database error")
        
        self._active_drag = None
    
    def _validate_move(self, task_id: int, from_column: str, to_column: str) -> Dict[str, Any]:
        """
        Waliduj reguły biznesowe dla przeniesienia.
        
        Returns:
            {'valid': bool, 'reason': str (jeśli invalid)}
        """
        # 1. Sprawdź max_in_progress limit
        if to_column == 'in_progress':
            max_in_progress = self.settings.get('max_in_progress', 3)
            current_count = self._count_items_in_column('in_progress')
            
            # Jeśli przenosimy Z in_progress, nie liczymy tego zadania
            if from_column == 'in_progress':
                current_count -= 1
            
            if current_count >= max_in_progress:
                return {
                    'valid': False,
                    'reason': f'Max limit reached ({max_in_progress} tasks in progress)'
                }
        
        # 2. Sprawdź czy transition jest dozwolony
        # Pełna swoboda - wszystkie przejścia dozwolone (można przenosić wszędzie)
        # Tylko sprawdzamy czy nie przesuwamy do tej samej kolumny
        if from_column == to_column:
            return {
                'valid': False,
                'reason': 'Already in this column'
            }
        
        # Wszystkie inne przejścia są dozwolone
        
        # 3. Wszystko OK
        return {'valid': True}
    
    def _count_items_in_column(self, column_type: str) -> int:
        """Policz ile zadań jest w kolumnie"""
        if not self.db or not hasattr(self.db, 'get_kanban_items'):
            return 0
        
        try:
            items = self.db.get_kanban_items()
            return sum(1 for item in items if item.get('column_type') == column_type)
        except Exception as e:
            logger.error(f"[DragDropManager] Failed to count items: {e}")
            return 0
    
    def _move_task_in_database(self, task_id: int, from_column: str, 
                                to_column: str, position: int) -> bool:
        """
        Przenieś zadanie w bazie danych.
        
        Steps:
        1. Update kanban_item (column_type, position)
        2. Reorder other items w target column
        3. Update task status jeśli potrzebne
        4. Log move w kanban_log
        """
        if not self.db:
            return False
        
        try:
            # 1. Move kanban item
            if hasattr(self.db, 'move_kanban_item'):
                logger.debug(f"[DragDropManager] Calling move_kanban_item: task={task_id}, column={to_column}, position={position}")
                success = self.db.move_kanban_item(task_id, to_column, position)
                if not success:
                    logger.error(f"[DragDropManager] move_kanban_item returned False for task {task_id}")
                    return False
                logger.debug(f"[DragDropManager] move_kanban_item succeeded for task {task_id}")
            else:
                logger.error("[DragDropManager] db.move_kanban_item method not found!")
                return False
            
            # 2. Update task status (completion checkbox) based on column
            # status jest boolean: True=zaznaczony (done), False=niezaznaczony
            if hasattr(self.db, 'update_task'):
                # Zaznacz checkbox tylko gdy przenosimy DO 'done'
                # Odznacz checkbox gdy przenosimy Z 'done' do czegokolwiek innego
                if to_column == 'done':
                    success_status = self.db.update_task(task_id, status=1)  # Zaznacz
                    if success_status:
                        logger.debug(f"[DragDropManager] Marked task {task_id} as completed (status=1)")
                elif from_column == 'done':
                    success_status = self.db.update_task(task_id, status=0)  # Odznacz
                    if success_status:
                        logger.debug(f"[DragDropManager] Unmarked task {task_id} as completed (status=0)")
                # Jeśli przesuwamy między innymi kolumnami, nie zmieniamy status
            
            # 3. Log move (jeśli istnieje kanban_log)
            if hasattr(self.db, 'log_kanban_move'):
                self.db.log_kanban_move(
                    task_id=task_id,
                    from_column=from_column,
                    to_column=to_column,
                    reason="drag_and_drop"
                )
            
            return True
            
        except Exception as e:
            logger.error(f"[DragDropManager] Database move error: {e}")
            return False


# ============================================================================
# FAZA 4: INTEGRATION HELPERS
# ============================================================================

def convert_card_to_draggable(card: QFrame, task_id: int, column_type: str) -> DraggableTaskCard:
    """
    Helper: Konwertuj zwykły QFrame na DraggableTaskCard.
    
    Używane w KanbanView._create_task_card() do upgrade istniejących kart.
    """
    # Kopiuj właściwości z oryginalnej karty
    draggable = DraggableTaskCard(task_id, column_type, card.parent())
    draggable.setLayout(card.layout())
    draggable.setStyleSheet(card.styleSheet())
    draggable.setFrameShape(card.frameShape())
    draggable.setProperty('task_id', task_id)
    draggable.setProperty('column_type', column_type)
    
    return draggable


def enable_drop_for_column(column_widget: QWidget, column_type: str) -> DropZoneColumn:
    """
    Helper: Upgrade zwykłego QWidget na DropZoneColumn.
    
    Używane w KanbanView._create_column() do dodania drop support.
    """
    drop_zone = DropZoneColumn(column_type, column_widget.parent())
    drop_zone.setLayout(column_widget.layout())
    drop_zone.setStyleSheet(column_widget.styleSheet())
    
    return drop_zone


# ============================================================================
# USAGE EXAMPLE (do implementacji w kanban_view.py)
# ============================================================================

"""
W kanban_view.py:

1. Inicjalizacja w __init__:
    from ..Modules.task_module.kanban_drag_and_drop_logic import KanbanDragDropManager
    
    self.drag_drop_manager = KanbanDragDropManager(self.db, self.settings, self)
    self.drag_drop_manager.task_moved_successfully.connect(self._on_drag_drop_success)
    self.drag_drop_manager.task_move_failed.connect(self._on_drag_drop_failed)

2. W _create_task_card() zamień QFrame na DraggableTaskCard:
    card = DraggableTaskCard(task_id, column_type, parent)
    card.drag_started.connect(self.drag_drop_manager.handle_drag_started)
    # ... reszta setup karty

3. W _create_column() upgrade column container:
    tasks_container = DropZoneColumn(column_type)
    tasks_container.task_dropped.connect(self.drag_drop_manager.handle_task_dropped)

4. Callbacki:
    def _on_drag_drop_success(self, task_id, from_col, to_col, pos):
        # Refresh board
        self.refresh_board()
    
    def _on_drag_drop_failed(self, task_id, from_col, to_col, reason):
        # Show error message
        QMessageBox.warning(self, "Move Failed", reason)
"""
