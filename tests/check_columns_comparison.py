#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

# Sprawdź obie kolumny liczbowe
cursor.execute("""
    SELECT id, user_id, column_id, position, type, visible_main, is_system, editable, 
           default_value, display_name, width, alignment, sortable, filterable
    FROM task_columns_config 
    WHERE column_id IN ('liczby', 'Ilość') AND user_id = 1
    ORDER BY column_id
""")

print("=== Porównanie kolumn liczbowych ===\n")
columns = [desc[0] for desc in cursor.description]
for row in cursor.fetchall():
    print(f"column_id: {row[2]}")
    for i, col in enumerate(columns):
        print(f"  {col}: {row[i]}")
    print()

# Sprawdź wszystkie kolumny w tabeli task_columns_config
cursor.execute("PRAGMA table_info(task_columns_config)")
print("\n=== Struktura tabeli task_columns_config ===")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

conn.close()
