"""
Assistant Modules - baza modułów asystenta
=============================================================================
Definiuje abstrakcyjną klasę bazową dla modułów obsługujących komendy
rozpoznane przez AssistantCore. Każdy moduł jest odpowiedzialny za
obsługę konkretnego widoku/funkcjonalności w aplikacji.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, List

from ..assistant_core import ParsedCommand


class AssistantModule(ABC):
    """Abstrakcyjna baza modułu asystenta."""

    #: Nazwa modułu (np. "task", "note") musi być unikalna
    module_name: str = ""

    #: Markery nazw własnych w poszczególnych językach
    #: Przykład: {"pl": ["zadanie", "notatka"], "en": ["task", "note"]}
    entity_markers: Dict[str, List[str]] = {}

    def __init__(self):
        if not self.module_name:
            raise ValueError("AssistantModule requires module_name to be defined")

    @abstractmethod
    def handle_command(self, command: ParsedCommand) -> None:
        """Obsługuje komendę rozpoznaną przez AssistantCore."""
        ...

    def before_handle(self, command: ParsedCommand) -> None:  # pragma: no cover - hook opcjonalny
        """Hook wywoływany przed handle_command."""
        # Domyślnie nic nie robi, moduły mogą nadpisać

    def after_handle(self, command: ParsedCommand) -> None:  # pragma: no cover - hook opcjonalny
        """Hook wywoływany po handle_command."""
        # Domyślnie nic nie robi, moduły mogą nadpisać
