"""
API Client dla synchronizacji habit trackera z serwerem.

Ten moduł odpowiada za komunikację HTTP z FastAPI backend.
Obsługuje:
- CRUD operacje dla kolumn i rekordów habit trackera
- Bulk synchronizację
- Pobieranie miesięcznych danych
- Rozwiązywanie konfliktów wersji
- Automatyczne odświeżanie tokena po wygaśnięciu
"""

import requests
from typing import Optional, List, Dict, Any, Tuple, Callable
from datetime import datetime, date
from loguru import logger
import json


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


class HabitAPIClient:
    """
    Klient API dla synchronizacji habit trackera.
    
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
        
        logger.info(f"HabitAPIClient initialized with base_url: {base_url}")
    
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
    # OPERACJE KOLUMN HABIT TRACKERA
    # =========================================================================
    
    def sync_habit_column(self, column_data: Dict[str, Any], user_id: str) -> APIResponse:
        """
        Synchronizuj kolumnę habit trackera z serwerem (upsert).
        
        Args:
            column_data: Dane kolumny (dict z habit_column)
            user_id: ID użytkownika
            
        Returns:
            APIResponse z danymi z serwera
            
        Raises:
            ConflictError: Jeśli wersja na serwerze jest nowsza
        """
        try:
            # Mapowanie habit_type (polski -> angielski) dla API
            type_mapping = {
                'Checkbox': 'checkbox',
                'Licznik': 'counter',
                'Skala': 'scale',
                'Czas trwania': 'duration',
                'Tekst': 'text',
                'time': 'time',  # już angielskie
                'scale': 'scale',
                'checkbox': 'checkbox',
                'counter': 'counter',
                'duration': 'duration',
                'text': 'text'
            }
            
            # Przygotuj payload z transformacją pól
            payload = {
                'id': column_data.get('id'),
                'name': column_data.get('name'),
                'type': type_mapping.get(column_data.get('habit_type'), 'text'),  # habit_type -> type
                'scale_max': column_data.get('scale_max') or 10,  # None -> 10 dla scale
                'version': column_data.get('version', 1),
                'user_id': user_id
            }
            
            # Konwersja datetime do ISO string
            for field in ['created_at', 'updated_at']:
                if field in column_data and isinstance(column_data[field], datetime):
                    payload[field] = column_data[field].isoformat()
                elif field in column_data:
                    payload[field] = column_data[field]
            
            logger.debug(f"Syncing habit column {column_data.get('id')} to server")
            logger.debug(f"📤 [HABIT API] Payload for column: {payload}")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/habits/columns",
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
                        local_version=column_data.get('version', 1),
                        server_version=1
                    )
                else:
                    raise ConflictError(
                        detail.get('detail', 'Version conflict detected'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', column_data.get('version', 1)),
                        server_version=detail.get('server_version', 1)
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error syncing habit column: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error syncing habit column: {e}")
            return APIResponse(success=False, error=str(e))
    
    def sync_habit_record(self, record_data: Dict[str, Any], user_id: str) -> APIResponse:
        """
        Synchronizuj rekord habit trackera z serwerem (upsert).
        
        Args:
            record_data: Dane rekordu (dict z habit_record)
            user_id: ID użytkownika
            
        Returns:
            APIResponse z danymi z serwera
            
        Raises:
            ConflictError: Jeśli wersja na serwerze jest nowsza
        """
        try:
            # Przygotuj payload z transformacją pól (column_id -> habit_id, record_date -> date)
            payload = {
                'id': record_data.get('id'),
                'habit_id': record_data.get('column_id'),  # column_id -> habit_id
                'date': record_data.get('record_date'),    # record_date -> date
                'value': record_data.get('value'),
                'notes': record_data.get('notes', ''),
                'version': record_data.get('version', 1),
                'user_id': user_id
            }
            
            # Konwersja datetime/date do ISO string
            for field in ['created_at', 'updated_at']:
                if field in record_data and isinstance(record_data[field], datetime):
                    payload[field] = record_data[field].isoformat()
                elif field in record_data:
                    payload[field] = record_data[field]
            
            if isinstance(payload['date'], date):
                payload['date'] = payload['date'].isoformat()
            elif isinstance(payload['date'], str) and payload['date']:
                # Już string, pozostaw bez zmian
                pass
            
            logger.debug(f"Syncing habit record {record_data.get('id')} to server")
            logger.debug(f"📤 [HABIT API] Payload for record: {payload}")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/habits/records",
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
                        local_version=record_data.get('version', 1),
                        server_version=1
                    )
                else:
                    raise ConflictError(
                        detail.get('detail', 'Version conflict detected'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', record_data.get('version', 1)),
                        server_version=detail.get('server_version', 1)
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error syncing habit record: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error syncing habit record: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # OPERACJE POBIERANIA DANYCH
    # =========================================================================
    
    def fetch_habit_columns(self, user_id: str) -> APIResponse:
        """
        Pobierz wszystkie kolumny habit trackera użytkownika z serwera.
        
        Args:
            user_id: ID użytkownika
            
        Returns:
            APIResponse z listą kolumn
        """
        try:
            params = {'user_id': user_id}
            
            logger.debug(f"Fetching habit columns for user {user_id}")
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/habits/columns",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching habit columns: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching habit columns: {e}")
            return APIResponse(success=False, error=str(e))
    
    def fetch_habit_records(self, user_id: str, year: Optional[int] = None, month: Optional[int] = None) -> APIResponse:
        """
        Pobierz rekordy habit trackera użytkownika z serwera.
        
        Args:
            user_id: ID użytkownika
            year: Rok (opcjonalnie)
            month: Miesiąc (opcjonalnie)
            
        Returns:
            APIResponse z listą rekordów
        """
        try:
            params = {'user_id': user_id}
            if year is not None:
                params['year'] = year
            if month is not None:
                params['month'] = month
            
            logger.debug(f"Fetching habit records for user {user_id}, year={year}, month={month}")
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/habits/records",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching habit records: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching habit records: {e}")
            return APIResponse(success=False, error=str(e))
    
    def fetch_monthly_data(self, user_id: str, year: int, month: int) -> APIResponse:
        """
        Pobierz miesięczne dane habit trackera (kolumny + rekordy).
        
        Args:
            user_id: ID użytkownika
            year: Rok
            month: Miesiąc
            
        Returns:
            APIResponse z danymi miesięcznymi
        """
        try:
            params = {
                'user_id': user_id,
                'year': year,
                'month': month
            }
            
            logger.debug(f"Fetching monthly habit data for user {user_id}, {year}-{month:02d}")
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/habits/monthly",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching monthly data: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error fetching monthly data: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # OPERACJE USUWANIA
    # =========================================================================
    
    def delete_habit_column(self, column_id: str, soft: bool = True) -> APIResponse:
        """
        Usuń kolumnę habit trackera na serwerze.
        
        Args:
            column_id: ID kolumny
            soft: Czy soft delete (domyślnie True)
            
        Returns:
            APIResponse
        """
        try:
            params = {'soft': 'true' if soft else 'false'}
            
            logger.debug(f"Deleting habit column {column_id}, soft={soft}")
            
            response = self._request_with_retry(
                'DELETE',
                f"{self.base_url}/api/habits/columns/{column_id}",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error deleting habit column: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting habit column: {e}")
            return APIResponse(success=False, error=str(e))
    
    def delete_habit_record(self, record_id: str, soft: bool = True) -> APIResponse:
        """
        Usuń rekord habit trackera na serwerze.
        
        Args:
            record_id: ID rekordu
            soft: Czy soft delete (domyślnie True)
            
        Returns:
            APIResponse
        """
        try:
            params = {'soft': 'true' if soft else 'false'}
            
            logger.debug(f"Deleting habit record {record_id}, soft={soft}")
            
            response = self._request_with_retry(
                'DELETE',
                f"{self.base_url}/api/habits/records/{record_id}",
                params=params,
                timeout=self.timeout
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error deleting habit record: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error deleting habit record: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # BULK SYNCHRONIZACJA
    # =========================================================================
    
    def bulk_sync(
        self, 
        user_id: str,
        columns: Optional[List[Dict[str, Any]]] = None,
        records: Optional[List[Dict[str, Any]]] = None,
        last_sync: Optional[datetime] = None
    ) -> APIResponse:
        """
        Bulk synchronizacja habit trackera z serwerem.
        
        Args:
            user_id: ID użytkownika
            columns: Lista kolumn do synchronizacji (opcjonalnie)
            records: Lista rekordów do synchronizacji (opcjonalnie)  
            last_sync: Ostatnia synchronizacja (opcjonalnie)
            
        Returns:
            APIResponse z danymi do aktualizacji lokalnej
        """
        try:
            payload = {'user_id': user_id}
            
            if columns is not None:
                # Konwersja datetime do ISO string dla kolumn
                processed_columns = []
                for column in columns:
                    col_copy = column.copy()
                    for field in ['created_at', 'updated_at']:
                        if field in col_copy and isinstance(col_copy[field], datetime):
                            col_copy[field] = col_copy[field].isoformat()
                    processed_columns.append(col_copy)
                payload['columns'] = processed_columns
            
            if records is not None:
                # Konwersja datetime/date do ISO string dla rekordów
                processed_records = []
                for record in records:
                    rec_copy = record.copy()
                    for field in ['created_at', 'updated_at']:
                        if field in rec_copy and isinstance(rec_copy[field], datetime):
                            rec_copy[field] = rec_copy[field].isoformat()
                    if 'record_date' in rec_copy and isinstance(rec_copy['record_date'], date):
                        rec_copy['record_date'] = rec_copy['record_date'].isoformat()
                    processed_records.append(rec_copy)
                payload['records'] = processed_records
            
            if last_sync is not None:
                payload['last_sync'] = last_sync.isoformat()
            
            logger.debug(f"Bulk sync for user {user_id}: {len(columns or [])} columns, {len(records or [])} records")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/habits/sync",
                json=payload,
                timeout=30  # Dłuższy timeout dla bulk operacji
            )
            
            return self._handle_response(response)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error during bulk sync: {e}")
            return APIResponse(success=False, error=f"Network error: {str(e)}")
        except Exception as e:
            logger.error(f"Error during bulk sync: {e}")
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
        Rozwiąż konflikt między lokalną a serwerową wersją danych.
        
        Args:
            local_data: Lokalne dane
            server_data: Dane z serwera
            strategy: Strategia rozwiązywania konfliktów ('last_write_wins')
            
        Returns:
            Tuple[resolved_data, winner] - rozwiązane dane i źródło ('local'/'server')
        """
        if strategy == 'last_write_wins':
            # Porównaj updated_at timestamps
            local_updated = local_data.get('updated_at')
            server_updated = server_data.get('updated_at')
            
            if not local_updated or not server_updated:
                logger.warning("Missing updated_at timestamps for conflict resolution")
                return server_data, 'server'  # Domyślnie serwer wygrywa
            
            # Konwertuj do datetime jeśli to stringi
            if isinstance(local_updated, str):
                local_updated = datetime.fromisoformat(local_updated.replace('Z', '+00:00'))
            if isinstance(server_updated, str):
                server_updated = datetime.fromisoformat(server_updated.replace('Z', '+00:00'))
            
            if server_updated > local_updated:
                logger.debug(f"Conflict resolved: server wins (newer timestamp)")
                return server_data, 'server'
            else:
                logger.debug(f"Conflict resolved: local wins (newer timestamp)")
                return local_data, 'local'
        
        else:
            logger.warning(f"Unknown conflict resolution strategy: {strategy}")
            return server_data, 'server'
    
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
        logger.debug("Habit API client session closed")


# =========================================================================
# FUNKCJE POMOCNICZE
# =========================================================================

def create_habit_api_client(
    base_url: Optional[str] = None,
    auth_token: Optional[str] = None,
    refresh_token: Optional[str] = None,
    on_token_refreshed: Optional[Callable[[str, str], None]] = None
) -> HabitAPIClient:
    """
    Factory function dla tworzenia Habit API client.
    
    Args:
        base_url: URL serwera (jeśli None, użyje domyślnego z config)
        auth_token: Access token autentykacji
        refresh_token: Refresh token do odświeżania access token
        on_token_refreshed: Callback wywoływany po odświeżeniu tokena: (new_access_token, new_refresh_token) -> None
        
    Returns:
        Skonfigurowany HabitAPIClient
    """
    # TODO: Pobierz base_url z config jeśli nie podano
    if base_url is None:
        # z pliku config lub environment variable
        base_url = "http://localhost:8000"  # Placeholder
    
    return HabitAPIClient(
        base_url=base_url, 
        auth_token=auth_token,
        refresh_token=refresh_token,
        on_token_refreshed=on_token_refreshed
    )


def is_network_available() -> bool:
    """
    Sprawdź czy połączenie sieciowe jest dostępne.
    
    Returns:
        True jeśli sieć jest dostępna
    """
    try:
        response = requests.get("https://www.google.com", timeout=3)
        return response.status_code == 200
    except:
        return False