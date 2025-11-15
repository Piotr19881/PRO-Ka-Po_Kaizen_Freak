"""
Widgety dla mail_view - tabela maili, drzewa folderów, ulubione

Klasy:
- MailTableWidget - tabela z listą wiadomości + drag&drop
- FolderTreeWidget - drzewo folderów + obsługa drop maili
- FavoritesTreeWidget - drzewo ulubionych plików
- RecentFavoritesListWidget - lista ostatnio używanych
"""

from pathlib import Path
from typing import Any, Optional

from PyQt6.QtCore import Qt, QMimeData, QUrl
from PyQt6.QtGui import QDrag, QDragEnterEvent, QDragMoveEvent, QDropEvent
from PyQt6.QtWidgets import (
    QTableWidget,
    QTreeWidget,
    QTreeWidgetItem,
    QListWidget,
    QListWidgetItem,
    QAbstractItemView,
)


class MailTableWidget(QTableWidget):
    """Tabela wiadomości z obsługą przeciągania."""

    MIME_TYPE = "application/x-mail-item"

    def __init__(self, parent_view: Any) -> None:
        super().__init__(parent_view)
        self._mail_view = parent_view
        self.setDragEnabled(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DragOnly)
        viewport = self.viewport()
        if viewport is not None:
            viewport.setAcceptDrops(False)

    def startDrag(self, supported_actions):  # type: ignore[override]
        selected_indexes = self.selectedIndexes()
        if not selected_indexes:
            return
        rows = sorted({index.row() for index in selected_indexes})
        if not rows:
            return
        row = rows[0]
        mail = self._mail_view.get_mail_by_row(row)
        if mail is None:
            return

        uid = self._mail_view.ensure_mail_uid(mail)
        mime_data = QMimeData()
        mime_data.setData(self.MIME_TYPE, uid.encode("utf-8"))

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.MoveAction)
    
    def wheelEvent(self, event):
        """Obsługa Ctrl+Scroll dla zoomowania tabeli"""
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            delta = event.angleDelta().y()
            if delta > 0:
                self._mail_view.zoom_mail_table(110)
            else:
                self._mail_view.zoom_mail_table(90)
            event.accept()
        else:
            super().wheelEvent(event)


class FolderTreeWidget(QTreeWidget):
    """Drzewo folderów reagujące na drop maili."""

    MIME_TYPE = MailTableWidget.MIME_TYPE

    def __init__(self, parent_view: Any) -> None:
        super().__init__(parent_view)
        self._mail_view = parent_view
        self.setAcceptDrops(True)
        viewport = self.viewport()
        if viewport is not None:
            viewport.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QAbstractItemView.DragDropMode.DropOnly)

    def _accepts_mail_drag(self, event) -> bool:
        if event is None:
            return False
        mime = event.mimeData()
        if mime is None:
            return False
        if not mime.hasFormat(self.MIME_TYPE):
            return False
        return getattr(self._mail_view, "view_mode", "folders") == "folders"

    def dragEnterEvent(self, event: QDragEnterEvent):  # type: ignore[override]
        if event is None:
            return
        if self._accepts_mail_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event: QDragMoveEvent):  # type: ignore[override]
        if event is None:
            return
        if self._accepts_mail_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event: QDropEvent):  # type: ignore[override]
        if event is None:
            return
        if not self._accepts_mail_drag(event):
            event.ignore()
            return

        target_pos = event.position().toPoint()
        item = self.itemAt(target_pos)
        if not isinstance(item, QTreeWidgetItem):
            event.ignore()
            return

        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict) or data.get("type") != "folder":
            event.ignore()
            return

        folder_name = data.get("name")
        mime = event.mimeData()
        if mime is None:
            event.ignore()
            return
        raw_payload = mime.data(self.MIME_TYPE)
        if not folder_name or raw_payload.isEmpty():
            event.ignore()
            return

        try:
            payload_bytes = raw_payload.data()
            mail_uid = payload_bytes.decode("utf-8") if payload_bytes else ""
        except UnicodeDecodeError:
            event.ignore()
            return

        if not mail_uid:
            event.ignore()
            return

        moved = self._mail_view.handle_mail_drop(mail_uid, folder_name)
        if moved:
            event.acceptProposedAction()
        else:
            event.ignore()


class FavoritesTreeWidget(QTreeWidget):
    """Drzewo ulubionych obsługujące przeciąganie i upuszczanie plików."""

    def __init__(self, parent_view: Any) -> None:
        super().__init__(parent_view)
        self._mail_view = parent_view
        self.setAcceptDrops(True)
        viewport = self.viewport()
        if viewport is not None:
            viewport.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def startDrag(self, supported_actions):  # type: ignore[override]
        item = self.currentItem()
        if not isinstance(item, QTreeWidgetItem):
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict) or "path" not in data:
            return

        file_path = data.get("path")
        if not file_path or not Path(file_path).exists():
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(file_path))])

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)

    def _accepts_file_drag(self, event) -> bool:
        if event is None:
            return False
        mime = event.mimeData()
        if mime is None:
            return False
        return mime.hasUrls()

    def dragEnterEvent(self, event):  # type: ignore[override]
        if self._accepts_file_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # type: ignore[override]
        if self._accepts_file_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):  # type: ignore[override]
        if not self._accepts_file_drag(event):
            event.ignore()
            return

        mime = event.mimeData()
        if mime is None:
            event.ignore()
            return

        urls = [url for url in mime.urls() if url.isLocalFile()]
        file_paths = [url.toLocalFile() for url in urls]
        if not file_paths:
            event.ignore()
            return

        target_item = self.itemAt(event.position().toPoint())
        group_name = self._derive_group_name(target_item)

        if not self._mail_view.handle_favorite_drop(file_paths, group_name):
            event.ignore()
            return

        event.acceptProposedAction()

    def _derive_group_name(self, item: Optional[QTreeWidgetItem]) -> str:
        if isinstance(item, QTreeWidgetItem):
            data = item.data(0, Qt.ItemDataRole.UserRole)
            if isinstance(data, dict):
                if data.get("type") == "group":
                    return data.get("name", "Bez grupy")
                if data.get("type") == "recent":
                    return "Bez grupy"
                if "path" in data:
                    parent = item.parent()
                    return self._derive_group_name(parent)
        return "Bez grupy"


class RecentFavoritesListWidget(QListWidget):
    """Lista ostatnio używanych ulubionych plików."""

    def __init__(self, parent_view: Any) -> None:
        super().__init__(parent_view)
        self._mail_view = parent_view
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def startDrag(self, supported_actions):  # type: ignore[override]
        item = self.currentItem()
        if not isinstance(item, QListWidgetItem):
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            return
        file_path = data.get("path")
        if not file_path or not Path(file_path).exists():
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(file_path))])

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)

    def _accepts_file_drag(self, event) -> bool:
        if event is None:
            return False
        mime = event.mimeData()
        if mime is None:
            return False
        return mime.hasUrls()

    def dragEnterEvent(self, event):  # type: ignore[override]
        if self._accepts_file_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # type: ignore[override]
        if self._accepts_file_drag(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):  # type: ignore[override]
        if not self._accepts_file_drag(event):
            event.ignore()
            return

        mime = event.mimeData()
        if mime is None:
            event.ignore()
            return

        urls = [url for url in mime.urls() if url.isLocalFile()]
        file_paths = [url.toLocalFile() for url in urls]
        if not file_paths:
            event.ignore()
            return

        if not self._mail_view.handle_favorite_drop(file_paths, "Bez grupy"):
            event.ignore()
            return

        event.acceptProposedAction()
