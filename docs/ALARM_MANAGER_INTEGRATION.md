# AlarmManager Integration Guide

## Przegląd

`AlarmManager` został rozszerzony o pełną synchronizację local-first z WebSocket real-time updates. Obsługuje dwa tryby działania:

1. **Bez synchronizacji** - tylko JSON (backward compatible)
2. **Z synchronizacją** - LocalDatabase + Server + WebSocket

## Inicjalizacja

### Tryb bez synchronizacji (JSON only)

```python
from pathlib import Path
from src.Modules.Alarm_module.alarms_logic import AlarmManager

alarm_manager = AlarmManager(
    data_dir=Path("data/alarms"),
    enable_sync=False  # Domyślnie False
)
```

Dane zapisywane do:
- `data/alarms/alarms.json`
- `data/alarms/timers.json`

### Tryb z synchronizacją (Local-first)

```python
alarm_manager = AlarmManager(
    data_dir=Path("data/alarms"),
    user_id="user123",  # Wymagane!
    api_base_url="http://localhost:8000",  # URL serwera
    auth_token="your_jwt_token",  # JWT access token
    enable_sync=True  # Włącz sync
)
```

Co się dzieje:
1. ✅ Inicjalizuje `LocalDatabase` (SQLite)
2. ✅ Uruchamia `SyncManager` (background sync co 30s)
3. ✅ Łączy `WebSocketClient` (real-time updates)
4. ✅ Ładuje dane z LocalDatabase (priorytet nad JSON)

## Operacje CRUD

API pozostaje **takie same** - AlarmManager automatycznie wybiera backend (JSON lub LocalDB):

### Alarmy

```python
from datetime import time
from src.Modules.Alarm_module.alarms_logic import Alarm, AlarmRecurrence

# Dodaj alarm
alarm = Alarm(
    id="alarm_001",
    time=time(7, 30),
    label="Pobudka",
    enabled=True,
    recurrence=AlarmRecurrence.WEEKDAYS,
    days=[0, 1, 2, 3, 4]  # Pon-Pt
)

alarm_manager.add_alarm(alarm)
# Bez sync: zapisuje do JSON
# Z sync: zapisuje do LocalDB → kolejkuje do sync → broadcastuje przez WebSocket

# Aktualizuj
alarm.enabled = False
alarm_manager.update_alarm(alarm)

# Usuń
alarm_manager.delete_alarm("alarm_001")
# Z sync: soft delete (pozostaje w bazie z deleted_at)

# Przełącz (enable/disable)
alarm_manager.toggle_alarm("alarm_001")

# Pobierz aktywne
active_alarms = alarm_manager.get_active_alarms()
```

### Timery

```python
from src.Modules.Alarm_module.alarms_logic import Timer

# Dodaj timer
timer = Timer(
    id="timer_001",
    duration=300,  # 5 minut
    label="Herbata",
    enabled=False
)

alarm_manager.add_timer(timer)

# Uruchom
alarm_manager.start_timer("timer_001")

# Zatrzymaj
alarm_manager.stop_timer("timer_001")

# Aktualizuj pozostały czas
alarm_manager.update_timer_remaining("timer_001", 120)

# Pobierz aktywne
active_timers = alarm_manager.get_active_timers()
```

## Real-time Updates

### Rejestracja UI Callbacks

```python
def on_alarm_changed(alarm: Alarm):
    """Wywoływane gdy alarm się zmieni przez WebSocket"""
    print(f"Alarm updated: {alarm.label}")
    # Odśwież UI
    self.alarm_list_widget.refresh()

def on_timer_changed(timer: Timer):
    """Wywoływane gdy timer się zmieni przez WebSocket"""
    print(f"Timer updated: {timer.label}")
    self.timer_list_widget.refresh()

# Zarejestruj callbacki
alarm_manager.set_ui_callbacks(
    on_alarm_changed=on_alarm_changed,
    on_timer_changed=on_timer_changed
)
```

### Kiedy callbacks są wywoływane?

Callbacks są wywoływane gdy:
- Inny użytkownik/urządzenie zmieni alarm/timer
- Server wykryje konflikt i wymusi update
- WebSocket otrzyma event od serwera

**Nie są wywoływane** dla lokalnych zmian (które sam wykonujesz).

## Synchronizacja

### Automatyczna synchronizacja

SyncManager automatycznie synchronizuje co 30 sekund:

```python
# Dodaj alarm
alarm_manager.add_alarm(alarm)
# → Zapisane do LocalDatabase
# → Dodane do sync_queue
# → Za max 30s zsynchronizowane z serwerem
# → Inne urządzenia dostaną WebSocket notification
```

### Manualna synchronizacja

```python
# Wymuś natychmiastową synchronizację
alarm_manager.sync_now()
```

### Statystyki synchronizacji

```python
stats = alarm_manager.get_sync_stats()

if stats:
    print(f"Sync count: {stats['sync_count']}")
    print(f"Error count: {stats['error_count']}")
    print(f"Queue size: {stats['queue_size']}")
    print(f"Last sync: {stats['last_sync_time']}")
    print(f"Network available: {stats['network_available']}")
```

### Status WebSocket

```python
if alarm_manager.is_websocket_connected():
    print("Real-time updates enabled")
else:
    print("Fallback to polling (sync every 30s)")
```

## Lifecycle Management

### Inicjalizacja w aplikacji

```python
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        
        # Inicjalizuj AlarmManager
        self.alarm_manager = AlarmManager(
            data_dir=Path("data/alarms"),
            user_id=self.current_user_id,
            api_base_url=settings.API_URL,
            auth_token=self.auth_token,
            enable_sync=True
        )
        
        # Zarejestruj UI callbacks
        self.alarm_manager.set_ui_callbacks(
            on_alarm_changed=self.refresh_alarms,
            on_timer_changed=self.refresh_timers
        )
```

### Cleanup przy zamykaniu

**WAŻNE**: Zawsze wywołuj `cleanup()` przed zamknięciem aplikacji!

```python
class MainWindow(QMainWindow):
    def closeEvent(self, event):
        # Zatrzymaj sync i WebSocket
        self.alarm_manager.cleanup()
        
        event.accept()
```

Metoda `cleanup()`:
- Zatrzymuje WebSocket client
- Zatrzymuje SyncManager
- Zamyka połączenia z bazą danych

## Migracja z JSON

Jeśli masz istniejące dane w JSON:

```python
# Krok 1: Załaduj stary manager (JSON)
old_manager = AlarmManager(
    data_dir=Path("data/old"),
    enable_sync=False
)

# Krok 2: Utwórz nowy manager (sync)
new_manager = AlarmManager(
    data_dir=Path("data/new"),
    user_id=user_id,
    api_base_url=api_url,
    auth_token=token,
    enable_sync=True
)

# Krok 3: Migruj dane
for alarm in old_manager.alarms:
    new_manager.add_alarm(alarm)

for timer in old_manager.timers:
    new_manager.add_timer(timer)

# Dane automatycznie zsynchronizują się z serwerem!
```

## Przykłady użycia

### Przykład 1: Desktop app z sync

```python
from PyQt6.QtWidgets import QApplication, QMainWindow
from pathlib import Path

class AlarmApp(QMainWindow):
    def __init__(self):
        super().__init__()
        
        self.alarm_manager = AlarmManager(
            data_dir=Path("data/alarms"),
            user_id="user123",
            api_base_url="http://localhost:8000",
            auth_token=self.get_auth_token(),
            enable_sync=True
        )
        
        self.alarm_manager.set_ui_callbacks(
            on_alarm_changed=self.on_alarm_update
        )
        
        self.setup_ui()
    
    def on_alarm_update(self, alarm: Alarm):
        """Real-time update z WebSocket"""
        # Znajdź alarm w UI i zaktualizuj
        for i in range(self.alarm_list.count()):
            item = self.alarm_list.item(i)
            if item.data(Qt.UserRole) == alarm.id:
                item.setText(f"{alarm.time} - {alarm.label}")
                break
    
    def add_alarm_clicked(self):
        """Handler przycisku 'Dodaj alarm'"""
        alarm = Alarm(
            id=self.generate_id(),
            time=self.time_edit.time().toPyTime(),
            label=self.label_edit.text(),
            enabled=True,
            recurrence=self.recurrence_combo.currentData()
        )
        
        if self.alarm_manager.add_alarm(alarm):
            self.refresh_alarm_list()
    
    def refresh_alarm_list(self):
        """Odśwież listę alarmów"""
        self.alarm_list.clear()
        for alarm in self.alarm_manager.alarms:
            item = QListWidgetItem(f"{alarm.time} - {alarm.label}")
            item.setData(Qt.UserRole, alarm.id)
            self.alarm_list.addItem(item)
    
    def closeEvent(self, event):
        self.alarm_manager.cleanup()
        event.accept()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = AlarmApp()
    window.show()
    sys.exit(app.exec())
```

### Przykład 2: Offline-first workflow

```python
# Aplikacja działa offline
alarm_manager = AlarmManager(
    data_dir=Path("data"),
    user_id="user123",
    api_base_url="http://api.example.com",
    auth_token=token,
    enable_sync=True
)

# Dodaj alarmy offline
alarm_manager.add_alarm(alarm1)  # → LocalDB, queue dla sync
alarm_manager.add_alarm(alarm2)  # → LocalDB, queue dla sync

# Sprawdź kolejkę
stats = alarm_manager.get_sync_stats()
print(f"Pending sync: {stats['queue_size']} items")

# Gdy pojawi się internet:
# → SyncManager automatycznie zsynchronizuje
# → WebSocket połączy się
# → Real-time updates zaczną działać
```

### Przykład 3: Multi-device sync

```python
# Urządzenie 1 (Desktop)
alarm_manager_desktop = AlarmManager(...)
alarm_manager_desktop.add_alarm(alarm)
# → Zapisane lokalnie
# → Zsynchronizowane z serwerem
# → Broadcast przez WebSocket

# Urządzenie 2 (Laptop)
alarm_manager_laptop = AlarmManager(...)
# → WebSocket otrzymuje notification
# → Callback on_alarm_changed() wywoływany
# → UI automatycznie się odświeża
```

## Konfiguracja

### Interwał synchronizacji

Domyślnie: 30 sekund. Można zmienić w `_init_sync()`:

```python
self.sync_manager = SyncManager(
    local_db=self.local_db,
    api_client=api_client,
    user_id=self.user_id,
    sync_interval=60  # 60 sekund
)
```

### WebSocket auto-reconnect

Domyślnie: włączony. Zmiana w `create_websocket_client()`:

```python
self.ws_client = create_websocket_client(
    base_url=api_base_url,
    auth_token=auth_token,
    auto_reconnect=True,  # True/False
    # reconnect_delay=5  # Opcjonalne
)
```

## Error Handling

### Brak połączenia z serwerem

```python
# AlarmManager działa ZAWSZE - nawet bez internetu
alarm_manager = AlarmManager(
    ...,
    enable_sync=True
)

# Jeśli server niedostępny:
# - LocalDatabase działa normalnie
# - Zmiany kolejkowane w sync_queue
# - Gdy połączenie wróci → auto-sync

stats = alarm_manager.get_sync_stats()
if stats['error_count'] > 0:
    print("Sync errors - check network connection")
```

### Brak auth token

```python
# Jeśli brak tokena → fallback do JSON
alarm_manager = AlarmManager(
    data_dir=Path("data"),
    user_id=None,  # Brak user_id
    auth_token=None,  # Brak tokena
    enable_sync=True  # Próba włączenia sync
)

# AlarmManager automatycznie:
# - Wyłącza sync (enable_sync = False)
# - Używa JSON storage
# - Loguje warning
```

## Best Practices

### 1. Zawsze wywołuj cleanup()

```python
def closeEvent(self, event):
    self.alarm_manager.cleanup()
    event.accept()
```

### 2. Używaj UI callbacks

```python
self.alarm_manager.set_ui_callbacks(
    on_alarm_changed=self.refresh_ui
)
```

### 3. Sprawdzaj sync stats

```python
stats = self.alarm_manager.get_sync_stats()
if stats and stats['error_count'] > 0:
    self.show_sync_warning()
```

### 4. Graceful degradation

```python
if self.alarm_manager.is_websocket_connected():
    self.status_label.setText("Real-time sync: ON")
else:
    self.status_label.setText("Polling sync: every 30s")
```

### 5. Obsłuż brak sieci

```python
stats = self.alarm_manager.get_sync_stats()
if stats and not stats['network_available']:
    self.show_offline_indicator()
```

## Troubleshooting

### Problem: Alarmy nie synchronizują się

**Rozwiązanie:**
1. Sprawdź `enable_sync=True`
2. Sprawdź czy `user_id` i `auth_token` są podane
3. Sprawdź logi: `logger.info("SyncManager started")`
4. Sprawdź stats: `get_sync_stats()`

### Problem: WebSocket się nie łączy

**Rozwiązanie:**
1. Sprawdź czy server działa
2. Sprawdź URL (http/https → ws/wss)
3. Sprawdź token JWT
4. Sprawdź firewall/proxy

### Problem: Callbacks nie są wywoływane

**Rozwiązanie:**
1. Sprawdź czy callbacks są zarejestrowane: `set_ui_callbacks()`
2. Sprawdź czy WebSocket jest połączony: `is_websocket_connected()`
3. Sprawdź logi WebSocket

## Dokumentacja API

Pełna dokumentacja metod AlarmManager:

### Podstawowe operacje
- `add_alarm(alarm: Alarm) -> bool`
- `update_alarm(alarm: Alarm) -> bool`
- `delete_alarm(alarm_id: str) -> bool`
- `toggle_alarm(alarm_id: str) -> bool`
- `get_active_alarms() -> List[Alarm]`

### Timer operations
- `add_timer(timer: Timer) -> bool`
- `update_timer(timer: Timer) -> bool`
- `delete_timer(timer_id: str) -> bool`
- `start_timer(timer_id: str) -> bool`
- `stop_timer(timer_id: str) -> bool`
- `update_timer_remaining(timer_id: str, remaining: int) -> bool`
- `get_active_timers() -> List[Timer]`

### Sync management
- `sync_now() -> bool` - Wymusz synchronizację
- `get_sync_stats() -> Optional[dict]` - Pobierz statystyki
- `is_websocket_connected() -> bool` - Status WebSocket
- `set_ui_callbacks(on_alarm_changed, on_timer_changed)` - Zarejestruj callbacks
- `cleanup()` - Zatrzymaj komponenty sync

## Zobacz także

- `docs/ARCHITECTURE.md` - Architektura local-first
- `docs/WEBSOCKET.md` - Dokumentacja WebSocket
- `examples/alarm_manager_integration.py` - Przykłady użycia
- `examples/websocket_example.py` - Przykłady WebSocket
