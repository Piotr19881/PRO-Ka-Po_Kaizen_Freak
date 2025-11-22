from pathlib import Path
import sys

__all__ = ["get_base_dir", "resource_path"]


def get_base_dir() -> Path:
    """Return application base directory in both dev and frozen (PyInstaller) modes.

    - When frozen (sys.frozen is True), return the directory containing the executable.
    - Otherwise return the project package root (assumes this file is in src/utils).
    """
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    # two levels up: src/ -> PRO-Ka-Po_Kaizen_Freak/
    return Path(__file__).resolve().parent.parent


def resource_path(*parts) -> str:
    """Build a filesystem path for bundled resources.

    Usage:
        icon = resource_path('resources', 'icons', 'app.ico')
    """
    return str(get_base_dir().joinpath(*parts))
