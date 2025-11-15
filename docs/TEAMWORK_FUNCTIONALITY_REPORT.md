# TeamWork Module - Raport Funkcjonalności i Implementacji

**Data utworzenia:** 2025-11-13  
**Moduł:** TeamWork - Współpraca zespołowa i zarządzanie projektami  
**Status:** Layout poprawiony, funkcjonalność do implementacji

---

## 1. PODSUMOWANIE WYKONAWCZE

### 1.1 Status Integracji
✅ **UKOŃCZONE:**
- Przycisk TeamWork dodany do `navigation_bar.py` i `config_view.py`
- Tłumaczenia w `pl.json`, `en.json`, `de.json`
- Moduł `teamwork_module.py` zrefaktoryzowany (QWidget, i18n, theme_manager)
- Integracja w `main_window.py` (import, inicjalizacja, view switching)
- Naprawione importy (absolute → relative)
- **Layout poprawiony** (marginy toolbar: 10px/8px, splitter: 25%/75%, spacing: 8px)

⏳ **DO IMPLEMENTACJI:**
- Pełna funkcjonalność frontendu (dialogi, zarządzanie danymi)
- Backend PostgreSQL (modele, router, schemas)
- Sync manager (local SQLite ↔ API)
- Integracja z systemem autoryzacji

---

## 2. ARCHITEKTURA SCHEMATU BAZY DANYCH

### 2.1 Tabele (SQLite → PostgreSQL)

#### **USERS** - Użytkownicy systemu
```sql
CREATE TABLE users (
    user_id SERIAL PRIMARY KEY,           -- INTEGER AUTOINCREMENT → SERIAL
    email VARCHAR(255) UNIQUE NOT NULL,
    first_name VARCHAR(100),
    last_name VARCHAR(100),
    created_at TIMESTAMP DEFAULT NOW(),   -- DATETIME → TIMESTAMP
    is_active BOOLEAN DEFAULT TRUE
);
```

#### **TEAMS** - Zespoły (zdefiniowane grupy kontaktów)
```sql
CREATE TABLE teams (
    team_id SERIAL PRIMARY KEY,
    team_name VARCHAR(200) NOT NULL,
    description TEXT,
    created_by INTEGER REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW()
);
```

#### **TEAM_MEMBERS** - Członkowie zespołów
```sql
CREATE TABLE team_members (
    team_member_id SERIAL PRIMARY KEY,
    team_id INTEGER NOT NULL REFERENCES teams(team_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    added_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(team_id, user_id)
);
```

#### **WORK_GROUPS** - Grupy robocze (przestrzenie współpracy)
```sql
CREATE TABLE work_groups (
    group_id SERIAL PRIMARY KEY,
    group_name VARCHAR(200) NOT NULL,
    description TEXT,
    team_id INTEGER REFERENCES teams(team_id),  -- opcjonalne powiązanie
    created_by INTEGER NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

#### **GROUP_MEMBERS** - Członkowie grup roboczych
```sql
CREATE TABLE group_members (
    group_member_id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES work_groups(group_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id) ON DELETE CASCADE,
    role VARCHAR(50) DEFAULT 'member',  -- member, admin, owner
    joined_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(group_id, user_id)
);
```

#### **GROUP_INVITATIONS** - Zaproszenia do grup
```sql
CREATE TABLE group_invitations (
    invitation_id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES work_groups(group_id) ON DELETE CASCADE,
    invited_email VARCHAR(255) NOT NULL,
    invited_by INTEGER NOT NULL REFERENCES users(user_id),
    invitation_status VARCHAR(20) DEFAULT 'pending',  -- pending, accepted, rejected, cancelled
    invited_at TIMESTAMP DEFAULT NOW(),
    responded_at TIMESTAMP
);
```

#### **TOPICS** - Wątki tematyczne w ramach grupy
```sql
CREATE TABLE topics (
    topic_id SERIAL PRIMARY KEY,
    group_id INTEGER NOT NULL REFERENCES work_groups(group_id) ON DELETE CASCADE,
    topic_name VARCHAR(300) NOT NULL,
    created_by INTEGER NOT NULL REFERENCES users(user_id),
    created_at TIMESTAMP DEFAULT NOW(),
    is_active BOOLEAN DEFAULT TRUE
);
```

#### **MESSAGES** - Wiadomości w wątkach
```sql
CREATE TABLE messages (
    message_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(user_id),
    content TEXT NOT NULL,
    background_color VARCHAR(7) DEFAULT '#FFFFFF',  -- hex color
    is_important BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    edited_at TIMESTAMP
);
```

#### **TOPIC_FILES** - Pliki w wątkach
```sql
CREATE TABLE topic_files (
    file_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    file_name VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size INTEGER,  -- bajty
    uploaded_by INTEGER NOT NULL REFERENCES users(user_id),
    uploaded_at TIMESTAMP DEFAULT NOW(),
    is_important BOOLEAN DEFAULT FALSE
);
```

#### **TOPIC_LINKS** - Linki w wątkach
```sql
CREATE TABLE topic_links (
    link_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    url VARCHAR(2000) NOT NULL,
    title VARCHAR(500),
    description TEXT,
    added_by INTEGER NOT NULL REFERENCES users(user_id),
    added_at TIMESTAMP DEFAULT NOW(),
    is_important BOOLEAN DEFAULT FALSE
);
```

#### **TASKS** - Zadania w wątkach
```sql
CREATE TABLE tasks (
    task_id SERIAL PRIMARY KEY,
    topic_id INTEGER NOT NULL REFERENCES topics(topic_id) ON DELETE CASCADE,
    task_subject VARCHAR(500) NOT NULL,
    task_description TEXT,
    assigned_to INTEGER REFERENCES users(user_id),
    created_by INTEGER NOT NULL REFERENCES users(user_id),
    due_date DATE,
    created_at TIMESTAMP DEFAULT NOW(),
    completed BOOLEAN DEFAULT FALSE,
    completed_by INTEGER REFERENCES users(user_id),
    completed_at TIMESTAMP,
    is_important BOOLEAN DEFAULT FALSE
);
```

### 2.2 Indeksy (wydajność)
```sql
-- Team members
CREATE INDEX idx_team_members_team ON team_members(team_id);
CREATE INDEX idx_team_members_user ON team_members(user_id);

-- Group members
CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_user ON group_members(user_id);

-- Invitations
CREATE INDEX idx_group_invitations_email ON group_invitations(invited_email);
CREATE INDEX idx_group_invitations_status ON group_invitations(invitation_status);

-- Topics
CREATE INDEX idx_topics_group ON topics(group_id);

-- Messages
CREATE INDEX idx_messages_topic ON messages(topic_id);
CREATE INDEX idx_messages_important ON messages(is_important);

-- Files
CREATE INDEX idx_topic_files_topic ON topic_files(topic_id);
CREATE INDEX idx_topic_files_important ON topic_files(is_important);

-- Links
CREATE INDEX idx_topic_links_topic ON topic_links(topic_id);
CREATE INDEX idx_topic_links_important ON topic_links(is_important);

-- Tasks
CREATE INDEX idx_tasks_topic ON tasks(topic_id);
CREATE INDEX idx_tasks_assigned ON tasks(assigned_to);
CREATE INDEX idx_tasks_important ON tasks(is_important);
CREATE INDEX idx_tasks_completed ON tasks(completed);
```

---

## 3. ANALIZA FUNKCJONALNOŚCI

### 3.1 Zarządzanie Zespołami (Teams Management)

**Lokalizacja:**
- Frontend: `team_management_dialog.py`
- Backend: `Render_upload/app/teamwork_router.py` (endpoint `/teams`)
- Models: `Render_upload/app/teamwork_models.py` (Team, TeamMember)

**Funkcje do zaimplementowania:**

1. **Tworzenie zespołu**
   - Formularz: nazwa, opis
   - Dodawanie członków (wyszukiwanie po email)
   - Zapis do bazy: `teams` + `team_members`
   - Endpoint: `POST /api/teams`

2. **Przeglądanie zespołów**
   - Lista wszystkich zespołów użytkownika
   - Wyświetlanie członków każdego zespołu
   - Endpoint: `GET /api/teams`

3. **Edycja zespołu**
   - Zmiana nazwy/opisu
   - Dodawanie/usuwanie członków
   - Endpoint: `PUT /api/teams/{team_id}`, `POST /api/teams/{team_id}/members`, `DELETE /api/teams/{team_id}/members/{user_id}`

4. **Usuwanie zespołu**
   - Soft delete (is_active = false) lub hard delete
   - Endpoint: `DELETE /api/teams/{team_id}`

**Status:** ⚠️ Dialog istnieje, ale wymaga implementacji logiki zapisu/odczytu z bazy

---

### 3.2 Zarządzanie Grupami Roboczymi (Work Groups)

**Lokalizacja:**
- Frontend: `dialogs.py` (CreateGroupDialog, MyGroupsDialog)
- Backend: `Render_upload/app/teamwork_router.py` (endpoint `/groups`)
- Models: `Render_upload/app/teamwork_models.py` (WorkGroup, GroupMember)

**Funkcje do zaimplementowania:**

1. **Tworzenie grupy** ✅ Dialog gotowy
   - Formularz: nazwa, opis
   - Wybór zespołów jako źródła członków
   - Dodawanie dodatkowych członków (email)
   - Zapis: `work_groups` + `group_members`
   - Endpoint: `POST /api/groups`

2. **Przeglądanie grup**
   - Lista grup użytkownika (jako członek/owner)
   - Wyświetlanie w drzewie (GroupTreePanel)
   - Endpoint: `GET /api/groups`

3. **Edycja grupy**
   - Zmiana nazwy/opisu
   - Zarządzanie członkami (dodaj/usuń, zmiana roli: member/admin/owner)
   - Endpoint: `PUT /api/groups/{group_id}`, `POST /api/groups/{group_id}/members`

4. **Usuwanie grupy**
   - Tylko owner może usunąć
   - Endpoint: `DELETE /api/groups/{group_id}`

**Status:** ⚠️ CreateGroupDialog działa, wymaga połączenia z API

---

### 3.3 Zaproszenia (Invitations)

**Lokalizacja:**
- Frontend: `dialogs.py` (InvitationsDialog)
- Backend: `Render_upload/app/teamwork_router.py` (endpoint `/invitations`)
- Models: `Render_upload/app/teamwork_models.py` (GroupInvitation)

**Funkcje do zaimplementowania:**

1. **Wysyłanie zaproszenia**
   - Z poziomu CreateGroupDialog (podczas tworzenia grupy)
   - Email do nowego użytkownika
   - Status: pending
   - Endpoint: `POST /api/invitations`

2. **Przeglądanie zaproszeń**
   - Lista zaproszeń wysłanych (przez użytkownika)
   - Lista zaproszeń otrzymanych (do zaakceptowania)
   - Endpoint: `GET /api/invitations?type=sent`, `GET /api/invitations?type=received`

3. **Akceptacja/odrzucenie zaproszenia**
   - Zmiana statusu: accepted/rejected
   - Dodanie do group_members przy akceptacji
   - Endpoint: `PUT /api/invitations/{invitation_id}/accept`, `PUT /api/invitations/{invitation_id}/reject`

4. **Anulowanie zaproszenia**
   - Tylko nadawca może anulować
   - Status: cancelled
   - Endpoint: `DELETE /api/invitations/{invitation_id}`

**Status:** ⚠️ Dialog podstawowy, wymaga pełnej implementacji

---

### 3.4 Wątki Tematyczne (Topics)

**Lokalizacja:**
- Frontend: `dialogs.py` (CreateTopicDialog), `group_tree_panel.py`, `conversation_panel.py`
- Backend: `Render_upload/app/teamwork_router.py` (endpoint `/topics`)
- Models: `Render_upload/app/teamwork_models.py` (Topic)

**Funkcje do zaimplementowania:**

1. **Tworzenie wątku** ✅ Dialog gotowy
   - Formularz: nazwa wątku, grupa nadrzędna
   - Pierwsza wiadomość (opcjonalna)
   - Załączanie plików i linków od razu
   - Zapis: `topics` + `messages` (pierwsza) + `topic_files` + `topic_links`
   - Endpoint: `POST /api/topics`

2. **Przeglądanie wątków**
   - Lista wątków w grupie (drzewo)
   - Wyświetlanie metadanych (właściciel, data utworzenia, liczba wiadomości)
   - Endpoint: `GET /api/groups/{group_id}/topics`

3. **Edycja wątku**
   - Zmiana nazwy
   - Archiwizacja (is_active = false)
   - Endpoint: `PUT /api/topics/{topic_id}`

4. **Usuwanie wątku**
   - Soft delete lub hard delete (CASCADE usuwa messages, files, links, tasks)
   - Endpoint: `DELETE /api/topics/{topic_id}`

**Status:** ⚠️ CreateTopicDialog działa, wymaga integracji z API

---

### 3.5 Konwersacje (Messages)

**Lokalizacja:**
- Frontend: `conversation_panel.py`, `dialogs.py` (ReplyDialog)
- Backend: `Render_upload/app/teamwork_router.py` (endpoint `/messages`)
- Models: `Render_upload/app/teamwork_models.py` (Message)

**Funkcje do zaimplementowania:**

1. **Wyświetlanie wiadomości**
   - Lista wiadomości w wątku (chronologicznie)
   - Wyświetlanie autora, daty, treści
   - Kolor tła (background_color)
   - Oznaczenie ważnych (is_important = ⭐)
   - Endpoint: `GET /api/topics/{topic_id}/messages`

2. **Dodawanie wiadomości** ✅ ReplyDialog gotowy
   - Formularz: treść, kolor tła (opcjonalny)
   - Oznaczanie jako ważne
   - Zapis: `messages`
   - Endpoint: `POST /api/topics/{topic_id}/messages`

3. **Edycja wiadomości**
   - Tylko autor może edytować
   - Zmiana treści (edited_at = NOW())
   - Endpoint: `PUT /api/messages/{message_id}`

4. **Usuwanie wiadomości**
   - Soft delete lub hard delete
   - Endpoint: `DELETE /api/messages/{message_id}`

5. **Toggle ważne**
   - Zmiana is_important (True/False)
   - Endpoint: `PATCH /api/messages/{message_id}/important`

**Status:** ⚠️ ConversationPanel wyświetla dane z SAMPLE_GROUPS, wymaga połączenia z API

---

### 3.6 Pliki (Files)

**Lokalizacja:**
- Frontend: `conversation_panel.py` (display_topic_files)
- Backend: `Render_upload/app/teamwork_router.py` (endpoint `/files`)
- Models: `Render_upload/app/teamwork_models.py` (TopicFile)

**Funkcje do zaimplementowania:**

1. **Upload pliku**
   - Z poziomu CreateTopicDialog lub osobny przycisk w ConversationPanel
   - Zapis pliku na serwerze (folder uploads/ lub cloud storage)
   - Metadane: file_name, file_path, file_size, uploaded_by
   - Endpoint: `POST /api/topics/{topic_id}/files` (multipart/form-data)

2. **Przeglądanie plików**
   - Lista plików w wątku
   - Wyświetlanie nazwy, rozmiaru, autora, daty
   - Oznaczenie ważnych (⭐)
   - Endpoint: `GET /api/topics/{topic_id}/files`

3. **Pobieranie pliku**
   - Download przez kliknięcie
   - Endpoint: `GET /api/files/{file_id}/download`

4. **Usuwanie pliku**
   - Usunięcie z serwera i bazy
   - Endpoint: `DELETE /api/files/{file_id}`

5. **Toggle ważne**
   - Zmiana is_important
   - Endpoint: `PATCH /api/files/{file_id}/important`

**Status:** ⚠️ UI gotowe, wymaga implementacji upload/download

---

### 3.7 Linki (Links)

**Lokalizacja:**
- Frontend: `conversation_panel.py` (display_topic_links)
- Backend: `Render_upload/app/teamwork_router.py` (endpoint `/links`)
- Models: `Render_upload/app/teamwork_models.py` (TopicLink)

**Funkcje do zaimplementowania:**

1. **Dodawanie linku**
   - Formularz: URL, tytuł (opcjonalny), opis (opcjonalny)
   - Walidacja URL
   - Zapis: `topic_links`
   - Endpoint: `POST /api/topics/{topic_id}/links`

2. **Przeglądanie linków**
   - Lista linków w wątku
   - Wyświetlanie jako klikalne przyciski
   - Oznaczenie ważnych (⭐)
   - Endpoint: `GET /api/topics/{topic_id}/links`

3. **Edycja linku**
   - Zmiana tytułu/opisu/URL
   - Endpoint: `PUT /api/links/{link_id}`

4. **Usuwanie linku**
   - Endpoint: `DELETE /api/links/{link_id}`

5. **Toggle ważne**
   - Zmiana is_important
   - Endpoint: `PATCH /api/links/{link_id}/important`

**Status:** ⚠️ UI gotowe, wymaga implementacji CRUD

---

### 3.8 Zadania (Tasks)

**Lokalizacja:**
- Frontend: `task_dialog.py` (TaskDialog), `task_widgets.py` (GanttChartWidget), `conversation_panel.py`
- Backend: `Render_upload/app/teamwork_router.py` (endpoint `/tasks`)
- Models: `Render_upload/app/teamwork_models.py` (Task)

**Funkcje do zaimplementowania:**

1. **Tworzenie zadania** ✅ TaskDialog gotowy
   - Formularz: temat, opis, przypisanie (assigned_to), termin (due_date)
   - Oznaczanie jako ważne
   - Zapis: `tasks`
   - Endpoint: `POST /api/topics/{topic_id}/tasks`

2. **Przeglądanie zadań**
   - Lista zadań w wątku
   - Filtry: wszystkie / aktywne / ukończone / przypisane do mnie
   - Wyświetlanie statusu (completed), deadline, assignee
   - Endpoint: `GET /api/topics/{topic_id}/tasks`

3. **Edycja zadania**
   - Zmiana tematu/opisu/deadline/assignee
   - Endpoint: `PUT /api/tasks/{task_id}`

4. **Oznaczanie jako ukończone**
   - Zmiana completed = True, completed_by, completed_at
   - Endpoint: `PATCH /api/tasks/{task_id}/complete`

5. **Widok Gantt** ✅ GanttChartWidget istnieje
   - Wyświetlanie zadań na osi czasu
   - Filtry: grupa, wątek, przypisany użytkownik
   - Endpoint: `GET /api/groups/{group_id}/tasks?view=gantt`

6. **Usuwanie zadania**
   - Endpoint: `DELETE /api/tasks/{task_id}`

**Status:** ⚠️ Dialog i widget Gantt gotowe, wymaga połączenia z API

---

## 4. PLAN IMPLEMENTACJI BACKEND

### 4.1 Struktura Plików

```
Render_upload/app/
├── teamwork_models.py       # SQLAlchemy models (11 tabel)
├── teamwork_schemas.py      # Pydantic schemas (request/response)
├── teamwork_router.py       # FastAPI router z endpointami
└── main.py                  # Rejestracja routera
```

### 4.2 Modele SQLAlchemy (teamwork_models.py)

**Lista modeli do utworzenia:**
1. `User` - już istnieje w `auth.py`, użyć istniejący
2. `Team` - zespoły
3. `TeamMember` - relacja many-to-many (team ↔ user)
4. `WorkGroup` - grupy robocze
5. `GroupMember` - relacja many-to-many (group ↔ user) + rola
6. `GroupInvitation` - zaproszenia
7. `Topic` - wątki tematyczne
8. `Message` - wiadomości
9. `TopicFile` - pliki
10. `TopicLink` - linki
11. `Task` - zadania

**Relacje:**
- `Team` ← one-to-many → `TeamMember` → many-to-one → `User`
- `WorkGroup` ← one-to-many → `GroupMember` → many-to-one → `User`
- `WorkGroup` ← one-to-many → `Topic` ← one-to-many → `Message`, `TopicFile`, `TopicLink`, `Task`

### 4.3 Schematy Pydantic (teamwork_schemas.py)

**Dla każdej tabeli utworzyć:**
- `{Entity}Base` - wspólne pola
- `{Entity}Create` - pola wymagane przy tworzeniu
- `{Entity}Update` - pola opcjonalne przy aktualizacji
- `{Entity}Response` - pełny obiekt z ID i metadanymi

**Przykład:**
```python
class TeamBase(BaseModel):
    team_name: str
    description: Optional[str] = None

class TeamCreate(TeamBase):
    pass

class TeamUpdate(BaseModel):
    team_name: Optional[str] = None
    description: Optional[str] = None

class TeamResponse(TeamBase):
    team_id: int
    created_by: int
    created_at: datetime
    
    class Config:
        from_attributes = True
```

### 4.4 Router (teamwork_router.py)

**Grupy endpointów:**

1. **Teams** (`/api/teams`)
   - `POST /` - create_team
   - `GET /` - get_user_teams
   - `GET /{team_id}` - get_team
   - `PUT /{team_id}` - update_team
   - `DELETE /{team_id}` - delete_team
   - `POST /{team_id}/members` - add_team_member
   - `DELETE /{team_id}/members/{user_id}` - remove_team_member

2. **Groups** (`/api/groups`)
   - `POST /` - create_group
   - `GET /` - get_user_groups
   - `GET /{group_id}` - get_group
   - `PUT /{group_id}` - update_group
   - `DELETE /{group_id}` - delete_group
   - `POST /{group_id}/members` - add_group_member
   - `PUT /{group_id}/members/{user_id}` - update_member_role
   - `DELETE /{group_id}/members/{user_id}` - remove_group_member

3. **Invitations** (`/api/invitations`)
   - `POST /` - create_invitation
   - `GET /` - get_invitations (query param: type=sent|received)
   - `PUT /{invitation_id}/accept` - accept_invitation
   - `PUT /{invitation_id}/reject` - reject_invitation
   - `DELETE /{invitation_id}` - cancel_invitation

4. **Topics** (`/api/topics`)
   - `POST /` - create_topic
   - `GET /groups/{group_id}/topics` - get_group_topics
   - `GET /{topic_id}` - get_topic
   - `PUT /{topic_id}` - update_topic
   - `DELETE /{topic_id}` - delete_topic

5. **Messages** (`/api/messages`)
   - `POST /topics/{topic_id}/messages` - create_message
   - `GET /topics/{topic_id}/messages` - get_topic_messages
   - `PUT /{message_id}` - update_message
   - `DELETE /{message_id}` - delete_message
   - `PATCH /{message_id}/important` - toggle_important

6. **Files** (`/api/files`)
   - `POST /topics/{topic_id}/files` - upload_file
   - `GET /topics/{topic_id}/files` - get_topic_files
   - `GET /{file_id}/download` - download_file
   - `DELETE /{file_id}` - delete_file
   - `PATCH /{file_id}/important` - toggle_important

7. **Links** (`/api/links`)
   - `POST /topics/{topic_id}/links` - create_link
   - `GET /topics/{topic_id}/links` - get_topic_links
   - `PUT /{link_id}` - update_link
   - `DELETE /{link_id}` - delete_link
   - `PATCH /{link_id}/important` - toggle_important

8. **Tasks** (`/api/tasks`)
   - `POST /topics/{topic_id}/tasks` - create_task
   - `GET /topics/{topic_id}/tasks` - get_topic_tasks
   - `GET /groups/{group_id}/tasks` - get_group_tasks (dla Gantt)
   - `PUT /{task_id}` - update_task
   - `PATCH /{task_id}/complete` - mark_task_complete
   - `DELETE /{task_id}` - delete_task

**Autentykacja:** Wszystkie endpointy wymagają `current_user: User = Depends(get_current_user)`

---

## 5. PLAN IMPLEMENTACJI SYNC MANAGER

### 5.1 Architektura Synchronizacji

**Lokalizacja:** `src/Modules/custom_modules/TeamWork/sync_manager.py`

**Strategia:**
- **Local-first:** Dane przechowywane lokalnie w SQLite
- **Periodic sync:** Synchronizacja co X minut lub przy akcji użytkownika
- **Conflict resolution:** Last-write-wins lub merge strategy

### 5.2 Funkcje Sync Managera

1. **Inicjalizacja połączenia**
   - Pobranie tokena z auth_manager
   - Konfiguracja API URL z config.py

2. **Push (local → API)**
   - Znalezienie nowych/zmienionych rekordów (timestamp)
   - Wysłanie do API (POST/PUT)
   - Aktualizacja local record z remote ID

3. **Pull (API → local)**
   - Pobranie wszystkich danych użytkownika
   - Merge z lokalnymi danymi
   - Rozwiązywanie konfliktów

4. **Auto-sync**
   - Timer co 5 minut (konfigurowalne)
   - Sync przy starcie aplikacji
   - Sync przed zamknięciem aplikacji

### 5.3 Tabele Pomocnicze

**sync_status** - śledzenie stanu synchronizacji
```sql
CREATE TABLE sync_status (
    id INTEGER PRIMARY KEY,
    entity_type VARCHAR(50),  -- teams, groups, topics, messages, etc.
    entity_id INTEGER,
    local_id INTEGER,
    remote_id INTEGER,
    last_synced TIMESTAMP,
    sync_direction VARCHAR(10),  -- up, down, both
    conflict BOOLEAN DEFAULT FALSE
);
```

---

## 6. PRIORYTETY IMPLEMENTACJI

### Faza 1: Backend Foundation (Priorytet: WYSOKI)
1. ✅ Konwersja `database_schema.sql` → PostgreSQL
2. ✅ Utworzenie `teamwork_models.py` (wszystkie 11 modeli)
3. ✅ Utworzenie `teamwork_schemas.py` (Base/Create/Update/Response dla każdej tabeli)
4. ✅ Migracja Alembic (dodanie tabel do bazy Render)

### Faza 2: API Endpoints (Priorytet: WYSOKI)
1. ✅ Router: Teams (7 endpointów)
2. ✅ Router: Groups (8 endpointów)
3. ✅ Router: Topics (5 endpointów)
4. ✅ Router: Messages (5 endpointów)
5. ✅ Rejestracja routera w `main.py`

### Faza 3: Frontend Integration (Priorytet: ŚREDNI)
1. ✅ `db_manager.py` - lokalny SQLite manager
2. ✅ Połączenie CreateGroupDialog z API
3. ✅ Połączenie CreateTopicDialog z API
4. ✅ Połączenie ConversationPanel z API (wyświetlanie/dodawanie wiadomości)
5. ✅ Połączenie TaskDialog z API

### Faza 4: File & Link Management (Priorytet: ŚREDNI)
1. ✅ Router: Files (5 endpointów + upload/download)
2. ✅ Router: Links (5 endpointów)
3. ✅ Frontend: Upload UI
4. ✅ Frontend: Link management UI

### Faza 5: Tasks & Gantt (Priorytet: ŚREDNI)
1. ✅ Router: Tasks (6 endpointów)
2. ✅ Frontend: Połączenie TaskDialog
3. ✅ Frontend: Gantt view z API data

### Faza 6: Invitations & Teams (Priorytet: NISKI)
1. ✅ Router: Invitations (5 endpointów)
2. ✅ Email service dla zaproszeń
3. ✅ Frontend: InvitationsDialog
4. ✅ Frontend: TeamManagementDialog

### Faza 7: Synchronization (Priorytet: WYSOKI po Fazie 1-5)
1. ✅ Utworzenie `sync_manager.py`
2. ✅ Implementacja push/pull logic
3. ✅ Auto-sync timer
4. ✅ Conflict resolution UI

### Faza 8: Polish & Testing (Priorytet: NISKI)
1. ✅ Testy jednostkowe (pytest)
2. ✅ Testy integracyjne (API + frontend)
3. ✅ UI/UX improvements
4. ✅ Dokumentacja użytkownika

---

## 7. ZALEŻNOŚCI I UWAGI TECHNICZNE

### 7.1 Wymagane Biblioteki
```txt
# Backend (requirements.txt w Render_upload/)
fastapi
sqlalchemy
psycopg2-binary
pydantic
python-multipart  # dla upload plików

# Frontend (requirements.txt główny)
PyQt6
loguru
requests  # dla API calls
```

### 7.2 Konfiguracja

**Render_upload/app/config.py:**
```python
UPLOAD_DIR = "uploads/teamwork"  # folder na pliki
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
ALLOWED_EXTENSIONS = {".pdf", ".docx", ".xlsx", ".jpg", ".png", ".zip"}
```

**src/config.py:**
```python
TEAMWORK_SYNC_INTERVAL = 300  # 5 minut (seconds)
TEAMWORK_API_ENDPOINT = f"{API_BASE_URL}/api"
```

### 7.3 Autoryzacja

- Wszystkie endpointy wymagają `Authorization: Bearer {token}`
- Token pobierany z `auth_manager.get_current_token()`
- User ID z `current_user.id` (z JWT)

### 7.4 Migracje

**Utworzyć migrację Alembic:**
```bash
cd Render_upload
alembic revision --autogenerate -m "Add TeamWork tables"
alembic upgrade head
```

---

## 8. METRYKI SUKCESU

### 8.1 Backend
✅ Wszystkie 11 tabel utworzone w PostgreSQL  
✅ Wszystkie endpointy (47 total) działają poprawnie  
✅ Autoryzacja działa (tylko członkowie grup widzą dane)  
✅ Upload/download plików działa  

### 8.2 Frontend
✅ Wszystkie dialogi zapisują dane do API  
✅ ConversationPanel wyświetla dane z API  
✅ Synchronizacja działa automatycznie  
✅ Widok Gantt wyświetla zadania  

### 8.3 Wydajność
✅ API response time < 500ms dla podstawowych operacji  
✅ Sync time < 5s dla 100 wiadomości  
✅ UI responsywne (brak lagów podczas ładowania)  

---

## 9. NASTĘPNE KROKI

### Natychmiastowe (dzisiaj/jutro):
1. **Konwersja schema SQLite → PostgreSQL** (`database_schema.sql` → `teamwork_schema_postgres.sql`)
2. **Utworzenie `teamwork_models.py`** (11 modeli SQLAlchemy)
3. **Utworzenie `teamwork_schemas.py`** (Pydantic schemas)

### Krótkoterminowe (ten tydzień):
4. **Implementacja routera** (Teams, Groups, Topics, Messages)
5. **Migracja Alembic** (dodanie tabel)
6. **Testy API** (Postman/pytest)

### Średnioterminowe (przyszły tydzień):
7. **Frontend integration** (db_manager.py, API calls w dialogach)
8. **File upload/download**
9. **Sync manager** (podstawowa wersja)

### Długoterminowe (2+ tygodnie):
10. **Gantt view integration**
11. **Email notifications** (zaproszenia)
12. **Conflict resolution UI**
13. **Full testing suite**

---

## 10. PYTANIA I DECYZJE DO PODJĘCIA

### 10.1 Architektura
❓ **Soft delete czy hard delete?** (is_deleted flag vs. ON DELETE CASCADE)  
❓ **WebSocket dla real-time updates?** (nowe wiadomości/zadania)  
❓ **Cloud storage dla plików?** (AWS S3, Azure Blob) vs. local storage  

### 10.2 Funkcjonalność
❓ **Powiadomienia push?** (nowe wiadomości, przypisane zadania)  
❓ **Wersjonowanie wiadomości?** (historia edycji)  
❓ **Komentarze do plików/linków?** (jak w Google Drive)  

### 10.3 UI/UX
❓ **Drag & drop upload?** (przeciąganie plików do ConversationPanel)  
❓ **Rich text editor?** (formatowanie wiadomości)  
❓ **Emoji/reactions?** (reakcje na wiadomości)  

---

**Koniec raportu**  
**Autor:** GitHub Copilot  
**Data:** 2025-11-13
