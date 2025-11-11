# 🧪 UI Test Launcher - Dokumentacja

## 📋 Opis

**UI Test Launcher** to narzędzie do szybkiego testowania pojedynczych komponentów UI bez konieczności uruchamiania całej aplikacji. Umożliwia:

- ✅ Szybkie uruchamianie dialogów i widoków
- 🎨 Testowanie z różnymi motywami
- 🔄 Natychmiastową zmianę motywu na otwartych oknach
- 📋 Przejrzystą listę wszystkich komponentów UI

## 🚀 Jak uruchomić?

### Metoda 1: PowerShell Script (Zalecana)
```powershell
cd tests
.\run_ui_tests.ps1
```

### Metoda 2: Bezpośrednio przez Python
```bash
python tests/test_ui_launcher.py
```

### Metoda 3: Z poziomu głównego katalogu
```bash
cd PRO-Ka-Po_Kaizen_Freak
python -m tests.test_ui_launcher
```

## 🎯 Funkcjonalności

### 1. Wybór motywu
- Lista wszystkich dostępnych motywów w projekcie
- Przycisk "Zastosuj motyw" - zmienia motyw w czasie rzeczywistym
- Przycisk "Odśwież listę" - przeładowuje listę motywów (gdy dodasz nowy)

### 2. Grupy komponentów

#### 🤖 AI & Asystent (4 komponenty)
- **AI Settings** - Panel ustawień AI
- **AI Summary Dialog** - Dialog podsumowań AI
- **AI Task Communication Dialog** - Dialog komunikacji AI z zadaniami
- **Assistant Settings** - Ustawienia asystenta

#### 📋 Główne widoki (8 komponentów)
- Main Window
- Navigation Bar
- Task View
- Kanban View
- Note View
- Pomodoro View
- Alarms View
- QuickBoard View

#### 🔧 Moduły specjalistyczne (4 komponenty)
- CallCryptor View
- CallCryptor Dialogs
- ProApp View
- Web View

#### 💬 Dialogi (4 komponenty)
- **Style Creator Dialog** - Kreator motywów
- **Config View** - Widok konfiguracji
- Task Config Dialog
- Tag Manager

## 📝 Jak używać?

### Podstawowy workflow testowania motywu:

1. **Uruchom launcher**
   ```powershell
   .\run_ui_tests.ps1
   ```

2. **Wybierz motyw z listy** (np. "Dark Theme")

3. **Kliknij "Zastosuj motyw"**

4. **Kliknij przycisk komponentu** który chcesz przetestować (np. "▶ AI Settings")

5. **Komponent otworzy się z wybranym motywem**

6. **Zmień motyw** (np. na "Light Theme") i kliknij "Zastosuj motyw"

7. **Wszystkie otwarte okna automatycznie się odświeżą!**

### Testowanie wielu komponentów jednocześnie:

1. Wybierz motyw
2. Kliknij kilka przycisków komponentów (np. AI Settings, Style Creator, Config View)
3. Wszystkie otworzą się obok siebie
4. Zmień motyw → **wszystkie okna automatycznie się zaktualizują**

## 🔧 Dodawanie nowych komponentów do testów

### Krok 1: Znajdź metodę w `test_ui_launcher.py`

Każda metoda testowa ma format:
```python
def _test_nazwa_komponentu(self):
    """Test Nazwa Komponentu"""
    try:
        from src.ui.nazwa_pliku import NazwaKlasy
        dialog = NazwaKlasy(self)
        dialog.show()
        self.active_dialogs.append(dialog)
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to load:\n{str(e)}")
```

### Krok 2: Dodaj przycisk do odpowiedniej grupy

W metodzie `_init_ui()` znajdź odpowiednią grupę i dodaj:
```python
self._add_group(scroll_layout, "🤖 AI & Asystent", [
    ("AI Settings", self._test_ai_settings),
    ("Nowy Komponent", self._test_nowy_komponent),  # ← DODAJ TU
])
```

### Krok 3: Zaimplementuj metodę testową

```python
def _test_nowy_komponent(self):
    """Test Nowy Komponent"""
    try:
        from src.ui.nowy_komponent import NowyKomponent
        dialog = NowyKomponent(self)
        dialog.show()
        self.active_dialogs.append(dialog)
    except Exception as e:
        QMessageBox.critical(self, "Error", f"Failed to load:\n{str(e)}")
```

## 📊 Status implementacji

### ✅ Zaimplementowane (3 komponenty):
- [x] AI Settings
- [x] AI Summary Dialog
- [x] AI Task Communication Dialog
- [x] Style Creator Dialog
- [x] Config View

### ⏳ Do zaimplementowania (pozostałe):
- [ ] Assistant Settings
- [ ] Main Window
- [ ] Navigation Bar
- [ ] Task View
- [ ] Kanban View
- [ ] Note View
- [ ] Pomodoro View
- [ ] Alarms View
- [ ] QuickBoard View
- [ ] CallCryptor View
- [ ] CallCryptor Dialogs
- [ ] ProApp View
- [ ] Web View
- [ ] Task Config Dialog
- [ ] Tag Manager

## 💡 Przykłady użycia

### Przykład 1: Testowanie AI Settings z różnymi motywami
```
1. Uruchom launcher
2. Wybierz "Dark Theme" → Zastosuj
3. Kliknij "▶ AI Settings"
4. Sprawdź czy kolory są poprawne
5. Zmień na "Light Theme" → Zastosuj
6. AI Settings automatycznie się odświeży
7. Sprawdź czy kolory są poprawne
```

### Przykład 2: Testowanie wielu dialogów jednocześnie
```
1. Uruchom launcher
2. Kliknij "▶ AI Settings"
3. Kliknij "▶ Style Creator Dialog"
4. Kliknij "▶ Config View"
5. Teraz masz 3 okna obok siebie
6. Zmień motyw → wszystkie 3 się zaktualizują!
```

## 🐛 Rozwiązywanie problemów

### Problem: "Failed to load" error
**Rozwiązanie**: Sprawdź czy plik komponentu istnieje i czy importy są poprawne

### Problem: Motyw się nie zmienia
**Rozwiązanie**: Upewnij się że komponent ma metodę `apply_theme()`

### Problem: Dialog się nie otwiera
**Rozwiązanie**: Sprawdź w konsoli jakie są błędy importu/inicjalizacji

## 🔍 Wskazówki

1. **Używaj tego narzędzia zamiast uruchamiać całą aplikację** - znacznie szybsze!
2. **Testuj oba motywy** (jasny i ciemny) dla każdego komponentu
3. **Otwieraj wiele okien naraz** - łatwiej porównać motywy
4. **Dodawaj nowe komponenty** gdy pracujesz nad refaktoryzacją
5. **Mock danych** - używaj przykładowych danych do testów (jak w AI Summary Dialog)

## 📚 Powiązane pliki

- `tests/test_ui_launcher.py` - Główny launcher
- `tests/run_ui_tests.ps1` - Skrypt uruchomieniowy PowerShell
- `docs/THEME_REFACTORING_CHECKLIST.md` - Checklist refaktoryzacji
- `src/utils/theme_manager.py` - Manager motywów

## ⚡ Zalety tego podejścia

1. ✅ **Szybkość** - komponenty ładują się w <1s zamiast 10-20s całej aplikacji
2. ✅ **Izolacja** - testowanie jednego komponentu na raz
3. ✅ **Automatyzacja** - zmiana motywu odświeża wszystkie otwarte okna
4. ✅ **Wygoda** - wszystkie komponenty w jednym miejscu
5. ✅ **Efektywność** - można testować wiele komponentów równolegle

---

**Utworzono**: 2024-11-11  
**Wersja**: 1.0  
**Autor**: AI Assistant
