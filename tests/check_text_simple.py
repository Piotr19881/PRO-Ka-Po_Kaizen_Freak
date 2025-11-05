import sqlite3

db_path = "PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("""
    SELECT column_id, type, visible_main, is_system, editable 
    FROM task_columns_config 
    WHERE type='text' 
    ORDER BY position
""")

rows = cursor.fetchall()
print(f"\n=== Kolumny typu 'text' ===")
print(f"Znaleziono: {len(rows)} kolumn")
for row in rows:
    print(f"  - column_id: {row[0]}, type: {row[1]}, visible_main: {row[2]}, is_system: {row[3]}, editable: {row[4]}")

conn.close()
