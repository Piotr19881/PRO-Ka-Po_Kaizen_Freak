"""
Pomodoro Assistant Module
=============================================================================
Obsługuje komendy dla modułu pomodoro.
"""
from __future__ import annotations

from loguru import logger

from .base import AssistantModule
from ..assistant_core import ParsedCommand


class PomodoroAssistantModule(AssistantModule):
    module_name = "pomodoro"
    entity_markers = {
        "pl": ["sesja", "pomodoro"],
        "en": ["session", "pomodoro"],
    }

    def __init__(self, pomodoro_controller=None):
        super().__init__()
        self._pomodoro_controller = pomodoro_controller

    def handle_command(self, command: ParsedCommand) -> None:
        self.before_handle(command)
        try:
            logger.info("[PomodoroAssistant] Received command: %s", command)
            
            if not self._pomodoro_controller:
                logger.warning("[PomodoroAssistant] No pomodoro controller registered")
                return
            
            action = command.action
            
            if action == "open":
                self._handle_open()
            elif action == "start":
                self._handle_start()
            elif action == "pause":
                self._handle_pause()
            elif action == "stop":
                self._handle_stop()
            else:
                logger.warning("[PomodoroAssistant] Unknown action: %s", action)
                
        finally:
            self.after_handle(command)
    
    def _handle_open(self):
        """Otwiera widok pomodoro."""
        logger.debug("[PomodoroAssistant] Opening pomodoro view")
        if hasattr(self._pomodoro_controller, 'assistant_open'):
            self._pomodoro_controller.assistant_open()
        else:
            logger.warning("[PomodoroAssistant] assistant_open() not available")
    
    def _handle_start(self):
        """Rozpoczyna sesję pomodoro."""
        logger.debug("[PomodoroAssistant] Starting pomodoro session")
        if hasattr(self._pomodoro_controller, 'assistant_start'):
            self._pomodoro_controller.assistant_start()
        else:
            logger.warning("[PomodoroAssistant] assistant_start() not available")
    
    def _handle_pause(self):
        """Pauzuje sesję pomodoro."""
        logger.debug("[PomodoroAssistant] Pausing pomodoro session")
        if hasattr(self._pomodoro_controller, 'assistant_pause'):
            self._pomodoro_controller.assistant_pause()
        else:
            logger.warning("[PomodoroAssistant] assistant_pause() not available")
    
    def _handle_stop(self):
        """Zatrzymuje sesję pomodoro."""
        logger.debug("[PomodoroAssistant] Stopping pomodoro session")
        if hasattr(self._pomodoro_controller, 'assistant_stop'):
            self._pomodoro_controller.assistant_stop()
        else:
            logger.warning("[PomodoroAssistant] assistant_stop() not available")