# Architektura Local-First dla Modułu Alarmów

## Przegląd

Moduł alarmów wykorzystuje architekturę **local-first**, która zapewnia:
- ✅ Pełną funkcjonalność offline
- ✅ Automatyczną synchronizację z serwerem gdy dostępna jest sieć
- ✅ Rozwiązywanie konfliktów przez wersjonowanie
- ✅ Soft delete dla bezpiecznej synchronizacji
- ✅ Kolejkowanie operacji do synchronizacji

## Komponenty

### 1. LocalDatabase (`local_database.py`)

Główny komponent zarządzający lokalnym SQLite storage.

#### Struktura Unified Table

```sql
CREATE TABLE alarms_timers (
    -- Podstawowe pola
    id TEXT PRIMARY KEY,
    user_id TEXT,
    type TEXT CHECK(type IN ('alarm', 'timer')),  -- Unified approach
    label TEXT NOT NULL,
    enabled INTEGER DEFAULT 1,
    
    -- Pola specyficzne dla alarmów
    alarm_time TEXT,           -- Format: HH:MM
    recurrence TEXT,           -- 'once', 'daily', 'weekly', 'weekdays', 'weekends'
    days TEXT,                 -- JSON array: [0,1,2,3,4,5,6]
    
    -- Pola specyficzne dla timerów
    duration INTEGER,          -- Sekundy
    remaining INTEGER,         -- Pozostały czas
    repeat INTEGER,            -- Czy powtarzać
    started_at TEXT,           -- ISO timestamp
    
    -- Wspólne ustawienia
    play_sound INTEGER DEFAULT 1,
    show_popup INTEGER DEFAULT 1,
    custom_sound TEXT,         -- Ścieżka do pliku dźwiękowego
    
    -- Metadane synchronizacji
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    deleted_at TEXT,           -- Soft delete
    synced_at TEXT,            -- Ostatnia synchronizacja
    version INTEGER DEFAULT 1, -- Conflict resolution
    needs_sync INTEGER DEFAULT 0
);
```

#### Sync Queue Table

```sql
CREATE TABLE sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL,    -- 'alarm' lub 'timer'
    entity_id TEXT NOT NULL,
    operation TEXT NOT NULL,      -- 'upsert' lub 'delete'
    data TEXT,                    -- JSON payload
    created_at TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    last_error TEXT
);
```

### 2. Operacje CRUD

#### Alarmy

```python
# Zapisz alarm (INSERT or UPDATE)
local_db.save_alarm(alarm, user_id="user123")
# - Tworzy/aktualizuje rekord
# - Ustawia needs_sync=1
# - Dodaje do sync_queue

# Pobierz alarm
alarm = local_db.get_alarm("alarm_id")

# Pobierz wszystkie alarmy użytkownika
alarms = local_db.get_all_alarms(user_id="user123")

# Usuń alarm (soft delete)
local_db.delete_alarm("alarm_id", soft=True)
# - Ustawia deleted_at
# - Incrementuje version
# - Dodaje do sync_queue

# Hard delete (tylko lokalne)
local_db.delete_alarm("alarm_id", soft=False)
```

#### Timery

Analogicznie jak alarmy, ale z metodami `save_timer()`, `get_timer()`, etc.

### 3. Synchronizacja

#### Workflow

```
1. Użytkownik tworzy/edytuje alarm
   ↓
2. Zapisz w LocalDatabase (instant)
   ↓
3. Oznacz needs_sync=1
   ↓
4. Dodaj do sync_queue
   ↓
5. Background worker sprawdza sieć
   ↓
6. Gdy sieć dostępna → sync z serwerem
   ↓
7. Serwer odpowiada success/conflict
   ↓
8. Jeśli success → mark_alarm_synced()
   ↓
9. Jeśli conflict → resolve + retry
```

#### Metody Synchronizacji

```python
# Pobierz niezsynchronizowane alarmy
unsynced = local_db.get_unsynced_alarms()

# Pobierz kolejkę synchronizacji
queue = local_db.get_sync_queue(limit=10)

# Oznacz jako zsynchronizowany
local_db.mark_alarm_synced("alarm_id")

# Usuń z kolejki po sukcesie
local_db.remove_from_sync_queue(queue_id)

# Zaktualizuj błąd w kolejce
local_db.update_sync_queue_error(queue_id, "Network timeout")
```

### 4. Rozwiązywanie Konfliktów

#### Strategia: Last-Write-Wins z wersjonowaniem

```python
# Przykład konfliktu:
# - Lokalna wersja: version=3, updated_at="2024-01-10 14:30"
# - Serwer wersja: version=4, updated_at="2024-01-10 14:35"

if server_version > local_version:
    # Serwer wygrywa - nadpisz lokalną kopię
    local_db.save_alarm(server_alarm, user_id)
    local_db.mark_alarm_synced(alarm_id)
else:
    # Lokalna wersja nowsza - wyślij ponownie
    sync_to_server(local_alarm)
```

## Integracja z PostgreSQL

### Schema Mapping

**SQLite → PostgreSQL**

```
alarms_timers (SQLite) → s04_alarms_timers.alarms_timers (PostgreSQL)
```

Struktura jest identyczna, tylko PostgreSQL ma dodatkowe constrainty:

```sql
-- PostgreSQL specific
CONSTRAINT fk_user FOREIGN KEY (user_id) 
    REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE

-- Auto-update trigger
CREATE TRIGGER update_updated_at_column
BEFORE UPDATE ON s04_alarms_timers.alarms_timers
FOR EACH ROW
EXECUTE FUNCTION update_updated_at_column();
```

### Sync Endpoints (do zaimplementowania)

```python
# API Client
POST   /api/alarms-timers         # Upsert (create or update)
GET    /api/alarms-timers         # List user's items
GET    /api/alarms-timers/:id     # Get specific item
DELETE /api/alarms-timers/:id     # Soft delete
POST   /api/alarms-timers/sync    # Bulk sync
```

## Przykłady Użycia

### 1. Dodawanie Alarmu

```python
from Modules.Alarm_module.alarm_local_database import LocalDatabase
from Modules.Alarm_module.alarms_logic import Alarm, AlarmRecurrence
from datetime import time

db = LocalDatabase()

alarm = Alarm(
    id="alarm_123",
    time=time(7, 30),
    label="Pobudka",
    enabled=True,
    recurrence=AlarmRecurrence.WEEKDAYS,
    days=[1, 2, 3, 4, 5],
    play_sound=True,
    show_popup=True,
    custom_sound="/path/to/alarm.mp3"
)

# Zapisz lokalnie
db.save_alarm(alarm, user_id="user123")

# Alarm jest teraz:
# - Zapisany w SQLite
# - Oznaczony needs_sync=1
# - Dodany do sync_queue
# - Gotowy do synchronizacji
```

### 2. Pobieranie i Edycja

```python
# Pobierz alarm
alarm = db.get_alarm("alarm_123")

# Edytuj
alarm.time = time(8, 0)
alarm.label = "Nowa pobudka"

# Zapisz zmiany
db.save_alarm(alarm, user_id="user123")
# version automatycznie incrementowany w bazie
```

### 3. Soft Delete

```python
# Usuń alarm (soft delete)
db.delete_alarm("alarm_123", soft=True)

# Alarm jest:
# - Nadal w bazie (deleted_at ustawiony)
# - Niewidoczny dla użytkownika (WHERE deleted_at IS NULL)
# - W sync_queue do usunięcia na serwerze
# - Bezpieczny dla synchronizacji
```

### 4. Synchronizacja (pseudo-kod)

```python
# W background worker
def sync_worker():
    while True:
        if network_available():
            queue = db.get_sync_queue(limit=10)
            
            for item in queue:
                try:
                    if item['operation'] == 'upsert':
                        response = api_client.sync_alarm(item['data'])
                    elif item['operation'] == 'delete':
                        response = api_client.delete_alarm(item['entity_id'])
                    
                    if response.success:
                        if item['entity_type'] == 'alarm':
                            db.mark_alarm_synced(item['entity_id'])
                        else:
                            db.mark_timer_synced(item['entity_id'])
                        
                        db.remove_from_sync_queue(item['id'])
                    else:
                        db.update_sync_queue_error(item['id'], response.error)
                        
                except Exception as e:
                    db.update_sync_queue_error(item['id'], str(e))
        
        sleep(30)  # Retry co 30 sekund
```

## Zalety Unified Table Approach

### 1. Prostota Synchronizacji

- **Jeden endpoint** zamiast dwóch: `/api/alarms-timers`
- **Jeden model SQLAlchemy** zamiast dwóch
- **Jedna logika CRUD** dla obu typów

### 2. Łatwiejsze Rozszerzanie

```python
# Dodanie nowego typu:
# type='reminder' - przypomnienia
# type='countdown' - odliczanie do wydarzenia
```

### 3. Spójność Danych

- **Wspólne metadane** (version, synced_at, needs_sync)
- **Unified history** - wszystkie operacje w jednym miejscu
- **Łatwiejsze indexy** - user_id + type composite

### 4. Mniejszy Overhead

- **Mniej tabel** = mniej JOINów
- **Mniej kodu** = mniej bugów
- **Mniej migracji** = szybszy rozwój

## Bezpieczeństwo

### User Isolation

```sql
-- Użytkownik widzi tylko swoje dane
SELECT * FROM alarms_timers 
WHERE user_id = ? AND deleted_at IS NULL
```

### Soft Delete

```sql
-- Soft delete zachowuje dane dla synchronizacji
UPDATE alarms_timers 
SET deleted_at = ?, 
    updated_at = ?, 
    needs_sync = 1, 
    version = version + 1
WHERE id = ?
```

### Wersjonowanie

```sql
-- Każda zmiana incrementuje wersję
version = version + 1

-- Pozwala wykryć konflikty:
-- if local.version != server.version → conflict!
```

## Następne Kroki

1. ✅ **LocalDatabase implementation** - GOTOWE
2. ⏳ **API Client** - do implementacji
3. ⏳ **Sync Manager** - background worker
4. ⏳ **FastAPI Endpoints** - serwer
5. ⏳ **Conflict Resolution** - strategia rozwiązywania
6. ⏳ **API Documentation** - Swagger/OpenAPI

## Pliki

- `src/Modules/Alarm_module/alarm_local_database.py` - LocalDatabase class
- `src/Modules/Alarm_module/alarm_api_client.py` - AlarmsAPIClient class
- `src/Modules/Alarm_module/alarms_sync_manager.py` - SyncManager class
- `src/Modules/Alarm_module/alarms_logic.py` - Alarm/Timer dataclasses
- `docs/alarms_database_schema.sql` - PostgreSQL schema
- `docs/local_database_architecture.md` - Ten dokument

## Testowanie

```python
# Przykładowy test
import pytest
from Modules.Alarm_module.alarm_local_database import LocalDatabase

def test_save_and_retrieve_alarm():
    db = LocalDatabase(":memory:")  # Test w pamięci
    
    alarm = create_test_alarm()
    db.save_alarm(alarm, user_id="test_user")
    
    retrieved = db.get_alarm(alarm.id)
    assert retrieved.label == alarm.label
    assert retrieved.time == alarm.time
    
def test_soft_delete():
    db = LocalDatabase(":memory:")
    
    alarm = create_test_alarm()
    db.save_alarm(alarm, user_id="test_user")
    db.delete_alarm(alarm.id, soft=True)
    
    # Nie powinien być widoczny
    assert db.get_alarm(alarm.id) is None
    
    # Ale powinien być w kolejce sync
    queue = db.get_sync_queue()
    assert len(queue) > 0
    assert queue[0]['operation'] == 'delete'
```

---

**Ostatnia aktualizacja:** 2024-01-10  
**Autor:** PRO-Ka-Po Development Team  
**Wersja:** 1.0
