# 🧪 Tests - UI Test Launcher

## Szybkie testowanie komponentów UI

Ten folder zawiera narzędzie **UI Test Launcher** do szybkiego testowania pojedynczych komponentów UI bez konieczności uruchamiania całej aplikacji.

## 🚀 Quick Start

```powershell
# Uruchom launcher
.\run_ui_tests.ps1
```

## 📁 Pliki w tym folderze

- **`test_ui_launcher.py`** - Główne narzędzie do testowania UI
- **`run_ui_tests.ps1`** - Skrypt PowerShell do łatwego uruchamiania
- **`README.md`** - Ten plik

## 📖 Pełna dokumentacja

Zobacz: `docs/UI_TEST_LAUNCHER_GUIDE.md` dla szczegółowej dokumentacji

## ✨ Funkcje

- 🎨 Testowanie z różnymi motywami
- 🔄 Automatyczne odświeżanie otwartych okien po zmianie motywu
- ⚡ Szybkie uruchamianie - bez ładowania całej aplikacji
- 📋 Przejrzysta lista wszystkich komponentów UI

## 🎯 Przykład użycia

1. Uruchom `run_ui_tests.ps1`
2. Wybierz motyw z listy (np. "Dark Theme")
3. Kliknij "Zastosuj motyw"
4. Kliknij przycisk komponentu (np. "▶ AI Settings")
5. Komponent otworzy się z wybranym motywem
6. Zmień motyw → wszystkie okna automatycznie się odświeżą!

## 💡 Wskazówka

Używaj tego narzędzia podczas refaktoryzacji UI - znacznie przyspiesza testowanie!
