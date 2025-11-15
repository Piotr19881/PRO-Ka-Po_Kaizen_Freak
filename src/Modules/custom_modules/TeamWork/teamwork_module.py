"""
TeamWork Module - Główny moduł współpracy zespołowej
Refaktoryzacja zgodna ze standardem aplikacji PRO-Ka-Po
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QPushButton, QToolBar, QMessageBox, QDialog, QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal
from loguru import logger

try:
    from ....utils.i18n_manager import get_i18n
    from ....utils.theme_manager import get_theme_manager
    from ....config import TEAMWORK_API_BASE_URL
except ImportError:
    # Fallback for standalone execution
    get_i18n = None
    get_theme_manager = None
    TEAMWORK_API_BASE_URL = "http://127.0.0.1:8000"

# Import local TeamWork modules
from .conversation_panel import ConversationPanel
from .data_sample import SAMPLE_GROUPS
from .dialogs import CreateGroupDialog, InvitationsDialog, MyGroupsDialog, ReplyDialog, CreateTopicDialog
from .group_tree_panel import GroupTreePanel
from .task_dialog import TaskDialog
from .task_widgets import GanttChartWidget
from .team_management_dialog import TeamManagementDialog
from .teamwork_api_client import TeamWorkAPIClient


class TeamWorkModule(QWidget):
    """
    TeamWork Module - Współpraca zespołowa i zarządzanie projektami
    
    Funkcje:
    - Zarządzanie zespołami i grupami roboczymi
    - Wątki tematyczne (topics) z konwersacjami
    - Zadania zespołowe z widokiem Gantt
    - Udostępnianie plików i linków
    - System zaproszeń i powiadomień
    """
    
    # Sygnały
    module_activated = pyqtSignal()
    module_deactivated = pyqtSignal()
    data_changed = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Ustaw ObjectName dla theme_manager
        self.setObjectName("TeamWorkModule")
        
        # Menedżery
        self.i18n_manager = get_i18n() if get_i18n else None
        self.theme_manager = get_theme_manager() if get_theme_manager else None
        
        # Dane użytkownika i autentykacja
        self.user_data = {}
        self.user_id = None
        self.access_token = None
        self.refresh_token = None
        self.api_client = None  # TeamWorkAPIClient - utworzony po zalogowaniu
        
        # Dane modułu
        self._groups = SAMPLE_GROUPS  # Będzie zastąpione danymi z bazy
        self.current_groups = []  # Grupy załadowane z API (dla dialogów)
        
        # Konfiguracja UI
        self._setup_ui()
        self._connect_signals()
        self._apply_theme()
        
        # Połącz z menedżerem i18n dla automatycznego odświeżania tłumaczeń
        if self.i18n_manager:
            self.i18n_manager.language_changed.connect(self.update_translations)
        
        logger.info("[TeamWork] Module initialized")
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        # Główny layout
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(1)  # Minimalny spacing między toolbar a splitter
        
        # Toolbar z przyciskami akcji
        toolbar = self._create_toolbar()
        main_layout.addWidget(toolbar)
        
        # Splitter z panelem drzewa grup i panelem konwersacji
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setOpaqueResize(True)
        splitter.setHandleWidth(2)
        
        # Panel drzewa grup (lewy)
        self.tree_panel = GroupTreePanel(self)
        self.tree_panel.set_groups(self._groups)
        splitter.addWidget(self.tree_panel)
        
        # Panel konwersacji (prawy)
        self.conversation_panel = ConversationPanel(self)
        splitter.addWidget(self.conversation_panel)
        
        # Proporcje splitter - 25% lewy panel, 75% prawy panel
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        total_width = 1200  # Zakładana szerokość okna
        splitter.setSizes([int(total_width * 0.25), int(total_width * 0.75)])
        
        main_layout.addWidget(splitter)
        
        logger.debug("[TeamWork] UI setup complete")
    
    def _create_toolbar(self) -> QWidget:
        """Utworzenie paska narzędzi"""
        toolbar_widget = QWidget()
        toolbar_widget.setObjectName("TeamWorkToolbar")
        
        # Ustawienie polityki rozmiaru, aby widget nie rozciągał się w pionie
        toolbar_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        
        toolbar_layout = QHBoxLayout(toolbar_widget)
        toolbar_layout.setContentsMargins(8, 2, 8, 2)  # Zmniejszony margines góra/dół
        toolbar_layout.setSpacing(6)
        
        # Przyciski toolbar
        self.btn_my_groups = QPushButton("👥 Zarządzanie zespołami")
        self.btn_my_groups.setObjectName("toolbarButton")
        self.btn_my_groups.setToolTip(self._t("teamwork.my_groups_tooltip", "Zarządzaj swoimi zespołami"))
        self.btn_my_groups.setFixedHeight(32)
        self.btn_my_groups.clicked.connect(self._on_my_groups)
        toolbar_layout.addWidget(self.btn_my_groups)
        
        self.btn_create_group = QPushButton("➕ Utwórz grupę")
        self.btn_create_group.setObjectName("toolbarButton")
        self.btn_create_group.setToolTip(self._t("teamwork.create_group_tooltip", "Utwórz nową grupę roboczą"))
        self.btn_create_group.setFixedHeight(32)
        self.btn_create_group.clicked.connect(self._on_create_group)
        toolbar_layout.addWidget(self.btn_create_group)
        
        self.btn_create_topic = QPushButton("📝 Utwórz wątek")
        self.btn_create_topic.setObjectName("toolbarButton")
        self.btn_create_topic.setToolTip(self._t("teamwork.create_topic_tooltip", "Dodaj nowy wątek tematyczny"))
        self.btn_create_topic.setFixedHeight(32)
        self.btn_create_topic.clicked.connect(self._on_create_topic)
        toolbar_layout.addWidget(self.btn_create_topic)
        
        self.btn_invitations = QPushButton("📨 Zaproszenia")
        self.btn_invitations.setObjectName("toolbarButton")
        self.btn_invitations.setToolTip(self._t("teamwork.invitations_tooltip", "Zarządzaj zaproszeniami"))
        self.btn_invitations.setFixedHeight(32)
        self.btn_invitations.clicked.connect(self._on_invitations)
        toolbar_layout.addWidget(self.btn_invitations)
        
        toolbar_layout.addStretch()
        
        return toolbar_widget
    
    def _connect_signals(self):
        """Połącz sygnały i sloty"""
        # Sygnały z panelu drzewa
        self.tree_panel.group_selected.connect(self._handle_group_selected)
        self.tree_panel.topic_selected.connect(self._handle_topic_selected)
        self.tree_panel.topic_conversations_selected.connect(self._handle_topic_conversations)
        self.tree_panel.topic_files_selected.connect(self._handle_topic_files)
        self.tree_panel.topic_links_selected.connect(self._handle_topic_links)
        self.tree_panel.topic_tasks_selected.connect(self._handle_topic_tasks)
        self.tree_panel.topic_important_selected.connect(self._handle_topic_important)
        
        # Sygnały z panelu konwersacji
        self.conversation_panel.reply_requested.connect(self._handle_reply_requested)
        self.conversation_panel.create_task_requested.connect(self._handle_create_task)
        self.conversation_panel.view_gantt_requested.connect(self._handle_view_gantt)
        self.conversation_panel.toggle_important.connect(self._handle_toggle_important)
        
        logger.debug("[TeamWork] Signals connected")
    
    def _apply_theme(self):
        """Zastosuj aktualny motyw kolorystyczny"""
        if not self.theme_manager:
            return
        
        # Użyj property classes i polish/unpolish jak w PFile
        style = self.style()
        if style:
            style.unpolish(self)
            style.polish(self)
        self.update()
        
        # Opcjonalnie: odśwież kolory paneli podrzędnych
        if hasattr(self, 'tree_panel'):
            self.tree_panel.update()
        if hasattr(self, 'conversation_panel'):
            self.conversation_panel.update()
        
        logger.debug("[TeamWork] Theme applied")
    
    def update_translations(self):
        """Odśwież tłumaczenia interfejsu"""
        # Aktualizuj teksty przycisków
        self.btn_my_groups.setText(self._t("teamwork.my_groups", "👥 Zarządzanie zespołami"))
        self.btn_create_group.setText(self._t("teamwork.create_group", "➕ Utwórz grupę"))
        self.btn_create_topic.setText(self._t("teamwork.create_topic", "📝 Utwórz wątek"))
        self.btn_invitations.setText(self._t("teamwork.invitations", "📨 Zaproszenia"))
        
        # Aktualizuj tooltips
        self.btn_my_groups.setToolTip(self._t("teamwork.my_groups_tooltip", "Zarządzaj swoimi zespołami"))
        self.btn_create_group.setToolTip(self._t("teamwork.create_group_tooltip", "Utwórz nową grupę roboczą"))
        self.btn_create_topic.setToolTip(self._t("teamwork.create_topic_tooltip", "Dodaj nowy wątek tematyczny"))
        self.btn_invitations.setToolTip(self._t("teamwork.invitations_tooltip", "Zarządzaj zaproszeniami"))
        
        logger.debug("[TeamWork] Translations updated")
    
    def _t(self, key: str, default: str = "") -> str:
        """Helper function for translations"""
        if self.i18n_manager:
            from ....utils.i18n_manager import t
            return t(key, default)
        return default
    
    # === Handlers dla akcji toolbar ===
    
    def _on_my_groups(self):
        """Otwórz dialog zarządzania zespołami"""
        dialog = TeamManagementDialog(api_client=self.api_client, parent=self)
        dialog.exec()
    
    def _on_create_group(self):
        """Otwórz dialog tworzenia nowej grupy"""
        dialog = CreateGroupDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            group_data = dialog.get_group_data()
            
            # Sprawdź czy mamy API client
            if not self.api_client:
                QMessageBox.warning(
                    self,
                    "Brak połączenia",
                    "Nie można utworzyć grupy - brak połączenia z serwerem.\nZaloguj się ponownie."
                )
                return
            
            # Wywołaj API do utworzenia grupy
            logger.info(f"[TeamWork] Creating group via API: {group_data['name']}")
            response = self.api_client.create_group(
                group_name=group_data['name'],
                description=group_data['description']
            )
            
            if response.success:
                created_group = response.data
                logger.success(f"[TeamWork] Group created successfully: ID={created_group.get('id')}")
                
                # Odśwież listę grup
                self._refresh_groups_from_api()
                
                # Emit sygnał o zmianach
                self.data_changed.emit()
                
                # Pokaż potwierdzenie
                QMessageBox.information(
                    self,
                    self._t("teamwork.group_created", "Grupa utworzona"),
                    f"Grupa '{group_data['name']}' została utworzona pomyślnie.\n\n"
                    f"ID grupy: {created_group.get('id')}"
                )
            else:
                # Błąd API
                logger.error(f"[TeamWork] Failed to create group: {response.error}")
                QMessageBox.critical(
                    self,
                    "Błąd tworzenia grupy",
                    f"Nie udało się utworzyć grupy:\n{response.error}"
                )
    
    def _on_create_topic(self):
        """Otwórz dialog tworzenia nowego wątku"""
        dialog = CreateTopicDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            topic_data = dialog.get_group_data()  # Używa tej samej nazwy metody
            
            # Sprawdź czy mamy API client
            if not self.api_client:
                QMessageBox.warning(
                    self,
                    "Brak połączenia",
                    "Nie można utworzyć wątku - brak połączenia z serwerem.\nZaloguj się ponownie."
                )
                return
            
            # Sprawdź czy wybrano grupę
            if not topic_data.get('group_id'):
                QMessageBox.warning(
                    self,
                    "Brak grupy",
                    "Nie wybrano grupy. Wybierz grupę, w której chcesz utworzyć wątek."
                )
                return
            
            # Wywołaj API do utworzenia wątku
            logger.info(f"[TeamWork] Creating topic via API: {topic_data['name']} in group {topic_data['group_id']}")
            response = self.api_client.create_topic(
                group_id=topic_data['group_id'],
                topic_name=topic_data['name'],
                initial_message=topic_data.get('initial_message')
            )
            
            if response.success:
                created_topic = response.data
                topic_id = created_topic.get('id')
                logger.success(f"[TeamWork] Topic created successfully: ID={topic_id}")
                
                # Odśwież drzewo grup (aby zobaczyć nowy wątek)
                self._refresh_groups_from_api()
                
                # Emit sygnał o zmianach
                self.data_changed.emit()
                
                # Automatycznie otwórz nowy wątek
                if topic_id and hasattr(self, 'tree_panel'):
                    self.tree_panel.select_topic_by_id(topic_id)
                
                # Pokaż potwierdzenie
                QMessageBox.information(
                    self,
                    self._t("teamwork.topic_created", "Wątek utworzony"),
                    f"Wątek '{topic_data['name']}' został utworzony pomyślnie.\n\n"
                    f"ID wątku: {topic_id}\n"
                    f"Grupa: {topic_data['group_name']}"
                )
            else:
                # Błąd API
                logger.error(f"[TeamWork] Failed to create topic: {response.error}")
                QMessageBox.critical(
                    self,
                    "Błąd tworzenia wątku",
                    f"Nie udało się utworzyć wątku:\n{response.error}"
                )
    
    def _on_invitations(self):
        """Otwórz dialog zaproszeń - Phase 6 Task 6.2"""
        dialog = InvitationsDialog(self.api_client, self)
        dialog.exec()
    
    # === Handlers dla zdarzeń z panelu drzewa ===
    
    def _handle_group_selected(self, group: dict):
        """Obsługa wyboru grupy"""
        self.conversation_panel.display_group(group)
        logger.debug(f"[TeamWork] Group selected: {group.get('name')}")
    
    def _handle_topic_selected(self, topic: dict):
        """Obsługa wyboru wątku"""
        self.conversation_panel.display_topic(topic)
        logger.debug(f"[TeamWork] Topic selected: {topic.get('title')}")
    
    def _handle_topic_conversations(self, topic: dict):
        """Obsługa wyboru konwersacji w wątku"""
        self.conversation_panel.display_topic_conversations(topic)
    
    def _handle_topic_files(self, topic: dict):
        """Obsługa wyboru plików w wątku"""
        self.conversation_panel.display_topic_files(topic)
    
    def _handle_topic_links(self, topic: dict):
        """Obsługa wyboru linków w wątku"""
        self.conversation_panel.display_topic_links(topic)
    
    def _handle_topic_tasks(self, topic: dict):
        """Obsługa wyboru zadań w wątku"""
        self.conversation_panel.display_topic_tasks(topic)
    
    def _handle_topic_important(self, topic: dict):
        """Obsługa wyboru ważnych elementów w wątku"""
        self.conversation_panel.display_topic_important(topic)
    
    # === Handlers dla zdarzeń z panelu konwersacji ===
    
    def _handle_toggle_important(self, item_type: str, item_id: str, topic_id: str):
        """Oznacza lub usuwa element z listy ważnych"""
        QMessageBox.information(
            self,
            self._t("teamwork.mark_important", "Oznacz jako ważne"),
            f"Przełączono status 'ważne' dla:\nTyp: {item_type}\nID: {item_id}\n"
            f"Zostanie zapisane w bazie danych.",
        )
        # TODO: Implementacja zapisu do bazy danych
        self.data_changed.emit()
    
    def _handle_reply_requested(self, topic: dict, message: dict):
        """Obsługa żądania odpowiedzi na wiadomość"""
        dialog = ReplyDialog(topic.get("title", "Temat"), self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            payload = dialog.get_payload()
            
            # Sprawdź czy mamy API client
            if not self.api_client:
                QMessageBox.warning(
                    self,
                    "Brak połączenia",
                    "Nie można dodać odpowiedzi - brak połączenia z serwerem.\nZaloguj się ponownie."
                )
                return
            
            # Pobierz topic_id
            topic_id = topic.get('id')
            if not topic_id:
                QMessageBox.warning(self, "Błąd", "Nie można dodać wiadomości - brak ID wątku.")
                return
            
            # Wywołaj API do utworzenia wiadomości
            logger.info(f"[TeamWork] Creating message via API in topic {topic_id}")
            response = self.api_client.create_message(
                topic_id=topic_id,
                content=payload['message'],
                background_color=payload.get('background_color'),
                is_important=False
            )
            
            if response.success:
                created_message = response.data
                logger.success(f"[TeamWork] Message created successfully: ID={created_message.get('id')}")
                
                # Odśwież wiadomości w conversation_panel
                if hasattr(self, 'conversation_panel') and hasattr(self.conversation_panel, 'refresh_topic_messages'):
                    self.conversation_panel.refresh_topic_messages(topic_id)
                
                # Emit sygnał o zmianach
                self.data_changed.emit()
                
                # Pokaż potwierdzenie
                QMessageBox.information(
                    self,
                    self._t("teamwork.reply_saved", "Odpowiedź zapisana"),
                    "Odpowiedź została dodana pomyślnie."
                )
            else:
                # Błąd API
                logger.error(f"[TeamWork] Failed to create message: {response.error}")
                QMessageBox.critical(
                    self,
                    "Błąd dodawania odpowiedzi",
                    f"Nie udało się dodać odpowiedzi:\n{response.error}"
                )
    
    def _handle_create_task(self, topic: dict):
        """Obsługa tworzenia nowego zadania"""
        # Pobierz członków grupy z kontekstu
        group = self._find_group_for_topic(topic)
        members = group.get("members", []) if group else []
        
        dialog = TaskDialog(members, topic.get("title", ""), parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            task_data = dialog.get_task_data()
            
            # Sprawdź czy mamy API client
            if not self.api_client:
                QMessageBox.warning(
                    self,
                    "Brak połączenia",
                    "Nie można utworzyć zadania - brak połączenia z serwerem.\nZaloguj się ponownie."
                )
                return
            
            # Pobierz topic_id
            topic_id = topic.get('id')
            if not topic_id:
                QMessageBox.warning(self, "Błąd", "Nie można utworzyć zadania - brak ID wątku.")
                return
            
            # Wywołaj API do utworzenia zadania
            logger.info(f"[TeamWork] Creating task via API: {task_data['title']} in topic {topic_id}")
            response = self.api_client.create_task(
                topic_id=topic_id,
                task_subject=task_data['title'],
                assigned_to=task_data.get('assignee'),
                due_date=task_data.get('deadline').date() if task_data.get('deadline') else None,
                priority='medium'  # Można rozszerzyć dialog o wybór priorytetu
            )
            
            if response.success:
                created_task = response.data
                logger.success(f"[TeamWork] Task created successfully: ID={created_task.get('id')}")
                
                # Emit sygnał o zmianach
                self.data_changed.emit()
                
                # Pokaż potwierdzenie
                QMessageBox.information(
                    self,
                    self._t("teamwork.task_created", "Zadanie utworzone"),
                    f"Zadanie '{task_data['title']}' zostało utworzone pomyślnie.\n\n"
                    f"Odpowiedzialny: {task_data.get('assignee', '(brak)')}"
                )
            else:
                # Błąd API
                logger.error(f"[TeamWork] Failed to create task: {response.error}")
                QMessageBox.critical(
                    self,
                    "Błąd tworzenia zadania",
                    f"Nie udało się utworzyć zadania:\n{response.error}"
                )
    
    def _handle_view_gantt(self, topic: dict):
        """Obsługa wyświetlenia widoku Gantt - Task 3.4"""
        gantt_dialog = QDialog(self)
        gantt_dialog.setWindowTitle(f"{self._t('teamwork.gantt_view', 'Widok Gantt')}: {topic.get('title', 'Temat')}")
        gantt_dialog.resize(900, 600)
        
        layout = QVBoxLayout(gantt_dialog)
        
        # Pobierz zadania z API
        tasks = []
        topic_id = topic.get("id")
        
        if self.api_client and topic_id:
            response = self.api_client.get_topic_tasks(topic_id)
            if response.success:
                tasks = response.data or []
            else:
                # Pokaż błąd
                QMessageBox.warning(
                    gantt_dialog,
                    "Błąd pobierania zadań",
                    f"Nie udało się pobrać zadań dla wykresu Gantt:\n{response.error}"
                )
        
        gantt_widget = GanttChartWidget()
        gantt_widget.api_client = self.api_client  # Przekaż API client
        gantt_widget.set_tasks(tasks, topic.get("title", ""))
        layout.addWidget(gantt_widget)
        
        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(gantt_dialog.reject)
        layout.addWidget(buttons)
        
        gantt_dialog.exec()
    
    # === Utility methods ===
    
    def _find_group_for_topic(self, topic: dict) -> dict | None:
        """Znajduje grupę zawierającą dany temat"""
        topic_id = topic.get("id")
        if not topic_id:
            return None
        for group in self._groups:
            for t in group.get("topics", []):
                if t.get("id") == topic_id:
                    return group
        return None
    
    # === Public API ===
    
    def activate(self):
        """Aktywacja modułu"""
        self.module_activated.emit()
        logger.info("[TeamWork] Module activated")
        
        # Odśwież dane z API przy każdej aktywacji
        if self.api_client:
            self._refresh_groups_from_api()
    
    def deactivate(self):
        """Deaktywacja modułu"""
        self.module_deactivated.emit()
        logger.info("[TeamWork] Module deactivated")
    
    def set_user_data(self, user_data: dict):
        """
        Ustaw dane użytkownika (wywoływane przez main_window po zalogowaniu)
        
        Args:
            user_data: Słownik z danymi użytkownika:
                - id: user ID
                - access_token: JWT token
                - refresh_token: refresh token
                - email, first_name, last_name, etc.
        """
        self.user_data = user_data or {}
        self.user_id = user_data.get('id') if user_data else None
        self.access_token = user_data.get('access_token') if user_data else None
        self.refresh_token = user_data.get('refresh_token') if user_data else None
        
        logger.info(f"[TeamWork] User data set - User ID: {self.user_id}, Token present: {bool(self.access_token)}")
        
        # Utwórz API client jeśli mamy token
        if self.access_token:
            self.api_client = TeamWorkAPIClient(
                base_url=TEAMWORK_API_BASE_URL,
                auth_token=self.access_token,
                refresh_token=self.refresh_token,
                on_token_refreshed=self._on_token_refreshed
            )
            logger.success(f"[TeamWork] API Client initialized with base_url: {TEAMWORK_API_BASE_URL}")
        else:
            self.api_client = None
            logger.warning("[TeamWork] No access token - API Client not initialized")
        
        # Przekaż dane i API client do paneli
        if hasattr(self, 'conversation_panel'):
            self.conversation_panel.set_user_data(user_data)
            if self.api_client:
                self.conversation_panel.api_client = self.api_client
        
        if hasattr(self, 'tree_panel'):
            if self.api_client:
                self.tree_panel.api_client = self.api_client
                # Odśwież grupy z API po zalogowaniu
                self._refresh_groups_from_api()
    
    def _on_token_refreshed(self, new_access_token: str, new_refresh_token: str):
        """
        Callback wywoływany po odświeżeniu tokena przez API client
        
        Args:
            new_access_token: Nowy access token
            new_refresh_token: Nowy refresh token
        """
        self.access_token = new_access_token
        self.refresh_token = new_refresh_token
        
        # Aktualizuj user_data
        if self.user_data:
            self.user_data['access_token'] = new_access_token
            self.user_data['refresh_token'] = new_refresh_token
        
        logger.success("[TeamWork] Tokens refreshed and updated")
        
        # Opcjonalnie: powiadom main_window o nowych tokenach
        # (jeśli main_window ma mechanizm do aktualizacji tokenów)
    
    def _refresh_groups_from_api(self):
        """Odśwież listę grup z API"""
        if not self.api_client:
            logger.warning("[TeamWork] Cannot refresh groups - no API client")
            return
        
        logger.info("[TeamWork] Fetching user groups from API...")
        response = self.api_client.get_user_groups()
        
        if response.success:
            groups_raw = response.data
            logger.success(f"[TeamWork] Fetched {len(groups_raw) if groups_raw else 0} groups from API")
            logger.debug(f"[TeamWork] Raw API response: {groups_raw}")
            
            # Mapuj odpowiedź API do formatu oczekiwanego przez tree_panel
            groups = []
            for g in (groups_raw or []):
                logger.debug(f"[TeamWork] Processing group: {g.get('group_name')} with {len(g.get('topics', []))} topics")
                group = {
                    "id": g.get("group_id"),
                    "name": g.get("group_name"),
                    "description": g.get("description"),
                    "created_by": g.get("created_by"),
                    "is_active": g.get("is_active"),
                    "topics": []
                }
                
                # Mapuj topics
                for t in g.get("topics", []):
                    topic = {
                        "id": t.get("topic_id"),
                        "title": t.get("topic_name"),
                        "group_id": t.get("group_id"),
                        "created_by": t.get("created_by"),
                        "is_active": t.get("is_active")
                    }
                    group["topics"].append(topic)
                
                groups.append(group)
            
            logger.info(f"[TeamWork] Mapped {len(groups)} groups with total topics")
            
            # Zapisz grupy do current_groups (dla dialogów)
            self.current_groups = groups
            
            # Aktualizuj tree panel
            if hasattr(self, 'tree_panel') and groups:
                self.tree_panel.set_groups(groups)
        else:
            logger.error(f"[TeamWork] Failed to fetch groups: {response.error}")
            QMessageBox.warning(
                self,
                "Błąd pobierania grup",
                f"Nie udało się pobrać list grup:\n{response.error}"
            )
    
    def refresh_data(self):
        """Odśwież dane modułu z bazy"""
        # TODO: Implementacja pobierania danych z bazy/API
        logger.info("[TeamWork] Data refreshed")
    
    def get_module_name(self) -> str:
        """Zwraca nazwę modułu"""
        return "TeamWork"
    
    def get_module_icon(self) -> str:
        """Zwraca ikonę modułu"""
        return "👥"
