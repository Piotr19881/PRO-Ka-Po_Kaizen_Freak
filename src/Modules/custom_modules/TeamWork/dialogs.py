"""Placeholder dialogs used by the TeamWork prototype."""

from __future__ import annotations

from typing import List, Dict

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QTextEdit,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QGroupBox,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QInputDialog,
    QScrollArea,
    QWidget,
)
from PyQt6.QtGui import QColor


class _BaseInfoDialog(QDialog):
    def __init__(self, title: str, message: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.addWidget(QLabel(message))

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)


class MyGroupsDialog(_BaseInfoDialog):
    def __init__(self, parent=None) -> None:
        super().__init__("Moje grupy", "Lista grup pojawi się w kolejnej iteracji.", parent)


class CreateGroupDialog(QDialog):
    """Prosty dialog tworzenia nowej grupy roboczej."""
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Utwórz nową grupę")
        self.setModal(True)
        self.setMinimumSize(500, 350)
        
        # Dane zespołów
        self.teams: Dict[str, List[str]] = {}
        self._load_teams_data()
        
        self._setup_ui()

    def _load_teams_data(self):
        """Ładuje dane zespołów z modułu zarządzania."""
        # TODO: W przyszłości pobrać z bazy danych
        self.teams = {
            "Marketing 2025": ["anna@example.com", "bartek@example.com", "celina@example.com"],
            "Zespół developerski": ["ewa@example.com", "filip@example.com", "grzegorz@example.com"],
            "Zarząd": ["anna@example.com", "ewa@example.com"],
        }

    def _setup_ui(self):
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)
        
        # Informacja
        info_label = QLabel("Grupa to przestrzeń współpracy dla zespołu. W grupie będziesz mógł tworzyć wątki tematyczne.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # Nazwa grupy
        layout.addWidget(QLabel("<b>Nazwa grupy:</b>"))
        self.group_name_edit = QLineEdit()
        self.group_name_edit.setPlaceholderText("Np. Projekt Q1 2025, Marketing 2025")
        layout.addWidget(self.group_name_edit)
        
        # Opis grupy
        layout.addWidget(QLabel("<b>Opis grupy (opcjonalnie):</b>"))
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Krótki opis celu i zakresu grupy...")
        self.description_edit.setMaximumHeight(80)
        layout.addWidget(self.description_edit)
        
        # Wybór zespołów
        teams_group = QGroupBox("Członkowie - wybierz zespoły")
        teams_layout = QVBoxLayout(teams_group)
        
        self.teams_list = QListWidget()
        self.teams_list.setSelectionMode(QListWidget.SelectionMode.MultiSelection)
        for team_name in sorted(self.teams.keys()):
            member_count = len(self.teams[team_name])
            item = QListWidgetItem(f"📋 {team_name} ({member_count} członków)")
            item.setData(Qt.ItemDataRole.UserRole, team_name)
            self.teams_list.addItem(item)
        teams_layout.addWidget(self.teams_list)
        
        layout.addWidget(teams_group)
        
        layout.addStretch()
        
        # Przyciski
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    def _validate_and_accept(self):
        """Waliduje dane i akceptuje dialog."""
        if not self.group_name_edit.text().strip():
            QMessageBox.warning(self, "Błąd", "Podaj nazwę grupy.")
            return
        
        selected_teams = [item.data(Qt.ItemDataRole.UserRole) for item in self.teams_list.selectedItems()]
        if not selected_teams:
            reply = QMessageBox.question(
                self,
                "Brak członków",
                "Nie wybrano żadnego zespołu. Czy chcesz utworzyć pustą grupę?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        self.accept()

    def get_group_data(self) -> dict:
        """Zwraca dane wprowadzone w formularzu."""
        # Zbierz wszystkich członków z wybranych zespołów
        members_emails = set()
        selected_teams = [item.data(Qt.ItemDataRole.UserRole) for item in self.teams_list.selectedItems()]
        for team_name in selected_teams:
            members_emails.update(self.teams.get(team_name, []))
        
        return {
            "name": self.group_name_edit.text().strip(),
            "description": self.description_edit.toPlainText().strip(),
            "members": sorted(list(members_emails)),
            "selected_teams": selected_teams,
        }


class CreateTopicDialog(QDialog):
    """Dialog tworzenia nowego wątku/tematu w grupie."""
    
    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Utwórz nowy wątek")
        self.setModal(True)
        self.setMinimumSize(700, 680)
        
        # Dane zespołów, kontaktów i grup
        self.teams: Dict[str, List[str]] = {}
        self.contacts: List[Dict[str, str]] = []
        self.groups: List[Dict[str, str]] = []
        self._load_teams_data()
        
        self._setup_ui()

    def _load_teams_data(self):
        """Ładuje dane zespołów, kontaktów i grup z modułu zarządzania."""
        # Pobierz grupy z parent module (TeamWorkModule)
        if hasattr(self.parent(), 'current_groups') and self.parent().current_groups:
            self.groups = [
                {
                    "id": group.get("id"),  # int z API
                    "name": group.get("name")
                }
                for group in self.parent().current_groups
            ]
        else:
            # Fallback - przykładowe dane jeśli nie ma połączenia
            self.groups = []
        
        # TODO: W przyszłości pobrać kontakty z bazy danych
        self.contacts = [
            {"email": "anna@example.com", "first_name": "Anna", "last_name": "Kowalska"},
            {"email": "bartek@example.com", "first_name": "Bartek", "last_name": "Nowak"},
            {"email": "celina@example.com", "first_name": "Celina", "last_name": "Wiśniewska"},
            {"email": "ewa@example.com", "first_name": "Ewa", "last_name": "Zielińska"},
            {"email": "filip@example.com", "first_name": "Filip", "last_name": "Dąbrowski"},
            {"email": "grzegorz@example.com", "first_name": "Grzegorz", "last_name": "Mazur"},
        ]
        
        self.teams = {
            "Marketing 2025": ["anna@example.com", "bartek@example.com", "celina@example.com"],
            "Zespół developerski": ["ewa@example.com", "filip@example.com", "grzegorz@example.com"],
            "Zarząd": ["anna@example.com", "ewa@example.com"],
        }

    def _setup_ui(self):
        """Tworzy interfejs użytkownika."""
        main_layout = QVBoxLayout(self)
        
        # Scroll area dla długiego formularza
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        layout = QVBoxLayout(scroll_content)
        
        # Informacja
        info_label = QLabel("Wątek to temat dyskusji w grupie. Dodaj pierwszą wiadomość, pliki i linki.")
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info_label)
        
        # Wybór grupy
        layout.addWidget(QLabel("<b>Grupa, w której utworzyć wątek:</b>"))
        self.group_combo = QComboBox()
        for group in self.groups:
            self.group_combo.addItem(group["name"], group["id"])
        if not self.groups:
            self.group_combo.addItem("(brak dostępnych grup)", None)
            self.group_combo.setEnabled(False)
        layout.addWidget(self.group_combo)
        
        # Nazwa wątku
        layout.addWidget(QLabel("<b>Nazwa wątku:</b>"))
        self.group_name_edit = QLineEdit()
        self.group_name_edit.setPlaceholderText("Np. Kampania wiosenna, Sprint #5")
        layout.addWidget(self.group_name_edit)
        
        # Wiadomość początkowa
        layout.addWidget(QLabel("<b>Pierwsza wiadomość:</b>"))
        self.initial_message_edit = QTextEdit()
        self.initial_message_edit.setPlaceholderText("Rozpocznij dyskusję w tym wątku...")
        self.initial_message_edit.setMaximumHeight(100)
        layout.addWidget(self.initial_message_edit)
        
        info_access = QLabel("ℹ️ Dostęp do wątku będą mieli wszyscy członkowie wybranej grupy.")
        info_access.setStyleSheet("color: #666; font-style: italic; margin-top: 5px;")
        info_access.setWordWrap(True)
        layout.addWidget(info_access)
        
        # Sekcja plików (opcjonalnie)
        files_group = QGroupBox("Pliki początkowe (opcjonalnie)")
        files_layout = QVBoxLayout(files_group)
        
        files_desc = QLabel("Dodaj pliki, które mają być dostępne od razu:")
        files_layout.addWidget(files_desc)
        
        files_input_layout = QHBoxLayout()
        self.files_edit = QLineEdit()
        self.files_edit.setPlaceholderText("Ścieżki do plików, oddzielone przecinkami")
        files_input_layout.addWidget(self.files_edit)
        
        browse_files_btn = QPushButton("📁 Przeglądaj")
        browse_files_btn.clicked.connect(self._browse_files)
        files_input_layout.addWidget(browse_files_btn)
        
        files_layout.addLayout(files_input_layout)
        layout.addWidget(files_group)
        
        # Sekcja linków (opcjonalnie)
        links_group = QGroupBox("Linki początkowe (opcjonalnie)")
        links_layout = QVBoxLayout(links_group)
        
        links_desc = QLabel("Dodaj linki, które mają być dostępne od razu:")
        links_layout.addWidget(links_desc)
        
        # Lista linków z możliwością dodawania
        self.links_list = QListWidget()
        links_layout.addWidget(self.links_list)
        
        links_btn_layout = QHBoxLayout()
        add_link_btn = QPushButton("➕ Dodaj link")
        add_link_btn.clicked.connect(self._add_link)
        links_btn_layout.addWidget(add_link_btn)
        
        remove_link_btn = QPushButton("➖ Usuń link")
        remove_link_btn.clicked.connect(self._remove_link)
        links_btn_layout.addWidget(remove_link_btn)
        links_btn_layout.addStretch()
        
        links_layout.addLayout(links_btn_layout)
        layout.addWidget(links_group)
        
        scroll.setWidget(scroll_content)
        main_layout.addWidget(scroll)
        
        # Przyciski akcji
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self._validate_and_accept)
        buttons.rejected.connect(self.reject)
        main_layout.addWidget(buttons)
        
        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)

    def _browse_files(self):
        """Otwiera dialog wyboru plików."""
        from PyQt6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Wybierz pliki",
            "",
            "Wszystkie pliki (*.*)"
        )
        if files:
            current = self.files_edit.text()
            if current:
                current += ", "
            self.files_edit.setText(current + ", ".join(files))

    def _add_link(self):
        """Dodaje link do listy."""
        from PyQt6.QtWidgets import QInputDialog
        
        url, ok1 = QInputDialog.getText(self, "Dodaj link", "URL:")
        if ok1 and url.strip():
            title, ok2 = QInputDialog.getText(self, "Dodaj link", "Tytuł (opcjonalnie):")
            
            display_text = title.strip() if (ok2 and title.strip()) else url.strip()
            item = QListWidgetItem(display_text)
            item.setData(Qt.ItemDataRole.UserRole, {
                "url": url.strip(),
                "title": title.strip() if ok2 else ""
            })
            self.links_list.addItem(item)

    def _remove_link(self):
        """Usuwa wybrany link z listy."""
        current_item = self.links_list.currentItem()
        if current_item:
            self.links_list.takeItem(self.links_list.row(current_item))

    def _validate_and_accept(self):
        """Waliduje dane i akceptuje dialog."""
        if self.group_combo.currentData() is None:
            QMessageBox.warning(self, "Błąd", "Brak dostępnych grup. Najpierw utwórz grupę.")
            return
        
        if not self.group_name_edit.text().strip():
            QMessageBox.warning(self, "Błąd", "Podaj nazwę wątku.")
            return
        
        if not self.initial_message_edit.toPlainText().strip():
            QMessageBox.warning(self, "Błąd", "Podaj pierwszą wiadomość w wątku.")
            return
        
        self.accept()

    def get_group_data(self) -> dict:
        """Zwraca dane wprowadzone w formularzu."""
        # Wybrana grupa
        selected_group_id = self.group_combo.currentData()
        selected_group_name = self.group_combo.currentText()
        
        # Pliki
        files_text = self.files_edit.text().strip()
        files = [f.strip() for f in files_text.split(',') if f.strip()] if files_text else []
        
        # Linki
        links = []
        for i in range(self.links_list.count()):
            item = self.links_list.item(i)
            if item:
                link_data = item.data(Qt.ItemDataRole.UserRole)
                links.append(link_data)
        
        return {
            "group_id": selected_group_id,
            "group_name": selected_group_name,
            "name": self.group_name_edit.text().strip(),
            "initial_message": self.initial_message_edit.toPlainText().strip(),
            "files": files,
            "links": links,
        }


class InvitationsDialog(QDialog):
    """Dialog zarządzania zaproszeniami do grup - Phase 6 Task 6.2"""

    def __init__(self, api_client, parent=None) -> None:
        super().__init__(parent)
        self.api_client = api_client
        self.setWindowTitle("Zaproszenia do grup")
        self.setModal(True)
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Tabs: Otrzymane zaproszenia | Wyślij zaproszenie
        from PyQt6.QtWidgets import QTabWidget
        
        tabs = QTabWidget()
        
        # Tab 1: Otrzymane zaproszenia
        received_tab = QWidget()
        received_layout = QVBoxLayout(received_tab)
        
        info_label = QLabel("Zaproszenia oczekujące na twoją odpowiedź:")
        info_label.setWordWrap(True)
        received_layout.addWidget(info_label)
        
        self.invitations_table = QTableWidget()
        self.invitations_table.setColumnCount(5)
        self.invitations_table.setHorizontalHeaderLabels([
            "Topic", "Od kogo", "Rola", "Data", "Status"
        ])
        self.invitations_table.horizontalHeader().setStretchLastSection(True)
        self.invitations_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.invitations_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        received_layout.addWidget(self.invitations_table)
        
        buttons_layout = QHBoxLayout()
        
        self.accept_btn = QPushButton("✅ Akceptuj zaproszenie")
        self.accept_btn.clicked.connect(self._accept_invitation)
        buttons_layout.addWidget(self.accept_btn)
        
        self.decline_btn = QPushButton("❌ Odrzuć zaproszenie")
        self.decline_btn.clicked.connect(self._decline_invitation)
        buttons_layout.addWidget(self.decline_btn)
        
        buttons_layout.addStretch()
        received_layout.addLayout(buttons_layout)
        
        tabs.addTab(received_tab, "📨 Otrzymane")
        
        # Tab 2: Wyślij zaproszenie
        send_tab = QWidget()
        send_layout = QVBoxLayout(send_tab)
        
        send_info = QLabel("Wyślij zaproszenie do topicu przez email:")
        send_info.setWordWrap(True)
        send_layout.addWidget(send_info)
        
        # Wybór topicu
        topic_group = QGroupBox("Wybierz topic")
        topic_layout = QVBoxLayout()
        
        self.topics_combo = QComboBox()
        topic_layout.addWidget(QLabel("Topic:"))
        topic_layout.addWidget(self.topics_combo)
        
        topic_group.setLayout(topic_layout)
        send_layout.addWidget(topic_group)
        
        # Email i rola
        invite_group = QGroupBox("Szczegóły zaproszenia")
        invite_layout = QVBoxLayout()
        
        invite_layout.addWidget(QLabel("Email zapraszanej osoby:"))
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("email@example.com")
        invite_layout.addWidget(self.email_input)
        
        invite_layout.addWidget(QLabel("Rola:"))
        self.role_combo = QComboBox()
        self.role_combo.addItem("👁️ Viewer - tylko odczyt", "viewer")
        self.role_combo.addItem("✏️ Member - odczyt i zapis", "member")
        self.role_combo.addItem("👑 Admin - pełne uprawnienia", "admin")
        self.role_combo.setCurrentIndex(1)  # Domyślnie member
        invite_layout.addWidget(self.role_combo)
        
        invite_layout.addWidget(QLabel("Wiadomość (opcjonalna):"))
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Dołącz do nas w pracy nad tym projektem...")
        self.message_input.setMaximumHeight(80)
        invite_layout.addWidget(self.message_input)
        
        invite_group.setLayout(invite_layout)
        send_layout.addWidget(invite_group)
        
        send_btn_layout = QHBoxLayout()
        send_btn_layout.addStretch()
        
        self.send_invite_btn = QPushButton("📧 Wyślij zaproszenie")
        self.send_invite_btn.clicked.connect(self._send_invitation)
        send_btn_layout.addWidget(self.send_invite_btn)
        
        send_layout.addLayout(send_btn_layout)
        send_layout.addStretch()
        
        tabs.addTab(send_tab, "📤 Wyślij")
        
        layout.addWidget(tabs)

        # Przyciski dialogu
        dialog_buttons = QHBoxLayout()
        close_button = QPushButton("Zamknij")
        close_button.clicked.connect(self.accept)
        dialog_buttons.addStretch()
        dialog_buttons.addWidget(close_button)
        layout.addLayout(dialog_buttons)

        # Załaduj dane
        self._load_invitations()
        self._load_topics()

    def _load_invitations(self) -> None:
        """Ładuje listę otrzymanych zaproszeń z API"""
        if not self.api_client:
            return
        
        response = self.api_client.get_pending_invitations()
        
        if not response.success:
            QMessageBox.warning(
                self,
                "Błąd",
                f"Nie udało się pobrać zaproszeń:\n{response.error}"
            )
            return
        
        invitations = response.data or []
        
        self.invitations_table.setRowCount(len(invitations))
        for row, inv in enumerate(invitations):
            # Zapisz invitation_id w pierwszej komórce jako dane użytkownika
            topic_item = QTableWidgetItem(inv.get('topic_name', 'Unknown'))
            topic_item.setData(Qt.ItemDataRole.UserRole, inv.get('invitation_id'))
            self.invitations_table.setItem(row, 0, topic_item)
            
            self.invitations_table.setItem(row, 1, QTableWidgetItem(inv.get('invited_by_email', 'Unknown')))
            self.invitations_table.setItem(row, 2, QTableWidgetItem(inv.get('role', 'member')))
            self.invitations_table.setItem(row, 3, QTableWidgetItem(str(inv.get('created_at', ''))))
            self.invitations_table.setItem(row, 4, QTableWidgetItem(inv.get('status', 'pending')))

    def _load_topics(self) -> None:
        """Ładuje listę dostępnych topicsów do wysłania zaproszenia"""
        if not self.api_client:
            return
        
        # Pobierz grupy użytkownika
        response = self.api_client.get_user_groups()
        
        if not response.success:
            return
        
        groups = response.data or []
        
        # Dla każdej grupy pobierz topics
        for group in groups:
            group_id = group.get('group_id')
            if not group_id:
                continue
            
            topics_response = self.api_client.get_group_topics(group_id)
            if topics_response.success and topics_response.data:
                for topic in topics_response.data:
                    topic_name = topic.get('topic_name', 'Unknown')
                    topic_id = topic.get('topic_id')
                    group_name = group.get('group_name', '')
                    
                    display_name = f"{group_name} / {topic_name}"
                    self.topics_combo.addItem(display_name, topic_id)

    def _send_invitation(self) -> None:
        """Wysyła zaproszenie do topicu"""
        topic_id = self.topics_combo.currentData()
        email = self.email_input.text().strip()
        role = self.role_combo.currentData()
        message = self.message_input.toPlainText().strip() or None
        
        if not topic_id:
            QMessageBox.warning(self, "Błąd", "Wybierz topic, do którego chcesz zaprosić osobę.")
            return
        
        if not email:
            QMessageBox.warning(self, "Błąd", "Podaj adres email zapraszanej osoby.")
            return
        
        # Walidacja emaila (podstawowa)
        if '@' not in email or '.' not in email:
            QMessageBox.warning(self, "Błąd", "Podaj prawidłowy adres email.")
            return
        
        response = self.api_client.send_topic_invitation(int(topic_id), email, role, message)
        
        if response.success:
            QMessageBox.information(
                self,
                "Zaproszenie wysłane",
                f"Zaproszenie zostało wysłane na adres:\n{email}\n\n"
                f"Rola: {role}"
            )
            
            # Wyczyść formularz
            self.email_input.clear()
            self.message_input.clear()
        else:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się wysłać zaproszenia:\n{response.error}"
            )

    def _accept_invitation(self) -> None:
        """Akceptuje wybrane zaproszenie"""
        selected_rows = self.invitations_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz zaproszenie do zaakceptowania.")
            return
        
        row = selected_rows[0].row()
        invitation_id = self.invitations_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        topic_name = self.invitations_table.item(row, 0).text()
        
        if not invitation_id:
            return
        
        response = self.api_client.accept_invitation(int(invitation_id))
        
        if response.success:
            QMessageBox.information(
                self,
                "Zaproszenie zaakceptowane",
                f"Dołączyłeś do topicu:\n{topic_name}"
            )
            
            # Odśwież listę
            self._load_invitations()
        else:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się zaakceptować zaproszenia:\n{response.error}"
            )

    def _decline_invitation(self) -> None:
        """Odrzuca wybrane zaproszenie"""
        selected_rows = self.invitations_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz zaproszenie do odrzucenia.")
            return
        
        row = selected_rows[0].row()
        invitation_id = self.invitations_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        topic_name = self.invitations_table.item(row, 0).text()
        
        if not invitation_id:
            return
        
        reply = QMessageBox.question(
            self,
            "Odrzuć zaproszenie",
            f"Czy na pewno chcesz odrzucić zaproszenie do topicu:\n{topic_name}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        response = self.api_client.decline_invitation(int(invitation_id))
        
        if response.success:
            QMessageBox.information(
                self,
                "Zaproszenie odrzucone",
                f"Odrzuciłeś zaproszenie do topicu:\n{topic_name}"
            )
            
            # Odśwież listę
            self._load_invitations()
        else:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się odrzucić zaproszenia:\n{response.error}"
            )


class ReplyDialog(QDialog):
    """Dialog odpowiedzi na wątek."""

    def __init__(self, topic_name: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Odpowiedź w temacie: {topic_name}")
        self.setModal(True)
        self.setMinimumSize(500, 450)
        
        # Domyślny kolor tła
        self.selected_color = "#FFFFFF"

        layout = QVBoxLayout(self)
        
        # Sekcja wyboru koloru
        color_group = QGroupBox("Kolor tła wiadomości")
        color_layout = QVBoxLayout(color_group)
        
        color_desc = QLabel("Wybierz kolor tła dla Twojej odpowiedzi:")
        color_layout.addWidget(color_desc)
        
        # Paleta kolorów
        colors_grid = QHBoxLayout()
        
        self.color_buttons = []
        predefined_colors = [
            ("#FFFFFF", "Biały"),
            ("#E3F2FD", "Niebieski"),
            ("#E8F5E9", "Zielony"),
            ("#FFF9C4", "Żółty"),
            ("#FFE0B2", "Pomarańczowy"),
            ("#F3E5F5", "Fioletowy"),
            ("#FFEBEE", "Różowy"),
            ("#E0E0E0", "Szary"),
        ]
        
        for color_code, color_name in predefined_colors:
            btn = QPushButton()
            btn.setFixedSize(50, 40)
            btn.setStyleSheet(f"background-color: {color_code}; border: 2px solid #999;")
            btn.setToolTip(color_name)
            btn.clicked.connect(lambda checked=False, c=color_code: self._set_color(c))
            colors_grid.addWidget(btn)
            self.color_buttons.append((btn, color_code))
        
        # Przycisk niestandardowego koloru
        custom_color_btn = QPushButton("🎨 Inny kolor...")
        custom_color_btn.clicked.connect(self._choose_custom_color)
        colors_grid.addWidget(custom_color_btn)
        
        colors_grid.addStretch()
        color_layout.addLayout(colors_grid)
        
        # Podgląd wybranego koloru
        preview_layout = QHBoxLayout()
        preview_layout.addWidget(QLabel("Podgląd:"))
        
        self.color_preview = QLabel("To jest podgląd Twojej wiadomości z wybranym kolorem tła")
        self.color_preview.setWordWrap(True)
        self.color_preview.setStyleSheet(
            f"background-color: {self.selected_color}; "
            "padding: 10px; border-radius: 5px; border: 1px solid #ccc;"
        )
        preview_layout.addWidget(self.color_preview, 1)
        
        color_layout.addLayout(preview_layout)
        layout.addWidget(color_group)
        
        # Treść wiadomości
        layout.addWidget(QLabel("Treść wiadomości:"))
        self.message_edit = QTextEdit()
        self.message_edit.setPlaceholderText("Wprowadź treść odpowiedzi...")
        layout.addWidget(self.message_edit)

        layout.addWidget(QLabel("Linki (oddzielone przecinkami):"))
        self.links_edit = QLineEdit()
        self.links_edit.setPlaceholderText("https://example.com, https://kolejny.link")
        layout.addWidget(self.links_edit)

        layout.addWidget(QLabel("Załączniki (ścieżki, przecinkami):"))
        self.files_edit = QLineEdit()
        self.files_edit.setPlaceholderText("plik1.pdf, plik2.png")
        layout.addWidget(self.files_edit)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setWindowFlag(Qt.WindowType.WindowContextHelpButtonHint, False)
        
        # Podświetl domyślny kolor (biały)
        self._update_selected_button()

    def _set_color(self, color_code: str):
        """Ustawia wybrany kolor."""
        self.selected_color = color_code
        self.color_preview.setStyleSheet(
            f"background-color: {color_code}; "
            "padding: 10px; border-radius: 5px; border: 1px solid #ccc;"
        )
        self._update_selected_button()

    def _choose_custom_color(self):
        """Otwiera dialog wyboru niestandardowego koloru."""
        from PyQt6.QtWidgets import QColorDialog
        from PyQt6.QtGui import QColor
        
        color = QColorDialog.getColor(QColor(self.selected_color), self, "Wybierz kolor")
        if color.isValid():
            self._set_color(color.name())

    def _update_selected_button(self):
        """Aktualizuje obramowanie przycisków, zaznaczając wybrany."""
        for btn, color_code in self.color_buttons:
            if color_code == self.selected_color:
                btn.setStyleSheet(
                    f"background-color: {color_code}; "
                    "border: 3px solid #2196F3; border-radius: 3px;"
                )
            else:
                btn.setStyleSheet(
                    f"background-color: {color_code}; "
                    "border: 2px solid #999; border-radius: 3px;"
                )

    def get_payload(self) -> dict:
        """Zwraca dane wprowadzone w formularzu odpowiedzi."""
        return {
            "message": self.message_edit.toPlainText().strip(),
            "links": [link.strip() for link in self.links_edit.text().split(",") if link.strip()],
            "files": [path.strip() for path in self.files_edit.text().split(",") if path.strip()],
            "background_color": self.selected_color,
        }


class ShareLinkDialog(QDialog):
    """Dialog generowania linku współdzielenia dla topicu - Phase 6 Task 6.1"""

    def __init__(self, topic: dict, api_client, parent=None) -> None:
        super().__init__(parent)
        self.topic = topic
        self.api_client = api_client
        self.share_link = None
        
        self.setWindowTitle(f"Udostępnij: {topic.get('topic_name', topic.get('title', 'Topic'))}")
        self.setModal(True)
        self.setMinimumSize(600, 350)

        layout = QVBoxLayout(self)

        # Opis
        info_label = QLabel(
            f"Wygeneruj link współdzielenia dla topicu '{topic.get('topic_name', topic.get('title', 'Topic'))}'.\n"
            "Osoby posiadające link będą mogły dołączyć do tego topicu."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Opcje uprawnień
        permissions_group = QGroupBox("Uprawnienia dla zaproszonych osób")
        permissions_layout = QVBoxLayout()
        
        self.permission_combo = QComboBox()
        self.permission_combo.addItem("👁️ Viewer - tylko odczyt", "viewer")
        self.permission_combo.addItem("✏️ Member - odczyt i zapis", "member")
        self.permission_combo.addItem("👑 Admin - pełne uprawnienia", "admin")
        self.permission_combo.setCurrentIndex(1)  # Domyślnie member
        permissions_layout.addWidget(QLabel("Rola dla nowych członków:"))
        permissions_layout.addWidget(self.permission_combo)
        
        permissions_group.setLayout(permissions_layout)
        layout.addWidget(permissions_group)

        # Link współdzielenia
        link_group = QGroupBox("Link współdzielenia")
        link_layout = QVBoxLayout()
        
        self.link_edit = QLineEdit()
        self.link_edit.setReadOnly(True)
        self.link_edit.setPlaceholderText("Kliknij 'Generuj link' aby utworzyć link...")
        link_layout.addWidget(self.link_edit)
        
        link_buttons = QHBoxLayout()
        
        self.generate_btn = QPushButton("🔗 Generuj link")
        self.generate_btn.clicked.connect(self._generate_link)
        link_buttons.addWidget(self.generate_btn)
        
        self.copy_btn = QPushButton("📋 Kopiuj do schowka")
        self.copy_btn.setEnabled(False)
        self.copy_btn.clicked.connect(self._copy_to_clipboard)
        link_buttons.addWidget(self.copy_btn)
        
        link_buttons.addStretch()
        link_layout.addLayout(link_buttons)
        
        link_group.setLayout(link_layout)
        layout.addWidget(link_group)

        # Statystyki linku
        stats_group = QGroupBox("Statystyki")
        stats_layout = QVBoxLayout()
        
        self.stats_label = QLabel("Brak aktywnego linku")
        self.stats_label.setWordWrap(True)
        stats_layout.addWidget(self.stats_label)
        
        stats_group.setLayout(stats_layout)
        layout.addWidget(stats_group)

        # Przyciski dialogu
        dialog_buttons = QHBoxLayout()
        
        self.revoke_btn = QPushButton("🚫 Unieważnij link")
        self.revoke_btn.setEnabled(False)
        self.revoke_btn.clicked.connect(self._revoke_link)
        dialog_buttons.addWidget(self.revoke_btn)
        
        dialog_buttons.addStretch()
        
        close_button = QPushButton("Zamknij")
        close_button.clicked.connect(self.accept)
        dialog_buttons.addWidget(close_button)
        
        layout.addLayout(dialog_buttons)

        # Załaduj istniejący link (jeśli istnieje)
        self._load_existing_link()

    def _generate_link(self) -> None:
        """Generuje nowy link współdzielenia przez API"""
        topic_id = self.topic.get('topic_id') or self.topic.get('id')
        role = self.permission_combo.currentData()
        
        if not topic_id:
            QMessageBox.warning(self, "Błąd", "Nie można wygenerować linku - brak ID topicu")
            return
        
        # Wywołanie API
        response = self.api_client.generate_share_link(int(topic_id), role)
        
        if response.success:
            self.share_link = response.data
            link_url = self.share_link.get('share_url', '')
            
            self.link_edit.setText(link_url)
            self.copy_btn.setEnabled(True)
            self.revoke_btn.setEnabled(True)
            self.generate_btn.setText("🔄 Regeneruj link")
            
            # Aktualizuj statystyki
            clicks = self.share_link.get('clicks_count', 0)
            created_at = self.share_link.get('created_at', 'nieznana')
            self.stats_label.setText(
                f"Link utworzony: {created_at}\n"
                f"Liczba kliknięć: {clicks}\n"
                f"Uprawnienia: {role}"
            )
            
            QMessageBox.information(
                self,
                "Link wygenerowany",
                f"Link współdzielenia został utworzony!\n\n{link_url}"
            )
        else:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się wygenerować linku:\n{response.error}"
            )

    def _copy_to_clipboard(self) -> None:
        """Kopiuje link do schowka systemowego"""
        from PyQt6.QtWidgets import QApplication
        
        link_url = self.link_edit.text()
        if link_url:
            clipboard = QApplication.clipboard()
            clipboard.setText(link_url)
            
            QMessageBox.information(
                self,
                "Skopiowano",
                "Link został skopiowany do schowka!"
            )

    def _revoke_link(self) -> None:
        """Unieważnia istniejący link"""
        reply = QMessageBox.question(
            self,
            "Unieważnij link",
            "Czy na pewno chcesz unieważnić ten link?\n"
            "Osoby posiadające ten link nie będą już mogły dołączyć do topicu.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        if not self.share_link:
            return
        
        link_id = self.share_link.get('share_link_id')
        if not link_id:
            return
        
        response = self.api_client.revoke_share_link(int(link_id))
        
        if response.success:
            self.link_edit.clear()
            self.link_edit.setPlaceholderText("Link został unieważniony. Kliknij 'Generuj link' aby utworzyć nowy...")
            self.copy_btn.setEnabled(False)
            self.revoke_btn.setEnabled(False)
            self.generate_btn.setText("🔗 Generuj link")
            self.stats_label.setText("Brak aktywnego linku")
            self.share_link = None
            
            QMessageBox.information(
                self,
                "Link unieważniony",
                "Link współdzielenia został unieważniony."
            )
        else:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się unieważnić linku:\n{response.error}"
            )

    def _load_existing_link(self) -> None:
        """Ładuje istniejący link współdzielenia (jeśli istnieje)"""
        topic_id = self.topic.get('topic_id') or self.topic.get('id')
        if not topic_id:
            return
        
        response = self.api_client.get_topic_share_links(int(topic_id))
        
        if response.success and response.data:
            # Pobierz pierwszy aktywny link
            links = response.data
            active_links = [link for link in links if link.get('is_active')]
            
            if active_links:
                self.share_link = active_links[0]
                link_url = self.share_link.get('share_url', '')
                role = self.share_link.get('default_role', 'member')
                
                self.link_edit.setText(link_url)
                self.copy_btn.setEnabled(True)
                self.revoke_btn.setEnabled(True)
                self.generate_btn.setText("🔄 Regeneruj link")
                
                # Ustawwybór roli
                for i in range(self.permission_combo.count()):
                    if self.permission_combo.itemData(i) == role:
                        self.permission_combo.setCurrentIndex(i)
                        break
                
                # Aktualizuj statystyki
                clicks = self.share_link.get('clicks_count', 0)
                created_at = self.share_link.get('created_at', 'nieznana')
                self.stats_label.setText(
                    f"Link utworzony: {created_at}\n"
                    f"Liczba kliknięć: {clicks}\n"
                    f"Uprawnienia: {role}"
                )


class MembersManagementDialog(QDialog):
    """Dialog zarządzania członkami i uprawnieniami topicu - Phase 6 Task 6.3 & 6.4"""

    def __init__(self, topic: dict, api_client, parent=None) -> None:
        super().__init__(parent)
        self.topic = topic
        self.api_client = api_client
        self.current_user_role = None
        
        self.setWindowTitle(f"Członkowie: {topic.get('topic_name', topic.get('title', 'Topic'))}")
        self.setModal(True)
        self.setMinimumSize(800, 600)

        layout = QVBoxLayout(self)

        # Opis
        info_label = QLabel(
            f"Zarządzaj członkami topicu '{topic.get('topic_name', topic.get('title', 'Topic'))}'.\n"
            "Możesz zmieniać role członków oraz usuwać ich z topicu."
        )
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # Tabela członków
        members_group = QGroupBox("Lista członków")
        members_layout = QVBoxLayout()
        
        self.members_table = QTableWidget()
        self.members_table.setColumnCount(5)
        self.members_table.setHorizontalHeaderLabels([
            "Email", "Rola", "Dołączył", "Status", "Akcje"
        ])
        self.members_table.horizontalHeader().setStretchLastSection(True)
        self.members_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.members_table.setSelectionMode(QTableWidget.SelectionMode.SingleSelection)
        members_layout.addWidget(self.members_table)
        
        members_group.setLayout(members_layout)
        layout.addWidget(members_group)

        # Akcje
        actions_layout = QHBoxLayout()
        
        self.change_role_btn = QPushButton("👑 Zmień rolę")
        self.change_role_btn.clicked.connect(self._change_member_role)
        actions_layout.addWidget(self.change_role_btn)
        
        self.remove_member_btn = QPushButton("➖ Usuń członka")
        self.remove_member_btn.clicked.connect(self._remove_member)
        actions_layout.addWidget(self.remove_member_btn)
        
        actions_layout.addStretch()
        layout.addLayout(actions_layout)

        # Informacje o uprawnieniach
        perms_info = QLabel(
            "Uprawnienia ról:\n"
            "• 👁️ Viewer - tylko odczyt wiadomości, plików i zadań\n"
            "• ✏️ Member - odczyt + dodawanie wiadomości, plików, zadań\n"
            "• 👑 Admin - pełne uprawnienia + zarządzanie członkami\n"
            "• 👨‍💼 Owner - wszystkie uprawnienia + transfer ownership"
        )
        perms_info.setWordWrap(True)
        perms_info.setStyleSheet("color: #666; font-size: 9pt; padding: 10px; background: #f5f5f5; border-radius: 5px;")
        layout.addWidget(perms_info)

        # Przyciski dialogu
        dialog_buttons = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Odśwież")
        refresh_btn.clicked.connect(self._load_members)
        dialog_buttons.addWidget(refresh_btn)
        
        dialog_buttons.addStretch()
        
        close_button = QPushButton("Zamknij")
        close_button.clicked.connect(self.accept)
        dialog_buttons.addWidget(close_button)
        
        layout.addLayout(dialog_buttons)

        # Załaduj dane
        self._load_current_user_role()
        self._load_members()

    def _load_current_user_role(self) -> None:
        """Pobiera rolę zalogowanego użytkownika w topicu"""
        topic_id = self.topic.get('topic_id') or self.topic.get('id')
        if not topic_id:
            return
        
        response = self.api_client.get_my_topic_role(int(topic_id))
        
        if response.success and response.data:
            self.current_user_role = response.data.get('role', 'viewer')
        else:
            # Fallback - zakładamy member
            self.current_user_role = 'member'

    def _load_members(self) -> None:
        """Ładuje listę członków topicu z API"""
        topic_id = self.topic.get('topic_id') or self.topic.get('id')
        if not topic_id:
            return
        
        response = self.api_client.get_topic_members(int(topic_id))
        
        if not response.success:
            QMessageBox.warning(
                self,
                "Błąd",
                f"Nie udało się pobrać listy członków:\n{response.error}"
            )
            return
        
        members = response.data or []
        
        self.members_table.setRowCount(len(members))
        for row, member in enumerate(members):
            # Email
            email_item = QTableWidgetItem(member.get('email', 'Unknown'))
            email_item.setData(Qt.ItemDataRole.UserRole, member.get('user_id'))
            self.members_table.setItem(row, 0, email_item)
            
            # Rola
            role = member.get('role', 'member')
            role_icon = {
                'owner': '👨‍💼',
                'admin': '👑',
                'member': '✏️',
                'viewer': '👁️'
            }.get(role, '✏️')
            
            role_item = QTableWidgetItem(f"{role_icon} {role.capitalize()}")
            role_item.setData(Qt.ItemDataRole.UserRole, role)
            self.members_table.setItem(row, 1, role_item)
            
            # Dołączył
            joined_at = member.get('joined_at', '')
            self.members_table.setItem(row, 2, QTableWidgetItem(str(joined_at)))
            
            # Status
            is_online = member.get('is_online', False)
            status_item = QTableWidgetItem("🟢 Online" if is_online else "⚪ Offline")
            self.members_table.setItem(row, 3, status_item)
            
            # Akcje (button w komórce)
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            
            # Tylko admin/owner może zarządzać
            if self.current_user_role in ['admin', 'owner']:
                edit_btn = QPushButton("✏️")
                edit_btn.setToolTip("Zmień rolę")
                edit_btn.setMaximumWidth(30)
                edit_btn.clicked.connect(lambda checked, r=row: self._quick_change_role(r))
                actions_layout.addWidget(edit_btn)
                
                # Nie można usunąć owner
                if role != 'owner':
                    remove_btn = QPushButton("❌")
                    remove_btn.setToolTip("Usuń członka")
                    remove_btn.setMaximumWidth(30)
                    remove_btn.clicked.connect(lambda checked, r=row: self._quick_remove_member(r))
                    actions_layout.addWidget(remove_btn)
            
            actions_layout.addStretch()
            self.members_table.setCellWidget(row, 4, actions_widget)
        
        # Wyłącz przyciski jeśli nie masz uprawnień
        can_manage = self.current_user_role in ['admin', 'owner']
        self.change_role_btn.setEnabled(can_manage)
        self.remove_member_btn.setEnabled(can_manage)

    def _change_member_role(self) -> None:
        """Zmienia rolę wybranego członka"""
        selected_rows = self.members_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz członka, którego rolę chcesz zmienić.")
            return
        
        row = selected_rows[0].row()
        self._quick_change_role(row)

    def _quick_change_role(self, row: int) -> None:
        """Szybka zmiana roli dla wybranego wiersza"""
        user_id = self.members_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        email = self.members_table.item(row, 0).text()
        current_role = self.members_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        
        if not user_id:
            return
        
        # Dialog wyboru nowej roli
        roles = [
            ("👁️ Viewer - tylko odczyt", "viewer"),
            ("✏️ Member - odczyt i zapis", "member"),
            ("👑 Admin - pełne uprawnienia", "admin"),
        ]
        
        # Tylko owner może nadawać role owner
        if self.current_user_role == 'owner':
            roles.append(("👨‍💼 Owner - transfer ownership", "owner"))
        
        role_names = [r[0] for r in roles]
        role_values = [r[1] for r in roles]
        
        # Znajdź aktualną rolę
        try:
            current_index = role_values.index(current_role)
        except ValueError:
            current_index = 1  # Domyślnie member
        
        new_role_name, ok = QInputDialog.getItem(
            self,
            "Zmień rolę",
            f"Wybierz nową rolę dla {email}:",
            role_names,
            current_index,
            False
        )
        
        if not ok:
            return
        
        new_role = role_values[role_names.index(new_role_name)]
        
        if new_role == current_role:
            QMessageBox.information(self, "Info", "Wybrano tę samą rolę.")
            return
        
        # Ostrzeżenie przy transferze ownership
        if new_role == 'owner':
            reply = QMessageBox.warning(
                self,
                "Transfer ownership",
                f"Czy na pewno chcesz przekazać ownership topicu użytkownikowi {email}?\n\n"
                "Po tej operacji stracisz uprawnienia właściciela!",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
        
        topic_id = self.topic.get('topic_id') or self.topic.get('id')
        if not topic_id:
            return
        
        response = self.api_client.update_member_role(int(topic_id), int(user_id), new_role)
        
        if response.success:
            QMessageBox.information(
                self,
                "Rola zmieniona",
                f"Rola użytkownika {email} została zmieniona na: {new_role}"
            )
            
            # Jeśli to był transfer ownership, zaktualizuj naszą rolę
            if new_role == 'owner':
                self.current_user_role = 'admin'  # Automatyczna degradacja
            
            # Odśwież listę
            self._load_members()
        else:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się zmienić roli:\n{response.error}"
            )

    def _remove_member(self) -> None:
        """Usuwa wybranego członka z topicu"""
        selected_rows = self.members_table.selectedIndexes()
        if not selected_rows:
            QMessageBox.warning(self, "Brak wyboru", "Wybierz członka do usunięcia.")
            return
        
        row = selected_rows[0].row()
        self._quick_remove_member(row)

    def _quick_remove_member(self, row: int) -> None:
        """Szybkie usunięcie członka dla wybranego wiersza"""
        user_id = self.members_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
        email = self.members_table.item(row, 0).text()
        role = self.members_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        
        if not user_id:
            return
        
        # Nie można usunąć owner
        if role == 'owner':
            QMessageBox.warning(
                self,
                "Błąd",
                "Nie można usunąć właściciela topicu.\n"
                "Najpierw przenieś ownership na inną osobę."
            )
            return
        
        reply = QMessageBox.question(
            self,
            "Usuń członka",
            f"Czy na pewno chcesz usunąć użytkownika {email} z tego topicu?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        topic_id = self.topic.get('topic_id') or self.topic.get('id')
        if not topic_id:
            return
        
        response = self.api_client.remove_topic_member(int(topic_id), int(user_id))
        
        if response.success:
            QMessageBox.information(
                self,
                "Członek usunięty",
                f"Użytkownik {email} został usunięty z topicu."
            )
            
            # Odśwież listę
            self._load_members()
        else:
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się usunąć członka:\n{response.error}"
            )

