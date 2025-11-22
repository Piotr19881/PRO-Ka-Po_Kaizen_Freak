"""
launcher.py

Creates a project-local venv if missing, installs requirements (optional),
and launches main.py from the project folder using the venv's python.
On Windows it attempts to run the child process with no console (hidden).

Usage:
    - Double-clicking this file will normally show a console for the launcher
      itself unless the launcher is invoked by pythonw.exe or from a shortcut
      that launches pythonw.exe. The script launches `main.py` detached and
      hidden (Windows) so you can exit the launcher afterwards.

Behavior summary:
    1. If ./venv does not exist, create it and install requirements.txt (if present).
    2. Launch main.py using the venv python. On Windows prefer pythonw.exe if present,
       otherwise use python.exe with CREATE_NO_WINDOW.

Note: If you want no console at all when starting the launcher, create a shortcut
that runs the venv's pythonw.exe and passes this script, or call this script with
pythonw.exe.
"""

from __future__ import annotations
import sys
import os
import subprocess
import venv
from pathlib import Path
import shutil

APP_DIR = Path(__file__).resolve().parent
VENV_DIR = APP_DIR / "venv"

# Allow forcing use of system Python instead of the project venv.
# Methods:
#  - Command line flag: --use-system-python
#  - Environment variable: USE_SYSTEM_PYTHON=1
USE_SYSTEM_PYTHON = False
if os.environ.get('USE_SYSTEM_PYTHON', '').lower() in ('1', 'true', 'yes'):
    USE_SYSTEM_PYTHON = True
if '--use-system-python' in sys.argv:
    USE_SYSTEM_PYTHON = True

if os.name == "nt":
    PYTHON_EXE = VENV_DIR / "Scripts" / "python.exe"
    PYTHONW_EXE = VENV_DIR / "Scripts" / "pythonw.exe"
else:
    PYTHON_EXE = VENV_DIR / "bin" / "python"
    PYTHONW_EXE = None

REQUIREMENTS = APP_DIR / "requirements.txt"


def create_venv() -> None:
    """Create venv with pip and optionally install requirements."""
    print(f"Creating virtual environment in {VENV_DIR}")
    builder = venv.EnvBuilder(with_pip=True)
    builder.create(str(VENV_DIR))

    # Ensure pip/setuptools/wheel are up-to-date
    python = str(PYTHON_EXE)
    try:
        subprocess.check_call([python, "-m", "pip", "install", "--upgrade", "pip", "setuptools", "wheel"])
    except subprocess.CalledProcessError as e:
        print("Warning: failed to upgrade pip/setuptools/wheel:", e, file=sys.stderr)

    if REQUIREMENTS.exists():
        print("Installing requirements.txt into venv...")
        try:
            subprocess.check_call([python, "-m", "pip", "install", "-r", str(REQUIREMENTS)])
        except subprocess.CalledProcessError as e:
            print("Warning: failed to install requirements:", e, file=sys.stderr)


def ensure_venv() -> None:
    # Only ensure venv when not explicitly using system python
    if USE_SYSTEM_PYTHON:
        print("Launcher: using system Python (skipping venv ensure)")
        return

    if not PYTHON_EXE.exists():
        create_venv()


def launch_main() -> int:
    main_py = APP_DIR / "main.py"
    if not main_py.exists():
        print("Error: main.py not found in project folder.")
        return 2

    # Choose python executable: system Python or project venv
    if USE_SYSTEM_PYTHON:
        # Try to find pythonw (no console) first on Windows, then python
        if os.name == 'nt':
            pythonw = shutil.which('pythonw')
            python = shutil.which('python') or shutil.which('py')
            if pythonw:
                exe = pythonw
                use_creationflags = False
            elif python:
                exe = python
                use_creationflags = True
            else:
                print("Error: system Python not found in PATH." , file=sys.stderr)
                return 4
        else:
            # POSIX: use 'python3' or 'python'
            exe = shutil.which('python3') or shutil.which('python')
            if not exe:
                print("Error: system Python not found in PATH." , file=sys.stderr)
                return 4
            use_creationflags = False
    else:
        # Prefer pythonw on Windows if available in venv
        if os.name == "nt" and PYTHONW_EXE and PYTHONW_EXE.exists():
            exe = str(PYTHONW_EXE)
            use_creationflags = False
        else:
            exe = str(PYTHON_EXE)
            use_creationflags = os.name == "nt"

    cmd = [exe, str(main_py)]

    # Launch detached, hide console on Windows
    try:
        if os.name == "nt" and use_creationflags:
            # CREATE_NO_WINDOW to hide console. Don't wait for child.
            CREATE_NO_WINDOW = 0x08000000
            subprocess.Popen(cmd, cwd=str(APP_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW, close_fds=True)
        elif os.name == "nt":
            # pythonw case
            subprocess.Popen(cmd, cwd=str(APP_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        else:
            # POSIX: detach using setsid
            subprocess.Popen(cmd, cwd=str(APP_DIR), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, preexec_fn=os.setsid, close_fds=True)
    except Exception as e:
        print("Failed to start main.py:", e, file=sys.stderr)
        return 3

    return 0


def main() -> int:
    try:
        ensure_venv()
    except Exception as e:
        print("Failed to create/ensure venv:", e, file=sys.stderr)
        # continue: attempt to launch even if venv creation failed
    rc = launch_main()
    return rc


if __name__ == "__main__":
    sys.exit(main())
