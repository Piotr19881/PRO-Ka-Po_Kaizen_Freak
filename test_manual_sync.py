#!/usr/bin/env python3
"""
Test ręcznej synchronizacji habit trackera
"""
import sys
import asyncio
import sqlite3
from pathlib import Path

# Dodaj ścieżkę projektu
sys.path.append(str(Path(__file__).parent / "src"))

# Import bezpośredni - omijamy __init__.py który importuje view
sys.path.append(str(Path(__file__).parent / "src" / "Modules" / "habbit_tracker_module"))

from habit_database import HabitDatabase
from habit_api_client import HabitAPIClient
from habit_sync_manager import HabitSyncManager

async def test_manual_sync():
    """Test ręcznej synchronizacji"""
    print("🧪 Testowanie ręcznej synchronizacji habit trackera...")
    
    # 1. Inicjalizacja lokalnej bazy
    db_path = Path("src/database/habit_tracker.db")
    if not db_path.exists():
        print("❌ Baza habit_tracker.db nie istnieje!")
        return
    
    habit_db = HabitDatabase(db_path, user_id=1)
    print(f"✅ Połączono z lokalną bazą: {db_path}")
    
    # 2. Sprawdź lokalne dane
    print("\n📊 LOKALNE DANE:")
    columns = habit_db.get_all_columns()
    print(f"  Kolumny: {len(columns)}")
    for col in columns:
        print(f"    - {col}")
    
    records = habit_db.get_all_records()
    print(f"  Rekordy: {len(records)}")
    
    # 3. Sprawdź sync queue
    print(f"\n🔄 SYNC QUEUE:")
    pending_items = habit_db.get_pending_sync_items()
    print(f"  Elementy do synchronizacji: {len(pending_items)}")
    for item in pending_items:
        print(f"    - {item}")
    
    # 4. Test API Client
    print(f"\n🌐 TEST API CLIENT:")
    try:
        api_client = HabitAPIClient()
        
        # Test połączenia z serwerem
        server_columns = await api_client.get_columns(user_id=1)
        print(f"  Kolumny na serwerze: {len(server_columns)} - {server_columns}")
        
        # Test ręcznej synchronizacji
        if pending_items:
            print(f"\n🚀 URUCHOMIENIE RĘCZNEJ SYNCHRONIZACJI...")
            sync_manager = HabitSyncManager(
                api_client=api_client,
                habit_db=habit_db,
                sync_interval=60,  # nie uruchamiaj automatycznie
                max_retries=3
            )
            
            # Wykonaj jednorazową synchronizację
            await sync_manager._sync_once()
            print("✅ Synchronizacja zakończona!")
            
            # Sprawdź ponownie serwer
            server_columns_after = await api_client.get_columns(user_id=1)
            print(f"  Kolumny na serwerze po sync: {len(server_columns_after)}")
            for col in server_columns_after:
                print(f"    - {col}")
        else:
            print("  Brak elementów do synchronizacji")
            
    except Exception as e:
        print(f"❌ Błąd API: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_manual_sync())