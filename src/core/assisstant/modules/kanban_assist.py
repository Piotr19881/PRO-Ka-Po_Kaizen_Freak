"""
Kanban Assistant Module
=============================================================================
Obsługuje polecenia głosowe dla widoku Kanban:
- Otwieranie widoku
- Pokazywanie/ukrywanie kolumn
- Pokazywanie wszystkich kolumn
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Optional, Dict, List
from loguru import logger

from .base import AssistantModule

if TYPE_CHECKING:
    from ..assistant_core import ParsedCommand


class KanbanAssistantModule(AssistantModule):
    """Moduł asystenta dla widoku Kanban."""
    
    module_name = "kanban"
    
    # Markery dla rozpoznawania nazw kolumn w komendach
    entity_markers: Dict[str, List[str]] = {
        'in_progress': ['w trakcie', 'in progress', 'progress'],
        'todo': ['do wykonania', 'todo', 'to do'],
        'done': ['zakończone', 'ukończone', 'done', 'finished'],
        'review': ['do sprawdzenia', 'review', 'sprawdzenia'],
        'on_hold': ['wstrzymane', 'odłożone', 'on hold', 'hold'],
    }
    
    def __init__(self, kanban_controller=None):
        """
        Args:
            kanban_controller: Kontroler z metodami handle_assistant_kanban_*
        """
        super().__init__()
        self._controller = kanban_controller
    
    def set_kanban_controller(self, controller) -> None:
        """Ustawia kontroler Kanban (MainWindow)."""
        self._controller = controller
        logger.debug("[KanbanAssistantModule] Controller set")
    
    def handle_command(self, command: ParsedCommand) -> None:
        """
        Obsługuje polecenia dla modułu kanban.
        
        Args:
            command: Sparsowana komenda
        """
        self.before_handle(command)
        
        try:
            if not self._controller:
                logger.warning("[KanbanAssistantModule] No controller set")
                return
            
            action = command.action
            
            logger.info(
                "[KanbanAssistantModule] command=%s.%s entity=%s",
                command.module,
                command.action,
                command.entity_name,
            )
            
            if action == "open":
                self._handle_open(command)
            elif action == "show_all":
                self._handle_show_all(command)
            elif action == "show_column":
                self._handle_show_column(command)
            elif action == "hide_column":
                self._handle_hide_column(command)
            else:
                logger.debug(f"[KanbanAssistantModule] Unknown action: {action}")
                    
        except Exception as exc:
            logger.error(f"[KanbanAssistantModule] Error handling command: {exc}")
        finally:
            self.after_handle(command)
    
    def _handle_open(self, command: ParsedCommand) -> None:
        """Otwiera widok kanban."""
        if not hasattr(self._controller, 'handle_assistant_kanban_open'):
            logger.error("[KanbanAssistantModule] Controller missing handle_assistant_kanban_open")
            return
        
        self._controller.handle_assistant_kanban_open(command)
    
    def _handle_show_all(self, command: ParsedCommand) -> None:
        """Pokazuje wszystkie kolumny."""
        if not hasattr(self._controller, 'handle_assistant_kanban_show_all'):
            logger.error("[KanbanAssistantModule] Controller missing handle_assistant_kanban_show_all")
            return
        
        self._controller.handle_assistant_kanban_show_all(command)
    
    def _handle_show_column(self, command: ParsedCommand) -> None:
        """Pokazuje konkretną kolumnę."""
        column_name = self._extract_column_name(command)
        
        if not column_name:
            logger.warning(f"[KanbanAssistantModule] Cannot extract column name from: {command.entity_name}")
            return
        
        if not hasattr(self._controller, 'handle_assistant_kanban_show_column'):
            logger.error("[KanbanAssistantModule] Controller missing handle_assistant_kanban_show_column")
            return
        
        self._controller.handle_assistant_kanban_show_column(command, column_name)
    
    def _handle_hide_column(self, command: ParsedCommand) -> None:
        """Ukrywa konkretną kolumnę."""
        column_name = self._extract_column_name(command)
        
        if not column_name:
            logger.warning(f"[KanbanAssistantModule] Cannot extract column name from: {command.entity_name}")
            return
        
        if not hasattr(self._controller, 'handle_assistant_kanban_hide_column'):
            logger.error("[KanbanAssistantModule] Controller missing handle_assistant_kanban_hide_column")
            return
        
        self._controller.handle_assistant_kanban_hide_column(command, column_name)
    
    def _extract_column_name(self, command: ParsedCommand) -> Optional[str]:
        """
        Ekstraktuje internal column name z entity w komendzie.
        
        Args:
            command: ParsedCommand z entity_name (np. "w trakcie", "do wykonania")
            
        Returns:
            Internal column name ('in_progress', 'todo', etc.) lub None
        """
        entity = (command.entity_name or "").strip().lower()
        
        if not entity:
            # Próbuj wyekstrahować z raw_text jeśli entity_name nie został ustawiony
            raw = command.raw_text.lower()
            for internal_name, markers in self.entity_markers.items():
                for marker in markers:
                    if marker in raw:
                        logger.debug(f"[KanbanAssistantModule] Extracted '{internal_name}' from raw_text")
                        return internal_name
            return None
        
        # Mapuj entity na internal name
        for internal_name, markers in self.entity_markers.items():
            for marker in markers:
                if marker in entity:
                    logger.debug(f"[KanbanAssistantModule] Mapped '{entity}' -> '{internal_name}'")
                    return internal_name
        
        logger.debug(f"[KanbanAssistantModule] No mapping found for entity: {entity}")
        return None


__all__ = ['KanbanAssistantModule']
