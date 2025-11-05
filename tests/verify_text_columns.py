import sqlite3

conn = sqlite3.connect('PRO-Ka-Po_Kaizen_Freak/src/database/tasks.db')
cursor = conn.cursor()

# Sprawdź kolumny tekstowe użytkownika
cursor.execute("""
    SELECT column_id, type, visible_main, is_system, editable 
    FROM task_columns_config 
    WHERE type IN ('text', 'tekstowa', 'tekst', 'string', 'str')
    AND is_system = 0
    AND editable = 1
    ORDER BY position
""")

rows = cursor.fetchall()
print(f"\n=== Kolumny tekstowe użytkownika (niestandardowe, edytowalne) ===")
print(f"Znaleziono: {len(rows)} kolumn\n")

for row in rows:
    print(f"✓ Kolumna: '{row[0]}'")
    print(f"  Typ: {row[1]}")
    print(f"  Widoczna: {row[2]}")
    print(f"  Systemowa: {row[3]} (0=NIE)")
    print(f"  Edytowalna: {row[4]}")
    print(f"  → Dialog TextInputDialog powinien się otworzyć!")
    print()

if len(rows) == 0:
    print("❌ Brak kolumn tekstowych użytkownika!")
    print("   Użyj interfejsu konfiguracji kolumn aby dodać kolumnę typu 'tekstowa'")

conn.close()
