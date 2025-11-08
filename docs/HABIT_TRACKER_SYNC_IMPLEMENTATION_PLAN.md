# Plan Implementacji Synchronizacji Modułu Habit Tracker

**Data utworzenia:** 7 listopada 2025  
**Wersja:** 1.0  
**Status:** Draft - Do realizacji  
**Bazuje na:** TASKS_SYNC_IMPLEMENTATION_PLAN.md

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
Implementacja pełnej synchronizacji dwukierunkowej między lokalną bazą SQLite (offline-first) a PostgreSQL (cloud) dla modułu Habit Tracker.

### 🔑 Kluczowe założenia
1. **Offline-first:** Lokalna baza SQLite to primary source - aplikacja działa bez internetu
2. **Conflict resolution:** Last-write-wins (timestamp-based)
3. **Soft delete:** Wszystkie usunięcia są soft delete (`deleted_at`)
4. **Batch sync:** Maksymalnie 50 habit columns + 200 records/request
5. **Auto-sync:** Co 5 minut + przy zapisie/usunięciu
6. **Calendar-based:** Synchronizacja skupiona na danych miesięcznych

### 📊 Zakres synchronizacji

**Synchronizowane tabele:**
- ✅ `habit_columns` - definicje nawyków (nazwa, typ, pozycja)
- ✅ `habit_records` - wartości nawyków dla konkretnych dat

**Tylko lokalne (NIE synchronizowane):**
- ❌ `habit_settings` - ustawienia użytkownika (szerokości kolumn, preferencje UI)
- ❌ Stan UI (scroll position, selected cell)
- ❌ Cache danych (month_cache)

### ⏱️ Timeline
- **Faza 0-1 (Backend schema):** 2 dni
- **Faza 2-4 (Backend API + WS):** 3-4 dni
- **Faza 5-7 (Frontend sync):** 4-5 dni
- **Faza 8 (Integracja):** 2-3 dni
- **Faza 9 (Testing):** 2 dni
- **Faza 10 (Docs + Deploy):** 1 dzień

**RAZEM:** ~14-17 dni roboczych

---

## 2. Analiza istniejącej infrastruktury

### 2.1 Wzorzec z modułów Alarms i Tasks

**Do wykorzystania:**
```
Render_upload/app/
├── alarms_models.py          → wzór dla habit_models.py
├── alarms_router.py          → wzór dla habit_router.py
└── websocket_manager.py      → gotowy do reuse

PRO-Ka-Po_Kaizen_Freak/src/Modules/Alarm_module/
├── alarm_api_client.py       → wzór dla habit_api_client.py
├── alarm_local_database.py   → rozbuduj habit_database.py
├── alarms_sync_manager.py    → wzór dla habit_sync_manager.py
└── alarm_websocket_client.py → wzór dla habit_websocket_client.py
```

### 2.2 Różnice Habit Tracker vs Tasks/Alarms

| Aspekt | Tasks/Alarms | Habit Tracker |
|--------|--------------|---------------|
| **Struktura** | Hierarchiczna/Płaska | **Calendar-based (date-value pairs)** |
| **Relacje** | M2M (tags), Parent-child | **Simple FK (habit_id → column)** |
| **Dane** | Text, JSON | **Simple values (checkbox, counter, text)** |
| **Wzorzec użycia** | CRUD operations | **Daily tracking, bulk reads by month** |
| **Złożoność sync** | Średnia-wysoka | **Niska (tylko 2 tabele)** |
| **Batch size** | Max 100 tasks | **Max 50 habits + 200 records** |
| **WebSocket events** | 9 typów | **4 typy (create, update, delete x 2 tables)** |

### 2.3 Obecna struktura lokalnej bazy SQLite

**Plik:** `src/Modules/habbit_tracker_module/habit_database.py`

**Istniejące tabele:**
```sql
-- ✅ Gotowe do synchronizacji (z modyfikacjami)
habit_columns (id, user_id, name, type, position, scale_max, created_at, updated_at, deleted_at)
habit_records (id, user_id, habit_id, date, value, created_at, updated_at)

-- ❌ Tylko lokalne (NIE synchronizowane)
habit_settings (id, user_id, setting_key, setting_value, created_at, updated_at)
sqlite_sequence (auto-increment tracking)
```

**Kolumny sync metadata (DO DODANIA):**
```sql
-- W każdej synchronizowanej tabeli:
synced_at TIMESTAMP       -- Ostatnia synchronizacja
version INTEGER           -- Conflict resolution
remote_id TEXT            -- Mapowanie do serwera (UUID)
```

### 2.4 Specyfika Habit Tracker

**Wzorce użycia:**
- **Monthly view:** Użytkownik głównie pracuje na poziomie miesiąca
- **Daily entries:** Wprowadzanie wartości dziennych (checkbox, licznik, tekst)
- **Column management:** Rzadkie dodawanie/usuwanie nawyków
- **Settings sync:**  preferencje UI

**Typy danych nawyków:**
```python
HABIT_TYPES = {
    'checkbox': bool,      # True/False (✓/✗)
    'counter': int,        # Licznik (0, 1, 2, ...)
    'duration': str,       # Czas trwania "HH:MM"
    'time': str,          # Godzina "HH:MM"
    'scale': int,         # Skala 1-10
    'text': str           # Dowolny tekst
}
```

---

## 3. Architektura docelowa

### 3.1 Flow synchronizacji

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (PyQt6)                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐      ┌───────────────────────────┐   │
│  │ HabitTrackerView │◄────►│   HabitDatabase           │   │
│  │ - Monthly table  │      │   - habit_columns (sync)  │   │
│  │ - Daily entries  │      │   - habit_records (sync)  │   │
│  │ - Column mgmt    │      │   - habit_settings (local)│   │
│  └──────────────────┘      └───────┬───────────────────┘   │
│                                     │                        │
│                            ┌────────▼─────────┐             │
│                            │ HabitSyncManager │             │
│                            │  - Monthly sync  │             │
│                            │  - Batch records │             │
│                            │  - Column sync   │             │
│                            └────────┬─────────┘             │
│                                     │                        │
│         ┌───────────────────────────┴────────────┐          │
│         │                                        │          │
│  ┌──────▼─────────┐              ┌──────────────▼─────┐    │
│  │ HabitAPIClient │              │ HabitWebSocketClient│    │
│  │ - HTTP/REST    │              │ - Real-time sync    │    │
│  └──────┬─────────┘              └──────────────┬─────┘    │
│         │                                       │          │
└─────────┼───────────────────────────────────────┼──────────┘
          │                                       │
          │ HTTPS                                 │ WSS
          │                                       │
┌─────────▼───────────────────────────────────────▼──────────┐
│                    SERVER (FastAPI)                         │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  ┌──────────────┐      ┌────────────────┐                 │
│  │ habit_router │      │ websocket_mgr  │                 │
│  │ /api/habits  │      │   /ws/habits   │                 │
│  └──────┬───────┘      └────────┬───────┘                 │
│         │                       │                          │
│  ┌──────▼───────────────────────▼───────┐                 │
│  │       HabitsModels (Pydantic)        │                 │
│  └──────────────┬───────────────────────┘                 │
│                 │                                           │
│  ┌──────────────▼───────────────────────┐                 │
│  │   PostgreSQL - s07_habits schema     │                 │
│  │  - habit_columns                      │                 │
│  │  - habit_records                      │                 │
│  │  (habit_settings = tylko lokalnie)   │                 │
│  └───────────────────────────────────────┘                 │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

### 3.2 Sync triggers

**Automatyczna synchronizacja:**
1. **Timer:** Co 5 minut (background)
2. **On habit change:** Po dodaniu/usunięciu nawyku
3. **On record change:** Po zapisaniu wartości dziennej
4. **On startup:** Przy uruchomieniu aplikacji (initial sync)
5. **On month change:** Przy zmianie miesiąca w widoku

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

**Edge cases dla Habit Tracker:**
- **Column vs Records:** Usunięcie kolumny usuwa wszystkie rekordy
- **Pozycje kolumn:** Konflikt pozycji = server wins (canonical order)
- **Settings:** Wszystkie ustawienia UI zapisywane TYLKO lokalnie (brak synchronizacji)

---

## FAZA 0: Przygotowanie

### Krok 0.1: Backup bazy danych

**⚠️ KRYTYCZNE: Zrób backup przed zmianami!**

```bash
# Backup lokalnej bazy SQLite
cp src/Modules/habbit_tracker_module/test_habit_db.sqlite src/Modules/habbit_tracker_module/test_habit_db.backup_$(date +%Y%m%d).sqlite

# Backup wszystkich baz habit tracker w data/
find data/ -name "*habit*.db" -exec cp {} {}.backup_$(date +%Y%m%d) \;

# Backup PostgreSQL (jeśli potrzeba)
pg_dump -U postgres -h localhost kaizen_db > backup_habits_$(date +%Y%m%d).sql
```

**✅ Checklist:**
- [ ] Backup SQLite habit database
- [ ] Backup PostgreSQL (produkcja)
- [ ] Test przywracania z backup
- [ ] Zweryfikuj integralność backupu

### Krok 0.2: Przygotowanie środowiska deweloperskiego

```bash
# 1. Utwórz branch dla synchronizacji habit tracker
cd PRO-Ka-Po_Kaizen_Freak
git checkout -b feature/habit-tracker-sync
git push -u origin feature/habit-tracker-sync

# 2. Uruchom lokalny serwer FastAPI
cd Render_upload
uvicorn app.main:app --reload --port 8000

# 3. Sprawdź połączenie
curl http://localhost:8000/health
```

**✅ Checklist:**
- [ ] Branch `feature/habit-tracker-sync` utworzony
- [ ] Serwer FastAPI działa lokalnie
- [ ] Health check zwraca 200 OK
- [ ] PostgreSQL dostępny
- [ ] Test habit database lokalnie

---

## FAZA 1: Backend - Schema i Migration

### Krok 1.1: Utwórz schemat `s07_habits`

**Plik:** `Render_upload/migrations/create_habits_schema.sql`

```sql
-- =============================================================================
-- Migration: Create s07_habits schema for Habit Tracker synchronization
-- Date: 2025-11-07
-- Version: 1.0
-- =============================================================================

-- 1. Utwórz schemat
CREATE SCHEMA IF NOT EXISTS s07_habits;

-- 2. Ustaw search_path (dla wygody)
SET search_path TO s07_habits, public;

-- =============================================================================
-- TABELA: habit_columns
-- Definicje kolumn nawyków
-- =============================================================================

CREATE TABLE IF NOT EXISTS s07_habits.habit_columns (
    -- Primary key
    id TEXT PRIMARY KEY,  -- UUID z klienta
    
    -- Foreign keys
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    
    -- Core fields
    name TEXT NOT NULL CHECK (length(name) >= 1 AND length(name) <= 100),
    type TEXT NOT NULL CHECK (type IN ('checkbox', 'counter', 'duration', 'time', 'scale', 'text')),
    position INTEGER NOT NULL DEFAULT 0,
    scale_max INTEGER DEFAULT 10,  -- Dla typu 'scale'
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP,  -- Soft delete
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Constraints
    CONSTRAINT unique_user_habit_name UNIQUE (user_id, name) WHERE deleted_at IS NULL
);

-- Indexes dla habit_columns
CREATE INDEX idx_habit_columns_user ON s07_habits.habit_columns(user_id) WHERE deleted_at IS NULL;
CREATE INDEX idx_habit_columns_position ON s07_habits.habit_columns(user_id, position) WHERE deleted_at IS NULL;
CREATE INDEX idx_habit_columns_updated ON s07_habits.habit_columns(updated_at DESC);
CREATE INDEX idx_habit_columns_deleted ON s07_habits.habit_columns(deleted_at) WHERE deleted_at IS NOT NULL;

-- Trigger dla updated_at
CREATE OR REPLACE FUNCTION s07_habits.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_habit_columns_updated_at
    BEFORE UPDATE ON s07_habits.habit_columns
    FOR EACH ROW
    EXECUTE FUNCTION s07_habits.update_updated_at_column();

-- =============================================================================
-- TABELA: habit_records
-- Wartości nawyków dla konkretnych dat
-- =============================================================================

CREATE TABLE IF NOT EXISTS s07_habits.habit_records (
    -- Primary key
    id TEXT PRIMARY KEY,  -- UUID z klienta
    
    -- Foreign keys
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    habit_id TEXT NOT NULL REFERENCES s07_habits.habit_columns(id) ON DELETE CASCADE,
    
    -- Core fields
    date DATE NOT NULL,  -- Data rekordu
    value TEXT,  -- Wartość (może być pusta)
    
    -- Sync metadata
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    synced_at TIMESTAMP,
    version INTEGER NOT NULL DEFAULT 1,
    
    -- Unique constraint
    CONSTRAINT unique_user_habit_date UNIQUE (user_id, habit_id, date)
);

-- Indexes dla habit_records
CREATE INDEX idx_habit_records_user ON s07_habits.habit_records(user_id);
CREATE INDEX idx_habit_records_habit ON s07_habits.habit_records(habit_id);
CREATE INDEX idx_habit_records_date ON s07_habits.habit_records(user_id, date DESC);
CREATE INDEX idx_habit_records_month ON s07_habits.habit_records(user_id, date_trunc('month', date));
CREATE INDEX idx_habit_records_updated ON s07_habits.habit_records(updated_at DESC);

CREATE TRIGGER update_habit_records_updated_at
    BEFORE UPDATE ON s07_habits.habit_records
    FOR EACH ROW
    EXECUTE FUNCTION s07_habits.update_updated_at_column();

-- =============================================================================
-- UWAGA: habit_settings NIE są synchronizowane!
-- Wszystkie ustawienia UI (szerokości kolumn, preferencje) zapisywane tylko lokalnie w SQLite
-- =============================================================================

-- =============================================================================
-- PERMISSIONS
-- =============================================================================

-- Grant permissions dla użytkownika aplikacji (jeśli używasz innego usera)
-- GRANT USAGE ON SCHEMA s07_habits TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA s07_habits TO your_app_user;
-- GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA s07_habits TO your_app_user;

-- =============================================================================
-- VERIFICATION
-- =============================================================================

-- Sprawdź utworzone tabele
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 's07_habits' 
ORDER BY table_name;

-- Powinno pokazać 2 tabele:
-- 1. habit_columns
-- 2. habit_records
-- (habit_settings = tylko lokalne, nie w PostgreSQL)

-- Sprawdź indexes
SELECT indexname 
FROM pg_indexes 
WHERE schemaname = 's07_habits' 
ORDER BY tablename, indexname;

-- Sprawdź triggers
SELECT trigger_name, event_manipulation, event_object_table 
FROM information_schema.triggers 
WHERE trigger_schema = 's07_habits' 
ORDER BY event_object_table, trigger_name;
```

**Wykonanie:**
```bash
# Połącz się z bazą
psql -U postgres -h localhost -d kaizen_db

# Wykonaj migration
\i Render_upload/migrations/create_habits_schema.sql

# Weryfikacja
\dt s07_habits.*  # Lista tabel
\di s07_habits.*  # Lista indexów
```

**✅ Checklist:**
- [ ] Schemat `s07_habits` utworzony
- [ ] 2 tabele utworzone (habit_columns, habit_records)
- [ ] Wszystkie indexy utworzone
- [ ] Triggery `updated_at` działają
- [ ] Constraints (FK, unique) działają
- [ ] Weryfikacja zakończona sukcesem

### Krok 1.2: Rozszerz lokalną bazę SQLite o metadata sync

**Plik:** `src/Modules/habbit_tracker_module/habit_database.py`

**Modyfikacja metody `_init_database()`:**

```python
def _init_database(self):
    """Inicjalizacja struktury bazy danych z sync metadata"""
    with sqlite3.connect(self.db_path) as conn:
        cursor = conn.cursor()
        
        # ========== TABELA: habit_columns (z sync metadata) ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habit_columns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                position INTEGER NOT NULL,
                scale_max INTEGER DEFAULT 10,
                
                -- ✅ DODAJ sync metadata:
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                deleted_at TIMESTAMP,
                synced_at TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                -- ✅ DODAJ remote_id dla mapowania:
                remote_id TEXT UNIQUE,  -- UUID z serwera
                
                UNIQUE(user_id, name)
            )
        """)
        
        # ========== TABELA: habit_records (z sync metadata) ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habit_records (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                habit_id INTEGER NOT NULL,
                date TEXT NOT NULL,
                value TEXT,
                
                -- ✅ DODAJ sync metadata:
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                synced_at TIMESTAMP,
                version INTEGER DEFAULT 1,
                
                -- ✅ DODAJ remote_id:
                remote_id TEXT UNIQUE,
                
                FOREIGN KEY (habit_id) REFERENCES habit_columns(id) ON DELETE CASCADE,
                UNIQUE(user_id, habit_id, date)
            )
        """)
        
        # ========== TABELA: habit_settings (TYLKO LOKALNA - bez sync) ==========
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS habit_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                setting_key TEXT NOT NULL,
                setting_value TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, setting_key)
            )
        """)
        
        # ✅ DODAJ triggery dla updated_at:
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_habit_columns_timestamp 
            AFTER UPDATE ON habit_columns
            BEGIN
                UPDATE habit_columns SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END;
        """)
        
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_habit_records_timestamp 
            AFTER UPDATE ON habit_records
            BEGIN
                UPDATE habit_records SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END;
        """)
        
        # Trigger dla habit_settings (lokalne tylko)
        cursor.execute("""
            CREATE TRIGGER IF NOT EXISTS update_habit_settings_timestamp 
            AFTER UPDATE ON habit_settings
            BEGIN
                UPDATE habit_settings SET updated_at = CURRENT_TIMESTAMP 
                WHERE id = NEW.id;
            END;
        """)
        
        # Indexy dla sync
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_habit_columns_remote ON habit_columns(remote_id)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_habit_records_remote ON habit_records(remote_id)")
        # Indexy dla sync (tylko dla synchronizowanych tabel)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_habit_columns_sync ON habit_columns(synced_at, updated_at)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_habit_records_sync ON habit_records(synced_at, updated_at)")
        
        # Indexy lokalne dla habit_settings (bez sync)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_habit_settings_user_key ON habit_settings(user_id, setting_key)")
        
        conn.commit()
        logger.info("[HABIT DB] Database schema initialized with sync metadata")
```

**✅ Checklist:**
- [ ] 2 synchronizowane tabele rozszerzone o sync metadata
- [ ] Triggery `updated_at` utworzone
- [ ] Kolumny `remote_id` dodane
- [ ] Indexy sync utworzone
- [ ] Migration testowana na świeżej bazie
- [ ] Backup przed zmianami wykonany

---

## FAZA 2: Backend - Models

### Krok 2.1: Utwórz plik `habit_models.py`

**Plik:** `Render_upload/app/habit_models.py`

```python
"""
SQLAlchemy Models dla Habit Tracker
Schema: s07_habits
"""
from sqlalchemy import Column, String, Integer, Date, Text, ForeignKey, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime, date

from .database import Base


# =============================================================================
# MODEL: HabitColumn
# =============================================================================

class HabitColumn(Base):
    """
    Model kolumny nawyku (definicja nawyku)
    """
    __tablename__ = 'habit_columns'
    __table_args__ = {'schema': 's07_habits'}
    
    # Primary key
    id = Column(String, primary_key=True)  # UUID z klienta
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    
    # Core fields
    name = Column(Text, nullable=False)
    type = Column(String(20), nullable=False)  # checkbox, counter, duration, time, scale, text
    position = Column(Integer, default=0, nullable=False)
    scale_max = Column(Integer, default=10, nullable=False)
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    deleted_at = Column(TIMESTAMP, nullable=True)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<HabitColumn(id={self.id}, name={self.name}, type={self.type})>"


# =============================================================================
# MODEL: HabitRecord
# =============================================================================

class HabitRecord(Base):
    """
    Model rekordu nawyku (wartość dla konkretnej daty)
    """
    __tablename__ = 'habit_records'
    __table_args__ = {'schema': 's07_habits'}
    
    # Primary key
    id = Column(String, primary_key=True)  # UUID z klienta
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    habit_id = Column(String, ForeignKey('s07_habits.habit_columns.id', ondelete='CASCADE'), nullable=False)
    
    # Core fields
    date = Column(Date, nullable=False)
    value = Column(Text, nullable=True)  # Wartość może być pusta
    
    # Sync metadata
    created_at = Column(TIMESTAMP, default=datetime.utcnow, nullable=False)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)
    
    def __repr__(self):
        return f"<HabitRecord(habit_id={self.habit_id}, date={self.date}, value={self.value})>"


# =============================================================================
# UWAGA: HabitSettings nie ma modelu SQLAlchemy
# Wszystkie ustawienia zapisywane tylko lokalnie w SQLite
# =============================================================================


# =============================================================================
# Dla kompatybilności
# =============================================================================
HabitsSchema = HabitColumn
```

### Krok 2.2: Utwórz Pydantic schemas

**Plik:** `Render_upload/app/habit_schemas.py`

```python
"""
Pydantic Schemas dla Habit Tracker API
Request/Response models dla walidacji i serializacji
"""
from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any, Literal
from datetime import datetime, date


# =============================================================================
# HABIT COLUMN SCHEMAS
# =============================================================================

class HabitColumnBase(BaseModel):
    """Bazowy schemat kolumny nawyku"""
    id: str = Field(..., min_length=1, max_length=100)
    name: str = Field(..., min_length=1, max_length=100)
    type: Literal['checkbox', 'counter', 'duration', 'time', 'scale', 'text']
    position: int = Field(default=0, ge=0)
    scale_max: int = Field(default=10, ge=1, le=100)
    version: int = Field(default=1, ge=1)
    
    @validator('name')
    def name_not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError('Name cannot be empty')
        return v.strip()


class HabitColumnCreate(HabitColumnBase):
    """Schema dla tworzenia kolumny nawyku"""
    user_id: str = Field(..., description="User ID from authentication")


class HabitColumnUpdate(BaseModel):
    """Schema dla aktualizacji kolumny nawyku"""
    name: Optional[str] = Field(None, min_length=1, max_length=100)
    type: Optional[Literal['checkbox', 'counter', 'duration', 'time', 'scale', 'text']] = None
    position: Optional[int] = Field(None, ge=0)
    scale_max: Optional[int] = Field(None, ge=1, le=100)
    version: int = Field(..., ge=1, description="Current version for conflict detection")


class HabitColumnResponse(HabitColumnBase):
    """Schema odpowiedzi kolumny nawyku"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# HABIT RECORD SCHEMAS
# =============================================================================

class HabitRecordBase(BaseModel):
    """Bazowy schemat rekordu nawyku"""
    id: str = Field(..., min_length=1, max_length=100)
    habit_id: str = Field(..., min_length=1, max_length=100)
    date: date
    value: Optional[str] = Field(None, max_length=500)
    version: int = Field(default=1, ge=1)


class HabitRecordCreate(HabitRecordBase):
    """Schema dla tworzenia rekordu nawyku"""
    user_id: str


class HabitRecordUpdate(BaseModel):
    """Schema dla aktualizacji rekordu nawyku"""
    value: Optional[str] = Field(None, max_length=500)
    version: int = Field(..., ge=1, description="Current version for conflict detection")


class HabitRecordResponse(HabitRecordBase):
    """Schema odpowiedzi rekordu nawyku"""
    user_id: str
    created_at: datetime
    updated_at: datetime
    synced_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True


# =============================================================================
# UWAGA: Brak HabitSettings schemas 
# Wszystkie ustawienia UI zarządzane tylko lokalnie
# =============================================================================


# =============================================================================
# BULK SYNC SCHEMAS
# =============================================================================

class BulkHabitSyncRequest(BaseModel):
    """Schema żądania bulk sync dla habit tracker"""
    user_id: str
    columns: List[HabitColumnBase] = Field(default_factory=list)
    records: List[HabitRecordBase] = Field(default_factory=list)
    last_sync: Optional[datetime] = None
    
    @validator('columns')
    def limit_columns_count(cls, v):
        if len(v) > 50:
            raise ValueError('Maximum 50 habit columns per sync request')
        return v
    
    @validator('records')
    def limit_records_count(cls, v):
        if len(v) > 200:
            raise ValueError('Maximum 200 habit records per sync request')
        return v


class BulkHabitSyncItemResult(BaseModel):
    """Wynik dla pojedynczego item w bulk sync"""
    id: str
    entity_type: Literal['column', 'record']
    status: Literal['success', 'conflict', 'error']
    version: Optional[int] = None
    error: Optional[str] = None
    server_version: Optional[int] = None


class BulkHabitSyncResponse(BaseModel):
    """Schema odpowiedzi bulk sync"""
    results: List[BulkHabitSyncItemResult]
    success_count: int
    conflict_count: int
    error_count: int
    server_timestamp: datetime


# =============================================================================
# OTHER SCHEMAS
# =============================================================================

class MonthlyDataRequest(BaseModel):
    """Schema żądania danych miesięcznych"""
    user_id: str
    year: int = Field(..., ge=2020, le=2030)
    month: int = Field(..., ge=1, le=12)


class MonthlyDataResponse(BaseModel):
    """Schema odpowiedzi danych miesięcznych"""
    columns: List[HabitColumnResponse]
    records: List[HabitRecordResponse]
    month: int
    year: int
    last_sync: Optional[datetime] = None


class DeleteResponse(BaseModel):
    """Schema odpowiedzi usunięcia"""
    message: str
    id: str
    deleted_at: datetime
```

**✅ Checklist:**
- [ ] 2 modele SQLAlchemy utworzone (HabitColumn, HabitRecord)
- [ ] Pydantic schemas dla wszystkich operacji
- [ ] Validators dla wymaganych pól
- [ ] Limit 50 kolumn + 200 rekordów w bulk sync
- [ ] Monthly data endpoints schemas
- [ ] habit_settings pominiete (tylko lokalnie)

---

**Kontynuować do Fazy 3-10?**

Ten adaptowany plan różni się od planu Tasks w następujących kluczowych obszarach:

### 🔄 Kluczowe różnice w adaptacji:

1. **Prostsze relacje:** Habit Tracker ma tylko 3 tabele vs 8 w Tasks
2. **Calendar-based sync:** Skupienie na danych miesięcznych vs hierarchicznym CRUD
3. **Mniejsze batch sizes:** 50 kolumn + 200 rekordów vs 100 tasków
4. **Inne typy danych:** Proste wartości (checkbox, licznik) vs złożone JSON
5. **Mniej WebSocket events:** 6 vs 9 typów zdarzeń
6. **Schema s07_habits:** Nowy schemat vs modyfikacja istniejącego

### 📋 Status implementacji:
- ✅ **Faza 0:** Przygotowanie (backup, env)
- ✅ **Faza 1:** Backend Schema PostgreSQL + migracja SQLite  
- ✅ **Faza 2:** Backend Models (SQLAlchemy + Pydantic)
- 🔜 **Fazy 3-10:** Router, WebSocket, Frontend, Integration, Testing

Czy chcesz kontynuować z kolejnymi fazami implementacji?