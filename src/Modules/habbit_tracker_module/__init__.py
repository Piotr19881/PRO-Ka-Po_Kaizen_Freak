"""
Habit Tracker Module - Moduł śledzenia nawyków

Zawiera:
- HabitTrackerView: Główny widok z kalendarzem miesięcznym
- HabitDialogs: Dialogi do edycji różnych typów nawyków
- HabitDatabase: Warstwa dostępu do danych (lokalna + sync)
"""

from .habit_tracker_view import HabbitTrackerView
from .habit_dialogs import (
    AddHabbitDialog as AddHabitDialog,
    RemoveHabbitDialog as RemoveHabitDialog,
    SimpleCheckboxDialog,
    SimpleCounterDialog,
    SimpleDurationDialog,
    SimpleTimeDialog,
    SimpleScaleDialog,
    SimpleTextDialog
)

__all__ = [
    'HabbitTrackerView',
    'AddHabitDialog',
    'RemoveHabitDialog',
    'SimpleCheckboxDialog',
    'SimpleCounterDialog',
    'SimpleDurationDialog',
    'SimpleTimeDialog',
    'SimpleScaleDialog',
    'SimpleTextDialog',
]
