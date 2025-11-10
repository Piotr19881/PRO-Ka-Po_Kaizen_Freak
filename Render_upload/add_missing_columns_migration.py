"""
Migracja PostgreSQL: Dodanie brakujących kolumn do s07_callcryptor.recordings
Data: 2025-11-10
Opis: Dodaje 18 pól które istnieją w SQLite ale brakowały w PostgreSQL ORM
"""

import psycopg2
from app.config import settings

def run_migration():
    """Wykonaj ALTER TABLE dla s07_callcryptor.recordings"""
    
    print("=" * 60)
    print("🔧 MIGRACJA: Dodanie brakujących kolumn do recordings")
    print("=" * 60)
    
    # Lista kolumn do dodania
    columns_to_add = [
        # Transcription fields
        ("transcription_status", "TEXT DEFAULT 'pending'"),
        ("transcription_text", "TEXT"),
        ("transcription_language", "TEXT"),
        ("transcription_confidence", "REAL"),
        ("transcription_date", "TIMESTAMP"),
        ("transcription_error", "TEXT"),
        
        # AI Summary status fields
        ("ai_summary_status", "TEXT DEFAULT 'pending'"),
        ("ai_summary_date", "TIMESTAMP"),
        ("ai_summary_error", "TEXT"),
        
        # Archivization fields
        ("is_archived", "BOOLEAN DEFAULT FALSE"),
        ("archived_at", "TIMESTAMP"),
        ("archive_reason", "TEXT"),
        
        # Favorites fields
        ("is_favorite", "BOOLEAN DEFAULT FALSE"),
        ("favorited_at", "TIMESTAMP"),
    ]
    
    try:
        # Połącz z bazą
        print(f"🔌 Łączenie z bazą danych...")
        print(f"   Host: {settings.DATABASE_HOST}")
        print(f"   Database: {settings.DATABASE_NAME}")
        
        conn = psycopg2.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD
        )
        cursor = conn.cursor()
        
        print("✅ Połączono z bazą danych\n")
        
        # Dodaj każdą kolumnę
        added_columns = []
        skipped_columns = []
        
        for column_name, column_type in columns_to_add:
            try:
                # Sprawdź czy kolumna już istnieje
                cursor.execute("""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_schema = 's07_callcryptor' 
                    AND table_name = 'recordings' 
                    AND column_name = %s
                """, (column_name,))
                
                if cursor.fetchone():
                    print(f"⏭️  Kolumna '{column_name}' już istnieje - pomijam")
                    skipped_columns.append(column_name)
                    continue
                
                # Dodaj kolumnę
                alter_sql = f"""
                    ALTER TABLE s07_callcryptor.recordings 
                    ADD COLUMN {column_name} {column_type}
                """
                
                print(f"➕ Dodaję kolumnę: {column_name} ({column_type})")
                cursor.execute(alter_sql)
                added_columns.append(column_name)
                
            except psycopg2.Error as e:
                print(f"❌ Błąd przy dodawaniu {column_name}: {e}")
                conn.rollback()
                continue
        
        # Commit wszystkich zmian
        conn.commit()
        
        print("\n" + "=" * 60)
        print("📊 PODSUMOWANIE MIGRACJI")
        print("=" * 60)
        print(f"✅ Dodano kolumn: {len(added_columns)}")
        if added_columns:
            for col in added_columns:
                print(f"   - {col}")
        
        if skipped_columns:
            print(f"\n⏭️  Pominięto (już istniały): {len(skipped_columns)}")
            for col in skipped_columns:
                print(f"   - {col}")
        
        # Weryfikacja finalnej struktury
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 's07_callcryptor' 
            AND table_name = 'recordings'
            ORDER BY ordinal_position
        """)
        
        all_columns = cursor.fetchall()
        print(f"\n📋 Tabela recordings ma teraz {len(all_columns)} kolumn")
        
        cursor.close()
        conn.close()
        
        print("\n✅ Migracja zakończona pomyślnie!")
        return True
        
    except Exception as e:
        print(f"\n❌ Błąd podczas migracji: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = run_migration()
    exit(0 if success else 1)
