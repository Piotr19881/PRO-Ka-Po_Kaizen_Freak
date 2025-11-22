# Moduł Pomodoro - Specyfikacja Funkcjonalności

## 📋 Przegląd
Moduł Pomodoro to narzędzie do zarządzania czasem pracy i przerw według techniki Pomodoro z pełną integracją z systemem PRO-Ka-Po Kaizen Freak.

---

## 🎨 Struktura Interfejsu

### Layout Główny
- **Podział pionowy:** 1/3 (Akcje) + 2/3 (Ustawienia)
- **Kompatybilność:** Pełna zgodność z systemem motywów kolorystycznych
- **Internacjonalizacja:** 100% stringów przez i18n (brak hardcoded text)

---

## 📍 Sekcja Akcji (Lewa strona - 1/3)

### 1. Nagłówek Sesji
- **Tytuł:** "Sesja pracy" (i18n)
- **Temat sesji:** Domyślnie "Ogólna" (edytowalne)
- **Przycisk "Nadaj tytuł":**
  - Aktywny tylko gdy sesja NIE jest w toku
  - Otwiera dialog z:
    - Pole tekstowe (wprowadzenie tytułu)
    - Przycisk "Anuluj"
    - Przycisk "OK"

### 2. Liczniki Sesji
- **"Dziś wykonano N długich sesji"** (dynamiczna wartość)
- **"Sesja krótka N/X"** (postęp w cyklu)

### 3. Zegar Odliczający
- **Wyświetlanie:** Duży, czytelny format MM:SS
- **Kolor:** Zgodny z motywem (czerwony dla pracy, zielony dla przerwy)
- **Progress Bar:** Pod zegarem (pokazuje % zakończenia)

### 4. Popup Timer
- **Przycisk:** "Otwórz licznik popup"
- **Okno popup zawiera:**
  - Tytuł aktualnej sesji
  - Duży zegar odliczający (centralnie)
  - Licznik sesji N/X
  - Zawsze na wierzchu (always on top)

### 5. Kontrola Sesji (4 przyciski)
- **Start/Pauza:** Toggle między startem a pauzą
- **Reset:** Resetuje bieżący timer do ustawionego czasu
- **Pomiń:** Przeskakuje do kolejnego etapu (praca → przerwa lub przerwa → praca)
- **Stop:** Kończy całą sesję i zapisuje do logów

### 6. Motywacja Kaizen
- **Losowy cytat motywacyjny** w stylu Kaizen
- Zmienia się z każdą nową sesją
- Przykłady:
  - "Mały postęp każdego dnia prowadzi do wielkich rezultatów"
  - "Skupienie to klucz do mistrzostwa"
  - "Każda sesja przybliża Cię do celu"

---

## ⚙️ Sekcja Ustawień (Prawa strona - 2/3)

### 1. Podsekcja: Czasy Sesji
| Parametr | Wartość domyślna | Zakres |
|----------|------------------|--------|
| Czas pracy | 25 min | 1-60 min |
| Krótka przerwa | 5 min | 1-30 min |
| Długa przerwa | 15 min | 5-60 min |
| Sesje do długiej przerwy | 4 | 1-10 |

**UI:** SpinBox dla każdego parametru

### 2. Podsekcja: Opcje Automatyczne
- **Checkbox:** "Automatycznie rozpoczynaj przerwy"
  - Jeśli OFF: Popup z pytaniem "Rozpocząć przerwę?"
  
- **Checkbox:** "Automatycznie rozpoczynaj następne Pomodoro"
  - Jeśli OFF: Popup z pytaniem "Rozpocząć kolejną sesję pracy?"

**Logika:**
- Gdy obie opcje są ON → pełny automat
- Gdy OFF → użytkownik ma kontrolę przez popupy

### 3. Podsekcja: Powiadomienia Dźwiękowe
- **Checkbox:** "Odtwarzaj dźwięk po zakończeniu sesji pracy"
  - Pole wyboru dźwięku (dropdown): "Systemowy Błąd" (domyślnie)
  
- **Checkbox:** "Odtwarzaj dźwięk po zakończeniu przerwy"
  - Pole wyboru dźwięku (dropdown): "Systemowy Asterisk" (domyślnie)

**Integracja:**
- Wykorzystuje **ten sam system dźwięków** co Alarmy
- Wspólne źródło dźwięków z `src/utils/sound_manager.py`

### 4. Podsekcja: Statystyki Dzisiejsze
**Wyświetlane dane:**
- Ukończone sesje: **X**
- Całkowity czas skupienia: **Y min**

**Przycisk:** "Pokaż logi"
- Otwiera **Popup z historią sesji**
- Tabela zawiera:
  - Data i godzina rozpoczęcia
  - Czas trwania (praca/przerwa)
  - Status (ukończona/przerwana/pominięta)
  - Temat sesji
  - Ocena produktywności (opcjonalnie)

---

## 🔄 Logika Cyklu Pomodoro

### Przepływ Sesji
```
START → Praca (25min) → Krótka przerwa (5min) → Praca (25min) → ... 
→ Po 4 sesjach → Długa przerwa (15min) → RESET cyklu
```

### Statusy Sesji
- **`not_started`** - Timer gotowy do startu
- **`running`** - Aktywne odliczanie
- **`paused`** - Sesja wstrzymana
- **`completed`** - Zakończona normalnie
- **`interrupted`** - Przerwana przez użytkownika
- **`skipped`** - Pominięta (przycisk "Pomiń")

### Auto vs Manual Mode

**AUTO MODE (oba checkboxy ON):**
1. Koniec pracy → automatyczny start przerwy
2. Koniec przerwy → automatyczny start pracy
3. Zero interwencji użytkownika

**MANUAL MODE (checkboxy OFF):**
1. Koniec pracy → Popup: "Przerwa gotowa. Start?"
2. Użytkownik klika "Tak" lub "Nie"
3. "Nie" → timer zatrzymany, czeka na akcję

---

## 💾 Integracja z Bazą Danych

### Session Topics (Tematy)
**Zapisywane lokalnie + sync:**
- ID tematu
- Nazwa tematu
- Kolor (hex)
- Ikona (emoji)
- Statystyki (liczba sesji, łączny czas)

**CRUD Operations:**
- Create: Dialog "Nadaj tytuł" → zapisuje nowy temat
- Read: Lista tematów w dropdown
- Update: Edycja nazwy tematu
- Delete: Soft delete (deleted_at)

### Session Logs (Logi)
**Zapisywane po każdej sesji:**
- User ID
- Topic ID (FK)
- Typ sesji (work/short_break/long_break)
- Czas rozpoczęcia
- Czas zakończenia
- Planowany czas trwania
- Rzeczywisty czas trwania
- Status (completed/interrupted/skipped)
- Numer Pomodoro w cyklu (1-4)
- Notatki (opcjonalne)

**Kiedy zapisywać:**
- Po kliknięciu "Stop"
- Po automatycznym zakończeniu (jeśli auto-mode)
- Po przeskoczeniu ("Pomiń")

---

## 🎯 Funkcjonalności Dodatkowe

### 1. Popup Timer Window
**Cechy:**
- Always on top
- Minimalistyczny design
- Tylko zegar + tytuł + licznik sesji
- Można przeciągać
- Zamknięcie NIE przerywa sesji (działa w tle)

### 2. Powiadomienia Systemowe
- Windows notification po zakończeniu sesji/przerwy
- Treść: "Sesja pracy zakończona! Czas na przerwę."
- Kliknięcie → fokus na popup timer

### 3. Tray Icon Integration
- Ikona w system tray zmienia kolor (praca/przerwa)
- Tooltip pokazuje pozostały czas
- Menu kontekstowe:
  - Start/Pauza
  - Stop
  - Pokaż okno główne

### 4. Statystyki i Raporty
**Widok logów (popup) zawiera:**
- Filtr po dacie (dziś/tydzień/miesiąc/wszystkie)
- Filtr po temacie
- Filtr po statusie
- Export do CSV
- Wykresy (słupkowy - sesje per dzień)

---

## 🔊 Dźwięki

### Źródła Dźwięków
**Systemowe (Windows):**
- `SystemHand` - Błąd
- `SystemAsterisk` - Informacja
- `SystemExclamation` - Ostrzeżenie

**Custom:**
- Wsparcie dla plików .wav z folderu `data/sounds/`

### Implementacja
- Reużycie `SoundManager` z modułu Alarmów
- Osobne ustawienia dla:
  - Dźwięk końca pracy
  - Dźwięk końca przerwy

---

## 🌍 Internacjonalizacja (i18n)

### Klucze Tłumaczeń (przykłady)

```python
# pomodoro_view.py
"pomodoro.session_title": "Sesja pracy"
"pomodoro.general_topic": "Ogólna"
"pomodoro.set_title_btn": "Nadaj tytuł"
"pomodoro.today_sessions": "Dziś wykonano {count} długich sesji"
"pomodoro.short_session": "Sesja krótka {current}/{total}"
"pomodoro.open_popup": "Otwórz licznik popup"

# Przyciski kontroli
"pomodoro.btn_start": "Start"
"pomodoro.btn_pause": "Pauza"
"pomodoro.btn_reset": "Reset"
"pomodoro.btn_skip": "Pomiń"
"pomodoro.btn_stop": "Stop"

# Ustawienia
"pomodoro.settings_title": "Ustawienia"
"pomodoro.work_duration": "Czas pracy"
"pomodoro.short_break": "Krótka przerwa"
"pomodoro.long_break": "Długa przerwa"
"pomodoro.sessions_count": "Sesje do długiej przerwy"

# Auto-opcje
"pomodoro.auto_breaks": "Automatycznie rozpoczynaj przerwy"
"pomodoro.auto_pomodoro": "Automatycznie rozpoczynaj następne Pomodoro"

# Powiadomienia
"pomodoro.sound_work_end": "Odtwarzaj dźwięk po zakończeniu sesji pracy"
"pomodoro.sound_break_end": "Odtwarzaj dźwięk po zakończeniu przerwy"

# Statystyki
"pomodoro.stats_today": "Statystyki dzisiejsze"
"pomodoro.completed_sessions": "Ukończone sesje"
"pomodoro.total_focus_time": "Całkowity czas skupienia"
"pomodoro.show_logs": "Pokaż logi"

# Motywacja
"pomodoro.motivation_1": "Mały postęp każdego dnia prowadzi do wielkich rezultatów"
"pomodoro.motivation_2": "Skupienie to klucz do mistrzostwa"
"pomodoro.motivation_3": "Każda sesja przybliża Cię do celu"
```

---

## 📁 Struktura Plików

```
PRO-Ka-Po_Kaizen_Freak/
└── src/
    └── Modules/
        └── Pomodoro_module/
            ├── __init__.py
            ├── pomodoro_logic.py          # Logika timera i cykli
            ├── pomodoro_models.py         # SQLAlchemy models
            ├── pomodoro_session.py        # Klasa PomodoroSession
            ├── pomodoro_api_client.py     # API client (REST)
            └── pomodoro_websocket.py      # WebSocket client (sync)
    
    └── ui/
        ├── pomodoro_view.py               # Główny widok (TERAZ)
        ├── pomodoro_popup_timer.py        # Popup timer window
        └── pomodoro_logs_dialog.py        # Dialog z historią

    └── utils/
        └── sound_manager.py               # Reużycie z Alarms
```

---

## 🚀 Plan Implementacji

### Faza 1: UI Scaffold (TERAZ)
✅ Utworzenie `pomodoro_view.py`
✅ Layout zgodny z mock-upem
✅ Wszystkie komponenty UI (bez logiki)
✅ Integracja z i18n
✅ Integracja z theme system

### Faza 2: Logika Lokalna
- `pomodoro_logic.py` - timer logic
- `pomodoro_session.py` - session manager
- Połączenie UI ↔ Logic

### Faza 3: Database Models
- `pomodoro_models.py` - SQLAlchemy models
- Migracja lokalnej bazy (SQLite)
- CRUD operations

### Faza 4: API Backend
- FastAPI router (`pomodoro_router.py`)
- Endpoints dla topics i logs
- WebSocket dla real-time sync

### Faza 5: Sync & Integration
- `pomodoro_api_client.py` - REST client
- `pomodoro_websocket.py` - WS client
- Auto-refresh token integration

### Faza 6: Polish & Testing
- Popup timer window
- Logs dialog
- System notifications
- Comprehensive testing

---

## 🎨 Design Patterns

### Separation of Concerns
- **UI Layer:** `pomodoro_view.py` - tylko PyQt6 widgets
- **Logic Layer:** `pomodoro_logic.py` - business logic
- **Data Layer:** `pomodoro_models.py` - database models
- **API Layer:** `pomodoro_api_client.py` - komunikacja z backend

### Observer Pattern
- `PomodoroSession` emituje sygnały Qt
- `PomodoroView` subskrybuje sygnały
- Oddzielenie logiki od UI

### State Machine
- Timer states: NOT_STARTED → RUNNING → PAUSED → COMPLETED
- Session types: WORK → SHORT_BREAK → WORK → ... → LONG_BREAK

---

## 📊 Metryki Sukcesu

**Użyteczność:**
- Średni czas na rozpoczęcie sesji: < 5s
- Zero crashes podczas sesji
- Sync latency: < 2s

**UX:**
- Czytelny timer z odległości 2m
- Jednoznaczne przyciski
- Responsywny UI (60 FPS)

**Data:**
- 100% sesji zapisanych w logach
- Poprawne statystyki dzienne
- Zero data loss podczas sync

---

## ✅ Checklist Przed Release

- [ ] Wszystkie stringi przez i18n
- [ ] Zgodność z dark/light theme
- [ ] Auto-refresh token integration
- [ ] WebSocket real-time sync
- [ ] Popup timer always on top
- [ ] System notifications
- [ ] Sound playback (custom + system)
- [ ] Export logów do CSV
- [ ] Comprehensive unit tests
- [ ] E2E testing multi-device sync

---

**Status:** 📝 Dokumentacja gotowa - Przechodzę do implementacji UI

**Następny krok:** Stworzenie `pomodoro_view.py` z pełnym layoutem
