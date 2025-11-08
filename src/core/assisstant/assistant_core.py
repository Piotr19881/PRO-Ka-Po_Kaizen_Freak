"""
Assistant Core - centralny serwer asystenta
=============================================================================
Odpowiada za parsowanie fraz, rozpoznawanie intencji oraz delegowanie komend
do odpowiednich modułów asystenta.

Najważniejsze założenia:
- brak twardych stringów w logice rozpoznawania (frazy z bazy danych)
- obsługa wielu języków (frazy w tabeli zawierają kod języka)
- możliwość ekstrakcji nazw własnych (zapisanych w cudzysłowie lub po markerach)
- modułowa architektura (osobne klasy dla poszczególnych widoków)
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Callable, TYPE_CHECKING
from loguru import logger
import re
from PyQt6.QtCore import QObject, pyqtSignal

from .assistant_database import AssistantPhrase, AssistantDatabase

if TYPE_CHECKING:  # pragma: no cover - tylko dla type checkera
    from .modules.base import AssistantModule


@dataclass
class ParsedCommand:
    """Znormalizowana komenda rozpoznana przez asystenta."""
    module: str
    action: str
    phrase_id: int
    language: str
    entity_name: Optional[str] = None
    confidence: float = 1.0
    raw_text: str = ""
    extra_params: Dict[str, Any] | None = None
    
    def __post_init__(self):
        if self.extra_params is None:
            self.extra_params = {}


class AssistantCore(QObject):
    """Centralny parser i router asystenta."""

    # Ogólne sygnały
    command_recognized = pyqtSignal(ParsedCommand)
    command_failed = pyqtSignal(str)

    def __init__(self, database: AssistantDatabase, language_provider: Callable[[], str], parent=None):
        """
        Args:
            database: Obiekt dostępu do bazy fraz
            language_provider: Funkcja zwracająca aktualny kod języka UI
        """
        super().__init__(parent)
        self._db = database
        self._language_provider = language_provider
        
        # Cache fraz wg modułu
        self._phrases_by_module: Dict[str, List[AssistantPhrase]] = {}
        
        # Markery nazw własnych (można rozszerzać w modułach)
        self._entity_markers: Dict[str, Dict[str, List[str]]] = {}

        # Zarejestrowane moduły logiki
        self._module_handlers: Dict[str, "AssistantModule"] = {}

        logger.info("[ASSISTANT_CORE] Initialized")

    # ------------------------------------------------------------------
    # ŁADOWANIE FRAZ
    # ------------------------------------------------------------------
    def refresh_cache(self, language: Optional[str] = None):
        """Przeładowuje frazy z bazy do cache."""
        language = language or self._language_provider()
        phrases = self._db.get_phrases(language=language, active_only=True)

        phrases_by_module: Dict[str, List[AssistantPhrase]] = {}
        for phrase in phrases:
            phrases_by_module.setdefault(phrase.module, []).append(phrase)
        
        # Sortowanie po priorytecie (malejąco)
        for module, module_phrases in phrases_by_module.items():
            phrases_by_module[module] = sorted(module_phrases, key=lambda p: p.priority, reverse=True)

        self._phrases_by_module = phrases_by_module
        logger.debug("[ASSISTANT_CORE] Cache refreshed: %s modules", list(self._phrases_by_module.keys()))

    def register_entity_markers(self, module: str, markers: Dict[str, List[str]]):
        """Rejestruje markery nazw własnych dla modułu."""
        if module not in self._entity_markers:
            self._entity_markers[module] = {}
        
        for lang, values in markers.items():
            # Normalizuj do małych liter
            self._entity_markers[module][lang] = [value.lower() for value in values]

    def register_module(self, module_handler: "AssistantModule"):
        """Rejestruje moduł logiki asystenta."""
        module_name = module_handler.module_name
        self._module_handlers[module_name] = module_handler
        
        markers = module_handler.entity_markers
        if markers:
            self.register_entity_markers(module_name, markers)
        
        logger.debug("[ASSISTANT_CORE] Module registered: %s", module_name)

    # ------------------------------------------------------------------
    # PARSOWANIE
    # ------------------------------------------------------------------
    def parse(self, text: str) -> Optional[ParsedCommand]:
        """Przetwarza tekst i zwraca sparsowaną komendę."""
        cleaned = text.strip()
        if not cleaned:
            logger.debug("[ASSISTANT_CORE] Empty input")
            return None

        language = self._language_provider()
        lowered = cleaned.lower()

        # Upewnij się, że cache jest aktualny
        if not self._phrases_by_module:
            self.refresh_cache(language)

        for module, phrases in self._phrases_by_module.items():
            for phrase in phrases:
                matched, entity = self._match_phrase(lowered, phrase, language)
                if matched:
                    command = ParsedCommand(
                        module=phrase.module,
                        action=phrase.action,
                        phrase_id=phrase.id or -1,
                        language=phrase.language,
                        entity_name=entity,
                        confidence=1.0,
                        raw_text=cleaned,
                        extra_params={"matched_phrase": phrase.phrase},
                    )
                    logger.debug("[ASSISTANT_CORE] Matched phrase %s (module=%s)", phrase.phrase, module)
                    return command

        logger.info("[ASSISTANT_CORE] No match for input: %s", cleaned)
        return None

    def _match_phrase(self, lowered_text: str, phrase: AssistantPhrase, language: str) -> Tuple[bool, Optional[str]]:
        """Sprawdza dopasowanie do frazy z bazy."""
        pattern = phrase.phrase.lower()

        if phrase.extract_entity:
            if lowered_text.startswith(pattern):
                entity = self._extract_entity(lowered_text[len(pattern):].strip(), phrase.module, language)
                return True, entity
            return False, None
        
        # Frazy bez ekstrakcji traktujemy jako dokładne dopasowanie prefixu
        match = lowered_text == pattern or lowered_text.startswith(pattern + " ")
        return match, None

    def _extract_entity(self, remainder: str, module: str, language: str) -> Optional[str]:
        """Ekstraktuje nazwę własną z pozostałej części komendy."""
        if not remainder:
            return None

        # 1. Cudzysłowy
        quoted = re.search(r"[\"']([^\"']+)[\"']", remainder)
        if quoted:
            return quoted.group(1).strip()

        # 2. Markery modułu w danym języku
        markers = self._entity_markers.get(module, {}).get(language, [])
        for marker in markers:
            if remainder.startswith(marker + " "):
                candidate = remainder[len(marker):].strip()
                return self._clean_entity(candidate)

        # 3. Domyślnie całość
        return self._clean_entity(remainder)

    @staticmethod
    def _clean_entity(text: str) -> str:
        """Czyści tekst nazwy z trailing znaków interpunkcyjnych."""
        cleaned = re.sub(r"[.,!?;]+$", "", text).strip()
        return cleaned

    # ------------------------------------------------------------------
    # WYKONANIE KOMENDY
    # ------------------------------------------------------------------
    def execute(self, text: str) -> bool:
        """Parsuje i emituje sygnał z komendą."""
        command = self.parse(text)
        if not command:
            self.command_failed.emit(text)
            return False

        return self.dispatch(command)

    def dispatch(self, command: ParsedCommand) -> bool:
        """Przekazuje gotową komendę do właściwego modułu."""
        self.command_recognized.emit(command)

        handler = self._module_handlers.get(command.module)
        if handler:
            handler.handle_command(command)
            return True

        logger.warning("[ASSISTANT_CORE] No handler for module: %s", command.module)
        return False


__all__ = ["AssistantCore", "ParsedCommand"]
