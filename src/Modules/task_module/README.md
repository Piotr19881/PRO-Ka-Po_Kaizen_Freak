# Moduł Zadań - Task Module

## Przegląd

Moduł zadań PRO-Ka-Po to kompleksowy system zarządzania zadaniami z obsługą:
- ✅ Konfigurowalnymi kolumnami
- ✅ Podzadaniami (nieograniczona głębokość)
- ✅ Tagami z kolorami
- ✅ Listami własnymi użytkownika
- ✅ Archiwizacją i miękkimi usunięciami
- ✅ Synchronizacją z serwerem

## Struktura

```
src/Modules/task_module/
├── __init__.py                  # Eksporty modułu
├── task_logic.py                # Logika biznesowa (in-memory)
├── task_local_database.py       # Manager lokalnej bazy SQLite
└── README.md                    # Ten plik
```

## Komponenty

### 1. TaskLocalDatabase
Manager lokalnej bazy danych SQLite z pełną obsługą CRUD.

**Inicjalizacja:**
```python
from pathlib import Path
from src.Modules.task_module.task_local_database import TaskLocalDatabase

db_path = Path("data/tasks.db")
db = TaskLocalDatabase(db_path, user_id=1)
```

**Podstawowe operacje:**

#### Zarządzanie tagami
```python
# Dodaj tag
tag_id = db.add_tag("Pilne", "#FF0000")

# Pobierz tagi
tags = db.get_tags()

# Zaktualizuj tag
db.update_tag(tag_id, color="#FF00FF")

# Usuń tag (soft delete)
db.delete_tag(tag_id)
```

#### Zarządzanie listami własnymi
```python
# Dodaj listę
list_id = db.add_custom_list("Priorytet", ["Niski", "Średni", "Wysoki"])

# Pobierz listy
lists = db.get_custom_lists()

# Zaktualizuj listę
db.update_custom_list(list_id, values=["Niski", "Średni", "Wysoki", "Krytyczny"])
```

#### Zarządzanie zadaniami
```python
# Dodaj zadanie główne
task_id = db.add_task(
    title="Zaimplementować moduł zadań",
    custom_data={"Priorytet": "Wysoki", "Kategoria": "Rozwój"},
    tags=[tag_id],
    alarm_date="2025-11-10 10:00:00"
)

# Dodaj podzadanie
subtask_id = db.add_task(
    title="Stworzyć schemat bazy danych",
    parent_id=task_id,
    custom_data={"Priorytet": "Wysoki"}
)

# Pobierz zadania z podzadaniami
tasks = db.get_tasks(include_subtasks=True)

# Oznacz jako ukończone
db.update_task(task_id, status=True)
# completion_date zostanie automatycznie wypełniona!

# Usuń zadanie (soft delete)
db.delete_task(task_id)
```

#### Konfiguracja kolumn
```python
# Zapisz konfigurację kolumn
columns = [
    {
        'id': 'Zadanie',
        'position': 0,
        'type': 'text',
        'visible_main': True,
        'visible_bar': True,
        'default_value': '',
        'system': True,
        'editable': False
    },
    {
        'id': 'Priorytet',
        'position': 1,
        'type': 'lista',
        'visible_main': True,
        'visible_bar': True,
        'default_value': 'Średni',
        'list_name': 'Priorytet',
        'system': False,
        'editable': True
    }
]

db.save_columns_config(columns)

# Wczytaj konfigurację
loaded_columns = db.load_columns_config()
```

#### Ustawienia
```python
# Zapisz ustawienie
db.save_setting('auto_archive_enabled', True)
db.save_setting('auto_archive_after_days', 30)

# Pobierz ustawienie
enabled = db.get_setting('auto_archive_enabled', default=False)
```

### 2. TaskLogic
Logika biznesowa (obecnie in-memory, do integracji z TaskLocalDatabase).

```python
from src.Modules.task_module.task_logic import TaskLogic

logic = TaskLogic(db=db)
tasks = logic.load_tasks()
filtered = logic.filter_tasks(text="moduł", status="W trakcie")
```

## UI Components

### TaskView
Główny widok zadań z filtrowaniem i tabelą.

### TaskConfigDialog
Dialog konfiguracji:
- Zarządzanie kolumnami
- Zarządzanie tagami
- Zarządzanie listami własnymi
- Ustawienia ogólne

## Schemat bazy danych

Szczegółowy opis schematu znajduje się w `docs/TASK_DATABASE_SCHEMA.md`.

**Główne tabele:**
- `tasks` - zadania i podzadania
- `task_columns_config` - konfiguracja kolumn
- `task_tags` - tagi
- `task_custom_lists` - listy własne
- `task_tag_assignments` - przypisanie tagów do zadań
- `task_settings` - ustawienia modułu

## Testowanie

Uruchom skrypt testowy:
```bash
python test_task_database.py
```

Utworzy on przykładową bazę danych z:
- 3 tagami (Pilne, Praca, Dom)
- 2 listami własnymi (Priorytet, Status projektu)
- 3 zadaniami głównymi
- 3 podzadaniami
- Demonstracją wszystkich operacji CRUD

## Funkcjonalności specjalne

### 1. Podzadania rekurencyjne
Nieograniczona głębokość zagnieżdżenia:
```
Zadanie główne
├── Podzadanie 1
│   ├── Pod-podzadanie 1.1
│   └── Pod-podzadanie 1.2
└── Podzadanie 2
```

### 2. Miękkie usuwanie (Soft Delete)
Usunięte elementy mają ustawiony `deleted_at` zamiast fizycznego usunięcia.
Możliwość przywrócenia poprzez `UPDATE deleted_at = NULL`.

### 3. Automatyczne wypełnianie daty ukończenia
Gdy `status` zmienia się na `True`, `completion_date` jest automatycznie ustawiana na aktualny czas.

### 4. Custom data jako JSON
Dane niestandardowych kolumn przechowywane w formacie JSON:
```json
{
  "Priorytet": "Wysoki",
  "Kategoria": "Rozwój",
  "Data realizacji": "2025-11-10",
  "Koszt": "1500.00"
}
```

### 5. Archiwizacja
- Ręczna: `update_task(task_id, archived=True)`
- Automatyczna: według ustawień użytkownika (po X dniach)

## Integracja z innymi modułami

### Moduł Notatek
```python
# Powiąż zadanie z notatką
db.update_task(task_id, note_id=123)
```

### Moduł Kanban
```python
# Powiąż zadanie z kartą Kanban
db.update_task(task_id, kanban_id=456)
```

### Moduł Alarmów
```python
# Ustaw alarm/przypomnienie
db.update_task(task_id, alarm_date="2025-11-10 10:00:00")
```

## TODO / Przyszłe rozszerzenia

- [ ] Synchronizacja z serwerem (API)
- [ ] Import/Export do CSV, JSON
- [ ] Szablony zadań
- [ ] Powtarzające się zadania (recurring tasks)
- [ ] Załączniki do zadań
- [ ] Historia zmian (audit log)
- [ ] Współdzielone zadania (multi-user)
- [ ] Statystyki i raporty

## Licencja

© 2025 PRO-Ka-Po Team. Wszystkie prawa zastrzeżone.
