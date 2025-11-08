# CallCryptor Module - Plan Implementacji

**Data utworzenia:** 8 listopada 2025  
**Wersja:** 1.0  
**Autor:** AI Assistant

---

## 📋 Spis treści

1. [Przegląd modułu](#przegląd-modułu)
2. [Architektura](#architektura)
3. [Fazy implementacji](#fazy-implementacji)
4. [Struktura bazy danych](#struktura-bazy-danych)
5. [Integracje z systemami](#integracje-z-systemami)
6. [UI/UX Specyfikacja](#uiux-specyfikacja)
7. [API i funkcjonalności](#api-i-funkcjonalności)
8. [Zależności i biblioteki](#zależności-i-biblioteki)

---

## 🎯 Przegląd modułu

### Cel
CallCryptor to moduł zarządzania nagraniami rozmów z możliwością:
- Skanowania folderów lokalnych i skrzynek e-mail w poszukiwaniu nagrań
- Automatycznej transkrypcji nagrań
- Generowania podsumowań AI
- Tworzenia notatek i zadań z nagrań
- Organizacji przez tagi i archiwizację

### Kluczowe funkcjonalności
- ✅ Wieloźródłowe zarządzanie (foldery + e-mail)
- ✅ Transkrypcja audio → tekst
- ✅ Podsumowania AI
- ✅ Integracja z modułem notatek i zadań
- ✅ System tagów
- ✅ Archiwizacja
- ✅ Synchronizacja z serwerem (last win)

---

## 🏗️ Architektura

### Schemat przepływu danych

```
┌─────────────────────────────────────────────────────────────┐
│                    ŹRÓDŁA NAGRAŃ                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────────────┐         ┌──────────────────┐         │
│  │  Folder lokalny  │         │  Skrzynka e-mail │         │
│  │  - Ścieżka       │         │  - Konto         │         │
│  │  - Rozszerzenia  │         │  - Fraza         │         │
│  │  - Głębokość     │         │  - Folder        │         │
│  └────────┬─────────┘         └────────┬─────────┘         │
│           │                            │                   │
│           └────────────┬───────────────┘                   │
│                        │                                   │
└────────────────────────┼───────────────────────────────────┘
                         │
                         ▼
         ┌───────────────────────────┐
         │   Email Helper Connector  │
         │   - IMAP/POP3 support     │
         │   - Multi-account         │
         │   - Attachment download   │
         └───────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │  CallCryptor Database     │
         │  - recording_sources      │
         │  - recordings             │
         │  - recording_tags         │
         └───────────┬───────────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │   CallCryptor View        │
         │   - Tabela nagrań         │
         │   - Przyciski akcji       │
         │   - Filtry i wyszukiwanie │
         └───────────┬───────────────┘
                     │
         ┌───────────┴───────────┐
         │                       │
         ▼                       ▼
┌─────────────────┐   ┌─────────────────┐
│  Transkrypcja   │   │  AI Summary     │
│  - Whisper API  │   │  - Gemini/GPT   │
│  -              │   │  - Claude       │
└─────────────────┘   └─────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
                     ▼
         ┌───────────────────────────┐
         │   Integracje              │
         │   - Notes Module          │
         │   - Tasks Module          │
         │   - Voice Assistant       │
         └───────────────────────────┘
```

### Architektura Local-First

```
┌─────────────────────────────────────────────────────────────┐
│                         UI Layer                            │
│              (CallCryptorView + Dialogs)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                    Business Logic                           │
│            (CallCryptorManager + Helpers)                   │
└────────────┬───────────────────────┬────────────────────────┘
             │                       │
             ▼                       ▼
┌────────────────────┐   ┌──────────────────────────┐
│  Local Database    │   │    Sync Manager          │
│  (SQLite)          │   │    - Queue pending ops   │
│  - Offline-first   │◄──┤    - Last-write-wins     │
│  - is_synced flag  │   │    - Background worker   │
└────────────────────┘   └──────────┬───────────────┘
                                    │
                                    ▼
                         ┌──────────────────────────┐
                         │   API Client             │
                         │   - PostgreSQL Server    │
                         │   - WebSocket updates    │
                         └──────────────────────────┘
```

---

## 📊 Fazy implementacji

### 🔵 FAZA 1: Infrastruktura E-mail (PRIORYTET WYSOKI)

**Czas:** 2-3 dni  
**Pliki:**
- `src/core/assisstant/modules/email_helper.py`
- `src/ui/email_settings_card.py`
- `src/database/email_accounts.db` (schemat)

**Zadania:**
1. ✅ Implementacja EmailConnector
   - IMAP support
   - POP3 support
   - Multi-account management
   - Search & download attachments

2. ✅ Baza danych kont e-mail
   - Tabela `email_accounts`
   - Encryption dla haseł (keyring)
   - CRUD operations

3. ✅ Email Settings Card (UI)
   - Lista kont
   - Dodawanie/edycja/usuwanie
   - Test połączenia
   - Integracja z theme manager i i18n

4. ✅ Integracja w Config View
   - Dodanie karty "Email Accounts"
   - Signal/slot connections

**Warunki ukończenia:**
- [ ] Użytkownik może dodać konto e-mail
- [ ] Połączenie testowe działa
- [ ] Hasła są bezpiecznie przechowywane
- [ ] UI reaguje na zmiany motywu i języka

---

### 🟢 FAZA 2: Baza danych CallCryptor

**Czas:** 1 dzień  
**Pliki:**
- `src/Modules/CallCryptor_module/callcryptor_database.py`

**Zadania:**
1. ✅ Schemat tabel
   - `recording_sources`
   - `recordings`
   - `recording_tags`

2. ✅ CRUD operations
   - Add/update/delete sources
   - Add/update/delete recordings
   - Tag management

3. ✅ Sync support
   - `is_synced` flags
   - `synced_at` timestamps
   - Version tracking

**Warunki ukończenia:**
- [ ] Wszystkie tabele utworzone
- [ ] CRUD działa poprawnie
- [ ] Migracje działają

---

### 🟡 FAZA 3: CallCryptor View (Podstawowy UI)

**Czas:** 2-3 dni  
**Pliki:**
- `src/ui/callcryptor_view.py`
- `src/Modules/CallCryptor_module/callcryptor_dialogs.py`

**Zadania:**
1. ✅ Główny widok
   - Toolbar z przyciskami
   - QComboBox wyboru źródła
   - QTableWidget z nagraniami

2. ✅ Dialogi
   - AddSourceDialog (folder/email)
   - EditTagsDialog
   - RecordingDetailsDialog

3. ✅ Integracja systemowa
   - Theme Manager
   - i18n Manager
   - Icons

**Warunki ukończenia:**
- [ ] Widok wyświetla się poprawnie
- [ ] Tabela pokazuje nagrania
- [ ] Dialogi otwierają się i zapisują dane
- [ ] Wszystko reaguje na zmianę motywu

---

### 🟠 FAZA 4: Skanowanie źródeł

**Czas:** 2 dni  
**Pliki:**
- `src/Modules/CallCryptor_module/source_scanner.py`

**Zadania:**
1. ✅ Scanner folderów lokalnych
   - Rekurencyjne skanowanie
   - Filtrowanie po rozszerzeniach
   - Limit głębokości
   - Metadata extraction (duration, date)

2. ✅ Scanner skrzynek e-mail
   - Search by phrase
   - Download attachments
   - Parse metadata
   - Duplicate detection

3. ✅ Background scanning
   - QThread dla długich operacji
   - Progress bar
   - Cancellation support

**Warunki ukończenia:**
- [ ] Folder scanner znajduje pliki
- [ ] Email scanner pobiera załączniki
- [ ] Metadane są poprawnie wyodrębniane
- [ ] UI nie blokuje się podczas skanowania

---

### 🔴 FAZA 5: Transkrypcja i AI

**Czas:** 3-4 dni  
**Pliki:**
- `src/Modules/CallCryptor_module/transcription_service.py`
- `src/Modules/CallCryptor_module/ai_summary_service.py`

**Zadania:**
1. ✅ Transkrypcja Service
   - Integracja z Whisper API
   - Lokalna opcja (whisper.cpp)
   - Queue management
   - Error handling

2. ✅ AI Summary Service
   - Integracja z AI Module
   - Custom prompts dla call summaries
   - Key points extraction
   - Action items detection

3. ✅ Status tracking
   - Progress updates
   - Error messages
   - Retry logic

**Warunki ukończenia:**
- [ ] Transkrypcja działa (API lub lokalnie)
- [ ] AI generuje sensowne podsumowania
- [ ] Status jest widoczny w UI
- [ ] Błędy są obsługiwane

---

### 🟣 FAZA 6: Integracje

**Czas:** 2 dni  
**Pliki:**
- `src/Modules/CallCryptor_module/callcryptor_integrations.py`

**Zadania:**
1. ✅ Integracja z Notes Module
   - Create note from recording
   - Link recording to note
   - Automatic title generation

2. ✅ Integracja z Tasks Module
   - Create task from recording
   - Extract action items
   - Link recording to task

3. ✅ Voice Assistant
   - "otwórz nagrania"
   - "transkrybuj nagranie"
   - "podsumuj nagranie"

**Warunki ukończenia:**
- [ ] Notatka tworzy się z transkrypcji
- [ ] Zadanie tworzy się z action items
- [ ] Asystent reaguje na komendy

---

### 🟤 FAZA 7: Synchronizacja

**Czas:** 2-3 dni  
**Pliki:**
- `src/Modules/CallCryptor_module/callcryptor_sync_manager.py`
- `src/Modules/CallCryptor_module/callcryptor_api_client.py`

**Zadania:**
1. ✅ Sync Manager
   - Background worker
   - Queue operations
   - Last-write-wins strategy
   - Network availability check

2. ✅ API Client
   - REST endpoints
   - WebSocket updates
   - Conflict resolution

3. ✅ Server-side (Render)
   - Database tables
   - API routes
   - WebSocket handlers

**Warunki ukończenia:**
- [ ] Lokalne zmiany synchronizują się
- [ ] Zdalne zmiany aktualizują UI
- [ ] Konflikty są rozwiązywane
- [ ] Działa offline

---

## 🗄️ Struktura bazy danych

### Lokalna baza (SQLite)

**Lokalizacja:** `~/.pro_ka_po/callcryptor.db`

#### Tabela: recording_sources

```sql
CREATE TABLE recording_sources (
    -- Identyfikatory
    id TEXT PRIMARY KEY,                    -- UUID
    user_id TEXT NOT NULL,                  -- FK do users
    
    -- Podstawowe info
    source_name TEXT NOT NULL,              -- Nazwa wyświetlana
    source_type TEXT NOT NULL,              -- 'folder' | 'email'
    
    -- Opcje dla source_type = 'folder'
    folder_path TEXT,                       -- Ścieżka do folderu
    file_extensions TEXT,                   -- JSON: ["mp3", "wav", "m4a"]
    scan_depth INTEGER DEFAULT 1,           -- Głębokość rekurencji
    
    -- Opcje dla source_type = 'email'
    email_account_id TEXT,                  -- FK do email_accounts
    search_phrase TEXT,                     -- Fraza do wyszukiwania
    target_folder TEXT,                     -- Folder w skrzynce (np. "INBOX")
    attachment_pattern TEXT,                -- Regex dla nazw załączników
    
    -- Metadata
    is_active BOOLEAN DEFAULT 1,
    last_scan_at TEXT,                      -- ISO timestamp ostatniego skanowania
    recordings_count INTEGER DEFAULT 0,      -- Liczba nagrań
    
    -- Timestamps
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    
    -- Synchronizacja
    is_synced BOOLEAN DEFAULT 0,
    synced_at TEXT,
    version INTEGER DEFAULT 1,
    
    -- Foreign Keys
    FOREIGN KEY (email_account_id) REFERENCES email_accounts(id)
);

-- Indeksy
CREATE INDEX idx_sources_user ON recording_sources(user_id);
CREATE INDEX idx_sources_type ON recording_sources(source_type);
CREATE INDEX idx_sources_active ON recording_sources(is_active);
```

#### Tabela: recordings

```sql
CREATE TABLE recordings (
    -- Identyfikatory
    id TEXT PRIMARY KEY,                    -- UUID
    user_id TEXT NOT NULL,
    source_id TEXT NOT NULL,                -- FK do recording_sources
    
    -- Info o pliku
    file_name TEXT NOT NULL,
    file_path TEXT,                         -- Dla lokalnych plików
    file_size INTEGER,                      -- W bajtach
    file_hash TEXT,                         -- MD5/SHA256 dla deduplication
    
    -- Info z e-mail (jeśli applicable)
    email_message_id TEXT,                  -- Message-ID z e-maila
    email_subject TEXT,                     -- Temat wiadomości
    email_sender TEXT,                      -- Nadawca
    
    -- Metadata nagrania
    contact_name TEXT,                      -- Nazwa kontaktu
    contact_phone TEXT,                     -- Numer telefonu (opcjonalnie)
    duration INTEGER,                       -- Czas trwania w sekundach
    recording_date TEXT,                    -- ISO timestamp
    
    -- Organizacja
    tags TEXT,                              -- JSON: ["tag1", "tag2"]
    notes TEXT,                             -- Notatki użytkownika
    
    -- Transkrypcja
    transcription_status TEXT DEFAULT 'pending',  -- pending|processing|completed|failed
    transcription_text TEXT,
    transcription_language TEXT,            -- Wykryty język (np. "pl")
    transcription_confidence REAL,          -- 0.0 - 1.0
    transcription_date TEXT,
    transcription_error TEXT,               -- Komunikat błędu (jeśli failed)
    
    -- AI Summary
    ai_summary_status TEXT DEFAULT 'pending',
    ai_summary_text TEXT,
    ai_summary_date TEXT,
    ai_summary_error TEXT,
    ai_key_points TEXT,                     -- JSON: ["punkt1", "punkt2"]
    ai_action_items TEXT,                   -- JSON: [{"action": "...", "priority": "..."}]
    
    -- Linki do innych modułów
    note_id TEXT,                           -- FK do notes (jeśli utworzono)
    task_id TEXT,                           -- FK do tasks (jeśli utworzono)
    
    -- Archiwizacja
    is_archived BOOLEAN DEFAULT 0,
    archived_at TEXT,
    archive_reason TEXT,
    
    -- Timestamps
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    
    -- Synchronizacja
    is_synced BOOLEAN DEFAULT 0,
    synced_at TEXT,
    version INTEGER DEFAULT 1,
    
    -- Foreign Keys
    FOREIGN KEY (source_id) REFERENCES recording_sources(id) ON DELETE CASCADE,
    FOREIGN KEY (note_id) REFERENCES notes(id) ON DELETE SET NULL,
    FOREIGN KEY (task_id) REFERENCES tasks(id) ON DELETE SET NULL
);

-- Indeksy
CREATE INDEX idx_recordings_user ON recordings(user_id);
CREATE INDEX idx_recordings_source ON recordings(source_id);
CREATE INDEX idx_recordings_date ON recordings(recording_date);
CREATE INDEX idx_recordings_status ON recordings(transcription_status);
CREATE INDEX idx_recordings_archived ON recordings(is_archived);
CREATE INDEX idx_recordings_hash ON recordings(file_hash);  -- Dla deduplication
```

#### Tabela: recording_tags

```sql
CREATE TABLE recording_tags (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    tag_name TEXT UNIQUE NOT NULL,
    tag_color TEXT DEFAULT '#2196F3',       -- Hex color
    tag_icon TEXT,                          -- Emoji lub ikona
    usage_count INTEGER DEFAULT 0,          -- Ile razy użyty
    created_at TEXT NOT NULL,
    
    -- Indeks
    UNIQUE(user_id, tag_name)
);

CREATE INDEX idx_tags_user ON recording_tags(user_id);
```

#### Tabela: email_accounts

```sql
CREATE TABLE email_accounts (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    
    -- Dane konta
    account_name TEXT NOT NULL,             -- Nazwa wyświetlana
    email_address TEXT NOT NULL,
    
    -- Konfiguracja serwera
    server_type TEXT NOT NULL,              -- 'IMAP' | 'POP3'
    server_address TEXT NOT NULL,
    server_port INTEGER NOT NULL,
    
    -- Credentials
    username TEXT NOT NULL,
    password TEXT NOT NULL,                 -- ENCRYPTED!
    
    -- Opcje
    use_ssl BOOLEAN DEFAULT 1,
    use_tls BOOLEAN DEFAULT 0,
    
    -- Status
    is_active BOOLEAN DEFAULT 1,
    last_connection_at TEXT,
    connection_error TEXT,
    
    -- Timestamps
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    
    -- Synchronizacja
    is_synced BOOLEAN DEFAULT 0,
    synced_at TEXT
);

CREATE INDEX idx_email_accounts_user ON email_accounts(user_id);
```

---

## 🔗 Integracje z systemami

### 1. Wielojęzyczność (i18n)

**Klucze tłumaczeń:**

```json
{
  "callcryptor.title": "CallCryptor - Nagrania rozmów",
  "callcryptor.source": "Źródło",
  "callcryptor.add_source": "Dodaj źródło",
  "callcryptor.export": "Eksportuj",
  "callcryptor.edit_tags": "Zarządzaj tagami",
  "callcryptor.delete_source": "Usuń źródło",
  "callcryptor.refresh": "Odśwież",
  "callcryptor.record": "Nagrywaj",
  "callcryptor.scan": "Skanuj",
  
  "callcryptor.table.contact": "Kontakt",
  "callcryptor.table.duration": "Czas trwania",
  "callcryptor.table.date": "Data nagrania",
  "callcryptor.table.tag": "Tag",
  "callcryptor.table.transcribe": "Transkrypcja",
  "callcryptor.table.ai_summary": "Podsumowanie AI",
  "callcryptor.table.note": "Notatka",
  "callcryptor.table.task": "Zadanie",
  "callcryptor.table.archive": "Archiwizuj",
  "callcryptor.table.delete": "Usuń",
  
  "callcryptor.dialog.add_source.title": "Dodaj nowe źródło nagrań",
  "callcryptor.dialog.source_name": "Nazwa źródła:",
  "callcryptor.dialog.source_type": "Typ źródła:",
  "callcryptor.dialog.folder_local": "Folder lokalny",
  "callcryptor.dialog.email_account": "Skrzynka e-mail",
  "callcryptor.dialog.folder_path": "Ścieżka do folderu:",
  "callcryptor.dialog.browse": "Przeglądaj...",
  "callcryptor.dialog.extensions": "Rozszerzenia plików:",
  "callcryptor.dialog.scan_depth": "Głębokość skanowania:",
  "callcryptor.dialog.email_select": "Wybierz konto e-mail:",
  "callcryptor.dialog.search_phrase": "Fraza wyszukiwania:",
  "callcryptor.dialog.email_folder": "Folder:",
  
  "callcryptor.status.transcribing": "Transkrypcja w toku...",
  "callcryptor.status.generating_summary": "Generowanie podsumowania...",
  "callcryptor.status.completed": "Zakończono",
  "callcryptor.status.failed": "Błąd",
  
  "callcryptor.message.scan_complete": "Skanowanie zakończone. Znaleziono {count} nagrań.",
  "callcryptor.message.transcription_started": "Rozpoczęto transkrypcję",
  "callcryptor.message.note_created": "Utworzono notatkę z nagrania",
  "callcryptor.message.task_created": "Utworzono zadanie z nagrania",
  
  "settings.email_accounts": "Konta e-mail",
  "settings.email.add_account": "Dodaj konto",
  "settings.email.account_name": "Nazwa konta:",
  "settings.email.email_address": "Adres e-mail:",
  "settings.email.server_type": "Typ serwera:",
  "settings.email.server_address": "Adres serwera:",
  "settings.email.server_port": "Port:",
  "settings.email.username": "Nazwa użytkownika:",
  "settings.email.password": "Hasło:",
  "settings.email.use_ssl": "Użyj SSL",
  "settings.email.test_connection": "Testuj połączenie"
}
```

### 2. Theme Manager

**Stylowanie komponentów:**

```python
def apply_theme(self):
    """Aplikuj motyw do wszystkich komponentów"""
    colors = self.theme_manager.get_current_colors()
    
    # Tabela
    table_style = f"""
        QTableWidget {{
            background-color: {colors['bg_main']};
            alternate-background-color: {colors['bg_secondary']};
            gridline-color: {colors['border_light']};
            color: {colors['text_primary']};
        }}
        QTableWidget::item:selected {{
            background-color: {colors['accent_primary']};
            color: white;
        }}
        QHeaderView::section {{
            background-color: {colors['bg_secondary']};
            color: {colors['text_primary']};
            border: 1px solid {colors['border_light']};
            padding: 5px;
        }}
    """
    self.table.setStyleSheet(table_style)
    
    # Przyciski akcji
    btn_style = f"""
        QPushButton {{
            background-color: {colors['accent_primary']};
            color: white;
            border: none;
            padding: 8px 16px;
            border-radius: 4px;
        }}
        QPushButton:hover {{
            background-color: {colors['accent_hover']};
        }}
        QPushButton:pressed {{
            background-color: {colors['accent_pressed']};
        }}
    """
    for btn in self.action_buttons:
        btn.setStyleSheet(btn_style)
```

### 3. Voice Assistant

**Frazy i akcje:**

```python
# W assistant_phrases (baza danych)
CALLCRYPTOR_PHRASES = [
    # Otwarcie widoku
    ("pl", "otwórz nagrania", "open_callcryptor", 10),
    ("pl", "pokaż nagrania", "open_callcryptor", 9),
    ("en", "open recordings", "open_callcryptor", 10),
    ("de", "öffne aufnahmen", "open_callcryptor", 10),
    
    # Transkrypcja
    ("pl", "transkrybuj nagranie", "transcribe_recording", 10),
    ("pl", "przepisz nagranie", "transcribe_recording", 8),
    ("en", "transcribe recording", "transcribe_recording", 10),
    
    # Podsumowanie
    ("pl", "podsumuj nagranie", "summarize_recording", 10),
    ("pl", "podsumowanie ai", "summarize_recording", 9),
    ("en", "summarize recording", "summarize_recording", 10),
    
    # Skanowanie
    ("pl", "skanuj nagrania", "scan_sources", 10),
    ("en", "scan recordings", "scan_sources", 10),
]
```

### 4. Synchronizacja (Last-Write-Wins)

**Strategia:**

```python
def resolve_conflict(local_data: dict, server_data: dict) -> tuple[dict, str]:
    """
    Rozwiązuje konflikt między lokalną a serwerową wersją.
    
    Strategia: Last-Write-Wins
    - Porównaj updated_at timestamps
    - Nowszy wygrywa
    - Jeśli identyczne -> serwer wygrywa (source of truth)
    
    Returns:
        (winning_data, winner)  # winner: 'local' | 'server'
    """
    local_updated = datetime.fromisoformat(local_data['updated_at'])
    server_updated = datetime.fromisoformat(server_data['updated_at'])
    
    if local_updated > server_updated:
        return (local_data, 'local')
    else:
        return (server_data, 'server')
```

---

## 🎨 UI/UX Specyfikacja

### Layout głównego widoku

```
┌────────────────────────────────────────────────────────────────┐
│ CallCryptor - Nagrania rozmów                                  │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  Źródło: [Wszystkie nagrania     ▼]  [➕][💾][🏷️][🗑️][🔄][🎙️] │
│                                                                │
├────────────────────────────────────────────────────────────────┤
│  ID/Kontakt  │ Czas │  Data   │ Tag  │📝│🤖│📒│✅│📦│🗑️│        │
├──────────────┼──────┼─────────┼──────┼──┼──┼──┼──┼──┼──┤        │
│ Jan Kowalski │ 5:23 │ 2025-11 │ 📞  │✓ │✓ │  │  │  │  │        │
│ Firma XYZ    │ 12:45│ 2025-11 │ 💼  │✓ │  │✓ │✓ │  │  │        │
│ Helpdesk     │ 3:12 │ 2025-11 │ 🆘  │  │  │  │  │  │  │        │
│ ...          │ ...  │ ...     │ ... │  │  │  │  │  │  │        │
└────────────────────────────────────────────────────────────────┘
```

### Ikony i ich znaczenie

| Ikona | Funkcja | Opis |
|-------|---------|------|
| 📝 | Transkrypcja | Rozpocznij/pokaż transkrypcję |
| 🤖 | AI Summary | Wygeneruj podsumowanie AI |
| 📒 | Notatka | Utwórz notatkę z nagrania |
| ✅ | Zadanie | Utwórz zadanie z action items |
| 📦 | Archiwum | Zarchiwizuj nagranie |
| 🗑️ | Usuń | Usuń nagranie |
| ➕ | Dodaj | Dodaj nowe źródło |
| 💾 | Export | Eksportuj do CSV/JSON |
| 🏷️ | Tagi | Zarządzaj tagami |
| 🔄 | Odśwież | Skanuj ponownie źródła |
| 🎙️ | Nagrywaj | Rozpocznij nowe nagranie |

### Dialog dodawania źródła

```
┌──────────────────────────────────────────────────┐
│ Dodaj nowe źródło nagrań                    [✕]  │
├──────────────────────────────────────────────────┤
│                                                  │
│  Nazwa źródła:                                   │
│  [_____________________________________________] │
│                                                  │
│  Typ źródła:                                     │
│  ⦿ Folder lokalny      ○ Skrzynka e-mail        │
│                                                  │
│  ╔════════════════════════════════════════════╗ │
│  ║ Opcje dla folderu lokalnego                ║ │
│  ╠════════════════════════════════════════════╣ │
│  ║ Ścieżka do folderu:                        ║ │
│  ║ [C:\Users\...\Recordings    ] [Przeglądaj] ║ │
│  ║                                            ║ │
│  ║ Rozszerzenia plików:                       ║ │
│  ║ ☑ .mp3   ☑ .wav   ☑ .m4a   ☐ .ogg         ║ │
│  ║ ☐ .flac  ☐ .aac   ☐ .wma   ☐ .opus        ║ │
│  ║                                            ║ │
│  ║ Głębokość skanowania:                      ║ │
│  ║ [1 ▼] (1 = tylko główny folder)           ║ │
│  ╚════════════════════════════════════════════╝ │
│                                                  │
│  ╔════════════════════════════════════════════╗ │
│  ║ Opcje dla skrzynki e-mail                  ║ │
│  ╠════════════════════════════════════════════╣ │
│  ║ Konto e-mail:                              ║ │
│  ║ [Wybierz konto                         ▼]  ║ │
│  ║                                            ║ │
│  ║ Fraza wyszukiwania:                        ║ │
│  ║ [nagranie rozmowy___________________]      ║ │
│  ║                                            ║ │
│  ║ Folder w skrzynce:                         ║ │
│  ║ [INBOX                                 ▼]  ║ │
│  ║                                            ║ │
│  ║ Wzorzec nazw załączników (regex):          ║ │
│  ║ [.*\.(mp3|wav|m4a)$__________________]     ║ │
│  ╚════════════════════════════════════════════╝ │
│                                                  │
│                         [Anuluj]  [Zapisz]       │
└──────────────────────────────────────────────────┘
```

### Kolorystyka tagów (przykłady)

| Tag | Kolor | Emoji | Użycie |
|-----|-------|-------|--------|
| Klient | `#2196F3` | 💼 | Rozmowy biznesowe |
| Personal | `#4CAF50` | 👤 | Rozmowy prywatne |
| Support | `#FF9800` | 🆘 | Pomoc techniczna |
| Meeting | `#9C27B0` | 🤝 | Spotkania |
| Important | `#F44336` | ⚠️ | Ważne |
| Follow-up | `#FFEB3B` | 📌 | Do dalszego działania |

---

## 🔌 API i funkcjonalności

### EmailConnector API

```python
class EmailConnector:
    """Uniwersalny connector do kont e-mail"""
    
    def __init__(self, account_config: dict):
        """
        Args:
            account_config: {
                'server_type': 'IMAP' | 'POP3',
                'server_address': str,
                'server_port': int,
                'username': str,
                'password': str,
                'use_ssl': bool
            }
        """
        
    def connect(self) -> bool:
        """Nawiąż połączenie z serwerem"""
        
    def disconnect(self):
        """Zakończ połączenie"""
        
    def test_connection(self) -> tuple[bool, str]:
        """Testuj połączenie. Returns: (success, message)"""
        
    def get_folders(self) -> List[str]:
        """Pobierz listę folderów w skrzynce"""
        
    def search_messages(
        self,
        folder: str = "INBOX",
        search_criteria: dict = None
    ) -> List[dict]:
        """
        Wyszukaj wiadomości spełniające kryteria.
        
        Args:
            folder: Nazwa folderu
            search_criteria: {
                'subject': str,         # Szukaj w temacie
                'from': str,            # Nadawca
                'since': date,          # Od daty
                'before': date,         # Do daty
                'has_attachment': bool  # Czy ma załączniki
            }
            
        Returns:
            Lista wiadomości: [{
                'message_id': str,
                'subject': str,
                'from': str,
                'date': datetime,
                'has_attachments': bool,
                'attachment_count': int
            }]
        """
        
    def download_attachment(
        self,
        message_id: str,
        attachment_name: str,
        save_path: str
    ) -> bool:
        """Pobierz załącznik i zapisz do pliku"""
        
    def download_all_attachments(
        self,
        message_id: str,
        save_dir: str,
        pattern: str = None
    ) -> List[str]:
        """
        Pobierz wszystkie załączniki z wiadomości.
        
        Args:
            message_id: ID wiadomości
            save_dir: Katalog docelowy
            pattern: Regex pattern (opcjonalnie)
            
        Returns:
            Lista ścieżek pobranych plików
        """
```

### TranscriptionService API

```python
class TranscriptionService:
    """Serwis transkrypcji audio → tekst"""
    
    def __init__(self, provider: str = 'whisper'):
        """
        Args:
            provider: 'whisper' | 'local' | 'custom'
        """
        
    def transcribe(
        self,
        audio_path: str,
        language: str = None,
        callback: Callable = None
    ) -> dict:
        """
        Transkrybuj plik audio.
        
        Args:
            audio_path: Ścieżka do pliku
            language: Kod języka (opcjonalnie, auto-detect)
            callback: Funkcja callback(progress: float)
            
        Returns: {
            'text': str,
            'language': str,
            'confidence': float,  # 0.0 - 1.0
            'segments': [{
                'start': float,    # czas w sekundach
                'end': float,
                'text': str
            }],
            'error': str | None
        }
        """
        
    def is_available(self) -> bool:
        """Sprawdź czy serwis jest dostępny"""
```

### AISummaryService API

```python
class AISummaryService:
    """Serwis generowania podsumowań AI"""
    
    def __init__(self, ai_manager):
        """
        Args:
            ai_manager: Instancja AIManager z AI Module
        """
        
    def generate_summary(
        self,
        transcription: str,
        context: dict = None
    ) -> dict:
        """
        Wygeneruj podsumowanie z transkrypcji.
        
        Args:
            transcription: Tekst transkrypcji
            context: {
                'contact_name': str,
                'date': str,
                'duration': int,
                'additional_info': str
            }
            
        Returns: {
            'summary': str,              # Główne podsumowanie
            'key_points': List[str],     # Kluczowe punkty
            'action_items': [{           # Akcje do wykonania
                'action': str,
                'priority': 'high'|'medium'|'low',
                'due_date': str | None
            }],
            'sentiment': str,            # 'positive'|'neutral'|'negative'
            'topics': List[str],         # Wykryte tematy
            'error': str | None
        }
        """
        
    def extract_action_items(self, transcription: str) -> List[dict]:
        """Wyodrębnij tylko action items"""
        
    def detect_topics(self, transcription: str) -> List[str]:
        """Wykryj tematy rozmowy"""
```

---

## 📦 Zależności i biblioteki

### Nowe zależności Python

**requirements_callcryptor.txt:**

```txt
# ==================== EMAIL ====================
# IMAP/POP3 support
imapclient>=2.3.1
pyzmail36>=1.0.5

# Email parsing
email-validator>=2.1.0
python-dateutil>=2.8.2

# ==================== AUDIO ====================
# Audio metadata
mutagen>=1.47.0  # MP3, WAV, M4A metadata

# Audio processing (opcjonalnie)
pydub>=0.25.1  # Konwersja formatów

# ==================== TRANSKRYPCJA ====================
# OpenAI Whisper (lokalna opcja)
openai-whisper>=20231117

# LUB Whisper API (przez OpenAI)
openai>=1.0.0

# Speech recognition (alternatywa)
SpeechRecognition>=3.10.0

# ==================== BEZPIECZEŃSTWO ====================
# Encryption dla haseł
keyring>=24.0.0
cryptography>=41.0.0

# ==================== UTILITIES ====================
# Progress bars
tqdm>=4.66.0

# File type detection
python-magic>=0.4.27  # Linux/Mac
python-magic-bin>=0.4.14  # Windows

# Hashing
hashlib  # built-in

# ==================== NETWORKING ====================
# Requests (dla API calls)
requests>=2.31.0

# WebSocket (dla real-time updates)
websocket-client>=1.6.0
```

### Struktura plików modułu

```
src/Modules/CallCryptor_module/
├── __init__.py
├── callcryptor_manager.py          # Główna logika biznesowa
├── callcryptor_database.py         # Operacje bazodanowe
├── callcryptor_sync_manager.py     # Synchronizacja
├── callcryptor_api_client.py       # REST API client
├── email_connector.py              # Email helper
├── source_scanner.py               # Skanowanie źródeł
├── transcription_service.py        # Transkrypcja
├── ai_summary_service.py           # Podsumowania AI
├── models.py                       # Data models
└── utils.py                        # Funkcje pomocnicze

src/ui/
├── callcryptor_view.py             # Główny widok
├── callcryptor_dialogs.py          # Dialogi
├── email_settings_card.py          # Karta ustawień email
└── callcryptor_widgets.py          # Niestandardowe widgety

src/database/
└── callcryptor.db                  # Lokalna baza SQLite

resources/
└── i18n/
    ├── pl.json                     # Tłumaczenia PL
    ├── en.json                     # Tłumaczenia EN
    └── de.json                     # Tłumaczenia DE
```

---

## 🎯 Kryteria akceptacji

### Moduł gotowy do użycia jeśli:

- [ ] Użytkownik może dodać konto e-mail
- [ ] Użytkownik może dodać źródło (folder/email)
- [ ] Skanowanie źródeł znajduje nagrania
- [ ] Tabela wyświetla listę nagrań
- [ ] Transkrypcja działa (lokalnie lub przez API)
- [ ] AI generuje sensowne podsumowania
- [ ] Można utworzyć notatkę z transkrypcji
- [ ] Można utworzyć zadanie z action items
- [ ] System tagów działa
- [ ] Archiwizacja działa
- [ ] Synchronizacja z serwerem działa
- [ ] Voice assistant reaguje na komendy
- [ ] UI reaguje na zmiany motywu i języka
- [ ] Wszystko działa offline (local-first)
- [ ] Nie ma memory leaks
- [ ] Nie ma krytycznych bugów

---

## 📝 Notatki implementacyjne

### Bezpieczeństwo haseł e-mail

**Używamy keyring:**

```python
import keyring

# Zapisz hasło
keyring.set_password(
    "PRO-Ka-Po_CallCryptor",
    account_id,  # Unique identifier
    password
)

# Pobierz hasło
password = keyring.get_password(
    "PRO-Ka-Po_CallCryptor",
    account_id
)

# Usuń hasło
keyring.delete_password(
    "PRO-Ka-Po_CallCryptor",
    account_id
)
```

### Deduplication nagrań

Używamy hashowania plików:

```python
import hashlib

def calculate_file_hash(file_path: str, algorithm: str = 'md5') -> str:
    """Oblicz hash pliku dla deduplication"""
    hash_func = hashlib.new(algorithm)
    
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(4096), b''):
            hash_func.update(chunk)
    
    return hash_func.hexdigest()
```

### Optymalizacja wydajności

1. **Lazy loading** - ładuj transkrypcje tylko na żądanie
2. **Cache** - przechowuj często używane dane
3. **Background workers** - długie operacje w wątkach
4. **Batch operations** - grupuj operacje DB
5. **Indeksy** - optymalizacja zapytań SQL

---

## 🔄 Roadmap przyszłych ulepszeń

### Wersja 1.1
- [ ] Eksport do różnych formatów (CSV, JSON, PDF)
- [ ] Zaawansowane filtry i wyszukiwanie
- [ ] Statystyki i wykresy
- [ ] Automatyczne tagowanie AI

### Wersja 1.2
- [ ] Nagrywanie bezpośrednio z aplikacji
- [ ] Integracja z VoIP (SIP, Skype)
- [ ] Real-time transcription
- [ ] Speaker diarization (rozpoznawanie mówców)

### Wersja 2.0
- [ ] Mobile app (Android/iOS)
- [ ] Cloud storage dla nagrań
- [ ] Team collaboration
- [ ] Advanced analytics

---

## 📞 Kontakt i wsparcie

**Dokumentacja:** `docs/CALLCRYPTOR_MODULE_PLAN.md`  
**Issues:** GitHub Issues  
**Wiki:** GitHub Wiki (w przygotowaniu)

---

**Ostatnia aktualizacja:** 8 listopada 2025  
**Wersja dokumentu:** 1.0  
**Status:** ✅ Gotowy do implementacji
