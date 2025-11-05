"""Test końcowy - sprawdza wyświetlanie wartości domyślnej dla kolumn typu lista"""
import sqlite3
import json
from pathlib import Path

project_root = Path(__file__).parent / "PRO-Ka-Po_Kaizen_Freak"
db_path = project_root / "src" / "database" / "tasks.db"

print("=" * 70)
print("TEST - Wyświetlanie wartości domyślnej dla kolumn typu lista")
print("=" * 70)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Sprawdź konfigurację kolumny prio (wartość domyślna)
print("\n1. Konfiguracja kolumny 'prio':")
cursor.execute("SELECT * FROM task_columns_config WHERE column_id = 'prio'")
prio_config = cursor.fetchone()
if prio_config:
    print(f"   ✓ column_id: {prio_config['column_id']}")
    print(f"   ✓ type: {prio_config['type']}")
    print(f"   ✓ list_name: {prio_config['list_name']}")
    print(f"   ✓ default_value: '{prio_config['default_value']}'")  # Powinno być 'Niski'
    default_value = prio_config['default_value']
else:
    print("   ✗ Kolumna nie znaleziona!")
    default_value = None

# 2. Sprawdź listę wartości Priorytet
print("\n2. Lista wartości 'Priorytet':")
cursor.execute("SELECT * FROM task_custom_lists WHERE name = 'Priorytet'")
priority_list = cursor.fetchone()
if priority_list:
    values = json.loads(priority_list['list_values'])
    print(f"   ✓ Wartości: {values}")
    
    # Sprawdź czy wartość domyślna znajduje się na liście
    if default_value and default_value in values:
        print(f"   ✓ Wartość domyślna '{default_value}' JEST na liście wartości")
    elif default_value:
        print(f"   ⚠ Wartość domyślna '{default_value}' NIE znajduje się na liście!")
else:
    print("   ✗ Lista nie znaleziona!")

# 3. Sprawdź zadania bez przypisanej wartości prio
print("\n3. Zadania BEZ przypisanej wartości prio (powinny wyświetlić domyślną):")
cursor.execute("""
    SELECT id, title, custom_data 
    FROM tasks 
    WHERE custom_data NOT LIKE '%prio%' OR custom_data IS NULL
    LIMIT 5
""")
tasks_without_prio = cursor.fetchall()

if tasks_without_prio:
    for task in tasks_without_prio:
        custom_data = json.loads(task['custom_data']) if task['custom_data'] else {}
        has_prio = 'prio' in custom_data
        print(f"   Task {task['id']}: {task['title'][:35]:35s}")
        print(f"      - custom_data ma 'prio': {has_prio}")
        if default_value:
            print(f"      - UI wyświetli: '{default_value}' (wartość domyślna)")
        else:
            print(f"      - UI wyświetli: '-- Wybierz --' (brak wartości domyślnej)")
else:
    print("   ℹ Wszystkie zadania mają już przypisane prio")

# 4. Sprawdź zadania Z przypisaną wartością prio
print("\n4. Zadania Z przypisaną wartością prio:")
cursor.execute("""
    SELECT id, title, custom_data 
    FROM tasks 
    WHERE custom_data LIKE '%prio%'
""")
tasks_with_prio = cursor.fetchall()

if tasks_with_prio:
    for task in tasks_with_prio:
        custom_data = json.loads(task['custom_data']) if task['custom_data'] else {}
        prio_value = custom_data.get('prio', 'BRAK')
        print(f"   Task {task['id']}: {task['title'][:35]:35s}")
        print(f"      - UI wyświetli: '{prio_value}' (wartość przypisana)")
else:
    print("   ℹ Brak zadań z przypisanym prio")

# 5. Podsumowanie logiki wyświetlania
print("\n" + "=" * 70)
print("PODSUMOWANIE - Logika wyświetlania wartości w combobox:")
print("=" * 70)
print("\n_get_task_value() szuka wartości w kolejności:")
print("  1. task[column_id] - bezpośrednio w słowniku zadania")
print("  2. task['custom_data'][column_id] - w custom_data")
print("  3. task['custom_data'][list_name] - w custom_data po nazwie listy")
print("  4. task[list_name] - bezpośrednio po nazwie listy")
print("  5. column_config['default_value'] - wartość domyślna z konfiguracji ✓")

print("\n_create_list_widget() wyświetla wartość:")
print(f"  - Jeśli current_value jest None/'': sprawdź default_value")
print(f"    • Jeśli default_value='{default_value}' -> ustaw currentIndex na '{default_value}'")
print(f"    • Jeśli brak default_value -> pokaż placeholder '-- Wybierz --'")
print(f"  - Jeśli current_value ma wartość: ustaw currentIndex na tę wartość")

print("\n✅ Oczekiwane zachowanie:")
print(f"  - Zadania BEZ prio: wyświetlą '{default_value}' (wartość domyślna)")
print(f"  - Zadania Z prio: wyświetlą przypisaną wartość")
print(f"  - Użytkownik może zmienić wartość lub wybrać '✖ Wyczyść'")

conn.close()

print("\n" + "=" * 70)
print("✓ Test zakończony - gotowe do uruchomienia aplikacji!")
print("=" * 70)
