"""
Test script dla TaskLocalDatabase
Demonstracja użycia bazy danych zadań
"""
from pathlib import Path
import sys

# Dodaj ścieżkę do modułów
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.Modules.task_module.task_local_database import TaskLocalDatabase

def test_task_database():
    """Test podstawowych operacji na bazie danych zadań"""
    
    # Utwórz bazę danych w pamięci (sqlite)
    db_path = Path(__file__).parent.parent.parent / 'data' / 'test_tasks.db'
    db_path.parent.mkdir(exist_ok=True)
    
    db = TaskLocalDatabase(db_path, user_id=1)
    
    print("=" * 60)
    print("TEST 1: Dodawanie tagów")
    print("=" * 60)
    
    tag1_id = db.add_tag("Pilne", "#FF0000")
    tag2_id = db.add_tag("Praca", "#0000FF")
    tag3_id = db.add_tag("Dom", "#00FF00")
    
    print(f"Utworzono tagi: {tag1_id}, {tag2_id}, {tag3_id}")
    
    tags = db.get_tags()
    print(f"\nPobrane tagi ({len(tags)}):")
    for tag in tags:
        print(f"  - {tag['name']}: {tag['color']}")
    
    print("\n" + "=" * 60)
    print("TEST 2: Dodawanie list własnych")
    print("=" * 60)
    
    list1_id = db.add_custom_list("Priorytet", ["Niski", "Średni", "Wysoki", "Krytyczny"])
    list2_id = db.add_custom_list("Status projektu", ["Planowanie", "W trakcie", "Testowanie", "Zakończony"])
    
    print(f"Utworzono listy: {list1_id}, {list2_id}")
    
    lists = db.get_custom_lists()
    print(f"\nPobrane listy ({len(lists)}):")
    for lst in lists:
        print(f"  - {lst['name']}: {lst['values']}")
    
    print("\n" + "=" * 60)
    print("TEST 3: Zapisywanie konfiguracji kolumn")
    print("=" * 60)
    
    columns_config = [
        {
            'id': 'id',
            'position': 0,
            'type': 'int',
            'visible_main': False,
            'visible_bar': False,
            'default_value': '',
            'system': True,
            'editable': False
        },
        {
            'id': 'Zadanie',
            'position': 1,
            'type': 'text',
            'visible_main': True,
            'visible_bar': True,
            'default_value': '',
            'system': True,
            'editable': False
        },
        {
            'id': 'Priorytet',
            'position': 2,
            'type': 'lista',
            'visible_main': True,
            'visible_bar': True,
            'default_value': 'Średni',
            'list_name': 'Priorytet',
            'system': False,
            'editable': True
        }
    ]
    
    success = db.save_columns_config(columns_config)
    print(f"Zapisano konfigurację kolumn: {success}")
    
    loaded_config = db.load_columns_config()
    print(f"\nPobrana konfiguracja ({len(loaded_config)} kolumn):")
    for col in loaded_config:
        print(f"  - {col['column_id']} (pos={col['position']}, type={col['type']})")
    
    print("\n" + "=" * 60)
    print("TEST 4: Dodawanie zadań głównych")
    print("=" * 60)
    
    task1_id = db.add_task(
        title="Zaimplementować moduł zadań",
        custom_data={"Priorytet": "Wysoki"},
        tags=[tag1_id, tag2_id]
    )
    
    task2_id = db.add_task(
        title="Przygotować dokumentację",
        custom_data={"Priorytet": "Średni"},
        tags=[tag2_id]
    )
    
    task3_id = db.add_task(
        title="Zrobić zakupy",
        custom_data={"Priorytet": "Niski"},
        tags=[tag3_id]
    )
    
    print(f"Utworzono zadania: {task1_id}, {task2_id}, {task3_id}")
    
    print("\n" + "=" * 60)
    print("TEST 5: Dodawanie podzadań")
    print("=" * 60)
    
    subtask1_id = db.add_task(
        title="Stworzyć schemat bazy danych",
        parent_id=task1_id,
        custom_data={"Priorytet": "Wysoki"},
        tags=[tag1_id]
    )
    
    subtask2_id = db.add_task(
        title="Zaimplementować TaskLocalDatabase",
        parent_id=task1_id,
        custom_data={"Priorytet": "Wysoki"},
        status=True  # Ukończone
    )
    
    subtask3_id = db.add_task(
        title="Napisać testy jednostkowe",
        parent_id=task1_id,
        custom_data={"Priorytet": "Średni"}
    )
    
    print(f"Utworzono podzadania: {subtask1_id}, {subtask2_id}, {subtask3_id}")
    
    print("\n" + "=" * 60)
    print("TEST 6: Pobieranie zadań z podzadaniami")
    print("=" * 60)
    
    tasks = db.get_tasks(include_subtasks=True)
    print(f"\nPobrano {len(tasks)} zadań głównych:")
    
    for task in tasks:
        status_icon = "✓" if task['status'] else "○"
        print(f"\n{status_icon} {task['title']}")
        print(f"  ID: {task['id']}, Pozycja: {task['position']}")
        print(f"  Custom data: {task.get('custom_data', {})}")
        print(f"  Tagi: {[tag['name'] for tag in task.get('tags', [])]}")
        
        if task.get('subtasks'):
            print(f"  Podzadania ({len(task['subtasks'])}):")
            for subtask in task['subtasks']:
                sub_status = "✓" if subtask['status'] else "○"
                print(f"    {sub_status} {subtask['title']}")
                if subtask.get('completion_date'):
                    print(f"      Ukończono: {subtask['completion_date']}")
    
    print("\n" + "=" * 60)
    print("TEST 7: Aktualizacja zadania")
    print("=" * 60)
    
    # Oznacz zadanie jako ukończone
    success = db.update_task(task2_id, status=True)
    print(f"Oznaczono zadanie {task2_id} jako ukończone: {success}")
    
    # Zmień priorytet
    success = db.update_task(task3_id, custom_data={"Priorytet": "Wysoki"})
    print(f"Zmieniono priorytet zadania {task3_id}: {success}")
    
    print("\n" + "=" * 60)
    print("TEST 8: Zapisywanie ustawień")
    print("=" * 60)
    
    settings = {
        'auto_archive_enabled': True,
        'auto_archive_after_days': 30,
        'auto_move_completed': False
    }
    
    for key, value in settings.items():
        db.save_setting(key, value)
    
    print("Zapisano ustawienia:")
    for key in settings.keys():
        value = db.get_setting(key)
        print(f"  - {key}: {value}")
    
    print("\n" + "=" * 60)
    print("TEST 9: Usuwanie (soft delete)")
    print("=" * 60)
    
    # Usuń podzadanie
    success = db.delete_task(subtask3_id, soft_delete=True)
    print(f"Usunięto podzadanie {subtask3_id}: {success}")
    
    # Sprawdź czy podzadanie zniknęło
    tasks = db.get_tasks(include_subtasks=True)
    task1 = next(t for t in tasks if t['id'] == task1_id)
    print(f"Liczba podzadań zadania '{task1['title']}': {len(task1.get('subtasks', []))}")
    
    print("\n" + "=" * 60)
    print("WSZYSTKIE TESTY ZAKOŃCZONE POMYŚLNIE!")
    print("=" * 60)
    print(f"\nBaza danych znajduje się w: {db_path}")
    print("Możesz ją otworzyć w DB Browser for SQLite aby zobaczyć strukturę.\n")


if __name__ == "__main__":
    test_task_database()
