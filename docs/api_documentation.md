# API Documentation - Moduł Synchronizacji Alarmów

## Przegląd

API dla synchronizacji alarmów i timerów w architekturze local-first.

**Base URL (Production):** `https://api.pro-ka-po.com`  
**Base URL (Development):** `http://localhost:8000`

**Autentykacja:** Bearer Token w headerze `Authorization`

---

## Endpoints

### 1. Health Check

Sprawdź dostępność API.

```http
GET /health
```

**Response 200:**
```json
{
  "status": "ok",
  "version": "1.0.0",
  "timestamp": "2024-01-10T12:00:00Z"
}
```

---

### 2. List Items

Pobierz wszystkie alarmy/timery użytkownika.

```http
GET /api/alarms-timers
```

**Query Parameters:**
- `user_id` (required): ID użytkownika
- `type` (optional): Filtr typu (`alarm` | `timer`)
- `enabled` (optional): Filtr aktywnych (`true` | `false`)

**Request Example:**
```http
GET /api/alarms-timers?user_id=user123&type=alarm&enabled=true
Authorization: Bearer eyJhbGc...
```

**Response 200:**
```json
{
  "items": [
    {
      "id": "alarm_001",
      "user_id": "user123",
      "type": "alarm",
      "label": "Pobudka",
      "enabled": true,
      "alarm_time": "07:30",
      "recurrence": "weekdays",
      "days": [1, 2, 3, 4, 5],
      "play_sound": true,
      "show_popup": true,
      "custom_sound": null,
      "created_at": "2024-01-01T00:00:00Z",
      "updated_at": "2024-01-10T12:00:00Z",
      "synced_at": "2024-01-10T12:00:00Z",
      "version": 3
    }
  ],
  "count": 1
}
```

**Response 401 Unauthorized:**
```json
{
  "detail": "Invalid authentication token"
}
```

---

### 3. Get Single Item

Pobierz konkretny alarm/timer.

```http
GET /api/alarms-timers/{item_id}
```

**Path Parameters:**
- `item_id` (required): ID alarmu/timera

**Request Example:**
```http
GET /api/alarms-timers/alarm_001
Authorization: Bearer eyJhbGc...
```

**Response 200:**
```json
{
  "id": "alarm_001",
  "user_id": "user123",
  "type": "alarm",
  "label": "Pobudka",
  "enabled": true,
  "alarm_time": "07:30",
  "recurrence": "weekdays",
  "days": [1, 2, 3, 4, 5],
  "play_sound": true,
  "show_popup": true,
  "custom_sound": null,
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-10T12:00:00Z",
  "version": 3
}
```

**Response 404 Not Found:**
```json
{
  "detail": "Item not found"
}
```

---

### 4. Upsert (Create/Update) Item

Utwórz nowy lub zaktualizuj istniejący alarm/timer.

```http
POST /api/alarms-timers
```

**Request Body (Alarm):**
```json
{
  "id": "alarm_001",
  "user_id": "user123",
  "type": "alarm",
  "label": "Pobudka",
  "enabled": true,
  "alarm_time": "07:30",
  "recurrence": "weekdays",
  "days": [1, 2, 3, 4, 5],
  "play_sound": true,
  "show_popup": true,
  "custom_sound": "/path/to/sound.mp3",
  "version": 2
}
```

**Request Body (Timer):**
```json
{
  "id": "timer_001",
  "user_id": "user123",
  "type": "timer",
  "label": "Herbata",
  "enabled": true,
  "duration": 300,
  "remaining": 300,
  "repeat": false,
  "started_at": null,
  "play_sound": true,
  "show_popup": true,
  "custom_sound": null,
  "version": 1
}
```

**Response 200 (Created/Updated):**
```json
{
  "id": "alarm_001",
  "user_id": "user123",
  "type": "alarm",
  "label": "Pobudka",
  "enabled": true,
  "alarm_time": "07:30",
  "recurrence": "weekdays",
  "days": [1, 2, 3, 4, 5],
  "play_sound": true,
  "show_popup": true,
  "custom_sound": "/path/to/sound.mp3",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-10T12:05:00Z",
  "synced_at": "2024-01-10T12:05:00Z",
  "version": 3
}
```

**Response 409 Conflict (Version Mismatch):**
```json
{
  "detail": "Version conflict detected",
  "local_version": 2,
  "server_version": 4,
  "server_data": {
    "id": "alarm_001",
    "user_id": "user123",
    "type": "alarm",
    "label": "Pobudka (zaktualizowana)",
    "version": 4,
    "updated_at": "2024-01-10T11:00:00Z"
  }
}
```

**Response 400 Bad Request:**
```json
{
  "detail": "Validation error",
  "errors": [
    {
      "field": "alarm_time",
      "message": "Invalid time format. Use HH:MM"
    }
  ]
}
```

---

### 5. Delete Item

Usuń alarm/timer (soft lub hard delete).

```http
DELETE /api/alarms-timers/{item_id}
```

**Path Parameters:**
- `item_id` (required): ID alarmu/timera

**Query Parameters:**
- `soft` (optional): Soft delete (domyślnie `true`)

**Request Example:**
```http
DELETE /api/alarms-timers/alarm_001?soft=true
Authorization: Bearer eyJhbGc...
```

**Response 200:**
```json
{
  "message": "Item soft deleted successfully",
  "id": "alarm_001",
  "deleted_at": "2024-01-10T12:10:00Z"
}
```

**Response 404 Not Found:**
```json
{
  "detail": "Item not found"
}
```

---

### 6. Bulk Sync

Synchronizuj wiele elementów w jednym request.

```http
POST /api/alarms-timers/bulk
```

**Request Body:**
```json
{
  "user_id": "user123",
  "items": [
    {
      "id": "alarm_001",
      "type": "alarm",
      "label": "Pobudka",
      "alarm_time": "07:30",
      "recurrence": "daily",
      "days": [0, 1, 2, 3, 4, 5, 6],
      "enabled": true,
      "play_sound": true,
      "show_popup": true,
      "version": 1
    },
    {
      "id": "timer_001",
      "type": "timer",
      "label": "Herbata",
      "duration": 300,
      "remaining": 300,
      "repeat": false,
      "enabled": true,
      "play_sound": true,
      "show_popup": true,
      "version": 1
    }
  ]
}
```

**Response 200:**
```json
{
  "results": [
    {
      "id": "alarm_001",
      "status": "success",
      "version": 2
    },
    {
      "id": "timer_001",
      "status": "success",
      "version": 2
    }
  ],
  "success_count": 2,
  "error_count": 0
}
```

**Response 207 Multi-Status (Częściowy sukces):**
```json
{
  "results": [
    {
      "id": "alarm_001",
      "status": "success",
      "version": 2
    },
    {
      "id": "timer_001",
      "status": "conflict",
      "error": "Version mismatch",
      "server_version": 3
    }
  ],
  "success_count": 1,
  "error_count": 1
}
```

---

## Data Models

### Alarm Model

```typescript
{
  id: string;                    // UUID
  user_id: string;               // User ID
  type: "alarm";                 // Literal type
  label: string;                 // Display name
  enabled: boolean;              // Active/Inactive
  alarm_time: string;            // Format: "HH:MM"
  recurrence: string;            // "once" | "daily" | "weekly" | "weekdays" | "weekends"
  days: number[];                // 0-6 (Sunday-Saturday), empty for "once"
  play_sound: boolean;
  show_popup: boolean;
  custom_sound: string | null;   // File path or null
  created_at: string;            // ISO 8601
  updated_at: string;            // ISO 8601
  synced_at?: string;            // ISO 8601 (optional)
  version: number;               // For conflict resolution
}
```

### Timer Model

```typescript
{
  id: string;                    // UUID
  user_id: string;               // User ID
  type: "timer";                 // Literal type
  label: string;                 // Display name
  enabled: boolean;              // Active/Inactive
  duration: number;              // Total seconds
  remaining: number;             // Remaining seconds
  repeat: boolean;               // Auto-restart
  started_at: string | null;     // ISO 8601 or null
  play_sound: boolean;
  show_popup: boolean;
  custom_sound: string | null;   // File path or null
  created_at: string;            // ISO 8601
  updated_at: string;            // ISO 8601
  synced_at?: string;            // ISO 8601 (optional)
  version: number;               // For conflict resolution
}
```

---

## Error Codes

| Code | Meaning | Description |
|------|---------|-------------|
| 200 | OK | Request successful |
| 400 | Bad Request | Validation error |
| 401 | Unauthorized | Invalid or missing auth token |
| 403 | Forbidden | Access denied |
| 404 | Not Found | Resource not found |
| 409 | Conflict | Version conflict detected |
| 422 | Unprocessable Entity | Invalid data format |
| 500 | Internal Server Error | Server error |
| 503 | Service Unavailable | Temporary outage |

---

## Conflict Resolution

### Version Conflict (409)

Gdy lokalny `version` nie zgadza się z serwerowym, serwer zwraca 409 wraz z aktualnymi danymi.

**Strategia Last-Write-Wins:**

1. Porównaj `updated_at` timestamps
2. Nowszy timestamp wygrywa
3. Jeśli serwer wygrywa → nadpisz lokalną kopię
4. Jeśli local wygrywa → wyślij ponownie z `version + 1`

**Przykład w Python:**

```python
try:
    response = api_client.sync_alarm(alarm_data, user_id)
except ConflictError as e:
    # Rozwiąż konflikt
    winning_data, winner = api_client.resolve_conflict(
        local_data=alarm_data,
        server_data=e.server_data,
        strategy='last_write_wins'
    )
    
    if winner == 'server':
        # Nadpisz lokalną kopię
        local_db.save_alarm(Alarm.from_dict(winning_data), user_id)
    else:
        # Wyślij ponownie
        response = api_client.sync_alarm(winning_data, user_id)
```

---

## Rate Limiting

- **Limit:** 100 requests per minute per user
- **Header:** `X-RateLimit-Remaining: 95`
- **Reset:** `X-RateLimit-Reset: 1641825600`

**Response 429 (Too Many Requests):**
```json
{
  "detail": "Rate limit exceeded. Try again in 30 seconds.",
  "retry_after": 30
}
```

---

## Authentication

### Bearer Token

```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

### Token Structure (JWT)

```json
{
  "sub": "user123",
  "email": "user@example.com",
  "exp": 1641825600,
  "iat": 1641739200
}
```

### Refresh Token

```http
POST /auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI...",
  "expires_in": 3600
}
```

---

## WebSocket Support (Future)

Planowana implementacja WebSocket dla real-time synchronizacji.

```javascript
// Connect
const ws = new WebSocket('wss://api.pro-ka-po.com/ws/alarms');

// Subscribe to user's alarms
ws.send(JSON.stringify({
  action: 'subscribe',
  user_id: 'user123'
}));

// Receive updates
ws.onmessage = (event) => {
  const update = JSON.parse(event.data);
  console.log('Alarm updated:', update);
};
```

---

## SDK Examples

### Python (Official)

```python
from src.Modules.Alarm_module.alarm_api_client import create_api_client

# Initialize
client = create_api_client(
    base_url="https://api.pro-ka-po.com",
    auth_token="your_token_here"
)

# Create alarm
alarm_data = {
    "id": "alarm_001",
    "type": "alarm",
    "label": "Pobudka",
    "alarm_time": "07:30",
    "recurrence": "weekdays",
    "days": [1, 2, 3, 4, 5],
    "enabled": True,
    "play_sound": True,
    "show_popup": True,
    "version": 1
}

response = client.sync_alarm(alarm_data, user_id="user123")

if response.success:
    print("Alarm synced:", response.data)
else:
    print("Error:", response.error)
```

### JavaScript (Community)

```javascript
// TODO: Community SDK
```

---

## Testing

### cURL Examples

**Create Alarm:**
```bash
curl -X POST https://api.pro-ka-po.com/api/alarms-timers \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "id": "alarm_001",
    "user_id": "user123",
    "type": "alarm",
    "label": "Pobudka",
    "alarm_time": "07:30",
    "recurrence": "daily",
    "days": [0,1,2,3,4,5,6],
    "enabled": true,
    "play_sound": true,
    "show_popup": true,
    "version": 1
  }'
```

**List Alarms:**
```bash
curl -X GET "https://api.pro-ka-po.com/api/alarms-timers?user_id=user123&type=alarm" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Delete Alarm:**
```bash
curl -X DELETE "https://api.pro-ka-po.com/api/alarms-timers/alarm_001?soft=true" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

---

## Changelog

### v1.0.0 (2024-01-10)
- ✅ Initial API release
- ✅ Unified table approach (alarms + timers)
- ✅ Version-based conflict resolution
- ✅ Soft delete support
- ✅ Bulk sync endpoint

### v1.1.0 (Planned)
- ⏳ WebSocket real-time sync
- ⏳ Pagination for large lists
- ⏳ Advanced filtering
- ⏳ GraphQL endpoint

---

## Support

**Documentation:** https://docs.pro-ka-po.com  
**GitHub:** https://github.com/Piotr19881/Pro-Ka-Po_V5c  
**Issues:** https://github.com/Piotr19881/Pro-Ka-Po_V5c/issues  
**Email:** support@pro-ka-po.com

---

**Last Updated:** 2024-01-10  
**API Version:** 1.0.0  
**License:** Proprietary
