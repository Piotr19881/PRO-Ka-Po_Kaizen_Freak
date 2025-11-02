# PRO-Ka-Po Kaizen Freak - Instrukcje dla Copilot

## 🎯 Cel projektu
Budowa **komercyjnej aplikacji desktopowej** do zarządzania zadaniami i produktywnością z wykorzystaniem metodyki Kaizen.

## 🏗️ Architektura aplikacji

### Desktop Application (PyQt6)
- **Lokalizacja**: `PRO-Ka-Po_Kaizen_Freak/` (główny katalog)
- **Framework**: PyQt6 (GUI), Python 3.13.2
- **Struktura**:
  ```
  src/
  ├── ui/              # Interfejs użytkownika (views, dialogs)
  ├── core/            # Logika biznesowa, konfiguracja
  ├── database/        # Modele i migracje (lokalne cache)
  ├── auth/            # Moduł autoryzacji
  ├── utils/           # Narzędzia pomocnicze (i18n, theme_manager)
  └── modules/         # Moduły funkcjonalne (tasks, kanban, etc.)
  
  resources/
  ├── themes/          # Schematy kolorystyczne (QSS)
  │   ├── light.qss
  │   ├── dark.qss
  │   └── custom/      # Własne schematy użytkownika
  ├── i18n/            # Tłumaczenia (pl.json, en.json, de.json)
  └── icons/           # Ikony i zasoby graficzne
  ```

### API Server (FastAPI)
- **Lokalizacja**: `Render_upload/`
- **Framework**: FastAPI + Uvicorn
- **Baza danych**: PostgreSQL 17 (Render - Frankfurt)
- **Deployment**: Render.com
- **Struktura**:
  ```
  app/
  ├── main.py          # FastAPI application + endpoints
  ├── config.py        # Konfiguracja (zmienne środowiskowe)
  ├── database.py      # Modele SQLAlchemy + connection
  ├── auth.py          # JWT authentication (TODO)
  └── routers/         # Endpoints (TODO)
  ```

## 🎨 System motywów

### Zarządzanie motywami
- **ThemeManager** (`src/utils/theme_manager.py`) zarządza schematami kolorystycznymi
- **Dwa układy**: Układ 1 (light) i Układ 2 (dark) - przełączane przyciskiem ☀/🌙
- **Własne schematy**: Kreator stylów pozwala tworzyć i zapisywać własne kompozycje kolorystyczne

### Integracja z UI
- **KAŻDE okno dialogowe** musi:
  - Ładować aktualny motyw przy inicjalizacji
  - Reagować na zmiany motywu w czasie rzeczywistym (jeśli otwarte)
  - Używać QSS stylów z plików `resources/themes/*.qss`

### Style Creator Dialog
- 4 zakładki: Main Colors, Navigation, Buttons, Tables
- 20+ selektorów kolorów z live preview
- Generowanie QSS i zapis do `resources/themes/custom/`
- Pełna integracja z i18n

## 🌍 Międzynarodowość (i18n)

### System tłumaczeń
- **I18nManager** (`src/utils/i18n_manager.py`) - singleton, dziedziczy z QObject
- **Języki**: Polski (pl), English (en), Deutsch (de)
- **Pliki**: `resources/i18n/{pl,en,de}.json`
- **Signal**: `language_changed` - emitowany przy zmianie języka

### Implementacja w komponentach
```python
from ..utils.i18n_manager import t, get_i18n

# W __init__:
get_i18n().language_changed.connect(self.update_translations)

# Metoda odświeżająca UI:
def update_translations(self):
    self.label.setText(t('settings.colors'))
    self.button.setText(t('dialog.save'))
```

### Konwencje kluczy tłumaczeń
- `nav.*` - Przyciski nawigacji
- `settings.*` - Ustawienia
- `dialog.*` - Okna dialogowe
- `style_creator.*` - Kreator stylów
- `quick_input.*` - Szybkie wprowadzanie
- `auth.*` - Autoryzacja (TODO)
- `tasks.*` - Zadania (TODO)
- `kanban.*` - Kanban (TODO)

## 🔐 Autoryzacja i bezpieczeństwo

### Architektura bezpieczeństwa
1. **Aplikacja desktopowa** → komunikuje się TYLKO z API (nie bezpośrednio z bazą)
2. **API Server (Render)** → jedyne połączenie z PostgreSQL
3. **JWT Tokens** → autoryzacja żądań z aplikacji

### Dane dostępowe do bazy (TYLKO dla API)
```
Host: dpg-d433vlidbo4c73a516p0-a.frankfurt-postgres.render.com
Port: 5432
Database: pro_ka_po
User: pro_ka_po_user
Password: 01pHONi8u23ZlHNffO64TcmWywetoiUD
```
⚠️ **Nigdy nie commituj `.env` do repozytorium!**

### Moduły do implementacji
- [ ] `Render_upload/app/auth.py` - JWT token management
- [ ] `Render_upload/app/routers/auth.py` - /register, /login endpoints
- [ ] `src/auth/` - Moduł logowania w aplikacji desktopowej
- [ ] `src/utils/api_client.py` - HTTP client do komunikacji z API

## 📡 API Endpoints

### Zaimplementowane
- ✅ `GET /` - Info o API
- ✅ `GET /health` - Health check + database status
- ✅ `GET /api/test` - Test połączenia z PostgreSQL
- ✅ `GET /api/v1/info` - Lista dostępnych endpoints
- ✅ `GET /docs` - Swagger UI dokumentacja
- ✅ `GET /redoc` - ReDoc dokumentacja

### Do implementacji (priorytet)
- [ ] `POST /api/v1/auth/register` - Rejestracja użytkownika
- [ ] `POST /api/v1/auth/login` - Logowanie (zwraca JWT token)
- [ ] `POST /api/v1/auth/refresh` - Odświeżenie tokena
- [ ] `GET /api/v1/users/me` - Dane zalogowanego użytkownika
- [ ] `GET /api/v1/tasks` - Lista zadań
- [ ] `POST /api/v1/tasks` - Tworzenie zadania
- [ ] `PUT /api/v1/tasks/{id}` - Edycja zadania
- [ ] `DELETE /api/v1/tasks/{id}` - Usuwanie zadania
- [ ] `GET /api/v1/kanban/boards` - Lista tablic Kanban
- [ ] `POST /api/v1/kanban/boards` - Tworzenie tablicy

### Modele bazy danych (SQLAlchemy)
```python
User:
  - id (Text) - PRIMARY KEY
  - username (String) - UNIQUE
  - email (String) - UNIQUE
  - hashed_password (String)
  - full_name (String)
  - is_active (Boolean)
  - is_verified (Boolean)
  - created_at (DateTime)
  - last_login (DateTime)

Task:
  - id (Integer) - PRIMARY KEY
  - user_id (Text) - FOREIGN KEY
  - title (String)
  - description (Text)
  - status (String) - todo/in_progress/done
  - priority (String) - low/medium/high
  - due_date (DateTime)
  - created_at (DateTime)

KanbanBoard:
  - id (Integer) - PRIMARY KEY
  - user_id (Text) - FOREIGN KEY
  - name (String)
  - description (Text)
  - created_at (DateTime)

KanbanCard:
  - id (Integer) - PRIMARY KEY
  - board_id (Integer) - FOREIGN KEY
  - task_id (Integer) - FOREIGN KEY
  - column_name (String)
  - position (Integer)
```

## 💻 Interfejs użytkownika

### Główne okno (MainWindow)
- **NavigationBar**: 12 przycisków (Tasks, Reports, Kanban, Calendar, Notes, Analytics, Archive, Settings, Help, About, Metrics, HotKey)
- **Przycisk ☀/🌙**: Przełącza między Układem 1 a 2
- **ManagementBar**: Add, Edit, Delete, Search
- **DataDisplayArea**: Tabela z danymi
- **QuickInputSection**: Szybkie dodawanie zadań

### Settings View (8 zakładek)
1. **Ogólne** (General) ✅
   - Kolory i wygląd (Układ 1, Układ 2, Kreator własnych)
   - Język aplikacji
   - Ustawienia systemowe
   - Skróty klawiszowe
2. **Zadania** (Tasks)
3. **Kanban**
4. **Powiadomienia** (Notifications)
5. **Synchronizacja** (Sync)
6. **Prywatność** (Privacy)
7. **Zaawansowane** (Advanced)
8. **Informacje** (About)

### Style Creator Dialog ✅
- Pełna implementacja (656 linii kodu)
- 4 zakładki z kategoryzowanymi kolorami
- Live preview + zapis do pliku QSS
- Integracja z i18n i theme system
- Używamy emoji tylko na wyraźną prośbę 

## 📋 Standardy kodu

### Python Code Style
- **PEP 8** compliance
- **Type hints** dla wszystkich funkcji
- **Docstrings** w formacie Google Style
- **Logowanie** przez loguru (nie print!)
- **Error handling** - try/except z konkretynymi wyjątkami

### PyQt6 Patterns
```python
# Signal/Slot pattern
class MyWidget(QWidget):
    data_changed = pyqtSignal(str)  # Custom signals
    
    def __init__(self):
        super().__init__()
        self._setup_ui()
        self._connect_signals()
    
    def _setup_ui(self):
        """Konfiguracja interfejsu"""
        pass
    
    def _connect_signals(self):
        """Połączenia sygnałów"""
        self.button.clicked.connect(self._on_button_clicked)
```

### FastAPI Patterns
```python
# Dependency injection
@app.get("/api/users/me")
async def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme)
):
    """Endpoint description"""
    pass

# Response models
class UserResponse(BaseModel):
    id: str
    username: str
    email: str
```

## 🔄 Workflow development

### 🎯 Workflow ogólny - Rozpoczęcie pracy nad modułem

#### 1. Szkic interfejsu
- Przygotuj **szkic okna z blankami** (puste komponenty bez treści)
- **NIE używaj placeholderów** chyba że absolutnie konieczne
- Najpierw layout i struktura, potem funkcjonalność

#### 2. Planowanie bazy danych
- Przygotuj **plan struktury bazy danych** dla modułu
- **ZAWSZE pamiętaj**: aplikacja jest **wieloużytkownikowa**!
- Każda tabela musi mieć powiązanie z `user_id`
- Przygotuj **query SQL** do utworzenia struktury tabel
- Konsultuj strukturę przed implementacją

#### 3. Testowanie i kod analityczny
- **Wszystkie kody testowe** przechowuj w: `tests/`
- Struktura testów:
  ```
  tests/
  ├── test_auth/           # Testy modułu autoryzacji
  ├── test_tasks/          # Testy modułu zadań
  ├── test_kanban/         # Testy modułu kanban
  └── test_api/            # Testy API endpoints
  ```
- Dla każdego modułu twórz **osobny podfolder testowy** jeśli potrzebny
- Kod analityczny używaj do:
  - Testowania połączenia z API
  - Walidacji struktury danych
  - Debugowania złożonych funkcji

#### 4. Nadawanie funkcjonalności
- Po zatwierdzonym szkicu UI i strukturze bazy → implementuj funkcje
- Jedna funkcja = jedna metoda (single responsibility)
- Testuj na bieżąco każdą dodaną funkcjonalność

### ⚙️ Workflow szczególny - Implementacja funkcjonalności

#### Troska o integracje (zawsze!)
1. **Integracja z API**
   - Jeśli funkcja wymaga danych z bazy → endpoint API
   - NIE łącz się bezpośrednio z PostgreSQL z aplikacji desktop
   - Używaj HTTP client z error handling

2. **Integracja z motywami**
   - Każdy widget musi używać QSS classes/IDs
   - Testuj w obu motywach (light/dark)
   - Użyj ThemeManager do dynamicznych zmian

3. **Integracja z językami (i18n)**
   - Wszystkie stringi przez funkcję `t()`
   - Dodaj klucze do 3 plików (pl/en/de) PRZED użyciem
   - Implementuj `update_translations()` w każdym komponencie

#### Przygotowanie do buildu
- **Kod maksymalnie zoptymalizowany** - myśl o pliku wykonawczym
- Unikaj ciężkich dependencji jeśli nie konieczne
- Lazy loading dla dużych modułów
- Minimalizuj import statements (tylko co potrzebne)
- Testuj uruchomienie z `.exe` regularnie

### 🧹 Czystość kodu (zero tolerance dla śmieci!)

#### Kod modułowy i przejrzysty
```python
# ✅ DOBRZE - modułowo, przejrzyście
class TaskManager:
    """Manager for task operations"""
    
    def __init__(self, api_client):
        self.api = api_client
        self._cache = {}
    
    def get_tasks(self, user_id: str) -> List[Task]:
        """Fetch tasks for user"""
        return self._fetch_from_api_or_cache(user_id)
    
    def create_task(self, task_data: dict) -> Task:
        """Create new task"""
        return self.api.post("/tasks", task_data)

# ❌ ŹLE - monolityczny, nieczytelny
def do_everything(user, task_title, desc, status, priority, due_date, board_id):
    # 200 linii kodu w jednej funkcji...
```

#### Maksymalna optymalizacja
- **Unikaj duplikacji kodu** - DRY principle
- **Używaj list comprehensions** zamiast pętli gdzie można
- **Cache'uj wyniki** ciężkich operacji
- **Lazy loading** dla rzadko używanych modułów
- **Asynchroniczne operacje** dla I/O (API calls)

#### Czyszczenie na bieżąco
**ZAWSZE usuwaj:**
- ❌ Zakomentowany stary kod
- ❌ Nieużywane importy
- ❌ Funkcje debug/test w produkcyjnym kodzie
- ❌ Print statements (używaj loguru!)
- ❌ Placeholder funkcje bez implementacji
- ❌ TODO komentarze po zrobieniu zadania

**Narzędzia do czyszczenia:**
```python
# Przed commitem sprawdź:
# 1. Nieużywane importy
# 2. Dead code
# 3. Duplicate code
# 4. Code complexity
```

### 📝 Checklist przed commitem

#### UI Component Checklist
- [ ] Szkic UI bez placeholderów ✓
- [ ] Plan bazy danych (multi-user!) ✓
- [ ] SQL query przygotowane ✓
- [ ] Integracja z ThemeManager ✓
- [ ] Tłumaczenia (pl/en/de) dodane ✓
- [ ] `update_translations()` zaimplementowane ✓
- [ ] Signal/slot connections ✓
- [ ] QSS classes/IDs użyte ✓
- [ ] Testowane w obu motywach ✓
- [ ] Kod zoptymalizowany ✓
- [ ] Nieużywany kod usunięty ✓
- [ ] Loguru zamiast print ✓

#### API Endpoint Checklist
- [ ] Route dodany do `app/main.py` lub `app/routers/` ✓
- [ ] Pydantic models (request/response) ✓
- [ ] SQLAlchemy queries zoptymalizowane ✓
- [ ] Error handling (try/except) ✓
- [ ] JWT authorization (jeśli protected) ✓
- [ ] Dokumentacja w docstring ✓
- [ ] Testowane przez `/docs` ✓
- [ ] Response time < 500ms ✓
- [ ] Dead code usunięty ✓

#### Integracja Desktop ↔ API Checklist
- [ ] HTTP client z retry logic ✓
- [ ] JWT token w headers ✓
- [ ] Timeout ustawiony (5-10s) ✓
- [ ] Error handling dla network issues ✓
- [ ] Lokalne cache dla offline mode ✓
- [ ] Loading indicators w UI ✓
- [ ] Kod zoptymalizowany (async!) ✓

### Przed rozpoczęciem pracy
1. Sprawdź czy istnieje plik tłumaczeń dla nowych stringów
2. Upewnij się że nowy komponent integruje się z theme system
3. Jeśli endpoint API - dodaj do dokumentacji w README.md
4. Przygotuj szkic UI i plan bazy danych
5. Utwórz folder testowy jeśli potrzebny

### Podczas implementacji
1. **UI Component**:
   - Dodaj `update_translations()` method
   - Połącz z `language_changed` signal
   - Zastosuj aktualny motyw z ThemeManager
   - Użyj QSS classes/IDs dla stylowania
   - **Pisz kod modułowo i przejrzyście**
   - **Optymalizuj na bieżąco**

2. **API Endpoint**:
   - Dodaj route w `app/main.py` lub `app/routers/`
   - Dodaj response model (Pydantic)
   - Dodaj error handling
   - Przetestuj przez `/docs`
   - **Zoptymalizuj SQL queries**
   - **Usuń debug code**

3. **Integracja Desktop ↔ API**:
   - Użyj `requests` lub `httpx` dla HTTP calls
   - Obsłuż JWT token w headers
   - Dodaj retry logic i timeout
   - Cache lokalne dla offline mode
   - **Asynchroniczne wywołania**
   - **Minimalizuj network calls**

### Po zakończeniu
- [ ] Przetestuj zmiany w 3 językach (pl/en/de)
- [ ] Przetestuj oba motywy (light/dark)
- [ ] Sprawdź logi (loguru) - brak błędów
- [ ] Zaktualizuj dokumentację jeśli dodano API endpoint

## 🚀 Deployment

### Lokalne uruchomienie
```bash
# Desktop App
cd PRO-Ka-Po_Kaizen_Freak
.venv\Scripts\Activate.ps1  # Windows
python main.py

# API Server
cd Render_upload
pip install -r requirements.txt
python -m app.main
# Dostępne na http://localhost:8000
```

### Deploy API na Render
1. Push kod z `Render_upload/` do repozytorium
2. Render automatycznie wykryje `render.yaml`
3. Zmienne środowiskowe skonfigurowane w `render.yaml`
4. Deploy wykonuje: `pip install -r requirements.txt` → `uvicorn app.main:app`

## 📦 Zależności

### Desktop App
- PyQt6 6.10.0 - GUI framework
- loguru 0.7.3 - Logging
- pydantic 2.12.3 - Validation
- pydantic-settings 2.11.0 - Configuration
- requests / httpx - HTTP client (TODO)

### API Server
- fastapi 0.115.5 - Web framework
- uvicorn 0.32.1 - ASGI server
- sqlalchemy 2.0.36 - ORM
- psycopg2-binary 2.9.10 - PostgreSQL adapter
- python-jose 3.3.0 - JWT tokens
- passlib 1.7.4 - Password hashing
- pydantic 2.10.3 - Validation

## 🎯 Roadmap

### Faza 1: Fundament ✅
- [x] Struktura projektu
- [x] System motywów (light/dark + custom)
- [x] System i18n (pl/en/de)
- [x] Główne okno UI
- [x] Settings view
- [x] Style Creator Dialog
- [x] API Server podstawy
- [x] Połączenie z PostgreSQL

### Faza 2: Autoryzacja (W TRAKCIE)
- [ ] API: Register endpoint
- [ ] API: Login endpoint (JWT)
- [ ] Desktop: Login screen
- [ ] Desktop: HTTP client z token management
- [ ] API: Protected endpoints

### Faza 3: Zadania
- [ ] API: CRUD endpoints dla Tasks
- [ ] Desktop: Tasks module UI
- [ ] Desktop: Integracja z API
- [ ] Lokalne cache i offline mode

### Faza 4: Kanban
- [ ] API: Kanban boards endpoints
- [ ] Desktop: Kanban view
- [ ] Drag & drop functionality

### Faza 5: Funkcje dodatkowe
- [ ] Reports
- [ ] Calendar integration
- [ ] Analytics
- [ ] Notifications
- [ ] Synchronizacja

## 🐛 Troubleshooting

### Baza danych
- Modele muszą pasować do istniejącej struktury (nie używaj `create_all()`)
- `user.id` jest typu TEXT (nie Integer!)
- Używaj `text()` dla raw SQL: `db.execute(text("SELECT 1"))`

### Theme System
- Custom themes zapisywane w `resources/themes/custom/`
- Odśwież listę po zapisaniu: `theme_manager.get_available_themes()`
- Prefix ⭐ dla custom themes w UI

### i18n
- Zawsze dodawaj klucze do wszystkich 3 plików (pl/en/de)
- Używaj `t()` zamiast hardcoded strings
- Podłącz `language_changed` signal w każdym komponencie

---

**Ostatnia aktualizacja**: 2025-11-01  
**Wersja aplikacji**: 1.0.0 (Development)  
**Status**: Active Development 🚧

