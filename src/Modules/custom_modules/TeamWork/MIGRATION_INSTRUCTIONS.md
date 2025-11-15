# 📊 INSTRUKCJE MIGRACJI BAZY DANYCH TEAMWORK

## 🎯 WYJAŚNIENIE ARCHITEKTURY

Aplikacja TeamWork używa **dwóch baz danych** do obsługi synchronizacji offline:

```
┌─────────────────────────────────────────────────────────────┐
│                    ARCHITEKTURA SYNC                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐        │
│  │  APLIKACJA       │  SYNC   │   API SERVER     │        │
│  │  (Lokalna)       │ ◄─────► │   (Render)       │        │
│  │                  │         │                  │        │
│  │  SQLite          │         │  PostgreSQL      │        │
│  │  database.db     │         │  s02_teamwork    │        │
│  └──────────────────┘         └──────────────────┘        │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 1️⃣ **Baza Lokalna (SQLite)**
- **Lokalizacja**: `src/Modules/custom_modules/TeamWork/database.db`
- **Typ**: SQLite
- **Cel**: Przechowywanie danych offline w aplikacji
- **Migracja**: `sync_schema_migration_sqlite.sql`

### 2️⃣ **Baza Serwerowa (PostgreSQL)**
- **Lokalizacja**: Render Cloud (`dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com`)
- **Typ**: PostgreSQL
- **Schemat**: `s02_teamwork`
- **Cel**: Centralny serwer API dla synchronizacji wielourządzeniowej
- **Migracja**: `sync_schema_migration.sql`

---

## 🚀 INSTRUKCJA WYKONANIA MIGRACJI

### ✅ KROK 1: Migracja Bazy PostgreSQL (API Server)

**Kiedy**: Przed uruchomieniem serwera API na Render

**Jak**:
1. Otwórz VS Code z rozszerzeniem PostgreSQL (już podłączone)
2. Wybierz połączenie: `dpg-d433vlidbo4c73a516p0-a`
3. Otwórz plik: `sync_schema_migration.sql`
4. Kliknij prawym przyciskiem myszy → **Run Query**
5. Sprawdź wyniki w zakładce Results

**Sprawdzenie**:
```sql
-- Sprawdź czy kolumny zostały dodane
SELECT column_name 
FROM information_schema.columns 
WHERE table_schema = 's02_teamwork' 
  AND table_name = 'work_groups'
  AND column_name IN ('server_id', 'last_synced', 'sync_status', 'version', 'modified_locally');

-- Sprawdź czy tabele sync zostały utworzone
SELECT table_name 
FROM information_schema.tables 
WHERE table_schema = 's02_teamwork' 
  AND table_name IN ('sync_metadata', 'sync_conflicts');
```

---

### ✅ KROK 2: Migracja Bazy SQLite (Aplikacja Lokalna)

**Kiedy**: Przed pierwszym uruchomieniem modułu TeamWork w aplikacji

**Jak** (Opcja A - Automatyczna via Python):
```python
# Uruchom w terminalu z głównego katalogu projektu
cd "C:\Users\probu\Desktop\Aplikacje komercyjne\PRO-Ka-Po_Kaizen_Freak\PRO-Ka-Po_Kaizen_Freak"
python -c "
import sqlite3
import os

# Ścieżka do bazy
db_path = 'src/Modules/custom_modules/TeamWork/database.db'
migration_path = 'src/Modules/custom_modules/TeamWork/sync_schema_migration_sqlite.sql'

# Wczytaj skrypt migracji
with open(migration_path, 'r', encoding='utf-8') as f:
    migration_sql = f.read()

# Wykonaj migrację
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.executescript(migration_sql)
conn.commit()
conn.close()

print('✅ Migracja SQLite zakończona pomyślnie!')
"
```

**Jak** (Opcja B - Manualna via SQLite Browser):
1. Zainstaluj DB Browser for SQLite: https://sqlitebrowser.org/
2. Otwórz plik: `src/Modules/custom_modules/TeamWork/database.db`
3. Zakładka **Execute SQL**
4. Wklej zawartość: `sync_schema_migration_sqlite.sql`
5. Kliknij **Execute**

**Sprawdzenie**:
```sql
-- Sprawdź czy kolumny zostały dodane
PRAGMA table_info(work_groups);

-- Sprawdź czy tabele sync istnieją
SELECT name FROM sqlite_master 
WHERE type='table' 
  AND name IN ('sync_metadata', 'sync_conflicts');
```

---

## 📋 CO DODAJE MIGRACJA?

### Kolumny Sync w Tabelach (5 tabel):
- `work_groups`
- `topics`
- `messages`
- `tasks`
- `topic_files`

**Dodane kolumny** (identyczne w obu bazach):
```
server_id          - ID rekordu na serwerze API
last_synced        - Ostatni czas synchronizacji
sync_status        - Status: pending/synced/conflict/error
version            - Wersja dla wykrywania konfliktów
modified_locally   - Czy zmieniono lokalnie (wymaga sync)
```

### Nowe Tabele Sync:

#### `sync_metadata`
- Globalne metadane synchronizacji
- Ostatnie czasy pull/push dla każdego typu encji
- Licznik błędów synchronizacji

#### `sync_conflicts`
- Logi konfliktów synchronizacji
- Przechowuje dane lokalne i zdalne
- Strategia rozwiązania konfliktu

### Indeksy Wydajności:
- `idx_groups_sync`, `idx_topics_sync`, etc. - dla statusu sync
- `idx_groups_server`, `idx_topics_server`, etc. - dla mapowania ID

### Triggery Automatyczne:
- Automatycznie oznaczają `modified_locally = TRUE` przy edycji
- Ustawiają `sync_status = 'pending'` dla zmienionych rekordów

---

## ⚠️ RÓŻNICE MIĘDZY MIGRACJAMI

| Cecha | SQLite | PostgreSQL |
|-------|--------|------------|
| **Auto-increment** | `INTEGER PRIMARY KEY AUTOINCREMENT` | `SERIAL PRIMARY KEY` |
| **Typ daty** | `DATETIME` | `TIMESTAMP` |
| **Boolean** | `INTEGER DEFAULT 0` | `BOOLEAN DEFAULT FALSE` |
| **String** | `TEXT` | `VARCHAR(n)` lub `TEXT` |
| **Triggery** | `CREATE TRIGGER IF NOT EXISTS` | `CREATE OR REPLACE FUNCTION` + trigger |
| **Upsert** | `INSERT OR IGNORE` | `INSERT ... ON CONFLICT DO NOTHING` |
| **Schemat** | Brak (default) | `s02_teamwork.` prefix |

---

## 🔍 TROUBLESHOOTING

### Błąd: "relation work_groups does not exist"
**Przyczyna**: Próba uruchomienia migracji PostgreSQL w bazie SQLite lub odwrotnie
**Rozwiązanie**: Upewnij się, że używasz właściwej migracji dla właściwej bazy:
- SQLite → `sync_schema_migration_sqlite.sql`
- PostgreSQL → `sync_schema_migration.sql`

### Błąd: "duplicate column name"
**Przyczyna**: Migracja została już wykonana
**Rozwiązanie**: Pomiń ten błąd lub użyj `ADD COLUMN IF NOT EXISTS` (już jest w migracji)

### Błąd: "no such table: work_groups"
**Przyczyna**: Baza nie została zainicjalizowana podstawowym schematem
**Rozwiązanie**: Najpierw uruchom `database_schema.sql`, potem migrację sync

### Błąd: "syntax error near AUTOINCREMENT" (PostgreSQL)
**Przyczyna**: Użyto migracji SQLite w bazie PostgreSQL
**Rozwiązanie**: Użyj `sync_schema_migration.sql` (bez _sqlite)

### Błąd: "syntax error near SERIAL" (SQLite)
**Przyczyna**: Użyto migracji PostgreSQL w bazie SQLite
**Rozwiązanie**: Użyj `sync_schema_migration_sqlite.sql`

---

## ✅ WERYFIKACJA PO MIGRACJI

### PostgreSQL:
```sql
-- Sprawdź strukturę tabeli
\d s02_teamwork.work_groups

-- Sprawdź triggery
SELECT trigger_name, event_object_table 
FROM information_schema.triggers 
WHERE trigger_schema = 's02_teamwork';

-- Sprawdź dane w sync_metadata
SELECT * FROM s02_teamwork.sync_metadata;
```

### SQLite:
```sql
-- Sprawdź strukturę tabeli
PRAGMA table_info(work_groups);

-- Sprawdź triggery
SELECT name FROM sqlite_master WHERE type='trigger';

-- Sprawdź dane w sync_metadata
SELECT * FROM sync_metadata;
```

---

## 📝 KOLEJNOŚĆ WYKONANIA

1. ✅ **PostgreSQL** (API Server) - `sync_schema_migration.sql`
2. ✅ **SQLite** (Aplikacja) - `sync_schema_migration_sqlite.sql`
3. ▶️ Uruchom serwer API: `python -m uvicorn app.main:app --reload`
4. ▶️ Uruchom aplikację: `python main.py`
5. 🔄 Testuj synchronizację w module TeamWork

---

## 🎉 GOTOWE!

Po wykonaniu obu migracji:
- ✅ Baza PostgreSQL ma kolumny sync i tabele metadanych
- ✅ Baza SQLite ma kolumny sync i tabele metadanych
- ✅ Triggery automatycznie oznaczają zmiany
- ✅ SyncManager może działać (push/pull/conflict resolution)

**Następny krok**: Testowanie synchronizacji w Phase 7!
