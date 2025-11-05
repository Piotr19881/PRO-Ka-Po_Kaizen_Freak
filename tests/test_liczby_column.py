#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test edycji kolumny liczbowej
"""
import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

# Sprawdź kolumnę "liczby"
cursor.execute("""
    SELECT column_id, type, editable, is_system 
    FROM task_columns_config 
    WHERE column_id = 'liczby' AND user_id = 1
""")

result = cursor.fetchone()
if result:
    print("✅ Kolumna 'liczby' znaleziona:")
    print(f"  column_id: {result[0]}")
    print(f"  type: {result[1]}")
    print(f"  editable: {result[2]}")
    print(f"  is_system: {result[3]}")
    
    # Sprawdź czy są jakieś dane
    cursor.execute("""
        SELECT id, custom_data 
        FROM tasks 
        WHERE user_id = 1 
        LIMIT 5
    """)
    
    print("\n✅ Przykładowe zadania:")
    for task in cursor.fetchall():
        print(f"  Task ID={task[0]}, custom_data={task[1]}")
else:
    print("❌ Kolumna 'liczby' nie została znaleziona!")

conn.close()
