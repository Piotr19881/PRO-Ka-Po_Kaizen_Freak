# Plan Implementacji Synchronizacji Modułu Zadań i Kanban

**Data utworzenia:** 6 listopada 2025  
**Wersja:** 1.0  
**Status:** Draft - Do realizacji

---

## 📋 Spis treści

1. [Podsumowanie wykonawcze](#1-podsumowanie-wykonawcze)
2. [Analiza istniejącej infrastruktury](#2-analiza-istniejącej-infrastruktury)
3. [Architektura docelowa](#3-architektura-docelowa)
4. [Faza 0: Przygotowanie](#faza-0-przygotowanie)
5. [Faza 1: Backend - Schema i Migration](#faza-1-backend---schema-i-migration)
6. [Faza 2: Backend - Models](#faza-2-backend---models)
7. [Faza 3: Backend - Router](#faza-3-backend---router)
8. [Faza 4: Backend - WebSocket](#faza-4-backend---websocket)
9. [Faza 5: Frontend - API Client](#faza-5-frontend---api-client)
10. [Faza 6: Frontend - Sync Manager](#faza-6-frontend---sync-manager)
11. [Faza 7: Frontend - WebSocket Client](#faza-7-frontend---websocket-client)
12. [Faza 8: Integracja z istniejącą logiką](#faza-8-integracja-z-istniejącą-logiką)
13. [Faza 9: Testowanie](#faza-9-testowanie)
14. [Faza 10: Dokumentacja i deployment](#faza-10-dokumentacja-i-deployment)

---

## 1. Podsumowanie wykonawcze

### 🎯 Cel projektu
Implementacja pełnej synchronizacji dwukierunkowej między lokalną bazą SQLite (offline-first) a PostgreSQL (cloud) dla modułu Zadań i Kanban.

### 🔑 Kluczowe założenia
1. **Offline-first:** Lokalna baza SQLite to primary source - aplikacja działa bez internetu
2. **Conflict resolution:** Last-write-wins (timestamp-based)
3. **Soft delete:** Wszystkie usunięcia są soft delete (`deleted_at`)
4. **Batch sync:** Maksymalnie 100 zadań/request
5. **Auto-sync:** Co 5 minut + przy zapisie/usunięciu
6. **Unified module:** Kanban i Tasks to jeden moduł synchronizacji

### 📊 Zakres synchronizacji

**Synchronizowane tabele:**
- ✅ `tasks` - zadania główne
- ✅ `task_tags` - tagi zadań
- ✅ `task_custom_lists` - niestandardowe listy
- ✅ `kanban_items` - pozycje Kanban
- ✅ `kanban_settings` - ustawienia tablicy
- ✅ `task_tag_assignments` - relacje zadanie↔tag
- ✅ `task_history` - historia zmian
- ✅ `columns_config` - konfiguracja kolumn (widoczność/kolejność)

**Tylko lokalne (NIE synchronizowane):**
- ❌ Szerokości kolumn (UI preferences)
- ❌ Stan UI (rozwinięte subtaski, scroll position)
- ❌ Lokalne filtry

### ⏱️ Timeline
- **Faza 0-1 (Backend schema):** 2-3 dni
- **Faza 2-4 (Backend API + WS):** 3-4 dni
- **Faza 5-7 (Frontend sync):** 4-5 dni
- **Faza 8 (Integracja):** 2-3 dni
- **Faza 9 (Testing):** 2-3 dni
- **Faza 10 (Docs + Deploy):** 1-2 dni

**RAZEM:** ~15-20 dni roboczych

---

## 2. Analiza istniejącej infrastruktury

### 2.1 Wzorzec z modułu Alarms

**Zalety obecnej implementacji:**
- ✅ Dobrze zaprojektowana architektura local-first
- ✅ Automatic token refresh w `alarm_api_client.py`
- ✅ Exponential backoff w retry logic
- ✅ WebSocket z auto-reconnect
- ✅ Bulk sync z conflict resolution
- ✅ Status LED integration

**Do wykorzystania:**
```
Render_upload/app/
├── alarms_models.py          → wzór dla tasks_models.py
├── alarms_router.py          → wzór dla tasks_router.py
└── websocket_manager.py      → gotowy do reuse

PRO-Ka-Po_Kaizen_Freak/src/Modules/Alarm_module/
├── alarm_api_client.py       → wzór dla task_api_client.py
├── alarm_local_database.py   → rozbuduj task_local_database.py
├── alarms_sync_manager.py    → wzór dla tasks_sync_manager.py
└── alarm_websocket_client.py → wzór dla task_websocket_client.py
```

### 2.2 Różnice Tasks vs Alarms

| Aspekt | Alarms/Timers | Tasks/Kanban |
|--------|---------------|--------------|
| **Struktura** | Płaska (alarms_timers) | **Hierarchiczna (parent-child)** |
| **Relacje** | Brak | **Subtasks, Tags (M2M)** |
| **Custom fields** | Brak | **JSON custom_data** |
| **History** | Brak | **task_history tracking** |
| **Złożoność sync** | Niska | **Średnia-wysoka** |
| **Batch size** | Bez limitu | **Max 100** |
| **WebSocket events** | 6 typów | **9 typów (+moved, +reordered)** |

### 2.3 Obecna struktura lokalnej bazy

**Plik:** `src/Modules/task_module/task_local_database.py`

**Istniejące tabele:**
```sql
-- ✅ Gotowe do synchronizacji
tasks (id, user_id, title, description, status, ...)
task_tags (id, user_id, name, color)
task_custom_lists (id, user_id, name, values)
kanban_items (id, user_id, task_id, column_type, position)
kanban_settings (id, user_id, settings_json)
task_tag_assignments (id, task_id, tag_id)
task_history (id, user_id, task_id, action_type, ...)
columns_config (id, user_id, columns_json)

-- ❌ Tylko lokalne
sqlite_sequence (auto-increment tracking)
```

**Kolumny sync metadata (DO DODANIA):**
```sql
-- W każdej synchronizowanej tabeli:
created_at TIMESTAMP      -- Utworzenie
updated_at TIMESTAMP      -- Ostatnia edycja
deleted_at TIMESTAMP      -- Soft delete
synced_at TIMESTAMP       -- Ostatnia synchronizacja
version INTEGER           -- Conflict resolution
```

---

## 3. Architektura docelowa

### 3.1 Flow synchronizacji

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (PyQt6)                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌───────────────┐                   │
│  │  TaskView    │◄────►│  TaskLogic    │                   │
│  │  KanbanView  │      │               │                   │
│  └──────────────┘      └───────┬───────┘                   │
│                                 │                            │
│                        ┌────────▼─────────┐                 │
│                        │ TaskLocalDatabase│                 │
│                        │   (SQLite)       │                 │
│                        └────────┬─────────┘                 │
│                                 │                            │
│                        ┌────────▼──────────┐                │
│                        │ TasksSyncManager  │                │
│                        │  - Queue ops      │                │
│                        │  - Auto sync      │                │
│                        │  - Conflicts      │                │
│                        └────────┬──────────┘                │
│                                 │                            │
│         ┌───────────────────────┴────────────┐              │
│         │                                    │              │
│  ┌──────▼─────────┐              ┌──────────▼────────┐     │
│  │ TaskAPIClient  │              │ TaskWebSocketClient│     │
│  │ - HTTP/REST    │              │ - Real-time events │     │
│  └──────┬─────────┘              └──────────┬────────┘     │
│         │                                    │              │
└─────────┼────────────────────────────────────┼──────────────┘
          │                                    │
          │ HTTPS                              │ WSS
          │                                    │
┌─────────▼────────────────────────────────────▼──────────────┐
│                    SERVER (FastAPI)                          │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌────────────────┐                  │
│  │ tasks_router │      │ websocket_mgr  │                  │
│  │  /api/tasks  │      │   /ws/tasks    │                  │
│  └──────┬───────┘      └────────┬───────┘                  │
│         │                       │                           │
│  ┌──────▼───────────────────────▼───────┐                  │
│  │       TasksModels (Pydantic)         │                  │
│  └──────────────┬───────────────────────┘                  │
│                 │                                            │
│  ┌──────────────▼───────────────────────┐                  │
│  │   PostgreSQL - s06_tasks schema      │                  │
│  │  - tasks                              │                  │
│  │  - task_tags                          │                  │
│  │  - kanban_items                       │                  │
│  │  - ...                                │                  │
│  └───────────────────────────────────────┘                  │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Sync triggers

**Automatyczna synchronizacja:**
1. **Timer:** Co 5 minut (background)
2. **On save:** Po zapisaniu zadania
3. **On delete:** Po usunięciu zadania
4. **On startup:** Przy uruchomieniu aplikacji (initial sync)
5. **On reconnect:** Po przywróceniu połączenia sieciowego

**Manualna synchronizacja:**
- Przycisk "Synchronizuj" w UI
- Shortcut Ctrl+R (refresh)

### 3.3 Conflict resolution strategy

**Last-Write-Wins (LWW):**
```python
def resolve_conflict(local_item, remote_item):
    """
    Porównaj updated_at timestamps.
    Nowszy timestamp wygrywa.
    """
    if local_item['updated_at'] > remote_item['updated_at']:
        return 'local'  # Wyślij lokalne na serwer
    else:
        return 'remote'  # Zastosuj remote lokalnie
```

**Edge cases:**
- **Identyczne timestamps:** Remote wygrywa (server is source of truth)
- **Deleted vs Updated:** Deleted wygrywa (explicit user action)
- **Relacje (subtasks):** Parent musi istnieć przed sync child

---

## FAZA 0: Przygotowanie

### Krok 0.1: Analiza dependencies

**Wymagane biblioteki (sprawdź `requirements.txt`):**

Backend:
```txt
fastapi>=0.104.0
uvicorn>=0.24.0
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.9
pydantic>=2.0.0
websockets>=12.0
```

Frontend:
```txt
PyQt6>=6.6.0
requests>=2.31.0
websockets>=12.0
```

**✅ Checklist:**
- [ ] Zainstaluj brakujące dependencies
- [ ] Sprawdź kompatybilność wersji
- [ ] Zaktualizuj `requirements.txt`

### Krok 0.2: Backup bazy danych

**⚠️ KRYTYCZNE: Zrób backup przed zmianami!**

```bash
# Backup lokalnej bazy SQLite
cp data/tasks.db data/tasks.db.backup_$(date +%Y%m%d)

# Backup PostgreSQL (jeśli potrzeba)
pg_dump -U postgres -h localhost kaizen_db > backup_$(date +%Y%m%d).sql
```

**✅ Checklist:**
- [ ] Backup SQLite
- [ ] Backup PostgreSQL (produkcja)
- [ ] Test przywracania z backup

### Krok 0.3: Przygotowanie środowiska deweloperskiego

```bash
# 1. Utwórz branch dla synchronizacji
cd PRO-Ka-Po_Kaizen_Freak
git checkout -b feature/tasks-sync
git push -u origin feature/tasks-sync

# 2. Uruchom lokalny serwer FastAPI
cd Render_upload
uvicorn app.main:app --reload --port 8000

# 3. Sprawdź połączenie
curl http://localhost:8000/health
```

**✅ Checklist:**
- [ ] Branch `feature/tasks-sync` utworzony
- [ ] Serwer FastAPI działa lokalnie
- [ ] Health check zwraca 200 OK
- [ ] PostgreSQL dostępny

---

## FAZA 1: Backend - Schema i Migration

### Krok 1.1: Usuń stary schemat `s02_tasks`

**⚠️ UWAGA:** To operacja nieodwracalna!

**Plik:** `Render_upload/migrations/drop_old_tasks_schema.sql`

```sql
-- Migration: Drop old s02_tasks schema
-- Date: 2025-11-06
-- Author: Sync Implementation Team

-- UWAGA: To usunie WSZYSTKIE dane w schemacie s02_tasks!
-- Wykonaj tylko jeśli masz backup lub schemat jest pusty/testowy

DROP SCHEMA IF EXISTS s02_tasks CASCADE;

-- Verify schema is gone
SELECT schema_name 
FROM information_schema.schemata 
WHERE schema_name = 's02_tasks';
-- Powinno zwrócić 0 wierszy
```

**Wykonanie:**
```bash
# Połącz się z bazą
psql -U postgres -h localhost -d kaizen_db

# Wykonaj migration
\i Render_upload/migrations/drop_old_tasks_schema.sql

# Weryfikacja
\dn  # Lista schematów - nie powinno być s02_tasks
```

**✅ Checklist:**
- [ ] Backup wykonany ✅
- [ ] Migration wykonana
- [ ] Schemat `s02_tasks` usunięty
- [ ] Weryfikacja: `\dn` nie pokazuje s02_tasks

**🔴 Ostrzeżenia:**
1. **Nie wykonuj na produkcji** bez zgody i backupu!
2. Sprawdź czy żadne inne tabele nie mają FK do s02_tasks
3. Zweryfikuj że stary schemat nie jest używany

---

### Krok 1.2: Utwórz nowy schemat `s06_tasks`

**Plik:** `Render_upload/migrations/create_tasks_schema_v2.sql`

```sql
-- =============================================================================
-- Migration: Create s06_tasks schema for Tasks & Kanban synchronization
-- Date: 2025-11-06
-- Version: 2.0
-- =============================================================================

-- 1. Utwórz schemat
CREATE SCHEMA IF NOT EXISTS s06_tasks;

-- 2. Ustaw search_path (dla wygody)
SET search_path TO s06_tasks, public;

-- =============================================================================
-- TABELA: tasks
-- Główna tabela zadań
-- =============================================================================

CREATE TABLE IF NOT EXISTS s06_tasks.tasks (
    -- Primary key
    id TEXT PRIMARY KEY,  -- UUID lub GUID z klienta
    
    -- Foreign keys
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    parent_id TEXT REFERENCES s06_tasks.tasks(id) ON DELETE CASCADE,  -- Dla subtasków
    
    -- Core fields
    title TEXT NOT NULL CHECK (length(title) >= 1 AND length(title) <= 500),
    description TEXT,
    status BOOLEAN DEFAULT FALSE,  -- false=todo, true=done
    
    -- Dates
    due_date TIMESTAMP,
    completion_date TIMESTAMP,
    alarm_date TIMESTAMP,
    
    -- Relations
    note_id INTEGER,  -- FK do notatek (jeśli dostępne)
    
    -- Custom data (JSON)
    custom_data JSONB DEFAULT '{}',
    
    -- Metadata
    archived BOOLEAN DEFAULT FALSE,
    "order" INTEGER DEFAULT 0,
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,  -- Soft delete
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Constraints
    CONSTRAINT valid_parent CHECK (parent_id IS NULL OR parent_id != id)
);

-- Indexes dla tasks
CREATE INDEX idx_tasks_user ON s06_tasks.tasks(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_parent ON s06_tasks.tasks(parent_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_status ON s06_tasks.tasks(user_id, status) WHERE deleted_at IS NULL;
CREATE INDEX idx_tasks_updated ON s06_tasks.tasks(updated_at DESC);
CREATE INDEX idx_tasks_deleted ON s06_tasks.tasks(deleted_at) WHERE deleted_at IS NOT NULL;

-- Trigger dla updated_at
CREATE OR REPLACE FUNCTION s06_tasks.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_tasks_updated_at
    BEFORE UPDATE ON s06_tasks.tasks
    FOR EACH ROW
    EXECUTE FUNCTION s06_tasks.update_updated_at_column();

-- =============================================================================
-- TABELA: task_tags
-- Tagi zadań
-- =============================================================================

CREATE TABLE IF NOT EXISTS s06_tasks.task_tags (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(name) >= 1 AND length(name) <= 100),
    color TEXT NOT NULL DEFAULT '#CCCCCC' CHECK (color ~ '^#[0-9A-Fa-f]{6}$'),
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Unique constraint
    CONSTRAINT unique_user_tag_name UNIQUE (user_id, name) WHERE deleted_at IS NULL
);

CREATE INDEX idx_task_tags_user ON s06_tasks.task_tags(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_task_tags_updated ON s06_tasks.task_tags(updated_at DESC);

CREATE TRIGGER update_task_tags_updated_at
    BEFORE UPDATE ON s06_tasks.task_tags
    FOR EACH ROW
    EXECUTE FUNCTION s06_tasks.update_updated_at_column();

-- =============================================================================
-- TABELA: task_tag_assignments
-- Relacja M2M: zadania ↔ tagi
-- =============================================================================

CREATE TABLE IF NOT EXISTS s06_tasks.task_tag_assignments (
    id TEXT PRIMARY KEY,
    task_id TEXT NOT NULL REFERENCES s06_tasks.tasks(id) ON DELETE CASCADE,
    tag_id TEXT NOT NULL REFERENCES s06_tasks.task_tags(id) ON DELETE CASCADE,
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Unique constraint
    CONSTRAINT unique_task_tag UNIQUE (task_id, tag_id)
);

CREATE INDEX idx_task_tag_assign_task ON s06_tasks.task_tag_assignments(task_id);
CREATE INDEX idx_task_tag_assign_tag ON s06_tasks.task_tag_assignments(tag_id);

-- =============================================================================
-- TABELA: task_custom_lists
-- Niestandardowe listy (np. priorytety, statusy)
-- =============================================================================

CREATE TABLE IF NOT EXISTS s06_tasks.task_custom_lists (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL CHECK (length(name) >= 1 AND length(name) <= 100),
    values JSONB NOT NULL DEFAULT '[]',  -- Array wartości
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Unique constraint
    CONSTRAINT unique_user_list_name UNIQUE (user_id, name) WHERE deleted_at IS NULL
);

CREATE INDEX idx_custom_lists_user ON s06_tasks.task_custom_lists(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_custom_lists_updated ON s06_tasks.task_custom_lists(updated_at DESC);

CREATE TRIGGER update_task_custom_lists_updated_at
    BEFORE UPDATE ON s06_tasks.task_custom_lists
    FOR EACH ROW
    EXECUTE FUNCTION s06_tasks.update_updated_at_column();

-- =============================================================================
-- TABELA: kanban_items
-- Pozycje na tablicy Kanban
-- =============================================================================

CREATE TABLE IF NOT EXISTS s06_tasks.kanban_items (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL REFERENCES s06_tasks.tasks(id) ON DELETE CASCADE,
    column_type TEXT NOT NULL CHECK (column_type IN ('todo', 'in_progress', 'done', 'on_hold', 'review')),
    position INTEGER NOT NULL DEFAULT 0,
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Unique constraint
    CONSTRAINT unique_user_task_kanban UNIQUE (user_id, task_id) WHERE deleted_at IS NULL
);

CREATE INDEX idx_kanban_items_user ON s06_tasks.kanban_items(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_kanban_items_column ON s06_tasks.kanban_items(user_id, column_type, position) WHERE deleted_at IS NULL;
CREATE INDEX idx_kanban_items_updated ON s06_tasks.kanban_items(updated_at DESC);

CREATE TRIGGER update_kanban_items_updated_at
    BEFORE UPDATE ON s06_tasks.kanban_items
    FOR EACH ROW
    EXECUTE FUNCTION s06_tasks.update_updated_at_column();

-- =============================================================================
-- TABELA: kanban_settings
-- Ustawienia tablicy Kanban dla użytkownika
-- =============================================================================

CREATE TABLE IF NOT EXISTS s06_tasks.kanban_settings (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    settings JSONB NOT NULL DEFAULT '{}',  -- Wszystkie ustawienia jako JSON
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Unique constraint
    CONSTRAINT unique_user_kanban_settings UNIQUE (user_id)
);

CREATE INDEX idx_kanban_settings_user ON s06_tasks.kanban_settings(user_id);
CREATE INDEX idx_kanban_settings_updated ON s06_tasks.kanban_settings(updated_at DESC);

CREATE TRIGGER update_kanban_settings_updated_at
    BEFORE UPDATE ON s06_tasks.kanban_settings
    FOR EACH ROW
    EXECUTE FUNCTION s06_tasks.update_updated_at_column();

-- =============================================================================
-- TABELA: task_history
-- Historia zmian zadań (audit log)
-- =============================================================================

CREATE TABLE IF NOT EXISTS s06_tasks.task_history (
    id SERIAL PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    task_id TEXT NOT NULL REFERENCES s06_tasks.tasks(id) ON DELETE CASCADE,
    action_type TEXT NOT NULL,  -- 'created', 'updated', 'deleted', 'kanban_move', etc.
    old_value TEXT,
    new_value TEXT,
    details JSONB DEFAULT '{}',
    
    -- Metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    
    -- Sync metadata (historia też jest synchronizowana!)
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX idx_task_history_task ON s06_tasks.task_history(task_id, created_at DESC);
CREATE INDEX idx_task_history_user ON s06_tasks.task_history(user_id, created_at DESC);
CREATE INDEX idx_task_history_created ON s06_tasks.task_history(created_at DESC);

-- =============================================================================
-- TABELA: columns_config
-- Konfiguracja kolumn widoku zadań
-- =============================================================================

CREATE TABLE IF NOT EXISTS s06_tasks.columns_config (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    columns JSONB NOT NULL DEFAULT '[]',  -- Array konfiguracji kolumn
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Unique constraint
    CONSTRAINT unique_user_columns_config UNIQUE (user_id)
);

CREATE INDEX idx_columns_config_user ON s06_tasks.columns_config(user_id);
CREATE INDEX idx_columns_config_updated ON s06_tasks.columns_config(updated_at DESC);

CREATE TRIGGER update_columns_config_updated_at
    BEFORE UPDATE ON s06_tasks.columns_config
    FOR EACH ROW
    EXECUTE FUNCTION s06_tasks.update_updated_at_column();

-- =============================================================================
-- PERMISSIONS
-- =============================================================================

-- Grant permissions dla użytkownika aplikacji (jeśli używasz innego usera niż postgres)
-- GRANT USAGE ON SCHEMA s06_tasks TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA s06_tasks TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA s06_tasks TO your_app_user;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Sprawdź utworzone tabele
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 's06_tasks' 
ORDER BY table_name;

-- Powinno pokazać 8 tabel:
-- 1. columns_config
-- 2. kanban_items
-- 3. kanban_settings
-- 4. task_custom_lists
-- 5. task_history
-- 6. task_tag_assignments
-- 7. task_tags
-- 8. tasks

-- Sprawdź indexes
SELECT indexname 
FROM pg_indexes 
WHERE schemaname = 's06_tasks' 
ORDER BY tablename, indexname;

-- Sprawdź triggers
SELECT trigger_name, event_manipulation, event_object_table 
FROM information_schema.triggers 
WHERE trigger_schema = 's06_tasks' 
ORDER BY event_object_table, trigger_name;
```

**Wykonanie:**
```bash
# Połącz się z bazą
psql -U postgres -h localhost -d kaizen_db

# Wykonaj migration
\i Render_upload/migrations/create_tasks_schema_v2.sql

# Weryfikacja
\dt s06_tasks.*  # Lista tabel
\di s06_tasks.*  # Lista indexów
```

**✅ Checklist:**
- [ ] Schemat `s06_tasks` utworzony
- [ ] 8 tabel utworzonych
- [ ] Wszystkie indexy utworzone
- [ ] Triggery `updated_at` działają
- [ ] Constraints (FK, unique) działają
- [ ] Weryfikacja zakończona sukcesem

**🔴 Ostrzeżenia:**
1. **ID jako TEXT:** Używamy UUID/GUID z klienta (generowane lokalnie)
2. **Soft delete:** `deleted_at IS NULL` w większości queries
3. **Version conflict:** Increment version przy każdym UPDATE
4. **Parent-child:** Sprawdzaj cykliczne referencje (constraint `valid_parent`)

---

### Krok 1.3: Rozszerz lokalną bazę SQLite o metadata sync

**Plik:** `src/Modules/task_module/task_local_database.py`

**Modyfikacja metody `_init_database()`:**

```python
# W sekcji CREATE TABLE tasks - DODAJ kolumny:
cursor.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        title TEXT NOT NULL,
        description TEXT,
        status INTEGER DEFAULT 0,
        
        -- ... istniejące kolumny ...
        
        -- ✅ DODAJ sync metadata:
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        deleted_at TIMESTAMP,
        synced_at TIMESTAMP,
        version INTEGER DEFAULT 1,
        
        -- ✅ DODAJ remote_id dla mapowania:
        remote_id TEXT UNIQUE  -- UUID z serwera
    )
""")

# ✅ DODAJ triggery dla updated_at:
cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS update_tasks_timestamp 
    AFTER UPDATE ON tasks
    BEGIN
        UPDATE tasks SET updated_at = CURRENT_TIMESTAMP 
        WHERE id = NEW.id;
    END;
""")
```

**Analogicznie dla wszystkich synchronizowanych tabel:**
- `task_tags`
- `task_custom_lists`
- `kanban_items`
- `kanban_settings`
- `task_tag_assignments`
- `task_history`
- `columns_config`

**✅ Checklist:**
- [ ] Wszystkie 8 tabel rozszerzone o sync metadata
- [ ] Triggery `updated_at` utworzone
- [ ] Kolumna `remote_id` dodana (dla mapowania)
- [ ] Migration testowana na świeżej bazie
- [ ] Backup przed zmianami wykonany

**🔴 Ostrzeżenia:**
1. **ALTER TABLE:** Jeśli tabele już mają dane, użyj `ALTER TABLE ADD COLUMN`
2. **Default values:** Ustaw domyślne wartości dla istniejących wierszy
3. **Index remote_id:** Utwórz index dla szybkiego mapowania

**Przykład migracji z danymi:**
```python
def migrate_add_sync_metadata(cursor):
    """Dodaj sync metadata do istniejących tabel"""
    # Sprawdź czy kolumny już istnieją
    cursor.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'created_at' not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    
    if 'updated_at' not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
        # Ustaw updated_at = created_at dla istniejących
        cursor.execute("UPDATE tasks SET updated_at = created_at WHERE updated_at IS NULL")
    
    if 'deleted_at' not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN deleted_at TIMESTAMP")
    
    if 'synced_at' not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN synced_at TIMESTAMP")
    
    if 'version' not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN version INTEGER DEFAULT 1")
    
    if 'remote_id' not in columns:
        cursor.execute("ALTER TABLE tasks ADD COLUMN remote_id TEXT UNIQUE")
```

---

## FAZA 2: Backend - Models

### Krok 2.1: Utwórz plik `tasks_models.py`

**Plik:** `Render_upload/app/tasks_models.py`

```python
"""
SQLAlchemy Models dla Tasks & Kanban
Schema: s06_tasks
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, Text, ForeignKey, CheckConstraint, TIMESTAMP, JSON, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB
from datetime import datetime

from .database import Base


# =============================================================================
# MODEL: Task
# =============================================================================

class Task(Base):
    """
    Model zadania.
    
    Obsługuje zarówno zadania główne jak i subtaski (via parent_id).
    """
    __tablename__ = 'tasks'
    __table_args__ = {'schema': 's06_tasks'}
    
    # Primary key
    id = Column(String, primary_key=True)  # UUID z klienta
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    parent_id = Column(String, ForeignKey('s06_tasks.tasks.id', ondelete='CASCADE'), nullable=True)
    
    # Core fields
    title = Column(Text, nullable=False)
    description = Column(Text, nullable=True)
    status = Column(Boolean, default=False, nullable=False)  # False=todo, True=done
    
    # Dates
    due_date = Column(DateTime, nullable=True)
    completion_date = Column(DateTime, nullable=True)
    alarm_date = Column(DateTime, nullable=True)
    
    # Relations
    note_id = Column(Integer, nullable=True)
    
    # Custom data (JSON)
    custom_data = Column(JSONB, default={}, nullable=False, server_default=text("'{}'::jsonb"))
    
    # Metadata
    archived = Column(Boolean, default=False, nullable=False)
    order = Column(Integer, default=0, nullable=False)
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<Task(id={self.id}, title={self.title}, status={self.status})>"


# =============================================================================
# MODEL: TaskTag
# =============================================================================

class TaskTag(Base):
    """Model tagu zadania"""
    __tablename__ = 'task_tags'
    __table_args__ = {'schema': 's06_tasks'}
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    color = Column(String(7), nullable=False, default='#CCCCCC')
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<TaskTag(id={self.id}, name={self.name})>"


# =============================================================================
# MODEL: TaskTagAssignment
# =============================================================================

class TaskTagAssignment(Base):
    """Relacja M2M między zadaniami a tagami"""
    __tablename__ = 'task_tag_assignments'
    __table_args__ = {'schema': 's06_tasks'}
    
    id = Column(String, primary_key=True)
    task_id = Column(String, ForeignKey('s06_tasks.tasks.id', ondelete='CASCADE'), nullable=False)
    tag_id = Column(String, ForeignKey('s06_tasks.task_tags.id', ondelete='CASCADE'), nullable=False)
    
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    
    def __repr__(self):
        return f"<TaskTagAssignment(task_id={self.task_id}, tag_id={self.tag_id})>"


# =============================================================================
# MODEL: TaskCustomList
# =============================================================================

class TaskCustomList(Base):
    """Niestandardowe listy (np. priorytety, statusy)"""
    __tablename__ = 'task_custom_lists'
    __table_args__ = {'schema': 's06_tasks'}
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    name = Column(Text, nullable=False)
    values = Column(JSONB, nullable=False, default=[], server_default=text("'[]'::jsonb"))
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<TaskCustomList(id={self.id}, name={self.name})>"


# =============================================================================
# MODEL: KanbanItem
# =============================================================================

class KanbanItem(Base):
    """Pozycja na tablicy Kanban"""
    __tablename__ = 'kanban_items'
    __table_args__ = {'schema': 's06_tasks'}
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(String, ForeignKey('s06_tasks.tasks.id', ondelete='CASCADE'), nullable=False)
    column_type = Column(String(20), nullable=False)  # 'todo', 'in_progress', 'done', etc.
    position = Column(Integer, default=0, nullable=False)
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<KanbanItem(task_id={self.task_id}, column={self.column_type}, pos={self.position})>"


# =============================================================================
# MODEL: KanbanSettings
# =============================================================================

class KanbanSettings(Base):
    """Ustawienia tablicy Kanban użytkownika"""
    __tablename__ = 'kanban_settings'
    __table_args__ = {'schema': 's06_tasks'}
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    settings = Column(JSONB, nullable=False, default={}, server_default=text("'{}'::jsonb"))
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<KanbanSettings(user_id={self.user_id})>"


# =============================================================================
# MODEL: TaskHistory
# =============================================================================

class TaskHistory(Base):
    """Historia zmian zadań (audit log)"""
    __tablename__ = 'task_history'
    __table_args__ = {'schema': 's06_tasks'}
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    task_id = Column(String, ForeignKey('s06_tasks.tasks.id', ondelete='CASCADE'), nullable=False)
    action_type = Column(String(50), nullable=False)
    old_value = Column(Text, nullable=True)
    new_value = Column(Text, nullable=True)
    details = Column(JSONB, default={}, server_default=text("'{}'::jsonb"))
    
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<TaskHistory(task_id={self.task_id}, action={self.action_type})>"


# =============================================================================
# MODEL: ColumnsConfig
# =============================================================================

class ColumnsConfig(Base):
    """Konfiguracja kolumn widoku zadań"""
    __tablename__ = 'columns_config'
    __table_args__ = {'schema': 's06_tasks'}
    
    id = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    columns = Column(JSONB, nullable=False, default=[], server_default=text("'[]'::jsonb"))
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<ColumnsConfig(user_id={self.user_id})>"


# =============================================================================
# Dla kompatybilności
# =============================================================================
TasksSchema = Task
```

**✅ Checklist:**
- [ ] Wszystkie 8 modeli utworzone
- [ ] Relationships (ForeignKey) poprawne
- [ ] Sync metadata w każdym modelu
- [ ] `__repr__` dla debugowania
- [ ] Schema name = 's06_tasks'

**🔴 Ostrzeżenia:**
1. **JSONB vs JSON:** Używamy JSONB dla wydajności (PostgreSQL specific)
2. **server_default:** Ustawiamy dla compatibility z SQLAlchemy
3. **ondelete='CASCADE':** Usunięcie user usuwa wszystkie zadania
4. **parent_id:** Self-reference wymaga nullable=True

---

### Krok 2.2: Utwórz Pydantic schemas

**Plik:** `Render_upload/app/tasks_schemas.py`

```python
"""
Pydantic Schemas dla Tasks & Kanban API
Request/Response models dla walidacji i serializacji
"""
from pydantic import BaseModel, Field, validator, root_validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime


# =============================================================================
# BASE SCHEMAS
# =============================================================================

class TaskBase(BaseModel):
    """Bazowy schemat zadania"""
    id: str = Field(..., min_length=1, max_length=100)
    title: str = Field(..., min_length=1, max_length=500)
    description: Optional[str] = None
    status: bool = False
    parent_id: Optional[str] = None
    
    # Dates
    due_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    alarm_date: Optional[datetime] = None
    
    # Relations
    note_id: Optional[int] = None
    
    # Custom data
    custom_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Metadata
    archived: bool = False
    order: int = 0
    
    # Sync
    version: int = Field(default=1, ge=1)
    
    @validator('title')
    def title_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Title cannot be empty')
        return v.strip()
    
    @validator('custom_data', pre=True)
    def ensure_dict(cls, v):
        if v is None:
            return {}
        if not isinstance(v, dict):
            raise ValueError('custom_data must be a dict')
        return v


class TaskCreate(TaskBase):
    """Schema dla tworzenia zadania"""
    user_id: str = Field(..., description="User ID from authentication")


class TaskUpdate(BaseModel):
    """Schema dla aktualizacji zadania (partial update)"""
    title: Optional[str] = Field(None, min_length=1, max_length=500)
    description: Optional[str] = None
    status: Optional[bool] = None
    parent_id: Optional[str] = None
    due_date: Optional[datetime] = None
    completion_date: Optional[datetime] = None
    alarm_date: Optional[datetime] = None
    note_id: Optional[int] = None
    custom_data: Optional[Dict[str, Any]] = None
    archived: Optional[bool] = None
    order: Optional[int] = None
    version: int = Field(..., ge=1, description="Current version for conflict detection")


class TaskResponse(TaskBase):
    """Schema odpowiedzi zadania"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True  # Pydantic v2


# =============================================================================
# TAG SCHEMAS
# =============================================================================

class TaskTagBase(BaseModel):
    """Bazowy schemat tagu"""
    id: str
    name: str = Field(..., min_length=1, max_length=100)
    color: str = Field(default='#CCCCCC', pattern=r'^#[0-9A-Fa-f]{6}$')
    version: int = Field(default=1, ge=1)


class TaskTagCreate(TaskTagBase):
    """Schema dla tworzenia tagu"""
    user_id: str


class TaskTagResponse(TaskTagBase):
    """Schema odpowiedzi tagu"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# KANBAN SCHEMAS
# =============================================================================

class KanbanItemBase(BaseModel):
    """Bazowy schemat pozycji Kanban"""
    id: str
    task_id: str
    column_type: Literal['todo', 'in_progress', 'done', 'on_hold', 'review']
    position: int = Field(default=0, ge=0)
    version: int = Field(default=1, ge=1)


class KanbanItemCreate(KanbanItemBase):
    """Schema dla tworzenia pozycji Kanban"""
    user_id: str


class KanbanItemResponse(KanbanItemBase):
    """Schema odpowiedzi pozycji Kanban"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# BULK SYNC SCHEMAS
# =============================================================================

class BulkSyncRequest(BaseModel):
    """Schema żądania bulk sync"""
    user_id: str
    tasks: List[TaskBase] = Field(default_factory=list)
    tags: List[TaskTagBase] = Field(default_factory=list)
    kanban_items: List[KanbanItemBase] = Field(default_factory=list)
    last_sync: Optional[datetime] = None
    
    @validator('tasks')
    def limit_tasks_count(cls, v):
        if len(v) > 100:
            raise ValueError('Maximum 100 tasks per sync request')
        return v


class BulkSyncItemResult(BaseModel):
    """Wynik dla pojedynczego item w bulk sync"""
    id: str
    entity_type: Literal['task', 'tag', 'kanban_item']
    status: Literal['success', 'conflict', 'error']
    version: Optional[int] = None
    error: Optional[str] = None
    server_version: Optional[int] = None


class BulkSyncResponse(BaseModel):
    """Schema odpowiedzi bulk sync"""
    results: List[BulkSyncItemResult]
    success_count: int
    conflict_count: int
    error_count: int
    server_timestamp: datetime


# =============================================================================
# OTHER SCHEMAS
# =============================================================================

class DeleteResponse(BaseModel):
    """Schema odpowiedzi usunięcia"""
    message: str
    id: str
    deleted_at: datetime


class ConflictErrorResponse(BaseModel):
    """Schema odpowiedzi konfliktu wersji"""
    detail: str = "Version conflict detected"
    local_version: int
    server_version: int
    server_data: TaskResponse


class ListTasksResponse(BaseModel):
    """Schema odpowiedzi listy zadań"""
    items: List[TaskResponse]
    count: int
    last_sync: Optional[datetime] = None
```

**✅ Checklist:**
- [ ] Wszystkie base schemas utworzone
- [ ] Create/Update/Response variants
- [ ] Validators dla wymaganych pól
- [ ] Limit 100 zadań w bulk sync
- [ ] Conflict resolution schemas

**🔴 Ostrzeżenia:**
1. **Field validation:** Waliduj długości stringów
2. **Max 100 items:** Enforuj limit w bulk sync
3. **Version required:** Zawsze wymagaj version dla UPDATE
4. **Datetime:** Używaj timezone-aware datetime

---

Kontynuować do Fazy 3 (Router)?


Dokument zawiera:

✅ 10 szczegółowych faz implementacji:

✅ Faza 0: Przygotowanie (backup, env, dependencies)
✅ Faza 1: Backend - Schema PostgreSQL + migracja SQLite
✅ Faza 2: Backend - SQLAlchemy Models + Pydantic Schemas
🔜 Faza 3: Backend - Router (API endpoints)
🔜 Faza 4: Backend - WebSocket (real-time)
🔜 Faza 5: Frontend - API Client
🔜 Faza 6: Frontend - Sync Manager
🔜 Faza 7: Frontend - WebSocket Client
🔜 Faza 8: Integracja z task_logic.py
🔜 Faza 9-10: Testing & Deploy
Kluczowe punkty planu:

📊 Analiza różnic Tasks vs Alarms:

Struktura hierarchiczna (parent-child)
Relacje M2M (tags)
JSON custom_data
History tracking
Większa złożoność sync
🏗️ Architektura:

Schema s06_tasks (8 tabel)
Local-first z SQLite offline cache
Last-write-wins conflict resolution
Batch sync max 100 items
Auto-sync co 5 min
⚠️ Uwagi i pułapki przy każdym kroku

Czy chcesz:

Kontynuować tworzenie dokumentu (Fazy 3-10)?
Rozpocząć implementację od Fazy 0?
Doprecyzować jakiś konkretny aspekt?