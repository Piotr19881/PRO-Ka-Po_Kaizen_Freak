"""
Task Bar Voice/Text Assistant
=============================================================================
Asystent monitorujący pole szybkiego wprowadzania (quick-add) i uruchamiający
funkcje aplikacji na podstawie rozpoznanych fraz.

ARCHITEKTURA:
- Frazy przechowywane w bazie danych PostgreSQL (tabela: assistant_phrases)
- Lokalna cache fraz dla szybkiego dopasowania (bez ciągłego odpytywania DB)
- Parser sprawdza pierwsze 3 słowa inputu użytkownika
- Timeout 3s po zakończeniu pisania przed parsowaniem
- Wielojęzyczność: pl/en/de + możliwość dodawania własnych fraz
- Emisja PyQt6 signals do UI

FUNKCJE (metody):
- create_task -> tworzy zadanie
- create_note -> tworzy notatkę

BAZA DANYCH:
Tabela: assistant_phrases
- id, method_name, language, phrase, is_active, is_custom, priority

UŻYCIE:
    assistant = TaskBarAssistant(api_client, local_db)
    assistant.create_task_requested.connect(handle_create_task)
    assistant.feed_text(text)  # Wywołaj gdy użytkownik pisze
"""
from __future__ import annotations

from typing import Dict, List, Optional, Tuple
from PyQt6.QtCore import QObject, pyqtSignal, QTimer
from loguru import logger


class TaskBarAssistant(QObject):
    """
    Asystent paska zadań - rozpoznaje komendy głosowe/tekstowe i uruchamia funkcje.
    
    Signals:
        create_task_requested(str): Wywołane gdy wykryto komendę tworzenia zadania
        create_note_requested(str): Wywołane gdy wykryto komendę tworzenia notatki
        phrases_updated(): Wywołane gdy zaktualizowano frazy z bazy
    """
    
    create_task_requested = pyqtSignal(str)  # Payload: treść zadania
    create_note_requested = pyqtSignal(str)  # Payload: treść notatki
    phrases_updated = pyqtSignal()  # Frazy zostały odświeżone
    
    def __init__(
        self,
        api_client=None,
        local_db=None,
        silence_timeout_ms: int = 3000,
        parent: Optional[QObject] = None
    ):
        """
        Inicjalizacja asystenta.
        
        Args:
            api_client: Klient API do synchronizacji fraz z serwerem
            local_db: Lokalna baza danych (cache)
            silence_timeout_ms: Czas ciszy przed parsowaniem (domyślnie 3s)
            parent: Rodzic QObject
        """
        super().__init__(parent)
        
        self.api_client = api_client
        self.local_db = local_db
        
        # Timer wykrywający koniec pisania
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.setInterval(silence_timeout_ms)
        self._timer.timeout.connect(self._on_silence)
        
        self._last_text: str = ""
        self.language: str = "pl"  # Aktualny język (pl/en/de)
        
        # Cache fraz: {method_name: [(language, phrase, priority), ...]}
        self._phrases_cache: Dict[str, List[Tuple[str, str, int]]] = {}
        
        # Załaduj frazy z bazy (lub użyj domyślnych jeśli brak połączenia)
        self._load_phrases_from_db()
    
    # =============================================================================
    # PUBLIC API
    # =============================================================================
    
    def feed_text(self, text: str) -> None:
        """
        Przekaż tekst z pola quick-add do asystenta.
        
        Wywołuj za każdym razem gdy użytkownik zmienia tekst w polu.
        Timer zostanie zrestartowany - parsowanie nastąpi po 3s ciszy.
        
        Args:
            text: Aktualny tekst z pola wprowadzania
        """
        self._last_text = text or ""
        self._timer.start()  # Restart timera
        
    def stop(self) -> None:
        """Zatrzymaj asystenta (anuluj oczekujące parsowanie)."""
        self._timer.stop()
        
    def set_language(self, language: str) -> None:
        """
        Ustaw aktualny język interfejsu.
        
        Args:
            language: Kod języka: 'pl', 'en', 'de'
        """
        if language in ['pl', 'en', 'de']:
            self.language = language
            logger.info(f"[TaskBarAssistant] Language set to: {language}")
    
    def reload_phrases(self) -> None:
        """Odśwież frazy z bazy danych."""
        self._load_phrases_from_db()
        self.phrases_updated.emit()
        logger.info("[TaskBarAssistant] Phrases reloaded from database")
    
    def add_custom_phrase(
        self, 
        method_name: str, 
        phrase: str, 
        language: str = "pl",
        priority: int = 5
    ) -> bool:
        """
        Dodaj własną frazę użytkownika.
        
        Args:
            method_name: Nazwa metody ('create_task', 'create_note')
            phrase: Fraza uruchamiająca
            language: Język frazy
            priority: Priorytet (5 = standardowy dla custom)
            
        Returns:
            True jeśli udało się dodać do bazy
        """
        try:
            if self.local_db:
                # TODO: Dodaj do lokalnej bazy
                # self.local_db.add_phrase(method_name, language, phrase, is_custom=True, priority=priority)
                pass
            
            if self.api_client:
                # TODO: Synchronizuj z serwerem
                # self.api_client.post_phrase(method_name, language, phrase, is_custom=True, priority=priority)
                pass
            
            # Dodaj do cache
            if method_name not in self._phrases_cache:
                self._phrases_cache[method_name] = []
            
            self._phrases_cache[method_name].append((language, phrase.lower(), priority))
            self._phrases_cache[method_name].sort(key=lambda x: x[2], reverse=True)  # Sort by priority
            
            logger.info(f"[TaskBarAssistant] Added custom phrase: '{phrase}' -> {method_name}")
            return True
            
        except Exception as e:
            logger.error(f"[TaskBarAssistant] Failed to add custom phrase: {e}")
            return False
    
    # =============================================================================
    # INTERNAL METHODS
    # =============================================================================
    
    def _load_phrases_from_db(self) -> None:
        """
        Załaduj frazy z bazy danych do cache.
        
        Jeśli baza niedostępna - użyj domyślnych fraz hardcoded.
        """
        try:
            if self.local_db:
                # TODO: Implementuj pobieranie z local_db
                # phrases = self.local_db.get_active_phrases()
                # self._phrases_cache = self._build_cache_from_db(phrases)
                logger.warning("[TaskBarAssistant] Local DB integration not implemented yet")
                self._use_default_phrases()
            else:
                logger.warning("[TaskBarAssistant] No database available, using default phrases")
                self._use_default_phrases()
                
        except Exception as e:
            logger.error(f"[TaskBarAssistant] Failed to load phrases from DB: {e}")
            self._use_default_phrases()
    
    def _use_default_phrases(self) -> None:
        """Załaduj domyślne frazy (fallback gdy baza niedostępna)."""
        self._phrases_cache = {
            "create_task": [
                ("pl", "utwórz zadanie", 10),
                ("pl", "dodaj zadanie", 10),
                ("pl", "nowe zadanie", 10),
                ("pl", "stwórz zadanie", 9),
                ("en", "create task", 10),
                ("en", "add task", 10),
                ("en", "new task", 10),
                ("de", "aufgabe erstellen", 10),
                ("de", "aufgabe hinzufügen", 10),
                ("de", "neue aufgabe", 10),
            ],
            "create_note": [
                ("pl", "utwórz notatkę", 10),
                ("pl", "dodaj notatkę", 10),
                ("pl", "nowa notatka", 10),
                ("en", "create note", 10),
                ("en", "add note", 10),
                ("en", "new note", 10),
                ("de", "notiz erstellen", 10),
                ("de", "notiz hinzufügen", 10),
                ("de", "neue notiz", 10),
            ]
        }
        logger.info("[TaskBarAssistant] Loaded default phrases (fallback mode)")
    
    def _on_silence(self) -> None:
        """Callback po upływie timera - użytkownik skończył pisać."""
        text = self._last_text.strip()
        if not text:
            return
        
        logger.debug(f"[TaskBarAssistant] Parsing input: '{text}'")
        self._parse_and_emit(text)
    
    def _parse_and_emit(self, text: str) -> None:
        """
        Parsuj tekst i wywołaj odpowiednią akcję.
        
        Strategia:
        1. Wyciągnij pierwsze 3 słowa z inputu
        2. Sprawdź czy pasują do fraz w aktualnym języku (priorytet)
        3. Jeśli nie - sprawdź inne języki
        4. Wywołaj metodę i przekaż resztę tekstu jako payload
        
        Args:
            text: Tekst do sparsowania
        """
        # Wyciągnij pierwsze 3 słowa
        words = text.split()
        if not words:
            return
        
        # Testuj od 3 słów w dół do 1 słowa
        for word_count in range(min(3, len(words)), 0, -1):
            prefix = " ".join(words[:word_count]).lower()
            
            # Sprawdź dopasowanie
            match = self._match_phrase(prefix)
            if match:
                method_name, matched_phrase = match
                
                # Wyciągnij resztę tekstu (payload)
                remainder_words = words[word_count:]
                payload = " ".join(remainder_words).strip()
                
                logger.info(f"[TaskBarAssistant] Matched '{matched_phrase}' -> {method_name}, payload: '{payload}'")
                
                # Wywołaj odpowiednią akcję
                self._execute_action(method_name, payload)
                return
        
        logger.debug(f"[TaskBarAssistant] No matching phrase found for: '{text}'")
    
    def _match_phrase(self, prefix: str) -> Optional[Tuple[str, str]]:
        """
        Dopasuj prefix do fraz w cache.
        
        Priorytet:
        1. Frazy w aktualnym języku
        2. Frazy w innych językach
        3. Sortowane po priorytecie (wyższy = ważniejszy)
        
        Args:
            prefix: Pierwsze 1-3 słowa z inputu (lowercase)
            
        Returns:
            (method_name, matched_phrase) lub None
        """
        # Przeszukaj wszystkie metody
        for method_name, phrases in self._phrases_cache.items():
            # Sortuj: najpierw aktualny język, potem według priorytetu
            sorted_phrases = sorted(
                phrases,
                key=lambda x: (x[0] != self.language, -x[2])  # (not current lang, -priority)
            )
            
            for lang, phrase, priority in sorted_phrases:
                if prefix == phrase.lower() or prefix.startswith(phrase.lower() + " "):
                    return (method_name, phrase)
        
        return None
    
    def _execute_action(self, method_name: str, payload: str) -> None:
        """
        Wykonaj akcję na podstawie rozpoznanej metody.
        
        Args:
            method_name: Nazwa metody do wykonania
            payload: Reszta tekstu (treść zadania/notatki)
        """
        if method_name == "create_task":
            self.create_task_requested.emit(payload)
            logger.info(f"[TaskBarAssistant] Emitted create_task_requested: '{payload}'")
            
        elif method_name == "create_note":
            self.create_note_requested.emit(payload)
            logger.info(f"[TaskBarAssistant] Emitted create_note_requested: '{payload}'")
            
        else:
            logger.warning(f"[TaskBarAssistant] Unknown method: {method_name}")
    
    # =============================================================================
    # METODY AKCJI (wywoływane przez UI po odebraniu signalu)
    # =============================================================================
    
    def create_task(self, title: str) -> None:
        """
        Metoda placeholder - faktyczne tworzenie zadania powinno być w UI.
        Ta metoda służy tylko jako dokumentacja API.
        
        Args:
            title: Tytuł zadania
        """
        logger.debug(f"[TaskBarAssistant] create_task called with: '{title}'")
        # UI powinno obsłużyć signal create_task_requested
    
    def create_note(self, content: str) -> None:
        """
        Metoda placeholder - faktyczne tworzenie notatki powinno być w UI.
        
        Args:
            content: Treść notatki
        """
        logger.debug(f"[TaskBarAssistant] create_note called with: '{content}'")
        # UI powinno obsłużyć signal create_note_requested


__all__ = ["TaskBarAssistant"]
