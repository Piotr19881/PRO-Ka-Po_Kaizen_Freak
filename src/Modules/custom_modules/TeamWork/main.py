"""Entry point for running the TeamWork module standalone."""

import sys
from pathlib import Path

# Dodaj katalog nadrzędny do sys.path
parent_dir = Path(__file__).resolve().parent.parent
if str(parent_dir) not in sys.path:
    sys.path.insert(0, str(parent_dir))

from PyQt6.QtWidgets import QApplication
from .teamwork_window import TeamWorkWindow


def main() -> int:
    app = QApplication(sys.argv)
    window = TeamWorkWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
