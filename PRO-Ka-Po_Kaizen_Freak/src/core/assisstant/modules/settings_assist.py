"""
Settings Assistant Module
=============================================================================
Obsługuje komendy powiązane z konfiguracją aplikacji i preferencjami użytkownika.
"""
from __future__ import annotations

from loguru import logger

from .base import AssistantModule
from ..assistant_core import ParsedCommand


class SettingsAssistantModule(AssistantModule):
    module_name = "settings"
    entity_markers = {
        "pl": ["ustawienia", "preferencje"],
        "en": ["settings", "preferences"],
    }

    def __init__(self, settings_service=None):
        super().__init__()
        self._settings_service = settings_service

    def handle_command(self, command: ParsedCommand) -> None:
        self.before_handle(command)
        try:
            logger.info("[SettingsAssistant] Received command: %s", command)
            # TODO: implement adjust/get actions
        finally:
            self.after_handle(command)
