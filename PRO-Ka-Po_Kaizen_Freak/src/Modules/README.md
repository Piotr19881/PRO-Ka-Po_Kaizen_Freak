# Modules - Moduły Funkcjonalne Aplikacji

Ten folder zawiera moduły funkcjonalne aplikacji. Każdy moduł to osobny podfolder z pełną funkcjonalnością.

## Struktura Modułu

Każdy moduł powinien mieć następującą strukturę:

```
module_name/
├── __init__.py              # Inicjalizacja modułu
├── view.py                  # Widok główny modułu (UI)
├── management_bar.py        # Pasek zarządzania (opcjonalnie)
├── controller.py            # Logika kontrolera
├── models.py                # Modele danych (opcjonalnie)
└── README.md               # Dokumentacja modułu
```

## Planowane Moduły

1. **tasks/** - Moduł zarządzania zadaniami
2. **kanban/** - Widok tablicy Kanban
3. **tables/** - Moduł tabel
4. **notes/** - Moduł notatek
5. **habit_tracker/** - Śledzenie nawyków
6. **pomodoro/** - Timer Pomodoro
7. **alarms/** - Alarmy i przypomnienia
8. **settings/** - Ustawienia aplikacji

## Konwencje

- Każdy moduł jest niezależny
- Komunikacja między modułami przez sygnały PyQt
- Moduły mogą współdzielić wspólne komponenty z `src/ui/`
- Każdy moduł musi implementować interfejs `ModuleInterface`

## Przykład Użycia

```python
from src.Modules.tasks import TasksModule

module = TasksModule()
widget = module.get_widget()
management_bar = module.get_management_bar()
```
