import sqlite3
import json

# Użyj właściwej bazy danych
conn = sqlite3.connect('src/database/tasks.db')
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

print("=== Sprawdzanie wartości kolumny prio w zadaniach ===\n")

# Pobierz kilka zadań i sprawdź ich custom_data
cursor.execute("""
    SELECT id, title, custom_data 
    FROM tasks 
    WHERE deleted_at IS NULL
    LIMIT 10
""")

tasks = cursor.fetchall()
print(f"Znaleziono {len(tasks)} zadań:\n")

for task in tasks:
    print(f"Zadanie #{task['id']}: {task['title'][:50]}")
    if task['custom_data']:
        try:
            custom_data = json.loads(task['custom_data'])
            print(f"  custom_data: {json.dumps(custom_data, indent=4, ensure_ascii=False)}")
            
            # Sprawdź czy jest prio
            if 'prio' in custom_data:
                print(f"  ✓ Ma wartość prio: '{custom_data['prio']}'")
            elif 'Priorytet' in custom_data:
                print(f"  ✓ Ma wartość Priorytet: '{custom_data['Priorytet']}'")
            else:
                print(f"  ✗ Brak wartości prio/Priorytet")
        except json.JSONDecodeError:
            print(f"  custom_data (raw): {task['custom_data']}")
    else:
        print(f"  Brak custom_data")
    print()

conn.close()

conn.close()
