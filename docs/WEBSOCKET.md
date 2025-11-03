# WebSocket Real-time Synchronization

## Przegląd

System WebSocket umożliwia real-time synchronizację alarmów i timerów między serwerem a klientami. Klienci automatycznie otrzymują powiadomienia o zmianach bez konieczności ciągłego odpytywania serwera (polling).

## Architektura

```
Desktop App (PyQt6)
    |
    v
WebSocketClient (QThread)
    |
    v (WSS://server/api/alarms-timers/ws)
    |
    v
FastAPI WebSocket Endpoint
    |
    v
ConnectionManager
    |
    v
Broadcast to all user's connections
```

## Endpointy

### WebSocket Connection

**URL:** `ws://localhost:8000/api/alarms-timers/ws?token=JWT_TOKEN`  
**Protocol:** WebSocket  
**Auth:** JWT token w query parameter

#### Połączenie

```python
import websockets
import json

async with websockets.connect(
    "ws://localhost:8000/api/alarms-timers/ws?token=YOUR_JWT_TOKEN"
) as ws:
    # Odbieraj wiadomości
    async for message in ws:
        data = json.loads(message)
        print(data)
```

#### Autoryzacja

Token JWT musi być przekazany jako query parameter `token`. Server zwaliduje token i wyciągnie `user_id`.

**Przykład:**
```
ws://localhost:8000/api/alarms-timers/ws?token=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

## Message Types

### Server → Client

#### 1. Connected
Potwierdzenie połączenia.

```json
{
    "type": "connected",
    "timestamp": "2024-01-15T10:30:00",
    "user_id": "user123",
    "message": "WebSocket connection established"
}
```

#### 2. Alarm Created
Nowy alarm został utworzony.

```json
{
    "type": "alarm_created",
    "timestamp": "2024-01-15T10:30:00",
    "user_id": "user123",
    "data": {
        "id": "alarm_001",
        "type": "alarm",
        "label": "Pobudka",
        "enabled": true,
        "alarm_time": "07:30",
        "recurrence": "weekdays",
        "days": [1, 2, 3, 4, 5],
        "version": 1,
        "created_at": "2024-01-15T10:30:00",
        "updated_at": "2024-01-15T10:30:00"
    }
}
```

#### 3. Alarm Updated
Alarm został zaktualizowany.

```json
{
    "type": "alarm_updated",
    "timestamp": "2024-01-15T10:35:00",
    "user_id": "user123",
    "data": {
        "id": "alarm_001",
        "label": "Pobudka (updated)",
        "enabled": false,
        "version": 2,
        "updated_at": "2024-01-15T10:35:00"
    }
}
```

#### 4. Alarm Deleted
Alarm został usunięty.

```json
{
    "type": "alarm_deleted",
    "timestamp": "2024-01-15T10:40:00",
    "user_id": "user123",
    "data": {
        "id": "alarm_001",
        "deleted_at": "2024-01-15T10:40:00"
    }
}
```

#### 5. Timer Events
Analogicznie dla timerów: `timer_created`, `timer_updated`, `timer_deleted`.

#### 6. Sync Required
Server wymaga synchronizacji danych.

```json
{
    "type": "sync_required",
    "timestamp": "2024-01-15T10:45:00",
    "user_id": "user123",
    "reason": "Server changes detected"
}
```

#### 7. Heartbeat
Heartbeat dla utrzymania połączenia (co 30s).

```json
{
    "type": "heartbeat",
    "timestamp": "2024-01-15T10:50:00"
}
```

#### 8. Error
Błąd przetwarzania.

```json
{
    "type": "error",
    "timestamp": "2024-01-15T10:55:00",
    "error": "Invalid message format",
    "details": {}
}
```

### Client → Server

#### 1. Ping
Ping do sprawdzenia połączenia.

```json
{
    "type": "ping"
}
```

**Response:**
```json
{
    "type": "pong",
    "timestamp": "2024-01-15T11:00:00"
}
```

#### 2. Subscribe
Subskrypcja eventów (automatyczne przy connect).

```json
{
    "type": "subscribe"
}
```

#### 3. Unsubscribe
Rezygnacja z subskrypcji (disconnect).

```json
{
    "type": "unsubscribe"
}
```

## Python Client (PyQt6)

### Podstawowe użycie

```python
from src.Modules.Alarm_module.alarm_websocket_client import create_websocket_client

# Callbacks
def on_alarm_updated(alarm_data: dict):
    print(f"Alarm updated: {alarm_data['label']}")
    # Odśwież UI

def on_sync_required(reason: str):
    print(f"Sync needed: {reason}")
    # Wywołaj sync_manager.sync_now()

# Utwórz klienta
ws_client = create_websocket_client(
    base_url="http://localhost:8000",
    auth_token="your_jwt_token",
    on_alarm_updated=on_alarm_updated,
    on_sync_required=on_sync_required,
    auto_reconnect=True
)

# Uruchom
ws_client.start()

# Później: zatrzymaj
ws_client.stop()
```

### Integracja z SyncManager

```python
from src.Modules.Alarm_module.alarms_sync_manager import SyncManager

# Setup SyncManager
sync_manager = SyncManager(
    local_db=local_db,
    api_client=api_client,
    user_id=user_id
)
sync_manager.start()

# WebSocket callback - trigger sync
def trigger_sync(reason: str):
    sync_manager.sync_now()

# WebSocket client
ws_client = create_websocket_client(
    base_url=BASE_URL,
    auth_token=token,
    on_sync_required=trigger_sync
)
ws_client.start()
```

### Dostępne Sygnały

WebSocketClient emituje następujące sygnały PyQt6:

- `connected` - Połączono z serwerem
- `disconnected` - Rozłączono
- `error(str)` - Błąd
- `alarm_created(dict)` - Nowy alarm
- `alarm_updated(dict)` - Zaktualizowany alarm
- `alarm_deleted(dict)` - Usunięty alarm
- `timer_created(dict)` - Nowy timer
- `timer_updated(dict)` - Zaktualizowany timer
- `timer_deleted(dict)` - Usunięty timer
- `sync_required(str)` - Wymagana synchronizacja
- `heartbeat()` - Heartbeat

### Przykład z sygnałami

```python
ws_client = create_websocket_client(...)

# Podłącz sygnały
ws_client.connected.connect(lambda: print("Connected!"))
ws_client.disconnected.connect(lambda: print("Disconnected!"))
ws_client.error.connect(lambda msg: print(f"Error: {msg}"))

ws_client.alarm_updated.connect(refresh_alarm_in_ui)
ws_client.timer_updated.connect(refresh_timer_in_ui)

ws_client.start()
```

## JavaScript Client

### Vanilla JavaScript

```javascript
const token = "your_jwt_token";
const ws = new WebSocket(`ws://localhost:8000/api/alarms-timers/ws?token=${token}`);

ws.onopen = () => {
    console.log("WebSocket connected");
};

ws.onmessage = (event) => {
    const message = JSON.parse(event.data);
    
    switch(message.type) {
        case 'alarm_created':
            console.log("New alarm:", message.data);
            refreshAlarmList();
            break;
        
        case 'alarm_updated':
            console.log("Alarm updated:", message.data);
            updateAlarmInUI(message.data);
            break;
        
        case 'sync_required':
            console.log("Sync required:", message.reason);
            fetchAllAlarms();
            break;
        
        case 'heartbeat':
            // Server is alive
            break;
    }
};

ws.onerror = (error) => {
    console.error("WebSocket error:", error);
};

ws.onclose = () => {
    console.log("WebSocket closed");
    // Auto-reconnect
    setTimeout(() => connectWebSocket(), 5000);
};
```

### React Hook

```javascript
import { useEffect, useState } from 'react';

function useWebSocket(baseUrl, token) {
    const [connected, setConnected] = useState(false);
    const [ws, setWs] = useState(null);
    
    useEffect(() => {
        const wsUrl = baseUrl.replace('http', 'ws');
        const socket = new WebSocket(`${wsUrl}/api/alarms-timers/ws?token=${token}`);
        
        socket.onopen = () => {
            console.log('Connected');
            setConnected(true);
        };
        
        socket.onclose = () => {
            console.log('Disconnected');
            setConnected(false);
        };
        
        socket.onmessage = (event) => {
            const message = JSON.parse(event.data);
            handleMessage(message);
        };
        
        setWs(socket);
        
        return () => {
            socket.close();
        };
    }, [baseUrl, token]);
    
    return { ws, connected };
}

// Usage
function App() {
    const { ws, connected } = useWebSocket('http://localhost:8000', authToken);
    
    return (
        <div>
            Status: {connected ? 'Connected' : 'Disconnected'}
        </div>
    );
}
```

## Server-side Broadcasting

### Automatyczne powiadomienia

Server automatycznie broadcastuje eventy po każdej zmianie:

```python
# W alarms_router.py

# Po utworzeniu alarmu
response_data = db_model_to_response(new_item)
event_type = WSEventType.ALARM_CREATED
asyncio.create_task(
    notify_item_change(event_type, response_data.dict(), user_id)
)
```

### Manualne triggering

```python
from app.websocket_manager import notify_sync_required

# Wymuś synchronizację dla użytkownika
await notify_sync_required(user_id, reason="Manual trigger")
```

### Statystyki połączeń

```bash
GET /api/alarms-timers/ws/stats
Authorization: Bearer JWT_TOKEN
```

**Response:**
```json
{
    "total_users": 5,
    "total_connections": 8,
    "users": {
        "user123": 2,
        "user456": 1,
        "user789": 3
    }
}
```

## Konfiguracja

### Server

```python
# requirements.txt
websockets==12.0

# main.py
from app.alarms_router import router
app.include_router(router)
```

### Client

```python
# requirements.txt (dla PyQt6 app)
PyQt6==6.6.1
websockets==12.0
```

## Best Practices

### 1. Auto-reconnect

Zawsze używaj auto-reconnect:

```python
ws_client = WebSocketClient(
    base_url=BASE_URL,
    auth_token=token,
    auto_reconnect=True,
    reconnect_delay=5  # 5 sekund
)
```

### 2. Heartbeat Monitoring

Monitor heartbeat do wykrywania połączenia:

```python
last_heartbeat = time.time()

def on_heartbeat():
    global last_heartbeat
    last_heartbeat = time.time()

ws_client.heartbeat.connect(on_heartbeat)

# Check co 60s
def check_connection():
    if time.time() - last_heartbeat > 60:
        print("Connection might be dead!")
```

### 3. Graceful Shutdown

Zawsze zatrzymuj WebSocket podczas zamykania:

```python
# PyQt6 app
class MainWindow(QMainWindow):
    def closeEvent(self, event):
        self.ws_client.stop()
        self.sync_manager.stop()
        event.accept()
```

### 4. Error Handling

Obsługuj błędy połączenia:

```python
def on_error(error_msg: str):
    logger.error(f"WebSocket error: {error_msg}")
    
    # Fallback do polling
    if not ws_client.is_connected():
        sync_manager.set_interval(10)  # Częstszy sync
```

### 5. Deduplication

Unikaj duplikatów przy otrzymywaniu eventów:

```python
processed_events = set()

def on_alarm_updated(data):
    event_id = f"{data['id']}_{data['version']}"
    
    if event_id in processed_events:
        return  # Już przetworzony
    
    processed_events.add(event_id)
    refresh_ui(data)
```

## Troubleshooting

### Problem: Nie można połączyć

**Rozwiązanie:**
1. Sprawdź czy token JWT jest poprawny
2. Sprawdź czy serwer obsługuje WebSocket
3. Sprawdź firewall/proxy

### Problem: Częste rozłączenia

**Rozwiązanie:**
1. Zwiększ `ping_interval`
2. Sprawdź stabilność sieci
3. Sprawdź logi serwera

### Problem: Nie otrzymuję eventów

**Rozwiązanie:**
1. Sprawdź czy `user_id` się zgadza
2. Sprawdź czy callback jest podpięty
3. Sprawdź logi serwera - czy broadcast działa

## Przykłady

Zobacz:
- `examples/websocket_example.py` - Przykłady Python
- `src/Modules/Alarm_module/alarm_websocket_client.py` - Implementacja klienta
- `Render_upload/app/websocket_manager.py` - Implementacja serwera
- `Render_upload/app/alarms_router.py` - WebSocket endpoint

## Security

### 1. Token Validation

Token jest walidowany przy każdym połączeniu:

```python
payload = decode_token(token)
user_id = payload.get("user_id")

if not user_id:
    await websocket.close(code=1008, reason="Invalid token")
```

### 2. User Isolation

Każdy user otrzymuje tylko swoje eventy:

```python
await manager.broadcast_to_user(event, user_id)  # Tylko dla tego user
```

### 3. WSS (Production)

W produkcji używaj WSS (WebSocket Secure):

```
wss://api.example.com/api/alarms-timers/ws?token=...
```

## Performance

### Connection Limits

Server może obsłużyć wiele połączeń na użytkownika:

- 1 user × 3 devices = 3 connections
- Wszystkie otrzymują te same eventy
- Broadcast jest efektywny dzięki asyncio

### Bandwidth

Minimalne zużycie:
- Heartbeat (30s): ~50 bytes
- Event: ~200-500 bytes
- Całkowite: < 1 KB/min przy braku zmian

## Monitoring

### Logi Server

```python
# websocket_manager.py
logger.info(f"WebSocket connected: user={user_id}")
logger.info(f"Notified user {user_id} about {event_type}")
```

### Metryki Client

```python
stats = {
    "connections": ws_client.connected_count,
    "events_received": ws_client.events_count,
    "errors": ws_client.error_count
}
```
