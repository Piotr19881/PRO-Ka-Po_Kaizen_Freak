import sqlite3
from pathlib import Path

db_path = Path.home() / ".pro_ka_po" / "pomodoro.db"
print(f"Baza danych: {db_path}")
print(f"Istnieje: {db_path.exists()}")

if db_path.exists():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Tabele
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
    tables = cursor.fetchall()
    print(f"\nTabele ({len(tables)}):")
    for table in tables:
        print(f"  - {table[0]}")
    
    # Session topics
    if any('session_topics' in t for t in tables):
        cursor.execute("SELECT COUNT(*) FROM session_topics")
        count = cursor.fetchone()[0]
        print(f"\nSession Topics: {count} rekordów")
        
        cursor.execute("SELECT id, name, is_synced FROM session_topics LIMIT 5")
        for row in cursor.fetchall():
            print(f"  {row[0][:8]}... | {row[1]} | synced={row[2]}")
    
    # Session logs
    if any('session_logs' in t for t in tables):
        cursor.execute("SELECT COUNT(*) FROM session_logs")
        count = cursor.fetchone()[0]
        print(f"\nSession Logs: {count} rekordów")
        
        cursor.execute("SELECT id, session_date, status, is_synced FROM session_logs ORDER BY started_at DESC LIMIT 5")
        for row in cursor.fetchall():
            print(f"  {row[0][:8]}... | {row[1]} | {row[2]} | synced={row[3]}")
    
    conn.close()
