"""
Moduł WebBrowser - Przeglądarka stron internetowych z zapisanymi zakładkami
"""

import sys
import json
import os
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QComboBox, QDialog, QLabel, QLineEdit, QMessageBox,
    QDialogButtonBox, QListWidget, QListWidgetItem, QColorDialog, QStyledItemDelegate
)
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEngineProfile
from PyQt6.QtCore import QUrl, Qt
from PyQt6.QtGui import QColor, QPalette


class ColoredComboBoxDelegate(QStyledItemDelegate):
    """Delegate dla ComboBox z kolorowymi elementami"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.colors = {}
    
    def set_item_color(self, index, color):
        """Ustawia kolor dla danego indeksu"""
        self.colors[index] = color
    
    def paint(self, painter, option, index):
        """Rysuje element z kolorowym tłem"""
        if index.row() in self.colors:
            color = self.colors[index.row()]
            painter.fillRect(option.rect, color)
            
            # Dobór koloru tekstu
            brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
            text_color = QColor(255, 255, 255) if brightness < 128 else QColor(0, 0, 0)
            
            # Rysowanie tekstu
            painter.setPen(text_color)
            text = index.data(Qt.ItemDataRole.DisplayRole)
            painter.drawText(option.rect, Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, f"  {text}")
        else:
            super().paint(painter, option, index)


class AddPageDialog(QDialog):
    """Dialog do dodawania nowej strony internetowej"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Dodaj stronę")
        self.setModal(True)
        self.resize(400, 200)
        
        self.selected_color = QColor(255, 255, 255)  # Domyślny biały
        
        layout = QVBoxLayout()
        
        # Nazwa strony
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nazwa:"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Np. Google, YouTube...")
        name_layout.addWidget(self.name_input)
        layout.addLayout(name_layout)
        
        # Adres URL
        url_layout = QHBoxLayout()
        url_layout.addWidget(QLabel("Adres URL:"))
        self.url_input = QLineEdit()
        self.url_input.setPlaceholderText("https://www.example.com")
        url_layout.addWidget(self.url_input)
        layout.addLayout(url_layout)
        
        # Wybór koloru
        color_layout = QHBoxLayout()
        color_layout.addWidget(QLabel("Kolor:"))
        self.color_button = QPushButton("Wybierz kolor")
        self.color_button.clicked.connect(self.choose_color)
        self.color_preview = QLabel()
        self.color_preview.setFixedSize(50, 25)
        self.update_color_preview()
        color_layout.addWidget(self.color_button)
        color_layout.addWidget(self.color_preview)
        color_layout.addStretch()
        layout.addLayout(color_layout)
        
        # Przyciski OK/Cancel
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def choose_color(self):
        """Otwiera dialog wyboru koloru"""
        color = QColorDialog.getColor(self.selected_color, self, "Wybierz kolor dla strony")
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
        return {
            'name': self.name_input.text().strip(),
            'url': self.url_input.text().strip(),
            'color': self.selected_color.name()
        }


class DeletePageDialog(QDialog):
    """Dialog do usuwania zapisanych stron"""
    
    def __init__(self, pages, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Usuń stronę")
        self.setModal(True)
        self.resize(400, 300)
        
        self.pages = pages
        self.selected_page = None
        
        layout = QVBoxLayout()
        
        layout.addWidget(QLabel("Wybierz stronę do usunięcia:"))
        
        # Lista stron
        self.page_list = QListWidget()
        for page in pages:
            item = QListWidgetItem(page['name'])
            item.setData(Qt.ItemDataRole.UserRole, page)
            # Ustawienie koloru tła
            color = QColor(page['color'])
            item.setBackground(color)
            # Dobór koloru tekstu (jasny/ciemny) w zależności od tła
            if self.is_dark_color(color):
                item.setForeground(QColor(255, 255, 255))
            else:
                item.setForeground(QColor(0, 0, 0))
            self.page_list.addItem(item)
        
        layout.addWidget(self.page_list)
        
        # Przyciski
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
    
    def is_dark_color(self, color):
        """Sprawdza czy kolor jest ciemny (do doboru koloru tekstu)"""
        # Wzór na jasność koloru
        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        return brightness < 128
    
    def accept(self):
        """Zapisuje wybraną stronę przed zamknięciem"""
        current_item = self.page_list.currentItem()
        if current_item:
            self.selected_page = current_item.data(Qt.ItemDataRole.UserRole)
            super().accept()
        else:
            QMessageBox.warning(self, "Błąd", "Proszę wybrać stronę do usunięcia.")


class WebBrowserModule(QMainWindow):
    """Główne okno modułu przeglądarki stron internetowych"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Moduł WebBrowser")
        self.resize(1200, 800)
        
        # Wczytanie zapisanych stron
        self.pages = []
        self.load_pages()
        
        self.init_ui()
    
    def init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Pasek operacyjny u góry
        toolbar_layout = QHBoxLayout()
        
        # Przycisk Wstecz (po lewej)
        btn_back = QPushButton("Wstecz")
        btn_back.clicked.connect(self.go_back)
        toolbar_layout.addWidget(btn_back)
        
        # Lista zapisanych stron (ComboBox)
        self.page_combo = QComboBox()
        self.page_combo.setMinimumWidth(200)
        self.page_combo.currentIndexChanged.connect(self.on_page_selected)
        
        # Ustawienie delegata dla kolorowych elementów
        self.combo_delegate = ColoredComboBoxDelegate(self.page_combo)
        self.page_combo.setItemDelegate(self.combo_delegate)
        
        self.update_page_combo()
        toolbar_layout.addWidget(QLabel("Strona:"))
        toolbar_layout.addWidget(self.page_combo)
        
        # Przycisk Odśwież
        btn_refresh = QPushButton("Odśwież")
        btn_refresh.clicked.connect(self.refresh_page)
        toolbar_layout.addWidget(btn_refresh)
        
        # Separator - reszta przycisków po prawej
        toolbar_layout.addStretch()
        
        # Przycisk Dodaj stronę (po prawej)
        btn_add = QPushButton("Dodaj stronę")
        btn_add.clicked.connect(self.add_page)
        toolbar_layout.addWidget(btn_add)
        
        # Przycisk Usuń stronę (po prawej)
        btn_delete = QPushButton("Usuń stronę")
        btn_delete.clicked.connect(self.delete_page)
        toolbar_layout.addWidget(btn_delete)
        
        main_layout.addLayout(toolbar_layout)
        
        # Sekcja główna - widok strony internetowej z trwałym profilem
        # Konfiguracja domyślnego profilu do zapisywania danych
        profile_path = os.path.join(os.path.dirname(__file__), "browser_profile")
        os.makedirs(profile_path, exist_ok=True)
        
        self.profile = QWebEngineProfile.defaultProfile()
        self.profile.setPersistentStoragePath(profile_path)
        self.profile.setCachePath(os.path.join(profile_path, "cache"))
        self.profile.setPersistentCookiesPolicy(QWebEngineProfile.PersistentCookiesPolicy.ForcePersistentCookies)
        
        self.web_view = QWebEngineView()
        self.web_view.setUrl(QUrl("about:blank"))
        main_layout.addWidget(self.web_view)
    
    def update_page_combo(self):
        """Aktualizuje listę rozwijaną z zapisanymi stronami"""
        self.page_combo.blockSignals(True)
        self.page_combo.clear()
        
        # Czyszczenie kolorów w delegacie
        self.combo_delegate.colors.clear()
        
        for i, page in enumerate(self.pages):
            self.page_combo.addItem(page['name'], page)
            color = QColor(page['color'])
            
            # Ustawienie koloru w delegacie
            self.combo_delegate.set_item_color(i, color)
        
        self.page_combo.blockSignals(False)
    
    def is_dark_color(self, color):
        """Sprawdza czy kolor jest ciemny"""
        brightness = (color.red() * 299 + color.green() * 587 + color.blue() * 114) / 1000
        return brightness < 128
    
    def on_page_selected(self, index):
        """Obsługa wyboru strony z listy"""
        if index >= 0:
            page = self.page_combo.itemData(index)
            if page:
                url = page['url']
                # Sprawdzenie czy URL ma protokół
                if not url.startswith(('http://', 'https://')):
                    url = 'https://' + url
                self.web_view.setUrl(QUrl(url))
    
    def add_page(self):
        """Dodaje nową stronę"""
        dialog = AddPageDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            data = dialog.get_data()
            
            # Walidacja
            if not data['name']:
                QMessageBox.warning(self, "Błąd", "Proszę podać nazwę strony.")
                return
            
            if not data['url']:
                QMessageBox.warning(self, "Błąd", "Proszę podać adres URL.")
                return
            
            # Dodanie strony
            self.pages.append(data)
            self.save_pages()
            self.update_page_combo()
            
            # Automatyczne przejście do nowo dodanej strony
            self.page_combo.setCurrentIndex(len(self.pages) - 1)
    
    def delete_page(self):
        """Usuwa wybraną stronę"""
        if not self.pages:
            QMessageBox.information(self, "Informacja", "Brak zapisanych stron do usunięcia.")
            return
        
        dialog = DeletePageDialog(self.pages, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            if dialog.selected_page:
                self.pages.remove(dialog.selected_page)
                self.save_pages()
                self.update_page_combo()
                
                # Wczytanie pierwszej strony lub pustej
                if self.pages:
                    self.page_combo.setCurrentIndex(0)
                else:
                    self.web_view.setUrl(QUrl("about:blank"))
    
    def refresh_page(self):
        """Odświeża aktualną stronę"""
        self.web_view.reload()
    
    def go_back(self):
        """Wraca do poprzedniej strony w historii"""
        if self.web_view.history().canGoBack():
            self.web_view.back()
    
    def load_pages(self):
        """Wczytuje zapisane strony z pliku JSON"""
        try:
            with open('web_pages.json', 'r', encoding='utf-8') as f:
                self.pages = json.load(f)
        except FileNotFoundError:
            self.pages = []
        except json.JSONDecodeError:
            self.pages = []
            QMessageBox.warning(self, "Błąd", "Uszkodzony plik danych. Rozpoczynam z pustą listą stron.")
    
    def save_pages(self):
        """Zapisuje strony do pliku JSON"""
        try:
            with open('web_pages.json', 'w', encoding='utf-8') as f:
                json.dump(self.pages, f, indent=2, ensure_ascii=False)
        except Exception as e:
            QMessageBox.critical(self, "Błąd", f"Nie udało się zapisać danych: {str(e)}")


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("WebBrowser Module")
    app.setOrganizationName("Commercial App")
    
    window = WebBrowserModule()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
