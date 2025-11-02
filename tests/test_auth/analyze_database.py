"""
Test połączenia z bazą danych i analiza schematu s01_user_accounts
"""
import psycopg2
from psycopg2 import sql

# Dane połączenia
DB_CONFIG = {
    'host': 'dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com',
    'port': 5432,
    'database': 'pro_ka_po',
    'user': 'pro_ka_po_user',
    'password': '01pHONi8u23ZlHNffO64TcmWywetoiUD'
}

def analyze_user_accounts_schema():
    """Analiza struktury schematu s01_user_accounts i jego tabel"""
    try:
        # Połączenie z bazą
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        print("=" * 80)
        print("ANALIZA SCHEMATU: s01_user_accounts")
        print("=" * 80)
        
        # Sprawdź czy schemat istnieje
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.schemata 
                WHERE schema_name = 's01_user_accounts'
            );
        """)
        schema_exists = cursor.fetchone()[0]
        
        if not schema_exists:
            print("\n⚠️  SCHEMAT s01_user_accounts NIE ISTNIEJE!")
            print("Potrzebujemy utworzyć nowy schemat.\n")
            return False
        
        print("\n✓ Schemat s01_user_accounts ISTNIEJE\n")
        
        # Pobierz wszystkie tabele w schemacie
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 's01_user_accounts'
            AND table_type = 'BASE TABLE'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        
        if not tables:
            print("⚠️  Schemat jest PUSTY - brak tabel!\n")
            return False
        
        print(f"TABELE W SCHEMACIE s01_user_accounts ({len(tables)}):")
        print("-" * 80)
        for table in tables:
            print(f"  • {table[0]}")
        print()
        
        # Dla każdej tabeli pobierz szczegóły
        for table in tables:
            table_name = table[0]
            print("\n" + "=" * 80)
            print(f"TABELA: s01_user_accounts.{table_name}")
            print("=" * 80)
            
            # Pobierz strukturę kolumn
            cursor.execute("""
                SELECT 
                    column_name,
                    data_type,
                    character_maximum_length,
                    is_nullable,
                    column_default
                FROM information_schema.columns
                WHERE table_schema = 's01_user_accounts' 
                AND table_name = %s
                ORDER BY ordinal_position;
            """, (table_name,))
            
            columns = cursor.fetchall()
            
            print("\nSTRUKTURA KOLUMN:")
            print("-" * 80)
            print(f"{'Kolumna':<30} {'Typ':<25} {'Długość':<10} {'Nullable':<10} {'Default'}")
            print("-" * 80)
            
            for col in columns:
                col_name, data_type, max_length, nullable, default = col
                length_str = str(max_length) if max_length else '-'
                default_str = str(default)[:30] if default else '-'
                print(f"{col_name:<30} {data_type:<25} {length_str:<10} {nullable:<10} {default_str}")
            
            # Pobierz constraints
            print("\n\nCONSTRAINTS:")
            print("-" * 80)
            cursor.execute("""
                SELECT
                    tc.constraint_name,
                    tc.constraint_type,
                    kcu.column_name
                FROM information_schema.table_constraints tc
                LEFT JOIN information_schema.key_column_usage kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                WHERE tc.table_schema = 's01_user_accounts'
                AND tc.table_name = %s
                ORDER BY tc.constraint_type, kcu.column_name;
            """, (table_name,))
            
            constraints = cursor.fetchall()
            if constraints:
                for constraint in constraints:
                    col_name = constraint[2] if constraint[2] else 'N/A'
                    print(f"{constraint[0]:<50} {constraint[1]:<20} {col_name}")
            else:
                print("Brak constraints")
            
            # Pobierz indexy
            print("\n\nINDEXY:")
            print("-" * 80)
            cursor.execute("""
                SELECT
                    indexname,
                    indexdef
                FROM pg_indexes
                WHERE tablename = %s
                AND schemaname = 's01_user_accounts';
            """, (table_name,))
            
            indexes = cursor.fetchall()
            if indexes:
                for index in indexes:
                    print(f"{index[0]}:")
                    print(f"  {index[1]}\n")
            else:
                print("Brak indexów")
            
            # Pobierz liczbę rekordów
            cursor.execute(sql.SQL("SELECT COUNT(*) FROM {}.{}").format(
                sql.Identifier('s01_user_accounts'),
                sql.Identifier(table_name)
            ))
            count = cursor.fetchone()[0]
            print(f"\nLiczba rekordów: {count}")
            
            if count > 0:
                print("\nPrzykładowy rekord (pierwszy):")
                print("-" * 80)
                cursor.execute(sql.SQL("SELECT * FROM {}.{} LIMIT 1").format(
                    sql.Identifier('s01_user_accounts'),
                    sql.Identifier(table_name)
                ))
                sample = cursor.fetchone()
                col_names = [desc[0] for desc in cursor.description]
                for name, value in zip(col_names, sample):
                    print(f"{name}: {value}")
        
        cursor.close()
        conn.close()
        
        print("\n" + "=" * 80)
        return True
        
    except Exception as e:
        print(f"\n❌ BŁĄD: {e}")
        import traceback
        traceback.print_exc()
        return False


def get_recommended_schema():
    """Zwraca zalecaną strukturę tabeli dla systemu rejestracji/logowania"""
    return """
    ZALECANA STRUKTURA TABELI s01_user_accounts:
    
    Kolumny wymagane:
    - id                    UUID PRIMARY KEY DEFAULT gen_random_uuid()
    - email                 VARCHAR(255) UNIQUE NOT NULL
    - username              VARCHAR(50) UNIQUE NOT NULL
    - password_hash         VARCHAR(255) NOT NULL
    - first_name            VARCHAR(100)
    - last_name             VARCHAR(100)
    - address               TEXT
    - preferred_language    VARCHAR(5) DEFAULT 'pl'  -- pl, en, de
    - age                   INTEGER
    - phone                 VARCHAR(20)
    - is_active             BOOLEAN DEFAULT FALSE
    - is_verified           BOOLEAN DEFAULT FALSE
    - email_verified        BOOLEAN DEFAULT FALSE
    - verification_code     VARCHAR(6)
    - verification_code_expires TIMESTAMP
    - reset_password_code   VARCHAR(6)
    - reset_password_expires TIMESTAMP
    - created_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - updated_at            TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    - last_login            TIMESTAMP
    - login_attempts        INTEGER DEFAULT 0
    - locked_until          TIMESTAMP
    
    Indexes:
    - idx_email ON s01_user_accounts(email)
    - idx_username ON s01_user_accounts(username)
    - idx_verification_code ON s01_user_accounts(verification_code)
    - idx_is_active ON s01_user_accounts(is_active)
    """


if __name__ == "__main__":
    print("\n🔍 ROZPOCZYNAM ANALIZĘ BAZY DANYCH...\n")
    
    exists = analyze_user_accounts_schema()
    
    if not exists:
        print(get_recommended_schema())
    
    print("\n✅ ANALIZA ZAKOŃCZONA")
