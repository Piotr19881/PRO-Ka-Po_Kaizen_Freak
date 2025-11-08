# Instrukcja testowania dialogu TextInputDialog

## Krok 1: Sprawdź czy kolumna 'tekstowa' istnieje
python verify_text_columns.py

## Krok 2: Uruchom aplikację
python PRO-Ka-Po_Kaizen_Freak/main.py

## Krok 3: W aplikacji
1. Przejdź do widoku Zadania
2. Znajdź kolumnę "tekstowa" (powinna być widoczna w tabeli)
3. Kliknij dwukrotnie na dowolną komórkę w kolumnie "tekstowa"
4. Powinien otworzyć się dialog TextInputDialog z wieloliniowym polem tekstowym

## Krok 4: Sprawdź logi
W konsoli powinien pojawić się log:
[TaskView] Opening text dialog for column: tekstowa

## Co zostało naprawione:
✅ Metoda _is_text_column() teraz:
   - Wykrywa typ 'tekstowa' (oraz 'text', 'tekst', 'string', 'str')
   - Pomija kolumny systemowe (is_system=1) jak 'Tag' i 'Zadanie'
   - Sprawdza czy kolumna jest edytowalna (editable=1)

✅ Dialog używa QTextEdit:
   - Wieloliniowe pole tekstowe
   - Własny suwak
   - Szerokość: 400px
   - Wysokość: 150-300px

✅ Pełna integracja:
   - Theme Manager (dynamiczne kolory)
   - i18n (tłumaczenia PL/EN/DE)
   - Zapis do bazy (custom_data JSON)
