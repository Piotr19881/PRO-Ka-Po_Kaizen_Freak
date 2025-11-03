"""
Przykład użycia systemu synchronizacji alarmów.

Ten skrypt demonstruje:
1. Inicjalizację LocalDatabase
2. Konfigurację API Client
3. Uruchomienie Sync Manager
4. Dodawanie alarmów/timerów
5. Automatyczną synchronizację w tle
"""

import time
from datetime import time as dt_time, datetime
from pathlib import Path

# Import komponentów synchronizacji
from src.Modules.Alarm_module.alarm_local_database import LocalDatabase
from src.Modules.Alarm_module.alarm_api_client import AlarmsAPIClient, create_api_client
from src.Modules.Alarm_module.alarms_sync_manager import SyncManager, SyncManagerContext
from src.Modules.Alarm_module.alarms_logic import Alarm, Timer, AlarmRecurrence

from loguru import logger


def example_basic_usage():
    """Podstawowe użycie systemu synchronizacji"""
    
    print("=== Basic Usage Example ===\n")
    
    # 1. Inicjalizacja LocalDatabase
    db_path = Path("data/alarms.db")
    local_db = LocalDatabase(db_path)
    print(f"✓ LocalDatabase initialized: {db_path}")
    
    # 2. Konfiguracja API Client
    api_client = create_api_client(
        base_url="https://api.example.com",  # Zastąp prawdziwym URL
        auth_token="your_auth_token_here"     # Zastąp prawdziwym tokenem
    )
    print("✓ API Client configured")
    
    # 3. Utworzenie Sync Manager
    sync_manager = SyncManager(
        local_db=local_db,
        api_client=api_client,
        user_id="user123",
        sync_interval=30  # Sync co 30 sekund
    )
    print("✓ Sync Manager created")
    
    # 4. Uruchomienie background worker
    sync_manager.start()
    print("✓ Sync worker started\n")
    
    try:
        # 5. Dodaj alarm
        alarm = Alarm(
            id="alarm_001",
            time=dt_time(7, 30),
            label="Pobudka",
            enabled=True,
            recurrence=AlarmRecurrence.WEEKDAYS,
            days=[1, 2, 3, 4, 5],
            play_sound=True,
            show_popup=True,
            custom_sound=None
        )
        
        local_db.save_alarm(alarm, user_id="user123")
        print(f"✓ Alarm saved: {alarm.label} at {alarm.time}")
        
        # 6. Dodaj timer
        timer = Timer(
            id="timer_001",
            duration=300,  # 5 minut
            label="Herbata",
            enabled=True,
            remaining=300,
            play_sound=True,
            show_popup=True,
            repeat=False,
            custom_sound=None
        )
        
        local_db.save_timer(timer, user_id="user123")
        print(f"✓ Timer saved: {timer.label} ({timer.duration}s)")
        
        # 7. Sprawdź kolejkę synchronizacji
        queue = local_db.get_sync_queue()
        print(f"\n✓ Sync queue: {len(queue)} items pending")
        
        # 8. Poczekaj na synchronizację
        print("\nWaiting for sync... (10 seconds)")
        time.sleep(10)
        
        # 9. Sprawdź statystyki
        stats = sync_manager.get_stats()
        print(f"\n=== Sync Stats ===")
        print(f"  Sync count: {stats['sync_count']}")
        print(f"  Error count: {stats['error_count']}")
        print(f"  Queue size: {stats['queue_size']}")
        print(f"  Last sync: {stats['last_sync_time']}")
        
    finally:
        # 10. Zatrzymaj worker
        sync_manager.stop()
        print("\n✓ Sync worker stopped")


def example_context_manager():
    """Użycie z context manager"""
    
    print("\n=== Context Manager Example ===\n")
    
    db_path = Path("data/alarms.db")
    local_db = LocalDatabase(db_path)
    api_client = create_api_client()
    
    sync_manager = SyncManager(
        local_db=local_db,
        api_client=api_client,
        user_id="user123"
    )
    
    # Context manager automatycznie start() i stop()
    with SyncManagerContext(sync_manager) as sm:
        print("✓ Sync manager running")
        
        # Dodaj alarm
        alarm = Alarm(
            id="alarm_002",
            time=dt_time(22, 0),
            label="Wieczorny alarm",
            enabled=True,
            recurrence=AlarmRecurrence.DAILY,
            days=list(range(7)),
            play_sound=True,
            show_popup=True
        )
        
        local_db.save_alarm(alarm, user_id="user123")
        print(f"✓ Alarm saved: {alarm.label}")
        
        # Manualny sync
        sm.sync_now()
        print("✓ Manual sync triggered")
        
        time.sleep(5)
    
    print("✓ Context exited, sync manager stopped")


def example_conflict_resolution():
    """Przykład rozwiązywania konfliktów"""
    
    print("\n=== Conflict Resolution Example ===\n")
    
    api_client = create_api_client()
    
    # Symulacja danych
    local_data = {
        'id': 'alarm_003',
        'label': 'Local version',
        'updated_at': datetime.now().isoformat(),
        'version': 2
    }
    
    server_data = {
        'id': 'alarm_003',
        'label': 'Server version',
        'updated_at': datetime(2024, 1, 10, 10, 0).isoformat(),
        'version': 3
    }
    
    # Rozwiąż konflikt - last write wins
    winning_data, winner = api_client.resolve_conflict(
        local_data=local_data,
        server_data=server_data,
        strategy='last_write_wins'
    )
    
    print(f"Conflict resolved: {winner} wins")
    print(f"Winning label: {winning_data['label']}")


def example_manual_operations():
    """Ręczne operacje bez background worker"""
    
    print("\n=== Manual Operations Example ===\n")
    
    db_path = Path("data/alarms.db")
    local_db = LocalDatabase(db_path)
    api_client = create_api_client()
    
    # 1. Dodaj alarm lokalnie
    alarm = Alarm(
        id="alarm_manual",
        time=dt_time(15, 30),
        label="Spotkanie",
        enabled=True,
        recurrence=AlarmRecurrence.ONCE,
        days=[],
        play_sound=True,
        show_popup=True
    )
    
    local_db.save_alarm(alarm, user_id="user123")
    print(f"✓ Alarm saved locally: {alarm.label}")
    
    # 2. Ręczna synchronizacja (bez background worker)
    try:
        alarm_data = alarm.to_dict()
        response = api_client.sync_alarm(alarm_data, user_id="user123")
        
        if response.success:
            print("✓ Alarm synced to server successfully")
            local_db.mark_alarm_synced(alarm.id)
        else:
            print(f"✗ Sync failed: {response.error}")
    
    except Exception as e:
        print(f"✗ Error syncing: {e}")
    
    # 3. Pobierz z serwera
    try:
        response = api_client.fetch_all(user_id="user123", item_type="alarm")
        
        if response.success:
            alarms = response.data or []
            print(f"✓ Fetched {len(alarms)} alarms from server")
        else:
            print(f"✗ Fetch failed: {response.error}")
    
    except Exception as e:
        print(f"✗ Error fetching: {e}")


def example_health_check():
    """Sprawdzanie health status"""
    
    print("\n=== Health Check Example ===\n")
    
    api_client = create_api_client(
        base_url="https://api.example.com"
    )
    
    # Sprawdź czy serwer jest dostępny
    is_healthy = api_client.health_check()
    
    if is_healthy:
        print("✓ Server is healthy and responding")
    else:
        print("✗ Server is not responding")
    
    # Sprawdź dostępność sieci
    from src.Modules.Alarm_module.alarm_api_client import is_network_available
    
    network_ok = is_network_available()
    if network_ok:
        print("✓ Network is available")
    else:
        print("✗ Network is not available")


def example_stats_monitoring():
    """Monitorowanie statystyk synchronizacji"""
    
    print("\n=== Stats Monitoring Example ===\n")
    
    db_path = Path("data/alarms.db")
    local_db = LocalDatabase(db_path)
    api_client = create_api_client()
    
    sync_manager = SyncManager(
        local_db=local_db,
        api_client=api_client,
        user_id="user123"
    )
    
    sync_manager.start()
    
    try:
        # Dodaj kilka alarmów
        for i in range(3):
            alarm = Alarm(
                id=f"alarm_{i:03d}",
                time=dt_time(8 + i, 0),
                label=f"Alarm {i+1}",
                enabled=True,
                recurrence=AlarmRecurrence.DAILY,
                days=list(range(7)),
                play_sound=True,
                show_popup=True
            )
            local_db.save_alarm(alarm, user_id="user123")
        
        print("✓ Added 3 alarms")
        
        # Poczekaj na sync
        time.sleep(35)
        
        # Pobierz statystyki
        stats = sync_manager.get_stats()
        
        print("\n=== Sync Statistics ===")
        print(f"  Running: {stats['is_running']}")
        print(f"  Total syncs: {stats['sync_count']}")
        print(f"  Errors: {stats['error_count']}")
        print(f"  Conflicts: {stats['conflict_count']}")
        print(f"  Queue size: {stats['queue_size']}")
        print(f"  Network: {'Available' if stats['network_available'] else 'Unavailable'}")
        print(f"  Last sync: {stats['last_sync_time']}")
        
        # Pobierz status kolejki
        queue_status = sync_manager.get_queue_status()
        print(f"\n=== Queue Status ===")
        for item in queue_status[:5]:  # Pokaż pierwsze 5
            print(f"  {item['entity_type']} {item['entity_id']}: {item['operation']} (retry={item['retry_count']})")
    
    finally:
        sync_manager.stop()
        print("\n✓ Sync manager stopped")


def main():
    """Uruchom wszystkie przykłady"""
    
    logger.info("Starting sync examples...")
    
    try:
        # Uwaga: Te przykłady wymagają działającego serwera API
        # Dla testów możesz zakomentować przykłady wymagające serwera
        
        # example_basic_usage()
        # example_context_manager()
        example_conflict_resolution()
        # example_manual_operations()
        # example_health_check()
        # example_stats_monitoring()
        
    except Exception as e:
        logger.error(f"Error in examples: {e}")
        raise
    
    print("\n=== All Examples Completed ===")


if __name__ == "__main__":
    main()
