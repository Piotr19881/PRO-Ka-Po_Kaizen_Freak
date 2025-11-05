import sqlite3

db_path = "PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Sprawdź wszystkie kolumny
cursor.execute("""
    SELECT column_id, type, visible_main, is_system, editable, widget_type 
    FROM task_columns_config 
    ORDER BY position
""")

rows = cursor.fetchall()
print(f"\n=== Wszystkie kolumny w task_columns_config ===")
print(f"Znaleziono: {len(rows)} kolumn\n")
for row in rows:
    print(f"column_id: {row[0]}")
    print(f"  type: {row[1]}")
    print(f"  visible_main: {row[2]}")
    print(f"  is_system: {row[3]}")
    print(f"  editable: {row[4]}")
    print(f"  widget_type: {row[5]}")
    print()

conn.close()
