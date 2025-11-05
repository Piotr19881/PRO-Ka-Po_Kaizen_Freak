import sqlite3
import os

def clean_note_links():
    """Usuwa invalid note_links z lokalnej bazy danych"""
    db_path = os.path.expanduser("~/.pro_ka_po/notes.db")
    
    if not os.path.exists(db_path):
        print("✅ Baza notes.db nie istnieje - nie ma co czyścić")
        return
    
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Znajdź invalid linki
        cursor.execute("""
            SELECT id, start_position, end_position, link_text 
            FROM note_links 
            WHERE start_position = end_position
        """)
        invalid_links = cursor.fetchall()
        
        print(f"🔍 Znalezione invalid linki: {len(invalid_links)}")
        for link_id, start, end, text in invalid_links:
            print(f"  - {link_id}: {start}={end} '{text[:50]}...'")
        
        if invalid_links:
            # Usuń invalid linki
            cursor.execute("DELETE FROM note_links WHERE start_position = end_position")
            deleted_count = cursor.rowcount
            
            conn.commit()
            print(f"✅ Usunięto {deleted_count} invalid linków")
        else:
            print("✅ Nie znaleziono invalid linków")
            
        conn.close()
        
    except Exception as e:
        print(f"❌ Błąd podczas czyszczenia: {e}")

if __name__ == "__main__":
    clean_note_links()