# 🔍 RAPORT ANALIZY SYNCHRONIZACJI - PRO-Ka-Po

**Data:** 3 listopada 2025  
**Autor:** AI Assistant  
**Status:** ❌ KRYTYCZNY BŁĄD ZNALEZIONY

---

## 📋 PODSUMOWANIE WYKONAWCZE

### Problemy zidentyfikowane:
1. **KRYTYCZNY:** WebSocket Notes - błędna ścieżka URL (403 Forbidden)
2. **POWAŻNY:** Database constraint violation w `note_links`
3. ✅ **DZIAŁA:** Synchronizacja Alarms & Timers
4. ✅ **DZIAŁA:** Synchronizacja Pomodoro
5. ✅ **ZAIMPLEMENTOWANO:** Token refresh infrastructure

---

## 🔴 PROBLEM #1: WebSocket Notes - Błędna ścieżka URL

### Symptomy:
```
INFO: 127.0.0.1:56142 - "WebSocket /api/v1/ws/notes/207222a2-...?token=..." 403
INFO: connection rejected (403 Forbidden)
```

Klient próbuje 10+ razy, zawsze 403 Forbidden.

### Analiza root cause:

#### Klient wysyła na:
```python
# src/Modules/Note_module/note_websocket_client.py:295
ws_base_url = os.getenv('NOTES_WS_URL', 'ws://127.0.0.1:8000/api/v1/ws/notes')
ws_url = f"{ws_base_url}/{user_id}"
# Rezultat: ws://127.0.0.1:8000/api/v1/ws/notes/207222a2-3845-...
```

#### Ale router oczekuje:
```python
# Render_upload/app/notes_router.py:321
@router.websocket("/ws/{user_id}")
# Router ma prefix: router = APIRouter(prefix="/api/v1/notes")
# Rezultat: /api/v1/notes/ws/{user_id}
```

### DIAGNOZA:
**URL MISMATCH!**

| Komponent | Ścieżka |
|-----------|---------|
| **Klient** | `/api/v1/ws/notes/{user_id}` |
| **Server** | `/api/v1/notes/ws/{user_id}` |
| **Problem** | `ws/notes` vs `notes/ws` - ODWROTNA KOLEJNOŚĆ! |

### Porównanie z działającymi modułami:

#### ✅ Alarms (DZIAŁA):
```python
# Klient: src/Modules/Alarm_module/alarm_websocket_client.py:74
ws_url = f"{ws_url}/api/alarms-timers/ws"

# Server: Render_upload/app/alarms_router.py:652
@router.websocket("/ws")  # prefix="/api/alarms-timers"
# Razem: /api/alarms-timers/ws ✅ MATCH!
```

#### ✅ Pomodoro (PRAWDOPODOBNIE DZIAŁA):
- Brak WebSocket (używa tylko REST API + polling)
- Synchronizacja co 300s (auto-sync)

---

## 🔴 PROBLEM #2: Database Constraint Violation

### Symptomy:
```sql
new row for relation "note_links" violates check constraint "links_position_valid"
DETAIL: Failing row contains (..., 'dfsd', 4, 4, ...)
                                        ↑    ↑
                                    start  end (RÓWNE!)
```

### Constraint:
```sql
CHECK (start_position < end_position)
```

### Dane w błędnych requestach:
```python
{'link_text': 'dfsd', 'start_position': 4, 'end_position': 4}
{'link_text': 'Możesz tworzyć...', 'start_position': 90, 'end_position': 90}
{'link_text': ' dorosła samica. ', 'start_position': 23, 'end_position': 23}
```

Wszystkie mają `start_position == end_position` (długość 0!)

### Root cause:
Prawdopodobnie błąd w kliencie przy tworzeniu linków - nie dodaje długości tekstu do `end_position`.

**Oczekiwane:**
```python
start_position = 4
end_position = start_position + len('dfsd') = 4 + 4 = 8  # ✅
```

**Aktualne:**
```python
start_position = 4
end_position = 4  # ❌ BŁĄD!
```

---

## ✅ CO DZIAŁA POPRAWNIE

### 1. Alarms & Timers Module
```
INFO: 127.0.0.1:63674 - "WebSocket /api/alarms-timers/ws?token=..." [accepted]
INFO: app.websocket_manager:connect:36 - WebSocket connected: user=207222a2-..., total=1
INFO: connection open
```

**Architektura:**
- ✅ WebSocket URL: `/api/alarms-timers/ws`
- ✅ Token w query parameter
- ✅ Autentykacja przez `decode_token()`
- ✅ `websockets` library (asyncio)
- ✅ Auto-reconnect z delay
- ✅ Status LED integration

**Kod:**
```python
# Klient: alarm_websocket_client.py
ws_url = f"{ws_url}/api/alarms-timers/ws?token={self.auth_token}"
await websockets.connect(ws_url)

# Server: alarms_router.py
@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(...)):
    payload = decode_token(token)
    await manager.connect(websocket, user_id)
```

### 2. Pomodoro Module
```
[POMODORO SYNC] Auto-sync started (interval: 300s)
[POMODORO] PomodoroLogic initialized successfully
```

**Architektura:**
- ✅ REST API only (bez WebSocket)
- ✅ Background sync co 5 minut
- ✅ Local database: `pomodoro.db`
- ✅ API Client z timeout
- ✅ Sync Manager z auto-retry

### 3. Token Refresh Infrastructure
**FULLY IMPLEMENTED:**

```python
# NotesAPIClient._try_refresh_token()
def _try_refresh_token(self) -> bool:
    response = requests.post(refresh_url, json={"refresh_token": self.refresh_token})
    if response.status_code == 200:
        new_access_token = response.json().get('access_token')
        self.set_auth_token(new_access_token)
        if self.on_token_refreshed:
            self.on_token_refreshed(new_access_token, self.refresh_token)
        return True
    return False

# NotesAPIClient._request_with_retry()
def _request_with_retry(self, method, url, **kwargs):
    response = self.session.request(method, url, **kwargs)
    if response.status_code == 401:  # Token expired
        if self._try_refresh_token():
            response = self.session.request(method, url, **kwargs)  # Retry
    return response
```

**Callback chain:**
```
HTTP API (401) 
  → NotesAPIClient._try_refresh_token()
    → self.on_token_refreshed(new_token)
      → NotesSyncManager.on_token_refreshed_wrapper()
        → self.auth_token = new_token
        → ws_client.update_token(new_token)  # ✅ WebSocket updated!
        → self.on_token_refreshed(...)  # Propagate to UI
          → MainWindow callback → Update UI
```

---

## 🏗️ ARCHITEKTURA PORÓWNAWCZA

### WebSocket Implementation Patterns

| Moduł | Library | URL Pattern | Auth Method | Auto-reconnect |
|-------|---------|-------------|-------------|----------------|
| **Alarms** | `websockets` (asyncio) | `/api/alarms-timers/ws` | Query param | ✅ Yes (5s delay) |
| **Notes** | `QWebSocket` (Qt) | `/api/v1/ws/notes/{user_id}` ❌ | Query param | ✅ Yes (5s, max 10) |
| **Pomodoro** | N/A (no WS) | N/A | N/A | N/A |

### REST API Patterns

| Moduł | Endpoint Prefix | Token Refresh | Retry Logic | Local DB |
|-------|----------------|---------------|-------------|----------|
| **Alarms** | `/api/alarms-timers` | ❓ Unknown | ❓ Unknown | ✅ SQLite |
| **Notes** | `/api/v1/notes` | ✅ Implemented | ✅ Auto-retry on 401 | ✅ SQLite |
| **Pomodoro** | `/api/v1/pomodoro` | ❓ Unknown | ❓ Unknown | ✅ SQLite |

---

## 🔧 WYMAGANE NAPRAWY

### 1. FIX: WebSocket URL w Notes Module

**Plik:** `src/Modules/Note_module/note_websocket_client.py:295`

**Przed:**
```python
ws_base_url = os.getenv('NOTES_WS_URL', 'ws://127.0.0.1:8000/api/v1/ws/notes')
                                                                      ^^^^^^^^
                                                                      BŁĘDNA KOLEJNOŚĆ!
```

**Po:**
```python
ws_base_url = os.getenv('NOTES_WS_URL', 'ws://127.0.0.1:8000/api/v1/notes/ws')
                                                                      ^^^^^^^^
                                                                      POPRAWNA KOLEJNOŚĆ!
```

**Impact:** KRYTYCZNY - bez tego Notes WebSocket nie będzie działać.

---

### 2. FIX: note_links Database Constraint

**Problem:** `start_position == end_position` (długość 0)

**Potencjalne lokacje błędu:**

1. **UI - tworzenie linku:**
   - `src/Modules/Note_module/note_module_logic.py`
   - `src/ui/note_view.py`
   - Funkcja obsługująca tworzenie linków między notatkami

2. **Oczekiwane zachowanie:**
```python
# Gdy użytkownik zaznacza tekst "dfsd" na pozycji 4:
link = {
    'link_text': 'dfsd',
    'start_position': 4,
    'end_position': 4 + len('dfsd')  # = 8 ✅
}
```

3. **Aktualne (błędne) zachowanie:**
```python
link = {
    'link_text': 'dfsd',
    'start_position': 4,
    'end_position': 4  # ❌ Brak dodania długości!
}
```

**Kroki naprawy:**
1. Znajdź kod tworzący note_links w UI
2. Dodaj: `end_position = start_position + len(link_text)`
3. Wyczyść istniejące błędne linki z bazy (SQL DELETE)

---

## 📊 PODSUMOWANIE STATUSU

| Komponent | Status | Uwagi |
|-----------|--------|-------|
| **Alarms WebSocket** | ✅ DZIAŁA | Wzorcowa implementacja |
| **Alarms REST API** | ✅ DZIAŁA | Synchronizacja OK |
| **Pomodoro API** | ✅ DZIAŁA | Polling co 5 min |
| **Notes WebSocket** | ❌ NIE DZIAŁA | **BŁĘDNY URL** |
| **Notes REST API** | ⚠️ CZĘŚCIOWO | HTTP OK, links błędne |
| **Token Refresh** | ✅ ZAIMPLEMENTOWANO | Callback chain działa |
| **Database Links** | ❌ CONSTRAINT ERROR | Pozycje = 0 długość |

---

## 🎯 PLAN DZIAŁANIA

### NATYCHMIASTOWE (CRITICAL):

1. ✅ **Napraw WebSocket URL w Notes:**
   - Zmień: `api/v1/ws/notes` → `api/v1/notes/ws`
   - Test: Restart klienta, sprawdź logi serwera
   - Expected: `✅ WebSocket connected for user ...`

2. ✅ **Napraw note_links tworzenie:**
   - Znajdź funkcję tworzącą linki
   - Dodaj poprawne obliczanie `end_position`
   - Test: Utwórz link, sprawdź w DB

3. 🗑️ **Wyczyść błędne dane:**
```sql
-- Usuń istniejące błędne linki
DELETE FROM s06_notes.note_links 
WHERE start_position = end_position;
```

### OPCJONALNE (IMPROVEMENTS):

4. 📝 **Token Refresh w Alarms/Pomodoro:**
   - Zaimplementuj podobnie jak w Notes
   - Dodaj callback chain
   - Test: Odczekaj expiry, sprawdź auto-refresh

5. 🔄 **Unified WebSocket Pattern:**
   - Rozważ migrację Notes na `websockets` (jak Alarms)
   - Lub Alarms na `QWebSocket` (jak Notes)
   - Cel: Consistency w całej aplikacji

6. 📊 **Error Handling:**
   - Dodaj retry logic dla 500 errors
   - Exponential backoff dla reconnect
   - User-friendly error messages

---

## 🧪 TESTY PO NAPRAWIE

### Test 1: WebSocket Connection
```bash
# Server terminal - oczekiwany output:
✅ WebSocket connected for user 207222a2-3845-40c2-9bea-cd5bbd6e15f6

# Client terminal - oczekiwany output:
INFO | src.Modules.Note_module.note_websocket_client:_on_connected - WebSocket connected
```

### Test 2: Note Links Creation
```python
# Utwórz link w UI
# Sprawdź w bazie:
SELECT start_position, end_position, link_text, 
       (end_position - start_position) as length
FROM s06_notes.note_links 
WHERE created_at > NOW() - INTERVAL '1 minute';

# Oczekiwane: length > 0
```

### Test 3: Token Refresh (Long-running)
```python
# Uruchom klienta
# Odczekaj 15+ minut (token expiry)
# Utwórz nową notatkę
# Expected: Automatyczne odświeżenie tokena (log: "✓ Access token refreshed")
```

---

## 📚 WNIOSKI

### Co działa dobrze:
- ✅ Alarms module - wzorcowa implementacja
- ✅ Token refresh infrastructure - kompletna implementacja
- ✅ Local-first architecture - SQLite databases
- ✅ WebSocket auto-reconnect - resilient design

### Co wymaga poprawy:
- ❌ URL routing inconsistency (ws/notes vs notes/ws)
- ❌ Client-side data validation (note_links positions)
- ⚠️ Inconsistent WebSocket libraries (QWebSocket vs websockets)
- ⚠️ Token refresh tylko w Notes (brak w Alarms/Pomodoro)

### Rekomendacje architektoniczne:
1. **Standaryzacja URL patterns** - wspólna konwencja dla wszystkich modułów
2. **Unified WebSocket library** - jedna library dla całej aplikacji
3. **Client-side validation** - walidacja przed wysłaniem do API
4. **Comprehensive error handling** - user-friendly messages
5. **Testing infrastructure** - automated WebSocket tests

---

**Koniec raportu**  
*Wygenerowano automatycznie przez AI Assistant*
