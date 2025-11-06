"""
API Client for Tasks & Kanban synchronization with server.

Handles HTTP communication with FastAPI backend:
- Upsert (create/update) tasks, tags, kanban items
- Fetching data from server
- Soft delete
- Bulk synchronization
- Version conflict resolution
- Automatic token refresh on expiration
"""

import requests
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime
from loguru import logger


class APIResponse:
    """Wrapper for API responses"""
    
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
    """Exception for version conflicts"""
    
    def __init__(self, message: str, server_data: Dict[str, Any], local_version: int, server_version: int):
        super().__init__(message)
        self.server_data = server_data
        self.local_version = local_version
        self.server_version = server_version


class TasksAPIClient:
    """
    API Client for Tasks & Kanban synchronization.
    
    Handles communication with FastAPI server, authentication,
    and version conflict resolution.
    """
    
    def __init__(
        self, 
        base_url: str, 
        auth_token: Optional[str] = None, 
        refresh_token: Optional[str] = None, 
        on_token_refreshed: Optional[Callable[[str, str], None]] = None
    ):
        """
        Initialize API client.
        
        Args:
            base_url: Server URL (e.g., "https://api.example.com")
            auth_token: Access token for authentication (optional)
            refresh_token: Refresh token for access token renewal (optional)
            on_token_refreshed: Callback called after token refresh: (new_access_token, new_refresh_token) -> None
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.on_token_refreshed = on_token_refreshed
        self.session = requests.Session()
        self.timeout = 10  # seconds
        
        # Default headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        if auth_token:
            self.session.headers['Authorization'] = f'Bearer {auth_token}'
        
        logger.info(f"TasksAPIClient initialized with base_url: {base_url}")
    
    def set_auth_token(self, token: str):
        """Set authentication token"""
        self.auth_token = token
        self.session.headers['Authorization'] = f'Bearer {token}'
        logger.debug("Auth token updated")
    
    def _try_refresh_token(self) -> bool:
        """
        Try to refresh access token using refresh token.
        
        Returns:
            True if refresh succeeded, False otherwise
        """
        if not self.refresh_token:
            logger.warning("Cannot refresh token: no refresh_token available")
            return False
        
        try:
            # Use new session without auth header (refresh endpoint doesn't require auth)
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
                    
                    # Call callback if exists
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
        Execute HTTP request with automatic retry after 401 (token refresh).
        
        Args:
            method: HTTP method (GET, POST, DELETE, etc.)
            url: Full URL
            **kwargs: Additional arguments for requests (json, params, etc.)
            
        Returns:
            Response object
        """
        # First request
        response = self.session.request(method, url, timeout=self.timeout, **kwargs)
        
        # If 401 and we have refresh_token, try to refresh
        if response.status_code == 401 and self.refresh_token:
            logger.info("Got 401 Unauthorized, attempting token refresh...")
            
            if self._try_refresh_token():
                # Token refreshed, retry request
                logger.info("Token refreshed, retrying request...")
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            else:
                logger.error("Token refresh failed, returning 401 response")
        
        return response
    
    def _handle_response(self, response: requests.Response) -> APIResponse:
        """
        Handle HTTP response.
        
        Args:
            response: Requests response
            
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
                status_code=getattr(response, 'status_code', None)
            )
    
    # =========================================================================
    # TASK OPERATIONS
    # =========================================================================
    
    def sync_task(self, task_data: Dict[str, Any], user_id: str) -> APIResponse:
        """
        Sync task with server (upsert).
        
        Args:
            task_data: Task data (dict)
            user_id: User ID
            
        Returns:
            APIResponse with server data
            
        Raises:
            ConflictError: If server version is newer
        """
        try:
            payload = {**task_data, 'user_id': user_id}
            
            # Convert datetime to ISO string
            for key in ['due_date', 'completion_date', 'alarm_date', 'created_at', 'updated_at']:
                if key in payload and isinstance(payload[key], datetime):
                    payload[key] = payload[key].isoformat()
            
            logger.debug(f"Syncing task {task_data.get('id')} to server")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/tasks/task",
                json=payload
            )
            
            # Check version conflict (409 Conflict)
            if response.status_code == 409:
                response_data = response.json()
                detail = response_data.get('detail', {})
                
                if isinstance(detail, dict):
                    raise ConflictError(
                        detail.get('message', 'Version conflict'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', task_data.get('version', 1)),
                        server_version=detail.get('server_version', 1)
                    )
                else:
                    raise ConflictError(
                        str(detail),
                        server_data={},
                        local_version=task_data.get('version', 1),
                        server_version=1
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except Exception as e:
            logger.error(f"Error syncing task: {e}")
            return APIResponse(success=False, error=str(e))
    
    def list_tasks(self, user_id: str, include_deleted: bool = False, include_archived: bool = True, since: Optional[datetime] = None) -> APIResponse:
        """
        Fetch tasks list from server.
        
        Args:
            user_id: User ID
            include_deleted: Include soft-deleted tasks
            include_archived: Include archived tasks
            since: Get only tasks modified after this timestamp (incremental sync)
            
        Returns:
            APIResponse with tasks list
        """
        try:
            params = {
                'user_id': user_id,
                'include_deleted': include_deleted,
                'include_archived': include_archived
            }
            
            if since:
                params['since'] = since.isoformat()
            
            logger.debug(f"Fetching tasks for user {user_id}")
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/tasks/tasks",
                params=params
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error fetching tasks: {e}")
            return APIResponse(success=False, error=str(e))
    
    def get_task(self, task_id: str) -> APIResponse:
        """
        Get single task by ID.
        
        Args:
            task_id: Task ID
            
        Returns:
            APIResponse with task data
        """
        try:
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/tasks/task/{task_id}"
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error fetching task {task_id}: {e}")
            return APIResponse(success=False, error=str(e))
    
    def delete_task(self, task_id: str, soft: bool = True) -> APIResponse:
        """
        Delete task.
        
        Args:
            task_id: Task ID
            soft: Use soft delete (default True)
            
        Returns:
            APIResponse
        """
        try:
            response = self._request_with_retry(
                'DELETE',
                f"{self.base_url}/api/tasks/task/{task_id}",
                params={'soft': soft}
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error deleting task {task_id}: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # TAG OPERATIONS
    # =========================================================================
    
    def sync_tag(self, tag_data: Dict[str, Any], user_id: str) -> APIResponse:
        """Sync tag with server (upsert)"""
        try:
            payload = {**tag_data, 'user_id': user_id}
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/tasks/tag",
                json=payload
            )
            
            if response.status_code == 409:
                response_data = response.json()
                detail = response_data.get('detail', {})
                
                if isinstance(detail, dict):
                    raise ConflictError(
                        detail.get('message', 'Version conflict'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', tag_data.get('version', 1)),
                        server_version=detail.get('server_version', 1)
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except Exception as e:
            logger.error(f"Error syncing tag: {e}")
            return APIResponse(success=False, error=str(e))
    
    def list_tags(self, user_id: str, include_deleted: bool = False) -> APIResponse:
        """Fetch tags list from server"""
        try:
            params = {'user_id': user_id, 'include_deleted': include_deleted}
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/tasks/tags",
                params=params
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error fetching tags: {e}")
            return APIResponse(success=False, error=str(e))
    
    def delete_tag(self, tag_id: str, soft: bool = True) -> APIResponse:
        """Delete tag"""
        try:
            response = self._request_with_retry(
                'DELETE',
                f"{self.base_url}/api/tasks/tag/{tag_id}",
                params={'soft': soft}
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error deleting tag {tag_id}: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # KANBAN OPERATIONS
    # =========================================================================
    
    def sync_kanban_item(self, item_data: Dict[str, Any], user_id: str) -> APIResponse:
        """Sync Kanban item with server (upsert)"""
        try:
            payload = {**item_data, 'user_id': user_id}
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/tasks/kanban/item",
                json=payload
            )
            
            if response.status_code == 409:
                response_data = response.json()
                detail = response_data.get('detail', {})
                
                if isinstance(detail, dict):
                    raise ConflictError(
                        detail.get('message', 'Version conflict'),
                        server_data=detail.get('server_data', {}),
                        local_version=detail.get('local_version', item_data.get('version', 1)),
                        server_version=detail.get('server_version', 1)
                    )
            
            return self._handle_response(response)
            
        except ConflictError:
            raise
        except Exception as e:
            logger.error(f"Error syncing kanban item: {e}")
            return APIResponse(success=False, error=str(e))
    
    def list_kanban_items(self, user_id: str, column_type: Optional[str] = None, include_deleted: bool = False) -> APIResponse:
        """Fetch Kanban items from server"""
        try:
            params = {'user_id': user_id, 'include_deleted': include_deleted}
            
            if column_type:
                params['column_type'] = column_type
            
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/tasks/kanban/items",
                params=params
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error fetching kanban items: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # BULK SYNC
    # =========================================================================
    
    def bulk_sync(
        self,
        user_id: str,
        tasks: List[Dict[str, Any]] = None,
        tags: List[Dict[str, Any]] = None,
        kanban_items: List[Dict[str, Any]] = None
    ) -> APIResponse:
        """
        Bulk synchronization of multiple items.
        
        Args:
            user_id: User ID
            tasks: List of task data (max 100)
            tags: List of tag data (max 100)
            kanban_items: List of kanban item data (max 100)
            
        Returns:
            APIResponse with bulk sync results
        """
        try:
            payload = {
                'user_id': user_id,
                'tasks': tasks or [],
                'tags': tags or [],
                'kanban_items': kanban_items or []
            }
            
            # Convert datetime to ISO string in tasks
            for task in payload['tasks']:
                for key in ['due_date', 'completion_date', 'alarm_date', 'created_at', 'updated_at']:
                    if key in task and isinstance(task[key], datetime):
                        task[key] = task[key].isoformat()
            
            logger.debug(f"Bulk sync: {len(payload['tasks'])} tasks, {len(payload['tags'])} tags, {len(payload['kanban_items'])} kanban items")
            
            response = self._request_with_retry(
                'POST',
                f"{self.base_url}/api/tasks/bulk-sync",
                json=payload
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error in bulk sync: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # STATS
    # =========================================================================
    
    def get_sync_stats(self, user_id: str) -> APIResponse:
        """
        Get user's synchronization statistics.
        
        Args:
            user_id: User ID
            
        Returns:
            APIResponse with stats data
        """
        try:
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/tasks/stats",
                params={'user_id': user_id}
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Error fetching sync stats: {e}")
            return APIResponse(success=False, error=str(e))
    
    # =========================================================================
    # HEALTH CHECK
    # =========================================================================
    
    def health_check(self) -> APIResponse:
        """Check API health"""
        try:
            response = self._request_with_retry(
                'GET',
                f"{self.base_url}/api/tasks/health"
            )
            
            return self._handle_response(response)
            
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return APIResponse(success=False, error=str(e))
