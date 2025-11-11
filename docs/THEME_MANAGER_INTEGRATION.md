# Integracja Modułów z ThemeManager

## Spis Treści
1. [Przegląd Systemu Motywów](#przegląd-systemu-motywów)
2. [Architektura ThemeManager](#architektura-thememanager)
3. [Jak Działa System Motywów](#jak-działa-system-motywów)
4. [Integracja Krok po Kroku](#integracja-krok-po-kroku)
5. [Przykłady Implementacji](#przykłady-implementacji)
6. [Najlepsze Praktyki](#najlepsze-praktyki)
7. [Troubleshooting](#troubleshooting)

---

## Przegląd Systemu Motywów

### Co to jest ThemeManager?
ThemeManager to centralny system zarządzania motywami wizualnymi aplikacji. Obsługuje:
- **Built-in motywy**: `light.qss`, `dark.qss` (predefiniowane)
- **Niestandardowe motywy**: Utworzone przez użytkownika w `resources/themes/custom/`
- **Dual-layout system**: Dwa niezależne schematy kolorystyczne (Layout 1 i Layout 2)
- **Dynamiczne przełączanie**: Natychmiastowa zmiana motywu bez restartu aplikacji

### Struktura Folderów
```
resources/
└── themes/
    ├── light.qss           # Built-in jasny motyw
    ├── dark.qss            # Built-in ciemny motyw
    └── custom/             # Motywy użytkownika
        ├── mojmotyw.qss    # Plik stylu QSS
        ├── mojmotyw.json   # Definicja kolorów (opcjonalne)
        └── mojmotyw_metadata.json  # Metadane (opcjonalne)
```

### Kluczowe Pojęcia

#### 1. Layout (Układ)
Aplikacja posiada **2 niezależne układy**, które mogą mieć różne schematy kolorów:
- **Layout 1**: Domyślnie jasny motyw (`light`)
- **Layout 2**: Domyślnie ciemny motyw (`dark`)

Użytkownik może przełączać się między układami bez utraty konfiguracji.

#### 2. Color Scheme (Schemat Kolorów)
Konkretny motyw przypisany do układu. Może być:
- Built-in: `light`, `dark`
- Custom: `⭐ Nazwa_Motywu` (z prefiksem gwiazdki)

#### 3. Plik JSON Motywu
Opcjonalny plik definiujący kolory do użycia w kodzie Python:
```json
{
  "name": "mojmotyw",
  "colors": {
    "bg_main": "#FFFFFF",
    "bg_secondary": "#F5F5F5",
    "text_primary": "#2C3E50",
    "text_secondary": "#7F8C8D",
    "accent_primary": "#FF9800",
    "accent_hover": "#F57C00",
    "border_light": "#DDD",
    "checkbox_checked": "#4CAF50"
  }
}
```

---

## Architektura ThemeManager

### Singleton Pattern
ThemeManager jest singletonem dostępnym globalnie:

```python
from src.utils.theme_manager import get_theme_manager

theme_manager = get_theme_manager()
```

### Kluczowe Metody

#### `get_available_themes() -> list[str]`
Zwraca listę wszystkich dostępnych motywów:
```python
themes = theme_manager.get_available_themes()
# Wynik: ['light', 'dark', '⭐ test1', '⭐ mojmotyw']
```

#### `apply_theme(theme_name: str) -> bool`
Aplikuje motyw do całej aplikacji:
```python
success = theme_manager.apply_theme('dark')
```

#### `get_current_colors() -> dict`
Zwraca słownik kolorów aktualnego motywu:
```python
colors = theme_manager.get_current_colors()
bg_color = colors.get('bg_main', '#FFFFFF')
```

#### `set_layout_scheme(layout_number: int, scheme_name: str)`
Przypisuje schemat do układu:
```python
theme_manager.set_layout_scheme(1, 'light')
theme_manager.set_layout_scheme(2, 'dark')
```

#### `apply_layout(layout_number: int)`
Przełącza na konkretny układ:
```python
theme_manager.apply_layout(1)  # Przełącz na Layout 1
```

#### `toggle_layout() -> int`
Przełącza między Layout 1 a 2:
```python
new_layout = theme_manager.toggle_layout()
```

#### `get_current_layout() -> int`
Zwraca numer aktualnego układu:
```python
current = theme_manager.get_current_layout()  # 1 lub 2
```

---

## Jak Działa System Motywów

### 1. Inicjalizacja w main.py
```python
from src.utils.theme_manager import ThemeManager

# Utworzenie ThemeManager
theme_manager = ThemeManager()

# Wczytaj ustawienia użytkownika
settings = load_settings()
layout1_scheme = settings.get('color_scheme_1', 'light')
layout2_scheme = settings.get('color_scheme_2', 'dark')

# Przypisz schematy do układów
theme_manager.set_layout_scheme(1, layout1_scheme)
theme_manager.set_layout_scheme(2, layout2_scheme)

# Zastosuj aktualny układ
current_layout = settings.get('current_layout', 1)
theme_manager.apply_layout(current_layout)
```

### 2. Konfiguracja w Ustawieniach (config_view.py)
Użytkownik wybiera motywy w karcie "Ogólne":
- **ComboBox Layout 1**: Wybór motywu dla układu 1
- **ComboBox Layout 2**: Wybór motywu dla układu 2
- **Przycisk "Utwórz własną kompozycję"**: Otwiera StyleCreatorDialog

Zmiany są aplikowane **natychmiast**:
```python
def _on_layout1_changed(self, scheme_name: str):
    self.theme_manager.set_layout_scheme(1, scheme_name)
    
    # Jeśli aktualnie jest układ 1, zastosuj zmianę
    if self.theme_manager.get_current_layout() == 1:
        self.theme_manager.apply_theme(scheme_name)
```

### 3. Przełączanie Układów
Użytkownik może przełączać się między układami (np. przycisk w UI):
```python
def _toggle_layout(self):
    new_layout = self.theme_manager.toggle_layout()
    # Wszystkie moduły automatycznie otrzymają nowy motyw przez QSS
```

---

## Integracja Krok po Kroku

### Metoda 1: Komponenty Obsługiwane Przez QSS (Rekomendowana)

Jeśli Twój moduł używa standardowych widgetów Qt, **nie musisz nic robić**. QSS jest aplikowany globalnie.

**Wymagania:**
1. Używaj ObjectName dla unikalnych stylów:
```python
self.my_button = QPushButton("Kliknij")
self.my_button.setObjectName("myModule_customButton")
```

2. Dodaj styl do pliku `.qss`:
```css
QPushButton#myModule_customButton {
    background-color: #2196F3;
    color: white;
}
```

**To wszystko!** ThemeManager automatycznie zaaplikuje styl.

---

### Metoda 2: Komponenty Wymagające Kodu Python

Dla komponentów, które potrzebują dynamicznego stylu (np. QWebEngineView, własne widgety):

#### Krok 1: Pobierz ThemeManager w `__init__`
```python
class MyModuleView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Pobierz ThemeManager (singleton)
        try:
            from src.utils.theme_manager import get_theme_manager
            self.theme_manager = get_theme_manager()
        except Exception as e:
            logger.warning(f"Could not get theme manager: {e}")
            self.theme_manager = None
        
        self._setup_ui()
```

#### Krok 2: Utwórz Metodę `apply_theme()`
```python
def apply_theme(self):
    """Aplikuje aktualny motyw do komponentów modułu"""
    if not self.theme_manager:
        return
    
    # Pobierz kolory aktualnego schematu
    colors = self.theme_manager.get_current_colors()
    
    bg_main = colors.get('bg_main', '#FFFFFF')
    text_primary = colors.get('text_primary', '#000000')
    accent_primary = colors.get('accent_primary', '#2196F3')
    
    # Aplikuj do komponentów
    self.my_widget.setStyleSheet(f"""
        QWidget {{
            background-color: {bg_main};
            color: {text_primary};
        }}
    """)
```

#### Krok 3: Wywołaj `apply_theme()` po Inicjalizacji
```python
def __init__(self, parent=None):
    super().__init__(parent)
    
    self.theme_manager = get_theme_manager()
    self._setup_ui()
    
    # Zastosuj motyw po utworzeniu UI
    self.apply_theme()
```

#### Krok 4: (Opcjonalne) Połącz z i18n dla Auto-Update
Jeśli chcesz, aby motyw był aktualizowany przy zmianie języka/motywu:
```python
from src.utils.i18n_manager import get_i18n

def __init__(self, parent=None):
    super().__init__(parent)
    
    self.theme_manager = get_theme_manager()
    self._setup_ui()
    
    # Połącz z sygnałem zmiany języka (który jest też wywoływany przy zmianie motywu)
    get_i18n().language_changed.connect(self.apply_theme)
    
    self.apply_theme()
```

#### Krok 5: Dodaj Metodę `update_translations()`
```python
def update_translations(self):
    """Aktualizuje tłumaczenia i motyw"""
    # Aktualizuj teksty
    self.btn_save.setText(t("button.save"))
    
    # Aktualizuj motyw (kolory mogły się zmienić)
    self.apply_theme()
```

---

### Metoda 3: Integracja z QWebEngineView

QWebEngineView wymaga specjalnej obsługi, bo renderuje w osobnym procesie.

```python
def _setup_browser_profile(self):
    """Konfiguracja profilu przeglądarki"""
    from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
    
    self.profile = QWebEngineProfile.defaultProfile()
    
    # Konfiguruj ustawienia
    settings = self.profile.settings()
    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
    
    # Synchronizuj z motywem aplikacji
    self._apply_browser_theme()

def _apply_browser_theme(self):
    """Stosuje motyw aplikacji do przeglądarki"""
    if not hasattr(self, 'web_view'):
        return
    
    try:
        from PyQt6.QtGui import QColor
        
        # Pobierz kolory z motywu
        if self.theme_manager:
            colors = self.theme_manager.get_current_colors()
            bg_color = colors.get('bg_main', '#FFFFFF')
        else:
            bg_color = '#FFFFFF'
        
        # Ustaw kolor tła dla przeglądarki
        self.web_view.page().setBackgroundColor(QColor(bg_color))
        
        logger.debug(f"Applied browser theme with background: {bg_color}")
    except Exception as e:
        logger.warning(f"Could not apply browser theme: {e}")

def update_translations(self):
    """Aktualizuje tłumaczenia i motyw"""
    # Aktualizuj teksty...
    
    # Aktualizuj motyw przeglądarki
    self._apply_browser_theme()
```

---

## Przykłady Implementacji

### Przykład 1: Prosty Moduł (Tylko QSS)

```python
# src/Modules/simple_module/simple_view.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton
from src.utils.i18n_manager import t

class SimpleModuleView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_ui()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.btn_action = QPushButton(t("simple.action"))
        self.btn_action.setObjectName("simpleModule_actionButton")
        layout.addWidget(self.btn_action)
    
    def update_translations(self):
        self.btn_action.setText(t("simple.action"))
```

```css
/* resources/themes/light.qss */
QPushButton#simpleModule_actionButton {
    background-color: #4CAF50;
    color: white;
    padding: 10px;
}
```

**Gotowe!** Moduł automatycznie działa z ThemeManager.

---

### Przykład 2: Moduł z Dynamicznymi Stylami

```python
# src/ui/advanced_module_view.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton
from src.utils.theme_manager import get_theme_manager
from src.utils.i18n_manager import t, get_i18n
from loguru import logger

class AdvancedModuleView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Pobierz ThemeManager
        try:
            self.theme_manager = get_theme_manager()
        except Exception as e:
            logger.warning(f"Could not get theme manager: {e}")
            self.theme_manager = None
        
        self._setup_ui()
        
        # Połącz z i18n dla auto-update
        get_i18n().language_changed.connect(self.update_translations)
        
        # Zastosuj motyw
        self.apply_theme()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.title_label = QLabel(t("advanced.title"))
        self.title_label.setObjectName("advanced_titleLabel")
        layout.addWidget(self.title_label)
        
        self.custom_widget = QWidget()
        self.custom_widget.setObjectName("advanced_customWidget")
        layout.addWidget(self.custom_widget)
        
        self.btn_save = QPushButton(t("button.save"))
        self.btn_save.setObjectName("advanced_saveButton")
        layout.addWidget(self.btn_save)
    
    def apply_theme(self):
        """Aplikuje motyw do komponentów"""
        if not self.theme_manager:
            return
        
        # Pobierz kolory
        colors = self.theme_manager.get_current_colors()
        
        bg_main = colors.get('bg_main', '#FFFFFF')
        bg_secondary = colors.get('bg_secondary', '#F5F5F5')
        text_primary = colors.get('text_primary', '#000000')
        accent_primary = colors.get('accent_primary', '#2196F3')
        border_light = colors.get('border_light', '#CCCCCC')
        
        # Aplikuj style
        self.custom_widget.setStyleSheet(f"""
            QWidget#advanced_customWidget {{
                background-color: {bg_secondary};
                border: 2px solid {border_light};
                border-radius: 8px;
                padding: 15px;
            }}
        """)
        
        self.title_label.setStyleSheet(f"""
            QLabel#advanced_titleLabel {{
                color: {accent_primary};
                font-size: 18pt;
                font-weight: bold;
            }}
        """)
        
        logger.debug("[AdvancedModule] Theme applied")
    
    def update_translations(self):
        """Aktualizuje tłumaczenia i motyw"""
        self.title_label.setText(t("advanced.title"))
        self.btn_save.setText(t("button.save"))
        
        # Aktualizuj motyw (kolory mogły się zmienić)
        self.apply_theme()
```

---

### Przykład 3: Moduł z QWebEngineView (P-Web)

```python
# src/ui/p_web_view.py
from PyQt6.QtWidgets import QWidget, QVBoxLayout
from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtCore import QUrl
from src.utils.theme_manager import get_theme_manager
from src.utils.i18n_manager import t, get_i18n
from loguru import logger

class PWebView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Theme manager
        try:
            self.theme_manager = get_theme_manager()
        except Exception as e:
            logger.warning(f"Could not get theme manager: {e}")
            self.theme_manager = None
        
        self._setup_ui()
        
        # Połącz z i18n
        get_i18n().language_changed.connect(self.update_translations)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Przeglądarka
        self.web_view = QWebEngineView()
        self.web_view.setObjectName("pweb_web_view")
        self.web_view.setUrl(QUrl("about:blank"))
        layout.addWidget(self.web_view)
        
        # Konfiguruj profil
        self._setup_browser_profile()
    
    def _setup_browser_profile(self):
        """Konfiguracja profilu przeglądarki"""
        from PyQt6.QtWebEngineCore import QWebEngineProfile, QWebEngineSettings
        
        self.profile = QWebEngineProfile.defaultProfile()
        
        # Ustawienia
        settings = self.profile.settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
        
        # Synchronizuj z motywem
        self._apply_browser_theme()
    
    def _apply_browser_theme(self):
        """Stosuje motyw aplikacji do przeglądarki"""
        if not hasattr(self, 'web_view'):
            return
        
        try:
            from PyQt6.QtGui import QColor
            
            # Pobierz kolory
            if self.theme_manager:
                colors = self.theme_manager.get_current_colors()
                bg_color = colors.get('bg_main', '#FFFFFF')
            else:
                bg_color = '#FFFFFF'
            
            # Ustaw kolor tła
            self.web_view.page().setBackgroundColor(QColor(bg_color))
            
            logger.debug(f"[PWebView] Applied browser theme: {bg_color}")
        except Exception as e:
            logger.warning(f"[PWebView] Could not apply browser theme: {e}")
    
    def update_translations(self):
        """Aktualizuje tłumaczenia i motyw"""
        # Aktualizuj teksty przyciski...
        
        # Aktualizuj motyw przeglądarki (kolory mogły się zmienić)
        self._apply_browser_theme()
```

---

## Najlepsze Praktyki

### 1. Użyj ObjectName dla Wszystkich Kluczowych Widgetów
```python
self.my_widget.setObjectName("moduleName_widgetType")
```

**Dlaczego?**
- Umożliwia precyzyjne targetowanie w QSS
- Unika konfliktów między modułami
- Łatwiejszy debugging

### 2. Zawsze Używaj `get_current_colors()` Zamiast Hardcode
❌ **ŹLE:**
```python
self.label.setStyleSheet("color: #FF0000;")
```

✅ **DOBRZE:**
```python
colors = self.theme_manager.get_current_colors()
accent = colors.get('accent_primary', '#2196F3')
self.label.setStyleSheet(f"color: {accent};")
```

### 3. Obsługuj Brak ThemeManager (Graceful Degradation)
```python
if self.theme_manager:
    colors = self.theme_manager.get_current_colors()
    bg = colors.get('bg_main', '#FFFFFF')
else:
    bg = '#FFFFFF'  # Fallback
```

### 4. Loguj Aplikację Motywu dla Debugowania
```python
logger.debug(f"[MyModule] Applied theme with colors: {colors}")
```

### 5. Testuj z Różnymi Motywami
- Jasny motyw (`light`)
- Ciemny motyw (`dark`)
- Własny motyw użytkownika

### 6. Aktualizuj Motyw w `update_translations()`
```python
def update_translations(self):
    # Aktualizuj teksty
    self.btn.setText(t("button.text"))
    
    # Aktualizuj motyw
    self.apply_theme()
```

### 7. Używaj Domyślnych Wartości w `colors.get()`
```python
bg = colors.get('bg_main', '#FFFFFF')  # Zawsze podaj fallback
```

---

## Dostępne Kolory w `get_current_colors()`

### Kolory Podstawowe
| Klucz | Opis | Jasny Domyślny | Ciemny Domyślny |
|-------|------|----------------|-----------------|
| `bg_main` | Główne tło | `#FFFFFF` | `#1E1E1E` |
| `bg_secondary` | Drugie tło | `#F5F5F5` | `#2D2D2D` |
| `text_primary` | Główny tekst | `#1A1A1A` | `#FFFFFF` |
| `text_secondary` | Drugi tekst | `#666666` | `#B0B0B0` |

### Kolory Akcentów
| Klucz | Opis | Jasny Domyślny | Ciemny Domyślny |
|-------|------|----------------|-----------------|
| `accent_primary` | Główny akcent | `#2196F3` | `#64B5F6` |
| `accent_hover` | Hover nad akcentem | `#1976D2` | `#42A5F5` |
| `accent_pressed` | Wciśnięty akcent | `#0D47A1` | `#2196F3` |

### Kolory Statusów
| Klucz | Opis | Jasny Domyślny | Ciemny Domyślny |
|-------|------|----------------|-----------------|
| `success_bg` | Tło sukcesu (zielony) | `#4CAF50` | `#4CAF50` |
| `success_hover` | Hover sukcesu | `#45A049` | `#45A049` |
| `error_bg` | Tło błędu (czerwony) | `#f44336` | `#f44336` |
| `error_hover` | Hover błędu | `#da190b` | `#da190b` |
| `disabled_bg` | Tło wyłączone | `#cccccc` | `#424242` |
| `disabled_text` | Tekst wyłączony | `#666666` | `#757575` |
| `disabled_border` | Ramka wyłączona | `#999999` | `#555555` |

### Kolory Obramowań
| Klucz | Opis | Jasny Domyślny | Ciemny Domyślny |
|-------|------|----------------|-----------------|
| `border_light` | Jasna ramka | `#CCCCCC` | `#404040` |
| `border_dark` | Ciemna ramka | `#999999` | `#202020` |
| `border_disabled` | Ramka wyłączona | `#BDBDBD` | `#555555` |

### Kolory Specjalne
| Klucz | Opis | Jasny Domyślny | Ciemny Domyślny |
|-------|------|----------------|-----------------|
| `weekend_saturday` | Tło soboty | `#C8FFC8` | `#1B4D3E` |
| `weekend_sunday` | Tło niedzieli | `#FFC896` | `#4A2C2A` |
| `weekend_text` | Tekst weekendu | `#000000` | `#E0E0E0` |
| `checkbox_border` | Ramka checkboxa | `#3498db` | `#64B5F6` |
| `checkbox_checked` | Zaznaczony checkbox | `#27ae60` | `#4CAF50` |
| `checkbox_checked_hover` | Hover nad checkboxem | `#229954` | `#45A049` |

**Uwaga:** Motywy niestandardowe mogą definiować własne kolory w pliku `.json`.

---

## Troubleshooting

### Problem: Motyw Nie Aplikuje Się do Mojego Widgetu

**Rozwiązanie 1: Użyj ObjectName**
```python
self.my_widget.setObjectName("myModule_widget")
```

**Rozwiązanie 2: Aplikuj Style Programowo**
```python
def apply_theme(self):
    colors = self.theme_manager.get_current_colors()
    self.my_widget.setStyleSheet(f"background-color: {colors.get('bg_main')};")
```

---

### Problem: `AttributeError: 'NoneType' object has no attribute 'get_current_colors'`

**Przyczyna:** ThemeManager nie został poprawnie zainicjalizowany.

**Rozwiązanie:**
```python
def apply_theme(self):
    if not self.theme_manager:
        logger.warning("ThemeManager not available")
        return
    
    colors = self.theme_manager.get_current_colors()
    # ...
```

---

### Problem: QWebEngineView Ma Czarne Tło Mimo Jasnego Motywu

**Przyczyna:** QWebEngineView renderuje w osobnym procesie i nie respektuje QSS.

**Rozwiązanie:**
```python
def _apply_browser_theme(self):
    from PyQt6.QtGui import QColor
    colors = self.theme_manager.get_current_colors()
    bg_color = colors.get('bg_main', '#FFFFFF')
    self.web_view.page().setBackgroundColor(QColor(bg_color))
```

---

### Problem: Kolory Nie Aktualizują Się Przy Zmianie Motywu

**Rozwiązanie:** Połącz `apply_theme()` z sygnałem `language_changed`:
```python
get_i18n().language_changed.connect(self.apply_theme)
```

**Lub** wywołaj w `update_translations()`:
```python
def update_translations(self):
    self.apply_theme()
```

---

### Problem: Własny Motyw Nie Pojawia Się w Liście

**Sprawdź:**
1. Czy plik `.qss` jest w `resources/themes/custom/`
2. Czy nazwa pliku nie zawiera spacji (użyj `_` lub `-`)
3. Czy aplikacja została zrestartowana po dodaniu pliku

**Opcjonalnie:** Dodaj `_metadata.json`:
```json
{
  "name": "Mój Piękny Motyw",
  "description": "Mój własny schemat kolorów"
}
```

---

## Podsumowanie

### Checklist Integracji Modułu

- [ ] Pobierz ThemeManager w `__init__` przez `get_theme_manager()`
- [ ] Ustaw ObjectName dla kluczowych widgetów
- [ ] Utwórz metodę `apply_theme()` jeśli potrzebujesz dynamicznych stylów
- [ ] Wywołaj `apply_theme()` po `_setup_ui()`
- [ ] Połącz `update_translations()` z `apply_theme()`
- [ ] Obsłuż przypadek gdy `theme_manager` jest `None`
- [ ] Używaj `get_current_colors()` zamiast hardcode kolorów
- [ ] Przetestuj z jasnym, ciemnym i własnym motywem
- [ ] Dodaj logi dla debugowania

### Minimalna Implementacja
```python
from src.utils.theme_manager import get_theme_manager
from src.utils.i18n_manager import get_i18n

class MyModuleView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        self.theme_manager = get_theme_manager()
        self._setup_ui()
        
        get_i18n().language_changed.connect(self.update_translations)
        self.apply_theme()
    
    def apply_theme(self):
        if not self.theme_manager:
            return
        
        colors = self.theme_manager.get_current_colors()
        # Aplikuj kolory do komponentów
    
    def update_translations(self):
        # Aktualizuj teksty
        self.apply_theme()
```

---

## Dodatkowe Zasoby

- **Plik:** `src/utils/theme_manager.py` - Implementacja ThemeManager
- **Plik:** `src/ui/config_view.py` - Konfiguracja motywów w UI
- **Plik:** `src/ui/style_creator_dialog.py` - Dialog tworzenia motywów
- **Folder:** `resources/themes/` - Motywy built-in
- **Folder:** `resources/themes/custom/` - Motywy użytkownika

---

**Autor:** PRO-Ka-Po Development Team  
**Data:** 2025-11-10  
**Wersja:** 1.0
