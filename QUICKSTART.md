# Quick Start Guide

## Uruchomienie Aplikacji

### 1. Środowisko Wirtualne

```powershell
# Przejdź do folderu projektu
cd "c:\Users\probu\Desktop\Aplikacje komercyjne\PRO-Ka-Po_Kaizen_Freak\PRO-Ka-Po_Kaizen_Freak"

# Aktywuj środowisko wirtualne
.\venv\Scripts\Activate.ps1

# Lub użyj środowiska z folderu nadrzędnego
..\..\.venv\Scripts\Activate.ps1
```

### 2. Instalacja Zależności

```powershell
pip install -r requirements.txt
```

### 3. Uruchomienie Aplikacji

```powershell
python main.py
```

## Struktura Okna Głównego

Aplikacja składa się z trzech głównych sekcji:

### 1. Górny Pasek Nawigacyjny
- Przyciski zmiany widoków (Zadania, KanBan, Tabele, etc.)
- Zaznaczony przycisk pokazuje aktywny widok (pomarańczowy)

### 2. Sekcja Główna (Zmienna)
- **Pasek Zarządzania**: Przyciski akcji (Dodaj, Edytuj, Usuń, Szukaj)
- **Obszar Danych**: Tabela lub inny widok danych

### 3. Sekcja Dolna - Szybkie Wprowadzanie
- **Wiersz 1**: 
  - Pole tekstowe (szerokie)
  - Przycisk "+" (zielony - dodaj)
  - Przycisk "📝" (pomarańczowy - notatka)
- **Wiersz 2**: 
  - 5 list rozwijanych (Osoba, Narzędzia, Sprzęt, Czas, Oferta)
  - Checkbox "Kanban"

## Funkcjonalności

### Aktualnie Zaimplementowane
- ✅ Struktura trzech sekcji
- ✅ Nawigacja między widokami
- ✅ Pasek zarządzania
- ✅ Sekcja szybkiego wprowadzania
- ✅ Obsługa motywów (light/dark)
- ✅ Obsługa tłumaczeń (PL/EN/DE)

### Do Implementacji
- [ ] Faktyczna zmiana zawartości przy zmianie widoku
- [ ] Funkcjonalność dodawania zadań
- [ ] Moduły dla każdego widoku
- [ ] Integracja z bazą danych
- [ ] System logowania

## Zmiana Motywu

Edytuj `src/core/config.py`:
```python
DEFAULT_THEME: str = "dark"  # lub "light"
```

## Zmiana Języka

Edytuj `src/core/config.py`:
```python
DEFAULT_LANGUAGE: str = "en"  # lub "pl", "de"
```

## Rozwój

Moduły funkcjonalne tworzymy w folderze `src/Modules/`.

Przykład: `src/Modules/tasks/`
