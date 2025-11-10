"""
API Client dla synchronizacji nagrań CallCryptor z serwerem.
=============================================================

PRIVACY-FIRST: Synchronizuje TYLKO metadane nagrań, NIE pliki audio!

Ten moduł odpowiada za komunikację HTTP z FastAPI backend.
Obsługuje:
- CRUD operacje na recording_sources, recordings, tags
- Bulk synchronizację (max 100 nagrań)
- Soft delete
- Rozwiązywanie konfliktów Last-Write-Wins
- Automatyczne odświeżanie tokena po wygaśnięciu
"""

import json
import requests
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from loguru import logger
from uuid import UUID


class APIResponse:
    """Wrapper dla odpowiedzi API"""
    
    def __init__(self, success: bool, data: Any = None, error: Optional[str] = None, status_code: Optional[int] = None):
        self.success = success
        self.data = data
        self.error = error
        self.status_code = status_code
    
    def __repr__(self) -> str:
        if self.success:
            return f"<APIResponse success=True status={self.status_code}>"
        return f"<APIResponse success=False error='{self.error}' status={self.status_code}>"


class ConflictError(Exception):
    """Wyjątek dla konfliktów wersji (Last-Write-Wins)"""
    
    def __init__(self, message: str, server_data: Dict[str, Any], local_version: int, server_version: int):
        super().__init__(message)
        self.server_data = server_data
        self.local_version = local_version
        self.server_version = server_version


class RecordingsAPIClient:
    """
    Klient API dla synchronizacji nagrań CallCryptor.
    
    UWAGA: Synchronizuje TYLKO metadane - pliki audio pozostają lokalne!
    
    Obsługuje komunikację z serwerem FastAPI, autentykację,
    oraz rozwiązywanie konfliktów wersji (Last-Write-Wins).
    """
    
    def __init__(
        self, 
        base_url: str, 
        auth_token: Optional[str] = None, 
        refresh_token: Optional[str] = None,
        on_token_refreshed: Optional[Callable[[str, str], None]] = None
    ):
        """
        Inicjalizacja API client.
        
        Args:
            base_url: URL serwera (np. "https://api.example.com")
            auth_token: Access token autentykacji (opcjonalnie)
            refresh_token: Refresh token do odświeżania access token (opcjonalnie)
            on_token_refreshed: Callback wywoływany po odświeżeniu tokena: (new_access_token, new_refresh_token) -> None
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.on_token_refreshed = on_token_refreshed
        self.session = requests.Session()
        self.timeout = 30  # 30 sekund (bulk sync może być wolniejszy)
        
        # Domyślne headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        if auth_token:
            self.session.headers['Authorization'] = f'Bearer {auth_token}'
        
        logger.info(f"[CallCryptor API] Client initialized with base_url: {base_url}")
    
    def set_auth_token(self, token: str):
        """Ustaw token autentykacji"""
        self.auth_token = token
        self.session.headers['Authorization'] = f'Bearer {token}'
        logger.debug("[CallCryptor API] Auth token updated")
    
    def _try_refresh_token(self) -> bool:
        """
        Spróbuj odświeżyć access token używając refresh token.
        
        Returns:
            True jeśli udało się odświeżyć, False w przeciwnym razie
        """
        if not self.refresh_token:
            logger.warning("[CallCryptor API] Cannot refresh token: no refresh_token available")
            return False
        
        try:
            # Użyj nowego session bez auth header
            response = requests.post(
                f"{self.base_url}/api/v1/auth/refresh",
                json={"refresh_token": self.refresh_token},
                headers={'Content-Type': 'application/json'},
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                new_access_token = data.get('access_token')
                
                if new_access_token:
                    self.set_auth_token(new_access_token)
                    
                    # Wywołaj callback jeśli istnieje
                    if self.on_token_refreshed:
                        self.on_token_refreshed(new_access_token, self.refresh_token)
                    
                    logger.success("[CallCryptor API] Access token refreshed successfully")
                    return True
            
            logger.error(f"[CallCryptor API] Token refresh failed: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Token refresh error: {e}")
            return False
    
    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Wykonaj request HTTP z automatycznym retry po 401 (odświeżenie tokena).
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE)
            url: Full URL
            **kwargs: Dodatkowe argumenty dla requests (json, params, etc.)
            
        Returns:
            Response object
        """
        # Pierwszy request
        response = self.session.request(method, url, **kwargs)
        
        # Jeśli 401 i mamy refresh_token, spróbuj odświeżyć
        if response.status_code == 401 and self.refresh_token:
            logger.info("[CallCryptor API] Got 401 Unauthorized, attempting token refresh...")
            
            if self._try_refresh_token():
                # Token odświeżony, retry request
                logger.info("[CallCryptor API] Token refreshed, retrying request...")
                response = self.session.request(method, url, **kwargs)
            else:
                logger.error("[CallCryptor API] Token refresh failed, returning 401 response")
        
        return response
    
    def _handle_response(self, response: requests.Response) -> APIResponse:
        """
        Obsłuż odpowiedź HTTP.
        
        Args:
            response: Odpowiedź requests
            
        Returns:
            APIResponse object
        """
        try:
            response.raise_for_status()
            data = response.json() if response.content else None
            return APIResponse(
                success=True,
                data=data,
                status_code=response.status_code
            )
        except requests.exceptions.HTTPError as e:
            error_message = str(e)
            try:
                error_data = response.json()
                error_message = error_data.get('detail', error_message)
            except:
                pass
            
            logger.error(f"[CallCryptor API] HTTP Error {response.status_code}: {error_message}")
            return APIResponse(
                success=False,
                error=error_message,
                status_code=response.status_code
            )
        except Exception as e:
            logger.error(f"[CallCryptor API] Unexpected error: {e}")
            return APIResponse(
                success=False,
                error=str(e),
                status_code=response.status_code if hasattr(response, 'status_code') else None
            )
    
    def _serialize_datetime(self, obj: Any) -> Any:
        """
        Konwertuj datetime na ISO string i parse JSON strings.
        
        UWAGA: To jest FALLBACK - normalnie JSON powinien być sparsowany
        w sync_manager przed wysłaniem tutaj.
        """
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, UUID):
            return str(obj)
        elif isinstance(obj, dict):
            # Recursively process dict, parsing JSON strings if needed
            result = {}
            for k, v in obj.items():
                # Special handling for known JSON fields
                if k in ('tags', 'ai_summary_tasks', 'ai_key_points', 'ai_action_items'):
                    result[k] = self._parse_json_field(v)
                else:
                    result[k] = self._serialize_datetime(v)
            return result
        elif isinstance(obj, list):
            return [self._serialize_datetime(item) for item in obj]
        return obj
    
    def _parse_json_field(self, value: Any) -> Any:
        """
        Parse JSON field if it's a string, otherwise return as-is.
        
        FALLBACK: Powinno być parsowane w sync_manager, ale to zapewnia bezpieczeństwo.
        """
        if value is None:
            return None
        
        # Already parsed
        if isinstance(value, (list, dict)):
            return value
        
        # Parse JSON string
        if isinstance(value, str):
            # Empty string or non-JSON
            if not value or value == 'null':
                return None
            
            try:
                return json.loads(value)
            except (json.JSONDecodeError, ValueError):
                logger.warning(f"[CallCryptor API] Failed to parse JSON field: {value[:50]}")
                return None
        
        return value
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    def health_check(self) -> APIResponse:
        """Sprawdź status serwera"""
        try:
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/recordings/health",
                timeout=5
            )
            return self._handle_response(response)
        except Exception as e:
            logger.error(f"[CallCryptor API] Health check error: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # RECORDING SOURCES
    # =========================================================================
    
    def create_source(self, source_data: Dict[str, Any]) -> APIResponse:
        """
        Utwórz nowe źródło nagrań.
        
        Args:
            source_data: Dane źródła (bez user_id - dodawane automatycznie z tokena)
            
        Returns:
            APIResponse z utworzonym źródłem
        """
        try:
            payload = self._serialize_datetime(source_data)
            
            logger.debug(f"[CallCryptor API] Creating source: {payload.get('source_name')}")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/recordings/sources",
                json=payload,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error creating source: {e}")
            return APIResponse(success=False, error=str(e))
    
    def list_sources(self, include_deleted: bool = False) -> APIResponse:
        """
        Pobierz listę źródeł nagrań.
        
        Args:
            include_deleted: Czy dołączyć usunięte źródła (soft-deleted)
            
        Returns:
            APIResponse z listą źródeł
        """
        try:
            params = {'include_deleted': include_deleted}
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/recordings/sources",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error listing sources: {e}")
            return APIResponse(success=False, error=str(e))
    
    def update_source(self, source_id: str, updates: Dict[str, Any]) -> APIResponse:
        """
        Zaktualizuj źródło nagrań.
        
        Args:
            source_id: UUID źródła
            updates: Dane do aktualizacji
            
        Returns:
            APIResponse z zaktualizowanym źródłem
        """
        try:
            payload = self._serialize_datetime(updates)
            
            response = self._request_with_retry(
                'PUT',
                f"{self.base_url}/api/recordings/sources/{source_id}",
                json=payload,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error updating source: {e}")
            return APIResponse(success=False, error=str(e))
    
    def delete_source(self, source_id: str, hard_delete: bool = False) -> APIResponse:
        """
        Usuń źródło nagrań.
        
        Args:
            source_id: UUID źródła
            hard_delete: True = trwałe usunięcie, False = soft delete
            
        Returns:
            APIResponse z wynikiem usunięcia
        """
        try:
            params = {'hard_delete': hard_delete}
            
            response = self._request_with_retry(
                'DELETE',
                f"{self.base_url}/api/recordings/sources/{source_id}",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error deleting source: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # RECORDINGS
    # =========================================================================
    
    def create_recording(self, recording_data: Dict[str, Any]) -> APIResponse:
        """
        Utwórz nowe nagranie (TYLKO metadane, bez pliku audio!).
        
        Args:
            recording_data: Dane nagrania (bez user_id)
            
        Returns:
            APIResponse z utworzonym nagraniem
        """
        try:
            payload = self._serialize_datetime(recording_data)
            
            logger.debug(f"[CallCryptor API] Creating recording: {payload.get('file_name')}")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/recordings/",
                json=payload,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error creating recording: {e}")
            return APIResponse(success=False, error=str(e))
    
    def list_recordings(
        self, 
        source_id: Optional[str] = None,
        include_deleted: bool = False,
        limit: int = 100,
        offset: int = 0
    ) -> APIResponse:
        """
        Pobierz listę nagrań.
        
        Args:
            source_id: Filtruj po źródle (opcjonalnie)
            include_deleted: Czy dołączyć usunięte nagrania
            limit: Maksymalna liczba wyników (max 1000)
            offset: Przesunięcie dla paginacji
            
        Returns:
            APIResponse z listą nagrań
        """
        try:
            params = {
                'include_deleted': include_deleted,
                'limit': min(limit, 1000),
                'offset': offset
            }
            if source_id:
                params['source_id'] = source_id
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/recordings/",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error listing recordings: {e}")
            return APIResponse(success=False, error=str(e))
    
    def get_recording(self, recording_id: str) -> APIResponse:
        """
        Pobierz pojedyncze nagranie.
        
        Args:
            recording_id: UUID nagrania
            
        Returns:
            APIResponse z nagraniem
        """
        try:
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/recordings/{recording_id}",
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error getting recording: {e}")
            return APIResponse(success=False, error=str(e))
    
    def update_recording(self, recording_id: str, updates: Dict[str, Any]) -> APIResponse:
        """
        Zaktualizuj nagranie.
        
        Args:
            recording_id: UUID nagrania
            updates: Dane do aktualizacji
            
        Returns:
            APIResponse z zaktualizowanym nagraniem
        """
        try:
            payload = self._serialize_datetime(updates)
            
            response = self._request_with_retry(
                'PUT',
                f"{self.base_url}/api/recordings/{recording_id}",
                json=payload,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error updating recording: {e}")
            return APIResponse(success=False, error=str(e))
    
    def delete_recording(self, recording_id: str, hard_delete: bool = False) -> APIResponse:
        """
        Usuń nagranie.
        
        Args:
            recording_id: UUID nagrania
            hard_delete: True = trwałe usunięcie, False = soft delete
            
        Returns:
            APIResponse z wynikiem usunięcia
        """
        try:
            params = {'hard_delete': hard_delete}
            
            response = self._request_with_retry(
                'DELETE',
                f"{self.base_url}/api/recordings/{recording_id}",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error deleting recording: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # BULK SYNC
    # =========================================================================
    
    def bulk_sync(
        self,
        recordings: List[Dict[str, Any]],
        sources: Optional[List[Dict[str, Any]]] = None,
        tags: Optional[List[Dict[str, Any]]] = None,
        last_sync_at: Optional[datetime] = None
    ) -> APIResponse:
        """
        Bulk synchronizacja nagrań (max 100 naraz).
        
        Last-Write-Wins conflict resolution:
        - Porównuje updated_at timestamps
        - Nowszy rekord wygrywa
        
        Args:
            recordings: Lista nagrań do synchronizacji (max 100)
            sources: Lista źródeł do synchronizacji (opcjonalnie)
            tags: Lista tagów do synchronizacji (opcjonalnie)
            last_sync_at: Timestamp ostatniej synchronizacji (opcjonalnie)
            
        Returns:
            APIResponse z wynikami synchronizacji i danymi z serwera
        """
        try:
            if len(recordings) > 100:
                return APIResponse(
                    success=False,
                    error="Cannot sync more than 100 recordings at once"
                )
            
            payload = {
                'recordings': [self._serialize_datetime(r) for r in recordings],
                'sources': [self._serialize_datetime(s) for s in sources] if sources else [],
                'tags': [self._serialize_datetime(t) for t in tags] if tags else [],
                'last_sync_at': last_sync_at.isoformat() if last_sync_at else None
            }
            
            logger.info(f"[CallCryptor API] Bulk sync: {len(recordings)} recordings, {len(sources or [])} sources, {len(tags or [])} tags")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/recordings/bulk-sync",
                json=payload,
                timeout=60  # Bulk sync może trwać dłużej
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error during bulk sync: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # SYNC STATS
    # =========================================================================
    
    def get_sync_stats(self) -> APIResponse:
        """
        Pobierz statystyki synchronizacji.
        
        Returns:
            APIResponse ze statystykami
        """
        try:
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/recordings/sync/stats",
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"[CallCryptor API] Error getting sync stats: {e}")
            return APIResponse(success=False, error=str(e))
