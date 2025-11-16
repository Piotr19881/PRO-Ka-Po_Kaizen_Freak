import runpy
import sys
import traceback
from datetime import datetime
from pathlib import Path

LOG_PATH = Path("data") / "startup.log"
LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

with LOG_PATH.open("a", encoding="utf-8") as f:
    f.write(f"\n--- START {datetime.utcnow().isoformat()} UTC ---\n")
    f.write(f"python executable: {sys.executable}\n")
    f.write(f"cwd: {Path('.').resolve()}\n")
    try:
        # Run main.py as a script (preserve __main__ behavior)
        runpy.run_path("main.py", run_name="__main__")
        f.write(f"Exited normally at {datetime.utcnow().isoformat()}\n")
    except SystemExit as se:
        f.write(f"SystemExit: {se}\n")
        f.write(traceback.format_exc())
    except Exception:
        f.write("Unhandled exception:\n")
        f.write(traceback.format_exc())
        # don't re-raise: we want to persist the trace in log
