# Schemat Bazy Danych - Moduł Zadań

## Przegląd

Baza danych modułu zadań obsługuje:
- ✅ Konfigurowalne kolumny (systemowe + użytkownika)
- ✅ Zadania główne i podzadania (rekurencyjne)
- ✅ Tagi z kolorami
- ✅ Listy własne użytkownika
- ✅ Archiwizacja i miękkie usuwanie
- ✅ Synchronizacja z serwerem
- ✅ Niestandardowe dane w formacie JSON

---

## Tabele

### 1. `task_columns_config`
**Przeznaczenie:** Przechowuje konfigurację kolumn dla każdego użytkownika

| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | INTEGER PK | Unikalny identyfikator |
| `user_id` | INTEGER | ID użytkownika |
| `column_id` | TEXT | Nazwa kolumny (np. "Zadanie", "Status") |
| `position` | INTEGER | Pozycja wyświetlania (kolejność) |
| `type` | TEXT | Typ kolumny (text, checkbox, data, lista, etc.) |
| `visible_main` | BOOLEAN | Widoczna w głównym widoku zadań |
| `visible_bar` | BOOLEAN | Widoczna w pasku dolnym (quick input) |
| `default_value` | TEXT | Wartość domyślna dla nowych zadań |
| `list_name` | TEXT | Nazwa powiązanej listy (dla typu "lista") |
| `is_system` | BOOLEAN | Czy kolumna systemowa (nieusuwalna) |
| `editable` | BOOLEAN | Czy użytkownik może edytować |
| `allow_edit` | TEXT | JSON z dozwolonymi polami do edycji |
| `created_at` | TIMESTAMP | Data utworzenia |
| `updated_at` | TIMESTAMP | Data ostatniej aktualizacji |

**Indeksy:**
- `idx_columns_user` na `(user_id, position)`

**Unique constraint:** `(user_id, column_id)`

---

### 2. `task_tags`
**Przeznaczenie:** Przechowuje tagi zadań z kolorami

| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | INTEGER PK | Unikalny identyfikator |
| `user_id` | INTEGER | ID użytkownika |
| `name` | TEXT | Nazwa tagu (np. "Pilne", "Praca") |
| `color` | TEXT | Kolor w formacie hex (np. "#FF0000") |
| `created_at` | TIMESTAMP | Data utworzenia |
| `updated_at` | TIMESTAMP | Data ostatniej aktualizacji |
| `deleted_at` | TIMESTAMP | Data usunięcia (soft delete) |

**Indeksy:**
- `idx_tags_user` na `(user_id, deleted_at)`

**Unique constraint:** `(user_id, name)`

---

### 3. `task_custom_lists`
**Przeznaczenie:** Przechowuje listy własne użytkownika (dla kolumn typu "lista")

| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | INTEGER PK | Unikalny identyfikator |
| `user_id` | INTEGER | ID użytkownika |
| `name` | TEXT | Nazwa listy (np. "Priorytet", "Status projektu") |
| `values` | TEXT | JSON array z wartościami (np. ["Niski", "Średni", "Wysoki"]) |
| `created_at` | TIMESTAMP | Data utworzenia |
| `updated_at` | TIMESTAMP | Data ostatniej aktualizacji |
| `deleted_at` | TIMESTAMP | Data usunięcia (soft delete) |

**Indeksy:**
- `idx_lists_user` na `(user_id, deleted_at)`

**Unique constraint:** `(user_id, name)`

---

### 4. `tasks` ⭐ GŁÓWNA TABELA
**Przeznaczenie:** Przechowuje zadania i podzadania

| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | INTEGER PK | Unikalny identyfikator |
| `user_id` | INTEGER | ID użytkownika |
| `parent_id` | INTEGER FK | ID zadania nadrzędnego (NULL = zadanie główne) |
| `position` | INTEGER | Pozycja w liście (dla sortowania) |
| `title` | TEXT | Tytuł zadania |
| `status` | BOOLEAN | Status ukończenia (0=nieukończone, 1=ukończone) |
| `completion_date` | TIMESTAMP | Data ukończenia (wypełniana automatycznie) |
| `archived` | BOOLEAN | Czy zarchiwizowane |
| `archived_at` | TIMESTAMP | Data archiwizacji |
| `note_id` | INTEGER | ID powiązanej notatki |
| `kanban_id` | INTEGER | ID powiązanej karty Kanban |
| `alarm_date` | TIMESTAMP | Data alarmu/przypomnienia |
| `custom_data` | TEXT | JSON z danymi niestandardowych kolumn |
| `created_at` | TIMESTAMP | Data utworzenia |
| `updated_at` | TIMESTAMP | Data ostatniej aktualizacji |
| `deleted_at` | TIMESTAMP | Data usunięcia (soft delete) |
| `synced` | BOOLEAN | Czy zsynchronizowane z serwerem |
| `server_id` | INTEGER | ID zadania na serwerze (po synchronizacji) |

**Indeksy:**
- `idx_tasks_user` na `(user_id, deleted_at, archived)`
- `idx_tasks_parent` na `(parent_id)` - dla podzadań
- `idx_tasks_position` na `(user_id, position)` - dla sortowania

**Foreign Keys:**
- `parent_id` → `tasks(id)` ON DELETE CASCADE (usunięcie zadania usuwa podzadania)

**Przykład struktury `custom_data`:**
```json
{
  "Priorytet": "Wysoki",
  "Data realizacji": "2025-11-10",
  "Kategoria": "Rozwój",
  "Koszt": "1500.00"
}
```

---

### 5. `task_tag_assignments`
**Przeznaczenie:** Relacja many-to-many między zadaniami a tagami

| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | INTEGER PK | Unikalny identyfikator |
| `task_id` | INTEGER FK | ID zadania |
| `tag_id` | INTEGER FK | ID tagu |
| `created_at` | TIMESTAMP | Data przypisania |

**Indeksy:**
- `idx_tag_assignments` na `(task_id, tag_id)`

**Foreign Keys:**
- `task_id` → `tasks(id)` ON DELETE CASCADE
- `tag_id` → `task_tags(id)` ON DELETE CASCADE

**Unique constraint:** `(task_id, tag_id)`

---

### 6. `task_settings`
**Przeznaczenie:** Przechowuje ustawienia modułu zadań dla użytkownika

| Kolumna | Typ | Opis |
|---------|-----|------|
| `id` | INTEGER PK | Unikalny identyfikator |
| `user_id` | INTEGER | ID użytkownika |
| `key` | TEXT | Klucz ustawienia |
| `value` | TEXT | Wartość w formacie JSON |
| `created_at` | TIMESTAMP | Data utworzenia |
| `updated_at` | TIMESTAMP | Data ostatniej aktualizacji |

**Unique constraint:** `(user_id, key)`

**Przykładowe ustawienia:**
```json
{
  "auto_archive_enabled": true,
  "auto_archive_after_days": 30,
  "auto_move_completed": false,
  "auto_archive_completed": true
}
```

---

## Diagram relacji

```
┌─────────────────────┐
│ task_columns_config │
│  - user_id          │
│  - column_id        │
│  - position         │
│  - type             │
│  - visible_*        │
│  - default_value    │
│  - list_name ───────┼──┐
└─────────────────────┘  │
                         │
┌─────────────────────┐  │   ┌──────────────────┐
│ task_custom_lists   │◄─┘   │   task_tags      │
│  - name             │      │  - name          │
│  - values (JSON)    │      │  - color         │
└─────────────────────┘      └──────────────────┘
                                      ▲
                                      │
┌─────────────────────┐      ┌───────┴──────────┐
│       tasks         │      │ task_tag_        │
│  - parent_id ───┐   │      │ assignments      │
│  - title        │   │◄─────┤  - task_id       │
│  - status       │   │      │  - tag_id        │
│  - custom_data  │   │      └──────────────────┘
│  - note_id      │   │
│  - kanban_id    │   │
│  - alarm_date   │   │
└─────────────────┴───┘
        ▲         │
        └─────────┘
    (podzadania rekurencyjnie)
```

---

## Kluczowe funkcjonalności

### 1. **Podzadania rekurencyjne**
- Zadanie może mieć nieograniczoną liczbę poziomów podzadań
- `parent_id` wskazuje na zadanie nadrzędne
- CASCADE DELETE: usunięcie zadania usuwa wszystkie podzadania

### 2. **Soft delete (miękkie usuwanie)**
- Wszystkie główne tabele mają `deleted_at`
- Usunięte elementy są oznaczane timestamp zamiast fizycznego usuwania
- Możliwość przywrócenia usuniętych elementów

### 3. **Konfigurowalne kolumny**
- Kolumny systemowe (id, title, status) + kolumny użytkownika
- Każda kolumna ma typ (text, lista, data, checkbox, etc.)
- Wartości niestandardowych kolumn w `tasks.custom_data` jako JSON

### 4. **Synchronizacja**
- `synced` - flaga czy zadanie zsynchronizowane
- `server_id` - ID zadania na serwerze po synchronizacji
- Umożliwia offline-first z późniejszą synchronizacją

### 5. **Automatyzacje**
- Automatyczne wypełnianie `completion_date` przy `status = True`
- Archiwizacja po X dniach (ustawienie)
- Przenoszenie ukończonych (ustawienie)

---

## Przykładowe zapytania SQL

### Pobierz wszystkie zadania główne z podzadaniami (1 poziom)
```sql
SELECT t.*, 
       GROUP_CONCAT(st.title) as subtasks
FROM tasks t
LEFT JOIN tasks st ON st.parent_id = t.id AND st.deleted_at IS NULL
WHERE t.user_id = ? 
  AND t.parent_id IS NULL 
  AND t.deleted_at IS NULL
  AND t.archived = 0
GROUP BY t.id
ORDER BY t.position;
```

### Pobierz zadania z tagami
```sql
SELECT t.*, 
       GROUP_CONCAT(tt.name) as tags,
       GROUP_CONCAT(tt.color) as tag_colors
FROM tasks t
LEFT JOIN task_tag_assignments tta ON tta.task_id = t.id
LEFT JOIN task_tags tt ON tt.id = tta.tag_id
WHERE t.user_id = ? AND t.deleted_at IS NULL
GROUP BY t.id;
```

### Znajdź zadania do archiwizacji
```sql
SELECT * FROM tasks
WHERE user_id = ?
  AND status = 1
  AND archived = 0
  AND deleted_at IS NULL
  AND completion_date <= datetime('now', '-30 days');
```

---

## Migracje i wersjonowanie

Baza danych jest automatycznie inicjalizowana przy pierwszym uruchomieniu.
W przyszłości można dodać system migracji do zarządzania zmianami schematu.

**Wersja:** 1.0  
**Data utworzenia:** 2025-11-04  
**Autor:** PRO-Ka-Po Team
