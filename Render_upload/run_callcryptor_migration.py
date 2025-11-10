"""
Uruchomienie migracji CallCryptor Sync
Tworzy schema s07_callcryptor z tabelami: recording_sources, recordings, recording_tags
"""
import psycopg2
from pathlib import Path
import sys

# Dodaj parent directory do path
sys.path.append(str(Path(__file__).parent))

from app.config import settings

def run_migration():
    """Wykonaj migrację CallCryptor SQL"""
    
    # Najpierw schema SQL
    schema_file = Path(__file__).parent / "database" / "s07_callcryptor_schema.sql"
    
    print(f"📂 Odczytywanie pliku schema: {schema_file}")
    if not schema_file.exists():
        print(f"❌ Plik nie istnieje: {schema_file}")
        return False
        
    with open(schema_file, 'r', encoding='utf-8') as f:
        schema_sql = f.read()
    
    # Połączenie z bazą
    conn_string = f"host={settings.DATABASE_HOST} port={settings.DATABASE_PORT} dbname={settings.DATABASE_NAME} user={settings.DATABASE_USER} password={settings.DATABASE_PASSWORD} sslmode=require"
    
    print("🔌 Łączenie z bazą danych...")
    print(f"   Host: {settings.DATABASE_HOST}")
    print(f"   Database: {settings.DATABASE_NAME}")
    
    try:
        conn = psycopg2.connect(conn_string)
        conn.autocommit = True
        cursor = conn.cursor()
        
        print("⚙️  Wykonywanie migracji schema...")
        cursor.execute(schema_sql)
        print("✅ Schema s07_callcryptor utworzone pomyślnie!")
        
        # Weryfikacja
        print("\n🔍 Weryfikacja...")
        
        # Sprawdź czy schema istnieje
        cursor.execute("""
            SELECT nspname FROM pg_namespace WHERE nspname = 's07_callcryptor';
        """)
        if cursor.fetchone():
            print("✓ Schema s07_callcryptor istnieje")
        
        # Sprawdź tabele
        tables = ['recording_sources', 'recordings', 'recording_tags']
        for table in tables:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 's07_callcryptor' 
                AND table_name = %s;
            """, (table,))
            if cursor.fetchone():
                print(f"✓ Tabela {table} istnieje")
                
                # Policz kolumny
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.columns 
                    WHERE table_schema = 's07_callcryptor' 
                    AND table_name = %s;
                """, (table,))
                col_count = cursor.fetchone()[0]
                print(f"  └─ Liczba kolumn: {col_count}")
        
        print("\n✅ Migracja CallCryptor zakończona pomyślnie!")
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        print(f"\n❌ Błąd podczas migracji: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 MIGRACJA CALLCRYPTOR SYNC")
    print("=" * 60)
    success = run_migration()
    sys.exit(0 if success else 1)
