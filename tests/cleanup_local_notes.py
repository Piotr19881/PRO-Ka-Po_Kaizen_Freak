"""
Notes Local Database Cleanup Script
==================================
Usuwa błędne note_links z lokalnej bazy SQLite z start_position >= end_position
"""

import sqlite3
from pathlib import Path

# Ścieżka do lokalnej bazy Notes (zgodna z src/config.py)
LOCAL_DB_DIR = Path.home() / '.pro_ka_po'
notes_db_path = LOCAL_DB_DIR / 'notes.db'

def cleanup_local_notes_db():
    """Czyści błędne note_links z lokalnej bazy SQLite"""
    
    if not notes_db_path.exists():
        print(f"❌ Nie znaleziono lokalnej bazy: {notes_db_path}")
        return
    
    print(f"🔍 Sprawdzanie lokalnej bazy: {notes_db_path}")
    
    try:
        # Połączenie z lokalną bazą SQLite
        conn = sqlite3.connect(str(notes_db_path))
        cursor = conn.cursor()
        
        # Sprawdź błędne rekordy
        cursor.execute("""
            SELECT id, link_text, start_position, end_position,
                   (end_position - start_position) as link_length
            FROM note_links 
            WHERE start_position >= end_position
            ORDER BY created_at DESC;
        """)
        
        bad_records = cursor.fetchall()
        print(f"Znaleziono {len(bad_records)} błędnych rekordów w lokalnej bazie:")
        
        for record in bad_records:
            id_short = record[0][:8] + "..." if len(record[0]) > 8 else record[0]
            text = record[1][:30] + "..." if len(record[1]) > 30 else record[1]
            print(f"  ID: {id_short}, text: '{text}', start: {record[2]}, end: {record[3]}, length: {record[4]}")
        
        if bad_records:
            print(f"\n🗑️ Usuwanie {len(bad_records)} błędnych rekordów z lokalnej bazy...")
            
            # Usuń błędne rekordy
            cursor.execute("DELETE FROM note_links WHERE start_position >= end_position;")
            deleted_count = cursor.rowcount
            
            # Zapisz zmiany
            conn.commit()
            print(f"✅ Usunięto {deleted_count} błędnych rekordów z lokalnej bazy")
            
            # Weryfikacja
            cursor.execute("""
                SELECT COUNT(*) as total_links,
                       COALESCE(MIN(end_position - start_position), 0) as min_length,
                       COALESCE(MAX(end_position - start_position), 0) as max_length
                FROM note_links;
            """)
            
            result = cursor.fetchone()
            print(f"\n📊 Stan po cleanup:")
            print(f"   Pozostało rekordów: {result[0]}")
            if result[0] > 0:
                print(f"   Minimalna długość: {result[1]}")
                print(f"   Maksymalna długość: {result[2]}")
                
                if result[1] > 0:
                    print("✅ Wszystkie pozostałe rekordy mają prawidłową długość!")
                else:
                    print("⚠️ Wciąż są problemy z długością linków")
            else:
                print("📝 Brak linków w lokalnej bazie")
        else:
            print("✅ Brak błędnych rekordów w lokalnej bazie")
            
        conn.close()
        print("\n🎉 Cleanup lokalnej bazy zakończony!")
        print("\n🔄 RESTART KLIENTA aby załadować czyste dane")
        
    except Exception as e:
        print(f"❌ Błąd podczas cleanup: {e}")

if __name__ == "__main__":
    cleanup_local_notes_db()