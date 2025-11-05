# Moduł Folder

## Opis
Zaawansowany moduł do zarządzania skrótami do plików, folderów i skrótów (.lnk) z systemem tagów kolorowych i komentarzy.

## Główne funkcjonalności

### 🗂️ Zarządzanie folderami
- Tworzenie wielu niezależnych folderów do organizacji elementów
- Przełączanie między folderami za pomocą listy rozwijanej
- Przenoszenie elementów między folderami

### 📁 Dodawanie elementów
- **Pliki** - dowolne typy plików
- **Foldery** - całe katalogi
- **Skróty** - pliki .lnk
- Automatyczne zapisywanie ikon (64x64 PNG)
- Przechowywanie tylko ścieżek (bez kopiowania plików)

### 🏷️ System tagów
- Nieograniczona liczba tagów
- Każdy tag ma swój unikalny kolor
- Wizualne wyróżnienie kolorami
- Dialog zarządzania tagami (dodawanie/usuwanie/wybór koloru)
- Automatyczne dopasowanie koloru tekstu (czarny/biały) do tła

### 💬 Komentarze
- Dodawanie notatek do każdego elementu
- Szybki dostęp przez menu kontekstowe lub dwukrotne kliknięcie

## Widoki

### 📊 Widok listy (tabela)
**Kolumny:**
- Nazwa - można zmieniać szerokość
- Tag - ComboBox z listą tagów (podświetlenie kolorem)
- Komentarz - pole edytowalne, rozciągalne
- Data utworzenia - automatyczne dopasowanie
- Data modyfikacji - automatyczne dopasowanie
- Ścieżka - rozciągalna

**Dwukrotne kliknięcie:**
- **Nazwa** → otwiera plik/folder
- **Komentarz** → otwiera dialog edycji
- **Data** → pokazuje właściwości systemowe (Windows API)
- **Ścieżka** → otwiera folder docelowy

### 🖼️ Widok ikon
- Siatka ikon (6 kolumn)
- Systemowe ikony plików/folderów
- Ramka w kolorze tagu (3px, zaokrąglona)
- Etykieta tagu na górze (wewnątrz ramki)

**Interakcje:**
- **Pojedyncze kliknięcie** → zaznaczenie
- **Dwukrotne kliknięcie** → otwiera plik/folder
- **Prawy przycisk** → menu kontekstowe

## Menu kontekstowe

Dostępne po kliknięciu prawym przyciskiem w widoku ikon:

1. **Otwórz** - otwiera element w domyślnej aplikacji
2. **Otwórz folder docelowy** - pokazuje lokalizację w Explorerze
3. **Otwórz komentarz** - edycja tagu i komentarza
4. **Zmień tag** - szybki wybór tagu z listy
5. **Kopiuj ścieżkę** - kopiuje do schowka
6. **Udostępnij** - upload do chmury Backblaze B2 + wysyłka emaila z linkiem
7. **Przenieś do innego folderu** - podmenu z listą folderów
8. **Usuń z folderu aplikacji** - usuwa tylko skrót
9. **Usuń w miejscu docelowym** - ⚠️ trwale usuwa plik z dysku

## Udostępnianie plików

### ☁️ Integracja z Backblaze B2

Moduł oferuje możliwość udostępniania plików przez:
- Upload do chmury Backblaze B2
- Automatyczne wysłanie emaila z linkiem do pobrania
- Wsparcie dla wielu języków (PL/EN/DE)

**Jak użyć:**
1. Kliknij prawym przyciskiem na plik w widoku ikon
2. Wybierz "Udostępnij"
3. Wprowadź:
   - Email odbiorcy
   - Twoje imię/nazwę
   - Język emaila (polski/angielski/niemiecki)
   - URL API (np. `http://localhost:8000` lub `https://your-api.onrender.com`)
4. Kliknij OK

**Wymagania:**
- Uruchomione API (Render_upload)
- Połączenie z internetem
- Maksymalny rozmiar pliku: 100 MB

**Odbiorca otrzyma:**
- Email z linkiem do pobrania
- Informacje o pliku (nazwa, rozmiar)
- Link ważny przez 7 dni

## Pasek nawigacyjny

- **Lista folderów** - przełączanie między folderami
- **Nowy folder** - tworzenie nowego folderu
- **Wyświetl listę** - przełączenie na widok tabeli
- **Wyświetl ikony** - przełączenie na widok siatki
- **Dodaj nowy plik** - dialog wyboru typu (plik/folder/skrót)
- **Usuń plik** - usuwa zaznaczony element
- **Komentarz** - edycja komentarza zaznaczonego elementu
- **Edytuj tagi plików** - zarządzanie tagami
- **Udostępnij** - upload pliku do chmury (wymaga API)

## Wymagania

```
Python 3.8+
PyQt6>=6.4.0
requests>=2.31.0  # Do komunikacji z API
```

## Instalacja

```bash
pip install -r requirements.txt
```

## Uruchomienie

```bash
python folder_module.py
```

## Struktura danych

Dane zapisywane w `folder_data.json`:

```json
{
  "folders": {
    "Nazwa folderu": [
      {
        "name": "dokument.pdf",
        "path": "C:/Users/user/Documents/dokument.pdf",
        "type": "file",
        "tag": "Projekt",
        "comment": "Ważny dokument",
        "icon_path": "icons_cache/dokument_pdf_123456.png",
        "created": "2025-11-02 12:00:00",
        "modified": "2025-11-02 14:30:00"
      }
    ]
  },
  "tags_colors": {
    "Projekt": "#FF5733",
    "Dokumenty": "#3498DB",
    "Zdjęcia": "#2ECC71"
  }
}
```

## Ikony

Ikony przechowywane w katalogu `icons_cache/`:
- Format: PNG
- Rozmiar: 64x64 pikseli
- Nazewnictwo: `{nazwa_pliku}_{hash}.png`
- Zachowane nawet po usunięciu oryginalnego pliku

## Funkcje zaawansowane

### Automatyczne dopasowanie tabeli
- Kolumny rozciągają się automatycznie
- Wykorzystanie całej dostępnej przestrzeni
- Responsywność przy zmianie rozmiaru okna

### Windows API Integration
- Natywne okno właściwości pliku (ShellExecuteExW)
- Systemowe ikony plików i folderów
- Otwieranie w domyślnych aplikacjach

### Bezpieczeństwo
- Potwierdzenie przed usunięciem
- Domyślnie "Nie" dla operacji trwałego usuwania
- Jasne ostrzeżenia o nieodwracalności akcji
- Sprawdzanie istnienia plików przed operacjami

## Optymalizacje

- Wydajne zarządzanie widgetami (proper cleanup)
- Lazy loading ikon
- Minimalne zużycie pamięci
- Szybkie przełączanie między widokami

## Autor

Moduł stworzony dla aplikacji komercyjnej.

## Licencja

Proprietary

