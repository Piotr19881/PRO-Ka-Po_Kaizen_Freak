"""
Authentication Window for PRO-Ka-Po
Okno logowania i rejestracji użytkownika
"""
import sys
import os
import requests
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QLineEdit, QTabWidget, QWidget, QComboBox, QCheckBox,
    QMessageBox, QFrame, QApplication
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QFont, QIcon
from loguru import logger

# Dodaj ścieżkę do modułu src
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.utils.theme_manager import get_theme_manager
from src.utils.i18n_manager import get_i18n

def t(key: str) -> str:
    """Skrócona funkcja do tłumaczeń"""
    return get_i18n().translate(key)


class AuthWindow(QDialog):
    """Okno autoryzacji - logowanie i rejestracja"""
    
    login_successful = pyqtSignal(dict)  # Emituje dane użytkownika po zalogowaniu
    
    def __init__(self, parent=None):
        super().__init__(parent)
        # Użyj URL z konfiguracji zamiast hardcoded localhost
        from src.core.config import config
        self.api_url = config.API_BASE_URL
        self.access_token = None
        self.refresh_token = None
        self.user_data = None
        
        self.setWindowTitle(t('auth.login'))
        self.setMinimumSize(550, 650)
        self.resize(550, 650)
        self.setModal(True)
        
        self._init_ui()
        self._apply_theme()
        self._load_remember_me()  # Załaduj zapisany stan "Zapamiętaj mnie"
        
        # Podłącz sygnał zmiany języka
        get_i18n().language_changed.connect(self.update_translations)
        
    def _init_ui(self):
        """Inicjalizacja interfejsu użytkownika"""
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(40, 40, 40, 40)
        
        # Logo / Tytuł
        title = QLabel(t('auth.title'))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(24)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        subtitle = QLabel(t('auth.subtitle'))
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet("color: #666; margin-bottom: 20px;")
        layout.addWidget(subtitle)
        
        # Tab Widget - Logowanie / Rejestracja
        self.tab_widget = QTabWidget()
        self.tab_widget.addTab(self._create_login_tab(), t('auth.login'))
        self.tab_widget.addTab(self._create_register_tab(), t('auth.register'))
        layout.addWidget(self.tab_widget)
        
        # Status message
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setStyleSheet("padding: 10px;")
        layout.addWidget(self.status_label)
        
    def _create_login_tab(self) -> QWidget:
        """Tworzy zakładkę logowania"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Email
        email_label = QLabel(t('auth.email'))
        self.login_email = QLineEdit()
        self.login_email.setPlaceholderText("twoj-email@example.com")
        self.login_email.setMinimumHeight(35)
        self.login_email.returnPressed.connect(self._on_login_clicked)
        
        # Password
        password_label = QLabel(t('auth.password'))
        self.login_password = QLineEdit()
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_password.setPlaceholderText(t('auth.password'))
        self.login_password.setMinimumHeight(35)
        self.login_password.returnPressed.connect(self._on_login_clicked)
        
        # Remember me
        self.remember_me = QCheckBox(t('auth.remember_me'))
        
        # Login button
        self.login_btn = QPushButton(t('auth.login'))
        self.login_btn.setMinimumHeight(40)
        self.login_btn.clicked.connect(self._on_login_clicked)
        
        # Forgot password
        self.forgot_btn = QPushButton(t('auth.forgot_password'))
        self.forgot_btn.setFlat(True)
        self.forgot_btn.clicked.connect(self._on_forgot_password_clicked)
        
        # Layout
        layout.addWidget(email_label)
        layout.addWidget(self.login_email)
        layout.addWidget(password_label)
        layout.addWidget(self.login_password)
        layout.addWidget(self.remember_me)
        layout.addSpacing(10)
        layout.addWidget(self.login_btn)
        layout.addWidget(self.forgot_btn)
        layout.addStretch()
        
        return tab
        
    def _create_register_tab(self) -> QWidget:
        """Tworzy zakładkę rejestracji"""
        from PyQt6.QtWidgets import QScrollArea
        
        # Scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        
        # Content widget
        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Email
        self.email_label = QLabel(t('auth.email'))
        self.register_email = QLineEdit()
        self.register_email.setPlaceholderText("twoj-email@example.com")
        self.register_email.setMinimumHeight(35)
        
        # Password
        self.password_label = QLabel(t('auth.password'))
        self.register_password = QLineEdit()
        self.register_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_password.setPlaceholderText("Min. 8 znaków")
        self.register_password.setMinimumHeight(35)
        
        # Confirm password
        self.confirm_label = QLabel(t('auth.confirm_password'))
        self.register_password_confirm = QLineEdit()
        self.register_password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_password_confirm.setPlaceholderText(t('auth.confirm_password'))
        self.register_password_confirm.setMinimumHeight(35)
        
        # Name
        self.name_label = QLabel(t('auth.name'))
        self.register_name = QLineEdit()
        self.register_name.setPlaceholderText("Jan Kowalski")
        self.register_name.setMinimumHeight(35)
        
        # Phone (optional)
        self.phone_label = QLabel(t('auth.phone'))
        self.register_phone = QLineEdit()
        self.register_phone.setPlaceholderText("+48 123 456 789")
        self.register_phone.setMinimumHeight(35)
        
        # Language
        self.language_label = QLabel(t('auth.language'))
        self.register_language = QComboBox()
        self.register_language.addItems(["Polski (pl)", "English (en)", "Deutsch (de)"])
        
        # Terms checkbox
        self.accept_terms = QCheckBox(t('auth.accept_terms'))
        
        # Register button
        self.register_btn = QPushButton(t('auth.register'))
        self.register_btn.setMinimumHeight(40)
        self.register_btn.clicked.connect(self._on_register_clicked)
        
        # Layout
        layout.addWidget(self.email_label)
        layout.addWidget(self.register_email)
        layout.addWidget(self.password_label)
        layout.addWidget(self.register_password)
        layout.addWidget(self.confirm_label)
        layout.addWidget(self.register_password_confirm)
        layout.addWidget(self.name_label)
        layout.addWidget(self.register_name)
        layout.addWidget(self.phone_label)
        layout.addWidget(self.register_phone)
        layout.addWidget(self.language_label)
        layout.addWidget(self.register_language)
        layout.addWidget(self.accept_terms)
        layout.addSpacing(10)
        layout.addWidget(self.register_btn)
        layout.addStretch()
        
        # Ustaw content w scroll area
        scroll.setWidget(content)
        
        return scroll
        
    def _apply_theme(self):
        """Zastosuj motyw z ThemeManager"""
        theme_manager = get_theme_manager()
        if theme_manager:
            # ThemeManager automatycznie zastosuje motyw do wszystkich widgetów
            # Możemy dodatkowo ustawić styl dla tego okna
            pass
            
    def _show_status(self, message: str, is_error: bool = False):
        """Wyświetl wiadomość statusu"""
        if is_error:
            self.status_label.setStyleSheet(
                "color: #f44336; background-color: #ffebee; "
                "padding: 10px; border-radius: 5px;"
            )
        else:
            self.status_label.setStyleSheet(
                "color: #4caf50; background-color: #e8f5e9; "
                "padding: 10px; border-radius: 5px;"
            )
        self.status_label.setText(message)
        
        # Automatycznie ukryj po 5 sekundach
        QTimer.singleShot(5000, lambda: self.status_label.setText(""))
        
    def _on_login_clicked(self):
        """Obsługa kliknięcia przycisku logowania"""
        email = self.login_email.text().strip()
        password = self.login_password.text()
        
        # Walidacja
        if not email or not password:
            self._show_status("Wypełnij wszystkie pola", is_error=True)
            return
            
        # Wyłącz przyciski podczas logowania
        self.login_btn.setEnabled(False)
        self.login_btn.setText("Logowanie...")
        
        try:
            # Wysłanie żądania logowania (zwiększony timeout dla Render)
            response = requests.post(
                f"{self.api_url}/api/v1/auth/login",
                json={"email": email, "password": password},
                headers={"Content-Type": "application/json"},
                timeout=60  # Zwiększony timeout dla Render (cold start może trwać ~30s)
            )
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result['access_token']
                self.refresh_token = result['refresh_token']
                self.user_data = result['user']
                
                self._show_status(f"Witaj, {self.user_data['name']}!", is_error=False)
                
                # Zapisz tokeny (w prawdziwej aplikacji użyj keyring)
                self._save_tokens()
                
                # Poczekaj chwilę i zamknij okno
                QTimer.singleShot(1000, self._emit_login_success)
                
            elif response.status_code == 403:
                # Email nie zweryfikowany
                self._show_status(
                    "⚠️ Email nie został zweryfikowany! Sprawdź swoją skrzynkę (także spam).",
                    is_error=True
                )
                # Pokaż dialog weryfikacji
                QTimer.singleShot(1500, lambda: self._show_verification_dialog(email))
                
            elif response.status_code == 401:
                self._show_status("Nieprawidłowy email lub hasło", is_error=True)
                
            else:
                error = response.json().get('detail', 'Nieznany błąd')
                self._show_status(f"Błąd: {error}", is_error=True)
                
        except requests.exceptions.Timeout:
            self._show_status(
                "⏱️ Serwer nie odpowiada (timeout). Render może się budzić (~30s). Spróbuj ponownie.",
                is_error=True
            )
        except requests.exceptions.ConnectionError:
            self._show_status(
                "Nie można połączyć z serwerem. Sprawdź połączenie internetowe.",
                is_error=True
            )
        except Exception as e:
            self._show_status(f"Błąd: {str(e)}", is_error=True)
            
        finally:
            self.login_btn.setEnabled(True)
            self.login_btn.setText("Zaloguj")
            
    def _on_register_clicked(self):
        """Obsługa kliknięcia przycisku rejestracji"""
        email = self.register_email.text().strip()
        password = self.register_password.text()
        password_confirm = self.register_password_confirm.text()
        name = self.register_name.text().strip()
        phone = self.register_phone.text().strip()
        
        # Pobierz kod języka
        language_map = {"Polski (pl)": "pl", "English (en)": "en", "Deutsch (de)": "de"}
        language = language_map.get(self.register_language.currentText(), "pl")
        
        # Walidacja
        if not email or not password or not name:
            self._show_status("Wypełnij wszystkie wymagane pola", is_error=True)
            return
            
        if len(password) < 8:
            self._show_status("Hasło musi mieć minimum 8 znaków", is_error=True)
            return
            
        if password != password_confirm:
            self._show_status("Hasła nie są identyczne", is_error=True)
            return
            
        if not self.accept_terms.isChecked():
            self._show_status("Musisz zaakceptować regulamin", is_error=True)
            return
            
        # Wyłącz przyciski podczas rejestracji
        self.register_btn.setEnabled(False)
        self.register_btn.setText("Rejestracja...")
        
        try:
            # Przygotuj dane
            register_data = {
                "email": email,
                "password": password,
                "name": name,
                "language": language,
                "timezone": "Europe/Warsaw"
            }
            
            if phone:
                register_data["phone"] = phone
            
            # Logowanie requestu
            logger.info(f"[AUTH] Sending registration request to: {self.api_url}/api/v1/auth/register")
            logger.debug(f"[AUTH] Registration data: {register_data}")
                
            # Wysłanie żądania rejestracji (zwiększony timeout dla Render)
            response = requests.post(
                f"{self.api_url}/api/v1/auth/register",
                json=register_data,
                headers={"Content-Type": "application/json"},
                timeout=60  # Zwiększony timeout dla Render (cold start może trwać ~30s)
            )
            
            logger.info(f"[AUTH] Registration response status: {response.status_code}")
            
            if response.status_code == 201:
                result = response.json()
                self._show_status(
                    "Rejestracja zakończona! Sprawdź email i wprowadź kod weryfikacyjny.",
                    is_error=False
                )
                
                # Poczekaj chwilę i pokaż dialog weryfikacji
                QTimer.singleShot(2000, lambda: self._show_verification_dialog(email))
                
            elif response.status_code == 400:
                error = response.json().get('detail', 'Nieprawidłowe dane')
                if 'already registered' in error:
                    self._show_status("Ten email jest już zarejestrowany", is_error=True)
                else:
                    self._show_status(f"Błąd: {error}", is_error=True)
                    
            else:
                error = response.json().get('detail', 'Nieznany błąd')
                self._show_status(f"Błąd: {error}", is_error=True)
                logger.warning(f"[AUTH] Registration failed with status {response.status_code}: {error}")
        
        except requests.exceptions.Timeout:
            logger.error(f"[AUTH] Registration timeout after 60s - server not responding")
            self._show_status(
                "⏱️ Serwer nie odpowiada (timeout). Render może się budzić (~30s). Spróbuj ponownie.",
                is_error=True
            )
        except requests.exceptions.ConnectionError as e:
            logger.error(f"[AUTH] Registration connection error: {str(e)}")
            self._show_status(
                "Nie można połączyć z serwerem. Sprawdź połączenie internetowe.",
                is_error=True
            )
        except Exception as e:
            logger.error(f"[AUTH] Registration unexpected error: {type(e).__name__}: {str(e)}", exc_info=True)
            self._show_status(f"Błąd: {str(e)}", is_error=True)
            
        finally:
            self.register_btn.setEnabled(True)
            self.register_btn.setText("Zarejestruj się")
            
    def _show_verification_dialog(self, email: str):
        """Pokazuje dialog weryfikacji emaila"""
        dialog = VerificationDialog(email, self.api_url, self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Weryfikacja zakończona sukcesem
            self.access_token = dialog.access_token
            self.refresh_token = dialog.refresh_token
            
            # Pobierz dane użytkownika (zapisz email z dialogu)
            self._fetch_user_data(email)
            
    def _fetch_user_data(self, email: str | None = None):
        """Pobiera dane użytkownika po weryfikacji z endpointa /me"""
        import requests
        from requests.exceptions import Timeout, ConnectionError
        
        if not email:
            email = self.register_email.text() or self.login_email.text()
        
        # Jeśli nie mamy access_token, użyj fallback
        if not hasattr(self, 'access_token') or not self.access_token:
            logger.warning("No access token available, using minimal user data")
            self.user_data = {
                "id": None,
                "name": "Użytkownik",
                "email": email,
                "language": "pl",
                "timezone": "Europe/Warsaw"
            }
            self._save_tokens()
            self._emit_login_success()
            return
        
        # Pobierz pełne dane użytkownika z API
        try:
            headers = {
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json"
            }
            
            logger.info(f"Fetching user profile from {self.api_url}/api/v1/auth/me")
            response = requests.get(
                f"{self.api_url}/api/v1/auth/me",
                headers=headers,
                timeout=60
            )
            
            if response.status_code == 200:
                profile = response.json()
                logger.info(f"User profile fetched successfully: {profile.get('email')}")
                
                self.user_data = {
                    "id": profile.get("id"),
                    "name": profile.get("name", "Użytkownik"),
                    "email": profile.get("email", email),
                    "language": profile.get("language", "pl"),
                    "timezone": profile.get("timezone", "Europe/Warsaw"),
                    "email_verified": profile.get("email_verified", False)
                }
            else:
                logger.warning(f"Failed to fetch user profile: {response.status_code} - {response.text}")
                # Fallback do minimalnych danych
                self.user_data = {
                    "id": None,
                    "name": "Użytkownik",
                    "email": email,
                    "language": "pl",
                    "timezone": "Europe/Warsaw"
                }
                
        except Timeout:
            logger.error("Timeout while fetching user profile")
            self.user_data = {
                "id": None,
                "name": "Użytkownik",
                "email": email,
                "language": "pl",
                "timezone": "Europe/Warsaw"
            }
        except ConnectionError as e:
            logger.error(f"Connection error while fetching user profile: {e}")
            self.user_data = {
                "id": None,
                "name": "Użytkownik",
                "email": email,
                "language": "pl",
                "timezone": "Europe/Warsaw"
            }
        except Exception as e:
            logger.error(f"Unexpected error while fetching user profile: {e}")
            self.user_data = {
                "id": None,
                "name": "Użytkownik",
                "email": email,
                "language": "pl",
                "timezone": "Europe/Warsaw"
            }
        
        self._save_tokens()
        self._emit_login_success()
        
    def _on_forgot_password_clicked(self):
        """Obsługa zapomnienia hasła"""
        dialog = ForgotPasswordDialog(self.api_url, self)
        dialog.exec()
        
    def _save_tokens(self):
        """Zapisuje tokeny TYLKO jeśli 'Zapamiętaj mnie' jest zaznaczone"""
        import json
        from src.core.config import config
        
        # Sprawdź czy użytkownik chce być zapamiętany
        if not self.remember_me.isChecked():
            logger.info("Remember me not checked - tokens will not be saved")
            # Usuń istniejące tokeny jeśli istnieją
            tokens_file = config.DATA_DIR / "tokens.json"
            if tokens_file.exists():
                try:
                    tokens_file.unlink()
                    logger.info("Removed existing tokens")
                except Exception as e:
                    logger.warning(f"Failed to remove tokens: {e}")
            return
        
        try:
            tokens = {
                "access_token": self.access_token,
                "refresh_token": self.refresh_token,
                "user_data": self.user_data
            }
            
            # Zapisz tokeny do pliku (tylko jeśli remember_me = True)
            tokens_file = config.DATA_DIR / "tokens.json"
            with open(tokens_file, "w") as f:
                json.dump(tokens, f, indent=2)
            
            logger.info("Tokens saved successfully (remember me enabled)")
                
        except Exception as e:
            logger.error(f"Error saving tokens: {e}")
            
    def _emit_login_success(self):
        """Emituje sygnał sukcesu logowania"""
        # Zapisz stan "Zapamiętaj mnie"
        if self.remember_me.isChecked():
            self._save_remember_me()
        
        # Dodaj tokeny do user_data przed emitowaniem sygnału
        if self.user_data and self.access_token and self.refresh_token:
            self.user_data['access_token'] = self.access_token
            self.user_data['refresh_token'] = self.refresh_token
        
        self.login_successful.emit(self.user_data)
        self.accept()
    
    def _load_remember_me(self):
        """Załaduj zapisany stan checkboxa 'Zapamiętaj mnie'"""
        from src.core.config import load_settings
        settings = load_settings()
        remember = settings.get('remember_me', False)
        self.remember_me.setChecked(remember)
    
    def _save_remember_me(self):
        """Zapisz stan checkboxa 'Zapamiętaj mnie'"""
        from src.core.config import save_settings
        save_settings({'remember_me': self.remember_me.isChecked()})
    
    def update_translations(self):
        """Aktualizuj wszystkie tłumaczenia w oknie"""
        # Tytuł okna
        self.setWindowTitle(t('auth.login'))
        
        # Zakładki
        self.tab_widget.setTabText(0, t('auth.login'))
        self.tab_widget.setTabText(1, t('auth.register'))
        
        # Zakładka logowania
        self.login_btn.setText(t('auth.login'))
        self.forgot_btn.setText(t('auth.forgot_password'))
        self.remember_me.setText(t('auth.remember_me'))
        
        # Zakładka rejestracji
        self.email_label.setText(t('auth.email'))
        self.password_label.setText(t('auth.password'))
        self.confirm_label.setText(t('auth.confirm_password'))
        self.name_label.setText(t('auth.name'))
        self.phone_label.setText(t('auth.phone'))
        self.language_label.setText(t('auth.language'))
        self.accept_terms.setText(t('auth.accept_terms'))
        self.register_password_confirm.setPlaceholderText(t('auth.confirm_password'))
        self.register_btn.setText(t('auth.register'))


class VerificationDialog(QDialog):
    """Dialog weryfikacji emaila - wprowadzanie 6-cyfrowego kodu"""
    
    def __init__(self, email: str, api_url: str, parent=None):
        super().__init__(parent)
        self.email = email
        self.api_url = api_url
        self.access_token = None
        self.refresh_token = None
        
        self.setWindowTitle("Weryfikacja emaila")
        self.setFixedSize(400, 250)
        self.setModal(True)
        
        self._init_ui()
        
    def _init_ui(self):
        """Inicjalizacja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Instrukcja
        info = QLabel(f"Wprowadź 6-cyfrowy kod weryfikacyjny\nwysłany na adres:\n{self.email}")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        info.setWordWrap(True)
        layout.addWidget(info)
        
        # Kod weryfikacyjny
        code_label = QLabel(t('auth.verification_code'))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("000000")
        self.code_input.setMaxLength(6)
        self.code_input.setAlignment(Qt.AlignmentFlag.AlignCenter)
        code_font = QFont()
        code_font.setPointSize(18)
        code_font.setBold(True)
        code_font.setLetterSpacing(QFont.SpacingType.AbsoluteSpacing, 5)
        self.code_input.setFont(code_font)
        self.code_input.returnPressed.connect(self._on_verify_clicked)
        
        # Przyciski
        btn_layout = QHBoxLayout()
        
        self.resend_btn = QPushButton("Wyślij ponownie")
        self.resend_btn.clicked.connect(self._on_resend_clicked)
        
        self.verify_btn = QPushButton("Weryfikuj")
        self.verify_btn.setMinimumHeight(35)
        self.verify_btn.clicked.connect(self._on_verify_clicked)
        
        btn_layout.addWidget(self.resend_btn)
        btn_layout.addWidget(self.verify_btn)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        
        # Layout
        layout.addWidget(code_label)
        layout.addWidget(self.code_input)
        layout.addSpacing(10)
        layout.addLayout(btn_layout)
        layout.addWidget(self.status_label)
        
    def _on_verify_clicked(self):
        """Weryfikacja kodu"""
        code = self.code_input.text().strip()
        
        if len(code) != 6 or not code.isdigit():
            self._show_status("Kod musi składać się z 6 cyfr", is_error=True)
            return
            
        self.verify_btn.setEnabled(False)
        self.verify_btn.setText("Weryfikacja...")
        
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/auth/verify-email",
                json={"email": self.email, "code": code},
                headers={"Content-Type": "application/json"},
                timeout=60  # Zwiększony timeout dla Render
            )
            
            if response.status_code == 200:
                result = response.json()
                self.access_token = result['access_token']
                self.refresh_token = result['refresh_token']
                
                self._show_status("✅ Email zweryfikowany!", is_error=False)
                QTimer.singleShot(1000, self.accept)
                
            elif response.status_code == 400:
                error = response.json().get('detail', '')
                if 'expired' in error.lower():
                    self._show_status("Kod wygasł. Kliknij 'Wyślij ponownie'", is_error=True)
                else:
                    self._show_status("Nieprawidłowy kod weryfikacyjny", is_error=True)
            else:
                self._show_status("Błąd weryfikacji", is_error=True)
                
        except Exception as e:
            self._show_status(f"Błąd: {str(e)}", is_error=True)
            
        finally:
            self.verify_btn.setEnabled(True)
            self.verify_btn.setText("Weryfikuj")
            
    def _on_resend_clicked(self):
        """Ponowne wysłanie kodu"""
        self.resend_btn.setEnabled(False)
        self.resend_btn.setText("Wysyłanie...")
        
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/auth/resend-verification",
                params={"email": self.email, "language": "pl"},
                timeout=60  # Zwiększony timeout dla Render
            )
            
            if response.status_code == 200:
                self._show_status("Kod został wysłany ponownie. Sprawdź email.", is_error=False)
            else:
                self._show_status("Błąd wysyłania kodu", is_error=True)
                
        except Exception as e:
            self._show_status(f"Błąd: {str(e)}", is_error=True)
            
        finally:
            self.resend_btn.setEnabled(True)
            self.resend_btn.setText("Wyślij ponownie")
            
    def _show_status(self, message: str, is_error: bool = False):
        """Wyświetl status"""
        if is_error:
            self.status_label.setStyleSheet("color: #f44336;")
        else:
            self.status_label.setStyleSheet("color: #4caf50;")
        self.status_label.setText(message)


class ForgotPasswordDialog(QDialog):
    """Dialog resetowania hasła"""
    
    def __init__(self, api_url: str, parent=None):
        super().__init__(parent)
        self.api_url = api_url
        self.email = None
        self.code_sent = False
        
        self.setWindowTitle("Resetowanie hasła")
        self.setFixedSize(400, 450)
        self.setModal(True)
        
        self._init_ui()
        
    def _init_ui(self):
        """Inicjalizacja interfejsu"""
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setSpacing(15)
        self.main_layout.setContentsMargins(30, 30, 30, 30)
        
        self._show_email_step()
        
    def _show_email_step(self):
        """Krok 1: Wprowadzenie emaila"""
        self._clear_layout()
        
        info = QLabel(t('auth.email_info'))
        info.setWordWrap(True)
        
        self.email_input = QLineEdit()
        self.email_input.setPlaceholderText("twoj-email@example.com")
        self.email_input.setMinimumHeight(35)
        self.email_input.returnPressed.connect(self._on_send_code_clicked)
        
        self.send_code_btn = QPushButton("Wyślij kod resetowania")
        self.send_code_btn.setMinimumHeight(35)
        self.send_code_btn.clicked.connect(self._on_send_code_clicked)
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addWidget(info)
        self.main_layout.addWidget(self.email_input)
        self.main_layout.addWidget(self.send_code_btn)
        self.main_layout.addWidget(self.status_label)
        self.main_layout.addStretch()
        
    def _show_reset_step(self):
        """Krok 2: Wprowadzenie kodu i nowego hasła"""
        self._clear_layout()
        
        info = QLabel(f"Kod resetowania został wysłany na:\n{self.email}")
        info.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        code_label = QLabel(t('auth.code_from_email'))
        self.code_input = QLineEdit()
        self.code_input.setPlaceholderText("000000")
        self.code_input.setMaxLength(6)
        self.code_input.setMinimumHeight(35)
        
        password_label = QLabel(t('auth.new_password'))
        self.new_password = QLineEdit()
        self.new_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password.setPlaceholderText("Min. 8 znaków")
        self.new_password.setMinimumHeight(35)
        
        confirm_label = QLabel(t('auth.confirm_password'))
        self.new_password_confirm = QLineEdit()
        self.new_password_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self.new_password_confirm.setMinimumHeight(35)
        
        self.reset_btn = QPushButton("Resetuj hasło")
        self.reset_btn.setMinimumHeight(35)
        self.reset_btn.clicked.connect(self._on_reset_password_clicked)
        
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.main_layout.addWidget(info)
        self.main_layout.addWidget(code_label)
        self.main_layout.addWidget(self.code_input)
        self.main_layout.addWidget(password_label)
        self.main_layout.addWidget(self.new_password)
        self.main_layout.addWidget(confirm_label)
        self.main_layout.addWidget(self.new_password_confirm)
        self.main_layout.addWidget(self.reset_btn)
        self.main_layout.addWidget(self.status_label)
        
    def _on_send_code_clicked(self):
        """Wysyła kod resetowania"""
        email = self.email_input.text().strip()
        
        if not email:
            self._show_status("Wprowadź adres email", is_error=True)
            return
            
        self.send_code_btn.setEnabled(False)
        self.send_code_btn.setText("Wysyłanie...")
        
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/auth/forgot-password",
                json={"email": email, "language": "pl"},
                headers={"Content-Type": "application/json"},
                timeout=60  # Zwiększony timeout dla Render
            )
            
            if response.status_code == 200:
                self.email = email
                self._show_status("Kod wysłany. Sprawdź email.", is_error=False)
                QTimer.singleShot(1500, self._show_reset_step)
            else:
                self._show_status("Błąd wysyłania kodu", is_error=True)
                
        except Exception as e:
            self._show_status(f"Błąd: {str(e)}", is_error=True)
            
        finally:
            self.send_code_btn.setEnabled(True)
            self.send_code_btn.setText("Wyślij kod resetowania")
            
    def _on_reset_password_clicked(self):
        """Resetuje hasło"""
        code = self.code_input.text().strip()
        new_password = self.new_password.text()
        confirm = self.new_password_confirm.text()
        
        if not code or len(code) != 6:
            self._show_status("Wprowadź 6-cyfrowy kod", is_error=True)
            return
            
        if len(new_password) < 8:
            self._show_status("Hasło musi mieć min. 8 znaków", is_error=True)
            return
            
        if new_password != confirm:
            self._show_status("Hasła nie są identyczne", is_error=True)
            return
            
        self.reset_btn.setEnabled(False)
        self.reset_btn.setText("Resetowanie...")
        
        try:
            response = requests.post(
                f"{self.api_url}/api/v1/auth/reset-password",
                json={
                    "email": self.email,
                    "code": code,
                    "new_password": new_password
                },
                headers={"Content-Type": "application/json"},
                timeout=60  # Zwiększony timeout dla Render
            )
            
            if response.status_code == 200:
                self._show_status("✅ Hasło zmienione!", is_error=False)
                QTimer.singleShot(1500, self.accept)
            elif response.status_code == 400:
                self._show_status("Nieprawidłowy lub wygasły kod", is_error=True)
            else:
                self._show_status("Błąd resetowania hasła", is_error=True)
                
        except Exception as e:
            self._show_status(f"Błąd: {str(e)}", is_error=True)
            
        finally:
            self.reset_btn.setEnabled(True)
            self.reset_btn.setText("Resetuj hasło")
            
    def _show_status(self, message: str, is_error: bool = False):
        """Wyświetl status"""
        if is_error:
            self.status_label.setStyleSheet("color: #f44336;")
        else:
            self.status_label.setStyleSheet("color: #4caf50;")
        self.status_label.setText(message)
        
    def _clear_layout(self):
        """Czyści layout"""
        while self.main_layout.count():
            item = self.main_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()


# Test aplikacji
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    window = AuthWindow()
    
    def on_login_success(user_data):
        print(f"Zalogowano jako: {user_data}")
        QMessageBox.information(None, "Sukces", f"Witaj, {user_data['name']}!")
        
    window.login_successful.connect(on_login_success)
    window.show()
    
    sys.exit(app.exec())
