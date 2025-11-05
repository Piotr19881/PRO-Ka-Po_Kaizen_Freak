# Plan Implementacji Synchronizacji Modułu Notatek

**Data:** 2025-11-03  
**Cel:** Synchronizacja notatek z bazą PostgreSQL na Render przez API  
**Wzorzec:** Local-First Architecture (jak w module Alarm)

---

## 📋 ANALIZA ISTNIEJĄCYCH MODUŁÓW

### ✅ Moduł Alarm (Wzorcowy)

**Struktura plików:**
```
src/Modules/Alarm_module/
├── alarm_models.py              # Modele danych (Alarm, Timer)
├── alarm_local_database.py      # SQLite local-first storage
├── alarm_api_client.py          # HTTP client do API
├── alarm_websocket_client.py    # WebSocket real-time sync
└── alarms_sync_manager.py       # Background synchronizacja

Render_upload/app/
├── alarms_models.py             # SQLAlchemy models (PostgreSQL)
├── alarms_router.py             # FastAPI endpoints
└── websocket_manager.py         # WebSocket server
```

**Schemat bazy PostgreSQL:**
```sql
s04_alarms_timers
└── alarms_timers (unified table)
    ├── id (TEXT, PK)
    ├── user_id (TEXT, FK)
    ├── type (TEXT: 'alarm'|'timer')
    ├── version (INT) -- conflict resolution
    ├── created_at, updated_at, deleted_at (TIMESTAMP)
    ├── synced_at (TIMESTAMP)
    └── ... (specific fields)
```

**Kluczowe cechy:**
- ✅ Unified table approach (jedna tabela dla różnych typów)
- ✅ Soft delete (deleted_at)
- ✅ Version-based conflict resolution
- ✅ Sync queue dla offline operations
- ✅ Auto-reconnect WebSocket
- ✅ Exponential backoff retry logic

---

## 📊 ANALIZA OBECNEGO MODUŁU NOTATEK

### Obecna struktura SQLite (lokalna):

```sql
notes
├── id (TEXT, PK)
├── user_id (TEXT)
├── parent_id (TEXT, FK) -- hierarchia!
├── title (TEXT)
├── content (TEXT) -- HTML
├── color (TEXT)
├── sort_order (INTEGER)
├── is_favorite (BOOLEAN)
├── created_at (TEXT)
├── updated_at (TEXT)
└── deleted_at (TEXT)

note_links
├── id (TEXT, PK)
├── source_note_id (TEXT, FK)
├── target_note_id (TEXT, FK)
├── link_text (TEXT)
├── start_position (INTEGER)
├── end_position (INTEGER)
└── created_at (TEXT)
```

**Różnice vs Alarm:**
- ❌ Brak pola `version` (conflict resolution)
- ❌ Brak pola `synced_at`
- ❌ Brak sync_queue
- ✅ Ma parent_id (hierarchia zagnieżdżona)
- ✅ Ma note_links (dodatkowa relacja)

---

## 🎯 PLAN IMPLEMENTACJI

### FAZA 1: Schemat PostgreSQL (s06_notes)

**Plik:** `Render_upload/database/s06_notes_schema.sql`

```sql
-- Schema: s06_notes
CREATE SCHEMA IF NOT EXISTS s06_notes;

-- Table: notes (główna tabela notatek)
CREATE TABLE s06_notes.notes (
    -- Primary key
    id TEXT PRIMARY KEY,
    
    -- Foreign key do users
    user_id TEXT NOT NULL REFERENCES s01_user_accounts.users(id) ON DELETE CASCADE,
    
    -- Hierarchia (parent-child)
    parent_id TEXT REFERENCES s06_notes.notes(id) ON DELETE CASCADE,
    
    -- Dane notatki
    title TEXT NOT NULL,
    content TEXT, -- HTML z formatowaniem
    color TEXT DEFAULT '#1976D2',
    sort_order INTEGER DEFAULT 0,
    is_favorite BOOLEAN DEFAULT FALSE,
    
    -- Timestamps & sync metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP, -- Soft delete
    synced_at TIMESTAMP, -- Ostatnia synchronizacja
    version INTEGER DEFAULT 1 NOT NULL -- Conflict resolution
);

-- Table: note_links (hiperłącza między notatkami)
CREATE TABLE s06_notes.note_links (
    -- Primary key
    id TEXT PRIMARY KEY,
    
    -- Relations
    source_note_id TEXT NOT NULL REFERENCES s06_notes.notes(id) ON DELETE CASCADE,
    target_note_id TEXT NOT NULL REFERENCES s06_notes.notes(id) ON DELETE CASCADE,
    
    -- Link data
    link_text TEXT NOT NULL,
    start_position INTEGER NOT NULL,
    end_position INTEGER NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    
    -- Sync metadata
    version INTEGER DEFAULT 1 NOT NULL
);

-- Indeksy dla wydajności
CREATE INDEX idx_notes_user ON s06_notes.notes(user_id, deleted_at);
CREATE INDEX idx_notes_parent ON s06_notes.notes(parent_id, sort_order);
CREATE INDEX idx_notes_updated ON s06_notes.notes(updated_at DESC);
CREATE INDEX idx_links_source ON s06_notes.note_links(source_note_id);
CREATE INDEX idx_links_target ON s06_notes.note_links(target_note_id);

-- Trigger dla auto-update updated_at
CREATE OR REPLACE FUNCTION s06_notes.update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER update_notes_updated_at 
BEFORE UPDATE ON s06_notes.notes
FOR EACH ROW EXECUTE FUNCTION s06_notes.update_updated_at_column();
```

---

### FAZA 2: Modele SQLAlchemy (Backend)

**Plik:** `Render_upload/app/notes_models.py`

```python
from sqlalchemy import Column, String, Text, Integer, Boolean, TIMESTAMP, ForeignKey
from datetime import datetime
from .database import Base

class Note(Base):
    """Model notatki w PostgreSQL"""
    __tablename__ = 'notes'
    __table_args__ = {'schema': 's06_notes'}
    
    # Primary key
    id = Column(String, primary_key=True)
    
    # Foreign keys
    user_id = Column(String, ForeignKey('s01_user_accounts.users.id', ondelete='CASCADE'), nullable=False)
    parent_id = Column(String, ForeignKey('s06_notes.notes.id', ondelete='CASCADE'), nullable=True)
    
    # Data
    title = Column(String(500), nullable=False)
    content = Column(Text, nullable=True)
    color = Column(String(20), default='#1976D2')
    sort_order = Column(Integer, default=0)
    is_favorite = Column(Boolean, default=False)
    
    # Timestamps & sync
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    updated_at = Column(TIMESTAMP, default=datetime.utcnow, onupdate=datetime.utcnow)
    deleted_at = Column(TIMESTAMP, nullable=True)
    synced_at = Column(TIMESTAMP, nullable=True)
    version = Column(Integer, default=1, nullable=False)

class NoteLink(Base):
    """Model hiperłącza między notatkami"""
    __tablename__ = 'note_links'
    __table_args__ = {'schema': 's06_notes'}
    
    id = Column(String, primary_key=True)
    source_note_id = Column(String, ForeignKey('s06_notes.notes.id', ondelete='CASCADE'), nullable=False)
    target_note_id = Column(String, ForeignKey('s06_notes.notes.id', ondelete='CASCADE'), nullable=False)
    link_text = Column(String(500), nullable=False)
    start_position = Column(Integer, nullable=False)
    end_position = Column(Integer, nullable=False)
    created_at = Column(TIMESTAMP, default=datetime.utcnow)
    version = Column(Integer, default=1, nullable=False)
```

---

### FAZA 3: API Router (Backend)

**Plik:** `Render_upload/app/notes_router.py`

**Endpointy (wzorowane na alarms_router.py):**

```python
# CRUD Operations
POST   /api/notes              # Upsert (create/update)
GET    /api/notes              # List all (with filters)
GET    /api/notes/{note_id}    # Get single
DELETE /api/notes/{note_id}    # Soft/hard delete

# Bulk sync
POST   /api/notes/bulk         # Bulk synchronization

# Links
POST   /api/notes/{note_id}/links     # Create link
GET    /api/notes/{note_id}/links     # Get note links
DELETE /api/notes/links/{link_id}     # Delete link

# Hierarchy
GET    /api/notes/{note_id}/children  # Get child notes
GET    /api/notes/roots               # Get root notes (no parent)

# WebSocket
WS     /api/notes/ws                  # Real-time sync
```

**Kluczowe funkcje:**
- Version-based conflict detection
- Soft delete support
- Hierarchical queries (parent-child)
- Bulk operations for offline sync
- WebSocket notifications

---

### FAZA 4: API Client (Frontend)

**Plik:** `src/Modules/Note_module/note_api_client.py`

```python
class NotesAPIClient:
    """HTTP client dla synchronizacji notatek"""
    
    def __init__(self, base_url, auth_token, refresh_token, on_token_refreshed):
        # Wzorowane na alarm_api_client.py
        
    def sync_note(self, note_data: Dict, user_id: str) -> APIResponse:
        """Upsert notatki z conflict resolution"""
        
    def sync_note_link(self, link_data: Dict) -> APIResponse:
        """Sync hiperłącza"""
        
    def fetch_all_notes(self, user_id: str) -> APIResponse:
        """Pobierz wszystkie notatki użytkownika"""
        
    def fetch_note_hierarchy(self, note_id: str) -> APIResponse:
        """Pobierz notatkę z dziećmi"""
        
    def delete_note(self, note_id: str, soft: bool = True) -> APIResponse:
        """Usuń notatkę (soft/hard)"""
        
    def bulk_sync(self, notes: List[Dict], links: List[Dict], user_id: str) -> APIResponse:
        """Bulk synchronizacja"""
```

---

### FAZA 5: WebSocket Client (Frontend)

**Plik:** `src/Modules/Note_module/note_websocket_client.py`

```python
class NoteWebSocketClient(QThread):
    """WebSocket dla real-time synchronizacji notatek"""
    
    # Signals
    note_created = pyqtSignal(dict)
    note_updated = pyqtSignal(dict)
    note_deleted = pyqtSignal(dict)
    link_created = pyqtSignal(dict)
    sync_required = pyqtSignal(str)
    
    # Wzorowane na alarm_websocket_client.py
```

---

### FAZA 6: Sync Manager (Frontend)

**Plik:** `src/Modules/Note_module/notes_sync_manager.py`

```python
class NotesSyncManager:
    """Background synchronizacja notatek"""
    
    def __init__(self, local_db: NoteDatabase, api_client: NotesAPIClient, user_id: str):
        # Wzorowane na alarms_sync_manager.py
        
    def start(self):
        """Uruchom background worker"""
        
    def _sync_cycle(self):
        """Cykl synchronizacji:
        1. Pobierz z sync_queue
        2. Sync notes
        3. Sync note_links
        4. Resolve conflicts
        5. Update local DB
        """
        
    def _resolve_conflict(self, local_note, server_note) -> Dict:
        """Last-write-wins based on updated_at"""
        
    def initial_sync(self) -> bool:
        """Początkowa synchronizacja przy starcie"""
```

---

### FAZA 7: Aktualizacja lokalnej bazy (Frontend)

**Plik:** `src/Modules/Note_module/note_module_logic.py`

**Zmiany w NoteDatabase:**

```python
# Dodać pola do tabeli notes:
ALTER TABLE notes ADD COLUMN version INTEGER DEFAULT 1;
ALTER TABLE notes ADD COLUMN synced_at TEXT;

# Dodać sync_queue table:
CREATE TABLE IF NOT EXISTS sync_queue (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_type TEXT NOT NULL, -- 'note' or 'link'
    entity_id TEXT NOT NULL,
    action TEXT NOT NULL, -- 'create', 'update', 'delete'
    data TEXT, -- JSON
    created_at TEXT NOT NULL,
    retry_count INTEGER DEFAULT 0,
    error TEXT
);

# Nowe metody:
def get_unsynced_notes() -> List[Dict]
def mark_note_synced(note_id: str) -> bool
def update_note_version(note_id: str, version: int) -> bool
def add_to_sync_queue(entity_type, entity_id, action, data)
def get_sync_queue(limit: int) -> List[Dict]
```

---

## 🔄 KOLEJNOŚĆ IMPLEMENTACJI

### Krok 1: Schemat PostgreSQL ✅
```bash
# Wykonaj SQL query na Render PostgreSQL
psql -h dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com \
     -U pro_ka_po_user \
     -d pro_ka_po \
     -f s06_notes_schema.sql
```

### Krok 2: Backend Models ✅
- Utwórz `notes_models.py`
- Dodaj import w `main.py`

### Krok 3: Backend Router ✅
- Utwórz `notes_router.py` z wszystkimi endpointami
- Dodaj do `main.py`: `app.include_router(notes_router)`
- Test z Postman/Thunder Client

### Krok 4: Frontend API Client ✅
- Utwórz `note_api_client.py`
- Test połączenia z API

### Krok 5: Aktualizacja lokalnej bazy ✅
- Dodaj pola sync do SQLite
- Dodaj sync_queue
- Dodaj metody sync

### Krok 6: WebSocket Client ✅
- Utwórz `note_websocket_client.py`
- Integracja z UI

### Krok 7: Sync Manager ✅
- Utwórz `notes_sync_manager.py`
- Background worker
- Conflict resolution

### Krok 8: Integracja z UI ✅
- Połącz sync manager z `note_view.py`
- Status LED dla sync
- Error handling

---

## 🧪 TESTOWANIE

### Test 1: Podstawowa synchronizacja
1. Utwórz notatkę offline
2. Zaloguj się (token)
3. Sprawdź czy zsynchronizowało

### Test 2: Conflict resolution
1. Utwórz notatkę na urządzeniu A
2. Edytuj tę samą notatkę na urządzeniu B (offline)
3. Połącz B - sprawdź czy conflict się rozwiązał (last-write-wins)

### Test 3: Hierarchia
1. Utwórz notatkę z podnotatkami
2. Sync - sprawdź czy parent_id zachowane
3. Usuń parent - sprawdź czy cascade delete działa

### Test 4: WebSocket
1. Otwórz aplikację na 2 urządzeniach
2. Edytuj notatkę na A
3. Sprawdź czy B dostał update przez WebSocket

---

## 📝 RÓŻNICE VS MODUŁ ALARM

| Aspekt | Alarm | Notes | Rozwiązanie |
|--------|-------|-------|-------------|
| Struktura | Flat (unified table) | Hierarchiczna (parent_id) | Zachować parent_id, dodać indeksy |
| Relacje | Brak dodatkowych | note_links | Osobna tabela + sync |
| Pole type | 'alarm'\|'timer' | Nie potrzebne | Jeden typ: 'note' |
| Conflict | Last-write-wins | Last-write-wins | Identyczne |
| Soft delete | ✅ | ✅ | Identyczne |

---

## ⚠️ UWAGI KRYTYCZNE

1. **Parent-child synchronizacja:**
   - Sync musi zachować kolejność (parent przed child)
   - Bulk sync: sortuj po parent_id (roots first)

2. **Note links synchronizacja:**
   - Sync link tylko jeśli oba notes zsynchronizowane
   - Jeśli target note niezsync - dodaj do queue

3. **Cascade delete:**
   - PostgreSQL ma ON DELETE CASCADE
   - SQLite także - upewnij się że działa

4. **HTML content:**
   - Walidacja długości (max 100KB?)
   - Escape HTML przy sync (bezpieczeństwo)

5. **WebSocket events:**
   ```
   note_created: {note_id, parent_id, user_id}
   note_updated: {note_id, version}
   note_deleted: {note_id}
   link_created: {link_id, source, target}
   ```

---

## 📋 CHECKLIST

### Backend (Render)
- [ ] SQL schema s06_notes created
- [ ] notes_models.py created
- [ ] notes_router.py created
- [ ] WebSocket support added
- [ ] Tests with Postman

### Frontend (Desktop)
- [ ] note_api_client.py created
- [ ] note_websocket_client.py created
- [ ] notes_sync_manager.py created
- [ ] NoteDatabase updated (version, synced_at, sync_queue)
- [ ] Integration with note_view.py
- [ ] Status LED integration
- [ ] Error handling & retry logic

### Testing
- [ ] Basic CRUD sync
- [ ] Hierarchy sync (parent-child)
- [ ] Links sync
- [ ] Conflict resolution
- [ ] WebSocket real-time
- [ ] Offline → Online sync
- [ ] Cascade delete

---

## 🚀 DEPLOYMENT

### Lokalne API (development)
```bash
cd Render_upload
uvicorn app.main:app --reload --port 8000
```

### Render (production)
1. Push do GitHub
2. Render auto-deploy
3. Test z produkcyjnym URL

---

## 📞 NASTĘPNE KROKI

1. ✅ **ZATWIERDZENIE PLANU** - weryfikacja z użytkownikiem
2. 📝 **Schemat SQL** - przygotowanie query
3. 🔧 **Backend Models** - SQLAlchemy
4. 🌐 **Router** - FastAPI endpoints
5. 💻 **Frontend Client** - HTTP + WebSocket
6. 🔄 **Sync Manager** - Background worker
7. ✅ **Testing** - End-to-end

---

**Podsumowanie:**
Plan jest spójny z istniejącą architekturą modułu Alarm. Główne różnice to hierarchia (parent_id) i dodatkowa tabela note_links. Implementacja będzie w 8 krokach, z priorytetem na schemat PostgreSQL i backend API.

**Czas realizacji:** ~8-12h (przy założeniu wzorowania się na module Alarm)

**Ready to start!** 🎯
