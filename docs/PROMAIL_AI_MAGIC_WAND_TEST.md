# 🪄 Test Magicznej Różdżki AI w ProMail

## Zakończone implementacje (4/5 zadań - 80%)

### ✅ Zadanie 1: Konektor AI
**Plik:** `src/Modules/AI_module/promail_ai_connector.py`
- Singleton pattern - jeden connector dla całej aplikacji
- Obsługa źródeł prawdy (PDF, TXT, CSV, JSON)
- Generowanie odpowiedzi z kontekstem
- Thread-safe operations

### ✅ Zadanie 2: Dialog źródeł prawdy
**Plik:** `src/Modules/custom_modules/mail_client/truth_sources_dialog.py`
- Hierarchiczna struktura folderów/plików
- System checkboxów (folder → wszystkie pliki)
- CRUD operations (dodaj/usuń/zarządzaj)
- Zapis do JSON: `mail_client/ai_truth_sources.json`

### ✅ Zadanie 3: Dialog komunikacji AI
**Plik:** `src/Modules/custom_modules/mail_client/ai_quick_response_dialog.py`
- Wyświetlanie treści emaila (readonly)
- Edytowalny prompt bazowy i dodatkowy
- Drzewo źródeł prawdy z checkboxami
- **Checkbox załączania wątku konwersacji**
- **Progress bar 0→100%**
- **Auto-zamykanie po wygenerowaniu**
- **Sygnał `response_generated(str, dict)`**

### ✅ Zadanie 4: Integracja przycisku 🪄
**Pliki:**
- `src/Modules/custom_modules/mail_client/mail_view.py`
- `src/Modules/custom_modules/mail_client/new_mail_window.py`

**Zmiany w mail_view.py:**
- Kolumna 11 (🪄) już istniała w tabeli
- Linie 3834-3881: Obsługa `logical_col_idx == 11` w `on_mail_clicked()`
- Linie 4263-4350: Metoda `open_ai_quick_response(mail, row)`:
  * Ekstrahuje kontekst emaila
  * Pobiera wątek z `mail_threads` jeśli istnieje
  * Tworzy `AIQuickResponseDialog`
  * Łączy sygnał `response_generated`
- Linie 4352-4387: Metoda `on_ai_response_generated(response, reply_context)`:
  * Odbiera odpowiedź AI
  * Otwiera `NewMailWindow` z `reply_to` i `initial_body`
  * Użytkownik może edytować i wysłać

**Zmiany w new_mail_window.py:**
- Konstruktor: Dodano parametr `initial_body=None`
- `setup_reply()`: Priorytet `initial_body` nad cytowaniem oryginalnej wiadomości

---

## 🧪 Instrukcja testowania

### Krok 1: Uruchom aplikację
```powershell
cd "c:\Users\probu\Desktop\Aplikacje komercyjne\PRO-Ka-Po_Kaizen_Freak\PRO-Ka-Po_Kaizen_Freak"
python main.py
```

### Krok 2: Otwórz moduł ProMail
1. W głównym oknie aplikacji wybierz moduł **ProMail**
2. Poczekaj na załadowanie listy maili (lub kliknij 🔄 Odśwież)

### Krok 3: Sprawdź kolumnę 🪄
1. W tabeli maili powinna być widoczna kolumna **🪄** (ostatnia kolumna)
2. Tooltip: "Generuj szybką odpowiedź AI"

### Krok 4: Kliknij magiczną różdżkę
1. Wybierz dowolną wiadomość z listy
2. Kliknij ikonę 🪄 w tej samej linii
3. **Oczekiwany rezultat:** Otwiera się dialog "Szybka odpowiedź AI"

### Krok 5: Sprawdź dialog AI
**Elementy do weryfikacji:**

✅ **Treść emaila (górna sekcja):**
- Readonly QTextEdit z treścią emaila
- Metadata: From, To, Subject, Date

✅ **Prompt bazowy (środkowa sekcja):**
- Edytowalny QTextEdit z domyślnym promptem
- Placeholder: "Wpisz bazowy prompt dla AI..."

✅ **Dodatkowy prompt (opcjonalny):**
- Edytowalny QTextEdit
- Placeholder: "Dodatkowe instrukcje dla AI..."

✅ **Źródła prawdy:**
- Drzewo z plikami/folderami
- Checkboxy do wyboru
- Przycisk "Edytuj źródła prawdy..." otwiera `TruthSourcesDialog`

✅ **Checkbox wątku:**
- "Załącz całą konwersację z wątku"
- Gdy zaznaczone → AI otrzymuje historię emaili

✅ **Progress bar:**
- Niewidoczny na początku
- Po kliknięciu "Generuj" pojawia się 0%
- Aktualizuje się: 10% → 20% → 40% → 60% → 100%

### Krok 6: Wygeneruj odpowiedź
1. (Opcjonalnie) Zaznacz checkbox "Załącz całą konwersację"
2. (Opcjonalnie) Edytuj prompty
3. (Opcjonalnie) Wybierz źródła prawdy
4. Kliknij **"Generuj"**

**Oczekiwane zachowanie:**
1. Progress bar pojawia się i aktualizuje
2. Po zakończeniu dialog **automatycznie się zamyka**
3. **Otwiera się okno "Odpowiedz"** (`NewMailWindow`)

### Krok 7: Sprawdź okno odpowiedzi
**Weryfikacja NewMailWindow:**

✅ **Pole "Do":**
- Automatycznie wypełnione adresem nadawcy

✅ **Pole "Temat":**
- Automatycznie "Re: [oryginalny temat]"

✅ **Treść wiadomości:**
- Zawiera **wygenerowaną przez AI odpowiedź**
- NIE zawiera cytowania oryginalnej wiadomości
- Kursor na początku tekstu

✅ **Edycja:**
- Użytkownik może edytować wygenerowany tekst
- Może dodać/usunąć fragmenty
- Może wysłać lub anulować

### Krok 8: Wyślij/Anuluj
- Kliknij **"Wyślij"** → mail trafia do kolejki
- Kliknij **"Anuluj"** → szkic zapisany (jeśli włączone autosave)

---

## 🐛 Co sprawdzić w przypadku błędów

### Problem: Dialog AI się nie otwiera
**Diagnostyka:**
```python
# W mail_view.py sprawdź logi:
logger.error(f"[ProMail] Failed to open AI Quick Response: {e}")
```
**Możliwe przyczyny:**
- Import `AIQuickResponseDialog` nie działa
- Brak modułu `src/Modules/AI_module/promail_ai_connector.py`

### Problem: Progress bar nie działa
**Sprawdź:**
- `AIGenerationThread` w `ai_quick_response_dialog.py`
- Sygnał `progress` (linie 75-125)

### Problem: Okno odpowiedzi nie otwiera się
**Diagnostyka:**
```python
# W mail_view.py → on_ai_response_generated()
logger.error(f"[ProMail] Failed to open reply window: {e}")
```
**Możliwe przyczyny:**
- `NewMailWindow` nie ma parametru `initial_body` (NAPRAWIONE)
- Sygnał `response_generated` nie jest połączony

### Problem: Treść AI nie pojawia się w oknie
**Sprawdź:**
- `new_mail_window.py` → `setup_reply()` (linia 835+)
- Czy `self.initial_body` jest przekazywane?
- Czy `body_field.setPlainText(self.initial_body)` jest wywołane?

---

## 📊 Status projektu

**Zakończone: 4/5 zadań (80%)**

✅ ProMail AI Connector  
✅ Truth Sources Dialog  
✅ AI Quick Response Dialog  
✅ Magic Wand Integration  
⏳ **Pozostaje:** Integracja źródeł prawdy w `new_mail_window.py`

---

## 🔄 Następne kroki

### Zadanie 5: Integracja z new_mail_window.py
**Cel:** Zastąpić stary `TruthSourcesManager` UI nowym `TruthSourcesDialog`

**Pliki do modyfikacji:**
- `src/Modules/custom_modules/mail_client/new_mail_window.py`

**Wymagane zmiany:**
1. Import `TruthSourcesDialog` z `truth_sources_dialog.py`
2. Znaleźć istniejące UI do zarządzania źródłami prawdy
3. Zastąpić stare UI przyciskiem otwierającym nowy dialog
4. Połączyć sygnał `sources_updated` z refreshem listy
5. Integrować wybrane źródła z panelem AI w oknie kompozycji

**Szacowany czas:** 1-2 godziny

---

## 📝 Notatki techniczne

### Architektura sygnałów
```
MailView (🪄 click)
    ↓
open_ai_quick_response()
    ↓
AIQuickResponseDialog
    ↓ (sygnał: response_generated)
on_ai_response_generated(response, reply_context)
    ↓
NewMailWindow(reply_to=X, initial_body=response)
```

### Format thread_emails
```python
thread_emails = [
    {
        "from": "jan@example.com",
        "to": "anna@example.com",
        "subject": "Re: Projekt",
        "date": "2024-01-15 10:30",
        "content": "Treść emaila..."
    },
    # ... kolejne maile w wątku
]
```

### Zależności
- `ProMailAIConnector` ← singleton z `AI_module`
- `get_thread_id()` ← metoda w `mail_view.py` (linia 2831)
- `mail_threads` ← dict w `mail_view.py` (populated przez `group_mails_into_threads()`)

---

Data utworzenia: 2025-01-11
Wersja dokumentu: 1.0
Status: Ready for testing ✅
