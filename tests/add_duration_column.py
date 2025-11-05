import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

# Sprawdź czy kolumna "czas trwania" już istnieje
existing = cursor.execute("SELECT * FROM task_columns_config WHERE column_id = 'czas_trwania'").fetchone()

if existing:
    print("Kolumna 'czas trwania' już istnieje")
else:
    # Dodaj kolumnę typu czas
    cursor.execute("""
        INSERT INTO task_columns_config 
        (user_id, column_id, position, type, visible_main, visible_bar, default_value, is_system, editable)
        VALUES (1, 'czas_trwania', 100, 'czas', 1, 0, '0', 0, 1)
    """)
    conn.commit()
    print("Dodano kolumnę 'czas_trwania' typu 'czas'")

# Wyświetl wszystkie kolumny typu czas
print("\nKolumny typu 'czas':")
rows = cursor.execute("SELECT column_id, type, default_value FROM task_columns_config WHERE type LIKE '%czas%' OR type LIKE '%time%' OR type LIKE '%duration%'").fetchall()
for r in rows:
    print(f'  {r}')

conn.close()
