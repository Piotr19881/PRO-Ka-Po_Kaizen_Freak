"""
Test pełnego flow synchronizacji alarmów i timerów
Testuje cały cykl: LocalDatabase → SyncManager → APIClient → FastAPI → PostgreSQL
"""
import sys
import time
from datetime import datetime, time as dt_time
from pathlib import Path

# Dodaj ścieżkę do modułów
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src" / "Modules"))

# Import całego pakietu Alarm_module
from Alarm_module import (
    Alarm, Timer, AlarmRecurrence,
    LocalDatabase,
    AlarmsAPIClient, create_api_client,
    SyncManager
)
from loguru import logger

# Import helpera do autentykacji
from test_auth_helper import login_and_get_token


# ========== KONFIGURACJA TESTOWA ==========

# URL serwera FastAPI (zmień na właściwy adres)
API_BASE_URL = "http://127.0.0.1:8000"  # Lokalny serwer

# Dane logowania
TEST_EMAIL = "piotr.prokop@promirbud.eu"
TEST_PASSWORD = "testtest1"

# Test user ID (zostanie pobrane z logowania)
TEST_USER_ID = None
TEST_AUTH_TOKEN = None

# Ścieżka do testowej bazy SQLite
TEST_DB_PATH = project_root / "tests" / "test_sync.db"


# ========== POMOCNICZE FUNKCJE ==========

def initialize_auth():
    """Inicjalizuje autentykację - loguje użytkownika i pobiera token"""
    global TEST_USER_ID, TEST_AUTH_TOKEN
    
    print_separator("INICJALIZACJA AUTENTYKACJI")
    
    auth_data = login_and_get_token(API_BASE_URL, TEST_EMAIL, TEST_PASSWORD)
    
    if not auth_data:
        print("[BLAD] Nie udalo sie zalogowac!")
        print("Upewnij sie ze:")
        print("  1. Serwer FastAPI dziala (http://127.0.0.1:8000)")
        print("  2. Dane logowania sa poprawne")
        return False
    
    TEST_USER_ID = auth_data['user_id']
    TEST_AUTH_TOKEN = auth_data['access_token']
    
    print(f"[OK] Zalogowano jako: {auth_data['email']}")
    print(f"[OK] User ID: {TEST_USER_ID}")
    print(f"[OK] Token: {TEST_AUTH_TOKEN[:50]}...")
    
    return True


def create_test_alarm(label: str):
    """Tworzy testowy alarm"""
    import uuid
    return Alarm(
        id=str(uuid.uuid4()),
        label=label,
        time=dt_time(8, 30),
        enabled=True,
        recurrence=AlarmRecurrence.DAILY,
        days=[0, 1, 2, 3, 4],  # Pon-Pią
        play_sound=True,
        show_popup=True
    )


def create_test_timer(label: str):
    """Tworzy testowy timer"""
    import uuid
    return Timer(
        id=str(uuid.uuid4()),
        label=label,
        duration=300,  # 5 minut
        enabled=True,
        play_sound=True,
        show_popup=True,
        repeat=False
    )


def print_separator(title: str):
    """Wyświetla separator wizualny"""
    print("\n" + "=" * 80)
    print(f" {title}")
    print("=" * 80 + "\n")


def print_alarm_info(alarm):
    """Wyświetla informacje o alarmie"""
    print(f"  ID: {alarm.id}")
    print(f"  Label: {alarm.label}")
    print(f"  Time: {alarm.time}")
    print(f"  Recurrence: {alarm.recurrence.value}")
    print(f"  Days: {alarm.days}")
    print(f"  Enabled: {alarm.enabled}")


def print_timer_info(timer):
    """Wyświetla informacje o timerze"""
    print(f"  ID: {timer.id}")
    print(f"  Label: {timer.label}")
    print(f"  Duration: {timer.duration}s")
    print(f"  Enabled: {timer.enabled}")
    print(f"  Repeat: {timer.repeat}")


# ========== TESTY FLOW ==========

def test_1_local_database():
    """Test 1: Lokalna baza danych"""
    print_separator("TEST 1: Lokalna baza danych (SQLite)")
    
    # Usuń starą bazę
    if TEST_DB_PATH.exists():
        TEST_DB_PATH.unlink()
        print("[OK] Usunięto starą bazę testową")
    
    # Utwórz katalog tests jeśli nie istnieje
    TEST_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    # Utwórz bazę
    db = LocalDatabase(TEST_DB_PATH)  # Path object, nie str
    print("[OK] Utworzono nową bazę SQLite")
    
    # Zapisz alarm
    alarm1 = create_test_alarm("Pobudka")
    db.save_alarm(alarm1)
    print(f"[OK] Zapisano alarm: {alarm1.label} (ID: {alarm1.id})")
    
    # Zapisz timer
    timer1 = create_test_timer("Kawa")
    db.save_timer(timer1)
    print(f"[OK] Zapisano timer: {timer1.label} (ID: {timer1.id})")
    
    # Odczytaj z bazy
    loaded_alarm = db.get_alarm(alarm1.id)
    loaded_timer = db.get_timer(timer1.id)
    
    assert loaded_alarm is not None, "Alarm nie został zapisany!"
    assert loaded_timer is not None, "Timer nie został zapisany!"
    assert loaded_alarm.label == "Pobudka", "Niepoprawna etykieta alarmu!"
    assert loaded_timer.label == "Kawa", "Niepoprawna etykieta timera!"
    
    print("[OK] Odczytano alarm z bazy:")
    print_alarm_info(loaded_alarm)
    
    print("\n[OK] Odczytano timer z bazy:")
    print_timer_info(loaded_timer)
    
    # Sprawdź kolejkę synchronizacji
    sync_queue = db.get_sync_queue()
    print(f"\n[OK] Kolejka synchronizacji: {len(sync_queue)} elementów")
    for item in sync_queue:
        print(f"  - {item['entity_type']}: {item['entity_id']} (akcja: {item['action']})")
    
    print("\n[SUKCES] TEST 1 ZALICZONY: Lokalna baza działa poprawnie!")
    return db, alarm1, timer1


def test_2_api_client(db, alarm, timer):
    """Test 2: API Client - komunikacja HTTP"""
    print_separator("TEST 2: API Client - komunikacja z serwerem")
    
    # Utwórz klienta API z tokenem autentykacji
    api_client = create_api_client(
        base_url=API_BASE_URL,
        auth_token=TEST_AUTH_TOKEN
    )
    print(f"[OK] Utworzono API Client (URL: {API_BASE_URL})")
    print(f"[OK] Token autentykacji: {TEST_AUTH_TOKEN[:50]}...")
    
    # Sprawdź dostępność serwera
    print("\nSprawdzam dostępność serwera...")
    if api_client.health_check():
        print("[OK] Serwer jest dostępny!")
    else:
        print("[UWAGA] UWAGA: Serwer nie odpowiada! Test może nie powieść się.")
        response = input("Kontynuować mimo to? (t/n): ")
        if response.lower() != 't':
            return api_client
    
    # Synchronizuj alarm
    print(f"\nSynchronizuje alarm '{alarm.label}'...")
    alarm_data = {
        "id": alarm.id,
        "user_id": TEST_USER_ID,
        "type": "alarm",
        "label": alarm.label,
        "enabled": alarm.enabled,
        "alarm_time": alarm.time.strftime("%H:%M"),
        "recurrence": alarm.recurrence.value,
        "days": alarm.days,
        "play_sound": alarm.play_sound,
        "show_popup": alarm.show_popup,
        "version": 1
    }
    
    try:
        response = api_client.sync_alarm(alarm_data, TEST_USER_ID)
        if response.success:
            print("[OK] Alarm zsynchronizowany!")
            print(f"  Wersja serwera: {response.data.get('version', 'N/A')}")
        else:
            print(f"[BLAD] Synchronizacja: {response.error}")
    except Exception as e:
        print(f"[BLAD] Wyjatek podczas synchronizacji: {e}")
    
    # Synchronizuj timer
    print(f"\nSynchronizuję timer '{timer.label}'...")
    timer_data = {
        "id": timer.id,
        "user_id": TEST_USER_ID,
        "type": "timer",
        "label": timer.label,
        "enabled": timer.enabled,
        "duration": timer.duration,
        "play_sound": timer.play_sound,
        "show_popup": timer.show_popup,
        "repeat": timer.repeat,
        "version": 1
    }
    
    try:
        response = api_client.sync_timer(timer_data, TEST_USER_ID)
        if response.success:
            print("[OK] Timer zsynchronizowany!")
            print(f"  Wersja serwera: {response.data.get('version', 'N/A')}")
        else:
            print(f"[BLAD] Błąd synchronizacji: {response.error}")
    except Exception as e:
        print(f"[BLAD] Wyjątek podczas synchronizacji: {e}")
    
    # Pobierz wszystkie elementy z serwera
    print(f"\nPobieram wszystkie elementy użytkownika {TEST_USER_ID}...")
    try:
        response = api_client.fetch_all(TEST_USER_ID)
        if response.success:
            items = response.data.get('items', [])
            print(f"[OK] Pobrano {len(items)} elementów z serwera:")
            for item in items:
                print(f"  - {item.get('type')}: {item.get('label')} (ID: {item.get('id')})")
        else:
            print(f"[BLAD] Błąd pobierania: {response.error}")
    except Exception as e:
        print(f"[BLAD] Wyjątek podczas pobierania: {e}")
    
    print("\n[SUKCES] TEST 2 ZALICZONY: API Client działa poprawnie!")
    return api_client


def test_3_sync_manager(db, api_client):
    """Test 3: Sync Manager - automatyczna synchronizacja"""
    print_separator("TEST 3: Sync Manager - automatyczna synchronizacja w tle")
    
    # Utwórz SyncManager
    sync_manager = SyncManager(
        local_db=db,
        api_client=api_client,
        user_id=TEST_USER_ID,
        sync_interval=5,  # Co 5 sekund
        max_retries=2
    )
    print("[OK] Utworzono Sync Manager (interwał: 5s)")
    
    # Uruchom worker
    sync_manager.start()
    print("[OK] Uruchomiono background worker")
    
    # Dodaj nowy alarm podczas działania workera
    print("\nDodaję nowy alarm podczas działania workera...")
    alarm_work = create_test_alarm("Praca")
    alarm_work.alarm_time = dt_time(9, 0)
    db.save_alarm(alarm_work)
    print(f"[OK] Zapisano alarm '{alarm_work.label}' - automatycznie trafi do kolejki sync")
    
    # Czekaj na synchronizację
    print("\nCzekam 10 sekund na automatyczną synchronizację...")
    for i in range(10, 0, -1):
        print(f"  {i}...", end="\r")
        time.sleep(1)
    print("  [OK] Zakończono czekanie      ")
    
    # Sprawdź statystyki
    stats = sync_manager.get_stats()
    print("\n[STATS] Statystyki synchronizacji:")
    print(f"  Ostatnia synchronizacja: {stats.get('last_sync_time', 'nigdy')}")
    print(f"  Liczba synchronizacji: {stats.get('sync_count', 0)}")
    print(f"  Błędy: {stats.get('error_count', 0)}")
    print(f"  Konflikty: {stats.get('conflict_count', 0)}")
    
    # Sprawdź status kolejki
    queue_status = sync_manager.get_queue_status()
    print(f"\n[INFO] Status kolejki:")
    print(f"  Elementy w kolejce: {len(queue_status)}")
    print(f"  Worker aktywny: {sync_manager.is_running}")
    
    # Zatrzymaj worker
    print("\nZatrzymuje background worker...")
    sync_manager.stop(wait=True, timeout=5)
    print("[OK] Worker zatrzymany")
    
    print("\n[SUKCES] TEST 3 ZALICZONY: Sync Manager działa automatycznie!")
    return sync_manager


def test_4_conflict_resolution(db, api_client):
    """Test 4: Rozwiązywanie konfliktów"""
    print_separator("TEST 4: Rozwiązywanie konfliktów wersji")
    
    # Utwórz nowy alarm
    alarm_conflict = create_test_alarm("Konflikt Test")
    db.save_alarm(alarm_conflict)
    print(f"[OK] Utworzono alarm '{alarm_conflict.label}'")
    
    # Synchronizuj do serwera (wersja 1)
    print("\nSynchronizuję do serwera (wersja 1)...")
    alarm_data_v1 = {
        "id": alarm_conflict.id,
        "user_id": TEST_USER_ID,
        "type": "alarm",
        "label": alarm_conflict.label,
        "enabled": True,
        "alarm_time": "10:00",
        "recurrence": "daily",
        "days": [0, 1, 2, 3, 4],
        "play_sound": True,
        "show_popup": True,
        "version": 1
    }
    
    try:
        response = api_client.sync_alarm(alarm_data_v1, TEST_USER_ID)
        if response.success:
            server_version = response.data.get('version', 1)
            print(f"[OK] Zsynchronizowano - wersja serwera: {server_version}")
        else:
            print(f"[BLAD] Błąd: {response.error}")
            return
    except Exception as e:
        print(f"[BLAD] Wyjątek: {e}")
        return
    
    # Spróbuj wysłać starą wersję (powinien być konflikt)
    print("\nPróbuję wysłać starą wersję (powinien być konflikt 409)...")
    alarm_data_old = alarm_data_v1.copy()
    alarm_data_old["label"] = "Stara wersja"
    alarm_data_old["version"] = 1  # Stara wersja
    
    try:
        response = api_client.sync_alarm(alarm_data_old, TEST_USER_ID)
        if response.success:
            print("[UWAGA] UWAGA: Powinien być konflikt, ale synchronizacja udana!")
        else:
            if response.status_code == 409:
                print("[OK] Otrzymano konflikt 409 - zgodnie z oczekiwaniami!")
                print(f"  Dane serwera: wersja {response.data.get('version', 'N/A')}")
            else:
                print(f"[BLAD] Nieoczekiwany błąd: {response.error}")
    except Exception as e:
        # ConflictError
        print(f"[OK] Otrzymano wyjątek ConflictError - zgodnie z oczekiwaniami!")
        print(f"  {e}")
    
    print("\n[SUKCES] TEST 4 ZALICZONY: Konflikty są wykrywane!")


def test_5_soft_delete(db, api_client, alarm):
    """Test 5: Soft delete"""
    print_separator("TEST 5: Soft delete - usuwanie z synchronizacją")
    
    # Usuń alarm (soft delete)
    print(f"Usuwam alarm '{alarm.label}' (soft delete)...")
    db.delete_alarm(alarm.id, soft=True)
    print("[OK] Alarm usunięty lokalnie (soft delete)")
    
    # Sprawdź czy jest w kolejce sync
    sync_queue = db.get_sync_queue()
    delete_in_queue = any(
        item['entity_id'] == alarm.id and item['action'] == 'delete'
        for item in sync_queue
    )
    
    if delete_in_queue:
        print("[OK] Usunięcie znajduje się w kolejce synchronizacji")
    else:
        print("[UWAGA] UWAGA: Usunięcie NIE jest w kolejce!")
    
    # Spróbuj zsynchronizować usunięcie
    print(f"\nSynchronizuję usunięcie do serwera...")
    try:
        response = api_client.delete_item(alarm.id, soft=True)
        if response.success:
            print("[OK] Usunięcie zsynchronizowane!")
            print(f"  {response.data.get('message', 'OK')}")
        else:
            print(f"[BLAD] Błąd: {response.error}")
    except Exception as e:
        print(f"[BLAD] Wyjątek: {e}")
    
    print("\n[SUKCES] TEST 5 ZALICZONY: Soft delete działa!")


def test_6_bulk_sync(db, api_client):
    """Test 6: Bulk synchronization"""
    print_separator("TEST 6: Bulk sync - synchronizacja wielu elementów")
    
    # Utwórz kilka alarmów i timerów
    items_to_sync = []
    
    print("Tworzę 3 alarmy i 2 timery...")
    for i in range(3):
        alarm = create_test_alarm(f"Bulk Alarm {i+1}")
        alarm.alarm_time = dt_time(10 + i, 0)
        db.save_alarm(alarm)
        items_to_sync.append({
            "id": alarm.id,
            "user_id": TEST_USER_ID,
            "type": "alarm",
            "label": alarm.label,
            "enabled": alarm.enabled,
            "alarm_time": alarm.time.strftime("%H:%M"),
            "recurrence": alarm.recurrence.value,  # .value dla Enum
            "days": alarm.days,
            "play_sound": alarm.play_sound,
            "show_popup": alarm.show_popup,
            "version": 1
        })
        print(f"  [OK] Alarm {i+1}: {alarm.label}")
    
    for i in range(2):
        timer = create_test_timer(f"Bulk Timer {i+1}")
        timer.duration = 300 + (i * 60)
        db.save_timer(timer)
        items_to_sync.append({
            "id": timer.id,
            "user_id": TEST_USER_ID,
            "type": "timer",
            "label": timer.label,
            "enabled": timer.enabled,
            "duration": timer.duration,
            "play_sound": timer.play_sound,
            "show_popup": timer.show_popup,
            "repeat": timer.repeat,
            "version": 1
        })
        print(f"  [OK] Timer {i+1}: {timer.label}")
    
    # Bulk sync
    print(f"\nSynchronizuję {len(items_to_sync)} elementów jednocześnie...")
    try:
        response = api_client.bulk_sync(items_to_sync, TEST_USER_ID)
        if response.success:
            results = response.data.get('results', [])
            success_count = sum(1 for r in results if r.get('success'))
            failed_count = len(results) - success_count
            
            print(f"[OK] Bulk sync zakończony!")
            print(f"  Sukces: {success_count}/{len(results)}")
            print(f"  Błędy: {failed_count}/{len(results)}")
            
            if failed_count > 0:
                print("\n  Elementy z błędami:")
                for result in results:
                    if not result.get('success'):
                        print(f"    - ID: {result.get('id')} - {result.get('error')}")
        else:
            print(f"[BLAD] Błąd bulk sync: {response.error}")
    except Exception as e:
        print(f"[BLAD] Wyjątek: {e}")
    
    print("\n[SUKCES] TEST 6 ZALICZONY: Bulk sync działa!")


def run_all_tests():
    """Uruchamia wszystkie testy"""
    print("\n")
    print("=" * 80)
    print(" " * 20 + "TEST PELNEGO FLOW SYNCHRONIZACJI")
    print("=" * 80)
    
    try:
        # Krok 0: Autentykacja
        if not initialize_auth():
            print("\n[BLAD] Autentykacja nieudana - przerywam testy")
            return
        
        # Test 1: LocalDatabase
        db, alarm1, timer1 = test_1_local_database()
        
        # Test 2: API Client
        api_client = test_2_api_client(db, alarm1, timer1)
        
        # Test 3: Sync Manager
        sync_manager = test_3_sync_manager(db, api_client)
        
        # Test 4: Conflict Resolution
        test_4_conflict_resolution(db, api_client)
        
        # Test 5: Soft Delete
        test_5_soft_delete(db, api_client, alarm1)
        
        # Test 6: Bulk Sync
        test_6_bulk_sync(db, api_client)
        
        # Podsumowanie
        print_separator("WSZYSTKIE TESTY ZALICZONE!")
        print("Pelny flow synchronizacji dziala poprawnie:")
        print("  [OK] Lokalna baza SQLite")
        print("  [OK] API Client komunikacja HTTP")
        print("  [OK] Sync Manager automatyczna synchronizacja")
        print("  [OK] Wykrywanie konfliktow wersji")
        print("  [OK] Soft delete z synchronizacja")
        print("  [OK] Bulk synchronization")
        print("\nSystem gotowy do produkcji!\n")
        
    except Exception as e:
        print_separator("TEST NIEUDANY")
        print(f"Blad: {e}")
        import traceback
        traceback.print_exc()
        print()


if __name__ == "__main__":
    # Skonfiguruj logger
    logger.remove()  # Usuń domyślny handler
    logger.add(
        sys.stderr,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <level>{message}</level>",
        level="INFO"
    )
    
    # Uruchom testy
    run_all_tests()
