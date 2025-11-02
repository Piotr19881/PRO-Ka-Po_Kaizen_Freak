# PRO-Ka-Po Kaizen Freak - Architecture Documentation

## 🏗️ Architektura Aplikacji

### Wzorzec Architektoniczny

Aplikacja wykorzystuje **Layered Architecture** (Architektura Warstwowa) z wyraźnym podziałem na:

1. **Presentation Layer** (Warstwa Prezentacji) - `src/ui/`
2. **Business Logic Layer** (Warstwa Logiki Biznesowej) - `src/core/`
3. **Data Access Layer** (Warstwa Dostępu do Danych) - `src/database/`
4. **Cross-Cutting Concerns** (Funkcjonalności Przekrojowe) - `src/utils/`, `src/auth/`

### Diagram Architektury

```
┌─────────────────────────────────────────────────────────┐
│                    User Interface (PyQt6)                │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐  │
│  │  Login   │ │  Main    │ │  Dialogs │ │  Widgets │  │
│  │  Window  │ │  Window  │ │          │ │          │  │
│  └──────────┘ └──────────┘ └──────────┘ └──────────┘  │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │
┌─────────────────────────────────────────────────────────┐
│              Business Logic / Core Services              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │Task Manager  │  │ Settings     │  │ Auth Service │  │
│  │              │  │ Manager      │  │              │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │
┌─────────────────────────────────────────────────────────┐
│                  Data Access Layer (ORM)                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │ Repository   │  │   Models     │  │  Database    │  │
│  │              │  │              │  │  Connection  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ▲
                           │
┌─────────────────────────────────────────────────────────┐
│                    Database (SQLite)                     │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              Cross-Cutting Concerns                      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │Theme Manager │  │i18n Manager  │  │  Validators  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
```

## 📁 Szczegółowa Struktura Modułów

### 1. UI Layer (`src/ui/`)

**Odpowiedzialność:** Prezentacja danych i interakcja z użytkownikiem

```
src/ui/
├── __init__.py
├── main_window.py          # Główne okno aplikacji
├── navigation_bar.py       # Górny pasek nawigacyjny
├── management_bar.py       # Pasek zarządzania (pod nawigacją)
├── data_table.py          # Widok tabeli z danymi
├── quick_input.py         # Sekcja szybkiego wprowadzania
├── dialogs/
│   ├── __init__.py
│   ├── login_dialog.py    # Okno logowania
│   ├── register_dialog.py # Okno rejestracji
│   ├── settings_dialog.py # Okno ustawień
│   └── task_dialog.py     # Okno dodawania/edycji zadania
└── widgets/
    ├── __init__.py
    ├── custom_button.py   # Niestandardowe przyciski
    └── custom_table.py    # Niestandardowa tabela
```

**Klasy kluczowe:**
- `MainWindow` - główne okno aplikacji (dziedziczy QMainWindow)
- `NavigationBar` - widget z przyciskami nawigacyjnymi
- `ManagementBar` - kontekstowy pasek narzędzi
- `DataTableView` - wyświetlanie danych w formie tabeli
- `QuickInputWidget` - szybkie dodawanie danych

### 2. Core Layer (`src/core/`)

**Odpowiedzialność:** Logika biznesowa aplikacji

```
src/core/
├── __init__.py
├── config.py              # Konfiguracja aplikacji
├── task_manager.py        # Zarządzanie zadaniami
└── settings.py            # Zarządzanie ustawieniami
```

**Klasy kluczowe:**
- `AppConfig` - konfiguracja aplikacji (Pydantic)
- `TaskManager` - operacje na zadaniach (CRUD)
- `SettingsManager` - zarządzanie ustawieniami użytkownika

### 3. Database Layer (`src/database/`)

**Odpowiedzialność:** Dostęp do danych i persystencja

```
src/database/
├── __init__.py
├── models.py              # Modele ORM (SQLAlchemy)
├── repository.py          # Repozytoria (Data Access Objects)
└── connection.py          # Zarządzanie połączeniem z bazą
```

**Modele:**
- `User` - użytkownik systemu
- `Task` - zadanie
- `Category` - kategoria zadań
- `Tag` - tagi dla zadań

### 4. Auth Layer (`src/auth/`)

**Odpowiedzialność:** Autentykacja i autoryzacja

```
src/auth/
├── __init__.py
├── login.py               # Logika logowania
├── register.py            # Logika rejestracji
├── session.py             # Zarządzanie sesją
└── password.py            # Operacje na hasłach (hash, verify)
```

### 5. Utils Layer (`src/utils/`)

**Odpowiedzialność:** Narzędzia pomocnicze

```
src/utils/
├── __init__.py
├── theme_manager.py       # Zarządzanie motywami (QSS)
├── i18n_manager.py        # Internacjonalizacja
├── validators.py          # Walidacja danych
└── logger.py              # Konfiguracja logowania
```

## 🔄 Przepływ Danych

### Przykład: Dodawanie Zadania

```
1. User Interface (quick_input.py)
   │
   ├─> User wpisuje dane zadania
   │
   └─> Kliknięcie "Dodaj" → emit signal(task_data)
       │
       ▼
2. Business Logic (task_manager.py)
   │
   ├─> Walidacja danych (validators.py)
   │
   ├─> Utworzenie obiektu Task
   │
   └─> Wywołanie repository.create(task)
       │
       ▼
3. Data Access (repository.py)
   │
   ├─> Mapowanie na model ORM
   │
   ├─> session.add(task_model)
   │
   └─> session.commit()
       │
       ▼
4. Database (SQLite)
   │
   └─> INSERT INTO tasks ...
       │
       ▼
5. Response Flow (odwrotnie)
   │
   ├─> Task object zwrócony
   │
   ├─> Signal: task_created.emit(task)
   │
   └─> UI update (odświeżenie tabeli)
```

## 🎨 Design Patterns

### 1. **Singleton Pattern**
- `ThemeManager`, `I18nManager`
- Jedna globalna instancja na aplikację

### 2. **Repository Pattern**
- `TaskRepository`, `UserRepository`
- Abstrakcja dostępu do danych

### 3. **Observer Pattern**
- Qt Signals & Slots
- Komunikacja między komponentami

### 4. **Factory Pattern**
- Tworzenie okien dialogowych
- Tworzenie widgetów

### 5. **Strategy Pattern**
- Różne strategie walidacji
- Różne strategie renderowania

## 🔐 Bezpieczeństwo

### Warstwy Bezpieczeństwa

1. **Autentykacja**
   - Hasła hashowane bcrypt
   - Salt per user
   - Minimalna długość hasła

2. **Sesje**
   - Timeout sesji
   - Automatyczne wylogowanie
   - Token sesji

3. **Walidacja**
   - Input validation na wszystkich poziomach
   - SQL Injection prevention (ORM)
   - XSS prevention

4. **Przechowywanie Danych**
   - Zaszyfrowana baza (opcjonalnie)
   - Bezpieczne przechowywanie credentials
   - Backup danych

## 🌐 Internacjonalizacja (i18n)

### Architektura i18n

```
resources/i18n/
├── en.json                # Angielski
├── pl.json                # Polski
└── de.json                # Niemiecki

Każdy plik zawiera:
{
  "key.path": "Translation value",
  "app.title": "Task Manager",
  "menu.file": "File",
  ...
}
```

### Użycie w kodzie

```python
from src.utils.i18n_manager import t

# W kodzie UI
button_text = t("button.save")  # "Zapisz" / "Save" / "Speichern"
window_title = t("app.title")   # "Menedżer Zadań" / "Task Manager"
```

## 🎨 Theming System

### Architektura Motywów

```
resources/themes/
├── light.qss              # Jasny motyw
├── dark.qss               # Ciemny motyw
└── custom.qss             # Niestandardowy

Każdy plik QSS:
- Definiuje kolory dla wszystkich widgetów
- Wspólne klasy CSS
- Responsive sizing
```

### Stosowanie Motywów

```python
from src.utils.theme_manager import ThemeManager

theme_manager = ThemeManager()
theme_manager.apply_theme("dark")
```

## 📊 Diagram Sekwencji - Logowanie

```
User          LoginDialog      AuthService      Database
 │                │                 │               │
 │─Enter credentials───>            │               │
 │                │                 │               │
 │                │──validate()────>│               │
 │                │                 │               │
 │                │                 │──query user──>│
 │                │                 │               │
 │                │                 │<─user data────│
 │                │                 │               │
 │                │                 │─verify_password()
 │                │                 │               │
 │                │<──auth result───│               │
 │                │                 │               │
 │<──login success / error──────────│               │
 │                │                 │               │
 │─────────────> MainWindow         │               │
```

## 🧪 Testing Strategy

### Poziomy Testowania

1. **Unit Tests** (`tests/`)
   - Testowanie pojedynczych funkcji
   - Mocki dla zależności
   - Coverage > 80%

2. **Integration Tests**
   - Testowanie integracji między modułami
   - Testowanie z bazą danych

3. **UI Tests**
   - pytest-qt dla testów UI
   - Testowanie interakcji użytkownika

## 📈 Performance Considerations

1. **Lazy Loading** - ładowanie danych na żądanie
2. **Caching** - cache dla motywów i tłumaczeń
3. **Database Indexing** - indeksy na kluczowych polach
4. **Connection Pooling** - efektywne zarządzanie połączeniami

## 🔮 Przyszłe Rozszerzenia

1. **Plugin System** - rozszerzalność przez pluginy
2. **Cloud Sync** - synchronizacja w chmurze
3. **Mobile App** - wersja mobilna
4. **REST API** - API dla integracji
5. **Real-time Updates** - aktualizacje w czasie rzeczywistym

---

**Ostatnia aktualizacja:** Listopad 2025
