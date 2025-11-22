"""
P-Web Tree Widget
Widget drzewa zakładek z filtrami i grupami
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLineEdit,
    QTreeWidget, QTreeWidgetItem, QCheckBox, QComboBox, QLabel
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor
from loguru import logger

from ...utils.i18n_manager import t, get_i18n
from .p_web_logic import PWebLogic


class PWebTreeWidget(QWidget):
    """Widget drzewa zakładek z filtrami"""
    
    # Sygnały
    bookmark_selected = pyqtSignal(dict)  # Emitowany gdy użytkownik wybierze zakładkę
    edit_groups_requested = pyqtSignal()  # Emitowany gdy kliknięto "Edytuj grupy"
    edit_tags_requested = pyqtSignal()  # Emitowany gdy kliknięto "Edytuj tagi"
    toggle_favorite_requested = pyqtSignal(dict)  # Emitowany gdy kliknięto "Ulubiona"
    open_in_split_requested = pyqtSignal(dict)  # Emitowany gdy "Otwórz w drugim oknie" z menu kontekstowego
    
    def __init__(self, logic: PWebLogic, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.current_bookmark = None  # Aktualnie wybrana zakładka
        
        self._setup_ui()
        self._connect_signals()
        
        # i18n
        get_i18n().language_changed.connect(self.update_translations)
        self.update_translations()
        
        # Załaduj dane
        self.refresh_tree()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # === Przyciski akcji ===
        buttons_layout = QHBoxLayout()
        
        self.btn_edit_groups = QPushButton("📂")
        self.btn_edit_groups.setObjectName("pweb_tree_edit_groups")
        self.btn_edit_groups.setMaximumWidth(40)
        buttons_layout.addWidget(self.btn_edit_groups)
        
        self.btn_edit_tags = QPushButton("🏷️")
        self.btn_edit_tags.setObjectName("pweb_tree_edit_tags")
        self.btn_edit_tags.setMaximumWidth(40)
        buttons_layout.addWidget(self.btn_edit_tags)
        
        self.btn_toggle_favorite = QPushButton("⭐")
        self.btn_toggle_favorite.setObjectName("pweb_tree_toggle_favorite")
        self.btn_toggle_favorite.setEnabled(False)  # Włącza się gdy coś wybrane
        self.btn_toggle_favorite.setMaximumWidth(40)
        buttons_layout.addWidget(self.btn_toggle_favorite)
        
        buttons_layout.addStretch()  # Przyciski po lewej stronie
        
        layout.addLayout(buttons_layout)
        
        # === Filtr frazy ===
        filter_layout = QHBoxLayout()
        
        self.filter_label = QLabel()
        self.filter_label.setObjectName("pweb_tree_filter_label")
        filter_layout.addWidget(self.filter_label)
        
        self.filter_input = QLineEdit()
        self.filter_input.setObjectName("pweb_tree_filter_input")
        self.filter_input.setClearButtonEnabled(True)
        filter_layout.addWidget(self.filter_input)
        
        layout.addLayout(filter_layout)
        
        # === Filtr tagu (z opcją "Ulubione" na końcu listy) ===
        tag_filter_layout = QHBoxLayout()
        
        self.tag_filter_label = QLabel()
        self.tag_filter_label.setObjectName("pweb_tree_tag_filter_label")
        tag_filter_layout.addWidget(self.tag_filter_label)
        
        self.tag_filter_combo = QComboBox()
        self.tag_filter_combo.setObjectName("pweb_tree_tag_filter_combo")
        tag_filter_layout.addWidget(self.tag_filter_combo)
        
        layout.addLayout(tag_filter_layout)
        
        # === Drzewo zakładek ===
        self.tree = QTreeWidget()
        self.tree.setObjectName("pweb_tree")
        self.tree.setHeaderHidden(True)
        self.tree.setAnimated(True)
        self.tree.setIndentation(20)
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        layout.addWidget(self.tree)
    
    def _connect_signals(self):
        """Połączenia sygnałów"""
        self.btn_edit_groups.clicked.connect(self.edit_groups_requested.emit)
        self.btn_edit_tags.clicked.connect(self.edit_tags_requested.emit)
        self.btn_toggle_favorite.clicked.connect(self._on_toggle_favorite)
        
        self.filter_input.textChanged.connect(self._on_filter_changed)
        self.tag_filter_combo.currentIndexChanged.connect(self._on_filter_changed)
        
        self.tree.itemClicked.connect(self._on_item_clicked)
        self.tree.itemDoubleClicked.connect(self._on_item_double_clicked)
        
        # Menu kontekstowe
        self.tree.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._on_tree_context_menu)
    
    def _on_filter_changed(self):
        """Obsługa zmiany filtrów"""
        self.refresh_tree()
    
    def _on_item_clicked(self, item: QTreeWidgetItem, column: int):
        """Obsługa kliknięcia na element"""
        bookmark = item.data(0, Qt.ItemDataRole.UserRole)
        
        if bookmark:
            self.current_bookmark = bookmark
            self.btn_toggle_favorite.setEnabled(True)
            
            # Aktualizuj tekst przycisku ulubionej
            if bookmark.get('favorite', False):
                self.btn_toggle_favorite.setText(t("pweb.tree_unfavorite"))
            else:
                self.btn_toggle_favorite.setText(t("pweb.tree_favorite"))
        else:
            self.current_bookmark = None
            self.btn_toggle_favorite.setEnabled(False)
    
    def _on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        """Obsługa dwukliku - otwiera zakładkę"""
        bookmark = item.data(0, Qt.ItemDataRole.UserRole)
        
        if bookmark:
            self.bookmark_selected.emit(bookmark)
            logger.debug(f"[PWebTree] Double-clicked bookmark: {bookmark['name']}")
    
    def _on_toggle_favorite(self):
        """Obsługa przycisku ulubionej"""
        if self.current_bookmark:
            self.toggle_favorite_requested.emit(self.current_bookmark)
    
    def _on_tree_context_menu(self, position):
        """Obsługa menu kontekstowego na drzewie"""
        from PyQt6.QtWidgets import QMenu
        
        item = self.tree.itemAt(position)
        if not item:
            return
        
        bookmark = item.data(0, Qt.ItemDataRole.UserRole)
        if not bookmark:
            # Kliknięto na grupę, nie na zakładkę
            return
        
        menu = QMenu(self)
        
        # Otwórz normalnie
        open_action = menu.addAction(t("pweb.context.open_normal"))
        open_action.triggered.connect(
            lambda: self.bookmark_selected.emit(bookmark)
        )
        
        # Otwórz w podzielonym widoku
        split_action = menu.addAction(t("pweb.context.open_in_split"))
        split_action.triggered.connect(
            lambda: self.open_in_split_requested.emit(bookmark)
        )
        
        menu.addSeparator()
        
        # Toggle ulubiona
        if bookmark.get('favorite'):
            fav_action = menu.addAction(t("pweb.context.remove_favorite"))
        else:
            fav_action = menu.addAction(t("pweb.context.add_favorite"))
        
        fav_action.triggered.connect(
            lambda: self.toggle_favorite_requested.emit(bookmark)
        )
        
        menu.exec(self.tree.viewport().mapToGlobal(position))
    
    def refresh_tree(self):
        """Odświeża drzewo zakładek z uwzględnieniem filtrów"""
        self.tree.clear()
        
        # Pobierz filtry
        phrase = self.filter_input.text().strip()
        selected_tag = self.tag_filter_combo.currentData()
        
        # Sprawdź czy wybrano "Ulubione" (specjalna wartość)
        tag = None
        favorites_only = False
        
        if selected_tag == "__favorites__":
            favorites_only = True
        elif selected_tag:  # Normalny tag (nie "Wszystkie tagi")
            tag = selected_tag
        
        # Aktualizuj combo tagów
        self._update_tag_combo()
        
        # Pobierz zakładki z filtrami
        bookmarks = self.logic.get_bookmarks(
            tag=tag,
            favorites_only=favorites_only,
            phrase=phrase
        )
        
        if not bookmarks:
            # Brak zakładek
            no_bookmarks_item = QTreeWidgetItem(self.tree)
            no_bookmarks_item.setText(0, t("pweb.tree_no_bookmarks"))
            no_bookmarks_item.setForeground(0, QColor(128, 128, 128))
            return
        
        # Grupuj po group_id
        groups_dict = {}
        for bookmark in bookmarks:
            group_id = bookmark.get('group_id', 'default')
            if group_id not in groups_dict:
                groups_dict[group_id] = []
            groups_dict[group_id].append(bookmark)
        
        # Dodaj grupy do drzewa
        for group in self.logic.get_groups():
            group_id = group['id']
            
            if group_id not in groups_dict:
                continue  # Pomiń puste grupy
            
            # Element grupy
            group_item = QTreeWidgetItem(self.tree)
            group_item.setText(0, f"📁 {group['name']} ({len(groups_dict[group_id])})")
            group_item.setExpanded(True)
            
            # Kolor grupy
            color = QColor(group['color'])
            group_item.setBackground(0, color)
            
            # Kolor tekstu (jasny/ciemny)
            if PWebLogic.is_dark_color(group['color']):
                group_item.setForeground(0, QColor(255, 255, 255))
            else:
                group_item.setForeground(0, QColor(0, 0, 0))
            
            # Dodaj zakładki do grupy
            for bookmark in sorted(groups_dict[group_id], key=lambda b: b['name'].lower()):
                bookmark_item = QTreeWidgetItem(group_item)
                
                # Ikona ulubionej
                icon = "⭐ " if bookmark.get('favorite', False) else "🔖 "
                
                # Nazwa + tagi
                tags_text = ""
                if bookmark.get('tags'):
                    tags_text = f" [{', '.join(bookmark['tags'])}]"
                
                bookmark_item.setText(0, f"{icon}{bookmark['name']}{tags_text}")
                bookmark_item.setData(0, Qt.ItemDataRole.UserRole, bookmark)
                
                # Kolor zakładki
                color = QColor(bookmark['color'])
                bookmark_item.setForeground(0, color)
        
        logger.debug(f"[PWebTree] Refreshed tree with {len(bookmarks)} bookmarks")
    
    def _update_tag_combo(self):
        """Aktualizuje combo box z tagami (z opcją Ulubione na końcu)"""
        current_tag = self.tag_filter_combo.currentData()
        
        self.tag_filter_combo.blockSignals(True)
        self.tag_filter_combo.clear()
        
        # Wszystkie tagi
        self.tag_filter_combo.addItem(t("pweb.tree_all_tags"), None)
        
        # Dodaj tagi
        for tag in self.logic.get_tags():
            self.tag_filter_combo.addItem(tag, tag)
        
        # Separator (opcjonalnie można dodać pustą linię)
        if self.logic.get_tags():  # Tylko jeśli są jakieś tagi
            self.tag_filter_combo.insertSeparator(self.tag_filter_combo.count())
        
        # Ulubione na końcu
        self.tag_filter_combo.addItem("⭐ " + t("pweb.tree_favorites_only"), "__favorites__")
        
        # Przywróć wybór jeśli możliwe
        if current_tag:
            for i in range(self.tag_filter_combo.count()):
                if self.tag_filter_combo.itemData(i) == current_tag:
                    self.tag_filter_combo.setCurrentIndex(i)
                    break
        
        self.tag_filter_combo.blockSignals(False)
    
    def get_selected_bookmark(self):
        """Zwraca aktualnie wybraną zakładkę"""
        return self.current_bookmark
    
    def update_translations(self):
        """Aktualizuje tłumaczenia"""
        self.btn_edit_groups.setToolTip(t("pweb.tree_edit_groups_tooltip"))
        self.btn_edit_tags.setToolTip(t("pweb.tree_edit_tags_tooltip"))
        
        # Przycisk ulubionej - tylko ikona
        if self.current_bookmark and self.current_bookmark.get('favorite', False):
            self.btn_toggle_favorite.setToolTip(t("pweb.tree_unfavorite"))
        else:
            self.btn_toggle_favorite.setToolTip(t("pweb.tree_favorite"))
        
        self.filter_label.setText(t("pweb.tree_filter_label"))
        self.filter_input.setPlaceholderText(t("pweb.tree_filter_placeholder"))
        
        self.tag_filter_label.setText(t("pweb.tree_tag_filter_label"))
        
        # Odśwież drzewo (nazwy mogły się zmienić)
        self.refresh_tree()
