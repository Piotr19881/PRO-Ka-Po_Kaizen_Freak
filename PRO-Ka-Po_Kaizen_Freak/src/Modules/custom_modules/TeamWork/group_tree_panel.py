"""Tree panel presenting groups and topics for the TeamWork module."""

from __future__ import annotations

from typing import Dict, List, Optional

from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtWidgets import QLabel, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget


class GroupTreePanel(QWidget):
    """Widget z lewej strony prezentujący drzewo grup i tematów."""

    group_selected = pyqtSignal(dict)
    topic_selected = pyqtSignal(dict)
    topic_conversations_selected = pyqtSignal(dict)
    topic_files_selected = pyqtSignal(dict)
    topic_links_selected = pyqtSignal(dict)
    topic_tasks_selected = pyqtSignal(dict)
    topic_important_selected = pyqtSignal(dict)

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setObjectName("GroupTreePanel")
        self._groups: List[dict] = []
        self._topics_by_id: Dict[str, dict] = {}
        self.api_client = None  # TeamWorkAPIClient - ustawiony przez teamwork_module

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        header_label = QLabel("Struktura zespołów:")
        header_label.setObjectName("panelHeader")
        layout.addWidget(header_label)

        self.tree = QTreeWidget()
        self.tree.setObjectName("teamTree")
        self.tree.setHeaderHidden(True)
        self.tree.setUniformRowHeights(True)
        self.tree.setAnimated(True)
        self.tree.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.tree.currentItemChanged.connect(self._handle_selection_changed)
        layout.addWidget(self.tree)

    def set_groups(self, groups: List[dict]) -> None:
        """Aktualizuje dane drzewa."""
        self._groups = groups
        self._topics_by_id = {}
        self.tree.clear()

        for group in groups:
            group_item = QTreeWidgetItem([group.get("name", "Grupa")])
            group_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "group", "payload": group})
            self.tree.addTopLevelItem(group_item)

            for topic in group.get("topics", []):
                topic_id = topic.get("id") or topic.get("title")
                if topic_id:
                    self._topics_by_id[str(topic_id)] = topic

                topic_item = QTreeWidgetItem([topic.get("title", "Temat")])
                topic_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {"type": "topic", "payload": topic, "group": group},
                )
                group_item.addChild(topic_item)

                conv_item = QTreeWidgetItem(["Rozmowy"])
                conv_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {"type": "conversations", "payload": topic, "group": group},
                )
                topic_item.addChild(conv_item)

                files_item = QTreeWidgetItem(["Pliki"])
                files_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {"type": "files", "payload": topic, "group": group},
                )
                topic_item.addChild(files_item)

                links_item = QTreeWidgetItem(["Linki"])
                links_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {"type": "links", "payload": topic, "group": group},
                )
                topic_item.addChild(links_item)

                tasks_item = QTreeWidgetItem(["Zadania"])
                tasks_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {"type": "tasks", "payload": topic, "group": group},
                )
                topic_item.addChild(tasks_item)

                important_item = QTreeWidgetItem(["⭐ Ważne"])
                important_item.setData(
                    0,
                    Qt.ItemDataRole.UserRole,
                    {"type": "important", "payload": topic, "group": group},
                )
                topic_item.addChild(important_item)

            group_item.setExpanded(True)

        if self.tree.topLevelItemCount() > 0:
            self.tree.setCurrentItem(self.tree.topLevelItem(0))

    def _handle_selection_changed(self, current: Optional[QTreeWidgetItem], _previous: Optional[QTreeWidgetItem]) -> None:
        if current is None:
            return

        meta = current.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(meta, dict):
            return

        payload = meta.get("payload", {})
        if meta.get("type") == "group":
            self.group_selected.emit(payload)
        elif meta.get("type") == "topic":
            self.topic_selected.emit(payload)
        elif meta.get("type") == "conversations":
            self.topic_conversations_selected.emit(payload)
        elif meta.get("type") == "files":
            self.topic_files_selected.emit(payload)
        elif meta.get("type") == "links":
            self.topic_links_selected.emit(payload)
        elif meta.get("type") == "tasks":
            self.topic_tasks_selected.emit(payload)
        elif meta.get("type") == "important":
            self.topic_important_selected.emit(payload)

    def get_topic_by_id(self, topic_id: str) -> Optional[dict]:
        """Zwraca temat na podstawie identyfikatora."""
        return self._topics_by_id.get(topic_id)
    
    def select_topic_by_id(self, topic_id: int):
        """
        Wybiera wątek w drzewie na podstawie ID.
        
        Args:
            topic_id: ID wątku do wybrania
        """
        # Przeszukaj drzewo w poszukiwaniu topic item
        for i in range(self.tree.topLevelItemCount()):
            group_item = self.tree.topLevelItem(i)
            
            for j in range(group_item.childCount()):
                topic_item = group_item.child(j)
                meta = topic_item.data(0, Qt.ItemDataRole.UserRole)
                
                if isinstance(meta, dict):
                    payload = meta.get("payload", {})
                    if payload.get("id") == topic_id:
                        # Znaleziono topic - rozwiń grupę i zaznacz
                        group_item.setExpanded(True)
                        self.tree.setCurrentItem(topic_item)
                        return
        
        print(f"[GroupTreePanel] Topic {topic_id} not found in tree")
