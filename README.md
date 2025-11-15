# PRO-Ka-Po - Kaizen Freak Edition 🚀# PRO-Ka-Po_Kaizen_Freak - Komercyjna Aplikacja do Organizacji Zadań



![Python](https://img.shields.io/badge/python-3.11+-blue.svg)## 📋 Opis Projektu

![PyQt6](https://img.shields.io/badge/PyQt6-GUI-green.svg)

![License](https://img.shields.io/badge/license-Open%20Source-orange.svg)Nowoczesna, wielojęzyczna aplikacja desktopowa do zarządzania zadaniami, oparta na PyQt6. Aplikacja oferuje intuicyjny interfejs użytkownika z systemem motywów, wielojęzycznością oraz zaawansowanymi funkcjami organizacji pracy.



**PRO-Ka-Po** to kompleksowy zestaw minimalistycznych narzędzi do organizacji pracy i zadań, stworzony z myślą o pasjonatach **KAIZEN** i **Lean Management**. Aplikacja idealna do pracy biurowej, współpracy zespołowej i zwiększania codziennej produktywności.## 🎯 Główne Założenia



---### Architektura UI

- **Górny pasek menu** - stały pasek z przyciskami nawigacyjnymi między sekcjami

## 📋 Spis treści- **Sekcja główna** składająca się z:

  - Pasek zarządzania (indywidualny dla każdej sekcji)

- [Funkcje](#-funkcje)  - Tabela danych

- [Moduły aplikacji](#-moduły-aplikacji)- **Dwuwierszowa sekcja szybkiego wprowadzania** - u dołu aplikacji

- [Instalacja](#-instalacja)

- [Wymagania](#-wymagania)### Kluczowe Funkcjonalności

- [Struktura projektu](#-struktura-projektu)- ✅ System rejestracji i logowania użytkowników

- [Konfiguracja](#-konfiguracja)- 🌍 Wielojęzyczność (i18n) - interfejs przystosowany do wielu języków

- [Użytkowanie](#-użytkowanie)- 🎨 System motywów - różne motywy i zmiany kolorystyczne

- [Bezpieczeństwo i prywatność](#-bezpieczeństwo-i-prywatność)- 🔐 Bezpieczne przechowywanie danych użytkowników

- [Roadmap](#-roadmap)- 📊 Zarządzanie zadaniami w formie tabelarycznej

- [Wsparcie projektu](#-wsparcie-projektu)- ⚡ Szybkie wprowadzanie danych

- [Licencja](#-licencja)

- [Kontakt](#-kontakt)## 🛠️ Technologie



---- **Python 3.11+**

- **PyQt6** - framework GUI

## ✨ Funkcje- **SQLite/PostgreSQL** - baza danych

- **bcrypt** - hashowanie haseł

### 🔄 Synchronizacja- **PyQt6-i18n** - wsparcie wielojęzyczności

Automatyczna synchronizacja danych między urządzeniami z zachowaniem pełnej funkcjonalności offline.

## 📁 Struktura Projektu

### 🎨 Motywy kolorystyczne

Dynamiczne motywy z możliwością tworzenia własnych schematów kolorów. Aplikacja dostosowuje się do Twoich preferencji.```

PRO-Ka-Po_Kaizen_Freak/

### 🤖 Integracja AI├── src/

Wsparcie dla różnych dostawców AI:│   ├── ui/                     # Moduły interfejsu użytkownika

- **OpenAI GPT-4** - zaawansowana analiza i generowanie treści│   │   ├── __init__.py

- **Google Gemini** - wielomodalne AI│   │   ├── main_window.py      # Główne okno aplikacji

- **Claude** - etyczne AI od Anthropic│   │   ├── navigation_bar.py   # Górny pasek nawigacyjny

- **Groq** - szybka inferencja│   │   ├── management_bar.py   # Pasek zarządzania sekcją

│   │   ├── data_table.py       # Widok tabeli

### 🌐 Wielojęzyczność│   │   ├── quick_input.py      # Sekcja szybkiego wprowadzania

Pełne wsparcie dla wielu języków:│   │   └── dialogs/            # Okna dialogowe

- 🇵🇱 Polski│   │

- 🇬🇧 Angielski│   ├── core/                   # Logika biznesowa

- 🇩🇪 Niemiecki│   │   ├── __init__.py

- 🇪🇸 Hiszpański│   │   ├── task_manager.py     # Zarządzanie zadaniami

- 🇯🇵 Japoński│   │   └── settings.py         # Ustawienia aplikacji

- 🇨🇳 Chiński│   │

│   ├── auth/                   # System autentykacji

### 📱 Responsywność│   │   ├── __init__.py

Dostosowanie interfejsu do różnych rozmiarów ekranów i urządzeń.│   │   ├── login.py            # Logika logowania

│   │   └── register.py         # Logika rejestracji

### 🔒 Bezpieczeństwo│   │

- Szyfrowanie wrażliwych danych│   ├── database/               # Warstwa bazodanowa

- Bezpieczne przechowywanie kluczy API│   │   ├── __init__.py

- Lokalne przechowywanie danych osobowych│   │   ├── models.py           # Modele danych

│   │   └── repository.py       # Repozytoria

---│   │

│   └── utils/                  # Narzędzia pomocnicze

## 🧩 Moduły aplikacji│       ├── __init__.py

│       ├── theme_manager.py    # Zarządzanie motywami

### 🤖 AI Module│       ├── i18n_manager.py     # Zarządzanie tłumaczeniami

Uniwersalna integracja z AI. Wsparcie dla Gemini, OpenAI, Claude, Groq. Transkrypcja, analiza tekstu, generowanie treści.│       └── validators.py       # Walidacja danych

│

**Funkcje:**├── resources/

- Transkrypcja audio i wideo│   ├── i18n/                   # Pliki tłumaczeń

- Podsumowania dokumentów│   │   ├── en.json

- Generowanie treści│   │   ├── pl.json

- Analiza tekstu i sentimentu│   │   └── de.json

- Wsparcie dla wielu dostawców AI│   │

│   ├── themes/                 # Pliki motywów (QSS)

### 🎯 Habit Tracker│   │   ├── light.qss

Śledzenie nawyków w formie tabeli miesięcznej. 6 typów nawyków, statystyki, synchronizacja i analiza postępów.│   │   ├── dark.qss

│   │   └── custom.qss

**Funkcje:**│   │

- Kalendarz miesięczny z wizualizacją│   └── icons/                  # Ikony aplikacji

- 6 typów nawyków (task, counter, checkbox, etc.)│

- Statystyki i wykresy postępów├── tests/                      # Testy jednostkowe

- Przypomnienia i powiadomienia│   ├── test_auth.py

- Synchronizacja między urządzeniami│   ├── test_tasks.py

│   └── test_ui.py

### 🍅 Pomodoro│

Technika zarządzania czasem. Sesje 25-minutowe z przerwami, tematy, statystyki i synchronizacja.├── docs/                       # Dokumentacja

│   ├── architecture.md

**Funkcje:**│   ├── user_guide.md

- Timer Pomodoro (25 min pracy + 5 min przerwy)│   └── api_reference.md

- Tematy i projekty│

- Statystyki produktywności├── .gitignore

- Dźwięki i powiadomienia├── requirements.txt

- Historia sesji├── setup.py

├── main.py                     # Punkt wejścia aplikacji

### 📋 Zadania└── README.md

Główny moduł aplikacji do zarządzania zadaniami. Dynamiczna konfiguracja kolumn, filtry, subtaski i integracja z innymi modułami.```



**Funkcje:**## 🚀 Instalacja i Uruchomienie

- Projekty i tagi

- Priorytety i terminy### Wymagania

- Subtaski i zależności- Python 3.11 lub nowszy

- Dynamiczne kolumny- pip (menedżer pakietów Python)

- Filtry i wyszukiwanie

- Integracja z Kanban i Pomodoro### Kroki instalacji



### 📊 KanBan1. Klonowanie repozytorium:

Wizualne zarządzanie zadaniami metodą KanBan. Przeciąganie kart między kolumnami, śledzenie postępów i optymalizacja workflow.```bash

git clone <repository-url>

**Funkcje:**cd PRO-Ka-Po_Kaizen_Freak

- Drag & drop kart```

- Własne kolumny

- WIP limits2. Utworzenie środowiska wirtualnego:

- Swimlanes```bash

- Filtrowanie i wyszukiwaniepython -m venv venv

```

### 📝 Notatki

Bogaty edytor tekstu z formatowaniem. Tworzenie notatek, tagi, kolory, wyszukiwanie i integracja z zadaniami.3. Aktywacja środowiska wirtualnego:

```bash

**Funkcje:**# Windows

- Rich text editor.\venv\Scripts\Activate.ps1

- Tagi i kategorie

- Kolory i formatowanie# Linux/Mac

- Wyszukiwanie pełnotekstowesource venv/bin/activate

- Załączniki```

- Powiązania z zadaniami

4. Instalacja zależności:

### ⏰ Alarmy```bash

Zarządzanie alarmami i timerami. Cykliczne przypomnienia, dźwięki, popup oraz synchronizacja między urządzeniami.pip install -r requirements.txt

```

**Funkcje:**

- Alarmy jednorazowe i cykliczne5. Uruchomienie aplikacji:

- Własne dźwięki```bash

- Popup notificationspython main.py

- Snooze function```

- Synchronizacja

## 🎨 Zasady Tworzenia Kodu

### 📞 CallCryptor

Zaawansowane zarządzanie nagraniami rozmów. Transkrypcja AI, podsumowania, tagi i integracja z notatkami.### Modularność

- Każdy moduł powinien mieć jedną, jasno określoną odpowiedzialność

**Funkcje:**- Maksymalna długość pliku: ~300 linii (orientacyjnie)

- Nagrywanie rozmów- Separacja logiki biznesowej od warstwy prezentacji

- Transkrypcja AI

- Automatyczne podsumowania### Style Kodowania

- Tagi i wyszukiwanie- PEP 8 - standard kodowania Python

- Integracja z notatkami- Type hints dla wszystkich funkcji i metod

- Szyfrowanie nagrań- Docstrings dla klas i funkcji publicznych

- Komentarze w języku angielskim

### ⚙️ Ustawienia

Konfiguracja aplikacji. Motywy, języki, dźwięki, skróty klawiszowe, środowisko i ustawienia modułów.### Nazewnictwo

- Klasy: PascalCase (np. `MainWindow`, `TaskManager`)

**Funkcje:**- Funkcje/metody: snake_case (np. `get_user`, `save_task`)

- Motywy kolorystyczne- Stałe: UPPER_SNAKE_CASE (np. `MAX_TASKS`, `DEFAULT_THEME`)

- Wybór języka- Pliki: snake_case (np. `main_window.py`, `task_manager.py`)

- Konfiguracja dźwięków

- Globalne skróty klawiszowe## 🌍 Wielojęzyczność (i18n)

- Autostart

- Ustawienia modułówAplikacja wspiera następujące języki:

- 🇵🇱 Polski (domyślny)

### ⌨️ FastKey- 🇬🇧 Angielski

Skróty klawiszowe i szybkie akcje — konfiguracja, przypisywanie, import/eksport skrótów.- 🇩🇪 Niemiecki



**Funkcje:**Pliki tłumaczeń znajdują się w `resources/i18n/` w formacie JSON.

- Własne skróty klawiszowe

- Szybkie akcje## 🎨 System Motywów

- Import/eksport konfiguracji

- Globalne i lokalne skrótyDostępne motywy:

- **Light** - jasny motyw (domyślny)

### 📁 P-File- **Dark** - ciemny motyw

Zarządzanie plikami i dokumentami w aplikacji, podgląd, wersjonowanie i synchronizacja.- **Custom** - motywy użytkownika



**Funkcje:**Style definiowane są w plikach QSS w katalogu `resources/themes/`.

- Zarządzanie plikami

- Podgląd dokumentów## 🔐 Bezpieczeństwo

- Wersjonowanie

- Tagi i foldery- Hasła hashowane przy użyciu bcrypt

- Synchronizacja- Sesje użytkowników z timeoutem

- Walidacja danych wejściowych

### 🧩 PRO App- SQL injection prevention (ORM/parametryzowane zapytania)

Ogólne informacje o aplikacji PRO-Ka-Po, instalacja, konfiguracja i zależności modułów.

## 📝 Roadmap

### 📧 PRO Mail

Integracja poczty, ustawienia kont, pobieranie załączników i automatyzacje wiadomości.### Wersja 1.0 (MVP)

- [x] Struktura projektu

**Funkcje:**- [ ] System logowania/rejestracji

- Wiele kont email- [ ] Podstawowy interfejs (nawigacja + tabela)

- Filtrowanie i reguły- [ ] Dodawanie/edycja zadań

- Szablony wiadomości- [ ] System motywów (light/dark)

- AI-powered odpowiedzi- [ ] Wsparcie dla PL/EN

- Automatyzacje

### Wersja 1.1

### 🌐 P-Web- [ ] Zaawansowane filtrowanie

Moduł P-Web — publikowanie treści, konfiguracja serwera i integracje webowe.- [ ] Eksport danych (CSV, PDF)

- [ ] Statystyki i raporty

### 🗂️ Quickboard- [ ] Wsparcie dla dodatkowych języków

Szybkie tablice, notatki i przypomnienia — lekka alternatywa dla pełnego kanbanu.

### Wersja 2.0

**Funkcje:**- [ ] Synchronizacja w chmurze

- Szybki dostęp- [ ] Aplikacja mobilna

- Clipboard manager- [ ] Współdzielenie zadań

- Historia schowka- [ ] Integracje (Calendar, Email)

- Szybkie notatki

## 🤝 Kontrybuacja

### 👥 TeamWork

Moduł współpracy zespołowej — role, uprawnienia, udostępnianie projektów i komunikacja.Projekt jest rozwijany zgodnie z najlepszymi praktykami:

- Feature branches

**Funkcje:**- Pull requests z code review

- Zespoły i projekty- Automatyczne testy przed merge

- Role i uprawnienia- Semantic versioning

- Czat i komunikacja

- Udostępnianie zadań## 📄 Licencja

- Komentarze i wzmianki

Aplikacja komercyjna - wszelkie prawa zastrzeżone.

---

## 👥 Autorzy

## 🛠️ Instalacja

Projekt rozwijany przez PRO-Ka-Po Team

### Wymagania wstępne

- **Python 3.11** lub nowszy---

- **PostgreSQL 13+** (opcjonalnie, dla funkcji serwerowych)

- System operacyjny: Windows 10/11, Linux, macOS**Status:** 🚧 W trakcie rozwoju

**Wersja:** 0.1.0-alpha

### Krok 1: Klonowanie repozytorium**Ostatnia aktualizacja:** Listopad 2025

# Pro-Ka-Po_V5c

```bash
git clone https://github.com/Piotr19881/PRO-Ka-Po_Kaizen_Freak.git
cd PRO-Ka-Po_Kaizen_Freak
```

### Krok 2: Utworzenie środowiska wirtualnego

```bash
# Windows
python -m venv venv
venv\Scripts\activate

# Linux/Mac
python3 -m venv venv
source venv/bin/activate
```

### Krok 3: Instalacja zależności

```bash
pip install -r requirements.txt
```

### Krok 4: Konfiguracja (opcjonalnie)

1. Skopiuj `config.example.json` do `config.json` (jeśli istnieje)
2. Wypełnij klucze API dla modułów AI (opcjonalnie)
3. Skonfiguruj połączenie z bazą danych (opcjonalnie)

### Krok 5: Uruchomienie aplikacji

```bash
python main.py
```

---

## 📦 Wymagania

### Wymagane biblioteki Python

```
PyQt6>=6.6.1
PyQt6-Qt6>=6.6.1
PyQt6-sip>=13.6.0
psycopg2-binary>=2.9.9
SQLAlchemy>=2.0.23
openai>=1.6.1
google-generativeai>=0.3.2
groq>=0.4.1
loguru>=0.7.2
python-dotenv>=1.0.0
requests>=2.31.0
pillow>=10.1.0
email-validator>=2.1.0
```

Pełna lista w pliku `requirements.txt`.

---

## 📂 Struktura projektu

```
PRO-Ka-Po_Kaizen_Freak/
├── src/                          # Kod źródłowy
│   ├── core/                     # Logika biznesowa
│   ├── ui/                       # Interfejs użytkownika (PyQt6)
│   ├── utils/                    # Narzędzia pomocnicze
│   ├── Modules/                  # Moduły aplikacji
│   │   ├── AI_module/           # Moduł AI
│   │   ├── task_module/         # Zarządzanie zadaniami
│   │   ├── Pomodoro_module/     # Timer Pomodoro
│   │   ├── habbit_tracker_module/ # Śledzenie nawyków
│   │   ├── QuickBoard/          # Clipboard manager
│   │   ├── custom_modules/      # Moduły niestandardowe
│   │   │   ├── mail_client/    # Klient email
│   │   │   ├── TeamWork/       # Współpraca zespołowa
│   │   │   ├── PFile/          # Zarządzanie plikami
│   │   │   └── Shortcuts/      # Skróty klawiszowe
│   │   └── p_web/              # Moduł web
│   └── resources/               # Zasoby (ikony, dźwięki)
├── data/                        # Baza danych i cache
│   ├── i18n/                   # Tłumaczenia
│   ├── shortcuts/              # Konfiguracja skrótów
│   └── browser_profile/        # Profil przeglądarki (NIE W REPO)
├── help_files/                  # Pliki pomocy (HTML)
├── docs/                        # Dokumentacja
├── tests/                       # Testy jednostkowe
├── logs/                        # Logi aplikacji (NIE W REPO)
├── main.py                      # Punkt wejścia
├── requirements.txt             # Zależności Python
└── README.md                    # Ten plik
```

---

## ⚙️ Konfiguracja

### Klucze API (opcjonalnie)

Aby korzystać z funkcji AI, skonfiguruj klucze API w ustawieniach aplikacji:

1. Otwórz **Ustawienia** → **AI Settings**
2. Dodaj klucze API dla:
   - OpenAI
   - Google Gemini
   - Groq
   - Claude (Anthropic)

### Baza danych

Aplikacja domyślnie używa SQLite. Dla zaawansowanych funkcji serwerowych możesz skonfigurować PostgreSQL.

---

## 🚀 Użytkowanie

### Szybki start

1. **Uruchom aplikację**: `python main.py`
2. **Wybierz język**: Kliknij ikonę flagi w prawym górnym rogu
3. **Utwórz pierwsze zadanie**: Przejdź do modułu **Zadania** → **Nowe zadanie**
4. **Skonfiguruj nawyki**: Otwórz **Habit Tracker** → **Dodaj nawyk**
5. **Rozpocznij sesję Pomodoro**: Kliknij **Pomodoro** → **Start**

### Skróty klawiszowe

- `Ctrl+N` - Nowe zadanie
- `Ctrl+Shift+N` - Nowa notatka
- `Ctrl+P` - Pomodoro timer
- `Ctrl+H` - Habit Tracker
- `Ctrl+K` - KanBan
- `Ctrl+,` - Ustawienia

### Pomoc

Kliknij ikonę **?** lub przejdź do `help_files/index.html` w przeglądarce, aby uzyskać szczegółową pomoc dla każdego modułu.

---

## 🔒 Bezpieczeństwo i prywatność

### Dane osobowe - WYKLUCZONE z repozytorium

**To repozytorium jest publiczne. Wszystkie wrażliwe dane są wykluczone:**

- ❌ **Nagrania rozmów** (`data/recordings/`)
- ❌ **Backend i serwer** (`Render_upload/` - zawiera klucze, migracje, konfigurację)
- ❌ **Bazy danych lokalnych** (`*.db`, `*.sqlite`)
- ❌ **Tokeny uwierzytelniające** (`data/tokens.json`)
- ❌ **Ustawienia użytkownika** (`user_settings.json`)
- ❌ **Historia schowka** (`clipboard_history.json`)
- ❌ **Drafty email** (`mail_client/drafts/`)
- ❌ **Profil przeglądarki** (`data/browser_profile/`)
- ❌ **Logi** (`logs/`)
- ❌ **Pliki .env** i konfiguracje z sekretami

### Co znajdziesz w repozytorium

✅ Kod źródłowy aplikacji  
✅ Pliki pomocy i dokumentacja  
✅ Tłumaczenia (i18n)  
✅ Zasoby (ikony, dźwięki)  
✅ Motywy kolorystyczne  
✅ Przykładowe konfiguracje  
✅ Testy jednostkowe  

### Szyfrowanie

- Nagrania rozmów są szyfrowane lokalnie
- Klucze API są przechowywane w bezpiecznej konfiguracji
- Hasła do kont email są szyfrowane

### Synchronizacja

Dane synchronizowane są przez bezpieczne połączenie HTTPS. Możesz wyłączyć synchronizację w ustawieniach.

---

## 🎯 Roadmap

### Wersja 2.0 (Q1 2026)
- [ ] Aplikacja mobilna (React Native)
- [ ] Synchronizacja w chmurze (własny serwer)
- [ ] Rozszerzona integracja AI
- [ ] Plugin system
- [ ] Marketplace dodatków

### Wersja 2.1 (Q2 2026)
- [ ] Integracja z kalendarzami (Google, Outlook)
- [ ] Eksport/import danych (CSV, JSON, Excel)
- [ ] Zaawansowane raporty i statystyki
- [ ] API dla integracji zewnętrznych
- [ ] Dark mode improvements

### Długoterminowe
- [ ] Desktop apps (Electron)
- [ ] Współpraca real-time
- [ ] Integracja z Slack, Teams
- [ ] Voice commands
- [ ] Blockchain-based sync

---

## 🤝 Wsparcie projektu

### Wkład w rozwój

Zapraszamy do współtworzenia! Proces:

1. **Fork** repozytorium
2. Utwórz **branch** dla funkcji (`git checkout -b feature/AmazingFeature`)
3. **Commit** zmian (`git commit -m 'feat: Add AmazingFeature'`)
4. **Push** do brancha (`git push origin feature/AmazingFeature`)
5. Otwórz **Pull Request**

### Konwencje commitów

- `feat:` - nowa funkcja
- `fix:` - poprawka błędu
- `docs:` - dokumentacja
- `style:` - formatowanie kodu
- `refactor:` - refaktoryzacja
- `test:` - testy
- `chore:` - maintenance

### Zgłaszanie błędów

Znalazłeś błąd? [Otwórz issue](https://github.com/Piotr19881/PRO-Ka-Po_Kaizen_Freak/issues/new) z opisem:
- Kroki do reprodukcji
- Oczekiwane zachowanie
- Aktualne zachowanie
- Środowisko (OS, Python version)

### Propozycje funkcji

Masz pomysł na nową funkcję? [Otwórz dyskusję](https://github.com/Piotr19881/PRO-Ka-Po_Kaizen_Freak/discussions/new) w kategorii **Ideas**.

---

## 💝 Podziękowania

Aplikacja wykorzystuje następujące biblioteki open-source:
- **PyQt6** - GUI framework
- **SQLAlchemy** - ORM
- **Loguru** - logging
- **OpenAI, Google, Anthropic** - AI APIs

Dziękujemy wszystkim kontrybutom i społeczności open-source!

---

## 📄 Licencja

Ten projekt jest udostępniony na licencji **Open Source**.

```
Copyright (c) 2025 Piotr Prokop

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```

---

## 📧 Kontakt

**Piotr Prokop**

- 🌐 Website: [www.promirbud.eu](https://www.promirbud.eu)
- 📧 Email: [piotr.prokop@promirbud.eu](mailto:piotr.prokop@promirbud.eu)
- 🐙 GitHub: [@Piotr19881](https://github.com/Piotr19881)

---

## 🏢 O firmie

**Promir-Bud** to producent budynków modułowych i kontenerowych. Nasza aplikacja PRO-Ka-Po została stworzona wewnętrznie do zarządzania projektami budowlanymi i została udostępniona społeczności open-source.

Odwiedź nas: [www.promirbud.eu](https://www.promirbud.eu)

---

<p align="center">
  <strong>Stworzone z ❤️ dla pasjonatów KAIZEN</strong>
</p>

<p align="center">
  <a href="#-spis-treści">⬆️ Wróć do góry</a>
</p>
