# 🎨 Theme Refactoring Checklist - UI Files

## 🧪 Narzędzie testowe
**UI Test Launcher** - Szybkie testowanie komponentów bez uruchamiania całej aplikacji!

```powershell
# Uruchom launcher testów
cd tests
.\run_ui_tests.ps1
```

📖 **Pełna dokumentacja**: `docs/UI_TEST_LAUNCHER_GUIDE.md`

---

## 📋 Cel refaktoryzacji
Usunięcie wszystkich hardkodowanych stylów i pełna integracja z ThemeManager w plikach UI.

## ✅ Zakres prac dla każdego pliku:
1. Znaleźć wszystkie `setStyleSheet()` z hardkodowanymi kolorami
2. Zaimplementować/ulepszyć metodę `apply_theme()`
3. Użyć `get_current_colors()` z ThemeManager
4. Zastąpić hardkodowane kolory zmiennymi z ThemeManager
5. **Przetestować z UI Test Launcher** (zmiana motywu jasny/ciemny)

---

## 📂 Lista plików do refaktoryzacji (36 plików)

### ✅ **UKOŃCZONE**
- [x] `config_view.py` - Zrefaktoryzowany (GeneralSettingsTab, EnvironmentSettingsTab, SettingsView)
- [x] `style_creator_dialog.py` - Zrefaktoryzowany (ColorPickerWidget, globalny podgląd)
- [x] `ai_settings.py` - Zrefaktoryzowany (hardkodowane kolory usunięte, apply_theme dodany)
- [x] `ai_summary_dialog.py` - Zrefaktoryzowany (hardkodowany kolor #9C27B0 → accent_primary)
- [x] `ai_task_communication_dialog.py` - Zrefaktoryzowany (apply_theme dodany, semantic highlight zachowane)
- [x] `assistant_settings_tab.py` - Zrefaktoryzowany (hardkodowane "gray" → ObjectName infoLabel)
- [x] `main_window.py` - Zrefaktoryzowany (hardcoded #2196F3 → accent_primary, apply_theme, settings propagacja)
- [x] `navigation_bar.py` - Zrefaktoryzowany (apply_theme dodany, ObjectName navButton)

---

### 🔄 **DO WYKONANIA**

#### **Grupa 1: AI & Asystent (4 pliki)**
- [x] `ai_settings.py` - ✅ Zrefaktoryzowany (hardkodowane kolory usunięte, apply_theme dodany)
- [x] `ai_summary_dialog.py` - ✅ Zrefaktoryzowany (hardkodowany kolor #9C27B0 → accent_primary)
- [x] `ai_task_communication_dialog.py` - ✅ Zrefaktoryzowany (apply_theme dodany, hardkodowane kolory usunięte, semantic highlight zachowane)
- [x] `assistant_settings_tab.py` - ✅ Zrefaktoryzowany (hardkodowane "gray" → ObjectName infoLabel, styling dodany)

#### **Grupa 2: Główne widoki (8 plików)**
- [x] `main_window.py` - ✅ Zrefaktoryzowany (hardcoded #2196F3 → accent_primary dla kolorów notatek, dodano apply_theme)
- [x] `navigation_bar.py` - ✅ Zrefaktoryzowany (dodano apply_theme, ObjectName dla przycisków)
- [x] `task_view.py` - ✅ Zrefaktoryzowany (stretch_btn state-based colors, wszystkie przyciski akcji, apply_theme)
- [x] `kanban_view.py` - ✅ Zrefaktoryzowany (usunięto ostatnie hardcoded #FFFFFF, done card, note button)
- [x] `note_view.py` - ✅ Zrefaktoryzowany (apply_theme używa get_current_colors() zamiast hardcode)
- [x] `pomodoro_view.py` - ✅ Zrefaktoryzowany (timer colors, progress bar, popup window, apply_theme)
- [ ] `alarms_view.py` - Widok alarmów
- [ ] `quickboard_view.py` - Widok QuickBoard (schowek)

#### **Grupa 3: Moduły specjalistyczne (5 plików)**
- [ ] `callcryptor_view.py` - Moduł CallCryptor
- [ ] `callcryptor_dialogs.py` - Dialogi CallCryptor
- [ ] `pro_app_view.py` - Menedżer aplikacji
- [ ] `p_web_view.py` - Przeglądarka webowa
- [ ] `p_web_view_v2.py` - Przeglądarka webowa v2

#### **Grupa 4: Paski zadań (2 pliki)**
- [ ] `task_bar.py` - Pasek zadań główny
- [ ] `quick_task_bar.py` - Szybki pasek zadań

#### **Grupa 5: Dialogi i okna pomocnicze (11 plików)**
- [ ] `auth_window.py` - Okno autoryzacji
- [ ] `email_settings_card.py` - Karta ustawień email (częściowo done)
- [ ] `custom_button_dialog.py` - Dialog własnych przycisków
- [ ] `habit_statistics_window.py` - Okno statystyk nawyków
- [ ] `help_dialogs.py` - Dialogi pomocy
- [ ] `help_view.py` - Widok pomocy
- [ ] `kanban_log_dialog.py` - Dialog logów Kanban
- [ ] `tag_manager_dialog.py` - Menedżer tagów
- [ ] `task_config_dialog.py` - Dialog konfiguracji zadań
- [ ] `transcription_dialog.py` - Dialog transkrypcji
- [ ] `ui_task_simple_dialogs.py` - Proste dialogi zadań

#### **Grupa 6: Komponenty pomocnicze (3 pliki)**
- [ ] `simple_pweb_dialogs.py` - Proste dialogi webowe
- [ ] `status_led.py` - Komponent LED statusu
- [ ] `p_web_view_old_backup.py` - Backup (niski priorytet)

---

## 🔍 Szablon refaktoryzacji dla każdego pliku

### Krok 1: Analiza
```bash
# Sprawdź hardkodowane style
grep -n "setStyleSheet" plik.py
grep -n "#[0-9A-F]" plik.py
```

### Krok 2: Sprawdź czy istnieje apply_theme()
- Jeśli TAK → ulepsz
- Jeśli NIE → dodaj

### Krok 3: Zaimplementuj wzorzec
```python
def apply_theme(self):
    """Zastosuj aktualny motyw"""
    if not hasattr(self, 'theme_manager'):
        from ..utils.theme_manager import get_theme_manager
        self.theme_manager = get_theme_manager()
    
    if not self.theme_manager:
        return
    
    try:
        colors = self.theme_manager.get_current_colors()
        
        # Zastosuj style z get_current_colors()
        self.setStyleSheet(f"""
            QWidget {{
                background-color: {colors.get('bg_main', '#FFFFFF')};
                color: {colors.get('text_primary', '#000000')};
            }}
        """)
        
        logger.debug(f"[{self.__class__.__name__}] Theme applied")
    except Exception as e:
        logger.error(f"[{self.__class__.__name__}] Error applying theme: {e}")
```

### Krok 4: Testowanie
1. Uruchom aplikację
2. Przejdź do modułu/widoku
3. Zmień motyw (Layout 1 ↔ Layout 2)
4. Sprawdź czy wszystkie elementy się zaktualizowały
5. Zaznacz [x] w liście

---

## 📊 Postęp

- **Ukończone:** 3/36 (8%)
- **W trakcie:** 0/36
- **Do zrobienia:** 33/36 (92%)

---

## 🎯 Priorytety

### **Wysoki priorytet:**
1. `main_window.py` - Kluczowy plik
2. `navigation_bar.py` - Widoczny przez cały czas
3. `task_view.py` - Główny widok
4. `kanban_view.py` - Często używany
5. `note_view.py` - Często używany

### **Średni priorytet:**
6. `pomodoro_view.py`
7. `alarms_view.py`
8. `task_bar.py`
9. `quick_task_bar.py`
10. AI/Assistant pliki

### **Niski priorytet:**
- Dialogi pomocnicze
- Backup files
- Komponenty rzadko używane

---

## 📝 Notatki

### Wzorce do zastosowania:
- **Przyciski główne:** `accent_primary`, `accent_hover`, `accent_pressed`
- **Tło:** `bg_main`, `bg_secondary`
- **Tekst:** `text_primary`, `text_secondary`
- **Obramowania:** `border_light`, `border_dark`
- **Nawigacja:** `nav_bg`, `nav_text`, `nav_hover_bg`, `nav_checked_bg`
- **Tabele:** `table_header_bg`, `table_row_bg`, `table_selection`

### Kluczowe kolory ThemeManager:
```python
colors = {
    'bg_main': '#FFFFFF',           # Główne tło
    'bg_secondary': '#F5F5F5',      # Drugorzędne tło
    'text_primary': '#2C3E50',      # Tekst główny
    'text_secondary': '#7F8C8D',    # Tekst drugorzędny
    'accent_primary': '#FF9800',    # Akcent główny
    'accent_hover': '#F57C00',      # Akcent hover
    'accent_pressed': '#E65100',    # Akcent wciśnięty
    'border_light': '#DDD',         # Obramowanie jasne
    'border_dark': '#888',          # Obramowanie ciemne
}
```

---

## 🚀 Start refaktoryzacji

**Następny plik:** `ai_summary_dialog.py`

**Data rozpoczęcia:** 2025-11-11
**Ostatnia aktualizacja:** 2025-11-11 (3/36 ukończone)
