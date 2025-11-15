"""
Skrypt do analizy schematu istniejącej bazy danych PostgreSQL.

Użycie:
1. Upewnij się, że masz zainstalowane wymagane biblioteki:
   pip install sqlalchemy psycopg2-binary python-dotenv
2. Uruchom skrypt z głównego folderu projektu:
   python scripts/analyze_database_schema.py
"""

import sys
import os
from sqlalchemy import create_engine, inspect
from sqlalchemy.exc import OperationalError
from loguru import logger

# Dodaj główny folder projektu do ścieżki, aby umożliwić importy
# To jest potrzebne, aby skrypt mógł znaleźć moduł config
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, project_root)

try:
    # Importuj konfigurację z Render_upload/app/config.py
    from Render_upload.app.config import Settings
except ImportError as e:
    logger.error(f"Nie można zaimportować konfiguracji: {e}")
    logger.error("Upewnij się, że uruchamiasz skrypt z głównego folderu projektu.")
    sys.exit(1)

def analyze_schema():
    """Łączy się z bazą danych i analizuje jej schemat."""
    settings = Settings()
    
    # Tworzenie URL połączenia z bazą danych
    db_url = (
        f"postgresql+psycopg2://{settings.DATABASE_USER}:{settings.DATABASE_PASSWORD}@"
        f"{settings.DATABASE_HOST}:{settings.DATABASE_PORT}/{settings.DATABASE_NAME}"
    )
    
    logger.info(f"Łączenie z bazą danych: {settings.DATABASE_HOST}...")
    
    try:
        engine = create_engine(db_url)
        inspector = inspect(engine)
    except OperationalError as e:
        logger.error(f"Błąd połączenia z bazą danych: {e}")
        logger.error("Sprawdź dane uwierzytelniające w Render_upload/app/config.py oraz dostęp sieciowy.")
        return
    except Exception as e:
        logger.error(f"Wystąpił nieoczekiwany błąd: {e}")
        return

    logger.success("Połączenie z bazą danych udane!")
    print("\n" + "="*80)
    print("RAPORT STRUKTURY BAZY DANYCH")
    print("="*80)

    # 1. Pobierz listę wszystkich schematów
    schemas = inspector.get_schema_names()
    print(f"\n[INFO] Znalezione schematy ({len(schemas)}):")
    for schema in schemas:
        print(f"  - {schema}")
        
    # 2. Skup się na schemacie zdefiniowanym w konfiguracji
    target_schema = settings.DATABASE_SCHEMA
    print(f"\n[INFO] Analiza docelowego schematu: '{target_schema}'")

    if target_schema not in schemas:
        logger.warning(f"Schemat '{target_schema}' nie istnieje w bazie danych.")
        # Spróbujmy przeanalizować domyślny schemat 'public'
        if 'public' in schemas:
            logger.info("Przełączam na analizę schematu 'public'.")
            target_schema = 'public'
        else:
            return

    # 3. Pobierz listę tabel w docelowym schemacie
    try:
        tables = inspector.get_table_names(schema=target_schema)
        print(f"\n[INFO] Znalezione tabele w schemacie '{target_schema}' ({len(tables)}):")
        if not tables:
            print("  - Brak tabel w tym schemacie.")
            return
            
        for table_name in tables:
            print(f"\n--- Tabela: {target_schema}.{table_name} ---")
            
            # 4. Pobierz kolumny dla każdej tabeli
            columns = inspector.get_columns(table_name, schema=target_schema)
            print("  Kolumny:")
            for column in columns:
                col_info = (
                    f"    - {column['name']} ({column['type']})"
                    f"{' (PRIMARY KEY)' if column.get('primary_key') else ''}"
                    f"{' (NOT NULL)' if not column.get('nullable') else ''}"
                    f"{' (default: ' + str(column.get('default')) + ')' if column.get('default') else ''}"
                )
                print(col_info)

            # 5. Pobierz klucze obce
            foreign_keys = inspector.get_foreign_keys(table_name, schema=target_schema)
            if foreign_keys:
                print("  Klucze obce:")
                for fk in foreign_keys:
                    print(f"    - Kolumna(y) `{', '.join(fk['constrained_columns'])}` referencjonuje `{fk['referred_table']}` (`{', '.join(fk['referred_columns'])}`)")

            # 6. Pobierz indeksy
            indexes = inspector.get_indexes(table_name, schema=target_schema)
            if indexes:
                print("  Indeksy:")
                for index in indexes:
                    print(f"    - Nazwa: {index['name']}, Kolumny: {', '.join(index['column_names'])}{' (UNIQUE)' if index.get('unique') else ''}")

    except Exception as e:
        logger.error(f"Błąd podczas inspekcji schematu '{target_schema}': {e}")

    print("\n" + "="*80)
    print("Koniec raportu.")
    print("="*80)


if __name__ == "__main__":
    # Sprawdzenie, czy wymagane biblioteki są zainstalowane
    try:
        import sqlalchemy
        import psycopg2
    except ImportError:
        logger.error("Brak wymaganych bibliotek. Zainstaluj je, uruchamiając:")
        logger.error("pip install sqlalchemy psycopg2-binary")
        sys.exit(1)
        
    analyze_schema()
