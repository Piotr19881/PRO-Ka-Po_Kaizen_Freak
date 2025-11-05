import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

# Dodaj testową kolumnę tekstową użytkownika
cursor.execute("""
    INSERT INTO task_columns_config 
    (column_id, type, visible_main, default_value, is_system, editable, position)
    VALUES (?, ?, ?, ?, ?, ?, ?)
""", ('Notatka', 'text', 1, '', 0, 1, 100))

conn.commit()
print("✅ Dodano kolumnę niestandardową 'Notatka' (type=text, is_system=0, editable=1)")
print("   Teraz możesz podwójnie kliknąć na komórkę 'Notatka' aby otworzyć dialog tekstowy!")

conn.close()
