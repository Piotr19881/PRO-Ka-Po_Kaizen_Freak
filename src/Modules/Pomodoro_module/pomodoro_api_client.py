"""
API Client dla synchronizacji sesji Pomodoro z serwerem.

Ten moduł odpowiada za komunikację HTTP z FastAPI backend.
Obsługuje:
- Upsert (create/update) tematów i sesji Pomodoro
- Pobieranie danych z serwera
- Soft delete
- Bulk synchronizację
- Rozwiązywanie konfliktów wersji
- Automatyczne odświeżanie tokena po wygaśnięciu
"""

import requests
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from loguru import logger

from .pomodoro_models import PomodoroTopic, PomodoroSession


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
    """Wyjątek dla konfliktów wersji"""
    
    def __init__(self, message: str, server_data: Dict[str, Any], local_version: int, server_version: int):
        super().__init__(message)
        self.server_data = server_data
        self.local_version = local_version
        self.server_version = server_version


class PomodoroAPIClient:
    """
    Klient API dla synchronizacji sesji Pomodoro.
    
    Obsługuje komunikację z serwerem FastAPI, autentykację,
    oraz rozwiązywanie konfliktów wersji.
    """
    
    def __init__(self, base_url: str, auth_token: Optional[str] = None, refresh_token: Optional[str] = None, on_token_refreshed: Optional[Callable[[str, str], None]] = None):
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
        self.timeout = 10  # sekundy
        
        # Domyślne headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        if auth_token:
            self.session.headers['Authorization'] = f'Bearer {auth_token}'
        
        logger.info(f"[POMODORO] API Client initialized with base_url: {base_url}")
    
    def set_auth_token(self, token: str):
        """Ustaw token autentykacji"""
        self.auth_token = token
        self.session.headers['Authorization'] = f'Bearer {token}'
        logger.debug("[POMODORO] Auth token updated")
    
    def _try_refresh_token(self) -> bool:
        """
        Spróbuj odświeżyć access token używając refresh token.
        
        Returns:
            True jeśli udało się odświeżyć, False w przeciwnym razie
        """
        if not self.refresh_token:
            logger.warning("[POMODORO] Cannot refresh token: no refresh_token available")
            return False
        
        try:
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
                    
                    if self.on_token_refreshed:
                        self.on_token_refreshed(new_access_token, self.refresh_token)
                    
                    logger.success("[POMODORO] Access token refreshed successfully")
                    return True
            
            logger.error(f"[POMODORO] Token refresh failed: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"[POMODORO] Token refresh error: {e}")
            return False
    
    def _request_with_retry(self, method: str, url: str, **kwargs) -> requests.Response:
        """
        Wykonaj request HTTP z automatycznym retry po 401 (odświeżenie tokena).
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            url: Full URL
            **kwargs: Dodatkowe argumenty dla requests (json, params, etc.)
            
        Returns:
            Response object
        """
        response = self.session.request(method, url, **kwargs)
        
        if response.status_code == 401 and self.refresh_token:
            logger.info("[POMODORO] Got 401 Unauthorized, attempting token refresh...")
            
            if self._try_refresh_token():
                logger.info("[POMODORO] Token refreshed, retrying request...")
                response = self.session.request(method, url, **kwargs)
            else:
                logger.error("[POMODORO] Token refresh failed, returning 401 response")
        
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
            
            logger.error(f"[POMODORO] HTTP Error {response.status_code}: {error_message}")
            return APIResponse(
                success=False,
                error=error_message,
                status_code=response.status_code
            )
        except Exception as e:
            logger.error(f"[POMODORO] Unexpected error: {e}")
            return APIResponse(
                success=False,
                error=str(e),
                status_code=response.status_code if hasattr(response, 'status_code') else None
            )
    
    # =========================================================================
    # OPERACJE TOPICS (TEMATY SESJI)
    # =========================================================================
    
    def sync_topic(self, topic_data: Dict[str, Any], user_id: str) -> APIResponse:
        """
        Synchronizuj temat sesji z serwerem (upsert).
        
        Args:
            topic_data: Dane tematu (dict z PomodoroTopic.to_dict())
            user_id: ID użytkownika
            
        Returns:
            APIResponse z danymi z serwera
            
        Raises:
            ConflictError: Jeśli wersja na serwerze jest nowsza
        """
        try:
            payload = {
                **topic_data,
                'user_id': user_id
            }
            
            # Konwersja datetime do ISO string
            for field in ['created_at', 'updated_at', 'deleted_at']:
                if field in payload and payload[field] and isinstance(payload[field], datetime):
                    payload[field] = payload[field].isoformat()
            
            logger.debug(f"[POMODORO] Syncing topic {topic_data.get('id')} to server")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/pomodoro/topics",
                json=payload,
                timeout=self.timeout
            )
            
            # Sprawdź konflikt wersji (409 Conflict)
            if response.status_code == 409:
                response_data = response.json()
                detail = response_data.get('detail', {})
                
                if isinstance(detail, str):
                    raise ConflictError(
                        detail,
                        server_data={},
                        local_version=topic_data.get('version', 1),
                        server_version=1
                    )
                else:
                    raise ConflictError(
                        detail.get('detail', 'Version conflict detected'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', topic_data.get('version', 1)),
                        server_version=detail.get('server_version', 1)
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"[POMODORO] Network error syncing topic: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"[POMODORO] Error syncing topic: {e}")
            return APIResponse(success=False, error=str(e))
    
    def sync_session(self, session_data: Dict[str, Any], user_id: str) -> APIResponse:
        """
        Synchronizuj sesję Pomodoro z serwerem (upsert).
        
        Args:
            session_data: Dane sesji (dict z PomodoroSession.to_dict())
            user_id: ID użytkownika
            
        Returns:
            APIResponse z danymi z serwera
            
        Raises:
            ConflictError: Jeśli wersja na serwerze jest nowsza
        """
        try:
            payload = {
                **session_data,
                'user_id': user_id
            }
            
            # Konwersja datetime do ISO string
            for field in ['session_date', 'started_at', 'ended_at', 'created_at', 'updated_at', 'deleted_at', 'synced_at']:
                if field in payload and payload[field]:
                    if isinstance(payload[field], datetime):
                        payload[field] = payload[field].isoformat()
            
            logger.debug(f"[POMODORO] Syncing session {session_data.get('id')} to server")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/pomodoro/sessions",
                json=payload,
                timeout=self.timeout
            )
            
            # Sprawdź konflikt wersji (409 Conflict)
            if response.status_code == 409:
                response_data = response.json()
                detail = response_data.get('detail', {})
                
                if isinstance(detail, str):
                    raise ConflictError(
                        detail,
                        server_data={},
                        local_version=session_data.get('version', 1),
                        server_version=1
                    )
                else:
                    raise ConflictError(
                        detail.get('detail', 'Version conflict detected'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', session_data.get('version', 1)),
                        server_version=detail.get('server_version', 1)
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"[POMODORO] Network error syncing session: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"[POMODORO] Error syncing session: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # OPERACJE POBIERANIA (READ)
    # =========================================================================
    
    def fetch_all(self, user_id: str, item_type: Optional[str] = None) -> APIResponse:
        """
        Pobierz wszystkie dane Pomodoro użytkownika z serwera.
        
        Args:
            user_id: ID użytkownika
            item_type: Typ ('topic', 'session' lub None dla wszystkich)
            
        Returns:
            APIResponse z listą danych
        """
        try:
            params = {}
            if item_type:
                params['type'] = item_type
            
            logger.debug(f"[POMODORO] Fetching all data for user {user_id}, type={item_type}")
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/pomodoro/all",
                params=params if params else None,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[POMODORO] Network error fetching data: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"[POMODORO] Error fetching data: {e}")
            return APIResponse(success=False, error=str(e))
    
    def fetch_topics(self, user_id: str) -> APIResponse:
        """Pobierz wszystkie tematy sesji użytkownika"""
        return self.fetch_all(user_id, item_type='topic')
    
    def fetch_sessions(self, user_id: str) -> APIResponse:
        """Pobierz wszystkie sesje użytkownika"""
        return self.fetch_all(user_id, item_type='session')
    
    # =========================================================================
    # OPERACJE USUWANIA (DELETE - SOFT DELETE)
    # =========================================================================
    
    def delete_topic(self, topic_id: str, user_id: str, version: int) -> APIResponse:
        """
        Soft delete tematu sesji.
        
        Args:
            topic_id: ID tematu
            user_id: ID użytkownika
            version: Aktualna wersja (do kontroli konfliktów)
            
        Returns:
            APIResponse
            
        Raises:
            ConflictError: Jeśli wersja na serwerze jest inna
        """
        try:
            logger.debug(f"[POMODORO] Deleting topic {topic_id} (version {version})")
            
            response = self._request_with_retry(
                'DELETE',
                f"{self.base_url}/api/pomodoro/topics/{topic_id}",
                params={'user_id': user_id, 'version': version},
                timeout=self.timeout
            )
            
            if response.status_code == 409:
                response_data = response.json()
                detail = response_data.get('detail', {})
                
                if isinstance(detail, str):
                    raise ConflictError(
                        detail,
                        server_data={},
                        local_version=version,
                        server_version=version + 1
                    )
                else:
                    raise ConflictError(
                        detail.get('detail', 'Version conflict detected'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', version),
                        server_version=detail.get('server_version', version + 1)
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"[POMODORO] Network error deleting topic: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"[POMODORO] Error deleting topic: {e}")
            return APIResponse(success=False, error=str(e))
    
    def delete_session(self, session_id: str, user_id: str, version: int) -> APIResponse:
        """
        Soft delete sesji Pomodoro.
        
        Args:
            session_id: ID sesji
            user_id: ID użytkownika
            version: Aktualna wersja (do kontroli konfliktów)
            
        Returns:
            APIResponse
            
        Raises:
            ConflictError: Jeśli wersja na serwerze jest inna
        """
        try:
            logger.debug(f"[POMODORO] Deleting session {session_id} (version {version})")
            
            response = self._request_with_retry(
                'DELETE',
                f"{self.base_url}/api/pomodoro/sessions/{session_id}",
                params={'user_id': user_id, 'version': version},
                timeout=self.timeout
            )
            
            if response.status_code == 409:
                response_data = response.json()
                detail = response_data.get('detail', {})
                
                if isinstance(detail, str):
                    raise ConflictError(
                        detail,
                        server_data={},
                        local_version=version,
                        server_version=version + 1
                    )
                else:
                    raise ConflictError(
                        detail.get('detail', 'Version conflict detected'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', version),
                        server_version=detail.get('server_version', version + 1)
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"[POMODORO] Network error deleting session: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"[POMODORO] Error deleting session: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # BULK OPERATIONS
    # =========================================================================
    
    def bulk_sync(self, topics: List[Dict[str, Any]], sessions: List[Dict[str, Any]], user_id: str) -> APIResponse:
        """
        Synchronizuj wiele elementów naraz (bulk operation).
        
        Args:
            topics: Lista danych tematów
            sessions: Lista danych sesji
            user_id: ID użytkownika
            
        Returns:
            APIResponse z wynikami synchronizacji
        """
        try:
            payload = {
                'user_id': user_id,
                'topics': topics,
                'sessions': sessions
            }
            
            # Konwersja datetime dla wszystkich elementów
            for topic in payload['topics']:
                for field in ['created_at', 'updated_at', 'deleted_at']:
                    if field in topic and topic[field] and isinstance(topic[field], datetime):
                        topic[field] = topic[field].isoformat()
            
            for session in payload['sessions']:
                for field in ['session_date', 'started_at', 'ended_at', 'created_at', 'updated_at', 'deleted_at', 'synced_at']:
                    if field in session and session[field] and isinstance(session[field], datetime):
                        session[field] = session[field].isoformat()
            
            logger.debug(f"[POMODORO] Bulk sync: {len(topics)} topics, {len(sessions)} sessions")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/pomodoro/bulk-sync",
                json=payload,
                timeout=self.timeout * 3  # Dłuższy timeout dla bulk operations
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"[POMODORO] Network error in bulk sync: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"[POMODORO] Error in bulk sync: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    def health_check(self) -> bool:
        """
        Sprawdź połączenie z serwerem.
        
        Returns:
            True jeśli serwer odpowiada, False w przeciwnym razie
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5
            )
            return response.status_code == 200
        except:
            return False
