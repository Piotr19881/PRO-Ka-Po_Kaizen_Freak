# Status refaktoryzacji task_config_dialog.py

## ✅ ZROBIONE:

### 1. Integracja z theme_manager i i18n_manager
- ✅ Dodano import `from ..utils.i18n_manager import get_i18n, t`
- ✅ Dodano import `from ..utils.theme_manager import get_theme_manager`
- ✅ Dodano metodę `_apply_theme()` w TaskConfigDialog
- ✅ Wywołanie `self._apply_theme()` w `__init__`
- ✅ Dodano `_apply_theme()` w AddTagDialog

### 2. Poprawki rozmiaru pól i kolumn

#### W sekcji kolumn (_create_columns_section):
- ✅ Kolumna "Pozycja" - Fixed width (50px)
- ✅ Kolumna "Typ" - Interactive (120px)
- ✅ Kolumna "Nazwa" - Stretch (rozciągliwa)
- ✅ Kolumna "Widoczna" - Fixed (100px)
- ✅ Kolumna "Pasek dolny" - Fixed (120px)
- ✅ Kolumna "Wartość domyślna" - Interactive (150px)

#### W sekcji tagów (_create_tags_section):
- ✅ Kolumna "Tag" - Stretch
- ✅ Kolumna "Kolor" - Fixed (100px)
- ✅ Kolumna pusta - Fixed (30px)

#### W sekcji list (_create_lists_section):
- ✅ Kolumna "Nazwa listy" - Interactive (200px)
- ✅ Kolumna "Wartości" - Stretch

### 3. Tłumaczenia dodane do pl.json
- ✅ tasks.config.* - wszystkie sekcje i kolumny
- ✅ tasks.dialog.* - wszystkie dialogi
- ✅ tasks.error.* - wszystkie komunikaty błędów
- ✅ tasks.confirm.* - komunikaty potwierdzenia
- ✅ tasks.success.* - komunikaty sukcesu

### 4. Zamienione stringi na t():
- ✅ AddTagDialog - tytuł okna, labele formularza
- ✅ TaskConfigDialog - tytuł okna
- ✅ _create_columns_section - tytuł sekcji, nagłówki kolumn, przyciski
- ✅ _create_tags_section - tytuł sekcji, nagłówki, przyciski
- ✅ _create_lists_section - tytuł sekcji, nagłówki, przyciski
- ✅ AddTagDialog._on_accept - komunikaty błędów (częściowo)

### 5. Poprawki w formularzach
- ✅ AddTagDialog - dodano `setMinimumWidth(300)` dla QLineEdit
- ✅ AddTagDialog - dodano `form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)`
- ✅ AddTagDialog - dodano `form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)`

## ❌ DO ZROBIENIA:

### 1. Zamiany stringów w dialogach na t():

#### EditTagDialog:
- [ ] Tytuł okna
- [ ] Labele formularza
- [ ] Komunikaty błędów
- [ ] Placeholder
- [ ] Dialog wyboru koloru

#### AddColumnDialog:
- [ ] Tytuł okna
- [ ] Labele formularza (nazwa, typ, wartość domyślna, lista)
- [ ] Typy kolumn (7 typów)
- [ ] Placeholder
- [ ] Komunikaty błędów
- [ ] Opcje widoczności
- [ ] "(wybierz listę)"
- [ ] "Odznaczone" / "Zaznaczone"

#### EditColumnDialog:
- [ ] Tytuł okna
- [ ] Ostrzeżenie o kolumnie systemowej
- [ ] Labele formularza
- [ ] Komunikaty błędów

#### AddListDialog:
- [ ] Tytuł okna
- [ ] Labele formularza
- [ ] Placeholder
- [ ] "Wartości listy" (GroupBox)
- [ ] Przyciski (Dodaj, Usuń, ▲, ▼)
- [ ] Komunikaty błędów

#### EditListDialog:
- [ ] Tytuł okna
- [ ] Labele formularza
- [ ] Komunikaty błędów
- [ ] Przyciski

### 2. Zamiany stringów w handlerach TaskConfigDialog:

#### _on_add_column:
- [ ] QMessageBox.information - komunikat sukcesu

#### _on_edit_column:
- [ ] QMessageBox.warning - brak zaznaczenia
- [ ] QMessageBox.warning - nie znaleziono kolumny
- [ ] QMessageBox.information - sukces

#### _on_delete_column:
- [ ] QMessageBox.warning - brak zaznaczenia
- [ ] QMessageBox.warning - nie można usunąć systemowej
- [ ] QMessageBox.question - potwierdzenie
- [ ] QMessageBox.information - sukces

#### _on_add_tag:
- [ ] QMessageBox.information - sukces

#### _on_edit_tag:
- [ ] QMessageBox.warning - brak zaznaczenia
- [ ] QMessageBox.warning - nie znaleziono
- [ ] QMessageBox.information - sukces

#### _on_delete_tag:
- [ ] QMessageBox.warning - brak zaznaczenia
- [ ] QMessageBox.question - potwierdzenie
- [ ] QMessageBox.information - sukces

#### _on_add_list:
- [ ] QMessageBox.information - sukces

#### _on_edit_list:
- [ ] QMessageBox.warning - brak zaznaczenia
- [ ] QMessageBox.warning - nie znaleziono
- [ ] QMessageBox.information - sukces

#### _on_delete_list:
- [ ] QMessageBox.warning - brak zaznaczenia
- [ ] QMessageBox.warning - lista używana (z formatowaniem)
- [ ] QMessageBox.question - potwierdzenie
- [ ] QMessageBox.information - sukces

#### _on_move_column_up/_on_move_column_down:
- [ ] Ewentualne komunikaty błędów

### 3. Pozostałe poprawki:
- [ ] Dodać _apply_theme() we wszystkich dialogach (Edit*, Add*)
- [ ] Poprawić rozmiary pól w formularzach wszystkich dialogów
- [ ] Sprawdzić czy wszystkie QLineEdit mają ustawione minimalne szerokości
- [ ] Dodać QFormLayout.FieldGrowthPolicy we wszystkich formularzach

### 4. Tłumaczenia do dodania (jeśli brakuje):
- [ ] Sprawdzić czy wszystkie klucze istnieją w pl.json
- [ ] Dodać tłumaczenia dla en.json
- [ ] Dodać tłumaczenia dla de.json

## PRZYKŁADOWE ZAMIANY:

```python
# PRZED:
QMessageBox.warning(self, "Błąd", "Podaj nazwę kolumny")

# PO:
QMessageBox.warning(self, t('tasks.error.no_selection'), t('tasks.error.provide_column_name'))
```

```python
# PRZED:
QMessageBox.information(self, "Sukces", f"Kolumna '{updated_column['id']}' została zaktualizowana")

# PO:
QMessageBox.information(self, t('button.save'), 
                       t('tasks.success.column_updated').replace('{0}', updated_column['id']))
```

```python
# PRZED:
self.setWindowTitle("Dodaj kolumnę")

# PO:
self.setWindowTitle(t('tasks.dialog.add_column.title'))
```

## PRIORYTETY:

1. **WYSOKI**: Zamiany w komunikatach (QMessageBox) - użytkownik widzi
2. **ŚREDNI**: Zamiany w dialogach (tytuły, labele) - użytkownik widzi
3. **NISKI**: Dodanie _apply_theme w pozostałych dialogach
4. **NISKI**: Tłumaczenia en.json i de.json

## NOTATKI:

- Wszystkie tłumaczenia są już w pl.json
- Theme manager jest zintegrowany z TaskConfigDialog
- Główna tabela kolumn ma poprawione rozmiary
- Należy użyć `.replace('{0}', value)` dla parametryzowanych komunikatów
- Dla list wartości używanych przez kolumny: `"\n".join(used_by)` w .replace('{1}', ...)
