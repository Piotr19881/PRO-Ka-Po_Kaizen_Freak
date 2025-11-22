from pathlib import Path
from pprint import pprint
from datetime import date
import sys

# Make the Modules folder importable so this script can be run standalone
sys.path.insert(0, str(Path(__file__).parent.parent))

from importlib.util import spec_from_file_location, module_from_spec

# Load habit_database.py directly to avoid package-level relative import side effects
spec = spec_from_file_location(
    "habit_database_module",
    Path(__file__).parent / "habit_database.py",
)
if spec is None or spec.loader is None:
    raise RuntimeError("Failed to create module spec for habit_database.py")
mod = module_from_spec(spec)
spec.loader.exec_module(mod)
HabitDatabase = mod.HabitDatabase


def run_test():
    base = Path(__file__).parent
    db_file = base / "test_habit_db.sqlite"
    # remove existing file for a clean run
    try:
        db_file.unlink()
    except Exception:
        pass

    db = HabitDatabase(db_file, user_id=1)

    print("Created DB at:", db_file)

    # Add a habit column
    habit_id = db.add_habit_column("Test Habit", "checkbox", scale_max=1)
    print("Added habit_id:", habit_id)

    # List habits
    habits = db.get_habit_columns()
    print("Habits:")
    pprint(habits)

    # Set a record for today
    today = date.today().isoformat()
    ok = db.set_habit_record(habit_id, today, "1")
    print(f"Set record for {today}: {ok}")

    # Read it back
    val = db.get_habit_record(habit_id, today)
    print(f"Read back value for {today}: {val}")

    # Get month records
    r = db.get_habit_records_for_month(habit_id, date.today().year, date.today().month)
    print("Records for month:")
    pprint(r)

    # Export
    data = db.export_all_data()
    print("Exported data summary:")
    print(f"Columns: {len(data.get('columns', []))}, Records: {len(data.get('records', []))}")

    db.close()


if __name__ == '__main__':
    run_test()
