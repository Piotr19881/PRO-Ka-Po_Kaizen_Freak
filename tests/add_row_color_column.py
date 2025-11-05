#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Dodaj kolumnę row_color do tabeli tasks
"""
import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

try:
    # Sprawdź czy kolumna już istnieje
    cursor.execute("PRAGMA table_info(tasks)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'row_color' in columns:
        print("✅ Kolumna 'row_color' już istnieje!")
    else:
        # Dodaj kolumnę
        cursor.execute("""
            ALTER TABLE tasks 
            ADD COLUMN row_color TEXT DEFAULT NULL
        """)
        conn.commit()
        print("✅ Dodano kolumnę 'row_color' do tabeli tasks")
    
    # Sprawdź strukturę
    cursor.execute("PRAGMA table_info(tasks)")
    print("\nStruktura tabeli tasks:")
    for col in cursor.fetchall():
        print(f"  {col[1]} ({col[2]})")
        
except Exception as e:
    print(f"❌ Błąd: {e}")
    conn.rollback()
finally:
    conn.close()
