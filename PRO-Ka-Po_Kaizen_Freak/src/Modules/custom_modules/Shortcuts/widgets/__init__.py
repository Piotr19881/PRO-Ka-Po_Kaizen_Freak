"""
Widgets package for Shortcuts module
Contains reusable UI components
"""

from .shortcut_capture_widget import ShortcutCaptureWidget
from .context_menus import TemplateContextMenu, ShortcutsContextMenu

__all__ = [
    'ShortcutCaptureWidget',
    'TemplateContextMenu',
    'ShortcutsContextMenu',
]
