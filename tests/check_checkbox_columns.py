#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Sprawdź kolumny checkbox użytkownika
"""
import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

# Znajdź kolumny checkbox
cursor.execute("""
    SELECT column_id, type, is_system, editable, position
    FROM task_columns_config 
    WHERE user_id = 1 AND type = 'checkbox'
    ORDER BY position
""")

print("=== Kolumny checkbox ===\n")
results = cursor.fetchall()
for row in results:
    system_status = "SYSTEMOWA" if row[2] == 1 else "UŻYTKOWNIKA"
    print(f"  {row[0]}: type={row[1]}, {system_status}, editable={row[3]}, position={row[4]}")

if not results:
    print("  Brak kolumn checkbox")

# Sprawdź przykładowe dane
print("\n=== Przykładowe dane custom_data ===")
cursor.execute("""
    SELECT id, custom_data 
    FROM tasks 
    WHERE user_id = 1 
    LIMIT 3
""")

for task in cursor.fetchall():
    print(f"  Task ID={task[0]}: {task[1]}")

conn.close()
