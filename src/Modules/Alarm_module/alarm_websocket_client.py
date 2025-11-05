"""
WebSocket Client dla real-time synchronizacji alarmów.

Automatycznie łączy się z serwerem i nasłuchuje na zmiany:
- alarm_created, alarm_updated, alarm_deleted
- timer_created, timer_updated, timer_deleted  
- sync_required

Emisja sygnałów PyQt6 dla UI updates.
"""

from PyQt6.QtCore import QThread, pyqtSignal, QObject
from typing import Optional, Callable, Dict, Any
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


class WebSocketClient(QThread):
    """
    WebSocket client z auto-reconnect i event handling.
    
    Signals:
        connected: Połączono z serwerem
        disconnected: Rozłączono
        error: Błąd połączenia (str)
        alarm_created: Nowy alarm (dict)
        alarm_updated: Zaktualizowany alarm (dict)
        alarm_deleted: Usunięty alarm (dict)
        timer_created: Nowy timer (dict)
        timer_updated: Zaktualizowany timer (dict)
        timer_deleted: Usunięty timer (dict)
        sync_required: Wymaga synchronizacji (str reason)
        heartbeat: Heartbeat otrzymany
    """
    
    # Sygnały
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    error = pyqtSignal(str)
    
    alarm_created = pyqtSignal(dict)
    alarm_updated = pyqtSignal(dict)
    alarm_deleted = pyqtSignal(dict)
    
    timer_created = pyqtSignal(dict)
    timer_updated = pyqtSignal(dict)
    timer_deleted = pyqtSignal(dict)
    
    sync_required = pyqtSignal(str)
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
        self.ws_base_url = f"{ws_url}/api/alarms-timers/ws"
        
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
            logger.error(f"WebSocket client error: {e}")
            self.error.emit(str(e))
        finally:
            self._loop.close()
    
    async def _connect_loop(self):
        """Główna pętla z auto-reconnect"""
        consecutive_auth_failures = 0  # 🔧 DODAJ: Licznik kolejnych błędów autoryzacji
        max_auth_failures = 3  # 🔧 DODAJ: Maksymalna liczba prób z wygasłym tokenem
        
        while self._running:
            try:
                await self._connect_and_listen()
                consecutive_auth_failures = 0  # Reset po udanym połączeniu
                
            except websockets.exceptions.ConnectionClosedError as e:
                # 🔧 SPRAWDŹ czy to błąd autoryzacji (403 Forbidden)
                if e.code == 403:
                    consecutive_auth_failures += 1
                    logger.error(f"WebSocket authorization failed (403) - attempt {consecutive_auth_failures}/{max_auth_failures}")
                    
                    if consecutive_auth_failures >= max_auth_failures:
                        logger.warning("🔴 Too many authorization failures - stopping WebSocket reconnect")
                        logger.warning("💡 Token may have expired - please refresh authentication")
                        self.error.emit("Authorization failed: Token may have expired")
                        break  # Zatrzymaj pętlę reconnect
                else:
                    consecutive_auth_failures = 0  # Reset dla innych błędów
                    
                logger.error(f"WebSocket connection failed: {e}")
                self.error.emit(f"Connection failed: {e}")
                self.disconnected.emit()
                
            except Exception as e:
                consecutive_auth_failures = 0  # Reset dla innych błędów
                logger.error(f"WebSocket connection failed: {e}")
                self.error.emit(f"Connection failed: {e}")
                self.disconnected.emit()
                
            if not self.auto_reconnect:
                break
            
            # 🔧 Zwiększ opóźnienie dla błędów autoryzacji
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
            logger.info("WebSocket connected")
            
            # Rejestruj połączenie w Status LED
            if STATUS_LED_AVAILABLE:
                record_websocket_connected("alarms")
            
            try:
                # Główna pętla odbierania wiadomości
                async for message in websocket:
                    await self._handle_message(message)
            
            except websockets.ConnectionClosed:
                logger.info("WebSocket connection closed")
                self.disconnected.emit()
                
                # Rejestruj rozłączenie w Status LED
                if STATUS_LED_AVAILABLE:
                    record_websocket_disconnected("alarms")
            
            except Exception as e:
                logger.error(f"Error receiving message: {e}")
                self.error.emit(str(e))
                
                # Rejestruj błąd w Status LED
                if STATUS_LED_AVAILABLE:
                    record_websocket_disconnected("alarms")
            
            finally:
                self._websocket = None
    
    async def _handle_message(self, message: str):
        """
        Obsłuż wiadomość od serwera.
        
        Args:
            message: JSON string z wiadomością
        """
        try:
            data = json.loads(message)
            msg_type = data.get("type")
            
            # Emisja odpowiedniego sygnału
            if msg_type == "alarm_created":
                self.alarm_created.emit(data.get("data", {}))
            
            elif msg_type == "alarm_updated":
                self.alarm_updated.emit(data.get("data", {}))
            
            elif msg_type == "alarm_deleted":
                self.alarm_deleted.emit(data.get("data", {}))
            
            elif msg_type == "timer_created":
                self.timer_created.emit(data.get("data", {}))
            
            elif msg_type == "timer_updated":
                self.timer_updated.emit(data.get("data", {}))
            
            elif msg_type == "timer_deleted":
                self.timer_deleted.emit(data.get("data", {}))
            
            elif msg_type == "sync_required":
                reason = data.get("reason", "Server changes")
                self.sync_required.emit(reason)
            
            elif msg_type == "heartbeat":
                self.heartbeat.emit()
            
            elif msg_type == "connected":
                logger.info(f"WebSocket connected: {data.get('message')}")
            
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
                self._send_message({"type": "ping"}),
                self._loop
            )
    
    def stop(self):
        """Zatrzymaj WebSocket client"""
        self._running = False
        
        if self._websocket and not self._websocket.closed:
            # Wyślij unsubscribe
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._send_message({"type": "unsubscribe"}),
                    self._loop
                )
            
            # Zamknij połączenie
            if self._loop and self._loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    self._websocket.close(),
                    self._loop
                )
        
        # Zatrzymaj wątek
        self.quit()
        self.wait()
        
        logger.info("WebSocket client stopped")
    
    def is_connected(self) -> bool:
        """Sprawdź czy połączony"""
        return self._websocket is not None and not self._websocket.closed


# =============================================================================
# Helper Functions
# =============================================================================

def create_websocket_client(
    base_url: str,
    auth_token: str,
    on_alarm_updated: Optional[Callable[[dict], None]] = None,
    on_timer_updated: Optional[Callable[[dict], None]] = None,
    on_sync_required: Optional[Callable[[str], None]] = None,
    auto_reconnect: bool = True
) -> WebSocketClient:
    """
    Utwórz i skonfiguruj WebSocket client.
    
    Args:
        base_url: Base URL serwera
        auth_token: JWT access token
        on_alarm_updated: Callback dla zmian alarmów
        on_timer_updated: Callback dla zmian timerów
        on_sync_required: Callback dla wymaganej synchronizacji
        auto_reconnect: Czy automatycznie reconnect
    
    Returns:
        Skonfigurowany WebSocketClient (nie uruchomiony)
    
    Example:
        ws = create_websocket_client(
            base_url="http://localhost:8000",
            auth_token="your_token",
            on_alarm_updated=lambda data: print(f"Alarm updated: {data}"),
            auto_reconnect=True
        )
        
        ws.start()  # Uruchom w tle
        
        # Później:
        ws.stop()  # Zatrzymaj
    """
    client = WebSocketClient(base_url, auth_token, auto_reconnect)
    
    # Podłącz callbacki
    if on_alarm_updated:
        client.alarm_updated.connect(on_alarm_updated)
        client.alarm_created.connect(on_alarm_updated)
        client.alarm_deleted.connect(on_alarm_updated)
    
    if on_timer_updated:
        client.timer_updated.connect(on_timer_updated)
        client.timer_created.connect(on_timer_updated)
        client.timer_deleted.connect(on_timer_updated)
    
    if on_sync_required:
        client.sync_required.connect(on_sync_required)
    
    return client
