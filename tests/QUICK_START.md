# 🚀 Quick Start - UI Test Launcher

## Jak szybko przetestować komponenty UI?

### Krok 1: Uruchom launcher
```powershell
cd tests
.\run_ui_tests.ps1
```

### Krok 2: Wybierz motyw
- Kliknij combo box "Aktualny motyw"
- Wybierz motyw (np. "Dark Theme")
- Kliknij **"✓ Zastosuj motyw"**

### Krok 3: Testuj komponenty
Kliknij przycisk komponentu, który chcesz przetestować:

#### ✅ Gotowe do testowania:
- **▶ AI Settings** - Panel ustawień AI
- **▶ AI Summary Dialog** - Dialog podsumowań
- **▶ AI Task Communication Dialog** - Dialog planowania AI
- **▶ Style Creator Dialog** - Kreator motywów
- **▶ Config View** - Widok konfiguracji

#### ⏳ W przygotowaniu:
- Assistant Settings
- Main Window
- Task View
- Kanban View
- i inne...

### Krok 4: Testuj zmianę motywu
1. Otwórz kilka komponentów (np. AI Settings + Style Creator)
2. Zmień motyw na inny
3. Kliknij **"✓ Zastosuj motyw"**
4. **Wszystkie otwarte okna automatycznie się odświeżą!** 🎨

## 💡 Pro Tips

### Szybkie testowanie refaktoryzacji:
```
1. Zrefaktoruj plik (np. ai_settings.py)
2. Uruchom launcher
3. Wybierz "Dark Theme" → test
4. Zmień na "Light Theme" → test
5. Gotowe! ✅
```

### Testowanie wielu komponentów:
```
1. Otwórz 3-4 komponenty naraz
2. Zmień motyw
3. Zobacz jak wszystkie reagują jednocześnie
```

### Debug błędów:
```
- Jeśli komponent nie działa → sprawdź komunikat błędu
- Jeśli motyw się nie zmienia → sprawdź apply_theme()
- Sprawdź konsolę terminala dla szczegółów
```

## 📋 Checklist testowania motywu

Po refaktoryzacji pliku UI:

- [ ] Uruchom launcher
- [ ] Otwórz zrefaktoryzowany komponent
- [ ] Testuj z "Dark Theme"
- [ ] Testuj z "Light Theme"
- [ ] Sprawdź czy wszystkie kolory są dynamiczne
- [ ] Sprawdź czy zmiana motywu działa bez restartu
- [ ] Oznacz plik jako ✅ w THEME_REFACTORING_CHECKLIST.md

## 🎯 Przykłady

### Przykład 1: Test AI Settings
```powershell
# Uruchom
.\run_ui_tests.ps1

# W launcherze:
1. Wybierz "Dark Theme" → Zastosuj
2. Kliknij "▶ AI Settings"
3. Sprawdź kolory przycisków, tekstu, tła
4. Zmień na "Light Theme" → Zastosuj
5. Sprawdź czy AI Settings się odświeżył
```

### Przykład 2: Test wielu dialogów
```powershell
# Uruchom
.\run_ui_tests.ps1

# W launcherze:
1. Kliknij "▶ AI Settings"
2. Kliknij "▶ Style Creator Dialog"
3. Kliknij "▶ Config View"
4. Zmień motyw → wszystkie 3 okna się zaktualizują!
```

## ❓ FAQ

**Q: Dlaczego niektóre komponenty pokazują "To be implemented"?**  
A: Te komponenty jeszcze nie zostały dodane do launchera. Dodaj je według wzoru w dokumentacji.

**Q: Jak dodać nowy komponent do testów?**  
A: Zobacz `docs/UI_TEST_LAUNCHER_GUIDE.md` → sekcja "Dodawanie nowych komponentów"

**Q: Launcher się nie uruchamia?**  
A: Sprawdź czy jesteś w folderze `tests/` i czy Python jest w PATH

**Q: Komponent pokazuje błąd?**  
A: Sprawdź komunikat błędu - prawdopodobnie brakuje importów lub mock danych

---

**Gotowy do testowania? Uruchom:** `.\run_ui_tests.ps1` 🚀
