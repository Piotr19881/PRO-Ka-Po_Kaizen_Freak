"""
Status LED - Wskaźnik statusu połączenia z bazą danych
====================================================
Wyświetla status połączenia w postaci kolorowej kropki LED na pasku tytułowym.

Kolory statusu:
- 🔴 Czerwony: Brak połączenia z serwerem
- 🟢 Zielony: Połączenie OK, brak aktywności
- 🟠 Pomarańczowy: Wysyłanie/odbieranie z problemami
- 🔵 Niebieski: Wysyłanie/odbieranie bez problemów

Dwukrotne kliknięcie otwiera konsolę w stylu Matrix z logami sieciowymi.
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QDialog, QTextEdit, QFrame, QSizePolicy, QScrollArea
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint, QThread, QObject
from PyQt6.QtGui import QFont, QPainter, QColor, QMouseEvent
import time
from typing import Optional, List, Dict, Any
from loguru import logger
from pathlib import Path
import json

from ..utils.i18n_manager import t
from ..core.config import config


class NetworkStatus:
    """Status połączenia z bazą danych"""
    DISCONNECTED = "disconnected"  # 🔴 Brak połączenia
    CONNECTED_IDLE = "connected_idle"  # 🟢 Połączenie OK, brak aktywności
    SYNCING_WITH_ISSUES = "syncing_with_issues"  # 🟠 Wysyłanie/odbieranie z problemami
    SYNCING_OK = "syncing_ok"  # 🔵 Wysyłanie/odbieranie bez problemów


class StatusLED(QWidget):
    """Kontrolka LED wyświetlająca status połączenia"""

    # Sygnały
    double_clicked = pyqtSignal()  # Dwukrotne kliknięcie

    def __init__(self, parent=None):
        super().__init__(parent)
        self.status = NetworkStatus.DISCONNECTED
        self.last_click_time = 0
        self.setFixedSize(20, 20)  # Mała okrągła kontrolka
        self.setToolTip("Status połączenia z bazą danych\nDwukrotne kliknięcie: konsola sieciowa")

    def set_status(self, status: str):
        """Ustaw status LED"""
        self.status = status
        self.update()  # Odśwież wyświetlanie

        # Zaktualizuj tooltip
        tooltip_text = self._get_tooltip_text()
        self.setToolTip(tooltip_text)

    def _get_tooltip_text(self) -> str:
        """Pobierz tekst tooltip dla aktualnego statusu"""
        base_text = "Status połączenia z bazą danych\nDwukrotne kliknięcie: konsola sieciowa\n\n"

        if self.status == NetworkStatus.DISCONNECTED:
            return base_text + "🔴 Brak połączenia z serwerem"
        elif self.status == NetworkStatus.CONNECTED_IDLE:
            return base_text + "🟢 Połączenie OK, brak aktywności"
        elif self.status == NetworkStatus.SYNCING_WITH_ISSUES:
            return base_text + "🟠 Synchronizacja z problemami"
        elif self.status == NetworkStatus.SYNCING_OK:
            return base_text + "🔵 Synchronizacja w toku"
        else:
            return base_text + "⚪ Nieznany status"

    def paintEvent(self, a0):
        """Rysuj okrągłą kropkę LED"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Pobierz kolor dla statusu
        color = self._get_status_color()

        # Rysuj okrąg
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(2, 2, 16, 16)

        # Rysuj obwódkę
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QColor(100, 100, 100))
        painter.drawEllipse(2, 2, 16, 16)

    def _get_status_color(self) -> QColor:
        """Pobierz kolor dla aktualnego statusu"""
        if self.status == NetworkStatus.DISCONNECTED:
            return QColor(220, 53, 69)  # Czerwony
        elif self.status == NetworkStatus.CONNECTED_IDLE:
            return QColor(40, 167, 69)  # Zielony
        elif self.status == NetworkStatus.SYNCING_WITH_ISSUES:
            return QColor(255, 193, 7)  # Pomarańczowy/Żółty
        elif self.status == NetworkStatus.SYNCING_OK:
            return QColor(0, 123, 255)  # Niebieski
        else:
            return QColor(128, 128, 128)  # Szary dla nieznanego

    def mouseDoubleClickEvent(self, a0: QMouseEvent | None = None):
        """Obsługa dwukrotnego kliknięcia"""
        if a0 and a0.button() == Qt.MouseButton.LeftButton:
            self.double_clicked.emit()
            a0.accept()

    def mousePressEvent(self, a0: QMouseEvent | None = None):
        """Obsługa pojedynczego kliknięcia (ignoruj)"""
        if a0:
            a0.accept()  # Nie propaguj dalej


class NetworkConsole(QDialog):
    """Konsola sieciowa w stylu Matrix"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("🖥️ Network Console - Matrix Mode")
        self.setModal(False)
        self.resize(800, 600)
        self._setup_ui()
        self._load_logs()

        # Timer do auto-odświeżania logów
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._load_logs)
        self.refresh_timer.start(2000)  # Odśwież co 2 sekundy

    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        layout = QVBoxLayout(self)

        # Nagłówek
        header = QLabel("NETWORK CONSOLE - MATRIX MODE")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_font = QFont("Courier New", 14, QFont.Weight.Bold)
        header.setFont(header_font)
        header.setStyleSheet("color: #00ff00; background: #000000; padding: 10px;")
        layout.addWidget(header)

        # Konsola
        self.console = QTextEdit()
        self.console.setReadOnly(True)
        self.console.setFont(QFont("Courier New", 10))
        self.console.setStyleSheet("""
            QTextEdit {
                background: #000000;
                color: #00ff00;
                border: 2px solid #00ff00;
                selection-background-color: #00ff00;
                selection-color: #000000;
            }
        """)
        layout.addWidget(self.console)

        # Przyciski
        buttons_layout = QHBoxLayout()

        self.clear_btn = QPushButton("🗑️ CLEAR")
        self.clear_btn.clicked.connect(self._clear_logs)
        buttons_layout.addWidget(self.clear_btn)

        self.refresh_btn = QPushButton("🔄 REFRESH")
        self.refresh_btn.clicked.connect(self._load_logs)
        buttons_layout.addWidget(self.refresh_btn)

        self.close_btn = QPushButton("❌ CLOSE")
        self.close_btn.clicked.connect(self.close)
        buttons_layout.addWidget(self.close_btn)

        layout.addLayout(buttons_layout)

    def _load_logs(self):
        """Załaduj logi z pliku"""
        try:
            log_file = Path("network_console.log")
            if log_file.exists():
                with open(log_file, 'r', encoding='utf-8') as f:
                    logs = f.read()
            else:
                logs = "NETWORK CONSOLE INITIALIZED\n> Waiting for network activity...\n"

            self.console.setPlainText(logs)
            # Przewiń na koniec
            scrollbar = self.console.verticalScrollBar()
            if scrollbar:
                scrollbar.setValue(scrollbar.maximum())

        except Exception as e:
            error_msg = f"ERROR LOADING LOGS: {e}\n"
            self.console.setPlainText(error_msg)

    def _clear_logs(self):
        """Wyczyść logi"""
        try:
            log_file = Path("network_console.log")
            if log_file.exists():
                log_file.unlink()
            self.console.setPlainText("LOGS CLEARED\n> Network console reset\n")
        except Exception as e:
            self.console.append(f"ERROR CLEARING LOGS: {e}\n")

    def closeEvent(self, a0):
        """Zatrzymaj timer przy zamknięciu"""
        self.refresh_timer.stop()
        super().closeEvent(a0)


class NetworkMonitor(QObject):
    """Monitor statusu połączenia z bazą danych"""

    # Sygnały
    status_changed = pyqtSignal(str)  # Zmiana statusu
    log_message = pyqtSignal(str)  # Nowa wiadomość do logów

    def __init__(self):
        super().__init__()
        self.current_status = NetworkStatus.DISCONNECTED
        self.last_sync_time = 0
        self.sync_errors = 0
        self.max_sync_errors = 3

        # Timer sprawdzania statusu
        self.status_timer = QTimer()
        self.status_timer.timeout.connect(self._check_status)
        self.status_timer.start(5000)  # Sprawdzaj co 5 sekund
        
        # Liczniki dla różnych modułów
        self.alarms_errors = 0
        self.pomodoro_errors = 0
        self.last_alarms_sync = 0
        self.last_pomodoro_sync = 0

    def _check_status(self):
        """Sprawdź aktualny status połączenia - rzeczywista logika"""
        import time
        
        current_time = time.time()
        new_status = self.current_status
        
        # Sprawdź czy są aktywne błędy synchronizacji
        total_errors = self.alarms_errors + self.pomodoro_errors
        
        # Sprawdź czas ostatniej synchronizacji (dla każdego modułu)
        time_since_alarms = current_time - self.last_alarms_sync if self.last_alarms_sync > 0 else 9999
        time_since_pomodoro = current_time - self.last_pomodoro_sync if self.last_pomodoro_sync > 0 else 9999
        
        # Logika określania statusu:
        if total_errors > 0:
            # Mamy błędy synchronizacji
            new_status = NetworkStatus.SYNCING_WITH_ISSUES
        elif time_since_alarms < 60 or time_since_pomodoro < 60:
            # Ostatnia sync w ciągu minuty - wszystko OK
            new_status = NetworkStatus.SYNCING_OK
        elif self.last_alarms_sync > 0 or self.last_pomodoro_sync > 0:
            # Był jakiś sync, ale dawno - idle
            new_status = NetworkStatus.CONNECTED_IDLE
        else:
            # Brak synchronizacji - disconnected
            new_status = NetworkStatus.DISCONNECTED

        # Jeśli status się zmienił, wyemituj sygnał
        if new_status != self.current_status:
            self.current_status = new_status
            self.status_changed.emit(new_status)

            # Loguj zmianę statusu
            status_msg = f"[{time.strftime('%H:%M:%S')}] STATUS CHANGE: {new_status.upper()}"
            self.log_message.emit(status_msg)

    def record_sync_event(self, success: bool, module: str = "unknown"):
        """Zarejestruj zdarzenie synchronizacji z konkretnego modułu"""
        import time

        if success:
            # Zapisz czas udanej synchronizacji dla modułu
            if module.lower() == "alarms":
                self.last_alarms_sync = time.time()
                self.alarms_errors = 0
            elif module.lower() == "pomodoro":
                self.last_pomodoro_sync = time.time()
                self.pomodoro_errors = 0
            
            msg = f"[{time.strftime('%H:%M:%S')}] ✓ SYNC SUCCESS: {module.upper()}"
            
            # Zmień status na syncing_ok
            if self.current_status != NetworkStatus.SYNCING_OK:
                self.current_status = NetworkStatus.SYNCING_OK
                self.status_changed.emit(self.current_status)
        else:
            # Zwiększ licznik błędów dla modułu
            if module.lower() == "alarms":
                self.alarms_errors += 1
            elif module.lower() == "pomodoro":
                self.pomodoro_errors += 1
            
            msg = f"[{time.strftime('%H:%M:%S')}] ✗ SYNC ERROR: {module.upper()}"
            
            # Zmień status na syncing_with_issues
            if self.current_status != NetworkStatus.SYNCING_WITH_ISSUES:
                self.current_status = NetworkStatus.SYNCING_WITH_ISSUES
                self.status_changed.emit(self.current_status)

        self.log_message.emit(msg)
    
    def record_websocket_event(self, connected: bool, module: str = "unknown"):
        """Zarejestruj zdarzenie WebSocket (połączono/rozłączono)"""
        import time
        
        if connected:
            msg = f"[{time.strftime('%H:%M:%S')}] ✓ WEBSOCKET CONNECTED: {module.upper()}"
            self.record_sync_event(True, module)
        else:
            msg = f"[{time.strftime('%H:%M:%S')}] ✗ WEBSOCKET DISCONNECTED: {module.upper()}"
            self.log_message.emit(msg)
            
            # Zwiększ licznik błędów
            if module.lower() == "alarms":
                self.alarms_errors += 1
            elif module.lower() == "pomodoro":
                self.pomodoro_errors += 1

    def force_status_check(self):
        """Wymuś sprawdzenie statusu"""
        self._check_status()


class StatusLEDManager:
    """Manager kontrolujący StatusLED"""

    def __init__(self):
        self.led = None
        self.console = None
        self.monitor = NetworkMonitor()
        self._setup_connections()

    def set_led_widget(self, led: StatusLED):
        """Ustaw kontrolkę LED (alias dla set_led)"""
        self.set_led(led)

    def set_led(self, led: StatusLED):
        """Ustaw kontrolkę LED"""
        self.led = led
        self.led.double_clicked.connect(self._show_console)
    
    def set_status(self, status: str):
        """Ustaw status bezpośrednio"""
        if self.led:
            self.led.set_status(status)
        # Aktualizuj też status w monitorze
        if hasattr(self.monitor, 'current_status'):
            self.monitor.current_status = status

    def _setup_connections(self):
        """Połącz sygnały monitora"""
        self.monitor.status_changed.connect(self._on_status_changed)
        self.monitor.log_message.connect(self._on_log_message)

    def _on_status_changed(self, status: str):
        """Obsługa zmiany statusu"""
        if self.led:
            self.led.set_status(status)

    def _on_log_message(self, message: str):
        """Obsługa nowej wiadomości log"""
        self._write_to_log_file(message)

    def _show_console(self):
        """Pokaż konsolę"""
        if not self.console:
            self.console = NetworkConsole()
        self.console.show()
        self.console.raise_()
        self.console.activateWindow()

    def _write_to_log_file(self, message: str):
        """Zapisz wiadomość do pliku log"""
        try:
            log_file = Path("network_console.log")
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(message + "\n")
        except Exception as e:
            logger.error(f"Failed to write to network log: {e}")

    def record_sync_event(self, success: bool, module: str = "unknown"):
        """Zarejestruj zdarzenie synchronizacji"""
        self.monitor.record_sync_event(success, module)

    def get_current_status(self) -> str:
        """Pobierz aktualny status"""
        return self.monitor.current_status


# Globalna instancja managera
_status_led_manager = None

def get_status_led_manager() -> StatusLEDManager:
    """Pobierz globalną instancję managera StatusLED"""
    global _status_led_manager
    if _status_led_manager is None:
        _status_led_manager = StatusLEDManager()
    return _status_led_manager


# ========== GLOBALNE FUNKCJE DLA MODUŁÓW ==========

def record_sync_success(module: str = "unknown"):
    """Zarejestruj udaną synchronizację - dostępne globalnie dla modułów"""
    manager = get_status_led_manager()
    manager.record_sync_event(True, module)


def record_sync_error(module: str = "unknown"):
    """Zarejestruj błąd synchronizacji - dostępne globalnie dla modułów"""
    manager = get_status_led_manager()
    manager.record_sync_event(False, module)


def record_websocket_connected(module: str = "unknown"):
    """Zarejestruj połączenie WebSocket - dostępne globalnie dla modułów"""
    manager = get_status_led_manager()
    manager.monitor.record_websocket_event(True, module)


def record_websocket_disconnected(module: str = "unknown"):
    """Zarejestruj rozłączenie WebSocket - dostępne globalnie dla modułów"""
    manager = get_status_led_manager()
    manager.monitor.record_websocket_event(False, module)


def log_network_event(message: str):
    """Dodaj wiadomość do logów sieciowych"""
    import time
    manager = get_status_led_manager()
    timestamped_msg = f"[{time.strftime('%H:%M:%S')}] {message}"
    manager._on_log_message(timestamped_msg)
