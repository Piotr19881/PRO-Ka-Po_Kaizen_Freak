"""
Moduł okna nowej wiadomości email

Funkcjonalność:
- Tworzenie nowej wiadomości
- Odpowiadanie na wiadomości
- Przekazywanie wiadomości
- Załączniki
- Formatowanie tekstu
- Wybór podpisu
- Zapisywanie szkiców
- Wysyłanie wiadomości

Autor: Moduł dla aplikacji komercyjnej
Data: 2025-11-06
"""

import copy
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from PyQt6.QtCore import Qt, QMimeData, QUrl, QTimer, pyqtSignal
from PyQt6.QtGui import QAction, QBrush, QColor, QDrag, QFont, QTextCursor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QCompleter,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QTextEdit,
    QToolBar,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


class AttachmentListWidget(QListWidget):
    """Lista załączników obsługująca przeciąganie plików."""

    def __init__(self, dialog: "NewMailWindow") -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self.setAcceptDrops(True)
        viewport = self.viewport()
        if viewport is not None:
            viewport.setAcceptDrops(True)
        self.setDragEnabled(False)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)

    def _has_files(self, event) -> bool:
        if event is None:
            return False
        mime = event.mimeData()
        if mime is None:
            return False
        return mime.hasUrls()

    def dragEnterEvent(self, event):  # type: ignore[override]
        if self._has_files(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dragMoveEvent(self, event):  # type: ignore[override]
        if self._has_files(event):
            event.acceptProposedAction()
        else:
            event.ignore()

    def dropEvent(self, event):  # type: ignore[override]
        if not self._has_files(event):
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

        self._dialog.add_attachments_from_paths(file_paths)
        event.acceptProposedAction()


class ComposeFavoritesTreeWidget(QTreeWidget):
    """Drzewo ulubionych w oknie tworzenia wiadomości."""

    def __init__(self, dialog: "NewMailWindow") -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self.setAcceptDrops(False)
        self.setDragEnabled(True)
        self.setDefaultDropAction(Qt.DropAction.CopyAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)

    def startDrag(self, supported_actions):  # type: ignore[override]
        item = self.currentItem()
        if not isinstance(item, QTreeWidgetItem):
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            return
        file_path = data.get("path")
        if not file_path or not os.path.exists(file_path):
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(file_path))])

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)


class ComposeRecentFavoritesListWidget(QListWidget):
    """Lista ostatnio używanych ulubionych plików w oknie tworzenia wiadomości."""

    def __init__(self, dialog: "NewMailWindow") -> None:
        super().__init__(dialog)
        self._dialog = dialog
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setAlternatingRowColors(True)
        self.setDragEnabled(True)

    def startDrag(self, supported_actions):  # type: ignore[override]
        item = self.currentItem()
        if not isinstance(item, QListWidgetItem):
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if not isinstance(data, dict):
            return
        file_path = data.get("path")
        if not file_path or not os.path.exists(file_path):
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(str(file_path))])

        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec(Qt.DropAction.CopyAction)


class NewMailWindow(QDialog):
    """Okno tworzenia nowej wiadomości email"""
    
    mail_sent = pyqtSignal()  # Sygnał emitowany po wysłaniu maila
    
    def __init__(self, parent=None, reply_to=None, forward=None, is_reply=False, original_mail=None):
        super().__init__(parent)
        self.reply_to = reply_to or original_mail  # Obsługa obu parametrów
        self.is_reply = is_reply
        self.forward = forward
        self.mail_view_parent = parent if hasattr(parent, "favorite_files") else None
        self.favorite_files: List[Dict[str, Any]] = self._load_initial_favorites()
        self.group_definitions: Dict[str, Dict[str, str]] = self.load_group_definitions()
        self.attachments: List[str] = []
        self._attachment_lookup: set[str] = set()
        self.signatures = self.load_signatures()
        self.email_addresses = self.collect_email_addresses()  # Zbierz adresy do autouzupełniania
        
        # Auto-zapisywanie szkiców
        self.draft_file = Path("mail_client/drafts") / f"draft_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        self.draft_file.parent.mkdir(parents=True, exist_ok=True)
        self.autosave_timer = QTimer(self)
        self.autosave_timer.timeout.connect(self.autosave_draft)
        self.autosave_timer.start(2000)  # Co 2 sekundy
        
        self.init_ui()
        
        # Jeśli odpowiadamy lub przekazujemy
        if self.reply_to:
            self.setup_reply()
        elif forward:
            self.setup_forward()
        else:
            # Dodaj domyślny podpis dla nowej wiadomości
            self.add_default_signature()
            
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        self.setWindowTitle("Nowa wiadomość")
        self.setMinimumSize(900, 600)
        
        # Dodaj przyciski minimalizuj i maksymalizuj do paska okna
        self.setWindowFlags(
            Qt.WindowType.Window |
            Qt.WindowType.WindowMinimizeButtonHint |
            Qt.WindowType.WindowMaximizeButtonHint |
            Qt.WindowType.WindowCloseButtonHint
        )
        
        # Główny layout poziomy
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Panel szablonów (rozwijany, po lewej)
        try:
            from mail_templates import TemplatesPanel
            self.templates_panel = TemplatesPanel(self)
            self.templates_panel.setMaximumWidth(300)
            self.templates_panel.setVisible(False)  # Ukryty domyślnie
            self.templates_panel.template_selected.connect(self.insert_template)
            main_layout.addWidget(self.templates_panel)
        except ImportError:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from mail_templates import TemplatesPanel
            self.templates_panel = TemplatesPanel(self)
            self.templates_panel.setMaximumWidth(300)
            self.templates_panel.setVisible(False)
            self.templates_panel.template_selected.connect(self.insert_template)
            main_layout.addWidget(self.templates_panel)
        
        # Pionowy przycisk "Szablony" po lewej stronie
        self.templates_toggle_btn = QPushButton("S\nZ\nA\nB\nL\nO\nN\nY")
        self.templates_toggle_btn.setCheckable(True)
        self.templates_toggle_btn.setMaximumWidth(25)
        self.templates_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #FFA726;
                color: white;
                font-weight: bold;
                font-size: 10pt;
                border: none;
                border-radius: 3px;
                padding: 10px 2px;
            }
            QPushButton:hover {
                background-color: #FB8C00;
            }
            QPushButton:checked {
                background-color: #F57C00;
            }
        """)
        self.templates_toggle_btn.clicked.connect(self.toggle_templates_panel)
        main_layout.addWidget(self.templates_toggle_btn)
        
        # Główny obszar wiadomości
        message_widget = QWidget()
        layout = QVBoxLayout()
        message_widget.setLayout(layout)
        main_layout.addWidget(message_widget)
        
        # Pionowy przycisk "AI" po prawej stronie
        self.ai_toggle_btn = QPushButton("A\nI")
        self.ai_toggle_btn.setCheckable(True)
        self.ai_toggle_btn.setMaximumWidth(25)
        self.ai_toggle_btn.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                font-size: 12pt;
                border: none;
                border-radius: 3px;
                padding: 10px 2px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:checked {
                background-color: #388E3C;
            }
        """)
        self.ai_toggle_btn.clicked.connect(self.toggle_ai_panel)
        main_layout.addWidget(self.ai_toggle_btn)
        
        # Panel AI (rozwijany, po prawej)
        try:
            from mail_ai_panel import AIPanel
            self.ai_panel = AIPanel(self)
            self.ai_panel.setMaximumWidth(350)
            self.ai_panel.setVisible(False)  # Ukryty domyślnie
            main_layout.addWidget(self.ai_panel)
        except ImportError:
            import sys
            import os
            sys.path.insert(0, os.path.dirname(__file__))
            from mail_ai_panel import AIPanel
            self.ai_panel = AIPanel(self)
            self.ai_panel.setMaximumWidth(350)
            self.ai_panel.setVisible(False)
            main_layout.addWidget(self.ai_panel)
        
        # Toolbar z akcjami
        toolbar = self.create_toolbar()
        layout.addWidget(toolbar)
        
        # Formularz nagłówka
        form_layout = QFormLayout()
        
        # Od (konto) - załaduj prawdziwe konta z bazy
        self.from_combo = QComboBox()
        self.load_sender_accounts()
        form_layout.addRow("Od:", self.from_combo)
        
        # Do
        self.to_field = QLineEdit()
        self.to_field.setPlaceholderText("adresat@email.com (oddziel przecinkiem dla wielu)")
        # Autouzupełnianie dla pola Do
        to_completer = QCompleter(self.email_addresses)
        to_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        to_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.to_field.setCompleter(to_completer)
        form_layout.addRow("Do:", self.to_field)
        
        # DW (Do wiadomości - CC)
        self.cc_field = QLineEdit()
        self.cc_field.setPlaceholderText("kopia@email.com")
        # Autouzupełnianie dla pola DW
        cc_completer = QCompleter(self.email_addresses)
        cc_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        cc_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.cc_field.setCompleter(cc_completer)
        form_layout.addRow("DW:", self.cc_field)
        
        # UDW (Ukryte do wiadomości - BCC)
        self.bcc_field = QLineEdit()
        self.bcc_field.setPlaceholderText("ukryta.kopia@email.com")
        # Autouzupełnianie dla pola UDW
        bcc_completer = QCompleter(self.email_addresses)
        bcc_completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        bcc_completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self.bcc_field.setCompleter(bcc_completer)
        form_layout.addRow("UDW:", self.bcc_field)
        
        # Temat
        self.subject_field = QLineEdit()
        self.subject_field.setPlaceholderText("Temat wiadomości")
        subject_font = QFont()
        subject_font.setPointSize(11)
        self.subject_field.setFont(subject_font)
        form_layout.addRow("Temat:", self.subject_field)
        
        layout.addLayout(form_layout)
        
        # Separator
        separator = QLabel()
        separator.setStyleSheet("background-color: #cccccc;")
        separator.setFixedHeight(1)
        layout.addWidget(separator)
        
        # Treść wiadomości
        self.body_field = QTextEdit()
        self.body_field.setPlaceholderText("Napisz wiadomość...")
        body_font = QFont()
        body_font.setPointSize(10)
        self.body_field.setFont(body_font)
        layout.addWidget(self.body_field)
        
        # Sekcja podpisu
        signature_layout = QHBoxLayout()
        signature_layout.addWidget(QLabel("Podpis:"))
        
        self.signature_combo = QComboBox()
        self.signature_combo.addItem("(brak podpisu)", "")
        for sig in self.signatures:
            default_marker = " ⭐" if sig.get('default', False) else ""
            self.signature_combo.addItem(f"{sig['name']}{default_marker}", sig['content'])
        self.signature_combo.currentIndexChanged.connect(self.on_signature_changed)
        signature_layout.addWidget(self.signature_combo, 1)
        
        btn_insert_sig = QPushButton("Wstaw podpis")
        btn_insert_sig.clicked.connect(self.insert_signature)
        signature_layout.addWidget(btn_insert_sig)
        
        layout.addLayout(signature_layout)
        
        # Załączniki (przeniesione tutaj, po podpisie)
        attachments_layout = QHBoxLayout()
        
        self.attachments_label = QLabel("Załączniki: brak")
        attachments_layout.addWidget(self.attachments_label)
        
        attachments_layout.addStretch()
        
        btn_attach = QPushButton("📎 Dodaj załącznik")
        btn_attach.clicked.connect(self.add_attachment)
        attachments_layout.addWidget(btn_attach)
        
        layout.addLayout(attachments_layout)
        
        # Lista załączników z obsługą przeciągania
        self.attachments_list = AttachmentListWidget(self)
        self.attachments_list.setMaximumHeight(120)
        self.attachments_list.setVisible(False)
        layout.addWidget(self.attachments_list)

        # Panel ulubionych plików (przeniesiony tutaj, po załącznikach)
        self.favorites_toggle = QPushButton("⭐ Ulubione pliki ▼")
        self.favorites_toggle.setCheckable(True)
        self.favorites_toggle.setChecked(False)
        self.favorites_toggle.clicked.connect(self.toggle_favorites_panel)
        self.favorites_toggle.setStyleSheet(
            """
            QPushButton {
                background-color: #FFA726;
                color: white;
                font-weight: bold;
                border: none;
                padding: 4px;
                text-align: left;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #FB8C00;
            }
            """
        )
        layout.addWidget(self.favorites_toggle)

        self.favorites_panel = QWidget()
        self.favorites_panel.setVisible(False)
        favorites_layout = QVBoxLayout()
        favorites_layout.setContentsMargins(0, 0, 0, 0)
        favorites_layout.setSpacing(4)
        self.favorites_panel.setLayout(favorites_layout)

        self.favorites_tabs = QTabWidget()
        self.favorites_tabs.setTabPosition(QTabWidget.TabPosition.North)
        self.favorites_tabs.setElideMode(Qt.TextElideMode.ElideRight)
        favorites_layout.addWidget(self.favorites_tabs)

        groups_tab = QWidget()
        groups_layout = QVBoxLayout()
        groups_layout.setContentsMargins(0, 0, 0, 0)
        groups_layout.setSpacing(2)
        self.compose_favorites_tree = ComposeFavoritesTreeWidget(self)
        self.compose_favorites_tree.setHeaderLabels(["Plik", "Grupa/Tag"])
        self.compose_favorites_tree.setColumnWidth(0, 200)
        self.compose_favorites_tree.setAlternatingRowColors(True)
        self.compose_favorites_tree.itemDoubleClicked.connect(self.on_favorite_tree_double_clicked)
        groups_layout.addWidget(self.compose_favorites_tree)
        groups_tab.setLayout(groups_layout)
        self.favorites_tabs.addTab(groups_tab, "Grupy")

        recent_tab = QWidget()
        recent_layout = QVBoxLayout()
        recent_layout.setContentsMargins(0, 0, 0, 0)
        recent_layout.setSpacing(2)
        self.compose_recent_list = ComposeRecentFavoritesListWidget(self)
        self.compose_recent_list.itemDoubleClicked.connect(self.on_recent_favorite_item_double_clicked)
        recent_layout.addWidget(self.compose_recent_list)
        recent_tab.setLayout(recent_layout)
        self.favorites_tabs.addTab(recent_tab, "Ostatnie")

        layout.addWidget(self.favorites_panel)
        
        # Przyciski akcji
        buttons_layout = QHBoxLayout()
        
        btn_send = QPushButton("📧 Wyślij")
        btn_send.clicked.connect(self.send_mail)
        btn_send.setMinimumHeight(35)
        btn_send.setStyleSheet("""
            QPushButton {
                background-color: #4CAF50;
                color: white;
                font-weight: bold;
                border-radius: 3px;
                padding: 5px 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
        """)
        buttons_layout.addWidget(btn_send)
        
        btn_draft = QPushButton("💾 Zapisz szkic")
        btn_draft.clicked.connect(self.save_draft)
        btn_draft.setMinimumHeight(35)
        buttons_layout.addWidget(btn_draft)
        
        buttons_layout.addStretch()
        
        btn_cancel = QPushButton("❌ Anuluj")
        btn_cancel.clicked.connect(self.cancel)
        btn_cancel.setMinimumHeight(35)
        buttons_layout.addWidget(btn_cancel)
        
        layout.addLayout(buttons_layout)
        
        # Ustaw główny layout
        self.setLayout(main_layout)

        self.update_attachments_header()
        self.refresh_favorite_widgets()
        
    def _load_initial_favorites(self) -> List[Dict[str, Any]]:
        """Wczytuje listę ulubionych plików z rodzica lub z pliku."""
        parent_favorites = None
        if self.mail_view_parent and hasattr(self.mail_view_parent, "favorite_files"):
            parent_favorites = getattr(self.mail_view_parent, "favorite_files")

        source = parent_favorites if isinstance(parent_favorites, list) else self.load_favorite_files()
        normalized: List[Dict[str, Any]] = []
        for entry in source:
            if isinstance(entry, dict):
                normalized_entry = self._normalize_favorite_entry(copy.deepcopy(entry))
                if normalized_entry is not None:
                    normalized.append(normalized_entry)
        return normalized

    def load_favorite_files(self) -> List[Dict[str, Any]]:
        """Ładuje ulubione pliki z dysku."""
        favorites_file = Path("mail_client/favorite_files.json")
        if favorites_file.exists():
            try:
                with open(favorites_file, "r", encoding="utf-8") as handle:
                    raw_data = json.load(handle)
                if not isinstance(raw_data, list):
                    return []
                normalized: List[Dict[str, Any]] = []
                for entry in raw_data:
                    if isinstance(entry, dict):
                        normalized_entry = self._normalize_favorite_entry(entry)
                        if normalized_entry is not None:
                            normalized.append(normalized_entry)
                return normalized
            except Exception:
                return []
        return []

    def load_group_definitions(self) -> Dict[str, Dict[str, str]]:
        """Ładuje definicje grup ulubionych plików."""
        groups_file = Path("mail_client/file_groups.json")
        if groups_file.exists():
            try:
                with open(groups_file, "r", encoding="utf-8") as handle:
                    raw_data = json.load(handle)
                result: Dict[str, Dict[str, str]] = {}
                if isinstance(raw_data, list):
                    for entry in raw_data:
                        name = entry.get("name")
                        if not name:
                            continue
                        result[name] = {
                            "icon": entry.get("icon", "📂"),
                            "color": entry.get("color", "#FFFFFF"),
                        }
                return result
            except Exception:
                return {}
        return {}

    def _normalize_favorite_entry(self, entry: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalizuje strukturę danych ulubionego pliku."""
        path_value = entry.get("path")
        if not path_value:
            return None

        path = str(Path(path_value))
        name = entry.get("name") or Path(path).name
        group = entry.get("group") or "Bez grupy"

        tags_raw = entry.get("tags")
        if isinstance(tags_raw, list):
            tags = [str(tag).strip() for tag in tags_raw if str(tag).strip()]
        else:
            tags = []

        added_at = entry.get("added_at") if isinstance(entry.get("added_at"), str) else None
        if added_at:
            try:
                datetime.fromisoformat(added_at)
            except ValueError:
                added_at = None
        if not added_at:
            added_at = "1970-01-01T00:00:00"

        last_used_at = entry.get("last_used_at") if isinstance(entry.get("last_used_at"), str) else None
        if last_used_at:
            try:
                datetime.fromisoformat(last_used_at)
            except ValueError:
                last_used_at = None
        if not last_used_at:
            last_used_at = added_at

        return {
            "name": name,
            "path": path,
            "group": group,
            "tags": tags,
            "added_at": added_at,
            "last_used_at": last_used_at,
        }

    def toggle_favorites_panel(self, checked: bool) -> None:
        """Rozwija lub zwija panel ulubionych."""
        if hasattr(self, "favorites_panel"):
            self.favorites_panel.setVisible(checked)
        if hasattr(self, "favorites_toggle"):
            self.favorites_toggle.setText("⭐ Ulubione pliki ▲" if checked else "⭐ Ulubione pliki ▼")

    def refresh_favorite_widgets(self) -> None:
        """Odświeża widoczność i dane panelu ulubionych."""
        self.populate_favorite_groups()
        self.populate_recent_favorites_panel()

    def populate_favorite_groups(self) -> None:
        """Buduje drzewo grup ulubionych plików."""
        tree = getattr(self, "compose_favorites_tree", None)
        if tree is None:
            return

        tree.clear()
        groups: Dict[str, List[Dict[str, Any]]] = {}
        for favorite in self.favorite_files:
            group = favorite.get("group", "Bez grupy")
            groups.setdefault(group, []).append(favorite)

        for group_name, items in groups.items():
            group_info = self.group_definitions.get(group_name, {"icon": "📂", "color": "#FFFFFF"})
            icon = group_info.get("icon", "📂")
            color_value = group_info.get("color", "#FFFFFF")

            group_item = QTreeWidgetItem([f"{icon} {group_name}", ""])
            group_item.setData(0, Qt.ItemDataRole.UserRole, {"type": "group", "name": group_name})

            try:
                color = QColor(color_value)
                color.setAlpha(120)
                group_item.setBackground(0, QBrush(color))
                group_item.setBackground(1, QBrush(color))
            except Exception:
                pass

            font = group_item.font(0)
            font.setBold(True)
            group_item.setFont(0, font)

            for favorite in items:
                tags_text = ", ".join(favorite.get("tags", []))
                child = QTreeWidgetItem([
                    f"📄 {favorite.get('name', 'Plik')}",
                    tags_text,
                ])
                child.setData(0, Qt.ItemDataRole.UserRole, favorite)
                try:
                    child_color = QColor(color_value)
                    child_color.setAlpha(40)
                    child.setBackground(0, QBrush(child_color))
                    child.setBackground(1, QBrush(child_color))
                except Exception:
                    pass
                group_item.addChild(child)

            group_item.setExpanded(True)
            tree.addTopLevelItem(group_item)

    def populate_recent_favorites_panel(self, limit: int = 12) -> None:
        """Aktualizuje listę ostatnio używanych plików ulubionych."""
        recent_list = getattr(self, "compose_recent_list", None)
        if recent_list is None:
            return

        recent_list.clear()

        scored: List[tuple[datetime, Dict[str, Any]]] = []
        for favorite in self.favorite_files:
            timestamp_str = favorite.get("last_used_at") or favorite.get("added_at")
            timestamp = datetime.min
            if isinstance(timestamp_str, str):
                try:
                    timestamp = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    timestamp = datetime.min
            scored.append((timestamp, favorite))

        scored.sort(key=lambda item: item[0], reverse=True)

        for _, favorite in scored[:limit]:
            text = f"📄 {favorite.get('name', 'Plik')}"
            group_name = favorite.get("group", "Bez grupy")
            if group_name and group_name != "Bez grupy":
                text = f"{text} ({group_name})"
            item = QListWidgetItem(text)
            item.setToolTip(favorite.get("path", ""))
            item.setData(Qt.ItemDataRole.UserRole, favorite)
            recent_list.addItem(item)

    def on_favorite_tree_double_clicked(self, item, _column) -> None:
        """Obsługuje dodawanie ulubionego pliku do załączników poprzez dwuklik."""
        if item is None:
            return
        data = item.data(0, Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get("path"):
            self.add_attachments_from_paths([data["path"]])

    def on_recent_favorite_item_double_clicked(self, item) -> None:
        """Dodaje plik z zakładki 'Ostatnie' do załączników."""
        if item is None:
            return
        data = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(data, dict) and data.get("path"):
            self.add_attachments_from_paths([data["path"]])

    def add_attachments_from_paths(self, file_paths: List[str]) -> None:
        """Dodaje pliki do listy załączników, unikając duplikatów."""
        added = 0
        for raw_path in file_paths:
            if not raw_path:
                continue

            normalized = os.path.normcase(os.path.abspath(raw_path))
            if normalized in self._attachment_lookup:
                continue

            if not os.path.exists(raw_path):
                continue

            resolved = str(Path(raw_path))
            self._attachment_lookup.add(normalized)
            self.attachments.append(resolved)

            item = QListWidgetItem(Path(resolved).name)
            item.setToolTip(resolved)
            item.setData(Qt.ItemDataRole.UserRole, resolved)
            self.attachments_list.addItem(item)

            if self._find_favorite_by_path(resolved):
                self.record_favorite_usage(resolved)

            added += 1

        if added or not self.attachments:
            self.update_attachments_header()

    def update_attachments_header(self) -> None:
        """Aktualizuje etykietę i widoczność listy załączników."""
        if self.attachments:
            self.attachments_label.setText(f"Załączniki: {len(self.attachments)}")
            self.attachments_list.setVisible(True)
        else:
            self.attachments_label.setText("Załączniki: brak")
            self.attachments_list.setVisible(False)

    def _find_favorite_by_path(self, file_path: str) -> Optional[Dict[str, Any]]:
        """Zwraca wpis ulubionego dla danego pliku, jeśli istnieje."""
        normalized = os.path.normcase(os.path.abspath(file_path))
        for favorite in self.favorite_files:
            existing_path = favorite.get("path")
            if not existing_path:
                continue
            if os.path.normcase(os.path.abspath(existing_path)) == normalized:
                return favorite
        return None

    def record_favorite_usage(self, file_path: str) -> None:
        """Aktualizuje znacznik ostatniego użycia ulubionego pliku."""
        favorite = self._find_favorite_by_path(file_path)
        if favorite is None:
            return

        favorite["last_used_at"] = datetime.utcnow().isoformat()
        self.populate_recent_favorites_panel()

        if self.mail_view_parent and hasattr(self.mail_view_parent, "mark_favorite_used"):
            self.mail_view_parent.mark_favorite_used(file_path)

    def create_toolbar(self):
        """Tworzy toolbar z opcjami formatowania"""
        toolbar = QToolBar()
        toolbar.setMovable(False)
        
        # Formatowanie tekstu
        action_bold = QAction("B", self)
        action_bold.setStatusTip("Pogrubienie")
        action_bold.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        action_bold.triggered.connect(self.format_bold)
        toolbar.addAction(action_bold)
        
        action_italic = QAction("I", self)
        action_italic.setStatusTip("Kursywa")
        font_italic = QFont("Arial", 10)
        font_italic.setItalic(True)
        action_italic.setFont(font_italic)
        action_italic.triggered.connect(self.format_italic)
        toolbar.addAction(action_italic)
        
        action_underline = QAction("U", self)
        action_underline.setStatusTip("Podkreślenie")
        font_underline = QFont("Arial", 10)
        font_underline.setUnderline(True)
        action_underline.setFont(font_underline)
        action_underline.triggered.connect(self.format_underline)
        toolbar.addAction(action_underline)
        
        toolbar.addSeparator()
        
        # Rozmiar czcionki
        self.font_size_combo = QComboBox()
        self.font_size_combo.addItems(["8", "9", "10", "11", "12", "14", "16", "18", "20", "24"])
        self.font_size_combo.setCurrentText("10")
        self.font_size_combo.currentTextChanged.connect(self.change_font_size)
        toolbar.addWidget(QLabel(" Rozmiar: "))
        toolbar.addWidget(self.font_size_combo)
        
        toolbar.addSeparator()
        
        # Menedżer dokumentów
        action_document_manager = QAction('📚 Dokumenty', self)
        action_document_manager.setStatusTip('Otwórz menedżer dokumentów (szablony, ulubione, AI)')
        action_document_manager.triggered.connect(self.open_document_manager)
        toolbar.addAction(action_document_manager)
        
        return toolbar
        
    def setup_reply(self):
        """Ustawia pola dla odpowiedzi"""
        if self.reply_to:
            self.setWindowTitle("Odpowiedz")
            self.to_field.setText(self.reply_to["from"])
            self.subject_field.setText(f"Re: {self.reply_to['subject']}")
            
            # Cytuj oryginalną wiadomość
            original = f"\n\n--- Oryginalna wiadomość ---\n"
            original += f"Od: {self.reply_to['from']}\n"
            original += f"Data: {self.reply_to['date']}\n"
            original += f"Temat: {self.reply_to['subject']}\n\n"
            original += self.reply_to['body']
            
            self.body_field.setPlainText(original)
            # Przesuń kursor na początek
            cursor = self.body_field.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.body_field.setTextCursor(cursor)
            
    def setup_forward(self):
        """Ustawia pola dla przekazania"""
        if self.forward:
            self.setWindowTitle("Przekaż")
            self.subject_field.setText(f"Fwd: {self.forward['subject']}")
            
            # Dołącz oryginalną wiadomość
            forwarded = f"\n\n--- Przekazana wiadomość ---\n"
            forwarded += f"Od: {self.forward['from']}\n"
            forwarded += f"Data: {self.forward['date']}\n"
            forwarded += f"Temat: {self.forward['subject']}\n\n"
            forwarded += self.forward['body']
            
            self.body_field.setPlainText(forwarded)
            # Przesuń kursor na początek
            cursor = self.body_field.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.body_field.setTextCursor(cursor)
            
    def add_attachment(self):
        """Dodaje załącznik"""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Wybierz pliki do załączenia",
            "",
            "Wszystkie pliki (*.*)"
        )
        
        if files:
            self.add_attachments_from_paths(files)
            
    def format_bold(self):
        """Pogrubia tekst"""
        font = self.body_field.currentFont()
        font.setBold(not font.bold())
        self.body_field.setCurrentFont(font)
        
    def format_italic(self):
        """Ustawia kursywę"""
        font = self.body_field.currentFont()
        font.setItalic(not font.italic())
        self.body_field.setCurrentFont(font)
        
    def format_underline(self):
        """Podkreśla tekst"""
        font = self.body_field.currentFont()
        font.setUnderline(not font.underline())
        self.body_field.setCurrentFont(font)
        
    def change_font_size(self, size):
        """Zmienia rozmiar czcionki"""
        font = self.body_field.currentFont()
        font.setPointSize(int(size))
        self.body_field.setCurrentFont(font)
    
    def toggle_templates_panel(self, checked):
        """Pokazuje/ukrywa panel szablonów"""
        if hasattr(self, 'templates_panel'):
            self.templates_panel.setVisible(checked)
    
    def toggle_ai_panel(self, checked):
        """Pokazuje/ukrywa panel AI"""
        if hasattr(self, 'ai_panel'):
            self.ai_panel.setVisible(checked)
    
    def insert_template(self, template_content):
        """Wstawia szablon do treści wiadomości"""
        cursor = self.body_field.textCursor()
        cursor.insertText(template_content)
        self.body_field.setTextCursor(cursor)
        
    
    def open_document_manager(self):
        try:
            from mail_client.document_manager import DocumentManagerDialog
            dialog = DocumentManagerDialog(self)
            dialog.template_selected_callback = self.apply_template
            dialog.exec()
        except Exception as e:
            QMessageBox.critical(self, 'Błąd', f'Nie można otworzyć: {e}')
    
    def apply_template(self, template_data):
        try:
            if 'name' in template_data and not self.subject_field.text().strip():
                self.subject_field.setText(template_data['name'])
            if 'content' in template_data:
                if not self.body_field.toPlainText().strip():
                    self.body_field.setPlainText(template_data['content'])
                else:
                    cursor = self.body_field.textCursor()
                    cursor.movePosition(QTextCursor.MoveOperation.End)
                    cursor.insertText('\n\n' + template_data['content'])
                    self.body_field.setTextCursor(cursor)
        except Exception as e:
            QMessageBox.warning(self, 'Błąd', f'Nie można zastosować: {e}')
        
    def send_mail(self):
        """Wysyła wiadomość"""
        # Walidacja
        if not self.to_field.text().strip():
            QMessageBox.warning(self, "Błąd", "Podaj adres odbiorcy!")
            return
            
        if not self.subject_field.text().strip():
            reply = QMessageBox.question(
                self,
                "Brak tematu",
                "Wiadomość nie ma tematu. Czy chcesz ją wysłać?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
                
        # Symulacja wysyłania
        QMessageBox.information(
            self,
            "Sukces",
            f"Wiadomość została wysłana do:\n{self.to_field.text()}\n\n"
            f"(To jest symulacja - rzeczywista funkcja wysyłania zostanie "
            f"zaimplementowana po skonfigurowaniu kont pocztowych)"
        )
        
        # Zatrzymaj auto-zapis i usuń szkic po wysłaniu
        self.autosave_timer.stop()
        if self.draft_file.exists():
            try:
                self.draft_file.unlink()
            except Exception:
                pass
        
        # Emituj sygnał że mail został wysłany
        self.mail_sent.emit()
        
        self.accept()
        
    def autosave_draft(self):
        """Automatycznie zapisuje szkic co 2 sekundy"""
        # Sprawdź czy są jakieś dane do zapisania
        has_content = (
            self.to_field.text().strip() or
            self.subject_field.text().strip() or
            self.body_field.toPlainText().strip()
        )
        
        if not has_content:
            return
        
        try:
            draft_data = {
                "from": self.from_combo.currentData() or self.from_combo.currentText(),
                "to": self.to_field.text(),
                "cc": self.cc_field.text(),
                "bcc": self.bcc_field.text(),
                "subject": self.subject_field.text(),
                "body": self.body_field.toPlainText(),
                "attachments": self.attachments.copy(),
                "timestamp": datetime.now().isoformat()
            }
            
            with open(self.draft_file, 'w', encoding='utf-8') as f:
                json.dump(draft_data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass  # Ciche niepowodzenie przy auto-zapisie
    
    def save_draft(self):
        """Zapisuje szkic"""
        QMessageBox.information(
            self,
            "Szkic zapisany",
            "Wiadomość została zapisana w folderze Szkice"
        )
        
    def cancel(self):
        """Anuluje tworzenie wiadomości"""
        # Sprawdź czy są jakieś zmiany
        has_content = (
            self.to_field.text().strip() or
            self.subject_field.text().strip() or
            self.body_field.toPlainText().strip()
        )
        
        if has_content:
            reply = QMessageBox.question(
                self,
                "Potwierdzenie",
                "Czy na pewno chcesz anulować? Niezapisane zmiany zostaną utracone.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.autosave_timer.stop()  # Zatrzymaj auto-zapis
                self.reject()
        else:
            self.autosave_timer.stop()  # Zatrzymaj auto-zapis
            self.reject()
            
    def load_signatures(self):
        """Wczytuje podpisy z pliku"""
        signatures_file = Path("mail_client/mail_signatures.json")
        if signatures_file.exists():
            try:
                with open(signatures_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                return []
        return []
    
    def collect_email_addresses(self):
        """Zbiera wszystkie unikalne adresy email z różnych źródeł"""
        emails = set()
        
        # Z kont email
        accounts_file = Path("mail_client/mail_accounts.json")
        if accounts_file.exists():
            try:
                with open(accounts_file, 'r', encoding='utf-8') as f:
                    accounts = json.load(f)
                    for account in accounts:
                        if "email" in account:
                            emails.add(account["email"])
            except Exception:
                pass
        
        # Z wiadomości (nadawcy i odbiorcy) jeśli jest dostęp do parent
        if self.mail_view_parent and hasattr(self.mail_view_parent, "sample_mails"):
            for folder_mails in self.mail_view_parent.sample_mails.values():
                for mail in folder_mails:
                    # Dodaj nadawcę
                    if "from" in mail:
                        # Wyciągnij email z formatu "Name <email@domain.com>"
                        from_addr = mail["from"]
                        if "<" in from_addr and ">" in from_addr:
                            email_part = from_addr.split("<")[1].split(">")[0].strip()
                            emails.add(email_part)
                        else:
                            emails.add(from_addr.strip())
                    
                    # Dodaj odbiorców (jeśli są w polu 'to')
                    if "to" in mail:
                        to_addr = mail["to"]
                        if to_addr:
                            if "<" in to_addr and ">" in to_addr:
                                email_part = to_addr.split("<")[1].split(">")[0].strip()
                                emails.add(email_part)
                            else:
                                emails.add(to_addr.strip())
        
        # Z prawdziwych maili
        if self.mail_view_parent and hasattr(self.mail_view_parent, "real_mails"):
            for account_mails in self.mail_view_parent.real_mails.values():
                for mail in account_mails:
                    if "from" in mail:
                        from_addr = mail["from"]
                        if "<" in from_addr and ">" in from_addr:
                            email_part = from_addr.split("<")[1].split(">")[0].strip()
                            emails.add(email_part)
                        else:
                            emails.add(from_addr.strip())
        
        return sorted(list(emails))
    
    def load_sender_accounts(self):
        """Wczytuje konta email do pola Od"""
        accounts_file = Path("mail_client/mail_accounts.json")
        if accounts_file.exists():
            try:
                with open(accounts_file, 'r', encoding='utf-8') as f:
                    accounts = json.load(f)
                    for account in accounts:
                        if "email" in account:
                            # Wyświetl nazwę konta i email
                            name = account.get("name", account["email"])
                            if name and name != account["email"]:
                                display_text = f"{name} <{account['email']}>"
                            else:
                                display_text = account["email"]
                            self.from_combo.addItem(display_text, account["email"])
            except Exception:
                pass
        
        # Jeśli nie ma żadnych kont, dodaj placeholder
        if self.from_combo.count() == 0:
            self.from_combo.addItem("(Brak skonfigurowanych kont)", None)
    
    def add_default_signature(self):
        """Dodaje domyślny podpis do nowej wiadomości"""
        for sig in self.signatures:
            if sig.get('default', False):
                # Ustaw combo na domyślny podpis
                for i in range(self.signature_combo.count()):
                    if self.signature_combo.itemData(i) == sig['content']:
                        self.signature_combo.setCurrentIndex(i)
                        break
                # Automatycznie wstaw podpis
                self.insert_signature()
                break
    
    def on_signature_changed(self, index):
        """Obsługa zmiany wybranego podpisu"""
        # Możesz dodać logikę podglądu podpisu
        pass
    
    def insert_signature(self):
        """Wstawia wybrany podpis do treści wiadomości"""
        signature = self.signature_combo.currentData()
        if signature:
            # Pobierz aktualną treść
            current_text = self.body_field.toPlainText()
            
            # Usuń poprzedni podpis jeśli istnieje
            # (sprawdź czy na końcu jest separator podpisu)
            separator = "\n\n-- \n"
            if separator in current_text:
                # Usuń wszystko od separatora
                current_text = current_text.split(separator)[0]
            
            # Dodaj nowy podpis
            new_text = current_text + separator + signature
            self.body_field.setPlainText(new_text)
            
            # Przesuń kursor przed podpis
            cursor = self.body_field.textCursor()
            cursor.movePosition(QTextCursor.MoveOperation.Start)
            self.body_field.setTextCursor(cursor)


if __name__ == '__main__':
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    window = NewMailWindow()
    window.exec()
    sys.exit()
