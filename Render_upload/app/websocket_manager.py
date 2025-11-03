"""
WebSocket Manager dla real-time synchronizacji alarmów i timerów.

Obsługuje:
- Połączenia WebSocket per user
- Broadcasting zmian do wszystkich połączonych klientów użytkownika
- Heartbeat dla utrzymania połączenia
- Automatyczne rozłączanie nieaktywnych połączeń
"""

from fastapi import WebSocket, WebSocketDisconnect
from typing import Dict, Set, Optional, Any
from datetime import datetime
import json
import asyncio
from loguru import logger


class ConnectionManager:
    """Zarządzanie połączeniami WebSocket"""
    
    def __init__(self):
        # user_id -> Set[WebSocket]
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        self._lock = asyncio.Lock()
    
    async def connect(self, websocket: WebSocket, user_id: str):
        """Dodaj nowe połączenie WebSocket dla użytkownika"""
        await websocket.accept()
        
        async with self._lock:
            if user_id not in self.active_connections:
                self.active_connections[user_id] = set()
            self.active_connections[user_id].add(websocket)
        
        logger.info(f"WebSocket connected: user={user_id}, total={len(self.active_connections[user_id])}")
    
    async def disconnect(self, websocket: WebSocket, user_id: str):
        """Usuń połączenie WebSocket"""
        async with self._lock:
            if user_id in self.active_connections:
                self.active_connections[user_id].discard(websocket)
                
                # Usuń user_id jeśli brak połączeń
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        
        logger.info(f"WebSocket disconnected: user={user_id}")
    
    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Wyślij wiadomość do konkretnego WebSocket"""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.error(f"Error sending personal message: {e}")
    
    async def broadcast_to_user(self, message: dict, user_id: str):
        """Wyślij wiadomość do wszystkich połączeń użytkownika"""
        if user_id not in self.active_connections:
            logger.debug(f"No active connections for user {user_id}")
            return
        
        # Kopia set żeby uniknąć modyfikacji podczas iteracji
        connections = self.active_connections[user_id].copy()
        
        disconnected = []
        for connection in connections:
            try:
                await connection.send_json(message)
            except WebSocketDisconnect:
                disconnected.append(connection)
            except Exception as e:
                logger.error(f"Error broadcasting to user {user_id}: {e}")
                disconnected.append(connection)
        
        # Usuń rozłączone połączenia
        if disconnected:
            async with self._lock:
                for conn in disconnected:
                    self.active_connections[user_id].discard(conn)
                
                if not self.active_connections[user_id]:
                    del self.active_connections[user_id]
        
        logger.debug(f"Broadcast to user {user_id}: {len(connections)} connections, {len(disconnected)} failed")
    
    async def broadcast_to_all(self, message: dict):
        """Wyślij wiadomość do wszystkich użytkowników"""
        users = list(self.active_connections.keys())
        for user_id in users:
            await self.broadcast_to_user(message, user_id)
    
    def get_user_connection_count(self, user_id: str) -> int:
        """Zwróć liczbę aktywnych połączeń użytkownika"""
        return len(self.active_connections.get(user_id, set()))
    
    def get_total_connections(self) -> int:
        """Zwróć łączną liczbę połączeń"""
        return sum(len(connections) for connections in self.active_connections.values())
    
    def get_stats(self) -> dict:
        """Zwróć statystyki połączeń"""
        return {
            "total_users": len(self.active_connections),
            "total_connections": self.get_total_connections(),
            "users": {
                user_id: len(connections)
                for user_id, connections in self.active_connections.items()
            }
        }


# Singleton instance
manager = ConnectionManager()


# =============================================================================
# Event Types
# =============================================================================

class WSEventType:
    """Typy eventów WebSocket"""
    
    # Server -> Client
    ALARM_CREATED = "alarm_created"
    ALARM_UPDATED = "alarm_updated"
    ALARM_DELETED = "alarm_deleted"
    TIMER_CREATED = "timer_created"
    TIMER_UPDATED = "timer_updated"
    TIMER_DELETED = "timer_deleted"
    SYNC_REQUIRED = "sync_required"
    HEARTBEAT = "heartbeat"
    ERROR = "error"
    
    # Client -> Server
    PING = "ping"
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"


# =============================================================================
# Message Builders
# =============================================================================

def build_item_event(event_type: str, item_data: dict, user_id: str) -> dict:
    """
    Zbuduj event dla zmiany alarmu/timera.
    
    Args:
        event_type: Typ eventu (np. WSEventType.ALARM_CREATED)
        item_data: Dane alarmu/timera
        user_id: ID użytkownika
    
    Returns:
        Dict z eventem gotowym do wysłania przez WebSocket
    """
    return {
        "type": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "data": item_data
    }


def build_sync_event(user_id: str, reason: str = "Changes detected") -> dict:
    """
    Zbuduj event wymuszający synchronizację.
    
    Args:
        user_id: ID użytkownika
        reason: Powód synchronizacji
    
    Returns:
        Dict z eventem sync_required
    """
    return {
        "type": WSEventType.SYNC_REQUIRED,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "reason": reason
    }


def build_heartbeat() -> dict:
    """Zbuduj heartbeat message"""
    return {
        "type": WSEventType.HEARTBEAT,
        "timestamp": datetime.utcnow().isoformat()
    }


def build_error(error_message: str, details: Optional[dict] = None) -> dict:
    """Zbuduj error message"""
    return {
        "type": WSEventType.ERROR,
        "timestamp": datetime.utcnow().isoformat(),
        "error": error_message,
        "details": details or {}
    }


# =============================================================================
# Broadcasting Functions
# =============================================================================

async def notify_item_change(
    event_type: str,
    item_data: dict,
    user_id: str
):
    """
    Powiadom użytkownika o zmianie alarmu/timera.
    
    Args:
        event_type: Typ eventu (WSEventType.ALARM_CREATED itp.)
        item_data: Dane alarmu/timera (dict z Pydantic model)
        user_id: ID użytkownika
    """
    event = build_item_event(event_type, item_data, user_id)
    await manager.broadcast_to_user(event, user_id)
    logger.debug(f"Notified user {user_id} about {event_type}")


async def notify_sync_required(user_id: str, reason: str = "Server changes"):
    """
    Powiadom użytkownika że powinien zsynchronizować dane.
    
    Args:
        user_id: ID użytkownika
        reason: Powód wymaganej synchronizacji
    """
    event = build_sync_event(user_id, reason)
    await manager.broadcast_to_user(event, user_id)
    logger.debug(f"Notified user {user_id} to sync: {reason}")


# =============================================================================
# Heartbeat Task
# =============================================================================

async def heartbeat_task(websocket: WebSocket, interval: int = 30):
    """
    Wysyłaj heartbeat co X sekund.
    
    Args:
        websocket: Połączenie WebSocket
        interval: Interwał w sekundach (domyślnie 30)
    """
    try:
        while True:
            await asyncio.sleep(interval)
            heartbeat = build_heartbeat()
            await websocket.send_json(heartbeat)
            logger.debug("Heartbeat sent")
    except WebSocketDisconnect:
        logger.debug("Heartbeat stopped - WebSocket disconnected")
    except Exception as e:
        logger.error(f"Heartbeat error: {e}")


# =============================================================================
# Message Handler
# =============================================================================

async def handle_client_message(message: dict, websocket: WebSocket, user_id: str):
    """
    Obsłuż wiadomość od klienta.
    
    Args:
        message: Wiadomość od klienta (dict)
        websocket: Połączenie WebSocket
        user_id: ID użytkownika
    """
    msg_type = message.get("type")
    
    if msg_type == WSEventType.PING:
        # Odpowiedz pongiem
        await manager.send_personal_message({
            "type": "pong",
            "timestamp": datetime.utcnow().isoformat()
        }, websocket)
    
    elif msg_type == WSEventType.SUBSCRIBE:
        # Subskrypcja - już obsłużone przez connect
        await manager.send_personal_message({
            "type": "subscribed",
            "timestamp": datetime.utcnow().isoformat(),
            "user_id": user_id
        }, websocket)
    
    elif msg_type == WSEventType.UNSUBSCRIBE:
        # Unsubskrypcja - rozłącz
        await manager.disconnect(websocket, user_id)
    
    else:
        logger.warning(f"Unknown message type from client: {msg_type}")
        await manager.send_personal_message(
            build_error(f"Unknown message type: {msg_type}"),
            websocket
        )
