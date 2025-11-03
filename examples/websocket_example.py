"""
Przykład użycia WebSocket real-time synchronizacji.

Demonstruje:
1. Połączenie WebSocket z serwerem
2. Nasłuchiwanie na zmiany (alarms/timers)
3. Auto-reconnect po rozłączeniu
4. Integracja z LocalDatabase i SyncManager
"""

import sys
from pathlib import Path
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QTimer
from datetime import time as dt_time

# Import komponentów
from src.Modules.Alarm_module.alarm_websocket_client import create_websocket_client
from src.Modules.Alarm_module.alarm_local_database import LocalDatabase
from src.Modules.Alarm_module.alarms_sync_manager import SyncManager
from src.Modules.Alarm_module.alarm_api_client import create_api_client
from src.Modules.Alarm_module.alarms_logic import Alarm, AlarmRecurrence

from loguru import logger


# =============================================================================
# Event Handlers
# =============================================================================

def on_alarm_change(alarm_data: dict):
    """
    Callback wywoływany gdy alarm się zmieni na serwerze.
    
    Args:
        alarm_data: Dane alarmu z serwera
    """
    logger.info(f"[WebSocket] Alarm changed: {alarm_data.get('id')} - {alarm_data.get('label')}")
    
    # Opcjonalnie: Zaktualizuj lokalną bazę
    # local_db = ...
    # local_db.update_from_server(alarm_data)
    
    print(f"  ID: {alarm_data.get('id')}")
    print(f"  Label: {alarm_data.get('label')}")
    print(f"  Time: {alarm_data.get('alarm_time')}")
    print(f"  Enabled: {alarm_data.get('enabled')}")
    print(f"  Version: {alarm_data.get('version')}")


def on_timer_change(timer_data: dict):
    """Callback dla zmian timerów"""
    logger.info(f"[WebSocket] Timer changed: {timer_data.get('id')} - {timer_data.get('label')}")
    print(f"  Duration: {timer_data.get('duration')}s")


def on_sync_required(reason: str):
    """
    Callback gdy serwer wymaga synchronizacji.
    
    Args:
        reason: Powód wymaganej synchronizacji
    """
    logger.warning(f"[WebSocket] Sync required: {reason}")
    
    # Tutaj możesz wywołać sync_manager.sync_now()
    print(f"  -> Triggering sync: {reason}")


def on_connected():
    """Callback po połączeniu"""
    logger.success("[WebSocket] Connected to server!")
    print("  -> Real-time updates enabled")


def on_disconnected():
    """Callback po rozłączeniu"""
    logger.warning("[WebSocket] Disconnected from server")
    print("  -> Will auto-reconnect...")


def on_error(error_msg: str):
    """Callback dla błędów"""
    logger.error(f"[WebSocket] Error: {error_msg}")


# =============================================================================
# Example 1: Basic WebSocket Usage
# =============================================================================

def example_basic_websocket():
    """Podstawowe użycie WebSocket"""
    print("=== Basic WebSocket Example ===\n")
    
    # Konfiguracja
    BASE_URL = "http://localhost:8000"
    AUTH_TOKEN = "your_jwt_token_here"  # Zastąp prawdziwym tokenem
    
    # Utwórz aplikację Qt (wymagane dla QThread)
    app = QApplication(sys.argv)
    
    # Utwórz WebSocket client
    ws_client = create_websocket_client(
        base_url=BASE_URL,
        auth_token=AUTH_TOKEN,
        on_alarm_updated=on_alarm_change,
        on_timer_updated=on_timer_change,
        on_sync_required=on_sync_required,
        auto_reconnect=True
    )
    
    # Podłącz dodatkowe sygnały
    ws_client.connected.connect(on_connected)
    ws_client.disconnected.connect(on_disconnected)
    ws_client.error.connect(on_error)
    
    # Uruchom WebSocket w tle
    ws_client.start()
    print("WebSocket client started...\n")
    
    # Wysyłaj ping co 10 sekund
    ping_timer = QTimer()
    ping_timer.timeout.connect(ws_client.send_ping)
    ping_timer.start(10000)
    
    # Zatrzymaj po 60 sekundach (dla demo)
    def stop_demo():
        print("\n=== Stopping demo ===")
        ping_timer.stop()
        ws_client.stop()
        app.quit()
    
    QTimer.singleShot(60000, stop_demo)
    
    # Uruchom event loop
    print("Listening for 60 seconds...\n")
    sys.exit(app.exec())


# =============================================================================
# Example 2: WebSocket + SyncManager Integration
# =============================================================================

def example_websocket_with_sync():
    """WebSocket zintegrowany z SyncManager"""
    print("=== WebSocket + SyncManager Example ===\n")
    
    # Konfiguracja
    BASE_URL = "http://localhost:8000"
    AUTH_TOKEN = "your_jwt_token_here"
    USER_ID = "user123"
    
    app = QApplication(sys.argv)
    
    # Setup LocalDatabase
    db_path = Path("data/alarms.db")
    local_db = LocalDatabase(db_path)
    print(f"LocalDatabase initialized: {db_path}\n")
    
    # Setup API Client
    api_client = create_api_client(
        base_url=BASE_URL,
        auth_token=AUTH_TOKEN
    )
    
    # Setup SyncManager
    sync_manager = SyncManager(
        local_db=local_db,
        api_client=api_client,
        user_id=USER_ID,
        sync_interval=30
    )
    sync_manager.start()
    print("SyncManager started\n")
    
    # Callback: Gdy serwer wymaga sync -> wywołaj sync_now()
    def trigger_sync(reason: str):
        logger.info(f"Server requested sync: {reason}")
        print(f"  -> Syncing now: {reason}")
        sync_manager.sync_now()
    
    # Callback: Gdy alarm się zmieni -> zaktualizuj UI
    def refresh_alarm(alarm_data: dict):
        logger.info(f"Alarm changed on server: {alarm_data.get('label')}")
        print(f"  -> UI should refresh alarm: {alarm_data.get('id')}")
        # Tutaj: emit signal do UI, albo bezpośrednio zaktualizuj widok
    
    # Setup WebSocket
    ws_client = create_websocket_client(
        base_url=BASE_URL,
        auth_token=AUTH_TOKEN,
        on_alarm_updated=refresh_alarm,
        on_sync_required=trigger_sync,
        auto_reconnect=True
    )
    
    ws_client.connected.connect(lambda: print("[WS] Connected - real-time sync active\n"))
    ws_client.disconnected.connect(lambda: print("[WS] Disconnected - falling back to polling\n"))
    
    # Uruchom WebSocket
    ws_client.start()
    
    # Dodaj przykładowy alarm lokalnie (wywoła sync)
    print("Creating alarm locally...\n")
    alarm = Alarm(
        id="alarm_ws_test",
        time=dt_time(10, 30),
        label="WebSocket Test Alarm",
        enabled=True,
        recurrence=AlarmRecurrence.DAILY,
        days=list(range(7)),
        play_sound=True,
        show_popup=True
    )
    
    local_db.save_alarm(alarm, user_id=USER_ID)
    print(f"Alarm saved: {alarm.label}")
    print("  -> Will be synced to server by SyncManager")
    print("  -> Changes on server will trigger WebSocket event\n")
    
    # Cleanup po 120 sekundach
    def cleanup():
        print("\n=== Cleanup ===")
        ws_client.stop()
        sync_manager.stop()
        app.quit()
    
    QTimer.singleShot(120000, cleanup)
    
    print("Running for 2 minutes...\n")
    print("Try modifying the alarm on server - you'll see WebSocket event!\n")
    
    sys.exit(app.exec())


# =============================================================================
# Example 3: Manual WebSocket Testing
# =============================================================================

def example_manual_testing():
    """Ręczne testowanie WebSocket bez auto-sync"""
    print("=== Manual WebSocket Testing ===\n")
    
    BASE_URL = "http://localhost:8000"
    AUTH_TOKEN = "your_jwt_token_here"
    
    app = QApplication(sys.argv)
    
    # Event counters
    events = {
        "connected": 0,
        "disconnected": 0,
        "alarms": 0,
        "timers": 0,
        "syncs": 0,
        "errors": 0
    }
    
    # Callbacks z licznikami
    def count_alarm(data):
        events["alarms"] += 1
        print(f"[{events['alarms']}] Alarm event: {data.get('label', 'N/A')}")
    
    def count_timer(data):
        events["timers"] += 1
        print(f"[{events['timers']}] Timer event: {data.get('label', 'N/A')}")
    
    def count_sync(reason):
        events["syncs"] += 1
        print(f"[{events['syncs']}] Sync required: {reason}")
    
    # WebSocket client
    ws_client = create_websocket_client(
        base_url=BASE_URL,
        auth_token=AUTH_TOKEN,
        on_alarm_updated=count_alarm,
        on_timer_updated=count_timer,
        on_sync_required=count_sync
    )
    
    ws_client.connected.connect(lambda: events.update({"connected": events["connected"] + 1}))
    ws_client.disconnected.connect(lambda: events.update({"disconnected": events["disconnected"] + 1}))
    ws_client.error.connect(lambda e: events.update({"errors": events["errors"] + 1}))
    
    ws_client.start()
    
    # Wyświetl statystyki co 10 sekund
    def print_stats():
        print("\n=== Statistics ===")
        print(f"  Connections: {events['connected']}")
        print(f"  Disconnections: {events['disconnected']}")
        print(f"  Alarm events: {events['alarms']}")
        print(f"  Timer events: {events['timers']}")
        print(f"  Sync requests: {events['syncs']}")
        print(f"  Errors: {events['errors']}")
        print(f"  Status: {'Connected' if ws_client.is_connected() else 'Disconnected'}\n")
    
    stats_timer = QTimer()
    stats_timer.timeout.connect(print_stats)
    stats_timer.start(10000)
    
    # Cleanup
    def cleanup():
        stats_timer.stop()
        print_stats()
        ws_client.stop()
        app.quit()
    
    QTimer.singleShot(60000, cleanup)
    
    print("Testing for 60 seconds...\n")
    print("Instructions:")
    print("1. Create/update/delete alarms via API or UI")
    print("2. Watch for WebSocket events in console")
    print("3. Statistics will be printed every 10s\n")
    
    sys.exit(app.exec())


# =============================================================================
# Main
# =============================================================================

def main():
    """Uruchom przykłady"""
    
    print("\nWebSocket Real-time Sync Examples")
    print("=" * 50)
    print("\nAvailable examples:")
    print("1. Basic WebSocket - connect and listen")
    print("2. WebSocket + SyncManager - full integration")
    print("3. Manual testing - event counting\n")
    
    choice = input("Select example (1-3) or 'q' to quit: ").strip()
    
    if choice == "1":
        example_basic_websocket()
    elif choice == "2":
        example_websocket_with_sync()
    elif choice == "3":
        example_manual_testing()
    elif choice.lower() == "q":
        print("Goodbye!")
    else:
        print("Invalid choice!")
        main()


if __name__ == "__main__":
    # Uwaga: Wymagany działający serwer z WebSocket support
    # Zastąp AUTH_TOKEN prawdziwym tokenem JWT przed uruchomieniem
    
    logger.info("Starting WebSocket examples...")
    
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        logger.error(f"Error: {e}")
        raise
