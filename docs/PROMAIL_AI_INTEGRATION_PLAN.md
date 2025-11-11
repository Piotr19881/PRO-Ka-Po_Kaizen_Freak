# Plan Integracji AI z Modułem ProMail

## Data utworzenia: 2025-11-11
## Data aktualizacji: 2025-11-11 (uproszczenie funkcjonalności)

## 1. Analiza Obecnego Stanu

### 1.1 Zidentyfikowane Elementy ProMail
- **Kolumna 🪄 (Magiczna różdżka)**: Dodana w kolumnie 11, ale brak implementacji funkcjonalności
- **Moduł AI_module**: Istniejący w `src/Modules/AI_module/` z wsparciem dla wielu providerów LLM (skonfigurowany przez użytkownika)
- **Brak integracji**: Obecnie kolumna 🪄 jest tylko wizualna, bez obsługi kliknięć

### 1.2 Lokalizacje w Kodzie
```
Plik: src/Modules/custom_modules/mail_client/mail_view.py
- Linia 248: column_visibility[11] = True  # 🪄
- Linia 262: column_names[11] = "🪄 Magiczna różdżka"
- Linia 2466-2470: Dodawanie ikony 🪄 do tabeli (tylko wizualnie)

Istniejący moduł AI:
- src/Modules/AI_module/ - gotowy moduł komunikacji z LLM API
```

## 2. Uproszczona Funkcjonalność AI - Zakres Projektu

### 2.1 Główna Funkcja: Generowanie Odpowiedzi

#### **🪄 Magiczna Różdżka - Generowanie Odpowiedzi**
- **Funkcja**: Kliknięcie 🪄 wysyła cały wątek mailowy do AI i generuje inteligentną odpowiedź
- **Zachowanie**:
  1. Użytkownik klika 🪄 przy mailu
  2. System zbiera cały wątek konwersacji (wszystkie powiązane maile)
  3. Wysyła wątek do skonfigurowanego LLM przez istniejący AI_module
  4. Otrzymaną odpowiedź wstawia jako treść nowego maila
  5. Otwiera okno nowego maila z:
     - Wygenerowaną odpowiedzią na górze
     - Oryginalnym wątkiem poniżej (jako cytowanie)
     - Możliwością edycji przed wysłaniem

### 2.2 Konteksty Generowania

System obsługuje trzy rodzaje kontekstu dla AI:

#### A. **Treść pojedynczej wiadomości**
- Najszybsza opcja
- Używana gdy nie ma wątku lub użytkownik wybierze tę opcję
- Prompt: treść aktualnego maila

#### B. **Treść całego wątku**
- Domyślna opcja (🪄)
- Zbiera wszystkie maile w wątku (na podstawie In-Reply-To, References)
- Prompt: chronologiczny wątek konwersacji

#### C. **Treść wątku + źródła prawdy** (zaawansowane)
- Dostępne z panelu AI w oknie nowego maila
- Użytkownik może dołączyć dodatkowy kontekst:
  - Pliki tekstowe
  - Notatki z modułu Notes
  - Zadania z modułu Tasks
- Prompt: wątek + załączone dokumenty kontekstowe

### 2.3 Integracje z Innymi Modułami (tylko 2)

#### **Integracja z Tasks Module**
- Wykrywanie zadań w mailach
- Sugestia "Czy dodać jako zadanie?" po wygenerowaniu odpowiedzi
- Możliwość szybkiego utworzenia taska z treści maila

#### **Integracja z Notes Module**
- Generowanie notatek z wątków mailowych
- Opcja "Utwórz notatkę z wątku" w panelu AI
- Zapisanie streszczenia korespondencji jako notatka

### 2.4 Wyłączone Funkcje (poza zakresem)

❌ **Nie implementujemy:**
- Automatyczne tagowanie maili
- Analiza spamu/phishingu
- Analiza sentymentu
- Automatyczne tłumaczenia
- Ekstrakcja danych strukturalnych (poza zadaniami)
- Integracja z Pomodoro Module
- Cache wyników AI
- Statystyki użycia AI

## 3. Architektura Implementacji (Uproszczona)

### 3.1 Struktura Modułów

```
src/Modules/AI_module/
├── ai_logic.py              # Istniejący - komunikacja z LLM
├── ai_config.py             # Istniejący - konfiguracja providerów
└── mail_ai_handler.py       # NOWY - dedykowany moduł dla ProMail

src/Modules/custom_modules/mail_client/
├── mail_view.py             # Główny moduł (modyfikacje)
└── mail_compose.py          # Okno nowego maila (modyfikacje - panel AI)
```

### 3.2 Nowy Moduł: `src/Modules/AI_module/mail_ai_handler.py`

```python
"""
Dedykowany moduł obsługi AI dla ProMail
Wykorzystuje istniejący AI_module do komunikacji z LLM
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from .ai_logic import get_ai_manager


@dataclass
class MailThread:
    """Reprezentacja wątku mailowego"""
    emails: List[Dict[str, Any]]  # Lista maili w kolejności chronologicznej
    subject: str
    participants: List[str]


@dataclass
class AIReplyContext:
    """Kontekst dla generowania odpowiedzi"""
    thread: MailThread
    truth_sources: Optional[List[Dict[str, Any]]] = None  # Opcjonalne źródła prawdy
    user_instructions: Optional[str] = None  # Dodatkowe instrukcje użytkownika


class MailAIHandler:
    """
    Uproszczony handler AI dla maili
    Tylko generowanie odpowiedzi i notatek
    """
    
    def __init__(self):
        self.ai_manager = get_ai_manager()
    
    def generate_reply(
        self, 
        context: AIReplyContext,
        tone: str = "professional"
    ) -> str:
        """
        Generuje odpowiedź na wątek mailowy
        
        Args:
            context: Kontekst z wątkiem i opcjonalnymi źródłami prawdy
            tone: Ton odpowiedzi (professional/casual/friendly)
        
        Returns:
            Wygenerowana treść odpowiedzi
        """
        prompt = self._build_reply_prompt(context, tone)
        response = self.ai_manager.send_message(prompt)
        return response
    
    def generate_note_from_thread(
        self, 
        thread: MailThread,
        note_type: str = "summary"
    ) -> str:
        """
        Generuje notatkę z wątku mailowego
        
        Args:
            thread: Wątek mailowy
            note_type: Typ notatki (summary/action_items/key_points)
        
        Returns:
            Wygenerowana treść notatki
        """
        prompt = self._build_note_prompt(thread, note_type)
        response = self.ai_manager.send_message(prompt)
        return response
    
    def extract_tasks_from_thread(
        self, 
        thread: MailThread
    ) -> List[Dict[str, Any]]:
        """
        Wydobywa zadania z wątku mailowego
        
        Returns:
            Lista zadań: [{"title": "...", "description": "...", "deadline": "..."}, ...]
        """
        prompt = self._build_tasks_prompt(thread)
        response = self.ai_manager.send_message(prompt)
        return self._parse_tasks_response(response)
    
    def _build_reply_prompt(self, context: AIReplyContext, tone: str) -> str:
        """Buduje prompt dla generowania odpowiedzi"""
        thread_text = self._format_thread(context.thread)
        
        tone_instructions = {
            "professional": "w profesjonalnym, biznesowym tonie",
            "casual": "w swobodnym, casualowym tonie",
            "friendly": "w przyjaznym, ciepłym tonie"
        }
        
        prompt = f"""Na podstawie poniższego wątku mailowego, napisz odpowiedź {tone_instructions.get(tone, 'w profesjonalnym tonie')}.

WĄTEK MAILOWY:
{thread_text}
"""
        
        if context.truth_sources:
            sources_text = self._format_truth_sources(context.truth_sources)
            prompt += f"\n\nDODATKOWY KONTEKST (źródła prawdy):\n{sources_text}\n"
        
        if context.user_instructions:
            prompt += f"\n\nDODATKOWE INSTRUKCJE:\n{context.user_instructions}\n"
        
        prompt += """
WYMAGANIA:
- Odpowiedź po polsku
- Zwięzła i konkretna
- Odniesienie do kluczowych punktów z wątku
- Bez dodatkowych komentarzy - tylko treść odpowiedzi

ODPOWIEDŹ:
"""
        return prompt
    
    def _build_note_prompt(self, thread: MailThread, note_type: str) -> str:
        """Buduje prompt dla generowania notatki"""
        thread_text = self._format_thread(thread)
        
        note_instructions = {
            "summary": "Napisz zwięzłe streszczenie tej korespondencji",
            "action_items": "Wylistuj wszystkie zadania i action items z tej korespondencji",
            "key_points": "Wypisz najważniejsze punkty i decyzje z tej korespondencji"
        }
        
        instruction = note_instructions.get(note_type, note_instructions["summary"])
        
        prompt = f"""{instruction}:

{thread_text}

Notatka powinna być:
- Po polsku
- W formacie Markdown
- Czytelna i uporządkowana
- Zawierać kluczowe informacje

NOTATKA:
"""
        return prompt
    
    def _build_tasks_prompt(self, thread: MailThread) -> str:
        """Buduje prompt dla wydobycia zadań"""
        thread_text = self._format_thread(thread)
        
        prompt = f"""Przeanalizuj poniższy wątek mailowy i wydobądź z niego zadania do wykonania:

{thread_text}

Odpowiedz w formacie JSON (lista obiektów):
[
  {{
    "title": "Krótki tytuł zadania",
    "description": "Opis zadania",
    "deadline": "YYYY-MM-DD lub null"
  }}
]

Jeśli nie ma zadań, zwróć pustą listę [].

ZADANIA (JSON):
"""
        return prompt
    
    def _format_thread(self, thread: MailThread) -> str:
        """Formatuje wątek mailowy do tekstu"""
        lines = [f"TEMAT: {thread.subject}", ""]
        
        for i, email in enumerate(thread.emails, 1):
            lines.append(f"--- Mail #{i} ---")
            lines.append(f"OD: {email.get('from', 'Unknown')}")
            lines.append(f"DO: {email.get('to', 'Unknown')}")
            lines.append(f"DATA: {email.get('date', 'Unknown')}")
            lines.append("")
            lines.append(email.get('body', ''))
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_truth_sources(self, sources: List[Dict[str, Any]]) -> str:
        """Formatuje źródła prawdy"""
        lines = []
        for source in sources:
            lines.append(f"--- {source.get('type', 'Dokument')}: {source.get('title', 'Bez tytułu')} ---")
            lines.append(source.get('content', ''))
            lines.append("")
        return "\n".join(lines)
    
    def _parse_tasks_response(self, response: str) -> List[Dict[str, Any]]:
        """Parsuje odpowiedź AI z zadaniami"""
        import json
        import re
        
        # Znajdź JSON w odpowiedzi
        json_match = re.search(r'\[.*\]', response, re.DOTALL)
        if json_match:
            try:
                tasks = json.loads(json_match.group(0))
                return tasks if isinstance(tasks, list) else []
            except json.JSONDecodeError:
                return []
        return []
```



#### Obsługa kliknięcia 🪄:
```python
def on_mail_clicked(self, row, column):
    """Obsługa kliknięcia w mail"""
    # ... istniejący kod ...
    
    # Sprawdź czy kliknięto w emoji z akcją (kolumny 3, 4 lub 11)
    item = self.mail_list.item(row, column)
    if item and item.data(Qt.ItemDataRole.UserRole):
        action_data = item.data(Qt.ItemDataRole.UserRole)
        
        if action_data.get("action") == "reply":
            self.reply_to_mail(action_data["mail"])
            return
        elif action_data.get("action") == "expand":
            self.toggle_mail_preview(action_data["row"])
            return
        elif action_data.get("action") == "ai_magic":  # NOWE
            self.generate_ai_reply(action_data["mail"])
            return
```

#### Dodanie akcji do kolumny 🪄:
```python
elif col_idx == 11:  # 🪄 (Magiczna różdżka)
    magic_item = QTableWidgetItem("🪄")
    magic_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    magic_item.setFlags(magic_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
    magic_item.setToolTip("Generuj odpowiedź AI - kliknij aby wygenerować odpowiedź na wątek")
    magic_item.setData(Qt.ItemDataRole.UserRole, {
        "action": "ai_magic",
        "mail": mail
    })
    self.mail_list.setItem(row, visual_idx, magic_item)
```

#### Nowa metoda: `generate_ai_reply()`:
```python
def generate_ai_reply(self, mail: Dict[str, Any]):
    """
    Generuje odpowiedź AI na mail i otwiera okno nowego maila
    """
    from PyQt6.QtWidgets import QProgressDialog
    from src.Modules.AI_module.mail_ai_handler import MailAIHandler, MailThread, AIReplyContext
    
    # Progress dialog
    progress = QProgressDialog("Generuję odpowiedź AI...", "Anuluj", 0, 0, self)
    progress.setWindowModality(Qt.WindowModality.WindowModal)
    progress.show()
    
    try:
        # Zbierz wątek
        thread = self._collect_mail_thread(mail)
        
        # Przygotuj kontekst
        context = AIReplyContext(thread=thread)
        
        # Generuj odpowiedź
        ai_handler = MailAIHandler()
        reply_body = ai_handler.generate_reply(context)
        
        # Otwórz okno nowego maila z odpowiedzią
        self._open_compose_with_reply(mail, thread, reply_body)
        
    except Exception as e:
        self.logger.error(f"Błąd generowania odpowiedzi AI: {e}")
        QMessageBox.warning(self, "Błąd AI", f"Nie udało się wygenerować odpowiedzi: {str(e)}")
    finally:
        progress.close()

def _collect_mail_thread(self, mail: Dict[str, Any]) -> MailThread:
    """Zbiera cały wątek mailowy"""
    # TODO: Implementacja zbierania wątku na podstawie Message-ID, In-Reply-To, References
    # Na razie zwraca tylko pojedynczy mail
    return MailThread(
        emails=[mail],
        subject=mail.get('subject', ''),
        participants=[mail.get('from', ''), mail.get('to', '')]
    )

def _open_compose_with_reply(self, original_mail: Dict[str, Any], thread: MailThread, ai_reply: str):
    """Otwiera okno nowego maila z wygenerowaną odpowiedzią"""
    # Formatuj treść z odpowiedzią AI na górze i cytatem poniżej
    quoted_thread = self._format_quoted_thread(thread)
    full_body = f"{ai_reply}\n\n{quoted_thread}"
    
    # Otwórz okno kompozycji (wykorzystaj istniejącą metodę lub stwórz nową)
    # TODO: Integracja z mail_compose.py
    pass

def _format_quoted_thread(self, thread: MailThread) -> str:
    """Formatuje wątek jako cytowany tekst"""
    lines = []
    for email in thread.emails:
        lines.append(f"\n--- Oryginalna wiadomość ---")
        lines.append(f"Od: {email.get('from', '')}")
        lines.append(f"Data: {email.get('date', '')}")
        lines.append(f"Temat: {email.get('subject', '')}")
        lines.append("")
        # Dodaj > przed każdą linią treści
        body_lines = email.get('body', '').split('\n')
        lines.extend([f"> {line}" for line in body_lines])
    return "\n".join(lines)
```

### 3.4 Panel AI w Oknie Nowego Maila (`mail_compose.py`)

```python
class AIAssistantPanel(QWidget):
    """
    Panel AI w oknie kompozycji maila
    Pozwala na dołączanie źródeł prawdy i regenerację odpowiedzi
    """
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.truth_sources = []
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Nagłówek
        header = QLabel("🤖 Asystent AI")
        header.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(header)
        
        # Ton odpowiedzi
        tone_layout = QHBoxLayout()
        tone_layout.addWidget(QLabel("Ton:"))
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["Profesjonalny", "Casualowy", "Przyjazny"])
        tone_layout.addWidget(self.tone_combo)
        layout.addLayout(tone_layout)
        
        # Źródła prawdy
        sources_label = QLabel("Źródła prawdy (opcjonalne):")
        layout.addWidget(sources_label)
        
        self.sources_list = QListWidget()
        self.sources_list.setMaximumHeight(100)
        layout.addWidget(self.sources_list)
        
        # Przyciski źródeł
        sources_buttons = QHBoxLayout()
        btn_add_note = QPushButton("➕ Dodaj notatkę")
        btn_add_task = QPushButton("➕ Dodaj zadanie")
        btn_add_file = QPushButton("➕ Dodaj plik")
        btn_remove = QPushButton("➖ Usuń")
        
        btn_add_note.clicked.connect(self.add_note_source)
        btn_add_task.clicked.connect(self.add_task_source)
        btn_add_file.clicked.connect(self.add_file_source)
        btn_remove.clicked.connect(self.remove_source)
        
        sources_buttons.addWidget(btn_add_note)
        sources_buttons.addWidget(btn_add_task)
        sources_buttons.addWidget(btn_add_file)
        sources_buttons.addWidget(btn_remove)
        layout.addLayout(sources_buttons)
        
        # Regeneruj odpowiedź
        btn_regenerate = QPushButton("🔄 Regeneruj odpowiedź")
        btn_regenerate.clicked.connect(self.regenerate_reply)
        layout.addWidget(btn_regenerate)
        
        layout.addStretch()
    
    def add_note_source(self):
        """Dodaje notatkę jako źródło prawdy"""
        # TODO: Dialog wyboru notatki z modułu Notes
        pass
    
    def add_task_source(self):
        """Dodaje zadanie jako źródło prawdy"""
        # TODO: Dialog wyboru zadania z modułu Tasks
        pass
    
    def add_file_source(self):
        """Dodaje plik tekstowy jako źródło prawdy"""
        from PyQt6.QtWidgets import QFileDialog
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "Wybierz plik", 
            "", 
            "Pliki tekstowe (*.txt *.md);;Wszystkie pliki (*.*)"
        )
        if file_path:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            self.truth_sources.append({
                "type": "Plik",
                "title": os.path.basename(file_path),
                "content": content
            })
            self.sources_list.addItem(f"📄 {os.path.basename(file_path)}")
    
    def remove_source(self):
        """Usuwa wybrane źródło"""
        current_row = self.sources_list.currentRow()
        if current_row >= 0:
            self.sources_list.takeItem(current_row)
            del self.truth_sources[current_row]
    
    def regenerate_reply(self):
        """Regeneruje odpowiedź z uwzględnieniem źródeł prawdy"""
        # TODO: Implementacja regeneracji z truth_sources
        pass
```

## 4. Uproszczone Etapy Implementacji

### Etap 1: Infrastruktura (1-2h)
- [x] Utworzenie `src/Modules/AI_module/mail_ai_handler.py`
- [ ] Import i konfiguracja istniejącego AI_module
- [ ] Podstawowe testy komunikacji z LLM

### Etap 2: Główna Funkcja - Generowanie Odpowiedzi (3-4h)
- [ ] Implementacja `generate_ai_reply()` w `mail_view.py`
- [ ] Zbieranie wątku mailowego (`_collect_mail_thread()`)
- [ ] Obsługa kliknięcia w 🪄
- [ ] Otwieranie okna kompozycji z wygenerowaną odpowiedzią

### Etap 3: Panel AI w Oknie Kompozycji (2-3h)
- [ ] Utworzenie `AIAssistantPanel` w `mail_compose.py`
- [ ] Dołączanie źródeł prawdy (pliki, notatki, zadania)
- [ ] Regeneracja odpowiedzi z dodatkowym kontekstem

### Etap 4: Integracje (2-3h)
- [ ] Integracja z Tasks Module (wykrywanie zadań, eksport)
- [ ] Integracja z Notes Module (generowanie notatek z wątków)
- [ ] Opcja "Utwórz notatkę" i "Dodaj zadanie" po wygenerowaniu odpowiedzi

### Etap 5: UI/UX i Obsługa Błędów (1-2h)
- [ ] Progress dialog podczas generowania
- [ ] Obsługa błędów API (brak klucza, limit, timeout)
- [ ] Tooltips i dokumentacja w aplikacji

### Etap 6: Testy (1-2h)
- [ ] Testy z różnymi LLM providerami
- [ ] Testy generowania odpowiedzi
- [ ] Testy integracji z Notes/Tasks

## 5. Przykładowe Workflow Użytkownika (Uproszczone)

### Workflow 1: Szybka Odpowiedź AI
1. Użytkownik otrzymuje maila
2. Klika 🪄 obok maila
3. AI pobiera wątek i generuje odpowiedź
4. Otwiera się okno nowego maila z:
   - Wygenerowaną odpowiedzią na górze
   - Cytatem oryginalnego wątku poniżej
5. Użytkownik może:
   - Edytować odpowiedź
   - Wysłać od razu
   - Anulować

### Workflow 2: Odpowiedź ze Źródłami Prawdy
1. Użytkownik klika 🪄
2. W oknie kompozycji otwiera panel AI
3. Dodaje źródła:
   - Notatkę z wymaganiami projektu
   - Plik z cennikiem
   - Zadanie z deadline'em
4. Klika "Regeneruj odpowiedź"
5. AI generuje odpowiedź uwzględniającą wszystkie źródła

### Workflow 3: Generowanie Notatki z Wątku
1. Użytkownik ma długi wątek mailowy (10+ maili)
2. Klika 🪄 → opcjonalne menu → "Utwórz notatkę"
3. AI generuje streszczenie wątku
4. Notatka zapisuje się w module Notes
5. Link do notatki pojawia się w mailu

### Workflow 4: Wykrywanie Zadań
1. Mail zawiera zadania: "Proszę przygotować raport do piątku"
2. Po wygenerowaniu odpowiedzi AI sugeruje:
   - "Znalazłem 1 zadanie. Dodać do Tasks?"
3. Użytkownik klika "Tak"
4. Zadanie "Przygotować raport" dodaje się z deadline na piątek

## 6. Integracje z Modułami (Tylko 2)

### 6.1 Integracja z Tasks Module ✅

**Funkcjonalność:**
- Wykrywanie zadań w treści maili
- Sugestie dodania zadań po wygenerowaniu odpowiedzi
- Eksport zadań z wątku do Tasks

**Implementacja:**
```python
def suggest_tasks_from_thread(self, thread: MailThread):
    """Sugeruje zadania z wątku"""
    ai_handler = MailAIHandler()
    tasks = ai_handler.extract_tasks_from_thread(thread)
    
    if tasks:
        # Pokaż dialog z sugestiami
        dialog = TaskSuggestionDialog(tasks, self)
        if dialog.exec():
            # Dodaj wybrane zadania do Tasks Module
            selected_tasks = dialog.get_selected_tasks()
            self._add_tasks_to_module(selected_tasks)
```

### 6.2 Integracja z Notes Module ✅

**Funkcjonalność:**
- Generowanie notatek ze streszczeniem wątków
- Wykorzystanie notatek jako źródeł prawdy w odpowiedziach
- Szybki zapis podsumowań korespondencji

**Implementacja:**
```python
def create_note_from_thread(self, thread: MailThread):
    """Tworzy notatkę ze streszczenia wątku"""
    ai_handler = MailAIHandler()
    note_content = ai_handler.generate_note_from_thread(thread, note_type="summary")
    
    # Zapisz w Notes Module
    note_title = f"Mail: {thread.subject}"
    self._save_to_notes_module(note_title, note_content)
    
    # Powiadomienie
    QMessageBox.information(self, "Notatka utworzona", 
                          f"Notatka '{note_title}' została zapisana w module Notes")
```

## 7. Wyłączone Funkcje (Poza Zakresem) ❌

**NIE implementujemy:**
- ❌ Automatyczne tagowanie maili
- ❌ Analiza spamu/phishingu  
- ❌ Analiza sentymentu
- ❌ Automatyczne tłumaczenia
- ❌ Ekstrakcja danych strukturalnych (poza zadaniami dla Tasks)
- ❌ Integracja z Pomodoro Module
- ❌ Cache wyników AI
- ❌ Statystyki i dashboard użycia AI
- ❌ Multi-mail actions
- ❌ AI scheduler
- ❌ Voice-to-email

## 8. Podsumowanie

**Uproszczony zakres funkcjonalności:**
1. 🪄 Generowanie odpowiedzi na wątki mailowe (główna funkcja)
2. 📝 Generowanie notatek z wątków (integracja Notes)
3. ✅ Wykrywanie i eksport zadań (integracja Tasks)
4. 📎 Wsparcie źródeł prawdy w panelu AI

**Szacowany czas implementacji: 10-15 godzin**

**Wymagane zasoby:**
- Istniejący moduł `src/Modules/AI_module/` (już skonfigurowany)
- Brak potrzeby dodatkowych kluczy API (używamy konfiguracji użytkownika)

**Korzyści:**
- Maksymalne uproszczenie (focus na 1 głównej funkcji)
- Wykorzystanie istniejącej infrastruktury AI
- Realne wsparcie dla codziennej pracy z mailami
- Integracja tylko z kluczowymi modułami (Notes, Tasks)
