import sqlite3

db_path = "data/callcryptor.db"
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

cursor.execute("SELECT source_id, source_name, source_type, target_folder, search_all_folders, search_phrase FROM recordings_sources")
rows = cursor.fetchall()

print("Sources in database:")
for row in rows:
    print(f"  ID: {row[0]}")
    print(f"  Name: {row[1]}")
    print(f"  Type: {row[2]}")
    print(f"  Folder: {row[3]}")
    print(f"  Search all folders: {row[4]}")
    print(f"  Search phrase: {row[5]}")
    print()

conn.close()
