import requests
import json
import sqlite3
from pathlib import Path

# Połącz się z lokalną bazą
db_path = Path.home() / ".pro_ka_po" / "pomodoro.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Pobierz pierwszą niezsynchronizowaną sesję
cursor.execute("""
    SELECT id, user_id, topic_id, session_date, started_at, ended_at,
           work_duration, short_break_duration, long_break_duration,
           actual_work_time, actual_break_time, session_type, status,
           pomodoro_count, notes, tags
    FROM session_logs 
    WHERE is_synced = 0 
    LIMIT 1
""")

row = cursor.fetchone()
if not row:
    print("Brak niezzsynchronizowanych sesji")
    conn.close()
    exit(0)

# Przygotuj dane
tags_value = row[15]
if tags_value:
    import json as json_lib
    try:
        tags_list = json_lib.loads(tags_value) if isinstance(tags_value, str) else tags_value
    except:
        tags_list = []
else:
    tags_list = []

session_data = {
    "id": row[0],
    "local_id": row[0],  # Używamy id jako local_id
    "user_id": row[1],
    "topic_id": row[2],
    "session_date": row[3],
    "started_at": row[4],
    "ended_at": row[5],
    "work_duration": row[6],
    "short_break_duration": row[7],
    "long_break_duration": row[8],
    "actual_work_time": row[9],
    "actual_break_time": row[10],
    "session_type": row[11],
    "status": row[12],
    "pomodoro_count": row[13],
    "notes": row[14],
    "tags": tags_list,
    "version": 1,
    "last_modified": row[4]  # Używamy started_at jako last_modified
}

conn.close()

print("Sesja do synchronizacji:")
print(json.dumps(session_data, indent=2))

# Wyślij do API
url = "http://127.0.0.1:8000/api/pomodoro/sessions"
token_file = r"C:\Users\probu\Desktop\Aplikacje komercyjne\PRO-Ka-Po_Kaizen_Freak\PRO-Ka-Po_Kaizen_Freak\data\tokens.json"

with open(token_file, 'r') as f:
    tokens = json.load(f)
    access_token = tokens.get('access_token')

headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

print(f"\nWysyłam POST {url}")
response = requests.post(url, json=session_data, headers=headers)

print(f"\nStatus: {response.status_code}")
print(f"Response: {response.text}")
