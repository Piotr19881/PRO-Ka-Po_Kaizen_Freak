"""
Habit Statistics Window - Okno statystyk nawyków
Umożliwia tworzenie różnych zestawień statystycznych na podstawie wybranych kolumn nawyków
"""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QPushButton, QLabel, QComboBox, QListWidget,
    QTableWidget, QTableWidgetItem, QAbstractItemView,
    QHeaderView, QWidget, QScrollArea, QCheckBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPainter, QFont, QColor, QBrush
from PyQt6.QtPrintSupport import QPrinter, QPrintDialog
from datetime import datetime, date
from typing import List, Dict, Any, Optional
from loguru import logger

# Opcjonalny import matplotlib (wspiera PyQt6)
try:
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.dates as mdates
    MATPLOTLIB_AVAILABLE = True
except Exception as exc:  # ImportError lub brak backendu Qt
    MATPLOTLIB_AVAILABLE = False
    logger.warning("[HABIT STATS] Matplotlib not available - charts will be limited (%s)", exc)

# Opcjonalny import numpy i scipy dla analiz statystycznych
try:
    import numpy as np
    from scipy import stats
    SCIPY_AVAILABLE = True
except ImportError:
    SCIPY_AVAILABLE = False
    logger.warning("[HABIT STATS] SciPy/NumPy not available - correlation analysis will be limited")

from ..utils.i18n_manager import t
from ..utils.theme_manager import get_theme_manager


class HabitStatisticsWindow(QDialog):
    """Okno statystyk nawyków z różnymi rodzajami zestawień"""
    
    def __init__(self, db_manager, habits: List[Dict[str, Any]], parent=None):
        super().__init__(parent)
        self.db_manager = db_manager
        self.habits = habits
        self.theme_manager = get_theme_manager()
        
        self.selected_habits = []  # Wybrane nawyki do analizy
        self.current_chart_type = "sum_table"  # Domyślny typ zestawienia
        
        self.setup_ui()
        self.apply_theme()
        
    def setup_ui(self):
        """Konfiguracja interfejsu użytkownika"""
        self.setWindowTitle(t("habit.statistics", "Statystyki nawyków"))
        self.setMinimumSize(1000, 700)
        
        main_layout = QVBoxLayout(self)
        
        # === Sekcja zarządzania wyborem ===
        control_group = self.create_control_section()
        main_layout.addWidget(control_group)
        
        # === Sekcja główna - wygenerowana treść ===
        self.content_area = QScrollArea()
        self.content_area.setWidgetResizable(True)
        self.content_area.setMinimumHeight(400)
        
        self.content_widget = QWidget()
        self.content_layout = QVBoxLayout(self.content_widget)
        self.content_area.setWidget(self.content_widget)
        
        # Placeholder
        placeholder_label = QLabel(t("habit.stats.select_habits", "Wybierz nawyki i rodzaj zestawienia, aby wygenerować statystyki."))
        placeholder_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        placeholder_label.setStyleSheet("color: gray; font-size: 14px; padding: 50px;")
        self.content_layout.addWidget(placeholder_label)
        
        main_layout.addWidget(self.content_area)
        
        # === Przyciski akcji ===
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        self.print_btn = QPushButton("🖨️ " + t("common.print", "Drukuj"))
        self.print_btn.clicked.connect(self.print_statistics)
        self.print_btn.setMinimumHeight(35)
        button_layout.addWidget(self.print_btn)
        
        self.close_btn = QPushButton(t("common.close", "Zamknij"))
        self.close_btn.clicked.connect(self.accept)
        self.close_btn.setMinimumHeight(35)
        button_layout.addWidget(self.close_btn)
        
        main_layout.addLayout(button_layout)
        
    def create_control_section(self) -> QGroupBox:
        """Tworzy sekcję zarządzania wyborem kolumn i rodzaju zestawień"""
        control_group = QGroupBox(t("habit.stats.control_panel", "Panel zarządzania"))
        control_layout = QHBoxLayout(control_group)
        
        # === Wybór nawyków ===
        habits_layout = QVBoxLayout()
        habits_label = QLabel(t("habit.stats.select_columns", "Wybierz nawyki:"))
        habits_label.setStyleSheet("font-weight: bold;")
        habits_layout.addWidget(habits_label)
        
        self.habits_list = QListWidget()
        self.habits_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        self.habits_list.setMaximumHeight(150)
        
        # Wypełnij listę nawykami
        for habit in self.habits:
            self.habits_list.addItem(f"{habit['name']} ({habit['type']})")
        
        habits_layout.addWidget(self.habits_list)
        control_layout.addLayout(habits_layout, stretch=2)
        
        # === Rodzaj zestawienia ===
        chart_layout = QVBoxLayout()
        chart_label = QLabel(t("habit.stats.chart_type", "Rodzaj zestawienia:"))
        chart_label.setStyleSheet("font-weight: bold;")
        chart_layout.addWidget(chart_label)
        
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItem("📊 " + t("habit.stats.sum_table", "Tabela sum"), "sum_table")
        self.chart_type_combo.addItem("📈 " + t("habit.stats.avg_table", "Tabela średnich"), "avg_table")
        self.chart_type_combo.addItem("� " + t("habit.stats.correlation", "Analiza korelacji"), "correlation")
        self.chart_type_combo.addItem("�📉 " + t("habit.stats.line_chart", "Wykres liniowy"), "line_chart")
        self.chart_type_combo.addItem("📊 " + t("habit.stats.bar_chart", "Wykres słupkowy"), "bar_chart")
        self.chart_type_combo.addItem("🔢 " + t("habit.stats.detailed_table", "Szczegółowa tabela"), "detailed_table")
        self.chart_type_combo.currentIndexChanged.connect(self.on_chart_type_changed)
        chart_layout.addWidget(self.chart_type_combo)
        
        # Opcje zakresu dat
        date_range_label = QLabel(t("habit.stats.date_range", "Zakres dat:"))
        date_range_label.setStyleSheet("font-weight: bold; margin-top: 15px;")
        chart_layout.addWidget(date_range_label)
        
        self.date_range_combo = QComboBox()
        self.date_range_combo.addItem(t("habit.stats.current_month", "Bieżący miesiąc"), "current_month")
        self.date_range_combo.addItem(t("habit.stats.last_30_days", "Ostatnie 30 dni"), "last_30_days")
        self.date_range_combo.addItem(t("habit.stats.last_90_days", "Ostatnie 90 dni"), "last_90_days")
        self.date_range_combo.addItem(t("habit.stats.current_year", "Bieżący rok"), "current_year")
        chart_layout.addWidget(self.date_range_combo)
        
        chart_layout.addStretch()
        control_layout.addLayout(chart_layout, stretch=1)
        
        # === Przycisk generowania ===
        generate_layout = QVBoxLayout()
        generate_layout.addStretch()
        
        self.generate_btn = QPushButton("✨ " + t("habit.stats.generate", "Generuj"))
        self.generate_btn.setMinimumHeight(50)
        self.generate_btn.setStyleSheet("font-size: 14px; font-weight: bold;")
        self.generate_btn.clicked.connect(self.generate_statistics)
        generate_layout.addWidget(self.generate_btn)
        
        generate_layout.addStretch()
        control_layout.addLayout(generate_layout, stretch=1)
        
        return control_group
    
    def on_chart_type_changed(self, index):
        """Obsługuje zmianę typu zestawienia"""
        self.current_chart_type = self.chart_type_combo.itemData(index)
    
    def generate_statistics(self):
        """Generuje statystyki na podstawie wybranych parametrów"""
        # Pobierz wybrane nawyki
        selected_items = self.habits_list.selectedItems()
        if not selected_items:
            return
        
        # Znajdź odpowiadające obiekty nawyków
        self.selected_habits = []
        for item in selected_items:
            item_text = item.text()
            # Pobierz nazwę nawyku (przed nawiasem)
            habit_name = item_text.split(" (")[0]
            for habit in self.habits:
                if habit['name'] == habit_name:
                    self.selected_habits.append(habit)
                    break
        
        # Wyczyść poprzednią treść
        while self.content_layout.count():
            child = self.content_layout.takeAt(0)
            if child.widget():
                child.widget().deleteLater()
        
        # Generuj odpowiednie zestawienie
        if self.current_chart_type == "sum_table":
            self.generate_sum_table()
        elif self.current_chart_type == "avg_table":
            self.generate_avg_table()
        elif self.current_chart_type == "correlation":
            self.generate_correlation_analysis()
        elif self.current_chart_type == "line_chart":
            self.generate_line_chart()
        elif self.current_chart_type == "bar_chart":
            self.generate_bar_chart()
        elif self.current_chart_type == "detailed_table":
            self.generate_detailed_table()
    
    def generate_sum_table(self):
        """Generuje tabelę sum"""
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels([
            t("habit.stats.habit_name", "Nazwa nawyku"),
            t("habit.stats.total_sum", "Suma"),
            t("habit.stats.unit", "Jednostka")
        ])
        table.setRowCount(len(self.selected_habits))
        
        for row, habit in enumerate(self.selected_habits):
            # Nazwa nawyku
            name_item = QTableWidgetItem(habit['name'])
            table.setItem(row, 0, name_item)
            
            # Oblicz sumę
            total = self.calculate_habit_sum(habit)
            habit_type = habit.get('type', '')
            
            # Formatuj wartość i jednostkę w zależności od typu
            if habit_type == "checkbox":
                sum_text = f"{int(total)}"
                unit_text = t("habit.stats.days_completed", "dni wykonane")
            elif habit_type == "counter":
                sum_text = f"{total:.0f}"
                unit_text = t("habit.stats.total_count", "suma")
            elif habit_type == "duration":
                # Konwertuj minuty na godziny i minuty
                hours = int(total // 60)
                minutes = int(total % 60)
                sum_text = f"{hours}:{minutes:02d}"
                unit_text = t("habit.stats.hours_minutes", "godz:min")
            elif habit_type == "time":
                sum_text = f"{int(total)}"
                unit_text = t("habit.stats.days_recorded", "dni zapisane")
            elif habit_type == "scale":
                sum_text = f"{total:.1f}"
                unit_text = t("habit.stats.total_points", "suma punktów")
            elif habit_type == "text":
                sum_text = f"{int(total)}"
                unit_text = t("habit.stats.days_with_notes", "dni z notatkami")
            else:
                sum_text = f"{total:.2f}"
                unit_text = ""
            
            sum_item = QTableWidgetItem(sum_text)
            unit_item = QTableWidgetItem(unit_text)
            table.setItem(row, 1, sum_item)
            table.setItem(row, 2, unit_item)
        
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.content_layout.addWidget(table)
    
    def generate_avg_table(self):
        """Generuje tabelę średnich"""
        table = QTableWidget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels([
            t("habit.stats.habit_name", "Nazwa nawyku"),
            t("habit.stats.average", "Średnia"),
            t("habit.stats.unit", "Jednostka")
        ])
        table.setRowCount(len(self.selected_habits))
        
        for row, habit in enumerate(self.selected_habits):
            name_item = QTableWidgetItem(habit['name'])
            table.setItem(row, 0, name_item)
            
            avg = self.calculate_habit_average(habit)
            habit_type = habit.get('type', '')
            
            # Formatuj wartość i jednostkę w zależności od typu
            if habit_type == "checkbox":
                avg_text = f"{avg:.1f}%"
                unit_text = t("habit.stats.completion_rate", "współczynnik wykonania")
            elif habit_type == "counter":
                avg_text = f"{avg:.2f}"
                unit_text = t("habit.stats.per_day_active", "śr. na dzień (aktywne)")
            elif habit_type == "duration":
                # Średni czas w minutach - konwertuj na godziny
                hours = avg / 60
                avg_text = f"{hours:.1f}"
                unit_text = t("habit.stats.hours_per_day", "godz/dzień")
            elif habit_type == "time":
                avg_text = f"{avg:.1f}%"
                unit_text = t("habit.stats.days_recorded_pct", "% dni z zapisem")
            elif habit_type == "scale":
                avg_text = f"{avg:.2f}"
                unit_text = t("habit.stats.avg_rating", "średnia ocena")
            elif habit_type == "text":
                avg_text = f"{avg:.1f}%"
                unit_text = t("habit.stats.days_with_notes_pct", "% dni z notatkami")
            else:
                avg_text = f"{avg:.2f}"
                unit_text = ""
            
            avg_item = QTableWidgetItem(avg_text)
            unit_item = QTableWidgetItem(unit_text)
            table.setItem(row, 1, avg_item)
            table.setItem(row, 2, unit_item)
        
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        self.content_layout.addWidget(table)
    
    def generate_correlation_analysis(self):
        """Generuje analizę korelacji między wybranymi nawykami"""
        if len(self.selected_habits) < 2:
            label = QLabel(t("habit.stats.select_min_2", "Wybierz przynajmniej 2 nawyki do analizy korelacji"))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 14px; color: orange; padding: 50px;")
            self.content_layout.addWidget(label)
            return
        
        if not SCIPY_AVAILABLE:
            # Wyświetl informację o brakującej bibliotece
            info_label = QLabel(
                t("habit.stats.scipy_required", 
                  "Analiza korelacji wymaga zainstalowania bibliotek scipy i numpy.\n\n"
                  "Zainstaluj używając: pip install scipy numpy")
            )
            info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            info_label.setStyleSheet("font-size: 14px; color: orange; padding: 50px;")
            self.content_layout.addWidget(info_label)
            
            # Pokaż prostą tabelę bez współczynników korelacji
            self.generate_simple_comparison_table()
            return
        
        # Pobierz dane dla wszystkich wybranych nawyków
        start_date, end_date = self.get_date_range()
        habit_data = {}
        
        for habit in self.selected_habits:
            records = self.get_habit_records(habit, start_date, end_date)
            dates, values = self.get_habit_timeline_data(habit)
            habit_data[habit['name']] = values
        
        # Sprawdź czy mamy dane
        if not habit_data:
            label = QLabel(t("habit.stats.no_data", "Brak danych dla wybranego zakresu"))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 14px; color: gray; padding: 50px;")
            self.content_layout.addWidget(label)
            return
        
        # Oblicz macierz korelacji
        habit_names = list(habit_data.keys())
        n_habits = len(habit_names)
        
        # Utwórz tabelę korelacji
        correlation_table = QTableWidget()
        correlation_table.setColumnCount(n_habits + 1)
        correlation_table.setRowCount(n_habits)
        
        headers = ["Nawyk"] + habit_names
        correlation_table.setHorizontalHeaderLabels(headers)
        
        for i, habit1 in enumerate(habit_names):
            # Pierwsza kolumna - nazwa nawyku
            name_item = QTableWidgetItem(habit1)
            name_item.setFont(QFont("Arial", 10, QFont.Weight.Bold))
            correlation_table.setItem(i, 0, name_item)
            
            for j, habit2 in enumerate(habit_names):
                if len(habit_data[habit1]) > 1 and len(habit_data[habit2]) > 1:
                    try:
                        # Oblicz współczynnik korelacji Pearsona
                        correlation, p_value = stats.pearsonr(
                            habit_data[habit1], 
                            habit_data[habit2]
                        )
                        
                        # Formatuj wynik
                        corr_text = f"{correlation:.3f}"
                        if p_value < 0.05:
                            corr_text += " *"  # Znacząca statystycznie
                        
                        corr_item = QTableWidgetItem(corr_text)
                        
                        # Koloruj komórki według siły korelacji
                        if i != j:  # Nie koloruj przekątnej
                            abs_corr = abs(correlation)
                            if abs_corr > 0.7:
                                # Silna korelacja - ciemnozielony/czerwony
                                color = QColor(34, 139, 34) if correlation > 0 else QColor(220, 20, 60)
                            elif abs_corr > 0.4:
                                # Umiarkowana korelacja - jasnozielony/pomarańczowy
                                color = QColor(60, 179, 113) if correlation > 0 else QColor(255, 140, 0)
                            elif abs_corr > 0.2:
                                # Słaba korelacja - bladozielony/bladoczerwony
                                color = QColor(144, 238, 144) if correlation > 0 else QColor(255, 160, 122)
                            else:
                                # Bardzo słaba - szary
                                color = QColor(200, 200, 200)
                            
                            corr_item.setBackground(QBrush(color))
                            corr_item.setForeground(QBrush(QColor(255, 255, 255) if abs_corr > 0.4 else QColor(0, 0, 0)))
                        
                        corr_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        correlation_table.setItem(i, j + 1, corr_item)
                        
                    except Exception as e:
                        logger.error(f"Error calculating correlation: {e}")
                        error_item = QTableWidgetItem("N/A")
                        error_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                        correlation_table.setItem(i, j + 1, error_item)
                else:
                    na_item = QTableWidgetItem("N/A")
                    na_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
                    correlation_table.setItem(i, j + 1, na_item)
        
        correlation_table.horizontalHeader().setStretchLastSection(True)
        correlation_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        # Dodaj tytuł i legendę
        title_label = QLabel(t("habit.stats.correlation_matrix", "Macierz korelacji nawyków"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(title_label)
        
        self.content_layout.addWidget(correlation_table)
        
        # Legenda
        legend_label = QLabel(
            t("habit.stats.correlation_legend",
              "Legenda:\n"
              "• Wartości od -1 do 1 (im bliżej 1 lub -1, tym silniejsza korelacja)\n"
              "• Wartość > 0: korelacja dodatnia (nawyki rosną razem)\n"
              "• Wartość < 0: korelacja ujemna (jeden nawyk rośnie gdy drugi maleje)\n"
              "• * oznacza istotność statystyczną (p < 0.05)\n"
              "• Kolory: zielony = dodatnia, czerwony = ujemna, szary = bardzo słaba")
        )
        legend_label.setStyleSheet("font-size: 11px; color: gray; padding: 10px; margin: 10px;")
        legend_label.setWordWrap(True)
        self.content_layout.addWidget(legend_label)
    
    def generate_simple_comparison_table(self):
        """Generuje prostą tabelę porównawczą gdy scipy nie jest dostępne"""
        table = QTableWidget()
        table.setColumnCount(len(self.selected_habits) + 1)
        table.setRowCount(3)  # Suma, Średnia, Liczba dni
        
        headers = ["Metryka"] + [h['name'] for h in self.selected_habits]
        table.setHorizontalHeaderLabels(headers)
        table.setVerticalHeaderLabels(["Suma", "Średnia", "Liczba dni z danymi"])
        
        for col, habit in enumerate(self.selected_habits):
            total = self.calculate_habit_sum(habit)
            avg = self.calculate_habit_average(habit)
            start_date, end_date = self.get_date_range()
            records = self.get_habit_records(habit, start_date, end_date)
            days_count = len([v for v in records.values() if v and v.strip()])
            
            table.setItem(0, col + 1, QTableWidgetItem(f"{total:.2f}"))
            table.setItem(1, col + 1, QTableWidgetItem(f"{avg:.2f}"))
            table.setItem(2, col + 1, QTableWidgetItem(str(days_count)))
        
        table.horizontalHeader().setStretchLastSection(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        
        title_label = QLabel(t("habit.stats.comparison_table", "Tabela porównawcza nawyków"))
        title_label.setStyleSheet("font-size: 16px; font-weight: bold; padding: 10px;")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.content_layout.addWidget(title_label)
        
        self.content_layout.addWidget(table)
    
    def generate_line_chart(self):
        """Generuje wykres liniowy"""
        if not MATPLOTLIB_AVAILABLE:
            label = QLabel(t("habit.stats.matplotlib_required", "Wykresy wymagają zainstalowania biblioteki matplotlib"))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 14px; color: orange; padding: 50px;")
            self.content_layout.addWidget(label)
            return
        
        fig = Figure(figsize=(8, 5))
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(360)
        ax = fig.add_subplot(111)

        has_series = False
        for habit in self.selected_habits:
            dates, values = self.get_habit_timeline_data(habit)
            if not dates:
                continue

            if all(value == 0 for value in values):
                # Jeśli wszystkie wartości są zerowe, spróbuj wykazać brak danych
                continue

            ax.plot(dates, values, marker='o', label=habit['name'])
            has_series = True

        if not has_series:
            label = QLabel(t("habit.stats.no_chart_data", "Brak danych do narysowania wykresu liniowego w wybranym okresie."))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 14px; color: gray; padding: 40px;")
            self.content_layout.addWidget(label)
            return

        ax.set_xlabel(t("habit.stats.date", "Data"))
        ax.set_ylabel(t("habit.stats.value", "Wartość"))
        ax.set_title(t("habit.stats.timeline", "Wykres czasowy nawyków"))
        ax.legend()
        ax.grid(True, alpha=0.3)

        # Formatowanie osi X z datami
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d"))
        fig.autofmt_xdate(rotation=30)
        fig.tight_layout()

        canvas.draw()
        self.content_layout.addWidget(canvas)
    
    def generate_bar_chart(self):
        """Generuje wykres słupkowy"""
        if not MATPLOTLIB_AVAILABLE:
            label = QLabel(t("habit.stats.matplotlib_required", "Wykresy wymagają zainstalowania biblioteki matplotlib"))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 14px; color: orange; padding: 50px;")
            self.content_layout.addWidget(label)
            return
        
        habit_names = [h['name'] for h in self.selected_habits]
        values = [self.calculate_habit_sum(h) for h in self.selected_habits]

        if not any(value != 0 for value in values):
            label = QLabel(t("habit.stats.no_bar_data", "Brak wyników do porównania w wybranym okresie."))
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setStyleSheet("font-size: 14px; color: gray; padding: 40px;")
            self.content_layout.addWidget(label)
            return

        fig = Figure(figsize=(8, 5))
        canvas = FigureCanvas(fig)
        canvas.setMinimumHeight(340)
        ax = fig.add_subplot(111)

        ax.bar(habit_names, values, color='skyblue')
        ax.set_xlabel(t("habit.stats.habit_name", "Nazwa nawyku"))
        ax.set_ylabel(t("habit.stats.total_sum", "Suma"))
        ax.set_title(t("habit.stats.comparison", "Porównanie nawyków"))
        ax.grid(True, alpha=0.3, axis='y')
        fig.tight_layout()

        canvas.draw()
        self.content_layout.addWidget(canvas)
    
    def generate_detailed_table(self):
        """Generuje szczegółową tabelę z wszystkimi danymi"""
        # Placeholder - tutaj można dodać bardziej szczegółowe dane
        label = QLabel(t("habit.stats.detailed_coming_soon", "Szczegółowa tabela - funkcja w przygotowaniu"))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setStyleSheet("font-size: 16px; padding: 50px;")
        self.content_layout.addWidget(label)
    
    def get_date_range(self):
        """Pobiera zakres dat na podstawie wybranego zakresu"""
        from datetime import timedelta
        from calendar import monthrange
        
        today = date.today()
        range_type = self.date_range_combo.currentData()
        
        if range_type == "current_month":
            # Pierwszy i ostatni dzień bieżącego miesiąca
            start_date = date(today.year, today.month, 1)
            days_in_month = monthrange(today.year, today.month)[1]
            end_date = date(today.year, today.month, days_in_month)
        elif range_type == "last_30_days":
            end_date = today
            start_date = today - timedelta(days=29)
        elif range_type == "last_90_days":
            end_date = today
            start_date = today - timedelta(days=89)
        elif range_type == "current_year":
            start_date = date(today.year, 1, 1)
            end_date = date(today.year, 12, 31)
        else:
            # Domyślnie bieżący miesiąc
            start_date = date(today.year, today.month, 1)
            days_in_month = monthrange(today.year, today.month)[1]
            end_date = date(today.year, today.month, days_in_month)
        
        return start_date, end_date
    
    def get_habit_records(self, habit: Dict[str, Any], start_date: date, end_date: date) -> Dict[str, str]:
        """Pobiera wszystkie rekordy nawyku dla zakresu dat"""
        if not self.db_manager:
            return {}
        
        all_records = {}
        current = start_date
        from datetime import timedelta
        
        # Pobierz rekordy miesiąc po miesiącu (optymalizacja)
        while current <= end_date:
            month_records = self.db_manager.get_habit_records_for_month(
                habit['id'], current.year, current.month
            )
            all_records.update(month_records)
            
            # Przejdź do następnego miesiąca
            if current.month == 12:
                current = date(current.year + 1, 1, 1)
            else:
                current = date(current.year, current.month + 1, 1)
        
        # Filtruj tylko dla wybranego zakresu dat
        filtered_records = {}
        current = start_date
        from datetime import timedelta
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            if date_str in all_records:
                filtered_records[date_str] = all_records[date_str]
            current += timedelta(days=1)
        
        return filtered_records
    
    def calculate_habit_sum(self, habit: Dict[str, Any]) -> float:
        """Oblicza sumę wartości dla nawyku - uwzględnia typ nawyku"""
        habit_type = habit.get('type', '')
        start_date, end_date = self.get_date_range()
        records = self.get_habit_records(habit, start_date, end_date)
        
        if not records:
            return 0.0
        
        total = 0.0
        
        if habit_type == "checkbox":
            # Checkbox: zliczamy dni z wartością "1" (wykonane)
            total = sum(1 for val in records.values() if val == "1")
        
        elif habit_type == "counter":
            # Counter: sumujemy wszystkie wartości liczbowe
            for val in records.values():
                try:
                    total += float(val) if val else 0.0
                except ValueError:
                    continue
        
        elif habit_type == "duration":
            # Duration: sumujemy czas w minutach (format: "HH:MM")
            for val in records.values():
                if val and ':' in val:
                    try:
                        parts = val.split(':')
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        total += hours * 60 + minutes  # Suma w minutach
                    except (ValueError, IndexError):
                        continue
        
        elif habit_type == "time":
            # Time: dla czasu zliczamy liczbę dni z zapisaną godziną
            total = sum(1 for val in records.values() if val and val.strip())
        
        elif habit_type == "scale":
            # Scale: sumujemy wartości liczbowe (np. 1-10)
            for val in records.values():
                try:
                    total += float(val) if val else 0.0
                except ValueError:
                    continue
        
        elif habit_type == "text":
            # Text: zliczamy dni z notatkami
            total = sum(1 for val in records.values() if val and val.strip())
        
        return total
    
    def calculate_habit_average(self, habit: Dict[str, Any]) -> float:
        """Oblicza średnią wartość dla nawyku - uwzględnia typ nawyku"""
        habit_type = habit.get('type', '')
        start_date, end_date = self.get_date_range()
        records = self.get_habit_records(habit, start_date, end_date)
        
        if not records:
            return 0.0
        
        # Oblicz liczbę dni w zakresie
        from datetime import timedelta
        total_days = (end_date - start_date).days + 1
        
        if habit_type == "checkbox":
            # Checkbox: procent dni wykonanych
            completed = sum(1 for val in records.values() if val == "1")
            return (completed / total_days * 100) if total_days > 0 else 0.0
        
        elif habit_type == "counter":
            # Counter: średnia liczba na dzień (tylko dni z wartością)
            values = [float(val) for val in records.values() if val and val != "0"]
            return sum(values) / len(values) if values else 0.0
        
        elif habit_type == "duration":
            # Duration: średni czas w minutach na dzień
            total_minutes = 0
            count = 0
            for val in records.values():
                if val and ':' in val:
                    try:
                        parts = val.split(':')
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        total_minutes += hours * 60 + minutes
                        count += 1
                    except (ValueError, IndexError):
                        continue
            return (total_minutes / count) if count > 0 else 0.0
        
        elif habit_type == "time":
            # Time: procent dni z zapisaną godziną
            filled_days = sum(1 for val in records.values() if val and val.strip())
            return (filled_days / total_days * 100) if total_days > 0 else 0.0
        
        elif habit_type == "scale":
            # Scale: średnia ocena
            values = [float(val) for val in records.values() if val]
            return sum(values) / len(values) if values else 0.0
        
        elif habit_type == "text":
            # Text: procent dni z notatkami
            filled_days = sum(1 for val in records.values() if val and val.strip())
            return (filled_days / total_days * 100) if total_days > 0 else 0.0
        
        return 0.0
    
    def get_habit_timeline_data(self, habit: Dict[str, Any]):
        """Pobiera dane czasowe dla nawyku do wykresu"""
        habit_type = habit.get('type', '')
        start_date, end_date = self.get_date_range()
        records = self.get_habit_records(habit, start_date, end_date)
        
        dates = []
        values = []
        
        from datetime import timedelta
        current = start_date
        while current <= end_date:
            date_str = current.strftime("%Y-%m-%d")
            val_str = records.get(date_str, "")
            
            dates.append(current)
            
            # Konwertuj wartość zgodnie z typem
            if habit_type == "checkbox":
                values.append(1 if val_str == "1" else 0)
            
            elif habit_type == "counter":
                try:
                    values.append(float(val_str) if val_str else 0.0)
                except ValueError:
                    values.append(0.0)
            
            elif habit_type == "duration":
                # Duration: konwertuj na minuty
                if val_str and ':' in val_str:
                    try:
                        parts = val_str.split(':')
                        hours = int(parts[0])
                        minutes = int(parts[1])
                        values.append(hours * 60 + minutes)
                    except (ValueError, IndexError):
                        values.append(0.0)
                else:
                    values.append(0.0)
            
            elif habit_type == "time":
                # Time: 1 jeśli zapisano, 0 jeśli nie
                values.append(1 if val_str and val_str.strip() else 0)
            
            elif habit_type == "scale":
                try:
                    values.append(float(val_str) if val_str else 0.0)
                except ValueError:
                    values.append(0.0)
            
            elif habit_type == "text":
                # Text: długość notatki jako wartość
                values.append(len(val_str) if val_str else 0)
            
            else:
                values.append(0.0)
            
            current += timedelta(days=1)
        
        return dates, values
    
    def print_statistics(self):
        """Drukuje wygenerowane statystyki"""
        printer = QPrinter(QPrinter.PrinterMode.HighResolution)
        dialog = QPrintDialog(printer, self)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            painter = QPainter(printer)
            # Renderuj zawartość content_widget
            self.content_widget.render(painter)
            painter.end()
    
    def apply_theme(self):
        """Aplikuje aktualny motyw do okna"""
        if not self.theme_manager:
            return

        colors = self.theme_manager.get_current_colors()

        bg_main = colors.get("bg_main", "#FFFFFF")
        bg_secondary = colors.get("bg_secondary", "#F5F5F5")
        text_primary = colors.get("text_primary", "#000000")
        text_secondary = colors.get("text_secondary", "#666666")
        accent_primary = colors.get("accent_primary", "#2196F3")
        accent_hover = colors.get("accent_hover", "#1976D2")
        border_light = colors.get("border_light", "#CCCCCC")
        disabled_bg = colors.get("disabled_bg", "#cccccc")
        disabled_text = colors.get("disabled_text", "#666666")

        self.setStyleSheet(f"""
            QDialog {{
                background-color: {bg_main};
                color: {text_primary};
            }}

            QGroupBox {{
                background-color: {bg_secondary};
                color: {text_primary};
                border: 2px solid {border_light};
                border-radius: 6px;
                margin-top: 10px;
                padding: 15px;
                font-weight: bold;
            }}

            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}

            QPushButton {{
                background-color: {accent_primary};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}

            QPushButton:hover {{
                background-color: {accent_hover};
            }}

            QPushButton:pressed {{
                background-color: {colors.get('accent_pressed', '#0D47A1')};
            }}

            QPushButton:disabled {{
                background-color: {disabled_bg};
                color: {disabled_text};
            }}

            QListWidget, QTableWidget, QComboBox {{
                background-color: {bg_main};
                color: {text_primary};
                border: 1px solid {border_light};
                border-radius: 4px;
                padding: 4px;
            }}

            QListWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {border_light};
            }}

            QListWidget::item:selected {{
                background-color: {accent_primary};
                color: white;
            }}

            QTableWidget::item {{
                padding: 4px;
                border-bottom: 1px solid {border_light};
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

            QScrollArea {{
                background-color: {bg_main};
                border: 1px solid {border_light};
                border-radius: 4px;
            }}

            QLabel {{
                color: {text_primary};
            }}

            QComboBox:focus {{
                border: 2px solid {accent_primary};
            }}

            QComboBox::drop-down {{
                border: none;
            }}

            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 6px solid {text_primary};
                margin-right: 5px;
            }}
        """)
