"""Test funkcji pobierania wartości dla kolumny typu lista"""
import sys
from pathlib import Path

# Dodaj ścieżkę do modułów projektu
project_root = Path(__file__).parent / "PRO-Ka-Po_Kaizen_Freak"
sys.path.insert(0, str(project_root))

# Import TaskLocalDatabase
from src.Modules.task_module.task_local_database import TaskLocalDatabase

# Inicjalizuj bazę danych
db_path = project_root / "src" / "database" / "tasks.db"
db = TaskLocalDatabase(str(db_path), user_id=1)

print("=== Test pobierania list własnych ===")
custom_lists = db.load_custom_lists()
print(f"Liczba list: {len(custom_lists)}")
for custom_list in custom_lists:
    print(f"  - {custom_list['name']}: {custom_list['values']}")

print("\n=== Test get_custom_lists (inna metoda) ===")
custom_lists2 = db.get_custom_lists()
print(f"Liczba list: {len(custom_lists2)}")
for custom_list in custom_lists2:
    print(f"  - {custom_list['name']}: {custom_list['values']}")

print("\n=== Test pobierania zadania z wartością prio ===")
task = db.get_task_by_id(1)
if task:
    print(f"Task ID: {task['id']}")
    print(f"Title: {task['title']}")
    print(f"custom_data: {task.get('custom_data', {})}")
    
    # Symuluj logikę _get_task_value z task_view.py
    column_id = 'prio'
    custom_data = task.get('custom_data', {})
    
    # Sprawdź różne ścieżki pobierania wartości
    value = None
    if column_id in task:
        value = task[column_id]
        print(f"✓ Znaleziono wartość w task['{column_id}']: {value}")
    elif custom_data and column_id in custom_data:
        value = custom_data[column_id]
        print(f"✓ Znaleziono wartość w custom_data['{column_id}']: {value}")
    else:
        print(f"✗ Nie znaleziono wartości dla kolumny '{column_id}'")
        print(f"  Dostępne klucze w task: {list(task.keys())}")
        if custom_data:
            print(f"  Dostępne klucze w custom_data: {list(custom_data.keys())}")

print("\n✓ Test zakończony")
