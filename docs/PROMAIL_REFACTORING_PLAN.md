# Plan Refaktoryzacji Modułu ProMail

## Spis Treści
1. [Analiza Obecnego Stanu](#analiza-obecnego-stanu)
2. [Zakres Refaktoryzacji](#zakres-refaktoryzacji)
3. [Etapy Implementacji](#etapy-implementacji)
4. [Szczegółowe Zadania](#szczegółowe-zadania)
5. [Integracja z Aplikacją](#integracja-z-aplikacją)
6. [Checklisty Kontrolne](#checklisty-kontrolne)

---

## Analiza Obecnego Stanu

### Struktura Modułu
```
src/Modules/custom_modules/mail_client/
├── mail_view.py (4892 linii) - GŁÓWNY WIDOK - QMainWindow ❌
├── new_mail_window.py - Okno kompozycji maila - QDialog
├── mail_widgets.py - Niestandardowe widgety (MailTableWidget, FolderTreeWidget, etc.)
├── compose_widgets.py - Widgety do kompozycji
├── mail_config.py (1553 linii) - Dialog konfiguracji kont
├── mail_ai_panel.py - Panel AI i Truth Sources
├── mail_templates.py - Zarządzanie szablonami
├── document_manager.py - Menedżer dokumentów
├── favorites_manager.py - Zarządzanie ulubionymi
├── autoresponder.py - Autoresponder
├── queue_view.py - Widok kolejki maili
├── cache_integration.py - Integracja cache
├── mail_cache.py - System cache dla maili
└── password_crypto.py - Szyfrowanie haseł

Pliki JSON:
├── mail_accounts.json - Konta email (DANE WRAŻLIWE) 
├── mail_filters.json - Filtry maili
├── mail_templates.json - Szablony wiadomości
├── mail_signatures.json - Podpisy
├── favorite_files.json - Ulubione pliki
└── ai_truth_sources.json - Źródła prawdy AI
```

### Główne Problemy Zidentyfikowane

#### 1. **Architektura Widoku**
- ❌ `MailViewModule(QMainWindow)` - powinno być `QWidget`
- ❌ Brak integracji z ThemeManager
- ❌ Brak integracji z i18n Manager
- ❌ Wszystkie teksty hardcoded (polskie stringi w kodzie)
- ❌ Hardcoded kolory (50+ instancji kolorów hex)

#### 2. **Hardcoded Kolory** (Przykłady znalezione)
```python
# queue_view.py
"#FFEBEE", "#FFF3E0", "#FFF9C4", "#E8F5E9"  # Tła kart
"#0D47A1", "#212121", "#1A237E", "#424242"  # Kolory tekstów
"#4CAF50", "#EF6C00", "#B71C1C"             # Przyciski akcji

# mail_view.py  
"#9C27B0", "#7B1FA2", "#E91E63"             # Przyciski UI
"#607D8B", "#546E7A", "#2196F3"             # Toolbary

# new_mail_window.py
"#FFA726", "#FB8C00", "#F57C00"             # Przyciski szablonów
"#4CAF50", "#45a049", "#388E3C"             # Przyciski wysyłania
```

#### 3. **Hardcoded Teksty** (Przykłady)
```python
# Brak użycia t() - wszystkie teksty po polsku bezpośrednio w kodzie:
"Klient pocztowy"
"Nowy mail"
"Odpowiedz"
"Usuń"
"Ustawienia kont"
"Odebrane", "Wysłane", "Spam", "Koszt"
"Zapisz", "Anuluj", "Wyślij"
```

#### 4. **Zarządzanie Kontami Email**
- ❌ Przechowywane w `mail_accounts.json` (duplikacja danych)
- ✅ Aplikacja już ma system przechowywania kont w `user_settings.json`
- ❌ Dialog konfiguracji wymaga ręcznego wprowadzania danych
- **ROZWIĄZANIE**: Pobierać konta z `user_settings.json` zamiast własnego JSON

#### 5. **Brak Systemu Motywów**
- Brak `apply_theme()` method
- Brak `objectName` dla widgetów
- Inline `setStyleSheet()` zamiast QSS
- Kolory nie reagują na przełączanie light/dark

#### 6. **Brak Wielojęzyczności**
- Wszystkie stringi hardcoded po polsku
- Brak obsługi `language_changed` signal
- Brak `update_translations()` method

---

## Zakres Refaktoryzacji

### 1. Konwersja na QWidget
**Plik**: `mail_view.py`

**Zmiany**:
```python
# PRZED:
class MailViewModule(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Klient pocztowy")
        self.resize(1400, 900)
        # ... toolbar, statusbar, menubar

# PO:
class MailViewModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.i18n = get_i18n()
        
        self.init_ui()
        self.apply_theme()
        
        # Podłączenia
        self.theme_manager.theme_changed.connect(self.apply_theme)
        self.i18n.language_changed.connect(self.update_translations)
    
    def cleanup(self):
        """Cleanup przy zamykaniu widoku"""
        # Zatrzymaj wątki, zapisz dane
        pass
```

**Elementy do usunięcia**:
- `self.setWindowTitle()` → przeniesione do navigation_bar
- `self.resize()` → zarządzane przez main_window
- `QToolBar` → przeniesione do widgetu jako QHBoxLayout z przyciskami
- `QStatusBar` → QLabel na dole layoutu
- `QMenuBar` → menu kontekstowe lub przyciski w toolbar

### 2. Integracja ThemeManager

**Dodać do `mail_view.py`**:
```python
from src.utils.theme_manager import get_theme_manager

class MailViewModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        # ...
        
    def apply_theme(self):
        """Aplikuje aktualny motyw"""
        colors = self.theme_manager.get_current_colors()
        
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {colors['bg_main']};
                color: {colors['text_primary']};
            }}
            
            QTreeWidget {{
                background-color: {colors['bg_main']};
                border: 1px solid {colors['border_light']};
                alternate-background-color: {colors['bg_secondary']};
            }}
            
            QTableWidget {{
                background-color: {colors['bg_main']};
                gridline-color: {colors['border_light']};
            }}
            
            QTableWidget::item:selected {{
                background-color: {colors['accent_primary']};
                color: white;
            }}
            
            QPushButton#mail_new_btn {{
                background-color: {colors['accent_primary']};
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            
            QPushButton#mail_new_btn:hover {{
                background-color: {colors['accent_hover']};
            }}
            
            QPushButton#mail_delete_btn {{
                background-color: #d32f2f;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
            }}
            
            QPushButton#mail_delete_btn:hover {{
                background-color: #b71c1c;
            }}
            
            QTextEdit {{
                background-color: {colors['bg_main']};
                border: 1px solid {colors['border_light']};
                color: {colors['text_primary']};
            }}
            
            QLineEdit {{
                background-color: {colors['bg_main']};
                border: 1px solid {colors['border_light']};
                color: {colors['text_primary']};
                padding: 5px;
            }}
            
            QLabel#mail_status_label {{
                color: {colors['text_secondary']};
                padding: 4px;
            }}
        """)
```

**ObjectNames do dodania**:
```python
# Przyciski toolbar
self.new_mail_btn.setObjectName("mail_new_btn")
self.reply_btn.setObjectName("mail_reply_btn")
self.delete_btn.setObjectName("mail_delete_btn")
self.config_btn.setObjectName("mail_config_btn")

# Panele
self.folder_tree.setObjectName("mail_folder_tree")
self.mail_table.setObjectName("mail_table")
self.content_viewer.setObjectName("mail_content_viewer")

# Status label
self.status_label.setObjectName("mail_status_label")
```

**Kolory do Zmiany** (queue_view.py):
```python
# PRZED:
bg_color = "#FFEBEE"  # Czerwony
bg_color = "#FFF3E0"  # Pomarańczowy
bg_color = "#FFF9C4"  # Żółty
bg_color = "#E8F5E9"  # Zielony

# PO:
colors = self.theme_manager.get_current_colors()
# Używać kolorów z theme_manager lub zdefiniować paletę w JSON motywu:
bg_color_old = colors.get('queue_old', colors['bg_secondary'])
bg_color_medium = colors.get('queue_medium', colors['bg_main'])
bg_color_recent = colors.get('queue_recent', colors['accent_light'])
bg_color_new = colors.get('queue_new', colors['accent_primary'])
```

### 3. Integracja i18n Manager

**Dodać do `mail_view.py`**:
```python
from src.utils.i18n_manager import get_i18n, t

class MailViewModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.i18n = get_i18n()
        self.i18n.language_changed.connect(self.update_translations)
        # ...
        
    def update_translations(self):
        """Aktualizuje wszystkie teksty po zmianie języka"""
        # Przyciski toolbar
        if hasattr(self, 'new_mail_btn'):
            self.new_mail_btn.setText(t('promail.button.new_mail'))
        if hasattr(self, 'reply_btn'):
            self.reply_btn.setText(t('promail.button.reply'))
        if hasattr(self, 'delete_btn'):
            self.delete_btn.setText(t('promail.button.delete'))
        if hasattr(self, 'config_btn'):
            self.config_btn.setText(t('promail.button.settings'))
            
        # Foldery
        self.update_folder_labels()
        
        # Status bar
        if hasattr(self, 'status_label'):
            count = len(self.displayed_mails)
            self.status_label.setText(t('promail.status.mails_count', count=count))
```

**Tłumaczenia do dodania** (`resources/i18n/pl.json`):
```json
{
  "promail.title": "ProMail - Klient Pocztowy",
  "promail.subtitle": "Zaawansowany menedżer poczty email",
  
  "promail.button.new_mail": "Nowy mail",
  "promail.button.reply": "Odpowiedz",
  "promail.button.reply_all": "Odpowiedz wszystkim",
  "promail.button.forward": "Przekaż",
  "promail.button.delete": "Usuń",
  "promail.button.settings": "Ustawienia",
  "promail.button.refresh": "Odśwież",
  "promail.button.send": "Wyślij",
  "promail.button.save_draft": "Zapisz szkic",
  "promail.button.cancel": "Anuluj",
  "promail.button.attach": "Załącz",
  
  "promail.folder.inbox": "Odebrane",
  "promail.folder.sent": "Wysłane",
  "promail.folder.drafts": "Szkice",
  "promail.folder.spam": "Spam",
  "promail.folder.trash": "Kosz",
  "promail.folder.archive": "Archiwum",
  "promail.folder.favorites": "Ulubione",
  
  "promail.tab.folders": "Foldery",
  "promail.tab.favorites": "Ulubione",
  "promail.tab.recent": "Ostatnio używane",
  "promail.tab.templates": "Szablony",
  "promail.tab.ai": "Asystent AI",
  "promail.tab.queue": "Kolejka",
  
  "promail.status.mails_count": "{count} wiadomości",
  "promail.status.loading": "Ładowanie...",
  "promail.status.syncing": "Synchronizacja...",
  "promail.status.ready": "Gotowe",
  
  "promail.compose.to": "Do:",
  "promail.compose.cc": "DW:",
  "promail.compose.bcc": "UDW:",
  "promail.compose.subject": "Temat:",
  "promail.compose.body": "Treść wiadomości...",
  "promail.compose.from": "Z konta:",
  "promail.compose.attachments": "Załączniki",
  
  "promail.config.title": "Ustawienia kont email",
  "promail.config.accounts": "Konta",
  "promail.config.add_account": "Dodaj konto",
  "promail.config.edit_account": "Edytuj konto",
  "promail.config.remove_account": "Usuń konto",
  "promail.config.test_connection": "Testuj połączenie",
  
  "promail.filter.all": "Wszystkie",
  "promail.filter.unread": "Nieprzeczytane",
  "promail.filter.flagged": "Oznaczone",
  "promail.filter.attachments": "Z załącznikami",
  
  "promail.message.sent_success": "Wiadomość wysłana pomyślnie",
  "promail.message.draft_saved": "Szkic zapisany",
  "promail.message.deleted": "Wiadomość usunięta",
  "promail.message.moved_to_spam": "Przeniesiono do spamu",
  
  "promail.error.no_account": "Nie skonfigurowano żadnego konta email",
  "promail.error.connection_failed": "Nie udało się połączyć z serwerem",
  "promail.error.send_failed": "Wysyłanie nie powiodło się: {error}",
  "promail.error.load_failed": "Nie udało się załadować wiadomości",
  
  "promail.confirm.delete_mail": "Czy na pewno chcesz usunąć tę wiadomość?",
  "promail.confirm.delete_account": "Czy na pewno chcesz usunąć konto {email}?",
  "promail.confirm.mark_spam": "Oznaczyć jako spam i przenieść?",
  
  "promail.ai.analyze": "Analizuj AI",
  "promail.ai.summarize": "Podsumuj",
  "promail.ai.draft_reply": "Szkic odpowiedzi",
  "promail.ai.truth_sources": "Źródła prawdy",
  
  "promail.template.apply": "Zastosuj szablon",
  "promail.template.save": "Zapisz jako szablon",
  "promail.template.manage": "Zarządzaj szablonami",
  
  "promail.queue.title": "Kolejka maili do odpowiedzi",
  "promail.queue.filter_time": "Filtruj według czasu",
  "promail.queue.replied": "Odpisano",
  "promail.queue.no_reply": "Nie odpisywać",
  "promail.queue.spam": "Spam",
  "promail.queue.add_note": "Dodaj notatkę"
}
```

### 4. Refaktoryzacja Zarządzania Kontami

**Problem**: Duplikacja danych - konta email przechowywane zarówno w `mail_accounts.json` jak i `user_settings.json`.

**Rozwiązanie**: Usunąć `mail_accounts.json`, pobierać dane z `user_settings.json`.

**Struktura `user_settings.json`**:
```json
{
  "user": {
    "name": "Jan Kowalski",
    "email": "jan@example.com"
  },
  "email_accounts": [
    {
      "name": "Konto główne",
      "email": "jan@example.com",
      "password": "encrypted_password",
      "imap_server": "imap.gmail.com",
      "imap_port": 993,
      "imap_ssl": true,
      "smtp_server": "smtp.gmail.com",
      "smtp_port": 587,
      "smtp_ssl": true,
      "signature": "Pozdrawiam,\nJan Kowalski"
    },
    {
      "name": "Konto firmowe",
      "email": "jkowalski@firma.pl",
      "password": "encrypted_password",
      "imap_server": "mail.firma.pl",
      "imap_port": 993,
      "imap_ssl": true,
      "smtp_server": "mail.firma.pl",
      "smtp_port": 587,
      "smtp_ssl": true
    }
  ]
}
```

**Zmiany w kodzie**:
```python
# PRZED (mail_view.py):
self.accounts_file = Path("mail_client/mail_accounts.json")
self.mail_accounts = self.load_mail_accounts()

def load_mail_accounts(self):
    if self.accounts_file.exists():
        with open(self.accounts_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# PO:
from src.config import Config

class MailViewModule(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.config = Config()
        self.mail_accounts = self.config.get_email_accounts()
        
    def get_email_accounts(self):
        """Pobiera konta email z user_settings.json"""
        settings = self.config.load_settings()
        return settings.get('email_accounts', [])
```

**Zmiany w `mail_config.py`**:
```python
# PRZED:
class MailConfigDialog(QDialog):
    def __init__(self, parent=None, accounts_file=None):
        # ... inicjalizacja dialogu konfiguracji
        # Pola do ręcznego wprowadzania WSZYSTKICH danych
        
# PO:
class MailConfigDialog(QDialog):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config = config_manager or Config()
        
        # Pobierz istniejące konta
        self.accounts = self.config.get_email_accounts()
        
        # UI: Lista kont + przyciski Dodaj/Edytuj/Usuń
        # Przy dodawaniu/edycji - dialog z polami:
        # - Wybór istniejącego email z user_settings (dropdown)
        # - ALBO ręczne wprowadzenie nowego konta
        # - Hasło (szyfrowane)
        # - Serwery IMAP/SMTP (autouzupełnianie dla znanych dostawców)
        
    def save_accounts(self):
        """Zapisuje konta do user_settings.json"""
        settings = self.config.load_settings()
        settings['email_accounts'] = self.accounts
        self.config.save_settings(settings)
```

---

## Etapy Implementacji

### **ETAP 1: Przygotowanie Struktury** (2-3h)
**Cel**: Utworzenie kopii modułu i przygotowanie infrastruktury

**Zadania**:
1. ✅ Utworzyć kopię `mail_client` → `mail_client_backup`
2. ✅ Dodać import ThemeManager do `mail_view.py`
3. ✅ Dodać import i18n Manager do `mail_view.py`
4. ✅ Utworzyć plik `promail.json` w `resources/i18n/pl.json` (sekcja promail.*)
5. ✅ Przygotować listę wszystkich hardcoded stringów do tłumaczenia

**Rezultat**: Infrastruktura gotowa, oryginał zabezpieczony

---

### **ETAP 2: Konwersja na QWidget** (4-5h)
**Cel**: Zmienić `MailViewModule(QMainWindow)` → `MailViewModule(QWidget)`

**Zadania**:
1. ✅ Zmienić dziedziczenie klasy
   ```python
   # PRZED:
   class MailViewModule(QMainWindow):
   
   # PO:
   class MailViewModule(QWidget):
   ```

2. ✅ Usunąć wszystkie metody specyficzne dla QMainWindow:
   - `self.setWindowTitle()` → usuń
   - `self.resize()` → usuń
   - `self.statusBar()` → zamień na `QLabel` w layoutcie
   - `self.menuBar()` → zamień na menu kontekstowe lub usuń
   - `self.toolBar()` → zamień na `QHBoxLayout` z przyciskami

3. ✅ Zmienić layout główny:
   ```python
   # PRZED:
   central_widget = QWidget()
   self.setCentralWidget(central_widget)
   layout = QVBoxLayout(central_widget)
   
   # PO:
   main_layout = QVBoxLayout(self)
   main_layout.setContentsMargins(0, 0, 0, 0)
   ```

4. ✅ Dodać metodę `cleanup()`:
   ```python
   def cleanup(self):
       """Cleanup przy zamykaniu widoku"""
       # Zatrzymaj wątki
       if hasattr(self, 'email_fetcher') and self.email_fetcher:
           self.email_fetcher.quit()
           self.email_fetcher.wait()
       
       # Zapisz stan
       self.save_state()
       
       # Odłącz sygnały
       try:
           self.theme_manager.theme_changed.disconnect(self.apply_theme)
           self.i18n.language_changed.disconnect(self.update_translations)
       except:
           pass
   ```

5. ✅ Toolbar → Panel przycisków:
   ```python
   # PRZED:
   toolbar = QToolBar("Main toolbar")
   self.addToolBar(toolbar)
   toolbar.addAction(new_action)
   
   # PO:
   toolbar_layout = QHBoxLayout()
   
   self.new_mail_btn = QPushButton(t('promail.button.new_mail'))
   self.new_mail_btn.setObjectName("mail_new_btn")
   self.new_mail_btn.clicked.connect(self.compose_new_mail)
   toolbar_layout.addWidget(self.new_mail_btn)
   
   # ...więcej przycisków
   toolbar_layout.addStretch()
   
   main_layout.addLayout(toolbar_layout)
   ```

6. ✅ Status bar → Status label:
   ```python
   # PRZED:
   self.statusBar().showMessage("Gotowe")
   
   # PO:
   self.status_label = QLabel(t('promail.status.ready'))
   self.status_label.setObjectName("mail_status_label")
   main_layout.addWidget(self.status_label)
   ```

**Rezultat**: Moduł działa jako QWidget, gotowy do integracji z main_window

---

### **ETAP 3: Integracja ThemeManager** (5-6h)
**Cel**: Usunąć wszystkie hardcoded kolory, zastąpić systemem motywów

**Zadania**:

**3.1. Dodać apply_theme() method** (mail_view.py)
```python
def apply_theme(self):
    """Aplikuje aktualny motyw"""
    colors = self.theme_manager.get_current_colors()
    
    # Główny stylesheet z QSS
    self.setStyleSheet(f"""
        /* ... pełny QSS jak w sekcji "Integracja ThemeManager" ... */
    """)
    
    # Przekaż motyw do sub-widgetów
    if hasattr(self, 'queue_view'):
        self.queue_view.apply_theme()
    if hasattr(self, 'ai_panel'):
        self.ai_panel.apply_theme()
```

**3.2. Dodać objectName do wszystkich widgetów**
```python
# Przyciski
self.new_mail_btn.setObjectName("mail_new_btn")
self.reply_btn.setObjectName("mail_reply_btn")
self.delete_btn.setObjectName("mail_delete_btn")

# Panele
self.folder_tree.setObjectName("mail_folder_tree")
self.mail_table.setObjectName("mail_table")
self.content_viewer.setObjectName("mail_content_viewer")

# Labels
self.status_label.setObjectName("mail_status_label")
```

**3.3. Usunąć wszystkie inline setStyleSheet() w:**
- `mail_view.py` - ~20 instancji
- `queue_view.py` - ~15 instancji
- `new_mail_window.py` - ~10 instancji
- `mail_widgets.py` - ~5 instancji

**3.4. Dodać apply_theme() do submodułów:**

**queue_view.py**:
```python
class QueueView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        # ...
        
    def apply_theme(self):
        colors = self.theme_manager.get_current_colors()
        
        # Użyj kolorów motywu zamiast hardcoded
        # Zmapuj stare kolory na nowe:
        # #FFEBEE → colors.get('queue_old', '#FFEBEE')
        # #E8F5E9 → colors.get('queue_new', '#E8F5E9')
```

**new_mail_window.py**:
```python
class NewMailWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.theme_manager = get_theme_manager()
        self.apply_theme()
        
    def apply_theme(self):
        colors = self.theme_manager.get_current_colors()
        # Zastosuj kolory do przycisków, pól tekstowych, etc.
```

**3.5. Podłączyć theme_changed signal**
```python
def __init__(self, parent=None):
    super().__init__(parent)
    self.theme_manager = get_theme_manager()
    # ...
    self.theme_manager.theme_changed.connect(self.apply_theme)
```

**Rezultat**: Wszystkie kolory pochodzą z ThemeManager, moduł reaguje na zmianę motywu

---

### **ETAP 4: Integracja i18n** (6-8h)
**Cel**: Usunąć wszystkie hardcoded stringi, zastąpić tłumaczeniami

**Zadania**:

**4.1. Dodać wszystkie tłumaczenia do `pl.json`**
- Skopiować sekcję promail.* z przykładów w tym dokumencie
- Rozszerzyć o brakujące stringi (~200 kluczy)

**4.2. Zamienić wszystkie hardcoded stringi na t()**

Przykłady zmian:
```python
# PRZED:
self.new_mail_btn = QPushButton("Nowy mail")
folder_item.setText(0, "Odebrane")
status_bar.showMessage("Gotowe")

# PO:
self.new_mail_btn = QPushButton(t('promail.button.new_mail'))
folder_item.setText(0, t('promail.folder.inbox'))
self.status_label.setText(t('promail.status.ready'))
```

**4.3. Dodać update_translations() method**
```python
def update_translations(self):
    """Aktualizuje wszystkie teksty po zmianie języka"""
    # Przyciski
    if hasattr(self, 'new_mail_btn'):
        self.new_mail_btn.setText(t('promail.button.new_mail'))
    if hasattr(self, 'reply_btn'):
        self.reply_btn.setText(t('promail.button.reply'))
    # ... wszystkie inne widgety
    
    # Foldery w drzewie
    self.update_folder_labels()
    
    # Odśwież listę maili (jeśli są wyświetlane)
    if self.displayed_mails:
        self.display_mails(self.displayed_mails)
```

**4.4. Podłączyć language_changed signal**
```python
self.i18n = get_i18n()
self.i18n.language_changed.connect(self.update_translations)
```

**4.5. Przetłumaczyć submoduły:**
- `mail_config.py` - dialog konfiguracji
- `new_mail_window.py` - okno kompozycji
- `queue_view.py` - widok kolejki
- `mail_templates.py` - szablony
- `mail_ai_panel.py` - panel AI

**Rezultat**: Wszystkie teksty pochodzą z systemu tłumaczeń, moduł wspiera wielojęzyczność

---

### **ETAP 5: Refaktoryzacja Zarządzania Kontami** (4-5h)
**Cel**: Usunąć `mail_accounts.json`, pobierać dane z `user_settings.json`

**Zadania**:

**5.1. Rozszerzyć Config class** (src/config.py)
```python
class Config:
    # ...
    
    def get_email_accounts(self) -> List[Dict[str, Any]]:
        """Pobiera listę kont email"""
        settings = self.load_settings()
        return settings.get('email_accounts', [])
    
    def save_email_accounts(self, accounts: List[Dict[str, Any]]):
        """Zapisuje konta email"""
        settings = self.load_settings()
        settings['email_accounts'] = accounts
        self.save_settings(settings)
    
    def add_email_account(self, account: Dict[str, Any]):
        """Dodaje nowe konto email"""
        accounts = self.get_email_accounts()
        accounts.append(account)
        self.save_email_accounts(accounts)
    
    def remove_email_account(self, email: str):
        """Usuwa konto email"""
        accounts = self.get_email_accounts()
        accounts = [acc for acc in accounts if acc.get('email') != email]
        self.save_email_accounts(accounts)
```

**5.2. Zmienić mail_view.py**
```python
# PRZED:
self.accounts_file = Path("mail_client/mail_accounts.json")
self.mail_accounts = self.load_mail_accounts()

def load_mail_accounts(self):
    if self.accounts_file.exists():
        with open(self.accounts_file, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# PO:
from src.config import Config

def __init__(self, parent=None):
    super().__init__(parent)
    self.config = Config()
    self.mail_accounts = self.config.get_email_accounts()
```

**5.3. Zrefaktoryzować mail_config.py**
```python
class MailConfigDialog(QDialog):
    def __init__(self, parent=None, config_manager=None):
        super().__init__(parent)
        self.config = config_manager or Config()
        self.theme_manager = get_theme_manager()
        self.i18n = get_i18n()
        
        # Załaduj konta z user_settings.json
        self.accounts = self.config.get_email_accounts()
        
        self.init_ui()
        self.apply_theme()
        self.update_translations()
        
    def init_ui(self):
        # Lista kont
        self.accounts_list = QListWidget()
        self.accounts_list.setObjectName("mail_accounts_list")
        
        # Przyciski
        add_btn = QPushButton(t('promail.config.add_account'))
        add_btn.setObjectName("mail_config_add_btn")
        add_btn.clicked.connect(self.add_account)
        
        edit_btn = QPushButton(t('promail.config.edit_account'))
        edit_btn.setObjectName("mail_config_edit_btn")
        edit_btn.clicked.connect(self.edit_account)
        
        remove_btn = QPushButton(t('promail.config.remove_account'))
        remove_btn.setObjectName("mail_config_remove_btn")
        remove_btn.clicked.connect(self.remove_account)
        
        # ...
        
    def add_account(self):
        """Dialog dodawania nowego konta"""
        dialog = AccountEditDialog(parent=self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            account = dialog.get_account_data()
            self.config.add_email_account(account)
            self.load_accounts()  # Odśwież listę
    
    def save_accounts(self):
        """Zapisuje konta do user_settings.json"""
        self.config.save_email_accounts(self.accounts)
```

**5.4. Migracja danych**
```python
def migrate_mail_accounts():
    """Migruje konta z mail_accounts.json do user_settings.json"""
    old_file = Path("mail_client/mail_accounts.json")
    
    if not old_file.exists():
        return
    
    # Wczytaj stare konta
    with open(old_file, 'r', encoding='utf-8') as f:
        old_accounts = json.load(f)
    
    # Zapisz do nowego systemu
    config = Config()
    existing = config.get_email_accounts()
    
    for account in old_accounts:
        # Sprawdź czy konto już istnieje
        if not any(acc['email'] == account['email'] for acc in existing):
            config.add_email_account(account)
    
    # Backup starego pliku i usuń
    old_file.rename(old_file.with_suffix('.json.backup'))
    print(f"Migracja zakończona. Backup: {old_file.with_suffix('.json.backup')}")
```

**Rezultat**: Konta email zarządzane centralnie w `user_settings.json`, bez duplikacji

---

### **ETAP 6: Integracja z Main Window** (2-3h)
**Cel**: Zintegrować ProMail z główną aplikacją

**Zadania**:

**6.1. Dodać import do main_window.py**
```python
# main_window.py (około linii 30-35)
from src.Modules.custom_modules.mail_client.mail_view import MailViewModule
```

**6.2. Utworzyć widok w content_stack**
```python
# main_window.py w metodzie __init__ (około linii 900)
try:
    self.promail_view = MailViewModule()
    self.content_stack.addWidget(self.promail_view)
    logger.info("ProMail view initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize ProMail view: {e}")
    # Fallback - pusty widget
    self.promail_view = QWidget()
    error_label = QLabel(f"Błąd inicjalizacji ProMail: {str(e)}")
    error_layout = QVBoxLayout(self.promail_view)
    error_layout.addWidget(error_label)
    self.content_stack.addWidget(self.promail_view)
```

**6.3. Dodać obsługę przełączania widoku**
```python
# main_window.py w metodzie switch_view (około linii 1140)
elif view_name == 'promail':
    self.content_stack.setCurrentWidget(self.promail_view)
    if hasattr(self.promail_view, 'update_stats'):
        self.promail_view.update_stats()
    if hasattr(self.promail_view, 'refresh_folders'):
        self.promail_view.refresh_folders()
```

**6.4. Dodać cleanup w closeEvent**
```python
# main_window.py w metodzie closeEvent (około linii 1750)
if hasattr(self, 'promail_view') and hasattr(self.promail_view, 'cleanup'):
    try:
        self.promail_view.cleanup()
        logger.info("ProMail view cleaned up successfully")
    except Exception as e:
        logger.error(f"Error cleaning up ProMail view: {e}")
```

**6.5. Zaktualizować config_view.py**
```python
# config_view.py (około linii 890)
{
    'id': 'promail',
    'label': 'ProMail',
    'description': 'Zaawansowany klient pocztowy',
    'visible': True,
    'locked': False
}
```

**6.6. Migracja danych kont (jednorazowo)**
```python
# main.py - przed utworzeniem app
from src.Modules.custom_modules.mail_client.mail_view import migrate_mail_accounts

# Migruj konta przy pierwszym uruchomieniu
try:
    migrate_mail_accounts()
except Exception as e:
    logger.warning(f"Mail accounts migration failed: {e}")
```

**Rezultat**: ProMail w pełni zintegrowane z aplikacją, dostępne z navigation_bar

---

### **ETAP 7: Testy i Optymalizacja** (3-4h)
**Cel**: Przetestować wszystkie funkcje, naprawić błędy, zoptymalizować wydajność

**Zadania**:

**7.1. Testy Funkcjonalne**
- ✅ Otwieranie modułu z navigation_bar
- ✅ Przełączanie motywów (light/dark)
- ✅ Przełączanie języków (pl/en)
- ✅ Dodawanie/edycja/usuwanie kont email
- ✅ Synchronizacja z serwerami IMAP
- ✅ Wysyłanie maili
- ✅ Odpowiadanie/przekazywanie
- ✅ Zarządzanie folderami
- ✅ Kolejka maili
- ✅ Szablony
- ✅ Panel AI
- ✅ Ulubione pliki

**7.2. Testy Wydajnościowe**
- ✅ Czas ładowania modułu < 2s
- ✅ Synchronizacja 100 maili < 5s
- ✅ Przełączanie motywów < 0.5s
- ✅ Wyszukiwanie w 1000 maili < 1s

**7.3. Testy Kompatybilności**
- ✅ Działanie z wieloma kontami (3+)
- ✅ Duże załączniki (>10MB)
- ✅ Różne serwery (Gmail, Outlook, Exchange)
- ✅ Obsługa błędów połączenia

**7.4. Optymalizacje**
```python
# Cache dla często używanych danych
self._email_parse_cache = {}
self._folder_cache = {}
self._mail_index = {}

# Lazy loading folderów
def load_folder_contents(self, folder_name):
    if folder_name in self._folder_cache:
        return self._folder_cache[folder_name]
    
    # Pobierz z serwera
    mails = self.fetch_folder_mails(folder_name)
    self._folder_cache[folder_name] = mails
    return mails

# Paginacja dla dużych list
MAX_MAILS_PER_PAGE = 50

def display_mails(self, mails):
    # Wyświetl tylko pierwszą stronę
    page_mails = mails[:MAX_MAILS_PER_PAGE]
    self.populate_mail_table(page_mails)
    
    if len(mails) > MAX_MAILS_PER_PAGE:
        self.show_pagination_controls(len(mails))
```

**Rezultat**: Stabilny, szybki, w pełni funkcjonalny moduł ProMail

---

## Szczegółowe Zadania

### Lista Wszystkich Plików do Modyfikacji

#### Główne Pliki (WYMAGANE ZMIANY)
1. ✅ **mail_view.py** (4892 linii)
   - Zmiana dziedziczenia: QMainWindow → QWidget
   - Dodanie ThemeManager integration
   - Dodanie i18n integration
   - Usunięcie toolbar/statusbar/menubar
   - Dodanie apply_theme() method
   - Dodanie update_translations() method
   - Dodanie cleanup() method
   - Zmiana zarządzania kontami (Config zamiast JSON)
   - Zmiana ~50 hardcoded kolorów
   - Zmiana ~200 hardcoded stringów

2. ✅ **mail_config.py** (1553 linii)
   - Integracja z Config class
   - Usunięcie mail_accounts.json dependency
   - Dodanie apply_theme()
   - Dodanie update_translations()
   - Zmiana ~20 hardcoded kolorów
   - Zmiana ~50 hardcoded stringów

3. ✅ **new_mail_window.py**
   - Dodanie apply_theme()
   - Dodanie update_translations()
   - Zmiana ~15 hardcoded kolorów
   - Zmiana ~40 hardcoded stringów

4. ✅ **queue_view.py**
   - Dodanie apply_theme()
   - Dodanie update_translations()
   - Zmiana ~20 hardcoded kolorów (tła kart, przyciski)
   - Zmiana ~30 hardcoded stringów

5. ✅ **mail_widgets.py**
   - Dodanie apply_theme() do każdej klasy widgetu
   - Usunięcie inline setStyleSheet()
   - Dodanie objectName do widgetów

6. ✅ **mail_ai_panel.py**
   - Dodanie apply_theme()
   - Dodanie update_translations()
   - Zmiana ~10 hardcoded kolorów
   - Zmiana ~25 hardcoded stringów

7. ✅ **mail_templates.py**
   - Dodanie apply_theme()
   - Dodanie update_translations()
   - Zmiana ~15 hardcoded stringów

#### Pliki Wspomagające (OPCJONALNE ZMIANY)
8. ⚠️ **compose_widgets.py**
   - Dodanie apply_theme() do widgetów
   - Update kolorów

9. ⚠️ **document_manager.py**
   - Dodanie apply_theme()
   - Dodanie update_translations()

10. ⚠️ **favorites_manager.py**
    - Dodanie apply_theme()
    - Dodanie update_translations()

11. ⚠️ **autoresponder.py**
    - Dodanie update_translations()

#### Pliki Infrastruktury (BEZ ZMIAN)
- ✅ **password_crypto.py** - bez zmian (logika szyfrowania)
- ✅ **mail_cache.py** - bez zmian (system cache)
- ✅ **cache_integration.py** - bez zmian (integracja cache)

#### Pliki JSON do Zmiany
- ❌ **mail_accounts.json** → USUNĄĆ (migracja do user_settings.json)
- ✅ **mail_filters.json** - bez zmian
- ✅ **mail_templates.json** - bez zmian
- ✅ **mail_signatures.json** - bez zmian
- ✅ **favorite_files.json** - bez zmian
- ✅ **ai_truth_sources.json** - bez zmian

---

## Integracja z Aplikacją

### 1. Dodanie do main_window.py
```python
# Import
from src.Modules.custom_modules.mail_client.mail_view import MailViewModule

# W __init__ (content_stack)
try:
    self.promail_view = MailViewModule()
    self.content_stack.addWidget(self.promail_view)
    logger.info("ProMail view initialized")
except Exception as e:
    logger.error(f"ProMail init failed: {e}")
    self.promail_view = QWidget()
    self.content_stack.addWidget(self.promail_view)

# W switch_view
elif view_name == 'promail':
    self.content_stack.setCurrentWidget(self.promail_view)
    if hasattr(self.promail_view, 'refresh_folders'):
        self.promail_view.refresh_folders()

# W closeEvent
if hasattr(self, 'promail_view'):
    self.promail_view.cleanup()
```

### 2. Dodanie do config_view.py
```python
{
    'id': 'promail',
    'label': 'ProMail',
    'description': 'Zaawansowany klient pocztowy z AI',
    'visible': True,
    'locked': False
}
```

### 3. Dodanie do resources/i18n/pl.json
```json
{
  "promail.title": "ProMail - Klient Pocztowy",
  // ... ~200 kluczy tłumaczeń (patrz sekcja "Integracja i18n")
}
```

### 4. Rozszerzenie Config class (src/config.py)
```python
def get_email_accounts(self) -> List[Dict[str, Any]]:
    settings = self.load_settings()
    return settings.get('email_accounts', [])

def save_email_accounts(self, accounts: List[Dict[str, Any]]):
    settings = self.load_settings()
    settings['email_accounts'] = accounts
    self.save_settings(settings)
```

---

## Checklisty Kontrolne

### ✅ Checklist Etap 1: Przygotowanie
- [ ] Utworzono backup `mail_client_backup`
- [ ] Dodano import ThemeManager
- [ ] Dodano import i18n Manager
- [ ] Utworzono sekcję promail.* w pl.json
- [ ] Zidentyfikowano wszystkie hardcoded stringi
- [ ] Zidentyfikowano wszystkie hardcoded kolory

### ✅ Checklist Etap 2: Konwersja QWidget
- [ ] Zmieniono `QMainWindow` → `QWidget`
- [ ] Usunięto `setWindowTitle()`
- [ ] Usunięto `resize()`
- [ ] Zamieniono `QToolBar` → `QHBoxLayout`
- [ ] Zamieniono `QStatusBar` → `QLabel`
- [ ] Usunięto `QMenuBar` (lub zamieniono na context menu)
- [ ] Layout główny używa `QVBoxLayout(self)`
- [ ] Dodano metodę `cleanup()`
- [ ] Moduł uruchamia się bez błędów jako QWidget
- [ ] Wszystkie funkcje działają poprawnie

### ✅ Checklist Etap 3: ThemeManager
- [ ] Dodano `get_theme_manager()` import
- [ ] Dodano `self.theme_manager` w `__init__`
- [ ] Utworzono metodę `apply_theme()`
- [ ] Dodano `objectName` do wszystkich głównych widgetów
- [ ] Usunięto wszystkie inline `setStyleSheet()` z mail_view.py
- [ ] Usunięto wszystkie inline `setStyleSheet()` z queue_view.py
- [ ] Usunięto wszystkie inline `setStyleSheet()` z new_mail_window.py
- [ ] Usunięto wszystkie inline `setStyleSheet()` z mail_widgets.py
- [ ] Podłączono `theme_changed.connect(self.apply_theme)`
- [ ] Przełączanie motywów działa (light/dark)
- [ ] Wszystkie widgety reagują na zmianę motywu

### ✅ Checklist Etap 4: i18n
- [ ] Dodano wszystkie klucze promail.* do pl.json (~200 kluczy)
- [ ] Zamieniono wszystkie hardcoded stringi na `t()` w mail_view.py
- [ ] Zamieniono wszystkie hardcoded stringi na `t()` w mail_config.py
- [ ] Zamieniono wszystkie hardcoded stringi na `t()` w new_mail_window.py
- [ ] Zamieniono wszystkie hardcoded stringi na `t()` w queue_view.py
- [ ] Zamieniono wszystkie hardcoded stringi na `t()` w mail_templates.py
- [ ] Zamieniono wszystkie hardcoded stringi na `t()` w mail_ai_panel.py
- [ ] Utworzono metodę `update_translations()`
- [ ] Podłączono `language_changed.connect(self.update_translations)`
- [ ] Przełączanie języków działa poprawnie
- [ ] Wszystkie teksty aktualizują się po zmianie języka

### ✅ Checklist Etap 5: Zarządzanie Kontami
- [ ] Rozszerzono Config class (get/save_email_accounts)
- [ ] Zmieniono mail_view.py na używanie Config
- [ ] Zrefaktoryzowano mail_config.py
- [ ] Utworzono funkcję `migrate_mail_accounts()`
- [ ] Uruchomiono migrację danych
- [ ] Usunięto dependency na mail_accounts.json
- [ ] Konta zapisują się w user_settings.json
- [ ] Dodawanie nowych kont działa
- [ ] Edycja kont działa
- [ ] Usuwanie kont działa

### ✅ Checklist Etap 6: Integracja Main Window
- [ ] Dodano import MailViewModule do main_window.py
- [ ] Utworzono self.promail_view w content_stack
- [ ] Dodano obsługę view_name=='promail' w switch_view
- [ ] Dodano cleanup() w closeEvent
- [ ] Zaktualizowano config_view.py (visible=True)
- [ ] Uruchomiono migrację kont (jednorazowo)
- [ ] Moduł pojawia się w navigation_bar
- [ ] Kliknięcie przycisku otwiera ProMail
- [ ] Przełączanie między modułami działa
- [ ] Zamknięcie aplikacji wywołuje cleanup()

### ✅ Checklist Etap 7: Testy
- [ ] Moduł otwiera się < 2s
- [ ] Przełączanie motywów działa (light/dark)
- [ ] Przełączanie języków działa (pl/en)
- [ ] Dodawanie kont działa
- [ ] Synchronizacja IMAP działa
- [ ] Wysyłanie maili działa
- [ ] Odpowiadanie działa
- [ ] Kolejka maili działa
- [ ] Szablony działają
- [ ] Panel AI działa
- [ ] Brak błędów w logach
- [ ] Brak memory leaks

---

## Podsumowanie

### Szacowany Czas Całkowitej Refaktoryzacji
- **Etap 1**: 2-3h
- **Etap 2**: 4-5h
- **Etap 3**: 5-6h
- **Etap 4**: 6-8h
- **Etap 5**: 4-5h
- **Etap 6**: 2-3h
- **Etap 7**: 3-4h

**RAZEM**: 26-34 godzin pracy

### Priorytety
1. **WYSOKI**: Etap 1-2 (Przygotowanie + Konwersja QWidget) - konieczne do integracji
2. **WYSOKI**: Etap 3 (ThemeManager) - kluczowe dla spójności UI
3. **ŚREDNI**: Etap 4 (i18n) - ważne dla UX
4. **WYSOKI**: Etap 5 (Konta) - eliminuje duplikację danych
5. **KRYTYCZNY**: Etap 6 (Integracja) - bez tego moduł nie działa
6. **ŚREDNI**: Etap 7 (Testy) - zapewnia stabilność

### Kolejność Wykonania (Zalecana)
```
1. Etap 1 → Backup i przygotowanie infrastruktury
2. Etap 2 → Konwersja na QWidget
3. Etap 6 → Integracja z main_window (wczesne testy)
4. Etap 3 → ThemeManager (wizualna spójność)
5. Etap 5 → Zarządzanie kontami (eliminacja duplikacji)
6. Etap 4 → i18n (wielojęzyczność)
7. Etap 7 → Testy i optymalizacja
```

### Ryzyka i Wyzwania
1. ⚠️ **Duży rozmiar kodu** (4892 linii w mail_view.py) - możliwe trudności w refaktoryzacji
2. ⚠️ **Wiele zależności** - 14 plików .py + 6 plików JSON
3. ⚠️ **Złożona logika IMAP/SMTP** - ostrożność przy zmianach
4. ⚠️ **Migracja danych** - ryzyko utraty danych kont email
5. ⚠️ **Cache system** - może wymagać aktualizacji po zmianach

### Mitygacje Ryzyk
1. ✅ **Backup kompletny** przed każdym etapem
2. ✅ **Testy po każdym etapie** - nie kontynuować jeśli coś nie działa
3. ✅ **Migracja z backupem** - zachować mail_accounts.json.backup
4. ✅ **Stopniowe zmiany** - nie zmieniać wszystkiego naraz
5. ✅ **Logi szczegółowe** - łatwiejsze debugowanie

---

**Dokument utworzony**: 2025-11-10  
**Wersja**: 1.0  
**Autor**: Plan refaktoryzacji modułu ProMail dla aplikacji PRO-Ka-Po  
**Status**: Gotowy do implementacji
