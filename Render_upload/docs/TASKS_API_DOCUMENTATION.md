# Tasks & Kanban API Documentation

## Overview
REST API dla synchronizacji zadań (Tasks) i widoku Kanban w architekturze local-first.

**Base URL:** `/api/tasks`

**Authentication:** Bearer JWT token w header `Authorization: Bearer <token>`

---

## Endpoints

### Health Check

#### `GET /health`
Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "service": "tasks-sync",
  "timestamp": "2024-11-06T10:30:00.000Z"
}
```

---

## Tasks Endpoints

### Create/Update Task

#### `POST /task`
Upsert (create or update) task with version-based conflict detection.

**Request Body:**
```json
{
  "id": "uuid-string",
  "user_id": "user-uuid",
  "title": "Task title",
  "description": "Optional description",
  "status": false,
  "parent_id": null,
  "due_date": "2024-12-01T00:00:00Z",
  "completion_date": null,
  "alarm_date": null,
  "note_id": null,
  "custom_data": {},
  "archived": false,
  "order": 0,
  "version": 1
}
```

**Response (200 OK):**
```json
{
  "id": "uuid-string",
  "user_id": "user-uuid",
  "title": "Task title",
  "version": 2,
  "created_at": "2024-11-06T10:00:00Z",
  "updated_at": "2024-11-06T10:30:00Z",
  "deleted_at": null,
  "synced_at": "2024-11-06T10:30:00Z",
  ...
}
```

**Response (409 CONFLICT):**
```json
{
  "detail": {
    "message": "Version conflict detected",
    "local_version": 1,
    "server_version": 3,
    "server_data": { ... }
  }
}
```

---

### List Tasks

#### `GET /tasks`
List user's tasks with optional filtering.

**Query Parameters:**
- `user_id` (required): User ID
- `include_deleted` (optional, default=false): Include soft-deleted tasks
- `include_archived` (optional, default=true): Include archived tasks
- `parent_id` (optional): Filter by parent task ID
- `since` (optional): Get only tasks modified after this timestamp (ISO 8601)

**Response:**
```json
{
  "items": [
    {
      "id": "uuid",
      "title": "Task 1",
      ...
    }
  ],
  "count": 10,
  "last_sync": "2024-11-06T10:30:00Z"
}
```

---

### Get Single Task

#### `GET /task/{task_id}`
Get single task by ID.

**Response (200 OK):**
```json
{
  "id": "task-uuid",
  "title": "Task title",
  ...
}
```

**Response (404 NOT FOUND):**
```json
{
  "detail": "Task task-uuid not found"
}
```

---

### Delete Task

#### `DELETE /task/{task_id}`
Delete task (soft delete by default).

**Query Parameters:**
- `soft` (optional, default=true): Use soft delete (set `deleted_at`) or hard delete (physical removal)

**Response:**
```json
{
  "message": "Task soft deleted",
  "id": "task-uuid",
  "deleted_at": "2024-11-06T10:30:00Z"
}
```

---

## Tags Endpoints

### Create/Update Tag

#### `POST /tag`
Upsert tag with conflict detection.

**Request:**
```json
{
  "id": "tag-uuid",
  "user_id": "user-uuid",
  "name": "Important",
  "color": "#FF5733",
  "version": 1
}
```

**Response:** Same structure as request with timestamps.

---

### List Tags

#### `GET /tags`
List user's tags.

**Query Parameters:**
- `user_id` (required)
- `include_deleted` (optional, default=false)

**Response:**
```json
{
  "items": [...],
  "count": 5
}
```

---

### Delete Tag

#### `DELETE /tag/{tag_id}`
Delete tag (soft delete by default).

---

## Kanban Endpoints

### Create/Update Kanban Item

#### `POST /kanban/item`
Upsert Kanban item (task position in column).

**Request:**
```json
{
  "id": "item-uuid",
  "user_id": "user-uuid",
  "task_id": "task-uuid",
  "column_type": "todo",
  "position": 0,
  "version": 1
}
```

---

### List Kanban Items

#### `GET /kanban/items`
List Kanban items.

**Query Parameters:**
- `user_id` (required)
- `column_type` (optional): Filter by column (e.g., "todo", "in_progress", "done")
- `include_deleted` (optional, default=false)

---

### Get/Update Kanban Settings

#### `GET /kanban/settings`
Get user's Kanban settings (JSON object).

**Query Parameters:**
- `user_id` (required)

**Response:**
```json
{
  "id": "settings-uuid",
  "user_id": "user-uuid",
  "settings": {
    "columns": ["todo", "in_progress", "done"],
    "auto_archive": true,
    ...
  },
  "version": 1,
  "created_at": "...",
  "updated_at": "..."
}
```

#### `POST /kanban/settings`
Update Kanban settings.

**Request:** Same structure as GET response.

---

## Columns Configuration

### Get/Update Columns Config

#### `GET /columns-config`
Get user's columns configuration (visible columns, order, sort).

**Response:**
```json
{
  "id": "config-uuid",
  "user_id": "user-uuid",
  "visible_columns": ["title", "status", "due_date"],
  "column_order": ["title", "status", "due_date", "tags"],
  "sort_column": "due_date",
  "sort_direction": "asc",
  "version": 1,
  ...
}
```

#### `POST /columns-config`
Update columns configuration.

---

## Custom Lists

### Create/Update Custom List

#### `POST /custom-list`
Upsert custom list (predefined values for custom fields).

**Request:**
```json
{
  "id": "list-uuid",
  "user_id": "user-uuid",
  "name": "Priority Levels",
  "values": ["Low", "Medium", "High", "Critical"],
  "version": 1
}
```

---

### List Custom Lists

#### `GET /custom-lists`
List user's custom lists.

**Query Parameters:**
- `user_id` (required)
- `include_deleted` (optional, default=false)

---

### Delete Custom List

#### `DELETE /custom-list/{list_id}`
Delete custom list.

---

## Bulk Synchronization

### Bulk Sync

#### `POST /bulk-sync`
Synchronize multiple items in one request (tasks, tags, kanban items).

**Request:**
```json
{
  "user_id": "user-uuid",
  "tasks": [
    { "id": "...", "title": "...", "version": 1, ... }
  ],
  "tags": [
    { "id": "...", "name": "...", "version": 1, ... }
  ],
  "kanban_items": [
    { "id": "...", "task_id": "...", "version": 1, ... }
  ]
}
```

**Limits:**
- Max 100 tasks per request
- Max 100 tags per request
- Max 100 kanban_items per request

**Response:**
```json
{
  "results": [
    {
      "id": "item-uuid",
      "entity_type": "task",
      "status": "success",
      "version": 2
    },
    {
      "id": "item2-uuid",
      "entity_type": "task",
      "status": "conflict",
      "server_version": 5
    },
    {
      "id": "item3-uuid",
      "entity_type": "tag",
      "status": "error",
      "error": "Validation error: ..."
    }
  ],
  "success_count": 45,
  "conflict_count": 3,
  "error_count": 2,
  "server_timestamp": "2024-11-06T10:30:00Z"
}
```

**Result statuses:**
- `success`: Item synced successfully
- `conflict`: Version conflict detected (client should fetch server data)
- `error`: Sync failed (see `error` field)

---

## Statistics

### Get Sync Stats

#### `GET /stats`
Get user's synchronization statistics.

**Query Parameters:**
- `user_id` (required)

**Response:**
```json
{
  "user_id": "user-uuid",
  "last_sync": "2024-11-06T10:30:00Z",
  "pending_tasks": 5,
  "pending_tags": 2,
  "pending_kanban_items": 3,
  "total_tasks": 120,
  "total_tags": 15
}
```

---

## WebSocket

### Real-time Sync Notifications

#### `WebSocket /ws`
WebSocket endpoint for real-time synchronization notifications.

**Connection:**
```
ws://server/api/tasks/ws?token=<jwt_token>
```

**Events sent to client:**

1. **CONNECTED**
```json
{
  "type": "CONNECTED",
  "user_id": "user-uuid",
  "timestamp": "2024-11-06T10:30:00Z",
  "message": "Tasks WebSocket connected"
}
```

2. **SYNC_REQUIRED**
```json
{
  "type": "SYNC_REQUIRED",
  "entity_type": "task",
  "timestamp": "2024-11-06T10:30:00Z"
}
```

3. **ITEM_CHANGED**
```json
{
  "type": "ITEM_CHANGED",
  "entity_type": "task",
  "item_id": "task-uuid",
  "action": "updated",
  "timestamp": "2024-11-06T10:30:00Z"
}
```

4. **PING** (heartbeat)
```json
{
  "type": "PING"
}
```

**Client should respond to PING:**
```json
{
  "type": "PONG"
}
```

**Event types:**
- `CONNECTED`: Connection established
- `SYNC_REQUIRED`: Data changed, client should sync
- `ITEM_CHANGED`: Specific item modified (with item_id and action)
- `PING`: Server heartbeat

**Actions:**
- `created`: New item created
- `updated`: Item updated
- `deleted`: Item deleted (soft or hard)

---

## Error Responses

### 400 Bad Request
Invalid request data.

### 401 Unauthorized
Missing or invalid JWT token.

### 403 Forbidden
User ID mismatch or insufficient permissions.

### 404 Not Found
Resource not found.

### 409 Conflict
Version conflict detected. Response includes server data.

### 500 Internal Server Error
Server error.

---

## Conflict Resolution Strategy

**Last-write-wins by version number:**

1. Client sends item with `version` field
2. Server compares with stored version
3. If `client_version < server_version` → **CONFLICT** (HTTP 409)
4. If `client_version >= server_version` → **ACCEPT** and increment version
5. Client receiving conflict must:
   - Fetch server data from `server_data` field
   - Merge changes (or use server data)
   - Retry with updated version

**Example conflict resolution flow:**
```
1. Client: POST task with version=2
2. Server: version=5 (conflict!)
3. Server responds: 409 with server_data
4. Client: Fetch server_data (version=5)
5. Client: Merge or overwrite local
6. Client: POST task with version=5
7. Server: Accept, increment to version=6
```

---

## Rate Limiting

- Bulk sync: Max 100 items per entity type
- Recommended sync interval: Every 5 minutes for background sync
- Manual sync: Trigger on user actions (save, delete)

---

## Best Practices

1. **Incremental Sync:**
   - Use `since` parameter with last sync timestamp
   - Only fetch items modified after last sync

2. **Conflict Handling:**
   - Always include version field
   - Handle 409 responses gracefully
   - Prefer server data in conflicts unless user explicitly overwrites

3. **WebSocket:**
   - Connect once per session
   - Listen for SYNC_REQUIRED events
   - Respond to PING with PONG

4. **Offline Support:**
   - Queue changes locally (SQLite)
   - Sync when connection restored
   - Handle conflicts from concurrent changes

5. **Batch Operations:**
   - Use bulk-sync for multiple items
   - Reduces HTTP overhead
   - Better for slow connections
