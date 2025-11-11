"""
Simple P-Web Dialogs
Dialogi do zarządzania grupami, tagami i zakładkami w module P-Web
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QDialogButtonBox,
    QColorDialog, QMessageBox, QCheckBox, QTextEdit, QComboBox,
    QWidget
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor

from ..utils.i18n_manager import t, get_i18n
from ..Modules.p_web.p_web_logic import PWebLogic
from loguru import logger


class GroupManagerDialog(QDialog):
    """Dialog do zarządzania grupami"""
    
    def __init__(self, logic: PWebLogic, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.setModal(True)
        self.resize(500, 400)
        
        self._setup_ui()
        self._load_groups()
        
        # i18n
        get_i18n().language_changed.connect(self.update_translations)
        self.update_translations()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        
        # Info
        self.info_label = QLabel()
        self.info_label.setObjectName("pweb_group_manager_info")
        layout.addWidget(self.info_label)
        
        # Lista grup
        self.group_list = QListWidget()
        self.group_list.setObjectName("pweb_group_list")
        layout.addWidget(self.group_list)
        
        # Przyciski akcji
        buttons_layout = QHBoxLayout()
        
        self.btn_add = QPushButton()
        self.btn_add.setObjectName("pweb_group_add")
        self.btn_add.clicked.connect(self._add_group)
        buttons_layout.addWidget(self.btn_add)
        
        self.btn_edit = QPushButton()
        self.btn_edit.setObjectName("pweb_group_edit")
        self.btn_edit.clicked.connect(self._edit_group)
        buttons_layout.addWidget(self.btn_edit)
        
        self.btn_delete = QPushButton()
        self.btn_delete.setObjectName("pweb_group_delete")
        self.btn_delete.clicked.connect(self._delete_group)
        buttons_layout.addWidget(self.btn_delete)
        
        layout.addLayout(buttons_layout)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.accept)
        layout.addWidget(self.button_box)
    
    def _load_groups(self):
        """Wczytuje grupy do listy"""
        self.group_list.clear()
        
        for group in self.logic.get_groups():
            item = QListWidgetItem(group['name'])
            item.setData(Qt.ItemDataRole.UserRole, group)
            
            # Kolor tła
            color = QColor(group['color'])
            item.setBackground(color)
            
            # Kolor tekstu (jasny/ciemny)
            if PWebLogic.is_dark_color(group['color']):
                item.setForeground(QColor(255, 255, 255))
            else:
                item.setForeground(QColor(0, 0, 0))
            
            self.group_list.addItem(item)
    
    def _add_group(self):
        """Dodaje nową grupę"""
        dialog = GroupEditDialog(None, self.logic, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            success, result = self.logic.add_group(data['name'], data['color'])
            
            if success:
                self._load_groups()
                logger.info(f"[GroupManager] Added group: {data['name']}")
            else:
                if result == "no_name":
                    QMessageBox.warning(self, t("pweb.group_manager_title"), t("pweb.error_no_group_name"))
                else:
                    QMessageBox.critical(self, t("pweb.group_manager_title"), 
                                       t("pweb.error_save_json").format(result))
    
    def _edit_group(self):
        """Edytuje wybraną grupę"""
        current_item = self.group_list.currentItem()
        if not current_item:
            QMessageBox.information(self, t("pweb.group_manager_title"), t("pweb.error_select_group"))
            return
        
        group = current_item.data(Qt.ItemDataRole.UserRole)
        
        if group['id'] == 'default':
            QMessageBox.warning(self, t("pweb.group_manager_title"), t("pweb.error_cannot_edit_default_group"))
            return
        
        dialog = GroupEditDialog(group, self.logic, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            success, error = self.logic.edit_group(group['id'], data['name'], data['color'])
            
            if success:
                self._load_groups()
                logger.info(f"[GroupManager] Edited group: {data['name']}")
            else:
                QMessageBox.critical(self, t("pweb.group_manager_title"), 
                                   t("pweb.error_save_json").format(error))
    
    def _delete_group(self):
        """Usuwa wybraną grupę"""
        current_item = self.group_list.currentItem()
        if not current_item:
            QMessageBox.information(self, t("pweb.group_manager_title"), t("pweb.error_select_group"))
            return
        
        group = current_item.data(Qt.ItemDataRole.UserRole)
        
        if group['id'] == 'default':
            QMessageBox.warning(self, t("pweb.group_manager_title"), t("pweb.error_cannot_delete_default_group"))
            return
        
        # Potwierdzenie
        reply = QMessageBox.question(
            self,
            t("pweb.group_manager_title"),
            t("pweb.confirm_delete_group").format(name=group['name']),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, error = self.logic.delete_group(group['id'])
            
            if success:
                self._load_groups()
                logger.info(f"[GroupManager] Deleted group: {group['name']}")
            else:
                QMessageBox.critical(self, t("pweb.group_manager_title"), 
                                   t("pweb.error_save_json").format(error))
    
    def update_translations(self):
        """Aktualizuje tłumaczenia"""
        self.setWindowTitle(t("pweb.group_manager_title"))
        self.info_label.setText(t("pweb.group_manager_info"))
        self.btn_add.setText(t("pweb.group_add"))
        self.btn_edit.setText(t("pweb.group_edit"))
        self.btn_delete.setText(t("pweb.group_delete"))


class GroupEditDialog(QDialog):
    """Dialog do dodawania/edycji grupy"""
    
    def __init__(self, group: dict, logic: PWebLogic, parent=None):
        super().__init__(parent)
        self.group = group
        self.logic = logic
        self.setModal(True)
        self.resize(400, 150)
        
        # Domyślny kolor
        self.selected_color = QColor(group['color']) if group else QColor("#2196F3")
        
        self._setup_ui()
        
        # Wypełnij danymi jeśli edycja
        if group:
            self.name_input.setText(group['name'])
        
        # i18n
        get_i18n().language_changed.connect(self.update_translations)
        self.update_translations()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        
        # Nazwa
        self.name_label = QLabel()
        self.name_label.setObjectName("pweb_group_edit_name_label")
        layout.addWidget(self.name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setObjectName("pweb_group_edit_name_input")
        layout.addWidget(self.name_input)
        
        # Kolor
        color_layout = QHBoxLayout()
        
        self.color_label = QLabel()
        self.color_label.setObjectName("pweb_group_edit_color_label")
        color_layout.addWidget(self.color_label)
        
        self.color_preview = QWidget()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.setObjectName("pweb_group_color_preview")
        self.update_color_preview()
        color_layout.addWidget(self.color_preview)
        
        self.color_button = QPushButton()
        self.color_button.setObjectName("pweb_group_choose_color")
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_button)
        
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def choose_color(self):
        """Wybór koloru"""
        color = QColorDialog.getColor(self.selected_color, self)
        if color.isValid():
            self.selected_color = color
            self.update_color_preview()
    
    def update_color_preview(self):
        """Aktualizuje podgląd koloru"""
        self.color_preview.setStyleSheet(
            f"background-color: {self.selected_color.name()}; border: 1px solid #000;"
        )
    
    def get_data(self):
        """Zwraca dane"""
        return {
            'name': self.name_input.text().strip(),
            'color': self.selected_color.name()
        }
    
    def update_translations(self):
        """Aktualizuje tłumaczenia"""
        if self.group:
            self.setWindowTitle(t("pweb.group_edit_dialog_title"))
        else:
            self.setWindowTitle(t("pweb.group_add_dialog_title"))
        
        self.name_label.setText(t("pweb.group_edit_name_label"))
        self.name_input.setPlaceholderText(t("pweb.group_edit_name_placeholder"))
        self.color_label.setText(t("pweb.group_edit_color_label"))
        self.color_button.setText(t("pweb.group_edit_choose_color"))


class TagManagerDialog(QDialog):
    """Dialog do zarządzania tagami"""
    
    def __init__(self, logic: PWebLogic, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.setModal(True)
        self.resize(400, 400)
        
        self._setup_ui()
        self._load_tags()
        
        # i18n
        get_i18n().language_changed.connect(self.update_translations)
        self.update_translations()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        
        # Info
        self.info_label = QLabel()
        self.info_label.setObjectName("pweb_tag_manager_info")
        layout.addWidget(self.info_label)
        
        # Lista tagów
        self.tag_list = QListWidget()
        self.tag_list.setObjectName("pweb_tag_list")
        layout.addWidget(self.tag_list)
        
        # Dodawanie nowego tagu
        add_layout = QHBoxLayout()
        
        self.tag_input = QLineEdit()
        self.tag_input.setObjectName("pweb_tag_input")
        add_layout.addWidget(self.tag_input)
        
        self.btn_add = QPushButton()
        self.btn_add.setObjectName("pweb_tag_add")
        self.btn_add.clicked.connect(self._add_tag)
        add_layout.addWidget(self.btn_add)
        
        layout.addLayout(add_layout)
        
        # Przycisk usuń
        self.btn_delete = QPushButton()
        self.btn_delete.setObjectName("pweb_tag_delete")
        self.btn_delete.clicked.connect(self._delete_tag)
        layout.addWidget(self.btn_delete)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        self.button_box.rejected.connect(self.accept)
        layout.addWidget(self.button_box)
    
    def _load_tags(self):
        """Wczytuje tagi do listy"""
        self.tag_list.clear()
        
        for tag in self.logic.get_tags():
            item = QListWidgetItem(tag)
            self.tag_list.addItem(item)
    
    def _add_tag(self):
        """Dodaje nowy tag"""
        tag = self.tag_input.text().strip()
        
        if not tag:
            QMessageBox.warning(self, t("pweb.tag_manager_title"), t("pweb.error_no_tag_name"))
            return
        
        success, error = self.logic.add_tag(tag)
        
        if success:
            self._load_tags()
            self.tag_input.clear()
            logger.info(f"[TagManager] Added tag: {tag}")
        else:
            if error == "tag_exists":
                QMessageBox.warning(self, t("pweb.tag_manager_title"), t("pweb.error_tag_exists"))
            else:
                QMessageBox.critical(self, t("pweb.tag_manager_title"), 
                                   t("pweb.error_save_json").format(error))
    
    def _delete_tag(self):
        """Usuwa wybrany tag"""
        current_item = self.tag_list.currentItem()
        if not current_item:
            QMessageBox.information(self, t("pweb.tag_manager_title"), t("pweb.error_select_tag"))
            return
        
        tag = current_item.text()
        
        # Potwierdzenie
        reply = QMessageBox.question(
            self,
            t("pweb.tag_manager_title"),
            t("pweb.confirm_delete_tag").format(tag=tag),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            success, error = self.logic.delete_tag(tag)
            
            if success:
                self._load_tags()
                logger.info(f"[TagManager] Deleted tag: {tag}")
            else:
                QMessageBox.critical(self, t("pweb.tag_manager_title"), 
                                   t("pweb.error_save_json").format(error))
    
    def update_translations(self):
        """Aktualizuje tłumaczenia"""
        self.setWindowTitle(t("pweb.tag_manager_title"))
        self.info_label.setText(t("pweb.tag_manager_info"))
        self.tag_input.setPlaceholderText(t("pweb.tag_input_placeholder"))
        self.btn_add.setText(t("pweb.tag_add"))
        self.btn_delete.setText(t("pweb.tag_delete"))


class QuickOpenDialog(QDialog):
    """Dialog do szybkiego otwierania URL bez zapisywania"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setModal(True)
        self.resize(500, 120)
        
        self._setup_ui()
        
        # i18n
        get_i18n().language_changed.connect(self.update_translations)
        self.update_translations()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)
        
        # Info
        self.info_label = QLabel()
        self.info_label.setObjectName("pweb_quick_open_info")
        layout.addWidget(self.info_label)
        
        # URL input
        self.url_input = QLineEdit()
        self.url_input.setObjectName("pweb_quick_open_url")
        layout.addWidget(self.url_input)
        
        # Buttons
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # Focus na input
        self.url_input.setFocus()
    
    def get_url(self):
        """Zwraca wprowadzony URL"""
        return self.url_input.text().strip()
    
    def update_translations(self):
        """Aktualizuje tłumaczenia"""
        self.setWindowTitle(t("pweb.quick_open_title"))
        self.info_label.setText(t("pweb.quick_open_info"))
        self.url_input.setPlaceholderText(t("pweb.quick_open_placeholder"))


class AddBookmarkDialog(QDialog):
    """Dialog do dodawania nowych zakładek (rozszerzony o grupy, tagi, ulubione)"""
    
    def __init__(self, logic: PWebLogic, parent=None):
        super().__init__(parent)
        self.logic = logic
        self.setModal(True)
        self.resize(500, 350)
        
        # Domyślny kolor
        self.selected_color = QColor("#4CAF50")
        
        self._setup_ui()
        
        # i18n
        get_i18n().language_changed.connect(self.update_translations)
        self.update_translations()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        layout = QVBoxLayout(self)
        
        # Nazwa strony
        self.name_label = QLabel()
        self.name_label.setObjectName("pweb_add_name_label")
        layout.addWidget(self.name_label)
        
        self.name_input = QLineEdit()
        self.name_input.setObjectName("pweb_add_name_input")
        layout.addWidget(self.name_input)
        
        # Adres URL
        self.url_label = QLabel()
        self.url_label.setObjectName("pweb_add_url_label")
        layout.addWidget(self.url_label)
        
        self.url_input = QLineEdit()
        self.url_input.setObjectName("pweb_add_url_input")
        layout.addWidget(self.url_input)
        
        # Grupa
        self.group_label = QLabel()
        self.group_label.setObjectName("pweb_add_group_label")
        layout.addWidget(self.group_label)
        
        self.group_combo = QComboBox()
        self.group_combo.setObjectName("pweb_add_group_combo")
        self._load_groups()
        layout.addWidget(self.group_combo)
        
        # Tagi
        self.tags_label = QLabel()
        self.tags_label.setObjectName("pweb_add_tags_label")
        layout.addWidget(self.tags_label)
        
        self.tags_input = QLineEdit()
        self.tags_input.setObjectName("pweb_add_tags_input")
        layout.addWidget(self.tags_input)
        
        # Wybór koloru
        color_layout = QHBoxLayout()
        
        self.color_label = QLabel()
        self.color_label.setObjectName("pweb_add_color_label")
        color_layout.addWidget(self.color_label)
        
        self.color_preview = QWidget()
        self.color_preview.setFixedSize(30, 30)
        self.color_preview.setObjectName("pweb_color_preview")
        self.update_color_preview()
        color_layout.addWidget(self.color_preview)
        
        self.color_button = QPushButton()
        self.color_button.setObjectName("pweb_choose_color_button")
        self.color_button.clicked.connect(self.choose_color)
        color_layout.addWidget(self.color_button)
        
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # Ulubiona
        self.favorite_checkbox = QCheckBox()
        self.favorite_checkbox.setObjectName("pweb_add_favorite_checkbox")
        layout.addWidget(self.favorite_checkbox)
        
        # Przyciski
        self.button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        self.button_box.setObjectName("pweb_add_button_box")
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def _load_groups(self):
        """Wczytuje grupy do ComboBox"""
        self.group_combo.clear()
        
        for group in self.logic.get_groups():
            self.group_combo.addItem(group['name'], group['id'])
    
    def choose_color(self):
        """Otwiera dialog wyboru koloru"""
        color = QColorDialog.getColor(self.selected_color, self, t("pweb.add_dialog_choose_color"))
        if color.isValid():
            self.selected_color = color
            self.update_color_preview()
    
    def update_color_preview(self):
        """Aktualizuje podgląd wybranego koloru"""
        self.color_preview.setStyleSheet(
            f"background-color: {self.selected_color.name()}; border: 1px solid #000;"
        )
    
    def get_data(self):
        """Zwraca wprowadzone dane"""
        # Parsuj tagi (rozdzielone przecinkami)
        tags_text = self.tags_input.text().strip()
        tags = [tag.strip() for tag in tags_text.split(',') if tag.strip()] if tags_text else []
        
        return {
            'name': self.name_input.text().strip(),
            'url': self.url_input.text().strip(),
            'color': self.selected_color.name(),
            'group_id': self.group_combo.currentData(),
            'tags': tags,
            'favorite': self.favorite_checkbox.isChecked()
        }
    
    def update_translations(self):
        """Aktualizuje tłumaczenia w dialogu"""
        self.setWindowTitle(t("pweb.add_dialog_title"))
        self.name_label.setText(t("pweb.add_dialog_name_label"))
        self.name_input.setPlaceholderText(t("pweb.add_dialog_name_placeholder"))
        self.url_label.setText(t("pweb.add_dialog_url_label"))
        self.url_input.setPlaceholderText(t("pweb.add_dialog_url_placeholder"))
        self.group_label.setText(t("pweb.add_dialog_group_label"))
        self.tags_label.setText(t("pweb.add_dialog_tags_label"))
        self.tags_input.setPlaceholderText(t("pweb.add_dialog_tags_placeholder"))
        self.color_label.setText(t("pweb.add_dialog_color_label"))
        self.color_button.setText(t("pweb.add_dialog_choose_color"))
        self.favorite_checkbox.setText(t("pweb.add_dialog_favorite"))


class SplitViewSelectDialog(QDialog):
    """Dialog wyboru strony do otwarcia w podzielonym widoku"""
    
    def __init__(self, logic, parent=None):
        super().__init__(parent)
        self.logic = logic
        self._setup_ui()
        self._load_bookmarks()
        
        # i18n
        get_i18n().language_changed.connect(self.update_translations)
        self.update_translations()
    
    def _setup_ui(self):
        """Konfiguracja UI"""
        self.setObjectName("split_view_select_dialog")
        self.setModal(True)
        self.resize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # Info
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        layout.addWidget(self.info_label)
        
        # Lista zakładek
        list_label = QLabel()
        list_label.setObjectName("list_label")
        layout.addWidget(list_label)
        self.list_label = list_label
        
        self.bookmark_combo = QComboBox()
        self.bookmark_combo.setObjectName("bookmark_combo")
        layout.addWidget(self.bookmark_combo)
        
        # Separator
        separator = QLabel("─" * 50)
        separator.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(separator)
        
        # Lub wpisz URL
        url_label = QLabel()
        url_label.setObjectName("url_label")
        layout.addWidget(url_label)
        self.url_label = url_label
        
        self.url_input = QLineEdit()
        self.url_input.setObjectName("url_input")
        self.url_input.setPlaceholderText("https://...")
        layout.addWidget(self.url_input)
        
        # Przyciski
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.ok_button = QPushButton()
        self.ok_button.setObjectName("ok_button")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton()
        self.cancel_button.setObjectName("cancel_button")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
    
    def _load_bookmarks(self):
        """Ładuje zakładki do combo"""
        self.bookmark_combo.clear()
        self.bookmark_combo.addItem("", None)  # Pusta opcja
        
        for bookmark in self.logic.get_bookmarks():
            self.bookmark_combo.addItem(bookmark['name'], bookmark['url'])
    
    def get_url(self):
        """Zwraca wybrany/wpisany URL"""
        # Najpierw sprawdź wpisany URL
        manual_url = self.url_input.text().strip()
        if manual_url:
            return manual_url
        
        # Następnie sprawdź wybraną zakładkę
        selected_url = self.bookmark_combo.currentData()
        if selected_url:
            return selected_url
        
        return None
    
    def update_translations(self):
        """Aktualizuje tłumaczenia"""
        self.setWindowTitle(t("pweb.split_select_dialog_title"))
        self.info_label.setText(t("pweb.split_select_dialog_info"))
        self.list_label.setText(t("pweb.split_select_from_list"))
        self.url_label.setText(t("pweb.split_or_enter_url"))
        self.ok_button.setText(t("common.ok"))
        self.cancel_button.setText(t("common.cancel"))

