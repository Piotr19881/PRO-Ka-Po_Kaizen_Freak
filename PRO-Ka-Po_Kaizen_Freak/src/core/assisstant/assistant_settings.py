"""
Assistant Settings Manager - wersja DB
=============================================================================
Warstwa zarządzająca frazami asystenta oparta o bazę SQLite. Oferuje API
wykorzystywane przez UI ustawień do przeglądania i modyfikacji fraz.
"""
from __future__ import annotations

from typing import Dict, List, Optional
from dataclasses import dataclass
from loguru import logger

from .assistant_database import AssistantDatabase, AssistantPhrase

try:  # pragma: no cover - środowisko testowe może nie mieć i18n
    from ...utils.i18n_manager import t
except ImportError:  # pragma: no cover
    def t(key: str, default: str = "") -> str:
        return default or key


@dataclass(frozen=True)
class AssistantActionMeta:
    """Metadane pojedynczej akcji w module asystenta."""

    module: str
    action: str
    label_key: str
    label_default: str
    description_key: str
    description_default: str

    @property
    def label(self) -> str:
        return t(self.label_key, self.label_default)

    @property
    def description(self) -> str:
        return t(self.description_key, self.description_default)


class AssistantSettingsManager:
    """Warstwa zarządzająca frazami asystenta."""

    def __init__(self, database: Optional[AssistantDatabase] = None):
        self._db = database or AssistantDatabase()
        self._db.init_default_phrases()

        # Rejestr metadanych modułów/akcji (może być rozszerzany dynamicznie)
        self._actions: Dict[str, Dict[str, AssistantActionMeta]] = {}
        self._init_default_actions()

    # ------------------------------------------------------------------
    # Akcje / moduły
    # ------------------------------------------------------------------
    def _init_default_actions(self) -> None:
        """Inicjalizuje podstawowe moduły i akcje w systemie."""

        def register(module: str, action: str, label_key: str, label_default: str, desc_key: str, desc_default: str):
            self._actions.setdefault(module, {})[action] = AssistantActionMeta(
                module=module,
                action=action,
                label_key=label_key,
                label_default=label_default,
                description_key=desc_key,
                description_default=desc_default,
            )

        register("task", "create", "assistant.action.task.create", "Utwórz zadanie", "assistant.action.task.create.desc", "Tworzy nowe zadanie")
        register("task", "delete", "assistant.action.task.delete", "Usuń zadanie", "assistant.action.task.delete.desc", "Usuwa zadanie")
        register("task", "open", "assistant.action.task.open", "Otwórz zadanie", "assistant.action.task.open.desc", "Otwiera zadanie")
        register("task", "list", "assistant.action.task.list", "Pokaż zadania", "assistant.action.task.list.desc", "Wyświetla listę zadań")

        register("note", "create", "assistant.action.note.create", "Utwórz notatkę", "assistant.action.note.create.desc", "Tworzy nową notatkę")
        register("note", "delete", "assistant.action.note.delete", "Usuń notatkę", "assistant.action.note.delete.desc", "Usuwa notatkę")
        register("note", "open", "assistant.action.note.open", "Otwórz notatkę", "assistant.action.note.open.desc", "Otwiera notatkę")
        register("note", "list", "assistant.action.note.list", "Pokaż notatki", "assistant.action.note.list.desc", "Wyświetla listę notatek")

        register("alarm", "create", "assistant.action.alarm.create", "Ustaw alarm", "assistant.action.alarm.create.desc", "Tworzy nowy alarm")
        register("alarm", "delete", "assistant.action.alarm.delete", "Usuń alarm", "assistant.action.alarm.delete.desc", "Usuwa alarm")
        register("alarm", "list", "assistant.action.alarm.list", "Pokaż alarmy", "assistant.action.alarm.list.desc", "Wyświetla alarmy")

        register("pomodoro", "open", "assistant.action.pomodoro.open", "Otwórz pomodoro", "assistant.action.pomodoro.open.desc", "Otwiera moduł pomodoro")
        register("pomodoro", "start", "assistant.action.pomodoro.start", "Start pomodoro", "assistant.action.pomodoro.start.desc", "Uruchamia sesję pomodoro")
        register("pomodoro", "pause", "assistant.action.pomodoro.pause", "Pauza pomodoro", "assistant.action.pomodoro.pause.desc", "Wstrzymuje sesję pomodoro")
        register("pomodoro", "stop", "assistant.action.pomodoro.stop", "Stop pomodoro", "assistant.action.pomodoro.stop.desc", "Zatrzymuje sesję pomodoro")

        register("kanban", "open", "assistant.action.kanban.open", "Otwórz tablicę", "assistant.action.kanban.open.desc", "Otwiera moduł kanban")
        register("transcryptor", "open", "assistant.action.transcryptor.open", "Otwórz transkryptor", "assistant.action.transcryptor.open.desc", "Otwiera moduł transkryptora")
        register("mail", "create", "assistant.action.mail.create", "Nowa wiadomość", "assistant.action.mail.create.desc", "Tworzy nową wiadomość e-mail")
        register("folder", "open", "assistant.action.folder.open", "Otwórz folder", "assistant.action.folder.open.desc", "Otwiera folder dokumentów")
        register("browser", "open", "assistant.action.browser.open", "Otwórz przeglądarkę", "assistant.action.browser.open.desc", "Uruchamia przeglądarkę wbudowaną")
        register("settings", "open", "assistant.action.settings.open", "Otwórz ustawienia", "assistant.action.settings.open.desc", "Otwiera ustawienia aplikacji")

    def get_modules(self) -> List[str]:
        """Zwraca zarejestrowane moduły."""
        modules = sorted(set(self._actions.keys()) | set(self._db.get_available_modules()))
        logger.debug("[AssistantSettings] Modules available: %s", modules)
        return modules

    def get_actions(self, module: str) -> List[AssistantActionMeta]:
        """Zwraca akcje dla modułu."""
        actions = self._actions.get(module, {})
        ordered = sorted(actions.values(), key=lambda meta: meta.label)
        logger.debug("[AssistantSettings] Actions for %s: %s", module, [a.action for a in ordered])
        return ordered

    def get_action_meta(self, module: str, action: str) -> Optional[AssistantActionMeta]:
        return self._actions.get(module, {}).get(action)

    # ------------------------------------------------------------------
    # Operacje na frazach
    # ------------------------------------------------------------------
    def get_phrases(self, module: str, action: Optional[str] = None, language: Optional[str] = None, active_only: bool = True) -> List[AssistantPhrase]:
        return self._db.get_phrases(module=module, action=action, language=language, active_only=active_only)

    def add_phrase(
        self,
        module: str,
        action: str,
        phrase: str,
        language: str = "pl",
        priority: int = 5,
        extract_entity: bool = False,
        is_custom: bool = True,
        description: str = "",
    ) -> AssistantPhrase:
        phrase_obj = AssistantPhrase(
            module=module,
            action=action,
            phrase=phrase.strip(),
            language=language,
            priority=max(1, min(10, priority)),
            is_active=True,
            is_custom=is_custom,
            extract_entity=extract_entity,
            description=description,
        )
        phrase_id = self._db.add_phrase(phrase_obj)
        phrase_obj.id = phrase_id if phrase_id != -1 else None
        return phrase_obj

    def update_phrase(self, phrase: AssistantPhrase) -> bool:
        return self._db.update_phrase(phrase)

    def delete_phrase(self, phrase_id: int) -> bool:
        return self._db.delete_phrase(phrase_id)

    def toggle_phrase(self, phrase_id: int) -> bool:
        return self._db.toggle_phrase(phrase_id)

    def get_phrase(self, phrase_id: int) -> Optional[AssistantPhrase]:
        return self._db.get_phrase_by_id(phrase_id)

    def refresh_defaults(self) -> None:
        """Ponownie inicjalizuje domyślne frazy (tylko jeśli brak danych)."""
        self._db.init_default_phrases()
    
    # ------------------------------------------------------------------
    # Backward compatibility dla UI
    # ------------------------------------------------------------------
    def get_all_methods(self) -> Dict[str, Dict[str, str]]:
        """
        Zwraca słownik wszystkich metod/akcji w formacie zgodnym ze starym UI.
        
        Returns:
            Dict[method_name, {'name_pl': str, 'description_pl': str}]
        """
        result = {}
        for module in self.get_modules():
            actions = self.get_actions(module)
            for action_meta in actions:
                method_key = f"{module}.{action_meta.action}"
                result[method_key] = {
                    'name_pl': action_meta.label,
                    'description_pl': action_meta.description,
                }
        return result
    
    def get_phrases_for_method(
        self,
        method_name: str,
        language: Optional[str] = None,
    ) -> List[AssistantPhrase]:
        """
        Pobiera frazy dla konkretnej metody (module.action).
        
        Args:
            method_name: Nazwa metody w formacie "module.action"
            language: Opcjonalny filtr języka
            
        Returns:
            Lista fraz AssistantPhrase
        """
        parts = method_name.split(".", 1)
        if len(parts) != 2:
            logger.warning("[AssistantSettings] Invalid method name format: %s", method_name)
            return []
        
        module, action = parts
        return self.get_phrases(module=module, action=action, language=language, active_only=False)


__all__ = ["AssistantSettingsManager", "AssistantPhrase", "AssistantActionMeta"]
