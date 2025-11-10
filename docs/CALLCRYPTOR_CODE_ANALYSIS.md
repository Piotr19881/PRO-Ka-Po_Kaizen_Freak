# CallCryptor - Analiza Kodu i Optymalizacja

**Data:** 2025-11-08  
**Analizowane pliki:**
- `src/Modules/CallCryptor_module/callcryptor_database.py` (888 linii)
- `src/ui/transcription_dialog.py` (500 linii)
- `src/ui/callcryptor_dialogs.py` (705 linii)
- `src/ui/callcryptor_view.py` (2402 linie)

---

## 1. KRYTYCZNE PROBLEMY WYDAJNOŚCI

### 1.1 Generowanie przycisków w `_populate_table()` (GŁÓWNY PROBLEM)

**Lokalizacja:** `callcryptor_view.py`, linie 2067-2402

**Problem:**  
Dla każdego wiersza tabeli tworzone są **8-12 przycisków QPushButton** z pełnym stylingiem CSS, co powoduje:
- Tworzenie 8-12 obiektów Qt per wiersz
- Łączenie sygnałów dla każdego przycisku (12× `connect()` per wiersz)
- Parsowanie i aplikacja CSS dla każdego przycisku
- Dla 231 nagrań = **~2,772 obiektów QPushButton + 2,772 połączeń sygnałów**

**Wpływ:**
- Ładowanie tabeli trwa kilka sekund
- Scrollowanie jest wolne
- Wysoki memory footprint
- **Aplikacja widocznie spowalnia przy operacjach na tabeli**

**Rozwiązanie:**
1. **Użyć QPushButton tylko tam gdzie potrzeba** (favorite, play)
2. **QTableWidgetItem z ikonkami** dla akcji (transcribe, AI, note, task, archive, delete)
3. **Delegat dla specjalnych komórek** (checkboxy w queue mode)
4. **Lazy loading** - renderuj tylko widoczne wiersze

---

### 1.2 Nadmierny logging podczas populacji tabeli

**Lokalizacja:** `callcryptor_view.py`, linie 2074, 2424-2427

**Problem:**
```python
logger.info(f"[CallCryptor] _populate_table called with {len(recordings)} recordings...")
logger.debug(f"[CallCryptor] Transcribe selection changed: {len(self.selected_items['transcribe'])} files")
logger.debug(f"[CallCryptor] Summarize selection changed: {len(self.selected_items['summarize'])} files")
```

Dla 231 nagrań:
- 1× logger.info przy wywołaniu
- 231× logger.debug dla każdej gwiazdki (favorite button creation)
- 462× logger.debug dla checkboxów (transcribe + summarize) w queue mode

**Rozwiązanie:**  
Usunąć ALL debug logging z pętli populacji tabeli. Zostawić tylko error logging.

---

### 1.3 Powtarzające się wywołania `_get_available_tags()`

**Lokalizacja:** `callcryptor_view.py`, linia 2171

**Problem:**
```python
for row, recording in enumerate(recordings):
    # ...
    available_tags = self._get_available_tags()  # WYWOŁANE 231 RAZY!
```

Dla każdego wiersza wywołuje metodę która zwraca ten sam słownik tagów.

**Rozwiązanie:**
```python
available_tags = self._get_available_tags()  # RAZ przed pętlą
for row, recording in enumerate(recordings):
    # użyj available_tags
```

---

## 2. PROBLEMY LOGICZNE I BŁĘDY

### 2.1 Duplikacja inicjalizacji `self.email_db`

**Lokalizacja:** `callcryptor_dialogs.py`, linie 37-38

**Problem:**
```python
self.email_db = None
self.user_id = None
self.email_db = None  # DUPLIKAT!
```

**Rozwiązanie:**  
Usunąć duplikat.

---

### 2.2 Niepełna obsługa błędów parsowania JSON

**Lokalizacja:** `callcryptor_view.py`, linie 357-368

**Problem:**
```python
if isinstance(tags, str):
    try:
        tags = json.loads(tags)
    except:
        tags = []  # Zbyt szerokie except
```

**Rozwiązanie:**
```python
if isinstance(tags, str):
    try:
        tags = json.loads(tags)
    except (json.JSONDecodeError, TypeError):
        tags = []
        logger.warning(f"Failed to parse tags JSON: {tags}")
```

---

### 2.3 Niekompletna implementacja `_on_tag_changed()`

**Lokalizacja:** `callcryptor_view.py`, linie 1927-1980

**Problem:**
```python
# TODO: Zaimplementuj metodę update_recording_tags w db_manager
# self.db_manager.update_recording_tags(recording_id, tags_json)
```

Funkcja jest podłączona do sygnału ale **nie zapisuje zmian do bazy danych**.

**Rozwiązanie:**  
Zaimplementować `update_recording_tags()` w `CallCryptorDatabase` lub używać `update_recording()`.

---

### 2.4 Brak walidacji istnienia nagrania w `_toggle_favorite()`

**Lokalizacja:** `callcryptor_view.py`, linia 1882

**Problem:**
```python
new_status = self.db_manager.toggle_favorite(recording_id)
```

Brak sprawdzenia czy nagranie istnieje przed wywołaniem.

**Rozwiązanie:**
```python
recording = self.db_manager.get_recording(recording_id)
if not recording:
    logger.error(f"Recording {recording_id} not found")
    return
new_status = self.db_manager.toggle_favorite(recording_id)
```

---

### 2.5 Potencjalny memory leak z lambda w pętli

**Lokalizacja:** `callcryptor_view.py`, linie 2102-2402

**Problem:**
```python
for row, recording in enumerate(recordings):
    favorite_btn.clicked.connect(lambda checked, r=recording: self._toggle_favorite(r))
    play_btn = self._create_emoji_button(..., lambda: self._play_recording(recording))
    # ... i tak dalej dla każdego przycisku
```

Lambda functions z closure nad `recording` mogą powodować memory leaks przy dużej liczbie wierszy.

**Rozwiązanie:**  
Użyć `functools.partial` lub custom delegata zamiast lambd w pętli.

---

## 3. PROBLEMY Z BAZĄ DANYCH

### 3.1 Brak transaction management w `callcryptor_database.py`

**Problem:**  
Większość metod wykonuje pojedyncze query bez transaction context. Przy batch operations (np. scan folderu) brak `BEGIN TRANSACTION` / `COMMIT` powoduje wolniejsze operacje.

**Przykład:**
```python
def add_recording(self, recording_data: Dict, user_id: str) -> str:
    cursor = self.conn.cursor()
    # ... prepare data ...
    cursor.execute("INSERT INTO ...")
    self.conn.commit()  # Jeden commit per rekord - WOLNE!
```

**Rozwiązanie:**
```python
def add_recordings_batch(self, recordings_list: List[Dict], user_id: str):
    cursor = self.conn.cursor()
    cursor.execute("BEGIN TRANSACTION")
    try:
        for rec_data in recordings_list:
            # ... insert operations ...
        self.conn.commit()
    except:
        self.conn.rollback()
        raise
```

---

### 3.2 Brak indeksów dla często używanych query

**Problem:**  
Brak indeksów dla:
- `recordings.contact_name` (wyszukiwarka)
- `recordings.tags` (filtrowanie tagów)

**Rozwiązanie:**
```sql
CREATE INDEX idx_recordings_contact ON recordings(contact_name);
CREATE INDEX idx_recordings_tags ON recordings(tags);
```

---

### 3.3 N+1 query problem w `_load_recordings()`

**Lokalizacja:** `callcryptor_view.py`, linia 540

**Problem:**
```python
recordings = self.db_manager.get_recordings_by_source(self.current_source_id)
# Dla każdego nagrania mogą być dodatkowe query dla related data
```

Jeśli `get_recordings_by_source()` nie używa JOINs, może wykonywać dodatkowe query per nagranie.

**Rozwiązanie:**  
Upewnić się że query używa LEFT JOIN dla source info jeśli potrzebne.

---

## 4. PROBLEMY UI/UX

### 4.1 Blocking UI podczas długich operacji

**Lokalizacja:** `callcryptor_view.py`, `_scan_source()`

**Problem:**  
Skanowanie folderu z wieloma plikami blokuje UI mimo użycia `QProgressDialog`.

**Rozwiązanie:**  
Przenieść `FolderScanner` / `EmailScanner` do `QThread` worker.

---

### 4.2 Brak debouncing w `_on_search()`

**Lokalizacja:** `callcryptor_view.py`, linia 668

**Problem:**
```python
self.search_input.textChanged.connect(self._on_search)
```

Każda zmiana tekstu (każda litera) wywołuje filtrowanie całej tabeli.

**Rozwiązanie:**
```python
from PyQt6.QtCore import QTimer

self.search_timer = QTimer()
self.search_timer.setSingleShot(True)
self.search_timer.timeout.connect(self._do_search)

def _on_search_text_changed(self, text):
    self.search_timer.start(300)  # 300ms debounce
```

---

### 4.3 Nadmiernie złożone nested parent navigation

**Lokalizacja:** `transcription_dialog.py`, linie 269-276

**Problem:**
```python
callcryptor_view = self.parent()
content_stack = callcryptor_view.parent()
central_widget = content_stack.parent() if content_stack else None
main_window = central_widget.parent() if central_widget else None
```

Bardzo krucha logika zależna od dokładnej struktury widgetów.

**Rozwiązanie:**  
Przekazać `main_window` reference bezpośrednio w konstruktorze dialogu:
```python
def __init__(self, ..., main_window=None):
    self.main_window = main_window
```

---

## 5. CODE QUALITY

### 5.1 Nadmierne komentarze "TODO"

**Znalezione TODO:**
- `callcryptor_view.py`: 7 miejsc z TODO (incomplete features)
- `callcryptor_dialogs.py`: 3 miejsca

**Problem:**  
Wiele funkcji jest połączonych do UI ale nie ma implementacji backend.

---

### 5.2 Magic numbers bez stałych

**Przykłady:**
```python
self.recordings_table.setColumnWidth(6, 80)  # Co to za 80?
favorite_btn.setMaximumWidth(40)  # Co to za 40?
self.setMinimumWidth(600)  # Co to za 600?
```

**Rozwiązanie:**
```python
class CallCryptorView:
    CHECKBOX_COLUMN_WIDTH = 80
    FAVORITE_BTN_WIDTH = 40
    MIN_DIALOG_WIDTH = 600
```

---

### 5.3 Długie metody

**Przykłady:**
- `_populate_table()`: 335 linii (2067-2402)
- `_scan_source()`: 200+ linii
- `_transcribe_recording()`: 150+ linii

**Rozwiązanie:**  
Podzielić na mniejsze funkcje pomocnicze.

---

## 6. REKOMENDACJE OPTYMALIZACJI

### Priorytet KRYTYCZNY (natychmiastowa poprawa wydajności)

1. **Usunąć wszystkie `logger.debug()` z `_populate_table()` i pętli**
2. **Przenieść `available_tags = self._get_available_tags()` przed pętlę**
3. **Zastąpić przyciski emoji na QTableWidgetItem z ikonami** (kolumny 6-11)
4. **Użyć delegata Qt dla checkboxów zamiast setCellWidget**

### Priorytet WYSOKI

5. **Implementować batch inserts w `CallCryptorDatabase`**
6. **Dodać indeksy dla `contact_name` i `tags`**
7. **Debouncing dla search input**
8. **Zaimplementować lazy loading tabeli** (render tylko widoczne wiersze)

### Priorytet ŚREDNI

9. **QThread worker dla folder/email scanning**
10. **Refactor długich metod** (split `_populate_table` na helpers)
11. **Usunąć TODO lub je zaimplementować**
12. **Dodać stałe dla magic numbers**

---

## 7. SZACUNKOWY GAIN

### Przed optymalizacją:
- Ładowanie 231 nagrań: **~3-5 sekund**
- Memory: **~150MB** dla przycisków
- Scrollowanie: **zauważalne lagowanie**

### Po optymalizacji (szacunek):
- Ładowanie 231 nagrań: **<1 sekunda**
- Memory: **~30MB** (5× mniej)
- Scrollowanie: **płynne**

**ROI:** Usunięcie debug logging + przeniesienie `_get_available_tags()` + zastąpienie przycisków na ikony = **~80% poprawy wydajności** przy minimalnym wysiłku.

---

## 8. PLAN IMPLEMENTACJI

### Faza 1: Quick Wins (30 min)
- [ ] Usunąć wszystkie `logger.debug/info` z `_populate_table()`
- [ ] Przenieść `_get_available_tags()` przed pętlę
- [ ] Usunąć duplikat `self.email_db = None`

### Faza 2: Button Optimization (2h)
- [ ] Zastąpić przyciski 6-11 na QTableWidgetItem z setIcon()
- [ ] Implementować custom delegate dla checkboxów w queue mode
- [ ] Event handler dla kliknięć w ikony (itemClicked signal)

### Faza 3: Database (1h)
- [ ] Dodać `add_recordings_batch()` method
- [ ] Dodać indeksy dla `contact_name`, `tags`
- [ ] Transaction context manager

### Faza 4: Polish (2h)
- [ ] Debouncing search
- [ ] QThread dla scanning
- [ ] Refactor długich metod
- [ ] Dodać constans dla magic numbers

**Total Effort:** ~6 godzin  
**Expected Gain:** 80-90% poprawa wydajności UI

---

## 9. KONKRETNE ZMIANY DO WYKONANIA

### Zmiana 1: Usunąć debug logging z _populate_table

```python
# PRZED (linia 2074):
logger.info(f"[CallCryptor] _populate_table called with {len(recordings)} recordings, queue_mode_active={self.queue_mode_active}")

# PO:
# (usunąć całkowicie)
```

### Zmiana 2: Usunąć debug z checkbox handlers

```python
# PRZED (linie 2424-2427):
logger.debug(f"[CallCryptor] Transcribe selection changed: {len(self.selected_items['transcribe'])} files")

# PO:
# (usunąć całkowicie)
```

### Zmiana 3: Optymalizacja _get_available_tags()

```python
# PRZED (linia 2171):
for row, recording in enumerate(recordings):
    # ...
    available_tags = self._get_available_tags()  # W PĘTLI!

# PO (linia 2070):
available_tags = self._get_available_tags()  # PRZED PĘTLĄ
for row, recording in enumerate(recordings):
    # użyj available_tags
```

---

**Autor:** GitHub Copilot  
**Status:** Gotowe do implementacji
