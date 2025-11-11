# -*- coding: utf-8 -*-
"""Moduł menedżera dokumentów - ulubione, szablony, AI"""

import json
import os
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QGuiApplication
from PyQt6.QtWidgets import (
    QCheckBox, QComboBox, QDialog, QFileDialog, QFormLayout,
    QHBoxLayout, QInputDialog, QLabel, QLineEdit, QListWidget,
    QListWidgetItem, QMenu, QMessageBox, QPushButton, QSpinBox,
    QTabWidget, QTextEdit, QVBoxLayout, QWidget
)


class DocumentManagerDialog(QDialog):
    """Dialog zarządzania dokumentami"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Menedżer dokumentów")
        self.resize(800, 600)
        self.template_selected_callback = None
        self.mail_client_dir = Path(__file__).parent
        self.favorites_file = self.mail_client_dir / "favorite_files.json"
        self.templates_file = self.mail_client_dir / "document_templates.json"
        self.ai_sources_file = self.mail_client_dir / "ai_knowledge_sources.json"
        self.setup_ui()
        self.load_data()    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        self.favorites_tab = QWidget()
        self.setup_favorites_tab()
        self.tabs.addTab(self.favorites_tab, "📂 Ulubione pliki")
        self.templates_tab = QWidget()
        self.setup_templates_tab()
        self.tabs.addTab(self.templates_tab, "📄 Szablony")
        self.ai_sources_tab = QWidget()
        self.setup_ai_sources_tab()
        self.tabs.addTab(self.ai_sources_tab, "🤖 Źródła AI")
        layout.addWidget(self.tabs)
        buttons_layout = QHBoxLayout()
        btn_close = QPushButton("Zamknij")
        btn_close.clicked.connect(self.accept)
        buttons_layout.addStretch()
        buttons_layout.addWidget(btn_close)
        layout.addLayout(buttons_layout)
    
    def setup_favorites_tab(self):
        layout = QVBoxLayout(self.favorites_tab)
        self.favorites_list = QListWidget()
        self.favorites_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.favorites_list.customContextMenuRequested.connect(self.show_favorites_context_menu)
        self.favorites_list.itemDoubleClicked.connect(self.open_favorite_file)
        layout.addWidget(self.favorites_list)
        buttons_layout = QHBoxLayout()
        btn_add = QPushButton("➕ Dodaj plik")
        btn_add.clicked.connect(self.add_favorite_file)
        buttons_layout.addWidget(btn_add)
        btn_add_folder = QPushButton("📁 Dodaj folder")
        btn_add_folder.clicked.connect(self.add_favorite_folder)
        buttons_layout.addWidget(btn_add_folder)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
    
    def setup_templates_tab(self):
        layout = QVBoxLayout(self.templates_tab)
        self.templates_list = QListWidget()
        self.templates_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.templates_list.customContextMenuRequested.connect(self.show_templates_context_menu)
        self.templates_list.itemDoubleClicked.connect(self.edit_template)
        layout.addWidget(self.templates_list)
        buttons_layout = QHBoxLayout()
        btn_add = QPushButton("➕ Nowy szablon")
        btn_add.clicked.connect(self.add_template)
        buttons_layout.addWidget(btn_add)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
    
    def setup_ai_sources_tab(self):
        layout = QVBoxLayout(self.ai_sources_tab)
        self.ai_sources_list = QListWidget()
        self.ai_sources_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.ai_sources_list.customContextMenuRequested.connect(self.show_ai_sources_context_menu)
        layout.addWidget(self.ai_sources_list)
        buttons_layout = QHBoxLayout()
        btn_add = QPushButton("➕ Nowe źródło")
        btn_add.clicked.connect(self.add_ai_source)
        buttons_layout.addWidget(btn_add)
        buttons_layout.addStretch()
        layout.addLayout(buttons_layout)
    
    def load_favorites(self):
        if not self.favorites_file.exists():
            return []
        try:
            with open(self.favorites_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    
    def save_favorites(self, favorites):
        try:
            with open(self.favorites_file, "w", encoding="utf-8") as f:
                json.dump(favorites, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można zapisać: {e}")
    
    def add_favorite_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Wybierz plik")
        if file_path:
            favorites = self.load_favorites()
            if not any(f.get("path") == file_path for f in favorites):
                favorites.append({"path": file_path, "name": Path(file_path).name, "type": "file"})
                self.save_favorites(favorites)
                self.refresh_favorites_list()
    
    def add_favorite_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "Wybierz folder")
        if folder_path:
            favorites = self.load_favorites()
            if not any(f.get("path") == folder_path for f in favorites):
                favorites.append({"path": folder_path, "name": Path(folder_path).name, "type": "folder"})
                self.save_favorites(favorites)
                self.refresh_favorites_list()
    
    def refresh_favorites_list(self):
        self.favorites_list.clear()
        for fav in self.load_favorites():
            icon = "📁" if fav.get("type") == "folder" else "📄"
            item = QListWidgetItem(f"{icon} {fav.get('name', 'Bez nazwy')}")
            item.setData(Qt.ItemDataRole.UserRole, fav)
            self.favorites_list.addItem(item)
    
    def show_favorites_context_menu(self, position):
        item = self.favorites_list.itemAt(position)
        if not item:
            return
        fav_data = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        action_open = QAction("📂 Otwórz", self)
        action_open.triggered.connect(lambda: self.open_favorite_file(item))
        menu.addAction(action_open)
        action_show = QAction("📁 Pokaż w Eksploratorze", self)
        action_show.triggered.connect(lambda: self.show_in_explorer(fav_data.get("path")))
        menu.addAction(action_show)
        menu.addSeparator()
        action_delete = QAction("🗑️ Usuń", self)
        action_delete.triggered.connect(lambda: self.delete_favorite(item))
        menu.addAction(action_delete)
        menu.exec(self.favorites_list.mapToGlobal(position))
    
    def open_favorite_file(self, item):
        if isinstance(item, QListWidgetItem):
            path = item.data(Qt.ItemDataRole.UserRole).get("path")
            if path and Path(path).exists():
                try:
                    os.startfile(path)
                except Exception as e:
                    QMessageBox.warning(self, "Błąd", f"Nie można otworzyć: {e}")
    
    def show_in_explorer(self, path):
        if path and Path(path).exists():
            try:
                subprocess.run(['explorer', '/select,', path])
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Błąd: {e}")
    
    def delete_favorite(self, item):
        if QMessageBox.question(self, "Potwierdzenie", "Usunąć?") == QMessageBox.StandardButton.Yes:
            fav_data = item.data(Qt.ItemDataRole.UserRole)
            favorites = [f for f in self.load_favorites() if f.get("path") != fav_data.get("path")]
            self.save_favorites(favorites)
            self.refresh_favorites_list()
    
    def load_templates(self):
        if not self.templates_file.exists():
            defaults = [
                {"name": "Szablon oferty", "category": "Biznesowe", "content": "Szanowni Państwo,\n\nW odpowiedzi na Państwa zapytanie...\n\nPozdrawiam"},
                {"name": "Podziękowanie", "category": "Biznesowe", "content": "Dziękujemy za zamówienie!\n\nPozdrawiam"}
            ]
            try:
                with open(self.templates_file, "w", encoding="utf-8") as f:
                    json.dump(defaults, f, indent=2, ensure_ascii=False)
                return defaults
            except:
                return []
        try:
            with open(self.templates_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    
    def save_templates(self, templates):
        try:
            with open(self.templates_file, "w", encoding="utf-8") as f:
                json.dump(templates, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można zapisać: {e}")
    
    def refresh_templates_list(self):
        self.templates_list.clear()
        for template in self.load_templates():
            name = template.get("name", "Bez nazwy")
            category = template.get("category", "Ogólne")
            item = QListWidgetItem(f"📄 {name} ({category})")
            item.setData(Qt.ItemDataRole.UserRole, template)
            self.templates_list.addItem(item)
    
    def show_templates_context_menu(self, position):
        item = self.templates_list.itemAt(position)
        if not item:
            return
        template_data = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        action_use = QAction("📧 Użyj w mailu", self)
        action_use.triggered.connect(lambda: self.use_template_in_mail(template_data))
        menu.addAction(action_use)
        menu.addSeparator()
        action_edit = QAction("✏️ Edytuj", self)
        action_edit.triggered.connect(lambda: self.edit_template(item))
        menu.addAction(action_edit)
        action_delete = QAction("🗑️ Usuń", self)
        action_delete.triggered.connect(lambda: self.delete_template(item))
        menu.addAction(action_delete)
        menu.exec(self.templates_list.mapToGlobal(position))
    
    def use_template_in_mail(self, template_data):
        if self.template_selected_callback:
            self.template_selected_callback(template_data)
            self.accept()
        else:
            QMessageBox.information(self, "Info", f"Szablon '{template_data.get('name')}' - dostępne z okna nowej wiadomości")
    
    def add_template(self):
        dialog = TemplateEditDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            templates = self.load_templates()
            templates.append(dialog.get_template_data())
            self.save_templates(templates)
            self.refresh_templates_list()
    
    def edit_template(self, item):
        if isinstance(item, QListWidgetItem):
            template_data = item.data(Qt.ItemDataRole.UserRole)
            dialog = TemplateEditDialog(self, template_data)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                templates = self.load_templates()
                for i, t in enumerate(templates):
                    if t.get("name") == template_data.get("name"):
                        templates[i] = dialog.get_template_data()
                        break
                self.save_templates(templates)
                self.refresh_templates_list()
    
    def delete_template(self, item):
        if QMessageBox.question(self, "Potwierdzenie", "Usunąć szablon?") == QMessageBox.StandardButton.Yes:
            template_data = item.data(Qt.ItemDataRole.UserRole)
            templates = [t for t in self.load_templates() if t.get("name") != template_data.get("name")]
            self.save_templates(templates)
            self.refresh_templates_list()
    
    def load_ai_sources(self):
        if not self.ai_sources_file.exists():
            defaults = [
                {"name": "FAQ", "type": "faq", "priority": 10, "active": True, "content": "Q: Pytanie?\nA: Odpowiedź"}
            ]
            try:
                with open(self.ai_sources_file, "w", encoding="utf-8") as f:
                    json.dump(defaults, f, indent=2, ensure_ascii=False)
                return defaults
            except:
                return []
        try:
            with open(self.ai_sources_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return []
    
    def save_ai_sources(self, sources):
        try:
            with open(self.ai_sources_file, "w", encoding="utf-8") as f:
                json.dump(sources, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.warning(self, "Błąd", f"Nie można zapisać: {e}")
    
    def refresh_ai_sources_list(self):
        self.ai_sources_list.clear()
        for source in self.load_ai_sources():
            name = source.get("name", "Bez nazwy")
            priority = source.get("priority", 5)
            active = "✅" if source.get("active", True) else "❌"
            item = QListWidgetItem(f"{active} {name} (priorytet: {priority})")
            item.setData(Qt.ItemDataRole.UserRole, source)
            self.ai_sources_list.addItem(item)
    
    def show_ai_sources_context_menu(self, position):
        item = self.ai_sources_list.itemAt(position)
        if not item:
            return
        source_data = item.data(Qt.ItemDataRole.UserRole)
        menu = QMenu(self)
        action_view = QAction("👁️ Podgląd", self)
        action_view.triggered.connect(lambda: QMessageBox.information(self, source_data.get("name"), source_data.get("content", "")))
        menu.addAction(action_view)
        action_delete = QAction("🗑️ Usuń", self)
        action_delete.triggered.connect(lambda: self.delete_ai_source(item))
        menu.addAction(action_delete)
        menu.exec(self.ai_sources_list.mapToGlobal(position))
    
    def add_ai_source(self):
        name, ok = QInputDialog.getText(self, "Nowe źródło AI", "Nazwa:")
        if ok and name:
            sources = self.load_ai_sources()
            sources.append({"name": name, "type": "document", "priority": 5, "active": True, "content": ""})
            self.save_ai_sources(sources)
            self.refresh_ai_sources_list()
    
    def delete_ai_source(self, item):
        if QMessageBox.question(self, "Potwierdzenie", "Usunąć źródło?") == QMessageBox.StandardButton.Yes:
            source_data = item.data(Qt.ItemDataRole.UserRole)
            sources = [s for s in self.load_ai_sources() if s.get("name") != source_data.get("name")]
            self.save_ai_sources(sources)
            self.refresh_ai_sources_list()
    
    def load_data(self):
        self.refresh_favorites_list()
        self.refresh_templates_list()
        self.refresh_ai_sources_list()


class TemplateEditDialog(QDialog):
    def __init__(self, parent=None, template_data=None):
        super().__init__(parent)
        self.template_data = template_data or {}
        self.setWindowTitle("Edytuj szablon" if template_data else "Nowy szablon")
        self.resize(600, 400)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        form = QFormLayout()
        self.name_edit = QLineEdit()
        self.name_edit.setText(self.template_data.get("name", ""))
        form.addRow("Nazwa:", self.name_edit)
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.category_combo.addItems(["Biznesowe", "Osobiste", "Marketing", "Ogólne"])
        self.category_combo.setCurrentText(self.template_data.get("category", "Ogólne"))
        form.addRow("Kategoria:", self.category_combo)
        layout.addLayout(form)
        layout.addWidget(QLabel("Treść:"))
        self.content_edit = QTextEdit()
        self.content_edit.setPlainText(self.template_data.get("content", ""))
        layout.addWidget(self.content_edit)
        buttons = QHBoxLayout()
        btn_save = QPushButton("Zapisz")
        btn_save.clicked.connect(self.accept)
        btn_cancel = QPushButton("Anuluj")
        btn_cancel.clicked.connect(self.reject)
        buttons.addStretch()
        buttons.addWidget(btn_save)
        buttons.addWidget(btn_cancel)
        layout.addLayout(buttons)
    
    def get_template_data(self):
        return {
            "name": self.name_edit.text().strip(),
            "category": self.category_combo.currentText().strip(),
            "content": self.content_edit.toPlainText()
        }
