"""Test dodawania kolumny typu data do bazy danych"""
import sqlite3
import json
from pathlib import Path

project_root = Path(__file__).parent / "PRO-Ka-Po_Kaizen_Freak"
db_path = project_root / "src" / "database" / "tasks.db"

print("=" * 70)
print("DODAWANIE KOLUMNY TYPU DATA")
print("=" * 70)

conn = sqlite3.connect(str(db_path))
conn.row_factory = sqlite3.Row
cursor = conn.cursor()

# 1. Sprawdź czy kolumna już istnieje
print("\n1. Sprawdzanie istniejących kolumn typu data...")
cursor.execute("SELECT * FROM task_columns_config WHERE type IN ('date', 'data')")
existing_date_columns = cursor.fetchall()

if existing_date_columns:
    print(f"   Znaleziono {len(existing_date_columns)} kolumn typu data:")
    for col in existing_date_columns:
        print(f"   - {col['column_id']}: type={col['type']}, default={col['default_value']}")
else:
    print("   Brak kolumn typu data")

# 2. Dodaj przykładową kolumnę "termin" jeśli nie istnieje
column_id = 'termin'
cursor.execute("SELECT * FROM task_columns_config WHERE column_id = ?", (column_id,))
termin_col = cursor.fetchone()

if termin_col:
    print(f"\n2. Kolumna '{column_id}' już istnieje")
    print(f"   ID: {termin_col['id']}")
    print(f"   Typ: {termin_col['type']}")
    print(f"   Wartość domyślna: {termin_col['default_value']}")
else:
    print(f"\n2. Dodawanie nowej kolumny '{column_id}'...")
    
    # Pobierz maksymalną pozycję
    cursor.execute("SELECT MAX(position) as max_pos FROM task_columns_config")
    max_pos = cursor.fetchone()['max_pos'] or 0
    
    # Wstaw nową kolumnę
    cursor.execute("""
        INSERT INTO task_columns_config 
        (user_id, column_id, type, visible_main, visible_bar, position, is_system, default_value)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        1,  # user_id
        column_id,  # column_id
        'date',  # type (lub 'data' po polsku)
        1,  # visible_main
        0,  # visible_bar
        max_pos + 1,  # position
        0,  # is_system (kolumna użytkownika)
        ''  # default_value (pusta data domyślnie)
    ))
    conn.commit()
    print(f"   ✓ Kolumna '{column_id}' została dodana!")

# 3. Sprawdź końcowy stan
print("\n3. Weryfikacja - wszystkie kolumny typu data:")
cursor.execute("SELECT * FROM task_columns_config WHERE type IN ('date', 'data', 'datetime')")
all_date_columns = cursor.fetchall()

for col in all_date_columns:
    print(f"   - {col['column_id']}:")
    print(f"     • type: {col['type']}")
    print(f"     • visible_main: {col['visible_main']}")
    print(f"     • position: {col['position']}")
    print(f"     • default_value: '{col['default_value']}'")

# 4. Dodaj przykładową wartość daty dla pierwszego zadania
print("\n4. Ustawianie przykładowej daty dla zadania #1...")
cursor.execute("SELECT id, title, custom_data FROM tasks WHERE id = 1")
task1 = cursor.fetchone()

if task1:
    custom_data = json.loads(task1['custom_data']) if task1['custom_data'] else {}
    
    if 'termin' not in custom_data:
        from datetime import date, timedelta
        # Ustaw termin na dzisiaj + 7 dni
        deadline = (date.today() + timedelta(days=7)).strftime('%Y-%m-%d')
        custom_data['termin'] = deadline
        
        cursor.execute(
            "UPDATE tasks SET custom_data = ? WHERE id = 1",
            (json.dumps(custom_data, ensure_ascii=False),)
        )
        conn.commit()
        print(f"   ✓ Ustawiono termin dla zadania #1: {deadline}")
    else:
        print(f"   Zadanie #1 już ma termin: {custom_data['termin']}")

conn.close()

print("\n" + "=" * 70)
print("✓ KONFIGURACJA ZAKOŃCZONA")
print("=" * 70)
print("\nAby przetestować:")
print("1. Uruchom aplikację: python main.py")
print("2. Znajdź kolumnę 'termin' w widoku zadań")
print("3. Kliknij dwukrotnie na komórkę z datą")
print("4. Powinien otworzyć się kalendarz do wyboru daty")
print("5. Wybierz datę i kliknij OK - data zostanie zapisana")
print("6. Możesz również kliknąć 'Wyczyść' aby usunąć datę")
print("\n✓ Gotowe do testowania!")
