#!/usr/bin/env python3
"""
Sprawdza zawartość lokalnej bazy habit_tracker.db
"""
import sqlite3
from pathlib import Path

db_path = Path("src/database/habit_tracker.db")
if not db_path.exists():
    print(f"❌ Baza danych nie istnieje: {db_path}")
    exit(1)

print(f"✅ Sprawdzam bazę: {db_path}")
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

print("\n=== TABELE W BAZIE ===")
cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
tables = cursor.fetchall()
for table in tables:
    print(f"- {table[0]}")

print("\n=== KOLUMNY NAWYKÓW (user_id=1) ===")
cursor.execute("SELECT * FROM habit_columns WHERE user_id = 1")
columns = cursor.fetchall()
print(f"Znaleziono {len(columns)} kolumn:")
for col in columns:
    print(f"  {col}")

print("\n=== REKORDY NAWYKÓW (user_id=1) ===")
cursor.execute("SELECT * FROM habit_records WHERE user_id = 1 LIMIT 5")
records = cursor.fetchall()
print(f"Znaleziono {len(records)} rekordów (pierwsze 5):")
for rec in records:
    print(f"  {rec}")

print("\n=== SYNC QUEUE ===")
cursor.execute("SELECT * FROM sync_queue WHERE user_id = 1")
sync_items = cursor.fetchall()
print(f"W kolejce synchronizacji: {len(sync_items)} elementów:")
for item in sync_items:
    print(f"  {item}")

conn.close()