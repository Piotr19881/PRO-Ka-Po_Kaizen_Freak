"""Testuje ustawianie i odczytywanie wartości prio dla zadań"""
import sqlite3
import json
import sys
from pathlib import Path

# Dodaj ścieżkę do modułów projektu
project_root = Path(__file__).parent / "PRO-Ka-Po_Kaizen_Freak"
sys.path.insert(0, str(project_root))

db_path = project_root / "src" / "database" / "tasks.db"
print(f"Otwieranie bazy: {db_path}")
print(f"Plik istnieje: {db_path.exists()}\n")

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Sprawdź aktualne wartości custom_data dla kilku zadań
print("=== Sprawdzanie aktualnych wartości custom_data ===")
cursor.execute("SELECT id, title, custom_data FROM tasks LIMIT 5")
tasks = cursor.fetchall()

for task in tasks:
    task_id = task['id']
    title = task['title']
    custom_data_str = task['custom_data']
    custom_data = json.loads(custom_data_str) if custom_data_str else {}
    prio_value = custom_data.get('prio', 'BRAK')
    print(f"Task {task_id}: {title[:30]:30s} | prio: {prio_value}")

# 2. Ustaw wartość prio dla pierwszego zadania (jeśli brak)
print("\n=== Ustawianie wartości prio dla pierwszego zadania ===")
if tasks:
    first_task = tasks[0]
    task_id = first_task['id']
    custom_data_str = first_task['custom_data']
    custom_data = json.loads(custom_data_str) if custom_data_str else {}
    
    if 'prio' not in custom_data:
        print(f"Zadanie {task_id} nie ma wartości prio. Ustawiam 'Wysoki'...")
        custom_data['prio'] = 'Wysoki'
        cursor.execute(
            "UPDATE tasks SET custom_data = ? WHERE id = ?",
            (json.dumps(custom_data, ensure_ascii=False), task_id)
        )
        conn.commit()
        print("✓ Wartość zapisana")
    else:
        print(f"Zadanie {task_id} już ma wartość prio: {custom_data['prio']}")

# 3. Weryfikuj zapis
print("\n=== Weryfikacja zapisu ===")
cursor.execute("SELECT id, title, custom_data FROM tasks WHERE id = ?", (task_id,))
updated_task = cursor.fetchone()
custom_data = json.loads(updated_task['custom_data']) if updated_task['custom_data'] else {}
print(f"Task {updated_task['id']}: {updated_task['title'][:40]}")
print(f"custom_data: {custom_data}")
print(f"prio value: {custom_data.get('prio', 'BRAK')}")

# 4. Sprawdź konfigurację kolumny prio
print("\n=== Konfiguracja kolumny prio ===")
cursor.execute("SELECT * FROM task_columns_config WHERE column_id = 'prio'")
prio_config = cursor.fetchone()
if prio_config:
    print(f"column_id: {prio_config['column_id']}")
    print(f"type: {prio_config['type']}")
    print(f"list_name: {prio_config['list_name']}")
    print(f"default_value: {prio_config['default_value']}")
    print(f"visible_main: {prio_config['visible_main']}")
else:
    print("Kolumna prio nie została znaleziona w konfiguracji")

# 5. Sprawdź wartości listy Priorytet
print("\n=== Wartości listy Priorytet ===")
cursor.execute("PRAGMA table_info(task_custom_lists)")
columns = cursor.fetchall()
print(f"Kolumny w task_custom_lists: {[col['name'] for col in columns]}")

cursor.execute("SELECT * FROM task_custom_lists WHERE name = 'Priorytet'")
priority_list = cursor.fetchone()
if priority_list:
    print(f"Lista: {priority_list['name']}")
    # Sprawdź, która kolumna zawiera wartości (może być 'values' lub 'list_values')
    for key in priority_list.keys():
        if 'value' in key.lower():
            values_str = priority_list[key]
            values = json.loads(values_str) if values_str else []
            print(f"Wartości ({key}): {values}")
else:
    print("Lista Priorytet nie została znaleziona")

conn.close()
print("\n✓ Test zakończony")
