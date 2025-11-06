"""
Widok Habbit Tracker - śledzenie nawyków w formie tabeli miesięcznej
"""

import calendar
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QCalendarWidget,
    QGroupBox, QMessageBox, QAbstractItemView, QFrame, QComboBox, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont

# Import dialogów
try:
    from .habbit_dialogs import AddHabbitDialog, RemoveHabbitDialog
except ImportError:
    from habbit_dialogs import AddHabbitDialog, RemoveHabbitDialog


class HabbitTrackerView(QWidget):
    """Główny widok śledzenia nawyków"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.habits = []  # Lista nawyków
        self._updating_combo = False  # Flaga zapobiegająca niepotrzebnym odświeżeniom
        self.setup_ui()
        self.load_habits()
        self.refresh_table()
        self.update_navigation_buttons()
        
        # Załaduj zapisane szerokości kolumn
        self.load_column_widths()
        
        # Załaduj stan blokady kolumn
        self.load_lock_state()
        
    def setup_ui(self):
        """Tworzy interfejs użytkownika"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Tytuł
        title_label = QLabel("Habbit Tracker")
        title_label.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(title_label)
        
        # Pasek zarządzania
        self.create_toolbar(layout)
        
        # Tabela nawyków
        self.create_habits_table(layout)
        
    def create_toolbar(self, parent_layout):
        """Tworzy kompaktowy pasek narzędzi w jednym wierszu"""
        toolbar_frame = QFrame()
        toolbar_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        toolbar_layout = QHBoxLayout(toolbar_frame)
        toolbar_layout.setContentsMargins(10, 10, 10, 10)
        
        # Przycisk poprzedni miesiąc
        self.prev_month_btn = QPushButton("◀")
        self.prev_month_btn.setMinimumSize(40, 35)
        self.prev_month_btn.setMaximumSize(40, 35)
        self.prev_month_btn.clicked.connect(self.prev_month)
        self.prev_month_btn.setToolTip("Poprzedni miesiąc")
        toolbar_layout.addWidget(self.prev_month_btn)
        
        # Lista miesięcy (ComboBox)
        self.month_combo = QComboBox()
        self.month_combo.setMinimumHeight(35)
        self.month_combo.setMinimumWidth(200)
        
        # Wypełnij miesiące (tylko do aktualnego miesiąca)
        months = [
            "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
            "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"
        ]
        
        # Pobierz aktualną datę
        today = date.today()
        current_year = today.year
        current_month = today.month
        
        # Dodaj miesiące tylko do aktualnego miesiąca w aktualnym roku
        # lub wszystkie miesiące w poprzednich latach
        if self.current_year == current_year:
            # Aktualny rok - dodaj miesiące tylko do obecnego miesiąca
            for i in range(current_month):
                self.month_combo.addItem(f"{months[i]} {self.current_year}", i + 1)
        else:
            # Poprzedni rok - dodaj wszystkie miesiące
            for i, month in enumerate(months):
                self.month_combo.addItem(f"{month} {self.current_year}", i + 1)
        
        # Ustaw aktualny miesiąc (jeśli dostępny)
        if self.current_year == current_year and self.current_month <= current_month:
            self.month_combo.setCurrentIndex(self.current_month - 1)
        elif self.current_year < current_year:
            # Poprzedni rok - ustaw ostatni dostępny miesiąc
            self.month_combo.setCurrentIndex(self.month_combo.count() - 1)
        self.month_combo.currentIndexChanged.connect(self.on_month_combo_changed)
        toolbar_layout.addWidget(self.month_combo)
        
        # Przycisk następny miesiąc
        self.next_month_btn = QPushButton("▶")
        self.next_month_btn.setMinimumSize(40, 35)
        self.next_month_btn.setMaximumSize(40, 35)
        self.next_month_btn.clicked.connect(self.next_month)
        self.next_month_btn.setToolTip("Następny miesiąc")
        toolbar_layout.addWidget(self.next_month_btn)
        
        # Separator
        toolbar_layout.addSpacing(20)
        
        # Przyciski zarządzania
        # Przycisk dodaj nawyk
        self.add_habit_btn = QPushButton("📝 Dodaj")
        self.add_habit_btn.setMinimumHeight(35)
        self.add_habit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.add_habit_btn.clicked.connect(self.on_add_habit_clicked)
        self.add_habit_btn.setToolTip("Dodaj nowy nawyk")
        toolbar_layout.addWidget(self.add_habit_btn)
        
        # Przycisk usuń nawyk
        self.remove_habit_btn = QPushButton("�️ Usuń")
        self.remove_habit_btn.setMinimumHeight(35)
        self.remove_habit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.remove_habit_btn.clicked.connect(self.on_remove_habit_clicked)
        self.remove_habit_btn.setToolTip("Usuń nawyk")
        toolbar_layout.addWidget(self.remove_habit_btn)
        
        # Przycisk edytuj nawyk
        self.edit_habit_btn = QPushButton("✏️ Edytuj")
        self.edit_habit_btn.setMinimumHeight(35)
        self.edit_habit_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.edit_habit_btn.clicked.connect(self.on_edit_habit_clicked)
        self.edit_habit_btn.setToolTip("Edytuj nawyk")
        toolbar_layout.addWidget(self.edit_habit_btn)
        
        # Przycisk blokowania/odblokowywania kolumn
        self.lock_columns_btn = QPushButton("🔓 Odblokowane")
        self.lock_columns_btn.setMinimumHeight(35)
        self.lock_columns_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.lock_columns_btn.clicked.connect(self.toggle_column_lock)
        self.lock_columns_btn.setToolTip("Zablokuj/odblokuj regulację szerokości kolumn")
        self.columns_locked = False
        toolbar_layout.addWidget(self.lock_columns_btn)
        
        # Przycisk eksportu CSV
        self.export_csv_btn = QPushButton("📊 Eksportuj CSV")
        self.export_csv_btn.setMinimumHeight(35)
        self.export_csv_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        self.export_csv_btn.setToolTip("Eksportuj tabelę do pliku CSV")
        toolbar_layout.addWidget(self.export_csv_btn)
        
        # Przycisk odśwież
        self.refresh_btn = QPushButton("🔄 Odśwież")
        self.refresh_btn.setMinimumHeight(35)
        self.refresh_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.refresh_btn.clicked.connect(self.refresh_table)
        self.refresh_btn.setToolTip("Odśwież tabelę")
        toolbar_layout.addWidget(self.refresh_btn)
        
        parent_layout.addWidget(toolbar_frame)
        
    def create_habits_table(self, parent_layout):
        """Tworzy tabelę nawyków"""
        table_group = QGroupBox("Nawyki")
        table_layout = QVBoxLayout(table_group)
        
        self.habits_table = QTableWidget()
        self.habits_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.habits_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.habits_table.setAlternatingRowColors(True)
        
        # Stylizacja nagłówków
        self.habits_table.setStyleSheet("""
            QTableWidget::horizontalHeader {
                height: 50px;  /* Zwiększ wysokość o około 40% (z domyślnych ~35px) */
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                font-weight: bold;
                font-size: 12px;
            }
            QTableWidget::horizontalHeader::section {
                height: 50px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QTableWidget::horizontalHeader::section:hover {
                background-color: #e9ecef;
                border: 2px solid #007bff;
            }
        """)
        
        # Sygnały
        header = self.habits_table.horizontalHeader()
        if header:
            header.sectionClicked.connect(self.on_header_clicked)
        
        # Dodaj obsługę kliknięć w komórki
        self.habits_table.itemClicked.connect(self.on_cell_clicked)
        
        # Zmienne do przechowywania wybranej komórki
        self.selected_row = -1
        self.selected_column = -1
        
        table_layout.addWidget(self.habits_table)
        parent_layout.addWidget(table_group)
        
    def update_month_label(self):
        """Aktualizuje combobox z nazwą miesiąca"""
        month_names = [
            "Styczeń", "Luty", "Marzec", "Kwiecień", "Maj", "Czerwiec",
            "Lipiec", "Sierpień", "Wrzesień", "Październik", "Listopad", "Grudzień"
        ]
        
        # Aktualizuj combo box
        if hasattr(self, 'month_combo'):
            self._updating_combo = True  # Zapobiega niepotrzebnemu odświeżaniu
            self.month_combo.clear()
            
            # Pobierz aktualną datę
            today = date.today()
            current_year = today.year
            current_month = today.month
            
            # Dodaj miesiące tylko do aktualnego miesiąca w aktualnym roku
            # lub wszystkie miesiące w poprzednich latach
            if self.current_year == current_year:
                # Aktualny rok - dodaj miesiące tylko do obecnego miesiąca
                for i in range(current_month):
                    self.month_combo.addItem(f"{month_names[i]} {self.current_year}", i + 1)
            else:
                # Poprzedni rok - dodaj wszystkie miesiące
                for i, month in enumerate(month_names):
                    self.month_combo.addItem(f"{month} {self.current_year}", i + 1)
            
            # Ustaw aktualny miesiąc (jeśli dostępny)
            if self.current_year == current_year and self.current_month <= current_month:
                self.month_combo.setCurrentIndex(self.current_month - 1)
            elif self.current_year < current_year:
                # Poprzedni rok - ustaw ostatni dostępny miesiąc
                if self.month_combo.count() > 0:
                    self.month_combo.setCurrentIndex(self.month_combo.count() - 1)
            
            self._updating_combo = False
    
    def prev_month(self):
        """Przejdź do poprzedniego miesiąca"""
        if self.current_month == 1:
            self.current_month = 12
            self.current_year -= 1
        else:
            self.current_month -= 1
        self.update_month_label()
        self.refresh_table()
        self.update_navigation_buttons()
    
    def next_month(self):
        """Przejdź do następnego miesiąca (ale nie do przyszłości)"""
        # Sprawdź czy można przejść do następnego miesiąca
        today = date.today()
        next_month = self.current_month + 1 if self.current_month < 12 else 1
        next_year = self.current_year if self.current_month < 12 else self.current_year + 1
        
        # Nie pozwól na przejście do przyszłych miesięcy
        if next_year > today.year or (next_year == today.year and next_month > today.month):
            return  # Nie rób nic jeśli to byłby przyszły miesiąc
        
        if self.current_month == 12:
            self.current_month = 1
            self.current_year += 1
        else:
            self.current_month += 1
        self.update_month_label()
        self.refresh_table()
        self.update_navigation_buttons()
        self.update_navigation_buttons()
    
    def update_navigation_buttons(self):
        """Aktualizuje stan przycisków nawigacji"""
        today = date.today()
        
        # Sprawdź czy można przejść do następnego miesiąca
        next_month = self.current_month + 1 if self.current_month < 12 else 1
        next_year = self.current_year if self.current_month < 12 else self.current_year + 1
        
        can_go_next = not (next_year > today.year or (next_year == today.year and next_month > today.month))
        
        if hasattr(self, 'next_month_btn'):
            self.next_month_btn.setEnabled(can_go_next)
    
    def on_month_combo_changed(self, index):
        """Obsługuje zmianę miesiąca w combo box"""
        if hasattr(self, 'month_combo') and not hasattr(self, '_updating_combo'):
            month_data = self.month_combo.itemData(index)
            if month_data and month_data != self.current_month:
                self.current_month = month_data
                self.refresh_table()
                self.update_navigation_buttons()
    
    def on_edit_habit_clicked(self):
        """Obsługuje edycję wybranej komórki nawyku"""
        # Sprawdź czy wybrano komórkę
        if self.selected_row == -1 or self.selected_column == -1:
            QMessageBox.information(self, "Informacja", 
                                   "Aby edytować wartość nawyku, najpierw kliknij na komórkę w tabeli.")
            return
            
        # Sprawdź czy to kolumna nawyku
        if self.selected_column <= 1:
            QMessageBox.information(self, "Informacja", 
                                   "Nie można edytować kolumn daty i dnia tygodnia.")
            return
            
        habit_index = self.selected_column - 2
        if habit_index >= len(self.habits):
            QMessageBox.warning(self, "Błąd", "Nieprawidłowa kolumna nawyku.")
            return
            
        # Pobierz informacje o nawyku i dacie
        habit = self.habits[habit_index]
        selected_date = date(self.current_year, self.current_month, self.selected_row + 1)
        
        # Otwórz dialog edycji dla wybranej komórki
        self.open_cell_edit_dialog(habit, selected_date)
        
    def open_cell_edit_dialog(self, habit: Dict[str, Any], edit_date: date):
        """Otwiera uproszczony dialog edycji dla konkretnej komórki"""
        current_value = self.get_habit_value(habit['id'], edit_date)
        habit_name = habit['name']
        date_str = edit_date.strftime("%d.%m.%Y")
        
        # Importuj nowe dialogi
        try:
            from .habbit_dialogs import (
                SimpleCheckboxDialog, SimpleCounterDialog, SimpleDurationDialog,
                SimpleTimeDialog, SimpleScaleDialog, SimpleTextDialog
            )
        except ImportError as e:
            QMessageBox.warning(self, "Błąd", f"Nie można załadować dialogów: {e}")
            return
        
        # Wybierz odpowiedni dialog na podstawie typu
        dialog = None
        
        if habit['type'] == 'checkbox':
            dialog = SimpleCheckboxDialog(self, habit_name, date_str, current_value)
        elif habit['type'] == 'counter':
            dialog = SimpleCounterDialog(self, habit_name, date_str, current_value)
        elif habit['type'] == 'duration':
            dialog = SimpleDurationDialog(self, habit_name, date_str, current_value)
        elif habit['type'] == 'time':
            dialog = SimpleTimeDialog(self, habit_name, date_str, current_value)
        elif habit['type'] == 'scale':
            scale_max = habit.get('scale_max', 10)
            dialog = SimpleScaleDialog(self, habit_name, date_str, current_value, scale_max)
        elif habit['type'] == 'text':
            dialog = SimpleTextDialog(self, habit_name, date_str, current_value)
        
        if dialog and dialog.exec() == dialog.DialogCode.Accepted:
            # Zapisz nową wartość
            new_value = dialog.get_value()
            
            try:
                if self.db_manager:
                    self.db_manager.set_habit_record(habit['id'], edit_date, new_value)
                    self.refresh_table()
                    
                    # Wyczyść zaznaczenie
                    self.selected_row = -1
                    self.selected_column = -1
                    
                    print(f"DEBUG: Zapisano {habit_name}: {new_value} na {edit_date}")
                else:
                    QMessageBox.warning(self, "Błąd", "Brak połączenia z bazą danych.")
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie można zapisać wartości nawyku:\n{e}")
        
    def toggle_column_lock(self):
        """Przełącza blokadę/odblokowanie regulacji szerokości kolumn"""
        self.columns_locked = not self.columns_locked
        
        header = self.habits_table.horizontalHeader()
        if not header:
            return
        
        if self.columns_locked:
            # Zablokuj regulację szerokości kolumn
            header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            self.lock_columns_btn.setText("🔒 Zablokowane")
            self.lock_columns_btn.setToolTip("Kliknij aby odblokować regulację szerokości kolumn")
            
            # Zapisz aktualne szerokości kolumn jako domyślne
            self.save_column_widths()
            # Zapisz stan blokady
            self.save_lock_state(True)
            
        else:
            # Odblokuj regulację szerokości kolumn
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            self.lock_columns_btn.setText("🔓 Odblokowane")
            self.lock_columns_btn.setToolTip("Kliknij aby zablokować regulację szerokości kolumn")
            # Zapisz stan odblokowania
            self.save_lock_state(False)
    
    def save_column_widths(self):
        """Zapisuje aktualne szerokości kolumn jako domyślne"""
        if not hasattr(self, 'habits_table') or not self.habits_table:
            return
            
        column_widths = {}
        for i in range(self.habits_table.columnCount()):
            column_widths[i] = self.habits_table.columnWidth(i)
        
        # Zapisz do pliku JSON
        try:
            import json
            import os
            
            settings_dir = "data"
            if not os.path.exists(settings_dir):
                os.makedirs(settings_dir)
                
            settings_file = os.path.join(settings_dir, "habit_column_widths.json")
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(column_widths, f, indent=2)
            
            self.saved_column_widths = column_widths
            print(f"DEBUG: Zapisano szerokości kolumn do pliku: {column_widths}")
        except Exception as e:
            print(f"DEBUG: Błąd podczas zapisywania szerokości kolumn: {e}")
            # Fallback - zapisz w zmiennej
            self.saved_column_widths = column_widths
    
    def load_column_widths(self):
        """Ładuje zapisane szerokości kolumn"""
        try:
            import json
            import os
            
            settings_file = os.path.join("data", "habit_column_widths.json")
            
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    column_widths = json.load(f)
                
                # Konwertuj klucze z string na int (JSON używa string keys)
                column_widths = {int(k): v for k, v in column_widths.items()}
                
                for column, width in column_widths.items():
                    if column < self.habits_table.columnCount():
                        self.habits_table.setColumnWidth(column, width)
                
                self.saved_column_widths = column_widths
                print(f"DEBUG: Załadowano szerokości kolumn z pliku: {column_widths}")
                return True
            else:
                print("DEBUG: Brak zapisanych szerokości kolumn")
                return False
                
        except Exception as e:
            print(f"DEBUG: Błąd podczas ładowania szerokości kolumn: {e}")
            # Fallback - spróbuj załadować ze zmiennej instancji
            if hasattr(self, 'saved_column_widths') and self.saved_column_widths:
                for column, width in self.saved_column_widths.items():
                    if column < self.habits_table.columnCount():
                        self.habits_table.setColumnWidth(column, width)
                print(f"DEBUG: Załadowano szerokości kolumn z zmiennej: {self.saved_column_widths}")
                return True
            return False
    
    def save_lock_state(self, locked: bool):
        """Zapisuje stan blokady kolumn"""
        try:
            import json
            import os
            
            settings_dir = "data"
            if not os.path.exists(settings_dir):
                os.makedirs(settings_dir)
                
            settings_file = os.path.join(settings_dir, "habit_lock_state.json")
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump({"columns_locked": locked}, f, indent=2)
            
            print(f"DEBUG: Zapisano stan blokady kolumn: {locked}")
        except Exception as e:
            print(f"DEBUG: Błąd podczas zapisywania stanu blokady: {e}")
    
    def load_lock_state(self):
        """Ładuje stan blokady kolumn"""
        try:
            import json
            import os
            
            settings_file = os.path.join("data", "habit_lock_state.json")
            
            if os.path.exists(settings_file):
                with open(settings_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                locked = data.get("columns_locked", False)
                
                # Ustaw stan blokady
                self.columns_locked = locked
                
                header = self.habits_table.horizontalHeader()
                if header:
                    if locked:
                        header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
                        self.lock_columns_btn.setText("🔒 Zablokowane")
                        self.lock_columns_btn.setToolTip("Kliknij aby odblokować regulację szerokości kolumn")
                    else:
                        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                        self.lock_columns_btn.setText("🔓 Odblokowane")
                        self.lock_columns_btn.setToolTip("Kliknij aby zablokować regulację szerokości kolumn")
                
                print(f"DEBUG: Załadowano stan blokady kolumn: {locked}")
                return locked
            else:
                print("DEBUG: Brak zapisanego stanu blokady")
                return False
                
        except Exception as e:
            print(f"DEBUG: Błąd podczas ładowania stanu blokady: {e}")
            return False
    
    def unlock_columns_after_habit_change(self):
        """Automatycznie odblokowuje kolumny po dodaniu nowego nawyku"""
        if self.columns_locked:
            header = self.habits_table.horizontalHeader()
            if header:
                self.columns_locked = False
                header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                self.lock_columns_btn.setText("🔓 Odblokowane")
                self.lock_columns_btn.setToolTip("Kliknij aby zablokować regulację szerokości kolumn")
                print("DEBUG: Automatycznie odblokowano kolumny po zmianie nawyków")
        
    def on_month_changed(self, selected_date):
        """Obsługuje zmianę miesiąca w kalendarzu (już nieużywane)"""
        self.current_year = selected_date.year()
        self.current_month = selected_date.month()
        self.update_month_label()
        self.refresh_table()
        
    def load_habits(self):
        """Ładuje listę nawyków z bazy danych"""
        if not self.db_manager:
            return
            
        try:
            self.habits = self.db_manager.get_habit_columns()
            print(f"DEBUG: Załadowano {len(self.habits)} nawyków")
        except Exception as e:
            print(f"ERROR: Błąd ładowania nawyków: {e}")
            self.habits = []
            
    def style_habit_headers(self):
        """Stylizuje nagłówki nawyków (kolumny 2+) jako przyciski z ramką"""
        header = self.habits_table.horizontalHeader()
        if not header:
            return
            
        # Dodaj specjalną stylizację dla nagłówków nawyków
        habit_header_style = """
            QTableWidget::horizontalHeader::section {
                height: 50px;
                background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                padding: 4px 8px;
                font-weight: bold;
                font-size: 12px;
            }
            QTableWidget::horizontalHeader::section:hover {
                background-color: #e9ecef;
                border: 2px solid #007bff;
            }
        """
        
        # Dodaj specjalne style dla kolumn nawyków (od kolumny 2)
        for i in range(2, self.habits_table.columnCount()):
            habit_header_style += f"""
                QTableWidget::horizontalHeader::section:nth({i}) {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #f8f9fa, stop:1 #e9ecef);
                    border: 2px solid #007bff;
                    border-radius: 3px;
                    margin: 1px;
                    font-weight: bold;
                    color: #0056b3;
                }}
                QTableWidget::horizontalHeader::section:nth({i}):hover {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #e3f2fd, stop:1 #bbdefb);
                    border: 2px solid #0056b3;
                    color: #003c82;
                }}
                QTableWidget::horizontalHeader::section:nth({i}):pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                                stop:0 #bbdefb, stop:1 #90caf9);
                    border: 2px solid #003c82;
                }}
            """
            
        self.habits_table.setStyleSheet(habit_header_style)

    def refresh_table(self):
        """Odświeża tabelę nawyków"""
        print(f"DEBUG: refresh_table() wywołane dla {self.current_month}/{self.current_year}")
        
        if not self.habits:
            # Tabela pusta - pokaż informację
            self.habits_table.setRowCount(1)
            self.habits_table.setColumnCount(1)
            self.habits_table.setHorizontalHeaderLabels(["Informacja"])
            
            item = QTableWidgetItem("Brak nawyków. Dodaj pierwszy nawyk używając przycisku 'Dodaj nawyk'.")
            item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Tylko do odczytu
            self.habits_table.setItem(0, 0, item)
            
            # Rozciągnij kolumnę
            header = self.habits_table.horizontalHeader()
            if header:
                header.setStretchLastSection(True)
            return
            
        # Przygotuj tabelę
        days_in_month = calendar.monthrange(self.current_year, self.current_month)[1]
        
        print(f"DEBUG: Miesiąc {self.current_month}/{self.current_year} ma {days_in_month} dni")
        
        self.habits_table.setRowCount(days_in_month)
        self.habits_table.setColumnCount(len(self.habits) + 2)  # +2 dla kolumny z datami i dniami tygodnia
        
        # Nagłówki kolumn - pierwszy to data, drugi to dzień tygodnia, potem nawyki
        headers = ["Data", "Dzień"]
        for habit in self.habits:
            habit_header = f"{habit['name']}\n({habit['type']})"
            headers.append(habit_header)
            
        self.habits_table.setHorizontalHeaderLabels(headers)
        
        # Stylizuj nagłówki nawyków (kolumny 2+) jako przyciski
        self.style_habit_headers()
        
        # Mapowanie dni tygodnia na skróty
        weekday_names = ['PN', 'WT', 'ŚR', 'CZ', 'PT', 'SO', 'ND']
        
        # Wypełnij wiersze dniami miesiąca
        for day in range(1, days_in_month + 1):
            current_date = date(self.current_year, self.current_month, day)
            weekday = current_date.weekday()  # 0=poniedziałek, 6=niedziela
            
            # Kolumna daty
            date_item = QTableWidgetItem(f"{day:02d}")
            date_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            date_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Tylko do odczytu
            
            # Kolumna dnia tygodnia
            weekday_item = QTableWidgetItem(weekday_names[weekday])
            weekday_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            weekday_item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Tylko do odczytu
            
            # Kolorowanie weekendów dla obu kolumn
            if weekday == 5:  # Sobota
                date_item.setBackground(QBrush(QColor(200, 255, 200)))  # Jasny zielony
                date_item.setForeground(QBrush(QColor(0, 0, 0)))  # Czarna czcionka
                weekday_item.setBackground(QBrush(QColor(200, 255, 200)))
                weekday_item.setForeground(QBrush(QColor(0, 0, 0)))  # Czarna czcionka
            elif weekday == 6:  # Niedziela
                date_item.setBackground(QBrush(QColor(255, 200, 150)))  # Jasny pomarańczowy
                date_item.setForeground(QBrush(QColor(0, 0, 0)))  # Czarna czcionka
                weekday_item.setBackground(QBrush(QColor(255, 200, 150)))
                weekday_item.setForeground(QBrush(QColor(0, 0, 0)))  # Czarna czcionka
                
            self.habits_table.setItem(day - 1, 0, date_item)
            self.habits_table.setItem(day - 1, 1, weekday_item)
            
            # Kolumny nawyków
            for col, habit in enumerate(self.habits, 2):
                value = self.get_habit_value(habit['id'], current_date)
                
                # Specjalne traktowanie dla checkbox
                if habit['type'] == 'checkbox':
                    checkbox = QCheckBox()
                    checkbox.setChecked(value == "1")
                    checkbox.setEnabled(False)  # Tylko do odczytu
                    checkbox.setStyleSheet("""
                        QCheckBox::indicator {
                            width: 20px;
                            height: 20px;
                            border: 2px solid #3498db;
                            border-radius: 4px;
                            background-color: white;
                        }
                        QCheckBox::indicator:checked {
                            background-color: #27ae60;
                            border-color: #27ae60;
                        }
                        QCheckBox::indicator:checked:hover {
                            background-color: #229954;
                        }
                        QCheckBox {
                            spacing: 0px;
                        }
                    """)
                    
                    # Kolorowanie weekendów dla checkboxa
                    if weekday == 5:  # Sobota
                        checkbox.setStyleSheet(checkbox.styleSheet() + """
                            QCheckBox {
                                background-color: rgb(200, 255, 200);
                            }
                        """)
                    elif weekday == 6:  # Niedziela
                        checkbox.setStyleSheet(checkbox.styleSheet() + """
                            QCheckBox {
                                background-color: rgb(255, 200, 150);
                            }
                        """)
                    
                    self.habits_table.setCellWidget(day - 1, col, checkbox)
                else:
                    # Dla innych typów nawyków używamy standardowego QTableWidgetItem
                    display_value = self.format_habit_value(value, habit)
                    
                    item = QTableWidgetItem(display_value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Tylko do odczytu
                    
                    # Kolorowanie weekendów dla kolumn nawyków
                    if weekday == 5:  # Sobota
                        item.setBackground(QBrush(QColor(200, 255, 200)))
                        item.setForeground(QBrush(QColor(0, 0, 0)))  # Czarna czcionka
                    elif weekday == 6:  # Niedziela
                        item.setBackground(QBrush(QColor(255, 200, 150)))
                        item.setForeground(QBrush(QColor(0, 0, 0)))  # Czarna czcionka
                        
                    self.habits_table.setItem(day - 1, col, item)
                
        # Dostosuj szerokości kolumn
        self.habits_table.resizeColumnsToContents()
        header = self.habits_table.horizontalHeader()
        if header:
            header.setStretchLastSection(True)
        
        print(f"DEBUG: Tabela odświeżona - {days_in_month} dni, {len(self.habits)} nawyków")
        
        # Przywróć szerokości kolumn jeśli są zablokowane
        if hasattr(self, 'columns_locked') and self.columns_locked:
            self.load_column_widths()
            
        # Ponownie podłącz sygnał kliknięcia nagłówka (może zostać zresetowany podczas refresh)
        header = self.habits_table.horizontalHeader()
        if header:
            try:
                # Najpierw odłącz żeby uniknąć wielokrotnych połączeń
                header.sectionClicked.disconnect()
            except:
                pass  # Ignoruj błąd jeśli nie było połączenia
            # Podłącz ponownie
            header.sectionClicked.connect(self.on_header_clicked)
            print(f"DEBUG: Ponownie podłączono sygnał kliknięcia nagłówka")
        
    def get_habit_value(self, habit_id: int, date_obj: date) -> str:
        """Pobiera wartość nawyku dla danej daty"""
        if not self.db_manager:
            return ""
            
        try:
            date_str = date_obj.strftime("%Y-%m-%d")
            return self.db_manager.get_habit_record(habit_id, date_str) or ""
        except Exception as e:
            print(f"ERROR: Błąd pobierania wartości nawyku {habit_id} dla {date_obj}: {e}")
            return ""
            
    def format_minutes_display(self, minutes):
        """Formatuje minuty do wyświetlenia w postaci 'XhYmin' lub 'Ymin'"""
        try:
            total_minutes = int(minutes)
            if total_minutes == 0:
                return ""
            elif total_minutes < 60:
                return f"{total_minutes}min"
            else:
                hours = total_minutes // 60
                remaining_minutes = total_minutes % 60
                if remaining_minutes == 0:
                    return f"{hours}h"
                else:
                    return f"{hours}h{remaining_minutes}min"
        except (ValueError, TypeError):
            return ""

    def format_habit_value(self, value: str, habit: dict) -> str:
        """Formatuje wartość nawyku do wyświetlenia"""
        if not value:
            return ""
            
        habit_type = habit['type']
        
        if habit_type == "odznacz":
            return "✓" if value == "1" else ""
        elif habit_type == "Ile razy":
            return value if value != "0" else ""
        elif habit_type == "czas trwania" or habit_type == "duration":
            # Dla duration formatuj minuty jako XhYmin lub Ymin
            return self.format_minutes_display(value)
        elif habit_type == "scale" or habit_type == "Skala":
            # Dla skali pokazuj n/max
            if value and value != "0":
                scale_max = habit.get('scale_max', 10)
                return f"{value}/{scale_max}"
            return ""
        elif habit_type in ["Godzina", "tekst"]:
            return value
        else:
            return value
            
    def on_cell_clicked(self, item):
        """Obsługuje kliknięcie w komórkę tabeli"""
        if not item:
            return
            
        row = item.row()
        column = item.column()
        
        # Ignoruj kliknięcia w kolumny daty i dnia tygodnia
        if column <= 1:
            return
            
        # Sprawdź czy to kolumna nawyku
        habit_index = column - 2
        if habit_index >= len(self.habits):
            return
            
        # Zapisz wybraną komórkę
        self.selected_row = row
        self.selected_column = column
        
        print(f"DEBUG: Wybrano komórkę - wiersz: {row}, kolumna: {column}, nawyk: {habit_index}")
        
    def on_header_clicked(self, logical_index: int):
        """Obsługuje kliknięcie nagłówka kolumny nawyku - wprowadza dane dla dzisiejszego dnia"""
        print(f"DEBUG: Kliknięto nagłówek kolumny {logical_index}")
        
        if logical_index <= 1:  # Kolumny daty i dnia tygodnia - ignoruj
            print(f"DEBUG: Ignorowanie kolumny {logical_index} (data/dzień)")
            return
            
        habit_index = logical_index - 2  # Teraz mamy 2 kolumny przed kolumnami nawyków
        if habit_index >= len(self.habits):
            print(f"DEBUG: Nieprawidłowy indeks nawyku {habit_index}, mamy {len(self.habits)} nawyków")
            return
            
        habit = self.habits[habit_index]
        print(f"DEBUG: Otwieranie dialogu dla nawyku {habit['name']} - dzisiejszy dzień")
        
        # Użyj dzisiejszego dnia w aktualnie wyświetlanym miesiącu
        today = date.today()
        
        # Sprawdź czy dzisiejszy dzień jest w aktualnie wyświetlanym miesiącu
        if today.year == self.current_year and today.month == self.current_month:
            selected_date = today
        else:
            # Jeśli przeglądamy inny miesiąc, użyj pierwszego dnia tego miesiąca
            selected_date = date(self.current_year, self.current_month, 1)
        
        # Bezpośrednio otwórz dialog edycji dla wybranej daty
        self.open_cell_edit_dialog(habit, selected_date)
        
    def on_add_habit_clicked(self):
        """Obsługuje dodawanie nowego nawyku"""
        dialog = AddHabbitDialog(self)
        
        if dialog.exec() == dialog.DialogCode.Accepted:
            habit_data = dialog.get_habit_data()
            
            try:
                if not self.db_manager:
                    QMessageBox.warning(self, "Błąd", "Brak połączenia z bazą danych.")
                    return
                
                # Mapowanie nazw typów z polskiego na angielski dla bazy
                type_mapping = {
                    "odznacz": "checkbox",
                    "Ile razy": "counter", 
                    "czas trwania": "duration",
                    "Godzina": "time",
                    "Skala": "scale",
                    "tekst": "text"
                }
                
                db_type = type_mapping.get(habit_data['type'], habit_data['type'])
                
                habit_id = self.db_manager.add_habit_column(
                    habit_data['name'],
                    db_type,
                    habit_data.get('scale_max')
                )
                
                print(f"DEBUG: Dodano nawyk {habit_data['name']} (ID: {habit_id})")
                
                # Odśwież listę i tabelę
                self.load_habits()
                self.refresh_table()
                
                # Automatycznie odblokuj kolumny po dodaniu nawyku
                self.unlock_columns_after_habit_change()
                
                QMessageBox.information(self, "Sukces", f"Dodano nawyk: {habit_data['name']}")
                
            except Exception as e:
                QMessageBox.warning(self, "Błąd", f"Nie można dodać nawyku:\n{e}")
                
    def on_remove_habit_clicked(self):
        """Obsługuje usuwanie nawyku"""
        if not self.habits:
            QMessageBox.information(self, "Informacja", "Brak nawyków do usunięcia.")
            return
            
        # Przygotuj listę nawyków z polskimi nazwami typów
        display_habits = []
        for habit in self.habits:
            # Mapowanie typów z angielskiego na polski
            type_mapping = {
                "checkbox": "odznacz",
                "counter": "Ile razy",
                "duration": "czas trwania", 
                "time": "Godzina",
                "scale": "Skala",
                "text": "tekst"
            }
            
            display_type = type_mapping.get(habit['type'], habit['type'])
            display_habits.append({
                'id': habit['id'],
                'name': habit['name'],
                'type': display_type
            })
            
        dialog = RemoveHabbitDialog(self, display_habits)
        
        if dialog.exec() == dialog.DialogCode.Accepted:
            habit_id = dialog.get_selected_habit_id()
            if habit_id:
                try:
                    if not self.db_manager:
                        QMessageBox.warning(self, "Błąd", "Brak połączenia z bazą danych.")
                        return
                    
                    # Znajdź nazwę nawyku dla komunikatu
                    habit_name = next((h['name'] for h in self.habits if h['id'] == habit_id), "Nieznany")
                    
                    success = self.db_manager.remove_habit_column(habit_id)
                    if success:
                        print(f"DEBUG: Usunięto nawyk {habit_name} (ID: {habit_id})")
                        
                        # Odśwież listę i tabelę
                        self.load_habits()
                        self.refresh_table()
                        
                        QMessageBox.information(self, "Sukces", f"Usunięto nawyk: {habit_name}")
                    else:
                        QMessageBox.warning(self, "Błąd", "Nie można usunąć nawyku.")
                        
                except Exception as e:
                    QMessageBox.warning(self, "Błąd", f"Nie można usunąć nawyku:\n{e}")
    
    def export_to_csv(self):
        """Eksportuje tabelę nawyków do pliku CSV"""
        try:
            from PyQt6.QtWidgets import QFileDialog
            import csv
            import os
            from datetime import date
            
            # Dialog wyboru pliku
            default_filename = f"habit_tracker_{self.current_year}_{self.current_month:02d}.csv"
            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Eksportuj do CSV",
                default_filename,
                "Pliki CSV (*.csv);;Wszystkie pliki (*)"
            )
            
            if not file_path:
                return  # Użytkownik anulował
            
            # Przygotuj dane do eksportu
            days_in_month = calendar.monthrange(self.current_year, self.current_month)[1]
            weekday_names = ['PN', 'WT', 'ŚR', 'CZ', 'PT', 'SO', 'ND']
            
            # Nagłówki CSV
            headers = ["Data", "Dzień"]
            for habit in self.habits:
                headers.append(f"{habit['name']} ({habit['type']})")
            
            # Zbierz dane
            export_data = []
            
            for day in range(1, days_in_month + 1):
                current_date = date(self.current_year, self.current_month, day)
                weekday = current_date.weekday()
                
                # Sprawdź czy ten dzień ma jakiekolwiek dane w kolumnach nawyków
                has_data = False
                habit_values = []
                
                for habit in self.habits:
                    value = self.get_habit_value(habit['id'], current_date)
                    display_value = self.format_habit_value(value, habit)
                    habit_values.append(display_value)
                    
                    # Sprawdź czy ma jakąkolwiek wartość
                    if display_value and display_value.strip():
                        has_data = True
                
                # Dodaj wiersz tylko jeśli ma dane w kolumnach nawyków
                if has_data:
                    row = [
                        f"{day:02d}.{self.current_month:02d}.{self.current_year}",  # Data
                        weekday_names[weekday]  # Dzień tygodnia
                    ]
                    row.extend(habit_values)  # Wartości nawyków
                    export_data.append(row)
            
            # Zapisz do pliku CSV
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                writer = csv.writer(csvfile, delimiter=';')  # Używamy ; jako separator dla lepszej kompatybilności z Excel
                
                # Zapisz nagłówki
                writer.writerow(headers)
                
                # Zapisz dane
                for row in export_data:
                    writer.writerow(row)
            
            # Komunikat o sukcesie
            exported_days = len(export_data)
            QMessageBox.information(
                self, 
                "Eksport zakończony", 
                f"Pomyślnie wyeksportowano {exported_days} dni z danymi do pliku:\n{file_path}"
            )
            
            print(f"DEBUG: Wyeksportowano {exported_days} dni do {file_path}")
            
        except Exception as e:
            QMessageBox.warning(self, "Błąd eksportu", f"Nie można wyeksportować danych:\n{e}")
            print(f"DEBUG: Błąd eksportu CSV: {e}")


if __name__ == "__main__":
    # Test widoku
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    view = HabbitTrackerView()
    view.show()
    sys.exit(app.exec())
