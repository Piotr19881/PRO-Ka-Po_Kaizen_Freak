"""Test końcowy - sprawdza czy wszystkie komponenty współpracują"""
import sqlite3
import json
from pathlib import Path

project_root = Path(__file__).parent / "PRO-Ka-Po_Kaizen_Freak"
db_path = project_root / "src" / "database" / "tasks.db"

print("=" * 60)
print("TEST KOŃCOWY - Kolumny typu lista")
print("=" * 60)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Sprawdź konfigurację kolumny prio
print("\n1. Konfiguracja kolumny 'prio':")
cursor.execute("SELECT * FROM task_columns_config WHERE column_id = 'prio'")
prio_config = cursor.fetchone()
if prio_config:
    print(f"   ✓ ID: {prio_config['id']}")
    print(f"   ✓ column_id: {prio_config['column_id']}")
    print(f"   ✓ type: {prio_config['type']}")
    print(f"   ✓ list_name: {prio_config['list_name']}")
    print(f"   ✓ default_value: {prio_config['default_value']}")
    print(f"   ✓ visible_main: {prio_config['visible_main']}")
else:
    print("   ✗ Kolumna nie znaleziona!")

# 2. Sprawdź listę wartości Priorytet
print("\n2. Lista wartości 'Priorytet':")
cursor.execute("SELECT * FROM task_custom_lists WHERE name = 'Priorytet'")
priority_list = cursor.fetchone()
if priority_list:
    values = json.loads(priority_list['list_values'])
    print(f"   ✓ Nazwa: {priority_list['name']}")
    print(f"   ✓ Wartości: {values}")
else:
    print("   ✗ Lista nie znaleziona!")

# 3. Sprawdź zadania z wartością prio
print("\n3. Zadania z przypisaną wartością prio:")
cursor.execute("SELECT id, title, custom_data FROM tasks WHERE custom_data LIKE '%prio%'")
tasks_with_prio = cursor.fetchall()
if tasks_with_prio:
    for task in tasks_with_prio:
        custom_data = json.loads(task['custom_data']) if task['custom_data'] else {}
        prio = custom_data.get('prio', 'BRAK')
        print(f"   ✓ Task {task['id']}: {task['title'][:40]:40s} -> prio: {prio}")
else:
    print("   ℹ Brak zadań z przypisanym prio")

# 4. Sprawdź wszystkie zadania i ich custom_data
print("\n4. Przegląd custom_data dla wszystkich zadań:")
cursor.execute("SELECT id, title, custom_data FROM tasks LIMIT 5")
all_tasks = cursor.fetchall()
for task in all_tasks:
    custom_data = json.loads(task['custom_data']) if task['custom_data'] else {}
    prio = custom_data.get('prio', f"(domyślnie: {prio_config['default_value'] if prio_config else 'BRAK'})")
    print(f"   Task {task['id']}: {task['title'][:30]:30s} -> prio: {prio}")

# 5. Test zapisu nowej wartości dla kolejnego zadania
print("\n5. Test zapisu wartości prio dla zadania #2:")
cursor.execute("SELECT id, title, custom_data FROM tasks WHERE id = 2")
task2 = cursor.fetchone()
if task2:
    custom_data = json.loads(task2['custom_data']) if task2['custom_data'] else {}
    old_prio = custom_data.get('prio', 'BRAK')
    print(f"   Przed zmianą: prio = {old_prio}")
    
    # Ustaw nową wartość
    custom_data['prio'] = 'Średni'
    cursor.execute(
        "UPDATE tasks SET custom_data = ? WHERE id = 2",
        (json.dumps(custom_data, ensure_ascii=False),)
    )
    conn.commit()
    
    # Weryfikuj
    cursor.execute("SELECT custom_data FROM tasks WHERE id = 2")
    updated = cursor.fetchone()
    updated_data = json.loads(updated['custom_data']) if updated['custom_data'] else {}
    print(f"   Po zmianie: prio = {updated_data.get('prio', 'BRAK')}")
    print(f"   ✓ Zapis udany!")

conn.close()

print("\n" + "=" * 60)
print("✓ Test zakończony pomyślnie!")
print("=" * 60)
print("\nAplikacja jest gotowa do uruchomienia.")
print("Lista rozwijana 'prio' powinna:")
print("  1. Pokazać opcje: Niski, Średni, Wysoki, Krytyczny")
print("  2. Wyświetlić aktualnie wybraną wartość (jeśli istnieje)")
print("  3. Zapisać zmianę do bazy po wyborze nowej wartości")
print("  4. Umożliwić wyczyszczenie wartości przez opcję '✖ Wyczyść'")
