from __future__ import annotations

from typing import Optional, Tuple
from datetime import date

from PyQt6.QtCore import Qt, QDate, QLocale
from PyQt6.QtGui import QDoubleValidator
from PyQt6.QtWidgets import (
	QDialog,
	QDialogButtonBox,
	QHBoxLayout,
	QLabel,
	QLineEdit,
	QPushButton,
	QVBoxLayout,
	QWidget,
	QCalendarWidget,
	QTextEdit,
)

from ..utils import get_theme_manager
from ..utils.i18n_manager import t, get_i18n


class CurrencyInputDialog(QDialog):
	"""Dialog used to capture or edit currency values."""

	def __init__(
		self,
		parent: Optional[QWidget] = None,
		initial_amount: float = 0.0,
		step: float = 1.0,
	):
		super().__init__(parent)
		self.setModal(True)
		self.setObjectName("CurrencyInputDialog")
		self._theme_manager = get_theme_manager()
		self._step = step if step > 0 else 1.0
		self._amount = float(initial_amount if initial_amount is not None else 0.0)

		self.setWindowTitle(t("tasks.currency_dialog.title", "Amount"))
		self._build_ui()
		self._apply_theme()
		self._update_amount_text(self._amount)

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)
		layout.setContentsMargins(16, 16, 16, 16)
		layout.setSpacing(12)

		label = QLabel(t("tasks.currency_dialog.prompt", "Enter amount"))
		layout.addWidget(label)

		self._amount_input = QLineEdit(self)
		self._amount_input.setAlignment(Qt.AlignmentFlag.AlignRight)
		validator = QDoubleValidator(-1e12, 1e12, 2, self._amount_input)
		validator.setNotation(QDoubleValidator.Notation.StandardNotation)
		self._amount_input.setValidator(validator)
		self._amount_input.textEdited.connect(self._on_text_edited)

		adjust_layout = QHBoxLayout()
		adjust_layout.setSpacing(8)
		adjust_layout.addWidget(self._amount_input, 1)

		self._minus_button = QPushButton(
			t("tasks.currency_dialog.decrease", "-")
		)
		self._minus_button.clicked.connect(lambda: self._adjust_amount(-self._step))
		adjust_layout.addWidget(self._minus_button)

		self._plus_button = QPushButton(
			t("tasks.currency_dialog.increase", "+")
		)
		self._plus_button.clicked.connect(lambda: self._adjust_amount(self._step))
		adjust_layout.addWidget(self._plus_button)

		layout.addLayout(adjust_layout)

		self._button_box = QDialogButtonBox(self)
		self._button_box.setStandardButtons(
			QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
		)
		self._button_box.accepted.connect(self._on_accept)
		self._button_box.rejected.connect(self.reject)

		ok_button = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
		if ok_button:
			ok_button.setText(t("tasks.currency_dialog.ok", "OK"))
			ok_button.setDefault(True)
			ok_button.setAutoDefault(True)

		cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
		if cancel_button:
			cancel_button.setText(t("tasks.currency_dialog.cancel", "Cancel"))

		layout.addWidget(self._button_box)

	def _apply_theme(self) -> None:
		# Pobierz kolory z aktualnego schematu
		if self._theme_manager:
			colors = self._theme_manager.get_current_colors()
			panel_bg = colors.get("bg_main", "#FFFFFF")
			text_color = colors.get("text_primary", "#1A1A1A")
			border_color = colors.get("border_light", "#CCCCCC")
			primary_color = colors.get("accent_primary", "#2196F3")
		else:
			# Fallback jeśli brak theme managera
			panel_bg = "#ffffff"
			text_color = "#212529"
			border_color = "#ced4da"
			primary_color = "#0d6efd"

		self.setStyleSheet(
			f"""
			QDialog#CurrencyInputDialog {{
				background-color: {panel_bg};
				color: {text_color};
			}}
			QLabel {{
				color: {text_color};
			}}
			QLineEdit {{
				border: 1px solid {border_color};
				border-radius: 6px;
				padding: 6px 8px;
				color: {text_color};
				background-color: {panel_bg};
			}}
			QLineEdit:focus {{
				border: 2px solid {primary_color};
			}}
			QPushButton {{
				min-width: 36px;
				padding: 6px 10px;
				border-radius: 6px;
			}}
			QPushButton#PrimaryAction {{
				background-color: {primary_color};
				color: #ffffff;
			}}
			"""
		)

		ok_button = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
		if ok_button:
			ok_button.setObjectName("PrimaryAction")

	def _on_text_edited(self, text: str) -> None:
		value = self._safe_to_float(text)
		if value is not None:
			self._amount = value

	def _adjust_amount(self, delta: float) -> None:
		value = self._safe_to_float(self._amount_input.text())
		if value is None:
			value = self._amount
		value += delta
		self._amount = round(value, 2)
		self._update_amount_text(self._amount)

	def _on_accept(self) -> None:
		value = self._safe_to_float(self._amount_input.text())
		if value is None:
			self._amount_input.setFocus(Qt.FocusReason.OtherFocusReason)
			return
		self._amount = round(value, 2)
		self.accept()

	def _update_amount_text(self, value: float) -> None:
		self._amount_input.blockSignals(True)
		self._amount_input.setText(f"{value:.2f}")
		self._amount_input.blockSignals(False)
		self._amount_input.setCursorPosition(len(self._amount_input.text()))

	def _safe_to_float(self, value: str) -> Optional[float]:
		if not value:
			return None
		try:
			return float(value.replace(",", "."))
		except ValueError:
			return None

	def get_amount(self) -> float:
		return self._amount

	@classmethod
	def prompt(
		cls,
		parent: Optional[QWidget] = None,
		initial_amount: float = 0.0,
		step: float = 1.0,
	) -> Tuple[bool, float]:
		dialog = cls(parent=parent, initial_amount=initial_amount, step=step)
		result = dialog.exec()
		accepted = result == QDialog.DialogCode.Accepted
		return accepted, dialog.get_amount() if accepted else initial_amount


class DurationInputDialog(QDialog):
	"""Dialog do wprowadzania czasu trwania (w minutach)."""

	def __init__(
		self,
		parent: Optional[QWidget] = None,
		initial_minutes: int = 0,
		title: str = None,
	):
		super().__init__(parent)
		self.setModal(True)
		self.setObjectName("DurationInputDialog")
		self._theme_manager = get_theme_manager()
		self._minutes = max(0, initial_minutes)

		window_title = title if title else t("tasks.duration_dialog.title", "Ustaw czas trwania")
		self.setWindowTitle(window_title)
		self.setMinimumWidth(400)
		self._build_ui()
		self._apply_theme()

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)
		layout.setContentsMargins(20, 20, 20, 20)
		layout.setSpacing(16)

		# Etykieta
		label = QLabel(t("tasks.duration_dialog.prompt", "Wprowadź czas trwania (w minutach):"))
		label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		layout.addWidget(label)

		# Kontener na przyciski i pole wprowadzania
		duration_layout = QHBoxLayout()
		duration_layout.setSpacing(10)

		# Przycisk minus (dekrementacja)
		self._minus_btn = QPushButton("−")
		self._minus_btn.setObjectName("MinusButton")
		self._minus_btn.setMinimumSize(60, 80)
		self._minus_btn.setMaximumSize(60, 80)
		self._minus_btn.clicked.connect(self._decrement)
		duration_layout.addWidget(self._minus_btn)

		# Pole z dużymi cyframi (edytowalne)
		self._duration_input = QLineEdit()
		self._duration_input.setObjectName("DurationInput")
		self._duration_input.setText(str(self._minutes))
		self._duration_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
		self._duration_input.setMinimumHeight(80)
		self._duration_input.textChanged.connect(self._on_text_changed)
		duration_layout.addWidget(self._duration_input, 1)

		# Przycisk plus (inkrementacja)
		self._plus_btn = QPushButton("+")
		self._plus_btn.setObjectName("PlusButton")
		self._plus_btn.setMinimumSize(60, 80)
		self._plus_btn.setMaximumSize(60, 80)
		self._plus_btn.clicked.connect(self._increment)
		duration_layout.addWidget(self._plus_btn)

		layout.addLayout(duration_layout)

		# Informacja o formacie
		info_label = QLabel(t("tasks.duration_dialog.info", "Czas w minutach (0 = brak)"))
		info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
		info_label.setStyleSheet("font-size: 11px; color: gray;")
		layout.addWidget(info_label)

		# Przyciski OK i Anuluj
		self._button_box = QDialogButtonBox(
			QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
		)
		self._button_box.accepted.connect(self.accept)
		self._button_box.rejected.connect(self.reject)
		
		# Ustawienie tekstów przycisków
		ok_button = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
		cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
		if ok_button:
			ok_button.setText(t("tasks.duration_dialog.ok", "OK"))
		if cancel_button:
			cancel_button.setText(t("tasks.duration_dialog.cancel", "Anuluj"))
		
		layout.addWidget(self._button_box)

	def _increment(self) -> None:
		"""Zwiększ czas o 1 minutę."""
		self._minutes += 1
		self._duration_input.setText(str(self._minutes))

	def _decrement(self) -> None:
		"""Zmniejsz czas o 1 minutę (minimum 0)."""
		if self._minutes > 0:
			self._minutes -= 1
			self._duration_input.setText(str(self._minutes))

	def _on_text_changed(self, text: str) -> None:
		"""Obsługa ręcznej zmiany tekstu."""
		if not text:
			self._minutes = 0
			return
		
		try:
			value = int(text)
			if value >= 0:
				self._minutes = value
			else:
				# Nie zezwalaj na wartości ujemne
				self._duration_input.setText(str(self._minutes))
		except ValueError:
			# Przywróć poprzednią wartość jeśli wprowadzono nieprawidłowe dane
			self._duration_input.setText(str(self._minutes))

	def _apply_theme(self) -> None:
		"""Zastosuj style zgodne z aktualnym motywem."""
		if not self._theme_manager:
			return

		# Pobierz kolory z aktualnego schematu
		colors = self._theme_manager.get_current_colors()
		bg_main = colors.get("bg_main", "#FFFFFF")
		bg_secondary = colors.get("bg_secondary", "#F5F5F5")
		text_primary = colors.get("text_primary", "#1A1A1A")
		text_secondary = colors.get("text_secondary", "#666666")
		accent = colors.get("accent_primary", "#2196F3")
		accent_hover = colors.get("accent_hover", "#1976D2")
		accent_pressed = colors.get("accent_pressed", "#0D47A1")
		border = colors.get("border_light", "#CCCCCC")
		
		# Dodatkowe kolory dla przycisków (z fallbackiem)
		button_bg = colors.get("btn_add_bg", accent)
		button_hover = colors.get("btn_add_hover", accent_hover)
		input_bg = colors.get("table_row_bg", bg_secondary)

		self.setStyleSheet(f"""
			QDialog#DurationInputDialog {{
				background-color: {bg_main};
			}}
			
			QLabel {{
				color: {text_primary};
				font-size: 13px;
			}}
			
			QLineEdit#DurationInput {{
				background-color: {input_bg};
				color: {text_primary};
				border: 2px solid {border};
				border-radius: 8px;
				padding: 10px;
				font-size: 48px;
				font-weight: bold;
				font-family: 'Segoe UI', Arial, sans-serif;
			}}
			
			QLineEdit#DurationInput:focus {{
				border: 2px solid {accent};
			}}
			
			QPushButton#MinusButton,
			QPushButton#PlusButton {{
				background-color: {button_bg};
				color: white;
				border: 1px solid {border};
				border-radius: 8px;
				font-size: 32px;
				font-weight: bold;
			}}
			
			QPushButton#MinusButton:hover,
			QPushButton#PlusButton:hover {{
				background-color: {button_hover};
				border: 1px solid {accent};
			}}
			
			QPushButton#MinusButton:pressed,
			QPushButton#PlusButton:pressed {{
				background-color: {accent_pressed};
				color: white;
			}}
			
			QDialogButtonBox QPushButton {{
				background-color: {bg_secondary};
				color: {text_primary};
				border: 1px solid {border};
				border-radius: 4px;
				padding: 8px 16px;
				min-width: 80px;
			}}
			
			QDialogButtonBox QPushButton:hover {{
				background-color: {button_hover};
				border: 1px solid {accent};
			}}
			
			QDialogButtonBox QPushButton:pressed {{
				background-color: {accent_pressed};
				color: white;
			}}
		""")

	def get_minutes(self) -> int:
		"""Zwraca wprowadzony czas w minutach."""
		return self._minutes

	@classmethod
	def prompt(
		cls,
		parent: Optional[QWidget] = None,
		initial_minutes: int = 0,
		title: str = None,
	) -> Tuple[bool, int]:
		"""
		Wyświetl dialog i zwróć wynik.
		
		Returns:
			Tuple[bool, int]: (czy zaakceptowano, wprowadzone minuty)
		"""
		dialog = cls(parent=parent, initial_minutes=initial_minutes, title=title)
		result = dialog.exec()
		accepted = result == QDialog.DialogCode.Accepted
		return accepted, dialog.get_minutes() if accepted else initial_minutes


class DatePickerDialog(QDialog):
	"""Dialog z kalendarzem do wyboru daty."""

	def __init__(
		self,
		parent: Optional[QWidget] = None,
		initial_date: Optional[date] = None,
		title: str = None,
	):
		super().__init__(parent)
		self.setModal(True)
		self.setObjectName("DatePickerDialog")
		self._theme_manager = get_theme_manager()
		self._selected_date = initial_date if initial_date else date.today()

		window_title = title if title else t("tasks.date_dialog.title", "Wybierz datę")
		self.setWindowTitle(window_title)
		self._build_ui()
		self._apply_theme()

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)
		layout.setContentsMargins(16, 16, 16, 16)
		layout.setSpacing(12)

		# Etykieta
		label = QLabel(t("tasks.date_dialog.prompt", "Wybierz datę:"))
		layout.addWidget(label)

		# Widget kalendarza
		self._calendar = QCalendarWidget(self)
		self._calendar.setGridVisible(True)
		
		# Ustaw locale kalendarza na podstawie języka aplikacji
		i18n = get_i18n()
		current_lang = i18n.current_language if i18n else "pl"
		
		# Mapowanie kodów języków na QLocale
		locale_map = {
			"pl": QLocale(QLocale.Language.Polish, QLocale.Country.Poland),
			"en": QLocale(QLocale.Language.English, QLocale.Country.UnitedStates),
			"de": QLocale(QLocale.Language.German, QLocale.Country.Germany),
		}
		
		calendar_locale = locale_map.get(current_lang, QLocale(QLocale.Language.Polish))
		self._calendar.setLocale(calendar_locale)
		
		# Ustaw aktualnie wybraną datę
		qdate = QDate(self._selected_date.year, self._selected_date.month, self._selected_date.day)
		self._calendar.setSelectedDate(qdate)
		
		# Podłącz sygnał zmiany daty
		self._calendar.clicked.connect(self._on_date_clicked)
		
		layout.addWidget(self._calendar)

		# Przyciski
		self._button_box = QDialogButtonBox(self)
		self._button_box.setStandardButtons(
			QDialogButtonBox.StandardButton.Ok | 
			QDialogButtonBox.StandardButton.Cancel |
			QDialogButtonBox.StandardButton.Reset
		)
		self._button_box.accepted.connect(self.accept)
		self._button_box.rejected.connect(self.reject)
		
		# Przycisk Reset (wyczyść datę)
		reset_button = self._button_box.button(QDialogButtonBox.StandardButton.Reset)
		if reset_button:
			reset_button.setText(t("tasks.date_dialog.clear", "Wyczyść"))
			reset_button.clicked.connect(self._on_clear)

		ok_button = self._button_box.button(QDialogButtonBox.StandardButton.Ok)
		if ok_button:
			ok_button.setText(t("tasks.date_dialog.ok", "OK"))
			ok_button.setDefault(True)

		cancel_button = self._button_box.button(QDialogButtonBox.StandardButton.Cancel)
		if cancel_button:
			cancel_button.setText(t("tasks.date_dialog.cancel", "Anuluj"))

		layout.addWidget(self._button_box)

	def _apply_theme(self) -> None:
		"""Zastosuj stylizację zgodną z aktualnym motywem."""
		if not self._theme_manager:
			# Fallback na domyślne kolory jasne
			panel_bg = "#ffffff"
			text_color = "#212529"
			border_color = "#ced4da"
			primary_color = "#0d6efd"
			hover_color = "#0b5ed7"
			calendar_bg = "#f8f9fa"
			calendar_header_bg = "#e9ecef"
			weekend_color = "#dc3545"
			selected_bg = "#0d6efd"
			today_bg = "#20c997"
		else:
			# Pobierz kolory z aktualnego schematu
			colors = self._theme_manager.get_current_colors()
			panel_bg = colors.get("bg_main", "#FFFFFF")
			text_color = colors.get("text_primary", "#1A1A1A")
			border_color = colors.get("border_light", "#CCCCCC")
			primary_color = colors.get("accent_primary", "#2196F3")
			hover_color = colors.get("accent_hover", "#1976D2")
			calendar_bg = colors.get("bg_secondary", "#F5F5F5")
			calendar_header_bg = colors.get("table_header_bg", "#E9ECEF")
			weekend_color = colors.get("btn_delete_bg", "#DC3545")
			selected_bg = colors.get("table_selection", primary_color)
			today_bg = colors.get("btn_add_bg", "#20C997")

		self.setStyleSheet(
			f"""
			QDialog#DatePickerDialog {{
				background-color: {panel_bg};
				color: {text_color};
			}}
			QLabel {{
				color: {text_color};
				font-weight: bold;
				font-size: 13px;
			}}
			QCalendarWidget {{
				background-color: {calendar_bg};
				color: {text_color};
				border: 1px solid {border_color};
				border-radius: 6px;
			}}
			QCalendarWidget QWidget {{
				alternate-background-color: {calendar_bg};
			}}
			QCalendarWidget QToolButton {{
				color: {text_color};
				background-color: {panel_bg};
				border: 1px solid {border_color};
				border-radius: 4px;
				padding: 5px;
				margin: 2px;
				font-weight: bold;
			}}
			QCalendarWidget QToolButton:hover {{
				background-color: {primary_color};
				color: white;
				border-color: {primary_color};
			}}
			QCalendarWidget QToolButton:pressed {{
				background-color: {hover_color};
			}}
			QCalendarWidget QMenu {{
				background-color: {panel_bg};
				color: {text_color};
				border: 1px solid {border_color};
			}}
			QCalendarWidget QSpinBox {{
				background-color: {panel_bg};
				color: {text_color};
				border: 1px solid {border_color};
				border-radius: 4px;
				padding: 2px 5px;
			}}
			QCalendarWidget QSpinBox::up-button, 
			QCalendarWidget QSpinBox::down-button {{
				background-color: {panel_bg};
				border: 1px solid {border_color};
			}}
			QCalendarWidget QSpinBox::up-button:hover, 
			QCalendarWidget QSpinBox::down-button:hover {{
				background-color: {primary_color};
			}}
			QCalendarWidget QAbstractItemView {{
				background-color: {calendar_bg};
				color: {text_color};
				selection-background-color: {selected_bg};
				selection-color: white;
				border: none;
				outline: none;
			}}
			QCalendarWidget QAbstractItemView:enabled {{
				color: {text_color};
			}}
			/* Nagłówek kalendarza */
			QCalendarWidget QWidget#qt_calendar_navigationbar {{
				background-color: {calendar_header_bg};
				border-bottom: 1px solid {border_color};
			}}
			/* Przyciski dialogu */
			QPushButton {{
				padding: 6px 14px;
				border-radius: 6px;
				border: 1px solid {border_color};
				background-color: {panel_bg};
				color: {text_color};
				min-width: 70px;
			}}
			QPushButton:hover {{
				background-color: {primary_color};
				color: white;
				border-color: {primary_color};
			}}
			QPushButton:pressed {{
				background-color: {hover_color};
			}}
			QPushButton:default {{
				background-color: {primary_color};
				color: white;
				border-color: {primary_color};
				font-weight: bold;
			}}
			QPushButton:default:hover {{
				background-color: {hover_color};
			}}
			"""
		)

	def _on_date_clicked(self, qdate: QDate) -> None:
		"""Obsługa kliknięcia w datę w kalendarzu."""
		self._selected_date = date(qdate.year(), qdate.month(), qdate.day())

	def _on_clear(self) -> None:
		"""Obsługa kliknięcia przycisku Wyczyść."""
		self._selected_date = None
		self.accept()

	def get_date(self) -> Optional[date]:
		"""Zwróć wybraną datę."""
		return self._selected_date

	@classmethod
	def prompt(
		cls,
		parent: Optional[QWidget] = None,
		initial_date: Optional[date] = None,
		title: str = None,
	) -> Tuple[bool, Optional[date]]:
		"""
		Wyświetl dialog wyboru daty i zwróć wynik.
		
		Returns:
			Tuple[bool, Optional[date]]: (czy zaakceptowano, wybrana data lub None)
		"""
		dialog = cls(parent=parent, initial_date=initial_date, title=title)
		result = dialog.exec()
		accepted = result == QDialog.DialogCode.Accepted
		return accepted, dialog.get_date() if accepted else initial_date


class TextInputDialog(QDialog):
	"""Dialog do wprowadzania wartości tekstowych."""

	def __init__(
		self,
		parent: Optional[QWidget] = None,
		initial_text: str = "",
		title: str = None,
	):
		super().__init__(parent)
		self.setModal(True)
		self.setObjectName("TextInputDialog")
		self._theme_manager = get_theme_manager()
		self._text = initial_text

		dialog_title = title if title else t("tasks.text_dialog.title", "Wprowadź tekst")
		self.setWindowTitle(dialog_title)
		self._build_ui()
		self._apply_theme()

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)
		layout.setContentsMargins(16, 16, 16, 16)
		layout.setSpacing(12)

		# Etykieta
		label = QLabel(t("tasks.text_dialog.prompt", "Wprowadź wartość tekstową:"))
		label.setObjectName("TextInputLabel")
		layout.addWidget(label)

		# Pole tekstowe (QTextEdit zamiast QLineEdit - wieloliniowe z suwakiem)
		self._text_input = QTextEdit()
		self._text_input.setObjectName("TextInputField")
		self._text_input.setPlainText(self._text)
		self._text_input.setPlaceholderText(t("tasks.text_dialog.placeholder", "Wpisz tutaj..."))
		self._text_input.setMinimumWidth(400)
		self._text_input.setMinimumHeight(150)
		self._text_input.setMaximumHeight(300)
		layout.addWidget(self._text_input)

		# Przyciski
		button_layout = QHBoxLayout()
		button_layout.setSpacing(8)

		self._ok_button = QPushButton(t("tasks.text_dialog.ok", "OK"))
		self._ok_button.setObjectName("OkButton")
		self._ok_button.clicked.connect(self.accept)

		self._cancel_button = QPushButton(t("tasks.text_dialog.cancel", "Anuluj"))
		self._cancel_button.setObjectName("CancelButton")
		self._cancel_button.clicked.connect(self.reject)

		button_layout.addStretch()
		button_layout.addWidget(self._ok_button)
		button_layout.addWidget(self._cancel_button)

		layout.addLayout(button_layout)

	def _apply_theme(self) -> None:
		"""Zastosuj kolory z Theme Managera."""
		colors = self._theme_manager.get_current_colors()
		
		bg_main = colors.get('bg_main', '#1e1e1e')
		text_primary = colors.get('text_primary', '#e0e0e0')
		text_secondary = colors.get('text_secondary', '#b0b0b0')
		accent_primary = colors.get('accent_primary', '#0d7377')
		accent_hover = colors.get('accent_hover', '#14ffec')
		accent_pressed = colors.get('accent_pressed', '#0a5c5f')
		border_light = colors.get('border_light', '#3c3c3c')

		self.setStyleSheet(f"""
			QDialog {{
				background-color: {bg_main};
			}}
			QLabel#TextInputLabel {{
				color: {text_primary};
				font-size: 12px;
				font-weight: bold;
			}}
			QTextEdit#TextInputField {{
				background-color: {bg_main};
				color: {text_primary};
				border: 1px solid {border_light};
				border-radius: 4px;
				padding: 8px;
				font-size: 14px;
				font-family: 'Segoe UI', Arial, sans-serif;
			}}
			QTextEdit#TextInputField:focus {{
				border: 1px solid {accent_primary};
			}}
			/* Styl suwaka (scrollbar) */
			QTextEdit#TextInputField QScrollBar:vertical {{
				background-color: {bg_main};
				width: 12px;
				border: 1px solid {border_light};
				border-radius: 6px;
			}}
			QTextEdit#TextInputField QScrollBar::handle:vertical {{
				background-color: {accent_primary};
				border-radius: 5px;
				min-height: 20px;
			}}
			QTextEdit#TextInputField QScrollBar::handle:vertical:hover {{
				background-color: {accent_hover};
			}}
			QTextEdit#TextInputField QScrollBar::add-line:vertical,
			QTextEdit#TextInputField QScrollBar::sub-line:vertical {{
				height: 0px;
			}}
			QPushButton#OkButton {{
				background-color: {accent_primary};
				color: {text_primary};
				border: none;
				border-radius: 4px;
				padding: 8px 16px;
				font-weight: bold;
			}}
			QPushButton#OkButton:hover {{
				background-color: {accent_hover};
			}}
			QPushButton#OkButton:pressed {{
				background-color: {accent_pressed};
			}}
			QPushButton#CancelButton {{
				background-color: transparent;
				color: {text_secondary};
				border: 1px solid {border_light};
				border-radius: 4px;
				padding: 8px 16px;
			}}
			QPushButton#CancelButton:hover {{
				border-color: {accent_primary};
				color: {text_primary};
			}}
		""")

	def get_text(self) -> str:
		"""Zwróć wprowadzony tekst."""
		return self._text_input.toPlainText()

	@classmethod
	def prompt(
		cls,
		parent: Optional[QWidget] = None,
		initial_text: str = "",
		title: str = None,
	) -> Tuple[bool, str]:
		"""
		Wyświetl dialog wprowadzania tekstu i zwróć wynik.
		
		Returns:
			Tuple[bool, str]: (czy zaakceptowano, wprowadzony tekst)
		"""
		dialog = cls(parent=parent, initial_text=initial_text, title=title)
		result = dialog.exec()
		accepted = result == QDialog.DialogCode.Accepted
		return accepted, dialog.get_text() if accepted else initial_text


class TextInputDialog(QDialog):
	"""Prosty dialog do wprowadzania wartości tekstowych."""

	def __init__(
		self,
		parent: Optional[QWidget] = None,
		initial_text: str = "",
		title: str = None,
		column_name: str = None,
	):
		super().__init__(parent)
		self.setModal(True)
		self.setObjectName("TextInputDialog")
		self._theme_manager = get_theme_manager()
		self._text = initial_text or ""
		self._column_name = column_name

		if title:
			self.setWindowTitle(title)
		elif column_name:
			self.setWindowTitle(t("tasks.text_dialog.title_for", "Edit {column}").format(column=column_name))
		else:
			self.setWindowTitle(t("tasks.text_dialog.title", "Enter Text"))
		
		self._build_ui()
		self._apply_theme()

	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)
		layout.setContentsMargins(16, 16, 16, 16)
		layout.setSpacing(12)

		# Prompt label
		prompt = t("tasks.text_dialog.prompt", "Enter text value:")
		label = QLabel(prompt)
		label.setAlignment(Qt.AlignmentFlag.AlignLeft)
		layout.addWidget(label)

		# Text input field
		self._line_edit = QLineEdit(self._text)
		self._line_edit.setPlaceholderText(t("tasks.text_dialog.placeholder", "Type here..."))
		self._line_edit.selectAll()
		layout.addWidget(self._line_edit)

		# Buttons
		btn_layout = QHBoxLayout()
		btn_layout.setSpacing(8)
		btn_layout.addStretch()

		self._ok_btn = QPushButton(t("tasks.text_dialog.ok", "OK"))
		self._ok_btn.setMinimumWidth(80)
		self._ok_btn.clicked.connect(self.accept)
		btn_layout.addWidget(self._ok_btn)

		self._cancel_btn = QPushButton(t("tasks.text_dialog.cancel", "Cancel"))
		self._cancel_btn.setMinimumWidth(80)
		self._cancel_btn.clicked.connect(self.reject)
		btn_layout.addWidget(self._cancel_btn)

		layout.addLayout(btn_layout)

		# Set focus to input field
		self._line_edit.setFocus()

	def _apply_theme(self) -> None:
		colors = self._theme_manager.get_current_colors()

		bg_main = colors.get("bg_main", "#1e1e1e")
		text_primary = colors.get("text_primary", "#e0e0e0")
		accent = colors.get("accent_primary", "#0078d4")
		accent_hover = colors.get("accent_hover", "#1a86d9")
		border_light = colors.get("border_light", "#3c3c3c")

		self.setStyleSheet(f"""
			QDialog#TextInputDialog {{
				background-color: {bg_main};
			}}
			QLabel {{
				color: {text_primary};
				font-size: 13px;
			}}
			QLineEdit {{
				background-color: {bg_main};
				color: {text_primary};
				border: 1px solid {border_light};
				border-radius: 4px;
				padding: 8px;
				font-size: 14px;
			}}
			QLineEdit:focus {{
				border: 1px solid {accent};
			}}
			QPushButton {{
				background-color: {accent};
				color: white;
				border: none;
				border-radius: 4px;
				padding: 8px 16px;
				font-size: 13px;
			}}
			QPushButton:hover {{
				background-color: {accent_hover};
			}}
			QPushButton:pressed {{
				background-color: {accent};
			}}
		""")

	def get_text(self) -> str:
		"""Zwraca wprowadzony tekst."""
		return self._line_edit.text()

	@classmethod
	def prompt(
		cls,
		parent: Optional[QWidget] = None,
		initial_text: str = "",
		title: str = None,
		column_name: str = None,
	) -> Tuple[bool, str]:
		"""
		Wyświetl dialog wprowadzania tekstu i zwróć wynik.
		
		Returns:
			Tuple[bool, str]: (czy zaakceptowano, wprowadzony tekst)
		"""
		dialog = cls(parent=parent, initial_text=initial_text, title=title, column_name=column_name)
		result = dialog.exec()
		accepted = result == QDialog.DialogCode.Accepted
		return accepted, dialog.get_text() if accepted else initial_text


class TaskEditDialog(QDialog):
	"""Dialog do edycji treści zadania."""
	
	def __init__(
		self,
		parent: Optional[QWidget] = None,
		task_title: str = "",
	):
		super().__init__(parent)
		self.setModal(True)
		self.setObjectName("TaskEditDialog")
		self._theme_manager = get_theme_manager()
		self._task_title = task_title
		
		self.setWindowTitle(t("tasks.edit_dialog.title", "Edytuj zadanie"))
		self._build_ui()
		self._apply_theme()
	
	def _build_ui(self) -> None:
		layout = QVBoxLayout(self)
		layout.setContentsMargins(16, 16, 16, 16)
		layout.setSpacing(12)
		
		# Etykieta
		label = QLabel(t("tasks.edit_dialog.label", "Treść zadania:"))
		label.setObjectName("TaskEditLabel")
		layout.addWidget(label)
		
		# Pole tekstowe
		self._text_edit = QTextEdit()
		self._text_edit.setObjectName("TaskEditTextEdit")
		self._text_edit.setPlainText(self._task_title)
		self._text_edit.setMinimumWidth(500)
		self._text_edit.setMinimumHeight(150)
		self._text_edit.setMaximumHeight(300)
		self._text_edit.selectAll()  # Zaznacz cały tekst
		layout.addWidget(self._text_edit)
		
		# Przyciski
		button_box = QDialogButtonBox(
			QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
		)
		button_box.accepted.connect(self.accept)
		button_box.rejected.connect(self.reject)
		layout.addWidget(button_box)
		
		self.setLayout(layout)
	
	def _apply_theme(self) -> None:
		"""Zastosuj kolory z theme managera."""
		colors = self._theme_manager.get_current_colors()
		
		bg = colors.get("background", "#FFFFFF")
		fg = colors.get("text", "#000000")
		accent = colors.get("accent", "#2196F3")
		border = colors.get("border", "#CCCCCC")
		
		# Style dla dialogu
		self.setStyleSheet(f"""
			QDialog#TaskEditDialog {{
				background-color: {bg};
			}}
			QLabel#TaskEditLabel {{
				color: {fg};
				font-size: 13px;
				font-weight: bold;
			}}
			QTextEdit#TaskEditTextEdit {{
				background-color: {bg};
				color: {fg};
				border: 2px solid {border};
				border-radius: 4px;
				padding: 8px;
				font-size: 13px;
			}}
			QTextEdit#TaskEditTextEdit:focus {{
				border-color: {accent};
			}}
			QTextEdit#TaskEditTextEdit QScrollBar:vertical {{
				width: 12px;
				background: {bg};
				border-radius: 6px;
			}}
			QTextEdit#TaskEditTextEdit QScrollBar::handle:vertical {{
				background: {accent};
				border-radius: 6px;
				min-height: 20px;
			}}
			QTextEdit#TaskEditTextEdit QScrollBar::handle:vertical:hover {{
				background: {accent};
			}}
		""")
	
	def get_text(self) -> str:
		"""Zwróć wprowadzony tekst."""
		return self._text_edit.toPlainText().strip()
	
	@classmethod
	def prompt(
		cls,
		parent: Optional[QWidget] = None,
		task_title: str = "",
	) -> Tuple[bool, str]:
		"""
		Wyświetl dialog edycji zadania i zwróć wynik.
		
		Returns:
			Tuple[bool, str]: (czy zaakceptowano, nowa treść zadania)
		"""
		dialog = cls(parent=parent, task_title=task_title)
		result = dialog.exec()
		accepted = result == QDialog.DialogCode.Accepted
		return accepted, dialog.get_text() if accepted else task_title
