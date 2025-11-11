"""
CallCryptor Dialogs - Dialogi dla modułu CallCryptor
====================================================

Zawiera dialogi:
- AddSourceDialog: Dodawanie źródła nagrań (folder lokalny / konto e-mail)
- EditTagsDialog: Zarządzanie tagami (TODO)
- RecordingDetailsDialog: Szczegóły nagrania (TODO)

Integracja:
- Theme Manager
- i18n Manager
- Email Accounts Database (dla wyboru konta)
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QLineEdit, QComboBox, QRadioButton,
    QGroupBox, QFormLayout, QSpinBox, QFileDialog,
    QCheckBox, QMessageBox, QButtonGroup
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from loguru import logger
from typing import Optional, Dict, List
from pathlib import Path

from ..utils.i18n_manager import t
from ..utils.theme_manager import get_theme_manager
from ..database.email_accounts_db import EmailAccountsDatabase


class AddSourceDialog(QDialog):
    """Dialog dodawania nowego źródła nagrań"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.email_db = None
        self.user_id = None
        
        # Pobierz user_id z parent (CallCryptorView)
        if parent and hasattr(parent, 'user_id'):
            self.user_id = parent.user_id
            
            # Inicjalizuj bazę kont e-mail
            try:
                from ..core.config import config
                email_db_path = config.DATA_DIR / "email_accounts.db"
                # Zawsze twórz instancję - _init_database utworzy tabelę jeśli nie istnieje
                self.email_db = EmailAccountsDatabase(str(email_db_path))
                logger.info(f"[CallCryptor] Email DB initialized: {email_db_path}")
            except Exception as e:
                logger.error(f"[CallCryptor] Failed to initialize email DB: {e}")
                import traceback
                logger.error(traceback.format_exc())
                self.email_db = None
        
        self.setWindowTitle(t('callcryptor.dialog.add_source.title'))
        self.setMinimumWidth(600)
        self.setModal(True)
        
        self._setup_ui()
        self.apply_theme()
    
    def _setup_ui(self):
        """Konfiguracja UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # === NAZWA ŹRÓDŁA ===
        name_layout = QFormLayout()
        
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText(t('callcryptor.dialog.source_name_placeholder'))
        name_layout.addRow(f"{t('callcryptor.dialog.source_name')}:", self.name_input)
        
        layout.addLayout(name_layout)
        
        # === TYP ŹRÓDŁA ===
        type_group = QGroupBox(t('callcryptor.dialog.source_type'))
        type_layout = QVBoxLayout()
        
        self.source_type_group = QButtonGroup(self)
        
        self.folder_radio = QRadioButton(f"📁 {t('callcryptor.dialog.folder_local')}")
        self.folder_radio.setChecked(True)
        self.folder_radio.toggled.connect(self._on_type_changed)
        self.source_type_group.addButton(self.folder_radio, 0)
        type_layout.addWidget(self.folder_radio)
        
        self.email_radio = QRadioButton(f"📧 {t('callcryptor.dialog.email_account')}")
        self.email_radio.toggled.connect(self._on_type_changed)
        self.source_type_group.addButton(self.email_radio, 1)
        type_layout.addWidget(self.email_radio)
        
        type_group.setLayout(type_layout)
        layout.addWidget(type_group)
        
        # === OPCJE DLA FOLDERU ===
        self.folder_group = QGroupBox(t('callcryptor.dialog.folder_options'))
        folder_layout = QFormLayout()
        folder_layout.setSpacing(10)
        
        # Ścieżka
        path_layout = QHBoxLayout()
        self.folder_path_input = QLineEdit()
        self.folder_path_input.setPlaceholderText("C:\\Users\\...")
        path_layout.addWidget(self.folder_path_input)
        
        self.browse_btn = QPushButton(t('callcryptor.dialog.browse'))
        self.browse_btn.clicked.connect(self._browse_folder)
        path_layout.addWidget(self.browse_btn)
        
        folder_layout.addRow(f"{t('callcryptor.dialog.folder_path')}:", path_layout)
        
        # Rozszerzenia plików - rozszerzona lista dla dyktafonów i telefonów
        ext_label = QLabel(t('callcryptor.dialog.extensions'))
        ext_layout = QVBoxLayout()
        
        # Wiersz 1 - Najpopularniejsze
        ext_row1 = QHBoxLayout()
        self.ext_amr = QCheckBox(".amr")  # AMR - główny format w telefonach
        self.ext_amr.setChecked(True)
        ext_row1.addWidget(self.ext_amr)
        
        self.ext_mp3 = QCheckBox(".mp3")
        self.ext_mp3.setChecked(True)
        ext_row1.addWidget(self.ext_mp3)
        
        self.ext_m4a = QCheckBox(".m4a")  # AAC w kontenerze M4A (iPhone)
        self.ext_m4a.setChecked(True)
        ext_row1.addWidget(self.ext_m4a)
        
        self.ext_3gp = QCheckBox(".3gp")  # 3GPP - stare telefony
        self.ext_3gp.setChecked(True)
        ext_row1.addWidget(self.ext_3gp)
        
        self.ext_wav = QCheckBox(".wav")
        self.ext_wav.setChecked(True)
        ext_row1.addWidget(self.ext_wav)
        ext_row1.addStretch()
        ext_layout.addLayout(ext_row1)
        
        # Wiersz 2 - Dodatkowe formaty
        ext_row2 = QHBoxLayout()
        self.ext_opus = QCheckBox(".opus")  # OPUS - nowoczesny codec
        ext_row2.addWidget(self.ext_opus)
        
        self.ext_ogg = QCheckBox(".ogg")
        ext_row2.addWidget(self.ext_ogg)
        
        self.ext_flac = QCheckBox(".flac")
        ext_row2.addWidget(self.ext_flac)
        
        self.ext_wma = QCheckBox(".wma")  # Windows Media Audio
        ext_row2.addWidget(self.ext_wma)
        
        self.ext_aac = QCheckBox(".aac")  # AAC raw
        ext_row2.addWidget(self.ext_aac)
        ext_row2.addStretch()
        ext_layout.addLayout(ext_row2)
        
        folder_layout.addRow(ext_label, ext_layout)
        
        # Głębokość skanowania
        self.scan_depth_spin = QSpinBox()
        self.scan_depth_spin.setRange(1, 10)
        self.scan_depth_spin.setValue(1)
        self.scan_depth_spin.setSuffix(" " + t('callcryptor.dialog.levels'))
        folder_layout.addRow(f"{t('callcryptor.dialog.scan_depth')}:", self.scan_depth_spin)
        
        self.folder_group.setLayout(folder_layout)
        layout.addWidget(self.folder_group)
        
        # === OPCJE DLA E-MAIL ===
        self.email_group = QGroupBox(t('callcryptor.dialog.email_options'))
        email_layout = QFormLayout()
        email_layout.setSpacing(10)
        
        # Wybór konta
        self.email_account_combo = QComboBox()
        self._load_email_accounts()
        email_layout.addRow(f"{t('callcryptor.dialog.email_select')}:", self.email_account_combo)
        
        # Gdzie szukać (folder)
        folder_search_layout = QHBoxLayout()
        
        self.search_all_folders_check = QCheckBox("Wszystkie foldery")
        self.search_all_folders_check.setChecked(True)  # DOMYŚLNIE ZAZNACZONE
        self.search_all_folders_check.toggled.connect(self._on_all_folders_toggled)
        folder_search_layout.addWidget(self.search_all_folders_check)
        
        folder_search_layout.addSpacing(20)
        folder_search_layout.addWidget(QLabel("lub wybierz folder:"))
        
        self.email_folder_combo = QComboBox()
        self.email_folder_combo.addItems(['INBOX', 'Sent', 'Drafts', 'Archive', '[Gmail]/All Mail'])
        self.email_folder_combo.setEditable(True)
        self.email_folder_combo.setEnabled(False)  # DOMYŚLNIE WYŁĄCZONE (bo wszystkie foldery zaznaczone)
        folder_search_layout.addWidget(self.email_folder_combo)
        folder_search_layout.addStretch()
        
        email_layout.addRow("📁 Zakres wyszukiwania:", folder_search_layout)
        
        # Typ wyszukiwania
        search_type_layout = QHBoxLayout()
        
        self.search_type_group = QButtonGroup(self)
        
        self.search_subject_radio = QRadioButton("W temacie (SUBJECT)")
        self.search_subject_radio.setChecked(True)
        self.search_type_group.addButton(self.search_subject_radio, 0)
        search_type_layout.addWidget(self.search_subject_radio)
        
        self.search_body_radio = QRadioButton("W treści (BODY)")
        self.search_type_group.addButton(self.search_body_radio, 1)
        search_type_layout.addWidget(self.search_body_radio)
        
        self.search_anywhere_radio = QRadioButton("Wszędzie (TEXT)")
        self.search_type_group.addButton(self.search_anywhere_radio, 2)
        search_type_layout.addWidget(self.search_anywhere_radio)
        
        search_type_layout.addStretch()
        email_layout.addRow("🔍 Typ wyszukiwania:", search_type_layout)
        
        # Fraza wyszukiwania
        self.search_phrase_input = QLineEdit()
        self.search_phrase_input.setPlaceholderText("nagranie rozmowy")
        self.search_phrase_input.setToolTip(
            "Fraza do wyszukania w wiadomościach.\n"
            "Zostanie użyta zgodnie z wybranym typem wyszukiwania.\n"
            "Można też użyć zaawansowanych komend IMAP:\n"
            "  ALL - wszystkie wiadomości\n"
            "  FROM adres@email.com - od nadawcy"
        )
        email_layout.addRow(f"{t('callcryptor.dialog.search_phrase')}:", self.search_phrase_input)
        
        # Rozszerzenia załączników - checkboxy (jak dla folderu)
        att_ext_label = QLabel("Szukane rozszerzenia załączników:")
        att_ext_layout = QVBoxLayout()
        
        # Wiersz 1
        att_ext_row1 = QHBoxLayout()
        self.att_ext_amr = QCheckBox(".amr")
        self.att_ext_amr.setChecked(True)
        att_ext_row1.addWidget(self.att_ext_amr)
        
        self.att_ext_mp3 = QCheckBox(".mp3")
        self.att_ext_mp3.setChecked(True)
        att_ext_row1.addWidget(self.att_ext_mp3)
        
        self.att_ext_m4a = QCheckBox(".m4a")
        self.att_ext_m4a.setChecked(True)
        att_ext_row1.addWidget(self.att_ext_m4a)
        
        self.att_ext_3gp = QCheckBox(".3gp")
        self.att_ext_3gp.setChecked(True)
        att_ext_row1.addWidget(self.att_ext_3gp)
        
        self.att_ext_wav = QCheckBox(".wav")
        self.att_ext_wav.setChecked(True)
        att_ext_row1.addWidget(self.att_ext_wav)
        att_ext_row1.addStretch()
        att_ext_layout.addLayout(att_ext_row1)
        
        # Wiersz 2
        att_ext_row2 = QHBoxLayout()
        self.att_ext_opus = QCheckBox(".opus")
        att_ext_row2.addWidget(self.att_ext_opus)
        
        self.att_ext_ogg = QCheckBox(".ogg")
        att_ext_row2.addWidget(self.att_ext_ogg)
        
        self.att_ext_flac = QCheckBox(".flac")
        att_ext_row2.addWidget(self.att_ext_flac)
        
        self.att_ext_wma = QCheckBox(".wma")
        att_ext_row2.addWidget(self.att_ext_wma)
        
        self.att_ext_aac = QCheckBox(".aac")
        att_ext_row2.addWidget(self.att_ext_aac)
        att_ext_row2.addStretch()
        att_ext_layout.addLayout(att_ext_row2)
        
        email_layout.addRow(att_ext_label, att_ext_layout)
        
        # Pomijane słowa w nazwie kontaktu
        self.contact_ignore_input = QLineEdit()
        self.contact_ignore_input.setPlaceholderText("np. Nagranie rozmowy;Voicemail;Recording")
        self.contact_ignore_input.setToolTip(
            "Słowa lub frazy do pominięcia podczas parsowania nazwy kontaktu z tematu emaila.\n"
            "Oddziel średnikami (;)\n"
            "Przykład: 'Nagranie rozmowy;CallRecorder;Voicemail'\n"
            "Te słowa będą usuwane z tematu, pozostawiając czystą nazwę kontaktu."
        )
        email_layout.addRow("🏷️ Pomijane w kontakcie:", self.contact_ignore_input)
        
        self.email_group.setLayout(email_layout)
        self.email_group.setVisible(False)  # Domyślnie ukryte
        layout.addWidget(self.email_group)
        
        # === PRZYCISKI ===
        buttons_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton(t('button.cancel'))
        self.cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(self.cancel_btn)
        
        buttons_layout.addStretch()
        
        self.save_btn = QPushButton(t('button.save'))
        self.save_btn.clicked.connect(self._save)
        self.save_btn.setDefault(True)
        buttons_layout.addWidget(self.save_btn)
        
        layout.addLayout(buttons_layout)
    
    def _load_email_accounts(self):
        """Załaduj konta e-mail do combo boxa"""
        if not self.email_db or not self.user_id:
            self.email_account_combo.addItem(t('callcryptor.dialog.no_email_accounts'), None)
            return
        
        accounts = self.email_db.get_all_accounts(self.user_id)
        
        if not accounts:
            self.email_account_combo.addItem(t('callcryptor.dialog.no_email_accounts'), None)
        else:
            for account in accounts:
                display = f"{account['account_name']} ({account['email_address']})"
                self.email_account_combo.addItem(display, account['id'])
    
    def _on_type_changed(self):
        """Obsługa zmiany typu źródła"""
        is_folder = self.folder_radio.isChecked()
        
        self.folder_group.setVisible(is_folder)
        self.email_group.setVisible(not is_folder)
    
    def _on_all_folders_toggled(self, checked: bool):
        """Obsługa zmiany opcji 'wszystkie foldery'"""
        self.email_folder_combo.setEnabled(not checked)
        if checked:
            self.email_folder_combo.setCurrentText("*")
    
    def _browse_folder(self):
        """Przeglądaj folder"""
        folder = QFileDialog.getExistingDirectory(
            self,
            t('callcryptor.dialog.select_folder'),
            str(Path.home())
        )
        
        if folder:
            self.folder_path_input.setText(folder)
    
    def _validate(self) -> bool:
        """Walidacja formularza"""
        # Nazwa źródła
        if not self.name_input.text().strip():
            QMessageBox.warning(
                self,
                t('error.general'),
                t('callcryptor.dialog.error.name_required')
            )
            return False
        
        # Folder
        if self.folder_radio.isChecked():
            if not self.folder_path_input.text().strip():
                QMessageBox.warning(
                    self,
                    t('error.general'),
                    t('callcryptor.dialog.error.path_required')
                )
                return False
            
            # Sprawdź czy folder istnieje
            if not Path(self.folder_path_input.text()).is_dir():
                QMessageBox.warning(
                    self,
                    t('error.general'),
                    t('callcryptor.dialog.error.path_not_exists')
                )
                return False
            
            # Sprawdź czy wybrano jakieś rozszerzenia
            if not any([self.ext_mp3.isChecked(), self.ext_wav.isChecked(),
                       self.ext_m4a.isChecked(), self.ext_ogg.isChecked(),
                       self.ext_flac.isChecked()]):
                QMessageBox.warning(
                    self,
                    t('error.general'),
                    t('callcryptor.dialog.error.extensions_required')
                )
                return False
        
        # E-mail
        else:
            if self.email_account_combo.currentData() is None:
                QMessageBox.warning(
                    self,
                    t('error.general'),
                    t('callcryptor.dialog.error.email_account_required')
                )
                return False
            
            if not self.search_phrase_input.text().strip():
                QMessageBox.warning(
                    self,
                    t('error.general'),
                    t('callcryptor.dialog.error.search_phrase_required')
                )
                return False
        
        return True
    
    def _save(self):
        """Zapisz dane"""
        if not self._validate():
            return
        
        self.accept()
    
    def get_source_data(self) -> Dict:
        """
        Pobierz dane źródła.
        
        Returns:
            Dict z konfiguracją źródła
        """
        data = {
            'source_name': self.name_input.text().strip(),
            'source_type': 'folder' if self.folder_radio.isChecked() else 'email',
            'is_active': True
        }
        
        if self.folder_radio.isChecked():
            # Folder lokalny
            data['folder_path'] = self.folder_path_input.text().strip()
            data['scan_depth'] = self.scan_depth_spin.value()
            
            # Rozszerzenia - wszystkie nowe formaty
            extensions = []
            if self.ext_amr.isChecked():
                extensions.append('amr')
            if self.ext_mp3.isChecked():
                extensions.append('mp3')
            if self.ext_m4a.isChecked():
                extensions.append('m4a')
            if self.ext_3gp.isChecked():
                extensions.append('3gp')
            if self.ext_wav.isChecked():
                extensions.append('wav')
            if self.ext_opus.isChecked():
                extensions.append('opus')
            if self.ext_ogg.isChecked():
                extensions.append('ogg')
            if self.ext_flac.isChecked():
                extensions.append('flac')
            if self.ext_wma.isChecked():
                extensions.append('wma')
            if self.ext_aac.isChecked():
                extensions.append('aac')
            
            data['file_extensions'] = extensions
        
        else:
            # Konto e-mail
            data['email_account_id'] = self.email_account_combo.currentData()
            
            # Fraza wyszukiwania
            search_phrase = self.search_phrase_input.text().strip()
            
            # Określ typ wyszukiwania na podstawie wyboru użytkownika
            if self.search_subject_radio.isChecked():
                search_type = 'SUBJECT'
            elif self.search_body_radio.isChecked():
                search_type = 'BODY'
            else:  # search_anywhere_radio
                search_type = 'TEXT'
            
            data['search_phrase'] = search_phrase
            data['search_type'] = search_type  # Nowe pole
            
            # Folder docelowy lub wszystkie foldery
            if self.search_all_folders_check.isChecked():
                data['target_folder'] = '*'  # Specjalna wartość dla wszystkich folderów
                data['search_all_folders'] = True
            else:
                data['target_folder'] = self.email_folder_combo.currentText()
                data['search_all_folders'] = False
            
            # Buduj wzorzec załączników z checkboxów
            extensions = []
            if self.att_ext_amr.isChecked():
                extensions.append('amr')
            if self.att_ext_mp3.isChecked():
                extensions.append('mp3')
            if self.att_ext_m4a.isChecked():
                extensions.append('m4a')
            if self.att_ext_3gp.isChecked():
                extensions.append('3gp')
            if self.att_ext_wav.isChecked():
                extensions.append('wav')
            if self.att_ext_opus.isChecked():
                extensions.append('opus')
            if self.att_ext_ogg.isChecked():
                extensions.append('ogg')
            if self.att_ext_flac.isChecked():
                extensions.append('flac')
            if self.att_ext_wma.isChecked():
                extensions.append('wma')
            if self.att_ext_aac.isChecked():
                extensions.append('aac')
            
            if extensions:
                data['attachment_pattern'] = r".*\.(" + '|'.join(extensions) + r")$"
            else:
                # Jeśli nic nie zaznaczono, ustaw domyślny
                data['attachment_pattern'] = r".*\.(amr|mp3|m4a|3gp|wav)$"
            
            # Pomijane słowa w kontakcie
            contact_ignore = self.contact_ignore_input.text().strip()
            data['contact_ignore_words'] = contact_ignore if contact_ignore else None
        
        return data
    
    def apply_theme(self):
        """Aplikuj motyw"""
        if not self.theme_manager:
            return
        
        colors = self.theme_manager.get_current_colors()
        
        # Style dla inputów
        input_style = f"""
            QLineEdit, QSpinBox, QComboBox {{
                background-color: {colors.get('bg_main', '#FFFFFF')};
                color: {colors.get('text_primary', '#000000')};
                border: 1px solid {colors.get('border_light', '#CCCCCC')};
                border-radius: 4px;
                padding: 5px;
            }}
            QLineEdit:focus, QSpinBox:focus, QComboBox:focus {{
                border: 2px solid {colors.get('accent_primary', '#2196F3')};
            }}
        """
        self.setStyleSheet(input_style)


class EmailDateRangeDialog(QDialog):
    """Dialog wyboru zakresu dat dla skanowania emaili"""
    
    def __init__(self, total_messages: int, oldest_date: Optional[str] = None, newest_date: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.total_messages = total_messages
        self.oldest_date = oldest_date
        self.newest_date = newest_date
        self.selected_range = None
        
        self.setWindowTitle("Wybór zakresu dat")
        self.setModal(True)
        self.setMinimumWidth(500)
        
        self._init_ui()
        self._apply_theme()
    
    def _init_ui(self):
        """Inicjalizuj UI"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Informacja o znalezionych wiadomościach
        info_label = QLabel(
            f"📧 Znaleziono {self.total_messages} wiadomości "
            f"z załącznikami audio\n"
            f"📅 Zakres dat: {self.oldest_date or 'N/A'} — {self.newest_date or 'N/A'}"
        )
        info_label.setWordWrap(True)
        font = info_label.font()
        font.setPointSize(10)
        info_label.setFont(font)
        layout.addWidget(info_label)
        
        # Separator
        separator = QLabel()
        separator.setFrameStyle(QLabel.Shape.HLine | QLabel.Shadow.Sunken)
        layout.addWidget(separator)
        
        # Opcje zakresu
        range_group = QGroupBox("Wybierz zakres do pobrania:")
        range_layout = QVBoxLayout()
        range_layout.setSpacing(10)
        
        self.range_buttons = QButtonGroup(self)
        
        # Preset ranges
        from datetime import datetime, timedelta
        now = datetime.now()
        
        presets = [
            ("7 dni", (now - timedelta(days=7)).strftime('%d-%b-%Y'), "Ostatnie 7 dni"),
            ("30 dni", (now - timedelta(days=30)).strftime('%d-%b-%Y'), "Ostatni miesiąc"),
            ("90 dni", (now - timedelta(days=90)).strftime('%d-%b-%Y'), "Ostatnie 3 miesiące"),
            ("180 dni", (now - timedelta(days=180)).strftime('%d-%b-%Y'), "Ostatnie 6 miesięcy"),
            ("365 dni", (now - timedelta(days=365)).strftime('%d-%b-%Y'), "Ostatni rok"),
            ("all", None, f"Wszystkie ({self.total_messages} wiadomości)")
        ]
        
        for idx, (key, date_from, label) in enumerate(presets):
            radio = QRadioButton(f"📅 {label}")
            radio.setProperty("range_key", key)
            radio.setProperty("date_from", date_from)
            self.range_buttons.addButton(radio, idx)
            range_layout.addWidget(radio)
            
            # Domyślnie zaznacz 30 dni
            if key == "30 dni":
                radio.setChecked(True)
        
        range_group.setLayout(range_layout)
        layout.addWidget(range_group)
        
        # Przyciski
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("❌ Anuluj")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        ok_btn = QPushButton("✅ Pobierz")
        ok_btn.setDefault(True)
        ok_btn.clicked.connect(self._on_ok)
        btn_layout.addWidget(ok_btn)
        
        layout.addLayout(btn_layout)
    
    def _on_ok(self):
        """Zapisz wybrany zakres"""
        checked_button = self.range_buttons.checkedButton()
        if checked_button:
            range_key = checked_button.property("range_key")
            date_from = checked_button.property("date_from")
            
            if range_key == "all":
                self.selected_range = None  # Wszystkie wiadomości
            else:
                self.selected_range = {
                    'from': date_from,
                    'to': None  # Do teraz
                }
        
        self.accept()
    
    def get_date_range(self) -> Optional[Dict[str, str]]:
        """Zwróć wybrany zakres dat"""
        return self.selected_range
    
    def _apply_theme(self):
        """Zastosuj motyw"""
        colors = self.theme_manager.get_current_colors()
        
        style = f"""
            QDialog {{
                background-color: {colors.get('bg_main', '#FFFFFF')};
            }}
            QLabel {{
                color: {colors.get('text_primary', '#000000')};
            }}
            QGroupBox {{
                color: {colors.get('text_primary', '#000000')};
                border: 1px solid {colors.get('border_light', '#CCCCCC')};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
            QRadioButton {{
                color: {colors.get('text_primary', '#000000')};
                spacing: 8px;
            }}
            QPushButton {{
                background-color: {colors.get('accent_primary', '#2196F3')};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {colors.get('accent_hover', '#1976D2')};
            }}
        """
        self.setStyleSheet(style)


# ============================================================================
# SYNC DIALOGS
# ============================================================================

class SyncConsentDialog(QDialog):
    """
    Dialog zgody na synchronizację CallCryptor
    Pokazywany przy pierwszym włączeniu sync (privacy-first)
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.auto_sync_enabled = False
        self.dont_show_again = False
        
        self.setWindowTitle(t('callcryptor.sync.title'))
        self.setMinimumWidth(600)
        self.setMinimumHeight(500)
        
        self._init_ui()
        self._apply_theme()
        
    def _init_ui(self):
        """Inicjalizacja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Nagłówek z emoji
        header_layout = QHBoxLayout()
        header_icon = QLabel("📨")
        header_icon.setFont(QFont("Segoe UI Emoji", 32))
        header_layout.addWidget(header_icon)
        
        header_text = QLabel(t('callcryptor.sync.consent_header'))
        header_text.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_text.setWordWrap(True)
        header_layout.addWidget(header_text, 1)
        layout.addLayout(header_layout)
        
        # Separator
        layout.addSpacing(10)
        
        # Ostrzeżenie o prywatności
        warning_group = QGroupBox("⚠️ " + t('callcryptor.sync.privacy_warning_title'))
        warning_layout = QVBoxLayout(warning_group)
        
        warning_text = QLabel(t('callcryptor.sync.privacy_warning_text'))
        warning_text.setWordWrap(True)
        warning_text.setStyleSheet("padding: 10px; background-color: rgba(255, 140, 0, 0.1); border-radius: 4px;")
        warning_layout.addWidget(warning_text)
        
        layout.addWidget(warning_group)
        
        # Co BĘDZIE synchronizowane
        sync_yes_group = QGroupBox("✅ " + t('callcryptor.sync.will_sync'))
        sync_yes_layout = QVBoxLayout(sync_yes_group)
        
        sync_yes_items = [
            t('callcryptor.sync.will_sync_metadata'),
            t('callcryptor.sync.will_sync_transcriptions'),
            t('callcryptor.sync.will_sync_tags'),
            t('callcryptor.sync.will_sync_links')
        ]
        
        for item in sync_yes_items:
            label = QLabel(f"  • {item}")
            label.setWordWrap(True)
            sync_yes_layout.addWidget(label)
        
        layout.addWidget(sync_yes_group)
        
        # Co NIE będzie synchronizowane
        sync_no_group = QGroupBox("❌ " + t('callcryptor.sync.wont_sync'))
        sync_no_layout = QVBoxLayout(sync_no_group)
        
        sync_no_items = [
            t('callcryptor.sync.wont_sync_audio'),
            t('callcryptor.sync.wont_sync_passwords')
        ]
        
        colors = self.theme_manager.get_current_colors() if self.theme_manager else {}
        error_color = colors.get('error_bg', '#D32F2F')
        
        for item in sync_no_items:
            label = QLabel(f"  • {item}")
            label.setWordWrap(True)
            label.setStyleSheet(f"color: {error_color}; font-weight: bold;")
            sync_no_layout.addWidget(label)
        
        layout.addWidget(sync_no_group)
        
        # Opcje
        layout.addSpacing(10)
        
        self.auto_sync_checkbox = QCheckBox(t('callcryptor.sync.enable_auto_sync'))
        self.auto_sync_checkbox.setToolTip(t('callcryptor.sync.auto_sync_tooltip'))
        layout.addWidget(self.auto_sync_checkbox)
        
        self.dont_show_checkbox = QCheckBox(t('callcryptor.sync.dont_show_again'))
        layout.addWidget(self.dont_show_checkbox)
        
        layout.addStretch()
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        cancel_btn = QPushButton(t('common.cancel'))
        cancel_btn.setMinimumWidth(120)
        cancel_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(cancel_btn)
        
        colors = self.theme_manager.get_current_colors() if self.theme_manager else {}
        warning_bg = colors.get('warning_bg', '#FFA000')
        success_bg = colors.get('success_bg', '#4CAF50')
        
        sync_once_btn = QPushButton(t('callcryptor.sync.sync_once'))
        sync_once_btn.setMinimumWidth(150)
        sync_once_btn.clicked.connect(self._sync_once)
        sync_once_btn.setStyleSheet(f"background-color: {warning_bg};")
        buttons_layout.addWidget(sync_once_btn)
        
        enable_btn = QPushButton(t('callcryptor.sync.enable_sync'))
        enable_btn.setMinimumWidth(150)
        enable_btn.clicked.connect(self._enable_sync)
        enable_btn.setStyleSheet(f"background-color: {success_bg};")
        buttons_layout.addWidget(enable_btn)
        
        layout.addLayout(buttons_layout)
    
    def _sync_once(self):
        """Synchronizuj raz bez włączania auto-sync"""
        self.auto_sync_enabled = False
        self.dont_show_again = self.dont_show_checkbox.isChecked()
        self.accept()
    
    def _enable_sync(self):
        """Włącz synchronizację"""
        self.auto_sync_enabled = self.auto_sync_checkbox.isChecked()
        self.dont_show_again = self.dont_show_checkbox.isChecked()
        self.accept()
    
    def _apply_theme(self):
        """Zastosuj motyw"""
        if not self.theme_manager or not self.theme_manager.current_theme:
            return
        
        colors = self.theme_manager.get_current_colors()
        
        style = f"""
            QDialog {{
                background-color: {colors.get('background_primary', '#FFFFFF')};
                color: {colors.get('text_primary', '#000000')};
            }}
            QGroupBox {{
                border: 2px solid {colors.get('border_primary', '#E0E0E0')};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }}
            QPushButton {{
                color: white;
                border: none;
                border-radius: 6px;
                padding: 10px 20px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
        """
        self.setStyleSheet(style)


class SyncStatusDialog(QDialog):
    """
    Dialog statusu synchronizacji
    Pokazywany gdy sync jest już włączona
    """
    
    def __init__(self, sync_stats: dict, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.sync_stats = sync_stats
        self.disable_sync = False
        
        self.setWindowTitle(t('callcryptor.sync.title'))
        self.setMinimumWidth(500)
        self.setMinimumHeight(400)
        
        self._init_ui()
        self._apply_theme()
    
    def _init_ui(self):
        """Inicjalizacja interfejsu"""
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        
        # Nagłówek
        header_layout = QHBoxLayout()
        header_icon = QLabel("📨")
        header_icon.setFont(QFont("Segoe UI Emoji", 32))
        header_layout.addWidget(header_icon)
        
        header_text = QLabel(t('callcryptor.sync.status_header'))
        header_text.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        header_layout.addWidget(header_text, 1)
        layout.addLayout(header_layout)
        
        # Status
        status_group = QGroupBox(t('callcryptor.sync.status'))
        status_layout = QFormLayout(status_group)
        
        status_label = QLabel("✅ " + t('callcryptor.sync.enabled'))
        status_label.setStyleSheet("color: #4CAF50; font-weight: bold;")
        status_layout.addRow(t('callcryptor.sync.state'), status_label)
        
        last_sync = self.sync_stats.get('last_sync_at', None)
        if last_sync:
            last_sync_label = QLabel(str(last_sync))
        else:
            last_sync_label = QLabel(t('callcryptor.sync.never'))
            last_sync_label.setStyleSheet("color: #999;")
        status_layout.addRow(t('callcryptor.sync.last_sync'), last_sync_label)
        
        layout.addWidget(status_group)
        
        # Statystyki
        stats_group = QGroupBox(t('callcryptor.sync.statistics'))
        stats_layout = QFormLayout(stats_group)
        
        total_recordings = self.sync_stats.get('total_recordings', 0)
        synced_recordings = total_recordings  # TODO: track synced vs unsynced
        pending = self.sync_stats.get('pending_uploads', 0)
        
        stats_layout.addRow(t('callcryptor.sync.total_recordings'), QLabel(str(total_recordings)))
        stats_layout.addRow(t('callcryptor.sync.synced_recordings'), QLabel(str(synced_recordings)))
        stats_layout.addRow(t('callcryptor.sync.pending_sync'), QLabel(str(pending)))
        
        layout.addWidget(stats_group)
        
        # Opcje
        self.auto_sync_checkbox = QCheckBox(t('callcryptor.sync.auto_sync_every_5min'))
        self.auto_sync_checkbox.setChecked(self.sync_stats.get('auto_sync_enabled', False))
        layout.addWidget(self.auto_sync_checkbox)
        
        self.disable_sync_checkbox = QCheckBox(t('callcryptor.sync.disable_sync'))
        self.disable_sync_checkbox.setToolTip(t('callcryptor.sync.disable_sync_tooltip'))
        layout.addWidget(self.disable_sync_checkbox)
        
        layout.addStretch()
        
        # Przyciski
        buttons_layout = QHBoxLayout()
        buttons_layout.addStretch()
        
        close_btn = QPushButton(t('common.close'))
        close_btn.setMinimumWidth(120)
        close_btn.clicked.connect(self.reject)
        buttons_layout.addWidget(close_btn)
        
        sync_now_btn = QPushButton(t('callcryptor.sync.sync_now'))
        sync_now_btn.setMinimumWidth(150)
        sync_now_btn.clicked.connect(self._sync_now)
        sync_now_btn.setStyleSheet("background-color: #4CAF50; color: white;")
        buttons_layout.addWidget(sync_now_btn)
        
        layout.addLayout(buttons_layout)
    
    def _sync_now(self):
        """Rozpocznij synchronizację"""
        self.disable_sync = self.disable_sync_checkbox.isChecked()
        self.accept()
    
    def _apply_theme(self):
        """Zastosuj motyw"""
        if not self.theme_manager or not self.theme_manager.current_theme:
            return
        
        colors = self.theme_manager.get_current_colors()
        
        style = f"""
            QDialog {{
                background-color: {colors.get('background_primary', '#FFFFFF')};
                color: {colors.get('text_primary', '#000000')};
            }}
            QGroupBox {{
                border: 2px solid {colors.get('border_primary', '#E0E0E0')};
                border-radius: 8px;
                margin-top: 12px;
                padding-top: 15px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px;
            }}
        """
        self.setStyleSheet(style)


