import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

# Sprawdź strukturę tabeli
cursor.execute("PRAGMA table_info(task_columns_config)")
columns = cursor.fetchall()
print("=== Struktura tabeli task_columns_config ===")
for col in columns:
    print(f"  {col[1]} ({col[2]}) - NOT NULL: {col[3]}, DEFAULT: {col[4]}")

# Sprawdź istniejące kolumny użytkownika (is_system=0)
cursor.execute("SELECT * FROM task_columns_config WHERE is_system=0 LIMIT 3")
user_cols = cursor.fetchall()
print(f"\n=== Przykładowe kolumny użytkownika (is_system=0) ===")
for row in user_cols:
    print(row)

conn.close()
