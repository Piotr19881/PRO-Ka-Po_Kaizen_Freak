"""
Skrypt do automatycznej aktualizacji task_config_dialog.py z i18n i theme manager
"""
import re

# Mapowanie stringów do kluczy tłumaczeń
REPLACEMENTS = {
    # Tytuły dialogów
    r'"Dodaj tag"': "t('tasks.dialog.add_tag.title')",
    r'"Edytuj tag"': "t('tasks.dialog.edit_tag.title')",
    r'"Dodaj kolumnę"': "t('tasks.dialog.add_column.title')",
    r'"Edytuj kolumnę"': "t('tasks.dialog.edit_column.title')",
    r'"Dodaj listę własną"': "t('tasks.dialog.add_list.title')",
    r'"Edytuj listę własną"': "t('tasks.dialog.edit_list.title')",
    r'"Konfiguracja tabeli zadań"': "t('tasks.config.title')",
    
    # Labele formularzy - tagi
    r'"Nazwa tagu:"': "t('tasks.dialog.tag.name_label')",
    r'"Kolor:"': "t('tasks.dialog.tag.color_label')",
    r'"Wybierz kolor\.\.\."': "t('tasks.dialog.tag.choose_color')",
    r'"np\. Pilne, W trakcie, Do zrobienia\.\.\."': "t('tasks.dialog.tag.name_placeholder')",
    
    # Labele formularzy - kolumny
    r'"Nazwa kolumny:"': "t('tasks.dialog.column.name_label')",
    r'"Typ kolumny:"': "t('tasks.dialog.column.type_label')",
    r'"Wartość domyślna:"': "t('tasks.dialog.column.default_label')",
    r'"Wybierz listę:"': "t('tasks.dialog.column.list_label')",
    r'"Widoczność"': "t('tasks.dialog.column.visibility')",
    r'"Widoczna w głównym widoku zadań"': "t('tasks.dialog.column.visible_main')",
    r'"Widoczna w pasku dolnym \(quick input\)"': "t('tasks.dialog.column.visible_bar')",
    r'"⚠️ Kolumna systemowa - możesz edytować tylko niektóre właściwości"': "t('tasks.dialog.column.system_warning')",
    r'"np\. Kategoria, Budżet, Deadline\.\.\."': "t('tasks.dialog.column.name_placeholder')",
    
    # Typy kolumn
    r'"tekstowa"': "t('tasks.config.column_type.text')",
    r'"Waluta"': "t('tasks.config.column_type.currency')",
    r'"data"': "t('tasks.config.column_type.date')",
    r'"Czas trwania"': "t('tasks.config.column_type.duration')",
    r'"lista"': "t('tasks.config.column_type.list')",
    r'"checkbox"': "t('tasks.config.column_type.checkbox')",
    r'"liczbowa"': "t('tasks.config.column_type.number')",
    
    # Labele formularzy - listy
    r'"Nazwa listy:"': "t('tasks.dialog.list.name_label')",
    r'"Wartości listy"': "t('tasks.dialog.list.values_group')",
    r'"Nowa wartość\.\.\."': "t('tasks.dialog.list.value_placeholder')",
    r'"Dodaj"': "t('tasks.dialog.list.button_add_value')",
    r'"np\. Priorytety, Statusy, Kategorie\.\.\."': "t('tasks.dialog.list.name_placeholder')",
    
    # Inne
    r'"\(wybierz listę\)"': "t('tasks.dialog.list_select')",
    r'"Odznaczone"': "t('tasks.dialog.checkbox_unchecked')",
    r'"Zaznaczone"': "t('tasks.dialog.checkbox_checked')",
    
    # Komunikaty błędów
    r'"Błąd"': "t('tasks.error.no_selection')",
    r'"Podaj nazwę kolumny"': "t('tasks.error.provide_column_name')",
    r'"Podaj nazwę tagu"': "t('tasks.error.provide_tag_name')",
    r'"Podaj nazwę listy"': "t('tasks.error.provide_list_name')",
    r'"Wybierz kolumnę do edycji"': "t('tasks.error.select_column')",
    r'"Zaznacz kolumnę do usunięcia"': "t('tasks.error.select_column_delete')",
    r'"Zaznacz tag do edycji"': "t('tasks.error.select_tag')",
    r'"Zaznacz tag do usunięcia"': "t('tasks.error.select_tag_delete')",
    r'"Zaznacz listę do edycji"': "t('tasks.error.select_list')",
    r'"Zaznacz listę do usunięcia"': "t('tasks.error.select_list_delete')",
    r'"Nie znaleziono kolumny"': "t('tasks.error.column_not_found')",
    r'"Nie znaleziono tagu"': "t('tasks.error.tag_not_found')",
    r'"Nie znaleziono listy"': "t('tasks.error.list_not_found')",
    r'"Brak zaznaczenia"': "t('tasks.error.no_selection')",
    r'"Nie można usunąć kolumny systemowej"': "t('tasks.error.cannot_delete_system')",
    r'"Dodaj przynajmniej jedną wartość do listy"': "t('tasks.error.list_needs_values')",
    r'"Lista musi zawierać przynajmniej jedną wartość"': "t('tasks.error.list_must_have_values')",
    
    # Potwierdzenia
    r'"Potwierdzenie usunięcia"': "t('tasks.confirm.delete_column')",
    
    # Sukces
    r'"Sukces"': "t('tasks.error.no_selection')",  # używamy jako tytuł dialogu
}

def main():
    filepath = "src/ui/task_config_dialog.py"
    
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Zastosuj zamiany
    for pattern, replacement in REPLACEMENTS.items():
        content = re.sub(pattern, replacement, content)
    
    with open(filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print("Aktualizacja zakończona!")

if __name__ == "__main__":
    main()
