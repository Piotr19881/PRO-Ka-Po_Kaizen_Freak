# Analiza Modułu Pomodoro - Lista Zadań do Implementacji

## 📊 Status Obecny

### ✅ ZAIMPLEMENTOWANE (Szkielet UI):
1. **Interfejs użytkownika (pomodoro_view.py)**
   - ✅ Layout główny (1/3 akcje + 2/3 ustawienia)
   - ✅ Timer z dużym wyświetlaczem (120pt czcionka)
   - ✅ Progress bar (działający, 0-100%)
   - ✅ Przyciski kontroli (Start/Pauza, Reset, Pomiń, Stop)
   - ✅ Ustawienia czasów (praca, krótka/długa przerwa, liczba sesji)
   - ✅ Checkboxy (auto-start, dźwięki, popup)
   - ✅ Liczniki sesji (dziś wykonano, sesja N/X)
   - ✅ Tłumaczenia i18n (PL, EN, DE - 35 kluczy)
   - ✅ Kompatybilność z systemem motywów
   - ✅ Podstawowa logika timera (odliczanie)
   - ✅ Zmiana kolorów (czerwony dla pracy, niebieski dla przerwy)

2. **Specyfikacja (POMODORO_SPECIFICATION.md)**
   - ✅ Pełna dokumentacja funkcjonalności
   - ✅ Schemat bazy danych (PostgreSQL s05_pomodoro)
   - ✅ Plan implementacji

3. **Schemat bazy danych (pomodoro_schema.sql)**
   - ✅ Tabela `session_topics` (tematy sesji)
   - ✅ Tabela `session_logs` (historia sesji)
   - ✅ Triggery (auto-update, statystyki)
   - ✅ Widoki (daily_statistics, top_topics)

---

## ⏳ DO ZAIMPLEMENTOWANIA

### 🔴 PRIORYTET WYSOKI (Core Functionality)

#### 1. **Logika Biznesowa - PomodoroManager**
**Plik:** `src/Modules/Pomodoro_module/pomodoro_logic.py`

**Funkcjonalności:**
- [ ] Zarządzanie stanem sesji (NOT_STARTED, RUNNING, PAUSED, COMPLETED)
- [ ] Logika cyklu Pomodoro (praca → krótka przerwa → ... → długa przerwa)
- [ ] Automatyczne przełączanie między sesjami
- [ ] Obsługa auto-mode vs manual-mode
- [ ] Walidacja danych wejściowych
- [ ] Emitowanie sygnałów Qt dla UI

**Zależności:**
- Integracja z `pomodoro_view.py` (sygnały/sloty)
- Zarządzanie timerem QTimer
- Wywołania callback do UI

**Szacowany czas:** 4-6h

---

#### 2. **Modele Bazy Danych - SQLAlchemy**
**Plik:** `src/Modules/Pomodoro_module/pomodoro_models.py`

**Modele do stworzenia:**
```python
class SessionTopic(Base):
    """Model tematu sesji"""
    # Zgodny ze schematem s05_pomodoro.session_topics
    
class SessionLog(Base):
    """Model logu sesji"""
    # Zgodny ze schematem s05_pomodoro.session_logs
```

**Funkcjonalności:**
- [ ] Definicje modeli SQLAlchemy
- [ ] Relacje między tabelami (SessionLog → SessionTopic)
- [ ] Metody helper (to_dict, from_dict)
- [ ] Walidacje Pydantic (jeśli potrzebne)

**Zależności:**
- SQLAlchemy 2.x
- Zgodność ze schematem PostgreSQL
- Sync z LocalDatabase (SQLite)

**Szacowany czas:** 2-3h

---

#### 3. **Lokalna Baza Danych - SQLite**
**Plik:** `src/Modules/Pomodoro_module/pomodoro_local_database.py`

**Funkcjonalności:**
- [ ] Inicjalizacja SQLite (plik: `data/pomodoro.db`)
- [ ] CRUD dla `session_topics`:
  - `create_topic(user_id, name, color, icon) → SessionTopic`
  - `get_topics(user_id) → List[SessionTopic]`
  - `update_topic(topic_id, **kwargs) → bool`
  - `delete_topic(topic_id) → bool` (soft delete)
  
- [ ] CRUD dla `session_logs`:
  - `create_log(user_id, topic_id, session_data) → SessionLog`
  - `get_logs(user_id, filters) → List[SessionLog]`
  - `get_today_stats(user_id) → dict`
  - `delete_log(log_id) → bool`

- [ ] Migracja schematu (utworzenie tabel lokalnych)
- [ ] Synchronizacja version dla conflict resolution

**Wzorzec:** Podobny do `alarm_local_database.py`

**Szacowany czas:** 4-5h

---

#### 4. **Integracja z SoundManager**
**Lokalizacja:** `pomodoro_view.py` → metoda `_play_sound()`

**Funkcjonalności:**
- [ ] Import `SoundManager` z `src/utils/sound_manager.py`
- [ ] Odtwarzanie dźwięku końca pracy (jeśli checkbox włączony)
- [ ] Odtwarzanie dźwięku końca przerwy (jeśli checkbox włączony)
- [ ] Wykorzystanie dźwięków z ustawień globalnych (Ustawienia/Ogólne)
- [ ] Fallback do systemowych dźwięków

**Kod (przykład):**
```python
def _play_sound(self, sound_type: str):
    """Odtwarza dźwięk powiadomienia"""
    from ..utils.sound_manager import SoundManager
    
    if sound_type == "work_end" and self.sound_work_end_check.isChecked():
        # Pobierz dźwięk z ustawień globalnych
        sound_path = self._get_work_end_sound()
        SoundManager.play_sound(sound_path)
    elif sound_type == "break_end" and self.sound_break_end_check.isChecked():
        sound_path = self._get_break_end_sound()
        SoundManager.play_sound(sound_path)
```

**Zależności:**
- Dostęp do ustawień globalnych (`config` lub `settings`)
- SoundManager kompatybilny z PyQt6

**Szacowany czas:** 2h

---

#### 5. **Zapis Sesji do Bazy Danych**
**Lokalizacja:** `pomodoro_view.py` → metoda `_finish_current_session()`

**Funkcjonalności:**
- [ ] Utworzenie obiektu `SessionLog` z danymi sesji:
  - `user_id`
  - `topic_id` (jeśli wybrany temat)
  - `session_date` (dzisiaj)
  - `started_at` (timestamp rozpoczęcia)
  - `ended_at` (timestamp zakończenia)
  - `work_duration` / `short_break_duration` / `long_break_duration`
  - `actual_work_time` / `actual_break_time`
  - `session_type` ('work', 'short_break', 'long_break')
  - `status` ('completed', 'interrupted', 'skipped')
  - `pomodoro_count` (1-4)
  
- [ ] Zapis do LocalDatabase
- [ ] Aktualizacja statystyk dziennych w UI
- [ ] Wywołanie sync do serwera (w tle)

**Wzorzec:** Podobny do zapisywania alarmów/timerów

**Szacowany czas:** 3h

---

### 🟡 PRIORYTET ŚREDNI (Enhanced UX)

#### 6. **Popup Timer Window**
**Plik:** `src/ui/pomodoro_popup_timer.py` (NOWY)

**Funkcjonalności:**
- [ ] Małe okno always-on-top
- [ ] Minimalistyczny design:
  - Tytuł sesji
  - Duży zegar (80pt)
  - Licznik sesji N/X
  - Brak przycisków (tylko zamknięcie)
  
- [ ] Synchronizacja z głównym timerem
- [ ] Możliwość przeciągania
- [ ] Zamknięcie NIE przerywa sesji

**Kod (szkielet):**
```python
class PomodoroPopupTimer(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.WindowStaysOnTopHint | 
            Qt.WindowType.FramelessWindowHint
        )
        self.setWindowTitle("Pomodoro Timer")
        self._init_ui()
```

**Integracja:**
- Otwieranie przez checkbox "Otwórz licznik w popup"
- Aktualizacja czasu co sekundę (slot od głównego timera)

**Szacowany czas:** 3-4h

---

#### 7. **Dialog "Nadaj Tytuł" - Wybór z Listy**
**Lokalizacja:** `pomodoro_view.py` → `SessionTitleDialog`

**Funkcjonalności:**
- [ ] Dropdown z istniejącymi tematami (z LocalDatabase)
- [ ] Możliwość wpisania nowego tematu
- [ ] Wybór koloru tematu (QColorDialog)
- [ ] Wybór ikony/emoji (lista predefiniowanych)
- [ ] Zapis nowego tematu do bazy

**Kod (rozszerzenie):**
```python
class SessionTitleDialog(QDialog):
    def __init__(self, current_title: str, topics: List[SessionTopic], parent=None):
        # Dropdown z tematami
        # Pole "Nowy temat"
        # Color picker
        # Icon selector
```

**Szacowany czas:** 3h

---

#### 8. **Dialog Logów Sesji**
**Plik:** `src/ui/pomodoro_logs_dialog.py` (NOWY)

**Funkcjonalności:**
- [ ] Tabela z historią sesji:
  - Kolumny: Data, Godzina, Typ, Temat, Czas trwania, Status
  
- [ ] Filtry:
  - Data (dziś / tydzień / miesiąc / wszystkie)
  - Typ sesji (praca / przerwy / wszystkie)
  - Temat (dropdown)
  - Status (ukończone / przerwane / pominięte)
  
- [ ] Sortowanie (kliknięcie w nagłówek kolumny)
- [ ] Export do CSV
- [ ] Wykres słupkowy (sesje per dzień - opcjonalnie)

**Biblioteki:**
- QTableWidget
- matplotlib (dla wykresów - opcjonalnie)

**Szacowany czas:** 5-6h

---

#### 9. **Popup Pytania (Manual Mode)**
**Plik:** `src/ui/pomodoro_confirm_dialog.py` (NOWY)

**Funkcjonalności:**
- [ ] Mały dialog z pytaniem:
  - "Przerwa gotowa. Rozpocząć?" (po zakończeniu pracy)
  - "Kolejna sesja gotowa. Rozpocząć?" (po zakończeniu przerwy)
  
- [ ] Przyciski: "Tak" / "Nie" / "Zamknij"
- [ ] Dźwięk powiadomienia przy otwarciu
- [ ] Auto-zamknięcie po 30s bez akcji (opcjonalnie)

**Integracja:**
- Wywoływanie gdy auto-checkboxy są OFF
- Callback do `_on_start_pause_clicked()` przy "Tak"

**Szacowany czas:** 2h

---

### 🟢 PRIORYTET NISKI (Backend & Sync)

#### 10. **API Client - FastAPI Endpoints**
**Plik:** `src/Modules/Pomodoro_module/pomodoro_api_client.py` (NOWY)

**Endpointy do obsługi:**
```python
# Topics
GET    /api/v1/pomodoro/topics          # Lista tematów
POST   /api/v1/pomodoro/topics          # Nowy temat
PUT    /api/v1/pomodoro/topics/{id}     # Update tematu
DELETE /api/v1/pomodoro/topics/{id}     # Delete tematu

# Logs
GET    /api/v1/pomodoro/logs            # Lista logów (z filtrami)
POST   /api/v1/pomodoro/logs            # Nowy log
GET    /api/v1/pomodoro/logs/{id}       # Pojedynczy log
DELETE /api/v1/pomodoro/logs/{id}       # Delete logu

# Stats
GET    /api/v1/pomodoro/stats/today     # Statystyki dzienne
GET    /api/v1/pomodoro/stats/summary   # Podsumowanie (tydzień/miesiąc)

# Bulk sync
POST   /api/v1/pomodoro/sync            # Bulk sync (topics + logs)
```

**Funkcjonalności:**
- [ ] Klasa `PomodoroAPIClient` (wzorowany na `AlarmsAPIClient`)
- [ ] Obsługa JWT auth (auto-refresh token)
- [ ] Error handling (retry logic)
- [ ] Metody dla każdego endpointu

**Wzorzec:** Dokładnie jak `alarm_api_client.py`

**Szacowany czas:** 4-5h

---

#### 11. **Backend FastAPI Router**
**Plik:** `Render_upload/routes/pomodoro_router.py` (NOWY)

**Funkcjonalności:**
- [ ] Router z wszystkimi endpointami (patrz punkt 10)
- [ ] JWT authentication (`Depends(get_current_user)`)
- [ ] Walidacja Pydantic (request/response models)
- [ ] CRUD operations na PostgreSQL (s05_pomodoro)
- [ ] WebSocket endpoint dla real-time sync (opcjonalnie)

**Integracja:**
- Dodanie routera do `main.py` (Render)
- Testy API (ręczne lub pytest)

**Szacowany czas:** 6-8h

---

#### 12. **Sync Manager**
**Plik:** `src/Modules/Pomodoro_module/pomodoro_sync_manager.py` (NOWY)

**Funkcjonalności:**
- [ ] Automatyczna synchronizacja co N sekund (30s domyślnie)
- [ ] Wykrywanie konfliktów (version-based)
- [ ] Strategia rozwiązywania konfliktów:
  - Server wins (dla topics)
  - Last-write-wins (dla logs)
  
- [ ] Background thread (QThread)
- [ ] Retry logic (max 3 próby)
- [ ] Callback do UI (success/error)

**Wzorzec:** Dokładnie jak `alarms_sync_manager.py`

**Szacowany czas:** 5-6h

---

#### 13. **WebSocket Real-Time Sync (Opcjonalnie)**
**Plik:** `src/Modules/Pomodoro_module/pomodoro_websocket.py` (NOWY)

**Funkcjonalności:**
- [ ] Połączenie WebSocket z serwerem
- [ ] Nasłuchiwanie na zmiany (topics/logs)
- [ ] Automatyczna aktualizacja UI w czasie rzeczywistym
- [ ] Reconnection logic

**Wzorzec:** Jak `alarm_websocket_client.py`

**Szacowany czas:** 4-5h

---

### 🔵 PRIORYTET OPCJONALNY (Nice to Have)

#### 14. **Integracja z Systemem Motywów**
**Lokalizacja:** `pomodoro_view.py` → metoda `_apply_theme()`

**Funkcjonalności:**
- [ ] Odczyt aktualnego motywu (dark/light)
- [ ] Dynamiczne style dla:
  - Timer display (kolor tła)
  - Progress bar (kolory)
  - Przyciski (hover/pressed)
  - GroupBoxy (obramowanie)
  
- [ ] Obsługa zmiany motywu w runtime

**Szacowany czas:** 2-3h

---

#### 15. **Powiadomienia Systemowe**
**Funkcjonalności:**
- [ ] Windows notification po zakończeniu sesji
- [ ] Treść: "Sesja pracy zakończona! Czas na przerwę."
- [ ] Kliknięcie → fokus na popup timer / główne okno
- [ ] Integracja z PyQt6 (QSystemTrayIcon lub win10toast)

**Szacowany czas:** 2h

---

#### 16. **System Tray Integration**
**Funkcjonalności:**
- [ ] Ikona w system tray zmienia kolor (praca/przerwa)
- [ ] Tooltip pokazuje pozostały czas
- [ ] Menu kontekstowe:
  - Start/Pauza
  - Stop
  - Pokaż okno główne
  - Wyjście

**Szacowany czas:** 3h

---

#### 17. **Wykresy i Statystyki**
**Funkcjonalności:**
- [ ] Wykres słupkowy - sesje per dzień (matplotlib)
- [ ] Wykres kołowy - dystrybucja tematów
- [ ] Średni czas skupienia
- [ ] Najproduktywniejsze godziny dnia

**Biblioteka:** matplotlib + PyQt6 integration

**Szacowany czas:** 4-5h

---

#### 18. **Zapisywanie Ustawień**
**Funkcjonalności:**
- [ ] Zapis ustawień timera do `data/pomodoro_settings.json`:
  - Czas pracy
  - Czas krótkie/długiej przerwy
  - Liczba sesji
  - Auto-checkboxy
  - Sound-checkboxy
  - Ostatni wybrany temat
  
- [ ] Wczytywanie przy starcie aplikacji

**Szacowany czas:** 1-2h

---

## 📋 Podsumowanie Priorytetu

### **MUST HAVE** (Minimum Viable Product):
1. ✅ Logika biznesowa (PomodoroManager)
2. ✅ Modele bazy danych (SQLAlchemy)
3. ✅ Lokalna baza danych (SQLite CRUD)
4. ✅ Integracja z SoundManager
5. ✅ Zapis sesji do bazy
6. ✅ Zapisywanie ustawień

**Szacowany czas: 16-21h**

### **SHOULD HAVE** (Enhanced UX):
7. ✅ Popup Timer Window
8. ✅ Dialog wyboru tematu
9. ✅ Dialog logów sesji
10. ✅ Popup pytania (manual mode)

**Szacowany czas: 13-15h**

### **COULD HAVE** (Backend & Multi-Device):
11. ✅ API Client
12. ✅ Backend FastAPI Router
13. ✅ Sync Manager
14. ⚪ WebSocket (opcjonalnie)

**Szacowany czas: 15-19h**

### **NICE TO HAVE** (Polish):
15. ⚪ System motywów
16. ⚪ Powiadomienia systemowe
17. ⚪ System tray
18. ⚪ Wykresy

**Szacowany czas: 11-13h**

---

## 🚀 Sugerowana Kolejność Implementacji

### **Faza 1: Core (1-2 dni)**
1. `pomodoro_models.py` - Modele bazy danych
2. `pomodoro_local_database.py` - CRUD SQLite
3. `pomodoro_logic.py` - Manager logiki biznesowej
4. Integracja `_play_sound()` - SoundManager
5. Zapis sesji `_finish_current_session()` - LocalDatabase

**Rezultat:** Działający timer z zapisem do lokalnej bazy

---

### **Faza 2: UX (1-2 dni)**
6. `pomodoro_popup_timer.py` - Popup timer window
7. Rozszerzenie `SessionTitleDialog` - Wybór tematów
8. `pomodoro_logs_dialog.py` - Historia sesji
9. `pomodoro_confirm_dialog.py` - Manual mode popupy
10. Zapisywanie ustawień do JSON

**Rezultat:** Kompletny UX z wszystkimi dialogami

---

### **Faza 3: Backend (2-3 dni)**
11. `pomodoro_router.py` - FastAPI endpoints (Backend)
12. Utworzenie schematu w PostgreSQL (Render.com)
13. `pomodoro_api_client.py` - REST client
14. `pomodoro_sync_manager.py` - Auto-sync
15. Testy API (ręczne lub pytest)

**Rezultat:** Multi-device sync działający

---

### **Faza 4: Polish (1 dzień - opcjonalnie)**
16. System motywów
17. Powiadomienia systemowe
18. System tray integration
19. Wykresy i statystyki

**Rezultat:** Professional-grade application

---

## 🎯 Najbliższe Kroki (MVP)

### **Krok 1:** Modele bazy danych
```python
# src/Modules/Pomodoro_module/pomodoro_models.py
from sqlalchemy import Column, String, Integer, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship

class SessionTopic(Base):
    __tablename__ = 'session_topics'
    __table_args__ = {'schema': 's05_pomodoro'}
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), nullable=False)
    name = Column(String(100), nullable=False)
    # ... (pozostałe pola)
```

### **Krok 2:** Lokalna baza danych
```python
# src/Modules/Pomodoro_module/pomodoro_local_database.py
class PomodoroLocalDatabase:
    def __init__(self, db_path: Path):
        # Inicjalizacja SQLite
        
    def create_topic(self, user_id, name, color) -> SessionTopic:
        # CRUD operations
```

### **Krok 3:** Manager logiki
```python
# src/Modules/Pomodoro_module/pomodoro_logic.py
class PomodoroManager(QObject):
    session_state_changed = pyqtSignal(str)  # NOT_STARTED, RUNNING, PAUSED, COMPLETED
    
    def start_session(self):
        # Logika startu
        
    def pause_session(self):
        # Logika pauzy
```

---

**Status:** Gotowe do rozpoczęcia implementacji! 🚀
