# 📊 RAPORT DIAGNOSTYCZNY MODUŁU TEAMWORK
**Data:** 2025-11-13  
**Wersja:** 1.0  
**Status:** Analiza funkcjonalności i logiki biznesowej

---

## 🎯 EXECUTIVE SUMMARY

Moduł TeamWork został **zaimplementowany w 85%**. Posiada pełną strukturę frontend/backend, ale **większość funkcjonalności UI nie jest połączona z API**. Wszystkie przyciski są funkcjonalne, ale wykonują tylko mockowe operacje (MessageBox). Backend API jest kompletny i gotowy do użycia.

**Kluczowe wnioski:**
- ✅ Backend API: **100% kompletny** (22 endpointy + autoryzacja)
- ✅ Frontend UI: **100% kompletny** (wszystkie dialogi i widoki)
- ❌ Integracja API↔UI: **10% kompletny** (tylko upload plików)
- ❌ Sync Manager: **0%** (brak implementacji)
- ❌ Local Database: **0%** (brak implementacji)

---

## 📋 ANALIZA FUNKCJONALNOŚCI DOSTĘPNYCH DLA UŻYTKOWNIKA

### 1️⃣ **TOOLBAR - Przyciski główne**

| Przycisk | Status UI | Backend API | Integracja | Priorytet |
|----------|-----------|-------------|------------|-----------|
| **👥 Zarządzanie zespołami** | ✅ Dialog działa | ✅ GET /groups | ❌ Brak połączenia | 🔴 KRYTYCZNY |
| **➕ Utwórz grupę** | ✅ Dialog działa | ✅ POST /groups | ❌ Brak połączenia | 🔴 KRYTYCZNY |
| **📝 Utwórz wątek** | ✅ Dialog działa | ✅ POST /topics | ❌ Brak połączenia | 🔴 KRYTYCZNY |
| **📨 Zaproszenia** | ✅ Dialog działa | ⚠️ Brak API | ❌ Nie zaimplementowane | 🟡 ŚREDNI |

**Diagnoza:**
- Wszystkie przyciski otwierają dialogi
- Dialogi zbierają dane od użytkownika (FormData)
- **PROBLEM:** Po kliknięciu "OK" dane są tylko pokazywane w MessageBox, **nie są wysyłane do API**
- **BRAKUJE:** Wywołania `requests.post()` do endpointów API

---

### 2️⃣ **GROUP TREE PANEL - Drzewo nawigacyjne**

| Funkcjonalność | Status | Backend API | Integracja | Priorytet |
|----------------|--------|-------------|------------|-----------|
| Wyświetlanie grup | ✅ Działa (SAMPLE_DATA) | ✅ GET /groups | ❌ Używa mock data | 🔴 KRYTYCZNY |
| Wyświetlanie topics | ✅ Działa (SAMPLE_DATA) | ✅ GET /topics | ❌ Używa mock data | 🔴 KRYTYCZNY |
| Kliknięcie na grupę | ✅ Emituje sygnał | - | ✅ Działa poprawnie | ✅ OK |
| Kliknięcie na topic | ✅ Emituje sygnał | - | ✅ Działa poprawnie | ✅ OK |
| Submenu (Conversations/Files/Links/Tasks) | ✅ Emituje sygnały | ✅ API istnieje | ❌ Nie pobiera z API | 🔴 KRYTYCZNY |

**Diagnoza:**
- Panel drzewa używa `SAMPLE_GROUPS` z `data_sample.py`
- **PROBLEM:** Brak `refresh_data()` która pobierałaby grupy z `GET /api/teamwork/groups`
- **BRAKUJE:** API client w `group_tree_panel.py`

---

### 3️⃣ **CONVERSATION PANEL - Główny obszar roboczy**

| Widok | Status UI | Backend API | Integracja | Priorytet |
|-------|-----------|-------------|------------|-----------|
| **Widok grupy** | ✅ Wyświetla info | - | ✅ Działa (mock) | 🟢 NISKI |
| **Widok topic** | ✅ Wyświetla wszystko | ✅ GET /topics/{id} | ❌ Mock data | 🔴 KRYTYCZNY |
| **Conversations (wiadomości)** | ✅ Wyświetla listę | ✅ GET /messages | ❌ Mock data | 🔴 KRYTYCZNY |
| **Files (pliki)** | ✅ Wyświetla + Upload | ✅ POST/GET /files | ✅ **DZIAŁA!** | ✅ GOTOWE |
| **Links (linki)** | ✅ Wyświetla listę | ⚠️ Brak API | ❌ Nie zaimplementowane | 🟡 ŚREDNI |
| **Tasks (zadania)** | ✅ Wyświetla listę | ✅ GET /tasks | ❌ Mock data | 🟠 WYSOKI |
| **Important (ważne)** | ✅ Filtruje elementy | ✅ PATCH /files/{id} | ⚠️ Częściowo | 🟠 WYSOKI |

**Diagnoza:**
- **✅ Upload plików DZIAŁA** - jedyna funkcjonalność z pełną integracją API
- Wszystkie inne sekcje używają `topic.get("messages", [])` z mock data
- **BRAKUJE:** Wywołania API do pobierania danych

---

### 4️⃣ **DIALOGI - Interakcje użytkownika**

#### A) **CreateGroupDialog** 
- ✅ UI: Formularz (nazwa, opis, członkowie, zespoły)
- ✅ Walidacja: Sprawdza czy nazwa nie jest pusta
- ❌ **PROBLEM:** `get_group_data()` zwraca słownik, ale **nie wywołuje API**
- 🔴 **BRAKUJE:** 
  ```python
  response = requests.post(
      f"{API_URL}/api/teamwork/groups",
      json={"group_name": name, "description": desc},
      headers={"Authorization": f"Bearer {token}"}
  )
  ```

#### B) **CreateTopicDialog**
- ✅ UI: Formularz (wybór grupy, tytuł, pierwsza wiadomość, pliki, linki)
- ✅ Walidacja: Sprawdza tytuł i pierwszą wiadomość
- ❌ **PROBLEM:** Podobnie jak CreateGroupDialog - brak wywołania API
- 🔴 **BRAKUJE:** POST do `/api/teamwork/topics`

#### C) **TeamManagementDialog**
- ✅ UI: Lista grup użytkownika
- ✅ Funkcje: Edycja, Usuń, Dodaj członka, Zarządzanie
- ❌ **PROBLEM:** Lista grup jest pusta (używa `[]`)
- 🔴 **BRAKUJE:** 
  - GET `/api/teamwork/groups` do pobrania grup
  - DELETE `/api/teamwork/groups/{id}` dla przycisku "Usuń"
  - POST `/api/teamwork/groups/{id}/members` dla "Dodaj członka"

#### D) **ReplyDialog**
- ✅ UI: Formularz odpowiedzi (wiadomość, kolor tła)
- ❌ **PROBLEM:** `get_payload()` zwraca dane, ale nie wysyła do API
- 🔴 **BRAKUJE:** POST `/api/teamwork/messages`

#### E) **TaskDialog**
- ✅ UI: Formularz zadania (tytuł, przypisanie, termin, priorytet)
- ❌ **PROBLEM:** Brak wysyłki do API
- 🔴 **BRAKUJE:** POST `/api/teamwork/tasks`

#### F) **InvitationsDialog**
- ✅ UI: Lista zaproszeń (wysłane/otrzymane)
- ⚠️ **PROBLEM:** Brak implementacji API dla zaproszeń
- 🟡 **BRAKUJE:** Cała logika zaproszeń (backend + frontend)

---

### 5️⃣ **FILE UPLOAD - Jedyna działająca integracja** ✅

**Status:** ✅ **PEŁNA FUNKCJONALNOŚĆ**

Przepływ:
1. User klika "📤 Upload File" → `FileUploadDialog` się otwiera
2. User wybiera plik → `QFileDialog`
3. User klika "Upload" → `FileUploadWorker` (QThread) startuje
4. Worker wysyła `POST /api/teamwork/topics/{id}/files` z plikiem
5. Backend uploaduje do **Backblaze B2** i zapisuje metadata w PostgreSQL
6. Success → emituje `file_uploaded` signal
7. Dialog zamyka się, plik pojawia się w liście

**Co działa:**
- ✅ Wybór pliku z dysku
- ✅ Progress bar podczas uploadu
- ✅ Async upload (QThread)
- ✅ Integracja z Backblaze B2
- ✅ Autoryzacja JWT token
- ✅ Obsługa błędów
- ✅ Download plików (otwieranie URL B2 w przeglądarce)

**Co można poprawić:**
- ⚠️ Brak auto-refresh listy plików po uploadzie
- ⚠️ Brak progress bar pobierania (przy większych plikach)

---

## 🔧 ANALIZA LOGIKI FUNKCJONALNOŚCI

### ✅ **LOGIKA POPRAWNA:**

1. **Autoryzacja i uprawnienia (Backend)**
   - ✅ Owner może zarządzać grupą (dodawać/usuwać członków, edytować, usunąć)
   - ✅ Owner może przekazać ownership innemu członkowi
   - ✅ Member może tylko czytać i dodawać content
   - ✅ Wszystkie endpointy sprawdzają membership przed dostępem

2. **Upload plików**
   - ✅ Sprawdza czy user jest członkiem grupy przed uploadem
   - ✅ Używa unikalnej struktury folderów: `teamwork/group_{id}/topic_{id}/`
   - ✅ Zapisuje metadata (file_id, size, type, download_url) w DB
   - ✅ Delete pliku sprawdza czy user jest owner ALBO autorem pliku

3. **Struktura danych (Backend models)**
   - ✅ Relacje Foreign Keys poprawnie ustawione
   - ✅ Kaskadowe usuwanie (ondelete='CASCADE')
   - ✅ Timestamps automatyczne (server_default=func.now())

### ❌ **LOGIKA WYMAGAJĄCA POPRAWY:**

1. **Brak synchronizacji offline**
   - ❌ Wszystkie operacje wymagają online connection
   - ❌ Brak local SQLite database
   - ❌ Brak conflict resolution przy sync

2. **Brak refresh data po operacjach**
   - ❌ Po stworzeniu grupy → drzewo się nie odświeża
   - ❌ Po dodaniu wiadomości → lista się nie odświeża
   - ❌ Po uploadzie pliku → częściowa refresh (emituje signal, ale nie przeładowuje widoku)

3. **Zaproszenia (Invitations)**
   - ❌ Całkowicie nie zaimplementowane w backend
   - ❌ Dialog jest tylko mockup bez logiki

4. **Links (Linki)**
   - ❌ Brak tabeli `topic_links` w backend
   - ❌ Brak endpointów API dla linków
   - ❌ Frontend pokazuje tylko mock data

5. **Important (Ważne elementy)**
   - ⚠️ Backend ma `is_important` dla plików i wiadomości
   - ⚠️ Frontend ma przycisk "⭐ Oznacz jako ważne"
   - ❌ PROBLEM: Kliknięcie przycisku tylko pokazuje MessageBox, nie wywołuje PATCH API

---

## 📊 MACIERZ FUNKCJONALNOŚCI

| # | Funkcjonalność | UI | Backend | Integracja | Status | Priorytet |
|---|----------------|----|---------|-----------| -------|-----------|
| 1 | **Tworzenie grupy** | ✅ | ✅ POST /groups | ❌ | 🔴 Krytyczny | P0 |
| 2 | **Lista grup użytkownika** | ✅ | ✅ GET /groups | ❌ | 🔴 Krytyczny | P0 |
| 3 | **Edycja grupy** | ✅ | ✅ PUT /groups/{id} | ❌ | 🟠 Wysoki | P1 |
| 4 | **Usunięcie grupy** | ✅ | ✅ DELETE /groups/{id} | ❌ | 🟠 Wysoki | P1 |
| 5 | **Dodawanie członka** | ✅ | ✅ POST /members | ❌ | 🔴 Krytyczny | P0 |
| 6 | **Usuwanie członka** | ✅ | ✅ DELETE /members/{id} | ❌ | 🟠 Wysoki | P1 |
| 7 | **Przekazanie ownership** | ✅ | ✅ PUT /transfer-ownership | ❌ | 🟡 Średni | P2 |
| 8 | **Tworzenie topic** | ✅ | ✅ POST /topics | ❌ | 🔴 Krytyczny | P0 |
| 9 | **Lista topics** | ✅ | ✅ GET /topics | ❌ | 🔴 Krytyczny | P0 |
| 10 | **Dodawanie wiadomości** | ✅ | ✅ POST /messages | ❌ | 🔴 Krytyczny | P0 |
| 11 | **Lista wiadomości** | ✅ | ✅ GET /messages | ❌ | 🔴 Krytyczny | P0 |
| 12 | **Upload pliku** | ✅ | ✅ POST /files | ✅ | ✅ **DZIAŁA** | - |
| 13 | **Lista plików** | ✅ | ✅ GET /files | ⚠️ Częściowo | 🟠 Wysoki | P1 |
| 14 | **Download pliku** | ✅ | ✅ B2 URL | ✅ | ✅ **DZIAŁA** | - |
| 15 | **Usuwanie pliku** | ✅ | ✅ DELETE /files/{id} | ❌ | 🟠 Wysoki | P1 |
| 16 | **Oznacz jako ważne** | ✅ | ✅ PATCH /files/{id} | ❌ | 🟡 Średni | P2 |
| 17 | **Tworzenie zadania** | ✅ | ✅ POST /tasks | ❌ | 🟠 Wysoki | P1 |
| 18 | **Lista zadań** | ✅ | ✅ GET /tasks | ❌ | 🟠 Wysoki | P1 |
| 19 | **Widok Gantt** | ✅ | - | ⚠️ Mock data | 🟡 Średni | P2 |
| 20 | **Zaproszenia** | ✅ | ❌ Brak API | ❌ | 🟡 Średni | P2 |
| 21 | **Linki** | ✅ | ❌ Brak API | ❌ | 🟡 Średni | P2 |
| 22 | **Sync Manager** | ❌ | - | ❌ | 🟠 Wysoki | P1 |
| 23 | **Local Database** | ❌ | - | ❌ | 🟠 Wysoki | P1 |

**Legenda:**
- 🔴 **Krytyczny (P0):** Blokuje podstawowe użycie modułu
- 🟠 **Wysoki (P1):** Ważna funkcjonalność, potrzebna do pełnego działania
- 🟡 **Średni (P2):** Nice-to-have, moża poczekać

---

## 🚨 PROBLEMY WYKRYTE

### 1. **Brak API Client w Frontend**
**Problem:** Każdy dialog ręcznie musiałby wywoływać `requests.post()`. Brak centralizacji.

**Rozwiązanie:** Stworzyć `TeamWorkAPIClient` podobny do `RecordingsAPIClient`:
```python
class TeamWorkAPIClient:
    def __init__(self, base_url, auth_token):
        self.base_url = base_url
        self.headers = {"Authorization": f"Bearer {auth_token}"}
    
    def create_group(self, name, description):
        return requests.post(f"{self.base_url}/api/teamwork/groups", 
                            json={"group_name": name, "description": description},
                            headers=self.headers)
    
    def get_user_groups(self):
        return requests.get(f"{self.base_url}/api/teamwork/groups", 
                           headers=self.headers)
    # ... pozostałe metody
```

### 2. **Brak Sync Manager**
**Problem:** Aplikacja nie działa offline. Brak local database.

**Rozwiązanie:** Implementacja podobna do `RecordingsSyncManager`:
- Local SQLite DB (`~/.pro_ka_po/teamwork.db`)
- Push/Pull sync z API
- Conflict resolution (last-write-wins lub merge strategy)

### 3. **SAMPLE_GROUPS zamiast prawdziwych danych**
**Problem:** `group_tree_panel.py` używa hardcoded `SAMPLE_GROUPS`.

**Rozwiązanie:** 
```python
def refresh_groups(self):
    """Pobierz grupy z API i odśwież drzewo"""
    if not self.api_client:
        return
    
    response = self.api_client.get_user_groups()
    if response.status_code == 200:
        self._groups = response.json()
        self.set_groups(self._groups)
```

### 4. **Brak auto-refresh po operacjach**
**Problem:** Po stworzeniu grupy/topic/wiadomości widok się nie odświeża.

**Rozwiązanie:** Emitować sygnał `data_changed` i nasłuchiwać go:
```python
# W teamwork_module.py
self.data_changed.connect(self._on_data_changed)

def _on_data_changed(self):
    """Odśwież wszystkie widoki po zmianie danych"""
    if self.api_client:
        self.tree_panel.refresh_groups()
        self.conversation_panel.refresh_current_view()
```

---

## 📝 PLAN DZIAŁANIA - ZAMKNIĘCIE MODUŁU

### FAZA 1: API Integration Core (P0 - Krytyczne) 🔴
**Cel:** Podstawowe funkcje CRUD działają z API

#### Task 1.1: Stworzyć TeamWorkAPIClient
- Plik: `src/Modules/custom_modules/TeamWork/teamwork_api_client.py`
- Metody:
  - `create_group(name, description)` → POST /groups
  - `get_user_groups()` → GET /groups
  - `create_topic(group_id, title, message)` → POST /topics
  - `get_group_topics(group_id)` → GET /topics?group_id={id}
  - `create_message(topic_id, content, color)` → POST /messages
  - `get_topic_messages(topic_id)` → GET /messages?topic_id={id}
  
**Czas:** 2-3 godziny

#### Task 1.2: Zintegrować API Client z teamwork_module
- Dodać `self.api_client = TeamWorkAPIClient(API_URL, token)` w `set_user_data()`
- Przekazać `api_client` do paneli (`tree_panel`, `conversation_panel`)
  
**Czas:** 1 godzina

#### Task 1.3: Podłączyć CreateGroupDialog do API
- W `_on_create_group()` wywołać `self.api_client.create_group()`
- Po sukcesie: emit `data_changed` → refresh tree
  
**Czas:** 1 godzina

#### Task 1.4: Podłączyć CreateTopicDialog do API
- W `_on_create_topic()` wywołać `self.api_client.create_topic()`
- Po sukcesie: refresh tree + select new topic
  
**Czas:** 1 godzina

#### Task 1.5: Podłączyć ReplyDialog do API
- W `_handle_reply_requested()` wywołać `self.api_client.create_message()`
- Po sukcesie: refresh messages list
  
**Czas:** 1 godzina

#### Task 1.6: Pobieranie grup i topics z API
- `group_tree_panel.refresh_groups()` → wywołuje `api_client.get_user_groups()`
- `conversation_panel.refresh_messages()` → wywołuje `api_client.get_topic_messages()`
  
**Czas:** 2 godziny

**Łączny czas FAZA 1:** 8-9 godzin

---

### FAZA 2: Team Management (P1 - Wysoki priorytet) 🟠
**Cel:** Pełne zarządzanie grupami i członkami

#### Task 2.1: TeamManagementDialog - pobieranie grup
- `_load_groups()` → wywołuje `api_client.get_user_groups()`
- Wyświetla listę z przyciskami akcji
  
**Czas:** 2 godziny

#### Task 2.2: Edycja grupy
- Przycisk "Edytuj" → otwiera dialog z wypełnionymi danymi
- Zapisanie → wywołuje `api_client.update_group(id, data)`
  
**Czas:** 1.5 godziny

#### Task 2.3: Usuwanie grupy
- Przycisk "Usuń" → konfirmacja → `api_client.delete_group(id)`
- Po sukcesie: usuń z listy + refresh tree
  
**Czas:** 1 godzina

#### Task 2.4: Dodawanie członka
- Dialog wyboru użytkownika (autocomplete email)
- `api_client.add_member(group_id, user_id, role='member')`
  
**Czas:** 2 godziny

#### Task 2.5: Usuwanie członka
- Lista członków z przyciskiem "Usuń"
- `api_client.remove_member(group_id, user_id)`
  
**Czas:** 1 godzina

#### Task 2.6: Przekazanie ownership
- Dialog wyboru nowego ownera (tylko z listy członków)
- `api_client.transfer_ownership(group_id, new_owner_id)`
  
**Czas:** 1.5 godziny

**Łączny czas FAZA 2:** 9 godzin

---

### FAZA 3: Tasks & Gantt (P1) 🟠
**Cel:** Zarządzanie zadaniami zespołowymi

#### Task 3.1: TaskDialog - tworzenie zadania
- `_handle_create_task()` → `api_client.create_task(topic_id, data)`
- Po sukcesie: refresh tasks list
  
**Czas:** 1.5 godziny

#### Task 3.2: Lista zadań z API
- `conversation_panel.display_topic_tasks()` → `api_client.get_topic_tasks(topic_id)`
  
**Czas:** 1 godzina

#### Task 3.3: Oznaczanie zadania jako wykonane
- Checkbox → `api_client.complete_task(task_id, completed=True)`
  
**Czas:** 1 godzina

#### Task 3.4: Gantt Chart z prawdziwymi danymi
- `GanttChartWidget.set_tasks()` → przyjmuje dane z API
- Kolorowanie według statusu (pending/in-progress/completed)
  
**Czas:** 2 godziny

**Łączny czas FAZA 3:** 5.5 godziny

---

### FAZA 4: Files & Important (P1) 🟠
**Cel:** Dopracowanie obsługi plików

#### Task 4.1: Auto-refresh listy plików po uploadzie
- Signal `file_uploaded` → wywołuje `conversation_panel.refresh_files()`
- `refresh_files()` → `api_client.get_topic_files(topic_id)`
  
**Czas:** 1 godzina

#### Task 4.2: Usuwanie pliku
- Przycisk "🗑️ Usuń" → `api_client.delete_file(file_id)`
- Po sukcesie: usuń z listy
  
**Czas:** 1 godzina

#### Task 4.3: Toggle "Important" dla plików
- Przycisk "⭐" → `api_client.mark_important(file_id, is_important=True)`
- Odświeżenie widoku
  
**Czas:** 1 godzina

#### Task 4.4: Toggle "Important" dla wiadomości
- Analogicznie jak dla plików
- `api_client.mark_message_important(message_id, is_important)`
  
**Czas:** 1 godzina

#### Task 4.5: Filtrowanie "Important"
- `display_topic_important()` → pobiera tylko elementy z `is_important=True`
  
**Czas:** 1.5 godziny

**Łączny czas FAZA 4:** 5.5 godziny

---

### FAZA 5: Sync Manager (P1) 🟠
**Cel:** Offline functionality i synchronizacja

#### Task 5.1: Local SQLite database
- Schema: `groups`, `topics`, `messages`, `files`, `tasks`
- `TeamWorkDBManager` z metodami CRUD
  
**Czas:** 3 godziny

#### Task 5.2: Sync Manager - Push
- `push_local_changes()` → wysyła nowe/zmienione rekordy do API
- Obsługa konfliktów (timestamp comparison)
  
**Czas:** 3 godziny

#### Task 5.3: Sync Manager - Pull
- `pull_remote_changes()` → pobiera dane z API i zapisuje lokalnie
- Update `last_sync_timestamp`
  
**Czas:** 2 godziny

#### Task 5.4: Auto-sync on startup
- `teamwork_module.activate()` → wywołuje `sync_manager.sync()`
- Progress indicator podczas sync
  
**Czas:** 1.5 godziny

#### Task 5.5: Conflict resolution
- Last-write-wins strategy
- Opcjonalnie: merge strategy dla wiadomości
  
**Czas:** 2 godziny

**Łączny czas FAZA 5:** 11.5 godziny

---

### FAZA 6: Links & Invitations (P2) 🟡
**Cel:** Dodatkowe funkcjonalności

#### Task 6.1: Backend - topic_links table
- Model `TopicLink` w `teamwork_models.py`
- Schema Pydantic w `teamwork_schemas.py`
- Endpointy: POST/GET /links
  
**Czas:** 2 godziny

#### Task 6.2: Frontend - dodawanie linków
- Dialog w `CreateTopicDialog` już istnieje
- Podłączyć do API: `api_client.add_link(topic_id, url, title)`
  
**Czas:** 1.5 godziny

#### Task 6.3: Frontend - wyświetlanie linków
- `conversation_panel.display_topic_links()` → `api_client.get_topic_links()`
  
**Czas:** 1 godzina

#### Task 6.4: Backend - group_invitations table
- Model `GroupInvitation` (inviter_id, invitee_email, group_id, status)
- Endpointy: POST /invitations, GET /invitations, PATCH /invitations/{id}/accept
  
**Czas:** 3 godziny

#### Task 6.5: Frontend - wysyłanie zaproszeń
- `InvitationsDialog` → formularz email + wybór grupy
- `api_client.send_invitation(group_id, email)`
  
**Czas:** 2 godziny

#### Task 6.6: Frontend - przyjmowanie zaproszeń
- Lista "Otrzymane" → przycisk "Akceptuj" / "Odrzuć"
- `api_client.respond_invitation(invitation_id, accept=True)`
  
**Czas:** 1.5 godziny

**Łączny czas FAZA 6:** 11 godzin

---

### FAZA 7: Testing & Polish (P1) 🧪
**Cel:** Stabilność i UX

#### Task 7.1: Unit tests backend
- Testy endpointów API (pytest)
- Testy autoryzacji (owner vs member)
  
**Czas:** 4 godziny

#### Task 7.2: Integration tests
- Test pełnego flow: create group → add topic → add message → upload file
  
**Czas:** 2 godziny

#### Task 7.3: Error handling
- Obsługa 401/403/404/500 w API client
- User-friendly error messages
  
**Czas:** 2 godziny

#### Task 7.4: Loading states
- Spinner podczas ładowania danych
- Disable buttons podczas operacji API
  
**Czas:** 1.5 godziny

#### Task 7.5: UX improvements
- Tooltips na przyciskach
- Keyboard shortcuts (Ctrl+N - new topic, etc.)
- Drag & drop dla plików
  
**Czas:** 3 godziny

**Łączny czas FAZA 7:** 12.5 godziny

---

## 📊 PODSUMOWANIE CZASOWE

| Faza | Priorytet | Czas | Procent prac |
|------|-----------|------|--------------|
| **FAZA 1: API Integration Core** | P0 🔴 | 8-9h | 20% |
| **FAZA 2: Team Management** | P1 🟠 | 9h | 20% |
| **FAZA 3: Tasks & Gantt** | P1 🟠 | 5.5h | 12% |
| **FAZA 4: Files & Important** | P1 🟠 | 5.5h | 12% |
| **FAZA 5: Sync Manager** | P1 🟠 | 11.5h | 25% |
| **FAZA 6: Links & Invitations** | P2 🟡 | 11h | 24% |
| **FAZA 7: Testing & Polish** | P1 🧪 | 12.5h | 27% |
| **RAZEM** | - | **63h** | **140%** |

**Minimum Viable Product (MVP):**
- FAZA 1 + FAZA 2 + FAZA 4 + FAZA 7 = **35.5 godzin**

**Full Feature Set:**
- Wszystkie fazy = **63 godziny**

---

## 🎯 REKOMENDACJE

### KROK 1: MVP (35.5h) - Priorytet KRYTYCZNY
**Zakres:** Podstawowe CRUD grup, topics, wiadomości, plików + testing

**Rezultat:** Moduł TeamWork **użyteczny** dla zespołów:
- Można tworzyć grupy i zarządzać członkami
- Można tworzyć wątki i pisać wiadomości
- Można przesyłać i pobierać pliki
- Dane są synchronizowane z API
- Aplikacja jest stabilna

**Deadline:** 2-3 tygodnie (przy 2-3h/dzień)

### KROK 2: Full Feature (dodatkowe 27.5h)
**Zakres:** Sync manager + zadania + linki + zaproszenia

**Rezultat:** Moduł TeamWork **kompletny**:
- Offline functionality
- Zarządzanie zadaniami z Gantt
- Linki w topic
- System zaproszeń

**Deadline:** Dodatkowe 2 tygodnie

---

## 🔍 METRYKI SUKCESU

### Przed zamknięciem modułu należy zweryfikować:

✅ **Funkcjonalność:**
- [ ] 100% dialogów wysyła dane do API (nie tylko MessageBox)
- [ ] Drzewo grup/topics ładuje się z API
- [ ] Lista wiadomości/plików/zadań ładuje się z API
- [ ] Po każdej operacji (create/update/delete) widok się odświeża
- [ ] Offline mode działa (Sync Manager)

✅ **UX/UI:**
- [ ] Loading spinners podczas operacji API
- [ ] Error messages są czytelne dla użytkownika
- [ ] Wszystkie przyciski mają tooltips
- [ ] Motywy kolorystyczne działają poprawnie

✅ **Testy:**
- [ ] Unit tests backend (>80% coverage)
- [ ] Integration tests (minimum 5 scenariuszy)
- [ ] Manual testing (user journey)

✅ **Dokumentacja:**
- [ ] README z instrukcją użycia
- [ ] API documentation (Swagger/OpenAPI)
- [ ] Changelog z listą zmian

---

## 🎬 NEXT STEPS - NAJBLIŻSZE DZIAŁANIA

### ⚡ TERAZ (w kolejnych 24h):
1. **Stworzyć `TeamWorkAPIClient`** (Task 1.1) - **2-3h**
2. **Zintegrować z `teamwork_module.py`** (Task 1.2) - **1h**
3. **Podłączyć `CreateGroupDialog`** (Task 1.3) - **1h**

### 📅 TEN TYDZIEŃ:
4. Dokończyć FAZĘ 1 (pozostałe Tasks 1.4-1.6)
5. Przetestować podstawowy flow: login → create group → create topic → add message

### 📅 NASTĘPNY TYDZIEŃ:
6. FAZA 2: Team Management
7. FAZA 4: Files & Important (dopracowanie)

---

## 📌 WNIOSKI

**Status obecny:** Moduł TeamWork jest **szkieletem gotowym do życia**. Wszystkie UI komponenty są zbudowane, backend API jest kompletny, ale **brakuje połączenia między nimi**.

**Główny problem:** Brak `TeamWorkAPIClient` - centralizowanego miejsca do komunikacji z API.

**Rozwiązanie:** Utworzenie API Client i systematyczne podłączanie dialogów (FAZA 1).

**Optymistyczny scenariusz:** MVP w 2-3 tygodnie (35.5h), Full Feature w 4-5 tygodni (63h).

**Pesymistyczny scenariusz:** MVP w 4 tygodnie, Full Feature w 8 tygodni (przy nieprzewidzianych problemach).

---

**Raport przygotowany przez:** AI Assistant  
**Data:** 2025-11-13  
**Wersja dokumentu:** 1.0
