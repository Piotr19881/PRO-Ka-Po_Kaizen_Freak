import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

print("Kolumny typu 'text':")
rows = cursor.execute("""
    SELECT column_id, type, visible_main, is_system, editable 
    FROM task_columns_config 
    WHERE type = 'text'
    ORDER BY position
""").fetchall()

for r in rows:
    print(f'  {r}')

conn.close()
