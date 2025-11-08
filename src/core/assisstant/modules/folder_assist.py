"""
Folder Assistant Module
=============================================================================
Obsługuje komendy dla modułu zarządzania folderami/dokumentami.
"""
from __future__ import annotations

from loguru import logger

from .base import AssistantModule
from ..assistant_core import ParsedCommand


class FolderAssistantModule(AssistantModule):
    module_name = "folder"
    entity_markers = {
        "pl": ["folder", "katalog"],
        "en": ["folder", "directory"],
    }

    def __init__(self, file_controller=None):
        super().__init__()
        self._file_controller = file_controller

    def handle_command(self, command: ParsedCommand) -> None:
        self.before_handle(command)
        try:
            logger.info("[FolderAssistant] Received command: %s", command)
            # TODO: implement open/browse actions
        finally:
            self.after_handle(command)
