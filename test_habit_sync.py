"""
Test sprawdzający działanie synchronizacji Habit Tracker po dodaniu is_synced
"""
import sqlite3
from pathlib import Path
from datetime import date

# Ścieżka do bazy danych
db_path = Path.home() / ".pro_ka_po" / "habit_tracker.db"

print(f"🔍 Sprawdzanie bazy danych: {db_path}")
print(f"📁 Baza istnieje: {db_path.exists()}")

if not db_path.exists():
    print("❌ Baza danych nie istnieje. Uruchom aplikację najpierw.")
    exit(1)

with sqlite3.connect(db_path) as conn:
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Sprawdź strukturę habit_columns
    print("\n📊 Struktura tabeli habit_columns:")
    cursor.execute("PRAGMA table_info(habit_columns)")
    columns_info = cursor.fetchall()
    for col in columns_info:
        print(f"  - {col['name']}: {col['type']} (notnull={col['notnull']}, default={col['dflt_value']})")
    
    # Sprawdź czy is_synced istnieje
    column_names = [col['name'] for col in columns_info]
    if 'is_synced' in column_names:
        print("  ✅ Kolumna is_synced ISTNIEJE")
    else:
        print("  ❌ Kolumna is_synced NIE ISTNIEJE - uruchom aplikację aby wykonać migrację")
    
    # Sprawdź strukturę habit_records
    print("\n📊 Struktura tabeli habit_records:")
    cursor.execute("PRAGMA table_info(habit_records)")
    records_info = cursor.fetchall()
    for col in records_info:
        print(f"  - {col['name']}: {col['type']} (notnull={col['notnull']}, default={col['dflt_value']})")
    
    # Sprawdź czy is_synced istnieje
    record_names = [col['name'] for col in records_info]
    if 'is_synced' in record_names:
        print("  ✅ Kolumna is_synced ISTNIEJE")
    else:
        print("  ❌ Kolumna is_synced NIE ISTNIEJE - uruchom aplikację aby wykonać migrację")
    
    # Sprawdź istniejące kolumny
    print("\n📋 Istniejące kolumny nawyków:")
    cursor.execute("""
        SELECT id, name, type, remote_id, is_synced, synced_at, version 
        FROM habit_columns 
        WHERE deleted_at IS NULL
        ORDER BY position
    """)
    
    columns = cursor.fetchall()
    if columns:
        for col in columns:
            synced_status = "✅ SYNCED" if col['is_synced'] else "❌ NOT SYNCED"
            print(f"  - {col['name']} ({col['type']})")
            print(f"    ID: {col['id']}, Remote: {col['remote_id']}")
            print(f"    Version: {col['version']}, Status: {synced_status}")
            print(f"    Synced at: {col['synced_at']}")
    else:
        print("  (brak kolumn)")
    
    # Sprawdź sync_queue
    print("\n🔄 Kolejka synchronizacji (sync_queue):")
    cursor.execute("""
        SELECT entity_type, entity_id, action, retry_count, error_message, created_at
        FROM sync_queue
        ORDER BY created_at
        LIMIT 20
    """)
    
    queue = cursor.fetchall()
    if queue:
        for item in queue:
            print(f"  - {item['entity_type']} {item['entity_id'][:8]}... ({item['action']})")
            print(f"    Retries: {item['retry_count']}, Created: {item['created_at']}")
            if item['error_message']:
                print(f"    Error: {item['error_message']}")
    else:
        print("  (kolejka pusta)")
    
    # Statystyki
    print("\n📈 Statystyki:")
    cursor.execute("SELECT COUNT(*) as count FROM habit_columns WHERE deleted_at IS NULL")
    total_columns = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM habit_columns WHERE deleted_at IS NULL AND is_synced = 0")
    unsynced_columns = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM habit_records")
    total_records = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM habit_records WHERE is_synced = 0")
    unsynced_records = cursor.fetchone()['count']
    
    cursor.execute("SELECT COUNT(*) as count FROM sync_queue")
    queue_size = cursor.fetchone()['count']
    
    print(f"  Kolumny: {total_columns} total, {unsynced_columns} niezsynchronizowanych")
    print(f"  Rekordy: {total_records} total, {unsynced_records} niezsynchronizowanych")
    print(f"  Kolejka sync: {queue_size} items")
    
    if unsynced_columns > 0 or unsynced_records > 0:
        print("\n⚠️  WYKRYTO NIEZSYNCHRONIZOWANE DANE:")
        print(f"  - {unsynced_columns} kolumn wymaga synchronizacji")
        print(f"  - {unsynced_records} rekordów wymaga synchronizacji")
        print("  Sync manager powinien je automatycznie zsynchronizować w ciągu 30 sekund.")
    else:
        print("\n✅ Wszystkie dane są zsynchronizowane!")

print("\n✅ Test zakończony")
