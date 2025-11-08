"""
Sprawdź status synchronizacji Habit Tracker
"""
import sqlite3
from pathlib import Path

# Ścieżka do bazy
db_path = Path("src/database/habit_tracker.db")

print(f"🔍 Sprawdzanie: {db_path}")
print(f"📁 Istnieje: {db_path.exists()}")

if not db_path.exists():
    print("❌ Baza nie istnieje - uruchom aplikację i dodaj kolumnę")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Sprawdź strukturę habit_columns
print("\n📊 STRUKTURA habit_columns:")
cursor.execute("PRAGMA table_info(habit_columns)")
columns = cursor.fetchall()
for col in columns:
    print(f"  - {col[1]} ({col[2]})")

# Sprawdź czy jest kolumna is_synced
has_is_synced = any(col[1] == 'is_synced' for col in columns)
print(f"\n✅ Kolumna is_synced: {'TAK' if has_is_synced else 'NIE'}")

# Pokaż kolumny
print("\n📋 KOLUMNY W BAZIE:")
cursor.execute("SELECT id, name, type, remote_id, is_synced, synced_at FROM habit_columns")
rows = cursor.fetchall()
for row in rows:
    print(f"  ID={row[0]}, Name={row[1]}, Type={row[2]}, Remote={row[3]}, is_synced={row[4]}, synced_at={row[5]}")

if not rows:
    print("  (brak kolumn)")

# Sprawdź sync_queue
print("\n🔄 SYNC QUEUE:")
cursor.execute("SELECT id, entity_type, entity_id, action, retry_count FROM sync_queue")
queue = cursor.fetchall()
for item in queue:
    print(f"  [{item[0]}] {item[1]} {item[2]} - {item[3]} (retry={item[4]})")

if not queue:
    print("  (pusta kolejka)")

# Sprawdź niezsynchronizowane
print("\n⏳ NIEZSYNCHRONIZOWANE:")
cursor.execute("SELECT COUNT(*) FROM habit_columns WHERE is_synced = 0")
unsynced = cursor.fetchone()[0]
print(f"  Kolumny: {unsynced}")

conn.close()
