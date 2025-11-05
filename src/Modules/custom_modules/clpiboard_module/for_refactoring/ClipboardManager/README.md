# 📋 Clipboard Manager - Menedżer Schowka

Zaawansowany menedżer historii schowka dla systemu Windows.

## 🚀 Funkcje

### Podstawowe
- ✅ **Automatyczne monitorowanie schowka** - zapisuje wszystko co kopiujesz
- ✅ **Historia 50 elementów** - przechowuje ostatnie skopiowane treści
- ✅ **Inteligentne wykrywanie typu** - automatycznie rozpoznaje: Tekst, Link, Kod, Email, Plik
- ✅ **Podgląd zawartości** - pełny podgląd wybranego elementu
- ✅ **Szybkie kopiowanie** - podwójne kliknięcie lub przycisk

### Zaawansowane
- 📌 **Przypinanie ważnych elementów** - przypięte nigdy nie zostaną usunięte
- 🔍 **Wyszukiwanie w historii** - szybkie znajdowanie potrzebnych treści
- 🎯 **Filtrowanie po typie** - pokaż tylko linki, kod, pliki itp.
- 📊 **Statystyki** - liczba elementów, przypięte, dzisiejsze
- 💾 **Eksport/Import** - backup historii do pliku JSON
- 🧹 **Zarządzanie historią** - czyszczenie, usuwanie pojedynczych elementów

### Typy zawartości
- 📝 **Tekst** - zwykły tekst
- 🔗 **Link** - adresy URL (http://, https://, www.)
- 💻 **Kod** - wykrywa składnię programowania
- 📧 **Email** - adresy e-mail
- 📁 **Plik** - ścieżki do plików i folderów

## 📦 Instalacja

### Wymagane biblioteki:
```bash
pip install pyperclip keyboard PyQt6
```

## 🎮 Użycie

### Uruchomienie:
```bash
python clipboard_module.py
```

### Podstawowe operacje:

1. **Automatyczne zapisywanie**
   - Wszystko co skopiujesz (Ctrl+C) zostanie automatycznie zapisane w historii

2. **Kopiowanie z historii**
   - Podwójne kliknięcie na element
   - Lub: zaznacz element → przycisk "📋 Kopiuj"

3. **Przypinanie**
   - Zaznacz element → przycisk "📌 Przypnij"
   - Przypięte elementy mają żółte tło i nie są usuwane podczas czyszczenia

4. **Wyszukiwanie**
   - Wpisz frazę w polu "🔍 Szukaj w historii..."
   - Wybierz typ z listy rozwijanej (Wszystkie, Tekst, Link, Kod...)

5. **Monitoring**
   - Przycisk "⏸ Wstrzymaj" - zatrzymuje automatyczne zapisywanie
   - Przycisk "▶ Uruchom" - wznawia monitoring

6. **Eksport/Import**
   - "💾 Eksport" - zapisz historię do pliku JSON
   - "📥 Import" - wczytaj historię z pliku JSON

7. **Czyszczenie**
   - "🗑 Usuń" - usuwa wybrany element
   - "🧹 Wyczyść wszystko" - usuwa całą historię (zachowuje przypięte)

## 🎨 Interfejs

### Lewy panel - Historia
- Lista wszystkich elementów z podglądem
- Ikony typów zawartości
- Znaczniki czasu
- Oznaczenie przypiętych (📌)
- Filtry i wyszukiwanie

### Prawy panel - Podgląd
- Pełna zawartość wybranego elementu
- Informacje: typ, data, rozmiar
- Statystyki użytkowania
- Przyciski eksportu/importu

### Pasek statusu
- Aktualny status monitoringu (🟢 włączony / 🔴 wyłączony)
- Liczba elementów w historii
- Komunikaty o wykonanych akcjach

## ⚙️ Konfiguracja

### Maksymalna liczba elementów
Edytuj w pliku `clipboard_module.py`:
```python
self.max_history = 50  # Zmień na dowolną liczbę
```

### Interwał monitorowania
Edytuj w klasie `ClipboardMonitor`:
```python
self.msleep(500)  # 500ms = 0.5 sekundy
```

### Globalny skrót klawiszowy (opcjonalny)
Odkomentuj w `__init__()`:
```python
# self.register_global_hotkey()  # Usuń #
```

## 📂 Struktura plików

```
ClipboardManager/
├── clipboard_module.py      # Główny program
├── clipboard_history.json   # Automatyczny zapis historii
└── README.md               # Ten plik
```

## 🔧 Rozwiązywanie problemów

### Monitoring nie działa
- Sprawdź czy pyperclip jest zainstalowany: `pip install pyperclip`
- Upewnij się że status pokazuje "🟢 Monitoring WŁĄCZONY"

### Nie można skopiować elementu
- Sprawdź czy element jest zaznaczony
- Spróbuj podwójnego kliknięcia

### Historia nie zapisuje się
- Sprawdź uprawnienia do zapisu w folderze
- Upewnij się że plik clipboard_history.json nie jest tylko do odczytu

### Aplikacja się zawiesza
- Sprawdź ilość elementów (zbyt duża historia może spowolnić)
- Wyczyść starą historię

## 💡 Planowane funkcje (do dodania)

- [ ] Globalny skrót Ctrl+Shift+V do szybkiego dostępu
- [ ] Snippety z parametrami {{nazwa}}, {{data}}
- [ ] Formatowanie (plain text, HTML, Markdown)
- [ ] Kategorie użytkownika
- [ ] Podgląd obrazów
- [ ] Synchronizacja między urządzeniami
- [ ] Dark mode

## 📝 Licencja

Część aplikacji komercyjnej "Pro Ka Po Comer"

## 👨‍💻 Autor

Aplikacja komercyjna - 2025
