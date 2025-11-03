"""
Przykład użycia zintegrowanego AlarmManager z synchronizacją.

Pokazuje:
1. Inicjalizację z sync (local-first + WebSocket)
2. Inicjalizację bez sync (tylko JSON)
3. Operacje CRUD
4. Real-time updates przez WebSocket
5. UI callbacks
"""

import sys
from pathlib import Path
from datetime import time
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer

from src.Modules.Alarm_module.alarms_logic import AlarmManager, Alarm, AlarmRecurrence, Timer
from loguru import logger


# =============================================================================
# Przykład 1: AlarmManager BEZ synchronizacji (tylko local JSON)
# =============================================================================

def example_without_sync():
    """Użycie AlarmManager bez synchronizacji - tylko local storage"""
    
    print("\n=== Example 1: Without Sync (JSON only) ===\n")
    
    # Inicjalizacja bez sync
    data_dir = Path("data/alarms_no_sync")
    alarm_manager = AlarmManager(
        data_dir=data_dir,
        enable_sync=False  # Wyłącz sync
    )
    
    print(f"Loaded {len(alarm_manager.alarms)} alarms from JSON")
    print(f"Loaded {len(alarm_manager.timers)} timers from JSON")
    
    # Dodaj alarm
    alarm = Alarm(
        id="alarm_001",
        time=time(7, 30),
        label="Pobudka",
        enabled=True,
        recurrence=AlarmRecurrence.WEEKDAYS,
        days=[0, 1, 2, 3, 4]  # Pon-Pt
    )
    
    if alarm_manager.add_alarm(alarm):
        print(f"✓ Alarm added: {alarm.label}")
    
    # Dodaj timer
    timer = Timer(
        id="timer_001",
        duration=300,  # 5 minut
        label="Herbata",
        enabled=False
    )
    
    if alarm_manager.add_timer(timer):
        print(f"✓ Timer added: {timer.label}")
    
    print(f"\nTotal: {len(alarm_manager.alarms)} alarms, {len(alarm_manager.timers)} timers")


# =============================================================================
# Przykład 2: AlarmManager Z synchronizacją (local-first + server)
# =============================================================================

def example_with_sync():
    """Użycie AlarmManager z synchronizacją"""
    
    print("\n=== Example 2: With Sync (LocalDB + Server + WebSocket) ===\n")
    
    # Konfiguracja
    BASE_URL = "http://localhost:8000"
    AUTH_TOKEN = "your_jwt_token_here"  # Zastąp prawdziwym tokenem
    USER_ID = "user123"
    
    # Wymagana aplikacja Qt dla WebSocket
    app = QApplication(sys.argv)
    
    # Inicjalizacja Z sync
    data_dir = Path("data/alarms_with_sync")
    alarm_manager = AlarmManager(
        data_dir=data_dir,
        user_id=USER_ID,
        api_base_url=BASE_URL,
        auth_token=AUTH_TOKEN,
        enable_sync=True  # Włącz sync!
    )
    
    print(f"Loaded {len(alarm_manager.alarms)} alarms from LocalDatabase")
    print(f"Loaded {len(alarm_manager.timers)} timers from LocalDatabase")
    
    # Dodaj alarm - automatycznie się zsynchronizuje
    alarm = Alarm(
        id="alarm_sync_001",
        time=time(8, 0),
        label="Pobudka ze synchronizacją",
        enabled=True,
        recurrence=AlarmRecurrence.DAILY,
        days=list(range(7))
    )
    
    if alarm_manager.add_alarm(alarm):
        print(f"✓ Alarm saved to LocalDatabase (will auto-sync)")
    
    # Sprawdź statystyki sync
    stats = alarm_manager.get_sync_stats()
    if stats:
        print(f"\nSync stats:")
        print(f"  Sync count: {stats['sync_count']}")
        print(f"  Queue size: {stats['queue_size']}")
        print(f"  WebSocket: {'Connected' if alarm_manager.is_websocket_connected() else 'Disconnected'}")
    
    # Poczekaj 10 sekund na sync
    print("\nWaiting 10s for background sync...")
    
    def check_sync():
        stats = alarm_manager.get_sync_stats()
        if stats:
            print(f"\nAfter sync:")
            print(f"  Synced: {stats['sync_count']} times")
            print(f"  Queue: {stats['queue_size']} items")
        
        alarm_manager.cleanup()
        app.quit()
    
    QTimer.singleShot(10000, check_sync)
    
    sys.exit(app.exec())


# =============================================================================
# Przykład 3: Real-time UI updates przez WebSocket
# =============================================================================

def example_realtime_ui():
    """Przykład real-time UI updates"""
    
    print("\n=== Example 3: Real-time UI Updates ===\n")
    
    BASE_URL = "http://localhost:8000"
    AUTH_TOKEN = "your_jwt_token_here"
    USER_ID = "user123"
    
    app = QApplication(sys.argv)
    
    # Inicjalizacja
    data_dir = Path("data/alarms_realtime")
    alarm_manager = AlarmManager(
        data_dir=data_dir,
        user_id=USER_ID,
        api_base_url=BASE_URL,
        auth_token=AUTH_TOKEN,
        enable_sync=True
    )
    
    # Liczniki eventów
    events = {"alarms": 0, "timers": 0}
    
    # Callbacks dla UI
    def on_alarm_changed(alarm: Alarm):
        """Callback wywoływany gdy alarm się zmieni (przez WebSocket)"""
        events["alarms"] += 1
        print(f"\n[{events['alarms']}] ALARM CHANGED:")
        print(f"  ID: {alarm.id}")
        print(f"  Label: {alarm.label}")
        print(f"  Time: {alarm.time}")
        print(f"  Enabled: {alarm.enabled}")
        
        # Tutaj: odśwież UI
        # self.alarm_list_widget.refresh()
    
    def on_timer_changed(timer: Timer):
        """Callback wywoływany gdy timer się zmieni (przez WebSocket)"""
        events["timers"] += 1
        print(f"\n[{events['timers']}] TIMER CHANGED:")
        print(f"  ID: {timer.id}")
        print(f"  Label: {timer.label}")
        print(f"  Duration: {timer.duration}s")
        print(f"  Enabled: {timer.enabled}")
        
        # Tutaj: odśwież UI
        # self.timer_list_widget.refresh()
    
    # Zarejestruj callbacki
    alarm_manager.set_ui_callbacks(
        on_alarm_changed=on_alarm_changed,
        on_timer_changed=on_timer_changed
    )
    
    print("Listening for WebSocket events...")
    print("Try modifying alarms/timers from another device or API!")
    print("\nWaiting 60 seconds...\n")
    
    # Cleanup po 60s
    def cleanup():
        print(f"\n=== Summary ===")
        print(f"Alarm events received: {events['alarms']}")
        print(f"Timer events received: {events['timers']}")
        
        alarm_manager.cleanup()
        app.quit()
    
    QTimer.singleShot(60000, cleanup)
    
    sys.exit(app.exec())


# =============================================================================
# Przykład 4: Migracja z JSON do sync
# =============================================================================

def example_migration():
    """Migracja danych z JSON do LocalDatabase"""
    
    print("\n=== Example 4: Migration from JSON to Sync ===\n")
    
    # Krok 1: Załaduj z JSON (stary sposób)
    data_dir = Path("data/alarms_old")
    old_manager = AlarmManager(
        data_dir=data_dir,
        enable_sync=False
    )
    
    print(f"Old system (JSON):")
    print(f"  Alarms: {len(old_manager.alarms)}")
    print(f"  Timers: {len(old_manager.timers)}")
    
    # Krok 2: Utwórz nowy manager Z sync
    BASE_URL = "http://localhost:8000"
    AUTH_TOKEN = "your_jwt_token_here"
    USER_ID = "user123"
    
    app = QApplication(sys.argv)
    
    new_data_dir = Path("data/alarms_new")
    new_manager = AlarmManager(
        data_dir=new_data_dir,
        user_id=USER_ID,
        api_base_url=BASE_URL,
        auth_token=AUTH_TOKEN,
        enable_sync=True
    )
    
    # Krok 3: Migruj dane
    print("\nMigrating...")
    
    migrated_alarms = 0
    for alarm in old_manager.alarms:
        if new_manager.add_alarm(alarm):
            migrated_alarms += 1
    
    migrated_timers = 0
    for timer in old_manager.timers:
        if new_manager.add_timer(timer):
            migrated_timers += 1
    
    print(f"✓ Migrated {migrated_alarms} alarms")
    print(f"✓ Migrated {migrated_timers} timers")
    print("\nData will sync to server automatically!")
    
    # Poczekaj na sync
    def finish_migration():
        stats = new_manager.get_sync_stats()
        if stats:
            print(f"\nSync completed: {stats['sync_count']} times")
        
        new_manager.cleanup()
        app.quit()
    
    QTimer.singleShot(15000, finish_migration)
    
    print("\nWaiting 15s for sync...\n")
    sys.exit(app.exec())


# =============================================================================
# Przykład 5: Użycie w PyQt6 aplikacji
# =============================================================================

class AlarmApp:
    """Przykładowa aplikacja z AlarmManager"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        
        # Inicjalizacja AlarmManager
        self.alarm_manager = AlarmManager(
            data_dir=Path("data/app"),
            user_id="user123",
            api_base_url="http://localhost:8000",
            auth_token="token_here",
            enable_sync=True
        )
        
        # Zarejestruj UI callbacks
        self.alarm_manager.set_ui_callbacks(
            on_alarm_changed=self.refresh_alarm_list,
            on_timer_changed=self.refresh_timer_list
        )
        
        print("App initialized with sync enabled")
        print(f"Alarms: {len(self.alarm_manager.alarms)}")
        print(f"Timers: {len(self.alarm_manager.timers)}")
    
    def refresh_alarm_list(self, alarm: Alarm):
        """Odśwież listę alarmów w UI"""
        print(f"UI: Refreshing alarm list (changed: {alarm.label})")
        # Tutaj: self.alarm_list_widget.refresh()
    
    def refresh_timer_list(self, timer: Timer):
        """Odśwież listę timerów w UI"""
        print(f"UI: Refreshing timer list (changed: {timer.label})")
        # Tutaj: self.timer_list_widget.refresh()
    
    def create_alarm(self):
        """Handler dla przycisku "Dodaj alarm" """
        alarm = Alarm(
            id=f"alarm_{len(self.alarm_manager.alarms)}",
            time=time(9, 0),
            label="Nowy alarm",
            enabled=True,
            recurrence=AlarmRecurrence.DAILY,
            days=list(range(7))
        )
        
        if self.alarm_manager.add_alarm(alarm):
            print(f"✓ Alarm created: {alarm.label}")
            # Automatycznie zsynchronizuje się w tle
    
    def closeEvent(self):
        """Handler zamknięcia aplikacji"""
        print("\nCleaning up...")
        self.alarm_manager.cleanup()
        self.app.quit()
    
    def run(self):
        """Uruchom aplikację"""
        # Dodaj przykładowy alarm
        self.create_alarm()
        
        # Symuluj zamknięcie po 10s
        QTimer.singleShot(10000, self.closeEvent)
        
        print("\nApp running for 10s...\n")
        sys.exit(self.app.exec())


def example_app():
    """Przykład użycia w aplikacji"""
    print("\n=== Example 5: PyQt6 App Integration ===\n")
    
    app = AlarmApp()
    app.run()


# =============================================================================
# Main
# =============================================================================

def main():
    """Uruchom przykłady"""
    
    print("\n" + "=" * 60)
    print("AlarmManager Integration Examples")
    print("=" * 60)
    print("\nAvailable examples:")
    print("1. Without sync (JSON only)")
    print("2. With sync (LocalDB + Server + WebSocket)")
    print("3. Real-time UI updates")
    print("4. Migration from JSON to sync")
    print("5. PyQt6 app integration")
    print()
    
    choice = input("Select example (1-5) or 'q' to quit: ").strip()
    
    if choice == "1":
        example_without_sync()
    elif choice == "2":
        example_with_sync()
    elif choice == "3":
        example_realtime_ui()
    elif choice == "4":
        example_migration()
    elif choice == "5":
        example_app()
    elif choice.lower() == "q":
        print("Goodbye!")
    else:
        print("Invalid choice!")
        main()


if __name__ == "__main__":
    logger.info("Starting AlarmManager integration examples...")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
