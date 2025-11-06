"""
WebSocket Client dla real-time synchronizacji Tasks & Kanban.

Automatycznie łączy się z serwerem i nasłuchuje na zmiany:
- SYNC_REQUIRED: Wymaga synchronizacji (entity_type)
- ITEM_CHANGED: Zmiana konkretnego item (entity_type, item_id, action)
- CONNECTED: Potwierdzenie połączenia
- PING/PONG: Heartbeat

Emisja sygnałów PyQt6 dla UI updates.
"""

from PyQt6.QtCore import QThread, pyqtSignal
from typing import Optional, Callable
import websockets
import json
import asyncio
from loguru import logger

# Import Status LED funkcji (optional)
try:
    from ...ui.status_led import record_websocket_connected, record_websocket_disconnected
    STATUS_LED_AVAILABLE = True
except ImportError:
    STATUS_LED_AVAILABLE = False
    logger.debug("Status LED module not available for WebSocket")


class TasksWebSocketClient(QThread):
    """
    WebSocket client dla Tasks & Kanban z auto-reconnect.
    
    Signals:
        connected: Połączono z serwerem
        disconnected: Rozłączono
        error: Błąd połączenia (str)
        sync_required: Wymaga synchronizacji (str entity_type)
        item_changed: Zmiana item (str entity_type, str item_id, str action)
        heartbeat: Heartbeat otrzymany
    """
    
    # Sygnały
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    
    sync_required = pyqtSignal(str)  # entity_type
    item_changed = pyqtSignal(str, str, str)  # entity_type, item_id, action
    heartbeat = pyqtSignal()
    
    def __init__(
        self,
        base_url: str,
        auth_token: str,
        auto_reconnect: bool = True,
        reconnect_delay: int = 5
    ):
        """
        Initialize WebSocket client.
        
        Args:
            base_url: Base URL serwera (np. "http://localhost:8000" lub "https://api.example.com")
            auth_token: JWT access token
            auto_reconnect: Czy automatycznie reconnect po rozłączeniu
            reconnect_delay: Opóźnienie między próbami reconnect (sekundy)
        """
        super().__init__()
        
        # Konwertuj HTTP na WS
        self.base_url = base_url
        ws_url = base_url.replace("http://", "ws://").replace("https://", "wss://")
        self.ws_base_url = f"{ws_url}/api/tasks/ws"
        
        self.auth_token = auth_token
        self.auto_reconnect = auto_reconnect
        self.reconnect_delay = reconnect_delay
        
        self._websocket: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def update_token(self, new_token: str):
        """Zaktualizuj token autoryzacji (np. po refresh)"""
        self.auth_token = new_token
        logger.debug("WebSocket token updated")
    
    @property
    def ws_url(self) -> str:
        """Zwraca URL WebSocket z aktualnym tokenem"""
        return f"{self.ws_base_url}?token={self.auth_token}"
    
    def run(self):
        """Uruchom WebSocket client w osobnym wątku"""
        self._running = True
        
        # Utwórz event loop dla tego wątku
        self._loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self._loop)
        
        try:
            self._loop.run_until_complete(self._connect_loop())
        except Exception as e:
            logger.error(f"Tasks WebSocket client error: {e}")
            self.error.emit(str(e))
        finally:
            self._loop.close()
    
    async def _connect_loop(self):
        """Główna pętla z auto-reconnect"""
        consecutive_auth_failures = 0
        max_auth_failures = 3
        
        while self._running:
            try:
                await self._connect_and_listen()
                consecutive_auth_failures = 0  # Reset po udanym połączeniu
                
            except websockets.exceptions.ConnectionClosedError as e:
                # Sprawdź czy to błąd autoryzacji (403 Forbidden)
                if e.code == 403:
                    consecutive_auth_failures += 1
                    logger.error(f"WebSocket authorization failed (403) - attempt {consecutive_auth_failures}/{max_auth_failures}")
                    
                    if consecutive_auth_failures >= max_auth_failures:
                        logger.warning("🔴 Too many authorization failures - stopping WebSocket reconnect")
                        logger.warning("💡 Token may have expired - please refresh authentication")
                        self.error.emit("Authorization failed: Token may have expired")
                        break  # Zatrzymaj pętlę reconnect
                else:
                    consecutive_auth_failures = 0
                    
                logger.error(f"WebSocket connection failed: {e}")
                self.error.emit(f"Connection failed: {e}")
                self.disconnected.emit()
                
            except Exception as e:
                consecutive_auth_failures = 0
                logger.error(f"WebSocket connection failed: {e}")
                self.error.emit(f"Connection failed: {e}")
                self.disconnected.emit()
                
            if not self.auto_reconnect:
                break
            
            # Zwiększ opóźnienie dla błędów autoryzacji
            delay = self.reconnect_delay
            if consecutive_auth_failures > 0:
                delay = min(30, self.reconnect_delay * consecutive_auth_failures)  # Maksymalnie 30s
                logger.info(f"Authorization failure - waiting {delay}s before retry...")
            else:
                logger.info(f"Reconnecting in {delay}s...")
                
            await asyncio.sleep(delay)
    
    async def _connect_and_listen(self):
        """Połącz się i nasłuchuj na wiadomości"""
        async with websockets.connect(
            self.ws_url,
            ping_interval=30,
            ping_timeout=10,
            close_timeout=5
        ) as websocket:
            self._websocket = websocket
            self.connected.emit()
            logger.info("Tasks WebSocket connected")
            
            # Rejestruj połączenie w Status LED
            if STATUS_LED_AVAILABLE:
                record_websocket_connected("tasks")
            
            try:
                # Główna pętla odbierania wiadomości
                async for message in websocket:
                    await self._handle_message(message)
            
            except websockets.ConnectionClosed:
                logger.info("Tasks WebSocket connection closed")
                self.disconnected.emit()
                
                # Rejestruj rozłączenie w Status LED
                if STATUS_LED_AVAILABLE:
                    record_websocket_disconnected("tasks")
            
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                self.error.emit(str(e))
                
                if STATUS_LED_AVAILABLE:
                    record_websocket_disconnected("tasks")
            
            finally:
                self._websocket = None
    
    async def _handle_message(self, message: str):
        """
        Obsłuż wiadomość od serwera.
        
        Expected message formats:
        - {"type": "CONNECTED", "message": "..."}
        - {"type": "SYNC_REQUIRED", "entity_type": "task"}
        - {"type": "ITEM_CHANGED", "entity_type": "task", "item_id": "uuid", "action": "created"}
        - {"type": "PING"}
        - {"type": "PONG"}
        
        Args:
            message: JSON string z wiadomością
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            # Emisja odpowiedniego sygnału
            if msg_type == "SYNC_REQUIRED":
                entity_type = data.get("entity_type", "unknown")
                logger.debug(f"Sync required for: {entity_type}")
                self.sync_required.emit(entity_type)
            
            elif msg_type == "ITEM_CHANGED":
                entity_type = data.get("entity_type", "unknown")
                item_id = data.get("item_id", "")
                action = data.get("action", "updated")
                logger.debug(f"Item changed: {entity_type}:{item_id} ({action})")
                self.item_changed.emit(entity_type, item_id, action)
            
            elif msg_type == "CONNECTED":
                logger.info(f"Tasks WebSocket connected: {data.get('message')}")
            
            elif msg_type == "PING":
                # Odpowiedz PONGiem
                await self._send_message({"type": "PONG"})
                self.heartbeat.emit()
            
            elif msg_type == "PONG":
                self.heartbeat.emit()
            
            elif msg_type == "error":
                error_msg = data.get("error", "Unknown error")
                logger.error(f"Server error: {error_msg}")
                self.error.emit(error_msg)
            
            else:
                logger.warning(f"Unknown message type: {msg_type}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode message: {e}")
            self.error.emit(f"Invalid JSON: {e}")
        
        except Exception as e:
            logger.error(f"Error handling message: {e}")
            self.error.emit(str(e))
    
    async def _send_message(self, message: dict):
        """Wyślij wiadomość do serwera"""
        if self._websocket and not self._websocket.closed:
            try:
                await self._websocket.send(json.dumps(message))
            except Exception as e:
                logger.error(f"Failed to send message: {e}")
                self.error.emit(f"Send failed: {e}")
    
    def send_ping(self):
        """Wyślij ping do serwera"""
        if self._loop and self._loop.is_running():
            asyncio.run_coroutine_threadsafe(
                self._send_message({"type": "PING"}),
                self._loop
            )
    
    def stop(self):
        """Zatrzymaj WebSocket client"""
        self._running = False
        
        if self._websocket and not self._websocket.closed:
            # Zamknij połączenie
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._websocket.close(),
                    self._loop
                )
        
        # Zatrzymaj wątek
        self.quit()
        self.wait()
        
        logger.info("Tasks WebSocket client stopped")
    
    def is_connected(self) -> bool:
        """Sprawdź czy połączony"""
        return self._websocket is not None and not self._websocket.closed


# =============================================================================
# Helper Functions
# =============================================================================

def create_tasks_websocket_client(
    base_url: str,
    auth_token: str,
    on_sync_required: Optional[Callable[[str], None]] = None,
    on_item_changed: Optional[Callable[[str, str, str], None]] = None,
    auto_reconnect: bool = True
) -> TasksWebSocketClient:
    """
    Utwórz i skonfiguruj Tasks WebSocket client.
    
    Args:
        base_url: Base URL serwera
        auth_token: JWT access token
        on_sync_required: Callback dla wymaganej synchronizacji (entity_type)
        on_item_changed: Callback dla zmiany item (entity_type, item_id, action)
        auto_reconnect: Czy automatycznie reconnect
    
    Returns:
        Skonfigurowany TasksWebSocketClient (nie uruchomiony)
    
    Example:
        ws = create_tasks_websocket_client(
            base_url="http://localhost:8000",
            auth_token="your_token",
            on_sync_required=lambda entity_type: print(f"Sync required: {entity_type}"),
            on_item_changed=lambda et, id, action: print(f"{et}:{id} {action}"),
            auto_reconnect=True
        )
        
        ws.start()  # Uruchom w tle
        
        # Później:
        ws.stop()  # Zatrzymaj
    """
    client = TasksWebSocketClient(base_url, auth_token, auto_reconnect)
    
    # Podłącz callbacki
    if on_sync_required:
        client.sync_required.connect(on_sync_required)
    
    if on_item_changed:
        client.item_changed.connect(on_item_changed)
    
    return client
