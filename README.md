# PRO-Ka-Po_Kaizen_Freak - Komercyjna Aplikacja do Organizacji Zadań

## 📋 Opis Projektu

Nowoczesna, wielojęzyczna aplikacja desktopowa do zarządzania zadaniami, oparta na PyQt6. Aplikacja oferuje intuicyjny interfejs użytkownika z systemem motywów, wielojęzycznością oraz zaawansowanymi funkcjami organizacji pracy.

## 🎯 Główne Założenia

### Architektura UI
- **Górny pasek menu** - stały pasek z przyciskami nawigacyjnymi między sekcjami
- **Sekcja główna** składająca się z:
  - Pasek zarządzania (indywidualny dla każdej sekcji)
  - Tabela danych
- **Dwuwierszowa sekcja szybkiego wprowadzania** - u dołu aplikacji

### Kluczowe Funkcjonalności
- ✅ System rejestracji i logowania użytkowników
- 🌍 Wielojęzyczność (i18n) - interfejs przystosowany do wielu języków
- 🎨 System motywów - różne motywy i zmiany kolorystyczne
- 🔐 Bezpieczne przechowywanie danych użytkowników
- 📊 Zarządzanie zadaniami w formie tabelarycznej
- ⚡ Szybkie wprowadzanie danych

## 🛠️ Technologie

- **Python 3.11+**
- **PyQt6** - framework GUI
- **SQLite/PostgreSQL** - baza danych
- **bcrypt** - hashowanie haseł
- **PyQt6-i18n** - wsparcie wielojęzyczności

## 📁 Struktura Projektu

```
PRO-Ka-Po_Kaizen_Freak/
├── src/
│   ├── ui/                     # Moduły interfejsu użytkownika
│   │   ├── __init__.py
│   │   ├── main_window.py      # Główne okno aplikacji
│   │   ├── navigation_bar.py   # Górny pasek nawigacyjny
│   │   ├── management_bar.py   # Pasek zarządzania sekcją
│   │   ├── data_table.py       # Widok tabeli
│   │   ├── quick_input.py      # Sekcja szybkiego wprowadzania
│   │   └── dialogs/            # Okna dialogowe
│   │
│   ├── core/                   # Logika biznesowa
│   │   ├── __init__.py
│   │   ├── task_manager.py     # Zarządzanie zadaniami
│   │   └── settings.py         # Ustawienia aplikacji
│   │
│   ├── auth/                   # System autentykacji
│   │   ├── __init__.py
│   │   ├── login.py            # Logika logowania
│   │   └── register.py         # Logika rejestracji
│   │
│   ├── database/               # Warstwa bazodanowa
│   │   ├── __init__.py
│   │   ├── models.py           # Modele danych
│   │   └── repository.py       # Repozytoria
│   │
│   └── utils/                  # Narzędzia pomocnicze
│       ├── __init__.py
│       ├── theme_manager.py    # Zarządzanie motywami
│       ├── i18n_manager.py     # Zarządzanie tłumaczeniami
│       └── validators.py       # Walidacja danych
│
├── resources/
│   ├── i18n/                   # Pliki tłumaczeń
│   │   ├── en.json
│   │   ├── pl.json
│   │   └── de.json
│   │
│   ├── themes/                 # Pliki motywów (QSS)
│   │   ├── light.qss
│   │   ├── dark.qss
│   │   └── custom.qss
│   │
│   └── icons/                  # Ikony aplikacji
│
├── tests/                      # Testy jednostkowe
│   ├── test_auth.py
│   ├── test_tasks.py
│   └── test_ui.py
│
├── docs/                       # Dokumentacja
│   ├── architecture.md
│   ├── user_guide.md
│   └── api_reference.md
│
├── .gitignore
├── requirements.txt
├── setup.py
├── main.py                     # Punkt wejścia aplikacji
└── README.md
```

## 🚀 Instalacja i Uruchomienie

### Wymagania
- Python 3.11 lub nowszy
- pip (menedżer pakietów Python)

### Kroki instalacji

1. Klonowanie repozytorium:
```bash
git clone <repository-url>
cd PRO-Ka-Po_Kaizen_Freak
```

2. Utworzenie środowiska wirtualnego:
```bash
python -m venv venv
```

3. Aktywacja środowiska wirtualnego:
```bash
# Windows
.\venv\Scripts\Activate.ps1

# Linux/Mac
source venv/bin/activate
```

4. Instalacja zależności:
```bash
pip install -r requirements.txt
```

5. Uruchomienie aplikacji:
```bash
python main.py
```

## 🎨 Zasady Tworzenia Kodu

### Modularność
- Każdy moduł powinien mieć jedną, jasno określoną odpowiedzialność
- Maksymalna długość pliku: ~300 linii (orientacyjnie)
- Separacja logiki biznesowej od warstwy prezentacji

### Style Kodowania
- PEP 8 - standard kodowania Python
- Type hints dla wszystkich funkcji i metod
- Docstrings dla klas i funkcji publicznych
- Komentarze w języku angielskim

### Nazewnictwo
- Klasy: PascalCase (np. `MainWindow`, `TaskManager`)
- Funkcje/metody: snake_case (np. `get_user`, `save_task`)
- Stałe: UPPER_SNAKE_CASE (np. `MAX_TASKS`, `DEFAULT_THEME`)
- Pliki: snake_case (np. `main_window.py`, `task_manager.py`)

## 🌍 Wielojęzyczność (i18n)

Aplikacja wspiera następujące języki:
- 🇵🇱 Polski (domyślny)
- 🇬🇧 Angielski
- 🇩🇪 Niemiecki

Pliki tłumaczeń znajdują się w `resources/i18n/` w formacie JSON.

## 🎨 System Motywów

Dostępne motywy:
- **Light** - jasny motyw (domyślny)
- **Dark** - ciemny motyw
- **Custom** - motywy użytkownika

Style definiowane są w plikach QSS w katalogu `resources/themes/`.

## 🔐 Bezpieczeństwo

- Hasła hashowane przy użyciu bcrypt
- Sesje użytkowników z timeoutem
- Walidacja danych wejściowych
- SQL injection prevention (ORM/parametryzowane zapytania)

## 📝 Roadmap

### Wersja 1.0 (MVP)
- [x] Struktura projektu
- [ ] System logowania/rejestracji
- [ ] Podstawowy interfejs (nawigacja + tabela)
- [ ] Dodawanie/edycja zadań
- [ ] System motywów (light/dark)
- [ ] Wsparcie dla PL/EN

### Wersja 1.1
- [ ] Zaawansowane filtrowanie
- [ ] Eksport danych (CSV, PDF)
- [ ] Statystyki i raporty
- [ ] Wsparcie dla dodatkowych języków

### Wersja 2.0
- [ ] Synchronizacja w chmurze
- [ ] Aplikacja mobilna
- [ ] Współdzielenie zadań
- [ ] Integracje (Calendar, Email)

## 🤝 Kontrybuacja

Projekt jest rozwijany zgodnie z najlepszymi praktykami:
- Feature branches
- Pull requests z code review
- Automatyczne testy przed merge
- Semantic versioning

## 📄 Licencja

Aplikacja komercyjna - wszelkie prawa zastrzeżone.

## 👥 Autorzy

Projekt rozwijany przez PRO-Ka-Po Team

---

**Status:** 🚧 W trakcie rozwoju
**Wersja:** 0.1.0-alpha
**Ostatnia aktualizacja:** Listopad 2025
# Pro-Ka-Po_V5c
