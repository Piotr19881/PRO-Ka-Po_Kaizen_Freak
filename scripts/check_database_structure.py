"""
Skrypt do sprawdzania struktury bazy danych PostgreSQL
Wyświetla wszystkie schematy, tabele i ich strukturę
"""
import sys
from pathlib import Path

# Dodaj ścieżkę do modułów aplikacji
sys.path.insert(0, str(Path(__file__).parent.parent / "Render_upload"))

from sqlalchemy import inspect, text
from app.database import engine
from app.config import settings

def check_schemas():
    """Sprawdź wszystkie schematy w bazie danych"""
    print("=" * 80)
    print("SPRAWDZANIE STRUKTURY BAZY DANYCH POSTGRESQL")
    print("=" * 80)
    print(f"\n📊 Baza danych: {settings.DATABASE_URL.split('@')[1] if '@' in settings.DATABASE_URL else 'N/A'}")
    print(f"📂 Domyślny schemat: {settings.DATABASE_SCHEMA}")
    print("\n" + "=" * 80)
    
    with engine.connect() as conn:
        # Pobierz wszystkie schematy
        result = conn.execute(text("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema', 'pg_toast')
            ORDER BY schema_name
        """))
        
        schemas = [row[0] for row in result]
        
        print(f"\n🗂️  ZNALEZIONE SCHEMATY ({len(schemas)}):")
        print("-" * 80)
        for schema in schemas:
            print(f"  • {schema}")
        
        # Dla każdego schematu pokaż tabele
        for schema in schemas:
            print("\n" + "=" * 80)
            print(f"📋 SCHEMAT: {schema}")
            print("=" * 80)
            
            # Pobierz tabele w schemacie
            result = conn.execute(text(f"""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = '{schema}' 
                AND table_type = 'BASE TABLE'
                ORDER BY table_name
            """))
            
            tables = [row[0] for row in result]
            
            if not tables:
                print("  ⚠️  Brak tabel w tym schemacie")
                continue
            
            print(f"\n📑 Tabele ({len(tables)}):")
            print("-" * 80)
            
            for table in tables:
                print(f"\n  ┌─ {table}")
                
                # Pobierz kolumny tabeli
                result = conn.execute(text(f"""
                    SELECT 
                        column_name,
                        data_type,
                        character_maximum_length,
                        is_nullable,
                        column_default
                    FROM information_schema.columns
                    WHERE table_schema = '{schema}'
                    AND table_name = '{table}'
                    ORDER BY ordinal_position
                """))
                
                columns = result.fetchall()
                
                for col in columns:
                    col_name, data_type, max_len, nullable, default = col
                    
                    # Formatuj typ danych
                    if max_len:
                        type_str = f"{data_type}({max_len})"
                    else:
                        type_str = data_type
                    
                    # Formatuj nullable
                    null_str = "NULL" if nullable == "YES" else "NOT NULL"
                    
                    # Formatuj default
                    default_str = f" DEFAULT {default}" if default else ""
                    
                    print(f"  │  ├─ {col_name:30} {type_str:20} {null_str:10}{default_str}")
                
                # Pobierz klucze główne
                result = conn.execute(text(f"""
                    SELECT kcu.column_name
                    FROM information_schema.table_constraints tc
                    JOIN information_schema.key_column_usage kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    WHERE tc.constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = '{schema}'
                    AND tc.table_name = '{table}'
                """))
                
                pks = [row[0] for row in result]
                if pks:
                    print(f"  │  └─ 🔑 PRIMARY KEY: {', '.join(pks)}")
                
                # Pobierz klucze obce
                result = conn.execute(text(f"""
                    SELECT
                        kcu.column_name,
                        ccu.table_schema AS foreign_table_schema,
                        ccu.table_name AS foreign_table_name,
                        ccu.column_name AS foreign_column_name
                    FROM information_schema.table_constraints AS tc
                    JOIN information_schema.key_column_usage AS kcu
                        ON tc.constraint_name = kcu.constraint_name
                        AND tc.table_schema = kcu.table_schema
                    JOIN information_schema.constraint_column_usage AS ccu
                        ON ccu.constraint_name = tc.constraint_name
                        AND ccu.table_schema = tc.table_schema
                    WHERE tc.constraint_type = 'FOREIGN KEY'
                    AND tc.table_schema = '{schema}'
                    AND tc.table_name = '{table}'
                """))
                
                fks = result.fetchall()
                if fks:
                    print(f"  │  └─ 🔗 FOREIGN KEYS:")
                    for fk in fks:
                        col, fk_schema, fk_table, fk_col = fk
                        print(f"  │     └─ {col} → {fk_schema}.{fk_table}({fk_col})")
                
                # Pobierz indeksy
                result = conn.execute(text(f"""
                    SELECT
                        indexname,
                        indexdef
                    FROM pg_indexes
                    WHERE schemaname = '{schema}'
                    AND tablename = '{table}'
                """))
                
                indexes = result.fetchall()
                if len(indexes) > 1:  # Pomijamy domyślny indeks PK
                    print(f"  │  └─ 📊 INDEXES:")
                    for idx in indexes:
                        idx_name, idx_def = idx
                        if not idx_name.endswith('_pkey'):  # Pomijamy PK index
                            print(f"  │     └─ {idx_name}")
                
                print("  └─" + "─" * 78)


def check_specific_schema(schema_name: str):
    """Sprawdź konkretny schemat szczegółowo"""
    print(f"\n{'=' * 80}")
    print(f"SZCZEGÓŁOWA ANALIZA SCHEMATU: {schema_name}")
    print("=" * 80)
    
    with engine.connect() as conn:
        # Sprawdź czy schemat istnieje
        result = conn.execute(text(f"""
            SELECT EXISTS (
                SELECT 1 FROM information_schema.schemata 
                WHERE schema_name = '{schema_name}'
            )
        """))
        
        exists = result.scalar()
        
        if not exists:
            print(f"\n❌ Schemat '{schema_name}' NIE ISTNIEJE w bazie danych!")
            return
        
        print(f"\n✅ Schemat '{schema_name}' istnieje")
        
        # Statystyki
        result = conn.execute(text(f"""
            SELECT 
                COUNT(DISTINCT table_name) as table_count,
                SUM(CASE WHEN table_type = 'BASE TABLE' THEN 1 ELSE 0 END) as base_tables,
                SUM(CASE WHEN table_type = 'VIEW' THEN 1 ELSE 0 END) as views
            FROM information_schema.tables
            WHERE table_schema = '{schema_name}'
        """))
        
        stats = result.fetchone()
        print(f"\n📊 Statystyki:")
        print(f"  • Łączna liczba obiektów: {stats[0]}")
        print(f"  • Tabele: {stats[1]}")
        print(f"  • Widoki: {stats[2]}")


def suggest_alarm_schema():
    """Zasugeruj nazwę dla schematu alarmów"""
    print("\n" + "=" * 80)
    print("💡 SUGESTIA DLA NOWEGO SCHEMATU ALARMÓW")
    print("=" * 80)
    
    with engine.connect() as conn:
        result = conn.execute(text("""
            SELECT schema_name 
            FROM information_schema.schemata 
            WHERE schema_name LIKE 's%'
            ORDER BY schema_name
        """))
        
        existing = [row[0] for row in result]
        
        print("\n📋 Istniejące schematy z prefiksem 's':")
        for schema in existing:
            print(f"  • {schema}")
        
        # Wyciągnij numery
        numbers = []
        for schema in existing:
            if schema.startswith('s') and '_' in schema:
                try:
                    num = int(schema.split('_')[0][1:])
                    numbers.append(num)
                except ValueError:
                    pass
        
        if numbers:
            next_num = max(numbers) + 1
        else:
            next_num = 2  # s01 już jest użyty
        
        suggested_name = f"s{next_num:02d}_alarms_timers"
        
        print(f"\n✨ Sugerowana nazwa dla nowego schematu:")
        print(f"   {suggested_name}")
        print(f"\n📝 Konwencja nazewnictwa:")
        print(f"   • sXX_ - prefix z numerem (s01, s02, s03...)")
        print(f"   • nazwa opisująca moduł funkcjonalny")
        print(f"   • separacja różnych modułów aplikacji")


def main():
    """Główna funkcja"""
    try:
        print("\n🔌 Łączenie z bazą danych...")
        
        # Test połączenia
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version()"))
            version = result.scalar()
            print(f"✅ Połączono z PostgreSQL")
            print(f"📌 Wersja: {version.split(',')[0]}")
        
        # Sprawdź wszystkie schematy
        check_schemas()
        
        # Sprawdź szczegółowo schemat s01_user_accounts
        check_specific_schema('s01_user_accounts')
        
        # Zasugeruj nazwę dla schematu alarmów
        suggest_alarm_schema()
        
        print("\n" + "=" * 80)
        print("✅ ANALIZA ZAKOŃCZONA POMYŚLNIE")
        print("=" * 80)
        
    except Exception as e:
        print(f"\n❌ BŁĄD: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
