"""
Widok Habit Tracker - śledzenie nawyków w formie tabeli miesięcznej

Zintegrowany z:
- i18n (internationalization)
- Theme Manager (zarządzanie motywami)
- Local Database (offline-first)
"""

import calendar
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional, Any
from loguru import logger

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QCalendarWidget,
    QGroupBox, QMessageBox, QAbstractItemView, QFrame, QComboBox, QCheckBox, QSizePolicy
)
from PyQt6.QtCore import Qt, QDate, pyqtSignal
from PyQt6.QtGui import QColor, QBrush, QFont

# Import i18n
from ...utils.i18n_manager import t
# Import theme manager
from ...utils.theme_manager import get_theme_manager

# Import dialogów
try:
    from .habit_dialogs import (
        AddHabbitDialog, RemoveHabbitDialog,
        SimpleCheckboxDialog, SimpleCounterDialog, SimpleDurationDialog,
        SimpleTimeDialog, SimpleScaleDialog, SimpleTextDialog
    )
except ImportError:
    from .habit_dialogs import (
        AddHabbitDialog, RemoveHabbitDialog,
        SimpleCheckboxDialog, SimpleCounterDialog, SimpleDurationDialog,
        SimpleTimeDialog, SimpleScaleDialog, SimpleTextDialog
    )

# Import synchronizacji
try:
    from .habit_sync_manager import HabitSyncManager
    from .habit_api_client import HabitAPIClient
    SYNC_AVAILABLE = True
except ImportError as e:
    logger.warning(f"[HABIT] Sync not available: {e}")
    SYNC_AVAILABLE = False


class HabbitTrackerView(QWidget):
    """Główny widok śledzenia nawyków"""
    
    def __init__(self, db_manager=None, parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.current_year = datetime.now().year
        self.current_month = datetime.now().month
        self.habits = []  # Lista nawyków
        self._updating_combo = False  # Flaga zapobiegająca niepotrzebnym odświeżeniom
        
        # Inicjalizacja synchronizacji
        self.sync_manager = None
        self.user_id = None  # Przechowuj user_id
        if SYNC_AVAILABLE and self.db_manager:
            try:
                # Import konfiguracji
                from ...config import HABIT_API_BASE_URL
                
                # Tworzy API client i sync manager
                api_client = HabitAPIClient(base_url=HABIT_API_BASE_URL)
                self.sync_manager = HabitSyncManager(
                    api_client=api_client,
                    habit_db=self.db_manager,
                    sync_interval=30,  # synchronizacja co 30 sekund
                    max_retries=3
                )
                # NIE uruchamiaj jeszcze - wymaga user_id (zostanie uruchomiony w set_user_data)
                logger.info("[HABIT] 🔄 Sync manager utworzony - oczekuje na user_id")
            except Exception as e:
                logger.error(f"[HABIT] ❌ Błąd inicjalizacji synchronizacji: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.sync_manager = None
        
        # Inicjalizacja theme managera
        self.theme_manager = get_theme_manager()
        logger.info("[HABIT] Theme manager initialized")
        
        # Pobierz kolory motywu
        self.colors = self.theme_manager.get_current_colors()
        
        self.setup_ui()
        self.load_habits()
        self.refresh_table()
        self.update_navigation_buttons()
        
        # Załaduj zapisane szerokości kolumn
        self.load_column_widths()
        
        # Załaduj stan blokady kolumn
        self.load_lock_state()
        
        # Aplikuj motyw
        self.apply_theme()
    
    def set_user_data(self, user_data: dict, **kwargs):
        """
        Ustaw dane użytkownika i uruchom synchronizację
        
        Args:
            user_data: Słownik z danymi użytkownika zawierający 'id'
        """
        try:
            logger.info(f"[HABIT] 🔧 set_user_data called with: {list(user_data.keys())}")
            self.user_id = user_data.get('id')
            logger.info(f"[HABIT] 🔐 User ID ustawiony: {self.user_id}")
            
            # Uruchom sync manager z user_id
            if self.sync_manager and self.user_id:
                logger.info(f"[HABIT] 🎯 Próba uruchomienia sync_manager...")
                self.sync_manager.set_user_id(self.user_id)
                logger.info(f"[HABIT] ✅ user_id ustawiony w sync_manager")
                
                # Wykonaj początkową synchronizację z serwerem (pobierz kolumny i rekordy)
                logger.info("[HABIT] 📥 Wykonywanie initial sync z serwera...")
                if self.sync_manager.initial_sync():
                    logger.success("[HABIT] ✅ Initial sync completed successfully")
                    # Odśwież UI po pobraniu danych z serwera
                    self.load_habits()
                    self.refresh_table()
                else:
                    logger.warning("[HABIT] ⚠️ Initial sync failed or returned no data")
                
                # Uruchom background worker
                self.sync_manager.start()
                logger.info(f"[HABIT] 🚀 Synchronizacja uruchomiona dla user {self.user_id}")
            else:
                if not self.sync_manager:
                    logger.error("[HABIT] ❌ Sync manager nie został utworzony!")
                if not self.user_id:
                    logger.error(f"[HABIT] ❌ Brak user_id w user_data! Keys: {list(user_data.keys())}")
                    
        except Exception as e:
            logger.error(f"[HABIT] ❌ Błąd w set_user_data: {e}")
            import traceback
            logger.error(traceback.format_exc())
        
    def setup_ui(self):
        """Tworzy interfejs użytkownika"""
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        
        # Pasek zarządzania (bez nagłówka)
        self.create_toolbar(layout)
        
        # Tabela nawyków
        self.create_habits_table(layout)
        
    def create_toolbar(self, parent_layout):
        """Tworzy pasek narzędzi z przyciskami w jednym poziomym wierszu"""
        
        # Tworzymy ramkę (kontener) dla całego paska narzędzi z wizualną obwódką
        toolbar_frame = QFrame()
        # Ustawiamy styl obwódki - StyledPanel daje ramkę 3D zgodną z motywem
        toolbar_frame.setFrameStyle(QFrame.Shape.StyledPanel)
        
        # Tworzymy układ poziomy (QHBoxLayout) - wszystkie widgety będą w jednym wierszu od lewej do prawej
        toolbar_main_layout = QHBoxLayout(toolbar_frame)
        # Ustawiamy marginesy wewnętrzne (góra, lewo, dół, prawo) = 10px ze wszystkich stron
        toolbar_main_layout.setContentsMargins(10, 10, 10, 10)
        # Ustawiamy odstęp między widgetami na 10px
        toolbar_main_layout.setSpacing(10)
        
        # ========== PRZYCISK BLOKADY KOLUMN ==========
        # Tworzymy przycisk z ikoną kłódki (🔓 = odblokowane)
        self.lock_columns_btn = QPushButton("🔓")
        # Ustawiamy minimalny rozmiar przycisku: szerokość=40px, wysokość=35px
        self.lock_columns_btn.setMinimumSize(40, 35)
        # Ustawiamy maksymalny rozmiar: szerokość=40px, wysokość=35px (przycisk nie rozciągnie się)
        self.lock_columns_btn.setMaximumSize(40, 35)
        # KLUCZOWE: Wyzeruj padding (domyślny theme dodaje 8px 16px)
        self.lock_columns_btn.setStyleSheet("padding: 2px;")
        # Podłączamy kliknięcie przycisku do metody toggle_column_lock
        self.lock_columns_btn.clicked.connect(self.toggle_column_lock)
        # Ustawiamy tooltip (dymek po najechaniu myszką) z opisem funkcji
        self.lock_columns_btn.setToolTip(t("habit.lock_columns", "Zablokuj/odblokuj regulację szerokości kolumn"))
        # Inicjalizujemy flagę stanu - False = kolumny są odblokowane
        self.columns_locked = False
        # Dodajemy przycisk do poziomego układu (będzie pierwszym elementem od lewej)
        toolbar_main_layout.addWidget(self.lock_columns_btn)
        
        # ========== PRZYCISK ODŚWIEŻANIA ==========
        # Tworzymy przycisk z ikoną odświeżania (🔄)
        self.refresh_btn = QPushButton("🔄")
        # Minimalny rozmiar: 40x35px
        self.refresh_btn.setMinimumSize(40, 35)
        # Maksymalny rozmiar: 40x35px (kompaktowy przycisk)
        self.refresh_btn.setMaximumSize(40, 35)
        # KLUCZOWE: Wyzeruj padding
        self.refresh_btn.setStyleSheet("padding: 2px;")
        # Podłączamy kliknięcie do metody refresh_table
        self.refresh_btn.clicked.connect(self.refresh_table)
        # Tooltip z opisem akcji
        self.refresh_btn.setToolTip(t("habit.refresh", "Odśwież tabelę"))
        # Dodajemy do układu (drugi element od lewej)
        toolbar_main_layout.addWidget(self.refresh_btn)
        
        # ========== SEPARATOR (odstęp) ==========
        # Dodajemy 20px pustej przestrzeni jako separator wizualny między grupami przycisków
        toolbar_main_layout.addSpacing(20)
        
        # ========== PRZYCISK EKSPORTU CSV ==========
        # Tworzymy przycisk z ikoną i tekstem (Eksportuj CSV)
        self.export_csv_btn = QPushButton("📂" )
        # Minimalna wysokość: 35px
        self.export_csv_btn.setMinimumHeight(35)
        # Maksymalna wysokość: 35px (zgodna z innymi przyciskami)
        self.export_csv_btn.setMaximumHeight(35)
        # Minimalna szerokość: 150px (pomieści tekst)
        self.export_csv_btn.setMinimumWidth(50)
        # Maksymalna szerokość: 200px (nie rozciągnie się nadmiernie)
        self.export_csv_btn.setMaximumWidth(100)
        # Podłączamy kliknięcie do metody export_to_csv
        self.export_csv_btn.clicked.connect(self.export_to_csv)
        # Tooltip z opisem
        self.export_csv_btn.setToolTip(t("habit.export_csv", "Eksportuj tabelę do pliku CSV"))
        # Dodajemy do układu
        toolbar_main_layout.addWidget(self.export_csv_btn)
        
        # ========== SEPARATOR ==========
        toolbar_main_layout.addSpacing(20)
        
        # ========== PRZYCISK POPRZEDNI MIESIĄC ==========
        # Przycisk ze strzałką w lewo (◀)
        self.prev_month_btn = QPushButton("◀")
        # Rozmiar: 40x35px (kompaktowy)
        self.prev_month_btn.setMinimumSize(40, 35)
        self.prev_month_btn.setMaximumSize(40, 35)
        # KLUCZOWE: Wyzeruj padding
        self.prev_month_btn.setStyleSheet("padding: 2px;")
        # Podłączamy do metody prev_month
        self.prev_month_btn.clicked.connect(self.prev_month)
        # Tooltip
        self.prev_month_btn.setToolTip(t("habit.prev_month", "Poprzedni miesiąc"))
        # Dodajemy do układu
        toolbar_main_layout.addWidget(self.prev_month_btn)
        
        # ========== LISTA ROZWIJANA MIESIĘCY ==========
        # Tworzymy ComboBox (listę rozwijaną) do wyboru miesiąca
        self.month_combo = QComboBox()
        # Minimalna wysokość: 35px (zgodna z przyciskami)
        self.month_combo.setMinimumHeight(35)
        # Minimalna szerokość: 200px (pomieści nazwy miesięcy z rokiem, np. "Październik 2025")
        self.month_combo.setMinimumWidth(200)
        
        # Wypełnij miesiące (tylko do aktualnego miesiąca) - z tłumaczeniami
        # Lista polskich nazw miesięcy pobrana z systemu tłumaczeń
        months = [
            t("habit.month.january", "Styczeń"),
            t("habit.month.february", "Luty"),
            t("habit.month.march", "Marzec"),
            t("habit.month.april", "Kwiecień"),
            t("habit.month.may", "Maj"),
            t("habit.month.june", "Czerwiec"),
            t("habit.month.july", "Lipiec"),
            t("habit.month.august", "Sierpień"),
            t("habit.month.september", "Wrzesień"),
            t("habit.month.october", "Październik"),
            t("habit.month.november", "Listopad"),
            t("habit.month.december", "Grudzień")
        ]
        
        # Pobierz aktualną datę systemową
        today = date.today()
        # Rok bieżący (np. 2025)
        current_year = today.year
        # Miesiąc bieżący (1-12)
        current_month = today.month
        
        # LOGIKA: Dodaj miesiące tylko do aktualnego miesiąca w aktualnym roku
        # lub wszystkie miesiące w poprzednich latach (nie pozwalaj wybierać przyszłych miesięcy)
        if self.current_year == current_year:
            # Jeśli przeglądamy aktualny rok - dodaj miesiące tylko do obecnego miesiąca
            # range(current_month) generuje liczby od 0 do (current_month-1)
            for i in range(current_month):
                # Dodaj element do listy rozwijanej: "Styczeń 2025", wartość data: 1
                self.month_combo.addItem(f"{months[i]} {self.current_year}", i + 1)
        else:
            # Jeśli przeglądamy poprzedni rok - dodaj wszystkie 12 miesięcy
            # enumerate() zwraca (indeks, wartość) dla każdego elementu listy
            for i, month in enumerate(months):
                self.month_combo.addItem(f"{month} {self.current_year}", i + 1)
        
        # Ustaw aktualny miesiąc jako wybrany (jeśli dostępny na liście)
        if self.current_year == current_year and self.current_month <= current_month:
            # Jeśli przeglądamy aktualny rok i miesiąc jest dostępny
            # setCurrentIndex przyjmuje indeks od 0, a miesiące są od 1, więc -1
            self.month_combo.setCurrentIndex(self.current_month - 1)
        elif self.current_year < current_year:
            # Jeśli przeglądamy poprzedni rok - ustaw ostatni dostępny miesiąc (grudzień)
            # count() zwraca liczbę elementów, -1 bo indeksy od 0
            self.month_combo.setCurrentIndex(self.month_combo.count() - 1)
        
        # Podłącz sygnał zmiany wyboru do metody on_month_combo_changed
        # Wywoła się gdy użytkownik wybierze inny miesiąc z listy
        self.month_combo.currentIndexChanged.connect(self.on_month_combo_changed)
        # Dodaj ComboBox do układu poziomego
        toolbar_main_layout.addWidget(self.month_combo)
        
        # ========== PRZYCISK NASTĘPNY MIESIĄC ==========
        # Przycisk ze strzałką w prawo (▶)
        self.next_month_btn = QPushButton("▶")
        # Rozmiar: 40x35px (kompaktowy)
        self.next_month_btn.setMinimumSize(40, 35)
        self.next_month_btn.setMaximumSize(40, 35)
        # KLUCZOWE: Wyzeruj padding
        self.next_month_btn.setStyleSheet("padding: 2px;")
        # Podłączamy do metody next_month
        self.next_month_btn.clicked.connect(self.next_month)
        # Tooltip
        self.next_month_btn.setToolTip(t("habit.next_month", "Następny miesiąc"))
        # Dodajemy do układu
        toolbar_main_layout.addWidget(self.next_month_btn)
        
        # ========== SEPARATOR ==========
        toolbar_main_layout.addSpacing(20)
        
        # ========== PRZYCISK DODAJ NAWYK ==========
        # Przycisk z ikoną notatnika (📝) - bez tekstu
        self.add_habit_btn = QPushButton("➕")
        # Rozmiar: 40x35px (kompaktowy, ikona)
        self.add_habit_btn.setMinimumSize(40, 35)
        self.add_habit_btn.setMaximumSize(40, 35)
        # KLUCZOWE: Wyzeruj padding
        self.add_habit_btn.setStyleSheet("padding: 2px;")
        # Podłączamy do metody on_add_habit_clicked
        self.add_habit_btn.clicked.connect(self.on_add_habit_clicked)
        # Tooltip - pełny opis pojawi się po najechaniu myszką
        self.add_habit_btn.setToolTip(t("habit.add_habit", "Dodaj nowy nawyk"))
        # Dodajemy do układu
        toolbar_main_layout.addWidget(self.add_habit_btn)
        
        # ========== PRZYCISK USUŃ NAWYK ==========
        # Przycisk z ikoną kosza (🗑️) - bez tekstu
        self.remove_habit_btn = QPushButton("➖")
        # Rozmiar: 40x35px
        self.remove_habit_btn.setMinimumSize(40, 35)
        self.remove_habit_btn.setMaximumSize(40, 35)
        # KLUCZOWE: Wyzeruj padding
        self.remove_habit_btn.setStyleSheet("padding: 2px;")
        # Podłączamy do metody on_remove_habit_clicked
        self.remove_habit_btn.clicked.connect(self.on_remove_habit_clicked)
        # Tooltip
        self.remove_habit_btn.setToolTip(t("habit.remove_habit", "Usuń nawyk"))
        # Dodajemy do układu
        toolbar_main_layout.addWidget(self.remove_habit_btn)
        
        # ========== PRZYCISK EDYTUJ NAWYK ==========
        # Przycisk z ikoną ołówka (✏️) - bez tekstu
        self.edit_habit_btn = QPushButton("✏️")
        # Rozmiar: 40x35px
        self.edit_habit_btn.setMinimumSize(40, 35)
        self.edit_habit_btn.setMaximumSize(40, 35)
        # KLUCZOWE: Wyzeruj padding
        self.edit_habit_btn.setStyleSheet("padding: 2px;")
        # Podłączamy do metody on_edit_habit_clicked
        self.edit_habit_btn.clicked.connect(self.on_edit_habit_clicked)
        # Tooltip
        self.edit_habit_btn.setToolTip(t("habit.edit_habit", "Edytuj nawyk"))
        # Dodajemy do układu
        toolbar_main_layout.addWidget(self.edit_habit_btn)
        
        # ========== SEPARATOR ==========
        toolbar_main_layout.addSpacing(20)
        
        # ========== PRZYCISK STATYSTYK ==========
        # Przycisk z ikoną wykresu (📊) - bez tekstu
        self.statistics_btn = QPushButton("📊")
        # Rozmiar: 40x35px (kompaktowy)
        self.statistics_btn.setMinimumSize(40, 35)
        self.statistics_btn.setMaximumSize(40, 35)
        # KLUCZOWE: Wyzeruj padding
        self.statistics_btn.setStyleSheet("padding: 2px;")
        # Podłączamy do metody open_statistics
        self.statistics_btn.clicked.connect(self.open_statistics)
        # Tooltip
        self.statistics_btn.setToolTip(t("habit.statistics", "Otwórz okno statystyk"))
        # Dodajemy do układu
        toolbar_main_layout.addWidget(self.statistics_btn)
        
        # ========== PRZYCISK ANALIZY AI ==========
        # Przycisk z ikoną robota i tekstem (🤖 Analiza AI) - zachowany tekst dla rozpoznawalności
        self.ai_analysis_btn = QPushButton("🪄 ")
        # Minimalna wysokość: 35px (zgodna z innymi)
        self.ai_analysis_btn.setMinimumHeight(35)
        # Maksymalna wysokość: 35px
        self.ai_analysis_btn.setMaximumHeight(35)
        # Minimalna szerokość: 120px (pomieści tekst)
        self.ai_analysis_btn.setMinimumWidth(120)
        # Maksymalna szerokość: 150px (nie rozciągnie się nadmiernie)
        self.ai_analysis_btn.setMaximumWidth(150)
        # Podłączamy do metody open_ai_analysis
        self.ai_analysis_btn.clicked.connect(self.open_ai_analysis)
        # Tooltip
        self.ai_analysis_btn.setToolTip(t("habit.ai_analysis", "Analiza AI nawyków"))
        # Dodajemy do układu
        toolbar_main_layout.addWidget(self.ai_analysis_btn)
        
        # ========== STRETCH (elastyczna przestrzeń) ==========
        # KLUCZOWE: Dodaj stretch na końcu, aby przyciski nie rozciągały się
        # Wszystka wolna przestrzeń w poziomym układzie pójdzie tutaj (na koniec)
        # Dzięki temu przyciski zachowają swoje minimalne/maksymalne rozmiary i będą wyrównane do lewej
        toolbar_main_layout.addStretch()
        
        # Dodaj cały toolbar (ramkę z układem i przyciskami) do głównego layoutu widoku
        parent_layout.addWidget(toolbar_frame)
        
    def create_habits_table(self, parent_layout):
        """Tworzy tabelę nawyków"""
        table_group = QGroupBox(t("habit.habits_title", "Nawyki"))
        table_layout = QVBoxLayout(table_group)
        
        self.habits_table = QTableWidget()
        self.habits_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectItems)
        self.habits_table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.habits_table.setAlternatingRowColors(True)
        
        # NIE stosuj stylesheet tutaj - będzie aplikowany przez apply_theme()
        
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
            t("habit.month.january", "Styczeń"),
            t("habit.month.february", "Luty"),
            t("habit.month.march", "Marzec"),
            t("habit.month.april", "Kwiecień"),
            t("habit.month.may", "Maj"),
            t("habit.month.june", "Czerwiec"),
            t("habit.month.july", "Lipiec"),
            t("habit.month.august", "Sierpień"),
            t("habit.month.september", "Wrzesień"),
            t("habit.month.october", "Październik"),
            t("habit.month.november", "Listopad"),
            t("habit.month.december", "Grudzień")
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
            QMessageBox.information(self, t("common.info", "Informacja"), 
                                   t("habit.message.select_cell", "Aby edytować wartość nawyku, najpierw kliknij na komórkę w tabeli."))
            return
            
        # Sprawdź czy to kolumna nawyku
        if self.selected_column <= 1:
            QMessageBox.information(self, t("common.info", "Informacja"), 
                                   t("habit.message.cannot_edit_date", "Nie można edytować kolumn daty i dnia tygodnia."))
            return
            
        habit_index = self.selected_column - 2
        if habit_index >= len(self.habits):
            QMessageBox.warning(self, t("common.error", "Błąd"), t("habit.message.invalid_column", "Nieprawidłowa kolumna nawyku."))
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
            from .habit_dialogs import (
                SimpleCheckboxDialog, SimpleCounterDialog, SimpleDurationDialog,
                SimpleTimeDialog, SimpleScaleDialog, SimpleTextDialog
            )
        except ImportError as e:
            QMessageBox.warning(self, t("common.error", "Błąd"), t("habit.message.cannot_load_dialogs", "Nie można załadować dialogów: {error}").format(error=str(e)))
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
                    QMessageBox.warning(self, t("common.error", "Błąd"), t("habit.message.no_db_connection", "Brak połączenia z bazą danych."))
            except Exception as e:
                QMessageBox.warning(self, t("common.error", "Błąd"), t("habit.message.cannot_save_value", "Nie można zapisać wartości nawyku:\n{error}").format(error=str(e)))
        
    def toggle_column_lock(self):
        """Przełącza blokadę/odblokowanie regulacji szerokości kolumn"""
        self.columns_locked = not self.columns_locked
        
        header = self.habits_table.horizontalHeader()
        if not header:
            return
        
        if self.columns_locked:
            # Zablokuj regulację szerokości kolumn
            header.setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
            self.lock_columns_btn.setText("🔒")
            self.lock_columns_btn.setToolTip(t("habit.unlock_columns", "Kliknij aby odblokować regulację szerokości kolumn"))
            
            # Zapisz aktualne szerokości kolumn jako domyślne
            self.save_column_widths()
            # Zapisz stan blokady
            self.save_lock_state(True)
            
        else:
            # Odblokuj regulację szerokości kolumn
            header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
            self.lock_columns_btn.setText("🔓")
            self.lock_columns_btn.setToolTip(t("habit.lock_columns", "Kliknij aby zablokować regulację szerokości kolumn"))
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
                        self.lock_columns_btn.setText("🔒")
                        self.lock_columns_btn.setToolTip(t("habit.unlock_columns", "Kliknij aby odblokować regulację szerokości kolumn"))
                    else:
                        header.setSectionResizeMode(QHeaderView.ResizeMode.Interactive)
                        self.lock_columns_btn.setText("🔓")
                        self.lock_columns_btn.setToolTip(t("habit.lock_columns", "Kliknij aby zablokować regulację szerokości kolumn"))
                
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
            
        # Użyj kolorów zapisanych w self.colors
        header_bg = self.colors.get("bg_secondary", "#F5F5F5")
        border_color = self.colors.get("border_light", "#CCCCCC")
        accent_color = self.colors.get("accent_primary", "#2196F3")
        accent_hover = self.colors.get("accent_hover", "#1976D2")
        accent_pressed = self.colors.get("accent_pressed", "#0D47A1")
        text_color = self.colors.get("text_primary", "#1A1A1A")
        
        # Dodaj specjalną stylizację dla nagłówków nawyków
        habit_header_style = f"""
            QTableWidget::horizontalHeader::section {{
                height: 50px;
                background-color: {header_bg};
                border: 1px solid {border_color};
                padding: 4px 8px;
                font-weight: bold;
                font-size: 12px;
            }}
            QTableWidget::horizontalHeader::section:hover {{
                background-color: {accent_hover};
                border: 2px solid {accent_color};
            }}
        """
        
        # Dodaj specjalne style dla kolumn nawyków (od kolumny 2)
        for i in range(2, self.habits_table.columnCount()):
            habit_header_style += f"""
                QTableWidget::horizontalHeader::section:nth({i}) {{
                    background-color: {header_bg};
                    border: 2px solid {accent_color};
                    border-radius: 3px;
                    margin: 1px;
                    font-weight: bold;
                    color: {text_color};
                }}
                QTableWidget::horizontalHeader::section:nth({i}):hover {{
                    background-color: {accent_hover};
                    border: 2px solid {accent_pressed};
                    color: {text_color};
                }}
                QTableWidget::horizontalHeader::section:nth({i}):pressed {{
                    background-color: {accent_pressed};
                    border: 2px solid {accent_pressed};
                    color: white;
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
            self.habits_table.setHorizontalHeaderLabels([t("common.info", "Informacja")])
            
            item = QTableWidgetItem(t("habit.message.no_habits_info", "Brak nawyków. Dodaj pierwszy nawyk używając przycisku 'Dodaj nawyk'."))
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
        headers = [t("habit.date", "Data"), t("habit.day_column", "Dzień")]
        for habit in self.habits:
            habit_header = f"{habit['name']}\n({habit['type']})"
            headers.append(habit_header)
            
        self.habits_table.setHorizontalHeaderLabels(headers)
        
        # Stylizuj nagłówki nawyków (kolumny 2+) jako przyciski
        self.style_habit_headers()
        
        # Mapowanie dni tygodnia na skróty
        weekday_names = [
            t("habit.day.mon", "PN"),
            t("habit.day.tue", "WT"),
            t("habit.day.wed", "ŚR"),
            t("habit.day.thu", "CZ"),
            t("habit.day.fri", "PT"),
            t("habit.day.sat", "SO"),
            t("habit.day.sun", "ND")
        ]
        
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
            
            # Użyj kolorów z self.colors (odświeżane przez apply_theme)
            saturday_color = QColor(self.colors.get("weekend_saturday", "#C8FFC8"))
            sunday_color = QColor(self.colors.get("weekend_sunday", "#FFC896"))
            weekend_text_color = QColor(self.colors.get("weekend_text", "#000000"))
            
            # Kolorowanie weekendów dla obu kolumn
            if weekday == 5:  # Sobota
                date_item.setBackground(QBrush(saturday_color))
                date_item.setForeground(QBrush(weekend_text_color))
                weekday_item.setBackground(QBrush(saturday_color))
                weekday_item.setForeground(QBrush(weekend_text_color))
            elif weekday == 6:  # Niedziela
                date_item.setBackground(QBrush(sunday_color))
                date_item.setForeground(QBrush(weekend_text_color))
                weekday_item.setBackground(QBrush(sunday_color))
                weekday_item.setForeground(QBrush(weekend_text_color))
                
            self.habits_table.setItem(day - 1, 0, date_item)
            self.habits_table.setItem(day - 1, 1, weekday_item)
            
            # Kolumny nawyków
            for col, habit in enumerate(self.habits, 2):
                value = self.get_habit_value(habit['id'], current_date)
                
                # Specjalne traktowanie dla checkbox
                if habit['type'] == 'checkbox':
                    # Użyj kolorów z self.colors
                    checkbox_border = self.colors.get("checkbox_border", "#3498db")
                    checkbox_checked = self.colors.get("checkbox_checked", "#27ae60")
                    checkbox_checked_hover = self.colors.get("checkbox_checked_hover", "#229954")
                    saturday_color = self.colors.get("weekend_saturday", "#C8FFC8")
                    sunday_color = self.colors.get("weekend_sunday", "#FFC896")
                    
                    checkbox = QCheckBox()
                    checkbox.setChecked(value == "1")
                    checkbox.setEnabled(False)  # Tylko do odczytu
                    checkbox.setStyleSheet(f"""
                        QCheckBox::indicator {{
                            width: 20px;
                            height: 20px;
                            border: 2px solid {checkbox_border};
                            border-radius: 4px;
                            background-color: white;
                        }}
                        QCheckBox::indicator:checked {{
                            background-color: {checkbox_checked};
                            border-color: {checkbox_checked};
                        }}
                        QCheckBox::indicator:checked:hover {{
                            background-color: {checkbox_checked_hover};
                        }}
                        QCheckBox {{
                            spacing: 0px;
                        }}
                    """)
                    
                    # Stwórz kontener do wyśrodkowania checkboxa
                    container = QWidget()
                    layout = QHBoxLayout(container)
                    layout.addWidget(checkbox)
                    layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
                    layout.setContentsMargins(0, 0, 0, 0)
                    
                    # Kolorowanie weekendów dla kontenera
                    if weekday == 5:  # Sobota
                        container.setStyleSheet(f"""
                            QWidget {{
                                background-color: {saturday_color};
                            }}
                        """)
                    elif weekday == 6:  # Niedziela
                        container.setStyleSheet(f"""
                            QWidget {{
                                background-color: {sunday_color};
                            }}
                        """)
                    
                    self.habits_table.setCellWidget(day - 1, col, container)
                else:
                    # Dla innych typów nawyków używamy standardowego QTableWidgetItem
                    display_value = self.format_habit_value(value, habit)
                    
                    # Użyj kolorów z self.colors
                    saturday_color = QColor(self.colors.get("weekend_saturday", "#C8FFC8"))
                    sunday_color = QColor(self.colors.get("weekend_sunday", "#FFC896"))
                    weekend_text_color = QColor(self.colors.get("weekend_text", "#000000"))
                    
                    item = QTableWidgetItem(display_value)
                    item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled)  # Tylko do odczytu
                    
                    # Kolorowanie weekendów dla kolumn nawyków
                    if weekday == 5:  # Sobota
                        item.setBackground(QBrush(saturday_color))
                        item.setForeground(QBrush(weekend_text_color))
                    elif weekday == 6:  # Niedziela
                        item.setBackground(QBrush(sunday_color))
                        item.setForeground(QBrush(weekend_text_color))
                        
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
                return t("habit.format.minutes", "{min}min").format(min=total_minutes)
            else:
                hours = total_minutes // 60
                remaining_minutes = total_minutes % 60
                if remaining_minutes == 0:
                    return t("habit.format.hours", "{h}h").format(h=hours)
                else:
                    return t("habit.format.hours_minutes", "{h}h{min}min").format(h=hours, min=remaining_minutes)
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
        if logical_index <= 1:  # Kolumny daty i dnia tygodnia - ignoruj
            return
            
        habit_index = logical_index - 2  # Teraz mamy 2 kolumny przed kolumnami nawyków
        
        if habit_index >= len(self.habits):
            return
            
        habit = self.habits[habit_index]
        
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
                    QMessageBox.warning(self, t("common.error", "Błąd"), t("habit.message.no_db_connection", "Brak połączenia z bazą danych."))
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
                
                QMessageBox.information(self, t("common.success", "Sukces"), t("habit.message.added", "Dodano nawyk: {name}").format(name=habit_data['name']))
                
            except Exception as e:
                QMessageBox.warning(self, t("common.error", "Błąd"), t("habit.message.cannot_add_habit", "Nie można dodać nawyku:\n{error}").format(error=str(e)))
                
    def on_remove_habit_clicked(self):
        """Obsługuje usuwanie nawyku"""
        if not self.habits:
            QMessageBox.information(self, t("common.info", "Informacja"), t("habit.message.no_habits_to_remove", "Brak nawyków do usunięcia."))
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
                        QMessageBox.warning(self, t("common.error", "Błąd"), t("habit.message.no_db_connection", "Brak połączenia z bazą danych."))
                        return
                    
                    # Znajdź nazwę nawyku dla komunikatu
                    habit_name = next((h['name'] for h in self.habits if h['id'] == habit_id), "Nieznany")
                    
                    success = self.db_manager.remove_habit_column(habit_id)
                    if success:
                        print(f"DEBUG: Usunięto nawyk {habit_name} (ID: {habit_id})")
                        
                        # Odśwież listę i tabelę
                        self.load_habits()
                        self.refresh_table()
                        
                        QMessageBox.information(self, t("common.success", "Sukces"), t("habit.message.removed", "Usunięto nawyk: {name}").format(name=habit_name))
                    else:
                        QMessageBox.warning(self, t("common.error", "Błąd"), t("habit.message.remove_failed", "Nie można usunąć nawyku."))
                        
                except Exception as e:
                    QMessageBox.warning(self, t("common.error", "Błąd"), t("habit.message.cannot_remove_habit", "Nie można usunąć nawyku:\n{error}").format(error=str(e)))
    
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
                t("habit.export_csv_dialog", "Eksportuj do CSV"),
                default_filename,
                t("habit.csv_files_filter", "Pliki CSV (*.csv);;Wszystkie pliki (*)")
            )
            
            if not file_path:
                return  # Użytkownik anulował
            
            # Przygotuj dane do eksportu
            days_in_month = calendar.monthrange(self.current_year, self.current_month)[1]
            weekday_names = [
                t("habit.day.mon", "PN"),
                t("habit.day.tue", "WT"),
                t("habit.day.wed", "ŚR"),
                t("habit.day.thu", "CZ"),
                t("habit.day.fri", "PT"),
                t("habit.day.sat", "SO"),
                t("habit.day.sun", "ND")
            ]
            
            # Nagłówki CSV
            headers = [t("habit.date", "Data"), t("habit.day_column", "Dzień")]
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
                t("common.success", "Sukces"), 
                t("habit.message.export_success", "Pomyślnie wyeksportowano {count} dni z danymi do pliku:\n{path}").format(count=exported_days, path=file_path)
            )
            
            print(f"DEBUG: Wyeksportowano {exported_days} dni do {file_path}")
            
        except Exception as e:
            QMessageBox.warning(self, t("common.error", "Błąd"), t("habit.message.export_error", "Nie można wyeksportować danych:\n{error}").format(error=str(e)))
            print(f"DEBUG: Błąd eksportu CSV: {e}")
    
    def open_statistics(self):
        """Otwiera okno statystyk nawyków"""
        from ...ui.habit_statistics_window import HabitStatisticsWindow
        
        # Pobierz wszystkie nawyki
        habits = self.habits if hasattr(self, 'habits') and self.habits else []
        
        # Otwórz okno statystyk
        stats_window = HabitStatisticsWindow(
            db_manager=self.db_manager,
            habits=habits,
            parent=self
        )
        stats_window.exec()
    
    def open_ai_analysis(self):
        """Otwiera okno analizy AI (placeholder)"""
        QMessageBox.information(
            self,
            t("habit.ai_analysis", "Analiza AI"),
            t("habit.ai_analysis_placeholder", "Funkcja analizy AI będzie dostępna wkrótce.")
        )
    
    def apply_theme(self):
        """Aplikuje aktualny motyw do widoku Habit Tracker"""
        if not self.theme_manager:
            logger.warning("[HABIT] Theme manager not available")
            return
        
        # Odśwież kolory z aktualnego schematu
        self.colors = self.theme_manager.get_current_colors()
        
        # Pobierz podstawowe kolory
        bg_main = self.colors.get("bg_main", "#FFFFFF")
        bg_secondary = self.colors.get("bg_secondary", "#F5F5F5")
        text_primary = self.colors.get("text_primary", "#1A1A1A")
        text_secondary = self.colors.get("text_secondary", "#666666")
        accent_primary = self.colors.get("accent_primary", "#2196F3")
        accent_hover = self.colors.get("accent_hover", "#1976D2")
        border_light = self.colors.get("border_light", "#CCCCCC")
        
        # Aplikuj stylesheet do głównego widgetu
        self.setStyleSheet(f"""
            QWidget#HabbitTrackerView {{
                background-color: {bg_main};
                color: {text_primary};
            }}
            
            QLabel {{
                color: {text_primary};
            }}
            
            QPushButton {{
                background-color: {accent_primary};
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            
            QPushButton:hover {{
                background-color: {accent_hover};
            }}
            
            QPushButton:disabled {{
                background-color: {border_light};
                color: {text_secondary};
            }}
            
            QTableWidget {{
                background-color: {bg_main};
                alternate-background-color: {bg_secondary};
                gridline-color: {border_light};
                border: 1px solid {border_light};
                color: {text_primary};
            }}
            
            QTableWidget::item:selected {{
                background-color: {accent_primary};
                color: white;
            }}
            
            QHeaderView::section {{
                background-color: {bg_secondary};
                color: {text_primary};
                padding: 8px;
                border: none;
                border-bottom: 2px solid {accent_primary};
                font-weight: bold;
            }}
            
            QComboBox {{
                background-color: {bg_main};
                border: 1px solid {border_light};
                border-radius: 4px;
                padding: 6px;
                color: {text_primary};
            }}
            
            QComboBox:hover {{
                border: 2px solid {accent_primary};
            }}
            
            QFrame {{
                background-color: {bg_secondary};
                border: 1px solid {border_light};
                border-radius: 4px;
            }}
            
            QGroupBox {{
                background-color: {bg_main};
                color: {text_primary};
                border: 1px solid {border_light};
                border-radius: 4px;
                margin-top: 10px;
                font-weight: bold;
            }}
            
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """)
        
        # Ustaw nazwę obiektu dla stylowania
        self.setObjectName("HabbitTrackerView")
        
        # Zastosuj style nagłówków tabeli jeśli tabela istnieje
        if hasattr(self, 'habits_table') and self.habits_table:
            self.style_habit_headers()
    
    def closeEvent(self, event):
        """Cleanup przy zamykaniu widoku"""
        try:
            if self.sync_manager:
                logger.info("[HABIT] 🛑 Zatrzymywanie synchronizacji...")
                self.sync_manager.stop()
                self.sync_manager = None
            super().closeEvent(event)
        except Exception as e:
            logger.error(f"[HABIT] ❌ Błąd podczas zamykania: {e}")
            event.accept()
    
    def __del__(self):
        """Destruktor - cleanup synchronizacji"""
        try:
            if hasattr(self, 'sync_manager') and self.sync_manager:
                logger.info("[HABIT] 🧹 Cleanup synchronizacji w destruktorze")
                self.sync_manager.stop()
        except Exception as e:
            logger.error(f"[HABIT] ❌ Błąd cleanup w destruktorze: {e}")
            
            # 🎨 KLUCZOWE: Odśwież komórki tabeli aby zastosować nowe kolory
            if len(self.habits) > 0:
                self.refresh_table()
                logger.info("[HABIT] Table refreshed with new theme colors")
        
        logger.info("[HABIT] Theme applied successfully")
    
    def refresh_theme(self):
        """Odświeża motyw i tabelę"""
        logger.info("[HABIT] Refreshing theme...")
        self.apply_theme()
        # Teraz odśwież tabelę aby zastosować nowe kolory do komórek
        if hasattr(self, 'habits_table') and self.habits_table and len(self.habits) > 0:
            self.refresh_table()


if __name__ == "__main__":
    # Test widoku
    import sys
    from PyQt6.QtWidgets import QApplication
    
    app = QApplication(sys.argv)
    view = HabbitTrackerView()
    view.show()
    sys.exit(app.exec())

