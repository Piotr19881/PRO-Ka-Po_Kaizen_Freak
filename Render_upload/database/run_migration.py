"""
Uruchomienie migracji bazy danych
Dodaje kolumnę local_id do tabel Pomodoro
"""
import psycopg2
from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings

def run_migration():
    """Wykonaj migrację SQL"""
    migration_file = Path(__file__).parent / "migrations" / "001_add_local_id_to_pomodoro.sql"
    
    print(f"📂 Odczytywanie pliku migracji: {migration_file}")
    with open(migration_file, 'r', encoding='utf-8') as f:
        migration_sql = f.read()
    
    # Użyj konfiguracji z settings
    conn_string = f"host={settings.DATABASE_HOST} port={settings.DATABASE_PORT} dbname={settings.DATABASE_NAME} user={settings.DATABASE_USER} password={settings.DATABASE_PASSWORD} sslmode=require"
    
    print("🔌 Łączenie z bazą danych...")
    print(f"   Host: {settings.DATABASE_HOST}")
    print(f"   Database: {settings.DATABASE_NAME}")
    conn = psycopg2.connect(conn_string)
    conn.autocommit = True
    cursor = conn.cursor()
    
    try:
        print("⚙️  Wykonywanie migracji...")
        cursor.execute(migration_sql)
        print("✅ Migracja zakończona pomyślnie!")
        
        # Sprawdź czy kolumny istnieją
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 's05_pomodoro' 
            AND table_name = 'session_topics' 
            AND column_name = 'local_id';
        """)
        result = cursor.fetchone()
        if result:
            print(f"✓ Kolumna local_id w session_topics: {result[1]}")
        
        cursor.execute("""
            SELECT column_name, data_type 
            FROM information_schema.columns 
            WHERE table_schema = 's05_pomodoro' 
            AND table_name = 'session_logs' 
            AND column_name = 'local_id';
        """)
        result = cursor.fetchone()
        if result:
            print(f"✓ Kolumna local_id w session_logs: {result[1]}")
            
    except Exception as e:
        print(f"❌ Błąd podczas migracji: {e}")
        raise
    finally:
        cursor.close()
        conn.close()
        print("🔌 Połączenie zamknięte")

if __name__ == "__main__":
    run_migration()
