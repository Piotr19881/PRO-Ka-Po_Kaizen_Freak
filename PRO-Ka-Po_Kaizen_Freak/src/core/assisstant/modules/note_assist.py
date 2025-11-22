"""
Note Assistant Module
=============================================================================
Obsługuje komendy dotyczące modułu notatek.
"""
from __future__ import annotations

from loguru import logger

from .base import AssistantModule
from ..assistant_core import ParsedCommand


class NoteAssistantModule(AssistantModule):
    module_name = "note"
    entity_markers = {
        "pl": ["notatka", "notatki"],
        "en": ["note", "notes", "memo"],
    }

    def __init__(self, notes_controller=None):
        super().__init__()
        self._notes_controller = notes_controller

    def handle_command(self, command: ParsedCommand) -> None:
        self.before_handle(command)
        try:
            logger.info("[NoteAssistant] Received command: %s", command)
            # TODO: obsługa create/delete/open/list
        finally:
            self.after_handle(command)