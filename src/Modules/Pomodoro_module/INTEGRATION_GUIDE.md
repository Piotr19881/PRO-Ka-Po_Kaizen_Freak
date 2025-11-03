# Integracja PomodoroLogic z PomodoroView

## ✅ Status implementacji

**UKOŃCZONE:**
- ✅ `pomodoro_logic.py` - Manager logiki biznesowej cyklu Pomodoro
- ✅ Testy jednostkowe przeszły pomyślnie
- ✅ Wszystkie funkcjonalności działają:
  - Zarządzanie cyklem sesji (work → short_break → work → long_break)
  - Auto/manual mode logic
  - Pauza/wznowienie/reset/skip/interrupt
  - Liczniki i statystyki (postęp cyklu, sesje dzienne)
  - Zarządzanie tematami sesji
  - Eksport danych do zapisu w bazie

---

## 🎯 Następny krok: Integracja z PomodoroView

### Zmiany w `src/ui/pomodoro_view.py`:

#### 1. Import PomodoroLogic (dodaj na górze pliku)

```python
from ..Modules.Pomodoro_module import (
    PomodoroLogic,
    PomodoroSettings,
    SessionData,
    SessionType,
    SessionStatus,
)
```

#### 2. Inicjalizacja logiki w `__init__`

```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.user_data = None
    self.current_theme = "light"
    
    # NOWE: Manager logiki Pomodoro
    self.pomodoro_logic: Optional[PomodoroLogic] = None
    
    # Timer UI (bez zmian)
    self.timer = QTimer()
    self.timer.timeout.connect(self._on_timer_tick)
    self.remaining_seconds = 25 * 60
    self.total_seconds = 25 * 60
    
    # USUNIĘTE (logika przeniesiena do PomodoroLogic):
    # self.session_topic = "Ogólna"
    # self.is_running = False
    # self.is_paused = False
    # self.current_session_type = "work"
    # self.completed_pomodoros = 0
    # self.total_pomodoros = 4
    # self.today_long_sessions = 0
    
    # ... reszta bez zmian
```

#### 3. Utwórz metodę do inicjalizacji logiki (po zalogowaniu)

```python
def set_user_data(self, user_data: dict):
    """Ustawia dane użytkownika i inicjalizuje logikę Pomodoro"""
    self.user_data = user_data
    
    # Utwórz ustawienia z localStorage/JSON (TODO: implementacja load)
    settings = self._load_settings()
    
    # Inicjalizuj manager logiki
    self.pomodoro_logic = PomodoroLogic(
        user_id=user_data['id'],
        settings=settings
    )
    
    # Podłącz callbacki
    self.pomodoro_logic.on_session_end = self._on_logic_session_end
    self.pomodoro_logic.on_cycle_complete = self._on_logic_cycle_complete
    
    # Załaduj statystyki dzienne (TODO: z bazy danych)
    self._load_today_stats()
    
    # Aktualizuj UI
    self._update_counters()
    self._update_display()

def _load_settings(self) -> PomodoroSettings:
    """Ładuje ustawienia z localStorage (TODO: implementacja)"""
    # TODO: Odczyt z pliku JSON lub bazy danych
    return PomodoroSettings(
        work_duration=25,
        short_break_duration=5,
        long_break_duration=15,
        sessions_count=4,
        auto_start_breaks=False,
        auto_start_pomodoro=False,
    )

def _load_today_stats(self):
    """Ładuje statystyki dzienne z bazy (TODO: implementacja)"""
    # TODO: Query do bazy danych (LocalDatabase)
    # SELECT COUNT(*), SUM(...) FROM session_logs WHERE user_id=? AND session_date=TODAY
    pass
```

#### 4. Przepisz metodę `_on_start_pause_clicked()` używając logiki

```python
def _on_start_pause_clicked(self):
    """Obsługuje kliknięcie Start/Pauza"""
    if not self.pomodoro_logic:
        return
    
    # START - rozpocznij nową sesję
    if not self.pomodoro_logic.is_session_active():
        # Określ typ sesji (auto lub manual)
        session_data = self.pomodoro_logic.start_new_session()
        
        # Ustaw timer na odpowiedni czas
        self.total_seconds = self.pomodoro_logic.get_session_duration_seconds()
        self.remaining_seconds = self.total_seconds
        
        # Uruchom timer UI
        self.timer.start(1000)
        
        # Aktualizuj UI
        self.start_pause_btn.setText(t("pomodoro.btn_pause"))
        self._update_display()
        self._update_counters()
        
        # Sygnał
        self.session_started.emit()
        
        # Otwórz popup jeśli włączone
        if self.pomodoro_logic.settings.popup_timer:
            self._show_popup_timer()  # TODO
    
    # PAUZA - zapauzuj bieżącą sesję
    elif self.pomodoro_logic.current_session.status == SessionStatus.RUNNING:
        self.pomodoro_logic.pause_session()
        self.timer.stop()
        
        self.start_pause_btn.setText(t("pomodoro.btn_start"))
        self._update_display()
        
        self.session_paused.emit()
    
    # WZNOWIENIE - kontynuuj zapauzowaną sesję
    elif self.pomodoro_logic.current_session.status == SessionStatus.PAUSED:
        self.pomodoro_logic.resume_session()
        self.timer.start(1000)
        
        self.start_pause_btn.setText(t("pomodoro.btn_pause"))
        self._update_display()
```

#### 5. Przepisz metodę `_on_reset_clicked()`

```python
def _on_reset_clicked(self):
    """Resetuje timer do wartości początkowej"""
    if not self.pomodoro_logic:
        return
    
    self.pomodoro_logic.reset_session()
    
    # Resetuj timer UI
    self.total_seconds = self.pomodoro_logic.get_session_duration_seconds()
    self.remaining_seconds = self.total_seconds
    
    self._update_display()
```

#### 6. Przepisz metodę `_on_skip_clicked()`

```python
def _on_skip_clicked(self):
    """Pomija bieżącą sesję i przechodzi do kolejnej"""
    if not self.pomodoro_logic or not self.pomodoro_logic.is_session_active():
        return
    
    # Zakończ bieżącą jako pominiętą
    self.pomodoro_logic.skip_session()
    
    # Stop timer UI
    self.timer.stop()
    
    # Rozpocznij kolejną sesję jeśli auto-start
    if self.pomodoro_logic.should_auto_start_next():
        self._start_next_session()
    else:
        # Manual mode - pokaż pytanie
        self._show_next_session_question()  # TODO
```

#### 7. Przepisz metodę `_on_stop_clicked()`

```python
def _on_stop_clicked(self):
    """Zatrzymuje całą sesję i zapisuje do logów"""
    if not self.pomodoro_logic or not self.pomodoro_logic.is_session_active():
        return
    
    # Oblicz przepracowany czas
    elapsed_seconds = self.total_seconds - self.remaining_seconds
    
    # Przerwij sesję w logice
    session_data = self.pomodoro_logic.interrupt_session(elapsed_seconds)
    
    # Stop timer UI
    self.timer.stop()
    
    # Reset UI
    self.start_pause_btn.setText(t("pomodoro.btn_start"))
    self._reset_timer()
    self._update_counters()
    
    # Zapisz do bazy (TODO)
    # self._save_session_to_db(session_data)
    
    self.session_stopped.emit()
```

#### 8. Przepisz metodę `_on_timer_tick()`

```python
def _on_timer_tick(self):
    """Tick timera - odlicza sekundę"""
    if self.remaining_seconds > 0:
        self.remaining_seconds -= 1
        self._update_display()
    else:
        # Timer doszedł do 0 - zakończ sesję
        self.timer.stop()
        self._finish_current_session(SessionStatus.COMPLETED)
```

#### 9. Przepisz metodę `_finish_current_session()`

```python
def _finish_current_session(self, status: SessionStatus):
    """Kończy bieżącą sesję"""
    if not self.pomodoro_logic or not self.pomodoro_logic.is_session_active():
        return
    
    # Oblicz rzeczywisty czas
    elapsed_seconds = self.total_seconds - self.remaining_seconds
    
    # Zakończ w logice
    if status == SessionStatus.COMPLETED:
        session_data = self.pomodoro_logic.complete_session(elapsed_seconds)
    else:
        session_data = self.pomodoro_logic.interrupt_session(elapsed_seconds)
    
    # Odtwórz dźwięk
    if self.pomodoro_logic.current_session.session_type == SessionType.WORK:
        if self.pomodoro_logic.settings.sound_work_end:
            self._play_sound("work_end")
    else:
        if self.pomodoro_logic.settings.sound_break_end:
            self._play_sound("break_end")
    
    # Zapisz do bazy (TODO)
    # self._save_session_to_db(session_data)
    
    # Emit sygnał
    self.session_completed.emit(session_data.session_type.value)
    
    # Automatyczne przejście lub pytanie
    if self.pomodoro_logic.should_auto_start_next():
        self._start_next_session()
    else:
        self._show_next_session_question()  # TODO
```

#### 10. Dodaj metodę `_start_next_session()`

```python
def _start_next_session(self):
    """Rozpoczyna kolejną sesję w cyklu"""
    if not self.pomodoro_logic:
        return
    
    # Rozpocznij nową sesję (logika automatycznie określi typ)
    session_data = self.pomodoro_logic.start_new_session()
    
    # Ustaw timer
    self.total_seconds = self.pomodoro_logic.get_session_duration_seconds()
    self.remaining_seconds = self.total_seconds
    
    # Uruchom timer
    self.timer.start(1000)
    
    # Aktualizuj UI
    self._update_session_title(session_data.session_type)
    self._update_display()
    self._update_counters()
    
    self.session_started.emit()
```

#### 11. Przepisz metodę `_update_counters()`

```python
def _update_counters(self):
    """Aktualizuje liczniki sesji"""
    if not self.pomodoro_logic:
        return
    
    stats = self.pomodoro_logic.get_today_stats()
    progress = self.pomodoro_logic.get_cycle_progress()
    
    # "Dziś wykonano N długich sesji"
    self.today_counter_label.setText(
        t("pomodoro.today_counter").format(count=stats['long_sessions'])
    )
    
    # "Sesja krótka N/X"
    self.session_counter_label.setText(
        t("pomodoro.session_counter").format(
            current=progress[0] + 1,
            total=progress[1]
        )
    )
```

#### 12. Przepisz metodę `_on_set_title_clicked()`

```python
def _on_set_title_clicked(self):
    """Otwiera dialog do nadania tytułu sesji"""
    if not self.pomodoro_logic:
        return
    
    # Nie pozwól zmieniać podczas aktywnej sesji
    if self.pomodoro_logic.is_session_active():
        return
    
    current_topic = self.pomodoro_logic.get_current_topic()
    
    dialog = SessionTitleDialog(current_topic[1], self)
    if dialog.exec() == QDialog.DialogCode.Accepted:
        new_topic = dialog.get_topic()
        
        # Ustaw w logice (topic_id będzie None dla "Ogólna")
        self.pomodoro_logic.set_topic(topic_id=None, topic_name=new_topic)
        
        # Aktualizuj UI
        self.topic_label.setText(new_topic)
```

#### 13. Obsługa zmiany ustawień

```python
def _on_work_duration_changed(self, value: int):
    """Zmiana czasu pracy"""
    if not self.pomodoro_logic:
        return
    
    self.pomodoro_logic.settings.work_duration = value
    
    # Jeśli nie ma aktywnej sesji, zaktualizuj timer
    if not self.pomodoro_logic.is_session_active():
        self.total_seconds = value * 60
        self.remaining_seconds = self.total_seconds
        self._update_display()
    
    # Zapisz ustawienia (TODO)
    # self._save_settings()

def _on_sessions_count_changed(self, value: int):
    """Zmiana liczby sesji do długiej przerwy"""
    if not self.pomodoro_logic:
        return
    
    self.pomodoro_logic.settings.sessions_count = value
    self._update_counters()
    
    # Zapisz ustawienia (TODO)
    # self._save_settings()

# Podobnie dla pozostałych ustawień...
```

#### 14. Callbacki z logiki

```python
def _on_logic_session_end(self, session_data: SessionData):
    """Callback wywoływany przez logikę po zakończeniu sesji"""
    print(f"Sesja zakończona: {session_data.session_type.value} - {session_data.status.value}")
    
    # TODO: Zapisz do bazy danych
    # self.local_db.save_session(session_data.to_dict())

def _on_logic_cycle_complete(self):
    """Callback wywoływany po ukończeniu pełnego cyklu (4 pomodoros)"""
    print("Gratulacje! Ukończono pełny cykl Pomodoro!")
    
    # TODO: Pokaż komunikat gratulacyjny
    # TODO: Zaproponuj długą przerwę
```

---

## 📊 Korzyści z integracji

### ✅ Separacja odpowiedzialności
- **PomodoroLogic:** Zarządza LOGIKĄ biznesową (co się dzieje)
- **PomodoroView:** Zarządza INTERFEJSEM użytkownika (jak wygląda)

### ✅ Łatwiejsze testowanie
- Logikę można testować bez UI (unit tests)
- UI można testować z mockami logiki

### ✅ Łatwiejsza synchronizacja
- SessionData jest gotowe do zapisu w DB
- Wszystkie dane sesji w jednym miejscu

### ✅ Spójność stanów
- Jeden source of truth (PomodoroLogic)
- Brak duplikacji stanów między UI a logiką

### ✅ Elastyczność
- Łatwo dodać nowe funkcje (np. różne tryby)
- Łatwo zmienić reguły biznesowe bez dotykania UI

---

## 🚀 TODO: Dalsze kroki

### Krok 2: Modele i baza lokalna
1. `pomodoro_models.py` - SQLAlchemy models
2. `pomodoro_local_database.py` - SQLite CRUD

### Krok 3: Integracja z UI
1. Przepisz `pomodoro_view.py` używając `PomodoroLogic`
2. Dodaj zapisy do bazy lokalnej
3. Dodaj ładowanie statystyk

### Krok 4: Popup i dialogi
1. `pomodoro_popup_timer.py`
2. Enhanced `SessionTitleDialog` (z wyborem tematu)
3. `pomodoro_logs_dialog.py`

### Krok 5: Backend i sync
1. `pomodoro_router.py` (FastAPI)
2. `pomodoro_api_client.py`
3. `pomodoro_sync_manager.py`

---

## ✅ Podsumowanie

**STATUS:** Krok 1 (Logika biznesowa) **UKOŃCZONY** ✅

**ZAIMPLEMENTOWANO:**
- ✅ Pełny manager cyklu Pomodoro
- ✅ Auto/manual mode logic
- ✅ Zarządzanie stanami sesji (IDLE/RUNNING/PAUSED/COMPLETED/INTERRUPTED/SKIPPED)
- ✅ Liczniki i statystyki
- ✅ Eksport danych do zapisu
- ✅ Testy jednostkowe przeszły pomyślnie

**GOTOWE DO:**
- Integracji z `pomodoro_view.py`
- Zapisu sesji do bazy danych
- Rozbudowy o backend i synchronizację

**NASTĘPNY KROK:** Implementacja modeli i bazy lokalnej (Krok 2)
