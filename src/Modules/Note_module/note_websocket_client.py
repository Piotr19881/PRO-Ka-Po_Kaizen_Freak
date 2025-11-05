"""
Notes WebSocket Client - Real-time synchronization updates
Obsługuje WebSocket connection do serwera dla live updates notatek
"""
import json
import logging
from typing import Optional, Dict, Any
from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QUrl
from PyQt6.QtWebSockets import QWebSocket
from PyQt6.QtNetwork import QAbstractSocket

logger = logging.getLogger(__name__)


class NoteWebSocketClient(QObject):
    """
    WebSocket client do real-time synchronizacji notatek
    Nasłuchuje zmian z serwera i emituje sygnały PyQt
    """
    
    # Sygnały emitowane przy otrzymaniu event'ów z serwera
    note_created = pyqtSignal(dict)      # {'id': str, 'user_id': str, 'title': str, ...}
    note_updated = pyqtSignal(dict)      # {'id': str, 'title': str, 'content': str, ...}
    note_deleted = pyqtSignal(str)       # note_id: str
    link_created = pyqtSignal(dict)      # {'id': str, 'source_note_id': str, ...}
    link_deleted = pyqtSignal(str)       # link_id: str
    
    # Sygnały statusu połączenia
    connected = pyqtSignal()
    disconnected = pyqtSignal()
    connection_error = pyqtSignal(str)   # error_message: str
    
    def __init__(self, ws_url: str, user_id: str, auth_token: Optional[str] = None):
        """
        Inicjalizacja WebSocket client
        
        Args:
            ws_url: WebSocket URL (np. "ws://localhost:8000/api/v1/ws/notes/{user_id}")
            user_id: UUID użytkownika
            auth_token: JWT token autoryzacyjny (opcjonalny)
        """
        super().__init__()
        
        self.user_id = user_id
        self.auth_token = auth_token
        self.ws_url = ws_url.format(user_id=user_id) if "{user_id}" in ws_url else ws_url
        
        # WebSocket instance
        self.websocket: Optional[QWebSocket] = None
        
        # Reconnection logic
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self._attempt_reconnect)
        self.reconnect_interval = 5000  # 5 sekund
        self.max_reconnect_attempts = 10
        self.reconnect_attempts = 0
        
        # Connection state
        self.is_connected = False
        self.is_intentional_disconnect = False
        
        logger.info(f"WebSocket client initialized for user {user_id}")
    
    def update_token(self, new_token: str):
        """Zaktualizuj token autoryzacji (np. po refresh)"""
        self.auth_token = new_token
        logger.debug("WebSocket token updated")
    
    def connect_to_server(self):
        """Nawiązuje połączenie WebSocket z serwerem"""
        if self.websocket and self.is_connected:
            logger.warning("Already connected to WebSocket server")
            return
        
        self.is_intentional_disconnect = False
        
        # Utwórz nowy WebSocket
        self.websocket = QWebSocket()
        
        # Podłącz sygnały WebSocket
        self.websocket.connected.connect(self._on_connected)
        self.websocket.disconnected.connect(self._on_disconnected)
        self.websocket.textMessageReceived.connect(self._on_message_received)
        self.websocket.errorOccurred.connect(self._on_error)
        
        # Dodaj Authorization header jeśli mamy token
        if self.auth_token:
            # WebSocket nie wspiera custom headers w Qt, więc dodajemy token do URL
            if "?" in self.ws_url:
                url_with_token = f"{self.ws_url}&token={self.auth_token}"
            else:
                url_with_token = f"{self.ws_url}?token={self.auth_token}"
        else:
            url_with_token = self.ws_url
        
        logger.info(f"Connecting to WebSocket: {self.ws_url}")
        # Konwertuj string URL na QUrl przed otwarciem połączenia
        self.websocket.open(QUrl(url_with_token))
    
    def disconnect_from_server(self):
        """Zamyka połączenie WebSocket"""
        self.is_intentional_disconnect = True
        self.reconnect_timer.stop()
        
        if self.websocket and self.is_connected:
            logger.info("Closing WebSocket connection")
            self.websocket.close()
    
    def send_message(self, message: Dict[str, Any]):
        """
        Wysyła wiadomość do serwera przez WebSocket
        
        Args:
            message: Dict z danymi do wysłania (zostanie serializowany do JSON)
        """
        if not self.websocket or not self.is_connected:
            logger.warning("Cannot send message - WebSocket not connected")
            return
        
        try:
            message_json = json.dumps(message)
            self.websocket.sendTextMessage(message_json)
            logger.debug(f"Sent message: {message}")
        except Exception as e:
            logger.error(f"Failed to send message: {e}")
    
    # =============================================================================
    # PRIVATE METHODS - WebSocket Event Handlers
    # =============================================================================
    
    def _on_connected(self):
        """Callback wywoływany po nawiązaniu połączenia"""
        self.is_connected = True
        self.reconnect_attempts = 0
        self.reconnect_timer.stop()
        
        logger.info("✅ WebSocket connected successfully")
        self.connected.emit()
    
    def _on_disconnected(self):
        """Callback wywoływany po rozłączeniu"""
        was_connected = self.is_connected
        self.is_connected = False
        
        logger.warning("❌ WebSocket disconnected")
        self.disconnected.emit()
        
        # Próbuj reconnect jeśli nie było to celowe rozłączenie
        if not self.is_intentional_disconnect and was_connected:
            self._schedule_reconnect()
    
    def _on_message_received(self, message: str):
        """
        Callback wywoływany po otrzymaniu wiadomości
        
        Args:
            message: JSON string z danymi
        """
        try:
            data = json.loads(message)
            event_type = data.get("type")
            payload = data.get("data", {})
            
            logger.debug(f"Received WebSocket event: {event_type}")
            
            # Obsłuż różne typy eventów
            if event_type == "note_created":
                self.note_created.emit(payload)
            
            elif event_type == "note_updated":
                self.note_updated.emit(payload)
            
            elif event_type == "note_deleted":
                note_id = payload.get("id") or payload.get("note_id")
                if note_id:
                    self.note_deleted.emit(note_id)
            
            elif event_type == "link_created":
                self.link_created.emit(payload)
            
            elif event_type == "link_deleted":
                link_id = payload.get("id") or payload.get("link_id")
                if link_id:
                    self.link_deleted.emit(link_id)
            
            elif event_type == "ping":
                # Odpowiedz na ping z pong
                self.send_message({"type": "pong"})
            
            elif event_type == "error":
                error_msg = payload.get("message", "Unknown error")
                logger.error(f"Server error: {error_msg}")
                self.connection_error.emit(error_msg)
            
            else:
                logger.warning(f"Unknown event type: {event_type}")
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode WebSocket message: {e}")
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def _on_error(self, error_code):
        """
        Callback wywoływany przy błędzie WebSocket
        
        Args:
            error_code: QAbstractSocket.SocketError
        """
        if self.websocket:
            error_string = self.websocket.errorString()
            logger.error(f"WebSocket error ({error_code}): {error_string}")
            self.connection_error.emit(error_string)
        
        # Jeśli błąd połączenia, spróbuj reconnect
        if error_code in [
            QAbstractSocket.SocketError.ConnectionRefusedError,
            QAbstractSocket.SocketError.RemoteHostClosedError,
            QAbstractSocket.SocketError.HostNotFoundError,
            QAbstractSocket.SocketError.NetworkError
        ]:
            self._schedule_reconnect()
    
    def _schedule_reconnect(self):
        """Planuje próbę reconnect"""
        if self.is_intentional_disconnect:
            return
        
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error(f"Max reconnect attempts ({self.max_reconnect_attempts}) reached")
            self.connection_error.emit("Cannot reconnect to server after multiple attempts")
            return
        
        if not self.reconnect_timer.isActive():
            logger.info(f"Scheduling reconnect in {self.reconnect_interval/1000}s...")
            self.reconnect_timer.start(self.reconnect_interval)
    
    def _attempt_reconnect(self):
        """Próbuje ponownie połączyć się z serwerem"""
        self.reconnect_attempts += 1
        logger.info(f"Reconnect attempt {self.reconnect_attempts}/{self.max_reconnect_attempts}")
        
        # Zamknij stare połączenie jeśli istnieje
        if self.websocket:
            self.websocket.deleteLater()
            self.websocket = None
        
        # Próbuj połączyć ponownie
        self.connect_to_server()
    
    def set_auth_token(self, token: str):
        """
        Aktualizuje token autoryzacyjny
        
        Args:
            token: Nowy JWT token
        """
        self.auth_token = token
        
        # Jeśli jesteśmy połączeni, reconnect z nowym tokenem
        if self.is_connected:
            logger.info("Auth token updated, reconnecting...")
            self.disconnect_from_server()
            self.connect_to_server()
    
    def cleanup(self):
        """Czyści zasoby (wywoływane przed zamknięciem aplikacji)"""
        logger.info("Cleaning up WebSocket client")
        self.disconnect_from_server()
        
        if self.websocket:
            self.websocket.deleteLater()
            self.websocket = None
        
        self.reconnect_timer.stop()


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_websocket_client(user_id: str, auth_token: Optional[str] = None) -> NoteWebSocketClient:
    """
    Tworzy i konfiguruje WebSocket client
    
    Args:
        user_id: UUID użytkownika
        auth_token: JWT token autoryzacyjny
        
    Returns:
        Skonfigurowany NoteWebSocketClient
    """
    import os
    
    # Pobierz WebSocket URL z environment variable
    # POPRAWKA: Zmieniono z /api/v1/ws/notes na /api/v1/notes/ws (zgodnie z router prefix)
    ws_base_url = os.getenv('NOTES_WS_URL', 'ws://127.0.0.1:8000/api/v1/notes/ws')
    ws_url = f"{ws_base_url}/{user_id}"
    
    client = NoteWebSocketClient(
        ws_url=ws_url,
        user_id=user_id,
        auth_token=auth_token
    )
    
    logger.info(f"Created WebSocket client for user: {user_id}")
    
    return client
