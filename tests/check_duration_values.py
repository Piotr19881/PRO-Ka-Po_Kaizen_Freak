"""
Sprawdź wartości czasu trwania w bazie danych
"""
import sqlite3
import json

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

print("Zadania z wartościami w custom_data:")
rows = cursor.execute("""
    SELECT id, title, custom_data 
    FROM tasks 
    WHERE custom_data IS NOT NULL AND custom_data != '{}'
    ORDER BY id
""").fetchall()

for row in rows:
    task_id, title, custom_data_str = row
    print(f"\nTask ID: {task_id}")
    print(f"  Title: {title}")
    try:
        custom_data = json.loads(custom_data_str) if custom_data_str else {}
        print(f"  Custom Data: {custom_data}")
        if 'czas_trwania' in custom_data:
            minutes = custom_data['czas_trwania']
            print(f"  Czas trwania: {minutes} min")
    except json.JSONDecodeError as e:
        print(f"  Error parsing custom_data: {e}")

conn.close()
