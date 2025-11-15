"""Dialog zarządzania zespołami i kontaktami."""

from __future__ import annotations

from typing import List, Dict, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QTabWidget,
    QWidget,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QInputDialog,
    QSplitter,
)


class TeamManagementDialog(QDialog):
    """Dialog do zarządzania kontaktami i zespołami."""

    def __init__(self, api_client=None, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Zarządzanie zespołami")
        self.resize(900, 600)
        
        # API Client
        self.api_client = api_client
        
        # Dane
        self.contacts: List[Dict[str, str]] = []
        self.teams: Dict[str, List[str]] = {}  # team_name -> [email1, email2, ...]
        self.groups: List[Dict] = []  # Grupy robocze z API
        
        self._setup_ui()
        self._load_sample_data()
        self._refresh_contacts_table()
        self._refresh_teams_list()
        
        # Załaduj grupy z API jeśli dostępny
        if self.api_client:
            self._load_groups_from_api()

    def _setup_ui(self):
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)
        
        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_groups_tab(), "🏢 Grupy robocze")  # Nowa zakładka
        tabs.addTab(self._create_contacts_tab(), "📇 Kontakty")
        tabs.addTab(self._create_teams_tab(), "👥 Zespoły")
        layout.addWidget(tabs)
        
        # Przyciski akcji
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        save_btn = QPushButton("💾 Zapisz")
        save_btn.clicked.connect(self._save_changes)
        buttons_layout.addWidget(save_btn)
        
        close_btn = QPushButton("Zamknij")
        close_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(close_btn)
        
        layout.addLayout(buttons_layout)
    
    def _create_groups_tab(self) -> QWidget:
        """Tworzy zakładkę zarządzania grupami roboczymi."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Nagłówek
        header = QLabel("Grupy robocze - zarządzanie")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header)
        
        info = QLabel("Zarządzaj swoimi grupami roboczymi. Możesz edytować, usuwać grupy oraz zarządzać członkami.")
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Przyciski akcji
        btn_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("🔄 Odśwież")
        refresh_btn.clicked.connect(self._load_groups_from_api)
        btn_layout.addWidget(refresh_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Tabela grup
        self.groups_table = QTableWidget()
        self.groups_table.setColumnCount(6)
        self.groups_table.setHorizontalHeaderLabels([
            "ID", "Nazwa grupy", "Członkowie", "Rola", "Status", "Akcje"
        ])
        self.groups_table.horizontalHeader().setStretchLastSection(False)
        self.groups_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.groups_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.groups_table.setColumnWidth(0, 60)
        self.groups_table.setColumnWidth(1, 200)
        self.groups_table.setColumnWidth(2, 80)
        self.groups_table.setColumnWidth(3, 80)
        self.groups_table.setColumnWidth(4, 80)
        self.groups_table.setColumnWidth(5, 300)
        layout.addWidget(self.groups_table)
        
        return widget

    def _create_contacts_tab(self) -> QWidget:
        """Tworzy zakładkę zarządzania kontaktami."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Nagłówek
        header = QLabel("Zarządzanie kontaktami")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header)
        
        # Przyciski akcji
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ Dodaj kontakt")
        add_btn.clicked.connect(self._add_contact)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("✏️ Edytuj")
        edit_btn.clicked.connect(self._edit_contact)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("🗑️ Usuń")
        delete_btn.clicked.connect(self._delete_contact)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Tabela kontaktów
        self.contacts_table = QTableWidget()
        self.contacts_table.setColumnCount(3)
        self.contacts_table.setHorizontalHeaderLabels(["E-mail", "Imię", "Nazwisko"])
        self.contacts_table.horizontalHeader().setStretchLastSection(True)
        self.contacts_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.contacts_table.setAlternatingRowColors(True)
        layout.addWidget(self.contacts_table)
        
        return widget

    def _create_teams_tab(self) -> QWidget:
        """Tworzy zakładkę zarządzania zespołami."""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
    
        # Splitter: lista zespołów | członkowie zespołu
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Lewa strona - lista zespołów
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        
        teams_label = QLabel("Zespoły")
        teams_label.setStyleSheet("font-weight: bold;")
        left_layout.addWidget(teams_label)
        
        teams_btn_layout = QHBoxLayout()
        add_team_btn = QPushButton("➕ Nowy zespół")
        add_team_btn.clicked.connect(self._add_team)
        teams_btn_layout.addWidget(add_team_btn)
        
        rename_team_btn = QPushButton("✏️ Zmień nazwę")
        rename_team_btn.clicked.connect(self._rename_team)
        teams_btn_layout.addWidget(rename_team_btn)
        
        delete_team_btn = QPushButton("🗑️ Usuń")
        delete_team_btn.clicked.connect(self._delete_team)
        teams_btn_layout.addWidget(delete_team_btn)
        
        left_layout.addLayout(teams_btn_layout)
        
        self.teams_list = QListWidget()
        self.teams_list.currentItemChanged.connect(self._on_team_selected)
        left_layout.addWidget(self.teams_list)
        
        splitter.addWidget(left_widget)
        
        # Prawa strona - członkowie zespołu
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        
        self.team_members_label = QLabel("Członkowie zespołu")
        self.team_members_label.setStyleSheet("font-weight: bold;")
        right_layout.addWidget(self.team_members_label)
        
        members_btn_layout = QHBoxLayout()
        add_member_btn = QPushButton("➕ Dodaj członka")
        add_member_btn.clicked.connect(self._add_team_member)
        members_btn_layout.addWidget(add_member_btn)
        
        remove_member_btn = QPushButton("➖ Usuń z zespołu")
        remove_member_btn.clicked.connect(self._remove_team_member)
        members_btn_layout.addWidget(remove_member_btn)
        
        members_btn_layout.addStretch()
        right_layout.addLayout(members_btn_layout)
        
        self.team_members_list = QListWidget()
        self.team_members_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        right_layout.addWidget(self.team_members_list)
        
        splitter.addWidget(right_widget)
        
        splitter.setSizes([300, 600])
        layout.addWidget(splitter)
        
        return widget

    def _load_sample_data(self):
        """Ładuje przykładowe dane."""
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

    def _refresh_contacts_table(self):
        """Odświeża tabelę kontaktów."""
        self.contacts_table.setRowCount(len(self.contacts))
        
        for row, contact in enumerate(self.contacts):
            email_item = QTableWidgetItem(contact["email"])
            email_item.setFlags(email_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.contacts_table.setItem(row, 0, email_item)
            
            first_name_item = QTableWidgetItem(contact["first_name"])
            first_name_item.setFlags(first_name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.contacts_table.setItem(row, 1, first_name_item)
            
            last_name_item = QTableWidgetItem(contact["last_name"])
            last_name_item.setFlags(last_name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.contacts_table.setItem(row, 2, last_name_item)

    def _refresh_teams_list(self):
        """Odświeża listę zespołów."""
        current_team = self.teams_list.currentItem()
        current_text = current_team.text() if current_team else None
        
        self.teams_list.clear()
        for team_name in sorted(self.teams.keys()):
            item = QListWidgetItem(team_name)
            self.teams_list.addItem(item)
            if team_name == current_text:
                self.teams_list.setCurrentItem(item)

    def _add_contact(self):
        """Dodaje nowy kontakt."""
        dialog = ContactEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            contact_data = dialog.get_contact_data()
            
            # Sprawdź czy email już istnieje
            if any(c["email"] == contact_data["email"] for c in self.contacts):
                QMessageBox.warning(self, "Błąd", "Kontakt z tym adresem e-mail już istnieje.")
                return
            
            self.contacts.append(contact_data)
            self._refresh_contacts_table()

    def _edit_contact(self):
        """Edytuje wybrany kontakt."""
        current_row = self.contacts_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Informacja", "Wybierz kontakt do edycji.")
            return
        
        contact = self.contacts[current_row]
        dialog = ContactEditDialog(self, contact)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            old_email = contact["email"]
            new_data = dialog.get_contact_data()
            
            # Sprawdź czy nowy email nie koliduje
            if new_data["email"] != old_email:
                if any(c["email"] == new_data["email"] for c in self.contacts):
                    QMessageBox.warning(self, "Błąd", "Kontakt z tym adresem e-mail już istnieje.")
                    return
                
                # Zaktualizuj email w zespołach
                for team_members in self.teams.values():
                    for i, email in enumerate(team_members):
                        if email == old_email:
                            team_members[i] = new_data["email"]
            
            self.contacts[current_row] = new_data
            self._refresh_contacts_table()
            self._refresh_team_members()

    def _delete_contact(self):
        """Usuwa wybrany kontakt."""
        current_row = self.contacts_table.currentRow()
        if current_row < 0:
            QMessageBox.information(self, "Informacja", "Wybierz kontakt do usunięcia.")
            return
        
        contact = self.contacts[current_row]
        email = contact["email"]
        
        # Sprawdź czy kontakt jest używany w zespołach
        teams_using = [name for name, members in self.teams.items() if email in members]
        if teams_using:
            msg = f"Kontakt jest używany w zespołach: {', '.join(teams_using)}\n\nCzy na pewno usunąć?"
            reply = QMessageBox.question(self, "Potwierdzenie", msg)
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Usuń z zespołów
            for members in self.teams.values():
                if email in members:
                    members.remove(email)
        
        del self.contacts[current_row]
        self._refresh_contacts_table()
        self._refresh_team_members()

    def _add_team(self):
        """Dodaje nowy zespół."""
        name, ok = QInputDialog.getText(self, "Nowy zespół", "Nazwa zespołu:")
        if ok and name:
            if name in self.teams:
                QMessageBox.warning(self, "Błąd", "Zespół o tej nazwie już istnieje.")
                return
            
            self.teams[name] = []
            self._refresh_teams_list()

    def _rename_team(self):
        """Zmienia nazwę zespołu."""
        current_item = self.teams_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Informacja", "Wybierz zespół do zmiany nazwy.")
            return
        
        old_name = current_item.text()
        new_name, ok = QInputDialog.getText(self, "Zmiana nazwy", "Nowa nazwa zespołu:", text=old_name)
        
        if ok and new_name and new_name != old_name:
            if new_name in self.teams:
                QMessageBox.warning(self, "Błąd", "Zespół o tej nazwie już istnieje.")
                return
            
            self.teams[new_name] = self.teams.pop(old_name)
            self._refresh_teams_list()

    def _delete_team(self):
        """Usuwa zespół."""
        current_item = self.teams_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Informacja", "Wybierz zespół do usunięcia.")
            return
        
        team_name = current_item.text()
        reply = QMessageBox.question(
            self, 
            "Potwierdzenie", 
            f"Czy na pewno usunąć zespół '{team_name}'?"
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            del self.teams[team_name]
            self._refresh_teams_list()
            self.team_members_list.clear()

    def _on_team_selected(self, current, previous):
        """Obsługuje zmianę wybranego zespołu."""
        if current:
            self.team_members_label.setText(f"Członkowie zespołu: {current.text()}")
            self._refresh_team_members()
        else:
            self.team_members_label.setText("Członkowie zespołu")
            self.team_members_list.clear()

    def _refresh_team_members(self):
        """Odświeża listę członków aktualnie wybranego zespołu."""
        current_item = self.teams_list.currentItem()
        if not current_item:
            return
        
        team_name = current_item.text()
        members = self.teams.get(team_name, [])
        
        self.team_members_list.clear()
        for email in members:
            contact = self._get_contact_by_email(email)
            if contact:
                display_name = f"{contact['first_name']} {contact['last_name']} ({email})"
            else:
                display_name = f"{email} (kontakt nie znaleziony)"
            
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, email)
            self.team_members_list.addItem(item)

    def _add_team_member(self):
        """Dodaje członka do zespołu."""
        current_item = self.teams_list.currentItem()
        if not current_item:
            QMessageBox.information(self, "Informacja", "Wybierz zespół.")
            return
        
        team_name = current_item.text()
        
        # Dialog wyboru kontaktu
        dialog = ContactSelectionDialog(self.contacts, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            selected_emails = dialog.get_selected_emails()
            
            members = self.teams[team_name]
            added_count = 0
            
            for email in selected_emails:
                if email not in members:
                    members.append(email)
                    added_count += 1
            
            if added_count > 0:
                self._refresh_team_members()
                QMessageBox.information(self, "Sukces", f"Dodano {added_count} członków do zespołu.")

    def _remove_team_member(self):
        """Usuwa członka z zespołu."""
        current_team = self.teams_list.currentItem()
        if not current_team:
            QMessageBox.information(self, "Informacja", "Wybierz zespół.")
            return
        
        selected_items = self.team_members_list.selectedItems()
        if not selected_items:
            QMessageBox.information(self, "Informacja", "Wybierz członków do usunięcia.")
            return
        
        team_name = current_team.text()
        members = self.teams[team_name]
        
        for item in selected_items:
            email = item.data(Qt.ItemDataRole.UserRole)
            if email in members:
                members.remove(email)
        
        self._refresh_team_members()

    def _get_contact_by_email(self, email: str) -> Optional[Dict[str, str]]:
        """Zwraca kontakt po adresie email."""
        for contact in self.contacts:
            if contact["email"] == email:
                return contact
        return None

    def _save_changes(self):
        """Zapisuje zmiany."""
        QMessageBox.information(
            self,
            "Zapis",
            "Zmiany zostały zapisane.\n\n(W kolejnej iteracji zostanie zintegrowane z bazą danych)"
        )
    
    # =============================================================================
    # Metody zarządzania grupami roboczymi (API Integration)
    # =============================================================================
    
    def _load_groups_from_api(self):
        """Ładuje grupy z API i wyświetla w tabeli."""
        from loguru import logger
        
        if not self.api_client:
            QMessageBox.warning(
                self,
                "Brak połączenia",
                "Nie można pobrać grup - brak połączenia z API.\nZaloguj się ponownie."
            )
            return
        
        logger.info("[TeamManagement] Fetching groups from API...")
        response = self.api_client.get_user_groups()
        
        if response.success:
            self.groups = response.data or []
            logger.success(f"[TeamManagement] Fetched {len(self.groups)} groups")
            self._refresh_groups_table()
        else:
            logger.error(f"[TeamManagement] Failed to fetch groups: {response.error}")
            QMessageBox.critical(
                self,
                "Błąd pobierania grup",
                f"Nie udało się pobrać list grup:\n{response.error}"
            )
    
    def _refresh_groups_table(self):
        """Odświeża tabelę grup."""
        from loguru import logger
        
        self.groups_table.setRowCount(len(self.groups))
        
        for row, group in enumerate(self.groups):
            # ID
            id_item = QTableWidgetItem(str(group.get("id", "")))
            id_item.setFlags(id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.groups_table.setItem(row, 0, id_item)
            
            # Nazwa grupy
            name_item = QTableWidgetItem(group.get("group_name", ""))
            name_item.setFlags(name_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.groups_table.setItem(row, 1, name_item)
            
            # Liczba członków
            members = group.get("members", [])
            members_count = QTableWidgetItem(str(len(members)))
            members_count.setFlags(members_count.flags() & ~Qt.ItemFlag.ItemIsEditable)
            members_count.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.groups_table.setItem(row, 2, members_count)
            
            # Rola użytkownika
            owner_id = group.get("owner_id")
            # TODO: Pobierz user_id z parent module
            user_role = "Owner" if owner_id else "Member"  # Uproszczenie
            role_item = QTableWidgetItem(user_role)
            role_item.setFlags(role_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            role_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.groups_table.setItem(row, 3, role_item)
            
            # Status
            is_active = group.get("is_active", True)
            status_item = QTableWidgetItem("Aktywna" if is_active else "Nieaktywna")
            status_item.setFlags(status_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            status_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.groups_table.setItem(row, 4, status_item)
            
            # Przyciski akcji
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)
            
            # Przycisk Edytuj
            edit_btn = QPushButton("✏️ Edytuj")
            edit_btn.setToolTip("Edytuj nazwę i opis grupy")
            edit_btn.clicked.connect(lambda checked, g=group: self._edit_group(g))
            actions_layout.addWidget(edit_btn)
            
            # Przycisk Członkowie
            members_btn = QPushButton("👥 Członkowie")
            members_btn.setToolTip("Zarządzaj członkami grupy")
            members_btn.clicked.connect(lambda checked, g=group: self._manage_members(g))
            actions_layout.addWidget(members_btn)
            
            # Przycisk Usuń (tylko dla owner)
            if user_role == "Owner":
                delete_btn = QPushButton("🗑️ Usuń")
                delete_btn.setToolTip("Usuń grupę (tylko właściciel)")
                delete_btn.clicked.connect(lambda checked, g=group: self._delete_group(g))
                actions_layout.addWidget(delete_btn)
            
            actions_layout.addStretch()
            self.groups_table.setCellWidget(row, 5, actions_widget)
        
        logger.debug(f"[TeamManagement] Groups table refreshed with {len(self.groups)} rows")
    
    def _edit_group(self, group: Dict):
        """Edytuj grupę."""
        from loguru import logger
        
        # Dialog edycji
        group_name, ok1 = QInputDialog.getText(
            self,
            "Edytuj grupę",
            "Nazwa grupy:",
            text=group.get("group_name", "")
        )
        
        if not ok1 or not group_name.strip():
            return
        
        description, ok2 = QInputDialog.getText(
            self,
            "Edytuj grupę",
            "Opis grupy (opcjonalnie):",
            text=group.get("description", "")
        )
        
        if not ok2:
            return
        
        # Wywołaj API
        logger.info(f"[TeamManagement] Updating group {group['id']}: {group_name}")
        response = self.api_client.update_group(
            group_id=group['id'],
            group_name=group_name.strip(),
            description=description.strip() if description else None
        )
        
        if response.success:
            logger.success(f"[TeamManagement] Group {group['id']} updated successfully")
            QMessageBox.information(self, "Sukces", f"Grupa '{group_name}' została zaktualizowana.")
            self._load_groups_from_api()  # Odśwież listę
        else:
            logger.error(f"[TeamManagement] Failed to update group: {response.error}")
            QMessageBox.critical(self, "Błąd", f"Nie udało się zaktualizować grupy:\n{response.error}")
    
    def _delete_group(self, group: Dict):
        """Usuń grupę."""
        from loguru import logger
        
        # Konfirmacja
        reply = QMessageBox.question(
            self,
            "Potwierdź usunięcie",
            f"Czy na pewno chcesz usunąć grupę '{group.get('group_name')}'?\n\n"
            f"Ta operacja jest nieodwracalna i usunie także wszystkie wątki, wiadomości i zadania w tej grupie.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Wywołaj API
        logger.info(f"[TeamManagement] Deleting group {group['id']}")
        response = self.api_client.delete_group(group_id=group['id'])
        
        if response.success:
            logger.success(f"[TeamManagement] Group {group['id']} deleted successfully")
            QMessageBox.information(self, "Sukces", f"Grupa '{group.get('group_name')}' została usunięta.")
            self._load_groups_from_api()  # Odśwież listę
            
            # TODO: Emit signal do parent (teamwork_module) aby odświeżył drzewo
        else:
            logger.error(f"[TeamManagement] Failed to delete group: {response.error}")
            QMessageBox.critical(self, "Błąd", f"Nie udało się usunąć grupy:\n{response.error}")
    
    def _manage_members(self, group: Dict):
        """Zarządzaj członkami grupy."""
        from loguru import logger
        
        logger.info(f"[TeamManagement] Opening members dialog for group {group['id']}")
        
        # Otwórz dedykowany dialog zarządzania członkami
        dialog = GroupMembersDialog(
            group=group,
            api_client=self.api_client,
            current_user_id=None,  # TODO: Przekazać current_user_id z parent
            parent=self
        )
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Po zamknięciu dialogu odśwież listę grup (mogły się zmienić członkowie/owner)
            self._load_groups_from_api()

    def get_contacts(self) -> List[Dict[str, str]]:
        """Zwraca listę kontaktów."""
        return self.contacts

    def get_teams(self) -> Dict[str, List[str]]:
        """Zwraca słownik zespołów."""
        return self.teams




# =============================================================================
# Dialog zarządzania członkami grupy
# =============================================================================

class GroupMembersDialog(QDialog):
    """Dialog do zarządzania członkami konkretnej grupy."""
    
    def __init__(self, group: Dict, api_client, current_user_id: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.group = group
        self.api_client = api_client
        self.current_user_id = current_user_id
        self.members = group.get("members", [])
        
        self.setWindowTitle(f"Członkowie grupy: {group.get('group_name', 'Grupa')}")
        self.resize(700, 500)
        
        self._setup_ui()
        self._refresh_members_list()
    
    def _setup_ui(self):
        """Tworzy interfejs użytkownika."""
        layout = QVBoxLayout(self)
        
        # Nagłówek
        header = QLabel(f"Zarządzanie członkami grupy '{self.group.get('group_name')}'")
        header.setStyleSheet("font-weight: bold; font-size: 12pt;")
        layout.addWidget(header)
        
        # Info o grupie
        info = QLabel(f"ID: {self.group.get('id')} | Owner: {self.group.get('owner_id', 'N/A')}")
        info.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(info)
        
        # Przyciski akcji
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("➕ Dodaj członka")
        add_btn.clicked.connect(self._add_member)
        btn_layout.addWidget(add_btn)
        
        transfer_btn = QPushButton("👑 Przekaż ownership")
        transfer_btn.clicked.connect(self._transfer_ownership)
        btn_layout.addWidget(transfer_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Tabela członków
        self.members_table = QTableWidget()
        self.members_table.setColumnCount(4)
        self.members_table.setHorizontalHeaderLabels(["User ID", "Rola", "Data dodania", "Akcje"])
        self.members_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.members_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.members_table.setColumnWidth(0, 200)
        self.members_table.setColumnWidth(1, 100)
        self.members_table.setColumnWidth(2, 150)
        self.members_table.setColumnWidth(3, 150)
        layout.addWidget(self.members_table)
        
        # Przycisk zamknij
        close_layout = QHBoxLayout()
        close_layout.addStretch()
        
        close_btn = QPushButton("Zamknij")
        close_btn.clicked.connect(self.accept)
        close_layout.addWidget(close_btn)
        
        layout.addLayout(close_layout)
    
    def _refresh_members_list(self):
        """Odświeża listę członków z danych grupy."""
        from loguru import logger
        
        self.members_table.setRowCount(len(self.members))
        
        for row, member in enumerate(self.members):
            # User ID
            user_id_item = QTableWidgetItem(member.get("user_id", ""))
            user_id_item.setFlags(user_id_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.members_table.setItem(row, 0, user_id_item)
            
            # Rola
            role = member.get("role", "member")
            role_item = QTableWidgetItem(role.capitalize())
            role_item.setFlags(role_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            role_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.members_table.setItem(row, 1, role_item)
            
            # Data dodania
            joined_at = member.get("joined_at", "")
            date_item = QTableWidgetItem(str(joined_at)[:10] if joined_at else "N/A")
            date_item.setFlags(date_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.members_table.setItem(row, 2, date_item)
            
            # Przyciski akcji
            actions_widget = QWidget()
            actions_layout = QHBoxLayout(actions_widget)
            actions_layout.setContentsMargins(4, 2, 4, 2)
            actions_layout.setSpacing(4)
            
            # Przycisk Usuń (nie dla ownera i nie dla siebie jeśli jesteś ownerem)
            if role != "owner":
                remove_btn = QPushButton("🗑️ Usuń")
                remove_btn.setToolTip("Usuń członka z grupy")
                remove_btn.clicked.connect(lambda checked, m=member: self._remove_member(m))
                actions_layout.addWidget(remove_btn)
            
            actions_layout.addStretch()
            self.members_table.setCellWidget(row, 3, actions_widget)
        
        logger.debug(f"[GroupMembers] Members table refreshed with {len(self.members)} rows")
    
    def _add_member(self):
        """Dodaj nowego członka do grupy."""
        from loguru import logger
        
        # Dialog do wpisania user_id
        user_id, ok = QInputDialog.getText(
            self,
            "Dodaj członka",
            "Wprowadź User ID członka do dodania:"
        )
        
        if not ok or not user_id.strip():
            return
        
        # Sprawdź czy użytkownik już nie jest członkiem
        if any(m.get("user_id") == user_id.strip() for m in self.members):
            QMessageBox.warning(
                self,
                "Uwaga",
                f"Użytkownik {user_id} jest już członkiem tej grupy."
            )
            return
        
        # Wybór roli
        role, ok = QInputDialog.getItem(
            self,
            "Wybierz rolę",
            "Rola nowego członka:",
            ["member", "owner"],
            0,
            False
        )
        
        if not ok:
            return
        
        # Wywołaj API
        logger.info(f"[GroupMembers] Adding member {user_id} to group {self.group['id']}")
        response = self.api_client.add_member(
            group_id=self.group['id'],
            user_id=user_id.strip(),
            role=role
        )
        
        if response.success:
            logger.success(f"[GroupMembers] Member {user_id} added successfully")
            QMessageBox.information(
                self,
                "Sukces",
                f"Użytkownik {user_id} został dodany do grupy jako {role}."
            )
            # Odśwież dane grupy
            self._reload_group_data()
        else:
            logger.error(f"[GroupMembers] Failed to add member: {response.error}")
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się dodać członka:\n{response.error}"
            )
    
    def _remove_member(self, member: Dict):
        """Usuń członka z grupy."""
        from loguru import logger
        
        user_id = member.get("user_id")
        
        # Konfirmacja
        reply = QMessageBox.question(
            self,
            "Potwierdź usunięcie",
            f"Czy na pewno chcesz usunąć użytkownika {user_id} z grupy?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Wywołaj API
        logger.info(f"[GroupMembers] Removing member {user_id} from group {self.group['id']}")
        response = self.api_client.remove_member(
            group_id=self.group['id'],
            user_id=user_id
        )
        
        if response.success:
            logger.success(f"[GroupMembers] Member {user_id} removed successfully")
            QMessageBox.information(
                self,
                "Sukces",
                f"Użytkownik {user_id} został usunięty z grupy."
            )
            # Odśwież dane grupy
            self._reload_group_data()
        else:
            logger.error(f"[GroupMembers] Failed to remove member: {response.error}")
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się usunąć członka:\n{response.error}"
            )
    
    def _transfer_ownership(self):
        """Przekaż ownership grupy innemu członkowi."""
        from loguru import logger
        
        # Pobierz listę członków (bez ownera)
        non_owner_members = [
            m for m in self.members 
            if m.get("role") != "owner"
        ]
        
        if not non_owner_members:
            QMessageBox.warning(
                self,
                "Brak członków",
                "W grupie nie ma żadnych członków do których można przekazać ownership.\n"
                "Dodaj najpierw członków do grupy."
            )
            return
        
        # Dialog wyboru nowego ownera
        member_ids = [m.get("user_id", "") for m in non_owner_members]
        
        new_owner_id, ok = QInputDialog.getItem(
            self,
            "Przekaż ownership",
            "Wybierz nowego właściciela grupy:",
            member_ids,
            0,
            False
        )
        
        if not ok or not new_owner_id:
            return
        
        # Konfirmacja
        reply = QMessageBox.question(
            self,
            "Potwierdź przekazanie ownership",
            f"Czy na pewno chcesz przekazać ownership grupy użytkownikowi {new_owner_id}?\n\n"
            f"Po tej operacji stracisz uprawnienia właściciela.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Wywołaj API
        logger.info(f"[GroupMembers] Transferring ownership of group {self.group['id']} to {new_owner_id}")
        response = self.api_client.transfer_ownership(
            group_id=self.group['id'],
            new_owner_id=new_owner_id
        )
        
        if response.success:
            logger.success(f"[GroupMembers] Ownership transferred to {new_owner_id}")
            QMessageBox.information(
                self,
                "Sukces",
                f"Ownership grupy został przekazany użytkownikowi {new_owner_id}."
            )
            # Odśwież dane grupy
            self._reload_group_data()
        else:
            logger.error(f"[GroupMembers] Failed to transfer ownership: {response.error}")
            QMessageBox.critical(
                self,
                "Błąd",
                f"Nie udało się przekazać ownership:\n{response.error}"
            )
    
    def _reload_group_data(self):
        """Przeładuj dane grupy z API."""
        from loguru import logger
        
        logger.info(f"[GroupMembers] Reloading group {self.group['id']} data")
        response = self.api_client.get_group(group_id=self.group['id'])
        
        if response.success:
            updated_group = response.data
            self.group = updated_group
            self.members = updated_group.get("members", [])
            self._refresh_members_list()
            logger.success(f"[GroupMembers] Group data reloaded")
        else:
            logger.error(f"[GroupMembers] Failed to reload group: {response.error}")
            QMessageBox.warning(
                self,
                "Uwaga",
                "Nie udało się odświeżyć danych grupy. Zamknij i otwórz ponownie dialog."
            )


# =============================================================================
# Dialogi pomocnicze
# =============================================================================

class ContactEditDialog(QDialog):
    """Dialog edycji/dodawania kontaktu."""

    def __init__(self, parent=None, contact: Optional[Dict[str, str]] = None):
        super().__init__(parent)
        self.setWindowTitle("Edycja kontaktu" if contact else "Nowy kontakt")
        self.resize(400, 200)
        
        layout = QVBoxLayout(self)
        
        # Email
        layout.addWidget(QLabel("E-mail:"))
        self.email_edit = QLineEdit()
        if contact:
            self.email_edit.setText(contact["email"])
        layout.addWidget(self.email_edit)
        
        # Imię
        layout.addWidget(QLabel("Imię:"))
        self.first_name_edit = QLineEdit()
        if contact:
            self.first_name_edit.setText(contact["first_name"])
        layout.addWidget(self.first_name_edit)
        
        # Nazwisko
        layout.addWidget(QLabel("Nazwisko:"))
        self.last_name_edit = QLineEdit()
        if contact:
            self.last_name_edit.setText(contact["last_name"])
        layout.addWidget(self.last_name_edit)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        ok_btn = QPushButton("OK")
        ok_btn.clicked.connect(self._validate_and_accept)
        buttons_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)

    def _validate_and_accept(self):
        """Waliduje dane i akceptuje dialog."""
        if not self.email_edit.text().strip():
            QMessageBox.warning(self, "Błąd", "Podaj adres e-mail.")
            return
        
        if not self.first_name_edit.text().strip():
            QMessageBox.warning(self, "Błąd", "Podaj imię.")
            return
        
        if not self.last_name_edit.text().strip():
            QMessageBox.warning(self, "Błąd", "Podaj nazwisko.")
            return
        
        self.accept()

    def get_contact_data(self) -> Dict[str, str]:
        """Zwraca dane kontaktu."""
        return {
            "email": self.email_edit.text().strip(),
            "first_name": self.first_name_edit.text().strip(),
            "last_name": self.last_name_edit.text().strip(),
        }


class ContactSelectionDialog(QDialog):
    """Dialog wyboru kontaktów do dodania do zespołu."""

    def __init__(self, contacts: List[Dict[str, str]], parent=None):
        super().__init__(parent)
        self.setWindowTitle("Wybierz kontakty")
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Wybierz kontakty do dodania do zespołu:")
        layout.addWidget(label)
        
        self.contacts_list = QListWidget()
        self.contacts_list.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)
        
        for contact in contacts:
            display_name = f"{contact['first_name']} {contact['last_name']} ({contact['email']})"
            item = QListWidgetItem(display_name)
            item.setData(Qt.ItemDataRole.UserRole, contact["email"])
            self.contacts_list.addItem(item)
        
        layout.addWidget(self.contacts_list)
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        ok_btn = QPushButton("Dodaj")
        ok_btn.clicked.connect(self.accept)
        buttons_layout.addWidget(ok_btn)
        
        cancel_btn = QPushButton("Anuluj")
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        layout.addLayout(buttons_layout)

    def get_selected_emails(self) -> List[str]:
        """Zwraca listę wybranych adresów email."""
        return [item.data(Qt.ItemDataRole.UserRole) for item in self.contacts_list.selectedItems()]
