import sqlite3
from pathlib import Path

db_path = Path.home() / ".pro_ka_po" / "pomodoro.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Schema session_logs
cursor.execute("PRAGMA table_info(session_logs)")
columns = cursor.fetchall()

print("Kolumny w session_logs:")
for col in columns:
    print(f"  {col[1]} ({col[2]})")

conn.close()
