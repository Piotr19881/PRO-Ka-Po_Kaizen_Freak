import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

# Sprawdź kolumny typu text, które NIE są systemowe
cursor.execute("""
    SELECT column_id, type, visible_main, is_system, editable, position 
    FROM task_columns_config 
    WHERE type='text' 
    ORDER BY position
""")

rows = cursor.fetchall()
print(f"\n=== Wszystkie kolumny typu 'text' ===")
print(f"Znaleziono: {len(rows)} kolumn\n")
for row in rows:
    print(f"  column_id: {row[0]}")
    print(f"  type: {row[1]}")
    print(f"  visible_main: {row[2]}")
    print(f"  is_system: {row[3]} {'(SYSTEMOWA)' if row[3] else '(UŻYTKOWNIKA)'}")
    print(f"  editable: {row[4]}")
    print(f"  position: {row[5]}")
    print()

# Kolumny niestandardowe użytkownika
cursor.execute("""
    SELECT column_id, type, visible_main, editable 
    FROM task_columns_config 
    WHERE type='text' AND is_system=0 AND editable=1
    ORDER BY position
""")

user_cols = cursor.fetchall()
print(f"\n=== Kolumny NIESTANDARDOWE użytkownika (type='text', is_system=0, editable=1) ===")
print(f"Znaleziono: {len(user_cols)} kolumn\n")
for row in user_cols:
    print(f"  ✓ {row[0]} (type={row[1]}, visible={row[2]}, editable={row[3]})")

conn.close()
