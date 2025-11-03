"""Test ręcznej synchronizacji Pomodoro"""
import sys
from pathlib import Path

# Dodaj ścieżkę do modułów
sys.path.insert(0, str(Path.cwd() / 'src'))

from Modules.Pomodoro_module.pomodoro_local_database import PomodoroLocalDatabase
from Modules.Pomodoro_module.pomodoro_api_client import PomodoroAPIClient
from Modules.Pomodoro_module.pomodoro_sync_manager import PomodoroSyncManager
import json

# Wczytaj tokeny
tokens_path = Path.cwd() / 'data' / 'tokens.json'
with open(tokens_path) as f:
    tokens = json.load(f)

# Dekoduj user_id z tokena (base64 decode środkowej części)
import base64
token_parts = tokens['access_token'].split('.')
payload = token_parts[1]
# Dodaj padding jeśli potrzebny
payload += '=' * (4 - len(payload) % 4)
decoded_bytes = base64.urlsafe_b64decode(payload)
decoded = json.loads(decoded_bytes)
user_id = decoded['sub']

print("=" * 80)
print("TEST SYNCHRONIZACJI POMODORO")
print("=" * 80)
print(f"User ID: {user_id}")

# Inicjalizuj lokalną bazę
db_path = Path.home() / ".pro_ka_po" / "pomodoro.db"
print(f"\n1. Inicjalizacja lokalnej bazy: {db_path}")
local_db = PomodoroLocalDatabase(
    db_path=str(db_path),
    user_id=user_id
)

# Sprawdź ile jest niezsynchronizowanych sesji
unsynced = local_db.get_unsynced_items('session_logs')
print(f"   Niezsynchronizowane sesje: {len(unsynced)}")
for session in unsynced[:3]:
    print(f"     - {session['id'][:8]}... | {session.get('session_date')} | {session.get('status')}")

# Inicjalizuj API client
print(f"\n2. Inicjalizacja API client")
api_client = PomodoroAPIClient(
    base_url="https://pro-ka-po-backend.onrender.com",
    auth_token=tokens['access_token'],
    refresh_token=tokens['refresh_token']
)
print(f"   Base URL: {api_client.base_url}")

# Test czy API działa
print(f"\n3. Test połączenia z API...")
try:
    response = api_client.fetch_all(type='session')
    if response.success:
        print(f"   ✓ API działa! Otrzymano {len(response.data)} sesji z serwera")
    else:
        print(f"   ✗ API błąd: {response.error}")
        print(f"   Status code: {response.status_code}")
except Exception as e:
    print(f"   ✗ Wyjątek: {e}")

# Inicjalizuj sync manager
print(f"\n4. Inicjalizacja Sync Manager")
sync_manager = PomodoroSyncManager(
    local_db=local_db,
    api_client=api_client,
    auto_sync_interval=999999  # Wyłącz auto-sync
)
print(f"   Sync Manager gotowy")

# Uruchom ręczną synchronizację
print(f"\n5. Uruchamianie ręcznej synchronizacji...")
print("=" * 80)
try:
    result = sync_manager.sync_now()
    print("=" * 80)
    if result:
        print(f"✓ Synchronizacja zakończona pomyślnie!")
    else:
        print(f"✗ Synchronizacja nie powiodła się")
except Exception as e:
    print("=" * 80)
    print(f"✗ Błąd podczas synchronizacji: {e}")
    import traceback
    traceback.print_exc()

# Sprawdź ponownie ile jest niezsynchronizowanych
print(f"\n6. Sprawdzanie stanu po synchronizacji...")
unsynced_after = local_db.get_unsynced_items('session_logs')
print(f"   Niezsynchronizowane sesje: {len(unsynced_after)}")
print(f"   Zsynchronizowano: {len(unsynced) - len(unsynced_after)}")

print("\n" + "=" * 80)
print("TEST ZAKOŃCZONY")
print("=" * 80)
