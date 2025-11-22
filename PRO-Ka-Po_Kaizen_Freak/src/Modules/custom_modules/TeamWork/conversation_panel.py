"""Main content area of the TeamWork module."""

from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QFont, QColor
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from .file_upload_dialog import FileUploadDialog


def get_contrast_text_color(background_hex: str) -> str:
    """
    Oblicza kontrastowy kolor tekstu (czarny lub biały) dla danego tła.
    
    Args:
        background_hex: Kolor tła w formacie #RRGGBB
        
    Returns:
        '#000000' dla jasnego tła lub '#FFFFFF' dla ciemnego tła
    """
    try:
        # Usuń # jeśli istnieje
        hex_color = background_hex.lstrip('#')
        
        # Konwertuj do RGB
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        
        # Oblicz względną jasność (luminance) używając wzoru WCAG
        # https://www.w3.org/TR/WCAG20/#relativeluminancedef
        def to_linear(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4
        
        luminance = 0.2126 * to_linear(r) + 0.7152 * to_linear(g) + 0.0722 * to_linear(b)
        
        # Jeśli jasność > 0.5, użyj czarnego tekstu, w przeciwnym razie białego
        return '#000000' if luminance > 0.5 else '#FFFFFF'
    except:
        # W przypadku błędu zwróć czarny tekst
        return '#000000'


class ConversationPanel(QWidget):
    """Wyświetla tematy, rozmowy oraz metadane."""

    reply_requested = pyqtSignal(dict, dict)
    create_task_requested = pyqtSignal(dict)
    view_gantt_requested = pyqtSignal(dict)
    toggle_important = pyqtSignal(str, str, str)  # type, item_id, topic_id

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("ConversationPanel")
        
        # Przechowuj aktualne topic_id dla uploadu plików
        self.current_topic_id: Optional[int] = None
        self.current_topic_name: Optional[str] = None
        
        # Dane użytkownika i autentykacja
        self.user_data = {}
        self.user_id: Optional[str] = None
        self.access_token: Optional[str] = None
        self.api_client = None  # TeamWorkAPIClient - ustawiony przez teamwork_module

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.scroll_area = QScrollArea()
        self.scroll_area.setObjectName("conversationScrollArea")
        self.scroll_area.setWidgetResizable(True)
        root_layout.addWidget(self.scroll_area)

        self._content_widget = QWidget()
        self._content_widget.setObjectName("conversationContent")
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(12, 12, 12, 12)
        self._content_layout.setSpacing(12)
        self.scroll_area.setWidget(self._content_widget)

        self._set_placeholder("Wybierz grupę lub temat, aby rozpocząć pracę.")

    def _clear_content(self) -> None:
        while self._content_layout.count():
            item = self._content_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

    def _set_placeholder(self, text: str) -> None:
        self._clear_content()
        label = QLabel(text)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("color: #777; font-size: 12pt;")
        self._content_layout.addWidget(label)
        self._content_layout.addStretch()

    def display_group(self, group: dict) -> None:
        self._clear_content()

        header = QLabel(group.get("name", "Grupa"))
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        self._content_layout.addWidget(header)

        if group.get("description"):
            desc = QLabel(group["description"])
            desc.setWordWrap(True)
            self._content_layout.addWidget(desc)

        members = group.get("members", [])
        if members:
            members_label = QLabel("Członkowie: " + ", ".join(members))
            self._content_layout.addWidget(members_label)

        topics = group.get("topics", [])
        info = QLabel(f"Liczba tematów: {len(topics)}")
        info.setStyleSheet("color: #555;")
        self._content_layout.addWidget(info)

        self._content_layout.addStretch()

    def display_topic(self, topic: dict) -> None:
        """Wyświetla szczegóły tematu - pobiera dane z API"""
        self._clear_content()
        
        # Zapisz current topic dla uploadu plików
        self.current_topic_id = topic.get("id") or topic.get("topic_id")
        self.current_topic_name = topic.get("title") or topic.get("topic_name", "Temat")
        
        # Pobierz wiadomości z API
        if self.api_client and self.current_topic_id:
            try:
                topic_id_int = int(self.current_topic_id)
                response = self.api_client.get_topic_messages(topic_id_int)
                if response.success:
                    topic["messages"] = response.data or []
            except (ValueError, TypeError):
                pass  # Mock topic - użyj lokalnych danych
        
        self._content_layout.addWidget(self._build_topic_header(topic))
        self._add_members_section(topic)  # Phase 6 Task 6.4
        self._add_plans_section(topic.get("plans", []))
        self._add_files_section(topic.get("files", []))
        self._add_links_section(topic.get("links", []))
        self._add_messages_section(topic)
        self._content_layout.addStretch()

    def display_topic_conversations(self, topic: dict) -> None:
        """Wyświetla rozmowy/wiadomości tematu - pobiera z API"""
        self._clear_content()
        title = QLabel(f"Rozmowy w temacie: {topic.get('title', 'Temat')}")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self._content_layout.addWidget(title)
        
        # Pobierz wiadomości z API
        messages = []
        topic_id = topic.get("id") or topic.get("topic_id")
        
        if self.api_client and topic_id:
            try:
                topic_id_int = int(topic_id)
                response = self.api_client.get_topic_messages(topic_id_int)
                if response.success:
                    messages = response.data or []
                else:
                    error_label = QLabel(f"⚠️ Błąd pobierania wiadomości: {response.error}")
                    error_label.setStyleSheet("color: #cc0000; padding: 8px;")
                    self._content_layout.addWidget(error_label)
            except (ValueError, TypeError):
                # Mock topic - użyj lokalnych danych
                messages = topic.get("messages", [])
        
        # Aktualizuj topic z nowymi wiadomościami
        topic["messages"] = messages
        
        self._add_messages_section(topic)
        self._content_layout.addStretch()

    def display_topic_files(self, topic: dict) -> None:
        """Wyświetla pliki tematu - Task 4.1: Pobiera z API"""
        self._clear_content()
        title = QLabel(f"Pliki w temacie: {topic.get('title', 'Temat')}")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self._content_layout.addWidget(title)
        
        # Pobierz pliki z API
        files = []
        topic_id = topic.get("id") or topic.get("topic_id")
        
        if self.api_client and topic_id:
            # Sprawdź czy topic_id jest numeryczny (tylko wtedy wywołaj API)
            try:
                topic_id_int = int(topic_id)
                response = self.api_client.get_topic_files(topic_id_int)
                if response.success:
                    files = response.data or []
                else:
                    # Pokaż błąd, ale kontynuuj z pustą listą
                    error_label = QLabel(f"⚠️ Błąd pobierania plików: {response.error}")
                    error_label.setStyleSheet("color: #cc0000; padding: 8px;")
                    self._content_layout.addWidget(error_label)
            except (ValueError, TypeError):
                # Mock topic - użyj lokalnych danych
                files = topic.get("files", [])
        
        self._add_files_section(files, topic.get("id", ""))
        self._content_layout.addStretch()

    def display_topic_links(self, topic: dict) -> None:
        self._clear_content()
        title = QLabel(f"Linki w temacie: {topic.get('title', 'Temat')}")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self._content_layout.addWidget(title)
        self._add_links_section(topic.get("links", []), topic.get("id", ""))
        self._content_layout.addStretch()

    def display_topic_tasks(self, topic: dict) -> None:
        self._clear_content()
        title = QLabel(f"Zadania w temacie: {topic.get('title', 'Temat')}")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self._content_layout.addWidget(title)

        # Przyciski akcji
        btn_layout = QHBoxLayout()
        add_task_btn = QPushButton("➕ Dodaj zadanie")
        add_task_btn.clicked.connect(lambda: self.create_task_requested.emit(topic))
        btn_layout.addWidget(add_task_btn)

        view_gantt_btn = QPushButton("📊 Widok Gantt")
        view_gantt_btn.clicked.connect(lambda: self.view_gantt_requested.emit(topic))
        btn_layout.addWidget(view_gantt_btn)
        btn_layout.addStretch()

        self._content_layout.addLayout(btn_layout)

        # Pobierz zadania z API
        tasks = []
        topic_id = topic.get("id") or topic.get("topic_id")
        
        if self.api_client and topic_id:
            # Wywołaj API dla każdego topic_id (zarówno int jak i UUID string)
            try:
                # API może przyjąć zarówno int jak i string
                topic_id_value = int(topic_id) if str(topic_id).isdigit() else topic_id
                response = self.api_client.get_topic_tasks(topic_id_value)
                if response.success:
                    tasks = response.data or []
                else:
                    # Pokaż błąd, ale kontynuuj z pustą listą
                    error_label = QLabel(f"⚠️ Błąd pobierania zadań: {response.error}")
                    error_label.setStyleSheet("color: #cc0000; padding: 8px;")
                    self._content_layout.addWidget(error_label)
            except Exception as e:
                # W razie jakiegokolwiek błędu, pokaż go i użyj pustej listy
                error_label = QLabel(f"⚠️ Błąd API: {str(e)}")
                error_label.setStyleSheet("color: #cc0000; padding: 8px;")
                self._content_layout.addWidget(error_label)
                tasks = []
        
        # Tabela zadań
        if not tasks:
            placeholder = QLabel("Brak zadań w tym temacie.")
            placeholder.setStyleSheet("color: #666;")
            self._content_layout.addWidget(placeholder)
        else:
            from .task_widgets import TaskTableWidget
            task_widget = TaskTableWidget(self)
            task_widget.api_client = self.api_client  # Przekaż API client
            task_widget.set_tasks(tasks, topic.get("title", ""), topic.get("id", ""))
            task_widget.toggle_important.connect(self.toggle_important.emit)
            # Podłącz sygnał zmiany statusu zadania - odśwież listę po zmianie
            task_widget.task_completed_changed.connect(lambda: self.display_topic_tasks(topic))
            self._content_layout.addWidget(task_widget)

        self._content_layout.addStretch()

    def display_topic_important(self, topic: dict) -> None:
        """
        Wyświetla wszystkie elementy oznaczone jako ważne w temacie - Task 4.5.
        Pobiera dane z API i filtruje ważne elementy.
        """
        self._clear_content()
        title = QLabel(f"⭐ Ważne w temacie: {topic.get('title', 'Temat')}")
        title.setStyleSheet("font-size: 14pt; font-weight: bold;")
        self._content_layout.addWidget(title)
        
        topic_id = topic.get("id") or topic.get("topic_id")
        
        # Pobierz wszystkie dane z API
        important_messages = []
        important_files = []
        important_tasks = []
        
        if self.api_client and topic_id:
            # Sprawdź czy topic_id jest numeryczny
            try:
                topic_id_int = int(topic_id)
                
                # Pobierz wiadomości i filtruj ważne
                messages_response = self.api_client.get_topic_messages(topic_id_int)
                if messages_response.success:
                    all_messages = messages_response.data or []
                    important_messages = [msg for msg in all_messages if msg.get("is_important", False)]
                
                # Pobierz pliki i filtruj ważne
                files_response = self.api_client.get_topic_files(topic_id_int)
                if files_response.success:
                    all_files = files_response.data or []
                    important_files = [f for f in all_files if f.get("is_important", False)]
                
                # Pobierz zadania i filtruj ważne
                tasks_response = self.api_client.get_topic_tasks(topic_id_int)
                if tasks_response.success:
                    all_tasks = tasks_response.data or []
                    important_tasks = [task for task in all_tasks if task.get("is_important", False)]
            except (ValueError, TypeError):
                # Mock topic - użyj lokalnych danych
                all_messages = topic.get("messages", [])
                important_messages = [msg for msg in all_messages if msg.get("important", False)]
                all_files = topic.get("files", [])
                important_files = [f for f in all_files if f.get("important", False)]
                all_tasks = topic.get("tasks", [])
                important_tasks = [task for task in all_tasks if task.get("important", False)]
        
        # Wyświetl ważne wiadomości
        if important_messages:
            header = QLabel("Ważne wiadomości")
            header.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
            self._content_layout.addWidget(header)
            for msg in important_messages:
                self._content_layout.addWidget(self._build_message_card(topic, msg))

        # Wyświetl ważne pliki
        if important_files:
            header = QLabel("Ważne pliki")
            header.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
            self._content_layout.addWidget(header)
            for file_entry in important_files:
                self._content_layout.addWidget(self._build_file_card(file_entry, topic.get("id", "")))

        # Wyświetl ważne zadania
        if important_tasks:
            header = QLabel("Ważne zadania")
            header.setStyleSheet("font-weight: bold; font-size: 12pt; margin-top: 10px;")
            self._content_layout.addWidget(header)
            from .task_widgets import TaskTableWidget
            task_widget = TaskTableWidget(self)
            task_widget.api_client = self.api_client
            task_widget.set_tasks(important_tasks, topic.get("title", ""), topic.get("id", ""))
            # Odśwież po zmianie
            task_widget.task_completed_changed.connect(lambda: self.display_topic_important(topic))
            self._content_layout.addWidget(task_widget)

        if not (important_messages or important_files or important_tasks):
            placeholder = QLabel("Brak elementów oznaczonych jako ważne.")
            placeholder.setStyleSheet("color: #666; margin-top: 20px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._content_layout.addWidget(placeholder)

        self._content_layout.addStretch()

    def _build_topic_header(self, topic: dict) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        # Header z tytułem i przyciskami
        header_layout = QHBoxLayout()
        
        title = QLabel(topic.get("title", "Temat"))
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        title.setFont(title_font)
        header_layout.addWidget(title)
        
        header_layout.addStretch()
        
        # Przycisk udostępniania - Phase 6 Task 6.1
        share_btn = QPushButton("🔗 Udostępnij")
        share_btn.setToolTip("Wygeneruj link współdzielenia dla tego topicu")
        share_btn.clicked.connect(lambda: self._share_topic(topic))
        header_layout.addWidget(share_btn)
        
        # Przycisk zarządzania członkami - Phase 6 Task 6.3
        members_btn = QPushButton("👥 Członkowie")
        members_btn.setToolTip("Zarządzaj członkami i uprawnieniami")
        members_btn.clicked.connect(lambda: self._manage_members(topic))
        header_layout.addWidget(members_btn)
        
        layout.addLayout(header_layout)

        owner = topic.get("owner")
        created_at = topic.get("created_at")
        details = []
        if owner:
            details.append(f"Właściciel: {owner}")
        if isinstance(created_at, datetime):
            details.append(f"Data utworzenia: {self._format_dt(created_at)}")
        if details:
            layout.addWidget(QLabel(" | ".join(details)))

        return widget
    
    def _add_members_section(self, topic: dict) -> None:
        """
        Wyświetla sekcję z członkami topicu - Phase 6 Task 6.4
        Pokazuje listę członków, ich role i status online
        """
        if not self.api_client:
            return
        
        topic_id = topic.get("id") or topic.get("topic_id")
        if not topic_id:
            return
        
        # Sprawdź czy topic_id jest numeryczny (z API), jeśli nie - pomiń (mock data)
        try:
            topic_id_int = int(topic_id)
        except (ValueError, TypeError):
            # Mock topic z lokalnych danych - nie ma członków z API
            return
        
        # Header z przyciskiem zarządzania
        header_layout = QHBoxLayout()
        header = QLabel("👥 Członkowie")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        # Przycisk zarządzania członkami
        manage_btn = QPushButton("⚙️ Zarządzaj")
        manage_btn.setToolTip("Zarządzaj członkami i uprawnieniami")
        manage_btn.clicked.connect(lambda: self._manage_members(topic))
        header_layout.addWidget(manage_btn)
        
        header_widget = QWidget()
        header_widget.setLayout(header_layout)
        self._content_layout.addWidget(header_widget)
        
        # Pobierz listę członków z API
        response = self.api_client.get_topic_members(topic_id_int)
        
        if not response.success:
            error_label = QLabel(f"Nie udało się pobrać listy członków: {response.error}")
            error_label.setStyleSheet("color: #dc3545;")
            self._content_layout.addWidget(error_label)
            return
        
        members = response.data or []
        
        if not members:
            placeholder = QLabel("Brak członków w tym topicu.")
            placeholder.setStyleSheet("color: #666;")
            self._content_layout.addWidget(placeholder)
            return
        
        # Lista członków (max 5 widocznych, reszta w dialogu)
        members_to_show = members[:5]
        
        for member in members_to_show:
            member_widget = self._build_member_card(member)
            self._content_layout.addWidget(member_widget)
        
        # Jeśli jest więcej członków, pokaż link "Zobacz wszystkich"
        if len(members) > 5:
            more_label = QLabel(f"<a href='#'>+ {len(members) - 5} więcej członków...</a>")
            more_label.setStyleSheet("color: #007bff; margin-left: 10px;")
            more_label.linkActivated.connect(lambda: self._manage_members(topic))
            self._content_layout.addWidget(more_label)
    
    def _build_member_card(self, member: dict) -> QWidget:
        """
        Tworzy kartę pojedynczego członka.
        
        Args:
            member: Dane członka z API (email, role, is_online, joined_at)
        
        Returns:
            Widget z informacjami o członku
        """
        widget = QFrame()
        widget.setFrameShape(QFrame.Shape.StyledPanel)
        widget.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 4px;
                padding: 8px;
            }
        """)
        
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(8, 6, 8, 6)
        
        # Status online
        is_online = member.get("is_online", False)
        status_icon = QLabel("🟢" if is_online else "⚪")
        status_icon.setToolTip("Online" if is_online else "Offline")
        layout.addWidget(status_icon)
        
        # Email/nazwa użytkownika
        email = member.get("email", "Unknown")
        username = member.get("username", email.split("@")[0] if "@" in email else email)
        name_label = QLabel(username)
        name_label.setStyleSheet("font-weight: bold;")
        layout.addWidget(name_label)
        
        layout.addStretch()
        
        # Rola z ikoną
        role = member.get("role", "member")
        role_icon = {
            'owner': '👨‍💼',
            'admin': '👑',
            'member': '✏️',
            'viewer': '👁️'
        }.get(role, '✏️')
        
        role_label = QLabel(f"{role_icon} {role.capitalize()}")
        role_label.setStyleSheet("color: #666; font-size: 9pt;")
        role_label.setToolTip(f"Rola: {role}")
        layout.addWidget(role_label)
        
        return widget

    def _add_plans_section(self, plans: Iterable[str]) -> None:
        plan_list = list(plans)
        if not plan_list:
            return

        header = QLabel("Plan działań")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        self._content_layout.addWidget(header)

        widget = QListWidget()
        for plan_entry in plan_list:
            QListWidgetItem(str(plan_entry), widget)
        self._content_layout.addWidget(widget)

    def _add_files_section(self, files: Iterable[dict], topic_id: str = "") -> None:
        file_entries = list(files)
        
        # Header z przyciskiem Upload
        header_layout = QHBoxLayout()
        header = QLabel("Załączone pliki")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        header_layout.addWidget(header)
        header_layout.addStretch()
        
        # Przycisk Upload (dostępny tylko gdy mamy topic_id)
        if self.current_topic_id:
            upload_btn = QPushButton("📤 Upload File")
            upload_btn.setObjectName("uploadFileButton")
            upload_btn.clicked.connect(self._open_file_upload_dialog)
            header_layout.addWidget(upload_btn)
        
        header_container = QWidget()
        header_container.setLayout(header_layout)
        self._content_layout.addWidget(header_container)
        
        # Lista plików lub placeholder
        if not file_entries:
            placeholder = QLabel("Brak załączonych plików.")
            placeholder.setStyleSheet("color: #666;")
            self._content_layout.addWidget(placeholder)
        else:
            for file_entry in file_entries:
                self._content_layout.addWidget(self._build_file_card(file_entry, topic_id))

    def _add_links_section(self, links: Iterable[dict], topic_id: str = "") -> None:
        link_entries = list(links)
        if not link_entries:
            placeholder = QLabel("Brak linków.")
            placeholder.setStyleSheet("color: #666;")
            self._content_layout.addWidget(placeholder)
            return

        header = QLabel("Załączone linki")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        self._content_layout.addWidget(header)

        for link in link_entries:
            widget = QFrame()
            widget.setFrameShape(QFrame.Shape.StyledPanel)
            layout = QVBoxLayout(widget)
            layout.setContentsMargins(8, 8, 8, 8)
            layout.addWidget(QLabel(str(link.get("title", link.get("url", "Link")))))
            layout.addWidget(QLabel(str(link.get("url", ""))))
            meta = self._format_meta(str(link.get("author", "")), link.get("added_at"))
            if meta:
                meta_label = QLabel(meta)
                meta_label.setStyleSheet("color: #666; font-size: 9pt;")
                layout.addWidget(meta_label)
            
            # Przycisk oznaczania jako ważne
            if topic_id:
                important_btn = QPushButton("⭐ Ważne" if link.get("important") else "☆ Oznacz jako ważne")
                important_btn.clicked.connect(
                    lambda _checked=False, lid=link.get("id", ""), tid=topic_id: 
                    self.toggle_important.emit("link", lid, tid)
                )
                layout.addWidget(important_btn)
            
            self._content_layout.addWidget(widget)

    def _add_messages_section(self, topic: dict) -> None:
        messages = topic.get("messages", [])
        if not messages:
            placeholder = QLabel("Brak wiadomości w tym temacie.")
            placeholder.setStyleSheet("color: #666;")
            self._content_layout.addWidget(placeholder)
            return

        header = QLabel("Rozmowy")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        self._content_layout.addWidget(header)

        for message in messages:
            self._content_layout.addWidget(self._build_message_card(topic, message))

    def _build_message_card(self, topic: dict, message: dict) -> QWidget:
        card = QFrame()
        card.setFrameShape(QFrame.Shape.StyledPanel)
        
        # Ustaw kolor tła z wiadomości
        bg_color = message.get("background_color", "#FFFFFF")
        
        # Oblicz kontrast - wybierz czarny lub biały tekst
        text_color = get_contrast_text_color(bg_color)
        
        card.setStyleSheet(f"""
            QFrame {{ 
                background-color: {bg_color}; 
                color: {text_color};
            }}
            QLabel {{
                color: {text_color};
            }}
        """)
        
        layout = QVBoxLayout(card)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        header_layout = QHBoxLayout()
        author_label = QLabel(message.get("author", "Użytkownik"))
        author_label.setStyleSheet(f"font-weight: bold; color: {text_color};")
        header_layout.addWidget(author_label)
        header_layout.addStretch()
        posted_at = message.get("posted_at")
        header_layout.addWidget(QLabel(self._format_dt(posted_at) if posted_at else ""))
        layout.addLayout(header_layout)

        body = QLabel(message.get("content", ""))
        body.setWordWrap(True)
        layout.addWidget(body)

        files = message.get("files", [])
        if files:
            files_header = QLabel("Załączone pliki:")
            files_header.setStyleSheet("font-weight: bold;")
            layout.addWidget(files_header)
            for file_entry in files:
                layout.addWidget(self._build_file_card(file_entry))

        links = message.get("links", [])
        if links:
            links_header = QLabel("Linki:")
            links_header.setStyleSheet("font-weight: bold;")
            layout.addWidget(links_header)
            for link in links:
                layout.addWidget(self._build_link_row(link))

        # Przyciski akcji
        actions_layout = QHBoxLayout()
        
        reply_btn = QPushButton("Odpowiedz")
        reply_btn.clicked.connect(lambda _checked=False, t=topic, m=message: self.reply_requested.emit(t, m))
        actions_layout.addWidget(reply_btn)
        
        # Important toggle (Task 4.4)
        message_id = message.get("message_id") or message.get("id", "")
        is_important = message.get("is_important") or message.get("important", False)
        important_btn = QPushButton("⭐ Ważna" if is_important else "☆ Oznacz jako ważną")
        important_btn.clicked.connect(
            lambda _checked=False, mid=str(message_id), tid=str(topic.get("id", "")): 
            self._toggle_message_important(mid, not is_important, tid)
        )
        actions_layout.addWidget(important_btn)
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)

        return card

    def _build_file_card(self, file_entry: Dict[str, object], topic_id: str = "") -> QWidget:
        widget = QFrame()
        widget.setFrameShape(QFrame.Shape.StyledPanel)
        widget.setObjectName("fileCard")
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(4)

        # Nazwa pliku jako link
        file_name = file_entry.get("file_name") or file_entry.get("path", "plik")
        download_url = file_entry.get("download_url", "")
        
        file_label = QLabel(f"📎 {file_name}")
        file_label.setStyleSheet("font-weight: bold; color: #0066cc;")
        layout.addWidget(file_label)
        
        # Rozmiar pliku i typ
        file_size = file_entry.get("file_size")
        content_type = file_entry.get("content_type")
        if file_size or content_type:
            info_parts = []
            if file_size:
                info_parts.append(self._format_file_size(file_size))
            if content_type:
                info_parts.append(content_type)
            info_label = QLabel(" | ".join(info_parts))
            info_label.setStyleSheet("color: #666; font-size: 9pt;")
            layout.addWidget(info_label)
        
        # Notatka (jeśli jest)
        note = file_entry.get("note")
        if note:
            note_label = QLabel(str(note))
            note_label.setWordWrap(True)
            layout.addWidget(note_label)

        # Metadane (autor, data)
        uploaded_by = file_entry.get("uploaded_by") or file_entry.get("author")
        uploaded_at = file_entry.get("uploaded_at") or file_entry.get("added_at")
        meta = self._format_meta(uploaded_by, uploaded_at)
        if meta:
            meta_label = QLabel(meta)
            meta_label.setStyleSheet("color: #666; font-size: 9pt;")
            layout.addWidget(meta_label)
        
        # Przyciski akcji
        actions_layout = QHBoxLayout()
        
        # Download button
        if download_url:
            download_btn = QPushButton("⬇️ Pobierz")
            download_btn.setObjectName("downloadButton")
            download_btn.clicked.connect(
                lambda: self._download_file(download_url, file_name)
            )
            actions_layout.addWidget(download_btn)
        
        # Important toggle (Task 4.3)
        file_id = file_entry.get("file_id") or file_entry.get("id", "")
        is_important = file_entry.get("is_important", False)
        important_btn = QPushButton("⭐ Ważny" if is_important else "☆ Oznacz jako ważny")
        important_btn.clicked.connect(
            lambda _checked=False, fid=str(file_id): 
            self._toggle_file_important(fid, not is_important, topic_id)
        )
        actions_layout.addWidget(important_btn)
        
        # Delete button (Task 4.2)
        if file_id:
            delete_btn = QPushButton("🗑️ Usuń")
            delete_btn.setObjectName("deleteFileButton")
            delete_btn.setStyleSheet("color: #cc0000;")
            delete_btn.clicked.connect(
                lambda _checked=False, fid=str(file_id): 
                self._delete_file(fid, file_name, topic_id)
            )
            actions_layout.addWidget(delete_btn)
        
        actions_layout.addStretch()
        
        layout.addLayout(actions_layout)

        return widget

    def _build_link_row(self, link: Dict[str, object]) -> QWidget:
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        layout.addWidget(QLabel(link.get("title", link.get("url", "Link"))))
        layout.addWidget(QLabel(link.get("url", "")))
        meta = self._format_meta(link.get("author"), link.get("added_at"))
        if meta:
            meta_label = QLabel(meta)
            meta_label.setStyleSheet("color: #666; font-size: 9pt;")
            layout.addWidget(meta_label)

        return widget
    
    # ========================================================================
    # FILE UPLOAD INTEGRATION
    # ========================================================================
    
    def set_user_data(self, user_data: dict):
        """Ustaw dane użytkownika dla uploadu plików"""
        self.user_data = user_data or {}
        self.user_id = user_data.get('id') if user_data else None
        self.access_token = user_data.get('access_token') if user_data else None
    
    def _format_file_size(self, size_bytes: int) -> str:
        """Formatuj rozmiar pliku do czytelnej postaci"""
        size = float(size_bytes)
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} TB"
    
    def _download_file(self, download_url: str, file_name: str):
        """Pobierz plik z Backblaze B2"""
        import webbrowser
        try:
            # Otwórz URL w przeglądarce (automatyczny download)
            webbrowser.open(download_url)
        except Exception as e:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Błąd pobierania",
                f"Nie można otworzyć pliku:\n{str(e)}"
            )
    
    def _delete_file(self, file_id: str, file_name: str, topic_id: str):
        """
        Usuń plik - Task 4.2.
        
        Args:
            file_id: ID pliku do usunięcia
            file_name: Nazwa pliku (do potwierdzenia)
            topic_id: ID topicu (do odświeżenia widoku)
        """
        if not self.api_client:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Brak połączenia",
                "Nie można usunąć pliku - brak połączenia z API."
            )
            return
        
        # Potwierdzenie
        from PyQt6.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Potwierdzenie usunięcia",
            f"Czy na pewno chcesz usunąć plik:\n{file_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Walidacja file_id
        try:
            file_id_int = int(file_id)
        except (ValueError, TypeError):
            QMessageBox.warning(
                self,
                "Błąd",
                "Nie można usunąć pliku - nieprawidłowe ID."
            )
            return
        
        # Wywołaj API
        response = self.api_client.delete_file(file_id_int)
        
        if response.success:
            QMessageBox.information(
                self,
                "Sukces",
                f"Plik '{file_name}' został usunięty."
            )
            # Odśwież widok plików
            if self.current_topic_id and self.current_topic_name:
                topic = {
                    'id': self.current_topic_id,
                    'title': self.current_topic_name
                }
                self.display_topic_files(topic)
        else:
            QMessageBox.critical(
                self,
                "Błąd usuwania",
                f"Nie udało się usunąć pliku:\n{response.error}"
            )
    
    def _toggle_file_important(self, file_id: str, important: bool, topic_id: str):
        """
        Przełącz status ważności pliku - Task 4.3.
        
        Args:
            file_id: ID pliku
            important: Nowy status ważności
            topic_id: ID topicu (do odświeżenia widoku)
        """
        if not self.api_client:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Brak połączenia",
                "Nie można oznaczyć pliku - brak połączenia z API."
            )
            return
        
        # Walidacja file_id
        try:
            file_id_int = int(file_id)
        except (ValueError, TypeError):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Błąd",
                "Nie można oznaczyć pliku - nieprawidłowe ID."
            )
            return
        
        # Wywołaj API
        response = self.api_client.mark_file_important(file_id_int, important)
        
        if response.success:
            # Odśwież widok plików
            if self.current_topic_id and self.current_topic_name:
                topic = {
                    'id': self.current_topic_id,
                    'title': self.current_topic_name
                }
                self.display_topic_files(topic)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Błąd aktualizacji",
                f"Nie udało się oznaczyć pliku jako {'ważny' if important else 'nieważny'}:\n{response.error}"
            )
    
    def _toggle_message_important(self, message_id: str, important: bool, topic_id: str):
        """
        Przełącz status ważności wiadomości - Task 4.4.
        
        Args:
            message_id: ID wiadomości
            important: Nowy status ważności
            topic_id: ID topicu (do odświeżenia widoku)
        """
        if not self.api_client:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Brak połączenia",
                "Nie można oznaczyć wiadomości - brak połączenia z API."
            )
            return
        
        # Walidacja message_id
        try:
            message_id_int = int(message_id)
        except (ValueError, TypeError):
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Błąd",
                "Nie można oznaczyć wiadomości - nieprawidłowe ID."
            )
            return
        
        # Wywołaj API
        response = self.api_client.mark_message_important(message_id_int, important)
        
        if response.success:
            # Odśwież widok wiadomości
            if self.current_topic_id and self.current_topic_name:
                topic = {
                    'id': self.current_topic_id,
                    'title': self.current_topic_name
                }
                self.display_topic_conversations(topic)
        else:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.critical(
                self,
                "Błąd aktualizacji",
                f"Nie udało się oznaczyć wiadomości jako {'ważna' if important else 'nieważna'}:\n{response.error}"
            )
    
    def _open_file_upload_dialog(self):
        """Otwórz dialog uploadu pliku"""
        if not self.current_topic_id or not self.current_topic_name:
            return
        
        # Pobierz API URL z config
        from ...config import TEAMWORK_API_BASE_URL
        
        # Sprawdź czy user jest zalogowany
        if not self.access_token:
            from PyQt6.QtWidgets import QMessageBox
            QMessageBox.warning(
                self,
                "Brak autoryzacji",
                "Musisz być zalogowany, aby przesyłać pliki."
            )
            return
        
        dialog = FileUploadDialog(
            topic_id=self.current_topic_id,
            topic_name=self.current_topic_name,
            api_url=TEAMWORK_API_BASE_URL,
            auth_token=self.access_token,
            parent=self
        )
        
        # Połącz signal uploadu
        dialog.file_uploaded.connect(self._on_file_uploaded)
        
        dialog.exec()
    
    def _on_file_uploaded(self, file_data: dict):
        """
        Callback po udanym uploadzie pliku - Task 4.1: Auto-refresh.
        
        Args:
            file_data: Dane uploadowanego pliku
        """
        print(f"Plik zauploadowany: {file_data}")
        
        # Odśwież widok plików dla aktualnego topicu
        if self.current_topic_id and self.current_topic_name:
            topic = {
                'id': self.current_topic_id,
                'title': self.current_topic_name
            }
            self.display_topic_files(topic)
    
    def refresh_topic_messages(self, topic_id: int):
        """
        Odśwież wiadomości w wątku po dodaniu nowej.
        
        Args:
            topic_id: ID wątku do odświeżenia
        """
        if not self.api_client:
            print("[ConversationPanel] Cannot refresh - no API client")
            return
        
        # Pobierz wiadomości z API
        response = self.api_client.get_topic_messages(topic_id)
        
        if response.success and response.data:
            messages = response.data
            
            # Znajdź topic w aktualnie wyświetlanym widoku
            # TODO: Zaimplementować pełne odświeżenie widoku topic
            # Na razie wystarczy info w konsoli
            print(f"[ConversationPanel] Refreshed {len(messages)} messages for topic {topic_id}")
            
            # Jeśli ten topic jest aktualnie wyświetlany, odśwież go
            if self.current_topic_id == topic_id:
                # TODO: Re-render conversation view with new messages
                pass
        else:
            print(f"[ConversationPanel] Failed to refresh messages: {response.error if response else 'No response'}")

    def _share_topic(self, topic: dict):
        """
        Otwiera dialog współdzielenia topicu - Phase 6 Task 6.1
        
        Args:
            topic: Dane topicu
        """
        from .dialogs import ShareLinkDialog
        
        dialog = ShareLinkDialog(topic, self.api_client, parent=self)
        dialog.exec()
    
    def _manage_members(self, topic: dict):
        """
        Otwiera dialog zarządzania członkami topicu - Phase 6 Task 6.3
        """
        from .dialogs import MembersManagementDialog

        dialog = MembersManagementDialog(topic, self.api_client, parent=self)
        if dialog.exec():
            # Odśwież widok po zmianach
            self.display_topic(topic)

    @staticmethod
    def _format_meta(author: Optional[str], when: Optional[datetime]) -> str:
        pieces: List[str] = []
        if author:
            pieces.append(f"Od: {author}")
        if isinstance(when, datetime):
            pieces.append(f"Dodano: {ConversationPanel._format_dt(when)}")
        return " | ".join(pieces)

    @staticmethod
    def _format_dt(value: datetime) -> str:
        return value.strftime("%Y-%m-%d %H:%M")
