"""
Task Assistant Module
=============================================================================
Obsługuje komendy asystenta powiązane z modułem zadań.
"""
from __future__ import annotations

from typing import Any

from loguru import logger

from .base import AssistantModule
from ..assistant_core import ParsedCommand


class TaskAssistantModule(AssistantModule):
    module_name = "task"
    entity_markers = {
        "pl": ["zadanie", "zadania"],
        "en": ["task", "tasks", "todo"],
    }

    def __init__(self, task_controller: Any | None = None) -> None:
        super().__init__()
        self._task_controller = task_controller

    def set_task_controller(self, controller: Any | None) -> None:
        """Aktualizuje referencję do kontrolera odpowiedzialnego za obsługę zadań."""
        self._task_controller = controller

    def handle_command(self, command: ParsedCommand) -> None:
        self.before_handle(command)
        try:
            logger.info(
                "[TaskAssistant] command=%s.%s entity=%s",
                command.module,
                command.action,
                command.entity_name,
            )

            if command.action == "create":
                self._handle_create(command)
            else:  # pragma: no cover - kolejne akcje będą dodane w przyszłości
                logger.debug("[TaskAssistant] Action '%s' not handled yet", command.action)
        finally:
            self.after_handle(command)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _handle_create(self, command: ParsedCommand) -> None:
        title = self._resolve_title(command)
        if not title:
            logger.warning("[TaskAssistant] Skipping create action – no title detected")
            return

        controller = self._task_controller
        if controller and hasattr(controller, "handle_assistant_task_create"):
            try:
                controller.handle_assistant_task_create(command, title)
            except Exception as exc:  # pragma: no cover - defensively log unexpected issues
                logger.error("[TaskAssistant] Controller failed to create task: %s", exc)
        else:
            logger.warning("[TaskAssistant] No controller available to create task '%s'", title)

    @staticmethod
    def _resolve_title(command: ParsedCommand) -> str:
        if command.entity_name:
            return command.entity_name.strip()

        extra = command.extra_params or {}
        candidate = str(extra.get("entity_guess", "")).strip()
        if candidate:
            return candidate

        raw_text = (command.raw_text or "").strip()
        return raw_text