"""
Mail Assistant Module
=============================================================================
Obsługuje komendy dotyczące modułu mailowego.
"""
from __future__ import annotations

from loguru import logger

from .base import AssistantModule
from ..assistant_core import ParsedCommand


class MailAssistantModule(AssistantModule):
    module_name = "mail"
    entity_markers = {
        "pl": ["wiadomość", "mail", "email"],
        "en": ["mail", "email", "message"],
    }

    def __init__(self, mail_controller=None):
        super().__init__()
        self._mail_controller = mail_controller

    def handle_command(self, command: ParsedCommand) -> None:
        self.before_handle(command)
        try:
            logger.info("[MailAssistant] Received command: %s", command)
            # TODO: implement create/open actions
        finally:
            self.after_handle(command)
