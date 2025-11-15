# Instrukcja publikacji dokumentacji na GitHub Pages

## 🎯 Cel

Folder `help_files` zawiera pełną dokumentację pomocy aplikacji PRO-Ka-Po w formacie HTML. Dokumentacja została skonfigurowana do automatycznej publikacji na GitHub Pages.

## ✅ Co zostało zrobione

1. ✅ Utworzono workflow GitHub Actions (`.github/workflows/deploy-help-pages.yml`)
2. ✅ Dodano README.md w folderze `help_files` z opisem dokumentacji
3. ✅ Dodano plik `.nojekyll` dla poprawnej obsługi zasobów
4. ✅ Zaktualizowano główny README.md z linkiem do dokumentacji online

## 🚀 Jak uruchomić GitHub Pages

### Krok 1: Włącz GitHub Pages w ustawieniach repozytorium

1. Przejdź do swojego repozytorium: https://github.com/Piotr19881/PRO-Ka-Po_Kaizen_Freak
2. Kliknij **Settings** (Ustawienia)
3. W lewym menu wybierz **Pages**
4. W sekcji "Build and deployment":
   - **Source**: wybierz "GitHub Actions"
   - (To już wszystko! Workflow automatycznie opublikuje dokumentację)

### Krok 2: Uruchom workflow ręcznie (opcjonalnie)

Po zmergowaniu tego PR:

1. Przejdź do zakładki **Actions** w repozytorium
2. Wybierz workflow "Deploy Help Files to GitHub Pages"
3. Kliknij **Run workflow** → wybierz branch `main` → **Run workflow**

### Krok 3: Sprawdź publikację

Po kilku minutach dokumentacja będzie dostępna pod adresem:
**https://piotr19881.github.io/PRO-Ka-Po_Kaizen_Freak/**

## 🔄 Automatyczna aktualizacja

Workflow jest skonfigurowany aby automatycznie publikować zmiany gdy:
- Zmiany są pushowane do brancha `main`
- Zmienione zostają pliki w folderze `help_files/`

Nie musisz robić nic więcej - każda zmiana w dokumentacji będzie automatycznie publikowana!

## 📝 Struktura dokumentacji

```
help_files/
├── index.html              # Strona główna (punkt wejścia)
├── .nojekyll              # Konfiguracja GitHub Pages
├── README.md              # Ten plik
├── assets/                # Zasoby (JS, CSS, i18n)
│   ├── lang-switcher.js   # System tłumaczeń
│   ├── lang-switcher.css  
│   └── i18n/              
│       ├── pl.json        # Polskie tłumaczenia
│       ├── en.json        # Angielskie tłumaczenia
│       └── i18n.js
└── [moduły].html          # Dokumentacja poszczególnych modułów
```

## 🌍 Funkcje dokumentacji

- ✅ Responsywny design (działa na desktop i mobile)
- ✅ System tłumaczeń (PL/EN/DE)
- ✅ Piękny, nowoczesny interfejs
- ✅ Nawigacja między modułami
- ✅ Wyszukiwanie (w przeglądarce: Ctrl+F)

## 🛠️ Testowanie lokalne

Aby przetestować dokumentację lokalnie przed publikacją:

```bash
cd help_files
python -m http.server 8000
```

Następnie otwórz http://localhost:8000 w przeglądarce.

## 📧 Wsparcie

Jeśli masz pytania lub problemy:
- Email: piotr.prokop@promirbud.eu
- GitHub Issues: https://github.com/Piotr19881/PRO-Ka-Po_Kaizen_Freak/issues

---

**Autor**: GitHub Copilot  
**Data**: 2025-11-15
