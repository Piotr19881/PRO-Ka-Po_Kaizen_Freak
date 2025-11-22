"""
Transcryptor Assistant Module
=============================================================================
Obsługuje komendy dotyczące modułu transkryptora.
"""
from __future__ import annotations

from loguru import logger

from .base import AssistantModule
from ..assistant_core import ParsedCommand


class TranscryptorAssistantModule(AssistantModule):
    module_name = "transcryptor"
    entity_markers = {
        "pl": ["transkryptor"],
        "en": ["transcryptor", "transcriber"],
    }

    def __init__(self, transcryptor_controller=None):
        super().__init__()
        self._transcryptor_controller = transcryptor_controller

    def handle_command(self, command: ParsedCommand) -> None:
        self.before_handle(command)
        try:
            logger.info("[TranscryptorAssistant] Received command: %s", command)
            # TODO: implement open/start actions
        finally:
            self.after_handle(command)