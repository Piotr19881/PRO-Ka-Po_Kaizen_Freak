# Analiza zgodności schematów baz danych
**Data:** 2025-11-10  
**Status:** 🔴 Wykryto krytyczne rozbieżności w CallCryptor

---

## 🎯 Cel analizy
Weryfikacja zgodności między:
1. **SQLite (lokalna baza)** - `callcryptor_database.py`
2. **PostgreSQL (zdalna baza)** - `s07_callcryptor_schema.sql`
3. **SQLAlchemy ORM** - `recordings_orm.py`
4. **Pydantic Models** - `recordings_models.py` (RecordingSyncItem)

---

## ❌ CallCryptor - KRYTYCZNE ROZBIEŻNOŚCI

### 📊 Porównanie pól: recordings table

| Pole | SQLite (lokalne) | PostgreSQL (schema) | ORM Model | RecordingSyncItem | Status |
|------|------------------|---------------------|-----------|-------------------|--------|
| `duration` | ✅ INTEGER | ⚠️ INTEGER | ❌ `duration_seconds` | ✅ `duration_seconds` | **NIEZGODNOŚĆ** |
| `transcription_status` | ✅ TEXT | ✅ TEXT | ❌ BRAK | ❌ BRAK | **MISSING** |
| `transcription_text` | ✅ TEXT | ✅ TEXT | ⚠️ `ai_transcript` | ✅ `ai_transcript` | **RÓŻNE NAZWY** |
| `transcription_language` | ✅ TEXT | ✅ TEXT | ⚠️ `ai_language` | ✅ `ai_language` | **RÓŻNE NAZWY** |
| `transcription_confidence` | ✅ REAL | ✅ REAL | ❌ BRAK | ❌ BRAK | **MISSING** |
| `transcription_date` | ✅ TEXT | ✅ TIMESTAMP | ❌ BRAK | ❌ BRAK | **MISSING** |
| `transcription_error` | ✅ TEXT | ✅ TEXT | ❌ BRAK | ❌ BRAK | **MISSING** |
| `ai_summary_status` | ✅ TEXT | ✅ TEXT | ❌ BRAK | ❌ BRAK | **MISSING** |
| `ai_summary_text` | ✅ TEXT | ✅ TEXT | ✅ `ai_summary` | ✅ `ai_summary` | ✅ OK |
| `ai_summary_date` | ✅ TEXT | ✅ TIMESTAMP | ❌ BRAK | ❌ BRAK | **MISSING** |
| `ai_summary_error` | ✅ TEXT | ✅ TEXT | ❌ BRAK | ❌ BRAK | **MISSING** |
| `ai_summary_tasks` | ❌ BRAK | ✅ JSONB | ✅ JSON | ✅ List[str] | **DODANE (OK)** |
| `ai_key_points` | ✅ TEXT (JSON) | ✅ JSONB | ✅ JSON | ✅ List[str] | ✅ OK |
| `ai_action_items` | ✅ TEXT (JSON) | ✅ JSONB | ✅ JSON | ✅ List[str] | ✅ OK |
| `is_archived` | ✅ BOOLEAN | ✅ BOOLEAN | ❌ BRAK | ❌ BRAK | **MISSING** |
| `archived_at` | ✅ TEXT | ✅ TIMESTAMP | ❌ BRAK | ❌ BRAK | **MISSING** |
| `archive_reason` | ✅ TEXT | ✅ TEXT | ❌ BRAK | ❌ BRAK | **MISSING** |
| `is_favorite` | ✅ BOOLEAN | ✅ BOOLEAN | ❌ BRAK | ❌ BRAK | **MISSING** |
| `favorited_at` | ✅ TEXT | ✅ TIMESTAMP | ❌ BRAK | ❌ BRAK | **MISSING** |
| `file_path` | ✅ TEXT | ❌ BRAK | ❌ BRAK | ❌ BRAK | **LOKALNE ONLY** |
| `category` | ❌ BRAK | ❌ BRAK | ✅ String(100) | ✅ str | **DODANE (OK)** |
| `ai_sentiment` | ❌ BRAK | ❌ BRAK | ✅ String(20) | ✅ str | **DODANE (OK)** |
| `pomodoro_session_id` | ❌ BRAK | ❌ BRAK | ✅ String | ✅ str | **DODANE (OK)** |
| `is_synced` | ✅ BOOLEAN | ❌ BRAK | ❌ BRAK | ❌ BRAK | **LOKALNE ONLY** |
| `server_id` | ✅ TEXT | ❌ BRAK | ❌ BRAK | ❌ BRAK | **LOKALNE ONLY** |

### 📊 Porównanie pól: recording_sources table

| Pole | SQLite | PostgreSQL | ORM Model | Status |
|------|--------|------------|-----------|--------|
| `search_type` | ❌ BRAK | ✅ TEXT | ✅ String(20) | **DODANE** |
| `search_all_folders` | ❌ BRAK | ✅ BOOLEAN | ✅ Boolean | **DODANE** |
| `contact_ignore_words` | ❌ BRAK | ✅ TEXT | ✅ Text | **DODANE** |
| `deleted_at` | ❌ BRAK | ✅ TIMESTAMP | ✅ TIMESTAMP | **DODANE** |
| `is_synced` | ✅ BOOLEAN | ❌ BRAK | ❌ BRAK | **LOKALNE ONLY** |
| `server_id` | ✅ TEXT | ❌ BRAK | ❌ BRAK | **LOKALNE ONLY** |

### 📊 Porównanie pól: recording_tags table

| Pole | SQLite | PostgreSQL | ORM Model | Status |
|------|--------|------------|-----------|--------|
| `updated_at` | ❌ BRAK | ✅ TIMESTAMP | ✅ TIMESTAMP | **DODANE** |
| `deleted_at` | ❌ BRAK | ✅ TIMESTAMP | ✅ TIMESTAMP | **DODANE** |
| `version` | ❌ BRAK | ✅ INTEGER | ✅ Integer | **DODANE** |
| `synced_at` | ❌ BRAK | ❌ BRAK | ✅ TIMESTAMP | **DODANE** |

---

## 🔍 Wykryte problemy synchronizacji

### ❌ Problem 1: Brakujące pola w ORM/Pydantic
**Pola które są w SQLite i PostgreSQL, ale NIE w ORM:**
- `transcription_status` - status transkrypcji ('pending', 'processing', 'completed', 'failed')
- `transcription_confidence` - pewność transkrypcji (0.0 - 1.0)
- `transcription_date` - data wykonania transkrypcji
- `transcription_error` - błąd transkrypcji
- `ai_summary_status` - status podsumowania AI
- `ai_summary_date` - data wygenerowania podsumowania
- `ai_summary_error` - błąd generowania podsumowania
- `is_archived` - czy nagranie zarchiwizowane
- `archived_at` - kiedy zarchiwizowano
- `archive_reason` - powód archiwizacji
- `is_favorite` - czy nagranie ulubione
- `favorited_at` - kiedy dodano do ulubionych

**Konsekwencje:**
- ❌ Te pola NIE będą synchronizowane
- ❌ Dane zarchiwizowane/ulubione będą tracone podczas sync
- ❌ Status transkrypcji będzie resetowany
- ❌ Błędy AI będą tracone

### ❌ Problem 2: Różne nazwy pól
**Mapowanie niezgodne:**
- SQLite: `duration` ↔ ORM: `duration_seconds`
- SQLite: `transcription_text` ↔ ORM: `ai_transcript`
- SQLite: `transcription_language` ↔ ORM: `ai_language`

**Konsekwencje:**
- ⚠️ Kod synchronizacji musi robić mapowanie pól
- ⚠️ Ryzyko błędów przy update (duration vs duration_seconds)

### ❌ Problem 3: Typy danych
**TEXT (SQLite) vs TIMESTAMP (PostgreSQL):**
- `recording_date` - TEXT vs TIMESTAMP
- `last_scan_at` - TEXT vs TIMESTAMP  
- `created_at` - TEXT vs TIMESTAMP
- `updated_at` - TEXT vs TIMESTAMP

**Konsekwencje:**
- ⚠️ Wymagana konwersja datetime ↔ string
- ⚠️ Różne timezone handling

### ❌ Problem 4: JSON storage
**TEXT (SQLite) vs JSONB (PostgreSQL):**
- `tags` - TEXT vs JSONB
- `file_extensions` - TEXT vs JSONB
- `ai_key_points` - TEXT vs JSONB
- `ai_action_items` - TEXT vs JSONB

**Konsekwencje:**
- ✅ Sync manager już robi `json.loads()` - OK
- ⚠️ Ale ORM używa `Column(JSON)` co może dawać konflikty

---

## ✅ Inne moduły - szybka weryfikacja

### Habit Tracker
**Status:** ✅ Prawdopodobnie OK
- ORM: `HabitColumn`, `HabitRecord` w `habit_models.py`
- Pydantic: `HabitColumnCreate`, `HabitRecordCreate` w `habit_schemas.py`
- PostgreSQL: `s07_habits` schema
- **Znane problemy:** Brak - moduł działał przed CallCryptor

### Tasks
**Status:** ⚠️ DO SPRAWDZENIA
- Duży moduł z wieloma tabelami (tasks, tags, kanban_items)
- Może mieć podobne problemy z JSONB vs TEXT

### Notes
**Status:** ⚠️ DO SPRAWDZENIA  
- Schema: `s06_notes`
- Prostsza struktura ale może mieć problemy z timestamps

### Alarms/Pomodoro
**Status:** ⚠️ DO SPRAWDZENIA
- Schema: `s03_alarms`, `s05_pomodoro`
- Mniej pól ale może mieć problemy z version conflicts

---

## 🔧 Rekomendowane poprawki dla CallCryptor

### Priorytet 1: Dodać brakujące pola do ORM
**Plik:** `Render_upload/app/recordings_orm.py`

```python
class Recording(Base):
    # ... existing fields ...
    
    # Transkrypcja - DODAĆ:
    transcription_status = Column(String(20), default='pending')
    transcription_confidence = Column(Float, nullable=True)
    transcription_date = Column(TIMESTAMP, nullable=True)
    transcription_error = Column(Text, nullable=True)
    
    # AI Summary - DODAĆ:
    ai_summary_status = Column(String(20), default='pending')
    ai_summary_date = Column(TIMESTAMP, nullable=True)
    ai_summary_error = Column(Text, nullable=True)
    
    # Archiwizacja - DODAĆ:
    is_archived = Column(Boolean, default=False)
    archived_at = Column(TIMESTAMP, nullable=True)
    archive_reason = Column(Text, nullable=True)
    
    # Ulubione - DODAĆ:
    is_favorite = Column(Boolean, default=False)
    favorited_at = Column(TIMESTAMP, nullable=True)
```

### Priorytet 2: Zaktualizować RecordingSyncItem
**Plik:** `Render_upload/app/recordings_models.py`

```python
class RecordingSyncItem(BaseModel):
    # ... existing fields ...
    
    # Transkrypcja - DODAĆ:
    transcription_status: str = "pending"
    transcription_confidence: Optional[float] = None
    transcription_date: Optional[datetime] = None
    transcription_error: Optional[str] = None
    
    # AI Summary - DODAĆ:
    ai_summary_status: str = "pending"
    ai_summary_date: Optional[datetime] = None
    ai_summary_error: Optional[str] = None
    
    # Archiwizacja - DODAĆ:
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    archive_reason: Optional[str] = None
    
    # Ulubione - DODAĆ:
    is_favorite: bool = False
    favorited_at: Optional[datetime] = None
```

### Priorytet 3: Zaktualizować sync_manager mapowanie
**Plik:** `src/Modules/CallCryptor_module/recordings_sync_manager.py`

Dodać mapowanie:
- `duration` → `duration_seconds`
- `transcription_text` → `ai_transcript`
- `transcription_language` → `ai_language`

### Priorytet 4: Zaktualizować PostgreSQL schema
**Plik:** `Render_upload/database/s07_callcryptor_schema.sql`

Zmienić nazwy kolumn aby pasowały do ORM:
- `duration` → `duration_seconds`
- `transcription_text` → `ai_transcript`  
- `transcription_language` → `ai_language`

**LUB** zmienić ORM aby pasował do schema (zalecane).

---

## 📋 Plan działania

### Krok 1: Zatrzymać synchronizację
- ❌ NIE uruchamiać sync dopóki schema nie są zgodne
- ⚠️ Ryzyko utraty danych (archiwizacja, transkrypcje)

### Krok 2: Zdecydować o nazwach pól
**Opcja A:** Zmienić PostgreSQL schema (ZALECANE)
- Dodać brakujące kolumny
- Zmienić nazwy: `duration_seconds`, `ai_transcript`, `ai_language`
- Uruchomić migrację ALTER TABLE

**Opcja B:** Zmienić ORM i Pydantic
- Zmienić `duration_seconds` → `duration`
- Zmienić `ai_transcript` → `transcription_text`
- Dodać wszystkie brakujące pola

### Krok 3: Zaktualizować kod synchronizacji
- Dodać mapowanie wszystkich nowych pól w `bulk_sync()`
- Dodać parsowanie status fields
- Zaktualizować testy

### Krok 4: Przetestować na próbnych danych
- Utworzyć testowe nagranie z wszystkimi polami
- Zsynchronizować
- Sprawdzić czy wszystkie pola zapisały się poprawnie

---

## 🎯 Podsumowanie

**CallCryptor synchronizacja NIE DZIAŁA poprawnie:**
- ❌ 18 pól BRAKUJE w ORM (transkrypcja, archiwizacja, ulubione)
- ❌ 3 pola mają RÓŻNE NAZWY (duration, transcript, language)
- ⚠️ Dane będą TRACONE podczas synchronizacji

**Inne moduły:**
- ✅ Habits - prawdopodobnie OK
- ⚠️ Tasks, Notes, Alarms - wymagają weryfikacji

**Akcja wymagana:**
1. Zdecydować o strategii nazewnictwa (PostgreSQL → ORM czy ORM → PostgreSQL)
2. Dodać brakujące pola
3. Zaktualizować migrację bazy
4. Przetestować ponownie
