"""
TeamWork Module Diagnostics Script
Skrypt diagnostyczny modułu TeamWork - analiza stanu bazy danych
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime

# Konfiguracja połączenia z bazy (z config.py)
DB_CONFIG = {
    "host": "dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com",
    "port": 5432,
    "database": "pro_ka_po",
    "user": "pro_ka_po_user",
    "password": "01pHONi8u23ZlHNffO64TcmWywetoiUD"
}

USER_EMAIL = "piotr.prokop@promirbud.eu"
USER_ID = "207222a2-3845-40c2-9bea-cd5bbd6e15f6"

def print_section(title):
    """Wyświetla separator sekcji"""
    print("\n" + "="*80)
    print(f" {title}")
    print("="*80)

def execute_query(cursor, query, params=None):
    """Wykonuje zapytanie i zwraca wyniki"""
    try:
        cursor.execute(query, params)
        return cursor.fetchall()
    except Exception as e:
        print(f"❌ Błąd wykonania zapytania: {e}")
        return []

def main():
    """Główna funkcja diagnostyczna"""
    print_section("🔍 DIAGNOSTYKA MODUŁU TEAMWORK")
    print(f"📅 Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"👤 Użytkownik: {USER_EMAIL}")
    print(f"🆔 User ID: {USER_ID}")
    
    try:
        # Połączenie z bazą
        print_section("📡 ŁĄCZENIE Z BAZĄ DANYCH")
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor(cursor_factory=RealDictCursor)
        print("✅ Połączono z bazą danych PostgreSQL")
        
        # ========================================================================
        # KROK 1: Sprawdź użytkownika
        # ========================================================================
        print_section("👤 KROK 1: Weryfikacja użytkownika")
        query = """
            SELECT id, email, name, created_at 
            FROM s01_user_accounts.users 
            WHERE email = %s
        """
        results = execute_query(cursor, query, (USER_EMAIL,))
        
        if results:
            user = results[0]
            print(f"✅ Użytkownik znaleziony:")
            print(f"   ID: {user['id']}")
            print(f"   Email: {user['email']}")
            print(f"   Name: {user['name']}")
            print(f"   Created: {user['created_at']}")
        else:
            print(f"❌ Użytkownik nie znaleziony: {USER_EMAIL}")
            return
        
        # ========================================================================
        # KROK 2: Sprawdź grupy
        # ========================================================================
        print_section("📁 KROK 2: Wszystkie grupy w systemie")
        query = """
            SELECT group_id, group_name, created_by, is_active, created_at
            FROM s02_teamwork.work_groups
            ORDER BY group_id
        """
        groups = execute_query(cursor, query)
        
        if groups:
            print(f"✅ Znaleziono {len(groups)} grup:")
            for g in groups:
                print(f"   [{g['group_id']}] {g['group_name']} (active: {g['is_active']})")
                print(f"       Created by: {g['created_by']}")
        else:
            print("❌ Brak grup w systemie!")
        
        # ========================================================================
        # KROK 3: Sprawdź członkostwa w grupach
        # ========================================================================
        print_section("👥 KROK 3: Wszystkie członkostwa w grupach")
        query = """
            SELECT 
                gm.group_id,
                g.group_name,
                gm.user_id,
                u.email,
                gm.role,
                gm.joined_at
            FROM s02_teamwork.group_members gm
            LEFT JOIN s02_teamwork.work_groups g ON gm.group_id = g.group_id
            LEFT JOIN s01_user_accounts.users u ON gm.user_id = u.id
            ORDER BY gm.group_id, gm.user_id
        """
        memberships = execute_query(cursor, query)
        
        if memberships:
            print(f"✅ Znaleziono {len(memberships)} członkostw:")
            for m in memberships:
                print(f"   Grupa [{m['group_id']}] {m['group_name']}")
                print(f"   └─ User: {m['email']} (role: {m['role']})")
        else:
            print("❌ Brak członkostw w systemie!")
        
        # ========================================================================
        # KROK 4: Sprawdź członkostwa dla naszego użytkownika
        # ========================================================================
        print_section(f"🎯 KROK 4: Członkostwa dla {USER_EMAIL}")
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
        user_groups = execute_query(cursor, query, (USER_ID,))
        
        if user_groups:
            print(f"✅ Użytkownik jest członkiem {len(user_groups)} grup:")
            for ug in user_groups:
                print(f"   [{ug['group_id']}] {ug['group_name']} (role: {ug['role']})")
        else:
            print(f"❌ Użytkownik NIE jest członkiem żadnej grupy!")
            print(f"   To wyjaśnia dlaczego API zwraca pustą listę!")
        
        # ========================================================================
        # KROK 5: Sprawdź tematy
        # ========================================================================
        print_section("📋 KROK 5: Wszystkie tematy w systemie")
        query = """
            SELECT 
                t.topic_id,
                t.topic_name,
                t.group_id,
                g.group_name,
                t.is_active
            FROM s02_teamwork.topics t
            LEFT JOIN s02_teamwork.work_groups g ON t.group_id = g.group_id
            ORDER BY t.topic_id
        """
        topics = execute_query(cursor, query)
        
        if topics:
            print(f"✅ Znaleziono {len(topics)} tematów:")
            for t in topics:
                print(f"   [{t['topic_id']}] {t['topic_name']}")
                print(f"       Grupa: [{t['group_id']}] {t['group_name']}")
        else:
            print("❌ Brak tematów w systemie!")
        
        # ========================================================================
        # KROK 6: Sprawdź zadania
        # ========================================================================
        print_section("✅ KROK 6: Zadania w systemie")
        query = """
            SELECT 
                task_id,
                topic_id,
                task_subject,
                completed,
                is_important
            FROM s02_teamwork.tasks
            ORDER BY topic_id, task_id
        """
        tasks = execute_query(cursor, query)
        
        if tasks:
            print(f"✅ Znaleziono {len(tasks)} zadań:")
            completed = sum(1 for t in tasks if t['completed'])
            important = sum(1 for t in tasks if t['is_important'])
            print(f"   Ukończone: {completed}/{len(tasks)}")
            print(f"   Ważne: {important}/{len(tasks)}")
        else:
            print("❌ Brak zadań w systemie!")
        
        # ========================================================================
        # KROK 7: Test zapytania API endpoint
        # ========================================================================
        print_section("🔬 KROK 7: Symulacja zapytania API /groups")
        query = """
            SELECT 
                g.group_id,
                g.group_name,
                g.description,
                g.created_by,
                g.is_active
            FROM s02_teamwork.work_groups g
            JOIN s02_teamwork.group_members gm ON g.group_id = gm.group_id
            WHERE gm.user_id = %s
            ORDER BY g.group_id
        """
        api_result = execute_query(cursor, query, (USER_ID,))
        
        print(f"📊 Wynik zapytania API:")
        if api_result:
            print(f"✅ API powinno zwrócić {len(api_result)} grup:")
            for r in api_result:
                print(f"   [{r['group_id']}] {r['group_name']}")
        else:
            print(f"❌ API zwraca pustą listę - brak członkostwa!")
        
        # ========================================================================
        # KROK 8: Statystyki ogólne
        # ========================================================================
        print_section("📊 KROK 8: Statystyki ogólne")
        
        stats_queries = {
            "Grupy": "SELECT COUNT(*) FROM s02_teamwork.work_groups",
            "Członkostwa grup": "SELECT COUNT(*) FROM s02_teamwork.group_members",
            "Tematy": "SELECT COUNT(*) FROM s02_teamwork.topics",
            "Członkostwa tematów": "SELECT COUNT(*) FROM s02_teamwork.topic_members",
            "Wiadomości": "SELECT COUNT(*) FROM s02_teamwork.messages",
            "Zadania": "SELECT COUNT(*) FROM s02_teamwork.tasks"
        }
        
        for name, query in stats_queries.items():
            result = execute_query(cursor, query)
            count = result[0]['count'] if result else 0
            status = "✅" if count > 0 else "❌"
            print(f"   {status} {name}: {count}")
        
        # ========================================================================
        # KROK 9: Sprawdź duplikaty
        # ========================================================================
        print_section("🔍 KROK 9: Sprawdzanie duplikatów")
        query = """
            SELECT group_id, user_id, COUNT(*) as count
            FROM s02_teamwork.group_members
            GROUP BY group_id, user_id
            HAVING COUNT(*) > 1
        """
        duplicates = execute_query(cursor, query)
        
        if duplicates:
            print(f"⚠️  Znaleziono {len(duplicates)} duplikatów w group_members!")
            for d in duplicates:
                print(f"   Grupa {d['group_id']}, User {d['user_id']}: {d['count']} wpisów")
        else:
            print("✅ Brak duplikatów w group_members")
        
        # ========================================================================
        # PODSUMOWANIE
        # ========================================================================
        print_section("📝 PODSUMOWANIE DIAGNOSTYKI")
        
        if not user_groups:
            print("❌ PROBLEM ZIDENTYFIKOWANY:")
            print(f"   Użytkownik {USER_EMAIL} NIE jest członkiem żadnej grupy!")
            print(f"   Dlatego API zwraca pustą listę []")
            print()
            print("💡 ROZWIĄZANIE:")
            print("   Wykonaj INSERT do tabeli group_members:")
            print(f"   INSERT INTO s02_teamwork.group_members (group_id, user_id, role)")
            print(f"   VALUES (1, '{USER_ID}', 'owner'), (2, '{USER_ID}', 'owner');")
        else:
            print("✅ Użytkownik ma członkostwa w grupach")
            print("✅ API powinno działać poprawnie")
            print()
            print("🔍 Jeśli API nadal zwraca [], sprawdź:")
            print("   1. Czy topics są dodane z joinedload w endpointcie")
            print("   2. Czy mapowanie w _refresh_groups_from_api jest poprawne")
            print("   3. Czy token JWT zawiera poprawny user_id")
        
        cursor.close()
        conn.close()
        print_section("✅ DIAGNOSTYKA ZAKOŃCZONA")
        
    except Exception as e:
        print(f"\n❌ BŁĄD: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
