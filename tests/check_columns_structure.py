#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

# Sprawdź strukturę tabeli
cursor.execute("PRAGMA table_info(task_columns_config)")
print("=== Struktura tabeli task_columns_config ===")
for col in cursor.fetchall():
    print(f"  {col[1]} ({col[2]})")

# Sprawdź obie kolumny liczbowe
cursor.execute("""
    SELECT * FROM task_columns_config 
    WHERE column_id IN ('liczby', 'Ilość') AND user_id = 1
    ORDER BY column_id
""")

print("\n=== Porównanie kolumn liczbowych ===\n")
columns = [desc[0] for desc in cursor.description]
for row in cursor.fetchall():
    print(f"column_id: {row[columns.index('column_id')]}")
    for i, col in enumerate(columns):
        print(f"  {col}: {row[i]}")
    print()

conn.close()
