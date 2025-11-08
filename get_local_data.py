import sqlite3
import json
from datetime import datetime

# Sprawdź lokalne dane
conn = sqlite3.connect('src/database/habit_tracker.db')
cursor = conn.cursor()

print("=== LOKALNE DANE ===")
cursor.execute('SELECT * FROM habit_columns WHERE user_id = 1')
columns = cursor.fetchall()
print(f"Kolumny: {len(columns)}")
for col in columns:
    print(f"  {col}")

# Przygotuj sync payload
columns_data = []
for col in columns:
    column_json = {
        "id": str(col[0]),
        "user_id": col[1], 
        "name": col[2],
        "type": col[3],
        "position": col[4] or 0,
        "created_at": col[5] or datetime.now().isoformat(),
        "updated_at": col[6] or datetime.now().isoformat(),
        "server_id": col[8] if len(col) > 8 and col[8] else None,
        "version": col[10] if len(col) > 10 and col[10] else 1
    }
    columns_data.append(column_json)

# Mapowanie typów z polskiego na angielski
type_mapping = {
    'Licznik': 'counter',
    'Czas trwania': 'duration', 
    'Checkbox': 'checkbox',
    'Tekst': 'text',
    'time': 'time',
    'scale': 'scale'
}

# Popraw typy kolumn i user_id
for col in columns_data:
    original_type = col['type']
    col['type'] = type_mapping.get(original_type, original_type.lower())
    col['user_id'] = "207222a2-3845-40c2-9bea-cd5bbd6e15f6"  # Prawidłowy UUID

sync_payload = {
    "user_id": "207222a2-3845-40c2-9bea-cd5bbd6e15f6",  # Prawidłowy UUID użytkownika
    "columns": columns_data,
    "records": []
}

print("\n=== PAYLOAD JSON ===")
print(json.dumps(sync_payload, indent=2))

# Zapisz do pliku
with open('sync_payload.json', 'w') as f:
    json.dump(sync_payload, f, indent=2)

print("\n✅ Zapisano do sync_payload.json")
conn.close()