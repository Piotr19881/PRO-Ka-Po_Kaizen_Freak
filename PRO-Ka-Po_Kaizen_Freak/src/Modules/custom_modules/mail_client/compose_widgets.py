"""
Widgety pomocnicze dla okna komponowania wiadomości email

- AttachmentListWidget: lista załączników z drag&drop
- ComposeFavoritesTreeWidget: drzewo ulubionych plików
- ComposeRecentFavoritesListWidget: lista ostatnio używanych plików
"""

from typing import List
from PyQt6.QtCore import Qt, QMimeData, QUrl
from PyQt6.QtGui import QDrag
from PyQt6.QtWidgets import QListWidget, QListWidgetItem, QTreeWidget, QTreeWidgetItem, QApplication


class AttachmentListWidget(QListWidget):
    """Widget listy załączników z obsługą drag and drop"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionMode(QListWidget.SelectionMode.ExtendedSelection)

    def _has_files(self, mime_data: QMimeData) -> bool:
        """Sprawdza czy dane MIME zawierają pliki"""
        if not mime_data.hasUrls():
            return False
        for url in mime_data.urls():
            if url.isLocalFile():
                return True
        return False

    def dragEnterEvent(self, event):
        """Obsługa wejścia przeciąganego elementu"""
        if self._has_files(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """Obsługa ruchu przeciąganego elementu"""
        if self._has_files(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):
        """Obsługa upuszczenia plików"""
        if self._has_files(event.mimeData()):
            paths = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    paths.append(url.toLocalFile())
            if paths and self.parent_window:
                self.parent_window.add_attachments_from_paths(paths)
            event.acceptProposedAction()
        else:
            event.ignore()


class ComposeFavoritesTreeWidget(QTreeWidget):
    """Widget drzewa ulubionych z drag and drop"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setDragEnabled(True)
        self.setAcceptDrops(False)

    def startDrag(self, supported_actions):
        """Rozpoczyna przeciąganie ulubionego pliku"""
        item = self.currentItem()
        if item and item.data(0, Qt.ItemDataRole.UserRole):
            drag = QDrag(self)
            mime_data = QMimeData()
            file_path = item.data(0, Qt.ItemDataRole.UserRole)
            mime_data.setUrls([QUrl.fromLocalFile(file_path)])
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)


class ComposeRecentFavoritesListWidget(QListWidget):
    """Widget listy ostatnio używanych ulubionych z drag and drop"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_window = parent
        self.setDragEnabled(True)
        self.setAcceptDrops(False)

    def startDrag(self, supported_actions):
        """Rozpoczyna przeciąganie ostatnio używanego pliku"""
        item = self.currentItem()
        if item and item.data(Qt.ItemDataRole.UserRole):
            drag = QDrag(self)
            mime_data = QMimeData()
            file_path = item.data(Qt.ItemDataRole.UserRole)
            mime_data.setUrls([QUrl.fromLocalFile(file_path)])
            drag.setMimeData(mime_data)
            drag.exec(Qt.DropAction.CopyAction)
