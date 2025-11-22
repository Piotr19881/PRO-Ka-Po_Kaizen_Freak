# 📋 MODUŁ SHORTCUTS - PLAN IMPLEMENTACJI

**Data utworzenia:** 2025-11-02  
**Wersja:** 1.0  
**Status:** W TRAKCIE IMPLEMENTACJI

---

## 📊 STAN OBECNY - ZAIMPLEMENTOWANE FUNKCJONALNOŚCI

### ✅ Interfejs użytkownika (100%)
- [x] Formularz dodawania skrótów (nazwa, rodzaj, wartość, tryb, opis, status)
- [x] Tabela listy skrótów (Lp, Nazwa, Skrót/Fraza, Tryb akcji, Status)
- [x] Przechwytywanie kombinacji klawiszy (Ctrl+Alt+Shift+Win + klawisz)
- [x] Wsparcie dla magicznych fraz (edytowalny tekst)
- [x] Nagrywanie sekwencji kliknięć z nakładką na wszystkie monitory
- [x] Testowanie sekwencji kliknięć z animacją
- [x] Przyciski: Dodaj, Edytuj, Usuń, Import, Export, Odśwież

### ✅ Zarządzanie danymi (100%)
- [x] Dodawanie skrótów do listy
- [x] Edycja istniejących skrótów
- [x] Usuwanie skrótów
- [x] Import/Export do JSON
- [x] Zapisywanie/ładowanie z pliku (shortcuts_data.json)
- [x] Walidacja unikalności skrótów

### ✅ Rodzaje skrótów (100%)
- [x] Kombinacja klawiszy
- [x] Przytrzymaj klawisz
- [x] Magiczna fraza

### ⚠️ Tryby akcji (ZDEFINIOWANE, NIE WYKONYWANE - 0%)
- [x] Wklej tekst (zdefiniowany)
- [x] Otwórz aplikację (zdefiniowany)
- [x] Otwórz plik (zdefiniowany)
- [x] Polecenie PowerShell (zdefiniowany)
- [x] Polecenie wiersza poleceń (zdefiniowany)
- [x] Wykonaj sekwencję kliknięć (zdefiniowany)

---

## ❌ FUNKCJONALNOŚCI DO IMPLEMENTACJI

### 🔴 PRIORYTET 1: KRYTYCZNE - Podstawowe działanie

#### 1. System aktywacji skrótów globalnych
**Status:** ❌ NIE ZAIMPLEMENTOWANE  
**Priorytet:** KRYTYCZNY  
**Czas:** 2-3 dni

**Zadania:**
- [ ] Instalacja biblioteki `pynput` lub `keyboard`
- [ ] Utworzenie klasy `HotkeyListener` do nasłuchiwania globalnych skrótów
- [ ] Obsługa kombinacji klawiszy (Ctrl+Alt+N, Shift+F1, itp.)
- [ ] Obsługa przytrzymania pojedynczego klawisza
- [ ] Detekcja magicznych fraz (monitoring bufora klawiatury)
- [ ] Uruchomienie listenera w osobnym wątku/procesie
- [ ] Mapowanie wykrytych skrótów do akcji
- [ ] Obsługa włączania/wyłączania systemu

**Wymagane biblioteki:**
```python
pip install pynput
# LUB
pip install keyboard
```

**Klucze techniczne:**
- `pynput.keyboard.Listener` - globalne przechwytywanie klawiszy
- `threading.Thread` - uruchomienie w tle
- Sprawdzanie `shortcut_type` i `shortcut_value` z bazy skrótów

---

#### 2. Wykonywanie akcji
**Status:** ❌ NIE ZAIMPLEMENTOWANE  
**Priorytet:** KRYTYCZNY  
**Czas:** 1-2 dni

**Zadania:**

##### 2.1 Wklej tekst
- [ ] Instalacja `pyperclip`
- [ ] Kopiowanie tekstu do schowka
- [ ] Symulacja Ctrl+V za pomocą `pynput`
- [ ] Obsługa wieloliniowego tekstu
- [ ] Przywracanie poprzedniej zawartości schowka

**Implementacja:**
```python
import pyperclip
from pynput.keyboard import Key, Controller

def paste_text(text):
    old_clipboard = pyperclip.paste()
    pyperclip.copy(text)
    keyboard = Controller()
    keyboard.press(Key.ctrl)
    keyboard.press('v')
    keyboard.release('v')
    keyboard.release(Key.ctrl)
    # Opcjonalnie: przywróć stary schowek
```

##### 2.2 Otwórz aplikację
- [ ] Użycie `subprocess.Popen()` dla .exe
- [ ] Walidacja ścieżki do pliku
- [ ] Obsługa błędów (plik nie istnieje)
- [ ] Timeout wykonania

**Implementacja:**
```python
import subprocess
import os

def open_application(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Nie znaleziono: {path}")
    subprocess.Popen(path, shell=True)
```

##### 2.3 Otwórz plik
- [ ] Użycie `os.startfile()` dla Windows
- [ ] Walidacja ścieżki
- [ ] Obsługa różnych typów plików

**Implementacja:**
```python
import os

def open_file(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Nie znaleziono: {path}")
    os.startfile(path)
```

##### 2.4 Polecenie PowerShell
- [ ] Użycie `subprocess.run()` z PowerShell
- [ ] Przechwytywanie stdout/stderr
- [ ] Timeout wykonania (domyślnie 30s)
- [ ] Obsługa błędów wykonania

**Implementacja:**
```python
import subprocess

def run_powershell(command, timeout=30):
    result = subprocess.run(
        ['powershell', '-Command', command],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.stdout, result.stderr
```

##### 2.5 Polecenie wiersza poleceń (CMD)
- [ ] Użycie `subprocess.run()` z cmd
- [ ] Przechwytywanie output
- [ ] Timeout wykonania
- [ ] Obsługa błędów

**Implementacja:**
```python
import subprocess

def run_cmd(command, timeout=30):
    result = subprocess.run(
        ['cmd', '/c', command],
        capture_output=True,
        text=True,
        timeout=timeout
    )
    return result.stdout, result.stderr
```

##### 2.6 Wykonaj sekwencję kliknięć
- [ ] Parser JSON z sekwencją
- [ ] Instalacja `pyautogui` lub użycie `pynput.mouse`
- [ ] Symulacja kliknięć z opóźnieniami czasowymi
- [ ] Obsługa lewego/prawego/środkowego przycisku
- [ ] Walidacja współrzędnych

**Implementacja:**
```python
import json
import time
from pynput.mouse import Button, Controller

def execute_click_sequence(sequence_json):
    clicks = json.loads(sequence_json)
    mouse = Controller()
    start_time = time.time()
    
    for click in clicks:
        # Czekaj do właściwego czasu
        target_time = click['time_offset'] / 1000.0  # ms -> s
        while (time.time() - start_time) < target_time:
            time.sleep(0.01)
        
        # Przesuń mysz
        mouse.position = (click['x'], click['y'])
        
        # Kliknij
        button = Button.left
        if click['button'] == 'right':
            button = Button.right
        elif click['button'] == 'middle':
            button = Button.middle
        
        mouse.click(button, 1)
```

**Wymagane biblioteki:**
```python
pip install pyperclip
pip install pynput
# LUB
pip install pyautogui
```

---

#### 3. Zarządzanie stanem skrótów
**Status:** ❌ NIE ZAIMPLEMENTOWANE  
**Priorytet:** WYSOKI  
**Czas:** 0.5 dnia

**Zadania:**
- [ ] Dodanie przycisku "Uruchom system skrótów" / "Zatrzymaj system"
- [ ] Flaga `system_active` w głównej klasie
- [ ] Filtrowanie tylko włączonych skrótów (`enabled=True`)
- [ ] Wskaźnik wizualny stanu systemu (zielony/czerwony)
- [ ] Ikona statusu w pasku tytułu
- [ ] Tooltip z liczbą aktywnych skrótów

**Implementacja:**
```python
class ShortcutsModule(QMainWindow):
    def __init__(self):
        # ...
        self.system_active = False
        self.hotkey_listener = None
    
    def toggle_system(self):
        if self.system_active:
            self.stop_system()
        else:
            self.start_system()
    
    def start_system(self):
        active_shortcuts = [s for s in self.shortcuts if s['enabled']]
        # Uruchom listener
        self.system_active = True
        self.update_status_indicator()
    
    def stop_system(self):
        # Zatrzymaj listener
        self.system_active = False
        self.update_status_indicator()
```

---

### 🟡 PRIORYTET 2: WAŻNE - Rozszerzone funkcje

#### 4. Wykonywanie sekwencji kliknięć
**Status:** ❌ NIE ZAIMPLEMENTOWANE  
**Priorytet:** ŚREDNI  
**Czas:** 1 dzień

(Szczegóły w sekcji 2.6 powyżej)

---

### 🟢 PRIORYTET 3: DODATKOWE - Usprawnienia

#### 5. System tray / Działanie w tle
**Status:** ❌ NIE ZAIMPLEMENTOWANE  
**Priorytet:** NISKI  
**Czas:** 1 dzień

**Zadania:**
- [ ] Dodanie `QSystemTrayIcon`
- [ ] Ikona w zasobniku systemowym
- [ ] Menu kontekstowe (Pokaż/Ukryj, Włącz/Wyłącz, Wyjście)
- [ ] Minimalizacja do tray zamiast zamykania
- [ ] Powiadomienia z tray
- [ ] Autostart z systemem Windows (wpis w rejestrze)

**Implementacja:**
```python
from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtGui import QIcon, QAction

class ShortcutsModule(QMainWindow):
    def create_tray_icon(self):
        self.tray_icon = QSystemTrayIcon(self)
        self.tray_icon.setIcon(QIcon("icon.png"))
        
        tray_menu = QMenu()
        show_action = QAction("Pokaż", self)
        show_action.triggered.connect(self.show)
        tray_menu.addAction(show_action)
        
        quit_action = QAction("Wyjście", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
```

---

#### 6. Logi i diagnostyka
**Status:** ❌ NIE ZAIMPLEMENTOWANE  
**Priorytet:** NISKI  
**Czas:** 0.5 dnia

**Zadania:**
- [ ] Panel logów w interfejsie (QTextEdit readonly)
- [ ] Logowanie wywołanych skrótów z timestampem
- [ ] Logowanie błędów wykonania
- [ ] Eksport logów do pliku .txt
- [ ] Czyszczenie starych logów
- [ ] Filtrowanie logów (błędy/wszystkie)

**Format logu:**
```
[2025-11-02 14:32:15] EXECUTED: "Otwórz Notatnik" (Ctrl+Alt+N)
[2025-11-02 14:32:45] ERROR: "Test PowerShell" - Timeout wykonania
[2025-11-02 14:33:10] EXECUTED: "Wklej tekst" (magiczna fraza: hello)
```

---

#### 7. Ustawienia zaawansowane
**Status:** ❌ NIE ZAIMPLEMENTOWANE  
**Priorytet:** NISKI  
**Czas:** 1 dzień

**Zadania:**
- [ ] Okno ustawień (QDialog)
- [ ] Opóźnienie wykonania akcji (ms)
- [ ] Timeout dla poleceń (PowerShell/CMD)
- [ ] Włącz/wyłącz powiadomienia
- [ ] Tryb debugowania (verbose logs)
- [ ] Zapis ustawień do config.json

---

#### 8. Bezpieczeństwo
**Status:** ❌ NIE ZAIMPLEMENTOWANE  
**Priorytet:** NISKI  
**Czas:** 1 dzień

**Zadania:**
- [ ] Potwierdzenie przed wykonaniem poleceń PowerShell/CMD
- [ ] Lista zaufanych komend
- [ ] Walidacja ścieżek (tylko istniejące pliki)
- [ ] Timeout wykonania (kill po X sekundach)
- [ ] Sandbox/izolacja dla skryptów
- [ ] Logowanie wszystkich wykonanych akcji

---

### 🔵 PRIORYTET 4: PRZYSZŁOŚĆ - Zaawansowane

#### 9. Zaawansowane funkcje skrótów
**Status:** ❌ NIE ZAPLANOWANE  
**Priorytet:** BARDZO NISKI  
**Czas:** 3-5 dni

**Pomysły:**
- Makra (łączenie wielu akcji)
- Warunkowe wykonanie
- Zmienne środowiskowe
- Parametry dynamiczne (input dialogs)
- Skrypty Python inline
- Harmonogram czasowy (wykonaj o 14:00)

---

#### 10. Optymalizacja UX
**Status:** ❌ NIE ZAPLANOWANE  
**Priorytet:** BARDZO NISKI  
**Czas:** 2 dni

**Pomysły:**
- Wyszukiwanie w tabeli
- Sortowanie kolumn
- Grupy/kategorie
- Eksport do CSV/XML
- Duplikowanie skrótów
- Masowa edycja

---

## 📦 WYMAGANE BIBLIOTEKI

### Zainstalowane:
- ✅ PyQt6

### Do instalacji (FAZA 1):
```bash
pip install pynput
pip install pyperclip
pip install pyautogui  # Opcjonalnie, alternatywa dla pynput
```

### Opcjonalne (późniejsze fazy):
```bash
pip install keyboard  # Alternatywa dla pynput
pip install pillow    # Dla pyautogui (screenshots)
```

---

## 🎯 PLAN IMPLEMENTACJI - HARMONOGRAM

### ✅ FAZA 0: Przygotowanie (UKOŃCZONE)
- [x] Analiza istniejącego kodu
- [x] Przygotowanie raportu
- [x] Identyfikacja brakujących funkcji

### ✅ FAZA 1: Podstawowe działanie (UKOŃCZONE) ✓
**Cel:** Wykonywanie akcji bez globalnych hooków

**Dzień 1:** ✅ UKOŃCZONE
- [x] Instalacja bibliotek (pynput, pyperclip, pyautogui)
- [x] Implementacja `ActionExecutor` klasy - dispatcher
- [x] Implementacja akcji: Wklej tekst
- [x] Implementacja akcji: Otwórz aplikację
- [x] Implementacja akcji: Otwórz plik
- [x] Implementacja akcji: Polecenie PowerShell
- [x] Implementacja akcji: Polecenie CMD
- [x] Implementacja akcji: Sekwencja kliknięć
- [x] Przycisk "🧪 Testuj akcję" w formularzu
- [x] Obsługa błędów i walidacja
- [x] Testy wszystkich 6 trybów akcji

---

### 🔄 FAZA 2: Globalne skróty (W TRAKCIE) - **DZ IEŃ 1 UKOŃCZONY**
**Cel:** Nasłuchiwanie i aktywacja skrótów

**Dzień 1:** ✅ UKOŃCZONE
- [x] Klasa `HotkeyListener` 
- [x] Parsowanie kombinacji klawiszy
- [x] Mapowanie skrót -> akcja
- [x] Uruchomienie w wątku
- [x] Obsługa magicznych fraz
- [x] Detekcja przytrzymania klawisza
- [x] System włączania/wyłączania
- [x] Wskaźnik stanu w UI (zielony/czerwony)
- [x] Przycisk "URUCHOM/ZATRZYMAJ SYSTEM"
- [x] Licznik aktywnych skrótów

**Dzień 2:** ⏳ DO ZROBIENIA
- [ ] Testy wszystkich rodzajów skrótów
- [ ] Obsługa konfliktów skrótów
- [ ] Optymalizacja detekcji
- [ ] Dokumentacja

---

### ⏳ FAZA 3: Zaawansowane (2-3 dni) - ZAPLANOWANE
**Dzień 1:**
- [ ] System tray
- [ ] Minimalizacja do tray
- [ ] Menu kontekstowe

**Dzień 2:**
- [ ] Panel logów
- [ ] Eksport logów
- [ ] Filtrowanie

**Dzień 3:**
- [ ] Obsługa błędów końcowa
- [ ] Walidacja bezpieczeństwa
- [ ] Testy integracyjne

---

### ⏳ FAZA 4: Dopracowanie (1 dzień) - ZAPLANOWANE
- [ ] Testy użytkowe
- [ ] Poprawki UX
- [ ] Optymalizacja wydajności
- [ ] Dokumentacja użytkownika
- [ ] Przygotowanie do wdrożenia

---

## 📈 METRYKI POSTĘPU

**Obecny stan implementacji:**
- Interfejs: 100% ✅
- Zarządzanie danymi: 100% ✅
- Wykonywanie akcji: 100% ✅
- System aktywacji: 90% ✅ (testy w toku)
- Funkcje dodatkowe: 0%

**CAŁKOWITY POSTĘP: ~75%** 🎉

---

## 🎉 ZAIMPLEMENTOWANE FUNKCJONALNOŚCI

### ✅ FAZA 1 - Wykonywanie akcji (100%)
1. **ActionExecutor** - kompletna klasa wykonawcza
   - `paste_text()` - wklejanie przez schowek + Ctrl+V ✅
   - `open_application()` - subprocess.Popen() ✅
   - `open_file()` - os.startfile() ✅
   - `run_powershell()` - z timeout i przechwytywaniem output ✅
   - `run_cmd()` - z timeout i przechwytywaniem output ✅
   - `execute_click_sequence()` - pynput.mouse z opóźnieniami ✅

2. **Przycisk testowania** - 🧪 Testuj akcję ✅
   - Wykonuje akcję bez zapisywania skrótu
   - Pokazuje komunikaty sukcesu/błędu
   - Status bar z informacjami

### ✅ FAZA 2 - Globalne skróty (90%)
1. **HotkeyListener** - nasłuchiwanie globalne ✅
   - Działa w osobnym wątku (threading)
   - Wykrywa kombinacje klawiszy (Ctrl+Alt+N, itp.)
   - Obsługuje przytrzymanie pojedynczego klawisza
   - Wykrywa magiczne frazy (typing buffer)
   - Mapuje skróty do akcji
   - Wykonuje akcje w osobnych wątkach

2. **System sterowania** ✅
   - Przycisk "▶ URUCHOM SYSTEM" / "⏸ ZATRZYMAJ SYSTEM"
   - Wskaźnik statusu (czerwony/zielony)
   - Licznik aktywnych skrótów
   - Walidacja przed startem (sprawdza czy są skróty)
   - Auto-stop przy zamykaniu aplikacji

3. **Parsowanie skrótów** ✅
   - Kombinacje: "Ctrl+Alt+N", "Shift+F1"
   - Modyfikatory: Ctrl, Alt, Shift, Win (lewy i prawy)
   - Zwykłe klawisze: litery, funkcyjne (F1-F12)
   - Case-insensitive

---

## 🐛 ZNANE PROBLEMY

1. ⚠️ Ostrzeżenia Pylance (type hints) - nie krytyczne, kod działa
2. ⚠️ Brak walidacji JSON przy ręcznym wpisywaniu sekwencji kliknięć
3. ⚠️ Brak obsługi duplikacji nazw skrótów (tylko shortcut_value)
4. ⚠️ Magiczne frazy - resetują się przy backspace (zamierzone zachowanie)

---

## 📝 NOTATKI TECHNICZNE

### Architektura wykonania akcji:
```python
def execute_action(shortcut):
    """Główny dispatcher wykonywania akcji"""
    action_type = shortcut['action_type']
    action_value = shortcut['action_value']
    
    try:
        if action_type == "Wklej tekst":
            paste_text(action_value)
        elif action_type == "Otwórz aplikację":
            open_application(action_value)
        elif action_type == "Otwórz plik":
            open_file(action_value)
        elif action_type == "Polecenie PowerShell":
            run_powershell(action_value)
        elif action_type == "Polecenie wiersza poleceń":
            run_cmd(action_value)
        elif action_type == "Wykonaj sekwencję kliknięć":
            execute_click_sequence(action_value)
        
        log_success(shortcut['name'])
    except Exception as e:
        log_error(shortcut['name'], str(e))
        show_error_notification(shortcut['name'], str(e))
```

### Architektura globalnych hotkeys:
```python
class HotkeyListener:
    def __init__(self, shortcuts, callback):
        self.shortcuts = shortcuts
        self.callback = callback
        self.listener = None
        self.pressed_keys = set()
    
    def start(self):
        from pynput import keyboard
        self.listener = keyboard.Listener(
            on_press=self.on_press,
            on_release=self.on_release
        )
        self.listener.start()
    
    def on_press(self, key):
        self.pressed_keys.add(key)
        self.check_shortcuts()
    
    def check_shortcuts(self):
        for shortcut in self.shortcuts:
            if self.matches(shortcut):
                self.callback(shortcut)
```

---

## 🎓 WNIOSKI I REKOMENDACJE

1. **Priorytet:** Rozpocząć od FAZY 1 - wykonywania akcji, bez globalnych hooków
2. **Biblioteka:** Użyć `pynput` (bardziej stabilna niż `keyboard`)
3. **Bezpieczeństwo:** Dodać timeout i walidację przed FAZĄ 2
4. **UI:** Dodać przycisk "Testuj akcję" do szybkiego sprawdzania
5. **Logi:** Zaimplementować podstawowe logowanie od początku
6. **Dokumentacja:** Komentować kod na bieżąco

---

**Ostatnia aktualizacja:** 2025-11-02  
**Następna rewizja:** Po zakończeniu FAZY 1  
**Autor:** AI Assistant + User
