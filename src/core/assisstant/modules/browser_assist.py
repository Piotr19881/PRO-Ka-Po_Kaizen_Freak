"""
Browser Assistant Module
=============================================================================
Obsługuje komendy dotyczące wbudowanej przeglądarki.
"""
from __future__ import annotations

from loguru import logger

from .base import AssistantModule
from ..assistant_core import ParsedCommand


class BrowserAssistantModule(AssistantModule):
    module_name = "browser"
    entity_markers = {
        "pl": ["przeglądarka", "www"],
        "en": ["browser", "web"],
    }

    def __init__(self, browser_controller=None):
        super().__init__()
        self._browser_controller = browser_controller

    def handle_command(self, command: ParsedCommand) -> None:
        self.before_handle(command)
        try:
            logger.info("[BrowserAssistant] Received command: %s", command)
            # TODO: implement open/search actions
        finally:
            self.after_handle(command)
