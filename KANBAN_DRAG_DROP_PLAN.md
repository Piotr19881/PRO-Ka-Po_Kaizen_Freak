# PLAN INTEGRACJI DRAG & DROP - KANBAN
# =====================================

## ETAPY IMPLEMENTACJI

### ETAP 1: Inicjalizacja DragDropManager (5 min)
**Plik:** kanban_view.py, metoda __init__()

```python
# Po linii 52 (po self.context_menu = ...)
from ..Modules.task_module.kanban_drag_and_drop_logic import KanbanDragDropManager

# Inicjalizacja managera (po załadowaniu settings)
self.drag_drop_manager = None  # Będzie utworzony w set_task_logic()
```

**W metodzie set_task_logic() (po linii 72):**
```python
# Utwórz DragDropManager z aktualną bazą danych
if self.db and not self.drag_drop_manager:
    self.drag_drop_manager = KanbanDragDropManager(self.db, self.settings, self)
    self.drag_drop_manager.task_moved_successfully.connect(self._on_drag_drop_success)
    self.drag_drop_manager.task_move_failed.connect(self._on_drag_drop_failed)
    logger.info("[KanBanView] Drag & Drop Manager initialized")
```

---

### ETAP 2: Upgrade kart na DraggableTaskCard (10 min)
**Plik:** kanban_view.py, metody _build_*_card()

**Modyfikacja _create_base_card() (linia 767):**
```python
def _create_base_card(self, column_type: str, task_id: Optional[int]) -> Tuple[QFrame, QVBoxLayout]:
    from ..Modules.task_module.kanban_drag_and_drop_logic import DraggableTaskCard
    
    # Zamień QFrame na DraggableTaskCard
    if task_id and self.drag_drop_manager:
        card = DraggableTaskCard(task_id, column_type)
        # Podłącz sygnały
        card.drag_started.connect(self.drag_drop_manager.handle_drag_started)
        card.drag_finished.connect(self._on_card_drag_finished)
    else:
        # Fallback dla kart bez task_id
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
```

---

### ETAP 3: Upgrade kolumn na DropZoneColumn (15 min)
**Plik:** kanban_view.py, metoda _populate_column()

**Problem:** Obecny tasks_container to zwykły QWidget.  
**Rozwiązanie:** Zamień na DropZoneColumn w _create_column()

**Modyfikacja _create_column() (linia 200):**
```python
def _create_column(self, column_type: str) -> QGroupBox:
    from ..Modules.task_module.kanban_drag_and_drop_logic import DropZoneColumn
    
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
    
    # ZMIANA: DropZoneColumn zamiast QWidget
    tasks_container = DropZoneColumn(column_type)
    tasks_container.setObjectName(f"{column_type}_tasks")
    
    # Podłącz sygnał drop
    if self.drag_drop_manager:
        tasks_container.task_dropped.connect(self.drag_drop_manager.handle_task_dropped)
    
    tasks_layout = QVBoxLayout(tasks_container)
    tasks_layout.setContentsMargins(0, 0, 0, 0)
    tasks_layout.setSpacing(5)
    tasks_layout.addStretch()
    
    scroll.setWidget(tasks_container)
    column_layout.addWidget(scroll)
    
    column.setLayout(column_layout)
    return column
```

---

### ETAP 4: Implementacja callbacków (10 min)
**Plik:** kanban_view.py, nowe metody na końcu klasy

**Dodaj przed metodą apply_theme():**
```python
def _on_card_drag_finished(self, task_id: int, source_column: str, success: bool):
    """Callback po zakończeniu drag (success lub cancel)"""
    if not success:
        logger.debug(f"[KanBanView] Drag cancelled for task {task_id}")
    # Można dodać animację powrotu karty jeśli cancel

def _on_drag_drop_success(self, task_id: int, from_column: str, to_column: str, position: int):
    """Callback po udanym przeniesieniu zadania"""
    logger.info(f"[KanBanView] Drag & Drop success: task {task_id} moved {from_column} → {to_column}")
    
    # Odśwież board
    self.refresh_board()
    
    # Emituj sygnał task_moved (dla sync)
    self.task_moved.emit(task_id, to_column, position)

def _on_drag_drop_failed(self, task_id: int, from_column: str, to_column: str, reason: str):
    """Callback gdy przeniesienie nie powiodło się"""
    logger.warning(f"[KanBanView] Drag & Drop failed: {reason}")
    
    # Pokaż toast/message
    from PyQt6.QtWidgets import QMessageBox
    QMessageBox.warning(
        self,
        t('kanban.drag.failed_title', 'Nie można przenieść'),
        t('kanban.drag.failed_message', f'Powód: {reason}')
    )
```

---

### ETAP 5: Update drag_drop_manager settings (5 min)
**Plik:** kanban_view.py, metoda _save_settings()

**Dodaj po linii z save_setting (około 585):**
```python
def _save_settings(self):
    """Zapisz ustawienia Kanban"""
    # ... istniejący kod ...
    
    # Update drag_drop_manager settings
    if self.drag_drop_manager:
        self.drag_drop_manager.settings = self.settings
        logger.debug("[KanBanView] DragDropManager settings updated")
```

---

## TESTOWANIE

### Test 1: Basic Drag & Drop
1. Uruchom aplikację
2. Przejdź do widoku Kanban
3. Dodaj zadanie do kolumny "Do wykonania"
4. Przeciągnij zadanie do kolumny "W trakcie"
5. ✅ Zadanie powinno się przenieść

### Test 2: Max Limit Validation
1. Ustaw max_in_progress = 2
2. Dodaj 2 zadania do "W trakcie"
3. Spróbuj przeciągnąć 3. zadanie
4. ✅ Powinien pojawić się komunikat błędu

### Test 3: Invalid Transition
1. Przeciągnij zadanie z "Do wykonania" bezpośrednio do "Zakończone"
2. ✅ Powinien pojawić się komunikat (transition not allowed)

### Test 4: Cancel Drag
1. Rozpocznij przeciąganie
2. Naciśnij ESC lub upuść poza kolumnami
3. ✅ Zadanie powinno wrócić do oryginalnej kolumny

### Test 5: Visual Feedback
1. Rozpocznij przeciąganie
2. ✅ Ghost image powinien być widoczny
3. ✅ Karta źródłowa powinna mieć opacity 0.5
4. ✅ Kolumna docelowa powinna mieć highlight

---

## TROUBLESHOOTING

### Problem: Karty nie są draggable
**Rozwiązanie:** Sprawdź czy DraggableTaskCard ma setCursor(OpenHandCursor)

### Problem: Drop nie działa
**Rozwiązanie:** 
1. Sprawdź czy DropZoneColumn ma setAcceptDrops(True)
2. Sprawdź czy mime_data zawiera "application/x-kanban-task"

### Problem: Manager nie jest zainicjalizowany
**Rozwiązanie:** Sprawdź czy set_task_logic() jest wywoływane z poprawnym db

---

## KOLEJNE KROKI (OPCJONALNE)

### Feature 1: Reordering w obrębie kolumny
- Implement _calculate_drop_position() w DropZoneColumn
- Rysuj indicator line między kartami

### Feature 2: Smooth Animations
- Dodaj QPropertyAnimation dla karty po drop
- Animate cards moving up/down w kolumnie

### Feature 3: Batch Operations
- Ctrl+Click do zaznaczania wielu kart
- Przeciągaj wiele kart jednocześnie

### Feature 4: Undo/Redo
- Stack operacji drag & drop
- Przycisk Undo w control bar
