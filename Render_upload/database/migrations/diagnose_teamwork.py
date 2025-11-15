"""
DIAGNOSTYKA TEAMWORK - Skrypt Analityczny
==========================================
Sprawdza stan bazy danych TeamWork i diagnozuje problem z pustymi grupami
"""

import psycopg2
from psycopg2.extras import RealDictCursor
from datetime import datetime
import json


# Konfiguracja połączenia z bazą
DB_CONFIG = {
    "host": "dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com",
    "port": 5432,
    "database": "pro_ka_po",
    "user": "pro_ka_po_user",
    "password": "01pHONi8u23ZlHNffO64TcmWywetoiUD"
}

USER_ID = "207222a2-3845-40c2-9bea-cd5bbd6e15f6"
USER_EMAIL = "piotr.prokop@promirbud.eu"


def print_section(title):
    """Wydrukuj nagłówek sekcji"""
    print("\n" + "=" * 80)
    print(f"  {title}")
    print("=" * 80)


def print_results(results, title="Wyniki"):
    """Wydrukuj wyniki zapytania w czytelny sposób"""
    if not results:
        print(f"  ❌ Brak wyników dla: {title}")
        return
    
    print(f"\n  ✅ {title} ({len(results)} rekordów):")
    for i, row in enumerate(results, 1):
        print(f"\n  [{i}]")
        for key, value in row.items():
            if isinstance(value, datetime):
                value = value.strftime("%Y-%m-%d %H:%M:%S")
            print(f"    {key}: {value}")


def execute_query(cursor, query, params=None):
    """Wykonaj zapytanie i zwróć wyniki"""
    try:
        cursor.execute(query, params or ())
        return cursor.fetchall()
    except Exception as e:
        print(f"  ❌ Błąd zapytania: {e}")
        # Rollback transakcji aby móc kontynuować
        cursor.connection.rollback()
        return []


def main():
    print("\n" + "🔍" * 40)
    print("  DIAGNOSTYKA TEAMWORK - ANALIZA BAZY DANYCH")
    print("🔍" * 40)
    
    try:
        # Połączenie z bazą
        print("\n📡 Łączenie z bazą danych...")
        conn = psycopg2.connect(**DB_CONFIG, cursor_factory=RealDictCursor)
        cursor = conn.cursor()
        print("✅ Połączono z bazą danych PostgreSQL")
        
        # ====================================================================
        # KROK 1: Sprawdź użytkownika
        # ====================================================================
        print_section("KROK 1: SPRAWDZENIE UŻYTKOWNIKA")
        
        query = """
            SELECT id, email, name, created_at, is_verified
            FROM s01_user_accounts.users 
            WHERE email = %s
        """
        results = execute_query(cursor, query, (USER_EMAIL,))
        print_results(results, "Użytkownik z bazy")
        
        if results:
            actual_user_id = results[0]['id']
            print(f"\n  📋 Faktyczny user_id z bazy: {actual_user_id}")
            print(f"  📋 Oczekiwany user_id:        {USER_ID}")
            
            if actual_user_id != USER_ID:
                print(f"\n  ⚠️  OSTRZEŻENIE: User ID się nie zgadza!")
                print(f"      Używamy faktycznego ID: {actual_user_id}")
                USER_ID = actual_user_id
        
        # ====================================================================
        # KROK 2: Sprawdź grupy
        # ====================================================================
        print_section("KROK 2: WSZYSTKIE GRUPY W BAZIE")
        
        query = """
            SELECT group_id, group_name, created_by, is_active, created_at
            FROM s02_teamwork.work_groups
            ORDER BY group_id
        """
        results = execute_query(cursor, query)
        print_results(results, "Grupy TeamWork")
        
        # ====================================================================
        # KROK 3: Sprawdź członkostwa w grupach
        # ====================================================================
        print_section("KROK 3: WSZYSTKIE CZŁONKOSTWA W GRUPACH")
        
        query = """
            SELECT 
                gm.group_member_id,
                gm.group_id,
                g.group_name,
                gm.user_id,
                u.email as user_email,
                gm.role,
                gm.joined_at
            FROM s02_teamwork.group_members gm
            LEFT JOIN s02_teamwork.work_groups g ON gm.group_id = g.group_id
            LEFT JOIN s01_user_accounts.users u ON gm.user_id = u.id
            ORDER BY gm.group_id, gm.user_id
        """
        results = execute_query(cursor, query)
        print_results(results, "Członkostwa w grupach")
        
        # ====================================================================
        # KROK 4: Członkostwa dla konkretnego użytkownika
        # ====================================================================
        print_section(f"KROK 4: CZŁONKOSTWA DLA USER_ID = {USER_ID}")
        
        query = """
            SELECT 
                gm.group_id,
                g.group_name,
                gm.role,
                gm.joined_at
            FROM s02_teamwork.group_members gm
            JOIN s02_teamwork.work_groups g ON gm.group_id = g.group_id
            WHERE gm.user_id = %s
            ORDER BY gm.group_id
        """
        results = execute_query(cursor, query, (USER_ID,))
        print_results(results, f"Członkostwa użytkownika {USER_EMAIL}")
        
        user_groups_count = len(results) if results else 0
        
        # ====================================================================
        # KROK 5: Tematy
        # ====================================================================
        print_section("KROK 5: WSZYSTKIE TEMATY")
        
        query = """
            SELECT 
                t.topic_id,
                t.topic_name,
                t.group_id,
                g.group_name,
                t.created_by,
                t.is_active
            FROM s02_teamwork.topics t
            LEFT JOIN s02_teamwork.work_groups g ON t.group_id = g.group_id
            ORDER BY t.topic_id
        """
        results = execute_query(cursor, query)
        print_results(results, "Tematy")
        
        # ====================================================================
        # KROK 6: Zadania
        # ====================================================================
        print_section("KROK 6: ZADANIA")
        
        query = """
            SELECT 
                task_id,
                topic_id,
                task_subject,
                completed,
                is_important,
                due_date
            FROM s02_teamwork.tasks
            ORDER BY topic_id, task_id
        """
        results = execute_query(cursor, query)
        print_results(results, "Zadania")
        
        # ====================================================================
        # KROK 7: Test zapytania API
        # ====================================================================
        print_section("KROK 7: TEST ZAPYTANIA UŻYWANEGO PRZEZ API ENDPOINT /groups")
        
        query = """
            SELECT 
                g.group_id,
                g.group_name,
                g.description,
                g.created_by,
                g.is_active,
                g.created_at
            FROM s02_teamwork.work_groups g
            JOIN s02_teamwork.group_members gm ON g.group_id = gm.group_id
            WHERE gm.user_id = %s
            ORDER BY g.group_id
        """
        results = execute_query(cursor, query, (USER_ID,))
        print_results(results, "Grupy z API query")
        
        api_groups_count = len(results) if results else 0
        
        # ====================================================================
        # KROK 8: Tematy dla grup użytkownika
        # ====================================================================
        print_section("KROK 8: TEMATY W GRUPACH UŻYTKOWNIKA")
        
        query = """
            SELECT 
                t.topic_id,
                t.topic_name,
                t.group_id,
                g.group_name
            FROM s02_teamwork.topics t
            JOIN s02_teamwork.work_groups g ON t.group_id = g.group_id
            JOIN s02_teamwork.group_members gm ON g.group_id = gm.group_id
            WHERE gm.user_id = %s AND t.is_active = true
            ORDER BY t.group_id, t.topic_id
        """
        results = execute_query(cursor, query, (USER_ID,))
        print_results(results, "Tematy użytkownika")
        
        # ====================================================================
        # KROK 9: Typy danych
        # ====================================================================
        print_section("KROK 9: TYPY DANYCH KOLUMN")
        
        query = """
            SELECT 
                table_name,
                column_name,
                data_type,
                character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = 's02_teamwork' 
            AND table_name IN ('work_groups', 'group_members', 'topics')
            AND column_name IN ('user_id', 'created_by', 'group_id', 'topic_id')
            ORDER BY table_name, column_name
        """
        results = execute_query(cursor, query)
        print_results(results, "Typy danych kluczowych kolumn")
        
        # ====================================================================
        # KROK 10: Statystyki
        # ====================================================================
        print_section("KROK 10: STATYSTYKI")
        
        stats_queries = {
            "Grupy": "SELECT COUNT(*) as count FROM s02_teamwork.work_groups",
            "Członkostwa w grupach": "SELECT COUNT(*) as count FROM s02_teamwork.group_members",
            "Tematy": "SELECT COUNT(*) as count FROM s02_teamwork.topics",
            "Członkostwa w tematach": "SELECT COUNT(*) as count FROM s02_teamwork.topic_members",
            "Wiadomości": "SELECT COUNT(*) as count FROM s02_teamwork.messages",
            "Zadania": "SELECT COUNT(*) as count FROM s02_teamwork.tasks"
        }
        
        print("\n  📊 Statystyki ogólne:")
        for name, query in stats_queries.items():
            results = execute_query(cursor, query)
            count = results[0]['count'] if results else 0
            print(f"    {name}: {count}")
        
        # ====================================================================
        # PODSUMOWANIE I DIAGNOZA
        # ====================================================================
        print_section("PODSUMOWANIE I DIAGNOZA")
        
        print("\n  📋 Wyniki analizy:")
        print(f"    • User email: {USER_EMAIL}")
        print(f"    • User ID: {USER_ID}")
        print(f"    • Członkostwa użytkownika (z group_members): {user_groups_count}")
        print(f"    • Grupy zwrócone przez API query: {api_groups_count}")
        
        if user_groups_count == 0:
            print("\n  ❌ PROBLEM: Użytkownik nie jest członkiem żadnej grupy!")
            print("     ROZWIĄZANIE: Wykonaj INSERT do tabeli group_members")
        elif api_groups_count == 0:
            print("\n  ⚠️  PROBLEM: Członkostwa istnieją, ale API query nic nie zwraca!")
            print("     MOŻLIWE PRZYCZYNY:")
            print("       - Błędny user_id w zapytaniu API")
            print("       - Problem z JOIN w zapytaniu")
            print("       - Grupy oznaczone jako is_active=false")
        elif user_groups_count > 0 and api_groups_count > 0:
            print(f"\n  ✅ OK: Znaleziono {api_groups_count} grup dla użytkownika")
            print("     Sprawdź czy API zwraca zagnieżdżone topics!")
        
        cursor.close()
        conn.close()
        
        print("\n" + "✅" * 40)
        print("  DIAGNOSTYKA ZAKOŃCZONA")
        print("✅" * 40 + "\n")
        
    except psycopg2.Error as e:
        print(f"\n❌ Błąd połączenia z bazą danych:")
        print(f"   {e}")
    except Exception as e:
        print(f"\n❌ Nieoczekiwany błąd:")
        print(f"   {e}")


if __name__ == "__main__":
    main()
