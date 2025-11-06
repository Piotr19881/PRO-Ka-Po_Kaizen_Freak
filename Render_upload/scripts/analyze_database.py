"""
Script do analizy struktury bazy danych PostgreSQL na Render
"""
import psycopg2
from psycopg2 import sql
import sys
import os

# Dodaj ścieżkę do app
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.config import settings

def analyze_database():
    """Analizuj strukturę bazy danych"""
    
    print("=" * 80)
    print("ANALIZA BAZY DANYCH POSTGRESQL NA RENDER")
    print("=" * 80)
    print(f"\nHost: {settings.DATABASE_HOST}")
    print(f"Database: {settings.DATABASE_NAME}")
    print(f"User: {settings.DATABASE_USER}")
    
    try:
        # Połączenie z bazą
        conn = psycopg2.connect(
            host=settings.DATABASE_HOST,
            port=settings.DATABASE_PORT,
            database=settings.DATABASE_NAME,
            user=settings.DATABASE_USER,
            password=settings.DATABASE_PASSWORD
        )
        cursor = conn.cursor()
        
        print("\n✅ Połączono z bazą danych!")
        
        # 1. Lista schematów
        print("\n" + "=" * 80)
        print("1. SCHEMATY W BAZIE DANYCH")
        print("=" * 80)
        
        cursor.execute("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('information_schema', 'pg_catalog', 'pg_toast')
            ORDER BY schema_name;
        """)
        
        schemas = cursor.fetchall()
        print(f"\nZnaleziono {len(schemas)} schematów użytkownika:\n")
        for schema in schemas:
            print(f"  • {schema[0]}")
        
        # 2. Szczegóły dla każdego schematu
        for schema in schemas:
            schema_name = schema[0]
            
            print("\n" + "=" * 80)
            print(f"2. TABELE W SCHEMACIE: {schema_name}")
            print("=" * 80)
            
            # Lista tabel
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = %s 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name;
            """, (schema_name,))
            
            tables = cursor.fetchall()
            print(f"\nZnaleziono {len(tables)} tabel:\n")
            
            for table in tables:
                table_name = table[0]
                print(f"\n  📋 {schema_name}.{table_name}")
                
                # Kolumny tabeli
                cursor.execute("""
                    SELECT 
                        column_name, 
                        data_type, 
                        is_nullable,
                        column_default
                    FROM information_schema.columns 
                    WHERE table_schema = %s 
                    AND table_name = %s 
                    ORDER BY ordinal_position;
                """, (schema_name, table_name))
                
                columns = cursor.fetchall()
                print(f"     Kolumny ({len(columns)}):")
                for col in columns:
                    col_name, data_type, nullable, default = col
                    null_str = "NULL" if nullable == "YES" else "NOT NULL"
                    default_str = f" DEFAULT {default}" if default else ""
                    print(f"       - {col_name}: {data_type} {null_str}{default_str}")
                
                # Liczba wierszy
                try:
                    cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                        sql.Identifier(schema_name),
                        sql.Identifier(table_name)
                    ))
                    count = cursor.fetchone()[0]
                    print(f"     📊 Wierszy: {count}")
                except Exception as e:
                    print(f"     ⚠️  Nie można policzyć wierszy: {e}")
        
        # 3. Sprawdź czy istnieje s02_tasks (stary schemat)
        print("\n" + "=" * 80)
        print("3. SPRAWDZANIE STAREGO SCHEMATU s02_tasks")
        print("=" * 80)
        
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 
                FROM information_schema.schemata 
                WHERE schema_name = 's02_tasks'
            );
        """)
        
        s02_exists = cursor.fetchone()[0]
        
        if s02_exists:
            print("\n⚠️  UWAGA: Schemat s02_tasks ISTNIEJE!")
            print("   Ten schemat powinien zostać usunięty przed migracją.")
            
            # Pokaż tabele w s02_tasks
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 's02_tasks' 
                AND table_type = 'BASE TABLE';
            """)
            old_tables = cursor.fetchall()
            
            if old_tables:
                print(f"\n   Tabele w s02_tasks ({len(old_tables)}):")
                for t in old_tables:
                    print(f"     - {t[0]}")
        else:
            print("\n✅ Schemat s02_tasks nie istnieje (OK)")
        
        # 4. Sprawdź czy istnieje s06_tasks (nowy schemat)
        print("\n" + "=" * 80)
        print("4. SPRAWDZANIE NOWEGO SCHEMATU s06_tasks")
        print("=" * 80)
        
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 
                FROM information_schema.schemata 
                WHERE schema_name = 's06_tasks'
            );
        """)
        
        s06_exists = cursor.fetchone()[0]
        
        if s06_exists:
            print("\n✅ Schemat s06_tasks ISTNIEJE!")
            
            # Pokaż tabele w s06_tasks
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 's06_tasks' 
                AND table_type = 'BASE TABLE';
            """)
            new_tables = cursor.fetchall()
            
            if new_tables:
                print(f"\n   Tabele w s06_tasks ({len(new_tables)}):")
                for t in new_tables:
                    print(f"     - {t[0]}")
            else:
                print("\n   ⚠️  Schemat istnieje, ale nie ma tabel")
        else:
            print("\n❌ Schemat s06_tasks NIE ISTNIEJE")
            print("   Należy wykonać migration create_tasks_schema_v2.sql")
        
        # 5. Podsumowanie dla Alarms (wzorzec)
        print("\n" + "=" * 80)
        print("5. ANALIZA SCHEMATU s04_alarms_timers (WZORZEC)")
        print("=" * 80)
        
        cursor.execute("""
            SELECT EXISTS(
                SELECT 1 
                FROM information_schema.schemata 
                WHERE schema_name = 's04_alarms_timers'
            );
        """)
        
        s04_exists = cursor.fetchone()[0]
        
        if s04_exists:
            print("\n✅ Schemat s04_alarms_timers istnieje")
            
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 's04_alarms_timers' 
                AND table_type = 'BASE TABLE';
            """)
            alarms_tables = cursor.fetchall()
            
            if alarms_tables:
                print(f"\n   Tabele ({len(alarms_tables)}):")
                for t in alarms_tables:
                    table_name = t[0]
                    print(f"\n     📋 {table_name}")
                    
                    # Szczegóły kolumn
                    cursor.execute("""
                        SELECT column_name, data_type 
                        FROM information_schema.columns 
                        WHERE table_schema = 's04_alarms_timers' 
                        AND table_name = %s 
                        ORDER BY ordinal_position;
                    """, (table_name,))
                    
                    cols = cursor.fetchall()
                    for col in cols:
                        print(f"        - {col[0]}: {col[1]}")
        else:
            print("\n❌ Schemat s04_alarms_timers NIE ISTNIEJE")
        
        # 6. Rekomendacje
        print("\n" + "=" * 80)
        print("6. REKOMENDACJE")
        print("=" * 80)
        
        print("\nNastępne kroki:")
        
        if s02_exists:
            print("\n  1️⃣  BACKUP - Zrób backup bazy przed usunięciem s02_tasks:")
            print("     pg_dump -h ... -U ... -d pro_ka_po > backup_$(date +%Y%m%d).sql")
            print("\n  2️⃣  DROP - Usuń stary schemat s02_tasks:")
            print("     DROP SCHEMA s02_tasks CASCADE;")
        
        if not s06_exists:
            print("\n  3️⃣  CREATE - Utwórz nowy schemat s06_tasks:")
            print("     Wykonaj migration: create_tasks_schema_v2.sql")
        
        print("\n  4️⃣  MODELS - Utwórz pliki:")
        print("     - Render_upload/app/tasks_models.py")
        print("     - Render_upload/app/tasks_schemas.py")
        print("     - Render_upload/app/tasks_router.py")
        
        print("\n  5️⃣  FRONTEND - Rozszerz lokalną bazę SQLite o sync metadata")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        print("ANALIZA ZAKOŃCZONA")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ BŁĄD: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = analyze_database()
    sys.exit(exit_code)
