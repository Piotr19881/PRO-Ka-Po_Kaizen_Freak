"""
Assistant Input Watcher
=============================================================================
Utility for monitoring text inputs (e.g., quick task bars) and delegating
recognized commands to AssistantCore with debounce.
"""
from __future__ import annotations

from typing import Callable, Optional
from PyQt6.QtCore import QObject, QTimer
from PyQt6.QtWidgets import QLineEdit
from loguru import logger

from .assistant_core import AssistantCore, ParsedCommand

ContextProvider = Callable[[ParsedCommand], Optional[dict]]
CommandFilter = Callable[[ParsedCommand], bool]


class AssistantInputWatcher(QObject):
    """Observes a QLineEdit and dispatches assistant commands after debounce."""

    def __init__(
        self,
        line_edit: QLineEdit,
        assistant: AssistantCore,
        *,
        debounce_ms: int = 1200,
        context_provider: ContextProvider | None = None,
        command_filter: CommandFilter | None = None,
        context_name: str = "",
    ) -> None:
        super().__init__(line_edit)
        self._line_edit = line_edit
        self._assistant = assistant
        self._debounce_ms = max(200, int(debounce_ms))
        self._context_provider = context_provider
        self._command_filter = command_filter
        self._context_name = context_name or getattr(line_edit, "objectName", lambda: "")() or "input"

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self._on_timeout)

        self._pending_text: str = ""
        self._last_processed: str = ""

        line_edit.textChanged.connect(self._on_text_changed)
        line_edit.destroyed.connect(self._on_line_destroyed)
        logger.debug("[AssistantInputWatcher] Initialized for %s", self._context_name)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------
    def _on_text_changed(self, text: str) -> None:
        if text is None:
            text = ""

        stripped = text.strip()
        if not stripped:
            self._timer.stop()
            self._pending_text = ""
            return

        if stripped == self._last_processed:
            # Ignore duplicates to prevent repeated execution
            return

        self._pending_text = stripped
        self._timer.start(self._debounce_ms)
        logger.trace("[AssistantInputWatcher] Pending text (%s): %s", self._context_name, stripped)

    def _on_line_destroyed(self) -> None:  # pragma: no cover - Qt cleanup
        self._timer.stop()
        logger.debug("[AssistantInputWatcher] Line edit destroyed for %s", self._context_name)

    def _on_timeout(self) -> None:
        text = self._pending_text
        if not text or text == self._last_processed:
            return

        try:
            command = self._assistant.parse(text)
        except Exception as exc:  # pragma: no cover - defensive
            logger.error("[AssistantInputWatcher] Failed to parse input '%s': %s", text, exc)
            return

        if not command:
            logger.trace("[AssistantInputWatcher] No command detected for: %s", text)
            return

        if self._command_filter and not self._command_filter(command):
            logger.trace(
                "[AssistantInputWatcher] Command filtered out (%s.%s) for context %s",
                command.module,
                command.action,
                self._context_name,
            )
            return

        if self._context_provider:
            try:
                context = self._context_provider(command) or {}
                if isinstance(context, dict):
                    command.extra_params.update(context)
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("[AssistantInputWatcher] Context provider failed: %s", exc)

        handled = self._assistant.dispatch(command)
        if handled:
            self._last_processed = text
            
            # Wyczyść pole po pomyślnym wykonaniu komendy
            if self._line_edit and hasattr(self._line_edit, 'clear'):
                self._line_edit.clear()
            
            logger.info(
                "[AssistantInputWatcher] Command handled (%s.%s) for context %s",
                command.module,
                command.action,
                self._context_name,
            )
        else:
            logger.debug(
                "[AssistantInputWatcher] Command not handled (%s.%s) for context %s",
                command.module,
                command.action,
                self._context_name,
            )