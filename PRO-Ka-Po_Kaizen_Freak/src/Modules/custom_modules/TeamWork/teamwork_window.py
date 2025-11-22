"""Main window for the TeamWork collaborative module."""

from __future__ import annotations

from typing import List

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from .conversation_panel import ConversationPanel
from .data_sample import SAMPLE_GROUPS
from .dialogs import CreateGroupDialog, InvitationsDialog, MyGroupsDialog, ReplyDialog
from .group_tree_panel import GroupTreePanel


class TeamWorkWindow(QMainWindow):
    """Główne okno modułu TeamWork."""

    def __init__(self, groups: List[dict] | None = None, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("TeamWork – współpraca zespołu")
        self.resize(1200, 800)

        self._groups = groups or SAMPLE_GROUPS

        self._setup_toolbar()
        self._setup_body()

    def _setup_toolbar(self) -> None:
        toolbar = QToolBar("Nawigacja")
        toolbar.setMovable(False)
        self.addToolBar(Qt.ToolBarArea.TopToolBarArea, toolbar)

        btn_my_groups = QPushButton("👥 Zarządzanie zespołami")
        btn_my_groups.clicked.connect(self._open_my_groups_dialog)
        toolbar.addWidget(btn_my_groups)

        btn_create_group = QPushButton("➕ Utwórz grupę")
        btn_create_group.clicked.connect(self._open_create_group_dialog)
        toolbar.addWidget(btn_create_group)
        
        btn_create_topic = QPushButton("📝 Utwórz wątek")
        btn_create_topic.clicked.connect(self._open_create_topic_dialog)
        toolbar.addWidget(btn_create_topic)

        btn_invitations = QPushButton("📨 Zaproszenia")
        btn_invitations.clicked.connect(self._open_invitations_dialog)
        toolbar.addWidget(btn_invitations)

    def _setup_body(self) -> None:
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setChildrenCollapsible(False)
        splitter.setOpaqueResize(True)

        self.tree_panel = GroupTreePanel(self)
        self.tree_panel.set_groups(self._groups)
        self.tree_panel.group_selected.connect(self._handle_group_selected)
        self.tree_panel.topic_selected.connect(self._handle_topic_selected)
        self.tree_panel.topic_conversations_selected.connect(self._handle_topic_conversations)
        self.tree_panel.topic_files_selected.connect(self._handle_topic_files)
        self.tree_panel.topic_links_selected.connect(self._handle_topic_links)
        self.tree_panel.topic_tasks_selected.connect(self._handle_topic_tasks)
        self.tree_panel.topic_important_selected.connect(self._handle_topic_important)

        self.conversation_panel = ConversationPanel(self)
        self.conversation_panel.reply_requested.connect(self._handle_reply_requested)
        self.conversation_panel.create_task_requested.connect(self._handle_create_task)
        self.conversation_panel.view_gantt_requested.connect(self._handle_view_gantt)
        self.conversation_panel.toggle_important.connect(self._handle_toggle_important)

        splitter.addWidget(self.tree_panel)
        splitter.addWidget(self.conversation_panel)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 3)
        splitter.setSizes([300, 900])

        container = QWidget()
        self.setCentralWidget(container)

        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        container_layout.addWidget(splitter)

    def _handle_group_selected(self, group: dict) -> None:
        self.conversation_panel.display_group(group)

    def _handle_topic_selected(self, topic: dict) -> None:
        self.conversation_panel.display_topic(topic)

    def _handle_topic_conversations(self, topic: dict) -> None:
        self.conversation_panel.display_topic_conversations(topic)

    def _handle_topic_files(self, topic: dict) -> None:
        self.conversation_panel.display_topic_files(topic)

    def _handle_topic_links(self, topic: dict) -> None:
        self.conversation_panel.display_topic_links(topic)

    def _handle_topic_tasks(self, topic: dict) -> None:
        self.conversation_panel.display_topic_tasks(topic)

    def _handle_topic_important(self, topic: dict) -> None:
        self.conversation_panel.display_topic_important(topic)

    def _handle_toggle_important(self, item_type: str, item_id: str, topic_id: str) -> None:
        """Oznacza lub usuwa element z listy ważnych."""
        QMessageBox.information(
            self,
            "Oznacz jako ważne",
            f"Przełączono status 'ważne' dla:\nTyp: {item_type}\nID: {item_id}\n"
            f"W kolejnej iteracji zostanie zapisane w bazie danych.",
        )
        # TODO: Implementacja zapisu do bazy danych

    def _handle_reply_requested(self, topic: dict, message: dict) -> None:
        dialog = ReplyDialog(topic.get("title", "Temat"), self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            payload = dialog.get_payload()
            QMessageBox.information(
                self,
                "Odpowiedź zapisana",
                "W kolejnej iteracji zapiszemy odpowiedź do bazy.\n"
                f"Treść: {payload['message'][:80] or '(pusto)'}\n"
                f"Kolor tła: {payload['background_color']}",
            )

    def _handle_create_task(self, topic: dict) -> None:
        from .task_dialog import TaskDialog

        # Pobierz członków grupy z kontekstu
        group = self._find_group_for_topic(topic)
        members = group.get("members", []) if group else []

        dialog = TaskDialog(members, topic.get("title", ""), parent=self)
        if dialog.exec() == dialog.DialogCode.Accepted:
            task_data = dialog.get_task_data()
            QMessageBox.information(
                self,
                "Zadanie utworzone",
                f"Zadanie '{task_data['title']}' zostanie zapisane w bazie.\n"
                f"Odpowiedzialny: {task_data.get('assignee', '(brak)')}"
            )

    def _handle_view_gantt(self, topic: dict) -> None:
        from .task_widgets import GanttChartWidget

        gantt_dialog = QDialog(self)
        gantt_dialog.setWindowTitle(f"Widok Gantt: {topic.get('title', 'Temat')}")
        gantt_dialog.resize(900, 600)

        layout = QVBoxLayout(gantt_dialog)
        gantt_widget = GanttChartWidget()
        gantt_widget.set_tasks(topic.get("tasks", []), topic.get("title", ""))
        layout.addWidget(gantt_widget)

        from PyQt6.QtWidgets import QDialogButtonBox
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(gantt_dialog.reject)
        layout.addWidget(buttons)

        gantt_dialog.exec()

    def _find_group_for_topic(self, topic: dict) -> dict | None:
        """Znajduje grupę zawierającą dany temat."""
        topic_id = topic.get("id")
        if not topic_id:
            return None
        for group in self._groups:
            for t in group.get("topics", []):
                if t.get("id") == topic_id:
                    return group
        return None

    def _open_my_groups_dialog(self) -> None:
        from .team_management_dialog import TeamManagementDialog
        TeamManagementDialog(self).exec()

    def _open_create_group_dialog(self) -> None:
        dialog = CreateGroupDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            group_data = dialog.get_group_data()
            
            # Pokaż informacje o utworzonej grupie
            members_list = "\n".join(f"  • {email}" for email in group_data['members']) if group_data['members'] else "  (brak)"
            teams_list = "\n".join(f"  • {team}" for team in group_data['selected_teams']) if group_data['selected_teams'] else "  (brak)"
            
            message = (
                f"Utworzono grupę: {group_data['name']}\n\n"
                f"Opis:\n{group_data['description'] or '(brak)'}\n\n"
                f"Członkowie ({len(group_data['members'])}):\n{members_list}\n\n"
                f"Z zespołów:\n{teams_list}\n\n"
                "Grupa została utworzona. Teraz możesz w niej tworzyć wątki tematyczne.\n"
                "Grupa zostanie zapisana w bazie danych w kolejnej iteracji."
            )
            
            QMessageBox.information(self, "Grupa utworzona", message)

    def _open_create_topic_dialog(self) -> None:
        from .dialogs import CreateTopicDialog
        
        dialog = CreateTopicDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            topic_data = dialog.get_group_data()  # Używa tej samej nazwy metody
            
            # Pokaż informacje o utworzonym wątku
            files_list = "\n".join(f"  • {file}" for file in topic_data['files']) if topic_data['files'] else "  (brak)"
            links_list = "\n".join(f"  • {link['title'] or link['url']}" for link in topic_data['links']) if topic_data['links'] else "  (brak)"
            
            message = (
                f"Utworzono wątek: {topic_data['name']}\n"
                f"W grupie: {topic_data['group_name']}\n\n"
                f"Pierwsza wiadomość:\n{topic_data['initial_message']}\n\n"
                f"Pliki:\n{files_list}\n\n"
                f"Linki:\n{links_list}\n\n"
                "Dostęp do wątku będą mieli wszyscy członkowie wybranej grupy.\n"
                "Wątek zostanie zapisany w wybranej grupie w bazie danych."
            )
            
            QMessageBox.information(self, "Wątek utworzony", message)


    def _open_invitations_dialog(self) -> None:
        InvitationsDialog(self).exec()
