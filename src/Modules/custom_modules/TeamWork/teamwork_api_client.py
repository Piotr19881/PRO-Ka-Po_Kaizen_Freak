"""
API Client for TeamWork Module
================================

Klient HTTP do komunikacji z FastAPI backend dla modułu współpracy zespołowej.

Obsługuje:
- CRUD operacje na grupach (WorkGroups)
- CRUD operacje na wątkach (Topics)
- CRUD operacje na wiadomościach (Messages)
- CRUD operacje na zadaniach (Tasks)
- CRUD operacje na plikach (TopicFiles)
- Zarządzanie członkami grup (GroupMembers)
- Automatyczne odświeżanie tokena JWT
"""

import requests
from typing import Optional, List, Dict, Any, Callable
from datetime import datetime, date
from loguru import logger


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


class TeamWorkAPIClient:
    """
    Klient API dla modułu TeamWork.
    
    Obsługuje komunikację z FastAPI backend, autentykację JWT,
    oraz wszystkie operacje CRUD dla współpracy zespołowej.
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
            base_url: URL serwera (np. "http://127.0.0.1:8000")
            auth_token: JWT access token
            refresh_token: JWT refresh token (opcjonalnie)
            on_token_refreshed: Callback po odświeżeniu tokena (new_access, new_refresh) -> None
        """
        self.base_url = base_url.rstrip('/')
        self.auth_token = auth_token
        self.refresh_token = refresh_token
        self.on_token_refreshed = on_token_refreshed
        self.session = requests.Session()
        self.timeout = 30
        
        # Domyślne headers
        self.session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        if auth_token:
            self.session.headers['Authorization'] = f'Bearer {auth_token}'
        
        logger.info(f"[TeamWork API] Client initialized with base_url: {base_url}")
    
    def set_auth_token(self, token: str):
        """Ustaw token autentykacji"""
        self.auth_token = token
        self.session.headers['Authorization'] = f'Bearer {token}'
        logger.debug("[TeamWork API] Auth token updated")
    
    def _try_refresh_token(self) -> bool:
        """Odśwież access token używając refresh token"""
        if not self.refresh_token:
            logger.warning("[TeamWork API] Cannot refresh token: no refresh_token available")
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
                    
                    logger.success("[TeamWork API] Access token refreshed")
                    return True
            
            logger.error(f"[TeamWork API] Token refresh failed: {response.status_code}")
            return False
            
        except Exception as e:
            logger.error(f"[TeamWork API] Token refresh error: {e}")
            return False
    
    def _request(self, method: str, endpoint: str, **kwargs) -> APIResponse:
        """
        Wykonaj request HTTP z automatycznym retry po 401.
        
        Args:
            method: HTTP method (GET, POST, PUT, DELETE, PATCH)
            endpoint: Endpoint (np. "/api/teamwork/groups")
            **kwargs: Dodatkowe argumenty (json, params, data, files)
        
        Returns:
            APIResponse object
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            
            # 401 Unauthorized - spróbuj odświeżyć token
            if response.status_code == 401 and self._try_refresh_token():
                # Retry request z nowym tokenem
                response = self.session.request(method, url, timeout=self.timeout, **kwargs)
            
            # Sukces (2xx)
            if 200 <= response.status_code < 300:
                try:
                    data = response.json() if response.content else None
                except ValueError:
                    data = None
                
                return APIResponse(
                    success=True,
                    data=data,
                    status_code=response.status_code
                )
            
            # Błąd (4xx, 5xx)
            error_msg = f"HTTP {response.status_code}"
            try:
                error_detail = response.json().get('detail', response.text)
                error_msg = f"{error_msg}: {error_detail}"
            except:
                error_msg = f"{error_msg}: {response.text[:200]}"
            
            logger.warning(f"[TeamWork API] Request failed: {method} {endpoint} -> {error_msg}")
            
            return APIResponse(
                success=False,
                error=error_msg,
                status_code=response.status_code
            )
            
        except requests.exceptions.Timeout:
            logger.error(f"[TeamWork API] Request timeout: {method} {endpoint}")
            return APIResponse(success=False, error="Request timeout")
        
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[TeamWork API] Connection error: {e}")
            return APIResponse(success=False, error=f"Connection error: {str(e)}")
        
        except Exception as e:
            logger.error(f"[TeamWork API] Unexpected error: {e}")
            return APIResponse(success=False, error=f"Unexpected error: {str(e)}")
    
    # ========================================================================
    # WORK GROUPS - Grupy robocze
    # ========================================================================
    
    def create_group(self, group_name: str, description: Optional[str] = None) -> APIResponse:
        """
        Utwórz nową grupę roboczą.
        
        Args:
            group_name: Nazwa grupy
            description: Opis grupy (opcjonalnie)
        
        Returns:
            APIResponse z danymi utworzonej grupy
        """
        payload = {
            "group_name": group_name,
            "description": description
        }
        
        logger.info(f"[TeamWork API] Creating group: {group_name}")
        return self._request("POST", "/api/teamwork/groups", json=payload)
    
    def get_user_groups(self) -> APIResponse:
        """
        Pobierz wszystkie grupy użytkownika.
        
        Returns:
            APIResponse z listą grup
        """
        logger.debug("[TeamWork API] Fetching user groups")
        return self._request("GET", "/api/teamwork/groups")
    
    def get_group(self, group_id: int) -> APIResponse:
        """
        Pobierz szczegóły grupy.
        
        Args:
            group_id: ID grupy
        
        Returns:
            APIResponse z danymi grupy (wraz z członkami)
        """
        logger.debug(f"[TeamWork API] Fetching group {group_id}")
        return self._request("GET", f"/api/teamwork/groups/{group_id}")
    
    def update_group(self, group_id: int, group_name: Optional[str] = None, 
                    description: Optional[str] = None, is_active: Optional[bool] = None) -> APIResponse:
        """
        Zaktualizuj grupę (tylko owner).
        
        Args:
            group_id: ID grupy
            group_name: Nowa nazwa (opcjonalnie)
            description: Nowy opis (opcjonalnie)
            is_active: Status aktywności (opcjonalnie)
        
        Returns:
            APIResponse z zaktualizowanymi danymi grupy
        """
        payload = {}
        if group_name is not None:
            payload["group_name"] = group_name
        if description is not None:
            payload["description"] = description
        if is_active is not None:
            payload["is_active"] = is_active
        
        logger.info(f"[TeamWork API] Updating group {group_id}")
        return self._request("PUT", f"/api/teamwork/groups/{group_id}", json=payload)
    
    def delete_group(self, group_id: int) -> APIResponse:
        """
        Usuń grupę (tylko owner).
        
        Args:
            group_id: ID grupy
        
        Returns:
            APIResponse (204 No Content przy sukcesie)
        """
        logger.info(f"[TeamWork API] Deleting group {group_id}")
        return self._request("DELETE", f"/api/teamwork/groups/{group_id}")
    
    # ========================================================================
    # GROUP MEMBERS - Członkowie grup
    # ========================================================================
    
    def add_member(self, group_id: int, user_id: str, role: str = "member") -> APIResponse:
        """
        Dodaj członka do grupy (tylko owner).
        
        Args:
            group_id: ID grupy
            user_id: ID użytkownika do dodania
            role: Rola ('owner' lub 'member', domyślnie 'member')
        
        Returns:
            APIResponse z danymi dodanego członka
        """
        payload = {
            "user_id": user_id,
            "role": role
        }
        
        logger.info(f"[TeamWork API] Adding member {user_id} to group {group_id}")
        return self._request("POST", f"/api/teamwork/groups/{group_id}/members", json=payload)
    
    def remove_member(self, group_id: int, user_id: str) -> APIResponse:
        """
        Usuń członka z grupy (tylko owner, nie może usunąć siebie).
        
        Args:
            group_id: ID grupy
            user_id: ID użytkownika do usunięcia
        
        Returns:
            APIResponse (204 No Content przy sukcesie)
        """
        logger.info(f"[TeamWork API] Removing member {user_id} from group {group_id}")
        return self._request("DELETE", f"/api/teamwork/groups/{group_id}/members/{user_id}")
    
    def transfer_ownership(self, group_id: int, new_owner_id: str) -> APIResponse:
        """
        Przekaż ownership grupy innemu członkowi (tylko owner).
        
        Args:
            group_id: ID grupy
            new_owner_id: ID nowego właściciela (musi być członkiem)
        
        Returns:
            APIResponse z zaktualizowanymi danymi grupy
        """
        payload = {"new_owner_id": new_owner_id}
        
        logger.info(f"[TeamWork API] Transferring ownership of group {group_id} to {new_owner_id}")
        return self._request("PUT", f"/api/teamwork/groups/{group_id}/transfer-ownership", json=payload)
    
    # ========================================================================
    # TOPICS - Wątki tematyczne
    # ========================================================================
    
    def create_topic(self, group_id: int, topic_name: str, initial_message: Optional[str] = None) -> APIResponse:
        """
        Utwórz nowy wątek w grupie.
        
        Args:
            group_id: ID grupy
            topic_name: Nazwa wątku
            initial_message: Opcjonalna pierwsza wiadomość w wątku
        
        Returns:
            APIResponse z danymi utworzonego wątku
        """
        payload = {
            "group_id": group_id,
            "topic_name": topic_name,
            "initial_message": initial_message
        }
        
        logger.info(f"[TeamWork API] Creating topic '{topic_name}' in group {group_id}")
        return self._request("POST", "/api/teamwork/topics", json=payload)
    
    def get_group_topics(self, group_id: int) -> APIResponse:
        """
        Pobierz wszystkie wątki w grupie.
        
        Args:
            group_id: ID grupy
        
        Returns:
            APIResponse z listą wątków
        """
        logger.debug(f"[TeamWork API] Fetching topics for group {group_id}")
        return self._request("GET", f"/api/teamwork/groups/{group_id}/topics")
    
    def get_topic(self, topic_id: int) -> APIResponse:
        """
        Pobierz szczegóły wątku.
        
        Args:
            topic_id: ID wątku
        
        Returns:
            APIResponse z danymi wątku
        """
        logger.debug(f"[TeamWork API] Fetching topic {topic_id}")
        return self._request("GET", f"/api/teamwork/topics/{topic_id}")
    
    def update_topic(self, topic_id: int, topic_name: Optional[str] = None,
                    description: Optional[str] = None, is_active: Optional[bool] = None) -> APIResponse:
        """
        Zaktualizuj wątek.
        
        Args:
            topic_id: ID wątku
            topic_name: Nowa nazwa (opcjonalnie)
            description: Nowy opis (opcjonalnie)
            is_active: Status aktywności (opcjonalnie)
        
        Returns:
            APIResponse z zaktualizowanymi danymi wątku
        """
        payload = {}
        if topic_name is not None:
            payload["topic_name"] = topic_name
        if description is not None:
            payload["description"] = description
        if is_active is not None:
            payload["is_active"] = is_active
        
        logger.info(f"[TeamWork API] Updating topic {topic_id}")
        return self._request("PUT", f"/api/teamwork/topics/{topic_id}", json=payload)
    
    # ========================================================================
    # MESSAGES - Wiadomości w wątkach
    # ========================================================================
    
    def create_message(self, topic_id: int, content: str, background_color: Optional[str] = None,
                      is_important: bool = False) -> APIResponse:
        """
        Dodaj wiadomość do wątku.
        
        Args:
            topic_id: ID wątku
            content: Treść wiadomości
            background_color: Kolor tła (hex, opcjonalnie)
            is_important: Czy wiadomość jest ważna
        
        Returns:
            APIResponse z danymi utworzonej wiadomości
        """
        payload = {
            "topic_id": topic_id,
            "content": content,
            "background_color": background_color,
            "is_important": is_important
        }
        
        logger.info(f"[TeamWork API] Creating message in topic {topic_id}")
        return self._request("POST", "/api/teamwork/messages", json=payload)
    
    def get_topic_messages(self, topic_id: int) -> APIResponse:
        """
        Pobierz wszystkie wiadomości w wątku.
        
        Args:
            topic_id: ID wątku
        
        Returns:
            APIResponse z listą wiadomości
        """
        logger.debug(f"[TeamWork API] Fetching messages for topic {topic_id}")
        return self._request("GET", f"/api/teamwork/topics/{topic_id}/messages")
    
    def update_message(self, message_id: int, content: Optional[str] = None,
                      background_color: Optional[str] = None, is_important: Optional[bool] = None) -> APIResponse:
        """
        Zaktualizuj wiadomość.
        
        Args:
            message_id: ID wiadomości
            content: Nowa treść (opcjonalnie)
            background_color: Nowy kolor (opcjonalnie)
            is_important: Nowy status (opcjonalnie)
        
        Returns:
            APIResponse z zaktualizowanymi danymi wiadomości
        """
        payload = {}
        if content is not None:
            payload["content"] = content
        if background_color is not None:
            payload["background_color"] = background_color
        if is_important is not None:
            payload["is_important"] = is_important
        
        logger.info(f"[TeamWork API] Updating message {message_id}")
        return self._request("PUT", f"/api/teamwork/messages/{message_id}", json=payload)
    
    # ========================================================================
    # TASKS - Zadania
    # ========================================================================
    
    def create_task(self, topic_id: int, task_subject: str, assigned_to: Optional[str] = None,
                   due_date: Optional[date] = None, priority: str = "medium") -> APIResponse:
        """
        Utwórz zadanie w wątku.
        
        Args:
            topic_id: ID wątku
            task_subject: Tytuł zadania
            assigned_to: ID przypisanej osoby (opcjonalnie)
            due_date: Termin wykonania (opcjonalnie)
            priority: Priorytet ('low', 'medium', 'high')
        
        Returns:
            APIResponse z danymi utworzonego zadania
        """
        payload = {
            "topic_id": topic_id,
            "task_subject": task_subject,
            "assigned_to": assigned_to,
            "due_date": due_date.isoformat() if due_date else None,
            "priority": priority
        }
        
        logger.info(f"[TeamWork API] Creating task '{task_subject}' in topic {topic_id}")
        return self._request("POST", "/api/teamwork/tasks", json=payload)
    
    def get_topic_tasks(self, topic_id: int) -> APIResponse:
        """
        Pobierz wszystkie zadania w wątku.
        
        Args:
            topic_id: ID wątku
        
        Returns:
            APIResponse z listą zadań
        """
        logger.debug(f"[TeamWork API] Fetching tasks for topic {topic_id}")
        return self._request("GET", f"/api/teamwork/topics/{topic_id}/tasks")
    
    def complete_task(self, task_id: int, completed: bool = True) -> APIResponse:
        """
        Oznacz zadanie jako wykonane/niewykonane.
        
        Args:
            task_id: ID zadania
            completed: True = wykonane, False = niewykonane
        
        Returns:
            APIResponse z zaktualizowanymi danymi zadania
        """
        payload = {"completed": completed}
        
        logger.info(f"[TeamWork API] Marking task {task_id} as {'completed' if completed else 'not completed'}")
        return self._request("PATCH", f"/api/teamwork/tasks/{task_id}/complete", json=payload)
    
    # ========================================================================
    # FILES - Pliki (używane przez FileUploadDialog, tutaj dla kompletności)
    # ========================================================================
    
    def get_topic_files(self, topic_id: int) -> APIResponse:
        """
        Pobierz wszystkie pliki w wątku.
        
        Args:
            topic_id: ID wątku
        
        Returns:
            APIResponse z listą plików
        """
        logger.debug(f"[TeamWork API] Fetching files for topic {topic_id}")
        return self._request("GET", f"/api/teamwork/topics/{topic_id}/files")
    
    def delete_file(self, file_id: int) -> APIResponse:
        """
        Usuń plik z wątku.
        
        Args:
            file_id: ID pliku
        
        Returns:
            APIResponse (204 No Content przy sukcesie)
        """
        logger.info(f"[TeamWork API] Deleting file {file_id}")
        return self._request("DELETE", f"/api/teamwork/files/{file_id}")
    
    def mark_file_important(self, file_id: int, is_important: bool = True) -> APIResponse:
        """
        Oznacz plik jako ważny/nieważny.
        
        Args:
            file_id: ID pliku
            is_important: True = ważny, False = nieważny
        
        Returns:
            APIResponse z zaktualizowanymi danymi pliku
        """
        payload = {"is_important": is_important}
        
        logger.info(f"[TeamWork API] Marking file {file_id} as {'important' if is_important else 'not important'}")
        return self._request("PATCH", f"/api/teamwork/files/{file_id}", json=payload)
    
    def mark_message_important(self, message_id: int, is_important: bool = True) -> APIResponse:
        """
        Oznacz wiadomość jako ważną/nieważną.
        
        Args:
            message_id: ID wiadomości
            is_important: True = ważna, False = nieważna
        
        Returns:
            APIResponse z zaktualizowanymi danymi wiadomości
        """
        payload = {"is_important": is_important}
        
        logger.info(f"[TeamWork API] Marking message {message_id} as {'important' if is_important else 'not important'}")
        return self._request("PATCH", f"/api/teamwork/messages/{message_id}", json=payload)
    
    # ========================================================================
    # SHARE LINKS - Linki współdzielenia - Phase 6 Task 6.1
    # ========================================================================
    
    def generate_share_link(self, topic_id: int, default_role: str = "member") -> APIResponse:
        """
        Generuje link współdzielenia dla topicu.
        
        Args:
            topic_id: ID topicu
            default_role: Domyślna rola dla nowych członków (viewer/member/admin)
        
        Returns:
            APIResponse z danymi linku (share_url, share_link_id, created_at, etc.)
        """
        payload = {"default_role": default_role}
        
        logger.info(f"[TeamWork API] Generating share link for topic {topic_id} with role {default_role}")
        return self._request("POST", f"/api/teamwork/topics/{topic_id}/share-links", json=payload)
    
    def get_topic_share_links(self, topic_id: int) -> APIResponse:
        """
        Pobiera wszystkie linki współdzielenia dla topicu.
        
        Args:
            topic_id: ID topicu
        
        Returns:
            APIResponse z listą linków
        """
        logger.info(f"[TeamWork API] Getting share links for topic {topic_id}")
        return self._request("GET", f"/api/teamwork/topics/{topic_id}/share-links")
    
    def revoke_share_link(self, link_id: int) -> APIResponse:
        """
        Unieważnia link współdzielenia.
        
        Args:
            link_id: ID linku do unieważnienia
        
        Returns:
            APIResponse (204 No Content przy sukcesie)
        """
        logger.info(f"[TeamWork API] Revoking share link {link_id}")
        return self._request("DELETE", f"/api/teamwork/share-links/{link_id}")
    
    def get_share_link_stats(self, link_id: int) -> APIResponse:
        """
        Pobiera statystyki linku współdzielenia (clicks, użycia).
        
        Args:
            link_id: ID linku
        
        Returns:
            APIResponse ze statystykami (clicks_count, unique_visitors, etc.)
        """
        logger.info(f"[TeamWork API] Getting stats for share link {link_id}")
        return self._request("GET", f"/api/teamwork/share-links/{link_id}/stats")
    
    # ========================================================================
    # INVITATIONS - System zaproszeń - Phase 6 Task 6.2
    # ========================================================================
    
    def send_topic_invitation(self, topic_id: int, email: str, role: str = "member", message: Optional[str] = None) -> APIResponse:
        """
        Wysyła zaproszenie do topicu przez email.
        
        Args:
            topic_id: ID topicu
            email: Email osoby zapraszanej
            role: Rola dla zaproszonej osoby (viewer/member/admin)
            message: Opcjonalna wiadomość w zaproszeniu
        
        Returns:
            APIResponse z danymi zaproszenia
        """
        payload = {
            "email": email,
            "role": role,
            "message": message
        }
        
        logger.info(f"[TeamWork API] Sending topic invitation to {email} for topic {topic_id}")
        return self._request("POST", f"/api/teamwork/topics/{topic_id}/invitations", json=payload)
    
    def get_pending_invitations(self) -> APIResponse:
        """
        Pobiera listę oczekujących zaproszeń dla zalogowanego użytkownika.
        
        Returns:
            APIResponse z listą zaproszeń
        """
        logger.info("[TeamWork API] Getting pending invitations")
        return self._request("GET", "/api/teamwork/invitations/pending")
    
    def accept_invitation(self, invitation_id: int) -> APIResponse:
        """
        Akceptuje zaproszenie do topicu.
        
        Args:
            invitation_id: ID zaproszenia
        
        Returns:
            APIResponse z danymi topicu
        """
        logger.info(f"[TeamWork API] Accepting invitation {invitation_id}")
        return self._request("POST", f"/api/teamwork/invitations/{invitation_id}/accept")
    
    def decline_invitation(self, invitation_id: int) -> APIResponse:
        """
        Odrzuca zaproszenie do topicu.
        
        Args:
            invitation_id: ID zaproszenia
        
        Returns:
            APIResponse (204 No Content przy sukcesie)
        """
        logger.info(f"[TeamWork API] Declining invitation {invitation_id}")
        return self._request("POST", f"/api/teamwork/invitations/{invitation_id}/decline")
    
    def get_topic_invitations(self, topic_id: int) -> APIResponse:
        """
        Pobiera listę wszystkich zaproszeń dla topicu (dla adminów).
        
        Args:
            topic_id: ID topicu
        
        Returns:
            APIResponse z listą zaproszeń
        """
        logger.info(f"[TeamWork API] Getting invitations for topic {topic_id}")
        return self._request("GET", f"/api/teamwork/topics/{topic_id}/invitations")
    
    # ========================================================================
    # PERMISSIONS - Zarządzanie uprawnieniami - Phase 6 Task 6.3
    # ========================================================================
    
    def get_topic_members(self, topic_id: int) -> APIResponse:
        """
        Pobiera listę członków topicu z ich rolami.
        
        Args:
            topic_id: ID topicu
        
        Returns:
            APIResponse z listą członków (user_id, email, role, joined_at)
        """
        logger.info(f"[TeamWork API] Getting members for topic {topic_id}")
        return self._request("GET", f"/api/teamwork/topics/{topic_id}/members")
    
    def update_member_role(self, topic_id: int, user_id: int, role: str) -> APIResponse:
        """
        Aktualizuje rolę członka topicu.
        
        Args:
            topic_id: ID topicu
            user_id: ID użytkownika
            role: Nowa rola (viewer/member/admin/owner)
        
        Returns:
            APIResponse z zaktualizowanymi danymi członka
        """
        payload = {"role": role}
        
        logger.info(f"[TeamWork API] Updating role for user {user_id} in topic {topic_id} to {role}")
        return self._request("PATCH", f"/api/teamwork/topics/{topic_id}/members/{user_id}", json=payload)
    
    def remove_topic_member(self, topic_id: int, user_id: int) -> APIResponse:
        """
        Usuwa członka z topicu (tylko admin/owner).
        
        Args:
            topic_id: ID topicu
            user_id: ID użytkownika do usunięcia
        
        Returns:
            APIResponse (204 No Content przy sukcesie)
        """
        logger.info(f"[TeamWork API] Removing user {user_id} from topic {topic_id}")
        return self._request("DELETE", f"/api/teamwork/topics/{topic_id}/members/{user_id}")
    
    def get_my_topic_role(self, topic_id: int) -> APIResponse:
        """
        Pobiera rolę zalogowanego użytkownika w topicu.
        
        Args:
            topic_id: ID topicu
        
        Returns:
            APIResponse z rolą (owner/admin/member/viewer)
        """
        logger.info(f"[TeamWork API] Getting my role for topic {topic_id}")
        return self._request("GET", f"/api/teamwork/topics/{topic_id}/my-role")


