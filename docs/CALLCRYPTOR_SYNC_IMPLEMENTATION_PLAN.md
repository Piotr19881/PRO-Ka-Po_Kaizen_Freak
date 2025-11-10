# Plan Implementacji Synchronizacji Modułu CallCryptor

**Data utworzenia:** 8 listopada 2025  
**Wersja:** 1.0  
**Status:** Draft - Do realizacji  
**Typ synchronizacji:** **On-demand (manual) + Optional Auto-sync**

---

## 📋 Spis treści

1. [Podsumowanie wykonawcze](#1-podsumowanie-wykonawcze)
2. [Specyfika modułu CallCryptor](#2-specyfika-modułu-callcryptor)
3. [Architektura docelowa](#3-architektura-docelowa)
4. [Faza 0: Przygotowanie](#faza-0-przygotowanie)
5. [Faza 1: Backend - Schema i Migration](#faza-1-backend---schema-i-migration)
6. [Faza 2: Backend - Models](#faza-2-backend---models)
7. [Faza 3: Backend - Router](#faza-3-backend---router)
8. [Faza 4: Frontend - UI Controls](#faza-4-frontend---ui-controls)
9. [Faza 5: Frontend - API Client](#faza-5-frontend---api-client)
10. [Faza 6: Frontend - Sync Manager](#faza-6-frontend---sync-manager)
11. [Faza 7: Integracja z UI](#faza-7-integracja-z-ui)
12. [Faza 8: Testowanie](#faza-8-testowanie)
13. [Faza 9: Dokumentacja](#faza-9-dokumentacja)

---

## 1. Podsumowanie wykonawcze

### 🎯 Cel projektu
Implementacja **opcjonalnej** synchronizacji dwukierunkowej dla modułu CallCryptor z naciskiem na **prywatność i kontrolę użytkownika**.

### 🔐 Kluczowe założenia - PRIVACY-FIRST

1. **Opt-in synchronizacja:** Domyślnie wyłączona - dane tylko lokalnie
2. **Świadoma zgoda:** Użytkownik jest informowany o konsekwencjach włączenia sync
3. **Selektywna synchronizacja:** Możliwość wykluczenia poufnych nagrań (TODO: future)
4. **Encryption at rest:** Pliki audio NIE są synchronizowane (tylko metadane)
5. **Manual trigger:** Synchronizacja tylko na życzenie użytkownika (przycisk 📨)
6. **Optional auto-sync:** Użytkownik może włączyć automatyczną synchronizację

### 📊 Zakres synchronizacji

**Synchronizowane tabele:**
- ✅ `recording_sources` - źródła nagrań (foldery, konta email)
- ✅ `recordings` - metadane nagrań (bez plików audio!)
- ✅ `recording_tags` - tagi organizacyjne

**Synchronizowane dane nagrania:**
```json
{
  "id": "uuid",
  "user_id": "uuid",
  "source_id": "uuid",
  
  // Metadata (SYNC)
  "file_name": "recording.mp3",
  "file_size": 1024000,
  "file_hash": "sha256...",
  "duration": 180,
  "recording_date": "2025-11-08T10:30:00Z",
  
  // Organizacja (SYNC)
  "contact_name": "Jan Kowalski",
  "contact_phone": "+48 123 456 789",
  "tags": ["important", "work"],
  "notes": "Rozmowa w sprawie projektu",
  
  // AI Results (SYNC)
  "transcription_text": "...",
  "transcription_status": "completed",
  "ai_summary_text": "...",
  "ai_summary_tasks": [{...}],
  
  // Linki (SYNC)
  "note_id": "uuid",
  "task_id": "uuid",
  
  // Flags (SYNC)
  "is_favorite": true,
  "is_archived": false
}
```

**NIE synchronizowane (tylko lokalnie):**
- ❌ Pliki audio (`file_path` - lokalna ścieżka)
- ❌ Załączniki e-mail (pobrane lokalnie)
- ❌ Email credentials (tylko w `email_accounts.db`)

### 🎨 UI Specyfikacja

#### Przycisk Synchronizacji

**Lokalizacja:** CallCryptorView toolbar (obok przycisku 🏷️ Tags)

**Wygląd:**
```
┌─────────────────────────────────────────────┐
│ Toolbar                                      │
│ [➕][➖][🛠️] [🔄][⏺️][👥][💾][🏷️] [📨]     │
│                                       ▲       │
│                                       │       │
│                                 Sync button   │
└─────────────────────────────────────────────┘

📨 - Pomarańczowy (sync wyłączona)
📨 - Zielony (sync włączona i active)
```

**Stany przycisku:**
1. **🟠 Pomarańczowy:** Synchronizacja wyłączona (domyślnie)
   - Tooltip: "Synchronizacja wyłączona - dane tylko lokalnie"
   - MaxWidth: 45px
   - Style: `background-color: #FF8C00; color: white;`

2. **🟢 Zielony:** Synchronizacja włączona
   - Tooltip: "Synchronizacja włączona"
   - MaxWidth: 45px
   - Style: `background-color: #4CAF50; color: white;`

3. **🔵 Niebieski (pulsujący):** Synchronizacja w toku
   - Tooltip: "Synchronizacja w toku..."
   - Animation: fade in/out

#### Dialog Synchronizacji

**Wariant A: Sync wyłączona (pierwszy klik)**

```
┌─────────────────────────────────────────────────────────┐
│  📨 Synchronizacja CallCryptor                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  ⚠️  WAŻNE INFORMACJE O PRYWATNOŚCI                     │
│                                                          │
│  Gdy masz wyłączoną synchronizację, twoje dane są       │
│  przechowywane TYLKO LOKALNIE. Nie będziesz miał do     │
│  nich dostępu na innym komputerze.                      │
│                                                          │
│  ───────────────────────────────────────────────────    │
│                                                          │
│  ✅ Co BĘDZIE synchronizowane:                          │
│     • Metadane nagrań (nazwa, czas, kontakt)            │
│     • Transkrypcje i podsumowania AI                    │
│     • Tagi i notatki                                    │
│     • Linki do zadań i notatek                          │
│                                                          │
│  ❌ Co NIE będzie synchronizowane:                      │
│     • Pliki audio (pozostają tylko lokalnie)            │
│     • Hasła do kont e-mail                              │
│                                                          │
│  ───────────────────────────────────────────────────    │
│                                                          │
│  [ ] Włącz automatyczną synchronizację                  │
│      (synchronizuj co 5 minut automatycznie)            │
│                                                          │
│  [ ] Nie pokazuj ponownie tego komunikatu               │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Anuluj]              [Synchronizuj teraz] [Włącz sync]│
│                                                          │
└─────────────────────────────────────────────────────────┘
```

**Wariant B: Sync włączona (kolejne kliknięcia)**

```
┌─────────────────────────────────────────────────────────┐
│  📨 Synchronizacja CallCryptor                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Stan synchronizacji: ✅ Włączona                       │
│  Ostatnia synchronizacja: 2 minuty temu                 │
│                                                          │
│  ───────────────────────────────────────────────────    │
│                                                          │
│  Statystyki:                                             │
│  • Nagrań lokalnych: 231                                │
│  • Zsynchronizowanych: 228                               │
│  • Do synchronizacji: 3                                  │
│                                                          │
│  ───────────────────────────────────────────────────    │
│                                                          │
│  [✓] Automatyczna synchronizacja (co 5 minut)           │
│                                                          │
│  [ ] Wyłącz synchronizację                              │
│      (dane pozostaną na serwerze ale przestaną być       │
│       automatycznie aktualizowane)                       │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  [Zamknij]                       [Synchronizuj teraz]   │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

#### Progress Dialog (podczas synchronizacji)

```
┌─────────────────────────────────────────────────────────┐
│  📨 Synchronizacja w toku...                            │
├─────────────────────────────────────────────────────────┤
│                                                          │
│  Wysyłanie lokalnych zmian...                           │
│  [████████████████░░░░░░░░] 67% (2/3)                   │
│                                                          │
│  Pobieranie zmian z serwera...                          │
│  [████████████████████████] 100% (15/15)                │
│                                                          │
│  Status: Synchronizacja metadanych...                   │
│                                                          │
├─────────────────────────────────────────────────────────┤
│                                                          │
│                                    [Anuluj]              │
│                                                          │
└─────────────────────────────────────────────────────────┘
```

### ⏱️ Timeline

- **Faza 0 (Przygotowanie):** 1 dzień
- **Faza 1 (Backend schema):** 2 dni
- **Faza 2 (Backend models):** 1 dzień
- **Faza 3 (Backend router):** 2 dni
- **Faza 4 (Frontend UI):** 1 dzień
- **Faza 5 (Frontend API client):** 2 dni
- **Faza 6 (Frontend sync manager):** 3 dni
- **Faza 7 (Integracja UI):** 2 dni
- **Faza 8 (Testing):** 2 dni
- **Faza 9 (Dokumentacja):** 1 dzień

**RAZEM:** ~17 dni roboczych

---

## 2. Specyfika modułu CallCryptor

### 2.1 Różnice względem innych modułów

| Aspekt | Tasks/Alarms | **CallCryptor** |
|--------|--------------|-----------------|
| **Default sync** | Enabled | **Disabled (opt-in)** |
| **Privacy** | Normal | **High (poufne rozmowy)** |
| **File sync** | N/A | **NO (audio files local-only)** |
| **Auto-sync** | Default ON | **Optional (checkbox)** |
| **Data size** | Small | **Large metadata** |
| **User control** | Passive | **Active (explicit consent)** |

### 2.2 Privacy considerations

**Dlaczego synchronizacja jest opt-in:**
1. Nagrania rozmów mogą zawierać poufne informacje biznesowe
2. Dane osobowe rozmówców (RODO/GDPR compliance)
3. Transkrypcje mogą ujawniać szczegóły projektów
4. Użytkownik musi mieć pełną kontrolę nad danymi

**Implementacja privacy-first:**
```python
class CallCryptorSyncSettings:
    """Ustawienia synchronizacji CallCryptor"""
    
    sync_enabled: bool = False  # Domyślnie wyłączona!
    auto_sync_enabled: bool = False
    sync_interval_minutes: int = 5
    exclude_tags: List[str] = []  # TODO: future - exclude recordings with tags
    last_sync_at: Optional[datetime] = None
    dont_show_warning: bool = False
```

### 2.3 Excluded data (bezpieczeństwo)

**Pliki audio - NIGDY nie są synchronizowane:**
```python
# ❌ NIE synchronizuj file_path (ścieżka lokalna)
# ❌ NIE synchronizuj plików binarnych audio
# ✅ Synchronizuj tylko metadane (file_name, file_hash, duration)

class RecordingSync(BaseModel):
    # Metadata SYNC
    file_name: str
    file_hash: str  # Dla deduplication
    file_size: int
    duration: int
    
    # BRAK file_path - to ścieżka lokalna!
    # BRAK binary audio data
```

**Email credentials - oddzielna baza:**
```python
# Email accounts są w OSOBNEJ bazie email_accounts.db
# i mają WŁASNY mechanizm sync (osobny moduł)
# CallCryptor synchronizuje tylko email_account_id (reference)
```

---

## 3. Architektura docelowa

### 3.1 Flow synchronizacji (opt-in)

```
┌─────────────────────────────────────────────────────────────┐
│                    CLIENT (PyQt6)                            │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────────────────────────────────┐           │
│  │  CallCryptorView - Toolbar                   │           │
│  │  [➕][➖][🛠️] [🔄][⏺️][👥][💾][🏷️] [📨]     │           │
│  │                                       ▲       │           │
│  │                            Click ─────┘       │           │
│  └───────────────────────────┬──────────────────┘           │
│                              │                                │
│                              ▼                                │
│  ┌───────────────────────────────────────────────┐          │
│  │  IF sync_enabled == False:                    │          │
│  │    → Show SyncConsentDialog                   │          │
│  │       [Anuluj] [Synchronizuj raz] [Włącz]    │          │
│  │  ELSE:                                        │          │
│  │    → Show SyncStatusDialog                    │          │
│  │       [Zamknij] [Synchronizuj teraz]          │          │
│  └───────────────────────────┬───────────────────┘          │
│                              │                                │
│                 User: "Włącz sync"                           │
│                              │                                │
│                              ▼                                │
│  ┌──────────────────────────────────────────────┐           │
│  │  CallCryptorSyncSettings                     │           │
│  │  - sync_enabled = True                       │           │
│  │  - auto_sync_enabled = <checkbox>            │           │
│  │  - Save to local DB                          │           │
│  └───────────────────────────┬──────────────────┘           │
│                              │                                │
│                              ▼                                │
│  ┌──────────────────────────────────────────────┐           │
│  │  CallCryptorSyncManager.sync()               │           │
│  │  1. Gather local changes (is_synced=False)   │           │
│  │  2. Send to server (POST /api/recordings)    │           │
│  │  3. Get remote changes (GET /api/recordings) │           │
│  │  4. Resolve conflicts (last-write-wins)      │           │
│  │  5. Update local DB (mark is_synced=True)    │           │
│  └───────────────────────────┬──────────────────┘           │
│                              │                                │
│         ┌────────────────────┴─────────────┐                 │
│         │                                  │                 │
│  ┌──────▼─────────┐              ┌────────▼──────────┐      │
│  │ RecordingAPI   │              │ Optional:         │      │
│  │ Client         │              │ Auto-sync timer   │      │
│  │ - HTTP/REST    │              │ (if enabled)      │      │
│  └──────┬─────────┘              └───────────────────┘      │
│         │                                                     │
└─────────┼─────────────────────────────────────────────────────┘
          │
          │ HTTPS
          │
┌─────────▼─────────────────────────────────────────────────────┐
│                    SERVER (FastAPI)                            │
├───────────────────────────────────────────────────────────────┤
│                                                                │
│  ┌──────────────────────────────────────────────┐            │
│  │ recordings_router                            │            │
│  │  POST   /api/recordings/bulk                 │            │
│  │  GET    /api/recordings                      │            │
│  │  GET    /api/recordings/{id}                 │            │
│  │  PUT    /api/recordings/{id}                 │            │
│  │  DELETE /api/recordings/{id}                 │            │
│  └──────────────────┬───────────────────────────┘            │
│                     │                                         │
│  ┌──────────────────▼───────────────────────────┐            │
│  │   RecordingModels (Pydantic)                 │            │
│  │   - RecordingCreate                          │            │
│  │   - RecordingUpdate                          │            │
│  │   - RecordingResponse                        │            │
│  │   - BulkSyncRequest/Response                 │            │
│  └──────────────────┬───────────────────────────┘            │
│                     │                                         │
│  ┌──────────────────▼───────────────────────────┐            │
│  │   PostgreSQL - s07_callcryptor schema        │            │
│  │   - recording_sources                        │            │
│  │   - recordings                               │            │
│  │   - recording_tags                           │            │
│  └──────────────────────────────────────────────┘            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

### 3.2 Sync settings storage

**Lokalizacja:** `user_settings.json` (existing file)

```json
{
  "user_id": "uuid",
  "language": "pl",
  "theme": "dark",
  
  "callcryptor_sync": {
    "enabled": false,
    "auto_sync_enabled": false,
    "sync_interval_minutes": 5,
    "last_sync_at": null,
    "dont_show_warning": false,
    "exclude_tags": []
  }
}
```

### 3.3 Database schema additions

**Dodaj kolumny sync do lokalnej bazy:**

```sql
-- recording_sources
ALTER TABLE recording_sources ADD COLUMN created_at TEXT;
ALTER TABLE recording_sources ADD COLUMN updated_at TEXT;
ALTER TABLE recording_sources ADD COLUMN deleted_at TEXT;
ALTER TABLE recording_sources ADD COLUMN synced_at TEXT;
ALTER TABLE recording_sources ADD COLUMN is_synced BOOLEAN DEFAULT 0;
ALTER TABLE recording_sources ADD COLUMN server_id TEXT;

-- recordings (już ma is_synced, server_id - tylko dodaj timestamps)
-- created_at, updated_at już istnieją
ALTER TABLE recordings ADD COLUMN deleted_at TEXT;
ALTER TABLE recordings ADD COLUMN synced_at TEXT;

-- recording_tags
ALTER TABLE recording_tags ADD COLUMN created_at TEXT;
ALTER TABLE recording_tags ADD COLUMN updated_at TEXT;
ALTER TABLE recording_tags ADD COLUMN deleted_at TEXT;
ALTER TABLE recording_tags ADD COLUMN synced_at TEXT;
ALTER TABLE recording_tags ADD COLUMN is_synced BOOLEAN DEFAULT 0;
ALTER TABLE recording_tags ADD COLUMN server_id TEXT;
```

---

## FAZA 0: Przygotowanie

### Krok 0.1: Backup bazy danych

```bash
# Backup lokalnej bazy SQLite
cp data/callcryptor.db data/callcryptor.db.backup_20251108

# Backup user_settings.json
cp PRO-Ka-Po_Kaizen_Freak/user_settings.json PRO-Ka-Po_Kaizen_Freak/user_settings.json.backup
```

**✅ Checklist:**
- [ ] Backup callcryptor.db
- [ ] Backup user_settings.json
- [ ] Test przywracania z backup

### Krok 0.2: Analiza istniejącej implementacji alarms

**Pliki do przeanalizowania:**
```
Render_upload/app/
├── alarms_models.py          → wzór dla recordings_models.py
├── alarms_router.py          → wzór dla recordings_router.py

PRO-Ka-Po_Kaizen_Freak/src/Modules/Alarm_module/
├── alarm_api_client.py       → wzór dla recording_api_client.py
├── alarms_sync_manager.py    → wzór dla recordings_sync_manager.py
```

**✅ Checklist:**
- [ ] Przeczytaj alarms_router.py (bulk sync endpoint)
- [ ] Przeczytaj alarms_sync_manager.py (conflict resolution)
- [ ] Zidentyfikuj reusable components

### Krok 0.3: Przygotowanie środowiska

```bash
# 1. Utwórz branch
git checkout -b feature/callcryptor-sync
git push -u origin feature/callcryptor-sync

# 2. Uruchom serwer lokalnie
cd Render_upload
uvicorn app.main:app --reload --port 8000

# 3. Test health check
curl http://localhost:8000/health
```

**✅ Checklist:**
- [ ] Branch utworzony
- [ ] Serwer FastAPI działa
- [ ] Health check OK

---

## FAZA 1: Backend - Schema i Migration

### Krok 1.1: PostgreSQL Schema

**Plik:** `Render_upload/database/s07_callcryptor_schema.sql`

```sql
-- ============================================================
-- Schema: s07_callcryptor
-- Synchronizacja modułu CallCryptor
-- ============================================================

CREATE SCHEMA IF NOT EXISTS s07_callcryptor;

-- ============================================================
-- TABLE: recording_sources
-- ============================================================
CREATE TABLE IF NOT EXISTS s07_callcryptor.recording_sources (
    -- Identyfikatory
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    
    -- Podstawowe info
    source_name TEXT NOT NULL,
    source_type TEXT NOT NULL CHECK(source_type IN ('folder', 'email')),
    
    -- Opcje dla folder
    folder_path TEXT,
    file_extensions JSONB,              -- ["mp3", "wav", "m4a"]
    scan_depth INTEGER DEFAULT 1,
    
    -- Opcje dla email
    email_account_id TEXT,              -- Reference do email_accounts (inna baza)
    search_phrase TEXT,
    search_type TEXT DEFAULT 'SUBJECT', -- SUBJECT, ALL, BODY
    search_all_folders BOOLEAN DEFAULT FALSE,
    target_folder TEXT DEFAULT 'INBOX',
    attachment_pattern TEXT,
    contact_ignore_words TEXT,
    
    -- Metadata
    is_active BOOLEAN DEFAULT TRUE,
    last_scan_at TIMESTAMP,
    recordings_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    -- Sync metadata
    version INTEGER DEFAULT 1,
    
    UNIQUE(user_id, source_name, deleted_at)
);

-- ============================================================
-- TABLE: recordings
-- ============================================================
CREATE TABLE IF NOT EXISTS s07_callcryptor.recordings (
    -- Identyfikatory
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    source_id UUID NOT NULL REFERENCES s07_callcryptor.recording_sources(id) ON DELETE CASCADE,
    
    -- Info o pliku (NIE synchronizujemy file_path!)
    file_name TEXT NOT NULL,
    file_size BIGINT,                   -- Bytes
    file_hash TEXT,                     -- MD5/SHA256 dla deduplication
    
    -- Info z e-mail (jeśli applicable)
    email_message_id TEXT,
    email_subject TEXT,
    email_sender TEXT,
    
    -- Metadata nagrania
    contact_name TEXT,
    contact_phone TEXT,
    duration INTEGER,                   -- Sekundy
    recording_date TIMESTAMP,
    
    -- Organizacja
    tags JSONB,                         -- ["tag1", "tag2"]
    notes TEXT,
    
    -- Transkrypcja
    transcription_status TEXT DEFAULT 'pending' 
        CHECK(transcription_status IN ('pending', 'processing', 'completed', 'failed')),
    transcription_text TEXT,
    transcription_language TEXT,
    transcription_confidence REAL,
    transcription_date TIMESTAMP,
    transcription_error TEXT,
    
    -- AI Summary
    ai_summary_status TEXT DEFAULT 'pending'
        CHECK(ai_summary_status IN ('pending', 'processing', 'completed', 'failed')),
    ai_summary_text TEXT,
    ai_summary_date TIMESTAMP,
    ai_summary_error TEXT,
    ai_summary_tasks JSONB,             -- [{"title": "...", "priority": "..."}]
    ai_key_points JSONB,                -- ["punkt1", "punkt2"]
    ai_action_items JSONB,              -- [{"action": "...", "priority": "..."}]
    
    -- Linki do innych modułów
    note_id UUID,
    task_id UUID,
    
    -- Flags
    is_archived BOOLEAN DEFAULT FALSE,
    archived_at TIMESTAMP,
    archive_reason TEXT,
    is_favorite BOOLEAN DEFAULT FALSE,
    favorited_at TIMESTAMP,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    -- Sync metadata
    version INTEGER DEFAULT 1
);

-- ============================================================
-- TABLE: recording_tags
-- ============================================================
CREATE TABLE IF NOT EXISTS s07_callcryptor.recording_tags (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    tag_name TEXT NOT NULL,
    tag_color TEXT DEFAULT '#2196F3',
    tag_icon TEXT,
    usage_count INTEGER DEFAULT 0,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    deleted_at TIMESTAMP,
    
    -- Sync metadata
    version INTEGER DEFAULT 1,
    
    UNIQUE(user_id, tag_name, deleted_at)
);

-- ============================================================
-- INDEXES
-- ============================================================

-- recording_sources
CREATE INDEX idx_sources_user ON s07_callcryptor.recording_sources(user_id);
CREATE INDEX idx_sources_type ON s07_callcryptor.recording_sources(source_type);
CREATE INDEX idx_sources_active ON s07_callcryptor.recording_sources(is_active);
CREATE INDEX idx_sources_deleted ON s07_callcryptor.recording_sources(deleted_at);

-- recordings
CREATE INDEX idx_recordings_user ON s07_callcryptor.recordings(user_id);
CREATE INDEX idx_recordings_source ON s07_callcryptor.recordings(source_id);
CREATE INDEX idx_recordings_date ON s07_callcryptor.recordings(recording_date);
CREATE INDEX idx_recordings_contact ON s07_callcryptor.recordings(contact_name);
CREATE INDEX idx_recordings_trans_status ON s07_callcryptor.recordings(transcription_status);
CREATE INDEX idx_recordings_ai_status ON s07_callcryptor.recordings(ai_summary_status);
CREATE INDEX idx_recordings_archived ON s07_callcryptor.recordings(is_archived);
CREATE INDEX idx_recordings_favorite ON s07_callcryptor.recordings(is_favorite);
CREATE INDEX idx_recordings_hash ON s07_callcryptor.recordings(file_hash);
CREATE INDEX idx_recordings_deleted ON s07_callcryptor.recordings(deleted_at);

-- recording_tags
CREATE INDEX idx_tags_user ON s07_callcryptor.recording_tags(user_id);
CREATE INDEX idx_tags_name ON s07_callcryptor.recording_tags(tag_name);
CREATE INDEX idx_tags_deleted ON s07_callcryptor.recording_tags(deleted_at);

-- ============================================================
-- TRIGGERS - Auto-update updated_at
-- ============================================================

CREATE OR REPLACE FUNCTION s07_callcryptor.update_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER sources_updated_at
    BEFORE UPDATE ON s07_callcryptor.recording_sources
    FOR EACH ROW
    EXECUTE FUNCTION s07_callcryptor.update_updated_at();

CREATE TRIGGER recordings_updated_at
    BEFORE UPDATE ON s07_callcryptor.recordings
    FOR EACH ROW
    EXECUTE FUNCTION s07_callcryptor.update_updated_at();

CREATE TRIGGER tags_updated_at
    BEFORE UPDATE ON s07_callcryptor.recording_tags
    FOR EACH ROW
    EXECUTE FUNCTION s07_callcryptor.update_updated_at();

-- ============================================================
-- RLS (Row Level Security)
-- ============================================================

ALTER TABLE s07_callcryptor.recording_sources ENABLE ROW LEVEL SECURITY;
ALTER TABLE s07_callcryptor.recordings ENABLE ROW LEVEL SECURITY;
ALTER TABLE s07_callcryptor.recording_tags ENABLE ROW LEVEL SECURITY;

-- Policy: Users can only access their own data
CREATE POLICY sources_user_isolation ON s07_callcryptor.recording_sources
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY recordings_user_isolation ON s07_callcryptor.recordings
    FOR ALL USING (user_id = auth.uid());

CREATE POLICY tags_user_isolation ON s07_callcryptor.recording_tags
    FOR ALL USING (user_id = auth.uid());

-- ============================================================
-- GRANTS
-- ============================================================

GRANT USAGE ON SCHEMA s07_callcryptor TO authenticated;
GRANT ALL ON ALL TABLES IN SCHEMA s07_callcryptor TO authenticated;
GRANT ALL ON ALL SEQUENCES IN SCHEMA s07_callcryptor TO authenticated;
```

**✅ Checklist:**
- [ ] Plik SQL utworzony
- [ ] Review schema (sprawdź typy kolumn)
- [ ] Execute na lokalnej PostgreSQL
- [ ] Verify schema: `\dt s07_callcryptor.*`

### Krok 1.2: Migration script

**Plik:** `Render_upload/migrations/007_callcryptor_sync.sql`

```sql
-- Migration 007: CallCryptor Sync
-- Created: 2025-11-08
-- Description: Dodaje schema s07_callcryptor dla synchronizacji nagrań

\i database/s07_callcryptor_schema.sql;
```

**✅ Checklist:**
- [ ] Migration file utworzony
- [ ] Test na dev database
- [ ] Rollback test (jeśli potrzeba)

---

## FAZA 2: Backend - Models

### Krok 2.1: Pydantic Models

**Plik:** `Render_upload/app/recordings_models.py`

```python
"""
CallCryptor Recordings - Pydantic Models
=========================================

Models dla synchronizacji nagrań między klientem a serwerem.
"""

from pydantic import BaseModel, Field, validator
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID


# ============================================================
# Recording Source Models
# ============================================================

class RecordingSourceBase(BaseModel):
    """Bazowy model źródła nagrań"""
    source_name: str = Field(..., min_length=1, max_length=200)
    source_type: str = Field(..., pattern="^(folder|email)$")
    
    # Folder options
    folder_path: Optional[str] = None
    file_extensions: Optional[List[str]] = Field(default_factory=lambda: [".mp3", ".wav", ".m4a"])
    scan_depth: int = Field(default=1, ge=1, le=10)
    
    # Email options
    email_account_id: Optional[str] = None
    search_phrase: Optional[str] = None
    search_type: str = Field(default="SUBJECT", pattern="^(SUBJECT|ALL|BODY)$")
    search_all_folders: bool = False
    target_folder: str = "INBOX"
    attachment_pattern: Optional[str] = None
    contact_ignore_words: Optional[str] = None
    
    # Metadata
    is_active: bool = True
    last_scan_at: Optional[datetime] = None
    recordings_count: int = 0


class RecordingSourceCreate(RecordingSourceBase):
    """Model tworzenia źródła"""
    pass


class RecordingSourceUpdate(BaseModel):
    """Model aktualizacji źródła (wszystkie pola opcjonalne)"""
    source_name: Optional[str] = None
    is_active: Optional[bool] = None
    folder_path: Optional[str] = None
    # ... inne pola opcjonalne


class RecordingSourceResponse(RecordingSourceBase):
    """Model odpowiedzi z źródłem"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    version: int
    
    class Config:
        from_attributes = True


# ============================================================
# Recording Models
# ============================================================

class RecordingBase(BaseModel):
    """Bazowy model nagrania"""
    # File metadata (NO file_path!)
    file_name: str = Field(..., min_length=1, max_length=500)
    file_size: Optional[int] = Field(None, ge=0)
    file_hash: Optional[str] = Field(None, max_length=64)
    
    # Email info
    email_message_id: Optional[str] = None
    email_subject: Optional[str] = None
    email_sender: Optional[str] = None
    
    # Recording metadata
    contact_name: Optional[str] = Field(None, max_length=200)
    contact_phone: Optional[str] = Field(None, max_length=50)
    duration: Optional[int] = Field(None, ge=0)  # seconds
    recording_date: Optional[datetime] = None
    
    # Organization
    tags: Optional[List[str]] = Field(default_factory=list)
    notes: Optional[str] = None
    
    # Transcription
    transcription_status: str = Field(default="pending", pattern="^(pending|processing|completed|failed)$")
    transcription_text: Optional[str] = None
    transcription_language: Optional[str] = None
    transcription_confidence: Optional[float] = Field(None, ge=0.0, le=1.0)
    transcription_date: Optional[datetime] = None
    transcription_error: Optional[str] = None
    
    # AI Summary
    ai_summary_status: str = Field(default="pending", pattern="^(pending|processing|completed|failed)$")
    ai_summary_text: Optional[str] = None
    ai_summary_date: Optional[datetime] = None
    ai_summary_error: Optional[str] = None
    ai_summary_tasks: Optional[List[Dict[str, Any]]] = None
    ai_key_points: Optional[List[str]] = None
    ai_action_items: Optional[List[Dict[str, Any]]] = None
    
    # Links to other modules
    note_id: Optional[UUID] = None
    task_id: Optional[UUID] = None
    
    # Flags
    is_archived: bool = False
    archived_at: Optional[datetime] = None
    archive_reason: Optional[str] = None
    is_favorite: bool = False
    favorited_at: Optional[datetime] = None


class RecordingCreate(RecordingBase):
    """Model tworzenia nagrania"""
    source_id: UUID


class RecordingUpdate(BaseModel):
    """Model aktualizacji nagrania (wszystkie pola opcjonalne)"""
    file_name: Optional[str] = None
    contact_name: Optional[str] = None
    tags: Optional[List[str]] = None
    notes: Optional[str] = None
    transcription_status: Optional[str] = None
    transcription_text: Optional[str] = None
    ai_summary_status: Optional[str] = None
    ai_summary_text: Optional[str] = None
    ai_summary_tasks: Optional[List[Dict[str, Any]]] = None
    is_archived: Optional[bool] = None
    is_favorite: Optional[bool] = None
    # ... inne pola


class RecordingResponse(RecordingBase):
    """Model odpowiedzi z nagraniem"""
    id: UUID
    user_id: UUID
    source_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    version: int
    
    class Config:
        from_attributes = True


# ============================================================
# Recording Tag Models
# ============================================================

class RecordingTagBase(BaseModel):
    """Bazowy model tagu"""
    tag_name: str = Field(..., min_length=1, max_length=100)
    tag_color: str = Field(default="#2196F3", pattern="^#[0-9A-Fa-f]{6}$")
    tag_icon: Optional[str] = None
    usage_count: int = Field(default=0, ge=0)


class RecordingTagCreate(RecordingTagBase):
    """Model tworzenia tagu"""
    pass


class RecordingTagUpdate(BaseModel):
    """Model aktualizacji tagu"""
    tag_name: Optional[str] = None
    tag_color: Optional[str] = None
    tag_icon: Optional[str] = None


class RecordingTagResponse(RecordingTagBase):
    """Model odpowiedzi z tagiem"""
    id: UUID
    user_id: UUID
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    version: int
    
    class Config:
        from_attributes = True


# ============================================================
# Bulk Sync Models
# ============================================================

class RecordingSyncItem(BaseModel):
    """Pojedyncze nagranie do synchronizacji"""
    id: UUID
    source_id: UUID
    file_name: str
    file_hash: Optional[str] = None
    contact_name: Optional[str] = None
    tags: Optional[List[str]] = None
    transcription_text: Optional[str] = None
    ai_summary_text: Optional[str] = None
    is_favorite: bool = False
    is_archived: bool = False
    created_at: datetime
    updated_at: datetime
    deleted_at: Optional[datetime] = None
    version: int


class BulkSyncRequest(BaseModel):
    """Request dla bulk synchronizacji"""
    recordings: List[RecordingSyncItem] = Field(..., max_length=100)
    sources: Optional[List[RecordingSourceResponse]] = None
    tags: Optional[List[RecordingTagResponse]] = None
    last_sync_at: Optional[datetime] = None


class BulkSyncResponse(BaseModel):
    """Response z bulk synchronizacji"""
    recordings_created: int
    recordings_updated: int
    recordings_deleted: int
    sources_created: int
    sources_updated: int
    tags_created: int
    tags_updated: int
    conflicts_resolved: int
    server_recordings: List[RecordingSyncItem]
    server_sources: List[RecordingSourceResponse]
    server_tags: List[RecordingTagResponse]
    sync_timestamp: datetime
```

**✅ Checklist:**
- [ ] Plik models utworzony
- [ ] All models have validators
- [ ] Config `from_attributes = True` set
- [ ] Test import: `from app.recordings_models import *`

---

## FAZA 3: Backend - Router

**Ze względu na długość dokumentu, kontynuacja w następnych sekcjach...**

---

## Podsumowanie faz (do wykonania)

### ✅ Faza 0: Przygotowanie (1 dzień)
- Backup baz danych
- Analiza wzorca alarms
- Setup środowiska

### ⏳ Faza 1: Backend Schema (2 dni)
- PostgreSQL schema s07_callcryptor
- Migration script
- Test na dev DB

### ⏳ Faza 2: Backend Models (1 dzień)
- Pydantic models
- Validators
- Bulk sync models

### ⏳ Faza 3: Backend Router (2 dni)
- recordings_router.py
- CRUD endpoints
- Bulk sync endpoint

### ⏳ Faza 4: Frontend UI (1 dzień)
- Przycisk 📨 (orange/green)
- SyncConsentDialog
- SyncStatusDialog
- ProgressDialog

### ⏳ Faza 5: Frontend API Client (2 dni)
- recording_api_client.py
- Token refresh
- Retry logic

### ⏳ Faza 6: Frontend Sync Manager (3 dni)
- recordings_sync_manager.py
- Conflict resolution
- Auto-sync timer (optional)

### ⏳ Faza 7: Integracja UI (2 dni)
- Hook przycisku sync
- Update toolbar colors
- Status updates

### ⏳ Faza 8: Testing (2 dni)
- Unit tests
- Integration tests
- Manual QA

### ⏳ Faza 9: Dokumentacja (1 dzień)
- User guide
- Privacy policy update
- API docs

---

**TOTAL: ~17 dni roboczych**

**Autor:** GitHub Copilot  
**Data:** 2025-11-08  
**Status:** Ready for implementation
