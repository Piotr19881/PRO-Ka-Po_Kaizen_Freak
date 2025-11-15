# PRO-Ka-Po Kaizen Freak - Dokumentacja pomocy

Witamy w dokumentacji pomocy aplikacji **PRO-Ka-Po Kaizen Freak Edition**!

## 📚 Dostęp do dokumentacji

Ta dokumentacja jest dostępna na żywo pod adresem:
**https://piotr19881.github.io/PRO-Ka-Po_Kaizen_Freak/**

## 🌐 Moduły aplikacji

Dokumentacja obejmuje następujące moduły:

- **[AI Module](ai_help.html)** - Uniwersalna integracja z AI (Gemini, OpenAI, Claude, Grok)
- **[Habit Tracker](habbit_tracker_help.html)** - Śledzenie nawyków w formie tabeli miesięcznej
- **[Pomodoro](pomodoro_help.html)** - Technika zarządzania czasem
- **[Zadania](tasks_help.html)** - Główny moduł zarządzania zadaniami
- **[KanBan](kanban_help.html)** - Wizualne zarządzanie zadaniami
- **[Notatki](notes_help.html)** - Bogaty edytor tekstu z formatowaniem
- **[Alarmy](alarms_help.html)** - Zarządzanie alarmami i timerami
- **[CallCryptor](callcryptor_help.html)** - Zaawansowane zarządzanie nagraniami rozmów
- **[Ustawienia](settings_help.html)** - Konfiguracja aplikacji
- **[FastKey](FastKey_help.html)** - Skróty klawiszowe i szybkie akcje
- **[P-File](pfile_help.html)** - Zarządzanie plikami i dokumentami
- **[PRO App](pro_app.html)** - Ogólne informacje o aplikacji
- **[PRO Mail](pro_mail_help.html)** - Integracja poczty
- **[P-Web](p_web_help.html)** - Moduł publikowania treści
- **[Quickboard](quickboard_help.html)** - Szybkie tablice i notatki
- **[TeamWork](TeamWork_module.html)** - Moduł współpracy zespołowej

## 🌍 Wielojęzyczność

Dokumentacja zawiera wbudowany system tłumaczeń obsługujący:
- Polski (domyślny)
- English
- Deutsch

Przełącznik języków znajduje się w prawym górnym rogu każdej strony.

## 🚀 Lokalne przeglądanie

Aby przeglądać dokumentację lokalnie:

```bash
# Prosta metoda - Python HTTP server
cd help_files
python -m http.server 8000
# Otwórz http://localhost:8000 w przeglądarce

# Lub bezpośrednio otwórz index.html w przeglądarce
```

## 📝 Struktura plików

```
help_files/
├── index.html              # Strona główna
├── assets/                 # Zasoby
│   ├── lang-switcher.js   # System tłumaczeń
│   ├── lang-switcher.css  # Style przełącznika języków
│   └── i18n/              # Pliki tłumaczeń
│       ├── en.json
│       ├── pl.json
│       └── i18n.js
├── ai_help.html
├── habbit_tracker_help.html
├── pomodoro_help.html
├── tasks_help.html
├── kanban_help.html
├── notes_help.html
├── alarms_help.html
├── callcryptor_help.html
├── settings_help.html
├── FastKey_help.html
├── pfile_help.html
├── pro_app.html
├── pro_mail_help.html
├── p_web_help.html
├── quickboard_help.html
└── TeamWork_module.html
```

## 🔧 Aktualizacja dokumentacji

Aby zaktualizować dokumentację:

1. Edytuj odpowiednie pliki HTML w folderze `help_files/`
2. Commituj zmiany do repozytorium
3. Push do brancha `main`
4. GitHub Actions automatycznie wdroży zmiany na GitHub Pages

## 📄 Licencja

© 2025 Piotr Prokop  
Aplikacja udostępniona na licencji Open Source

## 📧 Kontakt

- Website: https://www.promirbud.eu
- Email: piotr.prokop@promirbud.eu
- GitHub: https://github.com/Piotr19881/PRO-Ka-Po_Kaizen_Freak
