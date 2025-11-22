"""
Notes API Client - Komunikacja z backendem (synchronizacja notatek)
Obsługuje REST API endpoints oraz WebSocket dla real-time updates
"""
import requests
import json
from typing import Optional, Dict, Any, List, Callable
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class NotesAPIClient:
    """Klient API do synchronizacji notatek z serwerem"""
    
    def __init__(
        self, 
        base_url: str, 
        auth_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        on_token_refreshed: Optional[Callable[[str, str], None]] = None,
        timeout: int = 10
    ):
        """
        Inicjalizacja klienta API
        
        Args:
            base_url: URL bazowy API (np. "https://api.example.com/api/v1")
            auth_token: JWT token autoryzacyjny
            refresh_token: JWT refresh token
            on_token_refreshed: Callback wywoływany po odświeżeniu tokena: (new_access_token, new_refresh_token) -> None
            timeout: Timeout dla requestów w sekundach
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.on_token_refreshed = on_token_refreshed
        self.timeout = timeout
        self.session = requests.Session()
        self._update_headers()
    
    def _update_headers(self):
        """Aktualizuje nagłówki sesji z tokenem autoryzacyjnym"""
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json'
        })
        if self.auth_token:
            self.session.headers.update({
                'Authorization': f'Bearer {self.auth_token}'
            })
    
    def set_auth_token(self, token: str):
        """
        Ustawia token autoryzacyjny
        
        Args:
            token: JWT token
        """
        self.auth_token = token
        self._update_headers()
    
    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """
        Obsługuje odpowiedź z serwera
        
        Args:
            response: Obiekt Response z requests
            
        Returns:
            Dict z danymi odpowiedzi
            
        Raises:
            Exception: W przypadku błędu HTTP
        """
        try:
            response.raise_for_status()
            return response.json()
        except requests.exceptions.HTTPError as e:
            logger.error(f"HTTP Error: {e}, Response: {response.text}")
            raise Exception(f"API Error: {response.status_code} - {response.text}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Request Error: {e}")
            raise Exception(f"Network Error: {str(e)}")
        except json.JSONDecodeError as e:
            logger.error(f"JSON Decode Error: {e}, Response: {response.text}")
            raise Exception(f"Invalid JSON response: {str(e)}")
    
    # =============================================================================
    # TOKEN REFRESH
    # =============================================================================
    
    def _try_refresh_token(self) -> bool:
        """
        Próbuje odświeżyć access token za pomocą refresh tokena
        
        Returns:
            bool: True jeśli odświeżenie się powiodło, False w przeciwnym razie
        """
        if not self.refresh_token:
            logger.warning("Cannot refresh token: no refresh_token available")
            return False
        
        # Uzyskaj root URL (bez /notes)
        parts = self.base_url.split('/')
        root_url = '/'.join(parts[:3])  # http://127.0.0.1:8000
        refresh_url = f"{root_url}/api/v1/auth/refresh"
        
        logger.info("Attempting to refresh access token...")
        
        try:
            response = requests.post(
                refresh_url,
                json={"refresh_token": self.refresh_token},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                new_access_token = data.get('access_token')
                
                if new_access_token:
                    # Zaktualizuj token
                    self.set_auth_token(new_access_token)
                    logger.info("✓ Access token refreshed successfully")
                    
                    # Powiadom callback (który zaktualizuje WebSocket)
                    if self.on_token_refreshed:
                        self.on_token_refreshed(new_access_token, self.refresh_token)
                    
                    return True
                else:
                    logger.error("Refresh response missing access_token")
                    return False
            else:
                logger.error(f"Token refresh failed: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
            return False
    
    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Wykonuje request z automatycznym odświeżeniem tokena przy 401
        
        Args:
            method: Metoda HTTP (get, post, put, delete)
            url: URL endpointa
            **kwargs: Dodatkowe argumenty dla requests (json, params, timeout, etc.)
            
        Returns:
            requests.Response: Odpowiedź z serwera
            
        Raises:
            Exception: W przypadku błędu HTTP po retry
        """
        # Pierwszy próba
        response = self.session.request(method, url, **kwargs)
        
        # Jeśli 401 (Unauthorized), próbuj odświeżyć token
        if response.status_code == 401:
            logger.warning("Received 401, attempting token refresh...")
            
            if self._try_refresh_token():
                # Token odświeżony, ponów request
                logger.info("Retrying request with new token...")
                response = self.session.request(method, url, **kwargs)
            else:
                logger.error("Token refresh failed, cannot retry request")
        
        return response
    
    # =============================================================================
    # NOTES ENDPOINTS
    # =============================================================================
    
    def sync_note(self, note_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronizuje notatkę z serwerem (create/update)
        
        Args:
            note_data: Dane notatki:
                - local_id (str): UUID lokalne
                - user_id (str): UUID użytkownika
                - parent_id (Optional[str]): UUID rodzica
                - title (str): Tytuł
                - content (str): Treść HTML
                - color (str): Kolor (#RRGGBB)
                - version (int): Wersja (dla conflict resolution)
                - synced_at (Optional[str]): ISO timestamp ostatniej sync
        
        Returns:
            Dict z danymi zsynchronizowanej notatki (włącznie z server_id)
        """
        url = f"{self.base_url}/sync"
        
        # Przygotuj payload
        payload = {
            "local_id": note_data.get("local_id"),
            "user_id": note_data.get("user_id"),
            "parent_id": note_data.get("parent_id"),
            "title": note_data.get("title", ""),
            "content": note_data.get("content", ""),
            "color": note_data.get("color", "#1976D2"),
            "version": note_data.get("version", 1),
            "synced_at": note_data.get("synced_at")
        }
        
        logger.info(f"Syncing note: {payload.get('local_id')} (v{payload.get('version')})")
        
        try:
            response = self._request_with_retry('post', url, json=payload, timeout=10)
            result = self._handle_response(response)
            logger.info(f"Note synced successfully: {result.get('id')}")
            return result
        except Exception as e:
            logger.error(f"Failed to sync note {payload.get('local_id')}: {e}")
            raise
    
    def fetch_note(self, note_id: str) -> Dict[str, Any]:
        """
        Pobiera pojedynczą notatkę z serwera
        
        Args:
            note_id: UUID notatki na serwerze
            
        Returns:
            Dict z danymi notatki
        """
        url = f"{self.base_url}/notes/{note_id}"
        
        logger.info(f"Fetching note: {note_id}")
        
        try:
            response = self._request_with_retry('get', url, timeout=10)
            result = self._handle_response(response)
            logger.info(f"Note fetched: {note_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch note {note_id}: {e}")
            raise
    
    def fetch_user_notes(self, user_id: str) -> List[Dict[str, Any]]:
        """
        Pobiera wszystkie notatki użytkownika z serwera
        
        Args:
            user_id: UUID użytkownika
            
        Returns:
            ListaDict z notatkami
        """
        url = f"{self.base_url}/notes/user/{user_id}"
        
        logger.info(f"Fetching notes for user: {user_id}")
        
        try:
            response = self._request_with_retry('get', url, timeout=15)
            result = self._handle_response(response)
            # Response powinien być listą
            if isinstance(result, dict):
                result = result.get('notes', [])
            logger.info(f"Fetched {len(result)} notes for user {user_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch notes for user {user_id}: {e}")
            raise
    
    def delete_note(self, note_id: str) -> Dict[str, Any]:
        """
        Usuwa notatkę na serwerze
        
        Args:
            note_id: UUID notatki na serwerze
            
        Returns:
            Dict z potwierdzeniem usunięcia
        """
        url = f"{self.base_url}/notes/{note_id}"
        
        logger.info(f"Deleting note: {note_id}")
        
        try:
            response = self._request_with_retry('delete', url, timeout=10)
            result = self._handle_response(response)
            logger.info(f"Note deleted: {note_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to delete note {note_id}: {e}")
            raise
    
    # =============================================================================
    # NOTE LINKS ENDPOINTS
    # =============================================================================
    
    def sync_note_link(self, link_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Synchronizuje link między notatkami
        
        Args:
            link_data: Dane linka:
                - local_id (str): UUID lokalne linka
                - source_note_id (str): UUID notatki źródłowej
                - target_note_id (str): UUID notatki docelowej
                - link_text (str): Tekst linku
                - start_position (int): Pozycja początkowa w treści
                - end_position (int): Pozycja końcowa w treści
        
        Returns:
            Dict z danymi zsynchronizowanego linka
        """
        url = f"{self.base_url}/links/sync"
        
        payload = {
            "local_id": link_data.get("local_id"),
            "source_note_id": link_data.get("source_note_id"),
            "target_note_id": link_data.get("target_note_id"),
            "link_text": link_data.get("link_text", ""),
            "start_position": link_data.get("start_position", 0),
            "end_position": link_data.get("end_position", 0)
        }
        
        logger.info(f"Syncing link: {payload.get('local_id')}")
        
        try:
            response = self._request_with_retry('post', url, json=payload, timeout=10)
            result = self._handle_response(response)
            logger.info(f"Link synced successfully: {result.get('id')}")
            return result
        except Exception as e:
            logger.error(f"Failed to sync link {payload.get('local_id')}: {e}")
            raise
    
    def fetch_note_links(self, note_id: str) -> List[Dict[str, Any]]:
        """
        Pobiera wszystkie linki dla danej notatki
        
        Args:
            note_id: UUID notatki
            
        Returns:
            Lista Dict z linkami
        """
        url = f"{self.base_url}/note-links/note/{note_id}"
        
        logger.info(f"Fetching links for note: {note_id}")
        
        try:
            response = self._request_with_retry('get', url, timeout=10)
            result = self._handle_response(response)
            # Response powinien być listą
            if isinstance(result, dict):
                result = result.get('links', [])
            logger.info(f"Fetched {len(result)} links for note {note_id}")
            return result
        except Exception as e:
            logger.error(f"Failed to fetch links for note {note_id}: {e}")
            raise
    
    # =============================================================================
    # BATCH OPERATIONS
    # =============================================================================
    
    def sync_notes_batch(self, notes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Synchronizuje wiele notatek w jednym wywołaniu
        
        Args:
            notes: Lista Dict z danymi notatek
            
        Returns:
            Lista Dict z wynikami synchronizacji
        """
        results = []
        errors = []
        
        logger.info(f"Starting batch sync for {len(notes)} notes")
        
        for note in notes:
            try:
                result = self.sync_note(note)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to sync note {note.get('local_id')}: {e}")
                errors.append({
                    "local_id": note.get("local_id"),
                    "error": str(e)
                })
        
        logger.info(f"Batch sync completed: {len(results)} success, {len(errors)} errors")
        
        if errors:
            logger.warning(f"Errors during batch sync: {errors}")
        
        return results
    
    def sync_links_batch(self, links: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Synchronizuje wiele linków w jednym wywołaniu
        
        Args:
            links: Lista Dict z danymi linków
            
        Returns:
            Lista Dict z wynikami synchronizacji
        """
        results = []
        errors = []
        
        logger.info(f"Starting batch sync for {len(links)} links")
        
        for link in links:
            try:
                result = self.sync_note_link(link)
                results.append(result)
            except Exception as e:
                logger.error(f"Failed to sync link {link.get('local_id')}: {e}")
                errors.append({
                    "local_id": link.get("local_id"),
                    "error": str(e)
                })
        
        logger.info(f"Batch sync completed: {len(results)} success, {len(errors)} errors")
        
        if errors:
            logger.warning(f"Errors during batch sync: {errors}")
        
        return results
    
    # =============================================================================
    # CONNECTION TEST
    # =============================================================================
    
    def test_connection(self) -> bool:
        """
        Testuje połączenie z API
        
        Returns:
            True jeśli połączenie działa, False w przeciwnym razie
        """
        try:
            # Próbujemy wywołać root endpoint (bez autoryzacji)
            # base_url = http://127.0.0.1:8000/api/v1/notes
            # Chcemy http://127.0.0.1:8000/
            parts = self.base_url.split('/')
            root_url = '/'.join(parts[:3])  # ['http:', '', '127.0.0.1:8000'] -> 'http://127.0.0.1:8000'
            response = self.session.get(root_url, timeout=5)
            response.raise_for_status()
            logger.info("API connection test successful")
            return True
        except Exception as e:
            logger.error(f"API connection test failed: {e}")
            return False
    
    def close(self):
        """Zamyka sesję HTTP"""
        self.session.close()
        logger.info("API client session closed")


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def create_api_client(
    user_id: Optional[str] = None, 
    auth_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    on_token_refreshed: Optional[Callable[[str, str], None]] = None
) -> NotesAPIClient:
    """
    Tworzy i konfiguruje klienta API
    
    Args:
        user_id: UUID użytkownika (opcjonalne, do loggingu)
        auth_token: JWT token autoryzacyjny
        refresh_token: Refresh token do odświeżania access tokena
        on_token_refreshed: Callback wywoływany po odświeżeniu tokena (access, refresh)
        
    Returns:
        Skonfigurowany NotesAPIClient
    """
    # Import lokalny aby uniknąć circular imports
    import os
    
    # Pobierz URL API z environment variable lub użyj domyślnego
    api_base_url = os.getenv('NOTES_API_URL', 'https://prokapo-server-render-1.onrender.com/api/v1/notes')
    
    client = NotesAPIClient(
        base_url=api_base_url, 
        auth_token=auth_token,
        refresh_token=refresh_token,
        on_token_refreshed=on_token_refreshed
    )
    
    logger.info(f"Created API client for user: {user_id or 'unknown'}")
    
    return client
