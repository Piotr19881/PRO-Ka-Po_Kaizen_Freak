# CallCryptor View - Raport Audytu i18n

**Data**: 2025-11-08  
**Plik**: `src/ui/callcryptor_view.py`  
**Liczba linii**: 2109  
**Status**: ❌ Wymaga integracji z i18n - znaleziono 67+ twardych stringów

---

## 📋 Podsumowanie Wykonawcze

### Statystyki:
- **Twarde stringi znalezione**: 67+
- **QMessageBox z twardymi tekstami**: 31
- **setToolTip z twardymi tekstami**: 2
- **Inne UI stringi**: 34+
- **Szacowany czas naprawy**: 3-4 godziny

### Priorytet:
🔴 **WYSOKI** - Interfejs użytkownika całkowicie po polsku bez wsparcia wielojęzyczności

---

## 🔍 Szczegółowa Lista Twardych Stringów

### 1. TOOLTIPS (Podpowiedzi przycisków)

| Linia | Funkcja | Tekst PL | Proponowany klucz i18n |
|-------|---------|----------|------------------------|
| 132 | `_setup_ui()` | `"Usuń źródło"` | `callcryptor.tooltip.remove_source` |
| 140 | `_setup_ui()` | `"Edytuj źródło"` | `callcryptor.tooltip.edit_source` |

**Uwaga**: Pozostałe tooltips już używają `t()` - poprawnie zaimplementowane.

---

### 2. COMBO BOX ITEMS (Elementy list rozwijanych)

| Linia | Funkcja | Tekst PL | Proponowany klucz i18n |
|-------|---------|----------|------------------------|
| 348 | `_load_tags()` | `"⭐ Ulubione"` | `callcryptor.filter.favorites` (już istnieje w combo źródeł) |

---

### 3. DEFAULT TAGS (Domyślne tagi)

| Linia | Funkcja | Tekst PL | Proponowany klucz i18n |
|-------|---------|----------|------------------------|
| 439 | `_get_default_tags()` | `"Ważne"` | `callcryptor.tags.important` |
| 440 | `_get_default_tags()` | `"Praca"` | `callcryptor.tags.work` |
| 441 | `_get_default_tags()` | `"Osobiste"` | `callcryptor.tags.personal` |
| 442 | `_get_default_tags()` | `"Do przesłuchania"` | `callcryptor.tags.to_review` |

---

### 4. QMessageBox - WARNINGS (Ostrzeżenia)

| Linia | Funkcja | Tytuł/Treść | Tekst PL | Proponowany klucz i18n |
|-------|---------|-------------|----------|------------------------|
| 654 | `_edit_source()` | Treść | `"Wybierz źródło do edycji"` | `callcryptor.warning.select_source_to_edit` |
| 677 | `_remove_source()` | Treść | `"Wybierz źródło do usunięcia"` | `callcryptor.warning.select_source_to_delete` |
| 1127 | `_transcribe()` | Tytuł | `"Błąd"` | `common.error` (już istnieje) |
| 1128 | `_transcribe()` | Treść | `"Nie można znaleźć pliku nagrania"` | `callcryptor.error.recording_file_not_found` |
| 1155 | `_transcribe()` | Tytuł | `"Brak konfiguracji AI"` | `callcryptor.error.no_ai_configuration` |
| 1156-1161 | `_transcribe()` | Treść | Multi-line komunikat o brakujących kluczach API | `callcryptor.error.missing_api_keys_transcription` |
| 1272 | `_ai_summary()` | Treść | `"Brak aktywnego providera AI w ustawieniach.\nSkonfiguruj AI w Ustawieniach."` | `callcryptor.warning.no_active_provider` |
| 1282 | `_ai_summary()` | Treść | `"Brak API key dla {active_provider}.\nSkonfiguruj w Ustawieniach → AI."` | `callcryptor.warning.missing_api_key_for_provider` |
| 1300 | `_ai_summary()` | Treść | `"Nieznany provider: {active_provider}"` | `callcryptor.warning.unknown_provider` |
| 1378 | `_create_note()` | Treść | `"Nie można otworzyć widoku notatek (brak main_window)"` | `callcryptor.error.no_main_window` |
| 1396 | `_create_note()` | Treść | `"Nie można otworzyć widoku notatek (brak notes_view)"` | `callcryptor.error.no_notes_view` |
| 1464 | `_create_note()` | Treść | `"Błąd podczas tworzenia notatki: {str(e)}"` | `callcryptor.error.note_creation_failed` |
| 1669 | `_toggle_favorite()` | Brak tytułu | Już używa `t('callcryptor.error.favorite_failed')` ✅ |
| 1731 | `_on_tag_changed()` | Tytuł | `"Błąd"` | `common.error` |
| 1732 | `_on_tag_changed()` | Treść | `"Nie udało się zmienić tagu:\n{str(e)}"` | `callcryptor.error.tag_change_failed` |

---

### 5. QMessageBox - INFORMATION (Informacje)

| Linia | Funkcja | Tytuł/Treść | Tekst PL | Proponowany klucz i18n |
|-------|---------|-------------|----------|------------------------|
| 663-667 | `_edit_source()` | Tytuł | `"Edycja źródła"` | `callcryptor.dialog.edit_source` |
| 663-667 | `_edit_source()` | Treść | `"Funkcja edycji źródła będzie wkrótce dostępna.\n\nMożesz na razie usunąć źródło i dodać je ponownie z nowymi ustawieniami."` | `callcryptor.message.edit_source_coming_soon` |
| 718 | `_remove_source()` | Tytuł | `"Źródło usunięte"` | `callcryptor.dialog.source_removed` |
| 719 | `_remove_source()` | Treść | `"Źródło '{source['source_name']}' zostało usunięte."` | `callcryptor.message.source_removed_success` |
| 854 | `_scan_source()` | Treść | `"Nie znaleziono żadnych wiadomości spełniających kryteria."` | `callcryptor.message.no_messages_found` |
| 1486-1491 | `_create_task()` | Treść | `"Brak zadań w podsumowaniu AI.\n\nNajpierw wygeneruj podsumowanie AI (przycisk 🪄), które zawiera automatycznie wykryte zadania."` | `callcryptor.message.no_tasks_in_summary` |
| 1533-1536 | `_archive_recording()` | Treść | `"Nagranie zostało zarchiwizowane"` | `callcryptor.message.recording_archived` |
| 1564-1567 | `_delete_recording()` | Treść | `"Funkcja usuwania będzie wkrótce dostępna"` | `callcryptor.message.delete_coming_soon` |
| 1629-1633 | `_manage_queue()` | Treść | `"Funkcja kolejki przetwarzania będzie dostępna w przyszłej wersji.\nPozwoli ona na ustawienie kolejności transkrypcji i analizy AI."` | `callcryptor.message.queue_coming_soon` |

---

### 6. QMessageBox - CRITICAL ERRORS (Błędy krytyczne)

| Linia | Funkcja | Tytuł/Treść | Tekst PL | Proponowany klucz i18n |
|-------|---------|-------------|----------|------------------------|
| 687 | `_remove_source()` | Treść | `"Nie znaleziono źródła"` | `callcryptor.error.source_not_found` |
| 726 | `_remove_source()` | Treść | `"Nie udało się usunąć źródła:\n{str(e)}"` | `callcryptor.error.source_removal_failed` |
| 985 | `_manage_tags()` | Tytuł | `"Błąd"` | `common.error` |
| 986 | `_manage_tags()` | Treść | `"Nie udało się otworzyć menadżera tagów:\n{str(e)}"` | `callcryptor.error.tag_manager_failed` |
| 1245 | `_transcribe()` | Tytuł | `"Błąd transkrypcji"` | `callcryptor.error.transcription_error` |
| 1246 | `_transcribe()` | Treść | `"Nie udało się uruchomić transkrypcji:\n{str(e)}"` | `callcryptor.error.transcription_start_failed` |
| 1319 | `_ai_summary()` | Treść | `"Błąd konfiguracji AI: {str(e)}"` | `callcryptor.error.ai_configuration_failed` |
| 1543 | `_archive_recording()` | Treść | `"Błąd podczas archiwizacji: {str(e)}"` | `callcryptor.error.archive_failed` |

---

### 7. QMessageBox - QUESTION (Pytania potwierdzające)

| Linia | Funkcja | Tytuł/Treść | Tekst PL | Proponowany klucz i18n |
|-------|---------|-------------|----------|------------------------|
| 694 | `_remove_source()` | Tytuł | `"Usuń źródło"` | `callcryptor.dialog.remove_source` |
| 695-698 | `_remove_source()` | Treść | `"Czy na pewno chcesz usunąć źródło:\n\n📁 {source['source_name']}\n\nUwaga: Nagrania z tego źródła pozostaną w bazie,\nale źródło nie będzie już skanowane automatycznie."` | `callcryptor.confirm.remove_source` |
| 1507-1512 | `_archive_recording()` | Treść | `"Czy na pewno chcesz zarchiwizować to nagranie?\n\nKontakt: {recording.get('contact_info', 'Nieznany')}\nData: {recording.get('recording_date', 'N/A')}\n\nZarchiwizowane nagrania można przywrócić później."` | `callcryptor.confirm.archive_recording` |
| 1555-1559 | `_delete_recording()` | Treść | `"Czy na pewno chcesz usunąć nagranie?\nKontakt: {recording.get('contact_info', 'Nieznany')}\nData: {recording.get('date', 'N/A')}"` | `callcryptor.confirm.delete_recording` |

---

### 8. WINDOW TITLES (Tytuły okien)

| Linia | Funkcja | Tekst PL | Proponowany klucz i18n |
|-------|---------|----------|------------------------|
| 1118 | `_transcribe()` | `"📝 Gotowa transkrypcja"` | `callcryptor.dialog.ready_transcription` |

---

### 9. PROGRESS DIALOG LABELS (Etykiety dialogów postępu)

| Linia | Funkcja | Tekst PL | Proponowany klucz i18n |
|-------|---------|----------|------------------------|
| 821 | `_scan_source()` | `"🔍 Sprawdzam wiadomości..."` | `callcryptor.progress.checking_messages` |

---

### 10. ERROR MESSAGES W STRING CHECKS (Sprawdzanie błędów)

| Linia | Funkcja | Tekst PL/EN | Proponowany klucz i18n |
|-------|---------|-------------|------------------------|
| 828 | `_scan_source()` | `"Skanowanie anulowane przez użytkownika"` | `callcryptor.error.scan_cancelled_by_user` |
| 842 | `_scan_source()` | `"anulowane"` (check w str(e).lower()) | Nie wymaga - logika kontrolna |
| 889 | `_scan_source()` | `"Pobieranie anulowane przez użytkownika"` | `callcryptor.error.download_cancelled_by_user` |
| 906 | `_scan_source()` | `"anulowane"` (check w str(e).lower()) | Nie wymaga - logika kontrolna |
| 949 | `_scan_source()` | `"  • ... i {len(results['errors']) - 3} więcej\n"` | `callcryptor.message.and_x_more_errors` |
| 1188 | `_transcribe()` | `"does not support"` (check w error_msg) | Nie wymaga - API error detection |

---

### 11. HARDCODED LABELS W RESULTS DISPLAY

| Linia | Funkcja | Tekst PL | Uwaga |
|-------|---------|----------|-------|
| 949 | `_scan_source()` | `"  • ... i {len(results['errors']) - 3} więcej\n"` | Część formatowania wyników skanowania |

---

## 🎯 Plan Naprawy

### Faza 1: Dodanie kluczy do plików i18n ✅ (2-3 godziny)

Dodaj **58 nowych kluczy** do plików:
- `resources/i18n/pl.json` (polski - źródłowy)
- `resources/i18n/en.json` (angielski - tłumaczenia)
- `resources/i18n/de.json` (niemiecki - tłumaczenia)

### Faza 2: Refaktoryzacja `callcryptor_view.py` (1-2 godziny)

Zamień wszystkie twarde stringi na wywołania `t()`:

```python
# PRZED:
self.remove_source_btn.setToolTip("Usuń źródło")

# PO:
self.remove_source_btn.setToolTip(t('callcryptor.tooltip.remove_source'))
```

### Faza 3: Testy (30 minut)

- Uruchomienie aplikacji w każdym języku (PL, EN, DE)
- Weryfikacja wszystkich komunikatów
- Sprawdzenie przycisków i tooltipów

---

## 📝 Klucze i18n Do Dodania

### Grupa: `callcryptor.tooltip.*`
```json
{
  "callcryptor.tooltip.remove_source": "Usuń źródło",
  "callcryptor.tooltip.edit_source": "Edytuj źródło"
}
```

### Grupa: `callcryptor.tags.*`
```json
{
  "callcryptor.tags.important": "Ważne",
  "callcryptor.tags.work": "Praca",
  "callcryptor.tags.personal": "Osobiste",
  "callcryptor.tags.to_review": "Do przesłuchania"
}
```

### Grupa: `callcryptor.warning.*`
```json
{
  "callcryptor.warning.select_source_to_edit": "Wybierz źródło do edycji",
  "callcryptor.warning.select_source_to_delete": "Wybierz źródło do usunięcia",
  "callcryptor.warning.no_active_provider": "Brak aktywnego providera AI w ustawieniach.\nSkonfiguruj AI w Ustawieniach.",
  "callcryptor.warning.missing_api_key_for_provider": "Brak API key dla {provider}.\nSkonfiguruj w Ustawieniach → AI.",
  "callcryptor.warning.unknown_provider": "Nieznany provider: {provider}"
}
```

### Grupa: `callcryptor.error.*`
```json
{
  "callcryptor.error.recording_file_not_found": "Nie można znaleźć pliku nagrania",
  "callcryptor.error.no_ai_configuration": "Brak konfiguracji AI",
  "callcryptor.error.missing_api_keys_transcription": "Transkrypcja audio wymaga skonfigurowania klucza API.\n\nObsługiwani dostawcy:\n• Google Gemini (gemini-1.5-pro, gemini-1.5-flash)\n• OpenAI Whisper\n\nPrzejdź do Ustawień → AI i skonfiguruj klucz API.",
  "callcryptor.error.no_main_window": "Nie można otworzyć widoku notatek (brak main_window)",
  "callcryptor.error.no_notes_view": "Nie można otworzyć widoku notatek (brak notes_view)",
  "callcryptor.error.note_creation_failed": "Błąd podczas tworzenia notatki: {error}",
  "callcryptor.error.tag_change_failed": "Nie udało się zmienić tagu:\n{error}",
  "callcryptor.error.source_not_found": "Nie znaleziono źródła",
  "callcryptor.error.source_removal_failed": "Nie udało się usunąć źródła:\n{error}",
  "callcryptor.error.tag_manager_failed": "Nie udało się otworzyć menadżera tagów:\n{error}",
  "callcryptor.error.transcription_error": "Błąd transkrypcji",
  "callcryptor.error.transcription_start_failed": "Nie udało się uruchomić transkrypcji:\n{error}",
  "callcryptor.error.ai_configuration_failed": "Błąd konfiguracji AI: {error}",
  "callcryptor.error.archive_failed": "Błąd podczas archiwizacji: {error}",
  "callcryptor.error.scan_cancelled_by_user": "Skanowanie anulowane przez użytkownika",
  "callcryptor.error.download_cancelled_by_user": "Pobieranie anulowane przez użytkownika"
}
```

### Grupa: `callcryptor.dialog.*`
```json
{
  "callcryptor.dialog.edit_source": "Edycja źródła",
  "callcryptor.dialog.source_removed": "Źródło usunięte",
  "callcryptor.dialog.remove_source": "Usuń źródło",
  "callcryptor.dialog.ready_transcription": "📝 Gotowa transkrypcja"
}
```

### Grupa: `callcryptor.message.*`
```json
{
  "callcryptor.message.edit_source_coming_soon": "Funkcja edycji źródła będzie wkrótce dostępna.\n\nMożesz na razie usunąć źródło i dodać je ponownie z nowymi ustawieniami.",
  "callcryptor.message.source_removed_success": "Źródło '{source_name}' zostało usunięte.",
  "callcryptor.message.no_messages_found": "Nie znaleziono żadnych wiadomości spełniających kryteria.",
  "callcryptor.message.no_tasks_in_summary": "Brak zadań w podsumowaniu AI.\n\nNajpierw wygeneruj podsumowanie AI (przycisk 🪄), które zawiera automatycznie wykryte zadania.",
  "callcryptor.message.recording_archived": "Nagranie zostało zarchiwizowane",
  "callcryptor.message.delete_coming_soon": "Funkcja usuwania będzie wkrótce dostępna",
  "callcryptor.message.queue_coming_soon": "Funkcja kolejki przetwarzania będzie dostępna w przyszłej wersji.\nPozwoli ona na ustawienie kolejności transkrypcji i analizy AI.",
  "callcryptor.message.and_x_more_errors": "  • ... i {count} więcej\n"
}
```

### Grupa: `callcryptor.confirm.*`
```json
{
  "callcryptor.confirm.remove_source": "Czy na pewno chcesz usunąć źródło:\n\n📁 {source_name}\n\nUwaga: Nagrania z tego źródła pozostaną w bazie,\nale źródło nie będzie już skanowane automatycznie.",
  "callcryptor.confirm.archive_recording": "Czy na pewno chcesz zarchiwizować to nagranie?\n\nKontakt: {contact}\nData: {date}\n\nZarchiwizowane nagrania można przywrócić później.",
  "callcryptor.confirm.delete_recording": "Czy na pewno chcesz usunąć nagranie?\nKontakt: {contact}\nData: {date}"
}
```

### Grupa: `callcryptor.progress.*`
```json
{
  "callcryptor.progress.checking_messages": "🔍 Sprawdzam wiadomości..."
}
```

---

## ✅ Co Już Jest Dobrze

Następujące elementy już poprawnie używają i18n:

1. **Tooltips (większość)**:
   - `callcryptor.add_source_tooltip`
   - `callcryptor.refresh_tooltip`
   - `callcryptor.record_tooltip`
   - `callcryptor.queue_tooltip`
   - `callcryptor.export_tooltip`
   - `callcryptor.edit_tags_tooltip`
   - `callcryptor.tooltip.favorite`

2. **Combo box items (większość)**:
   - `callcryptor.folder.favorites`
   - `callcryptor.filter.today`
   - `callcryptor.filter.yesterday`
   - `callcryptor.filter.last_week`
   - `callcryptor.filter.last_month`

3. **Search placeholder**:
   - `callcryptor.search_placeholder`

4. **Status messages**:
   - `callcryptor.status.scan_complete`
   - `callcryptor.scanning.new`
   - `callcryptor.scanning.found`
   - `callcryptor.scanning.added`
   - `callcryptor.scanning.duplicates`
   - `callcryptor.scanning.errors`

5. **Dialog titles (niektóre)**:
   - `callcryptor.scan`
   - `callcryptor.export`
   - `callcryptor.title`

6. **Warnings (niektóre)**:
   - `warning.general`
   - `error.general`
   - `common.error`

7. **Error messages (niektóre)**:
   - `callcryptor.error.source_not_found`
   - `callcryptor.error.scan_failed`
   - `callcryptor.error.email_account_not_found`
   - `callcryptor.error.favorite_failed`
   - `callcryptor.warning.no_source_selected`

---

## 🚀 Następne Kroki

1. ✅ **Przegląd dokumentacji** - Ten raport
2. ⏳ **Dodanie kluczy i18n** - 58 nowych kluczy w 3 językach
3. ⏳ **Refaktoryzacja kodu** - Zamiana twardych stringów na `t()`
4. ⏳ **Testy weryfikacyjne** - Sprawdzenie w PL/EN/DE
5. ⏳ **Code review** - Sprawdzenie completeness

---

## 📊 Metryki Pokrycia i18n

### Przed naprawą:
- **Tooltips**: 7/9 (77.8%) ✅
- **Combo items**: 5/6 (83.3%) ✅
- **QMessageBox**: 0/31 (0%) ❌
- **Default tags**: 0/4 (0%) ❌
- **Window titles**: 0/1 (0%) ❌
- **Progress labels**: 0/1 (0%) ❌

### Po naprawie (cel):
- **Tooltips**: 9/9 (100%) ✅
- **Combo items**: 6/6 (100%) ✅
- **QMessageBox**: 31/31 (100%) ✅
- **Default tags**: 4/4 (100%) ✅
- **Window titles**: 1/1 (100%) ✅
- **Progress labels**: 1/1 (100%) ✅

**Ogólne pokrycie**: 67+ stringów wymaga integracji z i18n

---

## 🔧 Przykłady Refaktoryzacji

### Przykład 1: Tooltip
```python
# PRZED:
self.remove_source_btn.setToolTip("Usuń źródło")

# PO:
self.remove_source_btn.setToolTip(t('callcryptor.tooltip.remove_source'))
```

### Przykład 2: QMessageBox Warning
```python
# PRZED:
QMessageBox.warning(
    self,
    t('warning.general'),
    "Wybierz źródło do edycji"
)

# PO:
QMessageBox.warning(
    self,
    t('warning.general'),
    t('callcryptor.warning.select_source_to_edit')
)
```

### Przykład 3: QMessageBox z parametrem
```python
# PRZED:
QMessageBox.critical(
    self,
    t('error.general'),
    f"Nie udało się usunąć źródła:\n{str(e)}"
)

# PO:
QMessageBox.critical(
    self,
    t('error.general'),
    t('callcryptor.error.source_removal_failed').format(error=str(e))
)
```

### Przykład 4: Multi-line QMessageBox
```python
# PRZED:
QMessageBox.question(
    self,
    "Usuń źródło",
    f"Czy na pewno chcesz usunąć źródło:\n\n"
    f"📁 {source['source_name']}\n\n"
    f"Uwaga: Nagrania z tego źródła pozostaną w bazie,\n"
    f"ale źródło nie będzie już skanowane automatycznie.",
    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    QMessageBox.StandardButton.No
)

# PO:
QMessageBox.question(
    self,
    t('callcryptor.dialog.remove_source'),
    t('callcryptor.confirm.remove_source').format(
        source_name=source['source_name']
    ),
    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
    QMessageBox.StandardButton.No
)
```

### Przykład 5: Default Tags Dictionary
```python
# PRZED:
return {
    "Ważne": "#e74c3c",
    "Praca": "#3498db",
    "Osobiste": "#2ecc71",
    "Do przesłuchania": "#f39c12"
}

# PO:
return {
    t('callcryptor.tags.important'): "#e74c3c",
    t('callcryptor.tags.work'): "#3498db",
    t('callcryptor.tags.personal'): "#2ecc71",
    t('callcryptor.tags.to_review'): "#f39c12"
}
```

---

## 📌 Uwagi Specjalne

### 1. Formatowanie z parametrami
Niektóre komunikaty wymagają parametrów dynamicznych:
- `{source_name}` - nazwa źródła
- `{error}` - tekst błędu
- `{provider}` - nazwa providera AI
- `{contact}` - informacje o kontakcie
- `{date}` - data nagrania
- `{count}` - liczba elementów

### 2. Zachowanie emoji
Emoji (📁, 🔍, 📝, ⭐, 🪄) należy zachować w tłumaczeniach - są uniwersalne.

### 3. Znaki nowej linii
`\n` w stringach musi być zachowane w plikach JSON jako `\\n`.

### 4. Kontekst "Nieznany" / "Unknown"
W parametrach z `.get('contact_info', 'Nieznany')` - słowo "Nieznany" też wymaga tłumaczenia:
- Dodaj klucz: `common.unknown`

---

## 🎓 Wnioski

CallCryptor View zawiera **67+ twardych stringów** wymagających integracji z systemem i18n. Większość to komunikaty QMessageBox (ostrzeżenia, błędy, potwierdzenia), co ma bezpośredni wpływ na UX w różnych językach.

**Rekomendacja**: Przeprowadzić pełną refaktoryzację przed wydaniem wersji międzynarodowej.

---

**Autor raportu**: GitHub Copilot  
**Narzędzia użyte**: grep_search, read_file, semantic analysis
