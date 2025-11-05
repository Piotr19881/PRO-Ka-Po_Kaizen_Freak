#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

try:
    # Usuń kolumnę "Ilość"
    cursor.execute("""
        DELETE FROM task_columns_config 
        WHERE column_id = 'Ilość' AND user_id = 1
    """)
    
    conn.commit()
    print("✅ Usunięto kolumnę 'Ilość'")
    
except Exception as e:
    print(f"❌ Błąd: {e}")
    conn.rollback()
finally:
    conn.close()
