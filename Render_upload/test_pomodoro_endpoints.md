# Test Pomodoro API Endpoints

## 🔐 Uwaga: Najpierw musisz się zalogować!

### 1. Zaloguj się (POST /api/v1/auth/login)
```json
{
  "email": "twoj_email@example.com",
  "password": "twoje_haslo"
}
```
**Skopiuj `access_token` z odpowiedzi!**

### 2. Autoryzuj w Swagger
- Kliknij przycisk **"Authorize"** (🔓) w prawym górnym rogu
- Wpisz: `Bearer TWOJ_ACCESS_TOKEN`
- Kliknij "Authorize"

---

## 📝 Test Endpoints

### ✅ 1. Utwórz nowy temat sesji (POST /api/pomodoro/topics)

**Request Body:**
```json
{
  "local_id": "topic_001",
  "name": "Nauka Python",
  "color": "#FF5733",
  "icon": "🐍",
  "description": "Sesje nauki programowania w Python",
  "is_favorite": true,
  "sort_order": 1,
  "version": 1,
  "last_modified": "2025-11-02T10:30:00Z"
}
```

**Oczekiwany wynik:** 
- Status: 200 OK
- Response zawiera `server_id`, `version`, wszystkie pola

---

### ✅ 2. Pobierz wszystkie tematy (GET /api/pomodoro/all?type=topic)

**Query Parameters:**
- `user_id`: (zostanie automatycznie wypełniony z tokenu)
- `type`: `topic`
- `last_sync`: (opcjonalnie) `2025-11-01T00:00:00Z`

**Oczekiwany wynik:** 
- Status: 200 OK
- Lista tematów w `topics`
- Pusty array w `sessions`

---

### ✅ 3. Utwórz sesję Pomodoro (POST /api/pomodoro/sessions)

**Request Body:**
```json
{
  "local_id": "session_001",
  "topic_id": "UŻYJ_SERVER_ID_Z_KROKU_1",
  "session_type": "work",
  "session_date": "2025-11-02",
  "planned_start_time": "10:00:00",
  "actual_start_time": "10:02:00",
  "planned_end_time": "10:25:00",
  "actual_end_time": "10:27:00",
  "planned_duration_minutes": 25,
  "actual_duration_minutes": 25,
  "status": "completed",
  "interruptions_count": 1,
  "productivity_rating": 4,
  "notes": "Dobra sesja, jedna przerwa na telefon",
  "tags": ["python", "nauka"],
  "version": 1,
  "last_modified": "2025-11-02T10:30:00Z"
}
```

**Oczekiwany wynik:** 
- Status: 200 OK
- Response zawiera `server_id`, powiązanie z `topic_id`

---

### ✅ 4. Pobierz wszystkie sesje (GET /api/pomodoro/all?type=session)

**Query Parameters:**
- `user_id`: (automatycznie)
- `type`: `session`
- `last_sync`: (opcjonalnie)

**Oczekiwany wynik:** 
- Status: 200 OK
- Lista sesji w `sessions`
- Pusty array w `topics`

---

### ✅ 5. Pobierz WSZYSTKO (GET /api/pomodoro/all)

**Query Parameters:**
- `user_id`: (automatycznie)
- `type`: (puste - pobierze topics + sessions)

**Oczekiwany wynik:** 
- Status: 200 OK
- Wypełnione oba: `topics` i `sessions`

---

### ✅ 6. Aktualizuj temat (POST /api/pomodoro/topics) - ten sam local_id

**Request Body:**
```json
{
  "local_id": "topic_001",
  "name": "Nauka Python - Zaawansowane",
  "color": "#FF5733",
  "icon": "🐍",
  "description": "Sesje nauki zaawansowanego Python",
  "is_favorite": true,
  "sort_order": 1,
  "version": 2,
  "last_modified": "2025-11-02T11:00:00Z"
}
```

**Oczekiwany wynik:** 
- Status: 200 OK
- `version` = 2
- Zaktualizowana nazwa i opis

---

### ⚠️ 7. Test konfliktu wersji (POST /api/pomodoro/topics)

**Request Body:** (stara wersja - powinno zwrócić konflikt)
```json
{
  "local_id": "topic_001",
  "name": "To nie powinno się zapisać",
  "color": "#FF5733",
  "icon": "🐍",
  "version": 1,
  "last_modified": "2025-11-02T09:00:00Z"
}
```

**Oczekiwany wynik:** 
- Status: 409 CONFLICT
- Response zawiera `server_data` z aktualną wersją

---

### ✅ 8. Bulk Sync - synchronizacja wsadowa (POST /api/pomodoro/bulk-sync)

**Request Body:**
```json
{
  "topics": [
    {
      "local_id": "topic_002",
      "name": "Projekt PRO-Ka-Po",
      "color": "#3498DB",
      "icon": "💼",
      "version": 1,
      "last_modified": "2025-11-02T12:00:00Z"
    },
    {
      "local_id": "topic_003",
      "name": "Trening",
      "color": "#2ECC71",
      "icon": "🏋️",
      "version": 1,
      "last_modified": "2025-11-02T12:00:00Z"
    }
  ],
  "sessions": [
    {
      "local_id": "session_002",
      "topic_id": "UŻYJ_SERVER_ID_Z_TOPIC_002",
      "session_type": "work",
      "session_date": "2025-11-02",
      "planned_start_time": "12:00:00",
      "actual_start_time": "12:00:00",
      "planned_end_time": "12:25:00",
      "actual_end_time": "12:25:00",
      "planned_duration_minutes": 25,
      "actual_duration_minutes": 25,
      "status": "completed",
      "version": 1,
      "last_modified": "2025-11-02T12:30:00Z"
    }
  ]
}
```

**Oczekiwany wynik:** 
- Status: 200 OK
- `synced_topics`: 2
- `synced_sessions`: 1
- Arrays `topics` i `sessions` z pełnymi danymi

---

### 🗑️ 9. Usuń sesję (DELETE /api/pomodoro/sessions/{session_id})

**Path Parameters:**
- `session_id`: UŻYJ_SERVER_ID_Z_SESJI
- `version`: 1

**Oczekiwany wynik:** 
- Status: 200 OK
- `message`: "Session soft-deleted successfully"

---

### 🗑️ 10. Usuń temat (DELETE /api/pomodoro/topics/{topic_id})

**Path Parameters:**
- `topic_id`: UŻYJ_SERVER_ID_Z_TEMATU
- `version`: 2 (lub aktualna wersja)

**Oczekiwany wynik:** 
- Status: 200 OK
- `message`: "Topic soft-deleted successfully"

---

## 🧪 Scenariusze testowe

### Scenariusz 1: Kompletny flow
1. Login → otrzymaj token
2. Authorize w Swagger
3. Utwórz temat → zapisz `server_id`
4. Utwórz sesję z tym `topic_id`
5. Pobierz wszystko → sprawdź, czy są oba
6. Aktualizuj temat → sprawdź `version++`
7. Usuń sesję
8. Usuń temat

### Scenariusz 2: Conflict resolution
1. Utwórz temat (version=1)
2. Zaktualizuj temat (version=2)
3. Próbuj nadpisać starą wersję (version=1) → 409 Conflict
4. Użyj `server_data` z odpowiedzi 409 do merge

### Scenariusz 3: Bulk sync
1. Utwórz 3 tematy bulk sync
2. Utwórz 5 sesji bulk sync
3. Pobierz wszystko → sprawdź liczby

---

## 📊 Sprawdzanie w bazie danych

Możesz również sprawdzić dane bezpośrednio w PostgreSQL:

```sql
-- Wszystkie tematy użytkownika
SELECT * FROM s05_pomodoro.session_topics 
WHERE user_id = 'TWOJ_USER_ID' 
AND deleted_at IS NULL;

-- Wszystkie sesje użytkownika
SELECT * FROM s05_pomodoro.session_logs 
WHERE user_id = 'TWOJ_USER_ID' 
AND deleted_at IS NULL;

-- Sesje z tematami (JOIN)
SELECT 
    sl.id, 
    sl.session_date, 
    sl.session_type, 
    sl.status,
    st.name as topic_name,
    sl.actual_duration_minutes,
    sl.productivity_rating
FROM s05_pomodoro.session_logs sl
LEFT JOIN s05_pomodoro.session_topics st ON sl.topic_id = st.id
WHERE sl.user_id = 'TWOJ_USER_ID'
AND sl.deleted_at IS NULL
ORDER BY sl.session_date DESC, sl.actual_start_time DESC;
```

---

## ✨ Tips

1. **Authorization Header**: Zawsze pamiętaj o `Bearer TOKEN`
2. **Version Control**: Każda aktualizacja zwiększa `version` o 1
3. **Soft Delete**: Usunięte elementy mają `deleted_at` nie NULL
4. **Timestamps**: Używaj ISO 8601 format: `2025-11-02T10:30:00Z`
5. **Conflict 409**: Zawiera `server_data` do merge

---

## 🎯 Checklist testowy

- [ ] Login działa
- [ ] Authorization działa
- [ ] POST /topics - create
- [ ] POST /topics - update (ta sama local_id)
- [ ] POST /topics - conflict 409 (stara wersja)
- [ ] GET /all?type=topic
- [ ] POST /sessions - create
- [ ] POST /sessions - update
- [ ] GET /all?type=session
- [ ] GET /all (bez type - wszystko)
- [ ] POST /bulk-sync - topics
- [ ] POST /bulk-sync - sessions
- [ ] DELETE /sessions/{id}
- [ ] DELETE /topics/{id}
- [ ] DELETE - conflict 409 (zła wersja)

**Powodzenia! 🚀**
