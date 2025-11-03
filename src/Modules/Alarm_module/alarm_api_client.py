"""
API Client dla synchronizacji alarmów i timerów z serwerem.

Ten moduł odpowiada za komunikację HTTP z FastAPI backend.
Obsługuje:
- Upsert (create/update) alarmów i timerów
- Pobieranie danych z serwera
- Soft delete
- Bulk synchronizację
- Rozwiązywanie konfliktów wersji
- Automatyczne odświeżanie tokena po wygaśnięciu
"""

import requests
from typing import Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime
from loguru import logger
from dataclasses import asdict

from .alarm_models import Alarm, Timer


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


class AlarmsAPIClient:
    """
    Klient API dla synchronizacji alarmów i timerów.
    
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
        
        logger.info(f"AlarmsAPIClient initialized with base_url: {base_url}")
    
    def set_auth_token(self, token: str):
        """Ustaw token autentykacji"""
        self.auth_token = token
        self.session.headers['Authorization'] = f'Bearer {token}'
        logger.debug("Auth token updated")
    
    def _try_refresh_token(self) -> bool:
        """
        Spróbuj odświeżyć access token używając refresh token.
        
        Returns:
            True jeśli udało się odświeżyć, False w przeciwnym razie
        """
        if not self.refresh_token:
            logger.warning("Cannot refresh token: no refresh_token available")
            return False
        
        try:
            # Użyj nowego session bez auth header (refresh endpoint nie wymaga auth)
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
                    # Update token
                    self.set_auth_token(new_access_token)
                    
                    # Wywołaj callback jeśli istnieje
                    if self.on_token_refreshed:
                        self.on_token_refreshed(new_access_token, self.refresh_token)
                    
                    logger.success("Access token refreshed successfully")
                    return True
            
            logger.error(f"Token refresh failed: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"Token refresh error: {e}")
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
        # Pierwszy request
        response = self.session.request(method, url, **kwargs)
        
        # Jeśli 401 i mamy refresh_token, spróbuj odświeżyć
        if response.status_code == 401 and self.refresh_token:
            logger.info("Got 401 Unauthorized, attempting token refresh...")
            
            if self._try_refresh_token():
                # Token odświeżony, retry request
                logger.info("Token refreshed, retrying request...")
                response = self.session.request(method, url, **kwargs)
            else:
                logger.error("Token refresh failed, returning 401 response")
        
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
            
            logger.error(f"HTTP Error {response.status_code}: {error_message}")
            return APIResponse(
                success=False,
                error=error_message,
                status_code=response.status_code
            )
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return APIResponse(
                success=False,
                error=str(e),
                status_code=response.status_code if hasattr(response, 'status_code') else None
            )
    
    # =========================================================================
    # OPERACJE UPSERT (CREATE/UPDATE)
    # =========================================================================
    
    def sync_alarm(self, alarm_data: Dict[str, Any], user_id: str) -> APIResponse:
        """
        Synchronizuj alarm z serwerem (upsert).
        
        Args:
            alarm_data: Dane alarmu (dict z Alarm.to_dict())
            user_id: ID użytkownika
            
        Returns:
            APIResponse z danymi z serwera
            
        Raises:
            ConflictError: Jeśli wersja na serwerze jest nowsza
        """
        try:
            payload = {
                **alarm_data,
                'user_id': user_id,
                'type': 'alarm'
            }
            
            # Konwersja datetime do ISO string
            if 'created_at' in payload and isinstance(payload['created_at'], datetime):
                payload['created_at'] = payload['created_at'].isoformat()
            
            logger.debug(f"Syncing alarm {alarm_data.get('id')} to server")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/alarms-timers",
                json=payload,
                timeout=self.timeout
            )
            
            # Sprawdź konflikt wersji (409 Conflict)
            if response.status_code == 409:
                response_data = response.json()
                # Detail może być słownikiem lub stringiem
                detail = response_data.get('detail', {})
                if isinstance(detail, str):
                    # Jeśli detail to string, nie mamy server_data
                    raise ConflictError(
                        detail,
                        server_data={},
                        local_version=alarm_data.get('version', 1),
                        server_version=1
                    )
                else:
                    # Detail to słownik z danymi konfliktu
                    raise ConflictError(
                        detail.get('detail', 'Version conflict detected'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', alarm_data.get('version', 1)),
                        server_version=detail.get('server_version', 1)
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error syncing alarm: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error syncing alarm: {e}")
            return APIResponse(success=False, error=str(e))
    
    def sync_timer(self, timer_data: Dict[str, Any], user_id: str) -> APIResponse:
        """
        Synchronizuj timer z serwerem (upsert).
        
        Args:
            timer_data: Dane timera (dict z Timer.to_dict())
            user_id: ID użytkownika
            
        Returns:
            APIResponse z danymi z serwera
            
        Raises:
            ConflictError: Jeśli wersja na serwerze jest nowsza
        """
        try:
            payload = {
                **timer_data,
                'user_id': user_id,
                'type': 'timer'
            }
            
            # Konwersja datetime do ISO string
            for field in ['created_at', 'started_at']:
                if field in payload and isinstance(payload[field], datetime):
                    payload[field] = payload[field].isoformat()
            
            logger.debug(f"Syncing timer {timer_data.get('id')} to server")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/alarms-timers",
                json=payload,
                timeout=self.timeout
            )
            
            # Sprawdź konflikt wersji (409 Conflict)
            if response.status_code == 409:
                response_data = response.json()
                # Detail może być słownikiem lub stringiem
                detail = response_data.get('detail', {})
                if isinstance(detail, str):
                    # Jeśli detail to string, nie mamy server_data
                    raise ConflictError(
                        detail,
                        server_data={},
                        local_version=timer_data.get('version', 1),
                        server_version=1
                    )
                else:
                    # Detail to słownik z danymi konfliktu
                    raise ConflictError(
                        detail.get('detail', 'Version conflict detected'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', timer_data.get('version', 1)),
                        server_version=detail.get('server_version', 1)
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error syncing timer: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error syncing timer: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # OPERACJE POBIERANIA (READ)
    # =========================================================================
    
    def fetch_all(self, user_id: str, item_type: Optional[str] = None) -> APIResponse:
        """
        Pobierz wszystkie alarmy/timery użytkownika z serwera.
        
        Args:
            user_id: ID użytkownika
            item_type: Typ ('alarm', 'timer' lub None dla wszystkich)
            
        Returns:
            APIResponse z listą items
        """
        try:
            params = {'user_id': user_id}
            if item_type:
                params['type'] = item_type
            
            logger.debug(f"Fetching items for user {user_id}, type={item_type}")
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/alarms-timers",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching items: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching items: {e}")
            return APIResponse(success=False, error=str(e))
    
    def fetch_item(self, item_id: str) -> APIResponse:
        """
        Pobierz konkretny alarm/timer z serwera.
        
        Args:
            item_id: ID alarmu/timera
            
        Returns:
            APIResponse z danymi item
        """
        try:
            logger.debug(f"Fetching item {item_id}")
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/alarms-timers/{item_id}",
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching item: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching item: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # OPERACJE USUWANIA (DELETE)
    # =========================================================================
    
    def delete_item(self, item_id: str, soft: bool = True) -> APIResponse:
        """
        Usuń alarm/timer na serwerze.
        
        Args:
            item_id: ID alarmu/timera
            soft: Czy soft delete (domyślnie True)
            
        Returns:
            APIResponse
        """
        try:
            params = {'soft': 'true' if soft else 'false'}
            
            logger.debug(f"Deleting item {item_id}, soft={soft}")
            
            response = self._request_with_retry(
                'DELETE',
                f"{self.base_url}/api/alarms-timers/{item_id}",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error deleting item: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting item: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # BULK SYNCHRONIZACJA
    # =========================================================================
    
    def bulk_sync(self, items: List[Dict[str, Any]], user_id: str) -> APIResponse:
        """
        Synchronizuj wiele elementów w jednym request.
        
        Args:
            items: Lista słowników z danymi alarmów/timerów
            user_id: ID użytkownika
            
        Returns:
            APIResponse z listą wyników
        """
        try:
            payload = {
                'user_id': user_id,
                'items': items
            }
            
            logger.debug(f"Bulk syncing {len(items)} items")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/alarms-timers/bulk",
                json=payload,
                timeout=self.timeout * 2  # Dłuższy timeout dla bulk
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error in bulk sync: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error in bulk sync: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # ROZWIĄZYWANIE KONFLIKTÓW
    # =========================================================================
    
    def resolve_conflict(
        self, 
        local_data: Dict[str, Any], 
        server_data: Dict[str, Any],
        strategy: str = 'last_write_wins'
    ) -> Tuple[Dict[str, Any], str]:
        """
        Rozwiąż konflikt między lokalną a serwerową wersją.
        
        Args:
            local_data: Lokalne dane
            server_data: Dane z serwera
            strategy: Strategia ('last_write_wins', 'server_wins', 'local_wins')
            
        Returns:
            Tuple (winning_data, winner) - ('local' lub 'server')
        """
        if strategy == 'server_wins':
            logger.debug("Conflict resolved: server wins")
            return server_data, 'server'
        
        elif strategy == 'local_wins':
            logger.debug("Conflict resolved: local wins")
            return local_data, 'local'
        
        else:  # last_write_wins (default)
            local_updated = local_data.get('updated_at')
            server_updated = server_data.get('updated_at')
            
            if not local_updated:
                logger.debug("Conflict resolved: server wins (no local updated_at)")
                return server_data, 'server'
            
            if not server_updated:
                logger.debug("Conflict resolved: local wins (no server updated_at)")
                return local_data, 'local'
            
            # Konwertuj do datetime jeśli string
            if isinstance(local_updated, str):
                local_updated = datetime.fromisoformat(local_updated)
            if isinstance(server_updated, str):
                server_updated = datetime.fromisoformat(server_updated)
            
            if server_updated > local_updated:
                logger.debug(f"Conflict resolved: server wins (newer timestamp)")
                return server_data, 'server'
            else:
                logger.debug(f"Conflict resolved: local wins (newer timestamp)")
                return local_data, 'local'
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    def health_check(self) -> bool:
        """
        Sprawdź czy serwer jest dostępny.
        
        Returns:
            True jeśli serwer odpowiada
        """
        try:
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/health",
                timeout=3
            )
            is_healthy = response.status_code == 200
            logger.debug(f"Health check: {'OK' if is_healthy else 'FAILED'}")
            return is_healthy
            
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False
    
    def close(self):
        """Zamknij session"""
        self.session.close()
        logger.debug("API client session closed")


# =========================================================================
# FUNKCJE POMOCNICZE
# =========================================================================

def create_api_client(
    base_url: Optional[str] = None,
    auth_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    on_token_refreshed: Optional[Callable[[str, str], None]] = None
) -> AlarmsAPIClient:
    """
    Factory function dla tworzenia API client.
    
    Args:
        base_url: URL serwera (jeśli None, użyje domyślnego z config)
        auth_token: Access token autentykacji
        refresh_token: Refresh token do odświeżania access token
        on_token_refreshed: Callback wywoływany po odświeżeniu tokena: (new_access_token, new_refresh_token) -> None
        
    Returns:
        Skonfigurowany AlarmsAPIClient
    """
    # TODO: Pobierz base_url z config jeśli nie podano
    if base_url is None:
        # z pliku config lub environment variable
        base_url = "http://localhost:8000"  # Placeholder
    
    return AlarmsAPIClient(
        base_url=base_url, 
        auth_token=auth_token,
        refresh_token=refresh_token,
        on_token_refreshed=on_token_refreshed
    )


def is_network_available() -> bool:
    """
    Sprawdź czy jest dostęp do sieci.
    
    Returns:
        True jeśli sieć jest dostępna
    """
    try:
        # Ping Google DNS
        response = requests.get("http://1.1.1.1", timeout=2)
        return True
    except:
        return False
