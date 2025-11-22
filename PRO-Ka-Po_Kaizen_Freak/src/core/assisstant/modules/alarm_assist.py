"""
Alarm Assistant Module
=============================================================================
Obsługuje komendy dotyczące alarmów/przypomnień.
"""
from __future__ import annotations

from loguru import logger

from .base import AssistantModule
from ..assistant_core import ParsedCommand


class AlarmAssistantModule(AssistantModule):
    module_name = "alarm"
    entity_markers = {
        "pl": ["alarm", "przypomnienie"],
        "en": ["alarm", "reminder"],
    }

    def __init__(self, alarm_controller=None):
        super().__init__()
        self._alarm_controller = alarm_controller

    def handle_command(self, command: ParsedCommand) -> None:
        self.before_handle(command)
        try:
            logger.info("[AlarmAssistant] Received command: %s", command)
            # TODO: implement delete/create/list
        finally:
            self.after_handle(command)